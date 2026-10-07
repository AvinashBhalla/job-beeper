"""Best-effort public job-board adapters.
Uses public unauthenticated pages/endpoints only. These adapters are optional because
public HTML/API shapes can change or be rate-limited.
"""
import re
import requests
from bs4 import BeautifulSoup

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
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
    base = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    for start in (0, 25, 50, 75):
        soup = _soup(base, {"keywords": keyword, "location": "India", "start": start})
        cards = soup.select("li")
        if not cards:
            break
        for card in cards:
            link = card.select_one("a.base-card__full-link") or card.select_one("a[href*='/jobs/view/']")
            title = card.select_one("h3.base-search-card__title")
            company = card.select_one("h4.base-search-card__subtitle")
            loc = card.select_one("span.job-search-card__location")
            time = card.select_one("time")
            if not link or not title:
                continue
            url = link.get("href", "").split("?")[0]
            jid = re.search(r"jobs/view/(\d+)", url)
            yield _job(
                f"li-{jid.group(1) if jid else url}", _text(company), _text(title),
                _text(loc), url, time.get("datetime") if time else None, _text(card)
            )

def naukri_public(keyword):
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
    soup = _soup(f"https://www.naukri.com/{slug}-jobs-in-india")
    cards = soup.select("article.jobTuple, article.jobTupleHeader, div.jobTuple")
    for card in cards:
        link = card.select_one("a.title") or card.select_one("a[href*='/job-listings-']")
        company = card.select_one("a.subTitle")
        loc = card.select_one("span.locWdth") or card.select_one("span[title]")
        exp = card.select_one("span.expwdth")
        posted = card.select_one("span.job-post-day")
        desc = card.select_one("div.job-description")
        if not link:
            continue
        href = link.get("href")
        yield _job(
            f"nk-{href}", _text(company), _text(link), _text(loc), href,
            _text(posted), f"{_text(desc)} {_text(exp)}"
        )

def instahyre_public(keyword):
    soup = _soup("https://www.instahyre.com/search-jobs/",
                 {"q": keyword, "location": "India"})
    seen = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if not re.search(r"/job[s]?/", href, re.I):
            continue
        if href.startswith("/"):
            href = "https://www.instahyre.com" + href
        if href in seen:
            continue
        seen.add(href)
        title = _text(a)
        if len(title) < 3:
            continue
        card = a.find_parent(lambda x: x.name in ("article", "li", "div") and len(_text(x)) > 40)
        yield _job(f"ih-{href}", "Instahyre", title, "India", href, None, _text(card or a))
