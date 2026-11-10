# JobBeeper recovery checkpoint — 2026-11-09 19:37 IST

## Current branch and PR
- Repository: AvinashBhalla/job-beeper
- Feature branch: feat/global-ats-discovery-hirebase-guard-20261109
- Pull request: #65, open, draft, mergeable, base v2-live-radar
- Earlier exact-head V2 CI #1427 passed on implementation commit 999b665 (430 tests); the Workday inventory code below is newer and requires exact-head CI after push.
- Worktree: /tmp/job-radar-global-discovery. Check git status and final HEAD before making changes.

## Completed before this session
1. Optional Hirebase collector, disabled by default, server-key-only, estimate-first, SQLite budget ledger, 400/month, 12/day, 4/provider/day and fail-closed unknown request reservation.
2. Hirebase incremental per-provider pagination, daily sample limits, Free-tier calendar-month UTC handling, two-hour overlap and 429 cooldown.
3. Admin-only Hirebase status/estimate endpoints and UI.
4. Attributed LastRound AI August 2026 CC BY 4.0 directory snapshot with 9,935 Greenhouse/Lever/Ashby candidate rows. Import is candidate-only and never auto-activates.
5. Admin-only registry coverage summary; no invented market-coverage percentage.
6. Research report for Freehire, Career-Ops, ats-scrapers, JobSpy, JobNavigator, Job Board Aggregator and Job Forager.
7. Direct ATS provider gap analysis and recovery/handover docs.

## Completed in this continuation — Workday inventory
1. Added durable SQLite table workday_board_poll_state keyed by normalized tenant:site. It stores next inventory offset, last attempt, last full inventory, reported total, facets metadata, completion and truncation state.
2. Kept Workday offset 0 on its existing 120-second source poll interval.
3. Added at most one additional inventory page per board every 15 minutes, starting at offset 20 and rotating forward with a durable cursor.
4. Detail lookups remain on the fast page. The slower inventory page adds one list request only.
5. Cursor changes remain pending until jobs have been upserted. Failed inventory pages preserve their offset but record attempt time to avoid immediate retries.
6. Existing 429 Retry-After and Workday cooldown behaviour is preserved.
7. Short final pages or reached reported totals below 2,000 mark a sweep complete; completed inventory is rechecked weekly.
8. A reported total at 2,000, an inconsistent empty page at that cap, or the local 2,000 offset cap is marked truncated/incomplete. It is never reported complete. Facet subdivision remains outstanding.
9. Added admin-only GET /api/workday/inventory-status and Coverage & Health UI to show board, status, reported total, facet count, next offset and truncation reason.
10. Added tests for cursor commit, freshness cadence, throttling, advancing offsets, failed-page retry, weekly refresh, 2,000-cap truncation and admin-only status.

## Validation
- Full V2 suite: 436 passed in 398.870 seconds; exit code 0.
- Focused Workday collector + global discovery/Hirebase tests: 31 passed.
- Python compileall, JSON config validation and git diff --check passed.
- HTML duplicate-ID/required-ID and Workday loader-wiring checks passed.
- VM Node is v12 and cannot parse existing optional chaining/nullish-coalescing. Exact-head GitHub CI must validate dashboard JavaScript after push.
- No live ATS requests were made by tests; provider requests were mocked.

## Research findings worth retaining
- Career-Ops is the best reverse employer discovery/rate-limit reference. It uses different concurrency limits for different host topologies and documents real 429-caused lost boards.
- ats-scrapers is the best provider code reference. Workday facet subdivision is required beyond the 2,000-result ceiling. Keka supports /careers and /careers/{portal}. Its Darwinbox adapter uses httpcloak against Cloudflare; do not copy that bypass.
- Freehire is the strongest provider-isolated ingestion, deduplication and outbox reference.
- Job Forager has useful company inventories and pagination ideas, but inspected HTTP code disables TLS verification, swallows errors and lacks robust per-host cooldown.
- Do not reuse CC BY-NC company directories commercially. LastRound AI snapshot here is attributed CC BY 4.0.

## Next priorities
### P0
1. Workday facet-aware full inventory. Current cursor advances only through the first 2,000-result query. Inspect facets and partition jobFamilyGroup, timeType, locations and workerSubType with bounded depth/request budgets, dedup and explicit completeness. Do not claim full coverage until proven.
2. Keka actual portal slug resolution. Current collector and probe still hardcode default in /careers/api/embedjobs/default/active/{id}. Follow docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md: strict URL parser, portal-specific embed endpoint, source IDs and job URLs, same-host redirect validation. Test default plus at least two non-default portals with mocks.
3. Global Workday/Keka/Darwinbox employer discovery using public career links, sitemaps, Common Crawl CDX and licensed sources, with provenance/confidence and review-first candidate state.
4. Persistent per-board due queue: per-board next_due_at, per-host concurrency budgets, Retry-After, jitter, cooldown, independent retry/page state, backpressure and queue-age visibility. Current source-level scheduler remains.
### P1
5. Darwinbox per-board 403/429/5xx classification and re-verification; keep 403 blocked. Never add Cloudflare/TLS impersonation or anti-bot bypass.
6. Benchmark p50/p95, 429 rates, page completeness, job-posted-to-first-seen, queue age and feed visibility on verified public canary boards before tuning concurrency.
7. Continue job freshness, stale/repost detection and legitimacy checks after coverage/telemetry reliability improves.
### P2
8. Add broader ATS adapters after discovery, registry, scheduler and telemetry contracts are stable.
9. Hirebase estimate-only development experiment only after secure key configuration and explicit approval; no commercial multi-user use without vendor permission.

## User action required
Nothing is needed from the user right now. Do not request the Hirebase key in chat. It remains absent; the dedicated server-side development file is empty. Workday/Keka/Darwinbox/Hirebase source flags remain off.

## Release/safety boundary
- PR #65 remains draft and unmerged.
- No deployment/restart, source activation, live ATS requests, Hirebase requests or notifications.
- No production/shared-development configuration was changed.
- After push, verify exact-head V2 CI and update this checkpoint. Keep PR draft; do not merge/deploy without review.
