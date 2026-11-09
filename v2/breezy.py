"""Parser for Breezy HR's publicly accessible employer careers portal feed.

The /json response is an observed, undocumented public portal endpoint, not an
authenticated Breezy API. Keep the adapter default-off and board-verified.
"""
from __future__ import annotations

import ipaddress
import json
import re
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

MAX_FEED_BYTES = 2_000_000
MAX_DETAIL_BYTES = 1_500_000
MAX_JOBS_PER_BOARD = 3_000
MAX_DETAIL_FETCHES_PER_BOARD = 20
MAX_DESCRIPTION_CHARS = 30_000


def _safe_board_url(value: str, tenant: str) -> str | None:
    raw = value.strip()
    if not raw or len(raw) > 2_048:
        return None
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme.lower() != "https"
            or host != f"{tenant.lower()}.breezy.hr"
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            return None
    except ValueError:
        return None
    return raw


def _location_label(value: Any) -> tuple[str, bool]:
    candidates = value if isinstance(value, list) else [value]
    labels: list[str] = []
    remote = False
    for item in candidates:
        if not isinstance(item, dict):
            continue
        remote = remote or bool(item.get("is_remote"))
        name = str(item.get("name") or "").strip()
        parts = [
            str(item.get("city") or "").strip(),
            str(item.get("state") or "").strip(),
            str(item.get("country") or "").strip(),
        ]
        label = ", ".join(part for part in parts if part) or name
        if label and label not in labels:
            labels.append(label[:200])
    if not labels and remote:
        return "Remote", True
    return "; ".join(labels)[:500] or ("Remote" if remote else "Unspecified"), remote


def parse_public_jobs(payload: Any, *, tenant: str, company: str) -> list[dict[str, Any]]:
    """Parse the public /json board list into safe, normalized listing records."""
    tenant = str(tenant or "").lower()
    if not re.fullmatch(r"[a-z0-9-]{1,80}", tenant):
        raise ValueError("Invalid Breezy HR board slug.")
    if not isinstance(payload, list):
        raise ValueError("Breezy public jobs feed must be a JSON list.")
    if len(payload) > MAX_JOBS_PER_BOARD:
        raise ValueError("Breezy public jobs feed exceeded the per-board listing limit.")

    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_id = str(item.get("id") or "").strip()
        friendly_id = str(item.get("friendly_id") or "").strip()
        identity = raw_id or friendly_id
        if not identity or not re.fullmatch(r"[A-Za-z0-9_-]{1,180}", identity):
            continue
        title = str(item.get("name") or "").strip()
        link = _safe_board_url(str(item.get("url") or ""), tenant)
        if not title or not link or identity in seen:
            continue
        seen.add(identity)

        location, is_remote = _location_label(item.get("locations") or item.get("location"))
        job_type = item.get("type")
        if isinstance(job_type, dict):
            job_type = job_type.get("name")
        company_node = item.get("company")
        feed_company = (
            company_node.get("name")
            if isinstance(company_node, dict)
            else company_node
        )
        parsed.append({
            "reference": identity,
            "friendly_id": friendly_id or None,
            "title": title[:300],
            "company": str(feed_company or company)[:200],
            "location": location,
            "url": link,
            "posted": str(item.get("published_date") or "").strip() or None,
            "department": str(item.get("department") or "").strip()[:160] or None,
            "salary": str(item.get("salary") or "").strip()[:500] or None,
            "employment_type": str(job_type or "").strip()[:120] or None,
            "remote": is_remote,
        })
        if len(parsed) >= MAX_JOBS_PER_BOARD:
            break
    return parsed


def _job_posting_nodes(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _job_posting_nodes(item)
    elif isinstance(value, dict):
        types = value.get("@type")
        if types == "JobPosting" or (isinstance(types, list) and "JobPosting" in types):
            yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _job_posting_nodes(graph)


def parse_public_job_detail(html_content: bytes) -> dict[str, Any] | None:
    """Extract a narrow JobPosting JSON-LD allowlist from a public job detail page."""
    if not isinstance(html_content, bytes):
        raise ValueError("Breezy job detail must be HTML bytes.")
    if len(html_content) > MAX_DETAIL_BYTES:
        raise ValueError("Breezy job detail exceeded the configured size limit.")
    soup = BeautifulSoup(html_content, "html.parser")
    for node in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(node.string or node.get_text())
        except (TypeError, ValueError):
            continue
        posting = next(_job_posting_nodes(payload), None)
        if posting is None:
            continue
        description = BeautifulSoup(
            str(posting.get("description") or ""), "html.parser"
        ).get_text(" ", strip=True)
        salary = posting.get("baseSalary")
        return {
            "description": description[:MAX_DESCRIPTION_CHARS],
            "date_posted": str(posting.get("datePosted") or "").strip() or None,
            "employment_type": str(posting.get("employmentType") or "").strip() or None,
            "salary_json": salary if isinstance(salary, (dict, list, str, int, float)) else None,
            "url": str(posting.get("url") or "").strip() or None,
            "details_fetched": True,
        }
    return None
