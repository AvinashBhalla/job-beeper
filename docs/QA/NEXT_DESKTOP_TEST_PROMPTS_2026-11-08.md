# Next Desktop prompts — 2026-11-08

Run these as separate Desktop tasks. Attach one Markdown result per task. Do not combine them into one long session.

## Prompt 1 — Verify the two QA fixes on the candidate build

```text
You are doing controlled browser regression testing for the JobBeeper repository.

Read docs/QA/desktop-browser-findings-2026-11-08.md and the latest sections of docs/JOB_RADAR_HANDOVER.md and docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md.

Target only the isolated candidate QA app at http://localhost:18005/dashboard/. Before testing, I will keep this SSH tunnel open: ssh -N -L 18005:127.0.0.1:8005 ubuntu@130.210.27.197. Use the temporary qa-member and qa-admin credentials I provide in chat; do not include passwords in your report. Do not use ports 8000, 8001, 8002 or 18004. Do not edit code/config/database or restart any service. Do not send Telegram messages, OAuth requests, applications or source collector requests.

QA-001 member test:
1. Sign in as a normal member.
2. Verify Source Health is absent from desktop sidebar and mobile navigation.
3. Navigate directly to #sources, including after reload and browser back/forward. It must redirect to Jobs and never flash Source Health.
4. Inspect Network after login and during the refresh interval. Member sessions must not call /api/source-status, /api/source-status/summary or /api/latency-summary.
5. Using the existing member session, issue read-only GETs to those endpoints. Expected: 403. Do not copy or report cookie values.
6. Sign in as administrator. Source Health must appear on desktop and mobile, and the three APIs must return 200.

QA-002 mobile test:
1. Test member and admin viewports 390x844, 375x812 and 320x740.
2. Capture screenshots. Today/discovered, matched and alerted metrics must be fully visible, readable and non-overlapping.
3. Confirm no horizontal page overflow, controls clipped or content hidden behind the mobile bottom navigation.
4. Verify 1280x800 remains visually correct.

Do not fix defects. Record actual observations. Mark incomplete work BLOCKED, never PASS. Attach desktop-qa-fix-verification-2026-11-08.md with build identity, routes, viewport, PASS/FAIL/BLOCKED by test, response codes, network requests, screenshots (redacted), console errors and reproducibility. No secrets.
```

## Prompt 2 — Reverse-engineer the public JobBeeper product

```text
You are researching the publicly visible reference product at https://jobbeeper.com/ to inform our JobBeeper clone.

Read docs/PRODUCT_REVERSE_ENGINEERING_PLAN.md, docs/JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md, docs/JOBBEEPER_REFERENCE.md and docs/INGESTION_FIRST_ROADMAP.md.

Use normal public browser navigation only. Do not register, sign in, pay, use private APIs, bypass access controls, scrape the full catalogue or submit applications. Do not assume landing-page claims are verified functionality.

Inspect one representative example of: landing page/navigation; browse/search by role/company/location; public job detail; pricing/plan comparison/trial/renewal wording; account and Google sign-in entry points without completing signup; privacy/legal pages; app download/store links; source coverage claims; public/private job sharing claims.

For each feature, record URL, click path, exact visible labels/fields, expected action, observed behavior, screenshot, and evidence class VERIFIED/OBSERVED/INFERRED/UNKNOWN. Distinguish marketing claims from observed functionality. Record unavailable pages as UNKNOWN.

Specifically investigate company include/exclude, remote/work mode filters, pause/resume alerts, resume upload or grading, job tracker/notes/follow-ups, saved searches, Telegram/browser/app alerts, public/private release windows, source freshness, browse routes and pagination. Do not mark a feature present unless observed.

Compare the reference with our current repository and prioritize gaps P0/P1/P2. Include a route map, UI field inventory, workflow diagrams, feature matrix and next tests. Do not change code or runtime. Attach jobbeeper-public-product-reverse-engineering-2026-11-08.md.
```

## Prompt 3 — Rigorous security and tenant-isolation regression

```text
Run a controlled security regression against the isolated JobBeeper candidate QA app only. Do not target 8000 or 8001, generate load, or trigger source collectors. Do not change code/config. Use only synthetic member/admin accounts and data supplied for this QA run.

Read docs/QA/desktop-browser-findings-2026-11-08.md and the latest QA-fix verification report.

A. Authorization/tenant isolation:
- Direct navigation and direct GETs to admin pages/APIs; ensure Source Health is admin-only regardless of hidden UI.
- On safe read-only requests only, attempt user_id/owner_id/role parameter tampering where such parameters exist.
- Try another member's known job detail, preferences, daily summary, applied state, resume metadata, Telegram state and notification state only where the UI/API exposes an identifier. Expected: own data only or 403/404.

B. CSRF/session:
- Missing, invalid and other-session CSRF tokens against preference, applied-state, Telegram settings/link and other state-changing requests; expected 403 with no state change.
- Verify logout revokes old session, replay fails, expired/disabled-account session is rejected, and role escalation through client state or payload is impossible.

C. Input/output:
- Use inert HTML/XSS test strings in tags, search, job detail and other text fields. Monitor dialogs, DOM, network and console; no payload should execute or create unsafe markup.
- Use SQL-like strings in search/filter/preference fields and verify literal handling and no query manipulation.
- Check escaping in title/company/location/description/source/reasons/account fields.

D. Preferences/feed:
- Capture exact save request body with secrets redacted; verify pending tags appear once.
- Test missing required role/location, min/max range, whitespace, duplicate tags, and Save after reload.
- Test sort/filter combinations, pages 1/2/last/beyond-last, malformed/negative pagination, no results and refresh.
- Test keyboard-only tag add/remove, pending-tag Save, focus and accessible labels.

Do not use destructive payloads, external hosts, credential guessing, brute force, application submission or data exfiltration. Stop if a test could affect a real user/external system.

Attach jobbeeper-security-regression-2026-11-08.md with test IDs, setup, exact route/action, expected/actual, evidence, severity, reproducibility, data impact and remediation. Untested means UNKNOWN, not PASS. Do not alter the app.
```
## Additional Prompt 3 check — canonical baseline notification suppression

During engineering review, a cross-source edge case was found: the Lever initial-inventory marker is canonical-opportunity-level, while the member notification queue also uses a per-job baseline flag. The code has now been patched and has four regression tests.

On the isolated candidate QA environment only, verify by read-only UI/telemetry inspection where exposed that no first-inventory/baseline records are queued for member Telegram notifications. Do not configure Telegram or trigger a real send. If internal queue visibility is not available in the UI, mark this check BLOCKED and rely on automated tests; do not probe undocumented destructive endpoints.

Automated coverage now includes: canonical marker exclusion at enqueue; cancellation of an already queued row at claim time; final send-time revalidation; and per-job baseline exclusion. Full V2 suite currently passes 336 tests.