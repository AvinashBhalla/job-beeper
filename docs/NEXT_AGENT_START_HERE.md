# Next Agent Start Here — Job Radar V2

**Checkpoint:** 2026-11-08, 17:10 Asia/Kolkata  
**Read this first when taking over the Job Radar task.**

## Owner's product goal

Build a reliable multi-source job radar that fetches new jobs from all 36 requested platforms, filters each job separately against each user's saved preferences, and sends Telegram alerts only to matching users. The owner expects near-real-time capture (target 2-minute polling for high-priority boards where permitted; webhooks when an employer authorizes them), not a daily batch.

The required 36 platforms and source-by-source current status are in [ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md](ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md). Workday and Darwinbox are the first missing connectors the owner called out. The list mixes ATS vendors and job marketplaces; ATS feeds generally require a specific employer board/tenant, so company/career-site discovery is a core requirement.

## Current environment

- Oracle VM: job-radar; SSH login ubuntu; full passwordless sudo. Use sudo for Docker/systemd.
- Shared dev: container job-radar-dev, image job-radar-dev-multitenant:b16fb83, host port 8001, health HTTP 200.
- Production: container v2-radar-1 on port 8000, still old image and untouched. Health HTTP 200.
- Shared-dev app/test code SHA used to build b16fb83: 754809fe406e8c5cb09f8e36140ac5cf3e4f7238. Later branch commits are documentation-only; re-check PR head and CI.
- PR #51: https://github.com/AvinashBhalla/job-beeper/pull/51 — open/draft, not merged.
- Only Naukri is enabled in shared-dev's recurring scheduler. Notifications/Telegram, Gemini and LLM routing are off in shared dev.

## What is actually live-tested

Real shared-dev end-to-end pipeline evidence exists for:
- Naukri scheduled polling
- Instahyre: 140 inserted, 4 HTTP 200 pages; current response parser fixed
- Greenhouse: 369 inserted, 3/3 boards
- Ashby: 828 observed, 34 new, 2/2 boards
- Lever: 500 inserted via one-off paytmpayments board, 5-page cap reached; not configured for recurring polling
- LinkedIn: one paced HTTP 200 probe, 10 unique jobs inserted; not configured for recurring polling

V2 COLLECTORS currently registers only those six sources. The other 30 named platforms are not production-grade V2 integrations yet. Do not claim all 36 are working.

Latest verified shared-dev data: SQLite integrity ok; jobs/canonical/global evaluations/per-user evaluations/global notification ledger = 9,444; source_runs=7,858; one admin user, one profile preference row, zero user_notification_ledger rows. Global ledger sent_at count=0.

## Immediate blockers before production

1. Fix an intermittent sqlite3 OperationalError: database is locked in notification_worker -> recover_stale_claims during concurrent source ingestion. Add a concurrency regression/load test and prove it stops recurring.
2. Verify multi-user signup/login, preferences, CSRF-protected mutations, and per-user Telegram linking/delivery with at least two test users. Use a fake transport or dedicated test chat; never request secrets in chat.
3. Implement employer/board discovery and the first missing ATSs: Workday, then Darwinbox.
4. Continue the remaining 36-platform roadmap. Mark a source complete only after a real board test with stable polling/webhook, pagination, dedup, correct timestamps, close/update handling, DB matching/evaluation and per-user notification decisions.
5. Keep the known 320px toolbar overlap deferred as requested; it is not the priority now.
6. Do not deploy production yet. Production has live global Telegram credentials and notifications enabled; preserve its existing queue/delivery behaviour. The earlier disposable production DB migration preflight is not a production backup or deployment.
7. Production promotion requires a fresh formal online SQLite backup, a reviewed safe delivery plan, all P0 gates, and separate explicit owner approval. Prior deployment approval covered shared dev only.

## Required reading / handover

1. [36-platform coverage, connector research and acceptance criteria](ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md)
2. [Deployment runbook](DEV_DEPLOYMENT_RUNBOOK_2026-11-08.md)
3. [Promotion execution record](QA/shared-dev-promotion-execution-2026-11-08.md)
4. The latest appended section at the END of [JOB_RADAR_HANDOVER.md](JOB_RADAR_HANDOVER.md)
5. The latest appended section at the END of [JOB_RADAR_KNOWLEDGE_TRANSFER.md](JOB_RADAR_KNOWLEDGE_TRANSFER.md)

Do not ask the owner to repeat the platform list, latency goal, Workday/Darwinbox priority or per-user Telegram requirement.
