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

PR #87 updates the V2 pin and regression tests. Expected result: 100 rows, 92 enabled / 8 disabled, 19 candidate_staged / 81 manual_review. Old production candidates lever/mistral and greenhouse/soundhoundinc still need admin rejection after the corrected manifest is deployed and imported. No production import, SQL patch, link, verification, activation, or polling change has been made.

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

Six merged remote branches were deleted after verifying PRs #80–#85 were merged. The temporary source-fix branch for PR #89 was deleted after merge. Current remote branch count: five — main, v2-live-radar, docs/search-engine-ats-discovery-design-20261118 (PR #86), fix/company-watch-manifest-corrections-20261118 (PR #87), and docs/maintenance-checkpoint-20261118 (PR #88). Main and v2-live-radar were retained. The local production checkout was fetch-pruned but not pulled or reset.

## Checkouts intentionally preserved

- /home/ubuntu/job-beeper: clean working tree on v2-live-radar, still 782 commits behind origin at inspection. Not pulled, reset, rebuilt or deployed.
- /home/ubuntu/job-beeper-dev: dirty, 176 commits behind, with modified v2/config.json and untracked .env.save, .venv and config backup. Preserved untouched.
- /home/ubuntu/job-beeper-global-ats-test and /tmp/job-radar-source-observability: preserved; not modified.

## Open work

1. Wait for exact-head CI on PR #87 after the corrected source CSV; fix any failures before merging.
2. Review/merge PR #86 after the updated discovery design CI passes.
3. Do not deploy PR #87 or import its manifest until normal release gates and owner approval are satisfied.
4. When deployed, dry-run and import the corrected manifest, verify 10 registry boards / 10 schedules remain unchanged, then reject the two stale candidate keys through the admin review API.
5. Complete the 24-hour source reliability assessment at 20:59:46Z on 18 November.
6. Ask the owner to confirm the off-host backup draft and approve a maintenance reboot window.
7. Continue daily read-only VM, database, scheduler, source and GitHub monitoring. Keep Telegram/member-feature expansion out of scope.