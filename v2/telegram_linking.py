"""Per-user Telegram account linking. Notification delivery is deliberately separate."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOKEN_TTL_SECONDS = 10 * 60


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init_schema(db_path: Path) -> None:
    with _connect(Path(db_path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS telegram_link_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                consumed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_telegram_link_tokens_expiry
                ON telegram_link_tokens(expires_at);
            CREATE TABLE IF NOT EXISTS user_telegram_chats (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                chat_id TEXT NOT NULL UNIQUE,
                chat_type TEXT NOT NULL,
                linked_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )


def create_link_token(db_path: Path, user_id: int, now: float | None = None) -> tuple[str, float]:
    timestamp = time.time() if now is None else float(now)
    token = secrets.token_urlsafe(32)
    expires_at = timestamp + TOKEN_TTL_SECONDS
    with _connect(Path(db_path)) as connection:
        connection.execute("DELETE FROM telegram_link_tokens WHERE expires_at < ? OR consumed_at IS NOT NULL OR user_id=?", (timestamp, int(user_id)))
        connection.execute(
            "INSERT INTO telegram_link_tokens(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
            (_hash(token), int(user_id), timestamp, expires_at),
        )
    return token, expires_at


def consume_link_token(
    db_path: Path, token: str, chat_id: str, chat_type: str = "private", now: float | None = None
) -> int | None:
    if not isinstance(token, str) or not 20 <= len(token) <= 128:
        return None
    if not isinstance(chat_id, str) or not chat_id.isdigit() or len(chat_id) > 32:
        return None
    if chat_type != "private":
        return None
    timestamp = time.time() if now is None else float(now)
    with _connect(Path(db_path)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM telegram_link_tokens WHERE expires_at <= ?", (timestamp,))
        row = connection.execute(
            "SELECT user_id FROM telegram_link_tokens WHERE token_hash=? AND consumed_at IS NULL AND expires_at>?",
            (_hash(token), timestamp),
        ).fetchone()
        if row is None:
            return None
        user_id = int(row["user_id"])
        try:
            connection.execute(
                "UPDATE telegram_link_tokens SET consumed_at=? WHERE token_hash=? AND consumed_at IS NULL",
                (timestamp, _hash(token)),
            )
            connection.execute(
                """INSERT INTO user_telegram_chats(user_id,chat_id,chat_type,linked_at,updated_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id,
                     chat_type=excluded.chat_type, updated_at=excluded.updated_at""",
                (user_id, chat_id, chat_type, timestamp, timestamp),
            )
        except sqlite3.IntegrityError:
            # A Telegram private chat can belong to only one Job Beeper account.
            raise ValueError("This Telegram account is already linked to another Job Beeper account.") from None
    return user_id


def get_connection(db_path: Path, user_id: int) -> dict[str, Any] | None:
    with _connect(Path(db_path)) as connection:
        row = connection.execute(
            "SELECT chat_type, linked_at, updated_at FROM user_telegram_chats WHERE user_id=?",
            (int(user_id),),
        ).fetchone()
    if row is None:
        return None
    return {"connected": True, "chat_type": row["chat_type"], "linked_at": row["linked_at"], "updated_at": row["updated_at"]}


def disconnect(db_path: Path, user_id: int) -> bool:
    with _connect(Path(db_path)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute("DELETE FROM user_telegram_chats WHERE user_id=?", (int(user_id),))
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        stamp = datetime.now(timezone.utc).isoformat()
        if "user_notification_settings" in tables:
            connection.execute(
                "UPDATE user_notification_settings SET enabled=0,enabled_at=NULL,updated_at=? WHERE user_id=?",
                (stamp, int(user_id)),
            )
        if "user_notification_ledger" in tables:
            connection.execute(
                "UPDATE user_notification_ledger SET status='cancelled',updated_at=? "
                "WHERE user_id=? AND status IN ('queued','failed','sending')",
                (stamp, int(user_id)),
            )
    return cursor.rowcount > 0
