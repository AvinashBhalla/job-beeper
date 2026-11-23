# Discovery Engine Activity — 2026-11-23

## Verified source of truth

- Repository: `https://github.com/AvinashBhalla/job-beeper.git`
- Current implementation worktree: `C:\Users\avibh\Downloads\jobwatch\jobwatch-current`
- Revision tested: `1273858` (`v2-live-radar` tip at the time of verification)
- The older checkout in `C:\Users\avibh\Downloads\jobwatch\jobwatch` was preserved and not rebased or reset. Its local safety commit and pre-existing config stash remain intact.

## Validation completed

- Installed the declared test dependencies in an isolated `.venv`.
- Ran the full suite from a clean Linux VM worktree at the same revision: **629 tests passed** in 377.411 seconds.
- The Windows run exposed temporary SQLite cleanup errors caused by raw `sqlite3.Connection` context managers not closing handles on Windows. The worktree includes a lifecycle fix in `v2/sqlite_store.py` and app-specific helpers; the Linux result above validates the unmodified GitHub tip, while the Windows fix remains local pending its next commit/review.
- No paid SERP calls, production changes, or Telegram sends were made during validation.

## Development deployment and browser smoke check

- Started the isolated Compose development instance from the clean revision in `/home/ubuntu/job-beeper-current-test` as `job-radar-dev` on loopback port `8001`.
- Development config keeps `notifications_enabled: false` and both Telegram credentials blank. The isolated dev runtime was synchronized to disable the failing Naukri collector and enable the public Greenhouse boards already present in the fixture (`coinbase`, `gravitonresearchcapital`, `zocdoc`).
- The first dev scheduler cycle completed three successful Greenhouse board polls: 252 Coinbase jobs, 20 Graviton Research Capital jobs, and 66 Zocdoc jobs. The shared database contains 338 jobs, 338 canonical opportunities, 338 evaluations, and three persisted board schedules.
- A second all-board Greenhouse poll completed successfully with 338 seen, **0 new**, 3/3 boards successful, and the database remained at 338 jobs, confirming idempotent deduplication.
- The browser check confirmed the dashboard renders jobs and filtering metadata: title, company, location, freshness, experience evidence, match reason, source, and direct-apply URL. A “Machine Learning Engineer” profile match produced a 94 personalized score and an experience line sourced from the description; the `python` search narrowed the backend result set to 66 opportunities. The source-health view exposes successful board outcomes, request timing, zero HTTP 429s, and the global ATS candidate review queue.
- The visible feed is intentionally constrained by the configured 72-hour freshness filter; older Greenhouse postings remain persisted and searchable but are not rendered as current cards.
- The public port-8000 dashboard is the separate main container; it was inspected but not modified.

## Next steps

1. Review closed/stale transitions as boards age and confirm the persisted freshness/closed-state telemetry on a scheduled cycle.
2. Keep SERP/paid providers disabled and review the staged global ATS candidates before linking or activating additional boards.
3. If desired, run a separately approved Telegram smoke test against an explicitly selected test chat; the current dev instance remains notifications-off and sent zero alerts.
