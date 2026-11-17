# JobBeeper release readiness, repository cleanup and VM health — 2026-11-17

## Executive status

The production Source Health screenshots show a live product, not a dormant scanner. The admin dashboard recorded 379 jobs discovered today, 26 matched and 25 alerted. Naukri Relay, Greenhouse and Ashby reported operational status. LinkedIn was partial and Workday was failing heavily with HTTP 429 responses.

The repository cleanup is complete on GitHub: there are no open PRs and only two remote branches remain, main and v2-live-radar. The two branches have different purposes and must stay separate: main contains the standalone Company Watch discovery/dry-run work; v2-live-radar contains the JobBeeper V2 product and its Company Watch integration.

This is not yet a production release of Company Watch. PR #76 is merged into V2 code, but the importer has not been deployed to a shared runtime and the 100-row manifest has not been imported into a persistent database. No new Company Watch board has been verified, activated or polled.

## Production Source Health evidence supplied by the owner

Screenshots: production dashboard /dashboard/#sources, captured 17 Nov 2026 around 6:31–6:32 pm IST.

| Source | Latest jobs seen / new | 24h requests | HTTP 429 | Page/board failures | Last success | Assessment |
|---|---:|---:|---:|---:|---|---|
| LinkedIn | 21 / 16 | 79 | 6 | 3/37 pages | 17 Nov, 10:33 am IST | Partial; rate-limited |
| Naukri Relay | 311 / 1 | 286 | 0 | 2/286 pages | 17 Nov, 6:31 pm IST | Active; relay snapshot reported fresh |
| Instahyre | 0 / 0 | Not measured | Not measured | Not measured | Not specified | Disabled; stale 400 diagnostic |
| Greenhouse | 346 / 0 | 861 | 0 | 0/861 boards | 17 Nov, 6:32 pm IST | Active / Operational |
| Ashby | 849 / 0 | 570 | 0 | 0/570 boards | 17 Nov, 6:28 pm IST | Running / Operational |
| Lever | 0 / 0 | Not measured | Not measured | Not measured | Not specified | Disabled |
| Workday | 0 / 0 | 360 | 285 | 241/286 pages | 16 Nov, 12:35 pm IST | Error; severe 429 failure |

Notes:
- The Workday row is the most urgent source-health issue: 285 HTTP 429 responses out of 360 requests, 241/286 page/board failures, and no success since 16 Nov in the screenshot.
- LinkedIn is still finding jobs (16 new in its latest run) but has partial page failures and 6 HTTP 429 responses.
- Naukri, Greenhouse and Ashby are the currently healthy feeds in this view. Naukri has 1 new job in the latest snapshot cycle; a high seen count is not the same as a high new-job count.
- The Company Watch manifest candidates in this plan are not yet part of these source counts.

### Important meaning of the “25 alerted” number

The dashboard HTML labels this metric “Telegram alerts sent today”. The admin /api/daily-summary implementation counts rows in the legacy/global notification_ledger with status=sent. The legacy Telegram sender writes status=sent only after Telegram sendMessage responds successfully and the JSON payload has ok=true.

This proves that the legacy/global Telegram delivery path recorded 25 successful sends today. It does not prove that 25 messages were sent through the newer per-user notification system.

The member notification path is separate:
- It uses user_notification_ledger, not the legacy notification_ledger.
- The member APIs are GET /api/telegram/status, GET /api/notifications/settings and PUT /api/notifications/settings.
- Those routes explicitly reject admin accounts; per-user Telegram linking/settings are for a normal member account.
- A member must have a linked private Telegram chat and must explicitly enable notifications. The enabled_at timestamp is the no-backlog boundary; old jobs are not supposed to be sent as a historical backlog.
- The per-user dispatcher revalidates the current match and opt-in before sending, and records sent only after Telegram returns ok=true.

Therefore the 25 count must not be used as the acceptance test for the owner's own per-user notifications. The admin dashboard currently reports the legacy/global count; the personal member delivery path needs its own end-to-end test and ideally a user-scoped dashboard metric.

## GitHub PR and branch cleanup

### PRs

| PR | Result | Reason / effect |
|---|---|---|
| #70 — evaluation fingerprint rollout / Dev QA docs | Closed, not merged | Stale documentation-only proposal; its operational findings are now in the maintained handovers |
| #71 — reuse experience extraction for unchanged jobs | Merged into v2-live-radar as e3f1c9c | Rebased to the current V2 base; full exact-head CI ran 496 tests, 0 failures in 60.133s. Reduces repeated regex-heavy extraction for unchanged title/description/format and invalidates cache on text/parser-version changes |
| #73 — Company Watch ATS coverage and scan reporting | Merged into main as fced495f | Changes the separate Company Watch dry-run scanner/reporting lane; it does not activate V2 boards or deploy Company Watch into JobBeeper |

PR #76 remains merged into v2-live-radar at 0220eef. It adds review-only manifest import capability; it is not a deployment. PR #74 and #75 were already merged. At the cleanup verification point, GitHub reported zero open PRs.

### Remote branches

Only these remote branches remain:
- main — default branch and isolated Company Watch discovery/dry-run lane
- v2-live-radar — JobBeeper V2 product and integration/release lane

The old feature branches that had already been merged, superseded or closed were deleted from GitHub. main is intentionally retained; do not merge its standalone Company Watch project wholesale into V2. Only reviewed data and integration changes belong in v2-live-radar.

### VM-local repository/worktree cleanup

The development clone had accumulated many historical feature branches and 24 Git worktrees. Eight worktrees whose branch tips were already in V2 or whose docs/PRs were superseded were removed first. The remaining local refs were then archived; after that, twelve more clean, unused worktrees and their stale refs were removed. In total, 20 worktrees were removed. The archive is:

/home/ubuntu/.archives/job-beeper-local-branches-2026-11-17.bundle

It is 5.7 MB, contains 65 refs, and git bundle verify succeeded. It is a recovery archive, not a live branch.

Four worktrees remain deliberately:
1. /home/ubuntu/job-beeper-dev — primary dev checkout. It is dirty and behind; preserve it.
2. /home/ubuntu/job-beeper-global-ats-test — dirty global ATS QA checkout; preserve it.
3. /tmp/job-radar-source-observability — has three modified/uncommitted entries; preserve it.
4. /tmp/job-radar-linkedin-backoff — backing the currently running QA API on port 8003; preserve it while that service is alive.

The dev clone now has four local branch refs: v2-live-radar plus the three branches attached to those retained QA worktrees. The main dev checkout still has its modified v2/config.json and untracked .env.save, .venv/ and v2/config.json.backup.20261105-183321; these were preserved. The global ATS QA worktree has 17 dirty entries and the source-observability worktree has three; both were preserved. No uncommitted files were overwritten or deleted. The GitHub remote branch list remains just main and v2-live-radar.

The production clone /home/ubuntu/job-beeper has two local branches, main and v2-live-radar, and a clean working tree. After a safe fetch-only refresh of remote tracking refs, its local V2 branch is 782 commits behind current origin/v2-live-radar and local main is 129 commits behind origin/main. The dev clone is 176 commits behind origin/v2-live-radar. These are source checkouts, not the running container revision. Neither checkout was pulled, reset, rebuilt or deployed.

## VM health and optimization

Read-only host checks on 17 Nov 2026:
- 2 vCPU and about 956 MiB physical RAM.
- Swap is 2.0 GiB and was almost completely used (about 36 MiB free); available RAM was about 333 MiB.
- Load average at the sample was 3.42 on 2 cores.
- Memory pressure: memory PSI full avg10 19.69%, avg60 12.14%.
- I/O pressure: I/O PSI full avg10 54.23%, avg60 32.35%.
- Root disk: about 19 GiB used of 45 GiB (41%), with about 27 GiB free. Disk capacity is not currently the limiting resource.
- Journald used about 392 MB.
- The process list showed six Uvicorn processes using the production V2 command/port 8000 and additional isolated QA processes on ports 8003–8005. Docker inventory was not available to the Termalin ubuntu user, so the exact container/image/mount ownership remains unverified.

Recommendation:
1. Right-size the VM to 4 GiB RAM if production and isolated QA are expected to coexist; 2 GiB is a minimum improvement, not a comfortable target for this service mix. Confirm the Oracle shape/cost and maintenance window before resizing.
2. After Docker inventory is available, identify and retire only QA containers that are no longer being used. Ports 8003–8005 are QA-only candidates; 8003 is currently backed by the active LinkedIn-backoff worktree, so do not stop it until that QA task is formally closed. Preserve production port 8000 and all persistent volumes.
3. Keep one current QA app+DB rather than several overlapping QA app instances. Archive test code before removing old QA workspaces; the Git bundle now provides branch-history recovery.
4. Repair the daily SQLite snapshot service. Its logs on 15–17 Nov show the production online snapshot itself succeeded and passed integrity_check, but the script then failed on a subsequent stopped container with “cannot exec in a stopped state”. Termalin reports no configured encrypted backup jobs/archives for this VM. Do not deploy until a fresh backup and a restore check are complete.
5. Do not run swapoff, delete logs, prune Docker volumes, change Docker permissions or restart containers as a performance shortcut. Those actions can turn current pressure into data loss or an outage.

No VM resize, Docker stop/remove, package update, snapshot-service repair, database change, source toggle or production deployment was performed. The server account used for inspection cannot access /var/run/docker.sock; I did not bypass that permission boundary.

## Release path before Company Watch goes live

The correct next milestone is a controlled V2 QA release and notification acceptance test—not immediate production activation.

### Gate 1 — Stabilize existing sources and verify runtime identity
- Resolve the Workday HTTP 429 problem. Current per-host Workday fallback cooldown is 300 seconds (up to 3600 seconds when Retry-After specifies more). In board_scheduler.finish_poll, repeated rate-limited outcomes increment the failure count but the retry delay currently does not grow from that count when Retry-After is absent. Prepare a bounded adaptive per-host backoff change that continues to honor Retry-After and does not pause unrelated tenants globally.
- Review LinkedIn's partial failure/429 evidence and the retained longer-backoff candidate before any change. Do not widen LinkedIn request volume.
- Obtain container/image digest, running app commit/config, source-run telemetry, actual DB volume identity and Telegram settings using an approved Docker/operator path. The authenticated screenshot confirms product activity but does not identify the running image SHA.
- Keep Naukri, Greenhouse and Ashby as the observed healthy baseline. Do not enable more sources just to increase the number of jobs.

### Gate 2 — Create an isolated QA runtime from current V2
- Use a fresh clean checkout/build of current v2-live-radar (currently e3f1c9c, plus any reviewed follow-up fixes); do not use the dirty /home/ubuntu/job-beeper-dev checkout.
- Use an isolated persistent QA database and config. No production user data, production Telegram destination or production bot secrets.
- Run the full V2 test suite on the exact build. The last current V2 head passed 496 tests after PR #71; all new Workday/backoff changes must also pass exact-head CI.

### Gate 3 — Import and verify the Company Watch sample, still review-only
- Import the pinned 100-row manifest into QA using the PR #76 admin dry-run/import API. The parser stages 19 ATS candidates and holds 81 records for manual review; all staged candidates start low-confidence and unlinked.
- Resolve canonical employer identity before linking. The current link path requires an existing employer row; the employer-creation route crawls public pages, so do not use it as a metadata-only registration workaround.
- The suggested four-company sample is Canva and Abercrombie & Fitch (SmartRecruiters), plus Cyderes and Kobie (Lever). Their manifest label is a review hint, not V2 live verification or approval.
- Verify those exact official boards through the V2 verification path in QA. Record 401/403, 404, 429, TLS, timeout and parser failures distinctly. Do not activate them yet.

### Gate 4 — Activate only the approved four in QA and validate two polls
- Before activation, ensure the QA config contains only the approved sample for each provider. The existing activation route enables a provider-level source flag and synchronizes the provider's whole configured allowlist; unrelated peer boards could otherwise be scheduled.
- Activate only the explicit approved board IDs.
- First successful poll must be baseline-only and silent. Confirm baseline_pending clears and no backlog Telegram notification is queued.
- On a second poll, verify new unique listings, canonical dedupe, correct company/title/location/posted date/apply URL and complete job descriptions. Check the source-run and board-scheduler ledgers.

### Gate 5 — Test actual user matching and private Telegram delivery
- Use a normal member account with the owner's saved preferences. An admin account cannot use the member Telegram-link/settings routes; the code deliberately returns 403 for admins.
- Confirm GET /api/telegram/status reports a connected private chat and GET /api/notifications/settings reports enabled=true after explicit opt-in. A private chat must be linked before enabling notifications.
- The enabled_at time is the no-backlog boundary. Existing/first-poll baseline jobs should not be sent as a burst.
- Wait for a genuinely new job from one of the four boards that matches the member's saved role, experience, skills and location. Verify the per-user evaluation, user_notification_ledger row, message content, Telegram API ok=true response and final per-user sent state. Check that a repeat poll does not send the same canonical opportunity twice.
- The dashboard's current admin “25 alerted” metric is not this acceptance test; it counts the legacy/global ledger. Add/verify a user-scoped alert metric before relying on the number for member delivery.

### Gate 6 — Production approval and monitored rollout
- Create a fresh encrypted production backup, verify database integrity and prove the restore procedure.
- Compare the candidate image digest, source commit, effective config and DB volume to the approved release manifest. The production checkout is currently far behind the V2 branch; do not treat a Git merge as a deployment.
- Deploy only after QA acceptance and explicit approval. Keep the first production board allowlist to the four reviewed boards, retain baseline suppression, and keep a rollback image/config/DB recovery path ready.
- Monitor per-source runs, new jobs, matching precision, JD completeness, user_notification_ledger and Telegram delivery for 24–72 hours before adding any more companies.

## Current next-action order

1. Workday per-host 429/backoff fix and LinkedIn review.
2. Docker/container and production DB identity access, snapshot repair and backup/restore readiness.
3. Fresh isolated QA runtime from current V2.
4. Company Watch manifest import, identity resolution and four-board QA verification.
5. Four-board QA activation, silent baseline and second-poll ingestion.
6. Member-account Telegram canary, then explicit production rollout.
