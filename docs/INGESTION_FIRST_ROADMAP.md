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
- Commit 04c0605 is pushed to feat/source-observability-20261107 and PR #47 description is updated. PR #47 remains draft; no changes to shared dev 8001 or production 8000. GitHub V2 CI #1311 / run 42398484593 passed for implementation commit 04c0605e078fbc376fc0688def66d3d0b9c18d5a (dashboard syntax, focused 32 tests, full V2 suite 205 tests).


## 2026-11-08 — Relay scheduler verified; publisher metadata and product discovery scope

- Confirmed the relay workflow on its default branch is manual-dispatch only; the VM systemd timer dispatches every five minutes. The latest 15 successful runs took 138–164 seconds end-to-end. Run #7599 completed all 18 query/location targets and produced 325 unique jobs. Keep the 15-minute staleness ceiling provisional but evidence-based (three five-minute cycles).
- The existing relay feed has a snapshot-level updated_at, count and full jobs list. A separate relay feature branch now adds fail-closed last-good retention on any failed target and per-job relay_first_observed_at / relay_last_observed_at. The V2 consumer is being updated to use these optional fields without losing compatibility with older feed records.
- Product readiness: public JobBeeper homepage promises 11 sources, role/location/experience/company preferences, Telegram/browser/app notifications, free job browsing and application tracking. The current repository is sufficient to build further; broad private-backend reverse engineering is not a blocker. Use targeted black-box acceptance checks only for signup, preferences validation/save, job search/details/save/application tracking, notification channels and plan gating. See docs/REVERSE_ENGINEERING_SCOPE.md.

## 2026-11-08 — Current PR/release gate status

- Source observability and Naukri consumer freshness are merged into v2-live-radar (PR #47, merge `dd4d21e`), with GitHub CI run `42442324585` passing the full 207-test suite and dashboard syntax. This is not a deployment.
- Matcher benchmark methodology note is merged (PR #41, merge `4e48836`); its deterministic runner and two tests were already in the V2 branch. 4/4 scored cases pass; one remains review-only.
- Keep user preferences PR #46 draft while the preferences-save frontend/backend validation issue and per-user Telegram live E2E remain open. OAuth sign-in and resume parser were confirmed by owner UAT.
- Relay publisher PR #4 is CI-green but remains draft because merging it changes the public feed on the VM's five-minute timer. Do not merge/dispatch without explicit owner approval.
- PR #35 is the WIP V2-to-main promotion gate; main/V2 divergence and production migration still need deliberate reconciliation.
- PR #37 and relay PR #3 were closed as superseded/deferred. See `docs/PR_BRANCH_AUDIT_2026-11-08.md` for exact branch cleanup.
## 2026-11-08 — Relay publisher live verification and next LinkedIn 429 work

- Relay publisher PR #4 is merged to relay main (359df41). The VM timer triggered run 42445116273 at 04:01:49 UTC; it published a 323-job feed at 04:03:47.799 UTC. All 323 feed entries contain relay first/last observation timestamps and satisfy first <= last.
- Read-only production evidence found 27 LinkedIn HTTP 429s in 24h, with 18 reaching the former 30-minute cooldown cap. Production has LinkedIn and Naukri enabled; shared dev has LinkedIn off.
- The production DB has not yet been migrated to request-level telemetry, so the 429 counts come from log analysis, not /api/source-status.
- Code-only backoff correction is prepared on fix/linkedin-429-longer-backoff-20261108: four-hour maximum fallback and 24-hour clean-window reset; honor any larger Retry-After; no increase in request rate/volume. Focused tests 5 passed and full V2 suite 209 passed locally. Run GitHub CI before merging. No deploy.
- See docs/LINKEDIN_429_DIAGNOSTIC_2026-11-08.md for evidence, denominator limitations and the production rollout boundary.