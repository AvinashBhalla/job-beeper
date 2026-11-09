# JobBeeper recovery checkpoint — 2026-11-09 18:10 IST

## Current state

- Repository: AvinashBhalla/job-beeper
- Feature branch: feat/global-ats-discovery-hirebase-guard-20261109
- Pull request: #65, open, draft, mergeable; base v2-live-radar
- Current head: 999b66543ac162346d42cd3be2c39993c0475a6e
- Exact-head GitHub Actions V2 CI: run #1427, ID 42620547252, completed successfully. Python syntax, dashboard JavaScript syntax, focused tests and full V2 suite all passed.
- Local full V2 suite: 430 passed in 385.001 seconds (exit code 0).
- Focused discovery/Hirebase tests: 30 passed.
- Working tree was clean before this documentation refresh. This checkpoint is part of the PR branch documentation.

## Completed on the feature branch

1. Optional Hirebase collector is disabled by default, daily, server-key-only and guarded by:
   - zero-job-credit estimate before each metered search;
   - four rows per provider per page;
   - 12 rows/day across providers;
   - 400 results per Hirebase billing period, keeping 100 credits below the 500-job Free limit;
   - four-row local budget reservations and SQLite usage ledger;
   - uncertain requests retaining their reservations;
   - Retry-After and persisted 429 cooldown;
   - Free-tier calendar-month UTC period support when billing period/subscription fields are null.
2. Incremental Hirebase paging stores last_polled_at, window_start and next_page per ATS provider. First scan is bounded to seven days; next pages are resumed; completion advances to a two-hour overlap. The cursor is committed after JobBeeper upserts the returned jobs.
3. Admin-only Hirebase usage status and estimate endpoints and UI controls exist. A confirmation protects source enablement. API key never appears in the browser or API response.
4. LastRound AI August 2026 CC BY 4.0 ATS directory has 9,935 rows: 4,966 Greenhouse, 2,856 Ashby and 2,113 Lever. Attribution and pinned source metadata are included. Import adds low-confidence unverified board candidates only, never verifies, activates, polls or notifies.
5. Admin-only provider/registry coverage summary is present and does not invent a market-coverage percentage.
6. New source tests cover quota reservation, pagination/watermark commit, Free-tier usage, admin-only routes, directory candidate-only import, repeated import deduplication and 429 handling.

## Open-source research findings

Research report: docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md

- Freehire (3.4k stars / 373 forks): strongest ingestion architecture. Provider-isolated run-once workers, board catalogue, idempotent IDs, per-board cooldown and transactional outboxes.
- Career-Ops (80.9k / 14.9k): strongest reverse ATS discovery and rate-limit lessons. Current scan-ats-full.mjs uses 20 workers for per-tenant Workday, 6 for shared Greenhouse/Lever/Ashby hosts, 2 for Paylocity and Join; its comments document real 429-caused lost boards and recovery after cooldown.
- ats-scrapers (151 / 37): strongest Python adapter reference. Current code includes Workday, Keka and Darwinbox. Workday must partition high-volume queries by facets because pagination wraps after 2,000 jobs; Keka has public career portal JSON endpoints; Darwinbox's current adapter uses httpcloak against Cloudflare. Do not copy this bypass path.
- JobSpy (4.6k / 905): supplementary job boards (LinkedIn, Indeed, Glassdoor, ZipRecruiter, Bayt, Naukri, BDJobs, HelloWork); explicitly warns about 429s. Not a global ATS company directory.
- Job Board Aggregator (181 / 40): Common Crawl + daily source anomaly monitoring. Code is MIT; company lists are CC BY-NC. Do not use those datasets commercially.
- JobNavigator (184 / 52): product UX and job-hunt workflow reference.
- Job Forager: 18-source CLI claims and incremental tracking are interesting, but its inspected Greenhouse/Workday/SmartRecruiters paths disable TLS verification, swallow errors and use fixed concurrency without robust per-host cooldown. Do not copy its HTTP transport.

## Important remaining work

This branch is a discovery foundation, not a complete global ATS crawler.

1. Build first-party public employer/tenant discovery for Workday, Keka and Darwinbox: company career links, sitemaps, public search results, Common Crawl CDX and licensed directory seeds.
2. Preserve source provenance, discovery method, confidence, tenant URL, portal/site segment, last verified time and board status in the registry.
3. Verify public board endpoints using bounded, low-concurrency probes. Do not activate candidates automatically.
4. Create per-board scheduled work with host-aware concurrency, Retry-After, exponential backoff/jitter, persistent cooldown, checkpoints, backpressure and observable queue age.
5. Workday collection must handle the documented 2,000-result cap with facet subdivision and dedup.
6. Keka public career portal discovery needs the right portal path/slug; adapter support alone does not find every employer.
7. Darwinbox's adapter in ats-scrapers uses httpcloak to overcome Cloudflare. Do not add TLS impersonation or anti-bot bypass to JobBeeper. Require a documented/public allowed access path or employer permission.
8. Benchmark p50/p95 HTTP latency, 429 rates, actual page completeness, job-posted-to-first-seen delay, queue age and source freshness before increasing concurrency.
9. Keep the Hirebase API key empty until user privately supplies it. After that, run estimate-only checks in isolated dev only after explicit approval. Do not use Hirebase in commercial multi-user production without written vendor permission.
10. Reconcile config migration ordering with sibling PRs #59–#64 before merging.

## Release/safety boundary

- PR #65 remains draft/open and unmerged.
- No Hirebase key has been written or read; no Hirebase API request has been made.
- Hirebase source remains disabled.
- No container was rebuilt/restarted.
- No ATS source was activated.
- No live directory import was performed.
- No Telegram/notification delivery occurred.
- No production or shared-development deployment/change occurred.

## Suggested immediate next action

Review PR #65's new research note and migration ordering, then proceed with a separate feature branch for the first-party Workday/Keka/Darwinbox candidate-discovery pipeline. Keep its first iteration discovery-only and non-activating.


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
