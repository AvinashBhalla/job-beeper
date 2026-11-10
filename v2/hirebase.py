"""Quota-aware optional Hirebase client.

This module has no import-time network activity. All metered calls require an
explicit call from an admin-only workflow, estimate first, and a local budget
reservation before search. The API key is read only from HIREBASE_API_KEY.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from typing import Any
from urllib.parse import urlsplit

import requests

API_BASE = "https://api.hirebase.org"
API_TIMEOUT_SECONDS = 20
MAX_RESULT_LIMIT = 4
MONTHLY_JOB_BUDGET = 400  # Free plan is 500; retain a 100-result safety buffer.
DAILY_JOB_BUDGET = 12
PROVIDER_DAILY_BUDGET = 4
ALLOWED_PROVIDERS = frozenset({"workday", "keka", "darwinbox"})
USAGE_METER = "m_jobs_api_calls"


class HirebaseError(RuntimeError):
    """Sanitized integration or quota failure; never includes API key or URL query."""

    def __init__(self, message: str, *, response: requests.Response | None = None):
        super().__init__(message)
        self.response = response


def api_key_configured() -> bool:
    return bool(os.getenv("HIREBASE_API_KEY", "").strip())


def _api_key() -> str:
    value = os.getenv("HIREBASE_API_KEY", "").strip()
    if not value:
        raise HirebaseError("Hirebase API key is not configured in this environment.")
    if len(value) > 256 or any(ch.isspace() for ch in value):
        raise HirebaseError("Hirebase API key format is invalid.")
    return value


def provider_query(provider: str, *, limit: int = MAX_RESULT_LIMIT,
                   ingested_after: str | None = None, page: int = 1) -> dict[str, Any]:
    """Build a broad, non-user-specific India query for one ATS platform."""
    name = str(provider or "").strip().lower()
    if name not in ALLOWED_PROVIDERS:
        raise ValueError("Unsupported Hirebase ATS provider.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULT_LIMIT:
        raise ValueError(f"Hirebase query limit must be between 1 and {MAX_RESULT_LIMIT}.")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1 or page > 100_000:
        raise ValueError("Hirebase page must be a positive integer no greater than 100000.")
    payload: dict[str, Any] = {
        "job_board": [name],
        "geo_locations": [{"country": "India"}],
        "sort_order": "asc" if ingested_after else "desc",
        "page": page,
        "limit": limit,
        "hide_recruiting_agencies": "true",
        "filter_incomplete_jobs": "true",
    }
    if ingested_after:
        # Hirebase recommends an ingested_after cursor with a two-hour overlap;
        # sort oldest-first so a small result limit does not starve earlier jobs.
        payload["ingested_after"] = ingested_after
        payload["sort_by"] = "first_ingested"
    else:
        # First run is a small discovery sample; later runs switch to incremental.
        payload["days_ago"] = 7
        payload["sort_by"] = "date_posted"
    return payload


def _request(method: str, path: str, *, payload: dict[str, Any] | None = None, requester=None) -> requests.Response:
    if not path.startswith("/v2/") or ".." in path:
        raise HirebaseError("Invalid Hirebase API path.")
    try:
        request_fn = requester or requests.request
        response = request_fn(
            method,
            API_BASE + path,
            headers={
                "x-api-key": _api_key(),
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "JobBeeper/0.1 (+https://github.com/AvinashBhalla/job-beeper)",
            },
            json=payload,
            timeout=API_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.Timeout as exc:
        raise HirebaseError("Hirebase request timed out; metered search status may be uncertain.") from exc
    except requests.RequestException as exc:
        raise HirebaseError(f"Hirebase request failed ({type(exc).__name__}).") from exc

    if response.is_redirect or 300 <= response.status_code < 400:
        raise HirebaseError("Hirebase returned a redirect; redirects are not followed.")
    if response.status_code == 401:
        raise HirebaseError("Hirebase rejected the configured API key (401).", response=response)
    if response.status_code == 403:
        raise HirebaseError("Hirebase denied this API request (403).", response=response)
    if response.status_code == 429:
        billing_code = response.headers.get("X-Billing-Code", "")
        if billing_code == "limit_exceeded":
            raise HirebaseError("Hirebase monthly job allowance is exhausted.", response=response)
        raise HirebaseError("Hirebase request rate limit reached; retry later.", response=response)
    if not response.ok:
        raise HirebaseError(f"Hirebase returned HTTP {response.status_code}.", response=response)
    return response


def _json_object(response: requests.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HirebaseError("Hirebase returned invalid JSON.", response=response) from exc
    if not isinstance(value, dict):
        raise HirebaseError("Hirebase returned an unexpected response shape.", response=response)
    return value


def estimate(payload: dict[str, Any], *, requester=None) -> int:
    """Estimate job credits at zero job-credit cost."""
    response = _request("POST", "/v2/jobs/estimate", payload=payload, requester=requester)
    body = _json_object(response)
    cost = body.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
        raise HirebaseError("Hirebase estimate response did not contain a valid cost.")
    return cost


def usage_summary(*, requester=None) -> dict[str, Any]:
    """Read the live billing period and job allowance without fetching job rows."""
    response = _request("GET", "/v2/billing/usage/summary", requester=requester)
    body = _json_object(response)
    meters = body.get("meters")
    if not isinstance(meters, list):
        raise HirebaseError("Hirebase usage response did not contain meters.")
    meter = next((item for item in meters if isinstance(item, dict)
                  and item.get("event_name") == USAGE_METER), None)
    if meter is None:
        raise HirebaseError("Hirebase usage response did not include the Jobs meter.")
    remaining = meter.get("remaining")
    included = meter.get("included")
    used = meter.get("used")
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0
           for x in (remaining, included, used)):
        raise HirebaseError("Hirebase Jobs meter returned invalid counters.")
    raw_status = body.get("subscription_status")
    status = str(raw_status or "").lower()
    period_start = body.get("period_start")
    period_end = body.get("period_end")
    if period_start is None and period_end is None and raw_status is None:
        # Hirebase Free accounts have no Stripe subscription window. Their
        # included allowances reset at 00:00 UTC on the first of each month.
        utc_now = dt.datetime.now(dt.timezone.utc)
        month_start = utc_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        period_start = month_start.isoformat()
        period_end = next_month.isoformat()
        status = "free"
    elif status in {"active", "trialing"} and isinstance(period_start, str) and isinstance(period_end, str):
        pass
    else:
        raise HirebaseError("Hirebase usage response did not contain a supported active or Free billing period.")
    return {
        "subscription_status": status,
        "period_start": period_start,
        "period_end": period_end,
        "used": used,
        "included": included,
        "remaining": remaining,
        "overage_mode": str(meter.get("overage_mode") or ""),
    }


def usage_from_headers(headers: Any) -> dict[str, Any] | None:
    """Extract the metered allowance after a search; None means unverifiable."""
    prefix = "Hirebase-Usage-"
    remaining = headers.get(prefix + "Included-Remaining")
    used = headers.get(prefix + "Included-Used")
    meter = headers.get(prefix + "Meter")
    if meter != USAGE_METER or remaining is None or used is None:
        return None
    try:
        remaining_n = int(remaining)
        used_n = int(used)
    except (TypeError, ValueError):
        return None
    if remaining_n < 0 or used_n < 0:
        return None
    return {"included_remaining": remaining_n, "included_used": used_n}


def search(payload: dict[str, Any], *, requester=None) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, int]]:
    """Run one already-budgeted search; caller must reserve quota first."""
    response = _request("POST", "/v2/jobs/search", payload=payload, requester=requester)
    body = _json_object(response)
    jobs = body.get("jobs")
    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        raise HirebaseError("Hirebase search response did not contain a valid jobs list.")
    if len(jobs) > int(payload.get("limit") or MAX_RESULT_LIMIT):
        raise HirebaseError("Hirebase returned more jobs than the requested limit.", response=response)
    page = body.get("page", payload.get("page", 1))
    total_pages = body.get("total_pages")
    total_count = body.get("total_count")
    if (isinstance(page, bool) or not isinstance(page, int) or page < 1
            or isinstance(total_pages, bool) or not isinstance(total_pages, int) or total_pages < 1
            or isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0):
        raise HirebaseError("Hirebase search response omitted valid pagination metadata.", response=response)
    return jobs, usage_from_headers(response.headers), {
        "page": page, "total_pages": total_pages, "total_count": total_count,
    }


def parse_posted_at(value: Any) -> tuple[dt.datetime | None, str]:
    if not isinstance(value, str) or not value.strip():
        return None, "unknown"
    raw = value.strip()
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        # Hirebase sometimes represents date_posted as a date-only value.
        try:
            parsed = dt.datetime.combine(dt.date.fromisoformat(raw[:10]), dt.time.min, tzinfo=dt.timezone.utc)
            return parsed, "date"
        except ValueError:
            return None, "unknown"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed, "minute" if "T" in raw and len(raw) >= 16 else "date"


def normalize_provider_job(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Hirebase job to JobBeeper's normalized-job input."""
    raw_id = str(item.get("_id") or item.get("md5_hash") or item.get("platform_job_id") or "").strip()
    company = str(item.get("company_name") or "").strip()
    title = str(item.get("job_title") or item.get("job_title_raw") or "").strip()
    url = str(item.get("application_link") or "").strip()
    parsed_url = urlsplit(url)
    if (
        not raw_id or not company or not title or len(url) > 2_048
        or parsed_url.scheme != "https" or not parsed_url.hostname
        or parsed_url.username is not None or parsed_url.password is not None
        or parsed_url.fragment or parsed_url.port not in (None, 443)
    ):
        return None

    locations = item.get("locations")
    labels: list[str] = []
    if isinstance(locations, list):
        for location in locations:
            if not isinstance(location, dict):
                continue
            label = ", ".join(str(location.get(key) or "").strip()
                              for key in ("city", "region", "country")
                              if str(location.get(key) or "").strip())
            if label and label not in labels:
                labels.append(label)
    location_text = "; ".join(labels) or str(item.get("location_raw") or item.get("location_type") or "Unspecified").strip()

    description = item.get("description")
    from bs4 import BeautifulSoup
    description = BeautifulSoup(str(description or ""), "html.parser").get_text(" ", strip=True)[:30_000]
    provider = str(item.get("job_board") or "unknown").strip().lower()
    posted_at, precision = parse_posted_at(item.get("date_posted"))
    source_details = {
        "external_index": "hirebase",
        "hirebase_id": raw_id,
        "job_board": provider,
        "first_ingested": item.get("first_ingested"),
        "job_board_link": item.get("job_board_link"),
        "company_slug": item.get("company_slug"),
        "company_link": item.get("company_link"),
        "job_type": item.get("job_type"),
        "location_type": item.get("location_type"),
        "experience_level": item.get("experience_level"),
        "yoe_range": item.get("yoe_range"),
        "salary_range": item.get("salary_range"),
        "requirements_summary": item.get("requirements_summary"),
    }
    return {
        "source": "hirebase",
        "source_job_id": f"{provider}:{raw_id}",
        "company": company,
        "title": title,
        "location": location_text,
        "url": url,
        "posted_at": posted_at,
        "posted_precision": precision,
        "description": description,
        "source_details": source_details,
    }


def provider_allowance(summary: dict[str, Any], *, local_monthly_used: int,
                       local_daily_used: int, provider_daily_used: int,
                       monthly_cap: int = MONTHLY_JOB_BUDGET,
                       daily_cap: int = DAILY_JOB_BUDGET,
                       provider_daily_cap: int = PROVIDER_DAILY_BUDGET) -> int:
    """Return remaining job rows this integration is allowed to spend."""
    caps = (
        max(0, monthly_cap - max(0, local_monthly_used)),
        max(0, daily_cap - max(0, local_daily_used)),
        max(0, provider_daily_cap - max(0, provider_daily_used)),
        max(0, int(summary.get("remaining", 0))),
    )
    return min(caps)
