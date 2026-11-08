# Naukri relay freshness and repeat-ingestion behavior

**Status:** Consumer implementation pushed to the draft JobBeeper PR #47; publisher changes prepared separately on a draft branch in the public relay repository. Not merged or deployed.

## Observed feed and scheduler contract

The public relay JSON exposes top-level `updated_at`, `count`, and a full `jobs` array. At initial inspection on 2026-11-07, the snapshot contained 322 jobs; a later successful run produced 325. Job records had stable IDs/URLs and a date-like `posted` value, but no per-job relay-observed timestamp.

The active publisher workflow in `AvinashBhalla/job-beeper-naukri-relay` is `workflow_dispatch` only; it has no GitHub `schedule` trigger. The VM's `job-radar-naukri-relay.timer` dispatches it every five minutes (`OnUnitActiveSec=5min`). Do not change this timer as part of consumer work.

A read-only sample of the latest 15 successful runs on 2026-11-07 showed end-to-end durations from 138 to 164 seconds. Run #7599 took 154 seconds; its collector step scanned 18 configured query/location targets with all 18 successful and produced 325 unique jobs. This supports a conservative 15-minute consumer freshness ceiling (three nominal 5-minute dispatch intervals), but the threshold remains provisional and should be reassessed from ongoing operational data.

## Publisher hardening and per-job timestamps

A separate relay-repository feature branch is being prepared to:
- Load the last successfully published `naukri-relay` branch snapshot before collecting.
- Fail closed if fetching/parsing the last-good snapshot fails, rather than silently resetting first-seen metadata.
- Preserve the previous complete snapshot when any configured query/location target fails; do not publish a partial feed.
- Add `relay_first_observed_at` and `relay_last_observed_at` to each published job.
- Preserve a job's existing first-observed timestamp by stable ID, with URL fallback. For pre-existing records that predate this schema, the previous feed-level `updated_at` is used as a migration baseline. This is not a claim about the job's true historic first-seen time.
- Set each job's last-observed timestamp on every successful complete run.

The fields represent when the relay first/last observed the listing, not when the employer posted it. Date-only `posted` values still cannot support exact publication latency.

## Consumer changes

The V2 consumer:
- Requires a JSON object, a non-empty jobs list, a parseable top-level timestamp, count consistency when count is supplied, and at least one valid normalized job.
- Rejects snapshots more than five minutes in the future or older than 15 minutes.
- Does not replace last-good feed metadata or upsert listings from rejected snapshots.
- Persists safe feed metadata in additive `source_feed_state`: relay timestamp, app observation timestamp, age, accepted normalized count, SHA-256 content hash and unchanged-content indicator.
- Hashes job content independently of job order and excludes volatile `relay_last_observed_at`, so a fresh relay run containing the same jobs is detectable as unchanged.
- Consumes the optional per-job relay first/last observation fields. Older snapshots fall back to the snapshot timestamp.
- Keeps job `discovered_at` / `first_seen_at` stable and advances job/canonical `last_seen_at` monotonically.
- Skips expensive matcher re-evaluation when the persisted matching inputs did not change, while still updating last-seen metadata.

Admin `GET /api/source-status` returns `last_feed` for Naukri (age, age at poll, job count, freshness and unchanged snapshot). The Source Health dashboard displays the last accepted relay status.

## What this does not do

- The consumer still downloads and parses the full JSON snapshot every poll. This is not cursor-based or per-job incremental fetching.
- It does not infer precise publication time or latency from date-only posting labels.
- It does not change source polling cadence, source enablement, retry policy, notifications or provider request pressure.
- The 15-minute maximum age is a provisional safety threshold, not a formal SLA.

## Follow-up

1. Merge and validate the relay-publisher change only after its independent CI passes; confirm a published feed includes the two optional per-job timestamps.
2. Observe failed target frequency and feed age for several days before adjusting the 15-minute cutoff.
3. Consider ETag/Last-Modified only if the raw-content host exposes dependable validators.
4. Measure new/unique/relevant yield over time before changing search targets or expanding source coverage.

## Validation

- Consumer regression tests cover stale/empty/count-mismatched snapshots, last-good state retention, future timestamps, same-content snapshots with changing relay timestamps/order, feed health, per-job first/last observation import, monotonic last-seen persistence and matcher re-evaluation avoidance.
- Full V2 suite after per-job timestamp integration: **207 tests passed** locally on the isolated Python 3.10 environment.
- Python compileall, dashboard build using esbuild 0.25.12 and `git diff --check` passed locally.
- GitHub V2 CI #1311 / run 42398484593 passed on the earlier consumer implementation commit 04c0605: dashboard JavaScript syntax, focused router/extractor tests 32 passed, and full V2 suite 205 passed. The newer per-job timestamp integration still needs a fresh GitHub CI run after push.
- No deployment to the 8003 preview, shared dev 8001 or production 8000 has been made.
