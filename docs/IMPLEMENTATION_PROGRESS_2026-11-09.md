# JobBeeper implementation progress — 2026-11-09

## Start here

1. `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md` — exact current state, tests, CI and priorities.
2. `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md` — facet algorithm and bounded-state details.
3. `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md` — source repository findings.
4. `docs/ATS_PROVIDER_GAP_ANALYSIS_2026-11-09.md` — direct JobBeeper connector gaps.
5. `docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md` — completed Keka portal implementation.

## Completed in PR #65 before current uncommitted increment

- Optional Hirebase estimate-first sampler, disabled; key absent.
- LastRound AI CC BY 4.0 directory seed import (9,935 Greenhouse/Lever/Ashby candidates), candidate-only.
- Workday incremental inventory (commit 6197446; CI #1430 passed).
- Keka multi-portal URL/collector/verifier support (commit afa177b; CI #1431 passed).
- Detailed open-source research and handover.

## Current uncommitted Workday facet increment

- Persisted Workday facet queue, active filters and depth; migration-safe SQLite columns.
- Facet selection order: jobFamilyGroup → timeType → locations → workerSubType.
- Root/child 2,000-cap queries are subdivided across scheduled runs. One inventory page per board every 15 minutes; no concurrent fan-out.
- Depth cap 4; queue cap 500; unresolvable leaves/overflow remain incomplete.
- Admin API/UI show active filters, pending queue and incomplete-vs-terminal status.
- Focused Workday suite: 22 passed. Previous full V2 suite: 443 passed in 402.776s, but that full run predated the final extra status test. Final full suite job `3tjy6iwusp` is running; check `/tmp/job-radar-workday-facets-final-tests.log` before committing.

## Next work

P0: exact-head CI; reviewed Workday canary; company-agnostic public employer discovery for Workday/Keka/Darwinbox; per-board scheduler/host rate budgets.

P1: Darwinbox 403 handling; p50/p95, 429, completeness, first-seen latency; stale/repost/legitimacy signals.

P2: additional ATS adapters once scheduler/discovery contracts are stable; Hirebase estimate-only after explicit approval.

## User input

Nothing now. Hirebase key is absent. All four source flags remain disabled.

## Next company-agnostic discovery design (2026-11-09)

New design note: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Research confirms Common Crawl CDX is heavily rate-limited: serialize requests, no proxies, sleep between calls, and stop for 24 hours after an IP block/503. For broad/high-volume filtering, use the Parquet URL Index via Athena/Spark/Polars/DuckDB rather than frequent CDX wildcard sweeps. The next code step should create a separate unmatched ATS candidate table because current `ats_board_registry` requires a real company ID; do not manufacture employer identities from tenant slugs. Candidate URLs must preserve crawl provenance, be live-verified, and only then linked to the employer board registry.
