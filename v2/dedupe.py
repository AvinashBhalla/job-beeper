from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


LEGAL_SUFFIXES = {
    "inc", "incorporated", "llp", "ltd", "limited", "pvt", "private",
    "company", "co", "corp", "corporation",
}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "trk", "trkcampaign", "trackingid", "ref", "refid",
}


def normalize_entity(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    parts = [part for part in text.split() if part not in LEGAL_SUFFIXES]
    return " ".join(parts)


def normalize_title(value: str) -> str:
    return normalize_entity(value)


def normalize_company(value: str) -> str:
    return normalize_entity(value)


def normalize_location(value: str) -> str:
    text = str(value or "").lower()
    aliases = (
        (r"\bbengaluru\b", "bangalore"),
        (r"\bgurugram\b", "gurgaon"),
        (r"\bdelhi ncr\b", "delhi"),
        (r"\bremote\b", "remote"),
    )
    for pattern, replacement in aliases:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    if "bangalore" in text:
        return "bangalore"
    if "gurgaon" in text:
        return "gurgaon"
    if "delhi" in text:
        return "delhi"
    if "remote" in text:
        return "remote"
    return text


def canonicalize_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw.rstrip("/").lower()
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    if not host:
        return raw.rstrip("/").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    query.sort()
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def extract_experience_signature(text: str) -> tuple[float | None, float | None]:
    raw = str(text or "").lower().replace("–", "-").replace("—", "-")
    raw = re.sub(r"\s+", " ", raw).strip()
    ranges = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        raw,
    )
    if ranges:
        lows = [float(left) for left, _ in ranges]
        highs = [float(right) for _, right in ranges]
        return min(lows), max(highs)
    plus = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", raw)
    if plus:
        return float(plus.group(1)), None
    singles = re.findall(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", raw)
    if singles:
        years = [float(value) for value in singles]
        return min(years), max(years)
    return None, None


def _description_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]{3,}", str(value or "").lower()))
    noise = {
        "years", "year", "experience", "apply", "applicant", "today",
        "days", "day", "hours", "hour", "ago", "remote", "india",
        "linkedin", "job", "jobs", "company", "location",
    }
    return tokens - noise


def description_similarity(left: str, right: str) -> float:
    a = _description_tokens(left)
    b = _description_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def title_similarity(left: str, right: str) -> float:
    a = normalize_title(left)
    b = normalize_title(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def experience_equal(left: str, right: str) -> bool:
    left_sig = extract_experience_signature(left)
    right_sig = extract_experience_signature(right)
    return left_sig != (None, None) and left_sig == right_sig


def canonical_match_score(job: dict, candidate: dict) -> tuple[int, str]:
    job_url = canonicalize_url(job.get("url", ""))
    candidate_url = canonicalize_url(candidate.get("canonical_url") or candidate.get("url", ""))
    if job_url and candidate_url and job_url == candidate_url:
        return 100, "canonical_url"

    company_match = normalize_company(job.get("company", "")) == normalize_company(candidate.get("company", ""))
    location_match = normalize_location(job.get("location", "")) == normalize_location(candidate.get("location", ""))
    title_sim = title_similarity(job.get("title", ""), candidate.get("title", ""))
    if not (company_match and location_match) or title_sim < 0.88:
        return 0, "none"

    if experience_equal(
        f"{job.get('title', '')} {job.get('description', '')}",
        f"{candidate.get('title', '')} {candidate.get('description', '')}",
    ):
        return (98 if title_sim >= 0.99 else 95), "metadata_experience"

    desc_sim = description_similarity(job.get("description", ""), candidate.get("description", ""))
    if title_sim >= 0.99 and desc_sim >= 0.60:
        return 97, "metadata_description"
    if title_sim >= 0.99 and desc_sim >= 0.35:
        return 93, "metadata_description"

    return 88, "metadata_probable"


def canonical_identity(job: dict) -> dict:
    return {
        "company_norm": normalize_company(job.get("company", "")),
        "title_norm": normalize_title(job.get("title", "")),
        "location_norm": normalize_location(job.get("location", "")),
        "url_norm": canonicalize_url(job.get("url", "")),
    }


def auto_link_allowed(score: int, method: str) -> bool:
    return score >= 95 and method != "none"
