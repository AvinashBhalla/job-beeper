# CURRENT HANDOVER — 2026-11-09 repository cleanup

**Read first:** [Repository cleanup and next-agent handover](REPOSITORY_CLEANUP_2026-11-09.md). It records the current seven open PRs, 16 remote branches, archived/deleted stale docs branches, the closed unmerged PR #35, current dev/QA image and live-feed evidence, owner QA steps, and the ordered next tasks.

The older dated notes below are retained as history and may describe earlier runtime images, branch counts or PR states. Use the newest dated checkpoint in `docs/JOB_RADAR_HANDOVER.md` and the cleanup report above as the current source of truth. The production-first/older promotion guidance in historical sections is superseded by `docs/DEVELOPMENT_RELEASE_POLICY_AND_REPO_CLEANUP_2026-11-09.md`: engineering is dev-first and production requires separate owner approval.

---

# Next Agent Start Here — Job Radar V2


## 2026-11-09 22:09 IST — current feature and live-feed rollout (READ THIS FIRST)

Current feature branch is `feat/global-ats-discovery-hirebase-guard-20261109` at `243da9c35e93979e59d0de281130581cad4124d1`; PR #65 is OPEN/DRAFT/UNMERGED. Exact-head GitHub V2 CI #1437 (`42648073320`) passed all stages. Local final V2 suite: 451 passed in 482.864s; candidate-specific API suite 11 passed.

The owner asked for the same real public feeds in non-production before prod. This is now deployed: shared dev port 8001 and connector QA port 8010 both run image `job-radar-dev-multitenant:243da9c`, image SHA `sha256:75d1f8ffe01335f35a7a7447671d2319f46edb4fcfe5eb9cf829617998de5e31`. Both use separate databases and the same production public board allowlist for eight feeds: Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka and Darwinbox. LinkedIn stays disabled outside prod due to production telemetry showing 10 HTTP 429s / 7 failed pages. Instahyre, Lever, Hirebase remain off. Notifications/Telegram/Gemini/LLM all off. Production port 8000 was not changed.

Dev has successfully completed the eight-source live pass plus follow-on cycles: 3 runs each for Ashby, Darwinbox, Greenhouse, Keka, Workable, Workday; 2 SmartRecruiters; ongoing Naukri. Last two hours: 0 429, 0 page/board failures. Latest DB 10,259 jobs, 8,221 source_runs, integrity ok, zero notification sends. QA now has two successful passes per provider: 1,891 jobs, 16 source runs, zero 429/page/board failures, integrity ok, zero sends. Second pass was a controlled run; autonomous 60-minute scheduler cycle remains to be observed.

Deployment/backups/metrics and tunnel links are fully recorded in `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md` and `docs/RECOVERY_CHECKPOINT_2026-11-09_2209_IST.md`. Use shared dev at `http://localhost:18001/dashboard/` via `ssh -N -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197`; live connector QA at `http://localhost:18010/dashboard/` via `ssh -N -L 18010:127.0.0.1:8010 ubuntu@130.210.27.197`; synthetic QA remains `http://localhost:18006/dashboard/` and is unchanged.

Connector QA currently has zero users; owner must provision QA-only users interactively (never copy prod users): `sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-admin --email qa-admin@local.test`, then `... create-user --email qa-member@local.test`. CLI prompts for passwords locally.

Next: owner UAT dev/QA + create QA admin/member; observe QA next 60-minute cycle; keep PR #65 draft pending UAT; then merge/review separately. Continue P1 per-board scheduling/host budgets, serialized Common Crawl/sitemap discovery and latency/completeness benchmarking. Do not deploy to production without separate explicit owner approval.

**Checkpoint:** 2026-11-09 22:19 IST — PR #65 and docs CI passed; candidate deployed to dev and QA with two successful live passes
**Read this first when taking over the Job Radar task.**

## Owner's product goal

Build a reliable multi-source job radar that fetches new jobs from all 36 requested platforms, filters each job separately against each user's saved preferences, and sends Telegram alerts only to matching users. The owner expects near-real-time capture (target 2-minute polling for high-priority boards where permitted; webhooks when an employer authorizes them), not a daily batch.

The required 36 platforms and source-by-source current status are in [ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md](ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md). Workday is now implemented and tested on one NVIDIA public board but remains disabled; Darwinbox is the next connector. The list mixes ATS vendors and job marketplaces; ATS feeds generally require a specific employer board/tenant, so company/career-site discovery is a core requirement.

## Current environment — supersedes older historical sections below

- Production: `v2-radar-1`, port 8000, image `job-radar-prod-canary:6e5becb`, config v15. Nine active feeds including LinkedIn; notifications/Telegram remain live. **Never touch for feature work.**
- Shared dev: `job-radar-dev`, port 8001, image `job-radar-dev-multitenant:243da9c`, candidate SHA `243da9c`. Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka and Darwinbox enabled; LinkedIn/Instahyre/Lever/Hirebase off. Notifications off. Separate persistent dev volume.
- Connector QA: `job-radar-connectors-qa`, port 8010, same immutable image SHA as dev; same eight public feed allowlists, 60-minute polling, isolated QA volume, notifications off. First full real-feed pass succeeded (1,864 jobs). No QA accounts yet.
- Synthetic browser QA: `job-radar-browser-qa`, port 8006, 4 demo jobs, two existing QA accounts, all collectors off; unchanged.
- PR #65 is open/draft/unmerged at `243da9c35e93979e59d0de281130581cad4124d1`; exact-head CI #1437 passed; local V2 suite 451 passed. Same candidate is deliberately deployed to dev/QA ahead of merge.
- Full promotion procedure, backups, runtime config precedence, poll cadences, source metrics, tunnel commands and QA-account provisioning are in `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md` and `docs/RECOVERY_CHECKPOINT_2026-11-09_2209_IST.md`.

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

## Immediate release gates

1. Owner UAT on dev 8001 and live connector QA 8010; create QA-only admin/member through the interactive CLI.
2. Observe the next 60-minute QA poll cycle for all eight providers; confirm zero 429/page/board failures, healthy DB and zero sends.
3. Review PR #65 and keep it draft until UAT/review accepted.
4. Keep LinkedIn disabled in non-production because production showed 10 HTTP 429s and 7 page failures in the preceding 24 hours.
5. Do not touch production until separate explicit owner approval.

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

## 2026-11-09 — Global ATS discovery + optional Hirebase sampler feature branch

**Branch:** `feat/global-ats-discovery-hirebase-guard-20261109` (based on `origin/v2-live-radar` at `ecb347a`). **No merge, deployment, source activation or external Hirebase request has occurred.**

### What this branch adds

- A strict optional Hirebase client (`v2/hirebase.py`) with fixed API host, env-only `HIREBASE_API_KEY`, no redirects, no import-time requests, sanitized errors and metered usage header parsing.
- Admin-only `/api/hirebase/status` and `/api/hirebase/estimate`. Estimate is a zero-job-credit endpoint and caps each query at four rows, only for Workday/Keka/Darwinbox. Key value is never returned.
- Optional `hirebase` collector, disabled in default config, daily poll. Each provider query is estimate-first, global (not filtered using a user's private role/profile), and capped at four rows/day/provider for Workday, Keka and Darwinbox.
- Persisted Hirebase usage ledger reserves estimated credits before search. Local guardrails: 400 per current billing period (100 below the 500 Free allowance), 12/day total and 4/day per provider. Timeouts, malformed success responses or missing metering confirmation retain the full reservation. HTTP 429 persists cooldown and stops remaining provider queries. Hirebase requests are included in source request telemetry.
- Config migration v16→v17 forces Hirebase off. Enabling it requires `HIREBASE_API_KEY` in the server environment. No key has been set.
- Dedicated optional env file wired in development Compose: `/home/ubuntu/.config/job-beeper/dev-hirebase.env`. The file was created with an empty placeholder and mode 600 under a mode-700 directory; never read/printed. The existing `/home/ubuntu/job-beeper-dev/.env` was not changed. Compose configuration validation passed; no container was rebuilt/restarted.
- A CC BY 4.0 LastRound AI August 2026 snapshot is bundled as `v2/data/lastroundai-ats-company-directory-2026-08.csv`: 9,935 candidate slugs (4,966 Greenhouse, 2,856 Ashby, 2,113 Lever). The source CSV, commit and blob SHA plus attribution are recorded in `v2/data/LASTROUND_AI_ATTRIBUTION.md`.
- Admin-only `/api/discovery/directories/last-round/import` imports these only as low-confidence `discovered` candidates, preserving the snapshot date. It does not verify, activate, poll, ingest jobs or alert. It reuses an existing provider/slug record instead of duplicating a manually discovered board.
- Admin-only `/api/discovery/coverage-summary` returns registry counts per provider/review state but no market-coverage percentage. Dashboard adds Hirebase estimate buttons, usage-budget display, opt-in confirmation, directory import, snapshot dates and coverage summary. Showing Coverage & Health triggers its data loaders.
- Research docs: `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md` and `docs/GLOBAL_ATS_DISCOVERY_IMPLEMENTATION_2026-11-09.md`.

### Validation

- Focused new tests: **27 passed** (`test_hirebase`, `test_ats_directory`, `test_global_discovery_hirebase`).
- Full V2 suite: **426 passed** in 416.2s at the last full regression run. This run preceded the final dashboard lazy-load/title tweak and added last assertions; rerun full suite at final HEAD before merge.
- Python compile, JSON config validation, `git diff --check`, HTML duplicate/missing ID checks, CSS variable checks and development Compose config validation passed.
- VM has Node v12.22.9, which cannot parse existing dashboard optional-chaining/nullish-coalescing syntax. Exact-head GitHub CI with the modern Node runtime is required for JS validation.

### Limits and next work

This branch is **not yet the complete autonomous global crawler**. LastRound gives candidate seeds only for Greenhouse/Lever/Ashby. Hirebase only provides a small India-focused Workday/Keka/Darwinbox sample after the key is supplied and source explicitly enabled. It does not discover every new Workday/Keka/Darwinbox tenant. No independent Common Crawl harvester, search-index crawler, complete tenant resolver or global board-to-scheduler is delivered yet.

Next: final exact-HEAD test/CI; user securely adds the key to the empty development secret file; verify `/api/hirebase/status` reports configured while disabled; use only the free estimate buttons; then, with explicit approval, enable the sampler in development. Separately build first-party Workday/Keka/Darwinbox employer discovery and board-level scheduling. Hirebase's terms restrict competing job-data products/raw redistribution; do not use it for commercial multi-user JobBeeper production without written permission.

### Open-source research shortlist

- Freehire `strelov1/freehire` — 3.4k/373 snapshot; strongest ingestion architecture reference (run-once provider workers, board catalogue, shards, idempotent upserts, cooldown, transactional outboxes).
- Career-Ops `career-ops-hq/career-ops` — about 80.6k/14.8k snapshot; strongest reverse ATS discovery/per-host concurrency reference. Its external Feashliaa company dataset is CC BY-NC; do not reuse commercially.
- `kalil0321/ats-scrapers` — 151/37; useful Python adapter/fetcher pattern.
- `Riley-Dorrington/job-board-aggregator` — 181/40; Common Crawl + daily anomaly monitoring pattern. Code MIT, curated company lists CC BY-NC; don't bundle them into commercial JobBeeper.
- JobSpy `speedyapply/JobSpy` — about 4.7k/927; supplementary job-board aggregator adapters, not global ATS directory.
- JobNavigator `vesaias/JobNavigator` — 184/52; product UX reference.

Stars are attention, not latency or rate-limit proof. Benchmark p50/p95 and 429s per host before changing concurrency. See `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md`.


## 2026-11-09 18:07 IST — recovery checkpoint after ChatGPT connection interruption

The user reported the conversation UI stuck on “Connection interrupted. Waiting for the complete answer” and supplied a screenshot. This is a ChatGPT response-stream interruption, not evidence of a JobBeeper application outage. The screenshot shows the prior answer did not finish rendering. The implementation and documentation are on the development VM; do not repeat work blindly.

### Current working state

- Repository/worktree: /tmp/job-radar-global-discovery
- Branch: feat/global-ats-discovery-hirebase-guard-20261109
- Base: origin/v2-live-radar at ecb347aef013e5249ce1270006d3bc226e111c3e
- Not pushed, no PR created, no merge or deployment.
- Files already modified/new: see git status --short --branch on the VM. git diff --check had passed before the latest watermark changes; rerun it.
- Docs already added:
  - docs/GLOBAL_ATS_DISCOVERY_IMPLEMENTATION_2026-11-09.md
  - docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md
  - v2/data/LASTROUND_AI_ATTRIBUTION.md
  - appendices in docs/NEXT_AGENT_START_HERE.md, docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md, docs/PRODUCT_VISION_AND_DELIVERY_ROADMAP.md
- User explicitly asked that findings and next steps be documented first. This checkpoint is appended to the three primary handover docs before any further implementation work.

### Last known test state — important distinction

- Before incremental cursor work and the final dashboard tweaks, a complete V2 regression run passed 426 tests in 416.2 seconds.
- The focused Hirebase/directory suite now passes 30 tests, including incremental query construction, per-provider pagination cursor state, zero-estimate advancement and candidate-only import.
- After Free-plan period handling, the Hirebase client-only suite passed 12 tests.
- A full suite job ipu4poub1j was started at 12:23 UTC but was stopped after the user interruption and subsequent code changes made its run stale. Its log /tmp/job-radar-global-discovery-final-tests.log is not a final exact-HEAD result.
- Therefore the current branch has no final test result yet. Do not claim 426 tests validates current HEAD. Rerun focused tests, then the complete V2 suite after watermark/pagination work is settled.

### Latest implementation changes since the previous handover

Hirebase incremental ingestion is now being changed to avoid repeatedly spending credits on the same rolling seven-day results:

- First run uses a bounded seven-day sample.
- Later runs use Hirebase ingested_after with sort_by=first_ingested, ascending, and a two-hour overlap.
- New hirebase_provider_state stores per-provider cursor/pagination state.
- Cursor commits are deferred until run_source has successfully upserted the jobs, to avoid advancing the cursor when DB ingestion fails.
- The schema currently includes last_polled_at, window_start, and next_page; the latest code has evolved beyond the first simple watermark patch to support paginated continuation. Inspect current code before editing; don't overwrite it with the older design.
- Current helper functions are around v2/radar.py:5687-5715; collector around v2/radar.py:5752-5881; run-source commit around v2/radar.py:5970.
- v2/hirebase.py:49-72 constructs first-run vs incremental query. normalize_provider_job retains first_ingested.
- The test test_provider_query_uses_incremental_first_ingested_cursor was added to v2/test_hirebase.py, but it may not have landed inside the test class correctly. Inspect tail -50 v2/test_hirebase.py and fix if necessary.
- Need add tests for per-provider watermark persistence, two-hour overlap, page continuation when estimated results exceed the limit, commit only after upsert, and no cursor advance on search/DB failure. Keep the result limit at or below the zero-credit estimate.
- Be careful: the previous test launch ran before the current cursor/pagination implementation. It is stale and must not be relied on.

### Safety / Hirebase status

- Hirebase source remains disabled by default; 24-hour schedule.
- No Hirebase API key has been supplied or read. The dedicated dev secret file /home/ubuntu/.config/job-beeper/dev-hirebase.env was created empty with mode 600 under a mode-700 directory. Existing shared .env untouched.
- No Hirebase API estimate/search requests have been made.
- Free plan usage API has null subscription and period dates. Code now falls back to the calendar month in UTC while requiring valid meter counters. Hirebase client test passed after this change.
- Per-query result cap must remain no larger than its estimate. Local guardrails: 400/month, 12/day overall, 4/day/provider.
- Hirebase Terms restrict competing job-data products and raw redistribution. Do not enable for commercial multi-user JobBeeper production without written permission. The UI requires explicit confirmation before enabling and estimate buttons remain disabled without a key.

### Candidate discovery status

- LastRound AI August 2026 CSV snapshot is CC BY 4.0 and has exactly 9,935 rows: 4,966 Greenhouse, 2,856 Ashby, 2,113 Lever.
- Import creates low-confidence, unverified candidates only; does not activate or poll boards. Reuses existing provider/slug rows.
- Snapshot is dated; verify endpoints before activation. No total market coverage percentage is claimed.
- This still does not deliver autonomous employer/tenant discovery for Workday/Keka/Darwinbox. Hirebase is only a tiny India-focused sample for those providers.

### Immediate next steps (do these in order)

1. Inspect/fix v2/test_hirebase.py method placement and review the current incremental cursor/pagination code.
2. Add focused tests for cursor persistence/commit semantics and pagination. Ensure estimate-first and hard caps are intact.
3. Run focused Hirebase/directory tests and git diff --check, compile Python, validate JSON and Compose.
4. Run the full V2 suite at exact final HEAD. If long-running, use a background job and poll until completed; do not abandon it.
5. Validate dashboard JS using GitHub Actions/modern Node. VM Node 12 cannot parse existing optional chaining/nullish-coalescing syntax; do not rewrite unrelated JS to satisfy that old runtime.
6. Update the implementation note and all three handovers with exact final test count, commit SHA, CI run and any remaining blockers.
7. Only then push branch and create/update a draft PR. No deployment, no Hirebase activation, no key setup or live source enablement without explicit user approval.
8. Future P0 after this branch: implement first-party global Workday/Keka/Darwinbox company/tenant discovery and a verified-board-to-scheduler pipeline. Use Freehire's provider-isolated workers/outboxes, Career-Ops reverse discovery/per-host concurrency, and ats-scrapers fetcher contracts as architecture references. Do not reuse CC BY-NC company datasets from Career-Ops/Riley aggregator commercially.

### Open-source shortlist

See docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md for details. Leading references: Freehire (ingestion architecture), Career-Ops (reverse discovery and per-host concurrency; dataset is CC BY-NC), ats-scrapers (Python adapters), Job Board Aggregator (Common Crawl and anomaly monitoring; bundled dataset CC BY-NC), JobSpy (non-ATS board adapters), JobNavigator (product UX). Stars are popularity, not latency/rate-limit proof.

## PR and commit checkpoint — 2026-11-09 18:50 IST

- Commit: 533c889574bb6daddece8121c66f208c6fcec8de (`feat: add guarded global ATS discovery foundation`).
- Branch pushed: `feat/global-ats-discovery-hirebase-guard-20261109`.
- Draft PR: https://github.com/AvinashBhalla/job-beeper/pull/65 (base `v2-live-radar`).
- Full V2 regression: 430 tests passed in 385.001 seconds; background job `bjo6lrjfig` exit code 0. Focused discovery/Hirebase suite: 30 passed. Python compile, JSON, Compose config and diff checks passed.
- Superseded CI note: exact-head GitHub Actions V2 CI run #1427 (42620547252) passed on 999b66543ac162346d42cd3be2c39993c0475a6e, including dashboard JavaScript syntax and the full V2 test suite.
- PR remains draft/open, unmerged. No deployment or Hirebase requests/activation.\n

## 2026-11-09 18:10 IST — verified CI and updated research

PR #65 is still **open and draft**, mergeable, based on v2-live-radar. Current head is 999b66543ac162346d42cd3be2c39993c0475a6e. Exact-head GitHub Actions V2 CI run #1427 / ID 42620547252 completed successfully, including dashboard JS syntax, focused tests and the full V2 unittest suite. The local full suite is 430/430 (385.001s); focused new tests are 30/30.

The expanded open-source comparison is in docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md. New high-value finding: current kalil0321/ats-scrapers has Workday, Keka and Darwinbox adapters. Workday uses facet subdivision to address the 2,000-result query cap; Keka exposes credential-free public career portal JSON endpoints; Darwinbox's adapter uses httpcloak for a Cloudflare-protected endpoint. Do not adopt TLS impersonation to evade an anti-bot control. The library's shared Fetcher does Retry-After-aware 429/5xx retries and explicit 403/406 handling. This makes it the best Python provider reference, but not a dependency we should blindly import.

Job Forager's company-list expansion and Workday pagination are useful to study, but inspected HTTP clients disable TLS certificate validation, broadly swallow exceptions and use fixed concurrency rather than persistent host budgets. Do not copy those transport choices. JobSpy is for supplementary job boards and explicitly warns about 429s; it is not a global ATS discovery source.

### Next priorities

1. Keep PR #65 draft while we review the latest research note and migration ordering across sibling branches.
2. Build an independent, compliant public-board candidate harvester for Workday/Keka/Darwinbox using career-link/sitemap/Common Crawl and trusted directory seeds, with provenance recorded.
3. Reuse/adapt the allowed Keka public portal extraction pattern and Workday facet-aware pagination. Do not enable the Darwinbox Cloudflare-bypass path; require a documented/public authorised route.
4. Turn verified candidate boards into a per-board queue with host-aware concurrency, Retry-After, persistent cooldown, jitter, backpressure and page/facet checkpoints.
5. Run controlled p50/p95, 429, incomplete-page, first-seen-delay and freshness benchmarks before increasing concurrency.
6. Hirebase remains an optional, dev-only sample until the user supplies a key securely and approves estimate-only testing. Do not use its data in a commercial multi-user product without written permission.

Do not merge or deploy this branch as an assertion that JobBeeper now has complete global ATS coverage. It is the quota-safe sampling and candidate-directory foundation; independent Workday/Keka/Darwinbox employer discovery and full board scheduling remain outstanding.

## Latest recovery checkpoint

Start with `docs/RECOVERY_CHECKPOINT_2026-11-09_1810_IST.md` for verified branch/PR/CI state, completed work, research findings, safety boundaries and next tasks.


## 2026-11-09 18:15 IST — direct collector gap analysis

New document: docs/ATS_PROVIDER_GAP_ANALYSIS_2026-11-09.md. This compares JobBeeper's actual v2/radar.py collectors against the researched ats-scrapers implementations.

Concrete gaps:
- Workday in JobBeeper currently has WORKDAY_PAGE_SIZE=20 and WORKDAY_MAX_PAGES_PER_BOARD=1. It only polls the first 20 jobs and has no facet partitioning for large tenants. ats-scrapers explains the hidden 2,000-result per-query cap and uses jobFamilyGroup/timeType/locations/workerSubType partitions.
- Keka in JobBeeper extracts the public document/feed ID but hardcodes /careers/api/embedjobs/default/active/{id}. ats-scrapers resolves the actual portal path and may call /organization/{portal}/careerportalinfo before the matching portal-specific embedjobs endpoint.
- Darwinbox in JobBeeper already uses a bounded candidate-site collector and only detects .darwinbox.in boards. Its current code does not use TLS impersonation. The ats-scrapers implementation pins httpcloak against Cloudflare; this is explicitly not approved for reuse. A 403 must remain blocked/not verified unless an authorized documented access path exists.
- The three collectors still poll source-level config arrays. Board-specific next_due_at, host concurrency budgets, independent backoff/cursors, and a full inventory completion signal are not yet implemented.
- The directory seed import covers Greenhouse/Ashby/Lever only; Hirebase is not an employer directory. Automatic public employer/tenant discovery for Workday/Keka/Darwinbox remains P0 outstanding.

Next implementation order is now more precise:
1. Workday: retain fast first-page incremental polling; separately add low-frequency facet-aware full inventory, persisted page/facet checkpoints, completeness and truncated-reason fields.
2. Keka: resolve actual portal slug from URL, validate it, call matching public portal-info and embed endpoints, test at least two non-default public portals, and add truncation/paging handling.
3. Darwinbox: preserve .in-only candidate shape and tenant-specific verification; classify 403 separately from 429; no Cloudflare/TLS bypass.
4. Global discovery: career links + sitemaps + Common Crawl CDX candidate seeds with provenance, confidence and stale-candidate handling.
5. Per-board queue: host-aware concurrency, per-board due times, Retry-After, cooldown, jitter, backpressure and observable queue age.
6. Benchmark completeness, p50/p95, 429s and first-seen delay before raising concurrency.

This addendum is static code review and does not change collectors, activate sources, contact ATS providers or spend Hirebase credits.
---

## 2026-11-09 — Workday inventory implementation checkpoint

**Branch:** feat/global-ats-discovery-hirebase-guard-20261109
**Worktree:** /tmp/job-radar-global-discovery
**Current code:** Workday incremental inventory implementation is in the worktree and under full regression testing. It has not been deployed.

### Completed in this work session

1. Added durable SQLite table workday_board_poll_state, keyed by normalized tenant:site, with next inventory offset, last attempt, last full inventory, reported total, provider facets metadata, completion state and truncation reason.
2. Preserved the fast first Workday page on the existing source poll interval (default 120 seconds).
3. Added one optional inventory page per board no more often than every 15 minutes. The first pass starts at offset 20; subsequent attempts resume the saved cursor.
4. Kept detail page requests limited to the fast freshness page. The slower inventory page adds only one list request and derives basic location from listing fields if detail data is absent.
5. Inventory cursor state is held pending and committed only after upsert_jobs succeeds. A failed inventory page does not advance its offset; its attempt timestamp is persisted so a 120-second source cycle does not hammer the failed page.
6. Existing Workday 429 Retry-After/cooldown behaviour remains in force.
7. A short final page or a reached reported total below 2,000 marks a sweep complete; completed sweeps are rechecked weekly.
8. A response at the 2,000-result ceiling, an early empty page inconsistent with that ceiling, or the local 2,000 offset safety cap is marked truncated/incomplete. The code does not claim full inventory. Facet subdivision remains the next Workday completeness task.
9. Added admin-only GET /api/workday/inventory-status and Coverage & Health panel UI that shows board, status, reported total, facet count, next offset and truncation reason.
10. Added tests for persisted cursor commit, first-page cadence, inventory throttling, advancing offsets, failed-page retry throttling, weekly refresh, 2,000-cap truncation and admin-only status.

### Current validation

- Focused tests: 31 passed across Workday collector and global discovery/Hirebase suites.
- Full V2 test suite is currently running; do not report a final count until job completion.
- Python compilation and git diff --check passed on the current implementation.
- VM Node is v12 and cannot parse the dashboard's existing optional chaining/nullish-coalescing syntax. Use exact-head GitHub V2 CI for dashboard JS syntax.
- No production/shared-dev changes, service restarts, source activation or Hirebase requests occurred.

### Next implementation priorities (updated)

**P0**
1. Workday facet-aware full inventory. The current cursor paginates up to the 2,000 reported-result ceiling and surfaces truncation; it does not yet partition jobFamilyGroup, timeType, locations or workerSubType.
2. Keka actual portal slug resolution. Current collector still hardcodes default in /careers/api/embedjobs/default/active/{id}. Implement safe path parsing, optional portal-info call and matching portal-specific embed endpoint; test at least two non-default public boards.
3. Independent Workday/Keka/Darwinbox employer/tenant discovery. The seed directory in PR #65 only covers Greenhouse/Lever/Ashby; Hirebase is not a complete tenant directory.
4. Per-board scheduling: due queue, host budget, jitter, persistent cooldown, independent retry/page state and queue-age visibility. Current source-wide scheduler remains a limitation.

**P1**
5. Darwinbox per-board 403/429/5xx classification and re-verification. Keep blocked 403 visible. No Cloudflare/TLS impersonation or anti-bot bypass.
6. Benchmark p50/p95 HTTP latency, 429 rate, pages attempted/completed, jobs available vs fetched, first-seen delay and user-feed lag on verified canary boards.
7. Extend freshness/stale/repost and job legitimacy checks once collection completeness and telemetry are reliable.

**P2**
8. Broader ATS adapters only after the provider registry, scheduler and health contracts are in place.
9. Hirebase estimate-only development experiment only after the user adds the key to the dedicated server-side file and explicitly approves testing. Do not use Hirebase for a commercial multi-user product without vendor permission.

### Required from the user

Nothing is required right now. Do not ask for credentials in chat. The Hirebase key remains absent; the server-side development env file is an empty placeholder. Only request the key be added securely when estimate-only validation is actually ready and the user approves it.

### Safe continuation

After the full suite completes, fix any regression, commit the Workday code + tests + UI, push the same PR #65 branch, update the PR description and this handover, and verify exact-head GitHub CI. Keep PR #65 draft until the Workday/Keka/global-discovery milestones have received their own review. Do not merge/deploy solely because CI passes.

Latest work in progress: see docs/WORKDAY_INCREMENTAL_INVENTORY_2026-11-09.md for the design and the Workday inventory implementation checkpoint appended to the recovery document for current test status and next priorities.
## Next adapter implementation note

After Workday full-suite validation, continue with `docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md`. It contains the exact default/non-default portal behavior, safe URL rules, reference adapter findings and required tests.\n
## 2026-11-09 19:37 IST — Workday inventory implementation verified locally

Workday now preserves offset 0 on the existing 120-second freshness poll and adds a durable per-board cursor that fetches at most one extra page every 15 minutes. Cursor advances only after upsert; failed pages are throttled without advancing; boards at the 2,000-result cap are explicitly marked incomplete. An admin-only inventory-status API and Coverage & Health panel expose progress. This is not facet-aware full inventory.

Validation: full V2 suite 436 passed in 398.870s (exit code 0); focused Workday/global discovery tests 31 passed. Python compileall, JSON config validation, git diff check and HTML panel wiring passed. Exact-head GitHub CI remains required after push.

Next priorities: Workday facet subdivision; Keka non-default portal slug support; independent public Workday/Keka/Darwinbox employer discovery; per-board scheduler/host budgets; controlled p50/p95 and 429 benchmarks. Darwinbox 403 must remain blocked, with no Cloudflare/TLS bypass.

User action: nothing required now. Hirebase key remains absent and source flags remain off.

Latest checkpoint: docs/RECOVERY_CHECKPOINT_2026-11-09_1947_IST.md. Keka plan: docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md.\n

Latest recovery checkpoint: docs/RECOVERY_CHECKPOINT_2026-11-09_1937_IST.md.

## Latest continuation — 2026-11-09 19:47 IST

Read `docs/RECOVERY_CHECKPOINT_2026-11-09_1947_IST.md` first. Workday incremental inventory is pushed in commit `6197446` and exact-head GitHub V2 CI #1430 passed. Keka non-default portal support was pushed as afa177b; exact-head V2 CI #1431 passed. Focused board-discovery tests passed 37/37; full V2 regression passed 439/439 in 359.301 seconds. Next: Workday facet-aware partitioning, company-agnostic Workday/Keka/Darwinbox discovery, and a persistent per-board scheduler. No user action is required; Hirebase key remains absent and sources remain disabled.

## 2026-11-09 20:10 IST — Workday facet-aware inventory in progress

The next P0 implementation is now in the worktree. JobBeeper reads Workday facet metadata using the upstream response shape (`facetParameter`, `values[].id`, `values[].count`) and schedules partitions in the order jobFamilyGroup → timeType → locations → workerSubType. It does not copy the upstream library's concurrent fan-out: JobBeeper keeps one inventory page per board per 15-minute interval, a maximum facet depth of 4 and a queue budget of 500.

State is persisted per tenant:site in SQLite (`facet_queue_json`, `active_facets_json`, depth, active-query flag and partition-started flag), with migration helpers for existing tables. The fast 120-second offset-0 poll and detail cap remain unchanged. Stable external IDs + idempotent upsert deduplicate overlapping multi-tag partitions. Incomplete leaves (2,000 cap with no safe next facet, depth limit, no usable facet or queue-budget overflow) remain incomplete.

Admin status/UI adds pending partition count and active filters. Focused Workday collector suite: 21 passed. Full V2 regression job `4c646ih8lj` is running; log `/tmp/job-radar-workday-facets-full-tests.log`. This code is not yet committed/pushed. Read `docs/RECOVERY_CHECKPOINT_2026-11-09_2010_IST.md` for exact continuation instructions.

Latest authoritative checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2010_IST.md`.

Workday facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.


## 2026-11-09 20:18 IST — Workday facet partitioning implemented locally

The Workday collector now builds a persisted FIFO facet queue when an unfiltered query hits the 2,000 cap and exposes `jobFamilyGroup`, `timeType`, `locations`, `workerSubType` partitions in priority order. Capped child queries recursively subdivide on an unused facet. It is deliberately sequential (one extra inventory page per board per 15 minutes), with depth cap 4 and queue cap 500. Incomplete leaves/overflow remain incomplete. Queue/active filters are migration-safe SQLite state and commit after upsert. Admin API/UI show pending partitions and active filters.

Validation: focused Workday tests 22 passed; full V2 suite 443 passed in 402.776s; compileall, JSON, diff check and dashboard HTML/panel checks passed. Exact-head CI remains required after push. No live ATS calls; actual tenant facet shapes still require an approved canary. Details: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`; latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2018_IST.md`.

Latest authoritative checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md`.


## 2026-11-09 20:25 IST — exact final Workday facet tree

The current uncommitted Workday facet implementation now includes the final admin status distinction for `in_progress_incomplete` versus terminal `truncated`. Focused Workday tests are 22/22. The earlier full V2 run passed 443 tests in 402.776s but began before the final status test was added. A second full-suite job `3tjy6iwusp` is running against the exact final tree; see `/tmp/job-radar-workday-facets-final-tests.log`. Run exact-head GitHub CI after push for modern dashboard JS and final full-suite validation.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md`. Facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.

## Next company-agnostic discovery design (2026-11-09)

New design note: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Research confirms Common Crawl CDX is heavily rate-limited: serialize requests, no proxies, sleep between calls, and stop for 24 hours after an IP block/503. For broad/high-volume filtering, use the Parquet URL Index via Athena/Spark/Polars/DuckDB rather than frequent CDX wildcard sweeps. The next code step should create a separate unmatched ATS candidate table because current `ats_board_registry` requires a real company ID; do not manufacture employer identities from tenant slugs. Candidate URLs must preserve crawl provenance, be live-verified, and only then linked to the employer board registry.

## Latest authoritative handover — 2026-11-09 21:11 IST

Read `docs/RECOVERY_CHECKPOINT_2026-11-09_2111_IST.md` first.

- Feature branch: `feat/global-ats-discovery-hirebase-guard-20261109`; PR #65 remains open/draft/unmerged.
- Workday facet-aware inventory is pushed in `4d75138`; exact-head V2 CI #1435 passed; local V2 444 passed.
- Keka multi-portal support is pushed in `afa177b`; exact-head V2 CI #1431 passed; local V2 439 passed.
- Current unmatched ATS candidate staging API/UI/tests are implemented locally but uncommitted. Full V2 suite passed **451 tests in 501.840 seconds** (`lkscpl0ioe`); focused candidate API suite 11/11 passed. Compileall, JSON, HTML ID/panel checks and `git diff --check` passed.
- Candidate staging does not create employer rows or normal ATS registry rows. Linking requires an existing employer and only creates/reuses a `discovered` board; verification/activation are separate.
- Next: commit/push candidate staging, update PR body, verify exact-head GitHub V2 CI; then implement serialized Common Crawl CDX and sitemap/career-link candidate discovery, followed by safe live verification and a per-board scheduler.
- Nothing required from user. Hirebase key absent; Workday/Keka/Darwinbox/Hirebase all disabled. No live ATS/Common Crawl/Hirebase requests, deployments or notifications.

Read `docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md` for implementation detail and `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md` for the Common Crawl plan.

Latest authoritative checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2111_IST.md`.


## 2026-11-09 — connector QA autonomous cadence checkpoint

The next autonomous 60-minute connector-QA run was observed at 17:05:04 UTC, following the initial scheduled run at 16:05:03 UTC. Eight of eight sources succeeded: 1,879 seen, 25 new, 55 HTTP 200 responses, zero 429/request/page/board failures. QA DB: 1,916 jobs, 24 source_runs, canonical/evaluation/notification-ledger rows 1,916, integrity `ok`, sent notifications 0, users/preferences 0. The autonomous-cycle gate is complete for one interval. Next owner action: create QA-only admin/member accounts interactively and execute role/tenant-isolation UAT on port 8010. Detailed per-source counts are in `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md` and `docs/REPOSITORY_CLEANUP_2026-11-09.md`.

## 2026-11-09 — next branch: persistent per-board ATS scheduler

Continue from branch `feat/per-board-scheduler-20261109` in `/tmp/job-radar-board-scheduler` (stacked on global-discovery branch `feat/global-ats-discovery-hirebase-guard-20261109` at `751e9d2`). Read `docs/PER_BOARD_SCHEDULER_2026-11-09.md` first. Implemented: SQLite per-board due times and host leases/cooldowns; one-board scoped collector runs; three-host global concurrency cap; per-board failure backoff; board-level initial-snapshot baseline; admin-only `/api/discovery/scheduler/status`; Source Health dashboard panel; immediate DB sync on activate/deactivate. Dev/QA/prod deployments are unchanged. Before PR: finish full V2 suite, run CI syntax and dashboard checks, build a new candidate image without replacing existing tags, run an isolated QA container and have ChatGPT Desktop execute visual/API/browser QA. Do not merge/deploy until test report is reviewed. See scheduler design note for safety constraints and limitations.

### Candidate environment for Desktop QA (2026-11-09)

A separate candidate image/container is built and running: `job-radar-board-scheduler:candidate` / `job-radar-board-scheduler-qa`, loopback port `18011`, isolated volume `job-radar-board-scheduler-qa-data`, notifications disabled. It completed a 10/10 board first pass (1,660 jobs, 53/53 HTTP 2xx, no 429/request/page/board failures, integrity ok, no notifications sent). Private Termalin internal-site access was created for owner access. See `docs/CANDIDATE_QA_SMOKE_2026-11-09.md`. Owner must create test admin/member accounts via `v2.auth_admin` CLI before role-based browser checks.

## Continuation checkpoint — 2026-11-10 09:28 IST

This is the latest verified state after the prior chat hit a delivery timeout. The agent was verifying the final CI test count; CI had in fact completed successfully.

- Feature branch: `feat/per-board-scheduler-20261109`.
- Feature commit: `06a2ca472c4cc8368b27c4c8ee4a86aa91a6eb1e`.
- Draft PR: [#66](https://github.com/AvinashBhalla/job-beeper/pull/66), stacked on draft PR #65 (`feat/global-ats-discovery-hirebase-guard-20261109`). Review/merge #65 first, then #66. No deployment or merge has occurred.
- Exact-head GitHub Actions V2 CI: run #1444 (`42676092793`) passed on `06a2ca4`. The completed `syntax` job shows Python compile, dashboard JS syntax, focused router/extractor tests and full V2 unittest suite all succeeded. The downloaded job log reports **466 tests in 60.421 seconds; OK**.
- Local targeted scheduler/discovery suite: **52 tests passed** after the final retained-history baseline and cooldown tests.
- Candidate image: `job-radar-board-scheduler:candidate`, image digest `sha256:339bd42f54e3f51beedba1a576a55861f992f381d89a54e261505aa5c1b6429c`.
- Candidate container: `job-radar-board-scheduler-qa`, loopback-only `127.0.0.1:18011`, isolated volume `job-radar-board-scheduler-qa-data`; it was rebuilt from the exact feature commit and restarted without replacing dev, connector-QA, synthetic-QA or production. Private Termalin internal-site access was created for owner browsing.
- Candidate first-pass live-feed result: **10/10 boards succeeded** across eight ATS providers; 1,660 jobs observed; 53/53 HTTP 2xx; zero 429s, request exceptions, page failures or board failures; SQLite integrity `ok`; all 10 baselines cleared; no sent notifications. Seven API hosts were represented. Workday had 15 facet partitions queued, so its total inventory remains explicitly incomplete.
- Dashboard JS syntax passed with Node 22; `/dashboard/`, `/dashboard/app.js` and `/dashboard/auth.js` returned HTTP 200. Anonymous scheduler telemetry returned HTTP 401 as expected.
- The isolated candidate has no test users yet. Owner-created QA-only admin and member accounts plus a Desktop browser report are the outstanding acceptance tasks. Exact commands and a browser test prompt are provided in the continuation response. Do not place passwords in command-line arguments or paste them into chat.

Next work: have the owner provision QA-only accounts and run the Desktop browser prompt against the isolated candidate. Review the report, fix any issues, update this file and the smoke-test report, then keep #66 draft until the owner accepts the browser QA. Only after #65 is merged should #66 be retargeted/rebased and considered for merge. Do not deploy to dev/QA/prod merely because CI passed.

## Extended autonomous scheduler observation — 2026-11-10 09:30 IST

A later read-only inspection confirms the candidate continued operating after the initial smoke test rather than merely remaining healthy. The isolated container has remained up with restart count zero. It recorded 100 source runs across the 10 scheduled boards during the overnight observation window. Per-source records are consistent with ten polls per board: Ashby 20 runs for two boards, Greenhouse 30 runs for three boards, and one board each for Darwinbox, Keka, SmartRecruiters, Workable and Workday (10 runs each).

| Provider | Board count | Source runs | Aggregate jobs seen | Aggregate new jobs | Requests | 429 / exceptions / page failures / board failures |
|---|---:|---:|---:|---:|---:|---|
| Ashby | 2 | 20 | 8,270 | 839 | 20 | 0 / 0 / 0 / 0 |
| Darwinbox | 1 | 10 | 356 | 36 | 10 | 0 / 0 / 0 / 0 |
| Greenhouse | 3 | 30 | 3,685 | 371 | 30 | 0 / 0 / 0 / 0 |
| Keka | 1 | 10 | 1,090 | 109 | 20 | 0 / 0 / 0 / 0 |
| SmartRecruiters | 1 | 10 | 2,999 | 319 | 230 | 0 / 0 / 0 / 0 |
| Workable | 1 | 10 | 60 | 6 | 10 | 0 / 0 / 0 / 0 |
| Workday | 1 | 10 | 362 | 201 | 219 | 0 / 0 / 0 / 0 |
| **Total** | **10** | **100** | **16,822** | **1,881** | **539** | **All zero** |

These are cumulative *observations*, not unique jobs. The database contains 1,881 unique job rows and 1,881 notification-ledger rows. Every board's latest outcome is success, every consecutive failure count is zero, all 10 baselines are clear, all 7 host records have no active lease, no HTTP 429 was recorded, no notifications have been sent, no QA users exist yet, and SQLite integrity remains `ok`. Container health returns HTTP 200 and restart count is zero. The most recent run records are spread across the providers at the expected staggered times.

This is extended cadence evidence, but it is still one isolated candidate configuration and not a production load/SLA certification. The Desktop browser/admin/member acceptance is pending.

For owner-driven ChatGPT Desktop browser QA, read `docs/DESKTOP_QA_PROMPT_2026-11-10.md`. It contains the interactive QA account provisioning commands, safe test boundaries, admin/member authorization checks, responsive viewport matrix and report format. Do not ask the owner for passwords in chat or include them in evidence.

## Final exact-head CI result — 2026-11-10

- Latest code/docs head before this documentation-only result entry: `e3a9be13abd69b023ea7d2f0703b47f0beeb00a4`.
- GitHub Actions V2 CI **run #1446** (`42753221761`) completed successfully on that exact SHA: https://github.com/AvinashBhalla/job-beeper/actions/runs/42753221761
- The successful job ran Python compilation, dashboard JavaScript syntax, focused router/extractor tests (32), and the full V2 unittest suite (**466 tests in 62.218 seconds, OK**). Do not confuse the focused 32-test subset with the full suite.
- The branch's final documentation-only changes do not modify application code; the code and browser assets tested by #1446 are unchanged.

## 2026-11-10 — Desktop QA follow-up

See docs/DESKTOP_QA_FOLLOWUP_2026-11-10.md. The previously blocked anonymous scheduler request is now independently proven to return HTTP 401 with no cookie. Updated evidence totals: PASS 11 / FAIL 0 / BLOCKED 5 / UNKNOWN 4. Admin reload, post-handoff admin viewport tests, and exported PNGs remain pending; do not claim release acceptance. Automation-only test users ids 3/4 were disabled; owner QA accounts ids 1/2 remain active.


## 2026-11-10 13:25 IST — evaluation fingerprint defect found and fix underway

- PR #68 telemetry release is merged and deployed to dev/connector QA (image `job-radar-dev-multitenant:1763673`).
- Natural dev samples showed Ashby evaluation median ~52.8s (7 runs) and Greenhouse ~47.2s (11 runs), with request medians ~1.4s and ~1.2s.
- Read-only audit: dev 10,815 jobs / 10,815 evaluations, all fingerprints differed from the global fingerprint. QA 2,400 jobs/evaluations and zero mismatches at audit time.
- Cause: per-board scheduler scopes board/source configuration, but `_config_fingerprint()` hashed the entire config. Each ATS board poll therefore caused a full inventory re-evaluation.
- Fix branch: `fix/stable-evaluation-fingerprint-20261110`, commit currently includes regression code and handover notes. Fingerprint now contains only matcher/alertability inputs plus matcher rules version. Added tests for board/operational stability and evaluation-setting invalidation.
- Focused tests: fingerprint regressions 3/3 pass; full `MatcherTests` class 97/97 pass. First broad local suite attempt exposed an environment mismatch (the runtime image omits the CI-only `httpx2` dependency) and one legacy assertion that expected a deprecated, unused setting to force a redundant refresh. Updated that assertion to require no refresh; the CI-equivalent full suite is rerunning after installing `v2/requirements-dev.txt`'s `httpx2` dependency in an ephemeral container as Termalin job `cs6l7m3y3s`.
- Next: confirm full suite; inspect diff; update handover; commit/push any final docs; open PR to `v2-live-radar`; wait exact-head CI; merge only on green; deploy dev first, then connector QA. Keep rollback images and backups. Do not touch prod, cadence, concurrency, rate limits or notification settings.
- After deployment, allow ordinary scheduled runs to perform the one-time evaluation fingerprint migration. Confirm mismatch count reaches zero and remains zero after later board polls; compare phase timings before/after. No manual refresh.
