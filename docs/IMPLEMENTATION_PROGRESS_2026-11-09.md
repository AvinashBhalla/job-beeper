# JobBeeper implementation progress — 2026-11-09

## Start here

1. `docs/RECOVERY_CHECKPOINT_2026-11-09_2111_IST.md` — latest verified state, tests, safety and next steps.
2. `docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md` — candidate table/API/UI design and validation.
3. `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md` — Common Crawl and unmatched discovery approach.
4. `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md` — completed Workday inventory architecture.
5. `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md` and `docs/ATS_PROVIDER_GAP_ANALYSIS_2026-11-09.md` — research and code comparison.

## Completed and CI verified in PR #65

- Optional Hirebase estimate-first dev sampler and quota guard, disabled; no key/API calls.
- LastRound AI CC BY 4.0 candidate directory (9,935 Greenhouse/Lever/Ashby rows), unverified only.
- Workday incremental/facet-aware inventory and admin status UI; full V2 444 passed; exact-head CI #1435 passed.
- Keka default/non-default portal resolution/collection/verification; full V2 439 passed; exact-head CI #1431 passed.
- Open-source research and Common Crawl candidate-only architecture.

## Current uncommitted increment

- Separate `ats_global_discovery_candidates` SQLite table, unique by provider+host+board key.
- Admin-only import/list/link/reject APIs; no synthetic employer creation.
- Strict Workday/Keka/Darwinbox URL canonicalization, source provenance, capture timestamps, low confidence, terminal state preservation.
- Existing company association only; link creates/reuses normal board row as discovered, never verifies/activates.
- Coverage & Health candidate form/table/link/reject UI.
- Focused candidate API suite 11 passed. Full V2 suite **451 passed in 501.840s**, exit 0 (`lkscpl0ioe`).
- Compileall, JSON configs, diff check, HTML IDs/panels and dashboard JS workflow wiring passed. GitHub exact-head CI still needed after push.

## Next work

P0: commit/push candidate staging and verify CI; serialized Common Crawl CDX worker; sitemap/career-link candidate discovery; safe live verification; per-board scheduler/host budgets.

P1: Darwinbox blocked-state correctness; latency/429/completeness/first-seen benchmarks; stale/repost/legitimacy.

P2: more ATS connectors after discovery/scheduler contracts; Hirebase estimate-only only after explicit approval.

## User input

Nothing required now. Hirebase key absent. Workday/Keka/Darwinbox/Hirebase source flags remain false.
