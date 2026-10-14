# Job Radar V2 — Knowledge Transfer

**Snapshot:** 2026-10-14 — Gemini cached matcher is committed and opt-in; dev Compose now wires its gate; live credentials/cache/mount verification pending
**Active release branch:** `v2-live-radar`  
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, merge SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Current verified state — 2026-10-14 (authoritative)

### Active issue: Gemini required-experience extraction → matcher → persisted evaluation
- Branch: `AvinashBhalla/job-beeper:v2-live-radar`; consult both handovers and `docs/JOBBEEPER_REFERENCE.md`.
- Matcher commits: `1b667e4`, `c3cc276`, `ce69cec`, `14516a0`, `0b74444`. Earlier user-reported tests passed: 11 Gemini tests and 88 Radar tests. No tests ran this turn.
- Dev Compose now forwards `GEMINI_MATCHER_ENABLED` with a false default (commit `7ea83e024f2da4923633c23221ea8085a3643a10`).
- Latest dotenv diagnostic: `.env` exists, is ignored by Git, contains exactly one non-empty `GEMINI_API_KEY` entry; default Compose discovery does not resolve it, but explicit `--env-file .env` does. Both Gemini flags remain false and Telegram credentials empty. The running API previously reported extraction disabled, key absent, 0 calls today, 14 cache successes and 6 errors. Recent cache shapes do not prove current JD hash/model acceptance or persisted-evaluation consumption.
- User's `id` does not list group `docker`. Docker socket is `root:docker` with mode `660`, and Docker API operations fail with permission denied. Do not use `sudo`, alter socket permissions or group membership. Container identity/environment and actual `/data` volume remain unverified.
- No application-code change, test run, container recreation, DB mutation, production change or alert replay. Preserve user-local `v2/config.json` modification and untracked `.venv/`.
- Next: always pass `--env-file .env` to dev Compose commands (documented in root README commit `f3df8d6330797a582b7e0a50f117c84a2482899a`). Before any service lifecycle action, have an already-authorized Docker session/account or VM administrator verify the existing container identity and actual `/data` volume using the filtered read-only commands in the detailed handover.
- After access is safely resolved: inspect actual dev volume, recreate only isolated dev with both Gemini gates false, verify environment/mount, enable bounded extraction, then prove fresh exact-JD/model-matched cache values reach persisted evaluations. Keep Telegram blank, notifications disabled and LinkedIn off. Production rollout requires explicit approval.

## Historical verified state — 2026-10-12 (superseded by the 2026-10-14 Gemini matcher state below)

### Active issue: Gemini required-experience extraction → matcher → persisted evaluation
- Branch: `AvinashBhalla/job-beeper:v2-live-radar`. Read this file with `docs/JOB_RADAR_HANDOVER.md` and `docs/JOBBEEPER_REFERENCE.md`.
- Matcher bridge commits already present: `1b667e4`, `c3cc276`, `ce69cec`, `14516a0`, `0b74444`. Earlier user-reported tests: 11 Gemini tests and 88 Radar tests passed; no tests were rerun in this turn.
- Dev Compose wiring: `v2/docker-compose.dev.yml` passes `GEMINI_MATCHER_ENABLED`, default false (commit `7ea83e024f2da4923633c23221ea8085a3643a10`). Product reference synchronized in commit `6828153f485e5e247e984a2a735f813ff6ef1d84`.
- Latest user VM output: checkout pull at that time reached `b27de42`; local `v2/config.json` modification and untracked `.venv/` were preserved. Compose syntax validation passed. Docker `ps`, `inspect`, and `exec` failed due to permission denied on `/var/run/docker.sock`; do not use sudo or change permissions.
- The API at `127.0.0.1:8001/api/llm-shadow-status` answered `enabled=false`, `api_key_configured=false`, `model=gemini-3.5-flash-lite`, `calls_today=0`, `cache_successes=14`, `cache_errors=6`. A small subset of ten recent successes met a preliminary structural shape, but this is not proof of exact current JD hash/model eligibility or persisted evaluation consumption.
- The in-container environment command pasted by the user was malformed and Docker access was denied, so effective runtime variables, service identity and actual `/data` mount remain unknown. Do not assume a particular database path beyond Compose's intended `JOB_RADAR_DB=/data/jobs.db` and named volume declaration.
- This turn changed no application code, ran no tests, and made no container restart/rebuild, DB write, production setting change or notification replay. Detailed handover update: `1dc03364eed07dc38ee5cf28fd63593ca2e5f22a`. CI status for the recent Compose/docs commits was not confirmed.
- Next action: run the latest safe host-side Compose interpolation and Docker socket metadata command at the bottom of `docs/JOB_RADAR_HANDOVER.md`. It prints no secret values. If the current user lacks Docker socket access, determine only whether a fresh login restores already-assigned group membership; do not use `sudo`, `chmod` or add groups. If no Gemini key is available to Compose, configure it only through an ignored VM-local `.env` using a hidden prompt, never in chat.
- Keep extraction and matcher gates false until baseline and actual mount are verified. Keep Telegram credentials blank, notifications disabled and LinkedIn off. Once Docker access is resolved, verify cache freshness/current-JD hash and persisted evaluation in dev before seeking explicit production rollout approval. Preserve local `v2/config.json` and `.venv/` at all times.

## Historical verified state — 2026-10-12 (superseded by the 2026-10-14 Gemini matcher state below)

### Active issue: Gemini required-experience extraction → matcher → persisted evaluation
- Repository/branch: `AvinashBhalla/job-beeper`, `v2-live-radar`. Read this file together with `docs/JOB_RADAR_HANDOVER.md` and `docs/JOBBEEPER_REFERENCE.md`.
- Matcher bridge commits already present: `1b667e4`, `c3cc276`, `ce69cec`, `14516a0`, `0b74444`. It reads a fresh cache entry for the exact current JD hash and configured model, revalidates evidence, and only trusts required `total_professional` experience with verbatim evidence and confidence ≥ 0.85. The matcher makes no Gemini network calls; deterministic parsing remains fallback.
- User previously reported 11 Gemini extractor tests and 88 Radar tests passing. These are earlier test results, not live runtime proof. No tests ran this turn.
- Dev Compose wiring fix: commit `7ea83e024f2da4923633c23221ea8085a3643a10` adds `GEMINI_MATCHER_ENABLED` to `v2/docker-compose.dev.yml`, defaulting to false. Before this, the dev Compose environment map omitted the matcher flag. Production Compose and application code are unchanged by this fix.
- Prior VM check reported matcher/extraction/model variables unset, no key detected in the checked environment, and no SQLite file found in the searched checkout depth. Do not infer current container configuration or DB location from that. The dev service declares `JOB_RADAR_DB=/data/jobs.db` on named volume `radar-dev-data`; with project `job-radar-dev`, expected volume name is `job-radar-dev_radar-dev-data`.
- Keep dev notifications disabled; dev Compose forces Telegram token/chat ID to empty. Keep LinkedIn disabled; dev config enables Naukri relay only. Matcher and extraction remain off until runtime config, credentials and volume are verified.
- Commits this turn: Compose wiring `7ea83e024f2da4923633c23221ea8085a3643a10`; reference synchronization/formatting `6828153f485e5e247e984a2a735f813ff6ef1d84` (initial content commit `8b71918468e41084f363cc1eb4a5250757e85b74`); latest detailed handover update `7a430b1c4b771dcc09eb9902d9d5ebd63ff7ff4d` (cache-precheck caution update; prior reference-sync entry `71e2b4e27904e88eaf44da34914b0ceeee7420d8`; initial reference-sync entry `85315e98009d069c301bbcec28b1b90a98f98d90`). This knowledge-transfer update is committed directly to `v2-live-radar`.
- CI result for `7ea83e0` has not been independently verified. No dev container restart/rebuild, production rollout, database write, or notification replay occurred. Preserve the user's local `v2/config.json` modification and untracked `.venv/`; never stage, reset, clean, overwrite, or delete them.
- Exact next action: run the sanitized VM commands in the latest dated section of `docs/JOB_RADAR_HANDOVER.md`. Return only that output. If the API key is absent, configure it through the VM-local ignored `.env` or exported environment without printing/pasting the value.

## Historical verified state — 2026-10-12 (superseded by the 2026-10-14 Gemini matcher state below)

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
Use Gemini for job-description extraction; the user will enter the API key directly on the dev VM. Work stays on `v2-live-radar`; do not merge or deploy this feature to production.

### Code changes
- Added `v2/gemini_extractor.py`: bounded Gemini REST integration with strict structured JSON output and local semantic validation for overall experience range/type/evidence, required skills, preferred skills, and confidence.
- Default model is `gemini-3.5-flash-lite` (configurable via `GEMINI_MODEL`). Google’s current pricing page lists a free tier for this model and a 1M-token context window; free-tier content may be used to improve Google products. Confirm current model quota/terms in AI Studio before enabling.
- Wired extraction into `run_source` as shadow-only. Extracted values are stored separately in SQLite table `gemini_shadow_cache`; they do not modify jobs, matching, scores, notification decisions, or Telegram delivery.
- Added `GET /api/llm-shadow-status`, returning enabled/key-configured booleans, model, usage caps, cache summary, and recent structured results. It never returns the key or raw JD.
- Dev Compose accepts `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_EXTRACTION_ENABLED`, `GEMINI_MAX_CALLS_PER_RUN`, and `GEMINI_MAX_CALLS_PER_DAY`. Defaults: disabled, 3 calls per source run, 20 calls/day. Output is capped and cached by source/job/JD hash; errors are briefly cached. API key is passed only through runtime environment, never committed.
- Added `v2/test_gemini_extractor.py` for validation, evidence checks, cache behavior, disabled-by-default behavior, and no mutation of source job data.

### Verification status
- Code/config committed directly to `v2-live-radar`; latest known application patch commit: `5a73bd041bbf5455b1fa9c0a0828ce21a39ecab3` (later doc commits follow).
- The new Gemini test suite and the full 78-test existing suite have **not yet been run on the dev VM**. Do not describe this as verified or production-ready until the dev rebuild, full test suite, API smoke test (with key kept hidden), status endpoint, and production health check pass.
- Production must remain unchanged at port 8000. Dev remains loopback-only at port 8001, with notifications disabled and Naukri as the only enabled source.
- No key, secret, raw JD, or full model request/response should be copied into GitHub, handover docs, logs, or chat. Avoid sending candidate PII; only public job-posting text is in scope.

### Next steps
1. On the VM, fetch `v2-live-radar`, enter the key through a hidden prompt, export the Gemini environment variables, rebuild only `job-radar-dev`, run the full unit suite, and verify `/health`, `/api/config`, `/api/llm-shadow-status`, and port 8000 health. Keep notifications off.
2. Review the first shadow outputs for explicit overall experience vs skill-specific experience, required vs preferred skills, null handling, and confidence. Confirm no matcher/alert output changes.
3. Fix any failures before further work. Keep Gemini shadow-only until accuracy is measured on representative fixtures. Do not promote or merge as part of this VM smoke test.

### Continuation prompt
“Continue Job Radar V2. First read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handover docs after every prompt. Gemini extraction has now been implemented on `v2-live-radar` as a disabled-by-default, separately cached, shadow-only feature. Default model is `gemini-3.5-flash-lite`; runtime env key is `GEMINI_API_KEY`, feature toggle `GEMINI_EXTRACTION_ENABLED=true`, limits 3 calls/run and 20/day. New tests are not yet verified on the dev VM. Next: hidden-input API key, rebuild only dev port 8001, run all tests, check `/api/llm-shadow-status`, keep notifications off, and confirm production port 8000 remains healthy. Do not merge or deploy. Never log or commit secrets.”


### Follow-up hardening — 2026-10-12
- Added explicit `experience_scope` (`total_professional`, `skill_specific`, `unknown`) to the structured result so skill-specific years cannot be silently treated as total experience.
- Corrected nullable Gemini schema fields and broadened detection of skill-specific experience wording.
- Wrapped the shadow pass fail-open so cache/LLM errors cannot block normal source ingestion.
- Default model is `gemini-3.5-flash-lite`, selected for structured extraction and free-tier availability listed on Google’s current pricing page. Free-tier data-use terms and model quotas still apply; verify the selected project/model in AI Studio before enabling.
- Draft validation PR: https://github.com/AvinashBhalla/job-beeper/pull/35. It is not merged and must not be merged until dev VM tests and shadow review pass. The GitHub connector reported no status checks/workflow runs for the latest head at the time of this update; this is not evidence of passing CI.
- Latest app-code commit at this point: `cd3a8a694e08b451d738d6fbc789b86c323c4f5b`. New and existing tests have not yet been executed on the VM.



## 2026-10-12 — Dev VM feedback: test syntax fixed; rerun required

### User-reported evidence
- The Gemini API smoke test succeeded with the synthetic posting and returned 4–6 years, required Python/FastAPI, preferred Kubernetes, and `total_professional` scope.
- Dev health was OK; Naukri was the only enabled source. Dev config confirmed `notifications_enabled=false`; production port 8000 remained healthy.
- `/api/llm-shadow-status` showed Gemini enabled/configured, 3 calls today, 3 successful cached results, 0 errors. Recent Naukri results included several role/domain experience ranges incorrectly or ambiguously labeled `skill_specific`; treat this as an extraction-quality issue, not a matcher input, because mode remains shadow-only.

### Fixes made on `v2-live-radar`
- Fixed malformed dictionary/list brackets in `v2/test_gemini_extractor.py` that caused a SyntaxError during unittest discovery. Fix commit: `7941a99129614ffb03a7406e8fd002e1535fb05d`.
- Tightened the prompt in `v2/gemini_extractor.py`: `total_professional` requires explicit overall/total/professional/work wording; named technology experience is `skill_specific`; role/domain-only phrases such as “Java Full Stack Development experience” should be `unknown` unless scope is explicit. Prompt change commit: `def76ed2fe1f181b8501f25c09098161ef669b87`.
- The previously reported full test run is **failed**, not passed: 79 tests discovered, with one import-time SyntaxError. No new full test run has yet confirmed the fix.

### Immediate next steps
1. Fetch latest `origin/v2-live-radar` on `/home/ubuntu/job-beeper-dev`.
2. Rebuild only `job-radar-dev`, rerun the full unittest discovery. Do not continue if any tests fail.
3. Recheck dev health/config, `/api/llm-shadow-status`, and production port 8000. Keep notifications disabled.
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


## 2026-10-12 — Dev rebuild after fast-forward; tests green, Gemini disabled
- User fast-forwarded `/home/ubuntu/job-beeper-dev` from `a800e9d` to `2e168ad` and rebuilt only `job-radar-dev`. Build completed; container is Up at loopback `127.0.0.1:8001`; `/health` reports OK and Naukri has no error (`295` seen, `3` new in latest run).
- Full test suite passed again: 86 tests in 53.279s, `OK`. The GitHub branch source confirms `v2/gemini_extractor.py` sets `EXTRACTION_VERSION = "gemini-shadow-v2"`, and `v2/test_gemini_extractor.py` contains the whitespace-wrap regression test.
- `/api/llm-shadow-status` still shows `enabled=false`, `api_key_configured=false`, calls_today 20/20, 14 successes/6 cached errors, and historical cached results labeled `gemini-shadow-v1`. Historical cache rows are expected to retain their original version and cannot verify runtime code version. No new Gemini API calls were triggered by the validation.
- Next safe check: run inside the container `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml exec -T radar python -c 'from v2.gemini_extractor import EXTRACTION_VERSION; print(EXTRACTION_VERSION)'`. Expect `gemini-shadow-v2`. Also optionally verify config booleans only; do not print environment values or secrets. Do not enable Gemini or configure credentials without explicit approval and a deliberate plan. No source scan is needed.
- Production remains untouched; notifications remain off; PR #35 remains unmerged; no Greenhouse canary until a reviewed fresh sample is available after quota reset and an approved test plan.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both after every prompt. Dev is rebuilt at HEAD `2e168ad`; health OK; 86 tests pass. Branch source contains `gemini-shadow-v2` and new regression test. API status says Gemini disabled/unconfigured and cache rows are old v1; verify imported runtime version directly inside container without scans/API calls. Keep production untouched, notifications off, PR #35 unmerged.”


## 2026-10-12 — Persistent source-error visibility work started
- No deployment: code changes committed directly to v2-live-radar: 150d287 exposes the most recent persisted source-run error from source_runs in GET /api/source-status; 6e78074 updates dashboard source-health rendering to display the persisted error; c3f64c6 adds regression tests for an errored latest run and a later successful run clearing the error.
- CI run #459 (38233473677) was in progress at handover update time; do not claim tests passed until its result is checked.
- No source scan, Gemini API call, source activation, or production change was made. Keep Gemini disabled, notifications off in dev, PR #35 unmerged, and production untouched.
- Next: check V2 CI. If green, update/rebuild only the dev checkout and run full tests plus health/source-status checks. Confirm a simulated/persisted error appears and clears after a successful run. Then choose the next source roadmap item one at a time.
- Continuation: Read both handovers and JOBBEEPER_REFERENCE.md on v2-live-radar. Update both handovers after every prompt. Source status now exposes persisted last_error and dashboard displays it; tests were added but CI was still running. Do not scan sources or call Gemini; production untouched.


## 2026-10-12 — Source-error visibility CI result
- Follow-up to the previous entry: V2 CI run #459 (run ID 38233473677) completed successfully for code commit c3f64c684d47045bcc334e77213d913ad912f67b. PR #35 remains draft/open/unmerged; this is not production approval.
- Documentation updates are on v2-live-radar: knowledge transfer commit da4b0fb42773c2effd6af8b4e6dfed1f3d1dfcf9 and detailed handover commit 65d6825034115cdba8ac183692de37ba8ed80027. Latest branch head after these updates is expected to be 65d6825.
- Next action: in /home/ubuntu/job-beeper-dev, verify clean tree and correct branch, fast-forward only, rebuild only job-radar-dev, run full tests and health/source-status checks. Do not run manual scans, enable Gemini, turn on notifications, or touch production.
- Continuation: Source-error visibility patch passed V2 CI #459. Validate in isolated dev, then continue roadmap one item at a time. Keep production untouched and PR #35 unmerged.


## 2026-10-12 — Dev regression suite result received
- User reports the isolated development test suite completed: `Ran 88 tests in 53.297s` and `OK`. This is a positive test result for the current checkout, but by itself does not confirm the new `/api/source-status` behavior at runtime or dashboard rendering.
- The source-error visibility code is committed on `v2-live-radar` (150d287 API, 6e78074 dashboard, c3f64c6 tests); V2 CI #459 succeeded. No production deployment, source scan, Gemini API call, or source activation.
- Next verification: ask for `curl -fsS http://127.0.0.1:8001/health` and `curl -fsS http://127.0.0.1:8001/api/source-status` output from dev. Confirm `last_error` is present and latest successful run shows null. Then visually check Source Health dashboard. If all good, continue with the reference roadmap’s next item: verify the LinkedIn experience parser patch on dev before considering any main promotion. Keep Gemini disabled, notifications off, and PR #35 unmerged until separately reviewed.
- Continuation: Read both handovers and docs/JOBBEEPER_REFERENCE.md on v2-live-radar; update both handovers after each prompt. Dev reports 88 tests OK in 53.297s. Need health/source-status runtime output and dashboard check before moving to LinkedIn parser validation; production untouched.


## 2026-10-12 — Dev source-status runtime output received
- User ran `curl -fsS http://127.0.0.1:8001/health` and `curl -fsS http://127.0.0.1:8001/api/source-status` in `/home/ubuntu/job-beeper-dev`. Health returned `status=ok`, version `2.0.0`; Naukri was idle after a successful run at `2026-10-12T10:03:49.082163+00:00`, with 292 jobs seen, 2 new, and no runtime error.
- The source-status response includes `last_error` for all four source entries. Naukri has `last_error=null`; LinkedIn, Instahyre, and Greenhouse are disabled and have no run history, as expected. This confirms the patched API response shape and a healthy runtime, but no real persisted error was present to test display/clear behavior.
- Remaining acceptance check: visually inspect the dev Source Health dashboard via the existing SSH tunnel and confirm source errors are rendered when present. Do not induce a real source failure or run a scan solely to test this. Once dashboard rendering is confirmed, proceed to validate the LinkedIn experience-parser patch in dev before any promotion consideration.
- No production deployment, notification change, source activation, manual scan, or Gemini API call. Production port 8000 remains untouched; Gemini remains disabled; dev notifications remain off; PR #35 remains unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar` and update both handovers after every prompt. Dev health is OK and `/api/source-status` includes persisted `last_error`; Naukri had 292 seen / 2 new / no error. Need visual Source Health dashboard confirmation via SSH tunnel, then validate LinkedIn experience parser in dev. No scans or induced failures; keep production untouched, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — Source Health dashboard visually confirmed; LinkedIn parser validation next
- User supplied a screenshot of the dev dashboard at `127.0.0.1:8001/dashboard/#sources` through the SSH tunnel. Source Health table loads correctly: LinkedIn, Instahyre, and Greenhouse show disabled; Naukri Relay shows active; diagnostics display Operational for all four. No visible frontend error or layout issue in the screenshot.
- This completes visual confirmation of the source-status UI in its current healthy/no-error state. Since no source error is present, the screenshot does not prove how a non-null error is rendered; do not force a source failure or run a scan solely for this.
- Start the next roadmap item: validate the committed LinkedIn labeled-experience parser in the isolated dev checkout. The current branch code has `extract_linkedin_labeled_experience` in `v2/radar.py`, documented for labels such as `Experience: 4.00-6.00 Years`. Inspect its call site and regression tests, run targeted tests (then full suite if needed) in dev, and do not enable LinkedIn scanning or promote to main until evidence is green.
- No production deployment, source activation, notification change, scan, or Gemini API call. Production port 8000 remains untouched; Gemini disabled; dev notifications off; PR #35 unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`, update both handovers after every prompt. Dev Source Health screenshot is visually correct (Naukri active; other sources disabled; all diagnostics Operational). Next inspect `extract_linkedin_labeled_experience` call site and regression tests, then validate in dev without enabling LinkedIn or triggering scans. Keep production untouched, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — LinkedIn labeled-experience integration inspected
- User confirmed dev checkout reports clean branch `## v2-live-radar...origin/v2-live-radar`; the grep output shows `extract_linkedin_labeled_experience` supports labeled ranges (`Experience: 4.00-6.00 Years`), plus values and single values. Regression test `test_linkedin_structured_experience_metadata_outside_description_is_captured` in `v2/test_radar.py` mocks the detail HTML, calls `enrich_linkedin_job`, asserts 4.0–6.0 is stored in JD experience fields, and checks matcher rejection for candidate experience 2.
- The detail-fetch call site parses `page_text` for labeled experience before gathering JD description candidates. This is a promising integration regression test; no runtime tests were executed by the assistant and no promotion is approved yet.
- Next command in isolated dev: `python -m unittest v2.test_radar` (or the repository's standard test command) to exercise the focused test and neighboring radar behavior; then run the full suite if green. Do not enable LinkedIn, trigger a source scan, or promote to main as part of this test. Capture exact pass/fail output and investigate any failure before changing code.
- Production port 8000 remains untouched; dev notifications off; Gemini disabled; PR #35 unmerged; no scans or Gemini calls.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. LinkedIn experience parser call site and regression test were inspected. Run `python -m unittest v2.test_radar` in isolated dev, capture output, then full suite if green. Keep LinkedIn disabled, no scans, production untouched, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — Test command adjustment: Python executable
- User attempted `python -m unittest v2.test_radar` from `/home/ubuntu/job-beeper-dev`; the VM shell reports `python: command not found` and suggests `python3`. This is an executable-name/environment issue, not a test failure; no tests ran yet.
- Next try `python3 -m unittest v2.test_radar`. If project dependencies are installed only in its virtual environment, inspect `ls -la` and use the repo's documented venv/test command; do not install packages globally or alter system Python. Capture full output, then run the full test suite if targeted tests pass.
- Keep LinkedIn disabled, do not trigger scans, keep notifications off, Gemini disabled, production untouched, and PR #35 unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. In dev, `python -m unittest v2.test_radar` did not run because `python` executable is missing. Retry using `python3 -m unittest v2.test_radar`; if dependencies are in a venv, use repo's documented environment. No source scan/activation, no production changes, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — Host Python test import failed due to missing dependency
- User ran `python3 -m unittest v2.test_radar` in `/home/ubuntu/job-beeper-dev`; import failed at `from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning` with `ModuleNotFoundError: No module named 'bs4'`. The unittest loader reports one failed import; no radar tests executed.
- Project Docker image installs `v2/requirements.txt` in Python 3.12 container; dev Compose service/container is `radar` / `job-radar-dev`. Prefer testing with the dev container's Python environment (e.g. `sudo docker exec job-radar-dev python -m unittest v2.test_radar` only if the tests are present inside that image; current Dockerfile copies only `v2/radar.py` and related runtime files? Verify test availability before using this exact command). Safer next step is inspect `v2/requirements.txt` and available repo test-run instructions, then use an isolated virtual environment if host tests are needed; do not pip-install into system Python.
- Keep LinkedIn disabled, do not run source scans, notifications off, Gemini disabled, production untouched, PR #35 unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Host `python3 -m unittest v2.test_radar` failed during import because host Python lacks `bs4`; no tests ran. Docker dev container installs app requirements but may not contain tests; verify test availability before choosing container or isolated venv. Never install into system Python. Keep LinkedIn disabled, no scans, notifications off, Gemini disabled, production untouched, PR #35 unmerged.”


## 2026-10-12 — Full test suite passed
- User reports complete dev-container suite: `Ran 88 tests in 53.229s`, `OK`.
- Targeted radar module and complete suite both pass in the isolated dev container. This is test evidence only; it does not authorize production deployment or enabling LinkedIn.
- Next: inspect CI status for current `v2-live-radar` commits and review exact parser patch / release diff. Only then decide on reviewed promotion to `main`. No live scan or Gemini API call.
- Guardrails unchanged: LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


## 2026-10-12 — Release diff blocked by missing local base ref
- Dev checkout is clean and aligned with `origin/v2-live-radar`; HEAD was `54fc75c` (`docs: record source status CI success`). Recent five commits are documentation commits; this alone does not establish whether the parser patch is in the branch history.
- The requested `git diff origin/main...HEAD -- v2/radar.py v2/test_radar.py` failed with `fatal: bad revision 'origin/main...HEAD'`, so the code diff has not been reviewed. Likely issue is an absent/unfetched local `origin/main` ref; verify with `git remote -v` and `git branch -a` before fetching/comparing.
- Full dev-container suite reported green: 88 tests in 53.229s. Continue with read-only remote/branch and file-history checks, then fetch the intended base ref if appropriate and inspect the exact parser/test diff. Do not promote to `main` until review and CI evidence for the relevant code commit.
- Safety constraints: LinkedIn disabled; notifications off; Gemini disabled; no live scans/API calls; production port 8000 and its DB/config untouched; PR #35 remains unmerged.
- Continuation: Read both handovers plus `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Review is paused on missing `origin/main` ref. Run the prescribed read-only diagnostics, then safely establish the base ref and inspect parser/test changes before any release decision.


## 2026-10-12 — Base branch identified; release scope is broad
- User's read-only diagnostics show only `origin` remote URL configured and only `v2-live-radar` plus `origin/v2-live-radar` refs locally. HEAD is `54fc75c`, a docs-only commit. File history confirms LinkedIn experience parser/test commits exist in branch history: `6ac58a1 Fix LinkedIn labeled experience extraction before alert decisions` and `22496f9 Add regression tests for LinkedIn labeled experience metadata`.
- GitHub compare API for `main...v2-live-radar`: status `diverged`, branch is 87 commits ahead and 4 behind; merge base `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`, main SHA `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`. Changed files include README, dashboard, three docs, dev config/compose, Gemini shadow extractor/tests, `v2/radar.py` (139 additions/4 deletions) and `v2/test_radar.py` (157 additions). Therefore do not promote the full branch as one unreviewed change.
- Main versions of `v2/radar.py` and `v2/test_radar.py` do not contain the new `extract_linkedin_labeled_experience` helper / named regression test. Branch does contain them. Workflow lookup for abbreviated parser commit `6ac58a1` returned no PR-triggered workflow runs; CI for the exact parser code commit is not yet verified.
- Next safe step on VM: `git fetch origin main` (updates remote-tracking ref only), then inspect `git diff origin/main...HEAD -- v2/radar.py v2/test_radar.py` and full changed-file list. Keep scope focused; don't merge the entire divergent branch or deploy. Full dev container test suite reported green (88 tests). Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.
- Continuation: Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. The parser fix exists on dev but is absent from main; branch is 87 ahead/4 behind and contains unrelated Gemini/UI/docs work. Fetch main ref safely, review the exact parser/test diff and CI before release. No production promotion.


### Parser diff review follow-up — 2026-10-12
- User ran `git fetch origin main`; it fetched main into `FETCH_HEAD` but did not create `refs/remotes/origin/main`, so `git diff origin/main...HEAD` failed with `fatal: bad revision 'origin/main...HEAD'`.
- Safe correction requested: `git fetch origin main:refs/remotes/origin/main`, verify `git show -s --oneline origin/main` and `HEAD`, then rerun the scoped diff for `v2/radar.py` and `v2/test_radar.py`. No app files changed, no deployment/rebuild, production untouched.
- Await the actual diff before judging or promoting the LinkedIn experience parser fix. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, and PR #35 unmerged.
- Continuation: read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar` at the start of the next turn; update both handovers after every user prompt. Review the fetched parser/test diff and confirm relevant CI before any release plan.


### LinkedIn parser diff reviewed — 2026-10-12
- User successfully created `origin/main` locally with `git fetch origin main:refs/remotes/origin/main`; refs: `origin/main=a1db74f`, dev HEAD `54fc75c`. Scoped diff reports `v2/radar.py` +143/-4 and `v2/test_radar.py` +157 lines vs merge-base/main.
- Reviewed parser helper `extract_linkedin_labeled_experience`: parses explicitly labeled numeric ranges, plus values, and single values. Detail enrichment reads full LinkedIn page text for this label and prefixes the selected JD text when needed. Regression test fixture has `Experience: 4.00-6.00 Years` outside description and asserts extracted 4–6 years plus rejection against candidate max 2 years. Also a test checks generic experience snippet does not skip JD enrichment.
- Important scope issue: `v2/radar.py` diff also imports `v2.gemini_extractor`, so this is not a parser-only change. Do not cherry-pick/merge the whole radar/test files or promote the divergent branch. The pasted terminal diff stopped before the rest of the hunk/test diff, but GitHub source inspection confirms the helper and regression fixture. Need isolate the minimum parser-only change from Gemini shadow wiring and run targeted/full tests + CI for that isolated patch.
- Current state unchanged: no deployment, no merge, production untouched. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.
- Next step: inspect the remaining diff for non-parser hunks and CI status, then prepare a narrowly scoped parser-only patch against current `main` (prefer separate clean worktree/branch or explicit patch); run the regression and full dev container suite before any reviewed release.


### Parser patch isolation identified — 2026-10-12
- Full user-provided diff confirms the parser fix is already isolated in two dedicated commits: `22496f9714a7628d4c93929005a2d10773a753cc` adds only `v2/test_radar.py` regression tests; `6ac58a1d4757c3c545203b84a61f4f8058d4747b` changes only `v2/radar.py` for labeled LinkedIn experience extraction. Commit diffs verified via GitHub; unlike aggregate branch diff, neither commit contains Gemini or source-status changes.
- Aggregate diff also includes Gemini shadow extraction/wiring/API and persisted source-health changes, which must not be included in the parser-only release. Main SHA observed by user: `a1db74f`; dev HEAD `54fc75c`. No production changes.
- Recommended isolation path: create a fresh local branch from `origin/main` in a separate worktree or after ensuring the existing dev checkout has no uncommitted changes, cherry-pick the two exact parser commits, inspect the resulting diff, and test before pushing/opening a parser-only PR. Suggested order: test commit `22496f9`, then implementation `6ac58a1`; stop if cherry-pick conflicts rather than resolving blindly. Do not cherry-pick source-status or Gemini commits. Confirm CI for the resulting isolated branch; existing 88-test result was on the aggregate dev branch and is not a substitute for isolated-branch CI.
- Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged. Do not merge or deploy until isolated diff and tests are green.


### Parser worktree cherry-pick paused on Git identity — 2026-10-12
- User created clean worktree `/home/ubuntu/job-beeper-parser-fix` from `origin/main` at `a1db74f`, branch `fix/linkedin-experience-parser`. Original dev checkout `/home/ubuntu/job-beeper-dev` reported clean before worktree creation.
- First cherry-pick (`22496f9714a7628d4c93929005a2d10773a753cc`, tests-only) applied changes but could not create commit because Git committer identity is unset. Second cherry-pick attempt was rejected because the first pick's changes remain in worktree/index. This is not yet a code conflict; likely paused cherry-pick state.
- Recovery: in parser worktree, set repo-local Git identity to the user's intended commit name/email (do not use `--global` and do not invent their email), inspect `git status`, then if the first pick is still in progress and its intended changes are staged, run `git cherry-pick --continue` (do not rerun first cherry-pick). After it succeeds, cherry-pick implementation commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`. Stop and share output if status indicates conflicts or unexpected changes.
- No push, CI, deployment, or production changes. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Git identity check follow-up — 2026-10-12
- User checked `git config user.name` and `git config user.email` in `/home/ubuntu/job-beeper-parser-fix`; both returned blank, confirming repo-local identity is unset. No `git status`/cherry-pick state output provided yet.
- Next: check whether `/home/ubuntu/job-beeper-dev` already has a valid repo-local identity (`git -C /home/ubuntu/job-beeper-dev config user.name` and `... user.email`) and inspect parser worktree state (`git status`, `git diff --cached --stat`, `git rev-parse -q --verify CHERRY_PICK_HEAD`). Do not invent identity values, reset changes, or retry cherry-pick. Set parser worktree identity from user's actual configured identity only, then continue pending pick if confirmed safe.


### Parser cherry-pick ready to continue — 2026-10-12
- Confirmed parser worktree is mid-cherry-pick of `22496f9714a7628d4c93929005a2d10773a753cc`; no conflicts remain and only `v2/test_radar.py` is staged (+82 lines). `CHERRY_PICK_HEAD` matches the expected commit. Existing dev worktree also has no configured user.name/user.email.
- Safe next step is set repository-local identity in parser worktree using the user's actual chosen commit name/email, then run `git cherry-pick --continue`. Do not use guessed identity values. After completion, apply implementation commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`, stopping if any conflict. No push or deployment yet.


### Parser-only branch created successfully — 2026-10-12
- User reports isolated branch `fix/linkedin-experience-parser` now has two commits: `715b94d Add regression tests for LinkedIn labeled experience metadata` and `9b9cbf1 Fix LinkedIn labeled experience extraction before alert decisions`.
- Reported diff versus `origin/main`: only `v2/radar.py` and `v2/test_radar.py`, 149 insertions and 3 deletions. This matches the intended parser-only scope; full diff content has not yet been reviewed in this conversation.
- Next action: inspect full diff (`git diff origin/main...HEAD -- v2/radar.py v2/test_radar.py`) and working-tree status before running tests. Do not push or deploy yet. Then test in an isolated environment/CI for this branch, not by running the live dev container against the wrong checkout. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Parser diff reviewed; isolated test setup next — 2026-10-12
- User supplied the complete `origin/main...HEAD` diff for `fix/linkedin-experience-parser`; `git status --short` was empty. Diff touches only `v2/radar.py` and `v2/test_radar.py` (149 insertions, 3 deletions), with the expected test and implementation commits.
- Code review: implementation explicitly parses labeled LinkedIn metadata before generic JD experience extraction and avoids treating generic search-snippet year mentions as sufficient to skip JD enrichment. Regression tests cover metadata outside description and incidental snippet years. No obvious scope creep in the shown diff. Testing is still required; edge cases/runtimes are not yet verified.
- Next step: inspect the dev container's image/mount/config so tests can run against the parser worktree in a separate, temporary container/environment. Do not use `docker exec -w /app job-radar-dev` as that tests the live dev checkout, not this worktree. No push/PR/deployment yet. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Isolated parser test environment identified — 2026-10-12
- User reports image `job-radar-dev-radar`; the running dev container mounts only its persistent dev data volume at `/data` and `/home/ubuntu/job-beeper-dev/v2/config.dev.json` at `/app/v2/config.json`. Parser worktree `9b9cbf1` is clean (`git status --short` empty).
- Safe test approach: run a disposable container from the same image with `--network none`, mount `/home/ubuntu/job-beeper-parser-fix` at `/app:ro`, and use `--entrypoint sh` so no app server starts. Run the two focused `v2.test_radar.MatcherTests` regression tests first, then full `python -m unittest discover -s v2 -p 'test_*.py'` only if focused tests pass. Do not mount production/dev data or config; do not execute tests inside `job-radar-dev` because that uses the other checkout. If tests require writable paths, add only temporary container-local/tmpfs paths after examining failure output.
- No push/PR/deployment yet. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Parser regression tests passed; full suite next — 2026-10-12
- User ran both focused regression tests against `/home/ubuntu/job-beeper-parser-fix` in disposable container `job-radar-dev-radar`, with `--network none` and source mounted read-only. Result: `Ran 2 tests in 0.149s`, `OK`; one expected mocked LinkedIn discovery log, no live network.
- Next run full suite in same isolated mode: `sudo docker run --rm --network none --entrypoint sh -v /home/ubuntu/job-beeper-parser-fix:/app:ro -w /app job-radar-dev-radar -lc 'python -m unittest discover -s v2 -p "test_*.py"'`. Capture complete output. If suite passes, inspect test summary and then push branch/open narrow PR for CI/review; no deployment or merge without review. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Full isolated parser suite passed — 2026-10-12
- User ran the full test suite in the disposable no-network container against `/home/ubuntu/job-beeper-parser-fix` mounted read-only. Result: `Ran 78 tests in 53.319s`, `OK`.
- Focused regression tests also passed earlier (`Ran 2 tests in 0.149s`, `OK`). Isolated patch is two commits and only `v2/radar.py` + `v2/test_radar.py` changed (149 insertions, 3 deletions); clean working tree reported before testing.
- Next: push only `fix/linkedin-experience-parser` and open a narrow PR targeting `main`, then confirm its CI. Do not merge/deploy without review/approval. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### PR #35 status rechecked — 2026-10-12
- User shared https://github.com/AvinashBhalla/job-beeper/pull/35. GitHub confirms PR #35 remains open, draft, unmerged; base `main`, head `v2-live-radar` at `c194ef18da03a8472d8af796f813cc6ce5a5b333`; 11 files, 111 commits, broad development integration diff. No submitted reviews or conversation comments were returned.
- Diagnosis: PR #35 is the existing broad Gemini shadow-mode/integration draft and is not a safe vehicle for the narrow LinkedIn experience parser fix. Do not merge PR #35 to ship that fix.
- Latest isolated parser evidence remains: `fix/linkedin-experience-parser`, two commits based on production `main` `a1db74f`, only `v2/radar.py` and `v2/test_radar.py` changed (149 insertions, 3 deletions); focused tests 2/2 and full suite 78/78 passed in a no-network disposable container. The branch has not yet been confirmed pushed and has no dedicated PR/CI result.
- Production impact: none confirmed; no merge/deployment was performed. Keep LinkedIn disabled in dev, notifications off, Gemini shadow disabled, and production port 8000 untouched.
- Next action: user should run the previously supplied push checklist in `/home/ubuntu/job-beeper-parser-fix`: `git status --short`, `git fetch origin main`, `git diff --stat origin/main...HEAD`, `git push -u origin fix/linkedin-experience-parser`. Confirm clean worktree and narrow diff before push; then open a PR targeting `main` and inspect CI. No merge/deploy until review and explicit approval.


### LinkedIn parser fix PR opened — 2026-10-12
- User pushed `fix/linkedin-experience-parser` successfully. Remote branch tracks origin; diff versus `main` is limited to `v2/radar.py` and `v2/test_radar.py`, 149 insertions and 3 deletions; two commits ahead, zero behind, based on `main` SHA `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`.
- Opened dedicated PR #36: https://github.com/AvinashBhalla/job-beeper/pull/36 — title `Fix LinkedIn labeled experience extraction`, base `main`, head `fix/linkedin-experience-parser`, not draft, open and unmerged. GitHub reports mergeable; V2 CI was in progress at last check.
- Validation before push: targeted regression tests 2/2 passed and full isolated no-network suite 78/78 passed. CI still needs to finish; do not treat it as passed yet.
- No production deployment or live LinkedIn scan. Keep dev LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched. PR #35 remains a separate broad draft and must not be used to ship this fix.
- Next: inspect PR #36 checks until V2 CI completes; if green, review the exact two-file diff and arrange review/approval before any merge. If CI fails, inspect logs and fix only on `fix/linkedin-experience-parser`, then rerun tests. Do not merge/deploy yet.


### PR #36 CI failure — investigation required — 2026-10-12
- GitHub Actions run #543 for PR #36 (`V2 CI`, run ID `38273658480`) completed with failure. Syntax/compile and dependency install passed; full unittest step failed: 78 tests, 5 failures.
- Failures: `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_linkedin_fast_scan_uses_broader_recency_window`, `test_linkedin_skips_deep_scan_after_fast_lane_rate_limit`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`. New structured-experience regression test passed. Need establish whether these failures are baseline/environmental or caused by patch before changing code.
- CI logs show the fast-scan tests made zero mocked calls and the enrichment test retained its original description. Do not dismiss as flaky without a baseline run and test-isolation review.
- PR #36 remains open/unmerged. No production deployment/live LinkedIn scan. Keep LinkedIn disabled in dev, notifications off, Gemini disabled, production port 8000 untouched; PR #35 remains separate and unmerged.
- Next: compare CI results on `main` baseline and inspect affected tests/LinkedIn cooldown global state; reproduce exact full-suite command on the isolated worktree. Make the smallest evidence-backed fix on `fix/linkedin-experience-parser`, rerun focused and full tests, then push and verify CI. Do not merge/deploy.


### Baseline test comparison — 2026-10-12
- User confirmed `origin/main:v2/test_radar.py` contains at least three of the CI-failing tests: `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_new_linkedin_job_is_enriched_from_jd_before_matching`, and `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`. This only confirms test definitions exist on baseline; it does not show whether baseline CI passes or fails.
- Parser worktree remains at `9b9cbf1` on `fix/linkedin-experience-parser`; output showed two commits and no visible dirty-status lines. CI run #543 still failed 5 tests (four LinkedIn scan/cooldown tests and one JD-enrichment test). Need execute full suite against `origin/main` to separate baseline failures from patch regressions.
- Next action for user: create a separate baseline worktree at `/tmp/job-beeper-main-baseline` from `origin/main`, run the full unittest suite inside the same `job-radar-dev-radar` image with `--network none`, then share the summary/failures. Do not alter or reset the parser branch, and do not merge/deploy. If baseline fails the same tests, investigate shared test environment/global state; if baseline passes, inspect patch/test interaction.


### Parser PR focused-test invocation — 2026-10-12
- Confirmed the separate baseline run on `origin/main` passed: 76 tests, `OK`. PR #36 CI on the parser branch still reports 5 failures (four LinkedIn scan/cooldown tests and `test_new_linkedin_job_is_enriched_from_jd_before_matching`); do not merge or deploy until isolated and fixed.
- First focused-test invocation from `/app` failed to import `test_radar`; second invocation from `/app/v2` found `test_radar.py` but failed because its `import v2.radar` requires repository root on `sys.path`. Neither invocation executed tests.
- Correct focused invocation: mount the isolated parser worktree read-only at `/app`, set container workdir to `/app`, and use fully qualified test names `v2.test_radar.MatcherTests...` in the existing `job-radar-dev-radar` image with `--network none`. Await output before making a code change.
- Production remains untouched (port 8000); dev LinkedIn and notifications remain disabled. PR #36 remains unmerged.
- Next action: run the corrected focused command, inspect the actual test results, then make only evidence-backed changes and rerun focused plus full suites. Keep both handover docs synchronized after each prompt.


### Parser PR focused tests passed; full-suite investigation is next — 2026-10-12
- Correct focused test invocation was run from repository root `/app` in a disposable container, with the parser worktree mounted read-only and container networking disabled. Output: `Ran 3 tests in 32.100s — OK`. Passing tests: `test_linkedin_fast_lane_and_periodic_deep_scan`, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`.
- This confirms the focused cases pass individually/together but does not explain PR #36 CI run #543 (run ID `38273658480`), which failed five tests in the full suite. The `origin/main` baseline passed 76 tests. Earlier CI symptoms: four LinkedIn scan/cooldown tests appear to cascade after HTTP 429 cooldown state, while `test_new_linkedin_job_is_enriched_from_jd_before_matching` failed in the full suite despite passing in the focused run. Treat this as an investigation hypothesis, not a confirmed root cause.
- Next: run the complete suite on branch `fix/linkedin-experience-parser` in the same no-network container; capture the full output, failure tracebacks and test ordering. Reproduce each implicated test alone and in combinations. Inspect global cooldown/config/mock cleanup and order-dependent state before changing parser code. Make the smallest evidence-backed correction; rerun focused tests, the full suite, and verify PR #36 CI.
- Test invocation must use workdir `/app` and fully qualified names `v2.test_radar.MatcherTests...`; `/app/v2` causes `ModuleNotFoundError: No module named 'v2'`, while running from `/app` with unqualified `test_radar` causes `No module named 'test_radar'`. Those attempts did not execute tests.
- PR #36 (`fix/linkedin-experience-parser` → `main`) remains open/unmerged. Do not merge/deploy with CI red. Keep production port 8000 untouched, LinkedIn disabled in dev, notifications off, and Gemini shadow mode disabled. PR #35 remains separate/unmerged.

## PR #36 full-suite failure follow-up — 2026-10-12
- Direct GitHub inspection: PR #36 remains open/unmerged, base main `a1db74f`, head `9b9cbf1`, only `v2/radar.py` and `v2/test_radar.py` changed. Actions run #543 (`38273658480`) failed at the unittest step; install/compile succeeded; 78 tests, 5 failures.
- Log evidence: four LinkedIn scan tests are skipped with log `linkedin scan skipped; rate-limit cooldown has 299s remaining`, causing zero-call/empty-parameter assertions. This strongly suggests leaked module-level cooldown state from earlier tests. The separate JD enrichment failure has `'JD:' not found`; its test patches `radar.requests.get`, while implementation routes fetches through `_linkedin_http_get`. Confirm exact cause with isolated suite/order reproduction before code changes.
- Focused tests pass (3/3), baseline main passed 76 tests; neither result overrides red full-suite CI. No code changed and no deployment. Full local suite has not yet been executed from the current turn due no VM shell access.
- Next action: run requested disposable Docker full-suite command from `/home/ubuntu/job-beeper-parser-fix`, with read-only source mount and network disabled; then run failing tests solo and in combinations. Inspect cooldown global/state restoration and the HTTP mock seam; fix only the demonstrated root causes. Push/retest and verify PR CI before any merge recommendation.
- Safety unchanged: production 8000 untouched; dev LinkedIn disabled, notifications and Gemini disabled; PR #35 separate. Do not evade LinkedIn limits or merge/deploy while red.

## Isolated full-suite reproduction received — 2026-10-12
- The exact prescribed Docker command was run from `/home/ubuntu/job-beeper-parser-fix` with networking disabled, parser worktree mounted read-only at `/app`, and `/app` as working directory.
- Complete test output ended `Ran 78 tests in 53.229s — OK`. All five failures from CI run #543 pass in this full-suite run, including the four LinkedIn scan tests and the JD enrichment test. The 429 cooldown tests appear later in the output, so the simple cooldown-leak theory is not confirmed by this ordering and should not be treated as root cause.
- CI run #543 (ID `38273658480`) still reports failure on PR head `9b9cbf1195f57a34f5539b31a06c3ce476bcdcc7`; PR remains open/unmerged. Local green is not sufficient to merge.
- Next: run the five tests separately and in combinations, repeat the suite to probe intermittency, compare Python/dependency versions and workflow setup with CI, then make a minimal evidence-based fix only if failure reproduces. No code changes or deployment in this turn. Keep PR #35 separate; production 8000 untouched, dev LinkedIn disabled, notifications/Gemini disabled.

## Test command clarification — 2026-10-12
- Important correction to the next-step instructions: piping full `unittest discover` output through `grep` only filters displayed lines; it does not run an individual test in isolation. Do not use that as proof of isolated reproduction.
- The recorded full isolated suite result remains 78/78 passing, while CI run #543 remains red. For the next diagnostic pass, select each test case by exact method name from the discovered suite and run each in a fresh Python process; then compare CI Python/dependency/workflow configuration. No code change or merge/deploy until root cause is established.

## Individual test command correction — 2026-10-12
- The user-provided five-heading loop ran full `unittest discover` five times and only filtered the output with `grep`; it did not isolate the named tests. Each full-suite run passed all 78 tests.
- Use `python -m unittest v2.test_radar.MatcherTests.<exact_test_method> -v` from `/app` to execute exactly one named method. Run each of the five CI-failing methods in a fresh invocation within the network-disabled Docker container, with source mounted read-only. Continue to compare environment/workflow only after obtaining true isolated results. No code changes, merge, or deployment authorized.

## CI command/import-mode discrepancy — 2026-10-12
- All five formerly failing tests now pass in true individual invocations (`python -m unittest v2.test_radar.MatcherTests.<method> -v`), and the full suite has repeatedly passed 78/78 using `discover -s v2 -t .`.
- CI run #543 logs show Ubuntu 24.04 and CPython 3.12.15; workflow executed `python -m unittest discover -s v2 -p 'test_*.py' -v` without `-t .`, producing five failures in 20.472 seconds. The local command used a different unittest discovery/import mode (`v2.test_radar` vs CI's `test_radar`). This is a confirmed setup difference, but not yet confirmed as the cause.
- Next: run the exact CI unittest command inside the network-disabled disposable container from `/app`, with source mounted read-only and omit `-t .`. Then compare environment/dependency versions if needed. Do not change application code based on assumptions. PR #36 stays open/unmerged; production/dev safety restrictions unchanged.


## Exact CI command passes locally; environment comparison next — 2026-10-12
- User ran the exact GitHub Actions unittest discovery command inside the disposable container against `fix/linkedin-experience-parser`: `python -m unittest discover -s v2 -p "test_*.py" -v` (without `-t .`), from `/app`, source mounted read-only and container network disabled.
- Result: `Ran 78 tests in 53.319s — OK`. All five tests previously failing in CI run #543 passed in this exact-command local run. The output shows the four LinkedIn scan tests and JD enrichment test passing; cooldown/rate-limit tests also pass.
- This disproves the simple hypothesis that omitting `-t .` alone reproduces the CI failure. Import/discovery mode differs from the earlier local command, but the exact CI command still passes in the available container. Root cause remains unresolved; do not label CI flaky or change application code without evidence.
- CI environment previously confirmed as Ubuntu 24.04.5 / CPython 3.12.15 with fresh installs from `v2/requirements.txt`; local container's Python and installed dependency versions have not yet been compared. Likely next diagnostic: report `python --version`, `python -m pip freeze`, OS release, and the exact dependency constraints from `v2/requirements.txt` inside the same test container, then compare against CI log/install output. If practical, reproduce CI's Python 3.12.15 and fresh dependency resolution in a disposable container; preserve network-disabled test execution after dependencies are available.
- No code change, push, merge, or deployment in this turn. PR #36 remains open/unmerged. Production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 remains separate.
- Next user action: run the environment fingerprint command in the latest chat response and paste the output. Then compare with the CI job log and decide whether a dependency/runtime mismatch or order-dependent nondeterminism is supported.


## Runtime/dependency comparison received; inspect earlier cooldown mutation — 2026-10-12
- User supplied the local isolated-container fingerprint: CPython 3.12.15, pip 25.0.1, Debian GNU/Linux 13 (trixie). Installed packages include FastAPI 0.143.0, Starlette 1.7.0, requests 2.34.2, BeautifulSoup 4.15.0, tzdata 2026.5 and the same other versions reported in the prior CI log. Requirements are broad ranges in `v2/requirements.txt`, so they do not pin reproducible dependency versions. CI ran CPython 3.12.15 on Ubuntu 24.04.5; Python and visible dependency versions align, but the OS differs (Debian 13 vs Ubuntu 24.04).
- Re-read Actions run #543 logs. Before the four scan failures, each scan reports `linkedin scan skipped; rate-limit cooldown has 299s remaining`; the JD enrichment test then fails because no `JD:` enrichment was appended. This confirms the failures share a pre-existing cooldown state in the CI process, not five independent assertions. The exact local CI command passes 78/78, so root cause still needs order/state reproduction.
- Important test isolation issue to investigate: tests mutate module-level LinkedIn cooldown state (`linkedin_rate_limited_until_monotonic`, `linkedin_last_rate_limit_monotonic`, `linkedin_rate_limit_streak`, `linkedin_rate_limit_generation`). Some tests save/restore this state, but CI's cooldown is already active before the four scan tests run. Identify the earliest preceding test or import/runtime behavior that activates it; do not merely suppress cooldown checks.
- No source change, push, merge or deployment in this turn. PR #36 remains open/unmerged; production 8000 untouched, dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 separate.
- Next diagnostic: run the exact CI suite repeatedly in fresh disposable processes to check whether the early cooldown state is intermittent, and inspect the CI log from the first occurrence of `HTTP 429`/cooldown activation and the tests immediately preceding it. Prefer a minimal test-order reproduction and explicit cleanup of test-owned global state if proven; do not change production rate-limit behavior without evidence.


## Root cause found: scan test leaked a real LinkedIn 429 — 2026-10-12
- Re-inspected Actions run #543 and source around the failure. The log shows `test_linkedin_fast_lane_and_periodic_deep_scan` completing its mocked search scans, then `linkedin JD enrichment stopped after HTTP 429`, followed by the next fast-lane tests seeing a 299-second global cooldown. The JD-enrichment test also fails because cooldown prevents the detail request.
- Root cause: the pagination test mocks `_linkedin_request` but not `enrich_linkedin_job`. The parser fix correctly no longer trusts a generic search snippet like `2 years experience` as authoritative labeled metadata, so `linkedin_collect` now queues a matching candidate for JD enrichment. In GitHub Actions (network-enabled), the test unexpectedly performs a real LinkedIn detail request and gets HTTP 429; the process-global cooldown then cascades into later tests. The no-network local container did not reproduce the real 429, explaining the green local suite.
- Evidence-based test-only fix committed directly to `fix/linkedin-experience-parser`: `572f56573fa8f66a532ee676c2aa66b25a843d0a` (`test: prevent live LinkedIn enrichment in scan pagination test`). In `v2/test_radar.py`, `test_linkedin_fast_lane_and_periodic_deep_scan` now also mocks `enrich_linkedin_job` to return the job unchanged, keeping a pagination test hermetic and preventing live HTTP/cooldown leakage. The exact replacement was fetched back and verified. Production application code was not changed by this follow-up.
- Validation is pending: local focused/full tests and the new GitHub Actions run have not yet been confirmed green. PR #36 remains open/unmerged; do not merge/deploy until checks pass. No production impact.
- Next user action: in `/home/ubuntu/job-beeper-parser-fix`, fast-forward the local branch to the new commit, run the focused pagination test and the full suite in the same isolated `--network none` container, then inspect PR #36 CI. If CI remains red, use the new exact failure/log sequence rather than assuming this fully resolved all failures.
- Safety unchanged: production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 separate/unmerged.


## Validation received: hermetic test fix passes locally — 2026-10-12
- User fast-forwarded `/home/ubuntu/job-beeper-parser-fix` cleanly to `572f56573fa8f66a532ee676c2aa66b25a843d0a` (`test: prevent live LinkedIn enrichment in scan pagination test`); the shown `git status --short` produced no changes before the pull.
- Focused test passed in the disposable `job-radar-dev-radar` container with `--network none`: `v2.test_radar.MatcherTests.test_linkedin_fast_lane_and_periodic_deep_scan` (1/1).
- Full suite passed in that same network-disabled container: `python -m unittest discover -s v2 -p "test_*.py" -v`, 78/78 in 37.205s. Output confirms the previously affected scan tests and JD enrichment test pass without live LinkedIn requests.
- GitHub Actions run #592 (ID `38284476851`) for this head is completed/success, but the connected job listing exposes only a successful job named `syntax`. Do **not** describe the complete CI test suite as green based on that run alone; local full suite is green, prior run #543 had failed, and CI coverage needs confirmation if a dedicated test job is expected.
- PR #36 is still OPEN and UNMERGED, head `572f56573fa8f66a532ee676c2aa66b25a843d0a`, base `main`. No merge/deploy authorized or performed.
- Next: inspect PR checks/workflow configuration to establish whether the successful `syntax` job is the only configured check or whether the test job did not run. If the test job is absent, verify why before considering merge. Keep production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 remains separate.


## CI fully verified; next step is PR review, not another local run — 2026-10-12
- Follow-up repo check resolved the earlier ambiguity: `.github/workflows/v2-ci.yml` on `fix/linkedin-experience-parser` defines one job named `syntax`, and that job explicitly runs both `python -m py_compile v2/radar.py v2/test_radar.py` and `python -m unittest discover -s v2 -p 'test_*.py' -v`. The job name is misleadingly broad; it is not syntax-only.
- GitHub Actions run #592, ID `38284476851`, completed with conclusion `success`. Job `syntax` step 6 (`python -m unittest discover -s v2 -p 'test_*.py' -v`) is completed/success. Run URL: https://github.com/AvinashBhalla/job-beeper/actions/runs/38284476851. The earlier run #543 failed specifically at this full-suite step before the test isolation fix.
- PR #36 remains OPEN, UNMERGED, mergeable, targeting `main`; head `572f56573fa8f66a532ee676c2aa66b25a843d0a`. The reviewed diff contains only `v2/radar.py` and `v2/test_radar.py` (156 additions, 4 deletions). Local focused test and local full suite both pass; GitHub Actions full suite also passes. No further test command is required now.
- Recommended next step: review the PR diff and repository policy/required approvals, then merge PR #36 only with the user's explicit authorization. Do not deploy production as part of this parser fix unless separately requested. Preserve safety: production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 remains separate.


## PR #36 final review checkpoint — 2026-10-12
- User asked “what next?”; no code changes requested or made in this turn.
- Rechecked PR #36: https://github.com/AvinashBhalla/job-beeper/pull/36 remains open, not merged, mergeable, base `main`, head `fix/linkedin-experience-parser` at `572f56573fa8f66a532ee676c2aa66b25a843d0a`. Scope remains `v2/radar.py` and `v2/test_radar.py`; 156 additions, 4 deletions.
- Current GitHub review submissions: none returned. Inline review threads: none returned. This means there are no recorded reviews or inline threads in those endpoints; it does not establish that an external approval policy is unnecessary.
- Prior verified validation remains: isolated local suite 78/78 passed and GitHub Actions run #592 passed on the PR head. No merge or deployment performed.
- Recommended next action: inspect the current PR checks/branch protection and request an authorized maintainer review if required. Then, after explicit user authorization and any required approval, merge PR #36 into `main`. Keep deployment separate and preserve production DB/volume/env; do not enable LinkedIn or notifications as part of merge.
- Safety and goal: maintain reliable source discovery and accurate matching while avoiding live LinkedIn requests during tests and protecting production. No code/config/runtime changes in this turn.
- Continuation prompt: “Read the latest dated handoff sections in `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`. Recheck PR #36 status, current required checks and branch protection. Do not merge or deploy without explicit authorization. If approved, merge only PR #36 to main; keep PR #35 separate and production rollout separate.”


## PR #36 merged — 2026-10-12
- User confirmed “merged”; live GitHub verification confirms PR #36 is `closed` and `merged: true`, merged at 2026-10-12T17:45:33Z.
- PR: https://github.com/AvinashBhalla/job-beeper/pull/36
- Merge commit on `main`: `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. PR head: `572f56573fa8f66a532ee676c2aa66b25a843d0a`. Scope: `v2/radar.py` and `v2/test_radar.py`.
- Before merge, isolated local tests passed 78/78 and PR-head GitHub Actions run #592 was green. Check CI on the merge commit before any release action; do not infer it from PR-head CI.
- No production deployment was performed or verified in this turn. Keep production DB/volume/env unchanged, keep dev LinkedIn disabled and notifications off, and do not trigger live LinkedIn scans as a smoke test.
- Next action: verify CI for merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; then inspect clean git state, production/development checkout and Compose/volume identity, take a verified backup, and only then plan a separately authorized controlled deployment.
- Goal remains reliable multi-source discovery and correct matching with isolated tests and production-safe rollout. No runtime/deployment changes in this turn.
- Continuation prompt: “Read the latest dated sections in `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`. PR #36 was merged to main at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. Check merge-commit CI first, then prepare a production-safe deployment checklist. Do not deploy, enable LinkedIn, or enable notifications without explicit authorization and verified backups/volume identity.”


## Merge-commit CI verification and rollout preparation — 2026-10-12
- User asked the assistant to carry out the next step after PR #36 merged.
- Rechecked PR #36 directly: closed and merged; merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; PR head `572f56573fa8f66a532ee676c2aa66b25a843d0a`. PR-head Actions run #592 (`38284476851`) had passed the full suite before merge (78 tests).
- Checked the merge commit through the connected commit-workflow-runs and combined-status endpoints. The workflow-runs wrapper only returns PR-triggered runs and returned no merge-commit run; combined commit status returned an empty status list for both merge commit and PR head. GitHub web access was unavailable in this session. Therefore **merge-commit CI remains unverified**; do not claim it passed or failed.
- No production VM/shell connection is available in this task context, so the current production/development checkout, containers, Compose project, database volume, env, and live health have not been inspected. No backup was taken and no deployment/restart/config change was performed.
- Safety: do not switch production or run live LinkedIn requests as a smoke test. Preserve production DB/volume/env; dev LinkedIn stays disabled; notifications and Gemini shadow stay off; PR #35 remains separate.
- Exact next action: obtain CI run/check evidence for merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` from GitHub Actions; then use a shell session on the Oracle VM to inspect git status, current commit/branch, Compose project/service/container and mounted volume identity, and health endpoints without changing runtime. Only after identity and clean state are verified should a timestamped DB/config backup be taken and validated. Deployment remains a separate explicit decision.
- Continuation prompt: “Read the newest sections of `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`. PR #36 is merged at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. PR-head CI passed, but merge-commit CI is still unverified because available endpoints returned no runs/statuses. First obtain Actions evidence for the merge commit. Then inspect production/development VM state read-only; do not deploy, restart, enable LinkedIn, or enable notifications without verified backup/volume identity and explicit authorization.”


## Read-only production inspection commands — 2026-10-12
- User requested the shell commands needed to continue the post-PR #36 checks. No code change and no production action taken.
- First command block checks hostname, time, user, repository branch/status/HEAD in `/home/ubuntu/job-beeper` and `/home/ubuntu/job-beeper-dev`.
- Second block should inspect running containers, Compose projects/services, container image/health/restart state, and mounts without printing environment variables or secrets. Do not use `docker inspect .Config.Env`, `env`, `printenv`, or `cat .env`.
- Third block should inspect Compose configuration and relevant health endpoints only after confirming the service names/ports from the prior output. Do not run pull/build/up/down/restart, migrations, scans, or notification sends.
- User should paste command output back, redacting IPs/tokens/passwords and any private values. Continue evidence-first. Do not deploy until merge-commit CI, exact production container/volume identity, and validated backup are confirmed; production changes need explicit authorization.
- Continuation prompt: “Review the read-only SSH output for Job Beeper. Identify production vs dev by Compose project, container names, ports, image and mounts. Do not deploy or restart. Check GitHub Actions status for merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; available commit status endpoint returned no entries, so CI is still unverified. Decide the next read-only check and update both handover docs.”


## Oracle VM read-only inspection results — 2026-10-12 17:58 UTC
- User ran the requested inspection commands on host `job-radar` as user `ubuntu`, timestamp `2026-10-12T17:58:43+00:00`, working directory `/home/ubuntu`.
- Production checkout `/home/ubuntu/job-beeper`: branch `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, working tree reported clean, local branch reported `behind 19` relative to `origin/v2-live-radar`.
- Development checkout `/home/ubuntu/job-beeper-dev`: branch `v2-live-radar`, HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`, working tree reported clean, local branch reported `behind 69` relative to `origin/v2-live-radar`.
- Docker commands failed with `permission denied while trying to connect to the Docker API at unix:///var/run/docker.sock`. This establishes a permissions barrier for the current account; it does **not** establish that Docker is stopped or that containers are absent. Container, Compose project, health and mount identity remain unknown.
- Root filesystem is 45 GB total, 7.4 GB used, 38 GB available (17% used). Docker disk usage, volumes and recent events could not be read because of the same Docker socket permission failure.
- No pull/fetch/reset, container change, deployment, restart, backup, scan or database action was performed. Do not sync either checkout yet: first inspect the remote-vs-local commit ranges and identify which remote commits account for the 19/69-behind reports. Never assume the production and dev checkout roles solely from directory names.
- Next safe action: retry Docker inspection using `sudo docker ps --no-trunc --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'`, `sudo docker compose ls`, and read-only `sudo docker inspect` on running container IDs to inspect only name, image, state, health, restart count, Compose labels and mount source/destination. If sudo is unavailable, report the exact error and stop rather than changing permissions/groups. Do not print container environment variables or secrets.
- In parallel, use read-only Git commands in each checkout: `git remote -v`, `git status --porcelain=v1`, `git log --oneline --decorate HEAD..origin/v2-live-radar`, `git log --oneline --decorate origin/v2-live-radar..HEAD`, and `git diff --stat HEAD...origin/v2-live-radar`. These inspect commit divergence without changing refs or files; do not run `git pull`, reset, checkout, or deployment commands.
- Merge-commit CI for PR #36 merge SHA `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` remains unverified; PR-head run #592 passed but must not be treated as proof of merge-commit CI. No production deployment has been performed or verified. Keep production DB/volume/env unchanged, dev LinkedIn disabled, notifications off, Gemini shadow off; PR #35 stays separate.
- Continuation prompt: “Read the latest dated sections of both handover docs. On the Oracle VM, use sudo only for read-only Docker inspection and collect local-vs-remote Git commit ranges in both checkouts; do not fetch/pull/reset/deploy/restart or expose secrets. Confirm merge-commit CI for `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` separately. Update and re-fetch both handover docs after this prompt.”


## Merge-commit CI confirmed; VM admin access is the current blocker — 2026-10-12
- User supplied the full GitHub Actions log for workflow run checking out exact merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. Evidence in the log: checkout line reports that SHA; dependencies installed successfully; `python -m py_compile v2/radar.py v2/test_radar.py` passed; the exact configured full suite `python -m unittest discover -s v2 -p 'test_*.py' -v` ran 78 tests and ended `OK`. This now verifies CI on the merge commit; replace the earlier “merge-commit CI unverified” status with “verified green, 78/78”.
- Latest SSH output from host `job-radar`: production checkout `/home/ubuntu/job-beeper` is on `v2-live-radar` at `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, reported clean and 19 commits behind cached `origin/v2-live-radar`; dev checkout `/home/ubuntu/job-beeper-dev` is on `v2-live-radar` at `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`, reported clean and 69 behind cached `origin/v2-live-radar`. These are cached-ref comparisons, not proof of current remote divergence. Do not pull or reset either checkout yet.
- Docker API inspection failed with socket permission denied. `sudo -v` prompted for a password that the user does not have, so Docker container/Compose/volume identities remain unknown. Do not change Docker socket permissions, add groups, or alter sudoers as a workaround. Use the VM provider's authorized console/cloud-shell/recovery path or an already-authorized administrative account to restore admin access; otherwise continue GitHub-only work without touching runtime.
- Current status: PR #36 is merged to `main`; merge SHA `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; merge-commit CI green 78/78. No production deployment, container restart, backup, source enablement, or database change has been performed/verified. Root disk had 38 GB free. Production-vs-dev runtime and persistent volume identity are still unverified.
- Product roadmap after the parser fix: (1) regain authorized read-only VM/Docker visibility and identify production/dev Compose projects, ports, health and mounts; (2) inspect local-vs-remote commit ranges with a fresh fetch only when safe/authorized, then plan a reviewed, backed-up production branch/runtime transition as a separate authorized action; (3) in isolated dev, run the already-implemented Greenhouse adapter as a one-board canary with notifications off, verify two polls, stable IDs/deduplication, first_published timestamp behavior, request/error isolation, and useful yield; (4) validate Instahyre schema/freshness/yield before enabling; (5) add Ashby, Lever and SmartRecruiters one at a time; (6) improve per-source observability and monitor low-pressure LinkedIn for 24–72 hours. Do not enable multiple new sources at once. Keep LinkedIn low-volume with stop-on-429/backoff; no proxy/IP rotation or CAPTCHA bypass. Gemini remains shadow-only/off until dev validation; PR #35 remains separate.
- Immediate next action for the user: resolve VM administrative access through the cloud provider's supported console/recovery or authorized administrator. Do not repeat sudo Docker commands until access is fixed. Meanwhile the next development task should be a code-review/acceptance checklist for the existing Greenhouse one-board dev canary—not enabling it or changing production. Do not expose environment variables or tokens.
- Continuation prompt: “Read the newest dated sections of both handover docs. Merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` has confirmed green merge-commit CI (78/78). VM Docker inspection is blocked because ubuntu has no sudo password; do not weaken permissions or guess. Help restore authorized admin access through the cloud provider, then inspect runtime/mount identity read-only. Separately prepare the existing Greenhouse adapter's one-board dev canary acceptance checklist; do not enable it until runtime is verified and do not deploy or change production without explicit authorization.”


## No-sudo read-only diagnostics — 2026-10-12
- User asked to run the VM inspection commands without sudo. The assistant cannot execute commands inside the user's SSH session; provided copyable commands for the user to run.
- Safe no-sudo checks: `hostname`, `whoami`, `id`, `groups`, `ls -l /var/run/docker.sock`, `docker ps --no-trunc --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'`, and `docker compose ls`. Docker may still return permission denied; that is expected given prior evidence and does not show containers are stopped. Do not chmod the socket, add groups, alter sudoers, or otherwise bypass the permission barrier.
- Safe Git-only checks in both `/home/ubuntu/job-beeper` and `/home/ubuntu/job-beeper-dev`: `git status --short --branch`, `git log -1 --oneline --decorate`, `git remote -v`, `git log --oneline HEAD..origin/v2-live-radar`, `git log --oneline origin/v2-live-radar..HEAD`, and `git diff --stat HEAD...origin/v2-live-radar`. These compare against cached refs; they do not refresh remote refs. Do not fetch/pull/reset/checkout/deploy yet.
- No VM command was executed by the assistant, and no runtime or repository state was changed in this turn. Production deployment and runtime/mount identity remain unverified. PR #36 merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` has confirmed green merge-commit CI (78/78).
- Next action: user runs the no-sudo diagnostics and shares output, redacting any private remote URL if desired. If Docker access remains denied, use the cloud provider's supported console/recovery path or an already-authorized administrator. Continue GitHub-only review meanwhile; do not enable the Greenhouse canary or change production.
- Continuation prompt: “Read the newest dated sections of both handover docs. Review the no-sudo VM diagnostics. Do not bypass Docker permissions or mutate the VM. If Docker is still inaccessible, help restore authorized admin access through OCI's supported recovery path; otherwise continue read-only runtime identification. Keep production unchanged and prepare a Greenhouse one-board dev acceptance checklist without enabling it.”


## No-sudo diagnostics received: Docker group barrier and clean Git checkouts — 2026-10-12
- User supplied no-sudo diagnostics from host `job-radar`, user `ubuntu`, UID/GID `1001`. `id` shows membership in `sudo` and `lxd`, but **not** `docker`. Socket is `root:docker`, mode `srw-rw----` (0660). Both `docker ps` and `docker compose ls` fail with permission denied. This is consistent with the account lacking access to the Docker socket; it does not reveal whether containers are running. Do not attempt LXD-based privilege escalation, change socket mode, add groups, or alter sudoers. Use an authorized VM admin/cloud-console recovery path.
- Git checks in `/home/ubuntu/job-beeper`: clean `v2-live-radar` at `61d8271`, 19 commits behind the **cached** `origin/v2-live-radar`; no local-only commits shown. Diff summary versus cached ref: README, both handover docs, `v2/config.dev.json`, and `v2/docker-compose.dev.yml` (492 insertions, 85 deletions).
- Git checks in `/home/ubuntu/job-beeper-dev`: clean `v2-live-radar` at `54fc75c`, 69 commits behind the **cached** `origin/v2-live-radar`; no local-only commits shown. The output entered a pager (`(END)`); use `GIT_PAGER=cat` or `git --no-pager` on future output to avoid that. These counts compare cached refs only and do not establish current remote state.
- No Git fetch/pull/reset/checkout, Docker action, deployment, restart, backup, scan, or database change was performed. The assistant did not execute commands on the VM. Production runtime/container/volume identity remains unknown.
- Next safe action without sudo: query live remote branch SHAs without updating local refs using `git ls-remote origin refs/heads/main refs/heads/v2-live-radar`; then compare those SHAs with local `git rev-parse` values and inspect branch ancestry only after confirming the intended refs. Do not fetch or synchronize either checkout yet. For Docker visibility, obtain authorized admin access via OCI-supported console/recovery or an existing administrator; no permission workaround.
- CI/release status unchanged: PR #36 merged to main at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, merge-commit CI verified green (78/78). No production deployment has been performed or verified. Keep production unchanged, dev LinkedIn disabled, notifications off, Gemini shadow off, and PR #35 separate.
- Continuation prompt: “Read the newest dated sections of both handover docs. No-sudo checks confirm ubuntu is not in the docker group and cannot access the root:docker 0660 socket. Both checkouts are clean but 19/69 commits behind cached origin/v2-live-radar, with no local-only commits shown. First use git ls-remote to check live branch SHAs without fetching, then compare safely; do not sync or deploy. Restore authorized Docker admin visibility through OCI-supported access, not permission workarounds. Production remains untouched.”


## Live remote SHA and ancestry verification — 2026-10-12
- User ran read-only `git ls-remote`: live `main` is `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; live `v2-live-radar` is `816946c27248e0002df6aaacab7dd1caff56db79` (the docs-only commit recording the previous diagnostics).
- Local production checkout: HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; cached `origin/main` `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`; cached `origin/v2-live-radar` `232aeef1b7e4b294d38314297b730b6548b87622`.
- Local development checkout: HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`; cached `origin/main` `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`; cached `origin/v2-live-radar` `58aa277eb5d84bab4989618730927ba02a14e8bb`. Therefore both local remote-tracking namespaces are stale; do not use their ahead/behind counts as current truth.
- GitHub compare API confirms live `main...v2-live-radar` is **diverged**: v2 branch is 160 commits ahead and 8 behind main; merge base is `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`. This is not a safe basis for merging or deploying without reviewing the eight main-only commits and full branch diff.
- The production checkout HEAD is an ancestor of live `v2-live-radar` (172 commits ahead from that base); the development checkout HEAD is also an ancestor (89 commits ahead). These are GitHub-side comparisons against the supplied local commit SHAs and do not establish which checkout, Compose project, image, bind mount, database, or volume is actually running.
- No fetch, pull, reset, checkout, merge, deploy, Docker action, restart, backup, or database change was performed. No VM commands were executed by the assistant. Production runtime/container/volume identity remains unverified, and Docker socket access remains blocked for `ubuntu`.
- Next step: keep both checkouts untouched. Obtain authorized Docker visibility through OCI-supported console/recovery or an existing administrator. After runtime identity and a verified backup are established, separately plan Git synchronization; first review the 8 commits on `main` not in v2 and resolve the intended release/merge strategy. Do not merge/deploy v2 into production merely because its branch has a higher commit count.
- Keep PR #36 merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` as the known green CI baseline (78/78). No production deployment has been performed or verified. Greenhouse canary remains a later isolated dev task with notifications off; dev LinkedIn and Gemini shadow stay disabled.
- Continuation prompt: “Read the latest dated sections of both handover docs. Live refs: main=`58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, v2-live-radar=`816946c27248e0002df6aaacab7dd1caff56db79`. GitHub says the branches diverged: v2 is 160 ahead / 8 behind main, merge base `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`. Local prod/dev HEADs are ancestors of live v2, but local origin refs are stale. Do not fetch/sync/merge/deploy. First restore authorized Docker visibility and identify actual runtime/mounts with a verified backup plan; review the 8 main-only commits before choosing any release strategy.” 


## Execution preference and next action clarified — 2026-10-12
- User explicitly asked that the assistant either perform work directly through GitHub or provide exact executable commands for VM-only actions. Do not respond with a vague task list alone; distinguish what can be completed through GitHub from what requires the user's authorized SSH/OCI access.
- Current confirmed Git state remains: live `main` = `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; live `v2-live-radar` = `816946c27248e0002df6aaacab7dd1caff56db79`; GitHub comparison says v2 is 160 commits ahead and 8 behind main. Do not merge, pull, reset, or deploy while the eight main-only commits and actual runtime/mounts remain unreviewed/unverified.
- Next: use GitHub-only read operations to inspect the branch difference and review the main-only changes where possible. For VM-only diagnostics, provide a minimal copy-paste command block with explicit expected output and redact-secret guidance. Docker access for `ubuntu` is denied by the current root:docker 0660 socket; do not suggest permission bypasses. Authorized OCI console/recovery or an existing administrator is required.
- No VM command was executed and no runtime/production state changed in this turn.


## Runtime containers confirmed; main-only parser fix reviewed — 2026-10-12
- User supplied successful authorized sudo docker read-only output from host job-radar: job-radar-dev is Up 8 hours, image job-radar-dev-radar, bound only to 127.0.0.1:8001->8000/tcp and Compose config /home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml; v2-radar-1 is Up 15 hours, image ID 97368934ed14, exposed on 0.0.0.0:8000 and Compose project v2 using /home/ubuntu/job-beeper/v2/docker-compose.yml. This confirms both containers are running and port separation is in place. It does not yet identify source revision baked into each image, mounts/volume identities, or prove the production container corresponds to its checkout.
- Both local checkouts report clean v2-live-radar working trees and stale cached tracking refs: production checkout is 19 behind cached origin/v2-live-radar; dev checkout is 69 behind cached origin/v2-live-radar. Do not infer current live-remote divergence from these counts.
- GitHub compare of v2-live-radar...main confirms the branches remain diverged. The current net main-only code difference is limited to v2/radar.py and v2/test_radar.py (70 changes in radar, 90 in tests). Reviewed commits 9b9cbf1 and 715b94d: main contains a LinkedIn structured Experience-label parser that prioritizes explicit fields like “Experience: 4.00-6.00 Years” over incidental JD mentions, plus regression tests. Commit 572f565 also makes the pagination test hermetic by mocking enrichment, avoiding real LinkedIn requests/429 cooldown contamination. Merge commit 58fdff1 is CI-green (78/78) per earlier verified run. This looks like a relevant parser correctness fix, but it must still be applied/reviewed against the live V2 branch in a controlled way; do not merge or deploy without checking branch ancestry and runtime/volume backup.
- No pull/fetch/reset/checkout/merge/deploy/restart, DB change, or backup was performed in this turn. Container identity is partially confirmed; exact image source SHA and persistent mount identities remain unknown.
- Immediate next action: use sudo docker inspect read-only to collect each container's image ID, Compose labels, mounts (names/source/destination only), and safe revision labels if present; do not print environment variables. Then inspect Compose rendered configuration carefully with secret values redacted, verify named volume mappings, and plan a backup before any source change. Keep production running untouched.
- Copyable command for the user (read-only; inspect output before sharing and redact any private host paths if needed):
```bash
for c in job-radar-dev v2-radar-1; do
  echo "===== $c ====="
  sudo docker inspect --format 'container={{.Name}} image={{.Config.Image}} image_id={{.Image}} created={{.Created}}' "$c"
  sudo docker inspect --format '{{range .Config.Labels}}{{println .}}{{end}}' "$c" | grep -E 'com.docker.compose.(project|service|project.config_files|image|version)' || true
  sudo docker inspect --format '{{range .Mounts}}{{println .Type .Name .Source "->" .Destination}}{{end}}' "$c"
done
```
- Continuation prompt: “Read the newest dated sections of both handover docs. VM confirms job-radar-dev on loopback port 8001 and v2-radar-1 on public port 8000 are running in separate Compose projects. Both checkouts are clean but cached tracking refs are stale. GitHub review shows main-only parser fix in v2/radar.py and regression tests, including explicit LinkedIn Experience-label extraction and a hermetic pagination test; merge commit CI passed 78/78. Next inspect container image IDs, Compose labels and mounts read-only, without printing env vars. Do not change production, sync branches, or deploy until image source SHA and DB/volume identity are verified and backup plan is ready. Update both handover docs after every prompt.”


## Runtime image and volume identities captured — 2026-10-12
- User ran read-only `docker inspect` for both services. Development: container `/job-radar-dev`, image `job-radar-dev-radar`, container image ID `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`, created `2026-10-12T10:03:31Z`, Compose project `job-radar-dev`, config `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`, working dir `/home/ubuntu/job-beeper-dev/v2`; named volume `job-radar-dev_radar-dev-data` mounted at `/data`; bind-mounted `/home/ubuntu/job-beeper-dev/v2/config.dev.json` at `/app/v2/config.json`.
- Production-facing V2: container `/v2-radar-1`, image `v2-radar`, container image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, created `2026-10-12T03:44:43Z`, Compose project `v2`, config `/home/ubuntu/job-beeper/v2/docker-compose.yml`, working dir `/home/ubuntu/job-beeper/v2`, Compose environment file path `/home/ubuntu/job-beeper/.env` (path only; no environment values read); named volume `v2_radar-data` mounted at `/data`. The volume names differ, confirming distinct named volumes; do not assume either volume contains a valid restorable backup without checking.
- Runtime container image IDs and Compose/mount labels are now known, but the labels shown do not expose the Git source SHA used to build either image. Need inspect image-level labels/metadata and the non-secret Compose build/image declarations next. Do not dump `.Config.Env`, `.env`, config contents, or rendered Compose output that might contain secrets.
- No runtime state changed and no production deployment/restart/backup was performed. Do not pull/reset/merge/rebuild/deploy yet. Next use read-only image inspection to look for OCI revision/source labels and inspect Compose files for only `build:`/`image:` lines and Dockerfile revision-label conventions; if no revision label exists, report that source SHA is not embedded and plan to compare image creation metadata / running app version before any change.
- Suggested read-only command: `for i in job-radar-dev-radar v2-radar; do echo "===== $i ====="; sudo docker image inspect --format 'id={{.Id}} created={{.Created}} digests={{json .RepoDigests}} labels={{json .Config.Labels}}' "$i"; done` then `grep -nE '^[[:space:]]*(build:|image:|dockerfile:)|org.opencontainers.image.revision|org.opencontainers.image.source|VCS_REF|GIT_SHA' /home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml /home/ubuntu/job-beeper-dev/v2/Dockerfile /home/ubuntu/job-beeper/v2/docker-compose.yml /home/ubuntu/job-beeper/v2/Dockerfile 2>/dev/null` (missing Dockerfiles may simply be in another path; do not infer from grep absence).
- Continuation prompt: “Read the latest dated sections of both handover docs. Runtime separation is confirmed: dev image ID sha256:13b233... uses named volume job-radar-dev_radar-dev-data and dev config bind mount; V2 image ID sha256:973689... uses named volume v2_radar-data and its .env file path. Different volume names establish separation, not backup validity. Next inspect image-level OCI revision/source labels and only safe build/image/Dockerfile declarations, never environment values or secrets. Source SHA is still unknown. Keep both containers untouched and update both docs after every prompt.”


## Image provenance check — 2026-10-12

Latest VM output confirms both runtime images have only Docker Compose labels and no OCI source/revision, `VCS_REF`, or `GIT_SHA` labels. The image IDs differ from the previously captured dev image/container identity: dev image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`, created `2026-10-12T10:03:24Z`; production-facing V2 image `sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`, created `2026-10-12T03:44:38Z`. Both Compose files declare a build and `dockerfile: v2/Dockerfile`, but the grep output did not establish the build context or locate the Dockerfile. Therefore the source commit baked into either running image remains unknown. No runtime, image, or persistent data was changed.

### Next safe step

Inspect only the Compose build context, Dockerfile path/content, checkout HEADs and worktree status, and image history metadata. Do not pull, rebuild, recreate, restart, merge, deploy, reset, or modify database volumes until source provenance and backup/rollback details are understood. Never print `.env` contents or environment-variable values.


## Runtime image identity follow-up — 2026-10-12

VM output: `job-radar-dev` runs image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`; `v2-radar-1` runs `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`. Docker cannot inspect the latter as a local image (`No such image`), although the existing container remains running with that image ID. The `v2-radar` tag points to a different image (`sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`). Both Compose files use build context `..` and `v2/Dockerfile`. Production checkout HEAD: `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; dev checkout HEAD: `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`. Behind counts rely on cached refs and are not authoritative. No runtime or checkout changes were made. Next: inspect Dockerfile/history and container mounts/config without exposing secrets; do not restart, recreate, prune, pull, rebuild, or deploy until image provenance, database backup, and rollback are understood.


## Dockerfile and image history review — 2026-10-13

Read-only VM output shows the production and development Dockerfiles are currently identical: Python 3.12 slim base, install `v2/requirements.txt`, copy `v2` and `dashboard`, set `/data/jobs.db`, run Uvicorn on port 8000. Their Dockerfile Git histories match through the displayed last four commits. Both Compose build contexts are `..` and Dockerfile is `v2/Dockerfile`. Current dev image `sha256:13b233...` and current `v2-radar:latest` image `sha256:a0c38e...` were built from layers with differing copied `v2` sizes (324kB vs 369kB), so the copied application contents differ. Crucially, the running production container `v2-radar-1` still points to `sha256:973689...`, whose image metadata is unavailable locally; it must not be conflated with the current `v2-radar:latest` tag. Persistent volumes remain distinct: dev `job-radar-dev_radar-dev-data` mounted at `/data`, production `v2_radar-data` mounted at `/data`. No services or data were changed.

### Next safe step

Compare hashes of selected application files in each checkout and inside each running container, and collect container health/restart status plus a non-mutating listing of database file metadata (not contents). Do not restart/recreate/prune/pull/build/deploy or run migrations. Before any rollout, verify a tested backup and rollback method for `v2_radar-data`.


## Runtime source-hash and database metadata verification — 2026-10-13

Read-only VM checks compared SHA-256 hashes of application files in both checkouts and running containers, inspected container state, and read only database file metadata from the named Docker volumes. Findings:

- Production checkout `/home/ubuntu/job-beeper/v2/radar.py` and running container `v2-radar-1:/app/v2/radar.py` match exactly: `bba3558aa293e6729ba431d72e61fcf298f6ad845ad86fda335c4847b3863bfe`.
- Development checkout `/home/ubuntu/job-beeper-dev/v2/radar.py` and running container `job-radar-dev:/app/v2/radar.py` match exactly: `ef3ce0e99f1527afc306227043478e53780bab1da235fcd6173f692f97e0a8f6`.
- Both checkouts and containers have matching `v2/requirements.txt` hash `9904eb1672148185b976a1e4228123eeacb012c864948414243b3259e6fd431b`.
- Production `/app/v2/config.json` matches the production checkout config hash `2a4faf5710cf36829646be3c91dda8da35e914e60937d07488d6d4367f3000b5`. Development `/app/v2/config.json` matches the development config bind-mounted from `v2/config.dev.json`, hash `c8961f5b288ec6b808163f1c4fc91b52237b60b1d1a4c1a4b5ccbe71c637d201`.
- Both containers were running with restart count 0; health checks are not configured. This establishes running state, not application-level health.
- Separate database volumes remain in use. Read-only metadata showed dev `jobs.db` size 3,960,832 bytes (modified 2026-10-12 18:59:03 UTC) and production `jobs.db` size 17,670,144 bytes (modified 2026-10-12 19:00:39 UTC). No database contents were read or changed.
- The diagnostic command pulled `python:3.12-slim` because it was not locally available, then mounted each database volume read-only for metadata inspection. No app containers or database data were modified.
- The command output was slightly malformed at the shell loop boundary, but both volume metadata checks completed and returned the above results.

Interpretation and next safe step: the current source files inside each running container match their respective checkout files, and dev/prod app code differs as expected. This does not prove which Git commit or image build produced the production container, because image provenance labels are absent and its reported image ID was not found in local image metadata. Before any rollout, read-only inspect each checkout's current branch, HEAD, working-tree status, and the Git commit(s) containing the exact `radar.py` blob; separately capture container image IDs and available image metadata. Do not rebuild, retag, restart, pull application code, or deploy, and do not query or mutate database contents until provenance and rollback/backup are established.


## Git blob and image-reference provenance audit — 2026-10-13

Read-only VM output adds these provenance findings:

- Production checkout `/home/ubuntu/job-beeper` is on `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` (`Document free-first LinkedIn strategy and release cleanup`, 2026-10-12 00:08:42 +05:30); its working tree is clean and `v2/radar.py` has no unstaged/staged diff. Its current file blob is `db405442e706af778a2a1e927864629a6e699d3e`; local history reports blob introduction at commit `6c93473844cd469493a0c61acf1477ba20252d69` (`Reduce LinkedIn request pressure with free-first pacing`, 2026-10-11).
- Development checkout `/home/ubuntu/job-beeper-dev` is on `v2-live-radar`, HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2` (`docs: record source status CI success`, 2026-10-12 15:31:19 +05:30); its working tree is clean and `v2/radar.py` has no unstaged/staged diff. Its current file blob is `e1b30717bfeac33fa9e0973ab5ad7d426ccf7085`; local history reports blob introduction at commit `150d2878ac7b66d11ff0f5b81e991210c7f413a8` (`Expose persisted last source error in status API`, 2026-10-12).
- Both local checkouts show their local `origin/v2-live-radar` tracking refs ahead of the checked-out HEAD by stale/unfetched counts (production behind 19, dev behind 69). No fetch was performed in this audit; these counts are not proof of the current remote delta.
- Running production container `/v2-radar-1` references image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, created 2026-10-12T03:44:43Z. That image ID is absent from `docker image ls`; the current `v2-radar:latest` tag points to a different image, `sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`, created 2026-10-12T03:44:38Z. The tag's labels contain Compose project/service/version only, with no source SHA or build revision. Do not assume the current tag is the image the running production container started from.
- Development container uses the locally available `job-radar-dev-radar:latest` image ID `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`, created 2026-10-12T10:03:31Z. Its runtime source hash matches the dev checkout.

Interpretation: runtime `radar.py` files match their corresponding checkout files, but neither the production source commit nor image provenance is fully attested by image labels. The reported `git log --find-object` commits identify local history entries associated with those blobs, not by themselves a full reproducible build attestation. The production running image's missing local image metadata and different current tag are important uncertainties. Next safe step is a read-only remote-ref comparison (e.g. `git ls-remote origin refs/heads/v2-live-radar` from each checkout) plus local `git show`/commit metadata for the identified blob-introduction commits and the commit that the container code is expected to correspond to. Do not fetch, pull, build, retag, restart, deploy, prune, or alter databases until the remote state, backup, and rollback image/source are understood.


## Remote-ref and container writable-layer audit — 2026-10-13

Read-only VM output reports `git ls-remote origin` returned the same refs from both checkouts: `main` at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` and `v2-live-radar` at `4f21c219244bfe5c490c1e3536de0a7c9bf6a921`. The latter is the latest docs-only commit created during this workflow, so local `behind 19` / `behind 69` tracking indicators are stale; do not treat them as accurate current remote deltas. No fetch was performed.

Local `git show` confirmed production HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` and its blob-introduction commit `6c93473844cd469493a0c61acf1477ba20252d69` both resolve `v2/radar.py` to blob `db405442e706af778a2a1e927864629a6e699d3e`. Dev HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2` and its blob-introduction commit `150d2878ac7b66d11ff0f5b81e991210c7f413a8` both resolve `v2/radar.py` to blob `e1b30717bfeac33fa9e0973ab5ad7d426ccf7085`.

`docker diff v2-radar-1` showed only runtime-generated Python `__pycache__`/`.pyc` changes under Python libraries and `/app/v2`; no source-file modifications were listed. This is consistent with normal Python bytecode caching, not evidence of manual source edits. The final container inspect output still identifies production image `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f` and dev image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`.

Next: compare each local HEAD to remote `v2-live-radar` via GitHub's compare API (read-only) and inspect the changed-file summary. Since the remote head includes the recent docs-only commits, separate those from code changes. Do not fetch, pull, rebuild, retag, restart, deploy, prune, or touch DB contents until source provenance and backup/rollback safety are understood.


## GitHub remote compare against both VM checkouts — 2026-10-13

Used GitHub's read-only compare endpoint against remote branch head `a158b9bf73a26a3309ac6ef801581c19981be790` (current `v2-live-radar` after the latest handover-note commits). No VM fetch or checkout changes were made.

- Production local HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` is an ancestor of the remote branch head; compare reports remote head 193 commits ahead and 0 behind, with merge base equal to the production HEAD. Diff summary includes `v2/radar.py` (143 changed lines: 139 additions, 4 deletions), `v2/test_radar.py` (157 additions), new `v2/gemini_extractor.py` (411 additions), new `v2/test_gemini_extractor.py` (110 additions), dev config/compose files, plus README/dashboard/docs. This establishes that production checkout is older than the current remote code and must not be assumed to be current.
- Development local HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2` is an ancestor of the same remote head; compare reports remote head 110 commits ahead and 0 behind, with merge base equal to the development HEAD. The compare endpoint's file summary lists only `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`; it lists no application source, tests, config, or dashboard changes between dev HEAD and remote head. This suggests the dev checkout's tracked application code matches the remote branch's code at this compare point, with the remaining differences in the two handover documents. Verify this before treating it as a candidate release.
- These counts supersede stale local tracking indicators (`behind 19` and `behind 69`), which were based on outdated remote-tracking refs. They do not indicate the branch is behind remote; both local HEADs are ancestors of remote.
- `docker diff v2-radar-1` showed only Python-generated `.pyc`/`__pycache__` paths under runtime Python packages and `/app/v2`; no source modifications were listed. This is expected runtime cache behavior and does not by itself suggest source tampering.

Next safe work: inspect exact source/test diffs between the production code baseline and the candidate remote branch through read-only GitHub commit/file inspection, then review CI/test evidence and current dev runtime behavior. Do not deploy or restart production until a database backup and rollback path are explicitly verified and the production image provenance gap is resolved. No production or database changes were made during this comparison.


## Exact production-versus-remote source review — 2026-10-13

Read-only GitHub file inspection compared `v2/radar.py`, `v2/test_radar.py`, `v2/gemini_extractor.py`, `v2/test_gemini_extractor.py`, and `v2/requirements.txt` at production baseline commit `61d8271480eaf48b0a6442b62b1b0bb9a032df34` versus remote `v2-live-radar`.

- Production `v2/radar.py` blob is `db405442e706af778a2a1e927864629a6e699d3e` (114,244 chars, 2,991 lines); remote blob is `e1b30717bfeac33fa9e0973ab5ad7d426ccf7085` (120,033 chars, 3,126 lines). Remote `radar.py` blob matches the previously measured dev checkout/container SHA-1 Git blob identity, confirming dev code matches the current remote file at this path.
- The 143 changed lines in `radar.py` comprise 139 additions and 4 deletions. Reviewed hunks show: a new LinkedIn structured `Experience:` parser; prioritization of labeled experience metadata over incidental JD year counts; additional LinkedIn JD selection/enrichment handling; Gemini LLM shadow-only extraction integration with fail-open exception handling; `/api/llm-shadow-status`; and persistence/exposure of latest source errors as `last_error` in source status.
- Production baseline lacks `v2/gemini_extractor.py` and `v2/test_gemini_extractor.py`; both exist on remote (16,708 and 5,491 characters respectively). `v2/test_radar.py` also differs (production blob `3b6d0eef70683c8ccb95d4730da36c671b679365`, remote blob `8a739fa3f5f1d8c09a5e80501e25a2d2f625c892`). `v2/requirements.txt` is byte-identical at both refs (blob `77919a4fcd76ebc09137e54e46b9be5aa0f37922`).
- The code review confirms that current remote/dev code is functionally newer than production code. It does not, by itself, prove end-to-end test success, production compatibility, Gemini credentials/limits, or a safe release. No application or database changes were made.

Next safe step: inspect CI/check status for the code-bearing commit(s), then run or review the project's test suite against the dev checkout with explicit confirmation tests use isolated temporary databases/config. Do not run tests against production DB, deploy, restart, or change database state until backup and rollback are verified.


## Development test-isolation audit — 2026-10-13

Read-only output from `/home/ubuntu/job-beeper-dev` shows a clean worktree (local `origin/v2-live-radar` tracking status still reports `[behind 69]`, known stale tracking metadata; current remote head was separately checked via `git ls-remote`). Grep inspection of `v2/test_radar.py` and `v2/test_gemini_extractor.py` found extensive use of `TemporaryDirectory`, reassignment of `radar.DB_PATH` to a temporary `jobs.db`, and temporary SQLite paths for Gemini shadow-cache tests. Gemini tests mock `gemini.requests.post` and use test-only API-key/model values in the matched test snippets. Test files use standard-library `unittest`; requirements listing showed `fastapi>=0.115,<1` as the only displayed dependency line. Development volume `job-radar-dev_radar-dev-data` currently has `/inspect/jobs.db` metadata size 4,104,192 bytes, modified 2026-10-12 19:09:05 UTC; metadata only, no DB contents read.

Safety qualification: grep output is a partial static audit, not proof that every test is isolated or cannot invoke network/source collectors, startup hooks, or default DB paths. Before running the full suite, inspect test module setup/import side effects and the relevant functions in `v2/radar.py`, especially module-level DB initialization and collector/enrichment entry points. If any risk remains, run the suite in a separate process with a temporary `JOB_RADAR_DB` path and network calls patched/disabled; do not run against production or the persistent dev volume. No tests were run and no application/database state was changed in this step.


## Isolated test execution plan — 2026-10-13

Follow-up static inspection of current remote `v2/radar.py` confirms `DB_PATH` is set from `JOB_RADAR_DB` (defaulting to `ROOT / jobs.db`) and FastAPI startup calls `init_db()`. Therefore tests should not be run directly in the long-running development container or against its persistent `/data/jobs.db` volume. The test modules use standard-library `unittest`; the Gemini test's HTTP POST is patched in its network-related test. Many radar DB tests explicitly replace `radar.DB_PATH` with a `TemporaryDirectory` database, but the suite as a whole was not executed during this audit and no claim is made that every test is isolated.

Recommended next validation is a disposable one-off container from the dev image, with `--network none`, no persistent data-volume mounts, `JOB_RADAR_DB=/tmp/jobs.db`, and the dev config bind-mounted read-only at `/app/v2/config.json`. Run `python -m unittest v2.test_radar v2.test_gemini_extractor` from `/app` in that container. This isolates any startup-created DB to the disposable container and prevents external network calls; it does not change the long-running dev or production containers or their database volumes. Do not use production container/image or production database for tests.


## Isolated test suite passed — 2026-10-13

- The user reported the isolated test run completed successfully: `Ran 88 tests in 53.320s`, `OK`.
- Record this as a successful 88-test run; the short result alone does not identify individual test names or independently prove the exact invocation/environment.
- Next: preserve the full test command/output if available, then continue with read-only verification of current remote branch/CI state and production-versus-development source/image provenance.
- No production deployment, container restart, database mutation, or persistent-volume test was authorized or performed as part of this result. Keep production changes blocked until image/source provenance and a backup/rollback plan are verified.


## 88 isolated tests pass; inspect intermittent PR workflow failures — 2026-10-13

- User supplied the complete isolated command output: `python -m unittest v2.test_radar v2.test_gemini_extractor` ran with Docker `--network none`, a disposable `/tmp/jobs.db`, and the development config mounted read-only. Result: `Ran 88 tests in 53.320s`, `OK`.
- The accompanying Actions screenshot shows docs-only workflow runs #689 and #691 passing, while the “Draft: Gemini JD extraction shadow mode” PR #35 synchronize workflow has both failures (#688 and #692) and a pass (#690). This screenshot alone does not reveal the failing step or root cause.
- Next: inspect the failed run/job logs for #692 (and compare #688 with passing #690) before changing code or rerunning anything. Treat the local 88-test success and PR CI status as separate evidence.
- No production deployment, restart, or persistent database operation was performed or authorized. Keep production unchanged pending source/image provenance and backup/rollback verification.


## Diagnose CI failures from uploaded full test log — 2026-10-13

- User provided the full failed GitHub Actions test log. Workflow run #694 failed with 6 test failures out of 88; run #696 subsequently passed (per user's latest Actions screenshot), so the issue appears intermittent/order-sensitive rather than a deterministic failure on every run.
- Failure cluster: five LinkedIn scan tests see zero calls/results because an earlier test `test_linkedin_fast_lane_and_periodic_deep_scan` triggers HTTP 429 and leaves a 299-second global cooldown active; subsequent tests log “linkedin scan skipped; rate-limit cooldown has 299s remaining.” The six failures are: `test_linkedin_fast_lane_and_periodic_deep_scan`, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_linkedin_fast_scan_uses_broader_recency_window`, `test_linkedin_skips_deep_scan_after_fast_lane_rate_limit`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`.
- This points to shared LinkedIn rate-limit/cooldown state leaking across tests and/or test fixtures not resetting it, with a separate affected JD-enrichment assertion as a downstream consequence of the scan being skipped. Confirm exact setup/teardown and workflow command before changing implementation.
- The local user's isolated command `python -m unittest v2.test_radar v2.test_gemini_extractor` passed 88 tests in 53.320s. CI log shows `python -m unittest discover -s v2 -p 'test_*.py' -v` and 6 failures in 12.375s. These differ in test invocation/order/environment, so local pass does not invalidate CI failure.
- Latest screenshot shows run #696 passed and #694 failed for PR #35; compare logs and test invocation, then run targeted failing tests and the full discovery command in a disposable offline environment. No production changes, restarts, or database writes.


## Resume roadmap after green tests; clarify branch and release gates — 2026-10-13

- User reports the isolated module invocation passes all 88 tests in 53.323s. The latest provided Actions screenshot shows PR #35 workflow run #700 green; the docs commit workflow #699 is green too. The earlier full-discovery failure was intermittent/order-sensitive; the latest green CI is useful evidence but does not erase the need to avoid claiming every invocation/environment is permanently stable.
- Current branch state was checked through GitHub compare: `main` at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; `v2-live-radar` is reported as 195 ahead and 8 behind, status `diverged`, merge base `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`. Therefore do not say all V2 work is pushed/merged to main; PR #35 remains separate and the branch has not been reconciled. No merge/pull/deploy performed.
- Re-read `docs/JOBBEEPER_REFERENCE.md`: Greenhouse adapter already exists, is disabled, and next planned source step is a one-board development canary with notifications off; acceptance criteria include two polls, stable IDs/deduplication, first_published timestamp behavior, request/error isolation, and useful yield. Instahyre schema/freshness validation follows; Ashby, Lever, and SmartRecruiters are later one-at-a-time adapters.
- Recommended next work: resume planned roadmap, starting with a concise Greenhouse one-board canary acceptance checklist and read-only verification that current dev runtime/config and authorized Docker visibility support a safe isolated test. Do not enable the source until runtime/config are verified and the user explicitly authorizes the canary. Keep notifications off, Gemini shadow-only/disabled until its quality gate is satisfied, and production untouched.
- Production image/source provenance, named-volume identity, and verified backup/rollback remain unresolved gates. No production deployment, restart, source activation, or database modification occurred.


## Implement read-only Greenhouse two-poll canary — 2026-10-13

- Implemented directly on `v2-live-radar`:
  - Added `v2/greenhouse_canary.py`, a read-only CLI that fetches one explicitly selected public Greenhouse board twice through the existing collector and reports total/unique IDs, stable/new/missing IDs, and second-poll first-published timestamp coverage.
  - The default gap is 900 seconds; intervals under 60 seconds are rejected. It does not write the radar DB, run matching, change `source_enabled`, or send notifications.
  - Added `v2/test_greenhouse_canary.py` with tests for report metrics, two-poll sequencing, input validation, and no collector call for an invalid interval.
  - Added usage and safety/acceptance notes to `docs/JOBBEEPER_REFERENCE.md`. The existing dev config keeps Greenhouse disabled.
- GitHub commits on `v2-live-radar`: script `14c74222751a4bb466bf4d05f2ffe39a370954c6`; tests `30b85ad1c494a452f464909b045da66d9892d09e`; reference docs `fea5b112492e85f071e211370d4eba7728610821`.
- CI run #708 for the test commit was observed in progress at handover time; do not record it as passed until checked. No live Greenhouse poll has been run yet, so no canary yield/timestamp result is claimed.
- Next: confirm CI #708 result; then pull the branch in the development checkout and build only the development Compose image. Run the CLI against one selected configured board with notifications still disabled, retain the JSON output, and evaluate two-poll acceptance before any scheduler activation.
- Production was not changed. Do not build/deploy production or enable Greenhouse in production as part of this task.


## Greenhouse canary quality metrics and CI compilation — 2026-10-13

- User authorized direct GitHub development on `v2-live-radar` and requested VM pull/build commands plus handover updates.
- Updated `v2/greenhouse_canary.py` to report per-poll missing source IDs, duplicate source IDs, and published-timestamp coverage for both polls, in addition to stable/new/missing IDs. The utility remains GET-only and does not activate Greenhouse, write the radar DB, run matching, or send notifications.
- Expanded `v2/test_greenhouse_canary.py` assertions for duplicate IDs and timestamp coverage; updated `.github/workflows/v2-ci.yml` py_compile step to include the canary utility and its tests.
- Commits on `v2-live-radar`: canary `7966ae423a44ff04cbf2bc26a6f417a52365fc4b`; tests `030adf62fe0cdc913d977c7e52e182c94dc11c9f`; CI workflow `aff4fd7e5dc6bd6be536c491bf46d2bfd059f4b6`. Workflow status must be checked before VM build; these edits have not been deployed.
- Next: wait for/check V2 CI on the latest branch head. On the VM, first verify clean status and branch; fetch and fast-forward only (no force reset). Build only the isolated development image using `docker compose -f v2/docker-compose.dev.yml build`. Do not restart production or activate Greenhouse. For the actual canary, keep dev `source_enabled.greenhouse=false`, choose one already-configured public board, and run `python -m v2.greenhouse_canary --board-token <board-slug> --company "<company>" --interval-seconds 900` from the repo root; this requires outbound network and takes at least 15 minutes. Save the JSON report and review yield, IDs, timestamps and errors before any scheduler activation.
- Production source/image provenance, backup and rollback are still unverified; no deployment, service restart, source activation, or database mutation occurred.


## Greenhouse canary command blocked by host Python lookup — 2026-10-13

- User ran a build from the development checkout; terminal reported `[+] build 1/1 ✔ Image v2-radar Built`. The selected canary command then failed immediately with `Command 'python' not found`. Therefore **the canary did not execute and no Greenhouse HTTP polls or report were produced**.
- Attempted command: `python -m v2.greenhouse_canary --board-token coinbase --company "Coinbase" --interval-seconds 900` from `/home/ubuntu/job-beeper-dev`. The missing `python` executable is a host-shell issue, not a demonstrated canary-code failure. Do not assume `python3` has the application dependencies; prior host-Python tests failed import due to missing `bs4`.
- GitHub config inspection confirms `v2/config.dev.json` contains the public Greenhouse board token `coinbase` / company `Coinbase` and `source_enabled.greenhouse=false`. The canary helper at `v2/greenhouse_canary.py` is designed to make two GET-only polls, default gap 900 seconds, and emit JSON metrics without DB writes, matching, scheduler activation or notifications.
- Important image-tag caution: the build output names `v2-radar`, whereas the dedicated dev Compose file's expected image is project-derived (`job-radar-dev-radar`). Because the exact build command was not included, inspect `docker image inspect` for image tags/IDs and read-only `docker inspect` of `v2-radar-1` and `job-radar-dev` before using any image. Do not run/recreate/restart either service, retag/prune/pull images, or build with production Compose. A build by itself does not prove the running production container changed, but the local tag may have been moved; verify rather than assume.
- Next agent must: read this note plus both handovers and `docs/JOBBEEPER_REFERENCE.md`; check GitHub Actions for the latest `v2-live-radar` head and canary CI; inspect the exact VM command that produced the `v2-radar` build if available; check branch/clean-tree state; fast-forward only if safe; then build only with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml build`. Use an isolated one-off container from the verified dev image to run `python -m v2.greenhouse_canary --board-token coinbase --company "Coinbase" --interval-seconds 900`; outbound network is needed, so do not use `--network none`. Do not mount any persistent DB volume. Keep source disabled and notifications off. Retain the JSON output and review both polls, job yield, stable/duplicate/new/missing IDs, timestamp coverage and failure status. If image provenance/compose target is unclear, stop and ask for the read-only inspect output before running the canary.
- No evidence that the canary ran, no source activation, no service restart or deployment is reported. Production source/image provenance and backup/rollback gates remain unresolved.


## CI failure review and canary blocked — 2026-10-13

- Current `v2-live-radar` head at review: `5915f53c4292f1d6c444eab8a16c6aa55b5b74fd`. Re-read the detailed handover and `docs/JOBBEEPER_REFERENCE.md` before this update.
- Latest V2 CI runs #727 and #726 failed in full unittest discovery. py_compile and the displayed Greenhouse canary tests passed; failures were 5–6 LinkedIn scan/enrichment tests. Earlier run #718 passed on commit `aff4fd7e5dc6bd6be536c491bf46d2bfd059f4b6`. Current CI is not green; diagnose and get a passing run before any development image build or live canary.
- The host `python` invocation failed before execution; no Greenhouse HTTP polls or JSON report exist. Prior build label `v2-radar` is ambiguous, and running-container impact is unverified. No source activation, notification change, DB mutation, restart, or deployment is evidenced.
- No code/config change in this review. Keep Greenhouse disabled and notifications off. Next: fix/verify CI; then request read-only VM git/image/container identity checks before considering safe fast-forward, dedicated dev build, isolated tests, and only then the disposable network-enabled two-poll canary. Never expose environment values or touch production/persistent DB volumes.


## VM identity check and latest CI recheck — 2026-10-13

- VM reports clean checkout at `eeb59eb4cbe3cc9771572b5bd73c69e3245124bf`; remote branch is `b58c2acc603d412d8bcfda18365046655e139c38`. Remote is a descendant of local; fast-forward is possible but deferred because latest-head CI results conflict.
- Docker identity: `v2-radar:latest` image ID `sha256:6300862b5d8071221343dc5c95006d73a90a22db42983aecf3b6e0215cc9fee3`; running `v2-radar-1` uses different ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`. `job-radar-dev-radar:latest` and running `job-radar-dev` both use `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`. Keep image tags distinct; build only dedicated dev Compose after CI is resolved.
- CI at remote head `b58c2acc603d412d8bcfda18365046655e139c38` is inconsistent: run #730 failed 5 LinkedIn scan/enrichment tests among 92, while run #731 passed. Canary tests displayed as passing; full-suite reliability still needs investigation.
- Live canary has not run; no JSON report or two-poll results. Greenhouse remains disabled; notifications off; no production action or persistent DB changes were performed.
- Next: resolve/reproduce same-head CI disagreement, then safe fast-forward, dedicated dev image build, isolated full test suite, and only after passing tests the network-enabled disposable canary. Never mount a persistent DB volume or modify production.


## LinkedIn unit-test isolation fix — 2026-10-13

- Investigated CI run #735 on commit `5a71fc18060d5eb790b202e20ef5e339482ebf7b`: five failures were clustered around LinkedIn scans being skipped by a shared ~300-second 429 cooldown; JD enrichment also did not execute, consistent with the same cooldown short-circuit.
- Committed test-only isolation in `v2/test_radar.py` as `a3ae210a099576717913aa6aec7a7c1dae8bd6c7`: `MatcherTests.setUp/tearDown` now resets and restores the module-level LinkedIn request/cooldown/streak/generation values so one test's synthetic rate limit cannot contaminate another test.
- Latest-head CI run #736 (`38355269626`) was still in progress at the time of this note; this change is NOT yet confirmed by a completed green full suite. Review its final result and, if necessary, diagnose remaining failures before any dev VM build or canary.
- No canary was run, no production container/database was touched, Greenhouse remains disabled, and notifications remain off.


## Hermetic LinkedIn collector test follow-up — 2026-10-13

- CI run #736 after the rate-state isolation change reduced the suite from five failures to one. The remaining failure was `test_linkedin_fast_lane_and_periodic_deep_scan`: its parsed listing triggered JD enrichment that was not mocked, and the CI log showed a real HTTP 429 during the second scan, which activated the process-wide cooldown and caused the test to fail.
- Follow-up commit `6aa2e020a0898d660abb57fc5488203738dc3444` mocks `radar.enrich_linkedin_job` in that test so it remains offline/hermetic; the test's purpose is scan cadence, not JD extraction or live LinkedIn behavior.
- Full-suite confirmation for this latest code is still pending. Do not fast-forward/build/run the canary until latest-head CI is green and the VM safety checks are revalidated. Greenhouse remains disabled, notifications off, and production/persistent DB untouched.


## Latest-head CI verified; VM validation still pending — 2026-10-13

- Verified GitHub Actions run #744 (`38355415401`) for branch head `b51d3f8b2aa0bee6e66ac932fd32b599df1893e8`: completed successfully. Job `syntax` passed dependency install, `py_compile`, and full `python -m unittest discover -s v2 -p 'test_*.py' -v`; log reports `Ran 92 tests in 16.864s` and `OK`.
- Also verified runs #742 (`6aa2e020a0898d660abb57fc5488203738dc3444`) and #743 (`dc9d8f2335d1d380d287b1634baa7bafce209051`) completed successfully with the full-suite step passing.
- GitHub branch head matched the SHA tested by run #744 at verification time. This proves CI on GitHub only; no SSH/remote-shell tool is available in this session, so VM checkout fast-forward, dedicated dev-image rebuild, isolated container suite, and canary have NOT been executed or verified.
- Next action when on the VM: confirm clean checkout and ancestry; fast-forward only if safe; build only `job-radar-dev` using `v2/docker-compose.dev.yml`; verify exact image ID; run the full test suite in a `--network none` disposable container; only if that passes, run the read-only disposable two-poll Greenhouse canary. Do not touch production Compose/container or persistent database; keep Greenhouse disabled in config/scheduler and notifications off.


## VM isolated suite passed; CI found cursor-isolation issue — 2026-10-13

- User reported the VM disposable-container suite completed with `Ran 92 tests in 18.255s` and `OK`. The exact VM checkout SHA and image ID used for that run were not included, so do not yet treat it as validation of current branch head/image identity.
- Rechecked GitHub Actions run #746 for commit `fdf9654eddec287ac8b5f32a4d227b57ddafcd55`: it failed one test, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, because the process-wide `linkedin_fast_target_cursor` could be left at a nonzero value by earlier tests. This is test-state leakage; the failure was `second_cycle` length 0 rather than 2.
- Fixed the test to save, reset to zero, and restore `linkedin_fast_target_cursor` in commit `82d1082df84f7028822692a739949d65c879d8e2`. CI for this fix must pass before canary execution.
- Do not run the Greenhouse canary yet. Confirm the new commit's latest-head CI passes, and establish VM checkout/image identity before any canary. Production container/database untouched; Greenhouse remains disabled in config/scheduler; notifications remain off.


## Latest-head CI green; VM checkout needs safe fast-forward — 2026-10-13

- Verified current GitHub branch head `60c337f964f4b7b040d33c4f0c23773fc4c0a788`; latest-head Actions run #749 (`38365552304`) completed successfully. Run #747 for the test-cursor isolation fix (`82d1082df84f7028822692a739949d65c879d8e2`) also passed the full suite.
- User-provided VM output shows checkout `fdf9654eddec287ac8b5f32a4d227b57ddafcd55` and dev image `sha256:57a6a204922201f70e226116bb107ef0a82ac9b3da428b50f542e55809668364`, created at `2026-10-13T07:49:32Z`. This is behind current GitHub head; prior reported 92-test success therefore does not validate the latest commit.
- Next: on the VM fetch latest branch, confirm working tree clean and fast-forward ancestry, fast-forward only, then rebuild only the dedicated dev image, inspect its image ID, and rerun the full suite in a disposable `--network none` container. Do not run canary until that passes. No production container/database touched; Greenhouse remains disabled and notifications remain off.


## VM head/image and isolated tests verified; Greenhouse canary next — 2026-10-13

- User reports the dev VM checkout is `c15c40b699a89a78d4440d86eecd5ef8b4eff8f8`, clean on `v2-live-radar`; dev image is `sha256:10587b0403ade778c5f0bc844d6984da2a251789b0ae7545512a03e68d1febb5`, created `2026-10-13T07:57:37Z`; disposable image test suite passed `Ran 92 tests in 17.992s / OK`. The reported checkout matches GitHub branch head.
- Verified latest GitHub Actions run #751 for this head succeeded: https://github.com/AvinashBhalla/job-beeper/actions/runs/38365680132. Reviewed current `v2/config.dev.json` and `v2/greenhouse_canary.py`: notifications are false, Greenhouse source is disabled, and the canary makes two public-board polls without DB writes, matching, or notifications.
- Next action: run a disposable canary for one existing dev-config board (Coinbase) with 900 seconds between polls, using the rebuilt dev image and a network-enabled disposable container. Capture the JSON report and review ID stability, timestamp coverage, request errors, and job yield. This is a dev-only observation, not permission to enable Greenhouse or deploy. Production Compose/container and persistent database remain untouched.


## Coinbase canary first poll confirmed; waiting for second snapshot — 2026-10-13

- User screenshot shows the disposable canary command running on the verified dev image and log `boards=1 successful=1 failed=0 jobs=225`. This confirms the first Coinbase Greenhouse poll succeeded with 225 jobs; the final report is expected only after the configured 900-second interval and second poll.
- Advise the user not to interrupt the process yet; wait for the final JSON report. No production Compose/container or persistent DB touched; Greenhouse remains disabled in scheduler config and notifications remain off.


## Coinbase Greenhouse two-poll canary passed — 2026-10-13

- User supplied the final JSON report from the disposable two-poll canary on the verified dev image. Both polls completed with 225 jobs and 225 unique source IDs each; `stable_ids=225`, `new_ids_on_second_poll=0`, `missing_ids_on_second_poll=0`, duplicate IDs 0, and jobs without source IDs 0.
- Publication timestamps were present for all 225 jobs in both snapshots (unknown timestamp count 0). Report explicitly confirms `database_writes=0`, `matching_executed=false`, `notifications_sent=false`, `status=completed`.
- Conclusion: successful two-snapshot validation for the existing Coinbase board only. Do not enable Greenhouse in the scheduler or production based on this single-board canary. Any next step requires separate review of scope, board coverage, and operational acceptance. Production Compose/container and persistent database remain untouched; notifications remain disabled.


## User decision: close Coinbase canary and move to product roadmap — 2026-10-13

- User explicitly chose not to run more Greenhouse board tests after the Coinbase two-poll canary passed. Accepted evidence: 225 jobs in each poll, 225 stable unique IDs, zero duplicates/new/missing IDs, full publication timestamp coverage, no database writes/matching/notifications. No further Greenhouse polling is planned unless a concrete issue emerges.
- No code/config change this turn. Greenhouse stays disabled in scheduler config; notifications remain disabled; production Compose/container and persistent DB remain untouched.
- Reviewed docs/JOBBEEPER_REFERENCE.md: next implementation priority is the LinkedIn experience-parser patch validation/promotion, followed by the broader source roadmap. However, GitHub compare reports main...v2-live-radar as diverged (v2 ahead by 232 commits and behind by 8); v2/radar.py has different blob SHAs on the two branches. Do not merge or promote the diverged branch wholesale. Before the next code change, inspect the existing parser patch and isolate its minimal intended diff against current main, then use a safe focused promotion path with CI.
- Next action: inspect parser-specific changes/tests and branch history, determine whether the parser patch is already present on main, and propose/prepare a narrow change only if still needed. Preserve all existing production safety constraints.


## Next action: inspect isolated LinkedIn parser diff before safe promotion — 2026-10-13

- User asked to proceed with minimal explanation and wants only VM commands; assistant handles GitHub-side review. No code/config changes or VM mutations in this turn.
- Re-read the three source-of-truth docs before acting. Coinbase canary is accepted as complete; no additional Greenhouse board tests. Keep Greenhouse disabled, notifications off, production container and persistent database untouched.
- GitHub compare confirms `main...v2-live-radar` is diverged (v2 ahead by 234 and behind by 8); never merge or promote the branch wholesale. The current `v2/radar.py` parser patch adds `extract_linkedin_labeled_experience` and metadata parsing, while main has a different `v2/radar.py` blob. Next action is read-only local inspection on the VM of branch SHAs, relevant parser diff, parser-focused tests, and CI before deciding on a narrow cherry-pick/patch. Do not modify branches or deploy until the diff and target main state are established.
- User command requested: run the read-only Git inspection block supplied in chat and return all output. This is not a deployment command and does not touch runtime state.


## Inspection update: parser logic already exists on main — 2026-10-13

- Re-read handover, knowledge transfer, and reference docs. The user's VM output confirms the local checkout is clean but behind the latest remote v2 branch; remote heads are main `a1db74f...` and v2 `4e70f9c...`, with divergence reported as 4 main-only commits and 236 v2-only commits at that fetch.
- GitHub read-only review shows current `main` already contains `extract_linkedin_labeled_experience` and the focused LinkedIn structured-experience tests (`test_linkedin_structured_experience_metadata_outside_description_is_captured`, `test_linkedin_generic_experience_snippet_does_not_skip_jd_enrichment`, and overall-experience extraction tests). Therefore, do not cherry-pick the entire v2 branch or assume the parser is absent from main. Next step is compare the exact parser/enrichment/collector sections on both refs and inspect main CI to establish whether any small missing fix remains.
- No code changes or VM runtime changes made. Greenhouse remains disabled, notifications off, production container and persistent database untouched.


## VM comparison corrected: parser patch is missing from main — 2026-10-13

- User-provided VM output is authoritative for the checked refs: worktree clean on local `c15c40b...`; refreshed remote heads were `main=a1db74f...` and `v2-live-radar=c79d636...`, with divergence `4 main-only / 236 v2-only`. The second fetch advanced v2 after the first command block, so use the latest remote head rather than the earlier `4e70f9c...`.
- Correction to the prior note: `git show origin/main:v2/radar.py | grep ... extract_linkedin_labeled_experience` returned no match. Main has general overall-experience extraction tests, but not the new LinkedIn-labeled metadata parser or the two focused regression tests shown in the v2 diff. The v2 patch also contains unrelated Gemini shadow extraction and source-status observability changes, which must not be promoted with it.
- Decision: do not merge/cherry-pick the diverged v2 branch wholesale. Next step is a narrowly scoped promotion branch from current main containing only the LinkedIn labeled-experience parser/enrichment/collector fix and its focused regression tests; inspect dependencies and run CI before opening a PR. No production or VM runtime changes made. Greenhouse remains disabled; notifications remain off; persistent production database untouched.
- Expected evidence: focused diff against current main, PR/CI result, then only if CI passes provide VM commands for dev-only validation. Never deploy directly from v2-live-radar.


## Current refs rechecked before parser promotion — 2026-10-13

- Current GitHub compare reports `main=58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, with `v2-live-radar` 240 commits ahead and 8 behind. These refs differ from earlier VM output; do not act on stale SHAs.
- The current fetched `main:v2/radar.py` and `main:v2/test_radar.py` already contain the LinkedIn labeled-experience parser and focused regression tests. A parser promotion branch is not justified until a fresh VM fetch and exact diff establish a remaining fix.
- No code/runtime changes or deployment. Greenhouse disabled, notifications off, production and persistent database untouched.


## VM ref comparison: refresh remote-tracking main explicitly — 2026-10-13

- User's VM diff confirms the LinkedIn labeled-experience parser and focused tests exist on the fetched v2 branch relative to its reported `origin/main=a1db74f...`. However, `git fetch origin main v2-live-radar` reported main only as `FETCH_HEAD`; it advanced `origin/v2-live-radar` but did not refresh `origin/main`. Thus the displayed main SHA is likely a stale remote-tracking ref and is not valid evidence for promotion.
- Current GitHub API compare reports main `58fdff19...`, v2-live-radar 242 commits ahead and 8 behind; fetching current GitHub main confirms it already contains `extract_linkedin_labeled_experience` and the structured-metadata regression test. Do not promote parser code or merge the diverged branch.
- Next VM step is read-only: explicitly fetch `refs/heads/main:refs/remotes/origin/main` and `refs/heads/v2-live-radar:refs/remotes/origin/v2-live-radar`, then compare the updated refs. No code/runtime changes. Greenhouse remains disabled, notifications off, production and persistent database untouched.


## Parser comparison closed; next roadmap item is isolated Instahyre validation — 2026-10-13

- User refreshed both remote-tracking refs correctly: `origin/main=58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, `origin/v2-live-radar=55c3a3adf76c5fa39ba99f59c8e379ceec0dc8fa`. The exact diff shows no LinkedIn parser/enrichment change missing from main; v2-only `radar.py` hunks are Gemini shadow extraction and persisted source-error observability. Test diff is mostly rate-limit isolation and source-status error tests. Do not merge or promote the diverged branch.
- Main's Instahyre collector currently calls `https://www.instahyre.com/api/v1/job_search/`, uses a location and limit 35, accepts several possible payload shapes, and normalizes IDs/URLs/timestamps. Instahyre remains disabled by default. Next roadmap step is a bounded, read-only dev validation of its live response/schema/freshness and useful yield, without database writes, matching, notifications, or changing source enablement; only then decide whether adapter fixes are needed.
- No code, runtime, production container, or persistent database changes. Greenhouse remains disabled and notifications remain off.


## Instahyre validation preparation — 2026-10-13

- User VM output confirms `extract_linkedin_labeled_experience` is already present on `origin/main`; both inspected configs keep `instahyre` and `greenhouse` disabled. The local `v2-live-radar` checkout is clean but 18 commits behind its remote; do not run app code from this stale checkout or merge branches.
- Next step is a bounded direct GET-only probe of Instahyre's public search endpoint using `curl` and `jq`, saving only a temporary response under `/tmp` and summarizing payload shape, available fields, IDs, posting timestamps, and result count. This avoids importing the app, touching any database, matching jobs, changing source enablement, or sending notifications.
- No runtime/code/config/production changes. Greenhouse remains disabled and notifications remain off.


## Instahyre probe returned HTTP 400 — 2026-10-13

- User's bounded direct GET to `https://www.instahyre.com/api/v1/job_search/?jobLocations=Bengaluru&limit=35` returned HTTP 400, so no response JSON/schema, IDs, timestamps, or useful-yield evidence was obtained. Treat the endpoint as unvalidated; do not enable Instahyre or repeat broad probing. A single bounded diagnostic may inspect status/body only if needed; otherwise move to the next documented public ATS source.
- The command failed before writing `/tmp/instahyre_probe.json`; VM `git status` remains clean on `v2-live-radar`, 18 commits behind `origin/v2-live-radar`. No code/config/runtime/database changes; notifications remain off and Greenhouse remains disabled.


## Ashby PostHog board probe — 2026-10-13

- Read-only public Ashby endpoint returned 10 listed jobs with 10 unique IDs and no missing IDs, titles, URLs, or publication timestamps. Sample roles are mixed and many are region-specific; one board is not enough evidence to enable a source. Keep scheduler flags unchanged, notifications off, and production untouched. VM checkout remains clean but 24 commits behind `origin/v2-live-radar`; do not run app code from this stale checkout.


## Ashby OpenAI board probe — 2026-10-13

- User-provided read-only VM output for the public Ashby OpenAI board shows 808 listed jobs, 808 unique IDs, and no missing IDs, titles, job URLs, or published timestamps. The payload is structurally promising, but the sample contains postings dated as far back as 2023 and is globally distributed; structure alone does not establish freshness or useful India/remote yield.
- Next step: summarize the already-downloaded /tmp/ashby_openai_probe.json locally by publication-age buckets and India/remote locations; do not repeat the network request, run app code from the stale checkout, enable Ashby, change scheduler/config, run matching, send notifications, or touch production/database volumes.
- No repository code, config, runtime, production, or database changes. Greenhouse and Instahyre remain disabled; notifications stay disabled for all validation work.


## Ashby OpenAI timestamp parsing correction — 2026-10-13

- The first local summary command failed because jq `fromdateiso8601` rejected fractional seconds with a `+00:00` timezone suffix (example: `2026-03-12T16:38:15.322+00:00`). The corrected read-only jq command strips fractional seconds, normalizes `+00:00` to `Z`, and safely counts unparseable timestamps.
- Next step remains local analysis of the already-downloaded `/tmp/ashby_openai_probe.json`; do not repeat the network request, run app code from the stale checkout, enable Ashby, alter scheduler/config, run matching, send notifications, or touch production/database volumes.
- No repository code, config, runtime, production, or database changes. Greenhouse and Instahyre remain disabled; notifications stay disabled for this validation.


## Ashby OpenAI freshness and geography summary — 2026-10-13

- User-provided local jq summary of the already-downloaded public Ashby OpenAI board payload `/tmp/ashby_openai_probe.json`: 808 total jobs; 8 India-location matches; 30 remote-location matches; 35 matching India OR remote (sets overlap); 237 published within 30 days; 532 within 90 days; 59 older than one year; 0 unparseable publication timestamps.
- Timestamp parser issue is resolved. The initial `jq fromdateiso8601` failed on fractional seconds and `+00:00`; the corrected summary successfully parsed all timestamps. Do not repeat the network request just for this summary.
- Interpretation: payload structure and timestamps are complete, and the board has a substantial fresh pool overall, but only 35/808 (4.3%) match the broad India-or-remote location text filter, including just 8 explicit India matches. The remote text match does not establish remote eligibility for India; location semantics and role relevance still need inspection. This is promising enough to consider an isolated Ashby adapter implementation with a narrow board allowlist, but is not evidence to enable the source in the scheduler.
- Next work: inspect current `v2-live-radar` docs and source code again; design a minimal Ashby public posting API adapter behind a default-off feature flag, with stable job IDs, canonical apply URLs, company/title/location/description/publishedAt normalization, pagination/board configuration, bounded requests/backoff, per-source error isolation, and fixture-based tests. Start with a small explicit board allowlist and assess useful India-eligible/remote-eligible developer-role yield before expanding. Keep Ashby disabled, notifications disabled for validation, and do not run matching or touch production/persistent database volumes until a separately reviewed dev validation plan is approved.
- Other source outcomes remain: PostHog Ashby board returned 10 structurally complete jobs but mixed regional relevance; Instahyre endpoint returned HTTP 400 with `{"job_locations":["Invalid location"]}` and remains unvalidated/disabled; Coinbase Greenhouse two-poll canary passed with 225 stable jobs per poll and no duplicates/new/missing IDs, but Greenhouse remains disabled.
- No code, config, runtime, production, or database changes were made for this summary. Never merge the diverged `v2-live-radar` branch wholesale into `main`; do not enable sources or notifications as a side effect of adapter development.


## Ashby adapter implementation readiness — 2026-10-13

- Re-fetched the current three required documents from `v2-live-radar` and inspected the current source/config files directly on GitHub. This was GitHub-side inspection only; no VM commands were run.
- Current `v2/radar.py` has collectors for LinkedIn, Naukri, Instahyre, and Greenhouse only. No Ashby collector or Ashby entry exists in `COLLECTORS`; current config validation recognizes only those four sources. The current V2 config is version 10, and Ashby is not yet represented in either `v2/config.json` or `v2/config.dev.json`.
- Current development config is safely isolated in configuration: notifications are disabled; LinkedIn, Instahyre, and Greenhouse are disabled; Naukri alone is enabled. Preserve that state. Root `config.json` is a different legacy/configuration surface and must not be changed for this V2 adapter task.
- The Ashby OpenAI public-board summary remains the latest measured payload evidence: 808 jobs; 8 India text matches; 30 remote text matches; 35 in the overlapping India OR remote union; 237 published within 30 days; 532 within 90 days; 59 older than one year; zero unparseable timestamps. The broad text filter does not prove remote eligibility in India or role relevance. Do not repeat this request.
- Next implementation: add a minimal public Ashby posting API collector behind a new explicit `ashby_boards` allowlist and a default-off `source_enabled.ashby` flag; bump config version and migrate existing persisted configs so Ashby cannot become enabled implicitly; add a conservative poll interval; normalize stable IDs, company/title/location, direct job URL, description and `publishedAt`; handle malformed payloads, partial board failures, duplicate IDs and unknown timestamps; add deterministic fixture-based unit tests for valid/empty/malformed/failed-board payloads and default-off migration.
- Validation must remain synthetic/unit-test first. Do not run matching, persist jobs, send notifications, enable Ashby in either scheduler config, touch production services or persistent volumes, or run app code from the stale VM checkout. Verify current refs and exact diff before any commit. Use CI evidence only after the workflow actually completes; no test or CI result is claimed in this entry.
- No code/config/runtime/production/database changes were made in this inspection turn. Greenhouse and Instahyre remain disabled; notification safety restrictions remain in force. Never merge the diverged `v2-live-radar` branch wholesale into `main`.


## 2026-10-13 — Ashby adapter engineering update
- Current branch inspection found no Ashby source; config v10 and source registry/migration conventions were in `v2/radar.py`. Added adapter with explicit `ashby_boards` allowlist (OpenAI and PostHog seed entries, maximum 20), per-board 15-second bounded GET, deterministic board-scoped IDs, direct job URLs, description normalization, duplicate suppression, partial-failure isolation and strict `publishedAt` parsing. Missing/malformed publication time remains unknown; `updatedAt` is not substituted. Config v11 migration forces Ashby off in existing pre-v11 persisted runtime configs; poll target is 1800 seconds.
- Changed files include `v2/radar.py`, `v2/config.json`, `v2/config.dev.json`, `v2/test_radar.py`, and `v2/README.md`; dated update appended to the detailed handover. Commits so far: `ea7b02b35b4667a91aca6bb7f5428c607b0be6f9`, `7e69799e650e09ba00fee98397bed4c959ab429f`, `04cae9034a7d084319989b1f63df2c648d1ba981`, `1b5f1ff93d4d88040b028b32c6eb895a15ad5eec`, `a00e00ec5ac2f1da48db75b27938506001ccd1ca`, and handover commit `b550fe97535ac10d8f7f64f1554aafb19a6e0b28`. Documentation verification remains pending in this note.
- Tests added cover valid, empty, malformed/partial and total failures, duplicate IDs, no-update-time fallback, migration and allowlist validation. No local execution is claimed; CI must be checked for the final branch head. No deployment or VM validation occurred.
- Ashby is false in both V2 configs; development notifications remain false. Production services/DB/volume, root config, `main`, Greenhouse, Instahyre and matching/notification code paths were not altered. No repeated Ashby/Greenhouse/Instahyre probes; no matching or notifications ran.
- Remaining risks: live payload variation, timestamp completeness, India/remote eligibility, relevant role yield and historical alert replay. Next: finish docs, re-fetch both docs and changed files to verify, then inspect CI. If CI is green, plan a separate read-only dev validation with notifications disabled and Ashby still off. Do not merge the diverged branch wholesale into main.


## Follow-up validation — 2026-10-13
- GitHub Actions runs `38413031061`, `38413124663`, and `38413220587` ran 100 tests and reported one failure: existing LinkedIn round-robin rotation test had zero mocked calls on the second cycle because the test did not isolate the global rate-limit cooldown. These runs are failures, not passing CI.
- Added an isolation patch in `v2/test_radar.py` so the rotation test stubs `_linkedin_cooldown_remaining` at zero and tests the cursor only. Commit `7d6c3d3df76b9c269608a83173b08e331077b67e`. The corresponding CI run `38413635868` was queued at the time of this note; do not assume its outcome.
- Ashby stays disabled in both v11 configs; development notifications remain off. No local tests, VM commands, deployment, matching or notifications occurred. Next: inspect the run result and re-fetch both handover files to verify these notes. Production and main remain untouched.


## Final verification — 2026-10-13
- Verified branch head before this documentation commit: `83a2de2a042209f4267fc98e22f859c4e9d7c899`. GitHub Actions run `38413707935` succeeded; job `syntax` passed and log states 100 tests ran, `OK`: https://github.com/AvinashBhalla/job-beeper/actions/runs/38413707935
- Re-fetched and verified both handover documents and V2 config files. Both docs include today's dated entries. Config version 11 in both files; Ashby disabled and set to a 1800-second poll target; development notifications disabled.
- No deployment, VM commands, production access, matching, notifications, or repeated live source probes. `main`, root config, Greenhouse and Instahyre activation unchanged.
- Next: request the user's local checkout status/path only if needed to run read-only development validation; keep sources/notifications disabled. Then inspect historical-listing replay protections and assess a separate Ashby activation review only after measured eligibility and relevance results.


## Development checkout test verification — 2026-10-13
- User ran the test suite from `/home/ubuntu/job-beeper-dev` after fast-forwarding branch `v2-live-radar` to `a9dd83953d06f360ca707ba207387961818241d9`.
- The project runtime dependencies installed from `v2/requirements.txt`; that requirements file did not install pytest, so the user installed pytest into the checkout-local `.venv` only. No repository dependency files were changed.
- Verified user-reported command: `python -m pytest -q v2/test_radar.py v2/test_greenhouse_canary.py v2/test_gemini_extractor.py` → **100 passed, 4 warnings, 2 subtests passed in 12.56s**.
- The four warnings are FastAPI `on_event` startup/shutdown deprecations in `v2/radar.py` / FastAPI; they did not fail tests. This is unit-test evidence only, not a runtime/deployment check.
- No service was started; no matching, source polling, database writes, or notifications were run. Ashby, Greenhouse, and Instahyre remain disabled; notifications must remain disabled in dev.
- Next: verify the local checkout branch/HEAD/working tree and inspect `v2/config.dev.json` to confirm source flags and notification state. If safe, proceed only with explicitly read-only validation; do not run the service or change source enablement as part of this step. Record the exact output before planning the next canary.


## Dev checkout status follow-up — 2026-10-13
- User verified the local development checkout at `/home/ubuntu/job-beeper-dev`: branch `v2-live-radar`, HEAD `a9dd83953d06f360ca707ba207387961818241d9`.
- `git status --short` reports ` M v2/config.json` and untracked `.venv/`. The changed root V2 config is not yet inspected; preserve it and do not reset/checkout it until its diff is reviewed. The untracked virtual environment is expected local tooling and must not be committed.
- Parsed `v2/config.dev.json`: `config_version=11`; LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, Ashby=false; `notifications_enabled=false`.
- User-reported unit tests on this checkout passed: 100 passed, 4 FastAPI deprecation warnings, 2 subtests passed in 12.56s. No service, matching, polling, database writes or notifications were run.
- Next exact action: from `~/job-beeper-dev`, run `git diff -- v2/config.json` and `git diff --stat`; inspect output before deciding whether the local config modification is an intentional local-only change. Do not include `.venv/` in commits. Keep production, `main`, services, source flags and notification settings untouched.


## Local checkout fast-forward — 2026-10-13
- User restored only the formatting-only changes in `v2/config.json`; `git status --short` showed only the local untracked `.venv/`, which must remain uncommitted.
- User fetched `origin/v2-live-radar`; local branch was reported four commits behind, then `git pull --ff-only origin v2-live-radar` completed successfully as a fast-forward from `a9dd839` to `48e921a`, updating only `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` (17 lines each).
- Next: verify with `git status -sb` and `git rev-parse HEAD`. No services, polling, matching, DB writes, or notifications were run; keep source flags and notifications unchanged.


## Checkout synchronized — 2026-10-13
- User fast-forwarded local `~/job-beeper-dev` from `48e921a` to `cab194b1c62dc2cbe07e0c1673813000b67b2601`, matching `origin/v2-live-radar` at the time of verification.
- `git status -sb` shows branch aligned with origin and only `?? .venv/`; retain the virtual environment locally and do not commit it.
- Next safe step: run a read-only check of `v2/config.dev.json` source flags and notification setting, plus JSON syntax validation. Do not start services, poll sources, run matching, write to the DB, or send notifications.


## Read-only config validation confirmed — 2026-10-13
- User ran the sync successfully; local `v2-live-radar` was aligned with `origin/v2-live-radar` at `cc98d62be1fd78a3266dd813f6a8029ae64f0d7a`. `git status -sb` showed only `?? .venv/`; keep it local and uncommitted.
- User's Python check confirmed both `v2/config.json` and `v2/config.dev.json` are valid JSON. Development config is version 11 with LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, Ashby=false, and `notifications_enabled=false`.
- No application/service was started; no source polling, matching, DB writes, or notifications were run. Combined commit status lookup for `cc98d62` returned no status checks, so do not describe that commit as CI-verified.
- Next: if continuing, inspect the existing read-only Greenhouse canary utility and its usage/tests, without executing network polling or starting the radar service. Preserve disabled sources/notifications and production isolation.


## Greenhouse canary code review — 2026-10-13
- User fast-forwarded `/home/ubuntu/job-beeper-dev` to `3db196dfd07fce316ad501d310c7f86c4fcd61e8`, matching `origin/v2-live-radar`. `git status -sb` showed only untracked `.venv/`; retain locally and do not commit.
- User supplied read-only inspection output for `v2/greenhouse_canary.py` and `v2/test_greenhouse_canary.py`. Code implements two snapshots of one explicit board, enforces a minimum 60-second interval (default 900 seconds), reports unique/stable/new/missing IDs, duplicate and missing source IDs, and published timestamp coverage. Tests cover report arithmetic, two collection calls/sleep, and invalid inputs before collection.
- This is a static review of supplied source plus mocked unit tests, not evidence of a live request or board yield. No canary execution, service startup, scheduler polling, matching, DB writes, source activation, or notifications occurred.
- Keep `source_enabled.greenhouse=false` and `notifications_enabled=false` in development. Do not activate Greenhouse or touch production/main. Before any separate canary run, inspect the existing `greenhouse_boards` allowlist read-only and select exactly one already-configured board; use the utility directly, not the radar service. Review the JSON report for failures, duplicate/missing IDs, timestamp coverage and useful yield. Preserve the local `.venv/`.
- Next exact action: read-only inspect the current `greenhouse_boards` entries in `v2/config.dev.json` and verify the local branch/HEAD/status. No code changes or runtime validation claimed. Continuation: select one existing board for an explicitly bounded read-only canary only after reviewing its config entry; do not enable the source or notifications.


## Greenhouse board allowlist reviewed — 2026-10-13
- User reported local `~/job-beeper-dev` branch `v2-live-radar`, HEAD `3db196dfd07fce316ad501d310c7f86c4fcd61e8), aligned with origin before pulling the prior handover notes. Working tree showed only untracked `.venv/`. User then successfully fast-forwarded from `3db196d` to `ff44a6466529ea80b36e2a6d8345962f955e1b11`, updating only the two handover docs.
- Read-only parse of `v2/config.dev.json` reported Greenhouse disabled and notifications disabled. Existing configured boards are `coinbase` / Coinbase, `gravitonresearchcapital` / Graviton Research Capital, and `zocdoc` / Zocdoc. No config was changed.
- Earlier documented Coinbase two-poll canary returned 225 jobs in each poll with all 225 IDs stable, no new/missing/duplicate IDs and timestamp coverage present; this is historical evidence for those two snapshots only. For a distinct board-level payload check, propose a one-board Zocdoc canary, using only its existing allowlist entry.
- No live canary was run in this turn; no service startup, scheduler polling, matching, DB writes, source activation or notifications. Preserve `.venv/` locally; do not commit it. Keep Greenhouse false and notifications false; production and `main` untouched.
- Next action: from repository root with the local virtual environment active, run `python -m v2.greenhouse_canary --board-token zocdoc --company "Zocdoc" --interval-seconds 900`, which performs two public GET polls 15 minutes apart. Retain the JSON report and review request success, counts, ID stability, duplicate/missing IDs, timestamp coverage and useful yield. This does not authorize scheduler activation. After the report, record evidence and decide next step separately.


## Zocdoc Greenhouse two-poll canary result — 2026-10-13
- User ran `python -m v2.greenhouse_canary --board-token zocdoc --company "Zocdoc" --interval-seconds 900` from the dev checkout and supplied the completed JSON report.
- Live collector logs reported `boards=1 successful=1 failed=0 jobs=58` on both polls. Report: 58 jobs and 58 unique IDs in each poll; 58 stable IDs; zero new IDs and zero missing IDs on poll two; zero duplicate source IDs; zero jobs without source IDs; 58/58 published timestamps present in each poll. Status completed.
- Assessment: clean two-snapshot stability and timestamp/ID coverage for this Zocdoc board during this test window. This does not establish longer-term freshness, relevant-job yield, or unseen/new-job discovery. Treat as board-and-window-specific evidence only.
- Report states `database_writes=0`, `matching_executed=false`, `notifications_sent=false`. No service/scheduler was started and no source toggle was changed as part of this canary. Keep Greenhouse disabled in dev and notifications disabled; do not touch production or main.
- No code/config change. Existing local `.venv/` remains local and must not be committed.
- Next: record this canary as passed for the two-poll stability gate; before any scheduler activation, separately review relevant/new-job yield and source health strategy, then obtain explicit approval for any config activation. Do not enable Greenhouse merely because this canary passed.
- Continuation: start by reading this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; inspect only evidence relevant to the next explicitly approved step.


## Local handover sync reported — 2026-10-13
- User confirmed they completed the requested `git pull --ff-only origin v2-live-radar` after the Zocdoc canary. Pull output/HEAD was not pasted, so this is user-reported rather than independently verified local-state evidence.
- Read the latest handover, knowledge-transfer, and JobBeeper reference documents from `v2-live-radar`; no repository code/config changes were made in this turn.
- Zocdoc two-poll canary evidence remains: 58 jobs in each poll; all 58 IDs stable; no duplicates, missing IDs, missing source IDs, or unknown published timestamps. The test did not establish relevant-job yield.
- Next exact action: run one additional read-only Zocdoc public-board sample and print only a compact summary of job titles, locations, publication timestamps, and source URLs (no descriptions), so useful yield can be assessed. Do not start the app/scheduler, change source toggles, write the database, run matching, or send notifications. Keep Greenhouse and notifications disabled; leave production and `main` untouched. Preserve local `.venv/` untracked.
- Continuation: review the compact sample for relevant/new-job yield before proposing any source activation; this does not itself authorize activation.


## Zocdoc job-yield sample reviewed — 2026-10-13
- User supplied one live read-only sample from `snapshot("zocdoc", "Zocdoc")`: 58 jobs returned; first 15 shown with titles, locations, posted timestamps and URLs. This was one public-board request, not a scheduler run.
- Sample contains many US-based sales/manager/director roles and several old general-interest/application postings. India-based examples include Analyst, Quality Assurance (Pune), Coordinator, Workplace Experience (Pune), Enterprise Support Associate (Pune), and General Interest Technology/Operations roles. This sample shows some India presence but weak apparent fit against dev target roles (software/full-stack/frontend/backend/Python/AI/LLM engineering) and configured locations (Bengaluru, Gurugram, Delhi, Remote India); Pune is not in the configured location list. Since only 15 of 58 were inspected and no matcher was run, do not generalize to all 58 or claim a definitive relevance count.
- Assessment: Zocdoc passed the two-poll ID/timestamp stability check, but the visible sample is not compelling evidence of useful yield for the current target profile. Do not activate Greenhouse on the strength of this board alone.
- Next: inspect a compact sample from the existing Coinbase board using one public GET, with no descriptions, matching, database writes, source activation, scheduler startup or notifications. Compare the sample against target roles/locations before deciding whether to evaluate Graviton Research Capital. Keep Greenhouse and notifications disabled; production and `main` untouched; preserve local `.venv/` untracked.


## Coinbase Greenhouse sample — 2026-10-13
- Read-only user-provided sample: `snapshot("coinbase", "Coinbase")` returned 226 jobs; log showed 1 board successful, 0 failed. First 20 entries are largely finance/accounting, legal, operations, management and internships across non-target geographies. Alphabetical first-20 output cannot establish total engineering-role yield; no matcher was run and no definitive relevant count is known.
- Conclusion: successful retrieval, but insufficient evidence of useful yield for configured India locations and software/AI engineering target roles. Greenhouse and notifications remain disabled; no config/code change, DB write, matching, scheduler run, notification, CI or deployment occurred. Production and `main` untouched; keep local `.venv/` untracked.
- Next: optionally produce a compact role/location summary across the full payload or role-filtered counts as a read-only analysis; do not activate the source based on this sample. Review `docs/JOB_RADAR_HANDOVER.md` and `docs/JOBBEEPER_REFERENCE.md` before continuing.


## Coinbase full-payload relevance check proposed — 2026-10-13
- User says latest docs were pulled; local branch/HEAD not independently verified. Current `v2/config.dev.json` has Greenhouse and notifications disabled, target India locations (Bengaluru, Gurugram, Delhi, Remote India), and software/AI/LLM engineering target roles.
- Existing one-GET Coinbase sample returned 226 listings; only the first 20 alphabetically were inspected and they were mostly non-target functions/geographies. There is not yet a defensible full-board relevance count. No code/config changes, matching, DB writes, scheduler run, notifications, CI or deployment.
- Next: perform a bounded, read-only one-GET analysis of all Coinbase job titles/locations, count role and geography keyword hits/overlap/exclusions, and show a small candidate sample. These are heuristic indicators, not deterministic matcher results. Keep Greenhouse and notifications disabled; leave production and `main` untouched; preserve local `.venv/`.


## Coinbase full-payload keyword yield assessed — 2026-10-13
- User ran a single-GET heuristic scan of all 226 Coinbase listings: 82 title keyword hits, 9 target-location hits, 7 overlap, and 174 titles containing exclusion terms. Counts overlap and are not actual matcher results; overlap can include excluded senior/staff/manager jobs and old postings. Example Remote - India Machine Learning Engineer listing was posted 2026-06-22, outside the configured 72-hour window as of this review.
- Decision: source retrieval works, but useful current yield is low/uncertain for the configured India locations and software/AI target profile. Keep Greenhouse and notifications disabled. No code/config changes, matching, DB writes, scheduler, notifications, CI or deployment. Production and `main` untouched; preserve local `.venv/` untracked.
- Next: optionally assess the existing allowlisted Graviton Research Capital board using one read-only public GET and title/location/posting-time summary, then compare likely relevant and fresh yield. Do not activate Greenhouse or start the scheduler without a separate approval.


## Graviton sample reviewed — 2026-10-13
- Read-only sample from the configured Graviton Research Capital Greenhouse board: 1 successful board, 0 failed, 20 jobs. Visible likely target examples were dated 2026-09-04 (Application Reliability Engineer), 2026-03-10 (Machine Learning Researcher), 2026-09-01 (Software Engineer graduate), 2021-02-23 (Software Engineer), and 2025-09-01 (Software Engineer-Python); these are all outside the 72-hour freshness window as of 2026-10-13. Data Center Engineer dated 2026-10-06 is not clearly a target software/AI role. A sample cannot establish closure status.
- Successful retrieval does not demonstrate fresh relevant yield. With previous Coinbase and Zocdoc samples, do not enable Greenhouse. Keep Greenhouse and notifications disabled; production and main untouched.
- No code/config change, matcher, DB write, scheduler, notification, CI, or deployment occurred. Preserve local .venv untracked.
- Overall status: V2 core architecture and integrations exist; remaining acceptance includes fresh/relevant yield, verified end-to-end normalization/deduplication/matching/alert correctness, dev runtime checks, safe production rollout, and observation. No completion percentage claimed without a full acceptance audit.
- Next: prioritize measurable fresh India/Remote-India software/AI yield; pull the updated handover before the next local command.


## MVP fast-track — 2026-10-13
User prioritizes an early MVP. Freeze scope; defer experimental sources and nonessential features. Keep Greenhouse/Ashby/Instahyre and dev notifications disabled. Next, collect read-only dev health/status/log diagnostics before tests or any deployment. No code/config/runtime changes or production actions in this turn. Preserve .venv untracked.


## MVP decision rule and dev diagnostics — 2026-10-13
- **Mandatory scope rule:** Every task must either remove a launch blocker, verify a launch requirement, or improve the usefulness of the MVP. If it does none of those, defer it. Classify the task against one of these outcomes before doing the work.
- User-provided read-only diagnostics: dev branch `v2-live-radar`, HEAD `8992ac8`, aligned with origin; `.venv/` remains the only untracked item. Isolated container `job-radar-dev` is up on loopback port 8001; health is OK, version 2.0.0, DB `/data/jobs.db`. Naukri last success 2026-10-13T16:04:43Z, 351 jobs seen, 0 new in latest poll, no reported error; recent logs show repeated polls and some new jobs. Zero new jobs in one poll is not a failure by itself.
- Verified: basic dev health and active Naukri polling. Not yet verified: fresh/relevant yield, matcher/dedupe, alert-ledger idempotency, full test suite, production readiness. No tests, DB inspection, matching, notifications, config changes, restart, CI or deployment occurred. Production and main untouched; preserve `.venv/` untracked.
- Next: run the existing dev test suite, address only real launch blockers, then verify matching/freshness/dedupe/notification safety through existing tests or read-only checks. Keep experimental sources and notifications disabled. Pull updated docs before the next local command.


## Next MVP gate: existing CI checks — 2026-10-13
- User has pulled the updated handover docs. Next action verifies a launch requirement; defer unrelated work under the MVP decision rule.
- Current `.github/workflows/v2-ci.yml` specifies these checks after dependencies are installed: `python -m py_compile v2/radar.py v2/test_radar.py v2/greenhouse_canary.py v2/test_greenhouse_canary.py`, then `python -m unittest discover -s v2 -p 'test_*.py' -v`. Agent has not run these commands on the VM.
- Ask user to run both from `~/job-beeper-dev` in the active `.venv` and paste complete output. No service restart, config/source changes, notifications, or production actions. Preserve `.venv/` untracked.


## Existing test suite passed — 2026-10-13
- User reports the existing unittest discovery completed: `Ran 100 tests in 19.302s`, `OK`. This is user-reported output; agent has not run the tests directly on the VM.
- Unit tests passed, but source yield/freshness, live matcher/dedupe correctness, notification-ledger idempotency, and production readiness remain unverified. No code/config/service changes and no production actions.
- Next: confirm `python -m py_compile v2/radar.py v2/test_radar.py v2/greenhouse_canary.py v2/test_greenhouse_canary.py` also passed; if not, run it in `~/job-beeper-dev` with `.venv` active. Then review only remaining MVP acceptance gates. Keep experimental sources and dev notifications disabled; preserve `.venv/`; do not touch `main` or production.


## MVP test gate passed and next-agent contract — 2026-10-13
- **Product goal:** dependable low-noise discovery of fresh India/Remote-India software/AI jobs, truthful timestamps/stable IDs, normalization and cross-source deduplication, explainable deterministic matching, and reliable alerts for eligible new matches. Raw job count and process health are not sufficient proof of usefulness or launch readiness.
- **Mandatory task filter:** every task must remove a launch blocker, verify a launch requirement, or improve MVP usefulness; otherwise defer it. Freeze scope and explicitly classify proposed work against this rule.
- **Latest user-reported verification:** compile command `python -m py_compile v2/radar.py v2/test_radar.py v2/greenhouse_canary.py v2/test_greenhouse_canary.py` returned without errors. The user then ran `git pull --ff-only origin v2-live-radar`; output showed fast-forward `a3034cb..1284b0a` and only the two handover docs changed. The existing test suite reported `Ran 100 tests in 19.302s`, `OK`. These are user-supplied results, not independently executed by the agent.
- **Achieved:** prior dev health check returned status OK and Naukri polling had no reported error; compile passed; 100 unit tests passed; Greenhouse board canaries passed basic two-poll ID/timestamp stability but sampled yield was weak/uncertain. Greenhouse, Ashby, Instahyre, Gemini shadow extraction, and development notifications remain disabled unless explicitly approved. Production and `main` have not been changed by this verification work.
- **Remaining launch gates:** demonstrate fresh/relevant target-role yield; verify end-to-end normalization, dedupe, freshness and matcher explanations/exclusions; verify notification-ledger idempotency and no replay; confirm production DB backup and persistent-volume identity; then conduct an explicitly approved production cutover, smoke test and 24–72-hour observation. Do not claim readiness or a completion percentage without evidence for the gates.
- **Next action:** sync the newest docs, then inspect existing tests/code to select one safe, test-based or read-only check of the most important remaining MVP gap. Do not rerun passing tests without a reason, access or mutate the live DB, restart/rebuild services, or send notifications merely to gather evidence. Ask the user for only the precise commands needed and review full output before recommending changes.
- **Mandatory documentation contract:** every agent must read this file, `docs/JOB_RADAR_HANDOVER.md`, and `docs/JOBBEEPER_REFERENCE.md` before substantive work. At every turn end, update BOTH this knowledge transfer and the detailed handover, even if no code changed. Include goal/decision rule, achievements, exact evidence and whether user-reported or independently verified, current branch/runtime/deployment state, changed/unchanged paths, tests/CI, remaining risks and gates, one exact next action with copy-paste commands and expected output, and a next-agent continuation prompt. Update `JOBBEEPER_REFERENCE.md` only for architecture/guardrail changes. Fetch the latest content/SHA before sequential writes and re-fetch to verify. Never claim commands/tests/deployment not proven by output.
- **Next-agent communication style:** user specifically wants commands to run, with only a brief explanation and what output to return. Put broader project history and context here in the handover; do not overwhelm the user with repeated background. Work one issue at a time, evidence first; do not touch production or `main`, change configs, enable sources, or activate notifications without explicit approval.
- **Before next local command:** `git pull --ff-only origin v2-live-radar` (this note is newer than the user's last reported pull). Preserve local `.venv/` untracked.


## MVP acceptance review — 2026-10-13 (current agent turn)
- **Product goal:** deliver a reliable, low-noise Job Radar MVP for fresh/relevant India and Remote-India software/AI jobs, with truthful timestamps, stable IDs, canonical cross-source dedupe, deterministic/explainable matching, and safe alert delivery.
- **Mandatory scope rule:** every task must remove a launch blocker, verify a launch requirement, or improve MVP usefulness; otherwise defer it. This turn serves **verification of a launch requirement**.
- **Documents reviewed:** this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` were fetched from `v2-live-radar` via GitHub on 2026-10-13. The previously fetched blob SHAs were handover `6c896ed39f581eae5925c2e3552dbc35391054b2`, knowledge transfer `18ed2193b65a3360d36035aea3576f05c8c6bb4d`, reference `1d06ece64cc5abe296953776a79dedf654b95485`. Raw URL fetches returned 404, but GitHub repository-file retrieval on the specified branch succeeded.
- **Current evidence (user-reported, not independently run on VM):** development checkout is `~/job-beeper-dev`, branch `v2-live-radar`; `127.0.0.1:8001/health` was healthy, Naukri polling had no reported error, compile check completed without errors, and existing tests reported 100 passed in 19.302 seconds (`OK`). Greenhouse board samples demonstrated basic two-poll ID/timestamp stability but not useful fresh target-profile yield. The agent did not run these commands on the user's VM.
- **Most important remaining MVP acceptance gap:** demonstrate actual **fresh and relevant job yield for the target profile**. Process health and total jobs seen do not prove the feed is useful. End-to-end normalization/dedupe, deterministic match reasons/exclusions, notification-ledger idempotency/no historical replay, production backup/volume identity, and approved cutover remain unverified.
- **What changed / deliberately unchanged:** documentation only; no application code, configuration, DB, service, scheduler, source enablement, notification, CI, deployment, `main`, or production change. Keep Greenhouse/Ashby/Instahyre and development notifications disabled. Preserve local `.venv/` as untracked and never delete or commit it.
- **Next exact action:** user must synchronize the newly updated handovers before any further local command: `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`. Expected output is a fast-forward (or “Already up to date”) with handover-doc changes only; paste the complete output. After confirming sync, select one bounded read-only/test-based check of fresh/relevant yield without rerunning the passing suite, mutating the DB, restarting containers, or sending notifications.
- **Continuation instructions:** read all three documents on `v2-live-radar`; work one issue at a time; provide copy-paste commands and briefly state purpose/expected output; review returned evidence before deciding next step. At every turn end, update both handovers sequentially using freshly fetched content/blob SHA and verify both updates. Do not touch `main` or production without explicit approval.


## User confirmed handover sync; next read-only yield audit — 2026-10-13
- **Product goal / scope rule:** prove useful, fresh India/Remote-India software/AI job discovery for the target profile. Every task must remove a launch blocker, verify a launch requirement, or improve MVP usefulness; this task verifies the fresh/relevant-yield launch gate.
- **User-reported evidence:** user ran `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`; it fast-forwarded local tracking from `f2ed8b5` to `566e6f5`, changing only `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` (22 insertions). This confirms the previous documentation updates are synced locally.
- **Next action:** run a bounded read-only audit against the isolated dev API on `127.0.0.1:8001`: fetch `/api/daily-summary`, `/api/source-status`, and `/api/jobs?today_only=true&limit=100`; print only aggregate counts and selected job fields (source/title/company/location, posted/discovered timestamps, match score/reasons, alertable/status) so no URLs or secrets are exposed. This checks whether today's feed has fresh, relevant target-profile yield and shows its existing persisted decisions; it must not trigger matching, mutate the DB, or send notifications.
- **Expected output:** JSON summary, source enabled/last-run/new-job/error status, and a compact list of today's observed jobs. A lack of today's jobs is evidence to investigate, not proof of a code defect. Paste the complete output for review.
- **Known state / unchanged:** user previously reported dev health OK, Naukri polling without error, compile clean, and 100 tests passing in 19.302s; not independently executed by agent. Do not rerun passing tests without a reason. Keep Greenhouse/Ashby/Instahyre and dev notifications disabled; do not restart/rebuild services or touch production/main. Preserve `.venv/` untracked. Fresh/relevant yield, cross-source dedupe, deterministic matcher explanations, notification-ledger idempotency/no replay, production backup/volume identity and approved cutover remain open gates.
- **Continuation:** review full audit output before selecting the next step. At every turn end, update both handovers sequentially after fetching current content/blob SHA, then refetch and verify. Ask the user to pull updated docs before their next local command.


## 2026-10-13 — Read-only API audit command correction
- The user's attempted audit command failed because Ubuntu reports `python: command not found`; the pasted command also appears duplicated/corrupted. No audit output is available yet, so make no claims about API health, database state, source status, or fresh/relevant yield.
- Provided a corrected `python3` heredoc that reads only `/api/daily-summary`, `/api/source-status`, and `/api/jobs?today_only=true&limit=100` from isolated dev API `127.0.0.1:8001`, displaying selected job fields and catching request errors. It is read-only and does not run matching, write to the DB, send alerts, enable sources, or restart services.
- Next action: wait for complete output; diagnose only from evidence. If connection fails, retain the exact exception and inspect service status without restarting. If results arrive, evaluate posting/discovery timestamps, relevant job yield, source health, matcher reasons, and notification ledger state. Empty daily results alone are not conclusive.
- Preserve guardrails: no production/main changes or cutover without explicit approval; Greenhouse/Ashby/Instahyre and development notifications remain disabled; preserve `.venv/` untracked. User must pull updated branch docs before the next local command using `git pull --ff-only origin v2-live-radar`.


## 2026-10-13 — Read-only audit results received
- User-provided isolated dev API output: daily summary has 523 jobs discovered, 16 matches, 0 alertable, and 0 alerts sent. Naukri is enabled and its latest reported poll saw 357 jobs, added 2, and had no reported error; LinkedIn, Instahyre, and Greenhouse are disabled. Treat these as supplied evidence, not independently executed observations.
- Some returned Naukri rows are marked matches, but visible matching rows are non-alertable because Telegram notifications are disabled. Do not enable notifications to test this.
- In the sampled rows, `source_posted_at` is consistently `2026-10-13T00:00:00+00:00`, while `discovered_at` has finer precision. Whether this is normal date-only source precision or an adapter normalization issue remains unknown; inspect more rows and source parsing before deciding.
- Code inspection on branch shows `/api/jobs` caps limit at 500 and reads persisted evaluation/notification-ledger fields without recomputing matches; `/api/opportunities` caps at 500 and returns canonical opportunity observation counts and distinct source counts. Next diagnostic after pulling docs: read-only Python 3 query both endpoints with `today_only=true&limit=500`; print aggregates for match/alert/source/timestamp distribution and opportunity observation/source-count distribution, never canonical URLs.
- Since only Naukri is enabled in the supplied status, current runtime data cannot by itself prove cross-source dedupe. Do not infer success solely from aggregate canonical opportunities. No app/config/database/notification/service change was made.
- Keep Greenhouse/Ashby/Instahyre and development notifications disabled, preserve `.venv/` untracked, and make no production/main changes or cutover without explicit approval. User must pull updated docs before the next local command.


## 2026-10-13 — Expanded job/canonical audit reviewed
- User-provided read-only API aggregation: 500 jobs returned, all Naukri; 484 not matched and 16 matched; all 500 not alertable; ledger status 484 `suppressed`, 16 `pending`. These states do not show that alerts were sent. Need inspect persisted alertability/notification decision reasons for matched pending records before concluding why they remain pending.
- First 500 canonical opportunities all have `source_count=1` and `observation_count=1`. Only Naukri is enabled in the supplied runtime status, so cross-source dedupe remains unproven; these counts do not establish a defect.
- Source code review confirms Naukri adapter parses relay `posted` and labels it `posted_precision="date"` when present (otherwise unknown); discovery time uses relay `updated_at`. Midnight UTC posted values are consistent with date-only precision, not sufficient proof of fabricated times or broken freshness.
- Next safe action after pulling docs: aggregate read-only `/api/jobs?today_only=true&limit=500` fields `posted_precision`, `alertability_reasons`, `notification_decision_reasons`, `notification_status`, especially among matched rows. Do not print URLs, re-run matcher, mutate DB, enable sources, send notifications, or restart services.
- Guardrails unchanged: keep Greenhouse/Ashby/Instahyre and dev notifications disabled; preserve `.venv/` untracked; no production/main changes or cutover without explicit approval. Pull branch docs before the next local command.


## 2026-10-13 — Alertability and posting precision diagnostic
- User-provided read-only diagnostic on today's first 500 rows: `posted_precision` is `date` for all 500; exact posting-time freshness cannot be inferred from these records. Midnight UTC is consistent with date-only precision.
- Alertability reasons: 484 `not a profile match`, 16 `Telegram notifications disabled`. Notification decision reasons: 484 `no profile-matching observation`, 16 `Telegram notifications disabled; awaiting future re-evaluation`. The 16 matched records are pending as expected while Telegram is disabled; no sent alerts are indicated.
- Next diagnostic should print a privacy-safe summary of the 16 matched jobs only: title, company, location, score/reasons, experience fields, discovered_at, posted_precision, alertability and notification reasons. Exclude URLs and full descriptions. No matcher/config/DB/notification changes.
- Guardrails unchanged: keep Greenhouse/Ashby/Instahyre and development notifications disabled; preserve `.venv/` untracked; no production/main changes or cutover without explicit approval. Pull branch docs before next local command.


## 2026-10-13 — Matched-job quality review
- User-provided matched-job output contains 16 matches scoring 70–100; each is pending/non-alertable because Telegram is disabled. All 500 audited rows had date-only posting precision, so exact posting-time freshness remains unknown.
- Four distinct rows share `Accenture / Custom Software Engineer / Bengaluru, India` with scores 70, 76, 76, 82 and differing discovery timestamps. Could be distinct roles or duplicate listings; IDs/canonical grouping are required before calling this a dedupe defect.
- API response shows experience fields `experience_min`, `experience_max`, `experience_text` null while match reasons mention a 2-year candidate and compatible ranges. Investigate field mapping/projection read-only.
- Next safe command: group rows by normalized company/title/location and print stable source IDs, canonical opportunity IDs, canonical match method/confidence, scores/reasons and experience fields only. Exclude URLs and full descriptions. No code/config/DB/notification changes absent evidence and approval.
- Guardrails unchanged: keep Greenhouse/Ashby/Instahyre and development notifications disabled; preserve `.venv/` untracked; no production/main changes or cutover without explicit approval. Pull docs before next local command.


## 2026-10-13 — Repeated identity audit
- User-provided read-only audit grouped 500 today's job rows by company/title/location and found 15 repeated groups. The largest was Accenture / Custom Software Engineer / Bengaluru (172 rows). Across the 206 rows in the reported groups, all source job IDs and canonical opportunity IDs were unique; all displayed canonical match methods were `new`, confidence 0. This suggests possible repeated Naukri query-variant ingestion or canonical identity keys that are too strict, but is not yet proof that each row is the same vacancy.
- Experience fields `experience_min`, `experience_max`, and `experience_text` are null in the returned API rows even though matcher reasons cite specific experience requirements. The API projection/schema versus matcher inputs needs read-only inspection.
- No code/config/database/runtime/notification/CI/deployment/main/production changes. Experimental sources and dev notifications remain disabled; preserve `.venv/` untracked.
- Next: after pulling docs, inspect existing source adapter, canonicalization inputs and API/schema projection, then run a privacy-safe read-only diagnostic to establish whether repeated rows share stable upstream requisition identity. Do not change matcher or dedupe logic until confirmed.
- User must run `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar` before the next local command. Every subsequent turn must update both handover docs sequentially and verify.


## 2026-10-13 — Source inspection fallback
- User pulled latest docs successfully, but source inspection stopped because `rg` is not installed. No source inspection or app changes occurred.
- Next: use standard `grep -n -E -C 3` to inspect canonical identity/dedupe and experience extraction/matching in `v2/radar.py`; then review evidence before any fix. No DB writes, polling, notification/source changes, restarts, or production/main changes.
- Pull docs before the next local command: `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`.


## 2026-10-13 — Canonical and experience inspection findings
- Grep output confirms canonical matching is implemented in `v2/dedupe.py`, imported by `v2/radar.py`. Existing linked jobs return their current canonical ID; unlinked jobs are candidate-scored and linked only if `auto_link_allowed` passes. Inspect score thresholds and canonical identity inputs before fixing repeated same-title/company/location groups.
- Caution: `rebuild_canonical_opportunities` deletes `notification_ledger` rows while resetting canonical IDs. Do not run it as a diagnostic.
- Experience evaluation min/max values are stored in `job_evaluations` and mapped from API query aliases. Compatibility reasons alongside null fields remain unexplained; stale evaluations or persistence/mapping mismatch are hypotheses only.
- No app/runtime/database/notification changes. Next inspect `v2/dedupe.py` and full canonical opportunity helper / evaluation write and API projection using read-only grep/sed. Pull latest docs before the next local command: `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`.


## 2026-10-13 — Same-source dedupe restriction
- Confirmed from source: same-source candidate records are skipped when canonical URLs differ. Auto-link threshold is 95; exact canonical URL scores 100, metadata-description 93, metadata-probable 88. Thus metadata similarity cannot link same-source jobs with different URLs under the current loop. This plausibly explains repeated Naukri company/title/location groups, but duplicates versus genuinely distinct postings are not yet distinguished.
- Do not alter matching thresholds or merge/rebuild canonical groups until a privacy-safe sample establishes identity. `rebuild_canonical_opportunities` is especially risky because it deletes notification ledger rows.
- Experience fields may be null while the reason references candidate/configured-profile compatibility because the job's explicit range can be unknown; investigate matcher semantics before calling it a bug.
- Next: inspect full `v2/dedupe.py` and `match_details` around 1790–1895, then perform read-only identity audit. No app/runtime/database/notification/production changes. Pull latest docs before the next local command.


## 2026-10-13 — Full dedupe and experience semantics
- Confirmed same-source candidates with differing canonical URLs are skipped. Match score rules: URL exact=100; identical experience plus high title similarity=98 or 95; title plus description similarity can be 97/93; probable metadata=88; auto-link threshold >=95. Explicitly differing experience signatures block metadata linking.
- Next inspect candidate group selection and job-to-canonical data; perform a privacy-safe, read-only sample audit of repeated groups. Do not merge groups or rebuild canonical identities before proving vacancy identity.
- Experience reasons and min/max are generated in the same matcher result and persisted together. “Experience compatible” plus null min/max may indicate stale/inconsistent evaluation lifecycle, but not yet proven. Inspect evaluation timestamps/fingerprints and stored rows read-only.
- No application or runtime changes. Avoid canonical rebuild because it deletes notification ledger rows. Pull latest docs before next local command.


## 2026-10-13 follow-up: canonical candidate selection and evaluation lifecycle

### Evidence received
- The displayed excerpt of _candidate_canonical_groups() shows candidate selection using canonical URL when the incoming job has a normalized URL; the excerpt does not include the complete fallback/query logic.
- _assign_canonical() skips a candidate when it has the same source as the incoming job and a different canonical URL. Therefore same-source listings cannot be linked by metadata similarity alone in that branch. This is a confirmed code limitation and a plausible contributor to repeated Naukri company/title/location groups, but it does not prove those rows are the same real vacancy.
- _persist_job_evaluation() calculates match_details() and alertability_details(), then persists reasons and experience bounds in the same upsert. refresh_job_evaluations() re-evaluates only rows with no evaluation or a different config fingerprint. backfill_job_evaluations() fills only missing evaluations.
- A persisted match reason that states a specific experience range while the same evaluation row has null experience bounds needs record-level verification; do not assume API mapping is the root cause.
- Do not run rebuild_canonical_opportunities() as a diagnostic: the inspected implementation deletes notification-ledger rows while rebuilding canonical groups.

### Next read-only verification
1. Inspect the full _candidate_canonical_groups() implementation (around lines 527–575) to understand URL and metadata candidate selection.
2. Inspect representative persisted job/evaluation rows together: job ID, source, company/title/location, source URL host/path only (avoid printing full URLs), evaluation timestamp, config fingerprint, reasons JSON, and persisted experience bounds.
3. Compare each suspicious record's stored evaluation with a fresh in-memory match_details(job, config) result without persisting it. If the stored row and fresh result differ, investigate evaluation refresh/config lifecycle; if both are null but reasons claim a range, inspect parsing and the exact job payload.
4. No code fix or dedupe rebuild until candidate query semantics and real-vacancy evidence are understood. Keep Naukri/other canaries and notifications disabled as currently guarded.

### User-provided terminal evidence
The user supplied grep output from the dev checkout showing _persist_job_evaluation() upserts reasons_json, experience_min_years, and experience_max_years together; refresh_job_evaluations() compares config_fingerprint; and canonical assignment includes the same-source/different-URL skip described above. These are terminal excerpts, not independently executed tests by the assistant.


## 2026-10-13 follow-up: full candidate query and API evaluation fields

### Additional user-provided source excerpts
- _candidate_canonical_groups() first queries canonical_opportunities by exact normalized canonical URL and returns those rows if found. If none are found, it falls back to groups with matching company_norm and location_norm, ordered by last_seen_at descending, limited to 100.
- _assign_canonical() then skips any candidate whose representative source matches the incoming job source unless canonical URLs match. This means the company/location fallback does not enable same-source metadata matching when URLs differ. This strengthens the hypothesis that same-source query-variant Naukri results may form separate groups, but does not establish that every repeated listing is the same vacancy.
- /api/jobs selects persisted job_evaluations fields and maps evaluation_experience_min_years / evaluation_experience_max_years to the response. The handler explicitly documents that it returns the persisted matcher/ledger decisions rather than independently running the matcher at request time.
- The displayed matcher excerpt returns experience_min_years and experience_max_years alongside reasons. _persist_job_evaluation() upserts those values and reasons_json together. Thus a saved reason naming a specific range with null saved bounds warrants a record-level comparison between the stored evaluation and a fresh in-memory match_details() result.

### Next safe step
Use a read-only SQLite/Python diagnostic against the isolated dev database. For a small sample of suspicious job IDs, print only job ID, source, company/title/location, URL host/path (not query strings or full URLs), evaluation timestamp, fingerprint prefix, saved reasons, and saved experience bounds; then compute match_details() in memory using the same loaded config and compare results without calling _persist_job_evaluation(). Do not update evaluations, rebuild canonical groups, or alter the notification ledger during this diagnostic.


## 2026-10-13 follow-up: diagnostic command did not run

- User pulled the latest branch successfully, but the read-only diagnostic stopped immediately because Ubuntu has no `python` command (`python3` is available per the shell hint). The Python diagnostic itself did not execute, so no result was produced and no database mutation occurred.
- Next attempt should prefer the already-existing project interpreter at `.venv/bin/python` if executable; otherwise use `python3`. Do not install packages or change the environment solely to address the command alias. Preserve `.venv/` as untracked and never delete or commit it.


## 2026-10-13 follow-up: read-only SQLite diagnostic could not open DB

- User successfully ran the diagnostic with the existing project interpreter at /home/ubuntu/job-beeper-dev/.venv/bin/python.
- The app reports DB_PATH as /home/ubuntu/job-beeper-dev/v2/jobs.db, but sqlite3.connect(file:...jobs.db?mode=ro, uri=True) failed immediately with OperationalError: unable to open database file. No rows were read, the fresh matcher comparison did not run, and no database writes occurred.
- Next step is filesystem-only verification: check whether the DB path exists and is a regular file, inspect parent directory permissions and the configured DB_PATH source. Do not create the DB, change permissions, copy databases, or fall back to a different DB until the path/runtime setup is understood. Keep the next diagnostic read-only.


## 2026-10-13 follow-up: expected DB file absent from checkout

- User ran the filesystem diagnostic after pulling the latest branch. The repository checkout directory and v2/ directory are accessible, but `v2/jobs.db` does not exist in the checkout. Because the command used `&&`, `stat` and the DB_PATH grep did not run. The earlier import printed `radar.DB_PATH` as `/home/ubuntu/job-beeper-dev/v2/jobs.db`; SQLite's read-only open error is consistent with that file being absent, though the intended live DB may be elsewhere (for example, in a container-mounted path).
- Do not create a DB, change permissions, or point diagnostics at a guessed file. Next step: read the DB_PATH definition, search only the checkout for SQLite files, inspect running app/container process metadata, and check whether Docker is available. Avoid environment dumps or printing secrets. Only after locating the actual isolated dev DB should the read-only evaluation comparison be retried.


## 2026-10-13 follow-up: checkout DB absent; live process discovery

- User's latest read-only diagnostics show `v2/radar.py` defines `DB_PATH = Path(os.getenv("JOB_RADAR_DB", ROOT / "jobs.db"))`; no `.db`, `.sqlite`, or `.sqlite3` files were found within five levels of the checkout. Two Uvicorn processes run `/usr/local/bin/python3.12 /usr/local/bin/uvicorn v2.radar:app --host 0.0.0.0 --port 8000` (PIDs reported as 157883 and 165424). Docker API access returned permission denied for the current user.
- This supports the conclusion that the prior diagnostic targeted a missing checkout-relative database; it does not identify the live DB path or establish whether the service uses `JOB_RADAR_DB`. Next safe step is to inspect each process's `/proc/<pid>/cwd`, command line, and only the `JOB_RADAR_DB` environment entry, then request the local `/health` endpoint on port 8000. Do not dump full process environments, use sudo, alter permissions, restart services, create/copy a DB, or guess the database location.


## 2026-10-13 follow-up: live health confirms container DB path

- User's latest `/health` output from `http://127.0.0.1:8000/health` reports `status=ok`, `version=2.0.0`, and DB path `/data/jobs.db`. It reports Naukri last success `2026-10-13T17:46:27.677899+00:00`, 355 jobs seen, 0 new, no error; LinkedIn is not running and has a rate-limit cooldown. Treat these as user-provided runtime observations, not independently verified.
- Reading `/proc/<pid>/cwd` yielded no path, and process environments were not readable for the current user, so `JOB_RADAR_DB` remains unconfirmed. Do not access `/data/jobs.db` as a host path or assume it is available in the checkout. Docker socket access remains denied.
- Next safe step: inspect repository runtime manifests and `/api/jobs` route parameters to determine whether the intended isolated dev service exposes enough persisted evaluation data through its local API, and how the container volume maps to host storage. Keep reads bounded and redact job URLs/descriptions. Do not use sudo, restart, rebuild, create/copy databases, or write to the DB.


## 2026-10-13 follow-up: why DB-path investigation is part of matcher audit

- User asked whether locating the database is part of the process. Clarify that it is only a prerequisite to the active launch-gate investigation, not a separate product task: determine whether persisted job evaluation experience bounds/reasons match a fresh in-memory `match_details()` result, and investigate potentially irrelevant skill reasons without writing to the DB.
- User-provided source inspection confirms `GET /api/jobs` joins `jobs`, `job_evaluations`, and `notification_ledger`, then returns persisted evaluation decisions rather than re-running the matcher. The runtime manifests `v2/docker-compose.yml`, `v2/docker-compose.dev.yml`, and `v2/Dockerfile` all set `JOB_RADAR_DB=/data/jobs.db`. The live `/health` endpoint reports `/data/jobs.db`; checkout-relative `v2/jobs.db` is absent. Docker socket access is denied, so direct host-side DB inspection is not currently available.
- Next step should be narrowly focused: inspect the dev compose file and the read-only API output shape, then choose the least-invasive way to compare a few specific persisted evaluations against fresh in-memory matcher output in the same isolated dev runtime. Do not alter DB, restart/rebuild, use sudo, or expose full job URLs/descriptions. No diagnosis or fix has been established yet.


## 2026-10-13 follow-up: user prioritizes shipping experience parser fix

- User explicitly asks to move quickly and ship the experience-parser fix to production, preferring a minimal/smart path over extended investigation.
- Current evidence only establishes the runtime DB path and that `/api/jobs` returns persisted evaluations. It does not establish the exact code diff, whether the parser fix is committed/pushed, whether targeted tests pass, or whether production deployment is approved. Keep the path short: inspect `git status` and diff for parser/matcher/test files, run the narrow relevant tests, push only the verified fix to `v2-live-radar`, and report the exact commit. Do not deploy/cut over production without explicit approval; do not touch production DB or trigger historical notification replay. Note dev Compose uses port 8001 and a separate `radar-dev-data` volume; prior health response on port 8000 is not proof of the dev instance.


## 2026-10-13 follow-up: worktree check for experience parser release

- User's latest `git status --short --branch` shows `v2/config.json` modified and `.venv/` untracked; neither is an experience-parser code change. Preserve both, especially `.venv/`, and do not stage or commit config. `git diff -- v2/radar.py v2/test_radar.py` is empty.
- Existing `v2/test_radar.py` contains experience-related tests around lines 1754-2200, but this output alone does not prove the production fix is present or passed. The recent commit list is dominated by handover-document commits, so inspect `git log --oneline -- v2/radar.py v2/test_radar.py`, identify the test class names, and run targeted parser/matcher tests before deciding whether any code change is needed. Do not push docs-only commits as if they were the parser fix; no production deployment yet.


## 2026-10-13 follow-up: full test suite passed; verify exact parser fix

- User reports `python -m unittest v2.test_radar` completed successfully: 88 tests in 10.552s, `OK`. This is current branch test evidence, but does not alone prove the intended experience-parser fix is included.
- `git status --short --branch` showed only user-local `v2/config.json` modification and untracked `.venv/`; preserve both and never stage either. No diff for `v2/radar.py` or `v2/test_radar.py`. Recent code history includes commit `cd3a8a6` titled `Detect more skill-specific experience phrases for shadowing`, whose relevance to the user-requested production experience-parser fix must be checked before claiming readiness.
- Next fast path: inspect `git log --all --oneline --grep='experience\|parser'` and `git show --stat`/diff for `cd3a8a6`, then identify whether the exact matcher/parser fix and a regression test exist. Do not create a docs-only release commit or deploy production without verifying the intended code change. No production cutover or database changes.


## 2026-10-13: Production Gemini JD-experience parsing issue

- User clarifies the release goal: production still reports `experience not stated` when JD text contains an experience requirement, despite a Gemini-based JD parsing development they made; they want that development promoted to production.
- Commit `cd3a8a6` (`Detect more skill-specific experience phrases for shadowing`) only changes the regex used for skill-specific shadow extraction in `run_source`; it does not alone demonstrate that Gemini extraction feeds the persisted matcher fields in production.
- Full current test run reported by user: `python -m unittest v2.test_radar` — 88 tests, 10.552s, `OK`. Still must establish that these tests cover the Gemini path and its persistence into `experience_min_years` / `experience_max_years` and saved evaluation records.
- Next action: inspect local history and current implementation for Gemini JD experience extraction, its invocation, persistence, and config gating. Preserve local `v2/config.json` modification and untracked `.venv/`; do not stage either. Keep Telegram disabled in dev and do not replay historical alerts. User explicitly wants production promotion, but deploy only after identifying the actual code path and passing targeted regression checks; verify the production image/commit and health after rollout, without altering the production DB.


## 2026-10-13: Root cause narrowed to shadow-only Gemini path

- User's current code search shows `v2/radar.py` imports `shadow_extract_jobs, shadow_status` from `v2.gemini_extractor`; normal `match_details` at approximately lines 1808–1813 uses `jd_experience_min_years`/`jd_experience_max_years`, then regex extraction. The Gemini call is around lines 2664–2715 in the source-ingestion path and is explicitly described as shadow-only.
- This explains why Gemini shadow output can exist without populating the normal matcher’s persisted `experience_min_years`/`experience_max_years` fields; must inspect `v2/gemini_extractor.py` output schema, validation, and cache/persistence before implementing the smallest safe promotion.
- Current branch test run reported by user: 88 tests pass. Worktree has modified `v2/config.json` and untracked `.venv/`; preserve both and never stage them. No parser code diff in worktree. Do not deploy until the validated Gemini result is wired into matching and targeted regression tests pass. Keep historical alert replay disabled and do not alter production DB.


## 2026-10-13: Latest VM output confirms Gemini remains shadow-only; check branch promotion

- User's uploaded command output confirms `run_source` labels Gemini deliberately shadow-only and calls `shadow_extract_jobs` before `upsert_jobs`/`refresh_job_evaluations`; normal `match_details` reads `jd_experience_min_years` / `jd_experience_max_years` and regexes only. Thus shadow extraction does not populate the production matcher path in the shown code.
- The `--all` history also shows `58fdff1` on `origin/main` merging PR #36 and `9b9cbf1` `Fix LinkedIn labeled experience extraction before alert decisions`; do not assume those commits are in `v2-live-radar`. Next inspect `v2/gemini_extractor.py` validation/result/cache and check whether `58fdff1` is an ancestor of current HEAD before deciding the minimal promotion.
- User's full suite report remains 88 tests passing. Worktree still has modified `v2/config.json` and untracked `.venv/`; preserve them. No staging/reset/deletion, no production DB mutation, and no replay of historical notifications. Before production rollout, ensure the intended Gemini result is validated, integrated into matcher inputs, covered by regression tests, and deployed from the correct branch/commit.


## 2026-10-13: Gemini experience parsing diagnosis
- Current VM output confirms Gemini extraction is shadow-only. `shadow_extract_jobs()` validates/caches a result but deliberately does not change `jobs`; normal `match_details()` continues to use deterministic JD regex parsing and may report `experience not stated` when that parser misses an explicit range.
- `git merge-base --is-ancestor 58fdff1 HEAD` returned 1, so `v2-live-radar` does not contain the `main` merge that includes LinkedIn labeled experience fix `9b9cbf1`. Avoid wholesale merging `main`.
- Follow-up: inspect `run_source` order and evaluation fields, then implement/test the smallest safe Gemini-to-matcher integration before `refresh_job_evaluations` and notification decisions. Only use validated evidence-backed total-professional experience; retain deterministic fallback for Gemini failures, low confidence, and unclear scope. Keep dev notifications off; no historical replay.
- Status is diagnosis only; no parser implementation or production release has occurred. Protect local `v2/config.json` and untracked `.venv/`. Production cutover still needs regression tests and explicit approval.


## 2026-10-13: Gemini matcher integration points confirmed
- Normal matching uses `jd_experience_min_years`/`jd_experience_max_years` followed by regex parsing; it never consults `gemini_shadow_cache`.
- `run_source()` calls shadow extraction before upsert/evaluation/notification refresh, but shadow extraction currently only persists cache results and does not annotate job dictionaries.
- Before hard-matcher integration, inspect `v2/test_gemini_extractor.py` and cache samples. Treat only validated, exact-evidence, required total-professional experience at an explicit confidence threshold as an overall experience requirement. Do not hard-reject on preferred or skill-specific years.
- Preserve local `v2/config.json` and untracked `.venv/`; no parser code has been changed or deployed.


## 2026-10-13: Gemini matcher bridge committed; validation pending
- `cached_matcher_experience(job, conn)` now reads only a fresh cache entry matching the current JD hash and configured model, revalidates it, and accepts only required total-professional experience with exact evidence and confidence >= 0.85.
- `_job_for_canonical()` attaches trusted values to the in-memory job dict before the normal matcher runs. Existing regex parsing remains fallback; matcher does not make Gemini network calls.
- Three regression tests added for accepted values, unsafe-result rejection, and the persisted job loading bridge. Not yet executed on the VM; run targeted Gemini tests and then full suite.
- Commits: `1b667e4`, `c3cc276`, `ce69cec`. No production deployment has occurred. Preserve local `v2/config.json` and `.venv/`; no historical notification replay.


## 2026-10-13: Gemini matcher rollout gate
- `GEMINI_MATCHER_ENABLED` must be explicitly set to `1`, `true`, or `yes` before validated Gemini cache results can affect matching. Default off means code deployment alone will not change matcher outcomes or alerts.
- Integration tests set the gate on for test cases. Latest code/test commits `14516a0` / `0b74444`; run tests in VM before release. No production environment was changed.


## 2026-10-13: Gemini matcher tests passed
- User reports 11/11 `v2.test_gemini_extractor` tests passed and 88/88 `v2.test_radar` tests passed.
- Matcher integration remains gated by `GEMINI_MATCHER_ENABLED`, default off. Passing tests do not equal production deployment.
- Next release checks: identify actual production target and deployment mechanism; verify Gemini extraction enablement/auth and cache quality; back up and confirm persistent production DB; preserve notification ledger and avoid historical replay. Deploy with matcher gate off, verify health/cache, then enable only as an explicit controlled step. Protect local `v2/config.json` and `.venv/`.


### Gemini matcher validation update — 2026-10-14
- Validation on the development VM passed: 11 Gemini extractor integration tests and all 88 Radar tests.
- Test success is not production validation. The matcher rollout flag remains default-off, and no production environment change, DB mutation, or deployment has been performed.
- Next step: inspect development environment flag/model settings and verify fresh, matching-model Gemini cache entries before deciding whether to request a controlled production rollout.


## 2026-10-14 — Gemini matcher tests pass; runtime config remains unverified
- User-provided VM output: v2.test_gemini_extractor passed 11/11 and v2.test_radar passed 88/88.
- Latest VM rollout check: matcher/extraction/model env vars were unset and no Gemini API key was detected by that check; no SQLite DB file was found in the checkout search. This does not establish the running container's effective env or volume path.
- GEMINI_MATCHER_ENABLED defaults off. No production deployment/config change, DB mutation, or notification replay occurred.
- Next: inspect dev Compose/env wiring and secure secret source without printing values; verify fresh Gemini cache rows for the configured model while notifications remain disabled. Preserve local v2/config.json and untracked .venv/. No production enablement without explicit user approval and DB/ledger/cache checks.
- Every turn: update both handover docs. Provide user-run commands and wait for output; make safe GitHub code/doc changes directly as needed. Do not claim unobserved runtime success or deploy production without explicit approval.


## 2026-10-14 — Gemini development-runtime configuration gate

- **No application-code change.** Added the previously missing `GEMINI_MATCHER_ENABLED` variable to the dev Compose environment map with default `false` (commit `7ea83e024f2da4923633c23221ea8085a3643a10`). No production settings changed.
- Prior reported tests remain 11/11 `v2.test_gemini_extractor` and 88/88 `v2.test_radar`; no tests were rerun for the Compose-only change. CI status for the new commit remains unverified.
- The previous shell check did not detect a Gemini key; actual container environment and the mounted database are still unverified. Do not inspect or mutate an assumed checkout-relative SQLite path. Verify the live `/data` mount using the detailed handover's filtered container-inspection command.
- Next: fetch/pull the dev branch with `git pull --ff-only origin v2-live-radar`, checking that the local `v2/config.json` modification and `.venv/` remain untouched; run the handover's sanitized container/API checks; then report the terminal output. Do not start/recreate the container or enable extraction until that baseline is understood.
- Once runtime wiring/key status is known, use the ignored VM-local `.env` or exported environment to set only the required dev variables, keeping Telegram empty and LinkedIn disabled. Verify bounded Gemini calls, fresh/model-aligned validated cache entries, and persisted evaluation via read-only DB/API checks. No production matcher enablement, deployment, DB mutation, or historical alert replay without explicit approval.

### Continuation prompt

Continue only the Gemini required-experience pipeline in `AvinashBhalla/job-beeper` on `v2-live-radar`. Read both handovers plus `docs/JOBBEEPER_REFERENCE.md`. First run the detailed handover's sanitized dev-runtime commands and wait for the actual terminal output. Preserve local `v2/config.json` and `.venv/`; never use `sudo`, print secrets, alter production, or replay alerts. Keep extraction/matcher defaults false and Telegram disabled while verifying configuration and the actual `/data` volume. After any change, run the targeted Gemini tests and full Radar suite, report only results actually observed, and update both handover documents before ending the turn.


## 2026-10-14 — Reference synchronized with matcher gate

- Updated `docs/JOBBEEPER_REFERENCE.md` in commit `6828153f485e5e247e984a2a735f813ff6ef1d84` (initial content commit `8b71918468e41084f363cc1eb4a5250757e85b74`) to reflect the current architecture: extraction writes validated cache entries; the normal matcher may read only fresh, exact-JD/model-matched, evidence-backed total-professional requirements when the explicit matcher gate is enabled.
- The authoritative chronological handover's latest follow-up is commit `7a430b1c4b771dcc09eb9902d9d5ebd63ff7ff4d` (cache-precheck caution; prior update `71e2b4e27904e88eaf44da34914b0ceeee7420d8`, initial entry `85315e98009d069c301bbcec28b1b90a98f98d90`). No application code or production settings changed. No tests or live runtime checks were run this turn; the combined-status lookup returned no status records, so CI cannot be claimed.
- Next action: run the safe commands in the latest 2026-10-14 section of `docs/JOB_RADAR_HANDOVER.md`; return only sanitized output. Keep extraction/matcher false and notifications disabled until actual container environment, API status and the `/data` volume are confirmed. Preserve the local `v2/config.json` modification and untracked `.venv/`; no `sudo`, no secrets in chat, no DB writes or historical alert replay.

## 2026-10-14 — Live API confirms Gemini disabled; Docker socket blocks runtime inspection

- API evidence received from the user: extraction disabled; API key not configured in the service responding on 127.0.0.1:8001; model gemini-3.5-flash-lite; zero calls today; 14 successful cache entries and 6 errors. Some of 10 recent cached results match a preliminary shape, but not necessarily the current JD hash or persisted matcher path.
- Docker metadata/exec attempts are blocked by permission denied on /var/run/docker.sock. The environment inspection command itself was malformed; no container variable values were recovered. Compose syntax validation did succeed. No Docker permissions were changed, no sudo used.
- No application-code change and no tests run. No container lifecycle action, DB mutation, production change or notification replay.
- The current handover now has a host-side Compose interpolation check and safe Docker socket/group diagnostic command. Run it and return output. This can establish what a new container would receive without exposing the key, but cannot stand in for inspection of the running container.
- Only after Docker access is available to an already-authorized account/session, verify the actual dev volume mount. If credentials are absent, use the ignored local `.env` and hidden prompt; keep extraction/matcher false while recreating the isolated dev service. Then test extraction/cache/evaluation. No production rollout without explicit approval.

### Continuation prompt

Continue the Job Radar Gemini experience issue on `v2-live-radar`. Read both handovers and `docs/JOBBEEPER_REFERENCE.md`. The live API endpoint on port 8001 reports extraction disabled, no key configured, model gemini-3.5-flash-lite, 0 calls today, 14 successful and 6 error cache records, but Docker socket access is denied; do not use sudo or change permissions. First run the final safe diagnostic command in `docs/JOB_RADAR_HANDOVER.md` and inspect host-side Compose interpolation only without printing secrets. Preserve local `v2/config.json` and `.venv/`. Once Docker access is available, verify actual volume, securely configure key only if absent, keep Telegram disabled and LinkedIn off, run targeted Gemini tests and full Radar tests after code changes, confirm fresh cache reaches persisted evaluation, and update both handovers before the turn ends. Never enable production matcher or replay historical notifications without explicit approval.
## 2026-10-14 — Host config confirms missing Gemini key; Docker group not assigned

- Latest user output: `id` does not include `docker`; socket metadata `root:docker`, mode `660`; Docker daemon commands denied. Do not use sudo or change account/group/socket permissions.
- Compose-resolved configuration (which does not require Docker daemon access) confirms no Gemini key, both Gemini flags false, default model `gemini-3.5-flash-lite`, and empty Telegram credentials. Live API continues to report extraction disabled, no key, zero calls today, 14 successes and 6 errors.
- Actual running container environment, service identity and `/data` volume mapping remain unverified. Recent cache structural screens are not enough to prove that current job evaluations use those rows.
- No code changes, tests, Docker lifecycle commands, DB changes, production rollout or historical notification replay occurred. Existing user-local configuration and `.venv/` must remain untouched.
- If a key is available, store it using the hidden-input command in the detailed handover's newest section; the ignored VM-local `.env` preserves unrelated values and leaves both Gemini gates off. Do not paste the key into chat. Then ask an already-authorized VM account/administrator to inspect the dev mount and running env; the current `ubuntu` account cannot do that through Docker.

### Continuation prompt

Continue the Job Radar Gemini JD-experience issue on `v2-live-radar`. Read both handovers and `docs/JOBBEEPER_REFERENCE.md`. Latest host Compose status: API key absent, both Gemini flags false, model `gemini-3.5-flash-lite`, Telegram credentials empty. Live API on port 8001 reports extraction false, key absent, zero calls today, 14 cache successes and 6 errors. `ubuntu` is not in Docker group; socket is `root:docker` mode 660; do not use sudo or change permissions. If a key is available, save it through the hidden-input ignored `.env` command in the handover, preserving unrelated entries and keeping both flags false. Do not recreate the service until an authorized Docker session/account can verify the actual `/data` mount and running container environment. Preserve local `v2/config.json` and `.venv/`; don't deploy production or replay notifications without explicit approval. Once runtime access is available, verify fresh cache values reach persisted evaluation, run relevant tests after any code changes, and update both handovers each turn.
## 2026-10-14 — Local Gemini key saved; Compose verification pending

- User reports that the hidden-input `.env` setup completed with `dev_gemini_key_saved=true`, `gemini_extraction_enabled=false`, `gemini_matcher_enabled=false`. The API key did not appear in chat. This records local write success only; Compose resolution and running-container delivery are still unverified.
- Next run the final compact redacted Compose configuration check in `docs/JOB_RADAR_HANDOVER.md`, expecting key-configured true, extraction/matcher false and Telegram credentials empty. Do not reveal any secret. Compose config does not require Docker daemon access.
- Docker remains blocked for the current `ubuntu` account: the account's groups omit `docker`, and the socket is `root:docker` mode 660. Do not use sudo or modify permissions/groups. Have an already-authorized session/account or VM administrator verify the real dev container environment and `/data` volume before any restart/recreate.
- No application-code change, test run, container lifecycle action, DB mutation, production deployment or notification replay. Keep local `v2/config.json` and `.venv/` intact. Production matcher remains disabled absent explicit approval.

### Continuation prompt

Continue the Job Radar Gemini experience issue on `v2-live-radar`. User saved the Gemini API key through a hidden-input ignored `.env` script and reported `dev_gemini_key_saved=true`; both `GEMINI_EXTRACTION_ENABLED` and `GEMINI_MATCHER_ENABLED` are still false. First run the latest redacted Compose config verification in the detailed handover and confirm key-configured true without printing its value. Docker access is still blocked for `ubuntu` because they are not in the `docker` group and socket is `root:docker` mode 660; do not use sudo or change permissions. An authorized Docker session/account or VM administrator must verify the running container and actual `/data` volume before recreation. Preserve modified `v2/config.json` and untracked `.venv/`, keep Telegram disabled, do not deploy production or replay alerts, and update both handovers at the end of each turn.
## 2026-10-14 — Explicit env-file resolves Gemini key; default discovery does not

- User output confirms `.env` exists, is ignored by Git, and has one non-empty key line. Default Compose interpolation reports key absent; explicit `--env-file .env` reports key configured. Both extraction/matcher flags remain false; Telegram credentials are empty.
- Root README dev commands updated in commit `f3df8d6330797a582b7e0a50f117c84a2482899a` to pass `--env-file .env` explicitly and require actual dev-volume verification before service recreation.
- The current `ubuntu` account cannot access Docker: not in group `docker`, socket is `root:docker` mode `660`. Do not use sudo or alter socket/group permissions. Use an already-authorized Docker session/account or VM administrator for the filtered read-only mount/container inspection in the detailed handover.
- Do not restart/recreate until actual dev container identity and `/data` volume are confirmed. Once confirmed by an authorized operator, recreate only dev with both Gemini gates false; verify effective env/mount before enabling extraction. No code change, tests, DB mutation, production rollout or historical replay occurred this turn. Preserve local `v2/config.json` and `.venv/`.

### Continuation prompt

Continue only the Job Radar Gemini experience issue on `v2-live-radar`. User evidence: `.env` exists, is ignored and has one non-empty API key line; default Compose discovery reports key absent while explicit `docker compose --env-file .env ... config` reports configured. Both Gemini gates false and Telegram credentials empty. README dev commands now require `--env-file .env` (commit `f3df8d6330797a582b7e0a50f117c84a2482899a`). Current ubuntu account lacks Docker access (not in group; socket root:docker 660); don't use sudo or change permissions. Before any recreate, have an already-authorized Docker session/account or VM administrator verify the existing dev container and actual `/data` volume with filtered read-only inspection. Then keep both gates off while recreating dev, verify env/mount, enable bounded extraction only after checks pass, and prove fresh cache reaches persisted evaluation. Preserve local `v2/config.json` and `.venv/`, no production rollout/replay without explicit approval, and update both handovers each turn.
## 2026-10-14 — Docker volume query denied again

- User ran the read-only volume listing and received `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock` twice. This means volume existence is still unknown, not absent. The shell prompt was `ubuntu@job-radar:~$`; socket access is the issue.
- Prior account metadata showed ubuntu is not in group `docker`; socket is owned by `root:docker` with mode `660`. Do not use sudo or change socket/group permissions. The next step requires an already-authorized Docker session/account or a VM administrator to execute filtered read-only container/mount/volume inspection.
- Explicit `--env-file .env` is the verified fix for Compose interpolation: it sees the locally stored Gemini key, while default dotenv discovery does not. Keep `GEMINI_EXTRACTION_ENABLED=false`, `GEMINI_MATCHER_ENABLED=false`, Telegram empty and notifications disabled until the actual dev volume and container environment are verified.
- No code change, test run, container/database modification, production deployment/config change or notification replay this turn. Preserve local `v2/config.json` and `.venv/`.

### Continuation prompt

Continue Job Radar Gemini matcher validation on `v2-live-radar`. Explicit `docker compose --env-file .env ... config` resolves the API key; both Gemini gates remain false and Telegram is empty. The current ubuntu user has repeatedly been denied Docker API access, and prior `id` output omits group `docker` while socket ownership/mode is `root:docker 660`. A read-only `docker volume ls` attempt returned permission denied, so the dev volume's existence is unknown. Do not use sudo, change permissions/groups, create a new volume or recreate the service. Get an already-authorized Docker account/session or VM administrator to run the filtered read-only `docker ps -a`, `docker inspect` and volume listing. Verify the actual `/data` mount before any recreation. Preserve modified `v2/config.json` and `.venv/`, don't touch production or replay notifications, and update both handovers after each prompt.

## 2026-10-14 — Repeated Docker API denial; administrator action required

- User retried the read-only `docker volume ls` command and again received permission denied on `/var/run/docker.sock`. No new runtime evidence; volume existence remains unknown.
- Do not repeat Docker commands from the unauthorized current account or recommend `sudo`/permission changes. Existing evidence: ubuntu is not in the `docker` group; socket is `root:docker` mode 660.
- The only safe next step is for an already-authorized Docker session/account or VM administrator to run the filtered read-only container/volume inspection in the detailed handover and verify the actual `/data` mount. Do not create/recreate containers or volumes before that evidence.
- No code change, tests, Docker lifecycle action, DB mutation, production rollout, or notification replay. API key remains in ignored local `.env`; use explicit `--env-file .env`; extraction and matcher gates remain false, Telegram empty. Preserve `v2/config.json` and `.venv/`.

### Continuation prompt

Continue the Gemini experience matcher issue on `v2-live-radar`. User has retried `docker volume ls` from their ubuntu account and again received permission denied on `/var/run/docker.sock`; do not ask them to repeat it from that account. They are not in group `docker`, and the socket is `root:docker` mode 660. Do not use sudo or change permissions/groups. Ask them to have an already-authorized Docker account/session or VM administrator run the previously documented filtered read-only `docker ps -a`, `docker inspect` and `docker volume ls` commands, returning the dev container identity and `/data` mount. Until then the volume remains unknown; don't recreate anything. The API key is stored in ignored `.env`, explicit `--env-file .env` resolves it, both Gemini gates are false and Telegram is empty. No production changes, DB writes, or alert replay. Preserve local config and `.venv/`; update both handovers every turn.
## 2026-10-14 — Same Docker socket denial repeated again

- User re-ran the filtered read-only Docker volume listing from `ubuntu@job-radar:~`; permission denied on `/var/run/docker.sock` was printed three times. Do not treat this as evidence that the volume exists or is absent.
- Avoid asking for another retry from this same unauthorized account. Existing evidence: account is not in `docker` group; socket owner/group `root:docker`, mode `660`. No sudo, chmod, group edits, or other permission workaround.
- Progress is blocked pending output from an already-authorized Docker account/session or VM administrator using the read-only `docker ps -a`, `docker inspect`, and `docker volume ls` commands from the detailed handover. Need identify the current dev service and `/data` mount before any recreate; until then make no container/volume lifecycle changes and don't touch SQLite.
- No code/test changes, database writes, production changes, or notification replay. Preserve local `v2/config.json` and `.venv/`. `.env` remains ignored/local, explicit `--env-file .env` resolves its interpolation, both Gemini gates false and Telegram empty.

### Continuation prompt

Continue the existing Job Radar V2 Gemini experience matcher task on `v2-live-radar`; do not restart from scratch. Before decisions read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`. User has repeatedly received permission denied from `docker volume ls` on `/var/run/docker.sock` using `ubuntu@job-radar:~`. Do not ask them to repeat from the same account or suggest sudo/socket/group changes. Need an already-authorized Docker session/account or VM administrator to run the filtered read-only `docker ps -a`, `docker inspect`, and `docker volume ls` commands and return actual container identity plus `/data` mount metadata. Until verified, do not create/recreate containers or volumes or inspect/mutate SQLite. Both Gemini flags remain false, Telegram credentials empty, `.env` ignored and requires explicit Compose `--env-file .env`; preserve local `v2/config.json` and `.venv/`. No production rollout or notification replay. Update both handover docs each turn, commit to `v2-live-radar`, and re-fetch/verify both.
## 2026-10-14 — User is OCI administrator; SSH connection path

- User says they administer the Oracle Cloud VM and have the private/secret key file plus its public-key file. Guide them to OCI Console → Compute → Instances → select `job-radar` → copy Public IP, then connect from Windows PowerShell with `ssh -i "$env:USERPROFILE\Downloads\<private-key-filename>.key" ubuntu@<PUBLIC_IP>` (substitute actual path/IP; `.pem` may be the private key extension). Do not request either key or allow it to be shared. The confirmed SSH username is `ubuntu` from the host prompt.
- An OCI API signing key is not an SSH private key; explain the distinction if file type is unclear. SSH timeout means check public IP/private-network access and narrow TCP/22 ingress; `Permission denied (publickey)` means check the correct key/user. If no public IP, use an appropriate authorized path such as OCI Bastion/private networking, not necessarily the serial console for general administration.
- SSH access to the Linux VM does not grant Docker socket access. `ubuntu` was not in group `docker`, socket is `root:docker` mode 660. Prior guardrail says no sudo, chmod/socket changes, or group changes. Stay read-only and do not recreate the container/volume. Docker inspection still requires a separately pre-authorized Docker account/session or explicit approval to choose a different access approach.
- Keep Gemini extraction/matcher gates false and Telegram empty. Preserve local `v2/config.json` and `.venv/`; no code/test/container/DB/production changes or notification replay.

### Continuation prompt

Continue the current Job Radar V2 Gemini experience matcher issue on branch `v2-live-radar`; read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` before decisions. User is the OCI VM administrator and has a private/secret SSH key and its `.pub` file. Help them connect from Windows PowerShell: in OCI Compute → Instances → `job-radar`, copy the Public IP, then use `ssh -i "$env:USERPROFILE\Downloads\<private-key-filename>.key" ubuntu@<PUBLIC_IP>` with real values substituted. Never request/share keys; distinguish an OCI API signing key from an SSH private key. SSH success will not solve Docker socket access: ubuntu is not in group docker and socket is root:docker 660. Existing guardrails prohibit sudo or permission/group changes. Keep Docker work read-only, require authorized access, verify `/data` mount before recreation, and do not mutate DB/production or replay notifications. Preserve `v2/config.json` and `.venv/`. Both Gemini gates false; Telegram empty; `.env` ignored and Compose requires `--env-file .env`. Update and verify both handovers after each turn.
## 2026-10-14 — SSH is connected; do not bypass Docker guardrail without approval

- User says SSH login to the Oracle VM succeeded and asks for next steps. SSH access alone does not change Docker API permissions: prior `id` showed no `docker` group and socket is `root:docker` 660.
- Existing user-established project rule explicitly forbids sudo, Docker socket permission changes, and docker-group changes. Do not re-run the same volume query or suggest privileged commands until the user explicitly changes/overrides the restriction. If asked what next, explain that we need to decide whether they authorize `sudo` solely for read-only Docker inspection (`docker ps -a`, `docker inspect`, `docker volume ls`) while still prohibiting all lifecycle operations and DB reads/writes, or continue without sudo using an existing authorized Docker session. Admin/SSH status alone is not explicit approval.
- No code/tests/runtime/database/production/notification action. Preserve `v2/config.json` and `.venv/`; Gemini gates remain false; Telegram credentials empty.

### Continuation prompt

Continue the existing Job Radar V2 Gemini matcher task on `v2-live-radar`. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` before decisions. User now says SSH to the Oracle VM is connected. Do not repeat the Docker volume query; ubuntu lacks docker-group membership and `/var/run/docker.sock` is root:docker mode 660. A previous handover explicitly prohibits sudo or Docker permission/group changes, so explain that the current blocker remains and ask whether they explicitly authorize `sudo` for read-only Docker metadata commands only, with no container/volume operations and no database or production changes. Otherwise wait for existing authorized Docker access. Both Gemini flags false; Telegram empty; preserve local `v2/config.json` and `.venv/`. No production rollout or notification replay. Update and verify both handovers each turn.
## 2026-10-14 — Approved sudo for metadata inspection only

- User explicitly authorizes sudo solely for read-only Docker inspection. This supersedes the previous no-sudo rule only for commands reading container labels/status, mount metadata, and volume names. It does not authorize container/volume lifecycle operations, SQLite access/writes, production changes, or alert replay.
- Guide user in their connected SSH terminal: (1) `sudo docker ps -a --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'`; (2) `sudo docker volume ls --filter name=job-radar-dev_radar-dev-data --format 'volume={{.Name}}'`; (3) inspect the actual exact container name from command 1 using `sudo docker inspect <ACTUAL_CONTAINER_NAME_FROM_PS_OUTPUT> --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}'`. Replace the placeholder with the literal name and remove angle brackets.
- If sudo asks for a password, it goes into their own SSH terminal only. If sudo rejects authorization or inspect says there is no such object, collect only the non-secret error and do not bypass. An empty `ps` result means no matching container found; do not create one. No `docker compose up/down`, start/stop/recreate, volume creation/removal, `sqlite` commands or dumping environment values.
- After outputs arrive, determine whether the current container uses the intended isolated dev volume mounted at `/data`. Both Gemini gates remain false and Telegram empty. Preserve local `v2/config.json` and `.venv/`; no code/tests/DB/production/notification changes yet.

### Continuation prompt

Continue the existing Job Radar V2 Gemini experience matcher task on branch `v2-live-radar`. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` first. User is connected over SSH as ubuntu and explicitly approved `sudo` for read-only Docker metadata inspection only. Give these commands to run locally in SSH: `sudo docker ps -a --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'`; `sudo docker volume ls --filter name=job-radar-dev_radar-dev-data --format 'volume={{.Name}}'`; and, using the exact name found by `ps`, `sudo docker inspect <ACTUAL_CONTAINER_NAME_FROM_PS_OUTPUT> --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}'`. This only reads metadata; no lifecycle operations, database access, production changes, or notification replay are authorized. Don't create container/volume if empty; verify `/data` mount before proposing anything further. Preserve `v2/config.json` and `.venv/`; Gemini gates false and Telegram empty. Update both handovers and verify every turn.
## 2026-10-14 — Dev container and expected volume found

- User's read-only metadata results: `container=job-radar-dev status=Up 46 hours image=13b233998d70`; named volume listing returned `volume=job-radar-dev_radar-dev-data`. Therefore the container is running and the expected volume exists, but the actual container mount is not yet confirmed.
- The first `docker inspect` attempt used literal text `ACTUAL_CONTAINER_NAME` and yielded `error: no such object: ACTUAL_CONTAINER_NAME`. This is a placeholder substitution mistake, not evidence of a missing container.
- Run exactly: `sudo docker inspect job-radar-dev --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}'`. Confirm destination `/data` maps to the named dev volume before further decisions.
- Sudo is authorized for read-only Docker metadata only. No container/volume lifecycle operations, SQLite access, env dumping, production changes, or alert replay. Both Gemini gates false, Telegram credentials empty; preserve local `v2/config.json` and `.venv/`. No code/test/runtime changes this turn.

### Continuation prompt

Continue the existing Job Radar V2 Gemini experience matcher on `v2-live-radar`. Read all three handovers/reference docs before decisions. User authorized sudo for read-only Docker metadata. They have confirmed `container=job-radar-dev status=Up 46 hours image=13b233998d70` and `volume=job-radar-dev_radar-dev-data`. Their inspect attempt failed because they used literal placeholder `ACTUAL_CONTAINER_NAME`. Next ask them to run `sudo docker inspect job-radar-dev --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}'`. Need actual `/data` mount identity before anything else. Do not run Docker lifecycle commands, access/mutate DB, dump env, change production or replay notifications. Keep both Gemini gates false, Telegram empty; preserve `v2/config.json` and `.venv/`. Update and verify both docs every turn.
## 2026-10-14 — Expected development volume mount verified

- User's read-only `sudo docker inspect job-radar-dev` output: `project=job-radar-dev service=radar data_mount=type=volume name=job-radar-dev_radar-dev-data source=/var/lib/docker/volumes/job-radar-dev_radar-dev-data/_data destination=/data`. Existing dev container is Up 46 hours, expected volume exists, and exact mount is confirmed. This is not evidence that latest code or local `.env` key/gates reached the existing container.
- Next check only the whitelisted non-secret env fields, never print `.Config.Env` wholesale: `sudo docker inspect job-radar-dev --format '{{range .Config.Env}}{{if eq (index (split . "=") 0) "GEMINI_API_KEY"}}gemini_key={{if gt (len (index (split . "=") 1)) 0}}configured{{else}}empty{{end}} {{end}}{{if eq (index (split . "=") 0) "GEMINI_EXTRACTION_ENABLED"}}extraction={{index (split . "=") 1}} {{end}}{{if eq (index (split . "=") 0) "GEMINI_MATCHER_ENABLED"}}matcher={{index (split . "=") 1}} {{end}}{{if eq (index (split . "=") 0) "GEMINI_MODEL"}}model={{index (split . "=") 1}}{{end}}{{end}}'`. It emits only key presence status, two flags, and model, not the key itself.
- Sudo authorization is for read-only metadata inspection only. If environment state is stale/missing, get explicit approval before restarting or recreating the dev container; first check local branch/Compose env-file configuration and protect current DB. No volume lifecycle action, SQLite content, env dumps, production changes or alert replay. Keep both Gemini gates false until runtime validation and later explicit rollout approval. Preserve local `v2/config.json` and `.venv/`; Telegram blank, notifications off, LinkedIn disabled.

### Continuation prompt

Continue existing Job Radar V2 Gemini matcher task on `v2-live-radar`. Read handover, knowledge transfer and `docs/JOBBEEPER_REFERENCE.md` before decisions. User authorized sudo for read-only Docker inspection only. They confirmed running container `job-radar-dev` (`Up 46 hours`, image `13b233998d70`) and volume `job-radar-dev_radar-dev-data`; inspect confirmed project `job-radar-dev`, service `radar`, type volume, name `job-radar-dev_radar-dev-data`, source `/var/lib/docker/volumes/job-radar-dev_radar-dev-data/_data`, destination `/data`. Next run the filtered command in detailed handover to emit only Gemini API-key presence (never actual key), extraction flag, matcher flag, and model. Do not print `.Config.Env` wholesale. No lifecycle actions or DB access are authorized; if stale env/code means container replacement needed, request separate explicit permission and protect the existing DB. Both Gemini gates false until isolated runtime validation; Telegram blank, notifications off, LinkedIn disabled. Preserve `v2/config.json` and `.venv/`. No production rollout/notification replay. Update/verify both handovers every turn.
## 2026-10-14 — Running dev container lacks Gemini key environment

- Filtered `sudo docker inspect job-radar-dev` output from user: `model=gemini-3.5-flash-liteextraction=false gemini_key=empty`; there was no `matcher=` field. This means running container model is set, extraction flag false, API key empty, and matcher env var did not appear in `.Config.Env`. It does not prove the host `.env` is empty; prior diagnostic showed local ignored `.env` contained a key and `docker compose --env-file .env ... config` resolved it.
- Container `job-radar-dev` remains Up and `/data` mount to `job-radar-dev_radar-dev-data` is verified. Key/config changes made after container startup are not applied to the old container. Never print the key or entire container env.
- Read-only next step: `cd ~/job-beeper-dev && printf 'branch=' && git branch --show-current && printf 'head=' && git rev-parse --short HEAD && git status --short && docker compose --env-file .env -f v2/docker-compose.dev.yml config --quiet`. Ask user for output, including whether `config --quiet` succeeded. This confirms branch/config parse and preserves any reported `M v2/config.json` and `?? .venv/`; it doesn't alter the running service and should not reveal secret values.
- User authorized `sudo` for read-only Docker inspection only, not restarting/recreating services. If this validation succeeds, explain need/impact and request explicit approval before any Compose `up`/recreate. No database inspection/write, volume lifecycle change, production change, or notification replay. Gemini extraction/matcher flags remain false in the current container; preserve local files, Telegram blank and notifications off.

### Continuation prompt

Continue existing Job Radar V2 Gemini experience matcher issue on `v2-live-radar`. Read detailed handover, knowledge transfer, and `docs/JOBBEEPER_REFERENCE.md` before decisions. Confirmed dev container `job-radar-dev` is Up and mounts named volume `job-radar-dev_radar-dev-data` at `/data` (Compose project `job-radar-dev`, service `radar`). User's filtered current-container env report: `model=gemini-3.5-flash-liteextraction=false gemini_key=empty`, no `matcher=` printed. Local ignored `.env` was previously checked and had a nonempty API key line; explicit `docker compose --env-file .env` interpolation finds it. This older running container has not received the env. Next run read-only host checks: `cd ~/job-beeper-dev && printf 'branch=' && git branch --show-current && printf 'head=' && git rev-parse --short HEAD && git status --short && docker compose --env-file .env -f v2/docker-compose.dev.yml config --quiet`. Don't print key/full env. User only authorized sudo for read-only metadata inspection, so no restart/recreate until separate explicit approval. Preserve local `v2/config.json` and `.venv/`; keep Gemini gates false until validation and explicit approval; Telegram blank, LinkedIn disabled, notifications off, no production or DB changes. Update/re-fetch both handovers every turn.
## 2026-10-14 — Compose validation succeeded on VM checkout

- User reports from `~/job-beeper-dev`: branch `v2-live-radar`, HEAD `c40e5d7`, worktree `M v2/config.json` and `?? .venv/`; `docker compose --env-file .env -f v2/docker-compose.dev.yml config --quiet` passed (`compose_config=valid`). Preserve both local items and never stage/reset/clean them.
- GitHub compare from `c40e5d7` to current `v2-live-radar` shows ahead 25, behind 0; only changed files are `README.md` and the two handover docs. The application/compose source code is the same. Current container is up 46h but runtime environment has `gemini_key=empty`, `extraction=false`, model `gemini-3.5-flash-lite`, and the matcher env was absent. Host `.env` was previously verified non-empty, with `--env-file .env` required.
- Verified current dev mount: project `job-radar-dev`, service `radar`, volume `job-radar-dev_radar-dev-data` mounted to `/data`. The repository README says dev start/build command `docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build`; user only authorized sudo for read-only metadata so far. Do not execute build/recreate until user separately authorizes this lifecycle action. If approved, scope to the dev `radar` service, use explicit `.env` and same Compose project/volume; no `down`, volume operations, SQLite access, production service change or notification replay. Keep both Gemini flags false until later controlled validation/approval; Telegram blank, notifications off, LinkedIn disabled.
- Root `.dockerignore` and `v2/.dockerignore` are absent. Build context is the checkout root; Dockerfile copies only `v2/` and `dashboard/`, but an untracked local `.venv/` could still be sent in the context. Warn user before build approval, preserve the directory, and consider a `.dockerignore` change in a future code-reviewed step rather than silently deleting it. No code/tests/runtime/db/production changes this turn.

### Continuation prompt

Continue the existing Job Radar V2 Gemini experience matcher task on `v2-live-radar`. Read both handovers and `docs/JOBBEEPER_REFERENCE.md` before any decisions. User reported VM checkout at `~/job-beeper-dev`, branch `v2-live-radar`, HEAD `c40e5d7`, status `M v2/config.json`, `?? .venv/`, and Compose config `valid` with explicit `--env-file .env`. GitHub compare from c40e5d7 to current branch says +25/-0 commits, only README and handover docs changed; source/Compose code unchanged. Current running dev container lacks Gemini key and matcher env; local ignored `.env` has the key and must be passed explicitly. Database mount has been confirmed: project `job-radar-dev`, service `radar`, volume `job-radar-dev_radar-dev-data` at `/data`. User has authorized sudo for read-only Docker metadata only, so ask separate explicit approval before `docker compose ... up -d --build radar`. Build context is repo root with no `.dockerignore`; local `.venv/` may be sent as context, though Dockerfile copies only `v2/` and `dashboard/`. Don't delete or change `.venv/` or `v2/config.json`; optionally propose adding `.dockerignore` in a reviewed code change, not as a surprise. No `down`, volume commands, SQLite access, production changes or notification replay. Both Gemini gates false, Telegram empty, notifications off, LinkedIn disabled. Update/re-fetch both handovers every turn.