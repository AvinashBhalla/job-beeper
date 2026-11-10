# Persistent per-board ATS scheduler — 2026-11-09

## Status

Implementation is in the isolated branch `feat/per-board-scheduler-20261109`, based on the current global-discovery branch `feat/global-ats-discovery-hirebase-guard-20261109` at `751e9d2077f9cc2c9f01e0488f189af9938b78f3`. It is intentionally a stacked change: review/merge the global-discovery foundation first, then this scheduler PR. The work is not deployed to the running dev, connector-QA, synthetic-QA or production containers.

## Why this change

The previous `scheduler()` kept provider-level monotonic due times in process memory. It scheduled an entire provider allowlist in one run, reset due times on application restart, and could not expose which employer board was due, delayed, failing or cooling down. A failure on one board could also be mixed with the results of every other board for that provider.

## Implementation

### Persistent state

New module: `v2/board_scheduler.py`.

Two additive SQLite tables are created by `init_db()`:

- `ats_board_poll_schedule`: one row per explicitly enabled source + board key, including normalized board config, registry ID, host key, configured interval, due time, last outcome, run counts, error type, failure streak, baseline state and expiring lease.
- `ats_board_host_poll_state`: one row per request host, including minimum next-allowed time, 429 cooldown, active host lease, last outcome and 429 count.

Existing job, canonical-opportunity, notification and source-run rows are not migrated or deleted by this change.

### Scheduling and safety limits

- Only the existing explicit provider allowlists (`greenhouse_boards`, `ashby_boards`, `lever_boards`, `workday_boards`, `smartrecruiters_boards`, `workable_boards`, `keka_boards`, `darwinbox_boards`) are scheduled, and only when that source is enabled. Discovered, unmatched or merely verified candidates remain unscheduled until the existing explicit activation flow adds them to an allowlist.
- Every employer board gets an independent persisted next-due timestamp. The `poll_seconds` value remains the source cadence and is applied to each board.
- A scheduled collector receives a scoped config containing exactly one board. `source_state` still guarantees at most one active run for a provider; SQLite host leases guarantee at most one active board per API host.
- Global cap: three concurrent API hosts. Per-host minimum spacing: five seconds after the previous board run completes. Host leases expire after 15 minutes to recover abandoned claims after a process crash.
- A normal collector failure backs off independently for 60 seconds, then exponentially, up to 15 minutes and never beyond the configured board interval. A 429 persists a cooldown against that API host and honors the collector's already-clamped Retry-After/default cooldown. Different tenants on different hosts are not blocked by a provider-wide scheduler exclusion.
- The old LinkedIn/Naukri/Instahyre/Hirebase provider-level scheduling path remains separate. Hirebase stays disabled by current dev/QA configs and is not added to board polling.
- Existing per-collector pagination, page caps, delays, Workday inventory cursor, and source request telemetry remain in place.

### Baseline and alert safety

- Every new board is marked `baseline_pending`, even when another board under the same provider has already had successful runs.
- A newly activated or reactivated board becomes due immediately but gets a silent initial inventory pass. Job rows stay visible; the baseline matches the board's full retained `source_details.board_key` history, not only rows first seen after activation. Eligible unattempted notifications are suppressed/cancelled. Already-sent or attempted notifications and older cross-source canonical observations are preserved.
- On the first successful board run, its scheduler baseline is cleared. Generic failures and rate-limited/partial runs keep the baseline pending, so a partial first snapshot cannot produce a burst of alerts.
- Stable `board_key` provenance is written into each supported ATS job's `source_details_json`, alongside existing registry IDs.

### API and dashboard

New admin-only endpoint: `GET /api/discovery/scheduler/status`.

It returns active/inactive board counts, board due times/outcomes/baseline/failure state and shared host lease/429/cooldown state. It does not return tokens, request URLs, API credentials or payloads.

The Source Health section now has a **Persistent employer-board scheduler** panel with per-board rows and shared API-host budget rows. Existing coverage, Workday inventory and provider health tables remain intact. The data is read-only and fetched through the authenticated admin API.

Activation and deactivation sync the scheduler database before returning, instead of waiting for the periodic scheduler loop to notice the config change.

## Tests

New tests:

- `v2/test_board_scheduler.py`: stable identities, opt-in config sync, due-time persistence, same-host exclusion, cross-host concurrency, per-board failure backoff, host 429 cooldown, deactivation, reactivation and first-baseline rules.
- `v2/test_board_scheduler_baseline.py`: a first-inventory baseline for one employer does not suppress a neighbouring employer's canonical opportunity.
- `v2/test_board_scheduler_orchestration.py`: one scheduler claim invokes `run_source` with exactly one board and persists that board's metrics/outcome.
- Added admin-only API/status coverage and immediate schedule create/deactivate assertions to `v2/test_board_discovery.py`.

The focused scheduler/discovery suite passed **51 tests** after the activation/deactivation and cross-tenant host-cooldown changes. One further retained-history reactivation-baseline regression was added and passed; the final scheduler/baseline/orchestration subset is **14/14**. A complete V2 regression run passed **464 tests** before the last two targeted regressions; the exact pushed head must pass the dispatched V2 CI workflow before merge.

Python validation uses isolated environment `/tmp/job-radar-test-venv` (not the production runtime). Server system Python and the server's pre-existing venv lacked required test dependencies; no packages were installed into either runtime environment. Dashboard JS syntax passed with Node 22 in a disposable container; the VM's system Node 12.22.9 was not used.

## Outstanding verification

1. Confirm final full V2 unittest run passes after the last changes.
2. Confirm exact-head GitHub Actions CI after pushing the candidate branch. A Node 22 syntax check and static asset HTTP checks already passed.
3. Candidate image `job-radar-board-scheduler:candidate` was built without retagging or replacing `job-radar-dev-multitenant:243da9c`.
4. A separate, loopback-only candidate container `job-radar-board-scheduler-qa` is running on port 18011 with volume `job-radar-board-scheduler-qa-data`. It uses a copied QA config (`notifications_enabled=false`, Hirebase/Naukri/LinkedIn disabled, public ATS boards enabled at one-hour cadence); no dev/QA database is mounted.
5. Candidate first-pass smoke test: 10/10 boards succeeded; 1,660 jobs; 53/53 HTTP 2xx; zero 429s, request exceptions, page or board failures; database integrity `ok`; zero sent notifications. Workday has 15 facet partitions queued and remains explicitly incomplete. See `docs/CANDIDATE_QA_SMOKE_2026-11-09.md`.
6. Owner must create isolated QA admin/member accounts with `python -m v2.auth_admin` (commands in the smoke-test note), then Desktop browser QA must verify admin/member views, responsiveness, console/network and per-board status. Do not merge or deploy until exact-head CI and the Desktop report are reviewed.

## Known limits / deliberate trade-offs

- Board-level collector metrics are recorded in `ats_board_poll_schedule`; provider `source_runs` and provider Source Health summaries remain provider-scoped and therefore their latest run can represent the most recently polled board rather than a combined board snapshot. The new board panel is the authoritative per-board view.
- Maximum three active API hosts and one provider worker at a time are deliberately conservative. Do not increase concurrency or host spacing based only on a successful synthetic test; first measure real latency, request counts and provider-specific 429 behavior.
- Host leases and due times are durable. In-flight HTTP work itself is not resumable; after a hard process kill, the lease expires and the board is safely retried.
- The 5-second host spacing is between board runs, not a token bucket around each individual HTTP request. Existing collector-internal pagination caps and delays still bound requests inside one board run. A future per-request token bucket needs a transport-level design and separate tests.

## Current branch worktree

`/tmp/job-radar-board-scheduler` — branch `feat/per-board-scheduler-20261109`. Keep the existing `/tmp/job-radar-global-discovery` worktree and the live `job-radar-user-preferences` worktree untouched.

## Continuation checkpoint — 2026-11-10 09:28 IST

This is the latest verified state after the prior chat hit a delivery timeout. The agent was verifying the final CI test count; CI had in fact completed successfully.

- Feature branch: `feat/per-board-scheduler-20261109`.
- Feature commit: `06a2ca472c4cc8368b27c4c8ee4a86aa91a6eb1e`.
- Draft PR: [#66](https://github.com/AvinashBhalla/job-beeper/pull/66), stacked on draft PR #65 (`feat/global-ats-discovery-hirebase-guard-20261109`). Review/merge #65 first, then #66. No deployment or merge has occurred.
- Exact-head GitHub Actions V2 CI: run #1444 (`42676092793`) passed on `06a2ca4`. The completed `syntax` job shows Python compile, dashboard JS syntax, focused router/extractor tests and full V2 unittest suite all succeeded. The downloaded job log reports **466 tests in 60.421 seconds; OK**.
- Local targeted scheduler/discovery suite: **52 tests passed** after the final retained-history baseline and cooldown tests.
- Candidate image: `job-radar-board-scheduler:candidate`, image digest `sha256:339bd42f54e3f51beedba1a576a55861f992f381d89a54e261505aa5c1b6429c`.
- Candidate container: `job-radar-board-scheduler-qa`, loopback-only `127.0.0.1:18011`, isolated volume `job-radar-board-scheduler-qa-data`; it was rebuilt from the exact feature commit and restarted without replacing dev, connector-QA, synthetic-QA or production. Private Termalin internal-site access was created for owner browsing.
- Candidate first-pass live-feed result: **10/10 boards succeeded** across eight ATS providers; 1,660 jobs observed; 53/53 HTTP 2xx; zero 429s, request exceptions, page failures or board failures; SQLite integrity `ok`; all 10 baselines cleared; no sent notifications. Seven API hosts were represented. Workday had 15 facet partitions queued, so its total inventory remains explicitly incomplete.
- Dashboard JS syntax passed with Node 22; `/dashboard/`, `/dashboard/app.js` and `/dashboard/auth.js` returned HTTP 200. Anonymous scheduler telemetry returned HTTP 401 as expected.
- The isolated candidate has no test users yet. Owner-created QA-only admin and member accounts plus a Desktop browser report are the outstanding acceptance tasks. Exact commands and a browser test prompt are provided in the continuation response. Do not place passwords in command-line arguments or paste them into chat.

Next work: have the owner provision QA-only accounts and run the Desktop browser prompt against the isolated candidate. Review the report, fix any issues, update this file and the smoke-test report, then keep #66 draft until the owner accepts the browser QA. Only after #65 is merged should #66 be retargeted/rebased and considered for merge. Do not deploy to dev/QA/prod merely because CI passed.

## Extended autonomous scheduler observation — 2026-11-10 09:30 IST

A later read-only inspection confirms the candidate continued operating after the initial smoke test rather than merely remaining healthy. The isolated container has remained up with restart count zero. It recorded 100 source runs across the 10 scheduled boards during the overnight observation window. Per-source records are consistent with ten polls per board: Ashby 20 runs for two boards, Greenhouse 30 runs for three boards, and one board each for Darwinbox, Keka, SmartRecruiters, Workable and Workday (10 runs each).

| Provider | Board count | Source runs | Aggregate jobs seen | Aggregate new jobs | Requests | 429 / exceptions / page failures / board failures |
|---|---:|---:|---:|---:|---:|---|
| Ashby | 2 | 20 | 8,270 | 839 | 20 | 0 / 0 / 0 / 0 |
| Darwinbox | 1 | 10 | 356 | 36 | 10 | 0 / 0 / 0 / 0 |
| Greenhouse | 3 | 30 | 3,685 | 371 | 30 | 0 / 0 / 0 / 0 |
| Keka | 1 | 10 | 1,090 | 109 | 20 | 0 / 0 / 0 / 0 |
| SmartRecruiters | 1 | 10 | 2,999 | 319 | 230 | 0 / 0 / 0 / 0 |
| Workable | 1 | 10 | 60 | 6 | 10 | 0 / 0 / 0 / 0 |
| Workday | 1 | 10 | 362 | 201 | 219 | 0 / 0 / 0 / 0 |
| **Total** | **10** | **100** | **16,822** | **1,881** | **539** | **All zero** |

These are cumulative *observations*, not unique jobs. The database contains 1,881 unique job rows and 1,881 notification-ledger rows. Every board's latest outcome is success, every consecutive failure count is zero, all 10 baselines are clear, all 7 host records have no active lease, no HTTP 429 was recorded, no notifications have been sent, no QA users exist yet, and SQLite integrity remains `ok`. Container health returns HTTP 200 and restart count is zero. The most recent run records are spread across the providers at the expected staggered times.

This is extended cadence evidence, but it is still one isolated candidate configuration and not a production load/SLA certification. The Desktop browser/admin/member acceptance is pending.

## Final exact-head CI result — 2026-11-10

- Latest code/docs head before this documentation-only result entry: `e3a9be13abd69b023ea7d2f0703b47f0beeb00a4`.
- GitHub Actions V2 CI **run #1446** (`42753221761`) completed successfully on that exact SHA: https://github.com/AvinashBhalla/job-beeper/actions/runs/42753221761
- The successful job ran Python compilation, dashboard JavaScript syntax, focused router/extractor tests (32), and the full V2 unittest suite (**466 tests in 62.218 seconds, OK**). Do not confuse the focused 32-test subset with the full suite.
- The branch's final documentation-only changes do not modify application code; the code and browser assets tested by #1446 are unchanged.

## Desktop acceptance follow-up — 2026-11-10

Read docs/DESKTOP_QA_FOLLOWUP_2026-11-10.md for the owner-uploaded browser findings and independent anonymous 401 proof. The anonymous authorization gap is closed at the HTTP layer. The final release recommendation remains BLOCKED because admin reload persistence, admin responsive coverage after member handoff, and exported screenshot files are still missing. Do not mark this feature accepted based only on unit/CI/live-feed success.
