# JobBeeper V2 production release qualification — 18 November 2026

**Status: PROMOTED — FINAL GATE PASSED (19 November 2026, 02:45 IST)**  
**Release commit:** `dda6d5757f4701ce916a94a48f7ec94d6297e51a`  
**Release tag:** `job-radar-prod-release:dda6d57`  
**Production baseline:** `job-radar-prod-release:472c2ee`

## 1. Release scope and exclusions

The candidate contains the merged V2 branch through commit `dda6d5757f4701ce916a94a48f7ec94d6297e51a`. Relative to the current production commit `472c2eef80bf34e0c87e9b1e65967181a7e698f5`, the application-code diff is limited to:
- `v2/radar.py`: add `search_engine_serp` to the allowed discovery provenance methods, and update the pinned Company Watch manifest path/source ref/SHA.
- `v2/data/company_watch_companies_2026-11-18.csv`: new 100-row corrected, pinned snapshot.

The branch also includes the already reviewed/merged SERP discovery adapter, clients, disabled coordinator/worker, offline benchmark and test modules; these are disabled/not scheduled and have no credentials. No paid requests have been made. The Naukri ten-minute timer template is repository-only and is not installed or enabled. The member-submitted shared career URL feature is P2/next-release issue #99 and is excluded.

No production database, source flags, board allowlist, member preference, Telegram setting or notification configuration has been changed during this qualification.

## 2. Exact-head validation

- Exact release checkout: `dda6d5757f4701ce916a94a48f7ec94d6297e51a`.
- Full V2 test suite: **557 passed, 0 failed**, `Ran 557 tests in 316.187s`, exit code 0.
- GitHub Actions run for the exact push head `44303242450` failed before executing a job step (`steps=[]`) because the private repository runner remains blocked by the account billing/spending restriction. Treat this as unavailable hosted CI, not a product test failure. Do not upgrade the plan or spend money to unblock it; the full local suite was run using the repository's `requirements-dev.txt`.
- No source or credential was fetched during the tests.

## 3. Release image

Built on the production VM from the exact release checkout using the existing local `python:3.12-slim` base image (no registry pull):
- Release tag: `job-radar-prod-release:dda6d57`
- Image ID: `sha256:bbf5252047ed2b3bbc8d06f7c51663e6deae4be28d9c82fdfc65e9a8b005ba5d`
- Size: 318,231,433 bytes
- Docker manifest digest: `sha256:bbf5252047ed2b3bbc8d06f7c51663e6deae4be28d9c82fdfc65e9a8b005ba5d`
- Existing rollback tag retained: `job-radar-prod-release:472c2ee`
- Rollback image ID: `sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c`

## 4. Isolated application smoke

A throwaway clone of the production database and runtime config was used. The candidate ran with `--network none`, a copied DB/config directory, and no production volume mount. The copied config had notifications disabled and global LinkedIn/Naukri disabled; the ten approved ATS board settings were retained. In the throwaway DB only, each schedule's `next_due_at` was moved to 2099 so the scheduler could initialize without attempting any collector requests.

Results:
- Application startup completed; log: `board scheduler: synchronized configured boards=10`.
- `GET /health`: HTTP 200.
- `GET /dashboard/`: HTTP 200.
- `GET /openapi.json`: HTTP 200.
- Throwaway DB `PRAGMA quick_check`: `ok`.
- Active registry boards / active schedules: **10 / 10**.
- Due board schedules during smoke: **0**.
- Container: no OOM, no restart.
- The test container and throwaway DB/config files were removed afterward.

An earlier minimal-config smoke also returned HTTP 200 on all three endpoints. The real-config smoke is the relevant scheduler/startup evidence.

## 5. Company Watch corrected manifest — isolated production-DB simulation

A fresh SQLite online-backup copy of production was used to test the exact production code path. Production was not modified.

Pinned manifest:
- SHA-256: `146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd`
- Source: `main@da7e42dbaaeee0a89ebdde92799aee8db7543ec6`
- Rows: 100; candidate staged: 19; manual review: 81; invalid: 0.

Dry-run returned the expected 100 / 19 / 81 counts and zero side effects. Import against the disposable production DB returned:
- candidates inserted: 2;
- candidates updated: 17;
- terminal candidates preserved: 0;
- employer records created: 0;
- boards linked/verified/activated: 0;
- schedules added: 0;
- network requests: 0;
- notifications: 0.

The two replacement candidates are `ashby/mistral.ai` and `workday/standard:search`. The superseded `lever/mistral` and `greenhouse/soundhoundinc` records were then rejected using the guarded review function; both returned `activated: false`. The 100 manifest audit rows were persisted in the clone. Final SQLite integrity was `ok`; employer count remained 10, active boards 10 and active schedules 10.

**Production still has the previous manifest import and old candidate statuses.** The corrected manifest has not been imported to production, and the two old candidates have not been rejected there. This remains the controlled post-promotion data step after the 24-hour reliability window closes.

## 6. Pre-release backup and rollback

Root-only pre-release artifact directory:

`/var/backups/job-radar-daily/release-dda6d57-20261118T2210IST`

Contents include:
- `production.sqlite3`: consistent SQLite online backup, 139,456,512 bytes, 28,001 jobs, 2 users, 10 active registry boards, 10 active schedules; `PRAGMA integrity_check=ok`.
- `config.json` and `config_token`.
- `runtime.env`: captured runtime environment values needed to recreate the current production container.
- `container-inspect.json`: prior container metadata.
- `production-compose.yml`: rollback compose referencing `job-radar-prod-release:472c2ee`.
- `candidate-compose.yml`: candidate compose referencing `job-radar-prod-release:dda6d57`.
- `rollback-image-id.txt`.
- `SHA256SUMS`: all pre-release artifacts verified; nine entries.

Directory mode is 0700 and files are 0600. Existing production data volume `v2_radar-data`, loopback binding `127.0.0.1:8000`, and `unless-stopped` restart policy are preserved by both compose definitions. Both rollback and candidate compose files pass `docker compose config --quiet`.

Rollback: restore the old compose file/image tag with the same `runtime.env` and external `v2_radar-data` volume, then verify app health and DB integrity. The pre-release DB is preserved separately and should not be restored unless there is actual DB corruption; a normal image rollback must reuse the current DB.

## 7. Live production and 24-hour reliability gate (interim pre-cutoff snapshot)

Production was not restarted or promoted during this qualification. Latest live check at 18 November 2026 16:47:21 UTC:
- App HTTP 200; container `v2-radar-1`, still on `job-radar-prod-release:472c2ee`.
- SQLite integrity `ok`; active registry / schedules **10 / 10**.
- Naukri relay timer: disabled/inactive/dead by owner choice.
- Daily local snapshot timer: enabled/waiting; latest checksum manifest passes.
- VM: 2 vCPU, about 1 GiB RAM; disk 28% used, approximately 33 GB free.

The source reliability window started `2026-11-17T20:59:46Z` and ends `2026-11-18T20:59:46Z` (19 November 2026, 02:29:46 IST). At 16:47:21 UTC, the window was still open.

Interim roll-up through 16:47 UTC:

| Source | Runs | Success | Non-success | HTTP 429 | Jobs seen* | New rows |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 453 | 452 | 1 | 0 | 191,240 | 6 |
| Darwinbox | 578 | 578 | 0 | 0 | 23,680 | 6 |
| Greenhouse | 696 | 696 | 0 | 0 | 79,874 | 2 |
| Keka | 570 | 570 | 0 | 0 | 66,170 | 1 |
| LinkedIn | 107 | 101 | 6 | 6 | 1,455 | 211 |
| Naukri | 237 | 142 | 95 | 0 | 44,259 | 102 |
| SmartRecruiters | 231 | 231 | 0 | 0 | 69,297 | 129 |
| Workable | 582 | 582 | 0 | 0 | 3,492 | 0 |
| Workday | 23 | 0 | 23 | 23 | 0 | 0 |
| **Total** | **3,477** | **3,352** | **125** | **29** | **479,467** | **457** |

*Jobs seen is poll observation volume, not unique job inventory.

Interpretation:
- Workday remains rate-limited on every attempt (23/23 HTTP 429). Its persisted cooldown is capped at 60 minutes; the latest run was 16:18:26 UTC and next due is 17:18:29 UTC. This has cut Workday attempt frequency from the former multi-thousand-request/day storm to roughly one request/hour, but Workday has not recovered jobs. Treat it as a controlled degraded source, not a successful source.
- LinkedIn has six 429 events in 107 runs, with 101 successful/partial-success runs. Its last completed scan at 14:07 UTC succeeded after the persisted long cooldown; do not reset cooldowns.
- Naukri's 95 non-success runs are expected stale-feed rejections after the owner intentionally paused the publisher. It ingested successfully before the pause (142 runs, 102 new rows). Do not resume the relay or bypass the 15-minute freshness guard.
- Darwinbox, Greenhouse, Keka, SmartRecruiters and Workable were successful in every observed run; Ashby had one isolated non-success.
- Continue read-only observation to the exact cutoff. The final assessment must preserve Naukri's intentional-pause distinction and report Workday as degraded if the 429s continue. Do not use this gate to justify manual probes or cooldown resets.

## 8. Final promotion result — 19 November 2026

**Gate decision: PASS. The candidate was promoted; no rollback was required.** This section supersedes the pre-cutoff interim roll-up and staged-only decision above.

### Promotion and runtime verification

- Promotion completed: 2026-11-18 21:15:35 UTC / 2026-11-19 02:45:35 IST.
- Production container: v2-radar-1.
- Image: job-radar-prod-release:dda6d57.
- Image ID/digest: sha256:bbf5252047ed2b3bbc8d06f7c51663e6deae4be28d9c82fdfc65e9a8b005ba5d.
- Rollback image retained: job-radar-prod-release:472c2ee, sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c.
- Startup completed; scheduler synchronized exactly 10 configured boards.
- /health, /dashboard/, /openapi.json: HTTP 200.
- Container running, restart count 0, OOMKilled false.
- Live SQLite quick_check: ok.
- Final live inventory: 28,048 jobs, 2 users, 10 employer companies, 10 active registry boards, 10 active schedules, 21 global ATS candidates.
- Active registry and schedule key sets match the pre-release backup exactly. No board, employer, source flag or schedule was added or removed.
- Runtime config SHA-256 remains ec78fbf2607b9b9b06b4dd0e0bcdfb5417324dda3f498916c86760a0a6804e81.
- Candidate and rollback Compose files had both passed docker compose config validation before promotion. External volume v2_radar-data, loopback port 127.0.0.1:8000 and unless-stopped policy were preserved.

### Final exact 24-hour source window

Query bounds: started_at >= 2026-11-17T20:59:46Z AND started_at < 2026-11-18T20:59:46Z. Window closed at 2026-11-18 20:59:46 UTC / 2026-11-19 02:29:46 IST. These are the final live DB results, not the earlier 16:47 UTC interim snapshot.

| Source | Runs | Success | Non-success | HTTP 429 | Request errors | Jobs seen | New rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ashby | 549 | 548 | 1 | 0 | 1 | 231,905 | 11 |
| Darwinbox | 701 | 701 | 0 | 0 | 0 | 29,215 | 6 |
| Greenhouse | 846 | 846 | 0 | 0 | 0 | 97,050 | 5 |
| Keka | 692 | 692 | 0 | 0 | 0 | 80,322 | 1 |
| LinkedIn | 111 | 104 | 7 | 7 | 0 | 1,503 | 231 |
| Naukri | 287 | 142 | 145 | 0 | 0 | 44,259 | 102 |
| SmartRecruiters | 280 | 280 | 0 | 0 | 0 | 83,997 | 145 |
| Workable | 706 | 706 | 0 | 0 | 0 | 4,236 | 0 |
| Workday | 27 | 0 | 27 | 27 | 0 | 0 | 0 |
| **Total** | **4,199** | **4,019** | **180** | **34** | **1** | **572,487** | **501** |

Interpretation and persisted state:
- Workday is still degraded, not recovered. All 27 window attempts returned HTTP 429. The persisted host cooldown remained capped at 3,600 seconds. The first naturally scheduled post-promotion poll ran at 21:18:45 UTC, returned another 429, and set cooldown_until and next_due_at to 2026-11-18T22:18:46.345895Z. The host counter is now 28. No manual probe or cooldown reset was made.
- LinkedIn had 7 HTTP 429 events (5 partial-rate-limited and 2 rate-limited) and 104 successful runs. Its latest persisted event is 2026-11-18T18:16:04.375728Z with a 14,400-second cooldown. Candidate startup logged successful restoration of the persisted breaker with 3,612 seconds remaining at boot. No cooldown was reset.
- Naukri had 145 RuntimeError failures after the owner-paused publisher stopped refreshing its feed, plus 142 earlier successful runs and 102 new rows. The persisted source feed reports an unchanged snapshot; the Naukri relay timer and service remain inactive/dead and the timer remains disabled. These are treated as the known owner-pause/stale-feed condition, not a new release regression. The 15-minute freshness guard was not changed.
- Darwinbox, Greenhouse, Keka, SmartRecruiters and Workable were 100% successful. Ashby had one isolated RuntimeError and 548 successful runs.
- Jobs seen is poll observation volume, not unique inventory.

### Company Watch production correction

Candidate runtime reported the exact pinned path /app/v2/data/company_watch_companies_2026-11-18.csv, source ref main@da7e42dbaaeee0a89ebdde92799aee8db7543ec6 and SHA-256 146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd.

The production runtime dry-run used payload {"dry_run": true} and returned 100 rows: 19 candidate_staged, 81 manual_review, 0 invalid. It reported zero companies created, boards linked, verified, activated, scheduled, network requests or notifications.

Before production import, the same candidate code was run against a fresh online-backup copy of the current production DB. The complete simulated import/rejection sequence passed, including preservation checks for all existing candidates. Production import then ran at 2026-11-18 21:17:20.785205 UTC / 2026-11-19 02:47:20.785 IST via radar.import_company_watch_manifest({}):

- Candidate inserted: 2.
- Candidate updated: 17.
- Terminal candidates preserved: 0.
- Audit: 100 rows, 19 candidate_staged, 81 manual_review, 0 invalid.
- Replacement candidates present and still review-only/discovered: ashby/mistral.ai and workday/standard:search.
- The only two obsolete candidates rejected through radar.review_global_ats_candidate after resolving IDs by provider and board_key: lever/mistral and greenhouse/soundhoundinc. Both returned activated=false.
- Final candidate statuses: 19 discovered, 2 rejected. All other existing candidate IDs, statuses and linkage fields were unchanged; the two replacements remain unlinked.
- Employers remain 10; active boards/schedules remain 10/10 with exact original keys.
- Company records created, boards linked, verified, activated, schedules created, network requests and notifications: all 0.
- Notification ledger remained at 27,725 rows.
- Manifest audit and all 100 row records match the pinned SHA; SQLite quick_check remains ok.

### Preserved controls and recovery

- Naukri relay timer: inactive/dead/disabled; service inactive/dead. No relay dispatch.
- SERP coordinator: no crawl/run recorded, zero discovery runs, no host budget entries, no SERP/search API credential variables present, and no paid requests or spend.
- Member-submitted career URL feature issue #99 remains P2 for a later release.
- Source flags and runtime config are unchanged; LinkedIn, Naukri and the nine approved ATS source flags retain their pre-release values.
- Release recovery bundle remains root-only at /var/backups/job-radar-daily/release-dda6d57-20261118T2210IST. All nine SHA256SUMS entries verify. The consistent pre-release SQLite backup has integrity ok and 28,001 jobs, 2 users, 10 employers, 10 active boards and 10 active schedules.
- Daily snapshot manifest was independently verified from /var/backups/job-radar-daily; all five entries pass.
- The old production image remains tagged and available for image rollback. No DB restore was needed.

### Final activity log

- Confirmed the six commits after the candidate changed documentation only; no runtime, test, dashboard, deploy or CSV file changed.
- Rechecked exact rollback/candidate image IDs, both Compose files, the nine-entry recovery manifest, five-entry daily snapshot manifest, config hash, source flags, exact board/schedule keys, timers and health endpoints.
- Recomputed the complete source_runs window using the exact requested inclusive/exclusive timestamps.
- Re-ran the corrected Company Watch import and rejection simulation on a fresh disposable copy of the current production DB using the candidate image.
- Promoted the exact candidate image and verified startup, HTTP endpoints, SQLite integrity, board scheduler, config hash and persisted LinkedIn/Workday cooldown state.
- Executed the production Company Watch dry-run, import and two guarded rejections; verified no activation, linking, schedule, employer, network or notification side effects.
- Final verification at 2026-11-18 21:19:06 UTC / 2026-11-19 02:49:06 IST: candidate running, zero restarts/OOM, endpoints 200, DB integrity ok, 10 active boards and schedules, Naukri paused, SERP disabled, rollback image retained.
