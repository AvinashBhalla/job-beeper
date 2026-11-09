# JobBeeper recovery checkpoint — 2026-11-09 19:47 IST

## Current branch, PR and exact CI state

- Repository: `AvinashBhalla/job-beeper`.
- Branch: `feat/global-ats-discovery-hirebase-guard-20261109`.
- PR: [#65](https://github.com/AvinashBhalla/job-beeper/pull/65), open, draft, mergeable, base `v2-live-radar`.
- Latest pushed implementation commit: `6197446b2f4e6d270a3bf0967d9a39a82ddad904` (Workday incremental inventory).
- Exact-head GitHub Actions V2 CI run #1430 (`42632005997`) **passed**, including Python compilation, dashboard JavaScript syntax, focused tests and full V2 unittest suite.
- Workday local full suite: 436 passed in 398.870 seconds; exact-head CI passed for that commit.
- Keka portal implementation is currently in the worktree but not yet pushed. Full V2 regression completed: 439 tests passed in 359.301 seconds, exit code 0. Focused board-discovery suite: 37 passed.
- The docs have been restored to normal Markdown after detecting and correcting a newline-encoding mistake before commit. Verify line counts and `git diff --check` before pushing.

## Completed work in PR #65

### Hirebase / discovery foundation
1. Optional Hirebase collector, disabled by default, server-key-only, estimate-first, SQLite budget ledger, 400/month, 12/day, 4/provider/day, fail-closed unknown-request reservation, Free-tier period handling and 429 cooldown.
2. Incremental Hirebase provider cursors with 7-day initial sample, page resume, two-hour overlap and cursor commit after upsert.
3. Admin-only Hirebase status/estimate UI; no key in frontend.
4. LastRound AI August 2026 CC BY 4.0 seed catalogue with 9,935 Greenhouse/Lever/Ashby candidates. Import remains low-confidence/unverified and never activates sources.
5. Admin-only registry coverage summary; market coverage percentage is explicitly unknown, not invented.
6. Repo research and direct provider gap analysis for Freehire, Career-Ops, ats-scrapers, JobSpy, JobNavigator, Job Board Aggregator and Job Forager.

### Workday incremental inventory (pushed and CI passed)
1. Durable SQLite `workday_board_poll_state` keyed by tenant:site.
2. Keep first page (offset 0) on the existing 120-second freshness poll.
3. At most one additional inventory page per board every 15 minutes, starting at offset 20 and advancing using a durable cursor.
4. Detail lookups remain on the fast page; inventory pages add one list request only.
5. Cursor commits only after jobs are upserted; failed inventory attempts are throttled without advancing the cursor.
6. Existing 429 Retry-After/cooldown behavior is preserved.
7. Short final pages or reported total below 2,000 mark inventory complete; complete inventory refreshes weekly.
8. Workday's 2,000-result cap or safety offset cap is explicitly marked truncated/incomplete. Facet partitioning is still required.
9. Admin-only `/api/workday/inventory-status` and Coverage & Health UI show progress, cursor and truncation state.
10. Full V2 local tests 436/436 passed; GitHub V2 CI #1430 passed on exact commit 6197446.

### Keka multi-portal implementation (currently uncommitted)
1. Strict Keka careers URL resolver supports default `/careers` and non-default `/careers/{portal-slug}`.
2. Rejects non-HTTPS, credentials, nonstandard ports, query, fragment, extra path segments, encoded slashes, reserved routes and malformed slugs.
3. Default portal preserves existing board key and source-job ID format.
4. Non-default identity becomes `tenant:portal`; source IDs include tenant+portal so multiple portals on one tenant cannot collide.
5. Collector uses `/careers/api/embedjobs/{portal}/active/{feed_id}` and posts under `/careers/{portal}/jobdetails/{id}`.
6. Admin verification uses the same portal-specific endpoint.
7. Config accepts multiple distinct portals on one tenant and rejects duplicate tenant+portal.
8. Existing same-host redirect controls, payload caps, telemetry, 429 cooldown and default-off source policy remain.
9. Focused board-discovery suite: 37 passed, including two non-default portal collection and config tests.
10. The full V2 suite is running (job `jvlp1z3ljj`).

## Research findings that affect implementation

- Career-Ops is the strongest global employer-discovery and host-aware concurrency reference. It documents real 429s and different worker limits for tenant-specific Workday versus shared ATS hosts.
- ats-scrapers is the strongest provider-code reference. Workday facet subdivision is required beyond 2,000 results. Keka supports portal path segments. Do not copy its Darwinbox `httpcloak`/Cloudflare bypass.
- Freehire is the strongest provider-isolated ingestion, idempotent dedupe and transactional outbox reference.
- Job Forager has interesting source inventories but inspected HTTP code disables TLS verification, swallows errors and lacks robust per-host cooldown. Do not copy those transport choices.
- Do not reuse CC BY-NC company directory datasets commercially. LastRound AI snapshot bundled in PR #65 is attributed CC BY 4.0.

## Next priorities

### P0
1. Verify exact-head V2 CI #1431 for commit afa177b; fix any failures.
2. Implement Workday facet-aware partitions (`jobFamilyGroup`, `timeType`, `locations`, `workerSubType`) with bounded recursion, per-facet cursors, dedup and explicit completeness.
3. Build independent public employer/tenant discovery for Workday/Keka/Darwinbox from career links, sitemaps, Common Crawl CDX and licensed seeds, with provenance/confidence and candidate-only state.
4. Implement persistent per-board scheduler: `next_due_at`, per-host budgets, jitter, Retry-After, cooldowns, checkpoints, backpressure and queue-age visibility.
5. Keep Darwinbox 403 explicitly blocked. Only documented/public or employer-authorized access; no Cloudflare/TLS impersonation or anti-bot bypass.

### P1
6. Benchmark p50/p95, 429, pages attempted/completed, jobs available/fetched, job-posted-to-first-seen and user feed lag on verified canary boards.
7. Continue stale/repost detection and job legitimacy checks once collection completeness is reliable.

### P2
8. Add more ATS adapters only after discovery, registry, scheduler and telemetry contracts are stable.
9. Hirebase estimate-only dev test only after the user securely configures the key and explicitly approves; no commercial multi-user use without written vendor permission.

## User action needed

Nothing right now. Do not request the Hirebase key in chat. It remains absent; the dedicated server-side env file is an empty placeholder. Workday, Keka, Darwinbox and Hirebase flags remain off.

## Release and safety boundary

- PR #65 remains draft and unmerged.
- No production/shared-dev changes or service restarts.
- No live ATS requests from the tests; Keka HTTP is mocked.
- No Hirebase requests, no source activation, no live directory import and no notification dispatch.
- Keka full tests passed; code is pushed, PR body is updated, and exact-head V2 CI #1431 is in progress. Verify CI, update this checkpoint and keep PR draft until reviewed.