# ATS provider implementation gap analysis — JobBeeper vs open-source adapter research

**Date:** 2026-11-09  
**Branch:** feat/global-ats-discovery-hirebase-guard-20261109  
**Purpose:** translate repository research into specific changes required in JobBeeper's existing Workday, Keka and Darwinbox collectors. This review was static code inspection; it did not make live ATS requests.

## Executive result

JobBeeper already has working, default-off, tenant-configured collectors for Workday, Keka and Darwinbox, plus a review-first candidate registry. That is useful groundwork, but it is not global employer discovery.

The biggest technical limitations are not the lack of three adapters. They are:
1. no autonomous company/tenant discovery to continuously add employers;
2. Workday is deliberately limited to one list page (20 jobs) per configured tenant and has no large-board facet partitioning;
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
- WORKDAY_MAX_PAGES_PER_BOARD = 1
- WORKDAY_MAX_BOARDS = 20

**Observed limitation:** one configured board returns at most the first 20 postings in a normal run. There is no facet partitioning by job family, time type, location or worker subtype. The collector emits a warning if the configured page cap is reached, but with a one-page cap it is not a full inventory crawler. It also does not perform a cursor/checkpoint across pages or a large-board discovery sweep.

**Research comparison:** kalil0321/ats-scrapers documents that Workday limits page size to 20 and can report a capped total of 2,000 even when a tenant has far more openings. It partitions by jobFamilyGroup, then timeType, locations and workerSubType, and deduplicates overlapping results. Source: https://github.com/kalil0321/ats-scrapers/blob/main/src/ats_scrapers/scrapers/workday.py.

**Work needed:**
1. retain the current low-cost frequent first-page poll for freshness;
2. add a separate, lower-frequency board inventory sweep with persistent facet/page checkpoints;
3. inspect Workday facets and detect capped totals before claiming board coverage;
4. partition large tenants across available facets with hard depth/request budgets and a stable ID set;
5. preserve Retry-After cooldown, per-tenant pacing and request telemetry;
6. make the board's coverage_complete, last_full_inventory_at, last_incremental_poll_at and last_truncated_reason explicit in its registry/health view.

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
