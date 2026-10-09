"""Serpent Studio Control Plane & Administration Server.

Zero-dependency standard-library backend providing:
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

logger = logging.getLogger("serpent.control_plane")

DEFAULT_PORT = int(os.environ.get("PORT", os.environ.get("SERPENT_CONTROL_PLANE_PORT", 8080)))
DEFAULT_HOST = os.environ.get("SERPENT_CONTROL_PLANE_HOST", "0.0.0.0")
DB_PATH = os.environ.get("SERPENT_CONTROL_PLANE_DB", os.path.join(os.path.dirname(__file__), "control_plane.db"))

_ADMIN_DEFAULT_USER = os.environ.get("SERPENT_ADMIN_USER", "admin")
_ADMIN_DEFAULT_PASS = os.environ.get("SERPENT_ADMIN_PASS", "serpent2026")


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100000).hex()
    return hashed, salt


def verify_password(password: str, expected_hash: str, salt: str) -> bool:
    computed, _ = hash_password(password, salt)
    return hmac.compare_digest(computed, expected_hash)


class Database:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._lock, self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'tester',
                    display_name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    expires_at REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    client_version TEXT,
                    platform TEXT,
                    created_at REAL NOT NULL,
                    last_heartbeat REAL NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    app_version TEXT,
                    platform TEXT,
                    exception_type TEXT,
                    exception_message TEXT,
                    traceback TEXT,
                    active_tab TEXT,
                    recent_logs TEXT,
                    timestamp REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    project_name TEXT,
                    script_content TEXT,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

            # Ensure default superadmin exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (_ADMIN_DEFAULT_USER,))
            if not cursor.fetchone():
                h, s = hash_password(_ADMIN_DEFAULT_PASS)
                cursor.execute("""
                    INSERT INTO users (username, password_hash, salt, role, display_name, is_active, created_at)
                    VALUES (?, ?, ?, 'administrator', 'System Administrator', 1, ?)
                """, (_ADMIN_DEFAULT_USER, h, s, time.time()))
                conn.commit()

            # Ensure restricted_panels column exists
            cursor.execute("PRAGMA table_info(users)")
            cols = [r["name"] for r in cursor.fetchall()]
            if "restricted_panels" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN restricted_panels TEXT DEFAULT '[]'")
                conn.commit()

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
        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters."

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
            except sqlite3.IntegrityError:
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
            if not is_active:
                cur.execute("UPDATE sessions SET is_revoked = 1 WHERE username = ?", (username.strip().lower(),))
            conn.commit()
            return cur.rowcount > 0

    def reset_password(self, username: str, new_password: str) -> bool:
        h, s = hash_password(new_password)
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", (h, s, username.strip().lower()))
            conn.commit()
            return cur.rowcount > 0

    def delete_user(self, username: str) -> bool:
        if username.strip().lower() == _ADMIN_DEFAULT_USER.lower():
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
            cur.execute("""
                INSERT INTO error_reports
                (username, app_version, platform, exception_type, exception_message, traceback, active_tab, recent_logs, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, app_version, platform, exception_type, exception_message, traceback_str, active_tab, recent_logs, time.time()))
            conn.commit()
            return cur.lastrowid

    def list_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM error_reports ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def record_script(self, username: str, project_name: str, script_content: str) -> int:
        with self._lock, self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO scripts (username, project_name, script_content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (username, project_name, script_content, time.time()))
            conn.commit()
            return cur.lastrowid

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


class ControlPlaneHandler(http.server.BaseHTTPRequestHandler):
    db: Database

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, status_code: int, html_str: str) -> None:
        payload = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)
        except Exception:
            return {}

    def _get_bearer_token(self) -> str:
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        return ""

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.end_headers()

    def do_GET(self) -> None:
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
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_json_body()

        # Client Authentication Endpoint
        if path in ("/v1/auth/login", "/api/v1/auth/login"):
            username = str(body.get("username", "")).strip().lower()
            password = str(body.get("password", ""))
            client_version = str(body.get("client_version", ""))
            platform = str(body.get("platform", ""))

            user = self.db.get_user(username)
            if not user or not verify_password(password, user["password_hash"], user["salt"]):
                self._send_json(401, {"status": "error", "message": "Invalid username or password."})
                return

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

        # Client Error & Crash Report Endpoint
        if path == "/v1/telemetry/errors":
            token = self._get_bearer_token() or str(body.get("token", ""))
            valid, session_data = self.db.verify_and_touch_session(token)
            username = session_data["username"] if (valid and session_data) else str(body.get("username", "anonymous"))

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
            username = session_data["username"] if (valid and session_data) else str(body.get("username", "anonymous"))

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
            u = str(body.get("username", "")).strip().lower()
            p = str(body.get("password", ""))
            user = self.db.get_user(u)
            if user and user["role"] == "administrator" and verify_password(p, user["password_hash"], user["salt"]):
                adm_token = self.db.create_session(user["id"], user["username"], "web-admin", "browser")
                self._send_json(200, {"status": "ok", "token": adm_token, "username": user["username"]})
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
      --bg: #090D16;
      --card-bg: #111827;
      --border: #1F2937;
      --text: #F3F4F6;
      --text-muted: #9CA3AF;
      --accent: #38BDF8;
      --accent-hover: #0284C7;
      --danger: #EF4444;
      --danger-hover: #DC2626;
      --success: #10B981;
      --warning: #F59E0B;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; }
    .container { max-width: 1240px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
    h1 { font-size: 22px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
    .badge { font-size: 11px; padding: 3px 8px; border-radius: 99px; background: rgba(56, 189, 248, 0.15); color: var(--accent); }
    .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
    .tab-btn { background: var(--card-bg); border: 1px solid var(--border); color: var(--text-muted); padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s; }
    .tab-btn.active { background: var(--accent); color: #000; border-color: var(--accent); }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: middle; }
    th { color: var(--text-muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
    .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .status-active { background: var(--success); }
    .status-suspended { background: var(--danger); }
    button.btn { background: var(--accent); color: #000; border: none; padding: 8px 14px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s; }
    button.btn:hover { background: var(--accent-hover); }
    button.btn-danger { background: var(--danger); color: #fff; }
    button.btn-danger:hover { background: var(--danger-hover); }
    button.btn-warning { background: var(--warning); color: #000; }
    button.btn-secondary { background: #374151; color: #fff; }
    button.btn-secondary:hover { background: #4B5563; }
    button.btn-sm { padding: 4px 8px; font-size: 12px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; align-items: center; }
    input, select { background: #1F2937; border: 1px solid #374151; color: #fff; padding: 10px 14px; border-radius: 6px; font-size: 14px; outline: none; }
    input:focus { border-color: var(--accent); }
    pre { background: #000; padding: 12px; border-radius: 8px; color: #E5E7EB; font-size: 12px; overflow-x: auto; white-space: pre-wrap; max-height: 380px; }
    .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); justify-content: center; align-items: center; z-index: 1000; }
    .modal-content { background: var(--card-bg); border: 1px solid var(--border); padding: 24px; border-radius: 12px; max-width: 800px; width: 92%; max-height: 88vh; overflow-y: auto; }
    
    .pill-btn {
      display: inline-block;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: var(--accent);
      padding: 3px 10px;
      border-radius: 99px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      user-select: none;
    }
    .pill-btn:hover { background: var(--accent); color: #000; }
    
    .role-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
      transition: all 0.2s;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid rgba(56, 189, 248, 0.25);
    }
    .role-badge:hover { background: rgba(56, 189, 248, 0.3); border-color: var(--accent); }

    .restriction-pill {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 99px;
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.35);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .ok-pill {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 99px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.35);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .panel-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }
    .panel-card {
      background: #1F2937;
      border: 1px solid #374151;
      border-radius: 8px;
      padding: 12px;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      cursor: pointer;
      transition: border-color 0.2s, background 0.2s;
      user-select: none;
    }
    .panel-card:hover { border-color: var(--accent); }
    .panel-card.active-restricted {
      background: rgba(239, 68, 68, 0.12);
      border-color: rgba(239, 68, 68, 0.5);
    }
    .panel-card input[type="checkbox"] {
      margin-top: 3px;
      cursor: pointer;
      accent-color: var(--danger);
      width: 16px;
      height: 16px;
    }
    .panel-title { font-size: 13px; font-weight: 600; color: #F3F4F6; display: flex; align-items: center; gap: 6px; }
    .panel-desc { font-size: 11px; color: var(--text-muted); margin-top: 4px; line-height: 1.35; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>⚛️ Serpent Studio <span class="badge">Yönetim ve Telemetri Paneli</span></h1>
      <div id="authBox">
        <span id="adminName" style="margin-right: 12px; color: var(--accent);">Giriş Yapılmadı</span>
        <button class="btn btn-sm" onclick="logoutAdmin()">Çıkış</button>
      </div>
    </header>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('users')">👥 Kullanıcı Yönetimi & Testerlar</button>
      <button class="tab-btn" onclick="switchTab('errors')">🚨 Tester Hata & Çökme Raporları</button>
      <button class="tab-btn" onclick="switchTab('scripts')">📜 Çalıştırılan Serpent Betikleri</button>
    </div>

    <!-- USERS TAB -->
    <div id="tab-users">
      <div class="card">
        <h3>➕ Yeni Tester / Kullanıcı Oluştur (Uygulama Güncellemesi GEREKTİRMEZ)</h3>
        <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Buradan belirleyeceğiniz hesap ve şifre masaüstü uygulamasında anında geçerli olur.</p>
        
        <div class="form-row">
          <input type="text" id="newUsername" placeholder="Kullanıcı Adı (örn: tester_ali)" style="flex:1; min-width: 150px;">
          <input type="text" id="newPassword" placeholder="İlk Şifre (örn: 123456)" style="flex:1; min-width: 140px;">
          <input type="text" id="newDisplayName" placeholder="İsim (örn: Ali Mühendis)" style="flex:1; min-width: 150px;">
          <input type="text" id="newRole" placeholder="Rol / Keyword (örn: tester)" value="tester" style="flex:1; min-width: 150px;">
          <button class="btn" onclick="createUser()">Kullanıcıyı Kaydet</button>
        </div>

        <div style="display: flex; align-items: center; gap: 6px; margin-top: 10px; flex-wrap: wrap;">
          <span style="font-size: 12px; color: var(--text-muted);">Hızlı Rol / Keyword Seçin veya Yazın:</span>
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
        <h3>📋 Kayıtlı Kullanıcılar & Uzaktan Kısıtlama Denetimi</h3>
        <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Kullanıcıların erişebileceği panelleri buradan kısıtlayabilir veya hesaplarını anında askıya alabilirsiniz.</p>
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

    <!-- ERRORS TAB -->
    <div id="tab-errors" style="display: none;">
      <div class="card">
        <h3>🚨 Tester Hata ve İstisna Bildirimleri</h3>
        <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Arkadaşınızın test esnasında aldığı tüm unhandled exception ve çökmeler anlık olarak buraya düşer.</p>
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

    <!-- SCRIPTS TAB -->
    <div id="tab-scripts" style="display: none;">
      <div class="card">
        <h3>📜 Kullanıcıların Çalıştırdığı Serpent Betikleri</h3>
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

  <!-- MODAL: DETAIL (TRACEBACK / SCRIPT) -->
  <div class="modal" id="detailModal">
    <div class="modal-content">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 id="modalTitle">Detay</h3>
        <button class="btn btn-sm btn-danger" onclick="closeModal()">Kapat</button>
      </div>
      <pre id="modalBody"></pre>
    </div>
  </div>

  <!-- MODAL: PANEL RESTRICTIONS -->
  <div class="modal" id="restrictionsModal">
    <div class="modal-content">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
          <h3>🛡️ Panel ve Modül Kısıtlamaları</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 2px;">
            Kullanıcı: <strong id="modalRestrictUsername" style="color: var(--accent);"></strong>
          </p>
        </div>
        <button class="btn btn-sm btn-danger" onclick="closeRestrictionsModal()">Kapat</button>
      </div>

      <div style="background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 10px 14px; margin: 12px 0; font-size: 13px; color: #FCA5A5;">
        ⚠️ <strong>İşleyiş:</strong> İşaretlediğiniz paneller kullanıcının masaüstü uygulamasında anında devre dışı bırakılır ve gizlenir. Kullanıcı uygulamayı yeniden başlatmasa bile sonraki heartbeat (en geç 60 sn) ile canlı olarak güncellenir.
      </div>

      <!-- Quick Preset Buttons -->
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions([])">🔓 Tümünü Aç</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(ALL_PANEL_IDS)">🛑 Tümünü Kısıtla</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(['materials','assembly','geometry','control_rods','detectors','coefficients','simulation','settings','console'])">📊 Salt Okunur (Sadece Sonuç İnceleme)</button>
        <button class="btn btn-sm btn-secondary" onclick="setPresetRestrictions(['settings','console'])">🧪 Standart Tester (Ayarlar & Konsol Kilitli)</button>
      </div>

      <div class="panel-grid" id="panelGridContainer">
        <!-- Rendered dynamically -->
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; border-top: 1px solid var(--border); padding-top: 14px;">
        <button class="btn btn-secondary" onclick="closeRestrictionsModal()">İptal</button>
        <button class="btn" onclick="saveRestrictions()">💾 Kısıtlamaları Kaydet</button>
      </div>
    </div>
  </div>

  <script>
    let adminToken = localStorage.getItem('serpent_admin_token') || '';
    let currentRestrictUser = '';
    let usersCache = [];

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

    function checkAuth() {
      if (!adminToken) {
        const u = prompt("Yönetici Kullanıcı Adı:", "admin");
        const p = prompt("Yönetici Şifresi:", "serpent2026");
        if (u && p) {
          fetch('/admin/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
          }).then(r => r.json()).then(data => {
            if (data.status === 'ok') {
              adminToken = data.token;
              localStorage.setItem('serpent_admin_token', adminToken);
              document.getElementById('adminName').innerText = '👤 ' + data.username;
              loadAll();
            } else {
              alert("Giriş başarısız: " + data.message);
              checkAuth();
            }
          }).catch(() => alert("Sunucuya bağlanılamadı."));
        }
      } else {
        document.getElementById('adminName').innerText = '👤 Yönetici';
        loadAll();
      }
    }

    function logoutAdmin() {
      localStorage.removeItem('serpent_admin_token');
      adminToken = '';
      location.reload();
    }

    function switchTab(name) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      ['users', 'errors', 'scripts'].forEach(t => {
        document.getElementById('tab-' + t).style.display = (t === name) ? 'block' : 'none';
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

    function loadUsers() {
      apiCall('/admin/api/users').then(data => {
        usersCache = data.users || [];
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';
        if (!usersCache.length) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Kayıtlı kullanıcı yok.</td></tr>';
          return;
        }
        usersCache.forEach(u => {
          const isActive = !!u.is_active;
          const tr = document.createElement('tr');
          const lastSeenStr = u.last_seen ? new Date(u.last_seen * 1000).toLocaleString('tr-TR') : 'Hiç giriş yapmadı';
          const rPanels = Array.isArray(u.restricted_panels) ? u.restricted_panels : [];
          
          let restrictionsBadge = '';
          if (rPanels.length === 0) {
            restrictionsBadge = '<span class="ok-pill">✅ Tüm Paneller Açık</span>';
          } else {
            restrictionsBadge = `<span class="restriction-pill" title="${rPanels.join(', ')}">🛡️ ${rPanels.length} Panel Kısıtlı</span>`;
          }

          tr.innerHTML = `
            <td><strong>${u.username}</strong></td>
            <td>${u.display_name || '-'}</td>
            <td>
              <span class="role-badge" onclick="editUserRole('${u.username}', '${u.role}')" title="Rolü değiştirmek için tıklayın">
                🏷️ ${u.role} ✏️
              </span>
            </td>
            <td>
              <span class="status-dot ${isActive ? 'status-active' : 'status-suspended'}"></span>
              ${isActive ? '<span style="color:var(--success)">Aktif</span>' : '<span style="color:var(--danger)">Askıya Alındı</span>'}
            </td>
            <td>${restrictionsBadge}</td>
            <td>${lastSeenStr}</td>
            <td style="white-space: nowrap;">
              <button class="btn btn-sm" style="border: 1px solid var(--accent); background: rgba(56,189,248,0.12); color: var(--accent); margin-right: 4px;" onclick="openRestrictionsModal('${u.username}')">
                🛡️ Panelleri Kısıtla
              </button>
              <button class="btn btn-sm ${isActive ? 'btn-danger' : 'btn'}" style="margin-right: 4px;" onclick="toggleUser('${u.username}', ${!isActive})">
                ${isActive ? '🛑 Askıya Al' : '✅ Aktifleştir'}
              </button>
              <button class="btn btn-sm btn-warning" style="margin-right: 4px;" onclick="resetPass('${u.username}')">🔑 Şifre</button>
              ${u.username !== 'admin' ? `<button class="btn btn-sm btn-danger" onclick="deleteUser('${u.username}')">🗑️</button>` : ''}
            </td>
          `;
          tbody.appendChild(tr);
        });
      });
    }

    function createUser() {
      const username = document.getElementById('newUsername').value.trim();
      const password = document.getElementById('newPassword').value;
      const display_name = document.getElementById('newDisplayName').value.trim();
      const role = document.getElementById('newRole').value.trim() || 'tester';
      if (!username || !password) return alert("Kullanıcı adı ve şifre zorunludur!");

      apiCall('/admin/api/users/create', 'POST', { username, password, display_name, role }).then(res => {
        if (res.status === 'ok') {
          alert("Kullanıcı başarıyla oluşturuldu! Tester hemen masaüstü uygulamasından giriş yapabilir.");
          document.getElementById('newUsername').value = '';
          document.getElementById('newPassword').value = '';
          document.getElementById('newDisplayName').value = '';
          document.getElementById('newRole').value = 'tester';
          loadUsers();
        } else {
          alert("Hata: " + res.message);
        }
      });
    }

    function editUserRole(username, currentRole) {
      const newRole = prompt(`'${username}' kullanıcısı için yeni rol / keyword giriniz:`, currentRole);
      if (newRole && newRole.trim() && newRole.trim() !== currentRole) {
        apiCall('/admin/api/users/set-role', 'POST', { username, role: newRole.trim() }).then(res => {
          if (res.status === 'ok') {
            loadUsers();
          } else {
            alert("Rol güncellenemedi: " + (res.message || 'Bilinmeyen hata'));
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
          alert(`'${currentRestrictUser}' kullanıcısının panel yetkileri güncellendi (${selectedPanels.length} panel kısıtlandı). Masaüstü uygulamasında hemen geçerli olacaktır.`);
        } else {
          alert("Kısıtlamalar kaydedilemedi: " + (res.message || 'Bilinmeyen hata'));
        }
      });
    }

    function closeRestrictionsModal() {
      document.getElementById('restrictionsModal').style.display = 'none';
      currentRestrictUser = '';
    }

    function toggleUser(username, makeActive) {
      if (!confirm(`'${username}' kullanıcısının hesabını ${makeActive ? 'AKTİFLEŞTİRMEK' : 'ASKIYA ALMAK (TAM KISITLAMAK)'} istediğinizden emin misiniz?`)) return;
      apiCall('/admin/api/users/toggle-status', 'POST', { username, is_active: makeActive }).then(res => {
        loadUsers();
      });
    }

    function resetPass(username) {
      const newP = prompt(`'${username}' kullanıcısı için yeni şifreyi giriniz:`);
      if (!newP) return;
      apiCall('/admin/api/users/reset-password', 'POST', { username, password: newP }).then(res => {
        alert("Şifre güncellendi.");
      });
    }

    function deleteUser(username) {
      if (!confirm(`'${username}' kullanıcısını kalıcı olarak silmek istiyor musunuz?`)) return;
      apiCall('/admin/api/users/delete', 'POST', { username }).then(res => {
        loadUsers();
      });
    }

    function loadErrors() {
      apiCall('/admin/api/errors').then(data => {
        const tbody = document.getElementById('errorsTableBody');
        tbody.innerHTML = '';
        if (!data.errors || data.errors.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Henüz kaydedilmiş hata yok.</td></tr>';
          return;
        }
        data.errors.forEach(e => {
          const tr = document.createElement('tr');
          const timeStr = new Date(e.timestamp * 1000).toLocaleString('tr-TR');
          tr.innerHTML = `
            <td>${timeStr}</td>
            <td><strong>${e.username}</strong></td>
            <td style="color:var(--danger)"><strong>${e.exception_type}</strong></td>
            <td>${e.exception_message.substring(0, 50)}...</td>
            <td>${e.active_tab || '-'}</td>
            <td>${e.app_version || '-'}</td>
            <td><button class="btn btn-sm" onclick='showTraceback(${JSON.stringify(e)})'>🔍 Detay</button></td>
          `;
          tbody.appendChild(tr);
        });
      });
    }

    function showTraceback(e) {
      document.getElementById('modalTitle').innerText = `Hata: ${e.exception_type} (${e.username})`;
      document.getElementById('modalBody').innerText = `Kullanıcı: ${e.username}\nSürüm: ${e.app_version}\nPlatform: ${e.platform}\nAktif Sekme: ${e.active_tab}\nMesaj: ${e.exception_message}\n\n[TRACEBACK]:\n${e.traceback}\n\n[LOGLAR]:\n${e.recent_logs || '-'}`;
      document.getElementById('detailModal').style.display = 'flex';
    }

    function loadScripts() {
      apiCall('/admin/api/scripts').then(data => {
        const tbody = document.getElementById('scriptsTableBody');
        tbody.innerHTML = '';
        if (!data.scripts || data.scripts.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Kaydedilmiş betik yok.</td></tr>';
          return;
        }
        data.scripts.forEach(s => {
          const tr = document.createElement('tr');
          const timeStr = new Date(s.timestamp * 1000).toLocaleString('tr-TR');
          tr.innerHTML = `
            <td>${timeStr}</td>
            <td><strong>${s.username}</strong></td>
            <td>${s.project_name || '-'}</td>
            <td>${(s.size / 1024).toFixed(1)} KB</td>
            <td><button class="btn btn-sm" onclick="viewScript(${s.id})">📄 Betiği Gör</button></td>
          `;
          tbody.appendChild(tr);
        });
      });
    }

    function viewScript(id) {
      apiCall('/admin/api/script/' + id).then(data => {
        document.getElementById('modalTitle').innerText = "Serpent Girdi Betiği";
        document.getElementById('modalBody').innerText = data.content;
        document.getElementById('detailModal').style.display = 'flex';
      });
    }

    function closeModal() {
      document.getElementById('detailModal').style.display = 'none';
    }

    function loadAll() {
      loadUsers();
    }

    checkAuth();
  </script>
</body>
</html>
"""


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, db_path: str = DB_PATH) -> http.server.HTTPServer:
    db = Database(db_path)
    ControlPlaneHandler.db = db
    server = http.server.ThreadingHTTPServer((host, port), ControlPlaneHandler)
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
    print(f"👉  Default Admin  : admin / serpent2026", flush=True)
    print(f"👉  Database File  : {db_file}", flush=True)
    print(f"==================================================================", flush=True)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", flush=True)
        server.shutdown()
