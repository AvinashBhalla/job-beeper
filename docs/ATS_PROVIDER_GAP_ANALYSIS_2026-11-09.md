# ATS provider implementation gap analysis — JobBeeper vs open-source adapter research

**Date:** 2026-11-09
**Branch:** feat/global-ats-discovery-hirebase-guard-20261109
**Purpose:** translate repository research into specific changes required in JobBeeper's existing Workday, Keka and Darwinbox collectors. This review was static code inspection; it did not make live ATS requests.

## Executive result

JobBeeper already has working, default-off, tenant-configured collectors for Workday, Keka and Darwinbox, plus a review-first candidate registry. That is useful groundwork, but it is not global employer discovery.

The biggest technical limitations are not the lack of three adapters. They are:
1. no autonomous company/tenant discovery to continuously add employers;
2. Workday now has a persisted, throttled inventory cursor, but still has no large-board facet partitioning;
3. Keka assumes the public embed-feed portal name is always "default";
4. all three ATSs are polled as source-level jobs from config arrays rather than as independently scheduled, health-tracked board tasks.

## 1. Existing JobBeeper implementation

### Workday — v2/radar.py:4772–5011

What exists:
- accepts explicit public *.wdN.myworkdayjobs.com/{site} URLs from a configuration list;
- validates the tenant/cluster/site URL shape;
- uses the public candidate-site CXS /wday/cxs/{tenant}/{site}/jobs API, not the privileged Workday REST API;
- requests 20 jobs per page;
- has a separate detail lookup with a per-board cap of 20 detail attempts and a short inter-detail delay;
- has persisted 429 cooldown and request telemetry;
- deduplicates IDs by tenant/site/requisition ID.

The current constants are:
- WORKDAY_PAGE_SIZE = 20
- WORKDAY_MAX_PAGES_PER_BOARD = 2 (freshness page plus at most one inventory page)
- WORKDAY_INVENTORY_PAGE_INTERVAL_SECONDS = 900
- WORKDAY_FULL_INVENTORY_REFRESH_SECONDS = 604800
- WORKDAY_MAX_BOARDS = 20

**Current behaviour:** offset 0 is polled on the existing 120-second source interval. A separate per-tenant:site SQLite cursor fetches at most one additional page every 15 minutes, starting at offset 20. Cursor progress is committed only after job upsert; failed inventory pages retain their offset and are throttled. Detail calls remain limited to the freshness page. Completed non-truncated sweeps are rechecked weekly. An admin-only status endpoint and Coverage & Health panel expose cursor and truncation state.

**Current facet-aware state:** a bounded, persisted Workday facet queue is now implemented in the continuation dated 2026-11-09 20:10 IST. Root queries capped at 2,000 enqueue child queries using `jobFamilyGroup`, then `timeType`, `locations`, and `workerSubType`. Each child is paged and resumed over time. The queue is persisted by tenant:site and committed only after job upsert. It uses a 4-level recursion bound, 500-task queue budget, and one inventory page per board every 15 minutes. Overlapping `workerSubType` results are deduplicated through stable source IDs/upsert.

**Remaining limitation:** facet availability and depth do not guarantee complete inventory. Any leaf that reaches the 2,000 cap without another safe facet, depth/queue-budget overflow, or inconsistent response is explicitly incomplete. The queue is sequential and conservative; it does not copy the upstream concurrent fan-out. Verify actual public facet shapes on a low-volume approved canary before changing cadence or declaring market coverage.

**Research comparison:** kalil0321/ats-scrapers documents that Workday limits page size to 20 and can report a capped total of 2,000 even when a tenant has far more openings. It partitions by jobFamilyGroup, then timeType, locations and workerSubType, and deduplicates overlapping results. Source: https://github.com/kalil0321/ats-scrapers/blob/main/src/ats_scrapers/scrapers/workday.py.

**Work needed:**
1. retain the low-cost first-page poll for freshness (implemented);
2. keep the separate inventory cursor and checkpoint (implemented);
3. facet-aware partitioning using jobFamilyGroup, timeType, locations and workerSubType (implemented in current worktree; full regression/CI pending);
4. keep bounded per-facet page cursors, stable-ID deduplication and explicit incomplete-leaf reporting (implemented; verify exact-head CI);
5. preserve Retry-After cooldown, per-tenant pacing and request telemetry (existing behaviour retained);
6. make per-board completeness, last full inventory and truncation visible in registry/health (admin status endpoint added; registry-level persistence remains future work).

The first-page fast poll and full inventory sweep should not share one cadence. That keeps newly posted jobs fast while allowing large board inventories to finish over multiple bounded runs.

### Keka — v2/radar.py:5284–5440

What exists:
- detects a public https://{tenant}.keka.com/careers... board;
- fetches the public HTML page with redirect/host validation and response-size limits;
- extracts a career portal/document identifier from the HTML;
- calls the public embed jobs endpoint;
- normalizes job title, locations, description, dates, salary metadata, experience and skills;
- caps rows at KEKA_MAX_JOBS_PER_BOARD = 1000;
- records source request/page/board metrics and applies persisted 429 cooldown.

Current implementation uses:
 /careers/api/embedjobs/default/active/{feed_id}

It does not call the organization career-portal-info endpoint to understand the portal and it does not derive the portal slug from the actual careers path. The endpoint is currently hardcoded to default.

**Research comparison:** the current ats-scrapers Keka adapter parses a portal slug from the careers URL, extracts the document identifier from the bootstrap page, then calls:
- /careers/api/organization/{portal}/careerportalinfo
- /careers/api/embedjobs/{portal}/active/{identifier}

It optionally obtains company metadata from the organization endpoint. Source: https://github.com/kalil0321/ats-scrapers/blob/main/src/ats_scrapers/scrapers/keka.py.

**Work needed:**
1. parse the actual portal path segment from the employer's careers URL;
2. validate the portal segment against a strict safe slug pattern;
3. call the public organization/portal-info endpoint where available and validate the payload shape;
4. call the matching portal-specific embed-jobs endpoint instead of hardcoding default;
5. preserve the current host-redirect check and no-auth-only rule;
6. test multiple known real public Keka boards with different portal paths before enabling any new board;
7. add pagination or truncation detection if a tenant returns more than the current 1,000-row bound.

A Keka adapter working for one default portal does not prove all Keka portals use the same path.

### Darwinbox — v2/radar.py:5443–5560

What exists:
- discovery recognises *.darwinbox.in career sites and requires a candidate-facing /ms/candidatev2/{company_id}/careers path;
- the collector posts to the candidate-facing /ms/candidateapi/job/alljobs endpoint;
- the current request uses limit=50, pages 1–5, 0.2-second inter-page delay;
- jobs are normalized with location, description, dates, experience and metadata;
- it records request/page/board telemetry and handles 429 cooldown;
- it does not enable browser automation or TLS impersonation.

The roadmap records a tenant-specific test history: Arvind Group was previously verified at 36 rows; several other .in tenants returned 403, and .com test leads were rejected. These are historical test outcomes and must be reverified before use.

**Research comparison:** ats-scrapers describes the same candidate endpoint as Cloudflare-protected and uses httpcloak (TLS/client impersonation) to get through that layer. Its adapter pages ten jobs at a time. Source: https://github.com/kalil0321/ats-scrapers/blob/main/src/ats_scrapers/scrapers/darwinbox.py.

**Policy decision:** do not copy the Cloudflare/TLS impersonation path into JobBeeper. A 403 or anti-bot block must remain a visible provider/board failure, not a signal to evade access controls. Only use a documented public endpoint or an employer-authorized integration. Reconfirm whether the current 50-row page size and response envelope are correct per tenant; do not infer universal behaviour from one board.

**Work needed:**
1. retain strict .in candidate URL matching until additional tenant patterns are individually justified;
2. explicitly classify 403 separately from 429 in per-board health and show it as blocked/not verified;
3. keep per-board verification mandatory, with the existing bounded probes;
4. validate pagination size and total/page semantics against a documented or explicitly public authorized tenant;
5. do not retry 403 with alternate TLS fingerprints, proxy pools or browser automation;
6. maintain an employer-by-employer approved board state.

## 2. Discovery and scheduler gap

The current directory importer only adds Greenhouse, Lever and Ashby candidate rows. Hirebase is a small, optional India sample for Workday/Keka/Darwinbox, not a tenant directory. The ordinary manual company scan accepts one employer website at a time. A user still cannot ask JobBeeper to discover every new Workday/Keka/Darwinbox employer automatically.

The existing collectors consume source configuration arrays and run as a source-wide cycle. The board registry already stores provider, board key, URL, review status and telemetry, but there is not yet a persistent due queue for each employer board with its own next_due_at, request budget, retry state, last full inventory and latency target.

**Target design:**

Public employer discovery
- career-page links + sitemap crawl
- public Common Crawl CDX patterns
- licensed board-directory seeds
- ATS URL / tenant / portal resolver

↓

Candidate board registry (provenance + confidence)

↓

manual policy / safe verification

↓

Verified board registry

↓

Per-board due queue (host budgets, jitter, cursors, cooldown)

↓

Provider adapter → normalize → deduplicate → shared jobs store

↓

per-user matching → notifications / application workflow

### Discovery candidate sources and rules

- Crawl company websites' public careers links and sitemaps, not every page on the domain.
- Search Common Crawl CDX for known public ATS host shapes: *.myworkdayjobs.com, *.keka.com/careers/*, *.darwinbox.in/ms/candidatev2/*/careers, and other supported providers.
- Use licensed directories as seed candidates, preserving attribution, data date and source URL.
- Re-check candidates against the live public careers page before verification.
- Do not brute-force DNS tenant names, scrape authenticated HRMS APIs without employer credentials, defeat CAPTCHA/Cloudflare, or treat search index absence as evidence that a company has no jobs.
- Persist a provenance method and last-seen time for each candidate so stale seeds can be deprioritized and newly discovered employers can be added daily.
- Keep candidate, verified, active, rejected and retired states distinct.

## 3. Rate-limit and freshness architecture to adopt

Research suggests combining these patterns:
- Freehire: provider-isolated run-once workers, board catalog, idempotent IDs, persistent board cooldown and transactional outbox.
- Career-Ops: host-aware concurrency (many tenants can share one provider hostname; per-tenant Workday is a different host topology), cached board directories, checkpoints/resume, explicit cooldown after 429.
- ats-scrapers: shared request wrapper, bounded retry attempts, exponential delay and Retry-After; explicit handling for 403/406 rather than blind retries.

A single global worker count is not acceptable. Use a keyed concurrency budget by origin/host, plus a per-board limit. Track:
- request p50/p95 and full board poll duration;
- 2xx/403/404/408/429/5xx counts;
- Retry-After and cooldown duration;
- pages/facets attempted and completed;
- jobs available vs fetched;
- timestamp-to-first-seen delay;
- time spent in board queue;
- stale-board and incomplete-sweep counts.

Increase concurrency only when the host's observed 429 rate and error profile support it. A fast partial result is not better than a slower complete result.

## 4. Recommended execution order

**P0-A — improve existing collectors before adding more ATS names**
1. Workday page/inventory completeness, facet subdivision and checkpointing.
2. Keka portal slug resolution and non-default portal validation.
3. Darwinbox 403/429 health classification and strict authorized-access policy.

**P0-B — first-party global discovery**
4. Add public career-link/sitemap and Common Crawl CDX candidate harvesters.
5. Add provider-specific resolvers for Workday tenant/site, Keka tenant/portal and Darwinbox .in company ID.
6. Add provenance/confidence/staleness and batch candidate review/probe tooling.

**P0-C — per-board scheduling and observability**
7. Add the persistent per-board due queue and host budget service.
8. Run controlled canary sweeps and publish completeness/latency dashboards.
9. Only then expand global discovery cadence and coverage.

## 5. Acceptance criteria

- A new public employer careers URL can be discovered without the user typing a company name.
- The candidate record includes employer, ATS, tenant/portal/site, source URL, discovery method, discovery date and confidence.
- Candidate discovery alone never schedules or activates the board.
- A low-concurrency verification probe confirms the public endpoint and records exact response classification.
- Workday full inventory can show why a board is complete, truncated or partially processed.
- Keka can ingest at least two public employer portals whose portal slug is not default, without relaxing URL/host validation.
- Darwinbox 403 is visible as blocked and never invokes a bypass mechanism.
- A provider 429 stops or cools only the affected host/board queue, not unrelated providers.
- A fixed verified-board benchmark demonstrates p50/p95 latency, result completeness and job first-seen delay; worker increases are justified by those measurements.
- No user profile, resume, role preference or private candidate data is sent to a public ATS listing endpoint.

## 6. Release status

This gap analysis is documentation-only. It does not change collectors, activate sources, contact ATS providers or spend Hirebase credits. The code commit 999b665 remains the tested implementation; current branch documentation head is tracked in the PR #65 handover.
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


## 2026-11-09 19:37 IST — Workday inventory implementation verified locally

Workday now preserves offset 0 on the existing 120-second freshness poll and adds a durable per-board cursor that fetches at most one extra page every 15 minutes. Cursor advances only after upsert; failed pages are throttled without advancing; boards at the 2,000-result cap are explicitly marked incomplete. An admin-only inventory-status API and Coverage & Health panel expose progress. This is not facet-aware full inventory.

Validation: full V2 suite 436 passed in 398.870s (exit code 0); focused Workday/global discovery tests 31 passed. Python compileall, JSON config validation, git diff check and HTML panel wiring passed. Exact-head GitHub CI remains required after push.

Next priorities: Workday facet subdivision; Keka non-default portal slug support; independent public Workday/Keka/Darwinbox employer discovery; per-board scheduler/host budgets; controlled p50/p95 and 429 benchmarks. Darwinbox 403 must remain blocked, with no Cloudflare/TLS bypass.

User action: nothing required now. Hirebase key remains absent and source flags remain off.

Latest checkpoint: docs/RECOVERY_CHECKPOINT_2026-11-09_1937_IST.md. Keka plan: docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md.

## 2026-11-09 20:10 IST — Workday facet-aware inventory in progress

The next P0 implementation is now in the worktree. JobBeeper reads Workday facet metadata using the upstream response shape (`facetParameter`, `values[].id`, `values[].count`) and schedules partitions in the order jobFamilyGroup → timeType → locations → workerSubType. It does not copy the upstream library's concurrent fan-out: JobBeeper keeps one inventory page per board per 15-minute interval, a maximum facet depth of 4 and a queue budget of 500.

State is persisted per tenant:site in SQLite (`facet_queue_json`, `active_facets_json`, depth, active-query flag and partition-started flag), with migration helpers for existing tables. The fast 120-second offset-0 poll and detail cap remain unchanged. Stable external IDs + idempotent upsert deduplicate overlapping multi-tag partitions. Incomplete leaves (2,000 cap with no safe next facet, depth limit, no usable facet or queue-budget overflow) remain incomplete.

Admin status/UI adds pending partition count and active filters. Focused Workday collector suite: 21 passed. Full V2 regression job `4c646ih8lj` is running; log `/tmp/job-radar-workday-facets-full-tests.log`. This code is not yet committed/pushed. Read `docs/RECOVERY_CHECKPOINT_2026-11-09_2010_IST.md` for exact continuation instructions.

## 2026-11-09 20:10 IST — facet-aware Workday implementation (in progress)

The earlier statement that facet partitioning was outstanding is superseded by this work-in-progress. The current code reads Workday `facets[].facetParameter` and `values[].id/count`, then queues bounded partitions in the order `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`. This adapts the upstream strategy from `kalil0321/ats-scrapers` commit `6b44a1badc9bfbf5cf176f75265cc5729e520e99`, but does not copy its concurrent fan-out: JobBeeper runs at most one inventory page per board every 15 minutes. Queue, active filters and recursion depth are persisted with migration-safe SQLite columns. Depth is limited to 4 and queued partitions to 500; unresolved leaves/overflow remain incomplete. Stable Workday source IDs and idempotent upsert deduplicate overlapping partitions.

Focused Workday suite: 22 passed. Full V2 regression job `4c646ih8lj` is running; see `/tmp/job-radar-workday-facets-full-tests.log`. The worktree is uncommitted and not deployed. See `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md` for the design.


## 2026-11-09 20:18 IST — Workday facet partitioning implemented locally

The Workday collector now builds a persisted FIFO facet queue when an unfiltered query hits the 2,000 cap and exposes `jobFamilyGroup`, `timeType`, `locations`, `workerSubType` partitions in priority order. Capped child queries recursively subdivide on an unused facet. It is deliberately sequential (one extra inventory page per board per 15 minutes), with depth cap 4 and queue cap 500. Incomplete leaves/overflow remain incomplete. Queue/active filters are migration-safe SQLite state and commit after upsert. Admin API/UI show pending partitions and active filters.

Validation: focused Workday tests 22 passed; full V2 suite 443 passed in 402.776s; compileall, JSON, diff check and dashboard HTML/panel checks passed. Exact-head CI remains required after push. No live ATS calls; actual tenant facet shapes still require an approved canary. Details: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`; latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2018_IST.md`.


## 2026-11-09 20:25 IST — exact final Workday facet tree

The current uncommitted Workday facet implementation now includes the final admin status distinction for `in_progress_incomplete` versus terminal `truncated`. Focused Workday tests are 22/22. The earlier full V2 run passed 443 tests in 402.776s but began before the final status test was added. A second full-suite job `3tjy6iwusp` is running against the exact final tree; see `/tmp/job-radar-workday-facets-final-tests.log`. Run exact-head GitHub CI after push for modern dashboard JS and final full-suite validation.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md`. Facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.


## Common Crawl discovery implementation note — 2026-11-09

Use Common Crawl as a scheduled candidate source, not a live job source. Its CDX API is heavily rate-limited: serialize requests, sleep between them, avoid proxies, and stop for 24 hours on an IP block/503. For bulk filtering use the Parquet URL Index through Athena/Spark/Polars/DuckDB. See `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md` for official references and the detailed decision.

The first implementation should be one provider query at a time, a pinned crawl ID, capped response rows, latest-capture provenance, candidate-only registry state and current-live verification. Do not ingest archived postings as current jobs or claim complete global coverage from a sampled crawl.

## Next company-agnostic discovery design (2026-11-09)

New design note: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Research confirms Common Crawl CDX is heavily rate-limited: serialize requests, no proxies, sleep between calls, and stop for 24 hours after an IP block/503. For broad/high-volume filtering, use the Parquet URL Index via Athena/Spark/Polars/DuckDB rather than frequent CDX wildcard sweeps. The next code step should create a separate unmatched ATS candidate table because current `ats_board_registry` requires a real company ID; do not manufacture employer identities from tenant slugs. Candidate URLs must preserve crawl provenance, be live-verified, and only then linked to the employer board registry.


## 2026-11-09 20:30 IST — Workday facet full regression complete

The exact current worktree full V2 suite passed **444 tests in 346.385 seconds**, exit code 0 (job `3tjy6iwusp`, log `/tmp/job-radar-workday-facets-final-tests.log`). Focused Workday collector suite passed 22/22. The final admin `in_progress_incomplete` status test is included in the 444. Compileall, both config JSON files, HTML IDs/panel wiring and `git diff --check` passed. All Workday/Keka/Darwinbox/Hirebase source flags remain false.

Current Workday facet code, dashboard UI and docs are still uncommitted on branch `feat/global-ats-discovery-hirebase-guard-20261109`. Next: inspect diff, commit/push, update PR #65, verify exact-head V2 CI #1432 or later. Keep PR draft; no deployment/source activation.

Next global discovery design: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. It recommends a separate unmatched ATS candidate table and polite Common Crawl indexing; no AWS credentials needed unless choosing the Parquet/Athena bulk path.


## 2026-11-09 20:35 IST — Workday facet inventory verified on CI

Workday facet implementation was pushed in `4d7513803031d1c32c02a19ac8452dfb221c02ad`; exact-head GitHub V2 CI #1435 (42640211533) passed, including modern dashboard JS syntax and full V2 tests. Local full V2 suite 444 passed in 346.385s; focused Workday tests 22 passed. Latest recovery checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2035_IST.md`. Next P0: unmatched ATS candidate staging table/admin review-link flow, then serialized Common Crawl candidate discovery; preserve provenance, do not fabricate employer IDs, and require current public live verification before linking/activation.
