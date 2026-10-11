# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-11  
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; older sections may describe superseded states. Use this document and the deployed commit for current status.



## Latest operating update — 2026-10-11 (read this first)

### Confirmed: Telegram delivery restored
- On the Oracle VM `job-radar`, both `JOB_RADAR_TELEGRAM_BOT_TOKEN` and `JOB_RADAR_TELEGRAM_CHAT_ID` exist in the repository-root `.env`.
- Compose did **not** resolve those values when run without an explicit env file. The working form is:
  `sudo docker compose --env-file .env -f v2/docker-compose.yml ...`
- The user recreated only the `radar` container with `--env-file .env`; both values were then confirmed present in the running container. The app health endpoint returned `status=ok`, version `2.0.0`.
- The three retained queued LinkedIn notifications (HealthEdge, Scoutit, GeeksGod) were all confirmed `sent` with `last_error=None`. The older 37 queued notifications had been suppressed by user approval. Do not revisit or reverse that cleanup.
- Never print Telegram secrets. Continue to use presence-only checks.

### Current immediate task: diagnose stale Naukri relay freshness
The user is working one change at a time and expects the next agent to read this file and the detailed `docs/JOB_RADAR_HANDOVER.md` before proceeding. The user's next message to the agent will include the output of the relay workflow inspection command (run list JSON) described below. Treat that message as live evidence and continue from it; do not ask the user to run the same command again unless necessary.

Read-only baseline collected on 2026-10-11:
- Radar `/health` worked. Source status showed LinkedIn and Naukri enabled; latest supplied scans had LinkedIn `jobs_seen=20, new_jobs=0` and Naukri `jobs_seen=328, new_jobs=0`, with no runtime error.
- Jobs table: LinkedIn 2,668 stored records, 372 discovered in the prior 24h, 25 in the prior hour, latest `discovered_at=2026-10-11T13:11:56Z`. Repeated LinkedIn guest-endpoint HTTP 429s occurred across query/location pairs. Recent scans generally returned about 10–25 unique jobs per scan; a few deep scans returned 30–35.
- Jobs table: Naukri 1,227 stored rows (historical rows, not the current feed size); 83 rows had a `discovered_at` within 24h and zero within six hours. Latest stored Naukri `discovered_at=2026-10-11T07:05:55.267174Z`.
- Direct read-only fetch of the public relay JSON returned `updated_at=2026-10-11T07:05:55.267174Z`, declared count 328, actual entries 328, 328 unique IDs/URLs and zero duplicate IDs. All 328 feed IDs were already in the radar DB; zero feed IDs were unknown. Thus the Oracle ingestion matches the current feed. The immediate evidence points upstream to the relay not refreshing frequently enough, not to a missing-ID ingestion bug.
- The user then ran a GitHub Actions relay-workflow listing and a 12-run history query. Workflow shown: `public-naukri-relay`, state `active`, ID `379327541`. All 12 returned runs had conclusion `success` and event `schedule`, branch `main`, SHA `9d564e016da2ec50c70ee8bde9f2726539167460`. Most recent run was #`38120124080`, created `2026-10-11T07:04:06Z`, updated `07:06:01Z`; the relay JSON was updated at `07:05:55Z`. Prior run starts shown included `2026-10-11T01:01:47Z`, `2026-10-10T22:13:33Z`, `18:54:55Z`, `14:44:49Z`, `08:39:36Z`, and `02:17:55Z`. These observed gaps are roughly 2h48 to 6h21, not a five-minute cadence. Do not assume the intended cron; inspect it in the relay repository first.
- The user's local time when this was checked was approximately 2026-10-11 18:47 IST; the relay payload was therefore over six hours old.

### Exact next-agent instructions
1. Start by reading this Knowledge Transfer document and `docs/JOB_RADAR_HANDOVER.md`. Then inspect the relay-run JSON the user sends in the new session.
2. Inspect the **separate repository** `AvinashBhalla/job-beeper-naukri-relay`, especially the active workflow YAML on `main`, the `schedule.cron`, any `if`/concurrency conditions, workflow status, source collection logic, and the exact path/branch where it publishes `naukri_relay.json`. Compare the configured cadence to the supplied run timestamps. Confirm whether scheduled runs really are missing/rare or whether the command/query hid other runs.
3. Do read-only checks first: current workflow YAML, recent run history including failed/cancelled runs and all events, latest relay file timestamp/count, and workflow logs for the most recent successful run. Do not infer that a successful Actions run means fresh results were collected; inspect logs and whether the JSON's `updated_at` changes per run.
4. Propose and make **one minimal, testable relay-side change** only after identifying the cause. Keep the existing payload schema and stable job identity intact. Do not edit the private radar ingestion code, enable new sources, widen LinkedIn concurrency, or redesign acquisition in the same change.
5. Validate by manually dispatching one relay run if safe and supported, checking the run conclusion/logs and confirming the public JSON's `updated_at` advances and the count/IDs are plausible. Then verify the Oracle radar sees that same new `updated_at` on its next scan, with no false-new Telegram alerts. Use a backup/branch/PR and tests appropriate to the relay repo; do not directly commit experimental code to production without verifying its workflow and delivery path.
6. Only after Naukri relay freshness has been verified, return to LinkedIn coverage: rate-limit-aware handling for observed HTTP 429s, coverage measurements, and comparison with JobBeeper's observable behavior. Current V2 LinkedIn behavior is already conservative (`LINKEDIN_SEARCH_WORKERS=1`, four fast query/location targets per scan, deep scan about every 900s, one deep page batch, no same-scan retry on 429, and skip deep pagination when the fast lane is rate-limited). Do not increase concurrency as a first response.
7. Preserve the user's preferred interaction mode: one issue/change at a time, evidence first, then deploy/test, and report only verified outcomes. Do not print secrets. Keep the Greenhouse collector disabled; it is not part of this session's current blocker.

### Copyable continuation prompt
“You are taking over Job Radar V2. First read `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOB_RADAR_HANDOVER.md` on branch `v2-live-radar`. Continue the latest 2026-10-11 handoff; do not restart the previous diagnostics. I will send you the JSON output showing the active `public-naukri-relay` workflow and its last 12 runs. Interpret that output, inspect the separate `AvinashBhalla/job-beeper-naukri-relay` repository's actual workflow YAML and logs, and find why the public feed's `updated_at` is stuck at `2026-10-11T07:05:55Z` despite reported successful scheduled runs. The 328 current feed entries all already exist in the radar DB, so do not patch private ingestion yet. First prove whether the cron cadence is configured incorrectly, scheduled runs are missing, or successful runs fail to collect/publish fresh jobs. Make one minimal relay-side fix only after diagnosis, validate the public JSON timestamp/count, then verify the Oracle radar consumes it. After the Naukri freshness problem is confirmed fixed, address LinkedIn coverage/429s as a separate task. One change at a time; no secrets in logs; keep Greenhouse disabled.”

## 1. Current state

Latest merged V2 code: `c2f2ce659ad1a6287318ffc1fc1036135577ce4b` — Greenhouse first-publication timestamps and UTC parser fix. Post-merge [V2 CI run #297](https://github.com/AvinashBhalla/job-beeper/actions/runs/37931422233) passed.

Latest VM output supplied 2026-10-09:
- `/health` returned `status=ok`.
- LinkedIn last scan succeeded: 54 seen, 1 new, no error.
- Naukri last scan succeeded: 359 seen, 0 new, no error.
- Greenhouse dry run fetched 298 jobs across 3/3 successful boards. This was a direct collector/matcher preview: no database upsert and no Telegram sends.

### Source configuration

| Source | Enabled | Poll target | Current state |
|---|---:|---:|---|
| LinkedIn | Yes | 60s | Healthy at latest supplied check |
| Naukri | Yes | 300s | Healthy at latest supplied check |
| Instahyre | No | 600s | Not validated for activation |
| Greenhouse | **No** | 900s | Code deployed; awaiting ingestion/dashboard freshness gate |

Runtime config is schema version 7. Greenhouse boards are Coinbase (`coinbase`), Graviton Research Capital (`gravitonresearchcapital`), and Zocdoc (`zocdoc`). Clarifai and Veradigm Asia returned HTTP 404 from their candidate endpoints and were removed.

## 2. Greenhouse findings and current blocker

Latest read-only VM dry run:
- Jobs fetched: 298.
- Publication time: 297 with minute precision, 1 unknown.
- Published in the configured 72-hour window: 10; older: 287; future: 0.
- Profile matches: 1; matches passing current alert policy: 0.
- Only match: Graviton Research Capital, “Software Engineer (2027 Graduate),” Gurugram. Its `first_published` value was `2026-09-01T06:25:41+00:00`, outside the 72-hour window, and its experience requirement was not extracted.
- The corrected location matcher rejected 190 remote postings outside configured location targets.

**Do not enable Greenhouse yet.** The collector fetches the full board. The existing “today” lifecycle is based on discovery time, so importing all 298 board listings may make older postings look newly discovered in the dashboard. Before activation, either add a tested source-posted freshness guard for Greenhouse ingestion or update the UI to clearly separate first-seen time from original posting time. Do not weaken `require_explicit_experience_for_alerts=true) to force alerts.

### Engineering lessons

- `Remote, India` must not act as an unrestricted global `Remote` wildcard. PR #8 fixed this; plain `Remote` intentionally remains global.
- Use `first_published` as the original posting timestamp when present. Never substitute `updated_at`, which may reflect later edits.
- ISO parsing originally lowercased the `Z` timezone suffix, making valid timestamps parse as unknown. The parser now preserves the raw ISO string and handles uppercase/lowercase `Z`; regression tests cover this.
- Runtime preferences persist in the Docker volume at `/data/config.json`. Changing repository defaults in `v2/config.json` does not overwrite that saved VM config. Use the protected config API/dashboard and verify `GET /api/config`.

## 3. Runtime and architecture

- Repo path on VM: `/home/ubuntu/job-beeper`.
- Compose file: `v2/docker-compose.yml`; service: `radar`; usual container: `v2-radar-1`; host port: `8000`.
- Docker volume: `radar-data`; database `/data/jobs.db`; runtime config `/data/config.json`; config token `/data/config_token`.
- Health: `curl -fsS http://127.0.0.1:8000/health`.
- Useful read APIs: `/api/config`, `/api/source-status`, `/api/daily-summary`, `/api/latency-summary?hours=1`.
- Pipeline: source collector → normalize → SQLite upsert → canonical opportunity/deduplication → matching/evaluation → freshness and alertability policy → notification ledger → Telegram.
- The Naukri relay is scheduled in its **separate repository**. The old VM cron that dispatched a private-repo relay workflow was removed. Do not reintroduce it.
- Never print or commit the config token, Telegram secrets, runtime config, private feed, or SQLite database.

## 4. Repositories and branch map

### Repositories
- [Private app repository](https://github.com/AvinashBhalla/job-beeper): current V2 deployment work is in `v2-live-radar`.
- [Separate Naukri relay repository](https://github.com/AvinashBhalla/job-beeper-naukri-relay): active scheduled relay/public feed. It is not the `naukri-relay` branch of the private app repository.

### Branches remaining in the private app repository

| Branch | Purpose and status | Action |
|---|---|---|
| `v2-live-radar` | Active V2 release/deployment branch. Current branch HEAD is `0327c746` (merged documentation/legacy-relay guidance). Latest application-code merge is `c2f2ce65`; the subsequent commit changes docs only. | **Keep.** All V2 work branches from here and merges back here. |
| `main` | GitHub default branch; 59 commits behind `v2-live-radar` at the branch inventory snapshot. It retains the older GitHub Actions/static-dashboard implementation. | **Keep for now.** Do not deploy V2 from it. Decide separately whether to promote/sync V2 or change the default branch. |
| `naukri-relay` | Legacy orphan feed branch in this private app repo, containing `dashboard/data/naukri_relay.json`. The old `main` collector reads it and `.github/workflows/naukri-relay.yml` can manually republish it. | **Keep for now.** Retire or redirect old `main` consumers/workflow before deleting it. It is not the current V2 relay. |

The separate active relay is [`AvinashBhalla/job-beeper-naukri-relay`](https://github.com/AvinashBhalla/job-beeper-naukri-relay). The private repo's `origin/HEAD` still points to `origin/main`.

### Merged implementation PRs### Merged implementation PRs
- [#5 Naukri relay cache busting](https://github.com/AvinashBhalla/job-beeper/pull/5) — `f91f047c`.
- [#6 Greenhouse public board source](https://github.com/AvinashBhalla/job-beeper/pull/6) — `1cfd55b2`.
- [#7 Validated Greenhouse board registry](https://github.com/AvinashBhalla/job-beeper/pull/7) — `b42193c6`.
- [#8 Country-aware remote matching](https://github.com/AvinashBhalla/job-beeper/pull/8) — `2074bdab`.
- [#9 Greenhouse publication timestamps and ISO parser fix](https://github.com/AvinashBhalla/job-beeper/pull/9) — `c2f2ce65`.

**Verified branch cleanup completed on 2026-10-09 from the Oracle VM.** After fast-forwarding to `0327c746`, the user successfully deleted these seven remote refs: `feat/greenhouse-first-published-timestamps`, `feat/greenhouse-public-board-source`, `fix/naukri-relay-cache-busting`, `fix/remote-location-country-qualification`, `fix/validate-greenhouse-board-registry`, `docs/current-job-radar-knowledge-transfer`, and `docs/keep-legacy-relay-branch-safe`. `git fetch --prune` then showed only `origin/main`, `origin/naukri-relay`, and `origin/v2-live-radar` (plus `origin/HEAD -> origin/main`). Do not repeat deletion of those refs; they are already gone. Keep `main` and the legacy `naukri-relay` dependency until the main/relay transition is deliberately completed.

## 5. Blockers and next pipeline tasks

### P0 — Fix ingestion/dashboard freshness semantics, then trial Greenhouse
1. Ensure stale first-published Greenhouse jobs are not presented as newly posted merely because they were discovered today. Choose a source-level freshness guard or an explicit UI distinction between first-seen and first-published time.
2. Add tests that stale board listings do not appear as fresh and do not queue notification-ledger entries.
3. Confirm Greenhouse stays disabled until the above lands.
4. After CI passes, enable only for a controlled trial. Observe at least one 15-minute cycle, then check source status, logs, inserted rows, recent matches, alertability, and notification ledger.

### P1 — Protect LinkedIn/Naukri reliability
1. Observe several consecutive LinkedIn scans: request counts, 429/failures, duration and useful new jobs. Do not increase concurrency based on a short clean sample.
2. Verify the public Naukri relay keeps refreshing and date-only Naukri postings never claim exact discovery latency.
3. Test Telegram end-to-end on a genuinely fresh and eligible posting; confirm one alert per canonical opportunity.

### P2 — Branch/release hygiene
1. **Completed 2026-10-09:** removed the five merged feature branches and two temporary documentation branches; remaining remote refs confirmed as `main`, `naukri-relay`, and `v2-live-radar`. Do not remove the private `naukri-relay` branch yet: the legacy `main` code reads it and its manual relay workflow can overwrite it. Retire or redirect that path first.
2. Decide deliberately what to do with `main` and its legacy relay workflow. It still references the private `naukri-relay` branch, so either retire/disable the legacy workflow and redirect the old consumer before deleting the branch, or keep the branch. Until the repository transition is complete, production work and deployments must explicitly target `v2-live-radar`.
3. After each release, record the merge SHA, deployed SHA, HTTP health result, runtime config and source-status evidence here.

### P3 — Add sources only after current flow is stable
Evaluate Lever and Ashby next, one at a time. Each must have its own opt-in flag, verified public board, source ID, timestamp precision, dedupe tests, per-board failure isolation, and alert-safety validation.

## 6. Release checklist

Before merge: topic branch cut from current `v2-live-radar`; regression tests added; V2 CI green.

After deployment: verify branch/SHA; Docker service up; `/health` HTTP 200; runtime config/source flags; source-status/logs; no stale or mismatched job alerts; update this handover only with evidence from actual output.
