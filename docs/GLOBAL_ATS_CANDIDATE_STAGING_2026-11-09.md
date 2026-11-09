# Global ATS candidate staging — implementation and handover

**Date:** 2026-11-09 20:24 IST
**Branch:** `feat/global-ats-discovery-hirebase-guard-20261109`
**Status:** API/UI and focused tests implemented locally; full V2 regression passed 451/451 in 501.840s (job `lkscpl0ioe`); not yet committed/pushed or exact-head CI-verified.

## Product rule

A public ATS URL is not an employer record. A Workday tenant slug, Keka portal slug or Darwinbox company ID cannot reliably establish the legal/display employer name or canonical employer website. Therefore unmatched ATS URLs are stored separately and must not create synthetic `employer_companies` rows.

## New database table

`ats_global_discovery_candidates` contains:
- `id`, `provider`, `board_key`, canonical `board_url`, `candidate_host`;
- `discovery_method`, `source_reference`, `source_captured_at`;
- `first_discovered_at`, `last_seen_at`, low `confidence`;
- `review_status` (`discovered`, `linked`, `rejected`, `stale`);
- nullable `linked_company_id`, `linked_board_registry_id`, `last_error_type`, `created_at`, `updated_at`.

Candidate uniqueness is `(provider, candidate_host, board_key)`. This matters for Darwinbox where separate tenant hosts may reuse a company ID. The normal board registry remains unchanged and still requires a real company ID.

## Admin-only endpoints

- `POST /api/discovery/global-candidates/import`: accepts 1–200 candidate objects. Each needs `board_url`, supported `discovery_method`, and `source_reference`; optional `source_captured_at` accepts ISO or 14-digit Common Crawl time. Batch items are canonicalized to public Workday/Keka/Darwinbox roots. Invalid items are reported as skipped; no employer/board rows are created.
- `GET /api/discovery/global-candidates?status=&provider=&limit=`: lists candidates, provenance, confidence, review status and any linked employer/board status.
- `POST /api/discovery/global-candidates/{id}/link` with `{company_id}`: associates only to an existing employer. It reuses a normal board registry row for the exact same provider+URL if present; rejects cross-employer conflicts; otherwise inserts a low-confidence `discovered` ATS board. It does not verify or activate a source.
- `POST /api/discovery/global-candidates/{id}/review` with `{status:'rejected'}`: marks an unlinked candidate rejected. Linked candidates are managed through normal board review.

All endpoints are admin-only. Candidate import has a 200-item batch cap. Supported methods: `commoncrawl_cdx`, `commoncrawl_url_index`, `sitemap`, `career_link`, `licensed_seed`, `manual`. Confidence is always `low` at this stage.

## Import/re-discovery behaviour

- Existing candidates are upserted by provider+host+board key; `first_discovered_at` is preserved and `last_seen_at` is refreshed.
- The most recent capture timestamp/reference wins. Older captures do not overwrite newer provenance.
- `linked` and `rejected` are terminal for re-import; repeated sightings do not reset their review state.
- No employer row or ATS registry row is created by import.
- Linking a candidate is not verification. The resulting ATS board remains `discovered` unless it reuses an already-verified exact URL; activation remains a separate action.
- Darwinbox candidate identity includes host in the unique staging key, avoiding collisions across tenants with the same internal company ID.

## URL canonicalisation

- Workday: validates a public `*.wdN.myworkdayjobs.com` host, strips optional locale and deeper captured paths to the public site root, validates tenant/site with existing parser.
- Keka: accepts `/careers` and `/careers/{portal}` plus captured deeper job paths; canonicalizes to the corresponding portal root using the strict existing resolver.
- Darwinbox: accepts a public `*.darwinbox.in/ms/candidatev2/{company_id}/careers` path (including deeper captured paths), canonicalizes to candidate careers root.
- All reject non-HTTPS URLs, credentials, nonstandard ports, query strings/fragments and unsupported hosts/routes.

## Admin UI

Coverage & Health now has an “Unmatched global ATS candidates” panel:
- manual/captured URL staging form with discovery method, provenance reference and optional capture time;
- candidate list with provider/root/source/capture/confidence/status;
- select from existing employers and link action;
- reject action with confirmation;
- after linking, normal ATS registry table refreshes, but the board remains discovered/unverified/unactivated.

The employer association dropdown loads from the existing `/api/discovery/companies` endpoint. If no employer exists, the admin must first use the employer discovery form; the candidate import never fabricates one.

## Tests added

New `GlobalDirectoryApiTests` cases cover:
- staging Workday/Keka/Darwinbox canonical roots with zero employer and board rows;
- host-aware Darwinbox candidate uniqueness;
- capture timestamp normalization and older capture not replacing latest reference;
- re-import deduplication and preservation of rejected/linked terminal states;
- admin-only list/import/link/reject and batch-size validation;
- link to an existing employer creates only a discovered board and leaves source disabled;
- idempotent link, existing exact verified board reuse, cross-employer conflict and linked-board status reporting.

Focused suite: `v2.test_global_discovery_hirebase.GlobalDirectoryApiTests` — **11 passed** after final provenance and link-state refinements.

Final full V2 regression job `4q00ns5dgm` finished with 451 passed in 482.864s, exit code 0; log `/tmp/job-radar-global-candidate-final-tests.log`. Exact-head GitHub V2 CI #1437 (`42648073320`) also passed the full suite and modern dashboard JS syntax.

HTML candidate controls have unique IDs and the dashboard loader/import/link/reject functions are wired. VM Node 12 cannot parse existing dashboard optional chaining/nullish-coalescing; modern dashboard JS syntax requires exact-head GitHub V2 CI after push.

## PR and deployment status

Candidate staging was committed at `243da9c35e93979e59d0de281130581cad4124d1`, pushed to PR #65, and exact-head CI #1437 passed. The exact same immutable candidate image is deployed on shared dev 8001 and connector QA 8010. Both run eight real public source feeds; LinkedIn and Hirebase remain off; notifications and external LLM credentials are off. Dev completed multiple cycles and QA has one complete initial pass. Connector QA repeat pass: 2 runs per source, 1,891 total live jobs, 0 HTTP 429/page/board failures, SQLite integrity ok and zero sends. Dev DB latest: 10,278 jobs / 8,228 runs / integrity ok / zero sends. Exact-head docs CI #1438 passed on `b09cba6`. Detailed metrics, backups, cadence, SSH tunnels and the remaining QA-account action are in `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md`. Production remains untouched.

## Explicitly not implemented yet

- No Common Crawl CDX requests or Parquet/Athena extraction have been made.
- No autonomous career-site/sitemap crawler has been implemented in this increment.
- The manual admin form is a staging entry point for an externally captured URL; the next step is the polite serialized Common Crawl worker described in `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`.
- No live board verification, activation or ingestion happens at staging time.

## Next priorities

### P0
1. Finish the full V2 test job, fix any regression, and update this document with exact count/time.
2. Commit/push candidate staging + UI + tests/docs to PR #65 and verify exact-head V2 CI.
3. Implement a serialized Common Crawl CDX candidate harvester with global request lock/budget, one provider query per run, pinned crawl ID, 24-hour stop after 503, response caps and provenance.
4. Add reviewed current-live board verification for candidates and an admin association/link flow; import alone never activates.
5. Continue the per-board scheduler (next_due_at, host budgets, jitter, Retry-After, cooldown, cursors, backpressure, queue age).

### P1
6. Add sitemap/career-link candidate harvesting with host-aware crawl budgets and robots policy.
7. Benchmark first-seen latency, freshness, p50/p95, 429s and completeness on an approved canary set.
8. Darwinbox 403/429/5xx per-board classification; keep 403 blocked.

## User action / safety

Nothing is required from the user now. Hirebase key remains absent. Workday/Keka/Darwinbox/Hirebase are all disabled in both configs. No live ATS requests, Common Crawl calls, deployments, restarts, imports, source activations or notifications.
