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

## Current roadmap

1. LinkedIn: low-volume consolidated query + recency filtering — implemented.
2. Source health/backoff — implemented.
3. Naukri: replace HTML extraction with structured search — next.
4. Instahyre: replace HTML extraction with structured/public API — next.
5. Canonical identity + cross-source deduplication.
6. Incremental/new-or-changed fetching for large ATS boards.
7. India-aware remote/geography matching — implemented.
8. Freshness/discovery-lag metrics.
9. Dashboard auto-refresh and source-health visibility.
10. Scheduler tuning only after ingestion is reliable.
