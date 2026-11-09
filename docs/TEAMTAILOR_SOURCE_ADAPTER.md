# Teamtailor public RSS adapter

**Branch:** `feat/teamtailor-public-rss-20261109`
**Baseline:** `origin/v2-live-radar` at `ecb347aef013e5249ce1270006d3bc226e111c3e`
**Status:** default-off feature-branch candidate; not merged, deployed or activated. Dashboard admin source toggle, source-health label and job-feed source filter are included.

## Official feed contract

Teamtailor documents an RSS feed from its careers-site jobs page by appending `.rss`, e.g. `https://career.teamtailor.com/jobs.rss`. The feed exposes public job title, description, publication date, job URL, remote status, global ID, locations, department, role and division. The default page is 100 jobs; `offset` and `per_page` query parameters support pagination, including a documented example of 200 jobs per page.

One read-only GET to the official documentation sample returned HTTP 200, content-type `application/rss+xml`, and 16 entries. The parser accepted all 16, each with publication date, description, location and HTTPS job URL. This confirms the sample feed format, not populated-feed coverage for arbitrary employers.

The initial adapter recognizes Teamtailor-hosted `{slug}.teamtailor.com` domains. Branded custom career domains are not yet auto-detected; they need a separately verified provider signal before activation.

## Implementation

- Provider discovery recognizes `{slug}.teamtailor.com` career URLs.
- Admin lifecycle is discover → verify public RSS → explicitly activate. Discovery and verification never enable polling.
- Config key `teamtailor_boards`; source key `teamtailor`; 300-second default interval; default-off; config v15 → v16 migration forces the source off for existing persisted configs.
- Feed endpoint is fixed to `https://{slug}.teamtailor.com/jobs.rss`; the collector requests `per_page=200` with offset pagination, up to 10 pages / 2,000 listings per board per poll.
- Redirects are disabled; requests have a bounded timeout and no automatic retries. HTTP 429 honors Retry-After, persists source cooldown using shared source-run state, and stops polling remaining boards for that source run.
- Stable source ID is a hash of the RSS GUID, falling back to the public job URL. The employer's HTTPS job link is retained but never fetched by the collector.
- RFC 2822 `pubDate` is parsed as the publication timestamp. HTML descriptions are converted to plain text. Namespace-tagged location, department, role and division fields are retained. Remote-only listings fall back to a Remote location label when no specific location is supplied.
- First inventory uses the existing per-board silent baseline gate; no historical alert burst should be produced on activation.

## XML / URL safety

- Reject DTD/entity declarations, malformed XML, unexpected root/channel, and feeds over 2 MB.
- Bound items to 200 per page and 2,000 per board per poll; truncate only at the configured cap, with the next poll re-reading the latest feed window.
- Accept only HTTPS job links without embedded credentials, non-standard ports, fragments, localhost/internal hostnames or IP-literal hosts.
- Ignore all unknown feed nodes; raw RSS is not persisted or logged.

The response-size cap is currently enforced after the HTTP response is received. If boards return larger or chunked feeds, add streaming/body caps before raising the limit.

## Tests

The new `v2/test_teamtailor.py` covers:
1. Namespaced location, department, role and division mapping.
2. RSS publication time and HTML description parsing.
3. DTD/entity, oversized, malformed, wrong-root and invalid-slug rejection.
4. Unsafe link rejection and global-ID deduplication.
5. Collector mapping and board registry metadata.
6. Offset pagination and cap behavior.
7. Retry-After cooldown and stop-after-429 behavior.
8. Default-off config and v15 → v16 migration.
9. ATS discovery, RSS probe, and admin discover → verify → activate → deactivate lifecycle.

All nine focused tests pass. Full V2 suite and exact-head GitHub CI are required before this can be considered merge-ready.

## Release gates

- No Teamtailor board has been activated or put into recurring polling.
- No persistent application DB ingestion, Telegram delivery or user notification was run.
- No shared-dev or production container, database, configuration or scheduler was modified.
- Verify a populated employer board (not just the docs sample) and confirm all pages are complete, timestamps are sane, first-poll baseline is silent, and a second poll deduplicates.
- Keep the source default-off. Require exact-head CI, review and shared-dev UAT with notifications disabled before merge/deploy.

## Official sources

- RSS feed how-to, fields and pagination: https://support.teamtailor.com/en/articles/11171756-rss-feed-how-to-guide
- Teamtailor API key/scope distinction: https://support.teamtailor.com/en/articles/5963369-use-our-teamtailor-api
- API scope docs: https://docs.teamtailor.com/
