# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-11 — PR #17 deployed; LinkedIn observation pending  
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, merge SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Latest operating update — 2026-10-11 (read this first)

### Confirmed: Telegram delivery restored
- On the Oracle VM `job-radar`, both `JOB_RADAR_TELEGRAM_BOT_TOKEN` and `JOB_RADAR_TELEGRAM_CHAT_ID` exist in the repository-root `.env`.
- Compose did **not** resolve those values when run without an explicit env file. The working form is:
  `sudo docker compose --env-file .env -f v2/docker-compose.yml ...`
- The user recreated only the `radar` container with `--env-file .env`; both values were then confirmed present in the running container. The app health endpoint returned `status=ok`, version `2.0.0`.
- The three retained queued LinkedIn notifications (HealthEdge, Scoutit, GeeksGod) were all confirmed `sent` with `last_error=None`. The older 37 queued notifications had been suppressed by user approval. Do not revisit or reverse that cleanup.
- Never print Telegram secrets. Continue to use presence-only checks.

### Archived previous blocker — Naukri relay freshness
The earlier relay cadence investigation and its workflow history are preserved in `docs/JOB_RADAR_HANDOVER.md`. The source relay was subsequently moved to the VM-owned 5-minute systemd timer and its latest supplied run succeeded. Do **not** resume the old “diagnose stale relay workflow” task unless new production evidence shows the feed has stalled again. The active task is the post-PR-#17 LinkedIn verification documented above, followed by dashboard/Telegram decision consistency.

## 1. Current state

Latest merged V2 code: `097131797ddfbdec40c8d9911c6d5bc5b7b8a3bb` — [PR #17](https://github.com/AvinashBhalla/job-beeper/pull/17) LinkedIn lower-pressure/backoff update. CI [run #38156008065](https://github.com/AvinashBhalla/job-beeper/actions/runs/38156008065) passed the syntax check and 71 unit tests. Earlier Greenhouse timestamp/parser work is historical; Greenhouse remains disabled.

Latest VM output supplied 2026-10-09:
- `/health` returned `status=ok`.
- LinkedIn last scan succeeded: 54 seen, 1 new, no error.
- Naukri last scan succeeded: 359 seen, 0 new, no error.
- Greenhouse dry run fetched 298 jobs across 3/3 successful boards. This was a direct collector/matcher preview: no database upsert and no Telegram sends.

### Source configuration

| Source | Enabled | Poll target | Current state |
|---|---:|---:|---|
| LinkedIn | Yes | 120s (new target; verify post-deploy cadence) | Health/config confirmed after rebuild; sustained 429 behavior still unverified |
| Naukri | Yes | 300s | Healthy at latest supplied check |
| Instahyre | No | 600s | Not validated for activation |
| Greenhouse | **No** | 900s | Code deployed; awaiting ingestion/dashboard freshness gate |

Runtime config is schema version 8. User-supplied `GET /api/config` after rebuilding confirms it and LinkedIn poll target 120s. Greenhouse boards are Coinbase (`coinbase`), Graviton Research Capital (`gravitonresearchcapital`), and Zocdoc (`zocdoc`). Clarifai and Veradigm Asia returned HTTP 404 from their candidate endpoints and were removed.

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

## 5. Blockers and next pipeline tasks (current priority order)

### P0 — Verify LinkedIn backoff after PR #17
1. Collect timestamped logs/source status about 12 minutes after the October 11 deployment; exact command is in the Current handoff section at the top.
2. Validate approximately 120-second poll cadence, actual attempted-request log counts, active cooldown blocking, and escalation after recurring 429s. Do not evade platform limits or raise concurrency.

### P1 — Align dashboard and Telegram
1. Trace the same fresh job across `/api/jobs`, matcher/evaluation, alertability, age and canonical dedupe rules, `notification_ledger` decision/status, Telegram claim/delivery, and frontend filters.
2. User expects score threshold 55% to mean every fresh new profile match at/above threshold is considered for Telegram, apart from explicitly documented legitimate exclusions (role/experience/location incompatibility, stale age, disabled notifications, already-alerted canonical duplicate, or delivery failure). Current unknown-experience alertability gate is the leading suspected discrepancy.
3. Add regression tests and make dashboard/Telegram consume a consistent decision path. Do not replay historical/suppressed alerts in bulk. Validate with a new fresh opportunity and its persisted ledger state. Do not start this fix until LinkedIn verification has been reviewed.

### P2 — Greenhouse freshness gate (deferred)
Greenhouse is deployed in code but remains disabled. Before trialing it, ensure old board listings with stale `first_published` timestamps cannot masquerade as newly fresh, add ingestion/ledger tests, then enable for a controlled trial only after P0/P1 are stable.

### P3 — Broader architecture and source roadmap
See `docs/JOBBEEPER_REFERENCE.md`. Collect broadly where source APIs/public boards permit, then normalize, preserve timestamps/stable IDs, dedupe to canonical opportunities, evaluate preferences, and route the same explainable decisions to the dashboard and Telegram. Expand one structured ATS source at a time; do not introduce unnecessary infrastructure or enable new feeds before reliability and alert consistency gates pass.

### P4 — Branch/release hygiene
1. **Completed 2026-10-09:** removed the five merged feature branches and two temporary documentation branches; remaining remote refs were confirmed as `main`, `naukri-relay`, and `v2-live-radar`. Do not remove the private `naukri-relay` branch yet; legacy consumers must be retired/redirected first.
2. Decide deliberately what to do with `main` and its legacy relay workflow. Production V2 work/deployments must explicitly target `v2-live-radar`.
3. Record PR/merge SHA, CI, deployed SHA when proven, health, runtime config, source status and log evidence after each release. Update both handover files after every prompt.

## 6. Release checklist

Before merge: topic branch cut from current `v2-live-radar`; regression tests added; V2 CI green.

After deployment: verify branch/SHA when available; Docker service up; `/health` HTTP 200; runtime config/source flags; source-status/logs; no stale or mismatched job alerts. **After every user prompt, update both `docs/JOB_RADAR_HANDOVER.md` and this file before ending the turn, even for an evidence-only/plan-only turn; label historical checklists so they cannot override the latest handoff.**


## Continuation prompt for the next chat
“You are continuing Job Radar V2. First read `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `docs/JOB_RADAR_HANDOVER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`. Mandatory rule: after every prompt, update both handover files, even if no code changes; describe the goal, evidence, edits/PR/CI/deployment proof, what you need me to run, and next action. PR #17 (`09713179`) is merged and Oracle config version 8 / LinkedIn poll 120s is confirmed, but post-deploy rate-limit behavior still needs the timestamped 12-minute observation. First analyze that output. Only after LinkedIn behavior is assessed, fix dashboard-vs-Telegram alert consistency: user expects every fresh new match scoring at least 55% to be considered for Telegram; inspect the currently enabled unknown-experience alert gate and notification ledger, add tests, avoid historical alert floods, and verify one fresh job end-to-end. Keep Greenhouse disabled, one issue at a time, no secrets, no LinkedIn limit evasion.”
