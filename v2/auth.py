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

PASSWORD_MIN_LENGTH = 5
PASSWORD_MAX_BYTES = 1024
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_FAILURE_LIMIT = 5
LOGIN_ACCOUNT_FAILURE_LIMIT = 20
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
        raise ValueError("Password must be at least 5 characters and no more than 1024 UTF-8 bytes.")


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
                email_key_hash TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                window_started_at REAL NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
                updated_at REAL NOT NULL,
                PRIMARY KEY (email_key_hash, ip_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_updated
                ON login_attempts(updated_at);

            CREATE TABLE IF NOT EXISTS login_account_attempts (
                email_key_hash TEXT PRIMARY KEY,
                window_started_at REAL NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS google_oauth_identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subject TEXT NOT NULL UNIQUE,
                email_at_link TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_google_oauth_identities_user
                ON google_oauth_identities(user_id);

            CREATE TABLE IF NOT EXISTS google_oauth_states (
                state_hash TEXT PRIMARY KEY,
                nonce TEXT NOT NULL,
                code_verifier TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
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


def create_first_admin(db_path: Path, email: str, password: str) -> dict[str, Any]:
    """Atomically bootstrap the first administrator; concurrent attempts cannot create two."""
    normalized_email = _normalize_email(email)
    _validate_password(password)
    timestamp = _utc_iso()
    password_hash = _PASSWORD_HASHER.hash(password)
    try:
        with _connect(Path(db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role='admin'"
            ).fetchone()[0]
            if admin_count:
                raise ValueError("An administrator account already exists; bootstrap is disabled.")
            cursor = conn.execute(
                """INSERT INTO users
                   (email, email_normalized, password_hash, role, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'admin', 'active', ?, ?)""",
                (normalized_email, normalized_email, password_hash, timestamp, timestamp),
            )
            row = conn.execute(
                "SELECT id, email, role, status FROM users WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with that email already exists.") from exc
    return _safe_user(row)


def create_or_link_google_user(db_path: Path, email: str, subject: str) -> dict[str, Any]:
    """Link a verified Google identity or create a normal user, never an admin."""
    normalized_email = _normalize_email(email)
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
        raise ValueError("Google identity is invalid.")

    timestamp = _utc_iso()
    try:
        with _connect(Path(db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            identity = conn.execute(
                "SELECT user_id FROM google_oauth_identities WHERE subject=?",
                (subject,),
            ).fetchone()
            if identity:
                row = conn.execute(
                    "SELECT id, email, role, status FROM users WHERE id=?",
                    (int(identity["user_id"]),),
                ).fetchone()
                if row is None or row["status"] != "active":
                    raise ValueError("This Google account is not linked to an active account.")
                if row["email"].strip().lower() != normalized_email:
                    raise ValueError("This Google identity is already linked to another account.")
                return _safe_user(row)

            existing = conn.execute(
                "SELECT id, email, role, status FROM users WHERE email_normalized=?",
                (normalized_email,),
            ).fetchone()
            if existing and existing["status"] != "active":
                raise ValueError("This account is disabled.")
            if existing:
                user_id = int(existing["id"])
                row = existing
            else:
                password_hash = _PASSWORD_HASHER.hash(secrets.token_urlsafe(48))
                cursor = conn.execute(
                    """INSERT INTO users
                       (email, email_normalized, password_hash, role, status, created_at, updated_at)
                       VALUES (?, ?, ?, 'user', 'active', ?, ?)""",
                    (normalized_email, normalized_email, password_hash, timestamp, timestamp),
                )
                user_id = int(cursor.lastrowid)
                row = conn.execute(
                    "SELECT id, email, role, status FROM users WHERE id=?",
                    (user_id,),
                ).fetchone()

            conn.execute(
                """INSERT INTO google_oauth_identities(user_id, subject, email_at_link, created_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, subject, normalized_email, timestamp),
            )
            return _safe_user(row)
    except sqlite3.IntegrityError as exc:
        raise ValueError("This Google identity is already linked to another account.") from exc


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
    if not isinstance(email, str):
        raise ValueError("An email value is required for login throttling.")
    # Hash even malformed email values so invalid-address attempts are throttled
    # too, without storing a plaintext identifier for accounts that do not exist.
    normalized_email = email.strip().lower()[:254] or "<empty>"
    if not isinstance(client_ip, str) or not client_ip.strip():
        raise ValueError("A client IP address is required for login throttling.")
    return _token_hash(normalized_email), _token_hash(client_ip.strip())


def check_login_rate_limit(db_path: Path, email: str, client_ip: str) -> bool:
    email_key_hash, ip_hash = _rate_limit_identity(email, client_ip)
    now = time.time()
    with _connect(Path(db_path)) as conn:
        pair_row = conn.execute(
            """SELECT window_started_at, failed_attempts FROM login_attempts
               WHERE email_key_hash=? AND ip_hash=?""",
            (email_key_hash, ip_hash),
        ).fetchone()
        account_row = conn.execute(
            """SELECT window_started_at, failed_attempts FROM login_account_attempts
               WHERE email_key_hash=?""",
            (email_key_hash,),
        ).fetchone()
    pair_limited = bool(
        pair_row is not None
        and now - pair_row["window_started_at"] < LOGIN_WINDOW_SECONDS
        and pair_row["failed_attempts"] >= LOGIN_FAILURE_LIMIT
    )
    account_limited = bool(
        account_row is not None
        and now - account_row["window_started_at"] < LOGIN_WINDOW_SECONDS
        and account_row["failed_attempts"] >= LOGIN_ACCOUNT_FAILURE_LIMIT
    )
    return pair_limited or account_limited


def record_login_attempt(db_path: Path, email: str, client_ip: str, success: bool) -> None:
    email_key_hash, ip_hash = _rate_limit_identity(email, client_ip)
    now = time.time()
    with _connect(Path(db_path)) as conn:
        if success:
            # A successful account login clears failed attempts across all source IPs.
            conn.execute("DELETE FROM login_attempts WHERE email_key_hash=?", (email_key_hash,))
            conn.execute("DELETE FROM login_account_attempts WHERE email_key_hash=?", (email_key_hash,))
            return

        pair_row = conn.execute(
            """SELECT window_started_at FROM login_attempts
               WHERE email_key_hash=? AND ip_hash=?""",
            (email_key_hash, ip_hash),
        ).fetchone()
        if pair_row is None or now - pair_row["window_started_at"] >= LOGIN_WINDOW_SECONDS:
            conn.execute(
                """INSERT INTO login_attempts
                   (email_key_hash, ip_hash, window_started_at, failed_attempts, updated_at)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(email_key_hash, ip_hash) DO UPDATE SET
                     window_started_at=excluded.window_started_at,
                     failed_attempts=1,
                     updated_at=excluded.updated_at""",
                (email_key_hash, ip_hash, now, now),
            )
        else:
            conn.execute(
                """UPDATE login_attempts SET failed_attempts=failed_attempts+1, updated_at=?
                   WHERE email_key_hash=? AND ip_hash=?""",
                (now, email_key_hash, ip_hash),
            )

        account_row = conn.execute(
            "SELECT window_started_at FROM login_account_attempts WHERE email_key_hash=?",
            (email_key_hash,),
        ).fetchone()
        if account_row is None or now - account_row["window_started_at"] >= LOGIN_WINDOW_SECONDS:
            conn.execute(
                """INSERT INTO login_account_attempts
                   (email_key_hash, window_started_at, failed_attempts, updated_at)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(email_key_hash) DO UPDATE SET
                     window_started_at=excluded.window_started_at,
                     failed_attempts=1,
                     updated_at=excluded.updated_at""",
                (email_key_hash, now, now),
            )
        else:
            conn.execute(
                """UPDATE login_account_attempts SET failed_attempts=failed_attempts+1, updated_at=?
                   WHERE email_key_hash=?""",
                (now, email_key_hash),
            )


def begin_login_attempt(db_path: Path, email: str, client_ip: str) -> bool:
    """Atomically reserve per-IP and account-wide login attempts.

    Each email/IP pair gets five attempts and each account gets twenty attempts
    across all IPs per 15-minute window. Successful verification clears both scopes.
    """
    email_key_hash, ip_hash = _rate_limit_identity(email, client_ip)
    now = time.time()
    with _connect(Path(db_path)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        pair_row = conn.execute(
            """SELECT window_started_at, failed_attempts FROM login_attempts
               WHERE email_key_hash=? AND ip_hash=?""",
            (email_key_hash, ip_hash),
        ).fetchone()
        account_row = conn.execute(
            """SELECT window_started_at, failed_attempts FROM login_account_attempts
               WHERE email_key_hash=?""",
            (email_key_hash,),
        ).fetchone()

        pair_active = pair_row is not None and now - pair_row["window_started_at"] < LOGIN_WINDOW_SECONDS
        account_active = account_row is not None and now - account_row["window_started_at"] < LOGIN_WINDOW_SECONDS
        if pair_active and pair_row["failed_attempts"] >= LOGIN_FAILURE_LIMIT:
            return True
        if account_active and account_row["failed_attempts"] >= LOGIN_ACCOUNT_FAILURE_LIMIT:
            return True

        if pair_active:
            conn.execute(
                """UPDATE login_attempts SET failed_attempts=failed_attempts+1, updated_at=?
                   WHERE email_key_hash=? AND ip_hash=?""",
                (now, email_key_hash, ip_hash),
            )
        else:
            conn.execute(
                """INSERT INTO login_attempts
                   (email_key_hash, ip_hash, window_started_at, failed_attempts, updated_at)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(email_key_hash, ip_hash) DO UPDATE SET
                     window_started_at=excluded.window_started_at,
                     failed_attempts=1,
                     updated_at=excluded.updated_at""",
                (email_key_hash, ip_hash, now, now),
            )

        if account_active:
            conn.execute(
                """UPDATE login_account_attempts SET failed_attempts=failed_attempts+1, updated_at=?
                   WHERE email_key_hash=?""",
                (now, email_key_hash),
            )
        else:
            conn.execute(
                """INSERT INTO login_account_attempts
                   (email_key_hash, window_started_at, failed_attempts, updated_at)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(email_key_hash) DO UPDATE SET
                     window_started_at=excluded.window_started_at,
                     failed_attempts=1,
                     updated_at=excluded.updated_at""",
                (email_key_hash, now, now),
            )
    return False
