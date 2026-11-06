"""SQLite-backed identity, password, session, and login-throttle primitives."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_BYTES = 1024
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_FAILURE_LIMIT = 5
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PASSWORD_HASHER = PasswordHasher()
_DUMMY_PASSWORD_HASH = _PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def _utc_iso(timestamp: float | None = None) -> str:
    value = time.time() if timestamp is None else timestamp
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValueError("A valid email address is required.")
    normalized = email.strip().lower()
    if len(normalized) > 254 or not _EMAIL_RE.fullmatch(normalized):
        raise ValueError("A valid email address is required.")
    return normalized


def _validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise ValueError("Password must be text.")
    size = len(password.encode("utf-8"))
    if len(password) < PASSWORD_MIN_LENGTH or size > PASSWORD_MAX_BYTES:
        raise ValueError("Password must be at least 12 characters and no more than 1024 UTF-8 bytes.")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _safe_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "email": str(row["email"]),
        "role": str(row["role"]),
        "status": str(row["status"]),
    }


def init_auth_schema(db_path: Path) -> None:
    """Create auth tables and indexes without altering existing application data."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                email_normalized TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                csrf_token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at REAL NOT NULL,
                last_seen_at TEXT NOT NULL,
                revoked_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user_active
                ON sessions(user_id, revoked_at, expires_at);

            CREATE TABLE IF NOT EXISTS login_attempts (
                email_normalized TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                window_started_at REAL NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
                updated_at REAL NOT NULL,
                PRIMARY KEY (email_normalized, ip_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_updated
                ON login_attempts(updated_at);
            """
        )


def create_user(
    db_path: Path,
    email: str,
    password: str,
    role: str = "user",
) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    _validate_password(password)
    if role not in {"admin", "user"}:
        raise ValueError("Role must be 'admin' or 'user'.")

    timestamp = _utc_iso()
    password_hash = _PASSWORD_HASHER.hash(password)
    try:
        with _connect(Path(db_path)) as conn:
            cursor = conn.execute(
                """INSERT INTO users
                   (email, email_normalized, password_hash, role, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'active', ?, ?)""",
                (normalized_email, normalized_email, password_hash, role, timestamp, timestamp),
            )
            row = conn.execute(
                "SELECT id, email, role, status FROM users WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with that email already exists.") from exc
    return _safe_user(row)


def verify_user(db_path: Path, email: str, password: str) -> dict[str, Any] | None:
    """Verify credentials with a dummy Argon2 hash for unknown email addresses."""
    try:
        normalized_email = _normalize_email(email)
    except ValueError:
        normalized_email = "invalid-email"

    with _connect(Path(db_path)) as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, role, status FROM users WHERE email_normalized=?",
            (normalized_email,),
        ).fetchone()

    encoded_hash = row["password_hash"] if row else _DUMMY_PASSWORD_HASH
    try:
        verified = _PASSWORD_HASHER.verify(encoded_hash, password if isinstance(password, str) else "")
    except (VerificationError, InvalidHashError, TypeError, ValueError):
        verified = False
    if not verified or row is None or row["status"] != "active":
        return None
    return _safe_user(row)


def create_session(
    db_path: Path,
    user_id: int,
    ttl_seconds: int = SESSION_TTL_SECONDS,
) -> tuple[str, str, str]:
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        raise ValueError("Session lifetime must be a positive number of seconds.")
    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + ttl_seconds
    created_at = _utc_iso(now)
    with _connect(Path(db_path)) as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE id=? AND status='active'", (user_id,)
        ).fetchone()
        if user is None:
            raise ValueError("An active user is required to create a session.")
        conn.execute(
            """INSERT INTO sessions
               (user_id, token_hash, csrf_token_hash, created_at, expires_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, _token_hash(session_token), _token_hash(csrf_token), created_at, expires_at, created_at),
        )
    return session_token, csrf_token, _utc_iso(expires_at)


def get_session_user(db_path: Path, session_token: str) -> dict[str, Any] | None:
    if not isinstance(session_token, str) or not session_token:
        return None
    with _connect(Path(db_path)) as conn:
        row = conn.execute(
            """SELECT u.id, u.email, u.role, u.status
               FROM sessions s JOIN users u ON u.id=s.user_id
               WHERE s.token_hash=? AND s.revoked_at IS NULL
                 AND s.expires_at>? AND u.status='active'""",
            (_token_hash(session_token), time.time()),
        ).fetchone()
    return _safe_user(row) if row else None


def revoke_session(db_path: Path, session_token: str) -> bool:
    if not isinstance(session_token, str) or not session_token:
        return False
    with _connect(Path(db_path)) as conn:
        cursor = conn.execute(
            "UPDATE sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
            (_utc_iso(), _token_hash(session_token)),
        )
    return cursor.rowcount == 1


def validate_csrf(db_path: Path, session_token: str, csrf_token: str) -> bool:
    if not isinstance(session_token, str) or not session_token:
        return False
    if not isinstance(csrf_token, str) or not csrf_token:
        return False
    with _connect(Path(db_path)) as conn:
        row = conn.execute(
            """SELECT s.csrf_token_hash
               FROM sessions s JOIN users u ON u.id=s.user_id
               WHERE s.token_hash=? AND s.revoked_at IS NULL
                 AND s.expires_at>? AND u.status='active'""",
            (_token_hash(session_token), time.time()),
        ).fetchone()
    return bool(row and hmac.compare_digest(row["csrf_token_hash"], _token_hash(csrf_token)))


def _rate_limit_identity(email: str, client_ip: str) -> tuple[str, str]:
    normalized_email = _normalize_email(email)
    if not isinstance(client_ip, str) or not client_ip.strip():
        raise ValueError("A client IP address is required for login throttling.")
    return normalized_email, _token_hash(client_ip.strip())


def check_login_rate_limit(db_path: Path, email: str, client_ip: str) -> bool:
    normalized_email, ip_hash = _rate_limit_identity(email, client_ip)
    now = time.time()
    with _connect(Path(db_path)) as conn:
        row = conn.execute(
            """SELECT window_started_at, failed_attempts FROM login_attempts
               WHERE email_normalized=? AND ip_hash=?""",
            (normalized_email, ip_hash),
        ).fetchone()
    if row is None or now - row["window_started_at"] >= LOGIN_WINDOW_SECONDS:
        return False
    return row["failed_attempts"] >= LOGIN_FAILURE_LIMIT


def record_login_attempt(
    db_path: Path,
    email: str,
    client_ip: str,
    success: bool,
) -> None:
    normalized_email, ip_hash = _rate_limit_identity(email, client_ip)
    now = time.time()
    with _connect(Path(db_path)) as conn:
        if success:
            conn.execute(
                "DELETE FROM login_attempts WHERE email_normalized=? AND ip_hash=?",
                (normalized_email, ip_hash),
            )
            return
        row = conn.execute(
            """SELECT window_started_at, failed_attempts FROM login_attempts
               WHERE email_normalized=? AND ip_hash=?""",
            (normalized_email, ip_hash),
        ).fetchone()
        if row is None or now - row["window_started_at"] >= LOGIN_WINDOW_SECONDS:
            conn.execute(
                """INSERT INTO login_attempts
                   (email_normalized, ip_hash, window_started_at, failed_attempts, updated_at)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(email_normalized, ip_hash) DO UPDATE SET
                     window_started_at=excluded.window_started_at,
                     failed_attempts=1,
                     updated_at=excluded.updated_at""",
                (normalized_email, ip_hash, now, now),
            )
        else:
            conn.execute(
                """UPDATE login_attempts SET failed_attempts=failed_attempts+1, updated_at=?
                   WHERE email_normalized=? AND ip_hash=?""",
                (now, normalized_email, ip_hash),
            )
