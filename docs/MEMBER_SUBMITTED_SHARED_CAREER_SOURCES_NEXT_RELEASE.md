# Member-submitted shared career sources — next-release proposal

**Date:** 18 November 2026  
**Backlog:** [#99 — Member-submitted career URLs as shared global sources with cross-source deduplication](https://github.com/AvinashBhalla/job-beeper/issues/99)  
**Priority:** P2 / next release  
**Current-release decision:** Documentation only. No implementation, deployment, source activation or live URL polling in this release.

## 1. Product intent

Allow any authenticated JobBeeper member to paste a public employer career-site URL. JobBeeper should identify the provider/site, validate that public vacancies can be fetched safely and reliably, and—after verification/review—add the source to one shared master catalogue.

The source must not become a private scraper belonging only to the member who submitted it. Member submission is a discovery signal and attribution record. Once approved and activated, the source is polled once globally; jobs from it enter the shared jobs inventory and are evaluated against every member's own preferences.

If several members submit the same site, they should resolve to the same shared source record and the same scheduler entry.

## 2. Current implementation audit

### What already exists

- `board_discovery.discover_public_careers(company_name, website_url, careers_url)` performs a bounded public-site inspection (up to six pages). It can find supported ATS board links and detect pages containing JobPosting JSON-LD. It returns review candidates only; it does not poll those careers pages for jobs or activate a collector.
- `global_ats_discovery` contains polite, bounded Common Crawl and robots-aware sitemap discovery. Its purpose is candidate staging, not arbitrary page ingestion.
- `ats_global_discovery_candidates` is a global staging table separate from `ats_board_registry`. The admin-only import/list/link/reject workflow stores unmatched ATS URLs with provenance and low confidence. It does not create an employer or activate a board during import.
- The admin “Unmatched global ATS candidates” panel includes a manual/captured URL staging form. The form is not member-facing.
- The current board normalizer/collector/scheduler supports Workday, Keka, Darwinbox, Greenhouse, Ashby, Lever, SmartRecruiters and Workable. The per-board scheduler is built from shared application configuration, not per-member URL lists.
- Member preferences currently cover target roles, locations, skills, experience and match settings. There is no member career-source URL preference or submission endpoint.

### What is not implemented

- No authenticated member-facing URL submission form or API.
- No shared source catalogue that promotes a member suggestion into a centrally verified/active polling source.
- No generic “take any URL and keep scraping that page” collector. Generic JobPosting JSON-LD is currently detected as a candidate only.
- No Oracle Recruiting Cloud provider adapter, parser or scheduler mapping.
- No guarantee that cross-source duplicates render as only one card in the member feed.

### Oracle URL compatibility check

The two supplied URLs match Oracle Fusion / Oracle Recruiting Cloud Candidate Experience URL structure:

| Fixture | Tenant host | Site number |
|---|---|---|
| [Oracle site 1](https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs?mode=location) | `egug.fa.us2.oraclecloud.com` | `CX_1` |
| [Oracle site 2](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs) | `jpmc.fa.oraclecloud.com` | `CX_1001` |

A static test using the exact current V2 `board_discovery.detect_ats_board` implementation returned `None` for both URLs. No requests were made to these sites or their job endpoints, and no job listings/counts were fetched. These URLs are recorded as future Oracle adapter fixtures, not as verified active sources.

## 3. Cross-source duplicate handling: existing foundation and remaining gap

### Existing foundation

Each source observation is stored in the shared `jobs` table with a unique `(source, source_job_id)` key. JobBeeper also has a `canonical_opportunities` table.

The current cross-source canonical linker:
- first tries exact canonicalized job URL equality (score 100);
- otherwise compares normalized company and location plus title similarity;
- rejects matches with conflicting explicit experience ranges;
- can use matching experience or high title/description similarity to reach the auto-link threshold;
- auto-links only when the score is at least 95;
- creates/updates one notification-ledger record per canonical opportunity.

This means the existing data model already provides an important part of the desired behavior: multiple source observations can be linked to one canonical opportunity, and notification state is shared at the canonical-opportunity level.

### Remaining product gap

The member `GET /api/jobs` endpoint currently selects rows from `jobs` and joins per-job evaluations. It does not group or page by `canonical_opportunity_id`. The dashboard carries canonical ID/match metadata on each job, but it does not use that metadata to collapse duplicate cards.

Therefore the current implementation is **not yet a complete “show one job once across all sources” experience**. A LinkedIn observation and an employer-career-site observation can belong to the same canonical group but still be returned as separate job rows.

### Required next-release behavior

- Retain every source observation for provenance, source health, last-seen freshness and apply-link fallback.
- Show one member-facing opportunity/card per canonical opportunity, not one card per source observation.
- The first successfully ingested source may remain the initial representative, so the faster source can establish the first-visible record. Keep the other observations attached to that opportunity.
- Define a safe representative-selection policy for later observations (for example, preserve first-seen ordering but allow a verified richer description or healthier apply URL to improve the display record without creating a second opportunity).
- Count, sort and paginate by canonical opportunities, not raw job rows.
- Apply each member's preferences to the canonical opportunity once per member. The source remains globally shared; only relevance and notification decisions are user-specific.
- Continue one notification per canonical opportunity. Keep source observations available in an opportunity detail/“also found on” section.
- Keep conservative matching. Ambiguous title/company/location matches should not be merged automatically; add review/telemetry for likely duplicates and false merges.

## 4. Proposed architecture

### A. Member submission and shared identity

1. Add an authenticated “Suggest a career site” action in the member experience.
2. Validate and normalize the URL before any fetch. Require HTTPS and a public hostname; reject credentials, private/loopback/link-local destinations, unsafe ports and unsafe redirects. Bound URL length, body size, timeouts and submissions per account/host.
3. Parse provider, tenant host and site/board identity. For Oracle, identity should include the exact tenant host and `siteNumber`; a host can expose multiple distinct career sites.
4. Store member submission attribution separately from the shared source. Suggested entities:
   - `career_source_submissions`: submitted URL, submitting user ID, timestamp, status/result and any reviewer note.
   - `shared_career_sources`: provider, normalized host/site key, canonical career URL, company identity evidence, state, poll policy and last health/verification timestamps.
5. Enforce uniqueness on the shared source identity. Repeated submissions from the same or different members point to the existing shared source instead of making another scraper or schedule.

### B. Classification, verification and activation

- Recognize known ATS URL patterns and choose a provider adapter.
- For unknown sites, inspect public sitemap/robots and JobPosting JSON-LD using bounded same-host requests.
- Verify the employer/site identity from the official careers domain and public site metadata. Do not turn a tenant slug into a company name by guesswork.
- Keep explicit states such as `submitted`, `candidate`, `verified`, `active`, `paused`, `unsupported` and `rejected`.
- Require admin review for ambiguous providers, company identity, inaccessible pages or uncertain access rights. A member paste must never activate a source by itself.
- Reuse the global registry and per-board scheduler after verification. Enforce one active schedule per shared board/site, host-level pacing, bounded concurrency, jitter, backoff, freshness and visible health.

### C. Oracle Recruiting Cloud adapter research

The submitted sites have the common Candidate Experience path `/hcmUI/CandidateExperience/{language}/sites/{siteNumber}/...`. A recent third-party technical write-up reports that the candidate-facing UI calls same-host endpoints such as `/hcmRestApi/resources/latest/recruitingCEJobRequisitions`, using a `findReqs;siteNumber=...` finder with `limit/offset` pagination, with job details available from `recruitingCEJobRequisitionDetails`. It warns that a wrong/nonexistent site number can return a default site's results with HTTP 200, so a successful response alone does not prove site identity.

Important support/terms caveat:
- Oracle's official HCM REST documentation describes the `recruitingCEJobRequisitions` endpoints as **only for Oracle internal use**.
- Oracle's documented `recruitingJobSitePostedJobs` resource for publicly posted jobs is restricted to **approved Oracle Cloud Marketplace partners**.
- The candidate-facing UI may expose same-origin requests without login in practice, as observed in third-party research, but that is not the same as an Oracle-supported public third-party API guarantee.

Before production implementation, verify Oracle's permitted usage/terms and whether the candidate-facing endpoints can be used reliably without credentials. Do not use recruiter credentials, access candidate PII, use internal endpoints that require authorization, bypass access controls, or copy TLS/browser impersonation. If access or policy is unclear, fall back to permitted public sitemap/JobPosting markup or leave that site unsupported.

Initial acceptance fixtures:
- `egug.fa.us2.oraclecloud.com` / `CX_1`
- `jpmc.fa.oraclecloud.com` / `CX_1001`

For each, compare the adapter's reported site name and total-job count with the visible career site before activation. Never silently accept a default-site fallback.

### D. Shared ingestion and deduplication

- Normalize the provider's job record into the current common job schema: stable source job ID, company, title, location, posted timestamp/precision, description, application URL and source details.
- Use provider + tenant/site + requisition ID as the stable source identity where available.
- Upsert into the shared `jobs` store; preserve original source/apply URLs and observation timestamps.
- Attach duplicate observations to the canonical opportunity rather than dropping source evidence.
- Project canonical opportunities into the member feed once. Paginate and count after grouping.
- Keep one global notification-ledger event per canonical opportunity, then apply each member's preference/evaluation/notification policy to that opportunity.
- Build telemetry for duplicate hit rate, ambiguous matches, false merges, source-first detection time, job freshness and per-source health.

## 5. Acceptance criteria

- A member can paste a supported public career-site URL and receives a useful status: already tracked, submitted for review, active, unsupported or rejected.
- Multiple members submitting the same URL resolve to one shared source and one scheduler entry.
- Verified sources are polled globally, not once per member.
- New jobs enter the shared database and can be evaluated for all members.
- The same requisition discovered from an employer ATS and a general job board is displayed once and not notified twice, while preserving alternate source observations and links.
- Tests cover SSRF/redirect safety, provider/site parsing, duplicate submissions, uniqueness, schedule deduplication, adapter pagination, 429/5xx backoff, canonical linking, race conditions, feed grouping/count/pagination, one-notification semantics and member visibility.
- Oracle site IDs/counts are checked for both supplied fixtures; unexpected fallback results are rejected.

## 6. Current-release boundary and next steps

This is P2 / next release. It must not displace the current release work.

Current priorities remain:
1. Complete the 24-hour source reliability assessment and decide source-by-source acceptance.
2. Finish Company Watch release qualification and the gated candidate import/rejection plan. Do not change production boards or schedules without release qualification.
3. Continue read-only production health checks and verify the installed seven-day local snapshot retention over its scheduled daily runs.
4. Keep Naukri relay paused and paid SERP discovery disabled under the no-spend constraint.

After those items are closed, bring this specification into the next release planning session, break it into member submission, shared registry/scheduler, Oracle adapter, canonical feed projection and verification/test workstreams, then implement behind review/activation gates.

## 7. Activity log — 18 November 2026

- Inspected current V2 ATS provider patterns, candidate import/list/link workflow, career-site discovery, sitemap discovery, board registry/scheduler and member preference schema.
- Inspected canonical opportunity matching, notification-ledger identity and `GET /api/jobs` query.
- Tested the two supplied URLs against the current `detect_ats_board` function in the production application image. Both return `None`; no live network or job requests were made.
- Reviewed Oracle official HCM REST documentation and recent third-party observations of Candidate Experience website requests.
- Created and tracked issue #99. No application code, production DB, runtime config, source registry, scheduler or deployment was changed for this feature.
