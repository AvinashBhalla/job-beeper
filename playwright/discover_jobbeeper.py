"""Automatic local JobBeeper UI discovery for the IDE.

Login is performed manually in the headed browser once. The persistent local
profile keeps the session. Discovery then runs automatically and writes
playwright/knowledge/jobbeeper_snapshot.json and .md plus HTML/screenshots.

No cookies, localStorage, sessionStorage, passwords, or tokens are exported.
The crawler avoids Apply/Save/Delete/Logout/Submit and other state-changing UI.
"""
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT=Path(__file__).resolve().parents[1]
PROFILE=ROOT/".playwright-profile"
OUT=ROOT/"playwright"/"artifacts"
KNOW=ROOT/"playwright"/"knowledge"
DANGER=re.compile(r"\b(apply|save|delete|remove|logout|log out|submit|send|purchase|buy|disconnect)\b",re.I)
NAV=re.compile(r"\b(jobs?|applied|filters?|companies|openings|settings|sources|preferences|alerts?|notifications?)\b",re.I)

def iso(): return datetime.now(timezone.utc).isoformat()
def clean(s,n=500): return re.sub(r"\s+"," ",s or "").strip()[:n]
def slug(s): return re.sub(r"[^a-zA-Z0-9._-]+","-",clean(s,100)).strip("-")[:60] or "page"

def logged_out(page):
    u=page.url.lower()
    if any(x in u for x in ("/login","/signin","/sign-in","/auth")): return True
    try: body=clean(page.locator("body").inner_text(timeout=2500),2500).lower()
    except Exception: return True
    return sum(x in body for x in ("sign in","log in","login","create account","forgot password"))>=2

def wait_login(page,seconds):
    if not logged_out(page): return
    print("Complete JobBeeper login in the visible browser. Discovery will continue automatically.")
    end=time.time()+seconds
    while time.time()<end:
        if not logged_out(page):
            print("Login detected.")
            return
        page.wait_for_timeout(2000)
    raise TimeoutError("Login was not detected before timeout.")

def controls(page):
    out=[]
    for sel,kind in (("input","input"),("textarea","textarea"),("select","select"),("button","button")):
        for i,e in enumerate(page.locator(sel).all()):
            try:
                if not e.is_visible(): continue
                text=clean(e.inner_text(),160)
                aria=clean(e.get_attribute("aria-label") or "",120)
                name=clean(e.get_attribute("name") or "",120)
                ph=clean(e.get_attribute("placeholder") or "",160)
                typ=e.get_attribute("type") or ""
                opts=clean(e.inner_text(),500) if kind=="select" else ""
                disabled=e.is_disabled()
                safe=not disabled and not DANGER.search(" ".join((text,aria,name)))
                out.append({"kind":kind,"index":i,"text":text,"aria_label":aria,"name":name,"placeholder":ph,"type":typ,"options":opts,"disabled":disabled,"safe_to_click":safe})
            except Exception: pass
    return out

def links(page):
    out=[]
    for i,e in enumerate(page.locator("a").all()):
        try:
            if not e.is_visible(): continue
            text=clean(e.inner_text(),160); href=e.get_attribute("href") or ""
            out.append({"index":i,"text":text,"href":href,"url":urljoin(page.url,href) if href else "","safe":bool(href and not DANGER.search(text))})
        except Exception: pass
    return out

def capture(page,key):
    OUT.mkdir(parents=True,exist_ok=True)
    s=slug(key); hp=OUT/(s+".html"); pp=OUT/(s+".png")
    try: body=clean(page.locator("body").inner_text(timeout=5000),12000)
    except Exception: body=""
    try: heads=[clean(x,160) for x in page.locator("h1,h2,h3,h4").all_inner_texts() if clean(x)]
    except Exception: heads=[]
    cs=controls(page); ls=links(page)
    hp.write_text(page.content(),encoding="utf-8")
    page.screenshot(path=str(pp),full_page=True)
    return {"key":key,"captured_at":iso(),"url":page.url,"title":clean(page.title(),250),
            "headings":heads,"visible_text":body,"controls":cs,"links":ls,
            "artifacts":{"html":str(hp.relative_to(ROOT)),"screenshot":str(pp.relative_to(ROOT))}}

def nav_targets(page):
    seen=set(); out=[]
    for x in links(page):
        if not x["safe"] or not x["url"]: continue
        if urlparse(x["url"]).netloc!=urlparse(page.url).netloc: continue
        if not NAV.search(x["text"]): continue
        k=(x["text"],x["url"])
        if k not in seen: seen.add(k); out.append(k)
    for x in controls(page):
        text=x["text"] or x["aria_label"]
        if x["kind"]=="button" and x["safe_to_click"] and NAV.search(text):
            k=(text,"button:"+str(x["index"]))
            if k not in seen: seen.add(k); out.append(k)
    return out

def go(page,text,target):
    if target.startswith("button:"):
        try:
            b=page.get_by_role("button",name=re.compile(re.escape(text),re.I)).first
            if not b.is_visible() or b.is_disabled() or DANGER.search(text): return False
            b.click(timeout=5000); page.wait_for_timeout(700); return True
        except Exception: return False
    try:
        page.goto(target,wait_until="domcontentloaded",timeout=20000); return True
    except Exception: return False

def discover(page,max_pages):
    pages=[capture(page,"00-home")]; seen={page.url}; queue=nav_targets(page); i=1
    while queue and len(pages)<max_pages:
        text,target=queue.pop(0)
        if not go(page,text,target): continue
        try: page.wait_for_load_state("domcontentloaded",timeout=7000)
        except PWTimeout: pass
        page.wait_for_timeout(500)
        if page.url in seen or logged_out(page): continue
        pages.append(capture(page,"%02d-%s"%(i,text))); seen.add(page.url); i+=1
        for t in nav_targets(page):
            if t not in queue and t[1] not in seen: queue.append(t)
    return {"schema_version":1,"generated_at":iso(),"source":"JobBeeper",
            "purpose":"Rendered UI evidence for implementing our JobBeeper-like dashboard",
            "safety":{"credentials_saved":False,"cookies_saved":False,"local_storage_saved":False,
                      "session_storage_saved":False,"destructive_actions_clicked":False},
            "pages":pages,
            "summary":{"page_count":len(pages),"controls":sum(len(x["controls"]) for x in pages),
                       "links":sum(len(x["links"]) for x in pages)}}

def write(report):
    KNOW.mkdir(parents=True,exist_ok=True)
    jp=KNOW/"jobbeeper_snapshot.json"; mp=KNOW/"jobbeeper_snapshot.md"
    jp.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    lines=["# JobBeeper UI discovery","", "Generated: "+report["generated_at"],
           "","Primary evidence for the IDE. Authentication data is intentionally excluded.","",
           "## Pages"]
    for p in report["pages"]:
        lines += ["","### "+p["key"],"- URL: "+p["url"],"- Title: "+p["title"],
                  "- Headings: "+(", ".join(p["headings"]) or "none"),
                  "- HTML: "+p["artifacts"]["html"],"- Screenshot: "+p["artifacts"]["screenshot"],"",
                  "#### Controls"]
        for c in p["controls"]:
            lines.append("- %s | text=%s | name=%s | placeholder=%s | safe=%s" %
                         (c["kind"],c["text"],c["name"],c["placeholder"],c["safe_to_click"]))
        lines += ["","#### Links"]
        for l in p["links"]:
            if l["text"] or l["href"]: lines.append("- %s -> %s"%(l["text"],l["href"]))
        lines += ["","#### Visible text","",p["visible_text"][:5000]]
    mp.write_text("\n".join(lines),encoding="utf-8")
    print("Wrote",jp)
    print("Wrote",mp)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",default="https://jobbeeper.com")
    ap.add_argument("--login-timeout",type=int,default=300)
    ap.add_argument("--max-pages",type=int,default=15)
    ap.add_argument("--slow-mo",type=int,default=50)
    ap.add_argument("--watch",action="store_true")
    ap.add_argument("--interval",type=int,default=1800)
    a=ap.parse_args()
    PROFILE.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        ctx=p.chromium.launch_persistent_context(str(PROFILE),headless=False,slow_mo=a.slow_mo,viewport={"width":1440,"height":1000})
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(a.url,wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle",timeout=10000)
        except Exception: pass
        try:
            while True:
                wait_login(page,a.login_timeout)
                print("Starting automatic JobBeeper discovery:",page.url)
                report=discover(page,a.max_pages); write(report)
                print("Captured %d pages, %d controls, %d links."%(report["summary"]["page_count"],report["summary"]["controls"],report["summary"]["links"]))
                if not a.watch: break
                print("Next discovery in %d seconds."%a.interval)
                page.wait_for_timeout(a.interval*1000)
                page.goto(a.url,wait_until="domcontentloaded")
        except KeyboardInterrupt: print("Discovery stopped.")
        finally: ctx.close()

if __name__=="__main__": main()
