# JobBeeper overnight handover — 18 November 2026

## Executive direction

Follow `docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md` as the active execution plan. Do not divert into Telegram, member-only enhancements, notification redesign, or unrelated refactoring.

The owner has explicitly authorized production promotion without waiting for another in-chat approval. This does **not** waive the documented engineering release gates: exact-head CI, isolated QA, verified backup, additive migration review, allowlist preservation, rollback readiness, and post-deployment health/ingestion checks remain mandatory. If a gate fails, stop before production mutation and document the blocker.

## Priority order

1. **P0 — Workday request control and persistent scheduler rollout.** Verify the 10-board production allowlist, scheduler sync, 5/10/20/40/60-minute per-board cooldown, Retry-After handling, host isolation, and no unreviewed board activation. Roll out only after QA and backup/migration gates.
2. **P1 — Existing fetcher reliability.** LinkedIn conservative pacing; Naukri relay freshness, failed-page investigation and relay-to-V2 idempotency; preserve request budgets.
3. **P1 — SmartRecruiters efficiency.** PR #80 is merged into `v2-live-radar` at `69a204a7349b67d6439e50e27f673834be4d4971`. Its post-merge V2 CI run #1522 passed on that exact SHA. Detail caching retains listing-page polling and refreshes cached details after seven days.
4. **P2 — Feed correctness.** Verify normalization, upsert, canonical dedupe, evaluation, filters and dashboard freshness on repeated polls.
5. **Company Watch CSV.** The pinned 100-row CSV and review-only import are already in V2 source (PR #76). The documented manifest has 90 enabled / 10 disabled rows; 19 ATS candidates are stageable and 81 remain manual-review only. Do not infer approval from CSV `scan_enabled` or `verified_ats_board`. Import to persistent runtime and verify/activate only after core pipeline gates and documented review. Never activate all 100 by default.

## Current verified state at handover

- Repository: `AvinashBhalla/job-beeper`.
- V2 branch HEAD: `69a204a7349b67d6439e50e27f673834be4d4971` (`Reduce SmartRecruiters polling cost with cached detail lookups (#80)`).
- PR #80 was merged; GitHub Actions V2 CI run #1522 on the exact V2 HEAD completed successfully.
- A clean working branch `feat/fetcher-feed-reliability-20261118` is based on V2 HEAD. No application code changes have been made on it yet.
- Focused Company Watch + global-discovery regression tests: 32 passed, 0 failed (local Python 3.12 venv `/tmp/jb-v2-venv-20261118`).
- Full V2 regression suite is running as Termalin background job `b09ohct2xx` on host `f5d22bb1-3948-45a2-836a-5d47c34efaf7`. Check with `job_status` before starting another full suite.
- Production container: `v2-radar-1`, image `job-radar-prod-canary:6e5becb`, loopback port 8000; last read-only `/health` returned HTTP 200. This image predates the persistent V2 board scheduler and does not contain `v2.board_scheduler` / `ats_board_poll_schedule`.
- Current QA container: `job-radar-current-v2-qa`, image `job-radar-v2-qa:cc2087e`, loopback port 8013; last read-only `/health` returned HTTP 200. It contains scheduler code but predates merged PR #80. Its persistent data is isolated at `/var/lib/job-radar-current-v2-qa/data`.
- Production has 10 explicitly active ATS boards (Greenhouse 3, Ashby 2, Workday 1, SmartRecruiters 1, Workable 1, Keka 1, Darwinbox 1), plus global LinkedIn and Naukri fetchers. Do not expand this allowlist during scheduler rollout.
- The 17 November production snapshot is documented in the reliability plan and passed SQLite integrity check; it is not a substitute for a fresh pre-release backup on 18 November.
- Host resources are constrained: 956 MiB RAM total, approximately 327 MiB available at last check, 2 GiB swap with about 763 MiB used. Disk was 30% used. Avoid parallel image builds or heavy test jobs; preserve production headroom.

## Immediate next actions

1. Check background job `b09ohct2xx`; record full-suite pass/fail and test count. Do not assume it passed while running.
2. Review the exact V2 diff since the production image commit, focusing on scheduler/migration compatibility, source config defaults and filter behavior. Keep `main` separate from `v2-live-radar`; production currently runs the V2 line, not `main`.
3. Re-check host resources before building. Build a fresh candidate from exact V2 HEAD only if resource headroom is safe. Do not rebuild/restart the existing QA or production container in place.
4. Use a separate QA container, isolated DB copy and source-disabled config. Confirm 10-board sync, Workday cooldown and host isolation, then scheduled dispatch and second-poll idempotency. Existing 17 November evidence covers the 10-board sync, simulated 5/10-minute cooldown and two-poll Coinbase Greenhouse dispatch; extend only where new code requires it.
5. Inspect PR #80's merged SmartRecruiters cache behavior in QA. Confirm listing calls continue every poll, cached details are reused within seven days, expired/missing details refresh within the existing cap, and source metrics expose attempts/cache hits.
6. Capture a fresh consistent production DB backup, verify checksum and `PRAGMA integrity_check`, review additive migration against a disposable copy, and record image digest plus rollback image/config.
7. Only after all gates pass, execute a controlled production update preserving the exact 10-board allowlist, LinkedIn/Naukri settings and user data. Do not change notification settings or enable additional Company Watch boards as part of this rollout.
8. Verify `/health`, dashboard filters/preferences, source status, per-board due times, ingestion/dedupe and feed freshness. Compare source metrics to the 17 November baseline; Workday 429s should materially fall. Keep monitoring at least 24 hours before declaring release success.
9. After core feed reliability is established, continue the Company Watch documented lifecycle: persistent manifest import → candidate review → canonical employer/board mapping → provider endpoint verification → explicit limited allowlist → QA scheduler/baseline/second-poll proof → later phases. Keep all other CSV rows review-only until individually validated.
10. Update this handover, `docs/NEXT_AGENT_START_HERE.md`, and `docs/PRODUCTION_READINESS_AND_RELEASE_PLAN_2026-11-17.md` after each meaningful gate. Record exact commits, CI run IDs, image digests, backup checksums, test counts and observed source metrics.

## Explicit non-goals for this increment

- Telegram linking, webhook or alert-delivery work.
- Member-only feature expansion or admin/member parity.
- New notification channels.
- Activating all 100 CSV rows or running Company Watch as a second production pipeline.
- Broad refactors, new providers, or unrelated UI work.

## Continuation rule

The Termalin job above is a bounded background test process, not an autonomous six-to-seven-hour engineering agent. A new agent/session must resume from this file and the active reliability plan, inspect actual job/CI/runtime state, and never assume unattended implementation, deployment or monitoring continued after the previous session ended.
