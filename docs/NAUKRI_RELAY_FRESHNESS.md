# Naukri relay freshness and repeat-ingestion behavior

**Status:** Implemented locally on feat/source-observability-20261107; not merged or deployed.

## Observed feed contract

A read-only inspection of the public relay JSON on 2026-11-07 found these top-level fields:

- updated_at: one timestamp for the entire generated feed snapshot.
- count: total number of entries in jobs.
- jobs: a full snapshot, with stable id and url fields and a date-like posted value.

At the time of inspection, the snapshot contained 322 jobs. The job objects did not contain a per-job relay-observed timestamp. The top-level updated_at is therefore a feed-build/relay timestamp, not the employer's exact publication time and not an exact per-job discovery time.

## Consumer changes

The Naukri collector now validates the snapshot before accepting it:

- JSON root must be an object; jobs must be a non-empty list.
- When count is present, it must parse as an integer and match the list length.
- updated_at must be parseable.
- A timestamp more than five minutes in the future is rejected.
- A snapshot older than 15 minutes is rejected. This is a provisional threshold set to three nominal five-minute relay intervals; it must be revisited after measuring actual publisher cadence and workflow completion times.
- At least one valid job with a stable ID and URL must remain after normalization.

A rejected snapshot raises a failed source run. It does not update source_feed_state, upsert any jobs from that snapshot, or erase existing job rows. The last accepted feed metadata remains available for diagnosis.

The additive source_feed_state table stores only:

- relay updated_at;
- the consumer's last_observed_at;
- relay age at the last poll;
- accepted normalized job count;
- SHA-256 hash of the job snapshot;
- whether the job snapshot content was unchanged from the preceding accepted snapshot.

The snapshot hash excludes the changing top-level timestamp, so a newly generated snapshot containing the same job records can be identified as unchanged. It does not store job content, URLs, descriptions or credentials.

Repeated job observations still update last_seen_at. Existing job evaluations are recomputed only when matcher-relevant persisted inputs (description, description format, source-posted timestamp or precision) actually change. This avoids repeating expensive evaluation work for identical job data.

Admin GET /api/source-status now returns last_feed for Naukri, including current age, age at last poll, count, freshness status and unchanged-snapshot indicator. The Source Health dashboard surfaces this alongside the ordinary source metrics.

## What this does not do

- It does not turn the full snapshot into a cursor-based or per-job incremental endpoint. The current consumer still downloads and parses the entire JSON snapshot.
- It does not provide an exact per-job relay-observed timestamp. That requires the relay publisher to add a per-item field such as first_seen_at / observed_at, ideally with stable semantics and a versioned schema.
- It does not make the source real-time. Publisher schedule, job-board publication delay and feed update lag remain distinct.
- It does not infer precise publication time from date-only posted values. Naukri discovery-latency remains unknown for date-only records.
- It does not alter poll frequency, retries, source enablement, or notification behavior.

## Follow-up

1. Inspect the relay workflow's actual schedule and recent start/completion times; distinguish scheduled time, manual workflow-dispatch time and successful feed publication time.
2. Add per-job relay observation metadata at the publisher, preserving backward compatibility and explicit timestamp precision.
3. Consider conditional HTTP requests (ETag/Last-Modified) only if the GitHub raw-content host exposes dependable validators; retain a safe cache-busting path where required.
4. Reassess the 15-minute consumer freshness ceiling using measured publisher completion latency and actual relay failure patterns.
5. Measure unique and newly relevant jobs per relay run before expanding query families or increasing poll pressure.

## Validation

- Naukri tests cover stale/empty/count-mismatched snapshots, last-good state preservation, same-content snapshots with a newer relay timestamp, source-health reporting, date-only timestamp precision and repeat-upsert evaluation avoidance.
- Full V2 suite: 205 tests passed on the isolated Python 3.10 test environment.
- python -m compileall -q v2 and git diff --check passed.
- The VM's system Node is v12.22.9, below the syntax level already used by the dashboard; the dashboard was therefore checked with esbuild 0.25.12 locally. GitHub V2 CI #1311 / run 42398484593 passed for implementation commit 04c0605e078fbc376fc0688def66d3d0b9c18d5a: dashboard JavaScript syntax passed, focused router/extractor tests 32 passed, and full V2 suite 205 passed in 15.336 seconds.
- This implementation has not been deployed to port 8003, shared dev (8001) or production (8000).
