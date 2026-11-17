"""Isolated company career-board watcher for JobBeeper.

This module has no imports from the V2 application and never opens its SQLite
DB, reads its runtime config, touches Docker, or changes existing source state.

Safe default: dry-run. A live Telegram send requires an explicit --send flag.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DEFAULT_COMPANIES = ROOT / "companies.csv"
DEFAULT_FILTERS = ROOT / "filters.json"
DEFAULT_STATE = ROOT / ".state" / "seen.json"
DEFAULT_REPORT = ROOT / ".state" / "latest_report.json"
UTC = dt.timezone.utc
USER_AGENT = "JobBeeper-CompanyWatch/1.0 (+polite public careers-page watcher)"
REQUEST_TIMEOUT = 25
MAX_JOBS_PER_COMPANY = 150


def utc_now() -> str:
    return dt.datetime.now(UTC).replace(microsecond=0).isoformat()


def compile_patterns(values: list[str]) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{item})" for item in values) or r"(?!)", re.I)


def load_filters(path: Path = DEFAULT_FILTERS) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("title_must_match", "title_must_not_match", "location_must_match", "skills_any")
    for key in required:
        if not isinstance(data.get(key), list):
            raise ValueError(f"filters.json: {key} must be an array")
    data["_title_ok"] = compile_patterns(data["title_must_match"])
    data["_title_bad"] = compile_patterns(data["title_must_not_match"])
    data["_location_ok"] = compile_patterns(data["location_must_match"])
    data["_skills_ok"] = compile_patterns(data["skills_any"])
    data["_max_years"] = int(data.get("max_years_required", 2))
    return data


def load_companies(path: Path = DEFAULT_COMPANIES) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 100:
        raise ValueError(f"Expected 100 company rows, found {len(rows)}")
    required = {"no", "name", "careers_url", "scan_mode", "scan_enabled", "verification_status"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("companies.csv is missing required columns")
    for row in rows:
        if not row.get("careers_url", "").strip():
            raise ValueError(f"Company row {row.get('no')} has an empty careers_url")
        if row.get("scan_enabled", "false").lower() == "true":
            _validate_public_https_url(row["careers_url"])
    return rows


def _validate_public_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"Only absolute HTTPS career URLs are allowed: {url!r}")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith((".local", ".internal")):
        raise ValueError(f"Non-public URL is not allowed: {url!r}")


def _session() -> requests.Session:
    client = requests.Session()
    client.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    return client


def _json_response(client: requests.Session, url: str) -> Any:
    response = client.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(BeautifulSoup(value, "html.parser").get_text(" ").split())


def _normalise_job(title: str, location: str, url: str, description: str, company: str,
                   source: str, generic: bool = False) -> dict[str, Any] | None:
    title = " ".join(str(title or "").split())
    url = str(url or "").strip()
    if not title or not url:
        return None
    return {
        "company": company,
        "source": source,
        "title": title[:240],
        "location": " ".join(str(location or "").split())[:240],
        "url": url,
        "description": _clean_html(str(description or ""))[:30000],
        "generic": bool(generic),
    }


def _greenhouse(company: dict[str, str], client: requests.Session) -> list[dict[str, Any]]:
    parsed = urlparse(company["careers_url"])
    slug = next((part for part in parsed.path.split("/") if part), "")
    if not slug:
        raise ValueError("Greenhouse URL has no board slug")
    payload = _json_response(client, f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    out = []
    for item in (payload.get("jobs") or [])[:MAX_JOBS_PER_COMPANY]:
        location = (item.get("location") or {}).get("name", "")
        job = _normalise_job(item.get("title"), location, item.get("absolute_url"),
                             item.get("content", ""), company["name"], "greenhouse")
        if job:
            out.append(job)
    return out


def _lever(company: dict[str, str], client: requests.Session) -> list[dict[str, Any]]:
    parsed = urlparse(company["careers_url"])
    slug = next((part for part in parsed.path.split("/") if part), "")
    if not slug:
        raise ValueError("Lever URL has no site slug")
    region = "eu" if parsed.hostname and parsed.hostname.startswith("jobs.eu.lever.co") else "global"
    host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
    payload = _json_response(client, f"https://{host}/v0/postings/{slug}?mode=json")
    out = []
    for item in (payload if isinstance(payload, list) else [])[:MAX_JOBS_PER_COMPANY]:
        categories = item.get("categories") or {}
        description = item.get("descriptionPlain", "")
        description += " " + " ".join(str(entry.get("content", "")) for entry in item.get("lists", []) if isinstance(entry, dict))
        job = _normalise_job(item.get("text"), categories.get("location", ""), item.get("hostedUrl"),
                             description, company["name"], "lever")
        if job:
            out.append(job)
    return out


def _ashby(company: dict[str, str], client: requests.Session) -> list[dict[str, Any]]:
    parsed = urlparse(company["careers_url"])
    slug = next((part for part in parsed.path.split("/") if part), "")
    if not slug:
        raise ValueError("Ashby URL has no board slug")
    payload = _json_response(client, f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    out = []
    for item in (payload.get("jobs") or [])[:MAX_JOBS_PER_COMPANY]:
        job = _normalise_job(item.get("title"), item.get("location"), item.get("jobUrl"),
                             item.get("descriptionPlain", ""), company["name"], "ashby")
        if job:
            out.append(job)
    return out


def _smartrecruiters(company: dict[str, str], client: requests.Session) -> list[dict[str, Any]]:
    parsed = urlparse(company["careers_url"])
    slug = next((part for part in parsed.path.split("/") if part), "")
    if not slug:
        raise ValueError("SmartRecruiters URL has no company identifier")
    payload = _json_response(client, f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset=0")
    out = []
    for item in (payload.get("content") or [])[:MAX_JOBS_PER_COMPANY]:
        loc = item.get("location") or {}
        location = ", ".join(str(loc.get(k, "")).strip() for k in ("city", "region", "country") if loc.get(k))
        job = _normalise_job(item.get("name"), location, item.get("ref"), "", company["name"], "smartrecruiters", generic=True)
        if job:
            out.append(job)
    return out


def _jsonld_jobs(soup: BeautifulSoup, company: dict[str, str]) -> list[dict[str, Any]]:
    def walk(value: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(value, list):
            for child in value:
                found.extend(walk(child))
        elif isinstance(value, dict):
            kind = value.get("@type", [])
            kinds = kind if isinstance(kind, list) else [kind]
            if any(str(k).lower() == "jobposting" for k in kinds):
                found.append(value)
            for key, child in value.items():
                if key != "@context":
                    found.extend(walk(child))
        return found

    out = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        for item in walk(data):
            raw_location = item.get("jobLocation") or item.get("applicantLocationRequirements") or ""
            if isinstance(raw_location, list):
                places = raw_location
            else:
                places = [raw_location]
            location_parts = []
            for place in places:
                if isinstance(place, dict):
                    address = place.get("address") or place
                    if isinstance(address, dict):
                        location_parts.extend(str(address.get(key, "")) for key in ("addressLocality", "addressRegion", "addressCountry") if address.get(key))
            location = ", ".join(dict.fromkeys(location_parts))
            url = item.get("url") or item.get("sameAs") or company["careers_url"]
            description = item.get("description") or ""
            job = _normalise_job(item.get("title"), location, urljoin(company["careers_url"], str(url)),
                                 description, company["name"], "jobposting_jsonld")
            if job:
                out.append(job)
    return out


def _generic_careers_page(company: dict[str, str], client: requests.Session) -> list[dict[str, Any]]:
    response = client.get(company["careers_url"], timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    final_url = response.url
    soup = BeautifulSoup(response.text, "html.parser")
    structured = _jsonld_jobs(soup, {**company, "careers_url": final_url})
    if structured:
        return structured[:MAX_JOBS_PER_COMPANY]

    # Fallback is intentionally conservative: link-only candidates are never treated as verified matches.
    title_re = re.compile(r"\b(engineer|developer|software|frontend|front-end|backend|back-end|full.?stack|programmer|sde)\b", re.I)
    path_re = re.compile(r"/(jobs?|careers?|positions?|vacancies|openings)(/|$)|[?&](job|gh_jid)=", re.I)
    seen: set[str] = set()
    out = []
    for anchor in soup.find_all("a", href=True):
        title = " ".join(anchor.get_text(" ").split())
        href = urljoin(final_url, anchor["href"].strip())
        if not (5 < len(title) < 160 and title_re.search(title) and path_re.search(urlparse(href).path + "?" + urlparse(href).query)):
            continue
        if urlparse(href).scheme != "https" or href in seen:
            continue
        seen.add(href)
        job = _normalise_job(title, "", href, "", company["name"], "careers_page_link", generic=True)
        if job:
            out.append(job)
        if len(out) >= MAX_JOBS_PER_COMPANY:
            break
    return out


def fetch_company_jobs(company: dict[str, str], client: requests.Session) -> list[dict[str, Any]]:
    mode = company["scan_mode"].strip().lower()
    if mode == "greenhouse":
        return _greenhouse(company, client)
    if mode == "lever":
        return _lever(company, client)
    if mode == "ashby":
        return _ashby(company, client)
    if mode == "smartrecruiters":
        return _smartrecruiters(company, client)
    if mode == "careers_page":
        return _generic_careers_page(company, client)
    raise ValueError(f"Unsupported scan mode {mode!r}")


_RANGE_YEARS = re.compile(r"\b(\d{1,2})\s*(?:-|to|–|—)\s*(\d{1,2})\s*(?:years?|yrs?)\b", re.I)
_PLUS_YEARS = re.compile(r"\b(\d{1,2})\s*\+\s*(?:years?|yrs?)\b", re.I)
_SINGLE_YEARS = re.compile(r"\b(\d{1,2})\s*(?:years?|yrs?)\b", re.I)


def required_years(text: str) -> int | None:
    values: list[int] = []
    for match in _RANGE_YEARS.finditer(text):
        values.append(int(match.group(1)))
    for match in _PLUS_YEARS.finditer(text):
        values.append(int(match.group(1)))
    if values:
        return min(values)
    single = _SINGLE_YEARS.search(text)
    return int(single.group(1)) if single else None


def judge(job: dict[str, Any], filters: dict[str, Any]) -> tuple[str, list[str]]:
    title = str(job.get("title") or "")
    location = str(job.get("location") or "")
    description = str(job.get("description") or "")
    text = f"{title} {location} {description}"
    if not filters["_title_ok"].search(title):
        return "reject", ["title does not match target roles"]
    if filters["_title_bad"].search(title):
        return "reject", ["title is excluded by seniority/role rules"]

    # Generic HTML links and job-board summaries are candidate leads, not qualified matches.
    if job.get("generic") or not description:
        return "review", ["job description not available from this page"]

    remote_india = bool(re.search(r"remote", text, re.I) and re.search(r"india", text, re.I))
    location_ok = bool(filters["_location_ok"].search(location)) or (
        bool(filters.get("remote_ok_if_india_in_text", True)) and remote_india
    )
    if not location_ok:
        return "reject", ["not identified as India-based or India-remote"]

    years = required_years(description)
    if years is not None and years > filters["_max_years"]:
        return "reject", [f"requires at least {years} years"]
    if not filters["_skills_ok"].search(text):
        return "reject", ["no target technology or frontend/backend keyword found"]
    if years is None:
        return "review", ["experience requirement not stated clearly"]
    return "match", [f"minimum experience appears to be {years} years or less"]


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "seen_urls": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):  # migrate original watcher URL-list format
            urls = {str(url): None for url in data}
        elif isinstance(data, dict):
            urls = data.get("seen_urls", {})
        else:
            urls = {}
        if not isinstance(urls, dict):
            urls = {}
        return {"schema_version": 1, "seen_urls": urls}
    except (OSError, json.JSONDecodeError, AttributeError):
        # Corrupt state must not break collection. Report a clean baseline warning.
        return {"schema_version": 1, "seen_urls": {}, "state_warning": "Existing state was unreadable; a new baseline was started."}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def send_telegram(messages: list[str]) -> None:
    token = os.getenv("TG_TOKEN") or os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID") or os.getenv("JOB_RADAR_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Telegram credentials are unavailable. Expected configured repo secrets via environment aliases.")
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    with _session() as client:
        for message in messages:
            response = client.post(endpoint, data={"chat_id": chat_id, "text": message[:4000],
                                                   "disable_web_page_preview": True}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise RuntimeError(f"Telegram API rejected the message: {payload.get('description', 'unknown error')}")


def chunk_messages(lines: list[str], max_chars: int = 3400) -> list[str]:
    batches: list[str] = []
    current = ""
    for line in lines:
        addition = line + "\n\n"
        if current and len(current) + len(addition) > max_chars:
            batches.append(current.rstrip())
            current = ""
        current += addition
    if current:
        batches.append(current.rstrip())
    return batches


def run(args: argparse.Namespace) -> dict[str, Any]:
    filters = load_filters(Path(args.filters))
    companies = load_companies(Path(args.companies))
    state_path = Path(args.state_file)
    state = load_state(state_path)
    seen: dict[str, Any] = state["seen_urls"]
    client = _session()

    report: dict[str, Any] = {
        "generated_at": utc_now(),
        "mode": "send" if args.send else "dry_run",
        "companies_total": len(companies),
        "companies_scanned": 0,
        "companies_manual_review": 0,
        "company_failures": [],
        "jobs_seen": 0,
        "new_matches": [],
        "new_reviews": [],
        "rejected_count": 0,
        "already_seen_count": 0,
        "state_warning": state.get("state_warning"),
    }
    new_urls: dict[str, str] = {}
    for index, company in enumerate(companies):
        if company.get("scan_enabled", "false").lower() != "true":
            report["companies_manual_review"] += 1
            continue
        try:
            jobs = fetch_company_jobs(company, client)
            report["companies_scanned"] += 1
            report["jobs_seen"] += len(jobs)
            for job in jobs:
                verdict, reasons = judge(job, filters)
                if verdict == "reject":
                    report["rejected_count"] += 1
                    continue
                url = job["url"]
                if url in seen:
                    report["already_seen_count"] += 1
                    continue
                item = {**job, "verdict": verdict, "reasons": reasons}
                if verdict == "match":
                    report["new_matches"].append(item)
                else:
                    report["new_reviews"].append(item)
                new_urls[url] = utc_now()
        except Exception as exc:  # keep a bad board from stopping the rest
            report["company_failures"].append({
                "company": company["name"],
                "url": company["careers_url"],
                "error_type": exc.__class__.__name__,
                "message": str(exc)[:240],
            })
        if args.delay > 0 and index < len(companies) - 1:
            time.sleep(args.delay)

    report["new_matches_count"] = len(report["new_matches"])
    report["new_reviews_count"] = len(report["new_reviews"])
    report["new_candidate_count"] = report["new_matches_count"] + report["new_reviews_count"]
    report["state_urls_before"] = len(seen)

    # A dry-run baseline can be persisted in the isolated Actions cache. It never writes to Git.
    if args.send:
        messages = [f"Company Watch: {report['new_candidate_count']} new candidates ({report['new_matches_count']} matches, {report['new_reviews_count']} review)"]
        lines = []
        for job in report["new_matches"]:
            lines.append(f"✅ {job['company']}: {job['title']}\n{job['location']}\n{job['url']}\n{'; '.join(job['reasons'])}")
        for job in report["new_reviews"]:
            lines.append(f"🔎 REVIEW {job['company']}: {job['title']}\n{job['location']}\n{job['url']}\n{'; '.join(job['reasons'])}")
        messages.extend(chunk_messages(lines))
        if len(messages) > 1 or lines:
            send_telegram(messages)
        seen.update(new_urls)
        save_state(state_path, {"schema_version": 1, "seen_urls": seen, "updated_at": utc_now()})
        report["telegram_sent"] = bool(lines)
    elif args.remember_dry_run:
        seen.update(new_urls)
        save_state(state_path, {"schema_version": 1, "seen_urls": seen, "updated_at": utc_now()})
        report["baseline_saved"] = True
    else:
        report["baseline_saved"] = False

    report["state_urls_after"] = len(seen)
    report["new_matches"] = report["new_matches"][:args.report_limit]
    report["new_reviews"] = report["new_reviews"][:args.report_limit]
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("COMPANY WATCH", "SEND" if args.send else "DRY RUN")
    print(f"Companies: {report['companies_scanned']} scanned / {report['companies_manual_review']} manual review / {len(report['company_failures'])} failed")
    print(f"Jobs: {report['jobs_seen']} observed | {report['new_matches_count']} new matches | {report['new_reviews_count']} review | {report['rejected_count']} rejected | {report['already_seen_count']} already seen")
    print(f"Seen state: {report['state_urls_before']} -> {report['state_urls_after']} URLs")
    for job in report["new_matches"]:
        print(f"[MATCH] {job['company']} | {job['title']} | {job['location']} | {job['url']} | {'; '.join(job['reasons'])}")
    for job in report["new_reviews"]:
        print(f"[REVIEW] {job['company']} | {job['title']} | {job['location']} | {job['url']} | {'; '.join(job['reasons'])}")
    for failure in report["company_failures"]:
        print(f"[FAILED] {failure['company']} | {failure['error_type']}: {failure['message']}")
    if not args.send:
        print("DRY RUN: no Telegram messages sent.")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Isolated Company Watcher (dry-run by default)")
    parser.add_argument("--companies", default=str(DEFAULT_COMPANIES))
    parser.add_argument("--filters", default=str(DEFAULT_FILTERS))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT))
    parser.add_argument("--delay", type=float, default=0.4, help="Seconds between company requests (default: 0.4)")
    parser.add_argument("--report-limit", type=int, default=100, help="Maximum jobs of each verdict in report output")
    parser.add_argument("--dry-run", action="store_true", help="Explicitly run without sending Telegram messages (default)")
    parser.add_argument("--remember-dry-run", action="store_true", help="Persist the dry-run baseline to the supplied isolated state file")
    parser.add_argument("--send", action="store_true", help="Send results to Telegram. Never enabled by the committed workflow.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.send and args.dry_run:
        print("Choose either --send or --dry-run, not both.", file=sys.stderr)
        return 2
    if args.delay < 0 or args.delay > 10:
        print("--delay must be between 0 and 10 seconds.", file=sys.stderr)
        return 2
    try:
        run(args)
    except Exception as exc:
        print(f"Company Watch failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())