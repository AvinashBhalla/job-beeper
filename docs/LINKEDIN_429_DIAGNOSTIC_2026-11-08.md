# LinkedIn HTTP 429 diagnostic and conservative backoff — 2026-11-08

## Scope and evidence source

This is a read-only diagnostic of the currently running production container v2-radar-1 and its persisted SQLite data. No source request, config update, container restart or deployment was performed.

Production runtime config snapshot:
- LinkedIn enabled: true
- Naukri enabled: true
- Instahyre and Greenhouse disabled
- LinkedIn nominal poll target: 180 seconds

Shared development runtime has LinkedIn disabled and Naukri enabled. Its SQLite database contains no LinkedIn runs.

## Last-24-hour production observation

Window: the container's last 24 hours of retained logs at 2026-11-08 UTC.

- 298 LinkedIn discovery scan summaries.
- 643 request attempts reported by the discovery-scan log counter.
- 24 failed requests reported inside those discovery scans (3.73% of that scan-level denominator); 24 scan batches stopped after HTTP 429.
- Three additional HTTP 429s occurred during LinkedIn JD detail enrichment, outside the scan's failed_requests counter.
- Total HTTP 429 warning events: **27**.
- Every warning had Retry-After=not-provided.
- Cooldown distribution: 5 events at 300 seconds, 2 at 600 seconds, 2 at 1,200 seconds, and 18 at the previous 1,800-second maximum.
- Maximum observed in-process streak: 18.
- The 27 event count is the direct HTTP 429 warning count. Do not calculate a single global HTTP 429 percentage from it: the scan-level attempt counter does not include all successful detail-enrichment HTTP requests, while the 3 enrichment 429s are logged separately.

The production SQLite source_runs table still has only the legacy columns (source, finished_at, jobs_seen, new_jobs); the new request-level metrics migration has not been deployed there. Persisted history showed 298 LinkedIn runs in the last 24 hours but cannot provide an HTTP-level denominator. This is why the above count comes from sanitized container log patterns rather than a dashboard aggregate.

The recurring pattern is clear: the existing 30-minute maximum cooldown was reached 18 times. Retrying after that ceiling often received another 429. This is evidence to wait longer; it is not evidence to increase request volume or evade the restriction.

## Conservative code-only backoff change prepared

Branch: fix/linkedin-429-longer-backoff-20261108, based on current v2-live-radar.

- Base fallback remains five minutes.
- Exponential fallback steps now grow as 5m, 10m, 20m, 40m, 80m, 160m, then cap at **4 hours**.
- Escalation no longer resets after one clean hour. It requires **24 hours without another 429** before returning to the five-minute initial fallback.
- A server-provided Retry-After remains authoritative when larger than the fallback.
- Existing global LinkedIn request serialization and batch stop-on-429 behavior remain unchanged.
- No request spacing, scan cadence, targets per scan, detail worker count, source enablement or credentials were changed.

The purpose is solely to reduce repeat probes during an apparent longer restriction. It does not bypass access controls or rate limits. No changes have been deployed to the running production container.

## Validation

- Focused LinkedIn cooldown tests: 5 passed, covering Retry-After, escalation across successful scans, four-hour cap, retaining the streak after one hour, and reset after 24 hours.
- Full V2 suite: **209 tests passed** in 76.9 seconds in the isolated Python 3.10 environment.
- Python compilation and git diff --check passed.
- GitHub CI is still required for this new branch before merging.

## Naukri relay publisher post-merge verification

Relay PR #4 was merged to the relay repository's main as 359df41c22f1dd5d696fedbd926d813692c28728.

The VM's existing five-minute systemd timer triggered workflow run 42445116273 at 2026-11-08 04:01:49 UTC. It completed successfully and published a 323-job snapshot at 2026-11-08T04:03:47.799190+00:00.

A read-only fetch of the public feed confirmed:
- count = 323 and actual jobs length = 323.
- All 323 records have relay_first_observed_at and relay_last_observed_at.
- All present first timestamps are less than or equal to last timestamps.
- For a pre-existing job, first-observed was migrated from the preceding feed timestamp 2026-11-08T03:58:33.003516+00:00, and last-observed advanced to 2026-11-08T04:03:47.799190+00:00.

This confirms the publisher change is live and the new feed schema is present. It does not assert that the migration baseline is the job's historic first discovery time.

## Outstanding operational caveat

The cooldown streak remains process-memory state. A production container restart resets the in-memory streak today. Persisting the LinkedIn breaker across restarts can be a separate small follow-up using the new source-run table; do not overcomplicate this first backoff correction. The production/shared-dev rollout of the updated consumer code still requires its own approval and canary plan.