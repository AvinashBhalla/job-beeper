# Source performance benchmark — 2026-11-10

## Scope and method

Read-only snapshot from the live shared-dev and connector-QA SQLite databases after deploying image 5d6e2b4. The report uses completed rows in source_runs whose started_at fell within the previous 24 hours (and a 7-day comparison for dev). No collectors were manually triggered for this report.

- Run success/failure is derived from outcome.
- Runtime p50/p95 is duration_seconds per source run.
- Request-total p50 is the median of request_duration_ms_total per run. It is not per-request latency.
- New-job yield is new_jobs / jobs_seen; it is not a posting-to-alert freshness measurement and can be distorted by initial inventory/baseline runs.
- QA has only 132 source-run records in its retained DB history, all within the 24-hour window; therefore its 7-day result is identical to its 24-hour result.
- These are shared environment operational metrics, not a production SLA or a claim of full platform coverage.

## Shared dev — previous 24 hours

| Source | Runs | Success | 429s | Jobs seen | New jobs | Runtime p50 / p95 (s) |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 61 | 61 | 0 | 48,010 | 28 | 89.65 / 242.40 |
| Darwinbox | 59 | 59 | 0 | 2,097 | 36 | 15.58 / 53.20 |
| Greenhouse | 63 | 63 | 0 | 21,324 | 6 | 65.05 / 190.47 |
| Keka | 58 | 58 | 0 | 6,322 | 109 | 22.38 / 135.60 |
| Naukri | 172 | 172 | 0 | 37,002 | 261 | 5.77 / 39.89 |
| SmartRecruiters | 30 | 30 | 0 | 9,000 | 352 | 37.54 / 167.29 |
| Workable | 58 | 58 | 0 | 348 | 6 | 9.49 / 80.33 |
| Workday | 57 | 57 | 0 | 1,520 | 431 | 70.58 / 127.81 |
| **Total** | **558** | **558** | **0** | **125,523** | **1,229** | — |

## Shared dev — previous 7 days

| Source | Runs | Success | 429s | Jobs seen | New jobs | Runtime p50 / p95 (s) |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 64 | 64 | 0 | 49,659 | 883 | 88.69 / 242.38 |
| Darwinbox | 59 | 59 | 0 | 2,097 | 36 | 15.58 / 53.20 |
| Greenhouse | 64 | 64 | 0 | 21,693 | 375 | 64.60 / 190.47 |
| Instahyre | 1 | 1 | 0 | 140 | 140 | 3.09 / 3.09 |
| Keka | 58 | 58 | 0 | 6,322 | 109 | 22.38 / 135.60 |
| Lever | 1 | 1 | 0 | 500 | 500 | 50.12 / 50.12 |
| LinkedIn | 1 | 1 | 0 | 10 | 10 | 22.92 / 22.92 |
| Naukri | 1,903 | 1,903 | 0 | 594,754 | 1,244 | 6.08 / 33.01 |
| SmartRecruiters | 30 | 30 | 0 | 9,000 | 352 | 37.54 / 167.29 |
| Workable | 58 | 58 | 0 | 348 | 6 | 9.49 / 80.33 |
| Workday | 57 | 57 | 0 | 1,520 | 431 | 70.58 / 127.81 |
| **Total** | **2,296** | **2,296** | **0** | **689,503** | **4,086** | — |

The one-off Instahyre, Lever and LinkedIn rows are controlled probes/ingestions, not evidence that those sources are enabled in the recurring scheduler.

## Connector QA — retained previous 24 hours

| Source | Runs | Success | 429s | Jobs seen | New jobs | Runtime p50 / p95 (s) |
|---|---:|---:|---:|---:|---:|---:|
| Ashby | 17 | 17 | 0 | 13,244 | 846 | 80.15 / 111.58 |
| Darwinbox | 16 | 16 | 0 | 569 | 36 | 17.46 / 30.42 |
| Greenhouse | 18 | 18 | 0 | 5,902 | 373 | 61.17 / 112.19 |
| Keka | 16 | 16 | 0 | 1,744 | 109 | 21.49 / 105.30 |
| Naukri | 17 | 17 | 0 | 3,404 | 283 | 15.49 / 114.51 |
| SmartRecruiters | 16 | 16 | 0 | 4,799 | 350 | 66.54 / 100.11 |
| Workable | 16 | 16 | 0 | 96 | 6 | 7.12 / 19.01 |
| Workday | 16 | 16 | 0 | 597 | 325 | 67.46 / 96.85 |
| **Total** | **132** | **132** | **0** | **30,355** | **2,328** | — |

QA uses its intended 60-minute polling cadence; dev uses shorter provider-specific intervals. Both environments had all 10 active board schedules in successful state at the verification point.

## Findings

1. No observed 429s or failed source runs in these windows. This is not a reason to raise concurrency automatically; the current host budgets and cadences should remain in place.
2. Ashby and Greenhouse have the largest dev p95 runtime (242s and 190s). Their request totals and runtime need phase-level tracing before changing their polling schedule.
3. SmartRecruiters has the largest multi-request volume (690 requests across 30 dev runs) and a 167s dev p95. Inspect pagination/detail fetch behaviour and response timing.
4. Workday is expensive but productive: 1,520 seen / 431 new in dev over 24h, with 1,219 requests across 57 runs and no recorded 429. This is a high-yield source, so do not reduce its coverage blindly.
5. Keka and Darwinbox are stable on their current live tenants: 58/58 and 59/59 dev runs succeeded respectively, with zero 429s. Non-default Keka portal support exists in code/tests, but the configured live Keka tenant is the default Bridgestone portal.
6. New-job counts are affected by first inventory and baseline state. Do not use the initial QA new-job totals as a recurring yield estimate.

## Next engineering task

Profile slow source runs before tuning the scheduler:
- add or expose phase timings for fetch, parse/normalize, detail enrichment and database upsert;
- capture per-request latency distributions rather than only the per-run request-duration sum;
- start with Ashby and Greenhouse, then SmartRecruiters;
- keep provider intervals, concurrency limits and notifications unchanged during measurement;
- use existing tests and exact-head V2 CI; no UI work is required.

Workday facet partitioning, Keka non-default portal parsing/collection and Darwinbox collection are already present in the current integration code with focused tests. The remaining live-validation gaps are: a Workday tenant that actually reaches the 2,000-result cap, a real non-default Keka portal, and broader tenant coverage. Do not claim those cases are validated by the current NVIDIA/Bridgestone/Arvind live boards.


## Telemetry follow-up after PR #68 deployment (same day)

PR #68 merged as 1763673 and its image was deployed to shared dev and connector QA. New metrics are now available; historical rows remain NULL for newly introduced phase fields.

First observed post-deploy examples (not statistically sufficient for new p50/p95 estimates):
- Dev SmartRecruiters: 23 requests; request min/max about 482/2,400 ms; collector 19.39s; shadow 0.21s; upsert 0.99s; evaluation 0.71s; notification 0.78s.
- Dev Naukri: one request about 2.99s; collector 3.10s; shadow 1.91s; upsert 2.08s; evaluation 0.095s; notification 0.80s.
- Connector QA Naukri: one request about 0.28s; collector 0.50s; shadow 1.08s; upsert 1.89s; evaluation 0.002s; notification 0.092s.

The collector phase includes request time plus parsing/normalization and any source-specific work. The current metrics do not split parser/detail enrichment separately. New request min/max and latency buckets help distinguish network waits from non-network collector cost, but phase timing must be collected for Ashby and Greenhouse before drawing conclusions about their slow baseline runs. Do not tune cadence or concurrency based on the small sample above.


## Root cause and corrective implementation — 2026-11-10

The first-hour phase sample showed dev Ashby evaluation median about 52.8s (7 runs) and Greenhouse evaluation median about 47.2s (11 runs), while their median request durations were about 1.4s and 1.2s respectively. Dev had 10,815 jobs and evaluations, and all 10,815 stored evaluation fingerprints differed from the global runtime fingerprint.

Cause: the per-board scheduler passes a scoped configuration to the collector. The old `_config_fingerprint()` hashed the entire configuration, including board lists, source flags and poll cadence. Each board run therefore invalidated the full shared evaluation inventory.

Corrective change on branch `fix/stable-evaluation-fingerprint-20261110`:
- Fingerprint only the evaluation inputs read by `match_details()` and `alertability_details()` (roles, skills, locations, exclusions, remote-only, experience constraints, match threshold and notification-enabled state), plus `MATCHER_RULES_VERSION`.
- Board configuration, source enablement, cadence and concurrency no longer invalidate persisted evaluations.
- Added regression tests that operational/board-only changes preserve the fingerprint, while each evaluation input and matcher-rules version changes it.
- Focused fingerprint regression tests pass 3/3; full matcher test class passes 97/97. GitHub V2 CI run `42782187621` on code head `4092b22e847e3ebc8ac096a35a4eb6b8f7dba2b8` passed, including the full V2 unittest suite.

Expected rollout behavior: because the old persisted fingerprint scheme differs, the first normal run after this code is deployed will re-evaluate the inventory once. After that migration completes, board-scoped runs should not repeatedly re-evaluate all existing jobs. Do not manually invoke a full refresh or change scheduler cadence/concurrency. Verify the mismatch count reaches zero and stays zero over subsequent naturally scheduled board runs.
