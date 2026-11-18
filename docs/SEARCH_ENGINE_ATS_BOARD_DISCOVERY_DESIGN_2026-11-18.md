# Search-engine-assisted ATS board discovery — 18 November 2026

## Decision

Build search-engine-assisted discovery as a **candidate source for company ATS boards**, not as another job-search collector. The search engine finds public pages that reveal employer board URLs. JobBeeper's existing provider collectors then fetch the complete public vacancy inventory from approved boards; the existing JobBeeper matching and dashboard filters decide which jobs are relevant.

The first implementation should be a deterministic Python worker that uses a licensed search API, the existing ATS URL normalizer, provider-specific public board probes, and the existing candidate import/review flow. **Do not scrape Google Search HTML or browser result pages. Do not introduce Google ADK for the first version.**

## Why the idea is useful

A query such as:

```text
site:myworkdayjobs.com "Software Developer" India
```

can expose Workday job pages whose URLs reveal both the tenant hostname and the career-site path. Those values are the identifiers needed by the Workday board collector. Equivalent search coverage can reveal boards hosted by Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Keka and Darwinbox.

Search should intentionally be broader than JobBeeper's normal job filters. A board discovery query can use a small set of role-family terms plus country/region to find likely companies. Once a board is verified and onboarded, the provider collector should retrieve all currently open postings exposed by that public board. JobBeeper should then apply saved role, experience, location, remote and score filters. Do not hard-filter discovery on an experience phrase: many indexed pages omit or express experience in non-standard ways, so doing so would hide otherwise useful employer boards.

Search index coverage is not exhaustive and indexing is not real time. A 30-minute schedule means JobBeeper checks for new indexed evidence every 30 minutes; it does not mean search engines discover or index each new careers page within 30 minutes.

## Search provider research

### Google results without scraping

Google documents operators such as `site:`, quoted exact phrases, exclusions, and date operators. The manual Google query is a useful way to validate query design.

Automated scraping of Google Search result pages is not an acceptable production integration. Google's policies prohibit automated querying/scraping without express permission. Google Custom Search JSON API is also a poor new dependency: it is closed to new customers and the published migration timeline ends on 1 January 2027.

### Preferred first adapter: DataForSEO Google Organic SERP API

DataForSEO exposes Google's organic result page as structured API output. Its documentation supports a structured `target` domain/subdomain/webpage filter with wildcard matching. This should be evaluated in preference to embedding `site:` inside every keyword: DataForSEO documents a 5x price multiplier for search operators such as `site:`, `inurl:` and `intitle:`.

The API offers Standard, Priority and Live queues. Current documentation lists Standard normal priority at about 5 minutes on average but gives a 45-minute target turnaround (extended processing may occur); Standard high priority is about one minute on average; Live averages up to about six seconds. A strict 30-minute worker should start with Priority, not Standard, because the Standard normal target can exceed the discovery interval. Treat all turnaround figures as vendor processing targets, not guarantees of search-index freshness. Record the API-returned cost per task and enforce a hard monthly/daily budget; do not assume the wildcard `target` parameter is free of operator-related billing until a live pilot confirms actual charged cost.

Candidate target patterns to test:

| ATS provider | Search target pattern | What must be extracted |
|---|---|---|
| Workday | `*myworkdayjobs.com*` | tenant host + career-site path |
| Greenhouse | `*greenhouse.io*` | board token on supported boards host |
| Ashby | `*ashbyhq.com*` | board identifier on `jobs.ashbyhq.com` |
| Lever | `*lever.co*` | employer slug / regional host |
| SmartRecruiters | `*smartrecruiters.com*` | company identifier |
| Workable | `*workable.com*` | account slug |
| Keka | `*keka.com*` | tenant + careers portal |
| Darwinbox | `*darwinbox.in*` | tenant + public candidate careers path |

The actual API request should use the role-family keyword and India location/language fields, with the ATS target as a separate structured parameter. Validate that returned organic URLs are actually constrained to the intended ATS provider domain. Preserve the exact query, target, engine, region, device, result URL, title, snippet, rank, response timestamp and API task cost for audit.

Illustrative Priority cost, before taxes or any account-specific charges:
- Two SERP tasks every 30 minutes: 2,880 tasks per 30-day month × $0.0012 ≈ **$3.46/month**.
- Eight provider targets every 30 minutes: 11,520 tasks per month × $0.0012 ≈ **$13.82/month**.

These are base-price estimates only. The 5x operator multiplier, number of returned SERP pages, extra tasks, and live account pricing can change the actual cost. The first pilot must save and inspect the API's returned cost field before any recurring schedule is enabled.

### Secondary option: Brave Search API

Brave's independent web index is a useful future cross-check, especially if Google-index coverage misses a provider or the primary vendor becomes unavailable. Its public pricing is listed at $5 per 1,000 requests, with a monthly credit for eligible accounts. Do not integrate two engines at once in the first release. Add Brave only after the Google-index adapter has demonstrated useful, unique board discovery.

### Not recommended now

- Google Custom Search JSON API: sunset/migration deadline makes it unsuitable for a new long-lived integration.
- Microsoft Bing Search APIs: the standalone Search APIs were retired in 2025; the successor grounding product is an agent-oriented Azure service, not a simple low-friction SERP feed for this pipeline.
- Direct Google HTML scraping, headless-browser SERP scraping or rotating proxies: fragile, policy-risky and not needed when licensed APIs exist.
- Google ADK: not required for a repeatable sequence of search → parse URL → verify provider → stage candidate. ADK adds an agent framework, model/tool orchestration and evaluation surface without solving the core deterministic problems. Consider an LLM/ADK helper later only for ambiguous employer identity or evidence summarization, with human review and no authority to link/activate boards.

### Complementary discovery surfaces

Search-engine results should be one source in a source-diverse candidate funnel, not the only discovery mechanism:

- **Official employer career pages:** use the existing bounded, robots-aware crawler to find links to ATS tenants and preserve the canonical employer page as ownership evidence.
- **Public XML sitemaps and sitemap indexes:** use the existing sitemap scanner for companies already known from a directory, prior search result, customer-provided list, or another discovery source. Sitemap presence is evidence of a page, not proof that a page is a live job board.
- **Common Crawl CDX:** keep the existing global index query as a broad, low-cost historical discovery source. It can surface ATS URL patterns missed by current search indexes, but results can be stale and must be re-probed.
- **Independent web indexes:** consider Brave Search only after the first Google-index pilot has a measured unique-board yield. Brave uses its own independent index, so it can add coverage rather than merely duplicate Google results.
- **Curated directories and provider-native public endpoints:** ingest attributed directories as unverified candidates and use provider APIs only after the exact public board identity is known.

Do not add DNS/certificate-transparency enumeration, arbitrary web crawling, or an autonomous browser agent to the first release. Those sources create a large noisy host set and do not directly prove an employer-to-board relationship. They can be evaluated later against measured incremental candidate yield.

## Proposed 30-minute discovery cycle

1. **Select a bounded query batch.** Keep role-family seeds configurable, e.g. Software Developer, Software Engineer, Backend Engineer, Frontend Engineer, Full Stack Engineer, Python Developer and Automation Engineer. Do not multiply every role synonym by every ATS target on every cycle.
2. **Rotate provider targets.** A low-cost starting plan is two provider targets per 30-minute cycle, rotating through all eight providers. That checks each provider approximately every two hours. If measured unique discovery value justifies it, move to all eight targets each cycle.
3. **Query a licensed SERP API.** Use India and English locale settings. Store API task ID, query, target, execution time, returned result count and actual charged cost.
4. **Extract candidate URLs only.** Accept HTTPS public URLs; reject credentials, non-standard ports, arbitrary schemes, unrelated hosts and overly long URLs. Deduplicate by normalized `(provider, candidate_host, board_key)`.
5. **Normalize with existing code.** Reuse `board_discovery.detect_ats_board()` and `_normalise_global_ats_candidate_url()`. Do not create a second URL parser or a separate board identity format.
6. **Verify cheaply and politely.** Use the exact provider's existing public board endpoint probe. Bound response size, requests, redirects and timeout. Respect 429/Retry-After and provider cooldowns. A 200 response must also have the expected provider schema; where practical require evidence of a valid public board, not just any HTTP page.
7. **Stage a review-only candidate.** Add `discovery_method='search_engine'` and a durable source reference to the existing global candidate importer. Do not create employer records, link a candidate, mark it verified, activate it, schedule it, or emit notifications from the discovery worker.
8. **Review identity and ownership.** Prefer the official employer careers page linking to the same ATS board, together with a valid provider response. A SERP result alone does not prove the board belongs to the employer whose name appears in its snippet. Keep ambiguous, conflicting or shared-host records in manual review.
9. **Onboard through the existing guarded flow.** An admin links the candidate to the canonical employer record; a separate verification/activation gate controls registry state and scheduler inclusion. Keep the current explicit production allowlist unchanged until individual approvals are complete.

## Persistence and safety requirements

Use the existing `ats_global_discovery_candidates` as the normalized review queue. Add a small search audit store rather than a second company or board table. Suggested tables:

- `search_discovery_runs`: engine, provider target, query seed, locale, task ID, started/finished timestamps, outcome, HTTP status, result count, actual cost, and error type.
- `search_discovery_results`: run ID, canonical result URL, title, snippet, rank, source timestamp, normalized provider/key/host, and candidate ID where one was staged.

Requirements:
- unique idempotency on canonical provider/host/board key;
- retain provenance across repeated discoveries and newer/older result timestamps;
- terminal candidate statuses (linked/rejected) are never reopened by later search results;
- serialized worker lease and per-engine/per-target request budgets;
- explicit monthly spend ceiling and a stop switch;
- request timeout, response byte caps, bounded result page count and bounded candidates per run;
- retry only according to provider/API Retry-After and persistent cooldown;
- robots/terms review for any follow-up page crawl; SERP result collection itself uses the licensed API contract;
- no automatic broad crawling of every URL surfaced by search;
- no notifications and no effect on Telegram/member settings;
- dashboard/source-health evidence should distinguish search discovery runs from actual ATS job-collection runs.

The current production app already has candidate-only Common Crawl and robots-aware sitemap discovery code, but those are exposed as admin-triggered endpoints, not an autonomous recurring scheduler. Production currently has zero rows in `global_ats_discovery_runs`. This new feature therefore needs an explicit persistent scheduler; it should not silently claim the existing code is already scanning every 30 minutes.

## Pilot gates

### Gate 0 — no production writes

- Use a DataForSEO trial/API account or a separately provisioned secret in the QA environment. Never paste credentials into chat, source files, docs or command history.
- Manually test the wildcard `target` filter on all eight provider domains using a small number of role seeds.
- Compare returned URLs with the manual `site:` query and verify result-domain containment.
- Save the real per-task cost, result count, duplicates, malformed URLs and valid candidate count.
- Compare Google results with official employer careers links and existing Common Crawl/sitemap discovery.
- Do not add any result to the production database during this stage.

### Gate 1 — deterministic QA worker

- Implement the DataForSEO adapter behind an interface so it can be disabled independently.
- Add parser/normalizer tests for all eight ATS providers, result pagination caps, malicious URLs, duplicate board identity, stale results, 429/Retry-After, API errors, timeout, budget exhaustion and idempotent replays.
- Add worker lease, persistent due times and bounded target rotation.
- Test that discovery imports candidates only and has zero side effects on employer records, registry activation, schedule count, job inventory and notifications.
- Run for at least 24 hours in isolated QA and measure candidate precision, unique boards per dollar, overlap with Common Crawl/sitemaps and duplicate ratio.

### Gate 2 — controlled production canary

- Require a fresh production backup and reviewed, exact-head CI.
- Start with a very small target rotation and conservative spend cap.
- Stage candidates only; verify production schedule/registry count remains exactly unchanged.
- Review every candidate's employer identity and provider response before any manual onboarding.
- Expand cadence only if discovery yields useful unique boards at acceptable cost and no impact to job ingestion.

## Current project integration points

- `v2/global_ats_discovery.py`: existing Common Crawl and public sitemap candidate discovery, persisted cooldowns and audit runs.
- `v2/board_discovery.py`: provider URL detection, canonical board shape and public board API probes.
- `v2/radar.py`: `_normalise_global_ats_candidate_url()`, `import_global_ats_candidates()`, admin review/link routes and discovery endpoints.
- `ats_global_discovery_candidates`: existing review-only candidate store.
- `v2/board_scheduler.py`: production scheduler; only explicitly active registry boards should sync to poll schedules.

Do not integrate search directly into the job collector loop. Keep search API usage and provider board polling as separate subsystems with separate rate limits, observability and failure domains.

## External references

- Google Search operators: https://support.google.com/websearch/answer/2466433
- Google Search spam policies / machine-generated traffic: https://developers.google.com/search/docs/essentials/spam-policies
- Google Custom Search JSON API overview and migration notice: https://developers.google.com/custom-search/v1/overview
- DataForSEO Google Organic SERP API pricing: https://dataforseo.com/pricing/google-serp/google-organic-serp-api
- DataForSEO Google Organic SERP API reference: https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
- Brave Search API documentation: https://api-dashboard.search.brave.com/app/documentation/web-search
- Brave Search API pricing: https://brave.com/search/api/
- Google Agent Development Kit overview: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
