# JobBeeper Reference: Engineering Guardrails

This document records **publicly observable JobBeeper product behavior** that we use as a reference when evolving this personal job watcher. It is not a claim about JobBeeper's private implementation.

## Reference behaviors

Based on JobBeeper's public product pages:

1. **Broad source coverage**
   - JobBeeper publicly lists LinkedIn, Naukri, Workday, Greenhouse, Lever, Ashby, SmartRecruiters, Darwinbox, Instahyre, Hirist, Cutshort and company career pages.
   - Our source roadmap should therefore prioritize source-specific adapters rather than one generic scraper.

2. **Freshness is a product feature**
   - JobBeeper says it checks sources throughout the day and sends matching jobs within minutes.
   - Public job pages expose publishing/discovery timing.
   - Our pipeline must preserve source timestamps, discovery timestamps and avoid repeatedly treating old jobs as new.

3. **Match before notification**
   - Public messaging describes matching role, location, experience and company preferences before delivery.
   - Our architecture should fetch/normalize first, then match locally, then notify.

4. **Explainable matching**
   - Public examples show a preference-match percentage and reasons such as role, location and followed-company matches.
   - Every alert should carry deterministic match reasons. AI can enrich later, but should not be required for basic correctness.

5. **Daily active-feed lifecycle**
   - JobBeeper publicly describes a live/recent feed and continuous daily monitoring, but the public pages do not establish a literal midnight deletion rule.
   - For our personal implementation, the active dashboard/feed should reset at India local midnight: yesterday's jobs leave the visible daily feed and today's counts start from zero.
   - Historical observations remain in SQLite for deduplication, alert history, auditability and analytics.

6. **Direct application**
   - JobBeeper sends the original/direct employer link and does not automatically apply.
   - We preserve canonical source URLs and never automate application submission.

7. **Company-level aggregation**
   - Public company pages aggregate roles across multiple sources (for example LinkedIn, Naukri, Instahyre, Greenhouse and SmartRecruiters).
   - Our normalized job model must support source + company identity + canonical job identity so cross-source duplicates can be merged.

8. **Newest-first feeds**
   - Public browse/company pages present newest openings first.
   - Dashboard ordering should prioritize freshness, while retaining a separate match score.

9. **Source health**
   - Public coverage spans many heterogeneous sources. Our implementation must therefore tolerate individual source failures without stopping the entire run.
   - Failed sources use persistent exponential backoff; manual runs may bypass cooldowns for debugging.

## Engineering rules for this repository

### Before changing a source
- Identify the source's best available structured/public interface.
- Prefer API/JSON feeds over rendered HTML.
- Determine pagination, freshness fields, stable job IDs and rate limits.
- Add source-specific backoff before increasing request volume.

### Before increasing polling volume
Measure:
- requests/run
- jobs fetched/run
- relevant jobs/run
- new jobs/run
- 429/4xx/5xx rate
- median discovery lag

Never increase request volume merely because a source returned zero jobs.

### Before changing matching
Check:
- title include/exclude
- geography
- remote semantics
- experience
- company rules
- posting age

Keep geography and eligibility deterministic. Do not use substring matching where it can turn "Remote - United States" into an India match.

### Before adding a new source
The adapter should expose:
- stable job ID
- canonical URL
- company
- title
- location
- posted/updated timestamp
- description where available
- source name
- source health/error

### Target pipeline

```
source registry
  -> source-specific fetch
  -> normalize
  -> canonical identity
  -> deduplicate
  -> new/changed detection
  -> deterministic preference match
  -> score + reasons
  -> dashboard / Telegram
```

## What we know vs. what we infer

**Publicly supported:** source coverage, matching concepts, freshness/discovery presentation, direct links, newest-first feeds and company aggregation.

**Inference only:** JobBeeper's exact internal crawler, database, scheduling algorithm, queues, proxy strategy, incremental cursor implementation or infrastructure. We should not copy an imagined implementation; we should reproduce the observable product properties with a simpler personal architecture.

## Current source roadmap and platform inventory

### Current status
- LinkedIn: low-volume guest search with paced requests and global stop-on-429/backoff. The labeled experience metadata regression fix is committed on v2-live-radar; await dev verification before production promotion.
- Naukri: active separate public relay, polled by the app.
- Greenhouse: adapter implemented with three configured boards; previously dry-run validated ~298 entries without writes/alerts. Disabled; next run a one-board development canary.
- Instahyre: adapter exists but is disabled; verify its live response schema, stable IDs, posting timestamps and useful yield before enabling.

### Priority 1: documented public structured ATS feeds
1. Greenhouse Job Board API. Public GET data is available without authentication: https://docs.greenhouse.io/job-board.html
2. Ashby Public Job Posting API, requires an employer board name/slug: https://developers.ashbyhq.com/docs/public-job-posting-api
3. Lever published postings API, requires an employer site: https://github.com/lever/postings-api
4. SmartRecruiters Posting API, uses an employer company identifier: https://developers.smartrecruiters.com/docs/endpoints
5. Workable and Recruitee only after confirming a permitted public endpoint; their documented API integrations may need tenant tokens: https://help.workable.com/hc/en-us/articles/115012771647-Using-the-Workable-API-to-create-a-careers-page and https://support.recruitee.com/en/articles/1066282-api-documentation

### Priority 2: job boards / aggregators
Current: LinkedIn and Naukri; Instahyre adapter exists but is disabled.
To evaluate: Cutshort, Hirist, Wellfound and Y Combinator jobs. Prefer a public/searchable feed or documented API where available; do not assume a platform has an unauthenticated global API.

### Priority 3: employer-tenant ATS platforms
Requested inventory: Ashby, Avature, BambooHR, Breezy HR, Cutshort, Darwinbox, Eightfold AI, Freshteam, Greenhouse, Hireology, Hirist, HRsmart, iCIMS, Instahyre, Jibe (iCIMS), Jobvite, Keka, Lever, LinkedIn, Naukri, Oracle Cloud Recruiting, Paycom, PeopleStrong, Phenom People, Recruitee, Rippling ATS, SmartRecruiters, SAP SuccessFactors, Oracle Taleo, Teamtailor, UKG Pro/UltiPro, Wellfound, Workable, Workday, Y Combinator and Zoho Recruit.
Many named vendors are ATS products rather than globally searchable public job boards. An adapter alone is insufficient: support requires finding real employer board URLs/tenant identifiers, allowed public endpoints, pagination and stable job IDs. Prioritize India/remote developer employers and measure useful yield rather than merely counting integrated vendor names.

### Rollout acceptance gates
For every source: identify allowed endpoint and board discovery method; stable source ID and original apply URL; posted/updated and discovered timestamps; pagination/incremental fetch; normalization/dedupe fixtures; request budgets/backoff; per-source health/error isolation; fetched/unique/new/relevant counts; matching/ledger/delivery consistency; and no historical alert replay.

### Next implementation order
1. Verify LinkedIn experience parser patch on the dev container; then promote it to main.
2. Enable Greenhouse in dev on one board only with notifications disabled; pass two-poll timestamp/dedupe/yield/backoff checks before adding boards or turning it on in production.
3. Validate Instahyre endpoint/schema/freshness in dev, then enable only if it has useful new-job yield and reliable data.
4. Add Ashby, Lever and SmartRecruiters one at a time; evaluate Workable/Recruitee public interfaces and then tenant-specific sources.
5. Improve per-source observability and continue low-pressure LinkedIn monitoring over 24-72 hours.

Do not enable every provider simultaneously, and do not use proxy/IP rotation or CAPTCHA bypass to evade LinkedIn rate limits.

## Gemini JD extraction (development shadow mode)

- \`v2/gemini_extractor.py\` calls Gemini only when deterministic experience is missing/ambiguous or configured skills are absent from a sufficiently long JD.
- Default model: \`gemini-3.5-flash-lite\`; override with \`GEMINI_MODEL\`. Current Google pricing documentation lists a free tier and 1M-token context for this model family; free-tier quotas and data-use terms apply and must be checked in AI Studio.
- Feature is disabled by default. Enable only in the isolated dev Compose runtime with \`GEMINI_EXTRACTION_ENABLED=true\` and a VM-injected \`GEMINI_API_KEY\`.
- Limits: at most 3 requests per source run and 20 per day by default; bounded JD length, short timeout, hash-keyed SQLite cache, temporary error cache, strict schema/semantic validation.
- Results are stored in \`gemini_shadow_cache\` and exposed via \`GET /api/llm-shadow-status\`. They never modify the job record, matcher inputs, match score, notification decision, or Telegram delivery.
- Treat the posting as untrusted input. Do not send candidate PII. Never log/commit the API key or raw JD. Keep notifications disabled and do not merge/deploy until dev tests and a reviewed shadow sample pass.
