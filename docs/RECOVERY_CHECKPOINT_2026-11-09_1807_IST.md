
## 2026-11-09 18:07 IST — recovery checkpoint after ChatGPT connection interruption

The user reported the conversation UI stuck on “Connection interrupted. Waiting for the complete answer” and supplied a screenshot. This is a ChatGPT response-stream interruption, not evidence of a JobBeeper application outage. The screenshot shows the prior answer did not finish rendering. The implementation and documentation are on the development VM; do not repeat work blindly.

### Current working state

- Repository/worktree: /tmp/job-radar-global-discovery
- Branch: feat/global-ats-discovery-hirebase-guard-20261109
- Base: origin/v2-live-radar at ecb347aef013e5249ce1270006d3bc226e111c3e
- Not pushed, no PR created, no merge or deployment.
- Files already modified/new: see git status --short --branch on the VM. git diff --check had passed before the latest watermark changes; rerun it.
- Docs already added:
  - docs/GLOBAL_ATS_DISCOVERY_IMPLEMENTATION_2026-11-09.md
  - docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md
  - v2/data/LASTROUND_AI_ATTRIBUTION.md
  - appendices in docs/NEXT_AGENT_START_HERE.md, docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md, docs/PRODUCT_VISION_AND_DELIVERY_ROADMAP.md
- User explicitly asked that findings and next steps be documented first. This checkpoint is appended to the three primary handover docs before any further implementation work.

### Last known test state — important distinction

- Before incremental cursor work and the final dashboard tweaks, a complete V2 regression run passed 426 tests in 416.2 seconds.
- The focused Hirebase/directory suite now passes 30 tests, including incremental query construction, per-provider pagination cursor state, zero-estimate advancement and candidate-only import.
- After Free-plan period handling, the Hirebase client-only suite passed 12 tests.
- A full suite job ipu4poub1j was started at 12:23 UTC but was stopped after the user interruption and subsequent code changes made its run stale. Its log /tmp/job-radar-global-discovery-final-tests.log is not a final exact-HEAD result.
- Therefore the current branch has no final test result yet. Do not claim 426 tests validates current HEAD. Rerun focused tests, then the complete V2 suite after watermark/pagination work is settled.

### Latest implementation changes since the previous handover

Hirebase incremental ingestion is now being changed to avoid repeatedly spending credits on the same rolling seven-day results:

- First run uses a bounded seven-day sample.
- Later runs use Hirebase ingested_after with sort_by=first_ingested, ascending, and a two-hour overlap.
- New hirebase_provider_state stores per-provider cursor/pagination state.
- Cursor commits are deferred until run_source has successfully upserted the jobs, to avoid advancing the cursor when DB ingestion fails.
- The schema currently includes last_polled_at, window_start, and next_page; the latest code has evolved beyond the first simple watermark patch to support paginated continuation. Inspect current code before editing; don't overwrite it with the older design.
- Current helper functions are around v2/radar.py:5687-5715; collector around v2/radar.py:5752-5881; run-source commit around v2/radar.py:5970.
- v2/hirebase.py:49-72 constructs first-run vs incremental query. normalize_provider_job retains first_ingested.
- The test test_provider_query_uses_incremental_first_ingested_cursor was added to v2/test_hirebase.py, but it may not have landed inside the test class correctly. Inspect tail -50 v2/test_hirebase.py and fix if necessary.
- Need add tests for per-provider watermark persistence, two-hour overlap, page continuation when estimated results exceed the limit, commit only after upsert, and no cursor advance on search/DB failure. Keep the result limit at or below the zero-credit estimate.
- Be careful: the previous test launch ran before the current cursor/pagination implementation. It is stale and must not be relied on.

### Safety / Hirebase status

- Hirebase source remains disabled by default; 24-hour schedule.
- No Hirebase API key has been supplied or read. The dedicated dev secret file /home/ubuntu/.config/job-beeper/dev-hirebase.env was created empty with mode 600 under a mode-700 directory. Existing shared .env untouched.
- No Hirebase API estimate/search requests have been made.
- Free plan usage API has null subscription and period dates. Code now falls back to the calendar month in UTC while requiring valid meter counters. Hirebase client test passed after this change.
- Per-query result cap must remain no larger than its estimate. Local guardrails: 400/month, 12/day overall, 4/day/provider.
- Hirebase Terms restrict competing job-data products and raw redistribution. Do not enable for commercial multi-user JobBeeper production without written permission. The UI requires explicit confirmation before enabling and estimate buttons remain disabled without a key.

### Candidate discovery status

- LastRound AI August 2026 CSV snapshot is CC BY 4.0 and has exactly 9,935 rows: 4,966 Greenhouse, 2,856 Ashby, 2,113 Lever.
- Import creates low-confidence, unverified candidates only; does not activate or poll boards. Reuses existing provider/slug rows.
- Snapshot is dated; verify endpoints before activation. No total market coverage percentage is claimed.
- This still does not deliver autonomous employer/tenant discovery for Workday/Keka/Darwinbox. Hirebase is only a tiny India-focused sample for those providers.

### Immediate next steps (do these in order)

1. Inspect/fix v2/test_hirebase.py method placement and review the current incremental cursor/pagination code.
2. Add focused tests for cursor persistence/commit semantics and pagination. Ensure estimate-first and hard caps are intact.
3. Run focused Hirebase/directory tests and git diff --check, compile Python, validate JSON and Compose.
4. Run the full V2 suite at exact final HEAD. If long-running, use a background job and poll until completed; do not abandon it.
5. Validate dashboard JS using GitHub Actions/modern Node. VM Node 12 cannot parse existing optional chaining/nullish-coalescing syntax; do not rewrite unrelated JS to satisfy that old runtime.
6. Update the implementation note and all three handovers with exact final test count, commit SHA, CI run and any remaining blockers.
7. Only then push branch and create/update a draft PR. No deployment, no Hirebase activation, no key setup or live source enablement without explicit user approval.
8. Future P0 after this branch: implement first-party global Workday/Keka/Darwinbox company/tenant discovery and a verified-board-to-scheduler pipeline. Use Freehire's provider-isolated workers/outboxes, Career-Ops reverse discovery/per-host concurrency, and ats-scrapers fetcher contracts as architecture references. Do not reuse CC BY-NC company datasets from Career-Ops/Riley aggregator commercially.

### Open-source shortlist

See docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md for details. Leading references: Freehire (ingestion architecture), Career-Ops (reverse discovery and per-host concurrency; dataset is CC BY-NC), ats-scrapers (Python adapters), Job Board Aggregator (Common Crawl and anomaly monitoring; bundled dataset CC BY-NC), JobSpy (non-ATS board adapters), JobNavigator (product UX). Stars are popularity, not latency/rate-limit proof.

## PR and commit checkpoint — 2026-11-09 18:50 IST

- Commit: 533c889574bb6daddece8121c66f208c6fcec8de (`feat: add guarded global ATS discovery foundation`).
- Branch pushed: `feat/global-ats-discovery-hirebase-guard-20261109`.
- Draft PR: https://github.com/AvinashBhalla/job-beeper/pull/65 (base `v2-live-radar`).
- Full V2 regression: 430 tests passed in 385.001 seconds; background job `bjo6lrjfig` exit code 0. Focused discovery/Hirebase suite: 30 passed. Python compile, JSON, Compose config and diff checks passed.
- GitHub connector returned no PR-triggered workflow runs for this SHA at the time of handover; verify checks on PR #65 before review/merge.
- PR remains draft/open, unmerged. No deployment or Hirebase requests/activation.
