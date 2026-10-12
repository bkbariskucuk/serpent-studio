"""Serpent Studio Control Plane & Administration Server.

Standard-library HTTP backend (optional PostgreSQL storage) providing:
- Authentication & Session Token Management
- Remote User Provisioning & Account Suspension (Kill-Switch)
- Tester Error & Crash Report Ingestion
- User Serpent Script & Telemetry Collection
- Responsive Dark-Mode Web Admin Dashboard (/admin)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import http.server
import json
import logging
import os
import secrets
import sqlite3
import sys
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

if __package__:
    from .storage import Backend, validate_database_url
else:
    from storage import Backend, validate_database_url

logger = logging.getLogger("serpent.control_plane")

DEFAULT_PORT = int(os.environ.get("PORT", os.environ.get("SERPENT_CONTROL_PLANE_PORT", 8080)))
DEFAULT_HOST = os.environ.get("SERPENT_CONTROL_PLANE_HOST", "0.0.0.0")
DB_PATH = os.environ.get("SERPENT_CONTROL_PLANE_DB", os.path.join(os.path.dirname(__file__), "control_plane.db"))

MIN_PASSWORD_LENGTH = 12
SESSION_MAX_AGE = 30 * 86400
MAX_REQUEST_BODY = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 15
MAX_CONCURRENT_REQUESTS = 32

RATE_LIMIT_WINDOW_SECONDS = 300.0
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_LOCKOUT_SECONDS = 300.0


class LoginRateLimiter:
    """In-memory sliding window rate limiter to protect authentication endpoints."""

    def __init__(self, max_attempts: int = RATE_LIMIT_MAX_ATTEMPTS,
                 window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
                 lockout_seconds: float = RATE_LIMIT_LOCKOUT_SECONDS) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._lock = threading.Lock()
        self._failures: Dict[str, List[float]] = {}
        self._lockouts: Dict[str, float] = {}

    def is_locked(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        with self._lock:
            lockout_until = self._lockouts.get(key, 0.0)
            if now < lockout_until:
                return True, max(1, int(lockout_until - now))
            if key in self._lockouts:
                del self._lockouts[key]
            return False, 0

    def record_failure(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        with self._lock:
            timestamps = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
            timestamps.append(now)
            self._failures[key] = timestamps
            if len(timestamps) >= self.max_attempts:
                lockout_until = now + self.lockout_seconds
                self._lockouts[key] = lockout_until
                self._failures.pop(key, None)
                return True, int(self.lockout_seconds)
            return False, 0

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._lockouts.pop(key, None)

    def reset_for_tests(self) -> None:
        with self._lock:
            self._failures.clear()
            self._lockouts.clear()


LOGIN_RATE_LIMITER = LoginRateLimiter()


def validate_storage_configuration(db_path: str, database_url: str = '') -> None:
    """On Render, refuse SQLite on the ephemeral application filesystem."""
    if database_url:
        validate_database_url(database_url)
        return
    if os.environ.get("RENDER", "").lower() not in ("1", "true"):
        return
    data_dir = os.environ.get("SERPENT_CONTROL_PLANE_DATA_DIR", "")
    configured_db = os.environ.get("SERPENT_CONTROL_PLANE_DB", "")
    if not data_dir or not configured_db or not os.path.isabs(data_dir) or not os.path.isabs(configured_db):
        raise RuntimeError("Render requires SERPENT_DATABASE_URL for persistent PostgreSQL, or a configured persistent SQLite disk.")
    real_dir, real_db = os.path.realpath(data_dir), os.path.realpath(db_path)
    if (real_db != os.path.realpath(configured_db)
            or os.path.commonpath((real_dir, real_db)) != real_dir
            or real_db == real_dir or not os.path.ismount(real_dir)
            or not os.access(real_dir, os.W_OK)):
        raise RuntimeError("The control-plane database must be inside the writable persistent disk mount.")


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000).hex()
    return hashed, salt


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    try:
        computed, _ = hash_password(password, salt)
        return hmac.compare_digest(computed, expected_hash)
    except (ValueError, TypeError):
        return False


class Database:
    def __init__(self, db_path: str = DB_PATH, *, admin_username: Optional[str] = None, admin_password: Optional[str] = None,
                 database_url: str = '', bootstrap_admin: bool = True) -> None:
        self.db_path = db_path
        self._backend = Backend(db_path, database_url)
        self._lock = threading.Lock()
        self._admin_username = (admin_username or os.environ.get("SERPENT_ADMIN_USER", "admin")).strip().lower()
        self._admin_password = admin_password if admin_password is not None else os.environ.get("SERPENT_ADMIN_PASS")
        self._init_schema(bootstrap_admin=bootstrap_admin)
        self._admin_password = None

    def _get_conn(self):
        return self._backend.connection()

    def _init_schema(self, *, bootstrap_admin: bool = True) -> None:
        if not self._backend.postgres:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        identity = 'BIGSERIAL PRIMARY KEY' if self._backend.postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
        timestamp_type = 'DOUBLE PRECISION' if self._backend.postgres else 'REAL'
        with self._lock, self._get_conn() as conn:
            if self._backend.postgres:
                # Serializes migrations/bootstrap across overlapping web instances.
                conn.execute('SELECT pg_advisory_xact_lock(73657270656)')
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS users (
                    id {identity},
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'tester',
                    display_name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at {timestamp_type} NOT NULL,
                    expires_at {timestamp_type}
                )
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT NOT NULL,
                    client_version TEXT,
                    platform TEXT,
                    created_at {timestamp_type} NOT NULL,
                    last_heartbeat {timestamp_type} NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS error_reports (
                    id {identity},
                    username TEXT NOT NULL,
                    app_version TEXT,
                    platform TEXT,
                    exception_type TEXT,
                    exception_message TEXT,
                    traceback TEXT,
                    active_tab TEXT,
                    recent_logs TEXT,
                    timestamp {timestamp_type} NOT NULL
                )
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS scripts (
                    id {identity},
                    username TEXT NOT NULL,
                    project_name TEXT,
                    script_content TEXT,
                    timestamp {timestamp_type} NOT NULL
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS admin_bootstrap (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, salt TEXT NOT NULL)")
            # Ensure restricted_panels column exists
            if self._backend.postgres:
                cursor.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='users'")
            else:
                cursor.execute("PRAGMA table_info(users)")
            cols = [r["name"] for r in cursor.fetchall()]
            if "restricted_panels" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN restricted_panels TEXT DEFAULT '[]'")
            if bootstrap_admin:
                self._bootstrap_admin(cursor)
            conn.commit()

    def _bootstrap_admin(self, cursor) -> None:
        cursor.execute("SELECT id FROM users WHERE username = ?", (self._admin_username,))
        admin = cursor.fetchone()
        bootstrap_pass = self._admin_password
        if not admin and not bootstrap_pass:
            raise ValueError("Set SERPENT_ADMIN_PASS to bootstrap the administrator account; no default password is provided.")
        if bootstrap_pass and len(bootstrap_pass) < MIN_PASSWORD_LENGTH:
            raise ValueError("SERPENT_ADMIN_PASS must contain at least 12 characters.")
        if not admin:
            h, s = hash_password(bootstrap_pass)
            cursor.execute("""INSERT INTO users (username, password_hash, salt, role, display_name, is_active, created_at)
                              VALUES (?, ?, ?, 'administrator', 'System Administrator', 1, ?)""",
                           (self._admin_username, h, s, time.time()))
        if bootstrap_pass:
            cursor.execute("SELECT password_hash, salt FROM admin_bootstrap WHERE username = ?", (self._admin_username,))
            previous = cursor.fetchone()
            # A new env secret rotates credentials; an unchanged env must not undo
            # a self-service password change when the web service restarts.
            if not previous or not verify_password(bootstrap_pass, previous['password_hash'], previous['salt']):
                h, s = hash_password(bootstrap_pass)
                cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", (h, s, self._admin_username))
                cursor.execute("UPDATE sessions SET is_revoked = 1 WHERE username = ?", (self._admin_username,))
                cursor.execute("""INSERT INTO admin_bootstrap (username,password_hash,salt) VALUES (?, ?, ?)
                                  ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, salt=excluded.salt""",
                               (self._admin_username, h, s))

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_user(
        self, username: str, password: str, role: str = "tester",
        display_name: str = "", expires_at: Optional[float] = None,
        restricted_panels: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        u = username.strip().lower()
        if not u or len(u) < 3:
            return False, "Username must be at least 3 characters."
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            return False, "Password must be at least 12 characters."

        h, s = hash_password(password)
        panels_json = json.dumps(restricted_panels or [])
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO users (username, password_hash, salt, role, display_name, is_active, created_at, expires_at, restricted_panels)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """, (u, h, s, role.strip(), display_name or u, time.time(), expires_at, panels_json))
                conn.commit()
                return True, "User created successfully."
            except self._backend.integrity_error:
                conn.rollback()
                return False, f"User '{u}' already exists."

    def set_user_restrictions(self, username: str, restricted_panels: List[str]) -> bool:
        panels_json = json.dumps(restricted_panels or [])
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET restricted_panels = ? WHERE username = ?", (panels_json, username.strip().lower()))
            conn.commit()
            return cur.rowcount > 0

    def set_user_role(self, username: str, role: str) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET role = ? WHERE username = ?", (role.strip(), username.strip().lower()))
            conn.commit()
            return cur.rowcount > 0

    def set_user_status(self, username: str, is_active: bool) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_active = ? WHERE username = ?", (1 if is_active else 0, username.strip().lower()))
            changed = cur.rowcount > 0
            if not is_active:
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE username = ?", (username.strip().lower(),))
            conn.commit()
            return changed

    def reset_password(self, username: str, new_password: str) -> bool:
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return False
        h, s = hash_password(new_password)
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", (h, s, username.strip().lower()))
            changed = cur.rowcount > 0
            cur.execute("UPDATE sessions SET is_revoked = 1 WHERE username = ?", (username.strip().lower(),))
            conn.commit()
            return changed

    def delete_user(self, username: str) -> bool:
        if username.strip().lower() == self._admin_username:
            return False
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE username = ?", (username.strip().lower(),))
            cur.execute("DELETE FROM users WHERE username = ?", (username.strip().lower(),))
            conn.commit()
            return cur.rowcount > 0

    def list_users(self) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.id, u.username, u.role, u.display_name, u.is_active, u.created_at, u.expires_at, u.restricted_panels,
                       MAX(s.last_heartbeat) as last_seen, MAX(s.client_version) as client_version
                FROM users u
                LEFT JOIN sessions s ON u.id = s.user_id AND s.is_revoked = 0
                GROUP BY u.id
                ORDER BY u.created_at DESC
            """)
            users = []
            for r in cur.fetchall():
                d = dict(r)
                try:
                    d["restricted_panels"] = json.loads(d.get("restricted_panels") or "[]")
                except Exception:
                    d["restricted_panels"] = []
                users.append(d)
            return users

    def create_session(self, user_id: int, username: str, client_version: str = "", platform: str = "") -> str:
        token = secrets.token_hex(24)
        now = time.time()
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sessions (token, user_id, username, client_version, platform, created_at, last_heartbeat, is_revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (token, user_id, username, client_version, platform, now, now))
            conn.commit()
        return token

    def revoke_session(self, token: str) -> None:
        with self._lock, self._get_conn() as conn:
            conn.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
            conn.commit()

    def change_user_password(self, token: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Atomically change the authenticated user's password and rotate all sessions."""
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return False, "New password must be at least 12 characters."
        with self._lock, self._get_conn() as conn:
            if not self._backend.postgres:
                conn.execute("BEGIN IMMEDIATE")
            sql = "SELECT u.*, s.created_at AS session_created FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.is_revoked=0"
            if self._backend.postgres:
                sql += " FOR UPDATE OF u, s"
            row = conn.execute(sql, (token,)).fetchone()
            if (not row or not row["is_active"] or (row["expires_at"] and row["expires_at"] < time.time())
                    or time.time() - row["session_created"] > SESSION_MAX_AGE
                    or not verify_password(current_password, row["password_hash"], row["salt"])):
                return False, "Current password verification failed."
            hashed, salt = hash_password(new_password)
            conn.execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (hashed, salt, row["id"]))
            conn.execute("UPDATE sessions SET is_revoked=1 WHERE user_id=?", (row["id"],))
            replacement = secrets.token_hex(24)
            now = time.time()
            conn.execute("INSERT INTO sessions (token,user_id,username,created_at,last_heartbeat,is_revoked) VALUES (?,?,?,?,?,0)", (replacement, row["id"], row["username"], now, now))
            conn.commit()
            return True, replacement

    def verify_and_touch_session(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if not token:
            return False, None
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, u.is_active, u.role, u.expires_at, u.restricted_panels
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND s.is_revoked = 0
            """, (token,))
            row = cur.fetchone()
            if not row:
                return False, None

            data = dict(row)
            if time.time() - data["created_at"] > SESSION_MAX_AGE:
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
                conn.commit()
                return False, None
            if not data.get("is_active"):
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
                conn.commit()
                return False, None

            expires_at = data.get("expires_at")
            if expires_at and time.time() > expires_at:
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
                conn.commit()
                return False, None

            cur.execute("UPDATE sessions SET last_heartbeat = ? WHERE token = ?", (time.time(), token))
            conn.commit()
            return True, data

    def record_error(
        self, username: str, app_version: str, platform: str,
        exception_type: str, exception_message: str, traceback_str: str,
        active_tab: str = "", recent_logs: str = ""
    ) -> int:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            sql = """
                INSERT INTO error_reports
                (username, app_version, platform, exception_type, exception_message, traceback, active_tab, recent_logs, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            if self._backend.postgres:
                sql += " RETURNING id"
            cur.execute(sql, (username, app_version, platform, exception_type, exception_message, traceback_str, active_tab, recent_logs, time.time()))
            row_id = cur.fetchone()['id'] if self._backend.postgres else cur.lastrowid
            conn.commit()
            return row_id

    def list_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM error_reports ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def record_script(self, username: str, project_name: str, script_content: str) -> int:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            sql = """
                INSERT INTO scripts (username, project_name, script_content, timestamp)
                VALUES (?, ?, ?, ?)
            """
            if self._backend.postgres:
                sql += " RETURNING id"
            cur.execute(sql, (username, project_name, script_content, time.time()))
            row_id = cur.fetchone()['id'] if self._backend.postgres else cur.lastrowid
            conn.commit()
            return row_id

    def list_scripts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, username, project_name, timestamp, LENGTH(script_content) as size FROM scripts ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_script_content(self, script_id: int) -> Optional[str]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT script_content FROM scripts WHERE id = ?", (script_id,))
            row = cur.fetchone()
            return row["script_content"] if row else None


class RequestError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class BoundedHTTPServer(http.server.ThreadingHTTPServer):
    """Bound request threads and reject overload without queuing unbounded work."""

    daemon_threads = True

    def __init__(self, *args, max_workers: int = MAX_CONCURRENT_REQUESTS, **kwargs):
        if max_workers < 1:
            raise ValueError('max_workers must be positive.')
        self._request_slots = threading.BoundedSemaphore(max_workers)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._request_slots.acquire(blocking=False):
            try:
                request.settimeout(1.0)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\nRetry-After: 1\r\n\r\n')
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


class ControlPlaneHandler(http.server.BaseHTTPRequestHandler):
    db: Database

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    def log_message(self, format: str, *args: Any) -> None:
        # Request targets, driver exception strings, and bodies can contain secrets.
        logger.debug("Control-plane HTTP request handled")

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if self.client_address:
            return str(self.client_address[0])
        return "127.0.0.1"

    def _get_allowed_origin(self) -> Optional[str]:
        origin = self.headers.get("Origin")
        if not origin:
            return None
        parsed = urllib.parse.urlparse(origin)
        host_header = self.headers.get("Host", "").strip()
        if parsed.netloc and host_header and parsed.netloc.lower() == host_header.lower():
            return origin
        if parsed.hostname in ("127.0.0.1", "localhost", "::1"):
            return origin
        return None

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        allowed_origin = self._get_allowed_origin()
        if allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
            self.send_header("Vary", "Origin")
        if status_code == 429 and "retry_after" in data:
            self.send_header("Retry-After", str(data["retry_after"]))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, status_code: int, html_str: str) -> None:
        payload = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            raise RequestError(400, 'Invalid Content-Length.') from None
        if length < 0:
            raise RequestError(400, 'Invalid Content-Length.')
        if length > MAX_REQUEST_BODY:
            self.close_connection = True
            raise RequestError(413, 'Request body exceeds the 2 MiB limit.')
        if length == 0:
            return {}
        try:
            raw = self.rfile.read(length).decode("utf-8")
            body = json.loads(raw)
        except (UnicodeError, ValueError):
            raise RequestError(400, 'Request body must be a JSON object.') from None
        if not isinstance(body, dict):
            raise RequestError(400, 'Request body must be a JSON object.')
        return body

    def _handle_request(self, handler) -> None:
        try:
            handler()
        except RequestError as exc:
            self._send_json(exc.status, {'status':'error', 'message':str(exc)})
        except TimeoutError:
            self.close_connection = True
            self._send_json(408, {'status':'error', 'message':'Request timed out.'})
        except Exception as exc:
            logger.error('Control-plane request failed (%s)', type(exc).__name__)
            self._send_json(503, {'status':'error', 'message':'Service temporarily unavailable. Please retry.'})

    def _get_bearer_token(self) -> str:
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        return ""

    def do_OPTIONS(self) -> None:
        allowed_origin = self._get_allowed_origin()
        self.send_response(204)
        if allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:
        self._handle_request(self._do_GET)

    def _do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/health" or path == "":
            self._send_json(200, {"status": "ok", "service": "SerpentStudio-ControlPlane", "time": time.time()})
            return

        if path == "/admin":
            self._send_html(200, ADMIN_DASHBOARD_HTML)
            return

        # Admin REST Endpoints
        token = self._get_bearer_token()
        valid, session_data = self.db.verify_and_touch_session(token)

        if path.startswith("/admin/api/"):
            if not valid or session_data.get("role") != "administrator":
                self._send_json(401, {"status": "error", "message": "Unauthorized admin access."})
                return

            if path == "/admin/api/users":
                users = self.db.list_users()
                self._send_json(200, {"status": "ok", "users": users})
                return

            if path == "/admin/api/errors":
                errors = self.db.list_errors()
                self._send_json(200, {"status": "ok", "errors": errors})
                return

            if path == "/admin/api/scripts":
                scripts = self.db.list_scripts()
                self._send_json(200, {"status": "ok", "scripts": scripts})
                return

            if path.startswith("/admin/api/script/"):
                try:
                    s_id = int(path.split("/")[-1])
                    content = self.db.get_script_content(s_id)
                    if content is not None:
                        self._send_json(200, {"status": "ok", "content": content})
                    else:
                        self._send_json(404, {"status": "error", "message": "Script not found."})
                except Exception:
                    self._send_json(400, {"status": "error", "message": "Invalid script id."})
                return

        self._send_json(404, {"status": "error", "message": "Endpoint not found."})

    def do_POST(self) -> None:
        self._handle_request(self._do_POST)

    def _do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_json_body()

        # Client Authentication Endpoint
        if path in ("/v1/auth/login", "/api/v1/auth/login"):
            client_ip = self._client_ip()
            locked, remaining = LOGIN_RATE_LIMITER.is_locked(client_ip)
            if locked:
                self._send_json(429, {
                    "status": "error",
                    "message": f"Too many failed login attempts. Please wait {remaining} seconds before retrying.",
                    "retry_after": remaining,
                })
                return

            username = str(body.get("username", "")).strip().lower()
            password = str(body.get("password", ""))
            client_version = str(body.get("client_version", ""))
            platform = str(body.get("platform", ""))

            user = self.db.get_user(username)
            if not user or not verify_password(password, user["password_hash"], user["salt"]):
                locked_now, wait_time = LOGIN_RATE_LIMITER.record_failure(client_ip)
                if locked_now:
                    self._send_json(429, {
                        "status": "error",
                        "message": f"Too many failed login attempts. Account temporarily locked for {wait_time} seconds.",
                        "retry_after": wait_time,
                    })
                else:
                    self._send_json(401, {"status": "error", "message": "Invalid username or password."})
                return

            LOGIN_RATE_LIMITER.record_success(client_ip)

            if not user.get("is_active"):
                self._send_json(403, {"status": "error", "message": "Account suspended by administrator."})
                return

            expires_at = user.get("expires_at")
            if expires_at and time.time() > expires_at:
                self._send_json(403, {"status": "error", "message": "Account license expired."})
                return

            token = self.db.create_session(user["id"], user["username"], client_version, platform)
            try:
                restricted_panels = json.loads(user.get("restricted_panels") or "[]")
            except Exception:
                restricted_panels = []
            self._send_json(200, {
                "status": "success",
                "message": "Authentication successful",
                "token": token,
                "user": {
                    "username": user["username"],
                    "role": user["role"],
                    "display_name": user["display_name"],
                    "is_active": bool(user["is_active"]),
                    "restricted_panels": restricted_panels,
                },
                "restricted_panels": restricted_panels,
            })
            return

        # Client Heartbeat Endpoint
        if path == "/v1/telemetry/heartbeat":
            token = self._get_bearer_token() or str(body.get("token", ""))
            valid, session_data = self.db.verify_and_touch_session(token)
            if not valid or not session_data:
                self._send_json(403, {
                    "status": "suspended",
                    "account_status": "suspended",
                    "message": "Hesabınız yönetici tarafından askıya alınmıştır veya oturum sonlandırılmıştır."
                })
                return

            try:
                restricted_panels = json.loads(session_data.get("restricted_panels") or "[]")
            except Exception:
                restricted_panels = []

            self._send_json(200, {
                "status": "ok",
                "account_status": "active",
                "username": session_data["username"],
                "role": session_data.get("role", "tester"),
                "restricted_panels": restricted_panels,
                "message": "Heartbeat acknowledged"
            })
            return

        if path == "/v1/auth/change-password":
            token = self._get_bearer_token()
            valid, _ = self.db.verify_and_touch_session(token)
            if not valid:
                self._send_json(401, {"status": "error", "message": "Sign in again to change your password."})
                return
            ok, result = self.db.change_user_password(token, str(body.get("current_password", "")), str(body.get("new_password", "")))
            self._send_json(200 if ok else 403, {"status": "ok", "token": result} if ok else {"status": "error", "message": result})
            return

        if path in ("/v1/auth/logout", "/admin/api/logout"):
            self.db.revoke_session(self._get_bearer_token())
            self._send_json(200, {"status": "ok"})
            return

        # Client Error & Crash Report Endpoint
        if path == "/v1/telemetry/errors":
            token = self._get_bearer_token() or str(body.get("token", ""))
            valid, session_data = self.db.verify_and_touch_session(token)
            if not valid or not session_data:
                self._send_json(401, {"status": "error", "message": "A valid session is required for telemetry."})
                return
            username = session_data["username"]

            rep_id = self.db.record_error(
                username=username,
                app_version=str(body.get("app_version", "")),
                platform=str(body.get("platform", "")),
                exception_type=str(body.get("exception_type", "UnknownError")),
                exception_message=str(body.get("exception_message", "")),
                traceback_str=str(body.get("traceback", "")),
                active_tab=str(body.get("active_tab", "")),
                recent_logs=str(body.get("recent_logs", "")),
            )
            self._send_json(200, {"status": "ok", "report_id": rep_id, "message": "Error report recorded."})
            return

        # Client Script Ingestion Endpoint
        if path == "/v1/telemetry/scripts":
            token = self._get_bearer_token() or str(body.get("token", ""))
            valid, session_data = self.db.verify_and_touch_session(token)
            if not valid or not session_data:
                self._send_json(401, {"status": "error", "message": "A valid session is required for telemetry."})
                return
            username = session_data["username"]

            s_id = self.db.record_script(
                username=username,
                project_name=str(body.get("project_name", "Untitled")),
                script_content=str(body.get("script_content", "")),
            )
            self._send_json(200, {"status": "ok", "script_id": s_id, "message": "Script recorded."})
            return

        # Admin Web Management Endpoints
        token = self._get_bearer_token()
        valid, session_data = self.db.verify_and_touch_session(token)

        if path == "/admin/api/login":
            client_ip = self._client_ip()
            locked, remaining = LOGIN_RATE_LIMITER.is_locked(client_ip)
            if locked:
                self._send_json(429, {
                    "status": "error",
                    "message": f"Too many failed login attempts. Please wait {remaining} seconds before retrying.",
                    "retry_after": remaining,
                })
                return

            u = str(body.get("username", "")).strip().lower()
            p = str(body.get("password", ""))
            user = self.db.get_user(u)
            if (user and user["role"] == "administrator" and user["is_active"]
                    and (not user["expires_at"] or user["expires_at"] > time.time())
                    and verify_password(p, user["password_hash"], user["salt"])):
                LOGIN_RATE_LIMITER.record_success(client_ip)
                adm_token = self.db.create_session(user["id"], user["username"], "web-admin", "browser")
                self._send_json(200, {"status": "ok", "token": adm_token, "username": user["username"]})
            else:
                locked_now, wait_time = LOGIN_RATE_LIMITER.record_failure(client_ip)
                if locked_now:
                    self._send_json(429, {
                        "status": "error",
                        "message": f"Too many failed login attempts. Account temporarily locked for {wait_time} seconds.",
                        "retry_after": wait_time,
                    })
                else:
                    self._send_json(401, {"status": "error", "message": "Invalid administrator credentials."})
            return

        if path.startswith("/admin/api/"):
            if not valid or session_data.get("role") != "administrator":
                self._send_json(401, {"status": "error", "message": "Unauthorized admin access."})
                return

            if path == "/admin/api/users/create":
                panels = body.get("restricted_panels", [])
                ok, msg = self.db.create_user(
                    username=str(body.get("username", "")),
                    password=str(body.get("password", "")),
                    role=str(body.get("role", "tester")),
                    display_name=str(body.get("display_name", "")),
                    restricted_panels=panels if isinstance(panels, list) else [],
                )
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error", "message": msg})
                return

            if path == "/admin/api/users/set-restrictions":
                u = str(body.get("username", "")).strip().lower()
                panels = body.get("restricted_panels", [])
                if not isinstance(panels, list):
                    panels = []
                ok = self.db.set_user_restrictions(u, panels)
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error", "restricted_panels": panels})
                return

            if path == "/admin/api/users/set-role":
                u = str(body.get("username", "")).strip().lower()
                role = str(body.get("role", "tester")).strip()
                if not role:
                    self._send_json(400, {"status": "error", "message": "Role cannot be empty."})
                    return
                ok = self.db.set_user_role(u, role)
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error", "role": role})
                return

            if path == "/admin/api/users/toggle-status":
                u = str(body.get("username", ""))
                active = bool(body.get("is_active", True))
                ok = self.db.set_user_status(u, active)
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error", "is_active": active})
                return

            if path == "/admin/api/users/reset-password":
                u = str(body.get("username", ""))
                p = str(body.get("password", ""))
                ok = self.db.reset_password(u, p)
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error"})
                return

            if path == "/admin/api/users/delete":
                u = str(body.get("username", ""))
                ok = self.db.delete_user(u)
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error"})
                return

        self._send_json(404, {"status": "error", "message": "Endpoint not found."})


ADMIN_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>Serpent Studio - Yönetim ve Telemetri Konsolu</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg-base: #070B14;
      --bg-surface: #0E1526;
      --bg-surface-elevated: #151F36;
      --bg-card: rgba(14, 21, 38, 0.85);
      --border: rgba(56, 189, 248, 0.15);
      --border-hover: rgba(56, 189, 248, 0.45);
      --text: #F8FAFC;
      --text-muted: #94A3B8;
      --text-dim: #64748B;
      --accent: #38BDF8;
      --accent-hover: #0284C7;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --danger: #F43F5E;
      --danger-hover: #E11D48;
      --success: #10B981;
      --warning: #F59E0B;
      --purple: #8B5CF6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif; }
    body {
      background: var(--bg-base);
      background-image:
        radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 90% 100%, rgba(139, 92, 246, 0.05) 0%, transparent 40%);
      color: var(--text);
      padding: 24px;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }
    .container { max-width: 1280px; margin: 0 auto; }
    
    /* HEADER */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 14px;
      margin-bottom: 20px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }
    .brand-wrap { display: flex; align-items: center; gap: 14px; }
    .brand-icon {
      font-size: 26px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 12px;
      box-shadow: 0 0 16px var(--accent-glow);
    }
    h1 {
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
      letter-spacing: -0.3px;
    }
    .badge {
      font-size: 11px;
      padding: 3px 10px;
      border-radius: 99px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.35);
      font-weight: 600;
      letter-spacing: 0.2px;
    }
    .status-pill {
      font-size: 11px;
      padding: 3px 10px;
      border-radius: 99px;
      background: rgba(16, 185, 129, 0.12);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.3);
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-weight: 600;
    }
    .pulse-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }
    
    .auth-actions { display: flex; align-items: center; gap: 12px; }
    .user-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(255, 255, 255, 0.05);
      padding: 6px 12px;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 13px;
      font-weight: 600;
      color: var(--accent);
    }
    
    /* STATS OVERVIEW CARDS */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.25s ease;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    }
    .stat-card:hover {
      border-color: var(--border-hover);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }
    .stat-info h4 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-muted); margin-bottom: 6px; }
    .stat-number { font-size: 26px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }
    .stat-sub { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
    .stat-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent);
    }
    
    /* TABS */
    .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 12px; }
    .tab-btn {
      background: var(--bg-surface);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
      padding: 10px 18px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tab-btn:hover { color: #fff; border-color: rgba(255, 255, 255, 0.2); }
    .tab-btn.active {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border-color: var(--accent);
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
    }
    .tab-badge {
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 99px;
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }
    .tab-btn.active .tab-badge { background: var(--accent); color: #000; font-weight: 700; }
    
    /* CARDS */
    .card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 22px;
      margin-bottom: 24px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .card-title { font-size: 16px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
    .card-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 3px; }
    
    /* SEARCH & FILTER CONTROLS */
    .search-input-wrap {
      position: relative;
      display: flex;
      align-items: center;
      min-width: 260px;
    }
    .search-input {
      width: 100%;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #fff;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      transition: all 0.2s;
    }
    .search-input:focus { border-color: var(--accent); box-shadow: 0 0 10px rgba(56, 189, 248, 0.2); }
    
    /* FORM STYLES */
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 14px; align-items: center; }
    input, select {
      background: var(--bg-surface);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #fff;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      transition: all 0.2s;
    }
    input:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
    }
    
    /* BUTTONS */
    button.btn {
      background: var(--accent);
      color: #000;
      border: none;
      padding: 9px 16px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      user-select: none;
    }
    button.btn:hover { background: var(--accent-hover); box-shadow: 0 4px 12px var(--accent-glow); transform: translateY(-1px); }
    button.btn:active { transform: translateY(0); }
    button.btn-danger { background: rgba(244, 63, 94, 0.15); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.35); }
    button.btn-danger:hover { background: var(--danger); color: #fff; box-shadow: 0 4px 12px rgba(244, 63, 94, 0.4); }
    button.btn-warning { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.35); }
    button.btn-warning:hover { background: var(--warning); color: #000; }
    button.btn-secondary { background: rgba(255, 255, 255, 0.08); color: var(--text); border: 1px solid rgba(255, 255, 255, 0.12); }
    button.btn-secondary:hover { background: rgba(255, 255, 255, 0.15); }
    button.btn-sm { padding: 5px 10px; font-size: 12px; border-radius: 6px; }
    
    /* PILLS */
    .pill-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.25);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 99px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      user-select: none;
    }
    .pill-btn:hover { background: var(--accent); color: #000; transform: translateY(-1px); }
    
    /* TABLES */
    .table-container { width: 100%; overflow-x: auto; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06); }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    thead tr { background: rgba(15, 23, 42, 0.7); }
    th {
      padding: 12px 14px;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.6px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    tbody tr {
      transition: background 0.15s ease;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    tbody tr:hover { background: rgba(56, 189, 248, 0.04); }
    td {
      padding: 13px 14px;
      font-size: 13px;
      vertical-align: middle;
      color: #E2E8F0;
    }
    
    /* BADGES */
    .role-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      cursor: pointer;
      transition: all 0.2s;
      background: rgba(139, 92, 246, 0.12);
      color: #C084FC;
      padding: 3px 9px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid rgba(139, 92, 246, 0.3);
    }
    .role-badge:hover { background: rgba(139, 92, 246, 0.25); border-color: var(--purple); }
    
    .restriction-pill {
      font-size: 11px;
      padding: 3px 9px;
      border-radius: 99px;
      background: rgba(244, 63, 94, 0.12);
      color: var(--danger);
      border: 1px solid rgba(244, 63, 94, 0.35);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .ok-pill {
      font-size: 11px;
      padding: 3px 9px;
      border-radius: 99px;
      background: rgba(16, 185, 129, 0.12);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.35);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    
    /* MODALS */
    .modal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(3, 7, 18, 0.85);
      backdrop-filter: blur(8px);
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 20px;
    }
    .modal-content {
      background: var(--bg-surface);
      border: 1px solid var(--border-hover);
      padding: 26px;
      border-radius: 16px;
      max-width: 820px;
      width: 100%;
      max-height: 88vh;
      overflow-y: auto;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6);
      animation: modalFadeIn 0.2s ease-out;
    }
    @keyframes modalFadeIn { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }
    
    .panel-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }
    .panel-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      cursor: pointer;
      transition: all 0.2s;
      user-select: none;
    }
    .panel-card:hover { border-color: var(--accent); background: rgba(56, 189, 248, 0.04); }
    .panel-card.active-restricted {
      background: rgba(244, 63, 94, 0.12);
      border-color: rgba(244, 63, 94, 0.5);
    }
    .panel-card input[type="checkbox"] {
      margin-top: 3px;
      cursor: pointer;
      accent-color: var(--danger);
      width: 16px;
      height: 16px;
    }
    .panel-title { font-size: 13px; font-weight: 600; color: #F8FAFC; display: flex; align-items: center; gap: 6px; }
    .panel-desc { font-size: 11px; color: var(--text-muted); margin-top: 4px; line-height: 1.35; }
    
    pre {
      background: #030712;
      padding: 14px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      color: #E2E8F0;
      font-size: 12px;
      line-height: 1.5;
      overflow-x: auto;
      white-space: pre-wrap;
      max-height: 420px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    
    /* TOAST */
    #toastContainer {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .toast {
      background: var(--bg-surface-elevated);
      color: #fff;
      border: 1px solid var(--border);
      padding: 12px 18px;
      border-radius: 10px;
      font-size: 13px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      gap: 10px;
      animation: toastIn 0.25s ease forwards;
    }
    @keyframes toastIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand-wrap">
        <div class="brand-icon">⚛️</div>
        <div>
          <h1>Serpent Studio <span class="badge">Yönetim ve Telemetri</span></h1>
          <div style="margin-top: 4px; display: flex; align-items: center; gap: 8px;">
            <span class="status-pill"><span class="pulse-dot"></span> Canlı Bulut (Render + Neon PostgreSQL)</span>
          </div>
        </div>
      </div>
      <div class="auth-actions">
        <button class="btn btn-secondary btn-sm" onclick="loadAll()" title="Tüm verileri anlık yenile">🔄 Yenile</button>
        <div class="user-chip" id="adminChip">
          <span id="adminName">Giriş Yapılmadı</span>
        </div>
        <button class="btn btn-danger btn-sm" onclick="logoutAdmin()">Çıkış Yap</button>
      </div>
    </header>

    <!-- METRICS OVERVIEW -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-info">
          <h4>Kullanıcılar & Testerlar</h4>
          <div class="stat-number" id="statUsersCount">0</div>
          <div class="stat-sub" id="statUsersSub">0 Aktif · 0 Askıda</div>
        </div>
        <div class="stat-icon">👥</div>
      </div>
      <div class="stat-card">
        <div class="stat-info">
          <h4>Kısıtlamalı Hesaplar</h4>
          <div class="stat-number" id="statRestrictedCount" style="color: var(--warning);">0</div>
          <div class="stat-sub">Panel sınırlandırması olanlar</div>
        </div>
        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.1); color: var(--warning);">🛡️</div>
      </div>
      <div class="stat-card">
        <div class="stat-info">
          <h4>Hata & Çökme Raporları</h4>
          <div class="stat-number" id="statErrorsCount" style="color: var(--danger);">0</div>
          <div class="stat-sub">Tester exception bildirimleri</div>
        </div>
        <div class="stat-icon" style="background: rgba(244, 63, 94, 0.1); color: var(--danger);">🚨</div>
      </div>
      <div class="stat-card">
        <div class="stat-info">
          <h4>Serpent Betikleri</h4>
          <div class="stat-number" id="statScriptsCount" style="color: var(--purple);">0</div>
          <div class="stat-sub">Paylaşılan simülasyon girdileri</div>
        </div>
        <div class="stat-icon" style="background: rgba(139, 92, 246, 0.1); color: var(--purple);">📜</div>
      </div>
    </div>

    <!-- TABS NAVIGATION -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('users', event)">
        👥 Kullanıcı Yönetimi & Testerlar <span class="tab-badge" id="badgeUsers">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('errors', event)">
        🚨 Tester Hata & Çökme Raporları <span class="tab-badge" id="badgeErrors">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('scripts', event)">
        📜 Çalıştırılan Serpent Betikleri <span class="tab-badge" id="badgeScripts">0</span>
      </button>
    </div>

    <!-- USERS TAB -->
    <div id="tab-users">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">➕ Yeni Tester / Kullanıcı Oluştur</div>
            <div class="card-subtitle">Buradan belirleyeceğiniz hesap ve şifre masaüstü uygulamasında anında geçerli olur (Uygulama güncellemesi gerektirmez).</div>
          </div>
        </div>
        
        <div class="form-row">
          <input type="text" id="newUsername" placeholder="Kullanıcı Adı (örn: tester_ali)" style="flex:1; min-width: 160px;">
          <input type="password" id="newPassword" placeholder="İlk Şifre (en az 6 karakter)" style="flex:1; min-width: 160px;">
          <input type="text" id="newDisplayName" placeholder="İsim (örn: Ali Mühendis)" style="flex:1; min-width: 160px;">
          <input type="text" id="newRole" placeholder="Rol / Keyword (örn: tester)" value="tester" style="flex:1; min-width: 150px;">
          <button class="btn" onclick="createUser()">💾 Kullanıcıyı Kaydet</button>
        </div>

        <div style="display: flex; align-items: center; gap: 8px; margin-top: 14px; flex-wrap: wrap;">
          <span style="font-size: 12px; color: var(--text-muted);">Hızlı Rol Seçin:</span>
          <span class="pill-btn" onclick="setRole('tester')">+ Tester</span>
          <span class="pill-btn" onclick="setRole('araştırmacı')">+ Araştırmacı</span>
          <span class="pill-btn" onclick="setRole('öğrenci')">+ Öğrenci</span>
          <span class="pill-btn" onclick="setRole('stajyer')">+ Stajyer</span>
          <span class="pill-btn" onclick="setRole('nükleer-mühendis')">+ Nükleer Mühendis</span>
          <span class="pill-btn" onclick="setRole('proje-ekibi')">+ Proje Ekibi</span>
          <span class="pill-btn" onclick="setRole('misafir')">+ Misafir</span>
          <span class="pill-btn" onclick="setRole('administrator')">+ Yönetici</span>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">📋 Kayıtlı Kullanıcılar & Uzaktan Kısıtlama Denetimi</div>
            <div class="card-subtitle">Kullanıcıların erişebileceği panelleri buradan kısıtlayabilir veya hesaplarını anında askıya alabilirsiniz.</div>
          </div>
          <div class="search-input-wrap">
            <input type="text" class="search-input" id="searchUsers" placeholder="🔍 Kullanıcı veya rol ara..." oninput="filterUsers()">
          </div>
        </div>
        
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Kullanıcı Adı</th>
                <th>İsim</th>
                <th>Rol / Keyword</th>
                <th>Durum</th>
                <th>Panel Kısıtları</th>
                <th>Son Görülme</th>
                <th>İşlemler</th>
              </tr>
            </thead>
            <tbody id="usersTableBody">
              <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Yükleniyor...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ERRORS TAB -->
    <div id="tab-errors" style="display: none;">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">🚨 Tester Hata ve İstisna Bildirimleri</div>
            <div class="card-subtitle">Test esnasında alınan unhandled exception ve çökmeler anlık olarak buraya düşer.</div>
          </div>
          <div class="search-input-wrap">
            <input type="text" class="search-input" id="searchErrors" placeholder="🔍 Hata türü veya kullanıcı ara..." oninput="filterErrors()">
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Zaman</th>
                <th>Tester</th>
                <th>Hata Türü</th>
                <th>Hata Mesajı</th>
                <th>Sekme</th>
                <th>Sürüm</th>
                <th>Detay</th>
              </tr>
            </thead>
            <tbody id="errorsTableBody">
              <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Hata kaydı bulunmuyor.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- SCRIPTS TAB -->
    <div id="tab-scripts" style="display: none;">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">📜 Kullanıcıların Çalıştırdığı Serpent Betikleri</div>
            <div class="card-subtitle">Kullanıcıların izin verdiği paylaşılan modeller ve girdi betikleri.</div>
          </div>
          <div class="search-input-wrap">
            <input type="text" class="search-input" id="searchScripts" placeholder="🔍 Proje veya kullanıcı ara..." oninput="filterScripts()">
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Zaman</th>
                <th>Kullanıcı</th>
                <th>Proje Adı</th>
                <th>Boyut</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody id="scriptsTableBody">
              <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Kayıt yok.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- TOAST CONTAINER -->
  <div id="toastContainer"></div>

  <!-- MODAL: DETAIL (TRACEBACK / SCRIPT) -->
  <div class="modal" id="detailModal">
    <div class="modal-content">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <h3 id="modalTitle" style="color: #fff; font-size: 16px;">Detay</h3>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-sm btn-secondary" onclick="copyDetailModalContent()">📋 Panoya Kopyala</button>
          <button class="btn btn-sm btn-danger" onclick="closeModal()">Kapat</button>
        </div>
      </div>
      <pre id="modalBody"></pre>
    </div>
  </div>

  <!-- MODAL: PANEL RESTRICTIONS -->
  <div class="modal" id="restrictionsModal">
    <div class="modal-content">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
          <h3 style="color: #fff; font-size: 16px;">🛡️ Panel ve Modül Kısıtlamaları</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 2px;">
            Kullanıcı: <strong id="modalRestrictUsername" style="color: var(--accent);"></strong>
          </p>
        </div>
        <button class="btn btn-sm btn-danger" onclick="closeRestrictionsModal()">Kapat</button>
      </div>

      <div style="background: rgba(244,63,94,0.08); border: 1px solid rgba(244,63,94,0.3); border-radius: 10px; padding: 12px 16px; margin: 14px 0; font-size: 13px; color: #FDA4AF; line-height: 1.4;">
        ⚠️ <strong>İşleyiş:</strong> İşaretlediğiniz paneller kullanıcının masaüstü uygulamasında anında devre dışı bırakılır ve gizlenir. Canlı heartbeat (en geç 60 sn) ile uygulama yeniden başlatılmadan devreye girer.
      </div>

      <!-- Quick Preset Buttons -->
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;">
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions([])">🔓 Tümünü Aç</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(ALL_PANEL_IDS)">🛑 Tümünü Kısıtla</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(['materials','assembly','geometry','control_rods','detectors','coefficients','simulation','settings','console'])">📊 Salt Okunur (Sadece Sonuç İnceleme)</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(['settings','console'])">🧪 Standart Tester (Ayarlar & Konsol Kilitli)</button>
      </div>

      <div class="panel-grid" id="panelGridContainer">
        <!-- Rendered dynamically -->
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 14px;">
        <button class="btn btn-secondary" onclick="closeRestrictionsModal()">İptal</button>
        <button class="btn" onclick="saveRestrictions()">💾 Kısıtlamaları Kaydet</button>
      </div>
    </div>
  </div>

  <script>
    // Never persist bearer credentials in browser storage.
    localStorage.removeItem('serpent_admin_token');
    let adminToken = '';
    let currentRestrictUser = '';
    let usersCache = [];
    let errorsCache = [];
    let scriptsCache = [];

    const AVAILABLE_PANELS = [
      { id: 'materials', name: 'Malzeme Editörü', icon: '🧪', desc: 'Malzeme tanımlama kartları, izotop kütüphaneleri ve kompozisyon' },
      { id: 'assembly', name: 'Yakıt Demeti (Assembly)', icon: '📐', desc: 'Pin matrisleri, yakıt çubukları ve demet geometrisi' },
      { id: 'geometry', name: 'Kor (Core) Geometrisi', icon: '🌐', desc: 'Reaktör kor haritası, sınır yüzeyleri ve yerleşim' },
      { id: 'control_rods', name: 'Kontrol Çubukları', icon: '🕹️', desc: 'Kontrol çubuğu grupları, kademeleri ve malzemeleri' },
      { id: 'detectors', name: 'Detektör Ayarları', icon: '📡', desc: 'Hücre/örgü detektör kartları, enerji grupları ve tepkiler' },
      { id: 'coefficients', name: 'Kinetik & Katsayılar', icon: '📊', desc: 'Sıcaklık ve reaktivite katsayıları hesaplama seçenekleri' },
      { id: 'analysis_outputs', name: 'Analiz & Çıktılar', icon: '📈', desc: 'Etkileşimli sonuç grafikleri, PPF ve tükenme analizleri' },
      { id: 'simulation', name: 'Simülasyon Çalıştırıcı', icon: '🚀', desc: 'Serpent sss2 çalıştırıcı ve simülasyon başlatma butonu' },
      { id: 'settings', name: 'Genel Ayarlar', icon: '⚙️', desc: 'Kütüphane dizinleri, çekirdek/OMP sayıları ve dosya yolları' },
      { id: 'plot', name: 'Görselleştirme / Plot', icon: '🗺️', desc: 'Serpent geometri kesit plot alma paneli' },
      { id: 'console', name: 'Komut Konsolu', icon: '💻', desc: 'Alt komut satırı ve doğrudan terminal paneli' },
    ];
    const ALL_PANEL_IDS = AVAILABLE_PANELS.map(p => p.id);

    function showToast(message, type = 'info') {
      const container = document.getElementById('toastContainer');
      if (!container) return;
      const toast = document.createElement('div');
      toast.className = 'toast';
      if (type === 'error') toast.style.borderColor = 'var(--danger)';
      if (type === 'success') toast.style.borderColor = 'var(--success)';
      toast.textContent = message;
      container.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }, 3500);
    }

    function checkAuth() {
      if (adminToken) { loadAll(); return; }
      if (document.getElementById('adminLoginDialog')) return;
      const dialog = document.createElement('dialog');
      dialog.id = 'adminLoginDialog';
      dialog.style.cssText = 'margin:auto;padding:28px;background:var(--bg-surface);color:var(--text);border:1px solid var(--border-hover);border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.8);max-width:380px;width:90%';
      dialog.addEventListener('cancel', event => event.preventDefault());
      const form = document.createElement('form');
      const title = document.createElement('h2');
      title.textContent = '⚛️ Yönetici Girişi';
      title.style.cssText = 'font-size:18px;margin-bottom:16px;color:#fff;text-align:center;';
      const username = document.createElement('input');
      username.placeholder = 'Kullanıcı adı'; username.autocomplete = 'username'; username.required = true;
      username.style.cssText = 'width:100%;margin-bottom:12px;display:block;';
      const password = document.createElement('input');
      password.type = 'password'; password.placeholder = 'Şifre'; password.autocomplete = 'current-password'; password.required = true;
      password.style.cssText = 'width:100%;margin-bottom:14px;display:block;';
      const error = document.createElement('p'); error.setAttribute('role', 'alert');
      error.style.cssText = 'color:var(--danger);font-size:12px;margin-bottom:12px;min-height:16px;text-align:center;';
      const submit = document.createElement('button'); submit.type = 'submit'; submit.className = 'btn'; submit.textContent = 'Giriş Yap';
      submit.style.cssText = 'width:100%;justify-content:center;padding:11px;';
      form.append(title, username, password, error, submit);
      form.addEventListener('submit', event => {
        event.preventDefault(); submit.disabled = true; error.textContent = '';
        fetch('/admin/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:username.value, password:password.value})})
        .then(response => response.json().then(data => {
          if (!response.ok || data.status !== 'ok' || !data.token) throw new Error(data.message || 'Giriş başarısız.');
          adminToken = data.token; password.value = '';
          document.getElementById('adminName').textContent = '👤 ' + data.username;
          dialog.close(); dialog.remove(); loadAll();
          showToast('Hoş geldiniz, ' + data.username + '!', 'success');
        }))
        .catch(err => { error.textContent = err.message || 'Sunucuya bağlanılamadı.'; })
        .finally(() => { submit.disabled = false; });
      });
      dialog.append(form); document.body.append(dialog); dialog.showModal(); username.focus();
    }

    function logoutAdmin() {
      const token = adminToken;
      adminToken = '';
      fetch('/admin/api/logout', {method:'POST', headers:{Authorization:'Bearer ' + token}}).finally(() => location.reload());
    }

    function switchTab(name, ev) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      if (ev && ev.currentTarget) {
        ev.currentTarget.classList.add('active');
      }
      ['users', 'errors', 'scripts'].forEach(t => {
        const el = document.getElementById('tab-' + t);
        if (el) el.style.display = (t === name) ? 'block' : 'none';
      });
      if (name === 'users') loadUsers();
      if (name === 'errors') loadErrors();
      if (name === 'scripts') loadScripts();
    }

    function apiCall(endpoint, method='GET', body=null) {
      const opts = {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + adminToken
        }
      };
      if (body) opts.body = JSON.stringify(body);
      return fetch(endpoint, opts).then(r => {
        if (r.status === 401) { logoutAdmin(); throw new Error("Unauthorized"); }
        return r.json();
      });
    }

    function setRole(roleName) {
      document.getElementById('newRole').value = roleName;
    }

    function textCell(row, value) {
      const cell = document.createElement('td');
      cell.textContent = value == null ? '-' : String(value);
      row.appendChild(cell);
      return cell;
    }

    function actionButton(parent, label, callback, extraClass='') {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'btn btn-sm ' + extraClass;
      button.textContent = label; button.addEventListener('click', callback);
      parent.appendChild(button);
      return button;
    }

    function updateStats() {
      const totalUsers = usersCache.length;
      const activeUsers = usersCache.filter(u => !!u.is_active).length;
      const suspendedUsers = totalUsers - activeUsers;
      const restrictedUsers = usersCache.filter(u => Array.isArray(u.restricted_panels) && u.restricted_panels.length > 0).length;
      
      const elUCount = document.getElementById('statUsersCount');
      if (elUCount) elUCount.textContent = totalUsers;
      const elUSub = document.getElementById('statUsersSub');
      if (elUSub) elUSub.textContent = `${activeUsers} Aktif · ${suspendedUsers} Askıda`;
      const elRCount = document.getElementById('statRestrictedCount');
      if (elRCount) elRCount.textContent = restrictedUsers;
      
      const elBUsers = document.getElementById('badgeUsers');
      if (elBUsers) elBUsers.textContent = totalUsers;
      const elBErrors = document.getElementById('badgeErrors');
      if (elBErrors) elBErrors.textContent = errorsCache.length;
      const elBScripts = document.getElementById('badgeScripts');
      if (elBScripts) elBScripts.textContent = scriptsCache.length;
      
      const elECount = document.getElementById('statErrorsCount');
      if (elECount) elECount.textContent = errorsCache.length;
      const elSCount = document.getElementById('statScriptsCount');
      if (elSCount) elSCount.textContent = scriptsCache.length;
    }

    function loadUsers() {
      apiCall('/admin/api/users').then(data => {
        usersCache = data.users || [];
        updateStats();
        renderUsersTable(usersCache);
      });
    }

    function filterUsers() {
      const query = (document.getElementById('searchUsers').value || '').toLowerCase().trim();
      if (!query) {
        renderUsersTable(usersCache);
        return;
      }
      const filtered = usersCache.filter(u => 
        (u.username && u.username.toLowerCase().includes(query)) ||
        (u.display_name && u.display_name.toLowerCase().includes(query)) ||
        (u.role && u.role.toLowerCase().includes(query))
      );
      renderUsersTable(filtered);
    }

    function renderUsersTable(list) {
      const tbody = document.getElementById('usersTableBody');
      tbody.innerHTML = '';
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">Kayıtlı kullanıcı bulunamadı.</td></tr>';
        return;
      }
      list.forEach(u => {
        const isActive = !!u.is_active;
        const tr = document.createElement('tr');
        const lastSeenStr = u.last_seen ? new Date(u.last_seen * 1000).toLocaleString('tr-TR') : 'Hiç giriş yapmadı';
        const rPanels = Array.isArray(u.restricted_panels) ? u.restricted_panels : [];
        
        textCell(tr, u.username);
        textCell(tr, u.display_name || '-');
        const roleCell = textCell(tr, '');
        actionButton(roleCell, '🏷️ ' + u.role + ' ✏️', () => editUserRole(u.username, u.role), 'btn-secondary');
        const state = textCell(tr, isActive ? 'Aktif' : 'Askıya Alındı');
        state.style.color = isActive ? 'var(--success)' : 'var(--danger)';
        const permissions = textCell(tr, rPanels.length ? rPanels.length + ' Panel Kısıtlı' : 'Tüm Paneller Açık');
        permissions.title = rPanels.join(', ');
        permissions.style.color = rPanels.length ? 'var(--warning)' : 'var(--text-muted)';
        textCell(tr, lastSeenStr);
        const actions = textCell(tr, ''); actions.style.whiteSpace = 'nowrap';
        actionButton(actions, '🛡️ Kısıtla', () => openRestrictionsModal(u.username), 'btn-secondary');
        actionButton(actions, isActive ? '🛑 Askıya Al' : '✅ Aç', () => toggleUser(u.username, !isActive), isActive ? 'btn-danger' : 'btn-secondary');
        actionButton(actions, '🔑 Şifre', () => resetPass(u.username), 'btn-warning');
        actionButton(actions, '🗑️', () => deleteUser(u.username), 'btn-danger');
        tbody.appendChild(tr);
      });
    }

    function createUser() {
      const username = document.getElementById('newUsername').value.trim();
      const password = document.getElementById('newPassword').value;
      const display_name = document.getElementById('newDisplayName').value.trim();
      const role = document.getElementById('newRole').value.trim() || 'tester';
      if (!username || !password) return showToast("Kullanıcı adı ve şifre zorunludur!", "error");

      apiCall('/admin/api/users/create', 'POST', { username, password, display_name, role }).then(res => {
        if (res.status === 'ok') {
          showToast("Kullanıcı oluşturuldu! Tester hemen giriş yapabilir.", "success");
          document.getElementById('newUsername').value = '';
          document.getElementById('newPassword').value = '';
          document.getElementById('newDisplayName').value = '';
          document.getElementById('newRole').value = 'tester';
          loadUsers();
        } else {
          showToast("Hata: " + res.message, "error");
        }
      });
    }

    function editUserRole(username, currentRole) {
      const newRole = prompt(`'${username}' kullanıcısı için yeni rol / keyword giriniz:`, currentRole);
      if (newRole && newRole.trim() && newRole.trim() !== currentRole) {
        apiCall('/admin/api/users/set-role', 'POST', { username, role: newRole.trim() }).then(res => {
          if (res.status === 'ok') {
            showToast("Rol güncellendi: " + newRole.trim(), "success");
            loadUsers();
          } else {
            showToast("Rol güncellenemedi: " + (res.message || 'Bilinmeyen hata'), "error");
          }
        });
      }
    }

    function openRestrictionsModal(username) {
      currentRestrictUser = username;
      document.getElementById('modalRestrictUsername').innerText = username;
      
      const user = usersCache.find(u => u.username === username);
      const activeRestricted = (user && Array.isArray(user.restricted_panels)) ? user.restricted_panels : [];

      const grid = document.getElementById('panelGridContainer');
      grid.innerHTML = '';

      AVAILABLE_PANELS.forEach(p => {
        const isChecked = activeRestricted.includes(p.id);
        const card = document.createElement('label');
        card.className = 'panel-card' + (isChecked ? ' active-restricted' : '');
        card.innerHTML = `
          <input type="checkbox" value="${p.id}" ${isChecked ? 'checked' : ''} onchange="onPanelCheckboxChange(this)">
          <div class="panel-info">
            <div class="panel-title"><span>${p.icon}</span> <span>${p.name}</span></div>
            <div class="panel-desc">${p.desc}</div>
          </div>
        `;
        grid.appendChild(card);
      });

      document.getElementById('restrictionsModal').style.display = 'flex';
    }

    function onPanelCheckboxChange(cb) {
      const card = cb.closest('.panel-card');
      if (cb.checked) {
        card.classList.add('active-restricted');
      } else {
        card.classList.remove('active-restricted');
      }
    }

    function setPresetRestrictions(panelIds) {
      const checkboxes = document.querySelectorAll('#panelGridContainer input[type="checkbox"]');
      checkboxes.forEach(cb => {
        cb.checked = panelIds.includes(cb.value);
        onPanelCheckboxChange(cb);
      });
    }

    function saveRestrictions() {
      if (!currentRestrictUser) return;
      const checkedBoxes = document.querySelectorAll('#panelGridContainer input[type="checkbox"]:checked');
      const selectedPanels = Array.from(checkedBoxes).map(cb => cb.value);

      apiCall('/admin/api/users/set-restrictions', 'POST', {
        username: currentRestrictUser,
        restricted_panels: selectedPanels
      }).then(res => {
        if (res.status === 'ok') {
          closeRestrictionsModal();
          loadUsers();
          showToast(`'${currentRestrictUser}' için ${selectedPanels.length} panel kısıtlandı.`, "success");
        } else {
          showToast("Kısıtlamalar kaydedilemedi: " + (res.message || 'Bilinmeyen hata'), "error");
        }
      });
    }

    function closeRestrictionsModal() {
      document.getElementById('restrictionsModal').style.display = 'none';
      currentRestrictUser = '';
    }

    function toggleUser(username, makeActive) {
      if (!confirm(`'${username}' kullanıcısını ${makeActive ? 'AKTİFLEŞTİRMEK' : 'ASKIYA ALMAK'} istediğinize emin misiniz?`)) return;
      apiCall('/admin/api/users/toggle-status', 'POST', { username, is_active: makeActive }).then(res => {
        showToast(`'${username}' durumu güncellendi.`, "success");
        loadUsers();
      });
    }

    function resetPass(username) {
      const newP = prompt(`'${username}' için yeni şifreyi giriniz (en az 6 karakter):`);
      if (!newP) return;
      apiCall('/admin/api/users/reset-password', 'POST', { username, password: newP }).then(res => {
        if (res.status === 'ok') {
          showToast(`'${username}' şifresi başarıyla yenilendi.`, "success");
        } else {
          showToast("Şifre güncellenemedi. En az 12 karakter kullanın.", "error");
        }
      });
    }

    function deleteUser(username) {
      if (!confirm(`'${username}' kullanıcısını kalıcı olarak silmek istiyor musunuz?`)) return;
      apiCall('/admin/api/users/delete', 'POST', { username }).then(res => {
        showToast(`'${username}' hesabı silindi.`, "info");
        loadUsers();
      });
    }

    function filterErrors() {
      const query = (document.getElementById('searchErrors').value || '').toLowerCase().trim();
      if (!query) {
        renderErrorsTable(errorsCache);
        return;
      }
      const filtered = errorsCache.filter(e => 
        (e.username && e.username.toLowerCase().includes(query)) ||
        (e.exception_type && e.exception_type.toLowerCase().includes(query)) ||
        (e.exception_message && e.exception_message.toLowerCase().includes(query))
      );
      renderErrorsTable(filtered);
    }

    function loadErrors() {
      apiCall('/admin/api/errors').then(data => {
        errorsCache = data.errors || [];
        updateStats();
        renderErrorsTable(errorsCache);
      });
    }

    function renderErrorsTable(list) {
      const tbody = document.getElementById('errorsTableBody');
      tbody.innerHTML = '';
      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">Henüz kaydedilmiş hata yok.</td></tr>';
        return;
      }
      list.forEach(e => {
        const tr = document.createElement('tr');
        const timeStr = new Date(e.timestamp * 1000).toLocaleString('tr-TR');
        textCell(tr, timeStr);
        textCell(tr, e.username);
        textCell(tr, e.exception_type).style.color = 'var(--danger)';
        textCell(tr, String(e.exception_message || '').substring(0, 50) + '...');
        textCell(tr, e.active_tab || '-');
        textCell(tr, e.app_version || '-');
        actionButton(textCell(tr, ''), '🔍 Detay', () => showTraceback(e), 'btn-secondary');
        tbody.appendChild(tr);
      });
    }

    function showTraceback(e) {
      document.getElementById('modalTitle').innerText = `🚨 Hata: ${e.exception_type} (${e.username})`;
      document.getElementById('modalBody').innerText = `Kullanıcı: ${e.username}\nSürüm: ${e.app_version}\nPlatform: ${e.platform}\nAktif Sekme: ${e.active_tab}\nZaman: ${new Date(e.timestamp * 1000).toLocaleString('tr-TR')}\nMesaj: ${e.exception_message}\n\n[TRACEBACK]:\n${e.traceback}\n\n[LOGLAR]:\n${e.recent_logs || '-'}`;
      document.getElementById('detailModal').style.display = 'flex';
    }

    function filterScripts() {
      const query = (document.getElementById('searchScripts').value || '').toLowerCase().trim();
      if (!query) {
        renderScriptsTable(scriptsCache);
        return;
      }
      const filtered = scriptsCache.filter(s => 
        (s.username && s.username.toLowerCase().includes(query)) ||
        (s.project_name && s.project_name.toLowerCase().includes(query))
      );
      renderScriptsTable(filtered);
    }

    function loadScripts() {
      apiCall('/admin/api/scripts').then(data => {
        scriptsCache = data.scripts || [];
        updateStats();
        renderScriptsTable(scriptsCache);
      });
    }

    function renderScriptsTable(list) {
      const tbody = document.getElementById('scriptsTableBody');
      tbody.innerHTML = '';
      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:24px; color:var(--text-muted);">Kaydedilmiş betik yok.</td></tr>';
        return;
      }
      list.forEach(s => {
        const tr = document.createElement('tr');
        const timeStr = new Date(s.timestamp * 1000).toLocaleString('tr-TR');
        textCell(tr, timeStr);
        textCell(tr, s.username);
        textCell(tr, s.project_name || '-');
        textCell(tr, (s.size / 1024).toFixed(1) + ' KB');
        actionButton(textCell(tr, ''), '📄 Betiği Gör', () => viewScript(s.id), 'btn-secondary');
        tbody.appendChild(tr);
      });
    }

    function viewScript(id) {
      apiCall('/admin/api/script/' + id).then(data => {
        document.getElementById('modalTitle').innerText = "📜 Serpent Girdi Betiği";
        document.getElementById('modalBody').innerText = data.content;
        document.getElementById('detailModal').style.display = 'flex';
      });
    }

    function copyDetailModalContent() {
      const text = document.getElementById('modalBody').innerText;
      if (!text) return;
      navigator.clipboard.writeText(text).then(() => {
        showToast("Panoya kopyalandı!", "success");
      }).catch(() => {
        showToast("Kopyalanamadı, lütfen metni seçip kopyalayın.", "error");
      });
    }

    function closeModal() {
      document.getElementById('detailModal').style.display = 'none';
    }

    function loadAll() {
      loadUsers();
      loadErrors();
      loadScripts();
    }

    checkAuth();
  </script>
</body>
</html>
"""


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, db_path: str = DB_PATH) -> http.server.HTTPServer:
    database_url = os.environ.get('SERPENT_DATABASE_URL', '').strip()
    validate_storage_configuration(db_path, database_url)
    db = Database(db_path, database_url=database_url)
    # Every listening server owns its authority. Starting another instance must
    # never replace the database used by an already-running server's handlers.
    handler = type('BoundControlPlaneHandler', (ControlPlaneHandler,), {'db':db})
    server = BoundedHTTPServer((host, port), handler)
    logger.info("Serpent Studio Control Plane running on http://%s:%d (Admin UI: /admin)", host, port)
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Serpent Studio Control Plane & Telemetry Server")
    parser.add_argument("port_positional", nargs="?", type=int, default=None, help="Port number (e.g. 8080)")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT, help="Port number (default: 8080)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--db", default=DB_PATH, help="Path to sqlite database file")
    args = parser.parse_args()

    port = args.port_positional if args.port_positional is not None else args.port
    host = args.host
    db_file = args.db

    server = run_server(host, port, db_file)
    print(f"==================================================================", flush=True)
    print(f"⚛️  Serpent Studio Control Plane Server Started", flush=True)
    print(f"👉  Admin Web Panel: http://localhost:{port}/admin", flush=True)
    print("Admin credentials are supplied by environment configuration.", flush=True)
    print("👉  Storage        : " + ('persistent PostgreSQL' if server.RequestHandlerClass.db._backend.postgres else 'SQLite'), flush=True)
    print(f"==================================================================", flush=True)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", flush=True)
        server.shutdown()
