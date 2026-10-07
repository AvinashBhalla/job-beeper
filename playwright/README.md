# Playwright inspection and JobBeeper discovery

## Automatic discovery

Run from the repository root:

python -m pip install -r requirements.txt
python -m playwright install chromium
python playwright/discover_jobbeeper.py

The headed browser reuses the local .playwright-profile. If JobBeeper asks for login, complete it manually in the browser. After authentication the crawler continues automatically.

It discovers safe navigation sections and records rendered headings, text, links, buttons, inputs, textareas, selects, URLs, HTML and screenshots.

It intentionally does not export cookies, localStorage, sessionStorage, passwords, tokens, or other authentication state. It also avoids Apply, Save, Delete, Logout, Submit and other state-changing actions.

Outputs:
- playwright/knowledge/jobbeeper_snapshot.json — machine-readable evidence for the IDE
- playwright/knowledge/jobbeeper_snapshot.md — human-readable evidence
- playwright/artifacts/*.html — rendered DOM snapshots
- playwright/artifacts/*.png — screenshots

For repeated discovery while developing:

python playwright/discover_jobbeeper.py --watch --interval 1800

The generated snapshot is the handoff between JobBeeper and the IDE:
JobBeeper -> Playwright -> evidence -> IDE -> local dashboard implementation.
