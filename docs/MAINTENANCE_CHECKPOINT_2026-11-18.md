# JobBeeper engineering maintenance checkpoint — 18 November 2026

## Scope

Read-only production inspection, Company Watch correction preparation, ATS discovery research, VM housekeeping, and GitHub branch cleanup. No production application code, configuration, database rows, source flags, scheduler entries, or notifications were changed.

## Production VM

- Host: job-radar; online; 2 vCPU; approximately 956 MiB RAM; root disk 48.3 GB total / 14.8 GB used (30.6%).
- Latest six-hour monitor: CPU average 7.56%, peak 71.5%; memory average 65.13%, peak 72.7%; load1 average 0.18, peak 1.77; I/O wait average 1.84%, peak 22.6%; CPU steal average 4.26%, peak 53.9%.
- Latest sample at 04:54 UTC: CPU 5.0%, memory 61.7%, swap 626 MB / 2.15 GB, load1 0.10, disk 30.6%, OOM kills 0, no zombies.
- No open Termalin alerts.
- Production container: v2-radar-1, image job-radar-prod-release:472c2ee, healthy, one active container; latest Docker stats showed about 219 MiB container memory.
- Retained production and rollback/QA images. Do not run docker image prune: the retained candidate and rollback images are deliberate recovery assets.
- Removed two stopped QA container objects (job-radar-current-v2-qa and job-radar-pre-release-qa-cc2087e). No -v was used; the current QA bind-mounted data directory remains on disk (about 116 MiB). No running container was changed.

### Pending host maintenance

The host reports reboot-required. Running kernel is 6.8.0-1060-oracle while newer 6.8.0-1062/1067-oracle kernel packages and libc6 updates are installed. Do not reboot automatically: production will restart. Obtain an owner-approved maintenance window, verify backups and container restart policy, then reboot and recheck app health, source scheduler and snapshot timer.

## Backup and snapshot status

- The 18 November 02:45 UTC production SQLite snapshot completed successfully: integrity=ok, 27,656 jobs, 136,712,192 bytes. The development snapshot was skipped because no healthy development container was available.
- Historical 16/17 November snapshot failures were caused by an unavailable/stopped development container after the production snapshot succeeded. The 18 November run completed successfully using the optional-development skip behavior.
- Termalin reports no configured backup jobs and no off-host archives. Local snapshots exist, but local disk copies are not disaster recovery.
- Created draft backup job: JobBeeper production recovery snapshot. It is not active until the owner confirms it. Draft ID: 2a0b4cc8-c116-4f4d-88a8-aba34ec0dfe0. Confirmation: https://termal.in/account#backup-draft=2a0b4cc8-c116-4f4d-88a8-aba34ec0dfe0

## Production database and source reliability

Read-only SQLite inspection at approximately 04:55 UTC:

- PRAGMA quick_check: ok.
- Jobs: 27,664; employer records: 10.
- ATS registry: 10 active boards; scheduler: 10 active schedules.
- Company Watch: 19 candidates, 81 manual-review rows, 100 manifest rows.
- Global ATS discovery runs: 0; no search-engine discovery worker is configured.

Source runs since production promotion at 2026-11-17T20:59:46Z, observed through approximately 2026-11-18T04:55Z:

| Source | Runs | Requests | HTTP 429 | Failed pages | Jobs seen | New jobs |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 183 | 183 | 0 | 0 | 77,017 | 5 |
| Darwinbox | 232 | 232 | 0 | 0 | 9,048 | 0 |
| Greenhouse | 279 | 279 | 0 | 0 | 32,104 | 2 |
| Keka | 230 | 460 | 0 | 0 | 26,680 | 0 |
| LinkedIn | 88 | 525 | 2 | 1 | 1,163 | 93 |
| Naukri | 95 | 95 | 0 | 0 | 30,085 | 3 |
| SmartRecruiters | 92 | 568 | 0 | 0 | 27,600 | 15 |
| Workable | 234 | 234 | 0 | 0 | 1,404 | 0 |
| Workday | 11 | 11 | 11 | 11 | 0 | 0 |

The 24-hour window is not complete. It ends at 2026-11-18T20:59:46Z (2026-11-19 02:29:46 IST). Workday's 11 requests all received 429; its last run was 04:16:57Z and the next scheduled attempt is 05:16:57Z. LinkedIn's last run was 02:40:43Z and its 160-minute cooldown expires at 05:20:43Z. Do not manually probe either source or reset cooldowns. Final acceptance must compare request volume, 429s, page failures, source freshness, Naukri relay, duplicate IDs, and job ingestion against the previous baseline.

## Company Watch correction

The V2 production database still contains the old pinned manifest (19 candidate_staged / 81 manual_review). The main source CSV formatting fix is merged in PR #89 (main@da7e42dbaaeee0a89ebdde92799aee8db7543ec6); V2 correction PR #87 now pins its validated 100-row snapshot. Mistral AI changes from Lever to Ashby, SoundHound moves to manual review, The Standard is staged as Workday, and Caxton remains manual because V2 deliberately treats verified_workable_board as an ambiguous status.

- Mistral AI: Lever mistral → Ashby mistral.ai.
- SoundHound AI: invalid Greenhouse soundhoundinc → official careers page; keep manual.
- The Standard: Workday candidate now supported.
- Caxton Associates: Workable candidate now supported.

PR #87 has now merged into v2-live-radar as e1617dd50cb7970b2e7677eae990b37cfde87a3c. It updates the V2 pin and regression tests. Expected dry-run result: 100 rows, 92 enabled / 8 disabled, 19 candidate_staged / 81 manual_review. This merge is not deployed to production. Old production candidates lever/mistral and greenhouse/soundhoundinc still need admin rejection after the corrected manifest is deployed and imported. No production import, SQL patch, link, verification, activation, or polling change has been made.

## Search-engine-assisted ATS discovery

PR #86 documents a candidate-only design using a licensed Google SERP API adapter, structured provider target filtering, provider URL normalization, public board verification, existing global-candidate review queue, and a bounded 30-minute scheduler. The design also retains Common Crawl and robots-aware sitemap discovery as complementary sources. Google Search HTML scraping is excluded; Google ADK is not required for the deterministic first version. No API key, spend, worker, or recurring job has been configured.

Research correction: DataForSEO currently lists Standard normal priority at about five minutes average but a 45-minute target turnaround; Priority is about one minute average; Live is about six seconds. The design PR was updated to clarify that a 30-minute cadence should use Priority for the first pilot and does not imply search-index freshness.

## GitHub cleanup

Six remote branches associated with already-merged PRs #80–#85 were deleted after confirming those PRs were merged and no open PR depended on them:

- docs/nov18-morning-observation-20261118
- docs/production-release-manifest-20261118
- docs/release-qualification-20261118
- docs/workday-backoff-observation-20261118
- feat/fetcher-feed-reliability-20261118
- fix/smartrecruiters-detail-cache-20261117

Six merged remote branches were deleted after verifying PRs #80–#85 were merged. The temporary source-fix branch for PR #89 was deleted after merge. PR #86 (search-engine ATS discovery design) and PR #87 (Company Watch correction) have both merged into v2-live-radar. Their remote topic branches were deleted after merge. Current remote branch count: three — main, v2-live-radar, and docs/maintenance-checkpoint-20261118 (PR #88). PR #89's source-fix branch was also deleted after its merge. Main and v2-live-radar were retained. The local production checkout was fetch-pruned but not pulled or reset.

## Checkouts intentionally preserved

- /home/ubuntu/job-beeper: clean working tree on v2-live-radar, still 782 commits behind origin at inspection. Not pulled, reset, rebuilt or deployed.
- /home/ubuntu/job-beeper-dev: dirty, 176 commits behind, with modified v2/config.json and untracked .env.save, .venv and config backup. Preserved untouched.
- /home/ubuntu/job-beeper-global-ats-test and /tmp/job-radar-source-observability: preserved; not modified.

## Open work

1. Confirm exact-head CI for PR #88; merge the maintenance checkpoint when green.
2. PR #86 and PR #87 are merged but not deployed. Do not deploy the Company Watch correction or import its manifest until the 24-hour source reliability gate and owner approval are satisfied.
3. After deployment, dry-run and import the corrected manifest, verify 10 registry boards / 10 schedules remain unchanged, then reject the two stale candidate keys through the admin review API.
4. Complete the 24-hour source reliability assessment at 20:59:46Z on 18 November.
5. Ask the owner to confirm the off-host backup draft and approve a maintenance reboot window.
6. Continue hourly read-only VM, database, scheduler, source and GitHub monitoring. Keep Telegram/member-feature expansion out of scope.


## Post-reboot validation — 18 November 2026, 05:18 UTC

The owner approved the reboot without a scheduled maintenance window because the instance is a personal test environment with no active users. JobBeeper Health Watch was paused before reboot and remained paused during the planned outage; it is to be resumed after validation. The expected downtime must not be reported as an incident.

- Reboot completed: previous boot started 2026-10-07 18:45:42 UTC; new boot started 2026-11-18 05:15:56 UTC.
- Running kernel is now `6.8.0-1067-oracle`; `/var/run/reboot-required` is cleared.
- Docker is active and enabled; production container `v2-radar-1` automatically restarted using the existing `unless-stopped` policy and unchanged image `job-radar-prod-release:472c2ee`.
- Application health endpoint returned HTTP 200, version 2.0.0.
- SQLite `quick_check`: ok; jobs=27,675; active ATS boards=10; active schedules=10.
- No failed systemd units. Container restart count=0.
- Source polling resumed after boot. Latest observed runs: Greenhouse, SmartRecruiters, Keka, Darwinbox, Workable, Naukri and Ashby succeeded; Workday received another HTTP 429 and remains rate-limited. LinkedIn's persisted cooldown was restored at startup; it was not reset.
- Fresh pre-reboot SQLite snapshot: `/var/backups/job-radar-daily/pre-reboot-20261118.sqlite3`, 136,978,432 bytes; integrity=ok; SHA-256 `7a5e0f6000b38d083d9f0b566dedca639f80298e608c8740bdd3eab3303bf2c6`.
- The Termalin encrypted backup remains a draft; no off-host archive exists yet. The local pre-reboot snapshot is a recovery point, not off-host disaster recovery.
- A transient Termalin "server restarted" warning is expected for this approved reboot and should clear; it is not a production incident.

The reboot did not deploy the merged Company Watch changes or modify the production allowlist. The production application image and active board/schedule configuration remain unchanged.

## Follow-up engineering and post-reboot relay recovery — 18 November 2026, 05:59 UTC

### SERP discovery implementation

- PR #90: SERP-to-ATS URL normalizer merged into `v2-live-radar`.
- PR #91: credential-backed DataForSEO Live and Serper clients merged.
- PR #92: Company Watch candidate-rejection safety tests merged.
- PR #93: persistent disabled-by-default SERP discovery coordinator merged.
- PR #94: operator-invoked worker and matched 50-query DataForSEO/Serper benchmark merged as `67126335b3124760464fae4ae390c2f757fb7f26`.
- PR #94 CI passed: **537 V2 tests**.
- The worker has no installed timer. It requires an explicit persisted enable plus positive monthly cap and runtime DataForSEO credentials. The benchmark requires `--confirm-paid` and both provider credentials; it makes 100 requests (50 matched query pairs) and writes local JSONL evidence without importing candidates.
- No paid SERP requests, credentials, production deployment, SERP database writes, candidate activation or spend approval have occurred.

### Naukri relay timer recovery

The hourly health-watch inspection correctly identified a post-reboot relay issue. The systemd timer was `active/elapsed` with no future trigger, despite the service unit being enabled. This caused the relay feed to age past the application's 15-minute freshness limit. Naukri app fetches continued receiving HTTP 200, but failed closed with `RuntimeError` and zero jobs; this was a stale-feed problem, not an HTTP 429.

Recovery performed:
- Manually started the already-configured oneshot service `job-radar-naukri-relay.service` once at 05:53:59 UTC. Its configured action dispatches the existing workflow in the public relay repository; the service exited successfully at 05:54:01 UTC.
- GitHub workflow run [44247426037](https://github.com/AvinashBhalla/job-beeper-naukri-relay/actions/runs/44247426037) completed successfully at 05:56:18 UTC.
- Relay feed refreshed to 319 jobs at 05:56:13 UTC.
- The app's next Naukri poll at 05:57:46 UTC succeeded: 319 jobs seen, 5 new.
- The systemd timer returned to `active/waiting` with a next scheduled trigger at 05:58:59 UTC, and it triggered again at 05:59:17 UTC. This verifies the five-minute timer has re-armed after the manual service invocation.
- No app restart, cooldown reset, DB edit or production deploy was performed.

The JobBeeper Health Watch automation prompt has been updated to verify the timer's future trigger, relay workflow, feed freshness and successful app ingestion independently. It is explicitly read-only and must not trigger/restart the relay service.

### Current production state

- App health HTTP 200; SQLite `quick_check=ok`.
- Active registry: 10/10; active poll schedules: 10/10.
- All ten registered boards remain unchanged. Workday remains in its existing 429 backoff; do not probe or reset it.
- Naukri recovered after the relay refresh. The earlier five consecutive stale-feed failures remain part of the reliability-window evidence and should not be erased from the assessment.
- The 24-hour source reliability window remains open until **2026-11-18 20:59:46 UTC** (2026-11-19 02:29:46 IST). Do not block other engineering on this gate.

### Outstanding owner decisions

1. DataForSEO pilot and monthly spend cap approval (no paid requests until explicitly approved).
2. Confirmation of the Termalin off-host backup draft. It remains a draft; no off-site archive exists.
3. Company Watch correction remains merged but not deployed. Do not import/activate candidates until release qualification and owner approval.

### Company Watch release qualification — isolated QA only

Using a temporary shallow checkout of the exact `v2-live-radar` head (`cfb095d1d470a8b5f791d94c802a61f29ed0de21`) and the existing production image's Python dependencies, I ran the pinned manifest parser and importer without deploying or modifying the live database.

- Read-only dry run: 100 rows; SHA-256 matched the pinned value; 19 `candidate_staged`, 81 `manual_review`, 0 invalid. The dry-run response reported zero company creation, linking, verification, activation, scheduling, network requests or notifications.
- Full import simulation ran only against a temporary SQLite backup of production. Result: 2 candidates inserted, 17 existing candidates updated, 0 terminal candidates altered; 100 manifest rows recorded for the new hash.
- Before/after on the temporary database: active registry stayed 10/10 and active poll schedules stayed 10/10. No company records were created, no board was linked/verified/activated, and no schedule or notification was emitted.
- The temporary database copy was removed after inspection.
- Live production remains unchanged: its manifest-import table still contains only the prior hash `706ea1d6204cd80379aa57d8dd2b041f5c3f1f7af6666c7140c2c216ce2049bd`; the corrected hash has not been imported.
- The two stale live candidates remain `lever/mistral` (id 1) and `greenhouse/soundhoundinc` (id 6), both still `discovered`. They must be rejected through the guarded admin review route after the corrected manifest is deployed/imported. Do not alter them before that release step.

This qualifies the parser and candidate-only importer in an isolated production-like database. It does not authorize deployment or live import.

### SERP benchmark reporting follow-up

- PR #95 merged into `v2-live-radar` as `267d6138055217d8e5931b3497584e58ad1a8477`.
- CI passed: **539 V2 tests**.
- The benchmark now has an offline summarizer for coverage, unique boards, duplicate appearances, cross-engine overlap, actual DataForSEO task costs and Serper credit estimates.
- Optional manual labels distinguish verified employer-owned boards from false positives; unreviewed candidates and conflicting labels remain explicit.
- No network calls are made by the summarizer. The 50-pair benchmark itself remains unrun pending provider credentials and owner spend approval.

### Source reliability checkpoint — 18 November 2026, 06:09 UTC

The 24-hour window is still in progress. Current aggregate since 17 November 20:59:46 UTC:

| Source | Runs | Success | Non-success | HTTP 429 | Jobs seen | New jobs |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 211 | 210 | 1 | 0 | 88,861 | 5 |
| Darwinbox | 268 | 268 | 0 | 0 | 10,452 | 0 |
| Greenhouse | 324 | 324 | 0 | 0 | 37,267 | 2 |
| Keka | 264 | 264 | 0 | 0 | 30,650 | 1 |
| LinkedIn | 101 | 98 | 3 | 3 | 1,354 | 151 |
| Naukri | 110 | 105 | 5 | 0 | 33,061 | 17 |
| SmartRecruiters | 107 | 107 | 0 | 0 | 32,100 | 21 |
| Workable | 269 | 269 | 0 | 0 | 1,614 | 0 |
| Workday | 12 | 0 | 12 | 12 | 0 | 0 |

Naukri's five failures all correspond to the stale relay window after reboot. It has since succeeded on three consecutive app polls (05:57:46, 06:02:50, 06:07:50 UTC), with 319, 314 and 317 jobs respectively. The relay workflow dispatched by the timer at 05:59 and 06:04 completed successfully. The timer remains active/waiting and next scheduled at 06:14:19 UTC.

Workday remains in adaptive 429 backoff; no manual probes or resets. LinkedIn's 3 rate-limited runs are retained in the assessment; do not infer continuous failure from the aggregate because successful scans also occurred. Ashby had one isolated runtime failure; subsequent polls are succeeding. Other six sources have no non-success runs in this window.

This is an interim snapshot, not the final 24-hour acceptance decision. Continue monitoring until 20:59:46 UTC.

### Termalin backup decision — 18 November 2026

The owner does not want to spend on backup subscriptions. The Termalin confirmation form repeatedly became unresponsive and its server-side job remains DRAFT with no archives. The owner has explicitly chosen not to retry or subscribe. The existing draft is left untouched; it is not counted as a backup. No further owner action is requested for Termalin.

Off-site backup is therefore **not configured**. The recovery plan is local snapshots on the production VM's disk. This is not protection against VM/disk loss; that limitation is accepted under the current no-spend decision. Do not prompt the owner to retry the Termalin flow or upgrade a plan unless they ask to revisit off-site backup.

### Repository branch hygiene after SERP merges

After confirming PRs #90–#95 were merged and no PRs remained open, deleted the four remaining merged topic branches for PRs #90–#93, plus the branches for PRs #94 and #95. The two long-lived branches are retained: `main` and `v2-live-radar`. The local production checkout was not pulled, reset, rebuilt or deployed.

### Owner-paused Naukri relay — 18 November 2026, 09:03 UTC

The owner requested the Naukri relay pause at approximately 09:03 UTC. The first check still found the production timer enabled; one already-due final dispatch occurred at 09:05:18 UTC, with public workflow 44272634864 completing successfully at 09:05:20 UTC. The timer was then disabled/stopped to enforce the owner's intent. Verified post-change state: `ActiveState=inactive`, `SubState=dead`, `UnitFileState=disabled`, with no future trigger. No later public workflow runs appeared through the 09:23 UTC check.

Important billing distinction: the relay's repository `AvinashBhalla/job-beeper-naukri-relay` is public and runs on the standard `ubuntu-latest` GitHub-hosted runner. GitHub documentation says standard runners for public repositories are free and unlimited. The private JobBeeper repository's PR CI is the activity blocked by the account billing/spending notice; that is separate from the public relay workflow. No paid spend is needed to keep the standard public relay running.

The five-minute cadence still generated up to 288 runs/day, with recent run duration around 2m–2m30s. This is a lot of workflow/query activity even at no monetary runner cost. The recommended future compromise, only if explicitly resumed, is every ten minutes (up to 144 runs/day) with the existing 15-minute app freshness validation kept unchanged. PR #96 now carries that lower-frequency timer template, offline contract test and updated deployment instructions. It is not deployed.

The app-side Naukri collector is still configured to poll its raw relay feed every five minutes. Once the last published feed exceeds the existing 15-minute freshness threshold, the collector will fail closed; these failures are expected while the publisher is paused. No app config, database state, other ATS source or production application service was changed. Health Watch now treats the paused relay as expected and will not alert on stale-feed failures unless they materially affect overall app health or create noise.

### No-cost recovery and relay decisions — 18 November 2026

- PR #97 was merged into `v2-live-radar` as `d48e324b17d0ba5a9a5ed770da1e3f9404e8c3ea`. A follow-up production safety fix for immutable SQLite verification and sidecar cleanup was committed to the same branch.
- The seven-day local snapshot script/helper are now installed on production. The previous installed script is preserved for rollback.
- The first verified dated snapshot for 18 November contains 27,891 jobs (138,420,224 bytes); integrity check `ok`. The pre-upgrade rolling snapshot (27,656 jobs) and pre-reboot snapshot (27,673 jobs) are preserved and independently integrity-checked.
- The current `production-jobs.sqlite3` compatibility alias is a hard link to `production-jobs-20261118.sqlite3`. The first seven-day run also created dated production config/token snapshots, with mode 0600.
- The SHA-256 manifest contains five entries and all five passed `sha256sum -c`. No temp files or SQLite WAL/SHM sidecars remained after the final run. The backup directory is root:root mode 0700.
- Backup-specific tests: **6 passed** on the VM's disposable checkout; shell syntax and helper compile passed. Hosted CI remains unavailable because the private repository runner is blocked before startup by the account billing/spending restriction.
- The daily snapshot timer remains enabled. The installed systemd oneshot service was also started once after installation; `Result=success`, exit status 0, with both SQLite integrity checks ok and the snapshot published at 10:16:41 UTC. The app returned HTTP 200 before and after the snapshot and was not restarted. Disk free space was about 33 GB and the backup directory about 1.6 GB at final verification.
- PR #96 remains an optional ten-minute relay timer proposal only. The production Naukri relay timer remains disabled/inactive/dead by owner request; no paid runner, account upgrade or additional workflow dispatch is being pursued.
- No off-site archive exists. These snapshots remain on the same VM/disk and cannot recover from VM/disk loss.

### Interim 24-hour source reliability update — 18 November 2026, 11:01 UTC

Aggregated source runs since the assessment start at 17 November 20:59:46 UTC (window still open; final cutoff 18 November 20:59:46 UTC):

| Source | Runs | Success | Non-success | HTTP 429 | Jobs seen | New jobs |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 321 | 320 | 1 | 0 | 135,391 | 5 |
| Darwinbox | 409 | 409 | 0 | 0 | 16,268 | 4 |
| Greenhouse | 494 | 494 | 0 | 0 | 56,807 | 2 |
| Keka | 404 | 404 | 0 | 0 | 46,914 | 1 |
| LinkedIn | 104 | 99 | 5 | 5 | 1,394 | 169 |
| Naukri | 168 | 142 | 26 | 0 | 44,259 | 102 |
| SmartRecruiters | 163 | 163 | 0 | 0 | 48,899 | 74 |
| Workable | 412 | 412 | 0 | 0 | 2,472 | 0 |
| Workday | 17 | 0 | 17 | 17 | 0 | 0 |
| **Total** | **2,492** | **2,443** | **49** | **22** | **352,404** | **357** |

Interpretation:
- Workday remains the clear source reliability failure: 17/17 runs in this window received HTTP 429; adaptive backoff remains intact, with no manual probes/resets.
- LinkedIn had five 429 events but 99 successful runs and 169 new jobs; do not classify it as continuously down.
- Ashby had one isolated failure among 321 runs; subsequent scans succeeded.
- Naukri's 26 non-success runs include the five post-reboot stale-feed failures and additional stale snapshot failures after the owner paused the relay. The publisher is intentionally disabled, so further stale-feed rejection is expected. Do not re-enable the relay or change the app's 15-minute freshness guard as part of this reliability assessment.
- Darwinbox, Greenhouse, Keka, SmartRecruiters and Workable remain successful in all runs in the observed window.

This is an interim snapshot, not the final 24-hour acceptance decision. Continue read-only observation until 20:59:46 UTC.

### PR #98 — SERP budget numeric fail-closed guard merged

- Merged as `a0af67e313c12b663e0ab0c02940279284846c85` into `v2-live-radar`.
- New checks reject NaN/infinity/boolean caps, invalid persisted budget state and non-finite provider-reported task costs; a bad cost value retains the conservative reservation.
- Validation: **28 focused SERP tests passed; full V2 suite 550/550 passed** locally in 325.201 seconds. No hosted CI could start because of the private repository billing block.
- No paid provider requests, credentials, scheduler, production database writes or deployments.


### PR #96 merged — optional relay timer template only

- PR #96 merged into `v2-live-radar` as `2f45b947074b4221bc338ccfd2410394b881416c` after rebase onto the latest V2 head.
- Its repo-managed systemd timer/service templates target a ten-minute calendar cadence and are accompanied by seven offline contract tests.
- Validation on the exact rebased PR head: **7/7 focused timer tests and 557/557 full V2 tests passed locally** (351.012 seconds). `systemd-analyze calendar` parsed the ten-minute expression. `systemd-analyze verify` emitted only unrelated host warnings for netplan/snapd units.
- This merge only adds templates, tests and documentation. It does **not** install or enable the timer. Production Naukri timer remains inactive/dead/disabled with no future trigger, by owner choice. The app's 15-minute freshness guard remains unchanged. No relay workflow dispatch was triggered.

### Company Watch offline dry-run qualification — 18 November 2026

The corrected pinned manifest was dry-run from the current merged V2 checkout inside the production app image with container networking disabled. Exact hash matched `146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd`; parser returned 100 rows, 19 candidate_staged and 81 manual_review. The guarded dry-run reported zero company creates, links, verifications, activations, schedules, network requests or notifications. No SQLite file was created. This qualifies parsing/classification only; no runtime deploy or manifest import was performed, and production's current old candidates have not been altered.

### Source reliability refresh — 18 November 2026, 12:02 UTC

Read-only aggregate since the assessment start (17 November 20:59:46 UTC); final window cutoff remains 18 November 20:59:46 UTC:

| Source | Runs | Success | Non-success | HTTP 429 | Jobs seen | New jobs |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 345 | 344 | 1 | 0 | 145,543 | 5 |
| Darwinbox | 439 | 439 | 0 | 0 | 17,558 | 4 |
| Greenhouse | 531 | 531 | 0 | 0 | 61,003 | 2 |
| Keka | 433 | 433 | 0 | 0 | 50,278 | 1 |
| LinkedIn | 104 | 99 | 5 | 5 | 1,394 | 169 |
| Naukri | 180 | 142 | 38 | 0 | 44,259 | 102 |
| SmartRecruiters | 175 | 175 | 0 | 0 | 52,499 | 86 |
| Workable | 442 | 442 | 0 | 0 | 2,652 | 0 |
| Workday | 18 | 0 | 18 | 18 | 0 | 0 |
| **Total** | **2,667** | **2,605** | **62** | **23** | **375,186** | **369** |

- Workday continues to receive HTTP 429 on every observed run; the latest persisted cooldown is 300 seconds and runs have been about hourly. Leave the scheduler's rate-limit state untouched.
- LinkedIn's five 429s remain five within 104 runs; no manual probe or cooldown reset.
- Naukri's 38 non-successes are stale-feed rejections after the owner-paused publisher. Its latest three polls failed closed with `RuntimeError`; the publisher timer is still intentionally disabled. Do not treat these as failures in the independent ATS collectors or bypass the 15-minute freshness guard.
- Ashby has one isolated failure and 344 successes. Darwinbox, Greenhouse, Keka, SmartRecruiters and Workable remain successful in all runs in the window.
- JobBeeper health is HTTP 200; DB integrity is `ok`; active board/schedule counts remain 10/10; local snapshot checksums all verify.

This remains an interim checkpoint. Do not issue a final 24-hour acceptance until the window closes at 20:59:46 UTC.

### Next-release P2 feature documented — member-submitted shared career sources

- Created [issue #99](https://github.com/AvinashBhalla/job-beeper/issues/99) and `docs/MEMBER_SUBMITTED_SHARED_CAREER_SOURCES_NEXT_RELEASE.md`.
- Scope: any member can suggest a public careers URL; after validation and review it becomes one shared source in a global catalogue, polled once for all members. Submission attribution is retained separately; it must not create a per-member scraper.
- Initial fixtures recorded: Oracle Candidate Experience `egug.fa.us2.oraclecloud.com / CX_1` and `jpmc.fa.oraclecloud.com / CX_1001`.
- Static test against current V2 `detect_ats_board` returned `None` for both URLs. No live requests or job ingestion were made.
- Current manual candidate staging remains admin-only and candidate-only; it does not ingest jobs. Current member preferences contain no source URL list. Existing cross-source canonical-opportunity matching and one-per-canonical notification ledger are useful foundations, but `GET /api/jobs` still returns raw job rows without grouping by canonical opportunity, so duplicate cards are not yet guaranteed to collapse.
- Oracle integration caveat documented: Oracle's official HCM REST page labels `recruitingCEJobRequisitions` internal-use only and `recruitingJobSitePostedJobs` approved-Marketplace-partner only. A third-party October 28, 2026 write-up describes the unauthenticated Candidate Experience UI requests, but this is not an Oracle-supported public API guarantee. Terms/stability must be resolved before any production adapter.
- **Priority P2 / next release. Not current release and not P1.** No code, DB, member UI/API, provider registry, source schedule, production or deployment change was made for this request.
