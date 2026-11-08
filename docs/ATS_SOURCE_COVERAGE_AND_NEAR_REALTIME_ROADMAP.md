> **Current source of truth:** [Product Vision and Delivery Roadmap](PRODUCT_VISION_AND_DELIVERY_ROADMAP.md). This file remains detailed design/history; when priorities conflict, the product vision roadmap is authoritative.

# Job Radar — 36-platform source coverage and near-real-time delivery roadmap

**Owner requirement recorded:** 2026-11-08  
**Applies to:** V2 candidate / PR #51 and all future agents  
**Priority:** Product requirement, not optional future polish

## 1. Product expectation

Job Radar is expected to monitor all 36 named platforms below, discover employer career boards hosted on them, ingest newly published jobs with low latency, normalize and deduplicate the jobs, apply each user's saved profile/preferences, and send a Telegram notification only to the user whose filters match.

Target is near-real-time after a vacancy becomes publicly visible:
- Use employer/vendor publish webhooks when an employer authorizes and exposes one.
- Otherwise target a 2-minute poll interval for high-priority active boards, with jitter and source-specific rate limits. Lower-priority boards may use a slower interval where their terms, service limits or endpoint behaviour require it.
- Do not promise literal zero-delay delivery: a public feed can lag the employer's internal action, career-site cache/CDN refresh, provider indexing, and our next scheduled poll.
- Every notification must link to the source posting and show the source's real publication time when supplied. Keep first_seen_at separate from provider published_at; never invent a posting timestamp from an update timestamp.

## 2. Important distinction: platform coverage is not a global jobs API

The list mixes ATS/recruiting platforms used by individual employers (e.g. Workday, Darwinbox, Greenhouse, iCIMS, Oracle Recruiting) and job marketplaces/aggregators (e.g. Cutshort, Hirist, LinkedIn, Naukri, Instahyre, Wellfound, Y Combinator / Work at a Startup).

There is no single API that returns every employer using all 36 systems. Most ATS connectors need the individual employer's career URL, tenant, site, board slug/token or company identifier first. Job Radar therefore needs company/board discovery, not just 36 HTTP functions.

Required discovery behaviour:
- Maintain a company registry: employer name, company domain, known careers URL, country/region, enabled state and discovery provenance.
- Discover career links from employer websites and sitemaps; follow public links and detect ATS patterns/domains.
- Resolve ATS-specific board identifiers (Workday tenant + cluster + site; Greenhouse board token; Ashby board name; Lever site; SmartRecruiters company identifier; etc.).
- Support custom-branded career domains where the underlying ATS host differs.
- Store a verified board record, last successful probe, parser version, last cursor/checkpoint, last job count and next poll time.
- Provide an operator review queue for ambiguous or unsupported sites. Do not silently claim a company is covered merely because its ATS brand is on this list.

## 3. Exact requested platform inventory and current V2 status

Status legend:
- **Live-tested V2:** adapter exists in V2 and a real shared-dev pipeline run was successful on 2026-11-08.
- **V2 code exists; recurring scheduler disabled:** tested by a one-off run, but deliberately not enabled in the shared-dev scheduler.
- **Research lead:** a plausible public interface/career-site pattern has been identified from current research; it still needs per-tenant validation, vendor/terms review and implementation.
- **Not implemented in V2:** no production-grade V2 collector at this checkpoint.

| # | Platform | Kind | Checkpoint status | Expected connector/discovery approach |
|---:|---|---|---|---|
| 1 | Ashby | ATS | **V2 code exists; recurring scheduler disabled**; 2 boards live-tested | Public Job Postings API, board name from jobs.ashbyhq.com/{board}; published jobs only. |
| 2 | Avature | ATS | Research lead; not implemented in V2 | Tenant-specific public career site; parse server-rendered listing/detail pages and JobPosting JSON-LD where present. Templates vary by employer. |
| 3 | BambooHR | ATS | Research lead; not implemented in V2 | Public careers list/detail pages may be available per tenant. Distinguish the public careers feed from the authenticated BambooHR customer API; do not use employee/applicant endpoints. |
| 4 | Breezy HR | ATS | Research lead; not implemented in V2 | Employer subdomain career board; a public JSON board route has been observed by third parties, but verify response/terms per tenant and handle non-existent boards separately from throttling. |
| 5 | Cutshort | Job marketplace | Not implemented in V2 | Marketplace connector requires a documented/authorized feed or permitted public listing access; do not assume it is an ATS. |
| 6 | Darwinbox | ATS / HRMS | **Top priority requested by owner**; official Recruitment API research indicates employer API key required; no V2 connector | Tenant-specific candidate career site. Community research identifies a possible candidate-facing JSON endpoint, but this is not treated as a vendor-guaranteed API. Validate tenant/company ID and response contract before use. |
| 7 | Eightfold AI | ATS / talent platform | Research lead; not implemented in V2 | Tenant-specific public career site and job-search interface; verify pagination and domain scoping. Do not use authenticated recruiter APIs. |
| 8 | Freshteam | ATS | Not implemented in V2 | Public career page / sitemap / JobPosting JSON-LD first; no stable unauthenticated contract is assumed until verified. |
| 9 | Greenhouse | ATS | **V2 code exists; recurring scheduler disabled**; 3 boards live-tested | Public Job Board API, board token; tested 3/3 boards, 369 jobs on shared dev. |
| 10 | Hireology | ATS | Not implemented in V2 | Employer-specific career pages and schema.org JobPosting parsing; investigate only the public candidate-facing layer. |
| 11 | Hirist | Job marketplace | Not implemented in V2 | Marketplace access/partner feed or permitted public search pages; keep separate from ATS connector family. |
| 12 | HRsmart | ATS / legacy HR | Not implemented in V2 | Legacy, tenant-specific public career portals; require real tenant examples and contract validation. |
| 13 | iCIMS | ATS | Not implemented in V2 | Public iCIMS career portal page/search route and JobPosting JSON-LD; tenant templates differ. No universal unauthenticated API is assumed. |
| 14 | Instahyre | Job marketplace | **V2 code exists; recurring scheduler disabled**; live-tested after parser repair | Public candidate-facing search interface. Current API returns objects, nested employer, public_url, locations; map city aliases and bound pagination. Tested 140 jobs / 4 HTTP 200 pages. |
| 15 | Jibe (iCIMS) | ATS / career-site platform | Not implemented in V2 | Treat as a distinct iCIMS career-site family/variant; validate public /api/jobs-style endpoint per portal rather than assuming every iCIMS tenant behaves the same. |
| 16 | Jobvite | ATS | Not implemented in V2 | Employer-hosted Jobvite career sites; inspect public page, feeds and JSON-LD; use a parser only where legally permitted. |
| 17 | Keka | ATS / HRMS | Not implemented in V2 | Tenant-specific careers site; establish public feed/API availability with real customer board examples. |
| 18 | Lever | ATS | **V2 code exists; recurring scheduler disabled**; one board live-tested | Official public Postings API; global/EU host; bounded pagination. Test board returned 500 postings across 5 successful pages (cap reached). |
| 19 | LinkedIn | Job marketplace | **V2 code exists; recurring scheduler disabled**; one controlled live probe and ingestion passed | Publicly accessible job search only, with strict pacing/rate-limit handling and policy review. Do not bypass login, CAPTCHA, access controls or 429 cooldowns. Live probe: 1 request, HTTP 200, 10 unique jobs, 10 ingested. |
| 20 | Naukri | Job marketplace | **Live-tested V2; only source enabled in shared-dev scheduler** | Existing owner-controlled Naukri relay feed; poll freshness guard and consume only fresh snapshots. Scheduled live runs have succeeded. |
| 21 | Oracle Cloud Recruiting | ATS | Research lead; not implemented in V2 | Employer career-site requisition feed/REST route. Oracle has documented Recruiting requisitions resources, but public-career-site access and customer auth must be determined per site. |
| 22 | Paycom | ATS / HR platform | Not implemented in V2 | Employer career pages; determine if public structured listing is available or parse public HTML/JSON-LD. |
| 23 | PeopleStrong | ATS / HRMS | Not implemented in V2 | Employer/tenant-specific candidate career site; no universal public contract assumed. |
| 24 | Phenom People | Career-site platform | Research lead; not implemented in V2 | Tenant-specific career-site search/widget endpoints. Confirm public access, pagination and job-detail schema for each deployment. |
| 25 | Recruitee | ATS | Research lead; not implemented in V2 | Prefer published jobs XML feed / careers-site interface. Official Careers Site API documentation states an authorization token will be required for calls without the header from 2027-02-10; do not build a future dependency on the currently unauthenticated API. |
| 26 | Rippling ATS | ATS | Research lead; not implemented in V2 | Employer-specific public career board / jobs endpoint; verify endpoint version and pagination against actual tenant. |
| 27 | SmartRecruiters | ATS | Research lead; not implemented in V2 | Official public postings endpoint by company identifier, with offset pagination (maximum 100 per page); public-only destination. |
| 28 | SAP SuccessFactors | ATS / HCM | Not implemented in V2 | Career-site sitemap/search pages and tenant-specific public endpoints; do not assume authenticated OData HR endpoints are public. |
| 29 | Oracle Taleo | ATS / legacy | Not implemented in V2 | Legacy hosted career pages, tenant-specific search and JobPosting JSON-LD where present. |
| 30 | Teamtailor | ATS | Research lead; not implemented in V2 | Official API has a Public read permission for career-site-visible data but requires a board/client token; public RSS/XML patterns may be an alternative where terms permit. |
| 31 | UKG Pro / UltiPro | ATS / HCM | Not implemented in V2 | Customer career site / tenant-specific portal. Identify public job feed; do not use workforce/private HR endpoints. |
| 32 | Wellfound | Job marketplace | Not implemented in V2 | Marketplace connector requires permitted public or partner access. Keep separate from employer ATS board polling. |
| 33 | Workable | ATS | Research lead; not implemented in V2 | Public careers widget/account endpoint for public listings; distinguish it from authenticated customer API scopes. |
| 34 | Workday | ATS / HCM | **V2 candidate adapter implemented; NVIDIA board live-tested (20/20 full detail) + two-poll disposable DB pipeline; scheduler remains disabled** | Per-employer tenant + cluster + site. Public career sites commonly call a CXS jobs endpoint; this is not the same as Workday's authenticated tenant REST API. Treat the CXS interface as undocumented/subject to change unless a customer/vendor contract confirms otherwise. |
| 35 | Y Combinator | Job marketplace | Not implemented in V2 | Work at a Startup / YC company job marketplace; partner/public listing access must be verified. |
| 36 | Zoho Recruit | ATS | Research lead; not implemented in V2 | Candidate-facing career portal per employer; distinguish public careers pages from authenticated Zoho Recruit APIs. |

**Checkpoint truth:** the V2 runtime collector registry currently contains only linkedin, naukri, instahyre, greenhouse, ashby, and lever. Only Naukri is enabled for recurring shared-dev polling. Four additional sources plus LinkedIn were exercised as controlled one-off pipelines. The remaining named systems are product requirements, not completed integrations.

## 4. Evidence-based connector research

Use vendor documentation first. Third-party endpoint repositories are useful discovery leads, not an API contract; every endpoint must be re-probed against a real employer board and checked against vendor terms before production.

Vendor documentation / primary references:
- [Ashby public Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api) — public board URL, published job fields, publishedAt, job URLs and optional compensation.
- [Lever Postings API](https://github.com/lever/postings-api) — published job postings are publicly viewable; documents global/EU site-based endpoints and pagination.
- [SmartRecruiters list postings](https://developers.smartrecruiters.com/reference/v1listpostings) — active public postings by company identifier, offset/limit and public-only destination.
- [Workable public jobs account endpoint](https://workable.readme.io/reference/jobs-1) — public jobs account response, fields and descriptions. Its authenticated customer API is separately documented.
- [Recruitee published offers](https://docs.recruitee.com/reference/offers) and [XML feed behaviour](https://docs.recruitee.com/docs/feed) — published offers only; feed reflects changes to published offers. Review the [Careers Site API auth change](https://docs.recruitee.com/reference/authentication-1) before implementation.
- [Teamtailor API permissions](https://docs.teamtailor.com/) — Public read can access information visible on the career site; API access still requires a token.
- [Oracle Fusion Recruiting requisitions](https://docs.oracle.com/en/cloud/saas/human-resources/farws/op-recruitingcejobrequisitions-get.html) — official requisitions REST resource; does not by itself prove a public, keyless endpoint for every career portal.
- [BambooHR Get Job Summaries](https://documentation.bamboohr.com/reference/get-job-summaries) — authenticated ATS settings endpoint, not the unauthenticated candidate career-page feed. Do not confuse the two.
- [Workday developer platform](https://developer.workday.com/documentation/GUID-6c547385-848b-4005-ab2c-632f1d6b5688) — REST API Explorer is tenant-authenticated and security-domain protected; keep that separate from public candidate career-site traffic.
- [Public ATS endpoint comparison (research lead)](https://headcountlabs.com/guides/ats-public-job-apis/) and [tested ATS job-board API patterns](https://github.com/Mersetti/ats-job-board-apis).
- [Career-ops source/provider catalogue (research lead, not vendor authority)](https://github.com/nathanaelhub/career-ops/blob/main/docs/SUPPORTED_JOB_BOARDS.md) includes discovery patterns for Avature, BambooHR, Darwinbox and other tenants. Verify every endpoint independently.

## 5. Near-real-time source scheduler

A connector alone is not enough. Implement a shared scheduler around board state.

Required per-board fields:
- company_id, provider, careers_url, tenant_or_board_key, region/cluster, enabled
- last_success_at, last_attempt_at, next_poll_at, last_http_status, last_error_type
- cursor/offset/next_page, etag, last_modified, last_payload_hash
- parser_version, consecutive_failures, cooldown_until, last_job_count

Scheduler requirements:
- Event/webhook first when the employer can configure it; authenticated publish webhooks are not available to arbitrary external consumers.
- Otherwise stagger board polls with jitter. Default high-priority interval target: 120 seconds, never lower than a provider's documented or observed rate budget. Do not start every connector simultaneously.
- Implement bounded concurrency per host and globally. Use conditional GET/cache validators when supported.
- Maintain per-board cursor or content fingerprints. Avoid refetching details for unchanged jobs.
- Honor 304, 403, 404, 408, 429, 5xx distinctly. A missing board is not a 429; do not put dead tenants in long rate-limit cooldown. Use exponential backoff with jitter only for retryable errors.
- Stop a board scan on 429; honor Retry-After; persist cooldown across restarts. Do not bypass rate limits with proxy rotation or account/session tricks.
- Persist source-run telemetry without storing request secrets, full raw payloads or candidate PII.
- Record first-seen, provider-published and provider-updated timestamps independently.
- Detect updated and closed postings; update canonical records without emitting a new-job alert for an edit unless the user explicitly subscribes to meaningful changes.

## 6. Normalization, deduplication and freshness

All source adapters must emit the same normalized job contract:
- Source/platform and company/board identifier
- Stable source job ID and canonical opportunity ID
- Title, company, department, employment type
- All locations, remote/hybrid/onsite label, country/city
- Public posting URL and apply URL
- Description (safe text/HTML normalization), skills, role family
- Experience range only when supported by actual listing/JD evidence
- Salary min/max/currency/period only when explicitly provided
- published_at, updated_at, first_seen_at, source timestamp precision
- Active/closed state and raw-source metadata needed for audit

Deduplicate by stable vendor ID first, then canonical URL/company/title/location rules. Cross-source duplicates should map to one canonical opportunity but must preserve every source observation and URL. Do not merge two requisitions merely because title/company strings are similar. A new board's initial inventory is a baseline: suppress historical backfill notifications and notify only jobs that first appear after that board is activated.

## 7. Per-user matching and Telegram delivery

The owner explicitly expects notifications according to each user's own saved filters and preferences, not one global admin profile.

Per-user filter dimensions:
- Target roles/title keywords and excluded terms
- Skills / must-have / nice-to-have terms
- Location list, country/city and remote/hybrid/onsite rules
- Minimum/maximum experience and candidate experience
- Salary minimum/currency where the posting actually states compensation
- Recency/freshness window and excluded companies/sources
- Per-source enable/disable and notification frequency/digest settings
- User's Telegram linking state and destination (per user)

Delivery pipeline:
1. A new source observation is persisted and linked to a canonical opportunity.
2. Evaluate each active user's preferences independently and record match score + explainable reasons.
3. Insert an idempotent per-user outbox/ledger row keyed by user + canonical opportunity + notification type.
4. Queue only eligible new matches. Never send every row in a baseline or a full historical recompute.
5. A worker claims a row atomically, sends to the Telegram chat linked to that user, records Telegram message ID and sent status, and retries transient failures with bounded backoff.
6. Prevent cross-user leakage: never use the global admin chat ID as the destination for all members; never show one user's preferences/credentials/jobs to another user.
7. Allow user controls: pause/resume, mute company/source, frequency, mark applied/ignore, and unlink Telegram.

Testing must use a dedicated test account/chat or a safe fake transport. Do not ask the owner to paste Telegram tokens into chat. Provision secrets directly on the VM/secret manager and verify only presence/absence in logs.

## 8. Required implementation order

**P0 — stabilize current shared-dev candidate before production**
- Keep current production untouched until explicit production approval.
- Investigate and fix intermittent sqlite3.OperationalError: database is locked observed in the legacy notification worker's recover_stale_claims during concurrent one-off source ingestion. Add contention tests and prove the error stops recurring under concurrent poll + match + notification-worker load.
- Verify user signup/login, admin/member auth, CSRF-protected mutations and per-user preference persistence with separate test users.
- Test Telegram delivery using a dedicated test chat with a user-specific ledger, idempotency and zero cross-user leakage.
- Keep the known 320px hit-test overlap documented as deferred; it is not part of this source-coverage project.

**P1 — owner-requested and high-volume employer ATS**
1. Workday
2. Darwinbox
3. BambooHR
4. SmartRecruiters
5. Workable
6. Recruitee (use XML feed/token transition plan)
7. Teamtailor
8. Rippling
9. Eightfold AI
10. Phenom People
11. Oracle Cloud Recruiting
12. Avature
13. iCIMS and Jibe
14. SAP SuccessFactors

For each, implement adapter + contract fixtures + one real public board test + two-poll stable-ID/new-job test + closed-job test + rate-limit/backoff test. Do not mark an ATS supported on a single 200 response.

**P2 — remaining ATS / employer career-site families**
Breezy HR, Freshteam, Hireology, HRsmart, Jobvite, Keka, Paycom, PeopleStrong, Oracle Taleo, UKG Pro/UltiPro, Zoho Recruit.

**P3 — marketplaces / aggregators**
Cutshort, Hirist, Wellfound, Y Combinator / Work at a Startup, LinkedIn and Naukri (plus Instahyre). Check terms, public API/partner feeds and rate policies; keep marketplace connectors isolated from employer ATS connectors.

**P4 — company-board discovery at scale**
Build/reconcile the target-company registry, ATS host detection, board identifier resolution, scheduled recrawls and operator exception queue. Without this, 36 connectors still will not cover employers whose board URL is unknown.

## 9. Production acceptance checklist

Production is not "all 36 covered" until the matrix has a real implemented/validated status for every requested row. Before production promotion:
- PR head exact SHA and full CI are green; no unreviewed app-code diff after the shared-dev image.
- Shared dev remains healthy through a soak; scheduler runs at least two cycles for every recurring enabled source.
- At least Workday and Darwinbox connectors are actually exercised against real public tenant boards.
- The source discovery registry is able to resolve a set of target employer career sites to board IDs.
- All enabled adapters have error budgets, timeouts, bounded pages, pagination tests, duplicate handling, new/update/close handling and rate-limit persistence.
- A real member and admin can log in and manage preferences; two users with different preferences receive different expected results.
- Telegram delivery test succeeds from per-user outbox to each test chat with zero sends for non-matches and no cross-user leakage.
- SQLite concurrency/notification-worker errors are fixed and load-tested.
- A fresh production online SQLite backup is taken immediately before deployment; integrity, size and SHA-256 recorded. Do not use the earlier /tmp preflight copy as the production rollback backup.
- Preserve production's existing data volume and its global Telegram settings until per-user delivery rollout is explicitly validated. Do not start candidate notification workers against the live production queue without a reviewed delivery plan.
- Owner provides separate explicit production approval. Earlier approval was for shared dev only.

## 10. Current checkpoint — 2026-11-08 17:10 Asia/Kolkata

- Shared dev candidate image: job-radar-dev-multitenant:b16fb83, image ID sha256:75f8855338f150a79794d388c32733305e548165f71dd417cfa04e6443c8c917.
- Shared-dev app code/test head: 754809fe406e8c5cb09f8e36140ac5cf3e4f7238; later commits on the branch are documentation-only. PR #51 remains open/draft.
- Shared dev on port 8001 health and dashboard both returned HTTP 200; production on port 8000 also HTTP 200 and was not changed.
- Latest shared-dev DB check: integrity ok; jobs/canonical/global evaluations/per-user evaluations/notification ledger = 9,444 each; source_runs = 7,858; one admin user and one stored preference row; user Telegram ledger empty.
- Latest source results in live dev: Naukri scheduled polling success; Instahyre 140 inserted; Greenhouse 369 inserted; Ashby 828 observed / 34 new; Lever 500 inserted one-off; LinkedIn 10 fetched and ingested one-off. Current saved scheduler enables Naukri only.
- All delivery safety flags in shared dev: notifications false, Telegram token/chat blank, Gemini and LLM routing false. Zero notification rows have sent_at.
- A database-lock error was observed in notification_worker -> recover_stale_claims during a source pipeline ingestion test; it recurred once after the LinkedIn ingestion. Must be root-caused before production.
- Production read-only preflight at 2026-11-08 11:21:21 UTC copied 20,971 jobs; integrity ok; candidate init/matching refresh preserved counts on the disposable copy (refresh took ~73 seconds). Production has existing global Telegram credentials and notifications enabled, 1,482 sent rows and 10 failed rows; preserve this carefully.
- Latest production health reported LinkedIn cooldown until 2026-11-08T12:01:13.950862Z; do not probe production LinkedIn before that time.
- No production candidate deployment, PR merge, or production volume write has occurred.

## 11. Instructions to the next agent

Read this file and the latest appended state in docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, and docs/DEV_DEPLOYMENT_RUNBOOK_2026-11-08.md first.

Then take charge without asking the owner to repeat this list:
1. Fix the SQLite/notification worker contention with tests.
2. Verify per-user auth/preferences/Telegram delivery with a safe test chat/transport.
3. Implement Workday and Darwinbox first, as explicitly requested, then the public ATS tiers and marketplace integrations in the priority order above.
4. Build employer/board discovery so the system can find actual tenants, not only call known slugs.
5. Update this matrix and handover after each validated connector; distinguish implemented, real-board-tested, recurring-enabled and production-enabled states.
6. Keep production untouched until all required gates and a separate explicit production approval are recorded.

Never mark a connector done based only on source code, a mocked test, or HTTP 200. A real integration pass means two stable source polls or a documented webhook event, correct normalization and deduplication, live DB ingestion/evaluations, and verified per-user notification decisions.


## 11. Workday/Darwinbox live validation leads — 2026-11-08

**Workday public career-site CXS lead:** one live request against NVIDIA's public careers board succeeded: `POST https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs` with JSON body `{"appliedFacets":{},"limit":20,"offset":0,"searchText":""}`. It returned HTTP 200, JSON keys `facets`, `jobPostings`, `total`, `userAuthenticated`, 20 postings and a reported `total` of 2,000. Sample fields included `title`, `externalPath`, `postedOn`, `locationsText` and a requisition identifier in `bulletFields`. This is one real public endpoint probe, not an adapter, recurring integration, promise of all 2,000 results, or vendor-supported public API contract. A production-grade adapter still needs a verified employer-board registry, bounded page budget, pagination/cap handling, detail fetch rules, stable IDs, timestamp-quality rules, backoff and repeated-poll tests. CXS should be treated as an undocumented public career-site interface and kept separate from authenticated Workday REST APIs.

**Darwinbox:** vendor Recruitment API documentation research indicates a customer/employer-issued API key is required for the Jobs API. A candidate-facing unauthenticated route is an independent research hypothesis only; test it only against a real public employer careers site and its permitted access terms. Do not claim general Darwinbox integration or assume the official Recruitment API can be used without employer credentials.

**Next connector action:** implement Workday only after the P0 SQLite fix is merged into the integration candidate and shared-dev soak is green. Build the board registry/URL resolver as a first-class component; an adapter without real employer tenant/site identifiers will not produce broad coverage. Then investigate Darwinbox per employer and record which access pattern is public, vendor-authorized or customer-keyed.


## 12. Workday connector implementation and bounded real-board validation — 2026-11-08

**Implemented in the isolated candidate branch:** `v2/radar.py` registers `workday_collect` in `COLLECTORS`; config version 13 adds the opt-in `workday` flag, a 120-second interval default, and a validated `workday_boards` allowlist. Each board is identified by its actual HTTPS `*.wdN.myworkdayjobs.com/<site>` public career URL. The parser derives tenant, cluster, and site from that URL; it rejects arbitrary hosts, credentials, query strings, fragments, duplicate boards, and unsafe posting paths. No employer/site identifier is guessed from the company name. The admin UI now exposes a Workday source toggle and JSON allowlist editor, along with existing Ashby/Lever toggles.

**Current conservative poll policy:** one CXS listings page of 20 per board per cycle, up to 20 detail attempts, with 100ms delay between detail calls; at most 20 configured boards, processed sequentially. The board is polled at 120 seconds when explicitly enabled. Because the `postedOn` field is a human label (e.g. “Posted Today”), it is retained as source metadata only; `source_posted_at` stays null and precision stays `unknown`. Workday is included in initial-inventory baseline suppression. Stable IDs use tenant/site/requisition ID. The adapter trusts only the allowlisted board host and safe `/job/...` external paths; it does not trust arbitrary `externalUrl` values.

**Rate-limit behaviour:** list and detail HTTP 429s stop the current board's further requests, honour `Retry-After` (with a conservative default cooldown when absent and a one-hour cap), persist the cooldown through `source_runs`, restore it at startup, and make the scheduler skip Workday until it expires. This is source-wide (a single board 429 pauses all configured Workday boards), deliberately conservative for an undocumented endpoint. Regression tests cover list/detail 429s and restart restoration.

**Real public board evidence:** NVIDIA's actual public CXS board returned HTTP 200 with a reported total of 2,000 and 20 listings on the first page. The final adapter was run twice through `run_source` against a disposable SQLite DB using its current default budget: poll 1 inserted 20 jobs, all 20 had full descriptions, 20 canonical opportunities were created and all 20 were marked as initial baseline; poll 2 inserted zero duplicates. Two source runs were successful, SQLite integrity was `ok`, and sent Telegram rows were zero. A separate controlled HTTP 429 run persisted `outcome=rate_limited`, `http_status=429`, `retry_after_seconds=120` and `cooldown_seconds=120`. This is a real one-board/two-poll integration test, not a multi-employer soak or production approval.

**Tests:** 12 focused Workday tests pass, covering board URL parsing, unsafe URL/path rejection, opt-in migration, list/detail parsing, detail attempt caps, baseline behaviour, 429 stop/backoff and cooldown restoration. The full V2 unittest suite on the current candidate passes **359 tests in 266.690 seconds, zero failures**. GitHub CI still needs to run on the exact final pushed SHA (including dashboard syntax). The connected VM's system Node is v12 and cannot parse existing project syntax such as nullish coalescing; use the repository GitHub CI `node --check` as the authoritative dashboard syntax check.

**Not complete:** Workday is not in the deployed shared-dev image and remains disabled in both runtime configuration and repository defaults. The CXS interface is public candidate-site traffic and should be treated as undocumented/changeable, not as the authenticated Workday REST API or a vendor guarantee. Only the first 20 listings are fetched per 120-second cycle; pagination/backfill and board change/close tracking are not implemented. Twenty sequential detail calls take material time; measured runtime needs revalidation after the pacing and cooldown changes. Employer board discovery is missing; Workday currently requires a verified URL to be entered in the admin JSON allowlist. Automated company-to-board discovery is not implemented.

Darwinbox is still not implemented. Its official Recruitment API requires employer-provided authentication; a public candidate-site route must be validated per employer and is not assumed universal. Keep Darwinbox the next connector priority, paired with the employer-board registry, before claiming broad ATS coverage.


## 2026-11-08 — Employer board discovery + SmartRecruiters/Workable update

- Current candidate commit: `93f532c20b0dcf6b37429a65add18281c16c00f9`, attached to draft PR #51 (`integration/pr46-v2-rebase-20261108` → `v2-live-radar`). PR remains draft/open. GitHub Actions V2 CI run `42491830453` is running on this exact SHA; wait for its final result before merge consideration.
- Added admin-first company/board discovery in `v2/board_discovery.py`: submit company name, website and optional careers URL; inspect a bounded number of public HTTPS pages, follow likely careers links, detect known ATS board patterns and persist multiple boards per company. This is not a per-employer hand-built JobBeeper page. The admin workflow is scan → inspect → endpoint verify → explicit activate. Discovery alone never enables polling.
- Discovery recognises Workday, Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Recruitee, Breezy HR, Teamtailor, BambooHR, Rippling and Personio. Collector availability is distinct from detection: current V2 ATS collectors are Greenhouse, Ashby, Lever, Workday, SmartRecruiters and Workable. Recruitee/Breezy/Teamtailor/BambooHR/Rippling/Personio are discovery-only pending validated public endpoint adapters. Darwinbox is still not implemented; official recruitment APIs are employer-authenticated unless a specific public candidate endpoint is independently verified.
- Added SmartRecruiters public postings API and Workable public widget collectors. Config version 14; both source flags default false and allowlists are empty. SmartRecruiters uses bounded three-page scans (100 listings/page) and up to 20 detail lookups per board. Workable consumes the public published-jobs widget. Both include stable source IDs, descriptions where exposed, locations and publication metadata where supplied.
- Activation requires a verified public endpoint and explicit admin click. It enables the collector and binds the registry board ID into source metadata. First successful poll marks only that board's first inventory as baseline and cancels unattempted queued alerts; it does not replay historic jobs to Telegram. A second board on an already active source does not re-baseline other employers.
- Live public validation: Bosch Group SmartRecruiters returned 300 postings under the configured page cap (20 detailed descriptions); Hugging Face Workable returned 6 published jobs with descriptions. Each collector was run twice through `run_source` against a disposable SQLite database: first poll ingested 300/6 and marked all rows as baseline, second poll produced zero new rows; zero Telegram sends; `PRAGMA integrity_check=ok`.
- Full local V2 suite on this candidate: **377 tests passed in 224.191 seconds, zero failures**. Python compilation, JSON validation and `git diff --check` passed. Host Node is v12.22.9 and cannot parse the project's existing modern JS syntax; GitHub CI Node check is authoritative.
- A first full-suite run exposed a compatibility regression: board-baseline suppression queried the new registry table in legacy/test DBs. Fixed by making it safely no-op when the additive registry table is absent; the existing LinkedIn `partial_rate_limited` regression test then passed.
- No shared-dev or production deployment, scheduler enablement, or Telegram delivery occurred. SmartRecruiters/Workable remain disabled by default. Production remains untouched.

### Next agent — do not restart discovery work

1. Read this section, the latest PR #51 body and `docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md`. The discovery registry and two new collectors are already implemented; do not rebuild them.
2. Check exact-SHA GitHub CI run `42491830453` for `93f532c20b0dcf6b37429a65add18281c16c00f9`. Fix any failure and rerun full V2 suite; do not infer CI success from local tests.
3. Run a bounded admin UI browser QA against an isolated test DB: company scan, multiple board results, verify, activate, source status and no accidental notifications. Test that unverified/unsupported boards cannot activate.
4. Continue the requested 36-platform coverage matrix. Next priority: Darwinbox employer-by-employer public candidate endpoint research, then provider-specific adapters for the discovery-only ATS families. Do not call employer-authenticated endpoints without employer-issued credentials.
5. Add bounded concurrency/per-board scheduling and freshness/backfill/closure semantics before promising a two-minute SLA across many employers. Workday remains sequential and a board can take tens of seconds.
6. Preserve release gates: PR #51 stays draft until CI, security and browser QA pass; no shared-dev or production deployment without the separate explicit approval. Production has active Telegram/global notification state—do not modify its container, volume, config or queue.

## 2026-11-08 follow-up — Keka/Darwinbox local candidate

The isolated worktree `feat/darwinbox-keka-20261108` now has dedicated Keka and Darwinbox V2 collectors plus discovery/verification, admin activation, default-off config migrations, dashboard controls and regression tests. A two-poll disposable-DB run validated Bridgestone Keka (109 baseline rows, then zero new). The then-reported JG Summit Darwinbox (18 rows) was later re-probed and returned 403; see the correction below. No notifications were sent in the original tests and SQLite integrity was `ok`. The full local V2 suite passed 387/387 in 215.671s; compileall, JSON and diff checks passed.

This is **local candidate code**, not a GitHub CI-verified or deployed source. Production remains on image `job-radar-prod-canary:7b1a80d` and these connectors are not deployed/enabled. Next gates: push final feature branch, exact-SHA CI, isolated admin UI verification/activation, source telemetry and latency checks, then reviewed PR. Keep both source flags false by default. Darwinbox success is tenant-specific and must be re-verified for each employer; endpoint 403 is a source failure, not an empty board or rate-limit response.

### Darwinbox live validation correction — 2026-11-08

The previous JG Summit `*.darwinbox.com` candidate endpoint returned HTTP 403 on repeat verification and is not accepted by the current Career-Ops provider contract. Its earlier 18-job evidence is superseded. Darwinbox discovery now accepts only `*.darwinbox.in`. A fresh public probe for Arvind Group (`https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/a6a67448e9a280`) returned 36 jobs; Airtel, LeadSquared and Sterling probes returned 403. Keep Darwinbox per-board verification mandatory and only activate the Arvind board in any production trial.

## 2026-11-08 — Live verification sweep before rollout

The isolated QA candidate now verifies the currently configured Greenhouse and Ashby boards and selected public examples: Coinbase GH 283, Graviton Research Capital GH 21, Zocdoc GH 64; OpenAI Ashby 816, PostHog Ashby 10; NVIDIA Workday 20 in the first page; Bosch Group SmartRecruiters 10 in the verification page; Hugging Face Workable 6; Bridgestone Keka 109; Arvind Darwinbox 36. The Workable probe now uses the same `apply.workable.com/api/v1/widget/accounts/{slug}` endpoint as its collector. Arvind Darwinbox two-poll ingestion inserts 36 and silently baselines on poll 1, inserts 0 on poll 2, sends no Telegram messages and retains SQLite integrity `ok`.

Do not interpret one probe as universal ATS availability. Darwinbox `.com` and several `.in` tenant probes returned 403; detector is `.darwinbox.in` only and only Arvind is currently verified. No empty allowlist or unsupported provider should be enabled in production. Lever board allowlist is currently empty; the non-collector ATS families remain discovery-only until adapters are implemented.
