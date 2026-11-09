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
