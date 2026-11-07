# Ingestion-First Roadmap

**Updated:** 2026-11-07  
**Priority:** P0 — reliable, fresh, broad job ingestion  
**Primary branch:** `v2-live-radar`  
**Current implementation branch:** `feat/source-observability-20261107`

## Product priority

The primary product promise is fresh, useful job discovery. Jobs should enter the portal promptly after a source makes them available, with trustworthy source identity, timestamps, deduplication and visible source health. User signup, resume parsing and Telegram delivery are downstream of reliable shared ingestion.

## Current foundation

The collector registry contains LinkedIn, Naukri, Instahyre, Greenhouse and Ashby adapters. A registry entry does not mean the source is enabled or globally searchable. Runtime enablement must be verified from the running environment's configuration and source status; never infer it from code.

The source-run observability branch adds backward-compatible run-level telemetry:

- unique run ID and run outcome;
- monotonic run duration;
- sanitized error type/text and HTTP status;
- Retry-After and full applied cooldown duration;
- explicit `partial_rate_limited` outcome when LinkedIn returns some jobs but a 429 interrupts the scan;
- admin-only visibility through `/api/source-status`.

Existing source-run history is preserved by additive SQLite migration. Collector request behavior and source enablement are unchanged by this work.

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

Push `feat/source-observability-20261107`, open a draft PR against `v2-live-radar`, and require GitHub CI to pass. Then add request/page-level telemetry before tuning collection cadence or adding more sources.
