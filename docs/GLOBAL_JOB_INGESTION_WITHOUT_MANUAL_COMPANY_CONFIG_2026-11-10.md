# Global job ingestion without manual company configuration

**Date:** 2026-11-10  
**Repository:** `AvinashBhalla/job-beeper`  
**Branch:** `v2-live-radar`  
**Status:** Research conclusion and implementation direction; no code or runtime behavior changed by this document.

## Executive conclusion

JobBeeper should not ask users to configure employers or ATS boards. It should maintain a shared, internal employer-board catalog that is populated automatically from public discovery sources, validated against each ATS's public job-posting endpoint, and consumed by a database-backed per-board scheduler.

There are two viable ways to obtain broad coverage:

1. **Build our own global board catalog.** Use Common Crawl's URL index and public ATS directories to discover employer board identifiers, probe them, and poll eligible public feeds. This avoids a paid data dependency and gives us source-level control, but requires a substantial discovery and operations pipeline.
2. **Use a global job-data API.** Providers such as TheirStack or JobsPipe expose cross-company, multi-source search APIs. This can provide broad coverage immediately, but adds per-job costs, a vendor dependency, and data-redistribution/licensing questions.

Recommended direction: **hybrid**. Build direct-source ATS ingestion from a global board catalog, and run a small, measured evaluation of one commercial aggregator for sources that cannot be reached through permitted public feeds. Do not make LinkedIn or Naukri scraping the foundation of the product.

The critical distinction is:

> No user-facing company configuration does not mean no employer identifiers exist. It means JobBeeper discovers and maintains those identifiers internally instead of asking users to supply them.

## What the reference product establishes

The public JobBeeper site exposes role-based browse pages and says fresh matches are added regularly. The earlier public-site research checkpoint in `docs/PRODUCT_REVERSE_ENGINEERING_2026-11-08.md` recorded the product's marketing claims about broad source coverage and a large monitored career-page/company inventory. Those are marketing/coverage claims, not independently verified counts or proof of its private implementation.

The authenticated browser investigation recorded a server-fetched job feed, server-side keyword search, numeric pagination, source labels, and separate detail requests. It did not reveal the private ingestion backend, the board registry, or how new employers are discovered.

Therefore, we can reproduce the observable product behavior and build a credible equivalent architecture, but we must not claim to know JobBeeper's exact internal implementation from its UI.

## The key discovery method: Common Crawl is a global ATS board index

A public ATS board URL usually contains the employer's board identifier:

| ATS | Public board URL pattern | Identifier to extract |
| --- | --- | --- |
| Greenhouse | `boards.greenhouse.io/{token}` | First path segment |
| Ashby | `jobs.ashbyhq.com/{token}` | First path segment |
| Lever | `jobs.lever.co/{token}` | First path segment |
| Breezy | `{token}.breezy.hr` | Subdomain |
| Recruitee | `{token}.recruitee.com` | Subdomain |
| Teamtailor | `{token}.teamtailor.com` | Subdomain |
| Workday | `{tenant}.wd{cluster}.myworkdayjobs.com/{site}` | Tenant, cluster, site |
| Keka | `{tenant}.keka.com/careers/{portal}` | Tenant and portal/path |
| Darwinbox | `{tenant}.darwinbox.in/ms/candidatev2/{companyId}/careers` | Tenant and company ID |

Common Crawl's URL index contains archived URLs from across the web. This makes it possible to discover ATS board identifiers without first having a list of company names.

A recent public implementation, `veresk06/open-ats-feed`, demonstrates the method concretely:

- It treats Common Crawl's SURT-sorted `cluster.idx` files as a searchable global index.
- It uses HTTP range requests and binary search to locate only the index blocks for the relevant ATS host prefixes instead of downloading an entire index.
- It extracts board tokens from archived URLs.
- It probes each candidate against the ATS vendor's public API and separates live, empty, dead, blocked and error outcomes.
- Its published September 2026 measurement reported 32,545 candidate tokens, 18,164 live boards, and 439,867 live postings across Greenhouse, Ashby, Lever, Breezy, Recruitee and Teamtailor. These are measured results for that project's scope/date, not a guarantee of our coverage.

This is the missing mechanism that lets us discover thousands of employers without entering each employer in a configuration file.

Useful implementation reference:
- https://github.com/veresk06/open-ats-feed
- https://github.com/veresk06/open-ats-feed/blob/main/scripts/harvest-s3.mjs
- https://github.com/veresk06/open-ats-feed/blob/main/scripts/verify-coverage.mjs
- https://github.com/veresk06/open-ats-feed/blob/main/scripts/lib/tokens.mjs

The project itself explains why it reads Common Crawl's S3 index files rather than relying on the CDX query service as its unattended critical path: the CDX application server failed during its large sweep, while the public S3 index remained available.

### Seed directories are useful, but not the whole solution

A public CC BY 4.0 dataset, LastRound AI's ATS directory, maps 9,935 companies to Greenhouse, Lever and Ashby board slugs. It is useful as a bootstrap seed, but it is not a live or complete census.

- https://github.com/fyrosofttech/lastroundai-hiring-data/tree/main/ats-directory

Another recent public directory reports 12,244 live board addresses across eight ATS platforms. Any third-party directory must still be treated as a dated candidate list and re-probed before activation.

The right model is to combine seed directories with our own recurring discovery sweeps, not to rely on any one CSV as the entire company universe.

## Important limitation: ATS APIs are usually per employer

The public ATS APIs are not generally global search APIs. For example, Greenhouse, Ashby and Lever expose a public feed for a particular board slug. There is no single vendor endpoint that returns every employer's jobs.

So a direct-source platform needs two layers:

1. **Global discovery:** find employer board identifiers automatically.
2. **Per-board collection:** call the public feed for each verified board and normalize its jobs.

The board catalog is an internal operational registry, not user configuration. The user should never need to know what a Greenhouse token, Ashby slug, Workday tenant, or Keka portal is.

## What is already in our repository—and what is still missing

### Already present

- The ATS board registry stores provider, board key, public board URL, confidence and review state.
- The global candidate table stores provider, candidate host, board key, URL, discovery method and source provenance.
- The public ATS discovery module supports Common Crawl candidate discovery for Workday, Keka and Darwinbox, plus a bounded, robots-aware sitemap/career-link scan for one submitted website.
- The global-candidate importer stages candidates only; it does not silently create or activate employer boards.
- PR #66 added a persistent per-board polling scheduler with due times, host budgets, leases, cooldowns and baseline handling.
- The legacy seeded directory importer provides a starting roster for Greenhouse, Lever and Ashby.

PR #67 is merged on `v2-live-radar`. Its discovery module is a safe foundation, but it is not yet the global, autonomous company-agnostic collector described in this document.

### Current limitations to fix

1. `v2/global_ats_discovery.py` currently targets only Workday, Keka and Darwinbox in its Common Crawl provider set.
2. It queries `index.commoncrawl.org` with a `limit=200` per request. This is a bounded sample, not a complete multi-index token harvest.
3. It processes one Common Crawl request per manual admin trigger; it does not run a durable, unattended multi-index sweep over all supported ATS host patterns.
4. Sitemap discovery accepts one submitted website URL. It is not a global seed discovery engine on its own.
5. Global candidates still require an admin linking/review workflow before they become employer board records.
6. The board scheduler derives its active schedules from the configured source arrays. It is not yet driven directly by a continuously verified database catalog.
7. Adding newly discovered companies still involves changing the global source configuration/allowlist, which is precisely the operational dependency we want to remove.

### Required architectural change

Make `ats_board_registry` the authoritative internal inventory of boards to poll. The scheduler should claim eligible active boards from the database rather than requiring each board to be copied into `config.json` arrays.

Keep provider-level settings in config (global enable/disable, rate limits, safety policy, page sizes and credentials where applicable). Do not keep the discovered employer universe there.

The registry should contain at least:

- provider and provider-specific board key;
- canonical public board URL and host/tenant/site identifiers;
- company display name/domain when recoverable;
- discovery source, crawl ID, first-seen and last-seen times;
- robots/terms decision and verification evidence;
- liveness state: candidate, verified, active, empty, dead, blocked, rejected or stale;
- last HTTP status/error class, last successful poll, next due time and consecutive failures;
- provider-specific pagination/facet cursor and baseline state.

## Proposed end-to-end architecture

```text
Global discovery inputs
  ├─ Common Crawl S3 URL-index sweeps (SURT host prefixes)
  ├─ Public, attributed ATS company directories
  ├─ Public career-page links and sitemaps (as a supplement)
  └─ Permitted global job-data APIs (optional fallback)
                |
                v
      Candidate board catalog
      (provider + token + URL + provenance)
                |
                v
      Safe endpoint verifier
      (schema + status + robots/policy + host budget)
                |
         eligible public feeds
                |
                v
      Active ATS board registry
      (database-backed, no company config arrays)
                |
                v
      Persistent per-board scheduler
      (leases + jitter + cooldown + cursors + baseline)
                |
                v
      Provider adapters
      (fetch + normalize + checkpoint)
                |
                v
      Shared jobs table + canonical dedupe
                |
                v
      Per-user evaluations and filters
      (roles + skills + locations + experience + exclusions)
                |
                v
      Per-user feed and opt-in notifications
```

User profiles must never be passed to ATS discovery or collection workers. Collection is global; matching and alert delivery are tenant-scoped after shared ingestion.

## Provider access and safety boundaries

Not every job source has an open, global read API:

- **Greenhouse, Ashby, Lever, Breezy, Recruitee and Teamtailor:** strong candidates for direct public-board adapters, subject to current provider/path policy checks and request limits.
- **Workday, Keka and Darwinbox:** board-specific public career endpoints can be discovered from host/path patterns, but require provider-specific URL parsing and careful per-board verification. Do not assume every tenant behaves the same way.
- **SmartRecruiters and Personio:** a reachable endpoint is not automatically an authorized endpoint. The open-ATS-feed research declined some feeds based on robots.txt restrictions. Re-check the exact live and archived rules before using any path.
- **Naukri:** this research did not identify an open public job-search API. Naukri's documented integrations surfaced here are employer/recruiter integrations. Treat Naukri as requiring an approved commercial feed or a vetted data provider unless a permitted public read path is established.
- **LinkedIn:** its official Job Posting API is restricted to approved partners and is for posting jobs to LinkedIn, not a general public search/download API. LinkedIn's API terms explicitly restrict accessing LinkedIn content through scraping/crawling outside its APIs. Do not make unofficial authenticated scraping or anti-bot bypass a core production dependency.

The fact that JobBeeper's UI labels a source as LinkedIn or Naukri does not disclose how it obtains that data or whether it has a partner/vendor arrangement. We cannot infer that private implementation from the UI.

References:
- https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview
- https://developer.linkedin.com/legal
- https://support.greenhouse.io/hc/en-us/articles/16297968058651-Naukri-integration
- https://help.workable.com/hc/en-us/articles/26298085189271-Integrating-with-Naukri

## Commercial global-feed alternatives

These are worth a controlled sample comparison; neither should be adopted on marketing claims alone.

### TheirStack

- Documents search over jobs from thousands of websites and supports filtering by title, country, source domain and posting age.
- Provides `job.new` and `job.closed` webhooks driven by saved searches.
- Charges 1 API credit per returned job; the public pricing page currently shows 1,500 monthly API credits for $49 and larger tiers.
- Its public pricing page reports a 225M-record jobs dataset and 305k new records/day. Those are vendor-reported figures.
- Its India coverage page reports 15.7M live postings from 27,111 sources and lists Naukri, LinkedIn, Indeed and Workday among the sources. These are vendor-reported coverage figures.

### JobsPipe

- Documents one normalized `POST /v1/jobs/search` endpoint over 30+ sources, without requiring a company identifier in the query.
- Charges 1 credit per job returned per calendar month.
- Public monthly plans currently list $19.60 for 10,000 credits, $49 for 25,000, $149 for 100,000 and $399 for 300,000.
- JobsPipe's webhook documentation describes job-closed and alert-match events; new job discovery can also be handled through saved Signals or periodic searches.

These providers can bridge sources that are difficult to ingest directly, but they introduce job-level costs and a data-redistribution/licence dependency. Before using one in production, verify its exact source list, India coverage, posting freshness, original apply URLs, duplicate semantics, closed-job handling, rate limits and contractual rights to store/display the returned postings to our users.

References:
- https://theirstack.com/en/docs/api-reference/jobs/search_jobs_v1
- https://theirstack.com/en/pricing
- https://theirstack.com/en/docs/webhooks
- https://theirstack.com/en/job-postings-data/india
- https://docs.jobspipe.dev/api-reference/jobs-search
- https://docs.jobspipe.dev/usage/plans
- https://docs.jobspipe.dev/api-reference/webhooks

## Recommended execution sequence

### P0 — Prove global board discovery without a company list

1. Add a Common Crawl S3 `cluster.idx` range harvester based on the reproducible SURT method in `veresk06/open-ats-feed`.
2. Start with Greenhouse, Ashby, Lever, Breezy, Recruitee and Teamtailor; add Workday/Keka/Darwinbox as provider-specific token parsers and public endpoint probes.
3. Seed from the attributed 9,935-company ATS directory, but deduplicate and verify every record.
4. Sweep several crawl indices with durable per-crawl/per-host checkpoints. Record candidate tokens and capture dates; never interpret an archive hit as a currently active board.
5. Produce a measured report: candidates harvested, live/empty/dead/blocked/error boards, jobs returned, and provider-level request cost.

### P1 — Remove the config-array dependency

1. Make the verified board registry the scheduler's source of truth.
2. Add an explicit provider policy: auto-activate only feeds whose public access and usage rules pass verification; quarantine uncertain/blocked providers.
3. Keep the existing per-board scheduler's leases, cooldown, baseline and request budgets, but have it consume registry rows.
4. Make add/remove/disable actions update the registry and schedule, not rewrite a large `config.json` employer list.

### P2 — Measure coverage and freshness

Run a 24–72 hour canary on a bounded provider roster. Measure unique jobs per 1,000 board polls, first-seen latency, 429/403/5xx rates, board liveness decay, duplicate rate, and empty-board frequency. Use those measurements to set a realistic cadence and decide which provider families deserve more coverage.

### P3 — Evaluate one aggregator for the hard sources

Run the same set of role/location/date queries against TheirStack and JobsPipe, and compare against our direct-source canary. Compare actual job IDs, source mix, posting dates, original apply URLs, unique jobs, stale/closed results and credits consumed. Do not subscribe or enable a recurring sync until the trial proves its incremental value and rights are clear.

## Acceptance criteria

- A newly discovered public ATS board can be added to the internal registry without editing `config.json` or entering a company by hand.
- A new user can complete onboarding with role/location preferences and receive jobs from the existing shared corpus; no source setup is required from that user.
- Discovery and ingestion run once for the service, not once per user.
- Every posting retains source/provider, source URL, original apply URL, first-seen timestamp, published timestamp when trustworthy, last-seen timestamp, and source provenance.
- Each board has an observable verification state, poll schedule, cooldown, error classification and completeness marker.
- No blocked/403/robots-disallowed provider is silently counted as a dead company or retried through proxy/TLS/CAPTCHA evasion.
- Re-ingestion does not create duplicate job rows or duplicate canonical opportunities.
- Per-user preference changes only recalculate that user's evaluations and notification eligibility.
- Production promotion requires measured canary results, a passing CI suite, backup/rollback evidence and dev/QA validation.

## Decision

**Proceed with the global board-catalog path as the core direct-source architecture.** PR #67 is a candidate-discovery foundation, not the completed global discovery system. Its next meaningful step is not more company form fields: it is an exhaustive, resumable ATS-token harvest, live verification, and a scheduler driven from the database board registry. Keep TheirStack/JobsPipe as measured commercial fallbacks for sources that cannot be safely/legally collected directly.
