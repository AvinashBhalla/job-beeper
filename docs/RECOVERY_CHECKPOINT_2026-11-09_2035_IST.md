# JobBeeper recovery checkpoint — 2026-11-09 20:35 IST

## Current branch and PR

- Repository: `AvinashBhalla/job-beeper`.
- Worktree: `/tmp/job-radar-global-discovery`.
- Branch: `feat/global-ats-discovery-hirebase-guard-20261109`.
- PR: [#65](https://github.com/AvinashBhalla/job-beeper/pull/65), open, draft, mergeable, base `v2-live-radar`.
- Latest code commit: `4d7513803031d1c32c02a19ac8452dfb221c02ad` (`feat: add bounded Workday facet inventory`).
- Latest code commit exact-head GitHub V2 CI: **#1435**, run ID `42640211533`, completed successfully.
- Working tree was clean immediately after pushing 4d75138; this checkpoint is a documentation-only follow-up.

## Completed and verified

### Hirebase / global directory foundation
- Optional estimate-first Hirebase sampler, disabled by default, server-key-only, budget ledger and 429 cooldown. Key absent; no API calls.
- LastRound AI August 2026 CC BY 4.0 directory (9,935 Greenhouse/Lever/Ashby candidates) imported only as unverified review candidates.
- Admin registry coverage summary does not invent market coverage.

### Workday incremental + facet-aware inventory
- First page (offset 0) remains on existing 120-second freshness cadence.
- At most one extra inventory page per board every 15 minutes; durable cursor; failed inventory pages are throttled without cursor advance; progress commits after upsert.
- Root queries capped at 2,000 use persisted facet queue in order `jobFamilyGroup`, `timeType`, `locations`, `workerSubType`; capped children recursively split using an unused facet.
- Queue and active filters are migration-safe SQLite state keyed per tenant:site. Stable source IDs and DB upsert deduplicate overlapping facet partitions.
- Bounds: facet depth 4, pending queue 500, no concurrent fan-out. Incomplete leaves/queue overflow/depth exhaustion/unsupported facet remain explicitly incomplete.
- Admin-only `/api/workday/inventory-status` and Coverage & Health UI show pending partitions/active filters and incomplete-in-progress vs terminal truncation.
- No live Workday API requests; facet behaviour tested with mocked HTTP. Tenant-specific facet availability/counts require a future approved canary.

### Keka
- Default and non-default `/careers/{portal}` URLs supported; tenant:portal identities; portal-specific embed and job-detail routes; multiple portals per tenant; strict URL validation.

### Research and next discovery design
- Freehire, Career-Ops, ats-scrapers, JobSpy, JobNavigator, Job Board Aggregator, Job Forager researched.
- Common Crawl rate-limit constraints documented: serialized CDX calls, no proxy/parallel queries, stop for 24h after 503; Parquet URL Index/Athena for broad filtering.
- New design: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Candidate staging must be separate from real employer records because ATS registry requires `company_id`; do not manufacture an employer name from a tenant slug.

## Validation

- Full local V2 suite on exact Workday facet tree: **444 passed in 346.385 seconds**, exit code 0. Job `3tjy6iwusp`; log `/tmp/job-radar-workday-facets-final-tests.log`.
- Focused Workday collector tests: 22 passed.
- `compileall`, both config JSON files, `git diff --check`, HTML unique-ID/panel contract, Workday JS loader wiring passed.
- GitHub V2 CI #1435 passed: Python compile, modern dashboard JavaScript syntax, focused router/extractor tests and full V2 unittest suite.
- Prior Keka CI #1431 and Workday baseline CI #1430 also passed.

## Next priorities

### P0
1. Build `ats_global_discovery_candidates` (or similar) staging table without mandatory employer ID, with provider/board key/URL/source method/crawl ID/capture time/confidence/first-last-seen/review status and optional links to real company/board rows. Re-discovery must not revive rejected records.
2. Add admin-only candidate list/import/link/reject API/UI. Candidate discovery must not create synthetic employer identities, verify automatically or activate sources.
3. Add a polite Common Crawl discovery worker: refresh crawl catalogue infrequently; one provider query at a time; global host budget and timestamp; stop for 24h after 503; candidate-only output; record truncation; no archived job postings as current jobs. Broad Parquet URL Index/Athena option requires AWS account and explicit budget.
4. Live-verify candidates with existing safe probe only after admin association; link verified candidate to the normal ATS registry; activation remains separate.
5. Build persistent per-board due scheduler with host concurrency budgets, jitter, Retry-After, cooldown, checkpoints, backpressure and queue-age observability.

### P1
6. Darwinbox per-board 403/429/5xx classification and re-verification; 403 stays blocked; no Cloudflare/TLS bypass.
7. Benchmark p50/p95, 429, inventory completeness, first-seen delay and user-feed lag.
8. Improve stale/repost and legitimacy signals after ingestion coverage is reliable.

### P2
9. Add more ATS adapters once discovery/registry/scheduler contracts are stable.
10. Hirebase estimate-only dev experiment only after user securely configures the key and explicitly approves; no commercial multi-user use without written permission.

## User input / safety

- Nothing required from the user now. Do not ask for Hirebase key in chat.
- Workday/Keka/Darwinbox/Hirebase remain disabled in both configs.
- No live ATS/Hirebase API calls, no source activation, no deployment/container restart, no production/shared-dev change, no live DB import or notification delivery.
- PR #65 remains draft and unmerged. Keep it draft until candidate-discovery and scheduler work is reviewed.
