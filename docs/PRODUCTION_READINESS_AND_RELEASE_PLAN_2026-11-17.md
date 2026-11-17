# JobBeeper — production readiness, delivery plan and next-agent handover
**Status date:** 17 November 2026, 15:15 UTC
**Canonical purpose:** This is the current operational source of truth for the existing JobBeeper pipeline and the next production release. Read this before changing the VM, production database, source configuration, Telegram setup, or Company Watch.

## 1. Executive decision

**Priority 1: prove and safely release the complete existing V2 pipeline. Keep Company Watch Phase 2 paused.**

The existing system already collects and stores jobs. The remaining release-critical gap is the personal/member journey: a normal member account, member-owned preferences, a linked private Telegram chat, explicit notification opt-in, per-user match decisions and a real delivery. That path is implemented and has strong automated coverage, but production has not completed a real member-to-Telegram acceptance test.

The release target is:

Naukri / existing ATS sources → V2 collection → database upsert + canonical dedupe → member's saved preferences → member's job evaluations → notification eligibility + no-backlog boundary → member-owned Telegram chat / dashboard

Do not spend the next engineering cycle expanding employer/Company Watch discovery until this path is proven with a real member in QA and then a controlled production canary.

**Production has not been updated in this work.** The live production service remains on the older image job-radar-prod-canary:6e5becb on port 8000. The current V2 QA service is isolated on port 8013.

## 2. Current verified state

### 2.1 Runtime inventory after cleanup

| Component | Current state | Evidence / notes |
|---|---|---|
| Production app | Running, HTTP 200 | v2-radar-1, loopback port 8000, image job-radar-prod-canary:6e5becb; not redeployed |
| Current V2 QA app | Running, HTTP 200 | job-radar-current-v2-qa, loopback port 8013, built from V2 source commit 54fad21; copied production snapshot, independent data directory |
| QA source polling | Disabled | All 11 source flags disabled in QA config; live Naukri collector was invoked explicitly for a controlled test |
| QA legacy notifications | Disabled | notifications_enabled=false; no production bot token, chat ID, Google OAuth credentials, member webhook secret or Telegram webhook configured in QA |
| Docker containers | 2 running | Production + current V2 QA only |
| Docker volumes | 1 remaining | v2_radar-data, production volume; QA uses /var/lib/job-radar-current-v2-qa/data bind mount |
| Docker images | 4 retained | Current QA, current production, explicit production rollback image and Python base image |
| Docker build cache | 0 | Rebuildable cache removed |
| Legacy QA archive | Preserved | /var/backups/job-radar-daily/legacy-qa-environments-20261117.tar.gz, 0600, 44.5 MB compressed, 174 entries, SHA-256 f521107f233408cfbcfd420de68ec0ac0b869b54785d06b95bd21c0fb22f0501 |
| Root disk | 13 GB used / 45 GB, 28% | 33 GB available at 15:10 UTC |
| RAM | 956 MiB total; about 405 MB available | Swap 2 GiB total, about 789 MB used at 15:10 UTC |
| Production health | HTTP 200 | /health, version reports 2.0.0 |
| QA health | HTTP 200 | /health, version reports 2.0.0 |

The VM is still small for simultaneous collection, database work and QA. Disk is no longer the immediate constraint. RAM/CPU headroom is limited; a 4 GiB RAM shape is recommended before increasing ingestion concurrency or running heavy QA beside production. Do not resize the VM without checking provider cost, downtime and a maintenance window.

### 2.2 Cleanup actions completed

All operations below were performed on 17 November 2026. Production was not restarted, redeployed or given a configuration change.

1. Removed unused 3.64 GB Playwright image and unused Node image.
2. Stopped the old Company Watch/global ATS live-test container and source-performance test container; removed their container objects after archiving the relevant data.
3. Found the old dev container on port 8001 in a broken state: Docker reported it running, but it had no usable process table and docker exec failed. Copied its SQLite database to /var/backups/job-radar-daily/development-jobs.sqlite3; verified SQLite integrity ok and 11,584 jobs; only then removed the broken container.
4. Stopped and removed four superseded QA containers (connectors QA, board-scheduler QA, browser QA and user-preferences QA). Archived their persistent data and related QA configs before deleting the old Docker volumes.
5. Stopped three abandoned host-side QA Uvicorn processes that had been listening on ports 8003–8005 for 7–9 days. Their source worktrees were not deleted blindly: the clean LinkedIn-backoff worktree/branch was removed after its service stopped; dirty source-observability and global-ATS worktrees were retained.
6. Removed unused historical Docker image tags from the 5–10 November QA/build cycles. Retained the production image, a named production rollback image, the current QA image and Python base image.
7. Pruned all rebuildable Docker build cache. No production data volume was pruned.
8. Removed eight exited snapshot container objects and the old idle/Phase 2 test container objects. Persistent data was archived before deleting the legacy QA volumes.
9. Reduced Docker inventory from 34 images / about 1.687 GB build cache to 4 images / 0 build cache. Docker now has two running containers and one production volume.
10. Left the current V2 QA app running at port 8013 for release qualification.

**Retained workspaces:** the dirty primary development checkout (/home/ubuntu/job-beeper-dev), dirty global ATS QA checkout (/home/ubuntu/job-beeper-global-ats-test) and dirty source-observability checkout (/tmp/job-radar-source-observability) were preserved. The primary dev checkout still has modified v2/config.json and untracked .env.save, .venv/ and v2/config.json.backup.20261105-183321. Do not reset, clean or overwrite these.

The old LinkedIn-backoff worktree /tmp/job-radar-linkedin-backoff and its local branch were removed only after its Uvicorn service stopped and its worktree was verified clean. Its local branch had been ahead 1 / behind 103 and was not merged into the current V2 release.

### 2.3 Remaining VM disk footprint / ownership review

A final read-only directory-size pass found:
- /var/backups: about 1.4 GB, consisting of retained daily snapshots, pre-release snapshots and recovery archives. Keep these until an offsite backup and restore process has been proven and retention rules are agreed.
- /tmp: about 2.2 GB, mainly named JobBeeper QA/test workspaces, V2 test virtual environments, Naukri relay/JobSpy checks, ATS reference data, performance benchmark databases, preflight DB copies and release-canary backups. These are not active application services. They were retained where their provenance or rollback value was not certain.
- /home/ubuntu: about 657 MB, including the preserved primary and global-ATS worktrees, an archived Git branch bundle, npm cache (about 224 MB) and user cache (about 98 MB).
- The current running container/process inventory did not identify a separate unrelated application using this VM. Standard Ubuntu/Oracle system services and package caches remain; they are not project containers.
- There are still removable candidates inside /tmp (old benchmark copies and disposable virtual environments), but they were not deleted in this pass. Before removing them, confirm no active Termalin job/worktree uses them and archive any unique result needed for a future regression comparison.

The root disk is now 28% used, so there is no immediate need to take further deletion risk. The remaining data is documented rather than blindly labelled junk.

### 2.4 Backup job repaired

The daily SQLite snapshot script previously failed after successfully snapshotting production because it also tried to docker exec into the broken development container.

The script was backed up to:
 /var/backups/job-radar-daily/job-radar-sqlite-snapshot.sh.before-optional-dev-20261117

It was changed so:
- production snapshot is mandatory;
- development snapshot is optional and attempted only when the dev container exists, is running and supports docker exec;
- an unavailable development target is logged as skipped instead of failing the production backup.

The systemd snapshot service was manually run on 17 November and completed successfully (exit 0). The production snapshot passed PRAGMA integrity_check (ok) and reported 27,371 jobs. The development recovery snapshot was separately verified (ok). The production service itself was not restarted.

**Remaining backup gate:** these are same-VM backups. Configure an encrypted offsite backup and complete a restore drill before production promotion. Retain the current known-good production rollback image/config until the release is accepted.

## 3. Pipeline findings

### 3.1 Production database / member account audit

A read-only snapshot of production was opened and inspected. Production contains:
- exactly one active user, with the admin role;
- one admin preferences record;
- zero normal/member accounts;
- zero linked member Telegram private chats;
- zero per-user notification settings;
- zero per-user notification-ledger rows;
- 27,371 user-job evaluation rows for the admin profile in the snapshot.

The admin's copied preference profile had 1,977 matching evaluations in the snapshot before the isolated QA Naukri test added two new jobs. These rows are admin evaluations, not evidence of a member's end-to-end alert delivery.

The owner currently has admin credentials only. The database confirms that a member account has **not** been created in production, so this is not merely a forgotten password.

Production account setup:
- Google sign-in reports disabled.
- There is no public email/password signup route.
- The repository has an admin provisioning CLI (v2.auth_admin) that can create a normal user account and initialize its own empty preferences.
- A new member must complete their own preferences. New members must not inherit the admin's candidate profile.
- Do not convert the existing admin account into a member or alter its role to bypass the design.

**Owner input needed at the real-account step:** the email address to use for the member account. Do not invent an address or expose a temporary password in chat/logs. The member account can be provisioned when the owner provides the intended email and a secure credential-delivery method is selected.

### 3.2 Telegram setup finding

The existing production bot token passed the Telegram identity check. The production bot does not currently have a webhook configured.

The production environment is missing the per-user linking configuration:
- JOB_BEEPER_TELEGRAM_BOT_USERNAME
- JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET

The app also needs its correct public HTTPS origin and a webhook URL routed to the production endpoint. Configure secrets through the approved environment/secret store, not source control or handover docs. Do not paste token/secret values into chat or logs.

The legacy global Telegram sender is separate from the member sender. The admin dashboard's legacy “alerts sent” count must not be presented as proof that member Telegram delivery works.

### 3.3 Existing source-health evidence (production DB, latest 24-hour window available in the 14:37 UTC snapshot)

| Source | Runs | Requests | HTTP 429 | Page failures | Jobs seen | New jobs | Assessment |
|---|---:|---:|---:|---:|---:|---:|---|
| Naukri | 285 | 285 | 0 | 2 | 84,358 | 307 | Active; relay-backed |
| Greenhouse | 286 | 858 | 0 | 0 | 99,488 | 7 | Healthy in sampled window |
| Ashby | 285 | 570 | 0 | 0 | 241,245 | 20 | Healthy in sampled window |
| SmartRecruiters | 286 | 6,578 | 0 | 0 | 85,784 | 128 | Healthy in sampled window |
| Keka | 704 | 1,408 | 0 | 0 | 75,907 | 11 | Healthy in sampled window |
| Darwinbox | 708 | 708 | 0 | 0 | 26,764 | 3 | Healthy in sampled window |
| Workable | 707 | 707 | 0 | 0 | 4,242 | 0 | No new jobs in sampled window |
| Workday | 285 | 355 | 284 | 243 | 28 | 17 | Severe repeated 429 rate limiting |
| LinkedIn | 15 | 90 | 6 | 3 | 232 | 129 | Partial; rate-limited |

The most urgent reliability issue is Workday. It was making a request about every five minutes despite repeated 429 responses: 284 of 355 requests were 429s, with 243 failed pages out of 285 runs. It still found 17 jobs, so the source should not be globally disabled without a deliberate product decision.

### 3.4 Workday rate-limit fix prepared and tested

A change is prepared on local branch:
fix/ats-board-rate-limit-backoff-20261117

It changes the persistent ATS board scheduler so consecutive rate-limited outcomes progressively increase per-board/per-host cooldown:
- first 429: 5 minutes;
- second consecutive 429: 10 minutes;
- third: 20 minutes;
- fourth: 40 minutes;
- fifth and later: 60-minute cap.

A longer server-provided Retry-After is still honoured. A successful poll resets the consecutive failure count. Host-level isolation remains: one Workday tenant's cooldown must not pause another tenant on another host or unrelated ATS providers.

The focused board scheduler suite passed 12/12 tests. The full V2 suite on the modified source passed **497 tests, 0 failures** in 561.372 seconds. git diff --check passed.

**Release qualification still required:** commit the patch, push the branch, open a PR against v2-live-radar, wait for exact-head GitHub CI, review the diff, rebuild QA from the merged/release candidate and verify its runtime image includes the change. Do not deploy this uncommitted branch directly to production.

## 4. Work actually proven in the current V2 QA service

QA image:
job-radar-v2-qa:54fad21

QA container:
job-radar-current-v2-qa, loopback port 8013.

QA data:
 /var/lib/job-radar-current-v2-qa/data/jobs.db

It uses a copied production snapshot, but has separate writable data. All source flags and legacy notifications are disabled, and no production Telegram or Google OAuth credentials are present.

### 4.1 V2 service startup

- Container built from clean V2 source commit 54fad21.
- Startup database migration/reconciliation completed.
- /health returned HTTP 200.
- Snapshot database was 121,241,600 bytes and contained 27,371 jobs at the copy point.
- Existing admin user/preferences are in the copied QA snapshot only; production was not modified by QA tests.

### 4.2 Live Naukri relay → V2 ingest → dedupe

The V2 collector run_source("naukri") was invoked explicitly inside the QA application against the live Naukri relay:
- the relay snapshot contained 312 jobs and was about 135 seconds old;
- first pass: 312 seen, 2 new jobs inserted, successful source run;
- second pass: 312 seen, 0 new jobs inserted, successful source run;
- the second pass stored the same content fingerprint as unchanged;
- no Telegram notification was sent; QA legacy notifications remained disabled.

This proves the relay-to-V2 collector, normalization/upsert, evaluation and repeat-poll dedupe path against this live sample. It is not yet proof of continuous production polling on the new image or member Telegram delivery.

### 4.3 Per-user pipeline automated tests

The focused user-preferences, per-user notification, Telegram-linking and user-preferences API suites passed **61/61 tests**. Coverage includes:
- user preferences are separate per account; new members do not inherit admin preferences;
- incomplete member onboarding blocks the personal jobs feed;
- each member has independent job evaluations;
- notification defaults are off and enabling notifications requires a linked private chat;
- no historical backlog is sent after opt-in;
- queued notifications are revalidated against current preferences and opt-in;
- notification queue idempotency and canonical-opportunity dedupe;
- each user is sent only their own matching jobs and only to their own linked chat;
- private-chat-only linking, token expiry/replay checks and disconnect behaviour;
- Telegram webhook secret protection and mocked success/retry/failure handling.

These tests mock Telegram where appropriate. They do not constitute a real bot-to-owner-device delivery.

### 4.4 Full V2 suite

The full V2 unittest discovery run on the Workday-backoff working tree passed:
**497 tests, 0 failures**, exit code 0.

This is local VM test evidence. The branch-specific patch still needs a GitHub PR and exact-head CI run, then a QA image rebuilt from the reviewed release commit.

## 5. Production blockers and pre-release acceptance gates

Do not mark the release ready until all P0 gates are met.

### P0 — Must complete before production rollout

1. **Workday rate-limit fix:** commit and PR the adaptive backoff change; exact-head GitHub CI green; release image built from the approved commit; test Workday host cooldown and ensure healthy providers remain unaffected.
2. **Member account:** provision one normal user account for the owner using the intended email; sign in; complete role/location/preferences. Do not reuse the admin role.
3. **Telegram member linking:** provide the per-user bot username and webhook secret via secret management; configure the production HTTPS webhook; verify Telegram reports the correct webhook endpoint and no persistent delivery errors.
4. **Real personal matching:** with the member's saved preferences, verify existing Naukri/ATS listings produce the expected member-specific match results. Check both positive and negative samples; admin/global matching is not a substitute.
5. **Real Telegram canary:** link the member's private Telegram chat, explicitly enable notifications, verify the enabled_at no-backlog boundary, then observe one genuinely new matching job. Confirm the user-scoped ledger records the correct user, canonical opportunity, chat ownership and successful Telegram ok=true response. Repeat polling must not send the same opportunity twice.
6. **Backup/restore:** keep the repaired local daily production snapshot; configure encrypted offsite backup; run and record a restore drill against an isolated database.
7. **Exact production candidate:** build from the reviewed release commit; capture image digest, Git commit, effective non-secret config summary, database migration plan and rollback image; compare to the tested QA release candidate.
8. **Owner approval:** production deployment is a separate release decision. No production deployment has been performed in this work.

### P1 — Complete before broader rollout / within first monitored window

- Monitor Naukri, Greenhouse, Ashby, SmartRecruiters, Keka, Darwinbox and Workable over 24–72 hours after the candidate release.
- Monitor Workday cooldown, success rate and unique new jobs after the adaptive backoff.
- Review LinkedIn 429/partial failures; keep request volume conservative.
- Verify job detail completeness, application URLs, experience parsing and canonical dedupe.
- Confirm per-user dashboard counters reflect the per-user ledger, not the legacy/global ledger.
- Right-size VM to 4 GiB RAM if metrics continue to show pressure; run only production + one QA service on this VM.
- Add an alert for stale source snapshots, sustained 429s, failed backups and notification delivery failures.

### P2 — After existing pipeline is stable

- Resume Company Watch Phase 2 only after the existing member pipeline has passed real acceptance.
- Import the pinned 100-row manifest into an isolated QA database.
- Review/resolve canonical employer identities; do not infer identity from slugs.
- Verify only the small owner-reviewed sample. The manifest labels are research hints, not live approval.
- Ensure only explicit approved boards are configured before activation; the current provider-level source flag can otherwise activate every board in that provider's configured allowlist.
- First board poll must be a silent baseline; second poll must prove new unique ingestion.
- Then progress to JD completeness, quality audit and only later a Company Watch alert pilot. Keep its phases separate; do not compress them into one deployment.

## 6. Fastest safe delivery sequence

This is the shortest critical path. Work can proceed in parallel where noted, but do not skip release gates.

| Order | Workstream | Owner | Exit condition | Planning estimate |
|---|---|---|---|---:|
| 1 | Commit Workday backoff change, push branch, PR, exact-head CI | Engineering | Green CI and reviewed patch | 1–2 hours |
| 2 | Rebuild current V2 QA image from that exact commit; re-run source/member smoke checks | Engineering | QA image digest and evidence attached to handover | 2–3 hours |
| 3 | Provision owner member account | Owner + engineering | Member can log in and has completed preferences | 30–60 minutes after email is supplied |
| 4 | Configure per-user Telegram webhook and link private chat | Owner + engineering | Telegram link status connected; webhook secret validated | 1–2 hours if bot/domain access is ready |
| 5 | Real member match + Telegram canary; re-poll idempotency test | Engineering + owner | One expected alert delivered and duplicate prevented | 1–2 hours plus wait for a genuinely new matching job |
| 6 | Offsite backup/restore drill; candidate manifest and rollback verification | Engineering | Restore evidence and rollback runbook | 2–4 hours |
| 7 | Explicit owner-approved production rollout | Owner authorizes; engineering executes | Health checks pass, monitored first cohort | 1–2 hours plus 24–72 hours observation |

**Estimate from the current state:** approximately **8–14 focused engineering hours** to reach a controlled production canary, assuming the member email, bot ownership, webhook/domain configuration and production access are available without delay. In calendar terms, plan for **1–2 days of focused day/night work** to reach the first production canary, then **another 24–72 hours of monitoring** before calling the rollout stable.

This is not a promise that everything will be live in 8 hours. The main external dependencies are a real member identity, Telegram private-chat linking/webhook setup, GitHub CI, an offsite backup/restore route and explicit production approval. If any one of these is unavailable, the schedule moves by the dependency delay.

Company Watch Phase 2 is a separate follow-on and is not included in this estimate. Forcing it into the same overnight release would increase risk without helping prove the existing member pipeline.

## 7. Owner inputs required — only when the relevant step is reached

1. The email address you want to use for your normal member account. Production currently has admin only; no member record exists.
2. Access to the Telegram bot owner account and confirmation that the existing bot should be used for member notifications. Do not send the bot token in chat.
3. Explicit approval at the production deployment gate after QA acceptance and backup/restore evidence are available.

No other owner input is required for the code, QA rebuild, source health work or documentation steps.

## 8. Next-agent checklist — continue from here

1. Read this document first. Treat older timestamps/claims in REPOSITORY_CLEANUP_AND_VM_HEALTH_2026-11-17.md, NEXT_AGENT_START_HERE.md, JOB_RADAR_HANDOVER.md and JOB_RADAR_KNOWLEDGE_TRANSFER.md as historical where they conflict with this current state.
2. Inspect git status, git log, and the current PR/CI before touching the branch. Worktree: /tmp/job-beeper-perf-v2. Branch: fix/ats-board-rate-limit-backoff-20261117. The Workday backoff code and test are currently modified/uncommitted at the time this document was drafted; do not assume they are already on GitHub.
3. Run git diff --check; review the patch in v2/board_scheduler.py and v2/test_board_scheduler.py; commit it; push; open PR against v2-live-radar; wait for exact-head CI.
4. Rebuild job-radar-current-v2-qa from the reviewed commit. Keep QA source polling and notifications disabled by default. Keep the production bot token and Google OAuth credentials out of QA.
5. Complete the member provisioning and real Telegram linking gates once the owner supplies the member email and bot access.
6. Attach QA test outputs, source-run evidence, Telegram canary ledger evidence, image digest and backup/restore evidence to this handover.
7. Deploy only after the owner explicitly approves the release. Preserve job-radar-production-rollback:20261108 until the new release passes its monitoring window.
8. Do not resume Company Watch Phase 2 until the existing member path passes.

### Paths and retained evidence

- Repository/worktree: /tmp/job-beeper-perf-v2
- Current QA service: container job-radar-current-v2-qa, 127.0.0.1:8013
- Production service: container v2-radar-1, 127.0.0.1:8000
- QA database: /var/lib/job-radar-current-v2-qa/data/jobs.db
- Production backup: /var/backups/job-radar-daily/production-jobs.sqlite3
- Broken development DB recovery copy: /var/backups/job-radar-daily/development-jobs.sqlite3
- Legacy QA archive: /var/backups/job-radar-daily/legacy-qa-environments-20261117.tar.gz
- Snapshot script pre-edit copy: /var/backups/job-radar-daily/job-radar-sqlite-snapshot.sh.before-optional-dev-20261117
- Current rollback image: job-radar-production-rollback:20261108

---

## Change log

### 2026-11-17 — current execution update
- Completed privileged VM/Docker inventory and identified legacy QA containers, unused images, temporary QA runtimes and Docker build cache.
- Backed up and verified the broken development database before removing its unusable container.
- Archived old QA data/configs before removing old QA volumes and containers.
- Retired old host-side QA listeners and the clean, unused LinkedIn-backoff worktree; retained dirty development and QA worktrees.
- Repaired the daily snapshot service's optional development-target handling and verified a successful production snapshot.
- Built and started current V2 QA from 54fad21; verified health and a two-pass live Naukri relay ingest/dedupe test.
- Ran 61 focused per-user/auth/Telegram tests and the 497-test full V2 suite successfully.
- Prepared an adaptive Workday per-host 429 backoff change. The full test suite passes, but the patch is not yet committed, pushed or deployed.
- Production remained on its existing image and was not restarted or changed.
