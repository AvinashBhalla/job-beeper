# JobBeeper V2 production release qualification — 18 November 2026

**Status: RELEASE CANDIDATE STAGED — NOT YET PROMOTED**  
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

## 7. Live production and 24-hour reliability gate

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

## 8. Promotion decision and exact remaining work

The technical release candidate is built, unit-tested, smoke-tested, backed up and has a validated rollback config. GitHub-hosted CI is unavailable because of the account billing restriction; local exact-head validation is 557/557.

**Do not promote before the 24-hour source window closes at 20:59:46 UTC.** At/after the cutoff:
1. Read the final exact source-run roll-up and verify the Workday cooldown/next due, LinkedIn status, other ATS success rates, Naukri intentional pause, and production app/DB health.
2. If no new material regression exists, promote with the prevalidated candidate compose. Preserve the same external data volume and runtime.env. The existing production image remains the rollback target.
3. After startup, verify `/health`, dashboard, OpenAPI, DB quick_check, 10 active registry boards, 10 active schedules, source flags and persisted cooldowns. Do not change any source allowlist or schedule.
4. Run corrected Company Watch dry-run against production and verify the exact pinned hash, then import the 100-row manifest. Reject only the old `lever/mistral` and `greenhouse/soundhoundinc` candidates through the guarded review path (look up by provider/key; never rely on hard-coded IDs). Verify 10 companies, 10 active boards, 10 active schedules; zero activated candidates/new schedules/notifications.
5. Watch logs and source_runs after promotion. Keep Naukri paused, SERP coordinator disabled, no paid credentials/calls, and member-submitted URL P2 feature out of release.

If the final reliability report shows a new material regression or the candidate fails its post-start checks, do not promote; keep the current healthy production image running and document the blocker.

## 9. Activity log

- Reviewed current production image and V2 release diff against the exact base commit.
- Ran exact-head full V2 suite: 557/557 passed.
- Built candidate image on the production VM and recorded image ID/digest.
- Ran candidate in network-isolated container; with sanitized real production config it initialized and synchronized exactly 10 configured boards; health, dashboard and OpenAPI all returned HTTP 200; no board was due and no request was sent.
- Removed the isolated smoke container, copied database and config.
- Created root-only production database/config/runtime/compose/inspection backup and verified all checksums.
- Validated both candidate and rollback Compose configurations with the exact production volume/port/restart behavior.
- Simulated corrected Company Watch dry-run/import/rejection against a production DB copy; no live DB writes were made.
- Verified production remains healthy and unchanged at the current release base.

### Scheduled final gate

A one-time JobBeeper Release Gate task is scheduled for **19 November 2026, 02:40 IST** (10 minutes after the 24-hour cutoff). Task ID: `6afdd8f95b208191857e3074d1f49db6`. It will recalculate the final source-run window, verify the exact staged candidate and pre-release backup, and promote/import only if every explicit gate passes. Any material regression, incomplete window, checksum failure, code change beyond docs after the candidate build, or post-start failure must stop the release without changing production. Naukri stays paused and paid SERP stays disabled.
