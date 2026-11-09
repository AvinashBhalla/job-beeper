# JobBeeper implementation progress — 2026-11-09

## Start here

1. `docs/RECOVERY_CHECKPOINT_2026-11-09_2209_IST.md` — latest verified state, live feed deployments, metrics, user action and next priorities.
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

## Candidate staging pushed and CI-passed

- PR #65 head `243da9c35e93979e59d0de281130581cad4124d1`, exact-head CI #1437 passed.
- Full local V2 suite 451 passed in 482.864s; focused candidate API 11 passed.
- Candidate code is deployed to shared dev 8001 and connector QA 8010 on identical image SHA; eight live sources on both, LinkedIn off, all notification/LLM credentials blank.
- Dev: 10,259 jobs / 8,221 runs / integrity OK / zero sends after multiple cycles. QA: 1,864 jobs / 8 successful runs / integrity OK / zero sends after first cycle.
- Complete operating plan and backup hashes: `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md`.

## Current remaining work

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

## User input / next handoff

Owner to provision QA-only admin/member using interactive `v2.auth_admin` CLI and perform dev/QA UAT. No Hirebase key needed; Workday/Keka/Darwinbox are now enabled only in isolated non-production canaries, Hirebase remains disabled. Production unchanged; separate approval required.
