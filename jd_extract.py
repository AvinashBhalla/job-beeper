"""Best-effort job-description fetching and structured extraction.

No paid AI API is required. The extractor uses public job-page HTML plus
deterministic parsing so the dashboard can explain what it found.
"""
import json
import re
import requests
from bs4 import BeautifulSoup

def fetch_description(url):
    for target in _candidate_urls(url):
        try:
            r = requests.get(target, headers=UA, timeout=15)
            if r.status_code >= 400:
                continue
            soup = BeautifulSoup(r.text, "html.parser")

            # Prefer structured JSON-LD JobPosting.description.
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or script.get_text())
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            desc = BeautifulSoup(str(item.get("description") or ""), "html.parser").get_text(" ", strip=True)
                            if len(desc) >= 300:
                                return clean_text(desc)
                except Exception:
                    pass

            selectors = [
                '[class*="description"]',
                '[id*="description"]',
                '[class*="job-description"]',
                'article',
                'main',
            ]
            candidates = []
            for selector in selectors:
                for node in soup.select(selector):
                    text = clean_text(node.get_text(" ", strip=True))
                    if len(text) >= 300:
                        candidates.append(text)
            if candidates:
                return max(candidates, key=len)[:12000]

            meta = soup.select_one('meta[name="description"]')
            if meta and meta.get("content"):
                text = clean_text(meta["content"])
                if len(text) >= 200:
                    return text
        except Exception:
            continue
    return ""

def extract_experience(text):
    t = clean_text(text).lower()
    patterns = [
        r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:years?|yrs?)\b",
        r"(\d+)\s*\+\s*(?:years?|yrs?)\b",
        r"(?:minimum|at least)\s*(\d+)\s*(?:years?|yrs?)\b",
        r"(?:experience|exp)\s*(?:of|:)?\s*(\d+)\s*(?:years?|yrs?)\b",
        r"(\d+)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:professional|relevant|software|industry)\s+experience\b",
    ]
    ranges = []
    for a, b in re.findall(patterns[0], t):
        ranges.append((int(a), int(b)))
    if ranges:
        lo, hi = ranges[0]
        return {"min": lo, "max": hi, "label": f"{lo}-{hi} years", "source": "job_description"}
    m = re.search(patterns[1], t) or re.search(patterns[2], t)
    if m:
        n = int(m.group(1))
        return {"min": n, "max": None, "label": f"{n}+ years", "source": "job_description"}
    m = re.search(patterns[3], t) or re.search(patterns[4], t)
    if m:
        n = int(m.group(1))
        return {"min": n, "max": n, "label": f"{n} years", "source": "job_description"}
    return {"min": None, "max": None, "label": "Not specified", "source": "not_found"}

def extract_work_mode(text, location):
    t = clean_text(" ".join([location or "", text or ""])).lower()
    if re.search(r"\bhybrid\b", t):
        return "Hybrid"
    if re.search(r"\b(?:on[- ]site|onsite|office[- ]based)\b", t):
        return "On-site"
    if re.search(r"\b(?:fully )?remote\b", t):
        return "Remote"
    return "Not specified"

def extract_skills(text):
    t = clean_text(text).lower()
    found = []
    for skill in SKILL_TERMS:
        if re.search(rf"(?<![a-z0-9+#]){re.escape(skill)}(?![a-z0-9+#])", t):
            found.append(skill)
    return found[:20]

def extract_location(text, fallback):
    fallback = clean_text(fallback)
    t = clean_text(text)

    # Source-level location is usually more reliable than free-form JD prose.
    # Only replace it when the JD contains an explicit, compact location field.
    patterns = [
        r"\\b(?:location|locations?)\\s*[:\\-]\\s*([^.;|]{3,100})",
        r"\\b(?:based in|office in)\\s+([A-Z][^.;|]{2,80})",
    ]
    for pattern in patterns:
        m = re.search(pattern, t, re.I)
        if m:
            value = clean_text(m.group(1))
            if value and len(value) <= 100 and not value.lower().startswith(("employment type", "experience level")):
                return value

    if fallback:
        return fallback
    if re.search(r"\\bfully remote\\b|\\bremote role\\b|\\bremote position\\b", t, re.I):
        return "Remote"
    return "Not specified"

def enrich_job(job):
    existing = job.get("desc") or ""
    description = existing if len(existing) >= 500 else fetch_description(job.get("url", ""))
    if not description:
        description = existing

    experience = extract_experience(description)
    skills = extract_skills(" ".join([job.get("title", ""), description]))
    work_mode = extract_work_mode(description, job.get("location", ""))
    location = extract_location(description, job.get("location", ""))

    enriched = dict(job)
    enriched["description"] = description[:12000]
    enriched["experience"] = experience
    enriched["skills_detected"] = skills
    enriched["work_mode"] = work_mode
    enriched["jd_location"] = location
    enriched["jd_enriched"] = bool(description)
    return enriched
