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
import ipaddress
import json
import logging
import os
import re
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


def _load_server_version() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "VERSION"),
        os.path.join(os.path.dirname(__file__), "VERSION"),
        "/app/VERSION",
        "VERSION",
    ]
    for c in candidates:
        if os.path.isfile(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    ver = f.read().strip()
                    if ver:
                        return ver
            except Exception:
                pass
    return "v1.2.71.58"


CURRENT_SERVER_VERSION = _load_server_version()

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


_DUMMY_SALT = "00" * 16
_DUMMY_HASH = hashlib.pbkdf2_hmac("sha256", b"serpent_dummy_password", bytes.fromhex(_DUMMY_SALT), 100000).hex()


def hash_token(token: str) -> str:
    """Compute stable SHA-256 digest of session token for secure storage at rest."""
    if not token or not isinstance(token, str):
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TelemetryRateLimiter:
    """In-memory sliding window rate limiter to protect telemetry endpoints from spam and DoS."""

    def __init__(self, max_requests: int = 30, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            timestamps = [t for t in self._requests.get(key, []) if now - t < self.window_seconds]
            if len(timestamps) >= self.max_requests:
                self._requests[key] = timestamps
                return True
            timestamps.append(now)
            self._requests[key] = timestamps
            return False

    def reset_for_tests(self) -> None:
        with self._lock:
            self._requests.clear()


TELEMETRY_RATE_LIMITER = TelemetryRateLimiter()


def compute_error_fingerprint(exception_type: str, exception_message: str, traceback_str: str) -> str:
    """Compute a stable hash identifying the unique root failure site for error deduplication."""
    last_frame = ""
    if traceback_str:
        frames = re.findall(r'File "([^"]+)", line (\d+), in (\w+)', traceback_str)
        if frames:
            file_path, line_no, func_name = frames[-1]
            last_frame = f"{os.path.basename(file_path)}:{line_no}:{func_name}"

    clean_msg = re.sub(r'0x[0-9a-fA-F]+', '<hex>', exception_message or "")
    clean_msg = re.sub(r'\b\d+\b', '<num>', clean_msg)[:120]
    key = f"{exception_type}:{last_frame}:{clean_msg}".strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


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
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS announcements (
                    id {identity},
                    message TEXT NOT NULL,
                    target_type TEXT NOT NULL DEFAULT 'all',
                    target_usernames TEXT DEFAULT '[]',
                    created_at {timestamp_type} NOT NULL,
                    created_by TEXT,
                    expires_at {timestamp_type},
                    is_active INTEGER NOT NULL DEFAULT 1
                )
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS announcement_seen (
                    announcement_id BIGINT NOT NULL,
                    username TEXT NOT NULL,
                    seen_at {timestamp_type} NOT NULL,
                    UNIQUE (announcement_id, username)
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

            # Ensure error_reports deduplication columns exist
            if self._backend.postgres:
                cursor.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='error_reports'")
            else:
                cursor.execute("PRAGMA table_info(error_reports)")
            err_cols = [r["name"] for r in cursor.fetchall()]
            if "fingerprint" not in err_cols:
                cursor.execute("ALTER TABLE error_reports ADD COLUMN fingerprint TEXT")
            if "occurrence_count" not in err_cols:
                cursor.execute("ALTER TABLE error_reports ADD COLUMN occurrence_count INTEGER DEFAULT 1")
            if "last_seen" not in err_cols:
                cursor.execute(f"ALTER TABLE error_reports ADD COLUMN last_seen {timestamp_type}")
            if "extra_context" not in err_cols:
                cursor.execute("ALTER TABLE error_reports ADD COLUMN extra_context TEXT DEFAULT '{}'")
            if "affected_users" not in err_cols:
                cursor.execute("ALTER TABLE error_reports ADD COLUMN affected_users TEXT DEFAULT '[]'")
            if "status" not in err_cols:
                cursor.execute("ALTER TABLE error_reports ADD COLUMN status TEXT DEFAULT 'open'")

            # Backfill any existing error_reports rows that have NULL fingerprint or NULL status
            cursor.execute("UPDATE error_reports SET status = 'open' WHERE status IS NULL OR status = ''")
            cursor.execute("SELECT id, exception_type, exception_message, traceback FROM error_reports WHERE fingerprint IS NULL OR fingerprint = ''")
            for nr in cursor.fetchall():
                calc_fp = compute_error_fingerprint(
                    nr["exception_type"] or "",
                    nr["exception_message"] or "",
                    nr["traceback"] or ""
                )
                cursor.execute("UPDATE error_reports SET fingerprint = ? WHERE id = ?", (calc_fp, nr["id"]))

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
                       MAX(s.last_heartbeat) as last_seen,
                       (SELECT s2.client_version FROM sessions s2 WHERE s2.user_id = u.id AND s2.client_version IS NOT NULL AND s2.client_version != '' ORDER BY s2.last_heartbeat DESC LIMIT 1) as client_version,
                       (SELECT e.app_version FROM error_reports e WHERE e.username = u.username AND e.app_version IS NOT NULL AND e.app_version != '' ORDER BY e.timestamp DESC LIMIT 1) as error_version
                FROM users u
                LEFT JOIN sessions s ON u.id = s.user_id
                GROUP BY u.id, u.username, u.role, u.display_name, u.is_active, u.created_at, u.expires_at, u.restricted_panels
                ORDER BY u.created_at DESC
            """)
            users = []
            for r in cur.fetchall():
                d = dict(r)
                if not d.get("client_version"):
                    d["client_version"] = d.get("error_version") or ""
                try:
                    d["restricted_panels"] = json.loads(d.get("restricted_panels") or "[]")
                except Exception:
                    d["restricted_panels"] = []
                users.append(d)
            return users

    def create_session(self, user_id: int, username: str, client_version: str = "", platform: str = "") -> str:
        token = secrets.token_hex(24)
        token_digest = hash_token(token)
        now = time.time()
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sessions (token, user_id, username, client_version, platform, created_at, last_heartbeat, is_revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (token_digest, user_id, username, client_version, platform, now, now))
            conn.commit()
        return token

    def revoke_session(self, token: str) -> None:
        if not token or not isinstance(token, str):
            return
        token_digest = hash_token(token)
        with self._lock, self._get_conn() as conn:
            conn.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ? OR token = ?", (token_digest, token))
            conn.commit()

    def change_user_password(self, token: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Atomically change the authenticated user's password and rotate all sessions."""
        if not token or not isinstance(token, str):
            return False, "Invalid session token."
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return False, "New password must be at least 12 characters."
        token_digest = hash_token(token)
        with self._lock, self._get_conn() as conn:
            if not self._backend.postgres:
                conn.execute("BEGIN IMMEDIATE")
            sql = "SELECT u.*, s.created_at AS session_created FROM users u JOIN sessions s ON s.user_id=u.id WHERE (s.token=? OR s.token=?) AND s.is_revoked=0"
            if self._backend.postgres:
                sql += " FOR UPDATE OF u, s"
            row = conn.execute(sql, (token_digest, token)).fetchone()
            if (not row or not row["is_active"] or (row["expires_at"] and row["expires_at"] < time.time())
                    or time.time() - row["session_created"] > SESSION_MAX_AGE
                    or not verify_password(current_password, row["password_hash"], row["salt"])):
                return False, "Current password verification failed."
            hashed, salt = hash_password(new_password)
            conn.execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (hashed, salt, row["id"]))
            conn.execute("UPDATE sessions SET is_revoked=1 WHERE user_id=?", (row["id"],))
            replacement = secrets.token_hex(24)
            replacement_digest = hash_token(replacement)
            now = time.time()
            conn.execute("INSERT INTO sessions (token,user_id,username,created_at,last_heartbeat,is_revoked) VALUES (?,?,?,?,?,0)", (replacement_digest, row["id"], row["username"], now, now))
            conn.commit()
            return True, replacement

    def verify_and_touch_session(self, token: str, client_version: str = "", platform: str = "") -> Tuple[bool, Optional[Dict[str, Any]]]:
        if not token or not isinstance(token, str):
            return False, None
        token_digest = hash_token(token)
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, u.is_active, u.role, u.expires_at, u.restricted_panels
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE (s.token = ? OR s.token = ?) AND s.is_revoked = 0
            """, (token_digest, token))
            row = cur.fetchone()
            if not row:
                return False, None

            data = dict(row)
            if time.time() - data["created_at"] > SESSION_MAX_AGE:
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ? OR token = ?", (token_digest, token))
                conn.commit()
                return False, None
            if not data.get("is_active"):
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ? OR token = ?", (token_digest, token))
                conn.commit()
                return False, None

            expires_at = data.get("expires_at")
            if expires_at and time.time() > expires_at:
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ? OR token = ?", (token_digest, token))
                conn.commit()
                return False, None

            now = time.time()
            if client_version and platform:
                cur.execute("""
                    UPDATE sessions
                    SET last_heartbeat = ?, client_version = ?, platform = ?
                    WHERE token = ? OR token = ?
                """, (now, client_version, platform, token_digest, token))
            elif client_version:
                cur.execute("""
                    UPDATE sessions
                    SET last_heartbeat = ?, client_version = ?
                    WHERE token = ? OR token = ?
                """, (now, client_version, token_digest, token))
            elif platform:
                cur.execute("""
                    UPDATE sessions
                    SET last_heartbeat = ?, platform = ?
                    WHERE token = ? OR token = ?
                """, (now, platform, token_digest, token))
            else:
                cur.execute("UPDATE sessions SET last_heartbeat = ? WHERE token = ? OR token = ?", (now, token_digest, token))
            conn.commit()
            if client_version:
                data["client_version"] = client_version
            if platform:
                data["platform"] = platform
            return True, data

    def record_error(
        self, username: str, app_version: str, platform: str,
        exception_type: str, exception_message: str, traceback_str: str,
        active_tab: str = "", recent_logs: str = "", extra_context: Optional[Dict[str, Any]] = None,
        occurrence_increment: int = 1
    ) -> int:
        fp = compute_error_fingerprint(exception_type, exception_message, traceback_str)
        now = time.time()
        extra_ctx_str = json.dumps(extra_context or {})
        inc = max(1, int(occurrence_increment or 1))

        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, occurrence_count, username, affected_users FROM error_reports WHERE fingerprint = ? ORDER BY timestamp DESC LIMIT 1", (fp,))
            existing = cur.fetchone()
            if existing:
                row_id = existing['id']
                count = (existing['occurrence_count'] or 1) + inc

                # Parse and accumulate affected users
                raw_users = existing.get('affected_users') if isinstance(existing, dict) else (existing['affected_users'] if 'affected_users' in existing.keys() else None)
                try:
                    users_list = json.loads(raw_users or "[]")
                except Exception:
                    users_list = []
                if not isinstance(users_list, list):
                    users_list = []
                if username and username not in users_list:
                    users_list.append(username)
                users_json = json.dumps(users_list)

                cur.execute("""
                    UPDATE error_reports
                    SET occurrence_count = ?,
                        last_seen = ?,
                        timestamp = ?,
                        recent_logs = ?,
                        active_tab = ?,
                        app_version = ?,
                        extra_context = ?,
                        affected_users = ?,
                        status = 'open'
                    WHERE id = ?
                """, (count, now, now, recent_logs, active_tab, app_version, extra_ctx_str, users_json, row_id))
                conn.commit()
                return row_id

            users_json = json.dumps([username] if username else [])
            sql = """
                INSERT INTO error_reports
                (username, app_version, platform, exception_type, exception_message, traceback, active_tab, recent_logs, timestamp, fingerprint, occurrence_count, last_seen, extra_context, affected_users, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """
            if self._backend.postgres:
                sql += " RETURNING id"
            cur.execute(sql, (
                username, app_version, platform, exception_type, exception_message,
                traceback_str, active_tab, recent_logs, now, fp, inc, now, extra_ctx_str, users_json
            ))
            row_id = cur.fetchone()['id'] if self._backend.postgres else cur.lastrowid
            conn.commit()
            return row_id

    def set_error_status(self, fingerprint: str = "", status: str = "resolved", error_id: Optional[int] = None) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            updated = False
            if fingerprint:
                cur.execute("UPDATE error_reports SET status = ? WHERE fingerprint = ?", (status, fingerprint))
                if cur.rowcount > 0:
                    updated = True

            if error_id is not None:
                cur.execute("UPDATE error_reports SET status = ? WHERE id = ?", (status, error_id))
                if cur.rowcount > 0:
                    updated = True

            # Backfill any error records with NULL/empty fingerprint
            cur.execute("SELECT id, exception_type, exception_message, traceback FROM error_reports WHERE fingerprint IS NULL OR fingerprint = ''")
            null_rows = [dict(r) for r in cur.fetchall()]
            for nr in null_rows:
                calc_fp = compute_error_fingerprint(
                    nr.get("exception_type", "") or "",
                    nr.get("exception_message", "") or "",
                    nr.get("traceback", "") or ""
                )
                cur.execute("UPDATE error_reports SET fingerprint = ? WHERE id = ?", (calc_fp, nr["id"]))
                if fingerprint and calc_fp == fingerprint:
                    cur.execute("UPDATE error_reports SET status = ? WHERE id = ?", (status, nr["id"]))
                    updated = True

            conn.commit()
            return True

    def list_errors(self, limit: int = 200, unique_only: bool = True, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM error_reports ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]

            for r in rows:
                if not r.get("fingerprint"):
                    r["fingerprint"] = compute_error_fingerprint(r.get("exception_type", ""), r.get("exception_message", ""), r.get("traceback", ""))
                if not r.get("occurrence_count"):
                    r["occurrence_count"] = 1
                if not r.get("last_seen"):
                    r["last_seen"] = r.get("timestamp")
                r["first_seen"] = r.get("timestamp")
                if not r.get("status"):
                    r["status"] = "open"

                raw_users = r.get("affected_users")
                try:
                    r["users"] = json.loads(raw_users) if raw_users else ([r["username"]] if r.get("username") else [])
                except Exception:
                    r["users"] = [r["username"]] if r.get("username") else []

                raw_ctx = r.get("extra_context")
                try:
                    r["extra_context_data"] = json.loads(raw_ctx) if isinstance(raw_ctx, str) else (raw_ctx or {})
                except Exception:
                    r["extra_context_data"] = {}

                tb = r.get("traceback", "")
                frames = re.findall(r'File "([^"]+)", line (\d+), in (\w+)', tb)
                if frames:
                    f_name = os.path.basename(frames[-1][0])
                    r["call_site"] = f"{f_name}:{frames[-1][1]} in {frames[-1][2]}()"
                else:
                    r["call_site"] = r.get("active_tab") or "-"

            if unique_only:
                grouped: Dict[str, Dict[str, Any]] = {}
                for r in rows:
                    fp = r["fingerprint"]
                    if fp not in grouped:
                        grouped[fp] = dict(r)
                    else:
                        grouped[fp]["occurrence_count"] = (grouped[fp].get("occurrence_count", 1) or 1) + (r.get("occurrence_count", 1) or 1)
                        if r["timestamp"] > grouped[fp]["timestamp"]:
                            grouped[fp]["last_seen"] = r["timestamp"]
                            grouped[fp]["timestamp"] = r["timestamp"]
                            grouped[fp]["recent_logs"] = r.get("recent_logs")
                            grouped[fp]["app_version"] = r.get("app_version")
                            grouped[fp]["active_tab"] = r.get("active_tab")
                            grouped[fp]["status"] = r.get("status", "open")
                            if r.get("extra_context_data"):
                                grouped[fp]["extra_context_data"] = r["extra_context_data"]
                        if r["timestamp"] < grouped[fp].get("first_seen", float("inf")):
                            grouped[fp]["first_seen"] = r["timestamp"]
                        for u in r.get("users", []):
                            if u and u not in grouped[fp]["users"]:
                                grouped[fp]["users"].append(u)

                res = list(grouped.values())
                if status_filter and status_filter != "all":
                    res = [r for r in res if r.get("status") == status_filter]
                res.sort(key=lambda x: x.get("last_seen", x.get("timestamp", 0)), reverse=True)
                return res

            if status_filter and status_filter != "all":
                rows = [r for r in rows if r.get("status") == status_filter]

            return rows

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

    def user_detail(self, username: str, error_limit: int = 15, script_limit: int = 15) -> Optional[Dict[str, Any]]:
        """Aggregate a single user's row, sessions, recent errors and recent scripts."""
        u = (username or "").strip().lower()
        if not u:
            return None
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.id, u.username, u.role, u.display_name, u.is_active, u.created_at, u.expires_at, u.restricted_panels,
                       MAX(s.last_heartbeat) as last_seen,
                       (SELECT s2.client_version FROM sessions s2 WHERE s2.user_id = u.id AND s2.client_version IS NOT NULL AND s2.client_version != '' ORDER BY s2.last_heartbeat DESC LIMIT 1) as client_version
                FROM users u
                LEFT JOIN sessions s ON u.id = s.user_id
                WHERE u.username = ?
                GROUP BY u.id, u.username, u.role, u.display_name, u.is_active, u.created_at, u.expires_at, u.restricted_panels
            """, (u,))
            row = cur.fetchone()
            if not row:
                return None
            detail: Dict[str, Any] = dict(row)
            try:
                detail["restricted_panels"] = json.loads(detail.get("restricted_panels") or "[]")
            except Exception:
                detail["restricted_panels"] = []

            cur.execute("""
                SELECT client_version, platform, created_at, last_heartbeat, is_revoked
                FROM sessions WHERE user_id = ? ORDER BY last_heartbeat DESC LIMIT 20
            """, (detail["id"],))
            detail["sessions"] = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT id, exception_type, exception_message, active_tab, app_version, timestamp, last_seen, occurrence_count, status
                FROM error_reports WHERE username = ?
                ORDER BY COALESCE(last_seen, timestamp) DESC LIMIT ?
            """, (u, int(error_limit)))
            detail["errors"] = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT id, project_name, LENGTH(script_content) as size, timestamp
                FROM scripts WHERE username = ? ORDER BY timestamp DESC LIMIT ?
            """, (u, int(script_limit)))
            detail["scripts"] = [dict(r) for r in cur.fetchall()]
            return detail

    def create_announcement(
        self, message: str, created_by: str, target_type: str = "all",
        target_usernames: Optional[List[str]] = None,
        expires_at: Optional[float] = None,
    ) -> Tuple[bool, str]:
        msg = (message or "").strip()
        if not msg:
            return False, "Announcement message cannot be empty."
        if len(msg) > 2000:
            return False, "Announcement message is too long (max 2000 characters)."
        ttype = "selected" if str(target_type).strip().lower() == "selected" else "all"
        targets: List[str] = []
        if ttype == "selected":
            seen_names: set = set()
            for name in (target_usernames or []):
                candidate = str(name).strip().lower()
                if candidate and candidate not in seen_names:
                    seen_names.add(candidate)
                    targets.append(candidate)
            if not targets:
                return False, "Select at least one target user for a targeted announcement."
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO announcements (message, target_type, target_usernames, created_at, created_by, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (msg, ttype, json.dumps(targets), time.time(), str(created_by or "admin"), expires_at))
            conn.commit()
        return True, "Announcement published."

    def list_announcements(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id, a.message, a.target_type, a.target_usernames, a.created_at, a.created_by, a.expires_at, a.is_active,
                       (SELECT COUNT(*) FROM announcement_seen s WHERE s.announcement_id = a.id) as seen_count,
                       (SELECT COUNT(*) FROM users u WHERE u.is_active = 1) as total_users
                FROM announcements a ORDER BY a.created_at DESC
            """)
            items: List[Dict[str, Any]] = []
            for r in cur.fetchall():
                d = dict(r)
                try:
                    d["target_usernames"] = json.loads(d.get("target_usernames") or "[]")
                except Exception:
                    d["target_usernames"] = []
                d["target_count"] = len(d["target_usernames"]) if d.get("target_type") == "selected" else (d.get("total_users") or 0)
                d["is_expired"] = bool(d.get("expires_at") and d["expires_at"] <= now)
                d.pop("total_users", None)
                items.append(d)
            return items

    def set_announcement_active(self, announcement_id: Any, is_active: bool) -> bool:
        try:
            aid = int(announcement_id)
        except Exception:
            return False
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE announcements SET is_active = ? WHERE id = ?", (1 if is_active else 0, aid))
            changed = cur.rowcount
            conn.commit()
        return changed > 0

    def pending_announcements(self, username: str) -> List[Dict[str, Any]]:
        """Active, unexpired, unseen announcements targeting this user (oldest first)."""
        u = (username or "").strip().lower()
        if not u:
            return []
        now = time.time()
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id, a.message, a.created_at, a.created_by, a.target_type, a.target_usernames
                FROM announcements a
                WHERE a.is_active = 1
                  AND (a.expires_at IS NULL OR a.expires_at > ?)
                  AND NOT EXISTS (SELECT 1 FROM announcement_seen s WHERE s.announcement_id = a.id AND s.username = ?)
                ORDER BY a.created_at ASC
            """, (now, u))
            pending: List[Dict[str, Any]] = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("target_type") == "selected":
                    try:
                        targets = json.loads(d.get("target_usernames") or "[]")
                    except Exception:
                        targets = []
                    if u not in targets:
                        continue
                pending.append({"id": d["id"], "message": d["message"], "created_at": d["created_at"]})
            return pending

    def mark_announcements_seen(self, username: str, announcement_ids: Any) -> int:
        u = (username or "").strip().lower()
        if not u or not isinstance(announcement_ids, (list, tuple)):
            return 0
        ids: List[int] = []
        for raw in list(announcement_ids)[:50]:
            try:
                ids.append(int(raw))
            except Exception:
                continue
        if not ids:
            return 0
        now = time.time()
        marked = 0
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            for aid in ids:
                cur.execute("SELECT 1 FROM announcement_seen WHERE announcement_id = ? AND username = ?", (aid, u))
                if cur.fetchone():
                    continue
                cur.execute("INSERT INTO announcement_seen (announcement_id, username, seen_at) VALUES (?, ?, ?)", (aid, u, now))
                marked += 1
            conn.commit()
        return marked


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
        peer_ip_str = ""
        is_peer_trusted = False
        if self.client_address and len(self.client_address) > 0:
            try:
                peer_obj = ipaddress.ip_address(str(self.client_address[0]))
                peer_ip_str = str(peer_obj)
                # Loopback (127.0.0.1, ::1) is trusted local reverse proxy (e.g. Nginx, Render proxy)
                is_peer_trusted = peer_obj.is_loopback
            except ValueError:
                peer_ip_str = str(self.client_address[0])

        # Cloudflare / trusted edge headers if peer is trusted proxy
        if is_peer_trusted:
            for header in ("CF-Connecting-IP", "True-Client-IP"):
                val = self.headers.get(header, "").strip()
                if val:
                    try:
                        return str(ipaddress.ip_address(val))
                    except ValueError:
                        pass
            forwarded = self.headers.get("X-Forwarded-For", "")
            if forwarded:
                parts = [p.strip() for p in forwarded.split(",") if p.strip()]
                for p in reversed(parts):
                    try:
                        return str(ipaddress.ip_address(p))
                    except ValueError:
                        continue

        if peer_ip_str:
            return peer_ip_str
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
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none';")
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
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';")
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
            self._send_json(200, {
                "status": "ok",
                "service": "SerpentStudio-ControlPlane",
                "version": CURRENT_SERVER_VERSION,
                "latest_client_version": CURRENT_SERVER_VERSION,
                "time": time.time(),
            })
            return

        if path in ("/v1/version", "/api/v1/version"):
            self._send_json(200, {
                "status": "ok",
                "server_version": CURRENT_SERVER_VERSION,
                "latest_client_version": CURRENT_SERVER_VERSION,
                "minimum_client_version": "v1.2.0.0",
                "time": time.time(),
            })
            return

        if path == "/admin":
            html = ADMIN_DASHBOARD_HTML.replace("__CURRENT_SERVER_VERSION__", CURRENT_SERVER_VERSION)
            self._send_html(200, html)
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
                query_params = urllib.parse.parse_qs(parsed.query)
                unique_param = query_params.get("unique", ["1"])[0]
                unique_mode = unique_param not in ("0", "false")
                status_filter = query_params.get("status", [None])[0]
                errors = self.db.list_errors(unique_only=unique_mode, status_filter=status_filter)
                self._send_json(200, {"status": "ok", "errors": errors, "unique_mode": unique_mode})
                return

            if path == "/admin/api/scripts":
                scripts = self.db.list_scripts()
                self._send_json(200, {"status": "ok", "scripts": scripts})
                return

            if path == "/admin/api/users/detail":
                query_params = urllib.parse.parse_qs(parsed.query)
                target_user = (query_params.get("username", [""])[0] or "").strip().lower()
                detail = self.db.user_detail(target_user) if target_user else None
                if not detail:
                    self._send_json(404, {"status": "error", "message": "User not found."})
                    return
                self._send_json(200, {"status": "ok", "detail": detail})
                return

            if path == "/admin/api/announcements":
                self._send_json(200, {"status": "ok", "announcements": self.db.list_announcements()})
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
            valid_pw = False
            if user:
                valid_pw = verify_password(password, user["password_hash"], user["salt"])
            else:
                verify_password(password, _DUMMY_HASH, _DUMMY_SALT)

            if not user or not valid_pw:
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
            client_version = str(body.get("client_version") or "").strip()
            platform = str(body.get("platform") or "").strip()
            valid, session_data = self.db.verify_and_touch_session(token, client_version=client_version, platform=platform)
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

            # Acknowledgements for announcements shown in a previous cycle.
            seen_ids = body.get("seen_announcement_ids")
            if isinstance(seen_ids, list) and seen_ids:
                try:
                    self.db.mark_announcements_seen(session_data["username"], seen_ids)
                except Exception:
                    pass

            self._send_json(200, {
                "status": "ok",
                "account_status": "active",
                "username": session_data["username"],
                "role": session_data.get("role", "tester"),
                "restricted_panels": restricted_panels,
                "announcements": self.db.pending_announcements(session_data["username"]),
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
            token_to_revoke = self._get_bearer_token() or str(body.get("token", "")).strip()
            if token_to_revoke:
                self.db.revoke_session(token_to_revoke)
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

            if TELEMETRY_RATE_LIMITER.is_rate_limited(username):
                self._send_json(429, {"status": "error", "message": "Telemetry rate limit exceeded. Please slow down."})
                return

            client_count = int(body.get("client_occurrence_count", 1) or 1)
            rep_id = self.db.record_error(
                username=username,
                app_version=str(body.get("app_version", "")),
                platform=str(body.get("platform", "")),
                exception_type=str(body.get("exception_type", "UnknownError")),
                exception_message=str(body.get("exception_message", "")),
                traceback_str=str(body.get("traceback", "")),
                active_tab=str(body.get("active_tab", "")),
                recent_logs=str(body.get("recent_logs", "")),
                extra_context=body.get("extra_context"),
                occurrence_increment=client_count,
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

            if TELEMETRY_RATE_LIMITER.is_rate_limited(username):
                self._send_json(429, {"status": "error", "message": "Telemetry rate limit exceeded. Please slow down."})
                return

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
            valid_pw = False
            if user:
                valid_pw = verify_password(p, user["password_hash"], user["salt"])
            else:
                verify_password(p, _DUMMY_HASH, _DUMMY_SALT)

            if (user and user["role"] == "administrator" and user["is_active"]
                    and (not user["expires_at"] or user["expires_at"] > time.time())
                    and valid_pw):
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

            if path == "/admin/api/errors/status":
                fp = str(body.get("fingerprint", "")).strip()
                err_id = body.get("id")
                try:
                    err_id = int(err_id) if err_id is not None else None
                except Exception:
                    err_id = None
                new_status = str(body.get("status", "resolved")).strip().lower()
                if not fp and err_id is None:
                    self._send_json(400, {"status": "error", "message": "Missing fingerprint or id."})
                    return
                if new_status not in ("open", "resolved", "ignored"):
                    self._send_json(400, {"status": "error", "message": "Invalid status. Must be open, resolved, or ignored."})
                    return
                ok = self.db.set_error_status(fingerprint=fp, status=new_status, error_id=err_id)
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error", "status": new_status, "fingerprint": fp, "id": err_id})
                return

            if path == "/admin/api/announcements/create":
                usernames = body.get("usernames", [])
                if not isinstance(usernames, list):
                    usernames = []
                expires_at = None
                raw_hours = body.get("expires_in_hours")
                if raw_hours not in (None, "", "0", 0):
                    try:
                        hours = float(raw_hours)
                        if hours > 0:
                            expires_at = time.time() + hours * 3600.0
                    except Exception:
                        expires_at = None
                ok, msg = self.db.create_announcement(
                    message=str(body.get("message", "")),
                    created_by=str(session_data.get("username", "admin")),
                    target_type=str(body.get("target_type", "all")),
                    target_usernames=usernames,
                    expires_at=expires_at,
                )
                self._send_json(200 if ok else 400, {"status": "ok" if ok else "error", "message": msg})
                return

            if path == "/admin/api/announcements/toggle":
                ok = self.db.set_announcement_active(body.get("id"), bool(body.get("is_active", True)))
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
      color-scheme: light;
      /* Azure Glass Sky — Splash Identity (#D5EBFB → #9CC6EE crystal glass) */
      --bg-deep: #D5EBFB;
      --bg-base: #CFE7F9;
      --bg-surface: rgba(255, 255, 255, 0.60);
      --bg-surface-elevated: rgba(255, 255, 255, 0.78);
      --bg-surface-card: rgba(255, 255, 255, 0.58);
      --bg-input: rgba(255, 255, 255, 0.88);
      --surface-hover: rgba(2, 132, 199, 0.08);
      
      /* Sapphire Hairline Borders (Crystal Edge, #0284C7 family) */
      --border-stone-faint: rgba(2, 132, 199, 0.08);
      --border-stone: rgba(2, 132, 199, 0.16);
      --border-stone-hover: rgba(2, 132, 199, 0.32);
      
      /* Navy Enamel Typography (Splash logo family) */
      --text-main: #0A3A66;
      --text-soft: #23527C;
      --text-muted: #456F94;
      --text-dim: #7396B4;
      
      /* Sapphire Action Spectrum (Splash buttons #0284C7 → #0EA5E9) */
      --sapphire: #0284C7;
      --sapphire-deep: #0369A1;
      --sapphire-light: #0EA5E9;
      
      /* Alpine Health / Success (light-glass tuned) */
      --pine: #059669;
      --pine-deep: #047857;
      --pine-light: #047857;
      --pine-subtle: rgba(5, 150, 105, 0.10);
      --pine-border: rgba(5, 150, 105, 0.30);
      
      /* Glacial Stream / Telemetry (Sapphire family) */
      --stream: #0284C7;
      --stream-light: #0369A1;
      --stream-subtle: rgba(2, 132, 199, 0.10);
      --stream-border: rgba(2, 132, 199, 0.30);
      
      /* Ochre (Warnings, Restricted, light-glass tuned) */
      --ochre: #D97706;
      --ochre-light: #B45309;
      --ochre-subtle: rgba(217, 119, 6, 0.12);
      --ochre-border: rgba(217, 119, 6, 0.34);
      
      /* Terracotta (Exceptions, Danger, light-glass tuned) */
      --terracotta: #DC2626;
      --terracotta-dark: #B91C1C;
      --terracotta-subtle: rgba(220, 38, 38, 0.10);
      --terracotta-border: rgba(220, 38, 38, 0.30);
      
      /* Daylight Soft Shadows */
      --shadow-sm: 0 2px 8px rgba(10, 58, 102, 0.08);
      --shadow-md: 0 8px 24px rgba(10, 58, 102, 0.12);
      --shadow-lg: 0 16px 40px rgba(10, 58, 102, 0.18);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif; }
    body {
      background-color: var(--bg-deep);
      background-image:
        radial-gradient(ellipse 90% 45% at 50% -5%, rgba(255, 255, 255, 0.55), transparent 70%),
        radial-gradient(ellipse 60% 35% at 95% 100%, rgba(2, 132, 199, 0.10), transparent 60%),
        linear-gradient(160deg, #D5EBFB 0%, #B8DAF4 35%, #9CC6EE 75%, #C4E2F8 100%);
      background-attachment: fixed;
      color: var(--text-main);
      padding: 24px 20px 48px;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }
    #topoCanvas {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 0;
      pointer-events: none;
    }
    .container { max-width: 1320px; margin: 0 auto; position: relative; z-index: 1; }
    
    /* HEADER: Observatory & Command Bar */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: var(--bg-surface-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-stone);
      border-radius: 14px;
      margin-bottom: 22px;
      box-shadow: var(--shadow-md);
      position: relative;
      overflow: hidden;
    }
    header::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(2, 132, 199, 0.45), rgba(56, 189, 248, 0.35), transparent);
    }
    .brand-wrap { display: flex; align-items: center; gap: 14px; }
    .brand-icon {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(2, 132, 199, 0.14), rgba(56, 189, 248, 0.10));
      border: 1px solid var(--border-stone-hover);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
      flex-shrink: 0;
    }
    h1 {
      font-size: 19px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 10px;
      letter-spacing: -0.2px;
    }
    .badge {
      font-size: 11px;
      padding: 3px 10px;
      border-radius: 99px;
      background: var(--stream-subtle);
      color: var(--stream-light);
      border: 1px solid var(--stream-border);
      font-weight: 600;
      letter-spacing: 0.3px;
    }
    .status-pill {
      font-size: 11.5px;
      padding: 3px 10px;
      border-radius: 99px;
      background: var(--pine-subtle);
      color: var(--pine-light);
      border: 1px solid var(--pine-border);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
    }
    .pulse-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--pine-light);
      box-shadow: 0 0 8px rgba(5, 150, 105, 0.45);
      animation: pulse 2.5s infinite;
    }
    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.35; transform: scale(0.85); }
      100% { opacity: 1; transform: scale(1); }
    }
    
    .auth-actions { display: flex; align-items: center; gap: 10px; }
    .user-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-surface-elevated);
      padding: 6px 13px;
      border-radius: 8px;
      border: 1px solid var(--border-stone);
      font-size: 13px;
      font-weight: 500;
      color: var(--sapphire-deep);
    }
    
    /* STATS OVERVIEW CARDS: Geological Specimen Boxes */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--bg-surface-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-stone);
      border-radius: 14px;
      padding: 20px 22px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.25s ease;
      box-shadow: var(--shadow-sm);
      position: relative;
      overflow: hidden;
    }
    .stat-card:hover {
      border-color: var(--border-stone-hover);
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
    .stat-card::after {
      content: '';
      position: absolute;
      bottom: 0; left: 0; right: 0; height: 2px;
      background: transparent;
      transition: background 0.25s ease;
    }
    .stat-card.card-pine:hover::after { background: var(--pine); }
    .stat-card.card-ochre:hover::after { background: var(--ochre-light); }
    .stat-card.card-terracotta:hover::after { background: var(--terracotta); }
    .stat-card.card-glacial:hover::after { background: var(--stream-light); }
    
    .stat-info h4 {
      font-size: 11.5px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-muted);
      margin-bottom: 6px;
      font-weight: 600;
    }
    .stat-number {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.5px;
      line-height: 1.1;
    }
    .stat-sub {
      font-size: 11.5px;
      color: var(--text-dim);
      margin-top: 6px;
      font-weight: 400;
    }
    .stat-icon {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      border: 1px solid transparent;
    }
    .stat-icon-pine {
      background: var(--pine-subtle);
      color: var(--pine-light);
      border-color: var(--pine-border);
    }
    .stat-icon-ochre {
      background: var(--ochre-subtle);
      color: var(--ochre-light);
      border-color: var(--ochre-border);
    }
    .stat-icon-terracotta {
      background: var(--terracotta-subtle);
      color: var(--terracotta);
      border-color: var(--terracotta-border);
    }
    .stat-icon-glacial {
      background: var(--stream-subtle);
      color: var(--stream-light);
      border-color: var(--stream-border);
    }
    
    /* TABS: Field Log Indices */
    .tabs {
      display: flex;
      gap: 10px;
      margin-bottom: 22px;
      border-bottom: 1px solid var(--border-stone);
      padding-bottom: 12px;
    }
    .tab-btn {
      background: var(--bg-surface);
      border: 1px solid var(--border-stone);
      color: var(--text-muted);
      padding: 10px 18px;
      border-radius: 9px;
      cursor: pointer;
      font-weight: 500;
      font-size: 13px;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 8px;
      user-select: none;
    }
    .tab-btn:hover {
      color: var(--text-main);
      border-color: var(--border-stone-hover);
      background: var(--bg-surface-elevated);
    }
    .tab-btn.active {
      background: rgba(2, 132, 199, 0.12);
      color: var(--sapphire-deep);
      border-color: rgba(2, 132, 199, 0.35);
      font-weight: 600;
    }
    .tab-badge {
      font-size: 11px;
      padding: 1px 7px;
      border-radius: 99px;
      background: rgba(2, 132, 199, 0.10);
      color: var(--text-soft);
      font-weight: 600;
      transition: all 0.2s;
    }
    .tab-btn.active .tab-badge {
      background: var(--sapphire);
      color: #FFFFFF;
      font-weight: 700;
    }
    
    /* CARDS: Granite Tablet */
    .card {
      background: var(--bg-surface-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-stone);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
      letter-spacing: -0.2px;
    }
    .card-subtitle {
      font-size: 12.5px;
      color: var(--text-muted);
      margin-top: 4px;
      line-height: 1.4;
    }
    
    /* SEARCH & FILTER CONTROLS */
    .search-input-wrap {
      position: relative;
      display: flex;
      align-items: center;
      min-width: 270px;
    }
    .search-input {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border-stone);
      color: var(--text-main);
      padding: 8px 14px 8px 34px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      transition: all 0.2s ease;
    }
    .search-input:focus {
      border-color: var(--sapphire);
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.16);
    }
    .search-icon-svg {
      position: absolute;
      left: 11px;
      pointer-events: none;
      color: var(--text-dim);
    }
    
    /* FORMS & INPUTS: Deep Mineral Fields */
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 14px; align-items: center; }
    input, select {
      background: var(--bg-input);
      border: 1px solid var(--border-stone);
      color: var(--text-main);
      padding: 10px 14px;
      border-radius: 9px;
      font-size: 13px;
      outline: none;
      transition: all 0.2s ease;
    }
    input::placeholder { color: var(--text-dim); }
    textarea {
      background: var(--bg-input);
      border: 1px solid var(--border-stone);
      color: var(--text-main);
      padding: 10px 14px;
      border-radius: 9px;
      font-size: 13px;
      font-family: inherit;
      outline: none;
      transition: all 0.2s ease;
      width: 100%;
      resize: vertical;
      box-sizing: border-box;
    }
    textarea::placeholder { color: var(--text-dim); }
    textarea:focus {
      border-color: var(--sapphire);
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.16);
    }
    
    /* Hypsometric Version Distribution Bars */
    .vbar-row { display: flex; align-items: center; gap: 10px; }
    .vbar-label { font-size: 12px; font-weight: 700; font-family: monospace; color: var(--text-main); min-width: 92px; }
    .vbar-track { flex: 1; height: 10px; border-radius: 99px; background: rgba(2, 132, 199, 0.08); overflow: hidden; }
    .vbar-fill { height: 100%; border-radius: 99px; transition: width 0.4s ease; }
    .vbar-count { font-size: 12px; font-weight: 600; color: var(--text-soft); min-width: 72px; text-align: right; }
    input:focus, select:focus {
      border-color: var(--sapphire);
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.16);
    }
    
    /* BUTTONS: Tactile Natural Controls */
    button.btn {
      background: linear-gradient(135deg, var(--sapphire), var(--sapphire-light));
      color: #FFFFFF;
      border: none;
      padding: 9px 16px;
      border-radius: 9px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      user-select: none;
      box-shadow: 0 2px 6px rgba(2, 132, 199, 0.28);
    }
    button.btn:hover {
      background: linear-gradient(135deg, var(--sapphire-deep), var(--sapphire));
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
      transform: translateY(-1px);
    }
    button.btn:active { transform: translateY(0); }
    
    button.btn-secondary {
      background: var(--bg-surface-elevated);
      color: var(--text-soft);
      border: 1px solid var(--border-stone);
      box-shadow: none;
    }
    button.btn-secondary:hover {
      background: var(--bg-surface-elevated);
      border-color: var(--border-stone-hover);
      color: var(--text-main);
    }
    
    button.btn-secondary.active {
      background: rgba(2, 132, 199, 0.14);
      color: var(--sapphire-deep);
      font-weight: 600;
    }
    
    button.btn-danger {
      background: var(--terracotta-subtle);
      color: var(--terracotta);
      border: 1px solid var(--terracotta-border);
      box-shadow: none;
    }
    button.btn-danger:hover {
      background: var(--terracotta);
      color: #fff;
      box-shadow: 0 4px 12px rgba(220, 38, 38, 0.32);
    }
    
    button.btn-warning {
      background: var(--ochre-subtle);
      color: var(--ochre-light);
      border: 1px solid var(--ochre-border);
      box-shadow: none;
    }
    button.btn-warning:hover {
      background: #D97706;
      color: #FFFFFF;
      box-shadow: 0 4px 12px rgba(217, 119, 6, 0.32);
    }
    
    button.btn-success {
      background: var(--pine-subtle);
      color: var(--pine-light);
      border: 1px solid var(--pine-border);
      box-shadow: none;
    }
    button.btn-success:hover {
      background: var(--pine);
      color: #FFFFFF;
    }
    
    button.btn-sm {
      padding: 5px 11px;
      font-size: 12px;
      border-radius: 7px;
    }
    
    /* SPECIMEN PILLS */
    .pill-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-stone);
      color: var(--text-soft);
      padding: 4px 11px;
      border-radius: 99px;
      font-size: 11.5px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      user-select: none;
    }
    .pill-btn:hover {
      background: rgba(2, 132, 199, 0.10);
      border-color: rgba(2, 132, 199, 0.32);
      color: var(--sapphire-deep);
      transform: translateY(-1px);
    }
    
    /* TABLES: Precision Geological Log */
    .table-container {
      width: 100%;
      overflow-x: auto;
      border-radius: 10px;
      border: 1px solid var(--border-stone);
      background: var(--bg-surface);
    }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    thead tr {
      background: var(--bg-surface-elevated);
      border-bottom: 1px solid var(--border-stone);
    }
    th {
      padding: 12px 16px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.7px;
    }
    tbody tr {
      transition: background 0.15s ease;
      border-bottom: 1px solid var(--border-stone-faint);
    }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: rgba(2, 132, 199, 0.045); }
    td {
      padding: 13px 16px;
      font-size: 13px;
      vertical-align: middle;
      color: var(--text-soft);
    }
    
    /* BADGES */
    .role-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      cursor: pointer;
      transition: all 0.2s;
      background: var(--stream-subtle);
      color: var(--stream-light);
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      border: 1px solid var(--stream-border);
    }
    .role-badge:hover {
      background: rgba(2, 132, 199, 0.16);
      border-color: #0EA5E9;
    }
    
    /* MODALS: Basalt Monolith Dialogs */
    .modal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(10, 58, 102, 0.32);
      backdrop-filter: blur(8px);
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 20px;
    }
    .modal-content {
      background: rgba(249, 252, 255, 0.96);
      border: 1px solid var(--border-stone-hover);
      padding: 26px;
      border-radius: 16px;
      max-width: 820px;
      width: 100%;
      max-height: 88vh;
      overflow-y: auto;
      box-shadow: var(--shadow-lg);
      animation: modalFadeIn 0.2s ease-out;
      position: relative;
    }
    dialog::backdrop {
      background: rgba(10, 58, 102, 0.28);
      backdrop-filter: blur(6px);
    }
    @keyframes modalFadeIn {
      from { opacity: 0; transform: scale(0.98); }
      to { opacity: 1; transform: scale(1); }
    }
    
    .panel-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }
    .panel-card {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-stone);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      user-select: none;
    }
    .panel-card:hover {
      border-color: var(--sapphire);
      background: rgba(2, 132, 199, 0.06);
    }
    .panel-card.active-restricted {
      background: var(--terracotta-subtle);
      border-color: var(--terracotta-border);
    }
    .panel-card input[type="checkbox"] {
      margin-top: 3px;
      cursor: pointer;
      accent-color: var(--terracotta);
      width: 16px;
      height: 16px;
    }
    .panel-title { font-size: 13px; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 6px; }
    .panel-desc { font-size: 11.5px; color: var(--text-muted); margin-top: 4px; line-height: 1.35; }
    
    pre {
      background: rgba(2, 132, 199, 0.06);
      padding: 16px;
      border: 1px solid var(--border-stone);
      border-radius: 10px;
      color: var(--text-soft);
      font-size: 12px;
      line-height: 1.55;
      overflow-x: auto;
      white-space: pre-wrap;
      max-height: 440px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    
    /* TOAST: Natural Stone Notification */
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
      color: var(--text-main);
      border: 1px solid var(--border-stone-hover);
      padding: 12px 18px;
      border-radius: 10px;
      font-size: 13px;
      box-shadow: var(--shadow-lg);
      display: flex;
      align-items: center;
      gap: 10px;
      animation: toastIn 0.25s ease forwards;
    }
    @keyframes toastIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  </style>
</head>
<body>
  <canvas id="topoCanvas"></canvas>
  <div class="container">
    <header>
      <div class="brand-wrap">
        <div class="brand-icon" title="Serpent Studio Topografik Çekirdek">
          <svg width="26" height="26" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="14" cy="14" rx="12" ry="6" stroke="#0284C7" stroke-width="1.3" transform="rotate(-25 14 14)" stroke-dasharray="2 1"/>
            <ellipse cx="14" cy="14" rx="12" ry="6" stroke="#38BDF8" stroke-width="1.3" transform="rotate(25 14 14)"/>
            <circle cx="14" cy="14" r="3.2" fill="#0A3A66"/>
            <circle cx="14" cy="14" r="6" stroke="rgba(2, 132, 199, 0.35)" stroke-width="1"/>
          </svg>
        </div>
        <div>
          <h1>Serpent Studio <span class="badge">Yönetim ve Telemetri</span></h1>
          <div style="margin-top: 4px; display: flex; align-items: center; gap: 8px;">
            <span class="status-pill"><span class="pulse-dot"></span> Canlı Bulut (Render + Neon PostgreSQL)</span>
            <span class="badge" style="background: rgba(2, 132, 199, 0.10); color: #0369A1; border: 1px solid rgba(2, 132, 199, 0.30);">__CURRENT_SERVER_VERSION__</span>
          </div>
        </div>
      </div>
      <div class="auth-actions">
        <button class="btn btn-secondary btn-sm" onclick="loadAll()" title="Tüm verileri anlık yenile">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
          Yenile
        </button>
        <div class="user-chip" id="adminChip">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <span id="adminName">Giriş Yapılmadı</span>
        </div>
        <button class="btn btn-danger btn-sm" onclick="logoutAdmin()">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
          Çıkış Yap
        </button>
      </div>
    </header>

    <!-- METRICS OVERVIEW -->
    <div class="stats-grid">
      <div class="stat-card card-pine">
        <div class="stat-info">
          <h4>Kullanıcılar & Testerlar</h4>
          <div class="stat-number" id="statUsersCount">0</div>
          <div class="stat-sub" id="statUsersSub">0 Aktif · 0 Askıda</div>
        </div>
        <div class="stat-icon stat-icon-pine" title="Kullanıcı Havuzu">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
      </div>
      <div class="stat-card card-ochre">
        <div class="stat-info">
          <h4>Kısıtlamalı Hesaplar</h4>
          <div class="stat-number" id="statRestrictedCount" style="color: var(--ochre-light);">0</div>
          <div class="stat-sub">Panel sınırlandırması olanlar</div>
        </div>
        <div class="stat-icon stat-icon-ochre" title="Kısıtlı Hesaplar">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
      </div>
      <div class="stat-card card-terracotta">
        <div class="stat-info">
          <h4>Hata & Çökme Raporları</h4>
          <div class="stat-number" id="statErrorsCount" style="color: var(--terracotta);">0</div>
          <div class="stat-sub">Tester exception bildirimleri</div>
        </div>
        <div class="stat-icon stat-icon-terracotta" title="Telemetri İstisnaları">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
      </div>
      <div class="stat-card card-glacial">
        <div class="stat-info">
          <h4>Serpent Betikleri</h4>
          <div class="stat-number" id="statScriptsCount" style="color: var(--stream-light);">0</div>
          <div class="stat-sub">Paylaşılan simülasyon modelleri</div>
        </div>
        <div class="stat-icon stat-icon-glacial" title="Kayıtlı Serpent Girdileri">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        </div>
      </div>
    </div>

    <!-- VERSION DISTRIBUTION CARD -->
    <div class="card" style="margin-bottom: 18px;">
      <div class="card-header" style="margin-bottom: 0;">
        <div>
          <div class="card-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            İstemci Sürüm Dağılımı
          </div>
          <div class="card-subtitle">Testerların son bildirdiği uygulama sürümleri; güncelleme adaptasyonunu tek bakışta gösterir.</div>
        </div>
        <span class="badge" id="versionSummaryBadge" style="background: rgba(2, 132, 199, 0.10); color: #0369A1; border: 1px solid rgba(2, 132, 199, 0.30);">-</span>
      </div>
      <div id="versionBars" style="display: flex; flex-direction: column; gap: 8px; margin-top: 14px;"></div>
    </div>

    <!-- TABS NAVIGATION -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('users', event)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Kullanıcı Yönetimi & Testerlar <span class="tab-badge" id="badgeUsers">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('errors', event)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Tester Hata & Çökme Raporları <span class="tab-badge" id="badgeErrors">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('scripts', event)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        Çalıştırılan Serpent Betikleri <span class="tab-badge" id="badgeScripts">0</span>
      </button>
      <button class="tab-btn" onclick="switchTab('announcements', event)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/></svg>
        Duyurular & İletişim <span class="tab-badge" id="badgeAnnouncements">0</span>
      </button>
    </div>

    <!-- USERS TAB -->
    <div id="tab-users">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Yeni Tester / Kullanıcı Oluştur
            </div>
            <div class="card-subtitle">Belirleyeceğiniz hesap ve şifre masaüstü uygulamasında anında geçerli olur (uygulama güncellemesi gerektirmez).</div>
          </div>
        </div>
        
        <div class="form-row">
          <input type="text" id="newUsername" placeholder="Kullanıcı Adı (örn: tester_ali)" style="flex:1; min-width: 160px;">
          <input type="password" id="newPassword" placeholder="İlk Şifre (en az 6 karakter)" style="flex:1; min-width: 160px;">
          <input type="text" id="newDisplayName" placeholder="İsim (örn: Ali Mühendis)" style="flex:1; min-width: 160px;">
          <input type="text" id="newRole" placeholder="Rol / Keyword (örn: tester)" value="tester" style="flex:1; min-width: 150px;">
          <button class="btn" onclick="createUser()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            Kullanıcıyı Kaydet
          </button>
        </div>

        <div style="display: flex; align-items: center; gap: 8px; margin-top: 14px; flex-wrap: wrap;">
          <span style="font-size: 12px; color: var(--text-muted); font-weight: 500;">Hızlı Rol Şablonları:</span>
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
            <div class="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Kayıtlı Kullanıcılar & Uzaktan Kısıtlama Denetimi
            </div>
            <div class="card-subtitle">Kullanıcıların erişebileceği panelleri kısıtlayabilir veya hesaplarını anında askıya alabilirsiniz.</div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <div class="search-input-wrap">
              <svg class="search-icon-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" class="search-input" id="searchUsers" placeholder="Kullanıcı veya rol ara..." oninput="filterUsers()">
            </div>
            <button class="btn btn-secondary btn-sm" onclick="exportUsers('csv')" title="Listelenen kullanıcıları CSV olarak indir">CSV</button>
            <button class="btn btn-secondary btn-sm" onclick="exportUsers('json')" title="Listelenen kullanıcıları JSON olarak indir">JSON</button>
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
                <th>Son Sürüm</th>
                <th>Panel Kısıtları</th>
                <th>Son Görülme</th>
                <th>İşlemler</th>
              </tr>
            </thead>
            <tbody id="usersTableBody">
              <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">Yükleniyor...</td></tr>
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
            <div class="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Tester Hata ve İstisna Bildirimleri
            </div>
            <div class="card-subtitle">Test esnasında alınan unhandled exception ve çökmeler anlık olarak buraya düşer.</div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <div class="search-input-wrap">
              <svg class="search-icon-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" class="search-input" id="searchErrors" placeholder="Hata türü, dosya veya kullanıcı ara..." oninput="filterErrors()">
            </div>
            <div style="display: flex; gap: 4px; background: var(--bg-surface); padding: 2px; border-radius: 6px; border: 1px solid var(--border-stone);">
              <button id="btnStatusOpen" class="btn btn-secondary active" style="font-size: 11px; padding: 4px 10px; border: none;" onclick="toggleStatusFilter('open')">Açık Hatalar</button>
              <button id="btnStatusResolved" class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px; border: none;" onclick="toggleStatusFilter('resolved')">Çözülenler</button>
              <button id="btnStatusAll" class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px; border: none;" onclick="toggleStatusFilter('all')">Tümü</button>
            </div>
            <div style="display: flex; gap: 4px; background: var(--bg-surface); padding: 2px; border-radius: 6px; border: 1px solid var(--border-stone);">
              <button id="btnErrorsUnique" class="btn btn-secondary active" style="font-size: 11px; padding: 4px 10px; border: none;" onclick="toggleErrorsView(true)">Benzersiz Hatalar</button>
              <button id="btnErrorsAll" class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px; border: none;" onclick="toggleErrorsView(false)">Tüm Kayıtlar</button>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="exportErrors('csv')" title="Görünen hata listesini CSV olarak indir">CSV</button>
            <button class="btn btn-secondary btn-sm" onclick="exportErrors('json')" title="Görünen hata listesini JSON olarak indir">JSON</button>
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Son Görülme</th>
                <th>Durum</th>
                <th>Tekrar</th>
                <th>Hata & Çağrı Konumu</th>
                <th>Hata Mesajı</th>
                <th>Tester(lar)</th>
                <th>Sekme</th>
                <th>Sürüm</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody id="errorsTableBody">
              <tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 20px;">Hata kaydı bulunmuyor.</td></tr>
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
            <div class="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              Kullanıcıların Çalıştırdığı Serpent Betikleri
            </div>
            <div class="card-subtitle">Kullanıcıların izin verdiği paylaşılan modeller ve girdi betikleri.</div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <div class="search-input-wrap">
              <svg class="search-icon-svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" class="search-input" id="searchScripts" placeholder="Proje veya kullanıcı ara..." oninput="filterScripts()">
            </div>
            <button class="btn btn-secondary btn-sm" onclick="exportScripts('csv')" title="Listelenen betikleri CSV olarak indir">CSV</button>
            <button class="btn btn-secondary btn-sm" onclick="exportScripts('json')" title="Listelenen betikleri JSON olarak indir">JSON</button>
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
              <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Kayıt yok.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ANNOUNCEMENTS TAB -->
    <div id="tab-announcements" style="display: none;">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/></svg>
              Yeni Duyuru Gönder
            </div>
            <div class="card-subtitle">Mesaj, masaüstü uygulamasının canlı heartbeat'i (en geç 60 sn) ile uygulama yeniden başlatılmadan kullanıcılara bildirim olarak gösterilir.</div>
          </div>
        </div>
        <textarea id="announcementMessage" rows="3" placeholder="Duyuru metni (örn: Bu akşam 21:00-22:00 arası bakım yapılacaktır, lütfen çalışmalarınızı kaydedin)..." style="max-width: 820px;"></textarea>
        <div class="form-row" style="margin-top: 12px;">
          <select id="announcementTarget" onchange="onAnnouncementTargetChange()" style="flex: 1; min-width: 190px;">
            <option value="all">Tüm aktif kullanıcılar</option>
            <option value="selected">Seçili kullanıcılar</option>
          </select>
          <select id="announcementExpiry" style="flex: 1; min-width: 170px;">
            <option value="24">24 saat geçerli</option>
            <option value="72">3 gün geçerli</option>
            <option value="168">7 gün geçerli</option>
            <option value="0">Süresiz</option>
          </select>
          <button class="btn" onclick="createAnnouncement()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            Duyuruyu Gönder
          </button>
        </div>
        <div id="announcementTargets" style="display: none; margin-top: 14px;">
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px; font-weight: 500;">Hedef kullanıcıları seçin:</div>
          <div class="panel-grid" id="announcementUserPicker"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              Gönderilmiş Duyurular
            </div>
            <div class="card-subtitle">Görülme sayısı, duyuruyu masaüstünde gören kullanıcı sayısıdır; yayından kaldırılan duyurular yeni oturumlarda gösterilmez.</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="loadAnnouncements()" title="Duyuru listesini yenile">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Yenile
          </button>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Zaman</th>
                <th>Mesaj</th>
                <th>Hedef</th>
                <th>Görülme</th>
                <th>Bitiş</th>
                <th>Durum</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody id="announcementsTableBody">
              <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Yükleniyor...</td></tr>
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
    <div class="modal-content" style="max-width: 900px; width: 95%;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
        <h3 id="modalTitle" style="color: var(--text-main); font-size: 16px; font-weight: 600;">Detay</h3>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button id="btnModalStatus" class="btn btn-sm btn-success" style="display:none;" onclick="toggleCurrentModalErrorStatus()"></button>
          <button class="btn btn-sm btn-secondary" onclick="copyDetailModalContent()">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            Panoya Kopyala
          </button>
          <button class="btn btn-sm btn-danger" onclick="closeModal()">Kapat</button>
        </div>
      </div>
      <pre id="modalBody" style="max-height: 520px; overflow-y: auto; background: var(--bg-input); padding: 14px; border-radius: 8px; border: 1px solid var(--border-stone); font-size: 12px; color: var(--text-soft); font-family: monospace; white-space: pre-wrap; word-break: break-all;"></pre>
    </div>
  </div>

  <!-- MODAL: PANEL RESTRICTIONS -->
  <div class="modal" id="restrictionsModal">
    <div class="modal-content">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
          <h3 style="color: var(--text-main); font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--ochre-light)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Panel ve Modül Kısıtlamaları
          </h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 3px;">
            Kullanıcı: <strong id="modalRestrictUsername" style="color: var(--pine-light);"></strong>
          </p>
        </div>
        <button class="btn btn-sm btn-danger" onclick="closeRestrictionsModal()">Kapat</button>
      </div>

      <div style="background: var(--ochre-subtle); border: 1px solid var(--ochre-border); border-radius: 10px; padding: 12px 16px; margin: 14px 0; font-size: 13px; color: #92400E; line-height: 1.45;">
        <strong>İşleyiş Kuralı:</strong> İşaretlediğiniz paneller kullanıcının masaüstü uygulamasında anında devre dışı bırakılır ve gizlenir. Canlı heartbeat (en geç 60 sn) ile uygulama yeniden başlatılmadan devreye girer.
      </div>

      <!-- Quick Preset Buttons -->
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;">
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions([])">Tümünü Aç</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(ALL_PANEL_IDS)">Tümünü Kısıtla</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(['materials','assembly','geometry','control_rods','detectors','coefficients','simulation','settings','console'])">Salt Okunur (Sadece Sonuç İnceleme)</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(['settings','console'])">Standart Tester (Ayarlar & Konsol Kilitli)</button>
      </div>

      <div class="panel-grid" id="panelGridContainer">
        <!-- Rendered dynamically -->
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; border-top: 1px solid var(--border-stone); padding-top: 14px;">
        <button class="btn btn-secondary" onclick="closeRestrictionsModal()">İptal</button>
        <button class="btn" onclick="saveRestrictions()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          Kısıtlamaları Kaydet
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL: USER DETAIL -->
  <div class="modal" id="userDetailModal">
    <div class="modal-content" style="max-width: 980px; width: 95%;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
        <h3 id="userDetailTitle" style="color: var(--text-main); font-size: 16px; font-weight: 600;">Kullanıcı Detayı</h3>
        <button class="btn btn-sm btn-danger" onclick="closeUserDetail()">Kapat</button>
      </div>
      <div id="userDetailSummary" style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;"></div>

      <div style="font-size: 13px; font-weight: 700; color: var(--text-main); margin: 12px 0 8px;">Aktif / Kapatılmış Oturumlar</div>
      <div class="table-container" style="margin: 0 0 16px;">
        <table>
          <thead>
            <tr><th>Oluşturulma</th><th>Son Nabız</th><th>Sürüm</th><th>Platform</th><th>Durum</th></tr>
          </thead>
          <tbody id="userDetailSessions"></tbody>
        </table>
      </div>

      <div style="font-size: 13px; font-weight: 700; color: var(--text-main); margin: 12px 0 8px;">Son Hata Raporları</div>
      <div class="table-container" style="margin: 0 0 16px;">
        <table>
          <thead>
            <tr><th>Zaman</th><th>Tür</th><th>Mesaj</th><th>Tekrar</th><th>Durum</th></tr>
          </thead>
          <tbody id="userDetailErrors"></tbody>
        </table>
      </div>

      <div style="font-size: 13px; font-weight: 700; color: var(--text-main); margin: 12px 0 8px;">Son Paylaşılan Betikler</div>
      <div class="table-container" style="margin: 0;">
        <table>
          <thead>
            <tr><th>Zaman</th><th>Proje</th><th>Boyut</th></tr>
          </thead>
          <tbody id="userDetailScripts"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const currentServerVersion = '__CURRENT_SERVER_VERSION__';
    const appStorage = (typeof sessionStorage !== 'undefined') ? sessionStorage : {
      getItem: function() { return null; },
      setItem: function() {},
      removeItem: function() {}
    };
    let adminToken = appStorage.getItem('serpent_admin_token') || '';
    let currentRestrictUser = '';
    let usersCache = [];
    let errorsCache = [];
    let scriptsCache = [];
    let announcementsCache = [];
    let lastUsersRendered = [];
    let lastErrorsRendered = [];
    let lastScriptsRendered = [];

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
      if (type === 'error') toast.style.borderColor = 'var(--terracotta)';
      if (type === 'success') toast.style.borderColor = 'var(--pine)';
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
      if (adminToken) {
        const savedUser = appStorage.getItem('serpent_admin_username');
        if (savedUser && document.getElementById('adminName')) {
          document.getElementById('adminName').textContent = savedUser;
        }
        loadAll();
        return;
      }
      if (document.getElementById('adminLoginDialog')) return;
      const dialog = document.createElement('dialog');
      dialog.id = 'adminLoginDialog';
      dialog.style.cssText = 'margin:auto;padding:28px;background:var(--bg-surface-elevated);color:var(--text-main);border:1px solid var(--border-stone-hover);border-radius:16px;box-shadow:0 20px 60px rgba(10,58,102,0.35);max-width:380px;width:90%';
      dialog.addEventListener('cancel', event => event.preventDefault());
      const form = document.createElement('form');
      const title = document.createElement('h2');
      title.textContent = 'Serpent Studio Yönetici Girişi';
      title.style.cssText = 'font-size:18px;margin-bottom:16px;color:#0A3A66;text-align:center;font-weight:600;letter-spacing:-0.2px;';
      const username = document.createElement('input');
      username.placeholder = 'Kullanıcı adı'; username.autocomplete = 'username'; username.required = true;
      username.style.cssText = 'width:100%;margin-bottom:12px;display:block;';
      const password = document.createElement('input');
      password.type = 'password'; password.placeholder = 'Şifre'; password.autocomplete = 'current-password'; password.required = true;
      password.style.cssText = 'width:100%;margin-bottom:14px;display:block;';
      const error = document.createElement('p'); error.setAttribute('role', 'alert');
      error.style.cssText = 'color:var(--terracotta);font-size:12px;margin-bottom:12px;min-height:16px;text-align:center;';
      const submit = document.createElement('button'); submit.type = 'submit'; submit.className = 'btn'; submit.textContent = 'Giriş Yap';
      submit.style.cssText = 'width:100%;justify-content:center;padding:11px;';
      form.append(title, username, password, error, submit);
      form.addEventListener('submit', event => {
        event.preventDefault(); submit.disabled = true; error.textContent = '';
        fetch('/admin/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:username.value, password:password.value})})
        .then(response => response.json().then(data => {
          if (!response.ok || data.status !== 'ok' || !data.token) throw new Error(data.message || 'Giriş başarısız.');
          adminToken = data.token; password.value = '';
          appStorage.setItem('serpent_admin_token', data.token);
          appStorage.setItem('serpent_admin_username', data.username || username.value);
          document.getElementById('adminName').textContent = data.username || username.value;
          dialog.close(); dialog.remove(); loadAll();
          showToast('Hoş geldiniz, ' + (data.username || username.value) + '!', 'success');
        }))
        .catch(err => { error.textContent = err.message || 'Sunucuya bağlanılamadı.'; })
        .finally(() => { submit.disabled = false; });
      });
      dialog.append(form); document.body.append(dialog); dialog.showModal(); username.focus();
    }

    function logoutAdmin() {
      const token = adminToken;
      adminToken = '';
      appStorage.removeItem('serpent_admin_token');
      appStorage.removeItem('serpent_admin_username');
      fetch('/admin/api/logout', {method:'POST', headers:{Authorization:'Bearer ' + token}}).finally(() => location.reload());
    }

    function switchTab(name, ev) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      if (ev && ev.currentTarget) {
        ev.currentTarget.classList.add('active');
      }
      ['users', 'errors', 'scripts', 'announcements'].forEach(t => {
        const el = document.getElementById('tab-' + t);
        if (el) el.style.display = (t === name) ? 'block' : 'none';
      });
      if (name === 'users') loadUsers();
      if (name === 'errors') loadErrors();
      if (name === 'scripts') loadScripts();
      if (name === 'announcements') loadAnnouncements();
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
      if (elUSub) {
        const verMap = {};
        usersCache.forEach(u => {
          const v = u.client_version || 'Bilinmiyor';
          verMap[v] = (verMap[v] || 0) + 1;
        });
        const vParts = Object.entries(verMap).map(([ver, cnt]) => `${ver}: ${cnt}`);
        const vText = vParts.length ? ' · Sürümler: ' + vParts.join(', ') : '';
        elUSub.textContent = `${activeUsers} Aktif · ${suspendedUsers} Askıda${vText}`;
      }
      const elRCount = document.getElementById('statRestrictedCount');
      if (elRCount) elRCount.textContent = restrictedUsers;
      
      const elBUsers = document.getElementById('badgeUsers');
      if (elBUsers) elBUsers.textContent = totalUsers;
      const elBErrors = document.getElementById('badgeErrors');
      if (elBErrors) elBErrors.textContent = errorsCache.length;
      const elBScripts = document.getElementById('badgeScripts');
      if (elBScripts) elBScripts.textContent = scriptsCache.length;
      const elBAnnouncements = document.getElementById('badgeAnnouncements');
      if (elBAnnouncements) elBAnnouncements.textContent = announcementsCache.filter(a => !!a.is_active && !a.is_expired).length;
      
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
        renderVersionDistribution();
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
      lastUsersRendered = list;
      const tbody = document.getElementById('usersTableBody');
      tbody.innerHTML = '';
      if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:24px; color:var(--text-muted);">Kayıtlı kullanıcı bulunamadı.</td></tr>';
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
        actionButton(roleCell, u.role, () => editUserRole(u.username, u.role), 'role-badge');
        const state = textCell(tr, isActive ? 'Aktif' : 'Askıya Alındı');
        state.style.color = isActive ? 'var(--pine-light)' : 'var(--terracotta)';
        state.style.fontWeight = '600';

        // Son Sürüm (col 5)
        const verCell = textCell(tr, '');
        const verBadge = document.createElement('span');
        verBadge.style.display = 'inline-block';
        verBadge.style.padding = '2px 8px';
        verBadge.style.borderRadius = '99px';
        verBadge.style.fontWeight = '600';
        verBadge.style.fontSize = '11px';
        verBadge.style.fontFamily = 'monospace';
        if (u.client_version) {
          verBadge.textContent = u.client_version;
          const isLatest = currentServerVersion && (u.client_version === currentServerVersion || u.client_version.startsWith(currentServerVersion.split('.').slice(0, 3).join('.')));
          if (isLatest) {
            verBadge.style.backgroundColor = 'rgba(2, 132, 199, 0.10)';
            verBadge.style.color = '#0369A1';
            verBadge.style.border = '1px solid rgba(2, 132, 199, 0.30)';
          } else {
            verBadge.style.backgroundColor = 'rgba(217, 119, 6, 0.12)';
            verBadge.style.color = '#B45309';
            verBadge.style.border = '1px solid rgba(217, 119, 6, 0.34)';
          }
        } else {
          verBadge.textContent = 'Bilinmiyor';
          verBadge.style.color = 'var(--text-muted)';
        }
        verCell.appendChild(verBadge);

        const permissions = textCell(tr, rPanels.length ? rPanels.length + ' Panel Kısıtlı' : 'Tüm Paneller Açık');
        permissions.title = rPanels.join(', ');
        permissions.style.color = rPanels.length ? 'var(--ochre-light)' : 'var(--text-muted)';
        textCell(tr, lastSeenStr);
        const actions = textCell(tr, ''); actions.style.whiteSpace = 'nowrap';
        actionButton(actions, 'Detay', () => openUserDetail(u.username), 'btn-secondary');
        actionButton(actions, 'Kısıtla', () => openRestrictionsModal(u.username), 'btn-secondary');
        actionButton(actions, isActive ? 'Askıya Al' : 'Aktifleştir', () => toggleUser(u.username, !isActive), isActive ? 'btn-danger' : 'btn-success');
        actionButton(actions, 'Şifre', () => resetPass(u.username), 'btn-warning');
        actionButton(actions, 'Sil', () => deleteUser(u.username), 'btn-danger');
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
      if (document.getElementById('adminResetPassDialog')) return;
      const dialog = document.createElement('dialog');
      dialog.id = 'adminResetPassDialog';
      dialog.style.cssText = 'margin:auto;padding:24px;background:var(--bg-surface-elevated);color:var(--text-main);border:1px solid var(--border-stone-hover);border-radius:16px;box-shadow:0 20px 60px rgba(10,58,102,0.35);max-width:380px;width:90%';
      const form = document.createElement('form');
      const title = document.createElement('h3');
      title.textContent = `'${username}' İçin Yeni Şifre`;
      title.style.cssText = 'font-size:16px;margin-bottom:12px;color:#0A3A66;text-align:center;font-weight:600;';
      const desc = document.createElement('p');
      desc.textContent = 'En az 12 karakter içeren güçlü bir şifre giriniz:';
      desc.style.cssText = 'font-size:12px;color:var(--text-muted);margin-bottom:12px;text-align:center;';
      const password = document.createElement('input');
      password.type = 'password'; password.placeholder = 'Yeni şifre (min 12 karakter)'; password.autocomplete = 'new-password'; password.required = true;
      password.style.cssText = 'width:100%;margin-bottom:12px;display:block;';
      const error = document.createElement('p'); error.setAttribute('role', 'alert');
      error.style.cssText = 'color:var(--terracotta);font-size:12px;margin-bottom:12px;min-height:16px;text-align:center;';
      const btnGroup = document.createElement('div');
      btnGroup.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
      const cancelBtn = document.createElement('button');
      cancelBtn.type = 'button'; cancelBtn.className = 'btn'; cancelBtn.textContent = 'İptal';
      cancelBtn.style.cssText = 'background:transparent;border:1px solid var(--border-stone);';
      cancelBtn.onclick = () => { dialog.close(); dialog.remove(); };
      const submit = document.createElement('button');
      submit.type = 'submit'; submit.className = 'btn'; submit.textContent = 'Kaydet';
      btnGroup.append(cancelBtn, submit);
      form.append(title, desc, password, error, btnGroup);
      form.addEventListener('submit', event => {
        event.preventDefault();
        const newP = password.value;
        if (!newP || newP.length < 12) {
          error.textContent = 'Şifre en az 12 karakter olmalıdır.';
          return;
        }
        submit.disabled = true; error.textContent = '';
        apiCall('/admin/api/users/reset-password', 'POST', { username, password: newP }).then(res => {
          if (res.status === 'ok') {
            dialog.close(); dialog.remove();
            showToast(`'${username}' şifresi başarıyla yenilendi.`, "success");
          } else {
            error.textContent = res.message || 'Şifre güncellenemedi.';
          }
        }).catch(err => {
          error.textContent = err.message || 'Bağlantı hatası.';
        }).finally(() => { submit.disabled = false; });
      });
      dialog.append(form); document.body.append(dialog); dialog.showModal(); password.focus();
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
        (e.users && e.users.some(u => u.toLowerCase().includes(query))) ||
        (e.exception_type && e.exception_type.toLowerCase().includes(query)) ||
        (e.exception_message && e.exception_message.toLowerCase().includes(query)) ||
        (e.call_site && e.call_site.toLowerCase().includes(query))
      );
      renderErrorsTable(filtered);
    }

    let errorsUniqueMode = true;
    let errorsStatusFilter = 'open';
    let currentModalError = null;

    function toggleStatusFilter(filter) {
      errorsStatusFilter = filter;
      ['open', 'resolved', 'all'].forEach(s => {
        const btn = document.getElementById('btnStatus' + s.charAt(0).toUpperCase() + s.slice(1));
        if (btn) {
          if (s === filter) btn.classList.add('active');
          else btn.classList.remove('active');
        }
      });
      loadErrors();
    }

    function toggleErrorsView(isUnique) {
      errorsUniqueMode = isUnique;
      const btnU = document.getElementById('btnErrorsUnique');
      const btnA = document.getElementById('btnErrorsAll');
      if (btnU && btnA) {
        if (isUnique) {
          btnU.classList.add('active');
          btnA.classList.remove('active');
        } else {
          btnU.classList.remove('active');
          btnA.classList.add('active');
        }
      }
      loadErrors();
    }

    function loadErrors() {
      let url = '/admin/api/errors?unique=' + (errorsUniqueMode ? '1' : '0');
      if (errorsStatusFilter && errorsStatusFilter !== 'all') {
        url += '&status=' + encodeURIComponent(errorsStatusFilter);
      }
      apiCall(url).then(data => {
        errorsCache = data.errors || [];
        updateStats();
        renderErrorsTable(errorsCache);
      });
    }

    function renderErrorsTable(list) {
      lastErrorsRendered = list;
      const tbody = document.getElementById('errorsTableBody');
      tbody.innerHTML = '';
      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--text-muted);">Henüz kaydedilmiş hata yok.</td></tr>';
        return;
      }
      list.forEach(e => {
        const tr = document.createElement('tr');
        const timeVal = e.last_seen || e.timestamp;
        const timeStr = timeVal ? new Date(timeVal * 1000).toLocaleString('tr-TR') : '-';
        textCell(tr, timeStr);

        // Status badge
        const statusCell = textCell(tr, '');
        const isResolved = (e.status === 'resolved');
        const statusBadge = document.createElement('span');
        statusBadge.style.display = 'inline-block';
        statusBadge.style.padding = '2px 8px';
        statusBadge.style.borderRadius = '99px';
        statusBadge.style.fontWeight = '600';
        statusBadge.style.fontSize = '11px';
        statusBadge.style.cursor = 'pointer';
        statusBadge.title = isResolved ? 'Tekrar açmak için tıklayın' : 'Çözüldü olarak işaretlemek için tıklayın';
        statusBadge.onclick = (ev) => {
          ev.stopPropagation();
          toggleErrorStatusDirect(e, isResolved ? 'open' : 'resolved');
        };
        if (isResolved) {
          statusBadge.style.backgroundColor = 'var(--pine-subtle)';
          statusBadge.style.color = 'var(--pine-light)';
          statusBadge.style.border = '1px solid var(--pine-border)';
          statusBadge.textContent = '✓ Çözüldü';
        } else {
          statusBadge.style.backgroundColor = 'rgba(220, 38, 38, 0.10)';
          statusBadge.style.color = '#B91C1C';
          statusBadge.style.border = '1px solid rgba(220, 38, 38, 0.30)';
          statusBadge.textContent = '● Açık';
        }
        statusCell.appendChild(statusBadge);

        // Occurrence count badge
        const count = e.occurrence_count || 1;
        const countCell = textCell(tr, '');
        const countBadge = document.createElement('span');
        countBadge.style.display = 'inline-block';
        countBadge.style.padding = '2px 8px';
        countBadge.style.borderRadius = '10px';
        countBadge.style.fontWeight = '800';
        countBadge.style.fontSize = '11px';
        if (count > 5) {
          countBadge.style.backgroundColor = 'var(--terracotta)';
          countBadge.style.color = '#FFFFFF';
        } else if (count > 1) {
          countBadge.style.backgroundColor = '#B45309';
          countBadge.style.color = '#FFFFFF';
        } else {
          countBadge.style.backgroundColor = 'var(--surface-hover)';
          countBadge.style.color = 'var(--text-muted)';
        }
        countBadge.textContent = count + 'x';
        countCell.appendChild(countBadge);

        // Exception type & Call site
        const exCell = document.createElement('td');
        const exTitle = document.createElement('div');
        const isDiag = (e.exception_type === 'UserDiagnosticReport') || (e.extra_context_data && e.extra_context_data.manual_report);
        if (isDiag) {
          exTitle.style.color = 'var(--stream-light)';
          exTitle.style.fontWeight = '700';
          exTitle.textContent = 'Tanı Raporu (Diagnostic)';
        } else {
          exTitle.style.color = 'var(--terracotta)';
          exTitle.style.fontWeight = '700';
          exTitle.textContent = e.exception_type || 'Unknown';
        }
        exCell.appendChild(exTitle);
        if (e.call_site && e.call_site !== '-') {
          const csLabel = document.createElement('div');
          csLabel.style.fontSize = '10px';
          csLabel.style.color = 'var(--text-muted)';
          csLabel.style.fontFamily = 'monospace';
          csLabel.textContent = e.call_site;
          exCell.appendChild(csLabel);
        }
        tr.appendChild(exCell);

        textCell(tr, String(e.exception_message || '').substring(0, 50) + (String(e.exception_message || '').length > 50 ? '...' : ''));

        // Testers
        const usersStr = (e.users && e.users.length > 0) ? e.users.join(', ') : (e.username || '-');
        textCell(tr, usersStr);

        textCell(tr, e.active_tab || '-');
        textCell(tr, e.app_version || '-');
        const actionTd = textCell(tr, '');
        actionTd.style.whiteSpace = 'nowrap';
        actionButton(actionTd, isResolved ? 'Tekrar Aç' : '✓ Çözüldü', () => toggleErrorStatusDirect(e, isResolved ? 'open' : 'resolved'), isResolved ? 'btn-warning' : 'btn-success');
        actionButton(actionTd, 'Detay İncele', () => showTraceback(e), 'btn-secondary');
        tbody.appendChild(tr);
      });
    }

    function toggleErrorStatusDirect(e, targetStatus) {
      if (!e) return;
      const payload = { status: targetStatus };
      if (e.fingerprint) payload.fingerprint = e.fingerprint;
      if (e.id != null) payload.id = e.id;
      apiCall('/admin/api/errors/status', 'POST', payload).then(res => {
        if (res.status === 'ok') {
          e.status = targetStatus;
          showToast(targetStatus === 'resolved' ? "Hata çözüldü olarak işaretlendi!" : "Hata yeniden açık duruma getirildi.", "success");
          loadErrors();
        } else {
          showToast("Durum güncellenemedi: " + (res.message || 'Bilinmeyen hata'), "error");
        }
      }).catch(err => {
        showToast("İstek başarısız: " + (err.message || 'Bağlantı hatası'), "error");
      });
    }

    function toggleCurrentModalErrorStatus() {
      if (!currentModalError) return;
      const newStatus = (currentModalError.status === 'resolved') ? 'open' : 'resolved';
      const payload = { status: newStatus };
      if (currentModalError.fingerprint) payload.fingerprint = currentModalError.fingerprint;
      if (currentModalError.id != null) payload.id = currentModalError.id;
      apiCall('/admin/api/errors/status', 'POST', payload).then(res => {
        if (res.status === 'ok') {
          currentModalError.status = newStatus;
          showToast(newStatus === 'resolved' ? "Hata çözüldü olarak işaretlendi!" : "Hata yeniden açık duruma getirildi.", "success");
          updateModalStatusButton(newStatus);
          showTraceback(currentModalError);
          loadErrors();
        } else {
          showToast("Durum güncellenemedi: " + (res.message || 'Bilinmeyen hata'), "error");
        }
      }).catch(err => {
        showToast("İstek başarısız: " + (err.message || 'Bağlantı hatası'), "error");
      });
    }

    function updateModalStatusButton(st) {
      const btn = document.getElementById('btnModalStatus');
      if (!btn) return;
      btn.style.display = 'inline-flex';
      if (st === 'resolved') {
        btn.className = 'btn btn-sm btn-warning';
        btn.textContent = 'Tekrar Aç';
      } else {
        btn.className = 'btn btn-sm btn-success';
        btn.textContent = '✓ Çözüldü Olarak İşaretle';
      }
    }

    function showTraceback(e) {
      currentModalError = e;
      updateModalStatusButton(e.status || 'open');

      const ctx = e.extra_context_data || {};
      const isDiag = (e.exception_type === 'UserDiagnosticReport') || (ctx && ctx.manual_report);
      document.getElementById('modalTitle').innerText = isDiag
        ? `Tanı Raporu: ${e.username || 'Kullanıcı'} (${e.occurrence_count || 1}x Gönderim)`
        : `Hata Detayı: ${e.exception_type} (${e.occurrence_count || 1}x Tekrar)`;
      const firstStr = e.first_seen ? new Date(e.first_seen * 1000).toLocaleString('tr-TR') : '-';
      const lastStr = new Date((e.last_seen || e.timestamp) * 1000).toLocaleString('tr-TR');
      const usersStr = (e.users && e.users.length > 0) ? e.users.join(', ') : e.username;

      let overview = `=======================================================\n` +
                     (isDiag ? `KULLANICI MANUEL TANI RAPORU & SİSTEM ÖZETİ\n` : `HATA DETAYI & GELİŞTİRİCİ RAPORU\n`) +
                     `=======================================================\n` +
                     `Hata Türü      : ${e.exception_type}\n` +
                     `Hata Mesajı    : ${e.exception_message}\n` +
                     `Çağrı Konumu   : ${e.call_site || '-'}\n` +
                     `Durum          : ${(e.status === 'resolved' ? 'ÇÖZÜLDÜ' : 'AÇIK')}\n` +
                     `Tekrar Sayısı  : ${e.occurrence_count || 1} kez kaydedildi\n` +
                     `İlk Görülme    : ${firstStr}\n` +
                     `Son Görülme    : ${lastStr}\n` +
                     `Etkilenenler   : ${usersStr}\n` +
                     `Sürüm          : ${e.app_version || '-'}\n` +
                     `Platform       : ${e.platform || '-'}\n` +
                     `Aktif Sekme    : ${e.active_tab || '-'}\n\n`;

      if (ctx && Object.keys(ctx).length > 0) {
        overview +=  `=======================================================\n` +
                     `[SİSTEM VE ÇALIŞMA ZAMANI TANILARI]:\n` +
                     `=======================================================\n` +
                     `RAM (RSS)      : ${ctx.rss_memory_mb ? ctx.rss_memory_mb + ' MB' : '-'}\n` +
                     `Pencere Ortamı : ${ctx.window_system || '-'}\n` +
                     `Masaüstü (DE)  : ${ctx.desktop_env || '-'}\n` +
                     `Ekran DPI      : ${ctx.screen_dpi || '-'}\n` +
                     `Thread Sayısı  : ${ctx.thread_count || '-'}\n` +
                     `Python Sürümü  : ${ctx.python_version || '-'}\n\n`;

        if (Array.isArray(ctx.breadcrumbs) && ctx.breadcrumbs.length > 0) {
          overview += `=======================================================\n` +
                      `[KULLANICI EYLEM AKIŞI (BREADCRUMBS - SON ${ctx.breadcrumbs.length} EYLEM)]:\n` +
                      `=======================================================\n`;
          ctx.breadcrumbs.forEach(b => {
            const t = b.time_str || (b.timestamp ? new Date(b.timestamp * 1000).toLocaleTimeString('tr-TR') : '--:--:--');
            overview += `[${t}] [${b.category || 'event'}] ${b.message || ''}\n`;
          });
          overview += `\n`;
        }
      }

      overview +=    `=======================================================\n` +
                     `[PYTHON TRACEBACK]:\n` +
                     `=======================================================\n` +
                     `${e.traceback || 'Traceback bulunmuyor'}\n\n` +
                     `=======================================================\n` +
                     `[SON UYGULAMA LOGLARI]:\n` +
                     `=======================================================\n` +
                     `${e.recent_logs || 'Log bulunmuyor'}\n`;

      document.getElementById('modalBody').innerText = overview;
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
      lastScriptsRendered = list;
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
        actionButton(textCell(tr, ''), 'Betiği Gör', () => viewScript(s.id), 'btn-secondary');
        tbody.appendChild(tr);
      });
    }

    function viewScript(id) {
      apiCall('/admin/api/script/' + id).then(data => {
        document.getElementById('modalTitle').innerText = "Serpent Girdi Betiği";
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
      currentModalError = null;
      const btn = document.getElementById('btnModalStatus');
      if (btn) btn.style.display = 'none';
    }

    function loadAll() {
      loadUsers();
      loadErrors();
      loadScripts();
      loadAnnouncements();
    }

    function renderVersionDistribution() {
      const container = document.getElementById('versionBars');
      if (!container) return;
      while (container.firstChild) container.removeChild(container.firstChild);
      const summary = document.getElementById('versionSummaryBadge');
      const currentPrefix = currentServerVersion ? currentServerVersion.split('.').slice(0, 3).join('.') : '';
      const counts = {};
      let latestCount = 0;
      usersCache.forEach(u => {
        const v = String(u.client_version || '').trim() || 'Bilinmiyor';
        counts[v] = (counts[v] || 0) + 1;
        if (v !== 'Bilinmiyor' && currentPrefix && v.indexOf(currentPrefix) === 0) latestCount += 1;
      });
      const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      if (!entries.length) {
        const empty = document.createElement('div');
        empty.style.cssText = 'font-size: 12px; color: var(--text-muted); padding: 4px 0;';
        empty.textContent = 'Henüz istemci sürümü bildirilmedi.';
        container.appendChild(empty);
        if (summary) summary.textContent = '-';
        return;
      }
      const maxCount = entries[0][1];
      entries.forEach(entry => {
        const version = entry[0];
        const count = entry[1];
        const row = document.createElement('div');
        row.className = 'vbar-row';
        const label = document.createElement('span');
        label.className = 'vbar-label';
        label.textContent = version;
        const track = document.createElement('div');
        track.className = 'vbar-track';
        const fill = document.createElement('div');
        fill.className = 'vbar-fill';
        const isUnknown = (version === 'Bilinmiyor');
        const isLatest = !isUnknown && currentPrefix && version.indexOf(currentPrefix) === 0;
        fill.style.width = Math.max(6, Math.round((count / maxCount) * 100)) + '%';
        fill.style.background = isUnknown
          ? 'linear-gradient(90deg, #94A3B8, #CBD5E1)'
          : (isLatest ? 'linear-gradient(90deg, #0284C7, #0EA5E9)' : 'linear-gradient(90deg, #B45309, #D97706)');
        track.appendChild(fill);
        const countLabel = document.createElement('span');
        countLabel.className = 'vbar-count';
        countLabel.textContent = count + ' kişi';
        row.appendChild(label); row.appendChild(track); row.appendChild(countLabel);
        container.appendChild(row);
      });
      if (summary) summary.textContent = 'Güncel: ' + latestCount + ' / ' + usersCache.length;
    }

    function csvEscape(value) {
      const str = (value == null) ? '' : String(value);
      if (str.indexOf('"') >= 0 || str.indexOf(',') >= 0 || str.indexOf('\\n') >= 0) {
        return '"' + str.split('"').join('""') + '"';
      }
      return str;
    }

    function csvRows(header, rows) {
      const lines = [header].concat(rows);
      return lines.map(row => row.map(csvEscape).join(',')).join('\\n');
    }

    function downloadFile(filename, content, mime) {
      const blob = new Blob([content], {type: mime});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    }

    function exportUsers(format) {
      const list = lastUsersRendered || [];
      if (!list.length) { showToast('Dışa aktarılacak kullanıcı kaydı yok.', 'error'); return; }
      if (format === 'json') {
        downloadFile('serpent-kullanicilar.json', JSON.stringify(list, null, 2), 'application/json');
      } else {
        const rows = list.map(u => [
          u.username || '', u.display_name || '', u.role || '',
          u.is_active ? 'aktif' : 'askida',
          u.client_version || '',
          Array.isArray(u.restricted_panels) ? u.restricted_panels.join('|') : '',
          u.last_seen ? new Date(u.last_seen * 1000).toISOString() : ''
        ]);
        downloadFile('serpent-kullanicilar.csv', csvRows(['username','display_name','role','durum','son_surum','panel_kisitlari','son_gorulme'], rows), 'text/csv;charset=utf-8');
      }
      showToast('Kullanıcı listesi indirildi (' + (format === 'json' ? 'JSON' : 'CSV') + ').', 'success');
    }

    function exportErrors(format) {
      const list = lastErrorsRendered || [];
      if (!list.length) { showToast('Dışa aktarılacak hata kaydı yok.', 'error'); return; }
      if (format === 'json') {
        downloadFile('serpent-hatalar.json', JSON.stringify(list, null, 2), 'application/json');
      } else {
        const rows = list.map(e => {
          const names = (e.users && e.users.length) ? e.users.join('|') : (e.username || '');
          const timeVal = e.last_seen || e.timestamp;
          return [
            timeVal ? new Date(timeVal * 1000).toISOString() : '',
            e.status || 'open',
            e.occurrence_count || 1,
            e.exception_type || '',
            e.call_site || '',
            e.exception_message || '',
            names,
            e.active_tab || '',
            e.app_version || ''
          ];
        });
        downloadFile('serpent-hatalar.csv', csvRows(['zaman','durum','tekrar','tur','cagri_konumu','mesaj','kullanicilar','sekme','surum'], rows), 'text/csv;charset=utf-8');
      }
      showToast('Hata listesi indirildi (' + (format === 'json' ? 'JSON' : 'CSV') + ').', 'success');
    }

    function exportScripts(format) {
      const list = lastScriptsRendered || [];
      if (!list.length) { showToast('Dışa aktarılacak betik kaydı yok.', 'error'); return; }
      if (format === 'json') {
        downloadFile('serpent-betikler.json', JSON.stringify(list, null, 2), 'application/json');
      } else {
        const rows = list.map(s => [
          s.timestamp ? new Date(s.timestamp * 1000).toISOString() : '',
          s.username || '',
          s.project_name || '',
          ((s.size || 0) / 1024).toFixed(1) + ' KB'
        ]);
        downloadFile('serpent-betikler.csv', csvRows(['zaman','kullanici','proje','boyut'], rows), 'text/csv;charset=utf-8');
      }
      showToast('Betik listesi indirildi (' + (format === 'json' ? 'JSON' : 'CSV') + ').', 'success');
    }

    function loadAnnouncements() {
      apiCall('/admin/api/announcements').then(data => {
        announcementsCache = data.announcements || [];
        updateStats();
        renderAnnouncementsTable(announcementsCache);
      });
    }

    function renderAnnouncementsTable(list) {
      const tbody = document.getElementById('announcementsTableBody');
      while (tbody.firstChild) tbody.removeChild(tbody.firstChild);
      if (!list || list.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 7;
        td.style.textAlign = 'center';
        td.style.padding = '24px';
        td.style.color = 'var(--text-muted)';
        td.textContent = 'Henüz duyuru gönderilmedi.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
      }
      list.forEach(a => {
        const tr = document.createElement('tr');
        textCell(tr, a.created_at ? new Date(a.created_at * 1000).toLocaleString('tr-TR') : '-');

        const msgCell = textCell(tr, '');
        const msgDiv = document.createElement('div');
        const fullMsg = String(a.message || '');
        msgDiv.textContent = fullMsg.length > 60 ? (fullMsg.substring(0, 60) + '...') : fullMsg;
        msgDiv.title = fullMsg;
        msgDiv.style.maxWidth = '340px';
        msgCell.appendChild(msgDiv);

        const targetStr = (a.target_type === 'selected')
          ? ('Seçili: ' + (Array.isArray(a.target_usernames) ? a.target_usernames.join(', ') : ''))
          : 'Tüm kullanıcılar';
        textCell(tr, targetStr);

        textCell(tr, (a.seen_count || 0) + ' / ' + (a.target_count || 0));

        if (a.is_expired) {
          textCell(tr, 'Süresi doldu');
        } else if (a.expires_at) {
          textCell(tr, new Date(a.expires_at * 1000).toLocaleString('tr-TR'));
        } else {
          textCell(tr, 'Süresiz');
        }

        const stCell = textCell(tr, '');
        const stBadge = document.createElement('span');
        stBadge.style.display = 'inline-block';
        stBadge.style.padding = '2px 8px';
        stBadge.style.borderRadius = '99px';
        stBadge.style.fontWeight = '600';
        stBadge.style.fontSize = '11px';
        if (a.is_expired) {
          stBadge.style.backgroundColor = 'var(--surface-hover)';
          stBadge.style.color = 'var(--text-muted)';
          stBadge.textContent = 'Süresi Doldu';
        } else if (a.is_active) {
          stBadge.style.backgroundColor = 'rgba(2, 132, 199, 0.10)';
          stBadge.style.color = '#0369A1';
          stBadge.style.border = '1px solid rgba(2, 132, 199, 0.30)';
          stBadge.textContent = '● Yayında';
        } else {
          stBadge.style.backgroundColor = 'rgba(220, 38, 38, 0.10)';
          stBadge.style.color = '#B91C1C';
          stBadge.style.border = '1px solid rgba(220, 38, 38, 0.30)';
          stBadge.textContent = 'Yayından Kaldırıldı';
        }
        stCell.appendChild(stBadge);

        const actionTd = textCell(tr, '');
        actionTd.style.whiteSpace = 'nowrap';
        actionButton(actionTd, a.is_active ? 'Yayından Kaldır' : 'Yeniden Yayınla',
          () => toggleAnnouncement(a.id, !a.is_active),
          a.is_active ? 'btn-danger' : 'btn-success');
        tbody.appendChild(tr);
      });
    }

    function toggleAnnouncement(id, isActive) {
      apiCall('/admin/api/announcements/toggle', 'POST', {id: id, is_active: isActive}).then(res => {
        if (res.status === 'ok') {
          showToast(isActive ? 'Duyuru yeniden yayınlandı.' : 'Duyuru yayından kaldırıldı.', 'success');
          loadAnnouncements();
        } else {
          showToast('Duyuru güncellenemedi.', 'error');
        }
      }).catch(err => showToast('İstek başarısız: ' + (err.message || 'Bağlantı hatası'), 'error'));
    }

    function onAnnouncementTargetChange() {
      const targetSel = document.getElementById('announcementTarget');
      const wrap = document.getElementById('announcementTargets');
      if (!targetSel || !wrap) return;
      const isSelected = (targetSel.value === 'selected');
      wrap.style.display = isSelected ? 'block' : 'none';
      if (isSelected) buildAnnouncementUserPicker();
    }

    function buildAnnouncementUserPicker() {
      const picker = document.getElementById('announcementUserPicker');
      if (!picker) return;
      while (picker.firstChild) picker.removeChild(picker.firstChild);
      const candidates = usersCache.filter(u => !!u.is_active);
      if (!candidates.length) {
        const empty = document.createElement('div');
        empty.style.fontSize = '12px';
        empty.style.color = 'var(--text-muted)';
        empty.textContent = 'Aktif kullanıcı bulunmuyor.';
        picker.appendChild(empty);
        return;
      }
      candidates.forEach(u => {
        const card = document.createElement('label');
        card.className = 'panel-card';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = u.username || '';
        cb.className = 'announcement-user-check';
        const span = document.createElement('span');
        span.textContent = (u.display_name || u.username || '') + ' (' + (u.username || '') + ')';
        span.style.fontSize = '12px';
        card.appendChild(cb);
        card.appendChild(span);
        picker.appendChild(card);
      });
    }

    function createAnnouncement() {
      const msgEl = document.getElementById('announcementMessage');
      const message = (msgEl.value || '').trim();
      const targetType = document.getElementById('announcementTarget').value;
      const expiry = document.getElementById('announcementExpiry').value;
      if (!message) { showToast('Duyuru metni boş olamaz.', 'error'); return; }
      let usernames = [];
      if (targetType === 'selected') {
        document.querySelectorAll('.announcement-user-check').forEach(cb => { if (cb.checked) usernames.push(cb.value); });
        if (!usernames.length) { showToast('En az bir hedef kullanıcı seçin.', 'error'); return; }
      }
      apiCall('/admin/api/announcements/create', 'POST', {
        message: message,
        target_type: targetType,
        usernames: usernames,
        expires_in_hours: expiry
      }).then(res => {
        if (res.status === 'ok') {
          showToast('Duyuru yayınlandı! Kullanıcılara en geç 60 sn içinde gösterilecek.', 'success');
          msgEl.value = '';
          loadAnnouncements();
        } else {
          showToast('Duyuru gönderilemedi: ' + (res.message || 'Bilinmeyen hata'), 'error');
        }
      }).catch(err => showToast('İstek başarısız: ' + (err.message || 'Bağlantı hatası'), 'error'));
    }

    function openUserDetail(username) {
      apiCall('/admin/api/users/detail?username=' + encodeURIComponent(username)).then(data => {
        if (data.status !== 'ok' || !data.detail) {
          showToast('Kullanıcı detayı alınamadı.', 'error');
          return;
        }
        renderUserDetail(data.detail);
      }).catch(err => showToast('İstek başarısız: ' + (err.message || 'Bağlantı hatası'), 'error'));
    }

    function detailChip(label, value, colorValue) {
      const chip = document.createElement('span');
      chip.style.display = 'inline-flex';
      chip.style.alignItems = 'center';
      chip.style.gap = '6px';
      chip.style.padding = '6px 10px';
      chip.style.borderRadius = '9px';
      chip.style.background = 'var(--surface-hover)';
      chip.style.border = '1px solid var(--border-stone)';
      chip.style.fontSize = '12px';
      chip.style.color = 'var(--text-muted)';
      chip.textContent = label + ': ';
      const strong = document.createElement('strong');
      strong.style.color = colorValue || 'var(--text-main)';
      strong.textContent = value;
      chip.appendChild(strong);
      return chip;
    }

    function fillDetailEmptyRow(tbody, columns, message) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = columns;
      td.textContent = message;
      td.style.textAlign = 'center';
      td.style.padding = '14px';
      td.style.color = 'var(--text-muted)';
      tr.appendChild(td);
      tbody.appendChild(tr);
    }

    function renderUserDetail(detail) {
      document.getElementById('userDetailTitle').textContent = 'Kullanıcı Detayı: ' + (detail.username || '');
      const summary = document.getElementById('userDetailSummary');
      while (summary.firstChild) summary.removeChild(summary.firstChild);
      summary.appendChild(detailChip('Rol', detail.role || '-'));
      summary.appendChild(detailChip('Durum', detail.is_active ? 'Aktif' : 'Askıya Alındı', detail.is_active ? 'var(--pine-light)' : 'var(--terracotta)'));
      summary.appendChild(detailChip('İsim', detail.display_name || '-'));
      summary.appendChild(detailChip('Son Sürüm', detail.client_version || 'Bilinmiyor'));
      summary.appendChild(detailChip('Son Görülme', detail.last_seen ? new Date(detail.last_seen * 1000).toLocaleString('tr-TR') : 'Hiç giriş yapmadı'));
      const rp = Array.isArray(detail.restricted_panels) ? detail.restricted_panels : [];
      summary.appendChild(detailChip('Kısıtlar', rp.length ? rp.join(', ') : 'Yok', rp.length ? 'var(--ochre-light)' : 'var(--pine-light)'));

      const sessions = detail.sessions || [];
      const sessBody = document.getElementById('userDetailSessions');
      while (sessBody.firstChild) sessBody.removeChild(sessBody.firstChild);
      if (!sessions.length) {
        fillDetailEmptyRow(sessBody, 5, 'Kayıtlı oturum yok.');
      } else {
        sessions.forEach(s => {
          const tr = document.createElement('tr');
          textCell(tr, s.created_at ? new Date(s.created_at * 1000).toLocaleString('tr-TR') : '-');
          textCell(tr, s.last_heartbeat ? new Date(s.last_heartbeat * 1000).toLocaleString('tr-TR') : '-');
          textCell(tr, s.client_version || '-');
          textCell(tr, s.platform || '-');
          const stCell = textCell(tr, s.is_revoked ? 'Kapatıldı' : 'Aktif');
          stCell.style.color = s.is_revoked ? 'var(--text-muted)' : 'var(--pine-light)';
          stCell.style.fontWeight = '600';
          sessBody.appendChild(tr);
        });
      }

      const errors = detail.errors || [];
      const errBody = document.getElementById('userDetailErrors');
      while (errBody.firstChild) errBody.removeChild(errBody.firstChild);
      if (!errors.length) {
        fillDetailEmptyRow(errBody, 5, 'Bu kullanıcıya ait hata kaydı yok.');
      } else {
        errors.forEach(e => {
          const tr = document.createElement('tr');
          const timeVal = e.last_seen || e.timestamp;
          textCell(tr, timeVal ? new Date(timeVal * 1000).toLocaleString('tr-TR') : '-');
          const typeCell = textCell(tr, e.exception_type || '-');
          typeCell.style.color = 'var(--terracotta)';
          typeCell.style.fontWeight = '600';
          const msg = String(e.exception_message || '');
          textCell(tr, msg.length > 48 ? (msg.substring(0, 48) + '...') : msg);
          textCell(tr, (e.occurrence_count || 1) + 'x');
          const stCell = textCell(tr, e.status === 'resolved' ? 'Çözüldü' : 'Açık');
          stCell.style.color = e.status === 'resolved' ? 'var(--pine-light)' : '#B91C1C';
          stCell.style.fontWeight = '600';
          errBody.appendChild(tr);
        });
      }

      const scripts = detail.scripts || [];
      const sBody = document.getElementById('userDetailScripts');
      while (sBody.firstChild) sBody.removeChild(sBody.firstChild);
      if (!scripts.length) {
        fillDetailEmptyRow(sBody, 3, 'Paylaşılan betik yok.');
      } else {
        scripts.forEach(s => {
          const tr = document.createElement('tr');
          textCell(tr, s.timestamp ? new Date(s.timestamp * 1000).toLocaleString('tr-TR') : '-');
          textCell(tr, s.project_name || '-');
          textCell(tr, ((s.size || 0) / 1024).toFixed(1) + ' KB');
          sBody.appendChild(tr);
        });
      }

      document.getElementById('userDetailModal').style.display = 'flex';
    }

    function closeUserDetail() {
      document.getElementById('userDetailModal').style.display = 'none';
    }

    function initTopoAnimation() {
      const canvas = document.getElementById('topoCanvas');
      if (!canvas || !canvas.getContext) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      let width = 0, height = 0;
      function resize() {
        if (typeof window === 'undefined') return;
        width = canvas.width = window.innerWidth || 1400;
        height = canvas.height = window.innerHeight || 900;
      }
      if (typeof window !== 'undefined') {
        window.addEventListener('resize', resize);
      }
      resize();

      const reducedMotion = (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
      const N = 16;
      const steps = 110;

      function renderFrame(time) {
        ctx.clearRect(0, 0, width, height);

        const t = time || 0;
        // Ultra-slow, serene geological undulation speeds
        const t1 = t * 0.00010;
        const t2 = t * 0.00007;
        const t3 = t * 0.00012;

        // Hypsometric azure spectrum (splash identity): deep sapphire index
        // contours on even levels, cyan intermediate contours on odd levels.
        const levelStyles = [
          { color: 'rgba(2, 132, 199, 0.20)', index: true },
          { color: 'rgba(6, 182, 212, 0.14)', index: false },
          { color: 'rgba(14, 165, 233, 0.18)', index: true },
          { color: 'rgba(56, 189, 248, 0.12)', index: false },
        ];

        for (let i = 0; i < N; i++) {
          const u = (i + 0.6) / (N + 0.8);
          const levelStyle = levelStyles[i % levelStyles.length];

          ctx.beginPath();
          ctx.lineWidth = levelStyle.index ? 1.35 : 0.85;
          ctx.strokeStyle = levelStyle.color;

          for (let s = 0; s <= steps; s++) {
            const nx = s / steps;
            const x = nx * width;

            // Strictly bounded wave components: sum of |A_m * beta_m| <= 0.28 < 1.0
            // Guarantees du/dy > 0 strictly across all x and t (zero intersections mathematically)
            const w1 = 0.048 * Math.sin(nx * 3.4 + t1 + u * 1.6);
            const w2 = 0.034 * Math.sin(nx * 5.8 - t2 + u * 2.2 + 0.8);
            const w3 = 0.022 * Math.cos(nx * 2.2 + t3 - u * 1.4 + 1.8);
            const ridge = 0.040 * Math.sin(nx * Math.PI) * (1.0 - Math.pow(2 * u - 1, 2)) * Math.sin(t1 * 0.75 + nx * 1.8);

            const delta = w1 + w2 + w3 + ridge;
            const y = height * (u + delta);

            if (s === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.stroke();
        }

        // Top-right natural peak summit (concentric elevation rings, strictly non-intersecting)
        const sx = width * 0.82;
        const sy = height * 0.22;
        const summitLevels = [18, 38, 64, 96, 134];
        for (let k = 0; k < summitLevels.length; k++) {
          const R = summitLevels[k];
          const isIndex = (k % 2 === 0);
          ctx.beginPath();
          ctx.lineWidth = isIndex ? 1.3 : 0.8;
          ctx.strokeStyle = isIndex ? 'rgba(2, 132, 199, 0.19)' : 'rgba(14, 165, 233, 0.12)';

          const ringSteps = 60;
          for (let s = 0; s <= ringSteps; s++) {
            const theta = (s / ringSteps) * Math.PI * 2;
            const warp = 1.0 + 0.10 * Math.sin(2 * theta + t1 * 1.2) + 0.06 * Math.cos(3 * theta - t2 * 0.9 + 1.0);
            const r = R * warp;
            const px = sx + r * Math.cos(theta);
            const py = sy + r * Math.sin(theta) * 0.85;
            if (s === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }
          ctx.closePath();
          ctx.stroke();
        }

        // Spot elevation peak dot
        ctx.beginPath();
        ctx.arc(sx, sy, 2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(3, 105, 161, 0.50)';
        ctx.fill();

        if (!reducedMotion && typeof requestAnimationFrame === 'function') {
          requestAnimationFrame(renderFrame);
        }
      }

      if (typeof requestAnimationFrame === 'function') {
        requestAnimationFrame(renderFrame);
      }
    }

    initTopoAnimation();
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
