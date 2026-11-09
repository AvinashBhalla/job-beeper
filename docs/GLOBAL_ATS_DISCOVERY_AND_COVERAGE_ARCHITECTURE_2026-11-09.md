# Global ATS Discovery and Company-Agnostic Job Ingestion

**Owner requirement recorded:** 2026-11-09
**Priority:** P0 source coverage / ingestion architecture
**Status:** design and evidence review; no production changes. This supersedes the old assumption that admins should paste every employer board one at a time.

## 1. Product requirement

JobBeeper should discover and ingest publicly published vacancies across employers using Workday, Keka, Darwinbox and the other supported ATS platforms **without requiring the owner to manually add every company**.

The desired workflow is:

1. JobBeeper continuously discovers new employer career boards and ATS tenants.
2. It verifies the public, candidate-facing job feed or listing page.
3. It adds the board to a global employer/board registry.
4. The board scheduler fetches new and changed public vacancies with per-provider rate limits.
5. Jobs are normalized, deduplicated, checked for legitimacy/freshness/reposts, and stored once in the shared jobs layer.
6. Each user's preferences are applied after ingestion; notifications are sent only to that user's own eligible channel.

A candidate profile must not be sent to or used as the crawler query for every ATS tenant. Discovery and ingestion are global; matching and notification are user-scoped.

## 2. Current implementation gap (verified in repository and production UI)

The V2 candidate already has Workday, Keka and Darwinbox collectors. Their configuration is still per-employer:

- `workday_boards`: each entry must contain a verified public Workday career URL; the collector derives tenant, cluster and site from it.
- `keka_boards`: each entry requires a verified tenant careers URL; the collector extracts the public career-portal feed identifier from the page before requesting the job list.
- `darwinbox_boards`: each entry requires a verified candidate-careers URL including its company identifier; the current candidate collector is tenant/company specific.

Enabling Workday/Keka/Darwinbox with an empty board list fails closed. Their collectors cannot infer every company that uses those systems from the provider name alone.

The production Source Health screen includes a manual company form:
- company name,
- company website,
- optional careers URL,
- optional country,
- “Discover career boards” action.

The discovered-board table is a per-company review queue. This is useful for correcting or manually adding an edge case, but it does **not** meet the desired automatic, company-agnostic coverage.

Current board polling is also not a global discovery scheduler. It only polls configured/activated boards; Workday, Keka and Darwinbox board collection iterates those configured records. A connector being registered does not mean every company using that ATS is monitored.

## 3. Important platform realities — what can and cannot be fetched

### Workday

- Workday employer career sites are separate external sites; a public candidate site exposes jobs for that employer/site, not every Workday customer.
- The CXS job-list route used by public career pages is tenant/site-specific and is not a documented global job-postings API. Secondary technical references describe the common `/wday/cxs/{tenant}/{site}/jobs` route and 20-result pagination; schemas and limits can change.
- A company name alone does not identify tenant, data-centre cluster and site. Those identifiers must be discovered from a public careers URL or another legitimate index.
- Workday documentation says external career sites can be excluded from third-party search-engine indexing. Therefore search-engine discovery cannot guarantee every employer. Internal-only and confidential postings are not public candidate vacancies.

**Consequence:** use automated URL/tenant discovery and, optionally, a licensed global job index as a coverage accelerator. Do not pretend there is a universal Workday endpoint.

### Keka

There are two separate interfaces:

- Keka's documented HRMS API uses OAuth/client credentials and is a customer integration API. Do not treat that as an open public API.
- Some employer-hosted `{tenant}.keka.com/careers` portals expose a public candidate-facing jobs interface. Third-party engineering references describe extracting a portal identifier from the careers page and requesting a public list. This is a tenant-specific public portal pattern, not a global Keka company directory and not a guarantee that every tenant enables the same interface.

**Consequence:** automatically discover tenant hostnames from search indexes, public company career links and sitemaps; then verify the candidate-facing page and feed. If the portal is private, disabled, robots-disallowed or returns an auth challenge, stop and mark it unavailable. Do not use customer OAuth credentials or bypass a block.

### Darwinbox

- Darwinbox's official Recruitment API documentation describes privileged APIs, with a mandatory API key for job-list calls and Basic Auth/OAuth supported for the API family.
- This customer API is per Darwinbox tenant/subdomain and cannot be called as a universal unauthenticated feed.
- Some employers expose public candidate-career pages and may have anonymous listings. This must be proven per public board; it is not evidence that all Darwinbox tenants expose a stable anonymous endpoint.
- Internal job postings and candidate-only/restricted portals are outside public crawling.

**Consequence:** discover public candidate boards automatically and use only verified anonymous listing interfaces. For employers whose jobs are only available through the privileged Recruitment API, JobBeeper needs an authorized partner/customer integration. Do not try alternate endpoints, session tricks, or credentials belonging to another employer.

### Other ATS providers

The same distinction applies to Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Recruitee, Personio, Teamtailor, Breezy and other providers:
- a provider's public job-board endpoint is usually scoped to one employer board/slug;
- an API for an employer's HR/recruiter account may require that employer's credentials;
- discovery of company/tenant identifiers is a separate problem from parsing a known board.

## 4. Proposed architecture

### A. Discovery providers (find employers/boards without manual entry)

Build a small set of complementary discovery channels, not one brittle crawler:

1. **Public search-index discovery.** Use a compliant search API/provider to discover career URLs and indexed ATS-hosted job URLs by platform pattern, country/region, role-family and scheduled query rotations. Save the actual result URL and discovery provenance. Do not scrape search-engine result pages in violation of their terms.
2. **Employer-domain crawler.** For employer domains already seen in public postings, inspect robots.txt, sitemaps, career links, JSON-LD and public pages. Follow only bounded, same-site HTTPS links. Extract links to known ATS hosts and branded career pages.
3. **ATS-specific pattern resolvers.** Recognize known hosts and provider-specific path/tenant identifiers. Resolve a candidate board from the actual public URL; never brute-force tenant names or guess company IDs.
4. **Global job-index API (high-priority proof of concept).** Evaluate Hirebase before building a large crawler from scratch. Its current public ATS coverage page lists Workday with 1,154,129 live jobs across 6,917 companies, and lists Keka and Darwinbox among additional indexed ATSs (without separate public counts for those two). Its product page claims 840k+ company career pages, 6.3M+ active listings and 80+ ATS platforms. These figures are vendor-stated, dynamic and not independently audited; they are not a promise of complete coverage. Hirebase's API supports job and company search, company jobs and paginated/filtered jobs, so it may supply both job candidates and company/board discovery signals. It should be tested with separate Workday, Keka and Darwinbox queries and a held-out set of known employer boards. Current pricing: Free is 500 jobs and 50 companies per month; Starter is $99/month for 25,000 jobs and 10,000 companies; Growth is $249/month for 250,000 jobs and 50,000 companies; Scale is $999/month for 2M jobs and 200,000 companies. Every returned job counts against the allowance, so fetching the whole index is not a free strategy. Hirebase advertises hourly refresh on paid plans and “under 2 hours” on its product page; this is vendor-reported and does not meet the 2-minute target by itself. Sources: https://www.hirebase.org/ats, https://www.hirebase.org/products/job-data-api, https://www.hirebase.org/pricing, https://www.hirebase.org/docs.
5. **Public provider directories and employer lists.** Use them only as discovery seeds. A directory entry is not proof the board still exists or that it publishes public vacancies.

### A1. Hirebase licence and cost gate

Hirebase's API documentation says every data endpoint requires an API key. Its Terms of Service (updated 2026-10-12) permit an account in good standing to access, display job data (including publicly in the customer's own apps), integrate/reformat/filter/combine it, and store/cache it. They prohibit reselling or redistributing the raw dataset/feed/API, giving users bulk download/export access, and building a competing job-data database/API. They also say personal job-seeker web use is non-commercial and commercial use requires an API plan. That may permit a curated JobBeeper user-facing job-search workflow, but JobBeeper's product scope and data use should be confirmed in writing with Hirebase before shipping the integration. Do not build a raw bulk export from their API into JobBeeper.

The free plan's 500 jobs/month is suitable for a small proof-of-coverage test, not broad ingestion. Before any paid plan, measure result quality/coverage, monthly result count, update latency, duplicates/closed jobs, India/Keka/Darwinbox coverage, and legal fit. The direct employer-board path remains the fallback/source of verification and the likely route for high-priority sources needing fresher-than-hourly checks.

### B. Global employer and board registry

Persist one record per employer/ATS board, not a JSON allowlist edited by hand.

Minimum fields:
- `company_id`, normalized company name, official domain, country/region;
- `provider`, canonical careers URL, hostname, tenant/board slug, Workday cluster/site or Keka/Darwinbox identifiers;
- `discovery_method`, `discovered_from_url`, first-discovered timestamp, last-verified timestamp;
- board status: candidate, verified, active, temporarily unavailable, blocked/auth-required, unsupported, stale;
- discovery confidence and verification evidence;
- parser version, last successful poll, next poll, cursor/page, last job count, consecutive failures, cooldown.

Do not persist secrets or arbitrary response bodies in this registry.

### C. Discovery confidence and automatic activation

Use explicit evidence levels:

- **High:** recognized provider URL, same-site public candidate endpoint verified, valid job schema, safe HTTPS job/application links, company identity/provenance coherent.
- **Medium:** official employer page links to a recognized ATS, but feed schema/tenant mapping needs one more verification.
- **Low:** search-index mention or third-party URL only, ambiguous employer/board identity, redirect or incomplete candidate page.

Policy:
- High-confidence public boards can be automatically activated after bounded verification and silent first-inventory baseline.
- Medium-confidence boards enter a compact review queue; automatically retry/reverify after a reasonable interval.
- Low-confidence, auth-required, robots-disallowed, unsafe, internal-only or schema-invalid candidates remain inactive.
- The manual “add company” form remains an exception tool, not the normal coverage workflow.

### D. Board-level poll scheduler

Move from source-level loops over a large static array toward a per-board due queue:
- provider-specific interval and jitter;
- bounded concurrency per provider/host and global worker pool;
- persistent `next_poll_at`, `last_success_at`, cursor/page, 429 cooldown;
- stop on 429; honor Retry-After; do not rotate proxies or evade provider limits;
- distinguish 403/404/auth-required/robots block from transient server failure;
- conditional GET/cache validators where supported;
- no repeated detail fetch when the posting fingerprint has not changed;
- periodic full reconciliation for updates and closures.

A 2-minute target applies only to verified high-priority boards that can be polled safely; do not promise a universal two-minute SLA where provider policies or response times disallow it.

### E. One shared ingestion and per-user matching pipeline

`discovery → verify → board registry → poll → normalize → deduplicate → legitimacy/staleness check → shared jobs store → per-user preference evaluation → per-user notification queue`

Do not run separate collectors per user. Do not apply the owner's profile to the global crawl. Keep user profile data private and never use it to decide which source boards exist.

## 5. Source confidence is not the same as source health

Keep three separate concepts:

1. **Board discovery confidence:** how sure JobBeeper is that this discovered URL belongs to the named employer and the ATS provider.
2. **Source operational health:** whether the collector can currently fetch that board; last successful poll, errors, 429s, retries, response time and missed schedule.
3. **Job legitimacy/freshness confidence:** whether an individual posting is present on the employer's public board, has a valid apply link, is still open, appears duplicated/reposted, and has defensible publication metadata.

A healthy HTTP 200 response does not prove every posting is legitimate or current. A low-confidence job does not necessarily mean its source is offline.

## 6. Phased delivery and acceptance

### P0-A — Coverage architecture and source observability
- Run a capped Hirebase proof-of-coverage evaluation (no integration key in source control): Workday, Keka and Darwinbox query support; employer/job URL validity; India coverage; response fields; closed/repost behavior; freshness; quota cost; Terms of Service suitability.
- Add registry-wide discovered/verified/active/pending counts by provider.
- Add automatic discovery queue and board-level scheduler metrics.
- Explain source telemetry in plain language (see `SOURCE_HEALTH_EXPLAINED_AND_UX_REDESIGN_2026-11-09.md`).
- Prove Workday/Keka/Darwinbox discovery from public sources without requiring manual company entry.

### P0-B — Broad discovery pilot
- Combine Hirebase as a possible coverage accelerator with compliant search-index discovery and direct public employer-board crawls; do not make one third-party index the only source of truth.
- Start with Workday/Keka/Darwinbox public candidate boards in India plus a small global sample.
- Validate at least 10 newly discovered employers across at least 2 discovery channels per provider; keep a held-out list for discovery recall.
- Verify list counts against each employer's public careers page.
- Prove board discovery repeats over several days and finds newly appearing tenant hosts.
- Verify first inventory remains silent and second poll deduplicates; notifications remain off during the pilot.

### P0-C — Production safety and matching/notifications
- Measure fetch → ingest → match → notify latency separately.
- Verify per-user profile matching and no cross-user leakage.
- Run two-user test with isolated chats/fake delivery transport.
- Keep no-backlog behavior: no alerts for historical inventory or jobs that appeared before the user's opt-in boundary.

### Acceptance before promising broad coverage
- No per-company manual entry required for high-confidence discovery.
- Each new board has source URL, provenance, status and last-verified timestamp.
- New company boards are added automatically from multiple discovery channels; discovery recall is reported as a measured sample, not guessed.
- No auth-wall/private data access, proxy bypass or robots/terms circumvention.
- Every job links to an employer/public ATS posting; source publication time is kept separate from first-seen time.
- Job-level dedupe, repost/stale detection and per-user match evaluation are observable.
- Coverage gaps for private/non-indexed employers are explicitly surfaced.

## 7. Evidence and references

Primary vendor documentation:
- Workday career sites are configured per employer and external pages can be excluded from third-party indexing: https://doc.workday.com/workday-education/en-us/course-manuals/recruiting-for-administrators/career-sites.html
- Workday external job postings and internal/external separation: https://doc.workday.com/admin-guide/en-us/human-capital-management/recruiting/job-postings/ayo1575554886570.html
- Darwinbox official Recruitment API and mandatory API key for job-list V3: https://api-docs.darwinbox.com/
- Keka official HRMS APIs use OAuth/client credentials: https://apidocs.keka.com/

Secondary technical evidence (use as a discovery lead, revalidate on the live employer board):
- Workday per-tenant CXS route and 20-row pages: https://www.hirebase.org/ats/workday and https://ctriolab.com/jobs/workday-jobs-api/
- Keka tenant portal discovery and public careers route: https://github.com/career-ops-hq/career-ops/blob/main/docs/SUPPORTED_JOB_BOARDS.md
- Keka public careers robots/route observations: https://apify.com/nexgenwatch/keka-jobs
- Hirebase job index claims, source coverage and API: https://www.hirebase.org/products/job-data-api
- Hirebase published API pricing: https://www.hirebase.org/pricing
- Hirebase current ATS coverage (Workday count, Keka/Darwinbox listed among additional ATSs): https://www.hirebase.org/ats
- Hirebase current API product claims (company/jobs/freshness): https://www.hirebase.org/products/job-data-api
- Hirebase current API docs (API key, job/company endpoints and free allowance): https://www.hirebase.org/docs
- Hirebase current API pricing: https://www.hirebase.org/pricing
- Hirebase Terms of Service (commercial-use, app-display, caching, no raw redistribution/bulk export, no competing dataset): https://www.hirebase.org/terms

Do not treat a third-party code repository or marketing coverage page as a vendor-guaranteed API contract.
