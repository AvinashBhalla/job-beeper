"""Bounded readers for public employer job boards with common scheduling needs."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

LABELS = {
    "teamtailor": "Teamtailor",
    "breezy": "Breezy HR",
    "bamboohr": "BambooHR",
    "jobvite": "Jobvite",
    "hireology": "Hireology",
}
MAX_BOARDS = 30
DETAILS_PER_POLL = 10
MAX_BODY_BYTES = 8 * 1024 * 1024
HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
TENANT = r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}"
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
    try:
        stamp = parsedate_to_datetime(value) if rss else datetime.fromisoformat(value)
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


def list_jobs(board: Board, get, *, probe: bool = False) -> list[Posting]:
    if board.source == "teamtailor":
        jobs = _teamtailor(board, get, probe=probe)
    elif board.source == "breezy":
        jobs = _breezy(board, get)
    elif board.source == "bamboohr":
        jobs = _bamboohr(board, get)
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
    page = BeautifulSoup(bytes(_read(get, job.url, "text/html")), "html.parser")
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
        employment = _text(item.get("employmentType"))
        if employment and not job.details.get("employment_type"):
            job.details["employment_type"] = employment
        return
