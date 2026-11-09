# JobBeeper recovery checkpoint — 2026-11-09 20:25 IST

## Start here

1. Worktree: `/tmp/job-radar-global-discovery` on VM host `job-radar`.
2. Repository: `AvinashBhalla/job-beeper`.
3. Branch: `feat/global-ats-discovery-hirebase-guard-20261109`.
4. PR: [#65](https://github.com/AvinashBhalla/job-beeper/pull/65), open/draft/mergeable, base `v2-live-radar`.
5. Latest pushed branch head before the current Workday facet change: `10f7338` (documentation-only after Keka implementation). Current facet code/docs are uncommitted in the worktree; full local regression now passed and is ready to commit/push.
6. Previously exact-head CI passed: Workday incremental commit `6197446` / V2 CI #1430; Keka portal commit `afa177b` / V2 CI #1431.

## Completed before this continuation

- Optional, default-off Hirebase sampler, estimate-first quota guard, persisted usage ledger and admin estimate/status UI. Key absent; no Hirebase API requests made.
- LastRound AI August 2026 CC BY 4.0 seed directory, 9,935 Greenhouse/Lever/Ashby candidates. Import is review-only/unverified and never auto-activates.
- Admin-only employer-board registry/coverage summary.
- Workday incremental cursor/status baseline: offset0 remains 120s freshness; one inventory page per board every15m; cursor commits after upsert; errors throttle; 2,000 cap marked incomplete.
- Keka default/non-default portal support: strict `/careers/{portal}` parsing; tenant:portal identity; collector/verifier share portal-specific endpoint; same-tenant distinct portals supported.
- Research report and direct provider gap analysis covering Freehire, Career-Ops, ats-scrapers, JobSpy, JobNavigator, Job Board Aggregator and Job Forager.

## Current Workday facet-aware implementation — uncommitted

1. Pinned upstream reference: `kalil0321/ats-scrapers` Workday file at commit `6b44a1badc9bfbf5cf176f75265cc5729e520e99`. It documents page-size 20, total cap 2,000, facet schema `facets[].facetParameter` / `values[].id/count`, priority `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`, and overlapping `workerSubType` values.
2. Added migration-safe SQLite columns to `workday_board_poll_state`: `facet_queue_json`, `active_facets_json`, `active_facet_depth`, `active_facet_query`, `facet_partition_started`.
3. Added strict facet selector and bounded FIFO children, preferring those four Workday facet fields and skipping already-applied dimensions.
4. Root total=2,000 with usable facets enqueues child filters. Capped children can recursively split using the next unused facet.
5. Workday remains sequential: at most one inventory page per board per 15 minutes; no upstream concurrent fan-out copied. The 120-second offset0 freshness poll and detail cap remain.
6. Recursion depth max 4; queued partitions max 500. Unusable facet, depth exhaustion, queue overflow, or inconsistent capped response stays explicitly incomplete; no false full-coverage claim.
7. Stable source IDs plus idempotent upsert deduplicate across facets, including multi-tag workerSubType overlap.
8. Admin-only `/api/workday/inventory-status` and Coverage & Health UI report active facets, pending partitions, and differentiate `in_progress_incomplete` from terminal `truncated`.
9. Existing 429 Retry-After, cooldown and pending cursor-after-upsert semantics remain.

## Validation

- Focused `v2.test_radar.WorkdayCollectorTests`: **22 passed** after the final status-display change.
- Earlier V2 run: 443 passed in 402.776s (job `4c646ih8lj`). Final exact-worktree V2 regression: **444 passed in 346.385 seconds**, exit code 0 (job `3tjy6iwusp`; `/tmp/job-radar-workday-facets-final-tests.log`).
- Final full V2 suite for the exact current worktree is running as job `3tjy6iwusp`; log `/tmp/job-radar-workday-facets-final-tests.log`. Do not report its final count until job finishes.
- Latest compileall, JSON configs and `git diff --check` are part of job `3tjy6iwusp`.
- HTML unique-ID/panel and JS loader checks passed; VM Node 12 cannot parse existing dashboard optional chaining/nullish-coalescing, so exact-head GitHub CI is required after push.
- All Workday HTTP in tests is mocked. Actual Workday tenant-specific facet shape/counts are based on upstream source research and remain unverified by a live approved canary.

## Next agent instructions

1. Check `3tjy6iwusp` and its log. Fix any regression; rerun the focused Workday tests after any change.
2. Update this checkpoint and `docs/IMPLEMENTATION_PROGRESS_2026-11-09.md` with exact full-suite count/time and pass/fail.
3. Run `git diff --check`, `compileall`, config JSON validation, and HTML IDs. Check all source flags stay off.
4. Review full `git diff` and commit implementation/tests/docs on this branch.
5. Push branch, update PR #65 body, query GitHub exact-head V2 CI, verify dashboard JS and full suite pass. Keep PR #65 draft and unmerged.
6. After CI, arrange a reviewed, low-volume public Workday canary only with user approval; validate actual facets, true counts, pagination completeness and 429 behavior before enabling sources.

## Priorities after this milestone

### P0
1. Finish and CI-verify Workday facet queue.
2. Build independent public employer/tenant discovery for Workday/Keka/Darwinbox using public career links, sitemaps, Common Crawl CDX and properly licensed seeds. Preserve provenance/confidence; candidate discovery never activates boards.
3. Add persistent per-board scheduler: next_due_at, per-host concurrency budgets, jitter, Retry-After, cooldown, checkpoints, backpressure, queue-age visibility.
4. Keep Darwinbox 403 blocked. Use only documented/public or employer-authorized routes; no Cloudflare/TLS impersonation or anti-bot bypass.
5. Benchmark p50/p95, 429 rate, page completeness, first-seen delay and user-feed lag before increasing concurrency.

### P1
6. Improve stale/repost and job legitimacy signals after inventory/telemetry reliability.

### P2
7. More ATS adapters only after discovery/registry/scheduler contracts stabilize.
8. Hirebase estimate-only dev test only after secure key config and explicit user approval. Key is absent; no commercial multi-user use without written vendor permission.

## User action / safety

- Nothing required from the user now. Do not ask for Hirebase key in chat.
- `v2/config.json` and `v2/config.dev.json` show Workday/Keka/Darwinbox/Hirebase all disabled.
- No live ATS/Hirebase calls, source activation, deployment, container restart, live DB import, notifications, or production/shared-dev changes.
- PR #65 remains draft/unmerged/undeployed.

## Next company-agnostic discovery design (2026-11-09)

New design note: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Research confirms Common Crawl CDX is heavily rate-limited: serialize requests, no proxies, sleep between calls, and stop for 24 hours after an IP block/503. For broad/high-volume filtering, use the Parquet URL Index via Athena/Spark/Polars/DuckDB rather than frequent CDX wildcard sweeps. The next code step should create a separate unmatched ATS candidate table because current `ats_board_registry` requires a real company ID; do not manufacture employer identities from tenant slugs. Candidate URLs must preserve crawl provenance, be live-verified, and only then linked to the employer board registry.
