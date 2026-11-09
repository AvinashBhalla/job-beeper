# Next Agent Start Here — Job Radar V2

**Checkpoint:** 2026-11-08 — SQLite P0 live in shared dev; Workday adapter committed and exact-SHA CI passed
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
3. **Workday adapter is committed and exact-SHA CI-passed, not deployed.** Commit `c4f9c66cd05419242a761939f4c1ff883b4266d0`; GitHub V2 CI run `42483043107` passed all steps, including dashboard JavaScript syntax and full suite. Local full suite: 359 tests / 266.690s. Two real NVIDIA public-board `run_source` polls on a disposable DB: first inserted 20 jobs with full descriptions and suppressed all 20 as initial inventory; second inserted 0 duplicates; integrity `ok`, zero sends. Keep Workday disabled in shared dev until a verified employer-board pilot is separately approved.
4. **Darwinbox is next.** The official Recruitment API needs employer-provided authentication. Validate candidate-site feeds per real employer; do not assume one universal unauthenticated endpoint.
5. **Employer/board discovery is still missing.** Build a registry/search workflow for real ATS tenants and careers URLs. Workday currently requires the admin to paste a verified public board URL. Multi-board Workday calls are sequential and scale at roughly 24.6 seconds per board in the live test; a bounded concurrency/per-board scheduler is needed before claiming the two-minute target for larger registries.
6. Continue the remaining 36-platform roadmap. The runtime currently registers seven source collectors; only Naukri is recurring-enabled in shared dev. Mark a source complete only after repeated real-board polling, pagination/dedup, reliable timestamp handling, live DB evaluations and per-user notification decisions.
7. Keep the known 320px toolbar hit-test overlap deferred as requested. Do not deploy production: its Telegram/global notification settings and queue are live. Production requires a separate reviewed backup, all P0 gates and explicit owner approval.

## Newest branch / verification checkpoint

- Branch: `fix/sqlite-notification-contention-20261108`. P0 commit `c441737ca6c19f17002d9a43923a4a64353f0977` passed GitHub Actions run `42480365749` and is deployed to shared dev only. Workday adapter/UI changes are commit `c4f9c66cd05419242a761939f4c1ff883b4266d0`, pushed to both the feature branch and PR #51 integration branch; GitHub V2 CI run `42483043107` passed on that exact SHA.
- P0 exact-SHA V2 suite: **347 passed, 188.827s, zero failures**. Workday-focused class: **12 passed**. Workday final local full V2 suite: **359 passed, 266.690s, zero failures**. GitHub CI run `42483043107` is completed successfully on exact Workday SHA `c4f9c66`; py_compile, modern Node/dashboard syntax, focused router/extractor tests, and full V2 suite all passed.
- Shared-dev current image: `job-radar-dev-multitenant:c441737` on port 8001, DB WAL + `integrity_check=ok`, app busy timeout 15,000ms, jobs=9,462 and source_runs=7,874 at 2026-11-08 12:58 UTC. Three post-deploy Naukri runs succeeded; no lock error logged since rollout. Notifications false; Telegram credentials absent; Gemini extraction/matcher and LLM router/matcher all explicitly false in the effective container environment. A `.env` interpolation mismatch was discovered during rollout and fixed through explicit Compose false overrides; do not edit the shared `.env`.
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


## Current PR/CI confirmation — 2026-11-08

- Workday commit `c4f9c66cd05419242a761939f4c1ff883b4266d0` is pushed to the feature branch and integration PR #51. GitHub Actions V2 run `42483043107` completed successfully; all steps passed, including full V2 suite and dashboard JavaScript syntax. PR #51 remains open/draft, not merged. Workday is not deployed or enabled in shared dev.


## 2026-11-08 — Employer board discovery + SmartRecruiters/Workable update

- Current candidate commit: `93f532c20b0dcf6b37429a65add18281c16c00f9`, attached to draft PR #51 (`integration/pr46-v2-rebase-20261108` → `v2-live-radar`). PR remains draft/open. GitHub Actions V2 CI run `42491830453` is running on this exact SHA; wait for its final result before merge consideration.
- Added admin-first company/board discovery in `v2/board_discovery.py`: submit company name, website and optional careers URL; inspect a bounded number of public HTTPS pages, follow likely careers links, detect known ATS board patterns and persist multiple boards per company. This is not a per-employer hand-built JobBeeper page. The admin workflow is scan → inspect → endpoint verify → explicit activate. Discovery alone never enables polling.
- Discovery recognises Workday, Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Recruitee, Breezy HR, Teamtailor, BambooHR, Rippling and Personio. Collector availability is distinct from detection: current V2 ATS collectors are Greenhouse, Ashby, Lever, Workday, SmartRecruiters and Workable. Recruitee/Breezy/Teamtailor/BambooHR/Rippling/Personio are discovery-only pending validated public endpoint adapters. Darwinbox is still not implemented; official recruitment APIs are employer-authenticated unless a specific public candidate endpoint is independently verified.
- Added SmartRecruiters public postings API and Workable public widget collectors. Config version 14; both source flags default false and allowlists are empty. SmartRecruiters uses bounded three-page scans (100 listings/page) and up to 20 detail lookups per board. Workable consumes the public published-jobs widget. Both include stable source IDs, descriptions where exposed, locations and publication metadata where supplied.
- Activation requires a verified public endpoint and explicit admin click. It enables the collector and binds the registry board ID into source metadata. First successful poll marks only that board's first inventory as baseline and cancels unattempted queued alerts; it does not replay historic jobs to Telegram. A second board on an already active source does not re-baseline other employers.
- Live public validation: Bosch Group SmartRecruiters returned 300 postings under the configured page cap (20 detailed descriptions); Hugging Face Workable returned 6 published jobs with descriptions. Each collector was run twice through `run_source` against a disposable SQLite database: first poll ingested 300/6 and marked all rows as baseline, second poll produced zero new rows; zero Telegram sends; `PRAGMA integrity_check=ok`.
- Full local V2 suite on this candidate: **377 tests passed in 224.191 seconds, zero failures**. Python compilation, JSON validation and `git diff --check` passed. Host Node is v12.22.9 and cannot parse the project's existing modern JS syntax; GitHub CI Node check is authoritative.
- A first full-suite run exposed a compatibility regression: board-baseline suppression queried the new registry table in legacy/test DBs. Fixed by making it safely no-op when the additive registry table is absent; the existing LinkedIn `partial_rate_limited` regression test then passed.
- No shared-dev or production deployment, scheduler enablement, or Telegram delivery occurred. SmartRecruiters/Workable remain disabled by default. Production remains untouched.

### Next agent — do not restart discovery work

1. Read this section, the latest PR #51 body and `docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md`. The discovery registry and two new collectors are already implemented; do not rebuild them.
2. Check exact-SHA GitHub CI run `42491830453` for `93f532c20b0dcf6b37429a65add18281c16c00f9`. Fix any failure and rerun full V2 suite; do not infer CI success from local tests.
3. Run a bounded admin UI browser QA against an isolated test DB: company scan, multiple board results, verify, activate, source status and no accidental notifications. Test that unverified/unsupported boards cannot activate.
4. Continue the requested 36-platform coverage matrix. Next priority: Darwinbox employer-by-employer public candidate endpoint research, then provider-specific adapters for the discovery-only ATS families. Do not call employer-authenticated endpoints without employer-issued credentials.
5. Add bounded concurrency/per-board scheduling and freshness/backfill/closure semantics before promising a two-minute SLA across many employers. Workday remains sequential and a board can take tens of seconds.
6. Preserve release gates: PR #51 stays draft until CI, security and browser QA pass; no shared-dev or production deployment without the separate explicit approval. Production has active Telegram/global notification state—do not modify its container, volume, config or queue.

## 2026-11-09 owner release boundary (read first)

The owner is manually testing production. **Do not modify production directly.** All code/config changes go to isolated feature branches based on latest `origin/v2-live-radar`, then exact-SHA CI, review, shared-dev deployment/QA, owner UAT, and only then separately approved production promotion. Read `docs/DEVELOPMENT_RELEASE_POLICY_AND_REPO_CLEANUP_2026-11-09.md` before any code or GitHub cleanup. Preserve the dirty VM-local checkout `/home/ubuntu/job-beeper-dev` (`v2/config.json`, `.env.save`, `.venv/`, config backup); it is behind remote and not the authoritative clean worktree. Do not reset, clean, overwrite or stage it.

Career-Ops and its extension are reference projects, not replacement architectures. Adopt evidence-based fit, job legitimacy/repost checks, truthful resume tailoring, reusable answer bank, referral research/drafts and optional browser-assisted form fill with a human submit checkpoint. Do not copy code without license review, do not build local-first CLI architecture into the hosted app, and do not automate consequential submission/outreach without approval.

GitHub audit: keep #35 as draft release gate; #46, #50 and #52 are stale/superseded candidates for closure after verifying their useful changes are in current V2. Do not merge their stale trees or mass-delete branches/worktrees. Full rationale and cleanup sequence are in the policy doc.

## 2026-11-09 — Two-role Desktop QA ready

Read `docs/QA/DESKTOP_TWO_ROLE_QA_2026-11-09.md` before browser testing. A fresh isolated synthetic QA app runs on VM loopback 8006 (local browser URL `http://localhost:18006/dashboard/`, tunnel `ssh -N -L 18006:127.0.0.1:8006 ubuntu@130.210.27.197`). Temporary accounts `qa-admin@local.test` (admin) and `qa-member@local.test` (normal user) were created and verified in that isolated DB; passwords were shared in chat only, never commit them. Four synthetic demo jobs; all collectors off, notifications off, Telegram/OAuth/LLM credentials blank. Member source-health APIs return 403; admin returns 200. Do not use old candidate 8005/18005, production 8000, shared dev 8001, experiment 8002 or connector QA 8010 for this test. Prompt and complete manual checklist are in the QA runbook. Owner and Desktop should test both roles; report gaps, do not modify code/runtime. Fix on dev first.


## 2026-11-09 — Teamtailor public RSS connector candidate (not deployed)

- Isolated branch `feat/teamtailor-public-rss-20261109` from `origin/v2-live-radar`. Adds a default-off RSS collector, provider discovery/probe, explicit admin board activation/deactivation, 300-second default interval, offset/per_page pagination (200 rows/page, cap 2,000 per board/run), Retry-After cooldown, and silent first-board baseline. Dashboard source toggle, source-health label and job-source filter are included.
- Read-only GET to Teamtailor's official documentation sample returned HTTP 200 `application/rss+xml`, 16 items; parser accepted 16/16 with publication date, description, location and HTTPS job URL. This is format validation, not proof of a populated employer board.
- Focused suite: 9/9 passed. Python compile, config JSON validation and `git diff --check` passed. Full V2 suite and exact-head GitHub CI pending.
- Status: code/research only. Source remains disabled; no board activated, no DB ingestion, no Telegram, no shared-dev deployment and no production changes. Custom branded careers domains are not auto-detected in this initial branch.
- See `docs/TEAMTAILOR_SOURCE_ADAPTER.md`.

### Parallel connector merge ordering

Recruitee PR #59, Personio PR #60 and this Teamtailor branch were independently cut from the same V2 baseline. Each source adds its own migration at config version 16 and must remain default-off. Do not merge all unchanged sequentially. After the first source merges, rebase each later PR and advance its config version/migration to the next version while preserving earlier source flags and tests. No connector should be merged or deployed solely because CI passes.
