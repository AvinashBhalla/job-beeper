# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-11 — PR #21/#22 merged; free-first strategy and branch cleanup audited; v10 deployment pending  
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, merge SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Latest operating update — 2026-10-11 (read this first)

### Production runtime vs latest code
- User-supplied Oracle output after PR #19: health `ok`, app `2.0.0`, config version **9**, threshold `55`, `require_explicit_experience_for_alerts=false`, LinkedIn poll `120s`, Naukri `300s`. `/api/jobs?today_only=true&limit=500` returned 454 observations and 26 true profile matches ≥55.
- Some older candidates were intentionally `suppressed` during the v9 policy migration to prevent a historical Telegram burst (e.g. HGS AI Engineer, Five9 Software Engineer II, Duncit Software Engineer, FICO Customer Engineer/AI); do not manually requeue those. Some qualifying jobs were already `sent`. This is not yet proof a fresh post-v10 match reaches Telegram end-to-end.
- The repo is ahead of production. PR #21 merged as `6c93473844cd469493a0c61acf1477ba20252d69`; [CI #38161863816](https://github.com/AvinashBhalla/job-beeper/actions/runs/38161863816) passed 76 tests. It sets config v10, LinkedIn polling 180s, minimum global HTTP spacing 4s, one detail-enrichment worker, 2 first-page targets per scan and deep scans every 30m. PR #22 merged as `8eae61f2605c14903bccbc25c1a95d438e3a9f79`; [CI #38162375556](https://github.com/AvinashBhalla/job-beeper/actions/runs/38162375556) passed 76 tests and left only `.github/workflows/v2-ci.yml` on `v2-live-radar`. PR #23 recorded the merges and release gate.
- **Production remains v9 until the user pulls and rebuilds.** Deploy v10, verify health and runtime config, then observe 20–30 minutes of request attempts/429/cooldown/scan/new-job yield. A clean run or an enforced cooldown does not mean LinkedIn will stop returning 429s.

### LinkedIn 429: free-first policy
- PR #17 already proved that its 120s scheduler cadence and cooldown were respected, but 429s recurred. PR #21 deliberately lowers request volume; it cannot promise zero 429s. Global stop-on-429, `Retry-After` honoring and escalating 5/10/20/30-minute cooldowns remain.
- User prefers free and self-built methods before paid options. Do not use proxy/IP rotation, CAPTCHA bypass, fake identities or traffic disguise to evade access limits. LinkedIn's [User Agreement](https://www.linkedin.com/legal/user-agreement) and [prohibited scraping software page](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software) prohibit scraping software and limit evasion. A public guest endpoint is not guaranteed to match paid-scraper coverage.
- Free-first expansion should emphasize permitted public ATS/company-career feeds, stable IDs, true posted timestamps, dedupe, per-source backoff and alert tests. [Lever's public postings API](https://github.com/lever/postings-api) offers published postings for a known site but not full-text search. The [Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview?hl=en) is unavailable to new customers and scheduled to discontinue on Jan 1, 2027; do not start a new integration on it. Paid scraping vendors stay deferred until free source coverage/yield is measured and their terms/data-use policies are reviewed.

### Workflow, branch and main-promotion audit
- PR #22 removed `.github/workflows/pages.yml`, `job-watch.yml`, `naukri-relay.yml`, and `check-sources.yml` from `v2-live-radar`; V2 CI remains. Those four legacy workflows are still in `main`; delete them through the later promotion PR, not direct commits now. Static Pages would call relative `/api` on the Pages host; V1 job-watch writes legacy JSON/state to main; the private Naukri workflow is superseded by the separate public relay repo and VM systemd timer; check-sources edits root V1 config.
- Keep root `config.json` and root legacy modules for now: the separate Naukri relay checkout currently reads root `config.json`; don't remove that contract until the relay is deliberately migrated.
- Keep only `main`, `v2-live-radar`, `naukri-relay` when branch cleanup finishes. PRs #15–#23 are merged. The stale `optimize/behavior-preserving-pr12` branch is 22 behind / 0 ahead; verify with `git rev-list --left-right --count origin/v2-live-radar...origin/optimize/behavior-preserving-pr12` before deleting. Safe deletion commands are at the end of `docs/JOB_RADAR_HANDOVER.md`. The connected GitHub tool cannot delete refs.
- **Promote to main only after** v10 is deployed/observed and a fresh ≥55% match is verified end-to-end: dashboard status → canonical notification ledger → Telegram send, with no historical burst. Then make a dedicated, reviewed `v2-live-radar`→`main` PR that promotes V2, removes V1/static workflows, keeps V2 CI, verifies CI/smoke tests, and leaves Oracle on `v2-live-radar` until a documented cutover.

### Exact next actions
1. Pull/rebuild `v2-live-radar` using `--env-file .env`; expected config v10 / LinkedIn 180s / Naukri 300s.
2. Send `git log -1`, health and runtime config output.
3. After 20–30 minutes, send timestamped LinkedIn request/429/cooldown/new-job logs and source status.
4. Validate a fresh qualifying match's notification status and actual Telegram send.
5. Then perform the documented topic-branch cleanup. Main promotion follows the gate above.

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

### P0 — Deploy and observe config v10 (PR #21)
1. Production last confirmed v9 / LinkedIn 120s, while repository v2-live-radar has v10 / LinkedIn 180s.
2. User pulls/rebuilds, checks health, deployed SHA, config v10, threshold 55, deprecated experience setting false, LinkedIn 180s and Naukri 300s.
3. Observe 20–30 minutes of timestamped attempts/429/cooldown/successes/new jobs. Do not bypass platform controls or claim a zero-429 guarantee.

### P1 — Validate fresh alert consistency
1. Confirm a genuinely new true profile match ≥55% moves through the same persisted evaluation and canonical notification ledger used by Telegram, and the dashboard badge agrees with actual delivery.
2. Do not requeue historical entries suppressed during the v9 migration. Preserve explicit incompatible-experience rejection, freshness, notification-off behavior, canonical dedupe and delivery-failure handling.

### P2 — Clean topic branches
After verifying remote refs and no open/unique work, delete merged PR heads #15–#23 and the stale `optimize/behavior-preserving-pr12` branch (compare expected 22 behind / 0 ahead). Exact command is at the end of the detailed handover. Keep `main`, `v2-live-radar`, and `naukri-relay`.

### P3 — Promote V2 to main
Only after P0/P1 pass, create a dedicated reviewed `v2-live-radar`→`main` PR. Include V2 app/docs, removal of the four old V1 workflows, retain V2 CI, run CI/smoke tests, then schedule a deliberate cutover. No direct/force push; keep Oracle on `v2-live-radar` until verified.

### P4 — Expand free/authorized sources
Add public ATS/company career endpoints one at a time with stable IDs/timestamps, freshness guards, rate-limit handling, dedupe and alert tests. Greenhouse remains disabled until stale `first_published` posts cannot appear fresh. Paid providers remain deferred pending a measured free-first gap and terms review.

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


### Current continuation prompt (authoritative)
“You are continuing Job Radar V2. Read the latest operating update above, `docs/JOB_RADAR_HANDOVER.md`, and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handover files after every user prompt. PR #21 is merged (v10 / LinkedIn 180s; CI 76 tests) and PR #22 is merged (four obsolete workflows removed from v2-live-radar; CI 76 tests), but Oracle output still showed v9 / 120s. First ask the user to pull/rebuild and verify schema 10, then measure 20–30 minutes of LinkedIn request attempts/429/cooldown/new-job yield. Validate one fresh ≥55% match through dashboard, ledger and Telegram without replaying suppressed historical rows. Next safely delete merged/stale topic branches using the command in the detailed handover. Promote to main only after deployment and fresh-alert verification; use a dedicated PR, remove remaining V1 workflows, retain V2 CI and do not switch Oracle's deploy ref until validated. Use permitted free ATS/company-career sources first; no LinkedIn proxy/CAPTCHA evasion.”


## Latest verified cleanup state — 2026-10-11
- PR #21 merged as `6c93473844cd469493a0c61acf1477ba20252d69`; CI #38161863816 passed 76 tests. The new request budget needs deployment: config version 10, LinkedIn poll 180s, followed by 20–30 minutes of rate/freshness observation and one fresh qualifying alert verification.
- PR #22 merged as `8eae61f2605c14903bccbc25c1a95d438e3a9f79`; CI #38162375556 passed 76 tests. `v2-live-radar` now retains only V2 CI. `main` is intentionally unchanged and still has its legacy workflows pending promotion.
- PR #15–#21 topic heads are merged candidates for deletion after checking remote refs/extra commits; keep `main`, `v2-live-radar` and `naukri-relay`. Commands are in the detailed handover.
- Promote to main after PR #21 is deployed/observed, a fresh match proves dashboard/ledger/Telegram agreement, and branch/workflow cleanup is complete. Use a separate reviewed PR; do not switch the VM deployment ref/default branch until CI and smoke tests pass.
