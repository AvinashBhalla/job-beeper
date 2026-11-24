"""Parse Instahyre's public listing details without requiring a candidate session."""

import json
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from v2.job_requirements import clean_skills, description_to_markdown


MAX_PAGE_BYTES = 512 * 1024
MIN_EXPERIENCE_EXTRACTION_VERSION = 4
# Search previews and operator summaries remain visible but do not qualify
# for alerts. A complete capture also needs reliable experience evidence.
ALERT_EXPERIENCE_READY_SQL = f"""(j.source != 'instahyre' OR (
    j.experience_provenance IN ('description', 'employer_stated')
    AND COALESCE(j.experience_min_years, j.experience_max_years) IS NOT NULL
    AND j.experience_extraction_version >= {MIN_EXPERIENCE_EXTRACTION_VERSION}
    AND length(trim(j.description)) > 0
    AND CASE WHEN json_valid(j.source_details_json) THEN
        json_type(j.source_details_json, '$.instahyre_detail_verified') = 'true'
        AND (
            json_extract(j.source_details_json, '$.instahyre_detail_fetch_status') = 'complete'
            OR (
                json_extract(j.source_details_json, '$.instahyre_detail_fetch_status') IS NULL
                AND NULLIF(json_extract(j.source_details_json, '$.instahyre_detail_attempted_at'), '') IS NOT NULL
            )
        )
    ELSE 0 END
))"""


def has_complete_detail(description: str, details: dict) -> bool:
    status = details.get("instahyre_detail_fetch_status")
    return bool(
        description.strip()
        and details.get("instahyre_detail_verified") is True
        and (status == "complete" or (status is None and details.get("instahyre_detail_attempted_at")))
    )


def is_listing_url(url: str, source_id: str) -> bool:
    try:
        parts = urlsplit(url)
        return (
            parts.scheme == "https"
            and parts.netloc.lower() in {"instahyre.com", "www.instahyre.com"}
            and source_id.isdigit()
            and re.fullmatch(rf"/job-{source_id}-[a-z0-9-]+/?", parts.path) is not None
        )
    except ValueError:
        return False


def parse_listing(page: str | bytes, source_id: str) -> tuple[str, dict]:
    soup = BeautifulSoup(page, "html.parser")
    posting = None
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(node.string or "")
        except (ValueError, TypeError):
            continue
        if not isinstance(value, dict) or value.get("@type") != "JobPosting":
            continue
        identifier = value.get("identifier")
        if not isinstance(identifier, dict):
            continue
        slug = str(identifier.get("value") or "")
        if slug.startswith(f"job-{source_id}-"):
            posting = value
            break
    if posting is None:
        return "", {}

    details = {}
    badge = soup.select_one("#floating-header .experience, .employer-profile-info-wrapper .job-locations .experience")
    if badge:
        value = badge.get_text(" ", strip=True)
        if re.fullmatch(r"\d+(?:\s*(?:[-–—]|to)\s*\d+|\+)?\s+(?:years?|yrs?)", value, re.I):
            details["listing_experience"] = value
    skills = clean_skills([node.get_text(" ", strip=True) for node in soup.select("#job-skills-description li")])
    if skills:
        details["key_skills"] = skills
    description = soup.select_one("#job-description .quill-formatted")
    if description is None:
        html = posting.get("description")
        description = BeautifulSoup(html if isinstance(html, str) else "", "html.parser")
    else:
        # A detached copy lets the converter add boundaries around its blocks.
        description = BeautifulSoup(description.decode_contents(), "html.parser")
    markdown = description_to_markdown(description)
    if markdown:
        details["instahyre_detail_verified"] = True
    return markdown, details
