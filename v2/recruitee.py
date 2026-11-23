"""Read public Recruitee job feeds without retaining raw XML or off-site links."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

MAX_FEED_BYTES = 12 * 1024 * 1024
MAX_BOARDS = 20
BOARD_NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
OFFER_ID = re.compile(r"[A-Za-z0-9_-]{1,120}")
OFFER_PATH = re.compile(r"/o/[A-Za-z0-9_-]{1,250}(?:/c/new)?/?")


def feed_url(board: str) -> str:
    if not BOARD_NAME.fullmatch(board):
        raise ValueError("Invalid Recruitee board name.")
    return f"https://{board}.recruitee.com/api/feeds/offers.xml"


class _PublicFeedTree(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("Document type declarations are not allowed in public feeds.")


def read_offers(response) -> list[ET.Element]:
    """Read a bounded decoded body and accept only supported offer-feed roots."""
    with response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected Recruitee response status.")
        body = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            if len(body) + len(chunk) > MAX_FEED_BYTES:
                raise ValueError("Recruitee feed exceeds the response limit.")
            body.extend(chunk)
    root = ET.fromstring(body, parser=ET.XMLParser(target=_PublicFeedTree()))
    paths = {"offers": "./offer", "jobs": "./job", "hash": "./offers/offer"}
    if root.tag not in paths or (root.tag == "hash" and root.find("offers") is None):
        raise ValueError("Unexpected Recruitee feed structure.")
    return [
        offer for offer in root.findall(paths[root.tag])
        if (root.tag != "hash" or _value(offer, "status").lower() == "published")
        and _value(offer, "status").lower() in {"", "published"}
        and _value(offer, "kind").lower() in {"", "job"}
    ]


def _value(node: ET.Element, *names: str) -> str:
    for name in names:
        text = node.findtext(name, "").strip()
        if text:
            return text
    return ""


def _publication(value: str) -> tuple[datetime | None, str]:
    try:
        stamp = datetime.fromisoformat(re.sub(r"(?:\s+UTC|Z)$", "+00:00", value))
    except ValueError:
        return None, "unknown"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return stamp.replace(tzinfo=timezone.utc), "date"
    if stamp.utcoffset() is None:
        return None, "unknown"
    return stamp.astimezone(timezone.utc), "minute"


def _posting_url(offer: ET.Element, board: str) -> str:
    valid_hosts = {f"{board}.recruitee.com", f"{board}.s.recruitee.com"}
    for name in ("careers_url", "careers-url", "url", "apply_url", "careers-apply-url"):
        try:
            url = urlsplit(_value(offer, name))
        except ValueError:
            continue
        if url.scheme == "https" and url.netloc.lower() in valid_hosts and OFFER_PATH.fullmatch(url.path):
            return f"https://{url.netloc.lower()}{url.path}"
    slug = _value(offer, "slug")
    path = f"/o/{slug}"
    return f"https://{board}.recruitee.com{path}" if OFFER_PATH.fullmatch(path) else ""


def posting(offer: ET.Element, board: str) -> dict | None:
    """Select only fields used by the shared job ingestion pipeline."""
    external_id = _value(offer, "id", "reference")
    title = _value(offer, "title")
    url = _posting_url(offer, board)
    if not OFFER_ID.fullmatch(external_id) or not title or not url:
        return None
    locations = []
    for node in [*offer.findall("./locations/location"), offer]:
        location = ", ".join(dict.fromkeys(filter(None, (
            _value(node, "city"), _value(node, "state", "state_name", "state-name"),
            _value(node, "country", "country_code", "country-code"),
        ))))
        if location and location not in locations:
            locations.append(location)
    workplace = next((label for label, fields in (
        ("hybrid", ("hybrid",)), ("remote", ("remote",)), ("on_site", ("on_site", "on-site")),
    ) if _value(offer, *fields).lower() == "true"), None)
    location = " / ".join(locations) or _value(offer, "location")
    description = _value(offer, "description_requirements") or "\n".join(
        filter(None, (_value(offer, "description"), _value(offer, "requirements")))
    )
    published_at, precision = _publication(_value(offer, "published_at", "published-at", "posted"))
    return {
        "id": external_id, "title": title, "url": url, "location": location,
        "published_at": published_at, "precision": precision,
        "description": BeautifulSoup(description, "html.parser").get_text("\n", strip=True),
        "workplace": workplace, "locations": locations,
    }
