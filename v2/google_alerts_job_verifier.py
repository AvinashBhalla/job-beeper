"""Independent public-page verification for Google Alerts job candidates.

The email is only a discovery hint. This verifier fetches the public destination
using the existing SSRF-aware board-discovery fetcher, honours robots policy,
and requires structured JobPosting evidence from the page itself.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

from v2 import board_discovery
from v2.dedupe import canonicalize_url


USER_AGENT = "JobBeeperBot/1.0 (+https://jobbeeper.com/bot)"
MAX_JSONLD_BYTES = 1_000_000
MAX_DESCRIPTION_CHARS = 40_000


class PublicJobVerificationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _text(value: object, limit: int = 4000) -> str:
    if not isinstance(value, (str, int, float)):
        return ""
    clean = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", clean).strip()[:limit]


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raw += "T00:00:00+00:00"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _job_postings(value: Any):
    if isinstance(value, dict):
        types = value.get("@type")
        if types == "JobPosting" or (
            isinstance(types, list) and "JobPosting" in types
        ):
            yield value
        for child in value.values():
            yield from _job_postings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _job_postings(child)


def _robots_allows(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return False
    robots_url = f"https://{parsed.netloc}/robots.txt"
    try:
        final_url, body = board_discovery._safe_fetch(robots_url)
    except requests.HTTPError as exc:
        # A missing robots file permits crawling; other status failures are
        # treated conservatively and never bypassed.
        if getattr(getattr(exc, "response", None), "status_code", None) == 404:
            return True
        return False
    except Exception:
        return False
    if (urlsplit(final_url).hostname or "").lower().rstrip(".") != host:
        return False
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(body.splitlines())
    try:
        return bool(parser.can_fetch(USER_AGENT, url))
    except Exception:
        return False


def _locations(posting: dict[str, Any]) -> str:
    if str(posting.get("jobLocationType") or "").upper() == "TELECOMMUTE":
        return "Remote"
    values = posting.get("jobLocation") or posting.get("jobLocationAddress")
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        values = []
    found: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        address = value.get("address")
        if not isinstance(address, dict):
            address = value
        parts = [
            _text(address.get("addressLocality"), 120),
            _text(address.get("addressRegion"), 120),
            _text(address.get("addressCountry"), 120),
        ]
        place = ", ".join(part for part in parts if part)
        if place and place.casefold() not in {item.casefold() for item in found}:
            found.append(place)
    return "; ".join(found[:5]) or "Not specified"


def _extract_posting(document: dict[str, Any], final_url: str) -> dict[str, Any] | None:
    title = _text(document.get("title"), 500)
    organization = document.get("hiringOrganization")
    if isinstance(organization, list):
        organization = next((item for item in organization if isinstance(item, dict)), {})
    if not isinstance(organization, dict):
        organization = {}
    company = _text(organization.get("name"), 300)
    if not title or not company:
        return None

    valid_through = document.get("validThrough")
    if valid_through:
        expiry = _parse_datetime(valid_through)
        if expiry is None:
            return None
        if expiry < datetime.now(timezone.utc):
            return None

    description = _text(document.get("description"), MAX_DESCRIPTION_CHARS)
    if len(description) < 20:
        return None

    # The JSON-LD url and mainEntityOfPage are untrusted page-controlled
    # metadata. Link to the already fetched and revalidated final URL instead
    # of allowing the posting document to nominate a different destination.
    canonical = canonicalize_url(final_url)
    if not canonical:
        return None

    posted = _parse_datetime(document.get("datePosted"))
    return {
        "title": title,
        "company": company,
        "location": _locations(document),
        "description": description,
        "description_format": "plain",
        "url": canonical,
        "canonical_url": canonical,
        "source_posted_at": posted.isoformat() if posted else None,
        "posted_precision": "day" if posted else "unknown",
        "source_domain": (urlsplit(final_url).hostname or "").lower(),
        "verification_basis": "public_jsonld_jobposting",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_public_job_posting(candidate_url: str) -> dict[str, Any]:
    """Return verified public JobPosting fields or raise a sanitized rejection."""
    try:
        safe_url = board_discovery._public_https_url(candidate_url)
    except Exception:
        raise PublicJobVerificationError("destination_not_public_https") from None

    if not _robots_allows(safe_url):
        raise PublicJobVerificationError("robots_policy_denied_or_unavailable")

    try:
        final_url, html = board_discovery._safe_fetch(safe_url)
    except requests.HTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        code = "posting_not_found" if status == 404 else (
            "posting_access_denied" if status in {401, 403, 429} else "posting_fetch_failed"
        )
        raise PublicJobVerificationError(code) from None
    except Exception:
        raise PublicJobVerificationError("posting_fetch_failed") from None

    try:
        final_url = board_discovery._public_https_url(final_url)
    except Exception:
        raise PublicJobVerificationError("posting_redirect_not_public") from None

    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    found: list[dict[str, Any]] = []
    for script in scripts:
        raw = script.string or script.get_text(" ", strip=True)
        if not raw or len(raw.encode("utf-8", errors="ignore")) > MAX_JSONLD_BYTES:
            continue
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        found.extend(item for item in _job_postings(parsed) if isinstance(item, dict))

    for posting in found:
        verified = _extract_posting(posting, final_url)
        if verified:
            return verified
    raise PublicJobVerificationError("active_jobposting_evidence_missing")
