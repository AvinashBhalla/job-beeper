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
import uuid
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from v2 import auth, google_oauth, resume_parser, telegram_linking, user_preferences, user_notifications

from v2.dedupe import auto_link_allowed, canonical_identity, canonical_match_score, canonicalize_url
from v2.gemini_extractor import cached_matcher_experience, shadow_extract_jobs, shadow_status

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
LINKEDIN_MIN_REQUEST_INTERVAL_SECONDS = 4.0
LINKEDIN_RATE_LIMIT_BASE_COOLDOWN_SECONDS = 300
LINKEDIN_RATE_LIMIT_MAX_COOLDOWN_SECONDS = 4 * 60 * 60
LINKEDIN_RATE_LIMIT_STREAK_RESET_SECONDS = 24 * 60 * 60
LINKEDIN_DETAIL_WORKERS = 1
LINKEDIN_FAST_TARGETS_PER_SCAN = 2
LINKEDIN_DEEP_SCAN_SECONDS = 1800
LINKEDIN_DEEP_PAGE_BATCH = 1
LINKEDIN_FAST_TPR = "r21600"
LINKEDIN_DEEP_TPR = "r21600"
INITIAL_SNAPSHOT_BASELINE_SOURCES = frozenset({"lever"})

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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prevent_api_response_caching(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


db_lock = threading.Lock()
started = time.monotonic()
source_state: dict[str, dict[str, Any]] = {}
linkedin_last_deep_scan_at: str | None = None
linkedin_fast_target_cursor = 0
linkedin_http_lock = threading.Lock()
linkedin_last_http_request_monotonic = 0.0
linkedin_rate_limited_until_monotonic = 0.0
linkedin_last_rate_limit_monotonic = 0.0
linkedin_rate_limit_streak = 0
linkedin_rate_limit_generation = 0
stop_event = asyncio.Event()
config_lock = threading.RLock()
source_metrics_lock = threading.Lock()
active_source_metrics: dict[str, dict[str, Any]] = {}
SOURCE_METRIC_FIELDS = (
    "requests_attempted", "responses_received", "request_exceptions",
    "http_2xx", "http_3xx", "http_4xx", "http_5xx", "http_429",
    "retry_attempts", "request_duration_ms_total",
    "pages_attempted", "pages_succeeded", "pages_failed",
    "boards_attempted", "boards_succeeded", "boards_failed",
)


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
    # Version 8 reduces LinkedIn request pressure. Older persisted configs may
    # retain the previous 60-second poll interval, so migrate it explicitly.
    if current_version < 8 <= default_version:
        merged.setdefault("poll_seconds", {})["linkedin"] = max(
            120, int(defaults.get("poll_seconds", {}).get("linkedin", 120) or 120)
        )

    # Version 9 makes the configured match threshold the only relevance
    # threshold for an otherwise-valid match. Unknown experience is neutral,
    # not a separate reason to withhold Telegram alerts.
    if current_version < 9 <= default_version:
        merged["require_explicit_experience_for_alerts"] = False

    # Version 10 applies the free-first LinkedIn low-pressure request budget:
    # 180-second poll cadence. Do not keep a prior 120-second setting.
    if current_version < 10 <= default_version:
        merged.setdefault("poll_seconds", {})["linkedin"] = max(
            180, int(defaults.get("poll_seconds", {}).get("linkedin", 180) or 180)
        )
    # Version 11 introduces Ashby; never enable a new source via migration.
    if current_version < 11 <= default_version:
        merged.setdefault("source_enabled", {})["ashby"] = False
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
        if current_version < 11 <= default_version:
            merged["source_enabled"]["ashby"] = False
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

    ashby_boards = config.get("ashby_boards", [])
    if not isinstance(ashby_boards, list):
        raise HTTPException(status_code=422, detail="ashby_boards must be a list.")
    if len(ashby_boards) > 20:
        raise HTTPException(status_code=422, detail="ashby_boards cannot contain more than 20 boards.")
    normalized_ashby_boards: list[dict[str, str]] = []
    seen_ashby_board_names: set[str] = set()
    for board in ashby_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each Ashby board must be an object.")
        name = board.get("board")
        company = board.get("company")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name.strip()):
            raise HTTPException(status_code=422, detail="Each Ashby board requires a valid public board name.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each Ashby board requires a company label of at most 120 characters.")
        name = name.strip()
        if name.lower() in seen_ashby_board_names:
            raise HTTPException(status_code=422, detail=f"Duplicate Ashby board name: {name}.")
        seen_ashby_board_names.add(name.lower())
        normalized_ashby_boards.append({"board": name, "company": company.strip()})
    config["ashby_boards"] = normalized_ashby_boards

    source_enabled = config.get("source_enabled", {})
    if not isinstance(source_enabled, dict):
        raise HTTPException(status_code=422, detail="source_enabled must be an object.")
    config["source_enabled"] = {
        "linkedin": bool(source_enabled.get("linkedin", True)),
        "naukri": bool(source_enabled.get("naukri", True)),
        "instahyre": bool(source_enabled.get("instahyre", True)),
        "greenhouse": bool(source_enabled.get("greenhouse", False)),
        "ashby": bool(source_enabled.get("ashby", False)),
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
            "ashby": 1800,
        }.items()
    }

    return config


def suppress_preexisting_unknown_experience_pending_notifications(
    cutoff_minutes: int = 10,
) -> int:
    """Avoid replaying old pending matches when migrating away from the hidden experience gate.

    Only pending, never-attempted opportunities that were specifically blocked by
    the old explicit-experience policy and are older than the short live window
    are suppressed. New pending matches stay eligible under the updated policy.
    """
    if not DB_PATH.exists():
        return 0
    cutoff = iso(now() - dt.timedelta(minutes=max(1, cutoff_minutes)))
    timestamp = iso(now())
    reasons = json.dumps([
        "suppressed during alert-policy migration",
        "not replayed to avoid a historical Telegram alert burst",
        "future fresh source observations will use the updated threshold policy",
    ], ensure_ascii=False)
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"notification_ledger", "jobs", "job_evaluations"}.issubset(tables):
            return 0
        cursor = conn.execute("""
            UPDATE notification_ledger
            SET status='suppressed',
                candidate_job_id=NULL,
                updated_at=?,
                next_attempt_at=NULL,
                decision_reason_json=?
            WHERE status='pending'
              AND candidate_job_id IS NULL
              AND attempt_count=0
              AND sent_at IS NULL
              AND created_at < ?
              AND canonical_opportunity_id IN (
                  SELECT DISTINCT j.canonical_opportunity_id
                  FROM jobs j
                  JOIN job_evaluations e ON e.job_id=j.id
                  WHERE j.canonical_opportunity_id IS NOT NULL
                    AND e.match=1
                    AND e.alertable=0
                    AND e.alertability_reasons_json LIKE
                        '%explicit experience required for alerts%'
              )
        """, (timestamp, reasons, cutoff))
        conn.commit()
        return cursor.rowcount


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

    current_version = int(current.get("config_version", 1) or 1)
    default_version = int(defaults.get("config_version", 1) or 1)
    migrate_alert_policy = current_version < 9 <= default_version

    merged = validate_config(_merge_config(defaults, current))
    serialized = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"
    if not RUNTIME_CONFIG_PATH.exists() or RUNTIME_CONFIG_PATH.read_text(encoding="utf-8") != serialized:
        tmp = RUNTIME_CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(serialized, encoding="utf-8")
        os.replace(tmp, RUNTIME_CONFIG_PATH)

    # init_db runs before startup config migration. Preserve recently discovered
    # pending matches, but suppress older entries that were held only by the
    # retired experience gate so the new policy does not replay historical alerts.
    if migrate_alert_policy:
        suppressed = suppress_preexisting_unknown_experience_pending_notifications()
        if suppressed:
            log.warning(
                "alert policy migration suppressed %s historical pending notifications",
                suppressed,
            )


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


def normalize_job(
    source: str,
    source_id: str,
    company: str,
    title: str,
    location: str,
    url: str,
    posted_at: dt.datetime | None,
    posted_precision: str,
    description: str = "",
    description_format: str = "plain",
    source_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "description_format": (
            "markdown" if str(description_format).lower() == "markdown" else "plain"
        ),
        "source_details": source_details if isinstance(source_details, dict) else {},
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
    job = dict(row)
    if job.get("experience_min_years") is not None or job.get("experience_max_years") is not None:
        job["jd_experience_min_years"] = job.get("experience_min_years")
        job["jd_experience_max_years"] = job.get("experience_max_years")
    # Reuse only a fresh, exact-JD Gemini cache result that has validated
    # verbatim evidence for required total-professional experience. The regex
    # parser remains the fallback whenever Gemini is unavailable or ambiguous.
    trusted_experience = cached_matcher_experience(job, conn)
    if trusted_experience:
        job["jd_experience_min_years"] = trusted_experience["experience_min_years"]
        job["jd_experience_max_years"] = trusted_experience["experience_max_years"]
        job["jd_experience_source"] = "gemini_verified"
    return job


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
        job.get("last_seen_at") or job["discovered_at"],
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
            description_format TEXT NOT NULL DEFAULT 'plain',
            experience_min_years REAL,
            experience_max_years REAL,
            experience_provenance TEXT NOT NULL DEFAULT 'unknown',
            experience_confidence TEXT NOT NULL DEFAULT 'unknown',
            source_details_json TEXT NOT NULL DEFAULT '{}',
            source_initial_baseline INTEGER NOT NULL DEFAULT 0,
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
            error TEXT,
            run_id TEXT,
            outcome TEXT,
            duration_seconds REAL,
            error_type TEXT,
            http_status INTEGER,
            retry_after_seconds REAL,
            cooldown_seconds INTEGER,
            rate_limit_detected_at TEXT,
            requests_attempted INTEGER,
            responses_received INTEGER,
            request_exceptions INTEGER,
            http_2xx INTEGER,
            http_3xx INTEGER,
            http_4xx INTEGER,
            http_5xx INTEGER,
            http_429 INTEGER,
            retry_attempts INTEGER,
            request_duration_ms_total REAL,
            http_status_counts_json TEXT,
            pages_attempted INTEGER,
            pages_succeeded INTEGER,
            pages_failed INTEGER,
            boards_attempted INTEGER,
            boards_succeeded INTEGER,
            boards_failed INTEGER
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS source_feed_state (
            source TEXT PRIMARY KEY,
            feed_updated_at TEXT NOT NULL,
            last_observed_at TEXT NOT NULL,
            feed_age_seconds REAL NOT NULL,
            jobs_count INTEGER NOT NULL,
            payload_sha256 TEXT NOT NULL,
            snapshot_unchanged INTEGER NOT NULL DEFAULT 0
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
        _ensure_column(conn, "jobs", "description_format", "TEXT NOT NULL DEFAULT 'plain'")
        _ensure_column(conn, "jobs", "experience_min_years", "REAL")
        _ensure_column(conn, "jobs", "experience_max_years", "REAL")
        _ensure_column(conn, "jobs", "experience_provenance", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(conn, "jobs", "experience_confidence", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(conn, "jobs", "source_details_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "jobs", "source_initial_baseline", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "jobs", "canonical_opportunity_id", "INTEGER")
        _ensure_column(conn, "jobs", "canonical_match_method", "TEXT")
        _ensure_column(conn, "notification_ledger", "decision_reason_json", "TEXT DEFAULT '[]'")
        _ensure_column(conn, "notification_ledger", "attempt_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "notification_ledger", "next_attempt_at", "TEXT")
        _ensure_column(conn, "notification_ledger", "claimed_at", "TEXT")
        _ensure_column(conn, "jobs", "canonical_match_confidence", "INTEGER")
        _ensure_column(conn, "source_runs", "run_id", "TEXT")
        _ensure_column(conn, "source_runs", "outcome", "TEXT")
        _ensure_column(conn, "source_runs", "duration_seconds", "REAL")
        _ensure_column(conn, "source_runs", "error_type", "TEXT")
        _ensure_column(conn, "source_runs", "http_status", "INTEGER")
        _ensure_column(conn, "source_runs", "retry_after_seconds", "REAL")
        _ensure_column(conn, "source_runs", "cooldown_seconds", "INTEGER")
        _ensure_column(conn, "source_runs", "rate_limit_detected_at", "TEXT")
        _ensure_column(conn, "source_runs", "requests_attempted", "INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_source_runs_linkedin_429 "
            "ON source_runs(source, http_status, rate_limit_detected_at)"
        )
        _ensure_column(conn, "source_runs", "responses_received", "INTEGER")
        _ensure_column(conn, "source_runs", "request_exceptions", "INTEGER")
        _ensure_column(conn, "source_runs", "http_2xx", "INTEGER")
        _ensure_column(conn, "source_runs", "http_3xx", "INTEGER")
        _ensure_column(conn, "source_runs", "http_4xx", "INTEGER")
        _ensure_column(conn, "source_runs", "http_5xx", "INTEGER")
        _ensure_column(conn, "source_runs", "http_429", "INTEGER")
        _ensure_column(conn, "source_runs", "retry_attempts", "INTEGER")
        _ensure_column(conn, "source_runs", "request_duration_ms_total", "REAL")
        _ensure_column(conn, "source_runs", "http_status_counts_json", "TEXT")
        _ensure_column(conn, "source_runs", "pages_attempted", "INTEGER")
        _ensure_column(conn, "source_runs", "pages_succeeded", "INTEGER")
        _ensure_column(conn, "source_runs", "pages_failed", "INTEGER")
        _ensure_column(conn, "source_runs", "boards_attempted", "INTEGER")
        _ensure_column(conn, "source_runs", "boards_succeeded", "INTEGER")
        _ensure_column(conn, "source_runs", "boards_failed", "INTEGER")
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
    auth.init_auth_schema(DB_PATH)
    user_preferences.init_preferences_schema(DB_PATH)
    telegram_linking.init_schema(DB_PATH)
    user_notifications.init_schema(DB_PATH)
    user_preferences.migrate_first_admin_preferences(DB_PATH, get_config())


def upsert_jobs(
    jobs: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
    source_run_started_at: dt.datetime | None = None,
) -> int:
    new_count = 0
    affected_job_ids: list[int] = []
    config = config or get_config()
    baseline_cutoff_text = iso(source_run_started_at or now())
    baseline_pending_by_source: dict[str, bool] = {}

    with db_lock, sqlite3.connect(DB_PATH) as conn:
        def mark_initial_baseline(job_id: int, source: str) -> None:
            source_key = source.strip().lower()
            if source_key not in INITIAL_SNAPSHOT_BASELINE_SOURCES:
                return
            if source_key not in baseline_pending_by_source:
                prior_success = conn.execute(
                    "SELECT 1 FROM source_runs WHERE source=? AND outcome='success' LIMIT 1",
                    (source_key,),
                ).fetchone()
                baseline_pending_by_source[source_key] = prior_success is None
            if not baseline_pending_by_source[source_key]:
                return

            canonical = conn.execute(
                "SELECT canonical_opportunity_id FROM jobs WHERE id=?",
                (int(job_id),),
            ).fetchone()
            if not canonical or not canonical[0]:
                return
            first_seen = conn.execute(
                "SELECT first_seen_at FROM canonical_opportunities WHERE id=?",
                (int(canonical[0]),),
            ).fetchone()
            first_seen_at = parse_relative(first_seen[0]) if first_seen else None
            cutoff_at = parse_relative(baseline_cutoff_text)
            if first_seen_at and cutoff_at and first_seen_at >= cutoff_at:
                conn.execute(
                    "UPDATE jobs SET source_initial_baseline=1 WHERE id=?",
                    (int(job_id),),
                )

        for incoming in jobs:
            j = dict(incoming)
            incoming_description = str(j.get("description") or "")
            experience_details = _experience_provenance_details(j)
            j["experience_min_years"] = experience_details["min_years"]
            j["experience_max_years"] = experience_details["max_years"]
            j["experience_provenance"] = experience_details["provenance"]
            j["experience_confidence"] = experience_details["confidence"]
            incoming_description_format = (
                "markdown"
                if str(j.get("description_format") or "plain").lower() == "markdown"
                else "plain"
            )
            source_details = j.get("source_details")
            source_details_json = json.dumps(
                source_details if isinstance(source_details, dict) else {},
                ensure_ascii=False,
                sort_keys=True,
            )
            observed_at = parse_relative(j.get("discovered_at"))
            last_seen_at = parse_relative(j.get("last_seen_at")) or observed_at
            if (
                last_seen_at
                and observed_at
                and last_seen_at < observed_at
            ):
                last_seen_at = observed_at
            incoming_posted_at = parse_relative(j.get("source_posted_at"))
            if observed_at and incoming_posted_at and incoming_posted_at > observed_at:
                j["source_posted_at"] = None
                j["posted_precision"] = "unknown"
                j["discovery_latency_seconds"] = None

            existing = conn.execute(
                """SELECT
                       id, canonical_opportunity_id, discovered_at,
                       source_posted_at, posted_precision, description,
                       description_format, experience_min_years,
                       experience_max_years, experience_provenance,
                       experience_confidence
                   FROM jobs
                   WHERE source=? AND source_job_id=?""",
                (j["source"], j["source_job_id"]),
            ).fetchone()
            if existing:
                experience_rank = {
                    "unknown": 0,
                    "inferred": 1,
                    "description": 2,
                    "employer_stated": 3,
                }
                confidence_rank = {
                    "unknown": 0,
                    "low": 1,
                    "medium": 2,
                    "high": 3,
                }
                existing_experience_rank = (
                    experience_rank.get(str(existing[9] or "unknown"), 0),
                    confidence_rank.get(str(existing[10] or "unknown"), 0),
                )
                incoming_experience_rank = (
                    experience_rank.get(str(j["experience_provenance"]), 0),
                    confidence_rank.get(str(j["experience_confidence"]), 0),
                )
                if incoming_experience_rank < existing_experience_rank:
                    j["experience_min_years"] = existing[7]
                    j["experience_max_years"] = existing[8]
                    j["experience_provenance"] = existing[9]
                    j["experience_confidence"] = existing[10]

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
                    UPDATE jobs SET
                    last_seen_at=CASE
                        WHEN julianday(?) > julianday(last_seen_at) THEN ?
                        ELSE last_seen_at
                    END,
                    source_posted_at=COALESCE(?, source_posted_at),
                    posted_precision=CASE WHEN ?='minute' THEN ? ELSE posted_precision END,
                    description=CASE
                        WHEN ?='markdown' OR (description_format!='markdown' AND length(?) > length(description)) THEN ?
                        ELSE description
                    END,
                    description_format=CASE
                        WHEN ?='markdown' OR (description_format!='markdown' AND length(?) > length(description)) THEN ?
                        ELSE description_format
                    END,
                    experience_min_years=COALESCE(?, experience_min_years),
                    experience_max_years=COALESCE(?, experience_max_years),
                    experience_provenance=CASE
                        WHEN ?!='unknown' THEN ?
                        ELSE experience_provenance
                    END,
                    experience_confidence=CASE
                        WHEN ?!='unknown' THEN ?
                        ELSE experience_confidence
                    END,
                    source_details_json=CASE
                        WHEN ? <> '{}' THEN ?
                        ELSE source_details_json
                    END
                    WHERE id=?
                """, (
                    iso(last_seen_at) or j["discovered_at"],
                    iso(last_seen_at) or j["discovered_at"],
                    posted_at_for_update, precision_for_update,
                    precision_for_update,
                    incoming_description_format, incoming_description, incoming_description,
                    incoming_description_format, incoming_description, incoming_description_format,
                    j["experience_min_years"], j["experience_max_years"],
                    j["experience_provenance"], j["experience_provenance"],
                    j["experience_confidence"], j["experience_confidence"],
                    source_details_json, source_details_json, existing[0],
                ))

                newly_canonicalized = not existing[1]
                if newly_canonicalized:
                    _assign_canonical(conn, int(existing[0]))
                mark_initial_baseline(int(existing[0]), str(j["source"]))

                existing_description = str(existing[5] or "")
                existing_format = str(existing[6] or "plain")
                update_description = (
                    (
                        incoming_description_format == "markdown"
                        and (
                            existing_format != "markdown"
                            or incoming_description != existing_description
                        )
                    )
                    or (
                        existing_format != "markdown"
                        and len(incoming_description) > len(existing_description)
                    )
                )
                next_description = (
                    incoming_description if update_description else existing_description
                )
                next_format = (
                    incoming_description_format if update_description else existing_format
                )
                next_posted_at = posted_at_for_update or existing[3]
                next_precision = (
                    precision_for_update
                    if precision_for_update == "minute"
                    else existing[4]
                )
                experience_inputs_changed = (
                    j["experience_min_years"] != existing[7]
                    or j["experience_max_years"] != existing[8]
                    or j["experience_provenance"] != existing[9]
                    or j["experience_confidence"] != existing[10]
                )
                evaluation_inputs_changed = (
                    next_description != existing_description
                    or next_format != existing_format
                    or next_posted_at != existing[3]
                    or next_precision != existing[4]
                    or experience_inputs_changed
                )
                if evaluation_inputs_changed:
                    _persist_job_evaluation(conn, int(existing[0]), config)
                if evaluation_inputs_changed or newly_canonicalized:
                    affected_job_ids.append(int(existing[0]))
            else:
                if j.get("needs_jd_enrichment"):
                    j = enrich_linkedin_job(j)

                # LinkedIn enrichment may replace the original search snippet
                # with a full JD; persist the post-enrichment values.
                incoming_description = str(j.get("description") or "")
                experience_details = _experience_provenance_details(j)
                j["experience_min_years"] = experience_details["min_years"]
                j["experience_max_years"] = experience_details["max_years"]
                j["experience_provenance"] = experience_details["provenance"]
                j["experience_confidence"] = experience_details["confidence"]
                incoming_description_format = (
                    "markdown"
                    if str(j.get("description_format") or "plain").lower() == "markdown"
                    else "plain"
                )
                source_details = j.get("source_details")
                source_details_json = json.dumps(
                    source_details if isinstance(source_details, dict) else {},
                    ensure_ascii=False,
                    sort_keys=True,
                )

                cur = conn.execute("""
                    INSERT INTO jobs (
                        source, source_job_id, company, title, location, url,
                        source_posted_at, posted_precision, discovered_at,
                        discovery_latency_seconds, description, description_format,
                        experience_min_years, experience_max_years, experience_provenance,
                        experience_confidence, source_details_json, first_seen_at,
                        last_seen_at, source_initial_baseline
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                """, (
                    j["source"], j["source_job_id"], j["company"], j["title"],
                    j["location"], j["url"], j["source_posted_at"],
                    j["posted_precision"], j["discovered_at"],
                    j["discovery_latency_seconds"], incoming_description,
                    incoming_description_format, j["experience_min_years"],
                    j["experience_max_years"], j["experience_provenance"],
                    j["experience_confidence"], source_details_json,
                    j["discovered_at"], iso(last_seen_at) or j["discovered_at"]
                ))
                _assign_canonical(conn, int(cur.lastrowid))
                mark_initial_baseline(int(cur.lastrowid), str(j["source"]))
                _persist_job_evaluation(conn, int(cur.lastrowid), config)
                affected_job_ids.append(int(cur.lastrowid))
                new_count += 1
        conn.commit()
    # Shared ingestion evaluates only the touched jobs for every configured user.
    if affected_job_ids:
        refresh_configured_user_evaluations(affected_job_ids)
    return new_count

# Increment whenever deterministic matching/alertability rules change so
# persisted evaluations are invalidated and recomputed under the new rules.
MATCHER_RULES_VERSION = 3


def _config_fingerprint(config: dict[str, Any]) -> str:
    payload = {
        "config": config,
        "matcher_rules_version": MATCHER_RULES_VERSION,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


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


def _persist_user_job_evaluation(
    conn: sqlite3.Connection,
    user_id: int,
    job_id: int,
    preferences: dict[str, Any],
) -> dict[str, Any]:
    job = _job_for_canonical(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} does not exist")
    details = match_details(job, preferences)
    evaluated_at = iso(now())
    fingerprint = user_preferences.preferences_fingerprint(
        preferences, MATCHER_RULES_VERSION
    )
    # These legacy alertability fields are admin-policy metadata only.
    # Member delivery uses user_notifications with explicit opt-in, a
    # user-scoped ledger and a separately linked private Telegram chat.
    alertability_reasons = ["member alerts use separate per-user opt-in and delivery policy"]
    conn.execute(
        """INSERT INTO user_job_evaluations (
               user_id, job_id, preference_fingerprint, evaluated_at, match, score,
               reasons_json, experience_min_years, experience_max_years,
               alertable, alertability_reasons_json
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
           ON CONFLICT(user_id, job_id) DO UPDATE SET
               preference_fingerprint=excluded.preference_fingerprint,
               evaluated_at=excluded.evaluated_at,
               match=excluded.match,
               score=excluded.score,
               reasons_json=excluded.reasons_json,
               experience_min_years=excluded.experience_min_years,
               experience_max_years=excluded.experience_max_years,
               alertable=0,
               alertability_reasons_json=excluded.alertability_reasons_json""",
        (
            user_id, job_id, fingerprint, evaluated_at, int(details["match"]),
            int(details["score"]), json.dumps(details["reasons"], ensure_ascii=False),
            details["experience_min_years"], details["experience_max_years"],
            json.dumps(alertability_reasons),
        ),
    )
    return {**details, "evaluated_at": evaluated_at, "preference_fingerprint": fingerprint}


def refresh_user_job_evaluations(
    user_id: int,
    preferences: dict[str, Any],
    job_ids: list[int] | None = None,
) -> int:
    if not preferences.get("target_roles") or not preferences.get("locations"):
        return 0
    if job_ids and len(job_ids) > 500:
        return sum(
            refresh_user_job_evaluations(user_id, preferences, job_ids[start:start + 500])
            for start in range(0, len(job_ids), 500)
        )
    with sqlite3.connect(DB_PATH) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    if not {"jobs", "user_job_evaluations"}.issubset(tables):
        return 0
    fingerprint = user_preferences.preferences_fingerprint(
        preferences, MATCHER_RULES_VERSION
    )
    changed = 0
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = """SELECT j.id
                 FROM jobs j
                 LEFT JOIN user_job_evaluations e
                   ON e.job_id=j.id AND e.user_id=?
                 WHERE (e.job_id IS NULL OR e.preference_fingerprint != ?)"""
        params: list[Any] = [int(user_id), fingerprint]
        if job_ids:
            placeholders = ",".join("?" for _ in job_ids)
            sql += f" AND j.id IN ({placeholders})"
            params.extend(int(job_id) for job_id in job_ids)
        sql += " ORDER BY j.first_seen_at ASC, j.id ASC"
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            _persist_user_job_evaluation(
                conn, int(user_id), int(row["id"]), preferences
            )
            changed += 1
        conn.commit()
    return changed


def ensure_user_job_evaluations_initialized(
    user_id: int, preferences: dict[str, Any]
) -> int:
    if not preferences.get("target_roles") or not preferences.get("locations"):
        return 0
    with sqlite3.connect(DB_PATH) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"jobs", "user_job_evaluations"}.issubset(tables):
            return 0
        jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        existing = conn.execute(
            "SELECT 1 FROM user_job_evaluations WHERE user_id=? LIMIT 1",
            (int(user_id),),
        ).fetchone()
    if jobs_count and existing is None:
        return refresh_user_job_evaluations(user_id, preferences)
    return 0


def refresh_configured_user_evaluations(job_ids: list[int] | None = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"users", "user_preferences", "jobs", "user_job_evaluations"}.issubset(tables):
            return 0
        conn.row_factory = sqlite3.Row
        users = conn.execute(
            """SELECT u.id, p.preferences_json
               FROM users u
               JOIN user_preferences p ON p.user_id=u.id
               WHERE u.status='active'"""
        ).fetchall()
    total = 0
    for row in users:
        try:
            stored = json.loads(row["preferences_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            continue
        preferences = {**user_preferences.PREFERENCE_DEFAULTS, **stored}
        if preferences.get("target_roles") and preferences.get("locations"):
            total += refresh_user_job_evaluations(int(row["id"]), preferences, job_ids)
    return total


def _alert_age_timestamp(job: dict[str, Any]) -> dt.datetime | None:
    # Greenhouse first-seen time is not evidence of when the employer published
    # the role. Unknown or malformed publication timestamps must remain unknown
    # instead of being made to look fresh by the discovery timestamp.
    if str(job.get("source") or "").strip().lower() == "greenhouse":
        value = job.get("source_posted_at")
        return parse_relative(value) if value else None

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
                is_greenhouse = (
                    str(item.get("source") or "").strip().lower()
                    == "greenhouse"
                )
                is_fresh = (
                    (
                        age_timestamp is not None
                        and age_timestamp >=
                        now_value - dt.timedelta(hours=max_age)
                    )
                    if is_greenhouse
                    else (
                        not age_timestamp
                        or age_timestamp >=
                        now_value - dt.timedelta(hours=max_age)
                    )
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

def _new_source_run_metrics() -> dict[str, Any]:
    return {
        **{field: 0 for field in SOURCE_METRIC_FIELDS},
        "http_status_counts": {},
        "_lock": threading.Lock(),
    }


def _begin_source_run_metrics(source: str) -> None:
    metrics = _new_source_run_metrics()
    with source_metrics_lock:
        active_source_metrics[source] = metrics


def _source_metric_update(source: str, update) -> None:
    with source_metrics_lock:
        metrics = active_source_metrics.get(source)
        if metrics is None:
            return
        with metrics["_lock"]:
            update(metrics)


def _record_source_request(
    source: str,
    *,
    status_code: int | None,
    duration_ms: float,
    exception: bool = False,
    retry_attempt: bool = False,
) -> None:
    def update(metrics: dict[str, Any]) -> None:
        metrics["requests_attempted"] += 1
        metrics["request_duration_ms_total"] += max(0.0, duration_ms)
        if retry_attempt:
            metrics["retry_attempts"] += 1
        if exception:
            metrics["request_exceptions"] += 1
        if status_code is None:
            return
        metrics["responses_received"] += 1
        status_key = str(int(status_code))
        status_counts = metrics["http_status_counts"]
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        if 200 <= status_code < 300:
            metrics["http_2xx"] += 1
        elif 300 <= status_code < 400:
            metrics["http_3xx"] += 1
        elif 400 <= status_code < 500:
            metrics["http_4xx"] += 1
        elif 500 <= status_code < 600:
            metrics["http_5xx"] += 1
        if status_code == 429:
            metrics["http_429"] += 1

    _source_metric_update(source, update)


def _tracked_source_get(
    source: str,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    retry_attempt: bool = False,
) -> requests.Response:
    """Record safe request metadata; never persist URLs, query strings or payloads."""
    started_monotonic = time.monotonic()
    try:
        response = requests.get(
            endpoint, params=params, headers=headers, timeout=timeout
        )
    except Exception:
        _record_source_request(
            source,
            status_code=None,
            duration_ms=(time.monotonic() - started_monotonic) * 1000,
            exception=True,
            retry_attempt=retry_attempt,
        )
        raise
    _record_source_request(
        source,
        status_code=getattr(response, "status_code", None),
        duration_ms=(time.monotonic() - started_monotonic) * 1000,
        retry_attempt=retry_attempt,
    )
    return response


def _record_source_page(source: str, succeeded: bool) -> None:
    def update(metrics: dict[str, Any]) -> None:
        metrics["pages_attempted"] += 1
        metrics["pages_succeeded" if succeeded else "pages_failed"] += 1
    _source_metric_update(source, update)


def _record_source_board(source: str, succeeded: bool) -> None:
    def update(metrics: dict[str, Any]) -> None:
        metrics["boards_attempted"] += 1
        metrics["boards_succeeded" if succeeded else "boards_failed"] += 1
    _source_metric_update(source, update)


def _finish_source_run_metrics(source: str) -> dict[str, Any]:
    with source_metrics_lock:
        metrics = active_source_metrics.pop(source, None)
        if metrics is None:
            return {**{field: 0 for field in SOURCE_METRIC_FIELDS}, "http_status_counts": {}}
        with metrics["_lock"]:
            return {
                **{field: metrics[field] for field in SOURCE_METRIC_FIELDS},
                "http_status_counts": dict(metrics["http_status_counts"]),
            }


def record_run(
    source: str,
    started_at: dt.datetime,
    finished: dt.datetime,
    jobs_seen: int,
    new_jobs: int,
    error: str | None = None,
    *,
    run_id: str | None = None,
    outcome: str | None = None,
    duration_seconds: float | None = None,
    error_type: str | None = None,
    http_status: int | None = None,
    retry_after_seconds: float | None = None,
    cooldown_seconds: int | None = None,
    rate_limit_detected_at: str | None = None,
    request_metrics: dict[str, Any] | None = None,
) -> None:
    run_id = run_id or uuid.uuid4().hex
    if outcome is None:
        outcome = "failed" if error else "success"
    if duration_seconds is None:
        duration_seconds = max(0.0, (finished - started_at).total_seconds())
    metrics = request_metrics or {}
    status_counts_json = json.dumps(
        metrics.get("http_status_counts", {}), sort_keys=True
    )
    fields = list(SOURCE_METRIC_FIELDS)
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    metric_values = [metrics.get(field) for field in fields]
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT INTO source_runs(
                source, started_at, finished_at, jobs_seen, new_jobs, error,
                run_id, outcome, duration_seconds, error_type, http_status,
                retry_after_seconds, cooldown_seconds, rate_limit_detected_at,
                {columns}, http_status_counts_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,{placeholders},?)
            """,
            (
                source, iso(started_at), iso(finished), jobs_seen, new_jobs, error,
                run_id, outcome, max(0.0, float(duration_seconds)), error_type,
                http_status, retry_after_seconds, cooldown_seconds,
                rate_limit_detected_at, *metric_values, status_counts_json,
            ),
        )
        conn.commit()


def restore_linkedin_rate_limit_state() -> None:
    """Restore the LinkedIn 429 breaker from recent persisted source runs.

    The cooldown clock is monotonic within one process, so persist the UTC
    detection timestamp and reconstruct the remaining delay on startup.
    """
    global linkedin_last_rate_limit_monotonic
    global linkedin_rate_limit_streak, linkedin_rate_limited_until_monotonic

    cutoff = iso(now() - dt.timedelta(
        seconds=LINKEDIN_RATE_LIMIT_STREAK_RESET_SECONDS
    ))
    try:
        with db_lock, sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT started_at, finished_at, rate_limit_detected_at,
                       cooldown_seconds, retry_after_seconds
                FROM source_runs
                WHERE source='linkedin'
                  AND http_status=429
                  AND COALESCE(rate_limit_detected_at, finished_at) >= ?
                ORDER BY COALESCE(rate_limit_detected_at, finished_at) DESC, id DESC
                """,
                (cutoff,),
            ).fetchall()
    except sqlite3.Error:
        log.exception("linkedin: unable to restore persisted rate-limit state")
        return

    runtime = source_state.setdefault("linkedin", {})
    if not rows:
        linkedin_last_rate_limit_monotonic = 0.0
        linkedin_rate_limit_streak = 0
        linkedin_rate_limited_until_monotonic = 0.0
        for key in (
            "rate_limited_until",
            "rate_limit_cooldown_seconds",
            "rate_limit_retry_after_seconds",
            "rate_limit_detected_at",
        ):
            runtime.pop(key, None)
        return

    latest_detected_at = rows[0][2] or rows[0][1]
    detected_at = parse_relative(latest_detected_at)
    if detected_at is None:
        log.warning("linkedin: skipped invalid persisted rate-limit timestamp")
        return

    elapsed_seconds = max(0.0, (now() - detected_at).total_seconds())
    cooldown_seconds = max(0, int(rows[0][3] or 0))
    remaining_seconds = max(0.0, cooldown_seconds - elapsed_seconds)
    monotonic_now = time.monotonic()

    linkedin_rate_limit_streak = len(rows)
    linkedin_last_rate_limit_monotonic = monotonic_now - elapsed_seconds
    linkedin_rate_limited_until_monotonic = monotonic_now + remaining_seconds

    runtime["rate_limit_detected_at"] = iso(detected_at)
    runtime["rate_limit_cooldown_seconds"] = cooldown_seconds
    runtime["rate_limit_retry_after_seconds"] = rows[0][4]
    if remaining_seconds > 0:
        runtime["rate_limited_until"] = iso(
            now() + dt.timedelta(seconds=remaining_seconds)
        )
        log.warning(
            "linkedin: restored persisted 429 cooldown; streak=%s remaining=%ss",
            linkedin_rate_limit_streak,
            int(remaining_seconds),
        )
    else:
        runtime.pop("rate_limited_until", None)
        log.info(
            "linkedin: restored 429 streak from recent history; streak=%s",
            linkedin_rate_limit_streak,
        )


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



def extract_explicit_work_location(description: str) -> str | None:
    """Return a clearly labelled work-location value from a job description.

    Some aggregators combine several source locations even when the employer
    states one actual work location in the JD. Only trust the explicit
    "Work Location:" label; do not infer a city from an address or interview
    venue.
    """
    raw = re.sub(r"\s+", " ", str(description or "")).strip()
    if not raw:
        return None
    match = re.search(
        r"\bwork\s+location\s*[:\-]\s*(?P<location>.+?)"
        r"(?=\s+\b(?:interview\s+venue|work\s+mode|employment\s+type|"
        r"job\s+type|qualification|experience|key\s+responsibilities|"
        r"responsibilities|job\s+summary|job\s+description)\b\s*:|[;|\n]|\.(?=\s|$)|$)",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    value = re.sub(r"\s+", " ", match.group("location")).strip(" ,;|.-")
    if not value or len(value) > 80 or len(value.split()) > 8:
        return None
    return value


def job_location_for_matching(job: dict[str, Any]) -> str:
    """Prefer an explicit work location over broad aggregator metadata."""
    return (
        extract_explicit_work_location(str(job.get("description") or ""))
        or str(job.get("location") or "")
    )



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
        r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\s+of\s+"
        r"(?:overall|total|professional|work)\b[^.!?]{0,160}\bexperience\b",
        r"(?:overall|total|professional|work)\b[^.!?]{0,120}\bexperience\b"
        r"[^.!?]{0,80}?(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b",
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


def _experience_is_reliably_known_for_shadow(job: dict[str, Any]) -> bool:
    """Return true only when deterministic experience evidence is strong enough to skip Gemini review.

    Generic regex matches are deliberately reviewable: they can select tool-specific
    or incidental years from a longer description and should not suppress a bounded
    Gemini check merely because a number was found.
    """
    description = str(job.get("description") or "")
    source = str(job.get("source") or "").casefold()
    labeled = extract_linkedin_labeled_experience(description)
    if source == "linkedin" and labeled != (None, None):
        return True

    parsed = extract_jd_experience(description)
    if parsed == (None, None):
        return False

    # Trust only explicit overall/total/professional/work context. Phrases like
    # "3+ years of Python experience" or "5+ years of software development
    # experience" remain reviewable because they may be skill/domain-specific.
    return bool(re.search(
        r"\b(?:overall|total)\b[^.!?]{0,120}\bexperience\b"
        r"|\b(?:professional|work)\s+experience\b",
        description,
        re.I,
    ))


def extract_linkedin_labeled_experience(text: str) -> tuple[float | None, float | None]:
    """Parse LinkedIn's structured metadata label, e.g. 'Experience: 4.00-6.00 Years'.

    This is intentionally stricter than the generic JD parser so incidental
    mentions of years in a search-card snippet cannot masquerade as the job's
    experience requirement.
    """
    raw = _clean_experience_text(text)
    if not raw:
        return None, None

    range_match = re.search(
        r"\bexperience\s*:\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*"
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        raw,
        re.I,
    )
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))

    plus_match = re.search(
        r"\bexperience\s*:\s*(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b",
        raw,
        re.I,
    )
    if plus_match:
        return float(plus_match.group(1)), None

    single_match = re.search(
        r"\bexperience\s*:\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        raw,
        re.I,
    )
    if single_match:
        years = float(single_match.group(1))
        return years, years
    return None, None


def _experience_provenance_details(job: dict[str, Any]) -> dict[str, Any]:
    """Resolve job-level experience bounds and where the evidence came from.

    LinkedIn's explicit Experience label is treated as employer-stated source
    metadata. Explicit requirements parsed from the job description are
    description-derived. Generic year mentions remain marked inferred rather
    than being presented as an employer requirement.
    """
    description = str(job.get("description") or "")
    source = str(job.get("source") or "").casefold()

    if job.get("jd_experience_source") == "gemini_verified":
        low = job.get("jd_experience_min_years")
        high = job.get("jd_experience_max_years")
        if low is not None or high is not None:
            return {"min_years": low, "max_years": high, "provenance": "description", "confidence": "high"}

    if source == "linkedin":
        low, high = extract_linkedin_labeled_experience(description)
        if low is not None or high is not None:
            return {"min_years": low, "max_years": high, "provenance": "employer_stated", "confidence": "high"}

    low, high = extract_jd_experience(description)
    explicit_context = bool(re.search(
        r"\b(?:overall|total|professional)\b[^.!?]{0,120}\bexperience\b"
        r"|\bwork\s+experience\b"
        r"|\bexperience\b[^.!?]{0,80}\b(?:required|minimum|at\s+least)\b"
        r"|\b(?:minimum|at\s+least|required|requires?)\b[^.!?]{0,100}\bexperience\b"
        r"|\b\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?)\s+of\s+experience\b",
        description,
        re.I,
    ))
    if (low is not None or high is not None) and explicit_context:
        return {"min_years": low, "max_years": high, "provenance": "description", "confidence": "medium"}

    low, high = extract_experience(f"{job.get('title', '')} {description}")
    if low is not None or high is not None:
        return {"min_years": low, "max_years": high, "provenance": "inferred", "confidence": "low"}

    return {"min_years": None, "max_years": None, "provenance": "unknown", "confidence": "unknown"}


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
        page_text = soup.get_text(" ", strip=True)
        labeled_experience = extract_linkedin_labeled_experience(page_text)
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
            selected = max(pool, key=len)[:20000]
            # LinkedIn sometimes renders its Experience field outside the
            # description element. Preserve that structured field explicitly
            # and place it first so it takes precedence over generic JD mentions.
            if labeled_experience != (None, None):
                low, high = labeled_experience
                label = (
                    f"Experience: {low:g}-{high:g} years"
                    if high is not None and high != low
                    else (f"Experience: {low:g}+ years" if high is None else f"Experience: {low:g} years")
                )
                if extract_linkedin_labeled_experience(selected) != labeled_experience:
                    selected = f"{label}. {selected}"
            return selected[:20000]

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

    # The labeled LinkedIn metadata is more reliable than incidental years
    # mentioned elsewhere in the JD (for example, '2 years of Python experience').
    detail_experience = extract_linkedin_labeled_experience(detail)
    if detail_experience == (None, None):
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

    if not location_allowed(job_location_for_matching(job), config):
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

    # A role keyword mentioned in a description is not sufficient on its
    # own: non-engineering titles (for example, "Conversation Quality Analyst")
    # can mention engineers they collaborate with. Use description fallback
    # only when the title itself identifies a developer/engineer role family.
    if not role_hits and generic_title:
        description_role_hits = phrase_hits(config.get("target_roles", []), description)
        if description_role_hits:
            role_hits = description_role_hits
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

    # Unknown experience is neutral for profile matching. Explicit incompatible
    # experience is already rejected by match_details(); do not add a hidden
    # second gate after the configured match threshold has passed.
    return {"alertable": True, "reasons": ["passes match threshold and notification policy"]}




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



def _source_run_error_metadata(exc: Exception) -> dict[str, Any]:
    """Return safe, structured error details without persisting exception URLs or secrets."""
    response = getattr(exc, "response", None)
    raw_status = getattr(response, "status_code", None)
    try:
        http_status = int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError):
        http_status = None
    retry_after_seconds = _retry_after_seconds(response) if response is not None else None
    rate_limited = http_status == 429 or isinstance(exc, LinkedInRateLimitCooldown)
    if http_status is not None:
        safe_error = f"HTTP {http_status}"
    else:
        safe_error = type(exc).__name__
    return {
        "error": safe_error,
        "error_type": type(exc).__name__,
        "http_status": http_status,
        "retry_after_seconds": retry_after_seconds,
        "rate_limited": rate_limited,
    }


def _activate_linkedin_rate_limit(response: requests.Response) -> float:
    """Back off globally when any LinkedIn endpoint returns HTTP 429."""
    global linkedin_rate_limited_until_monotonic
    global linkedin_last_rate_limit_monotonic
    global linkedin_rate_limit_streak, linkedin_rate_limit_generation

    remaining = _linkedin_cooldown_remaining()
    if remaining > 0:
        return remaining

    monotonic_now = time.monotonic()
    # Keep escalation across the long cooldowns used for repeated 429s.
    # A full 24 hours without another rate-limit response is required before
    # returning to the five-minute initial backoff.
    if (
        linkedin_last_rate_limit_monotonic
        and monotonic_now - linkedin_last_rate_limit_monotonic
        >= LINKEDIN_RATE_LIMIT_STREAK_RESET_SECONDS
    ):
        linkedin_rate_limit_streak = 0
    linkedin_rate_limit_streak += 1
    linkedin_last_rate_limit_monotonic = monotonic_now
    multiplier = 2 ** min(linkedin_rate_limit_streak - 1, 6)
    fallback = min(
        LINKEDIN_RATE_LIMIT_MAX_COOLDOWN_SECONDS,
        LINKEDIN_RATE_LIMIT_BASE_COOLDOWN_SECONDS * multiplier,
    )
    retry_after = _retry_after_seconds(response)
    cooldown = max(fallback, retry_after or 0.0)
    linkedin_rate_limited_until_monotonic = monotonic_now + cooldown
    linkedin_rate_limit_generation += 1

    until_utc = now() + dt.timedelta(seconds=cooldown)
    source_runtime = source_state.setdefault("linkedin", {})
    source_runtime["rate_limited_until"] = iso(until_utc)
    source_runtime["rate_limit_cooldown_seconds"] = int(cooldown)
    source_runtime["rate_limit_retry_after_seconds"] = retry_after
    source_runtime["rate_limit_detected_at"] = iso(until_utc - dt.timedelta(seconds=cooldown))
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
    retry_attempt: bool = False,
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
        response = _tracked_source_get(
            "linkedin",
            endpoint,
            params=params,
            headers=headers or UA,
            timeout=timeout,
            retry_attempt=retry_attempt,
        )
        if response.status_code == 429:
            _activate_linkedin_rate_limit(response)
            response.raise_for_status()
        return response


def _linkedin_request(endpoint: str, params: dict[str, Any]) -> requests.Response:
    for attempt in range(3):
        response = _linkedin_http_get(
            endpoint,
            params=params,
            headers=UA,
            timeout=25,
            retry_attempt=attempt > 0,
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
    jobs: list[dict[str, Any]] = []
    last_deep = linkedin_last_deep_scan_at
    last_deep_at = parse_relative(last_deep) if last_deep else None
    do_deep = (
        last_deep_at is None
        or (now() - last_deep_at).total_seconds() >= LINKEDIN_DEEP_SCAN_SECONDS
    )

    # Spread first-page searches over consecutive cycles to reduce HTTP 429s.
    # If a target is rate-limited, keep the cursor on that target for the first
    # retry after cooldown instead of skipping the unattempted targets in its batch.
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
    search_requests_attempted = 0

    def run_batch(
        targets: list[tuple[str, str, int, bool]],
        *,
        retry_rate_limited_fast_target: bool = False,
    ) -> None:
        global linkedin_fast_target_cursor
        nonlocal failed_pages, rate_limited, search_requests_attempted
        # Run in paced order. Do not queue more search requests once a 429 occurs.
        for attempted, (query, location, start, fast) in enumerate(targets, start=1):
            search_requests_attempted += 1
            try:
                page_jobs = _linkedin_search_page(query, location, start, fast)
                _record_source_page("linkedin", True)
                jobs.extend(page_jobs)
            except Exception as exc:
                _record_source_page("linkedin", False)
                failed_pages += 1
                response = getattr(exc, "response", None)
                status_code = getattr(response, "status_code", None)
                if status_code == 429:
                    if _linkedin_cooldown_remaining() <= 0:
                        _activate_linkedin_rate_limit(response)
                    rate_limited = True
                    if retry_rate_limited_fast_target and all_fast_targets:
                        rewind = len(targets) - attempted + 1
                        linkedin_fast_target_cursor = (
                            linkedin_fast_target_cursor - rewind
                        ) % len(all_fast_targets)
                    log.warning("linkedin search batch stopped after HTTP 429")
                    break
                if isinstance(exc, LinkedInRateLimitCooldown):
                    rate_limited = True
                    if retry_rate_limited_fast_target and all_fast_targets:
                        rewind = len(targets) - attempted + 1
                        linkedin_fast_target_cursor = (
                            linkedin_fast_target_cursor - rewind
                        ) % len(all_fast_targets)
                    log.info("linkedin search batch stopped; rate-limit cooldown is active")
                    break
                log.warning("linkedin page request failed: %r", exc)

    run_batch(fast_targets, retry_rate_limited_fast_target=True)
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
        "linkedin discovery scan: queries=%s locations=%s requests_attempted=%s "
        "deep=%s unique_jobs=%s failed_requests=%s elapsed=%.1fs",
        len(scan_queries),
        len(scan_locations),
        search_requests_attempted,
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
        labeled_experience = extract_linkedin_labeled_experience(combined)
        if labeled_experience != (None, None):
            job["jd_experience_min_years"] = labeled_experience[0]
            job["jd_experience_max_years"] = labeled_experience[1]
            job.pop("needs_jd_enrichment", None)
            continue
        # Do not skip full JD inspection just because a search snippet contains
        # an incidental year count; the actual LinkedIn JD may state a different
        # experience band in its structured metadata.
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

    return jobs

# The public relay repository contains only the Naukri feed and its small
# scheduled collector workflow. The main application repository stays private.
NAUKRI_RELAY_URL = (
    "https://raw.githubusercontent.com/AvinashBhalla/"
    "job-beeper-naukri-relay/naukri-relay/dashboard/data/naukri_relay.json"
)
NAUKRI_RELAY_MAX_AGE_SECONDS = 15 * 60
NAUKRI_RELAY_FUTURE_TOLERANCE_SECONDS = 5 * 60


def _record_naukri_feed_state(
    feed_updated_at: dt.datetime,
    observed_at: dt.datetime,
    feed_age_seconds: float,
    jobs_count: int,
    payload_sha256: str,
) -> bool:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        previous = conn.execute(
            "SELECT payload_sha256 FROM source_feed_state WHERE source='naukri'"
        ).fetchone()
        unchanged = bool(previous and previous[0] == payload_sha256)
        conn.execute(
            """
            INSERT INTO source_feed_state(
                source, feed_updated_at, last_observed_at, feed_age_seconds,
                jobs_count, payload_sha256, snapshot_unchanged
            ) VALUES('naukri', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                feed_updated_at=excluded.feed_updated_at,
                last_observed_at=excluded.last_observed_at,
                feed_age_seconds=excluded.feed_age_seconds,
                jobs_count=excluded.jobs_count,
                payload_sha256=excluded.payload_sha256,
                snapshot_unchanged=excluded.snapshot_unchanged
            """,
            (
                iso(feed_updated_at),
                iso(observed_at),
                max(0.0, float(feed_age_seconds)),
                int(jobs_count),
                payload_sha256,
                int(unchanged),
            ),
        )
        conn.commit()
    return unchanged




def naukri_collect() -> list[dict[str, Any]]:
    # The public relay exposes a full snapshot with one relay-run timestamp.
    # Reject stale or empty snapshots before changing local job observations.
    relay_headers = {**UA, "Accept": "application/json"}
    response: requests.Response | None = None
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(4):
        try:
            candidate = _tracked_source_get(
                "naukri",
                NAUKRI_RELAY_URL,
                params={"t": int(time.time())},
                headers=relay_headers,
                timeout=20,
                retry_attempt=attempt > 0,
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
            candidate.raise_for_status()
            response = candidate
            break
        except requests.HTTPError:
            _record_source_page("naukri", False)
            raise
        except requests.RequestException:
            if attempt == 3:
                _record_source_page("naukri", False)
                raise
            wait = min(8, 2 ** attempt)
            log.warning("naukri relay network fetch failed; retrying in %ss", wait)
            time.sleep(wait)

    if response is None:
        _record_source_page("naukri", False)
        raise RuntimeError("Naukri relay fetch returned no response")

    try:
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Naukri relay payload must be a JSON object")

        relay_jobs = payload.get("jobs")
        if not isinstance(relay_jobs, list) or not relay_jobs:
            raise RuntimeError("Naukri relay snapshot is empty or has no jobs list")

        reported_count = payload.get("count")
        if reported_count is not None:
            try:
                reported_count = int(reported_count)
            except (TypeError, ValueError):
                raise RuntimeError("Naukri relay count is invalid")
            if reported_count != len(relay_jobs):
                raise RuntimeError("Naukri relay count does not match the snapshot")

        relay_collected_at = payload.get("updated_at")
        collected_at = parse_relative(relay_collected_at) if relay_collected_at else None
        if collected_at is None:
            raise RuntimeError("Naukri relay updated_at timestamp is missing or invalid")

        observed_at = now()
        feed_age_seconds = (observed_at - collected_at).total_seconds()
        if feed_age_seconds < -NAUKRI_RELAY_FUTURE_TOLERANCE_SECONDS:
            raise RuntimeError("Naukri relay timestamp is too far in the future")
        if feed_age_seconds > NAUKRI_RELAY_MAX_AGE_SECONDS:
            age_minutes = int(feed_age_seconds // 60)
            raise RuntimeError(
                f"Naukri relay snapshot is stale ({age_minutes} minutes old; "
                f"limit {NAUKRI_RELAY_MAX_AGE_SECONDS // 60} minutes)"
            )

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

            experience = item.get("experience")
            if not isinstance(experience, dict):
                experience = {}
            skills = item.get("skills_detected")
            if not isinstance(skills, list):
                skills = []
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
                description_format=str(item.get("description_format") or "plain"),
                source_details=(
                    item.get("source_details")
                    if isinstance(item.get("source_details"), dict)
                    else {}
                ),
            )
            # Relay observation timestamps are distinct from the employer's
            # posted date and are optional for older snapshots.
            first_observed_at = parse_relative(item.get("relay_first_observed_at"))
            last_observed_at = parse_relative(item.get("relay_last_observed_at"))
            future_limit = observed_at + dt.timedelta(
                seconds=NAUKRI_RELAY_FUTURE_TOLERANCE_SECONDS
            )
            if first_observed_at and first_observed_at > future_limit:
                first_observed_at = None
            if last_observed_at and last_observed_at > future_limit:
                last_observed_at = None
            if (
                first_observed_at
                and last_observed_at
                and first_observed_at > last_observed_at
            ):
                first_observed_at = None
                last_observed_at = None

            # Older published feed items have no per-job fields. In that case,
            # the previous snapshot-level timestamp is the best available
            # observation proxy, with its coarser precision documented.
            job["discovered_at"] = (
                iso(first_observed_at)
                or iso(collected_at)
                or job["discovered_at"]
            )
            job["last_seen_at"] = (
                iso(last_observed_at)
                or iso(collected_at)
                or job["discovered_at"]
            )
            job["discovery_latency_seconds"] = None
            jobs.append(job)

        if not jobs:
            raise RuntimeError("Naukri relay snapshot contains no valid job records")

        # The relay timestamp changes on every successful build; hash only
        # job content so a fresh build with identical listings is detectable.
        fingerprint_jobs = [
            {
                key: value
                for key, value in item.items()
                if key not in {"relay_last_observed_at"}
            }
            for item in relay_jobs
            if isinstance(item, dict)
        ]
        fingerprint_jobs.sort(
            key=lambda item: (str(item.get("id") or ""), str(item.get("url") or ""))
        )
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_jobs, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        unchanged = _record_naukri_feed_state(
            collected_at,
            observed_at,
            feed_age_seconds,
            len(jobs),
            fingerprint,
        )
        _record_source_page("naukri", True)
        log.info(
            "naukri relay snapshot accepted: jobs=%s age_seconds=%s unchanged=%s",
            len(jobs),
            round(max(0.0, feed_age_seconds)),
            unchanged,
        )
        return jobs
    except Exception:
        _record_source_page("naukri", False)
        raise

def instahyre_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = "https://www.instahyre.com/api/v1/job_search/"
    try:
        response = _tracked_source_get(
            "instahyre",
            endpoint,
            params={
                "jobLocations": next(
                    (
                        str(x).split(",")[0]
                        for x in config.get("locations", [])
                        if "remote" not in str(x).lower()
                    ),
                    "Bangalore",
                ),
                "limit": 35,
            },
            headers={**UA, "Referer": "https://www.instahyre.com/"},
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        _record_source_page("instahyre", False)
        raise
    _record_source_page("instahyre", True)
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
            _record_source_board("greenhouse", False)
            failures.append(f"{token or '<missing-token>'}: invalid board configuration")
            continue

        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            response = _tracked_source_get(
                "greenhouse",
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
            _record_source_board("greenhouse", True)
        except Exception as exc:
            _record_source_board("greenhouse", False)
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


def _parse_ashby_published_at(value: Any) -> tuple[dt.datetime | None, str]:
    """Parse Ashby's publishedAt field; missing or malformed values stay unknown."""
    if not isinstance(value, str) or not value.strip():
        return None, "unknown"
    raw = value.strip()
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        parsed = parsed.astimezone(UTC)
    except (OverflowError, OSError, TypeError, ValueError):
        return None, "unknown"
    precision = "minute" if re.search(r"\d{2}:\d{2}", raw) else "date"
    return parsed, precision


def ashby_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect an explicit allowlist of public Ashby boards with bounded requests."""
    boards = config.get("ashby_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Ashby is enabled but no public ashby_boards are configured")

    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []

    for board in boards:
        name = str(board.get("board") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        if not name or not company or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name):
            _record_source_board("ashby", False)
            failures.append(f"{name or '<missing-board>'}: invalid board configuration")
            continue

        endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{name}"
        try:
            response = _tracked_source_get(
                "ashby", endpoint, headers={**UA, "Accept": "application/json"}, timeout=15
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
                raise ValueError("Ashby response did not contain a jobs list")
            successful_boards += 1
            _record_source_board("ashby", True)
        except Exception as exc:
            _record_source_board("ashby", False)
            failures.append(f"{name}: {type(exc).__name__}")
            log.warning("ashby: board=%s failed error_type=%s", name, type(exc).__name__)
            continue

        for item in payload["jobs"]:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("id")
            title = item.get("title")
            url = item.get("jobUrl") or item.get("applyUrl")
            if raw_id in (None, "") or not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(url, str) or not url.strip():
                continue
            direct_url = url.strip()
            if not re.match(r"^https://", direct_url, re.I):
                continue

            source_id = f"ashby-{name}-{raw_id}"
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            location_value = item.get("location")
            if isinstance(location_value, dict):
                location = str(location_value.get("name") or "").strip()
            elif isinstance(location_value, str):
                location = location_value.strip()
            else:
                location = ""
            if not location:
                location = str(item.get("locationName") or "").strip()

            html_description = item.get("descriptionHtml")
            plain_description = item.get("descriptionPlain")
            if isinstance(html_description, str) and html_description.strip():
                description = BeautifulSoup(html_lib.unescape(html_description), "html.parser").get_text(" ", strip=True)
            elif isinstance(plain_description, str):
                description = re.sub(r"\s+", " ", plain_description).strip()
            else:
                description = ""

            published_at, posted_precision = _parse_ashby_published_at(item.get("publishedAt"))
            try:
                jobs.append(normalize_job(
                    "ashby", source_id, company, title.strip(), location,
                    direct_url, published_at, posted_precision, description,
                ))
            except (TypeError, ValueError) as exc:
                log.warning("ashby: board=%s skipped malformed job error_type=%s", name, type(exc).__name__)

    if successful_boards == 0:
        details = "; ".join(failures) or "no valid boards configured"
        raise RuntimeError(f"All configured Ashby boards failed: {details}")
    if failures:
        log.warning("ashby: partial board failures=%s successful_boards=%s", len(failures), successful_boards)
    log.info(
        "ashby: boards=%s successful=%s failed=%s jobs=%s timestamped=%s",
        len(boards), successful_boards, len(failures), len(jobs),
        sum(1 for job in jobs if job.get("source_posted_at")),
    )
    return jobs


COLLECTORS = {
    "linkedin": linkedin_collect,
    "naukri": lambda config: naukri_collect(),
    "instahyre": instahyre_collect,
    "greenhouse": greenhouse_collect,
    "ashby": ashby_collect,
}
SOURCE_NAMES = tuple(COLLECTORS)


def run_source(source: str, config: dict[str, Any]) -> None:
    if source_state.get(source, {}).get("running"):
        log.warning("%s: previous run still active; skipping this cycle", source)
        return

    started_at = now()
    started_monotonic = time.monotonic()
    run_id = uuid.uuid4().hex
    rate_limit_generation_at_start = (
        linkedin_rate_limit_generation if source == "linkedin" else None
    )
    runtime_at_start = source_state.setdefault(source, {})
    runtime_at_start["running"] = True
    runtime_at_start["current_run_id"] = run_id
    jobs: list[dict[str, Any]] = []
    new_jobs = 0
    request_metrics: dict[str, Any] | None = None
    _begin_source_run_metrics(source)
    try:
        try:
            jobs = COLLECTORS[source](config)
        except Exception:
            request_metrics = _finish_source_run_metrics(source)
            raise
        else:
            request_metrics = _finish_source_run_metrics(source)

        # Gemini is deliberately shadow-only: store a separately validated
        # extraction for evaluation, but never modify matcher inputs or alerts.
        shadow_candidates = [
            job for job in jobs
            if title_allowed(job.get("title", ""), config)
            and location_allowed(job_location_for_matching(job), config)
            and (
                match_details(job, config)["match"]
                or phrase_hits(config.get("target_roles", []), job.get("title", ""))
            )
        ]

        try:
            shadow_extract_jobs(
                shadow_candidates,
                DB_PATH,
                experience_known=_experience_is_reliably_known_for_shadow,
                configured_skills=config.get("skills", []),
            )
        except Exception as exc:
            # AI enrichment must fail open; source ingestion continues unchanged.
            log.warning(
                "gemini shadow pass skipped source=%s error_type=%s",
                source,
                type(exc).__name__,
            )
        new_jobs = upsert_jobs(
            jobs,
            config,
            source_run_started_at=started_at,
        )
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
        duration_seconds = max(0.0, time.monotonic() - started_monotonic)
        cooldown_remaining = (
            _linkedin_cooldown_remaining() if source == "linkedin" else 0.0
        )
        rate_limit_seen = (
            source == "linkedin"
            and linkedin_rate_limit_generation != rate_limit_generation_at_start
        )
        metrics = request_metrics or {}
        partial_page_failure = (
            metrics.get("pages_failed", 0) > 0
            and metrics.get("pages_succeeded", 0) > 0
        )
        partial_board_failure = (
            metrics.get("boards_failed", 0) > 0
            and metrics.get("boards_succeeded", 0) > 0
        )
        total_page_failure = (
            metrics.get("pages_failed", 0) > 0
            and metrics.get("pages_succeeded", 0) == 0
        )
        total_board_failure = (
            metrics.get("boards_failed", 0) > 0
            and metrics.get("boards_succeeded", 0) == 0
        )
        partial_failure = partial_page_failure or partial_board_failure
        total_failure = total_page_failure or total_board_failure
        outcome = (
            "partial_rate_limited" if jobs and rate_limit_seen
            else "rate_limited" if rate_limit_seen
            else "partial_failed" if partial_failure
            else "failed" if total_failure
            else "success"
        )
        if rate_limit_seen:
            error = "HTTP 429"
            error_type = "HTTPError"
        elif partial_failure:
            error = "Some source pages or boards failed"
            error_type = "PartialSourceError"
        elif total_failure:
            error = "Source pages or boards failed"
            error_type = "SourceError"
        else:
            error = None
            error_type = None
        current_runtime = source_state.get(source, {})
        retry_after_seconds = (
            current_runtime.get("rate_limit_retry_after_seconds")
            if rate_limit_seen else None
        )
        http_status = 429 if rate_limit_seen else None
        cooldown_seconds = (
            int(
                current_runtime.get("rate_limit_cooldown_seconds")
                or max(0.0, cooldown_remaining)
            )
            if rate_limit_seen else None
        )
        record_run(
            source, started_at, finished, len(jobs), new_jobs, error,
            run_id=run_id,
            outcome=outcome,
            duration_seconds=duration_seconds,
            error_type=error_type,
            http_status=http_status,
            retry_after_seconds=retry_after_seconds,
            cooldown_seconds=cooldown_seconds,
            rate_limit_detected_at=(
                current_runtime.get("rate_limit_detected_at")
                if rate_limit_seen else None
            ),
            request_metrics=request_metrics,
        )
        runtime = dict(source_state.get(source, {}))
        runtime.update({
            "running": False,
            "current_run_id": None,
            "run_id": run_id,
            "last_run": iso(finished),
            "last_run_outcome": outcome,
            "last_run_duration_seconds": round(duration_seconds, 3),
            "jobs_seen": len(jobs),
            "new_jobs": new_jobs,
            "error": error,
            "http_status": http_status,
            "retry_after_seconds": retry_after_seconds,
            "cooldown_seconds": cooldown_seconds,
            "request_metrics": request_metrics,
        })
        if outcome == "success":
            runtime["last_success"] = iso(finished)
        if cooldown_remaining > 0:
            runtime["rate_limited_until"] = iso(
                now() + dt.timedelta(seconds=cooldown_remaining)
            )
            runtime["rate_limit_cooldown_seconds"] = int(
                runtime.get("rate_limit_cooldown_seconds")
                or cooldown_seconds
                or cooldown_remaining
            )
        elif not rate_limit_seen:
            runtime.pop("rate_limited_until", None)
            runtime.pop("rate_limit_cooldown_seconds", None)
            runtime.pop("rate_limit_retry_after_seconds", None)
            runtime.pop("rate_limit_detected_at", None)
        source_state[source] = runtime
        log.info(
            "%s: seen=%s new=%s outcome=%s run_id=%s",
            source, len(jobs), new_jobs, outcome, run_id,
        )
    except Exception as exc:
        if request_metrics is None:
            request_metrics = _finish_source_run_metrics(source)
        finished = now()
        duration_seconds = max(0.0, time.monotonic() - started_monotonic)
        metadata = _source_run_error_metadata(exc)
        cooldown_remaining = (
            _linkedin_cooldown_remaining() if source == "linkedin" else 0.0
        )
        if source == "linkedin" and cooldown_remaining > 0:
            metadata["rate_limited"] = True
        if metadata["rate_limited"]:
            outcome = "rate_limited"
        else:
            outcome = "failed"
        retry_after_seconds = metadata["retry_after_seconds"]
        if retry_after_seconds is None and source == "linkedin":
            retry_after_seconds = source_state.get(source, {}).get(
                "rate_limit_retry_after_seconds"
            )
        cooldown_seconds = None
        if cooldown_remaining > 0:
            cooldown_seconds = int(
                source_state.get(source, {}).get("rate_limit_cooldown_seconds")
                or cooldown_remaining
            )
        record_run(
            source, started_at, finished, len(jobs), new_jobs, metadata["error"],
            run_id=run_id,
            outcome=outcome,
            duration_seconds=duration_seconds,
            error_type=metadata["error_type"],
            http_status=metadata["http_status"],
            retry_after_seconds=retry_after_seconds,
            cooldown_seconds=cooldown_seconds,
            rate_limit_detected_at=(
                source_state.get(source, {}).get("rate_limit_detected_at")
                if source == "linkedin" and metadata["rate_limited"] else None
            ),
            request_metrics=request_metrics,
        )
        runtime = dict(source_state.get(source, {}))
        runtime.update({
            "running": False,
            "current_run_id": None,
            "run_id": run_id,
            "last_run": iso(finished),
            "last_run_outcome": outcome,
            "last_run_duration_seconds": round(duration_seconds, 3),
            "last_success": runtime.get("last_success"),
            "jobs_seen": len(jobs),
            "new_jobs": new_jobs,
            "error": metadata["error"],
            "http_status": metadata["http_status"],
            "retry_after_seconds": retry_after_seconds,
            "cooldown_seconds": cooldown_seconds,
            "request_metrics": request_metrics,
        })
        if cooldown_remaining > 0:
            runtime["rate_limited_until"] = iso(
                now() + dt.timedelta(seconds=cooldown_remaining)
            )
            runtime["rate_limit_cooldown_seconds"] = cooldown_seconds
        source_state[source] = runtime
        log.error(
            "%s collector failed run_id=%s outcome=%s error_type=%s",
            source, run_id, outcome, metadata["error_type"],
        )


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
            log.exception("legacy Telegram worker failed")

        # Member delivery is independent of the legacy admin chat ID.
        try:
            user_delivered = await asyncio.to_thread(user_notifications.dispatch, DB_PATH, 20, MATCHER_RULES_VERSION)
            if user_delivered:
                log.info("telegram: per-user delivered=%s", user_delivered)
        except Exception:
            log.exception("per-user Telegram worker failed")

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
            if name == "linkedin":
                interval = max(180, interval)
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
    restore_linkedin_rate_limit_state()
    ensure_runtime_config()
    config = get_config()
    refresh_job_evaluations(config)
    refresh_notification_decisions(config)
    refresh_configured_user_evaluations()
    app.state.scheduler_task = asyncio.create_task(scheduler())
    app.state.notification_worker_task = asyncio.create_task(notification_worker())


@app.on_event("shutdown")
async def shutdown() -> None:
    stop_event.set()
    for task_name in ("scheduler_task", "notification_worker_task"):
        task = getattr(app.state, task_name, None)
        if task:
            await task


SESSION_COOKIE_NAME = "job_beeper_session"
CSRF_COOKIE_NAME = "job_beeper_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
GOOGLE_STATE_COOKIE_NAME = "job_beeper_google_state"


class AuthLoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)


def _auth_cookie_secure() -> bool:
    value = os.getenv("JOB_BEEPER_COOKIE_SECURE", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _expected_login_origin(request: Request):
    configured_origin = os.getenv("JOB_BEEPER_PUBLIC_ORIGIN", "").strip()
    expected = urlsplit(configured_origin or str(request.base_url))
    if (
        expected.scheme.lower() not in {"http", "https"}
        or not expected.netloc
        or expected.path not in {"", "/"}
        or expected.query
        or expected.fragment
    ):
        raise HTTPException(status_code=500, detail="Authentication public origin is misconfigured.")
    return expected


def _issue_user_session(request: Request, response: Response, user: dict[str, Any]) -> None:
    previous_session = request.cookies.get(SESSION_COOKIE_NAME, "")
    if previous_session:
        auth.revoke_session(DB_PATH, previous_session)
    session_token, csrf_token, _ = auth.create_session(DB_PATH, user["id"])
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET last_login_at=? WHERE id=?", (iso(now()), user["id"]))
    cookie_options = {
        "path": "/",
        "secure": _auth_cookie_secure(),
        "samesite": "lax",
        "max_age": auth.SESSION_TTL_SECONDS,
    }
    response.set_cookie(
        key=SESSION_COOKIE_NAME, value=session_token, httponly=True, **cookie_options
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME, value=csrf_token, httponly=False, **cookie_options
    )


def get_current_user(request: Request) -> dict[str, Any]:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    user = auth.get_session_user(DB_PATH, session_token or "")
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    request.state.current_user = user
    return user


def require_authenticated(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        session_token = request.cookies.get(SESSION_COOKIE_NAME, "")
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
        header_token = request.headers.get(CSRF_HEADER_NAME, "")
        if (
            not cookie_token
            or not header_token
            or not secrets.compare_digest(cookie_token, header_token)
            or not auth.validate_csrf(DB_PATH, session_token, header_token)
        ):
            raise HTTPException(status_code=403, detail="CSRF validation failed.")
    return user


def require_admin(
    user: dict[str, Any] = Depends(require_authenticated),
) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


@app.post("/api/auth/login")
def auth_login(payload: AuthLoginRequest, request: Request, response: Response):
    # Prevent login CSRF: browser form/fetch submissions carry Origin. Non-browser
    # clients may omit it, but a supplied origin must match this same-origin API.
    origin = request.headers.get("origin")
    if origin:
        supplied = urlsplit(origin)
        expected = _expected_login_origin(request)
        if (
            supplied.scheme.lower() != expected.scheme.lower()
            or supplied.netloc.lower() != expected.netloc.lower()
            or supplied.path not in {"", "/"}
            or supplied.query
            or supplied.fragment
        ):
            raise HTTPException(status_code=403, detail="Cross-origin login is not allowed.")

    client_ip = request.client.host if request.client else "unknown"
    email = payload.email.strip().lower()
    try:
        if auth.begin_login_attempt(DB_PATH, email, client_ip):
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    except ValueError:
        pass

    user = auth.verify_user(DB_PATH, email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    auth.record_login_attempt(DB_PATH, email, client_ip, success=True)

    # A successful login replaces any browser session cookie already presented.
    _issue_user_session(request, response, user)
    return {"user": user}


@app.get("/api/auth/google/status")
def google_auth_status():
    try:
        configured = google_oauth.load_config() is not None
    except ValueError:
        configured = False
    return {"enabled": configured}


@app.get("/api/auth/google/start")
def google_auth_start():
    try:
        config = google_oauth.load_config()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if config is None:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    authorization_url = google_oauth.create_authorization_url(DB_PATH, config)
    state = parse_qs(urlsplit(authorization_url).query).get("state", [""])[0]
    response = RedirectResponse(authorization_url, status_code=302)
    response.set_cookie(
        key=GOOGLE_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=_auth_cookie_secure(),
        samesite="lax",
        max_age=google_oauth.STATE_TTL_SECONDS,
        path="/api/auth/google",
    )
    return response


@app.get("/api/auth/google/callback")
def google_auth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
):
    failure_url = "/dashboard/?google_auth=failed"

    def finish_redirect(url: str):
        redirect = RedirectResponse(url, status_code=303)
        redirect.delete_cookie(
            key=GOOGLE_STATE_COOKIE_NAME,
            httponly=True,
            secure=_auth_cookie_secure(),
            samesite="lax",
            path="/api/auth/google",
        )
        return redirect

    # Validate and consume the one-time state before interpreting either a
    # successful authorization or Google's cancellation/error response.
    browser_state = request.cookies.get(GOOGLE_STATE_COOKIE_NAME, "")
    if not browser_state or not state or not secrets.compare_digest(browser_state, state):
        return finish_redirect(failure_url)
    state_data = google_oauth.consume_authorization_state(DB_PATH, state)
    if state_data is None:
        return finish_redirect(failure_url)
    if error:
        return finish_redirect("/dashboard/?google_auth=cancelled")

    try:
        config = google_oauth.load_config()
    except ValueError:
        return finish_redirect(failure_url)
    if config is None:
        return finish_redirect(failure_url)

    expected_nonce, code_verifier = state_data
    try:
        identity = google_oauth.exchange_code_for_identity(code, code_verifier, config)
        if not google_oauth.validate_nonce(identity["claims"], expected_nonce):
            raise ValueError("Google identity nonce validation failed.")
        user = auth.create_or_link_google_user(
            DB_PATH, identity["email"], identity["subject"]
        )
        user_preferences.ensure_user_preferences(DB_PATH, user["id"])
    except Exception as exc:
        log.warning("Google sign-in failed error_type=%s", type(exc).__name__)
        return finish_redirect(failure_url)

    response = finish_redirect("/dashboard/")
    _issue_user_session(request, response, user)
    return response


@app.get("/api/auth/me")
def auth_me(user: dict[str, Any] = Depends(get_current_user)):
    return {"user": user}


@app.post("/api/auth/logout")
def auth_logout(
    request: Request,
    response: Response,
    user: dict[str, Any] = Depends(get_current_user),
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME, "")
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
    header_token = request.headers.get(CSRF_HEADER_NAME, "")
    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
        or not auth.validate_csrf(DB_PATH, session_token, header_token)
    ):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")
    auth.revoke_session(DB_PATH, session_token)
    cookie_options = {
        "path": "/",
        "secure": _auth_cookie_secure(),
        "samesite": "lax",
    }
    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True, **cookie_options)
    response.delete_cookie(key=CSRF_COOKIE_NAME, httponly=False, **cookie_options)
    return {"status": "logged_out"}


@app.get("/health")
def health():
    # Public liveness endpoint: keep internal paths and operational diagnostics private.
    return {
        "status": "ok",
        "version": app.version,
        "uptime_seconds": int(time.monotonic() - started),
    }



@app.get("/api/preferences")
def read_user_preferences(user: dict[str, Any] = Depends(require_authenticated)):
    if user["role"] == "admin":
        user_preferences.migrate_first_admin_preferences(DB_PATH, get_config())
    preferences = user_preferences.get_user_preferences(DB_PATH, user["id"])
    if preferences["onboarding_complete"]:
        ensure_user_job_evaluations_initialized(user["id"], preferences)
    return {"preferences": preferences}


@app.post("/api/preferences/resume")
async def parse_user_resume(
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(require_authenticated),
):
    """Parse an optional resume into suggestions; never persist the uploaded file or preferences."""
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Resume-assisted preferences are for member accounts.")
    filename = file.filename or "resume"
    suffix = Path(filename).suffix.lower()
    allowed_types = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
    }
    if suffix not in allowed_types or (file.content_type and file.content_type.lower() not in allowed_types[suffix]):
        await file.close()
        raise HTTPException(status_code=422, detail="File extension and content type must match a PDF or DOCX resume.")
    try:
        # Read at most one byte beyond the hard limit, rather than trusting Content-Length.
        content = await file.read(resume_parser.MAX_RESUME_BYTES + 1)
        result = resume_parser.parse_resume(filename, content)
    except resume_parser.ResumeParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()
    # Deliberately return only bounded suggestions. No file, path, raw text, or DB write.
    return result


@app.get("/api/notifications/settings")
def read_user_notification_settings(user: dict[str, Any] = Depends(require_authenticated)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Member notification settings are not available to administrators.")
    settings = user_notifications.get_settings(DB_PATH, user["id"])
    connection = telegram_linking.get_connection(DB_PATH, user["id"])
    return {"settings": settings, "telegram_connected": bool(connection)}


@app.put("/api/notifications/settings")
def update_user_notification_settings(payload: dict[str, Any], user: dict[str, Any] = Depends(require_authenticated)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Member notification settings are not available to administrators.")
    if set(payload) != {"enabled"} or not isinstance(payload.get("enabled"), bool):
        raise HTTPException(status_code=422, detail="Provide only an enabled boolean.")
    if payload["enabled"] and not telegram_linking.get_connection(DB_PATH, user["id"]):
        raise HTTPException(status_code=409, detail="Connect a private Telegram chat before enabling notifications.")
    try:
        settings = user_notifications.set_enabled(DB_PATH, user["id"], payload["enabled"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"settings": settings}


@app.get("/api/telegram/status")
def telegram_connection_status(user: dict[str, Any] = Depends(require_authenticated)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Telegram account linking is for member accounts.")
    username = os.getenv("JOB_BEEPER_TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    configured = bool(
        username
        and re.fullmatch(r"[A-Za-z0-9_]{5,32}", username)
        and os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN")
        and re.fullmatch(r"[A-Za-z0-9_-]{1,256}", os.getenv("JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET", ""))
    )
    connection = telegram_linking.get_connection(DB_PATH, user["id"])
    return {"configured": configured, "bot_username": username if configured else None,
            "connection": connection or {"connected": False}}


@app.post("/api/telegram/link")
def create_telegram_link(user: dict[str, Any] = Depends(require_authenticated)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Telegram account linking is for member accounts.")
    username = os.getenv("JOB_BEEPER_TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    configured = bool(
        username
        and re.fullmatch(r"[A-Za-z0-9_]{5,32}", username)
        and os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN")
        and re.fullmatch(r"[A-Za-z0-9_-]{1,256}", os.getenv("JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET", ""))
    )
    if not configured:
        raise HTTPException(status_code=503, detail="Telegram linking is not configured yet.")
    token, expires_at = telegram_linking.create_link_token(DB_PATH, user["id"])
    return {"url": f"https://t.me/{username}?start={token}", "expires_in_seconds": telegram_linking.TOKEN_TTL_SECONDS,
            "expires_at": expires_at}


@app.delete("/api/telegram/link")
def disconnect_telegram_account(user: dict[str, Any] = Depends(require_authenticated)):
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Telegram account linking is for member accounts.")
    disconnected = telegram_linking.disconnect(DB_PATH, user["id"])
    return {"connected": False, "disconnected": disconnected}


@app.post("/api/telegram/webhook")
async def telegram_link_webhook(request: Request, background_tasks: BackgroundTasks):
    expected_secret = os.getenv("JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET", "")
    supplied_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not expected_secret or not supplied_secret or not secrets.compare_digest(expected_secret, supplied_secret):
        raise HTTPException(status_code=403, detail="Webhook authentication failed.")
    if not os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN"):
        raise HTTPException(status_code=503, detail="Telegram bot is not configured.")
    if request.headers.get("content-length", "").isdigit() and int(request.headers["content-length"]) > 65536:
        raise HTTPException(status_code=413, detail="Telegram update is too large.")
    try:
        raw_update = await request.body()
        if len(raw_update) > 65536:
            raise HTTPException(status_code=413, detail="Telegram update is too large.")
        update = json.loads(raw_update)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Telegram update.") from None
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Invalid Telegram update.")
    message = update.get("message")
    if not isinstance(message, dict):
        return {"ok": True}
    chat = message.get("chat")
    text = message.get("text")
    if not isinstance(chat, dict) or not isinstance(text, str):
        return {"ok": True}
    chat_id = str(chat.get("id", ""))
    chat_type = str(chat.get("type", ""))
    match = re.fullmatch(r"/start(?:@\w+)?\s+([A-Za-z0-9_-]{20,128})", text.strip())
    if match is None:
        return {"ok": True}
    try:
        linked_user_id = telegram_linking.consume_link_token(
            DB_PATH, match.group(1), chat_id, chat_type
        )
    except ValueError:
        log.warning("Telegram link attempt rejected: chat is already linked to another account")
        return {"ok": True}
    if linked_user_id is not None:
        background_tasks.add_task(
            _send_telegram_link_confirmation,
            os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN", ""), chat_id,
        )
    return {"ok": True}


def _send_telegram_link_confirmation(bot_token: str, chat_id: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": "Your Telegram account is now connected to Job Beeper. You can return to the dashboard."},
            timeout=10,
        ).raise_for_status()
    except requests.RequestException:
        log.warning("Could not send Telegram account-link confirmation")


@app.put("/api/preferences")
def update_user_preferences(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    user: dict[str, Any] = Depends(require_authenticated),
):
    if user["role"] == "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator candidate preferences are managed through /api/config.",
        )
    try:
        saved = user_preferences.save_user_preferences(DB_PATH, user["id"], payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(refresh_user_job_evaluations, user["id"], saved)
    return {"preferences": saved}


@app.get("/api/config", dependencies=[Depends(require_admin)])
def read_config():
    return {
        "config": get_config(),
        "runtime_path": str(RUNTIME_CONFIG_PATH),
        "config_update_protected": True,
    }


@app.put("/api/config", dependencies=[Depends(require_admin)])
def update_config(payload: dict[str, Any]):
    saved = save_config(payload)
    user_preferences.sync_first_admin_preferences(DB_PATH, saved)
    refresh_job_evaluations(saved)
    refresh_notification_decisions(saved)
    refresh_configured_user_evaluations()
    return {"config": saved, "runtime_path": str(RUNTIME_CONFIG_PATH)}


@app.get("/api/latency-summary", dependencies=[Depends(require_admin)])
def latency_summary(hours: int = 24):
    hours = max(1, min(hours, 168))
    cutoff = iso(now() - dt.timedelta(hours=hours))

    source_placeholders = ",".join("?" for _ in SOURCE_NAMES)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(f"""
            SELECT source, discovery_latency_seconds
            FROM jobs
            WHERE discovered_at >= ?
              AND discovery_latency_seconds IS NOT NULL
              AND discovery_latency_seconds >= 0
              AND source IN ({source_placeholders})
            ORDER BY source, discovery_latency_seconds ASC
        """, (cutoff, *SOURCE_NAMES)).fetchall()

    by_source: dict[str, list[int]] = {}
    for source, latency in rows:
        by_source.setdefault(source, []).append(int(latency))

    def percentile(values: list[int], p: float) -> int | None:
        if not values:
            return None
        index = min(len(values) - 1, max(0, round((len(values) - 1) * p)))
        return values[index]

    summary = {}
    for source in SOURCE_NAMES:
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


@app.get("/api/source-status/summary")
def source_status_summary(user: dict[str, Any] = Depends(require_authenticated)):
    """Expose operational availability without leaking collector diagnostics to members."""
    config = get_config()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT sr.source, sr.finished_at, sr.jobs_seen, sr.new_jobs
            FROM source_runs sr
            JOIN (
                SELECT source, MAX(finished_at) AS latest_finished_at
                FROM source_runs GROUP BY source
            ) latest
              ON latest.source = sr.source AND latest.latest_finished_at = sr.finished_at
            ORDER BY sr.source
        """).fetchall()
    history = {
        row[0]: {"last_run": row[1], "jobs_seen": row[2] or 0, "new_jobs": row[3] or 0}
        for row in rows
    }
    sources = []
    for source in SOURCE_NAMES:
        item = history.get(source, {})
        runtime = source_state.get(source, {})
        sources.append({
            "source": source,
            "enabled": bool(config.get("source_enabled", {}).get(source, True)),
            "last_run": item.get("last_run"),
            "jobs_seen": item.get("jobs_seen", 0),
            "new_jobs": item.get("new_jobs", 0),
            "runtime": {
                "running": bool(runtime.get("running")),
                "last_success": runtime.get("last_success"),
            },
        })
    return {"sources": sources}


@app.get("/api/source-status", dependencies=[Depends(require_admin)])
def source_status():
    config = get_config()
    cutoff = iso(now() - dt.timedelta(hours=24))
    with sqlite3.connect(DB_PATH) as conn:
        latest_rows = conn.execute("""
            SELECT
                sr.source, sr.finished_at, sr.jobs_seen, sr.new_jobs, sr.error,
                sr.run_id, sr.outcome, sr.duration_seconds, sr.error_type,
                sr.http_status, sr.retry_after_seconds, sr.cooldown_seconds,
                sr.requests_attempted, sr.responses_received, sr.request_exceptions,
                sr.http_2xx, sr.http_3xx, sr.http_4xx, sr.http_5xx, sr.http_429,
                sr.retry_attempts, sr.request_duration_ms_total,
                sr.http_status_counts_json, sr.pages_attempted, sr.pages_succeeded,
                sr.pages_failed, sr.boards_attempted, sr.boards_succeeded, sr.boards_failed
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
        window_rows = conn.execute("""
            SELECT
                source,
                COUNT(*) AS runs,
                SUM(CASE WHEN requests_attempted IS NOT NULL THEN 1 ELSE 0 END) AS measured_runs,
                SUM(COALESCE(requests_attempted, 0)),
                SUM(COALESCE(responses_received, 0)),
                SUM(COALESCE(request_exceptions, 0)),
                SUM(COALESCE(http_2xx, 0)),
                SUM(COALESCE(http_3xx, 0)),
                SUM(COALESCE(http_4xx, 0)),
                SUM(COALESCE(http_5xx, 0)),
                SUM(COALESCE(http_429, 0)),
                SUM(COALESCE(retry_attempts, 0)),
                SUM(COALESCE(request_duration_ms_total, 0)),
                SUM(COALESCE(pages_attempted, 0)),
                SUM(COALESCE(pages_succeeded, 0)),
                SUM(COALESCE(pages_failed, 0)),
                SUM(COALESCE(boards_attempted, 0)),
                SUM(COALESCE(boards_succeeded, 0)),
                SUM(COALESCE(boards_failed, 0)),
                SUM(COALESCE(jobs_seen, 0)),
                SUM(COALESCE(new_jobs, 0)),
                SUM(CASE WHEN outcome IN ('failed', 'rate_limited') THEN 1 ELSE 0 END),
                SUM(CASE WHEN outcome IN ('partial_failed', 'partial_rate_limited') THEN 1 ELSE 0 END)
            FROM source_runs
            WHERE finished_at >= ?
            GROUP BY source
        """, (cutoff,)).fetchall()
        status_rows = conn.execute("""
            SELECT source, http_status_counts_json
            FROM source_runs
            WHERE finished_at >= ? AND http_status_counts_json IS NOT NULL
        """, (cutoff,)).fetchall()
        try:
            naukri_feed_row = conn.execute(
                "SELECT feed_updated_at, last_observed_at, feed_age_seconds, jobs_count, snapshot_unchanged "
                "FROM source_feed_state WHERE source='naukri'"
            ).fetchone()
        except sqlite3.OperationalError:
            naukri_feed_row = None

    last_naukri_feed = None
    if naukri_feed_row:
        relay_updated_at = parse_relative(naukri_feed_row[0])
        current_feed_age = (
            max(0.0, (now() - relay_updated_at).total_seconds())
            if relay_updated_at else None
        )
        last_naukri_feed = {
            "relay_updated_at": naukri_feed_row[0],
            "last_observed_at": naukri_feed_row[1],
            "age_seconds": round(current_feed_age, 1) if current_feed_age is not None else None,
            "age_at_last_poll_seconds": round(naukri_feed_row[2], 1),
            "jobs_count": naukri_feed_row[3],
            "snapshot_unchanged": bool(naukri_feed_row[4]),
            "fresh": current_feed_age is not None and current_feed_age <= NAUKRI_RELAY_MAX_AGE_SECONDS,
            "max_age_seconds": NAUKRI_RELAY_MAX_AGE_SECONDS,
        }

    history = {}
    for row in latest_rows:
        status_counts = {}
        try:
            parsed_counts = json.loads(row[22] or "{}")
            if isinstance(parsed_counts, dict):
                status_counts = {
                    str(code): int(count)
                    for code, count in parsed_counts.items()
                    if str(code).isdigit() and isinstance(count, int) and count >= 0
                }
        except (TypeError, ValueError, json.JSONDecodeError):
            status_counts = {}
        metrics_measured = row[12] is not None
        history[row[0]] = {
            "last_run": row[1],
            "jobs_seen": row[2] or 0,
            "new_jobs": row[3] or 0,
            "last_error": row[4],
            "last_run_id": row[5],
            "last_run_outcome": row[6],
            "last_run_duration_seconds": row[7],
            "last_error_type": row[8],
            "last_http_status": row[9],
            "last_retry_after_seconds": row[10],
            "last_cooldown_seconds": row[11],
            "last_request_metrics": ({
                "measured": True,
                "requests_attempted": row[12] or 0,
                "responses_received": row[13] or 0,
                "request_exceptions": row[14] or 0,
                "http_2xx": row[15] or 0,
                "http_3xx": row[16] or 0,
                "http_4xx": row[17] or 0,
                "http_5xx": row[18] or 0,
                "http_429": row[19] or 0,
                "retry_attempts": row[20] or 0,
                "request_duration_ms_total": round(row[21] or 0.0, 3),
                "avg_request_duration_ms": round((row[21] or 0.0) / row[12], 2) if row[12] else None,
                "http_status_counts": status_counts,
                "pages_attempted": row[23] or 0,
                "pages_succeeded": row[24] or 0,
                "pages_failed": row[25] or 0,
                "boards_attempted": row[26] or 0,
                "boards_succeeded": row[27] or 0,
                "boards_failed": row[28] or 0,
            } if metrics_measured else None),
        }

    windows = {}
    for row in window_rows:
        windows[row[0]] = {
            "runs": row[1] or 0,
            "measured_runs": row[2] or 0,
            "requests_attempted": row[3] or 0,
            "responses_received": row[4] or 0,
            "request_exceptions": row[5] or 0,
            "http_2xx": row[6] or 0,
            "http_3xx": row[7] or 0,
            "http_4xx": row[8] or 0,
            "http_5xx": row[9] or 0,
            "http_429": row[10] or 0,
            "retry_attempts": row[11] or 0,
            "request_duration_ms_total": round(row[12] or 0.0, 3),
            "avg_request_duration_ms": round((row[12] or 0.0) / row[3], 2) if row[3] else None,
            "pages_attempted": row[13] or 0,
            "pages_succeeded": row[14] or 0,
            "pages_failed": row[15] or 0,
            "boards_attempted": row[16] or 0,
            "boards_succeeded": row[17] or 0,
            "boards_failed": row[18] or 0,
            "jobs_seen": row[19] or 0,
            "new_jobs": row[20] or 0,
            "failed_runs": row[21] or 0,
            "partial_runs": row[22] or 0,
            "http_status_counts": {},
        }
    for source, raw_counts in status_rows:
        try:
            parsed_counts = json.loads(raw_counts or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(parsed_counts, dict):
            continue
        target = windows.setdefault(source, {
            "runs": 0, "measured_runs": 0, **{field: 0 for field in (
                "requests_attempted", "responses_received", "request_exceptions",
                "http_2xx", "http_3xx", "http_4xx", "http_5xx", "http_429",
                "retry_attempts", "request_duration_ms_total", "pages_attempted",
                "pages_succeeded", "pages_failed", "boards_attempted", "boards_succeeded",
                "boards_failed", "jobs_seen", "new_jobs", "failed_runs", "partial_runs",
            )}, "http_status_counts": {},
        })
        for code, count in parsed_counts.items():
            if str(code).isdigit() and isinstance(count, int) and count >= 0:
                target["http_status_counts"][str(code)] = (
                    target["http_status_counts"].get(str(code), 0) + count
                )

    sources = []
    for source in SOURCE_NAMES:
        item = history.get(source, {})
        sources.append({
            "source": source,
            "enabled": bool(config.get("source_enabled", {}).get(source, True)),
            "last_run": item.get("last_run"),
            "jobs_seen": item.get("jobs_seen", 0),
            "new_jobs": item.get("new_jobs", 0),
            "last_error": item.get("last_error"),
            "last_run_id": item.get("last_run_id"),
            "last_run_outcome": item.get("last_run_outcome"),
            "last_run_duration_seconds": item.get("last_run_duration_seconds"),
            "last_error_type": item.get("last_error_type"),
            "last_http_status": item.get("last_http_status"),
            "last_retry_after_seconds": item.get("last_retry_after_seconds"),
            "last_cooldown_seconds": item.get("last_cooldown_seconds"),
            "last_request_metrics": item.get("last_request_metrics"),
            "last_feed": last_naukri_feed if source == "naukri" else None,
            "last_24h": windows.get(source, {
                "runs": 0, "measured_runs": 0, "requests_attempted": 0,
                "responses_received": 0, "request_exceptions": 0,
                "http_2xx": 0, "http_3xx": 0, "http_4xx": 0, "http_5xx": 0,
                "http_429": 0, "retry_attempts": 0, "request_duration_ms_total": 0.0,
                "avg_request_duration_ms": None, "pages_attempted": 0, "pages_succeeded": 0, "pages_failed": 0,
                "boards_attempted": 0, "boards_succeeded": 0, "boards_failed": 0,
                "jobs_seen": 0, "new_jobs": 0, "failed_runs": 0, "partial_runs": 0,
                "http_status_counts": {},
            }),
            "runtime": source_state.get(source, {}),
        })

    return {"window_hours": 24, "sources": sources}


@app.get("/api/dedupe-candidates", dependencies=[Depends(require_admin)])
def dedupe_candidates(limit: int = 100):
    limit = max(1, min(limit, 500))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        source_placeholders = ",".join("?" for _ in SOURCE_NAMES)
        rows = conn.execute(f"""
            SELECT id, source, source_job_id, company, title, location, url, description
            FROM jobs
            WHERE source IN ({source_placeholders})
            ORDER BY id ASC
        """, SOURCE_NAMES).fetchall()

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


@app.get("/api/opportunities", dependencies=[Depends(require_admin)])
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
def jobs(
    minutes: int = 60,
    limit: int = 100,
    today_only: bool = False,
    q: str = "",
    search: str = "",
    page: int | None = None,
    per_page: int | None = None,
    status: str | None = None,
    source: str = "",
    min_score: int = 0,
    max_age_hours: int | None = None,
    sort: str = "newest",
    sort_by: str | None = None,
    sort_order: str | None = None,
    alertable_only: bool = False,
    remote_only: bool = False,
    user: dict[str, Any] = Depends(require_authenticated),
):
    preferences = user_preferences.get_user_preferences(DB_PATH, user["id"])
    if not preferences["onboarding_complete"]:
        raise HTTPException(
            status_code=403,
            detail="Complete your target role and location preferences before opening the job feed.",
        )
    ensure_user_job_evaluations_initialized(user["id"], preferences)
    minutes = max(1, min(minutes, 10080))
    legacy_limit = max(1, min(limit, 500))
    paginated = page is not None or per_page is not None
    page_number = max(1, int(page or 1))
    page_size = max(1, min(int(per_page or legacy_limit), 100)) if paginated else legacy_limit
    offset = (page_number - 1) * page_size if paginated else 0
    cutoff = (
        iso(current_day_start_utc())
        if today_only
        else iso(now() - dt.timedelta(minutes=minutes))
    )

    query = (search or q or "").strip()[:200]
    escaped_query = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    search_pattern = f"%{escaped_query.lower()}%" if query else "%"
    source_filter = (source or "").strip().casefold()[:64]
    min_score = max(0, min(int(min_score), 100))
    max_age_hours = None if max_age_hours is None else max(1, min(int(max_age_hours), 72))
    status = (status or ("all" if user["role"] == "admin" else "matched")).strip().casefold()
    if status not in {"matched", "all", "unmatched"}:
        raise HTTPException(status_code=422, detail="status must be matched, all, or unmatched.")
    if user["role"] != "admin" and status != "matched":
        raise HTTPException(status_code=403, detail="Users can only view their matched opportunities.")
    legacy_sort = sort if sort in {"newest", "match", "company"} else "newest"
    sort_by = sort_by or {
        "newest": "created_at", "match": "match_score", "company": "company"
    }[legacy_sort]
    if sort_by not in {"created_at", "match_score", "company"}:
        raise HTTPException(status_code=422, detail="sort_by must be created_at, match_score, or company.")
    sort_order = (sort_order or ("asc" if sort_by == "company" else "desc")).casefold()
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="sort_order must be asc or desc.")
    age_cutoff = iso(now() - dt.timedelta(hours=max_age_hours)) if max_age_hours else None
    threshold = int(preferences.get("match_threshold", 55))

    score_sql = "CASE WHEN ?='admin' THEN COALESCE(ge.score, 0) ELSE COALESCE(e.score, 0) END"
    match_sql = "CASE WHEN ?='admin' THEN COALESCE(ge.match, 0) ELSE COALESCE(e.match, 0) END"
    alertable_sql = "CASE WHEN ?='admin' THEN COALESCE(ge.alertable, 0) ELSE COALESCE(e.alertable, 0) END"
    where_sql = """
        WHERE (?='all'
          OR (?='matched' AND (CASE WHEN ?='admin' THEN COALESCE(ge.match, 0) ELSE COALESCE(e.match, 0) END)=1)
          OR (?='unmatched' AND ?='admin' AND COALESCE(ge.match, 0)=0))
          AND j.discovered_at >= ?
          AND LOWER(
                COALESCE(j.company, '') || ' ' ||
                COALESCE(j.title, '') || ' ' ||
                COALESCE(j.location, '') || ' ' ||
                COALESCE(j.source, '') || ' ' ||
                COALESCE(j.source_job_id, '') || ' ' ||
                COALESCE(j.description, '') || ' ' ||
                COALESCE(j.source_details_json, '{{}}') || ' ' ||
                COALESCE(e.reasons_json, '') || ' ' ||
                COALESCE(ge.reasons_json, '')
              ) LIKE ? ESCAPE '\\'
          AND (?='' OR LOWER(j.source)=?)
          AND (?=0 OR (
                {score_sql} >= ?
                AND (? < ? OR {match_sql}=1)
              ))
          AND (? IS NULL OR julianday(COALESCE(j.source_posted_at, j.discovered_at)) >= julianday(?))
          AND (?=0 OR {alertable_sql}=1)
          AND (?=0 OR LOWER(COALESCE(j.location, '') || ' ' || COALESCE(j.description, '')) LIKE '%remote%')
    """.format(score_sql=score_sql, match_sql=match_sql, alertable_sql=alertable_sql)

    base_params = (
        user["id"], status, status, user["role"], status, user["role"],
        cutoff, search_pattern,
        source_filter, source_filter,
        min_score, user["role"], min_score, min_score, threshold, user["role"],
        age_cutoff, age_cutoff,
        int(bool(alertable_only)), user["role"],
        int(bool(remote_only)),
    )

    order_expressions = {
        "created_at": "COALESCE(j.source_posted_at, j.discovered_at)",
        "match_score": score_sql,
        "company": "j.company COLLATE NOCASE",
    }
    order_sql = (
        "ORDER BY " + order_expressions[sort_by] + " " + sort_order.upper()
        + ", COALESCE(j.source_posted_at, j.discovered_at) DESC, j.id DESC"
    )
    order_params = (user["role"],) if sort_by == "match_score" else ()

    count_params = (user["id"], *base_params[1:])
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = int(conn.execute(
            "SELECT COUNT(*) FROM jobs j "
            "LEFT JOIN user_job_evaluations e ON e.job_id=j.id AND e.user_id=? "
            "LEFT JOIN job_evaluations ge ON ge.job_id=j.id "
            + where_sql,
            count_params,
        ).fetchone()[0])
        page_count = (total + page_size - 1) // page_size if total else 0
        if paginated and page_count:
            page_number = min(page_number, page_count)
            offset = (page_number - 1) * page_size
        elif paginated and not page_count:
            page_number = 1
            offset = 0

        rows = conn.execute(
            """
            SELECT
                j.*,
                e.match AS evaluation_match,
                e.score AS evaluation_score,
                e.reasons_json AS evaluation_reasons_json,
                e.experience_min_years AS evaluation_experience_min_years,
                e.experience_max_years AS evaluation_experience_max_years,
                e.alertable AS evaluation_alertable,
                e.alertability_reasons_json AS evaluation_alertability_reasons_json,
                ge.alertable AS admin_evaluation_alertable,
                ge.alertability_reasons_json AS admin_evaluation_alertability_reasons_json,
                nl.status AS notification_status,
                nl.decision_reason_json AS notification_decision_reasons_json,
                nl.sent_at AS notification_sent_at,
                nl.last_error AS notification_last_error,
                nl.candidate_job_id AS notification_candidate_job_id
            FROM jobs j
            LEFT JOIN user_job_evaluations e
              ON e.job_id=j.id AND e.user_id=?
            LEFT JOIN job_evaluations ge ON ge.job_id=j.id
            LEFT JOIN notification_ledger nl
              ON nl.canonical_opportunity_id=j.canonical_opportunity_id
             AND ?='admin'
            """
            + where_sql
            + " " + order_sql
            + " LIMIT ? OFFSET ?",
            (user["id"], user["role"], *base_params[1:], *order_params, page_size, offset),
        ).fetchall()

    def parse_json_list(value: Any) -> list[Any]:
        try:
            parsed = json.loads(value or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        return parsed if isinstance(parsed, list) else []

    result = []
    for row in rows:
        item = dict(row)
        item["description_format"] = (
            "markdown" if item.get("description_format") == "markdown" else "plain"
        )
        try:
            parsed_source_details = json.loads(item.pop("source_details_json", "{}") or "{}")
        except (TypeError, json.JSONDecodeError):
            parsed_source_details = {}
        item["source_details"] = (
            parsed_source_details if isinstance(parsed_source_details, dict) else {}
        )
        item["likely_match"] = bool(item.pop("evaluation_match", 0) or 0)
        score = item.pop("evaluation_score", None)
        item["match_score"] = int(score or 0)
        item["match_reasons"] = parse_json_list(item.pop("evaluation_reasons_json", None))
        exp_min = item.pop("evaluation_experience_min_years", None)
        exp_max = item.pop("evaluation_experience_max_years", None)
        item["experience_min_years"] = exp_min if exp_min is not None else item.get("experience_min_years")
        item["experience_max_years"] = exp_max if exp_max is not None else item.get("experience_max_years")
        item["experience_provenance"] = item.get("experience_provenance") or "unknown"
        item["experience_confidence"] = item.get("experience_confidence") or "unknown"
        if item["experience_provenance"] == "unknown":
            inferred_experience = _experience_provenance_details(item)
            item["experience_provenance"] = inferred_experience["provenance"]
            item["experience_confidence"] = inferred_experience["confidence"]
            if item["experience_min_years"] is None:
                item["experience_min_years"] = inferred_experience["min_years"]
            if item["experience_max_years"] is None:
                item["experience_max_years"] = inferred_experience["max_years"]
        user_alertable = item.pop("evaluation_alertable", 0)
        user_alertability_reasons = item.pop("evaluation_alertability_reasons_json", None)
        admin_alertable = item.pop("admin_evaluation_alertable", 0)
        admin_alertability_reasons = item.pop("admin_evaluation_alertability_reasons_json", None)
        item["alertable"] = bool(
            (admin_alertable if user["role"] == "admin" else user_alertable) or 0
        )
        item["alertability_reasons"] = parse_json_list(
            admin_alertability_reasons if user["role"] == "admin" else user_alertability_reasons
        )
        item["notification_status"] = item.get("notification_status") or "not_eligible"
        item["notification_decision_reasons"] = parse_json_list(
            item.pop("notification_decision_reasons_json", None)
        )
        item["notification_sent_at"] = item.get("notification_sent_at")
        item["notification_last_error"] = item.get("notification_last_error")
        item["notification_candidate_job_id"] = item.get("notification_candidate_job_id")
        result.append(item)

    pagination = {
        "page": page_number,
        "per_page": page_size,
        "total": total,
        "total_pages": page_count,
        "has_previous": page_number > 1,
        "has_next": offset + len(result) < total,
    }
    return {"jobs": result, "pagination": pagination}


@app.get("/api/notification-queue", dependencies=[Depends(require_admin)])
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


@app.get("/api/opportunities/{opportunity_id}", dependencies=[Depends(require_admin)])
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


@app.get("/api/llm-shadow-status", dependencies=[Depends(require_admin)])
def llm_shadow_status():
    """Return bounded Gemini shadow-mode health without exposing credentials or JD text."""
    return shadow_status(DB_PATH)


@app.get("/api/daily-summary")
def daily_summary(user: dict[str, Any] = Depends(require_authenticated)):
    preferences = user_preferences.get_user_preferences(DB_PATH, user["id"])
    if not preferences["onboarding_complete"]:
        raise HTTPException(
            status_code=403,
            detail="Complete your target role and location preferences before opening the job feed.",
        )
    ensure_user_job_evaluations_initialized(user["id"], preferences)
    cutoff = iso(current_day_start_utc())
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE discovered_at >= ?", (cutoff,)
        ).fetchone()[0]
        matched = conn.execute("""
            SELECT COUNT(*)
            FROM jobs j
            JOIN user_job_evaluations e ON e.job_id=j.id AND e.user_id=?
            WHERE j.discovered_at >= ? AND e.match=1
        """, (user["id"], cutoff)).fetchone()[0]
        alertable = 0
        alerted = 0
        if user["role"] == "admin":
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
def job_detail(
    job_id: int,
    user: dict[str, Any] = Depends(require_authenticated),
):
    preferences = user_preferences.get_user_preferences(DB_PATH, user["id"])
    if not preferences["onboarding_complete"]:
        raise HTTPException(
            status_code=403,
            detail="Complete your target role and location preferences before opening job details.",
        )
    ensure_user_job_evaluations_initialized(user["id"], preferences)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT j.*, e.match AS likely_match, e.score AS match_score,
                      e.reasons_json AS match_reasons_json,
                      e.experience_min_years AS evaluation_experience_min_years,
                      e.experience_max_years AS evaluation_experience_max_years
               FROM jobs j
               JOIN user_job_evaluations e
                 ON e.job_id=j.id AND e.user_id=?
               WHERE j.id=?""",
            (user["id"], job_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    result = dict(row)
    result["experience_min_years"] = (
        result.pop("evaluation_experience_min_years")
        if result.get("evaluation_experience_min_years") is not None
        else result.get("experience_min_years")
    )
    result["experience_max_years"] = (
        result.pop("evaluation_experience_max_years")
        if result.get("evaluation_experience_max_years") is not None
        else result.get("experience_max_years")
    )
    result["experience_provenance"] = result.get("experience_provenance") or "unknown"
    result["experience_confidence"] = result.get("experience_confidence") or "unknown"
    if result["experience_provenance"] == "unknown":
        inferred_experience = _experience_provenance_details(result)
        result["experience_provenance"] = inferred_experience["provenance"]
        result["experience_confidence"] = inferred_experience["confidence"]
        if result["experience_min_years"] is None:
            result["experience_min_years"] = inferred_experience["min_years"]
        if result["experience_max_years"] is None:
            result["experience_max_years"] = inferred_experience["max_years"]
    try:
        result["match_reasons"] = json.loads(result.pop("match_reasons_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        result["match_reasons"] = []
    return result

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard/")


if DASHBOARD_PATH.exists():
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_PATH, html=True), name="dashboard")