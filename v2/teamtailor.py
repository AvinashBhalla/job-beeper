"""Parser for Teamtailor's employer-published public careers RSS feed."""
from __future__ import annotations

import hashlib
import ipaddress
import re
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

MAX_FEED_BYTES = 2_000_000
MAX_JOBS_PER_PAGE = 200
MAX_PAGES_PER_BOARD = 10
MAX_JOBS_PER_BOARD = MAX_JOBS_PER_PAGE * MAX_PAGES_PER_BOARD
MAX_DESCRIPTION_CHARS = 30_000
LOCATION_NAMESPACE = "https://teamtailor.com/locations"


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def _direct_text(element: ElementTree.Element, name: str, limit: int = 2_000) -> str:
    wanted = name.lower()
    for child in list(element):
        if _local_name(child.tag) == wanted:
            return " ".join(part.strip() for part in child.itertext() if part.strip())[:limit].strip()
    return ""


def _safe_public_https_url(value: str) -> str | None:
    raw = value.strip()
    if not raw or len(raw) > 2_048:
        return None
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme.lower() != "https"
            or not host
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or host == "localhost"
            or host.endswith((".localhost", ".local", ".internal"))
        ):
            return None
        try:
            ip = ipaddress.ip_address(host)
            if not ip.is_global:
                return None
        except ValueError:
            if "." not in host:
                return None
    except ValueError:
        return None
    return raw


def _location_text(item: ElementTree.Element) -> str:
    labels: list[str] = []
    for container in list(item):
        if _local_name(container.tag) != "locations":
            continue
        for location in list(container):
            if _local_name(location.tag) != "location":
                continue
            city = _direct_text(location, "city", 120)
            country = _direct_text(location, "country", 100)
            label = ", ".join(part for part in (city, country) if part)
            if not label:
                label = _direct_text(location, "name", 160)
            if label and label not in labels:
                labels.append(label)
    return "; ".join(labels)[:500]


def _publication_time(value: str):
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
        if result.tzinfo is None:
            from datetime import timezone
            result = result.replace(tzinfo=timezone.utc)
        return result
    except (TypeError, ValueError, OverflowError):
        return None


def parse_public_rss(xml_content: bytes, *, slug: str, company: str) -> list[dict[str, Any]]:
    """Parse Teamtailor public RSS jobs; unknown and private account fields are ignored."""
    if not isinstance(xml_content, bytes):
        raise ValueError("Teamtailor feed must be bytes.")
    slug = str(slug or "").lower()
    if not re.fullmatch(r"[a-z0-9-]{1,80}", slug):
        raise ValueError("Invalid Teamtailor board slug.")
    if len(xml_content) > MAX_FEED_BYTES:
        raise ValueError("Teamtailor feed exceeded the configured size limit.")
    upper = xml_content.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("Teamtailor feed must not contain a DTD or entity declaration.")
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise ValueError("Teamtailor RSS feed is malformed.") from exc
    if _local_name(root.tag) != "rss":
        raise ValueError("Teamtailor feed root must be <rss>.")
    channel = next((item for item in list(root) if _local_name(item.tag) == "channel"), None)
    if channel is None:
        raise ValueError("Teamtailor RSS feed is missing its channel.")
    items = [item for item in list(channel) if _local_name(item.tag) == "item"]

    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        title = _direct_text(item, "title", 300)
        link = _safe_public_https_url(_direct_text(item, "link", 2_048))
        guid = _direct_text(item, "guid", 2_048)
        if not title or not link:
            continue
        identity = guid or link
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        if digest in seen:
            continue
        seen.add(digest)
        description_html = _direct_text(item, "description", MAX_DESCRIPTION_CHARS)
        description = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
        remote_status = _direct_text(item, "remoteStatus", 80) or None
        location = _location_text(item)
        if not location and (remote_status or "").lower() in {"fully", "temporary"}:
            location = "Remote"
        parsed.append({
            "reference": digest,
            "guid": guid or None,
            "title": title,
            "company": company[:200],
            "location": location or "Unspecified",
            "url": link,
            "description": description[:MAX_DESCRIPTION_CHARS],
            "posted": _direct_text(item, "pubDate", 120) or None,
            "remote_status": remote_status,
            "department": _direct_text(item, "department", 160) or None,
            "role": _direct_text(item, "role", 160) or None,
            "division": _direct_text(item, "division", 160) or None,
        })
        if len(parsed) >= MAX_JOBS_PER_PAGE:
            break
    return parsed
