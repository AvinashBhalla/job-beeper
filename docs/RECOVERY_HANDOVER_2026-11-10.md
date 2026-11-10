# JobBeeper recovery and continuation checkpoint — 2026-11-10 (13:22 IST)

## Why this checkpoint exists
The prior ChatGPT response stalled during post-deployment verification. The work below was completed on the VM and GitHub before the interruption; this note is the canonical restart point.

## Merged work
### PR #67 — bounded company-agnostic ATS discovery
- Merged to `v2-live-radar` as `5d6e2b467be102de7056cf6681e1de13b0c3244f`.
- Adds manual/admin-only Common Crawl and robots-aware sitemap/career-link discovery.
- Candidates only; no automatic provider activation or notifications.
- Full V2 CI passed; focused discovery/API tests 34 passed.

### PR #68 — source phase and request latency telemetry
- Merged to `v2-live-radar` as `1763673dc638487fb2fd23a8f2ba1d74b81e1a4c`.
- Exact-head full V2 CI run 42771424120 passed, including full unittest suite.
- Adds collector, shadow, upsert, evaluation and notification timings; request min/max and bounded latency histograms; migration-safe fields and admin source-status reporting.
- Focused telemetry/status/latency tests passed 17/17 after updating the manually constructed legacy-schema test fixtures.

## Deployment completed
- Image: `job-radar-dev-multitenant:1763673`.
- Replaced shared dev and connector QA containers with the merged image.
- Existing volumes, environment, config and ports were preserved by recreating containers from their existing Docker inspect metadata.
- Previous containers retained for rollback:
  - `job-radar-dev-pre-source-phase-telemetry-20261110`
  - `job-radar-connectors-qa-pre-source-phase-telemetry-20261110`
- Pre-deploy SQLite backups, copied live-feed configs and SHA256SUMS:
  `/tmp/job-radar-release-backups/2026-11-10-pre-source-phase-telemetry/`
- Production was not changed.

## Post-deploy checks already observed
- Dev health HTTP 200; image tag correct; restart count zero; DB integrity `ok`; 10 active board schedules; zero sent notifications.
- Connector QA health HTTP 200; image tag correct; restart count zero; DB integrity `ok`; 10/10 active schedules reporting `success`; zero sent notifications.
- Schema migration ran on both volumes: new columns are present.
- Fresh telemetry rows are being written. Example:
  - Dev SmartRecruiters: 23 requests; request min/max ~482/2,400 ms; collector ~19.4s; shadow ~0.21s; upsert ~0.99s; evaluation ~0.71s; notification ~0.78s.
  - Dev Naukri: 1 request ~2.99s; collector ~3.10s; shadow ~1.91s; upsert ~2.08s; evaluation ~0.095s; notification ~0.80s.
  - Connector QA Naukri: 1 request ~0.28s; collector ~0.50s; shadow ~1.08s; upsert ~1.89s; evaluation ~0.002s; notification ~0.092s.
- Historical source_runs rows correctly retain nulls for new telemetry fields; new rows populate them.
- The first dev/QA query after rollout completed only partially due SQLite lock/wait contention while active poll cycles ran. Follow-up QA checks succeeded. Prefer short per-container read-only queries with busy_timeout=60000.

## Current worktrees
- Discovery release worktree: `/tmp/job-radar-roadmap-update-20261110`, detached at docs commit `6c89292`.
- Source telemetry worktree: `/tmp/job-radar-source-perf-20261110`, feature branch for PR #68.
- Release worktree: `/tmp/job-radar-release-source-perf-20261110`, detached at merge commit `1763673`.
- Feature branch for PR #68 should be deleted after successful merge confirmation; it is not required for ongoing work.

## Continue from here
1. Update this file and the performance benchmark/roadmap with the confirmed PR #68 merge/deployment and fresh telemetry values.
2. Verify current dev/QA health, image, restarts, DB integrity, schedule outcomes and sent notification count. Preserve cadence/config.
3. Inspect only naturally occurring post-deployment runs for Ashby and Greenhouse (and SmartRecruiters) to collect comparable phase timings. Do not trigger manual runs or shorten cadences.
4. Compare collector versus shadow/upsert/evaluation/notification durations. Collector duration includes network and parser/normalizer work; request min/max/histogram helps isolate network latency. This version does not yet have a separate parse/detail-enrichment timer.
5. Continue by instrumenting a more granular Ashby/Greenhouse collector phase only if the fresh telemetry shows collector remains the dominant source of elapsed time and request timings do not explain it.
6. Keep production untouched. Do not change poll intervals, concurrency, rate limits, sources or notification settings during profiling.
7. For further code changes, focused tests + full V2 CI + PR to `v2-live-radar`, then dev first and connector QA. Keep both rollback containers and database backups until stable.

## Outstanding QA limitations
- The prior desktop/browser screenshot evidence items for PR #66 remain separate from server/API behavior. They do not block the already merged board scheduler or current telemetry release; don't restart that UI effort unless explicitly requested.
