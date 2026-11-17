# Job Radar V2 — Knowledge Transfer

## CURRENT RELEASE STATE — 2026-11-17 15:15 UTC

**Canonical handover:** [Production readiness, delivery plan and next-agent handover](PRODUCTION_READINESS_AND_RELEASE_PLAN_2026-11-17.md).

- Existing V2 pipeline is the priority; Company Watch Phase 2 remains paused.
- Production is unchanged on job-radar-prod-canary:6e5becb, port 8000, health 200. Current V2 QA from 54fad21 runs separately on port 8013.
- Cleanup is complete: legacy QA runtimes and unused image tags removed after archiving old QA databases/configuration; only production and current QA containers remain. Production Docker volume is preserved.
- The daily production snapshot job has been repaired and a production DB snapshot passed SQLite integrity. Offsite encrypted backup/restore drill remains outstanding.
- Production contains admin only; no member account or linked member Telegram. Google sign-in is disabled and the bot webhook/per-user settings are not configured. Owner member email and Telegram bot access are required for the real canary.
- Naukri live relay was consumed in current V2 QA: 312 seen / 2 new first poll; 312 seen / 0 new on second poll. Notifications were disabled.
- Per-user tests: 61 passed. Full V2 suite: 497 passed, 0 failed.
- Workday adaptive 429 backoff is prepared in local branch fix/ats-board-rate-limit-backoff-20261117; full suite passes, but patch is not yet committed/pushed and production has not been updated.
- Fastest safe path: PR/CI → candidate QA rebuild → real member account/preferences → real Telegram webhook/link/canary → offsite backup/restore → explicit production approval and rollout → 24–72h monitoring.
- Current estimate to first production canary: 8–14 focused engineering hours, approximately 1–2 days if external access is available. See the canonical plan for assumptions and blockers.

Older timestamped checkpoints below are historical. Do not treat prior statements that Docker inventory was unavailable, that the snapshot service remained broken, or that four QA services were still running as current.

---

## Current release and cleanup status — 2026-11-17

**Read first:** [Repository cleanup, production readiness and VM health](REPOSITORY_CLEANUP_AND_VM_HEALTH_2026-11-17.md).

- Production Source Health screenshot: today 379 discovered / 26 matched / 25 alerted. Naukri, Greenhouse and Ashby operational; LinkedIn partial (6 HTTP 429 / 79 requests); Workday failing (285 HTTP 429 / 360 requests, 241/286 page/board failures). The 25 admin “alerted” count is the legacy/global Telegram ledger, not the newer per-user ledger.
- GitHub is clean: zero open PRs; only remote branches main and v2-live-radar. PR #71 merged into V2 as e3f1c9c after 496/496 CI tests passed. PR #73 merged into main as fced495f. PR #70 closed as stale docs. Keep main and V2 separate.
- VM-local cleanup: 20 clean worktrees removed after archiving 65 branch refs in /home/ubuntu/.archives/job-beeper-local-branches-2026-11-17.bundle (5.7 MB, verified). Four worktrees remain: dirty dev, dirty global-ATS QA, dirty source-observability QA, and active LinkedIn-backoff QA. No dirty config, DB, container, or active QA service was overwritten.
- VM is memory/I/O constrained (956 MiB RAM, about 2.0 GiB swap used, high memory/I/O pressure); disk is only 41% used. Recommend 4 GiB RAM, then retire obsolete QA containers after Docker inventory. Docker access is currently denied to the ubuntu user.
- Not release-ready for Company Watch production: PR #76 is merged in V2 but not deployed; manifest not imported to persistent DB; no Company Watch board has been verified/activated/polled. Follow the staged gates in the cleanup report before production.

---

## Live system health and end-to-end evidence — 2026-11-17 12:53 UTC

- Naukri upstream relay is scanning: five-minute systemd timer enabled; four consecutive workflow runs (#44083895797, #44084703987, #44085500607, #44086307997) completed all 18/18 targets with zero failed searches and 315 / 309 / 311 / 311 unique jobs. Latest feed timestamp 12:48:49 UTC; 311 jobs, 311 unique IDs/URLs and non-empty company/title/location/description.
- Actual V2 Naukri collector consumed the live feed in an isolated temp DB. Full run_source(naukri) smoke test twice: first 311 seen / 311 new; second 311 seen / 0 new. Temp DB had 311 jobs, 311 canonical opportunities, 311 global evaluations, two successful source_runs and integrity ok. Under repository default/global config, 15/311 matched and 296/311 did not; legacy decision ledger had 15 pending / 296 suppressed. Per-user tables had zero users/preferences/evaluations/Telegram chats/settings/per-user notification rows. Notifications and Telegram were disabled; this does not prove personal matching or delivery.
- Production app /health on port 8000 returns 200 (v2.0.0). Admin source-status and daily-summary returned 401 without an admin session. Docker access is denied to Termalin's ubuntu user. Shared dev 8001 resets; QA 8010, synthetic 8006 and feature QA 8002 health return 200. No container/log/production DB identity was inspected; no sudo workaround attempted.
- Production snapshot journal reports integrity ok and jobs row counts 25,641 (Nov 15), 26,067 (Nov 16), 27,024 (Nov 17). Snapshot service fails after the production snapshot when a subsequent target returns "cannot exec in a stopped state".
- Six-hour host metrics: CPU average 44% (peak 95.8%), memory average 72.9% (peak 85.5%), CPU steal average 32.4%, I/O wait average 20.4%; swap about 2.0/2.1 GiB. Shared dev checkout remains dirty/147 commits behind; production checkout 613 behind. Neither was touched.
- **Not proven:** the live production app is consuming the relay, evaluating actual per-user preferences, or delivering notifications; the deployed image/commit/config is also unverified. Do not claim end-to-end JobBeeper health from CI or relay success alone.
- **Next:** obtain an approved read-only path to source-run/notification telemetry and container identity; test relay → V2 ingestion → canonical dedupe → actual saved-user matching → notification decision in isolated QA, with no production credentials. Use a synthetic QA account/bot only after separate approval. No Company Watch boards have been approved or activated.

---

## Current checkpoint — 2026-11-17 Phase 1 merged

PR #76 is merged into `v2-live-radar`. PR #76 merge commit: `0220eef1044e042d3041adb97c2d4648afed56a0`. Latest subsequent V2 merge: PR #71 at `e3f1c9c` (496 exact-head tests passed); fetch latest remote HEAD before checkout. PR: https://github.com/AvinashBhalla/job-beeper/pull/76. Exact final PR-head CI #1501 passed 32 focused tests and **495 full V2 tests** (58.062s). Local full V2 tests: 495 passed; focused Phase 1 tests: 10 passed.

The pinned Company Watch manifest has 100 rows (90 enabled, 10 disabled); importer stages 19 direct ATS candidates and retains 81 manual-review rows. All 19 V2 candidates remain low-confidence and unlinked. The import code was not deployed to a shared runtime and the manifest was not imported to a persistent dev/QA/production DB; validation used temporary SQLite databases only.

**Next:** Phase 2 readiness, not implementation yet. First establish isolated QA from merge commit 0220eef and capture baseline. The link API requires an existing employer row, while the current employer-creation endpoint performs public crawling. The activation endpoint enables a provider-level flag and syncs the full provider config allowlist; QA must isolate that allowlist or activation must be safely narrowed before testing. Then owner-review a small sample. Source-manifest `verified_ats_board` candidates for review are Canva and Abercrombie & Fitch (SmartRecruiters), Cyderes and Kobie (Lever); none is approved for activation merely by its label. Any Greenhouse candidate needs official employer identity/link review first. In QA only, verify a small approved sample, then activate only the explicit approved allowlist; prove scheduler/lease/baseline invariants and silent first-poll + new second-poll behavior. Do not touch the dirty dev checkout or production; no notifications, Phase 3 JD work, Phase 4 quality pilot, Phase 5 alerts or deployment are authorized by the Phase 1 merge.

See `docs/COMPANY_WATCH_V2_INTEGRATION_HANDOVER_2026-11-17.md` for acceptance details and phase boundaries.

---



## Historical planning checkpoint — 2026-11-17 (superseded by merged Phase 1 checkpoint above)

Read first: [Company Watch → V2 integration plan and handover](COMPANY_WATCH_V2_INTEGRATION_HANDOVER_2026-11-17.md).

- Target the mature `v2-live-radar` branch, current HEAD `dfc7bb57c3e87f89d3d5f2a9859afbc2ad692eb5` (merged PR #75), not `main`. The original architecture audit was against parent `5c28d97ea39edfa8af13d9686f7b97c3997901f3`; PR #75 changed only test fixtures. Company Watch PR #72 is merged into main only; PR #73 remains draft/open on main. Do not merge/cherry-pick its complete tree into V2.
- Company Watch CSV: 100 records, 92 enabled/8 manual; 72 are generic careers pages. Existing V2 already has 12 source collectors including Greenhouse, Lever, Ashby, SmartRecruiters, Workday and Workable, a board registry, candidate staging, explicit verify/activate APIs, per-board scheduler, SQLite upsert/dedupe, per-user preference evaluation and per-user opt-in Telegram dispatcher.
- Integration must reuse V2's collectors/matcher/notification path. Do not migrate Company Watch `filters.json`, `judge()`, URL-only `seen.json` or `send_telegram()`.
- Gaps to fix in order: (1) extend provider-aware candidate import for Company Watch ATS board modes; (2) resolve and validate actual employer identity; (3) keep all imported records review-only and no polling until explicit verification/activation; (4) add first-class JD completeness/status and content hash; (5) fix same/shorter-length material JD updates in `upsert_jobs()`; (6) use a per-source JD-completeness alert gate for the new cohort only, checked during queue and final send; (7) expand labelled matcher/precision benchmark and rejection breakdown; (8) only later consider registry as scheduler source-of-truth.
- Runtime read-only evidence 2026-11-17: dev checkout is dirty and 147 commits behind; prod checkout 613 behind; Docker access denied to ubuntu. Ports 8000 timed out, 8001 reset, 8010/8006/18011 returned 200. Preserve local config/.env/.venv/backup; do not pull, reset, clean, restart, use sudo or touch prod.
- This prompt's work was documentation/inspection only; no code/config/DB/notification/deployment changes and no local tests run. No owner input is needed now.
- CI follow-up: the earlier PR #74 runs #1482–#1494 were against old base `5c28d97ea39edfa8af13d9686f7b97c3997901f3` and failed from stale static notification fixtures. The test-only correction was merged as PR #75 at `dfc7bb57c3e87f89d3d5f2a9859afbc2ad692eb5`; post-merge V2 CI [#1495](https://github.com/AvinashBhalla/job-beeper/actions/runs/44061666892) passed all 485 tests (64.834s). PR #74 was synchronized to that base; refreshed exact-base CI [#1497](https://github.com/AvinashBhalla/job-beeper/actions/runs/44062624606) passed all 485 tests (65.347s) and 32 focused tests. PR #74 is draft/mergeable and ready for owner review. After it is merged, the next increment is strict idempotent Company Watch manifest import only, with no polling/activation. No runtime/source/notification state changed.

**Historical snapshot:** 2026-11-08 — Candidate V2 integration branch; final browser regression completed, acceptance still blocked by evidence-only gates; not deployed
**Release integration branch:** `v2-live-radar`

**Active candidate branch:** `integration/pr46-v2-rebase-20261108`
**Production host:** Oracle Cloud Ubuntu VM `job-radar`

This is the current operating summary for an engineer taking over. `docs/JOB_RADAR_HANDOVER.md` is the detailed chronological record; `docs/JOBBEEPER_REFERENCE.md` describes the product architecture. **Mandatory rule: update both this file and the detailed handover after every user prompt before ending the turn/session, including decisions or evidence-only turns (record “no code change” when applicable).** After every code/config change, document what changed, tests/CI, commit SHA, deployment evidence, remaining work, exact commands/output expected from the user, and the next-chat continuation prompt. Newest handoff supersedes older instructions; explicitly label older checklists historical. Never rely on the current chat alone.



## Independent orchestrator review — 2026-10-16

- Detailed findings are recorded in `docs/JOB_RADAR_HANDOVER.md` under **Orchestrator review checklist — independent review, 2026-10-16**. The fetched worksheet still had Q1–Q10 marked `CLAUDE RESPONSE: Pending`; no pushed answers were available to assess. Do not treat this as Claude's completed response.
- Current branch `v2-live-radar` is discoverable, but the GitHub connector result available in this review did not expose its current commit SHA. The previously observed `694c0a3b4e3b64677783414a5f6f1d49aca3f822` is not independently confirmed as the current head. Obtain the exact branch HEAD before asserting commit-level source/CI alignment.
- Independently inspected `v2/gemini_experience_diagnostic.py`, `v2/test_gemini_experience_diagnostic.py`, `v2/greenhouse_canary.py`, and `v2/docker-compose.dev.yml`. The diagnostic's four tests cover trusted fresh exact-hash cache acceptance, mismatched hash, expiry and skill-specific scope. This supports the narrow cache/bridge/evaluation claim, not the whole product pipeline.
- `v2/greenhouse_canary.py` is a read-only two-snapshot ID/timestamp-coverage utility. It does not implement a freshness guard, establish upstream timestamp semantics, enforce a 72-hour cutoff, set pass/fail thresholds, measure relevant/new yield or prove scheduler dispatch cannot occur. Review the collector and fixtures before any freshness claim or source enablement.
- No VM shell was available and no tests were run by the independent reviewer. Sanitized VM results in the handover remain user-reported evidence. CI for the exact current head is unverified.
- Decision: defer `jd_experience_source` persistence until a concrete consumer and migration/backwards-compatibility design justify it. Keep production unchanged, Telegram/notifications disabled, and preserve VM-local `M v2/config.json`, untracked `.venv/`, and the existing dev volume.
- Single next increment: delivery-disabled integration coverage for one canonical opportunity through persisted evaluation, notification-ledger decision, API payload and dashboard-facing fields. Inspect current contracts, add a focused test, run it plus the full unit suite on the exact branch head, and record exit codes/CI. Separately, Claude must fill Q1–Q10 in the same handover and push both documents before the answers can be reviewed.
- Review documentation commit: `6e208a8295b24ea9e2802bd86476794e87427b8e` (detailed handover). Knowledge-transfer update and post-write re-fetch are pending.
## Follow-up review checkpoint — 2026-10-16

- Re-fetched `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` from `v2-live-radar`. Q1–Q10 are still `CLAUDE RESPONSE: Pending`; therefore no new Claude answers have been independently graded.
- Added **Follow-up review request — 2026-10-16** to the detailed handover. It asks for exact branch/local/VM revision identity; source-to-dashboard integration evidence; a decision on schema deferral; real Greenhouse timestamp semantics and old/missing/malformed timestamp tests; explicit two-poll canary acceptance thresholds and proof of dispatch isolation; official ATS endpoint evidence; LinkedIn parser/429/network-isolation evidence; release/rollback gates; roadmap drift review; and one prioritized next increment.
- New handover commit: `f6f92b7d5cff00df89b7c8aaab033a78197e6570`. Handover blob SHA from the write response: `03cb5e9839434479fd8ce0d9fcd9daa02e8891e7`.
- Latest commit search also showed `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` and `572f56573fa8f66a532ee676c2aa66b25a843d0a`; these are commit-search results only and do not independently establish current branch head, VM deployment, or CI status.
- After Claude answers Q1–Q10 and revises the plan if needed, proceed with exactly one test-first development increment. Default priority is delivery-disabled canonical opportunity → evaluation → notification-ledger decision → API/dashboard consistency. Do not perform production cutover, real Telegram sends/replay, volume deletion, broad reset or schema migration in this phase.
- Claude must update both handovers after the work unit, push to `v2-live-radar`, and provide exact commit/head, tests/CI, deployment evidence, risks and rollback. Re-fetch and verify both documents; reconcile concurrent changes rather than overwriting.
- No application code, VM configuration, production state or notifications were changed in this documentation-only work unit. No VM shell or test runner was available in this review.
## Current verified state — 2026-10-15 (authoritative exact-hash diagnostic and autonomy directive)

### Active issue: Gemini required-experience cache → bridge → live persisted evaluation
- Branch: `AvinashBhalla/job-beeper:v2-live-radar`; consult both handovers and `docs/JOBBEEPER_REFERENCE.md`.
- User-reported unit suites previously passed: `v2.test_gemini_extractor` (14 tests), `v2.test_radar` (88 tests), and `v2.test_gemini_experience_diagnostic` (4 tests). No tests were run this turn; CI for the new diagnostic was not independently verified.
- After matcher activation, first health curl reset and SSH closed; on the user's follow-up SSH session, read-only state checks showed `job-radar-dev` Up 14 minutes, state running, not restarting, restart_count=0, exit_code=0, not OOM-killed, no container error, and original `job-radar-dev_radar-dev-data:/data` mount retained. Effective `matcher=true`, `extraction=true`, Telegram token/chat absent, `notifications_enabled=false`, `linkedin_enabled=false`. Bounded health retry returned `status=ok`, version 2.0.0, one configured source and no source errors. The earlier reset was transient, not a continuing failure; production unchanged.
- Latest redacted live diagnostic returned `candidate_verified`: exact current input hash; successful cache matching `gemini-3.5-flash-lite`, age 3008 seconds inside the 30-day TTL; job last seen 616 seconds earlier; required `total_professional` 3–5 years, confidence 0.95, verifiable evidence present, and at least one range bound.
- The actual matcher bridge accepted this cache in a **temporary DB copy** with transient `jd_experience_source=gemini_verified`; actual `_persist_job_evaluation` wrote 3–5-year bounds and an experience match reason. The latest live row now is also verified: row present, min=3.0/max=5.0, `live_evaluation_bounds_match_cache=true`, one match reason and `live_evaluation_experience_reason_present=true`. Diagnostic reports source DB read-only/unmodified, no Gemini API calls and no notifications.
- Pre-activation baseline was min=1.0/no maximum; this is superseded by the latest runtime output proving the live row now matches min=3.0/max=5.0. Current `job_evaluations` schema has no `jd_experience_source` column. The alertability-reason flag being false in the sandbox is expected under disabled-notification/non-match policy; experience reason belongs to match reasons.
- Current app diagnostic files: `v2/gemini_experience_diagnostic.py` and `v2/test_gemini_experience_diagnostic.py`. No application-source or schema change was made for this verification. The user explicitly set the ignored dev `.env` matcher flag and recreated only the isolated dev service; the redacted diagnostic itself opened the source DB read-only and made no live DB writes or Gemini calls. Production stayed unchanged. Preserve VM-local `M v2/config.json` and untracked `.venv/`; never stage, overwrite, reset or clean them.
- **Standing authorization (2026-10-15):** user asked us to do required routine project work without asking at every step and explicitly approved enabling the matcher in isolated dev. Proceed with routine reversible code/docs/tests and dev-only config/restarts within scope without repeated confirmation. Keep production untouched, notifications/Telegram off, LinkedIn off; never expose secrets; preserve `M v2/config.json` and `.venv/`. Do not do destructive/irreversible actions, volume deletion, schema migrations, production rollout, notification sends/replay, credential rotation, or OS/Docker permission changes without a scoped safe reason. If no remote VM tool is available, state that accurately and give the narrowest command.
- **Next:** the Gemini required-experience cache → gated matcher → live persisted evaluation acceptance target is met for one trusted cache candidate: exact current input hash/model/TTL; required `total_professional` 3–5 years; confidence 0.95; evidence present; live persisted min/max 3–5 and experience reason. Container recovered from transient health reset; notifications/Telegram/LinkedIn remain off; production unchanged. Claude Code must connect directly from the user's Windows machine using `ssh -i "C:\\Users\\avibh\\Downloads\\ssh-key-2026-10-07.key" ubuntu@130.210.27.197` and execute routine VM checks itself, avoiding user-mediated command/output relay. The detailed `docs/JOB_RADAR_HANDOVER.md` now includes a Claude Code response questionnaire (Q1–Q10), suggested review gates and ChatGPT orchestrator checklist. Claude should fill responses in that same file, push updates to `v2-live-radar`, and update this compact transfer; the next ChatGPT session independently reviews answers against source, commits/PRs, tests/CI and sanitized VM evidence. Next implementation path after that review: test and verify canonical opportunity → evaluation → notification ledger/API/dashboard consistency while dispatch remains disabled; then Greenhouse upstream-timestamp freshness guard + GET-only two-poll one-board dev canary; Ashby, Lever, SmartRecruiters one at a time; source-health observability; finally a reviewed production promotion PR. No production cutover, real notification/replay, volume deletion, or schema migration before reviewed design. Preserve `M v2/config.json` and `.venv/`.

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
## 2026-10-14 — Approved dev-only `radar` service rebuild/recreate

- User explicitly approved recreating/rebuilding only the development `radar` service with local `.env` and the existing verified dev volume. Exact authorized command: `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`. This does not authorize `down`, volume lifecycle actions, production changes, SQLite commands/writes, notification replay, or turning on Gemini matcher.
- Preconditions: VM checkout branch `v2-live-radar` at `c40e5d7`; status `M v2/config.json`, `?? .venv/` (preserve both); Compose `config --quiet` passed with explicit `.env`. Container/project/service labels verified as `job-radar-dev`/`job-radar-dev`/`radar`; named volume `job-radar-dev_radar-dev-data` is mounted to `/data`. Comparison of VM HEAD to branch tip was 25 ahead, 0 behind, only README and handover docs changed, no app/Compose source changes.
- There is no root `.dockerignore`; the repository root is build context and `.env`/`.venv/` may be part of context sent to the local Docker daemon, but Dockerfile copies only `v2/` and `dashboard/` to image layers. Do not delete/modify these local files. Stay with the approved dev-only command and preserve named volume.
- After completion, run read-only status and filtered env checks; show only key presence, model and two flag values, never key or full environment. Verify `http://127.0.0.1:8001/health` and shadow diagnostics as appropriate. Both extraction and matcher must remain false initially; no matcher activation until separate validation and explicit approval. Do not infer functionality solely from container being Up/env presence. No production change or notification replay.

### Continuation prompt

Continue existing Job Radar V2 Gemini matcher task on `v2-live-radar`; read three reference/handover files first. User has explicitly approved rebuild/recreate of only dev `radar`, passing local `.env` and preserving DB volume. In SSH, run only `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`. Existing verified volume is `job-radar-dev_radar-dev-data` mounted at `/data`; branch is `v2-live-radar` HEAD `c40e5d7`, local `v2/config.json` modified and `.venv/` untracked, keep both. Compose config validation succeeded. No root `.dockerignore`, build context may contain `.env`/`.venv` but Dockerfile only copies `v2/` and `dashboard/` into image. Don't run down/remove volume, SQLite, production changes, or replay notifications. Following command, verify container status, safe-filtered key presence/model/flags (never actual key/full env), dev port 8001 health, then shadow-only Gemini diagnostics. Keep extraction and matcher false pending controlled validation; do not enable matcher without explicit approval. Update and verify both handovers each turn.
## 2026-10-14 — Dev `radar` build/recreation succeeded; verify runtime next

- User posted Compose output confirming build finished successfully in 9.7s with 14/14 steps; `job-radar-dev-radar:latest` built and `job-radar-dev` started in 13.2s. Command was run from `~/job-beeper-dev` after explicit approval.
- Build output included `.dockerignore` transfer 2 B and context size 579.56 kB. Record those observed numbers; do not infer file contents. Preserve local `v2/config.json` and `.venv/` unchanged.
- Existing DB volume `job-radar-dev_radar-dev-data` is confirmed mounted at `/data`; explicit Compose env-file config validation passed earlier. Prior container lacked Gemini key; current new container has not yet been verified. Only approved lifecycle action is the dev `radar` rebuild/recreate; no `down`, volume change, DB access, production changes, or notification replay.
- Next request read-only outputs: `sudo docker ps --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'`; `sudo docker exec job-radar-dev sh -c 'if [ -n "$GEMINI_API_KEY" ]; then echo gemini_key=configured; else echo gemini_key=empty; fi; printf "model=%s\nextraction=%s\nmatcher=%s\n" "${GEMINI_MODEL:-unset}" "${GEMINI_EXTRACTION_ENABLED:-unset}" "${GEMINI_MATCHER_ENABLED:-unset}"'` (key value must never print); `curl -fsS http://127.0.0.1:8001/health`; `curl -fsS http://127.0.0.1:8001/api/llm-shadow-status`. Share outputs; only proceed with a shadow-only validation after confirming the fresh environment and status. Keep both flags false and Telegram blank unless user explicitly approves separate change.

### Continuation prompt

Continue existing Job Radar V2 Gemini matcher issue on `v2-live-radar`; read handover, knowledge transfer, `docs/JOBBEEPER_REFERENCE.md`. User ran approved command `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`. Build succeeded (14/14, 9.7s), image built, `job-radar-dev` started (13.2s); Docker output showed `.dockerignore` transfer 2B and context 579.56kB, without a confirmed reading of ignore rules. Verified existing volume `job-radar-dev_radar-dev-data` mounted at `/data`. Next check container status, safe env presence/config values without outputting key, `curl -fsS http://127.0.0.1:8001/health`, and `/api/llm-shadow-status`. Do not alter flags or replay notifications yet. Both Gemini flags false by default and Telegram must remain empty. No volume/DB/production changes. Preserve local `v2/config.json` and `.venv/`; update and re-fetch both handovers every user turn.
## 2026-10-14 — Fresh container is healthy; Gemini extraction remains off

- User-reported runtime checks after successful dev rebuild: `job-radar-dev` Up for 4 minutes, image `job-radar-dev-radar`; safe-filtered env `gemini_key=configured`, `model=gemini-3.5-flash-lite`, `extraction=false`, `matcher=false`; `/health` returned `status=ok`, version `2.0.0`, DB `/data/jobs.db`, no currently running Naukri loop shown, previous successful ingestion recorded.
- `/api/llm-shadow-status` returned `enabled=false`, `api_key_configured=true`, model `gemini-3.5-flash-lite`, `mode=shadow_only`, daily limit 20, calls today 0, cache successes 14 and errors 6. Recent cache examples displayed timestamps from 2026-10-12, i.e. before rebuild/date 2026-10-14. These old records are not proof of a fresh extraction/current hash/current persisted evaluation. The response emitted titles, IDs and evidence; do not re-share/copy raw response, use only the sanitized status/cache-precheck script in detailed handover.
- The exact dev `/data` named volume is confirmed. Both prerequisites for controlled shadow extraction are satisfied (key configured, isolated volume verified), but `GEMINI_EXTRACTION_ENABLED` remains false. Ask for separate explicit approval before updating ignored local `.env` to enable shadow extraction and recreating only development `radar`. That step makes up to the configured bounded Gemini API calls and writes shadow cache data into the existing dev database. Budgets are `GEMINI_MAX_CALLS_PER_RUN=3`, `GEMINI_MAX_CALLS_PER_DAY=20`. Keep `GEMINI_MATCHER_ENABLED=false`, Telegram credentials empty, notifications off and LinkedIn disabled. No production changes or historical alert replay.
- Once approved, turn on only extraction, recreate only dev `radar` with explicit `--env-file .env` and same project/volume, then inspect sanitized status/cache eligibility and exact-JD/model hash plus persisted evaluation in read-only checks. Do not enable matcher without fresh eligibility evidence and separate explicit approval. Preserve `v2/config.json` and `.venv/`.

### Continuation prompt

Continue the existing Job Radar V2 Gemini experience matcher task on `v2-live-radar`; read both handovers and `docs/JOBBEEPER_REFERENCE.md`. The approved development `radar` rebuild succeeded. Current container `job-radar-dev` Up, image `job-radar-dev-radar`; key configured, model `gemini-3.5-flash-lite`, extraction false, matcher false. Health endpoint OK, DB is `/data/jobs.db`, with verified mount to existing `job-radar-dev_radar-dev-data`. Shadow-status says enabled false, key true, `calls_today=0`, cache successes 14/errors 6; latest entries returned were dated 2026-10-12, prior to rebuild, and raw output exposed titles/IDs/evidence; use only sanitized indicator scripts going forward. Ask the user for explicit approval to enable only dev shadow extraction (`GEMINI_EXTRACTION_ENABLED=true`) and recreate only dev `radar`; this makes up to 3 Gemini calls per run, 20/day, and writes cache rows in dev DB. Leave matcher false, Telegram blank, LinkedIn off, no notifications, no production changes or historical replay. Need fresh cache exact-JD/model hash and persisted evaluation verification before separately asking about matcher enablement. Preserve local `v2/config.json`, `.venv/`; update/re-fetch both handovers every turn.
## 2026-10-14 — Latest continuation state and next-chat instructions

### Runtime evidence (user supplied)

- Dev-only rebuild completed successfully (14/14 build steps); image `job-radar-dev-radar` built and container started. Current container `job-radar-dev` reported Up for 4 minutes.
- Container environment was verified without printing key: `gemini_key=configured`, model `gemini-3.5-flash-lite`, `extraction=false`, `matcher=false`.
- `http://127.0.0.1:8001/health` returned `status=ok`, version `2.0.0`, DB `/data/jobs.db`. Naukri stats in the health response: `running=false` at that instant, last successful timestamp `2026-10-14T08:40:46.188540+00:00`, 366 jobs seen, 1 new job, no reported error. Do not interpret an instantaneous `running=false` alone as a scheduler fault.
- `/api/llm-shadow-status` currently showed extraction disabled, API key configured, model `gemini-3.5-flash-lite`, shadow-only mode, daily limit 20, calls_today 0, 14 cache successes and 6 errors. Sample timestamps were all 2026-10-12. No fresh cache evidence has been generated on 2026-10-14 yet, so no fresh exact-JD/model hash eligibility or persisted matcher consumption is proven.
- The actual dev volume is confirmed as `job-radar-dev_radar-dev-data` mounted at `/data`. Production is untouched. Preserve local `M v2/config.json` and untracked `.venv/`; don't stage/overwrite/reset/clean either.

### Code changes made directly on GitHub

- Commit `10d9c49d08d050c5639902166f697961328ab81b`: updated `v2/gemini_extractor.py` so `/api/llm-shadow-status` no longer returns job source IDs, titles, raw extraction payload, evidence quotations, or skill lists. The recent samples now carry only a safe summary: status/model/time/error code, experience bounds/type/scope/confidence, evidence-present boolean, and a shape-eligibility boolean. The shape boolean does not establish the exact current JD hash or matcher consumption.
- Commit `872bae496d3df7e501b7e5179c0a76376c42ea93`: added `test_shadow_status_redacts_job_identity_and_raw_extraction`.
- Follow-up commits `c1c2412e20b56538fcb10a1f5ee492b40611e27f` and `36db6b40c1aad80e7e6d0ae8ce6203bae381a030` harden malformed cached-field handling and add `test_shadow_status_handles_malformed_cached_payload`.
- These changes are committed on `v2-live-radar`, but tests have not yet been run after these code commits. A combined GitHub status lookup for test commit `36db6b40c1aad80e7e6d0ae8ce6203bae381a030` returned no status entries; do not claim CI passed. The running container image predates the new diagnostic-redaction code; the VM must fast-forward/pull and retest before a rebuild serves sanitized status.
- The build output said BuildKit loaded `.dockerignore` (2 B) and sent a 579.56 kB context. An earlier note that `.dockerignore` was absent was based on a failed GitHub file fetch and is not conclusive. Do not claim `.venv/` or `.env` was sent in the context; verify exact ignore behavior from the VM if relevant. Do not delete or change either local file.

### Next steps (do not skip gates)

1. Start each turn by reading `docs/JOB_RADAR_HANDOVER.md`, this file, and `docs/JOBBEEPER_REFERENCE.md`. Continue the single experience-matcher issue. Make appropriate code and tests directly in GitHub branch `v2-live-radar` with current blob SHAs; provide VM commands and wait for actual outputs. Do not ask the user to manually edit source files.
2. Ask user to run and share results of:
```bash
cd ~/job-beeper-dev
git status --short
git pull --ff-only
printf 'branch=' && git branch --show-current
printf 'head=' && git rev-parse --short HEAD
git status --short
./.venv/bin/python -m unittest v2.test_gemini_extractor
./.venv/bin/python -m unittest v2.test_radar
```
Pull must preserve `M v2/config.json` and `?? .venv/`. Do not stage either, use `git add .`, reset hard, clean, or overwrite the config. If pull conflicts or the test interpreter is missing, stop and diagnose.
3. The core matcher bridge is already implemented and opt-in via `GEMINI_MATCHER_ENABLED`; do not switch it on yet. Ask for separate explicit permission to change the VM-local ignored `.env` to `GEMINI_EXTRACTION_ENABLED=true` while explicitly keeping `GEMINI_MATCHER_ENABLED=false`. State the consequence: calls Gemini at bounded budget (up to 3 per source run, 20 per day) and writes structured cache rows into the dev database, but does not alter matcher decisions while matcher gate is false.
4. After explicit approval, edit only the two env flag lines without echoing `.env` or secrets; preserve `GEMINI_API_KEY` and all other values. Recreate only dev service with `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`; no `down`, no volume changes, no production actions. Then verify container status, key-presence/model/flags with a safe filter, `/health`, and sanitized `/api/llm-shadow-status`.
5. Fresh cache validation must not rely on total cache counts. Confirm fresh current-model successful entries and exact per-job cache/hash eligibility (`_input_hash(job)` includes source, source ID, title, company, trimmed description and extractor version, with TTL/model checks) using a tightly scoped read-only diagnostic. Do not print job description, IDs, titles, evidence text, API key, config token, or whole DB rows. Then verify `_job_for_canonical` returns `jd_experience_source=gemini_verified`, while the persisted `job_evaluations` row contains expected experience bounds/reasons. The existing `job_evaluations` schema has no source column, so do not claim that source marker is persisted; propose a separate schema migration/test only if persisted source attribution is required.
6. Only after proof that an exact current-JD cache entry is fresh, required, total-professional, evidence-backed, confidence >= 0.85, has a range bound and is loaded into persisted evaluation, ask separately for approval to set `GEMINI_MATCHER_ENABLED=true` in development. Keep Telegram credentials empty, notifications off, LinkedIn disabled. No production rollout or historical notification replay without separate explicit approval.

### Copyable next-chat prompt

> Continue the existing Job Radar V2 experience-matcher issue in `AvinashBhalla/job-beeper`, branch `v2-live-radar`; do not start over. First read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`. Goal: when a job description explicitly states total professional experience, trusted Gemini extraction should feed the existing matcher through a fresh exact-JD/model cache; `_job_for_canonical` should show source `gemini_verified`, and the persisted evaluation should carry the expected experience bounds/reasons. The current `job_evaluations` schema does not persist the source marker itself; don't claim otherwise. Matcher stays off until demonstrated and separately approved. Current development VM is `~/job-beeper-dev`, branch `v2-live-radar`, was at `c40e5d7`, local status included `M v2/config.json` and `?? .venv/` (preserve them). Dev container was rebuilt successfully and verified: `job-radar-dev` Up; Gemini key configured, model `gemini-3.5-flash-lite`, extraction false, matcher false; `/health` ok at `127.0.0.1:8001`; `/data/jobs.db` uses verified volume `job-radar-dev_radar-dev-data`. Shadow status is off, key configured, calls_today 0, cache successes 14/errors 6, sample records from Oct 12 only, so fresh cache/matcher consumption not yet proven. Direct GitHub commits just made: `10d9c49` sanitizes `/api/llm-shadow-status` records and `872bae4` adds a redaction unit test; tests haven't yet been run after these changes and runtime still predates them. First ask user to run fast-forward pull and test commands in this handover. Then get explicit approval before enabling only `GEMINI_EXTRACTION_ENABLED=true` (bounded 3 calls/source run, 20/day; writes dev cache); keep `GEMINI_MATCHER_ENABLED=false`. After approved, recreate only dev `radar` using explicit `--env-file .env` and same project/verified volume, inspect only sanitized outputs, confirm fresh exact hash/model/cache TTL, confirm `_job_for_canonical` returns `gemini_verified`, and confirm the persisted evaluation includes expected bounds/reasons without exposing IDs/title/JD/evidence/secrets. Don't state the source marker is persisted: schema currently has no source column. Only after evidence ask separately to enable matcher in dev. Directly commit justified source/tests to GitHub with current blob SHAs, run/report tests truthfully, give copyable commands, wait for output. No production changes, DB volume operations, notification replay, Telegram, or LinkedIn enablement. Preserve `v2/config.json` and `.venv/`; update and re-fetch both handovers every turn.
### Build-context note

- The successful BuildKit output said `.dockerignore` was loaded (2 B transfer) and context was 579.56 kB. Earlier GitHub fetch attempts for `.dockerignore` returned 404, so file absence is not certain; do not repeat the earlier claim as fact. VM's actual ignore-file content has not been reviewed. Never delete `.venv/` or change `.env` to influence build context.

## 2026-10-14 — Dev runtime healthy; GitHub code fixes need pull, tests, and rebuild

- After the approved rebuild, user confirmed: `job-radar-dev` Up 4 minutes, image `job-radar-dev-radar`; runtime key presence `configured`, model `gemini-3.5-flash-lite`, extraction false, matcher false; `/health` status `ok`, version `2.0.0`, DB path `/data/jobs.db`. Correct isolated volume is confirmed `job-radar-dev_radar-dev-data` mounted to `/data`.
- `/api/llm-shadow-status` shows extraction `enabled=false`, `api_key_configured=true`, mode `shadow_only`, daily limit 20, calls_today 0, cache successes 14 and errors 6. Samples were dated 2026-10-12, so fresh cache creation and matcher consumption are not proven. User output from old container exposed job/source IDs, titles, skills and literal evidence quotations; do not repeat/store those details.
- VM checkout was reported at `c40e5d7` on `v2-live-radar`; the remote branch is strictly ahead with no divergence (the last comparison before recent handover commits showed 50 commits ahead). This count changes as docs are committed; don't hardcode it. Use `git pull --ff-only origin v2-live-radar`. Changed files include README, both handovers, `v2/gemini_extractor.py`, and `v2/test_gemini_extractor.py`. Preserve local `M v2/config.json` and `?? .venv/`.
- Direct code/test commits on GitHub: `10d9c49d08d050c5639902166f697961328ab81b` sanitize `/api/llm-shadow-status` sample records; `872bae496d3df7e501b7e5179c0a76376c42ea93` tests redaction; `c1c2412e20b56538fcb10a1f5ee492b40611e27f` and `36db6b40c1aad80e7e6d0ae8ce6203bae381a030` harden malformed cache field handling/add test; `2eba968e29f74f442c675b1a7107f8f96a9bb199` reports `matcher_enabled` without exposing secrets; `d1c5813ac419c2cd4fd036ac0e43f810925cfeea` and `50e2e5422fe9ff1a400bb8fdf3e21dc3246ef022` test the matcher-gate status. No test run after these latest changes has been reported.
- Next do on VM: `cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD`. Preserve `v2/config.json` and `.venv/`; stop if pull fails/conflicts; never reset/clean. Then run `./.venv/bin/python -m unittest v2.test_gemini_extractor` and `./.venv/bin/python -m unittest v2.test_radar`; send actual outputs and stop on failures. Once both tests pass, use already-approved dev-only rebuild command `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar` to apply the GitHub redaction/diagnostics code. It reuses the verified named DB volume; no `down` or volume action.
- Then recheck status, safe-filtered env, `/health`, and `/api/llm-shadow-status`. New status must expose only redacted shape fields and `matcher_enabled=false`, without source IDs/title/raw result/evidence/skill lists. Do not print keys/full environment or replay raw endpoint output.
- Before toggling extraction, request separate explicit user approval: set only `GEMINI_EXTRACTION_ENABLED=true`, keep matcher false. Consequences: up to 3 Gemini calls per source run, max 20/day, writes cache rows to dev DB. After approval only, update local ignored `.env` without echoing secret and rebuild only dev radar. Then prove a fresh exact-JD hash/model/cache-TTL match, `_job_for_canonical(...)["jd_experience_source"] == "gemini_verified"`, and persisted `job_evaluations` bounds/reasons. `job_evaluations` does not currently persist the source marker; do not claim it does or add a schema migration without separate approval. Only ask for separate approval to enable matcher after proof. Production untouched, Telegram blank, notifications off, LinkedIn disabled; no historical alert replay or DB/volume lifecycle operations.

### Copyable next-chat prompt (latest state)

> Continue the existing Job Radar V2 Gemini experience-matcher task in `AvinashBhalla/job-beeper` on `v2-live-radar`; do not start from scratch. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` before decisions. The target is to prove that an explicit total-professional experience requirement in a job description is extracted by Gemini, accepted only via fresh exact-JD/current-model trusted cache, consumed by `_job_for_canonical` as `jd_experience_source=gemini_verified`, and reflected in the persisted `job_evaluations` experience bounds/reasons. The evaluation schema does not store the source marker itself. User VM at `~/job-beeper-dev` is `v2-live-radar`, HEAD `c40e5d7`, with `M v2/config.json` and `?? .venv/`; preserve both. Dev container is healthy after approved rebuild: `job-radar-dev`, key configured, model `gemini-3.5-flash-lite`, extraction false, matcher false, `/health` ok, DB `/data/jobs.db`, named volume `job-radar-dev_radar-dev-data` mounted at `/data`. `/api/llm-shadow-status` showed only old 2026-10-12 cache entries (14 successes/6 errors, calls_today 0) and old image output included raw IDs/titles/evidence. Direct code is already committed to GitHub to redact status samples, harden malformed cache handling, expose `matcher_enabled`, and test these behaviors (`10d9c49`, `872bae4`, `c1c2412`, `36db6b4`, `2eba968`, `d1c5813`, `50e2e54`); tests have not yet run. First provide commands to fast-forward pull `git pull --ff-only origin v2-live-radar`, then run `./.venv/bin/python -m unittest v2.test_gemini_extractor` and `./.venv/bin/python -m unittest v2.test_radar`. Stop on any pull conflict or test failure; never reset/clean or overwrite local files. If tests pass, use the previously approved dev-only command `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`, same named volume, no `down`. Recheck redacted status, flags and health. Before changing `.env`, ask separately for approval to set only `GEMINI_EXTRACTION_ENABLED=true` while keeping matcher false; this uses up to 3 calls/source run and 20/day and persists cache data to dev DB. After approval validate fresh exact hash/model/TTL and persisted evaluation; only later seek separate approval to enable matcher. Never print API key, config token, raw job IDs/titles/JD/evidence or whole DB rows. Production untouched; no Telegram/LinkedIn enablement, historical notification replay, volume actions, or schema change without separate approval. Make justified code/tests directly on GitHub with fresh blob SHAs, run/report tests truthfully, update and re-fetch both handovers each turn.
### CI status clarification

- Combined GitHub status lookups for the latest matcher status implementation commit `2eba968e29f74f442c675b1a7107f8f96a9bb199`, the gate test commit `50e2e5422fe9ff1a400bb8fdf3e21dc3246ef022`, and the preceding handover head returned empty status lists. No CI pass/fail can be inferred from empty status; run the two local unittest commands after pulling and report exact results.

## 2026-10-14 — Fresh runtime checks passed; tests/pull precede extraction

- User's latest runtime output: `job-radar-dev` Up 4 minutes, image `job-radar-dev-radar`; safe in-container output `gemini_key=configured`, model `gemini-3.5-flash-lite`, extraction false, matcher false. `/health` status `ok`, version `2.0.0`, DB `/data/jobs.db`, previous Naukri ingestion reported 366 seen, 1 new and no error at check time.
- `/api/llm-shadow-status`: `enabled=false`, API key configured, model `gemini-3.5-flash-lite`, shadow-only mode, daily limit 20, calls_today 0, cache successes 14/errors 6. Returned sample timestamps were 2026-10-12, so no fresh extraction/cache eligibility is proven. Raw output exposed source/job identifiers, titles and evidence; don't copy or repeat. User's command line had a stray malformed `curl` token before the valid status URL; the valid endpoint succeeded.
- Current checkout last reported `v2-live-radar` at `c40e5d7` with `M v2/config.json` and `?? .venv/`; preserve both. Existing isolated volume is confirmed `job-radar-dev_radar-dev-data` mounted at `/data`. Dev-only rebuild succeeded and key/health are now confirmed.
- Next: `cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD`. Expected local config/venv changes should remain untouched. Stop on conflict/failure, never reset/clean. Then run separately `./.venv/bin/python -m unittest v2.test_gemini_extractor` and `./.venv/bin/python -m unittest v2.test_radar`; report real outputs and fix any failure on GitHub before proceeding. Current image predates direct GitHub status-redaction and `matcher_enabled` diagnostic commits.
- After both tests pass, run already-approved dev-only rebuild with explicit env and same project/volume: `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`. No `down` or volume operations. Verify health, flags and redacted status; ensure status excludes source IDs/titles/raw results/evidence/skill lists and reports matcher false.
- Only then request separate approval to set local ignored `.env` `GEMINI_EXTRACTION_ENABLED=true`, explicitly leave `GEMINI_MATCHER_ENABLED=false`, and recreate only dev radar. This uses up to 3 Gemini calls per source run and 20/day and persists shadow-cache rows to dev DB. After fresh shadow activity, perform redacted read-only exact-JD/current-model/hash/TTL and persisted evaluation verification. Require required total-professional evidence, verbatim quote, confidence >=0.85 and at least one bound; `_job_for_canonical` source should be `gemini_verified`, persisted `job_evaluations` bounds/reasons match. The table does not persist the source marker. Only after evidence ask separately for matcher enablement approval. No production, notification replay, Telegram/LinkedIn, volume or schema actions without separate approval. Never expose API key/full env/raw job data.

### Continuation prompt

Continue existing Job Radar V2 Gemini experience-matcher task in `AvinashBhalla/job-beeper`, branch `v2-live-radar`; don't restart from scratch. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `docs/JOBBEEPER_REFERENCE.md` first. Goal: trusted Gemini extraction of explicitly stated total-professional experience must flow through fresh exact-JD/current-model cache to `_job_for_canonical` (`jd_experience_source=gemini_verified`) and affect persisted evaluation bounds/reasons. Current VM `~/job-beeper-dev`, last HEAD `c40e5d7`, local `M v2/config.json`, untracked `.venv/` (preserve, never stage/reset/clean). Container `job-radar-dev` was successfully rebuilt and now is Up; key configured, model `gemini-3.5-flash-lite`, extraction false, matcher false. Health is OK at `127.0.0.1:8001/health`; `/data/jobs.db` is on verified existing volume `job-radar-dev_radar-dev-data`. Shadow status currently disabled, calls_today 0, successes 14/errors 6, examples dated Oct 12; fresh cache isn't proven. The raw endpoint output exposed job identity/evidence, so never repeat it. GitHub already contains direct code/test commits sanitizing `/api/llm-shadow-status`, hardening cache fields, and adding `matcher_enabled` status + tests, but VM has not pulled or run tests. First ask/run `cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD`, stop on conflict, preserve local files. Then run `./.venv/bin/python -m unittest v2.test_gemini_extractor` and `./.venv/bin/python -m unittest v2.test_radar`; stop and fix any failure via direct GitHub commit and retest. After both pass, the previous explicit approval allows rebuilding only dev radar via `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`, same volume, no `down`. Confirm latest redacted status and flags. Ask separate approval to set only `GEMINI_EXTRACTION_ENABLED=true`, keep matcher false. Bounded usage is max 3 calls/source run and 20/day; writes shadow cache rows to dev DB. After approval, rebuild dev service and verify fresh exact-JD/model/hash/TTL cache and persisted `job_evaluations` bounds/reasons with redacted diagnostics. Require required total-professional scope, verbatim evidence, confidence >=0.85, range bound and `_job_for_canonical` source `gemini_verified`. Existing evaluation schema has no source column; don't claim it persists source. Ask separate approval for matcher gate only after evidence. No production changes, notification replay, Telegram/LinkedIn, DB volume actions or schema changes without explicit separate approval. Never print secrets or raw job data. Update/re-fetch both handovers every turn; code/docs via GitHub fresh blob SHAs, truthfully report tests.

## 2026-10-14 — Authoritative continuation: fast-forward VM, then test

- This update reconciles the latest user-provided runtime state with older history above. Continue the existing AvinashBhalla/job-beeper task on v2-live-radar; do not restart from scratch. Read docs/JOB_RADAR_HANDOVER.md and docs/JOBBEEPER_REFERENCE.md alongside this compact handover before future decisions.
- Goal: trusted Gemini extraction of explicitly required total professional experience must be consumed only through a fresh, exact-current-JD/hash/model/TTL cache entry; _job_for_canonical should mark the in-memory result jd_experience_source=gemini_verified, and the persisted job_evaluations row should contain expected experience bounds/reasons. Current schema does not persist the source marker itself.
- User's last-reported VM checkout: ~/job-beeper-dev, branch v2-live-radar, HEAD c40e5d7, local M v2/config.json and untracked .venv/. Preserve both; never stage, overwrite, reset, or clean. Container job-radar-dev is running, project job-radar-dev, service radar, image job-radar-dev-radar; DB path /data/jobs.db; verified volume job-radar-dev_radar-dev-data mounted at /data.
- Runtime reported by user: health ok, key configured (value never print), model gemini-3.5-flash-lite, extraction false, matcher false. Status counts were 0 calls today, 14 cache successes and 6 errors, but displayed examples were dated 2026-10-12. No fresh current-JD cache/matcher proof exists. Older raw status response included job identities and evidence; never copy it into messages or docs.
- Code/test hardening is committed on GitHub (redacted status response, malformed cache robustness, matcher-gate status diagnostics and tests), but VM pull/test completion has not been confirmed. Do not claim tests passed based on prior reports or empty CI status.
- **Immediate next command (pull only):**

      cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD

  Return its complete output. Preserve M v2/config.json and ?? .venv/. If pull fails/conflicts, stop; do not reset, clean, force-pull, or edit code manually.
- After a successful fast-forward, run separately and return complete output for ./.venv/bin/python -m unittest v2.test_gemini_extractor and then ./.venv/bin/python -m unittest v2.test_radar. Fix any failures directly on GitHub with fresh blob SHAs, update both handovers, pull, and rerun. Once both suites pass, the previous user approval covers rebuilding only dev radar via sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar, preserving the existing volume and avoiding down.
- After rebuild, verify container/health, key presence without printing value, model and both false flags, and sanitized /api/llm-shadow-status (no IDs, titles, raw extraction, evidence quotes, or skill lists). Extraction must remain false until the user separately approves setting only GEMINI_EXTRACTION_ENABLED=true in VM-local ignored .env. This makes up to 3 Gemini calls/source run and 20/day and persists shadow-cache entries in dev DB; matcher stays false.
- Before asking for matcher approval, prove a fresh success for exact current input/hash and configured model within TTL; requirement type required, scope total_professional, verbatim evidence present, confidence >= 0.85, at least one experience bound; bridge consumption by _job_for_canonical has source gemini_verified; persisted evaluation has the intended bounds/reasons. Use redacted read-only diagnostics only. Ask separately before enabling GEMINI_MATCHER_ENABLED=true; never change production or replay historical notifications.
- Keep Telegram blank/notifications off and LinkedIn disabled. No volume lifecycle/SQLite broad access or schema change without separate approval. Documentation was reconciled this turn; no application code/runtime/test change was made.


## 2026-10-14 — VM fast-forward confirmed; run Gemini test first

- User's SSH output confirms git pull --ff-only origin v2-live-radar fast-forwarded from c40e5d7 to bcb8cfc, with no reported conflict. The updated paths included README, both handovers, v2/gemini_extractor.py, and v2/test_gemini_extractor.py.
- The shared output omitted visible lines from the preceding git status --short, so do not claim this output confirms the local config/venv status. Preserve v2/config.json and .venv/ absolutely; never stage, overwrite, reset, or clean either.
- No tests have run in this turn and the pull output is not test evidence. No rebuild or environment/DB/runtime change was made. Gemini extraction and matcher remain disabled.
- Next request only the Gemini extractor suite and complete output:
  cd ~/job-beeper-dev
  git status --short
  ./.venv/bin/python -m unittest v2.test_gemini_extractor
  Wait before asking for the separate Radar suite. If this fails, stop and diagnose actual output; don't rebuild or change flags. After a successful result, ask separately for ./.venv/bin/python -m unittest v2.test_radar.
- Continue the same goal: a fresh exact-current-JD/hash/model/TTL, evidence-backed Gemini experience result must flow through the matcher and affect persisted experience bounds/reasons. Do not claim this end-to-end path has been proven. The current evaluation schema does not persist jd_experience_source; retain that caveat. Cross-reference docs/JOB_RADAR_HANDOVER.md and docs/JOBBEEPER_REFERENCE.md.


## 2026-10-14 — Gemini tests passed; run Radar tests next

- User's actual VM output confirms local status still contains M v2/config.json and ?? .venv/; preserve both. From ~/job-beeper-dev, ./.venv/bin/python -m unittest v2.test_gemini_extractor returned Ran 14 tests in 0.108s / OK.
- The test's INFO shadow-extraction line is not evidence of live Gemini API use or fresh runtime cache; no runtime, DB, environment, matcher, or production changes occurred. This turn made no application-code change.
- Next request the Radar suite separately:
  ```bash
  cd ~/job-beeper-dev
  ./.venv/bin/python -m unittest v2.test_radar
  ```
  Wait for and inspect complete output. If it fails, do not rebuild; diagnose and fix directly on GitHub, update both handovers, fast-forward pull while preserving local files, and rerun relevant tests. If it passes, the approved next step is the isolated dev radar rebuild only; do not enable extraction or matcher yet.
- The larger proof remains outstanding: fresh successful Gemini cache for exact current JD/hash/model within TTL, required total_professional scope with evidence/confidence/range bound, bridge consumption through _job_for_canonical, and expected persisted evaluation bounds/reasons. Existing job_evaluations schema does not persist the jd_experience_source marker.


## 2026-10-14 — Both test suites passed; approved dev rebuild next

- User's actual VM output for `./.venv/bin/python -m unittest v2.test_radar`: `Ran 88 tests in 18.796s`, `OK`. The output contains exercised warnings for invalid/partial ATS board fixtures and simulated LinkedIn HTTP 429/backoff paths, but the test process completed successfully. Previous user output confirms `v2.test_gemini_extractor`: 14 tests in 0.108s, `OK`. Both requested local suites pass on the VM code pulled to bcb8cfc.
- Preserve `M v2/config.json` and `?? .venv/`; no code/runtime/DB/flag change occurred this turn. Test results do not prove live Gemini activity or matcher use.
- Next action is the previously approved dev-only rebuild, and nothing broader:
  ```bash
  cd ~/job-beeper-dev
  sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar
  ```
  This reuses the verified dev project and named volume `job-radar-dev_radar-dev-data` mounted at `/data`. No `down`, volume lifecycle, production changes, broad DB/SQLite access, or historical notification replay. If it errors, stop and share complete output.
- Afterward, verify status/health, API-key presence without printing its value, model, both disabled feature flags, and sanitized `/api/llm-shadow-status`; ensure it does not reveal IDs, titles, raw extraction, verbatim evidence, or skill lists and that matcher is false. Do not claim fresh extraction from counters or old samples.
- Next approval gate remains enabling only `GEMINI_EXTRACTION_ENABLED=true` after safe runtime diagnostics; keep `GEMINI_MATCHER_ENABLED=false`. Then prove a fresh exact-current-JD/model/hash/cache-TTL entry, required total-professional scope, verbatim evidence, confidence >= 0.85, one range bound, bridge consumption via `_job_for_canonical`, and evaluation bounds/reasons. Source marker is not persisted in current schema. No production or notification replay.


## 2026-10-14 late update — Development rebuild completed; verify runtime safely

- Actual output from the user shows the approved dev-only build completed: image job-radar-dev-radar was built (14/14 steps FINISHED) and Compose reported container job-radar-dev Started. Build context reported 68.52 kB. This proves build/start command completion, not health, effective env, endpoint redaction, fresh cache, or matcher behavior.
- Local pre-rebuild suites passed: Gemini extractor 14 tests / 0.108s / OK, Radar 88 tests / 18.796s / OK. VM had fast-forwarded to bcb8cfc before subsequent documentation-only commits.
- Next request read-only checks: docker ps state for job-radar-dev; filtered docker exec that only reports Gemini key presence, model and extraction/matcher flag values; curl health at 127.0.0.1:8001/health; and a sanitized parse of /api/llm-shadow-status that prints only whitelisted summary fields plus a boolean/list of prohibited key names found. Never share the full endpoint JSON or any raw job IDs/titles/JD/evidence/skills/API key/config token.
- Required outcome: container running, key configured, model gemini-3.5-flash-lite, both flags false, health ok, matcher_enabled=false, no private job identity/evidence/skills in status. If anything differs, stop and diagnose before any gate change.
- No extraction/matcher activation, DB access/mutation, volume lifecycle, production change, or notification replay was performed. Preserve M v2/config.json and ?? .venv/. Source attribution caveat remains: current job_evaluations table does not persist jd_experience_source.
- After safe runtime verification, separately ask for approval to set only GEMINI_EXTRACTION_ENABLED=true. It consumes bounded Gemini API calls (up to 3 per source run; 20/day) and writes shadow cache rows to the existing dev DB while matcher remains false. Need real fresh activity and exact hash/model/TTL evidence before asking to enable the matcher.


## 2026-10-14 — Runtime redaction check passed; ask before shadow extraction

- User supplied post-rebuild checks: `job-radar-dev` Up, image `job-radar-dev-radar`; safe env shows Gemini key configured, model `gemini-3.5-flash-lite`, extraction false, matcher false. Health `/health` is `ok`, DB path `/data/jobs.db`.
- Sanitized shadow status reports enabled false, matcher_enabled false, api_key_configured true, model `gemini-3.5-flash-lite`, shadow_only mode, daily limit 20, calls_today 0, 14 cache successes and 6 cache errors. Recursive raw-field scan printed `forbidden_fields_present=none`; endpoint check returned ok. Treat counts and any old examples as historical only; fresh extraction has not occurred.
- Both local test suites passed before the rebuild: Gemini extractor 14 tests / 0.108s / OK; Radar 88 tests / 18.796s / OK. No source code, DB rows, or environment flags were changed in this turn.
- Next step is **approval-gated**: ask user permission to set only `GEMINI_EXTRACTION_ENABLED=true` in VM-local ignored `.env`, explicitly retain `GEMINI_MATCHER_ENABLED=false`. That uses Gemini API with existing caps (up to 3 calls per source run, 20/day) and writes shadow-cache rows to the existing development DB. No change to matching decisions while matcher stays false. Do not edit `.env` or recreate service without approval.
- Once approved, change only the extraction flag without exposing secrets, recreate only development `radar` with explicit `.env`, same Compose project and volume; verify settings safely and wait for actual live extraction. Require fresh current-JD/hash/model/TTL, required total-professional evidence, confidence >= 0.85 and a range bound, then bridge consumption and persisted evaluation verification before asking separately to enable matcher.
- Current `job_evaluations` schema does not persist `jd_experience_source`; do not claim it does. Preserve VM-local config/venv and keep production/notifications/Telegram/LinkedIn untouched.


## 2026-10-14 — Approval granted for dev shadow extraction only

- User explicitly approved development-only shadow extraction. Approval covers editing only GEMINI_EXTRACTION_ENABLED=true in VM-local ignored .env, keeping GEMINI_MATCHER_ENABLED=false, and recreating only the dev radar service using explicit .env, project job-radar-dev, and the existing named DB volume. Actual VM execution remains pending.
- Shadow extraction makes Gemini API calls under existing caps (up to 3/source run, 20/day) and writes cache rows to the isolated dev DB. It does not change match decisions while matcher is false. Never print .env or secrets.
- Next command should refuse if .env is absent, duplicate relevant env keys exist, or the matcher key is explicitly not false. Change/append only the extraction flag, guard against exported shell variables overriding it, then run only the approved dev radar up --build command. No down, volume changes, production, or notification replay.
- After command output, safely verify live flags, health and redacted shadow endpoint. Then wait for actual fresh activity and prove exact-current-JD/hash/model/TTL eligibility plus experience classification/evidence/confidence/bounds, bridge consumption, and persisted evaluation bounds/reasons before asking separately to enable matcher. The current evaluation schema does not persist jd_experience_source.
- Preserve M v2/config.json and ?? .venv/. Do not claim the VM environment changed until user returns command output.


## 2026-10-14 — Shadow extraction flag updated and dev container started

- After the user's explicit approval, the guarded command reported extraction_flag=true, matcher_flag=explicit_false, env_contents=not_printed. It updated only the VM-local ignored .env extraction flag; no secret value was printed.
- Dev Compose build reported 14/14 steps FINISHED, built job-radar-dev-radar, and started container job-radar-dev. This does not yet prove the effective in-container flags, post-start health, or a fresh Gemini call.
- Next run read-only checks: container status; key presence only plus safe model/extraction/matcher flags; /health; sanitized /api/llm-shadow-status. For the status response, allowlist top-level metrics and recent result summary fields only (status/model/created_at/error_code/experience bounds/type/scope/confidence/evidence-present/shape-eligible); scan for prohibited identity/title/raw-JD/evidence/skill keys and print only their names or none. Never print complete JSON, raw job data, evidence, API key or config token.
- Required effective values are extraction true and matcher false; health ok. Then wait for actual new shadow activity. Prior counts 14 success / 6 errors and old cache samples do not count as fresh activity. Config caps remain up to 3 Gemini calls per source run and 20/day; cache writes affect only the existing isolated dev DB.
- Do not enable matcher before proof of fresh exact current JD/hash/model/TTL, required total_professional scope, evidence-present, confidence >= 0.85 and a range bound, bridge source jd_experience_source=gemini_verified, and persisted evaluation experience bounds/reasons. The existing job_evaluations schema does not persist that source marker. Ask separately before matcher activation. Production, notifications, volume and schema stay untouched.


## 2026-10-14 — Fresh shadow extraction observed; exact-hash diagnostic committed

- User runtime output after approval: container up, health ok, Gemini key configured (value hidden), model gemini-3.5-flash-lite, extraction true, matcher false, status redaction passed. calls_today=6, successes=20 (up from 14), errors=6. New successful results have current-day timestamps. One shape-eligible sample was required/total_professional, evidence present, confidence 0.95, and had a range bound. This proves fresh extraction/cache writes occurred but not exact current job-hash matching or matcher consumption.
- Added v2/gemini_experience_diagnostic.py and v2/test_gemini_experience_diagnostic.py. The diagnostic opens the source SQLite DB read-only, matches a recently seen job's recomputed hash with a successful cache row and current model/TTL, revalidates the trusted required/total-professional evidence/confidence/range gates, inspects existing evaluation summaries, then copies one job/cache record to a temporary SQLite DB and invokes the real bridge and evaluation writer there with matcher=true scoped only to that diagnostic process. The temporary DB is removed. No API calls, live DB writes, alerts or global flag changes.
- Regression tests cover exact fresh hash and sandbox persisted evaluation, mismatched description hash, expired result and skill-specific rejection; the happy path asserts no Gemini network call. These new tests have not run yet.
- Next: pull latest branch with status check and fast-forward only, preserving M v2/config.json and ?? .venv/, then run ./.venv/bin/python -m unittest v2.test_gemini_experience_diagnostic. Stop on any failure/conflict. After tests pass, run the script inside the existing container without rebuild using sudo docker exec -i -w /app job-radar-dev python - < v2/gemini_experience_diagnostic.py; the script source is piped from checkout while imports use already-deployed app code. It reads live /data/jobs.db read-only and writes only a temporary clone. Return redacted output.
- Require exact current hash, current model, TTL, required total_professional evidence, confidence >=0.85, one range bound, sandbox gemini_verified bridge, sandbox evaluation row with matching bounds and experience reason. Check existing live evaluation-bound/reason booleans separately; don't claim real persisted evaluation has been updated if those are false. Source marker remains absent from the current job_evaluations schema; no schema change.
- Matcher remains false. Do not enable it without separate explicit approval after proof. Keep production and notifications untouched, no DB/volume actions; preserve local config and virtualenv.


## 2026-10-14 — Diagnostic unit tests passed; run read-only live probe next

- User's actual output confirms VM fast-forward from bcb8cfc to b427bab and `v2.test_gemini_experience_diagnostic` passed: 4 tests in 0.336s, OK. Fixtures exercise fresh exact hash plus trusted experience, reject mismatched description hash, expired cache and skill-specific scope. This does not establish that a qualifying current job is present in the live database.
- No live DB diagnostic has run yet. Preserve any local `M v2/config.json` and `?? .venv/`; do not stage/reset/clean/overwrite them.
- Next run the checked-out diagnostic source within the already-running container:

      cd ~/job-beeper-dev
      sudo docker exec -i -w /app job-radar-dev python - < v2/gemini_experience_diagnostic.py

  This invokes only the new script from stdin, imports the deployed app's core modules, opens /data/jobs.db read-only, recomputes candidate hashes, validates model/status/TTL and required total-professional evidence, checks live persisted evaluation summaries, and runs actual matcher bridge plus persistence writer in a temporary database copy of one candidate. Temp DB is deleted. No Gemini network request, live DB write, global feature flag change or notification action.
- Return complete output. It reports sanitized status/booleans and numeric bounds only. A no-candidate result is useful negative evidence but not proof no fresh extraction occurred; do not enable matcher.
- Require exact hash/model/freshness and trusted experience fields, sandbox source marker gemini_verified, matching sandbox evaluation bounds/reasons; separately assess existing live evaluation booleans. Existing schema does not persist jd_experience_source. Matcher remains false and a separate explicit approval is still required.


## 2026-10-14 — Exact-hash candidate verified; live consumption still gated

- The user's live diagnostic output verifies one recent job and successful cache row share the exact current input hash; configured model matches, cache age is 538 seconds against a 30-day success TTL, and job last-seen age is 606 seconds against the 24-hour selection window. Trusted extraction is required `total_professional`, 3.0–5.0 years, confidence 0.95, evidence present, range bound present.
- Real `_job_for_canonical` and `_persist_job_evaluation` ran against a temporary SQLite copy and produced source `gemini_verified`, a row written, matching 3–5 bounds, and an experience match reason. The live source DB was read-only/unmodified; no Gemini request or notification occurred.
- The existing live persisted evaluation is 1.0 minimum and no maximum; it is not Gemini-backed because the runtime matcher flag is still false. Live end-to-end persistence must be tested after separate approval to enable the matcher in isolated dev only. `job_evaluations` does not persist the source marker; no schema change planned.
- `sandbox_alertability_experience_reason_present=false` is expected under current policy because experience is recorded in match reasons, while alertability reasons reflect no-match/notifications-disabled policy. Notifications stay disabled and no alert replay is allowed.
- No code/config/schema/runtime changes or tests in this turn. Previously supplied test runs remain 14 extractor, 88 Radar, and 4 diagnostic tests, all OK. CI not independently verified. Preserve `M v2/config.json` and `.venv/`; production remains unchanged.
- Next step: ask the user to explicitly approve enabling the matcher on the isolated dev service. After approval only, use the existing `job-radar-dev` Compose project and `--env-file .env`, do not remove/recreate its volume, keep notifications off, verify matcher true, and inspect a freshly persisted 3–5 evaluation using only redacted fields. Keep production matcher false unless separately approved.


## 2026-10-15 — Standing autonomy and development matcher approval

- User instructed: “do whatever required without my permission, save context and put this rule in handover doc also.” They specifically approved matcher activation in isolated development. Routine/reversible project tasks may proceed without further per-step approval. Do not repeatedly ask for permission for the already-approved dev-only sequence.
- Keep model `gemini-3.5-flash-lite`, extraction call caps 3/source run and 20/day, Telegram/notifications off, LinkedIn off, production unchanged. Preserve ignored VM `.env` secrets, `M v2/config.json` and `.venv/`; never print secret values or raw job data. High-impact/destructive/out-of-scope steps remain bounded: no volume deletion, reset/clean, schema migration, credential rotation, production rollout/matcher, notification send/replay, or OS/Docker permission change without a safe scoped need.
- Live evidence currently: exact fresh cache hash/model/TTL candidate = required total-professional experience 3–5 years with 0.95 confidence and evidence; isolated bridge plus persistence writer passed in temporary DB; the existing live evaluation is still 1.0/no maximum because matcher had been false. The live matcher must now be enabled in dev and verified with actual persisted bounds/reasons. `job_evaluations` does not contain `jd_experience_source`; no schema change is required for this proof.
- Assistant cannot access the VM command line through the available tools. Therefore the runtime flag has not been changed from this session. The precise safe activation command is in `docs/JOB_RADAR_HANDOVER.md`; run it from `~/job-beeper-dev`, return only safe flags, health and sanitized status/evaluation output, and continue the already-authorized verification sequence without asking again.
- This update changes docs only; no tests, runtime actions or code changes this turn. CI status not independently verified. Production unchanged.


## 2026-10-15 — Dev matcher flag is true; health probe reset; diagnosis pending

- User's output confirms the intended dev `.env` setting was applied and the newly started container reports `GEMINI_MATCHER_ENABLED=true`, `GEMINI_EXTRACTION_ENABLED=true`. Telegram token/chat presence are false; `/data/config.json` flags show notifications disabled and LinkedIn disabled.
- Immediately afterward, `curl -fsS http://127.0.0.1:8001/health` reported `curl: (56) Recv failure: Connection reset by peer` and SSH disconnected. The shell aborted due to `set -e`; the redacted diagnostic was not executed. Need read-only container status, health/restart/OOM checks, sanitized logs and retry/backoff before deciding whether this was startup latency, an application/container failure or a VM/SSH drop. Do not assert live evaluation updated.
- The user's standing instruction authorizes routine reversible Job Radar work without repeated confirmation; the matcher activation itself was explicitly approved for isolated dev only. Continue diagnosis without another approval. Keep production unchanged, notifications off/credentials blank, LinkedIn disabled, and existing volume untouched. Preserve local `M v2/config.json` and untracked `.venv/`.
- No application code/schema change or tests this turn; documentation only. CI for the diagnostic remains unverified. The detailed handover now includes a copyable read-only command block: reconnect, inspect container state/restart/OOM and existing `/data` mount, print only sanitized log indicators, retry health in a shell without `set -e`, then run the already-committed redacted diagnostic if service is healthy. Do not restart again until state is understood. If recovery fails, roll back only dev matcher gate; require persisted expected bounds/reasons before calling this complete.


- Detailed handover follow-up commands were hardened after review: Docker state errors are represented as a presence boolean, application logs are never printed raw, log diagnostics emit only counts/booleans/exception class names, and the health check retries without shell-wide exit. This is documentation-only; actual runtime recovery remains pending VM output.


## 2026-10-15 — Dev matcher end-to-end persisted evaluation confirmed

- User-supplied runtime output after reconnect: `job-radar-dev` Up 14 minutes, running, restart count 0, exit code 0, not OOM-killed/restarting, no container error; current named volume `job-radar-dev_radar-dev-data:/data` unchanged. Effective extraction/matcher are both true, Telegram creds absent, notifications disabled, LinkedIn disabled. The bounded retry health result is OK, version 2.0.0, one enabled/configured source and no source error.
- The redacted diagnostic now verifies exact current input hash, model match, successful fresh cache age 3008s (<30-day TTL), job last seen 616s ago, required total-professional scope, 3–5 years, confidence 0.95, exact evidence present and range bound present. The LIVE `job_evaluations` row has min=3.0/max=5.0, bounds-match=true, one reason and experience-reason-present=true. Sandbox bridge/persistence also passes. Source DB remains read-only/unmodified for this diagnostic; no Gemini API calls or notifications were made. Schema still does not persist `jd_experience_source`.
- The transient connection reset recovered without an application restart during the read-only retry. Mark the prior pending-health item as resolved; no need to rerun that same diagnostic unless the service changes/fails again.
- Next execution plan: Claude Code should connect from the user's local Windows machine using the user-provided SSH identity; directly run VM commands and gather results, so the user is not the routine command/output messenger. Read these two handovers and `docs/JOBBEEPER_REFERENCE.md` first; follow its rollout gates. Run safe tests on the current checkout, inspect status/branch/HEAD, preserve local `M v2/config.json` and `?? .venv/`. Validate canonical opportunity, ledger, API and dashboard consistency with notifications disabled. Then add/verify source improvements one at a time: first Greenhouse stale-publication/freshness guard and GET-only two-poll single-board canary (do not enable source globally/production based only on canary); then Ashby, Lever, SmartRecruiters separately; then source-health observability; then prepare a reviewed promotion PR. No Telegram delivery test, alert replay, production rollout or volume/DB deletion.
- Standing autonomy granted 2026-10-15 remains: routine in-scope reversible steps need no repeated confirmation. Pause/report before destructive/security-sensitive actions, production cutover, any real notification or changes that violate the stated safety boundaries. Report material blockers to user early, and keep both handovers updated/re-fetched every turn with evidence, changed paths, tests/CI, deployment state, next action and continuation prompt.

- Current-state correction: the first health connection reset was subsequently shown to be transient. Latest follow-up output includes a successful bounded health check and live persisted bounds/reason verification; rely on the latest 2026-10-15 handoff, not the superseded pending-diagnosis note in the earlier chronological entry.


## 2026-10-16 — Claude Code/orchestrator handoff and review queue

- Verified acceptance state: the user's latest output confirms the dev matcher end-to-end experience evaluation for one current-hash job. Health recovered; matcher/extraction true, notification credentials absent/notifications disabled, LinkedIn disabled, existing dev volume retained. Live `job_evaluations` now has min=3.0/max=5.0 and an experience reason. The diagnostic was read-only and made zero Gemini API calls or notifications. Provenance is transient (`jd_experience_source=gemini_verified`); schema does not persist this marker. This does not establish end-to-end Telegram delivery, intentionally not tested.
- New authoritative detailed worksheet is in `docs/JOB_RADAR_HANDOVER.md` under “Claude Code execution plan, status, and independent review worksheet” (2026-10-16). It gives direct Windows SSH instructions, separates complete/incomplete milestones, prioritizes implementation, lists Q1–Q10 for Claude Code to answer in place, and includes the independent ChatGPT Orchestrator review checklist and standard per-work-unit report structure.
- Claude Code's requested connection is `ssh -i "C:\\Users\\avibh\\Downloads\\ssh-key-2026-10-07.key" ubuntu@130.210.27.197`; key must remain local and must not be printed/copied/committed. Claude should run routine commands/tests and diagnostics directly, not make the user mediate. ChatGPT independently reviews pushed answers, source diffs/PRs, test/CI evidence and runtime summaries; it should not rubber-stamp Claude's self-review.
- Required next step: Claude fills in the ten questions under `CLAUDE RESPONSE` in the detailed handover, citing file paths/functions, commits/PRs, tests and observed VM outcomes; pushes to `v2-live-radar`; and re-fetches both handovers. The next ChatGPT session reviews the updated document against source and actual evidence, writes findings under “Orchestrator review checklist”, then updates both handovers.
- Goal alignment guardrails: no stale/unknown posting timestamp may be treated as fresh (never substitute discovery time for posted time); Greenhouse needs GET-only, two-poll, one-board dev canary and old-job/duplicate/unknown-timestamp checks before source activation. Add sources one at a time with stable IDs, timestamps, backoff, dedupe and useful-yield metrics. Persisting `jd_experience_source` is a proposal requiring justified design/review, not an automatic migration. Validate ledger/API/dashboard consistency with delivery disabled. Do not promote or cut over production, add real Telegram credentials, send/replay alerts, or delete volumes as routine actions.
- Current branch is `v2-live-radar`; GitHub head observed before these worksheet changes was `df807042e52d737856441174df49b3b93609f205`. New documentation commits should be verified on GitHub and preserve development/production separation. Keep detailed history; newest dated handoff supersedes older next-task instructions.


- 2026-10-16 documentation verification: `docs/JOB_RADAR_HANDOVER.md` is the shared source for Claude Code's Q1–Q10 response worksheet and the ChatGPT Orchestrator review checklist. Claude should answer in place, push to `v2-live-radar`, and preserve the original prompts; next ChatGPT independently reviews the answer against live source/CI/PR/VM evidence and appends findings. Detailed handover metadata/authoritative heading were corrected in commit `6adf5a93cd1152393e6d665fb2854947b581b238`. No runtime/source-code change or test was made for that documentation correction.


## 2026-10-16 — ChatGPT direct-GitHub workflow

- Claude Code is not working; ChatGPT will make code/doc commits directly to `v2-live-radar`. User runs SSH commands in the dev VM and shares redacted output; do not claim VM access.
- Added a temporary-DB regression test in `v2/test_radar.py`: `test_canonical_evaluation_ledger_and_dashboard_api_stay_consistent_when_delivery_disabled`. It checks one Naukri job's canonical identity, persisted evaluation/reasons/experience, notification-ledger pending decision while notifications are disabled, and API/dashboard-facing consistency without delivery.
- Code commit: `bb88885698316b70dcb7b4319aad9d345041e710`. The test has not yet run; CI is unverified. No runtime, app logic, config, schema, production, or notification changes.
- Next: inspect VM branch/status/local HEAD and remote HEAD, fast-forward only if clean/safe, then run the focused test plus existing canonical/ledger tests. Preserve `M v2/config.json`, untracked `.venv/`, and the existing dev data volume. Stop on divergence or overwrite risk; no reset/clean, volume deletion, production cutover, or Telegram send/replay.


## 2026-10-16 — Greenhouse freshness regression fix (VM-confirmed focused tests)

- A first fix changed `_alert_age_timestamp` to require Greenhouse `source_posted_at`, but two tests still failed because `refresh_notification_decisions` treated a missing age timestamp as fresh. This was a real defect in the downstream predicate, not a stale checkout: VM output showed both regression tests failing after commit `a977d8f`.
- Follow-up commit `dba073683bf96c89f9f2342fd731fbee8c5daf48` updates the predicate so Greenhouse freshness requires a non-null timestamp within `max_age_hours`. Non-Greenhouse sources retain existing behavior.
- User fetched/fast-forwarded to `dba0736`; all four focused Greenhouse tests passed (`Ran 4 tests in 0.288s — OK`). Full suite is **pending**, so do not describe the whole test suite as passing yet.
- No schema/config changes, Docker rebuild/restart, production cutover, real notification delivery, or volume deletion occurred. Preserve VM-local `v2/config.json`, untracked `.venv/`, and `job-radar-dev_radar-dev-data:/data`. Notifications remain disabled.
- **Next:** run `./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py'` on the VM and return its full output plus sanitized branch/HEAD/status. Then review `v2/greenhouse_canary.py` and its acceptance criteria; no canary run or source activation until that review establishes safe scope and explicit pass/fail criteria.

## 2026-10-16 — Greenhouse canary timestamp-quality diagnostics (verification pending)

- Added timestamp-quality diagnostics to the read-only two-poll Greenhouse canary: each snapshot counts postings with a timestamp within 72 hours, stale timestamps, missing timestamps, malformed timestamps, and future timestamps. This is a diagnostic enhancement only; it does not create an automatic pass/fail decision.
- Test-first commit: 7f89f0f99f37bfd1cddff7eadc6a720db4d0d8c0; implementation commit: 53a799e53bcfced95c98a3cde26b49624ab1926a. Files: v2/test_greenhouse_canary.py, v2/greenhouse_canary.py.
- Tests and CI for this increment are pending/unverified. The GitHub combined-status query returned no status entries. No canary network calls were made.
- Greenhouse remains disabled; notifications remain disabled. No DB/schema/config change, Docker rebuild/restart, production change, volume operation, or real notification occurred.
- Next: fetch latest branch, run python -m unittest v2.test_greenhouse_canary and the full V2 unittest discovery command, then report the exit codes and current HEAD. Preserve local v2/config.json, .venv/, and the existing named dev volume. Do not execute the live canary or rebuild Docker in this verification step.

## 2026-10-16 — Experience parsing / Gemini review-gate fix (verification pending)

The experience bug is now the priority over additional sources/features. Review of `v2/radar.py` found two actionable defects: generic “N+ years of X experience” could win before explicit total/professional years later in the JD, and the Gemini review gate could skip generic regex-derived values as already known. Test-first commit `e99dbca7098af7689a636c076b179cd6347357ec` adds regressions; implementation commit `44c4cc0aebd194d7a9885216de5b8759a438ea79` adds explicit overall/total/professional/work precedence and a reliable-evidence helper for deciding whether Gemini review can be skipped. Tests/CI are pending VM confirmation.

Do not assume the LLM is active in production merely because the code exists. The runtime must have both `GEMINI_EXTRACTION_ENABLED` and `GEMINI_MATCHER_ENABLED` enabled for Gemini to affect matching, and a cache row must match the exact current job-description hash, configured model and TTL, with required overall-professional scope, verbatim evidence and confidence >= 0.85. Check only whitelisted flag/revision/health summaries; never print secrets or raw job payloads.

Architecture direction: platform-specific parser/normalizer adapters (LinkedIn, Naukri, Instahyre, Greenhouse, Ashby) should own each source's fields, HTML/JSON shape, experience extraction and provenance. They should emit a shared canonical job contract; common matching, deduplication, evaluation ledger, API/dashboard and notification policy remain shared. Start with in-process modules, not separately deployed microservices. Preserve VM-local `v2/config.json`, `.venv/`, and the named dev DB volume. No production rollout, real notifications, schema migration or Docker operation in this increment.


## 2026-10-16 — Dev Gemini key environment-file resolution (verification pending)

- VM evidence: development container rebuilt from the current v2-live-radar checkout and now contains the expected v2/radar.py SHA-256 c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2. Health recovered after a brief startup connection reset; /health returned OK, and the existing job-radar-dev_radar-dev-data:/data mount remains intact.
- Current root .env has populated GEMINI_API_KEY, GEMINI_EXTRACTION_ENABLED, and GEMINI_MATCHER_ENABLED. The running container reports the Gemini key empty/unset. The Compose file maps GEMINI_API_KEY from variable substitution, but Compose was invoked without an explicit --env-file .env, and the resulting effective config reported the key empty. Likely env-file resolution/interpolation issue; verify via an explicit root env-file path without printing values.
- v2/docker-compose.dev.yml deliberately sets Telegram token and chat ID to empty strings. Keep those values blank; never add the root .env as a container env_file because it could inject unrelated credentials. Use root .env only for Compose interpolation via --env-file /home/ubuntu/job-beeper-dev/.env.
- No secret value was printed or committed. No Telegram notification was sent. Production/other v2 project were not touched; the named dev DB volume was not deleted or recreated.
- Next action: run a filtered docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml config --format json check that prints only key-presence, Gemini flags/call limits, and that Telegram token/chat are blank. If safe and GEMINI_API_KEY is populated in the effective config, recreate only dev radar using the same --env-file argument, then verify health, key-presence only, and volume mount. Do not print raw config output, raw environment values, job payloads, or logs containing secrets.
- Evidence/confidence: high confidence that the current running container lacks the Gemini API key; medium confidence that explicit --env-file will resolve it, pending effective-config check. The service is currently healthy. Do not claim Gemini requests work until a safe runtime status check confirms key configured and the extraction path produces verified results.
- Cross-reference: docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, docs/JOB_RADAR_HANDOVER.md, and architecture guardrails in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-16 — Dev Gemini key injection applied; runtime verification pending

- User ran the filtered Compose interpolation check with the explicit root env file. Output: GEMINI_API_KEY=present; GEMINI_EXTRACTION_ENABLED=true; GEMINI_MATCHER_ENABLED=true; GEMINI_MAX_CALLS_PER_RUN=3; GEMINI_MAX_CALLS_PER_DAY=20; JOB_RADAR_TELEGRAM_BOT_TOKEN=blank; JOB_RADAR_TELEGRAM_CHAT_ID=blank. No secret values were shown.
- User then ran `docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --no-deps radar`; Compose reported `Container job-radar-dev Started`. This is evidence of the dev service start command completing, not yet proof that the running container received the key or is healthy.
- Next: perform read-only checks for container state/health, Gemini key presence only (never value), Telegram variables blank, and existing `/data` volume mount. Then inspect a safe status endpoint for extraction/cache counts without printing job titles, IDs, evidence, raw payloads or secrets. Do not trigger job processing, send/replay notifications, or touch the separate production-ish `v2` Compose project. Preserve VM-local `v2/config.json`, `.venv/`, and `job-radar-dev_radar-dev-data:/data`.
- No code changes, test run, production change, notification, DB/schema change or volume operation in this turn. CI status remains unverified. The only runtime action was the user-reported recreation/start of the isolated dev `radar` service with the explicit root env file.
- Overarching goal remains reliable multi-source discovery, normalization/deduplication, explainable matching, consistent dashboard/ledger and safe low-noise delivery. Cross-reference this handover, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md and architecture/rollout guardrails in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-16 — Dev Gemini key and service runtime verified; status endpoint next

- User-reported read-only VM output: container job-radar-dev is running, restart_count=0, health check is not configured in Docker metadata (health is checked via HTTP); runtime GEMINI_API_KEY=present, extraction=true, matcher=true, Telegram token/chat blank. /data is mounted from existing named volume job-radar-dev_radar-dev-data; /health returned status=ok, DB /data/jobs.db, Naukri error=null, jobs_seen=327, new_jobs=1. The user pasted a mangled retry loop but the health request succeeded; do not infer a Docker healthcheck exists.
- This confirms configuration injection and basic service health, but not yet a successful Gemini API call, successful fresh extraction/cache use, or correct preference matching. No processing endpoint was called, and no notification was sent.
- Next: call only the read-only GET /api/llm-shadow-status and print a strict whitelist of aggregate fields (enabled flags, api_key_configured, model, calls today, cache success/error counts); omit recent sample records and all job titles, IDs, evidence, raw payloads and secrets. If the status reports the key configured and cache/flags look plausible, decide whether an existing safe diagnostic can verify current cache/evaluation without network calls or notifications. Do not trigger polling or alert dispatch. Keep Telegram blank, preserve v2/config.json, .venv/, the named dev volume, and do not touch the separate v2 Compose instance.
- No code changes, tests, schema/config changes, production actions, notifications or volume operations this turn. CI remains unverified. Overarching goal remains reliable multi-source discovery, normalization/dedupe, explainable matching and safe low-noise delivery. Cross-reference docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, and architecture/rollout rules in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-16 — Gemini shadow-status counts verified; diagnostic next

- User-reported filtered GET /api/llm-shadow-status output: enabled=True, api_key_configured=True, model=gemini-3.5-flash-lite, calls_today=20, cache_successes=74, cache_errors=6. This confirms the status endpoint reports the key configured and the daily call counter at the configured 20-call cap; it does not by itself prove the latest extraction or experience matching is correct. Avoid any action that could cause additional Gemini API calls until the counter/reset semantics and current cache state are reviewed.
- Read-only diagnostic source reviewed at v2/gemini_experience_diagnostic.py (current branch file SHA 5347ab501372caaf344027fb6bba15c0f013d56; use actual Git blob SHA from repository metadata when needed). Its documented flow opens the source SQLite DB read-only, selects one fresh current job with a trusted exact-input-hash/model-matched successful cache entry, copies that candidate into a disposable temporary DB, and exercises the bridge/evaluation persistence only in that sandbox. The script reports aggregate/experience-bound diagnostics, makes zero Gemini API calls and triggers no notifications. Tests in v2/test_gemini_experience_diagnostic.py cover exact fresh trusted result, hash mismatch, expired cache, and skill-specific scope.
- Next action: run this existing diagnostic only against the isolated dev container/database, after verifying its container working directory/module path and the runtime config path. Share only its key=value diagnostic output; do not share raw database content, job titles/IDs, descriptions/evidence text, environment values or secrets. If it says not_verified, report reason_code and stop—do not trigger polling or extraction to manufacture a candidate.
- Runtime safeguards unchanged: keep Telegram credentials blank, notifications disabled, Gemini matcher shadow-only, production-ish v2 Compose untouched, and preserve /data volume job-radar-dev_radar-dev-data plus VM-local v2/config.json and .venv/. No code, test, config, schema, production, notification or volume changes were made this turn. CI remains unverified.


## 2026-10-16 — Read-only Gemini experience diagnostic candidate verified

- User-reported output from `sudo docker exec job-radar-dev python -m v2.gemini_experience_diagnostic`: `diagnostic_status=candidate_verified`; model `gemini-3.5-flash-lite`; source DB read-only and unmodified; 0 Gemini API calls; no notifications. Exact current-input hash matched; cache status `ok`; model matched; cache age 50,781 seconds within 30-day TTL; selected job last seen 49,543 seconds ago (within 24 hours). Trusted experience was `required` / `total_professional`, 5.0–10.0 years, confidence 0.95, with evidence present and range bounds present.
- Existing live evaluation row was present, bounds matched cache (5.0–10.0), and an experience/year reason was present. In disposable sandbox, bridge source was verified, bounds matched, evaluation row was written with matching bounds and one reason. `source_marker_in_job_evaluations_schema=False` is consistent with the design: the diagnostic uses the existing bridge and does not add a source marker to the live schema.
- Investigated `sandbox_alertability_experience_reason_present=False`: current `alertability_details()` intentionally returns `not a profile match` when there is no match and returns `Telegram notifications disabled` when notifications are disabled; otherwise it returns `passes match threshold and notification policy`. Alertability reasons are therefore policy outcomes, not a copy of the regular match reasons. The false experience-reason flag is not by itself evidence of a defect; in this diagnostic the regular evaluation experience reason is present. Do not change alertability or enable notifications based on this flag.
- Combined with the previously reported status endpoint (`calls_today=20` at configured daily limit, 74 cache successes, 6 cache errors), do not trigger extraction/polling just to gather more Gemini results. Keep extraction calls paused until the daily counter reset/limits are understood and the current result is reviewed. No production cutover, notifications, schema/database changes, volume operations, code edits, or tests were performed this turn. CI remains unverified.
- Next safe step: inspect aggregate shadow-status and cache-error categories only if a dedicated endpoint/query can avoid exposing job titles, IDs, descriptions/evidence, raw payloads or secrets; otherwise stop here and retain this as a successful one-candidate validation. Keep Gemini matcher shadow-only, Telegram blank, the dev named volume intact, VM-local `v2/config.json` and `.venv/` untouched, and do not touch the separate production-ish Compose project.


## 2026-10-16 — Multi-provider LLM planning
- User asked whether Job Radar V2 can use Groq, Gemini, OpenRouter, and NVIDIA API access to reduce dependence on Gemini's limits, with API keys entered directly on the VM.
- Feasible in principle, but the current code is Gemini-specific: `v2/gemini_extractor.py` owns the Gemini endpoint, request schema, model-keyed cache and bounded-call settings; `v2/docker-compose.dev.yml` currently injects only Gemini variables. No multi-provider router exists yet, and no code/config/runtime changes were made for this request.
- Recommended architecture: a small provider adapter/router with explicit per-task provider/model allowlists, normalized structured output, shared validation, provider-specific rate/cost budgets, timeout/retry rules, cache keys including provider/model/prompt version, and safe fallback only for retryable provider errors. Do not broadcast every job to every provider; route one call at a time to avoid multiplied costs and duplicated data exposure.
- Keep all credentials VM-local via environment or a permission-restricted ignored secrets file; never commit keys, print them, include them in diagnostics, or paste them into chat. Verify each provider's model access, endpoint, rate limits, pricing and data-retention terms before enabling it. OpenRouter is an additional gateway to models, not an independent pool of guaranteed free capacity; provider quotas remain separate and can change.
- Preserve current safety posture while designing: Gemini shadow extraction/matching must remain non-authoritative until tested, Telegram notifications stay disabled, no production cutover, no database/schema migration, and no provider calls during this planning step. Add unit tests with mocked HTTP responses and a dry-run/config validation path before any live API test.


## 2026-10-16 — Multi-provider LLM router implementation
- Added `v2/llm_router.py` for Groq, Gemini, OpenRouter, and NVIDIA NIM JSON extraction, with ordered single-provider attempts, sanitized fallback errors, shared semantic validation, and cache identity derived from configured provider/model names (never keys).
- Integrated the optional router into `v2/gemini_extractor.py`; existing Gemini-only behavior remains when `LLM_ROUTER_ENABLED=false`. Development Compose now passes the router flags, provider keys/model IDs, and bounded job budgets. Router is disabled by default; `LLM_ROUTER_MATCHER_ENABLED=false` gates routed outputs from hard matching until explicitly validated.
- Added mocked tests in `v2/test_llm_router.py` and an integration-path test in `v2/test_gemini_extractor.py`. Tests have been added but were not executed in this environment; no live provider API calls were made, and CI/test results remain unverified.
- Added `docs/LLM_PROVIDER_ROUTER.md` with VM-local environment setup, provider endpoints, cache/budget behavior, security guidance, and staged rollout steps. `docs/JOBBEEPER_REFERENCE.md` also references the runbook.
- No API keys were added to GitHub. No VM environment, container, SQLite data, named volume, production service, or Telegram setting was changed. No database schema migration was introduced. Next: fast-forward the dev checkout, run focused and full unit tests, then enter provider keys and account-valid model IDs only in the VM-local `.env`; review sanitized configuration and tests before rebuilding only `job-radar-dev`.


## 2026-10-16 — Multi-provider router implementation checkpoint and continuation
- Implemented an initial opt-in provider router in `v2/llm_router.py` and integrated it into the existing shadow extractor in `v2/gemini_extractor.py`. Supported adapters: Groq, Gemini native API, OpenRouter, and NVIDIA NIM using their configured endpoints. OpenAI-compatible providers request JSON-object output; all results pass the existing extraction validator. Provider fallback is sequential, not parallel, and includes request/rate-limit, timeout, malformed JSON, and semantic-validation failures.
- Added development Compose variables for provider keys/model IDs, order, router toggle, separate job-per-run/day caps, and a matcher safety gate. Defaults are safe/off: `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`; Telegram credentials remain blank as before. No secrets are in source control.
- Added mocked router tests in `v2/test_llm_router.py` for provider configuration, cache identity secret exclusion, legacy identity behavior, request construction, rate-limit fallback, semantic-validation fallback, sanitized failures, and timeout handling. **Tests have not yet been executed**; do not claim test success until the dev VM runs focused tests and the full suite.
- Added `docs/LLM_PROVIDER_ROUTER.md` with environment setup, provider endpoints, budgets/cache behavior, key hygiene, safety defaults, and staged rollout. Updated `docs/JOBBEEPER_REFERENCE.md` with the new router/runbook pointers.
- Cache identity when router mode is enabled includes the ordered provider/model set but not API keys; daily counts are scoped to that identity. Existing SQLite cache is reused; no schema migration. The job cap bounds jobs, not total provider requests: fallback attempts can mean more than one request per job, so each provider's rate limits/pricing and a global budget must be considered.
- Important implementation limitation: the router is an initial integration, not production-validated. Provider-specific model IDs/account access, structured JSON compatibility, timeout/retry behavior, and real output quality remain unverified. Mocked tests cannot establish live provider availability, pricing, quota, or quality. Do not enter keys or enable router on the VM until the checkout is fast-forwarded and tests/review pass. Then configure secrets and account-valid model IDs in the VM-local development `.env` only; verify allowlisted fields without printing secrets.
- Current repository branch: `v2-live-radar`, repo `AvinashBhalla/job-beeper`. Recent implementation commits include router `dd464720f1697602d03fca1cab417a66aa63554b`, extractor integration `6ccd0f1578899da97674c6b79f6a4184240ced6a`, dev Compose settings `1d960515122fcdba5ea4f8ce80c771083d7b6441`, mocked tests `44b6621438ed13ebb9591d6bb74295569a85da5d`, validation-fallback support `ee20bda74ebceae15c083adb004e1e00570cb694`, active-cache budget scoping `87befd65b442e0443286a002f75122251c53fe76`, semantic-fallback test `10c20427370fa98d9eb14083dba9291644e98799`, matcher safety gate `c9d2cfe01dbed968c9ec8fe984cfdaa5a15bc114`, and Compose matcher gate `de700fc64cf67030174c16f99f16a6f7418e1aee`. The runbook commit is `299a6f2513f54df173c40cc74ec2c80a50408619`; subsequent documentation commits may follow.
- Next steps: (1) review current router/extractor code for correctness and run focused tests, (2) fix all failures and run the full `v2` unittest suite, (3) inspect final diffs and document test results, (4) only then provide safe VM commands to fetch and fast-forward `v2-live-radar` without resetting/cleaning or overwriting local `v2/config.json`, `.venv/`, or the `job-radar-dev_radar-dev-data` volume, (5) configure keys locally after tests pass, (6) rebuild/recreate only `job-radar-dev` if explicitly needed, and (7) keep router matcher disabled and Telegram notifications disabled during shadow validation. Do not trigger live provider calls or job-processing endpoints during tests.


## 2026-10-16 — Multi-provider LLM router implementation checkpoint

### User request
The user asked to implement and document a multi-provider LLM fallback for Groq, Gemini, OpenRouter, and NVIDIA, with API keys to be entered directly on the VM after the code is pulled. The user now asks for a continuation prompt and for this handover/progress record to be updated.

### Changes pushed to `v2-live-radar`
- Added `v2/llm_router.py` (initial commit `dd464720f1697602d03fca1cab417a66aa63554b`, follow-up hardening `ee20bda74ebceae15c083adb004e1e00570cb694`). Supports sequential, configurable provider fallback for Groq, Gemini, OpenRouter, and NVIDIA NIM; sanitized error categories; bounded HTTP timeouts; JSON parsing; and optional shared semantic validation before accepting a provider result.
- Updated `v2/gemini_extractor.py` to optionally use the router when `LLM_ROUTER_ENABLED=true`; preserves legacy Gemini-only behavior when disabled. Cache identity reflects ordered provider/model IDs without keys, and daily cache-budget counting is scoped to that identity. Matcher bridge refuses router-produced cache by default unless `LLM_ROUTER_MATCHER_ENABLED=true` in addition to existing matcher gating.
- Updated `v2/docker-compose.dev.yml` with opt-in router variables, model IDs and key environment variables for Groq/OpenRouter/NVIDIA, ordered providers, per-run/per-day job budgets, and a matcher-disabled default. Telegram token/chat ID remain explicitly blank.
- Added `v2/test_llm_router.py` with mocked configuration, parsing, fallback, semantic-validation, timeout, and secret-redaction tests. These tests have NOT been executed in a real VM or CI as part of this work; do not claim they pass.
- Added `docs/LLM_PROVIDER_ROUTER.md` with VM-local configuration, endpoints, safety defaults, testing/pull instructions, budget caveats, and staged rollout guidance.

### Current commit trail
- `dd464720f1697602d03fca1cab417a66aa63554b` — add router
- `6ccd0f1578899da97674c6b79f6a4184240ced6a` — integrate router into shadow extraction
- `1d960515122fcdba5ea4f8ce80c771083d7b6441` — Compose environment settings
- `44b6621438ed13ebb9591d6bb74295569a85da5d` — initial router tests
- `ee20bda74ebceae15c083adb004e1e00570cb694` — fallback on semantic validation errors
- `87befd65b442e0443286a002f75122251c53fe76` — scope daily cache budget/status to active model identity
- `10c20427370fa98d9eb14083dba9291644e98799` — semantic-invalid-output fallback test
- `c9d2cfe01dbed968c9ec8fe984cfdaa5a15bc114` — keep router results out of matcher by default
- `de700fc64cf67030174c16f99f16a6f7418e1aee` — Compose matcher gate
- `299a6f2513f54df173c40cc74ec2c80a50408619` — router runbook

### Important status and constraints
- This is repository code, not a verified working deployment. No VM pull, test execution, Docker rebuild, live provider API call, database write, schema migration, or notification was performed in this implementation turn.
- Current defaults are safe/off: `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`; the router must be explicitly enabled in the development VM environment after tests pass. Do not ask the user to share any API key in chat.
- The current VM may have local modifications to `v2/config.json`, untracked `.venv/`, and a named volume `job-radar-dev_radar-dev-data`; preserve them. Do not use `git reset`, `git clean`, destructive checkout, or volume removal. Only update the isolated development service `job-radar-dev`, never the separate `v2-radar-1` project.
- Keep Telegram credentials blank and notifications disabled. Do not run endpoints that process jobs just to trigger calls. No further Gemini calls should be made during initial validation; previous status showed the Gemini daily counter at 20.
- Test quality gates before enabling: run focused tests `./.venv/bin/python -m unittest v2.test_llm_router` and relevant extractor tests, then the full suite `./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py'`. First check current tree/status and fetch updates safely. If any tests fail, fix and document before rebuilding.
- After tests pass, user can add keys/model IDs locally in `/home/ubuntu/job-beeper-dev/.env`; verify only allowlisted booleans/provider names/model IDs and key-present booleans, never echo values. Recreate only development container using `sudo docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build --no-deps radar` only after confirming tests and intended config; do not run this yet.
- The current router's daily/run budget is a job budget, not a per-provider request/token quota; fallbacks can make more than one request per job. Provider account billing/rate limits still apply. Model IDs and endpoint compatibility must be checked for the user's actual accounts before live smoke tests.
- Follow-up review should inspect code for integration issues, run mocked tests, then verify status. Specifically ensure provider-specific errors never leak raw response content, strict extractor validation is used as the router validator, the cache model identity behaves correctly, and the existing extraction job cap cannot exceed the intended budget. Do not enable routed matcher until a separate quality review approves it.

### Next actions
1. Continue from the latest `v2-live-radar` branch and re-read the latest versions of the handover, knowledge-transfer, reference, and router runbook docs before acting.
2. Review the router/extractor integration and run the focused mocked tests; fix any issues and record exact outcomes.
3. Give the user safe, non-destructive VM pull commands only after confirming test results and checking how to preserve local changes.
4. Ask the user to enter keys directly in the VM only after code/tests are ready; never request keys in chat.
5. Keep all runtime tests development-only, shadow-only, no schema migration, no production cutover, and no Telegram sends.


## 2026-10-16 — Multi-provider router code review and CI result
- Re-read current branch code/docs and reviewed signatures, strict validation, provider request shapes, cache identity, log/error sanitation and rollout flags at `b635b8969247c483bdfae7c2c9d0cb9a38895a61`.
- CI evidence: [V2 CI run 38934696862](https://github.com/AvinashBhalla/job-beeper/actions/runs/38934696862) succeeded on the exact branch head. Its full `unittest discover -s v2 -p 'test_*.py' -v` step passed. The separate focused router command was not run in this environment; there is no VM/shell execution access here.
- Review findings: strict extractor validation is wired as the semantic fallback validator; legacy Gemini-only call path remains when router flag is false; cache identity contains ordered provider/model IDs but not keys; routed data is hard-matcher gated by default; no raw provider body is logged by the router. Provider live compatibility remains unverified.
- Known coverage gap: add direct mocked request/response tests for native Gemini, OpenRouter and NVIDIA, malformed/empty response, request connection error, 5xx, all-provider failure, and fallback-attempt budget accounting. The run/day controls are job/cache-entry bounds, not request/token/spend quotas; fallback can produce multiple requests per job.
- No new code commit, no VM pull/test, no environment/API/DB/volume/deployment change, no Gemini calls, and no notifications occurred during this review.
- Next: use read-only git status/branch/HEAD/fetch on `/home/ubuntu/job-beeper-dev`, assess local diffs, fast-forward only if safe, run focused plus full tests in that checkout, then configure provider keys/model IDs only in its ignored VM-local `.env`. Keep router disabled until results are reviewed, matcher gate false, Telegram blank and notifications off. Never reset/clean or remove volumes.


## Historical handoff — 2026-10-28 (superseded by router hardening and CI results appended below)
- User asked for a reusable prompt for the next ChatGPT conversation and requested that progress/learning be captured in the handover documents. Re-read the latest versions of all three project reference docs and the current router, extractor, dev Compose file, tests, and router runbook before updating this note.
- Current documented branch head is `b635b8969247c483bdfae7c2c9d0cb9a38895a61`; CI run [38934696862](https://github.com/AvinashBhalla/job-beeper/actions/runs/38934696862) is documented as successful for full V2 unittest discovery on that exact head. This is CI evidence only; focused tests and full suite have not yet been run on the user's VM. Do not claim live provider compatibility or VM validation.
- Current implementation includes `v2/llm_router.py`, integration in `v2/gemini_extractor.py`, optional provider environment variables in `v2/docker-compose.dev.yml`, mocked tests in `v2/test_llm_router.py`, and `docs/LLM_PROVIDER_ROUTER.md`. Providers are Groq, Gemini, OpenRouter, NVIDIA, tried in configured order with shared strict extraction validation and sanitized failure logging. Router defaults off; routed matcher gate defaults off; Telegram remains disabled. No DB schema migration was added.
- Key learning: `LLM_MAX_JOBS_PER_RUN` / `LLM_MAX_JOBS_PER_DAY` limit jobs/cache entries, not aggregate HTTP requests, tokens, or spend. A fallback can call multiple providers for one job; provider billing/rate limits remain in force. Cache identity is the ordered configured provider/model list and excludes keys. API keys and model IDs must be entered/verified on the VM only.
- Remaining coverage gaps documented by review: direct mocked native Gemini, OpenRouter and NVIDIA response variants; malformed/empty response; connection error; 5xx; all-provider failure; and fallback attempts versus job budget. The next model should inspect latest files and run/review CI or local mocked tests before giving VM instructions, then fix issues and update these docs with exact test results.
- Safe next VM step, after reviewing current status: read-only `git status --short`, branch, HEAD and fetch for `origin/v2-live-radar` from `/home/ubuntu/job-beeper-dev`. Preserve VM-local modified `v2/config.json`, untracked `.venv/`, ignored `.env`, and named volume `job-radar-dev_radar-dev-data`. Do not reset/clean/stash blindly or touch the separate production-ish Compose project. Only use `git pull --ff-only` if the tree/branch/ahead-behind state proves it is safe.
- Do not ask the user to paste keys in chat. Do not enable the router, run job-processing endpoints, trigger Gemini/provider requests, rebuild/restart containers, change DB/volume state, enable matcher use, or send notifications until test results and an explicit staged rollout are agreed. If safe to proceed after tests, give exact VM-local secret-entry steps and verify only allowlisted booleans/provider names/model IDs, never secret values.


## 2026-10-28 — Multi-provider router hardening and test verification

- Fixed a log/error redaction edge case in v2/llm_router.py: arbitrary ValueError strings that merely started with invalid_ are no longer treated as safe codes. An explicit allowlist is used; unexpected validator messages become invalid_result.
- Expanded mocked coverage in v2/test_llm_router.py for native Gemini, OpenRouter and NVIDIA request/response formats, malformed/empty content, HTTP 5xx, connection failure, all-provider failure and sensitive-data redaction. Added a mixed-provider extractor test in v2/test_gemini_extractor.py confirming one job slot may incur multiple fallback HTTP attempts.
- Commits: code/tests db331cac992a0d433bad119ae3b1fe483831f71e; dedicated CI focused-test stage edc5b92404f94c2de84381407c7ed103bdda5f60 in .github/workflows/v2-ci.yml.
- CI: [#40651350087](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651350087) — full V2 suite 134 tests, 12.864 seconds, OK. [#40651562286](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651562286) — focused router/extractor suite 32 tests, 0.061 seconds, OK; full V2 suite 134 tests, 17.009 seconds, OK. All provider HTTP responses were mocked; CI made no live provider calls.
- Updated docs/LLM_PROVIDER_ROUTER.md to keep its example disabled by default and list exact test commands. Router and routed matcher remain off pending user-approved staged configuration. Telegram remains disabled.
- No VM/production-like checkout, environment, container, database, volume or notification state was changed. No live API request, secret entry or schema migration occurred.
- Remaining risk: the job caps do not bound total provider requests/tokens/spend, and provider account/model compatibility or output quality remains unverified.
- Next action: inspect and fetch on the VM using git status --short, branch, HEAD, git fetch origin v2-live-radar, git status -sb, git rev-list --left-right --count HEAD...origin/v2-live-radar and git diff --name-only HEAD..origin/v2-live-radar. Preserve local config, .venv/, .env and the named volume; assess the output before any fast-forward.


## 2026-11-05 — Product reverse-engineering kickoff (current)

- **User goal:** investigate public/accessible behavior of JobBeeper and Uplers HAPPPY, then design a personal multi-source job-discovery and referral-intelligence system. The current scope is product research and evidence collection; no implementation or deployment change is authorized by this note.
- **Repository evidence:** inspected `v2-live-radar` at `ef73b3c8bee77b14c4b0ebd7ac319ab7cf94fc7a`. GitHub Actions V2 CI run [#40651863587](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651863587) succeeded on that exact head on 2026-10-28. This is CI evidence, not Oracle VM deployment evidence. `main` is at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` and is behind the active V2 branch; continue V2 work from `v2-live-radar`.
- **Initial LinkedIn latency diagnosis (code-based estimate):** current tracked config has 4 LinkedIn queries × 4 locations = 16 first-page query/location targets. `linkedin_collect` scans up to 2 targets per scan and scheduler target is 180 seconds, so a complete uninterrupted fast-lane rotation is nominally 8 × 180 = 1,440 seconds (24 minutes). This is a theoretical scheduling calculation, not measured live latency. The HTTP wrapper paces calls at least 4 seconds apart, uses a 25-second timeout, and applies a global escalating cooldown after HTTP 429; fallback cooldown starts at 300 seconds and caps at 1,800 seconds while honoring Retry-After. Do not reduce intervals or increase request pressure before measuring source-specific yield and rate limits.
- **Source inventory:** collector registry contains LinkedIn, Naukri, Instahyre, Greenhouse and Ashby. Tracked `v2/config.json` enables LinkedIn/Naukri and disables the other three; isolated `v2/config.dev.json` enables Naukri only and notifications off. Treat these as repository configuration only: runtime `/data/config.json` may override production settings and must be checked on the VM before any state claim.
- **Observability gap:** current `/api/latency-summary`, `/api/source-status` and `/api/dedupe-candidates` enumerate LinkedIn, Naukri, Instahyre and Greenhouse but omit Ashby despite Ashby being in `COLLECTORS`. Verify the intended API contract and add regression tests before changing it.
- **Runtime status:** Oracle container/commit, effective runtime config, source last-success/errors, actual LinkedIn cooldown history and Telegram delivery timings have not been verified in this turn. The checked-in `source_state.json` is an old static snapshot and is not live health evidence.
- **REA research:** official project is [morluto/rea](https://github.com/morluto/rea), MIT-licensed. Current docs require Node.js 22.23.4+, 24.22.1+ or 26.12.1+. It supports passive website observation by attaching to a user-owned Chrome-family browser via CDP on loopback and offline inspection of HAR 1.2 captures. REA is not a general browser automation surface. Use a dedicated browser profile; do not expose the debugging port beyond loopback. Redact HAR cookies, authorization headers, tokens, inbox content and other personal information before sharing.
- **Next actions:** (1) verify local Node/npm versions; (2) install latest REA using `npx rea-agents@latest setup`, review its exact setup plan, select the intended coding agent and restart it; (3) launch a separate Chrome profile with CDP bound to `127.0.0.1:9222`; (4) inspect JobBeeper public/accessible pages, capture passive page/script/network metadata, and export a sanitized HAR; (5) separately capture HAPPPY workflow/consent screens; (6) request read-only Oracle runtime diagnostics before any code/deploy work.
- **Safety and scope:** inspect only publicly accessible or account-authorized product behavior. Do not attempt to access private SaaS backend source, bypass authentication/access controls, evade LinkedIn rate limits, automate prohibited LinkedIn activity, or disclose cookies/session tokens. Referral workflows should use authorized data providers and human-approved account activity.
- **Code/config/runtime changes:** none. No collectors were triggered; no VM command, container restart, DB write, schema migration, source setting, Telegram notification, provider API call or deployment was performed.


## 2026-11-05 — REA setup host clarification

- User ran `node -v` and `npm -v` at the Oracle prompt `ubuntu@job-radar:~$`; reported Node.js `v12.22.9` and npm `8.5.1`.
- This is the Oracle application host, not the Windows workstation selected for REA/browser investigation. Do not upgrade Node on Oracle just to install REA; the existing Job Radar V2 backend is Python/FastAPI and does not need this change for the planned investigation.
- Next action: on the Windows development workstation, open PowerShell (not the SSH terminal) and run `node -v; npm -v`. REA requires Node.js 22.23.4+, 24.22.1+ or 26.12.1+. Then follow the reviewed local setup instructions. The previously remembered Windows Node version (26.7.0) is historical and must be rechecked.
- No VM package installation, Node upgrade, collector run, service restart or application change was performed.


## 2026-11-05 — Windows REA Node prerequisite

- User's Windows PowerShell reports Node.js `v27.0.0-alpha.0.0.0`, npm `12.1.0`, executable `C:\\Program Files\\nodejs\\node.exe`. This is a prerelease and is unsupported by REA.
- Current REA docs require Node 22.23.4+, 24.22.1+ or 26.12.1+ and explicitly exclude prereleases. REA's Windows getting-started guide recommends installing Node 24 LTS with `winget install --exact --id OpenJS.NodeJS.LTS`; see https://morluto.github.io/rea/get-started/.
- Recommended next step: in a NEW Windows PowerShell session, run `winget install --exact --id OpenJS.NodeJS.LTS`. Reopen PowerShell and verify `node -v`, `npm -v`, and `where.exe node`. Do not uninstall the currently installed Node 27 alpha or manually delete `C:\\Program Files\\nodejs` if winget reports a conflict; capture the exact installer error and assess a version-manager route instead.
- Do not run the REA installation from the Oracle SSH session; no Node change is required on Oracle for the Python/FastAPI app.
- No Windows or Oracle installation was performed by the assistant; no application code, server runtime or source config was changed.


## 2026-11-05 — JobBeeper public homepage HAR and runtime API findings

### Evidence collected
- User supplied a sanitized Chrome DevTools HAR from the isolated REA Chrome profile, capturing a public homepage load and a short idle window. Browser: Chrome 156.0.8078.80. Capture starts 2026-11-05T10:56:51.520Z; first API activity follows shortly after page load.
- HAR contains 50 HTTP entries: 47 to jobbeeper.com, 1 Google Tag Manager script load, and 2 Google Analytics collection POSTs. Statuses: 46 x 200, 2 x 401 (unauthenticated session lookups), 2 x 204 (analytics). No failed static asset responses were observed.
- The sanitized HAR contains no Cookie/Authorization/Set-Cookie headers and no request postData. Do not reproduce public plan response payment-routing values in documentation, tickets, code or reports. The /api/auth/plan response included UPI routing fields; values intentionally omitted.
- Request headers show X-Client-Timezone: Asia/Calcutta. The HAR was captured with DevTools Disable cache and Preserve log enabled; request Cache-Control: no-cache / Pragma: no-cache therefore should not be used to infer normal browser cache behavior.

### OBSERVED — runtime HTTP endpoints
- GET /api/public/pulse -> 200, application/json, response time approx. 84 ms on first request and 99 ms on the second.
- GET /api/auth/plan -> 200, application/json.
- GET /api/auth/plans -> 200, application/json.
- GET /api/auth/user/me -> 401, response body reports missing authorization token.
- GET /api/auth/me -> 401, response body reports missing authorization token.
- The two 401s occurred in an unauthenticated public homepage session. No authenticated/private account behavior was exercised.
- /api/public/pulse response headers included Cache-Control: public, max-age=60. The auth plan endpoints returned private/no-store cache directives.
- /api/public/pulse was requested twice, approximately 14.5 seconds apart. This is only two requests and must not be described as a proven 15-second polling interval.

### OBSERVED — public pulse response shape and snapshot
- JSON top-level fields: generated_at, locked, open, stats, sufficient, window.
- locked items in the captured response included age_minutes, found_after_minutes, location, source and title; captured locked records did not include company or share_path.
- open items included age_minutes, company, found_after_minutes, location, share_path, source and title.
- Snapshot had 3 locked and 3 open records. Locked sample ages were 2–3 minutes; open sample ages were 362–363 minutes. open records had share_path values; locked records had found_after_minutes null and no share_path in the captured objects.
- stats snapshot (time-bound, not a stable product constant): companies_tracked=79,469; jobs_24h=77,742; jobs_last_hour=2,839; jobs_week=452,780; median_alert_minutes=10; portals_watched=89,905; share_delay_hours=6. Response window was "hour" and sufficient=true.
- generated_at values of the two pulse responses were approximately one minute apart even though the two client requests were approximately 14.5 seconds apart. Preserve as observed; generation/cache cadence is not yet explained.
- The captured record structure is consistent with the public-page statement that newer jobs are subscriber-first and held from the public feed for six hours. Treat this as a well-supported inference, not proof of the private subscriber delivery path.

### OBSERVED — static frontend code from HAR/REA bundle analysis
- API client module api-B1bIDMMX.js defines API base path /api and a fetch wrapper using credentials: include. It adds X-Client-Timezone from Intl.DateTimeFormat().resolvedOptions().timeZone; non-GET methods attach X-CSRF-Token from the jn_csrf cookie. Static code contains a 401 refresh fallback trying POST /auth/user/refresh and then /auth/refresh before retrying unless noRetry is set. Those POST refresh requests were NOT observed in this unauthenticated HAR; this is source-code evidence only.
- LiveJobFeed-DGhOmHyc.js calls the API client with GET /public/pulse. Its hook default interval is 90,000 ms; it fetches immediately on mount and has a visibilitychange handler which fetches again when document.visibilityState becomes visible. Thus, the 14.5-second separation in the HAR must not be interpreted as the normal polling interval; a visibility event or another trigger is plausible but the exact cause was not captured. Confirm with a longer stable Network recording if needed.
- The LiveJobFeed component calculates/display-formats job ages client-side and uses stats from the pulse response (jobs_last_hour or jobs_24h depending on window, median_alert_minutes, portals_watched, companies_tracked).
- portalLabels-tSl-pka_.js contains labels for many ATS/source families including LinkedIn, Greenhouse, Ashby, Lever, Workday, SmartRecruiters, Darwinbox, SuccessFactors, iCIMS, Naukri, Cutshort, Instahyre, Hirist, Oracle Cloud Recruiting, Wellfound, Workable, PeopleStrong, Phenom, Eightfold, Zoho Recruit, Keka, Freshteam, Taleo, Avature, BambooHR, BrassRing, Jobvite, Breezy, Recruitee, Rippling, Teamtailor, UKG, LinkedIn Hiring Posts, X Hiring Posts and others. This is a frontend label registry, not proof that every listed integration is active or currently collecting.
- portalLabels module contains static code paths for GET /companies/platforms and fallback GET /auth/user/portals; neither request appeared in this HAR, so runtime behavior remains unverified.
- REA's static bundle analysis retained 29 script sources and parsed most sources, but the 293 KB index bundle exceeded REA's per-script deadline. The HAR itself includes the fetched JavaScript response bodies, enabling targeted offline inspection of specific bundles if required.

### INFERRED — architecture implications
- /api/public/pulse is a public, aggregate feed/statistics endpoint and should be treated separately from authenticated user/job preference APIs.
- Public job access is staged: records in locked are newer and omit company/link fields in the observed representation; open records are older and include company/share_path. The six-hour delay matches the product's public statement.
- The frontend API utility centralizes the /api prefix, credentialed fetches, timezone header, CSRF behavior for mutations and a refresh/retry path. Do not imitate refresh endpoints or private APIs; only use documented/public behavior in the user's own design.
- The 90-second LiveJobFeed interval is source-code evidence. Validate actual runtime cadence with longer recording and page-visibility controlled before using it as a performance benchmark.

### UNKNOWN / not established by this HAR
- No logged-in behavior, private user feed, saved preferences, Telegram delivery, alert rules or subscriber-first notification path was observed.
- No search/filter queries, company directory requests, job-detail API calls, pagination cursors or source-specific feeds were captured.
- No backend framework, database schema, ingestion architecture, collector schedule, deduplication mechanism or exact meaning of found_after_minutes has been established.
- The 401 auth lookups do not establish the complete authentication design.
- The HAR's two pulse requests do not independently establish the 90-second interval; static bundle source contains that interval, and a longer runtime test remains desirable.

### Next exact investigation step
- Continue read-only public investigation. Navigate the isolated Chrome profile to /browse/hiring-this-week and capture a sanitized HAR with Preserve log; examine actual browse API calls, response shape, filter parameters, pagination and job IDs. Then open one public /j/{id}-{slug} detail page and capture its requests.
- Do not sign in, change settings, submit applications, create alerts, automate interactions, or access private account data during this public investigation.
- No Job Radar application code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed as part of this research.


## 2026-11-05 — JobBeeper browse, company and public job-detail HAR findings

### Capture overview
- User supplied a sanitized Chrome DevTools HAR captured while navigating the isolated browser through the homepage, `/browse/hiring-this-week`, `/browse/company/domino-s`, and `/j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s`.
- HAR contained 137 HTTP entries across four page groups. 81 requests were to jobbeeper.com and 56 to Google-related hosts/services.
- Overall statuses: 92 x 200, 22 x 301, 12 x 404, 7 x 204, 4 x 401.
- JobBeeper-only statuses: 77 x 200, 4 x 401. The 4 JobBeeper 401s were unauthenticated homepage lookups to /api/auth/user/me and /api/auth/me; the public browse/company/job-detail documents returned 200.
- The 22 HTTP 301 responses were Google favicon lookup redirects (/s2/favicons); the 12 HTTP 404 responses were gstatic favicon lookups (/faviconV2), not JobBeeper application routes. The 7 HTTP 204 responses were Google Analytics /g/collect POSTs.
- HAR contains 4 page records: homepage, hiring-this-week, Domino's company page, and one Domino's job detail. The main public routes were navigated as distinct pages.
- The capture did not include Cookie, Authorization, Set-Cookie, Proxy-Authorization or X-API-Key headers. HAR response objects had MIME type and body size but no response body text for the public HTML documents. Do not infer HTML content from byte sizes alone.

### OBSERVED — public page routing and delivery
- `GET /` -> 200 text/html.
- `GET /browse/hiring-this-week` -> 200 text/html, response content size 85,920 bytes; document request about 580 ms. HAR page timing: onContentLoad ~869 ms; onLoad ~1,200 ms.
- `GET /browse/company/domino-s` -> 200 text/html, response content size 176,280 bytes; document request about 321 ms. HAR page timing: onContentLoad ~494 ms; onLoad ~687 ms.
- `GET /j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s` -> 200 text/html, response content size 67,639 bytes; document request about 198 ms. HAR page timing: onContentLoad ~339 ms; onLoad ~576 ms.
- The browse, company and detail pages each loaded shared assets: `/static/jobpage.js`, `/static/publicpage-theme.js`, and `/static/publicpage-ui.js`. The job detail page additionally loaded `/static/public-job.css`. CSS and JavaScript resources returned 200.
- Each of the four page paths (including homepage) had a document request and a near-immediate duplicate Fetch request for the same URL. The second request's initiator stack points to `https://jobbeeper.com/sw.js` at line 58 (HAR lineNumber 57), confirming service-worker involvement in the duplicate fetch. The service-worker script body was not captured, so cache strategy, navigation preload behavior and purpose of this duplicate are unknown.
- On the three browse/company/detail page groups, no same-origin JSON API endpoints appeared in the HAR. The only observed same-origin API JSON traffic in this HAR was on the homepage: `/api/public/pulse`, `/api/auth/plan`, `/api/auth/plans`, `/api/auth/user/me`, and `/api/auth/me`.
- The 81 JobBeeper requests included the homepage's SPA bundles and pulse/plan endpoints, and the separate public-page static assets. This appears to be a distinct public HTML page delivery path for browse/company/job-detail routes, but implementation boundary needs source/runtime confirmation.

### INFERRED — public browsing architecture
- Large HTML documents plus shared public-page JavaScript/CSS, with no observed JSON API calls on the browse/company/detail pages, are consistent with server-rendered HTML or content embedded in delivered HTML. This is not proven because the sanitized HAR omitted response bodies.
- The `/sw.js`-initiated duplicate Fetch requests indicate the service worker participates in navigation handling or follow-up fetch behavior. Do not label the strategy as cache-first, network-first or stale-while-revalidate without observing the service-worker source or controlled runtime behavior.
- The public browsing pages may use a different implementation path from the homepage SPA. The homepage uses hashed `/assets/*.js` modules and /api JSON endpoints; the public browse/detail pages load `/static/*.js` and larger HTML documents.

### UNKNOWN / not established by this capture
- Actual HTML text, job-card data, company metadata, job description fields, filters, pagination, page size, and application outbound URL are unknown because HAR response bodies were not included.
- No filter form submission, query change, next-page action, detail CTA click, logged-in flow, or private job preference behavior was observed.
- No backend route handlers, database schema, template system, service-worker caching policy, source collection schedule, job ingestion or deduplication behavior were established.
- No same-origin JSON API calls for browse/company/detail appeared in this capture. This does not prove that those pages never call APIs; lazy loading, user interaction, scroll-triggered activity or a different state may initiate additional calls.

### Next exact investigation step
- Use REA `inspect-web-page` against the currently selected public job-detail or browse page, after refreshing target discovery, with accessibility text enabled; this should capture actual visible labels and page structure without relying on HAR response bodies. Keep the page stable during the capture.
- Then inspect `/static/jobpage.js` and `/static/publicpage-ui.js` as public, loaded scripts using REA bundle/source observation. Avoid executing unknown page code outside the site's normal browser context.
- After page content is understood, test public filtering and pagination manually in Chrome while recording a sanitized HAR. Record which controls were used and compare URL/query changes and network requests. Do not sign in, submit applications, create alerts, or access private data.
- No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed during this capture or its analysis.


## 2026-11-05 — Public Domino's job-detail page inspection

### Capture identity and completeness
- User supplied REA `inspect-web-page` capture for target `545C6994ACD1807FE62AFF719D41E56C`, URL `https://jobbeeper.com/j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s`, page title `Delivery Driver(02202) - 1027 W Hunter St at Domino's — JobBeeper`.
- Observation window: 2026-11-05T11:10:21.605Z through 11:10:22.672Z (about 1 second). Accessibility capture enabled; network requests and script source capture were not included, and observation begins after REA attaches.
- DOM contains 623 nodes; accessibility tree contains 313 nodes. Three first-party scripts were observed: `/static/publicpage-theme.js` (2,842 bytes), `/static/jobpage.js` (2,651 bytes by script metadata; resource size 2,653 bytes), and `/static/publicpage-ui.js` (5,259 bytes). No source maps reported.
- DOM URL metadata exposes public internal links and login/signup redirect paths. Four URLs were excluded because destination origins were outside the approved origin policy; their actual destinations were not disclosed. Do not infer or attempt to recover excluded external destinations.
- Network request list was empty due attach-limited timing; this does not mean page has no network activity.

### OBSERVED — job-detail content and fields
- Public listing title: `Delivery Driver(02202) - 1027 W Hunter St`.
- Company: Domino's.
- Location: Logan, OH, United States.
- Summary metadata:
  - Work mode: `No` (retain literal source value; field semantics require further interpretation).
  - Employment: `Full-time`.
  - Listed: `Posted 9 hours ago`.
  - Source: `Smartrecruiters`.
- Role description section says: `Only a short excerpt is available here.` and `The full responsibilities and requirements may be missing.`
- A public link says `Sign in to open the original listing` and another page message says to sign in to open the employer's application link and track the application.
- Application panel has CTA `Log in to apply` plus `Create free account`. Public href for login includes redirect to `/user/job/28752345` and UTM attribution. Signup href includes `next=/user/job/28752345` and UTM attribution.
- No salary or explicit experience requirement was exposed in the captured public accessibility tree. This does not prove the original employer listing has no such information.
- Public page contains a `Copy job link` button and `Browse openings` link.
- Related section `More openings worth a look` says `6 roles` and lists six other Domino's public job pages. Examples include Assistant Manager, Customer Service Rep and Delivery Driver roles in US locations.
- Footer/header include Create an alert, Sign in, Get App, JobBeeper home, How it works and Pricing navigation.

### OBSERVED — promotional metrics displayed on this individual page
- `31 min`: from SmartRecruiters publishing this role to JobBeeper finding it.
- `14 min`: median time from a role going live to a subscriber being told.
- `6 hours`: subscribers had this role before this page existed.
- `76,954`: roles found in the last 24 hours.
- These are page-displayed claims / a captured snapshot, not independently verified measurements; the 24-hour count is dynamic and differs from the homepage HAR snapshot.

### INFERRED — public preview and conversion model
- Public detail page is deliberately incomplete: it exposes title, company, location, a few normalized fields, listing age/source and a short description excerpt, but directs unauthenticated visitors to sign in to view the original listing and employer application URL.
- The `/user/job/28752345` redirect path suggests authentication gates a user-specific job/application view, but authenticated behavior has not been tested.
- The related-jobs module appears to connect opportunities within the same company and includes six alternative postings on the detail page.
- The metric labels distinguish source publishing -> JobBeeper discovery -> subscriber notification -> public-page availability. These should be separate timestamps/stages in our own latency model; definitions and measurement methodology remain unverified.
- The page uses a separate public-page rendering path from the homepage SPA, based on server-delivered HTML and three standalone public-page scripts; exact backend implementation remains unknown.

### UNKNOWN / not established
- Full employer description, original application URL, pay, benefits, skills, experience requirements, qualifications and complete canonical job object are unavailable from this public preview.
- Values `Work mode = No` and exact field semantics need inspection in more job examples before defining enum mappings.
- No evidence whether job detail data is embedded in HTML, retrieved by hidden/lazy scripts, or assembled by a server-side template; response body was not captured in HAR.
- No actual click behavior for Copy job link, sign-in, create account, apply, create alert or related-job links was tested. No account was created and no application submitted.
- No logged-in private listing, subscriber alert, tracking workflow, or original employer ATS redirect was observed.
- Four external DOM destinations were policy-excluded. Their targets remain unknown and will not be bypassed.

### Implications for our own canonical job model
- Public/basic fields to model: title, company, normalized location, employment type, work-mode source value, source/ATS label, listed_at or source-listed display, discovered_at, description_excerpt, description_completeness/visibility, public_detail_url, canonical job ID, related-company jobs.
- Keep separate source-posted, discovered, subscriber-notified and public-release timestamps; don't substitute page display claims for system timestamps.
- Preserve unknown/null values explicitly; don't map `Work mode = No` to onsite or remote until validated.
- Keep source application URL separately from our own application redirect/tracking. Decide access policy independently; no need to replicate JobBeeper's account gate.

### Next exact investigation step
- Run REA `analyze-web-bundle` on the current public job-detail target (and then, separately, on a browse target) to capture/analyze the three first-party public-page scripts. Focus on jobpage.js and publicpage-ui.js. Record any data-field names, outbound URL handling, analytics events and UI behavior as static-code evidence, distinct from runtime observations.
- Next, inspect the `/browse/hiring-this-week` page accessibility tree to identify visible filters, cards, sort controls, pagination and empty states; then manually exercise one public filter or pagination control while recording a sanitized HAR. Do not access the original employer application URL or private account data.
- No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed.


## 2026-11-05 — Static analysis of public job-detail JavaScript

### Capture and parser result
- User supplied REA `analyze-web-bundle` output for public Domino's job detail URL `https://jobbeeper.com/j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s`.
- Three first-party scripts were observed and all three parsed successfully:
  - `/static/publicpage-theme.js` — 2,842 bytes; SHA-256 `fedefd1627cfacc80c2fb9cfd8129ec8b7af820162339880eb9c4cc44e6555c8`.
  - `/static/jobpage.js` — 2,653 bytes; SHA-256 `628090b59538f7d42ff1bad4b13d6f0b236a172acba0e3d65e4395b251471b0e`.
  - `/static/publicpage-ui.js` — 5,259 bytes; SHA-256 `fbd77391e95e9232cf8b5a382f97e58c7ed625f3a7b62306d0211d3518a813d4`.
- REA analysis completeness: 3 parsed scripts, 0 parse failures, 1,520 AST nodes visited. Static source analysis only; scripts were not executed by REA.
- Source-map fetching was not requested; no source-map findings can be inferred.
- Route inventory found zero route patterns and zero route occurrences within these 3 provided sources. This is not proof that no routes exist elsewhere.

### OBSERVED — static call candidate
- REA identified one low-confidence static endpoint candidate in `jobpage.js` at line 38, column 2: `/api/auth/user/me`, mechanism `call:fetch`.
- The exact static call candidate is a fetch to the current-user/session endpoint. This is consistent with the earlier HAR's unauthenticated request to `GET /api/auth/user/me` returning 401 when no authorization token was present.
- No additional endpoint candidates, route strings, source-map references or import edges were identified in the three parsed scripts.

### INFERRED — public-page script responsibilities
- `publicpage-theme.js` and `publicpage-ui.js` appear to support shared theme and public-page UI behavior based on their filenames and DOM usage. Their detailed function-level responsibilities are not established by the static route/endpoint inventory.
- `jobpage.js` appears to include session-aware behavior, potentially toggling user-specific controls or sign-in state based on `/api/auth/user/me`. Exact response fields and resulting behavior remain unverified.
- Given the public page's detail content was already present in the DOM accessibility capture and no job-data fetch candidate was found in these three scripts, a plausible model is that the job content is delivered with the HTML while client JavaScript enhances the page and checks user session. This is only an inference; server templates or inline serialized data were not directly inspected in this bundle analysis.
- The lack of public job-content API candidates in these scripts is not evidence that no such API exists elsewhere or is never called by other code paths.

### UNKNOWN / not established
- No complete job schema, original application link, pay or experience extraction behavior was recovered from these three scripts.
- No event handler behavior for Copy job link, Apply/Log in, Create account, alert or related openings was behaviorally tested.
- Static analyzer did not enumerate dynamically constructed URLs or route names, hidden server-side routes, or network operations in other scripts.
- No source maps were requested; original source modules remain unavailable.
- The `/api/auth/user/me` candidate was previously observed in runtime HAR only on the homepage, not specifically exercised by this static analysis on the job page.

### Next exact investigation step
- Navigate the isolated Chrome profile to `/browse/hiring-this-week`; rediscover its target ID; capture accessibility text with `inspect-web-page`. Identify visible filters, sorting, job cards, pagination and links.
- Then manually use one public browse control (prefer a filter that changes the URL) with Network Preserve log enabled and export a sanitized HAR. Do not submit forms that create accounts, alerts or applications.
- If additional source analysis is needed, inspect public-page script source only within the normal page scope, and focus next on the hiring-this-week page's loaded scripts rather than re-running the detail-page bundle analysis.
- No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed.


## JobBeeper public hiring feed — inspection findings (2026-11-05)

### Evidence record
- Route/title: `/browse/hiring-this-week` — `Who is hiring this week — JobBeeper`.
- REA evidence ID: `ev_ab4ed5862048380655d9421dbfeccd63eb35f12e9a877546a181ada8e6a1635a`.
- One-second passive inspection: DOM 1,175 nodes; accessibility tree 545 nodes.

### Observed page structure and exposed data
- Two main content sections: `Top hiring companies` and `Freshest openings`.
- The companies section exposes 20 company links and live-opening counts. Sample snapshot: Domino's 844; Accenture India 413; jobgether 263; CVS Health 194; Winners Merchants International, L.P. 166.
- The page reports 5,873 active companies and 20,000 recent public openings, with an explicit caveat that the 20,000 figure is a sample and counts describe that sample rather than the whole market.
- The freshest section labels the set `Latest 20` and exposes 20 job detail links. Card labels contain title, company, and location. Examples include Motive's Senior Product Manager, Growth (Hybrid - Bangalore), Motive's Senior Product Designer (Bangalore, India), and New Relic's Software Engineer 1 (Hyderabad, India).
- Job-detail URLs follow `/j/{job-id}-{slug}`; the 20 captured IDs run 28757581 through 28757562. Treat that as one observed sample only.
- Company links follow `/browse/company/{slug}`.
- Browse navigation includes Companies, Hiring this week, Backend, Frontend, and Data.
- The capture contains no INPUT, SELECT, or FORM elements. The accessibility tree exposes one button, `Color theme: System`. No visible keyword/location/experience/type filters, sort control, or pagination/load-more control was found on this page.
- Salary, experience, source/ATS, and posted-age values are not present in the public job-card accessibility labels. Do not infer they are absent from canonical job data.
- Scripts loaded: `/static/jobpage.js` (2,653 bytes), `/static/publicpage-theme.js` (2,842 bytes), `/static/publicpage-ui.js` (5,259 bytes).

### Limitations and interpretation
- Values and company counts are dynamic page snapshots, not fixed product specifications.
- This REA capture started after page load. Its zero network requests are not evidence that the initial page load made no requests.
- A separate earlier sanitized HAR across the browse, company, and job-detail pages recorded no same-origin JSON API calls for those specific page loads; this is still bounded evidence, not a universal claim about all states/routes.
- HTML-delivered/server-rendered public content is plausible, but not proven solely by the present capture.
- Category links may be curated route pages rather than in-page filters. Their behavior remains untested.
- Authenticated browse capabilities, ranking, pagination, and hidden job metadata remain unknown.

### Next exact evidence to collect
- Follow only the public `Backend` category link (`/browse/role/backend`) with DevTools Network Preserve log enabled. Compare URL, content, job-card fields/count, and navigation; export a sanitized HAR. Do not create alerts, accounts, or applications.
- No application code, configuration, server runtime, database, collectors, Telegram settings, or deployment were changed.


## Backend category-route HAR — 2026-11-05

### Observed evidence
- Route: `https://jobbeeper.com/browse/role/backend`; analytics/page-view title: `Latest Backend jobs | JobBeeper`; navigation referrer: `/browse/hiring-this-week`.
- The sanitized HAR contains 10 requests, 8 first-party. All 8 first-party requests returned HTTP 200.
- The route is loaded as `GET /browse/role/backend`, MIME `text/html`, status 200. HAR also records a Fetch to the same URL initiated by `https://jobbeeper.com/sw.js` line 57.
- Main document request duration about 558 ms. HAR page timing: onContentLoad ~660 ms; onLoad ~859 ms.
- Actual Fetch response headers: `Cache-Control: public, max-age=3600`; `Content-Type: text/html; charset=utf-8`; `Content-Encoding: zstd`; `X-Cache-Status: MISS`.
- Same first-party shared scripts loaded as other public pages: `jobpage.js` (2,653 bytes), `publicpage-theme.js` (2,842 bytes), `publicpage-ui.js` (5,259 bytes). Fonts/CSS also loaded.
- Analytics page-view event is Google Analytics `POST /g/collect` with HTTP 204.
- No first-party JSON/XHR/API endpoint is present in this HAR.

### Interpretation and limitations
- This is evidence for a distinct public HTML route, not proof of how the category data is generated. Backend may be a server-side category query or a curated route; cannot distinguish from this HAR alone.
- The service worker is involved in the Fetch request (initiator stack), but HAR fields `_fetchedViaServiceWorker` and `_serviceWorkerResponseSource` are null. Cache strategy or cache-served behavior is not confirmed.
- HAR contains no response body text, therefore cannot derive the Backend page's visible job cards/count, ordering, filters, or pagination from this file.
- No API calls in this capture does not rule out APIs after user interactions or in authenticated states.

### Next action
- Inspect the live Backend page's accessibility tree with REA and compare its visible job cards and controls against the hiring-this-week feed. Then test one public route/control only if it is visible. No app code, deployment, database, collectors, or Telegram settings were changed.


## Backend category DOM — public controls and 200-result cap (2026-11-05)

### Observed
- REA evidence ID: `ev_c220ac81730bb00fc4720d535b3e1f69a40f858cb7c423e0d63ba7a6933a04a0`. Route `/browse/role/backend`; title `Latest Backend jobs | JobBeeper`.
- DOM: 3,797 nodes; accessibility tree: 2,057 nodes.
- Page text: `Fresh Backend roles, without the noise.`; `Latest Backend openings`; shortlist stated to be ordered by freshness.
- Page shows `200 found`, `200 roles`, and explains `Showing the latest 200 public results, up to 200. Search filters this displayed list.`
- Exactly 200 accessible job-card links in the list. Accessible job names combine title, company, and location, with Remote/Hybrid/On-site where exposed. Each links to a `/j/{id}-{slug}` detail page.
- Search field `Search Backend roles` has DOM attribute `data-filter-input`. All 200 job anchors have `data-filter-item` and `data-filter-text`.
- Separate location form includes `City, country, or remote` searchbox and `Filter location` button; form action is the same Backend URL.
- No accessible sort selector or pagination/load-more control. Accessible buttons are Filter location and Color theme: System.
- Category relevance is noisy in this snapshot: visible examples include Actuarial Internship Program 2027, DSRD Global Pathology Quality Control Scientist, Frontend Software Developer, Chemistry Expert, Mathematics Specialist, Biology Researcher, and Population Health Informaticist.
- Public card labels do not expose salary, experience, source/ATS or posting age; hidden canonical fields remain unknown.
- Contrast: hiring-this-week public route showed Latest 20 and no visible in-page search/location filter. Backend category shows 200 public results and the two search fields.
- The one-second REA capture started after load; its zero network requests do not represent the initial page load. Earlier sanitized HAR bounded evidence of the HTML route and shared scripts, without observed first-party JSON/XHR/API calls.

### Inference
- Client-side search over the loaded 200 cards is strongly suggested by the markup and explicit page statement; verify with one controlled search term before treating it as confirmed behavior.
- The location form likely submits a separate route-level filter, but its behavior is untested.
- Treat 200 as a public preview cap, not the total available job corpus. No pagination was visible.
- The category label is a noisy bucket; do not assume every listed role is truly a backend job.

### Unknowns
- Search match fields, debounce, URL mutation, reset behavior, and network effects.
- Location autocomplete, valid values, query parameters and resulting set.
- Selection/ranking logic, access to older results, and authenticated/public differences.
- Category assignment and relevance precision.

### Next controlled interaction
- Search for a visible unique employer, e.g. `Cognizant`, using DevTools Network Preserve log. Record count, matching cards, URL change, and any request to distinguish front-end filtering from a backend search call.
- Then separately test location form if needed. Do not create an alert, account or application. No app code, server, DB, collectors, notifications, or deployment changed.


## Search interaction result and decision to start development — 2026-11-05

### Observed search result
- REA evidence: `ev_fdb8b7bbb29e59ff3bb337775db569496bdb1d4df043e0108461bd84e9a9988a`; Backend role page at 11:33 UTC.
- Search field focused with `Cognizant`.
- DOM retains 200 job cards (`data-filter-item`); 199 are hidden and only one is visible: Engineering Manager — Cognizant — Bengaluru, Karnataka, India (Hybrid).
- Dynamic count reports `1 role`; page's base result count remains `200 found`.
- Strong evidence that search filters the 200 preloaded cards in the browser. Since capture starts after interaction, a 1-second empty network window is not proof that no request happened during the keypress.

### What is known vs unknown
- Known public delivery: Hiring-this-week page exposes Latest 20; role page exposes up to 200 preloaded results, local search, a location form, public HTML, and common static scripts. Backend HTML HAR included public cache headers: `Cache-Control: public, max-age=3600` and `X-Cache-Status: MISS`.
- Not known: JobBeeper's private source scheduler, crawl topology, worker count, queues, database/index, provider credentials, access agreements, polling cadence, rate limits, retry strategy or exact upstream fetch methods. Public browser evidence cannot establish these.
- JobBeeper's own public product claims coverage of LinkedIn, Naukri, Workday, company career pages, Greenhouse, Lever and Ashby, with detection varying by source. Those are vendor claims and snapshots, not an audited description of the underlying implementation.
- The speed of the browse UI is separate from collection freshness: 200 job elements are already present when the search field filters them, and public HTML can be cached/pre-rendered. A fast UI therefore does not prove a live source crawl happens at search time or that upstream rate limits are bypassed.

### Decision
- End open-ended reverse engineering for now; do not wait for private backend details before building our product.
- Extend the existing Job Radar v2 instead of replacing it. Preserve the current FastAPI/SQLite/Docker/Oracle/Telegram foundation and existing collectors unless read-only audit finds otherwise.
- Core ingestion design:
  1. A source registry with per-adapter access method, policy/permissions, interval, concurrency, last success/error, cursor, freshness expectation and rate-limit state.
  2. Independent per-source scheduler, jitter, bounded concurrency, host request budgets, incremental polling, conditional requests where supported, and Retry-After-aware backoff.
  3. Pipeline: collect → retain raw provenance → normalize → deduplicate/merge → upsert → classify/match → notify.
  4. Measure source-to-first-seen, processing, and notification lag separately; collect run duration, errors, 429s, stale/closed state, and collector coverage.
  5. Start with stable public ATS feeds/official career integrations; use compliant providers/partner APIs next; only use public-page collection where permitted and justified. No login bypass, CAPTCHA bypass, proxy/account rotation, or rate-limit circumvention.
- Build order: read-only repo/runtime audit → source inventory and architecture/PRD → instrumentation and one reliable adapter end-to-end → expand sources → refine ranking/matching → referral intelligence after discovery reliability is measured.
- No application code or production state changed in this update.

### Next exact action
- Read-only audit of current v2 repo/Oracle runtime. Confirm commit and collector state before editing. Then write the architecture baseline and implementation PRD from actual code, and start the first vertical slice. Never expose secrets in audit output.


## JobBeeper architecture: evidence, inference and LinkedIn limitation (2026-11-05)

### Publicly observed
- Homepage claims checks across LinkedIn, Naukri, Workday and company career pages, lists Greenhouse, Lever and Ashby, and explicitly says availability/detection times vary by source.
- Homepage snapshot (4 Nov 2026) claims 89,849 career pages/job boards watched, 79,424 companies tracked and an 11-source demonstration. Vendor marketing metrics only; not audited.
- Homepage describes subscriber-first private matches followed by jobs that can be shared on the public site after a six-hour private window.
- Public LinkedIn company page shows 18 open roles and source badges/logos including Greenhouse, Instahyre, Lever, LinkedIn, Naukri, own, SmartRecruiters and Workable. This supports multi-source coverage in the public product, but not the origin method for each job.
- Job detail pages label some jobs as LinkedIn-sourced and display discovery intervals such as 32 minutes or 14 minutes. Treat as vendor-supplied page claims, not verified measurements.
- Backend category page preloads 200 jobs; search for Cognizant leaves one visible card and 199 hidden, supporting local browser filtering.
- Backend page HAR shows public HTML cache headers `Cache-Control: public, max-age=3600` and `X-Cache-Status: MISS` for one observed response.

### Official LinkedIn API and policy facts
- Official Job Posting API is a restricted partner API for publishing jobs to LinkedIn on behalf of customers, not a general job-search/read API.
- Documentation requires LinkedIn approval and an API/partner agreement, says new Job Posting API partnerships are not being accepted and directs applicants to Apply Connect (page last updated 2026-06-03).
- LinkedIn explicitly prohibits unauthorized third-party crawlers/bots/extensions that scrape or automate the website, and prohibits circumventing access controls or use limits.
- Sources: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview?view=li-lts-2026-04 and https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions
- Therefore, do not assume there is an openly available LinkedIn Jobs API that JobBeeper is using, and do not claim the platform bypasses rate limits.

### Inference — not verified JobBeeper internals
- Likely high-level architecture: independent source connectors → schedulers → normalization/provenance → dedup/entity resolution → central job store/search index → matching → private alerts → delayed public catalogue.
- Pre-collected records plus pre-rendered/cached public pages and local search plausibly explain fast UI response. This does not explain the private upstream LinkedIn acquisition path.
- 89k+ pages monitored does not mean every page is fetched every minute. Source cadences likely differ; JobBeeper itself says detection times vary by source.

### Unknown
- The exact LinkedIn collection mechanism, partner arrangements, licensed data providers, polling intervals, request budgets, workers, queues, DB/index, retry policy and operational SLOs remain unknown.
- Whether a job labelled LinkedIn in JobBeeper was acquired directly from LinkedIn, a company ATS mirror, or multiple sources remains unknown.

### Design decision for our product
- Do not pursue anti-rate-limit bypasses, rotating accounts/proxies, CAPTCHA bypass, or automated login scraping.
- Build independent, permitted source adapters with per-source scheduler, concurrency/request budget, jitter, incremental/conditional polling, backoff, provenance, idempotency, normalization and cross-source deduplication.
- Prioritize official ATS/company career endpoints and licensed feeds; keep LinkedIn isolated and optional unless a permitted access path is available.
- Separate private matching/alert delivery from any public catalogue/index.
- No application code or production configuration changed during this research update.


## Latest user prompt follow-through — 2026-11-05 — Ashby observability fix
- Continued from the latest JobBeeper research. The Cognizant Backend-page interaction is already documented: 1 of 200 preloaded cards remains visible and 199 are hidden, strongly supporting client-side local search. Open-ended reverse engineering is closed for now; build our own product on V2.
- Read the root/V2 READMEs, chronological handover, JobBeeper reference, router runbook, and inspected the current source/Compose/config. Repo-only inventory: LinkedIn, Naukri, Instahyre, Greenhouse, Ashby collectors; FastAPI + SQLite; canonical opportunities, evaluations, notification ledger, dashboard APIs and Telegram path. Dev config remains Naukri-only, notifications off, other collectors off. This does not verify the VM runtime.
- Found and fixed a concrete observability gap: Ashby was registered in `COLLECTORS` but omitted from the hard-coded source lists in `source_status()` and `latency_summary()`. `SOURCE_NAMES = tuple(COLLECTORS)` now drives both endpoints; latency SQL uses parameterized placeholders. Regression tests cover Ashby in both outputs.
- Commits on `v2-live-radar`: `6f6c62dba78538ecefd94aa1242487a80b80c8a2` (fix), `4f73e73b0e7fcc6a4ec103bf8ee846c3324dc46d` (tests). No PR.
- CI status is unknown: combined status was empty and no PR workflow runs were returned. No local test execution, VM access, pull, rebuild, DB/config/volume mutation, production change, provider API call or Telegram send occurred. Do not claim tests/deployment passed.
- Preserve VM-local `v2/config.json`, `.venv/`, `.env`, and `job-radar-dev_radar-dev-data`; no reset/clean/volume removal. LinkedIn remains isolated; no login scraping, CAPTCHA bypass, proxy/account rotation or rate-limit evasion.
- **Next exact action:** from `/home/ubuntu/job-beeper-dev`, return output of `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git fetch origin v2-live-radar`, and `git rev-list --left-right --count HEAD...origin/v2-live-radar`. Do not pull if local changes exist or the branch is not simply behind. After a safe fast-forward, run `./.venv/bin/python -m py_compile v2/radar.py v2/test_radar.py`, focused tests `./.venv/bin/python -m unittest v2.test_radar.SourceStatusPersistenceTests v2.test_radar.SourceLatencySummaryTests -v`, and then `./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py' -v`. Review results before any dev rebuild.
- Then continue with the read-only runtime/source audit and architecture/PRD baseline; first vertical slice should improve measurable per-source freshness/health without altering source policies or alert delivery. Update both handovers after every prompt.
- Detailed evidence and continuation prompt: `docs/JOB_RADAR_HANDOVER.md`. Product/architecture constraints: `docs/JOBBEEPER_REFERENCE.md`.


## Current handoff — 2026-11-06 — two checkouts, stale runtime image, volume identity

- **Verified test checkout:** `/home/ubuntu/job-beeper-dev`, branch `v2-live-radar`, HEAD `7ebc38b321847e74895557551478c3ff11bd4a`. User-reported focused Ashby tests: 4/4 pass. Full V2 suite: **136 tests, 19.323s, OK**; `py_compile` completed. Tests validate checkout code only, not deployed runtime. CI for this head remains unverified.
- **Preserve dev local state:** `M v2/config.json`; untracked `.env.save`, `.venv/`, and `v2/config.json.backup.20261105-183321`. Never stage/reset/clean/overwrite/delete these.
- **Port 8000 runtime:** API healthy, DB path `/data/jobs.db`; LinkedIn and Naukri enabled, Instahyre and Greenhouse disabled; source status did not list Ashby. Daily summary on 2026-11-06: 5 discovered, 0 matched, 0 alertable, 0 sent. LinkedIn last-hour latency snapshot: p50 42m, p90 4h, max 5h; 4/19 under 5m. Naukri had 0 latency samples. Point-in-time evidence only.
- **Container identity:** `v2-radar-1`, image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, created 2026-10-12T03:44:43Z, Up about three weeks. Compose project label `v2`; Compose file label `/home/ubuntu/job-beeper/v2/docker-compose.yml`.
- **Actual persistent mount:** named Docker volume `v2_radar-data` → `/data`; host path `/var/lib/docker/volumes/v2_radar-data/_data`. Preserve this exact volume. Never `down -v`, prune, remove, or accidentally create a second project against another volume.
- **Original deployment checkout:** `/home/ubuntu/job-beeper`, branch `v2-live-radar`, HEAD `61d8271`; Compose service resolves to `radar`. Its Git status printed no lines, but re-check before acting. Container labels prove this is the checkout path used to create the current port-8000 service.
- **Critical distinction:** tested source is in `/home/ubuntu/job-beeper-dev`; running service's Compose path is under `/home/ubuntu/job-beeper`. Do not run Compose from the dev checkout for port 8000. The role of the original service (production/live vs development) is not yet confirmed; treat it as production/live until user clarifies. No pull/rebuild/restart/deploy has happened.
- Docker CLI without sudo returned permission denied; read-only inspect succeeded with sudo. A YAML `volumes:` snippet was accidentally entered as shell input and returned command-not-found; YAML belongs in the Compose file, not the terminal.
- No app/config/database/volume mutation, image build, container recreation, source enablement, provider call or Telegram send occurred. Runtime is still the old image; Ashby absence is consistent with this, not a regression in tested source.
- **Next:** ask whether `/home/ubuntu/job-beeper` / port 8000 is the live/production service or intended dev. Then, read-only in that directory, check `git status --short`, branch, HEAD, remotes, `git fetch origin v2-live-radar`, and `git rev-list --left-right --count HEAD...origin/v2-live-radar`. Do not pull, checkout, build or recreate until release target, exact volume and rollback are confirmed. If a separate dev runtime is needed, it must use a distinct Compose project, loopback-only port and separate volume. Never expose secrets or modify production without explicit approval.
- Detailed chronology and exact commands: `docs/JOB_RADAR_HANDOVER.md`. Architecture guardrails: `docs/JOBBEEPER_REFERENCE.md`. **Next-chat prompt:** “Read all three Job Radar docs first. Do not deploy. Clarify the role of `/home/ubuntu/job-beeper` (port 8000). The tested `job-beeper-dev` checkout is at `7ebc38b`, with 136 tests passing and local config/env files to preserve. The running container is from the original checkout path, old image created Oct 12, mounted volume `v2_radar-data:/data`; original checkout is at `61d8271`. First do read-only git status/fetch/compare and decide release target. No volume deletion, production change, or notifications.”


## User clarification — 2026-11-06 — port 8000 is production/live

- User confirmed `/home/ubuntu/job-beeper` and port 8000 are **production/live**. Treat its checkout, container `v2-radar-1`, Compose project `v2`, and persistent volume `v2_radar-data:/data` as production assets.
- This clarification is **not deployment approval**. Do not pull, checkout, build, recreate/restart, alter config/env, touch DB/volume, enable sources, or send notifications on production without separate explicit approval and a reviewed backup/rollback plan.
- Dev/test checkout remains `/home/ubuntu/job-beeper-dev` at `7ebc38b`; user-reported full suite: 136 tests passed. Preserve its modified `v2/config.json`, `.env.save`, `.venv/`, and timestamped backup.
- Next action: read-only inspection from `/home/ubuntu/job-beeper`: status, branch, HEAD, remotes, fetch `origin/v2-live-radar`, compare commit counts. Do not pull. Never print secrets. Purpose is release-drift analysis only; production runtime and `v2_radar-data` remain untouched.
- Detailed chronology and continuation prompt: `docs/JOB_RADAR_HANDOVER.md`. Architecture guardrails: `docs/JOBBEEPER_REFERENCE.md`.

## Current state — 2026-11-06 — production checkout is 611 commits behind

- Production `/home/ubuntu/job-beeper` (port 8000) is confirmed by user. Read-only audit: clean working tree, branch `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; fetch advanced `origin/v2-live-radar` to `f4f61b8d55d6a52c05e1dd9d98510ccea12ad77a`.
- Commit counts: `0 611` (production-only / remote-only). GitHub compare independently confirms 611 commits ahead, 0 behind, merge base = production HEAD. This is straight-line release drift, not deployment approval.
- Compare summary reports 22 changed paths, including `v2/config.json` (+15/-3), `v2/radar.py` (+313/-13), `v2/test_radar.py` (+528/-2), CI, dashboard, Compose/dev config, Gemini extractor/diagnostic, LLM router, Greenhouse canary, and docs. Review exact diffs and commit subjects before proposing any release; do not assume branch config should replace live config.
- Only `git fetch` updated remote-tracking metadata. No pull/checkout/build/restart, production config/env/DB/volume change, source enablement, provider call or notification send.
- Hard boundary: port 8000 is production; preserve `v2-radar-1` and `v2_radar-data:/data`. No production mutation without reviewed backup/rollback plan and separate explicit deployment approval.
- Next: read-only review of all 611 commit subjects and critical diffs, especially `v2/config.json`, source/notification settings, `v2/radar.py`, Compose and CI. Then propose a bounded release candidate and backup/rollback plan; do not deploy.
- Detailed evidence and continuation prompt: `docs/JOB_RADAR_HANDOVER.md`. Architecture guardrails: `docs/JOBBEEPER_REFERENCE.md`.

## Current release review — 2026-11-06 — 613 commits behind, production gates reviewed

- Production branch `v2-live-radar` HEAD `61d8271` is 613 commits behind fetched remote `a21e2f2`; working tree was clean. Aggregate range: 22 files, 9,694 additions / 120 deletions, much of it docs/tests. `v2/docker-compose.yml` is unchanged; dev Compose is separate, loopback-only 8001, separate volume, Telegram blank.
- Production default config v10→v11 adds Ashby cadence 1,800s and OpenAI/PostHog board definitions, but sets Ashby disabled. Migration explicitly forces Ashby false for pre-v11 runtime configs after merge. LinkedIn/Naukri remain true by defaults; notifications default true. Dev config keeps Naukri only and notifications off. Live `/data/config.json` remains authoritative; never overwrite it with repo config.
- AI paths are feature gated: Gemini extraction `GEMINI_EXTRACTION_ENABLED`, Gemini matcher `GEMINI_MATCHER_ENABLED`, router `LLM_ROUTER_ENABLED`, routed matcher `LLM_ROUTER_MATCHER_ENABLED`; code defaults false. Production Compose does not map these variables or provider keys. Verify actual live env gate presence/boolean only before any future release; never reveal values.
- Reviewed Ashby public-board collector and config allowlist; source is opt-in. Registry-derived `SOURCE_NAMES` fixes source-status and latency-summary coverage. Greenhouse freshness logic leaves missing publication timestamps unknown. Gemini extractor uses bounded cache/evidence validation; hard matching requires explicit separate gate.
- **Release review defect:** `/api/dedupe-candidates` retains hard-coded source filter without Ashby. Add Ashby or use registry-derived placeholders and test it before considering Ashby support complete.
- CI workflow now includes Greenhouse compile/tests, focused router/extractor tests, and full V2 suite. GitHub status lookup did not confirm CI. User-reported dev tests: 136 pass; not production/runtime validation.
- No production changes or notifications. No pull, build, restart, DB/config/volume mutation, or source enablement. Protect `v2-radar-1` and `v2_radar-data:/data`.
- Next: read-only check live `/api/config` safe projection and AI feature-gate booleans, then patch/test Ashby omission on dev/branch. Prepare release backup/rollback plan only after code review; separate explicit deployment approval remains mandatory.
- Detailed chronology: `docs/JOB_RADAR_HANDOVER.md`. Architecture guardrails: `docs/JOBBEEPER_REFERENCE.md`.

## Production config confirmed; Ashby dedupe endpoint fix

- Live config read-only snapshot: v10; notifications true; LinkedIn/Naukri true; Instahyre/Greenhouse false; cadence 180/300/600/900s; match threshold 55; candidate exp 2; max exp 3; explicit-experience alert requirement false. Ashby absent. All four AI gate booleans false.
- Preserve these live settings. Expected v11 migration adds Ashby disabled and retains current source/notification flags; do not replace live config with repo defaults.
- Code review found `/api/dedupe-candidates` hard-coded four-source SQL filter omitted Ashby. Patch now derives parameterized source placeholders from collector registry and adds a regression test for an Ashby/LinkedIn same-identity pair.
- Patch is repository-only, not deployed. Next: run focused + full V2 tests in dev checkout; no production pull/build/restart/DB writes/notification sends. CI unverified.

## User prompt follow-through — 2026-11-06 — isolated worktree uses python3

- User fetched origin/v2-live-radar and created the isolated detached worktree /tmp/job-beeper-ashby-dedupe-test at commit c93f041 (the latest fetched branch tip at that moment). This worktree does not overwrite the existing /home/ubuntu/job-beeper-dev checkout or its local config/env/venv files.
- The three attempted commands using python did not execute because this VM has no python executable; shell suggested python3. No focused tests, full-suite tests, or compilation result is available from this attempt.
- Next exact action, from /tmp/job-beeper-ashby-dedupe-test:

  python3 -m unittest v2.test_radar.DedupeCandidatesSourceCoverageTests -v
  python3 -m unittest discover -s v2 -p 'test_*.py' -v
  python3 -m py_compile v2/radar.py v2/test_radar.py

- Record actual output before judging the Ashby dedupe registry fix. If any command fails, diagnose from its output; do not claim tests passed. Do not remove the worktree without checking whether it is still in use.
- The patch remains repository-only. Production /home/ubuntu/job-beeper, port 8000, container v2-radar-1, and volume v2_radar-data:/data remain untouched; no deployment approval was given. No config, DB, source toggle, or notification state changed.
- Overarching goal remains reliable multi-source discovery → normalization/deduplication → consistent explainable matching → dashboard and Telegram delivery. The Ashby endpoint fix only closes registry coverage in dedupe candidate discovery; it does not activate Ashby or prove collection/runtime health.
- Continuation: run the three python3 commands above in the isolated worktree and return complete output. Then review failures or confirm test evidence, check CI, and update both handover documents. No production mutation or notification send.
## User prompt follow-through — 2026-11-06 — test import blocked by missing dependency

- User ran the focused Ashby regression test, full V2 unittest discovery, and py_compile from /tmp/job-beeper-ashby-dedupe-test at c93f041 using python3.
- Focused test did not load: importing v2.radar failed with ModuleNotFoundError: No module named 'bs4'. Full discovery loaded and passed 17 LLM-router tests, but four test modules failed to import (Radar, Gemini experience diagnostic, Gemini extractor, Greenhouse canary) for the same missing bs4 dependency. Therefore the full suite is BLOCKED/INCOMPLETE, not a code-test failure and not a pass.
- py_compile was the final command and emitted no error output; this is consistent with syntax compilation success, but the user did not separately show an exit code. Compilation does not validate imports or behavior.
- Repository-declared runtime dependencies are in v2/requirements.txt: FastAPI, Uvicorn, requests, beautifulsoup4, tzdata. The missing import maps to the declared beautifulsoup4 package.
- Next exact action, still inside /tmp/job-beeper-ashby-dedupe-test: create an isolated virtual environment and install the V2 requirements, without changing system Python or production:

  python3 -m venv .venv
  .venv/bin/python -m pip install -r v2/requirements.txt
  .venv/bin/python -m unittest v2.test_radar.DedupeCandidatesSourceCoverageTests -v
  .venv/bin/python -m unittest discover -s v2 -p 'test_*.py' -v
  .venv/bin/python -m py_compile v2/radar.py v2/test_radar.py

- If venv creation fails because python3-venv is unavailable, stop and return that error; do not install OS packages or modify the VM globally without a separate decision. If dependency installation fails, return the complete pip error. Preserve the temporary worktree until test results are reviewed.
- No application code/config change, test result validating the Ashby fix, CI confirmation, production deployment, DB/volume mutation, source activation, or Telegram send occurred. Production /home/ubuntu/job-beeper, port 8000, v2-radar-1, and v2_radar-data:/data remain untouched.
- Product goal remains reliable multi-source discovery → normalization/deduplication → explainable matching → dashboard and Telegram delivery. This is a test-environment setup issue; Ashby remains opt-in and this endpoint fix remains repository-only.
- Continuation: set up only the isolated worktree venv from v2/requirements.txt, rerun focused and full tests, report complete output. Then diagnose actual test failures, check CI, and keep production approval-gated.
## User prompt follow-through — 2026-11-06 — V2 suite passes with Ashby dedupe regression

- User supplied the completed unittest output from the isolated worktree /tmp/job-beeper-ashby-dedupe-test, code checkout at c93f041. Full V2 discovery completed: 137 tests in 18.998 seconds, result OK, zero failures/errors.
- Crucial regression test test_dedupe_candidates_includes_ashby_from_collector_registry passed in the full suite. This validates the registry-derived, parameterized source filter in /api/dedupe-candidates for the Ashby + LinkedIn candidate pair.
- Ashby collector tests also passed, including opt-in migration behavior and handling of invalid/missing published_at. Source status and latency-summary Ashby coverage tests passed. Gemini extractor/diagnostic, Greenhouse canary, LLM-router and broader matcher tests in the displayed run also passed.
- The user-supplied output contains the full-suite run only. It does not show a separate focused-only test invocation or the py_compile command's output/exit status; do not claim those separate commands completed based solely on this attachment. Full suite did include and pass the Ashby regression test.
- CI remains unverified: GitHub combined commit status returned no status rows for c93f041 and the commit workflow-runs lookup returned no PR-triggered runs. Local VM test pass is not CI evidence.
- No application code changed in this turn. No deployment, production pull/build/restart, config/DB/volume mutation, source activation, external provider call, or Telegram send occurred. Production /home/ubuntu/job-beeper, port 8000, container v2-radar-1, and volume v2_radar-data:/data remain untouched.
- The missing-bs4 import blocker from the prior attempt is resolved in the isolated test environment; the full suite now ran. Do not infer which installation method was used unless the user supplies that command.
- Goal remains reliable multi-source discovery → normalization/deduplication → explainable matching → dashboard and Telegram delivery. This test closes the code-level Ashby dedupe endpoint coverage check, but does not enable Ashby or establish collector/runtime health.
- Next exact action: confirm the isolated worktree's current HEAD and status, then inspect the code/test diff and CI workflow behavior if needed. Preserve all production gates. Before any release, prepare backup/rollback and isolated runtime validation; separate explicit production deployment approval remains mandatory.
## User prompt follow-through — 2026-11-06 — Ashby dedupe patch review and worktree verification pending

- Reviewed the two code commits directly: 0a09162d06fcd2ca6880bfbc9eb012132c0b2582 changes /api/dedupe-candidates to build parameter placeholders from SOURCE_NAMES and bind the registry tuple as SQLite parameters; 6dc6ac8c5e96938c7a39bf10b3fb3ba4359d5cf4 adds a temporary-SQLite regression test with matching LinkedIn and Ashby rows.
- Read the current v2/radar.py source around COLLECTORS and dedupe_candidates: SOURCE_NAMES = tuple(COLLECTORS), and Ashby is registered in COLLECTORS. The parameterized query is consistent with the existing registry-driven latency-summary query. No source values are interpolated into SQL; only placeholder count is generated, and source values are bound.
- Read the regression test: it patches radar.DB_PATH to a TemporaryDirectory DB, creates a minimal jobs table, inserts LinkedIn/Ashby same-company/title rows, asserts jobs_considered=2 and asserts a cross-source pair. User's full suite output confirms this test passed.
- Test class is currently placed after the module's if __name__ == '__main__': unittest.main() guard. Discovery/import-based test execution (the reported full suite) still discovers and runs it, but direct execution of test_radar.py would call unittest.main before defining this class. This is a test-file organization nit, not a failure in the tested discovery path; consider moving the class above the main guard in a later tidy-up only if useful.
- The user-created detached worktree was last confirmed at c93f041. Current local HEAD and uncommitted status cannot be read through GitHub; no VM shell access is available to the assistant. Exact next action for user, from /tmp/job-beeper-ashby-dedupe-test:

  git status --short
  git rev-parse HEAD
  git branch --show-current
  git diff --stat
  git diff -- v2/radar.py v2/test_radar.py

- Expected branch output is empty because the worktree was created detached. Confirm HEAD remains c93f0414e8f99540d6004f012e8cb286e32bf1f6 and that the code/test diff is clean; if status/diff shows local changes, stop and inspect rather than reset/clean. The branch has since received documentation-only follow-through commits; do not assume the old detached worktree includes those docs updates.
- User-provided full V2 suite result: 137 tests in 18.998s, OK. GitHub CI lookup for c93f041 returned no status rows and no PR-triggered workflow runs; CI is unverified. No separate focused-only output or py_compile exit code was supplied in the attachment.
- No application code was changed in this review. No production pull/build/restart, config/DB/volume mutation, source activation, provider call or Telegram send. Production /home/ubuntu/job-beeper, port 8000, v2-radar-1 and v2_radar-data:/data remain untouched.
- Goal remains reliable multi-source discovery → normalization/deduplication → explainable matching → dashboard and Telegram delivery. The endpoint code fix and regression are validated by the local full suite, but no runtime/deployment claim follows. Keep production approval-gated.
- Continuation: verify the isolated worktree status/HEAD/diff with the exact commands above. Then review CI availability and prepare an isolated runtime/release plan only after the code state is clean. Do not deploy or send notifications.

## 2026-11-06 follow-through — clean code diff
- Detached worktree HEAD verified as c93f0414e8f99540d6004f012e8cb286e32bf1f6. `v2/radar.py` and `v2/test_radar.py` have no diff. Local `v2/config.json` is modified (2 insertions/2 deletions) and `.venv/` is untracked; preserve both without reset/clean/stage/commit.
- Full V2 suite: 137 tests passed in 18.998s, including Ashby dedupe regression. CI remains unverified. Production remains untouched; no deploy, config/DB/volume mutation, source activation, or notification send.
- Next: prepare a non-mutating isolated runtime/release checklist; production changes require separate explicit approval and backup/rollback review.


## 2026-11-06 follow-through — verify isolated development Docker service
- User asked to verify whether the isolated development Docker service on port 8001 is still running. The assistant cannot inspect the VM directly; requested read-only VM checks: `sudo docker ps -a --filter 'publish=8001' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'`, `sudo docker compose ls`, `sudo ss -ltnp | grep ':8001' || ...`, and from `/home/ubuntu/job-beeper-dev`, `git status --short` plus `git rev-parse --short HEAD`.
- Await user-supplied command output before declaring service status. Do not start/stop/rebuild containers or change configuration. Keep production port 8000 and production checkout/container/volume untouched.


## 2026-11-06 follow-through — isolated development service verified running
- User supplied read-only VM output: container `job-radar-dev`, image `job-radar-dev-radar`, status `Up 2 weeks`, binding `127.0.0.1:8001->8000/tcp`. Compose project `job-radar-dev` is running from `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`; production project `v2` is separate and uses `/home/ubuntu/job-beeper/v2/docker-compose.yml`.
- `ss` confirms only `127.0.0.1:8001` listener via docker-proxy. Dev API is loopback-bound, not directly exposed on public interfaces. Service is running, but its two-week-old container is not proof it reflects current checkout code; no health endpoint or code/container parity check was performed yet.
- Dev checkout `/home/ubuntu/job-beeper-dev` is at `7ebc38b`. Preserve local changes: modified `v2/config.json`; untracked `.env.save`, `.venv/`, and `v2/config.json.backup.20261105-183321`. Do not reset, clean, stage, overwrite, or delete these.
- No container start/stop/rebuild/restart, config/DB/volume mutation, production operation, source activation, or notification send occurred.
- Suggested next read-only check, if continuing: query `http://127.0.0.1:8001/health` and `/api/source-status` from the VM, then inspect dev container image/config metadata to determine runtime health and code/config parity. Do not change service state.


## 2026-11-06 follow-through — dev API health and source registry
- User supplied read-only `GET /health` from port 8001: status `ok`, version `2.0.0`, uptime `1,732,027` seconds, DB `/data/jobs.db`. Runtime health reports only Naukri; it is not running, last success `2026-11-05T19:18:27.101126+00:00`, jobs_seen 335, new_jobs 0, error null.
- `GET /api/source-status` reports only LinkedIn, Naukri, Instahyre and Greenhouse; LinkedIn/Instahyre/Greenhouse disabled, Naukri enabled. Ashby is absent from the response. This is evidence that the running dev API does not expose the expected current five-source registry; likely stale container/code, but confirm before concluding exact cause. Version `2.0.0` is not a commit identifier. Health `ok` does not establish Ashby readiness.
- Do not enable sources or rebuild/restart the dev service yet. Next read-only diagnostics: inspect `job-radar-dev` image ID, container creation timestamp, working directory and Compose labels; locate the application file inside the container and compare its SHA256 with `/home/ubuntu/job-beeper-dev/v2/radar.py`. Also record the current dev checkout HEAD/status without modifying anything. Preserve dev local files/config. Production remains untouched.


## 2026-11-06 follow-through — container application path identified
- User confirms dev Compose labels: project `job-radar-dev`, Compose file `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`. Inside the running container, working directory is `/app`; application file is `./v2/radar.py` and config is `./v2/config.json`.
- Dev checkout HEAD is `7ebc38b7c321847e74895557551478c3ff11bd4a`; host checkout `sha256sum v2/radar.py` is `9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55`.
- The provided output did not include container `Created`, `ImageID`, or `WorkingDir` inspect fields, and did not yet include a checksum from `/app/v2/radar.py`. Exact host/container code parity remains unverified. Runtime API source-status still omits Ashby, despite the inspected newer registry containing it.
- Next read-only check: `sudo docker exec job-radar-dev sha256sum /app/v2/radar.py`; compare directly with the host hash above. Also capture `sudo docker inspect job-radar-dev --format 'Created={{.Created}} ImageID={{.Image}} WorkingDir={{.Config.WorkingDir}}'`. No rebuild/restart or config/source changes. Preserve dev checkout local files; production stays untouched.


## 2026-11-06 follow-through — dev container code mismatch confirmed
- User supplied container file checksum: `/app/v2/radar.py` = `c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2`.
- Host dev checkout checksum from the prior turn: `/home/ubuntu/job-beeper-dev/v2/radar.py` = `9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55`. Hashes differ, so running `job-radar-dev` does not use the same `radar.py` bytes as the current development checkout. Container metadata: Created `2026-10-16T18:15:03.877936825Z`, image ID `sha256:c41b89e3ee05ba5abe3de2612b8d86d51322baa47ceeaaab2b53f98e3eedba92`, working directory `/app`.
- Correlates with dev API `/api/source-status` exposing only LinkedIn/Naukri/Instahyre/Greenhouse and omitting Ashby. Therefore port 8001 is HTTP-healthy but not yet validated as running the current Ashby-capable checkout. Exact image source commit/build provenance is not established by this evidence alone; do not assert which commit the image contains.
- Next safe step: read-only inspect Compose labels, image labels, image creation metadata and Git commit details for host checkout; optionally inspect container's source registry using grep. Do not rebuild/recreate/restart or modify config/DB/volume yet. Keep production port 8000 and its assets untouched. Preserve local dev config, `.env.save`, `.venv/`, and timestamped config backup.


## 2026-11-06 follow-through — nuance: Ashby code exists in dev container
- User supplied image inspect: image Created 2026-10-16T17:13:11.778204261Z; RepoDigests reports local image digest job-radar-dev-radar@sha256:c41b89e3ee05ba5abe3de2612b8d86d51322baa47ceeaaab2b53f98e3eedba92. Labels identify Compose project job-radar-dev, service radar, Compose version 5.6.0; no source revision/commit label is present.
- User grep from container /app/v2/radar.py shows Ashby config migration/validation, Ashby board normalization, ashby_collect(), public API endpoint https://api.ashbyhq.com/posting-api/job-board/{name}, and COLLECTORS registration entry ashby: ashby_collect (line 2710). Thus Ashby collector code IS present in the running container. Correct earlier overstatement: the /api/source-status omission does not mean Ashby collector is absent.
- Hash mismatch remains proven: container c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2 vs host checkout 9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55. Image created 2026-10-16; host checkout HEAD 7ebc38b7c321847e74895557551478c3ff11bd4a dated 2026-11-05. Therefore container file differs from checkout, but exact source commit of image is unknown.
- Outstanding inconsistency: dev /api/source-status returns only linkedin, naukri, instahyre, greenhouse while container COLLECTORS includes ashby. Likely endpoint builds its own hardcoded source list or returns legacy structure; inspect exact endpoint and any SOURCE_NAMES definition in both container and host checkout before concluding or rebuilding.
- Next read-only command: run grep -nE 'SOURCE_NAMES|source-status|source_status|COLLECTORS' against /app/v2/radar.py inside container and v2/radar.py in /home/ubuntu/job-beeper-dev separately, then inspect nearby code with sed. No rebuild/restart or config/DB/volume mutation. Preserve all dev local changes; production untouched.
## 2026-11-06 follow-through — correct interpretation of dev container Ashby code

- User compared grep output from running `job-radar-dev` at `/app/v2/radar.py` with host checkout `/home/ubuntu/job-beeper-dev/v2/radar.py`.
- Running container file contains Ashby config validation/migration (lines 155-171, 254-298), `ashby_collect()` (2614-2698), Ashby in `COLLECTORS` (2705), and scheduler iteration over `COLLECTORS` (2823, 2830). Thus the Ashby collector implementation is present in the container and registered with the scheduler. The earlier interpretation that Ashby code itself was absent was incorrect.
- Running container grep did not show `SOURCE_NAMES`; its `/api/source-status` route begins at line 2946. The host checkout at `7ebc38b` defines `SOURCE_NAMES = tuple(COLLECTORS)` at line 2712, uses `source_placeholders` and registry-driven source loops for latency/source-status at lines 2907, 2930 and 2976. This explains the four-source response: the container's source observability code is older and does not expose Ashby even though the collector is registered.
- The running container's `radar.py` hash is `c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2`; host checkout hash at `7ebc38b` is `9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55`. Container image created `2026-10-16T17:13:11.778204261Z`, image ID `sha256:c41b89e3ee05ba5abe3de2612b8d86d51322baa47ceeaaab2b53f98e3eedba92`; labels do not identify source commit. Code is not byte-identical to host, and observability improvements are missing in the container.
- Correct conclusion: dev container is HTTP healthy and has Ashby collector code registered, but its source-status/latency observability is stale relative to host checkout. The API omitting Ashby is not evidence that Ashby collector code is missing. Whether Ashby is enabled/configured in the container's effective dev config is not established by this grep; inspect via read-only `/api/config` projection before testing any collection. Ashby should remain disabled until a controlled test is planned.
- No rebuild/restart or config/DB/volume mutation occurred. Production port 8000 remains untouched; dev port 8001 remains loopback-bound. Preserve host local config/env/venv/backup files.
- Next read-only verification: on port 8001, inspect only `config_version`, `source_enabled`, `ashby_boards`, `notifications_enabled`, `poll_seconds` from `/api/config`; inspect the running file's source-status and dedupe query code around the endpoint with `sed -n '2940,3010p' /app/v2/radar.py`. Then decide whether a development-only rebuild is useful to align observability and dedupe code with the tested checkout. Never point a dev recreation at production volume `v2_radar-data`.


## Termalin direct SSH access verified — 2026-11-06 — host health snapshot

- User explicitly invoked Termalin and asked whether direct SSH commands are now possible. `hosts_list` returned a reachable host `job-radar` (Ubuntu 22.04), online, default execution user `ubuntu`, policy `full`. Termalin keyless connector is online. Direct SSH-equivalent shell commands were executed successfully via Termalin; no SSH key or inbound port access was needed.
- Monitoring `server_metrics` (only one sample in preceding 6h, timestamp 2026-11-05 19:33 UTC): 2 CPU cores; load1 0.19, load5 0.07, load15 0.04; memory 57.4% used; root disk 17.4% used; 3.2% inode use; uptime about 29 days; swap had about 507MB used in the monitor sample. `alerts_list` reported no open alerts.
- Live read-only SSH checks at 2026-11-05T19:33:49Z: `/` 45G size, 7.9G used, 38G free (18%); inode usage 4%; memory 956MiB total, 389MiB used, 429MiB available, swap 490MiB used / 2.0GiB total; load averages 0.30/0.12/0.06; 146 processes, 0 zombies; NTP OK. `systemctl --failed` empty. `sshd` on port 22, production Radar on `0.0.0.0:8000`, development Radar on `127.0.0.1:8001`.
- Both containers are up: `v2-radar-1` (production) and `job-radar-dev` (development). Both report `RestartCount=0`, `OOMKilled=false`; started 2026-10-12 and 2026-10-16 respectively. Container stats at sample: dev 31.83MiB RAM, 0.21% CPU; prod 102.1MiB RAM, 7.88% CPU. Compose projects/config paths are separate: `v2` at `/home/ubuntu/job-beeper/v2/docker-compose.yml`; `job-radar-dev` at `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`.
- Both `/health` endpoints returned `status=ok`, version 2.0.0, DB `/data/jobs.db`. Production at sample: LinkedIn/Naukri last successful runs Nov 5 19:33 and 19:30 UTC; LinkedIn reported 3 new jobs in run, Naukri 0. Dev at sample: Naukri enabled, last success 19:33 UTC, 0 new jobs. These are individual snapshots, not a full freshness/SLO analysis.
- `journalctl -p warning --since '24 hours ago'` showed repeated SSH `kex_exchange_identification: Connection closed by remote host` and one reset-by-peer. This is not evidence of successful authentication or compromise; likely incomplete/aborted connection attempts but correlate with auth logs / firewall / expected client IPs if they continue. Do not disable SSH or alter firewall without evidence.
- `last -x reboot` showed two boot records on Oct 7 (14:33 and 18:44) still marked running; may reflect one boot replacing another due to log format/clock or multiple wtmp entries. Not enough evidence to call repeated unexpected reboots; corroborate with `uptime`, `who -b`, and journal boot IDs if needed.
- Overall: host is online and responsive; disk/load/service/container health looks good. Main capacity caution: only ~956MiB RAM total; about 429MiB available and ~490MiB swap used. No current alert. Continue monitoring memory/swap during builds or two-service activity. Current metrics history in Termalin only had one sample in 6h, so trend confidence is limited.
- Direct Termalin access is available and verified. Use `hosts_list` first, heed owner note/policy, prefer metrics/alerts then read-only `ssh_exec`; long installs/builds/backups should use job_start. Production mutations still require explicit user approval and reviewed backup/rollback; do not conflate SSH access with deployment authorization.
- This check made no file/config/DB/volume changes, no service restart, no container operation, no update, no provider network call and no Telegram send.

## 2026-11-06 — Backup established locally; encrypted Termalin job awaiting owner confirmation

### Backup inventory and scope
- Read all current Job Radar docs before acting. Termalin host `job-radar` is online with full command policy as `ubuntu`; direct Termalin shell is available. No pre-existing backup jobs or archives existed.
- Confirmed production container `v2-radar-1` volume `v2_radar-data:/data`; dev container `job-radar-dev` volume `job-radar-dev_radar-dev-data:/data`. Dev also bind-mounts `/home/ubuntu/job-beeper-dev/v2/config.dev.json` to `/app/v2/config.json`.
- Runtime data sizes: production volume approx 65 MB, dev volume approx 32 MB. Jobs databases are active SQLite files; do not copy the live `jobs.db` file directly as a consistency strategy. Use Python sqlite3 `Connection.backup()` against a read-only source connection from inside each container.
- Built `/var/backups/job-radar-pre-release-20261106/` (mode 0700) containing consistent initial SQLite snapshots (`production-jobs.sqlite3`, `development-jobs.sqlite3`), copied runtime `config.json` and `config_token` for each volume (secrets were not displayed), and exact running container images as `running-images.tar`. Initial snapshot and both later snapshots passed `PRAGMA integrity_check`. Initial job row counts at final snapshot: production 19,846; development 7,158. Initial DB sizes: 68,014,080 and 33,169,408 bytes. Exact running image IDs exported: production `sha256:6300862b5d8071221343dc5c95006d73a90a22db42983aecf3b6e0215cc9fee3`; dev `sha256:c41b89e3ee05ba5abe3de2618b2d86d51322baa47ceeaaab2b53f98e3eedba92`. Tar size 61,245,440 bytes. `docker image load -i` parsed the tar successfully.
- Created `/var/backups/job-radar-daily/` containing separate production/dev SQLite snapshots. Added root-owned script `/usr/local/sbin/job-radar-sqlite-snapshot.sh`, systemd service `/etc/systemd/system/job-radar-sqlite-snapshot.service`, and enabled timer `/etc/systemd/system/job-radar-sqlite-snapshot.timer` scheduled daily at 02:45 UTC (persistent, up to 30s random delay). The service snapshots production then dev DB using SQLite online backup API, verifies integrity/count, copies to host and atomically replaces the snapshot files. It also refreshes the SHA256 manifest.
- Initial script authoring had two bugs that were caught before relying on the result: (1) an over-escaped Bash variable caused a literal `${filename}` target and both snapshots collided; (2) checksum manifest generation included its own temporary file and verification ran from the wrong current directory. Both were corrected. Final service execution: `Result=success`, `ExecMainStatus=0`; distinct production and dev files exist with correct sizes/counts and pass integrity. Manifest verification from `/var/backups` returned OK for all 9 artifacts. The stray literal-name file was removed. Do not repeat earlier failed method; use final script on host as source of truth.
- Snapshot staging currently occupies about 155 MB in the initial pre-release directory plus 100 MB in the daily directory, leaving about 37 GB free on root. Snapshot directories and secret copies are permission-restricted. SHA manifest at `/var/backups/job-radar-pre-release-20261106/SHA256SUMS` contains checksums for both database snapshots, runtime config/token copies and image tar; daily script refreshes it after each scheduled snapshot.

### Encrypted Termalin archive — not yet complete
- `backup_list` before setup reported no jobs and no archives. Created Termalin backup job draft `Job Radar production and dev daily backup`, ID `ae51ea55-d396-417e-8792-8ddfc1cd66c7`. Confirmation link: `https://termal.in/account#backup-draft=ae51ea55-d396-417e-8792-8ddfc1cd66c7`.
- Draft scope: `/home/ubuntu/job-beeper`, `/home/ubuntu/job-beeper-dev`, both volume `_data` directories, pre-release staging directory, daily SQLite snapshot directory, snapshot script, and its systemd service/timer. Excludes: `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `node_modules`, `jobs.db`, `jobs.db-wal`, `jobs.db-shm`. Thus it backs up repo/env/config content (encrypted by Termalin) and volume config/token, while consistent sqlite snapshots are archived as separate `.sqlite3` files.
- Draft schedule is daily at 03:00 UTC, keep last 7, Termalin storage. This is one hour? correction: 15 minutes after 02:45 UTC snapshot timer, allowing snapshot completion before scheduled archive. No SQLite database dump option was supplied because Termalin database dump helper supports postgres/mysql only; separate SQLite online snapshots are included as files.
- `backup_list` confirms job remains DRAFT waiting for owner confirmation. **No encrypted Termalin archive exists yet.** Owner must open the link and confirm it to create the encryption key. After confirmation, call `backup_create` immediately for a first archive with label `Initial pre-release backup of production and development Job Radar`; then verify success and archive size with `backup_list`. Daily schedule then runs at 03:00 UTC. Do not claim off-host encrypted backup complete until this succeeds.

### Safety and next action
- This backup work did not modify application source, runtime config, live databases, source enablement, container images in use, container lifecycle, or send notifications. Production `v2-radar-1` and dev `job-radar-dev` remained running; volumes were only read for online snapshots and config copies.
- Production still requires a separate, explicit deployment approval. This backup is preparation only, not permission to deploy.
- Exact next action: user confirms the Termalin draft using the link above. Then assistant calls `backup_create` to generate the initial encrypted archive and verifies it in `backup_list`. Until confirmation/archive success, state is: consistent local snapshots + daily local snapshot timer installed; encrypted off-host archive pending.
- Continuation: read this handover first. Use Termalin `hosts_list`, metrics/alerts, then `ssh_exec` directly on host `job-radar`; do not ask user to run commands when Termalin can safely run them. Inspect output after every operation. Do not modify production unless separately approved. Keep updating both handovers with each new learning and exact operation/result.



## 2026-11-06 follow-through — user reviewed backup settings; Termalin still reports DRAFT
- User shared a screenshot of the Termalin 'Confirm backup' form for `Job Radar production and dev daily backup` and said the configs were confirmed. Screenshot displays the proposed paths/excludes, daily schedule at 03:00 UTC, retention 7, Termalin storage and a visible `Confirm` button; it does not show a success/completion state after clicking.
- Assistant re-queried `backup_list` twice after the user's message. Termalin still reports job `ae51ea55-d396-417e-8792-8ddfc1cd66c7` as `DRAFT, waiting for the owner to confirm`; recent archives: none. Therefore the encrypted backup job is NOT yet confirmed and no encrypted archive has been created. Do not call `backup_create` while status remains DRAFT.
- Next step: user must click the final Confirm button in that Termalin form and complete any cabinet confirmation step. Afterward, re-run `backup_list`; only when the job is no longer DRAFT should `backup_create` be called for the initial archive, then verify successful archive in `backup_list`.
- Local backups remain established: production/dev SQLite online snapshots, runtime configs/token copies, running image tar, SHA256 manifest, daily 02:45 UTC systemd snapshot timer. Final local snapshot service succeeded, both DBs passed `PRAGMA integrity_check`, and all 9 manifest entries verified. The Termalin encrypted off-host layer remains pending.
- No production service/config/database/container mutation occurred in this turn. Do not claim full backup complete until the encrypted archive succeeds.

## 2026-11-06 follow-through — confirmation click did not change Termalin backup state

- User reported clicking Confirm in the Termalin backup-draft dialog; UI button then appeared disabled/stuck and dialog remained visible in screenshot.
- Assistant re-queried `mcp__Termalin__backup_list` for host `job-radar` after the click. Authoritative response still reports backup job `ae51ea55-d396-417e-8792-8ddfc1cd66c7` as `DRAFT, waiting for the owner to confirm`; recent archives list is empty. Therefore confirmation has NOT completed and encrypted archive has NOT run. Do not call `backup_create` while still DRAFT.
- Screenshot shows the confirmation modal still open. Button appears orange in the captured frame, but no success toast/page state is visible. Possible browser request/UI hang is only an inference; do not treat disabled button as successful confirmation.
- Safe next troubleshooting: keep existing draft; don't create a duplicate. Wait briefly, then refresh the Termalin cabinet page and re-open the same draft link `https://termal.in/account#backup-draft=ae51ea55-d396-417e-8792-8ddfc1cd66c7`. Check whether job appears in confirmed backup jobs or remains draft. If still draft, try confirmation in a fresh browser tab/window, allow pop-ups/session, and inspect any visible inline error/toast; user can report exact error text. Do not repeatedly click rapidly. If UI still hangs, use Termalin support/UI or reconnect and then check `backup_list` again.
- Local backup prep remains valid: snapshot service and daily 02:45 UTC timer installed; both SQLite online snapshots passed integrity checks; all 9 checksum manifest entries verified. No encrypted off-host archive exists yet.
- No production application or database was changed by this confirmation troubleshooting. No container restart/build, config mutation, source activation, or notification send. Keep production and dev services untouched.
- Next agent must first call `backup_list` before attempting `backup_create`; only execute first archive after Termalin reports job status is confirmed (not DRAFT). After run, verify archive result and size with `backup_list`.


## 2026-11-06 follow-through — rechecked backup draft after user retry
- User asked to check again after reporting that the Confirm button appeared disabled/stuck. Re-read the latest handover and knowledge-transfer instructions first, then queried Termalin `backup_list` for host `job-radar`.
- Authoritative status is unchanged: `Job Radar production and dev daily backup` (`ae51ea55-d396-417e-8792-8ddfc1cd66c7`) remains `DRAFT, waiting for the owner to confirm`; recent archives: none. No encrypted backup has run.
- Do not call `backup_create` until `backup_list` reports a confirmed/active backup job. Do not create a duplicate draft. Owner should retry same draft link in a fresh tab/session or inspect visible inline errors; confirmation appears to remain client-side/UI-pending even after click. Link: `https://termal.in/account#backup-draft=ae51ea55-d396-417e-8792-8ddfc1cd66c7`.
- Local snapshot system remains established and previously verified: daily timer at 02:45 UTC; consistent production/dev SQLite snapshots passed integrity checks; checksum manifest verified. Encrypted off-host backup is still pending.

## 2026-11-06 — Development container rebuilt from tested Ashby patch; end-to-end Ashby dev ingestion passed

### Why the rebuild was needed
- User chose to continue development despite Termalin's encrypted-backup confirmation dialog being stuck. Encrypted off-host archive remains pending; this does not block dev-only work.
- Read current handover/knowledge transfer/reference before operations. The dev service is Compose project `job-radar-dev`, config `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`, loopback binding `127.0.0.1:8001->8000`, and separate named volume `job-radar-dev_radar-dev-data:/data`. Production is separate project `v2`, container `v2-radar-1`, public port 8000, volume `v2_radar-data:/data`.
- Older dev container was created 2026-10-16, image ID `sha256:c41b89e3ee05ba5abe3de2618b2d86d51322baa47ceeaaab2b53f98e3eedba92`. Its Ashby collector was present and registered, but `source_status()` and `latency_summary()` used hard-coded four-source loops; `dedupe_candidates()` also had a hard-coded filter excluding Ashby. Host checkout at `7ebc38b` was newer than the image but still older than tested patch.

### Source and build provenance
- Tested source worktree: `/tmp/job-beeper-ashby-dedupe-test`, detached commit `c93f0414e8f99540d6004f012e8cb286e32bf1f6`. It has local `M v2/config.json` and `?? .venv/`; preserve both. Its `v2/radar.py` and `v2/test_radar.py` diffs are empty. Its modified `v2/config.json` is NOT copied into build; tracked files are built from `git archive HEAD`.
- Clean tracked-only source context: `/opt/job-radar-dev-release-c93f041`, created using `git archive`. Context size 3.4 MB, Docker transferred 771.56 KB. No `.env` or `.venv` in build context. Source `radar.py` hash in context/worktree: `b87bc0a2aaceb29df6ebdc58174d5f910b8fa060b64449e6adb8e07ee56423da`.
- Compose and dev config hashes in release context match the existing home checkout exactly: compose `969f7dde98ba60abc60095bae17511869d0affe4d24c386fca6d5dff1f6258d8`; `config.dev.json` `fe3b4e5a32a484cb0abbc9fee8faf3377dab26b5eb414725618309bcb520d348`. Therefore existing Compose and config were reused unchanged.
- Previous dev image kept under rollback tag `job-radar-dev-radar:pre-c93f041-20261106` (old image ID `sha256:c41b89e3ee05ba5abe3de2618b2d86d51322baa47ceeaaab2b53f98e3eedba92`). New candidate built as `job-radar-dev-radar:c93f041`; new image ID `sha256:dee60f11b6364abb1457695d5f74e6faf247ab6e0e4f824767ed4eebd0bc56f3`; `radar.py` hash inside image equals release source hash above.
- New image was built with `Dockerfile` from the clean context. Python syntax compile passed. Full V2 test suite ran inside the actual Python 3.12 image with Docker network disabled: **137 tests in 20.819 seconds, OK**, including `test_dedupe_candidates_includes_ashby_from_collector_registry`, all Ashby collector tests, source status and latency tests, Greenhouse tests, and LLM router/extractor tests. This verifies the exact image code without making live provider requests.
- The first background build attempt exited before running Docker because Termalin shell is `/bin/sh` and `set -o pipefail` is unsupported. Re-ran with POSIX `set -eu`; build/test job `gn4za1n81k` finished exit code 0. No application changes resulted from first attempt.

### Dev-only container recreation and preserved runtime settings
- Promoted candidate to `job-radar-dev-radar:latest`, then recreated only dev service with `sudo docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --no-deps --no-build --force-recreate radar` from `/home/ubuntu/job-beeper-dev`. No Compose build was invoked from the older checkout; the image was built from the clean tested worktree source.
- New dev container uses image ID `sha256:dee60f11b6364abb1457695d5f74e6faf247ab6e0e4f824767ed4eebd0bc56f3`, still binds `127.0.0.1:8001->8000`, still uses named volume `job-radar-dev_radar-dev-data:/data`, and still mounts `/home/ubuntu/job-beeper-dev/v2/config.dev.json` read-only to `/app/v2/config.json`. Project remains `job-radar-dev`.
- Effective dev config after recreate: version 11; notifications false; LinkedIn false; Naukri true; Instahyre/Greenhouse/Ashby false; Ashby allowlist contains OpenAI and PostHog; poll interval Ashby 1800s. Telegram bot token and chat ID are blank.
- Actual environment flags were preserved from `/home/ubuntu/job-beeper-dev/.env`: `GEMINI_EXTRACTION_ENABLED=true`, `GEMINI_MATCHER_ENABLED=true`, `LLM_ROUTER_ENABLED=true`, `LLM_ROUTER_MATCHER_ENABLED=false`. Config/API shadow status showed provider router enabled, matcher enabled, `calls_today=20`, daily limit 20, configured providers Groq/Gemini/OpenRouter. Do not echo any provider key. For the controlled Ashby one-shot run below, all four AI gates were disabled only for that `docker exec` subprocess via `-e`; persistent container env and `.env` were not changed. Daily quota already at limit, and no additional LLM call was made by the smoke tests.
- Dev `/health`: status ok, version 2.0.0. `/api/source-status` and `/api/latency-summary` now both list all five registered sources including Ashby. Ashby `enabled=false` as expected before the one-shot run; last_run initially null. Dedupe route source filter in running file now uses `SOURCE_NAMES` and bound SQL parameters.

### Ashby live dev smoke and ingestion
- Direct public GET-only smoke from container: OpenAI board returned 815 jobs, all 815 with published timestamps; PostHog board returned 8 jobs, all 8 with timestamps. Calls used only explicit configured public boards; no database write, scheduler enablement or notification.
- Controlled one-shot end-to-end test invoked `run_source('ashby', config)` inside `job-radar-dev`, with in-memory `ashby_boards` narrowed to OpenAI only. It did NOT change persisted config or scheduler source-enabled flag. The subprocess had `GEMINI_EXTRACTION_ENABLED=false`, `GEMINI_MATCHER_ENABLED=false`, `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`; runtime config asserted notifications false, LinkedIn false; `credentials_available()` asserted false. Thus no LLM provider call or Telegram delivery was possible for this one-shot run.
- Result: OpenAI Ashby collector returned 815; `run_source` recorded 815 jobs seen and 815 new; zero source error. Development DB jobs rose from 7,158 to 7,973 (815 added). `PRAGMA integrity_check` returned `ok`. The persisted config still keeps `source_enabled.ashby=false`; API source status shows Ashby disabled with last run and 815/815 counts. This is a one-time validation, NOT scheduler activation.
- Daily summary after the run: total jobs discovered 817 for 2026-11-06 Asia/Kolkata; matched 0, alertable 0, alerts sent 0. Dedupe endpoint considered 7,973 jobs, 4,678 identity groups and returned 0 real cross-source candidates in this dataset. This means no real duplicates were surfaced in the current data, not that endpoint is broken; the focused regression test proves the Ashby+LinkedIn synthetic candidate path.

### Backup / rollback state after dev release
- Fresh pre-ingestion snapshot taken before one-shot run. After run, the daily snapshot service was executed again; both current snapshots pass integrity: production 19,853 jobs / 68,042,752 bytes; dev 7,973 jobs / 40,157,184 bytes.
- Exported new current dev image and previous rollback image to `/var/backups/job-radar-pre-release-20261106/dev-release-c93f041.tar` (61,205,504 bytes); archive contents inspected with `sudo tar -tf`. Existing `running-images.tar` retains previously running prod + old dev image. The new dev release tar is separately included in the SHA manifest.
- Daily SQLite snapshot timer remains enabled at 02:45 UTC. Snapshot service final result success. `sha256sum -c /var/backups/job-radar-pre-release-20261106/SHA256SUMS` verified all 10 entries (current and pre-release snapshots/config/token copies/images). Disk: 45 GB total, approx 8.2 GB used, 37 GB free (19%).
- Termalin encrypted backup draft `ae51ea55-d396-417e-8792-8ddfc1cd66c7` remains DRAFT because the confirmation UI did not complete; no off-host encrypted archive yet. User explicitly chose to proceed with dev work despite this. Do not claim encrypted backup complete. Local backups and old image tag support dev rollback.

### Production safety and exact next actions
- Production container remains unchanged: image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, original StartedAt `2026-10-12T03:44:45.989462781Z`, RestartCount 0. Port 8000, Compose project `v2`, volume `v2_radar-data:/data` untouched. All operations/recreates above were scoped to `job-radar-dev` and port 8001.
- No production code/config/database/volume change, no source enablement, no Telegram send, no deployment. Do not confuse successful dev validation with production approval.
- Next product step: review Ashby run's jobs/match quality using aggregate, privacy-safe breakdowns, then plan a limited dev scheduler soak. Keep Ashby disabled in saved config until user decides to enable it on dev. Keep notifications off, Telegram credentials blank, LinkedIn off; keep LLM calls off or capped during soak. Monitor source freshness, new-job yield, dedupe, alertability and CPU/memory. Only after successful dev soak and reviewed backup/rollback can production release be proposed; separate explicit production authorization required.
- Handover instruction for next model: read this file, `JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `JOBBEEPER_REFERENCE.md`, and `LLM_PROVIDER_ROUTER.md` first. Termalin is connected; prefer direct `hosts_list`/metrics/alerts/`ssh_exec`, inspect results after each command, and update both handovers after each task. Never touch production unless explicitly approved.
## 2026-11-06 — Matcher false-positive fix, fingerprint invalidation, and dev runtime validation

### False positive diagnosis and fix
- After the dev Ashby one-shot Bolna run, `Conversation Quality Analyst` had persisted as a profile match (score 62) because its job description mentioned “forward deployed engineer” plus LLM/AI skills, despite the title being a non-engineering analyst/internship role. This was a confirmed false positive from `match_details()` description-based role fallback.
- Changed `match_details()` so description-derived target-role fallback is permitted only when the title itself includes a generic `developer` or `engineer` signal. Direct title-role hits, Software Development Engineer/SDE aliases, full-stack aliases, and skill+generic developer/engineer title matches remain unchanged.
- Added regression tests: (1) `Conversation Quality Analyst` with “forward deployed engineers” in the description must not match; (2) `Product Engineer` can still match through a target-role phrase in description; existing JavaScript Developer and Software Development Engineer tests continue passing.
- A test fixture initially used plural “software engineers”, while `phrase_hits` matches configured singular phrase “software engineer” exactly; corrected the fixture to singular rather than broadening the matcher. Targeted test suite then passed.

### Persisted evaluation stale-cache issue found and fixed
- First one-shot call to `refresh_job_evaluations(config)` returned 0 because the evaluation invalidation key was only a hash of config JSON. A matcher code change with unchanged config does not invalidate stored rows, so `Conversation Quality Analyst` remained match=true in persisted evaluations even though `match_details()` now returned false.
- Added `MATCHER_RULES_VERSION = 2` into `_config_fingerprint()` payload, with a code comment instructing developers to increment it whenever deterministic matching/alertability rules change. This forces `refresh_job_evaluations()` to re-evaluate persisted jobs after a matcher rules version bump, even if config itself is unchanged.
- Added test `test_matcher_rules_version_changes_evaluation_fingerprint`.
- Important rollout implication: matcher rules version bump causes an entire database's stored jobs to be re-evaluated on the next `refresh_job_evaluations()` call. In production, this may change match/alertability decisions and notification ledger states; do not deploy without a reviewed release/notification plan. The version bump has only been exercised on dev in this session.

### Test evidence and source commits
- Commits on `v2-live-radar`: `4e81d82987f041b7d8c9b5f41bb9578d50bb3967` (role fallback fix); `e1fad74eb622a3d01bf6dc481eda8e83c3620915` (false-positive test); `99e661e6418bf2752d504a82dd01f6408fad0f0a` (singular phrase test fixture); `f4d56b198dbc89ef98f73ce2191efc55d44c8186` (matcher version in fingerprint); `f2a7998ce92641a5e7e62122d7c7a6ba2b71b35d` (fingerprint test).
- Targeted five matcher/fingerprint tests passed under the isolated Python 3.10 test venv.
- Full V2 suite passed twice after the code changes: 140 tests in 18.924s in the isolated worktree, then 140 tests in 20.409s inside the new Python 3.12 Docker image with Docker networking disabled. `py_compile` passed in the Docker image. No live LLM provider requests were possible in the image test (`--network none`).

### Dev-only image deployment
- Clean tracked-only build context `/opt/job-radar-matcher-version-2-f2a7998`, sourced by `git archive` from clean detached worktree `/tmp/job-radar-match-fingerprint` at `f2a7998ce92641a5e7e62122d7c7a6ba2b71b35d`. Host source hashes: `v2/radar.py` `31a4cad595dfb78593093b483208e432df04fde5f50fb93614c8c4feb2202b3d`; `v2/test_radar.py` `3a2c419c3e8e316aa57ea813b02e9b7140018fb95a15e83019380c803e32c955`. Hashes inside built image match exactly.
- New image tag `job-radar-dev-radar:f2a7998`, image ID `sha256:84f3f2c0ede06ef4bcef97a409617ba528d4b8bf3a14e798b3ef7b504d134b8d`. Container `job-radar-dev` was recreated using only dev Compose project `job-radar-dev`, with same loopback binding `127.0.0.1:8001`, same dev named volume `job-radar-dev_radar-dev-data:/data`, and same bind-mounted `config.dev.json`. Rollback image preserved as `job-radar-dev-radar:pre-fingerprint-f2a7998` (previous dev image ID `sha256:5db9d3f712c198492eeac6229072258f1827b7ecd63578da352503a21eeb2740`). Earlier c93 rollback images also remain tagged/exported.
- Initial health request immediately after recreate returned a connection reset while Uvicorn was still in application startup. Container was running with no restart/OOM; after a short wait application startup completed and `/health` returned OK. This was startup timing, not an app crash.

### Dev database reevaluation and Bolna outcome
- At startup, the enabled dev Naukri source completed its first cycle (`seen=335`, `new=0`, `error=null`). This ran `refresh_job_evaluations()` under matcher rules version 2 and recalculated the existing 7,979 development jobs. Evaluation rows all have one current fingerprint; their evaluation timestamps span `2026-11-05T20:25:12.675200+00:00` to `2026-11-05T20:25:37.673249+00:00`. Hence a later explicit `refresh_job_evaluations()` call returned 0: startup had already completed the full reevaluation. The explicit `refresh_notification_decisions()` call then adjusted 18 development ledger decisions.
- After reevaluation, six stored Bolna jobs: `AI Solutions Engineer` remains match=true, score 73; `Conversation Quality Analyst` is now match=false, score 32, reasons include `no configured target-role match`; remaining four jobs are non-matches. All six alertable=false because dev notifications are disabled. Total Ashby evaluation counts: 820 match=false / alertable=false; 1 match=true / alertable=false (AI Solutions Engineer).
- Dev config remains version 11, notifications false; LinkedIn false, Naukri true, Instahyre false, Greenhouse false, Ashby false. Ashby boards OpenAI/PostHog remain configured but scheduler-disabled. Telegram token/chat ID remain blank. AI gates persist as before: Gemini extraction true, Gemini matcher true, LLM router true, routed matcher false; daily LLM count was previously 20/20. No new provider calls were performed in the one-shot matcher reevaluation (the process explicitly disabled all four AI gates).
- Dev health: `status=ok`; API source status lists all five sources, Ashby disabled with last one-shot test counts 6/6; Naukri startup run seen 335/new 0. DB has 7,979 jobs and 7,979 evaluation rows; `PRAGMA integrity_check=ok`. Production image ID, StartedAt and RestartCount remain unchanged (`sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, StartedAt `2026-10-12T03:44:45.989462781Z`, RestartCount 0).

### Backup and next action
- Refreshed local snapshots after the new image/reevaluation: production DB 19,853 jobs / 68,042,752 bytes, dev DB 7,979 jobs / 40,194,048 bytes, both `PRAGMA integrity_check=ok`. Exported final matcher image plus previous dev rollback image to `/var/backups/job-radar-pre-release-20261106/dev-release-f2a7998.tar`; SHA256 manifest now has 11 entries and every entry verified OK. Daily local snapshot timer remains enabled at 02:45 UTC.
- Termalin encrypted backup job `ae51ea55-d396-417e-8792-8ddfc1cd66c7` remains DRAFT after repeated UI confirmation attempts; user chose to continue dev regardless. Local snapshots are verified; off-host encrypted archive remains pending. Do not claim remote encrypted backup succeeded.
- Production untouched. All code deployment, database reevaluation and source testing in this milestone were confined to dev port 8001 / dev volume. Do not enable Ashby scheduler or notifications without user direction.
- Exact next step: run a short dev-only observation period with Ashby still disabled, Naukri active, notification false. Review current matcher distribution and relevance of Bolna/other candidates using aggregate safe metrics. Consider a follow-on matching test set before enabling any ATS source. Do not trigger LLM calls while daily cap remains exhausted. Keep production release gated due matcher version 2 potentially recalculating all production jobs/notification decisions.



### Clarification — explicit dev refresh was already complete
- After container startup, a separately invoked `refresh_job_evaluations(config)` returned `0` because the Naukri startup `run_source()` had already refreshed all 7,979 evaluations under matcher rules version 2. This was confirmed by identical current fingerprints across all rows and evaluation timestamps clustered between 20:25:12 and 20:25:37 UTC. `refresh_notification_decisions(config)` then changed 18 dev ledger decisions; notifications remained disabled and Telegram credentials blank, so no delivery occurred.

## 2026-11-06 — Naukri description mismatch evidence and provisional matcher benchmark
- Continued from the matcher v3 dev deployment at source commit `5e96599e01ea0a605f43f9a46991d6ecd64bd971`; the running dev image remained `sha256:c4076ee204c64164b5db72e6de92c1f26075ee4b012093e38251dc1e53cf1a6f`. The home checkout `/home/ubuntu/job-beeper-dev` is stale at `7ebc38b7c321847e74895557551478c3ff11bd4a` with protected local artifacts; source work was done only in `/tmp/job-radar-naukri-location-v3`.
- Active Naukri feed source is the separate public repo `AvinashBhalla/job-beeper-naukri-relay`, branch `naukri-relay`; feed metadata observed: `updated_at=2026-11-05T20:54:25.142767+00:00`, 330 jobs, blob SHA `61b7cd70d4b0b8d9a0f8185620aedd42b8dcfb49`. A private-app-repo raw URL 404 was a wrong URL, not a feed failure.
- Novisync Solutions India / Python Developer / source ID `nk-nk-051126503145` in the relay already has a business-strategy/client-service responsibility body and technical terms only in a trailing skills-style keyword tail. The corresponding dev DB record id 7113 is match=true, score 88, due to title, skill and experience matching. Collector preserves the relay description; separate `skills_detected` data is absent for this row. Original employer posting is not yet independently verified, so classify as review-only rather than confirmed false positive.
- Grounded comparison cases: Ashok Maheshwary & Associates AI Automation Engineer has substantive hands-on AI/automation/workflow responsibilities (positive); Iqvia Biotech QA Automation Engineer has substantive automated testing/framework/CI responsibilities (soft-positive/adjacent). Existing Bolna Conversation Quality Analyst and Karnex explicit-Pune cases remain negatives covered by matcher regression tests.
- Added provisional anonymized seed: `v2/fixtures/matcher_quality_benchmark.json`, `v2/matcher_quality_benchmark.py`, `v2/test_matcher_quality_benchmark.py`. It evaluates 5 examples using `v2/config.dev.json` and `match_details()`, excludes one unresolved review item from precision scoring, and surfaces its observed match. Output: 4 scored / 1 review-only; 4 scored passed, 0 failed; Novisync still flagged review-required and matching at 88. The 2 new tests passed, and full V2 discovery passed **145 tests in 18.402s** in a throwaway Python 3.12 container with `--network none` and read-only mounts. No live LLM calls.
- No matcher logic/config/runtime changes; no dev restart, image rebuild, DB mutation, source enablement or Telegram notification. Dev notifications remain off and provider daily budget had already been reached; no further provider calls. Production untouched.
- Next: verify the employer's original Novisync posting or gather more independent mismatch examples; expand a manually reviewed benchmark before considering a more general content-quality gate. Never reject developer-title matches based on one noisy Naukri record. Preserve current source defaults and do not promote to production without separate approval. Termalin encrypted backup remains a DRAFT; local snapshot verification is not the same as an off-host encrypted archive.

## 2026-11-06 — Current feature branch, multi-user priority and referral roadmap

- New product priority: multi-user support is now the next milestone, replacing the earlier "multi-user later" assumption. Goal: multiple users, admin/user roles, isolated candidate preferences/evaluations, and independent Telegram connections/delivery for a small real-user beta.
- Read `docs/MULTI_USER_AND_REFERRAL_ROADMAP.md` for the architecture, schema proposal, security requirements, migration sequence, beta metrics and HAPPPY-like referral roadmap.
- Shared ingestion stays shared: one source scheduler and normalized/canonical job pool. User-specific: preferences, job evaluations, saved/applied state, notes, notification ledger and Telegram connection. Current global config, `job_evaluations(job_id)`, `notification_ledger(canonical_opportunity_id)` and `X-Config-Token` authorization are not multi-user safe.
- Recommended first auth design: admin/user roles; Argon2id passwords; opaque server-side sessions with hashed token storage; HttpOnly/Secure/SameSite cookies; CSRF; rate-limited login; explicit CORS origins. The current browser token in sessionStorage is a temporary single-user workaround, not a login system.
- Recommended Telegram design: one platform bot token on the server and a one-time expiring deep-link to bind each user's chat_id to their account. Do not require users to paste their own bot tokens for first beta. User-scoped notification ledger and no historical replay are mandatory.
- HAPPPY-like future: application tracker -> authorized contact discovery -> relevance ranking -> human-reviewed referral/follow-up draft -> user-authorized Gmail/Outlook draft -> reminder and response tracking. No automated LinkedIn messaging/connection requests or access-control/rate-limit bypass.
- 2026-11-06 feature evidence: local feature branch `feat/naukri-rich-descriptions-20261106` has commits `093c475` (server-side search across 72h) and `727bdb9` (Naukri Markdown/structured details). The running dev image matches the feature worktree's `v2/radar.py`, `dashboard/app.js`, and `dashboard/index.html` hashes. Full V2 suite passed 149 tests in 18.723s in a throwaway Docker container with `--network none`. These feature commits were local at audit time; do not assume they are on remote `v2-live-radar` until pushed and verified.
- Runtime audit: dev `job-radar-dev` is healthy on loopback port 8001; Naukri enabled; LinkedIn/Instahyre/Greenhouse/Ashby disabled; notifications off; Telegram credentials blank. Production `v2-radar-1` on port 8000 remains unchanged. Ordinary dev checkout is stale and has protected local config/env artifacts; work only from the feature worktree and preserve its pending docs/benchmark files.
- Termalin encrypted backup job is still DRAFT; local snapshots are not an off-host encrypted backup.
## 2026-11-06 — Six-minute Naukri dev soak and explicit-work-location quality fix

### Read-only dev soak
- Re-read the latest handover, knowledge-transfer, reference and router runbook before this task. Only dev service `job-radar-dev` at `127.0.0.1:8001` and dev volume were used; production service `v2-radar-1` stayed untouched.
- Captured six-minute read-only observation from 2026-11-05T20:35:47Z through 20:41:59Z, sampling health, source-status and Docker stats every 60 seconds. Uptime remained continuous; health returned ok in all seven samples; container CPU ranged 0.13–0.50%, memory 30.95–51.12 MiB. One scheduled Naukri poll completed at 20:40:41Z: jobs_seen=336, new_jobs=0, error=null. Last seven minutes contained two Naukri runs, 668 total jobs_seen, zero new jobs, zero failed runs; DB integrity ok. This is a short soak, not a multi-day reliability claim.
- Metrics/alerts check: no open Termalin alerts. Latest server sample at 20:33 UTC: CPU 0.9%, memory 50.2%, disk 18.3%, load1 0.02; over 6h CPU average 16.6% (peak 60.5), memory average 52.85% (peak 58.2), disk average 17.97% (peak 18.3), CPU steal average 10.98% (peak 40.1%). No action was taken on the host.

### Corrected source-trend audit
- Earlier exploratory SQL used SQLite `datetime('now', ...)` with a space separator against ISO timestamps containing `T`, which lexically over-counted records from the cutoff date. Re-ran with timezone-aware ISO cutoff strings; use these corrected numbers only.
- Naukri last 24h: 288 source runs, 95,467 jobs_seen, 176 new jobs, zero failed runs; median run interval over last 6h was 5.00 minutes. Last 6h: 72 runs, 24,050 seen, 26 new, zero failed. Last 1h: 12 runs, 4,046 seen, zero new, zero failed. Latest recorded job scan is 338 seen / 0 new with no error.
- Of the 176 Naukri jobs newly discovered over 24h, publication dates (date-level precision) were 104 in the last day, 65 one-to-three days old and 7 three-to-seven days old. This means 169/176 were dated within 3 days. These are date-only timestamps, not exact posting times; discovery latency is intentionally NULL for Naukri.
- Before the location-quality fix, the current profile matcher passed 4/176 Naukri jobs from the 24h window; after version 3 reevaluation it passes 3/176. The last 6h cohort had 26 new Naukri jobs and zero matches; primary rejection reasons were 16 above candidate experience, 4 excluded titles, 4 above configured max experience and 2 outside target location. These outcomes align with the configured 2-year candidate / max-3-year profile; no evidence justified loosening the experience filter.
- Ashby remains historical one-shot data only: 821 jobs, 1 match (the Bolna AI Solutions Engineer), 820 non-matches. Ashby is still disabled in saved config. OpenAI board remains a poor match for the India-focused profile; Bolna yielded one plausible AI/automation match after the description-role false positive was removed.
- `/api/latency-summary` contains 821 Ashby samples and zero Naukri samples. Naukri is date precision and deliberately excluded from exact seconds; Ashby samples reflect published-to-first-discovery age on first import (including old historical OpenAI postings), not just the scheduled polling interval. Do not interpret this as scan cadence; source-runs timestamps are the measure for poll cadence.

### Naukri matching-quality findings and code fix
- Manual review of four Naukri matches in the 24h cohort found two data-quality problems: (1) Karnex `Software Engineer` listing source metadata said `Pune, Chennai, Bengaluru, India`, while its description explicitly said `Work Location: Pune`; (2) Novisync `Python Developer` had a business-development/client-relationship description with a trailing detected-skill list, despite matching at scores 88 and 82. The latter remains flagged for upstream feed/description-quality investigation; no broad heuristic was added because the evidence set is too small and could suppress legitimate technical jobs.
- Implemented `extract_explicit_work_location()` and `job_location_for_matching()` in `v2/radar.py`. A clearly labelled `Work Location:` in the description takes precedence for profile matching and shadow-candidate filtering; an interview venue is not mistaken for work location. The persisted `jobs.location` field is intentionally not rewritten, preserving original source metadata and canonical identity. The rule applies only when an explicit label is found; otherwise original source location remains the fallback.
- Added three tests: broad multi-city feed metadata overridden by explicit Pune location (must reject), explicit Bengaluru location overrides stale Pune feed metadata (must match), and parser stops at `INTERVIEW VENUE` rather than using it as work location. Matcher rules version incremented to `MATCHER_RULES_VERSION = 3`, ensuring persisted evaluations are recalculated under the new deterministic location rule.
- Regression evidence: targeted location tests 3/3 passed; full V2 suite 143/143 passed under isolated test venv and again inside the actual Python 3.12 Docker image with networking disabled; py_compile passed. Image unit tests made no provider HTTP calls.
- Confirmed live stored Karnex record after reevaluation remains source location `Pune, Chennai, Bengaluru, India` but now `match=0`, score=0, reason `location outside configured targets`. This removes one known false match. Novisync business-description listing remains match=true (two source records) and is intentionally documented for follow-up rather than silently suppressed.

### Source commits and deployment
- Branch `v2-live-radar` now includes commits `7a0258029f8ad6691b31be1c58b34e16e99be0da` (explicit work-location matching and shadow filter), `786c1b735b6afd39387561cbdd2532322cd4e128` (three location regression tests), `80542be3af9e0618003dad08d7938bcf7837a5f6` (corrected regex escaping discovered by tests), and `5e96599e01ea0a605f43f9a46991d6ecd64bd971` (matcher version 3).
- Clean tracked-only build context `/opt/job-radar-naukri-location-v3-5e96599` came from detached worktree `/tmp/job-radar-naukri-location-v3` at commit `5e96599e01ea0a605f43f9a46991d6ecd64bd971`; no `.env` or `.venv` in context. Source hashes: `v2/radar.py` `6484e88edbbf773c271e94871994c73281b0ca5a7cfd2b01ae4f9af39cca3143`; `v2/test_radar.py` `3a463866337113fec049afa1a3da1702966f55dc5eb8230b17b4228550516f55`. Hashes inside image matched.
- New image `job-radar-dev-radar:5e96599`, image ID `sha256:c4076ee204c64164b5db72e6de92c1f26075ee4b012093e38251dc1e53cf1a6f`. Recreated only `job-radar-dev` with same Compose project, `127.0.0.1:8001` binding, named volume `job-radar-dev_radar-dev-data:/data`, bind-mounted dev config, and VM `.env`. Existing dev image retained as rollback tag `job-radar-dev-radar:pre-work-location-v3` (image ID `sha256:84f3f2c0ede06ef4bcef97a409617ba528d4b8bf3a14e798b3ef7b504d134b8d`).
- Startup initially returned connection resets while performing version-3 reevaluation; container stayed running, no OOM/restart, then Uvicorn completed startup. Health is now ok. Startup Naukri run seen=338/new=0/error=null. Database contains 7,979 jobs and 7,979 evaluations, one current fingerprint, PRAGMA integrity_check=ok.
- Final match totals: Naukri 274 matches / 7,158 jobs, zero alertable; last 24h 3 matches / 176 newly discovered. Ashby 1/821. Daily summary for 2026-11-06 Asia/Kolkata: 823 discovered, 1 matched, 0 alertable, 0 sent. Dev notifications false; Telegram token/chat ID blank; LinkedIn false; Ashby false; Naukri true. LLM call counter remains 20/20; do not trigger new model calls until budget resets. No matcher rule sends Telegram.

### Backups and production safety
- Pre-deploy snapshot taken; post-deploy snapshot refreshed successfully. Final snapshots: production 19,857 jobs / 68,063,232 bytes; development 7,979 jobs / 40,194,048 bytes; both PRAGMA integrity_check=ok. Production's count advanced while its normal service continued; no production restart or change was made.
- Exported final dev image plus previous dev rollback image to `/var/backups/job-radar-pre-release-20261106/dev-release-5e96599.tar` (61,079,040 bytes), inspected tar entries. Added its SHA-256 to manifest. `sha256sum -c /var/backups/job-radar-pre-release-20261106/SHA256SUMS` passed all 13 entries. Disk 45 GB total, 8.3 GB used, 37 GB free (19%).
- Production remains image `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, StartedAt `2026-10-12T03:44:45.989462781Z`, RestartCount 0. No production code, config, DB, volume, source, or notification change. Termalin encrypted backup remains a draft; local verified backups exist, off-host encryption still pending.

### Next actions
- Continue source observation. Keep Naukri active, Ashby/LinkedIn/Greenhouse/Instahyre disabled, notifications off, Telegram credentials blank, and LLM provider calls at zero until quota resets.
- Investigate Novisync's title/description mismatch at the Naukri relay layer. Inspect the public relay item's separate `description`, `skills_detected`, title and location fields; consider adding a conservative quality-review flag/test dataset, not a broad description keyword rejection based on one example.
- Build a small anonymized human-reviewed matcher benchmark from recent true positives and false positives (including AI Automation Engineer, QA Automation Engineer, Novisync Python Developer, Karnex explicit work-location case, and the Bolna Conversation Quality Analyst) before tuning role/skill thresholds.
- Consider discovering a broader set of India-focused public ATS boards only after reviewing board relevance and freshness. Do not enable any ATS source or change the dev config without staged testing; production release still requires a separate explicit approval.
- Handover for next run: read the latest versions of this handover, `JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `JOBBEEPER_REFERENCE.md`, and `LLM_PROVIDER_ROUTER.md` before action.

## 2026-11-06 — Feature PR publication status
- Feature branch `feat/naukri-rich-descriptions-20261106` is now pushed to GitHub at `c1004955fb2fe394e56f01f5015634d442aa3c5a`; it includes commits `093c475` (72-hour server-side search) and `727bdb9` (Markdown/structured Naukri descriptions), plus benchmark and roadmap documentation.
- Draft PR #44 targets `v2-live-radar`: https://github.com/AvinashBhalla/job-beeper/pull/44. Do not merge to `main` or deploy production. GitHub `syntax` check was still in progress at the first post-create check; re-check before claiming CI pass.
- Exact feature branch worktree remains `/tmp/job-radar-naukri-location-v3`; ordinary checkout `/home/ubuntu/job-beeper-dev` remains stale/protected and must not be reset/cleaned/overwritten. Dev image code hashes still match the feature worktree; no recreate occurred for this PR/docs operation.
- Local verification: 149 V2 tests passed in 18.723s in a throwaway Docker container with networking disabled; benchmark-focused tests 2/2 passed; benchmark seed reports 4/4 scored examples pass and one unresolved review-only example.

## 2026-11-06 — Multi-user readiness audit findings
- Live dev schema currently has only shared/system tables: `jobs`, `canonical_opportunities`, `job_evaluations`, `notification_ledger`, `source_runs`, `gemini_shadow_cache`; no `user_id` columns or users/sessions/preferences/application tables.
- Global `job_evaluations(job_id)` and `notification_ledger(canonical_opportunity_id)` must be replaced/augmented with user-scoped evaluation and notification records before multi-user alerts.
- One global `/data/config.json` and global `X-Config-Token` protect `PUT /api/config`; `GET /api/config` currently returns config without auth. Protect it before beta. No login/session/role API routes exist. Dashboard stores the token in sessionStorage.
- Telegram delivery uses one global bot token + one global chat ID from environment; delivery claims the global ledger. Implement per-user Telegram linking and a user-scoped delivery worker.
- Applied Jobs is currently browser localStorage (`job_beeper_applied_jobs_v1`), not server-side. Migrate to user-owned `applications` before referral intelligence.
- Full read-only inventory, API scoping recommendations and first implementation cut are in section 11 of `docs/MULTI_USER_AND_REFERRAL_ROADMAP.md`.

## 2026-11-06 — Production checkout drift warning
- Production checkout `/home/ubuntu/job-beeper` was observed at `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, **613 commits behind** its fetched `origin/v2-live-radar` ref. It was not pulled or modified.
- Running production container `v2-radar-1` remains on image `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, port 8000, Compose project `v2`, restart count 0. Never assume checkout and running image are synchronized. No production update is authorized.
- Current feature PR #44 targets `v2-live-radar`; keep production `main` and port 8000 untouched.


## 2026-11-06 — Current multi-user authentication handoff

- Worktree: `/tmp/job-radar-naukri-location-v3`; branch: `feat/multi-user-foundation-20261106`; base: `v2-live-radar` after merged PR #44 (`7b61d74`). Feature commits: `9ffed3f`, `93dea33`, `44a052f`, `27a77cd`, `ea463cb`; CI workflow commit `8b7f210`; documentation/test dependency commit `a5d8b42`. Pushed to GitHub; PR #45 is open against `v2-live-radar`; latest code commit `ea463cb` is awaiting CI and automated re-review.
- Implemented additive SQLite `users`, `sessions`, `login_attempts`, `login_account_attempts`; Argon2id passwords; `admin`/`user` roles; seven-day opaque sessions with hashed session/CSRF values; logout/revocation; same-origin login-Origin validation (use `JOB_BEEPER_PUBLIC_ORIGIN` behind TLS termination) plus concurrency-safe five-attempt/15-minute email/IP reservations plus a twenty-attempt account-wide cap across IPs; hashed keys and successful login resets the account throttle.
- API: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`. Every legacy `/api/*` route requires admin; unsafe admin requests require CSRF; all API responses are no-store. `/health` is public and sanitized. Login Origin validation supports `JOB_BEEPER_PUBLIC_ORIGIN` behind TLS termination. `GET /api/auth/me` and logout work for both roles.
- CLI inside the app container: `python -m v2.auth_admin create-admin --email ...` (first admin only), then `python -m v2.auth_admin create-user --email ...` for invite-only beta users. Passwords are prompted, never command-line arguments. Container DB path is `/data/jobs.db`.
- Dashboard login/account/logout uses cookie sessions; external `?api=` overrides are rejected so credentials cannot be sent to attacker-controlled origins. Ordinary users see a holding screen; the legacy global job feed is not loaded for them. Browser `X-Config-Token` and config-token sessionStorage flow is removed. Global candidate config/evaluations remain admin-only until per-user preferences/evaluations are built.
- Verification: final V2 suite 189 passed in 79.321s in a throwaway `--network none` Docker run (one Node-only test skipped there); Node-enabled dashboard contract 4/4 passed separately in 0.655s; esbuild 0.19.12 JS parse checks passed; dev Compose config resolved. No LLM/Telegram actions.
- Live dev and production were not deployed or migrated. Dev still uses `job-radar-dev-rich-jd:20261106`; production `v2-radar-1` remains unchanged. `JOB_BEEPER_COOKIE_SECURE` defaults true; require HTTPS. The loopback-only dev Compose defaults it false for SSH-tunnel use; production stays Secure. Set `JOB_BEEPER_PUBLIC_ORIGIN` when TLS termination means Uvicorn sees an internal origin. Termalin encrypted backup remains DRAFT.
- Next: verify CI and automated re-review on PR #45, merge into `v2-live-radar` when checks and review threads are clear, then implement user-scoped preferences and evaluations. Keep production untouched.


## 2026-11-07 — Source-run observability continuation checkpoint

- Current base: `v2-live-radar` at `dd7aeb1` (secure auth foundation merged). New isolated branch/worktree: `feat/source-observability-20261107` at `/tmp/job-radar-source-observability-clean`.
- Implemented additive `source_runs` metadata: `run_id`, `outcome`, `duration_seconds`, `error_type`, `http_status`, `retry_after_seconds`, `cooldown_seconds`. Legacy schema migration preserves existing rows.
- Run outcomes: `success`, `failed`, `rate_limited`, `partial_rate_limited`. LinkedIn 429s caught inside a collector are now recorded even when some jobs are returned. Partial results no longer look like a clean success. Sanitized error strings never persist exception URLs/query values. Full applied cooldown duration is stored separately from remaining time; a rate-limited run does not update `last_success`.
- Admin-only `/api/source-status` exposes the latest structured run metadata. Collector registry remains the source of truth for source enumeration.
- Verification on the VM host: 11 focused tests passed; full V2 unittest discovery 196 passed in 91.608s; Python compile and `git diff --check` passed. Test venv: `/tmp/job-radar-observability-venv` (Python 3.10). Docker access was unavailable, so no container validation was run.
- Implementation commit `a2ec0ba59919704c849cb0c5d7ee2e7c18daf6cf` (followed by documentation-only commit `c498ce8`); draft PR #47 targets `v2-live-radar`. GitHub V2 CI #1303 / `42388082207` passed on Python 3.12, including all 196 tests in 28.011s. PR #40 was closed unmerged as superseded by #47. #47 remains draft pending review; do not merge/deploy on CI alone.
- Scope guard: no source cadence, concurrency, retry behavior, enablement, matcher, notification, credentials or deployment changed. Production/shared-dev and their databases/volumes were not touched. No Telegram sends or LLM calls. Test runs left a whitespace-only local diff in tracked `v2/config.json`; parsed keys/values are unchanged and the diff is unstaged/excluded from the PR.
- Separate feature track `feat/user-preferences-evaluations-20261106` / PR #46 remains draft and isolated. Do not merge or promote it.
- Next: push/open draft PR against `v2-live-radar`; pass GitHub CI; then add per-request/page/status-class metrics and partial outcomes for ATS multi-board adapters. Use telemetry to diagnose LinkedIn 429s conservatively, then measure Naukri relay freshness/incremental behavior. Do not evade provider limits or enable new sources without a canary and explicit approval.


## 2026-11-07 — Source-level request metrics and owner preview

- In `feat/source-observability-20261107`, all existing collector GET requests (LinkedIn search/detail, Naukri relay, Instahyre, Greenhouse, Ashby) route through a common request metrics wrapper. It records attempts, responses, exceptions, status class/exact code, existing retry attempts and elapsed request milliseconds. Logical LinkedIn search/feed pages and Greenhouse/Ashby boards are counted separately.
- Additive SQLite metrics: `requests_attempted`, `responses_received`, `request_exceptions`, `http_2xx/http_3xx/http_4xx/http_5xx/http_429`, `retry_attempts`, `request_duration_ms_total`, `http_status_counts_json`, `pages_attempted/succeeded/failed`, `boards_attempted/succeeded/failed`. Old rows remain NULL/unmeasured.
- `/api/source-status` now returns `last_request_metrics` and rolling `last_24h` totals including `measured_runs`, status histograms, retries, request duration average, page/board failures, jobs seen/new jobs and failed/partial run counts. Dashboard Source Health matrix now shows the key 24-hour counters and labels partial run states distinctly.
- Run outcomes add `partial_failed` for mixed page/board results; no retries, request intervals, source enablement, notification or credentials changed. No endpoint URLs, query strings, headers, response payloads, descriptions or secrets are persisted.
- Focused metrics tests: 14 passed. Full V2 suite: 199 passed in 81.744s on Python 3.10; compileall, py_compile and whitespace checks passed. GitHub V2 CI #1307 / `42391947214` passed on the latest implementation commit using Python 3.12: dashboard JS syntax passed, focused tests 32 passed and full suite 199 passed in 27.721s.
- Local owner preview is available on remote 127.0.0.1:8003 with isolated DB `/tmp/job-radar-source-metrics-local/jobs.db`. All source collectors are disabled, notifications off, Telegram and LLM provider credentials blank. The five metrics cards/rows are synthetic preview examples, not live measurements. No source network requests are made. Tunnel: `ssh -N -L 18003:127.0.0.1:8003 ubuntu@130.210.27.197`; browser: `http://localhost:18003/dashboard`. Preview admin: `metrics-admin@local.test`; temporary password is shared only in chat, not in repo docs.
- OAuth remains on the separate PR #46 feature app (remote loopback 8002, owner tunnel 18002). Shared dev 8001 and production 8000 untouched. No deployment or merge is authorized.

## 2026-11-08 — PR merge and branch cleanup audit

- PR #41 was squash-merged to `v2-live-radar` as `4e48836`; the benchmark implementation/test files were already present in the current V2 branch, and the PR contributed its methodology note. The 2 benchmark tests pass; 4 of 4 scored cases pass and one remains explicitly review-only.
- PR #47 was squash-merged to `v2-live-radar` as `dd4d21e`. Latest GitHub V2 CI #1314 / run `42442324585` passed: Python compilation, dashboard JavaScript syntax, focused router/extractor tests and full V2 suite **207 passed**. This is a branch merge only; no container deployment/restart was performed.
- PR #37 closed unmerged because its source-registry change is already in current V2 (`SOURCE_NAMES = tuple(COLLECTORS)`, including Ashby) and its remaining docs were an older static snapshot. PR #3 in the relay repository closed unmerged/deferred because its JobSpy internal method patch lacks independent CI and overlaps relay PR #4.
- PR #35 is now titled `WIP: Promote Job Radar V2 to main — release gate`; it remains draft and dirty/diverged. Do not merge to main until V2/main divergence and the production migration checklist are reconciled.
- PR #46 remains draft. Owner confirmed live Google OAuth sign-in and resume parser smoke test on port 8002. Backlog: missing email/password self-service signup, Google consent branding still `n8nApp`, and preferences save response not surfaced (visible role chip vs backend 'at least one target role' error). Per-user Telegram webhook/delivery E2E remains unvalidated.
- Relay PR #4 remains draft. CI run `42442285937` passed the embedded workflow syntax and 3 publisher contract tests. It has not been merged or dispatched because the VM timer will use its new code on the next five-minute cycle and publish the changed public feed.
- Remote cleanup: removed merged/superseded app branches `feat/matcher-quality-benchmark-20261106`, `feat/source-observability-20261107`, `work/job-intelligence-foundation`, `work/source-run-telemetry-clean`; removed relay branches `feat/structured-naukri-details-20261106`, `fix/relay-schedule-offset`, `fix/vm-only-relay-scheduling`. Kept `fix/linkedin-experience-parser` for later focused transplant; do not merge its full stale branch.
- Full audit and branch inventory: `docs/PR_BRANCH_AUDIT_2026-11-08.md`.
- Deployment boundary unchanged: no changes to shared dev 8001 or production 8000, no public feed dispatch/publish, no Telegram send, no secrets moved.
## 2026-11-08 — Naukri relay merge verified; production LinkedIn 429 analysis and backoff follow-up

- Relay PR #4 was squash-merged to relay main as 359df41c22f1dd5d696fedbd926d813692c28728. The VM's existing five-minute timer triggered relay workflow run 42445116273 at 04:01:49 UTC; it completed successfully and published 323 jobs at 04:03:47.799190 UTC. A read-only public-feed check confirmed all 323 items contain relay_first_observed_at and relay_last_observed_at; first <= last. No manual workflow dispatch or schedule change occurred.
- Production read-only config: LinkedIn and Naukri enabled; Instahyre and Greenhouse disabled; LinkedIn poll target 180 seconds. Shared dev: LinkedIn disabled, Naukri enabled.
- Production last-24h logs: 298 LinkedIn scan summaries, 643 scan-level request attempts, 24 scan-level failed requests (3.73% of that denominator), plus 3 JD-enrichment 429s; total 27 HTTP 429 events. All 27 had no Retry-After; 18 reached the previous 1,800-second cooldown cap; maximum observed streak 18. Scan summary denominator excludes successful detail-enrichment requests, so do not infer one global HTTP 429 percentage.
- Production SQLite has not yet been migrated to request-level metrics; its source_runs table still has only source/finished_at/jobs_seen/new_jobs. The new request telemetry in V2 is not yet deployed. Do not represent production dashboard metrics as measured.
- A separate code-only branch fix/linkedin-429-longer-backoff-20261108 changes fallback cooldown escalation from 5/10/20/30 minutes (30-minute cap) to 5/10/20/40/80/160 minutes then 4-hour cap, with streak reset only after 24 hours without another 429. Larger Retry-After is still honored. Request spacing, schedule, target count, detail concurrency, source enablement and credentials are unchanged.
- Focused backoff tests: 5 passed. Full V2 suite: 209 passed locally in 76.9s; compilation and diff check passed. GitHub CI still required. No production or shared-dev deployment was performed.
- Detailed evidence, exact counters and caveats: docs/LINKEDIN_429_DIAGNOSTIC_2026-11-08.md.
- Remaining caveat: the LinkedIn cooldown streak remains in-memory and resets after container restart. A persistent breaker state can be considered separately after the backoff PR is validated.
## 2026-11-08 — LinkedIn cooldown persistence follow-up

- Longer conservative backoff is merged in V2 as PR #48 (`5b4b2fa`): 4-hour maximum fallback, 24-hour reset window, honor larger Retry-After.
- Persistence follow-up branch `fix/linkedin-cooldown-persistence-20261108` writes `rate_limit_detected_at` to additive source_runs and restores active cooldown + recent streak at startup. Focused 9 tests passed; full V2 suite 215 passed locally; CI pending.
- Production deployment caveat: legacy live DB has no structured HTTP status history. New column migration cannot reconstruct the 27 historical log-only 429 events, so first rollout starts without old streak; future 429 rows will survive restarts.
## 2026-11-08 — LinkedIn 429 cooldown policy and persistence merged

- PR #48 was merged into `v2-live-radar` as `5b4b2fa`; GitHub CI `42445585602` passed **209 tests** plus Python/dashboard syntax. Policy: 5-minute base; exponential fallback 5/10/20/40/80/160 minutes then 4-hour cap; retain streak until 24h with no 429; honor any larger Retry-After. Request cadence/spacing/targets/workers/source enablement unchanged.
- PR #49 was merged into `v2-live-radar` as `596bbbe`; GitHub CI `42446515750` passed **215 tests** plus Python/dashboard syntax. Additive nullable `source_runs.rate_limit_detected_at` stores actual LinkedIn 429 detection time. Startup restores the prior 24h streak and remaining cooldown from persisted LinkedIn 429 rows, using `finished_at` for legacy rows with no detection timestamp. Naukri/other source 429 rows do not influence LinkedIn.
- Important rollout limitation: production's current old SQLite `source_runs` table has no structured HTTP status history. The existing 27 429s were visible only in container logs and cannot be backfilled by this migration. On first deployment of the new schema, persisted breaker history starts empty; subsequent 429s will survive restarts.
- No runtime deployment/restart occurred. Production port 8000 and shared dev 8001 remain on their previous images/configs. No LinkedIn calls were made during the implementation. The V2 code branch is updated only.
- Redundant parser branch `fix/linkedin-experience-parser` was inspected; current V2 already includes `extract_linkedin_labeled_experience` plus its two regression tests, and the full 215-test CI covers them. Remove the stale branch, not the code.
- PR/branch audit: `docs/PR_BRANCH_AUDIT_2026-11-08.md`. Cooldown evidence: `docs/LINKEDIN_429_DIAGNOSTIC_2026-11-08.md`. Persistent design/migration: `docs/LINKEDIN_COOLDOWN_PERSISTENCE_2026-11-08.md`.
- Next task: investigate PR #46 preference-save error and surface useful server validation feedback. Keep PR #46 draft until preference persistence and per-user Telegram E2E are proven.

## 2026-11-08 — PR #46 local V2 integration candidate

- Integration candidate `integration/pr46-v2-rebase-20261108` is pushed to origin at `676dfaf`, merging PR #46 work with Lever baseline and QA fixes. It is a standalone branch, not a PR or deployment; running services 8002/8004 remain unchanged.
- Shared conflict in `v2/radar.py` was resolved by combining both implementations: preserve monotonic `last_seen_at`, safe source-posted timestamp handling and description-change-only global reevaluation; retain experience provenance/confidence ranking, min/max persistence and per-user evaluation refresh for only touched/new jobs.
- `dashboard/app.js` and `dashboard/index.html` auto-merged. Six conflict files were originally detected; the docs conflicts are being resolved by keeping the newer V2 handover/roadmap/audit and appending current PR #46/browser QA status. Feature-only docs and tests (OAuth, resume parser, Telegram, local browser QA) remain included from PR #46.
- Important next integration: ensure `user_notification_ledger` enqueue/delivery excludes global `notification_ledger.baseline_suppressed=1` opportunities before Lever or other first-snapshot ATS inventory is enabled for member Telegram. The user notification path must not bypass the initial-inventory baseline.
- This local candidate must pass the full V2 suite and user-preferences/OAuth/resume/Telegram focused suites. Keep PR #46 remote draft unchanged until owner desktop Browser report is returned and this candidate has full green CI.
- No push/deploy/runtime changes.

## 2026-11-08 — Lever source integration readiness

- Lever is the next source after Naukri relay / LinkedIn cooldown work. Official API reviewed: public v0 list GET with site slug and skip/limit pagination, global/EU hosts, published postings only, no API key; public fields include id/text/categories/descriptions/hostedUrl/workplaceType/salary. Timestamp semantics not guaranteed; keep posted_at unknown.
- Adapter code and config v12 are on `feat/lever-source-adapter-20261108`; default-off, explicit empty board allowlist, 1800s interval, max 5×100 pages per board/run, request/page/board metrics, partial-failure retention, duplicate IDs, safe hosted URL validation and no apply POST.
- 12 focused tests, 227 full V2 tests pass locally. GitHub CI not yet confirmed. No live board probe/enablement/deployment. See `docs/LEVER_SOURCE_ADAPTER.md`.

## GitHub CI result — 2026-11-08

- Draft PR #50: https://github.com/AvinashBhalla/job-beeper/pull/50
- GitHub V2 CI run #42452809803 passed on commit `c8967ac140647409e735b7ea5be18ea7c92f133d`: Python compilation, dashboard JavaScript syntax, focused router/extractor tests (32 passed), full V2 suite (227 passed in 27.508 seconds).
- PR #50 remains draft and mergeable. No Lever board has been configured or polled; Lever remains off in both config presets.


## Next ATS candidate research — Recruitee vs SmartRecruiters — 2026-11-08

- SmartRecruiters official docs describe a public company postings endpoint `GET /v1/companies/{companyIdentifier}/postings` with `destination=PUBLIC`, `limit` (max 100) and `offset`; its authentication guide lists the public Posting API among no-auth APIs. The separate `/feed/publications` endpoint requires `X-SmartToken`; do not confuse the two contracts. See https://developers.smartrecruiters.com/reference/v1listpostings and https://developers.smartrecruiters.com/docs/authentication.
- Recruitee's public company feed has two XML URLs per subdomain: formatted `/api/feeds/offers.xml` and raw `/api/offers.xml`. The raw feed contains currently published offers only, disappears when offers are unpublished, and updates immediately. Documented fields include stable reference, title/company, full description, multiple locations, remote/hybrid/on-site flags, hosted/apply URLs, `posted` (feed-added timestamp) and `updated` (last update). See https://support.recruitee.com/en/articles/8213076-faq-api and https://docs.recruitee.com/docs/feed.
- Recruitee's new Careers Site JSON API `/api/offers` will require `X-Careers-Sites-Token` starting 2027-02-10; official docs say XML feed and jobs widget are not covered by that token requirement. Prefer the raw XML feed if/when implementing. See https://docs.recruitee.com/reference/authentication-1.
- Critical parser rule: the XML feed may contain a `<credentials>` subtree with third-party job-board secrets. Parse only an allowlist of job fields; never persist/log raw XML or the credentials subtree. Use strict fixed Recruitee host construction from a validated subdomain, bounded response size, one GET/site, no retries, and keep default-off.
- Recommendation: Recruitee is the next adapter to evaluate after Lever; its feed has stronger location/timestamp signals and remains separate from the upcoming Careers API token cutover. SmartRecruiters is also viable but company-scoped; public endpoints are distinct from its authenticated `feed/publications` API. No Recruitee or SmartRecruiters live request/adapter was implemented in this research step.

## 2026-11-08 — Lever URL and pagination hardening

- Added strict Lever posting ID validation (alphanumeric, underscore and hyphen; max 200 chars) before deriving canonical hosted URLs.
- Hosted URL acceptance now checks HTTPS, exact allowed Lever host and port, configured site path, no userinfo/query/fragment and no dot/backslash traversal segments. Untrusted or malformed URLs fall back to the canonical URL built from the configured site and validated posting ID.
- Added fixture test proving maximum pagination is exactly five full pages / 500 unique postings and never requests a sixth page. Added unsafe-ID skip and hosted path-traversal fallback tests.
- Focused Lever suite: 15 tests passed. Full V2 suite: 230 passed in 80.326 seconds. Python compilation and git diff --check passed locally.
- GitHub CI run 42452809803 passed on the initial implementation (227 tests); a fresh CI run is required after this hardening commit.
- Lever remains disabled with an empty allowlist in both config presets. No live board probe, source request, matching, notification or deployment.
## Read-only Drivetrain board canary — 2026-11-08

- Public Lever board slug: `drivetrain` (discovered from its public careers page; no credentials required). Public page search showed India/remote engineering and automation roles.
- A bounded, unauthenticated GET was sent twice to `https://api.lever.co/v0/postings/drivetrain?mode=json&limit=100&skip=0`, two seconds apart. Both requests returned HTTP 200.
- Both snapshots contained 35 postings and 35 unique IDs. 35/35 IDs overlapped between the two snapshots; union size was 35 and churn was zero over this two-second interval.
- Both snapshots contained 22 records with India location metadata. A deliberately broad title-keyword filter found 9 India-based technical postings (software/backend/frontend/engineer/developer/QA/SDET/automation). This is a smoke-test estimate, not the JobBeeper matcher result.
- Sample relevant roles included Backend Engineer, Frontend Engineer, SDET/QA Manager, SDE Automation & Quality, SRE and Software Engineer (Data Engineering). The official board page also exposes roles that may not match our target experience/role filters.
- The two-second interval only verifies response schema and short-term ID consistency; it is not a long-term ID-stability, publication-freshness or source-yield SLA.
- This was a read-only direct public API probe outside JobBeeper. It did not add a board to either config, enable Lever, run the collector, write to SQLite, evaluate matches or trigger notifications.
- Suggested canary site for future explicit opt-in: `drivetrain`. Keep the runtime source disabled until the first-snapshot notification baseline gate below is implemented and reviewed.
## First-snapshot notification baseline gate — required before enabling Lever

Lever's documented public list API does not guarantee a reliable source publication timestamp. Its first full import could contain many old-but-still-open postings, each with `discovered_at=now`; the current freshness logic can consequently regard them as new and queue eligible alerts. Do not activate the source or notifications until an initial-inventory baseline is handled explicitly.

Required behavior for any timestamp-unknown full-snapshot ATS source:
- The first successful complete snapshot must ingest and evaluate listings but mark those existing canonical opportunities as baseline inventory, not newly discovered alerts.
- The baseline marker must be durable across restarts and later scheduled refreshes, and must not falsify `discovered_at`, `source_posted_at` or `posted_precision`.
- Subsequent genuinely new source IDs on later successful snapshots must remain eligible for the normal matching/notification path.
- A partial or failed first scan must not mark an incomplete inventory as a complete baseline. The source must retry its baseline establishment after a successful complete run.
- The baseline logic must be source-scoped and must not suppress notifications for LinkedIn, Naukri or other already-operational sources.
- Regression tests must cover first complete baseline, repeated unchanged snapshot, partial first run, restart durability, and a new posting after baseline.

Until that gate exists, Lever remains default-off with an empty configured allowlist; the Drivetrain probe above is not an activation.

## 2026-11-08 — Initial-inventory notification guard implemented

- Lever has no reliable publication timestamp in its documented public postings contract. The first full board snapshot must not be treated as newly published jobs.
- Added additive notification_ledger.baseline_suppressed INTEGER NOT NULL DEFAULT 0. During each Lever source run, after job upsert and before evaluation/notification dispatch, suppress_initial_source_snapshot_alerts() marks newly created canonical opportunities as suppressed while no prior successful Lever source run exists. The marker is durable and excluded from future global notification-decision refreshes.
- Partial first runs do not establish completion. A later partial run continues baselining newly seen records. Only a successful source run completes the baseline; subsequent genuinely new Lever IDs then use normal matching and notification rules. The code does not falsify or overwrite discovered_at or source_posted_at.
- Existing canonical opportunities with an older observation from another source are not baseline-suppressed. Only Lever is in INITIAL_SNAPSHOT_BASELINE_SOURCES; Naukri, LinkedIn and Greenhouse behavior is unchanged.
- Focused tests: 4 passed. Full V2 suite after this addition: 234 passed in 81.248 seconds. Tests cover partial-run baselining, success transition/new-job alerting, existing cross-source canonical preservation, source isolation and legacy SQLite migration.
- Important integration gate: PR #46 uses a separate user_notification_ledger. That branch's member enqueue query currently does not consult the global notification_ledger.baseline_suppressed flag. Before enabling Lever for member notifications or merging the multi-user notification integration, rebase PR #46 and add the equivalent baseline filter/test to its per-user enqueue/delivery paths. The present guard protects the V2 global/admin notification ledger only.
- Lever remains disabled with empty lever_boards in both config presets; no Lever source request, notification, DB canary, app deployment or service restart was performed by this code change.

## 2026-11-08 — Recruitee live feed canary and next adapter

- A bounded direct read-only canary of `https://tether.recruitee.com/api/offers.xml` returned HTTP 200 twice; each XML response was 8,785,676 bytes with 228 offers and 228 unique IDs. All offers had `published-at` and `updated-at`; 20 offers listed India locations and a broad title filter found 18 technical candidates; 226 remote / 2 hybrid. The two snapshots 2s apart had identical ID sets and metadata fingerprints. This is only short-interval consistency, not a source SLA.
- The live Tether raw XML shape differs from the older official example. Observed shape `<hash><offers><offer>` uses `id`, `guid`, `slug`, `published-at`, `updated-at`, `description`, `requirements`, `locations`, `remote`, `hybrid`, `on-site`, `careers-url`, `careers-apply-url`; the older docs sample uses `<jobs><job>` with `reference`, `posted`, `updated`, `description_requirements`. A future adapter must support both.
- The canary currently had no `<credentials>` node, but official Recruitee docs explicitly state credentials for partner job boards may appear in XML. Any parser must explicitly skip `<credentials>`, reject DTD/entities, cap response size, only parse allowlisted fields, and never log/persist raw XML.
- Official feed URLs: raw `/api/offers.xml`, formatted `/api/feeds/offers.xml`, JSON `/api/offers`. Careers Site JSON API token is required from 2027-02-10; official docs exclude XML feed and widget from that token change. Use official docs in `docs/RECRUITEE_SOURCE_RESEARCH_2026-11-08.md`.
- No Recruitee adapter or app source request was made. Recommendation: Recruitee is next candidate after Lever review; use Tether as test fixture with both schemas and credentials-skip coverage. Keep source off until code review and a no-notification first-snapshot policy is validated.

## 2026-11-08 — Desktop QA findings, local fixes and remaining verification

- User supplied a complete Desktop browser report: overall **Failed**, with QA-001 medium authorization exposure (member opens Source Health and sees source names/status/counts/last-success/diagnostics) and QA-002 low mobile header clipping at 390×844. All other tested scenarios are recorded in `docs/QA/desktop-browser-findings-2026-11-08.md`.
- Desktop could not save its report because its workspace lacked `.git`; a canonical copy and next prompts are now in this repository. The Desktop connection interruption occurred while its answer was being generated; local Git worktrees and QA server remained intact.
- Local integration candidate `/tmp/job-radar-pr46-integration`, branch `integration/pr46-v2-rebase-20261108`, already contained UI-only source-health hiding/route guard and mobile responsive CSS changes. We tightened the server boundary: `/api/source-status/summary` now uses `require_admin`, matching `/api/source-status` and `/api/latency-summary`.
- Candidate UI changes: admin-only desktop/mobile navigation and section; direct member `#sources` routes redirect to Jobs; `loadSourceStatusTelemetry()` returns immediately for members and never calls source-status APIs; mobile telemetry row wraps into 3 columns under 560px with `minmax(0,1fr)` and `overflow-wrap:anywhere`.
- Per-user first-inventory safety was checked during the merge: `user_notifications` excludes `jobs.source_initial_baseline` in enqueue and final send validation. We additionally exclude it from claim selection and explicitly cancel stale queued/failed member notification rows after a job becomes initial baseline.
- Regression tests updated: member `/api/source-status/summary`, `/api/source-status`, `/api/latency-summary` return 403; admin source summary and full status return 200; route dependency contract now classifies source summary as admin-only; dashboard markup/route/telemetry guards and mobile grid have contract tests.
- Focused auth/API/dashboard tests: **13 passed**. User notification tests: **14 passed**. Full V2 unittest discovery: **333 passed** in **174.474 seconds**. Python py_compile/compileall and `git diff --check` passed.
- Local VM Node is v12.22.9 and cannot parse the dashboard's optional-chaining/nullish syntax. The local `node --check` attempt is not a project failure; use GitHub CI's modern Node runtime for the JS syntax check.
- IMPORTANT: integration branch `integration/pr46-v2-rebase-20261108` at `676dfaf` is pushed but NOT deployed. A synthetic-only candidate server runs on loopback 8005; tunnel 18005. Port 8004 remains the old pre-fix PR #46 build. Use docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md Prompt 1 on 18005.
- Public reference research is summarized in `docs/PRODUCT_REVERSE_ENGINEERING_2026-11-08.md`; detailed Desktop tasks are in `docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md`. The public JobBeeper site mentions role/location/experience/company preferences, remote jobs, blocked companies, pause alerts, free browsing/application tracking, paid Telegram/browser/app alerts, and subscriber-first/public sharing. These are research leads, not verified account features; Prompt 2 should verify them without signing up or paying.
- Remaining gates: browser-verify QA-001/QA-002 on the candidate; run security/tenant-isolation Prompt 3 (CSRF, IDOR, expiry, exact preference payload, keyboard/pagination/filter matrix); update docs with each Desktop artifact; then run candidate GitHub CI. Keep PR #46 and #50 open/draft until integration/review decisions are made. No merge, port 8004 restart, shared-dev or production deploy is authorized.


## Candidate QA preview — 2026-11-08

- An isolated candidate server is running at remote loopback 127.0.0.1:8005 (Termalin job 3o9e1mx8d2). Browser tunnel: ssh -N -L 18005:127.0.0.1:8005 ubuntu@130.210.27.197; URL: http://localhost:18005/dashboard/.
- This preview uses a fresh synthetic database /tmp/job-radar-pr46-fixed-qa/jobs.db, not a copy of production, shared dev or the old port-8004 database. It has one admin, one member, two synthetic jobs and one clearly synthetic Naukri source-run row.
- All six collector flags (LinkedIn, Naukri, Instahyre, Greenhouse, Ashby, Lever) are false; notifications are false; Telegram, Google OAuth, Gemini and other LLM credentials are blank. The environment binds only to remote loopback.
- Temporary test accounts shared in chat: qa-member@local.test and qa-admin@local.test. Passwords are not written in repository files.
- HTTP smoke verification: /health, /dashboard/, dashboard JS and CSS returned 200. Member login/feed/daily-summary returned 200; member /api/source-status/summary, /api/source-status and /api/latency-summary returned 403. Admin login and all three source-health GETs returned 200. No outbound source requests or Telegram sends were made.
- The original port-8004 feature process still uses /tmp/job-radar-user-preferences and remains unchanged. Do not use it for post-fix verification. Ports 8000/8001 remain untouched.
- Next: run Prompt 1 in docs/QA/NEXT_DESKTOP_TEST_PROMPTS_2026-11-08.md against port 18005. It must verify real 390×844/375×812/320×740 rendering and direct #sources member navigation, then admin access.

## 2026-11-08 — Final integration review: canonical Lever baseline guard on member notifications

- A second code review found the member queue still lacked a canonical-opportunity baseline filter despite an earlier handover statement claiming complete protection. `user_notifications._queue_new_matches` checked `jobs.source_initial_baseline` only. This could miss a Lever baseline opportunity whose canonical ID originated from an older job in another source.
- Fixed member queue creation, claim selection and pre-send revalidation to exclude `notification_ledger.baseline_suppressed=1`; stale queued/failed/sending member rows are cancelled with `initial_source_baseline`. This remains source-agnostic and safe for all members.
- Added three new canonical-level regressions: suppress at enqueue for a cross-source canonical; cancel an already queued item before claim; prevent final send if canonical suppression appears after claim. Existing per-job baseline test remains.
- Member notification suite: **17 passed**. Full integration suite: **336 passed** in 194.322 seconds. Python compilation and `git diff --check` passed.
- No Telegram HTTP calls or messages occurred. Lever remains disabled and the candidate preview collector flags remain off. No shared-dev or production deployment.
- Updated QA prompt with this additional safety invariant. Current candidate still awaits browser Prompt 1 and security Prompt 3.

- Correction to earlier baseline-gate note: the member notification path did not previously consult the global canonical suppression marker. It now does so at enqueue, claim/cancel and final send revalidation (commit `08c256f`, integration candidate head `9ac6fab`). 17 notification tests and full 336-test suite pass.

## Latest verified state — 2026-11-08 (real-data core pipeline dry run; no deployment)

- Owner priority: defer UI fixes. Focus the current phase on core real-data ingestion/matching. The 320px mobile hit-test overlap is confirmed and documented, but intentionally deferred; no CSS changes were made.
- Candidate code SHA: `cf778c1f1da33c773f820cafea991fb084c58da8`; current PR #51 head is a later documentation-only revision. Previous V2 CI run `42470425337` passed on `a5b1e88`; check CI against the latest docs head before push.
- Real-data source snapshot copied from shared dev (44 MB, around 2026-11-08 09:44 UTC) to disposable `/tmp/job-radar-real-data-validation/jobs.db`. Snapshot: 8,368 jobs, 7,547 Naukri, 821 Ashby, 8,368 canonical opportunities, 8,368 global evaluations, 8,368 per-user evaluations, 8,368 notification ledger rows, 7,829 source runs; SQLite integrity `ok`.
- Candidate DB init preserved existing row counts. Candidate matching recomputed all 8,368 per-user and global evaluations; 130 matched. Feed code path: 40 matched in the last seven days for the stored profile under user-role semantics; admin all-jobs query returned 2,193. The DB had only one admin identity, so this was not a new-member authentication test.
- Candidate Naukri collector fetched one actual public relay snapshot: HTTP 200, 318 jobs, 351.46s old (15-minute guard), one request, one page success, 7 new jobs. Disposable DB ended with 8,375 jobs and canonical opportunities, 8,375 per-user/global evaluation rows, 130 matches, SQLite integrity `ok`. Global notification ledger: 24 pending (reason says Telegram disabled) and 8,351 suppressed. Zero per-user notification settings/chats/ledger rows; no Telegram or Gemini credentials; no sends.
- This proves Naukri ingestion -> normalisation/upsert -> canonical links -> matching/persisted evaluations -> API feed/notification decisions on real data in a disposable DB copy. It does not prove live shared-dev scheduler behavior or the other five V2 source adapters. Naukri is the active dev source; Ashby is 821 historical records with last seen 2026-11-05 and is disabled.
- The detailed evidence is `docs/QA/real-data-pipeline-dry-run-2026-11-08.md`.
- Current live shared-dev `/health` returned HTTP 200 and protected unauthenticated APIs returned 401. Termalin Docker access fails with permission denied; no live DB/config/volume/container was changed, no `sudo`/permission workaround used, and production remains untouched.
- Next action is a controlled shared-dev-only candidate push on port 8001, after explicit owner approval and a fresh SQLite online backup, preserving volume/rollback/config and keeping Naukri-only, notifications/Telegram off, LinkedIn and other new sources off, Gemini off. Verify at least two actual Naukri polling cycles plus job/canonical/evaluation/feed/ledger deltas; keep production port 8000 unchanged. A Docker-authorized operator/session is needed to execute the image build and container recreation.
- PR #51 remains open/draft. The candidate is **not yet pushed to shared dev**. Do not call this a production release.


## Latest state — 2026-11-08 (shared-dev promotion approved; awaiting Docker-authorized operator)

- Owner approved shared-dev promotion. Approval scope is port 8001 only, not production port 8000.
- Candidate PR #51 head before latest deployment note: `e299efdb228b4a05fdc106a0e5e70b9344adf607`; V2 CI run `42471400933` passed on that exact head. Candidate application code SHA `cf778c1f1da33c773f820cafea991fb084c58da8` passed the disposable real-data dry run.
- Core Naukri pipeline was demonstrated with a real shared-dev snapshot and fresh public relay, but no candidate container has been promoted to the live shared-dev database/scheduler.
- Termalin's only connected shell runs as `ubuntu`, not in the `docker` group; Docker socket is root:docker 0660 and Docker CLI returns permission denied. No sudo, group change or socket chmod workaround was attempted. No self-hosted deployment workflow/runner exists in repo.
- Fresh pre-promotion backup not available. Existing 09:44 UTC snapshot is older than the immediate deployment window; configured Termalin full-server backup is an unconfirmed DRAFT with no archives.
- Live `/health`: shared dev 8001 HTTP 200; production 8000 HTTP 200. Neither was changed. No fresh backup, image build/recreate, DB/config/volume mutation, source flag change, PR merge or production deployment occurred.
- Detailed execution report: `docs/QA/shared-dev-promotion-execution-2026-11-08.md`. Next step: provide an already Docker-authorized operator session, take a fresh SQLite online backup, deploy only shared dev with Naukri enabled and all other sources/notifications/Gemini disabled, verify health, then observe at least two Naukri scheduler cycles. Do not post credentials in chat.
- Promotion is approved but **not yet pushed**.

## 2026-11-08 — Final shared-dev access check

- Owner approval received; candidate is ready in GitHub, but Termalin's connected `ubuntu` account cannot access the `root:docker` mode-0660 socket and cannot trigger the root-owned SQLite snapshot service. The snapshot service last ran at 02:45:43 UTC and is not fresh enough for deployment; a start request returned `Interactive authentication required`.
- No fresh backup or image/container action occurred. Port 8001 and port 8000 health reads both returned HTTP 200. No state changed.
- An already authorized Docker/snapshot operator session is the single remaining infrastructure prerequisite. Don't use this session to alter sudoers, Docker groups or socket mode.

# 2026-11-08 CONTINUATION — expanded product scope and exact next steps

This is an appended checkpoint; preserve the complete existing knowledge transfer above.

## Current deployment facts
Shared dev is running candidate image job-radar-dev-multitenant:b16fb83 (sha256:75f8855338f150a79794d388c32733305e548165f71dd417cfa04e6443c8c917) on 127.0.0.1:8001. Its health and dashboard were HTTP 200 at 2026-11-08 11:39:59 UTC. Production on port 8000 remained healthy on the old image/container and was not modified.

V2 app/test source head used for that image: 754809fe406e8c5cb09f8e36140ac5cf3e4f7238. PR #51 remains open/draft on integration/pr46-v2-rebase-20261108; later changes on the PR were documentation-only. Recheck its actual head and CI before any new build.

The VM account ubuntu has passwordless full sudo (sudo -n -l => (ALL : ALL) ALL and (ALL) NOPASSWD: ALL). Use sudo docker/systemctl. No password needed.

## Real source integration results
V2 COLLECTORS currently includes only LinkedIn, Naukri, Instahyre, Greenhouse, Ashby and Lever. Real shared-dev live tests passed:
- Naukri: repeated scheduled cycles; latest observed around 306 jobs, successful; earlier 307/3 new and 308/2 new.
- Instahyre: patched parser now reads current objects payload and location aliases; 140 new jobs, four HTTP 200 pages.
- Greenhouse: three boards succeeded, 369 new jobs.
- Ashby: two boards succeeded, 828 observed, 34 new, all timestamped.
- Lever: one-off paytmpayments public board, 500 new across five 200 pages, capped at five pages. Not persisted/enabled.
- LinkedIn: after cooldown, one controlled HTTP 200 request gave 10 jobs; same results ingested through run_source, 10 new. Not persisted/enabled.
The first real Instahyre test revealed and the candidate fixed a real parser/location mismatch. Three regression tests were added; full CI run 42474145630 passed.

Latest dev DB: integrity ok, 9,444 jobs / canonical opportunities / global evaluations / per-user evaluations / notification ledger rows; 7,858 source runs; one admin account, one preferences row, no per-user notification ledger rows. Scheduler saved config is Naukri only. Telegram credentials blank, notifications disabled, Gemini and LLM router false, zero sent_at rows.
An intermittent sqlite3 OperationalError database is locked was seen in the notification worker's recover_stale_claims during ingestion. It recurred once following LinkedIn ingestion. Fix and regression/load test this before production.

## Expanded product requirement — all 36 platforms
The owner now requires all of these as first-class sources, with low-latency new-job capture and per-user Telegram alerts:
Ashby; Avature; BambooHR; Breezy HR; Cutshort; Darwinbox; Eightfold AI; Freshteam; Greenhouse; Hireology; Hirist; HRsmart; iCIMS; Instahyre; Jibe (iCIMS); Jobvite; Keka; Lever; LinkedIn; Naukri; Oracle Cloud Recruiting; Paycom; PeopleStrong; Phenom People; Recruitee; Rippling ATS; SmartRecruiters; SAP SuccessFactors; Oracle Taleo; Teamtailor; UKG Pro / UltiPro; Wellfound; Workable; Workday; Y Combinator; Zoho Recruit.

See docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md for a complete ordered matrix and research links. Workday and Darwinbox are the owner's first missing connectors to build.

The set mixes ATS vendors and job marketplaces. Employer ATS feeds are usually scoped to one company/tenant/career-board, so an employer registry and ATS/career-site discovery subsystem is required. Do not tell the owner that adding 36 collector functions magically yields all jobs: first discover and verify each employer's tenant/board ID.

Latency target: webhooks when the employer authorizes them; otherwise 2-minute polling for high-priority boards where allowed, with jitter, per-host budgets, backoff and cooldown. Promise only near-real-time after public availability, never literal instant at the employer's internal publish click.

## Per-user Telegram expectations
Every account has its own profile/preferences and Telegram destination. Each ingested job must be evaluated separately for each active user. Only new matches create idempotent per-user outbox entries; do not replay board baseline/history. Track per-user sent status and Telegram message ID. Test with two different users and safe fake/test transport; no cross-user leakage. Do not send all member alerts to the global admin chat. Do not ask user to paste Telegram secrets into chat.

## Production caution
Production currently has global Telegram credentials and notifications enabled; candidate preflight on a disposable 20,971-job copy preserved all existing job/canonical/evaluation/notification counts, 1,482 sent entries and 10 failed entries (19,168 suppressed), SQLite integrity ok. Matching refresh took ~73 seconds. Production tables for users/per-user preferences were empty/absent on that old schema snapshot. Do not simply replace the container and hope member delivery works. Preserve global Telegram behaviour and audit queue before any prod deployment.

Separate production approval is mandatory: prior explicit approval covered shared dev only. Do not merge/deploy production until SQLite contention fixed, user-specific Telegram verified, Workday/Darwinbox built/tested, board discovery working, fresh formal production backup recorded and owner approves.

## Handover priorities
P0: fix database-lock contention in legacy notification worker; prove auth/preferences/CSRF and per-user Telegram dispatch.
P1: Workday then Darwinbox, then BambooHR, SmartRecruiters, Workable, Recruitee, Teamtailor, Rippling, Eightfold, Phenom, Oracle Recruiting, Avature, iCIMS/Jibe, SAP.
P2: remaining ATS/career-site families.
P3: marketplaces (Cutshort, Hirist, Wellfound, YC, LinkedIn/Naukri/Instahyre) with legal/terms and API/access review.
P4: company-board discovery, registry, scheduled recrawls, operator review queue.
Every source completion means a real public board test over two polls or a real webhook event, stable IDs, correct ingestion and dedup, matching/evaluations, user-specific decisioning and successful notification test. Mocked test or HTTP 200 alone is not enough.


## 2026-11-08 — SQLite notification contention fix implemented and fully tested (not deployed)

**Branch:** `fix/sqlite-notification-contention-20261108` (based on integration head `ce502e1f8be51d5f2123c3bc0a1cb916245ec260`).

### Root cause found

- Shared dev logs showed `sqlite3.OperationalError: database is locked` in `notification_worker -> recover_stale_claims()` while collectors were ingesting. The DB uses a local Docker volume and was in SQLite `DELETE` journal mode.
- The legacy collector/notification paths used `radar.db_lock`; the independent multi-user notification service opened its own connections and used `BEGIN IMMEDIATE` without that lock for claim/queue/status writes. Both worker families could therefore compete for the same SQLite writer lock.
- `user_notifications.dispatch()` also repeated the full active-user queue scan once per attempted message. With no opted-in users it could still open claim/write transactions.
- A global Telegram credential by itself was not a sufficient send gate; the legacy send path did not consistently enforce `notifications_enabled`. The active shared-dev runtime was confirmed safe (credentials absent, feature disabled), but the code now enforces that state.

### Fix on the isolated branch

- Added `v2/sqlite_store.py` as the shared SQLite policy: process-wide re-entrant `DB_LOCK`, a 15,000 ms busy timeout on app-managed connections, and a checked WAL enable helper. WAL is enabled during `radar.init_db()`.
- Unified the radar and legacy Telegram connection helpers on that timeout and the same process-wide lock. Member notification schema/settings/queue/claim/final-state writes now use that same lock; no lock is held while making the outbound Telegram HTTP request.
- Changed the member dispatcher to queue new eligible jobs once per dispatch cycle using a single `INSERT ... SELECT`, return immediately when the bot token is missing or there are no opted-in users, and preserve `limit=0` as a true no-op.
- Gated both the legacy immediate-send and background-worker paths on credentials **and** the persisted `notifications_enabled` switch. Per-user notification delivery continues to use each user's own opt-in and private linked chat.
- Extended `.github/workflows/v2-ci.yml` syntax compilation coverage to all new/changed SQLite and notification modules/tests.

### Verification

- Focused final tests: **24 passed** (`test_sqlite_store`, `test_user_notifications`, `LegacyNotificationGateTests`). Includes separate-connection SQLite busy waiting, WAL persistence, concurrent member-claim vs legacy-recovery, no-opt-in/no-op behavior, batching and two-user chat isolation.
- Full final V2 suite on this exact code: **347 tests passed in 188.827 seconds; zero failures** (`python -m unittest discover -s v2 -p 'test_*.py' -v`).
- `py_compile`/`compileall` and `git diff --check` passed. No Telegram HTTP message was sent by these tests (delivery uses mocks).

### Deployment status and exact next steps

- **Not committed or pushed at this checkpoint; not deployed.** The running shared-dev container remains `job-radar-dev-multitenant:b16fb83`, built from app SHA `754809fe406e8c5cb09f8e36140ac5cf3e4f7238`. Its live DB still reports `journal_mode=delete`. Production remains untouched.
- A read-only shared-dev config check confirmed `notifications_enabled=false`, Telegram bot token/chat values absent, and `user_notification_settings` count 0. Existing dev scheduler remains Naukri-only.
- Next: inspect final diff, commit on `fix/sqlite-notification-contention-20261108`, push it, then update the existing open/draft PR #51 integration branch from its current `ce502e1` base (do not merge PR #51 or close PR #46). Wait for GitHub V2 CI on the exact new SHA and inspect its job results.
- The owner previously approved a **shared-dev port 8001** promotion only. After CI passes, use `docs/DEV_DEPLOYMENT_RUNBOOK_2026-11-08.md`: take a fresh SQLite online backup from the live container (integrity, size, SHA-256 recorded), build an immutable image, recreate only `job-radar-dev`, preserve volume/config/env/Telegram blanking and Naukri-only flags, and verify integrity/row counts/WAL/health/zero-send state. Do not touch production ports 8000/8002/8004/8005.
- After shared-dev deployment, observe at least two Naukri scheduler cycles and inspect logs for any further lock errors. WAL and timeout are not a substitute for observing the actual live system. Production still needs a separate explicit approval and a reviewed migration/delivery plan.
- WAL backup caution: while WAL is active, create snapshots with SQLite's online backup API. Do not copy only `jobs.db` from a live WAL database and omit `jobs.db-wal`; do not delete sidecar files manually.

### Workday discovery evidence (research only; adapter not implemented)

- A one-request probe against NVIDIA's public Workday career site succeeded: `POST https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs`, JSON `{"appliedFacets":{},"limit":20,"offset":0,"searchText":""}` returned HTTP 200, JSON keys `facets`, `jobPostings`, `total`, `userAuthenticated`, 20 postings and `total=2000`. Sample public fields included title, `externalPath`, `postedOn`, `locationsText` and a requisition ID in `bulletFields`. This is a real endpoint probe only, not recurring ingestion or a vendor-supported API guarantee.
- A Workday adapter needs an employer registry of real careers URLs and must derive each employer's cluster/host, tenant and career-site name. Never guess tenant/site IDs from the company name. CXS is a public career-site interface and should be treated as undocumented/changeable; distinguish it from authenticated Workday REST APIs.
- Darwinbox official recruitment API research indicates employer-issued API-key authentication. Validate a public candidate careers feed only against an actual employer URL and access terms; do not assume a universal unauthenticated API.
- The 36-platform matrix remains authoritative. Workday then Darwinbox remain the next connector priorities, paired with company-board discovery; no new source was enabled.


## 2026-11-08 — SQLite contention fix + first Workday connector completed (candidate branch; not deployed)

- Current branch: `fix/sqlite-notification-contention-20261108`, based on integration head `ce502e1f8be51d5f2123c3bc0a1cb916245ec260`. Earlier SQLite fix pushed on this branch/integration PR as `c441737ca6c19f17002d9a43923a4a64353f0977`; the Workday adapter/UI/docs changes in the current worktree must be committed and pushed before final CI.
- SQLite notification contention fix: shared `DB_LOCK` for the legacy and per-user queues, 15s busy timeout, WAL on init, queue-once batching, no-opt-in early return and global notifications switch gate. The full suite with Workday now passes **354 tests in 236.278s**; SQLite-only/notification focused suite 24 pass.
- Workday V2 adapter added to `COLLECTORS`; config version 13; `source_enabled.workday=false` by default, `poll_seconds.workday=120`, and `workday_boards` must contain a verified public HTTPS myworkdayjobs URL. Tenant, cluster and site are parsed from the actual board URL. Workday included in initial source baseline because `postedOn` is only a human label and `source_posted_at` remains unknown.
- Workday adapter limits each board to 5 list pages × 20 postings (100 listing records) and 5 detail fetches per cycle; public board URLs and paths are allowlisted, HTML description is stripped, requisition-based stable IDs are used, no arbitrary `externalUrl` is trusted. This is a public CXS candidate-site interface, not the authenticated Workday REST API and not a vendor guarantee.
- Live NVIDIA public board check: 100 unique listing IDs from 5 pages; 5 detail calls under current cap. Two-poll `run_source` application pipeline on a disposable SQLite DB (1 page per poll for controlled smoke): poll 1 inserted 20, 20 canonical opportunities and all 20 initial inventory rows were baseline-suppressed; poll 2 inserted 0; 2 successful source runs; integrity `ok`; no sent Telegram rows. This is one real board, not wide Workday support.
- Dashboard added Ashby/Lever/Workday admin source toggles and a Workday JSON allowlist editor. The admin still needs a manually verified board URL. Automated company/ATS detection and board discovery remain unimplemented.
- Workday adapter is not deployed to shared dev/production; shared dev remains image `b16fb83`, Naukri-only, notifications false, `journal_mode=delete`; production unchanged. Workday must stay disabled until exact-SHA CI and approved shared-dev promotion.
- Existing CI run `42480365749` passed on earlier SQLite-only commit `c441737`; it does not cover the current Workday changes. Push the final Workday commit and verify the next V2 CI run against its exact SHA. The VM system Node is v12 and cannot parse existing `??` syntax; use GitHub CI's modern Node check as the authoritative dashboard syntax verification.
- Darwinbox remains unimplemented; the official Recruitment API is employer-keyed. Next after Workday CI/shared-dev check: employer board registry/discovery, then validate Darwinbox per real employer board. Keep per-user interactive Telegram test and shared-dev SQLite lock-error soak as production gates.


## 2026-11-08 — P0 shared-dev rollout complete; Workday adapter refined and tested (candidate only)

### SQLite/notifications P0 status

- P0 implementation commit `c441737ca6c19f17002d9a43923a4a64353f0977` passed GitHub V2 CI run `42480365749` (all steps success) and the exact-commit V2 suite (347 passed, 188.827s).
- Shared dev is now running `job-radar-dev-multitenant:c441737` on port 8001. It uses the preserved external data volume and config bind. DB checks: WAL, `busy_timeout=15000`, integrity `ok`, current key tables 9,461 rows, source_runs 7,872. Three post-deploy Naukri polls completed successfully; no `database is locked` or traceback was found in logs since rollout. Continue soak and do not call this production-scale proof.
- Delivery safety: `notifications_enabled=false`, Telegram token/chat absent, both sent counts zero, per-user settings/outbox remain empty. Naukri is the only scheduler-enabled source. Gemini and LLM feature flags are explicitly false in effective container env. An initial interpolation issue set them true; this was corrected in the candidate Compose file and the service was recreated. The dev `.env` was not modified.
- Fresh online backup before deployment: `/var/backups/job-radar-daily/development-jobs.sqlite3`, SHA-256 `aa78251196c7c2925cf09e5e6b9cbb7878884681bd9920407e32f4e2ff0b49e0`, 9,459 jobs, integrity `ok`. Production snapshot was also taken for backup checks, but production container `v2-radar-1` and DB were not changed.

### Workday candidate status

- Local branch `fix/sqlite-notification-contention-20261108`, based on the CI/deployed P0 SHA above, now includes `workday_collect`, version-13 config, validated public-board allowlist, source toggle and admin JSON board editor. These Workday files are not yet committed/pushed; the deployed image does not include them.
- Nine focused Workday tests pass, including employer URL parsing, host/path rejection, config opt-in migration, 20-item pagination/detail parsing, detail failure attempt cap, and stop on HTTP 429. A full-suite run on this code exited 0 but its redirected output file was removed; rerun without redirection and retain the test summary before publish.
- Latest live public NVIDIA poll: 1 listing request + 20 detail requests, 20 unique stable requisition IDs, 20 descriptions, 20 locations, employment types included, 24.57 seconds. Human `postedOn` labels are retained but source timestamp precision remains unknown. The source remains a public undocumented CXS candidate-site interface, not an authenticated Workday REST integration or vendor guarantee.
- Current candidate limits: one page of 20 per board per cycle; at most 20 detail attempts; 100ms delay between details; max20 allowlisted boards. Boards run sequentially. At measured 24.57 seconds per board, four boards approach the 120-second poll interval; larger board sets cannot claim two-minute end-to-end capture until bounded concurrency/per-board scheduling exists. First run is baseline-suppressed to avoid historic alerts.
- Workday is disabled in repository defaults and shared-dev config; `workday_boards=[]` in both. Do not enable or deploy before fresh CI and a separately approved real employer-board pilot.

### Immediate next tasks

1. Finish/inspect full V2 suite output on the current Workday code, run modern GitHub CI on exact final SHA, and commit/push the Workday branch + fast-forward integration PR #51 without merging it. PR #51 remains draft/open; PR #46 remains untouched.
2. Continue shared-dev SQLite soak over additional Naukri cycles and watch for lock regressions. No production promotion.
3. Complete real member login + dedicated test-chat Telegram delivery with at least two users; tests cover isolation, but live member flow is not complete.
4. Build an employer/career-site discovery registry before scaling Workday board coverage. Then start Darwinbox; official Recruitment API uses employer-provided auth, so validate each public candidate board independently.
5. Continue the original 36-platform matrix. Do not claim full coverage; only seven sources are presently registered in candidate V2 and only Naukri is enabled on shared dev.


## 2026-11-08 — Current operational state: SQLite P0 deployed; Workday candidate pending CI

- Shared dev was promoted to `job-radar-dev-multitenant:c441737` on port 8001. Exact code SHA `c441737ca6c19f17002d9a43923a4a64353f0977`; GitHub V2 CI run `42480365749` passed. The SQLite contention fix is deployed; production container `v2-radar-1` remains unchanged and healthy.
- Live shared-dev checks: health HTTP 200, SQLite `journal_mode=wal`, `connect_sqlite()` busy timeout 15,000ms, integrity `ok`, 9,462 jobs and 7,874 source runs at 2026-11-08 12:58 UTC. Last eight source runs were successful Naukri cycles. No `database is locked` message was found in the last 90 minutes of dev logs. Keep observing; this is not a production-load proof.
- Shared-dev guardrails: Naukri only enabled; `notifications_enabled=false`; Telegram bot token/chat absent; Gemini and LLM router false; zero delivery activity. Existing external volume and config bind remain attached. Fresh pre-deploy online backup is documented in the deployment runbook. Production was not touched.
- Current local Workday candidate adds the Workday CXS collector, validated board URL allowlist/config version 13, admin checkbox + JSON board editor, source baseline suppression, bounded list/detail requests and persisted `Retry-After` cooldown. Workday is disabled by default and absent from the deployed `c441737` image.
- Current Workday request budget: one page of 20 listings per board per cycle; up to 20 detail calls, 100ms delay, 20-board allowlist cap; default 120-second interval when deliberately enabled. 429 halts the board scan, persists a cooldown, is restored on startup and suppresses scheduler polls until expiry. Workday CXS remains an undocumented public candidate-site interface; this is not authenticated Workday REST and not a universal employer discovery mechanism.
- Real NVIDIA public-board test against the final collector settings via disposable SQLite `run_source`: first poll 20 jobs inserted, all 20 with full descriptions, 20 canonical opportunities, 20 first-inventory baseline suppressions; second poll 0 new; 2 successful source runs; integrity `ok`; sent count zero. A controlled 429 run persisted a 120-second cooldown and `rate_limited` source run. Only one employer has been exercised. No Workday scheduler enablement, shared-dev deploy or recurring soak.
- Workday-focused tests: 12 pass (including list/detail 429 cooldown and startup restoration). Full V2 suite on current cooldown changes: **359 tests passed in 266.690s, zero failures**. Dashboard code uses modern JS syntax already present in project; VM Node v12 cannot parse the repo, so the next GitHub CI Node check is the authoritative JS syntax test.
- Current worktree `/tmp/job-radar-sqlite-contention` branch `fix/sqlite-notification-contention-20261108` has uncommitted Workday changes. Integration branch / PR #51 still points to `c441737`. After full tests pass: inspect diff, commit all intended Workday+docs changes, push feature branch and fast-forward `integration/pr46-v2-rebase-20261108`; confirm CI for exact new SHA. Leave PR #51 draft/open; do not merge or deploy Workday.
- Next after CI: build employer-board discovery/registry; Darwinbox follows Workday, noting its official Recruiting API is customer-keyed. Verify member/admin flows and real two-user dedicated-chat Telegram dispatch before production. Production promotion needs its own fresh formal backup, reviewed migration/delivery plan and separate owner approval.


## 2026-11-08 — final Workday candidate verification (after persisted cooldown hardening)

- Full V2 suite on current working tree: **359 tests passed in 266.690s, zero failures**. Workday-focused `WorkdayCollectorTests`: **12 passed**. `compileall`, JSON validation, and `git diff --check` passed. The separate existing GitHub CI run `42480365749` validates P0 SHA `c441737`; new Workday changes still require their own exact-SHA CI after push.
- NVIDIA current public board validation: 20 listings from one CXS POST + 20 full-detail requests, 20 unique requisition IDs, 20 descriptions, 20 actual detail locations and employment type, 24.57s elapsed. No exact posting timestamp is exposed; retain `postedOn` label and use unknown precision. No Workday recurring board is enabled in dev.
- Workday now also has source-wide 429 handling: respects `Retry-After`, clamps cooldown between 60s and 3600s, defaults to 300s when missing, stops the remaining board requests, persists status/cooldown into `source_runs`, and restores the remaining cooldown on app startup.
- `dashboard/app.js`/`dashboard/index.html` provide Ashby, Lever and Workday source toggles plus an admin-only JSON editor for `workday_boards`; JSON parsing/type errors are surfaced before save. GitHub CI's modern Node check is required; VM Node 12 cannot parse existing modern syntax.
- Current Workday config remains safely off (`source_enabled.workday=false`, `workday_boards=[]`, poll default 120s). Adapter and UI changes are local uncommitted modifications on top of P0 SHA `c441737`; not included in shared-dev image. Four post-deploy Naukri runs succeeded and no lock errors were observed in the shared-dev container logs.
- The full platform goal remains unfinished: only seven adapters are registered. Workday is sequential across boards; at 24.57s per board the two-minute target is not met at large board counts. Employer-board discovery, bounded multi-board scheduling, Darwinbox and remaining connectors are still required.


## 2026-11-08 — Workday candidate committed and pushed; exact-SHA CI running

- The Workday adapter, config version 13, dashboard controls, test coverage, and updated source/deployment handover were committed as `c4f9c66cd05419242a761939f4c1ff883b4266d0` (`feat: add bounded Workday public career-site collector`).
- The commit is pushed to `fix/sqlite-notification-contention-20261108` and fast-forwarded to `integration/pr46-v2-rebase-20261108` (PR #51). Remote refs have both been verified at `c4f9c66`.
- GitHub Actions V2 CI run `42483043107` is running against this exact SHA. Python compilation and the dashboard JavaScript syntax step succeeded; focused router/extractor tests succeeded; the full V2 unittest job was still running at this note. Local V2 full suite on this code passed 359 tests in 266.690s.
- Workday is not deployed or enabled in shared dev. Shared dev remains image c441737 (SQLite P0 only); production remains untouched. PR #51 remains open and draft. Do not merge or deploy Workday until exact-SHA CI passes and a controlled shared-dev board pilot is separately approved.


## 2026-11-08 — Exact Workday commit CI completed

GitHub V2 CI run `42483043107` completed successfully on Workday commit `c4f9c66cd05419242a761939f4c1ff883b4266d0`. All job steps passed, including Python compile, modern Node dashboard syntax, focused router/extractor tests and full V2 unittest suite. PR #51 remains open/draft and unmerged. Workday is committed but not deployed or enabled in shared dev.


## 2026-11-08 — External repo study and Keka/Darwinbox candidate snapshot

- Production: `job-radar-prod-canary:7b1a80d` on port 8000, health HTTP 200. Keka and Darwinbox are **not deployed**. Keep production config, SQLite volume and Telegram settings unchanged.
- Research: `docs/REFERENCE_REPOSITORIES_RESEARCH_2026-11-08.md`, doc-only draft PR #52. Career-Ops is a high-value reference for provider contracts, bounded HTTP, validation, redirect safety and per-source tests. Career-Ops Extension is application form filling/answer learning with a manual submit checkpoint; it is not a source collector.
- Connector candidate: `/tmp/job-radar-next`, branch `feat/darwinbox-keka-20261108`; new code adds Keka/Darwinbox discovery, verification and collectors, config v15 opt-in flags, admin controls, tests. Both flags default false.
- Historical live integration evidence: Keka Bridgestone 109 postings and the then-tested JG Summit Darwinbox `.com` endpoint 18 postings. The JG Summit result was later re-probed and returned 403; it is superseded by the 2026-11-08 Arvind Group `.in` 36-job verification below. The earlier two-poll run is not evidence for Arvind.
- Local V2 suite: 387 tests pass in 215.671s; compileall/config JSON/diff checks pass. Exact-SHA GitHub CI and isolated browser QA are still outstanding. Feature branch is not yet pushed/deployed.
- Next: review diff → push feature branch → exact-SHA CI → isolated admin browser QA → latency telemetry → reviewed promotion/canary. First production admin account also needs a user-supplied admin email; Google OAuth is currently disabled.


## 2026-11-08 — Current CI and connector QA checkpoint

- PR #51 now includes connector commit `07544e835212892a63e3f7e05d0f9ee0b6db3ab0`. Exact-SHA CI run `42505820970` passed (compile, dashboard syntax, focused and full suite); manual duplicate run `42505931091` was queued and must be checked.
- QA app: loopback port 8010, isolated volume `job-radar-connectors-qa_qa-data`, health OK, config v15, all source flags false, notifications false, no bot or model keys, SQLite integrity `ok`; dashboard GET 200 and anonymous admin API 401.
- Keka live probe: Bridgestone tenant 109 jobs.
- Darwinbox correction: JG Summit `.com` endpoint gave 403 and is no longer considered verified. Career-Ops reference pattern is `.darwinbox.in` only. Arvind `.in` returned 36 jobs; Airtel, LeadSquared and Sterling `.in` examples gave 403. Detector/tests now being narrowed to `.in`, with Arvind as verified sample. No production Darwinbox activation until the correction's CI passes.
- Production still runs image `job-radar-prod-canary:7b1a80d` on the existing persistent `v2_radar-data` volume. Runtime config remains v14: LinkedIn/Naukri enabled, Greenhouse/Ashby configured but off, and remaining provider allowlists empty. User wants all feasible connectors enabled; only individually verified sources with board IDs and silent initial-baseline handling may be activated.
- First admin account is not yet provisioned. The user supplied `bawejaavichal01@gmail.com`; the CLI still requires a password at bootstrap. Obtain that password through the intended secure input path before claiming admin UI/per-user Telegram is ready.

### 2026-11-08 — Verification correction and per-board canary results

- The Darwinbox `.in` restriction and Arvind fixture are in the working candidate; prior JG Summit `.com` evidence is superseded (repeat probe was 403). Arvind board probe=36; isolated two-poll `run_source` test: first 36 ingested and baseline-suppressed, second 0 new, sent=0, both success, `PRAGMA integrity_check=ok`.
- Workable probe mismatch fixed: it now uses the exact collector endpoint `https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true`, not the obsolete `www.workable.com/api/accounts` endpoint. Hugging Face current probe=6.
- Latest bounded live board probes in isolated QA: Greenhouse Coinbase=283, Graviton=21, Zocdoc=64; Ashby OpenAI=816, PostHog=10; Workday NVIDIA first page=20; SmartRecruiters Bosch verification page=10; Workable Hugging Face=6; Keka Bridgestone=109; Darwinbox Arvind=36. These are verification response counts, not exact total active board inventory except where the endpoint response contract supports it.
- Corrected local V2 full suite on Darwinbox host restriction passed 387 in 291.998s. After Workable probe change, 10 focused tests (Workable verification + Keka/Darwinbox class) pass; a complete exact-final-SHA CI run must cover all changes.
- QA app is isolated on 127.0.0.1:8010 with volume `job-radar-connectors-qa_qa-data`, config v15, all sources off and notifications off. Health/dashboard 200; anonymous admin endpoint 401; DB integrity ok. No Chromium browser is installed on the VM, so full visual login/discovery UI testing is still pending.
- No production changes. Production v14 source configuration remains unchanged. Do not enable empty/unverified boards; see detailed handover for exact prod config and per-source verification summary.

### Activation dedup guard

Production already contains Greenhouse and Ashby allowlist entries but no ATS board registry rows. The activation flow now links a verified registry row to an existing matching provider entry by its source-specific key and attaches `registry_id`, rather than appending a duplicate. A pre-existing entry linked to a different registry ID is rejected. A regression test covers Greenhouse; this protects per-employer silent-baseline suppression when the preconfigured boards are activated.


## 2026-11-08 — Product strategy and reference adoption

- New source-of-truth product plan: docs/PRODUCT_VISION_AND_DELIVERY_ROADMAP.md. Read this before reprioritizing features. It supersedes earlier conflicting priority orders in older roadmaps without discarding their technical history.
- Career-Ops should inform job legitimacy checks, explainable evidence weighting, factual resume tailoring, application preparation, contact provenance and draft-first human-approved outreach. Its local CLI architecture should not replace JobBeeper hosted shared-ingestion/multi-user architecture.
- Apply Factory contributes a reusable answer-bank concept with learning/correction events and optional browser-assisted form filling. The current reference's Kimi Webbridge/DOM scraping approach is not a stable dependency to copy. Build the first-party companion after answer-bank APIs.
- Current truth: Applied tracker uses browser localStorage and is not cross-device/server-owned. Resume parser is an onboarding-suggestion extractor only; no resume vault/tailored CV generation yet. Referral/contact discovery, follow-up workflow and browser fill are not implemented. Auto-submit is not implemented and must remain off until a distinct permissions/risk gate.
- Reprioritized: P0 release reliable source ingestion + production-safe notifications; P0.5 server-side user-owned application tracking before wider beta; P1 resume vault/factual tailoring + answer bank; P2 contact/referral/follow-up; P3 interview/search coach; P4 carefully gated automation with user confirmation.


## 2026-11-08 — Production release, first-admin instructions and board-manager gap

- Production image `job-radar-prod-canary:93a1372` is deployed on the original external `v2_radar-data` volume. Config v15. Health/dashboard return 200; DB integrity `ok`. PR #51 merged as `0aac3cb`; PR #53 baseline fix merged as `93a1372`. Exact-head CI passed for both. The hotfix full local V2 suite passed 390 tests.
- Active production sources: LinkedIn, Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka, Darwinbox. Instahyre and Lever remain disabled. Ten active board registry rows across seven ATS families are baseline-complete (`baseline_pending=0`).
- The fixed silent baseline replay completed: 1,665 jobs marked as initial inventory; 1,665 related notification ledger rows baseline-suppressed; seven source replay counts: 368/826/20/300/6/109/36. Each replay had 0 new rows. No Telegram historical backfill was sent. Notifications are restored enabled; no new-source queue items were left pending.
- Production has zero user/admin rows. The supplied admin email is `bawejaavichal01@gmail.com`. Provision the first administrator interactively with: `sudo docker exec -it v2-radar-1 python -m v2.auth_admin create-admin --email bawejaavichal01@gmail.com`. It prompts for password twice, stores only an Argon2id hash, and copies the existing `/data/config.json` candidate preferences to that first admin once. Do not put a password in command arguments, `.env`, Git or documentation. This agent's remote account creation attempt was blocked by the execution safety gate; no account/password was created.
- Google OAuth is implemented but disabled because the production `.env` has no client ID, client secret or redirect URI. OAuth creates/links normal `user` accounts, never an admin. Do not treat Google OAuth as the first-admin bootstrap.
- The global Telegram bot token/chat ID exist, but per-user bot linking is not configured: bot username, webhook secret and public origin are absent. Per-user notifications still require those settings plus a private-chat link and opt-in.
- Active board rows in the current dashboard support activation/review but lacked disable action. Branch `feat/admin-board-disable-20261108` adds a per-board deactivate endpoint and UI. It needs exact-SHA CI, full V2 suite, QA review and separate production deployment; current production is not yet running this branch.
- Read the detailed 2026-11-08 block in `docs/JOB_RADAR_HANDOVER.md` before changing production.


## 2026-11-08 — Admin board disable now deployed

- PR #54 merged as `00820f0eef9b6ddcd5e8b289cdb742fe88ca3b92`; exact PR-head GitHub CI passed; local V2 full suite passed 393 tests. Production canary against fresh DB copy passed (health 200, dashboard 200, anonymous admin routes 401, DB integrity `ok`).
- Production image is now `job-radar-prod-canary:00820f0` on the same external `v2_radar-data` volume. Config v15, notifications and current enabled sources preserved. All 10 registry board rows remain active and baseline-complete. No config/board was disabled in deployment.
- Admin Source Health workspace now shows **Disable board** on each active board. It is safe per-board removal from provider allowlist, preserving peer boards; provider turns off only if last board removed. Disabled entry stays verified for reactivation. It refuses while provider polling. Requires admin login and CSRF.
- Pre-deploy DB backup and config checksums documented in `docs/JOB_RADAR_HANDOVER.md` in the latest deployment section.
- Production admin still must be created interactively: `sudo docker exec -it v2-radar-1 python -m v2.auth_admin create-admin --email bawejaavichal01@gmail.com`. No account has been created yet. The first admin inherits the preserved candidate prefs once. Google OAuth requires owner-created client credentials and HTTPS redirect; per-user Telegram requires bot username/webhook secret/HTTPS webhook and private-chat opt-in.
- Use the Termalin internal site open link `https://termal.in/account#open-site=54768be5-95ea-4d86-9360-96d0c38c2843` to open the private dashboard, then log in once the admin has been bootstrapped.


## 2026-11-09 — P0.5 server-side Applications tracker (active implementation branch)

- Feature branch: `feat/server-application-tracker-20261109` from current `v2-live-radar`. This is **not yet merged/deployed**; production stays on image `job-radar-prod-canary:00820f0`.
- Replaces Applied tracking in `localStorage` with user-owned `user_applications`, unique by `(user_id, canonical_opportunity_id)`, with source `job_id`, applied_at, status, notes and timestamps. Separate users can track same job independently. Do not accept user ID from the request; derive owner from auth session.
- API: GET/POST `/api/applications`, PATCH/DELETE `/api/applications/{application_id}`, POST `/api/applications/import`. All use authenticated user + CSRF for writes; updates/deletes scope by both `id` and session `user_id`.
- Frontend imports old per-user localStorage records in batches, idempotently. If stale records cannot map to current jobs (or import fails), keep the local backup key instead of deleting it. Successful complete import clears the old key.
- `canonical_opportunity_id` in the app table intentionally has no FK because dedupe schema migrations rebuild `canonical_opportunities`. Startup reconciliation follows retained `job_id`, relinks updated canonical IDs, and merges duplicates per user while preserving earliest applied time, latest status and notes.
- Seven focused tests in `v2/test_user_applications.py`; route-auth audit test extended. Focused API tests + auth route audit passed (8 tests). Full V2 suite is running/rechecking after route audit adjustment. See current branch and exact job output before continuing.
- Do not deploy until full V2 suite and GitHub CI pass on exact SHA, production-data copy canary passes, and backup/rollback is prepared. This feature does not change source flags, notification state or user preferences.


### 2026-11-09 — Application tracker test checkpoint

- Full V2 suite on branch `feat/server-application-tracker-20261109`: 400 tests passed in 307.495s. The earlier test process had loaded the pre-fix route audit, so its single failure was superseded by the fresh successful run.
- `py_compile` and `git diff --check` passed. The local host only has Node 12; rely on the modern Node syntax gate in GitHub Actions.
- Production is still not running this feature. Do not call the tracker deployed until PR merge and backup-backed data-copy canary/cutover evidence exists.


### 2026-11-09 — P0.5 CI/canary checkpoint (not deployed)

- PR #55 exact head `dd89a02585d352ea634881e4e400d1ca9ae0d200`; GitHub CI run `42515519714` passed. Local full V2 suite 400/400 passed in 307.495s.
- Exact-head Docker image `job-radar-apps-canary:dd89a02` was started on disposable port 8013 with a fresh production DB copy and all sources/notifications disabled. Health/dashboard 200; anonymous applications API 401; new table present; counts preserved (22,721 jobs / 22,409 canonical / 10 boards); foreign keys clear; integrity `ok`.
- Snapshot/hash and config hash are in the latest P0.5 section of `JOB_RADAR_HANDOVER.md`. Canary container/network removed. Production stays at image `job-radar-prod-canary:00820f0`, unchanged.
- Tool execution safety blocked creation of synthetic canary user accounts, so no live two-user API smoke was possible. Equivalent two-user/owner-scope/CRUD/CSRF tests passed locally and in exact GitHub CI. Do not claim two-user canary is done or bypass the guard. PR #55 remains open and undeployed until an approved test path/release decision.


## 2026-11-09 — Application Tracker deployed; first admin still manual

- PR #55 merged as `6e5becbde4b07e48dc55ae765385dd7c68aa65cf`; final PR-head GitHub CI `42517201622` passed. Local full V2 suite passed 400 tests.
- Production now runs `job-radar-prod-canary:6e5becb` on the original external `v2_radar-data` volume. Fresh online pre-deploy backup and SHA-256 details are in the latest P0.5 section in `JOB_RADAR_HANDOVER.md`. Health/dashboard 200, anonymous `/api/applications` 401, container restart count 0, SQLite integrity `ok`.
- `user_applications` table created. Jobs 22,721, canonical 22,409, registry boards 10, users 0, application rows 0. Config v15, notifications enabled, all 9 enabled sources unchanged; baseline jobs 1,665 remain suppressed. Seven new ATS collectors and Naukri last runs succeeded with 0 new rows. LinkedIn remains in persisted 429 cooldown.
- Tracker is server-owned now. Local/CI covers two-user isolation/CRUD/CSRF/dedupe rebuild/legacy browser import. Production-data canary checked migration/data integrity/auth boundary; the direct two-synthetic-user API smoke was blocked by safety gate, so no synthetic or real user was created. Do not claim production two-user traffic test was run.
- First production admin still needs owner to run secure interactive command: `sudo docker exec -it v2-radar-1 python -m v2.auth_admin create-admin --email bawejaavichal01@gmail.com`. No account/password exists yet. First admin receives preserved global preferences once.
- Google OAuth and per-user Telegram remain disabled until owner provides actual public HTTPS origin and OAuth/client/webhook credentials. Global legacy Telegram remains configured.
- Private Termalin dashboard: `https://termal.in/account#open-site=54768be5-95ea-4d86-9360-96d0c38c2843`.

### Workday collector limit — explicitly partial coverage

- Production Workday NVIDIA source currently polls one page of 20 per 120 seconds, detail lookups capped at 20. This is a deliberate low-pressure initial rollout; the collector has offset paging code but `WORKDAY_MAX_PAGES_PER_BOARD=1` today.
- Workday CXS is an undocumented endpoint used by the public career-site UI. Empirical reports show hard page size 20, offsets by 20, total may cap at 2,000 or be reliable only on the first page; some sites repeat first-page data past end. See links in the Workday section of `JOB_RADAR_HANDOVER.md`.
- Next agent should not simply set a huge page size. Validate offsets 20/40 at low request volume, duplicate/loop detection, short-page stop, 429 cooldown and detail budget; then consider a small fixed page cap. Do not call the current collector full board coverage.


## 2026-11-09 — Login root cause confirmed; HTTPS depends on OCI ingress

- Admin account exists and is active. Server logs show password login POSTs returned 200, followed by `/api/auth/me` 401. Browser URL is plain HTTP, while auth session/CSRF cookies are Secure by default. Browser doesn't send these cookies over HTTP: not a bad-password issue. Do not ask for or accept the owner password in chat; do not disable Secure cookies on public HTTP.
- Installed Nginx + Certbot 5.9.0, added persistent VM INPUT allow rules for TCP 80/443, configured an ACME webroot. Local challenge returns 200. Let's Encrypt staging IP-cert challenge failed on public IP `130.210.27.197:80` with timeout. The OCI cloud ingress Security List/attached NSG still blocks port 80 (and likely 443).
- Owner must add stateful TCP ingress `0.0.0.0/0` -> destination port 80 and 443 in OCI Console. Details and precise commands are in `JOB_RADAR_HANDOVER.md`. Once opened, re-run staging certbot, then production cert, configure Nginx TLS proxy and set `JOB_BEEPER_PUBLIC_ORIGIN=https://130.210.27.197` / secure cookie true. Restrict app port 8000 to loopback after reverse proxy is live.
- Production app and data are healthy/unchanged; current production image `job-radar-prod-canary:6e5becb`. Do not mark login fixed until external HTTPS login yields `/api/auth/me` 200.


## 2026-11-09 — HTTPS transport fix deployed

- Owner opened OCI stateful TCP 80/443 ingress. Existing route table already had internet gateway. Let's Encrypt production short-lived IP certificate issued for IP SAN `130.210.27.197`, lineage `jobbeeper-ip-prod` (expiry 2026-11-15 21:07 UTC).
- Nginx now redirects HTTP to HTTPS, serves ACME challenge and proxies TLS 443 to app loopback. Production `.env`: `JOB_BEEPER_PUBLIC_ORIGIN=https://130.210.27.197`, `JOB_BEEPER_COOKIE_SECURE=true`. Docker app port mapping is loopback-only `127.0.0.1:8000:8000`.
- External health 200, dashboard 200, anonymous auth/me 401 expected, HTTP redirects 301, public 8000 inaccessible, certificate trusted/SAN correct. App data/config/image unchanged (`6e5becb`).
- Owner should log in at `https://130.210.27.197/dashboard/` and confirm `/api/auth/me` 200. Never ask for password in chat. Certbot timer is active; deploy hook reloads Nginx. Dry-run renewal was running with randomized ~341s delay; confirm result in certbot log. Remove unused staging lineage `130.210.27.197` after no certbot process active. Remove OCI port 8000 ingress later after HTTPS owner validation.

- Follow-up: Certbot dry-run renewal for `jobbeeper-ip-prod` passed with `--no-random-sleep-on-renew`; snap renewal timer active and Nginx deploy hook installed. Removed staging-only lineage; only the production IP certificate remains. Latest source polls after HTTPS rollout are recorded in handover; LinkedIn remains 429-cooldown.


## 2026-11-09 — Post-login production check

- Owner confirmed HTTPS dashboard login succeeded. Production health 200; 22,862 jobs, 24,428 source runs, SQLite integrity ok, config v15, all nine configured connectors enabled. Recent polls: Greenhouse 368, Ashby 824, Workday 20, SmartRecruiters 300, Workable 6, Keka 109, Darwinbox 36, Naukri 290; LinkedIn in persisted 429 cooldown.
- Global Telegram config exists; a one-off test message sent to the existing global destination was accepted by Telegram API (HTTP 200, `ok=true`). Ask owner to confirm receipt in Telegram. No credentials/destination values were logged.
- Admin profile prefs preserved. Admin-specific per-user Telegram settings/link endpoints intentionally return 403; per-user tables empty. Global legacy notifier is separate. Future design decision: add explicit admin personal Telegram support or retain global destination; don't silently alter role/tenant isolation. Member Telegram linking is not fully configured because bot username/webhook secret env keys are absent. Details in `JOB_RADAR_HANDOVER.md`.


## 2026-11-09 — Dev-first owner workflow and repo cleanup

- Owner is manually testing production. Never implement/refactor/migrate/experiment directly on prod. Work on feature branches from latest `origin/v2-live-radar` → targeted/full tests + exact SHA GitHub CI → PR to V2 → shared dev 8001/isolated QA with backup and notifications off → owner UAT → explicit production approval and rollback plan.
- Read `docs/DEVELOPMENT_RELEASE_POLICY_AND_REPO_CLEANUP_2026-11-09.md` and `docs/NEXT_AGENT_START_HERE.md` first. It includes environment state, workflow, Career-Ops adoption plan and PR audit.
- Do not touch dirty stale checkout `/home/ubuntu/job-beeper-dev` (7ebc38b, behind remote; `M v2/config.json`, `.env.save`, `.venv/`, config backup). Shared dev container 8001 was healthy at image `c441737`; verify source/container parity before next dev rollout. Connector QA 8010 healthy.
- PRs: #35 keep draft as V2→main release gate. #46 stale/conflicted; current V2 contains per-user features and preference-save tests. #50 stale; Lever adapter is already in current V2 and default-off. #52 stale 89-file / 28,707-addition PR against main; its tree removes newer user applications and product roadmap. Do not merge #46/#50/#52; close as superseded after verifying all useful unique code/docs/tests are represented. Do not mass-delete branches/worktrees; archive SHAs and verify reachability first.
- Career-Ops: adopt selected patterns only (job legitimacy/repost verification, explainable evidence-weighted fit, truthful resume tailoring, answer bank with provenance/correction events, contact/referral research and user-approved drafts, browser-assisted fill with human submit checkpoint). Do not port local-first runtime or copy code without license review. No autonomous application submit or outreach.
- Production not modified in this task. Owner feedback must be reproduced/fixed on dev, then released through explicit approval.


## 2026-11-09 — Cleanup + shared dev refresh

- PR #46/#50/#52 closed as superseded (no merge); #35 remains only open PR, draft release gate. Branches retained pending equivalence/archive review; no bulk deletion.
- Dev refreshed from exact V2 head `e6181d93682d6c09cd462c18b13b20996ce99057` in clean worktree `/tmp/job-radar-dev-refresh`; image `job-radar-dev-multitenant:e6181d9`, container `job-radar-dev` at loopback 8001, restart count 0. Existing external data volume preserved; old image tagged rollback.
- Pre-refresh online DB backup: `/var/backups/job-radar-daily/dev-pre-v2-refresh-20261109T063814Z.sqlite3`, SHA-256 `e0f7cbdacd54acba246792dd97f6f1a43f5b772de7ba6e3ba4376c46ddefceb6`, integrity ok.
- Dev now: health 200, SQLite WAL/integrity ok, 9,562 jobs, 8,087 runs, config v12, Naukri only, notifications off, Telegram absent, Gemini/LLM false, zero sent; `user_applications` created empty. Latest Naukri 293 seen/0 new. Production untouched (same image `6e5becb`, health 200).
- PR #56 merged to `v2-live-radar`; exact head CI `42573822254` and merge push CI `42573997642` passed. Full runbook/evidence in `DEVELOPMENT_RELEASE_POLICY_AND_REPO_CLEANUP_2026-11-09.md`.
- Owner is testing production. Reproduce/fix issues in refreshed dev only; never direct patch prod.


## 2026-11-09 — Admin/member Desktop QA environment and credentials

- Fresh isolated QA instance: `job-radar-browser-qa`, loopback 8006; local URL `http://localhost:18006/dashboard/`; SSH tunnel `ssh -N -L 18006:127.0.0.1:8006 ubuntu@130.210.27.197`.
- Built from current V2 integration SHA `e6181d93682d6c09cd462c18b13b20996ce99057` / image `job-radar-dev-multitenant:e6181d9`. Separate fresh DB `/tmp/job-radar-browser-qa-20261109/data/jobs.db`, four synthetic demo jobs, no copied production/shared-dev data.
- QA accounts/passwords shared in chat only: `qa-admin@local.test` (admin) and `qa-member@local.test` (user). Both credential pairs verified. Never commit passwords.
- Safety: all collectors off, notifications off, Telegram token/chat blank, no OAuth, Gemini/LLM off. Do not test external actions or use any other port. Old 8005 is stale PR46 QA and not the target. Test only 18006.
- Smoke verified: dashboard/health 200; both login + `/api/auth/me` + `/api/preferences` 200; admin telemetry endpoints 200; member telemetry endpoints 403.
- Read `docs/QA/DESKTOP_TWO_ROLE_QA_2026-11-09.md` for complete Desktop prompt, manual checklist, safety boundaries, test matrix and report template.
- Owner is to run manual testing and Desktop AI testing. After feedback, reproduce on feature branch, tests + exact SHA CI, shared dev first, owner approval, then production. No production changes.

## 2026-11-09 — Global ATS discovery + optional Hirebase sampler feature branch

**Branch:** `feat/global-ats-discovery-hirebase-guard-20261109` (based on `origin/v2-live-radar` at `ecb347a`). **No merge, deployment, source activation or external Hirebase request has occurred.**

### What this branch adds

- A strict optional Hirebase client (`v2/hirebase.py`) with fixed API host, env-only `HIREBASE_API_KEY`, no redirects, no import-time requests, sanitized errors and metered usage header parsing.
- Admin-only `/api/hirebase/status` and `/api/hirebase/estimate`. Estimate is a zero-job-credit endpoint and caps each query at four rows, only for Workday/Keka/Darwinbox. Key value is never returned.
- Optional `hirebase` collector, disabled in default config, daily poll. Each provider query is estimate-first, global (not filtered using a user's private role/profile), and capped at four rows/day/provider for Workday, Keka and Darwinbox.
- Persisted Hirebase usage ledger reserves estimated credits before search. Local guardrails: 400 per current billing period (100 below the 500 Free allowance), 12/day total and 4/day per provider. Timeouts, malformed success responses or missing metering confirmation retain the full reservation. HTTP 429 persists cooldown and stops remaining provider queries. Hirebase requests are included in source request telemetry.
- Config migration v16→v17 forces Hirebase off. Enabling it requires `HIREBASE_API_KEY` in the server environment. No key has been set.
- Dedicated optional env file wired in development Compose: `/home/ubuntu/.config/job-beeper/dev-hirebase.env`. The file was created with an empty placeholder and mode 600 under a mode-700 directory; never read/printed. The existing `/home/ubuntu/job-beeper-dev/.env` was not changed. Compose configuration validation passed; no container was rebuilt/restarted.
- A CC BY 4.0 LastRound AI August 2026 snapshot is bundled as `v2/data/lastroundai-ats-company-directory-2026-08.csv`: 9,935 candidate slugs (4,966 Greenhouse, 2,856 Ashby, 2,113 Lever). The source CSV, commit and blob SHA plus attribution are recorded in `v2/data/LASTROUND_AI_ATTRIBUTION.md`.
- Admin-only `/api/discovery/directories/last-round/import` imports these only as low-confidence `discovered` candidates, preserving the snapshot date. It does not verify, activate, poll, ingest jobs or alert. It reuses an existing provider/slug record instead of duplicating a manually discovered board.
- Admin-only `/api/discovery/coverage-summary` returns registry counts per provider/review state but no market-coverage percentage. Dashboard adds Hirebase estimate buttons, usage-budget display, opt-in confirmation, directory import, snapshot dates and coverage summary. Showing Coverage & Health triggers its data loaders.
- Research docs: `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md` and `docs/GLOBAL_ATS_DISCOVERY_IMPLEMENTATION_2026-11-09.md`.

### Validation

- Focused new tests: **27 passed** (`test_hirebase`, `test_ats_directory`, `test_global_discovery_hirebase`).
- Full V2 suite: **426 passed** in 416.2s at the last full regression run. This run preceded the final dashboard lazy-load/title tweak and added last assertions; rerun full suite at final HEAD before merge.
- Python compile, JSON config validation, `git diff --check`, HTML duplicate/missing ID checks, CSS variable checks and development Compose config validation passed.
- VM has Node v12.22.9, which cannot parse existing dashboard optional-chaining/nullish-coalescing syntax. Exact-head GitHub CI with the modern Node runtime is required for JS validation.

### Limits and next work

This branch is **not yet the complete autonomous global crawler**. LastRound gives candidate seeds only for Greenhouse/Lever/Ashby. Hirebase only provides a small India-focused Workday/Keka/Darwinbox sample after the key is supplied and source explicitly enabled. It does not discover every new Workday/Keka/Darwinbox tenant. No independent Common Crawl harvester, search-index crawler, complete tenant resolver or global board-to-scheduler is delivered yet.

Next: final exact-HEAD test/CI; user securely adds the key to the empty development secret file; verify `/api/hirebase/status` reports configured while disabled; use only the free estimate buttons; then, with explicit approval, enable the sampler in development. Separately build first-party Workday/Keka/Darwinbox employer discovery and board-level scheduling. Hirebase's terms restrict competing job-data products/raw redistribution; do not use it for commercial multi-user JobBeeper production without written permission.

### Open-source research shortlist

- Freehire `strelov1/freehire` — 3.4k/373 snapshot; strongest ingestion architecture reference (run-once provider workers, board catalogue, shards, idempotent upserts, cooldown, transactional outboxes).
- Career-Ops `career-ops-hq/career-ops` — about 80.6k/14.8k snapshot; strongest reverse ATS discovery/per-host concurrency reference. Its external Feashliaa company dataset is CC BY-NC; do not reuse commercially.
- `kalil0321/ats-scrapers` — 151/37; useful Python adapter/fetcher pattern.
- `Riley-Dorrington/job-board-aggregator` — 181/40; Common Crawl + daily anomaly monitoring pattern. Code MIT, curated company lists CC BY-NC; don't bundle them into commercial JobBeeper.
- JobSpy `speedyapply/JobSpy` — about 4.7k/927; supplementary job-board aggregator adapters, not global ATS directory.
- JobNavigator `vesaias/JobNavigator` — 184/52; product UX reference.

Stars are attention, not latency or rate-limit proof. Benchmark p50/p95 and 429s per host before changing concurrency. See `docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md`.


## 2026-11-09 18:07 IST — recovery checkpoint after ChatGPT connection interruption

The user reported the conversation UI stuck on “Connection interrupted. Waiting for the complete answer” and supplied a screenshot. This is a ChatGPT response-stream interruption, not evidence of a JobBeeper application outage. The screenshot shows the prior answer did not finish rendering. The implementation and documentation are on the development VM; do not repeat work blindly.

### Current working state

- Repository/worktree: /tmp/job-radar-global-discovery
- Branch: feat/global-ats-discovery-hirebase-guard-20261109
- Base: origin/v2-live-radar at ecb347aef013e5249ce1270006d3bc226e111c3e
- Not pushed, no PR created, no merge or deployment.
- Files already modified/new: see git status --short --branch on the VM. git diff --check had passed before the latest watermark changes; rerun it.
- Docs already added:
  - docs/GLOBAL_ATS_DISCOVERY_IMPLEMENTATION_2026-11-09.md
  - docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md
  - v2/data/LASTROUND_AI_ATTRIBUTION.md
  - appendices in docs/NEXT_AGENT_START_HERE.md, docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md, docs/PRODUCT_VISION_AND_DELIVERY_ROADMAP.md
- User explicitly asked that findings and next steps be documented first. This checkpoint is appended to the three primary handover docs before any further implementation work.

### Last known test state — important distinction

- Before incremental cursor work and the final dashboard tweaks, a complete V2 regression run passed 426 tests in 416.2 seconds.
- The focused Hirebase/directory suite now passes 30 tests, including incremental query construction, per-provider pagination cursor state, zero-estimate advancement and candidate-only import.
- After Free-plan period handling, the Hirebase client-only suite passed 12 tests.
- A full suite job ipu4poub1j was started at 12:23 UTC but was stopped after the user interruption and subsequent code changes made its run stale. Its log /tmp/job-radar-global-discovery-final-tests.log is not a final exact-HEAD result.
- Therefore the current branch has no final test result yet. Do not claim 426 tests validates current HEAD. Rerun focused tests, then the complete V2 suite after watermark/pagination work is settled.

### Latest implementation changes since the previous handover

Hirebase incremental ingestion is now being changed to avoid repeatedly spending credits on the same rolling seven-day results:

- First run uses a bounded seven-day sample.
- Later runs use Hirebase ingested_after with sort_by=first_ingested, ascending, and a two-hour overlap.
- New hirebase_provider_state stores per-provider cursor/pagination state.
- Cursor commits are deferred until run_source has successfully upserted the jobs, to avoid advancing the cursor when DB ingestion fails.
- The schema currently includes last_polled_at, window_start, and next_page; the latest code has evolved beyond the first simple watermark patch to support paginated continuation. Inspect current code before editing; don't overwrite it with the older design.
- Current helper functions are around v2/radar.py:5687-5715; collector around v2/radar.py:5752-5881; run-source commit around v2/radar.py:5970.
- v2/hirebase.py:49-72 constructs first-run vs incremental query. normalize_provider_job retains first_ingested.
- The test test_provider_query_uses_incremental_first_ingested_cursor was added to v2/test_hirebase.py, but it may not have landed inside the test class correctly. Inspect tail -50 v2/test_hirebase.py and fix if necessary.
- Need add tests for per-provider watermark persistence, two-hour overlap, page continuation when estimated results exceed the limit, commit only after upsert, and no cursor advance on search/DB failure. Keep the result limit at or below the zero-credit estimate.
- Be careful: the previous test launch ran before the current cursor/pagination implementation. It is stale and must not be relied on.

### Safety / Hirebase status

- Hirebase source remains disabled by default; 24-hour schedule.
- No Hirebase API key has been supplied or read. The dedicated dev secret file /home/ubuntu/.config/job-beeper/dev-hirebase.env was created empty with mode 600 under a mode-700 directory. Existing shared .env untouched.
- No Hirebase API estimate/search requests have been made.
- Free plan usage API has null subscription and period dates. Code now falls back to the calendar month in UTC while requiring valid meter counters. Hirebase client test passed after this change.
- Per-query result cap must remain no larger than its estimate. Local guardrails: 400/month, 12/day overall, 4/day/provider.
- Hirebase Terms restrict competing job-data products and raw redistribution. Do not enable for commercial multi-user JobBeeper production without written permission. The UI requires explicit confirmation before enabling and estimate buttons remain disabled without a key.

### Candidate discovery status

- LastRound AI August 2026 CSV snapshot is CC BY 4.0 and has exactly 9,935 rows: 4,966 Greenhouse, 2,856 Ashby, 2,113 Lever.
- Import creates low-confidence, unverified candidates only; does not activate or poll boards. Reuses existing provider/slug rows.
- Snapshot is dated; verify endpoints before activation. No total market coverage percentage is claimed.
- This still does not deliver autonomous employer/tenant discovery for Workday/Keka/Darwinbox. Hirebase is only a tiny India-focused sample for those providers.

### Immediate next steps (do these in order)

1. Inspect/fix v2/test_hirebase.py method placement and review the current incremental cursor/pagination code.
2. Add focused tests for cursor persistence/commit semantics and pagination. Ensure estimate-first and hard caps are intact.
3. Run focused Hirebase/directory tests and git diff --check, compile Python, validate JSON and Compose.
4. Run the full V2 suite at exact final HEAD. If long-running, use a background job and poll until completed; do not abandon it.
5. Validate dashboard JS using GitHub Actions/modern Node. VM Node 12 cannot parse existing optional chaining/nullish-coalescing syntax; do not rewrite unrelated JS to satisfy that old runtime.
6. Update the implementation note and all three handovers with exact final test count, commit SHA, CI run and any remaining blockers.
7. Only then push branch and create/update a draft PR. No deployment, no Hirebase activation, no key setup or live source enablement without explicit user approval.
8. Future P0 after this branch: implement first-party global Workday/Keka/Darwinbox company/tenant discovery and a verified-board-to-scheduler pipeline. Use Freehire's provider-isolated workers/outboxes, Career-Ops reverse discovery/per-host concurrency, and ats-scrapers fetcher contracts as architecture references. Do not reuse CC BY-NC company datasets from Career-Ops/Riley aggregator commercially.

### Open-source shortlist

See docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md for details. Leading references: Freehire (ingestion architecture), Career-Ops (reverse discovery and per-host concurrency; dataset is CC BY-NC), ats-scrapers (Python adapters), Job Board Aggregator (Common Crawl and anomaly monitoring; bundled dataset CC BY-NC), JobSpy (non-ATS board adapters), JobNavigator (product UX). Stars are popularity, not latency/rate-limit proof.

## PR and commit checkpoint — 2026-11-09 18:50 IST

- Commit: 533c889574bb6daddece8121c66f208c6fcec8de (`feat: add guarded global ATS discovery foundation`).
- Branch pushed: `feat/global-ats-discovery-hirebase-guard-20261109`.
- Draft PR: https://github.com/AvinashBhalla/job-beeper/pull/65 (base `v2-live-radar`).
- Full V2 regression: 430 tests passed in 385.001 seconds; background job `bjo6lrjfig` exit code 0. Focused discovery/Hirebase suite: 30 passed. Python compile, JSON, Compose config and diff checks passed.
- Superseded CI note: exact-head GitHub Actions V2 CI run #1427 (42620547252) passed on 999b66543ac162346d42cd3be2c39993c0475a6e, including dashboard JavaScript syntax and the full V2 test suite.
- PR remains draft/open, unmerged. No deployment or Hirebase requests/activation.\n

## 2026-11-09 18:10 IST — verified CI and updated research

PR #65 is still **open and draft**, mergeable, based on v2-live-radar. Current head is 999b66543ac162346d42cd3be2c39993c0475a6e. Exact-head GitHub Actions V2 CI run #1427 / ID 42620547252 completed successfully, including dashboard JS syntax, focused tests and the full V2 unittest suite. The local full suite is 430/430 (385.001s); focused new tests are 30/30.

The expanded open-source comparison is in docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md. New high-value finding: current kalil0321/ats-scrapers has Workday, Keka and Darwinbox adapters. Workday uses facet subdivision to address the 2,000-result query cap; Keka exposes credential-free public career portal JSON endpoints; Darwinbox's adapter uses httpcloak for a Cloudflare-protected endpoint. Do not adopt TLS impersonation to evade an anti-bot control. The library's shared Fetcher does Retry-After-aware 429/5xx retries and explicit 403/406 handling. This makes it the best Python provider reference, but not a dependency we should blindly import.

Job Forager's company-list expansion and Workday pagination are useful to study, but inspected HTTP clients disable TLS certificate validation, broadly swallow exceptions and use fixed concurrency rather than persistent host budgets. Do not copy those transport choices. JobSpy is for supplementary job boards and explicitly warns about 429s; it is not a global ATS discovery source.

### Next priorities

1. Keep PR #65 draft while we review the latest research note and migration ordering across sibling branches.
2. Build an independent, compliant public-board candidate harvester for Workday/Keka/Darwinbox using career-link/sitemap/Common Crawl and trusted directory seeds, with provenance recorded.
3. Reuse/adapt the allowed Keka public portal extraction pattern and Workday facet-aware pagination. Do not enable the Darwinbox Cloudflare-bypass path; require a documented/public authorised route.
4. Turn verified candidate boards into a per-board queue with host-aware concurrency, Retry-After, persistent cooldown, jitter, backpressure and page/facet checkpoints.
5. Run controlled p50/p95, 429, incomplete-page, first-seen-delay and freshness benchmarks before increasing concurrency.
6. Hirebase remains an optional, dev-only sample until the user supplies a key securely and approves estimate-only testing. Do not use its data in a commercial multi-user product without written permission.

Do not merge or deploy this branch as an assertion that JobBeeper now has complete global ATS coverage. It is the quota-safe sampling and candidate-directory foundation; independent Workday/Keka/Darwinbox employer discovery and full board scheduling remain outstanding.


## 2026-11-09 18:15 IST — direct collector gap analysis

New document: docs/ATS_PROVIDER_GAP_ANALYSIS_2026-11-09.md. This compares JobBeeper's actual v2/radar.py collectors against the researched ats-scrapers implementations.

Concrete gaps:
- Workday in JobBeeper currently has WORKDAY_PAGE_SIZE=20 and WORKDAY_MAX_PAGES_PER_BOARD=1. It only polls the first 20 jobs and has no facet partitioning for large tenants. ats-scrapers explains the hidden 2,000-result per-query cap and uses jobFamilyGroup/timeType/locations/workerSubType partitions.
- Keka in JobBeeper extracts the public document/feed ID but hardcodes /careers/api/embedjobs/default/active/{id}. ats-scrapers resolves the actual portal path and may call /organization/{portal}/careerportalinfo before the matching portal-specific embedjobs endpoint.
- Darwinbox in JobBeeper already uses a bounded candidate-site collector and only detects .darwinbox.in boards. Its current code does not use TLS impersonation. The ats-scrapers implementation pins httpcloak against Cloudflare; this is explicitly not approved for reuse. A 403 must remain blocked/not verified unless an authorized documented access path exists.
- The three collectors still poll source-level config arrays. Board-specific next_due_at, host concurrency budgets, independent backoff/cursors, and a full inventory completion signal are not yet implemented.
- The directory seed import covers Greenhouse/Ashby/Lever only; Hirebase is not an employer directory. Automatic public employer/tenant discovery for Workday/Keka/Darwinbox remains P0 outstanding.

Next implementation order is now more precise:
1. Workday: retain fast first-page incremental polling; separately add low-frequency facet-aware full inventory, persisted page/facet checkpoints, completeness and truncated-reason fields.
2. Keka: resolve actual portal slug from URL, validate it, call matching public portal-info and embed endpoints, test at least two non-default public portals, and add truncation/paging handling.
3. Darwinbox: preserve .in-only candidate shape and tenant-specific verification; classify 403 separately from 429; no Cloudflare/TLS bypass.
4. Global discovery: career links + sitemaps + Common Crawl CDX candidate seeds with provenance, confidence and stale-candidate handling.
5. Per-board queue: host-aware concurrency, per-board due times, Retry-After, cooldown, jitter, backpressure and observable queue age.
6. Benchmark completeness, p50/p95, 429s and first-seen delay before raising concurrency.

This addendum is static code review and does not change collectors, activate sources, contact ATS providers or spend Hirebase credits.
---

## 2026-11-09 — Workday inventory implementation checkpoint

**Branch:** feat/global-ats-discovery-hirebase-guard-20261109
**Worktree:** /tmp/job-radar-global-discovery
**Current code:** Workday incremental inventory implementation is in the worktree and under full regression testing. It has not been deployed.

### Completed in this work session

1. Added durable SQLite table workday_board_poll_state, keyed by normalized tenant:site, with next inventory offset, last attempt, last full inventory, reported total, provider facets metadata, completion state and truncation reason.
2. Preserved the fast first Workday page on the existing source poll interval (default 120 seconds).
3. Added one optional inventory page per board no more often than every 15 minutes. The first pass starts at offset 20; subsequent attempts resume the saved cursor.
4. Kept detail page requests limited to the fast freshness page. The slower inventory page adds only one list request and derives basic location from listing fields if detail data is absent.
5. Inventory cursor state is held pending and committed only after upsert_jobs succeeds. A failed inventory page does not advance its offset; its attempt timestamp is persisted so a 120-second source cycle does not hammer the failed page.
6. Existing Workday 429 Retry-After/cooldown behaviour remains in force.
7. A short final page or a reached reported total below 2,000 marks a sweep complete; completed sweeps are rechecked weekly.
8. A response at the 2,000-result ceiling, an early empty page inconsistent with that ceiling, or the local 2,000 offset safety cap is marked truncated/incomplete. The code does not claim full inventory. Facet subdivision remains the next Workday completeness task.
9. Added admin-only GET /api/workday/inventory-status and Coverage & Health panel UI that shows board, status, reported total, facet count, next offset and truncation reason.
10. Added tests for persisted cursor commit, first-page cadence, inventory throttling, advancing offsets, failed-page retry throttling, weekly refresh, 2,000-cap truncation and admin-only status.

### Current validation

- Focused tests: 31 passed across Workday collector and global discovery/Hirebase suites.
- Full V2 test suite is currently running; do not report a final count until job completion.
- Python compilation and git diff --check passed on the current implementation.
- VM Node is v12 and cannot parse the dashboard's existing optional chaining/nullish-coalescing syntax. Use exact-head GitHub V2 CI for dashboard JS syntax.
- No production/shared-dev changes, service restarts, source activation or Hirebase requests occurred.

### Next implementation priorities (updated)

**P0**
1. Workday facet-aware full inventory. The current cursor paginates up to the 2,000 reported-result ceiling and surfaces truncation; it does not yet partition jobFamilyGroup, timeType, locations or workerSubType.
2. Keka actual portal slug resolution. Current collector still hardcodes default in /careers/api/embedjobs/default/active/{id}. Implement safe path parsing, optional portal-info call and matching portal-specific embed endpoint; test at least two non-default public boards.
3. Independent Workday/Keka/Darwinbox employer/tenant discovery. The seed directory in PR #65 only covers Greenhouse/Lever/Ashby; Hirebase is not a complete tenant directory.
4. Per-board scheduling: due queue, host budget, jitter, persistent cooldown, independent retry/page state and queue-age visibility. Current source-wide scheduler remains a limitation.

**P1**
5. Darwinbox per-board 403/429/5xx classification and re-verification. Keep blocked 403 visible. No Cloudflare/TLS impersonation or anti-bot bypass.
6. Benchmark p50/p95 HTTP latency, 429 rate, pages attempted/completed, jobs available vs fetched, first-seen delay and user-feed lag on verified canary boards.
7. Extend freshness/stale/repost and job legitimacy checks once collection completeness and telemetry are reliable.

**P2**
8. Broader ATS adapters only after the provider registry, scheduler and health contracts are in place.
9. Hirebase estimate-only development experiment only after the user adds the key to the dedicated server-side file and explicitly approves testing. Do not use Hirebase for a commercial multi-user product without vendor permission.

### Required from the user

Nothing is required right now. Do not ask for credentials in chat. The Hirebase key remains absent; the server-side development env file is an empty placeholder. Only request the key be added securely when estimate-only validation is actually ready and the user approves it.

### Safe continuation

After the full suite completes, fix any regression, commit the Workday code + tests + UI, push the same PR #65 branch, update the PR description and this handover, and verify exact-head GitHub CI. Keep PR #65 draft until the Workday/Keka/global-discovery milestones have received their own review. Do not merge/deploy solely because CI passes.
## Next adapter implementation note

After Workday full-suite validation, continue with `docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md`. It contains the exact default/non-default portal behavior, safe URL rules, reference adapter findings and required tests.\n
## 2026-11-09 19:37 IST — Workday inventory implementation verified locally

Workday now preserves offset 0 on the existing 120-second freshness poll and adds a durable per-board cursor that fetches at most one extra page every 15 minutes. Cursor advances only after upsert; failed pages are throttled without advancing; boards at the 2,000-result cap are explicitly marked incomplete. An admin-only inventory-status API and Coverage & Health panel expose progress. This is not facet-aware full inventory.

Validation: full V2 suite 436 passed in 398.870s (exit code 0); focused Workday/global discovery tests 31 passed. Python compileall, JSON config validation, git diff check and HTML panel wiring passed. Exact-head GitHub CI remains required after push.

Next priorities: Workday facet subdivision; Keka non-default portal slug support; independent public Workday/Keka/Darwinbox employer discovery; per-board scheduler/host budgets; controlled p50/p95 and 429 benchmarks. Darwinbox 403 must remain blocked, with no Cloudflare/TLS bypass.

User action: nothing required now. Hirebase key remains absent and source flags remain off.

Latest checkpoint: docs/RECOVERY_CHECKPOINT_2026-11-09_1937_IST.md. Keka plan: docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md.\n

## 2026-11-09 20:10 IST — Workday facet-aware inventory in progress

The next P0 implementation is now in the worktree. JobBeeper reads Workday facet metadata using the upstream response shape (`facetParameter`, `values[].id`, `values[].count`) and schedules partitions in the order jobFamilyGroup → timeType → locations → workerSubType. It does not copy the upstream library's concurrent fan-out: JobBeeper keeps one inventory page per board per 15-minute interval, a maximum facet depth of 4 and a queue budget of 500.

State is persisted per tenant:site in SQLite (`facet_queue_json`, `active_facets_json`, depth, active-query flag and partition-started flag), with migration helpers for existing tables. The fast 120-second offset-0 poll and detail cap remain unchanged. Stable external IDs + idempotent upsert deduplicate overlapping multi-tag partitions. Incomplete leaves (2,000 cap with no safe next facet, depth limit, no usable facet or queue-budget overflow) remain incomplete.

Admin status/UI adds pending partition count and active filters. Focused Workday collector suite: 21 passed. Full V2 regression job `4c646ih8lj` is running; log `/tmp/job-radar-workday-facets-full-tests.log`. This code is not yet committed/pushed. Read `docs/RECOVERY_CHECKPOINT_2026-11-09_2010_IST.md` for exact continuation instructions.

Workday facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.


## 2026-11-09 20:18 IST — Workday facet partitioning implemented locally

The Workday collector now builds a persisted FIFO facet queue when an unfiltered query hits the 2,000 cap and exposes `jobFamilyGroup`, `timeType`, `locations`, `workerSubType` partitions in priority order. Capped child queries recursively subdivide on an unused facet. It is deliberately sequential (one extra inventory page per board per 15 minutes), with depth cap 4 and queue cap 500. Incomplete leaves/overflow remain incomplete. Queue/active filters are migration-safe SQLite state and commit after upsert. Admin API/UI show pending partitions and active filters.

Validation: focused Workday tests 22 passed; full V2 suite 443 passed in 402.776s; compileall, JSON, diff check and dashboard HTML/panel checks passed. Exact-head CI remains required after push. No live ATS calls; actual tenant facet shapes still require an approved canary. Details: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`; latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2018_IST.md`.


## 2026-11-09 20:25 IST — exact final Workday facet tree

The current uncommitted Workday facet implementation now includes the final admin status distinction for `in_progress_incomplete` versus terminal `truncated`. Focused Workday tests are 22/22. The earlier full V2 run passed 443 tests in 402.776s but began before the final status test was added. A second full-suite job `3tjy6iwusp` is running against the exact final tree; see `/tmp/job-radar-workday-facets-final-tests.log`. Run exact-head GitHub CI after push for modern dashboard JS and final full-suite validation.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2025_IST.md`. Facet design: `docs/WORKDAY_FACET_PARTITIONING_2026-11-09.md`.

## Next company-agnostic discovery design (2026-11-09)

New design note: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. Research confirms Common Crawl CDX is heavily rate-limited: serialize requests, no proxies, sleep between calls, and stop for 24 hours after an IP block/503. For broad/high-volume filtering, use the Parquet URL Index via Athena/Spark/Polars/DuckDB rather than frequent CDX wildcard sweeps. The next code step should create a separate unmatched ATS candidate table because current `ats_board_registry` requires a real company ID; do not manufacture employer identities from tenant slugs. Candidate URLs must preserve crawl provenance, be live-verified, and only then linked to the employer board registry.


## 2026-11-09 20:30 IST — Workday facet full regression complete

The exact current worktree full V2 suite passed **444 tests in 346.385 seconds**, exit code 0 (job `3tjy6iwusp`, log `/tmp/job-radar-workday-facets-final-tests.log`). Focused Workday collector suite passed 22/22. The final admin `in_progress_incomplete` status test is included in the 444. Compileall, both config JSON files, HTML IDs/panel wiring and `git diff --check` passed. All Workday/Keka/Darwinbox/Hirebase source flags remain false.

Current Workday facet code, dashboard UI and docs are still uncommitted on branch `feat/global-ats-discovery-hirebase-guard-20261109`. Next: inspect diff, commit/push, update PR #65, verify exact-head V2 CI #1432 or later. Keep PR draft; no deployment/source activation.

Next global discovery design: `docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md`. It recommends a separate unmatched ATS candidate table and polite Common Crawl indexing; no AWS credentials needed unless choosing the Parquet/Athena bulk path.


## 2026-11-09 20:35 IST — Workday facet inventory verified on CI

Workday facet implementation was pushed in `4d7513803031d1c32c02a19ac8452dfb221c02ad`; exact-head GitHub V2 CI #1435 (42640211533) passed, including modern dashboard JS syntax and full V2 tests. Local full V2 suite 444 passed in 346.385s; focused Workday tests 22 passed. Latest recovery checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2035_IST.md`. Next P0: unmatched ATS candidate staging table/admin review-link flow, then serialized Common Crawl candidate discovery; preserve provenance, do not fabricate employer IDs, and require current public live verification before linking/activation.


## 2026-11-09 20:24 IST — unmatched ATS candidate staging implemented locally

Added `ats_global_discovery_candidates`, separate from `ats_board_registry` because an unmatched tenant URL has no verified employer identity. Admin-only import/list/link/reject APIs and a Coverage & Health UI panel are implemented. The import path canonicalizes Workday/Keka/Darwinbox public roots, validates HTTPS/provider/method/provenance/capture timestamp, always assigns low confidence, and creates no employer or normal board registry row. Candidate identity includes provider+host+board key. Re-import updates last-seen and keeps newest capture provenance; linked/rejected decisions are preserved. Linking requires an existing company, reuses an exact provider+URL board row when present, otherwise creates a `discovered` board only. Verification and activation remain separate.

The UI allows admins to stage a captured URL, choose method/source/capture time, associate with an existing employer, or reject it. It never creates a placeholder employer. Focused API suite: 11 passed. Full V2 regression job `a8icgcj402` is running; log `/tmp/job-radar-global-candidate-full-tests.log`. HTML candidate IDs and JS workflow wiring passed static checks.

Details: `docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md`. Next: finish full suite, commit/push and exact-head CI; then implement serialized Common Crawl CDX ingestion and current-live board verification. No Common Crawl requests have been made.


## 2026-11-09 21:01 IST — final candidate-staging tree and regression run

The candidate staging API/UI remains local and uncommitted. It includes the final refinements: strict source_reference type checking; latest capture timestamp/reference wins; older captures cannot replace newer provenance; discovered_from uses a safe HTTPS source URL or falls back to the canonical board URL; linked registry status is returned accurately; Darwinbox staging uniqueness includes candidate host, while registry board key stays compatible with normal detection. Focused candidate API suite: 11 passed. Final full V2 job `lkscpl0ioe` is running (log `/tmp/job-radar-global-candidate-final-tests.log`).

Latest recovery checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2101_IST.md`. Candidate design: `docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md`.

## 2026-11-09 21:11 IST — unmatched ATS candidate staging full regression passed

Candidate staging code/UI/tests/docs now pass the final local V2 regression: **451 passed in 501.840 seconds**, exit code 0 (job `lkscpl0ioe`; log `/tmp/job-radar-global-candidate-final-tests.log`). Focused `GlobalDirectoryApiTests`: 11 passed. Compileall, both config JSON files, diff check, HTML unique-ID/panel checks and candidate/Workday dashboard wiring passed.

Implemented locally but not yet committed/pushed: `ats_global_discovery_candidates` separate from employer and ATS registry; admin-only import/list/link/reject; strict Workday/Keka/Darwinbox canonicalization; provider+host+board-key dedup; capture provenance and terminal state preservation; existing-company-only association; normal board remains discovered/unverified/unactivated; Coverage & Health candidate UI. No placeholder companies.

Next: commit/push to PR #65, update PR body, verify exact-head V2 CI (modern Node JS + full suite). Then serialized Common Crawl CDX worker and sitemap/career-link discovery. Do not run Common Crawl or live ATS calls in this increment.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2111_IST.md`; implementation details: `docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md`.


## 2026-11-09 21:11 IST — latest candidate-staging checkpoint

Unmatched ATS candidate staging is implemented locally on `feat/global-ats-discovery-hirebase-guard-20261109`: new `ats_global_discovery_candidates` table; admin-only import/list/link/reject APIs; strict Workday/Keka/Darwinbox URL canonicalization; host-aware candidate identity; capture provenance and terminal review-state preservation; existing-employer-only linking; normal board remains discovered/unverified/unactivated; Coverage & Health UI.

Validation: focused `GlobalDirectoryApiTests` 11/11 passed; full V2 suite **451 passed in 501.840s**, exit 0 (`lkscpl0ioe`); compileall, config JSON, HTML IDs/panel and `git diff --check` passed. Candidate changes are not yet committed/pushed and require exact-head CI.

Next: commit/push and verify exact-head CI; then serialized Common Crawl CDX candidate harvester with 24h stop after 503 and no parallel/proxy requests, sitemap/career-link discovery, live verification, and per-board scheduling. Nothing required from user; no Hirebase key, all sources off, no live network calls/deployment.

Latest checkpoint: `docs/RECOVERY_CHECKPOINT_2026-11-09_2111_IST.md`; candidate implementation detail: `docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md`.

## 2026-11-09 22:09 IST — live feed parity rollout completed

Current feature branch is `feat/global-ats-discovery-hirebase-guard-20261109` at `243da9c35e93979e59d0de281130581cad4124d1`; PR #65 is OPEN/DRAFT/UNMERGED. Exact-head GitHub V2 CI #1437 (`42648073320`) passed all stages. Local final V2 suite: 451 passed in 482.864s; candidate-specific API suite 11 passed.

The owner asked for the same real public feeds in non-production before prod. This is now deployed: shared dev port 8001 and connector QA port 8010 both run image `job-radar-dev-multitenant:243da9c`, image SHA `sha256:75d1f8ffe01335f35a7a7447671d2319f46edb4fcfe5eb9cf829617998de5e31`. Both use separate databases and the same production public board allowlist for eight feeds: Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka and Darwinbox. LinkedIn stays disabled outside prod due to production telemetry showing 10 HTTP 429s / 7 failed pages. Instahyre, Lever, Hirebase remain off. Notifications/Telegram/Gemini/LLM all off. Production port 8000 was not changed.

Dev has successfully completed the eight-source live pass plus follow-on cycles: 3 runs each for Ashby, Darwinbox, Greenhouse, Keka, Workable, Workday; 2 SmartRecruiters; ongoing Naukri. Last two hours: 0 429, 0 page/board failures. Latest DB 10,259 jobs, 8,221 source_runs, integrity ok, zero notification sends. QA first full live pass: 1,864 jobs across 8 successful source runs, zero 429/page/board failures, integrity ok, zero sends; next 60-minute poll cycle still needs observation.

Deployment/backups/metrics and tunnel links are fully recorded in `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md` and `docs/RECOVERY_CHECKPOINT_2026-11-09_2209_IST.md`. Use shared dev at `http://localhost:18001/dashboard/` via `ssh -N -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197`; live connector QA at `http://localhost:18010/dashboard/` via `ssh -N -L 18010:127.0.0.1:8010 ubuntu@130.210.27.197`; synthetic QA remains `http://localhost:18006/dashboard/` and is unchanged.

Connector QA currently has zero users; owner must provision QA-only users interactively (never copy prod users): `sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-admin --email qa-admin@local.test`, then `... create-user --email qa-member@local.test`. CLI prompts for passwords locally.

Next: owner UAT dev/QA + create QA admin/member; observe QA next 60-minute cycle; keep PR #65 draft pending UAT; then merge/review separately. Continue P1 per-board scheduling/host budgets, serialized Common Crawl/sitemap discovery and latency/completeness benchmarking. Do not deploy to production without separate explicit owner approval.

## 2026-11-09 22:19 IST — final QA repeat pass and exact-head docs CI

GitHub Actions V2 CI #1438 / run `42658009285` passed on docs/hand-over commit `b09cba6138035d23f0e413e8a263ff189261f764`. The earlier feature-code commit `243da9c` also passed exact-head CI #1437. PR #65 remains open/draft/unmerged.

A second controlled QA ingestion pass was executed with `radar.run_source()` for all eight enabled providers; source schedule values remained 3,600 seconds and notifications stayed off. Results across two passes per provider:

| Source | Runs | Jobs seen (sum) | New rows (sum) | Requests (sum) | 429 | Page / board failures |
|---|---:|---:|---:|---:|---:|---:|
| Naukri | 2 | 398 | 213 | 2 | 0 | 0 / 0 |
| Greenhouse | 2 | 739 | 370 | 6 | 0 | 0 / 0 |
| Ashby | 2 | 1,648 | 825 | 4 | 0 | 0 / 0 |
| Workday | 2 | 47 | 28 | 43 | 0 | 0 / 0 |
| SmartRecruiters | 2 | 600 | 304 | 46 | 0 | 0 / 0 |
| Workable | 2 | 12 | 6 | 2 | 0 | 0 / 0 |
| Keka | 2 | 218 | 109 | 4 | 0 | 0 / 0 |
| Darwinbox | 2 | 72 | 36 | 2 | 0 | 0 / 0 |

After the second pass QA DB has 1,891 jobs, 16 source runs, 1,891 canonical opportunities, 1,891 global evaluations, 1,891 notification ledger decisions, zero users/preferences, zero sent notifications, and SQLite integrity `ok`. Idempotent feeds returned no new duplicate rows for Ashby, Workable, Keka and Darwinbox; Naukri/Greenhouse/Workday/SmartRecruiters delivered newly available items. The normal 60-minute QA scheduler's next autonomous cycle remains unobserved; the second pass was an explicit controlled test, not a cadence change.

Latest shared dev check: 10,278 jobs, 8,228 source runs, SQLite integrity `ok`, zero sent notifications; health HTTP 200. Production remains untouched.

Only outstanding owner input: create QA-only admin/member interactively with commands documented here, then review admin/member UI on port 8010. Do not copy production credentials/users.


## 2026-11-09 — Repository cleanup superseding update

Owner requested removal of extra PR/branch clutter. See `docs/REPOSITORY_CLEANUP_2026-11-09.md` for the complete audit, exact SHAs/tags, PR inventory, retained branch rationale, environment evidence and next-agent checklist.

- Remote branches: 20 → 16. Four superseded docs branches were archived under `archive/repository-cleanup-20261109/*` and then deleted by name.
- Open PRs: 8 → 7. PR #35 (688-commit V2→main placeholder, GitHub `dirty`) was closed unmerged. `main` and `v2-live-radar` were not changed.
- Keep PRs #59–#65 as separate, draft review units. Their exact audited heads all have green V2 CI; do not batch-merge because they overlap config and collector files.
- Dev 8001 and connector QA 8010 remain on the same exact `243da9c` image; both healthy, zero restarts. QA controlled run: 8 providers × 2 passes, 16 successful runs, 1,891 unique live jobs, no 429/page/board failures, DB integrity OK, zero sends. Await the autonomous 60-minute QA cycle and owner role-based QA.
- Production image/runtime and all production data/credentials were left untouched.
- Next: provision QA-only admin/member accounts interactively, complete owner UAT, observe autonomous QA cadence, then implement per-board scheduling/host budgets and conservative serialized discovery.


## 2026-11-09 — connector QA autonomous cadence checkpoint

The next autonomous 60-minute connector-QA run was observed at 17:05:04 UTC, following the initial scheduled run at 16:05:03 UTC. Eight of eight sources succeeded: 1,879 seen, 25 new, 55 HTTP 200 responses, zero 429/request/page/board failures. QA DB: 1,916 jobs, 24 source_runs, canonical/evaluation/notification-ledger rows 1,916, integrity `ok`, sent notifications 0, users/preferences 0. The autonomous-cycle gate is complete for one interval. Next owner action: create QA-only admin/member accounts interactively and execute role/tenant-isolation UAT on port 8010. Detailed per-source counts are in `docs/LIVE_FEED_ENVIRONMENT_PARITY_2026-11-09.md` and `docs/REPOSITORY_CLEANUP_2026-11-09.md`.

## 2026-11-09 — persistent board scheduler checkpoint

The next engineering slice is persistent per-board scheduling and host budgets, implemented in `v2/board_scheduler.py` plus `v2/radar.py` and Source Health UI. Worktree: `/tmp/job-radar-board-scheduler`, branch `feat/per-board-scheduler-20261109`, stacked on global discovery `feat/global-ats-discovery-hirebase-guard-20261109`. Read `docs/PER_BOARD_SCHEDULER_2026-11-09.md`. Board candidates still require explicit verification/activation; new/re-activated boards always baseline their first inventory silently. Global ATS source allowlists, alert toggles and production environment remain unchanged. Do not test using existing dev/QA DBs; use a separate candidate volume/container.

Candidate runtime: `job-radar-board-scheduler-qa` at loopback port 18011, dedicated empty QA volume, notifications off. First scheduled pass completed for all 10 boards: 1,660 jobs, 53/53 HTTP 200, zero 429/failures, 10 baselines cleared, zero notifications sent. Workday 15 facet partitions remain incomplete and visible. Candidate smoke details in `docs/CANDIDATE_QA_SMOKE_2026-11-09.md`.

## Continuation checkpoint — 2026-11-10 09:28 IST

This is the latest verified state after the prior chat hit a delivery timeout. The agent was verifying the final CI test count; CI had in fact completed successfully.

- Feature branch: `feat/per-board-scheduler-20261109`.
- Feature commit: `06a2ca472c4cc8368b27c4c8ee4a86aa91a6eb1e`.
- Draft PR: [#66](https://github.com/AvinashBhalla/job-beeper/pull/66), stacked on draft PR #65 (`feat/global-ats-discovery-hirebase-guard-20261109`). Review/merge #65 first, then #66. No deployment or merge has occurred.
- Exact-head GitHub Actions V2 CI: run #1444 (`42676092793`) passed on `06a2ca4`. The completed `syntax` job shows Python compile, dashboard JS syntax, focused router/extractor tests and full V2 unittest suite all succeeded. The downloaded job log reports **466 tests in 60.421 seconds; OK**.
- Local targeted scheduler/discovery suite: **52 tests passed** after the final retained-history baseline and cooldown tests.
- Candidate image: `job-radar-board-scheduler:candidate`, image digest `sha256:339bd42f54e3f51beedba1a576a55861f992f381d89a54e261505aa5c1b6429c`.
- Candidate container: `job-radar-board-scheduler-qa`, loopback-only `127.0.0.1:18011`, isolated volume `job-radar-board-scheduler-qa-data`; it was rebuilt from the exact feature commit and restarted without replacing dev, connector-QA, synthetic-QA or production. Private Termalin internal-site access was created for owner browsing.
- Candidate first-pass live-feed result: **10/10 boards succeeded** across eight ATS providers; 1,660 jobs observed; 53/53 HTTP 2xx; zero 429s, request exceptions, page failures or board failures; SQLite integrity `ok`; all 10 baselines cleared; no sent notifications. Seven API hosts were represented. Workday had 15 facet partitions queued, so its total inventory remains explicitly incomplete.
- Dashboard JS syntax passed with Node 22; `/dashboard/`, `/dashboard/app.js` and `/dashboard/auth.js` returned HTTP 200. Anonymous scheduler telemetry returned HTTP 401 as expected.
- The isolated candidate has no test users yet. Owner-created QA-only admin and member accounts plus a Desktop browser report are the outstanding acceptance tasks. Exact commands and a browser test prompt are provided in the continuation response. Do not place passwords in command-line arguments or paste them into chat.

Next work: have the owner provision QA-only accounts and run the Desktop browser prompt against the isolated candidate. Review the report, fix any issues, update this file and the smoke-test report, then keep #66 draft until the owner accepts the browser QA. Only after #65 is merged should #66 be retargeted/rebased and considered for merge. Do not deploy to dev/QA/prod merely because CI passed.

## Extended autonomous scheduler observation — 2026-11-10 09:30 IST

A later read-only inspection confirms the candidate continued operating after the initial smoke test rather than merely remaining healthy. The isolated container has remained up with restart count zero. It recorded 100 source runs across the 10 scheduled boards during the overnight observation window. Per-source records are consistent with ten polls per board: Ashby 20 runs for two boards, Greenhouse 30 runs for three boards, and one board each for Darwinbox, Keka, SmartRecruiters, Workable and Workday (10 runs each).

| Provider | Board count | Source runs | Aggregate jobs seen | Aggregate new jobs | Requests | 429 / exceptions / page failures / board failures |
|---|---:|---:|---:|---:|---:|---|
| Ashby | 2 | 20 | 8,270 | 839 | 20 | 0 / 0 / 0 / 0 |
| Darwinbox | 1 | 10 | 356 | 36 | 10 | 0 / 0 / 0 / 0 |
| Greenhouse | 3 | 30 | 3,685 | 371 | 30 | 0 / 0 / 0 / 0 |
| Keka | 1 | 10 | 1,090 | 109 | 20 | 0 / 0 / 0 / 0 |
| SmartRecruiters | 1 | 10 | 2,999 | 319 | 230 | 0 / 0 / 0 / 0 |
| Workable | 1 | 10 | 60 | 6 | 10 | 0 / 0 / 0 / 0 |
| Workday | 1 | 10 | 362 | 201 | 219 | 0 / 0 / 0 / 0 |
| **Total** | **10** | **100** | **16,822** | **1,881** | **539** | **All zero** |

These are cumulative *observations*, not unique jobs. The database contains 1,881 unique job rows and 1,881 notification-ledger rows. Every board's latest outcome is success, every consecutive failure count is zero, all 10 baselines are clear, all 7 host records have no active lease, no HTTP 429 was recorded, no notifications have been sent, no QA users exist yet, and SQLite integrity remains `ok`. Container health returns HTTP 200 and restart count is zero. The most recent run records are spread across the providers at the expected staggered times.

This is extended cadence evidence, but it is still one isolated candidate configuration and not a production load/SLA certification. The Desktop browser/admin/member acceptance is pending.

Use `docs/DESKTOP_QA_PROMPT_2026-11-10.md` for ChatGPT Desktop browser QA. Owner setup uses interactive `v2.auth_admin` commands inside only the candidate container; passwords must not be pasted into chat or saved in repository files.

## Final exact-head CI result — 2026-11-10

- Latest code/docs head before this documentation-only result entry: `e3a9be13abd69b023ea7d2f0703b47f0beeb00a4`.
- GitHub Actions V2 CI **run #1446** (`42753221761`) completed successfully on that exact SHA: https://github.com/AvinashBhalla/job-beeper/actions/runs/42753221761
- The successful job ran Python compilation, dashboard JavaScript syntax, focused router/extractor tests (32), and the full V2 unittest suite (**466 tests in 62.218 seconds, OK**). Do not confuse the focused 32-test subset with the full suite.
- The branch's final documentation-only changes do not modify application code; the code and browser assets tested by #1446 are unchanged.

## 2026-11-10 — Desktop QA evidence follow-up

Read docs/DESKTOP_QA_FOLLOWUP_2026-11-10.md. Anonymous scheduler endpoint now independently returns 401 without a cookie. Original Desktop report provides admin scheduler success, member 403, Source Health absent for members, and member responsive widths without overflow. Admin reload, admin viewport rerun and PNG exports remain outstanding. Revised counts: PASS 11 / FAIL 0 / BLOCKED 5 / UNKNOWN 4. Automation-only QA users 3/4 disabled and temp password file removed; owner QA accounts 1/2 unchanged.


## 2026-11-10 — JobBeeper reference-product research

- Research synthesis: `docs/JOBBEEPER_REVERSE_ENGINEERING_LEARNINGS_2026-11-10.md`.
- Product roadmap update: `d3804df5e9b8cabb966c31bb8c77c393e0d86a8d`; detailed handover update: `7054045f50359aedbc9d56f8b7bd621928a50160`; research synthesis commit: `625140083790294dba34b52079bb567e913e2324`.
- Reference JobBeeper's public UX, visible source labels and a common authenticated browser-facing jobs API are reported as observed. Its private ingestion/discovery/scheduler mechanism is **UNKNOWN**. The authenticated network capture itself is a separate local artifact referenced by the uploaded report and must be inspected in Desktop.
- Our own shared ingestion architecture is already the right base. PR #67 merged bounded company-agnostic discovery (Common Crawl CDX + public careers/sitemap links). It is admin-triggered and review-first; candidate employers/boards are not automatically activated.
- Preserve the invariant: user-level source toggles filter only that user's inventory/matches/alerts; global admin source settings control shared collection. The actual user preference implementation still needs source-code/test verification.
- GitHub code baseline before docs-only updates: `v2-live-radar` `18f219dfab4ad6f2c5ad9b9704da5d3a220f7d37`. PR #69 is merged as `18f219dfab4ad6f2c5ad9b9704da5d3a220f7d37`; older unmerged wording is superseded.
- This turn changed documentation only. No code/tests/deployments/config/database/notification/credential changes; no tests run.
- Next action: Desktop implementation-readiness audit of the exact local checkout plus the separate network-evidence artifact. Verify source registry/discovery flow, board activation, per-user source preference persistence/filtering, schema/provenance/timestamps and test coverage. Return file/line/test evidence; do not implement until reviewed.
