# JobBeeper production release handover — 18 November 2026

## Release outcome

**V2 is deployed to production and the 100-company Company Watch manifest is imported persistently as review-only data.** Production was promoted to `job-radar-prod-release:472c2ee`; health, dashboard and OpenAPI return HTTP 200. The persistent scheduler synchronized exactly the existing 10 ATS boards. No additional Company Watch boards were activated or scheduled.

The owner explicitly authorized production promotion without another in-chat approval. The documented gates were completed before promotion: exact-head CI, full regression, isolated QA, fresh verified backup, additive migration review, preserved allowlist, and rollback image/config readiness. Continue post-deploy monitoring; do not call the release fully reliability-accepted until at least 24 hours of source telemetry has been reviewed.

## Verified code and CI

- Application code head: `69a204a7349b67d6439e50e27f673834be4d4971` (PR #80 SmartRecruiters detail cache), exact-head V2 CI #1522 passed.
- Full V2 regression suite: **507 passed, 0 failed** in 420.654 seconds. Focused Company Watch/global-discovery tests: 32 passed.
- Documentation PR #81 merged as `472c2eef80bf34e0c87e9b1e65967181a7e698f5`; PR #82 merged as `ed7c4c4ff258df6b6edd239b5eccce01976cbe8`. Both documentation PR exact-head CI runs passed.
- Production image was built from the reviewed application tree and tagged `job-radar-prod-release:472c2ee`. Image ID: `sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c`.

## Backup, compose and rollback evidence

- Final pre-deploy backup: `/var/backups/job-radar-daily/production-before-v2-release-20261118T2058Z.sqlite3`.
- Backup size 135,368,704 bytes; mode `0600`; `PRAGMA integrity_check=ok`.
- Backup counts: 27,546 jobs, 2 users, 10 active ATS registry boards, 51,984 source runs.
- Backup SHA-256: `6c8fa1f139ea05a081c0f65fefc84540f9d9600febe59f57b71b3a1a0bd9da15`.
- Original production compose copied to `/var/backups/job-radar-daily/production-compose-before-release-20261118.yml`, mode `0600`, SHA-256 `d9e695f6a4c0299b3bdae4d0ce8817fdfa21e31e301c6d6b93cb189201a21917`.
- Release compose `/tmp/job-radar-prod-release-compose-20261118.yml` was validated with `docker compose config --quiet`; diff from original compose was only the image tag. It retains the same env file, localhost port 8000, external `v2_radar-data` volume and restart policy.
- Previous production image `job-radar-prod-canary:6e5becb` and named rollback image `job-radar-production-rollback:20261108` remain available. The existing production data volume was reused; no DB restore or data replacement occurred.

## Production deployment and initial checks

- Container: `v2-radar-1`, image `job-radar-prod-release:472c2ee`, image ID above, started `2026-11-17T20:59:46Z`.
- `/health` HTTP 200; `/dashboard/` HTTP 200; `/openapi.json` HTTP 200.
- Dashboard contains search, source, score, age and sort filters, plus Alertable Only and Remote Only toggles. Filter behavior is covered by the passing full V2 suite.
- Startup synchronized **10 active ATS schedules**. Configured board keys matched the 10 active/available registry rows exactly: 3 Greenhouse, 2 Ashby, 1 Workday, 1 SmartRecruiters, 1 Workable, 1 Keka, 1 Darwinbox. Instahyre and Lever remain disabled. LinkedIn and Naukri remain enabled global fetchers.
- First scheduled pass: 9/10 boards succeeded. All successful first inventories were baseline-suppressed; no old jobs were treated as new. Workday returned HTTP 429 and the scheduler recorded a 5-minute host cooldown with consecutive failure count 1. Its next due time was `2026-11-17T21:06:27.910416+00:00`. Other hosts continued independently.
- Naukri relay systemd timer remains enabled at five-minute cadence. Relay workflow #9874 completed successfully. Post-deploy V2 Naukri run accepted 313 jobs and completed successfully with 0 new rows and 0 failed pages.
- LinkedIn's first post-deploy global scan succeeded (40 observed, 10 new, no failed requests). The pre-existing global notification configuration was left unchanged; one legacy notification was delivered for this LinkedIn run. No Telegram feature, webhook or notification configuration was changed as part of this release.
- SmartRecruiters first production poll saw 300 postings, reused 20 cached detail records and fetched 20 not-yet-cached details (23 requests total including three listing pages). Candidate QA warm-cache simulation confirmed the steady-state path: 300 cache hits, zero detail requests, three listing-page requests, zero new jobs. Cache warm-up is incremental under the 20-detail-per-board cap; do not claim steady-state savings from the first production poll alone.

## Company Watch 100-row manifest — production import complete

- Pinned manifest SHA-256: `706ea1d6204cd80379aa57d8dd2b041f5c3f1f7af6666c7140c2c216ce2049bd`.
- Source reference: `main@29cbb17190b26829d49e1458137d75f2e8f286aa`.
- Dry run validated 100 rows: 19 `candidate_staged`, 81 `manual_review`, 0 invalid.
- Production import inserted 19 ATS discovery candidates and 100 manifest row records. Candidate status is `discovered` (review-only).
- Import created 0 company records, linked 0 boards, verified 0, activated 0, scheduled 0, made 0 network requests and sent 0 notifications.
- Production still has exactly 10 active ATS registry boards and 10 active schedules. The manifest did not alter source flags or configured board arrays.
- SQLite integrity check after import: `ok`. Importer tests passed 9/9 in candidate image; isolated throwaway-DB dry-run/import/re-import proved idempotency (first import 19 inserts, second import 0 inserts).

## Immediate monitoring and remaining work

1. Confirm Workday did not retry before its persisted five-minute cooldown expired; record the next result. If it receives another 429, confirm the next cooldown escalates to 10 minutes and no unrelated host pauses.
2. Observe SmartRecruiters across subsequent polls. Cache hits should grow as each poll hydrates up to 20 previously uncached details; listing pages must continue every poll. Track `detail_attempts`, `detail_cache_hits`, requests and 429s.
3. Compare Workday, LinkedIn, Naukri, SmartRecruiters and all ATS source metrics against the 17 November 24-hour baseline. Workday was the critical issue before release; it is not fixed merely because the scheduler is deployed.
4. Check source freshness, dashboard feed and dedupe after subsequent polls. Verify no duplicate source IDs and that newly discovered jobs are evaluated as expected after the first silent baseline.
5. Keep the 19 Company Watch candidates review-only. Resolve canonical employer/board identity and verify provider endpoints before approving any limited allowlist. Keep all 81 manual-review rows held. Never activate all 100.
6. Update this file, `docs/NEXT_AGENT_START_HERE.md`, the active reliability plan and production readiness plan with exact cooldown observations and 24-hour metrics.

## Explicit non-goals

No Telegram linking/webhooks/member-alert work, notification redesign, member-only feature expansion, new providers, broad refactors or Company Watch activation were part of this release. The one legacy notification described above came from the existing unchanged global notification path.
