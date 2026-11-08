# Next Agent Start Here — Job Radar V2

**Checkpoint:** 2026-11-08 — SQLite contention fix live in shared dev; Workday adapter candidate tested, awaiting final CI/push
**Read this first when taking over the Job Radar task.**

## Owner's product goal

Build a reliable multi-source job radar that fetches new jobs from all 36 requested platforms, filters each job separately against each user's saved preferences, and sends Telegram alerts only to matching users. The owner expects near-real-time capture (target 2-minute polling for high-priority boards where permitted; webhooks when an employer authorizes them), not a daily batch.

The required 36 platforms and source-by-source current status are in [ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md](ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md). Workday is now implemented and tested on one NVIDIA public board but remains disabled; Darwinbox is the next connector. The list mixes ATS vendors and job marketplaces; ATS feeds generally require a specific employer board/tenant, so company/career-site discovery is a core requirement.

## Current environment

- Oracle VM: job-radar; SSH login ubuntu; full passwordless sudo. Use sudo for Docker/systemd.
- Shared dev: container `job-radar-dev`, image `job-radar-dev-multitenant:c441737`, host port 8001, health HTTP 200. P0 SQLite contention fix is live here only.
- Production: container v2-radar-1 on port 8000, still old image and untouched. Health HTTP 200.
- Shared-dev image was built from exact P0 CI-tested SHA `c441737ca6c19f17002d9a43923a4a64353f0977`. The Workday adapter is a later uncommitted candidate and is not in the running image.
- PR #51: https://github.com/AvinashBhalla/job-beeper/pull/51 — open/draft, not merged.
- Only Naukri is enabled in shared-dev's recurring scheduler. Notifications/Telegram, Gemini and LLM routing are off in shared dev.

## What is actually live-tested

Real shared-dev end-to-end pipeline evidence exists for:
- Naukri scheduled polling
- Instahyre: 140 inserted, 4 HTTP 200 pages; current response parser fixed
- Greenhouse: 369 inserted, 3/3 boards
- Ashby: 828 observed, 34 new, 2/2 boards
- Lever: 500 inserted via one-off paytmpayments board, 5-page cap reached; not configured for recurring polling
- LinkedIn: one paced HTTP 200 probe, 10 unique jobs inserted; not configured for recurring polling

The candidate V2 COLLECTORS registers seven sources: LinkedIn, Naukri, Instahyre, Greenhouse, Ashby, Lever and Workday. The deployed shared-dev image registers six (no Workday); only Naukri is enabled in its scheduler. Workday exists only in the local candidate worktree and is disabled by default. The other 29 named platforms are not production-grade V2 integrations. Do not claim all 36 are working.

Latest verified shared-dev data at 2026-11-08 12:58 UTC: SQLite integrity `ok`, journal mode `wal`, app connection busy timeout 15,000ms; jobs=9,462, source_runs=7,874. The last eight source runs were successful Naukri cycles; no `database is locked` log entry appeared in the last 90 minutes. Telegram delivery is disabled, Telegram credentials absent, and no per-user notification settings are configured.

## Immediate blockers before production

1. **SQLite lock fix is implemented, CI-passed and deployed to shared dev only.** Continue the canary soak: several Naukri polls have succeeded and there are no lock errors in post-deployment logs so far. Do not treat this as a production-scale stress test.
2. **Live multi-user flow remains incomplete.** Automated tests verify separate preferences, feeds, Telegram chats, opt-in, CSRF and user isolation. Still perform real signup/login for two users and deliver only to dedicated test chats or a fake Telegram transport. Never request secrets in chat.
3. **Workday adapter is implemented in the local candidate but not yet pushed/CI-checked.** Twelve focused Workday tests pass; the final full V2 suite passes 359 tests in 266.690s. Two real NVIDIA public-board `run_source` polls on a disposable DB: first inserted 20 jobs with full descriptions and suppressed all 20 as initial inventory; second inserted 0 duplicates; integrity `ok`, zero sends. Commit/push, then run exact-SHA GitHub CI. Keep Workday disabled in shared dev until a verified employer-board pilot is separately approved.
4. **Darwinbox is next.** The official Recruitment API needs employer-provided authentication. Validate candidate-site feeds per real employer; do not assume one universal unauthenticated endpoint.
5. **Employer/board discovery is still missing.** Build a registry/search workflow for real ATS tenants and careers URLs. Workday currently requires the admin to paste a verified public board URL. Multi-board Workday calls are sequential and scale at roughly 24.6 seconds per board in the live test; a bounded concurrency/per-board scheduler is needed before claiming the two-minute target for larger registries.
6. Continue the remaining 36-platform roadmap. The runtime currently registers seven source collectors; only Naukri is recurring-enabled in shared dev. Mark a source complete only after repeated real-board polling, pagination/dedup, reliable timestamp handling, live DB evaluations and per-user notification decisions.
7. Keep the known 320px toolbar hit-test overlap deferred as requested. Do not deploy production: its Telegram/global notification settings and queue are live. Production requires a separate reviewed backup, all P0 gates and explicit owner approval.

## Newest branch / verification checkpoint

- Branch: `fix/sqlite-notification-contention-20261108`, based on integration. P0 commit `c441737ca6c19f17002d9a43923a4a64353f0977` is pushed and passed GitHub Actions run `42480365749` (all jobs green); it is also deployed to shared dev only. Current Workday adapter/UI changes are uncommitted local changes on top of that SHA; commit/push and trigger fresh GitHub CI before considering them integrated.
- P0 exact-SHA V2 suite: **347 passed, 188.827s, zero failures**. P0 CI run succeeded. Latest Workday-focused class: **12 passed**. Latest complete V2 suite on the current Workday code: **359 passed, 266.690s, zero failures** (captured in `/tmp/job-radar-sqlite-contention-final-suite.log`).
- Shared-dev current image: `job-radar-dev-multitenant:c441737` on port 8001, DB WAL + `integrity_check=ok`, app busy timeout 15,000ms, all key table counts 9,461 and source_runs 7,872 at last check. Three post-deploy Naukri runs succeeded; no lock error logged since rollout. Notifications false; Telegram credentials absent; Gemini extraction/matcher and LLM router/matcher all explicitly false in the effective container environment. A `.env` interpolation mismatch was discovered during rollout and fixed through explicit Compose false overrides; do not edit the shared `.env`.
- Fresh pre-deploy online SQLite backup: `/var/backups/job-radar-daily/development-jobs.sqlite3`, SHA-256 `aa78251196c7c2925cf09e5b6c9cbfb7878884681bd9920407e32f4e2ff0b49e0`, 9,459 jobs, integrity ok. Production snapshot also completed but prod container was not changed. Production `v2-radar-1` remains untouched.
- Workday CXS adapter is registered in local code, config version 13, disabled by default, `workday_boards=[]`, poll default 120 seconds. It derives tenant/cluster/site from allowlisted HTTPS employer URLs, takes one page of 20 listings and up to 20 detail requests per board, uses stable requisition IDs and safe board-derived job URLs, strips HTML descriptions, preserves `postedOn` as a label only and sets `source_posted_at`/precision to unknown. NVIDIA live poll returned 20 unique postings with 20 full detail records in 24.57s. HTTP 429 is respected with bounded `Retry-After` cooldown, persisted into source-run history and restored after restart. This is one live public board and one current poll, not recurring coverage; no Workday employer board is enabled in shared dev.
- Dashboard has Workday/Ashby/Lever source toggles and an admin Workday JSON board editor. Dashboard syntax is checked in the modern GitHub CI runner; VM Node is 12.22.9 and cannot parse the existing nullish-coalescing syntax.
- Workday 429 responses now stop further requests, persist Retry-After cooldown in `source_runs`, restore on startup and make the scheduler skip Workday until expiry. A controlled `run_source` 429 test recorded status 429 and a 120-second cooldown.
- Important scale limitation: Workday boards currently run sequentially. The 24.57s measured per board means 4 boards approach the 120s poll interval and larger registries need a bounded concurrency/per-board schedule before claiming two-minute end-to-end capture. Company-to-board discovery is not implemented.
- Darwinbox remains unimplemented; official Recruitment API uses employer-issued authentication.


## Required reading / handover

1. [36-platform coverage, connector research and acceptance criteria](ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md)
2. [Deployment runbook](DEV_DEPLOYMENT_RUNBOOK_2026-11-08.md)
3. [Promotion execution record](QA/shared-dev-promotion-execution-2026-11-08.md)
4. The latest appended section at the END of [JOB_RADAR_HANDOVER.md](JOB_RADAR_HANDOVER.md)
5. The latest appended section at the END of [JOB_RADAR_KNOWLEDGE_TRANSFER.md](JOB_RADAR_KNOWLEDGE_TRANSFER.md)

Do not ask the owner to repeat the platform list, latency goal, Workday/Darwinbox priority or per-user Telegram requirement.
