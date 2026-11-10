# JobBeeper Dev — ChatGPT Desktop QA runbook (2026-11-10)

## Target

Open the private Termalin site from the owner's account:

- **Dev dashboard:** https://termal.in/account#open-site=776b26fb-86fa-4ac2-9762-4af7dd5fe33f
- App target: `http://127.0.0.1:8001/dashboard/`
- Expected image: `job-radar-dev-multitenant:18f219d`
- Release merge: `18f219dfab4ad6f2c5ad9b9704da5d3a220f7d37`

Do not use the candidate QA port 18011, connector-QA port 8010, old browser-QA port 8006, or production port 8000 for this run.

## Instructions for the owner

1. Open the Dev dashboard link above in a browser session signed in to Termalin.
2. Sign in to JobBeeper using the existing dev admin account. Enter the password yourself in the browser; do not put it in the ChatGPT prompt or report.
3. Open ChatGPT Desktop, start a Work session with browser/computer interaction enabled, and paste the prompt below.
4. Keep the test read-only. Review the report and screenshot files before sharing them back in this chat.

## Ready-to-paste ChatGPT Desktop prompt

You are acting as a QA engineer testing the **JobBeeper Dev environment only**. Use the browser already opened to the private JobBeeper Dev dashboard. If the login screen is present, ask me to enter credentials directly in the browser. Never request, display, copy, store, or include passwords, session cookies, CSRF tokens, API tokens, or other secrets in your notes or screenshots.

### Release context

This Dev environment is running the merged evaluation-fingerprint fix:
- Image: `job-radar-dev-multitenant:18f219d`
- Merge commit: `18f219dfab4ad6f2c5ad9b9704da5d3a220f7d37`
- PR: https://github.com/AvinashBhalla/job-beeper/pull/69
- Goal: per-board ATS polling must not invalidate all persisted job evaluations. The first migration has already completed; the current DB reports zero evaluation fingerprint mismatches.

### Safety boundaries — mandatory

This is a **read-only QA run**. Do not:
- Change any user or admin preferences, source settings, board settings, polling cadence, concurrency, rate limits, or notification settings.
- Activate, deactivate, delete, add, edit, or verify ATS boards.
- Trigger a manual scan, poll, refresh job evaluation, notification send, Telegram test, email, or other external action.
- Create, disable, or delete accounts.
- Restart containers or services, call write APIs, or edit data.
- Visit or test Production, connector QA, candidate QA, or any non-Dev environment.

You may navigate, reload, filter, search, open and close read-only panels, inspect the visible dashboard, read browser console/network status, and take screenshots. Do not expose secrets in screenshots. If a test would require a state-changing action, mark it BLOCKED and explain why.

### Test plan

1. **Open and authenticate**
   - Confirm the Termalin Dev link opens the JobBeeper Dev login/dashboard.
   - Use the existing admin account after I enter credentials.
   - Confirm the session remains active after a normal page reload.

2. **Dashboard and live feed**
   - Confirm dashboard renders without a blank page, broken layout, blocking error, or unexpected redirect.
   - Confirm jobs are visible and source labels/board names are plausible.
   - Check browser console for uncaught errors and warnings. Record exact messages, but redact tokens, cookies, and personal details.

3. **Per-board scheduler / source health**
   - Locate the admin scheduler/source-health view using the UI.
   - Expected current schedule inventory: **10 active boards across 7 providers and 7 API host keys**:
     - Ashby: OpenAI, PostHog
     - Darwinbox: Arvind
     - Greenhouse: Coinbase, Graviton Research Capital, Zocdoc
     - Keka: Bridgestone
     - SmartRecruiters: Bosch Group
     - Workable: Hugging Face
     - Workday: NVIDIA
   - Confirm the 10 board entries are distinct, visible, and report the latest known state as successful. If a row shows an in-progress state, wait/read it without triggering anything; report the state as observed.
   - Confirm board names, provider names and status labels remain after a hard reload.
   - Do not infer that a board has just completed a post-release poll solely because its last status says success; record the displayed last-run timestamp.

4. **Fingerprint-related behavior**
   - If the UI exposes evaluation/source metrics, inspect them read-only.
   - Verify no repeated global re-evaluation is visibly indicated on each board poll.
   - Do not manually trigger a refresh to test this.
   - The server-side release gate already confirmed: 10,838 jobs, 10,838 evaluations, zero fingerprint mismatches, SQLite integrity `ok`.
   - These backend values are context only; do not claim to have re-queried the database from the browser.

5. **Authorization boundaries (only if already available without changing accounts)**
   - Anonymous direct request to `/api/discovery/scheduler/status` should return HTTP 401.
   - Admin scheduler API access should be allowed after login.
   - If an existing member test account is available and I can enter its credentials directly, verify member scheduler API access returns HTTP 403 and admin-only Source Health is not visible to the member.
   - Do not create or disable a test member. If member credentials are unavailable, mark member-role tests BLOCKED rather than inventing a result.

6. **Responsive checks**
   - Test these viewport sizes: 1440×900, 1024×768, 768×1024, 390×844, and 320×740.
   - At each size, check horizontal overflow, clipped headers, hidden actions, overlapping controls, navigation access, and whether the bottom of the page is reachable.
   - At mobile widths, check the scheduler/source list remains readable and the primary controls are reachable. Do not change CSS or browser zoom as a substitute for responsive layout.

7. **Reload / persistence**
   - Hard reload the dashboard and scheduler page.
   - Confirm the same 10 board entries remain, no duplicate board rows appear, and the admin session behaves consistently.
   - Do not change settings to test persistence.

### Evidence and report requirements

Create a concise Markdown report named:

`JOBBEEPER_DEV_RELEASE_QA_2026-11-10.md`

Save it in the current QA workspace or project artifact directory. Also save real PNG screenshots (not placeholders) under:

`artifacts/dev-qa-2026-11-10/`

Capture at minimum:
- Admin dashboard after successful login
- Scheduler/source-health view showing the 10 board inventory
- Scheduler/source-health view after hard reload
- One desktop viewport screenshot
- One mobile viewport screenshot (390×844)
- 320×740 screenshot if the viewport test can be completed

Report:
- Environment and URL (Dev only)
- Browser and viewport sizes
- Test case table with PASS / FAIL / BLOCKED / NOT TESTED
- Observed board counts and visible statuses
- Reload/persistence result
- Console errors/warnings (redacted)
- Screenshots with exact file paths
- Any steps that could not be performed and why
- Final recommendation: PASS, PASS WITH ISSUES, or BLOCKED

Do not mark a test PASS without a visible observation or screenshot. Do not turn an inaccessible API, missing account, or unavailable browser capability into a guessed PASS. Do not modify the application. At the end, give me the full report and the exact paths of every screenshot created.
