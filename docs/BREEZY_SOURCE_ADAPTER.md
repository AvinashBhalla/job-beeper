# Breezy HR public careers portal adapter

**Branch:** `feat/breezy-public-json-20261109`
**Baseline:** `origin/v2-live-radar` at `ecb347aef013e5249ce1270006d3bc226e111c3e`
**Status:** default-off feature-branch candidate; not merged, deployed or activated. Dashboard admin toggle, source-health label and job-feed source filter are included.

## Evidence and interface status

Breezy HR portals commonly use `{company}.breezy.hr`. A read-only request to one public employer portal's `/json` endpoint returned HTTP 200 and 905 records. The response exposed IDs, friendly IDs, titles, same-board job URLs, published-date labels, employment type, location/remote state, department, salary and company data.

A read-only GET to one job URL on the same portal returned HTTP 200 HTML with a `schema.org/JobPosting` JSON-LD block containing title, description, datePosted, employmentType, baseSalary, jobLocation and URL. This is promising real-world evidence, but `/json` is an **observed public portal endpoint, not a documented/guaranteed Breezy API contract**. It may vary by portal, be rate-limited or change without notice. The adapter is therefore opt-in and must be verified per employer before activation.

The first implementation recognizes only hosted `{slug}.breezy.hr` portals. Custom domains and other Breezy deployments require separate detection evidence; do not guess slugs or silently treat every career page as Breezy.

## Implementation

- Public list endpoint: fixed `https://{slug}.breezy.hr/json`; same-board hostname only.
- Detail enrichment: fetches same-board job HTML only, with redirects disabled, and extracts a strict `JobPosting` JSON-LD allowlist.
- Config key `breezy_boards`; source key `breezy`; default 300-second poll; source disabled by default; v15 → v16 config migration forces it off.
- Admin flow: discover → verify one public portal feed → explicit activation. Verification does not enable polling.
- Board activation is explicit and uses the existing first-inventory silent-baseline mechanism.
- Listing ID is stable tenant + Breezy job ID; duplicate IDs and malformed records are skipped.
- Description, exact datePosted, employment type, salary and jobLocation are taken from same-board JobPosting JSON-LD where present. Feed published_date is a fallback label only; it is not silently replaced with the discovery timestamp.
- Existing rows without descriptions are prioritized for re-enrichment, so new feed records do not starve the older description backlog.
- **Global detail-fetch cap: 20 detail-page attempts across all Breezy boards per source run**, not 20 per employer. Of these, up to 10 are reserved for old jobs still missing descriptions; the rest go to current missing descriptions. Each attempt is separated by a short delay.
- HTTP 429 honors Retry-After, persists cooldown across restarts, and stops the current Breezy source scan. There are no automatic retries or proxy/session workarounds.

## Safety and data boundary

- Feed and detail URLs must be HTTPS on the exact validated `{slug}.breezy.hr` host, default/443 port, with no embedded credentials or fragment.
- Job-detail pages are never submitted to or used to initiate an application.
- Only structured JSON list fields and a narrow JobPosting JSON-LD allowlist are normalized. Raw list payloads/HTML and unknown fields are not persisted.
- Feed size is capped at 2 MB; detail HTML at 1.5 MB; listing count at 3,000 per board; description at 30,000 characters.
- Redirects are disabled. A 30x response or cross-host URL is not followed.
- Keep all boards disabled until vendor terms, portal-specific schema and request budgets are reviewed.

The response size cap is currently checked after the HTTP response has been received into memory. Before broad activation, add streaming/body caps if larger/streamed portals appear. The current list endpoint has no pagination contract established here; the adapter consumes the full observed list response and fails closed above the cap.

## Tests

The new `v2/test_breezy.py` covers:
1. Public-list mapping for title, company, IDs, location, remote flag, salary and employment type.
2. Rejection of unsafe URLs, invalid tenant slugs and malformed feed shapes.
3. Duplicate/invalid row handling.
4. JSON-LD JobPosting extraction and exclusion of raw HTML.
5. Malformed/oversized/non-byte detail page handling.
6. Bounded detail enrichment and exact publication-time mapping.
7. Backfill priority for existing jobs missing descriptions.
8. A global 20-detail-attempt budget across multiple employer boards.
9. Retry-After and stop-after-429 behavior.
10. Default-off config, provider detection and public feed verification.
11. Admin discover → verify → activate → deactivate lifecycle.

All 11 focused tests pass. Full V2 suite, exact-head GitHub Actions CI and code review remain gates before merge consideration.

## Live sample evidence

- Public list endpoint: HTTP 200, 783,244 bytes, 905 rows, fields included `company`, `department`, `friendly_id`, `id`, `location(s)`, `name`, `published_date`, `salary`, `type`, `url`.
- One same-portal job detail: HTTP 200 HTML, JSON-LD `JobPosting` present with description (3,120 characters in the inspected sample), datePosted, baseSalary and jobLocation.
- This was one bounded read-only sample. It does not prove all Breezy portals expose the same fields, feed or detail schema.
- No board activated, no jobs ingested into a persistent JobBeeper DB, no Telegram, no shared-dev deploy and no production change.

## Merge and release sequencing

Recruitee PR #59, Personio PR #60, Teamtailor PR #61 and this Breezy branch were independently cut from the same V2 baseline. Each independently introduces a v16 migration and must remain default-off. Do not merge these unchanged in sequence. After one source merges, rebase the next PR and advance its migration to the next config version, preserving the existing sources and disabled defaults.

## References

- Breezy HR careers portals (observed public portal): `https://{slug}.breezy.hr/`
- Public portal JSON feed (observed, not vendor-documented): `https://{slug}.breezy.hr/json`
- Structured job detail (same-board JobPosting JSON-LD): linked from the public portal feed.
