"""Persistent, conservative scheduling for explicitly configured ATS employer boards.

The scheduler stores one due time per employer board and one lease/cooldown per
request host. It deliberately allows at most one active board poll per host;
application-level dispatch limits total concurrent hosts separately.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from typing import Any
from urllib.parse import urlsplit

from v2 import board_discovery
from v2.recruitee import BOARD_NAME as RECRUITEE_BOARD_NAME
from v2.sqlite_store import DB_LOCK, connect

UTC = dt.timezone.utc
BOARD_CONFIG_KEYS = {
    "greenhouse": "greenhouse_boards",
    "ashby": "ashby_boards",
    "lever": "lever_boards",
    "workday": "workday_boards",
    "smartrecruiters": "smartrecruiters_boards",
    "workable": "workable_boards",
    "keka": "keka_boards",
    "darwinbox": "darwinbox_boards",
    "recruitee": "recruitee_boards",
}
BOARD_SCHEDULER_MAX_CONCURRENT_HOSTS = 3
BOARD_HOST_MIN_INTERVAL_SECONDS = 5
BOARD_LEASE_SECONDS = 15 * 60
BOARD_FAILURE_BACKOFF_BASE_SECONDS = 60
BOARD_FAILURE_BACKOFF_MAX_SECONDS = 15 * 60
RATE_LIMIT_BACKOFF_BASE_SECONDS = 5 * 60
RATE_LIMIT_BACKOFF_MAX_SECONDS = 60 * 60


def _iso(value: dt.datetime | None = None) -> str:
    value = value or dt.datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _workday_identity(url: str) -> tuple[str, str] | None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    match = re.fullmatch(r"(?P<tenant>[a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com", host)
    path = [part for part in parsed.path.split("/") if part]
    if not match or not path:
        return None
    return f"{match.group('tenant')}:{path[0]}".lower(), host


def _identity(source: str, board: dict[str, Any]) -> tuple[str, str] | None:
    """Return stable board key + host budget key for one allowlisted config entry."""
    if source == "greenhouse":
        key = str(board.get("token") or "").strip().lower()
        return (key, "boards-api.greenhouse.io") if key else None
    if source == "ashby":
        key = str(board.get("board") or "").strip().lower()
        return (key, "api.ashbyhq.com") if key else None
    if source == "recruitee":
        key = str(board.get("board") or "").strip().lower()
        return (key, f"{key}.recruitee.com") if RECRUITEE_BOARD_NAME.fullmatch(key) else None
    if source == "lever":
        site = str(board.get("site") or "").strip().lower()
        instance = str(board.get("instance") or "global").strip().lower()
        if not site or instance not in {"global", "eu"}:
            return None
        return f"{instance}:{site}", "api.eu.lever.co" if instance == "eu" else "api.lever.co"
    if source == "workday":
        value = _workday_identity(str(board.get("url") or ""))
        return value
    if source == "smartrecruiters":
        key = str(board.get("company_identifier") or board.get("identifier") or "").strip().lower()
        return (key, "api.smartrecruiters.com") if key else None
    if source == "workable":
        key = str(board.get("account") or board.get("subdomain") or "").strip().lower()
        return (key, "apply.workable.com") if key else None
    if source in {"keka", "darwinbox"}:
        url = str(board.get("careers_url") or board.get("url") or "").strip()
        detected = board_discovery.detect_ats_board(url) if url else None
        if not detected or detected.get("provider") != source:
            return None
        host = (urlsplit(str(detected.get("board_url") or url)).hostname or "").lower().rstrip(".")
        key = str(detected.get("board_key") or "").strip().lower()
        return (key, host) if key and host else None
    return None


def configured_boards(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize configured collector allowlists into scheduler records."""
    intervals = config.get("poll_seconds", {})
    entries: list[dict[str, Any]] = []
    enabled = config.get("source_enabled", {})
    for source, config_key in BOARD_CONFIG_KEYS.items():
        if not bool(enabled.get(source, False)):
            continue
        boards = config.get(config_key, [])
        if not isinstance(boards, list):
            continue
        interval = max(60, int(intervals.get(source, 600))) if isinstance(intervals, dict) else 600
        for board in boards:
            if not isinstance(board, dict):
                continue
            identity = _identity(source, board)
            if not identity:
                continue
            board_key, host_key = identity
            company = str(board.get("company") or "Unknown employer").strip()[:120]
            try:
                registry_id = int(board.get("registry_id")) if board.get("registry_id") not in (None, "") else None
            except (TypeError, ValueError):
                registry_id = None
            entries.append({
                "source": source,
                "config_key": config_key,
                "board_key": board_key,
                "host_key": host_key,
                "company_name": company,
                "registry_id": registry_id,
                "poll_interval_seconds": interval,
                "board_config": dict(board),
            })
    return entries


def init_schema(db_path: str) -> None:
    """Create additive scheduler state tables; existing source/job data is untouched."""
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ats_board_poll_schedule (
                source TEXT NOT NULL,
                board_key TEXT NOT NULL,
                config_key TEXT NOT NULL,
                board_config_json TEXT NOT NULL,
                registry_id INTEGER,
                company_name TEXT NOT NULL,
                host_key TEXT NOT NULL,
                poll_interval_seconds INTEGER NOT NULL,
                next_due_at TEXT NOT NULL,
                last_started_at TEXT,
                last_finished_at TEXT,
                last_outcome TEXT,
                last_error_type TEXT,
                last_jobs_seen INTEGER NOT NULL DEFAULT 0,
                last_jobs_new INTEGER NOT NULL DEFAULT 0,
                last_duration_seconds REAL,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                baseline_pending INTEGER NOT NULL DEFAULT 0,
                lease_until TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(source, board_key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ats_board_host_poll_state (
                host_key TEXT PRIMARY KEY,
                next_allowed_at TEXT,
                cooldown_until TEXT,
                lease_until TEXT,
                lease_source TEXT,
                lease_board_key TEXT,
                last_started_at TEXT,
                last_finished_at TEXT,
                last_outcome TEXT,
                http_429_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_board_poll_due ON ats_board_poll_schedule(is_active,next_due_at,lease_until)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_board_poll_host ON ats_board_poll_schedule(host_key,is_active)")
        conn.commit()


def sync_config(db_path: str, config: dict[str, Any], at: dt.datetime | None = None) -> int:
    """Sync configured boards, preserving poll history and failure backoff."""
    timestamp = _iso(at)
    entries = configured_boards(config)
    active_keys = {(item["source"], item["board_key"]) for item in entries}
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        for item in entries:
            source = item["source"]
            board_key = item["board_key"]
            existing = conn.execute(
                "SELECT is_active,next_due_at,last_finished_at,last_outcome "
                "FROM ats_board_poll_schedule WHERE source=? AND board_key=?",
                (source, board_key),
            ).fetchone()
            if existing:
                was_active = bool(existing[0])
                # Re-activation starts immediately with a fresh, silent baseline.
                if not was_active:
                    # Every reactivation is a new trust boundary, even when this
                    # provider has polled other employers successfully before.
                    conn.execute(
                        "UPDATE ats_board_poll_schedule SET next_due_at=?,baseline_pending=1,poll_interval_seconds=?,config_key=?,board_config_json=?,registry_id=?,company_name=?,host_key=?,is_active=1,lease_until=NULL,updated_at=? WHERE source=? AND board_key=?",
                        (timestamp, item["poll_interval_seconds"], item["config_key"], json.dumps(item["board_config"], sort_keys=True), item["registry_id"], item["company_name"], item["host_key"], timestamp, source, board_key),
                    )
                else:
                    next_due = existing[1]
                    # A tighter cadence can advance a healthy board's next poll.
                    # Failed polls keep their independently calculated backoff.
                    if existing[2] and existing[3] == "success":
                        on_new_cadence = dt.datetime.fromisoformat(existing[2]) + dt.timedelta(
                            seconds=item["poll_interval_seconds"]
                        )
                        next_due = min(next_due, _iso(on_new_cadence))
                    conn.execute(
                        "UPDATE ats_board_poll_schedule SET next_due_at=?,poll_interval_seconds=?,config_key=?,board_config_json=?,registry_id=?,company_name=?,host_key=?,updated_at=? WHERE source=? AND board_key=?",
                        (next_due, item["poll_interval_seconds"], item["config_key"], json.dumps(item["board_config"], sort_keys=True), item["registry_id"], item["company_name"], item["host_key"], timestamp, source, board_key),
                    )
            else:
                # Baseline belongs to the employer board, not its provider. A
                # provider's successful poll of Alpha says nothing about the
                # inventory age of newly added Beta.
                baseline_pending = True
                conn.execute("""
                    INSERT INTO ats_board_poll_schedule(
                        source,board_key,config_key,board_config_json,registry_id,company_name,
                        host_key,poll_interval_seconds,next_due_at,baseline_pending,is_active,
                        created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?)
                """, (
                    source, board_key, item["config_key"], json.dumps(item["board_config"], sort_keys=True),
                    item["registry_id"], item["company_name"], item["host_key"],
                    item["poll_interval_seconds"], timestamp, int(baseline_pending), timestamp, timestamp,
                ))
                conn.execute(
                    "INSERT OR IGNORE INTO ats_board_host_poll_state(host_key,updated_at) VALUES(?,?)",
                    (item["host_key"], timestamp),
                )
        rows = conn.execute("SELECT source,board_key FROM ats_board_poll_schedule WHERE is_active=1").fetchall()
        inactive = [(row[0], row[1]) for row in rows if (row[0], row[1]) not in active_keys]
        for source, board_key in inactive:
            conn.execute(
                "UPDATE ats_board_poll_schedule SET is_active=0,lease_until=NULL,updated_at=? WHERE source=? AND board_key=?",
                (timestamp, source, board_key),
            )
        # Ensure host rows exist for all currently configured boards.
        for host_key in {item["host_key"] for item in entries}:
            conn.execute(
                "INSERT OR IGNORE INTO ats_board_host_poll_state(host_key,updated_at) VALUES(?,?)",
                (host_key, timestamp),
            )
        conn.commit()
    return len(entries)


def claim_due_board(
    db_path: str,
    excluded_sources: set[str] | None = None,
    at: dt.datetime | None = None,
    lease_seconds: int = BOARD_LEASE_SECONDS,
) -> dict[str, Any] | None:
    """Atomically claim one due board and its host lease (one active poll per host)."""
    current = at or dt.datetime.now(UTC)
    now_text = _iso(current)
    lease_text = _iso(current + dt.timedelta(seconds=max(60, lease_seconds)))
    excluded_sources = excluded_sources or set()
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute("""
            SELECT b.source,b.board_key,b.config_key,b.board_config_json,b.registry_id,
                   b.company_name,b.host_key,b.poll_interval_seconds,b.baseline_pending
            FROM ats_board_poll_schedule b
            LEFT JOIN ats_board_host_poll_state h ON h.host_key=b.host_key
            WHERE b.is_active=1
              AND b.next_due_at<=?
              AND (b.lease_until IS NULL OR b.lease_until<=?)
              AND (h.lease_until IS NULL OR h.lease_until<=?)
              AND (h.cooldown_until IS NULL OR h.cooldown_until<=?)
              AND (h.next_allowed_at IS NULL OR h.next_allowed_at<=?)
            ORDER BY b.next_due_at ASC,b.source ASC,b.board_key ASC
            LIMIT 100
        """, (now_text, now_text, now_text, now_text, now_text)).fetchall()
        selected = None
        for row in rows:
            if row[0] in excluded_sources:
                continue
            selected = row
            break
        if selected is None:
            conn.commit()
            return None
        source, board_key, config_key, board_json, registry_id, company, host_key, interval, baseline = selected
        conn.execute(
            "UPDATE ats_board_poll_schedule SET lease_until=?,last_started_at=?,updated_at=? WHERE source=? AND board_key=?",
            (lease_text, now_text, now_text, source, board_key),
        )
        conn.execute("""
            INSERT INTO ats_board_host_poll_state(host_key,lease_until,lease_source,lease_board_key,last_started_at,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(host_key) DO UPDATE SET lease_until=excluded.lease_until,
                lease_source=excluded.lease_source,lease_board_key=excluded.lease_board_key,
                last_started_at=excluded.last_started_at,updated_at=excluded.updated_at
        """, (host_key, lease_text, source, board_key, now_text, now_text))
        conn.commit()
    try:
        board_config = json.loads(board_json)
    except (TypeError, json.JSONDecodeError):
        board_config = {}
    return {
        "source": source,
        "board_key": board_key,
        "config_key": config_key,
        "board_config": board_config if isinstance(board_config, dict) else {},
        "registry_id": registry_id,
        "company_name": company,
        "host_key": host_key,
        "poll_interval_seconds": int(interval),
        "baseline_pending": bool(baseline),
        "lease_until": lease_text,
    }


def release_claim(db_path: str, claim: dict[str, Any], at: dt.datetime | None = None) -> None:
    timestamp = _iso(at)
    with DB_LOCK, connect(db_path) as conn:
        conn.execute(
            "UPDATE ats_board_poll_schedule SET lease_until=NULL,updated_at=? WHERE source=? AND board_key=?",
            (timestamp, claim["source"], claim["board_key"]),
        )
        conn.execute(
            "UPDATE ats_board_host_poll_state SET lease_until=NULL,lease_source=NULL,lease_board_key=NULL,updated_at=? WHERE host_key=? AND lease_source=? AND lease_board_key=?",
            (timestamp, claim["host_key"], claim["source"], claim["board_key"]),
        )
        conn.commit()


def finish_poll(
    db_path: str,
    claim: dict[str, Any],
    *,
    outcome: str,
    jobs_seen: int = 0,
    jobs_new: int = 0,
    duration_seconds: float | None = None,
    error_type: str | None = None,
    cooldown_seconds: int | None = None,
    at: dt.datetime | None = None,
) -> dict[str, Any]:
    """Persist result, next due time, failure backoff and shared host cooldown."""
    finished = at or dt.datetime.now(UTC)
    finished_text = _iso(finished)
    source = claim["source"]
    board_key = claim["board_key"]
    host_key = claim["host_key"]
    with DB_LOCK, connect(db_path) as conn:
        row = conn.execute(
            "SELECT consecutive_failures,baseline_pending,poll_interval_seconds "
            "FROM ats_board_poll_schedule WHERE source=? AND board_key=?",
            (source, board_key),
        ).fetchone()
        interval = max(60, int(row[2] if row else claim["poll_interval_seconds"]))
        failures = int(row[0] or 0) if row else 0
        baseline_pending = bool(row[1]) if row else False
        rate_limited = outcome in {"rate_limited", "partial_rate_limited"}
        if outcome == "success":
            failures = 0
            retry_delay = interval
            baseline_pending = False
        elif rate_limited:
            failures += 1
            # A fixed Retry-After fallback makes a persistently throttled
            # employer board hit the same host every five minutes forever.
            # Escalate per board while retaining any longer provider-supplied
            # cooldown. The host lease then pauses only this API host, not
            # unrelated ATS providers or tenants on different hosts.
            requested_cooldown = max(60, int(cooldown_seconds or RATE_LIMIT_BACKOFF_BASE_SECONDS))
            adaptive_cooldown = min(
                RATE_LIMIT_BACKOFF_MAX_SECONDS,
                RATE_LIMIT_BACKOFF_BASE_SECONDS * (2 ** min(failures - 1, 5)),
            )
            effective_cooldown = max(requested_cooldown, adaptive_cooldown)
            retry_delay = max(interval, effective_cooldown)
        else:
            failures += 1
            retry_delay = min(
                interval,
                min(BOARD_FAILURE_BACKOFF_MAX_SECONDS,
                    BOARD_FAILURE_BACKOFF_BASE_SECONDS * (2 ** min(failures - 1, 4))),
            )
        next_due = _iso(finished + dt.timedelta(seconds=retry_delay))
        host_next = _iso(finished + dt.timedelta(seconds=BOARD_HOST_MIN_INTERVAL_SECONDS))
        cooldown_until = (
            _iso(finished + dt.timedelta(seconds=effective_cooldown))
            if rate_limited else None
        )
        conn.execute("""
            UPDATE ats_board_poll_schedule SET next_due_at=?,last_finished_at=?,last_outcome=?,
                last_error_type=?,last_jobs_seen=?,last_jobs_new=?,last_duration_seconds=?,
                consecutive_failures=?,baseline_pending=?,lease_until=NULL,updated_at=?
            WHERE source=? AND board_key=?
        """, (
            next_due, finished_text, outcome, error_type, max(0, int(jobs_seen)),
            max(0, int(jobs_new)), duration_seconds, failures, int(baseline_pending),
            finished_text, source, board_key,
        ))
        conn.execute("""
            INSERT INTO ats_board_host_poll_state(
                host_key,next_allowed_at,cooldown_until,lease_until,lease_source,
                lease_board_key,last_finished_at,last_outcome,http_429_count,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(host_key) DO UPDATE SET
                next_allowed_at=excluded.next_allowed_at,
                cooldown_until=CASE WHEN excluded.cooldown_until IS NOT NULL THEN excluded.cooldown_until
                                    WHEN ats_board_host_poll_state.cooldown_until<=excluded.last_finished_at THEN NULL
                                    ELSE ats_board_host_poll_state.cooldown_until END,
                lease_until=NULL,lease_source=NULL,lease_board_key=NULL,
                last_finished_at=excluded.last_finished_at,last_outcome=excluded.last_outcome,
                http_429_count=ats_board_host_poll_state.http_429_count+excluded.http_429_count,
                updated_at=excluded.updated_at
        """, (
            host_key, host_next, cooldown_until, None, None, None,
            finished_text, outcome, int(rate_limited), finished_text,
        ))
        conn.commit()
    return {
        "next_due_at": next_due,
        "consecutive_failures": failures,
        "baseline_pending": baseline_pending,
        "host_cooldown_until": cooldown_until,
    }


def status(db_path: str, limit: int = 500) -> dict[str, Any]:
    """Admin-safe scheduler telemetry; board identities only, no credentials."""
    limit = max(1, min(int(limit), 1000))
    with DB_LOCK, connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        boards = [dict(row) for row in conn.execute("""
            SELECT source,board_key,registry_id,company_name,host_key,poll_interval_seconds,
                   next_due_at,last_started_at,last_finished_at,last_outcome,last_error_type,
                   last_jobs_seen,last_jobs_new,last_duration_seconds,consecutive_failures,
                   baseline_pending,lease_until,is_active
            FROM ats_board_poll_schedule
            ORDER BY is_active DESC,next_due_at ASC,source ASC,board_key ASC LIMIT ?
        """, (limit,)).fetchall()]
        hosts = [dict(row) for row in conn.execute("""
            SELECT host_key,next_allowed_at,cooldown_until,lease_until,lease_source,
                   lease_board_key,last_started_at,last_finished_at,last_outcome,
                   http_429_count FROM ats_board_host_poll_state
            ORDER BY host_key ASC LIMIT ?
        """, (limit,)).fetchall()]
    return {
        "active_boards": sum(1 for row in boards if row["is_active"]),
        "inactive_boards": sum(1 for row in boards if not row["is_active"]),
        "max_concurrent_hosts": BOARD_SCHEDULER_MAX_CONCURRENT_HOSTS,
        "max_concurrent_boards_per_host": 1,
        "host_min_interval_seconds": BOARD_HOST_MIN_INTERVAL_SECONDS,
        "boards": boards,
        "hosts": hosts,
        "notes": [
            "Only explicitly configured collector allowlist boards are scheduled.",
            "Discovered, unmatched and merely verified boards are not polled until explicitly activated.",
            "At most one board poll per API host is active at a time; host cooldowns are persisted.",
            "Failed boards back off independently and do not block other hosts.",
        ],
    }
