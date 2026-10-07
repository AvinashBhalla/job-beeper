# Playwright inspection

This folder is for local browser inspection and future end-to-end automation.

## Install

From the repository root:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Playwright launches headed locally so you can watch every action. The persistent
profile lives in `.playwright-profile/`, which keeps the browser session/cookies
between runs.

## Inspect JobBeeper

```powershell
python playwright/inspect_jobbeeper.py
```

Or pass a specific page:

```powershell
python playwright/inspect_jobbeeper.py --url https://jobbeeper.com
```

The script does not contain or request a password. If the site asks you to log
in, complete that interactively in the headed browser.

## VS Code

Install the Playwright VS Code extension if you want locator picking, debugging,
and trace inspection. Keep the Python inspector script as the source of truth
for repeatable flows.

## Planned automation

1. Inspect JobBeeper filters and interaction behavior.
2. Record the filter model and page states.
3. Map those controls to our local dashboard.
4. Add configurable filters without hard-coding them into the scraper.
5. Add browser-based source adapters where HTTP scraping cannot expose a usable JD.
