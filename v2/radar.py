from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
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

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from fastapi import FastAPI, Header, HTTPException
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

app = FastAPI(title="Job Radar V2", version="2.0.0")
db_lock = threading.Lock()
started = time.monotonic()
source_state: dict[str, dict[str, Any]] = {}
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

    # Version 3 makes Instahyre opt-in. Any runtime config created before
    # this migration did not have a reliable Instahyre feed, so disable it
    # once while preserving all other user settings.
    if current_version < 3 <= default_version:
        merged.setdefault("source_enabled", {})["instahyre"] = False

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

    source_enabled = config.get("source_enabled", {})
    if not isinstance(source_enabled, dict):
        raise HTTPException(status_code=422, detail="source_enabled must be an object.")
    config["source_enabled"] = {
        "linkedin": bool(source_enabled.get("linkedin", True)),
        "naukri": bool(source_enabled.get("naukri", True)),
        "instahyre": bool(source_enabled.get("instahyre", True)),
    }

    poll_seconds = config.get("poll_seconds", {})
    if not isinstance(poll_seconds, dict):
        raise HTTPException(status_code=422, detail="poll_seconds must be an object.")
    config["poll_seconds"] = {
        name: max(60, int(poll_seconds.get(name, default)))
        for name, default in {
            "linkedin": 120,
            "naukri": 600,
            "instahyre": 600,
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


def now() -> dt.datetime:
    return dt.datetime.now(UTC)


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
    text = str(value).strip().lower()
    if text in {"just now", "now", "today"}:
        return base
    if text == "yesterday":
        return base - dt.timedelta(days=1)
    m = re.search(r"(\d+)\s*(minute|min|hour|hr|day|week)s?\s*(?:ago)?", text)
    if not m:
        try:
            parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
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
               j.id AS representative_job_id, j.company, j.title, j.location, j.url,
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
) -> int:
    identity = canonical_identity(job)
    canonical_url = identity["url_norm"] or None
    cur = conn.execute("""
        INSERT INTO canonical_opportunities (
            canonical_url, company_norm, title_norm, location_norm,
            representative_job_id, first_seen_at, last_seen_at, identity_version
        ) VALUES (?,?,?,?,?,?,?,1)
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
    return canonical_id


def _assign_canonical(conn: sqlite3.Connection, job_id: int) -> tuple[int, str, int]:
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
    for candidate in _candidate_canonical_groups(conn, job):
        candidate_source = candidate.get("representative_source")
        same_source = candidate_source and candidate_source == job.get("source")
        same_url = canonicalize_url(job.get("url", "")) and (
            canonicalize_url(job.get("url", "")) == canonicalize_url(candidate.get("canonical_url", ""))
        )
        if same_source and not same_url:
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

    new_id = _create_canonical_group(conn, job_id, job, "new", 0)
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
    conn.execute("DELETE FROM canonical_opportunities")


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
            _assign_canonical(conn, int(row["id"]))
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
        _ensure_column(conn, "jobs", "canonical_match_confidence", "INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_canonical ON jobs(canonical_opportunity_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canonical_lookup ON canonical_opportunities(company_norm, location_norm)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canonical_url ON canonical_opportunities(canonical_url)")
        conn.commit()
    backfill_canonical_opportunities()


def upsert_jobs(jobs: list[dict[str, Any]]) -> int:
    new_count = 0
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        for j in jobs:
            existing = conn.execute(
                "SELECT id, canonical_opportunity_id FROM jobs WHERE source=? AND source_job_id=?",
                (j["source"], j["source_job_id"])
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE jobs SET last_seen_at=?, source_posted_at=COALESCE(?, source_posted_at),
                    posted_precision=CASE WHEN ?='minute' THEN ? ELSE posted_precision END,
                    discovery_latency_seconds=COALESCE(?, discovery_latency_seconds),
                    description=CASE WHEN length(?) > length(description) THEN ? ELSE description
                    END
                    WHERE id=?
                """, (
                    j["discovered_at"], j["source_posted_at"], j["posted_precision"],
                    j["posted_precision"], j["discovery_latency_seconds"],
                    j["description"], j["description"], existing[0]
                ))
                if not existing[1]:
                    _assign_canonical(conn, int(existing[0]))
            else:
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
                new_count += 1
        conn.commit()
    return new_count

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
    if config.get("remote_only") and not phrase_hits(["remote"], value):
        return False
    terms = location_terms(config)
    return any(phrase_hits([term], value) for term in terms)




def extract_experience(text: str) -> tuple[float | None, float | None]:
    raw = str(text or "").lower().replace("–", "-").replace("—", "-")
    raw = re.sub(r"\s+", " ", raw).strip()

    ranges = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        raw,
    )
    if ranges:
        lows = [float(a) for a, _ in ranges]
        highs = [float(b) for _, b in ranges]
        return min(lows), max(highs)

    plus = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", raw)
    if plus:
        years = float(plus.group(1))
        return years, None

    normalized = normalize_phrase(raw)
    singles = re.findall(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", normalized)
    if singles:
        years = [float(x) for x in singles]
        return min(years), max(years)

    return None, None


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

    title_role_hits = phrase_hits(config.get("target_roles", []), title)
    role_hits = title_role_hits
    role_source = "title"
    if not role_hits:
        role_hits = phrase_hits(config.get("target_roles", []), description)
        role_source = "description"

    if role_hits:
        role_bonus = 30 if role_source == "title" else 25
        score += role_bonus
        reasons.append(f"role ({role_source}): {role_hits[0]}")
    else:
        reasons.append("no configured target-role match")

    skill_hits = phrase_hits(config.get("skills", []), combined)
    if skill_hits:
        score += min(30, 6 * len(skill_hits))
        reasons.append("skills: " + ", ".join(skill_hits[:5]))

    exp_min, exp_max = extract_experience(combined)
    candidate_years = config.get("candidate_experience_years")
    max_years = float(config.get("max_experience_years", 3))
    minimum_job_years = config.get("min_experience_years")

    if exp_min is not None or exp_max is not None:
        effective_min = exp_min if exp_min is not None else exp_max

        if candidate_years is not None and effective_min is not None and effective_min > float(candidate_years):
            return {
                "match": False,
                "score": 0,
                "reasons": [f"experience minimum {effective_min:g} exceeds candidate {float(candidate_years):g} years"],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        if minimum_job_years is not None and exp_max is not None and exp_max < float(minimum_job_years):
            return {
                "match": False,
                "score": 0,
                "reasons": [f"job maximum experience {exp_max:g} is below configured minimum {float(minimum_job_years):g} years"],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        if exp_max is not None and exp_max > max_years:
            return {
                "match": False,
                "score": 0,
                "reasons": [f"experience range exceeds configured maximum of {max_years:g} years"],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        score += 15
        experience_label = f"{effective_min:g}" + (f"-{exp_max:g}" if exp_max is not None else "+")
        candidate_label = f"{float(candidate_years):g} years" if candidate_years is not None else "configured profile"
        reasons.append(f"experience compatible: candidate {candidate_label}; job {experience_label}")
    else:
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


def _linkedin_request(endpoint: str, params: dict[str, Any]) -> requests.Response:
    for attempt in range(3):
        response = requests.get(endpoint, params=params, headers=UA, timeout=25)
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            return response
        wait = min(30, 2 ** attempt * 2)
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            wait = min(60, int(retry_after))
        time.sleep(wait)
    response.raise_for_status()
    return response


def linkedin_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    endpoint = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    # Keep a six-hour safety window so a transient failure does not create a
    # permanent hole in the feed. We still request newest-first and dedupe by
    # LinkedIn job id.
    for query in config.get("linkedin_queries", []):
        for location in config.get("locations", []):
            for start in (0, 10):
                params = {
                    "keywords": query,
                    "location": location,
                    "f_TPR": "r21600",
                    "sortBy": "DD",
                    "start": start,
                }
                response = _linkedin_request(endpoint, params)
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("li")
                if not cards:
                    break
                for card in cards:
                    link = card.select_one("a.base-card__full-link") or card.select_one(
                        "a[href*='/jobs/view/']"
                    )
                    title = card.select_one("h3.base-search-card__title")
                    company = card.select_one("h4.base-search-card__subtitle")
                    loc = card.select_one("span.job-search-card__location")
                    posted = card.select_one("time")
                    if not link or not title:
                        continue
                    url = (link.get("href") or "").split("?")[0]
                    match = re.search(r"(?:-|/)(\d{8,})$", url)
                    source_id = match.group(1) if match else hashlib.sha1(
                        url.encode()
                    ).hexdigest()[:20]
                    visible = posted.get_text(" ", strip=True) if posted else ""
                    posted_at = parse_relative(visible)
                    precision = "minute" if re.search(
                        r"(just now|\d+\s*(?:minute|min|hour|hr)s?\s*ago)",
                        visible.lower(),
                    ) else "date"
                    if not posted_at and posted and posted.get("datetime"):
                        posted_at = parse_relative(posted.get("datetime"))
                    jobs.append(normalize_job(
                        "linkedin", source_id,
                        company.get_text(" ", strip=True) if company else "",
                        title.get_text(" ", strip=True),
                        loc.get_text(" ", strip=True) if loc else "",
                        url, posted_at, precision,
                        card.get_text(" ", strip=True),
                    ))
                if len(cards) < 10:
                    break
    return jobs


NAUKRI_RELAY_URL = (
    "https://raw.githubusercontent.com/AvinashBhalla/job-beeper/naukri-relay/"
    "dashboard/data/naukri_relay.json"
)


def naukri_collect() -> list[dict[str, Any]]:
    response = requests.get(
        NAUKRI_RELAY_URL,
        params={"t": int(time.time())},
        headers=UA,
        timeout=20,
    )
    response.raise_for_status()
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
        if posted_at and posted_at.tzinfo:
            job["discovery_latency_seconds"] = max(
                0, int((collected_at - posted_at).total_seconds())
            )
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


COLLECTORS = {
    "linkedin": linkedin_collect,
    "naukri": lambda config: naukri_collect(),
    "instahyre": instahyre_collect,
}


def run_source(source: str, config: dict[str, Any]) -> None:
    if source_state.get(source, {}).get("running"):
        log.warning("%s: previous run still active; skipping this cycle", source)
        return

    started_at = now()
    source_state.setdefault(source, {})["running"] = True
    try:
        jobs = COLLECTORS[source](config)
        new_jobs = upsert_jobs(jobs)
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
    ensure_config_token()
    app.state.scheduler_task = asyncio.create_task(scheduler())


@app.on_event("shutdown")
async def shutdown() -> None:
    stop_event.set()
    task = getattr(app.state, "scheduler_task", None)
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
    return {"config": saved, "runtime_path": str(RUNTIME_CONFIG_PATH)}


@app.get("/api/source-status")
def source_status():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT source, MAX(finished_at), SUM(jobs_seen), SUM(new_jobs)
            FROM source_runs GROUP BY source ORDER BY source
        """).fetchall()
    return {
        "sources": [
            {
                "source": r[0],
                "last_run": r[1],
                "jobs_seen": r[2] or 0,
                "new_jobs": r[3] or 0,
                "runtime": source_state.get(r[0], {}),
            }
            for r in rows
        ]
    }


@app.get("/api/dedupe-candidates")
def dedupe_candidates(limit: int = 100):
    limit = max(1, min(limit, 500))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, source, source_job_id, company, title, location, url, description
            FROM jobs
            WHERE source IN ('linkedin', 'naukri', 'instahyre')
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
def opportunities(minutes: int = 60, limit: int = 100):
    minutes = max(1, min(minutes, 10080))
    limit = max(1, min(limit, 500))
    cutoff = iso(now() - dt.timedelta(minutes=minutes))
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
def jobs(minutes: int = 60, limit: int = 100):
    config = get_config()
    minutes = max(1, min(minutes, 10080))
    limit = max(1, min(limit, 500))
    cutoff = iso(now() - dt.timedelta(minutes=minutes))
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
