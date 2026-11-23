"""Polite, candidate-only discovery from Common Crawl and public sitemaps.

No source is activated and no employer record is created by this module.
Common Crawl is queried one request at a time with a shared SQLite lease and
persistent cooldown. Sitemap scans are host-scoped, robots-aware and bounded.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import uuid
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

from v2 import board_discovery
from v2.sqlite_store import DB_LOCK, connect

UTC = dt.timezone.utc
COMMONCRAWL_CATALOGUE_URL = "https://index.commoncrawl.org/collinfo.json"
COMMONCRAWL_INDEX_BASE = "https://index.commoncrawl.org"
COMMONCRAWL_USER_AGENT = "JobBeeper-GlobalDiscovery/1.0 (+public-candidate-discovery)"
COMMONCRAWL_CATALOGUE_TTL_SECONDS = 24 * 60 * 60
COMMONCRAWL_MIN_INTERVAL_SECONDS = 60
COMMONCRAWL_COOLDOWN_SECONDS = 24 * 60 * 60
COMMONCRAWL_LEASE_SECONDS = 180
COMMONCRAWL_TIMEOUT_SECONDS = 20
COMMONCRAWL_CATALOGUE_MAX_BYTES = 1_000_000
COMMONCRAWL_RESPONSE_MAX_BYTES = 1_500_000
COMMONCRAWL_MAX_RECORDS = 200
COMMONCRAWL_DOMAIN = {
    "workday": "myworkdayjobs.com",
    "keka": "keka.com",
    "darwinbox": "darwinbox.in",
    "recruitee": "recruitee.com",
    "teamtailor": "teamtailor.com",
    "breezy": "breezy.hr",
    "bamboohr": "bamboohr.com",
    "jobvite": "jobs.jobvite.com",
    "hireology": "careers.hireology.com",
    "rippling": "ats.rippling.com",
    "oraclecloud": "oraclecloud.com",
    "avature": "avature.net",
    "icims": "icims.com",
    "freshteam": "freshteam.com",
    "hrsmart": "hrsmart.com",
    "ukg": "ultipro.com",
    "zoho": "zohorecruit.com",
    "taleo": "taleo.net",
    "peoplestrong": "peoplestrong.com",
}
COMMONCRAWL_PROVIDERS = tuple(COMMONCRAWL_DOMAIN)
SITEMAP_USER_AGENT = board_discovery.USER_AGENT
SITEMAP_MAX_BYTES = 1_500_000
SITEMAP_ROBOTS_MAX_BYTES = 256_000
SITEMAP_MAX_DOCUMENTS = 3
SITEMAP_MAX_LOCATIONS = 2_000
SITEMAP_MAX_CAREER_PAGES = 4
SITEMAP_HOST_MIN_INTERVAL_SECONDS = 15 * 60
SITEMAP_HOST_COOLDOWN_SECONDS = 24 * 60 * 60
SITEMAP_TIMEOUT_SECONDS = 10
SITEMAP_MAX_REDIRECTS = 2
SITEMAP_MAX_CRAWL_DELAY_SECONDS = 30

CandidateImporter = Callable[[dict[str, Any]], dict[str, Any]]


def _utc(value: dt.datetime | None = None) -> dt.datetime:
    current = value or dt.datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _iso(value: dt.datetime | None = None) -> str:
    return _utc(value).isoformat()


def _parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def init_schema(db_path: str) -> None:
    """Create discovery request state and audit tables; safe to call repeatedly."""
    timestamp = _iso()
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_ats_discovery_state (
                id INTEGER PRIMARY KEY CHECK(id=1),
                cdx_crawl_id TEXT,
                cdx_crawl_from TEXT,
                cdx_crawl_to TEXT,
                cdx_catalogue_fetched_at TEXT,
                cdx_catalogue_reference TEXT,
                cdx_next_provider TEXT NOT NULL DEFAULT 'workday',
                cdx_next_request_at TEXT,
                cdx_cooldown_until TEXT,
                cdx_cooldown_reason TEXT,
                cdx_lease_token TEXT,
                cdx_lease_until TEXT,
                cdx_last_started_at TEXT,
                cdx_last_finished_at TEXT,
                cdx_last_outcome TEXT,
                cdx_last_provider TEXT,
                cdx_last_http_status INTEGER,
                cdx_last_response_records INTEGER NOT NULL DEFAULT 0,
                cdx_last_candidates INTEGER NOT NULL DEFAULT 0,
                cdx_last_inserted INTEGER NOT NULL DEFAULT 0,
                cdx_last_updated INTEGER NOT NULL DEFAULT 0,
                cdx_last_skipped INTEGER NOT NULL DEFAULT 0,
                cdx_last_truncated INTEGER NOT NULL DEFAULT 0,
                cdx_last_error_type TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO global_ats_discovery_state(id, cdx_next_provider, updated_at)
            VALUES(1, 'workday', ?)
        """, (timestamp,))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_ats_discovery_host_budget (
                host_key TEXT PRIMARY KEY,
                next_allowed_at TEXT,
                cooldown_until TEXT,
                lease_token TEXT,
                lease_until TEXT,
                last_scanned_at TEXT,
                last_outcome TEXT,
                last_http_status INTEGER,
                request_count INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                last_error_type TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_ats_discovery_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                provider TEXT,
                crawl_id TEXT,
                host_key TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                http_status INTEGER,
                outcome TEXT NOT NULL,
                response_records INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                inserted_count INTEGER NOT NULL DEFAULT 0,
                updated_count INTEGER NOT NULL DEFAULT 0,
                preserved_terminal_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                truncated INTEGER NOT NULL DEFAULT 0,
                error_type TEXT,
                source_reference TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_global_discovery_runs_method
            ON global_ats_discovery_runs(method, started_at DESC)
        """)
        conn.commit()


def _bounded_response_body(response: Any, max_bytes: int) -> tuple[bytes, bool]:
    """Read a response body up to max_bytes; the caller must close the response."""
    chunks = bytearray()
    truncated = False
    iterator = getattr(response, "iter_content", None)
    if callable(iterator):
        try:
            for chunk in iterator(chunk_size=64 * 1024):
                if not chunk:
                    continue
                remaining = max_bytes + 1 - len(chunks)
                if remaining <= 0:
                    truncated = True
                    break
                chunks.extend(chunk[:remaining])
                if len(chunks) > max_bytes:
                    truncated = True
                    break
        except TypeError:
            body = getattr(response, "content", b"") or b""
            chunks.extend(body[: max_bytes + 1])
            truncated = len(body) > max_bytes
    else:
        body = getattr(response, "content", b"") or b""
        chunks.extend(body[: max_bytes + 1])
        truncated = len(body) > max_bytes
    if len(chunks) > max_bytes:
        del chunks[max_bytes:]
        truncated = True
    return bytes(chunks), truncated


def _close_response(response: Any) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        close()


def _catalogue_latest(payload: Any) -> dict[str, str]:
    if not isinstance(payload, list):
        raise ValueError("Common Crawl collection catalogue must be a JSON array.")
    entries: list[tuple[tuple[int, int], dict[str, str]]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        crawl_id = item.get("id")
        match = re.fullmatch(r"CC-MAIN-(\d{4})-(\d{2})", str(crawl_id or ""))
        if not match:
            continue
        # Do not accept a catalogue entry that points the worker at an arbitrary host.
        api = str(item.get("cdx-api") or "")
        if api:
            parsed = urlsplit(api)
            if parsed.scheme != "https" or parsed.hostname != "index.commoncrawl.org":
                continue
        entries.append(((int(match.group(1)), int(match.group(2))), {
            "id": str(crawl_id),
            "from": str(item.get("from") or ""),
            "to": str(item.get("to") or ""),
        }))
    if not entries:
        raise ValueError("Common Crawl catalogue contained no supported CC-MAIN collection.")
    entries.sort(key=lambda value: value[0], reverse=True)
    return entries[0][1]


def _candidate_records(
    body: bytes,
    provider: str,
    crawl_id: str,
    *,
    response_truncated: bool,
) -> tuple[list[dict[str, Any]], int, bool]:
    """Parse CDX JSONL into one low-confidence candidate per employer board."""
    text = body.decode("utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    response_records = 0
    candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
    truncated = response_truncated or len(lines) >= COMMONCRAWL_MAX_RECORDS
    for line in lines[:COMMONCRAWL_MAX_RECORDS]:
        try:
            record = json.loads(line)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        response_records += 1
        if str(record.get("status") or "") != "200":
            continue
        mime = str(record.get("mime") or record.get("mime_type") or "").lower()
        if not mime.startswith("text/html"):
            continue
        url = record.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        detected = board_discovery.detect_ats_board(url)
        if not detected or detected.get("provider") != provider:
            continue
        if provider not in COMMONCRAWL_PROVIDERS:
            continue
        host = str(detected.get("host") or urlsplit(url).hostname or "").lower().rstrip(".")
        board_key = str(detected.get("board_key") or "")
        if not host or not board_key:
            continue
        timestamp = str(record.get("timestamp") or "")
        if not re.fullmatch(r"\d{14}", timestamp):
            timestamp = ""
        filename = str(record.get("filename") or "")
        offset = str(record.get("offset") or "")
        length = str(record.get("length") or "")
        reference = f"{crawl_id};{filename};offset={offset};length={length}"
        if not filename:
            reference = f"{crawl_id};capture={timestamp or 'unknown'}"
        reference = reference[:2048]
        key = (provider, host, board_key.lower())
        candidate = {
            "board_url": url,
            "discovery_method": "commoncrawl_cdx",
            "source_reference": reference,
            "source_captured_at": timestamp or None,
        }
        previous = candidates.get(key)
        if previous is None or str(candidate.get("source_captured_at") or "") > str(previous.get("source_captured_at") or ""):
            candidates[key] = candidate
    return list(candidates.values()), response_records, truncated


def _state_row(conn: Any) -> dict[str, Any]:
    conn.row_factory = None
    row = conn.execute("SELECT * FROM global_ats_discovery_state WHERE id=1").fetchone()
    names = [item[0] for item in conn.execute("SELECT * FROM global_ats_discovery_state WHERE id=1").description]
    return dict(zip(names, row)) if row else {}


def _insert_run(
    conn: Any,
    *,
    method: str,
    provider: str | None,
    crawl_id: str | None,
    started_at: str,
    finished_at: str,
    http_status: int | None,
    outcome: str,
    response_records: int = 0,
    candidate_count: int = 0,
    ingestion: dict[str, Any] | None = None,
    truncated: bool = False,
    error_type: str | None = None,
    source_reference: str | None = None,
    host_key: str | None = None,
) -> None:
    ingestion = ingestion or {}
    conn.execute("""
        INSERT INTO global_ats_discovery_runs(
            method,provider,crawl_id,host_key,started_at,finished_at,http_status,
            outcome,response_records,candidate_count,inserted_count,updated_count,
            preserved_terminal_count,skipped_count,truncated,error_type,source_reference
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        method, provider, crawl_id, host_key, started_at, finished_at, http_status,
        outcome, response_records, candidate_count,
        int(ingestion.get("inserted", 0) or 0),
        int(ingestion.get("updated", 0) or 0),
        int(ingestion.get("preserved_terminal", 0) or 0),
        int(ingestion.get("skipped", 0) or 0),
        int(bool(truncated)), error_type, source_reference,
    ))


def _finish_cdx(
    db_path: str,
    token: str,
    *,
    started_at: dt.datetime,
    outcome: str,
    provider: str | None = None,
    crawl_id: str | None = None,
    http_status: int | None = None,
    response_records: int = 0,
    candidates: list[dict[str, Any]] | None = None,
    ingestion: dict[str, Any] | None = None,
    truncated: bool = False,
    error_type: str | None = None,
    cooldown_until: dt.datetime | None = None,
) -> None:
    finished = _utc()
    started_text = _iso(started_at)
    finished_text = _iso(finished)
    ingestion = ingestion or {}
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        state = conn.execute("SELECT cdx_lease_token FROM global_ats_discovery_state WHERE id=1").fetchone()
        if not state or state[0] != token:
            conn.rollback()
            return
        conn.execute("""
            UPDATE global_ats_discovery_state SET
                cdx_cooldown_until=?,cdx_cooldown_reason=?,cdx_lease_token=NULL,cdx_lease_until=NULL,
                cdx_last_finished_at=?,cdx_last_outcome=?,cdx_last_provider=?,
                cdx_last_http_status=?,cdx_last_response_records=?,cdx_last_candidates=?,
                cdx_last_inserted=?,cdx_last_updated=?,cdx_last_skipped=?,
                cdx_last_truncated=?,cdx_last_error_type=?,updated_at=?
            WHERE id=1 AND cdx_lease_token=?
        """, (
            _iso(cooldown_until) if cooldown_until else None,
            "Common Crawl rate limit (HTTP 503/429); automatic requests paused for 24 hours." if cooldown_until else None,
            finished_text, outcome, provider, http_status, response_records,
            len(candidates or []), int(ingestion.get("inserted", 0) or 0),
            int(ingestion.get("updated", 0) or 0),
            int(ingestion.get("skipped", 0) or 0),
            int(bool(truncated)), error_type, finished_text, token,
        ))
        _insert_run(
            conn, method="commoncrawl_cdx" if provider else "commoncrawl_catalogue",
            provider=provider, crawl_id=crawl_id, started_at=started_text,
            finished_at=finished_text, http_status=http_status, outcome=outcome,
            response_records=response_records, candidate_count=len(candidates or []),
            ingestion=ingestion, truncated=truncated, error_type=error_type,
            source_reference=(f"{crawl_id}-index" if crawl_id else COMMONCRAWL_CATALOGUE_URL),
        )
        conn.commit()


def _claim_cdx(db_path: str, current: dt.datetime) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
    token = uuid.uuid4().hex
    now_text = _iso(current)
    lease_until = _iso(current + dt.timedelta(seconds=COMMONCRAWL_LEASE_SECONDS))
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM global_ats_discovery_state WHERE id=1").fetchone()
        if row is None:
            conn.rollback()
            return None, None, {"outcome": "state_missing"}
        names = [item[0] for item in conn.execute("SELECT * FROM global_ats_discovery_state WHERE id=1").description]
        state = dict(zip(names, row))
        cooldown = _parse_iso(state.get("cdx_cooldown_until"))
        if cooldown and cooldown > current:
            conn.rollback()
            return None, state, {
                "outcome": "cooldown",
                "cooldown_until": _iso(cooldown),
                "retry_after_seconds": max(0, int((cooldown - current).total_seconds())),
            }
        lease = _parse_iso(state.get("cdx_lease_until"))
        if lease and lease > current:
            conn.rollback()
            return None, state, {"outcome": "busy", "lease_until": _iso(lease)}
        next_request = _parse_iso(state.get("cdx_next_request_at"))
        if next_request and next_request > current:
            conn.rollback()
            return None, state, {
                "outcome": "throttled",
                "next_request_at": _iso(next_request),
                "retry_after_seconds": max(0, int((next_request - current).total_seconds())),
            }
        conn.execute("""
            UPDATE global_ats_discovery_state SET
                cdx_lease_token=?,cdx_lease_until=?,cdx_next_request_at=?,cdx_last_started_at=?,updated_at=?
            WHERE id=1
        """, (
            token, lease_until,
            _iso(current + dt.timedelta(seconds=COMMONCRAWL_MIN_INTERVAL_SECONDS)),
            now_text, now_text,
        ))
        conn.commit()
        return token, state, None


def _read_json_response(response: Any, max_bytes: int) -> tuple[Any, bool, bytes]:
    try:
        body, truncated = _bounded_response_body(response, max_bytes)
        if truncated:
            raise ValueError("Common Crawl response exceeded the bounded response size.")
        return json.loads(body.decode("utf-8")), False, body
    finally:
        _close_response(response)


def _read_text_response(response: Any, max_bytes: int) -> tuple[str, bool, int]:
    status = int(getattr(response, "status_code", 0) or 0)
    try:
        body, truncated = _bounded_response_body(response, max_bytes)
        return body.decode("utf-8", errors="replace"), truncated, status
    finally:
        _close_response(response)


def run_commoncrawl_once(
    db_path: str,
    *,
    importer: CandidateImporter | None = None,
    requester: Any | None = None,
    at: dt.datetime | None = None,
) -> dict[str, Any]:
    """Perform at most one Common Crawl HTTP request and at most one provider query.

    First invocation with an expired collection cache refreshes collinfo.json only.
    A later invocation runs one provider query, rotating Workday/Keka/Darwinbox.
    No background loop or startup network call is installed by this module.
    """
    init_schema(db_path)
    current = _utc(at)
    token, state, blocked = _claim_cdx(db_path, current)
    if blocked:
        return blocked
    if not token or state is None:
        return {"outcome": "state_missing"}
    client = requester or requests.Session()
    started = current
    provider: str | None = None
    crawl_id = str(state.get("cdx_crawl_id") or "") or None
    http_status: int | None = None
    response_records = 0
    candidates: list[dict[str, Any]] = []
    ingestion: dict[str, Any] = {}
    truncated = False
    cooldown_until: dt.datetime | None = None
    outcome = "error"
    error_type: str | None = None
    try:
        catalogue_checked = _parse_iso(state.get("cdx_catalogue_fetched_at"))
        catalogue_fresh = bool(
            state.get("cdx_crawl_id") and catalogue_checked
            and (current - catalogue_checked).total_seconds() < COMMONCRAWL_CATALOGUE_TTL_SECONDS
        )
        if not catalogue_fresh:
            response = client.get(
                COMMONCRAWL_CATALOGUE_URL,
                headers={"User-Agent": COMMONCRAWL_USER_AGENT, "Accept": "application/json"},
                timeout=COMMONCRAWL_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
            )
            http_status = int(getattr(response, "status_code", 0) or 0)
            if http_status in {429, 503}:
                _close_response(response)
                cooldown_until = current + dt.timedelta(seconds=COMMONCRAWL_COOLDOWN_SECONDS)
                outcome = "global_cooldown"
                error_type = f"http_{http_status}"
            elif http_status != 200:
                _close_response(response)
                outcome = "catalogue_http_error"
                error_type = f"http_{http_status}"
            else:
                payload, _truncated, _body = _read_json_response(response, COMMONCRAWL_CATALOGUE_MAX_BYTES)
                latest = _catalogue_latest(payload)
                crawl_id = latest["id"]
                with DB_LOCK, connect(db_path) as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("""
                        UPDATE global_ats_discovery_state SET cdx_crawl_id=?,cdx_crawl_from=?,
                            cdx_crawl_to=?,cdx_catalogue_fetched_at=?,cdx_catalogue_reference=?,
                            updated_at=? WHERE id=1 AND cdx_lease_token=?
                    """, (
                        crawl_id, latest["from"], latest["to"], _iso(current),
                        COMMONCRAWL_CATALOGUE_URL, _iso(current), token,
                    ))
                    conn.commit()
                outcome = "catalogue_refreshed"
        else:
            next_provider = str(state.get("cdx_next_provider") or COMMONCRAWL_PROVIDERS[0])
            provider = next_provider if next_provider in COMMONCRAWL_PROVIDERS else COMMONCRAWL_PROVIDERS[0]
            crawl_id = str(state["cdx_crawl_id"])
            domain = COMMONCRAWL_DOMAIN[provider]
            response = client.get(
                f"{COMMONCRAWL_INDEX_BASE}/{crawl_id}-index",
                params={
                    "url": domain,
                    "matchType": "domain",
                    "filter": ["=status:200", "=mime:text/html"],
                    "output": "json",
                    "fl": "url,timestamp,status,mime,filename,offset,length",
                    "limit": COMMONCRAWL_MAX_RECORDS,
                    "collapse": "urlkey",
                },
                headers={"User-Agent": COMMONCRAWL_USER_AGENT, "Accept": "application/json"},
                timeout=COMMONCRAWL_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,
            )
            http_status = int(getattr(response, "status_code", 0) or 0)
            if http_status in {429, 503}:
                _close_response(response)
                cooldown_until = current + dt.timedelta(seconds=COMMONCRAWL_COOLDOWN_SECONDS)
                outcome = "global_cooldown"
                error_type = f"http_{http_status}"
            elif http_status != 200:
                _close_response(response)
                outcome = "cdx_http_error"
                error_type = f"http_{http_status}"
            else:
                try:
                    body, truncated = _bounded_response_body(response, COMMONCRAWL_RESPONSE_MAX_BYTES)
                finally:
                    _close_response(response)
                response_records = len([line for line in body.splitlines() if line.strip()])
                candidates, parsed_records, parsed_truncated = _candidate_records(
                    body, provider, crawl_id, response_truncated=truncated,
                )
                response_records = parsed_records
                truncated = truncated or parsed_truncated
                if importer and candidates:
                    imported = importer({"candidates": candidates})
                    ingestion = imported if isinstance(imported, dict) else {}
                next_provider = COMMONCRAWL_PROVIDERS[
                    (COMMONCRAWL_PROVIDERS.index(provider) + 1) % len(COMMONCRAWL_PROVIDERS)
                ]
                with DB_LOCK, connect(db_path) as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("""
                        UPDATE global_ats_discovery_state SET cdx_next_provider=?,updated_at=?
                        WHERE id=1 AND cdx_lease_token=?
                    """, (next_provider, _iso(current), token))
                    conn.commit()
                outcome = "candidates_imported" if candidates else "no_candidates"
        _finish_cdx(
            db_path, token, started_at=started, outcome=outcome, provider=provider,
            crawl_id=crawl_id, http_status=http_status, response_records=response_records,
            candidates=candidates, ingestion=ingestion, truncated=truncated,
            error_type=error_type, cooldown_until=cooldown_until,
        )
        return {
            "outcome": outcome, "provider": provider, "crawl_id": crawl_id,
            "http_status": http_status, "response_records": response_records,
            "candidate_count": len(candidates), "imported": ingestion,
            "truncated": truncated,
            "cooldown_until": _iso(cooldown_until) if cooldown_until else None,
            "next_provider": None if provider is None else COMMONCRAWL_PROVIDERS[
                (COMMONCRAWL_PROVIDERS.index(provider) + 1) % len(COMMONCRAWL_PROVIDERS)
            ],
        }
    except Exception as exc:
        outcome = "request_error"
        error_type = type(exc).__name__
        _finish_cdx(
            db_path, token, started_at=started, outcome=outcome, provider=provider,
            crawl_id=crawl_id, http_status=http_status, response_records=response_records,
            candidates=candidates, ingestion=ingestion, truncated=truncated,
            error_type=error_type,
        )
        return {
            "outcome": outcome, "provider": provider, "crawl_id": crawl_id,
            "http_status": http_status, "error_type": error_type,
            "candidate_count": len(candidates), "truncated": truncated,
        }
    finally:
        close = getattr(client, "close", None)
        if requester is None and callable(close):
            close()


def _claim_sitemap_host(db_path: str, host: str, current: dt.datetime) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
    token = uuid.uuid4().hex
    timestamp = _iso(current)
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            INSERT OR IGNORE INTO global_ats_discovery_host_budget(host_key,updated_at)
            VALUES(?,?)
        """, (host, timestamp))
        row = conn.execute(
            "SELECT next_allowed_at,cooldown_until,lease_until FROM global_ats_discovery_host_budget WHERE host_key=?",
            (host,),
        ).fetchone()
        if row:
            next_allowed = _parse_iso(row[0])
            cooldown = _parse_iso(row[1])
            lease = _parse_iso(row[2])
            if cooldown and cooldown > current:
                conn.rollback()
                return None, None, {"outcome": "host_cooldown", "cooldown_until": _iso(cooldown)}
            if lease and lease > current:
                conn.rollback()
                return None, None, {"outcome": "host_busy", "lease_until": _iso(lease)}
            if next_allowed and next_allowed > current:
                conn.rollback()
                return None, None, {
                    "outcome": "host_throttled",
                    "next_allowed_at": _iso(next_allowed),
                    "retry_after_seconds": max(0, int((next_allowed - current).total_seconds())),
                }
        conn.execute("""
            UPDATE global_ats_discovery_host_budget SET lease_token=?,lease_until=?,updated_at=?
            WHERE host_key=?
        """, (
            token, _iso(current + dt.timedelta(minutes=5)), timestamp, host,
        ))
        conn.commit()
    return token, {}, None


def _finish_sitemap_host(
    db_path: str,
    host: str,
    token: str,
    *,
    current: dt.datetime,
    outcome: str,
    request_count: int,
    candidate_count: int,
    http_status: int | None = None,
    error_type: str | None = None,
    cooldown: bool = False,
    next_allowed_seconds: int | None = None,
) -> None:
    timestamp = _iso(current)
    allowed_seconds = max(SITEMAP_HOST_MIN_INTERVAL_SECONDS, int(next_allowed_seconds or 0))
    allowed = current + dt.timedelta(seconds=allowed_seconds)
    cool_until = current + dt.timedelta(seconds=SITEMAP_HOST_COOLDOWN_SECONDS) if cooldown else None
    with DB_LOCK, connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            UPDATE global_ats_discovery_host_budget SET next_allowed_at=?,
                cooldown_until=CASE WHEN ? IS NOT NULL THEN ? ELSE cooldown_until END,
                lease_token=NULL,lease_until=NULL,last_scanned_at=?,last_outcome=?,
                last_http_status=?,request_count=request_count+?,candidate_count=?,last_error_type=?,updated_at=?
            WHERE host_key=? AND lease_token=?
        """, (
            _iso(allowed), _iso(cool_until) if cool_until else None,
            _iso(cool_until) if cool_until else None, timestamp, outcome, http_status,
            max(0, request_count), max(0, candidate_count), error_type, timestamp, host, token,
        ))
        _insert_run(
            conn, method="sitemap", provider=None, crawl_id=None, host_key=host,
            started_at=timestamp, finished_at=timestamp, http_status=http_status,
            outcome=outcome, candidate_count=candidate_count, error_type=error_type,
            source_reference=host,
        )
        conn.commit()


def _bounded_same_host_get(
    requester: Any,
    url: str,
    allowed_host: str,
    *,
    max_bytes: int,
    user_agent: str,
) -> tuple[str, int, dict[str, str], bytes, bool]:
    current = board_discovery._public_https_url(url)
    if (urlsplit(current).hostname or "").lower().rstrip(".") != allowed_host:
        raise ValueError("Discovery fetch must remain on the submitted public host.")
    for _ in range(SITEMAP_MAX_REDIRECTS + 1):
        response = requester.get(
            current,
            headers={"User-Agent": user_agent, "Accept": "text/plain,application/xml,text/html,*/*;q=0.2"},
            timeout=SITEMAP_TIMEOUT_SECONDS,
            allow_redirects=False,
            stream=True,
        )
        status = int(getattr(response, "status_code", 0) or 0)
        headers = {str(k).lower(): str(v) for k, v in dict(getattr(response, "headers", {}) or {}).items()}
        if status in {301, 302, 303, 307, 308}:
            location = headers.get("location")
            _close_response(response)
            if not location:
                raise ValueError("Discovery redirect omitted its location.")
            current = board_discovery._public_https_url(urljoin(current, location))
            if (urlsplit(current).hostname or "").lower().rstrip(".") != allowed_host:
                raise ValueError("Cross-host discovery redirects are not followed.")
            continue
        if status == 404:
            _close_response(response)
            return current, status, headers, b"", False
        if status in {429, 503}:
            _close_response(response)
            raise requests.HTTPError(f"Host requested cooldown (HTTP {status})", response=response)
        if status != 200:
            _close_response(response)
            raise requests.HTTPError(f"Discovery URL returned HTTP {status}", response=response)
        try:
            body, truncated = _bounded_response_body(response, max_bytes)
        finally:
            _close_response(response)
        if truncated:
            raise ValueError("Discovery document exceeded its configured size cap.")
        return current, status, headers, body, truncated
    raise ValueError("Discovery URL exceeded the redirect limit.")


def _robots_policy(
    requester: Any,
    root_url: str,
) -> tuple[RobotFileParser, list[str], int, int]:
    parsed = urlsplit(root_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    robots_url = f"https://{parsed.netloc}/robots.txt"
    final_url, status, _headers, body, _ = _bounded_same_host_get(
        requester, robots_url, host, max_bytes=SITEMAP_ROBOTS_MAX_BYTES,
        user_agent=SITEMAP_USER_AGENT,
    )
    parser = RobotFileParser()
    parser.set_url(robots_url)
    sitemaps: list[str] = []
    if status == 404:
        parser.allow_all = True
        parser.parse([])
    else:
        text = body.decode("utf-8", errors="replace")
        parser.parse(text.splitlines())
        for line in text.splitlines():
            if line.strip().lower().startswith("sitemap:"):
                value = line.split(":", 1)[1].strip()
                try:
                    candidate = board_discovery._public_https_url(urljoin(robots_url, value))
                except ValueError:
                    continue
                if (urlsplit(candidate).hostname or "").lower().rstrip(".") == host:
                    sitemaps.append(candidate)
    return parser, list(dict.fromkeys(sitemaps)), status, 1


def _parse_sitemap_xml(body: bytes) -> tuple[list[str], list[str]]:
    """Return nested sitemap URLs and page URLs from a bounded XML document."""
    if len(body) > SITEMAP_MAX_BYTES:
        raise ValueError("Sitemap exceeded configured size.")
    lowered = body.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("Sitemap DTD/entity declarations are not accepted.")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError("Sitemap XML could not be parsed.") from exc
    kind = root.tag.rsplit("}", 1)[-1].lower()
    nested: list[str] = []
    pages: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() != "loc":
            continue
        value = (element.text or "").strip()
        if not value or len(value) > 2048:
            continue
        if kind == "sitemapindex":
            nested.append(value)
        elif kind == "urlset":
            pages.append(value)
    return nested, pages


def discover_public_sitemaps(
    db_path: str,
    website_url: str,
    *,
    careers_url: str | None = None,
    importer: CandidateImporter | None = None,
    requester: Any | None = None,
    at: dt.datetime | None = None,
) -> dict[str, Any]:
    """Inspect one public website's robots/sitemaps/careers links; stage candidates only."""
    init_schema(db_path)
    current = _utc(at)
    root_url = board_discovery._public_https_url(website_url)
    root_host = (urlsplit(root_url).hostname or "").lower().rstrip(".")
    careers = board_discovery._public_https_url(careers_url) if careers_url else None
    if careers and (urlsplit(careers).hostname or "").lower().rstrip(".") != root_host:
        raise ValueError("Careers URL must use the same host as the submitted employer website.")
    token, _state, blocked = _claim_sitemap_host(db_path, root_host, current)
    if blocked:
        return blocked
    client = requester or requests.Session()
    request_count = 0
    http_status: int | None = None
    candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
    outcome = "error"
    error_type: str | None = None
    cooldown = False
    crawl_delay = 0
    try:
        robots, sitemap_urls, http_status, used = _robots_policy(client, root_url)
        request_count += used
        if http_status not in {200, 404}:
            raise ValueError(f"Robots policy returned HTTP {http_status}.")
        robots_status = http_status
        crawl_delay = max(0, int(robots.crawl_delay(SITEMAP_USER_AGENT) or robots.crawl_delay("*") or 0))
        if crawl_delay > SITEMAP_MAX_CRAWL_DELAY_SECONDS:
            outcome = "robots_crawl_delay_deferred"
            _finish_sitemap_host(
                db_path, root_host, token, current=current, outcome=outcome,
                request_count=request_count, candidate_count=0,
                http_status=robots_status, next_allowed_seconds=crawl_delay,
            )
            return {
                "outcome": outcome, "host": root_host, "robots_status": robots_status,
                "requests_attempted": request_count, "crawl_delay_seconds": crawl_delay,
            }
        career_pages: list[str] = []
        if careers:
            detected = board_discovery.detect_ats_board(careers)
            if detected and detected.get("collector_available"):
                candidates[(detected["provider"], detected["host"], detected["board_key"])] = {
                    "board_url": careers, "discovery_method": "career_link",
                    "source_reference": root_url, "source_captured_at": None,
                }
            elif robots.can_fetch(SITEMAP_USER_AGENT, careers):
                career_pages.append(careers)
        if not sitemap_urls:
            default_sitemap = urljoin(root_url, "/sitemap.xml")
            if robots.can_fetch(SITEMAP_USER_AGENT, default_sitemap):
                sitemap_urls = [default_sitemap]
        sitemap_queue = list(sitemap_urls[:SITEMAP_MAX_DOCUMENTS])
        visited_sitemaps: set[str] = set()
        locations_seen = 0
        documents = 0
        while sitemap_queue and documents < SITEMAP_MAX_DOCUMENTS and locations_seen < SITEMAP_MAX_LOCATIONS:
            sitemap_url = sitemap_queue.pop(0)
            if sitemap_url in visited_sitemaps:
                continue
            parsed_sitemap = urlsplit(board_discovery._public_https_url(sitemap_url))
            if (parsed_sitemap.hostname or "").lower().rstrip(".") != root_host:
                continue
            if not robots.can_fetch(SITEMAP_USER_AGENT, sitemap_url):
                continue
            if request_count and crawl_delay:
                time.sleep(crawl_delay)
            request_count += 1
            final_url, http_status, _headers, body, _ = _bounded_same_host_get(
                client, sitemap_url, root_host, max_bytes=SITEMAP_MAX_BYTES,
                user_agent=SITEMAP_USER_AGENT,
            )
            documents += 1
            visited_sitemaps.add(sitemap_url)
            if http_status == 404:
                # Missing optional sitemap documents are normal; keep scanning
                # other sitemap entries rather than failing the whole host.
                continue
            nested, pages = _parse_sitemap_xml(body)
            locations_seen += len(nested) + len(pages)
            for nested_url in nested:
                try:
                    safe_nested = board_discovery._public_https_url(nested_url)
                except ValueError:
                    continue
                if (urlsplit(safe_nested).hostname or "").lower().rstrip(".") == root_host:
                    sitemap_queue.append(safe_nested)
            for page_url in pages:
                try:
                    safe_page = board_discovery._public_https_url(page_url)
                except ValueError:
                    continue
                detected = board_discovery.detect_ats_board(safe_page)
                if detected and detected.get("collector_available"):
                    key = (detected["provider"], detected["host"], detected["board_key"])
                    candidates[key] = {
                        "board_url": safe_page, "discovery_method": "sitemap",
                        "source_reference": final_url, "source_captured_at": None,
                    }
                elif (
                    (urlsplit(safe_page).hostname or "").lower().rstrip(".") == root_host
                    and re.search(r"(?:career|jobs?|work-with-us|join-us|vacanc|opportunit)", urlsplit(safe_page).path, re.I)
                ):
                    career_pages.append(safe_page)
        for page_url in list(dict.fromkeys(career_pages))[:SITEMAP_MAX_CAREER_PAGES]:
            if request_count >= SITEMAP_MAX_DOCUMENTS + 3:
                break
            if not robots.can_fetch(SITEMAP_USER_AGENT, page_url):
                continue
            if request_count and crawl_delay:
                time.sleep(crawl_delay)
            request_count += 1
            final_url, http_status, _headers, body, _ = _bounded_same_host_get(
                client, page_url, root_host, max_bytes=board_discovery.MAX_HTML_BYTES,
                user_agent=SITEMAP_USER_AGENT,
            )
            soup = BeautifulSoup(body, "html.parser")
            for tag in soup.find_all(["a", "iframe"]):
                raw = tag.get("href") or tag.get("src")
                if not isinstance(raw, str):
                    continue
                try:
                    candidate_url = board_discovery._normalise_candidate_url(urljoin(final_url, raw.strip()))
                except ValueError:
                    continue
                detected = board_discovery.detect_ats_board(candidate_url)
                if not detected or not detected.get("collector_available"):
                    continue
                key = (detected["provider"], detected["host"], detected["board_key"])
                candidates[key] = {
                    "board_url": candidate_url, "discovery_method": "career_link",
                    "source_reference": final_url, "source_captured_at": None,
                }
        all_candidates = list(candidates.values())
        candidate_list = all_candidates[:200]
        truncated_candidates = len(all_candidates) > len(candidate_list)
        ingestion = importer({"candidates": candidate_list}) if importer and candidate_list else {}
        outcome = "candidates_imported" if candidate_list else "no_candidates"
        _finish_sitemap_host(
            db_path, root_host, token, current=current, outcome=outcome,
            request_count=request_count, candidate_count=len(candidate_list),
            http_status=http_status,
        )
        return {
            "outcome": outcome, "host": root_host, "robots_status": robots_status,
            "sitemaps_checked": documents, "requests_attempted": request_count,
            "candidate_count": len(candidate_list), "imported": ingestion or {},
            "truncated": truncated_candidates, "crawl_delay_seconds": crawl_delay,
        }
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        status = int(getattr(response, "status_code", 0) or 0)
        cooldown = status in {429, 503}
        outcome = "host_cooldown" if cooldown else "http_error"
        error_type = f"http_{status}" if status else type(exc).__name__
        _finish_sitemap_host(
            db_path, root_host, token, current=current, outcome=outcome,
            request_count=request_count, candidate_count=len(candidates),
            http_status=status or http_status, error_type=error_type, cooldown=cooldown,
        )
        return {
            "outcome": outcome, "host": root_host, "http_status": status or http_status,
            "error_type": error_type, "cooldown_seconds": SITEMAP_HOST_COOLDOWN_SECONDS if cooldown else None,
        }
    except Exception as exc:
        outcome = "discovery_error"
        error_type = type(exc).__name__
        _finish_sitemap_host(
            db_path, root_host, token, current=current, outcome=outcome,
            request_count=request_count, candidate_count=len(candidates),
            http_status=http_status, error_type=error_type,
        )
        return {"outcome": outcome, "host": root_host, "http_status": http_status, "error_type": error_type}
    finally:
        close = getattr(client, "close", None)
        if requester is None and callable(close):
            close()


def discovery_status(db_path: str, history_limit: int = 20) -> dict[str, Any]:
    init_schema(db_path)
    with DB_LOCK, connect(db_path) as conn:
        state = _state_row(conn)
        conn.row_factory = None
        run_cursor = conn.execute("""
            SELECT * FROM global_ats_discovery_runs ORDER BY id DESC LIMIT ?
        """, (max(1, min(int(history_limit), 100)),))
        run_names = [item[0] for item in run_cursor.description]
        runs = [dict(zip(run_names, row)) for row in run_cursor.fetchall()]
        host_cursor = conn.execute("""
            SELECT host_key,next_allowed_at,cooldown_until,last_scanned_at,last_outcome,
                   last_http_status,request_count,candidate_count,last_error_type
            FROM global_ats_discovery_host_budget ORDER BY host_key
        """)
        host_names = [item[0] for item in host_cursor.description]
        hosts = [dict(zip(host_names, row)) for row in host_cursor.fetchall()]
    # Do not expose lock tokens to the admin dashboard/API.
    state.pop("cdx_lease_token", None)
    return {"commoncrawl": state, "host_budgets": hosts, "recent_runs": runs}
