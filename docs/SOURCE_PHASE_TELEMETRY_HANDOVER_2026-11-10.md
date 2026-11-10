

## Follow-up finding — board-scoped config invalidated every evaluation (2026-11-10)

Natural post-deploy phase timings exposed a second, more important issue than collector latency. In dev over the first hour of telemetry:
- Ashby 7 runs: evaluation phase median about 52.8s; request duration median about 1.4s.
- Greenhouse 11 runs: evaluation phase median about 47.2s; request duration median about 1.2s.
- Multiple Ashby/Greenhouse evaluations exceeded 60–100 seconds.
- Some upsert phases also spiked (for example, Ashby 75.3s and Keka 79.7s); these appear to include SQLite writer contention while other source jobs are active.

A read-only config-fingerprint audit showed dev had 10,815 jobs and 10,815 evaluations, but all 10,815 stored fingerprints differed from the global config fingerprint. QA had 2,400 jobs/evaluations and zero mismatches at the instant of that audit.

Code-path inspection found the cause: the durable board scheduler creates a scoped config for one board by replacing the provider's board list, then passes that scoped config to run_source(). _config_fingerprint() currently hashes the entire config, including per-board source configuration, poll intervals and source flags. refresh_job_evaluations() therefore treats all existing jobs as stale whenever a board-scoped poll runs and re-evaluates the complete inventory.

### Fix in progress
- Fingerprint only the configuration fields actually used by match_details() and alertability_details(): target roles, skills, locations, title exclusions, excluded role terms, remote-only, experience constraints, match threshold and notification-enabled state.
- Keep MATCHER_RULES_VERSION in the fingerprint so intentional matcher-rule changes still trigger re-evaluation.
- Add tests proving board lists, source flags and poll cadence do not invalidate evaluations, while matcher/alertability setting changes do.
- This creates a one-time fingerprint migration/re-evaluation of the existing inventory, then makes subsequent board-specific runs stable. Do not manually trigger that re-evaluation; let the ordinary run perform it once and verify the fingerprint mismatch count returns to zero.
- No source cadence, concurrency, collector, notifications or production config changes.
