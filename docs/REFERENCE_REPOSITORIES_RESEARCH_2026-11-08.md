# External repository research for JobBeeper

**Date:** 2026-11-08  
**Scope:** Read-only review of two public repositories, compared against JobBeeper's current V2 architecture.  
**Production impact:** None. This document is research only; no external source code was copied into production.

## Executive summary

The two repositories are useful in different ways:

1. **[career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops)** is a substantial local-first career workflow tool. Its provider layer is directly relevant to JobBeeper's ATS coverage: it contains independent adapters for a broad range of public ATS systems, a strict provider contract, source-validation guidance, redirect/SSRF protections, and extensive provider-specific regression tests. This is the high-value technical reference.
2. **[itshoax/career-ops-extension](https://github.com/itshoax/career-ops-extension)** is an application form-filling and learning extension for the Career-Ops workflow. Its README describes Kimi Webbridge prompts, human review before submission, LinkedIn job-search modes, and a local SQLite knowledge base that learns from applicant corrections. It is not an ATS collector or browser extension for discovering employer boards. Its useful ideas belong to a later optional application-assistance product area, not the current ingest/latency milestone.

**Recommendation:** Keep JobBeeper's current FastAPI + SQLite + dashboard + Telegram architecture. Borrow the provider design, validation checklist, safe HTTP practices, and selected tests from Career-Ops. Do not transplant its Node CLI, prompt system, file-based tracker, local LLM integration, Go TUI, or the extension's Kimi/Webbridge stack.

## Repository 1: career-ops-hq/career-ops

- Repository: https://github.com/career-ops-hq/career-ops
- Default branch observed: `main`
- Architecture reference: `ARCHITECTURE.md`, `docs/ARCHITECTURE.md`
- Provider contract: `providers/ADDING_A_PROVIDER.md`
- Source catalogue: `docs/SUPPORTED_JOB_BOARDS.md`
- Provider registry: `providers/_registry.mjs`
- Scan entrypoint: `scan.mjs`
- Board verification: `verify-portals.mjs`

### What it does

Career-Ops separates its system code from candidate-owned files. Its core discovery path is a zero-token Node scanner that calls public/no-auth ATS APIs and RSS/JSON feeds through small modules under `providers/`. Job evaluation and application workflows are separate from discovery. The tool's canonical user data is human-readable, git-diffable files; SQLite is a derived query index rather than its permanent source of truth.

The provider module contract is small:

- Optional `detect(entry)` identifies whether a configured career URL belongs to the provider.
- Required `fetch(entry, ctx)` returns normalized job records.
- The shared HTTP context handles fetching, timeouts/retries/caching and network controls.
- Provider modules do not own persistence or write tracker files.
- The scanner owns common filters, deduplication, output and history.

This is a useful separation of responsibilities even though JobBeeper's runtime and storage model are different.

### Most relevant learning: broad ATS coverage

The provider catalogue includes many of the systems in JobBeeper's planned coverage list, including:

- Workday
- Avature
- Ashby
- Greenhouse
- Lever
- BambooHR
- Breezy
- Keka
- Darwinbox
- SmartRecruiters
- Workable
- iCIMS
- ADP Workforce Now
- Oracle Cloud
- Jobvite
- Personio
- Recruitee
- Teamtailor
- Paylocity
- UKG/related enterprise ATS integrations

The catalogue is a research index, not a guarantee that every tenant is accessible or that every endpoint remains stable. Each candidate tenant must be checked against its actual public careers page and endpoint.

### Exact protocols learned from reference providers

#### Keka

Reference: `providers/keka.mjs`.

The tenant careers page is a small shell. The adapter reads a UUID from a fragment path shaped like:

`/ats/documents/<uuid>/careerportal/...`

It then reads the public embed feed:

`GET https://<tenant>.keka.com/careers/api/embedjobs/default/active/<uuid>`

The response is a top-level jobs array. The list includes title, description, locations and `publishedOn`. The feed is not paginated in the observed contract. The reference provider reconstructs the tenant origin from a strict host pattern, discards caller-provided paths/ports, and rejects malformed rows instead of declaring an unexpected envelope to be an empty board.

**JobBeeper status:** We independently verified a real public tenant, `bridgestone1.keka.com`, on 2026-11-08. The public feed returned HTTP 200 and 109 listings. JobBeeper's isolated local collector rehearsal ingested 109 jobs on first poll as a silent baseline, then reported zero new jobs on the second poll. The database integrity check remained `ok`, and no notifications were sent in the rehearsal. This provides concrete evidence that Keka can be supported through our existing pipeline.

#### Darwinbox

Reference: `providers/darwinbox.mjs`.

The candidate portal route contains the company ID:

`https://<tenant>.darwinbox.in/ms/candidatev2/<companyId>/careers/...`

The observed public candidate endpoint is:

`POST https://<tenant>.darwinbox.in/ms/candidateapi/job/alljobs?companyId=<companyId>`

with body fields `companyId`, `page`, `sort_option: "new"`, and `limit`. The response is expected to contain `status: "success"` and a `data` array. The reference implementation uses bounded pages, short inter-page pacing, stable posting URLs, and careful date handling: `posted_on` is epoch seconds, while `created_on` is a fallback.

**JobBeeper status:** Three initial tenant probes were blocked, but a later direct verification of the JG Summit candidate portal returned HTTP 200 and 18 listings on 2026-11-08. An isolated two-poll test ingested 18 jobs on the baseline poll and zero new jobs on the second poll, with no alerts. This proves that the endpoint works for that tenant and network path; it does not prove every Darwinbox tenant will expose the endpoint or avoid WAF/Cloudflare restrictions. Keep endpoint verification per discovered company mandatory.

### Engineering practices worth adopting

1. **Strict normalized provider contract.** Every source should return the same normalized job fields and leave persistence, matching, dedupe, notifications and API response ownership to core JobBeeper code.
2. **No silent empty results.** A response schema mismatch must be a source error, not a successful poll with zero jobs. Drop an isolated malformed row; fail the board when the whole response envelope is unexpected.
3. **Bounded pagination.** Every provider needs a known page size, hard maximum pages/records, a stop condition based on source metadata or short pages, and modest inter-page delay where necessary.
4. **One source, one adapter.** Keep provider-specific parsing and pagination in a small file/module or focused function. Avoid a generic collector with many provider-name conditionals that become difficult to reason about.
5. **Safe redirects and URL construction.** Reject cross-host redirects; do not let a user-provided path, port or redirect turn a public-board fetch into an internal request. JobBeeper already uses public URL validation in discovery; the same discipline must cover adapter network calls.
6. **Retries only for transient failures.** Honor Retry-After and back off on 429/5xx/timeouts. Do not retry permanent 4xx responses indefinitely or interpret WAF-denied data as an empty list.
7. **Probe and collection are different operations.** An admin verification probe should make the smallest bounded request possible and never schedule polling or mutate candidate notification state. A full collector has its own pagination and ingestion behavior.
8. **Tests per provider plus cross-provider safety tests.** Cover URL detection, response parsing, malformed envelopes, dates, duplicate IDs, pagination, 429, hard caps, redirects and no cross-board contamination.
9. **Keep source policy explicit.** Career-Ops documents source eligibility and checks robots.txt by path. JobBeeper should continue to use public employer-attributed postings, avoid login bypass/proxy rotation/CAPTCHA circumvention, and review source access rules before enabling any new board.

### What not to copy

Career-Ops is a local-first CLI and prompt workflow whose durable state is a set of local files. JobBeeper is an always-on hosted web service with multiple users, centralized SQLite storage, a notification ledger and a Telegram delivery path. Copying Career-Ops' data model, Node runtime, prompt execution architecture, tracker file format or optional Go TUI would create a parallel system instead of improving JobBeeper.

The provider patterns, source validation checklist and bounded HTTP design are the reusable parts.

## Repository 2: itshoax/career-ops-extension

- Repository: https://github.com/itshoax/career-ops-extension
- Default branch observed: `main`
- Main documentation reviewed: `README.md`
- The repository tree reviewed for this note exposes a README as its tracked file; implementation claims below are therefore attributed to the README's described behavior rather than independently validated against source modules.

### What it does

The project calls itself `apply-factory`, an extension for Career-Ops. It does not primarily fetch jobs from ATS platforms. It adds an application-assistance workflow:

1. Career-Ops evaluates a job and writes a report with prepared application answers.
2. The user invokes a fill command for that report.
3. The extension emits a prompt for Kimi Webbridge to type into the application page.
4. The user checks and corrects fields.
5. The browser agent creates a pre-submit snapshot.
6. The extension learns reusable answers from that snapshot.

The user still clicks Submit. The README explicitly describes a `never_auto_submit` setting and a human review checkpoint.

It also documents three LinkedIn discovery modes (browser-assisted full scrape, search URL generation, and manually supplied URLs) and an application knowledge base using a local SQLite database.

### Useful ideas for JobBeeper

- **Human-in-the-loop application assistance:** eventually let a user move from a matched job to a prepared application workspace without allowing silent or automatic submissions.
- **Candidate-specific reusable answers:** store reusable factual answers (work authorization, notice period, location, education, etc.) per user, but separate them from job-specific answers such as “why this company?” to avoid reusing incorrect text.
- **Correction-based learning with audit trail:** distinguish a newly learned answer, a confirmed answer and a user-corrected answer. Corrections should be attributable to the user and reviewable.
- **Explicit snapshots before external actions:** save the completed application form state for user review before any submission.
- **LinkedIn discovery as a separate acquisition mode:** browser-assisted/manual URL capture can complement permitted server-side sources, but it is not a substitute for stable public ATS APIs and will need to account for login state, changing DOM structure and source terms.

### What not to copy

- Kimi Webbridge and its prompt-driven DOM typing are vendor-specific and create an extra dependency.
- The extension's orchestration commands assume the Career-Ops local CLI, report format and Section G headings.
- A local per-installation knowledge-base DB is not a replacement for JobBeeper's per-user data model and server authorization.
- Browser DOM scraping is more brittle than a stable public ATS API and should not be introduced into the ingestion service as the default connector method.
- Do not allow automated submission of applications. Preserve explicit user review and user-controlled final submission.

## Direct comparison with JobBeeper

| Concern | Career-Ops | apply-factory extension | JobBeeper approach |
|---|---|---|---|
| Primary purpose | Job scanning, evaluation and career workflow | Application form assistance and answer learning | Fresh job discovery, personalized matching and Telegram notifications |
| Runtime | Local Node.js CLI, prompts and scripts | Local Python + AI CLI / Kimi Webbridge | Hosted FastAPI service |
| Job acquisition | Public per-provider ATS modules and RSS/JSON | LinkedIn browser-assisted search, plus manual URLs | Python collectors and Naukri relay |
| Persistence | Human-readable user files; derived SQLite index | Local SQLite answer knowledge base | Shared job observations and canonical opportunities in SQLite |
| Notifications | Not its main function | None as the core described feature | Telegram delivery and ledgers |
| Extension/browser role | Optional browser extraction/liveness | Form filling and snapshots | Dashboard today; browser helper could be optional later |

## Recommended JobBeeper adoption plan

### P0 — Apply now to the connector engineering process

- Keep every ATS adapter small and testable.
- Maintain a shared job record contract: source, source job ID, company, title, location, public posting URL, source publication timestamp, precision, description and source-specific details.
- Keep source observation time separate from actual posting time. Do not infer an exact publication timestamp from date-only labels or from a later update timestamp.
- Validate a board endpoint before activation, but do not confuse a successful first-page probe with a complete scan.
- Apply strict page/request budgets and source-specific cooldowns.
- Make the first collection from a newly activated board a silent baseline and only later new observations eligible for notifications.
- Emit per-source and per-request latency metrics: request duration, HTTP status, retry count, page count, board count, jobs returned, jobs newly ingested and freshness age.
- Keep user notification matching and delivery separate from the global legacy notifier. Test using separate test users/chats and never cause old historical postings to be sent as new.

### P1 — Use the provider catalogue to plan the next sources

Prioritize providers already identified in Career-Ops and relevant to the JobBeeper target-employer mix. Current order proposed:

1. Workday (many tenant boards, larger pagination and facet complexity).
2. Avature (tenant-specific public career pages; verify the public listing API per tenant).
3. Keka (already live-verified and two-poll rehearsed in an isolated DB).
4. Darwinbox (already live-verified for one tenant; verify each tenant and monitor WAF behavior).
5. BambooHR, Breezy and Teamtailor.
6. SmartRecruiters, Workable, Greenhouse, Ashby and Lever improvements as needed.

This is not a universal platform popularity ranking. It is an implementation sequence based on the current target list, observed endpoint feasibility and existing JobBeeper work.

### P2 — Optional application assistant, only after discovery is stable

A separate user-facing module could:
- collect job-specific application fields;
- suggest candidate-approved reusable answers;
- record user corrections as new answer versions;
- prepare a form snapshot;
- open the external application page;
- require the user to review and submit manually.

This would be a separate product milestone, not part of the job collector or Telegram notifier.

## Validation checklist for future ATS additions

- [ ] Confirm a real employer's public careers URL.
- [ ] Confirm the board provider and the exact tenant/company identifier.
- [ ] Check robots.txt and applicable access rules.
- [ ] Probe one public endpoint with bounded request/response sizes.
- [ ] Verify the response envelope, empty-board semantics and posting identifier.
- [ ] Determine whether dates are epoch seconds, milliseconds, ISO timestamps, relative labels or date-only.
- [ ] Confirm canonical employer posting URLs and location field semantics.
- [ ] Implement pagination with hard request/job caps and backoff.
- [ ] Add unit tests for parser, URL detection and failure modes.
- [ ] Run two ingestion polls against an isolated database.
- [ ] Verify first-poll baseline suppression and second-poll deduplication.
- [ ] Verify no user-facing notification is emitted during baseline.
- [ ] Run CI and latency/source-telemetry checks before promotion.

## Sources and reviewed references

All implementation observations are based on repository files as they appeared on 2026-11-08:

- [Career-Ops architecture](https://github.com/career-ops-hq/career-ops/blob/main/ARCHITECTURE.md)
- [Career-Ops runtime architecture](https://github.com/career-ops-hq/career-ops/blob/main/docs/ARCHITECTURE.md)
- [Supported job boards](https://github.com/career-ops-hq/career-ops/blob/main/docs/SUPPORTED_JOB_BOARDS.md)
- [Provider authoring and security contract](https://github.com/career-ops-hq/career-ops/blob/main/providers/ADDING_A_PROVIDER.md)
- [Keka provider](https://github.com/career-ops-hq/career-ops/blob/main/providers/keka.mjs)
- [Darwinbox provider](https://github.com/career-ops-hq/career-ops/blob/main/providers/darwinbox.mjs)
- [Workday provider](https://github.com/career-ops-hq/career-ops/blob/main/providers/workday.mjs)
- [Provider registry](https://github.com/career-ops-hq/career-ops/blob/main/providers/_registry.mjs)
- [Career-Ops extension README](https://github.com/itshoax/career-ops-extension/blob/main/README.md)
- JobBeeper's own current architecture: `README.md`, `v2/README.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md`.

## Handoff

This document is a research artifact. It does not merge, activate or release new collectors. Keka and Darwinbox work in progress is tracked separately on the connector-development branch. Before that work is promoted, re-run the full JobBeeper V2 test suite, complete the security/redirect tests, add latency evidence, update the operational handover, and promote through the normal reviewed release path.
