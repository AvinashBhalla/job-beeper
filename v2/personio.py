"""Parser for Personio's public, employer-enabled open-position XML feed."""
from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

from bs4 import BeautifulSoup

MAX_FEED_BYTES = 2_000_000
MAX_POSITIONS = 2_000
MAX_FIELD_CHARS = 30_000


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def _child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    wanted = name.lower()
    return next((item for item in list(element) if _local_name(item.tag) == wanted), None)


def _text(element: ElementTree.Element, name: str, limit: int = 2_000) -> str:
    node = _child(element, name)
    if node is None:
        return ""
    return " ".join(value.strip() for value in node.itertext() if value.strip())[:limit].strip()


def _description(element: ElementTree.Element) -> str:
    container = _child(element, "jobDescriptions")
    if container is None:
        return ""
    pieces: list[str] = []
    for block in list(container):
        if _local_name(block.tag) != "jobdescription":
            continue
        value = _text(block, "value", MAX_FIELD_CHARS)
        if not value:
            continue
        plain = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
        if plain and plain not in pieces:
            pieces.append(plain)
    return " ".join(pieces)[:MAX_FIELD_CHARS]


def _additional_offices(element: ElementTree.Element) -> list[str]:
    node = _child(element, "additionalOffices")
    if node is None:
        return []
    values: list[str] = []
    for child in node.iter():
        if child is node:
            continue
        value = " ".join(part.strip() for part in child.itertext() if part.strip())
        if value and value not in values:
            values.append(value[:200])
    return values[:20]


def parse_public_positions(
    xml_content: bytes, *, tenant: str, extension: str
) -> list[dict[str, Any]]:
    """Parse an allowlist of published Personio position fields.

    The XML feed is public only when the employer has enabled the feed in
    Personio Recruiting settings. Raw XML and unknown fields are never returned.
    """
    if not isinstance(xml_content, bytes):
        raise ValueError("Personio feed must be bytes.")
    tenant = str(tenant or "").lower()
    extension = str(extension or "").lower()
    if not re.fullmatch(r"[a-z0-9-]{1,80}", tenant):
        raise ValueError("Invalid Personio tenant.")
    if extension not in {"de", "com"}:
        raise ValueError("Unsupported Personio careers-site extension.")
    if len(xml_content) > MAX_FEED_BYTES:
        raise ValueError("Personio feed exceeded the configured size limit.")
    upper = xml_content.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("Personio feed must not contain a DTD or entity declaration.")
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise ValueError("Personio feed XML is malformed.") from exc
    if _local_name(root.tag) != "workzag-jobs":
        raise ValueError("Personio feed root must be <workzag-jobs>.")

    host = f"{tenant}.jobs.personio.{extension}"
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for position in list(root):
        if _local_name(position.tag) != "position":
            continue
        raw_id = _text(position, "id", 40)
        if not re.fullmatch(r"\d{1,20}", raw_id or "") or raw_id in seen:
            continue
        seen.add(raw_id)
        title = _text(position, "name", 300)
        if not title:
            continue

        offices = []
        office = _text(position, "office", 200)
        if office:
            offices.append(office)
        offices.extend(value for value in _additional_offices(position) if value not in offices)
        parsed.append({
            "reference": raw_id,
            "title": title,
            "location": "; ".join(offices)[:500],
            "url": f"https://{host}/job/{raw_id}",
            "description": _description(position),
            "subcompany": _text(position, "subcompany", 200) or None,
            "department": _text(position, "department", 200) or None,
            "recruiting_category": _text(position, "recruitingCategory", 200) or None,
            "employment_type": _text(position, "employmentType", 100) or None,
            "seniority": _text(position, "seniority", 100) or None,
            "schedule": _text(position, "schedule", 100) or None,
            "years_of_experience": _text(position, "yearsOfExperience", 100) or None,
            "keywords": _text(position, "keywords", 1_000) or None,
            "occupation": _text(position, "occupation", 200) or None,
            "occupation_category": _text(position, "occupationCategory", 200) or None,
            "created_at": _text(position, "createdAt", 80) or None,
            "salary_information": _text(position, "salaryInformation", 500) or None,
        })
        if len(parsed) >= MAX_POSITIONS:
            break
    return parsed
