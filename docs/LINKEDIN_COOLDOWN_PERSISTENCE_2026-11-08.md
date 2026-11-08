# Persist LinkedIn 429 cooldown state across restarts — 2026-11-08

**Branch:** `fix/linkedin-cooldown-persistence-20261108`  
**Base:** `v2-live-radar`  
**Status:** implemented and locally validated; not deployed.

## Why

The longer conservative backoff (PR #48, merged as `5b4b2fa`) keeps a 4-hour cap and 24-hour escalation streak while a process is alive. Before this follow-up, both the active cooldown deadline and escalation streak lived only in module globals. A container restart could therefore erase an active cooldown and restart the escalation ladder.

## Persistence design

An additive nullable `source_runs.rate_limit_detected_at` column stores the UTC instant at which the LinkedIn server returned an actual HTTP 429. The normal `http_status`, `cooldown_seconds` and `retry_after_seconds` columns continue to store the response classification and applied delay. Existing source-run history and all other fields are preserved.

Both successful/partial runs that observed a 429 and failed runs caused by a 429 persist the detection timestamp. Cooldown-blocked attempts that did not make a new HTTP request are not counted as another 429 event.

At startup, after `init_db()` has run additive migrations and before the scheduler starts, the app:
1. Reads LinkedIn source runs with `http_status=429` and a detection time in the preceding 24 hours.
2. Reconstructs the escalation streak from those recorded 429 events.
3. Reconstructs the most recent event's active cooldown using its stored `cooldown_seconds` minus elapsed wall-clock time, then maps that remaining duration onto the current process's monotonic clock.
4. Restores the last detection timestamp, applied cooldown, and server `Retry-After` metadata into in-memory source state.
5. Retains the escalation streak even when the latest cooldown has expired; it resets only after a full 24-hour window without a 429.

For old rows created before this column existed, the migration leaves the new field NULL and the restore query uses `finished_at` as a coarse fallback. This is a compatibility fallback, not an exact historical detection timestamp.

A small index on `(source, http_status, rate_limit_detected_at)` supports the startup lookup.

## Rollout limitation

The currently running production SQLite database was read-only inspected before this change and still has the older `source_runs` schema with no HTTP status fields. Its 27 recent 429s were observable in container logs but are not present as structured 429 rows in that old database. The additive migration cannot backfill events from container logs. Therefore the first deployment of this code will start with an empty persisted breaker history on that database; persistence will protect subsequent restarts after new code records fresh 429 events.

This change has not been deployed. No container, source schedule, request spacing, scan target count, detail worker count, source enablement, credentials or notification behavior was changed during implementation.

## Validation

- Focused persistence/migration/integration tests: **9 passed**.
- Full V2 suite: **215 passed** in 81.413 seconds in the isolated Python 3.10 environment.
- Coverage includes detection-time persistence, successful and failed run persistence, active cooldown restoration, expired-but-escalating streak restoration, reset after 24 hours, Naukri isolation, legacy-row fallback, and additive migration with old data preservation.
- Python compilation and `git diff --check` passed locally. GitHub CI is required before merge.