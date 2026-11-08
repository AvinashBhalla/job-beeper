"""User-owned application records for the candidate job-search workflow."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v2.sqlite_store import DB_LOCK, connect as connect_sqlite

APPLICATION_STATUSES = frozenset({"Applied", "Interviewing", "Offer", "Rejected"})
MAX_NOTES_LENGTH = 2000
MAX_IMPORT_RECORDS = 500


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_applied_at(value: Any) -> str:
    if value is None or value == "":
        return _stamp()
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("applied_at must be an ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("applied_at must be an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _validate_status(value: Any) -> str:
    if value not in APPLICATION_STATUSES:
        raise ValueError("status must be Applied, Interviewing, Offer, or Rejected.")
    return value


def _validate_notes(value: Any) -> str:
    if not isinstance(value, str) or len(value) > MAX_NOTES_LENGTH:
        raise ValueError(f"notes must be text of at most {MAX_NOTES_LENGTH} characters.")
    return value


def init_schema(db_path: Path) -> None:
    with DB_LOCK, connect_sqlite(Path(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                -- Canonical groups are rebuilt during dedupe migrations; startup relinks via job_id.
                canonical_opportunity_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE RESTRICT,
                applied_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied'
                    CHECK(status IN ('Applied','Interviewing','Offer','Rejected')),
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, canonical_opportunity_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_applications_recent
            ON user_applications(user_id, applied_at DESC, id DESC)
        """)
        conn.commit()



def reconcile_canonical_ids(db_path: Path) -> int:
    """Relink saved applications after the shared dedupe identity is rebuilt."""
    changed = 0
    with DB_LOCK, connect_sqlite(Path(db_path)) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_applications'"
        ).fetchone()
        if not exists:
            return 0
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT a.id,a.user_id,a.job_id,a.applied_at,a.status,a.notes,a.created_at,a.updated_at,
                   j.canonical_opportunity_id
            FROM user_applications a JOIN jobs j ON j.id=a.job_id
            ORDER BY a.user_id,a.applied_at,a.id
        """).fetchall()
        for row in rows:
            if not conn.execute(
                "SELECT 1 FROM user_applications WHERE id=?", (row["id"],)
            ).fetchone():
                continue
            canonical_id = row["canonical_opportunity_id"]
            if canonical_id is None:
                continue
            duplicate = conn.execute("""
                SELECT id,applied_at,status,notes,created_at,updated_at
                FROM user_applications
                WHERE user_id=? AND canonical_opportunity_id=? AND id<>?
            """, (row["user_id"], int(canonical_id), row["id"])).fetchone()
            if duplicate is None:
                conn.execute(
                    "UPDATE user_applications SET canonical_opportunity_id=? WHERE id=?",
                    (int(canonical_id), row["id"]),
                )
                changed += 1
                continue

            keep_current = str(row["applied_at"]) <= str(duplicate["applied_at"])
            keep_id = int(row["id"] if keep_current else duplicate["id"])
            discard_id = int(duplicate["id"] if keep_current else row["id"])
            notes = list(dict.fromkeys(
                value for value in (str(row["notes"] or "").strip(), str(duplicate["notes"] or "").strip()) if value
            ))
            latest = row if str(row["updated_at"]) >= str(duplicate["updated_at"]) else duplicate
            applied_at = min(str(row["applied_at"]), str(duplicate["applied_at"]))
            created_at = min(str(row["created_at"]), str(duplicate["created_at"]))
            # Remove the competing unique key before changing the retained row.
            conn.execute("DELETE FROM user_applications WHERE id=?", (discard_id,))
            conn.execute("""UPDATE user_applications
                SET canonical_opportunity_id=?,applied_at=?,status=?,notes=?,created_at=?,updated_at=?
                WHERE id=?""", (
                int(canonical_id), applied_at, latest["status"], "\n\n".join(notes),
                created_at, _stamp(), keep_id,
            ))
            changed += 1
        conn.commit()
    return changed


def _application_query() -> str:
    return """
        SELECT a.id,a.user_id,a.job_id,a.canonical_opportunity_id,
               a.applied_at,a.status,a.notes,a.created_at,a.updated_at,
               j.title,j.company,j.location,j.url,j.source,
               COALESCE(e.score,0) AS score
        FROM user_applications a
        JOIN jobs j ON j.id=a.job_id
        LEFT JOIN user_job_evaluations e
          ON e.user_id=a.user_id AND e.job_id=a.job_id
    """


def get_for_user(
    db_path: Path, user_id: int, application_id: int
) -> dict[str, Any] | None:
    with connect_sqlite(Path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            _application_query() + " WHERE a.user_id=? AND a.id=?",
            (int(user_id), int(application_id)),
        ).fetchone()
    return dict(row) if row else None


def list_for_user(db_path: Path, user_id: int) -> list[dict[str, Any]]:
    with connect_sqlite(Path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            _application_query()
            + " WHERE a.user_id=? ORDER BY a.applied_at DESC,a.id DESC LIMIT 2000",
            (int(user_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def create(
    db_path: Path,
    user_id: int,
    job_id: int,
    *,
    applied_at: Any = None,
    status: Any = "Applied",
    notes: Any = "",
) -> tuple[dict[str, Any], bool]:
    job_id = int(job_id)
    timestamp = _stamp()
    applied_at_value = _normalize_applied_at(applied_at)
    status_value = _validate_status(status)
    notes_value = _validate_notes(notes)
    with DB_LOCK, connect_sqlite(Path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute(
            "SELECT canonical_opportunity_id FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        if job is None:
            raise LookupError("Job not found.")
        canonical_id = job["canonical_opportunity_id"]
        if canonical_id is None:
            raise ValueError("This job is not linked to a canonical opportunity yet.")
        cursor = conn.execute("""
            INSERT OR IGNORE INTO user_applications
              (user_id,canonical_opportunity_id,job_id,applied_at,status,notes,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            int(user_id), int(canonical_id), job_id, applied_at_value,
            status_value, notes_value, timestamp, timestamp,
        ))
        row = conn.execute(
            _application_query() + " WHERE a.user_id=? AND a.canonical_opportunity_id=?",
            (int(user_id), int(canonical_id)),
        ).fetchone()
        conn.commit()
    if row is None:
        raise RuntimeError("Application record could not be loaded after saving.")
    return dict(row), cursor.rowcount == 1


def update(
    db_path: Path,
    user_id: int,
    application_id: int,
    *,
    status: Any = None,
    notes: Any = None,
) -> dict[str, Any] | None:
    updates: list[str] = []
    values: list[Any] = []
    if status is not None:
        updates.append("status=?")
        values.append(_validate_status(status))
    if notes is not None:
        updates.append("notes=?")
        values.append(_validate_notes(notes))
    if not updates:
        raise ValueError("Provide status or notes to update.")
    updates.append("updated_at=?")
    values.extend((_stamp(), int(application_id), int(user_id)))
    with DB_LOCK, connect_sqlite(Path(db_path)) as conn:
        conn.execute(
            f"UPDATE user_applications SET {','.join(updates)} WHERE id=? AND user_id=?",
            values,
        )
        conn.commit()
    return get_for_user(db_path, user_id, application_id)


def delete(db_path: Path, user_id: int, application_id: int) -> bool:
    with DB_LOCK, connect_sqlite(Path(db_path)) as conn:
        cursor = conn.execute(
            "DELETE FROM user_applications WHERE id=? AND user_id=?",
            (int(application_id), int(user_id)),
        )
        conn.commit()
    return cursor.rowcount == 1


def import_legacy(
    db_path: Path, user_id: int, records: list[dict[str, Any]]
) -> dict[str, int]:
    if len(records) > MAX_IMPORT_RECORDS:
        raise ValueError(f"Import is limited to {MAX_IMPORT_RECORDS} records.")
    imported = already_present = skipped = 0
    timestamp = _stamp()
    with DB_LOCK, connect_sqlite(Path(db_path)) as conn:
        for item in records:
            if not isinstance(item, dict):
                skipped += 1
                continue
            try:
                job_id = int(item.get("job_id", item.get("id")))
                applied_at = _normalize_applied_at(item.get("applied_at"))
                status = _validate_status(item.get("status") or "Applied")
                notes = _validate_notes(item.get("notes") or "")
            except (TypeError, ValueError):
                skipped += 1
                continue
            job = conn.execute(
                "SELECT canonical_opportunity_id FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if job is None or job[0] is None:
                skipped += 1
                continue
            cursor = conn.execute("""
                INSERT OR IGNORE INTO user_applications
                  (user_id,canonical_opportunity_id,job_id,applied_at,status,notes,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
            """, (
                int(user_id), int(job[0]), job_id, applied_at,
                status, notes, timestamp, timestamp,
            ))
            if cursor.rowcount == 1:
                imported += 1
            else:
                already_present += 1
        conn.commit()
    return {
        "total": len(records),
        "imported": imported,
        "already_present": already_present,
        "skipped": skipped,
    }

