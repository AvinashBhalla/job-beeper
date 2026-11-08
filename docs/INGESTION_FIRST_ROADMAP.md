# Ingestion-First Product Roadmap

**Updated:** 2026-11-07  
**Priority:** P0 — reliable, fresh, broad job ingestion  
**Repository:** `AvinashBhalla/job-beeper`  
**Current working branch for this documentation checkpoint:** `feat/user-preferences-evaluations-20261106`  
**Production:** `v2-radar-1`, port 8000 (read-only audit only)  
**Shared dev:** `job-radar-dev`, port 8001 (read-only audit only)  
**Isolated multi-user feature build:** `job-radar-user-preferences`, port 8002

## 1. Product priority reset — supersedes earlier multi-user-first plans

The primary product promise is **fresh job discovery**: a job should appear in our portal as soon as reasonably possible after the source makes it available, with reliable source identity, timestamps, deduplication and source health.

The order of work is now:

1. **P0 — Audit and improve the ingestion engine.** Establish actual source coverage, freshness, yield, rate-limit behavior and failure isolation. Keep jobs flowing into the portal without relying on signup or Telegram.
2. **P1 — Reverse-engineer observable JobBeeper behavior.** Use an authorized logged-in browser session to understand visible refresh cadence, request patterns, pagination, timestamps, source labels, job-card lifecycle and freshness UX. Record evidence before implementing.
3. **P2 — Build a measured source catalog and adapter platform.** Prioritize permitted public APIs/feeds and employer ATS boards, then job-board integrations. Add adapters incrementally with per-source request budgets and tests.
4. **P3 — Validate coverage and latency at scale.** Expand toward 100 useful sources/integrations, but measure useful new jobs, freshness, reliability and rate limits rather than counting adapters alone.
5. **P4 — Resume paused product features.** Complete live Telegram test-bot smoke test and promote multi-user preferences/notifications only after ingestion is reliable. Resume parser enhancements, signup UX, referral intelligence and hiring-post discovery follow later.

**Paused, not discarded:** PR #46 and the multi-user/resume/Telegram work remain in `feat/user-preferences-evaluations-20261106`, with a healthy isolated feature instance. Do not merge it into the shared dev or production environment while ingestion is the priority. No more signup, resume-parser, referral or Telegram feature expansion until P0/P1/P2 work is complete, unless a security fix is required.

## 2. What is actually implemented today (verified 2026-11-07)

### Collector inventory in the current feature-branch code

The `COLLECTORS` registry in `v2/radar.py` currently contains five adapters:

| Source | Implementation | Current production state | Important caveat |
|---|---|---|---|
| LinkedIn | Guest search HTML parser, staggered query/location targets, bounded deep pages and detail enrichment | Enabled | HTTP 429s are occurring; current design backs off but does not eliminate them |
| Naukri | External GitHub Actions relay using `python-jobspy==1.2.0`; main app polls generated JSON | Enabled | Relay publishes date-level posting dates; exact posting-to-discovery lag is not measurable from current data |
| Instahyre | Direct JSON endpoint adapter | Disabled | Last recorded production runs on Oct 8 failed with HTTP 400; not production-ready |
| Greenhouse | Public board API, explicit employer board allowlist | Disabled | Only a few configured boards; not a global Greenhouse index |
| Ashby | Public job-board posting API, explicit employer board allowlist | Not enabled in current production runtime | Current feature code supports it, but production image/config predates this adapter |

**Reality check:** this is five source adapters in the current feature code, not 100 platforms. Production currently has only LinkedIn and Naukri enabled. Shared dev currently has only Naukri enabled. Greenhouse/Ashby are employer-board integrations, not global searches across every employer using those ATS products.

### Read-only production runtime evidence

Production runtime config (`/data/config.json`, inspected inside the running container without printing secrets):

- Enabled: LinkedIn and Naukri.
- Disabled: Instahyre and Greenhouse; the deployed runtime config does not contain Ashby.
- LinkedIn: 4 query families × 4 locations; nominal 180-second scheduler interval; collector serializes HTTP calls with at least 4 seconds between requests.
- Naukri: 6 query families; app polls the relay every 300 seconds.

Production SQLite (`/data/jobs.db`, opened read-only) for the rolling 24 hours ending 2026-11-07 around 10:48 UTC:

| Source | Runs | Jobs seen across runs | New DB records | Failed source runs | Notes |
|---|---:|---:|---:|---:|---|
| LinkedIn | 368 | 4,570 | 313 | 0 | 36 HTTP 429 log events in the last 24 hours; collector applies global cooldowns up to 1,800 seconds |
| Naukri | 288 | 98,211 | 173 | 0 | Repeatedly ingests the whole relay snapshot; this is not 98k unique jobs |

Additional observed data:

- LinkedIn's 312 timestamped observations in the 24-hour window had stored discovery-latency values p50 **54 minutes**, p90 **4 hours**, maximum **6 hours**. Treat this as a diagnostic estimate, not a definitive SLA: source labels and their timestamp precision can be rounded/approximate, and the product needs a controlled timestamp validation exercise.
- Naukri had 171 observations with date-level posting precision and zero valid latency samples in the same window. This is correct caution: a date-only value must not be treated as an exact posting time.
- Last 72-hour production logs contained 60 LinkedIn HTTP 429 events; last 24 hours contained 36. Some events caused 1,800-second cooldowns. This means **we are not currently at a no-rate-limit state**.
- Recent Naukri relay runs were manually dispatched approximately every five minutes and completed successfully. The public feed snapshot at 2026-11-07 10:45 UTC contained 332 jobs. The relay workflow's YAML also declares a five-minute schedule, but the VM cron fallback is what is visibly generating `workflow_dispatch` runs in the latest run history.
- The Naukri relay queries each configured query for up to 30 results over a 72-hour window and publishes up to 500 deduplicated jobs. Its `updated_at` is the relay collection time, not the original posting time.
- Instahyre's last recorded production runs (2026-10-08) failed with HTTP 400; keep it disabled until the request/schema issue is diagnosed.

### Shared dev runtime evidence

- Shared dev is a separate container on `127.0.0.1:8001`, image `job-radar-dev-multitenant:f43cd4a` created 2026-11-06.
- Its mounted config enables Naukri only; LinkedIn, Instahyre, Greenhouse and Ashby are disabled. Poll interval for Naukri is 300 seconds.
- Read-only DB inspection showed historical Ashby/Naukri records, but latest source runs at audit time showed Naukri only. Do not interpret historical rows as a currently active source.
- Shared dev was not changed during this audit.

### Environments left untouched

- Production container `v2-radar-1` and production SQLite volume: read-only inspection only; no config, webhook, restart or deployment.
- Shared dev container `job-radar-dev` and its SQLite volume: read-only inspection only; no config, restart or deployment.
- Isolated feature container `job-radar-user-preferences` on port 8002 remains separate and healthy; no Telegram test bot credentials are configured and no messages were sent.

## 3. What the current data says

We have a working ingestion foundation, but not the stated product promise yet:

- Two sources are actually enabled in production, and only one is enabled in shared dev.
- The current LinkedIn implementation discovers new records but receives repeated 429s. Increasing request concurrency or trying to evade throttling would make reliability worse and is not acceptable.
- Naukri has a useful relay and repeated feed ingestion, but its five-minute collection cadence, relay runtime, main-app poll interval and date-only posting timestamps prevent a claim of instant discovery.
- Current `source_runs` records `jobs_seen`, `new_jobs`, and an error string, but not enough request-level data to explain request cost, 429 rate, retry behavior, page yield or per-endpoint freshness. A caught 429 can still be recorded as a successful run, so run success must be separated from source request health and partial-result status.
- The current source registry lives in the large `v2/radar.py` module. Source adapters have different request, timestamp and retry behavior; this needs a consistent contract before expanding to dozens of sources.
- No evidence presently supports the claim that our product can ingest from 100 platforms or match JobBeeper's observed freshness.

## 4. JobBeeper reverse-engineering scope

Reverse-engineering is useful **to understand observable product behavior and generate hypotheses**, not to recover or copy private backend code.

### Evidence to capture from the user's authorized browser session

1. Search/feed initial page load: requests that return job cards and source labels.
2. Background refresh: preserve the Network log and observe at least 10–15 minutes after initial load.
3. Filters: change one filter at a time and observe which request parameters change.
4. Pagination/infinite scroll: capture cursor/offset/page behavior and whether older pages are requested separately.
5. Job details: determine whether descriptions are embedded in the initial response or fetched lazily.
6. Freshness: record visible posted/discovered labels, refresh indicators, newest-first ordering and whether the same job changes when revisited.
7. Source coverage: record which sources are explicitly displayed for real job cards; distinguish observed sources from marketing claims.
8. Reliability: note status codes, 304 responses, 429 responses, request cadence, retry behavior and any user-visible stale/error state.

### Safe capture rules

- Use only the user's own authorized JobBeeper session. Do not bypass login, paywalls, CAPTCHAs, access controls or bot defenses.
- Prefer Chrome DevTools Network metadata and a **sanitized HAR**. Redact cookies, authorization/bearer headers, CSRF tokens, session IDs, user IDs, personal data and response fields that contain private account information.
- Do not paste secrets or raw authenticated HARs into chat or Git. Store any raw capture locally and inspect it locally; commit only a redacted evidence summary and sanitized fixtures.
- Do not replay private endpoints, automate account actions, or use observed credentials/tokens. No proxy/IP rotation or rate-limit evasion.
- Record each item as **Observed**, **Inferred**, or **Unknown**. A network request can reveal a product's observable client/server contract, but not prove its backend scheduler, data provider, crawler fleet or source agreements.

### Evidence report deliverable

Create `docs/JOBBEEPER_NETWORK_EVIDENCE_YYYY-MM-DD.md` after the browser investigation. Include timestamped request metadata, endpoint host/path (redacted as needed), method, cadence, status codes, pagination model, response field names, timestamp semantics, source names, and screenshots/har references that contain no secrets. End with an explicit unknowns list and engineering implications. Do not write implementation code until this report is reviewed.

## 5. Source expansion strategy toward 100

Do not build 100 brittle scrapers or assume 100 ATS vendor names equal 100 searchable job sources. Build a catalog and group integration patterns:

1. **Public ATS job-board APIs:** Greenhouse, Ashby, Lever, SmartRecruiters, Teamtailor and similar. Usually require employer board identifiers; one adapter can serve many employer boards.
2. **Employer career sites and structured feeds:** public JSON, RSS/Atom, schema.org JobPosting, sitemaps and official career pages, where permitted.
3. **Job boards/aggregators:** India-first sources such as Naukri, Instahyre, Cutshort, Hirist, Wellfound and other sources only after verifying permitted access and freshness.
4. **Global boards and ATS ecosystems:** Workday, iCIMS, Oracle Recruiting/Taleo, SAP SuccessFactors, Workable, Recruitee, SmartRecruiters, Darwinbox, Keka, Zoho Recruit and others. Determine whether there is a public board endpoint, tenant-specific API or only a customer-authenticated API; do not pretend a private tenant API is a global job search feed.
5. **Employer-specific sources:** curated list of high-value Indian and remote-first engineering employers. Add tenant/board configs using a supported adapter instead of writing a new scraper per employer.

Maintain a source catalog with: source/provider, integration type, official docs/endpoint, permission/terms review, discovery method, employer/board identifier needs, authentication, pagination/cursor, stable ID, canonical apply URL, posted/updated timestamp and precision, ETag/Last-Modified support, request limits, poll budget, retry policy, sample job yield, new-job yield, freshness p50/p90, failure rate, operational owner and enabled status.

Prioritize the sources that add **unique relevant jobs** for the target market. Count both platform adapters and configured employer boards, but report them separately.

## 6. Target ingestion architecture

Every adapter must implement a common contract:

- `fetch(cursor, since, request_budget) -> observations, next_cursor, source_metrics`
- stable source-specific ID and canonical application URL;
- source posted/updated timestamps plus explicit precision (`minute`, `date`, `unknown`);
- observed/fetched timestamp, first-seen timestamp and last-seen timestamp;
- pagination/incremental cursor and optional conditional request headers;
- request count, pages, records seen, records new/changed, response status classes, elapsed time and rate-limit signals;
- source-specific error classification and health state.

The scheduler should provide:

- per-source and per-host request budgets and concurrency limits;
- jittered polling to avoid synchronized bursts;
- adaptive backoff that honors `Retry-After` and provider guidance;
- no automatic retries for permanent 4xx/access-denied responses;
- source-level isolation so one failing provider cannot block others;
- conditional GET/ETag/Last-Modified when supported;
- incremental cursors and overlap windows to avoid repeatedly downloading full feeds;
- bounded page sizes, request timeouts and response sizes;
- transparent cooldown state and a manual diagnostic path that does not bypass provider limits.

The pipeline remains:

`fetch -> validate -> normalize -> canonicalize -> deduplicate -> persist -> evaluate -> expose in portal`

Per-user matching/notifications are downstream and must not slow or block shared ingestion.

## 7. Ingestion metrics and release gates

Track per source and per endpoint:

- poll schedule vs actual start delay;
- request count, page count, response status histogram, 429 count, retry count, cooldown duration and time in cooldown;
- fetched observations, unique source IDs, new records, changed records, duplicates and relevant jobs;
- timestamp coverage and precision;
- discovery lag p50/p90 only for timestamp types precise enough to support it;
- source-run duration, last successful fetch, last new job and freshness of the latest feed;
- cost per 1,000 unique jobs where a paid API/provider is involved.

Do not claim a source is real-time from poll interval alone. A five-minute poll interval does not establish five-minute discovery if the source itself updates slowly or the provider's feed is stale.

Before enabling a source in production, require:

1. documented and permitted endpoint/access method;
2. fixtures and stable-ID/dedupe tests;
3. timestamp precision and update semantics verified;
4. at least 24–72 hours of dev/canary observations where practical;
5. request budget and backoff tests, including simulated 429/Retry-After;
6. no cross-source failure propagation;
7. useful unique-job yield and measurable freshness;
8. source-health visibility and rollback/disable switch.

## 8. Immediate next steps

1. **Pause feature expansion.** Keep PR #46 draft and isolated. Do not create/configure a Telegram test bot now; it is not needed for ingestion work. Revisit it when the product returns to multi-user delivery.
2. **Complete JobBeeper browser evidence capture.** Owner/desktop agent: capture sanitized Network evidence for initial load, background refresh, filters, pagination and job detail. Do not include secrets. Save the evidence report under `docs/` and summarize it in the handover files.
3. **Baseline our current production ingestion read-only.** Findings above are the starting point. Add a reproducible diagnostic report/command that reports metrics without printing job descriptions or secrets.
4. **Fix observability before tuning.** Add request/page/status/429/cooldown and timestamp precision metrics to source runs. Correct any misleading latency calculations.
5. **Diagnose LinkedIn 429s.** Inspect the actual request cadence, query overlap, enrichment calls and cooldown history. Reduce pressure or move to a permitted structured provider; do not evade rate limits. Consider disabling LinkedIn in dev during tests if it would create unnecessary traffic.
6. **Make Naukri incremental and measurable.** Inspect relay workflow run duration and feed freshness, reduce repeated full-feed processing where possible, preserve last-good feed, and track the time the relay observed each job. Date-only `posted` values must remain low precision.
7. **Validate Instahyre and public ATS adapters individually.** Instahyre is disabled after HTTP 400. Greenhouse/Ashby need canaries against a few real board identifiers. Add Lever and SmartRecruiters after their public contracts and request policies are confirmed.
8. **Build a prioritized 100-source catalog.** Start with 20 high-value sources/ATS patterns and expand only when measured yield justifies it. A catalog entry is not a working integration.
9. **Only after ingestion gates pass:** return to PR #46, configure a dedicated Telegram test bot, run the opt-in delivery smoke test, and decide whether to promote multi-user signup/preferences/Telegram to shared dev.

## 9. Current owner action

The only immediate owner-assisted action is to run the JobBeeper browser inspection in the already authenticated desktop browser and provide a sanitized HAR or the redacted evidence summary. No Telegram bot creation or credential sharing is required now.


## 2026-11-07 owner update — ingestion and feature work run in parallel

The owner has asked that the existing authentication, resume-assisted onboarding and Telegram feature branch continue in parallel with the JobBeeper browser/network investigation. Earlier wording above that says to pause all multi-user/resume/Telegram development is superseded by this update. The ingestion-first product strategy remains authoritative for source priorities and production release readiness, but it is not a reason to stop isolated feature work.

- Feature work remains isolated on `feat/user-preferences-evaluations-20261106` and PR #46 stays draft. No shared-dev or production promotion without explicit approval.
- The owner is creating a dedicated development Telegram bot. Configure it only in the isolated feature environment; keep the production bot untouched. Live webhook testing waits for a public HTTPS endpoint.
- The owner is separately collecting sanitized JobBeeper Network evidence with Codex `@Chrome` and full CDP. The evidence report/HAR will be reviewed here when supplied; do not replay private endpoints or include credentials.
- Latest isolated feature verification on 2026-11-07: 262 V2 tests passed, 1 skipped. See the handover files and `docs/TELEGRAM_PER_USER_SETUP.md` for exact changes and remaining live E2E steps.


### Feature-track follow-up — resume parser tests (2026-11-07)

- The parallel feature branch now has 15 focused resume-parser tests and the full isolated V2 suite passes 270 tests with 1 skipped. Coverage includes PDF page/encryption limits and DOCX archive expansion defenses. This does not change ingestion priorities; it keeps the separate feature work healthy while JobBeeper evidence gathering continues.


### Feature-track follow-up — Google OAuth state lifecycle (2026-11-07)

- Google OAuth callback now consumes one-time state for both provider success and cancellation/error responses after verifying the browser-bound state cookie. New regressions cover cancellation cleanup and mismatched-state rejection. Full isolated V2 suite is **272 passed, 1 skipped**. This feature work remains parallel to the JobBeeper evidence investigation and does not change ingestion priorities.


## 2026-11-07 — Dev bot and local secret setup clarification

The owner supplied `@YourJobBeeperDevBot` as the intended development Telegram bot handle. BotFather token creation/verification remains pending. The webhook secret is generated separately in Windows PowerShell (`python -c "import secrets; print(secrets.token_urlsafe(32))"`, or `py -c ...`) or Ubuntu (`python3 -c ...`); it is not a Telegram command. `.env.feature` is currently absent and git-ignored; the documented setup is in `docs/TELEGRAM_PER_USER_SETUP.md`. Google OAuth env passthrough was added to the isolated feature Compose, but all three Google OAuth values remain blank. Feature port 8002 is loopback-only, so webhook registration still waits for an approved public HTTPS dev route.


## 2026-11-07 — JobBeeper authenticated network evidence and local comparison

The sanitized browser report is now tracked at docs/JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md. It records only request paths, methods, status codes, timing observations and UI labels. No cookies, authorization values, request/response bodies or storage values were retained.

### Evidence-backed JobBeeper behavior

- The /user/jobs document is followed by a browser fetch to /api/user/jobs with numeric page, per_page=20, status=matched, sort_by=created_at, and sort_order=desc parameters. Clicking Next changes page=1 to page=2.
- Keyword search is requested server-side through the same list route with search=<term>.
- Feed initialization also requests authenticated-user bootstrap, company/filter data, stats, notification summary and trial/offer state.
- Opening a detail caused separate metadata and tracker GETs plus a view-marking POST; notification summary was fetched again.
- UI source labels observed: LinkedIn, Ashby, Naukri, Lever and Hirist. Cards visibly distinguish employer-stated experience from description-derived experience.
- Ten one-minute idle windows showed no JobBeeper Fetch/XHR, WebSocket or SSE traffic. The observed account showed an expired-subscription six-hour-delay notice. This is not proof that active accounts never poll or that the product has no longer polling cadence.
- Timestamp meaning (original publish vs discovery/ingestion/update/display) and response schemas remain unknown because response bodies were not retained.

### Comparison with our current feature-branch implementation (read-only code inspection)

- Our GET /api/jobs already performs keyword search in SQLite before LIMIT, orders newest-first using COALESCE(source_posted_at, discovered_at) and returns per-user evaluation/match metadata. The UI passes minutes=4320, limit=500, and q when search is entered.
- Our feed has no numeric page/per_page parameters or total/page metadata. It retrieves up to 500 matching jobs in one request; most other feed filters are applied to that in-memory set. This is the main feed scalability/behavior gap against the observed page-based feed.
- Our job records already separate source_posted_at, posted_precision, discovered_at, and discovery-latency fields. The dashboard shows source-posted and discovered times in the inspector. However, the normalized dashboard model does not currently carry an explicit experience-provenance field equivalent to the JobBeeper UI's employer-stated/from-description distinction. Audit extraction-to-storage-to-API provenance before displaying such a label.
- Our /api/jobs/{job_id} returns a complete authorized job detail from the local database. The dashboard inspector currently renders the selected item from the in-memory feed; it does not issue separate metadata/tracker/view requests. We should add separate tracker or view events only when a concrete user-facing product requirement exists, not merely to imitate request names.
- Before this change, the dashboard polled the jobs feed every 10 seconds. The feature branch now polls once per minute while the tab is visible, refreshes on return to the tab, and skips periodic source-status calls while hidden. This is our operational choice, not a claim about JobBeeper's active-account cadence.

### Next implementation sequence

1. Add server-side numeric pagination with stable sort and total/has-next metadata while retaining a backwards-compatible limit path; update filters/search so they operate across all pages, not only the current slice.
2. Trace experience provenance end-to-end (source-stated vs description-derived vs inferred/unknown); persist an explicit provenance value and confidence only where supported by the extractor.
3. Keep the existing source-posted/discovered timestamp distinction; investigate last-successful-check and last-material-change tracking separately.
4. Add source-specific adapters for Lever/Hirist only after confirming public/authorized access methods and measuring unique useful yield. JobBeeper's visible source labels do not establish that those sources are globally searchable or expose a public API.
5. Repeat the refresh observation on an active subscription and test each visible filter independently. Record only sanitized parameter names, HTTP outcomes and timing; do not retain private payloads or replay authenticated third-party requests.

The report is behavioral evidence, not an implementation specification for JobBeeper's private backend.


## 2026-11-07 — Second-round JobBeeper evidence and implementation checkpoint

The second-round report is in docs/JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md. It confirms the list request shape more precisely:

GET /api/user/jobs?page=1&per_page=20&status=matched&sort_by=created_at&sort_order=desc&search=java

- search is a server-requested keyword parameter and the tested search resets page to 1.
- page is numeric (1 and 2 observed), per_page=20, status=matched, sort_by=created_at, sort_order=desc.
- The other visible filter controls were not individually tested. Do not invent their parameter names or values.
- Ten idle one-minute observations again showed no feed refresh traffic. Because the account remained expired with a six-hour delay notice, active-subscription and hidden-tab refresh behavior remain unverified.
- Response bodies were not retained. Pagination total fields, stable-ID overlap, actual provenance field names, extra detail request behavior and save/application tracking remain unknown.
- Two additional source-diverse detail opens were not completed.

### Independent implementation completed on the isolated feature branch

The feature API and dashboard now support the observed feed request contract while preserving legacy callers:

- GET /api/jobs accepts search, page, per_page, status, sort_by and sort_order. Legacy q, limit and sort remain supported.
- The dashboard requests 20 rows per page, uses numeric Previous/Next navigation, sends status=matched for regular users and status=all for admins, and maps newest-first to sort_by=created_at and sort_order=desc.
- Our own API returns pagination metadata (page, per_page, total, total_pages, has_previous, has_next). These are our implementation choices; JobBeeper's response fields are still unknown.
- Search, source, score, age, alertability and remote filters are applied in SQLite before LIMIT/OFFSET, so filtering spans the full result set. Our app-specific filter parameter names are not claimed to be JobBeeper's.
- Experience evidence is persisted as a range, provenance (employer_stated, description, inferred, unknown) and qualitative evidence strength (high, medium, low, unknown). The confidence value is a transparent rule-based evidence grade, not a calibrated probability.
- The resolver treats an explicit LinkedIn Experience label as employer-stated/high; a clearly framed overall/professional/work requirement in the captured JD as description/medium; a generic or skill-specific years mention as inferred/low; missing evidence as unknown. Exact JobBeeper response fields and its own classifier remain unknown.
- Existing rows migrate additively. We retain stronger existing provenance when a later weaker scrape does not provide equal evidence.

### Test status for this checkpoint

Focused API/dashboard contract suite: 28 passed, 1 skipped. Full isolated V2 suite: 279 passed, 1 skipped. The final feature image was rebuilt from v2/docker-compose.feature.yml and /health is healthy on 127.0.0.1:8002. GitHub V2 CI run 42383162683 passed Python compilation, modern dashboard JavaScript syntax, focused router/extractor tests and the full V2 suite. Shared dev 8001 and production 8000 were not changed.

## 2026-11-07 owner UAT update — authentication validated; ingestion remains priority

- Owner confirmed live Google OAuth sign-in and resume parser success on isolated feature port 8002. Google credentials are configured only in server-side /tmp/job-radar-user-preferences/.env.feature (git-ignored, mode 600). Production 8000 and shared dev 8001 remain untouched.
- Deferred PR #46 product/UI backlog: email/password self-service signup, Google consent branding still showing n8nApp, and a preferences-save failure that was not surfaced in the frontend. The reported response detail was "At least one target role is required before accessing the job feed." despite a visible target-role chip; request payload/status and root cause are unknown. See docs/GOOGLE_OAUTH_SETUP.md; no fixes requested now.
- Current highest-priority ingestion follow-up remains Naukri relay freshness/incremental processing: preserve the last-known-good snapshot, distinguish relay collection time from the main app's observation time, avoid reprocessing unchanged jobs where safe, and measure feed staleness without treating date-only posted values as exact timestamps.

## 2026-11-08 — Multi-user feature QA readiness

- Preference save patch on PR #46 branch now reconciles submitted tags with rendered chips, commits text still in the tag input, validates member roles/locations client-side and surfaces server validation detail. API + dashboard contract regressions pass; full V2 suite **281 passed** locally.
- A dedicated browser QA server is available on loopback 8004 with a fresh synthetic-only DB, 10 synthetic jobs, admin/member test accounts, all source collectors/notifications/Google/Telegram disabled. Tunnel to `localhost:18004`; see `docs/LOCAL_BROWSER_QA_2026-11-08.md` for steps and tests.
- No production/shared dev impact. Desktop built-in Browser should be used for localhost (not cloud browser); file upload automation is unsupported in the built-in Browser.
- Next: desktop browser QA, redacted findings, fix confirmed issues, then rebase PR #46 onto current `v2-live-radar`; separately validate Google OAuth on 8002 and per-user Telegram delivery using the dev bot only. PR remains draft.