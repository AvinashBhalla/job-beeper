"""Normalize licensed SERP results into review-only ATS board candidates.

This module does not make network requests, activate boards, or schedule discovery.
Provider clients can call these pure helpers after receiving DataForSEO/Serper
responses. Candidate identity is always derived from the existing ATS URL parser.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Any

import requests
from urllib.parse import parse_qs, urlsplit

from v2 import board_discovery

UTC = dt.timezone.utc

# These are search targets, not proof that a result belongs to an employer.
PROVIDER_TARGETS = {
    "workday": "*myworkdayjobs.com*",
    "greenhouse": "*greenhouse.io*",
    "ashby": "*ashbyhq.com*",
    "lever": "*lever.co*",
    "smartrecruiters": "*smartrecruiters.com*",
    "workable": "*workable.com*",
    "keka": "*keka.com*",
    "darwinbox": "*darwinbox.in*",
}

PROVIDER_SITE_DOMAINS = {
    "workday": "myworkdayjobs.com",
    "greenhouse": "greenhouse.io",
    "ashby": "ashbyhq.com",
    "lever": "lever.co",
    "smartrecruiters": "smartrecruiters.com",
    "workable": "workable.com",
    "keka": "keka.com",
    "darwinbox": "darwinbox.in",
}

DEFAULT_ROLE_TERMS = (
    "Software Engineer",
    "Software Developer",
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Engineer",
    "Python Developer",
    "Automation Engineer",
)


def _provider_name(provider: str) -> str:
    value = str(provider or "").strip().lower().replace("-", "").replace("_", "")
    aliases = {
        "workday": "workday",
        "greenhouse": "greenhouse",
        "ashby": "ashby",
        "lever": "lever",
        "smartrecruiters": "smartrecruiters",
        "workable": "workable",
        "keka": "keka",
        "darwinbox": "darwinbox",
    }
    if value not in aliases:
        raise ValueError(f"Unsupported ATS discovery provider: {provider!r}")
    return aliases[value]


def build_serper_query(
    provider: str,
    *,
    role_terms: tuple[str, ...] | list[str] = DEFAULT_ROLE_TERMS,
    location: str = "India",
) -> str:
    """Build a bounded Google-syntax query for a Serper-compatible endpoint."""
    provider = _provider_name(provider)
    terms = [str(term).strip() for term in role_terms if str(term).strip()]
    if not terms or len(terms) > 8:
        raise ValueError("Provide between one and eight non-empty role terms.")
    location = str(location or "").strip()
    if not location or len(location) > 80:
        raise ValueError("A bounded location term is required.")
    quoted = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
    return f"({quoted}) {location} site:{PROVIDER_SITE_DOMAINS[provider]}"


def build_dataforseo_live_payload(
    provider: str,
    *,
    keyword: str = "software engineer India",
    location_code: int = 2356,
    language_code: str = "en",
    depth: int = 10,
) -> dict[str, Any]:
    """Build one DataForSEO Live Google Organic task using structured target."""
    provider = _provider_name(provider)
    keyword = str(keyword or "").strip()
    if not keyword or len(keyword) > 200:
        raise ValueError("A non-empty keyword of at most 200 characters is required.")
    if not isinstance(location_code, int) or location_code <= 0:
        raise ValueError("location_code must be a positive integer.")
    if language_code not in {"en"}:
        raise ValueError("Only the reviewed English-language pilot is supported.")
    if depth not in {10, 20}:
        raise ValueError("depth must be 10 or 20.")
    return {
        "keyword": keyword,
        "location_code": location_code,
        "language_code": language_code,
        "target": PROVIDER_TARGETS[provider],
        "depth": depth,
    }


def _organic_items(payload: Any) -> list[dict[str, Any]]:
    """Read the organic result shapes returned by Serper and DataForSEO."""
    if not isinstance(payload, dict):
        return []
    serper = payload.get("organic")
    if isinstance(serper, list):
        return [item for item in serper if isinstance(item, dict)]
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return []
    items: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        results = task.get("result")
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            result_items = result.get("items")
            if not isinstance(result_items, list):
                continue
            for item in result_items:
                if isinstance(item, dict) and item.get("type", "organic") == "organic":
                    items.append(item)
    return items


def _unwrap_google_result(value: str) -> str | None:
    """Resolve only Google's documented /url?q= redirect shape."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"google.com", "www.google.com"} or parsed.path != "/url":
        return value
    query = parse_qs(parsed.query)
    target = (query.get("q") or query.get("url") or [""])[0]
    try:
        target_parsed = urlsplit(target)
    except ValueError:
        return None
    if target_parsed.scheme != "https" or not target_parsed.hostname:
        return None
    if (target_parsed.hostname or "").lower() in {"google.com", "www.google.com"}:
        return None
    return target


def _result_url(item: dict[str, Any]) -> str | None:
    raw = item.get("link") or item.get("url") or item.get("href")
    if not isinstance(raw, str) or len(raw) > 4096:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return _unwrap_google_result(raw)


def normalize_serp_candidates(
    payload: Any,
    provider: str,
    *,
    engine: str,
    query: str,
    fetched_at: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """Return unique, supported, review-only ATS candidates from a SERP response.

    Search snippets are deliberately not treated as proof of company identity.
    The canonical employer association must be established in the review flow.
    """
    provider = _provider_name(provider)
    engine = str(engine or "").strip().lower()
    if engine not in {"dataforseo_live", "serper"}:
        raise ValueError("engine must be dataforseo_live or serper.")
    query = str(query or "").strip()
    if not query or len(query) > 500:
        raise ValueError("A bounded source query is required.")
    captured = fetched_at or dt.datetime.now(UTC)
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=UTC)
    captured_text = captured.astimezone(UTC).isoformat()

    candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
    for rank, item in enumerate(_organic_items(payload), start=1):
        url = _result_url(item)
        if not url:
            continue
        detected = board_discovery.detect_ats_board(url)
        if not detected or detected.get("provider") != provider:
            continue
        if not detected.get("collector_available"):
            continue
        key = (
            provider,
            str(detected.get("host") or "").lower(),
            str(detected.get("board_key") or "").lower(),
        )
        if not key[1] or not key[2]:
            continue
        candidates.setdefault(key, {
            "board_url": detected["board_url"],
            "discovery_method": "search_engine_serp",
            "source_reference": (
                f"engine={engine};provider={provider};rank={rank};query={query}"
            )[:2048],
            "source_captured_at": captured_text,
        })
    return list(candidates.values())


DATAFORSEO_LIVE_ENDPOINT = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
SERPER_ENDPOINT = "https://google.serper.dev/search"
SEARCH_TIMEOUT_SECONDS = 20


def search_dataforseo_live(
    provider: str,
    *,
    keyword: str = "software engineer India",
    username: str | None = None,
    password: str | None = None,
    requester: Any = requests,
) -> dict[str, Any]:
    """Perform exactly one DataForSEO Live query using credentials from the secret store.

    Credentials are read from DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD when not
    supplied by the caller. No retries are performed because a retry is another
    billable SERP request. This function is not scheduled or called at import.
    """
    username = username if username is not None else os.getenv("DATAFORSEO_LOGIN")
    password = password if password is not None else os.getenv("DATAFORSEO_PASSWORD")
    if not username or not password:
        raise RuntimeError("DataForSEO credentials are not configured in the runtime secret store.")
    payload = [build_dataforseo_live_payload(provider, keyword=keyword)]
    response = requester.post(
        DATAFORSEO_LIVE_ENDPOINT,
        json=payload,
        auth=(username, password),
        timeout=SEARCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or not isinstance(result.get("tasks"), list):
        raise ValueError("DataForSEO response did not contain a tasks array.")
    return result


def search_serper(
    provider: str,
    *,
    role_terms: tuple[str, ...] | list[str] = DEFAULT_ROLE_TERMS,
    location: str = "India",
    api_key: str | None = None,
    requester: Any = requests,
) -> dict[str, Any]:
    """Perform exactly one Serper Google query; never retries a billable request."""
    api_key = api_key if api_key is not None else os.getenv("SERPER_API_KEY")
    if not api_key:
        raise RuntimeError("Serper API key is not configured in the runtime secret store.")
    query = build_serper_query(provider, role_terms=role_terms, location=location)
    response = requester.post(
        SERPER_ENDPOINT,
        headers={"X-API-KEY": api_key},
        json={"q": query, "gl": "in", "hl": "en", "num": 10},
        timeout=SEARCH_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or not isinstance(result.get("organic", []), list):
        raise ValueError("Serper response did not contain an organic results array.")
    return result
