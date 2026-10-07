"""Interactive headed JobBeeper inspector.

Run locally from VS Code:
    python playwright/inspect_jobbeeper.py

Or inspect a specific URL:
    python playwright/inspect_jobbeeper.py --url https://jobbeeper.com

A persistent Chromium profile is used so a user can sign in interactively once
and keep the session for later inspection. Credentials are never stored here.
The script only prints page metadata and saves a DOM snapshot/screenshot locally.
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / ".playwright-profile"
ARTIFACTS = ROOT / "playwright" / "artifacts"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://jobbeeper.com", help="URL to inspect")
    parser.add_argument("--slow-mo", type=int, default=100, help="Delay between browser actions in ms")
    args = parser.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=False,
            slow_mo=args.slow_mo,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        print("\n=== JobBeeper inspector ===")
        print("URL:", page.url)
        print("TITLE:", page.title())
        input("\nUse the headed browser to log in and navigate through the UI. Press Enter here when you want to capture the current page...")

        print("\nVisible headings:")
        for heading in page.locator("h1,h2,h3").all_inner_texts():
            text = heading.strip()
            if text:
                print(" -", text)

        print("\nButtons:")
        for button in page.get_by_role("button").all_inner_texts():
            text = button.strip()
            if text:
                print(" -", text)

        print("\nLinks:")
        for link in page.get_by_role("link").all_inner_texts():
            text = link.strip()
            if text:
                print(" -", text)

        page.screenshot(path=str(ARTIFACTS / "jobbeeper-inspection.png"), full_page=True)
        (ARTIFACTS / "jobbeeper-inspection.html").write_text(
            page.content(), encoding="utf-8"
        )

        print("\nSaved:")
        print(" -", ARTIFACTS / "jobbeeper-inspection.png")
        print(" -", ARTIFACTS / "jobbeeper-inspection.html")
        print("\nBrowser is intentionally left open.")
        print("Inspect filters/UI manually. Press Ctrl+C in this terminal when finished.")

        try:
            page.wait_for_timeout(60 * 60 * 1000)
        except KeyboardInterrupt:
            pass
        finally:
            context.close()


if __name__ == "__main__":
    main()
