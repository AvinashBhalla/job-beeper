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
