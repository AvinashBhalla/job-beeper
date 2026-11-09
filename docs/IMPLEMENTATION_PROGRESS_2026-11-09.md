# JobBeeper implementation progress — 2026-11-09

## Start here

1. docs/RECOVERY_CHECKPOINT_2026-11-09_1937_IST.md — latest complete state, tests, release boundary, priorities and user actions.
2. docs/WORKDAY_INCREMENTAL_INVENTORY_2026-11-09.md — Workday design and acceptance notes.
3. docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md — immediate next connector task.
4. docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md — repository research.
5. docs/ATS_PROVIDER_GAP_ANALYSIS_2026-11-09.md — actual JobBeeper collector gaps.

## Current milestone

Workday incremental inventory code, tests and admin progress UI are implemented locally. Full V2 regression passed 436/436 in 398.870s. Focused Workday/global discovery tests passed 31/31. The Workday code is locally tested and ready to commit/push on the current branch; verify exact-head GitHub CI before extending it. PR #65 remains draft and unmerged.

## Next milestones

P0: Workday facet-aware inventory; Keka non-default portal resolution; company-agnostic public Workday/Keka/Darwinbox employer discovery; per-board scheduler with host rate budgets.

P1: Darwinbox blocked-state correctness; p50/p95, 429, completeness and first-seen latency benchmarks; stale/repost detection.

P2: more ATS connectors after discovery/scheduling contracts, then optional Hirebase estimate-only dev test with user approval.

## User input needed

Nothing right now. Do not request the Hirebase key in chat. It remains absent and all four related source flags remain off.

## Current continuation — 2026-11-09 19:47 IST

- Workday incremental inventory + admin progress UI: pushed as `6197446`; exact-head GitHub V2 CI #1430 passed; local full V2 suite 436 passed.
- Keka portal resolver/collector/verifier: implemented in current worktree. Default portal remains compatible; non-default portal slug is part of board/job identity; same-tenant multiple portals supported; unsafe URLs rejected; portal-specific endpoint used by collector and verifier.
- Keka focused board-discovery suite: 37 passed. Full V2 regression: **439 passed in 359.301s**, exit code 0.
- Keka changes remain uncommitted/unpushed. Next: commit/push same PR #65 branch, update PR body, verify exact-head CI. Do not merge/deploy; PR remains draft.
- Next P0 after Keka CI: Workday facet-aware inventory, global public employer discovery for Workday/Keka/Darwinbox, persistent per-board scheduling/host budgets.
- User action: none. Do not request Hirebase key in chat; it remains absent and all sources remain disabled.
