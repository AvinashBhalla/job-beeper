"""Best-effort public job-board adapters.

Board strategy:
- LinkedIn: small public guest window, deliberately low request volume.
- Naukri: JobSpy's current Naukri adapter, which uses Naukri's structured
  /jobapi/v3/search path and generates the required nkparam token.
- Instahyre: public /api/v1/job_search/ JSON feed; HTML is not used.
"""
import re
import time
import datetime as dt
import requests
from bs4 import BeautifulSoup

try:
    from jobspy import scrape_jobs
except ImportError:
    scrape_jobs = None

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.instahyre.com/",
}

def _text(node):
    return " ".join(node.stripped_strings) if node else ""

def _soup(url, params=None, timeout=30):
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def _job(id_, company, title, location, url, posted=None, desc=""):
    return {"id": id_, "company": company or "", "title": title or "",
            "location": location or "", "url": url, "posted": posted,
            "desc": (desc or "").lower()}

def linkedin_guest(keyword):
    """Fetch a small, fresh LinkedIn window instead of broad pagination."""
    base = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": keyword,
        "location": "India",
        "f_TPR": "r86400",
        "f_E": "2,3",
        "sortBy": "DD",
    }
    for start in (0, 25):
        params["start"] = start
        try:
            soup = _soup(base, params)
        except requests.HTTPError as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = min(60, max(2, int(retry_after))) if retry_after and retry_after.isdigit() else 10
                time.sleep(wait)
                soup = _soup(base, params)
            else:
                raise
        cards = soup.select("li")
        if not cards:
            break
        for card in cards:
            link = card.select_one("a.base-card__full-link") or card.select_one("a[href*='/jobs/view/']")
            title = card.select_one("h3.base-search-card__title")
            company = card.select_one("h4.base-search-card__subtitle")
            loc = card.select_one("span.job-search-card__location")
            posted = card.select_one("time")
            if not link or not title:
                continue
            url = link.get("href", "").split("?")[0]
            jid = re.search(r"jobs/view/(\d+)", url)

            # LinkedIn's guest HTML often puts only the calendar date in the
            # <time datetime> attribute (e.g. 2026-10-07), while the visible
            # text contains the useful relative age ("5 minutes ago").
            # Prefer that relative value so the dashboard can correctly place
            # genuinely fresh jobs in its "Last hour" filter.
            posted_value = _text(posted) if posted else ""
            if not re.search(r"(?:just now|today|yesterday|\d+\s*(?:minute|min|hour|hr|day|week)s?\s*ago)", posted_value.lower()):
                posted_value = posted.get("datetime") if posted else None

            yield _job(
                f"li-{jid.group(1) if jid else url}", _text(company), _text(title),
                _text(loc), url, posted_value, _text(card)
            )

def _naukri_posted_from_url(url):
    """Recover the posting date from Naukri's numeric job id when JobSpy only
    returns a date-only value. Naukri job ids commonly begin with DDMMYY.
    """
    match = re.search(r"-(\d{11,})(?:[/?#-]|$)", str(url))
    if not match:
        return None
    raw = match.group(1)
    try:
        day, month, year = int(raw[:2]), int(raw[2:4]), int(raw[4:6])
        year += 2000
        candidate = dt.datetime(year, month, day, tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None
    if candidate > dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1):
        return None
    return candidate.isoformat()

def naukri_public(keyword):
    """Use JobSpy's Naukri-only adapter; it targets the structured search API."""
    if scrape_jobs is None:
        raise RuntimeError("python-jobspy is not installed")
    frame = scrape_jobs(
        site_name=["naukri"],
        search_term=keyword,
        location="India",
        results_wanted=30,
        hours_old=72,
        fetch_description=True,
        description_format="plain",
        verbose=0,
    )
    if frame is None or frame.empty:
        return
    for row in frame.to_dict("records"):
        job_id = str(row.get("id") or row.get("job_url") or "")
        url = row.get("job_url") or row.get("job_url_direct") or ""
        if not url:
            continue
        location = row.get("location") or ""
        company = row.get("company") or row.get("company_name") or ""
        title = row.get("title") or ""
        desc = row.get("description") or ""
        experience = row.get("experience_range") or ""
        skills = row.get("skills") or ""
        desc = " ".join(str(x) for x in (desc, experience, skills) if x)
        posted = row.get("date_posted")
        if hasattr(posted, "isoformat"):
            posted = posted.isoformat()
        url_posted = _naukri_posted_from_url(url)
        if url_posted:
            posted = url_posted
        yield _job(
            f"nk-{job_id}",
            str(company),
            str(title),
            str(location),
            str(url),
            posted,
            str(desc),
        )

def _instahyre_items(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("jobs", "jobDetails", "results", "data", "job_details"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested_items = (
                value.get(nested)
                for nested in ("jobs", "results", "data")
            )
            for items in nested_items:
                if isinstance(items, list):
                    return items
    return []

def _instahyre_location(item):
    value = item.get("locations") or item.get("location") or item.get("locationsRaw")
    if isinstance(value, list):
        return ", ".join(
            str(item.get("name") if isinstance(item, dict) else item)
            for item in value
        )
    return str(value or "")

def _instahyre_url(item, job_id):
    value = item.get("url") or item.get("publicUrl") or item.get("jobUrl")
    return str(value) if value else f"https://www.instahyre.com/job-{job_id}-"

def instahyre_public(_keyword=None):
    """Fetch the public JSON feed once; keyword matching happens downstream.

    The feed is intentionally fetched once per run rather than once per keyword:
    repeated keyword calls return overlapping pages and waste request budget.
    """
    url = "https://www.instahyre.com/api/v1/job_search/"
    params = {
        "jobLocations": "Bangalore",
        "limit": 35,
    }
    response = requests.get(url, params=params, headers=UA, timeout=30)
    response.raise_for_status()
    items = _instahyre_items(response.json())
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        job_id = item.get("jobId") or item.get("id") or item.get("jobID")
        if not job_id or str(job_id) in seen:
            continue
        seen.add(str(job_id))
        title = item.get("title") or item.get("candidateTitle") or item.get("jobTitle") or ""
        company = item.get("companyName") or item.get("company") or ""
        location = _instahyre_location(item)
        url = _instahyre_url(item, job_id)
        posted = (
            item.get("postedAt") or item.get("posted_at") or item.get("postedDate")
            or item.get("createdAt") or item.get("created_at") or item.get("scrapedAt")
        )
        skills = item.get("skills") or item.get("tags") or []
        functions = item.get("jobFunctions") or item.get("job_functions") or []
        exp_min = item.get("experienceMin")
        exp_max = item.get("experienceMax")
        exp = ""
        if exp_min is not None or exp_max is not None:
            exp = f" {exp_min or 0}-{exp_max or ''} years"
        desc = " ".join([
            str(item.get("description") or ""),
            str(item.get("descriptionText") or ""),
            _text(skills) if isinstance(skills, dict) else " ".join(map(str, skills)) if isinstance(skills, list) else str(skills),
            _text(functions) if isinstance(functions, dict) else " ".join(map(str, functions)) if isinstance(functions, list) else str(functions),
            exp,
        ])
        yield _job(f"ih-{job_id}", str(company), str(title), location, url, posted, desc)
