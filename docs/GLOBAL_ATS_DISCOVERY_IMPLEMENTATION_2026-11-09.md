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
- GitHub connector returned no PR-triggered workflow runs for this SHA at the time of handover; verify checks on PR #65 before review/merge.
- PR remains draft/open, unmerged. No deployment or Hirebase requests/activation.
