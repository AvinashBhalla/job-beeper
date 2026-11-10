# Real-time global job ingestion — feasibility, costs and engineering handoff

**Date:** 2026-11-10  
**Repository:** AvinashBhalla/job-beeper  
**Branch:** v2-live-radar  
**Companion design:** docs/GLOBAL_JOB_INGESTION_WITHOUT_MANUAL_COMPANY_CONFIG_2026-11-10.md  
**Purpose:** Give the next engineering agent the product goal, evidence, realistic freshness limits, cost model, implementation estimate and exact next steps. This document is a decision/handoff, not a claim that the architecture has already been implemented.

---

## 1. Product goal — what we are actually building

JobBeeper must collect jobs across supported ATS/job-board platforms without an administrator entering every employer separately.

The desired product experience is:

- **End user:** can enable or disable provider families such as Workday, Greenhouse, Ashby, SmartRecruiters, Lever, Keka, Darwinbox, etc. The user must not select companies or know board tokens, tenant names, portal IDs or career-site URLs.
- **Administrator:** can enable/disable a provider globally, inspect its freshness and errors, and manage safety/rate-limit policy. The administrator must not add Coinbase, NVIDIA, OpenAI, Bosch, or thousands of other employers one by one.
- **Backend:** automatically discovers employer boards, verifies them, maintains a shared internal catalogue, and polls active boards. The backend still stores provider-specific employer identifiers; those identifiers are discovered and managed by the service, not manually configured.
- **Matching:** ingestion is performed once into a shared jobs corpus. Each user's provider selections and job preferences are applied after ingestion. One user's Workday toggle must not stop Workday collection for other users.

**Important distinction:** “No company configuration” does not mean “there are no company identifiers.” ATS public endpoints are generally scoped to one employer board. We need a machine-maintained board catalogue so that the system knows which tenant/slug/site to query. The whole reason for switching architecture is to automate the creation and lifecycle of that catalogue.

## 2. What the board-count evidence says

These are independent public research measurements, not official ATS customer counts and not JobBeeper's achieved inventory. They show that the opportunity is large enough to justify a global catalogue.

### October 29, 2026 benchmark

HiringCensus reported the following board and open-posting counts:

| ATS/provider | Discovered boards | Open postings |
|---|---:|---:|
| Workday | 5,670 | 682,573 |
| Greenhouse | 5,967 | 153,771 |
| Ashby | 3,641 | 53,030 |
| Personio | 1,814 | 16,741 |
| Breezy | 1,805 | 24,359 |
| Teamtailor | 1,395 | 20,395 |
| Recruitee | 1,288 | 18,684 |
| Lever | 159 | 1,962 |
| Amazon | 1 | 0 |
| Workable | 1 | 0 |
| **Sum of provider-board entries** | **21,741** | **971,515** |

The same snapshot reported 20,964 distinct employers. The board rows sum to more than the unique-employer count because a company may have more than one board/provider association. Do not label 21,741 as unique companies.

**Workday conclusion:** use **5,670 discovered boards and approximately 682,573 open postings** as the latest benchmark located in this research (October 29, 2026). It is not a count already imported into JobBeeper.

Other independent datasets report different Workday totals (for example, 3,947 boards in a September 2026 index and 2,658 in an August 2026 ATS-feed sample). This variance is expected from different crawl histories, inclusion rules, source coverage and verification dates. Treat the counts as coverage benchmarks, not a promise that every board is discoverable or currently live.

### A second reproducible direct-ATS measurement

The public project veresk06/open-ats-feed measured 18,164 live boards and 439,867 open postings across six providers: Greenhouse, Ashby, Lever, Breezy, Recruitee and Teamtailor. Its method harvests candidate tokens from Common Crawl and verifies tokens against public posting APIs. It does **not** include Workday, Keka or Darwinbox in that six-provider total.

Its README explains that the Common Crawl S3 cluster.idx file is SURT-sorted and can be searched with HTTP byte-range requests. It reports roughly 700 KB of relevant index-block transfer to locate a provider prefix instead of downloading a roughly 110 MB index file. This is the implementation pattern to study for our harvester.

**Source-count caution:** the same GitHub page's About/header text currently displays 16,361 boards / 399,398 postings, while its README results section and provider table state 18,164 / 439,867. Treat the README table as the reported detailed measurement, but inspect its dated machine-readable output before using the figure as a strict benchmark. The source page itself has stale/inconsistent summary metadata.

### What we do not have a defensible number for yet

The October benchmark above does not provide Keka or Darwinbox board counts. Do not invent a number for either. Their discovery should be measured by running our own harvest, verifying candidates and publishing the results with a crawl date and status breakdown.

Also do not add the provider counts from different datasets together. They are different snapshots and may overlap.

## 3. Can the approach be real-time?

**Not at zero delay with direct polling.** It can be made near-real-time for boards we already know, but every polling architecture has a detection window.

A public ATS job-board API generally answers a GET request for a particular employer board. It does not automatically push a new-job event to every third-party consumer. Unless the ATS offers a supported event/webhook feed to us, the collector must ask the board repeatedly.

If a board is polled every N seconds:

- best case: the job is published just before a poll and is found almost immediately;
- average polling wait, assuming publication time is uniformly distributed: approximately N/2;
- worst normal polling wait: close to N, plus source/API response time, ingestion and feed refresh;
- 429s, provider outages, indexing delay or pagination can make it longer.

| Poll cadence | Approx. average detection wait | Normal upper bound before processing |
|---|---:|---:|
| 1 minute | 30 seconds | 1 minute |
| 2 minutes | 1 minute | 2 minutes |
| 5 minutes | 2.5 minutes | 5 minutes |
| 15 minutes | 7.5 minutes | 15 minutes |

These are mathematical polling windows, not latency guarantees. ATS publication/indexing delay occurs before our poll can see the job.

### There are two different freshness problems

1. **New job on an already-known board:** solved by polling that board frequently or receiving a supported upstream event.
2. **A new employer starts using an ATS or creates a new board:** solved by global board discovery. Common Crawl is an archive/index, not a live event stream. Its crawl/index cadence means it cannot be the sole mechanism for discovering a brand-new board immediately. Use Common Crawl for wide bootstrap/backfill, and supplement it with recurring discovery from permitted career-page/sitemap sources and other public/attributed directories.

Do not claim that Common Crawl makes a brand-new employer discoverable in seconds. It does not.

### Realistic product promise

Recommended initial service targets, to be validated by a live canary:

- **High-priority already-known boards:** aim for a 1–2 minute polling interval only where provider/host limits allow it.
- **Normal direct ATS boards:** 5–15 minute cadence initially.
- **Low-activity or constrained boards:** 15–60 minutes, based on provider policy and observed yield.
- **Vendor event/webhook sources:** accept the event immediately when the vendor discovers and delivers it, but report the vendor's discovered-at time and our received-at time separately. Do not promise ATS-publication-to-webhook latency unless the vendor contract provides an SLA.

An overall user-facing target of “usually within a few minutes on supported direct sources” is credible after measurement. “Zero delay” or “every job the instant it is posted” is not credible with polling and must not be advertised as a guarantee.

### What can get closer to instant?

- An ATS-supplied webhook/event stream, where a supported public integration actually exists.
- A licensed aggregator's new-job webhook. TheirStack documents a job.new webhook which fires when it discovers a new posting matching a saved search. That removes our need to poll their search endpoint continuously, but it does not prove the aggregator discovers the ATS posting instantly. TheirStack charges credits per webhook event.
- A hybrid: upstream webhooks where available, plus adaptive direct polling for public ATS endpoints, with a slower discovery/backfill process for new employer boards.

JobsPipe's current November 2026 changelog describes Signals that can deliver matching new postings to webhook destinations; it lists a first-class job.created webhook as roadmap work. Treat this as a signal/webhook feature, not an ATS-origin instant event feed.

### Important rate-limit constraint

High-frequency polling scales with every board, not with the number of users. Some provider APIs are shared hosts across thousands of boards. For example, the open-ats-feed project says it honours a one-request-per-second crawl delay for Lever's API host. That means the total schedule for a provider can be constrained even if each employer has a different board token. We must not simply set every board to a one-minute interval and assume the provider will accept it.

Respect provider terms, robots rules for the exact requested paths, Retry-After, 403/429/5xx responses and host-level cooldowns. Never interpret a refusal as a dead employer, and do not bypass blocks with proxies, CAPTCHA solving, TLS impersonation or alternate identities.

## 4. Request volume — why cadence matters

The minimum request count assumes one request per board per poll. Pagination, Workday facet splitting, retries and verification increase it.

Formula:

daily requests = active boards × 86,400 / poll_interval_seconds

Illustrative scale:

| Active boards | 15-minute cadence | 5-minute cadence | 1-minute cadence |
|---:|---:|---:|---:|
| 5,000 | 480,000/day | 1,440,000/day | 7,200,000/day |
| 21,739 benchmark board entries | 2,086,944/day | 6,262,832/day | 31,304,160/day |

For the 5,670 Workday benchmark alone:

- 15-minute cadence: 544,320 board polls/day;
- 5-minute cadence: 1,632,960 board polls/day;
- 1-minute cadence: 8,164,800 board polls/day.

This is the core trade-off. A minute-level cadence across every board is not a sensible first release. We should start at a safe cadence, measure provider response times, rate limits and job yield, then allocate faster polling to the boards/providers where it is permitted and valuable.

## 5. Cost — direct collection vs commercial data feeds

### A. Direct public ATS collection

For a publicly accessible endpoint, there may be no per-job API credit fee. That does **not** mean unlimited free collection. We still pay for:

- worker compute and concurrency;
- network transfer/egress and HTTP overhead;
- queue/scheduler/database reads and writes;
- job-description storage, indexes, backups and logs;
- monitoring, retries and operational support.

The biggest cost driver is not Common Crawl token harvesting. It is the recurring volume and size of responses from active boards, particularly if full job descriptions are returned every poll.

**Budgetary planning range only (not a cloud quote):**

- Initial proof-of-concept on the existing VM, a few hundred to roughly 2,000 boards at 5–15 minutes: potentially no new server bill if the current machine has spare capacity; allow roughly ₹0–₹5,000/month for incremental storage/monitoring/backup/network overhead.
- Early production, roughly 2,000–5,000 boards at 5–15 minutes: plan roughly ₹5,000–₹25,000/month for incremental worker/database/monitoring capacity.
- Broader 10,000–22,000 board operation at 5–15 minutes: use ₹15,000–₹60,000/month as an initial capacity-planning envelope, subject to actual payload sizes and hosting choice.
- Attempting 20,000+ boards at one-minute cadence can exceed that envelope substantially. Do not approve this operating mode until a representative canary measures request bytes, provider limits, CPU, DB write rate and 429s.

These INR ranges are engineering estimates, not vendor quotes or measured JobBeeper bills. Because the current VM size, cloud provider, region, egress allowance and typical response sizes have not been measured here, the next agent must run a 24–72 hour canary and replace these placeholders with actual metrics before committing to a monthly budget.

### B. Commercial aggregator pricing observed during this research

These are vendor-published USD plan prices found on November 10, 2026. Verify them again before purchasing.

**JobsPipe** currently documents:

| Plan | Monthly price | Monthly job credits |
|---|---:|---:|
| Seeker | $19.60 | 10,000 |
| Builder | $49 | 25,000 |
| Growth | $149 | 100,000 |
| Scale | $399 | 300,000 |
| Business | $650 | 500,000 |
| Enterprise | Quoted | 1,000,000+ |

JobsPipe says one credit buys one distinct job for the rest of the calendar month; returning the same job again that month is free. Webhook endpoints are available from Builder and above. This can be attractive for a measured fallback, but verify source mix and freshness in an India-focused sample.

**TheirStack** currently documents monthly API tiers including:

| Monthly API credits | Published monthly price |
|---:|---:|
| 1,500 | $49 |
| 5,000 | $100 |
| 10,000 | $169 |
| 20,000 | $240 |
| 50,000 | $400 |
| 100,000 | $600 |
| 200,000 | $900 |
| 500,000 | $1,200 |
| 1,000,000 | $1,500 |

TheirStack charges 1 API credit per returned job, including job.new/job.closed webhook events. Its documentation says repeated API returns are billed independently, and the same record can be charged again if multiple webhooks/searches deliver it. This cost behavior differs from JobsPipe's once-per-job-per-calendar-month rule.

At 100,000 returned jobs/month, the current published comparison is approximately $149/month for JobsPipe Growth versus $600/month for TheirStack's 100k API tier. This is not a recommendation by price alone. Compare actual unique jobs, source coverage, India freshness, original apply URLs, duplicate/closed handling, terms, retention and redistribution rights before choosing.

**Commercial integration recommendation:** do not buy a large plan yet. Run a capped, short comparison against the same role/location/date sample on both vendors and our direct ATS feed. Use them only for additional source coverage or event delivery that direct permitted APIs cannot provide economically.

## 6. Current JobBeeper code state — do not mistake foundation for completion

The current state in branch v2-live-radar is:

### Already present

- ATS registry and global discovery candidate tables exist.
- Global ATS discovery module exists.
- Candidate-only Common Crawl discovery for Workday, Keka and Darwinbox exists.
- The sitemap/career-link scan is bounded to a submitted website and is not a global company-discovery engine.
- Candidate import stages records; it does not automatically create/activate every employer.
- A persistent per-board scheduler exists, with due times, leases, host budgets, cooldowns, retries/backoff and baseline handling.
- Existing collector adapters and normalization/upsert pipeline exist for the currently supported/configured sources.
- The previous architecture note documents PR #67 and its role as a discovery foundation.

### Current blockers

1. The Common Crawl path uses a bounded CDX query (limit 200) and does not harvest the full SURT-sorted S3 cluster.idx ranges across many crawl indices.
2. Discovery covers only the three Workday/Keka/Darwinbox families in its current Common Crawl provider set. It does not yet perform the six-provider S3 harvest described by open-ats-feed.
3. Discovery is manually triggered and not a durable autonomous multi-index discovery job.
4. Candidates do not move through a fully automated candidate → verified → active lifecycle under a clear provider policy.
5. The scheduler's configured_boards(config) and sync_config(...) currently derive schedules from company-board arrays in runtime configuration. The database schedule is persistent, but the registry is not yet the authoritative source of employer boards.
6. The current Dev snapshot discussed in the admin investigation had 10 explicitly configured boards across providers, including one Workday board (NVIDIA); the discovery registry showed zero records. This explains why the UI could show active scheduler boards while the discovery registry was empty.
7. User preferences currently handle job-matching criteria. Persistent per-user provider toggles still need to be added. An ephemeral source query filter is not the same as a saved user preference.

### Code areas the next agent must inspect first

- v2/global_ats_discovery.py — candidate discovery, current CDX query behavior and provider patterns.
- v2/board_scheduler.py — configured_boards(config), sync_config(...), claim_due_board(...) and status(...).
- The ATS registry schema and candidate staging/import functions — make the registry authoritative without breaking existing data.
- Provider collectors and job normalization/upsert path — ensure new DB-discovered board records can be converted to the existing collector input shape.
- v2/user_preferences.py and the API routes for preferences/jobs — add saved per-user provider selection after shared ingestion, not inside the global collectors.

Do not rewrite working collectors just to change discovery. First make the scheduler consume verified registry rows while preserving the existing lease, host-budget, cooldown, retry, baseline and telemetry behavior.

## 7. Target architecture and behavior

Common Crawl S3 range index + public directories + permitted career links  
→ Global candidate harvester  
→ Candidate records with provenance  
→ Provider-specific URL/token normalizers  
→ Public endpoint + policy verifier  
→ eligible / uncertain / blocked  
→ ats_board_registry (database source of truth)  
→ Persistent database-backed scheduler  
→ Provider collectors  
→ Shared normalized jobs corpus  
→ dedupe + first-seen tracking  
→ Per-user provider selection + matching  
→ Feed + opt-in notifications

### Required state model

Every discovered board needs an explicit lifecycle:

- candidate — URL/token found, not yet verified;
- verified — endpoint returned a valid provider response and policy checks passed;
- active — eligible for the central scheduler;
- empty — valid board, no current open postings;
- blocked — 403/robots/policy restriction; do not classify as dead or bypass;
- rate_limited — 429/Retry-After; persist host cooldown;
- error — transient/provider/schema failure; retry according to policy;
- stale/dead — repeated evidence supports deactivation;
- rejected — false positive or policy-ineligible.

Store provenance, crawl ID/date, first-seen/last-seen, verification response, host/tenant/site, last successful poll, next due time, HTTP outcome, consecutive failures, pagination/facet cursor and baseline state.

### Configuration boundary

Keep in runtime config:
- provider-level global enable/disable;
- provider rate/concurrency policy;
- poll cadence policy;
- endpoint/schema feature flags;
- approved credentials for licensed feeds, if any.

Remove from runtime config:
- the complete employer list for each ATS.

Store employer board inventory in the database registry.

### User provider toggles

Add saved per-user provider preferences such as enabled_sources = [workday, greenhouse, ashby, ...].

- Default new users to all approved providers enabled (or use the explicit product default chosen by the owner).
- A user turning Workday off filters Workday jobs from that user's feed/matches/alerts.
- It must not stop the shared Workday collector or remove Workday jobs for other users.
- Admin global disable is a separate override that stops collection for everyone and must explain the impact.
- UI labels must say provider/platform, not employer. A user should never see thousands of company boards.

## 8. Implementation plan and time estimate

Estimate assumes one engineer familiar with this repository, the existing collectors remain reusable, CI is available, and no upstream vendor changes its public endpoints during the work. This is a planning estimate, not a delivery promise.

| Phase | Work | Estimate |
|---|---|---:|
| 0. Baseline | Inspect registry/schema/collector contracts; run current full tests; capture a Dev baseline | 0.5–1 day |
| 1. Global discovery | S3 range harvester, resumable checkpoints, token parsing for Greenhouse/Ashby/Lever/Breezy/Recruitee/Teamtailor; add Workday/Keka/Darwinbox patterns and probes; candidate metrics | 3–5 days |
| 2. Registry-driven scheduler | Make verified active DB registry the source of truth; preserve existing leases, cooldowns, baseline and host budgets; safe migration/compatibility path | 3–5 days |
| 3. Per-user source controls | Persist provider toggles; filter feed/evaluation/alerts; add user-facing provider panel and admin global override separation | 1–3 days |
| 4. QA and performance canary | 24–72 hour Dev/QA live-feed canary, load/429/freshness tests, duplicate checks, UI validation, rollback evidence | 3–5 days |

**Expected end-to-end range:** approximately **10–19 engineering working days (2–4 weeks)** for a production-ready first release covering the core ATS families and the database-led scheduler. A limited proof of concept for the six well-documented public ATS families can be demonstrated in roughly **5–7 working days**, but that is not the completed global, production-safe architecture.

Workday/Keka/Darwinbox edge cases, additional ATS families, aggregator legal/procurement review and provider-specific rate-limit constraints can extend the schedule. Do not label the first proof of concept “all jobs from everywhere.”

## 9. Ordered next steps for the next agent

1. Read this file and docs/GLOBAL_JOB_INGESTION_WITHOUT_MANUAL_COMPANY_CONFIG_2026-11-10.md before changing code.
2. Inspect current branch head and Dev deployment. Record the exact commit and run the current V2 test suite before editing.
3. Build a small, resumable Common Crawl S3 range-harvest proof for Greenhouse/Ashby first. Verify counts against the public reference and record candidates/live/empty/blocked/errors separately.
4. Expand to Lever/Breezy/Recruitee/Teamtailor, then Workday/Keka/Darwinbox. Never convert unverified URLs directly into active boards.
5. Refactor scheduler input from config company arrays to eligible registry rows. Preserve the current scheduler's safety behavior and provide an idempotent migration for the existing 10 configured Dev boards.
6. Make the per-user provider toggle a post-ingestion filter. It must never control global polling.
7. Run a 24–72 hour live Dev/QA canary, with the same real ingestion path as production but isolated data/credentials where required. Do not use temporary/synthetic jobs as evidence of source freshness.
8. Report actual board counts, jobs per provider, p50/p95 first-seen latency, request volume, average response bytes, 403/429/5xx rates, unique-job yield and projected monthly cost.
9. Only then decide whether a 1–2 minute tier is feasible for selected providers or whether 5–15 minutes is the safe operating cadence.
10. Production promotion requires passing regression tests, Dev/QA verification, backup/rollback evidence and a cost/freshness review.

## 10. Architecture decision

**Proceed with global, automatic board discovery plus a database-backed internal board registry. Remove manual employer lists from runtime configuration. Add user-facing provider toggles as per-user filters over one shared ingestion corpus.**

Do **not** promise zero-delay job detection. Aim for a measured few-minute experience on supported, already-known boards, use upstream event/webhook delivery where legitimately available, and make discovery of new boards a separate continuous background process.

The reason for this switch is operational and product-level: the current model scales admin effort with the number of employers and makes the admin panel depend on company-by-company configuration. The target model scales collection through an automatically maintained catalogue, lets users choose ATS families rather than employers, and makes the freshness/cost trade-off measurable.

---

## Research references

- HiringCensus coverage snapshot (October 29, 2026): https://hiringcensus.com/stats/
- Jobless ATS index snapshot (September 20, 2026): https://jobless.dev/tools
- Open ATS Feed implementation and its measured coverage: https://github.com/veresk06/open-ats-feed
- Open ATS Feed S3 harvester: https://github.com/veresk06/open-ats-feed/blob/main/scripts/harvest-s3.mjs
- Greenhouse public Job Board API documentation: https://docs.greenhouse.io/job-board
- Lever public postings API documentation: https://github.com/lever/postings-api
- TheirStack webhook documentation: https://theirstack.com/en/docs/webhooks
- TheirStack credits: https://theirstack.com/en/docs/pricing/credits
- TheirStack current pricing: https://theirstack.com/en/pricing
- JobsPipe current plans: https://docs.jobspipe.dev/usage/plans
- JobsPipe rate limits and credit accounting: https://docs.jobspipe.dev/usage/rate-limits
- JobsPipe changelog (November 2026): https://docs.jobspipe.dev/changelog
