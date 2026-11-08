# Product Reverse-Engineering Plan

**Status:** Discovery and evidence-gathering phase  
**Updated:** 2026-11-05  
**Working repository:** [AvinashBhalla/job-beeper](https://github.com/AvinashBhalla/job-beeper)  
**Active branch:** `v2-live-radar`

## Goal

Build a personal job-intelligence system that continuously discovers jobs from a broad set of permitted job-board, ATS and employer-career sources; normalizes and deduplicates the results; evaluates them against a personal candidate profile; and delivers fresh matches through Telegram and a dashboard. A separate referral-intelligence subsystem should identify relevant people using authorized sources, enrich professional contact details where permitted, prepare personalized messages and manage human-approved outreach.

The future hiring-post stream (recruiter/employee posts that announce openings) is explicitly later scope. Do not mix it into the first job-ingestion release.

## Research targets

1. **JobBeeper:** observable product pages, filters, job cards, freshness/discovery labels, company pages, source coverage, notification behavior, frontend bundles, and browser-visible network activity.
2. **Uplers HAPPPY:** job input, company/team identification, people discovery, contact enrichment, relevance ranking, personalization, Gmail consent/sending, LinkedIn permissions, review controls and follow-up tracking.
3. **Existing Job Radar V2:** code, tests, branch state, runtime configuration, source health, timestamps, matching, notification ledger, deployment and rollback path.
4. **REA:** use [morluto/rea](https://github.com/morluto/rea) for passive CDP website observation and offline HAR inspection. Do not treat it as a private-backend source extractor or an unrestricted browser automation tool.

## Initial repository findings (2026-11-05)

- Inspected branch head: `ef73b3c8bee77b14c4b0ebd7ac319ab7cf94fc7a` on `v2-live-radar`.
- Latest V2 CI run on the exact head: [#40651863587](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651863587), conclusion `success` (2026-10-28). This does not establish VM deployment.
- Older `main` head: `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; continue V2 work from `v2-live-radar`.
- Collectors currently registered: LinkedIn, Naukri, Instahyre, Greenhouse and Ashby.
- Tracked `v2/config.json`: LinkedIn and Naukri enabled; Instahyre, Greenhouse and Ashby disabled. Tracked development config: Naukri only, notifications disabled. Runtime `/data/config.json` can override tracked production configuration.
- LinkedIn has 16 tracked fast-lane query/location targets (4 queries × 4 locations) and scans up to 2 targets per 180-second cycle. Under uninterrupted success, a complete first-page rotation is nominally 24 minutes. This is a scheduling estimate, not a measured live p50/p90.
- LinkedIn requests are globally paced at 4 seconds, use a 25-second request timeout, and honor HTTP 429 with global escalating backoff (300-second base, 1,800-second cap, Retry-After respected).
- Observability gap: `/api/source-status`, `/api/latency-summary` and `/api/dedupe-candidates` currently omit Ashby although it is registered as a collector. Confirm and test the intended behavior before fixing.
- The tracked `source_state.json` is an old snapshot, not live runtime health.
- No source was triggered, no code/config was changed, and no Oracle operation was performed during this audit.

## Evidence standards

For each product claim, record:
- **Observed:** directly seen in the product, browser, a publicly accessible endpoint or an authorized account flow.
- **Inferred:** a plausible explanation, clearly labeled and tied to supporting evidence.
- **Unknown:** private implementation details, unavailable workflows or unverified claims.

Never claim to know a vendor's private backend implementation based only on its UI or public marketing. Reconstruct observable product behavior using independent implementation choices.

## REA and browser setup

1. Check Node.js and npm versions. REA currently requires Node 22.23.4+, 24.22.1+ or 26.12.1+.
2. Run `npx rea-agents@latest setup`; review the exact configuration plan and approve only the intended coding agent.
3. Restart that agent after setup.
4. Start a separate Chrome profile with a debugging endpoint bound only to `127.0.0.1`; do not expose CDP to LAN or public internet.
5. Use REA's passive browser tools to capture page structure, resources, scripts, console/network metadata and screenshots.
6. Use Chrome DevTools to save HAR with content when needed; inspect offline with REA.
7. Redact cookies, authorization headers, bearer tokens, secrets, inbox contents, personal contact details and other sensitive payloads before sharing captures.
8. Stop the dedicated browser after the investigation.

## Oracle runtime audit — read-only gate

Before any deployment or code change, establish:
- exact branch, commit and git working-tree state of production and development checkouts;
- container name, image/revision and compose project;
- mounted SQLite volume and effective runtime configuration without printing secrets;
- source enabled flags, last run/success, request counts, error classes, 429/cooldown state and per-source job yield;
- source posting timestamp precision, discovered timestamps and measured latency;
- match/evaluation/notification-ledger/Telegram timestamps.

Do not run job-processing endpoints simply to generate sample data. Do not print environment variables, API keys, config tokens, Telegram credentials or session material. Preserve local uncommitted files and volumes. No restart or pull until branch/runtime state is reviewed.

## Planned deliverables

1. JobBeeper evidence report and behavior map.
2. HAPPPY evidence report and permission/integration map.
3. Existing-system audit and measured latency diagnosis.
4. Source/provider matrix (coverage, timestamp quality, permissions, freshness, API limits, cost and terms).
5. Master architecture and separate PRDs for source ingestion, matching, notifications, referral intelligence and later hiring-post discovery.
6. Test and rollout plan with explicit freshness, dedupe, alert consistency, source isolation and rollback gates.

## Explicit non-goals for the initial phase

- No private SaaS backend extraction or authentication bypass.
- No LinkedIn proxy/account rotation, CAPTCHA bypass or policy-evading automation.
- No automatic LinkedIn connection requests or messages; use official authorized integrations if available, otherwise require human action.
- No expensive provider subscription until a controlled sample demonstrates added coverage, freshness or accuracy.
- No ground-up rewrite before the existing V2 audit is complete.

## 2026-11-06 — Product priority reset: multi-user first, referral intelligence after beta

The next product milestone is now **multi-user support**, not additional source expansion. The previous single-user/personal-watcher assumption is superseded for forward planning.

- Shared source collection and canonical job data should serve all users once.
- Candidate profiles/preferences, evaluations, saved/applied state, notification decisions and Telegram destinations must be user-scoped.
- Implement admin/user roles and real login/session security before inviting external beta users.
- First Telegram design should use one JobBeeper-owned bot and independently linked user chat IDs through a one-time deep link; BYO bot tokens are optional future scope.
- Use the new `docs/MULTI_USER_AND_REFERRAL_ROADMAP.md` as the detailed design and acceptance source.

HAPPPY-like referral intelligence remains a later phase, but is now explicitly documented as a product workflow: application tracking, relevant contact discovery from authorized/public sources, explainable contact ranking, user-approved referral/follow-up drafts, user-authorized email integration, draft creation, follow-up reminders and response tracking. Keep email sending human-approved in the first release. Do not automate LinkedIn connection requests/messages or evade platform controls.

The delivery sequence is: current search/description release -> multi-user identity/RBAC -> per-user preferences/evaluations -> per-user Telegram -> small beta/feedback -> application tracker -> referral intelligence. Hiring-post discovery remains later.


## 2026-11-07 — Priority reset: ingestion first, JobBeeper browser evidence next

The previous 2026-11-06 multi-user-first sequence is superseded. The primary product promise is now fresh, broad, reliable job ingestion into the portal. See `docs/INGESTION_FIRST_ROADMAP.md` for the verified runtime audit, current source metrics, JobBeeper browser evidence plan, adapter architecture, source catalog and acceptance gates.

- P0: audit/fix ingestion freshness, source coverage, request budgets, 429 behavior, timestamp quality and per-source observability.
- P1: inspect JobBeeper's observable authenticated UI/network behavior using a sanitized HAR from the user's own browser session. Do not infer private backend implementation or bypass access controls.
- P2: build a measured source/provider catalog and add public/authorized adapters incrementally toward 100 useful sources.
- P3: validate 24–72 hour canaries, useful unique-job yield and freshness.
- P4: continue multi-user signup/preferences, resume parsing and Telegram work in parallel on isolated PR #46, per the owner's 2026-11-07 update. Referral intelligence remains later scope. Do not merge or promote the feature branch while ingestion acceptance gates remain open.

Verified 2026-11-07: current feature code has five collectors (LinkedIn, Naukri, Instahyre, Greenhouse, Ashby); production has only LinkedIn and Naukri enabled; shared dev has only Naukri enabled. Production logged 36 LinkedIn HTTP 429 events in the previous 24 hours. In the same period, production recorded 313 new LinkedIn rows and 173 new Naukri rows; Naukri's relay is polled every five minutes and its current feed uses date-level posting timestamps. These findings mean we are not yet at 100-source coverage or reliably minute-level discovery. All runtime inspection was read-only.


## 2026-11-07 — Owner-requested parallel feature development

The owner clarified that ingestion-first product priorities do not require serializing engineering work. Continue the authentication/Google signup, resume parser and per-user Telegram work on the existing isolated feature branch while the owner performs the JobBeeper `@Chrome`/CDP network investigation. Earlier instructions in this document to pause all multi-user/resume/Telegram code work are superseded.

- Feature branch: `feat/user-preferences-evaluations-20261106`; PR #46 remains draft.
- Latest code commit at this checkpoint: `51db2f9`; GitHub V2 CI run `42370884022` passed.
- Full isolated V2 suite: **272 passed, 1 skipped**; focused tests: Google OAuth 15/15, resume parser 15/15, per-user notifications 12/12.
- Isolated feature runtime is rebuilt and healthy on loopback port 8002. Shared dev and production remain untouched.
- Dedicated dev Telegram bot and public HTTPS webhook are pending. Do not use production bot `Qdhorvbot` for testing.
- The JobBeeper sanitized HAR/report will be reviewed separately; ingestion engineering remains active and is not blocked by this feature track.


## 2026-11-07 — Authenticated JobBeeper network investigation completed

- Sanitized report added: docs/JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md.
- Direct observations: page-number feed pagination (page, per_page=20), server-side keyword search, separate metadata/tracker detail GETs, a view-marking POST, visible source labels and experience-provenance labels.
- Ten minutes of idle observation on an expired-subscription account showed no feed-related network events. It does not establish active-account refresh cadence.
- Unknowns remain: API response schemas, exact filter parameters beyond keyword search, timestamp semantics, longer polling/push behavior and private ingestion architecture.
- Local comparison is recorded in docs/INGESTION_FIRST_ROADMAP.md. The first product changes are to bound dashboard polling, plan server-side pagination and close the experience-provenance gap; source expansion remains governed by the ingestion acceptance gates.
- Continue only with the sanitized evidence. Do not retain/replay authenticated request bodies, cookies, authorization headers or account/session material.


## 2026-11-07 — Second-round JobBeeper evidence and local feed parity work

The second-round sanitized report is now in docs/JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md. It confirms search, numeric page, per_page=20, status=matched, sort_by=created_at and sort_order=desc. Search reset page=1 in the tested browser action. Other filter dropdown mappings, response schemas, stable page-ID overlap, exact experience provenance fields, repeated detail-view behavior, save/application requests, and active/hidden refresh behavior remain unknown. Ten idle one-minute windows again showed no refresh traffic, but the account remained expired with a six-hour feed-delay message, so no inference about an active subscription is justified.

Our own isolated implementation now supports the observed list query vocabulary at GET /api/jobs while retaining legacy aliases. It applies its own search/source/score/age/alertability/remote filters in SQL before pagination; those local filter names are not claims about JobBeeper. The dashboard requests 20 jobs per page and provides numeric navigation. Our total/page/has-next response fields are locally designed because JobBeeper's response body was intentionally not retained.

Experience values now carry a provenance category and qualitative evidence-strength grade in our data model and dashboard. The grade is rule-based and not a calibrated probability. Do not claim that our classifier reproduces JobBeeper's private implementation; its underlying provenance fields remain unknown.

## 2026-11-08 — Desktop QA findings, local fixes and remaining verification

- User supplied a complete Desktop browser report: overall **Failed**, with QA-001 medium authorization exposure (member opens Source Health and sees source names/status/counts/last-success/diagnostics) and QA-002 low mobile header clipping at 390×844. All other tested scenarios are recorded in `docs/QA/desktop-browser-findings-2026-11-08.md`.
- Desktop could not save its report because its workspace lacked `.git`; a canonical copy and next prompts are now in this repository. The Desktop connection interruption occurred while its answer was being generated; local Git worktrees and QA server remained intact.
- Local integration candidate `/tmp/job-radar-pr46-integration`, branch `integration/pr46-v2-rebase-20261108`, already contained UI-only source-health hiding/route guard and mobile responsive CSS changes. We tightened the server boundary: `/api/source-status/summary` now uses `require_admin`, matching `/api/source-status` and `/api/latency-summary`.
- Candidate UI changes: admin-only desktop/mobile navigation and section; direct member `#sources` routes redirect to Jobs; `loadSourceStatusTelemetry()` returns immediately for members and never calls source-status APIs; mobile telemetry row wraps into 3 columns under 560px with `minmax(0,1fr)` and `overflow-wrap:anywhere`.
- Per-user first-inventory safety was checked during the merge: `user_notifications` excludes `jobs.source_initial_baseline` in enqueue and final send validation. We additionally exclude it from claim selection and explicitly cancel stale queued/failed member notification rows after a job becomes initial baseline.
- Regression tests updated: member `/api/source-status/summary`, `/api/source-status`, `/api/latency-summary` return 403; admin source summary and full status return 200; route dependency contract now classifies source summary as admin-only; dashboard markup/route/telemetry guards and mobile grid have contract tests.
- Focused auth/API/dashboard tests: **13 passed**. User notification tests: **14 passed**. Full V2 unittest discovery: **333 passed** in **174.474 seconds**. Python py_compile/compileall and `git diff --check` passed.
- Local VM Node is v12.22.9 and cannot parse the dashboard's optional-chaining/nullish syntax. The local `node --check` attempt is not a project failure; use GitHub CI's modern Node runtime for the JS syntax check.
- IMPORTANT: the local candidate has not been pushed or deployed. Port 8004 still runs `/tmp/job-radar-user-preferences` (pre-fix PR #46 tree). Do not treat the old 18004 browser result as verification of the candidate. Rebuild/start the isolated candidate on a fresh loopback port (recommended 8005 / localhost tunnel 18005) with copied DB and all collectors/Telegram/OAuth/LLM disabled, then run Prompt 1.
- Public reference research is summarized in `docs/PRODUCT_REVERSE_ENGINEERING_2026-11-08.md`; detailed Desktop tasks are in `docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md`. The public JobBeeper site mentions role/location/experience/company preferences, remote jobs, blocked companies, pause alerts, free browsing/application tracking, paid Telegram/browser/app alerts, and subscriber-first/public sharing. These are research leads, not verified account features; Prompt 2 should verify them without signing up or paying.
- Remaining gates: browser-verify QA-001/QA-002 on the candidate; run security/tenant-isolation Prompt 3 (CSRF, IDOR, expiry, exact preference payload, keyboard/pagination/filter matrix); update docs with each Desktop artifact; then run candidate GitHub CI. Keep PR #46 and #50 open/draft until integration/review decisions are made. No merge, port 8004 restart, shared-dev or production deploy is authorized.
