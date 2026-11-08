"""Shared SQLite connection settings and process-wide writer serialization."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

SQLITE_BUSY_TIMEOUT_MS = 15_000
DB_LOCK = threading.RLock()


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection with the application's standard lock wait policy."""
    connection = sqlite3.connect(
        str(path), timeout=SQLITE_BUSY_TIMEOUT_MS / 1000
    )
    connection.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    return connection


def enable_wal(connection: sqlite3.Connection) -> str:
    """Enable WAL for a persistent local SQLite database, failing closed."""
    row = connection.execute("PRAGMA journal_mode=WAL").fetchone()
    mode = str(row[0] if row else "").lower()
    if mode != "wal":
        raise sqlite3.OperationalError(
            f"Unable to enable SQLite WAL journal mode (returned {mode or 'no result'})"
        )
    return mode
