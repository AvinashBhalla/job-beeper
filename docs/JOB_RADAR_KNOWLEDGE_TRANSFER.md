# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-12 — experience parser patch verified in dev (78 tests pass); LLM extraction proposed, not implemented
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, merge SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Current verified state — 2026-10-12 (authoritative)

### Release/runtime status
- PR #30 promoted V2 to `main` (`b384b8d6…`); main CI passed. PR #31 synchronized handover docs, PR #33 roadmap, and PR #34 corrected branch audit; docs/CI changes passed. Main and v2 have identical GitHub blob SHAs for `v2/radar.py`, `v2/config.json`, `v2/docker-compose.yml`, `v2/Dockerfile`, `v2/requirements.txt`, `dashboard/index.html`, and `.github/workflows/v2-ci.yml`.
- Oracle still runs the existing service from the current `/home/ubuntu/job-beeper` checkout on port 8000, currently `v2-live-radar`. No live branch switch has occurred.
- Config v10: threshold 55, explicit-experience gate false, LinkedIn 180s and Naukri 300s. The ~27-minute LinkedIn sample showed 22 requests without visible 429/failures (positive but limited evidence). Three fresh qualifying matches (two LinkedIn, one Naukri) were alertable and sent without errors in ~17–35 seconds. Preserve v9 migration suppressions.

### Two instances on one VM
- User requests production on `main` and development on `v2-live-radar`, coexisting on the same Oracle VM. Production must retain its existing persistent DB/volume; dev must have a separate Compose project, volume, SQLite DB, runtime config and generated token.
- Added directly to `v2-live-radar`: `v2/docker-compose.dev.yml` (`da81d4bf…`), `v2/config.dev.json` (`d14fb3ec…`), and updated root `README.md` (`50293998…`). Dev container is `job-radar-dev`, binds only `127.0.0.1:8001`, has empty Telegram credentials, and reads from Naukri relay only. LinkedIn/Instahyre/Greenhouse and Telegram notifications are disabled by default; this prevents test-alert spam and avoids doubling LinkedIn request pressure.
- These development files are committed but not yet run on the VM. Production has not been changed.

### Branch/docs policy
- The private repository now has only `main` and `v2-live-radar`. User requested direct documentation commits on `v2-live-radar`; no docs-only branches/PRs should be created.
- User explicitly asked for handover docs to be committed directly on `v2-live-radar`, not in new branches just for documentation. Follow this unless they ask otherwise. Keep both handovers and root README aligned; no extra docs PRs.

### Next exact action
Run the combined command at the bottom of `docs/JOB_RADAR_HANDOVER.md`: delete the temporary docs branch; verify that the app/config/runtime blobs match; report current container Compose project/volume and VM memory/disk; create `/home/ubuntu/job-beeper-dev` from `v2-live-radar`; start isolated dev and return health/config/source status. This leaves production port 8000 untouched.

### Roadmap
1. Start and verify isolated development instance; ensure Naukri-only and notifications off.
2. Back up production DB/config and move the existing production checkout to main while preserving the same Compose project and volume; smoke-test and retain rollback. Do not run `down -v`.
3. Watch LinkedIn source yield/rate-limit behavior for 24–72 hours without increasing request volume or evading restrictions.
4. Greenhouse single-board canary with dry-run, timestamp, dedupe, backoff and no-history-burst checks.
5. Add Lever, Ashby, SmartRecruiters one by one; evaluate Workday/company careers later. Add source observability and dashboard decision reasons. Multi-user preferences only if scope later requires it.

### Continuation prompt
“Read both handovers plus `docs/JOBBEEPER_REFERENCE.md`. Update both handovers directly on `v2-live-radar` after every user prompt; do not create docs-only branches or PRs. Main promotion is complete; main and v2 have identical current app/config/compose/Dockerfile/requirements/dashboard/CI blobs, but Oracle still runs V2 on port 8000. Added dev compose/config: container job-radar-dev, loopback 8001, separate volume/DB/config token, Naukri-only, notifications off and LinkedIn off. Next delete leftover docs branch, check VM resources/container project/volume and runtime diff, clone `/home/ubuntu/job-beeper-dev` from V2, start dev and verify health/config/source status. Then back up production DB/config and move existing production checkout to main using the same Compose project/volume, with smoke tests/rollback. No `down -v`; never expose dev port or secrets. Then 24–72h LinkedIn monitoring and Greenhouse one-board canary.”

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
After verifying remote refs and no open/unique work, delete merged PR heads #15–#23 and the stale `optimize/behavior-preserving-pr12` branch (latest user check: 23 behind / 0 ahead; recheck before deletion). Exact command is at the end of the detailed handover. Keep `main`, `v2-live-radar`, and `naukri-relay`.

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


## Latest user prompt — 2026-10-12
No application-code changes. User confirms config v10 is live. Both handover files record the live config, `23 0` branch comparison, exact 20–30-minute observation command, safe cleanup, and the promotion gate. Update both docs again after the next prompt.


## Latest user prompt — workflow audit — 2026-10-12
PR #26 merged as `ed7c159b1d0c4cc46d9f8be297f9551d06535bc5`; CI #38202816842 passed. Main workflow audit: keep V2 CI; retire `deploy-dashboard`/Pages, disabled `job-watch` and root-config `check-sources` during the reviewed V2 promotion; retain private `naukri-relay.yml` and branch until main's old code reference points at the separate public relay. User output was `24 0`, then GitHub comparison after PR #26 was `25 0`. Both handover docs record the audit and corrected cleanup list. No app code changed.


## Latest user prompt — 2026-10-12: observation and branch cleanup
No application-code/config changes. User supplied 10 scan summaries over ~27 minutes, 22 attempted requests, no visible HTTP 429/cooldown warnings, zero failed requests, latest source status `new_jobs=0`. User deleted every audited topic branch; final remote branches are main/naukri-relay/v2-live-radar. Next task is fresh qualifying alert proof. This documentation PR's temporary branch is deleted after merge.


## Latest user prompt — 2026-10-12: fresh alert proof complete
No application-code change this turn. API evidence has three qualifying recent jobs ≥55%, all `alertable=true`, `notification_status=sent`, no error; send latency 16.6s, 28.8s and 34.6s after discovery. Combined with config v10 and the observed low-pressure LinkedIn window, this satisfies the initial gate to prepare the reviewed main promotion PR. Both handovers updated.


## Latest user prompt — fresh alerts and main promotion — 2026-10-12
User's API output proves three fresh ≥55% matches were alertable and sent, no delivery errors, send delay 16.6s/28.8s/34.6s. PR #30 is open from v2-live-radar to main, compare 94 ahead/0 behind and 21 files changed. Its old head CI passed, but this handover commit advances v2-live-radar so latest-head CI must be rechecked. No main merge/deployment yet.


## Latest user prompt — promotion to main — 2026-10-12
PR #30 merged as `b384b8d6ae00c48c7765ebf11af407981de3cd35`; post-merge main CI #38206525826 passed. This promotes V2 in GitHub only; Oracle continues deploying `v2-live-radar`. The main code uses the separate public Naukri relay and the four legacy workflows are removed. Three recent qualifying matches have been sent through Telegram. Remaining cleanup is the now-unused private `naukri-relay` data branch and two temporary docs refs; do not delete the public relay repo's branch. Both handovers updated.


## Latest user prompt — roadmap planning — 2026-10-12
No application code changed. Current branch state: main and v2-live-radar are release refs; private `naukri-relay` and temporary docs branch are candidates for deletion; Oracle remains on v2. Roadmap priority: housekeeping, verified Oracle cutover, 24–72h LinkedIn low-pressure monitoring, Greenhouse single-board canary, then structured ATS adapters, per-source observability/dashboard and later per-user profiles if needed. Both handovers updated.


## Latest user prompt follow-through — current branch audit
The freshest branch inventory after PR #33 contains only `main`, `v2-live-radar`, and `docs/next-phase-roadmap-20261012`. Private `naukri-relay` and `docs/record-fresh-alerts-main-promotion-20261012` are already absent. Next delete only the temporary roadmap branch after no-open-PR check; do not touch the separate public relay. No app code/config change.


## Latest user prompt — dual dev/prod VM proposal
No live VM change. Added isolated dev files to v2-live-radar and updated README. The intended model is production on main, development on v2-live-radar, separate paths/containers/ports/databases/config tokens. Immediate next action is the detailed handover command to start dev safely and inspect the existing production Compose volume; cutover only after dev passes.


## Branch inventory correction — 2026-10-12
The latest GitHub branch listing contains only main and v2-live-radar, so no further topic cleanup is needed. Both handovers are committed directly to v2-live-radar per user preference. Immediate next task is safely starting the dev instance without modifying production.


## Latest prompt — LinkedIn experience bug and source expansion

The screenshots show a 4-6 year Experience label on LinkedIn while the dashboard/Telegram treated it as unknown and sent a 61% match. Patch committed to v2-live-radar: radar.py 6ac58a1d, regression tests 22496f97; CI #38211941792 passed. Not yet VM-dev tested, merged to main or deployed. Next use the dev-only verification command in the detailed handover; dev remains Naukri-only with notifications off and LinkedIn disabled. After dev passes, promote the patch to main, then Greenhouse one-board canary in dev, validate Instahyre endpoint and freshness, then integrate Ashby/Lever/SmartRecruiters and proceed through the full requested source inventory. Handover documents committed directly on v2-live-radar, no docs-only branch.


## Interruption recovery record — 2026-10-12

- Code fix is committed on development branch only: `v2/radar.py` `6ac58a1d4757c3c545203b84a61f4f8058d4747b`; tests `v2/test_radar.py` `22496f9714a7628d4c93929005a2d10773a753cc`.
- Full regression suite passed in GitHub Actions run [#38211941792](https://github.com/AvinashBhalla/job-beeper/actions/runs/38211941792). Follow-up CI checks for directly committed documentation updates also passed: [#38212605092](https://github.com/AvinashBhalla/job-beeper/actions/runs/38212605092), [#38212615004](https://github.com/AvinashBhalla/job-beeper/actions/runs/38212615004), [#38212626814](https://github.com/AvinashBhalla/job-beeper/actions/runs/38212626814).
- Current branch inventory: `main` and `v2-live-radar` only; no open PRs. No docs-only branch should be created.
- No VM rebuild/test has been confirmed from user output since the patch. No merge of this fix to main and no production deploy has happened.
- **The next step is exactly the dev-only test command immediately above this record in the handover.** Pull latest V2 in `/home/ubuntu/job-beeper-dev`, rebuild only Compose project `job-radar-dev`, run the full unittest suite in the built image with temporary DB path, check port 8001 health/safe config/source status and confirm port 8000 production remains healthy. Do not enable LinkedIn or Telegram in dev for this test and do not change production.
- After green dev evidence: review/promote the experience fix to main and confirm main CI. Next enable Greenhouse only as a one-board development canary with notifications off; validate Instahyre endpoint/schema/freshness before enabling that source. Continue the ATS rollout list in `docs/JOBBEEPER_REFERENCE.md`.
- Continuity rule reaffirmed: after every user prompt update both handovers directly on `v2-live-radar`.

## Latest handoff — 2026-10-12: dev verification passed; LLM job-description enrichment proposal

### Evidence received from Oracle VM
The user ran the dev-only rebuild/test command in `/home/ubuntu/job-beeper-dev`. Output reports **78 unit tests ran in 53.339 seconds; OK**. Development health returned `status=ok`, version `2.0.0`, database `/data/jobs.db`; Naukri's latest poll completed successfully at `2026-10-12T06:43:53.083706+00:00` with 292 jobs seen, zero new and no error. Safe dev config is version 10; LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, notifications=false. Source status agrees. Production port 8000 remains healthy and continues to report LinkedIn and Naukri status. This closes the stated development verification gate for the experience parser patch; it does not prove that the patch is on the VM's currently running dev image unless the displayed rebuild command was run against the latest branch, but the user supplied the expected full command output and no failures.

### Diagnosis / proposal: deterministic JD parsing needs a bounded LLM assist
The user proposes an LLM to extract required skills and experience from job descriptions because deterministic parsing misses varied formats. This is reasonable as an **enrichment layer**, not a replacement for source normalization, deterministic matching, eligibility rules, dedupe, notification ledger, or delivery policy. No application code changed in this turn. No API provider/model or spend ceiling has been configured; do not add a provider dependency or call any external model until key/config ownership and cost controls are decided.

Recommended implementation contract:
- Input: a bounded, sanitized plain-text job description plus title/source metadata; do not pass secrets, candidate PII, or unrelated page contents. Treat JD text as untrusted data, not model instructions.
- Output strict JSON schema: `experience_min_years`, `experience_max_years` (nullable numbers), `experience_type` (required/preferred/unspecified), `experience_evidence` (short verbatim evidence excerpt or null), `required_skills` (array of normalized skill names), `preferred_skills`, `responsibilities` (optional capped summary), `confidence` per field or an overall confidence, and schema/parser version. Explicitly distinguish total professional experience from experience with a particular tool and distinguish "preferred" from required; preserve ranges and avoid interpreting graduation year, product history, or incidental numbers as experience.
- Validate output locally and reject malformed, overlong, unsupported, contradictory or low-confidence results. Store provider/model, prompt/schema version, extraction timestamp, input content hash, latency, token usage/cost if supplied, and redacted error category; never log API keys or raw private content.
- Deterministic parsing and source-labeled metadata take precedence where confidently present. LLM can fill missing fields and add skill extraction, but must not silently overwrite explicit source metadata. Conflicts should be marked uncertain and may trigger a safe fail-closed experience gate for alerts rather than inferred eligibility.
- Job description is untrusted prompt-injection content: isolate it as data, do not provide tools, do not allow output to control config or network access, and never let it set its own eligibility/match score.
- Call the model only for records that lack essential fields or fail extraction; cache by canonical job ID + description hash + schema/prompt version; use bounded retries, request timeout, per-run budget/rate limit and provider error backoff. Continue gracefully with deterministic results when provider unavailable.
- Establish a labelled evaluation fixture set before rollout: explicit ranges ("4-6 years", "4.00-6.00 Years"), minimum-only, maximum-only, preferred-only, total-vs-skill-specific years, internships/fresher, conflicting metadata, no experience stated, and malicious JD instructions. Gate on exact experience-field accuracy and zero false-eligible alerts on known out-of-range samples, not generic model quality claims.
- Initial deployment should be disabled by default and tested in development with notifications off. Compare deterministic versus LLM extracts without changing matching/alert behavior first (shadow mode); only enable bounded enrichment after evals pass and cost/latency/yield are observed. Do not send historical suppressed notifications.

### Patch and deployment state
- Existing experience parser/test patches: `v2/radar.py` commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`; `v2/test_radar.py` commit `22496f9714a7628d4c93929005a2d10773a753cc`; GitHub CI run [#38211941792](https://github.com/AvinashBhalla/job-beeper/actions/runs/38211941792) passed.
- User's dev output confirms full suite 78 tests passing, dev safe source config and dev health are good, production remains healthy. LLM integration is not implemented. No new source commit, LLM CI run, main merge, or production deployment occurred this turn.
- Follow-up post-patch docs CI must be checked for the new documentation commit; record its result only when actually observed.

### Exact next actions
1. Promote the tested experience-parser fix through a reviewed release PR/merge to `main` and verify main CI. Do **not** switch the production VM checkout as part of this code promotion.
2. Before coding the LLM client, choose provider/API credential location and enforce a small monthly/request budget; store key only in dev/prod secret configuration, never in git/docs/chat. Prefer a provider API with constrained JSON schema output; OpenAI Structured Outputs documentation: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses . Structured schema adherence still needs local validation and application-level correctness evaluation.
3. Implement the extractor as a separate module and tests, disabled by default, then shadow-run only on missing/ambiguous descriptions in dev. No source integrations/Greenhouse canary until the one-current-issue release promotion and LLM choice are handled.
4. Collect metrics: candidate count, model calls/skips, valid/invalid outputs, per-field agreement vs deterministic/source metadata, p50/p95 latency, failure/backoff counts and estimated cost. Do not log secrets or dump full JD content.

### Continuation prompt
“Continue Job Radar V2. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Latest user VM verification: 78 tests passed in 53.339s; dev health OK on 8001, config v10 has Naukri only and notifications off; source status matches; prod 8000 healthy. The LinkedIn experience parser patch can now move through reviewed release PR/merge and main CI (do not switch production checkout during promotion). User proposes an LLM for required skills/experience because deterministic parsing misses formats. No LLM code/provider added yet. Design a separate, disabled-by-default, schema-validated enrichment module; source-labeled deterministic metadata takes precedence, conflicts remain uncertain, LLM never assigns match scores or controls eligibility by itself. Add fixtures for ranges, required/preferred, skill-specific vs total experience, absent/conflicting metadata and prompt-injection text; shadow-mode in dev, cost/latency/error metrics, timeout/backoff/cache. Choose provider and secret/budget configuration before implementation. Do not alter production or enable dev notifications/LinkedIn; then continue Greenhouse one-board canary only after the current fix is promoted.” 


## Latest handoff — 2026-10-12: dev verification passed; LLM job-description enrichment proposal

### User-provided Oracle VM verification
The user reported the full dev-only verification command completed successfully: **78 unit tests ran in 53.339s; OK**. Dev health is `status=ok`, version `2.0.0`, DB path `/data/jobs.db`; Naukri poll completed at `2026-10-12T06:43:53.083706+00:00`, 292 jobs seen, 0 new, no error. Safe dev config version 10: LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, notifications=false. Source status agrees. Production port 8000 remains healthy and reports its existing LinkedIn/Naukri status. Do not infer a production deployment: none occurred.

### User proposal and diagnosis
User wants an LLM to extract JD skills and required experience because deterministic parsing misses varied text formats. No app code changed this turn. The idea is sound as **bounded structured enrichment**, but the model must not become the eligibility/matching authority. Current LLM provider, model, secret location and spending budget are not yet selected; no external provider integration has been implemented.

### Proposed extraction contract and safety boundaries
- Input only a capped, sanitized plain-text job description and minimal source/title metadata. Treat it as untrusted data; job text may contain prompt-injection instructions. No tools or privileged actions exposed to the model.
- Strict JSON fields: `experience_min_years` / `experience_max_years` (nullable), `experience_type` (required/preferred/unspecified), `experience_evidence` (short evidence excerpt/null), normalized `required_skills`, `preferred_skills`, optional capped `responsibilities`, confidence, and schema/prompt version. Distinguish total professional experience from tool-specific years and preferred qualifications from hard requirements.
- Locally validate all output, bounds, ranges and enums. Keep explicit source-labelled metadata / deterministic high-confidence evidence authoritative. If outputs conflict or confidence is low, mark uncertainty; never use the LLM alone to make a job eligible or send an alert.
- New module, disabled by default, called only when important fields are missing/ambiguous. Cache by canonical job ID + JD content hash + extractor schema/prompt version; set strict timeout, bounded retry, cost/request/run caps, provider backoff and graceful deterministic fallback.
- Observe model/provider, schema/prompt version, hash, latency, valid/invalid rates, token/cost data where available, agreement rates and redacted failure categories. Never log API keys, `.env`, credentials or full raw JD. Keep candidate PII out of prompts.
- Build regression/eval fixtures for `4-6 years`, `4.00-6.00 Years`, minimum/maximum only, required vs preferred, total vs skill-specific experience, fresher/intern, no stated experience, conflicting metadata, and adversarial instructions embedded in JD. First run **shadow mode** in dev with notifications disabled; compare extractions without changing scores or delivery. Require high exact-field accuracy and zero known false-eligible alerts before enabling.
- Constrained JSON/schema output is available with supported model APIs; for example OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses . Schema conformance is not a substitute for semantic evaluation.

### Patch, CI, deployment
- Existing parser fix: `v2/radar.py` commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`; regression tests: `v2/test_radar.py` commit `22496f9714a7628d4c93929005a2d10773a753cc`; CI [#38211941792](https://github.com/AvinashBhalla/job-beeper/actions/runs/38211941792) passed.
- Current dev command's complete reported test run is green (78 tests); dev safe config is confirmed and prod health remains OK.
- LLM feature has no code/config/requirements change, no new CI run, no main merge or production deploy this turn. No source integration work performed.
- Handover files were updated directly on `v2-live-radar`, without a docs-only branch/PR. New documentation commits are `cb56269633878df78804363b86ae4e7b0a8aed7f` and `7101b74e19190807fd31c55a4e2dce74aa2ff90a`; latest documentation CI was pending at last check, not yet claimed passed.

### Next action
1. Promote the verified experience parser fix through a reviewed PR/merge to `main` and check main CI. Do not switch the production Oracle checkout as part of promotion.
2. Before implementing LLM code, decide provider/model, secret configuration, and hard spend/request limits. Store keys only in secret configuration, never git/docs/chat.
3. Add an isolated disabled-by-default extraction module and tests; shadow-run only missing/ambiguous descriptions on dev with notifications off. Measure accuracy, confidence, latency, failures and cost.
4. Resume source roadmap only after release gate: Greenhouse one-board dev canary, then Instahyre schema/freshness validation, then Ashby/Lever/SmartRecruiters. Preserve no historical alert replay and no LinkedIn limit evasion.

### Continuation prompt
“Continue Job Radar V2. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. User supplied successful dev verification: 78 tests pass in 53.339s; dev health OK at port 8001, config v10 is Naukri-only with notifications off, source status agrees, and production port 8000 remains healthy. The LinkedIn experience parser fix is ready for reviewed promotion to main; verify main CI, but do not switch the production VM checkout as part of promotion. User proposed an LLM to extract skills/experience from JDs. No LLM implementation/provider has been chosen. Design it as a separate disabled-by-default strict-schema extractor with local validation, deterministic/source-labelled metadata precedence, uncertainty on conflicts, prompt-injection isolation, cache by JD hash/schema, timeouts/backoff and hard spend caps. Shadow mode first with notifications off; evaluate required/preferred skills, year ranges, skill-specific vs total experience, missing/conflicting fields and malicious text. Select provider and secure budget/secrets before coding. No production change; then Greenhouse one-board dev canary and later Instahyre/ATS roadmap.” 


## 2026-10-12 — Gemini JD extraction implemented in dev branch (not yet VM-verified)

### User decision
Use Gemini for job-description extraction; the user will enter the API key directly on the dev VM. Work stays on \`v2-live-radar\`; do not merge or deploy this feature to production.

### Code changes
- Added \`v2/gemini_extractor.py\`: bounded Gemini REST integration with strict structured JSON output and local semantic validation for overall experience range/type/evidence, required skills, preferred skills, and confidence.
- Default model is \`gemini-3.5-flash-lite\` (configurable via \`GEMINI_MODEL\`). Google’s current pricing page lists a free tier for this model and a 1M-token context window; free-tier content may be used to improve Google products. Confirm current model quota/terms in AI Studio before enabling.
- Wired extraction into \`run_source\` as shadow-only. Extracted values are stored separately in SQLite table \`gemini_shadow_cache\`; they do not modify jobs, matching, scores, notification decisions, or Telegram delivery.
- Added \`GET /api/llm-shadow-status\`, returning enabled/key-configured booleans, model, usage caps, cache summary, and recent structured results. It never returns the key or raw JD.
- Dev Compose accepts \`GEMINI_API_KEY\`, \`GEMINI_MODEL\`, \`GEMINI_EXTRACTION_ENABLED\`, \`GEMINI_MAX_CALLS_PER_RUN\`, and \`GEMINI_MAX_CALLS_PER_DAY\`. Defaults: disabled, 3 calls per source run, 20 calls/day. Output is capped and cached by source/job/JD hash; errors are briefly cached. API key is passed only through runtime environment, never committed.
- Added \`v2/test_gemini_extractor.py\` for validation, evidence checks, cache behavior, disabled-by-default behavior, and no mutation of source job data.

### Verification status
- Code/config committed directly to \`v2-live-radar\`; latest known application patch commit: \`5a73bd041bbf5455b1fa9c0a0828ce21a39ecab3\` (later doc commits follow).
- The new Gemini test suite and the full 78-test existing suite have **not yet been run on the dev VM**. Do not describe this as verified or production-ready until the dev rebuild, full test suite, API smoke test (with key kept hidden), status endpoint, and production health check pass.
- Production must remain unchanged at port 8000. Dev remains loopback-only at port 8001, with notifications disabled and Naukri as the only enabled source.
- No key, secret, raw JD, or full model request/response should be copied into GitHub, handover docs, logs, or chat. Avoid sending candidate PII; only public job-posting text is in scope.

### Next steps
1. On the VM, fetch \`v2-live-radar\`, enter the key through a hidden prompt, export the Gemini environment variables, rebuild only \`job-radar-dev\`, run the full unit suite, and verify \`/health\`, \`/api/config\`, \`/api/llm-shadow-status\`, and port 8000 health. Keep notifications off.
2. Review the first shadow outputs for explicit overall experience vs skill-specific experience, required vs preferred skills, null handling, and confidence. Confirm no matcher/alert output changes.
3. Fix any failures before further work. Keep Gemini shadow-only until accuracy is measured on representative fixtures. Do not promote or merge as part of this VM smoke test.

### Continuation prompt
“Continue Job Radar V2. First read \`docs/JOB_RADAR_HANDOVER.md\`, \`docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md\`, and \`docs/JOBBEEPER_REFERENCE.md\` on \`v2-live-radar\`; update both handover docs after every prompt. Gemini extraction has now been implemented on \`v2-live-radar\` as a disabled-by-default, separately cached, shadow-only feature. Default model is \`gemini-3.5-flash-lite\`; runtime env key is \`GEMINI_API_KEY\`, feature toggle \`GEMINI_EXTRACTION_ENABLED=true\`, limits 3 calls/run and 20/day. New tests are not yet verified on the dev VM. Next: hidden-input API key, rebuild only dev port 8001, run all tests, check \`/api/llm-shadow-status\`, keep notifications off, and confirm production port 8000 remains healthy. Do not merge or deploy. Never log or commit secrets.”


### Follow-up hardening — 2026-10-12
- Added explicit \`experience_scope\` (\`total_professional\`, \`skill_specific\`, \`unknown\`) to the structured result so skill-specific years cannot be silently treated as total experience.
- Corrected nullable Gemini schema fields and broadened detection of skill-specific experience wording.
- Wrapped the shadow pass fail-open so cache/LLM errors cannot block normal source ingestion.
- Default model is \`gemini-3.5-flash-lite\`, selected for structured extraction and free-tier availability listed on Google’s current pricing page. Free-tier data-use terms and model quotas still apply; verify the selected project/model in AI Studio before enabling.
- Draft validation PR: https://github.com/AvinashBhalla/job-beeper/pull/35. It is not merged and must not be merged until dev VM tests and shadow review pass. The GitHub connector reported no status checks/workflow runs for the latest head at the time of this update; this is not evidence of passing CI.
- Latest app-code commit at this point: \`cd3a8a694e08b451d738d6fbc789b86c323c4f5b\`. New and existing tests have not yet been executed on the VM.



## 2026-10-12 — Dev VM feedback: test syntax fixed; rerun required

### User-reported evidence
- The Gemini API smoke test succeeded with the synthetic posting and returned 4–6 years, required Python/FastAPI, preferred Kubernetes, and \`total_professional\` scope.
- Dev health was OK; Naukri was the only enabled source. Dev config confirmed \`notifications_enabled=false\`; production port 8000 remained healthy.
- \`/api/llm-shadow-status\` showed Gemini enabled/configured, 3 calls today, 3 successful cached results, 0 errors. Recent Naukri results included several role/domain experience ranges incorrectly or ambiguously labeled \`skill_specific\`; treat this as an extraction-quality issue, not a matcher input, because mode remains shadow-only.

### Fixes made on \`v2-live-radar\`
- Fixed malformed dictionary/list brackets in \`v2/test_gemini_extractor.py\` that caused a SyntaxError during unittest discovery. Fix commit: \`7941a99129614ffb03a7406e8fd002e1535fb05d\`.
- Tightened the prompt in \`v2/gemini_extractor.py\`: \`total_professional\` requires explicit overall/total/professional/work wording; named technology experience is \`skill_specific\`; role/domain-only phrases such as “Java Full Stack Development experience” should be \`unknown\` unless scope is explicit. Prompt change commit: \`def76ed2fe1f181b8501f25c09098161ef669b87\`.
- The previously reported full test run is **failed**, not passed: 79 tests discovered, with one import-time SyntaxError. No new full test run has yet confirmed the fix.

### Immediate next steps
1. Fetch latest \`origin/v2-live-radar\` on \`/home/ubuntu/job-beeper-dev\`.
2. Rebuild only \`job-radar-dev\`, rerun the full unittest discovery. Do not continue if any tests fail.
3. Recheck dev health/config, \`/api/llm-shadow-status\`, and production port 8000. Keep notifications disabled.
4. Inspect new shadow rows after the next permitted source run. The model output remains observational only; do not connect it to matcher decisions or alerts yet.
5. Do not merge draft PR #35 or deploy to production until full tests and a representative shadow evaluation pass.



## Latest handoff — 2026-10-12: 84 tests pass; Gemini HTTP 401 is the active blocker

- User-reported full suite: **84 tests, 54.614s, OK**.
- Dev port 8001 health: healthy; Naukri only, 296 jobs seen and 1 new, no source error. Config remains notifications disabled and other sources disabled.
- Production port 8000 health: healthy. No production change/deployment.
- `/api/llm-shadow-status`: Gemini enabled, non-empty key detected, model `gemini-3.5-flash-lite`, shadow-only, cap 20/day, 6 calls today, 3 successful cached results and 3 recent `gemini_http_401` failures.
- Earlier Gemini requests succeeded in the same overall dev rollout, so the immediate failure is authentication/API authorization, not evidence of a parser/test regression. Root cause is not yet proven. A key-present flag is not key validation.
- Next: verify key active/project/API access and API-key restrictions in AI Studio/Cloud Console. Re-enter a valid key through the VM's hidden prompt if needed, rebuild only dev, run one synthetic request, and inspect only status/error category. Never echo/commit/share the key. Avoid triggering more source runs while troubleshooting; do not raise caps to compensate.
- Release gate: tests and both health checks pass; Gemini auth and extraction-quality review still pending. Keep PR #35 unmerged, shadow-only, no matcher/alert mutation, no production deployment.
- Continuation prompt: “Read the two handovers and `docs/JOBBEEPER_REFERENCE.md`; update both handovers after every prompt. 84 tests pass. Dev and prod health are good. Gemini model `gemini-3.5-flash-lite` has 3 cached successes and 3 latest HTTP 401 failures (6 calls today, cap 20). Diagnose API key/project/API restrictions without exposing the key, then test one synthetic request. Keep feature shadow-only and PR #35 unmerged until auth and representative shadow quality are verified.”


## Latest handoff — 2026-10-12: Recent Gemini calls are successful; quality review remains

- User-provided status: 12 calls today, 6 successful cached results and 6 cached errors. The newest three requests (created around 08:14 UTC) are `status=ok`; six older rows from 08:07–08:12 have `gemini_http_401`.
- This indicates the latest requests are authenticating successfully; earlier errors are persisted cache records. The root cause of the intermittent/previous 401s is not confirmed, so verify only if a new request fails. Do not clear error rows just to make the status look green.
- Recent successful outputs cover a 3–8 year range, 6+ years, and a 6–11 year range. One result has a populated range but null evidence, and scope labels need manual comparison against the original job text. High confidence is not an accuracy guarantee.
- No app code change, production deployment, or matcher/alert behavior change occurred. The feature remains shadow-only. The user previously reported 84 tests passing; no new test run was supplied in this message.
- Next: avoid extra source scans; calls are already 12/20 today. Review a small labelled sample for exact range, required/preferred skills, evidence, and total-professional versus skill-specific scope. Observe naturally occurring calls for fresh 401s. Keep notifications disabled, PR #35 unmerged, and production untouched until shadow evaluation passes.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md`; update both handovers after every prompt. Gemini status is 12 calls/day, 6 successes, 6 historical errors; newest three requests succeeded, older rows contain `gemini_http_401`. Auth appears to work for recent calls but root cause is unknown. Do not spend remaining quota unnecessarily. Review a small representative sample for experience range/evidence/scope and required/preferred skills. Keep Gemini shadow-only, PR #35 unmerged, and production unchanged.”


## 2026-10-12 — Dev access and remaining validation gate
- Dev dashboard access is via SSH tunnel because Compose maps `127.0.0.1:8001:8000`; use `ssh -L 8001:127.0.0.1:8001 ubuntu@YOUR_ORACLE_VM_IP`, then `http://127.0.0.1:8001`. Dev Telegram credentials are blank and notifications are intentionally off; do not expect dev alerts in the production Telegram chat.
- Dev health/status commands: `curl -s http://127.0.0.1:8001/health` and `curl -s http://127.0.0.1:8001/api/llm-shadow-status`. Production port 8000 must remain untouched.
- Gemini remains shadow-only; latest supplied status was 12 calls/day, 6 successful results, 6 historical cached HTTP 401 errors, with the newest three requests succeeding. Avoid extra scans. Review a small labelled sample against the original job-description text before proceeding.
- Extractor only retains evidence when the model's evidence string appears as an exact case-insensitive substring of the JD; paraphrases become null. Treat null evidence as a review flag, not proof that the extracted experience is wrong. No code changes this turn.
- Official Gemini docs describe the 2026 migration from standard keys to authorization keys and key error semantics: https://ai.google.dev/gemini-api/docs/api-key?authuser=00 and https://ai.google.dev/gemini-api/docs/api-errors. Since latest calls succeeded, don't rotate keys unless fresh failures occur.
- Next: manually label a small sample, then—only after quality gate passes—run Greenhouse one-board dev canary with notifications disabled. PR #35 stays unmerged; no production deployment.
- Continuation prompt: Read both handovers and `docs/JOBBEEPER_REFERENCE.md`; update both handovers after every prompt. Use SSH tunnel for dev dashboard; keep dev Telegram disabled and production unchanged. Evaluate Gemini against original JD evidence before Greenhouse canary; avoid unnecessary scans and do not merge PR #35.


## 2026-10-12 — Correct dev URL and Gemini evidence-quality patch
- Production URL supplied by user: `http://130.210.27.197:8000/dashboard/#jobs`. Dev Compose intentionally binds `127.0.0.1:8001`, so it cannot be opened through the public VM IP. SSH tunnel from the user's PC: `ssh -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197`; then open `http://127.0.0.1:8001/dashboard/#jobs`. Alternate local port if 8001 is occupied: `ssh -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197`, then `http://127.0.0.1:18001/dashboard/#jobs`.
- User-reported dev health: healthy, Naukri last success 2026-10-12T08:54:57Z, 294 jobs seen, 0 new, no source error. Production was not changed.
- Gemini latest status is 20/20 calls today, 14 successes, 6 errors; stop API calls/scans for the rest of the daily window. Recent populated experience ranges with null evidence and possible scope confusion are not confirmed extraction errors without the original JD text.
- Branch patch in `v2/gemini_extractor.py`: require verbatim contiguous evidence quote; treat technology focus/domain wording as ambiguous unless years are directly tied to a named tool; collapse whitespace before exact evidence substring validation; bump extraction version to `gemini-shadow-v2`. Tests added for multiline whitespace and prompt guidance in `v2/test_gemini_extractor.py`.
- Commits: `a9acd2e571760e325ddb9d98441f0924545dade8`, `0e4fd7332e4b8662ef89c500c7124f98e48dd712`, `782b2b8c4aead193e275d88adb7e9c98ec3a3c9a`. CI run #435 / ID 38226790483 was in progress at last check; no green CI confirmation and no dev rebuild/test evidence yet.
- Next: check CI; fetch branch and rebuild only dev, run full tests and health checks. Keep dev notifications disabled, port 8001 private, production untouched, PR #35 unmerged. After daily quota resets, compare new v2 outputs with source JD before Greenhouse canary.
- Continuation prompt: Read both handovers and `docs/JOBBEEPER_REFERENCE.md`; update both handovers after every prompt. Use SSH tunnel for dev dashboard; 20/20 Gemini quota used today. Verify CI and dev tests for evidence/scope patch; do not scan further today, enable dev Telegram, merge PR #35, or deploy production.


## 2026-10-12 — Dev SSH tunnel authentication blocked
- User ran `ssh -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197` from Windows PowerShell and received `Permission denied (publickey)`. The port-forward syntax is valid, but SSH authentication failed before the tunnel could be established. The previously known context does not identify the user's private-key path or working SSH invocation; do not guess a key or change server SSH settings.
- Next diagnostic: ask the user to run `Get-ChildItem "$env:USERPROFILE\.ssh"` in PowerShell and report filenames only (never paste private-key contents). If they use an Oracle Cloud downloaded `.key`/`.pem` file or a custom key, use that exact local path with `ssh -i "C:\path\to\key.pem" -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197`. If a known working SSH command/host alias exists, preserve its identity/user/options and add only the port-forward flag. Do not alter production, dev service bindings, or server authorized_keys without evidence.
- After SSH auth succeeds, keep the tunnel terminal open and visit `http://127.0.0.1:8001/dashboard/#jobs`; if local 8001 is occupied, forward local 18001 to remote 8001 and use `http://127.0.0.1:18001/dashboard/#jobs`.
- This turn did not change app code, deployment, SSH server configuration, or production. Continue pending CI/dev-only validation of the Gemini evidence-quality patch; do not trigger more Gemini calls while today's 20-call cap is exhausted.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. SSH tunnel command failed with `Permission denied (publickey)` from Windows PowerShell. Ask for SSH key filenames only using `Get-ChildItem \"$env:USERPROFILE\\.ssh\"`, then construct an SSH command using the user's actual key or known working SSH options; never request or expose private-key contents. Keep dev on localhost:8001, production untouched, Gemini shadow-only, and continue CI/dev-only validation.”


## 2026-10-12 — SSH tunnel established; CI green; dev-only validation next
- User confirmed the SSH tunnel is connected and the Job Radar V2 development dashboard opened at `http://127.0.0.1:8001/dashboard/#jobs`. This confirms local forwarding and authentication now work. No runtime health/test output has been supplied yet.
- GitHub Actions V2 CI run #435 (run ID `38226790483`) for commit `782b2b8c4aead193e275d88adb7e9c98ec3a3c9a` is now `completed/success`. This clears the CI gate for updating the isolated dev checkout, not for production release.
- Repo instructions confirm dev checkout `/home/ubuntu/job-beeper-dev`, Compose file `v2/docker-compose.dev.yml`, project `job-radar-dev`, service `radar`, loopback host port 8001, independent volume `job-radar-dev_radar-dev-data`; dev notifications are hard-disabled by blank Telegram environment values. Never run Compose commands against production project or use `down -v`.
- Next safe sequence: (1) from a second SSH session (keep the tunnel session open), inspect `cd /home/ubuntu/job-beeper-dev && git status --short --branch && git rev-parse --short HEAD && git fetch origin v2-live-radar && git log -1 --oneline origin/v2-live-radar`; stop if working tree is dirty or branch is not `v2-live-radar). (2) If clean and correct branch, `git pull --ff-only origin v2-live-radar`. (3) Rebuild/start dev only with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build`. (4) Verify `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml ps`, `curl -fsS http://127.0.0.1:8001/health`, `curl -fsS http://127.0.0.1:8001/api/llm-shadow-status`, and run tests inside the dev container with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml exec -T radar python -m unittest discover -s v2 -p 'test_*.py'`. Never print environment variables or secrets. If any check fails, capture sanitized error output and stop before source scans.
- Gemini quota was 20/20 for the prior reported daily window; do not initiate source scans or extra Gemini API calls as part of this validation. Confirm feature remains shadow-only, Telegram notifications remain disabled, and production port 8000/container/database remain untouched. PR #35 stays unmerged; Greenhouse canary remains gated on reviewed sample quality.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. SSH tunnel and dev dashboard now work. CI run #435 passed for `782b2b8c4aead193e275d88adb7e9c98ec3a3c9a`. In a second SSH session inspect the dev clone status/branch, fast-forward only if clean and on `v2-live-radar`, rebuild only `job-radar-dev`, then run full unittest discovery and health/shadow status checks. Do not scan jobs or spend Gemini quota, expose secrets, enable notifications, merge PR #35, or touch production.”


## 2026-10-12 — Dev checkout behind branch; runtime tests pass on old image
- User-reported dev checkout: branch `v2-live-radar...origin/v2-live-radar [behind 14]`, local HEAD `aa74445`; fetched remote tip shown as `a800e9d` at time of inspection. This checkout has not yet fast-forwarded to the extractor patch commits.
- User rebuilt/restarted `job-radar-dev` before pulling the branch: container is Up and maps `127.0.0.1:8001->8000/tcp`. Health endpoint is OK; Naukri reports last success `2026-10-12T09:41:56Z`, 294 jobs seen, 0 new, no error.
- Full in-container unittest discovery passed: 86 tests in 53.328s, `OK`. This verifies the currently built checkout only, not the newer Gemini evidence patch.
- `/api/llm-shadow-status` reports `enabled=false`, `api_key_configured=false`, calls_today 20/20, cache 14 successes/6 errors, and recent rows still use `gemini-shadow-v1`. Do not enable Gemini, expose/replace credentials, or trigger scans to test the patch. Old cache rows are not evidence of the new extraction version.
- Safe next step: run `git status --short --branch` and confirm clean working tree and branch `v2-live-radar`; then `git pull --ff-only origin v2-live-radar`. Rebuild only `job-radar-dev` with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build`, verify `ps` and `/health`, then rerun full unittest discovery. Re-check `/api/llm-shadow-status` for feature configuration/version only; do not trigger source scans. Stop if working tree is dirty, branch differs, pull is not fast-forwardable, or rebuild/tests fail.
- Production port 8000, production checkout/database/volume/config, notification settings, and PR #35 remain untouched; do not merge or deploy. Keep Greenhouse canary gated on a reviewed fresh Gemini sample after quota availability and deliberate approval.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Dev checkout was `aa74445`, 14 commits behind origin; container health OK and all 86 current-image tests pass, but Gemini status is disabled/unconfigured and cached rows remain `gemini-shadow-v1`, so new extractor patch is not yet deployed. Verify clean correct branch, fast-forward only, rebuild/test dev only. No scans/API calls, no secrets, notifications stay off, production untouched, PR #35 unmerged.”
