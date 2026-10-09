"""Search-index discovery for ATS/job platforms that do not expose a single
global public API.

This is a fallback/discovery layer, not a claim of exhaustive coverage.
It searches public indexed job pages using DDGS and normalizes the results.
Direct ATS adapters remain preferred where a company slug is configured.

No login or credential is required.
"""
from __future__ import annotations
import re
import hashlib
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

PLATFORMS = {
    "Ashby": ["jobs.ashbyhq.com"],
    "Avature": ["avature.net"],
    "BambooHR": ["bamboohr.com"],
    "Breezy": ["breezy.hr"],
    "Cutshort": ["cutshort.io"],
    "Darwinbox": ["darwinbox.com"],
    "Eightfold AI": ["eightfold.ai"],
    "Freshteam": ["freshteam.com"],
    "Greenhouse": ["boards.greenhouse.io", "job-boards.greenhouse.io"],
    "Hireology": ["hireology.com"],
    "Hirist": ["hirist.tech"],
    "HRsmart": ["hrsmart.com"],
    "iCIMS": ["icims.com"],
    "Instahyre": ["instahyre.com"],
    "Jibe (iCIMS)": ["icims.com"],
    "Jobvite": ["jobvite.com"],
    "Keka": ["keka.com"],
    "Lever": ["jobs.lever.co"],
    "LinkedIn": ["linkedin.com/jobs"],
    "Naukri": ["naukri.com"],
    "Oracle Cloud Recruiting": ["oraclecloud.com"],
    "Paycom": ["paycom.com"],
    "PeopleStrong": ["peoplestrong.com"],
    "Phenom People": ["phenompeople.com"],
    "Recruitee": ["recruitee.com"],
    "Rippling ATS": ["rippling.com"],
    "SmartRecruiters": ["jobs.smartrecruiters.com"],
    "SAP SuccessFactors": ["successfactors.com"],
    "Oracle Taleo": ["taleo.net"],
    "Teamtailor": ["teamtailor.com"],
    "UKG Pro / UltiPro": ["ultipro.com", "ukg.com"],
    "Wellfound": ["wellfound.com/jobs"],
    "Workable": ["apply.workable.com", "workable.com"],
    "Workday": ["myworkdayjobs.com"],
    "Y Combinator": ["ycombinator.com/jobs"],
    "Zoho Recruit": ["zohorecruit.com"],
}

ROLE_TERMS = [
    "software engineer", "software developer", "full stack developer",
    "frontend developer", "backend developer", "react developer",
    "python developer", "automation engineer", "ai engineer",
]

def _host(url):
    return urlparse(url).netloc.lower().replace("www.", "")

def _platform_url(url, domains):
    host=_host(url)
    path=urlparse(url).path.lower()
    return any(d in host or d in (host+path) for d in domains)

def _posted(value):
    text=(value or '').lower()
    if 'today' in text or 'just now' in text:
        return dt.datetime.now(dt.timezone.utc)
    m=re.search(r'(\d+)\s*(minute|min|hour|hr|day|week)s?\s*ago', text)
    if not m:
        return None
    n=int(m.group(1)); unit=m.group(2)
    sec={'minute':60,'min':60,'hour':3600,'hr':3600,'day':86400,'week':604800}[unit]
    return dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=n*sec)

def _company(url):
    p=urlparse(url)
    host=p.netloc.lower().replace("www.","")
    parts=[x for x in p.path.split("/") if x]
    if "myworkdayjobs.com" in host:
        return host.split(".")[0]
    if parts:
        return parts[0]
    return host.split(".")[0] if host else ""

def _query(filters, platform, domains):
    keywords=filters.get("keywords") or ROLE_TERMS
    locations=filters.get("locations") or ["India","Bengaluru","Gurugram","Delhi"]
    roles=" OR ".join('"'+str(x).strip()+'"' for x in keywords[:8] if str(x).strip())
    locs=" OR ".join('"'+str(x).strip()+'"' for x in locations[:8] if str(x).strip())
    domain=" OR ".join("site:"+d for d in domains)
    return f"({roles}) ({locs}) ({domain})"

def discover_platform(item):
    platform, domains, filters, max_results, timelimit = item
    if DDGS is None:
        return platform, [], "ddgs package not installed"
    q=_query(filters,platform,domains)
    try:
        results=DDGS(timeout=12).text(q, region="in-en", safesearch="moderate",
                                      timelimit=timelimit, max_results=max_results,
                                      backend="auto")
        jobs=[]
        for idx,r in enumerate(results or []):
            url=r.get("href") or r.get("url") or ""
            title=(r.get("title") or "").strip()
            body=(r.get("body") or "").strip()
            if not url or not _platform_url(url,domains):
                continue
            text=(title+" "+body).lower()
            if not any(k.lower() in text for k in ROLE_TERMS):
                continue
            # Avoid treating the platform home/search page as a job.
            path=urlparse(url).path.strip("/")
            if not path or len(path)<4:
                continue
            ident=f"web-{platform.lower().replace(' ','-')}-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]}"
            jobs.append({"id":ident,"company":_company(url),"title":title,"location":"","url":url,"posted":_posted(title+" "+body),"desc":body.lower()})
        return platform,jobs,None
    except Exception as exc:
        return platform,[],str(exc)

def discover(filters, max_results=8):
    if not filters.get("web_discovery_enabled", True):
        return []
    age=int(filters.get("max_age_hours") or 72)
    timelimit="d" if age <= 24 else "w"
    tasks=[(p,d,filters,max_results,timelimit) for p,d in PLATFORMS.items()]
    results=[]
    workers=min(3, len(tasks))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for platform,jobs,error in pool.map(discover_platform,tasks):
            results.append((platform,jobs,error))
    return results
