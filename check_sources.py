"""Tests every source in config.json and reports which slugs are dead.
  python check_sources.py            # report only
  python check_sources.py --prune    # also remove dead (404) entries from config.json
"""
import json, sys, requests
from concurrent.futures import ThreadPoolExecutor
import job_watch as jw

def check(task):
    name, arg = task
    try:
        n = sum(1 for _ in jw.LIST_SOURCES[name](arg))
        return name, arg, "ok", n
    except requests.HTTPError as e:
        return name, arg, ("dead" if e.response.status_code in (404, 400) else f"error {e.response.status_code}"), 0
    except Exception as e:
        return name, arg, f"error {type(e).__name__}", 0

def main():
    src = jw.CFG["sources"]
    tasks = [(n, a) for n in jw.LIST_SOURCES for a in src.get(n, [])]
    with ThreadPoolExecutor(8) as pool:
        res = list(pool.map(check, tasks))
    dead = []
    for name, arg, status, n in res:
        label = arg if isinstance(arg, str) else arg["url"]
        print(f"{status:12} {name:16} {label} ({n} jobs)")
        if status == "dead":
            dead.append((name, arg))
    print(f"\n{sum(r[2]=='ok' for r in res)} ok, {len(dead)} dead, {len(res)} total")
    if "--prune" in sys.argv and dead:
        cfg = json.loads((jw.ROOT / "config.json").read_text())
        for name, arg in dead:
            cfg["sources"][name].remove(arg)
        (jw.ROOT / "config.json").write_text(json.dumps(cfg, indent=2))
        print("pruned dead entries from config.json")

if __name__ == "__main__":
    main()
