## Upsert experience extraction reuse — engineering checkpoint (2026-11-10)

### Root cause

PR #68 source-phase telemetry showed inconsistent upsert_duration_ms on repeated board polls. SQL plan checks showed the hot job lookup uses the unique (source, source_job_id) index, and canonical URL / company-location lookups use their indexes.

A cProfile replay against 827 existing Ashby jobs identified the dominant cost: upsert_jobs() called _experience_provenance_details() before checking whether a job already existed. The parser ran extract_jd_experience() and fallback extract_experience() over the same long description on every board poll, even when title and description were unchanged. In the profiled baseline, experience parsing consumed about 24.3 seconds of a 25.96-second replay; regex search/sub work dominated.

### Isolated A/B benchmark

- Online SQLite backup of Dev DB copied to a disposable folder.
- Each variant got an identical fresh copy of the same 56 MB snapshot.
- Reconstructed 827 existing Ashby observations from the copied DB; last-seen timestamps advanced as a normal re-poll would.
- No network requests, no new records, no live DB access during benchmark.
- Same container image/runtime and CPU/memory constraints.

| Replay | Five run times (seconds) | Median |
|---|---|---:|
| Baseline release 18f219d | 27.499, 17.488, 31.308, 21.588, 16.746 | 21.588 |
| Optimized worktree | 0.642, 0.377, 0.354, 0.611, 0.592 | 0.592 |

About 36.5x faster / 97.3% lower median upsert time for this unchanged-row, 827-job replay. This is a focused microbenchmark, not a production-wide SLA claim.

### Implementation branch

Branch: perf/reuse-stored-experience-on-upsert-20261110

- Defer experience extraction until after the job lookup.
- For an existing job, reuse persisted experience values if title, description and description format are unchanged and there is no new verified Gemini result.
- Re-run extraction whenever text/title changes, a parser version is stale, or fresh Gemini-verified experience values are supplied.
- New rows run extraction once after optional LinkedIn JD enrichment.
- Add migration-safe jobs.experience_extraction_version and EXPERIENCE_EXTRACTION_VERSION. Bump the constant whenever parser rules change; stale rows are re-extracted on their next normal source observation.
- Preserve experience confidence/provenance ranking, canonicalization, evaluation, notification-baseline handling and last_seen_at updates.

### Validation

- NaukriRelayFreshnessTests: 9/9 passed. Covers first insert, unchanged text, changed description, changed title, parser-version invalidation, fresh Gemini-verified results and stored output.
- Full V2 suite in dedicated CI-like test container with httpx2 2.16.0: 485 tests passed, 1 skipped, 0 failures (709.498 seconds).
- Extended legacy jobs-table migration test verifies experience_extraction_version is added and initialized to the current parser version. Migration test plus all 9 focused freshness tests: 10/10 passed.
- python compilation and git diff --check pass.
- No code deployment or config change has been made. Dev and Connector QA remain on image 18f219d.

### Next steps

1. Commit/push and open PR to v2-live-radar; require exact-head GitHub V2 CI.
2. Do not deploy until green and reviewed. If merged, deploy Dev first and observe naturally scheduled polls; compare upsert timings before considering further optimization.
3. Do not change polling cadence, concurrency, rate limits, source flags, notifications or production during this task.
