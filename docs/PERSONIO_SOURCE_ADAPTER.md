# Personio public careers XML feed adapter

**Branch:** `feat/personio-public-feed-20261109`
**Baseline:** `origin/v2-live-radar` at `ecb347aef013e5249ce1270006d3bc226e111c3e`
**Status:** implementation candidate; feature branch only; default-off; not merged, deployed or activated. Dashboard source toggle, source-health label and job-feed source filter are included.

## Evidence and scope

Personio documents a tenant-specific careers XML feed at `https://{tenant}.jobs.personio.de/xml` (also `.com` where that is the board's configured domain) with a language query such as `?language=en`. Its Help Center states that the employer must enable the XML feed in Recruiting > Career page settings; once enabled, the feed is accessible without credentials. The feed includes currently published position information. A position has an integer ID, office/department/category, title, job-description blocks, employment type, seniority, schedule and years-of-experience labels. `createdAt` is available but is not assumed to be the true publication time.

A read-only HTTP smoke against the Personio documentation's example tenant `personio.jobs.personio.de/xml?language=en` returned HTTP 200 and the expected `workzag-jobs` XML root, but zero position records. This validates endpoint shape only, not a populated employer board. No populated tenant feed has been proven yet; a real employer tenant with the XML feed enabled is required before ingestion can be accepted. The adapter remains inactive until an administrator supplies and verifies a real employer tenant with the XML feed enabled.

## Implementation

- Provider discovery recognizes `{tenant}.jobs.personio.de` and `.com`.
- Admin flow remains discover → verify public endpoint → explicit activation. Verification does not enable polling.
- Config key `personio_boards`; source key `personio`; 300-second default poll interval; default-off; config v15 → v16 migration explicitly forces it off.
- One GET per configured board per poll, with `language=en`, redirects disabled, bounded timeout and no retries.
- Source-level HTTP 429 respects Retry-After, persists cooldown using shared source-run state, and stops polling the remaining Personio boards for that cycle.
- First poll of an explicitly activated board is marked as historical baseline using the existing board-registry mechanism; it must not create a historical alert burst.
- Stable job identity is tenant + position ID.
- The documented `createdAt` is retained as source metadata only. `source_posted_at` remains unknown; discovery time is never substituted for employer publication time.
- Job descriptions are read only from `jobDescriptions/jobDescription/value` blocks and converted from HTML to plain text.
- The per-position link uses the documented Personio job preview path `https://{tenant}.jobs.personio.{de|com}/job/{id}`. No application-form URL is invented or stored.

## XML security and data handling

- Accept only a strict tenant slug and `.de` / `.com` suffix.
- Reject DTD/entity declarations, malformed XML, unexpected roots and payloads over 2 MB.
- Bound job count and field lengths.
- Extract an explicit allowlist of job-related fields only.
- Never persist raw XML or unknown nodes.
- A board that returns a valid empty `workzag-jobs` document can have zero currently published listings; the admin verification UI should make the count visible rather than treating an empty feed as proof of a broken parser.

The response body is currently size-checked after the HTTP response is received. Before broad activation, add transport-level streaming/body caps to prevent an unexpectedly large chunked response from being fully buffered.

## Tests

The new `v2/test_personio.py` covers:
1. Published-position XML mapping and job-detail URL construction.
2. DTD/entity, oversize, malformed, wrong-root and invalid-tenant rejection.
3. Invalid and duplicate position IDs.
4. Publication-time conservatism (`createdAt` is not mapped to `source_posted_at`).
5. Retry-After and stop-after-429 behavior.
6. Default-off config and v15 → v16 migration.
7. Public board detection and endpoint verification.
8. Admin discovery → verify → explicit activate → deactivate lifecycle.

All eight focused tests pass. The full V2 suite passed **408 tests**; Python compile, config JSON validation and `git diff --check` passed. GitHub exact-head CI remains the next gate.

## Not yet done / release gates

- No employer feed has been activated.
- No real Personio jobs have been ingested into the application DB.
- No scheduled source polling, application state change, Telegram delivery or external user notification was run.
- No production, shared-dev, source scheduler, user preference, database or container was modified.
- Keep default-off. Require a real tenant sample with published positions, full-suite and exact-head CI, two-poll disposable-DB baseline/dedupe proof, and shared-dev UAT with notifications disabled before merge/deployment.
- The official support documentation recommends syncing the feed at least hourly; the candidate defaults to a conservative five-minute poll. Reassess based on provider terms and measured response behavior before increasing request frequency.

## Primary sources

- Personio XML feed setup and no-credentials statement: https://support.personio.de/hc/en-us/articles/207576365-Integrate-jobs-from-Personio-into-your-website-via-XML
- Personio XML field/schema documentation: https://developer.personio.de/docs/retrieving-open-job-positions
- Personio XML endpoint reference: https://developer.personio.de/v1.0/reference/get_xml
- Personio public job preview path example: https://support.personio.de/hc/en-us/articles/209821565-Summary-of-data-that-Personio-shares-with-external-job-boards
- Feed sync recommendation: https://support.personio.de/hc/en-us/articles/29375445597725-Frequently-asked-questions-on-XML-job-integration
