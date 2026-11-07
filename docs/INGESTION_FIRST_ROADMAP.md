# Ingestion-First Roadmap

**Updated:** 2026-11-07  
**Priority:** P0 — reliable, fresh, broad job ingestion  
**Primary branch:** `v2-live-radar`  
**Current implementation branch:** `feat/source-observability-20261107`

**Draft PR:** [#47](https://github.com/AvinashBhalla/job-beeper/pull/47) — V2 CI #1303 passed (196 tests on Python 3.12).

## Product priority

The primary product promise is fresh, useful job discovery. Jobs should enter the portal promptly after a source makes them available, with trustworthy source identity, timestamps, deduplication and visible source health. User signup, resume parsing and Telegram delivery are downstream of reliable shared ingestion.

## Current foundation

The collector registry contains LinkedIn, Naukri, Instahyre, Greenhouse and Ashby adapters. A registry entry does not mean the source is enabled or globally searchable. Runtime enablement must be verified from the running environment's configuration and source status; never infer it from code.

The source-observability branch now adds backward-compatible run-level and request-level telemetry:

- unique run ID, run outcome and monotonic run duration;
- sanitized error type/text, HTTP status, Retry-After and full applied cooldown duration;
- physical request attempts/responses/exceptions, status-class totals, HTTP 429 count and exact status histogram;
- retry attempts for existing collector retries and aggregate HTTP request duration;
- logical search/feed page counts and Greenhouse/Ashby employer-board counts;
- `partial_rate_limited` and `partial_failed` outcomes when usable data is returned alongside failures;
- latest-run and rolling 24-hour summaries through admin-only `/api/source-status`.

Existing source-run history is preserved by additive SQLite migration; historical metrics remain NULL and are reported as unmeasured. No collector cadence, retry behavior, source enablement or notification behavior was changed. See `docs/SOURCE_LEVEL_METRICS.md` for the complete contract.

## Priority sequence

1. **P0 — Complete source observability.** Add request/page counts, status-class histograms, retries, time in cooldown, partial-board outcomes, last successful fetch and last new job. Keep telemetry sanitized and avoid logging job descriptions or credentials.
2. **P0 — Diagnose LinkedIn 429s.** Use observed request cadence, target overlap, enrichment calls and cooldown history. Reduce unnecessary pressure or prefer a permitted structured source. Never use proxy rotation, identity rotation or rate-limit evasion.
3. **P0 — Make Naukri freshness measurable.** Track relay collection time separately from original posting date, preserve last-good feed, reduce repeated full-snapshot work where safe, and measure workflow duration and main-app poll lag. Date-only posting dates must not be treated as exact timestamps.
4. **P1 — Validate source adapters individually.** Keep Instahyre disabled until its HTTP 400/schema issue is diagnosed. Canary Greenhouse/Ashby against a small, relevant employer-board allowlist. Verify public/authorized Lever and SmartRecruiters contracts before implementing them.
5. **P1 — Build a measured source catalog.** Track official endpoint/terms, employer-board requirements, authentication, pagination, stable IDs, canonical apply URL, timestamp precision, request budgets, retry policy, unique-job yield, freshness and failure rate. Report adapters separately from configured employer boards.
6. **P2 — Validate coverage and latency.** Use 24–72-hour canaries where practical. Expand toward 100 useful integrations only when unique relevant job yield, freshness and reliability justify the maintenance cost.
7. **P3 — Resume downstream product work.** Continue user preferences, resume onboarding and per-user Telegram in the separate feature branch. Keep PR #46 draft and isolated until ingestion release gates pass and promotion is explicitly approved.

## Adapter and release gates

Every adapter should have a stable source ID, canonical application URL, explicit timestamp precision, bounded pagination/request budget, timeouts, classified errors, safe backoff and isolated failure handling. The pipeline remains:

`fetch -> validate -> normalize -> canonicalize -> deduplicate -> persist -> evaluate -> expose`

Before production enablement, require permitted access, deterministic fixtures/tests, timestamp semantics, simulated 429/Retry-After coverage, a dev/canary observation window, useful unique-job yield, source-health visibility and a rollback/disable switch.

## Current next action

Review draft PR #47 and merge into `v2-live-radar` only after human review/approval. Latest request-level implementation CI #1307 (`42391947214`) passed on Python 3.12/modern Node: focused tests 32 passed and full V2 suite 199 passed. A local preview is available on isolated port 8003 with synthetic rows and all collectors disabled. After review, the next metric slice is durable last-success/last-new-job and Naukri relay freshness telemetry. The older telemetry PR #40 is closed unmerged as superseded by #47.


## 2026-11-07 — Naukri feed freshness and repeated evaluation reduction (local branch)

- Public relay JSON was inspected read-only: top-level updated_at, count, and a full jobs array. The inspected snapshot had 322 jobs. Job records have IDs/URLs and date-only posted values, but no per-job relay-observed timestamp.
- Naukri consumer changes are implemented locally on feat/source-observability-20261107: reject malformed, empty, count-mismatched, stale (>15 minutes) or implausibly future snapshots; preserve last-known-good feed metadata; persist content hash/count/age/observed time; expose freshness and unchanged-content state in admin Source Health; skip repeated matcher evaluation when stored job evaluation inputs did not change.
- The 15-minute threshold is provisional (three nominal five-minute relay intervals), not a measured SLA. Actual workflow cadence and completion timing still need verification.
- The full feed is still fetched and parsed on every poll. True per-job incremental ingestion requires publisher-side per-item observed/updated timestamps or a supported cursor/conditional-fetch contract. Never infer exact discovery time from date-only posted values.
- Validation on the isolated Python 3.10 environment: full V2 suite 205 passed. Node 12 on the VM is too old for the dashboard syntax already present; final JavaScript syntax check must be confirmed by GitHub CI.
- Commit 04c0605 is pushed to feat/source-observability-20261107 and PR #47 description is updated. PR #47 remains draft; no changes to shared dev 8001 or production 8000. CI status for this head was not yet returned at the time of this note.
