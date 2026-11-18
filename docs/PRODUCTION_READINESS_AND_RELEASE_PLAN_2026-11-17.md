# JobBeeper — production readiness, delivery plan and next-agent handover

## Latest execution update — 18 November 2026, production promoted

Production is now running `job-radar-prod-release:472c2ee` (image ID `sha256:55d2de9446b72cb8d3a9f72627bda9a003750acceef7635a609dd0818c08985c`). Container health, dashboard and OpenAPI are HTTP 200. The persistent scheduler synchronized exactly 10 active schedules matching the existing 10 active registry boards. Initial pass succeeded for nine boards; Workday returned 429 and received a persisted five-minute host cooldown. Continue observing the cooldown and confirm escalation on another 429.

The 100-row Company Watch manifest is now imported persistently as review-only data: 19 candidates staged with `discovered` status, 81 manual-review rows, zero company records created, zero boards linked/verified/activated/scheduled, zero network requests and zero notifications. The existing registry and scheduler remain at 10 boards. Naukri relay workflow #9874 succeeded and post-deploy ingestion accepted 313 jobs with zero new rows / zero page failures. SmartRecruiters cache warm-up is incremental; first production poll reused 20 details and fetched 20 additional details, while a seeded warm-cache QA check reached 3 listing requests and zero detail requests.

Final pre-deploy backup: `/var/backups/job-radar-daily/production-before-v2-release-20261118T2058Z.sqlite3`, 135,368,704 bytes, mode 0600, integrity ok; 27,546 jobs, 2 users, 10 ATS boards and 51,984 source runs; SHA-256 `6c8fa1f139ea05a081c0f65fefc84540f9d9600febe59f57b71b3a1a0bd9da15`. The previous production image and rollback image remain available. The release is deployed, but reliability acceptance remains pending at least 24 hours of source telemetry and Workday cooldown verification.

First post-release Workday retries at 21:01:26, 21:06:34 and 21:16:37 UTC each received 429; persisted cooldown escalated 5 → 10 → 20 minutes with no early retry. Next due is `2026-11-17T21:36:38.680292+00:00`. Other hosts continued polling. SmartRecruiters cache hits grew 20 → 40 → 60 over three production polls; candidate warm-cache QA reached 300 hits / 0 details / 3 listing calls. Naukri relay #9878 succeeded; V2 ingestion accepted 317 jobs with no failures. The 100-row manifest is imported review-only (19 staged, 81 manual); 0 companies/boards were created or activated. Continue 24-hour observation before full reliability acceptance.

---

## Latest execution update — 17 November 2026, 18:30 UTC

This is the current source of truth. The earlier 17:18 status and 15:15 rollout table are superseded by docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md.

- PR #77 merged as 5b80499 and PR #78 merged as 3d05733. Workday adaptive cooldown code is in v2-live-radar, but it is not in the production runtime yet.
- Production image job-radar-prod-canary:6e5becb (created 8 Nov) has no v2.board_scheduler module and no ats_board_poll_schedule table. Candidate QA image job-radar-v2-qa:cc2087e (created 17 Nov) contains the new persistent per-board scheduler.
- Production 24-hour source baseline ending about 18:11 UTC: Workday 627 runs / 4,894 requests / 417 HTTP 429 / 362 failed pages / 33 new rows; LinkedIn 267 / 1,566 / 12 / 4 / 449; Naukri 503 / 503 / 0 / 2 / 706. SmartRecruiters made 11,592 requests in 504 successful runs and added 251 rows. Other five ATS sources were free of HTTP 429s in this window. See FETCHER_AND_FEED_RELIABILITY_PLAN for the full table and next investigations.
- Production has 10 active allowlisted ATS boards: Greenhouse 3, Ashby 2, Workday 1, SmartRecruiters 1, Workable 1, Keka 1 and Darwinbox 1. LinkedIn and Naukri are enabled global fetchers; Instahyre and Lever are disabled.
- Member account avi.bhalla2004@gmail.com now exists (user id 2, role user). Its saved Software Developer / India preferences currently have Remote only false and generated 1,052 matching evaluations. Telegram is not linked; that does not block dashboard, job collection, matching or feed usage.
- Pending code branch: fix/member-remote-only-global-20261117. It allows role + Remote only with no target location (explicitly remote worldwide), uses structured ATS workplace metadata, excludes hybrid/on-site, and hides the otherwise-empty Intelligence group from members. The current member preference is not changed by this code.
- Full local V2 regression suite on this branch: 504 tests passed, 0 failures (496.103 seconds). Python compilation, git diff --check and focused new tests passed. The VM's system Node is v12.22.9 and cannot parse existing optional chaining; rely on GitHub CI's Node syntax check for dashboard JavaScript rather than treating the local Node 12 error as an application error.
- Disposable QA scheduler simulation used the existing 10-board config and production poll intervals: sync created exactly 10 schedule rows; Workday's first simulated 429 persisted a 5-minute host cooldown, second persisted a 10-minute cooldown, and a different-host Ashby board remained claimable during the Workday cooldown. The test used a temporary SQLite DB and made no upstream Workday request. A scheduled-dispatch integration smoke then claimed one existing Coinbase Greenhouse board twice through the real scheduler dispatch path: first poll inserted 260 jobs and silently suppressed all 260 as the initial inventory baseline; second poll observed 260 and inserted 0. Both runs succeeded (1/1 board, 0 failures), no duplicate source IDs existed, and SQLite integrity was ok. The host minimum interval was respected. Notifications were disabled and no Telegram send occurred. Both tests used temporary SQLite DBs; the shared QA config remains unchanged with all source flags false and notifications false.
- Fresh production DB snapshot for the upcoming scheduler canary is saved at /var/backups/job-radar-daily/production-before-scheduler-canary-20261117.sqlite3; 129 MB, mode 0600, SQLite integrity ok, 27,497 jobs, 2 users, 10 active ATS boards. SHA-256: 8593c7fa32757635a0ee27624ec8c957c584163d13f5271976ac0f25fa684cf1.
- The candidate image's additive V2 DB initialization was applied to a disposable copy of that production snapshot. Existing job/user counts and 10 active registry boards were preserved; the scheduler table was created and synced to exactly 10 rows whose active board keys matched the production allowlist. The copy passed SQLite integrity. Temporary files were removed. No production database was migrated.
- Production and QA containers remain running; last health checks returned HTTP 200. No production container, DB, source flag, Telegram setting or Nginx config was changed.
- Telegram is optional. It is not required to log in, save preferences, collect jobs, evaluate matches or use the dashboard. It is used only when a user chooses Telegram as an alert channel and opts in. Do not gate fetcher/feed reliability work on Telegram linking, webhook setup or a per-user notification canary.

## Active priority and next steps

1. Complete review of the Remote only and member Intelligence-navigation fixes on the current branch; keep the member's saved Remote only setting unchanged.
2. Open a PR against v2-live-radar and require exact-head GitHub CI, including dashboard JS syntax and the full V2 suite.
3. In isolated QA, prove the production 10-board allowlist and board-scheduler dispatch path, including one controlled board poll, second-poll idempotency, silent first baseline, board/host isolation and Workday cooldown persistence. Keep the shared QA instance's sources disabled; use a throwaway DB/config.
4. Investigate Workday's repeated 429s, SmartRecruiters request volume and Naukri's failed pages. Preserve source allowlists and request budgets.
5. Rebuild a release candidate from the reviewed commit; verify additive migration, pre-release production backup, image digest and rollback. Deploy only after exact-head CI, QA evidence and explicit owner approval.

Member-only enhancements, Telegram and Company Watch expansion are later work. The core feed can and should be used without Telegram.

---

**Status date:** 17 November 2026, 15:15 UTC
**Canonical purpose:** This is the current operational source of truth for the existing JobBeeper pipeline and the next production release. Read this before changing the VM, production database, source configuration, Telegram setup, or Company Watch.

## 1. Executive decision

**Priority 1: stabilize the existing fetchers and job feed. Keep member-only enhancements, Telegram delivery and Company Watch expansion out of this increment.**

The immediate product requirement is dependable source polling, low avoidable rate limiting, complete pagination, truthful source health, stable normalization, canonical deduplication, relevant matching and a fresh dashboard feed. The production source baseline shows Workday is the principal reliability issue, followed by smaller LinkedIn and Naukri issues; SmartRecruiters request efficiency also needs investigation.

The core feed path is:

Naukri / LinkedIn / approved ATS boards → source-specific collectors and scheduler → normalized job records → idempotent upsert + canonical dedupe → match evaluation → dashboard feed

Telegram is optional. It is not required for login, preferences, job collection, matching or dashboard access. It is used only when a user chooses Telegram as an alert channel and opts in. Do not gate the fetcher/feed release on Telegram setup or personal notification delivery.

Do not expand Company Watch or member-only features until the existing collectors, board scheduler, freshness metrics and dashboard feed meet the reliability criteria in docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md.

**Production has not been updated in this work.** The live production service remains on the older image job-radar-prod-canary:6e5becb on port 8000. The current V2 QA service is isolated on port 8013.

## 2. Current verified state

### 2.1 Runtime inventory after cleanup

| Component | Current state | Evidence / notes |
|---|---|---|
| Production app | Running, HTTP 200 | v2-radar-1, loopback port 8000, image job-radar-prod-canary:6e5becb; not redeployed |
| Current V2 QA app | Running, HTTP 200 | job-radar-current-v2-qa, loopback port 8013, image job-radar-v2-qa:cc2087e from PR #77 source commit cc2087e; independent QA data directory |
| QA source polling | Disabled | All 12 source flags disabled in QA config; live Naukri collector was invoked explicitly for a controlled test |
| QA legacy notifications | Disabled | notifications_enabled=false; no production bot token, chat ID, Google OAuth credentials, member webhook secret or Telegram webhook configured in QA |
| Docker containers | 2 running | Production + current V2 QA only |
| Docker volumes | 1 remaining | v2_radar-data, production volume; QA uses /var/lib/job-radar-current-v2-qa/data bind mount |
| Docker images | 5 retained | Current QA candidate, prior QA image retained for quick QA rollback, current production, explicit production rollback image and Python base image |
| Docker build cache | 0 | Rebuildable cache removed again after the cc2087e image build |
| Legacy QA archive | Preserved | /var/backups/job-radar-daily/legacy-qa-environments-20261117.tar.gz, 0600, 44.5 MB compressed, 174 entries, SHA-256 f521107f233408cfbcfd420de68ec0ac0b869b54785d06b95bd21c0fb22f0501 |
| Root disk | 13 GB used / 45 GB, 28% | 33 GB available at 15:10 UTC |
| RAM | 956 MiB total; about 407 MB available | Swap 2 GiB total, about 807 MB used at 17:06 UTC |
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
9. Reduced Docker inventory from 34 images / about 1.687 GB build cache to a final 5 retained images / 0 build cache after the PR candidate QA image was built. Docker now has two running containers and one production volume.
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

### 3.4 Workday rate-limit fix — merged and validated

The change was developed on branch fix/ats-board-rate-limit-backoff-20261117 and merged into v2-live-radar in PR #77 as commit 5b80499.

It changes the persistent ATS board scheduler so consecutive rate-limited outcomes progressively increase per-board/per-host cooldown:
- first 429: 5 minutes;
- second consecutive 429: 10 minutes;
- third: 20 minutes;
- fourth: 40 minutes;
- fifth and later: 60-minute cap.

A longer server-provided Retry-After is still honoured. A successful poll resets the consecutive failure count. Host-level isolation remains: one Workday tenant's cooldown must not pause another tenant on another host or unrelated ATS providers.

The focused board scheduler suite passed 12/12 tests. The full V2 suite passed 497 tests, 0 failures locally, on PR exact-head CI #1512 and post-merge CI #1513. The candidate QA image was rebuilt from the merged application tree. The new QA container is healthy on port 8013; its in-container board-scheduler suite passes 12/12.

The change is now part of v2-live-radar, but it is not active in production until a separately approved production image is deployed. Production remains on image 6e5becb.

## 4. Work actually proven in the current V2 QA service

QA image:
job-radar-v2-qa:cc2087e

QA container:
job-radar-current-v2-qa, loopback port 8013.

QA data:
 /var/lib/job-radar-current-v2-qa/data/jobs.db

It uses a copied production snapshot, but has separate writable data. All source flags and legacy notifications are disabled, and no production Telegram or Google OAuth credentials are present.

### 4.1 V2 service startup

- Container built from PR #77 application source commit cc2087e (docs-only follow-up commit does not change the container build context).
- Startup database migration/reconciliation completed.
- /health returns HTTP 200 after the candidate swap.
- QA database contains 27,373 jobs after the two controlled Naukri test insertions; SQLite integrity_check returns ok.
- The QA copy contains one copied admin and its preferences/evaluations only; it contains zero member-linked Telegram chats, zero per-user notification settings and zero per-user notification ledger rows. Production was not modified by QA tests.

### 4.2 Live Naukri relay → V2 ingest → dedupe

The V2 collector run_source("naukri") was invoked explicitly inside the QA application against the live Naukri relay:
- the relay snapshot contained 312 jobs and was about 135 seconds old;
- first pass: 312 seen, 2 new jobs inserted, successful source run;
- second pass: 312 seen, 0 new jobs inserted, successful source run;
- the second pass stored the same content fingerprint as unchanged;
- no Telegram notification was sent; QA legacy notifications remained disabled.

This proves the relay-to-V2 collector, normalization/upsert, evaluation and repeat-poll dedupe path against this live sample. It is not yet proof of continuous production polling on the new image or member Telegram delivery.

The same candidate image was also tested manually with Greenhouse and Ashby collectors against the isolated QA database. Greenhouse returned 346 listings from 3/3 successful boards (2 inserted first pass, 0 on repeat); Ashby returned 848 listings from 2/2 successful boards (4 inserted first pass, 0 on repeat). All source flags remained off, notifications remained off, and there were no Telegram deliveries. These are controlled manual collector invocations, not scheduler enablement.

After the three-source smoke, the QA database contains 27,379 jobs and passes SQLite integrity_check. A fresh QA snapshot is saved at /var/backups/job-radar-daily/qa-after-ats-smoke-20261117.sqlite3 (SHA-256 8d14fa852b7e53ec795b6811273b171c49684602acc2da42c40a54d3994cf884).

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

Exact-head GitHub Actions run #1512 on PR #77 passed all 497 tests (63.506 seconds); post-merge run #1513 also passed all 497 tests (64.807 seconds) on merge commit 5b80499. The candidate image was built from the same application tree as the merged branch and health-checked after the isolated QA container swap. PR #77 is merged; the merge does not deploy to production.

## 5. Production blockers and pre-release acceptance gates

Do not mark the release ready until all P0 gates are met.

### P0 — Must complete before production rollout

1. **Workday rate-limit fix:** completed. PR #77 merged as 5b80499; post-merge CI #1513 passed 497 tests; candidate QA image passes the 12-test scheduler suite. The merged code is not in production yet.
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

## 6. Historical member/Telegram rollout sequence (superseded 18:24 UTC by fetcher-first plan)

This is the shortest critical path. Work can proceed in parallel where noted, but do not skip release gates.

| Order | Workstream | Owner | Exit condition | Status / planning estimate |
|---|---|---|---|---:|
| 1 | Workday backoff code, PR and exact-head/post-merge CI | Engineering | Merged as 5b80499; CI #1512/#1513 green, 497 tests each | Complete |
| 2 | Candidate V2 QA image and isolated runtime validation | Engineering | Image cc2087e healthy on 8013; 12 scheduler tests pass; sources/notifications off | Complete |
| 3 | Provision owner member account | Owner + engineering | Member can log in and has completed preferences | 30–60 minutes after email is supplied |
| 4 | Configure per-user Telegram webhook and link private chat | Owner + engineering | Telegram link status connected; webhook secret validated | 1–2 hours if bot/domain access is ready |
| 5 | Real member match + Telegram canary; re-poll idempotency test | Engineering + owner | One expected alert delivered and duplicate prevented | 1–2 hours plus wait for a genuinely new matching job |
| 6 | Encrypted offsite backup/restore drill; production candidate and rollback verification | Engineering | Restore evidence and rollback runbook | 2–4 hours |
| 7 | Explicit owner-approved production rollout | Owner authorizes; engineering executes | Reviewed image deployed; health checks pass; monitored first cohort | 1–2 hours plus 24–72 hours observation |

**Historical estimate, superseded:** the earlier 6–10-hour member/Telegram canary estimate is not the current delivery target. The active work is fetcher/feed reliability; estimate the production scheduler rollout after QA integration and GitHub CI complete. In calendar terms, plan for **1–2 days of focused day/night work** to reach the first production canary, then **another 24–72 hours of monitoring** before calling the rollout stable.

This is not a promise that everything will be live in 8 hours. The main external dependencies are a real member identity, Telegram private-chat linking/webhook setup, GitHub CI, an offsite backup/restore route and explicit production approval. If any one of these is unavailable, the schedule moves by the dependency delay.

Company Watch Phase 2 is a separate follow-on and is not included in this estimate. Forcing it into the same overnight release would increase risk without helping prove the existing member pipeline.

## 7. Owner input

No owner input is required for the current fetcher diagnostics, QA scheduler verification, code changes or documentation. A separate explicit owner approval will still be required before any production container/image update.

Telegram bot access is needed only if/when you later decide to enable Telegram as an optional notification channel. It is not required for the feed reliability work.

## 8. Next-agent checklist — continue from here

1. Read docs/FETCHER_AND_FEED_RELIABILITY_PLAN_2026-11-17.md first; it is the active priority and supersedes the earlier member/Telegram canary sequence.
2. Inspect the current production/QA images and confirm the production scheduler gap. Do not change production containers or source flags during QA work.
3. Finish tests for the Remote only and member Intelligence navigation fixes on branch fix/member-remote-only-global-20261117. Do not change the user's saved Remote only setting.
4. In a separate disposable QA database/config, enable only the existing 10-board allowlist and prove board_scheduler.sync_config creates the expected due rows. Test host leases, board failure isolation and Workday 429 cooldown without repeatedly hitting the throttled upstream.
5. Investigate SmartRecruiters request volume and Naukri failed-page details. Preserve source request budgets and existing active allowlists.
6. Open a PR against v2-live-radar, require exact-head CI, rebuild candidate QA and record source/scheduler results. No Telegram link, webhook or member notification canary is required for this workstream.
7. Before any production rollout, take and verify a DB backup, confirm additive migration and rollback image, then obtain explicit owner approval.
8. Do not resume Company Watch expansion or broader member-only work until the existing feed reliability criteria are met.
### Paths and retained evidence

- Repository/worktree: /tmp/job-beeper-perf-v2
- Current QA service: container job-radar-current-v2-qa, image job-radar-v2-qa:cc2087e, 127.0.0.1:8013
- Production service: container v2-radar-1, 127.0.0.1:8000
- QA database: /var/lib/job-radar-current-v2-qa/data/jobs.db
- Production backup: /var/backups/job-radar-daily/production-jobs.sqlite3
- Broken development DB recovery copy: /var/backups/job-radar-daily/development-jobs.sqlite3
- Legacy QA archive: /var/backups/job-radar-daily/legacy-qa-environments-20261117.tar.gz
- Snapshot script pre-edit copy: /var/backups/job-radar-daily/job-radar-sqlite-snapshot.sh.before-optional-dev-20261117
- Current rollback image: job-radar-production-rollback:20261108
- QA pre-candidate backup: /var/backups/job-radar-daily/qa-before-cc2087e.sqlite3

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
- Prepared the adaptive Workday per-host 429 backoff change; later committed it in PR #77. See the latest execution update above for exact-head CI and QA candidate results.
- Production remained on its existing image and was not restarted or changed.

### 2026-11-17 17:06 UTC — PR/CI and candidate QA update
- PR #77 opened against v2-live-radar with Workday adaptive backoff and the updated release plan.
- Exact-head GitHub CI #1511 passed 497 tests in 76.049s; full workflow conclusion success.
- Candidate image job-radar-v2-qa:cc2087e built from application source cc2087e. The isolated QA container was replaced on port 8013 and /health returned HTTP 200.
- Candidate QA configuration has all 12 source flags disabled and notifications disabled. SQLite integrity is ok; 27,373 jobs, one copied admin and zero member Telegram chat/per-user notification rows. Scheduler tests inside the candidate container passed 12/12.
- QA pre-swap database backup verified at /var/backups/job-radar-daily/qa-before-cc2087e.sqlite3 (SHA-256 recorded above). Production container remains unchanged on image 6e5becb and returns HTTP 200.
- Build cache was pruned again after image export. Final Docker inventory: two running containers, one production volume, five retained images (including prior QA rollback tag) and zero build cache.
- PR #77 remains open at this checkpoint. Next: green CI for this docs-only follow-up, merge PR #77, then provision the real member and configure Telegram canary. No production deployment.

### 2026-11-17 17:11 UTC — PR #77 merge and post-merge verification
- PR #77 merged into v2-live-radar as 5b80499d42046cbadc7570171944346d9bf57fb9.
- Exact post-merge GitHub Actions run #1513 passed 497 V2 tests in 64.807s; focused router/extractor tests passed 32/32.
- Confirmed the merged branch tree hash is identical to the PR-head tree used for the candidate QA image.
- Production is still on 6e5becb; no production image, environment, database, Telegram or Nginx changes were made.


## 18 November 2026 — morning production observation (03:50 UTC)

Observation window: production deployment at `2026-11-17T20:59:46Z` through `2026-11-18T03:50:39Z` (about 6h51m). This is an early post-release window, not a completed 24-hour acceptance period.

### Live source metrics since deployment

| Source | Runs | Requests | HTTP 429 | Failed pages | Jobs seen | New rows |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 159 | 159 | 0 | 0 | 66,865 | 5 |
| Darwinbox | 201 | 201 | 0 | 0 | 7,839 | 0 |
| Greenhouse | 243 | 243 | 0 | 0 | 27,964 | 2 |
| Keka | 198 | 396 | 0 | 0 | 22,968 | 0 |
| LinkedIn | 88 | 525 | 2 | 1 | 1,163 | 93 |
| Naukri | 82 | 82 | 0 | 0 | 25,949 | 2 |
| SmartRecruiters | 80 | 530 | 0 | 0 | 24,000 | 13 |
| Workable | 202 | 202 | 0 | 0 | 1,212 | 0 |
| Workday | 10 | 10 | 10 | 10 | 0 | 0 |

`jobs_seen` is an observation count across polls, not unique vacancies. `new rows` counts inserted records, not necessarily unique active vacancies.

### Reliability interpretation

- **Workday:** 10 requests in 6h51m, all HTTP 429, one request per due attempt, no jobs returned. The old baseline was 4,894 requests and 417 HTTP 429 in 24h. At the current capped hourly cadence, the observed request rate annualizes to roughly 35 requests/day, about 99.3% below the old 24-hour request count. This is a request-storm reduction, not a source recovery. The scheduler has reached its 60-minute cooldown cap; latest failure streak 10, next due `2026-11-18T04:16:55.329405Z`.
- **LinkedIn:** 525 requests, 2 HTTP 429, 1 failed page and 93 new rows. Latest partial-rate-limited run at `02:40:43Z` triggered a persisted 9,600-second (160-minute) global cooldown after the sixth consecutive 429 in the persisted history. No LinkedIn requests should resume before the cooldown expires (approximately `05:20:43Z`). Keep the breaker intact; do not reset it manually. Earlier scans before the 429 continued returning results.
- **SmartRecruiters:** 80 polls / 530 requests / 24,000 seen / 13 new / 0 failed pages. The 7-hour average is 6.6 requests per poll versus the old 23-request pattern (3 listing + 20 detail calls), approximately 71% fewer requests at the observed poll count. Most recent poll used 3 listing requests, 300 detail-cache hits and 0 detail attempts. This confirms the cache is now warm and listings continue to refresh.
- **Naukri:** 82 successful relay ingestions, 82 requests, 25,949 seen, 2 new rows, no 429 or failed pages. Five-minute systemd relay timer is active.
- **ATS peers:** Greenhouse, Ashby, Keka, Darwinbox and Workable have zero 429s and zero failed pages in this window. One Ashby board poll had a transient `ConnectionError` at `02:52:28Z`; subsequent polls succeeded.
- **Database/feed:** 27,661 job rows, 115 rows inserted since release, zero duplicate `(source, source_job_id)` groups, `PRAGMA quick_check=ok`. There are still exactly 10 active ATS registry boards and 10 active schedules. One schedule remains `baseline_pending` (Workday); the other nine are past baseline.
- **Host:** latest sample at `03:49Z`: CPU 5.1%, memory 67.1%, disk 30.6%, load1 0.07, no OOM kills. Twelve-hour average CPU 14.7%, peak 90%; memory average 64.8%, peak 77.1%; disk average 29.7%. No resource-driven reason to alter the release.

### Company Watch candidate endpoint verification (read-only)

Nineteen direct ATS candidates were checked with one read-only public provider API request each (no production DB changes, no linking, no activation, no scheduled polling):

- 17 endpoints returned HTTP 200 with a valid provider response: Greenhouse 9/10, Lever 5/6, SmartRecruiters 3/3.
- Two CSV-derived provider slugs returned 404: Lever `mistral` and Greenhouse `soundhoundinc`.
- The Mistral official careers page links to `jobs.ashbyhq.com/mistral.ai`; the Ashby public posting API returned HTTP 200 and 254 jobs. This is a well-supported replacement candidate, but it has not been written to production or linked to a company record.
- SoundHound's official careers page is live, but the failed Greenhouse slug is not valid. The page's rendered content did not expose a verifiable replacement provider slug. Keep it for manual review.
- All 19 existing manifest candidates remain `discovered`/low confidence; 81 other manifest rows remain manual review. API endpoint response alone does not prove canonical employer identity, so no candidate is promoted to verified/active.

Official source references checked: `https://mistral.ai/careers/` (Apply now links to `https://jobs.ashbyhq.com/mistral.ai`) and `https://www.soundhound.com/careers/`.

### Next actions

1. Keep Workday at the 60-minute cap and verify the next attempt only when due; do not send manual probes while it is throttled.
2. Let LinkedIn's persisted 160-minute cooldown expire naturally. Inspect the first post-cooldown request count/result and retain conservative pacing. If it 429s again, allow the exponential breaker to escalate; do not bypass it.
3. Correct the Mistral candidate through the supported global-candidate import workflow after review of the official Ashby source; reject or retain the stale Lever slug as rejected/manual review. Do not create/activate an employer board until the company mapping is approved.
4. Keep SoundHound manual until its actual ATS provider and board key are confirmed from official source evidence.
5. Continue the 24-hour source comparison before marking the release reliability-accepted. Recheck source freshness, user feed, canonical dedupe and notification decisions; preserve the current 10-board allowlist.
