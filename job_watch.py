"""Personal job watcher + dashboard feed.
Polls free sources in parallel, normalizes and scores jobs, alerts new matches on Telegram,
and writes dashboard/data/jobs.json for the live UI.
"""
import json, os, re, pathlib, datetime as dt, requests
from concurrent.futures import ThreadPoolExecutor
from job_sources_extra import linkedin_guest, naukri_public, instahyre_public
from apify_sources import linkedin as apify_linkedin, naukri as apify_naukri, instahyre as apify_instahyre
from jd_extract import enrich_job

ROOT = pathlib.Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text())
SEEN_FILE = ROOT / "seen.json"
SOURCE_STATE_FILE = ROOT / "source_state.json"
DASH_FILE = ROOT / "dashboard" / "data" / "jobs.json"
UA = {"User-Agent": "Mozilla/5.0 (personal-job-watcher)"}
NOW = dt.datetime.now(dt.timezone.utc)
SOURCE_GENERATION = 3
strip = lambda h: re.sub("<[^>]+>", " ", h or "")

def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=25, **kw)
    r.raise_for_status()
    return r.json()

def parse_time(v):
    if not v:
        return None
    try:
        if isinstance(v, (int, float)):
            return dt.datetime.fromtimestamp(v / 1000 if v > 1e11 else v, dt.timezone.utc)
        d = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        raw = str(v).lower()
        if raw in {"today", "just now"}:
            return NOW
        if raw == "yesterday":
            return NOW - dt.timedelta(days=1)
        m = re.search(r"(\d+)\s*(minute|min|hour|hr|day|week)s?\s*(?:ago)?", raw)
        if m:
            amount = int(m.group(1))
            seconds = {"minute": 60, "min": 60, "hour": 3600, "hr": 3600,
                       "day": 86400, "week": 604800}[m.group(2)]
            return NOW - dt.timedelta(seconds=amount * seconds)
        return None

def job(id, company, title, location, url, posted=None, desc=""):
    return dict(id=id, company=company or "", title=title or "", location=location or "",
                url=url, posted=parse_time(posted) if not isinstance(posted, dt.datetime) else posted,
                desc=(desc or "").lower())

def greenhouse(slug):
    for j in get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").get("jobs", []):
        yield job(f"gh-{j['id']}", slug, j["title"], (j.get("location") or {}).get("name"),
                  j["absolute_url"], j.get("updated_at"))

def lever(slug):
    for j in get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        yield job(f"lv-{j['id']}", slug, j["text"], (j.get("categories") or {}).get("location"),
                  j["hostedUrl"], j.get("createdAt"), j.get("descriptionPlain"))

def ashby(slug):
    for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", []):
        yield job(f"ab-{j['id']}", slug, j["title"], j.get("location"), j["jobUrl"],
                  j.get("publishedAt"), j.get("descriptionPlain"))

def smartrecruiters(slug):
    data = get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&country=in")
    for j in data.get("content", []):
        loc = j.get("location") or {}
        place = ", ".join(x for x in [loc.get("city"), loc.get("country", "").upper()] if x)
        yield job(f"sr-{j['id']}", slug, j["name"],
                  ("Remote " if loc.get("remote") else "") + place,
                  f"https://jobs.smartrecruiters.com/{slug}/{j['id']}", j.get("releasedDate"))

def workable(slug):
    data = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    for j in data.get("jobs", []):
        place = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        yield job(f"wk-{j['shortcode']}", slug, j["title"], place, j["url"],
                  j.get("published_on") or j.get("created_at"), strip(j.get("description")))

WD_RE = re.compile(r"https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)")

def workday_age(label):
    l = (label or "").lower()
    if "today" in l: return NOW
    if "yesterday" in l: return NOW - dt.timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*days", l)
    return NOW - dt.timedelta(days=int(m.group(1))) if m else None

def workday(entry):
    entry = {"url": entry} if isinstance(entry, str) else entry
    match = WD_RE.match(entry["url"])
    if not match:
        raise ValueError(f"unsupported Workday URL: {entry['url']}")
    tenant, wd, site = match.groups()
    host = f"{tenant}.{wd}.myworkdayjobs.com"
    for offset in (0, 20, 40):
        r = requests.post(f"https://{host}/wday/cxs/{tenant}/{site}/jobs", headers=UA, timeout=25,
                          json={"appliedFacets": {}, "limit": 20, "offset": offset,
                                "searchText": entry.get("search", "")})
        r.raise_for_status()
        posts = r.json().get("jobPostings", [])
        for j in posts:
            path = j.get("externalPath") or j.get("url") or j.get("jobUrl") or j.get("externalUrl")
            if not path:
                # Some tenants return a malformed posting without a public path.
                # Skip that posting instead of failing the entire tenant.
                continue
            path = str(path)
            if path.startswith("http"):
                public_url = path
            else:
                if not path.startswith("/"):
                    path = "/" + path
                public_url = f"https://{host}/en-US/{site}{path}"
            job_id = j.get("id") or j.get("jobId") or j.get("requisitionId") or path
            locations = j.get("locationsText") or j.get("location") or j.get("locations")
            if isinstance(locations, list):
                locations = ", ".join(
                    str(x.get("descriptor") or x.get("name") or x)
                    if isinstance(x, dict) else str(x)
                    for x in locations
                )
            yield job(f"wd-{tenant}-{job_id}", tenant, j.get("title"),
                      locations, public_url, workday_age(j.get("postedOn")),
                      strip(j.get("description") or j.get("jobDescription") or ""))
        if len(posts) < 20:
            break

def remotive(_):
    for j in get("https://remotive.com/api/remote-jobs?category=software-dev").get("jobs", []):
        yield job(f"rm-{j['id']}", j["company_name"], j["title"],
                  "Remote " + j.get("candidate_required_location", ""), j["url"],
                  j.get("publication_date"), strip(j.get("description")))

def remoteok(_):
    for j in get("https://remoteok.com/api")[1:]:
        yield job(f"ro-{j['id']}", j.get("company"), j.get("position"),
                  "Remote " + (j.get("location") or ""), j["url"], j.get("epoch"),
                  strip(j.get("description")))

def arbeitnow(_):
    for j in get("https://www.arbeitnow.com/api/job-board-api").get("data", []):
        yield job(f"an-{j['slug']}", j["company_name"], j["title"],
                  ("Remote " if j.get("remote") else "") + j.get("location", ""),
                  j["url"], j.get("created_at"), strip(j.get("description")))

def adzuna(cfg):
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return
    url = (f"https://api.adzuna.com/v1/api/jobs/{cfg['country']}/search/1?app_id={app_id}"
           f"&app_key={app_key}&results_per_page=50&sort_by=date&what={cfg['what']}&where={cfg['where']}")
    for j in get(url).get("results", []):
        yield job(f"az-{j['id']}", (j.get("company") or {}).get("display_name", ""),
                  j["title"], (j.get("location") or {}).get("display_name"),
                  j["redirect_url"], j.get("created"), j.get("description"))

LIST_SOURCES = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby,
                "smartrecruiters": smartrecruiters, "workable": workable, "workday": workday}
FLAG_SOURCES = {"remotive": remotive, "remoteok": remoteok, "arbeitnow": arbeitnow}
BOARD_SOURCES = {"linkedin": linkedin_guest, "naukri": naukri_public, "instahyre": instahyre_public}
APIFY_BOARD_SOURCES = {"linkedin": apify_linkedin, "naukri": apify_naukri, "instahyre": apify_instahyre}

def max_years_required(desc, url=""):
    text = " ".join([str(desc or ""), str(url or "")]).lower()
    nums = [int(n) for n in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?(?:years|yrs)", text)]
    ranges = re.findall(r"(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*years", text)
    nums.extend(int(high) for _, high in ranges)
    return max(nums) if nums else None

def location_matches(loc, allowed):
    """Match geography deliberately; 'remote' alone must not mean worldwide remote.
    For this India-focused profile, remote is accepted when the listing says India
    (or gives no conflicting country). City/location tokens remain exact-ish
    substring matches because source formatting varies.
    """
    loc = (loc or "").strip().lower()
    allowed = {x.strip().lower() for x in allowed}
    if not loc:
        return False
    if any(x in loc for x in ("united states", "usa", "canada", "uk", "united kingdom",
                              "europe", "germany", "france", "australia", "singapore")):
        return any(x in loc for x in ("india", "bengaluru", "bangalore", "gurugram",
                                      "gurgaon", "delhi"))
    for token in allowed - {"remote"}:
        if token in loc:
            return True
    if "remote" in allowed and "remote" in loc:
        return "india" in loc or not any(
            country in loc for country in ("united states", "usa", "canada", "uk",
                                           "united kingdom", "europe", "germany",
                                           "france", "australia", "singapore")
        )
    return False

def text_matches(value, phrase):
    value = re.sub(r"\s+", " ", (value or "").lower()).strip()
    phrase = re.sub(r"\s+", " ", (phrase or "").lower()).strip()
    if not phrase:
        return False
    if re.fullmatch(r"[a-z0-9]+", phrase) and len(phrase) <= 4:
        return bool(re.search(rf"\b{re.escape(phrase)}\b", value))
    return phrase in value


FIELD_TERMS = {
    "frontend": ["frontend", "front end", "react", "react native", "next.js", "next"],
    "backend": ["backend", "back end", "node.js", "node", "express", "fastapi", "django"],
    "full_stack": ["full stack", "fullstack"],
    "automation": ["automation", "workflow", "n8n", "orchestration"],
    "ai_ml": ["ai", "machine learning", "ml", "llm", "genai", "generative ai"],
    "python": ["python"],
    "javascript_typescript": ["javascript", "typescript"],
    "devops": ["devops", "ci/cd", "jenkins", "docker", "kubernetes"],
    "mobile": ["mobile", "react native", "flutter", "android", "ios"],
    "data": ["data engineer", "data science", "analytics", "pandas", "sql"],
}

def configured_title_terms(f):
    terms = list(f.get("title_include", []))
    terms.extend(f.get("keywords", []))
    for field in f.get("fields", []):
        terms.extend(FIELD_TERMS.get(str(field).lower(), [str(field)]))
    seen = set()
    return [x for x in terms if x and not (x.lower() in seen or seen.add(x.lower()))]

def board_queries(name, source_cfg, f):
    if not f.get("search_from_filters", True):
        return source_cfg.get(name, [])
    terms = []
    terms.extend(f.get("keywords", []))
    for field in f.get("fields", []):
        terms.extend(FIELD_TERMS.get(str(field).lower(), [str(field)]))
    terms = list(dict.fromkeys(x.strip() for x in terms if x and x.strip()))
    if not terms:
        return source_cfg.get(name, [])
    if name == "linkedin":
        return ["(" + " OR ".join(terms[:10]) + ")"]
    if name == "naukri":
        return terms[:8]
    if name == "instahyre":
        return [terms[0]]
    return source_cfg.get(name, [])

def passes(j, f):
    t, loc, d = j["title"].lower(), j["location"].lower(), j["desc"]
    title_terms = configured_title_terms(f)
    if title_terms and not any(text_matches(t, k) for k in title_terms):
        return False
    if any(text_matches(t, x) for x in f["title_exclude"]):
        return False
    if f["locations"] and not location_matches(loc, f["locations"]):
        return False
    if f["remote_only"] and "remote" not in loc:
        return False
    if f["max_age_hours"] and j["posted"] and (NOW - j["posted"]).total_seconds() > f["max_age_hours"] * 3600:
        return False
    if any(c.lower() in j["company"].lower() for c in f["company_exclude"]):
        return False
    if f["description_include_any"] and d and not any(text_matches(d, k) for k in f["description_include_any"]):
        return False
    if any(text_matches(d, k) for k in f["description_exclude_any"]):
        return False
    yrs = max_years_required(d, j.get("url"))
    if f["max_experience_years"] is not None and yrs is not None and yrs > f["max_experience_years"]:
        return False
    candidate = f.get("candidate_experience_years")
    if candidate is not None and yrs is not None and yrs > float(candidate):
        return False
    return True

def score_job(j, f):
    t, loc, d = j["title"].lower(), j["location"].lower(), j["desc"]
    score = 0
    reasons = []

    # Role / field relevance: up to 32 points.
    title_hits = list(dict.fromkeys(k for k in configured_title_terms(f) if text_matches(t, k)))
    score += min(32, len(title_hits) * 8)
    reasons.extend(title_hits[:4])

    # Skills match: up to 25 points.
    skill_hits = list(dict.fromkeys(k for k in f.get("skills", []) if text_matches(t, k) or text_matches(d, k)))
    score += min(25, len(skill_hits) * 5)
    reasons.extend(skill_hits[:5])

    # Location fit: 15 points, plus 5 for a remote listing.
    if location_matches(loc, f.get("locations", [])):
        score += 15
        reasons.append("location fit")
    if "remote" in loc:
        score += 5
        reasons.append("remote")

    # Freshness: up to 20 points.
    posted = j.get("posted")
    if isinstance(posted, str):
        posted = parse_time(posted)
        j["posted"] = posted
    if posted:
        age = max(0, (NOW - posted).total_seconds() / 3600)
        score += max(0, 20 - min(20, age))

    # Experience fit: 10 points when the listing exposes a requirement.
    required = max_years_required(d, j.get("url"))
    candidate = f.get("candidate_experience_years")
    if required is not None and candidate is not None:
        if required <= float(candidate):
            score += 10
            reasons.append("experience fit")
        else:
            reasons.append("experience gap")
    elif required is not None and f.get("max_experience_years") is not None and required <= f["max_experience_years"]:
        score += 5

    score = min(100, round(score))
    return score, list(dict.fromkeys(reasons))[:12]

def load_state():
    if not SEEN_FILE.exists():
        return None, set(), set()
    raw = json.loads(SEEN_FILE.read_text())
    if isinstance(raw, list):
        return True, set(raw), set()
    return True, set(raw["jobs"]), set(raw["sources"])

def load_source_state():
    if not SOURCE_STATE_FILE.exists():
        return {}
    try:
        raw = json.loads(SOURCE_STATE_FILE.read_text())
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}

def save_source_state(state):
    SOURCE_STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))

def source_key(name, arg):
    return f"{name}:{json.dumps(arg, sort_keys=True) if arg else ''}"

def cooldown_minutes(failures):
    # Back off broken sources instead of hammering them every scheduled run.
    # 20m, 40m, 80m ... capped at 6h.
    return min(360, 20 * (2 ** max(0, failures - 1)))

def should_poll(source_state, key, force=False):
    if force:
        return True
    until = source_state.get(key, {}).get("skip_until")
    if not until:
        return True
    try:
        return NOW >= dt.datetime.fromisoformat(until)
    except Exception:
        return True

def run_source(task):
    name, fn, arg = task
    try:
        return name, arg, list(fn(arg)), None
    except Exception as e:
        return name, arg, [], e

def run_board_source(task):
    name, fn, arg, cfg = task
    try:
        return name, arg, list(fn(cfg, arg)), None
    except Exception as e:
        return name, arg, [], e

def serial_job(j, source, score=None, reasons=None):
    experience = j.get("experience") or {"min": None, "max": None, "label": "Not specified", "source": "not_found"}
    return {
        "id": j["id"], "source": source, "company": j["company"], "title": j["title"],
        "location": j["location"], "jd_location": j.get("jd_location") or j["location"],
        "url": j["url"],
        "posted": j["posted"].isoformat() if j["posted"] else None,
        "score": score, "reasons": reasons or [],
        "description": j.get("description") or j.get("desc") or "",
        "experience": experience,
        "skills_detected": j.get("skills_detected", []),
        "work_mode": j.get("work_mode", "Not specified"),
        "jd_enriched": bool(j.get("jd_enriched")),
    }

def write_dashboard(jobs, source_status, sent):
    DASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": NOW.isoformat(),
        "last_run": NOW.isoformat(),
        "new_alerts": sent,
        "source_status": source_status,
        "jobs": jobs[:500]
    }
    DASH_FILE.write_text(json.dumps(payload, indent=2))

def notify(j, score, reasons):
    posted = j["posted"].strftime("%d %b %H:%M UTC") if j["posted"] else "unknown"
    why = ", ".join(reasons[:8]) or "profile filters"
    text = (f"🚨 {score}% MATCH\n{j['title']}\n🏢 {j['company']}\n"
            f"📍 {j['location']}\n🕒 {posted}\n✓ {why}\n🔗 {j['url']}")
    requests.post(f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
                  data={"chat_id": os.environ["TG_CHAT_ID"], "text": text}, timeout=20)

def main():
    exists, seen, known_sources = load_state()
    source_state = load_source_state()
    s, f = CFG["sources"], CFG["filters"]
    force_refresh = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    apify_cfg = CFG.get("apify", {})
    use_apify = (bool(os.environ.get("APIFY_API_TOKEN")) and
                 apify_cfg.get("enabled", True) and
                 apify_cfg.get("provider", "direct") == "apify")

    all_tasks = [(n, fn, a) for n, fn in LIST_SOURCES.items() for a in s.get(n, [])]
    all_tasks += [(n, fn, None) for n, fn in FLAG_SOURCES.items() if s.get(n)]
    all_board_tasks = []
    for name in BOARD_SOURCES:
        for query in board_queries(name, s, f):
            if use_apify:
                all_board_tasks.append((name, APIFY_BOARD_SOURCES[name], query, apify_cfg))
            else:
                all_board_tasks.append((name, BOARD_SOURCES[name], query, None))
    if s.get("adzuna", {}).get("enabled"):
        all_tasks.append(("adzuna", adzuna, s["adzuna"]))

    # Failed sources get exponential backoff. Manual runs always bypass it so
    # source debugging never gets stuck behind a previous failure.
    tasks = []
    board_tasks = []
    source_status = {}
    for task in all_tasks:
        key = source_key(task[0], task[2])
        if should_poll(source_state, key, force_refresh):
            tasks.append(task)
        else:
            source_status[key] = {
                "ok": False,
                "skipped": True,
                "count": 0,
                "error": "cooldown",
                "retry_at": source_state[key].get("skip_until"),
                "provider": "direct",
            }
    for task in all_board_tasks:
        key = source_key(task[0], task[2])
        if should_poll(source_state, key, force_refresh):
            board_tasks.append(task)
        else:
            source_status[key] = {
                "ok": False,
                "skipped": True,
                "count": 0,
                "error": "cooldown",
                "retry_at": source_state[key].get("skip_until"),
                "provider": "apify" if use_apify else "direct",
            }

    with ThreadPoolExecutor(max_workers=min(16, max(1, len(tasks) + len(board_tasks)))) as pool:
        results = list(pool.map(run_source, tasks))
        if use_apify:
            results += list(pool.map(run_board_source, board_tasks))
        else:
            # Keep public board scrapers sequential. LinkedIn rate-limits bursts,
            # so parallel board requests are counterproductive for a free setup.
            results += [run_source((x[0], x[1], x[2])) for x in board_tasks]

    alerts = []
    dashboard_jobs = []
    for name, arg, jobs, err in results:
        key = source_key(name, arg)
        provider = "apify" if use_apify and name in APIFY_BOARD_SOURCES else "direct"
        if err:
            previous = source_state.get(key, {})
            failures = int(previous.get("failures", 0)) + 1
            retry_at = NOW + dt.timedelta(minutes=cooldown_minutes(failures))
            source_state[key] = {
                "failures": failures,
                "last_error": str(err),
                "last_failure": NOW.isoformat(),
                "skip_until": retry_at.isoformat(),
                "generation": SOURCE_GENERATION,
            }
            source_status[key] = {
                "ok": False,
                "count": 0,
                "error": str(err),
                "provider": provider,
                "retry_at": retry_at.isoformat(),
                "failures": failures,
            }
            print(f"[warn] {key}: {err} (retry after {retry_at.isoformat()})")
            continue

        previous_generation = source_state.get(key, {}).get("generation")
        source_state[key] = {
            "failures": 0,
            "last_success": NOW.isoformat(),
            "last_count": len(jobs),
            "skip_until": None,
            "generation": SOURCE_GENERATION,
        }
        source_status[key] = {
            "ok": True,
            "count": len(jobs),
            "error": None,
            "provider": provider,
        }
        silent = ((not exists) or key not in known_sources or previous_generation != SOURCE_GENERATION)
        known_sources.add(key)
        for j in jobs:
            j["source"] = name

            # First apply cheap source-level filters. Only likely matches get
            # JD enrichment so a free run does not fetch every job page.
            if not passes(j, f):
                if j["id"] in seen:
                    continue
                seen.add(j["id"])
                continue

            # Enrich the likely match from its public job page. This supplies
            # structured experience, skills, work mode, location and the full JD.
            enriched = enrich_job(j)
            j.update({
                "desc": enriched.get("description") or j.get("desc", ""),
                "description": enriched.get("description", ""),
                "experience": enriched.get("experience"),
                "skills_detected": enriched.get("skills_detected", []),
                "work_mode": enriched.get("work_mode", "Not specified"),
                "jd_location": enriched.get("jd_location") or j.get("location", ""),
                "jd_enriched": enriched.get("jd_enriched", False),
            })

            # Re-check after enrichment because the JD may reveal an experience
            # requirement that was not present in the source listing card.
            if not passes(j, f):
                if j["id"] in seen:
                    continue
                seen.add(j["id"])
                continue

            score, reasons = score_job(j, f)
            dashboard_jobs.append(serial_job(j, name, score, reasons))

            if j["id"] in seen:
                continue
            seen.add(j["id"])
            if (not silent and f.get("notifications_enabled", True) and
                    os.environ.get("TG_TOKEN") and os.environ.get("TG_CHAT_ID")):
                notify(j, score, reasons)
                alerts.append(j["id"])

    dashboard_jobs.sort(key=lambda x: (x["score"] or 0, x["posted"] or ""), reverse=True)
    # Keep a compact, fresh feed. Deduplicate by job id across overlapping sources.
    unique = {}
    for item in dashboard_jobs:
        unique[item["id"]] = item
    dashboard_jobs = sorted(unique.values(), key=lambda x: (x["posted"] or ""), reverse=True)
    write_dashboard(dashboard_jobs, source_status, len(alerts))
    save_source_state(source_state)
    SEEN_FILE.write_text(json.dumps({"jobs": sorted(seen), "sources": sorted(known_sources)}))
    print(f"done: {len(alerts)} alerts from {len(tasks) + len(board_tasks)} sources; dashboard={len(dashboard_jobs)}")

if __name__ == "__main__":
    main()
