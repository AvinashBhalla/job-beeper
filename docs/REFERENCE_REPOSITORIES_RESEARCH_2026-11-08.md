
## Connector implementation follow-up (same day)

After the research note was drafted, the Keka/Darwinbox adapters were completed on the isolated VM worktree `feat/darwinbox-keka-20261108`. They add discovery detection, public endpoint verification, admin board activation mapping, opt-in config fields, bounded collection, source rate-limit handling, source status registration, dashboard controls and provider tests. Both switches default to disabled. No production image or production config was changed by this feature work.

Live verification against employer public boards on 2026-11-08:

- Keka `https://bridgestone1.keka.com/careers`: endpoint verification HTTP 200, 109 postings.
- Darwinbox Arvind Group public `.in` careers board: endpoint verification HTTP 200, 36 postings. The earlier JG Summit `.com` example was later re-probed and returned 403; it is superseded.

Isolated database run_source rehearsal for each provider:

- First run: Keka 109 / Darwinbox 18 ingested and tagged as first-board baseline.
- Second run: Keka 0 new / Darwinbox 0 new; no duplicate rows.
- Notification sending was disabled and the notification ledger had no sent items.
- SQLite integrity was `ok` after both runs.

A first complete local V2 suite run found one existing Workday collector test patching `requests.post/get` while the Workday adapter had moved to `_tracked_source_post/get`. The test was updated to mock the tracked request boundary and retain its original assertions. The focused Workday test then passed. The full V2 suite was started again afterward; record the final result from the run log before promoting this feature branch.

### Implementation test result — final local V2 rerun

- Full suite: **387 tests passed in 215.671 seconds, exit code 0** using `python -m unittest discover -s v2 -p 'test_*.py' -v` in the isolated candidate worktree.
- Python `compileall`, JSON parsing of `v2/config.json`, and `git diff --check` all passed.
- One earlier test run found a stale Workday test double that patched raw `requests.post/get`; Workday uses the common tracked request wrappers. The test now mocks `_tracked_source_post` and `_tracked_source_get` and the focused Workday test passes. The final full suite includes this correction.
- No GitHub CI has yet been run on the connector feature branch's final SHA; the feature changes remain local/uncommitted pending review and a deliberate push/PR step. Do not call the feature branch release-ready on the basis of local tests alone.
- Production remains on `job-radar-prod-canary:7b1a80d`; final read-only `/health` still returned HTTP 200. No connector flags, production DB or Telegram settings were changed by this work.

### Darwinbox source-pattern correction — 2026-11-08

The live re-verification invalidated the earlier `jgsummit.darwinbox.com` example: it returned HTTP 403 and must not be presented as a working public endpoint. The current Career-Ops provider and its example config recognize `*.darwinbox.in`; JobBeeper has tightened its detector to that suffix. `arvind.darwinbox.in` returned 36 jobs in a live public endpoint probe. Several other `.in` examples returned 403, reinforcing that every tenant must be individually verified.

### Live verifier contract improvement — 2026-11-08

The JobBeeper Workable verifier originally used a different, obsolete endpoint than the collector. It now calls the collector's public widget route `https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true`; the regression test pins that route and the live Hugging Face probe returns six postings. This is an implementation lesson from the reference provider architecture: probes should test the exact transport and envelope used by the production adapter, or the verifier can falsely reject a healthy collector.
