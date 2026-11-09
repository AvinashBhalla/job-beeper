# Workday incremental inventory implementation — working plan

**Date:** 2026-11-09 19:20 IST
**Branch:** feat/global-ats-discovery-hirebase-guard-20261109
**Status:** implemented and locally regression-tested; default-off source; not deployed.

## Objective

Preserve the current Workday first-page poll every configured 120 seconds, while allowing larger public boards to be traversed over time without requesting every page on every poll.

## Planned behaviour

- Always poll offset 0 for freshness, preserving current detail-fetch cap and behavior.
- Maintain a durable per-board SQLite cursor keyed by normalized Workday tenant + site.
- At most once every 15 minutes per board, request one additional inventory page at the persisted offset, starting at 20.
- Do not fetch detail pages for the slower inventory page; limit extra work to one list request.
- Commit a successful cursor advance only after JobBeeper has upserted the returned jobs.
- On a transient inventory-page failure, preserve the offset but persist the attempted time so a 120-second source cycle does not retry it immediately.
- Respect existing 429 Retry-After/cooldown.
- Detect early completion when a page is short or the reported total is reached.
- When Workday reports the 2,000-result cap, persist an explicit truncated reason and keep the board marked incomplete. Facet subdivision is a separate later step; this change must not claim full inventory.
- Refresh a completed non-truncated full inventory weekly.

## Non-goals for this change

- No global Workday tenant discovery.
- No automatic activation of unverified boards.
- No Workday facet subdivision yet.
- No change to default-off source flags, poll cadence, or production/shared-dev.
- No extra detail-page fan-out for inventory pages.

## Validation

- Unit tests with temporary SQLite database and mocked list/detail endpoints: 17 Workday tests passed.
- Focused Workday + global discovery/Hirebase suites: 31 passed.
- Full V2 regression: 436 passed in 398.870 seconds (exit code 0).
- Python compileall, config JSON validation, git diff check and HTML panel wiring passed. Exact-head GitHub CI is still required after push for dashboard JavaScript syntax.
- Prove first-page poll still occurs every invocation.
- Prove deep page is no more frequent than 15 minutes and advances across runs.
- Prove failed deep page does not advance cursor but is throttled.
- Prove page exhaustion and reported-total 2,000 truncation are distinguished.
- Full V2 regression, modern Node syntax in GitHub CI, git diff --check, and dev Compose syntax check.

## Risks / later follow-up

- Workday can cap a reported total at 2,000 even when more jobs exist. This feature surfaces that condition; it does not solve it. The next Workday milestone is facet discovery/partitioning with bounded recursion and deduplication.
- The first-page fast poll plus one 15-minute inventory page increases requests modestly. Observe p50/p95, 429 and page success rates on an isolated verified canary before changing cadence.

## 2026-11-09 20:10 IST — facet-aware Workday implementation (in progress)

The earlier statement that facet partitioning was outstanding is superseded by this work-in-progress. The current code reads Workday `facets[].facetParameter` and `values[].id/count`, then queues bounded partitions in the order `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`. This adapts the upstream strategy from `kalil0321/ats-scrapers` commit `6b44a1badc9bfbf5cf176f75265cc5729e520e99`, but does not copy its concurrent fan-out: JobBeeper runs at most one inventory page per board every 15 minutes. Queue, active filters and recursion depth are persisted with migration-safe SQLite columns. Depth is limited to 4 and queued partitions to 500; unresolved leaves/overflow remain incomplete. Stable Workday source IDs and idempotent upsert deduplicate overlapping partitions.

Focused Workday suite: 22 passed. Full V2 regression job `4c646ih8lj` is running; see `/tmp/job-radar-workday-facets-full-tests.log`. The worktree is uncommitted and not deployed. See `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md` for the design.

## Superseding update — 2026-11-09 20:10 IST

The facet-aware inventory follow-up is now implemented in the current worktree. When a root query returns total=2,000 and exposes usable facet metadata, JobBeeper creates persisted child tasks in priority order `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`. A child that also reaches 2,000 is subdivided again using an unused facet. One inventory page per board is processed every 15 minutes; there is no concurrent fan-out. Page offsets, active filters and the FIFO child queue are saved in SQLite and committed after upsert.

Limits: recursion depth 4; queued partitions 500. A leaf that cannot be further subdivided, a queue overflow, depth exhaustion or inconsistent early empty page remains explicitly incomplete. Stable IDs + DB upsert deduplicate overlapping multi-tag partitions. Admin status shows pending queue count and active filters. See `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.

Focused Workday suite: 22 passed. Full V2 suite job `4c646ih8lj` was started before the final status-display assertion was added; after it finishes, run or rely on exact-head CI for the latest committed tree. The current implementation is still uncommitted/unpushed.


## 2026-11-09 20:18 IST — Workday facet partitioning implemented locally

The Workday collector now builds a persisted FIFO facet queue when an unfiltered query hits the 2,000 cap and exposes `jobFamilyGroup`, `timeType`, `locations`, `workerSubType` partitions in priority order. Capped child queries recursively subdivide on an unused facet. It is deliberately sequential (one extra inventory page per board per 15 minutes), with depth cap 4 and queue cap 500. Incomplete leaves/overflow remain incomplete. Queue/active filters are migration-safe SQLite state and commit after upsert. Admin API/UI show pending partitions and active filters.

Validation: focused Workday tests 22 passed; full V2 suite 443 passed in 402.776s; compileall, JSON, diff check and dashboard HTML/panel checks passed. Exact-head CI remains required after push. No live ATS calls; actual tenant facet shapes still require an approved canary. Details: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`; latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2018_IST.md`.


## 2026-11-09 20:25 IST — exact final Workday facet tree

The current uncommitted Workday facet implementation now includes the final admin status distinction for `in_progress_incomplete` versus terminal `truncated`. Focused Workday tests are 22/22. The earlier full V2 run passed 443 tests in 402.776s but began before the final status test was added. A second full-suite job `3tjy6iwusp` is running against the exact final tree; see `/tmp/job-radar-workday-facets-final-tests.log`. Run exact-head GitHub CI after push for modern dashboard JS and final full-suite validation.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md`. Facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.


## 2026-11-09 20:30 IST — Workday facet full regression complete

The exact current worktree full V2 suite passed **444 tests in 346.385 seconds**, exit code 0 (job `3tjy6iwusp`, log `/tmp/job-radar-workday-facets-final-tests.log`). Focused Workday collector suite passed 22/22. The final admin `in_progress_incomplete` status test is included in the 444. Compileall, both config JSON files, HTML IDs/panel wiring and `git diff --check` passed. All Workday/Keka/Darwinbox/Hirebase source flags remain false.

Current Workday facet code, dashboard UI and docs are still uncommitted on branch `feat/global-ats-discovery-hirebase-guard-20261109`. Next: inspect diff, commit/push, update PR #65, verify exact-head V2 CI #1432 or later. Keep PR draft; no deployment/source activation.

Next global discovery design: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. It recommends a separate unmatched ATS candidate table and polite Common Crawl indexing; no AWS credentials needed unless choosing the Parquet/Athena bulk path.


## 2026-11-09 20:35 IST — Workday facet inventory verified on CI

Workday facet implementation was pushed in `4d7513803031d1c32c02a19ac8452dfb221c02ad`; exact-head GitHub V2 CI #1435 (42640211533) passed, including modern dashboard JS syntax and full V2 tests. Local full V2 suite 444 passed in 346.385s; focused Workday tests 22 passed. Latest recovery checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2035_IST.md`. Next P0: unmatched ATS candidate staging table/admin review-link flow, then serialized Common Crawl candidate discovery; preserve provenance, do not fabricate employer IDs, and require current public live verification before linking/activation.
