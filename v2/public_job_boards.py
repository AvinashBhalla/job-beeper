"""Bounded readers for public employer job boards with common scheduling needs."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

LABELS = {
    "teamtailor": "Teamtailor",
    "breezy": "Breezy HR",
    "bamboohr": "BambooHR",
    "jobvite": "Jobvite",
    "hireology": "Hireology",
    "rippling": "Rippling ATS",
    "oraclecloud": "Oracle Cloud Recruiting",
    "avature": "Avature",
    "ycombinator": "Y Combinator",
    "icims": "iCIMS",
    "freshteam": "Freshteam",
    "cutshort": "Cutshort",
    "hrsmart": "HRsmart",
    "ukg": "UKG Pro / UltiPro",
    "phenom": "Phenom People",
    "zoho": "Zoho Recruit",
    "taleo": "Oracle Taleo",
    "successfactors": "SAP SuccessFactors",
    "peoplestrong": "PeopleStrong",
}
BOARDS_WITH_DESCRIPTIONS = frozenset({"teamtailor", "cutshort"})
PHENOM_PATHS = {
    "www.careers.philips.com": "/global/en",
    "jobs.cvshealth.com": "/us/en",
}
SUCCESSFACTORS_HOSTS = frozenset({"jobs.bostonscientific.com", "jobs.lubrizol.com"})
SUCCESSFACTORS_JOB = r"/job/[^/]+/(\d{1,18})"
MAX_BOARDS = 30
DETAILS_PER_POLL = 10
MAX_BODY_BYTES = 8 * 1024 * 1024
HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
TENANT = r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
ORACLE_API = "/hcmRestApi/resources/latest/recruitingCEJobRequisition"
ZOHO_OPENINGS = "/recruit/v2/public/Job_Openings"
PEOPLESTRONG_API = "/api/cp/rest/altone/cp"
PEOPLESTRONG_JOB = rf"/job/detail/({TENANT})"
TEAMTAILOR_NS = "{https://teamtailor.com/locations}"
WORKPLACE = {
    "remote": "remote", "fully_remote": "remote", "hybrid": "hybrid",
    "flexible_remote": "hybrid", "none": "on_site", "on_site": "on_site",
    "no_remote": "on_site", "no_remote_work": "on_site", "onsite": "on_site",
}


@dataclass(frozen=True)
class Board:
    source: str
    key: str
    url: str
    host: str
    tenant: str = ""


@dataclass
class Posting:
    id: str
    title: str
    url: str
    locations: list[str] = field(default_factory=list)
    description: str = ""
    published_at: datetime | None = None
    precision: str = "unknown"
    details: dict = field(default_factory=dict)
    company: str = ""


def detect(value: str) -> Board | None:
    """Recognize only the ATS-owned public host and the employer's board root."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        url = urlsplit(value.strip())
        host = (url.hostname or "").lower()
        if url.scheme != "https" or url.username is not None or url.password is not None or url.port not in (None, 443):
            return None
    except ValueError:
        return None
    path = url.path.rstrip("/")
    origin = f"https://{host}"
    if re.fullmatch(rf"{HOST_LABEL}(?:\.na)?\.teamtailor\.com", host):
        return Board("teamtailor", host.removesuffix(".teamtailor.com"), origin + "/jobs", host)
    if re.fullmatch(rf"{HOST_LABEL}\.breezy\.hr", host):
        return Board("breezy", host.removesuffix(".breezy.hr"), origin, host)
    if re.fullmatch(rf"{HOST_LABEL}\.bamboohr\.com", host) and re.match(r"^/(?:careers|jobs)(?:/|$)", path):
        return Board("bamboohr", host.removesuffix(".bamboohr.com"), origin + "/careers", host)
    if host == "jobs.jobvite.com":
        match = re.fullmatch(rf"/(?:careers/)?({TENANT})(?:/jobs|/job/{TENANT}(?:/apply)?|/jobAlerts)?", path)
        if match:
            tenant = match[1]
            return Board("jobvite", tenant.lower(), f"{origin}/{tenant}/", host, tenant)
    if host == "careers.hireology.com":
        match = re.fullmatch(rf"/({TENANT})(?:/\d+/(?:description|apply))?", path)
        if match:
            tenant = match[1]
            return Board("hireology", tenant.lower(), f"{origin}/{tenant}", host, tenant)
    if host == "ats.rippling.com":
        match = re.fullmatch(rf"/({TENANT})/jobs(?:/{UUID}(?:/apply)?)?", path)
        if match:
            tenant = match[1]
            return Board("rippling", tenant.lower(), f"{origin}/{tenant}/jobs", host, tenant)
    if re.fullmatch(rf"{HOST_LABEL}\.fa\.{HOST_LABEL}\.oraclecloud\.com", host):
        match = re.fullmatch(
            rf"/hcmUI/CandidateExperience/[A-Za-z-]{{2,12}}/sites/({TENANT})(?:/jobs|/job/{TENANT})?", path,
        )
        if match:
            site = match[1]
            return Board("oraclecloud", f"{host}:{site.lower()}",
                         f"{origin}/hcmUI/CandidateExperience/en/sites/{site}/jobs", host, site)
    if re.fullmatch(rf"{HOST_LABEL}\.avature\.net", host):
        match = re.fullmatch(rf"/({TENANT})(?:/SearchJobs(?:/.*)?|/JobDetail/[^/]+/\d+)?", path)
        if match:
            portal = match[1]
            return Board("avature", f"{host.removesuffix('.avature.net')}:{portal.lower()}",
                         f"{origin}/{portal}/SearchJobs", host, portal)
    if host == "www.ycombinator.com" and path in {"/jobs/role/all", "/jobs/role/all/india"}:
        key = "india" if path.endswith("/india") else "all"
        return Board("ycombinator", key, origin + path, host)
    if re.fullmatch(rf"{HOST_LABEL}\.icims\.com", host) and re.fullmatch(r"/jobs(?:/search|/\d+/[^/]+/job)?", path):
        return Board("icims", host.removesuffix(".icims.com"), origin + "/jobs/search", host)
    if re.fullmatch(rf"{HOST_LABEL}\.freshteam\.com", host) and re.fullmatch(r"/jobs(?:/[-A-Za-z0-9_]{3,50}/[^/]+)?", path):
        return Board("freshteam", host.removesuffix(".freshteam.com"), origin + "/jobs", host)
    if host == "cutshort.io":
        match = re.fullmatch(r"/jobs/([a-z0-9-]{1,100})", path)
        if match:
            return Board("cutshort", match[1], origin + path, host)
    if re.fullmatch(rf"{HOST_LABEL}(?:\.hua)?\.hrsmart\.com", host) and re.fullmatch(
        r"/hr/ats/(?:JobSearch/(?:index|search)|Posting/view/\d+)", path,
    ):
        return Board("hrsmart", host.removesuffix(".hrsmart.com"), origin + "/hr/ats/JobSearch/index", host)
    if re.fullmatch(r"recruiting\d*\.ultipro\.(?:com|ca)", host):
        match = re.fullmatch(rf"/({TENANT})/JobBoard/({UUID})(?:/OpportunityDetail|/OpportunityList)?", path, re.I)
        if match:
            tenant, board_id = match.groups()
            return Board("ukg", f"{tenant.lower()}:{board_id.lower()}",
                         f"{origin}/{tenant}/JobBoard/{board_id.lower()}", host, tenant)
    if host in PHENOM_PATHS:
        prefix = PHENOM_PATHS[host]
        if re.fullmatch(rf"{prefix}/(?:search-results|job/{TENANT}(?:/[^/]+)?)", path):
            return Board("phenom", host, origin + prefix + "/search-results", host)
    if re.fullmatch(rf"{HOST_LABEL}\.zohorecruit\.(?:com|eu|in)", host):
        match = re.fullmatch(rf"/jobs/({TENANT})(?:/\d{{1,30}}(?:/[^/]+)?)?", path)
        if match:
            page = match[1]
            return Board("zoho", f"{host}:{page.lower()}", f"{origin}/jobs/{page}", host, page)
    if re.fullmatch(rf"{HOST_LABEL}\.taleo\.net", host):
        match = re.fullmatch(rf"/careersection/({TENANT})(?:/(?:jobsearch|joblist|jobdetail|moresearch|default)\.ftl)?", path)
        if match:
            section = match[1]
            return Board("taleo", f"{host}:{section.lower()}",
                         f"{origin}/careersection/{section}/jobsearch.ftl", host, section)
    if host in SUCCESSFACTORS_HOSTS and (path == "/search" or re.fullmatch(SUCCESSFACTORS_JOB, path)):
        return Board("successfactors", host, f"{origin}/search/", host)
    if re.fullmatch(rf"{HOST_LABEL}\.peoplestrong\.com", host) and (
        path == "/job/joblist" or re.fullmatch(PEOPLESTRONG_JOB, path)
    ):
        return Board("peoplestrong", host, f"{origin}/job/joblist", host)
    return None


def _read(get, url: str, accept: str, **kwargs) -> bytearray:
    with get(url, accept=accept, **kwargs) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected public board response status.")
        body = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                raise ValueError("Public jobs response exceeds the response limit.")
            body.extend(chunk)
        return body


class _PublicFeedTree(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("Document type declarations are not allowed in public job feeds.")


def _publication(value: str, *, rss: bool = False) -> tuple[datetime | None, str]:
    iso_date = re.sub(r"(?: UTC|Z)$", "+00:00", value)
    iso_date = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", iso_date)
    try:
        stamp = parsedate_to_datetime(value) if rss else datetime.fromisoformat(iso_date)
    except (ValueError, TypeError, OverflowError):
        return None, "unknown"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return stamp.replace(tzinfo=timezone.utc), "date"
    if stamp.utcoffset() is None:
        return None, "unknown"
    return stamp.astimezone(timezone.utc), "minute"


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _description(value) -> str:
    return BeautifulSoup(_text(value), "html.parser").get_text("\n", strip=True)


def _location(*parts: str) -> str:
    return ", ".join(dict.fromkeys(part for part in parts if part))


def _posting_link(value: str, board: Board, path_pattern: str) -> tuple[str, str] | None:
    try:
        url = urlsplit(urljoin(board.url, value))
    except ValueError:
        return None
    if url.scheme != "https" or url.netloc.lower() != board.host:
        return None
    path = url.path.rstrip("/")
    match = re.fullmatch(path_pattern, path)
    if not match:
        return None
    return match[1], f"https://{board.host}{path}"


def _teamtailor(board: Board, get, *, probe: bool) -> list[Posting]:
    postings = []
    page_size = 100
    for page in range(1 if probe else 4):
        body = _read(get, board.url + ".rss", "application/rss+xml", params={
            "offset": page * page_size, "per_page": page_size,
        })
        root = ET.fromstring(body, parser=ET.XMLParser(target=_PublicFeedTree()))
        channel = root.find("channel") if root.tag == "rss" else None
        if channel is None:
            raise ValueError("Teamtailor did not return an RSS channel.")
        items = channel.findall("item")
        for item in items:
            link = _posting_link(item.findtext("link", ""), board, r"/(?:[a-z]{2}(?:-[A-Z]{2})?/)?jobs/(\d+)(?:-[A-Za-z0-9_-]+)?")
            title = item.findtext("title", "").strip()
            if not link or not title:
                continue
            locations = []
            for node in item.findall(f"{TEAMTAILOR_NS}locations/{TEAMTAILOR_NS}location"):
                city = node.findtext(f"{TEAMTAILOR_NS}city", "").strip()
                country = node.findtext(f"{TEAMTAILOR_NS}country", "").strip()
                name = node.findtext(f"{TEAMTAILOR_NS}name", "").strip()
                location = _location(city or name, country)
                if location and location not in locations:
                    locations.append(location)
            reported_id = item.findtext("guid", "").strip()
            job_id = reported_id if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", reported_id) else link[0]
            timestamp, precision = _publication(item.findtext("pubDate", "").strip(), rss=True)
            mode = item.findtext("remoteStatus", "").strip().lower()
            details = {
                "workplace_type": WORKPLACE.get(mode),
                "department": item.findtext(f"{TEAMTAILOR_NS}department", "").strip(),
                "role": item.findtext(f"{TEAMTAILOR_NS}role", "").strip(),
                "division": item.findtext(f"{TEAMTAILOR_NS}division", "").strip(),
            }
            postings.append(Posting(job_id, title, link[1], locations, _description(item.findtext("description")), timestamp, precision, details))
        if len(items) < page_size:
            break
    return postings


def _breezy(board: Board, get) -> list[Posting]:
    rows = json.loads(_read(get, board.url + "/json", "application/json"))
    if not isinstance(rows, list):
        raise ValueError("Breezy HR did not return its public positions list.")
    postings = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        link = _posting_link(_text(item.get("url")), board, r"/p/([a-f0-9]+)(?:-[A-Za-z0-9_-]+)?")
        title = _text(item.get("name"))
        if not link or not title or _text(item.get("id")) != link[0]:
            continue
        locations = []
        raw_locations = item.get("locations") or [item.get("location")]
        modes = set()
        for node in raw_locations if isinstance(raw_locations, list) else []:
            if not isinstance(node, dict):
                continue
            state = node.get("state")
            country = node.get("country")
            location = _location(
                _text(node.get("city")),
                _text(state.get("name")) if isinstance(state, dict) else _text(state),
                _text(country.get("name")) if isinstance(country, dict) else _text(country),
            ) or _text(node.get("name"))
            if location and location not in locations:
                locations.append(location)
            if isinstance(node.get("is_remote"), bool):
                modes.add(node["is_remote"])
        mode = "remote" if modes == {True} else "on_site" if modes == {False} else None
        timestamp, precision = _publication(_text(item.get("published_date")))
        role_type = item.get("type")
        details = {
            "workplace_type": mode, "department": _text(item.get("department")),
            "employment_type": _text(role_type.get("name")) if isinstance(role_type, dict) else "",
        }
        postings.append(Posting(link[0], title, link[1], locations, published_at=timestamp, precision=precision, details=details))
    postings.sort(key=lambda job: job.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return postings


def _bamboohr(board: Board, get) -> list[Posting]:
    data = json.loads(_read(get, board.url + "/list", "application/json"))
    rows = data.get("result") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError("BambooHR did not return its public careers list.")
    postings = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("id", ""))
        title = _text(item.get("jobOpeningName"))
        if not re.fullmatch(r"\d{1,18}", job_id) or not title:
            continue
        posting = Posting(job_id, title, f"{board.url}/{job_id}")
        _bamboohr_metadata(posting, item)
        postings.append(posting)
    return postings


def _bamboohr_metadata(job: Posting, item: dict) -> None:
    ats_location = item.get("atsLocation")
    legacy_location = item.get("location")
    ats_location = ats_location if isinstance(ats_location, dict) else {}
    legacy_location = legacy_location if isinstance(legacy_location, dict) else {}
    place = _location(
        _text(ats_location.get("city")) or _text(legacy_location.get("city")),
        _text(ats_location.get("state")) or _text(ats_location.get("province")) or _text(legacy_location.get("state")),
        _text(ats_location.get("country")) or _text(legacy_location.get("addressCountry")),
    )
    if place:
        job.locations = [place]
    job.details.update({key: value for key, value in {
        "department": _text(item.get("departmentLabel")),
        "employment_type": _text(item.get("employmentType")) or _text(item.get("employmentStatusLabel")),
        "minimum_experience": _text(item.get("minimumExperience")),
        "workplace_type": "remote" if item.get("isRemote") is True else None,
    }.items() if value})


def _html_list(board: Board, get) -> list[Posting]:
    body = _read(get, board.url, "text/html")
    page = BeautifulSoup(bytes(body), "html.parser")
    tenant = re.escape(board.tenant)
    path = rf"/{tenant}/job/({TENANT})" if board.source == "jobvite" else rf"/{tenant}/(\d+)/description"
    postings = []
    for anchor in page.select("a[href]"):
        link = _posting_link(anchor["href"], board, path)
        title = anchor.get_text(" ", strip=True)
        if link and title:
            postings.append(Posting(link[0], title, link[1]))
    # An empty, content-free interstitial is never accepted as a successful poll.
    if not postings and not page.select_one(".jv-wrapper, .careers-page, [class*='career-site'], .no-openings"):
        raise ValueError("Career portal did not contain recognizable public job listings.")
    return postings


def _oracle(board: Board, get, *, probe: bool) -> list[Posting]:
    jobs = []
    page_size = 50
    endpoint = f"https://{board.host}{ORACLE_API}s"
    for page in range(1 if probe else 8):
        body = _read(get, endpoint, "application/json", params={
            "onlyData": "true", "expand": "requisitionList",
            "finder": f"findReqs;siteNumber={board.tenant},limit={page_size},offset={page * page_size}",
        })
        payload = json.loads(body)
        items = payload.get("items") if isinstance(payload, dict) else None
        search = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
        rows = search.get("requisitionList")
        if not isinstance(rows, list):
            raise ValueError("Oracle Cloud did not return its public requisition list.")
        for item in rows:
            if not isinstance(item, dict):
                continue
            job_id = _text(item.get("Id"))
            title = _text(item.get("Title"))
            if not re.fullmatch(TENANT, job_id) or not title:
                continue
            link = board.url.removesuffix("/jobs") + "/job/" + job_id
            location = _text(item.get("PrimaryLocation"))
            published, precision = _publication(_text(item.get("PostedDate")))
            details = {
                "department": _text(item.get("Department")),
                "workplace_type": WORKPLACE.get(_text(item.get("WorkplaceType")).lower()),
                "employment_type": _text(item.get("JobSchedule")),
            }
            jobs.append(Posting(job_id, title, link, [location] if location else [], published_at=published,
                                precision=precision, details=details))
        if len(rows) < page_size:
            break
    return jobs


def _next_page(get, url, **kwargs) -> dict:
    page = BeautifulSoup(bytes(_read(get, url, "text/html", **kwargs)), "html.parser")
    script = page.select_one("script#__NEXT_DATA__")
    if script is None:
        raise ValueError("Career page did not contain public board data.")
    payload = json.loads(script.get_text())
    props = payload.get("props", {}).get("pageProps", {})
    if not isinstance(props, dict):
        raise ValueError("Career page contained an unexpected board format.")
    return props


def _rippling(board: Board, get, *, probe: bool) -> list[Posting]:
    jobs = []
    for page in range(1 if probe else 8):
        props = _next_page(get, board.url, params={"page": page} if page else None)
        queries = props.get("dehydratedState", {}).get("queries", [])
        listing = next((
            query.get("state", {}).get("data") for query in queries
            if isinstance(query.get("queryKey"), list)
            and query["queryKey"][:3] == ["board", board.tenant, "job-posts"]
        ), None)
        if not isinstance(listing, dict) or not isinstance(listing.get("items"), list):
            raise ValueError("Rippling page did not contain its public jobs list.")
        for item in listing["items"]:
            if not isinstance(item, dict):
                continue
            link = _posting_link(_text(item.get("url")), board, rf"/{re.escape(board.tenant)}/jobs/({UUID})")
            title = _text(item.get("name"))
            if not link or not title or item.get("id") != link[0]:
                continue
            department = item.get("department") or {}
            locations = [
                _location(_text(place.get("city")), _text(place.get("state")), _text(place.get("country")))
                or _text(place.get("name"))
                for place in item.get("locations", []) if isinstance(place, dict)
            ]
            modes = {
                WORKPLACE.get(_text(place.get("workplaceType")).lower())
                for place in item.get("locations", []) if isinstance(place, dict)
            }
            details = {
                "department": _text(department.get("displayName")) if isinstance(department, dict) else "",
                "workplace_type": next(iter(modes)) if len(modes) == 1 else None,
            }
            jobs.append(Posting(link[0], title, link[1], list(dict.fromkeys(filter(None, locations))), details=details))
        total_pages = listing.get("totalPages")
        if not isinstance(total_pages, int) or page + 1 >= total_pages or not listing["items"]:
            break
    return jobs


def _avature(board: Board, get, *, probe: bool) -> list[Posting]:
    jobs = []
    params = None
    offset = 0
    for page in range(1 if probe else 6):
        endpoint = board.url + "/" if params else board.url
        body = _read(get, endpoint, "text/html", params=params)
        listing = BeautifulSoup(bytes(body), "html.parser")
        cards = listing.select('h3 a[href*="/JobDetail/"]')
        for anchor in cards:
            link = _posting_link(anchor["href"], board, rf"/{re.escape(board.tenant)}/JobDetail/[^/]+/(\d+)")
            title = anchor.get_text(" ", strip=True)
            card = anchor.find_parent("article")
            place = card.select_one(".list-item-location") if card else None
            location = place.get_text(" ", strip=True) if place else ""
            if link and title:
                jobs.append(Posting(link[0], title, link[1], [location] if location else []))
        offsets = {}
        for link in listing.select('a[href*="jobOffset="]'):
            query = parse_qs(urlsplit(link["href"]).query)
            value = query.get("jobOffset", [""])[0]
            size = query.get("jobRecordsPerPage", [""])[0]
            if re.fullmatch(r"\d{1,5}", value) and re.fullmatch(r"\d{1,2}", size) and int(value) > offset:
                offsets[int(value)] = int(size)
        if not offsets:
            break
        offset = min(offsets)
        params = {"jobRecordsPerPage": offsets[offset], "jobOffset": offset}
    if not jobs and not listing.select_one('form[action*="SearchJobs"], [class*="list--jobs"]'):
        raise ValueError("Avature returned no recognizable public careers listing.")
    return jobs


def _icims(board: Board, get, *, probe: bool) -> list[Posting]:
    postings = []
    for page in range(1 if probe else 8):
        body = _read(get, board.url, "text/html", params={"pr": page, "in_iframe": 1})
        listing = BeautifulSoup(bytes(body), "html.parser")
        links = listing.select('a[href*="/jobs/"][href*="/job"]')
        added = 0
        for anchor in links:
            link = _posting_link(anchor["href"], board, r"/jobs/(\d+)/[^/]+/job")
            title = re.sub(r"^Title\s+", "", anchor.get_text(" ", strip=True))
            if link and title:
                added += 1
                postings.append(Posting(link[0], title, link[1]))
        if not added or not listing.select_one(f'a[href*="pr={page + 1}&"]'):
            break
    if not postings and not listing.select_one('[class*="iCIMS"]'):
        raise ValueError("iCIMS returned no recognizable careers page.")
    return postings


def _ycombinator(board: Board, get) -> list[Posting]:
    page = BeautifulSoup(bytes(_read(get, board.url, "text/html")), "html.parser")
    jobs = []
    path = rf"/companies/({TENANT})/jobs/[A-Za-z0-9]+-[A-Za-z0-9_-]+"
    for anchor in page.select('a[href*="/companies/"][href*="/jobs/"]'):
        link = _posting_link(anchor["href"], board, path)
        title = anchor.get_text(" ", strip=True)
        if not link or not title:
            continue
        label = anchor.parent.parent.select_one("span.font-bold")
        company = re.sub(r"\s*\([A-Z]\d{2}\)$", "", label.get_text(" ", strip=True)) if label else ""
        job_id = urlsplit(link[1]).path.rsplit("/", 1)[-1].split("-", 1)[0]
        jobs.append(Posting(job_id, title, link[1], company=company or link[0]))
    if not jobs:
        raise ValueError("Y Combinator returned no recognizable job cards.")
    return jobs


def _freshteam(board: Board, get) -> list[Posting]:
    page = BeautifulSoup(bytes(_read(get, board.url, "text/html")), "html.parser")
    jobs = []
    for anchor in page.select('a[href*="/jobs/"]'):
        link = _posting_link(anchor["href"], board, r"/jobs/([-A-Za-z0-9_]{3,50})/[^/]+")
        heading = anchor.select_one(".job-title")
        if link and heading:
            title = heading.get_text(" ", strip=True)
            if title:
                jobs.append(Posting(link[0], title, link[1]))
    if not jobs and not page.select_one('.job-list, [class*="job-listing"]'):
        raise ValueError("Freshteam returned no recognizable public jobs list.")
    return jobs


def _cutshort(board: Board, get) -> list[Posting]:
    props = _next_page(get, board.url)
    queries = props.get("dehydratedState", {}).get("queries", [])
    listing = next((
        query.get("state", {}).get("data") for query in queries
        if query.get("queryKey") == ["jobListData", board.key]
    ), None)
    page = listing.get("data", {}).get("pageData", {}) if isinstance(listing, dict) else {}
    rows = page.get("jobs")
    if not isinstance(rows, list):
        raise ValueError("Cutshort returned no public job category data.")
    postings = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        link = _posting_link(_text(item.get("publicUrl")), board, r"/job/([A-Za-z0-9_-]{2,300})")
        title = _text(item.get("headline"))
        job_id = _text(item.get("_id"))
        company_data = item.get("companyDetails")
        company = _text(company_data.get("name")) if isinstance(company_data, dict) else ""
        if not link or not title or not company or not re.fullmatch(r"[0-9a-f]{24}", job_id):
            continue
        experience = item.get("expRange")
        experience = experience if isinstance(experience, dict) else {}
        low, high = experience.get("min"), experience.get("max")
        if not (type(low) in {int, float} and type(high) in {int, float} and 0 <= low <= high <= 60):
            low = high = None
        locations = item.get("locations")
        skills = item.get("allSkills")
        roles = item.get("roleTypes")
        details = {
            "workplace_type": {"remote_only": "remote", "remote_not_okay": "on_site", "hybrid": "hybrid"}.get(
                _text(item.get("remoteType"))
            ),
            "employment_type": ", ".join(filter(None, map(_text, roles))) if isinstance(roles, list) else "",
            "experience_min_years": low, "experience_max_years": high,
            "key_skills": list(dict.fromkeys(filter(None, map(_text, skills))))[:50] if isinstance(skills, list) else [],
        }
        places = list(filter(None, map(_text, locations))) if isinstance(locations, list) else []
        postings.append(Posting(job_id, title, link[1], places, _description(item.get("sanitizedComment")),
                                details=details, company=company))
    return postings


def _hrsmart(board: Board, get) -> list[Posting]:
    with requests.Session() as session:
        html = _read(get, board.url, "text/html", session=session)
        page = BeautifulSoup(bytes(html), "html.parser")
        form = page.select_one('form#jobSearchForm[action="/hr/ats/JobSearch/search"]')
        if not form:
            raise ValueError("HRsmart career site did not expose its public search form.")
        form_data = {
            item["name"]: item.get("value", "") if item.get("type") == "hidden" else ""
            for item in form.select('input[name][type="hidden"], input[name][type="text"]')
        }
        html = _read(get, f"https://{board.host}/hr/ats/JobSearch/search", "text/html",
                     session=session, form_data=form_data)
        results = BeautifulSoup(bytes(html), "html.parser")
    jobs = []
    for anchor in results.select('a[href*="/hr/ats/Posting/view/"]'):
        link = _posting_link(anchor["href"], board, r"/hr/ats/Posting/view/(\d+)")
        title = anchor.get_text(" ", strip=True)
        if link and title:
            jobs.append(Posting(link[0], title, link[1]))
    if not jobs and not results.select_one('[id*="jobSearch"]'):
        raise ValueError("HRsmart returned no recognizable job search results.")
    return jobs


def _ukg_locations(item: dict) -> list[str]:
    places = item.get("Locations")
    locations = []
    for place in places if isinstance(places, list) else []:
        if not isinstance(place, dict):
            continue
        address = place.get("Address")
        address = address if isinstance(address, dict) else {}
        state, country = address.get("State"), address.get("Country")
        location = _location(
            _text(address.get("City")),
            _text(state.get("Name")) if isinstance(state, dict) else "",
            _text(country.get("Name")) if isinstance(country, dict) else "",
        ) or _text(place.get("LocalizedName"))
        if location and location not in locations:
            locations.append(location)
    return locations


def _ukg(board: Board, get, *, probe: bool) -> list[Posting]:
    postings = []
    page_size = 50
    for page in range(1 if probe else 6):
        raw = _read(get, board.url + "/JobBoardView/LoadSearchResults", "application/json", json_body={
            "opportunitySearch": {
                "Top": page_size, "Skip": page * page_size, "QueryString": "", "OrderBy": [], "Filters": [],
            },
        })
        listing = json.loads(raw)
        rows = listing.get("opportunities") if isinstance(listing, dict) else None
        if not isinstance(rows, list):
            raise ValueError("UKG did not return its public opportunity list.")
        for item in rows:
            if not isinstance(item, dict):
                continue
            job_id = _text(item.get("Id")).lower()
            title = _text(item.get("Title"))
            if not re.fullmatch(UUID, job_id) or not title:
                continue
            employment = item.get("FullTime")
            details = {
                "employment_type": "Full-time" if employment is True else "Part-time" if employment is False else "",
                "department": _text(item.get("JobCategoryName")),
            }
            published, precision = _publication(_text(item.get("PostedDate")))
            postings.append(Posting(
                job_id, title, f"{board.url}/OpportunityDetail?opportunityId={job_id}",
                _ukg_locations(item), published_at=published, precision=precision, details=details,
            ))
        total = listing.get("totalCount")
        if len(rows) < page_size or (isinstance(total, int) and (page + 1) * page_size >= total):
            break
    return postings


def _phenom(board: Board, get, *, probe: bool) -> list[Posting]:
    jobs = []
    seen = set()
    offset = 0
    for _ in range(1 if probe else 6):
        body = _read(get, board.url, "text/html", params={"from": offset, "s": 1} if offset else None)
        page = BeautifulSoup(bytes(body), "html.parser")
        listing = None
        for script in page.select("script"):
            code = script.get_text()
            marker = re.search(r"phApp\.ddo\s*=\s*(\{)", code)
            if marker:
                data, _ = json.JSONDecoder().raw_decode(code, marker.start(1))
                listing = data.get("eagerLoadRefineSearch", {}).get("data", {}).get("jobs")
                if isinstance(listing, list):
                    break
        if not isinstance(listing, list):
            raise ValueError("Phenom did not expose its public search results.")
        added = 0
        for item in listing:
            if not isinstance(item, dict):
                continue
            job_id, title = _text(item.get("jobSeqNo")), _text(item.get("title"))
            if not re.fullmatch(TENANT, job_id) or not title or job_id in seen:
                continue
            seen.add(job_id)
            added += 1
            places = item.get("multi_location_array")
            locations = list(dict.fromkeys(filter(None, map(_text, places)))) if isinstance(places, list) else []
            place = _text(item.get("cityStateCountry")) or _text(item.get("location"))
            if not locations and place:
                locations = [place]
            published, precision = _publication(_text(item.get("postedDate")).split("T", 1)[0])
            mode = _text(item.get("remote")).casefold().replace("-", "_").replace(" ", "_")
            details = {
                "department": _text(item.get("department")) or _text(item.get("category")),
                "employment_type": _text(item.get("type")),
                "workplace_type": WORKPLACE.get(mode),
            }
            url = board.url.removesuffix("/search-results") + "/job/" + job_id
            jobs.append(Posting(job_id, title, url, locations, published_at=published, precision=precision, details=details))
        if not added:
            break
        offset += len(listing)
    return jobs


def _zoho_rows(board: Board, get, job_id: str = "") -> list:
    endpoint = f"https://{board.host}{ZOHO_OPENINGS}"
    if job_id:
        endpoint += f"/{job_id}"
    data = json.loads(_read(get, endpoint, "application/json", params={"pagename": board.tenant}))
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Zoho Recruit did not return public job openings for this career page.")
    return rows


def _zoho_metadata(job: Posting, item: dict) -> None:
    location = _location(*(_text(item.get(key)) for key in ("City", "State", "Country")))
    if location:
        job.locations = [location]
    job.details.update({key: value for key, value in {
        "employment_type": _text(item.get("Job_Type")),
        "department": _text(item.get("Team")),
        "minimum_experience": _text(item.get("Work_Experience")),
        "workplace_type": "remote" if _text(item.get("Remote_Job")).lower() == "yes" else None,
    }.items() if value})


def _zoho(board: Board, get) -> list[Posting]:
    jobs = []
    for item in _zoho_rows(board, get):
        if not isinstance(item, dict) or item.get("Publish") is False:
            continue
        job_id = _text(item.get("id"))
        title = _text(item.get("Posting_Title")) or _text(item.get("Job_Opening_Name"))
        if not re.fullmatch(r"\d{1,30}", job_id) or not title:
            continue
        job = Posting(job_id, title, f"{board.url}/{job_id}")
        _zoho_metadata(job, item)
        jobs.append(job)
    return jobs


def _taleo_fields(url: str, interface: str, get) -> list[str]:
    # Fetch a new anonymous form and submit the same read action as the public page.
    with requests.Session() as session:
        page = BeautifulSoup(bytes(_read(get, url, "text/html", session=session)), "html.parser")
        form = page.select_one("form#ftlform")
        if not form:
            raise ValueError("Taleo did not return its public career search form.")
        hidden = [(item["name"], item.get("value", "")) for item in form.select('input[type="hidden"][name]')]
        state = dict(hidden)
        if not state.get("ftlpageid") or not state.get("csrftoken"):
            raise ValueError("Taleo did not return the anonymous career form state.")
        action = [
            ("ftlpageid", state["ftlpageid"]),
            ("ftlinterfaceid", interface),
            ("ftlcompid", "validateTimeZoneId"),
            ("jsfCmdId", "validateTimeZoneId"),
            ("ftlcompclass", "InitTimeZoneAction"),
            ("ftlcallback", "requisition_restoreDatesValues"),
            ("ftlajaxid", "ftlx1"),
            ("tz", "GMT+00:00"),
            ("tzname", "UTC"),
        ]
        session.headers.update({"Referer": url, "X-Requested-With": "XMLHttpRequest"})
        endpoint = url.split("?", 1)[0].removesuffix(".ftl") + ".ajax"
        response = _read(get, endpoint, "text/html", session=session, form_data=action + hidden)
    parts = response.decode("utf-8").split("!$!", 3)
    if len(parts) < 3 or parts[1] != interface + "!|!validateTimeZoneId":
        raise ValueError("Taleo returned an unexpected public career response.")
    return [unquote(field) for field in parts[2].split("!|!")]


def _taleo(board: Board, get) -> list[Posting]:
    fields = _taleo_fields(board.url, "requisitionListInterface", get)
    jobs = []
    root = board.url.removesuffix("jobsearch.ftl")
    # The classic listing sends the job ID for several row actions and repeats the title.
    for index in range(len(fields) - 11):
        job_id, title = fields[index:index + 2]
        if not re.fullmatch(r"\d{1,18}", job_id) or not title or title.isdecimal():
            continue
        if fields[index + 2:index + 9] != [job_id, title, *[job_id] * 5]:
            continue
        published, precision = None, "unknown"
        try:
            published = datetime.strptime(fields[index + 10], "%b %d, %Y").replace(tzinfo=timezone.utc)
            precision = "date"
        except ValueError:
            pass
        jobs.append(Posting(
            job_id, title, f"{root}jobdetail.ftl?job={job_id}", published_at=published, precision=precision,
            details={"requisition_number": fields[index + 11]},
        ))
    if not jobs and "No jobs available" not in fields and "No jobs found" not in fields:
        raise ValueError("Taleo returned no recognizable public requisitions in this layout.")
    return jobs


def _taleo_detail(job: Posting, get) -> None:
    fields = _taleo_fields(job.url, "requisitionDescriptionInterface", get)
    if job.title not in fields:
        raise ValueError("Taleo did not return the expected requisition title.")
    snippets = dict.fromkeys(
        field.removeprefix("!*!")
        for field in fields if field.startswith("!*!") and "<" in field
    )
    documents = [BeautifulSoup(value, "html.parser") for value in snippets]
    job.description = "\n\n".join(document.get_text("\n", strip=True) for document in documents).replace(r"\:", ":")
    for document in documents:
        label = document.find(string=re.compile(r"^\s*location\\?:", re.I))
        if label is None:
            continue
        line = label.find_parent(["p", "div", "li"])
        text = line.get_text(" ", strip=True) if line else str(label).strip()
        location = re.fullmatch(r"location:\s*(.{3,140})", text.replace(r"\:", ":"), re.I)
        if location:
            value = re.sub(r"(\d)\s+(st|nd|rd|th)\b", r"\1\2", location.group(1))
            job.locations = [value.strip()]
            break


def _successfactors(board: Board, get) -> list[Posting]:
    body = _read(get, board.url, "text/html", params={
        "locale": "en_US", "sortColumn": "referencedate", "sortDirection": "desc",
    })
    page = BeautifulSoup(bytes(body), "html.parser")
    if not page.select_one('link[href^="//rmkcdn.successfactors.com/"], link[href^="https://rmkcdn.successfactors.com/"]'):
        raise ValueError("The search page did not identify itself as a SuccessFactors career site.")
    jobs = []
    for row in page.select("tr.data-row"):
        anchor = row.select_one("a.jobTitle-link[href]")
        if not anchor:
            continue
        link = _posting_link(anchor["href"], board, SUCCESSFACTORS_JOB)
        title = anchor.get_text(" ", strip=True)
        if not link or not title:
            continue
        location = row.select_one(".jobLocation")
        date = row.select_one(".jobDate")
        place = location.get_text(" ", strip=True) if location else ""
        published = None
        if date:
            try:
                published = datetime.strptime(date.get_text(" ", strip=True), "%b %d, %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        jobs.append(Posting(
            link[0], title, link[1] + "/", [place] if place else [],
            published_at=published, precision="date" if published else "unknown",
        ))
    if not jobs and not page.select_one(".noresults, .no-results"):
        raise ValueError("SuccessFactors returned no recognizable public job results.")
    return jobs


def _successfactors_detail(board: Board, job: Posting, page: BeautifulSoup) -> None:
    canonical = page.select_one('link[rel="canonical"][href]')
    link = _posting_link(canonical["href"], board, SUCCESSFACTORS_JOB) if canonical else None
    detail = page.select_one('[itemtype$="/JobPosting"]')
    description = detail.select_one('[itemprop="description"]') if detail else None
    if not link or link[0] != job.id or not description:
        raise ValueError("SuccessFactors did not return the expected public job detail.")
    job.description = description.get_text("\n", strip=True)
    if not job.locations:
        address = detail.select_one('[itemprop="jobLocation"] [itemprop="address"]')
        if address:
            fields = [
                address.select_one(f'[itemprop="{key}"]')
                for key in ("addressLocality", "addressRegion", "addressCountry")
            ]
            place = _location(*(field.get_text(" ", strip=True) for field in fields if field))
            if not place:
                street = address.select_one('[itemprop="streetAddress"]')
                place = street.get_text(" ", strip=True) if street else ""
            if place:
                job.locations = [place]
    if not job.published_at:
        date = detail.select_one('[itemprop="datePosted"]')
        value = _text(date.get("content")) if date else ""
        if value:
            try:
                day = datetime.strptime(value, "%a %b %d %H:%M:%S UTC %Y").date()
            except ValueError:
                job.published_at, job.precision = _publication(value[:10])
            else:
                job.published_at, job.precision = _publication(day.isoformat())


def _peoplestrong_payload(get, url: str, **kwargs):
    result = json.loads(_read(get, url, "application/json", **kwargs))
    status = result.get("messageCode") if isinstance(result, dict) else None
    if not isinstance(status, dict) or status.get("code") != 200:
        raise ValueError("PeopleStrong did not return a successful public career response.")
    data = result.get("response")
    return [] if data is None and result.get("totalRecords") == 0 else data


def _peoplestrong(board: Board, get) -> list[Posting]:
    # The candidate portal loads a public page of 45 jobs with an empty search.
    url = f"https://{board.host}{PEOPLESTRONG_API}/jobs/v1?offset=0&limit=45"
    rows = _peoplestrong_payload(get, url, json_body={})
    if not isinstance(rows, list):
        raise ValueError("PeopleStrong did not return a public jobs list.")
    jobs = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        link = _posting_link(_text(item.get("jobDetailUrl")), board, PEOPLESTRONG_JOB)
        title = _text(item.get("jobTitle"))
        if not link or not title:
            continue
        skills = item.get("skills")
        values = (
            _text(skill)
            for key in ("mustTohave", "goodtohave")
            for skill in (skills[key] if isinstance(skills, dict) and isinstance(skills.get(key), list) else [])
        )
        details = {"key_skills": list(dict.fromkeys(filter(None, values)))[:50]}
        experience = re.fullmatch(r"(\d{1,2})\s*-\s*(\d{1,2})\s+years?", _text(item.get("expRange")), re.I)
        if experience:
            low, high = map(int, experience.groups())
            if low <= high <= 60:
                details.update(experience_min_years=low, experience_max_years=high)
        location = _text(item.get("locationHierarchy"))
        date = _text(item.get("jobPostedDate"))
        published, precision = _publication(date) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else (None, "unknown")
        jobs.append(Posting(
            link[0], title, link[1], [location] if location else [],
            published_at=published, precision=precision, details=details,
            company=_text(item.get("organizationUnit")),
        ))
    if rows and not jobs:
        raise ValueError("PeopleStrong returned no recognizable public job records.")
    return jobs


def list_jobs(board: Board, get, *, probe: bool = False) -> list[Posting]:
    if board.source == "teamtailor":
        jobs = _teamtailor(board, get, probe=probe)
    elif board.source == "breezy":
        jobs = _breezy(board, get)
    elif board.source == "bamboohr":
        jobs = _bamboohr(board, get)
    elif board.source == "oraclecloud":
        jobs = _oracle(board, get, probe=probe)
    elif board.source == "rippling":
        jobs = _rippling(board, get, probe=probe)
    elif board.source == "avature":
        jobs = _avature(board, get, probe=probe)
    elif board.source == "ycombinator":
        jobs = _ycombinator(board, get)
    elif board.source == "icims":
        jobs = _icims(board, get, probe=probe)
    elif board.source == "freshteam":
        jobs = _freshteam(board, get)
    elif board.source == "cutshort":
        jobs = _cutshort(board, get)
    elif board.source == "hrsmart":
        jobs = _hrsmart(board, get)
    elif board.source == "ukg":
        jobs = _ukg(board, get, probe=probe)
    elif board.source == "phenom":
        jobs = _phenom(board, get, probe=probe)
    elif board.source == "zoho":
        jobs = _zoho(board, get)
    elif board.source == "taleo":
        jobs = _taleo(board, get)
    elif board.source == "successfactors":
        jobs = _successfactors(board, get)
    elif board.source == "peoplestrong":
        jobs = _peoplestrong(board, get)
    else:
        jobs = _html_list(board, get)
    unique = {}
    for job in jobs:
        unique.setdefault(job.id, job)
    return list(unique.values())


def _structured_items(node):
    if isinstance(node, list):
        for item in node:
            yield from _structured_items(item)
    elif isinstance(node, dict):
        if node.get("@type") == "JobPosting" or (
            isinstance(node.get("@type"), list) and "JobPosting" in node["@type"]
        ):
            yield node
        yield from _structured_items(node.get("@graph"))


def hydrate(board: Board, job: Posting, get) -> None:
    if board.source == "peoplestrong":
        url = f"https://{board.host}{PEOPLESTRONG_API}/job/{job.id}/v2"
        # The provider spells this selector "descriprion". It returns only the public description.
        item = _peoplestrong_payload(get, url, params={"part": "descriprion", "isReqId": "false"})
        if not isinstance(item, dict):
            raise ValueError("PeopleStrong did not return a public job description.")
        job.description = _description(item.get("jobDescription"))
        return
    if board.source == "taleo":
        _taleo_detail(job, get)
        return
    if board.source == "zoho":
        rows = _zoho_rows(board, get, job.id)
        item = next((row for row in rows if isinstance(row, dict) and _text(row.get("id")) == job.id), None)
        if not item or item.get("Publish") is False:
            raise ValueError("Zoho Recruit did not return the expected public opening.")
        _zoho_metadata(job, item)
        job.description = _description(item.get("Job_Description"))
        opened = _text(item.get("Date_Opened"))
        if opened:
            job.details["date_opened"] = opened
        return
    if board.source == "bamboohr":
        data = json.loads(_read(get, job.url + "/detail", "application/json"))
        result = data.get("result") if isinstance(data, dict) else None
        opening = result.get("jobOpening") if isinstance(result, dict) else None
        if not isinstance(opening, dict):
            raise ValueError("BambooHR did not return the public job opening.")
        _bamboohr_metadata(job, opening)
        job.description = _description(opening.get("description"))
        job.published_at, job.precision = _publication(_text(opening.get("datePosted")))
        return
    if board.source == "oraclecloud":
        endpoint = f"https://{board.host}{ORACLE_API}Details"
        body = _read(get, endpoint, "application/json", params={
            "onlyData": "true", "finder": f"ById;Id={job.id},siteNumber={board.tenant}",
        })
        result = json.loads(body)
        item = next((row for row in result.get("items", []) if _text(row.get("Id")) == job.id), None)
        if not item:
            raise ValueError("Oracle Cloud returned no matching public requisition detail.")
        parts = (_description(item.get(key)) for key in (
            "ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr",
        ))
        job.description = "\n\n".join(dict.fromkeys(filter(None, parts)))
        return
    if board.source == "rippling":
        data = _next_page(get, job.url).get("apiData", {}).get("jobPost", {})
        if data.get("uuid") != job.id:
            raise ValueError("Rippling detail did not contain the expected public job.")
        description = data.get("description")
        job.description = _description(description.get("role") if isinstance(description, dict) else description)
        employment = _text(data.get("employmentType"))
        if employment:
            job.details["employment_type"] = employment
        schema = data.get("jsonLd")
        if isinstance(schema, dict):
            job.published_at, job.precision = _publication(_text(schema.get("datePosted")))
        return
    params = {"in_iframe": 1} if board.source == "icims" else None
    page = BeautifulSoup(bytes(_read(get, job.url, "text/html", params=params)), "html.parser")
    if board.source == "successfactors":
        _successfactors_detail(board, job, page)
        return
    if board.source == "avature":
        field = page.select_one("article.article--details .field--rich-text")
        if field:
            job.description = field.get_text("\n", strip=True)
        return
    if board.source == "hrsmart":
        field = page.select_one("#job_details_ats_requisition_description")
        location = page.select_one("#job_details_hua_location_id")
        employment = page.select_one("#job_details_f_job_type_displayed_on_posting_0")
        workplace = page.select_one("#job_details_f_work_options_0")
        if field:
            job.description = field.get_text("\n", strip=True)
        if location:
            job.locations = list(dict.fromkeys(location.stripped_strings))
        if employment:
            job.details["employment_type"] = employment.get_text(" ", strip=True)
        if workplace:
            mode = workplace.get_text(" ", strip=True).casefold().replace("-", "_").replace(" ", "_")
            job.details["workplace_type"] = WORKPLACE.get(mode)
        return
    if board.source == "ukg":
        for script in page.select("script"):
            code = script.get_text()
            beginning = re.search(r"new US\.Opportunity\.CandidateOpportunityDetail\(\s*(\{)", code)
            if not beginning:
                continue
            item, _ = json.JSONDecoder().raw_decode(code, beginning.start(1))
            if _text(item.get("Id")).lower() != job.id or item.get("OpportunityIsClosed") is True:
                raise ValueError("UKG did not return the expected open job.")
            job.description = _description(item.get("Description"))
            job.locations = _ukg_locations(item) or job.locations
            return
        raise ValueError("UKG did not expose the public opportunity details.")
    for script in page.select('script[type="application/ld+json"]'):
        try:
            item = next(_structured_items(json.loads(script.get_text())), None)
        except (ValueError, RecursionError):
            continue
        if not item:
            continue
        job.description = _description(item.get("description"))
        if not job.published_at:
            job.published_at, job.precision = _publication(_text(item.get("datePosted")))
        if not job.locations:
            places = item.get("jobLocation")
            for place in places if isinstance(places, list) else [places]:
                address = place.get("address") if isinstance(place, dict) else None
                if isinstance(address, dict):
                    location = _location(*(_text(address.get(key)) for key in (
                        "addressLocality", "addressRegion", "addressCountry",
                    )))
                    if location and location not in job.locations:
                        job.locations.append(location)
        if _text(item.get("jobLocationType")).upper() == "TELECOMMUTE":
            job.details["workplace_type"] = "remote"
        if not job.locations:
            places = item.get("applicantLocationRequirements")
            for place in places if isinstance(places, list) else [places]:
                if isinstance(place, dict) and _text(place.get("name")):
                    job.locations.append(_text(place["name"]))
        employment = _text(item.get("employmentType"))
        if employment and not job.details.get("employment_type"):
            job.details["employment_type"] = employment
        return
