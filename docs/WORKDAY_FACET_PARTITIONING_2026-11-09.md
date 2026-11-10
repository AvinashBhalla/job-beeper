# Workday facet partitioning — implementation notes

**Date:** 2026-11-09 20:10 IST
**Branch:** `feat/global-ats-discovery-hirebase-guard-20261109`
**Status:** implemented in current worktree; full V2 regression passed 444/444; not yet committed/pushed or exact-head CI-verified.

## Upstream response contract confirmed

Inspected `kalil0321/ats-scrapers` Workday scraper at commit `6b44a1badc9bfbf5cf176f75265cc5729e520e99` (release v0.3.0). The code documents:
- page limit = 20;
- total is reported as 2,000 when a query exceeds the Workday per-query cap;
- facet response records contain `facetParameter` and `values`, and each value contains an `id` and true `count`;
- preferred subdivision axes: `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`;
- `workerSubType` is multi-tag and may return overlapping job subsets.

Reference source: https://github.com/kalil0321/ats-scrapers/blob/6b44a1badc9bfbf5cf176f75265cc5729e520e99/src/ats_scrapers/scrapers/workday.py

## JobBeeper design

JobBeeper retains the 120-second offset-0 freshness poll. The inventory walker is deliberately sequential and lower-frequency: at most one inventory page per configured board every 15 minutes. This is a conscious difference from the upstream concurrent fan-out to keep provider load low and observable.

On a root query reporting total=2,000, a safe facet is selected and all child filter tasks are placed in a bounded FIFO queue. Each task contains `applied_facets` plus recursion depth. The queue is persisted by `tenant:site`. A task is popped only when the 15-minute window is due. Page offset and current facet filter are persisted and committed after job upsert.

When a filtered query also reaches 2,000, the next unused allowed facet is selected and child tasks are appended. If no facet remains, depth is exhausted, or the 500-task budget is reached, that leaf/portion remains explicitly incomplete. The scheduler keeps draining other queued tasks where possible, but the board is never reported fully complete when any such truncation reason remains.

Deduplication uses existing stable Workday source IDs derived from tenant/site/requisition ID. This deduplicates across partitions and across separate scheduled runs; DB upsert remains idempotent. This is especially important for multi-tag `workerSubType` results.

## Safety and boundedness

- One inventory page per board per 15 minutes; no parallel fan-out.
- Max facet recursion depth: 4.
- Max queued partitions: 500; overflow records an incomplete reason rather than silently dropping coverage.
- Only the four explicit Workday facet parameters above are accepted.
- Facet IDs are non-empty strings up to 200 characters; empty/duplicate IDs and invalid counts are ignored.
- Existing Retry-After/429 cooldown applies to all Workday list requests.
- Existing fast-page detail requests remain limited to 20 per board; inventory pages do not fan out detail requests.
- Source remains disabled by default. All test network calls are mocked.

## Persistent state

`workday_board_poll_state` now includes:
- `facet_queue_json` — pending filters/depth.
- `active_facets_json` — current query filter.
- `active_facet_depth` — recursion depth.
- `active_facet_query` — whether current cursor belongs to a facet child rather than the root.
- `facet_partition_started` — distinguishes a linear root sweep from a subdivided inventory.
- existing offset, last attempt, last full inventory, reported total, raw facets and truncation status.

All new fields are added with `_ensure_column` for existing databases. The admin-only `/api/workday/inventory-status` API reports pending partition count and active filters. It distinguishes `in_progress_incomplete` (an unresolved leaf exists but other queued work remains) from terminal `truncated` (no remaining safe partition work).

## Current validation

- Focused `v2.test_radar.WorkdayCollectorTests`: **22 passed** after selector, two-partition multi-run resume, queue visibility, incomplete-in-progress state and schema-migration tests.
- Final full V2 regression: **444 passed in 346.385 seconds**, exit code 0. Job `3tjy6iwusp`; log `/tmp/job-radar-workday-facets-final-tests.log`.
- `compileall`, JSON config validation, `git diff --check`, HTML unique-ID/panel checks and Workday JS loader checks passed.
- Dashboard JS syntax still requires modern Node in GitHub CI; VM Node 12 is too old for existing dashboard syntax.

## Known remaining constraints

This is not proof of 100% Workday inventory. A leaf with no further usable facets, recursion depth 4, a partition budget overflow or a query reporting the cap remains incomplete. JobBeeper intentionally does not use high-concurrency requests to force coverage. It should show the unresolved reason to the operator.

Next steps after test/CI: verify actual public facet metadata on an explicitly approved low-volume canary; tune the 15-minute cadence only from measured p50/p95 and 429 rates; then proceed to company-agnostic employer discovery and per-board scheduling.
