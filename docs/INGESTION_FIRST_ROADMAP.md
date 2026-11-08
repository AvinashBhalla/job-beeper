# Ingestion-First Roadmap

**Updated:** 2026-11-07  
**Priority:** P0 — reliable, fresh, broad job ingestion  
**Primary branch:** `v2-live-radar`  
**Current implementation branch:** `feat/source-observability-20261107`

**Draft PR:** [#47](https://github.com/AvinashBhalla/job-beeper/pull/47) — V2 CI #1303 passed (196 tests on Python 3.12).

## Product priority

The primary product promise is fresh, useful job discovery. Jobs should enter the portal promptly after a source makes them available, with trustworthy source identity, timestamps, deduplication and visible source health. User signup, resume parsing and Telegram delivery are downstream of reliable shared ingestion.

## Current foundation

The collector registry contains LinkedIn, Naukri, Instahyre, Greenhouse and Ashby adapters. A registry entry does not mean the source is enabled or globally searchable. Runtime enablement must be verified from the running environment's configuration and source status; never infer it from code.

The source-observability branch now adds backward-compatible run-level and request-level telemetry:

- unique run ID, run outcome and monotonic run duration;
- sanitized error type/text, HTTP status, Retry-After and full applied cooldown duration;
- physical request attempts/responses/exceptions, status-class totals, HTTP 429 count and exact status histogram;
- retry attempts for existing collector retries and aggregate HTTP request duration;
- logical search/feed page counts and Greenhouse/Ashby employer-board counts;
- `partial_rate_limited` and `partial_failed` outcomes when usable data is returned alongside failures;
- latest-run and rolling 24-hour summaries through admin-only `/api/source-status`.

Existing source-run history is preserved by additive SQLite migration; historical metrics remain NULL and are reported as unmeasured. No collector cadence, retry behavior, source enablement or notification behavior was changed. See `docs/SOURCE_LEVEL_METRICS.md` for the complete contract.

## Priority sequence

1. **P0 — Complete source observability.** Add request/page counts, status-class histograms, retries, time in cooldown, partial-board outcomes, last successful fetch and last new job. Keep telemetry sanitized and avoid logging job descriptions or credentials.
2. **P0 — Diagnose LinkedIn 429s.** Use observed request cadence, target overlap, enrichment calls and cooldown history. Reduce unnecessary pressure or prefer a permitted structured source. Never use proxy rotation, identity rotation or rate-limit evasion.
3. **P0 — Make Naukri freshness measurable.** Track relay collection time separately from original posting date, preserve last-good feed, reduce repeated full-snapshot work where safe, and measure workflow duration and main-app poll lag. Date-only posting dates must not be treated as exact timestamps.
4. **P1 — Validate source adapters individually.** Keep Instahyre disabled until its HTTP 400/schema issue is diagnosed. Canary Greenhouse/Ashby against a small, relevant employer-board allowlist. Verify public/authorized Lever and SmartRecruiters contracts before implementing them.
5. **P1 — Build a measured source catalog.** Track official endpoint/terms, employer-board requirements, authentication, pagination, stable IDs, canonical apply URL, timestamp precision, request budgets, retry policy, unique-job yield, freshness and failure rate. Report adapters separately from configured employer boards.
6. **P2 — Validate coverage and latency.** Use 24–72-hour canaries where practical. Expand toward 100 useful integrations only when unique relevant job yield, freshness and reliability justify the maintenance cost.
7. **P3 — Resume downstream product work.** Continue user preferences, resume onboarding and per-user Telegram in the separate feature branch. Keep PR #46 draft and isolated until ingestion release gates pass and promotion is explicitly approved.

## Adapter and release gates

Every adapter should have a stable source ID, canonical application URL, explicit timestamp precision, bounded pagination/request budget, timeouts, classified errors, safe backoff and isolated failure handling. The pipeline remains:

`fetch -> validate -> normalize -> canonicalize -> deduplicate -> persist -> evaluate -> expose`

Before production enablement, require permitted access, deterministic fixtures/tests, timestamp semantics, simulated 429/Retry-After coverage, a dev/canary observation window, useful unique-job yield, source-health visibility and a rollback/disable switch.

## Current next action

Review draft PR #47 and merge into `v2-live-radar` only after human review/approval. Latest request-level implementation CI #1307 (`42391947214`) passed on Python 3.12/modern Node: focused tests 32 passed and full V2 suite 199 passed. A local preview is available on isolated port 8003 with synthetic rows and all collectors disabled. After review, the next metric slice is durable last-success/last-new-job and Naukri relay freshness telemetry. The older telemetry PR #40 is closed unmerged as superseded by #47.


## 2026-11-07 — Naukri feed freshness and repeated evaluation reduction (local branch)

- Public relay JSON was inspected read-only: top-level updated_at, count, and a full jobs array. The inspected snapshot had 322 jobs. Job records have IDs/URLs and date-only posted values, but no per-job relay-observed timestamp.
- Naukri consumer changes are implemented locally on feat/source-observability-20261107: reject malformed, empty, count-mismatched, stale (>15 minutes) or implausibly future snapshots; preserve last-known-good feed metadata; persist content hash/count/age/observed time; expose freshness and unchanged-content state in admin Source Health; skip repeated matcher evaluation when stored job evaluation inputs did not change.
- The 15-minute threshold is provisional (three nominal five-minute relay intervals), not a measured SLA. Actual workflow cadence and completion timing still need verification.
- The full feed is still fetched and parsed on every poll. True per-job incremental ingestion requires publisher-side per-item observed/updated timestamps or a supported cursor/conditional-fetch contract. Never infer exact discovery time from date-only posted values.
- Validation on the isolated Python 3.10 environment: full V2 suite 205 passed. Node 12 on the VM is too old for the dashboard syntax already present; final JavaScript syntax check must be confirmed by GitHub CI.
- Commit 04c0605 is pushed to feat/source-observability-20261107 and PR #47 description is updated. PR #47 remains draft; no changes to shared dev 8001 or production 8000. GitHub V2 CI #1311 / run 42398484593 passed for implementation commit 04c0605e078fbc376fc0688def66d3d0b9c18d5a (dashboard syntax, focused 32 tests, full V2 suite 205 tests).


## 2026-11-08 — Relay scheduler verified; publisher metadata and product discovery scope

- Confirmed the relay workflow on its default branch is manual-dispatch only; the VM systemd timer dispatches every five minutes. The latest 15 successful runs took 138–164 seconds end-to-end. Run #7599 completed all 18 query/location targets and produced 325 unique jobs. Keep the 15-minute staleness ceiling provisional but evidence-based (three five-minute cycles).
- The existing relay feed has a snapshot-level updated_at, count and full jobs list. A separate relay feature branch now adds fail-closed last-good retention on any failed target and per-job relay_first_observed_at / relay_last_observed_at. The V2 consumer is being updated to use these optional fields without losing compatibility with older feed records.
- Product readiness: public JobBeeper homepage promises 11 sources, role/location/experience/company preferences, Telegram/browser/app notifications, free job browsing and application tracking. The current repository is sufficient to build further; broad private-backend reverse engineering is not a blocker. Use targeted black-box acceptance checks only for signup, preferences validation/save, job search/details/save/application tracking, notification channels and plan gating. See docs/REVERSE_ENGINEERING_SCOPE.md.

## 2026-11-08 — Current PR/release gate status

- Source observability and Naukri consumer freshness are merged into v2-live-radar (PR #47, merge `dd4d21e`), with GitHub CI run `42442324585` passing the full 207-test suite and dashboard syntax. This is not a deployment.
- Matcher benchmark methodology note is merged (PR #41, merge `4e48836`); its deterministic runner and two tests were already in the V2 branch. 4/4 scored cases pass; one remains review-only.
- Keep user preferences PR #46 draft while the preferences-save frontend/backend validation issue and per-user Telegram live E2E remain open. OAuth sign-in and resume parser were confirmed by owner UAT.
- Relay publisher PR #4 is CI-green but remains draft because merging it changes the public feed on the VM's five-minute timer. Do not merge/dispatch without explicit owner approval.
- PR #35 is the WIP V2-to-main promotion gate; main/V2 divergence and production migration still need deliberate reconciliation.
- PR #37 and relay PR #3 were closed as superseded/deferred. See `docs/PR_BRANCH_AUDIT_2026-11-08.md` for exact branch cleanup.
## 2026-11-08 — Relay publisher live verification and next LinkedIn 429 work

- Relay publisher PR #4 is merged to relay main (359df41). The VM timer triggered run 42445116273 at 04:01:49 UTC; it published a 323-job feed at 04:03:47.799 UTC. All 323 feed entries contain relay first/last observation timestamps and satisfy first <= last.
- Read-only production evidence found 27 LinkedIn HTTP 429s in 24h, with 18 reaching the former 30-minute cooldown cap. Production has LinkedIn and Naukri enabled; shared dev has LinkedIn off.
- The production DB has not yet been migrated to request-level telemetry, so the 429 counts come from log analysis, not /api/source-status.
- Code-only backoff correction is prepared on fix/linkedin-429-longer-backoff-20261108: four-hour maximum fallback and 24-hour clean-window reset; honor any larger Retry-After; no increase in request rate/volume. Focused tests 5 passed and full V2 suite 209 passed locally. Run GitHub CI before merging. No deploy.
- See docs/LINKEDIN_429_DIAGNOSTIC_2026-11-08.md for evidence, denominator limitations and the production rollout boundary.
## 2026-11-08 — Durable LinkedIn 429 breaker state

- After merging longer conservative cooldown policy (PR #48), a separate follow-up adds additive source_runs.rate_limit_detected_at and startup restore of recent LinkedIn 429 events, remaining cooldown and the 24-hour escalation streak.
- Cooldown restoration is derived only from persisted LinkedIn HTTP 429 rows, keeps retry-after and applied cooldown, and supports old rows by using finished_at if the new detection timestamp is NULL.
- Focused persistence tests: 9 passed; full V2 suite: **215 passed** locally. GitHub CI required before merge. This remains code-only, not deployed.
- First production deployment limitation: the current live source_runs table has no HTTP status history, so old 429s visible only in logs cannot be backfilled. The first deploy starts with empty DB-backed breaker history and will persist new 429s going forward.
## 2026-11-08 — LinkedIn 429 policy and durable breaker complete in V2 code

- PR #48 merged as `5b4b2fa`: 4-hour maximum fallback and 24-hour escalation reset. PR #49 merged as `596bbbe`: persist actual LinkedIn 429 detection times and restore cooldown/streak on startup. CI passed 209 and then 215 full V2 tests, respectively.
- Neither merge was deployed. Production's legacy DB has no structured history for the prior 27 log-only 429s, so the first rollout starts with empty persisted breaker state; newly recorded 429s are durable across restarts.
- Old parser branch was redundant: labelled-experience helper and regression tests already exist in V2; stale branch removed. Current LinkedIn code remains under conservative cooldown; no request-pressure or access-method change.
- Next priority: diagnose and fix the preferences-save validation/UI issue on PR #46, then validate per-user Telegram link/opt-in/delivery/opt-out E2E. Keep #46 draft until those release gates pass.

## 2026-11-08 — PR #46 local V2 integration candidate

- A local-only integration worktree `/tmp/job-radar-pr46-integration` merges `feat/user-preferences-evaluations-20261106` onto the latest `v2-live-radar` base at `a719138`. This is a rebase/conflict-resolution candidate only; it has not been pushed and does not alter the 8002 feature service or 8004 desktop QA service.
- Shared conflict in `v2/radar.py` was resolved by combining both implementations: preserve monotonic `last_seen_at`, safe source-posted timestamp handling and description-change-only global reevaluation; retain experience provenance/confidence ranking, min/max persistence and per-user evaluation refresh for only touched/new jobs.
- `dashboard/app.js` and `dashboard/index.html` auto-merged. Six conflict files were originally detected; the docs conflicts are being resolved by keeping the newer V2 handover/roadmap/audit and appending current PR #46/browser QA status. Feature-only docs and tests (OAuth, resume parser, Telegram, local browser QA) remain included from PR #46.
- Important next integration: ensure `user_notification_ledger` enqueue/delivery excludes global `notification_ledger.baseline_suppressed=1` opportunities before Lever or other first-snapshot ATS inventory is enabled for member Telegram. The user notification path must not bypass the initial-inventory baseline.
- This local candidate must pass the full V2 suite and user-preferences/OAuth/resume/Telegram focused suites. Keep PR #46 remote draft unchanged until owner desktop Browser report is returned and this candidate has full green CI.
- No push/deploy/runtime changes.

## 2026-11-08 — Lever adapter implementation

- Added Lever as the next structured ATS adapter on `feat/lever-source-adapter-20261108`. Official Lever public Postings API uses unauthenticated HTTPS GET `/v0/postings/{SITE}` with explicit `skip`/`limit`; global and EU API hosts are documented. It only exposes published public postings.
- Adapter is default-off with a version-12 migration, explicit safe site allowlist, 1800s polling, page size 100, at most 5 pages/500 postings per board per run, per-request/page/board telemetry, partial-failure retention, duplicate suppression, hosted URL validation/fallback and plain-description normalization.
- No reliable published timestamp is documented, so Lever timestamps stay unknown even if sample payloads include a createdAt field. No application endpoint is called.
- 12 focused tests passed; full V2 suite **227 passed** locally. GitHub CI pending after push. Both configs Lever off with empty allowlist; no live probe, DB write, notifications or deployment.
- Next after CI: curated one/two-board GET-only two-snapshot canary, evaluate ID stability, fresh yield and India/remote relevance. Keep source disabled until separate review.

## GitHub CI result — 2026-11-08

- Draft PR #50: https://github.com/AvinashBhalla/job-beeper/pull/50
- GitHub V2 CI run #42452809803 passed on commit `c8967ac140647409e735b7ea5be18ea7c92f133d`: Python compilation, dashboard JavaScript syntax, focused router/extractor tests (32 passed), full V2 suite (227 passed in 27.508 seconds).
- PR #50 remains draft and mergeable. No Lever board has been configured or polled; Lever remains off in both config presets.


## Next ATS candidate research — Recruitee vs SmartRecruiters — 2026-11-08

- SmartRecruiters official docs describe a public company postings endpoint `GET /v1/companies/{companyIdentifier}/postings` with `destination=PUBLIC`, `limit` (max 100) and `offset`; its authentication guide lists the public Posting API among no-auth APIs. The separate `/feed/publications` endpoint requires `X-SmartToken`; do not confuse the two contracts. See https://developers.smartrecruiters.com/reference/v1listpostings and https://developers.smartrecruiters.com/docs/authentication.
- Recruitee's public company feed has two XML URLs per subdomain: formatted `/api/feeds/offers.xml` and raw `/api/offers.xml`. The raw feed contains currently published offers only, disappears when offers are unpublished, and updates immediately. Documented fields include stable reference, title/company, full description, multiple locations, remote/hybrid/on-site flags, hosted/apply URLs, `posted` (feed-added timestamp) and `updated` (last update). See https://support.recruitee.com/en/articles/8213076-faq-api and https://docs.recruitee.com/docs/feed.
- Recruitee's new Careers Site JSON API `/api/offers` will require `X-Careers-Sites-Token` starting 2027-02-10; official docs say XML feed and jobs widget are not covered by that token requirement. Prefer the raw XML feed if/when implementing. See https://docs.recruitee.com/reference/authentication-1.
- Critical parser rule: the XML feed may contain a `<credentials>` subtree with third-party job-board secrets. Parse only an allowlist of job fields; never persist/log raw XML or the credentials subtree. Use strict fixed Recruitee host construction from a validated subdomain, bounded response size, one GET/site, no retries, and keep default-off.
- Recommendation: Recruitee is the next adapter to evaluate after Lever; its feed has stronger location/timestamp signals and remains separate from the upcoming Careers API token cutover. SmartRecruiters is also viable but company-scoped; public endpoints are distinct from its authenticated `feed/publications` API. No Recruitee or SmartRecruiters live request/adapter was implemented in this research step.

## 2026-11-08 — Lever URL and pagination hardening

- Added strict Lever posting ID validation (alphanumeric, underscore and hyphen; max 200 chars) before deriving canonical hosted URLs.
- Hosted URL acceptance now checks HTTPS, exact allowed Lever host and port, configured site path, no userinfo/query/fragment and no dot/backslash traversal segments. Untrusted or malformed URLs fall back to the canonical URL built from the configured site and validated posting ID.
- Added fixture test proving maximum pagination is exactly five full pages / 500 unique postings and never requests a sixth page. Added unsafe-ID skip and hosted path-traversal fallback tests.
- Focused Lever suite: 15 tests passed. Full V2 suite: 230 passed in 80.326 seconds. Python compilation and git diff --check passed locally.
- GitHub CI run 42452809803 passed on the initial implementation (227 tests); a fresh CI run is required after this hardening commit.
- Lever remains disabled with an empty allowlist in both config presets. No live board probe, source request, matching, notification or deployment.
## Read-only Drivetrain board canary — 2026-11-08

- Public Lever board slug: `drivetrain` (discovered from its public careers page; no credentials required). Public page search showed India/remote engineering and automation roles.
- A bounded, unauthenticated GET was sent twice to `https://api.lever.co/v0/postings/drivetrain?mode=json&limit=100&skip=0`, two seconds apart. Both requests returned HTTP 200.
- Both snapshots contained 35 postings and 35 unique IDs. 35/35 IDs overlapped between the two snapshots; union size was 35 and churn was zero over this two-second interval.
- Both snapshots contained 22 records with India location metadata. A deliberately broad title-keyword filter found 9 India-based technical postings (software/backend/frontend/engineer/developer/QA/SDET/automation). This is a smoke-test estimate, not the JobBeeper matcher result.
- Sample relevant roles included Backend Engineer, Frontend Engineer, SDET/QA Manager, SDE Automation & Quality, SRE and Software Engineer (Data Engineering). The official board page also exposes roles that may not match our target experience/role filters.
- The two-second interval only verifies response schema and short-term ID consistency; it is not a long-term ID-stability, publication-freshness or source-yield SLA.
- This was a read-only direct public API probe outside JobBeeper. It did not add a board to either config, enable Lever, run the collector, write to SQLite, evaluate matches or trigger notifications.
- Suggested canary site for future explicit opt-in: `drivetrain`. Keep the runtime source disabled until the first-snapshot notification baseline gate below is implemented and reviewed.
## First-snapshot notification baseline gate — required before enabling Lever

Lever's documented public list API does not guarantee a reliable source publication timestamp. Its first full import could contain many old-but-still-open postings, each with `discovered_at=now`; the current freshness logic can consequently regard them as new and queue eligible alerts. Do not activate the source or notifications until an initial-inventory baseline is handled explicitly.

Required behavior for any timestamp-unknown full-snapshot ATS source:
- The first successful complete snapshot must ingest and evaluate listings but mark those existing canonical opportunities as baseline inventory, not newly discovered alerts.
- The baseline marker must be durable across restarts and later scheduled refreshes, and must not falsify `discovered_at`, `source_posted_at` or `posted_precision`.
- Subsequent genuinely new source IDs on later successful snapshots must remain eligible for the normal matching/notification path.
- A partial or failed first scan must not mark an incomplete inventory as a complete baseline. The source must retry its baseline establishment after a successful complete run.
- The baseline logic must be source-scoped and must not suppress notifications for LinkedIn, Naukri or other already-operational sources.
- Regression tests must cover first complete baseline, repeated unchanged snapshot, partial first run, restart durability, and a new posting after baseline.

Until that gate exists, Lever remains default-off with an empty configured allowlist; the Drivetrain probe above is not an activation.

## 2026-11-08 — Initial-inventory notification guard implemented

- Lever has no reliable publication timestamp in its documented public postings contract. The first full board snapshot must not be treated as newly published jobs.
- Added additive notification_ledger.baseline_suppressed INTEGER NOT NULL DEFAULT 0. During each Lever source run, after job upsert and before evaluation/notification dispatch, suppress_initial_source_snapshot_alerts() marks newly created canonical opportunities as suppressed while no prior successful Lever source run exists. The marker is durable and excluded from future global notification-decision refreshes.
- Partial first runs do not establish completion. A later partial run continues baselining newly seen records. Only a successful source run completes the baseline; subsequent genuinely new Lever IDs then use normal matching and notification rules. The code does not falsify or overwrite discovered_at or source_posted_at.
- Existing canonical opportunities with an older observation from another source are not baseline-suppressed. Only Lever is in INITIAL_SNAPSHOT_BASELINE_SOURCES; Naukri, LinkedIn and Greenhouse behavior is unchanged.
- Focused tests: 4 passed. Full V2 suite after this addition: 234 passed in 81.248 seconds. Tests cover partial-run baselining, success transition/new-job alerting, existing cross-source canonical preservation, source isolation and legacy SQLite migration.
- Important integration gate: PR #46 uses a separate user_notification_ledger. That branch's member enqueue query currently does not consult the global notification_ledger.baseline_suppressed flag. Before enabling Lever for member notifications or merging the multi-user notification integration, rebase PR #46 and add the equivalent baseline filter/test to its per-user enqueue/delivery paths. The present guard protects the V2 global/admin notification ledger only.
- Lever remains disabled with empty lever_boards in both config presets; no Lever source request, notification, DB canary, app deployment or service restart was performed by this code change.

## 2026-11-08 — Recruitee live feed canary and next adapter

- A bounded direct read-only canary of `https://tether.recruitee.com/api/offers.xml` returned HTTP 200 twice; each XML response was 8,785,676 bytes with 228 offers and 228 unique IDs. All offers had `published-at` and `updated-at`; 20 offers listed India locations and a broad title filter found 18 technical candidates; 226 remote / 2 hybrid. The two snapshots 2s apart had identical ID sets and metadata fingerprints. This is only short-interval consistency, not a source SLA.
- The live Tether raw XML shape differs from the older official example. Observed shape `<hash><offers><offer>` uses `id`, `guid`, `slug`, `published-at`, `updated-at`, `description`, `requirements`, `locations`, `remote`, `hybrid`, `on-site`, `careers-url`, `careers-apply-url`; the older docs sample uses `<jobs><job>` with `reference`, `posted`, `updated`, `description_requirements`. A future adapter must support both.
- The canary currently had no `<credentials>` node, but official Recruitee docs explicitly state credentials for partner job boards may appear in XML. Any parser must explicitly skip `<credentials>`, reject DTD/entities, cap response size, only parse allowlisted fields, and never log/persist raw XML.
- Official feed URLs: raw `/api/offers.xml`, formatted `/api/feeds/offers.xml`, JSON `/api/offers`. Careers Site JSON API token is required from 2027-02-10; official docs exclude XML feed and widget from that token change. Use official docs in `docs/RECRUITEE_SOURCE_RESEARCH_2026-11-08.md`.
- No Recruitee adapter or app source request was made. Recommendation: Recruitee is next candidate after Lever review; use Tether as test fixture with both schemas and credentials-skip coverage. Keep source off until code review and a no-notification first-snapshot policy is validated.

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


## Candidate QA preview — 2026-11-08

- An isolated candidate server is running at remote loopback 127.0.0.1:8005 (Termalin job 3o9e1mx8d2). Browser tunnel: ssh -N -L 18005:127.0.0.1:8005 ubuntu@130.210.27.197; URL: http://localhost:18005/dashboard/.
- This preview uses a fresh synthetic database /tmp/job-radar-pr46-fixed-qa/jobs.db, not a copy of production, shared dev or the old port-8004 database. It has one admin, one member, two synthetic jobs and one clearly synthetic Naukri source-run row.
- All six collector flags (LinkedIn, Naukri, Instahyre, Greenhouse, Ashby, Lever) are false; notifications are false; Telegram, Google OAuth, Gemini and other LLM credentials are blank. The environment binds only to remote loopback.
- Temporary test accounts shared in chat: qa-member@local.test and qa-admin@local.test. Passwords are not written in repository files.
- HTTP smoke verification: /health, /dashboard/, dashboard JS and CSS returned 200. Member login/feed/daily-summary returned 200; member /api/source-status/summary, /api/source-status and /api/latency-summary returned 403. Admin login and all three source-health GETs returned 200. No outbound source requests or Telegram sends were made.
- The original port-8004 feature process still uses /tmp/job-radar-user-preferences and remains unchanged. Do not use it for post-fix verification. Ports 8000/8001 remain untouched.
- Next: run Prompt 1 in docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md against port 18005. It must verify real 390×844/375×812/320×740 rendering and direct #sources member navigation, then admin access.
