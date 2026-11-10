# Source phase telemetry — recovery handover (2026-11-10)

## Previous work completed
- PR #67 merged to v2-live-radar as 5d6e2b4.
- Bounded Common Crawl and robots-aware sitemap/career-link discovery are deployed to dev and connector QA.
- Both environments use image job-radar-dev-multitenant:5d6e2b4, have HTTP 200 health, zero restarts, SQLite integrity ok, 10/10 successful board schedules, and zero notifications sent.
- Production was not changed. Rollback containers and database/config backups remain on the VM.
- The roadmap was updated at 6c89292. Performance baseline is docs/SOURCE_PERFORMANCE_BENCHMARK_2026-11-10.md.

## Current task
Branch: feat/source-phase-performance-telemetry-20261110
Worktree: /tmp/job-radar-source-perf-20261110
Base: v2-live-radar at 6c89292

Goal: add low-overhead phase-level timings to source_runs so slow source runs can be separated into collector/network, normalization, detail enrichment, database upsert and post-processing time. Also add per-request latency distribution summaries (not just request_duration_ms_total).

## Baseline findings (previous 24h, shared dev)
- Ashby: 61/61 successful, zero 429; runtime p50/p95 89.65/242.40 seconds.
- Greenhouse: 63/63 successful, zero 429; runtime p50/p95 65.05/190.47 seconds.
- SmartRecruiters: 30/30 successful, zero 429; 690 requests total; runtime p50/p95 37.54/167.29 seconds.
- Workday: 57/57 successful, zero 429; 1,520 jobs seen / 431 new; 1,219 requests; runtime p50/p95 70.58/127.81 seconds.
- Keka and Darwinbox: 58/58 and 59/59 successful respectively, zero 429.
- QA uses a slower 60-minute cadence. Do not change intervals or concurrency during measurement.

## Existing instrumentation inspected
- SOURCE_METRIC_FIELDS currently stores request counts, response counts, status buckets, retry attempts, aggregate request_duration_ms_total, page counts and board counts.
- _begin_source_run_metrics(source), _record_source_request(...), _record_source_page(...), _record_source_board(...), _finish_source_run_metrics(source) manage in-memory per-source metrics.
- run_source (source orchestration) calls COLLECTORS[source](config), then shadow extraction, upsert_jobs, baseline suppression, evaluation refresh and notification decisions before record_run.
- normalize_job currently returns a normalized dictionary with no timing.
- source_runs is migration-safe via _ensure_column; new columns should be additive and nullable/default-safe.
- Existing dashboard/admin source telemetry reads source_runs by selected metric columns. New fields must be exposed deliberately and must not break old databases.

## Immediate implementation plan
1. Add a thread-safe phase timing accumulator to active_source_metrics with explicit phases: collector_total_ms, upsert_ms, shadow_ms, evaluation_ms, notification_ms. Use monotonic clocks around existing orchestration boundaries.
2. Add per-request duration aggregates (count, total, min, max and bounded histogram buckets or compact percentile approximation). Keep endpoint URLs, query strings, request bodies and response contents out of telemetry.
3. Avoid timing every normalize_job call individually initially; collector_total_ms already captures parsing/normalization and request time. If phase breakdown still cannot explain Ashby/Greenhouse, instrument detail-fetch vs parse in those collectors separately.
4. Add nullable columns or one compact JSON field to source_runs; prefer explicit numeric columns for the main phases and a compact request latency summary. Use migration-safe _ensure_column.
5. Update record_run and source health aggregation/status API to expose fields only where useful. No UI work.
6. Add deterministic tests for phase accumulation, request latency aggregation, migration from old source_runs schema, error-path finalization, and backward compatibility of status summaries.
7. Run focused tests, full V2 unittest suite and exact-head GitHub CI. Push one PR to v2-live-radar.
8. Deploy to dev first, verify new metrics populate, then connector QA. Keep production untouched and keep current poll intervals, concurrency, source flags and notification settings unchanged.

## Non-goals
- Do not tune poll cadence, concurrency or rate budgets yet.
- Do not change collector behavior or data normalization.
- Do not add UI.
- Do not trigger extra live polls just to produce more benchmark data.
- Do not activate any disabled source or send test notifications.
