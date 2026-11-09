# Global ATS discovery + optional Hirebase sampler — implementation checkpoint

**Date:** 2026-11-09
**Branch:** feat/global-ats-discovery-hirebase-guard-20261109
**Base:** origin/v2-live-radar at ecb347aef013e5249ce1270006d3bc226e111c3e
**Status:** feature branch only; default-off; no Hirebase API key configured; no live Hirebase request made; no production/shared-dev changes.

## 1. Delivered in this branch

### Hirebase client and optional scheduled sampler

- New v2/hirebase.py client with fixed API origin, request timeout, redirects disabled, sanitized errors, and API key read only from HIREBASE_API_KEY.
- No network calls at import time. No API key is returned by status endpoints or written to config, SQLite, logs, screenshots or browser code.
- Admin-only GET /api/hirebase/status reports whether a key is configured, whether the source is enabled, local budget counters, last metered remaining value, and poll interval.
- Admin-only POST /api/hirebase/estimate accepts only Workday/Keka/Darwinbox and a result limit of 1–4. It calls the zero-job-credit estimate endpoint; it never calls the metered search endpoint.
- Scheduled source hirebase is disabled by default and has a 24-hour poll interval.
- Each daily run first reads Hirebase's billing usage summary, then estimates each provider, then checks local budgets and reserves estimated credits in SQLite before a search.
- Initial sampler is India-only and broad by platform (it does not use a user's target titles, CV, skills or saved preferences). It fetches at most four result rows per provider per run: Workday, Keka and Darwinbox.
- Local hard budgets: 400 results per Hirebase billing period, 12/day overall and 4/day/provider. With the Free plan's 500-job allowance this leaves a 100-job safety buffer. These are internal conservative limits, not plan limits.
- Quota reservation ledger records provider, estimate, actual returned rows, Hirebase period, metering headers and request status. Timeout/connection uncertainty and malformed successful responses retain the full estimate as reserved; only a verified metered response replaces the estimate with the actual result count.
- HTTP 429 sets a persisted cooldown and stops remaining provider queries. 401/403 fail closed; estimate failures do not silently start a search.
- The source uses the standard JobBeeper normalization, persistence, dedupe and telemetry paths. Hirebase IDs are namespaced by ATS provider to avoid cross-platform ID collisions.

### Licensed candidate-board directory

Bundled file: v2/data/lastroundai-ats-company-directory-2026-08.csv

Source: LastRound AI, ATS Company Directory (August 2026).
Source commit: 2816bfadd65b7bbec23701dd036bcc7496c729db.
File blob SHA: 94d01f1d42ae225a97df4df39c755e294d9f1502.
Licence: CC BY 4.0. Attribution and a link to the source are retained in v2/data/LASTROUND_AI_ATTRIBUTION.md.

Exact parsed inventory:
- 9,935 candidates total.
- Greenhouse: 4,966.
- Ashby: 2,856.
- Lever: 2,113.

New v2/ats_directory.py validates the pinned CSV schema, file size, provider allowlist, slug and date, and deduplicates provider/slug pairs.

Admin-only POST /api/discovery/directories/last-round/import inserts or refreshes registry candidates only. It:
- Stores source URL and last-crawled snapshot date.
- Gives imported candidates low confidence and review_status=discovered.
- Does not verify a live endpoint, activate a source, poll a board, ingest a job or send notifications.
- Reuses an existing board entry if the same provider/slug has already been discovered manually, rather than creating another employer row.
- Never imports Workday, Keka or Darwinbox because this snapshot does not contain them.

Admin-only GET /api/discovery/coverage-summary reports known registry boards and counts by provider/review status. It intentionally returns no market-coverage percentage because there is no verified denominator for all global employers.

### Development secret wiring and admin UX

- v2/docker-compose.dev.yml optionally reads /home/ubuntu/.config/job-beeper/dev-hirebase.env. This is a dedicated secret file; the existing shared .env is not modified.
- Config migration version 17 adds source_enabled.hirebase=false and poll_seconds.hirebase=86400.
- The validator refuses to enable Hirebase unless HIREBASE_API_KEY is present in the server environment.
- Admin UI has an Hirebase budget panel and three estimate-only controls, plus a local directory-import action and a provider/board coverage summary.
- No secret has been written to the VM and no API key has been read or used in this work.

## 2. Explicit limitations — do not overstate global discovery

This is a foundation and bounded sampler, not yet a complete global employer-discovery engine.

- The LastRound snapshot covers Greenhouse, Ashby and Lever only. It is a dated candidate directory, not a live inventory. Each board still needs endpoint verification.
- Hirebase supplies limited India-focused job samples for Workday/Keka/Darwinbox when enabled. It is not used to crawl or enumerate all employers on those platforms in this branch.
- No new automatic Common Crawl harvester or independent Workday/Keka/Darwinbox tenant directory is implemented here.
- Employer-specific Workday/Keka/Darwinbox public boards still need tenant/slug/site discovery. Private, internal or authenticated-only portals remain out of scope for anonymous crawling.
- The normal collector architecture still uses verified/activated employer boards. The full board-registry-to-provider scheduler and automatic high-confidence activation workflow are subsequent work.
- Hirebase's Free quota is 500 returned jobs/month and 50 companies/month as shown by the user's plan screenshot. The implementation does not attempt a 500-result full crawl.
- The initial Hirebase query is India-scoped for this proof of coverage, not a claim of global ingestion.
- Hirebase's Terms restrict competing job-data products and raw data redistribution. Do not enable the source for commercial multi-user JobBeeper production until written permission confirms the intended use. Internal dev evaluation remains disabled until the user supplies the key.
- No Hirebase search or estimate call has been performed; there is no empirical provider coverage result yet.

## 3. Why this quota policy is conservative

Free plan: 500 jobs/month. JobBeeper's local ceiling is 400/month, leaving 100 jobs for a safety buffer. Initial sampling is at most 4 per provider/day and 12/day overall. Every search is preceded by the free estimate endpoint. The metered usage summary and response headers are checked, and a local reservation is inserted before a metered request.

An uncertain request retains its estimated reservation because it may have consumed credits even when the response did not reach JobBeeper. This deliberately prefers under-use over unexpectedly exhausting the Free allowance.

Estimate queries and usage-summary reads consume API request capacity but not job-result credits. Hirebase's general API rate limit is distinct from its monthly job allowance; rate-limit responses receive cooldown handling.

## 4. Validation

Focused tests:
- v2.test_hirebase: API client shape, no-redirect behavior, usage summary, estimate endpoint, metered headers, budget calculations, timestamp parsing and normalization.
- v2.test_ats_directory: dataset schema, URL/provider/date validation, duplicate handling and stable registry key.
- v2.test_global_discovery_hirebase: quota reservation lifecycle, 400/12/4 ceilings, uncertain request reservation, estimate-before-search, 429 stop/cooldown, config default-off/migration, admin-only estimate/status and candidate-only directory import.

Full V2 suite status is recorded in the branch handover after completion. No live ATS or Hirebase requests are part of the test suite.

## 5. Next steps

1. User privately adds HIREBASE_API_KEY to /home/ubuntu/.config/job-beeper/dev-hirebase.env (never paste in chat or commit).
2. On isolated development only, rebuild after tests and verify the container reports api_key_configured=true while source_enabled remains false.
3. Run only the three free estimate buttons. Record Workday/Keka/Darwinbox estimated counts and confirm usage remains unchanged.
4. With separate explicit approval, enable Hirebase only in dev for the daily sample and inspect returned ATS tags, employer URLs, result quality and usage headers.
5. Build an independent company-agnostic discovery pipeline for Workday/Keka/Darwinbox: public search and sitemap discovery, ATS host/tenant resolver, a first-party company/board catalog, candidate verification and bounded automatic activation.
6. Convert verified board registry rows into per-board scheduled work with host-specific request budgets, due times, retry-after cooldown and board-level health.
7. Reconcile the dashboard and collector changes with the separate Coverage & Health UI PR #63 and connector PRs #59–#64 before merge. These branches were created from the same base; config migration versions must be sequenced and preserved.

## 6. Release boundary

Feature branch and draft PR only. No production deployment, no shared-development deployment, no source activation, no DB imports into a live service, no Telegram delivery, no external Hirebase calls and no changes to production Compose or the existing shared .env.


## 2026-11-09 18:07 IST — incremental sampler recovery checkpoint

The Hirebase sampler is being changed from a repeated rolling seven-day search to per-provider incremental polling. First run remains bounded to seven days; subsequent runs use ingested_after with first_ingested ascending and a two-hour overlap. SQLite provider state stores the watermark and pagination continuation. The watermark is committed only after normalized jobs are upserted, to avoid skipping records after a DB failure. The implementation has focused test coverage: 30 Hirebase/directory tests pass, including a continuation page and cursor commit helper. The full V2 suite completed successfully on this working tree: 430 tests passed in 385.001 seconds (job bjo6lrjfig, exit code 0). GitHub CI on the pushed commit is the remaining validation gate.

The user encountered a ChatGPT UI connection interruption (“Connection interrupted. Waiting for the complete answer”). This is not a JobBeeper outage. The earlier full-suite job ipu4poub1j was stopped because it predated the latest cursor changes; its output is not a final test result. The replacement full-suite job bjo6lrjfig started at 12:41:37 UTC and finished with exit code 0: 430 tests passed in 385.001 seconds. Previously, before cursor/pagination work, 426 V2 tests passed in 416.2 seconds and 30 focused tests passed on the current working tree. A fresh exact-working-tree full-suite run completed successfully as job bjo6lrjfig: 430 tests in 385.001 seconds, exit code 0. This is pre-commit local validation; GitHub CI is still required after push. See docs/RECOVERY_CHECKPOINT_2026-11-09_1807_IST.md for ordered next steps.

## PR and commit checkpoint — 2026-11-09 18:50 IST

- Commit: 533c889574bb6daddece8121c66f208c6fcec8de (`feat: add guarded global ATS discovery foundation`).
- Branch pushed: `feat/global-ats-discovery-hirebase-guard-20261109`.
- Draft PR: https://github.com/AvinashBhalla/job-beeper/pull/65 (base `v2-live-radar`).
- Full V2 regression: 430 tests passed in 385.001 seconds; background job `bjo6lrjfig` exit code 0. Focused discovery/Hirebase suite: 30 passed. Python compile, JSON, Compose config and diff checks passed.
- Superseded CI note: exact-head GitHub Actions V2 CI run #1427 (42620547252) passed on 999b66543ac162346d42cd3be2c39993c0475a6e, including dashboard JavaScript syntax and the full V2 test suite.
- PR remains draft/open, unmerged. No deployment or Hirebase requests/activation.\n\n---

## 2026-11-09 18:10 IST — latest Hirebase paging and regression checkpoint

The Hirebase sampler now stores a per-provider cursor with:
- last_polled_at
- fixed window_start
- next_page

Initial discovery starts with a bounded seven-day window. A provider query is estimated before the metered search. Pages are drained oldest-first with a fixed four-row page size; the next page is persisted across daily runs so a large initial result window cannot be truncated by the daily result budget. Once the window is drained, the cursor advances to the run-start timestamp minus a two-hour overlap, as recommended by the Hirebase ingestion docs. Pending cursors are committed only after JobBeeper has upserted the returned jobs. This is designed to avoid repeated first-page results while still catching delayed indexing.

The Hirebase Free-plan usage-summary response may have null Stripe subscription / period fields. The client handles the Free plan using a calendar-month UTC period while still requiring a valid m_jobs_api_calls meter. The local 400/12/4 budgets and conservative unknown-request reservations remain enforced.

**Verified release state at 2026-11-09 18:10 IST**
- PR #65: open, draft, mergeable; base v2-live-radar.
- Head: 999b66543ac162346d42cd3be2c39993c0475a6e.
- GitHub Actions V2 CI run #1427 (42620547252): completed successfully on this exact head. Its syntax job includes Python compilation checks, dashboard JavaScript syntax, focused tests and the full V2 unittest suite; every step succeeded.
- Local full V2 suite: 430 passed in 385.001 seconds.
- Focused discovery/Hirebase tests: 30 passed.
- Development Compose config validated. No container was rebuilt or restarted.
- Dedicated development Hirebase env file is empty, mode 600, under a mode-700 directory. No API key has been added or read; no Hirebase API call has been made; Hirebase source is disabled.
- No ATS source activated, no database import into a live service, no notifications sent, no production/shared-dev change.


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

After the full suite completes, fix any regression, commit the Workday code + tests + UI, push the same PR #65 branch, update the PR description and this handover, and verify exact-head GitHub CI. Keep PR #65 draft until the Workday/Keka/global-discovery milestones have received their own review. Do not merge/deploy solely because CI passes.\n
## 2026-11-09 19:37 IST — Workday inventory implementation verified locally

Workday now preserves offset 0 on the existing 120-second freshness poll and adds a durable per-board cursor that fetches at most one extra page every 15 minutes. Cursor advances only after upsert; failed pages are throttled without advancing; boards at the 2,000-result cap are explicitly marked incomplete. An admin-only inventory-status API and Coverage & Health panel expose progress. This is not facet-aware full inventory.

Validation: full V2 suite 436 passed in 398.870s (exit code 0); focused Workday/global discovery tests 31 passed. Python compileall, JSON config validation, git diff check and HTML panel wiring passed. Exact-head GitHub CI remains required after push.

Next priorities: Workday facet subdivision; Keka non-default portal slug support; independent public Workday/Keka/Darwinbox employer discovery; per-board scheduler/host budgets; controlled p50/p95 and 429 benchmarks. Darwinbox 403 must remain blocked, with no Cloudflare/TLS bypass.

User action: nothing required now. Hirebase key remains absent and source flags remain off.

Latest checkpoint: docs/RECOVERY_CHECKPOINT_2026-11-09_1937_IST.md. Keka plan: docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md.\n

## 2026-11-09 20:10 IST — Workday facet-aware inventory in progress

The next P0 implementation is now in the worktree. JobBeeper reads Workday facet metadata using the upstream response shape (`facetParameter`, `values[].id`, `values[].count`) and schedules partitions in the order jobFamilyGroup → timeType → locations → workerSubType. It does not copy the upstream library's concurrent fan-out: JobBeeper keeps one inventory page per board per 15-minute interval, a maximum facet depth of 4 and a queue budget of 500.

State is persisted per tenant:site in SQLite (`facet_queue_json`, `active_facets_json`, depth, active-query flag and partition-started flag), with migration helpers for existing tables. The fast 120-second offset-0 poll and detail cap remain unchanged. Stable external IDs + idempotent upsert deduplicate overlapping multi-tag partitions. Incomplete leaves (2,000 cap with no safe next facet, depth limit, no usable facet or queue-budget overflow) remain incomplete.

Admin status/UI adds pending partition count and active filters. Focused Workday collector suite: 21 passed. Full V2 regression job `4c646ih8lj` is running; log `/tmp/job-radar-workday-facets-full-tests.log`. This code is not yet committed/pushed. Read `docs/RECOVERY_CHECKPOINT_2026-11-09_2010_IST.md` for exact continuation instructions.

## 2026-11-09 20:10 IST — facet-aware Workday implementation (in progress)

The earlier statement that facet partitioning was outstanding is superseded by this work-in-progress. The current code reads Workday `facets[].facetParameter` and `values[].id/count`, then queues bounded partitions in the order `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`. This adapts the upstream strategy from `kalil0321/ats-scrapers` commit `6b44a1badc9bfbf5cf176f75265cc5729e520e99`, but does not copy its concurrent fan-out: JobBeeper runs at most one inventory page per board every 15 minutes. Queue, active filters and recursion depth are persisted with migration-safe SQLite columns. Depth is limited to 4 and queued partitions to 500; unresolved leaves/overflow remain incomplete. Stable Workday source IDs and idempotent upsert deduplicate overlapping partitions.

Focused Workday suite: 22 passed. Full V2 regression job `4c646ih8lj` is running; see `/tmp/job-radar-workday-facets-full-tests.log`. The worktree is uncommitted and not deployed. See `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md` for the design.

## 2026-11-09 20:10 IST — Workday facet partitions supersede the earlier outstanding note

The previous note that Workday facet partitioning remained outstanding is now historical. Current worktree implements it: pinned upstream response shape, bounded facet selector, persisted FIFO child queue, recursive partitions, active filters/cursor, and admin status. Limits are depth 4, 500 queued child queries and one inventory page per board every 15 minutes; it deliberately avoids parallel fan-out. Unresolved leaves/overflow remain incomplete. Full local regression job `4c646ih8lj` is running; focused Workday tests passed 22. See `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.


## 2026-11-09 20:18 IST — Workday facet partitioning implemented locally

The Workday collector now builds a persisted FIFO facet queue when an unfiltered query hits the 2,000 cap and exposes `jobFamilyGroup`, `timeType`, `locations`, `workerSubType` partitions in priority order. Capped child queries recursively subdivide on an unused facet. It is deliberately sequential (one extra inventory page per board per 15 minutes), with depth cap 4 and queue cap 500. Incomplete leaves/overflow remain incomplete. Queue/active filters are migration-safe SQLite state and commit after upsert. Admin API/UI show pending partitions and active filters.

Validation: focused Workday tests 22 passed; full V2 suite 443 passed in 402.776s; compileall, JSON, diff check and dashboard HTML/panel checks passed. Exact-head CI remains required after push. No live ATS calls; actual tenant facet shapes still require an approved canary. Details: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`; latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2018_IST.md`.


## 2026-11-09 20:25 IST — exact final Workday facet tree

The current uncommitted Workday facet implementation now includes the final admin status distinction for `in_progress_incomplete` versus terminal `truncated`. Focused Workday tests are 22/22. The earlier full V2 run passed 443 tests in 402.776s but began before the final status test was added. A second full-suite job `3tjy6iwusp` is running against the exact final tree; see `/tmp/job-radar-workday-facets-final-tests.log`. Run exact-head GitHub CI after push for modern dashboard JS and final full-suite validation.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md`. Facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.

## Next company-agnostic discovery design (2026-11-09)

New design note: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Research confirms Common Crawl CDX is heavily rate-limited: serialize requests, no proxies, sleep between calls, and stop for 24 hours after an IP block/503. For broad/high-volume filtering, use the Parquet URL Index via Athena/Spark/Polars/DuckDB rather than frequent CDX wildcard sweeps. The next code step should create a separate unmatched ATS candidate table because current `ats_board_registry` requires a real company ID; do not manufacture employer identities from tenant slugs. Candidate URLs must preserve crawl provenance, be live-verified, and only then linked to the employer board registry.


## 2026-11-09 20:30 IST — Workday facet full regression complete

The exact current worktree full V2 suite passed **444 tests in 346.385 seconds**, exit code 0 (job `3tjy6iwusp`, log `/tmp/job-radar-workday-facets-final-tests.log`). Focused Workday collector suite passed 22/22. The final admin `in_progress_incomplete` status test is included in the 444. Compileall, both config JSON files, HTML IDs/panel wiring and `git diff --check` passed. All Workday/Keka/Darwinbox/Hirebase source flags remain false.

Current Workday facet code, dashboard UI and docs are still uncommitted on branch `feat/global-ats-discovery-hirebase-guard-20261109`. Next: inspect diff, commit/push, update PR #65, verify exact-head V2 CI #1432 or later. Keep PR draft; no deployment/source activation.

Next global discovery design: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. It recommends a separate unmatched ATS candidate table and polite Common Crawl indexing; no AWS credentials needed unless choosing the Parquet/Athena bulk path.
