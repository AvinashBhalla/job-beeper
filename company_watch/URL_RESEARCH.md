# Company URL registry notes

Snapshot: 17 November 2026. The source list contains 100 companies. `companies.csv` keeps every row and separates the destination URL from whether it is suitable for automated scanning.

## Verification rules

1. Direct ATS endpoints are labelled `verified_ats_board` or `verified_workable_board`.
2. Official career pages are labelled `official_careers_page` / `official_careers_portal` and use the generic structured-data-first parser unless a specific ATS adapter is selected.
3. User-supplied pre-existing URLs are retained, not silently replaced, and labelled `provided_url_needs_live_validation` unless the ATS type is clearly supported.
4. Ambiguous identities and non-career homepages are populated with a research pointer but kept `scan_enabled=false`. These are not represented as official job boards.

The verification source URL is included in the `verification_source` CSV column. Search-only pointers are explicitly marked in `verification_note`. No API token or credential is stored in this registry.

## Manual review queue

The following rows remain out of automatic scanning until the intended entity or a true careers board can be confirmed:

- Tigent & Codec: the Codec careers page was found, but the CSV label combines two names and the intended entity is unclear.
- Leading Healthcare: not a unique company name.
- McCord Media: official company homepage found; no dedicated public careers board found in this pass.
- Japanese e-commerce: sector description rather than a company name.
- ARKO Corp: ARKO India career microsite found at https://talent500.com/arko/; kept disabled pending live opening/ownership validation.
- KARL Tech: exact legal/company identity not verified.
- Equiti Group: company identity and hiring activity confirmed; its listings identify SAP SuccessFactors, but the exact official board URL was not retrieved. Kept disabled.
- Halo Kinetic: exact company identity not verified.

`companies.csv` intentionally has no blank `careers_url` values. A research-only search URL is a populated pointer for an unresolved entity, not a claim that the company board has been located.

## Adapter fixes after the first live dry-run

- Mistral AI: the official careers page links to https://jobs.ashbyhq.com/mistral.ai. The old `jobs.lever.co/mistral` endpoint was stale; the registry now uses Ashby.
- SoundHound AI: the prior Greenhouse slug returned 404 in the first scan. The official destination is https://www.soundhound.com/careers, so the registry now uses the employer page and only collects machine-readable job postings or conservative job links from it.
- The Standard: the employer's Workday career site is now supported by the public Candidate Experience endpoint; the row is enabled for dry-run.
- Caxton Associates: Workable's published careers feed is now supported; the verified account board is enabled for dry-run.
- Workday detail requests are bounded to 30 target-title jobs per employer per scan. Workday listings page in groups of 20; Workable returns published postings with descriptions; SmartRecruiters now fetches posting details for target engineering titles (bounded to 40 detail requests).
- HTTP 403/401, 404, 429, TLS, timeout and server failures are categorized separately. Restricted sites are not bypassed; 404 entries are investigated as stale destinations; transient failures are flagged for a later recheck.

## Additional verification after initial build

- The Standard: the Workday search path was verified from an employer job page at https://standard.wd1.myworkdayjobs.com/en-US/search/job/Portland-OR/Graphic-Designer_REQ006681. The root search page is the populated destination; no Workday adapter is enabled here.
- ARKO Corp: an ARKO India career microsite is available at https://talent500.com/arko/. It is retained for manual validation and not automatically scanned.
- Equiti Group: JobBeeper's own collected result identifies the source as SuccessFactors, but this pass did not recover the public employer board URL. The row now distinguishes confirmed employer identity from an unverified board destination.
