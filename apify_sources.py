"""Apify-backed job-board adapters.

These adapters call public job-scraping Actors through Apify's synchronous dataset API.
The Actor IDs are configurable in config.json so a provider can be swapped without
rewriting the pipeline. No Apify token is stored in the repository.
"""
import datetime as dt
import os
import re
import requests

API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
TIMEOUT = 120

def _text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_text(x) for x in value)
    if isinstance(value, dict):
        for key in ("name", "label", "value", "text"):
            if value.get(key):
                return _text(value[key])
        return ", ".join(f"{k}: {_text(v)}" for k, v in value.items() if v)
    return str(value).strip()

def _first(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return None

def _parse_posted(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        stamp = value / 1000 if value > 1e11 else value
        return dt.datetime.fromtimestamp(stamp, dt.timezone.utc).isoformat()
    raw = str(value).strip()
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.isoformat()
    except ValueError:
        pass
    now = dt.datetime.now(dt.timezone.utc)
    text = raw.lower()
    if text in {"today", "just now"}:
        return now.isoformat()
    if text == "yesterday":
        return (now - dt.timedelta(days=1)).isoformat()
    match = re.search(r"(\d+)\s*(minute|min|hour|hr|day|week)s?\s*(?:ago)?", text)
    if match:
        amount = int(match.group(1))
        seconds = {"minute": 60, "min": 60, "hour": 3600, "hr": 3600,
                   "day": 86400, "week": 604800}[match.group(2)]
        return (now - dt.timedelta(seconds=amount * seconds)).isoformat()
    return None

def _job(source, item):
    job_id = _first(item, "jobId", "job_id", "id", "jobID", "externalId")
    url = _first(item, "url", "jobUrl", "job_url", "applyUrl", "apply_url", "link")
    title = _first(item, "title", "jobTitle", "position", "name")
    company = _first(item, "company", "companyName", "company_name", "employer")
    location = _first(item, "location", "locations", "locationName", "city")
    posted = _first(item, "postedAt", "posted_at", "postedDate", "posted_date",
                    "publicationDate", "publication_date", "createdAt", "created_at",
                    "updatedAt", "updated_at", "datePosted", "date_posted", "jobPosted")
    desc = _first(item, "description", "descriptionText", "descriptionPlain",
                  "jobDescription", "job_description", "summary", "details")
    skills = _first(item, "skills", "tagsAndSkills", "tags", "skill")
    experience = _first(item, "experience", "experienceRange", "experience_range",
                        "experienceRequired", "experience_required", "yearsOfExperience")
    if not url and not job_id:
        return None
    stable = str(job_id or url)
    return {
        "id": f"{source}-apify-{stable}",
        "company": _text(company),
        "title": _text(title),
        "location": _text(location),
        "url": _text(url) or "",
        "posted": _parse_posted(posted),
        "desc": (_text(desc) + " " + _text(skills) + " " + _text(experience)).lower(),
    }

def _run(actor, payload):
    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        raise RuntimeError("APIFY_API_TOKEN is not configured")
    response = requests.post(
        API.format(actor=actor),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Apify actor {actor} returned non-list dataset output")
    return data

def linkedin(cfg, keyword):
    # axiomworks/linkedin-jobs-scraper accepts a keyword string, location,
    # includeDetails and maxResults. Keep the payload to documented fields.
    payload = {
        "keywords": keyword,
        "location": cfg.get("location", "India"),
        "includeDetails": True,
        "maxResults": int(cfg.get("max_jobs_per_query", 50)),
    }
    actor = cfg["actors"]["linkedin"]
    return [j for j in (_job("linkedin", x) for x in _run(actor, payload)) if j]

def naukri(cfg, keyword):
    payload = {
        "keyword": keyword,
        "location": cfg.get("naukri_location", "Bangalore"),
        "maxResultsPerQuery": int(cfg.get("max_jobs_per_query", 50)),
    }
    actor = cfg["actors"]["naukri"]
    return [j for j in (_job("naukri", x) for x in _run(actor, payload)) if j]

def instahyre(cfg, keyword):
    payload = {
        "keywords": [keyword],
        "locations": cfg.get("locations", ["Bangalore", "Gurgaon", "Delhi", "India"]),
        "maxJobsPerSearch": int(cfg.get("max_jobs_per_query", 50)),
    }
    actor = cfg["actors"]["instahyre"]
    return [j for j in (_job("instahyre", x) for x in _run(actor, payload)) if j]
