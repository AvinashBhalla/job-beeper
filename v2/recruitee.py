"""Safe parser for Recruitee's public, published-offers XML feed.

Only allowlisted candidate-facing job fields are extracted. In particular, the
optional <credentials> subtree is deliberately never traversed or persisted.
"""
from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

MAX_FEED_BYTES = 2_000_000
MAX_JOBS_PER_BOARD = 2_000
MAX_DESCRIPTION_CHARS = 30_000


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def _child_text(element: ElementTree.Element, name: str, limit: int = 2_000) -> str:
    wanted = name.lower()
    for child in list(element):
        if _local_name(child.tag) == wanted:
            value = " ".join(part.strip() for part in child.itertext() if part.strip())
            return value[:limit].strip()
    return ""


def _safe_job_url(value: str, tenant: str, *, allow_employer_domain: bool = False) -> str | None:
    raw = value.strip()
    if not raw or len(raw) > 2_048:
        return None
    try:
        parsed = urlsplit(raw)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        tenant_host = f"{tenant.lower()}.recruitee.com"
        same_tenant = hostname == tenant_host
        employer_https = False
        if allow_employer_domain and hostname and "." in hostname:
            try:
                address = ipaddress.ip_address(hostname)
                employer_https = address.is_global
            except ValueError:
                employer_https = hostname != "localhost"
        if (
            parsed.scheme.lower() != "https"
            or not (same_tenant or employer_https)
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            return None
    except ValueError:
        return None
    return raw


def _job_locations(element: ElementTree.Element) -> str:
    labels: list[str] = []
    for child in list(element):
        if _local_name(child.tag) != "locations":
            continue
        for location in list(child):
            parts = [
                _child_text(location, "city", 120),
                _child_text(location, "state", 120),
                _child_text(location, "country", 80),
            ]
            label = ", ".join(part for part in parts if part)
            if not label:
                label = " ".join(part.strip() for part in location.itertext() if part.strip())
            if label and label not in labels:
                labels.append(label[:200])
    if labels:
        return "; ".join(labels)[:500]

    direct = _child_text(element, "location", 200)
    parts = [
        _child_text(element, "city", 120),
        _child_text(element, "state", 120),
        _child_text(element, "country", 80),
    ]
    fallback = ", ".join(part for part in parts if part)
    if direct and fallback and direct.casefold() not in fallback.casefold():
        return f"{direct}, {fallback}"[:500]
    return (direct or fallback)[:500]


def _description(element: ElementTree.Element) -> str:
    parts = []
    for key in ("description_requirements", "description", "requirements", "highlight"):
        value = _child_text(element, key, MAX_DESCRIPTION_CHARS)
        if value and value not in parts:
            plain = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
            if plain and plain not in parts:
                parts.append(plain)
    return " ".join(parts)[:MAX_DESCRIPTION_CHARS]


def _offer_records(root: ElementTree.Element) -> list[ElementTree.Element]:
    root_name = _local_name(root.tag)
    if root_name == "hash":
        nested = next((item for item in list(root) if _local_name(item.tag) == "offers"), None)
        if nested is None:
            raise ValueError("Recruitee XML wrapper did not contain an offers list.")
        root = nested
        root_name = _local_name(root.tag)
    if root_name == "jobs":
        record_name = "job"
    elif root_name == "offers":
        record_name = "offer"
    else:
        raise ValueError("Recruitee feed root must be <jobs> or <offers>.")
    return [item for item in list(root) if _local_name(item.tag) == record_name]


def parse_public_offers(xml_content: bytes, *, tenant: str, company: str) -> list[dict[str, Any]]:
    """Parse the documented and observed Recruitee public XML feed shapes."""
    if not isinstance(xml_content, bytes):
        raise ValueError("Recruitee feed must be bytes.")
    if not tenant or not re.fullmatch(r"[a-z0-9-]{1,80}", tenant.lower()):
        raise ValueError("Invalid Recruitee tenant.")
    if len(xml_content) > MAX_FEED_BYTES:
        raise ValueError("Recruitee feed exceeded the configured size limit.")
    upper = xml_content.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("Recruitee feed must not contain a DTD or entity declaration.")
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise ValueError("Recruitee feed XML is malformed.") from exc

    parsed: list[dict[str, Any]] = []
    for element in _offer_records(root):
        reference = (
            _child_text(element, "reference", 180)
            or _child_text(element, "id", 180)
            or _child_text(element, "slug", 180)
        )
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", reference or ""):
            continue
        title = _child_text(element, "title", 300)
        posting_url = _safe_job_url(
            _child_text(element, "url", 2_048) or _child_text(element, "careers_url", 2_048),
            tenant, allow_employer_domain=True,
        )
        if not title or not posting_url:
            continue

        feed_company = (
            _child_text(element, "company", 200)
            or _child_text(element, "company_name", 200)
            or company
        )
        parsed.append({
            "reference": reference,
            "title": title,
            "company": feed_company[:200],
            "location": _job_locations(element),
            "url": posting_url,
            "apply_url": _safe_job_url(_child_text(element, "apply_url", 2_048), tenant, allow_employer_domain=True),
            "description": _description(element),
            "posted": _child_text(element, "posted", 80) or _child_text(element, "published_at", 80) or None,
            "updated": _child_text(element, "updated", 80) or _child_text(element, "updated_at", 80) or None,
            "remote": _child_text(element, "remote", 20) or None,
            "hybrid": _child_text(element, "hybrid", 20) or None,
            "on_site": _child_text(element, "on_site", 20) or None,
            "experience": _child_text(element, "experience", 160) or _child_text(element, "experience_code", 160) or None,
            "education": _child_text(element, "education", 160) or _child_text(element, "education_code", 160) or None,
            "contract_type": _child_text(element, "contract_type", 160) or _child_text(element, "employment_type_code", 160) or None,
            "category": _child_text(element, "category", 160) or None,
            "salary": _child_text(element, "salary", 500) or None,
            "company_id": _child_text(element, "company_id", 80) or None,
        })
        if len(parsed) >= MAX_JOBS_PER_BOARD:
            break
    return parsed
