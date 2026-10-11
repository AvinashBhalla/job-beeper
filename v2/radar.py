from __future__ import annotations

import asyncio
import datetime as dt
from email.utils import parsedate_to_datetime
import hashlib
import html as html_lib
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
import warnings
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from v2.dedupe import auto_link_allowed, canonical_identity, canonical_match_score, canonicalize_url

ROOT = Path(__file__).resolve().parent
DASHBOARD_PATH = ROOT.parent / "dashboard"
DB_PATH = Path(os.getenv("JOB_RADAR_DB", ROOT / "jobs.db"))
DEFAULT_CONFIG_PATH = ROOT / "config.json"
RUNTIME_CONFIG_PATH = DB_PATH.parent / "config.json"
CONFIG_TOKEN_PATH = DB_PATH.parent / "config_token"
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("job-radar")

UTC = dt.timezone.utc
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

# Keep LinkedIn requests paced and honor HTTP 429 with an escalating global cooldown.
LINKEDIN_MIN_REQUEST_INTERVAL_SECONDS = 1.5
LINKEDIN_RATE_LIMIT_BASE_COOLDOWN_SECONDS = 300
LINKEDIN_RATE_LIMIT_MAX_COOLDOWN_SECONDS = 1800
LINKEDIN_DETAIL_WORKERS = 4
LINKEDIN_FAST_TARGETS_PER_SCAN = 4
LINKEDIN_DEEP_SCAN_SECONDS = 900
LINKEDIN_DEEP_PAGE_BATCH = 1
LINKEDIN_FAST_TPR = "r21600"
LINKEDIN_DEEP_TPR = "r21600"

app = FastAPI(title="Job Radar V2", version="2.0.0")

cors_origins = [
    origin.strip()
    for origin in os.getenv("JOB_RADAR_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "PUT", "OPTIONS"],
    allow_headers=["*"],
)
db_lock = threading.Lock()
started = time.monotonic()
source_state: dict[str, dict[str, Any]] = {}
linkedin_last_deep_scan_at: str | None = None
linkedin_fast_target_cursor = 0
linkedin_http_lock = threading.Lock()
linkedin_last_http_request_monotonic = 0.0
linkedin_rate_limited_until_monotonic = 0.0
linkedin_rate_limit_streak = 0
linkedin_rate_limit_generation = 0
stop_event = asyncio.Event()
config_lock = threading.RLock()





def _default_config() -> dict[str, Any]:
    return json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


def _merge_config(defaults: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(defaults))
    merged.update(current)
    current_version = int(current.get("config_version", 1) or 1)
    default_version = int(defaults.get("config_version", 1) or 1)
    merged["config_version"] = max(current_version, default_version)

    # Version 3 made Instahyre opt-in. Version 4 re-applied that safe
    # default for runtimes created before this policy was made explicit.
    if current_version < 4 <= default_version:
        merged.setdefault("source_enabled", {})["instahyre"] = False

    # Version 5 repairs persisted source-query configuration. Query families
    # are repository-owned, not exposed by the preferences UI, so stale
    # runtime query sets must not silently reduce fresh-job coverage.
    if current_version < 5 <= default_version:
        merged["linkedin_queries"] = json.loads(
            json.dumps(defaults.get("linkedin_queries", []))
        )
        merged["naukri_queries"] = json.loads(
            json.dumps(defaults.get("naukri_queries", []))
        )

    # Version 6 temporarily requires explicit captured experience for Telegram
    # alerts. LinkedIn public guest pages can omit poster-added requirements,
    # so unknown-experience jobs stay visible in the dashboard but do not alert.
    if current_version < 6 <= default_version:
        merged["require_explicit_experience_for_alerts"] = True

    # Version 7 adds Greenhouse as an opt-in structured ATS source. Existing
    # runtimes must not start querying/alerting from it without an explicit opt-in.
    if current_version < 7 <= default_version:
        merged.setdefault("source_enabled", {})["greenhouse"] = False

    if isinstance(defaults.get("poll_seconds"), dict):
        merged["poll_seconds"] = {
            **defaults.get("poll_seconds", {}),
            **current.get("poll_seconds", {}),
        }
    if isinstance(defaults.get("source_enabled"), dict):
        merged["source_enabled"] = {
            **defaults.get("source_enabled", {}),
            **current.get("source_enabled", {}),
        }
        # Source-disable migrations must be applied after merging persisted
        # settings; otherwise the old runtime value can overwrite the safe
        # repository default during migration.
        if current_version < 4 <= default_version:
            merged["source_enabled"]["instahyre"] = False
        if current_version < 7 <= default_version:
            merged["source_enabled"]["greenhouse"] = False
    return merged


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise HTTPException(status_code=422, detail="Configuration must be a JSON object.")

    for key in ("target_roles", "skills", "locations", "title_exclude", "excluded_role_terms"):
        value = config.get(key)
        if value is None:
            config[key] = []
            continue
        if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
            raise HTTPException(status_code=422, detail=f"{key} must be a list of non-empty strings.")
        config[key] = [x.strip() for x in value]

    if not config["target_roles"]:
        raise HTTPException(status_code=422, detail="At least one target role is required.")
    if not config["locations"]:
        raise HTTPException(status_code=422, detail="At least one target location is required.")

    for key in ("candidate_experience_years", "min_experience_years"):
        value = config.get(key)
        if value is not None:
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail=f"{key} must be a number or null.")
            if number < 0 or number > 30:
                raise HTTPException(status_code=422, detail=f"{key} must be between 0 and 30.")
            config[key] = number

    try:
        max_experience = float(config.get("max_experience_years", 3))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="max_experience_years must be a number.")
    if max_experience < 0 or max_experience > 30:
        raise HTTPException(status_code=422, detail="max_experience_years must be between 0 and 30.")
    config["max_experience_years"] = max_experience

    if config.get("min_experience_years") is not None and config["min_experience_years"] > max_experience:
        raise HTTPException(status_code=422, detail="Minimum job experience cannot exceed maximum experience.")

    threshold = int(config.get("match_threshold", 55))
    if not 0 <= threshold <= 100:
        raise HTTPException(status_code=422, detail="match_threshold must be between 0 and 100.")
    config["match_threshold"] = threshold

    try:
        max_age_hours = int(config.get("max_age_hours", 72))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="max_age_hours must be an integer.")
    if not 1 <= max_age_hours <= 720:
        raise HTTPException(status_code=422, detail="max_age_hours must be between 1 and 720 hours.")
    config["max_age_hours"] = max_age_hours

    for key in ("remote_only", "notifications_enabled", "require_explicit_experience_for_alerts"):
        config[key] = bool(config.get(key, False))

    greenhouse_boards = config.get("greenhouse_boards", [])
    if not isinstance(greenhouse_boards, list):
        raise HTTPException(status_code=422, detail="greenhouse_boards must be a list.")
    if len(greenhouse_boards) > 50:
        raise HTTPException(status_code=422, detail="greenhouse_boards cannot contain more than 50 boards.")
    normalized_boards: list[dict[str, str]] = []
    seen_board_tokens: set[str] = set()
    for board in greenhouse_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each greenhouse board must be an object.")
        token = board.get("token")
        company = board.get("company")
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", token.strip()):
            raise HTTPException(status_code=422, detail="Each greenhouse board requires a valid public board token.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each greenhouse board requires a company label of at most 120 characters.")
        token = token.strip()
        if token.lower() in seen_board_tokens:
            raise HTTPException(status_code=422, detail=f"Duplicate Greenhouse board token: {token}.")
        seen_board_tokens.add(token.lower())
        normalized_boards.append({"token": token, "company": company.strip()})
    config["greenhouse_boards"] = normalized_boards

    source_enabled = config.get("source_enabled", {})
    if not isinstance(source_enabled, dict):
        raise HTTPException(status_code=422, detail="source_enabled must be an object.")
    config["source_enabled"] = {
        "linkedin": bool(source_enabled.get("linkedin", True)),
        "naukri": bool(source_enabled.get("naukri", True)),
        "instahyre": bool(source_enabled.get("instahyre", True)),
        "greenhouse": bool(source_enabled.get("greenhouse", False)),
    }

    poll_seconds = config.get("poll_seconds", {})
    if not isinstance(poll_seconds, dict):
        raise HTTPException(status_code=422, detail="poll_seconds must be an object.")
    config["poll_seconds"] = {
        name: max(60, int(poll_seconds.get(name, default)))
        for name, default in {
            "linkedin": 60,
            "naukri": 300,
            "instahyre": 600,
            "greenhouse": 900,
        }.items()
    }

    return config


def ensure_runtime_config() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    defaults = _default_config()
    if RUNTIME_CONFIG_PATH.exists():
        try:
            current = json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = {}
    else:
        current = {}
    merged = validate_config(_merge_config(defaults, current))
    serialized = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"
    if not RUNTIME_CONFIG_PATH.exists() or RUNTIME_CONFIG_PATH.read_text(encoding="utf-8") != serialized:
        tmp = RUNTIME_CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(serialized, encoding="utf-8")
        os.replace(tmp, RUNTIME_CONFIG_PATH)


def get_config() -> dict[str, Any]:
    with config_lock:
        ensure_runtime_config()
        return json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict[str, Any]) -> dict[str, Any]:
    validated = validate_config(_merge_config(_default_config(), config))
    with config_lock:
        tmp = RUNTIME_CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(validated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, RUNTIME_CONFIG_PATH)
    return validated


def ensure_config_token() -> None:
    if os.getenv("JOB_RADAR_CONFIG_TOKEN"):
        return
    if CONFIG_TOKEN_PATH.exists():
        return
    CONFIG_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    CONFIG_TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    CONFIG_TOKEN_PATH.chmod(0o600)


def get_config_token() -> str:
    return os.getenv("JOB_RADAR_CONFIG_TOKEN") or CONFIG_TOKEN_PATH.read_text(encoding="utf-8").strip()


def authorize_config_update(provided_token: str | None) -> None:
    if not provided_token or not secrets.compare_digest(provided_token, get_config_token()):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Config-Token.")


IST = ZoneInfo("Asia/Kolkata")


def now() -> dt.datetime:
    return dt.datetime.now(UTC)


def current_day_start_utc() -> dt.datetime:
    local_now = now().astimezone(IST)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(UTC)


def iso(value: dt.datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value else None


def parse_relative(value: str | float | int | None, base: dt.datetime | None = None) -> dt.datetime | None:
    if value is None or value == "":
        return None
    base = base or now()
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 1e11:
            timestamp /= 1000
        try:
            return dt.datetime.fromtimestamp(timestamp, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    raw_text = str(value).strip()
    text = raw_text.lower()
    if text in {"just now", "now", "today"}:
        return base
    if text == "yesterday":
        return base - dt.timedelta(days=1)
    m = re.search(r"(\d+)\s*(minute|min|hour|hr|day|week)s?\s*(?:ago)?", text)
    if not m:
        try:
            iso_text = (
                raw_text[:-1] + "+00:00"
                if raw_text.endswith(("Z", "z"))
                else raw_text
            )
            parsed = dt.datetime.fromisoformat(iso_text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    amount = int(m.group(1))
    seconds = {
        "minute": 60, "min": 60, "hour": 3600, "hr": 3600,
        "day": 86400, "week": 604800
    }[m.group(2)]
    return base - dt.timedelta(seconds=amount * seconds)


def normalize_job(source: str, source_id: str, company: str, title: str,
                  location: str, url: str, posted_at: dt.datetime | None,
                  posted_precision: str, description: str = "") -> dict[str, Any]:
    discovered = now()
    if posted_at is not None:
        comparable_posted_at = posted_at
        if comparable_posted_at.tzinfo is None:
            comparable_posted_at = comparable_posted_at.replace(tzinfo=UTC)
        if comparable_posted_at.astimezone(UTC) > discovered:
            # Some source "just now" labels can resolve later than first discovery.
            # Keep the discovery time authoritative rather than showing a future post.
            posted_at = None
            posted_precision = "unknown"
    return {
        "source": source,
        "source_job_id": str(source_id),
        "company": (company or "").strip(),
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "url": (url or "").strip(),
        "source_posted_at": iso(posted_at),
        "posted_precision": posted_precision,
        "discovered_at": iso(discovered),
        "discovery_latency_seconds": (
            max(0, int((discovered - posted_at).total_seconds()))
            if posted_at and posted_precision == "minute" else None
        ),
        "description": description or "",
    }


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _job_for_canonical(conn: sqlite3.Connection, job_id: int) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def _candidate_canonical_groups(conn: sqlite3.Connection, job: dict[str, Any]) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    identity = canonical_identity(job)
    if identity["url_norm"]:
        rows = conn.execute("""
            SELECT co.id, co.canonical_url, co.company_norm, co.title_norm, co.location_norm,
                   j.id AS representative_job_id, j.source AS representative_source,
                   j.company, j.title, j.location, j.url,
                   j.description, j.source_posted_at, j.discovered_at
            FROM canonical_opportunities co
            JOIN jobs j ON j.id = co.representative_job_id
            WHERE co.canonical_url=?
            LIMIT 20
        """, (identity["url_norm"],)).fetchall()
        if rows:
            return [dict(row) for row in rows]

    rows = conn.execute("""
        SELECT co.id, co.canonical_url, co.company_norm, co.title_norm, co.location_norm,
               j.id AS representative_job_id, j.source AS representative_source,
               j.company, j.title, j.location, j.url,
               j.description, j.source_posted_at, j.discovered_at
        FROM canonical_opportunities co
        JOIN jobs j ON j.id = co.representative_job_id
        WHERE co.company_norm=? AND co.location_norm=?
        ORDER BY co.last_seen_at DESC
        LIMIT 100
    """, (identity["company_norm"], identity["location_norm"])).fetchall()
    return [dict(row) for row in rows]


def _create_canonical_group(
    conn: sqlite3.Connection,
    job_id: int,
    job: dict[str, Any],
    method: str,
    confidence: int,
    notification_state: str = "pending",
) -> int:
    identity = canonical_identity(job)
    canonical_url = identity["url_norm"] or None
    cur = conn.execute("""
        INSERT INTO canonical_opportunities (
            canonical_url, company_norm, title_norm, location_norm,
            representative_job_id, first_seen_at, last_seen_at, identity_version
        ) VALUES (?,?,?,?,?,?,?,2)
    """, (
        canonical_url,
        identity["company_norm"],
        identity["title_norm"],
        identity["location_norm"],
        job_id,
        job["discovered_at"],
        job["discovered_at"],
    ))
    canonical_id = int(cur.lastrowid)
    conn.execute("""
        UPDATE jobs
        SET canonical_opportunity_id=?,
            canonical_match_method=?,
            canonical_match_confidence=?
        WHERE id=?
    """, (canonical_id, method, confidence, job_id))
    _ensure_notification_state(conn, canonical_id, notification_state)
    return canonical_id


def _assign_canonical(
    conn: sqlite3.Connection,
    job_id: int,
    notification_state: str = "pending",
) -> tuple[int, str, int]:
    job = _job_for_canonical(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} does not exist")

    existing_id = job.get("canonical_opportunity_id")
    if existing_id:
        conn.execute(
            "UPDATE canonical_opportunities SET last_seen_at=? WHERE id=?",
            (job["last_seen_at"], existing_id),
        )
        return int(existing_id), job.get("canonical_match_method") or "existing", int(job.get("canonical_match_confidence") or 0)

    best_id = None
    best_score = 0
    best_method = "none"
    best_representative = None
    identity = canonical_identity(job)
    for candidate in _candidate_canonical_groups(conn, job):
        candidate_source = candidate.get("representative_source")
        same_source = candidate_source and candidate_source == job.get("source")
        same_canonical_url = bool(identity["url_norm"]) and candidate.get("canonical_url") == identity["url_norm"]
        if same_source and not same_canonical_url:
            continue
        score, method = canonical_match_score(job, candidate)
        if score > best_score:
            best_id = int(candidate["id"])
            best_score = score
            best_method = method
            best_representative = candidate

    if best_id is not None and auto_link_allowed(best_score, best_method):
        conn.execute("""
            UPDATE jobs
            SET canonical_opportunity_id=?,
                canonical_match_method=?,
                canonical_match_confidence=?
            WHERE id=?
        """, (best_id, best_method, best_score, job_id))
        conn.execute(
            "UPDATE canonical_opportunities SET last_seen_at=? WHERE id=?",
            (job["last_seen_at"], best_id),
        )
        return best_id, best_method, best_score

    new_id = _create_canonical_group(
        conn, job_id, job, "new", 0, notification_state
    )
    return new_id, "new", 0


CANONICAL_IDENTITY_VERSION = 2


def canonical_schema_needs_rebuild(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT MIN(identity_version), MAX(identity_version) FROM canonical_opportunities"
    ).fetchone()
    if not row or row[0] is None:
        return False
    return int(row[0]) < CANONICAL_IDENTITY_VERSION or int(row[1]) < CANONICAL_IDENTITY_VERSION


def rebuild_canonical_opportunities(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE jobs SET canonical_opportunity_id=NULL, canonical_match_method=NULL, canonical_match_confidence=NULL")
    conn.execute("DELETE FROM notification_ledger")
    conn.execute("DELETE FROM canonical_opportunities")


def backfill_notification_ledger() -> None:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO notification_ledger (
                canonical_opportunity_id, status, created_at, updated_at
            )
            SELECT co.id, 'suppressed', co.first_seen_at, co.last_seen_at
            FROM canonical_opportunities co
            LEFT JOIN notification_ledger nl
                ON nl.canonical_opportunity_id = co.id
            WHERE nl.canonical_opportunity_id IS NULL
        """)
        conn.commit()


def backfill_canonical_opportunities() -> None:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if canonical_schema_needs_rebuild(conn):
            rebuild_canonical_opportunities(conn)
        rows = conn.execute("""
            SELECT id FROM jobs
            WHERE canonical_opportunity_id IS NULL
            ORDER BY first_seen_at ASC, id ASC
        """).fetchall()
        for row in rows:
            _assign_canonical(conn, int(row["id"]), notification_state="suppressed")
        conn.commit()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_job_id TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            url TEXT NOT NULL,
            source_posted_at TEXT,
            posted_precision TEXT NOT NULL DEFAULT 'unknown',
            discovered_at TEXT NOT NULL,
            discovery_latency_seconds INTEGER,
            description TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            canonical_opportunity_id INTEGER,
            canonical_match_method TEXT,
            canonical_match_confidence INTEGER,
            UNIQUE(source, source_job_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS job_evaluations (
            job_id INTEGER PRIMARY KEY,
            evaluated_at TEXT NOT NULL,
            config_fingerprint TEXT NOT NULL,
            match INTEGER NOT NULL,
            score INTEGER NOT NULL,
            reasons_json TEXT NOT NULL,
            experience_min_years REAL,
            experience_max_years REAL,
            alertable INTEGER NOT NULL,
            alertability_reasons_json TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_ledger (
            canonical_opportunity_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,
            candidate_job_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            decision_reason_json TEXT NOT NULL DEFAULT '[]',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT,
            claimed_at TEXT,
            sent_at TEXT,
            last_error TEXT,
            FOREIGN KEY(canonical_opportunity_id) REFERENCES canonical_opportunities(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS source_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            jobs_seen INTEGER NOT NULL,
            new_jobs INTEGER NOT NULL,
            error TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS canonical_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_url TEXT,
            company_norm TEXT NOT NULL,
            title_norm TEXT NOT NULL,
            location_norm TEXT NOT NULL,
            representative_job_id INTEGER NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            identity_version INTEGER NOT NULL DEFAULT 1
        )
        """)
        _ensure_column(conn, "jobs", "canonical_opportunity_id", "INTEGER")
        _ensure_column(conn, "jobs", "canonical_match_method", "TEXT")
        _ensure_column(conn, "notification_ledger", "decision_reason_json", "TEXT DEFAULT '[]'")
        _ensure_column(conn, "notification_ledger", "attempt_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "notification_ledger", "next_attempt_at", "TEXT")
        _ensure_column(conn, "notification_ledger", "claimed_at", "TEXT")
        _ensure_column(conn, "jobs", "canonical_match_confidence", "INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_canonical ON jobs(canonical_opportunity_id)")
        conn.execute("UPDATE jobs SET discovery_latency_seconds=NULL WHERE discovery_latency_seconds < 0")
        # Repair records written by older builds where source metadata placed
        # the posting after the first time this VM had already discovered it.
        conn.execute("""
            UPDATE jobs
            SET source_posted_at=NULL,
                posted_precision='unknown',
                discovery_latency_seconds=NULL
            WHERE source_posted_at IS NOT NULL
              AND julianday(source_posted_at) IS NOT NULL
              AND julianday(discovered_at) IS NOT NULL
              AND julianday(source_posted_at) > julianday(discovered_at)
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canonical_lookup ON canonical_opportunities(company_norm, location_norm)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canonical_url ON canonical_opportunities(canonical_url)")
        conn.commit()
    backfill_canonical_opportunities()
    backfill_notification_ledger()


def upsert_jobs(jobs: list[dict[str, Any]], config: dict[str, Any] | None = None) -> int:
    new_count = 0
    config = config or get_config()
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        for incoming in jobs:
            j = dict(incoming)
            observed_at = parse_relative(j.get("discovered_at"))
            incoming_posted_at = parse_relative(j.get("source_posted_at"))
            if observed_at and incoming_posted_at and incoming_posted_at > observed_at:
                j["source_posted_at"] = None
                j["posted_precision"] = "unknown"
                j["discovery_latency_seconds"] = None

            existing = conn.execute(
                "SELECT id, canonical_opportunity_id, discovered_at FROM jobs WHERE source=? AND source_job_id=?",
                (j["source"], j["source_job_id"])
            ).fetchone()
            if existing:
                posted_at_for_update = j["source_posted_at"]
                precision_for_update = j["posted_precision"]
                first_discovered_at = parse_relative(existing[2])
                incoming_posted_at = parse_relative(posted_at_for_update)
                if (
                    incoming_posted_at
                    and first_discovered_at
                    and incoming_posted_at > first_discovered_at
                ):
                    # Never backfill a moving relative label ("just now", "1 min ago")
                    # with a timestamp that contradicts the job's original discovery.
                    posted_at_for_update = None
                    precision_for_update = "unknown"

                conn.execute("""
                    UPDATE jobs SET last_seen_at=?, source_posted_at=COALESCE(?, source_posted_at),
                    posted_precision=CASE WHEN ?='minute' THEN ? ELSE posted_precision END,
                    description=CASE WHEN length(?) > length(description) THEN ? ELSE description
                    END
                    WHERE id=?
                """, (
                    j["discovered_at"], posted_at_for_update, precision_for_update,
                    precision_for_update,
                    j["description"], j["description"], existing[0]
                ))
                if not existing[1]:
                    _assign_canonical(conn, int(existing[0]))
                _persist_job_evaluation(conn, int(existing[0]), config)
            else:
                if j.get("needs_jd_enrichment"):
                    j = enrich_linkedin_job(j)

                cur = conn.execute("""
                    INSERT INTO jobs (
                        source, source_job_id, company, title, location, url,
                        source_posted_at, posted_precision, discovered_at,
                        discovery_latency_seconds, description, first_seen_at, last_seen_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    j["source"], j["source_job_id"], j["company"], j["title"],
                    j["location"], j["url"], j["source_posted_at"],
                    j["posted_precision"], j["discovered_at"],
                    j["discovery_latency_seconds"], j["description"],
                    j["discovered_at"], j["discovered_at"]
                ))
                _assign_canonical(conn, int(cur.lastrowid))
                _persist_job_evaluation(conn, int(cur.lastrowid), config)
                new_count += 1
        conn.commit()
    return new_count

def _config_fingerprint(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _persist_job_evaluation(
    conn: sqlite3.Connection,
    job_id: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    job = _job_for_canonical(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} does not exist")

    details = match_details(job, config)
    alertability = alertability_details(job, details, config)
    evaluated_at = iso(now())
    fingerprint = _config_fingerprint(config)

    conn.execute("""
        INSERT INTO job_evaluations (
            job_id, evaluated_at, config_fingerprint, match, score,
            reasons_json, experience_min_years, experience_max_years,
            alertable, alertability_reasons_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(job_id) DO UPDATE SET
            evaluated_at=excluded.evaluated_at,
            config_fingerprint=excluded.config_fingerprint,
            match=excluded.match,
            score=excluded.score,
            reasons_json=excluded.reasons_json,
            experience_min_years=excluded.experience_min_years,
            experience_max_years=excluded.experience_max_years,
            alertable=excluded.alertable,
            alertability_reasons_json=excluded.alertability_reasons_json
    """, (
        job_id,
        evaluated_at,
        fingerprint,
        int(details["match"]),
        int(details["score"]),
        json.dumps(details["reasons"], ensure_ascii=False),
        details["experience_min_years"],
        details["experience_max_years"],
        int(alertability["alertable"]),
        json.dumps(alertability["reasons"], ensure_ascii=False),
    ))
    return {
        "match": details["match"],
        "score": details["score"],
        "reasons": details["reasons"],
        "experience_min_years": details["experience_min_years"],
        "experience_max_years": details["experience_max_years"],
        "alertable": alertability["alertable"],
        "alertability_reasons": alertability["reasons"],
        "evaluated_at": evaluated_at,
        "config_fingerprint": fingerprint,
    }


def _ensure_notification_state(
    conn: sqlite3.Connection,
    canonical_opportunity_id: int,
    initial_status: str = "pending",
) -> None:
    timestamp = iso(now())
    conn.execute("""
        INSERT INTO notification_ledger (
            canonical_opportunity_id, status, created_at, updated_at
        ) VALUES (?,?,?,?)
        ON CONFLICT(canonical_opportunity_id) DO NOTHING
    """, (canonical_opportunity_id, initial_status, timestamp, timestamp))


def backfill_job_evaluations(config: dict[str, Any] | None = None) -> int:
    config = config or get_config()
    count = 0
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT j.id
            FROM jobs j
            LEFT JOIN job_evaluations e ON e.job_id = j.id
            WHERE e.job_id IS NULL
            ORDER BY j.first_seen_at ASC, j.id ASC
        """).fetchall()
        for row in rows:
            _persist_job_evaluation(conn, int(row["id"]), config)
            count += 1
        conn.commit()
    return count


def refresh_job_evaluations(config: dict[str, Any] | None = None) -> int:
    config = config or get_config()
    fingerprint = _config_fingerprint(config)
    count = 0
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT j.id
            FROM jobs j
            LEFT JOIN job_evaluations e ON e.job_id = j.id
            WHERE e.job_id IS NULL OR e.config_fingerprint != ?
            ORDER BY j.first_seen_at ASC, j.id ASC
        """, (fingerprint,)).fetchall()
        for row in rows:
            _persist_job_evaluation(conn, int(row["id"]), config)
            count += 1
        conn.commit()
    return count


def _alert_age_timestamp(job: dict[str, Any]) -> dt.datetime | None:
    for field in ("source_posted_at", "discovered_at"):
        value = job.get(field)
        if value:
            parsed = parse_relative(value)
            if parsed:
                return parsed
    return None


def refresh_notification_decisions(config: dict[str, Any] | None = None) -> int:
    config = config or get_config()
    now_value = now()
    max_age = int(config.get("max_age_hours", 72))
    rediscovery_cutoff = iso(now_value - dt.timedelta(minutes=10))
    changed = 0

    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        candidates = conn.execute(
            """
            SELECT canonical_opportunity_id, status
            FROM notification_ledger
            WHERE status IN ('pending', 'queued')
               OR (
                    status='suppressed'
                    AND EXISTS (
                        SELECT 1
                        FROM jobs j
                        WHERE j.canonical_opportunity_id =
                              notification_ledger.canonical_opportunity_id
                          AND j.discovered_at >= ?
                    )
               )
            ORDER BY created_at ASC
            """,
            (rediscovery_cutoff,),
        ).fetchall()

        for row in candidates:
            opportunity_id = int(row["canonical_opportunity_id"])
            current_status = row["status"]

            observations = conn.execute(
                """
                SELECT
                    j.*,
                    e.match,
                    e.score,
                    e.reasons_json,
                    e.experience_min_years,
                    e.experience_max_years,
                    e.alertable,
                    e.alertability_reasons_json
                FROM jobs j
                JOIN job_evaluations e ON e.job_id=j.id
                WHERE j.canonical_opportunity_id=?
                ORDER BY
                    e.match DESC,
                    e.alertable DESC,
                    e.score DESC,
                    j.discovered_at DESC,
                    j.id DESC
                """,
                (opportunity_id,),
            ).fetchall()

            eligible = []
            fresh_matches = []
            recent_matches = []
            fresh_alertable = []

            for observation in observations:
                item = dict(observation)

                if not item["match"]:
                    continue

                eligible.append(item)

                age_timestamp = _alert_age_timestamp(item)
                is_fresh = (
                    not age_timestamp
                    or age_timestamp >=
                    now_value - dt.timedelta(hours=max_age)
                )

                if not is_fresh:
                    continue

                fresh_matches.append(item)

                # Discovery is the alert trigger. Do not expire a valid
                # opportunity just because evaluation or queue processing took
                # longer than expected. max_age above remains the historical
                # relevance guard.
                recent_matches.append(item)

                if item["alertable"]:
                    fresh_alertable.append(item)

            timestamp = iso(now_value)

            if current_status == "queued":
                if (
                    fresh_alertable
                    and config.get("notifications_enabled", True)
                ):
                    candidate = fresh_alertable[0]
                    reasons = [
                        "revalidated queued opportunity",
                        "passes current match and alert policy",
                        "eligible opportunity queued for prompt delivery",
                    ]

                    conn.execute(
                        """
                        UPDATE notification_ledger
                        SET candidate_job_id=?,
                            updated_at=?,
                            decision_reason_json=?
                        WHERE canonical_opportunity_id=?
                          AND status='queued'
                        """,
                        (
                            candidate["id"],
                            timestamp,
                            json.dumps(reasons, ensure_ascii=False),
                            opportunity_id,
                        ),
                    )
                elif recent_matches:
                    reasons = [
                        "job is still fresh and relevant but is not alertable under the current policy; awaiting future re-evaluation"
                    ]

                    conn.execute(
                        """
                        UPDATE notification_ledger
                        SET status='pending',
                            candidate_job_id=NULL,
                            updated_at=?,
                            decision_reason_json=?
                        WHERE canonical_opportunity_id=?
                          AND status='queued'
                        """,
                        (
                            timestamp,
                            json.dumps(reasons, ensure_ascii=False),
                            opportunity_id,
                        ),
                    )
                else:
                    reasons = [
                        "queued opportunity is outside the real-time alert window"
                    ]

                    conn.execute(
                        """
                        UPDATE notification_ledger
                        SET status='suppressed',
                            candidate_job_id=NULL,
                            updated_at=?,
                            decision_reason_json=?
                        WHERE canonical_opportunity_id=?
                          AND status='queued'
                        """,
                        (
                            timestamp,
                            json.dumps(reasons, ensure_ascii=False),
                            opportunity_id,
                        ),
                    )

                changed += 1
                continue

            if (
                fresh_alertable
                and config.get("notifications_enabled", True)
            ):
                candidate = fresh_alertable[0]

                reasons = [
                    (
                        "new canonical opportunity"
                        if current_status == "pending"
                        else "new source observation for previously suppressed opportunity"
                    ),
                    "passes match and alert policy",
                    "eligible opportunity queued for prompt delivery",
                    f"within {max_age} hour age window",
                ]

                conn.execute(
                    """
                    UPDATE notification_ledger
                    SET status='queued',
                        candidate_job_id=?,
                        updated_at=?,
                        decision_reason_json=?
                    WHERE canonical_opportunity_id=?
                      AND status IN ('pending', 'suppressed')
                    """,
                    (
                        candidate["id"],
                        timestamp,
                        json.dumps(reasons, ensure_ascii=False),
                        opportunity_id,
                    ),
                )

            elif not eligible:
                reasons = ["no profile-matching observation"]

                conn.execute(
                    """
                    UPDATE notification_ledger
                    SET status='suppressed',
                        candidate_job_id=NULL,
                        updated_at=?,
                        decision_reason_json=?
                    WHERE canonical_opportunity_id=?
                      AND status='pending'
                    """,
                    (
                        timestamp,
                        json.dumps(reasons, ensure_ascii=False),
                        opportunity_id,
                    ),
                )

            elif not fresh_matches:
                reasons = [
                    f"no matching observation within {max_age} hour age window"
                ]

                conn.execute(
                    """
                    UPDATE notification_ledger
                    SET status='suppressed',
                        candidate_job_id=NULL,
                        updated_at=?,
                        decision_reason_json=?
                    WHERE canonical_opportunity_id=?
                      AND status='pending'
                    """,
                    (
                        timestamp,
                        json.dumps(reasons, ensure_ascii=False),
                        opportunity_id,
                    ),
                )

            elif not config.get("notifications_enabled", True):
                reasons = [
                    "Telegram notifications disabled; awaiting future re-evaluation"
                ]

                conn.execute(
                    """
                    UPDATE notification_ledger
                    SET status='pending',
                        candidate_job_id=NULL,
                        updated_at=?,
                        decision_reason_json=?
                    WHERE canonical_opportunity_id=?
                      AND status='pending'
                    """,
                    (
                        timestamp,
                        json.dumps(reasons, ensure_ascii=False),
                        opportunity_id,
                    ),
                )

            elif not recent_matches:
                reasons = [
                    "matching job was discovered too long ago; waiting for a new source observation"
                ]

                conn.execute(
                    """
                    UPDATE notification_ledger
                    SET status='suppressed',
                        candidate_job_id=NULL,
                        updated_at=?,
                        decision_reason_json=?
                    WHERE canonical_opportunity_id=?
                      AND status IN ('pending', 'suppressed')
                    """,
                    (
                        timestamp,
                        json.dumps(reasons, ensure_ascii=False),
                        opportunity_id,
                    ),
                )

            else:
                reasons = [
                    "profile match exists but is not alertable under current policy; awaiting future re-evaluation"
                ]

                conn.execute(
                    """
                    UPDATE notification_ledger
                    SET status='pending',
                        candidate_job_id=NULL,
                        updated_at=?,
                        decision_reason_json=?
                    WHERE canonical_opportunity_id=?
                      AND status='pending'
                    """,
                    (
                        timestamp,
                        json.dumps(reasons, ensure_ascii=False),
                        opportunity_id,
                    ),
                )

            changed += 1

        conn.commit()

    return changed

def record_run(source: str, started_at: dt.datetime, finished: dt.datetime,
               jobs_seen: int, new_jobs: int, error: str | None = None) -> None:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO source_runs(source,started_at,finished_at,jobs_seen,new_jobs,error) VALUES(?,?,?,?,?,?)",
            (source, iso(started_at), iso(finished), jobs_seen, new_jobs, error)
        )
        conn.commit()


def normalize_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def phrase_hits(terms: list[str], text: str) -> list[str]:
    normalized_text = f" {normalize_phrase(text)} "
    hits: list[str] = []
    for term in terms:
        normalized_term = normalize_phrase(term)
        if normalized_term and f" {normalized_term} " in normalized_text:
            hits.append(term)
    return hits


def title_allowed(title: str, config: dict[str, Any]) -> bool:
    return not phrase_hits(config.get("title_exclude", []), title)


def location_terms(config: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    aliases = {
        "bengaluru": ["bengaluru", "bangalore"],
        "bangalore": ["bengaluru", "bangalore"],
        "gurugram": ["gurugram", "gurgaon"],
        "gurgaon": ["gurugram", "gurgaon"],
    }
    for raw in config.get("locations", []):
        primary = normalize_phrase(str(raw).split(",")[0])
        if not primary:
            continue
        terms.append(primary)
        if primary in aliases:
            terms.extend(aliases[primary])
    return sorted(set(terms))


def location_allowed(location: str, config: dict[str, Any]) -> bool:
    value = normalize_phrase(location)
    if not value:
        return False
    is_remote = bool(phrase_hits(["remote"], value))
    if config.get("remote_only") and not is_remote:
        return False

    # A configured region such as "Remote, India" is not a wildcard for
    # every remote job worldwide. Match its qualifier as well as "remote".
    # A plain "Remote" entry intentionally remains a global remote filter.
    configured_locations = config.get("locations", [])
    for raw in configured_locations:
        parts = str(raw).split(",", 1)
        primary = normalize_phrase(parts[0])
        if primary != "remote" or not is_remote:
            continue
        qualifier = normalize_phrase(parts[1]) if len(parts) > 1 else ""
        if not qualifier or phrase_hits([qualifier], value):
            return True

    terms = [
        term for term in location_terms(config)
        if term != "remote"
    ]
    return any(phrase_hits([term], value) for term in terms)




def _clean_experience_text(text: str) -> str:
    raw = html_lib.unescape(str(text or "")).replace("\xa0", " ")
    raw = re.sub(r"[‐‑‒–—−]", "-", raw)
    raw = re.sub(r"\s+", " ", raw).strip().lower()
    return raw


def extract_experience(text: str) -> tuple[float | None, float | None]:
    raw = _clean_experience_text(text)
    if not raw:
        return None, None

    # Prefer explicit experience ranges before generic single-number matches.
    ranges = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        raw,
    )
    if ranges:
        lows = [float(a) for a, _ in ranges]
        highs = [float(b) for _, b in ranges]
        return min(lows), max(highs)

    plus = re.search(
        r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b",
        raw,
    )
    if plus:
        years = float(plus.group(1))
        return years, None

    single = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        raw,
    )
    if single:
        years = float(single.group(1))
        return years, years

    # A few JDs write the requirement in reverse order.
    reverse_range = re.search(
        r"experience(?:\s+of|\s*[:\-])\s*"
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        raw,
    )
    if reverse_range:
        return float(reverse_range.group(1)), float(reverse_range.group(2))

    return None, None


def extract_jd_experience(text: str) -> tuple[float | None, float | None]:
    raw = _clean_experience_text(text)
    if not raw:
        return None, None

    # Prefer explicit "overall/total experience" statements. This avoids
    # accidentally selecting unrelated numeric requirements elsewhere in a JD.
    priority_patterns = (
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*"
        r"(?:years?|yrs?)\s+of\s+(?:overall|total)\b[^.!?]{0,160}\bexperience\b",
        r"(?:overall|total)\s+(?:software\s+engineering|professional|work\s+)?"
        r"experience\b[^.!?]{0,120}?(\d+(?:\.\d+)?)\s*(?:-|to)\s*"
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        r"(?:minimum|at\s+least|requires?|required)\s+(?:of\s+)?"
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b"
        r"[^.!?]{0,120}\bexperience\b",
        r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\s+"
        r"(?:of\s+)?[^.!?]{0,120}\bexperience\b",
    )

    for pattern in priority_patterns:
        match = re.search(pattern, raw, re.I)
        if not match:
            continue
        values = [float(value) for value in match.groups() if value is not None]
        if len(values) >= 2:
            return values[0], values[1]
        if values:
            return values[0], None

    # Fall back to the normal experience parser, but inspect focused
    # experience-bearing chunks first.
    chunks = [
        chunk.strip()
        for chunk in re.split(r"(?<=[.!?])\s+|\n+|•", raw)
        if chunk.strip()
    ]
    priority = [
        chunk
        for chunk in chunks
        if re.search(r"\bexperience\b", chunk, re.I)
    ]
    for chunk in priority + chunks:
        result = extract_experience(chunk)
        if result != (None, None):
            return result

    return None, None


def _linkedin_job_id(url: str) -> str | None:
    match = re.search(r"(?:-|/)(\d{8,})(?:[/?#]|$)", url or "")
    return match.group(1) if match else None


def _clean_detail_text(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _linkedin_job_description(url: str) -> str:
    job_id = _linkedin_job_id(url)
    endpoints = []
    if job_id:
        endpoints.append(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}")
    if url:
        endpoints.append(url)

    for endpoint in endpoints:
        try:
            response = _linkedin_http_get(
                endpoint,
                headers={**UA, "Accept": "text/html,application/xhtml+xml"},
                timeout=10,
            )
            if response.status_code != 200:
                continue
        except LinkedInRateLimitCooldown:
            return ""
        except requests.RequestException as exc:
            if getattr(getattr(exc, "response", None), "status_code", None) == 429:
                log.warning("linkedin JD enrichment stopped after HTTP 429")
                return ""
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[str] = []

        # Prefer JSON-LD JobPosting descriptions when available. This is
        # independent of LinkedIn's frequently changing CSS classes.
        for script in soup.select('script[type="application/ld+json"]'):
            raw_json = script.string or script.get_text()
            if not raw_json:
                continue
            try:
                payload = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                continue

            stack = payload if isinstance(payload, list) else [payload]
            while stack:
                item = stack.pop()
                if isinstance(item, list):
                    stack.extend(item)
                    continue
                if not isinstance(item, dict):
                    continue

                item_type = item.get("@type")
                is_job_posting = (
                    item_type == "JobPosting"
                    or (
                        isinstance(item_type, list)
                        and "JobPosting" in item_type
                    )
                )
                if is_job_posting and item.get("description"):
                    candidates.append(
                        _clean_detail_text(str(item["description"]))
                    )

                for value in item.values():
                    if isinstance(value, (dict, list)):
                        stack.append(value)

        selectors = (
            "div.show-more-less-html__markup",
            "div.description__text",
            "section.show-more-less-html",
            "div.decorated-job-posting__details",
            "main",
            "[class*='description']",
        )
        for selector in selectors:
            for node in soup.select(selector):
                text = _clean_detail_text(str(node))
                if text:
                    candidates.append(text)

        # Meta fallbacks help when LinkedIn changes its rendered description
        # markup but still publishes a description summary.
        for selector in (
            'meta[name="description"]',
            'meta[property="og:description"]',
        ):
            node = soup.select_one(selector)
            if node and node.get("content"):
                candidates.append(_clean_detail_text(node.get("content", "")))

        unique = list(dict.fromkeys(text for text in candidates if text))
        if unique:
            with_experience = [
                text for text in unique
                if re.search(r"\bexperience\b", text, re.I)
            ]
            pool = with_experience or unique
            return max(pool, key=len)[:20000]

    return ""


def enrich_linkedin_job(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("source") != "linkedin":
        return job

    # Always inspect the actual LinkedIn JD when available. Search-result
    # snippets can contain unrelated numbers (or omit requirements entirely),
    # so a generic experience hit must not short-circuit JD enrichment.
    existing_description = job.get("description") or ""
    detail = _linkedin_job_description(job.get("url", ""))
    if not detail:
        job.pop("needs_jd_enrichment", None)
        return job

    # Replace the previous captured JD section rather than appending a new
    # copy on every poll; keep the source metadata and latest detail text.
    existing_description = re.sub(
        r"\s*JD:\s*.*$",
        "",
        existing_description,
        flags=re.I,
    ).strip()
    job["description"] = (
        f"{existing_description} JD: {detail}".strip()
    )[:30000]

    detail_experience = extract_jd_experience(detail)
    if detail_experience != (None, None):
        job["jd_experience_min_years"] = detail_experience[0]
        job["jd_experience_max_years"] = detail_experience[1]

    job.pop("needs_jd_enrichment", None)
    return job
def match_details(job: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or get_config()
    title = job.get("title") or ""
    description = job.get("description") or ""
    combined = f"{title} {description}"
    reasons: list[str] = []

    if not title_allowed(title, config):
        return {
            "match": False,
            "score": 0,
            "reasons": ["excluded title"],
            "experience_min_years": None,
            "experience_max_years": None,
        }

    if config.get("excluded_role_terms") and phrase_hits(config["excluded_role_terms"], title):
        return {
            "match": False,
            "score": 0,
            "reasons": ["excluded role/category"],
            "experience_min_years": None,
            "experience_max_years": None,
        }

    if not location_allowed(job.get("location") or "", config):
        return {
            "match": False,
            "score": 0,
            "reasons": ["location outside configured targets"],
            "experience_min_years": None,
            "experience_max_years": None,
        }

    score = 20
    reasons.append("target location")

    normalized_title = normalize_phrase(title)
    configured_roles = {
        normalize_phrase(role): role
        for role in config.get("target_roles", [])
    }

    title_role_hits = phrase_hits(config.get("target_roles", []), title)
    role_hits = title_role_hits
    role_source = "title"

    # Common equivalent naming used by job portals:
    # Software Engineer ~= Software Development Engineer ~= SDE
    software_engineer_targeted = (
        "software engineer" in configured_roles
        or "software developer" in configured_roles
    )

    if not role_hits and software_engineer_targeted:
        if re.search(
            r"\bsoftware development engineer(?:\s+(?:[ivx]+|\d+))?\b",
            normalized_title,
        ) or re.search(
            r"\bsde(?:\s+(?:[ivx]+|\d+))?\b",
            normalized_title,
        ):
            role_hits = [
                configured_roles.get("software engineer", "software engineer")
            ]

    # Full-stack spelling variants.
    if not role_hits:
        full_stack_targeted = (
            "full stack developer" in configured_roles
            or "full stack engineer" in configured_roles
        )
        if full_stack_targeted and re.search(
            r"\bfull[- ]?stack\s+(?:developer|engineer)\b",
            normalized_title,
        ):
            role_hits = [
                configured_roles.get(
                    "full stack developer",
                    configured_roles.get(
                        "full stack engineer",
                        "full stack developer",
                    ),
                )
            ]

    # A configured skill plus a generic developer/engineer title is a valid
    # role-family signal. Example: "Javascript Developer".
    if not role_hits:
        generic_title = bool(
            re.search(r"\b(?:developer|engineer)\b", normalized_title)
        )
        title_skill_hits = phrase_hits(config.get("skills", []), title)

        if generic_title and title_skill_hits:
            role_hits = [f"{title_skill_hits[0]} developer"]

    if not role_hits:
        role_hits = phrase_hits(config.get("target_roles", []), description)
        role_source = "description"

    if role_hits:
        role_bonus = 35 if role_source == "title" else 30
        score += role_bonus
        reasons.append(f"role ({role_source}): {role_hits[0]}")
    else:
        reasons.append("no configured target-role match")

    skill_hits = phrase_hits(config.get("skills", []), combined)
    if skill_hits:
        score += min(30, 6 * len(skill_hits))
        reasons.append("skills: " + ", ".join(skill_hits[:5]))

    # Prefer structured JD extraction, then a JD-focused parse of the
    # description. Only fall back to generic text parsing when the JD has no
    # explicit requirement; never let a generic title/snippet override JD data.
    exp_min = job.get("jd_experience_min_years")
    exp_max = job.get("jd_experience_max_years")
    if exp_min is None and exp_max is None:
        exp_min, exp_max = extract_jd_experience(description)
    if exp_min is None and exp_max is None:
        exp_min, exp_max = extract_experience(combined)

    candidate_years = config.get("candidate_experience_years")
    max_years = float(config.get("max_experience_years", 3))
    minimum_job_years = config.get("min_experience_years")

    if exp_min is not None or exp_max is not None:
        effective_min = exp_min if exp_min is not None else exp_max

        if (
            candidate_years is not None
            and effective_min is not None
            and effective_min > float(candidate_years)
        ):
            return {
                "match": False,
                "score": 0,
                "reasons": [
                    f"experience minimum {effective_min:g} exceeds "
                    f"candidate {float(candidate_years):g} years"
                ],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        if (
            minimum_job_years is not None
            and exp_max is not None
            and exp_max < float(minimum_job_years)
        ):
            return {
                "match": False,
                "score": 0,
                "reasons": [
                    f"job maximum experience {exp_max:g} is below "
                    f"configured minimum {float(minimum_job_years):g} years"
                ],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        if exp_max is not None and exp_max > max_years:
            return {
                "match": False,
                "score": 0,
                "reasons": [
                    f"experience range exceeds configured maximum "
                    f"of {max_years:g} years"
                ],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        score += 15
        experience_label = (
            f"{effective_min:g}"
            + (f"-{exp_max:g}" if exp_max is not None else "+")
        )
        candidate_label = (
            f"{float(candidate_years):g} years"
            if candidate_years is not None
            else "configured profile"
        )
        reasons.append(
            f"experience compatible: candidate {candidate_label}; "
            f"job {experience_label}"
        )
    else:
        # Unknown experience is neutral for matching. The separate
        # alertability policy decides whether it can generate an alert.
        reasons.append("experience not stated in captured source data")

    threshold = int(config.get("match_threshold", 55))

    return {
        "match": score >= threshold and bool(role_hits),
        "score": min(score, 100),
        "reasons": reasons,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
    }


def alertability_details(job: dict[str, Any], details: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if not details["match"]:
        return {"alertable": False, "reasons": ["not a profile match"]}

    if not config.get("notifications_enabled", True):
        return {"alertable": False, "reasons": ["Telegram notifications disabled"]}

    if config.get("require_explicit_experience_for_alerts"):
        if details.get("experience_min_years") is None and details.get("experience_max_years") is None:
            return {"alertable": False, "reasons": ["explicit experience required for alerts"]}

    return {"alertable": True, "reasons": ["passes current alert policy"]}




def likely_match(job: dict[str, Any]) -> bool:
    return bool(match_details(job)["match"])


class LinkedInRateLimitCooldown(RuntimeError):
    """Raised when a previous LinkedIn HTTP 429 is still in its cooldown window."""


def _linkedin_cooldown_remaining() -> float:
    return max(0.0, linkedin_rate_limited_until_monotonic - time.monotonic())


def _retry_after_seconds(response: requests.Response) -> float | None:
    raw = str(getattr(response, "headers", {}).get("Retry-After", "") or "").strip()
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return max(0.0, (parsed.astimezone(UTC) - now()).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def _activate_linkedin_rate_limit(response: requests.Response) -> float:
    """Back off globally when any LinkedIn endpoint returns HTTP 429."""
    global linkedin_rate_limited_until_monotonic
    global linkedin_rate_limit_streak, linkedin_rate_limit_generation

    remaining = _linkedin_cooldown_remaining()
    if remaining > 0:
        return remaining

    linkedin_rate_limit_streak += 1
    multiplier = 2 ** min(linkedin_rate_limit_streak - 1, 3)
    fallback = min(
        LINKEDIN_RATE_LIMIT_MAX_COOLDOWN_SECONDS,
        LINKEDIN_RATE_LIMIT_BASE_COOLDOWN_SECONDS * multiplier,
    )
    retry_after = _retry_after_seconds(response)
    cooldown = max(fallback, retry_after or 0.0)
    linkedin_rate_limited_until_monotonic = time.monotonic() + cooldown
    linkedin_rate_limit_generation += 1

    until_utc = now() + dt.timedelta(seconds=cooldown)
    source_runtime = source_state.setdefault("linkedin", {})
    source_runtime["rate_limited_until"] = iso(until_utc)
    source_runtime["rate_limit_cooldown_seconds"] = int(cooldown)
    log.warning(
        "linkedin: HTTP 429; pausing all LinkedIn HTTP requests for %ss "
        "(streak=%s, retry_after=%s)",
        int(cooldown),
        linkedin_rate_limit_streak,
        int(retry_after) if retry_after is not None else "not-provided",
    )
    return cooldown


def _linkedin_http_get(
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 25,
) -> requests.Response:
    """Serialize and pace all LinkedIn HTTP calls, including JD enrichment."""
    global linkedin_last_http_request_monotonic

    with linkedin_http_lock:
        remaining = _linkedin_cooldown_remaining()
        if remaining > 0:
            raise LinkedInRateLimitCooldown(
                f"LinkedIn HTTP cooldown active for {int(remaining)}s"
            )

        spacing = LINKEDIN_MIN_REQUEST_INTERVAL_SECONDS - (
            time.monotonic() - linkedin_last_http_request_monotonic
        )
        if spacing > 0:
            time.sleep(spacing)

        # Re-check after waiting in case another worker received a 429.
        remaining = _linkedin_cooldown_remaining()
        if remaining > 0:
            raise LinkedInRateLimitCooldown(
                f"LinkedIn HTTP cooldown active for {int(remaining)}s"
            )

        linkedin_last_http_request_monotonic = time.monotonic()
        response = requests.get(
            endpoint,
            params=params,
            headers=headers or UA,
            timeout=timeout,
        )
        if response.status_code == 429:
            _activate_linkedin_rate_limit(response)
            response.raise_for_status()
        return response


def _linkedin_request(endpoint: str, params: dict[str, Any]) -> requests.Response:
    for attempt in range(3):
        response = _linkedin_http_get(
            endpoint, params=params, headers=UA, timeout=25
        )
        if response.status_code not in {500, 502, 503, 504}:
            response.raise_for_status()
            return response
        wait = min(30, 2 ** attempt * 2)
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            wait = min(60, int(retry_after))
        time.sleep(wait)
    response.raise_for_status()
    return response


def _linkedin_parse_page(response: requests.Response) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    soup = BeautifulSoup(response.text, "html.parser")

    links = soup.select("a.base-card__full-link")
    if not links:
        links = soup.select('a[href*="/jobs/view/"]')

    seen_ids: set[str] = set()
    for link in links:
        card = link.find_parent("div", class_="base-card")
        if card is None:
            card = link.find_parent("li") or link

        title = card.select_one("h3.base-search-card__title")
        company = card.select_one("h4.base-search-card__subtitle")
        loc = card.select_one("span.job-search-card__location")
        posted = card.select_one("time")
        if not title:
            continue

        url = (link.get("href") or "").split("?")[0]
        source_id = _linkedin_job_id(url) or hashlib.sha1(url.encode()).hexdigest()[:20]
        if source_id in seen_ids:
            continue
        seen_ids.add(source_id)

        visible = posted.get_text(" ", strip=True) if posted else ""
        posted_at = parse_relative(visible)
        precision = "minute" if re.search(
            r"(just now|\d+\s*(?:minute|min|hour|hr)s?\s*ago)", visible.lower()
        ) else "date"
        if not posted_at and posted and posted.get("datetime"):
            posted_at = parse_relative(posted.get("datetime"))

        jobs.append({
            **normalize_job(
                "linkedin", source_id,
                company.get_text(" ", strip=True) if company else "",
                title.get_text(" ", strip=True),
                loc.get_text(" ", strip=True) if loc else "",
                url, posted_at, precision,
                card.get_text(" ", strip=True),
            ),
            "needs_jd_enrichment": True,
        })

    return jobs

def _linkedin_search_page(query: str, location: str, start: int, fast: bool = True) -> list[dict[str, Any]]:
    endpoint = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": query,
        "location": location,
        "f_TPR": LINKEDIN_FAST_TPR if fast else LINKEDIN_DEEP_TPR,
        "sortBy": "DD",
        "start": start,
    }
    # The fast lane must search the full LinkedIn result set. Restricting it
    # to Easy Apply jobs can postpone otherwise relevant fresh postings until
    # the slower deep scan, increasing discovery latency.
    response = _linkedin_request(endpoint, params)
    return _linkedin_parse_page(response)


def linkedin_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    global linkedin_last_deep_scan_at, linkedin_fast_target_cursor
    global linkedin_rate_limit_streak
    scan_started = time.monotonic()
    if _linkedin_cooldown_remaining() > 0:
        remaining = int(_linkedin_cooldown_remaining())
        log.info("linkedin scan skipped; rate-limit cooldown has %ss remaining", remaining)
        return []
    rate_limit_generation_at_start = linkedin_rate_limit_generation
    jobs: list[dict[str, Any]] = []
    last_deep = linkedin_last_deep_scan_at
    last_deep_at = parse_relative(last_deep) if last_deep else None
    do_deep = (
        last_deep_at is None
        or (now() - last_deep_at).total_seconds() >= LINKEDIN_DEEP_SCAN_SECONDS
    )

    # Spread first-page searches over consecutive cycles to reduce HTTP 429s.
    # The cursor advances through every query/location pair, even when a scan
    # is rate-limited; a full pass takes ceil(pair_count / batch_size) cycles.
    scan_locations = list(config.get("locations", []))
    scan_queries = list(config.get("linkedin_queries", []))
    all_fast_targets = [
        (query, location, 0, True)
        for query in scan_queries
        for location in scan_locations
    ]
    if all_fast_targets:
        batch_size = min(LINKEDIN_FAST_TARGETS_PER_SCAN, len(all_fast_targets))
        start_index = linkedin_fast_target_cursor % len(all_fast_targets)
        end_index = start_index + batch_size
        if end_index <= len(all_fast_targets):
            fast_targets = all_fast_targets[start_index:end_index]
        else:
            fast_targets = all_fast_targets[start_index:] + all_fast_targets[:end_index % len(all_fast_targets)]
        linkedin_fast_target_cursor = end_index % len(all_fast_targets)
    else:
        fast_targets = []
    # Deep pagination is limited to the same small batch of pairs as the fast
    # lane, rather than creating a full-size burst on top of it.
    failed_pages = 0
    rate_limited = False

    def run_batch(targets: list[tuple[str, str, int, bool]]) -> None:
        nonlocal failed_pages, rate_limited
        # Run in paced order. Submitting every target to an executor allows
        # queued requests to continue even after the first request is rate-limited.
        for query, location, start, fast in targets:
            try:
                jobs.extend(_linkedin_search_page(query, location, start, fast))
            except Exception as exc:
                failed_pages += 1
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None)
                if status_code == 429:
                    if _linkedin_cooldown_remaining() <= 0:
                        _activate_linkedin_rate_limit(response)
                    rate_limited = True
                    log.warning("linkedin search batch stopped after HTTP 429")
                    break
                if isinstance(exc, LinkedInRateLimitCooldown):
                    rate_limited = True
                    log.info("linkedin search batch stopped; rate-limit cooldown is active")
                    break
                log.warning("linkedin page request failed: %r", exc)

    run_batch(fast_targets)
    deep_targets: list[tuple[str, str, int, bool]] = []

    # A 429 on the fast lane is a strong signal to reduce pressure. Do not
    # compound it with deep pagination in this same scan.
    if do_deep and not rate_limited:
        deep_targets = [
            (query, location, start, False)
            for query, location, _, _ in fast_targets
            for start in range(10, 10 + LINKEDIN_DEEP_PAGE_BATCH * 10, 10)
        ]
        run_batch(deep_targets)
        linkedin_last_deep_scan_at = iso(now())

    unique_jobs: dict[str, dict[str, Any]] = {
        job["source_job_id"]: job for job in jobs
    }
    jobs = list(unique_jobs.values())
    log.info(
        "linkedin discovery scan: queries=%s locations=%s requests=%s "
        "deep=%s unique_jobs=%s failed_requests=%s elapsed=%.1fs",
        len(scan_queries),
        len(scan_locations),
        len(fast_targets) + len(deep_targets),
        do_deep,
        len(jobs),
        failed_pages,
        time.monotonic() - scan_started,
    )

    # Keep enrichment bounded so it cannot consume the search worker pool.
    # Discovery results are returned even when a detail request fails.
    candidates = []
    for job in jobs:
        combined = f"{job.get('title', '')} {job.get('description', '')}"
        if extract_experience(combined) != (None, None):
            job.pop("needs_jd_enrichment", None)
            continue
        preliminary = match_details(job, config)
        if preliminary["match"]:
            candidates.append(job)
        else:
            job.pop("needs_jd_enrichment", None)

    with ThreadPoolExecutor(max_workers=LINKEDIN_DETAIL_WORKERS) as executor:
        futures = [executor.submit(enrich_linkedin_job, job) for job in candidates]
        for future in as_completed(futures):
            try:
                future.result()
            except LinkedInRateLimitCooldown:
                log.info("linkedin JD enrichment skipped; rate-limit cooldown is active")
            except Exception as exc:
                log.warning("linkedin JD enrichment failed: %r", exc)

    if linkedin_rate_limit_generation == rate_limit_generation_at_start:
        # A complete request cycle without a new 429 resets the escalation streak.
        linkedin_rate_limit_streak = 0

    return jobs

# The public relay repository contains only the Naukri feed and its small
# scheduled collector workflow. The main application repository stays private.
NAUKRI_RELAY_URL = (
    "https://raw.githubusercontent.com/AvinashBhalla/"
    "job-beeper-naukri-relay/naukri-relay/dashboard/data/naukri_relay.json"
)


def naukri_collect() -> list[dict[str, Any]]:
    # The separate public relay exposes only a generated feed, not the private
    # application source. No GitHub token is required to read public JSON.
    relay_headers = {**UA, "Accept": "application/json"}
    response: requests.Response | None = None
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(4):
        try:
            candidate = requests.get(
                NAUKRI_RELAY_URL,
                # GitHub's raw-content CDN can briefly serve the previous feed
                # after the relay branch advances. Bust that cache on each poll.
                params={"t": int(time.time())},
                headers=relay_headers,
                timeout=20,
            )
            if candidate.status_code in retryable_statuses:
                if attempt == 3:
                    candidate.raise_for_status()
                wait = min(8, 2 ** attempt)
                log.warning(
                    "naukri relay fetch returned HTTP %s; retrying in %ss",
                    candidate.status_code,
                    wait,
                )
                time.sleep(wait)
                continue
            # A missing feed or wrong public URL is a setup fault, not a
            # transient server error. Fail quickly without retrying a 404.
            candidate.raise_for_status()
            response = candidate
            break
        except requests.HTTPError:
            raise
        except requests.RequestException:
            if attempt == 3:
                raise
            wait = min(8, 2 ** attempt)
            log.warning("naukri relay network fetch failed; retrying in %ss", wait)
            time.sleep(wait)

    if response is None:
        raise RuntimeError("Naukri relay fetch returned no response")
    payload = response.json()
    relay_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    relay_collected_at = payload.get("updated_at") if isinstance(payload, dict) else None
    collected_at = parse_relative(relay_collected_at) if relay_collected_at else now()

    jobs: list[dict[str, Any]] = []
    for item in relay_jobs:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("id") or item.get("url") or "")
        url = str(item.get("url") or "")
        if not source_id or not url:
            continue

        posted_raw = item.get("posted")
        posted_at = parse_relative(str(posted_raw)) if posted_raw else None

        experience = item.get("experience") or {}
        skills = item.get("skills_detected") or []
        description = str(item.get("description") or "")
        if experience:
            description = f"{description} {experience.get('label', '')}".strip()
        if skills:
            description = f"{description} {' '.join(map(str, skills))}".strip()

        job = normalize_job(
            "naukri",
            source_id,
            str(item.get("company") or ""),
            str(item.get("title") or ""),
            str(item.get("jd_location") or item.get("location") or ""),
            url,
            posted_at,
            "date" if posted_at else "unknown",
            description,
        )

        # The actual Naukri acquisition happened on the external GitHub runner.
        # Preserve that timestamp rather than pretending the Oracle VM fetched
        # the job at the same moment.
        job["discovered_at"] = iso(collected_at) or job["discovered_at"]
        # Relay currently supplies date-level posting precision. Midnight
        # parsed from a date is not an exact posting time, so do not report a
        # misleading discovery-latency metric from it.
        job["discovery_latency_seconds"] = None
        jobs.append(job)

    return jobs

def instahyre_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = "https://www.instahyre.com/api/v1/job_search/"
    response = requests.get(
        endpoint,
        params={
            "jobLocations": next(
                (str(x).split(",")[0] for x in config.get("locations", []) if "remote" not in str(x).lower()),
                "Bangalore",
            ),
            "limit": 35,
        },
        headers={**UA, "Referer": "https://www.instahyre.com/"},
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    items = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in ("jobs", "jobDetails", "results", "data", "job_details"):
            value = payload.get(key)
            if isinstance(value, list):
                items = value
                break
    jobs = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = item.get("jobId") or item.get("id") or item.get("jobID")
        if not source_id:
            continue
        url = str(
            item.get("url") or item.get("publicUrl") or item.get("jobUrl")
            or f"https://www.instahyre.com/job-{source_id}-"
        )
        posted_raw = item.get("postedAt") or item.get("posted_at") or item.get("postedDate")
        posted_at = parse_relative(str(posted_raw)) if posted_raw else None
        jobs.append(normalize_job(
            "instahyre", str(source_id),
            str(item.get("companyName") or item.get("company") or ""),
            str(item.get("title") or item.get("jobTitle") or ""),
            str(item.get("location") or item.get("locations") or ""),
            url, posted_at, "minute" if posted_at else "unknown",
            str(item.get("description") or item.get("descriptionText") or ""),
        ))
    return jobs



def greenhouse_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect public Greenhouse job-board postings for configured employers.

    Greenhouse's public Job Board GET endpoint does not require authentication.
    The documented updated_at field describes an update time, not necessarily
    the original posting time, so it is intentionally not mapped to source_posted_at.
    """
    boards = config.get("greenhouse_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Greenhouse is enabled but no public greenhouse_boards are configured")

    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []

    for board in boards:
        token = str(board.get("token") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        if not token or not company:
            failures.append(f"{token or '<missing-token>'}: invalid board configuration")
            continue

        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            response = requests.get(
                endpoint,
                params={"content": "true"},
                headers={**UA, "Accept": "application/json"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
                raise ValueError("Greenhouse response did not contain a jobs list")
            successful_boards += 1
        except Exception as exc:
            failures.append(f"{token}: {exc!r}")
            log.warning("greenhouse: board=%s failed: %r", token, exc)
            continue

        for item in payload["jobs"]:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("id")
            title = str(item.get("title") or "").strip()
            url = str(item.get("absolute_url") or "").strip()
            if raw_id is None or not title or not url:
                continue

            source_id = f"gh-{token}-{raw_id}"
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            raw_location = item.get("location")
            if isinstance(raw_location, dict):
                location = str(raw_location.get("name") or "").strip()
            elif isinstance(raw_location, str):
                location = raw_location.strip()
            else:
                location = ""

            if not location:
                offices = item.get("offices") or []
                office_names = []
                if isinstance(offices, list):
                    for office in offices:
                        if not isinstance(office, dict):
                            continue
                        label = str(office.get("location") or office.get("name") or "").strip()
                        if label and label not in office_names:
                            office_names.append(label)
                location = ", ".join(office_names)

            description_html = html_lib.unescape(str(item.get("content") or ""))
            description = BeautifulSoup(
                description_html, "html.parser"
            ).get_text(" ", strip=True)
            departments = item.get("departments") or []
            department_names = [
                str(dept.get("name")).strip()
                for dept in departments
                if isinstance(dept, dict) and str(dept.get("name") or "").strip()
            ] if isinstance(departments, list) else []
            if department_names:
                description = f"{description} Department: {', '.join(department_names)}".strip()

            # first_published records when the job post first went live.
            # Never substitute updated_at, which may reflect a later edit.
            published_raw = item.get("first_published")
            published_at = (
                parse_relative(str(published_raw))
                if published_raw not in (None, "")
                else None
            )
            if published_at is None:
                posted_precision = "unknown"
            elif isinstance(published_raw, str) and re.search(
                r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", published_raw
            ):
                posted_precision = "minute"
            else:
                posted_precision = "date"

            jobs.append(normalize_job(
                "greenhouse",
                source_id,
                company,
                title,
                location,
                url,
                published_at,
                posted_precision,
                description,
            ))

    if successful_boards == 0:
        details = "; ".join(failures) or "no valid boards configured"
        raise RuntimeError(f"All configured Greenhouse boards failed: {details}")

    if failures:
        log.warning(
            "greenhouse: partial board failures=%s successful_boards=%s",
            len(failures),
            successful_boards,
        )
    log.info(
        "greenhouse: boards=%s successful=%s failed=%s jobs=%s",
        len(boards),
        successful_boards,
        len(failures),
        len(jobs),
    )
    return jobs


COLLECTORS = {
    "linkedin": linkedin_collect,
    "naukri": lambda config: naukri_collect(),
    "instahyre": instahyre_collect,
    "greenhouse": greenhouse_collect,
}


def run_source(source: str, config: dict[str, Any]) -> None:
    if source_state.get(source, {}).get("running"):
        log.warning("%s: previous run still active; skipping this cycle", source)
        return

    started_at = now()
    source_state.setdefault(source, {})["running"] = True
    try:
        jobs = COLLECTORS[source](config)
        new_jobs = upsert_jobs(jobs, config)
        refresh_job_evaluations(config)
        refresh_notification_decisions(config)

        # Deliver immediately after a discovery cycle queues eligible jobs.
        # The background worker remains as a fallback/retry path.
        try:
            from v2.telegram import credentials_available, deliver_queued_notifications

            if credentials_available():
                delivered = deliver_queued_notifications(50)
                if delivered:
                    log.info("telegram: delivered=%s source=%s", delivered, source)
        except Exception:
            log.exception("telegram immediate delivery failed source=%s", source)

        finished = now()
        record_run(source, started_at, finished, len(jobs), new_jobs)
        source_state[source] = {
            "running": False,
            "last_success": iso(finished),
            "jobs_seen": len(jobs),
            "new_jobs": new_jobs,
            "error": None,
        }
        log.info("%s: seen=%s new=%s", source, len(jobs), new_jobs)
    except Exception as exc:
        finished = now()
        record_run(source, started_at, finished, 0, 0, str(exc))
        source_state[source] = {
            "running": False,
            "last_success": source_state.get(source, {}).get("last_success"),
            "jobs_seen": 0,
            "new_jobs": 0,
            "error": repr(exc),
        }
        log.exception("%s collector failed", source)


async def notification_worker() -> None:
    while not stop_event.is_set():
        try:
            from v2.telegram import (
                credentials_available,
                deliver_queued_notifications,
                recover_stale_claims,
            )

            await asyncio.to_thread(recover_stale_claims)

            if credentials_available():
                delivered = await asyncio.to_thread(deliver_queued_notifications, 10)
                if delivered:
                    log.info("telegram: delivered=%s", delivered)
        except Exception:
            log.exception("telegram worker failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass


async def scheduler() -> None:
    next_run = {name: 0.0 for name in COLLECTORS}
    while not stop_event.is_set():
        config = get_config()
        current = time.monotonic()
        intervals = config.get("poll_seconds", {})
        enabled = config.get("source_enabled", {})

        for name in COLLECTORS:
            if not enabled.get(name, True):
                continue
            if name == "linkedin" and _linkedin_cooldown_remaining() > 0:
                continue
            if source_state.get(name, {}).get("running"):
                continue
            interval = max(60, int(intervals.get(name, 600)))
            if current >= next_run[name]:
                next_run[name] = current + interval
                asyncio.create_task(asyncio.to_thread(run_source, name, config))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=2)
        except asyncio.TimeoutError:
            pass


@app.on_event("startup")
async def startup() -> None:
    init_db()
    ensure_runtime_config()
    config = get_config()
    refresh_job_evaluations(config)
    refresh_notification_decisions(config)
    ensure_config_token()
    app.state.scheduler_task = asyncio.create_task(scheduler())
    app.state.notification_worker_task = asyncio.create_task(notification_worker())


@app.on_event("shutdown")
async def shutdown() -> None:
    stop_event.set()
    for task_name in ("scheduler_task", "notification_worker_task"):
        task = getattr(app.state, task_name, None)
        if task:
            await task


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": app.version,
        "uptime_seconds": int(time.monotonic() - started),
        "db": str(DB_PATH),
        "sources": source_state,
    }



@app.get("/api/config")
def read_config():
    return {
        "config": get_config(),
        "runtime_path": str(RUNTIME_CONFIG_PATH),
        "config_update_protected": True,
    }


@app.put("/api/config")
def update_config(payload: dict[str, Any], x_config_token: str | None = Header(default=None, alias="X-Config-Token")):
    authorize_config_update(x_config_token)
    saved = save_config(payload)
    refresh_job_evaluations(saved)
    refresh_notification_decisions(saved)
    return {"config": saved, "runtime_path": str(RUNTIME_CONFIG_PATH)}


@app.get("/api/latency-summary")
def latency_summary(hours: int = 24):
    hours = max(1, min(hours, 168))
    cutoff = iso(now() - dt.timedelta(hours=hours))

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT source, discovery_latency_seconds
            FROM jobs
            WHERE discovered_at >= ?
              AND discovery_latency_seconds IS NOT NULL
              AND discovery_latency_seconds >= 0
              AND source IN ('linkedin', 'naukri', 'instahyre', 'greenhouse')
            ORDER BY source, discovery_latency_seconds ASC
        """, (cutoff,)).fetchall()

    by_source: dict[str, list[int]] = {}
    for source, latency in rows:
        by_source.setdefault(source, []).append(int(latency))

    def percentile(values: list[int], p: float) -> int | None:
        if not values:
            return None
        index = min(len(values) - 1, max(0, round((len(values) - 1) * p)))
        return values[index]

    summary = {}
    for source in ("linkedin", "naukri", "instahyre", "greenhouse"):
        values = by_source.get(source, [])
        under_60 = sum(1 for value in values if value <= 60)
        under_120 = sum(1 for value in values if value <= 120)
        under_300 = sum(1 for value in values if value <= 300)
        summary[source] = {
            "samples": len(values),
            "p50_seconds": percentile(values, 0.50),
            "p90_seconds": percentile(values, 0.90),
            "max_seconds": max(values) if values else None,
            "under_60_seconds": under_60,
            "under_120_seconds": under_120,
            "under_300_seconds": under_300,
        }

    return {"hours": hours, "sources": summary}


@app.get("/api/source-status")
def source_status():
    config = get_config()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT sr.source, sr.finished_at, sr.jobs_seen, sr.new_jobs
            FROM source_runs sr
            JOIN (
                SELECT source, MAX(finished_at) AS latest_finished_at
                FROM source_runs
                GROUP BY source
            ) latest
              ON latest.source = sr.source
             AND latest.latest_finished_at = sr.finished_at
            ORDER BY sr.source
        """).fetchall()

    history = {
        row[0]: {
            "last_run": row[1],
            "jobs_seen": row[2] or 0,
            "new_jobs": row[3] or 0,
        }
        for row in rows
    }

    sources = []
    for source in ("linkedin", "naukri", "instahyre", "greenhouse"):
        item = history.get(source, {})
        sources.append({
            "source": source,
            "enabled": bool(config.get("source_enabled", {}).get(source, True)),
            "last_run": item.get("last_run"),
            "jobs_seen": item.get("jobs_seen", 0),
            "new_jobs": item.get("new_jobs", 0),
            "runtime": source_state.get(source, {}),
        })

    return {"sources": sources}


@app.get("/api/dedupe-candidates")
def dedupe_candidates(limit: int = 100):
    limit = max(1, min(limit, 500))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, source, source_job_id, company, title, location, url, description
            FROM jobs
            WHERE source IN ('linkedin', 'naukri', 'instahyre', 'greenhouse')
            ORDER BY id ASC
        """).fetchall()

    by_identity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        identity = canonical_identity(item)
        key = (identity["company_norm"], identity["title_norm"])
        if key[0] and key[1]:
            by_identity.setdefault(key, []).append(item)

    candidates = []
    for group in by_identity.values():
        sources = {item["source"] for item in group}
        if len(sources) < 2:
            continue

        for i, left in enumerate(group):
            for right in group[i + 1:]:
                if left["source"] == right["source"]:
                    continue
                score, method = canonical_match_score(left, right)
                if score <= 0:
                    continue
                candidates.append({
                    "job_a_id": left["id"],
                    "source_a": left["source"],
                    "source_job_id_a": left["source_job_id"],
                    "title_a": left["title"],
                    "company_a": left["company"],
                    "location_a": left["location"],
                    "job_b_id": right["id"],
                    "source_b": right["source"],
                    "source_job_id_b": right["source_job_id"],
                    "title_b": right["title"],
                    "company_b": right["company"],
                    "location_b": right["location"],
                    "score": score,
                    "method": method,
                    "auto_link": auto_link_allowed(score, method),
                })

    candidates.sort(key=lambda item: (-item["score"], item["job_a_id"], item["job_b_id"]))
    return {
        "candidates": candidates[:limit],
        "jobs_considered": len(rows),
        "identity_groups": len(by_identity),
    }


@app.get("/api/opportunities")
def opportunities(minutes: int = 60, limit: int = 100, today_only: bool = False):
    minutes = max(1, min(minutes, 10080))
    limit = max(1, min(limit, 500))
    cutoff = iso(current_day_start_utc()) if today_only else iso(
        now() - dt.timedelta(minutes=minutes)
    )
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT
                co.id,
                co.canonical_url,
                co.company_norm,
                co.title_norm,
                co.location_norm,
                co.first_seen_at,
                co.last_seen_at,
                co.representative_job_id,
                COUNT(j.id) AS observation_count,
                COUNT(DISTINCT j.source) AS source_count,
                GROUP_CONCAT(DISTINCT j.source) AS sources
            FROM canonical_opportunities co
            JOIN jobs j ON j.canonical_opportunity_id = co.id
            WHERE co.last_seen_at >= ?
            GROUP BY co.id
            ORDER BY co.last_seen_at DESC
            LIMIT ?
        """, (cutoff, limit)).fetchall()
    return {
        "opportunities": [dict(row) for row in rows]
    }


@app.get("/api/jobs")
def jobs(minutes: int = 60, limit: int = 100, today_only: bool = False):
    config = get_config()
    minutes = max(1, min(minutes, 10080))
    limit = max(1, min(limit, 500))
    cutoff = (
        iso(current_day_start_utc())
        if today_only
        else iso(now() - dt.timedelta(minutes=minutes))
    )
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE discovered_at >= ?
            ORDER BY COALESCE(source_posted_at, discovered_at) DESC, discovered_at DESC
            LIMIT ?
        """, (cutoff, limit)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        details = match_details(item, config)
        alertability = alertability_details(item, details, config)
        item["likely_match"] = details["match"]
        item["match_score"] = details["score"]
        item["match_reasons"] = details["reasons"]
        item["experience_min_years"] = details["experience_min_years"]
        item["experience_max_years"] = details["experience_max_years"]
        item["alertable"] = alertability["alertable"]
        item["alertability_reasons"] = alertability["reasons"]
        item["canonical_opportunity_id"] = item.get("canonical_opportunity_id")
        item["canonical_match_method"] = item.get("canonical_match_method")
        item["canonical_match_confidence"] = item.get("canonical_match_confidence")
        result.append(item)
    return {"jobs": result}


@app.get("/api/notification-queue")
def notification_queue(limit: int = 100):
    limit = max(1, min(limit, 500))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT
                nl.canonical_opportunity_id,
                nl.status,
                nl.candidate_job_id,
                nl.created_at,
                nl.updated_at,
                nl.sent_at,
                nl.last_error,
                nl.decision_reason_json,
                j.source,
                j.source_job_id,
                j.company,
                j.title,
                j.location,
                j.url,
                j.source_posted_at,
                j.discovered_at,
                e.score,
                e.reasons_json,
                e.experience_min_years,
                e.experience_max_years
            FROM notification_ledger nl
            LEFT JOIN jobs j ON j.id=nl.candidate_job_id
            LEFT JOIN job_evaluations e ON e.job_id=nl.candidate_job_id
            WHERE nl.status IN ('queued','failed')
            ORDER BY nl.created_at ASC
            LIMIT ?
        """, (limit,)).fetchall()

    result=[]
    for row in rows:
        item=dict(row)
        item["decision_reasons"]=json.loads(item.pop("decision_reason_json") or "[]")
        item["match_reasons"]=json.loads(item.pop("reasons_json") or "[]")
        result.append(item)
    return {"notifications": result}


@app.get("/api/opportunities/{opportunity_id}")
def opportunity_detail(opportunity_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        opportunity = conn.execute("""
            SELECT id, canonical_url, company_norm, title_norm, location_norm,
                   first_seen_at, last_seen_at, representative_job_id
            FROM canonical_opportunities
            WHERE id=?
        """, (opportunity_id,)).fetchone()
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        observations = conn.execute("""
            SELECT id, source, source_job_id, company, title, location, url,
                   source_posted_at, posted_precision, discovered_at,
                   discovery_latency_seconds, canonical_match_method,
                   canonical_match_confidence
            FROM jobs
            WHERE canonical_opportunity_id=?
            ORDER BY COALESCE(source_posted_at, discovered_at) DESC, id ASC
        """, (opportunity_id,)).fetchall()

    return {
        "opportunity": dict(opportunity),
        "observations": [dict(row) for row in observations],
    }


@app.get("/api/daily-summary")
def daily_summary():
    cutoff = iso(current_day_start_utc())
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE discovered_at >= ?", (cutoff,)
        ).fetchone()[0]
        matched = conn.execute("""
            SELECT COUNT(*)
            FROM jobs j
            JOIN job_evaluations e ON e.job_id=j.id
            WHERE j.discovered_at >= ? AND e.match=1
        """, (cutoff,)).fetchone()[0]
        alertable = conn.execute("""
            SELECT COUNT(*)
            FROM jobs j
            JOIN job_evaluations e ON e.job_id=j.id
            WHERE j.discovered_at >= ? AND e.alertable=1
        """, (cutoff,)).fetchone()[0]
        alerted = conn.execute("""
            SELECT COUNT(*)
            FROM notification_ledger nl
            JOIN jobs j ON j.id=nl.candidate_job_id
            WHERE j.discovered_at >= ? AND nl.status='sent'
        """, (cutoff,)).fetchone()[0]

    local_now = now().astimezone(IST)
    return {
        "date": local_now.strftime("%Y-%m-%d"),
        "timezone": "Asia/Kolkata",
        "total_jobs_discovered": total,
        "matched_jobs": matched,
        "alertable_jobs": alertable,
        "alerts_sent": alerted,
        "resets_at_local_midnight": True,
    }


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard/")


if DASHBOARD_PATH.exists():
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_PATH, html=True), name="dashboard")