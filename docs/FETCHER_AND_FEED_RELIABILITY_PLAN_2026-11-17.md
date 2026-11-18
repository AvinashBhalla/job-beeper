# JobBeeper — Fetcher and Feed Reliability Plan

**Status:** active priority, 17 November 2026, 18:11 UTC
**Branch:** v2-live-radar (latest observed head before this work: 3d057335bf5a69f7ffc3f63903d1075b8253b798)
**Production:** job-radar-prod-canary:6e5becb, port 8000
**QA candidate:** job-radar-v2-qa:cc2087e, port 8013

## Direction reset

The immediate goal is a **reliable, fresh, deduplicated job feed**. Prioritize source collectors, ATS board polling, source health, normalization, canonical deduplication, matching and dashboard freshness.

Telegram is **optional**. It is not required to use JobBeeper, log in, set preferences, collect jobs, evaluate jobs or view the dashboard. A user links Telegram only when they choose Telegram as an alert-delivery channel; they must then opt in to those alerts. Telegram linking, webhook setup and member notification enhancements are not blockers for the core fetcher/feed work and must not be treated as production-readiness prerequisites for dashboard access.

The existing member account can be used to verify that the dashboard feed is populated, but do not expand member-only functionality, per-user notification workflows or admin/member parity during this reliability increment. Company Watch/manifest expansion is also secondary until current collectors and the production scheduler are reliable.

## Current production evidence

Read-only production source_runs rollup for the 24-hour window ending approximately 17 November 2026, 18:11 UTC:

| Source | Runs | Requests | HTTP 429 | Failed pages | Jobs seen | New jobs | Assessment |
|---|---:|---:|---:|---:|---:|---:|---|
| Workday | 627 | 4,894 | 417 | 362 | 4,211 | 33 | **Critical: repeated throttling and page failures** |
| LinkedIn | 267 | 1,566 | 12 | 4 | 3,123 | 449 | Active, but occasional rate limiting |
| Naukri | 503 | 503 | 0 | 2 | 151,841 | 706 | High contribution; inspect the two failed pages |
| SmartRecruiters | 504 | 11,592 | 0 | 0 | 151,178 | 251 | Successful, but request volume deserves profiling |
| Greenhouse | 504 | 1,512 | 0 | 0 | 175,878 | 11 | Stable; confirm low new-job count is normal |
| Ashby | 502 | 1,004 | 0 | 0 | 425,366 | 26 | Stable |
| Workable | 1,245 | 1,245 | 0 | 1 | 7,464 | 0 | Stable polling; inspect the single failure and zero-new period |
| Keka | 1,243 | 2,486 | 0 | 0 | 135,339 | 12 | Stable |
| Darwinbox | 1,248 | 1,248 | 0 | 0 | 46,371 | 7 | Stable |

jobs_seen is a count of observations across runs, not unique jobs. Do not present it as unique inventory. new_jobs is new rows added by ingestion; it is not necessarily the same as the number of unique active vacancies.

The most important production finding is that the live container has no v2.board_scheduler module and no ats_board_poll_schedule table. The QA candidate does have that module and table. Therefore the newer persistent per-board scheduler and PR #77's adaptive per-board 429 cooldown are **not active in production**. The production image was created on 8 November; the QA image was created on 17 November. A tested code merge alone did not upgrade the live runtime.

Production's active ATS registry snapshot contains 10 active boards:
- Greenhouse: 3
- Ashby: 2
- Workday: 1
- SmartRecruiters: 1
- Workable: 1
- Keka: 1
- Darwinbox: 1

The runtime config also enables LinkedIn and Naukri as global fetchers. Instahyre and Lever are disabled.

## Priority order

### P0 — Workday request control and scheduler rollout

1. Validate v2.board_scheduler against the existing 10-board production allowlist in a disposable QA database. Do not turn on polling in the current QA service; create a separate test copy/config.
2. Prove scheduler config sync creates one due record for each enabled board, respects the existing explicit allowlist, and does not silently activate unreviewed registry rows.
3. Exercise success, ordinary failure and HTTP 429 paths. Verify progressive per-board cooldown (5/10/20/40/60 minutes, capped at 60 minutes), longer provider Retry-After handling, persistent host cooldown and no premature re-request.
4. Verify one throttled Workday host does not pause Greenhouse, Ashby, SmartRecruiters, Keka, Darwinbox, Naukri or LinkedIn.
5. Build the release image from the reviewed v2-live-radar commit, take and verify a production database backup, confirm schema migration is additive/backward-compatible, then plan a controlled production update. Do not activate additional boards during the scheduler rollout.
6. After the update, inspect per-board due times and source runs for at least 24 hours. Workday requests must fall materially; repeated 429s must no longer occur at the old cadence.

### P1 — LinkedIn and Naukri reliability

- LinkedIn: retain conservative request pacing and cooldown behavior; analyse the 12 recent 429s and four failed pages by query/target. Keep request budgets bounded and avoid broad retries after the first 429.
- Naukri: preserve the five-minute relay workflow, verify every expected target/search result and inspect the two recent failed pages. Verify relay-to-V2 ingestion and second-poll idempotency.
- Keep source discovery freshness separate from collector execution status: a successful run with zero new jobs is not a failure, but a stale last-success timestamp is not healthy.

### P1 — ATS collector request efficiency and completeness

- SmartRecruiters baseline: 508 runs / 11,684 requests in the latest 24-hour query; every run made exactly 23 calls (3 listing pages + 20 detail lookups), 0 failed pages / 0 HTTP 429, 300 postings seen per run and 251 new rows. The repeated 20 detail calls are the optimisation target; keep the 3 listing pages on every poll.
- A focused implementation is in branch fix/smartrecruiters-detail-cache-20261117: reuse stored successful detail responses (description, URL and fetch timestamp) for 7 days; refresh expired/missing details under the existing 20-detail-per-board cap; log detail_attempts and detail_cache_hits per run. This is not deployed. The first 5 focused tests passed, including normal mapping/429 tests, cache hit, seven-day refresh and a 25-posting request-budget test (20 cache hits, 5 detail calls). Full V2 regression is currently running.
- Do not claim request savings until exact-head CI, a QA image and post-deployment source telemetry confirm lower detail-call counts while descriptions and listing freshness remain correct. Brand-new / uncached postings can still consume the existing detail budget.
- Keep the existing 251 new jobs while reducing avoidable pagination/detail requests.
- Greenhouse/Ashby: verify active board identity, result caps, board-level failures and publication timestamps. Preserve the successful 3/3 and 2/2 board evidence from QA.
- Workable/Keka/Darwinbox: keep their stable paths; investigate isolated failures and ensure per-board metrics show partial failures rather than marking a provider fully successful.
- Do not add boards merely to increase counts. Board identity must be validated; activation stays explicit and allowlisted.

### P2 — Feed quality and visibility

- Verify normalize → upsert → canonical dedupe → user evaluation → dashboard feed on repeated polls.
- Confirm stable IDs/URLs, meaningful company/title/location, posted-time provenance, job freshness, and source attribution.
- Check that newly ingested jobs appear in the dashboard within the configured polling/refresh budget.
- Investigate duplicate clusters, malformed postings, stale/expired listings and source-specific zero-new periods.
- Keep role/location matching permissive enough to avoid silently excluding valid jobs; the current member profile is already producing matches with Remote only disabled.

### Later, not part of this increment

- Telegram linking, webhooks and per-user alert delivery.
- Broader member-only product features and administrator/member parity.
- Company Watch manifest expansion and adding many more employer boards.
- New notification channels.

These are separate product workstreams. They must not distract from making the existing fetchers and feed dependable.

## QA and release gates

- Exact-head GitHub CI passes on the PR.
- Unit tests cover scheduler cooldown, host isolation, retries, source contracts and idempotent ingestion.
- QA uses a copied database and separate config; no production credentials or Telegram secrets.
- QA board scheduler test proves allowlist sync and one controlled board poll; a second poll must not duplicate job rows.
- QA source flags remain disabled outside explicit test invocations.
- Production database snapshot passes SQLite integrity check before any release.
- Production image and configuration are identified; schema migration is additive and rollback image is recorded.
- After a controlled release, compare 24-hour source metrics to this baseline. Do not claim success based only on container health or a green unit-test suite.

## Small correctness fixes being handled alongside reliability

- Hide the empty Intelligence navigation group from members (the Source Health link was already hidden, but its parent heading remained visible).
- Implement the documented Remote only semantics: role is always required; a location is required unless Remote only is selected. With a location, the job must be explicitly remote and match that location. With no location, only explicitly remote worldwide jobs match. Hybrid and on-site roles do not count as remote.
- These are small UI/preference correctness changes; they must not expand into a Telegram or notification project. They remain behind their own review/CI gate and do not change the current saved member preference.

## Next exact actions

1. Finish the current role/navigation and Remote only regression tests.
2. Verify board-scheduler allowlist sync and one-board poll in an isolated QA DB/config, including Workday cooldown state without repeatedly hitting the already-throttled upstream.
3. Review SmartRecruiters request volume and Naukri failed-page detail, then implement the highest-value fetcher fixes.
4. Update the source-health dashboard/handovers with per-board freshness and last-success signals if current fields are insufficient.
5. Create a reviewed PR, pass exact-head CI, rebuild candidate QA and only then plan the controlled runtime update.


## 17 November 2026 — first isolated scheduler simulation

A temporary SQLite database was created from the existing production allowlist and poll intervals, while running the scheduler code inside the candidate QA container. This was not the shared QA database and did not make any network requests.

- configured_boards returned exactly 10 active allowlisted boards across 7 API hosts.
- sync_config created exactly 10 schedule rows.
- Workday's simulated first HTTP 429 persisted a 5-minute next-due/host cooldown.
- Workday's simulated second HTTP 429 persisted a 10-minute next-due/host cooldown.
- An Ashby board on api.ashbyhq.com remained claimable while the Workday NVIDIA host was cooling down.
- The second cooldown did not affect the live QA config: all source switches remain false and notifications remain false.
- The simulation passed. This proves the scheduler's temporary-DB state/claim/cooldown logic; it does not yet prove the full application scheduler dispatch path against a live QA ATS board. That is the next isolated QA test.


## 17 November 2026 — scheduled dispatch integration smoke

On the candidate QA image, a throwaway SQLite DB was initialized and synced with only one existing Greenhouse board (Coinbase). The normal application scheduler claim and scheduled-board dispatch path was exercised. One public Greenhouse board read returned 260 jobs; the collector/upsert persisted those rows; the scheduler recorded success with 1/1 board successful, zero failures and zero 429s; board baseline_pending cleared. The first inventory baseline was suppressed in the notification ledger. SQLite integrity_check returned ok. Telegram notifications were disabled and no Telegram credentials were available to the test. The shared QA config and production database/runtime were not changed.

This proves one real scheduled board dispatch and baseline behavior. Repeat-poll idempotency for this scheduler dispatch path remains a follow-up QA check; collector-level second-poll dedupe for Naukri, Greenhouse and Ashby was previously verified.


## 17 November 2026 — repeated scheduled-poll idempotency smoke

The first actual dispatch smoke proved the one-board claim → collector → upsert → baseline-suppression → scheduler-result path. A second isolated run repeated the same board poll after respecting the scheduler host minimum interval.

- First scheduled Coinbase Greenhouse poll: 260 seen, 260 inserted; all 260 first-inventory ledger entries were suppressed as baseline, not sent.
- Second scheduled poll: 260 seen, 0 inserted.
- Final job row count remained 260, duplicate (source, source_job_id) groups: 0, SQLite integrity_check: ok.
- Both source_runs recorded success, one board attempted / one succeeded / zero failures. The host pacing interval was not bypassed.
- Tests used temporary QA SQLite/config files, one public Greenhouse board per poll, notifications disabled and no Telegram credentials. The temporary files were removed. Neither shared QA data/config nor production was changed.

This closes the isolated two-poll scheduler idempotency check for one representative Greenhouse board. Workday-specific scheduled dispatch remains to be exercised without repeatedly hitting its throttled upstream; its cooldown state is covered by the no-network simulation above.


## 17 November 2026 — production snapshot migration compatibility check

A fresh consistent backup of the live production DB was created before preparing the scheduler canary: /var/backups/job-radar-daily/production-before-scheduler-canary-20261117.sqlite3 (129 MB, mode 0600, SQLite integrity ok, SHA-256 8593c7fa32757635a0ee27624ec8c957c584163d13f5271976ac0f25fa684cf1). At snapshot time it contained 27,497 jobs, 2 users and 10 active ATS registry boards.

The candidate V2 image was then used to initialize a disposable copy of that snapshot and sync the exact sanitized production source allowlist/poll intervals. Results:
- Existing 27,497 job rows, 2 user rows and 10 active registry rows were preserved.
- V2 initialization created the scheduler state schema; scheduler sync created exactly 10 schedule rows.
- The scheduled (source, board_key) set exactly matched the 10 configured production boards.
- SQLite integrity_check returned ok after the migration.
- Temporary cloned DB/config were removed after the check. The production DB was not migrated and its container was not restarted.

This proves schema/config-sync compatibility against a copy of the current production DB. It does not authorize production rollout or scheduled polling. Production rollout still requires reviewed code/CI, final candidate QA, an additive migration review, this verified backup and explicit owner approval.


## 17 November 2026 — SmartRecruiters detail-cache optimization in review

Production telemetry showed a fixed 23 requests per SmartRecruiters run: 3 listing-page calls plus 20 detail calls. The collector was making those detail calls on every poll, including for existing postings whose description and URL were already stored.

A separate implementation branch fix/smartrecruiters-detail-cache-20261117 now:
- reads previously fetched details from this board's existing jobs rows;
- reuses the stored description/URL for up to 7 days after a successful detail lookup;
- refreshes missing, failed or expired detail lookups under the existing per-board cap of 20;
- continues fetching listing pages on every poll so the new-job discovery path is unchanged;
- logs per-run detail_attempts and detail_cache_hits so a release can be measured.

Five focused SmartRecruiters tests pass, including existing mapping and Retry-After behavior, cached-detail reuse, 7-day refresh, and the 20-call detail budget. The 25-listing test fixture had 20 warm cached detail entries and verified exactly 20 cache hits plus 5 detail calls (one listing request + five detail requests total).

The full V2 suite is still running on this branch. No production or QA source configuration was changed, no live SmartRecruiters collector was invoked, and no production deployment has occurred. Do not merge/deploy until full local regression and exact-head GitHub CI pass, followed by QA image verification.

## 18 November 2026 — PR #80 CI and GitHub branch hygiene

- SmartRecruiters detail-cache commit 43826b361f85e1062cf15ec96705825ae866fa6c passed GitHub Actions V2 CI workflow #1520 (exact head SHA, conclusion: success). The full local V2 suite also passed: 507 tests, 0 failures, 434.418 seconds.
- PR #80 remains open against v2-live-radar; do not merge until the diff is reviewed and the candidate QA image is rebuilt from the reviewed commit. No live source flags or deployment were changed.
- Remote branch inventory at this audit: main, v2-live-radar, fix/smartrecruiters-detail-cache-20261117, and three merged-PR branches. The three obsolete branches were docs/post-pr77-merge-readiness-20261117 (PR #78 merged), fix/ats-board-rate-limit-backoff-20261117 (PR #77 merged), and fix/member-remote-only-global-20261117 (PR #79 merged).
- Cleanup policy: retain main and v2-live-radar; retain the current PR #80 head branch until merge/close; delete merged feature branches after verifying their PR is merged and the change is reachable from v2-live-radar. Do not delete branches for closed-but-unmerged PRs until their unique commits are checked for inclusion or explicitly abandoned.
- The closed, unmerged PR inventory (#70, #64, #63, #62, #61, #60, #59, #52, #50, #46, #43, #42, etc.) is not equivalent to active work. Their branch refs are not present in the current remote branch listing, so no further deletion is needed for those refs. PR #80 is the only open PR in the current repository inventory.
- VM check: production and QA health both HTTP 200; only the expected v2-radar-1 and job-radar-current-v2-qa containers are running; root filesystem 14 GB used / 45 GB total (29%). No VM cleanup or deployment was performed in this pass.


## 18 November 2026 — release qualification checkpoint

- PR #80 (SmartRecruiters detail-cache optimization) is merged into `v2-live-radar` at application head `69a204a7349b67d6439e50e27f673834be4d4971`; exact-head V2 CI run #1522 passed. Full local V2 regression: 507 tests, 0 failures, 420.654 seconds. Focused Company Watch/global-discovery suite: 32 passed.
- Documentation PR #81 merged as `472c2eef80bf34e0c87e9b1e65967181a7e698f5`; exact-head CI #1524 passed. This is documentation-only on top of application head `69a204a...`.
- Fresh production backup: `/var/backups/job-radar-daily/production-pre-release-20261118.sqlite3`, 135,303,168 bytes, mode 0600, SQLite integrity `ok`, 27,534 jobs, 2 users, 10 ATS registry boards, 51,920 source runs. SHA-256 `55b7402ad1a1fb3ebe871afee0c03008c1f7b5ecc25caf8689b399ff973b3e1c`.
- Candidate image `job-radar-v2-qa:472c2ee` built from the merged V2 tree; image ID `sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c`. It runs in isolated QA on loopback port 8013 using `/var/lib/job-radar-release-qa/data`, a copy of the verified production backup. All source flags and notifications are false; no production credentials/config token were copied.
- Candidate startup/migration: `/health` 200, dashboard and OpenAPI 200, SQLite integrity `ok`. Existing jobs/users/ATS registry/source_runs counts were preserved exactly. Schema comparison found no dropped tables/columns; 11 tables and additive columns were added.
- Candidate-container scheduler tests: 15 passed. Disposable scheduler sync from the sanitized production config created exactly 10 active board schedules across seven ATS providers. Workday 429 cooldowns escalated 5 to 10 minutes; Ashby remained claimable during Workday cooldown.
- Actual candidate-image scheduled dispatch smoke on a temporary DB and existing Coinbase Greenhouse board: first poll 259 seen / 259 inserted and baseline-suppressed; second poll 259 seen / 0 inserted. Both successful, 1/1 board, 0 failures, zero duplicate source IDs, SQLite integrity `ok`. Temporary DB files removed.
- Dashboard HTML serves search, source, score, age and sort controls, plus Alertable Only and Remote Only toggles. Filter behavior is covered by the passing full V2 suite.
- Production has not been changed or restarted. It remains on `job-radar-prod-canary:6e5becb` with HTTP 200. The exact 10-board allowlist and LinkedIn/Naukri global fetchers are preserved.
- Remaining gates: candidate SmartRecruiters cache telemetry check; read-only LinkedIn/Naukri/Workday and Naukri relay review; record rollback image/config and exact promotion invocation; controlled production promotion only after these checks. Observe at least 24 hours after deployment before declaring success.
- Company Watch manifest remains a follow-on: 100 rows (90 enabled / 10 disabled), 19 direct ATS candidates, 81 manual-review. It has not been imported into persistent runtime storage. After core feed reliability, import as review-only and activate only an explicitly verified/approved subset. Never auto-activate all 100.


## 18 November 2026 — production promotion and Company Watch import

- Production promoted to `job-radar-prod-release:472c2ee`, image ID `sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c`. Container `v2-radar-1` started at `2026-11-17T20:59:46Z`; `/health`, `/dashboard/` and `/openapi.json` return HTTP 200. The old production image and rollback image remain available; existing data volume was reused.
- Final pre-deploy backup: `/var/backups/job-radar-daily/production-before-v2-release-20261118T2058Z.sqlite3`, 135,368,704 bytes, mode 0600, SQLite integrity `ok`; 27,546 jobs, 2 users, 10 ATS boards, 51,984 source runs. SHA-256 `6c8fa1f139ea05a081c0f65fefc84540f9d9600febe59f57b71b3a1a0bd9da15`. Original compose backup checksum `d9e695f6a4c0299b3bdae4d0ce8817fdfa21e31e301c6d6b93cb189201a21917`; release compose diff changed only image tag.
- Scheduler startup synchronized exactly 10 active schedules matching the 10 active/available ATS registry rows. Initial scheduled pass: nine boards succeeded and first inventory was baseline-suppressed; Workday returned one HTTP 429 and entered a persisted 5-minute host cooldown (`consecutive_failures=1`). No unrelated provider was blocked. Verify no premature Workday retry; next due was `2026-11-17T21:06:27.910416+00:00`.
- Naukri relay timer remains active at 5-minute cadence; relay workflow #9874 succeeded. Post-deploy Naukri collector accepted 313 jobs and completed with 0 new rows / 0 failed pages. LinkedIn post-deploy scan succeeded (40 seen, 10 new); existing global notification configuration was unchanged and one legacy notification was delivered. No Telegram feature/config changes were made.
- SmartRecruiters first production poll saw 300 postings, reused 20 cached detail records and fetched 20 uncached details (23 total requests including three listing pages). Candidate warm-cache simulation proved steady state at 300 hits / 0 detail attempts / 3 listing requests. Cache warm-up is incremental at 20 new details per board poll; observe subsequent polls before claiming request savings.
- Pinned Company Watch manifest imported into production after the core scheduler rollout: hash `706ea1d6204cd80379aa57d8dd2b041f5c3f1f7af6666c7140c2c216ce2049bd`, source `main@29cbb17190b26829d49e1458137d75f2e8f286aa`, 100 rows, 19 candidate-staged / 81 manual review. Nineteen candidates inserted with review status `discovered`; 0 companies created, 0 boards linked, 0 verified, 0 activated, 0 scheduled, 0 network requests and 0 notifications. Production remains at 10 active registry boards and 10 active schedules; SQLite integrity `ok`.
- Release is deployed, but full reliability acceptance remains pending at least 24 hours of source telemetry and Workday cooldown verification.


## 18 November 2026 — first production cooldown observation

- Workday post-release requests at 21:01:26, 21:06:34 and 21:16:37 UTC each made one request and received one 429. The persisted host cooldown escalated 5 → 10 → 20 minutes; next due `2026-11-17T21:36:38.680292+00:00`. No early retry occurred. Other hosts continued; 29 non-Workday source runs completed after the second 429 before the 10-minute observation checkpoint.
- Post-deploy ATS board polls were successful for Greenhouse, Ashby, Workable, Keka and Darwinbox; first inventories were baseline-suppressed. Naukri relay #9878 succeeded and the V2 collector accepted 317 jobs with 0 new / 0 failed pages. LinkedIn had 0 post-deploy 429s in the observed window (70 seen / 10 new); one existing global notification was delivered by unchanged legacy settings.
- SmartRecruiters detail-cache hits progressed 20 → 40 → 60 across three production polls, with up to 20 uncached detail attempts per poll and three listing requests. A candidate warm-cache simulation reached 300 hits / 0 detail attempts / 3 listing requests. Continue observing until organic cache warm-up is complete.
- Production dashboard OpenAPI exposes `q`, `search`, `source`, `min_score`, `max_age_hours`, `sort`, `sort_by`, `sort_order`, `alertable_only`, `remote_only`. Post-release jobs count 27,556, duplicate source-ID groups 0, and production DB quick check `ok`.
- Company Watch manual-review reasons: 71 generic careers pages need discovery; 8 disabled/manual/employer-identity rows; 2 mixed board-type/scan-mode cases. The 19 staged candidates are Greenhouse 10, Lever 6, SmartRecruiters 3. CSV `verified_ats_board` labels are not V2 live verification; keep all candidates review-only.


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
