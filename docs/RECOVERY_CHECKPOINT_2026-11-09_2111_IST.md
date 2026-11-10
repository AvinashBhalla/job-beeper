# JobBeeper recovery checkpoint — 2026-11-09 21:11 IST

## Start here

1. VM worktree: `/tmp/job-radar-global-discovery`.
2. Repository: `AvinashBhalla/job-beeper`.
3. Branch: `feat/global-ats-discovery-hirebase-guard-20261109`.
4. PR: [#65](https://github.com/AvinashBhalla/job-beeper/pull/65), open/draft/mergeable, base `v2-live-radar`.
5. Latest pushed branch head before candidate staging: `59bbf8adddfb0b480e07573e1be24f26b5aa43b1`.
6. Candidate staging implementation/UI/tests are now locally validated but uncommitted; full V2 suite passed. Exact-head GitHub CI is still required after push.

## Previously completed and exact-head CI verified

- Hirebase optional estimate-first dev sampler, quota ledger, 429 cooldown and admin UI. Disabled; key absent; no API calls.
- LastRound AI August 2026 CC BY 4.0 candidate seed directory, 9,935 Greenhouse/Lever/Ashby rows; candidate-only/no auto-activation.
- Workday incremental + bounded facet-aware inventory; 120s fast poll; max one inventory page per board per 15m; persisted facet queue; depth 4/queue 500; incomplete leaves explicit; admin progress UI. Local V2 444 passed; exact-head CI #1435 passed on `4d75138`.
- Keka default/non-default portal URL resolver/collector/verifier, tenant:portal identity and URL validation. Local V2 439 passed; exact-head CI #1431 passed.
- Research for Freehire, Career-Ops, ats-scrapers, JobSpy, JobNavigator, Job Board Aggregator, Job Forager, and Common Crawl. Common Crawl CDX must be serialized; no proxies/parallel requests; stop for 24h on 503; Parquet/Athena is paid and requires budget.

## Current increment — unmatched global ATS candidate staging (uncommitted)

### Database
- New `ats_global_discovery_candidates` table, separate from employers and normal ATS board registry.
- Candidate fields: provider, board_key, canonical board URL, host, discovery method, source reference/capture timestamp, first/last seen, low confidence, review status and optional linked company/board IDs.
- Unique identity `(provider, candidate_host, board_key)` so Darwinbox hosts with the same internal ID do not collide.
- Import never creates an employer or normal ATS board row.

### Admin-only API
- `POST /api/discovery/global-candidates/import`: batch of 1–200, strict HTTPS Workday/Keka/Darwinbox canonicalization, allowed method/reference/capture time. Invalid rows are skipped with errors. Returns zero company/board creation counters.
- `GET /api/discovery/global-candidates?status=&provider=&limit=`: list with provenance, confidence, review state and actual linked board status.
- `POST /api/discovery/global-candidates/{id}/link` with existing `company_id`: reuses an exact provider+URL board when possible; rejects cross-employer/key conflicts; otherwise inserts a low-confidence `discovered` board. No verification or activation.
- `POST /api/discovery/global-candidates/{id}/review` with `status=rejected`: rejects unlinked candidates; linked candidates are managed in normal board registry.
- All routes admin-only. Batch limit 200. Allowed methods: commoncrawl_cdx, commoncrawl_url_index, sitemap, career_link, licensed_seed, manual.

### Import / identity / provenance behavior
- Workday: locale/deep page URLs canonicalized to public tenant/site root.
- Keka: `/careers` and `/careers/{portal}` deep captures canonicalized to default/non-default portal root.
- Darwinbox: candidate careers path canonicalized; unique candidate identity includes the tenant host even if company ID repeats.
- Re-import preserves first-discovered and terminal linked/rejected decisions, refreshes last-seen, and only replaces source reference/method/capture timestamp with a newer capture.
- `source_reference` must be string and <= 2,048 chars; timestamp ISO or Common Crawl 14-digit format.
- When linking, candidate provenance remains on staging record; normal board discovered_from uses a safe HTTPS provenance URL or the candidate board root.
- Linking to an existing exact verified board reuses it and reports its actual status; it does not downgrade it.

### Admin UI
- Coverage & Health now has a candidate staging form for public URL, discovery method, source reference and optional capture time.
- Candidate table shows provider, board root, provenance, capture time, confidence/state, existing-employer selector, Link and Reject actions.
- Employer selector uses existing employer records. If no employer exists, admin must create/review it first; no synthetic company is invented.
- Link refreshes normal ATS board registry; newly linked board remains `discovered`/unverified/unactivated.

## Validation

- Focused `GlobalDirectoryApiTests`: **11 passed** (latest API refinements).
- Full V2 regression on corrected candidate worktree: **451 passed in 501.840 seconds**, exit code 0. Job `lkscpl0ioe`; log `/tmp/job-radar-global-candidate-final-tests.log`.
- `compileall`, JSON config validation, `git diff --check`, HTML unique-ID/panel checks and candidate/Workday dashboard loader wiring passed.
- The previous full-suite job `a8icgcj402` was stopped after refinements; its result is not used. Use `lkscpl0ioe` as the authoritative full-suite result.
- VM Node 12 cannot parse existing dashboard optional chaining/nullish coalescing. Exact-head GitHub V2 CI must validate modern dashboard JS syntax after push.

## Next agent: immediate actions

1. Review current `git diff`; candidate staging work is uncommitted in the worktree.
2. Commit/push candidate code, tests, UI and docs on this same branch/PR #65.
3. Update PR body with 451-test local result; verify exact-head GitHub V2 CI and dashboard JS syntax.
4. Keep PR #65 draft/unmerged; do not deploy.
5. Then implement the serialized Common Crawl CDX worker: slow catalogue refresh, one provider query per invocation, global request lock/budget/timestamp, no parallel/proxy calls, 24h cooldown after 503, capped/incomplete response handling, candidate-only output with capture provenance.
6. Follow with sitemap/career-link discovery under robots and host budgets, current-public verification, then persistent per-board due scheduler/host rate budgets.

## Priorities

### P0
1. Exact-head CI for candidate staging.
2. Serialized Common Crawl CDX and public sitemap/career-link candidate discovery.
3. Live-verify reviewed candidates; link to real employer/normal board registry; candidate import alone never verifies or activates.
4. Per-board scheduler with next_due_at, host concurrency, jitter, Retry-After, cooldowns, page/facet state, backpressure and queue age.
5. Darwinbox per-board 403/429/5xx; 403 remains blocked; no Cloudflare/TLS bypass.

### P1
6. p50/p95, 429, board completeness, first-seen delay and feed lag benchmarks.
7. stale/repost and legitimacy signals after ingestion coverage stabilizes.

### P2
8. Additional ATS adapters after discovery/scheduler contracts are stable.
9. Hirebase estimate-only dev experiment only after secure key configuration and explicit user approval; no commercial multi-user use without written permission.

## User action / safety

- Nothing required from the user now; do not request Hirebase key in chat.
- Workday/Keka/Darwinbox/Hirebase remain disabled in both config files.
- No live ATS, Common Crawl or Hirebase network requests; no activations, deployments, restarts, live DB imports, notifications or production/shared-dev changes.
- PR #65 stays draft and unmerged.
