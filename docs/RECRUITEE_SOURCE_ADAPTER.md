# Recruitee public XML feed adapter

**Branch:** `feat/recruitee-public-feed-20261109`
**Baseline:** `origin/v2-live-radar` at `ecb347aef013e5249ce1270006d3bc226e111c3e`
**Status:** implementation candidate; feature branch only; default-off; not merged, deployed or activated. Dashboard source toggle, source-health label and job-feed source filter are included.

## Why this connector

Recruitee exposes a company-scoped XML feed for published jobs. This is separate from its Careers Site JSON API. Recruitee's documentation says the XML feed and jobs widget are not covered by the Careers Site API token requirement scheduled for 2027-02-10. The adapter therefore uses the public XML feed, not a token-protected customer API.

Public feed forms:
- Formatted feed: `https://{tenant}.recruitee.com/api/feeds/offers.xml`
- Raw feed: `https://{tenant}.recruitee.com/api/offers.xml`

The adapter currently uses the formatted feed. A read-only public feed check against the `bunq` tenant returned HTTP 200, XML, and 23 `<offer>` rows. After adjusting the URL mapping for employer-branded careers domains, the parser accepts all 23 records. This confirms one public feed sample only; it does not establish coverage for every Recruitee tenant.

## Implementation

- Provider discovery recognizes a public `{tenant}.recruitee.com` board URL.
- Admin flow is unchanged: discover → verify one public endpoint → explicit activation. Discovery and verification never enable polling.
- Config key `recruitee_boards`; source key `recruitee`; default poll interval 120 seconds; source is disabled by default and the config v15 → v16 migration forces it off for existing persisted configs.
- One GET per configured board per poll; redirects disabled; bounded request timeout; no retries.
- Recruitee source-level HTTP 429 observes Retry-After, persists cooldown with the shared source-run mechanism, and stops polling remaining Recruitee boards in that run.
- First inventory follows the existing per-board baseline mechanism. It must be silent; only post-baseline discoveries can become alert candidates.
- Job IDs are stable tenant + feed reference/ID; original posting and apply URLs are retained only when HTTPS and on the exact validated tenant host.
- `posted` / `published_at` is mapped to provider publication time when parseable. `updated` / `updated_at` is retained separately as metadata and is never substituted for publication time.
- HTML description fields are converted to plain text. Locations, category, employment type, experience label, education label, salary label, company and remote/hybrid/on-site flags are kept where exposed.

## XML security boundary

The feed may contain a `<credentials>` subtree for partner job-board integrations. It is untrusted and is **never traversed, copied, logged, or persisted**.

The parser:
- Extracts only a fixed allowlist of known candidate-facing fields.
- Supports the documented `<jobs><job>` sample and the observed `<offers><offer>` shape, including a raw-feed `<hash><offers>…</offers></hash>` wrapper.
- Rejects DTD/entity declarations, malformed XML, unexpected roots and payloads over 2 MB.
- Limits the number of rows and individual field lengths.
- Uses the fixed verified `{tenant}.recruitee.com` host for the feed request. Feed-supplied job/apply links may use an employer-branded public host, but must be HTTPS, use the default/443 port, have no embedded credentials or fragment, and must not point to localhost or an IP literal. The collector never fetches these links.
- Does not persist the raw XML, unrecognized feed nodes, `mailbox_email`, or partner credentials.

The size limit is currently enforced by the parser after the HTTP response is received. If real tenant samples routinely exceed the 2 MB bound, add transport-level streaming/body caps before broad activation; do not simply raise the limit without measuring.

## Tests added

The new `v2/test_recruitee.py` currently has ten focused tests covering:
1. Allowlist extraction and proof that a synthetic credentials subtree never appears in returned job data.
2. DTD/entity, malformed XML, wrong root and oversized payload rejection.
3. Same-tenant HTTPS URL enforcement.
4. Observed `offers` and raw wrapper variants.
5. Job normalization, publication vs update timestamps, apply URL and board registry provenance.
6. Retry-After handling and stopping after 429.
7. Config migration/default-off behavior.
8. ATS discovery and public-feed probe.
9. Admin discovery → verify → explicit activation → deactivation lifecycle.
10. HTTPS employer-branded links plus rejection of localhost, IP-literal, credentialed and nonstandard-port URLs.

All ten focused tests pass. The populated public `bunq` feed smoke parses 23/23 offers. The full V2 suite passed **409 tests**; Python compile, config JSON validation and `git diff --check` passed. GitHub exact-head CI remains the next gate.

## Not yet done / release gates

- No employer board has been activated in shared dev or production.
- No scheduled polling, ingestion into a persistent application DB, notification, or Telegram delivery was performed.
- No production configuration, container, DB, source scheduler or user settings were changed.
- Do not mark Recruitee as production-ready until full V2 tests and exact-head CI pass, the adapter is reviewed against at least two tenant schemas, the baseline/dedupe behavior is proven on a disposable DB across two polls, and shared-dev UAT passes with notifications disabled.
- Keep the connector opt-in. Do not claim all Recruitee tenants expose identical fields or feed schemas.
- Review vendor terms and tenant visibility before activating a real employer board.

## Primary documentation

- Recruitee XML feed: https://docs.recruitee.com/docs/feed
- Published offers: https://docs.recruitee.com/reference/offers
- Recruitee Help Center feed URL formats: https://support.recruitee.com/en/articles/8213076-faq-api
- Careers Site API authentication transition: https://docs.recruitee.com/reference/authentication-1
