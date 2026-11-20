# JobBeeper production acceptance — 20 November 2026

**Assessment: CONDITIONALLY ACCEPTED.** Direct read-only inspection of the production VM, container, SQLite database, scheduler, source-run telemetry and local backup manifest was completed at approximately 2026-11-20 08:52 UTC (14:22 IST). No production writes, scans, imports, restarts, config changes or cooldown resets were performed.

## 1. Deployment and host

- Host: job-radar; application version 2.0.0.
- Container: v2-radar-1, running job-radar-prod-release:dda6d57.
- Image ID: sha256:bbf5252047ed2b3bbc8d06f7c51663e6deae4be28d9c82fdfc65e9a8b005ba5d (matches release qualification).
- Container started 2026-11-18 21:15:42 UTC; restart count 0; OOMKilled=false.
- /health, /dashboard/ and /openapi.json returned HTTP 200 on the VM. Public-IP HTTPS /health also returned HTTP 200.
- Host load average 0.24 / 0.13 / 0.04; RAM 573 MiB used / 249 MiB available of 956 MiB; swap 611 MiB / 2 GiB; root disk 13 GiB / 45 GiB (29%).
- Docker daemon and Nginx are active. The application is listening on 127.0.0.1:8000.

## 2. Database integrity and inventory

- Live SQLite read-only PRAGMA quick_check: ok.
- Jobs: 28,465; canonical opportunities: 28,142.
- Every job row has a canonical_opportunity_id; 230 canonical groups have multiple source observations, representing 323 additional observations beyond one representative per group.
- Duplicate (source, source_job_id) groups: 0.
- ATS schedule rows: 10; all 10 point to distinct registry rows; orphan schedules: 0.
- ATS registry rows: 9,941 total, of which 10 have review_status=active and 9,931 have review_status=discovered. The discovered rows are low-confidence candidate records and are not scheduled. Recent samples reference the third-party fyrosofttech/lastroundai-hiring-data directory. They must not be described as active boards.
- Separate Company Watch manifest: latest pinned import is 100 rows (19 candidate_staged, 81 manual_review, 0 invalid). The two manifest imports account for 200 historical manifest-row records. No additional board activations or schedules were found.
- Global ATS discovery run table contains zero runs; the 9,931 discovered registry candidates must not be represented as proof of an automated recurring discovery worker.

## 3. Active production board scheduler

All 10 configured boards have active schedules and recent runs. Intervals are 120 or 300 seconds, staggered by host.

| Provider | Employer / board key | Interval | Latest result | Latest jobs seen / new |
|---|---|---:|---|---:|
| Ashby | OpenAI / openai | 300s | Success | 852 / 0 |
| Ashby | PostHog / posthog | 300s | Success | 9 / 0 |
| Darwinbox | Arvind / main | 120s | Success | 44 / 0 |
| Greenhouse | Coinbase / coinbase | 300s | Success | 253 / 0 |
| Greenhouse | Graviton Research Capital / gravitonresearchcapital | 300s | Success | 19 / 0 |
| Greenhouse | Zocdoc / zocdoc | 300s | Success | 65 / 0 |
| Keka | Bridgestone / bridgestone1 | 120s | Success | 108 / 0 |
| SmartRecruiters | Bosch Group / boschgroup | 300s | Success | 300 / 4 |
| Workable | Hugging Face / huggingface | 120s | Success | 6 / 0 |
| Workday | NVIDIA / nvidia:nvidiaexternalcareersite | 120s | Rate limited | 0 / 0 |

A successful scan with zero new rows is not a failed scan. The latest SmartRecruiters poll inserted four jobs.

## 4. Rolling 24-hour source-run roll-up

Window: started_at >= 2026-11-19T08:49:00Z and < 2026-11-20T08:49:00Z. These are live SQLite source_runs aggregates, not the browser's earlier snapshot.

| Source | Runs | Successful | HTTP 429 / rate-limited | Failed pages | Jobs seen | New rows |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 552 | 552 | 0 | 0 | 234,812 | 26 |
| Darwinbox | 705 | 705 | 0 | 0 | 31,185 | 0 |
| Greenhouse | 843 | 843 | 0 | 0 | 95,310 | 3 |
| Keka | 698 | 696 | 1 | 2 | 75,168 | 0 |
| LinkedIn | 17 | 11 | 6 | 6 | 148 | 89 |
| Naukri | 287 | 0 | 0 | 287 | 0 | 0 |
| SmartRecruiters | 281 | 281 | 0 | 0 | 84,299 | 159 |
| Workable | 708 | 708 | 0 | 0 | 4,248 | 0 |
| Workday | 24 | 0 | 24 | 20 | 1 | 1 |

Interpretation:
- Workday: 24/24 runs were rate-limited; 63 consecutive failures are persisted for the NVIDIA host. Latest attempt 08:20:22 UTC returned HTTP 429. A 3,600-second cooldown is persisted until 09:20:22 UTC. Do not force a scan or reset the breaker. The one seen/new row is from a partial attempt and does not constitute source recovery.
- LinkedIn: 11 successful runs and 6 HTTP 429 events in 17 runs; latest recorded run at 07:04:34 UTC returned 429. Treat as intermittent but materially degraded.
- Keka: latest poll succeeded and its scheduler failure streak is zero, but the rolling 24-hour history contains one 429 and two failed pages/boards. Source Health should expose this recent degradation instead of presenting only a clean ACTIVE label.
- Naukri: all 287 polls failed closed because the published relay snapshot is unchanged. The last feed publication is 2026-11-18 09:07:34 UTC with 315 jobs; at inspection it was about 47 hours 45 minutes old. This is the owner's intentional publisher pause. Do not restart the relay or bypass the 15-minute freshness guard.
- Ashby, Darwinbox, Greenhouse, SmartRecruiters and Workable had no failed runs in this window. SmartRecruiters contributed 159 new rows; Ashby 26; Greenhouse 3.

## 5. Feed, matching and notifications

- 56,930 per-user job-evaluation rows exist across two users; 3,119 are marked matched in the database.
- Legacy/global notification ledger: 11 sent and 267 suppressed in the rolling 24-hour window.
- Per-user notification settings: 0; per-user notification ledger: 0. Do not interpret the 11 legacy/global sends as proof of member-specific notification delivery.
- The Desktop report's member account had an expired subscription and a six-hour feed delay. Active-subscription freshness and member-specific alert delivery remain unverified.

## 6. Backup verification

- Daily job-radar-sqlite-snapshot.timer is active and waiting.
- Latest snapshot service run started 02:45:35 UTC, finished 02:48:12 UTC, Result=success, exit status 0.
- All 10 entries in /var/backups/job-radar-daily/SHA256SUMS verified OK, including the 20 November dated database snapshot.
- Backups are VM-local; this is not off-site disaster recovery.

## 7. Browser-to-backend mapping gap

The Desktop report inspected administrator UI at the VM IP and member UI at jobbeeper.com. This VM's Nginx configuration declares 130.210.27.197 and proxies to 127.0.0.1:8000; the jobbeeper.com request is served through Cloudflare and its /health route returned an HTML 404 rather than the VM's JSON health response. The member report displayed 41,899 feed results and job detail ID 29,569,734; this VM's jobs table has 28,465 rows and maximum local job ID 28,465, so that reported detail ID is not present here.

Conclusion: the member browser surface and this VM's API/database have not yet been proven to share the same feed backend. Obtain a sanitized browser Network record showing the member jobs API hostname/path and response count before claiming end-to-end member-feed acceptance. Do not capture cookies, authorization headers or personal data.

## 8. Repository / operational caution

- The production checkout at /home/ubuntu/job-beeper is stale: branch v2-live-radar, HEAD 61d8271480eaf48b0a6442b62b1b0bb9a032df34, 899 commits behind origin, with an untracked .worktrees/ directory.
- Do not pull, reset, clean or develop in this checkout. Use a fresh, separately verified worktree based on the current GitHub v2-live-radar head for future engineering.
- The ubuntu account cannot access Docker directly; the owner-provided sudo read-only Docker checks were used. The Terminal Commands companion was able to run the read-only checks.
- A shell startup warning references missing /home/ubuntu/.local/bin/env. It did not prevent these commands from completing, but should be cleaned up separately, not during production acceptance.

## 9. Acceptance decision and next actions

**CONDITIONALLY ACCEPTED.** Production backend is online, runs the expected release image, has 10/10 correctly linked schedules, a healthy SQLite integrity check, zero duplicate source IDs, verified local backups, and six healthy ATS providers in the rolling 24-hour window. Acceptance remains conditional because Workday and LinkedIn are rate-limited, Keka has recent partial failures, Naukri is intentionally paused, per-user notification settings are absent, and the member-domain/backend mapping is unresolved.

Next actions:
1. Use a sanitized browser Network capture to identify the member feed API origin and confirm whether it reads this VM's jobs database.
2. Correct Source Health semantics so recent Keka partial failures, LinkedIn 429s, Workday cooldown/failure streak and Naukri intentional pause are differentiated accurately.
3. Preserve Workday and LinkedIn cooldowns; do not force retries. Keep the Naukri publisher paused until the owner explicitly changes that decision.
4. Compare the member feed's possible repeated cards against canonical opportunity IDs only after its API/database mapping is established.
5. Treat member-specific notifications as unverified until an active member account has notification settings and a safe, approved test path.
6. Make any code change in a fresh clean workspace, add focused regression tests, then exact-head regression and a separately approved release. No production changes were made during this audit.

## 10. Commands and evidence scope

Read-only evidence came from docker inspect, docker ps, docker logs, local/public health requests, systemd timer/service status, SQLite opened with mode=ro, PRAGMA quick_check, SQL aggregation, and sha256sum -c. No production config/token values, passwords, cookies, or message bodies were read or printed.