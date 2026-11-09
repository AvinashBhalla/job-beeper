# Recovery checkpoint — candidate staging + live feed parity

Updated: 2026-11-09 22:09 IST
Feature branch: feat/global-ats-discovery-hirebase-guard-20261109
Feature SHA: 243da9c35e93979e59d0de281130581cad4124d1
PR: https://github.com/AvinashBhalla/job-beeper/pull/65 — OPEN, DRAFT, NOT MERGED.
Exact-head CI: V2 workflow #1437 / 42648073320 — SUCCESS, including Python compilation, dashboard JS syntax, focused tests and full V2 suite.
Local full V2 suite: 451 passed in 482.864s, exit 0; log /tmp/job-radar-global-candidate-final-tests.log. Candidate API-focused tests: 11 passed.

## 1. Completed code in PR #65

- Optional default-off Hirebase estimate-first sampler, persisted local usage quota and 429 cooldown. No key supplied; no Hirebase API calls.
- LastRound AI CC BY 4.0 company directory imported as 9,935 low-confidence ATS candidates only.
- Workday incremental inventory and bounded facet queue for the 2,000-result cap, persisted cursor and admin status UI.
- Keka default/named career portals with tenant:portal identity.
- Separate ats_global_discovery_candidates table and admin-only import/list/link/reject APIs. Strict public Workday/Keka/Darwinbox URL canonicalization, provider+host+board-key identity, newest capture provenance retained, linked/rejected state preserved.
- Import creates no employer or normal board-registry rows. Linking requires an existing employer and creates/reuses a discovered board; verification and activation are separate.
- Coverage & Health UI for candidate review/board status.
- Research covers Freehire, Career-Ops, JobSpy, JobNavigator, Job Board Aggregator, Job Forager, ats-scrapers and Common Crawl.
- Detail: docs/GLOBAL_ATS_CANDIDATE_STAGING_2026-11-09.md and docs/COMPANY_AGNOSTIC_ATS_DISCOVERY_2026-11-09.md.

## 2. Live environment rollout — completed dev first, then connector QA

| Environment | Container / address | Image | Enabled feeds | Cadence | Data/delivery |
|---|---|---|---|---|---|
| Production | v2-radar-1, port 8000 | job-radar-prod-canary:6e5becb | LinkedIn, Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka, Darwinbox | unchanged | Separate production volume; notifications on; Telegram credentials present. DO NOT TOUCH. |
| Shared dev | job-radar-dev, port 8001 | job-radar-dev-multitenant:243da9c | Naukri, Greenhouse, Ashby, Workday, SmartRecruiters, Workable, Keka, Darwinbox | mostly 15m; SmartRecruiters 30m | Separate job-radar-dev_radar-dev-data; notifications off; Telegram/Gemini/LLM/Hirebase credentials empty. |
| Connector QA | job-radar-connectors-qa, port 8010 | SAME image SHA as dev: sha256:75d1f8ffe01335f35a7a7447671d2319f46edb4fcfe5eb9cf829617998de5e31 | Same eight feeds and public board allowlist | 60m for all sources | Separate job-radar-connectors-qa_qa-data; notifications off; Telegram/Gemini/LLM/Hirebase credentials empty. |
| Browser QA | job-radar-browser-qa, port 8006 | prior synthetic image e6181d9 | all sources off | none | Separate synthetic DB: 4 demo jobs, 2 pre-existing QA accounts. Unchanged. |

LinkedIn is intentionally off in non-production: production telemetry over the prior 24 hours showed 10 HTTP 429s and 7 failed pages. Do not multiply that request pressure across dev and QA. Instahyre and Lever remain off because they are disabled in production. Hirebase remains off.

Public allowlist copied from production (no production IDs): Greenhouse 3, Ashby 2, Workday 1 NVIDIA public board, SmartRecruiters 1, Workable 1, Keka 1, Darwinbox 1; Naukri uses its public relay. Only public board identifiers/URLs and display names were copied. No production DB, users, preferences, sessions, registry IDs, notification ledger, bot tokens, OAuth or LLM secrets were copied.

Important runtime detail: the app creates /data/config.json, which takes precedence over the read-only mounted config. After deploying, save the reviewed config via radar.save_config() in each environment. Both non-production runtime configs are now v17 with eight active source flags, LinkedIn/Instahyre/Lever/Hirebase false and notifications false.

## 3. Live feed verification

### Shared dev 8001

Initial live poll completed successfully for all eight active feeds:
- Naukri: real relay; 199 observed, 0 new on first run because records already existed.
- Greenhouse: 3/3 boards, 369 postings.
- Ashby: 2/2 boards, 825 postings.
- Workday: 1/1 NVIDIA public board, 20 returned, 21 HTTP requests; capped root query queued 15 facet partitions.
- SmartRecruiters: 1/1 board, 300 postings, 3 pages/23 requests.
- Workable: 1/1 board, 6 postings.
- Keka: 1/1 portal, 109 postings.
- Darwinbox: 1/1 public candidate board, 36 postings.

Follow-up polling as of 2026-11-09 16:30 UTC: 3 runs each for Ashby, Darwinbox, Greenhouse, Keka, Workable and Workday; 2 for SmartRecruiters; continued Naukri polling. In the two-hour window: 0 HTTP 429, 0 page failures, 0 board failures. New-job sums: Ashby 6, Darwinbox 36, Greenhouse 3, Keka 109, Naukri 255, SmartRecruiters 301, Workable 6, Workday 49.

Latest dev DB: 10,259 jobs; 8,221 source runs; 1 user; 1 preferences row; 10,259 canonical opportunities; 10,259 global evaluations; 10,259 per-user evaluations; 10,259 notification-ledger rows. SQLite integrity ok; sent notifications 0. Health HTTP 200; container restart count 0.

### Connector QA 8010

First full live pass from all eight feeds:
- Naukri 199
- Greenhouse 369 (3/3 boards)
- Ashby 825 (2/2 boards)
- Workday 20 (one board, 21 HTTP requests)
- SmartRecruiters 300 (one board, 3 pages/23 requests)
- Workable 6
- Keka 109
- Darwinbox 36

Total 1,864 live jobs, 8 successful source runs, 0 HTTP 429, 0 page failures, 0 board failures. Workday facet queue persisted. Health HTTP 200; SQLite integrity ok; sent notifications 0; no QA users/preferences as of last check. QA has one complete pass; the next 60-minute cycle remains to be observed.

### Browser QA 8006

Still synthetic and separate: 4 demo jobs and 2 previously created QA accounts, all collectors off. It was not changed. Do not mistake it for live connector QA 8010.

## 4. Backups and image

- Dev pre-rollout online SQLite backup: /var/backups/job-radar-daily/dev-pre-live-feed-20261109T155300Z.sqlite3; 52,871,168 bytes; root:root 0600; SHA-256 cddc7bfbf31f37344a32680c4c2fc238e4c8918715be989c21dadfe56f9d5396; integrity ok; preserved 9,748 jobs, 8,197 source runs, 1 user and 1 preferences row.
- QA pre-rollout backup: /var/backups/job-radar-daily/qa-pre-live-feed-20261109T161000Z.sqlite3; 217,088 bytes; root:root 0600; SHA-256 89724422f7d207aaa24903812638f2ee5a8544ea9a22793dadf543afa931d392; integrity ok; QA was empty before enabling feeds.
- Candidate image tag job-radar-dev-multitenant:243da9c; image SHA sha256:75d1f8ffe01335f35a7a7447671d2319f46edb4fcfe5eb9cf829617998de5e31.
- Previous dev image e6181d9 and synthetic browser QA container remain available.
- Production was not restarted, reconfigured or modified. Health returned HTTP 200 on 8000, 8001, 8006 and 8010 at last check.

## 5. Owner test URLs and tunnels

From Windows PowerShell, keep each SSH tunnel open:
- Shared dev: ssh -N -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197 ; open http://localhost:18001/dashboard/
- Live connector QA: ssh -N -L 18010:127.0.0.1:8010 ubuntu@130.210.27.197 ; open http://localhost:18010/dashboard/
- Synthetic UI baseline: ssh -N -L 18006:127.0.0.1:8006 ubuntu@130.210.27.197 ; open http://localhost:18006/dashboard/

### QA account provisioning — owner action

Connector QA DB had zero users at the last check. The remote account-provisioning attempt did not complete; no account/password was created or shared. Do not copy production/dev users.

Run these commands from an interactive VM terminal and set passwords locally when prompted:
sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-admin --email qa-admin@local.test
sudo docker exec -it job-radar-connectors-qa python -m v2.auth_admin create-user --email qa-member@local.test

The first creates the QA admin and the second an ordinary member. Do not paste passwords into chat. These accounts are separate from the existing 8006 synthetic QA accounts.

## 6. Release boundary

- PR #65 is open/draft; not merged. Dev and connector QA intentionally run unmerged candidate SHA 243da9c for pre-merge validation.
- Production stays on image job-radar-prod-canary:6e5becb, port 8000, config v15. Production has nine source flags enabled including LinkedIn; notifications and Telegram are live.
- No notification delivery in dev/QA. A dedicated non-production Telegram bot/chat is only required for future delivery testing, not feed parity.
- No Hirebase API calls or Common Crawl requests. No production work.

## 7. Next priorities

### P0
1. Owner opens dev and live connector QA using the tunnels above; checks Coverage & Health, live job feed, source health and board list.
2. Owner provisions QA-only admin/member with the interactive CLI commands and validates role separation.
3. Observe the next 60-minute QA poll cycle: all eight sources should run successfully, with no 429/page/board errors, healthy DB and zero sends.
4. Review PR #65 diff/CI and UAT. Keep draft; merge only after owner acceptance.
5. Keep LinkedIn off in non-prod until cooldown/rate-limit issue is understood and a paced one-request canary is separately approved.

### P1
6. Persistent per-board due scheduler with host-level concurrency/budgets, jitter, Retry-After, cooldown, cursors/checkpoints, backpressure and queue-age status.
7. Serialized Common Crawl CDX candidate harvester with persisted request budget, pinned crawl ID, one provider query per invocation, response cap and 24h stop after 503; no proxy or parallel sweeps.
8. Sitemap/career-link candidate discovery under robots and per-host crawl budgets; stage candidates only until live-verified and linked to a real employer.
9. Darwinbox 403/429/5xx per-board classification; 403 stays blocked, no anti-bot bypass.
10. Benchmark p50/p95 latency, first-seen delay/freshness, feed completeness and rate limits; monitor Workday facet queue.

### P2
11. Stale/closed/repost/legitimacy checks, explainable fit, resume vault and answer bank.
12. Then approval-gated browser form fill, referral research and application follow-up automation.

## 8. User inputs

Only action needed for live two-role QA is to create the QA admin/member as above and perform UAT. No API key or production credential is required. Hirebase key remains absent. Production promotion needs separate explicit approval after dev/QA sign-off.

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


## 2026-11-09 — autonomous connector-QA scheduler cycle observed

The pending autonomous 60-minute cadence check is now **complete for one follow-on cycle**. QA's initial scheduled full pass started at `2026-11-09T16:05:03Z`; a controlled/manual verification batch followed around 16:48Z; the next scheduled batch started at `2026-11-09T17:05:04Z`, approximately 60 minutes after the first. This confirms one autonomous scheduler interval, not a long-term uptime/SLA guarantee.

| Source | Jobs seen | New rows | HTTP requests | Pages succeeded | Boards succeeded | Outcome |
|---|---:|---:|---:|---:|---:|---|
| Naukri | 195 | 2 | 1 | 1/1 | n/a | success |
| Greenhouse | 370 | 0 | 3 | n/a | 3/3 | success |
| Ashby | 823 | 0 | 2 | n/a | 2/2 | success |
| Workday | 40 | 20 | 22 | 2/2 | 1/1 | success |
| SmartRecruiters | 300 | 3 | 23 | 3/3 | 1/1 | success |
| Workable | 6 | 0 | 1 | 1/1 | 1/1 | success |
| Keka | 109 | 0 | 2 | 1/1 | 1/1 | success |
| Darwinbox | 36 | 0 | 1 | 1/1 | 1/1 | success |
| **Total** | **1,879** | **25** | **55** | **No failures** | **No failures** | **8/8 success** |

All 55 responses were HTTP 200; HTTP 429 = 0, request exceptions = 0, page failures = 0, board failures = 0. Workday's facet queue remains bounded and persisted. The read-only QA DB check returned `PRAGMA integrity_check=ok`; totals after the run: jobs 1,916; source_runs 24; canonical opportunities 1,916; evaluations 1,916; notification-ledger rows 1,916; sent notifications 0; users 0; preferences 0. The container health endpoint returned 200.

**Disposition:** autonomous-cycle P0 gate closed for this observation. Continue normal monitoring during owner UAT, but do not block the next step on repeating a manual ingestion pass. The remaining live-QA blocker is owner provisioning of QA-only admin/member accounts, followed by role/tenant-isolation browser checks.
