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

### Provider-neutral first pilot: DataForSEO Live target vs Serper

DataForSEO exposes Google's organic results as structured API output and supports a wildcard `target` domain/subdomain/webpage filter. Critical endpoint limitation: the structured `target` parameter is supported on the Live Google Organic endpoints, but not the queued Standard/Priority Task POST endpoint. Therefore `target` plus a strict 30-minute cadence means using Live mode. If using Standard/Priority queues, put the provider restriction in the keyword with `site:`; DataForSEO documents a 5x multiplier for operators such as `site:`, `inurl:` and `intitle:`. Do not model Priority plus structured target as a supported combination.

Current published timings: Standard normal priority averages about 5 minutes but has a 45-minute target (extended processing may occur); Standard high priority averages about one minute; Live averages about six seconds. A 30-minute worker can use Live + structured target, or Priority + `site:` query, but not Priority + structured target. Search-index freshness remains outside our control. Preserve actual task cost and enforce a hard budget.

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

For DataForSEO Live, use the role-family keyword and India location/language fields, with the ATS target as a separate structured parameter. Validate that returned organic URLs are actually constrained to the intended ATS provider domain. DataForSEO also warns that Google may wrap result URLs in redirect/goto links; if the returned URL/domain is google.com, the target filter may not expose the underlying ATS URL. Measure this failure mode in the benchmark and safely resolve only well-formed Google redirects. Preserve the exact query, target, engine, region, device, result URL, title, snippet, rank, response timestamp and API task cost for audit.

Illustrative monthly costs for one SERP per provider target (30-day month; before taxes/account-specific terms):
- DataForSEO Live + structured target: 2 targets every 30 minutes = 2,880 SERPs × $0.002 ≈ **$5.76/month**; all 8 targets every 30 minutes = 11,520 SERPs × $0.002 ≈ **$23.04/month**.
- DataForSEO Priority + `site:` query (5x operator multiplier): 2,880 × ($0.0012 × 5) ≈ **$17.28/month**; 11,520 × ($0.0012 × 5) ≈ **$69.12/month**.
- DataForSEO Standard + `site:` query: approximately **$8.64/month** for 2 targets or **$34.56/month** for 8 targets, but the 45-minute target turnaround is too loose for a strict 30-minute cycle.
- Serper: nominal usage is about **$2.88/month** for 2 targets or **$11.52/month** for 8 targets at the $1/1k starter rate, but its current entry purchase is a $50 prepaid 50k-credit pack valid for six months. The effective cost at low cadence is therefore affected by the prepaid minimum and expiry.

These are estimates, not a spend authorization. The first 50-query benchmark must save actual returned cost/credits, direct ATS URL coverage, duplicates and verified-board yield. Do not enable a recurring schedule until a monthly cap and provider are explicitly approved.

### Other search API candidates

**Serper (Google SERP API)** is the strongest price/performance alternative to benchmark against DataForSEO. Its current pricing lists a $50 prepaid pack for 50,000 credits (six-month validity), then $375 for 500,000 credits, $1,250 for 2.5 million, and $3,750 for 12.5 million. That works out to about $1.00, $0.75, $0.50 and $0.30 per 1,000 requests respectively. It accepts regular Google query syntax, including site-style queries, and reports typical response times around 1–2 seconds. Its trade-off is that this design would encode provider domains in the query rather than use DataForSEO's structured wildcard target filter. Run a fixed 50-query comparison before selecting the vendor; compare verified unique boards per 1,000 requests, latency, coverage and actual billed credits.

**SerpApi** also exposes structured Google SERP results and supports normal Google query operators and geographic localization. Its listed entry plan is $25/month for 1,000 searches, then $75 for 5,000 and $150 for 15,000. That is substantially more expensive for a recurring discovery worker, so it is not a first choice unless its support/compliance terms or result quality prove materially better.

**Exa** is a useful independent semantic discovery candidate rather than a direct Google replacement. It supports per-request includeDomains/excludeDomains filters, wildcard subdomains and path prefixes. Its documented Lite mode is $4 per 1,000 requests and Auto mode is $7 per 1,000. It may surface employer careers pages missed by exact keyword SERPs, but its neural ranking is less directly comparable to Google operator searches. Evaluate it later as a coverage-expansion source, not as the initial board enumerator.

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
2. **Rotate provider targets.** A low-cost starting plan is two provider targets per 30-minute cycle, rotating through all eight providers. That checks each provider approximately every two hours. Compare DataForSEO Live + target against Serper site: queries on the same 50-query set before choosing a vendor. If measured unique discovery value justifies it, move to all eight targets each cycle.
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

- Provision a trial/API account only for the selected vendor in QA. Never paste credentials into chat, source files, docs or command history.
- Manually test DataForSEO Live `target` filtering on all eight provider domains and Serper `site:` queries using the same role seeds.
- Compare returned URLs with manual `site:` queries; verify exact ATS host/path containment and check for Google redirect-wrapped result URLs.
- Save the real per-task cost, result count, duplicates, malformed URLs and valid candidate count.
- Compare Google results with official employer careers links and existing Common Crawl/sitemap discovery.
- Do not add any result to the production database during this stage.

### Gate 1 — deterministic QA worker

- Implement the selected SERP vendor behind a provider-neutral adapter interface so it can be disabled or swapped independently.
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

- DataForSEO Google Organic SERP API pricing: https://dataforseo.com/pricing/google-serp/google-organic-serp-api
- DataForSEO Live Advanced endpoint and target parameter: https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
- DataForSEO target filter limitations and redirect caveat: https://dataforseo.com/help-center/how-to-get-google-rankings-with-python-a-dataforseo-serp-api-tutorial
- Serper Google SERP API pricing: https://serper.dev/
- Brave Search API pricing: https://brave.com/search/api/
- Exa Search API domain filters: https://exa.ai/
- Google Search spam policies: https://developers.google.com/search/docs/essentials/spam-policies
- Google Custom Search JSON API sunset notice: https://developers.google.com/custom-search/v1/overview
