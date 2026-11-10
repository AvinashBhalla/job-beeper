

## Follow-up finding — board-scoped config invalidated every evaluation (2026-11-10)

Natural post-deploy phase timings exposed a second, more important issue than collector latency. In dev over the first hour of telemetry:
- Ashby 7 runs: evaluation phase median about 52.8s; request duration median about 1.4s.
- Greenhouse 11 runs: evaluation phase median about 47.2s; request duration median about 1.2s.
- Multiple Ashby/Greenhouse evaluations exceeded 60–100 seconds.
- Some upsert phases also spiked (for example, Ashby 75.3s and Keka 79.7s); these appear to include SQLite writer contention while other source jobs are active.

A read-only config-fingerprint audit showed dev had 10,815 jobs and 10,815 evaluations, but all 10,815 stored fingerprints differed from the global config fingerprint. QA had 2,400 jobs/evaluations and zero mismatches at the instant of that audit.

Code-path inspection found the cause: the durable board scheduler creates a scoped config for one board by replacing the provider's board list, then passes that scoped config to run_source(). _config_fingerprint() currently hashes the entire config, including per-board source configuration, poll intervals and source flags. refresh_job_evaluations() therefore treats all existing jobs as stale whenever a board-scoped poll runs and re-evaluates the complete inventory.

### Fix merged and deployed — 2026-11-10
- Fingerprint only the configuration fields actually used by match_details() and alertability_details(): target roles, skills, locations, title exclusions, excluded role terms, remote-only, experience constraints, match threshold and notification-enabled state.
- Keep MATCHER_RULES_VERSION in the fingerprint so intentional matcher-rule changes still trigger re-evaluation.
- Added regression tests proving board lists, source flags and poll cadence do not invalidate evaluations, while matcher/alertability setting changes do.
- This created a one-time fingerprint migration/re-evaluation of the existing inventory. The fix is merged in PR #69 and deployed to Dev and Connector QA as image job-radar-dev-multitenant:18f219d. Both environments now report zero fingerprint mismatches after the ordinary startup/run path. No manual refresh was triggered.
- No source cadence, concurrency, collector, notifications or production config changes.


## Rollout outcome — 2026-11-10 14:43 IST

- Merge: PR #69, commit 18f219dfab4ad6f2c5ad9b9704da5d3a220f7d37.
- Same image deployed to Dev 8001 and Connector QA 8010: job-radar-dev-multitenant:18f219d, image ID sha256:86693f94cf64db076ae79222ca4cf6a05a62c0b4b3fa0be0b6b09444077397d5.
- Both health endpoints HTTP 200, container restarts 0, DB integrity ok, jobs/evaluations equal, zero fingerprint mismatches, 10/10 active board rows in success state and zero sent notifications.
- Anonymous scheduler status and source status endpoints both return HTTP 401 in each environment.
- Dev natural post-deploy sample: 15 successful source runs since rollout; evaluation phases now generally around 0.1–1.4 seconds. Ashby/Greenhouse examples fell from repeated 40–160 second evaluations to sub-second phases. This is promising early telemetry, not a controlled benchmark.
- Upsert remains variable; Ashby reached 16.32 seconds in the early post-deploy sample. Do not change concurrency or SQL write behavior until more natural samples and lock-wait evidence are collected.
- Connector QA cadence is 60 minutes. At the verification point, only one post-deploy source run was recorded and the 10 boards' prior successful states remained. Wait for each board's natural next run; do not manually poll.
- Owner visual QA is pending. Run docs/DEV_DESKTOP_QA_PROMPT_2026-11-10.md; rollout details are in docs/RELEASE_ROLLOUT_EVAL_FINGERPRINT_2026-11-10.md.
- Production was not changed.
