# JobBeeper implementation progress — 2026-11-09

## Start here

1. `docs/RECOVERY_CHECKPOINT_2026-11-09_2035_IST.md` — latest verified branch/PR/CI state, safety boundaries and prioritized next actions.
2. `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md` — next engineering design for unmatched ATS candidates and Common Crawl.
3. `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md` — Workday facet algorithm, limits and completeness semantics.
4. `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md` — code-level repo research.
5. `docs/ATS_PROVIDER_GAP_ANALYSIS_2026-11-09.md` — mapping to current JobBeeper collectors.

## Completed and verified in PR #65

- Optional Hirebase quota-guarded dev sampler; no key/API calls; disabled.
- Attributed LastRound AI CC BY 4.0 directory; review-only Greenhouse/Lever/Ashby candidate seeds.
- Workday incremental page cursor/status UI and facet-aware bounded inventory (depth 4, queue 500, 15-minute extra-page interval).
- Keka default/non-default portal resolver, collector and verifier.
- Common Crawl research and candidate-staging design.

## Current validation

- Full V2 local suite: 444 passed in 346.385s.
- Focused Workday collector suite: 22 passed.
- Exact-head GitHub V2 CI #1435 passed on `4d7513803031d1c32c02a19ac8452dfb221c02ad` (Python compile, dashboard JS syntax, focused tests, full suite).
- Worktree was clean after commit and push; documentation checkpoint is the only new follow-up change.

## Next work

P0: unmatched ATS candidate staging table and admin review/link workflow; polite Common Crawl candidate discovery; public live verification; persistent per-board scheduler and host rate budgets.

P1: Darwinbox blocked-state correctness; latency/429/inventory-completeness benchmarks; stale/repost/legitimacy signals.

P2: additional ATS connectors after discovery/scheduling contract stable; Hirebase estimate-only experiment after explicit approval.

## User input

Nothing required now. Do not request Hirebase key in chat; it is absent. All ATS/Hirebase source flags remain off.
