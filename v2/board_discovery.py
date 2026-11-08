"""Safe, review-first discovery of public employer career boards and ATS providers.

This module deliberately discovers board candidates only. It never enables a
source or schedules an employer board automatically; an administrator reviews
and verifies each candidate before connecting it to a collector.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

USER_AGENT = "JobBeeper-BoardDiscovery/1.0 (+public-careers-discovery)"
MAX_HTML_BYTES = 1_500_000
MAX_PAGES_PER_SCAN = 6
MAX_CAREERS_LINKS = 5
MAX_REDIRECTS = 3
REQUEST_TIMEOUT_SECONDS = 10
CAREERS_HINT = re.compile(
    r"career|jobs?|work[- ]with[- ]us|join[- ]us|vacanc|opportunit|openings?",
    re.IGNORECASE,
)

# Provider names intentionally include platforms that do not yet have a V2
# collector. Discovery coverage and ingestion coverage remain separate facts.
PROVIDER_PATTERNS = (
    ("workday", re.compile(r"^(?P<tenant>[a-z0-9-]+)\.wd(?P<cluster>\d+)\.myworkdayjobs\.com$", re.I)),
    ("greenhouse", re.compile(r"^(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io$", re.I)),
    ("ashby", re.compile(r"^jobs\.ashbyhq\.com$", re.I)),
    ("lever", re.compile(r"^(?:jobs\.)?(?:eu\.)?lever\.co$|^jobs\.lever\.co$", re.I)),
    ("smartrecruiters", re.compile(r"^(?:jobs|careers)\.smartrecruiters\.com$", re.I)),
    ("workable", re.compile(r"^(?:apply\.)?workable\.com$", re.I)),
    ("keka", re.compile(r"^(?P<slug>[a-z0-9-]+)\.keka\.com$", re.I)),
    ("darwinbox", re.compile(r"^(?P<slug>[a-z0-9-]+)\.darwinbox\.(?:in|com)$", re.I)),
    ("recruitee", re.compile(r"^(?P<slug>[a-z0-9-]+)\.recruitee\.com$", re.I)),
    ("breezy", re.compile(r"^(?P<slug>[a-z0-9-]+)\.breezy\.hr$", re.I)),
    ("teamtailor", re.compile(r"^(?P<slug>[a-z0-9-]+)\.teamtailor\.com$", re.I)),
    ("bamboohr", re.compile(r"^(?P<slug>[a-z0-9-]+)\.bamboohr\.com$", re.I)),
    ("rippling", re.compile(r"^ats\.rippling\.com$", re.I)),
    ("personio", re.compile(r"^(?P<slug>[a-z0-9-]+)\.jobs\.personio\.(?:de|com)$", re.I)),
)

COLLECTOR_SOURCES = {
    "workday": "workday",
    "greenhouse": "greenhouse",
    "ashby": "ashby",
    "lever": "lever",
    "smartrecruiters": "smartrecruiters",
    "workable": "workable",
    "keka": "keka",
    "darwinbox": "darwinbox",
}


def _host_key(host: str) -> str:
    return (host or "").lower().rstrip(".").removeprefix("www.")


def domain_key(url: str) -> str:
    """Return the host key used to deduplicate company registrations."""
    return _host_key(urlsplit(url).hostname or "")


def _public_https_url(value: str) -> str:
    """Validate an HTTPS URL and reject loopback/private/reserved DNS targets."""
    if not isinstance(value, str) or len(value.strip()) > 2048:
        raise ValueError("A public HTTPS website URL is required.")
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Only public HTTPS website URLs are supported.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and non-standard ports are not allowed.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal hostnames are not allowed.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if not ip.is_global:
            raise ValueError("Private, loopback and reserved IP addresses are not allowed.")
    else:
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError("Website hostname could not be resolved publicly.") from exc
        if not addresses:
            raise ValueError("Website hostname has no public address.")
        for entry in addresses:
            address = ipaddress.ip_address(entry[4][0].split("%", 1)[0])
            if not address.is_global:
                raise ValueError("Website resolves to a private or reserved address.")
    path = parsed.path or "/"
    return urlunsplit(("https", parsed.netloc.lower(), path, "", ""))


def _normalise_candidate_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Career board URL must use HTTPS.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Career board URL contains disallowed credentials or port.")
    path = re.sub(r"/{2,}", "/", parsed.path or "/").rstrip("/") or "/"
    return urlunsplit(("https", parsed.netloc.lower(), path, "", ""))


def detect_ats_board(value: str) -> dict[str, Any] | None:
    """Recognise common ATS-hosted public board URLs without guessing slugs."""
    try:
        url = _normalise_candidate_url(value)
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        segments = [segment for segment in parsed.path.split("/") if segment]
        for provider, pattern in PROVIDER_PATTERNS:
            match = pattern.fullmatch(host)
            if not match:
                continue
            details = match.groupdict()
            if provider == "workday":
                if segments and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", segments[0]):
                    segments = segments[1:]
                if not segments or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", segments[0]):
                    return None
                tenant = details["tenant"]
                site = segments[0]
                board_key = f"{tenant}:{site}"
                display_key = site
            elif provider == "greenhouse":
                if not segments:
                    return None
                board_key = segments[0]
                display_key = board_key
            elif provider in {"ashby", "lever", "smartrecruiters", "workable", "rippling"}:
                if not segments:
                    return None
                board_key = segments[0]
                display_key = board_key
            elif provider == "bamboohr":
                if not segments or segments[0].lower() not in {"careers", "jobs"}:
                    return None
                board_key = details["slug"]
                display_key = board_key
            elif provider == "keka":
                if not segments or segments[0].lower() != "careers":
                    return None
                board_key = details["slug"]
                display_key = board_key
            elif provider == "darwinbox":
                match_careers = re.match(
                    r"^/ms/candidatev2/(?P<company_id>[A-Za-z0-9_-]{1,100})/careers(?:/|$)",
                    parsed.path,
                    re.I,
                )
                if not match_careers:
                    return None
                board_key = match_careers.group("company_id")
                display_key = board_key
            elif provider == "rippling":
                if not segments or segments[0].lower() != "api":
                    # Public board URLs use ats.rippling.com/{slug}/jobs.
                    if not segments:
                        return None
                    board_key = segments[0]
                else:
                    if len(segments) < 3:
                        return None
                    board_key = segments[2]
                display_key = board_key
            else:
                board_key = details.get("slug") or _host_key(host).split(".")[0]
                display_key = board_key
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", board_key):
                return None
            candidate = {
                "provider": provider,
                "board_key": board_key,
                "display_key": display_key,
                "board_url": url,
                "host": host,
                "collector_source": COLLECTOR_SOURCES.get(provider),
                "collector_available": provider in COLLECTOR_SOURCES,
            }
            if provider == "workday":
                candidate.update({
                    "tenant": details["tenant"],
                    "cluster": details["cluster"],
                    "site": display_key,
                })
            elif provider in {"keka", "darwinbox"}:
                candidate["tenant"] = details["slug"]
            return candidate
    except (ValueError, TypeError):
        return None
    return None


def probe_public_board(board: dict[str, Any]) -> dict[str, Any]:
    """Probe a supported public endpoint once without enabling its scheduler."""
    provider = str(board.get("provider") or "")
    board_url = _public_https_url(str(board.get("board_url") or ""))
    candidate = detect_ats_board(board_url)
    if not candidate or candidate["provider"] != provider:
        raise ValueError("Board URL no longer matches its discovered ATS provider.")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if provider == "workday":
        tenant = candidate["tenant"]
        site = candidate["site"]
        endpoint = (
            f"https://{candidate['host']}/wday/cxs/{tenant}/{site}/jobs"
        )
        response = requests.post(
            endpoint,
            json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
            headers={**headers, "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobPostings") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("Workday response did not contain jobPostings.")
    elif provider == "greenhouse":
        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{candidate['board_key']}/jobs"
        response = requests.get(
            endpoint, params={"content": "false"}, headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("Greenhouse response did not contain a jobs list.")
    elif provider == "ashby":
        endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{candidate['board_key']}"
        response = requests.get(
            endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("Ashby response did not contain a jobs list.")
    elif provider == "smartrecruiters":
        endpoint = f"https://api.smartrecruiters.com/v1/companies/{candidate['board_key']}/postings"
        response = requests.get(
            endpoint, params={"limit": 10, "offset": 0, "destination": "PUBLIC"},
            headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("content") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("SmartRecruiters response did not contain public postings.")
    elif provider == "workable":
        endpoint = f"https://www.workable.com/api/accounts/{candidate['board_key']}"
        response = requests.get(
            endpoint, params={"details": "true"}, headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("Workable response did not contain published jobs.")
    elif provider == "keka":
        careers_url = _public_https_url(board_url)
        final_url, html = _safe_fetch(careers_url)
        if (urlsplit(final_url).hostname or "").lower() != (urlsplit(careers_url).hostname or "").lower():
            raise ValueError("Keka careers page redirected to a different host.")
        feed_match = re.search(
            r"/ats/documents/([0-9a-fA-F-]{16,})/careerportal/?",
            html,
            re.I,
        )
        if not feed_match:
            raise ValueError("Keka careers page did not expose a public career-portal feed identifier.")
        feed_id = feed_match.group(1)
        origin = f"https://{urlsplit(final_url).hostname}"
        endpoint = f"{origin}/careers/api/embedjobs/default/active/{feed_id}"
        response = requests.get(
            endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        response.raise_for_status()
        jobs = response.json()
        if not isinstance(jobs, list):
            raise ValueError("Keka public career feed did not return a jobs list.")
    elif provider == "darwinbox":
        parsed = urlsplit(board_url)
        company_id = candidate["board_key"]
        endpoint = f"{parsed.scheme}://{parsed.netloc}/ms/candidateapi/job/alljobs?companyId={company_id}"
        response = requests.post(
            endpoint,
            json={"companyId": company_id, "page": 1, "sort_option": "new", "limit": 50},
            headers={**headers, "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("data") if isinstance(payload, dict) and payload.get("status") == "success" else None
        if not isinstance(jobs, list):
            raise ValueError("Darwinbox candidate API did not return a successful public jobs list.")
    elif provider == "lever":
        api_host = "api.eu.lever.co" if ".eu." in candidate["host"] else "api.lever.co"
        endpoint = f"https://{api_host}/v0/postings/{candidate['board_key']}"
        response = requests.get(
            endpoint, params={"mode": "json"}, headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=False,
        )
        response.raise_for_status()
        jobs = response.json()
        if not isinstance(jobs, list):
            raise ValueError("Lever response did not contain a postings list.")
    else:
        raise ValueError("This ATS is discovered but does not yet have a V2 collector to verify.")
    return {
        "provider": provider,
        "verified": True,
        "http_status": int(response.status_code),
        "jobs_observed": len(jobs),
        "verification_method": "public_board_endpoint_probe",
    }


def _safe_fetch(url: str) -> tuple[str, str]:
    """Fetch a small public HTML page, validating each redirect destination."""
    current = _public_https_url(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
    }
    for _ in range(MAX_REDIRECTS + 1):
        response = requests.get(
            current, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False, stream=True,
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise ValueError("Website returned a redirect without a destination.")
            current = _public_https_url(urljoin(current, location))
            continue
        response.raise_for_status()
        content_type = str(response.headers.get("Content-Type", "")).lower()
        if content_type and not any(kind in content_type for kind in ("text/html", "application/xhtml+xml", "text/plain")):
            response.close()
            raise ValueError("Career page did not return HTML content.")
        body = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                body.extend(chunk)
                if len(body) > MAX_HTML_BYTES:
                    raise ValueError("Career page exceeded the HTML size limit.")
        finally:
            response.close()
        encoding = response.encoding or "utf-8"
        return current, bytes(body).decode(encoding, errors="replace")
    raise ValueError("Career page exceeded the redirect limit.")


def _is_same_company_host(candidate: str, root: str) -> bool:
    left = _host_key(urlsplit(candidate).hostname or "")
    right = _host_key(urlsplit(root).hostname or "")
    return left == right


def _jsonld_has_jobposting(soup: BeautifulSoup) -> bool:
    def contains_jobposting(value: Any) -> bool:
        if isinstance(value, dict):
            kind = value.get("@type")
            if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
                return True
            return any(contains_jobposting(child) for child in value.values())
        if isinstance(value, list):
            return any(contains_jobposting(child) for child in value)
        return False

    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw or len(raw) > MAX_HTML_BYTES:
            continue
        try:
            if contains_jobposting(json.loads(raw)):
                return True
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return False


def discover_public_careers(
    company_name: str,
    website_url: str,
    careers_url: str | None = None,
) -> dict[str, Any]:
    """Inspect a company site and a few likely careers pages for ATS board links.

    The function returns review candidates only. It never schedules a source,
    follows an ATS board page, or activates notifications.
    """
    name = str(company_name or "").strip()
    if not name or len(name) > 160:
        raise ValueError("Company name must contain 1 to 160 characters.")
    root_url = _public_https_url(website_url)
    start_url = _public_https_url(careers_url) if careers_url else root_url
    queue = [root_url]
    if start_url != root_url:
        queue.append(start_url)
    seen_pages: set[str] = set()
    board_candidates: dict[tuple[str, str], dict[str, Any]] = {}
    jsonld_pages: list[str] = []
    errors: list[dict[str, str]] = []
    page_limit = MAX_PAGES_PER_SCAN

    while queue and len(seen_pages) < page_limit:
        requested_url = queue.pop(0)
        if requested_url in seen_pages:
            continue
        try:
            final_url, html = _safe_fetch(requested_url)
            seen_pages.add(final_url)
        except (requests.RequestException, ValueError) as exc:
            errors.append({"url": requested_url, "error_type": type(exc).__name__})
            continue

        current_board = detect_ats_board(final_url)
        if current_board:
            current_board["discovered_from"] = requested_url
            current_board["confidence"] = "high"
            board_candidates[(current_board["provider"], current_board["board_key"].lower())] = current_board

        soup = BeautifulSoup(html, "html.parser")
        if _jsonld_has_jobposting(soup):
            jsonld_pages.append(final_url)

        links: list[tuple[str, str]] = []
        for tag in soup.find_all(["a", "iframe"]):
            raw_href = tag.get("href") or tag.get("src")
            if not isinstance(raw_href, str) or not raw_href.strip():
                continue
            absolute = urljoin(final_url, raw_href.strip())
            try:
                candidate_url = _normalise_candidate_url(absolute)
            except ValueError:
                continue
            detected = detect_ats_board(candidate_url)
            if detected:
                detected["discovered_from"] = final_url
                detected["confidence"] = "high"
                board_candidates[(detected["provider"], detected["board_key"].lower())] = detected
                continue
            text = tag.get_text(" ", strip=True) if tag.name == "a" else ""
            allowed_career_hosts = (root_url, start_url)
            if any(_is_same_company_host(candidate_url, allowed_root) for allowed_root in allowed_career_hosts) and CAREERS_HINT.search(f"{text} {candidate_url}"):
                links.append((candidate_url, text[:160]))

        # Preserve discovery order while avoiding duplicate links and excessive crawling.
        for candidate_url, _label in links:
            if candidate_url not in seen_pages and candidate_url not in queue:
                queue.append(candidate_url)
                if len(queue) + len(seen_pages) >= page_limit:
                    break

    generic_candidates = []
    if jsonld_pages:
        generic_candidates.append({
            "provider": "jobposting_jsonld",
            "board_key": _host_key(urlsplit(root_url).hostname or ""),
            "display_key": name,
            "board_url": root_url,
            "host": urlsplit(root_url).hostname or "",
            "collector_source": None,
            "collector_available": False,
            "discovered_from": jsonld_pages[0],
            "confidence": "medium",
            "note": "Public JobPosting JSON-LD found; generic structured-data ingestion is not yet registered.",
        })

    candidates = sorted(
        list(board_candidates.values()) + generic_candidates,
        key=lambda item: (item["provider"], item["board_key"].lower()),
    )
    return {
        "company_name": name,
        "website_url": root_url,
        "careers_url": start_url,
        "pages_checked": len(seen_pages),
        "jobposting_jsonld_pages": jsonld_pages,
        "boards": candidates,
        "errors": errors,
        "discovery_status": "boards_found" if board_candidates else "jsonld_found" if jsonld_pages else "no_board_found",
    }
