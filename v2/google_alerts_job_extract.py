"""Conservative Schema.org JobPosting extraction for public job pages."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

from v2.dedupe import canonicalize_url
from v2.google_alerts_rss import _html_to_text

UTC = dt.timezone.utc


class _JsonLdScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._capture = False
        self._parts: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "script":
            return
        values = {str(key).lower(): value for key, value in attrs}
        content_type = str(values.get("type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/ld+json":
            self._capture = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._capture:
            self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._capture:
            self._parts.append(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture:
            self.scripts.append("".join(self._parts))
            self._capture = False
            self._parts = []


@dataclass(frozen=True)
class JobPostingExtraction:
    status: str
    reason: str | None
    job: dict[str, Any] | None


def _walk_jsonld(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _walk_jsonld(item)
        return
    if not isinstance(value, dict):
        return

    types = value.get("@type")
    if isinstance(types, str):
        type_values = [types]
    elif isinstance(types, list):
        type_values = [str(item) for item in types]
    else:
        type_values = []

    if any(item.rsplit("/", 1)[-1].rsplit("#", 1)[-1] == "JobPosting" for item in type_values):
        yield value

    for key in ("@graph", "mainEntity", "mainEntityOfPage", "hasPart"):
        nested = value.get(key)
        if isinstance(nested, (dict, list)):
            yield from _walk_jsonld(nested)


def _parse_date(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        parsed = dt.datetime.fromisoformat(
            raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        )
    except ValueError:
        try:
            parsed_date = dt.date.fromisoformat(raw)
            parsed = dt.datetime.combine(
                parsed_date, dt.time(0, 0), tzinfo=UTC
            )
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _named_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "").strip()
    return ""


def _extract_address(value: Any) -> str:
    if isinstance(value, list):
        values = [_extract_address(item) for item in value]
        return " / ".join(item for item in values if item)

    if not isinstance(value, dict):
        return _named_value(value)

    address = value.get("address", value)
    if isinstance(address, list):
        return _extract_address(address)
    if not isinstance(address, dict):
        return _named_value(address)

    parts = []
    for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode"):
        item = _named_value(address.get(key))
        if item and item not in parts:
            parts.append(item)
    country = _named_value(address.get("addressCountry"))
    if country and country not in parts:
        parts.append(country)
    if parts:
        return ", ".join(parts)
    return _named_value(value.get("name"))


def _location_text(posting: dict[str, Any]) -> str:
    location = _extract_address(posting.get("jobLocation"))
    remote_type = str(posting.get("jobLocationType") or "").upper()
    if "TELECOMMUTE" in remote_type and "remote" not in location.casefold():
        restrictions = _extract_address(posting.get("applicantLocationRequirements"))
        return f"Remote - {restrictions}" if restrictions else "Remote"
    return location


def _employment_type(value: Any) -> str:
    if isinstance(value, list):
        values = [_named_value(item) for item in value]
    else:
        values = [_named_value(value)]
    seen = []
    for item in values:
        if item and item.casefold() not in {existing.casefold() for existing in seen}:
            seen.append(item)
    return ", ".join(seen)


def extract_jobposting_jsonld(
    page_text: str,
    final_url: str,
    *,
    now: dt.datetime | None = None,
) -> JobPostingExtraction:
    """Extract one valid JobPosting. Never infer missing company/title fields.

    A page without usable JobPosting structured data is returned as
    `needs_review`; the feed snippet is intentionally not used as proof.
    """
    if not isinstance(page_text, str) or not page_text.strip():
        return JobPostingExtraction("needs_review", "empty_page", None)

    try:
        parsed_url = urlsplit(final_url)
    except ValueError:
        return JobPostingExtraction("needs_review", "invalid_final_url", None)
    if (
        parsed_url.scheme.lower() != "https"
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        return JobPostingExtraction("needs_review", "invalid_final_url", None)

    parser = _JsonLdScriptParser()
    try:
        parser.feed(page_text)
        parser.close()
    except Exception:
        return JobPostingExtraction("needs_review", "html_parse_error", None)

    postings: list[dict[str, Any]] = []
    for script in parser.scripts:
        if len(script.encode("utf-8", errors="ignore")) > 1_000_000:
            continue
        try:
            document = json.loads(script)
        except (json.JSONDecodeError, TypeError):
            continue
        postings.extend(item for item in _walk_jsonld(document) if isinstance(item, dict))

    if not postings:
        return JobPostingExtraction("needs_review", "jobposting_jsonld_not_found", None)

    current = now or dt.datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)

    for posting in postings:
        title = _named_value(posting.get("title") or posting.get("name"))
        company = _named_value(posting.get("hiringOrganization"))
        if not company and isinstance(posting.get("hiringOrganization"), dict):
            company = _named_value(posting["hiringOrganization"].get("name"))
        description_raw = str(posting.get("description") or "")
        description = _html_to_text(description_raw)
        location = _location_text(posting)
        date_posted = _parse_date(posting.get("datePosted"))
        valid_through = _parse_date(posting.get("validThrough"))
        if valid_through is not None and valid_through < current:
            continue
        if not title or not company:
            continue

        canonical_url = canonicalize_url(final_url)
        if not canonical_url:
            return JobPostingExtraction("needs_review", "canonical_url_missing", None)
        source_job_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:40]

        job = {
            "source_job_id": source_job_id,
            "company": company,
            "title": title,
            "location": location,
            "url": final_url,
            "source_posted_at": date_posted,
            "posted_precision": "day" if date_posted else "unknown",
            "description": description,
            "description_format": "plain",
            "source_details": {
                "extractor": "schema.org/JobPosting",
                "verification": "jobposting_jsonld",
                "employment_type": _employment_type(posting.get("employmentType")),
                "valid_through": valid_through.isoformat() if valid_through else None,
                "canonical_url": canonical_url,
            },
        }
        return JobPostingExtraction("verified", None, job)

    if any(
        _parse_date(posting.get("validThrough")) is not None
        and _parse_date(posting.get("validThrough")) < current
        for posting in postings
    ):
        return JobPostingExtraction("rejected", "posting_expired", None)
    return JobPostingExtraction("needs_review", "jobposting_missing_required_fields", None)
