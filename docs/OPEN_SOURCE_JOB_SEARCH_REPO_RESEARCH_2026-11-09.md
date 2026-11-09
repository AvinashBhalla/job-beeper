# Open-source job-search and ATS ingestion projects — research

**Research date:** 2026-11-09
**Purpose:** reusable patterns for JobBeeper's P0 global discovery, low-latency ingestion and rate-limit resilience.

> Stars and job counts are snapshots or project/vendor claims, not service-level guarantees. A large star count does not prove source coverage, data freshness, rate-limit safety or commercial data rights.

## Shortlist

| Project | Approximate stars / forks | Main strength | Recommended use |
|---|---:|---|---|
| [Freehire](https://github.com/strelov1/freehire) | 3.4k / 373 | Large multi-ATS catalogue, per-provider run-once workers, outboxes, shardable board crawls and dedup | **Primary ingestion architecture reference** |
| [Career-Ops](https://github.com/career-ops-hq/career-ops) | 80.6k / 14.8k | Reverse ATS directory scans, public board discovery, checkpoints and per-host concurrency | **Primary discovery/rate-control reference** |
| [JobSpy](https://github.com/speedyapply/JobSpy) | about 4.7k / 927 | Python job-board adapters (LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google, etc.) | Optional non-ATS board reference |
| [ats-scrapers](https://github.com/kalil0321/ats-scrapers) | 151 / 37 | Python adapters for Workday, Greenhouse, Lever, Ashby, SmartRecruiters, SuccessFactors; shared async retry/backoff/error mapping | **Best Python adapter reference** |
| [JobNavigator](https://github.com/vesaias/JobNavigator) | 184 / 52 | FastAPI multi-account job-hunt app, ATS handlers, browser extension and application assistance | Product UX reference |
| [Job Board Aggregator](https://github.com/Riley-Dorrington/job-board-aggregator) | 181 / 40 | Common Crawl-derived ATS company discovery, daily pipeline, per-platform worker budgets and anomaly monitoring | Discovery/observability reference; **do not reuse CC BY-NC datasets commercially** |

Star counts are rounded snapshots observed around 2026-11-09. GitHub search snapshots show Freehire at 3.4k stars/373 forks, Career-Ops around 80.6k/14.8k, JobNavigator 184/52, ats-scrapers 151/37 and Job Board Aggregator 181/40. JobSpy is reported around 4.7k/927 by an ecosystem snapshot. They are not performance scores.

## 1. Freehire — strongest end-to-end ingestion architecture

Repository: https://github.com/strelov1/freehire
Code licence: MIT
Stack: Go/Fiber, PostgreSQL + pgvector, sqlc, Meilisearch, Redis, S3-compatible storage, SvelteKit.

The project reports a 2026-10-30 snapshot of 4,785,488 unique open postings across 701,972 companies and 421 sources. Its README also describes 168 ATS platforms and 437 combined sources in a newer summary; those are project-maintained figures, not independently audited guarantees.

Its architecture docs and cmd/ingest show:

- API server is separate from run-once workers. Each provider is ingested by a standalone process, so one slow provider does not block another.
- One provider can be sharded round-robin when its board catalogue is too large for one run.
- Boards live in a first-party catalog with provider, board and region. New board submissions begin pending; verification precedes activation.
- Each board is validated against the adapter registry before any request.
- The pipeline normalizes postings and uses a stable unique (source, external_id) key for idempotent upserts.
- Persistent board failure backs off on a recorded cooldown rather than hammering every run.
- New/content-changed jobs enter transactional outboxes. Unchanged recrawls refresh last_seen cheaply and do not trigger enrichment/reindex.
- Search indexing is handled by a separate batch drain; batching replaced many direct per-board index pushes.

**What JobBeeper should borrow:** board catalog lifecycle, provider-isolated workers, idempotent external IDs, persistent per-board cooldown, outboxes, unchanged-content fast path and separate batched search indexing.

**What not to copy wholesale:** Freehire is Go/Postgres/Meilisearch/Redis at multi-million record scale. JobBeeper is currently Python/FastAPI/SQLite. Adopt the invariants and queue boundaries first; move infrastructure only when measured load requires it.

## 2. Career-Ops — strongest reverse-discovery reference

Repository: https://github.com/career-ops-hq/career-ops
Code licence: MIT; its public company-directory dataset has a separate licence.
Relevant files: scan-ats-full.mjs, providers/, docs/KEEPING_PORTALS_LIVE.md.

Career-Ops has normal scan (curated portals.yml) and scan:full, which reverses direction and walks public company directories for Greenhouse, Lever, Ashby, Workday, iCIMS, BambooHR, Paylocity and Join.

The reverse scan:
- Caches source directories for 24 hours.
- Supports --limit, per-ATS selection, checkpoints and resume.
- Uses provider-specific concurrency because API host topology differs.
- Values observed/tuned in scan-ats-full.mjs include 6 concurrent workers for Greenhouse/Lever/Ashby shared hosts, 2 for Paylocity and Join, and 20 for Workday's per-tenant hosts.
- Documents real 429-induced incomplete sweeps and cooldown recovery; it does not claim to bypass rate limits.

**Important licence boundary:** the external Feashliaa/job-board-aggregator company dataset used by the scanner is CC BY-NC 4.0. Do not copy that dataset into commercial JobBeeper without permission. The scanner's own MIT-licensed code and per-host concurrency logic are useful references; use a separately licensed directory or build our own.

Career-Ops is local-first and user-operated. It is not a central multi-user crawler with JobBeeper's shared registry, scheduler, database and per-user notification delivery. Those server-side pieces are still ours to build.

## 3. ats-scrapers — best Python adapter reference

Repository: https://github.com/kalil0321/ats-scrapers
Licence: MIT.

The README describes adapters for Workday, Greenhouse, Lever, Ashby, SmartRecruiters and SuccessFactors, alongside a hosted dataset client.

The base adapter expects async afetch() and asks providers to use BaseScraper.make_fetcher(). The shared fetcher centralizes retries, backoff, error mapping and HTTP-engine escalation. The 0.1.0 release notes report 52 reusable adapters and 1,035 offline tests; the hosted dataset is a separate service and should not be confused with the package's direct adapters.

**What JobBeeper should borrow:** a small typed provider protocol, common fetch wrapper, status taxonomy, bounded retries and a test suite per adapter. Do not add it as a runtime dependency without checking dependency footprint and overlap with our existing providers.

## 4. Job Board Aggregator — useful Common Crawl + operations pattern, with a dataset restriction

Repository: https://github.com/Riley-Dorrington/job-board-aggregator
Licence: MIT for code; CC BY-NC 4.0 for bundled company datasets.

Its README describes seven ATS adapters: Greenhouse, Lever, Ashby, BambooHR, iCIMS, Paylocity and Workday; a Common Crawl CDX discovery pipeline using 20+ ATS domain patterns and multiple snapshots; daily GitHub Actions ETL; deduplication and 30-day pruning; daily per-platform trend history and anomaly detection.

The README lists worker caps of 50 Workday, 30 Greenhouse/Lever/iCIMS, 10 BambooHR and 5 Ashby/Paylocity. Actual scripts/scraper.py shows explicit jitter/retry handling for Ashby, BambooHR and Paylocity, while the shown Greenhouse/Lever fetch functions have no comparable retry/backoff loop. Treat these as one reference point, not safe defaults for every environment.

The company lists in data/ are explicitly CC BY-NC 4.0. **Do not reuse those curated JSON datasets in commercial JobBeeper without permission.** The MIT-licensed scraper and anomaly-monitoring code may be studied/adapted while retaining notices.

## 5. JobSpy — useful for job-board search, not direct ATS market coverage

Repository: https://github.com/speedyapply/JobSpy
Licence: MIT.

JobSpy focuses on boards and aggregators such as Indeed, LinkedIn, Glassdoor, ZipRecruiter and Google. It is not a global employer ATS directory. Consider it later for non-ATS channels after reviewing platform rules, throttling, pagination caps and maintenance state.

The current ecosystem notes report per-site result caps and throttling; LinkedIn bursts can produce 429s and Glassdoor is rate-limited. It is not a route to unlimited scraping.

## 6. JobNavigator — product UX reference

Repository: https://github.com/vesaias/JobNavigator
GitHub snapshot: 184 stars / 52 forks.

It is a self-hosted FastAPI/React/Postgres job-hunt application with ATS handlers, browser extension, résumé tailoring and application tracking. Its README lists 13 ATS handlers and several discovery channels.

**What to study:** board onboarding, account isolation, résumé-to-job workflow and user-facing application assistance. Assess external data rights and authenticated-source policy before borrowing any collection path.

## 7. What stars do and do not say

Stars indicate community attention. They do not establish p50/p95 ingestion latency, ATS board discovery recall, success rate, 429 rate, live-posting freshness or commercial data rights.

For our own benchmark, record per provider and board:
1. candidates discovered, verified, active and stale;
2. success / 403 / 404 / 429 / 5xx counts;
3. p50/p95 request time and full poll duration;
4. posting timestamp precision and first-seen delay;
5. duplicate/repost rates and jobs closed on a later poll;
6. worker backlog, queue age, retries and cooldown time.

Do not increase concurrency until the board's host topology and observed throttling support it.

## Decision

- **Architecture:** use Freehire's provider workers, board catalog, cooldown and outbox invariants.
- **Discovery:** use Career-Ops' reverse-directory/checkpoint pattern, but not its CC BY-NC company data.
- **Python adapters:** study ats-scrapers for fetcher/provider contracts.
- **Candidate seed data:** use the separately licensed LastRound AI CC BY 4.0 snapshot bundled in this feature branch, not CC BY-NC datasets.
- **External boards:** consider JobSpy separately after the direct ATS path is sound.
- **Product workflow:** study JobNavigator, not its collection strategy as a performance guarantee.
