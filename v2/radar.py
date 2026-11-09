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
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from v2 import ats_directory, auth, board_discovery, google_oauth, hirebase, resume_parser, telegram_linking, user_preferences, user_notifications, user_applications

from v2.dedupe import auto_link_allowed, canonical_identity, canonical_match_score, canonicalize_url
from v2.gemini_extractor import cached_matcher_experience, shadow_extract_jobs, shadow_status
from v2.sqlite_store import DB_LOCK, connect as connect_sqlite, enable_wal

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
LEVER_PAGE_SIZE = 100
LEVER_MAX_PAGES_PER_BOARD = 5
LEVER_MAX_BOARDS = 20
WORKDAY_PAGE_SIZE = 20
WORKDAY_MAX_PAGES_PER_BOARD = 2  # Freshness page plus at most one inventory page.
WORKDAY_MAX_DETAILS_PER_BOARD = 20
WORKDAY_INVENTORY_PAGE_INTERVAL_SECONDS = 15 * 60
WORKDAY_FULL_INVENTORY_REFRESH_SECONDS = 7 * 24 * 60 * 60
WORKDAY_INVENTORY_MAX_OFFSET = 2000
WORKDAY_MAX_FACET_DEPTH = 4
WORKDAY_MAX_FACET_PARTITIONS = 500
WORKDAY_SUBDIVISION_FACETS = ("jobFamilyGroup", "timeType", "locations", "workerSubType")
WORKDAY_MAX_BOARDS = 20
WORKDAY_DETAIL_DELAY_SECONDS = 0.1
WORKDAY_DEFAULT_429_COOLDOWN_SECONDS = 300
WORKDAY_MAX_429_COOLDOWN_SECONDS = 3600
SMARTRECRUITERS_PAGE_SIZE = 100
SMARTRECRUITERS_MAX_PAGES_PER_BOARD = 3
SMARTRECRUITERS_MAX_DETAILS_PER_BOARD = 20
SMARTRECRUITERS_MAX_BOARDS = 50
SMARTRECRUITERS_DETAIL_DELAY_SECONDS = 0.1
WORKABLE_MAX_JOBS_PER_BOARD = 500
WORKABLE_MAX_BOARDS = 50
KEKA_MAX_BOARDS = 50
KEKA_MAX_JOBS_PER_BOARD = 1000
DARWINBOX_MAX_BOARDS = 50
DARWINBOX_PAGE_SIZE = 50
DARWINBOX_MAX_PAGES_PER_BOARD = 5
DARWINBOX_PAGE_DELAY_SECONDS = 0.2
HIREBASE_PROVIDER_LIMIT = 4
HIREBASE_MAX_MONTHLY_JOBS = 400
HIREBASE_MAX_DAILY_JOBS = 12
HIREBASE_PROVIDER_DAILY_JOBS = 4
PUBLIC_ATS_RATE_LIMIT_SOURCES = frozenset({"workday", "smartrecruiters", "workable", "keka", "darwinbox", "hirebase"})
INITIAL_SNAPSHOT_BASELINE_SOURCES = frozenset({"lever", "workday", "hirebase"})

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


db_lock = DB_LOCK
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
    # Version 12 introduces Lever's public postings API as an opt-in source.
    # Existing runtimes must never start polling new employer boards implicitly.
    if current_version < 12 <= default_version:
        merged.setdefault("source_enabled", {})["lever"] = False
    # Version 13 adds Workday CXS as an opt-in public career-site source.
    if current_version < 13 <= default_version:
        merged.setdefault("source_enabled", {})["workday"] = False
    if current_version < 14 <= default_version:
        merged.setdefault("source_enabled", {})["smartrecruiters"] = False
        merged.setdefault("source_enabled", {})["workable"] = False
    if current_version < 15 <= default_version:
        merged.setdefault("source_enabled", {})["keka"] = False
        merged.setdefault("source_enabled", {})["darwinbox"] = False
    if current_version < 17 <= default_version:
        merged.setdefault("source_enabled", {})["hirebase"] = False
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
        if current_version < 12 <= default_version:
            merged["source_enabled"]["lever"] = False
        if current_version < 13 <= default_version:
            merged["source_enabled"]["workday"] = False
        if current_version < 14 <= default_version:
            merged["source_enabled"]["smartrecruiters"] = False
            merged["source_enabled"]["workable"] = False
        if current_version < 15 <= default_version:
            merged["source_enabled"]["keka"] = False
            merged["source_enabled"]["darwinbox"] = False
        if current_version < 17 <= default_version:
            merged["source_enabled"]["hirebase"] = False
    return merged


def _parse_workday_board_url(value: Any) -> dict[str, str] | None:
    """Resolve a public Workday career-board URL into its CXS identifiers."""
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 500:
        return None
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").lower()
        match = re.fullmatch(
            r"(?P<tenant>[a-z0-9-]{1,80})\.wd(?P<cluster>[0-9]{1,3})\.myworkdayjobs\.com",
            host,
        )
        if (
            parsed.scheme.lower() != "https"
            or not match
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            return None
        segments = [segment for segment in parsed.path.split("/") if segment]
        if segments and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", segments[0]):
            segments = segments[1:]
        if len(segments) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", segments[0]):
            return None
        tenant = match.group("tenant")
        site = segments[0]
        return {
            "url": f"https://{host}/{site}",
            "host": host,
            "tenant": tenant,
            "cluster": match.group("cluster"),
            "site": site,
        }
    except ValueError:
        return None


def _optional_registry_id(board: dict[str, Any], provider: str) -> int | None:
    value = board.get("registry_id")
    if value is None:
        return None
    try:
        identifier = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{provider} registry_id must be an integer.") from exc
    if identifier < 1:
        raise HTTPException(status_code=422, detail=f"{provider} registry_id must be positive.")
    return identifier


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
        normalized_entry = {"token": token, "company": company.strip()}
        registry_id = _optional_registry_id(board, "Greenhouse")
        if registry_id is not None:
            normalized_entry["registry_id"] = registry_id
        normalized_boards.append(normalized_entry)
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
        normalized_entry = {"board": name, "company": company.strip()}
        registry_id = _optional_registry_id(board, "Ashby")
        if registry_id is not None:
            normalized_entry["registry_id"] = registry_id
        normalized_ashby_boards.append(normalized_entry)
    config["ashby_boards"] = normalized_ashby_boards

    lever_boards = config.get("lever_boards", [])
    if not isinstance(lever_boards, list):
        raise HTTPException(status_code=422, detail="lever_boards must be a list.")
    if len(lever_boards) > LEVER_MAX_BOARDS:
        raise HTTPException(
            status_code=422,
            detail=f"lever_boards cannot contain more than {LEVER_MAX_BOARDS} boards.",
        )
    normalized_lever_boards: list[dict[str, str]] = []
    seen_lever_sites: set[tuple[str, str]] = set()
    for board in lever_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each Lever board must be an object.")
        site = board.get("site")
        company = board.get("company")
        instance = str(board.get("instance") or "global").strip().lower()
        if not isinstance(site, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", site.strip()):
            raise HTTPException(status_code=422, detail="Each Lever board requires a valid public site name.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each Lever board requires a company label of at most 120 characters.")
        if instance not in {"global", "eu"}:
            raise HTTPException(status_code=422, detail="Lever board instance must be 'global' or 'eu'.")
        site = site.strip()
        identity = (instance, site.lower())
        if identity in seen_lever_sites:
            raise HTTPException(status_code=422, detail=f"Duplicate Lever board site: {site} ({instance}).")
        seen_lever_sites.add(identity)
        normalized_entry = {"site": site, "company": company.strip(), "instance": instance}
        registry_id = _optional_registry_id(board, "Lever")
        if registry_id is not None:
            normalized_entry["registry_id"] = registry_id
        normalized_lever_boards.append(normalized_entry)
    config["lever_boards"] = normalized_lever_boards

    workday_boards = config.get("workday_boards", [])
    if not isinstance(workday_boards, list):
        raise HTTPException(status_code=422, detail="workday_boards must be a list.")
    if len(workday_boards) > WORKDAY_MAX_BOARDS:
        raise HTTPException(status_code=422, detail=f"workday_boards cannot contain more than {WORKDAY_MAX_BOARDS} boards.")
    normalized_workday_boards: list[dict[str, str]] = []
    seen_workday_boards: set[tuple[str, str]] = set()
    for board in workday_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each Workday board must be an object.")
        parsed_board = _parse_workday_board_url(board.get("url"))
        company = board.get("company")
        if not parsed_board:
            raise HTTPException(status_code=422, detail="Each Workday board requires an HTTPS public myworkdayjobs.com career URL.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each Workday board requires a company label of at most 120 characters.")
        identity = (parsed_board["host"], parsed_board["site"].lower())
        if identity in seen_workday_boards:
            raise HTTPException(status_code=422, detail="Duplicate Workday career board URL.")
        seen_workday_boards.add(identity)
        normalized_entry = {"url": parsed_board["url"], "company": company.strip()}
        registry_id = _optional_registry_id(board, "Workday")
        if registry_id is not None:
            normalized_entry["registry_id"] = registry_id
        normalized_workday_boards.append(normalized_entry)
    config["workday_boards"] = normalized_workday_boards

    smartrecruiters_boards = config.get("smartrecruiters_boards", [])
    if not isinstance(smartrecruiters_boards, list) or len(smartrecruiters_boards) > SMARTRECRUITERS_MAX_BOARDS:
        raise HTTPException(status_code=422, detail=f"smartrecruiters_boards must be a list with at most {SMARTRECRUITERS_MAX_BOARDS} entries.")
    normalized_smartrecruiters: list[dict[str, str]] = []
    seen_smartrecruiters: set[str] = set()
    for board in smartrecruiters_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each SmartRecruiters board must be an object.")
        identifier = board.get("company_identifier") or board.get("identifier")
        company = board.get("company")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", identifier.strip()):
            raise HTTPException(status_code=422, detail="Each SmartRecruiters board requires a valid company identifier.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each SmartRecruiters board requires a company label of at most 120 characters.")
        identifier = identifier.strip()
        if identifier.lower() in seen_smartrecruiters:
            raise HTTPException(status_code=422, detail=f"Duplicate SmartRecruiters company identifier: {identifier}.")
        seen_smartrecruiters.add(identifier.lower())
        normalized_entry = {"company_identifier": identifier, "company": company.strip()}
        registry_id = _optional_registry_id(board, "SmartRecruiters")
        if registry_id is not None:
            normalized_entry["registry_id"] = registry_id
        normalized_smartrecruiters.append(normalized_entry)
    config["smartrecruiters_boards"] = normalized_smartrecruiters

    workable_boards = config.get("workable_boards", [])
    if not isinstance(workable_boards, list) or len(workable_boards) > WORKABLE_MAX_BOARDS:
        raise HTTPException(status_code=422, detail=f"workable_boards must be a list with at most {WORKABLE_MAX_BOARDS} entries.")
    normalized_workable: list[dict[str, str]] = []
    seen_workable: set[str] = set()
    for board in workable_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each Workable board must be an object.")
        account = board.get("account") or board.get("subdomain")
        company = board.get("company")
        if not isinstance(account, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,100}", account.strip()):
            raise HTTPException(status_code=422, detail="Each Workable board requires a valid public account slug.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each Workable board requires a company label of at most 120 characters.")
        account = account.strip()
        if account.lower() in seen_workable:
            raise HTTPException(status_code=422, detail=f"Duplicate Workable account: {account}.")
        seen_workable.add(account.lower())
        normalized_entry = {"account": account, "company": company.strip()}
        registry_id = _optional_registry_id(board, "Workable")
        if registry_id is not None:
            normalized_entry["registry_id"] = registry_id
        normalized_workable.append(normalized_entry)
    config["workable_boards"] = normalized_workable

    keka_boards = config.get("keka_boards", [])
    if not isinstance(keka_boards, list) or len(keka_boards) > KEKA_MAX_BOARDS:
        raise HTTPException(status_code=422, detail=f"keka_boards must be a list with at most {KEKA_MAX_BOARDS} entries.")
    normalized_keka: list[dict[str, Any]] = []
    seen_keka: set[str] = set()
    for board in keka_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each Keka board must be an object.")
        careers_url = board.get("careers_url") or board.get("url")
        detected = board_discovery.detect_ats_board(careers_url) if isinstance(careers_url, str) else None
        company = board.get("company")
        if not detected or detected.get("provider") != "keka":
            raise HTTPException(status_code=422, detail="Each Keka board requires a public HTTPS https://<tenant>.keka.com/careers URL.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each Keka board requires a company label of at most 120 characters.")
        board_key = str(detected["board_key"]).lower()
        if board_key in seen_keka:
            raise HTTPException(status_code=422, detail=f"Duplicate Keka public portal: {board_key}.")
        seen_keka.add(board_key)
        entry = {"careers_url": detected["board_url"], "company": company.strip()}
        registry_id = _optional_registry_id(board, "Keka")
        if registry_id is not None:
            entry["registry_id"] = registry_id
        normalized_keka.append(entry)
    config["keka_boards"] = normalized_keka

    darwinbox_boards = config.get("darwinbox_boards", [])
    if not isinstance(darwinbox_boards, list) or len(darwinbox_boards) > DARWINBOX_MAX_BOARDS:
        raise HTTPException(status_code=422, detail=f"darwinbox_boards must be a list with at most {DARWINBOX_MAX_BOARDS} entries.")
    normalized_darwinbox: list[dict[str, Any]] = []
    seen_darwinbox: set[tuple[str, str]] = set()
    for board in darwinbox_boards:
        if not isinstance(board, dict):
            raise HTTPException(status_code=422, detail="Each Darwinbox board must be an object.")
        careers_url = board.get("careers_url") or board.get("url")
        detected = board_discovery.detect_ats_board(careers_url) if isinstance(careers_url, str) else None
        company = board.get("company")
        if not detected or detected.get("provider") != "darwinbox":
            raise HTTPException(status_code=422, detail="Each Darwinbox board requires a public HTTPS /ms/candidatev2/<companyId>/careers URL.")
        if not isinstance(company, str) or not company.strip() or len(company.strip()) > 120:
            raise HTTPException(status_code=422, detail="Each Darwinbox board requires a company label of at most 120 characters.")
        identity = (str(detected["host"]).lower(), str(detected["board_key"]).lower())
        if identity in seen_darwinbox:
            raise HTTPException(status_code=422, detail="Duplicate Darwinbox careers board.")
        seen_darwinbox.add(identity)
        entry = {"careers_url": detected["board_url"], "company": company.strip()}
        registry_id = _optional_registry_id(board, "Darwinbox")
        if registry_id is not None:
            entry["registry_id"] = registry_id
        normalized_darwinbox.append(entry)
    config["darwinbox_boards"] = normalized_darwinbox

    source_enabled = config.get("source_enabled", {})
    if not isinstance(source_enabled, dict):
        raise HTTPException(status_code=422, detail="source_enabled must be an object.")
    config["source_enabled"] = {
        "linkedin": bool(source_enabled.get("linkedin", True)),
        "naukri": bool(source_enabled.get("naukri", True)),
        "instahyre": bool(source_enabled.get("instahyre", True)),
        "greenhouse": bool(source_enabled.get("greenhouse", False)),
        "ashby": bool(source_enabled.get("ashby", False)),
        "lever": bool(source_enabled.get("lever", False)),
        "workday": bool(source_enabled.get("workday", False)),
        "smartrecruiters": bool(source_enabled.get("smartrecruiters", False)),
        "workable": bool(source_enabled.get("workable", False)),
        "keka": bool(source_enabled.get("keka", False)),
        "darwinbox": bool(source_enabled.get("darwinbox", False)),
        "hirebase": bool(source_enabled.get("hirebase", False)),
    }
    if config["source_enabled"]["hirebase"] and not hirebase.api_key_configured():
        raise HTTPException(status_code=422, detail="Configure HIREBASE_API_KEY in the isolated server environment before enabling Hirebase.")
    if config["source_enabled"]["workday"] and not normalized_workday_boards:
        raise HTTPException(
            status_code=422,
            detail="Add at least one verified Workday public career board before enabling Workday.",
        )
    for source, configured_boards in (
        ("smartrecruiters", normalized_smartrecruiters),
        ("workable", normalized_workable),
        ("keka", normalized_keka),
        ("darwinbox", normalized_darwinbox),
    ):
        if config["source_enabled"][source] and not configured_boards:
            raise HTTPException(status_code=422, detail=f"Add at least one verified {source.title()} public career board before enabling {source.title()}.")

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
            "lever": 1800,
            "workday": 120,
            "smartrecruiters": 120,
            "workable": 120,
            "keka": 120,
            "darwinbox": 120,
            "hirebase": 86400,
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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
        enable_wal(conn)
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
            baseline_suppressed INTEGER NOT NULL DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS employer_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            domain TEXT NOT NULL UNIQUE,
            website_url TEXT NOT NULL,
            careers_url TEXT NOT NULL,
            country TEXT,
            discovery_status TEXT NOT NULL DEFAULT 'not_scanned',
            pages_checked INTEGER NOT NULL DEFAULT 0,
            last_discovered_at TEXT,
            error_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ats_board_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            board_key TEXT NOT NULL,
            board_url TEXT NOT NULL,
            discovered_from TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'medium',
            collector_source TEXT,
            collector_available INTEGER NOT NULL DEFAULT 0,
            review_status TEXT NOT NULL DEFAULT 'discovered',
            last_verified_at TEXT,
            last_seen_at TEXT NOT NULL,
            last_error_type TEXT,
            baseline_pending INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(company_id) REFERENCES employer_companies(id),
            UNIQUE(company_id, provider, board_key)
        )
        """)
        _ensure_column(conn, "ats_board_registry", "baseline_pending", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "ats_board_registry", "directory_last_crawled", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_board_provider ON ats_board_registry(provider, review_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ats_board_company ON ats_board_registry(company_id, provider)")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS workday_board_poll_state (
            board_key TEXT PRIMARY KEY,
            next_inventory_offset INTEGER NOT NULL DEFAULT 20,
            last_inventory_attempt_at TEXT,
            last_full_inventory_at TEXT,
            reported_total INTEGER,
            facets_json TEXT NOT NULL DEFAULT '[]',
            inventory_complete INTEGER NOT NULL DEFAULT 0,
            truncated_reason TEXT,
            facet_queue_json TEXT NOT NULL DEFAULT '[]',
            active_facets_json TEXT NOT NULL DEFAULT '{}',
            active_facet_depth INTEGER NOT NULL DEFAULT 0,
            active_facet_query INTEGER NOT NULL DEFAULT 0,
            facet_partition_started INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """)
        _ensure_column(conn, "workday_board_poll_state", "facet_queue_json", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(conn, "workday_board_poll_state", "active_facets_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "workday_board_poll_state", "active_facet_depth", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "workday_board_poll_state", "active_facet_query", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "workday_board_poll_state", "facet_partition_started", "INTEGER NOT NULL DEFAULT 0")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS hirebase_usage_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            created_at TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            estimated_jobs INTEGER NOT NULL,
            returned_jobs INTEGER,
            reserved_jobs INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            included_used INTEGER,
            included_remaining INTEGER,
            response_verified INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hirebase_usage_period ON hirebase_usage_ledger(period_start, created_at, provider)")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS hirebase_provider_state (
            provider TEXT PRIMARY KEY,
            last_polled_at TEXT NOT NULL,
            window_start TEXT NOT NULL,
            next_page INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        )
        """)
        _ensure_column(conn, "hirebase_provider_state", "window_start", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "hirebase_provider_state", "next_page", "INTEGER NOT NULL DEFAULT 1")
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
        _ensure_column(conn, "notification_ledger", "baseline_suppressed", "INTEGER NOT NULL DEFAULT 0")
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
    user_applications.reconcile_canonical_ids(DB_PATH)
    backfill_notification_ledger()
    auth.init_auth_schema(DB_PATH)
    user_preferences.init_preferences_schema(DB_PATH)
    telegram_linking.init_schema(DB_PATH)
    user_notifications.init_schema(DB_PATH)
    user_applications.init_schema(DB_PATH)
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

    with db_lock, connect_sqlite(DB_PATH) as conn:
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

            first_seen = conn.execute(
                "SELECT first_seen_at FROM jobs WHERE id=?",
                (int(job_id),),
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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    if not {"jobs", "user_job_evaluations"}.issubset(tables):
        return 0
    fingerprint = user_preferences.preferences_fingerprint(
        preferences, MATCHER_RULES_VERSION
    )
    changed = 0
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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


def suppress_initial_source_snapshot_alerts(
    source: str,
    started_at: dt.datetime,
) -> int:
    """Persistently suppress first-inventory alerts for timestamp-unknown ATS sources.

    Partial first runs are also baseline inventory: subsequent partial runs keep
    suppressing only newly discovered records until one complete successful run
    is recorded. Existing canonical opportunities seen before this run are not
    modified, and other sources are never affected.
    """
    if source not in INITIAL_SNAPSHOT_BASELINE_SOURCES:
        return 0

    with db_lock, connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        has_successful_run = conn.execute(
            """
            SELECT 1 FROM source_runs
            WHERE source=? AND outcome='success'
            LIMIT 1
            """,
            (source,),
        ).fetchone()
        if has_successful_run:
            return 0

        cutoff = iso(started_at)
        timestamp = iso(now())
        reasons = json.dumps(
            [
                "initial source inventory baseline",
                "source has no reliable publication timestamp",
                "do not alert on listings already present before first successful source run",
            ],
            ensure_ascii=False,
        )
        canonical_ids = conn.execute(
            """
            SELECT DISTINCT j.canonical_opportunity_id
            FROM jobs j
            WHERE j.source=?
              AND j.canonical_opportunity_id IS NOT NULL
              AND j.first_seen_at >= ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM jobs earlier
                  WHERE earlier.canonical_opportunity_id=j.canonical_opportunity_id
                    AND earlier.first_seen_at < ?
              )
            """,
            (source, cutoff, cutoff),
        ).fetchall()
        suppressed = 0
        for row in canonical_ids:
            cursor = conn.execute(
                """
                UPDATE notification_ledger
                SET status='suppressed',
                    candidate_job_id=NULL,
                    baseline_suppressed=1,
                    updated_at=?,
                    decision_reason_json=?
                WHERE canonical_opportunity_id=?
                  AND baseline_suppressed=0
                  AND status IN ('pending', 'queued', 'suppressed')
                  AND attempt_count=0
                  AND sent_at IS NULL
                """,
                (timestamp, reasons, int(row["canonical_opportunity_id"])),
            )
            suppressed += max(0, cursor.rowcount)
        conn.commit()
    return suppressed


def suppress_activated_board_inventory(source: str) -> int:
    """Silence the first snapshot of each newly activated employer board.

    Board discovery can identify an existing vacancy archive. These rows are
    useful in the dashboard, but should not be mistaken for freshly published
    jobs when an administrator first connects a company. The first successful
    source poll marks those board rows as baseline and cancels any unattempted
    legacy/member queue records for the same jobs.
    """
    suppressed_jobs = 0
    timestamp = iso(now())
    reasons = json.dumps([
        "initial employer-board inventory baseline",
        "board was explicitly activated after discovery and endpoint verification",
        "historical inventory is visible in the dashboard but is not a new-job alert",
    ], ensure_ascii=False)
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        registry_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ats_board_registry'"
        ).fetchone()
        if not registry_exists:
            return 0
        pending_rows = conn.execute(
            "SELECT id FROM ats_board_registry WHERE collector_source=? AND baseline_pending=1 AND review_status='active'",
            (source,),
        ).fetchall()
        pending_ids = {int(row["id"]) for row in pending_rows}
        if not pending_ids:
            return 0
        rows = conn.execute(
            "SELECT id,canonical_opportunity_id,source_details_json,first_seen_at FROM jobs WHERE source=?",
            (source,),
        ).fetchall()
        seen_registry_ids: set[int] = set()
        for row in rows:
            try:
                details = json.loads(row["source_details_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                details = {}
            raw_registry_id = details.get("board_registry_id") if isinstance(details, dict) else None
            try:
                registry_id = int(raw_registry_id) if raw_registry_id is not None else None
            except (TypeError, ValueError):
                registry_id = None
            if registry_id not in pending_ids:
                continue
            seen_registry_ids.add(registry_id)
            job_id = int(row["id"])
            conn.execute("UPDATE jobs SET source_initial_baseline=1 WHERE id=?", (job_id,))
            canonical_id = row["canonical_opportunity_id"]
            if canonical_id is not None:
                ledger = conn.execute(
                    "SELECT candidate_job_id FROM notification_ledger WHERE canonical_opportunity_id=?",
                    (int(canonical_id),),
                ).fetchone()
                if ledger is not None:
                    candidate_job_id = ledger["candidate_job_id"]
                    earlier_observation = conn.execute(
                        """SELECT 1 FROM jobs
                           WHERE canonical_opportunity_id=? AND id<>? AND first_seen_at<?
                           LIMIT 1""",
                        (int(canonical_id), job_id, row["first_seen_at"]),
                    ).fetchone()
                    # A ledger row is often created before matching chooses a
                    # candidate. Suppress that null-candidate row only when this
                    # activated board introduced the canonical opportunity.
                    # Preserve an existing cross-source opportunity and any
                    # already-selected candidate from another source.
                    safe_to_suppress = (
                        candidate_job_id == job_id
                        or (candidate_job_id is None and earlier_observation is None)
                    )
                    if safe_to_suppress:
                        conn.execute(
                            """UPDATE notification_ledger
                               SET status='suppressed',candidate_job_id=NULL,baseline_suppressed=1,
                                   next_attempt_at=NULL,claimed_at=NULL,updated_at=?,decision_reason_json=?
                               WHERE canonical_opportunity_id=?
                                 AND (candidate_job_id IS NULL OR candidate_job_id=?)
                                 AND baseline_suppressed=0
                                 AND status IN ('pending','queued','suppressed')
                                 AND attempt_count=0 AND sent_at IS NULL""",
                            (timestamp, reasons, int(canonical_id), job_id),
                        )
            conn.execute(
                """UPDATE user_notification_ledger
                   SET status='cancelled',claimed_at=NULL,next_attempt_at=NULL,
                       last_error='initial_employer_board_baseline',updated_at=?
                   WHERE candidate_job_id=? AND status IN ('queued','failed','sending')
                     AND attempt_count=0 AND sent_at IS NULL""",
                (timestamp, job_id),
            )
            suppressed_jobs += 1
        for registry_id in seen_registry_ids:
            conn.execute(
                "UPDATE ats_board_registry SET baseline_pending=0,updated_at=? WHERE id=?",
                (timestamp, registry_id),
            )
        conn.commit()
    return suppressed_jobs


def refresh_notification_decisions(config: dict[str, Any] | None = None) -> int:
    config = config or get_config()
    now_value = now()
    max_age = int(config.get("max_age_hours", 72))
    rediscovery_cutoff = iso(now_value - dt.timedelta(minutes=10))
    changed = 0

    with db_lock, connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        candidates = conn.execute(
            """
            SELECT canonical_opportunity_id, status
            FROM notification_ledger
            WHERE baseline_suppressed=0
              AND (
                status IN ('pending', 'queued')
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
    allow_redirects: bool = True,
) -> requests.Response:
    """Record safe request metadata; never persist URLs, query strings or payloads."""
    started_monotonic = time.monotonic()
    try:
        response = requests.get(
            endpoint, params=params, headers=headers, timeout=timeout,
            allow_redirects=allow_redirects,
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


def _tracked_source_post(
    source: str,
    endpoint: str,
    *,
    json_body: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    allow_redirects: bool = True,
) -> requests.Response:
    """Record safe request metadata for a JSON POST; never persist payloads or URLs."""
    started_monotonic = time.monotonic()
    try:
        response = requests.post(
            endpoint, json=json_body, headers=headers, timeout=timeout,
            allow_redirects=allow_redirects,
        )
    except Exception:
        _record_source_request(
            source, status_code=None,
            duration_ms=(time.monotonic() - started_monotonic) * 1000,
            exception=True,
        )
        raise
    _record_source_request(
        source, status_code=getattr(response, "status_code", None),
        duration_ms=(time.monotonic() - started_monotonic) * 1000,
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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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
        with db_lock, connect_sqlite(DB_PATH) as conn:
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


def restore_workday_rate_limit_state() -> None:
    """Restore the latest Workday Retry-After cooldown after an application restart."""
    runtime = source_state.setdefault("workday", {})
    try:
        with db_lock, connect_sqlite(DB_PATH) as conn:
            row = conn.execute(
                "SELECT http_status,rate_limit_detected_at,finished_at,cooldown_seconds,retry_after_seconds "
                "FROM source_runs WHERE source='workday' ORDER BY id DESC LIMIT 1"
            ).fetchone()
    except sqlite3.Error:
        log.exception("workday: unable to restore persisted 429 cooldown")
        return

    if not row or int(row[0] or 0) != 429:
        for key in (
            "rate_limited_until", "rate_limited_until_monotonic",
            "rate_limit_cooldown_seconds", "rate_limit_retry_after_seconds",
            "rate_limit_detected_at",
        ):
            runtime.pop(key, None)
        return

    detected_at = parse_relative(row[1] or row[2])
    if detected_at is None:
        log.warning("workday: skipped invalid persisted rate-limit timestamp")
        return
    cooldown_seconds = max(60, min(
        WORKDAY_MAX_429_COOLDOWN_SECONDS,
        int(row[3] or WORKDAY_DEFAULT_429_COOLDOWN_SECONDS),
    ))
    elapsed_seconds = max(0.0, (now() - detected_at).total_seconds())
    remaining_seconds = max(0.0, cooldown_seconds - elapsed_seconds)
    runtime["rate_limit_detected_at"] = iso(detected_at)
    runtime["rate_limit_cooldown_seconds"] = cooldown_seconds
    runtime["rate_limit_retry_after_seconds"] = row[4]
    if remaining_seconds > 0:
        runtime["rate_limited_until"] = iso(now() + dt.timedelta(seconds=remaining_seconds))
        runtime["rate_limited_until_monotonic"] = time.monotonic() + remaining_seconds
        log.warning("workday: restored persisted 429 cooldown; remaining=%ss", int(remaining_seconds))
    else:
        runtime.pop("rate_limited_until", None)
        runtime.pop("rate_limited_until_monotonic", None)


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



def _set_workday_rate_limit(response: requests.Response) -> int:
    """Record a conservative source-wide Workday cooldown from a 429 response."""
    return _set_source_rate_limit(
        "workday", response,
        default_seconds=WORKDAY_DEFAULT_429_COOLDOWN_SECONDS,
        maximum_seconds=WORKDAY_MAX_429_COOLDOWN_SECONDS,
    )


def _workday_cooldown_remaining() -> float:
    return _source_cooldown_remaining("workday")


def _set_source_rate_limit(
    source: str,
    response: requests.Response,
    *,
    default_seconds: int = 300,
    maximum_seconds: int = 3600,
) -> int:
    """Persist a conservative source-wide Retry-After cooldown in runtime state."""
    retry_after = _retry_after_seconds(response)
    requested = default_seconds if retry_after is None else max(60, retry_after)
    cooldown_seconds = int(min(maximum_seconds, requested))
    runtime = source_state.setdefault(source, {})
    runtime["rate_limit_retry_after_seconds"] = retry_after
    runtime["rate_limit_cooldown_seconds"] = cooldown_seconds
    runtime["rate_limit_detected_at"] = iso(now())
    runtime["rate_limited_until_monotonic"] = time.monotonic() + cooldown_seconds
    runtime["rate_limited_until"] = iso(now() + dt.timedelta(seconds=cooldown_seconds))
    log.warning("%s: HTTP 429; pausing source requests for %ss", source, cooldown_seconds)
    return cooldown_seconds


def _source_cooldown_remaining(source: str) -> float:
    return max(
        0.0,
        float(source_state.get(source, {}).get("rate_limited_until_monotonic", 0.0))
        - time.monotonic(),
    )


def restore_source_rate_limit_state(source: str) -> None:
    """Restore one source's last persisted HTTP 429 cooldown after restart."""
    runtime = source_state.setdefault(source, {})
    try:
        with DB_LOCK, connect_sqlite(DB_PATH) as conn:
            row = conn.execute(
                "SELECT http_status,rate_limit_detected_at,finished_at,cooldown_seconds,retry_after_seconds "
                "FROM source_runs WHERE source=? ORDER BY id DESC LIMIT 1", (source,)
            ).fetchone()
    except sqlite3.Error:
        log.exception("%s: unable to restore persisted 429 cooldown", source)
        return
    if not row or int(row[0] or 0) != 429:
        for key in ("rate_limited_until", "rate_limited_until_monotonic", "rate_limit_cooldown_seconds", "rate_limit_retry_after_seconds", "rate_limit_detected_at"):
            runtime.pop(key, None)
        return
    detected_at = parse_relative(row[1] or row[2])
    if detected_at is None:
        log.warning("%s: skipped invalid persisted rate-limit timestamp", source)
        return
    cooldown_seconds = max(60, min(3600, int(row[3] or 300)))
    remaining = max(0.0, cooldown_seconds - max(0.0, (now() - detected_at).total_seconds()))
    runtime["rate_limit_detected_at"] = iso(detected_at)
    runtime["rate_limit_cooldown_seconds"] = cooldown_seconds
    runtime["rate_limit_retry_after_seconds"] = row[4]
    if remaining > 0:
        runtime["rate_limited_until"] = iso(now() + dt.timedelta(seconds=remaining))
        runtime["rate_limited_until_monotonic"] = time.monotonic() + remaining
        log.warning("%s: restored persisted 429 cooldown; remaining=%ss", source, int(remaining))
    else:
        runtime.pop("rate_limited_until", None)
        runtime.pop("rate_limited_until_monotonic", None)


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
    with db_lock, connect_sqlite(DB_PATH) as conn:
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

INSTAHYRE_PAGE_SIZE = 35
INSTAHYRE_MAX_PAGES_PER_SCAN = 4


def _instahyre_search_location(config: dict[str, Any]) -> str:
    """Map profile location labels to Instahyre's accepted city names."""
    configured = config.get("locations", [])
    locations = configured if isinstance(configured, list) else []
    selected = next(
        (
            str(value).split(",")[0].strip()
            for value in locations
            if str(value).strip() and "remote" not in str(value).lower()
        ),
        "",
    )
    if not selected:
        selected = next(
            (str(value).split(",")[0].strip() for value in locations if str(value).strip()),
            "Bangalore",
        )
    if not selected:
        selected = "Bangalore"

    aliases = {
        "bengaluru": "Bangalore",
        "gurugram": "Gurgaon",
        "delhi": "Delhi / NCR",
        "remote": "Work From Home",
        "remote india": "Work From Home",
        "work from home": "Work From Home",
    }
    return aliases.get(selected.casefold(), selected)


def instahyre_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = "https://www.instahyre.com/api/v1/job_search/"
    location = _instahyre_search_location(config)
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    offset = 0

    for _page_number in range(INSTAHYRE_MAX_PAGES_PER_SCAN):
        params = {
            "jobLocations": location,
            "limit": INSTAHYRE_PAGE_SIZE,
            "offset": offset,
        }
        try:
            response = _tracked_source_get(
                "instahyre",
                endpoint,
                params=params,
                headers={**UA, "Referer": "https://www.instahyre.com/"},
                timeout=25,
            )
            response.raise_for_status()
            payload = response.json()
            next_page = None
            if isinstance(payload, list):
                items = payload
            elif isinstance(payload, dict):
                items = None
                for key in ("objects", "jobs", "jobDetails", "results", "data", "job_details"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        items = value
                        break
                meta = payload.get("meta")
                if isinstance(meta, dict):
                    next_page = meta.get("next")
                if items is None:
                    raise ValueError("Instahyre response did not contain a jobs list")
            else:
                raise ValueError("Instahyre response was not a jobs list or object")
        except Exception:
            _record_source_page("instahyre", False)
            raise

        _record_source_page("instahyre", True)
        for item in items:
            if not isinstance(item, dict):
                continue
            source_id = item.get("jobId") or item.get("id") or item.get("jobID")
            if not source_id:
                continue
            source_id = str(source_id)
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            employer = item.get("employer")
            employer_name = (
                employer.get("company_name") or employer.get("name") or ""
                if isinstance(employer, dict)
                else ""
            )
            url = str(
                item.get("public_url") or item.get("url") or item.get("publicUrl")
                or item.get("jobUrl")
                or f"https://www.instahyre.com/job-{source_id}-"
            )
            posted_raw = item.get("postedAt") or item.get("posted_at") or item.get("postedDate")
            posted_at = parse_relative(str(posted_raw)) if posted_raw else None

            raw_location = item.get("location") or item.get("locations") or ""
            if isinstance(raw_location, dict):
                job_location = str(raw_location.get("name") or "")
            elif isinstance(raw_location, list):
                job_location = ", ".join(str(value) for value in raw_location if value)
            else:
                job_location = str(raw_location)

            description = str(item.get("description") or item.get("descriptionText") or "")
            if not description:
                keywords = item.get("keywords")
                if isinstance(keywords, list):
                    keyword_values = [
                        str(value).strip()
                        for value in keywords
                        if isinstance(value, (str, int, float)) and str(value).strip()
                    ]
                    if keyword_values:
                        description = "Keywords: " + ", ".join(keyword_values)

            jobs.append(normalize_job(
                "instahyre",
                source_id,
                str(item.get("companyName") or item.get("company") or employer_name),
                str(item.get("title") or item.get("jobTitle") or item.get("candidate_title") or ""),
                job_location,
                url,
                posted_at,
                "minute" if posted_at else "unknown",
                description,
            ))

        if not items or not next_page:
            break
        next_offset = offset + INSTAHYRE_PAGE_SIZE
        if isinstance(next_page, str):
            match = re.search(r"(?:[?&])offset=(\d+)", next_page)
            if match:
                next_offset = int(match.group(1))
        if next_offset <= offset:
            break
        offset = next_offset

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
                source_details={"board_registry_id": board.get("registry_id")},
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
                    source_details={"board_registry_id": board.get("registry_id")},
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


def _lever_public_url(value: Any, *, site: str, instance: str, posting_id: str) -> str:
    """Accept only a Lever-hosted posting URL; derive its canonical public URL otherwise."""
    allowed_host = "jobs.eu.lever.co" if instance == "eu" else "jobs.lever.co"
    if isinstance(value, str) and value.strip():
        parsed = urlsplit(value.strip())
        expected_prefix = f"/{site}/"
        relative_path = unquote(parsed.path[len(expected_prefix):]) if parsed.path.startswith(expected_prefix) else ""
        path_segments = relative_path.split("/")
        if (
            parsed.scheme.lower() == "https"
            and parsed.hostname
            and parsed.hostname.lower() == allowed_host
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and bool(relative_path)
            and all(segment not in {"", ".", ".."} for segment in path_segments)
            and "\\" not in relative_path
            and parsed.query == ""
            and parsed.fragment == ""
        ):
            return value.strip()
    return f"https://{allowed_host}/{site}/{posting_id}"


def _normalize_lever_posting(
    item: dict[str, Any],
    *,
    site: str,
    company: str,
    instance: str,
    registry_id: int | None = None,
) -> dict[str, Any] | None:
    raw_id = item.get("id")
    title = item.get("text")
    if raw_id in (None, "") or not isinstance(title, str) or not title.strip():
        return None

    posting_id = str(raw_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", posting_id):
        return None
    source_id = f"lever-{instance}-{site}-{posting_id}"
    hosted_url = _lever_public_url(
        item.get("hostedUrl"),
        site=site,
        instance=instance,
        posting_id=posting_id,
    )

    categories = item.get("categories")
    if not isinstance(categories, dict):
        categories = {}
    locations = categories.get("allLocations")
    location_values = (
        [value.strip() for value in locations if isinstance(value, str) and value.strip()]
        if isinstance(locations, list)
        else []
    )
    primary_location = categories.get("location")
    location = (
        primary_location.strip()
        if isinstance(primary_location, str) and primary_location.strip()
        else ", ".join(dict.fromkeys(location_values))
    )

    plain_description = item.get("descriptionPlain")
    if isinstance(plain_description, str) and plain_description.strip():
        description = plain_description.strip()
    else:
        html_description = item.get("description") or item.get("descriptionBody")
        description = (
            BeautifulSoup(
                html_lib.unescape(html_description),
                "html.parser",
            ).get_text(" ", strip=True)
            if isinstance(html_description, str)
            else ""
        )

    extra_lines: list[str] = []
    for field, label in (
        ("team", "Team"),
        ("department", "Department"),
        ("commitment", "Commitment"),
        ("level", "Level"),
    ):
        value = categories.get(field)
        if isinstance(value, str) and value.strip():
            extra_lines.append(f"{label}: {value.strip()}")

    workplace_type = item.get("workplaceType")
    if isinstance(workplace_type, str) and workplace_type.strip():
        extra_lines.append(f"Workplace type: {workplace_type.strip()}")

    sections = item.get("lists")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_name = str(section.get("text") or "").strip()
            section_html = section.get("content")
            section_text = (
                BeautifulSoup(
                    html_lib.unescape(section_html),
                    "html.parser",
                ).get_text(" ", strip=True)
                if isinstance(section_html, str)
                else ""
            )
            if section_name or section_text:
                extra_lines.append(f"{section_name}: {section_text}".strip(": "))

    if extra_lines:
        description = "\n".join(part for part in (description, *extra_lines) if part)

    salary_range = item.get("salaryRange")
    source_details = {
        "lever_instance": instance,
        "lever_site": site,
        "board_registry_id": registry_id,
        "team": categories.get("team"),
        "department": categories.get("department"),
        "commitment": categories.get("commitment"),
        "level": categories.get("level"),
        "workplace_type": workplace_type if isinstance(workplace_type, str) else None,
        "salary_range": salary_range if isinstance(salary_range, dict) else None,
    }
    return normalize_job(
        "lever",
        source_id,
        company,
        title.strip(),
        location,
        hosted_url,
        None,
        "unknown",
        description,
        source_details=source_details,
    )


def lever_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect published postings from explicit Lever public-site allowlist entries.

    The public Postings API uses skip/limit pagination. No authentication or
    application endpoint is used. The v0 public field contract does not promise
    a trustworthy publication timestamp, so source_posted_at stays unknown.
    """
    boards = config.get("lever_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Lever is enabled but no public lever_boards are configured")
    if len(boards) > LEVER_MAX_BOARDS:
        raise RuntimeError("Lever board allowlist exceeds the configured safety limit")

    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []

    for board in boards:
        site = str(board.get("site") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        instance = str(board.get("instance") or "global").strip().lower() if isinstance(board, dict) else "global"
        if (
            not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", site)
            or not company
            or len(company) > 120
            or instance not in {"global", "eu"}
        ):
            _record_source_board("lever", False)
            failures.append(f"{site or '<missing-site>'}: invalid board configuration")
            continue

        api_host = "api.eu.lever.co" if instance == "eu" else "api.lever.co"
        endpoint = f"https://{api_host}/v0/postings/{site}"
        successful_pages = 0

        for page_number in range(LEVER_MAX_PAGES_PER_BOARD):
            try:
                response = _tracked_source_get(
                    "lever",
                    endpoint,
                    params={
                        "mode": "json",
                        "limit": LEVER_PAGE_SIZE,
                        "skip": page_number * LEVER_PAGE_SIZE,
                    },
                    headers={**UA, "Accept": "application/json"},
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ValueError("Lever response did not contain a postings list")
            except Exception as exc:
                _record_source_page("lever", False)
                failures.append(
                    f"{site} page {page_number + 1}: {type(exc).__name__}"
                )
                log.warning(
                    "lever: site=%s page=%s failed error_type=%s",
                    site,
                    page_number + 1,
                    type(exc).__name__,
                )
                break

            _record_source_page("lever", True)
            successful_pages += 1
            for item in payload:
                if not isinstance(item, dict):
                    continue
                job = _normalize_lever_posting(
                    item,
                    site=site,
                    company=company,
                    instance=instance,
                    registry_id=board.get("registry_id"),
                )
                if job and job["source_job_id"] not in seen_ids:
                    seen_ids.add(job["source_job_id"])
                    jobs.append(job)

            if len(payload) < LEVER_PAGE_SIZE:
                break
            if page_number == LEVER_MAX_PAGES_PER_BOARD - 1:
                log.warning(
                    "lever: site=%s reached bounded pagination cap pages=%s page_size=%s",
                    site,
                    LEVER_MAX_PAGES_PER_BOARD,
                    LEVER_PAGE_SIZE,
                )

        if successful_pages:
            successful_boards += 1
            _record_source_board("lever", True)
        else:
            _record_source_board("lever", False)

    if successful_boards == 0:
        details = "; ".join(failures) or "no valid boards configured"
        raise RuntimeError(f"All configured Lever boards failed: {details}")
    if failures:
        log.warning(
            "lever: partial board/page failures=%s successful_boards=%s",
            len(failures),
            successful_boards,
        )
    log.info(
        "lever: boards=%s successful=%s failed=%s jobs=%s timestamped=0 pages_cap=%s",
        len(boards),
        successful_boards,
        len(failures),
        len(jobs),
        LEVER_MAX_PAGES_PER_BOARD,
    )
    return jobs


def _workday_get_board_poll_state(board_key: str) -> dict[str, Any]:
    with connect_sqlite(DB_PATH) as conn:
        row = conn.execute(
            """SELECT next_inventory_offset,last_inventory_attempt_at,
                      last_full_inventory_at,reported_total,facets_json,
                      inventory_complete,truncated_reason,facet_queue_json,
                      active_facets_json,active_facet_depth,active_facet_query,
                      facet_partition_started
               FROM workday_board_poll_state WHERE board_key=?""",
            (board_key,),
        ).fetchone()
    if not row:
        return {
            "next_inventory_offset": WORKDAY_PAGE_SIZE,
            "last_inventory_attempt_at": None,
            "last_full_inventory_at": None,
            "reported_total": None,
            "facets": [],
            "inventory_complete": False,
            "truncated_reason": None,
            "facet_queue": [],
            "active_facets": {},
            "active_facet_depth": 0,
            "active_facet_query": False,
            "facet_partition_started": False,
        }
    try:
        facets = json.loads(row[4] or "[]")
        if not isinstance(facets, (list, dict)):
            facets = []
    except (TypeError, ValueError):
        facets = []
    try:
        facet_queue = json.loads(row[7] or "[]")
        if not isinstance(facet_queue, list):
            facet_queue = []
    except (TypeError, ValueError):
        facet_queue = []
    try:
        active_facets = json.loads(row[8] or "{}")
        if not isinstance(active_facets, dict):
            active_facets = {}
    except (TypeError, ValueError):
        active_facets = {}
    return {
        "next_inventory_offset": max(0, int(row[0] or 0)),
        "last_inventory_attempt_at": row[1],
        "last_full_inventory_at": row[2],
        "reported_total": row[3],
        "facets": facets,
        "inventory_complete": bool(row[5]),
        "truncated_reason": row[6],
        "facet_queue": facet_queue,
        "active_facets": active_facets,
        "active_facet_depth": max(0, int(row[9] or 0)),
        "active_facet_query": bool(row[10]),
        "facet_partition_started": bool(row[11]),
    }


def _workday_set_board_poll_state(board_key: str, state: dict[str, Any]) -> None:
    facets = state.get("facets")
    if not isinstance(facets, (list, dict)):
        facets = []
    facets_json = json.dumps(facets, ensure_ascii=False, separators=(",", ":"))[:16_000]
    facet_queue = state.get("facet_queue")
    if not isinstance(facet_queue, list):
        facet_queue = []
    facet_queue_json = json.dumps(facet_queue[:WORKDAY_MAX_FACET_PARTITIONS], ensure_ascii=False, separators=(",", ":"))
    if len(facet_queue_json) > 1_000_000:
        raise ValueError("Workday facet queue exceeded the persisted state size limit")
    active_facets = state.get("active_facets")
    if not isinstance(active_facets, dict):
        active_facets = {}
    active_facets_json = json.dumps(active_facets, ensure_ascii=False, separators=(",", ":"))[:16_000]
    reported_total = state.get("reported_total")
    if isinstance(reported_total, bool) or not isinstance(reported_total, int) or reported_total < 0:
        reported_total = None
    next_offset = state.get("next_inventory_offset", WORKDAY_PAGE_SIZE)
    if isinstance(next_offset, bool) or not isinstance(next_offset, int) or next_offset < 0:
        next_offset = WORKDAY_PAGE_SIZE
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO workday_board_poll_state(
                   board_key,next_inventory_offset,last_inventory_attempt_at,
                   last_full_inventory_at,reported_total,facets_json,
                   inventory_complete,truncated_reason,facet_queue_json,
                   active_facets_json,active_facet_depth,active_facet_query,
                   facet_partition_started,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(board_key) DO UPDATE SET
                   next_inventory_offset=excluded.next_inventory_offset,
                   last_inventory_attempt_at=excluded.last_inventory_attempt_at,
                   last_full_inventory_at=excluded.last_full_inventory_at,
                   reported_total=excluded.reported_total,
                   facets_json=excluded.facets_json,
                   inventory_complete=excluded.inventory_complete,
                   truncated_reason=excluded.truncated_reason,
                   facet_queue_json=excluded.facet_queue_json,
                   active_facets_json=excluded.active_facets_json,
                   active_facet_depth=excluded.active_facet_depth,
                   active_facet_query=excluded.active_facet_query,
                   facet_partition_started=excluded.facet_partition_started,
                   updated_at=excluded.updated_at""",
            (
                board_key, next_offset, state.get("last_inventory_attempt_at"),
                state.get("last_full_inventory_at"), reported_total, facets_json,
                int(bool(state.get("inventory_complete"))),
                state.get("truncated_reason"), facet_queue_json, active_facets_json,
                max(0, min(int(state.get("active_facet_depth") or 0), WORKDAY_MAX_FACET_DEPTH)),
                int(bool(state.get("active_facet_query"))),
                int(bool(state.get("facet_partition_started"))), iso(now()),
            ),
        )
        conn.commit()


def _workday_commit_pending_board_states() -> None:
    pending = source_state.setdefault("workday", {}).pop("pending_board_states", {})
    if not isinstance(pending, dict):
        return
    for board_key, state in pending.items():
        if isinstance(board_key, str) and isinstance(state, dict):
            _workday_set_board_poll_state(board_key, state)


def _workday_pick_subdivision_facet(
    facets: Any, *, already_applied: set[str]
) -> tuple[str, list[tuple[str, int]]] | None:
    """Choose a Workday subdivision facet from the public response metadata."""
    if not isinstance(facets, list):
        return None
    by_param: dict[str, list[tuple[str, int]]] = {}
    for facet in facets[:100]:
        if not isinstance(facet, dict):
            continue
        param = facet.get("facetParameter")
        values = facet.get("values")
        if (
            not isinstance(param, str) or param not in WORKDAY_SUBDIVISION_FACETS
            or param in already_applied or not isinstance(values, list)
        ):
            continue
        seen: set[str] = set()
        items: list[tuple[str, int]] = []
        for value in values[:WORKDAY_MAX_FACET_PARTITIONS]:
            if not isinstance(value, dict):
                continue
            value_id = value.get("id")
            count = value.get("count")
            if isinstance(count, bool):
                continue
            try:
                parsed_count = int(count)
            except (TypeError, ValueError, OverflowError):
                continue
            if (
                not isinstance(value_id, str) or not value_id.strip()
                or len(value_id) > 200 or value_id in seen or parsed_count <= 0
            ):
                continue
            seen.add(value_id)
            items.append((value_id, parsed_count))
        if len(items) > 1:
            by_param[param] = items
    for preferred in WORKDAY_SUBDIVISION_FACETS:
        if preferred in by_param:
            return preferred, by_param[preferred]
    if by_param:
        return max(by_param.items(), key=lambda entry: len(entry[1]))
    return None


def _workday_facet_children(
    applied_facets: dict[str, list[str]], depth: int, facets: Any,
    queue_size: int,
) -> tuple[list[dict[str, Any]], str | None]:
    """Build bounded child queries for one capped Workday query."""
    if depth >= WORKDAY_MAX_FACET_DEPTH:
        return [], "workday_facet_depth_limit_reached"
    selected = _workday_pick_subdivision_facet(
        facets, already_applied=set(applied_facets)
    )
    if selected is None:
        return [], "workday_no_usable_subdivision_facet"
    param, values = selected
    remaining = WORKDAY_MAX_FACET_PARTITIONS - queue_size
    if remaining <= 0:
        return [], "workday_facet_partition_budget_reached"
    children = [
        {"applied_facets": {**applied_facets, param: [value_id]}, "depth": depth + 1}
        for value_id, _count in values[:remaining]
    ]
    overflow_reason = (
        "workday_facet_partition_budget_reached"
        if len(children) < len(values) else None
    )
    return children, overflow_reason


def _workday_inventory_is_due(state: dict[str, Any], current: dt.datetime) -> bool:
    if state.get("truncated_reason") and not state.get("facet_queue") and not state.get("active_facet_query"):
        return False
    last_attempt = state.get("last_inventory_attempt_at")
    if state.get("inventory_complete"):
        last_full = state.get("last_full_inventory_at")
        if not last_full:
            return False
        try:
            parsed = dt.datetime.fromisoformat(str(last_full).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
        except ValueError:
            parsed = current - dt.timedelta(seconds=WORKDAY_FULL_INVENTORY_REFRESH_SECONDS)
        return (current - parsed).total_seconds() >= WORKDAY_FULL_INVENTORY_REFRESH_SECONDS
    if not last_attempt:
        return True
    try:
        parsed = dt.datetime.fromisoformat(str(last_attempt).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
    except ValueError:
        return True
    return (current - parsed).total_seconds() >= WORKDAY_INVENTORY_PAGE_INTERVAL_SECONDS


def workday_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect a bounded set of public Workday career-site postings.

    This uses the public candidate career-site CXS interface, not the authenticated
    Workday REST API. Boards must be explicitly allowlisted by real career URL.
    The first page is polled frequently; pagination and detail calls are bounded.
    """
    boards = config.get("workday_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Workday is enabled but no public workday_boards are configured")
    if len(boards) > WORKDAY_MAX_BOARDS:
        raise RuntimeError("Workday board allowlist exceeds the configured safety limit")

    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []
    headers = {**UA, "Accept": "application/json", "Content-Type": "application/json"}

    for board in boards:
        parsed_board = _parse_workday_board_url(
            board.get("url") if isinstance(board, dict) else None
        )
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        if not parsed_board or not company:
            _record_source_board("workday", False)
            failures.append("invalid Workday public board configuration")
            continue

        host = parsed_board["host"]
        tenant = parsed_board["tenant"]
        site = parsed_board["site"]
        board_url = parsed_board["url"]
        list_endpoint = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        successful_pages = 0
        details_attempted = 0
        details_fetched = 0
        board_jobs: list[dict[str, Any]] = []
        rate_limited = False
        board_key = f"{tenant}:{site}"
        poll_state = _workday_get_board_poll_state(board_key)
        inventory_due = _workday_inventory_is_due(poll_state, now())
        inventory_offset = int(poll_state.get("next_inventory_offset") or 0)
        facet_queue = list(poll_state.get("facet_queue") or [])
        active_facets = dict(poll_state.get("active_facets") or {})
        active_facet_depth = int(poll_state.get("active_facet_depth") or 0)
        active_facet_query = bool(poll_state.get("active_facet_query"))
        facet_partition_started = bool(poll_state.get("facet_partition_started"))
        if poll_state.get("inventory_complete") and inventory_due:
            # Weekly refresh starts a new root sweep; the freshness request below
            # will decide whether it remains linear or needs facet partitions.
            inventory_offset = WORKDAY_PAGE_SIZE
            facet_queue = []
            active_facets = {}
            active_facet_depth = 0
            active_facet_query = False
            facet_partition_started = False
            poll_state = {
                **poll_state,
                "inventory_complete": False,
                "truncated_reason": None,
                "facet_queue": [],
                "active_facets": {},
                "active_facet_depth": 0,
                "active_facet_query": False,
                "facet_partition_started": False,
            }
        # Resume a queued partition only when its throttle window is due.
        if inventory_due and facet_partition_started and not active_facet_query and facet_queue:
            task = facet_queue.pop(0)
            task_filters = task.get("applied_facets") if isinstance(task, dict) else None
            task_depth = task.get("depth") if isinstance(task, dict) else None
            if isinstance(task_filters, dict) and all(
                isinstance(key, str) and isinstance(value, list)
                and all(isinstance(item, str) for item in value)
                for key, value in task_filters.items()
            ):
                active_facets = task_filters
                active_facet_depth = max(1, min(int(task_depth or 1), WORKDAY_MAX_FACET_DEPTH))
                active_facet_query = True
                inventory_offset = 0
            else:
                poll_state = {**poll_state, "truncated_reason": "workday_invalid_facet_queue_entry"}
        page_specs = [(0, True, {})]
        inventory_spec_added = False
        if inventory_due and active_facet_query and WORKDAY_MAX_PAGES_PER_BOARD > 1:
            page_specs.append((inventory_offset, False, active_facets))
            inventory_spec_added = True
        reported_total = poll_state.get("reported_total")
        facets = poll_state.get("facets", [])
        inventory_state_update: dict[str, Any] | None = None
        inventory_attempt_at = iso(now()) or ""

        for page_number, (offset, freshness_page, request_facets) in enumerate(page_specs):
            payload = {
                "appliedFacets": request_facets,
                "limit": WORKDAY_PAGE_SIZE,
                "offset": offset,
                "searchText": "",
            }
            try:
                response = _tracked_source_post(
                    "workday", list_endpoint, json_body=payload, headers=headers, timeout=20
                )
                response.raise_for_status()
                data = response.json()
                postings = data.get("jobPostings") if isinstance(data, dict) else None
                if not isinstance(postings, list):
                    raise ValueError("Workday response did not contain jobPostings")
                if isinstance(data, dict):
                    raw_total = data.get("total")
                    if isinstance(raw_total, int) and not isinstance(raw_total, bool) and raw_total >= 0:
                        reported_total = raw_total
                    raw_facets = data.get("facets")
                    if isinstance(raw_facets, list):
                        facets = raw_facets[:100]
                    elif isinstance(raw_facets, dict):
                        facets = dict(list(raw_facets.items())[:100])
                successful_pages += 1
                _record_source_page("workday", True)

                if freshness_page and inventory_due and not facet_partition_started:
                    if reported_total == WORKDAY_INVENTORY_MAX_OFFSET:
                        children, partition_error = _workday_facet_children(
                            {}, 0, facets, len(facet_queue)
                        )
                        if children:
                            facet_queue.extend(children)
                            facet_partition_started = True
                            active_facets = {}
                            active_facet_depth = 0
                            active_facet_query = False
                            inventory_offset = 0
                            inventory_state_update = {
                                **poll_state,
                                "next_inventory_offset": 0,
                                "last_inventory_attempt_at": inventory_attempt_at,
                                "reported_total": reported_total,
                                "facets": facets,
                                "facet_queue": facet_queue,
                                "active_facets": {},
                                "active_facet_depth": 0,
                                "active_facet_query": False,
                                "facet_partition_started": True,
                                "inventory_complete": False,
                                "truncated_reason": partition_error,
                            }
                            log.info(
                                "workday: tenant=%s site=%s capped total=%s; queued %s facet partitions",
                                tenant, site, reported_total, len(facet_queue),
                            )
                            # Do not waste this cycle paginating the capped root
                            # query. The next scheduled inventory request starts
                            # at the first child partition.
                            inventory_spec_added = True
                        elif partition_error:
                            log.warning(
                                "workday: tenant=%s site=%s cannot subdivide capped root query reason=%s",
                                tenant, site, partition_error,
                            )
                    if (
                        not inventory_spec_added
                        and not facet_partition_started
                        and WORKDAY_MAX_PAGES_PER_BOARD > 1
                    ):
                        page_specs.append((max(WORKDAY_PAGE_SIZE, inventory_offset), False, {}))
                        inventory_spec_added = True
            except Exception as exc:
                _record_source_page("workday", False)
                failed_response = getattr(exc, "response", None)
                if not freshness_page:
                    # Failed inventory pages are throttled too. Keep the offset
                    # unchanged so the page is retried after the inventory cadence.
                    inventory_state_update = {
                        **poll_state,
                        "next_inventory_offset": inventory_offset,
                        "last_inventory_attempt_at": inventory_attempt_at,
                        "reported_total": reported_total,
                        "facets": facets,
                        "facet_queue": facet_queue,
                        "active_facets": active_facets,
                        "active_facet_depth": active_facet_depth,
                        "active_facet_query": active_facet_query,
                        "facet_partition_started": facet_partition_started,
                    }
                if getattr(failed_response, "status_code", None) == 429:
                    _set_workday_rate_limit(failed_response)
                    rate_limited = True
                    failures.append(f"{tenant}/{site} list rate limited")
                else:
                    failures.append(
                        f"{tenant}/{site} page offset {offset}: {type(exc).__name__}"
                    )
                log.warning(
                    "workday: tenant=%s site=%s page=%s failed error_type=%s",
                    tenant, site, page_number + 1, type(exc).__name__,
                )
                break

            for item in postings:
                if not isinstance(item, dict):
                    continue
                title = item.get("title")
                external_path = item.get("externalPath")
                if not isinstance(title, str) or not title.strip():
                    continue
                if not isinstance(external_path, str) or not external_path.startswith("/job/"):
                    continue
                try:
                    parsed_path = urlsplit(external_path)
                except ValueError:
                    continue
                if (
                    parsed_path.scheme or parsed_path.netloc or parsed_path.query
                    or parsed_path.fragment or parsed_path.path != external_path
                    or external_path.startswith("//") or "\\" in external_path
                    or any(part in {".", ".."} for part in external_path.split("/"))
                ):
                    continue

                bullet_fields = item.get("bulletFields")
                safe_bullet_fields = (
                    [str(value).strip() for value in bullet_fields
                     if isinstance(value, (str, int)) and str(value).strip()][:10]
                    if isinstance(bullet_fields, list) else []
                )

                detail_info: dict[str, Any] = {}
                # Detail retrieval does not depend on the administrator's role or
                # location filters; per-user evaluation happens after ingestion.
                if freshness_page and details_attempted < WORKDAY_MAX_DETAILS_PER_BOARD:
                    try:
                        if details_attempted:
                            time.sleep(WORKDAY_DETAIL_DELAY_SECONDS)
                        details_attempted += 1
                        detail_response = _tracked_source_get(
                            "workday",
                            f"https://{host}/wday/cxs/{tenant}/{site}{external_path}",
                            headers={**UA, "Accept": "application/json"},
                            timeout=20,
                        )
                        detail_response.raise_for_status()
                        detail_payload = detail_response.json()
                        candidate_info = (
                            detail_payload.get("jobPostingInfo")
                            if isinstance(detail_payload, dict) else None
                        )
                        if isinstance(candidate_info, dict):
                            detail_info = candidate_info
                        details_fetched += 1
                    except Exception as exc:
                        status_code = getattr(getattr(exc, "response", None), "status_code", None)
                        log.warning(
                            "workday: tenant=%s site=%s detail failed status=%s error_type=%s",
                            tenant, site, status_code, type(exc).__name__,
                        )
                        if status_code == 429:
                            _set_workday_rate_limit(exc.response)
                            rate_limited = True
                            failures.append(f"{tenant}/{site} detail rate limited")
                            break

                raw_requisition_id = (
                    detail_info.get("jobReqId")
                    or (safe_bullet_fields[0] if safe_bullet_fields else None)
                    or detail_info.get("jobPostingId")
                    or detail_info.get("id")
                    or external_path.rsplit("/", 1)[-1]
                )
                requisition_id = re.sub(
                    r"[^A-Za-z0-9_-]+", "-", str(raw_requisition_id)
                ).strip("-_")
                if not requisition_id:
                    continue
                source_id = f"workday-{tenant}-{site}-{requisition_id}"
                if source_id in seen_ids:
                    continue
                seen_ids.add(source_id)

                locations: list[str] = []
                primary_location = (
                    detail_info.get("location")
                    or detail_info.get("jobRequisitionLocation")
                    or (safe_bullet_fields[1] if len(safe_bullet_fields) > 1 else None)
                    or item.get("locationsText")
                )
                if isinstance(primary_location, dict):
                    primary_location = (
                        primary_location.get("descriptor")
                        or primary_location.get("name")
                    )
                if isinstance(primary_location, str) and primary_location.strip():
                    locations.append(primary_location.strip())
                extra_locations = detail_info.get("additionalLocations")
                if isinstance(extra_locations, list):
                    locations.extend(
                        value.strip() for value in extra_locations
                        if isinstance(value, str) and value.strip()
                    )
                location = ", ".join(dict.fromkeys(locations))

                raw_description = detail_info.get("jobDescription")
                description = (
                    BeautifulSoup(
                        html_lib.unescape(raw_description), "html.parser"
                    ).get_text(" ", strip=True)
                    if isinstance(raw_description, str) else ""
                )
                details = {
                    "workday_tenant": tenant,
                    "workday_cluster": parsed_board["cluster"],
                    "workday_site": site,
                    "board_registry_id": board.get("registry_id"),
                    "requisition_id": requisition_id,
                    "job_posting_id": detail_info.get("jobPostingId"),
                    "posted_on_label": item.get("postedOn") or detail_info.get("postedOn"),
                    "locations_text": item.get("locationsText"),
                    "employment_type": detail_info.get("timeType"),
                    "start_date": detail_info.get("startDate"),
                    "additional_locations": (
                        extra_locations if isinstance(extra_locations, list) else []
                    ),
                    "details_fetched": bool(detail_info),
                    "listing_bullet_fields": safe_bullet_fields,
                }
                board_jobs.append(normalize_job(
                    "workday",
                    source_id,
                    company,
                    str(detail_info.get("title") or title).strip(),
                    location,
                    board_url + external_path,
                    None,
                    "unknown",
                    description,
                    source_details=details,
                ))

            if not freshness_page:
                next_offset = offset + WORKDAY_PAGE_SIZE
                truncated_reason = poll_state.get("truncated_reason")
                inventory_complete = False
                last_full_inventory_at = poll_state.get("last_full_inventory_at")
                next_active = active_facet_query
                next_active_facets = active_facets
                next_active_depth = active_facet_depth
                next_partition_started = facet_partition_started
                next_queue = list(facet_queue)

                # A capped filtered query may be subdivided again using a
                # different facet. Keep the request budget bounded: one page
                # every 15 minutes, no fan-out.
                if (
                    reported_total == WORKDAY_INVENTORY_MAX_OFFSET
                    and next_active
                ):
                    children, partition_error = _workday_facet_children(
                        next_active_facets,
                        next_active_depth,
                        facets,
                        len(next_queue),
                    )
                    if children:
                        next_queue.extend(children)
                        next_active = False
                        next_active_facets = {}
                        next_active_depth = 0
                        next_offset = 0
                        if partition_error:
                            truncated_reason = partition_error
                        log.info(
                            "workday: tenant=%s site=%s query facets=%s capped; queued %s child partitions",
                            tenant, site, sorted(active_facets), len(children),
                        )
                    elif partition_error:
                        truncated_reason = partition_error
                        # No more safe facets are available. Continue this leaf
                        # query to its 2,000-result ceiling, then leave the
                        # board explicitly truncated.
                        if offset >= WORKDAY_INVENTORY_MAX_OFFSET - WORKDAY_PAGE_SIZE:
                            next_active = False
                            next_offset = 0
                        else:
                            next_offset = offset + WORKDAY_PAGE_SIZE

                elif (
                    not next_partition_started
                    and reported_total == WORKDAY_INVENTORY_MAX_OFFSET
                    and not next_active
                ):
                    # Root query had no usable facets. An empty page before the
                    # reported cap is inconsistent and should stop conservatively.
                    if len(postings) < WORKDAY_PAGE_SIZE:
                        truncated_reason = truncated_reason or "empty_page_before_reported_total_cap_requires_review"
                        next_offset = 0
                    elif offset >= WORKDAY_INVENTORY_MAX_OFFSET - WORKDAY_PAGE_SIZE:
                        truncated_reason = truncated_reason or "workday_no_usable_subdivision_facet"
                        next_offset = 0
                    else:
                        next_offset = offset + WORKDAY_PAGE_SIZE

                elif len(postings) < WORKDAY_PAGE_SIZE:
                    if next_active:
                        next_active = False
                        next_active_facets = {}
                        next_active_depth = 0
                        next_offset = 0
                    elif not next_partition_started:
                        next_offset = 0
                        inventory_complete = True
                        last_full_inventory_at = inventory_attempt_at
                    else:
                        next_offset = 0

                elif isinstance(reported_total, int) and reported_total < WORKDAY_INVENTORY_MAX_OFFSET and next_offset >= reported_total:
                    if next_active:
                        next_active = False
                        next_active_facets = {}
                        next_active_depth = 0
                    elif not next_partition_started:
                        inventory_complete = True
                        last_full_inventory_at = inventory_attempt_at
                    next_offset = 0

                elif (
                    not next_partition_started
                    and isinstance(reported_total, int)
                    and reported_total < WORKDAY_INVENTORY_MAX_OFFSET
                    and next_offset < reported_total
                ):
                    # Continue the ordinary unfiltered inventory query.
                    pass

                elif next_offset >= WORKDAY_INVENTORY_MAX_OFFSET:
                    truncated_reason = truncated_reason or "inventory_safety_offset_cap_reached"
                    next_offset = 0
                    next_active = False
                    next_active_facets = {}
                    next_active_depth = 0

                # If the last facet task completed successfully, mark the
                # overall sweep complete. A prior truncation always wins.
                if next_partition_started and not next_active and not next_queue:
                    if not truncated_reason:
                        inventory_complete = True
                        last_full_inventory_at = inventory_attempt_at
                    next_partition_started = False if inventory_complete else True

                inventory_state_update = {
                    **poll_state,
                    "next_inventory_offset": next_offset,
                    "last_inventory_attempt_at": inventory_attempt_at,
                    "last_full_inventory_at": last_full_inventory_at,
                    "reported_total": reported_total,
                    "facets": facets,
                    "inventory_complete": inventory_complete,
                    "truncated_reason": truncated_reason,
                    "facet_queue": next_queue,
                    "active_facets": next_active_facets,
                    "active_facet_depth": next_active_depth,
                    "active_facet_query": next_active,
                    "facet_partition_started": next_partition_started,
                }
                if truncated_reason:
                    log.warning(
                        "workday: tenant=%s site=%s inventory incomplete offset=%s total=%s reason=%s",
                        tenant, site, offset, reported_total, truncated_reason,
                    )
                elif inventory_complete:
                    log.info(
                        "workday: tenant=%s site=%s inventory sweep complete reported_total=%s",
                        tenant, site, reported_total,
                    )
            if rate_limited:
                break

        if inventory_state_update is not None:
            source_state.setdefault("workday", {}).setdefault("pending_board_states", {})[board_key] = inventory_state_update

        if successful_pages:
            successful_boards += 1
            _record_source_board("workday", True)
            jobs.extend(board_jobs)
        else:
            _record_source_board("workday", False)
        if rate_limited:
            break

    if successful_boards == 0:
        details = "; ".join(failures) or "no valid boards configured"
        raise RuntimeError(f"All configured Workday boards failed: {details}")
    if failures:
        log.warning(
            "workday: partial board/page failures=%s successful_boards=%s",
            len(failures), successful_boards,
        )
    log.info(
        "workday: boards=%s successful=%s failed=%s jobs=%s detail_attempt_cap_per_board=%s",
        len(boards), successful_boards, len(failures), len(jobs),
        WORKDAY_MAX_DETAILS_PER_BOARD,
    )
    return jobs


def smartrecruiters_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect active PUBLIC SmartRecruiters postings with bounded detail lookups."""
    boards = config.get("smartrecruiters_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("SmartRecruiters is enabled but no smartrecruiters_boards are configured")
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []
    headers = {**UA, "Accept": "application/json"}
    for board in boards:
        identifier = str(board.get("company_identifier") or board.get("identifier") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", identifier) or not company:
            _record_source_board("smartrecruiters", False)
            failures.append("invalid SmartRecruiters board configuration")
            continue
        endpoint = f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
        board_jobs: list[dict[str, Any]] = []
        pages_succeeded = 0
        detail_attempts = 0
        total_found = None
        rate_limited = False
        for page_number in range(SMARTRECRUITERS_MAX_PAGES_PER_BOARD):
            offset = page_number * SMARTRECRUITERS_PAGE_SIZE
            try:
                response = _tracked_source_get(
                    "smartrecruiters", endpoint,
                    params={"limit": SMARTRECRUITERS_PAGE_SIZE, "offset": offset, "destination": "PUBLIC"},
                    headers=headers, timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload.get("content") if isinstance(payload, dict) else None
                if not isinstance(content, list):
                    raise ValueError("SmartRecruiters response did not contain a content list")
                total_found = payload.get("totalFound")
                pages_succeeded += 1
                _record_source_page("smartrecruiters", True)
            except Exception as exc:
                _record_source_page("smartrecruiters", False)
                failed_response = getattr(exc, "response", None)
                if getattr(failed_response, "status_code", None) == 429:
                    _set_source_rate_limit("smartrecruiters", failed_response)
                    rate_limited = True
                failures.append(f"{identifier} page {page_number + 1}: {type(exc).__name__}")
                log.warning("smartrecruiters: identifier=%s page=%s failed error_type=%s", identifier, page_number + 1, type(exc).__name__)
                break

            for item in content:
                if not isinstance(item, dict):
                    continue
                raw_id = item.get("id")
                title = str(item.get("name") or "").strip()
                if raw_id in (None, "") or not title:
                    continue
                source_id = f"smartrecruiters-{identifier}-{raw_id}"
                if source_id in seen_ids:
                    continue
                seen_ids.add(source_id)

                raw_location = item.get("location") if isinstance(item.get("location"), dict) else {}
                location_parts = [
                    str(raw_location.get(field) or "").strip()
                    for field in ("city", "region", "country")
                    if str(raw_location.get(field) or "").strip()
                ]
                location = str(raw_location.get("fullLocation") or ", ".join(location_parts)).strip()
                if raw_location.get("remote"):
                    location = f"{location} (Remote)".strip()
                elif raw_location.get("hybrid"):
                    location = f"{location} (Hybrid)".strip()
                published_raw = item.get("releasedDate")
                published_at = parse_relative(published_raw) if isinstance(published_raw, str) else None
                precision = "minute" if published_at and re.search(r"\d{2}:\d{2}", str(published_raw)) else "date" if published_at else "unknown"

                detail: dict[str, Any] = {}
                if detail_attempts < SMARTRECRUITERS_MAX_DETAILS_PER_BOARD:
                    try:
                        if detail_attempts:
                            time.sleep(SMARTRECRUITERS_DETAIL_DELAY_SECONDS)
                        detail_attempts += 1
                        detail_response = _tracked_source_get(
                            "smartrecruiters", f"{endpoint}/{raw_id}",
                            headers=headers, timeout=20,
                        )
                        detail_response.raise_for_status()
                        detail_payload = detail_response.json()
                        if isinstance(detail_payload, dict):
                            detail = detail_payload
                    except Exception as exc:
                        failed_response = getattr(exc, "response", None)
                        if getattr(failed_response, "status_code", None) == 429:
                            _set_source_rate_limit("smartrecruiters", failed_response)
                            rate_limited = True
                            failures.append(f"{identifier} detail rate limited")
                        log.warning("smartrecruiters: identifier=%s detail failed error_type=%s", identifier, type(exc).__name__)

                sections = (((detail.get("jobAd") or {}).get("sections")) if isinstance(detail.get("jobAd"), dict) else {})
                description_parts = []
                if isinstance(sections, dict):
                    for key in ("jobDescription", "qualifications", "additionalInformation", "companyDescription"):
                        value = sections.get(key)
                        text_value = value.get("text") if isinstance(value, dict) else None
                        if isinstance(text_value, str) and text_value.strip():
                            description_parts.append(BeautifulSoup(html_lib.unescape(text_value), "html.parser").get_text(" ", strip=True))
                description = " ".join(part for part in description_parts if part)
                department = (item.get("department") or {}).get("label") if isinstance(item.get("department"), dict) else None
                function = (item.get("function") or {}).get("label") if isinstance(item.get("function"), dict) else None
                employment_type = (item.get("typeOfEmployment") or {}).get("label") if isinstance(item.get("typeOfEmployment"), dict) else None
                experience_level = (item.get("experienceLevel") or {}).get("label") if isinstance(item.get("experienceLevel"), dict) else None
                posting_url = detail.get("postingUrl") or item.get("postingUrl") or detail.get("applyUrl") or item.get("applyUrl")
                if not isinstance(posting_url, str) or not posting_url.startswith("https://"):
                    posting_url = f"https://jobs.smartrecruiters.com/{identifier}/{raw_id}"
                details = {
                    "company_identifier": identifier, "posting_id": str(raw_id),
                    "board_registry_id": board.get("registry_id"),
                    "job_ad_id": item.get("jobAdId"), "ref_number": item.get("refNumber"),
                    "department": department, "function": function,
                    "employment_type": employment_type, "experience_level": experience_level,
                    "details_fetched": bool(detail),
                }
                board_jobs.append(normalize_job(
                    "smartrecruiters", source_id,
                    str((item.get("company") or {}).get("name") if isinstance(item.get("company"), dict) else "") or company,
                    title, location, posting_url, published_at, precision, description,
                    source_details=details,
                ))
                if rate_limited:
                    break

            if rate_limited or len(content) < SMARTRECRUITERS_PAGE_SIZE:
                break
            if total_found is not None and offset + len(content) >= int(total_found):
                break
        if pages_succeeded:
            successful_boards += 1
            _record_source_board("smartrecruiters", True)
            jobs.extend(board_jobs)
        else:
            _record_source_board("smartrecruiters", False)
        if rate_limited:
            break
    if successful_boards == 0:
        raise RuntimeError("All configured SmartRecruiters boards failed: " + "; ".join(failures))
    if failures:
        log.warning("smartrecruiters: partial failures=%s successful_boards=%s", len(failures), successful_boards)
    log.info("smartrecruiters: boards=%s successful=%s failed=%s jobs=%s", len(boards), successful_boards, len(failures), len(jobs))
    return jobs


def workable_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect a public Workable account's published job widget (details included)."""
    boards = config.get("workable_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Workable is enabled but no workable_boards are configured")
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []
    for board in boards:
        account = str(board.get("account") or board.get("subdomain") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        if not re.fullmatch(r"[A-Za-z0-9-]{1,100}", account) or not company:
            _record_source_board("workable", False)
            failures.append("invalid Workable board configuration")
            continue
        endpoint = f"https://apply.workable.com/api/v1/widget/accounts/{account}"
        try:
            response = _tracked_source_get(
                "workable", endpoint, params={"details": "true"},
                headers={**UA, "Accept": "application/json"}, timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            postings = payload.get("jobs") if isinstance(payload, dict) else None
            if not isinstance(postings, list):
                raise ValueError("Workable response did not contain a jobs list")
            _record_source_page("workable", True)
            _record_source_board("workable", True)
            successful_boards += 1
        except Exception as exc:
            _record_source_page("workable", False)
            _record_source_board("workable", False)
            failed_response = getattr(exc, "response", None)
            if getattr(failed_response, "status_code", None) == 429:
                _set_source_rate_limit("workable", failed_response)
            failures.append(f"{account}: {type(exc).__name__}")
            log.warning("workable: account=%s failed error_type=%s", account, type(exc).__name__)
            if _source_cooldown_remaining("workable") > 0:
                break
            continue
        if len(postings) > WORKABLE_MAX_JOBS_PER_BOARD:
            log.warning("workable: account=%s returned %s jobs; processing first %s under the request budget", account, len(postings), WORKABLE_MAX_JOBS_PER_BOARD)
        for item in postings[:WORKABLE_MAX_JOBS_PER_BOARD]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            shortcode = str(item.get("shortcode") or item.get("code") or "").strip()
            if not title or not shortcode:
                continue
            source_id = f"workable-{account}-{shortcode}"
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            locations: list[str] = []
            raw_locations = item.get("locations")
            if isinstance(raw_locations, list):
                for value in raw_locations:
                    if not isinstance(value, dict):
                        continue
                    parts = [str(value.get(k) or "").strip() for k in ("city", "region", "country") if str(value.get(k) or "").strip()]
                    label = ", ".join(parts)
                    if label and label not in locations:
                        locations.append(label)
            if not locations:
                parts = [str(item.get(k) or "").strip() for k in ("city", "state", "country") if str(item.get(k) or "").strip()]
                if parts:
                    locations.append(", ".join(parts))
            workplace = str(item.get("workplace_type") or "").strip().lower()
            if not workplace and item.get("telecommuting"):
                workplace = "remote"
            location = ", ".join(locations)
            if workplace in {"remote", "hybrid", "on_site"}:
                location = f"{location} ({'On-site' if workplace == 'on_site' else workplace.title()})".strip()
            published_raw = item.get("published_on")
            published_at = parse_relative(published_raw) if isinstance(published_raw, str) else None
            precision = "date" if published_at else "unknown"
            description_html = item.get("description")
            description = (
                BeautifulSoup(html_lib.unescape(description_html), "html.parser").get_text(" ", strip=True)
                if isinstance(description_html, str) else ""
            )
            posting_url = item.get("url") or item.get("application_url") or f"https://apply.workable.com/{account}/"
            if not isinstance(posting_url, str) or not posting_url.startswith("https://"):
                posting_url = f"https://apply.workable.com/{account}/"
            details = {
                "account": account, "shortcode": shortcode,
                "board_registry_id": board.get("registry_id"),
                "employment_type": item.get("employment_type"),
                "department": item.get("department"), "function": item.get("function"),
                "industry": item.get("industry"), "experience": item.get("experience"),
                "education": item.get("education"), "telecommuting": bool(item.get("telecommuting")),
                "workplace_type": item.get("workplace_type"),
                "created_at": item.get("created_at"),
                "details_fetched": bool(description),
            }
            jobs.append(normalize_job(
                "workable", source_id, company or str(payload.get("name") or account),
                title, location, posting_url, published_at, precision, description,
                source_details=details,
            ))
    if successful_boards == 0:
        raise RuntimeError("All configured Workable boards failed: " + "; ".join(failures))
    if failures:
        log.warning("workable: partial failures=%s successful_boards=%s", len(failures), successful_boards)
    log.info("workable: boards=%s successful=%s failed=%s jobs=%s", len(boards), successful_boards, len(failures), len(jobs))
    return jobs



def _safe_board_redirect_url(url: str) -> str:
    """Validate every Keka careers-page redirect before following it."""
    return board_discovery._public_https_url(url)


def _keka_fetch_careers_page(source: str, careers_url: str) -> tuple[str, str]:
    current = _safe_board_redirect_url(careers_url)
    expected_host = (urlsplit(current).hostname or "").lower()
    headers = {**UA, "Accept": "text/html,application/xhtml+xml"}
    for _ in range(4):
        response = _tracked_source_get(
            source, current, headers=headers, timeout=20, allow_redirects=False
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location:
                raise ValueError("Keka careers page redirected without a destination.")
            next_url = _safe_board_redirect_url(urljoin(current, location))
            if (urlsplit(next_url).hostname or "").lower() != expected_host:
                raise ValueError("Keka careers page attempted to redirect to a different host.")
            current = next_url
            continue
        response.raise_for_status()
        if len(response.content) > board_discovery.MAX_HTML_BYTES:
            raise ValueError("Keka careers page exceeded the HTML size limit.")
        content_type = str(response.headers.get("Content-Type", "")).lower()
        if content_type and "html" not in content_type:
            raise ValueError("Keka careers page did not return HTML.")
        return current, response.text
    raise ValueError("Keka careers page exceeded the redirect limit.")


def keka_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect published Keka jobs through the public careers-site embed feed."""
    boards = config.get("keka_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Keka is enabled but no keka_boards are configured")
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []
    for board in boards:
        careers_url = str(board.get("careers_url") or board.get("url") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        detected = board_discovery.detect_ats_board(careers_url)
        if not detected or detected.get("provider") != "keka" or not company:
            _record_source_board("keka", False)
            failures.append("invalid Keka careers board configuration")
            continue
        tenant = str(detected["tenant"]).lower()
        portal = str(detected["portal"]).lower()
        careers_base = f"https://{detected['host']}/careers" if portal == "default" else f"https://{detected['host']}/careers/{portal}"
        try:
            final_url, html = _keka_fetch_careers_page("keka", careers_url)
            feed_match = re.search(
                r"/ats/documents/([0-9a-fA-F-]{16,})/careerportal/?",
                html,
                re.I,
            )
            if not feed_match:
                raise ValueError("Keka careers page did not expose a public career feed.")
            feed_id = feed_match.group(1)
            parsed = urlsplit(final_url)
            endpoint = f"https://{parsed.hostname}/careers/api/embedjobs/{portal}/active/{feed_id}"
            response = _tracked_source_get(
                "keka", endpoint,
                headers={**UA, "Accept": "application/json"},
                timeout=30, allow_redirects=False,
            )
            response.raise_for_status()
            if len(response.content) > 8_000_000:
                raise ValueError("Keka public career feed exceeded the response size limit.")
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Keka public career feed did not contain a jobs array.")
            _record_source_page("keka", True)
        except Exception as exc:
            _record_source_page("keka", False)
            failed_response = getattr(exc, "response", None)
            if getattr(failed_response, "status_code", None) == 429:
                _set_source_rate_limit("keka", failed_response)
            _record_source_board("keka", False)
            failures.append(f"{tenant}: {type(exc).__name__}")
            log.warning("keka: tenant=%s failed error_type=%s", tenant, type(exc).__name__)
            if _source_cooldown_remaining("keka") > 0:
                break
            continue

        successful_boards += 1
        _record_source_board("keka", True)
        if len(payload) > KEKA_MAX_JOBS_PER_BOARD:
            log.warning(
                "keka: tenant=%s returned %s jobs; processing first %s under the request budget",
                tenant, len(payload), KEKA_MAX_JOBS_PER_BOARD,
            )
        for item in payload[:KEKA_MAX_JOBS_PER_BOARD]:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("id")
            title = str(item.get("title") or "").strip()
            if raw_id in (None, "") or not title:
                continue
            source_id = f"keka-{tenant}-{raw_id}" if portal == "default" else f"keka-{tenant}-{portal}-{raw_id}"
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            locations: list[str] = []
            raw_locations = item.get("jobLocations")
            if isinstance(raw_locations, list):
                for loc in raw_locations:
                    if not isinstance(loc, dict):
                        continue
                    label = str(loc.get("name") or "").strip()
                    if not label:
                        parts = [
                            str(loc.get(field) or "").strip()
                            for field in ("city", "state", "countryName")
                            if str(loc.get(field) or "").strip()
                        ]
                        label = ", ".join(parts)
                    if label and label not in locations:
                        locations.append(label)
            location = "; ".join(locations)
            description_html = item.get("description") or item.get("excerpt") or ""
            description = (
                BeautifulSoup(html_lib.unescape(str(description_html)), "html.parser").get_text(" ", strip=True)
                if description_html else ""
            )
            published_raw = item.get("publishedOn")
            published_at = parse_relative(published_raw) if published_raw not in (None, "") else None
            precision = (
                "minute"
                if published_at and isinstance(published_raw, str)
                and re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}", published_raw)
                else "date" if published_at else "unknown"
            )
            url = f"{careers_base}/jobdetails/{quote(str(raw_id), safe='')}"
            salary = item.get("salaryRange") if isinstance(item.get("salaryRange"), dict) else {}
            details = {
                "tenant": tenant,
                "portal": portal,
                "board_registry_id": board.get("registry_id"),
                "job_number": item.get("jobNumber"),
                "department_id": item.get("departmentIdentifier"),
                "department": item.get("departmentName"),
                "experience": item.get("experience"),
                "job_type_code": item.get("jobType"),
                "salary_currency": salary.get("currency"),
                "salary_period_code": salary.get("salaryPeriod"),
                "salary_range_format": item.get("salaryRangeFormat"),
                "skill_names": item.get("skillNames") if isinstance(item.get("skillNames"), list) else [],
                "published_since_days": item.get("publishedSinceDays"),
                "details_fetched": bool(description),
            }
            jobs.append(normalize_job(
                "keka", source_id, company, title, location, url,
                published_at, precision, description, source_details=details,
            ))
    if successful_boards == 0:
        raise RuntimeError("All configured Keka boards failed: " + "; ".join(failures))
    if failures:
        log.warning("keka: partial failures=%s successful_boards=%s", len(failures), successful_boards)
    log.info("keka: boards=%s successful=%s failed=%s jobs=%s", len(boards), successful_boards, len(failures), len(jobs))
    return jobs


def darwinbox_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect public candidate-site postings where the tenant exposes its careers feed."""
    boards = config.get("darwinbox_boards", [])
    if not isinstance(boards, list) or not boards:
        raise RuntimeError("Darwinbox is enabled but no darwinbox_boards are configured")
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    successful_boards = 0
    failures: list[str] = []
    headers = {**UA, "Accept": "application/json"}
    for board in boards:
        careers_url = str(board.get("careers_url") or board.get("url") or "").strip() if isinstance(board, dict) else ""
        company = str(board.get("company") or "").strip() if isinstance(board, dict) else ""
        detected = board_discovery.detect_ats_board(careers_url)
        if not detected or detected.get("provider") != "darwinbox" or not company:
            _record_source_board("darwinbox", False)
            failures.append("invalid Darwinbox careers board configuration")
            continue
        tenant = str(detected.get("tenant") or "").lower()
        company_id = str(detected["board_key"])
        parsed = urlsplit(detected["board_url"])
        origin = f"https://{parsed.netloc}"
        successful_pages = 0
        failed_pages = 0
        board_jobs: list[dict[str, Any]] = []
        rate_limited = False
        for page_number in range(1, DARWINBOX_MAX_PAGES_PER_BOARD + 1):
            if page_number > 1:
                time.sleep(DARWINBOX_PAGE_DELAY_SECONDS)
            endpoint = f"{origin}/ms/candidateapi/job/alljobs?companyId={company_id}"
            try:
                response = _tracked_source_post(
                    "darwinbox", endpoint,
                    json_body={
                        "companyId": company_id,
                        "page": page_number,
                        "sort_option": "new",
                        "limit": DARWINBOX_PAGE_SIZE,
                    },
                    headers={**headers, "Content-Type": "application/json", "Referer": detected["board_url"]},
                    timeout=25,
                    allow_redirects=False,
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("data") if isinstance(payload, dict) and payload.get("status") == "success" else None
                if not isinstance(rows, list):
                    raise ValueError("Darwinbox public candidate endpoint returned an unexpected response envelope.")
                _record_source_page("darwinbox", True)
                successful_pages += 1
            except Exception as exc:
                _record_source_page("darwinbox", False)
                failed_pages += 1
                failed_response = getattr(exc, "response", None)
                if getattr(failed_response, "status_code", None) == 429:
                    _set_source_rate_limit("darwinbox", failed_response)
                    rate_limited = True
                failures.append(f"{tenant}/{company_id} page {page_number}: {type(exc).__name__}")
                log.warning("darwinbox: tenant=%s page=%s failed error_type=%s", tenant, page_number, type(exc).__name__)
                break
            for item in rows:
                if not isinstance(item, dict):
                    continue
                raw_id = item.get("id")
                title = str(item.get("title") or "").strip()
                if raw_id in (None, "") or not title:
                    continue
                source_id = f"darwinbox-{tenant}-{company_id}-{raw_id}"
                if source_id in seen_ids:
                    continue
                seen_ids.add(source_id)
                raw_locations = item.get("tool_tip_locations")
                locations = []
                if isinstance(raw_locations, list):
                    for value in raw_locations:
                        label = BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)
                        if label and label not in locations:
                            locations.append(label)
                if not locations:
                    label = str(item.get("locations") or "").strip()
                    if label:
                        locations.append(label)
                posted_raw = item.get("posted_on")
                if posted_raw in (None, ""):
                    posted_raw = item.get("created_on")
                published_at = parse_relative(posted_raw) if posted_raw not in (None, "") else None
                precision = (
                    "minute"
                    if published_at and (isinstance(posted_raw, (int, float)) or (isinstance(posted_raw, str) and re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}", posted_raw)))
                    else "date" if published_at else "unknown"
                )
                description_html = item.get("jd") or ""
                description = BeautifulSoup(html_lib.unescape(str(description_html)), "html.parser").get_text(" ", strip=True)
                url = f"{origin}/ms/candidatev2/{company_id}/careers/jobDetails/{quote(str(raw_id), safe='')}"
                details = {
                    "tenant": tenant,
                    "company_id": company_id,
                    "board_registry_id": board.get("registry_id"),
                    "internal_job_code": item.get("internal_job_code"),
                    "experience": item.get("experience"),
                    "locations_raw": item.get("locations"),
                    "details_fetched": bool(description),
                }
                board_jobs.append(normalize_job(
                    "darwinbox", source_id, company, title, "; ".join(locations),
                    url, published_at, precision, description, source_details=details,
                ))
            if len(rows) < DARWINBOX_PAGE_SIZE or rate_limited:
                break
        if successful_pages:
            successful_boards += 1
            _record_source_board("darwinbox", True)
            jobs.extend(board_jobs)
        else:
            _record_source_board("darwinbox", False)
        if rate_limited:
            break
    if successful_boards == 0:
        raise RuntimeError("All configured Darwinbox boards failed: " + "; ".join(failures))
    if failures:
        log.warning("darwinbox: partial failures=%s successful_boards=%s", len(failures), successful_boards)
    log.info("darwinbox: boards=%s successful=%s failed=%s jobs=%s", len(boards), successful_boards, len(failures), len(jobs))
    return jobs


def _tracked_hirebase_request(method: str, endpoint: str, **kwargs):
    """Record safe Hirebase request metrics without logging its key or query payload."""
    started_monotonic = time.monotonic()
    try:
        response = requests.request(method, endpoint, **kwargs)
    except Exception:
        _record_source_request(
            "hirebase", status_code=None,
            duration_ms=(time.monotonic() - started_monotonic) * 1000,
            exception=True,
        )
        raise
    _record_source_request(
        "hirebase", status_code=getattr(response, "status_code", None),
        duration_ms=(time.monotonic() - started_monotonic) * 1000,
    )
    return response


def _hirebase_local_usage(conn: sqlite3.Connection, period_start: str, today_start: str, provider: str) -> tuple[int, int, int]:
    row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                               THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0),
             COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                               THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0),
             COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                               THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0)
           FROM hirebase_usage_ledger
           WHERE period_start=? AND status IN ('reserved','unknown','complete_unverified','complete')
             AND created_at>=?""",
        (period_start, today_start),
    ).fetchone()
    daily_total = int(row[0] or 0) if row else 0
    provider_row = conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                                    THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0)
           FROM hirebase_usage_ledger
           WHERE period_start=? AND created_at>=? AND provider=?
             AND status IN ('reserved','unknown','complete_unverified','complete')""",
        (period_start, today_start, provider),
    ).fetchone()
    monthly_row = conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                                    THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0)
           FROM hirebase_usage_ledger
           WHERE period_start=? AND status IN ('reserved','unknown','complete_unverified','complete')""",
        (period_start,),
    ).fetchone()
    return int(monthly_row[0] or 0), daily_total, int(provider_row[0] or 0)


def _hirebase_reserve(provider: str, estimated_jobs: int, usage: dict[str, Any], *, reserve_jobs: int | None = None) -> int | None:
    today_start = iso(current_day_start_utc()) or iso(now())
    with db_lock, connect_sqlite(DB_PATH) as conn:
        monthly_used, daily_used, provider_daily_used = _hirebase_local_usage(
            conn, str(usage["period_start"]), str(today_start), provider
        )
        allowed = hirebase.provider_allowance(
            usage,
            local_monthly_used=monthly_used,
            local_daily_used=daily_used,
            provider_daily_used=provider_daily_used,
            monthly_cap=HIREBASE_MAX_MONTHLY_JOBS,
            daily_cap=HIREBASE_MAX_DAILY_JOBS,
            provider_daily_cap=HIREBASE_PROVIDER_DAILY_JOBS,
        )
        reservation_size = estimated_jobs if reserve_jobs is None else reserve_jobs
        if reservation_size > allowed or estimated_jobs <= 0 or reservation_size <= 0:
            return None
        cursor = conn.execute(
            """INSERT INTO hirebase_usage_ledger(
                   provider,created_at,period_start,period_end,estimated_jobs,
                   returned_jobs,reserved_jobs,status
               ) VALUES(?,?,?,?,?,NULL,?,'reserved')""",
            (provider, iso(now()), usage["period_start"], usage["period_end"],
             estimated_jobs, reservation_size),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _hirebase_finish_reservation(reservation_id: int, *, jobs_returned: int | None,
                                 usage_headers: dict[str, Any] | None,
                                 uncertain: bool = False) -> None:
    if uncertain:
        status = "unknown"
        returned = None
        reserved = None
    elif jobs_returned is None:
        status = "failed"
        returned = None
        reserved = 0
    elif usage_headers is None:
        # Keep the full estimate reserved until a later usage-summary reconciliation.
        status = "complete_unverified"
        returned = jobs_returned
        reserved = None
    else:
        status = "complete"
        returned = jobs_returned
        reserved = 0
    with db_lock, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            """UPDATE hirebase_usage_ledger
               SET status=?,returned_jobs=?,reserved_jobs=COALESCE(?,reserved_jobs),
                   included_used=?,included_remaining=?,response_verified=?
               WHERE id=?""",
            (status, returned, reserved,
             usage_headers.get("included_used") if usage_headers else None,
             usage_headers.get("included_remaining") if usage_headers else None,
             int(bool(usage_headers)), reservation_id),
        )
        conn.commit()


def _hirebase_get_window(provider: str) -> dict[str, Any] | None:
    with connect_sqlite(DB_PATH) as conn:
        row = conn.execute(
            "SELECT last_polled_at,window_start,next_page FROM hirebase_provider_state WHERE provider=?",
            (provider,),
        ).fetchone()
    if not row:
        return None
    return {
        "last_polled_at": str(row[0]),
        "window_start": str(row[1]),
        "next_page": max(1, int(row[2] or 1)),
    }


def _hirebase_set_window(provider: str, *, last_polled_at: str,
                         window_start: str, next_page: int) -> None:
    with db_lock, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO hirebase_provider_state(
                   provider,last_polled_at,window_start,next_page,updated_at
               ) VALUES(?,?,?,?,?) ON CONFLICT(provider) DO UPDATE SET
                   last_polled_at=excluded.last_polled_at,
                   window_start=excluded.window_start,
                   next_page=excluded.next_page,
                   updated_at=excluded.updated_at""",
            (provider, last_polled_at, window_start, next_page, iso(now())),
        )
        conn.commit()


def _hirebase_commit_pending_watermarks() -> None:
    pending = source_state.setdefault("hirebase", {}).pop("pending_watermarks", {})
    if not isinstance(pending, dict):
        return
    for provider, cursor in pending.items():
        if provider not in hirebase.ALLOWED_PROVIDERS or not isinstance(cursor, dict):
            continue
        last_polled_at = cursor.get("last_polled_at")
        window_start = cursor.get("window_start")
        next_page = cursor.get("next_page")
        if (isinstance(last_polled_at, str) and isinstance(window_start, str)
                and isinstance(next_page, int) and not isinstance(next_page, bool) and next_page >= 1):
            _hirebase_set_window(
                provider, last_polled_at=last_polled_at,
                window_start=window_start, next_page=next_page,
            )


def hirebase_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Optional daily Hirebase sampler with estimate-first, persisted hard budgets.

    This is disabled by default, fetches only 4 jobs per provider/day, caps local
    use at 400 jobs per Hirebase billing period (100 below the free allowance),
    and never uses a user's preferences to constrain global collection.
    """
    if not hirebase.api_key_configured():
        raise RuntimeError("Hirebase source enabled but HIREBASE_API_KEY is not configured")
    try:
        usage = hirebase.usage_summary(requester=_tracked_hirebase_request)
    except hirebase.HirebaseError as exc:
        response = getattr(exc, "response", None)
        if getattr(response, "status_code", None) == 429:
            _set_source_rate_limit("hirebase", response, default_seconds=300, maximum_seconds=3600)
        raise RuntimeError(f"Hirebase usage preflight failed: {exc}") from exc

    jobs: list[dict[str, Any]] = []
    spent_this_run = 0
    pending_watermarks: dict[str, dict[str, Any]] = {}
    for provider in ("workday", "keka", "darwinbox"):
        poll_started_at = iso(now()) or ""
        cursor = _hirebase_get_window(provider)
        if cursor:
            window_start = cursor["window_start"]
            page_number = cursor["next_page"]
        else:
            # First sample only starts with a seven-day discovery window. Pages
            # are drained oldest-first before the cursor advances to fresh data.
            initial_start = now() - dt.timedelta(days=7)
            window_start = iso(initial_start) or poll_started_at
            page_number = 1
        payload = hirebase.provider_query(
            provider, limit=HIREBASE_PROVIDER_LIMIT,
            ingested_after=window_start, page=page_number,
        )
        try:
            estimated = hirebase.estimate(payload, requester=_tracked_hirebase_request)
        except hirebase.HirebaseError as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            if status_code == 429:
                _set_source_rate_limit("hirebase", response, default_seconds=300, maximum_seconds=3600)
                _record_source_board("hirebase", False)
                log.warning("hirebase: provider=%s estimate rate-limited; remaining estimates stopped", provider)
                break
            if status_code in {401, 403}:
                _record_source_board("hirebase", False)
                raise RuntimeError(f"Hirebase estimate preflight failed: {exc}") from exc
            _record_source_board("hirebase", False)
            log.warning("hirebase: provider=%s estimate failed error=%s", provider, str(exc))
            continue
        _record_source_page("hirebase", True)
        if estimated == 0:
            # The current page is empty, so drain is complete. Resume from the
            # poll start minus two hours to catch late-indexed rows next cycle.
            next_window = iso(now() - dt.timedelta(hours=2)) or poll_started_at
            _hirebase_set_window(
                provider, last_polled_at=poll_started_at,
                window_start=next_window, next_page=1,
            )
            _record_source_board("hirebase", True)
            continue
        if estimated > HIREBASE_PROVIDER_LIMIT:
            _record_source_board("hirebase", False)
            log.warning("hirebase: provider=%s estimate exceeded hard per-query cap", provider)
            continue

        # Preserve the fixed page size so page boundaries do not shift when an
        # estimate returns fewer than four rows. Reserve the full requested limit
        # because Hirebase's hard-cap check holds the requested limit atomically.
        payload["limit"] = HIREBASE_PROVIDER_LIMIT
        reservation_id = _hirebase_reserve(
            provider, estimated, usage, reserve_jobs=HIREBASE_PROVIDER_LIMIT
        )
        if reservation_id is None:
            log.info("hirebase: provider=%s skipped; local or provider allowance would be exceeded", provider)
            _record_source_board("hirebase", True)
            continue
        try:
            raw_jobs, meter_headers, pagination = hirebase.search(
                payload, requester=_tracked_hirebase_request
            )
        except hirebase.HirebaseError as exc:
            message = str(exc)
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            uncertain = response is None or status_code >= 500 if status_code is not None else True
            # A successful HTTP response with invalid JSON/shape may already have
            # consumed credits; retain the reservation until usage reconciliation.
            if status_code == 200:
                uncertain = True
            _hirebase_finish_reservation(
                reservation_id, jobs_returned=None, usage_headers=None, uncertain=uncertain
            )
            _record_source_page("hirebase", False)
            if status_code == 429:
                _set_source_rate_limit(
                    "hirebase", response,
                    default_seconds=300, maximum_seconds=3600,
                )
                _record_source_board("hirebase", False)
                log.warning("hirebase: provider=%s rate limited; remaining provider searches stopped", provider)
                break
            _record_source_board("hirebase", False)
            log.warning("hirebase: provider=%s search failed error=%s", provider, message)
            if status_code in {401, 403}:
                raise RuntimeError(f"Hirebase search rejected authentication/authorization: {message}") from exc
            continue

        normalized: list[dict[str, Any]] = []
        for item in raw_jobs:
            parsed = hirebase.normalize_provider_job(item)
            if not parsed:
                continue
            normalized.append(normalize_job(
                "hirebase", parsed["source_job_id"], parsed["company"],
                parsed["title"], parsed["location"], parsed["url"],
                parsed["posted_at"], parsed["posted_precision"],
                parsed["description"], source_details=parsed["source_details"],
            ))
        _hirebase_finish_reservation(
            reservation_id, jobs_returned=len(raw_jobs), usage_headers=meter_headers
        )
        _record_source_page("hirebase", True)
        _record_source_board("hirebase", True)
        if pagination["page"] < pagination["total_pages"]:
            next_window = window_start
            next_page = pagination["page"] + 1
        else:
            next_window = iso(dt.datetime.fromisoformat(poll_started_at) - dt.timedelta(hours=2)) or poll_started_at
            next_page = 1
        pending_watermarks[provider] = {
            "last_polled_at": poll_started_at,
            "window_start": next_window,
            "next_page": next_page,
        }
        jobs.extend(normalized)
        spent_this_run += len(raw_jobs)
        if meter_headers:
            usage["remaining"] = meter_headers["included_remaining"]
        else:
            # No metering confirmation: stop after this search rather than risk a second request.
            usage["remaining"] = 0
            break
        if spent_this_run >= HIREBASE_MAX_DAILY_JOBS:
            break
    if pending_watermarks:
        source_state.setdefault("hirebase", {})["pending_watermarks"] = pending_watermarks
    return jobs


COLLECTORS = {
    "linkedin": linkedin_collect,
    "naukri": lambda config: naukri_collect(),
    "instahyre": instahyre_collect,
    "greenhouse": greenhouse_collect,
    "ashby": ashby_collect,
    "lever": lever_collect,
    "workday": workday_collect,
    "smartrecruiters": smartrecruiters_collect,
    "workable": workable_collect,
    "keka": keka_collect,
    "darwinbox": darwinbox_collect,
    "hirebase": hirebase_collect,
}
SOURCE_NAMES = tuple(COLLECTORS)


def _legacy_notifications_enabled(
    config: dict[str, Any], credentials_available: bool
) -> bool:
    """Require both configured credentials and the explicit global feature switch."""
    return bool(credentials_available and config.get("notifications_enabled", True))


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
    if source == "hirebase":
        runtime_at_start.pop("pending_watermarks", None)
    elif source == "workday":
        runtime_at_start.pop("pending_board_states", None)
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
        if source == "hirebase":
            _hirebase_commit_pending_watermarks()
        elif source == "workday":
            _workday_commit_pending_board_states()
        board_baseline_suppressed = suppress_activated_board_inventory(source)
        if board_baseline_suppressed:
            log.info(
                "source=%s newly activated board baseline suppressed jobs=%s",
                source, board_baseline_suppressed,
            )
        baseline_suppressed = suppress_initial_source_snapshot_alerts(
            source,
            started_at,
        )
        if baseline_suppressed:
            log.info(
                "source=%s initial inventory baseline suppressed canonical_opportunities=%s",
                source,
                baseline_suppressed,
            )
        refresh_job_evaluations(config)
        refresh_notification_decisions(config)

        # Deliver immediately after a discovery cycle queues eligible jobs.
        # The background worker remains as a fallback/retry path.
        try:
            from v2.telegram import credentials_available, deliver_queued_notifications

            if _legacy_notifications_enabled(config, credentials_available()):
                delivered = deliver_queued_notifications(50)
                if delivered:
                    log.info("telegram: delivered=%s source=%s", delivered, source)
        except Exception:
            log.exception("telegram immediate delivery failed source=%s", source)

        finished = now()
        duration_seconds = max(0.0, time.monotonic() - started_monotonic)
        cooldown_remaining = (
            _linkedin_cooldown_remaining() if source == "linkedin"
            else _source_cooldown_remaining(source) if source in PUBLIC_ATS_RATE_LIMIT_SOURCES
            else 0.0
        )
        metrics = request_metrics or {}
        rate_limit_seen = (
            (source == "linkedin" and linkedin_rate_limit_generation != rate_limit_generation_at_start)
            or (source in PUBLIC_ATS_RATE_LIMIT_SOURCES and bool(metrics.get("http_429", 0)))
        )
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
            runtime.pop("rate_limited_until_monotonic", None)
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
            _linkedin_cooldown_remaining() if source == "linkedin"
            else _source_cooldown_remaining(source) if source in PUBLIC_ATS_RATE_LIMIT_SOURCES
            else 0.0
        )
        if source == "linkedin" and cooldown_remaining > 0:
            metadata["rate_limited"] = True
        if source in PUBLIC_ATS_RATE_LIMIT_SOURCES and cooldown_remaining > 0:
            metadata.update({
                "rate_limited": True,
                "http_status": 429,
                "error": "HTTP 429",
                "error_type": "HTTPError",
                "retry_after_seconds": source_state.get(source, {}).get(
                    "rate_limit_retry_after_seconds"
                ),
            })
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
                if (source == "linkedin" or source in PUBLIC_ATS_RATE_LIMIT_SOURCES) and metadata["rate_limited"] else None
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

            legacy_notifications_enabled = _legacy_notifications_enabled(
                get_config(), credentials_available()
            )
            if legacy_notifications_enabled:
                await asyncio.to_thread(recover_stale_claims)
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
            if name in PUBLIC_ATS_RATE_LIMIT_SOURCES and _source_cooldown_remaining(name) > 0:
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
    restore_workday_rate_limit_state()
    restore_source_rate_limit_state("smartrecruiters")
    restore_source_rate_limit_state("workable")
    restore_source_rate_limit_state("keka")
    restore_source_rate_limit_state("darwinbox")
    restore_source_rate_limit_state("hirebase")
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
    with connect_sqlite(DB_PATH) as conn:
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
    return {"config": saved, "runtime_path": str(RUNTIME_CONFIG_PATH)}


@app.get("/api/latency-summary", dependencies=[Depends(require_admin)])
def latency_summary(hours: int = 24):
    hours = max(1, min(hours, 168))
    cutoff = iso(now() - dt.timedelta(hours=hours))

    source_placeholders = ",".join("?" for _ in SOURCE_NAMES)
    with connect_sqlite(DB_PATH) as conn:
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


@app.post("/api/discovery/companies/scan", dependencies=[Depends(require_admin)])
def discover_company_boards(payload: dict[str, Any]):
    """Register one employer and discover public ATS board candidates for review."""
    company_name = str(payload.get("company_name") or "").strip()
    website_url = str(payload.get("website_url") or "").strip()
    careers_url_value = payload.get("careers_url")
    careers_url = str(careers_url_value).strip() if careers_url_value else None
    country_value = payload.get("country")
    country = str(country_value).strip()[:80] if country_value else None
    if not company_name or not website_url:
        raise HTTPException(status_code=422, detail="company_name and website_url are required.")
    try:
        result = board_discovery.discover_public_careers(
            company_name, website_url, careers_url
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    domain = board_discovery.domain_key(result["website_url"])
    timestamp = iso(now())
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO employer_companies(
                   company_name,domain,website_url,careers_url,country,discovery_status,
                   pages_checked,last_discovered_at,error_count,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(domain) DO UPDATE SET
                   company_name=excluded.company_name,
                   website_url=excluded.website_url,
                   careers_url=excluded.careers_url,
                   country=COALESCE(excluded.country,employer_companies.country),
                   discovery_status=excluded.discovery_status,
                   pages_checked=excluded.pages_checked,
                   last_discovered_at=excluded.last_discovered_at,
                   error_count=excluded.error_count,
                   updated_at=excluded.updated_at""",
            (
                company_name, domain, result["website_url"], result["careers_url"],
                country, result["discovery_status"], result["pages_checked"],
                timestamp, len(result["errors"]), timestamp, timestamp,
            ),
        )
        company_row = conn.execute(
            "SELECT id FROM employer_companies WHERE domain=?", (domain,)
        ).fetchone()
        company_id = int(company_row[0])
        stored_ids: list[int] = []
        for board in result["boards"]:
            conn.execute(
                """INSERT INTO ats_board_registry(
                       company_id,provider,board_key,board_url,discovered_from,confidence,
                       collector_source,collector_available,review_status,last_seen_at,
                       created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,'discovered',?,?,?)
                   ON CONFLICT(company_id,provider,board_key) DO UPDATE SET
                       board_url=excluded.board_url,
                       discovered_from=excluded.discovered_from,
                       confidence=excluded.confidence,
                       collector_source=excluded.collector_source,
                       collector_available=excluded.collector_available,
                       last_seen_at=excluded.last_seen_at,
                       review_status=CASE
                           WHEN ats_board_registry.review_status IN ('active','rejected')
                           THEN ats_board_registry.review_status
                           ELSE 'discovered' END,
                       updated_at=excluded.updated_at""",
                (
                    company_id, board["provider"], board["board_key"],
                    board["board_url"], board["discovered_from"],
                    board.get("confidence", "medium"), board.get("collector_source"),
                    int(bool(board.get("collector_available"))), timestamp,
                    timestamp, timestamp,
                ),
            )
            row = conn.execute(
                "SELECT id FROM ats_board_registry WHERE company_id=? AND provider=? AND board_key=?",
                (company_id, board["provider"], board["board_key"]),
            ).fetchone()
            if row:
                stored_ids.append(int(row[0]))
        conn.commit()

    return {
        "company_id": company_id,
        "company_name": company_name,
        "domain": domain,
        "discovery_status": result["discovery_status"],
        "pages_checked": result["pages_checked"],
        "boards_discovered": len(result["boards"]),
        "board_ids": stored_ids,
        "boards": result["boards"],
        "errors": result["errors"],
        "activation_note": "Discovery never enables a source. Review and verify each board before connecting it to a collector.",
    }


@app.post("/api/discovery/directories/last-round/import", dependencies=[Depends(require_admin)])
def import_last_round_ats_directory():
    """Import the attributed CC BY 4.0 ATS directory as unverified candidates only."""
    directory_path = ROOT / "data" / "lastroundai-ats-company-directory-2026-08.csv"
    try:
        candidates = ats_directory.load_directory(directory_path)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"ATS directory could not be read ({type(exc).__name__}).") from exc
    timestamp = iso(now()) or ""
    inserted_companies = 0
    inserted_boards = 0
    updated_boards = 0
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        for board in candidates:
            provider = board["provider"]
            slug = board["board_key"]
            company_name = board["company_name"]
            # Reuse a previously discovered board instead of creating a duplicate
            # company row with a synthetic directory domain.
            existing_any = conn.execute(
                """SELECT id,company_id FROM ats_board_registry
                   WHERE provider=? AND board_key=?
                   ORDER BY CASE review_status WHEN 'active' THEN 0 WHEN 'verified' THEN 1 ELSE 2 END,id
                   LIMIT 1""",
                (provider, slug),
            ).fetchone()
            if existing_any:
                conn.execute(
                    "UPDATE ats_board_registry SET directory_last_crawled=?,last_seen_at=?,updated_at=? WHERE id=?",
                    (board["last_crawled"], timestamp, timestamp, int(existing_any[0])),
                )
                updated_boards += 1
                continue
            domain = ats_directory.synthetic_domain(provider, slug)
            before = conn.total_changes
            conn.execute(
                """INSERT INTO employer_companies(
                       company_name,domain,website_url,careers_url,country,discovery_status,
                       pages_checked,last_discovered_at,error_count,created_at,updated_at
                   ) VALUES(?,?,?,?,NULL,'seeded_directory',0,?,0,?,?)
                   ON CONFLICT(domain) DO UPDATE SET
                       company_name=excluded.company_name,
                       website_url=excluded.website_url,
                       careers_url=excluded.careers_url,
                       discovery_status=CASE WHEN employer_companies.discovery_status IN ('scanned','boards_found')
                                             THEN employer_companies.discovery_status ELSE 'seeded_directory' END,
                       last_discovered_at=excluded.last_discovered_at,
                       updated_at=excluded.updated_at""",
                (company_name, domain, board["board_url"], board["board_url"], timestamp, timestamp, timestamp),
            )
            if conn.total_changes > before:
                inserted_companies += 1
            company = conn.execute("SELECT id FROM employer_companies WHERE domain=?", (domain,)).fetchone()
            if not company:
                continue
            existing = conn.execute(
                "SELECT id,review_status FROM ats_board_registry WHERE company_id=? AND provider=? AND board_key=?",
                (int(company[0]), provider, slug),
            ).fetchone()
            conn.execute(
                """INSERT INTO ats_board_registry(
                       company_id,provider,board_key,board_url,discovered_from,confidence,
                       collector_source,collector_available,review_status,last_seen_at,
                       created_at,updated_at,directory_last_crawled
                   ) VALUES(?,?,?,?,?,'low',?,1,'discovered',?,?,?,?)
                   ON CONFLICT(company_id,provider,board_key) DO UPDATE SET
                       board_url=excluded.board_url,
                       discovered_from=excluded.discovered_from,
                       collector_source=excluded.collector_source,
                       collector_available=1,
                       directory_last_crawled=excluded.directory_last_crawled,
                       last_seen_at=excluded.last_seen_at,
                       review_status=CASE WHEN ats_board_registry.review_status IN ('active','rejected','verified','reviewed')
                                          THEN ats_board_registry.review_status ELSE 'discovered' END,
                       updated_at=excluded.updated_at""",
                (int(company[0]), provider, slug, board["board_url"], ats_directory.DATASET_URL,
                 provider, timestamp, timestamp, timestamp, board["last_crawled"]),
            )
            if existing is None:
                inserted_boards += 1
            elif existing[1] not in {"active", "rejected", "verified", "reviewed"}:
                updated_boards += 1
        conn.commit()
    return {
        "dataset": ats_directory.DATASET_NAME,
        "snapshot": ats_directory.DATASET_SNAPSHOT,
        "license": ats_directory.DATASET_LICENSE,
        "attribution": ats_directory.DATASET_ATTRIBUTION,
        "source_url": ats_directory.DATASET_URL,
        "companies_in_snapshot": len(candidates),
        "companies_added_or_refreshed": inserted_companies,
        "boards_added": inserted_boards,
        "unverified_boards_refreshed": updated_boards,
        "review_status": "discovered",
        "activation": "none; imported candidates are not verified or scheduled",
        "coverage_limit": "Greenhouse, Lever and Ashby only; Workday, Keka and Darwinbox are not in this dataset",
    }


@app.get("/api/discovery/companies", dependencies=[Depends(require_admin)])
def list_discovered_companies(limit: int = 100):
    limit = max(1, min(int(limit), 500))
    with connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT c.id,c.company_name,c.domain,c.website_url,c.careers_url,c.country,
                      c.discovery_status,c.pages_checked,c.last_discovered_at,c.error_count,
                      COUNT(b.id) AS board_count
               FROM employer_companies c LEFT JOIN ats_board_registry b ON b.company_id=c.id
               GROUP BY c.id ORDER BY c.updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"companies": [dict(row) for row in rows]}


@app.get("/api/discovery/coverage-summary", dependencies=[Depends(require_admin)])
def get_discovery_coverage_summary():
    """Return registry counts by provider and review state; never imply total market coverage."""
    with connect_sqlite(DB_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM ats_board_registry").fetchone()[0]
        directory_seeded = conn.execute(
            "SELECT COUNT(*) FROM ats_board_registry WHERE directory_last_crawled IS NOT NULL"
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT provider,review_status,COUNT(*),
                      SUM(CASE WHEN collector_available=1 THEN 1 ELSE 0 END),
                      SUM(CASE WHEN directory_last_crawled IS NOT NULL THEN 1 ELSE 0 END)
               FROM ats_board_registry GROUP BY provider,review_status ORDER BY provider,review_status"""
        ).fetchall()
    providers: dict[str, Any] = {}
    for provider, status, count, available, seeded in rows:
        entry = providers.setdefault(provider, {
            "total": 0, "collector_available": 0, "directory_seeded": 0, "by_status": {}
        })
        entry["by_status"][status] = int(count or 0)
        entry["total"] += int(count or 0)
        entry["collector_available"] += int(available or 0)
        entry["directory_seeded"] += int(seeded or 0)
    return {
        "employer_boards_known": int(total or 0),
        "directory_seed_candidates": int(directory_seeded or 0),
        "providers": providers,
        "market_coverage_percentage": None,
        "coverage_note": "Registry coverage is not total market coverage. Candidate directories are not verified boards; private and non-indexed employers may be absent.",
    }


@app.get("/api/workday/inventory-status", dependencies=[Depends(require_admin)])
def get_workday_inventory_status():
    """Explain per-board Workday inventory progress without implying full coverage."""
    config = get_config()
    configured = config.get("workday_boards", [])
    boards: list[dict[str, Any]] = []
    for board in configured if isinstance(configured, list) else []:
        if not isinstance(board, dict):
            continue
        parsed = _parse_workday_board_url(board.get("url"))
        if not parsed:
            continue
        board_key = f"{parsed['tenant']}:{parsed['site']}"
        state = _workday_get_board_poll_state(board_key)
        facet_work_remaining = bool(
            state.get("facet_queue") or state.get("active_facet_query")
        )
        if state.get("truncated_reason") and facet_work_remaining:
            status = "in_progress_incomplete"
            last_attempt = state.get("last_inventory_attempt_at")
            next_due_at = None
            if last_attempt:
                try:
                    last_dt = dt.datetime.fromisoformat(str(last_attempt).replace("Z", "+00:00"))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=UTC)
                    next_due_at = iso(last_dt + dt.timedelta(seconds=WORKDAY_INVENTORY_PAGE_INTERVAL_SECONDS))
                except ValueError:
                    next_due_at = None
        elif state.get("truncated_reason"):
            status = "truncated"
            next_due_at = None
        elif state.get("inventory_complete"):
            status = "complete"
            last_full = state.get("last_full_inventory_at")
            next_due_at = None
            if last_full:
                try:
                    last_dt = dt.datetime.fromisoformat(str(last_full).replace("Z", "+00:00"))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=UTC)
                    next_due_at = iso(last_dt + dt.timedelta(seconds=WORKDAY_FULL_INVENTORY_REFRESH_SECONDS))
                except ValueError:
                    next_due_at = None
        elif state.get("last_inventory_attempt_at"):
            status = "in_progress"
            try:
                last_dt = dt.datetime.fromisoformat(str(state["last_inventory_attempt_at"]).replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=UTC)
                next_due_at = iso(last_dt + dt.timedelta(seconds=WORKDAY_INVENTORY_PAGE_INTERVAL_SECONDS))
            except ValueError:
                next_due_at = None
        else:
            status = "not_started"
            next_due_at = iso(now())
        boards.append({
            "company": str(board.get("company") or "Unknown employer"),
            "board_key": board_key,
            "url": parsed["url"],
            "status": status,
            "freshness_poll_seconds": int(config.get("poll_seconds", {}).get("workday", 120)),
            "inventory_page_interval_seconds": WORKDAY_INVENTORY_PAGE_INTERVAL_SECONDS,
            "next_inventory_offset": state.get("next_inventory_offset"),
            "reported_total": state.get("reported_total"),
            "facets_available": len(state.get("facets") or []),
            "facet_partitioned": bool(state.get("facet_partition_started")),
            "pending_facet_partitions": len(state.get("facet_queue") or []),
            "active_facet_query": bool(state.get("active_facet_query")),
            "active_applied_facets": state.get("active_facets") or {},
            "last_inventory_attempt_at": state.get("last_inventory_attempt_at"),
            "last_full_inventory_at": state.get("last_full_inventory_at"),
            "next_inventory_due_at": next_due_at,
            "truncated_reason": state.get("truncated_reason"),
            "inventory_complete": bool(state.get("inventory_complete")),
        })
    return {
        "boards_configured": len(boards),
        "boards": boards,
        "freshness_poll_note": "The first page is polled on the source cadence. At most one extra inventory page per board is requested every 15 minutes.",
        "coverage_note": "Queries reporting the 2,000-result cap are subdivided using available jobFamilyGroup, timeType, locations and workerSubType facets. Any leaf that cannot be safely subdivided remains explicitly incomplete.",
    }


@app.get("/api/discovery/boards", dependencies=[Depends(require_admin)])
def list_discovered_boards(status: str | None = None, limit: int = 250):
    limit = max(1, min(int(limit), 1000))
    query = """SELECT b.id,b.company_id,c.company_name,c.domain,b.provider,b.board_key,
                      b.board_url,b.discovered_from,b.confidence,b.collector_source,
                      b.collector_available,b.review_status,b.baseline_pending,b.last_verified_at,
                      b.last_seen_at,b.last_error_type,b.directory_last_crawled
               FROM ats_board_registry b JOIN employer_companies c ON c.id=b.company_id"""
    values: list[Any] = []
    if status:
        if status not in {"discovered", "reviewed", "verified", "rejected", "active"}:
            raise HTTPException(status_code=422, detail="Unsupported board review status.")
        query += " WHERE b.review_status=?"
        values.append(status)
    query += " ORDER BY b.last_seen_at DESC,b.id DESC LIMIT ?"
    values.append(limit)
    with connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, values).fetchall()
    return {"boards": [dict(row) for row in rows]}


@app.post("/api/discovery/boards/{board_id}/verify", dependencies=[Depends(require_admin)])
def verify_discovered_board(board_id: int):
    """Probe a known public ATS endpoint; verification never enables polling."""
    with connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT id,provider,board_key,board_url,collector_available
               FROM ats_board_registry WHERE id=?""", (board_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Discovered board was not found.")
    candidate = dict(row)
    if not candidate["collector_available"]:
        raise HTTPException(status_code=409, detail="This ATS has been discovered but its V2 collector is not implemented yet.")
    try:
        result = board_discovery.probe_public_board(candidate)
    except (ValueError, requests.RequestException) as exc:
        error_type = type(exc).__name__
        with DB_LOCK, connect_sqlite(DB_PATH) as conn:
            conn.execute(
                "UPDATE ats_board_registry SET last_error_type=?,updated_at=? WHERE id=?",
                (error_type, iso(now()), board_id),
            )
            conn.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Public {candidate['provider']} board verification failed ({error_type}).",
        ) from exc
    timestamp = iso(now())
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            """UPDATE ats_board_registry
               SET review_status='verified',last_verified_at=?,last_seen_at=?,
                   last_error_type=NULL,updated_at=? WHERE id=?""",
            (timestamp, timestamp, timestamp, board_id),
        )
        conn.commit()
    return {"board_id": board_id, **result, "scheduler_enabled": False}


@app.post("/api/discovery/boards/{board_id}/review", dependencies=[Depends(require_admin)])
def review_discovered_board(board_id: int, payload: dict[str, Any]):
    status = str(payload.get("status") or "").strip().lower()
    if status not in {"reviewed", "rejected"}:
        raise HTTPException(status_code=422, detail="status must be 'reviewed' or 'rejected'.")
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        cursor = conn.execute(
            "UPDATE ats_board_registry SET review_status=?,updated_at=? WHERE id=? AND review_status!='active'",
            (status, iso(now()), board_id),
        )
        if cursor.rowcount == 0:
            existing = conn.execute("SELECT review_status FROM ats_board_registry WHERE id=?", (board_id,)).fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Discovered board was not found.")
            if existing[0] == "active":
                raise HTTPException(status_code=409, detail="Active boards cannot be changed through discovery review.")
        conn.commit()
    return {"board_id": board_id, "review_status": status}


@app.post("/api/discovery/boards/{board_id}/activate", dependencies=[Depends(require_admin)])
def activate_discovered_board(board_id: int):
    """Attach a verified board to its collector and enable that source.

    The first successful poll is marked as historical baseline so an existing
    vacancy archive does not trigger a backfill alert burst.
    """
    with connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT b.id,b.provider,b.board_key,b.board_url,b.collector_source,
                      b.collector_available,b.review_status,c.company_name
               FROM ats_board_registry b JOIN employer_companies c ON c.id=b.company_id
               WHERE b.id=?""", (board_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Discovered board was not found.")
    board = dict(row)
    if board["review_status"] != "verified":
        raise HTTPException(status_code=409, detail="Verify this public board endpoint before activation.")
    if not board["collector_available"] or not board["collector_source"]:
        raise HTTPException(status_code=409, detail="This ATS has been discovered but no supported V2 collector is available.")

    source = str(board["collector_source"])
    provider = str(board["provider"])
    key = str(board["board_key"])
    company = str(board["company_name"])
    registry_entry: dict[str, Any]
    config_key: str
    if provider == "workday":
        config_key = "workday_boards"
        registry_entry = {"url": board["board_url"], "company": company}
    elif provider == "greenhouse":
        config_key = "greenhouse_boards"
        registry_entry = {"token": key, "company": company}
    elif provider == "ashby":
        config_key = "ashby_boards"
        registry_entry = {"board": key, "company": company}
    elif provider == "lever":
        config_key = "lever_boards"
        registry_entry = {
            "site": key, "company": company,
            "instance": "eu" if ".eu." in (urlsplit(board["board_url"]).hostname or "") else "global",
        }
    elif provider == "smartrecruiters":
        config_key = "smartrecruiters_boards"
        registry_entry = {"company_identifier": key, "company": company}
    elif provider == "workable":
        config_key = "workable_boards"
        registry_entry = {"account": key, "company": company}
    elif provider == "keka":
        config_key = "keka_boards"
        registry_entry = {"careers_url": board["board_url"], "company": company}
    elif provider == "darwinbox":
        config_key = "darwinbox_boards"
        registry_entry = {"careers_url": board["board_url"], "company": company}
    else:
        raise HTTPException(status_code=409, detail="This board provider has no activation mapping.")

    config = get_config()
    current_entries = list(config.get(config_key) or [])

    def same_configured_board(item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        if provider == "greenhouse":
            return str(item.get("token") or "").strip().lower() == key.lower()
        if provider == "ashby":
            return str(item.get("board") or "").strip().lower() == key.lower()
        if provider == "lever":
            item_instance = str(item.get("instance") or "global").strip().lower()
            expected_instance = "eu" if ".eu." in (urlsplit(board["board_url"]).hostname or "") else "global"
            return str(item.get("site") or "").strip().lower() == key.lower() and item_instance == expected_instance
        if provider == "smartrecruiters":
            value = item.get("company_identifier") or item.get("identifier")
            return isinstance(value, str) and value.strip().lower() == key.lower()
        if provider == "workable":
            value = item.get("account") or item.get("subdomain")
            return isinstance(value, str) and value.strip().lower() == key.lower()
        if provider == "workday":
            parsed = _parse_workday_board_url(item.get("url"))
            return bool(parsed and f"{parsed['tenant']}:{parsed['site']}".lower() == key.lower())
        if provider in {"keka", "darwinbox"}:
            value = item.get("careers_url") or item.get("url")
            detected = board_discovery.detect_ats_board(value) if isinstance(value, str) else None
            return bool(detected and detected.get("provider") == provider and str(detected.get("board_key", "")).lower() == key.lower())
        return False

    existing = next((
        item for item in current_entries
        if isinstance(item, dict) and str(item.get("registry_id") or "") == str(board_id)
    ), None)
    if existing is None:
        existing = next((item for item in current_entries if same_configured_board(item)), None)
        if existing is not None:
            linked_id = existing.get("registry_id")
            if linked_id not in (None, "", board_id, str(board_id)):
                raise HTTPException(status_code=409, detail="This board is already linked to a different registry entry.")
            existing["registry_id"] = board_id
    if existing is None:
        registry_entry["registry_id"] = board_id
        current_entries.append(registry_entry)
    config[config_key] = current_entries
    config.setdefault("source_enabled", {})[source] = True
    try:
        saved = save_config(config)
    except HTTPException:
        raise
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Board configuration could not be activated: {type(exc).__name__}.") from exc

    timestamp = iso(now())
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            """UPDATE ats_board_registry
               SET review_status='active',baseline_pending=1,last_verified_at=COALESCE(last_verified_at,?),
                   last_seen_at=?,last_error_type=NULL,updated_at=? WHERE id=?""",
            (timestamp, timestamp, timestamp, board_id),
        )
        conn.commit()
    refresh_job_evaluations(saved)
    refresh_notification_decisions(saved)
    refresh_configured_user_evaluations()
    interval = int(saved.get("poll_seconds", {}).get(source, 120))
    return {
        "board_id": board_id, "provider": provider, "collector_source": source,
        "review_status": "active", "source_enabled": True,
        "poll_interval_seconds": interval, "baseline_pending": True,
        "first_poll_note": "Existing board inventory will be ingested silently once before fresh-job alerts are eligible.",
    }


@app.post("/api/discovery/boards/{board_id}/deactivate", dependencies=[Depends(require_admin)])
def deactivate_discovered_board(board_id: int):
    """Remove one active employer board without disabling its provider peers."""
    with connect_sqlite(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id,provider,collector_source,review_status FROM ats_board_registry WHERE id=?",
            (board_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Discovered board was not found.")
    board = dict(row)
    if board["review_status"] != "active":
        raise HTTPException(status_code=409, detail="Only an active board can be disabled.")

    source = str(board["collector_source"] or "")
    config_key = {
        "greenhouse": "greenhouse_boards",
        "ashby": "ashby_boards",
        "lever": "lever_boards",
        "workday": "workday_boards",
        "smartrecruiters": "smartrecruiters_boards",
        "workable": "workable_boards",
        "keka": "keka_boards",
        "darwinbox": "darwinbox_boards",
    }.get(str(board["provider"]))
    if not source or not config_key:
        raise HTTPException(status_code=409, detail="This board has no supported collector configuration.")
    if source_state.get(source, {}).get("running"):
        raise HTTPException(status_code=409, detail="This provider is polling now. Retry after the current poll completes.")

    config = get_config()
    entries = list(config.get(config_key) or [])
    remaining = [
        item for item in entries
        if not (isinstance(item, dict) and str(item.get("registry_id") or "") == str(board_id))
    ]
    if len(remaining) == len(entries):
        raise HTTPException(status_code=409, detail="Board is not linked to its provider allowlist; configuration was not changed.")

    config[config_key] = remaining
    if not remaining:
        config.setdefault("source_enabled", {})[source] = False
    try:
        saved = save_config(config)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Board configuration could not be updated: {type(exc).__name__}.") from exc

    timestamp = iso(now())
    with DB_LOCK, connect_sqlite(DB_PATH) as conn:
        conn.execute(
            "UPDATE ats_board_registry SET review_status='verified',baseline_pending=0,updated_at=? WHERE id=?",
            (timestamp, board_id),
        )
        conn.commit()
    return {
        "board_id": board_id,
        "review_status": "verified",
        "source": source,
        "source_enabled": bool(saved.get("source_enabled", {}).get(source)),
        "remaining_boards": len(remaining),
        "takes_effect_next_poll": True,
    }


@app.get("/api/hirebase/status", dependencies=[Depends(require_admin)])
def hirebase_status():
    """Show safe Hirebase configuration and local budget state; never returns the key."""
    config = get_config()
    cutoff = iso(current_day_start_utc()) or iso(now())
    with connect_sqlite(DB_PATH) as conn:
        monthly = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                                        THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0),
                      COUNT(*),MAX(created_at),MAX(period_end),MAX(included_remaining)
               FROM hirebase_usage_ledger
               WHERE period_start=(SELECT period_start FROM hirebase_usage_ledger
                                   ORDER BY created_at DESC,id DESC LIMIT 1)"""
        ).fetchone()
        daily = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                                        THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0)
               FROM hirebase_usage_ledger WHERE created_at>=?""", (cutoff,)
        ).fetchone()
        providers = conn.execute(
            """SELECT provider,COALESCE(SUM(CASE WHEN status IN ('reserved','unknown','complete_unverified')
                                                  THEN reserved_jobs ELSE COALESCE(returned_jobs,0) END),0)
               FROM hirebase_usage_ledger WHERE created_at>=? GROUP BY provider""", (cutoff,)
        ).fetchall()
    local_monthly = int(monthly[0] or 0)
    return {
        "api_key_configured": hirebase.api_key_configured(),
        "source_enabled": bool(config.get("source_enabled", {}).get("hirebase", False)),
        "poll_seconds": int(config.get("poll_seconds", {}).get("hirebase", 86400)),
        "budget": {
            "monthly_hard_cap": HIREBASE_MAX_MONTHLY_JOBS,
            "daily_hard_cap": HIREBASE_MAX_DAILY_JOBS,
            "per_provider_daily_cap": HIREBASE_PROVIDER_DAILY_JOBS,
            "free_plan_monthly_allowance": 500,
            "safety_buffer": 100,
            "locally_counted_period_jobs": local_monthly,
            "locally_counted_today_jobs": int(daily[0] or 0),
            "remaining_local_monthly_budget": max(0, HIREBASE_MAX_MONTHLY_JOBS - local_monthly),
            "remaining_local_daily_budget": max(0, HIREBASE_MAX_DAILY_JOBS - int(daily[0] or 0)),
            "provider_today": {str(row[0]): int(row[1] or 0) for row in providers},
            "last_query_at": monthly[2],
            "last_metered_remaining": monthly[4],
            "ledger_rows": int(monthly[1] or 0),
        },
        "note": "Hirebase remains optional and disabled by default. Usage counts include reserved/uncertain requests until reconciled.",
    }


@app.post("/api/hirebase/estimate", dependencies=[Depends(require_admin)])
def hirebase_estimate(payload: dict[str, Any]):
    """Estimate one small provider query without spending job-result credits."""
    provider = str(payload.get("provider") or "").strip().lower()
    limit = payload.get("limit", HIREBASE_PROVIDER_LIMIT)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= HIREBASE_PROVIDER_LIMIT:
        raise HTTPException(status_code=422, detail=f"limit must be between 1 and {HIREBASE_PROVIDER_LIMIT}.")
    try:
        query = hirebase.provider_query(provider, limit=limit)
        cost = hirebase.estimate(query)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except hirebase.HirebaseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "provider": provider, "estimated_job_credits": cost,
        "result_limit": limit, "estimate_costs_job_credits": 0,
        "query_scope": "public employer postings in India; global ingestion, no user profile filters",
        "search_spends_credits": True,
    }


@app.get("/api/source-status/summary", dependencies=[Depends(require_admin)])
def source_status_summary():
    """Return the reduced source summary to administrators only."""
    config = get_config()
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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


class ApplicationCreateRequest(BaseModel):
    job_id: int = Field(gt=0)
    applied_at: str | None = Field(default=None, max_length=64)
    status: str = "Applied"
    notes: str = Field(default="", max_length=user_applications.MAX_NOTES_LENGTH)


class ApplicationUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = Field(default=None, max_length=user_applications.MAX_NOTES_LENGTH)


class ApplicationImportRequest(BaseModel):
    applications: list[dict[str, Any]] = Field(max_length=user_applications.MAX_IMPORT_RECORDS)


@app.get("/api/applications")
def list_user_applications(user: dict[str, Any] = Depends(require_authenticated)):
    return {"applications": user_applications.list_for_user(DB_PATH, user["id"])}


@app.post("/api/applications")
def create_user_application(
    payload: ApplicationCreateRequest,
    response: Response,
    user: dict[str, Any] = Depends(require_authenticated),
):
    try:
        application, created = user_applications.create(
            DB_PATH, user["id"], payload.job_id,
            applied_at=payload.applied_at, status=payload.status, notes=payload.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.status_code = 201 if created else 200
    return {"application": application, "created": created}


@app.patch("/api/applications/{application_id}")
def update_user_application(
    application_id: int,
    payload: ApplicationUpdateRequest,
    user: dict[str, Any] = Depends(require_authenticated),
):
    fields = payload.model_fields_set
    if not fields or not fields.issubset({"status", "notes"}):
        raise HTTPException(status_code=422, detail="Provide application status or notes to update.")
    try:
        application = user_applications.update(
            DB_PATH, user["id"], application_id,
            status=payload.status if "status" in fields else None,
            notes=payload.notes if "notes" in fields else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if application is None:
        raise HTTPException(status_code=404, detail="Application record not found.")
    return {"application": application}


@app.delete("/api/applications/{application_id}", status_code=204)
def delete_user_application(
    application_id: int,
    user: dict[str, Any] = Depends(require_authenticated),
):
    if not user_applications.delete(DB_PATH, user["id"], application_id):
        raise HTTPException(status_code=404, detail="Application record not found.")
    return Response(status_code=204)


@app.post("/api/applications/import")
def import_user_applications(
    payload: ApplicationImportRequest,
    user: dict[str, Any] = Depends(require_authenticated),
):
    try:
        return user_applications.import_legacy(DB_PATH, user["id"], payload.applications)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
    with connect_sqlite(DB_PATH) as conn:
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
