"""Personal job watcher + dashboard feed.
Polls free sources in parallel, normalizes and scores jobs, alerts new matches on Telegram,
and writes dashboard/data/jobs.json for the live UI.
"""
import json, os, re, pathlib, datetime as dt, requests
from concurrent.futures import ThreadPoolExecutor
from job_sources_extra import linkedin_guest, naukri_public, instahyre_public

ROOT = pathlib.Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text())
SEEN_FILE = ROOT / "seen.json"
DASH_FILE = ROOT / "dashboard" / "data" / "jobs.json"
UA = {"User-Agent": "Mozilla/5.0 (personal-job-watcher)"}
NOW = dt.datetime.now(dt.timezone.utc)
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
            yield job(f"wd-{tenant}-{j['externalPath']}", tenant, j.get("title"),
                      j.get("locationsText"),
                      f"https://{host}/en-US/{site}{j['externalPath']}",
                      workday_age(j.get("postedOn")))
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

def max_years_required(desc):
    nums = [int(n) for n in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?(?:years|yrs)", desc)]
    return max(nums) if nums else None

def passes(j, f):
    t, loc, d = j["title"].lower(), j["location"].lower(), j["desc"]
    if f["title_include"] and not any(k.lower() in t for k in f["title_include"]):
        return False
    if any(x.lower() in t for x in f["title_exclude"]):
        return False
    if f["locations"] and loc and not any(l.lower() in loc for l in f["locations"]):
        return False
    if f["remote_only"] and "remote" not in loc:
        return False
    if f["max_age_hours"] and j["posted"] and (NOW - j["posted"]).total_seconds() > f["max_age_hours"] * 3600:
        return False
    if any(c.lower() in j["company"].lower() for c in f["company_exclude"]):
        return False
    if f["description_include_any"] and d and not any(k.lower() in d for k in f["description_include_any"]):
        return False
    if any(k.lower() in d for k in f["description_exclude_any"]):
        return False
    yrs = max_years_required(d)
    return not (f["max_experience_years"] is not None and yrs is not None and yrs > f["max_experience_years"])

def score_job(j, f):
    t, loc, d = j["title"].lower(), j["location"].lower(), j["desc"]
    score = 0
    reasons = []
    for k in f.get("title_include", []):
        if k.lower() in t:
            score += 8
            reasons.append(k)
    for k in f.get("skills", []):
        if k.lower() in t or k.lower() in d:
            score += 5
            reasons.append(k)
    if any(l.lower() in loc for l in f.get("locations", [])):
        score += 15
    if "remote" in loc:
        score += 10
    posted = j.get("posted")
    if isinstance(posted, str):
        posted = parse_time(posted)
        j["posted"] = posted
    if posted:
        age = max(0, (NOW - posted).total_seconds() / 3600)
        score += max(0, 20 - min(20, age))
    if max_years_required(d) is not None and max_years_required(d) <= (f.get("max_experience_years") or 99):
        score += 10
    score = min(100, round(score))
    return score, list(dict.fromkeys(reasons))[:12]

def load_state():
    if not SEEN_FILE.exists():
        return None, set(), set()
    raw = json.loads(SEEN_FILE.read_text())
    if isinstance(raw, list):
        return True, set(raw), set()
    return True, set(raw["jobs"]), set(raw["sources"])

def run_source(task):
    name, fn, arg = task
    try:
        return name, arg, list(fn(arg)), None
    except Exception as e:
        return name, arg, [], e

def serial_job(j, source, score=None, reasons=None):
    return {
        "id": j["id"], "source": source, "company": j["company"], "title": j["title"],
        "location": j["location"], "url": j["url"],
        "posted": j["posted"].isoformat() if j["posted"] else None,
        "score": score, "reasons": reasons or []
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
    s, f = CFG["sources"], CFG["filters"]
    tasks = [(n, fn, a) for n, fn in LIST_SOURCES.items() for a in s.get(n, [])]
    tasks += [(n, fn, None) for n, fn in FLAG_SOURCES.items() if s.get(n)]
    for name, fn in BOARD_SOURCES.items():
        for query in s.get(name, []):
            tasks.append((name, fn, query))
    if s.get("adzuna", {}).get("enabled"):
        tasks.append(("adzuna", adzuna, s["adzuna"]))

    with ThreadPoolExecutor(max_workers=min(16, max(1, len(tasks)))) as pool:
        results = list(pool.map(run_source, tasks))

    alerts = []
    dashboard_jobs = []
    source_status = {}
    for name, arg, jobs, err in results:
        key = f"{name}:{json.dumps(arg, sort_keys=True) if arg else ''}"
        source_status[key] = {"ok": err is None, "count": len(jobs), "error": str(err) if err else None}
        if err:
            print(f"[warn] {key}: {err}")
            continue
        silent = (not exists) or key not in known_sources
        known_sources.add(key)
        for j in jobs:
            j["source"] = name
            score, reasons = score_job(j, f)
            if passes(j, f):
                dashboard_jobs.append(serial_job(j, name, score, reasons))
            if j["id"] in seen:
                continue
            seen.add(j["id"])
            if not silent and passes(j, f) and os.environ.get("TG_TOKEN") and os.environ.get("TG_CHAT_ID"):
                notify(j, score, reasons)
                alerts.append(j["id"])

    dashboard_jobs.sort(key=lambda x: (x["score"] or 0, x["posted"] or ""), reverse=True)
    # Keep a compact, fresh feed. Deduplicate by job id across overlapping sources.
    unique = {}
    for item in dashboard_jobs:
        unique[item["id"]] = item
    dashboard_jobs = sorted(unique.values(), key=lambda x: (x["posted"] or ""), reverse=True)
    write_dashboard(dashboard_jobs, source_status, len(alerts))
    SEEN_FILE.write_text(json.dumps({"jobs": sorted(seen), "sources": sorted(known_sources)}))
    print(f"done: {len(alerts)} alerts from {len(tasks)} sources; dashboard={len(dashboard_jobs)}")

if __name__ == "__main__":
    main()
