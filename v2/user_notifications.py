"""Opt-in, tenant-isolated Telegram job notifications."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from v2 import user_preferences

API = "https://api.telegram.org"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def init_schema(db_path: Path) -> None:
    with _connect(Path(db_path)) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_notification_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            enabled INTEGER NOT NULL DEFAULT 0,
            enabled_at TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_notification_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            canonical_opportunity_id INTEGER NOT NULL REFERENCES canonical_opportunities(id) ON DELETE CASCADE,
            candidate_job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'queued',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT,
            claimed_at TEXT,
            sent_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, canonical_opportunity_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_notification_due
          ON user_notification_ledger(status, next_attempt_at, created_at);
        """)


def get_settings(db_path: Path, user_id: int) -> dict[str, Any]:
    with _connect(Path(db_path)) as conn:
        row = conn.execute("SELECT enabled, enabled_at, updated_at FROM user_notification_settings WHERE user_id=?", (int(user_id),)).fetchone()
    return {"enabled": bool(row["enabled"]), "enabled_at": row["enabled_at"], "updated_at": row["updated_at"]} if row else {"enabled": False, "enabled_at": None, "updated_at": None}


def set_enabled(db_path: Path, user_id: int, enabled: bool) -> dict[str, Any]:
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean.")
    stamp = _stamp()
    with _connect(Path(db_path)) as conn:
        conn.execute("""INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at)
          VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
          enabled=excluded.enabled, enabled_at=excluded.enabled_at, updated_at=excluded.updated_at""",
          (int(user_id), int(enabled), stamp if enabled else None, stamp))
        if not enabled:
            conn.execute("UPDATE user_notification_ledger SET status='cancelled',updated_at=? WHERE user_id=? AND status IN ('queued','failed','sending')", (stamp, int(user_id)))
    return get_settings(db_path, user_id)


def _queue_new_matches(conn: sqlite3.Connection, user_id: int, enabled_at: str, matcher_rules_version: int = 3) -> int:
    prefs_row = conn.execute("SELECT preferences_json FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
    if not prefs_row:
        return 0
    try:
        prefs = json.loads(prefs_row["preferences_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        prefs = {}
    if not isinstance(prefs, dict):
        prefs = {}
    try:
        threshold = max(0, min(100, int(prefs.get("match_threshold", 55))))
    except (TypeError, ValueError):
        threshold = 55
    expected_fingerprint = user_preferences.preferences_fingerprint(
        {**user_preferences.PREFERENCE_DEFAULTS, **prefs}, matcher_rules_version
    )
    max_age_hours = max(1, min(720, int(prefs.get("max_age_hours", 72))))
    fresh_after = _stamp(_now() - timedelta(hours=max_age_hours))
    rows = conn.execute("""SELECT j.id,j.canonical_opportunity_id FROM jobs j
      JOIN user_job_evaluations e ON e.job_id=j.id AND e.user_id=?
      WHERE e.match=1 AND e.score>=? AND e.preference_fingerprint=?
        AND j.discovered_at>=? AND j.discovered_at>=?
        AND j.canonical_opportunity_id IS NOT NULL
      ORDER BY j.discovered_at,j.id""", (user_id, threshold, expected_fingerprint, enabled_at, fresh_after)).fetchall()
    stamp = _stamp()
    queued = 0
    for row in rows:
        cur = conn.execute("""INSERT OR IGNORE INTO user_notification_ledger
          (user_id,canonical_opportunity_id,candidate_job_id,status,created_at,updated_at)
          VALUES(?,?,?,'queued',?,?)""", (user_id, row["canonical_opportunity_id"], row["id"], stamp, stamp))
        queued += cur.rowcount
    return queued


def _claim_one(db_path: Path) -> dict[str, Any] | None:
    stamp = _stamp()
    with _connect(Path(db_path)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Recover claims left behind by a process restart before retrying them.
        stale = _stamp(_now() - timedelta(minutes=5))
        conn.execute("UPDATE user_notification_ledger SET status='queued',claimed_at=NULL,updated_at=? WHERE status='sending' AND claimed_at<?", (stamp, stale))
        row = conn.execute("""SELECT l.id,l.user_id,l.attempt_count,t.chat_id,j.title,j.company,j.location,j.url,
          j.source,j.discovered_at,e.score,e.reasons_json
          FROM user_notification_ledger l
          JOIN user_notification_settings s ON s.user_id=l.user_id AND s.enabled=1
          JOIN user_telegram_chats t ON t.user_id=l.user_id AND t.chat_type='private'
          JOIN jobs j ON j.id=l.candidate_job_id
          JOIN user_job_evaluations e ON e.user_id=l.user_id AND e.job_id=j.id
          WHERE l.status='queued' OR (l.status='failed' AND l.next_attempt_at IS NOT NULL AND l.next_attempt_at<=?)
          ORDER BY l.created_at,l.id LIMIT 1""", (stamp,)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE user_notification_ledger SET status='sending',claimed_at=?,attempt_count=attempt_count+1,updated_at=? WHERE id=?", (stamp, stamp, row["id"]))
        return dict(row)


def _still_deliverable(db_path: Path, item: dict[str, Any]) -> bool:
    with _connect(Path(db_path)) as conn:
        row = conn.execute("""SELECT 1 FROM user_notification_ledger l
          JOIN user_notification_settings s ON s.user_id=l.user_id AND s.enabled=1
          JOIN user_telegram_chats t ON t.user_id=l.user_id AND t.chat_type='private'
          WHERE l.id=? AND l.status='sending' AND t.chat_id=?""",
          (item["id"], item["chat_id"])).fetchone()
    return row is not None


def dispatch(db_path: Path, limit: int = 20, matcher_rules_version: int = 3) -> int:
    token = os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN", "")
    if not token:
        return 0
    sent = 0
    for _ in range(max(0, min(int(limit), 100))):
        # Queue only after explicit opt-in. enabled_at is the no-backlog boundary.
        with _connect(Path(db_path)) as conn:
            active = conn.execute("SELECT user_id,enabled_at FROM user_notification_settings WHERE enabled=1 AND enabled_at IS NOT NULL").fetchall()
            for setting in active:
                _queue_new_matches(conn, int(setting["user_id"]), setting["enabled_at"], matcher_rules_version)
        item = _claim_one(db_path)
        if item is None:
            break
        if not _still_deliverable(db_path, item):
            with _connect(Path(db_path)) as conn:
                conn.execute("UPDATE user_notification_ledger SET status='cancelled',updated_at=? WHERE id=? AND status='sending'", (_stamp(), item["id"]))
            continue
        text = (f"🚨 {int(item['score'])}% MATCH\n\n{item['title']}\nCompany: {item['company']}\n"
                f"📍 {item['location']}\nSource: {item['source']}\n\nApply → {item['url']}")
        try:
            response = requests.post(f"{API}/bot{token}/sendMessage", json={"chat_id": item["chat_id"], "text": text}, timeout=15)
            if response.status_code == 429 or response.status_code >= 500:
                raise RuntimeError(f"retryable Telegram HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise RuntimeError("Telegram rejected the message")
            stamp = _stamp()
            with _connect(Path(db_path)) as conn:
                conn.execute("UPDATE user_notification_ledger SET status='sent',sent_at=?,updated_at=?,last_error=NULL WHERE id=? AND status='sending'", (stamp, stamp, item["id"]))
            sent += 1
        except Exception as exc:
            attempt = int(item["attempt_count"]) + 1
            retryable = attempt < 6 and (not isinstance(exc, requests.HTTPError) or getattr(exc.response, "status_code", 0) >= 500)
            stamp = _stamp()
            retry_at = _stamp(_now() + timedelta(seconds=min(3600, 30 * (2 ** max(0, attempt - 1))))) if retryable else None
            with _connect(Path(db_path)) as conn:
                conn.execute("UPDATE user_notification_ledger SET status=?,next_attempt_at=?,last_error=?,updated_at=? WHERE id=? AND status='sending'",
                  ("failed" if retryable else "dead", retry_at, type(exc).__name__, stamp, item["id"]))
    return sent
