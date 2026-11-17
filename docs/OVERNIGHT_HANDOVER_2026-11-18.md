# JobBeeper release qualification handover — 18 November 2026

## Executive direction

The active execution plan is `docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md`. Keep work focused on the existing collectors, persistent ATS scheduler, feed quality and production release. Telegram/member notification work is explicitly out of scope. The Company Watch 100-row CSV remains a required follow-on deliverable, but its rows must remain review-only until the documented lifecycle is completed.

The owner explicitly authorized production promotion without another in-chat approval. This authorizes a controlled release after all documented gates pass; it does not waive CI, QA, backup, migration, rollback, allowlist or post-deploy checks. If any gate fails, stop before production mutation and document the blocker.

## Current verified state

### Code and CI

- Repository: `AvinashBhalla/job-beeper`.
- Application release head: `69a204a7349b67d6439e50e27f673834be4d4971` (`Reduce SmartRecruiters polling cost with cached detail lookups (#80)`). PR #80 is merged; V2 CI run #1522 passed on that exact SHA.
- Full V2 local regression suite: **507 tests passed, 0 failures** in 420.654 seconds. Focused Company Watch/global-discovery tests: 32 passed.
- Documentation PR #81 is merged as `472c2eef80bf34e0c87e9b1e65967181a7e698f5`; it adds the November 18 handover and updates `NEXT_AGENT_START_HERE.md`. Its exact-head CI run #1524 passed; prior doc commit run #1523 also passed.
- Current `v2-live-radar` HEAD is `472c2eef80bf34e0c87e9b1e65967181a7e698f5`. This is a documentation-only merge on top of application head `69a204a...`; no application code changed after the PR #80 CI head.

### Production and backup

- Production remains unchanged: container `v2-radar-1`, image `job-radar-prod-canary:6e5becb`, loopback port 8000; `/health` returned HTTP 200 after QA work.
- Fresh pre-release backup: `/var/backups/job-radar-daily/production-pre-release-20261118.sqlite3`, 135,303,168 bytes, mode `0600`, SQLite `integrity_check=ok`.
- Backup counts: 27,534 jobs, 2 users, 10 ATS registry boards, 51,920 source runs.
- SHA-256: `55b7402ad1a1fb3ebe871afee0c03008c1f7b5ecc25caf8689b399ff973b3e1c`.
- Production's explicit allowlist is unchanged: Greenhouse 3, Ashby 2, Workday 1, SmartRecruiters 1, Workable 1, Keka 1, Darwinbox 1. LinkedIn and Naukri remain enabled global fetchers; Instahyre and Lever remain disabled.

### Candidate QA image and migration

- Built `job-radar-v2-qa:472c2ee` from the merged V2 tree. Image ID: `sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c` (319,640,769 bytes).
- Replaced the old QA container on loopback port 8013 with `job-radar-current-v2-qa` running the new image. The prior `cc2087e` QA container is preserved, stopped and renamed `job-radar-pre-release-qa-cc2087e`; its original data directory remains untouched.
- Candidate QA uses its own data directory `/var/lib/job-radar-release-qa/data`, initialized from the verified production backup. It has no production config token or external credentials. All source flags and notifications are false. Runtime scheduler startup synchronized zero active boards as expected because all sources are disabled.
- Candidate `/health` returned HTTP 200; dashboard route returned HTTP 200; `/openapi.json` returned HTTP 200. Dashboard HTML contains search, source, score, age and sort controls plus Alertable Only and Remote Only toggles. Filter behavior is covered by the passing full V2 suite.
- Candidate DB `PRAGMA integrity_check=ok`. Existing row counts preserved exactly: jobs 27,534; users 2; ATS registry 10; source_runs 51,920. Schema comparison found no removed tables or columns. It added 11 tables and additive columns only: `jobs.experience_extraction_version`, `ats_board_registry.directory_last_crawled`, and eight source-run timing/latency columns.
- Candidate-container scheduler tests: 15 passed (scheduler state, baseline, orchestration). A separate disposable-DB allowlist simulation synced exactly 10 configured boards across seven ATS providers. Workday 429 cooldown escalated 5 → 10 minutes, while Ashby on another host remained claimable.
- Actual candidate-image scheduler dispatch smoke used only the existing Coinbase Greenhouse board and a throwaway SQLite DB: first poll 259 seen / 259 inserted, all first-inventory jobs baseline-suppressed; second poll 259 seen / 0 inserted. Both runs succeeded (1/1 board, 0 failures), duplicate source IDs 0, final SQLite integrity `ok`. Temporary DB files were removed. No source flags were enabled in the running QA or production app.
- A broader test-module invocation inside the production runtime image was not applicable because the image intentionally lacks the test-only `httpx2` package; the full 507-test suite passed in the dedicated test venv and exact-head CI. The 15 scheduler tests ran successfully inside the candidate image.

## Remaining release work

1. Review SmartRecruiters cache behavior in candidate QA specifically: listing pages must continue every poll, successful details must be reused for seven days, expired/missing details refreshed within the 20-detail-per-board cap, and `detail_attempts` / `detail_cache_hits` reported. Its unit tests are included in the passing full V2 suite; verify candidate runtime behavior/metrics without enabling shared QA or production sources.
2. Inspect current LinkedIn/Naukri/Workday source telemetry and Naukri relay timer/second-poll state. Keep the documented request budgets and existing 10-board allowlist.
3. Confirm release image digest and rollback image/config, review the exact production compose/runtime invocation, and ensure no hidden config drift. The fresh backup and additive migration compatibility check are complete.
4. If all checks pass, use the owner's standing authorization for a controlled production promotion. Preserve the current data volume and exact source allowlist; do not enable any additional Company Watch boards in the same rollout.
5. After promotion, verify health, filters, source status, per-board due times, ingestion, dedupe and feed freshness. Compare source metrics to the 17 November baseline. Observe for at least 24 hours before declaring reliability success.
6. After the core pipeline is reliable, import the 100-row Company Watch manifest into persistent V2 storage as review-only candidates. Current documented manifest: 90 enabled / 10 disabled; 19 direct ATS candidates stageable; 81 manual-review rows. Resolve canonical employer/board identities and verify provider endpoints before approving a limited allowlist. Never activate all 100 by default.
7. Update this file, `docs/NEXT_AGENT_START_HERE.md`, `docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md`, and `docs/PRODUCTION_READINESS_AND_RELEASE_PLAN_2026-11-17.md` after each release gate with exact evidence.

## Explicit non-goals

- Telegram linking, webhook, member alert delivery or notification redesign.
- Member-only feature expansion or admin/member parity.
- New notification channels or broad refactors.
- Running Company Watch as a second production pipeline or auto-activating the CSV.

## Continuation rule

Background test/build jobs are bounded processes, not an autonomous engineering agent. A new session must inspect actual GitHub, Termalin and runtime state before acting; never assume unattended implementation, monitoring or deployment continued after the prior response.
