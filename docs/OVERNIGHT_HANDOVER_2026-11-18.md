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

## Post-deploy observation — 21:17 UTC

- Workday attempts after deployment: `21:01:26`, `21:06:34`, `21:16:37` UTC. Each made exactly one request and received one HTTP 429 / one failed page. The scheduler applied progressive host cooldowns of 5, 10 and 20 minutes; next due is `2026-11-17T21:36:38.680292+00:00`. No premature retries occurred. Other hosts continued polling during Workday cooldown; 29 non-Workday source runs completed after the second Workday 429 and before the 10-minute observation checkpoint.
- Correctly bounded post-deploy observation window (`started_at >= 2026-11-17T20:59:46`, through about 21:08 UTC): Ashby 4 runs / 4 requests / 0 429 / 0 failed pages; Darwinbox 4 / 4 / 0 / 0; Greenhouse 6 / 6 / 0 / 0; Keka 4 / 8 / 0 / 0; LinkedIn 3 / 28 / 0 / 0 (70 seen, 10 new); Naukri 2 / 2 / 0 / 0 (626 seen); SmartRecruiters 2 / 46 / 0 / 0 (600 seen); Workable 4 / 4 / 0 / 0; Workday 2 / 2 / 2 / 2 (0 jobs). No duplicate source IDs; production DB quick check `ok`.
- Naukri relay workflow #9878 succeeded; the post-deploy V2 collector accepted 317 jobs, 0 new and 0 failed pages. The five-minute systemd timer remains enabled.
- SmartRecruiters production polls progressed through 20, 40 and 60 cached detail hits while attempting up to 20 uncached details per poll. Each poll retained its three listing requests. Candidate warm-cache simulation showed the steady state: 300 hits, 0 detail attempts, 3 listing requests. Allow cache to warm; do not claim steady-state savings yet.
- Production dashboard OpenAPI exposes `q`, `search`, `source`, `min_score`, `max_age_hours`, `sort`, `sort_by`, `sort_order`, `alertable_only` and `remote_only`. Dashboard and OpenAPI return HTTP 200. Production jobs count is 27,556; duplicate `(source, source_job_id)` groups are 0; the 10 new post-release rows are LinkedIn jobs.
- Company Watch review breakdown: 19 staged candidates comprise Greenhouse 10, Lever 6, SmartRecruiters 3. The 81 manual-review rows comprise 71 generic careers pages requiring discovery, 8 disabled/manual/employer-identity confirmation, and 2 additional mixed cases involving board-type/scan-mode mismatch. Four rows carry a CSV `verified_ats_board` label and 15 carry `provided_url_needs_live_validation`; neither label is equivalent to V2 live verification or activation. Keep all 19 candidates and 81 rows review-only.

## Immediate monitoring and remaining work

1. Confirm Workday did not retry before its persisted five-minute cooldown expired; record the next result. If it receives another 429, confirm the next cooldown escalates to 10 minutes and no unrelated host pauses.
2. Observe SmartRecruiters across subsequent polls. Cache hits should grow as each poll hydrates up to 20 previously uncached details; listing pages must continue every poll. Track `detail_attempts`, `detail_cache_hits`, requests and 429s.
3. Compare Workday, LinkedIn, Naukri, SmartRecruiters and all ATS source metrics against the 17 November 24-hour baseline. Workday was the critical issue before release; it is not fixed merely because the scheduler is deployed.
4. Check source freshness, dashboard feed and dedupe after subsequent polls. Verify no duplicate source IDs and that newly discovered jobs are evaluated as expected after the first silent baseline.
5. Keep the 19 Company Watch candidates review-only. Resolve canonical employer/board identity and verify provider endpoints before approving any limited allowlist. Keep all 81 manual-review rows held. Never activate all 100.
6. Update this file, `docs/NEXT_AGENT_START_HERE.md`, the active reliability plan and production readiness plan with exact cooldown observations and 24-hour metrics.

## 18 November 2026 — morning production observation (03:50 UTC)

Observation window: production deployment at `2026-11-17T20:59:46Z` through `2026-11-18T03:50:39Z` (about 6h51m). This is an early post-release window, not a completed 24-hour acceptance period.

### Live source metrics since deployment

| Source | Runs | Requests | HTTP 429 | Failed pages | Jobs seen | New rows |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 159 | 159 | 0 | 0 | 66,865 | 5 |
| Darwinbox | 201 | 201 | 0 | 0 | 7,839 | 0 |
| Greenhouse | 243 | 243 | 0 | 0 | 27,964 | 2 |
| Keka | 198 | 396 | 0 | 0 | 22,968 | 0 |
| LinkedIn | 88 | 525 | 2 | 1 | 1,163 | 93 |
| Naukri | 82 | 82 | 0 | 0 | 25,949 | 2 |
| SmartRecruiters | 80 | 530 | 0 | 0 | 24,000 | 13 |
| Workable | 202 | 202 | 0 | 0 | 1,212 | 0 |
| Workday | 10 | 10 | 10 | 10 | 0 | 0 |

`jobs_seen` is an observation count across polls, not unique vacancies. `new rows` counts inserted records, not necessarily unique active vacancies.

### Reliability interpretation

- **Workday:** 10 requests in 6h51m, all HTTP 429, one request per due attempt, no jobs returned. The old baseline was 4,894 requests and 417 HTTP 429 in 24h. At the current capped hourly cadence, the observed request rate annualizes to roughly 35 requests/day, about 99.3% below the old 24-hour request count. This is a request-storm reduction, not a source recovery. The scheduler has reached its 60-minute cooldown cap; latest failure streak 10, next due `2026-11-18T04:16:55.329405Z`.
- **LinkedIn:** 525 requests, 2 HTTP 429, 1 failed page and 93 new rows. Latest partial-rate-limited run at `02:40:43Z` triggered a persisted 9,600-second (160-minute) global cooldown after the sixth consecutive 429 in the persisted history. No LinkedIn requests should resume before the cooldown expires (approximately `05:20:43Z`). Keep the breaker intact; do not reset it manually. Earlier scans before the 429 continued returning results.
- **SmartRecruiters:** 80 polls / 530 requests / 24,000 seen / 13 new / 0 failed pages. The 7-hour average is 6.6 requests per poll versus the old 23-request pattern (3 listing + 20 detail calls), approximately 71% fewer requests at the observed poll count. Most recent poll used 3 listing requests, 300 detail-cache hits and 0 detail attempts. This confirms the cache is now warm and listings continue to refresh.
- **Naukri:** 82 successful relay ingestions, 82 requests, 25,949 seen, 2 new rows, no 429 or failed pages. Five-minute systemd relay timer is active.
- **ATS peers:** Greenhouse, Ashby, Keka, Darwinbox and Workable have zero 429s and zero failed pages in this window. One Ashby board poll had a transient `ConnectionError` at `02:52:28Z`; subsequent polls succeeded.
- **Database/feed:** 27,661 job rows, 115 rows inserted since release, zero duplicate `(source, source_job_id)` groups, `PRAGMA quick_check=ok`. There are still exactly 10 active ATS registry boards and 10 active schedules. One schedule remains `baseline_pending` (Workday); the other nine are past baseline.
- **Host:** latest sample at `03:49Z`: CPU 5.1%, memory 67.1%, disk 30.6%, load1 0.07, no OOM kills. Twelve-hour average CPU 14.7%, peak 90%; memory average 64.8%, peak 77.1%; disk average 29.7%. No resource-driven reason to alter the release.

### Company Watch candidate endpoint verification (read-only)

Nineteen direct ATS candidates were checked with one read-only public provider API request each (no production DB changes, no linking, no activation, no scheduled polling):

- 17 endpoints returned HTTP 200 with a valid provider response: Greenhouse 9/10, Lever 5/6, SmartRecruiters 3/3.
- Two CSV-derived provider slugs returned 404: Lever `mistral` and Greenhouse `soundhoundinc`.
- The Mistral official careers page links to `jobs.ashbyhq.com/mistral.ai`; the Ashby public posting API returned HTTP 200 and 254 jobs. This is a well-supported replacement candidate, but it has not been written to production or linked to a company record.
- SoundHound's official careers page is live, but the failed Greenhouse slug is not valid. The page's rendered content did not expose a verifiable replacement provider slug. Keep it for manual review.
- All 19 existing manifest candidates remain `discovered`/low confidence; 81 other manifest rows remain manual review. API endpoint response alone does not prove canonical employer identity, so no candidate is promoted to verified/active.

Official source references checked: `https://mistral.ai/careers/` (Apply now links to `https://jobs.ashbyhq.com/mistral.ai`) and `https://www.soundhound.com/careers/`.

### Next actions

1. Keep Workday at the 60-minute cap and verify the next attempt only when due; do not send manual probes while it is throttled.
2. Let LinkedIn's persisted 160-minute cooldown expire naturally. Inspect the first post-cooldown request count/result and retain conservative pacing. If it 429s again, allow the exponential breaker to escalate; do not bypass it.
3. Correct the Mistral candidate through the supported global-candidate import workflow after review of the official Ashby source; reject or retain the stale Lever slug as rejected/manual review. Do not create/activate an employer board until the company mapping is approved.
4. Keep SoundHound manual until its actual ATS provider and board key are confirmed from official source evidence.
5. Continue the 24-hour source comparison before marking the release reliability-accepted. Recheck source freshness, user feed, canonical dedupe and notification decisions; preserve the current 10-board allowlist.

## Explicit non-goals

No Telegram linking/webhooks/member-alert work, notification redesign, member-only feature expansion, new providers, broad refactors or Company Watch activation were part of this release. The one legacy notification described above came from the existing unchanged global notification path.
