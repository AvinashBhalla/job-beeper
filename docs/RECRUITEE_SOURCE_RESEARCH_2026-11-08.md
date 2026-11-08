# Recruitee source research and canary — 2026-11-08

**Status:** Research only. No Recruitee collector implemented or enabled.

## Official contract reviewed

Official documentation:
- Feed structure: https://docs.recruitee.com/docs/feed
- Feed examples: https://docs.recruitee.com/docs/example-xml-feed
- Public feed URLs: https://support.recruitee.com/en/articles/8213076-faq-api
- Careers Site API auth deadline: https://docs.recruitee.com/reference/authentication-1

Documented raw XML path: `https://{company}.recruitee.com/api/offers.xml`; formatted path: `/api/feeds/offers.xml`; JSON path: `/api/offers`. These public feed URLs do not require an API token. Recruitee's new Careers Site API will require `X-Careers-Sites-Token` from 2027-02-10, but its docs explicitly exclude the XML feed and jobs widget from that token requirement.

The official documentation sample describes a legacy shape like `<jobs><job>` with `reference`, `title`, `company`, `description_requirements`, `posted`, `updated`, `url`, `apply_url`, `<locations>` and remote/hybrid/on_site flags.

## Live Tether raw XML canary

Public board: `tether.recruitee.com` (also discovered in current third-party index data as a Recruitee board with India/remote engineering roles). Two bounded GETs were made to `https://tether.recruitee.com/api/offers.xml`, 2 seconds apart, with a 10 MiB client response cap and no redirects.

Both snapshots:
- HTTP 200; body size 8,785,676 bytes (~8.38 MiB).
- 228 offers; 228 unique non-empty `id` values and 228 unique `guid` values.
- All 228 offers had `published-at`, `updated-at`, `title`, `status`, `careers-url` and `careers-apply-url`.
- All 228 had `status=published`.
- 20 offers had an India location in their location records; a broad title-keyword filter found 18 India technical-role candidates. This is not the JobBeeper matcher result.
- 226 offers had `remote=true`, 2 had `hybrid=true`; none had `on-site=true`.
- 228/228 IDs overlapped between snapshots; same ID set and same metadata fingerprint over the 2-second interval. This checks immediate consistency only, not long-term stability/freshness.
- The canary feed contained no `<credentials>` subtree, but this must not be assumed for other boards because Recruitee documents that credentials for third-party job boards may appear in an offer's XML.

Important: the live Tether raw XML shape was `<hash><offers><offer>` and used `id`, `guid`, `slug`, `published-at`, `updated-at`, `description`, `requirements`, `remote`, `hybrid`, `on-site`, `locations`, `careers-url` and `careers-apply-url`. It did **not** contain `reference`, `posted` or the legacy `description_requirements` element. Future code must support both the documented legacy sample and this currently observed live raw-feed schema; do not assume one replaces the other.

## Required parser security rules

1. Validate a company subdomain with a conservative slug allowlist and construct the HTTPS hostname yourself; never accept a user-supplied full URL (SSRF boundary).
2. Use a bounded single GET per board, explicit timeout, no automatic retries at first. Tether's 8.38 MiB feed suggests a 10 MiB cap may be too tight for a growing board; consider 12 MiB or a configurable hard limit with a test. Reject oversized responses before parsing.
3. Reject XML `DOCTYPE` and entity declarations before parsing; do not enable XInclude or external entity processing. Use `defusedxml` if available, or a safe stdlib parser with explicit DTD/entity rejection.
4. Parse only an allowlist of job elements and attributes. Explicitly remove/skip any `<credentials>` subtree; never store raw XML, serialize the full offer, log raw elements or include credential fields in diagnostics.
5. Use the observed stable ID (`id`) as source identity and retain `guid` as metadata/fallback only if verified. The legacy shape uses `reference`; support it explicitly.
6. Use `published-at` / `posted` for publication time; use `updated-at` / `updated` only as source metadata. Do not confuse update time with first publication. Record precision only after parsing and validating timezone.
7. Validate `careers-url` against the configured Recruitee host patterns (board subdomain and documented `.s.recruitee.com` variant); otherwise build a canonical `/o/{slug}` link from validated values. Do not trust arbitrary HTML links.
8. Filter to explicitly published offers and normalize all locations, not just the first. Preserve remote/hybrid/on-site flags; do not infer remote from title text.

## Recommendation

Recruitee is a viable next ATS source: its feed provides stable IDs, publication/update times, multiple locations and work-model flags. The Tether board is relevant to India remote engineering, but it is broad (228 total offers, 20 India offers). Keep research separate from activation. Do not create a Recruitee adapter until the Lever PR and first-inventory notification safety are reviewed; then use Tether as the first read-only test fixture and add tests for both XML schemas plus `<credentials>` exclusion before any live source enablement.

## No operational change

No Recruitee board was added to a JobBeeper config; no app collector request, SQLite write, evaluation, notification, service restart or deployment occurred.