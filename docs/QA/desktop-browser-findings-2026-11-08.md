# Desktop Browser QA findings — 2026-11-08

**Environment:** isolated PR #46 feature instance, browser URL `http://localhost:18004/dashboard/` (remote loopback port 8004).
**Tester result:** Failed — two confirmed defects (one medium authorization issue, one low mobile layout issue). Desktop did not modify source code or server configuration.
**Evidence caveat:** Desktop could not save the report because its workspace lacked `.git`. This repository copy is based on the complete report supplied in the conversation.

## Confirmed defects

### QA-001 — Member can access Source Health telemetry
- Severity: Medium; reproduced consistently (100%).
- Member opened `/#sources` through desktop/mobile navigation and saw collector names, enabled/disabled state, job-seen/new-job counts, last-success values and diagnostics.
- Expected: source health and operational source APIs are administrator-only.
- Root cause in the pre-fix PR #46 branch: member navigation and section were visible; direct hash navigation was not blocked; `loadSourceStatusTelemetry()` called `/source-status/summary` for members; and that endpoint accepted any authenticated user. The reduced payload still revealed operational metadata.
- Candidate fix in local integration worktree: admin-only desktop/mobile navigation and section; redirect member `#sources` navigation to Jobs; short-circuit member telemetry loading; protect `/api/source-status/summary` with `require_admin`.
- Automated verification: member receives 403 from `/api/source-status/summary`, `/api/source-status` and `/api/latency-summary`; admin receives 200. Route dependency and dashboard guard tests pass. Browser re-verification is still pending.

### QA-002 — Mobile header statistics clipped at 390 × 844
- Severity: Low; reproduced consistently (100%).
- Header ribbon clipped the alerts metric at viewport 390 × 844.
- Candidate fix: responsive header/ribbon wrapping at widths up to 560px; three-column `minmax(0,1fr)` metrics grid; hide dividers; allow labels/values to wrap and use `overflow-wrap:anywhere`.
- Automated verification: CSS contract test passes. Actual browser screenshots at 390×844 and 320px remain pending.

## Scenarios passed in the supplied Desktop run

- Unauthenticated dashboard displayed sign-in gate; member and admin login succeeded.
- Role, location and skills onboarding worked. Enter/comma tag creation, pending-tag Save, duplicate suppression and preferences persistence after reload worked.
- Personalized feed showed role/location, score and experience provenance.
- Invalid min/max range produced inline/toast validation.
- Harmless HTML canaries in search/tags rendered literally with no script execution, DOM breakage or console errors.
- Logout returned to sign-in and remained logged out after reload.
- No session token appeared in normal UI; Account showed HttpOnly cookie session description.

## Not covered by the supplied browser run

- CSRF forged cross-origin requests and missing/invalid CSRF token mutation tests.
- IDOR/tenant identifier tampering and cross-user access attempts.
- Exact preference-save payload capture.
- SQL-like input, sorting/filter matrix, pagination boundaries, keyboard-only tag removal and expired-session handling.
- OAuth, Telegram delivery, uploads and external application flows.

## Candidate regression work after the report

- Source Health UI now hides the navigation and workspace from members, blocks direct member hash navigation and skips member telemetry polling.
- Source Health summary API now requires admin; API tests cover member 403/admin 200.
- Per-user Telegram baseline protection now excludes initial-inventory jobs from enqueue, claim and final send validation. Previously queued/failed rows for newly marked baseline jobs are cancelled.
- Mobile telemetry header now has a narrow-screen wrapping grid.
- Full V2 suite: **333 tests passed** in **174.474 seconds**. Python compileall/py_compile and `git diff --check` passed.
- VM Node is v12.22.9 and cannot parse the app's optional-chaining/nullish syntax. GitHub CI must verify dashboard JS with modern Node.

## Deployment and branch boundary

- Fixes are in pushed branch `integration/pr46-v2-rebase-20261108` at `676dfaf`; not deployed. An isolated synthetic QA app runs on loopback 8005 / tunnel 18005; port 8004 is still the old pre-fix branch.
- Running port 8004 still uses `/tmp/job-radar-user-preferences` (original PR #46 branch). It was not restarted or changed.
- Production 8000 and shared development 8001 are untouched. No source enablement, collection schedule, credentials or notification config changed.
- Next: run Prompt 1 in `docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md` against the candidate build, then Prompt 3. Keep PR #46 draft until browser and GitHub CI verification are green.

## Candidate QA preview — 2026-11-08

- An isolated candidate server is running at remote loopback 127.0.0.1:8005 (Termalin job 3o9e1mx8d2). Browser tunnel: ssh -N -L 18005:127.0.0.1:8005 ubuntu@130.210.27.197; URL: http://localhost:18005/dashboard/.
- This preview uses a fresh synthetic database /tmp/job-radar-pr46-fixed-qa/jobs.db, not a copy of production, shared dev or the old port-8004 database. It has one admin, one member, two synthetic jobs and one clearly synthetic Naukri source-run row.
- All six collector flags (LinkedIn, Naukri, Instahyre, Greenhouse, Ashby, Lever) are false; notifications are false; Telegram, Google OAuth, Gemini and other LLM credentials are blank. The environment binds only to remote loopback.
- Temporary test accounts shared in chat: qa-member@local.test and qa-admin@local.test. Passwords are not written in repository files.
- HTTP smoke verification: /health, /dashboard/, dashboard JS and CSS returned 200. Member login/feed/daily-summary returned 200; member /api/source-status/summary, /api/source-status and /api/latency-summary returned 403. Admin login and all three source-health GETs returned 200. No outbound source requests or Telegram sends were made.
- The original port-8004 feature process still uses /tmp/job-radar-user-preferences and remains unchanged. Do not use it for post-fix verification. Ports 8000/8001 remain untouched.
- Next: run Prompt 1 in docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md against port 18005. It must verify real 390×844/375×812/320×740 rendering and direct #sources member navigation, then admin access.
