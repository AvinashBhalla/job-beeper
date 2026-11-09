# Company-agnostic ATS discovery — Common Crawl candidate staging design

**Date:** 2026-11-09 20:25 IST
**Status:** architecture/research note; not yet implemented. Do not enable any source.

## Why a separate candidate table is needed

The existing `ats_board_registry` requires `company_id` and the current admin review UI assumes a known employer. A Common Crawl URL can reveal a Workday tenant or Keka/Darwinbox career path, but it does not reliably reveal the legal/employer display name or the employer's canonical website. Turning a host slug into an employer name and inserting a synthetic company row would pollute company identity and make later matching harder.

Create a separate `ats_global_discovery_candidates` staging table without requiring `company_id`. An admin should associate the candidate with a real employer (or create a reviewed employer entry) before the candidate is converted into a normal `ats_board_registry` record.

## Proposed candidate record

- `id` — primary key.
- `provider` — workday / keka / darwinbox / other known ATS.
- `board_key` — provider-derived stable tenant/site/portal identity.
- `board_url` — normalized public career board root.
- `candidate_host` — normalized public host.
- `discovery_method` — commoncrawl_cdx / commoncrawl_url_index / sitemap / career_link / licensed_seed.
- `source_reference` — crawl ID, WARC/capture URL or sitemap URL.
- `source_captured_at` — capture timestamp from the discovery dataset.
- `first_discovered_at`, `last_seen_at` — first/last observation in discovery sources.
- `confidence` — initially low for archived URL-only candidates.
- `review_status` — discovered / linked / rejected / stale.
- `linked_company_id`, `linked_board_registry_id` — nullable references set only after human association/verification.
- `created_at`, `updated_at`.
- uniqueness on `(provider, board_key)`; re-discovery refreshes provenance/last_seen without reviving rejected records.

## Common Crawl query policy

Current research reviewed official Common Crawl documentation on 2026-11-09. The latest collection listed at that time was `CC-MAIN-2026-43`, crawl window 2026-10-05 through 2026-10-18. Refresh the crawl catalogue slowly; do not hardcode that ID forever.

CDX candidate patterns:
- Workday: wildcard domain `*.myworkdayjobs.com`, filter for public HTML / status 200 and the tenant host shape `*.wdN.myworkdayjobs.com`.
- Keka: wildcard domain `*.keka.com`, filter URL paths to `/careers` or `/careers/{portal-slug}` only.
- Darwinbox: wildcard domain `*.darwinbox.in`, filter URL paths to `/ms/candidatev2/{company_id}/careers` only.

Use recent capture windows, output JSON, collapse duplicate URL keys where supported, and apply a hard response-row cap. Do not ingest historical WARC job-page contents as current jobs. Normalize the captured URL to a board root, then persist it as an unmatched candidate with crawl provenance.

## Rate-limit controls

Common Crawl's own FAQ says the CDX API is heavily rate-limited; on 503, slow down, and if an IP is temporarily blocked, wait 24 hours. It asks clients to use HTTPS, sleep between requests, avoid multiple concurrent threads from the same IP, and not use proxy networks.

JobBeeper controls must be stricter than a general scraper:
1. One global Common Crawl request lock/budget shared by all discovery workers.
2. One provider query per scheduled invocation; rotate provider by persisted state rather than issuing three queries in parallel.
3. A minimum global interval between requests and a persisted request timestamp.
4. On 503 / temporary block, stop the whole CDX queue and set a 24-hour cooldown. Do not rotate IPs, proxies or user agents to evade the block.
5. If the result limit is reached, mark the run capped/incomplete. Use supported ZipNum pagination only when the selected index confirms it; otherwise do not claim exhaustive discovery.
6. For broad/high-volume discovery, prefer the Common Crawl Parquet URL Index over CDX. It is suitable for Athena/Spark/Polars/DuckDB filtering, but AWS Athena requires an AWS account and is paid.

## Verification / activation workflow

Common Crawl is a candidate signal, not a live ATS verifier:
1. Candidate-only staging insert; no employer identity guess is treated as authoritative.
2. Admin associates the candidate with an employer, or records the correct employer name/site after review.
3. Re-run existing safe public board verification with same-host redirects and bounded request budgets.
4. Only a verified, explicitly approved board can be linked into `ats_board_registry`.
5. Board activation remains a separate, explicit admin action; first inventory is silently baselined and notifications remain subject to user matching/approval rules.

## Acceptance criteria

- An unmatched ATS candidate is visible without manufacturing an employer row.
- Candidate preserves provider, normalized root URL, board key, capture timestamp, crawl ID and discovery method.
- Repeated crawls update last_seen without duplicating the candidate.
- Rejected/linked candidates are not reset to discovered on re-import.
- CDX worker serializes requests and persists a 24-hour cooldown after 503.
- No archived job description is inserted into JobBeeper as a current job.
- Candidate import alone never activates a source or sends an alert.
- A live approved verification step is required before linking to the normal employer board registry.

## Official references

- Common Crawl collection catalogue: https://index.commoncrawl.org/collinfo.json
- CDX index server: https://index.commoncrawl.org/
- Common Crawl FAQ / CDX 503 guidance: https://commoncrawl.org/faq
- Common Crawl URL Index / Parquet: https://commoncrawl.org/url-index
- pywb CDX API wildcard/filter/pagination reference: https://pywb.readthedocs.io/en/latest/manual/cdxserver_api.html

## User dependencies

Nothing required to implement the candidate staging schema or a polite CDX test harness. An AWS account, Athena output location and a spend cap are needed only if the product chooses the broad Parquet URL Index path. No credentials should be sent in chat.
