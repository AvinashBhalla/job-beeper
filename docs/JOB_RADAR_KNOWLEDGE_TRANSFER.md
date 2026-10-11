# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-11 — PR #17 LinkedIn cadence verified; PR #19 alert consistency fix under review  
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, merge SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Latest operating update — 2026-10-11 (read this first)

### LinkedIn after PR #17: cadence/cooldown verified; source still occasionally returns 429
- PR #17 (`097131797ddfbdec40c8d9911c6d5bc5b7b8a3bb`) merged and deployed. CI [run #38156008065](https://github.com/AvinashBhalla/job-beeper/actions/runs/38156008065) passed 71 tests. Runtime config after rebuild reported version 8, LinkedIn polling 120 seconds.
- User's timestamped trace: deep scan at `16:39:22.293Z` (8 attempts / 39 unique jobs), fast scans at `16:41:10.867Z` and `16:43:10.873Z` (4 attempts each), 429 at `16:45:04.912Z` after only 2 attempted search targets, then scans at `16:50:15.296Z` and `16:52:15.513Z`. This indicates the 300-second cooldown was respected and 120-second scan cadence resumed. Source status at `16:52:30.482Z`: 22 seen, 1 new, no error.
- Do not call this “429 fixed”: a 429 still happens. The first event after restart had streak 1, so 10/20/30-minute escalation is not yet confirmed in production. If another 429 occurs within one hour, check whether it escalates. Do not raise concurrency or evade source limits.

### Current implementation under review: dashboard / Telegram consistency
[PR #19 — Align dashboard and Telegram alert decisions with match threshold](https://github.com/AvinashBhalla/job-beeper/pull/19) is open at this snapshot; check CI and merge status live. Production is still on config version 8 / PR #17 until this PR is merged and the user rebuilds the container.
- Verified reason for missed alerts: config had `match_threshold=55` and `require_explicit_experience_for_alerts=true`. `match_details()` could return a true match at/above threshold with unknown experience, while `alertability_details()` blocked Telegram eligibility with a second hidden gate.
- Another consistency issue: dashboard `/api/jobs` recalculated matcher and alertability at read time; Telegram consumes stored `job_evaluations` plus `notification_ledger`. The dashboard did not expose ledger status/reason. PR #19 makes its response use the same persisted evaluation/canonical-ledger state, adds per-job Telegram status/reason badges, and makes a 55%+ threshold filter include only genuine `likely_match` opportunities.
- PR #19 removes the unknown-experience-only veto. Explicit incompatible experience is still rejected by the matcher; unknown experience is neutral. Config schema becomes v9 and migrates the old switch to false. Its startup migration suppresses only older pending notifications specifically blocked by the old gate and older than 10 minutes, to avoid bulk historical alert replay; recent pending matches remain eligible.
- Regression coverage is being added for unknown experience matching, config v9 migration, no historical backlog replay, and dashboard API/ledger consistency. **Do not deploy until CI is green and PR #19 is merged.** Then the user should pull/rebuild and share health, config version, plus a current qualifying job's API and notification-ledger state. Confirm actual Telegram delivery/status agrees; never claim this from CI alone.

### Previously confirmed: Telegram delivery restored
- Compose on the Oracle VM must use `--env-file .env`: `sudo docker compose --env-file .env -f v2/docker-compose.yml ...`.
- Three retained queued notifications (HealthEdge, Scoutit, GeeksGod) had previously been confirmed sent; the older 37 queued notifications had been suppressed by user approval. Do not restore/replay that historical backlog.
- Never display Telegram secrets; use presence-only checks.

### Previous Naukri relay blocker is archived
The old relay cadence investigation is in `docs/JOB_RADAR_HANDOVER.md`. The relay now has a VM-owned five-minute systemd timer; the latest supplied run was healthy. Do not restart the old task without evidence of a new feed stall.


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

### P0 — Finish dashboard / Telegram alert consistency (PR #19)
1. Read [PR #19](https://github.com/AvinashBhalla/job-beeper/pull/19), inspect current CI status and diff, and fix any failing tests before merge. It must be green before deployment.
2. Ensure the 55% threshold means a true profile match at/above 55% is alert-eligible even when experience is unknown. Explicit incompatible experience, excluded roles/titles, incompatible location, age/freshness, notifications disabled, canonical dedupe, and delivery failure remain valid reasons for no send.
3. Dashboard `/api/jobs` must expose the same stored `job_evaluations` and canonical `notification_ledger` decisions consumed by Telegram. Cards should show sent/queued/pending/failed/suppressed status plus reasons. When selecting the configured threshold or higher, filter to `likely_match=true`, not score alone.
4. Never replay the historical/suppressed backlog in bulk. Schema-v9 migration suppresses only old pending rows whose previous reason explicitly says they were blocked by the obsolete experience-presence gate; current pending entries remain eligible.
5. After merge, user pulls/rebuilds on Oracle. Verify health, config version 9 / threshold setting, a genuine current match, `/api/jobs` fields, canonical ledger state, and Telegram status. Record the merge SHA and deployment evidence only after received output.

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
“You are continuing Job Radar V2. Read `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, the latest section of `docs/JOB_RADAR_HANDOVER.md`, and `docs/JOBBEEPER_REFERENCE.md`. Mandatory rule: update both handover files after every user prompt, even when no code changes; record goal, evidence, PR/CI/merge/deployment state, remaining risks, expected user action, and a continuation prompt. The user's logs verified PR #17's 120s LinkedIn scan cadence and five-minute cooldown, although one 429 remains and escalation beyond 5 minutes has not yet been observed. Current task is PR #19: remove the hidden unknown-experience-only alert veto, make dashboard `/api/jobs` read stored evaluations and the canonical Telegram ledger, show per-opportunity Telegram state/reasons, and ensure threshold filters mean a true profile match. Check CI/diff; do not deploy until green and merged. Then have the user pull/rebuild, verify config schema 9, health, API and ledger fields, and one fresh match end-to-end without replaying historical notifications. Keep incompatible-experience rules, freshness, dedupe, notifications-enabled policy and Greenhouse disabled.”
