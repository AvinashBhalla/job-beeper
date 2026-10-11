# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-11 — PR #21 and PR #22 merged; config v10 deployment pending  
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, merge SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Latest operating update — 2026-10-11 (read this first)

### LinkedIn after PR #17: cadence/cooldown verified; source still occasionally returns 429
- PR #17 (`097131797ddfbdec40c8d9911c6d5bc5b7b8a3bb`) merged and deployed. CI [run #38156008065](https://github.com/AvinashBhalla/job-beeper/actions/runs/38156008065) passed 71 tests. Runtime config after rebuild reported version 8, LinkedIn polling 120 seconds.
- User's timestamped trace: deep scan at `16:39:22.293Z` (8 attempts / 39 unique jobs), fast scans at `16:41:10.867Z` and `16:43:10.873Z` (4 attempts each), 429 at `16:45:04.912Z` after only 2 attempted search targets, then scans at `16:50:15.296Z` and `16:52:15.513Z`. This indicates the 300-second cooldown was respected and 120-second scan cadence resumed. Source status at `16:52:30.482Z`: 22 seen, 1 new, no error.
- Do not call this “429 fixed”: a 429 still happens. The first event after restart had streak 1, so 10/20/30-minute escalation is not yet confirmed in production. If another 429 occurs within one hour, check whether it escalates. Do not raise concurrency or evade source limits.

### Current implementation under review: dashboard / Telegram consistency
[PR #19](https://github.com/AvinashBhalla/job-beeper/pull/19) merged as `05e1a19374b7cca830cb0cd442743b5f3d0468be`; latest-head [CI run #38159529440](https://github.com/AvinashBhalla/job-beeper/actions/runs/38159529440) passed compile and 74 tests. Production remains config version 8 until the user pulls/rebuilds; actual deployment is not yet verified.
- Verified reason for missed alerts: config had `match_threshold=55` and `require_explicit_experience_for_alerts=true`. `match_details()` could return a true match at/above threshold with unknown experience, while `alertability_details()` blocked Telegram eligibility with a second hidden gate.
- Another consistency issue: dashboard `/api/jobs` recalculated matcher and alertability at read time; Telegram consumes stored `job_evaluations` plus `notification_ledger`. The dashboard did not expose ledger status/reason. PR #19 makes its response use the same persisted evaluation/canonical-ledger state, adds per-job Telegram status/reason badges, and makes a 55%+ threshold filter include only genuine `likely_match` opportunities.
- PR #19 removes the unknown-experience-only veto. Explicit incompatible experience is still rejected by the matcher; unknown experience is neutral. Config schema becomes v9 and migrates the old switch to false. Its startup migration suppresses only older pending notifications specifically blocked by the old gate and older than 10 minutes, to avoid bulk historical alert replay; recent pending matches remain eligible.
- The first CI run exposed two stale assertions dependent on the retired gate; these were corrected to test threshold-only alerts and the real notifications-disabled case. Final merged-head CI run #38159529440 passed all 74 tests. **Next, have the user deploy the merge and verify live behavior** using the exact commands in the latest handoff. Confirm config schema 9, health, persisted evaluation/ledger data, and a current qualifying match's Telegram state; never claim deployment from CI alone.

### Previously confirmed: Telegram delivery restored
- Compose on the Oracle VM must use `--env-file .env`: `sudo docker compose --env-file .env -f v2/docker-compose.yml ...`.
- Three retained queued notifications (HealthEdge, Scoutit, GeeksGod) had previously been confirmed sent; the older 37 queued notifications had been suppressed by user approval. Do not restore/replay that historical backlog.
- Never display Telegram secrets; use presence-only checks.

### Previous Naukri relay blocker is archived
The old relay cadence investigation is in `docs/JOB_RADAR_HANDOVER.md`. The relay now has a VM-owned five-minute systemd timer; the latest supplied run was healthy. Do not restart the old task without evidence of a new feed stall.


## 1. Current state

Latest merged V2 code includes PR #19, merge `05e1a19374b7cca830cb0cd442743b5f3d0468be`; CI [run #38159529440](https://github.com/AvinashBhalla/job-beeper/actions/runs/38159529440) passed 74 tests. User supplied a healthy config-v9 deployment at `/health`, threshold 55, explicit experience alert gate false, and 454 jobs / 26 qualifying matches. Several old candidates are intentionally suppressed to avoid a migration-time notification flood. Free-first LinkedIn request-budget PR #21 has merged as `6c93473844cd469493a0c61acf1477ba20252d69`; latest CI #38161863816 passed 76 tests. It changes the config target to version 10 / LinkedIn poll 180s, but production is still v9 until the user rebuilds. Exact commands and output expectations are at the top of `docs/JOB_RADAR_HANDOVER.md`.

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

**Do not enable Greenhouse yet.** The collector fetches the full board. The existing “today” lifecycle is based on discovery time, so importing all 298 board listings may make older postings look newly discovered in the dashboard. Before activation, add a tested source-posted freshness guard or clearly distinguish first-seen and original posting time. The separate explicit-experience alert gate is being removed by PR #19 for threshold consistency; keep explicit incompatible-experience rejection in the matcher. This does not resolve Greenhouse's stale-board risk.

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

### Completed P0 — LinkedIn post-deploy verification
The user-supplied 2026-10-11 timestamped log confirms the 120s cadence and five-minute cooldown was respected. A 429 still occurred once, so watch for another event within an hour to prove the escalating backoff. Do not raise concurrency or evade limits.

### P0 — Deploy and verify merged dashboard / Telegram consistency fix
1. PR #19 is merged as `05e1a19374b7cca830cb0cd442743b5f3d0468be`; CI [#38159529440](https://github.com/AvinashBhalla/job-beeper/actions/runs/38159529440) passed 74 tests. Production deployment is not yet confirmed.
2. Have the user pull `v2-live-radar` and rebuild the `radar` service using explicit `--env-file .env`; use the exact copyable diagnostic in `docs/JOB_RADAR_HANDOVER.md`.
3. Verify health, config schema 9 / threshold 55 / deprecated gate false, and per-job `likely_match`, `alertable`, `notification_status`, and decision reasons. With threshold ≥55, the dashboard filter requires a real profile match; its Telegram status comes from the same persisted evaluation/canonical ledger as the worker.
4. Confirm a fresh qualifying opportunity is queued/sent and dashboard state agrees with the ledger/Telegram, with no old pending-message burst. Preserve incompatible experience rejection, freshness, notification-off behavior, canonical dedupe and delivery-failure visibility.

### P1 — Greenhouse freshness gate (deferred)
Greenhouse stays disabled. Before a controlled trial, ensure old board listings with stale `first_published` do not masquerade as newly fresh; add source-ingestion/ledger tests. Enable only after alert consistency and source freshness are stable.

### P2 — Broader architecture and source roadmap
See `docs/JOBBEEPER_REFERENCE.md`. Continue source-specific collection → normalization / stable timestamps → canonical dedupe → matching → freshness and eligibility → common decision to dashboard + Telegram. Expand one structured ATS source at a time and only after reliability/alertability gates pass. Avoid premature infrastructure.

### P3 — Branch/release hygiene
1. Completed 2026-10-09: removed the previously merged feature and temporary documentation branches. Keep private `naukri-relay` and `main` until legacy consumers are deliberately retired/redirected.
2. V2 development/deployments target `v2-live-radar`, not default `main`.
3. Every release records PR, merge SHA, CI, deployment proof, config, source health and relevant logs in both handover documents. Update both handover documents after every user prompt.

## 6. Release checklist

Before merge: topic branch cut from current `v2-live-radar`; regression tests added; V2 CI green.

After deployment: verify branch/SHA when available; Docker service up; `/health` HTTP 200; runtime config/source flags; source-status/logs; no stale or mismatched job alerts. **After every user prompt, update both `docs/JOB_RADAR_HANDOVER.md` and this file before ending the turn, even for an evidence-only/plan-only turn; label historical checklists so they cannot override the latest handoff.**


## Continuation prompt for the next chat
“You are continuing Job Radar V2. First read `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `docs/JOB_RADAR_HANDOVER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`. Mandatory rule: after every prompt, update both handover files, even if no code changes; describe the goal, evidence, edits/PR/CI/deployment proof, what you need me to run, and next action. PR #17 (`09713179`) is merged and Oracle config version 8 / LinkedIn poll 120s is confirmed, but post-deploy rate-limit behavior still needs the timestamped 12-minute observation. First analyze that output. Only after LinkedIn behavior is assessed, fix dashboard-vs-Telegram alert consistency: user expects every fresh new match scoring at least 55% to be considered for Telegram; inspect the currently enabled unknown-experience alert gate and notification ledger, add tests, avoid historical alert floods, and verify one fresh job end-to-end. Keep Greenhouse disabled, one issue at a time, no secrets, no LinkedIn limit evasion.”


## Latest continuation prompt — 2026-10-11
“You are continuing Job Radar V2. Read both handover documents and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handovers after every user prompt. PR #19 merged as `05e1a19374b7cca830cb0cd442743b5f3d0468be`; latest CI [#38159529440](https://github.com/AvinashBhalla/job-beeper/actions/runs/38159529440) passed 74 tests, but production deployment is not confirmed. Ask the user to pull `v2-live-radar`, rebuild using `--env-file .env`, and send health/config/schema-9/qualifying-job status output from the current handoff. Verify a current match at ≥55% gets queued/sent and the dashboard badge agrees with persisted notification ledger and Telegram. No historical alert burst; retain incompatible-experience rejection, freshness, canonical dedupe, notifications-disabled policy, and keep Greenhouse disabled.”


## Free-first LinkedIn access and request policy
User asked to prioritize free/self-built improvements and defer paid plans. LinkedIn's official [User Agreement](https://www.linkedin.com/legal/user-agreement) and [scraping-software policy](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software) prohibit scraping/crawlers and bypassing usage limits, so don't rotate residential proxies, evade CAPTCHAs, or disguise traffic. Direct public guest-endpoint access is best-effort and can still be blocked; no free or paid solution is guaranteed to reproduce exactly the same LinkedIn results.
- [PR #21](https://github.com/AvinashBhalla/job-beeper/pull/21) code/test commit `644180cba5a8ccfc17399d7bc0070d319e7c41bf` passed [CI run #38161564620](https://github.com/AvinashBhalla/job-beeper/actions/runs/38161564620), compile plus 76 tests. Initial CI exposed a stale test assumption about four targets per scan; it was corrected to verify full rotation across eight two-target scans. This doc update moves the PR head, so check latest CI before merge. Request policy: spacing 4s, one detail worker, two targets per scan, deep pagination every 30m and config v10 polling at 180s; preserve global cooldown/backoff and `Retry-After`.
- Free coverage should come next from authorized public company career / ATS board sources (one at a time), not by circumventing LinkedIn controls. Greenhouse remains disabled until old board listing freshness is safe. Paid actors/proxies remain deferred and require terms/budget review if revisited.

## Workflow and branch cleanup / promotion to main
The workflow inventory was inspected on both `main` and `v2-live-radar`. [PR #22](https://github.com/AvinashBhalla/job-beeper/pull/22) merged as `8eae61f2605c14903bccbc25c1a95d438e3a9f79`; CI [#38162375556](https://github.com/AvinashBhalla/job-beeper/actions/runs/38162375556) passed 76 tests. The V2 branch now retains only `.github/workflows/v2-ci.yml`. `main` intentionally remains unchanged and still has the four old workflows pending the eventual V2 promotion PR.
- Known remote branch names include active `v2-live-radar`, default `main`, legacy `naukri-relay`, merged-topic candidates `fix/dashboard-telegram-alert-consistency`, `fix/linkedin-lower-pressure-cooldown`, `fix/linkedin-rate-limit-backoff`, `fix/prevent-posted-after-discovered`, `docs/current-handover-rule-20261011`, `docs/record-alert-consistency-merge-20261011`, and current PR #21 topic branch. Check merged PR metadata before deleting any. Keep `main`, `v2-live-radar`, and legacy `naukri-relay` until the main promotion.
- Promotion decision: once PR #21 is deployed, LinkedIn request/new-job yield is measured, and the fresh-match dashboard/notification/Telegram path is verified, merge workflow cleanup and create a dedicated reviewed PR from `v2-live-radar` into `main`. The promotion PR must include V2 source, updated docs, and V1 workflow/root-artifact retirement, retain V2 CI, and keep static Pages disabled. Check CI on `main`; do not switch VM deploy ref or default branch until deliberate cutover proof.


### Copyable next-session prompt
“You are continuing Job Radar V2. Read both handover files and `docs/JOBBEEPER_REFERENCE.md`. Mandatory rule: update both handovers after every user prompt. Latest production v9 output confirms healthy V2, threshold 55 / explicit-experience gate false and 26 qualifying matches, with older migration candidates intentionally suppressed. PR #21 is the free-first LinkedIn request-volume reduction. Check CI; if green merge and ask the user to deploy, verify config v10 / 180s poll, then observe request attempts/429s/cooldowns/new jobs for 20–30 minutes. Do not use proxies/CAPTCHA bypass to evade LinkedIn terms. After that, remove only audited V1 manual/static workflows in a separate PR (retain V2 CI), clean only verified merged topic branches, and then prepare a dedicated v2-live-radar→main promotion PR after end-to-end fresh alert verification. Keep Oracle deployment ref unchanged during main promotion.”


### Current continuation prompt
“You are continuing Job Radar V2. Read both handover documents and `docs/JOBBEEPER_REFERENCE.md`. PR #21 merged as `6c93473844cd469493a0c61acf1477ba20252d69`, CI #38161863816 passed 76 tests; production is still on config v9. User must pull/rebuild and confirm config v10/LinkedIn poll 180s, then provide 20–30 minutes of timestamped LinkedIn event/yield logs and status. Workflow cleanup branch `chore/remove-legacy-v1-workflows` removes Pages, legacy V1 job-watch, private Naukri-relay and check-sources workflows from the V2 branch but keeps V2 CI; inspect CI and create/merge PR #22. Verified merged PRs #15–#21 have obsolete topic heads to delete after verifying no unmerged work; branch deletion must be done via GitHub UI/CLI. Prepare a dedicated V2-to-main promotion only after live alert and request-yield verification plus workflow cleanup. No LinkedIn proxy/CAPTCHA evasion; free authorized ATS/career sources first. Update both handover docs after every user prompt.”


## Latest verified cleanup state — 2026-10-11
- PR #21 merged as `6c93473844cd469493a0c61acf1477ba20252d69`; CI #38161863816 passed 76 tests. The new request budget needs deployment: config version 10, LinkedIn poll 180s, followed by 20–30 minutes of rate/freshness observation and one fresh qualifying alert verification.
- PR #22 merged as `8eae61f2605c14903bccbc25c1a95d438e3a9f79`; CI #38162375556 passed 76 tests. `v2-live-radar` now retains only V2 CI. `main` is intentionally unchanged and still has its legacy workflows pending promotion.
- PR #15–#21 topic heads are merged candidates for deletion after checking remote refs/extra commits; keep `main`, `v2-live-radar` and `naukri-relay`. Commands are in the detailed handover.
- Promote to main after PR #21 is deployed/observed, a fresh match proves dashboard/ledger/Telegram agreement, and branch/workflow cleanup is complete. Use a separate reviewed PR; do not switch the VM deployment ref/default branch until CI and smoke tests pass.
