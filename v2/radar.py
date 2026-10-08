from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
import warnings
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("JOB_RADAR_DB", ROOT / "jobs.db"))
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

TARGET_ROLES = [str(x).lower() for x in CONFIG.get("target_roles", [])]
SKILLS = [str(x).lower() for x in CONFIG.get("skills", [])]
MATCH_THRESHOLD = int(CONFIG.get("match_threshold", 55))

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
        conn.commit()


def upsert_jobs(jobs: list[dict[str, Any]]) -> int:
    new_count = 0
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        for j in jobs:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE source=? AND source_job_id=?",
                (j["source"], j["source_job_id"])
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE jobs SET last_seen_at=?, source_posted_at=COALESCE(?, source_posted_at),
                    posted_precision=CASE WHEN ?='minute' THEN ? ELSE posted_precision END,
                    discovery_latency_seconds=COALESCE(?, discovery_latency_seconds),
                    description=CASE WHEN length(?) > length(description) THEN ? ELSE description END
                    WHERE id=?
                """, (
                    j["discovered_at"], j["source_posted_at"], j["posted_precision"],
                    j["posted_precision"], j["discovery_latency_seconds"],
                    j["description"], j["description"], existing[0]
                ))
            else:
                conn.execute("""
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


def title_allowed(title: str) -> bool:
    excluded = [
        "senior", "sr", "staff", "principal", "director", "manager",
        "lead", "head", "architect", "intern", "vp", "vice president"
    ]
    return not phrase_hits(excluded, title)


def location_allowed(location: str) -> bool:
    value = normalize_phrase(location)
    return (
        re.search(r"\bbengaluru\b", value) is not None
        or re.search(r"\bbangalore\b", value) is not None
        or re.search(r"\bgurugram\b", value) is not None
        or re.search(r"\bgurgaon\b", value) is not None
        or re.search(r"\bdelhi\b", value) is not None
        or (
            "remote" in value
            and ("india" in value or not any(
                x in value for x in ["usa", "united states", "canada", "uk", "europe", "australia"]
            ))
        )
    )


def extract_experience(text: str) -> tuple[float | None, float | None]:
    value = normalize_phrase(text)
    ranges = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        value,
    )
    if ranges:
        lows = [float(a) for a, _ in ranges]
        highs = [float(b) for _, b in ranges]
        return min(lows), max(highs)

    plus = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", value)
    if plus:
        years = float(plus.group(1))
        return years, None

    singles = re.findall(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", value)
    if singles:
        years = [float(x) for x in singles]
        return min(years), max(years)

    return None, None


def match_details(job: dict[str, Any]) -> dict[str, Any]:
    title = (job.get("title") or "")
    description = (job.get("description") or "")
    combined = f"{title} {description}"

    reasons: list[str] = []

    if not title_allowed(title):
        return {
            "match": False,
            "score": 0,
            "reasons": ["excluded senior/leadership title"],
            "experience_min_years": None,
            "experience_max_years": None,
        }

    if not location_allowed(job.get("location") or ""):
        return {
            "match": False,
            "score": 0,
            "reasons": ["location outside configured cities/remote India"],
            "experience_min_years": None,
            "experience_max_years": None,
        }

    score = 20
    reasons.append("target location")

    title_role_hits = phrase_hits(TARGET_ROLES, title)
    role_hits = title_role_hits
    role_source = "title"
    if not role_hits:
        role_hits = phrase_hits(TARGET_ROLES, description)
        role_source = "description"

    if role_hits:
        role_bonus = 30 if role_source == "title" else 25
        score += role_bonus
        reasons.append(f"role ({role_source}): {role_hits[0]}")
    else:
        reasons.append("no configured target-role match")

    skill_hits = phrase_hits(SKILLS, combined)
    if skill_hits:
        bonus = min(30, 6 * len(skill_hits))
        score += bonus
        reasons.append("skills: " + ", ".join(skill_hits[:5]))

    exp_min, exp_max = extract_experience(combined)
    candidate_years = float(CONFIG.get("candidate_experience_years", 2))
    max_years = float(CONFIG.get("max_experience_years", 3))

    if exp_min is not None or exp_max is not None:
        effective_min = exp_min if exp_min is not None else exp_max

        # The candidate must satisfy the advertised minimum experience.
        if effective_min is not None and effective_min > candidate_years:
            return {
                "match": False,
                "score": 0,
                "reasons": [
                    f"experience minimum {effective_min:g} years exceeds candidate {candidate_years:g} years"
                ],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        # Do not surface roles whose stated range extends beyond the
        # configured maximum acceptable experience.
        if exp_max is not None and exp_max > max_years:
            return {
                "match": False,
                "score": 0,
                "reasons": [
                    f"experience range exceeds configured maximum of {max_years:g} years"
                ],
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
            }

        score += 15
        reasons.append(
            f"experience compatible: candidate {candidate_years:g} years; job {effective_min:g}"
            + (f"-{exp_max:g}" if exp_max is not None else "+")
        )
    else:
        reasons.append("experience not stated in captured source data")

    return {
        "match": score >= MATCH_THRESHOLD and bool(role_hits),
        "score": min(score, 100),
        "reasons": reasons,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
    }


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


def linkedin_collect() -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    endpoint = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    # Keep a six-hour safety window so a transient failure does not create a
    # permanent hole in the feed. We still request newest-first and dedupe by
    # LinkedIn job id.
    for query in CONFIG["linkedin_queries"]:
        for location in CONFIG["locations"]:
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


def instahyre_collect() -> list[dict[str, Any]]:
    endpoint = "https://www.instahyre.com/api/v1/job_search/"
    response = requests.get(
        endpoint,
        params={"jobLocations": "Bangalore", "limit": 35},
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
    "naukri": naukri_collect,
    "instahyre": instahyre_collect,
}


def run_source(source: str) -> None:
    if source_state.get(source, {}).get("running"):
        log.warning("%s: previous run still active; skipping this cycle", source)
        return

    started_at = now()
    source_state.setdefault(source, {})["running"] = True
    try:
        jobs = COLLECTORS[source]()
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
    intervals = CONFIG["poll_seconds"]
    while not stop_event.is_set():
        current = time.monotonic()
        for name in COLLECTORS:
            if current >= next_run[name] and not source_state.get(name, {}).get("running"):
                next_run[name] = current + intervals[name]
                asyncio.create_task(asyncio.to_thread(run_source, name))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=2)
        except asyncio.TimeoutError:
            pass


@app.on_event("startup")
async def startup() -> None:
    init_db()
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


@app.get("/api/jobs")
def jobs(minutes: int = 60, limit: int = 100):
    minutes = max(1, min(minutes, 1440))
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
        details = match_details(item)
        item["likely_match"] = details["match"]
        item["match_score"] = details["score"]
        item["match_reasons"] = details["reasons"]
        item["experience_min_years"] = details["experience_min_years"]
        item["experience_max_years"] = details["experience_max_years"]
        result.append(item)
    return {"jobs": result}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)
