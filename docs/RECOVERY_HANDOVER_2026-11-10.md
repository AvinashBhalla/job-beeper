# JobBeeper — 2026-11-10 Recovery & Continuation Handover

## User direction
- Prioritize working functionality over UI polish or screenshot evidence.
- Document progress before continuing after interruptions.
- Ship validated changes to `v2-live-radar`, keep GitHub tidy, then proceed to the next task.
- Do not spend time on the remaining visual QA unless it blocks functionality or acceptance.

## Completed before this task
### Integration and release
- PR #65 (guarded global ATS discovery foundation) merged to `v2-live-radar`.
- PR #66 (persistent per-board ATS scheduler) merged to `v2-live-radar`.
- Integration head at start of this work: `dee7b36` (verify current remote head before pushing).
- V2 CI recorded 466 passing tests on the combined application changes.
- Candidate scheduler smoke test: 10 boards, zero failures, no notifications sent.

### Dev / connector QA rollout
- Built image `job-radar-dev-multitenant:dee7b36` from the merged integration tree.
- Replaced `job-radar-dev` and `job-radar-connectors-qa` using that image while preserving their existing volumes, environment, ports and mounted configs.
- Previous containers retained, stopped, for rollback:
  - `job-radar-dev-pre-scheduler-20261110`
  - `job-radar-connectors-qa-pre-scheduler-20261110`
- Verified database backups and exact live-feed config copies at:
  `/tmp/job-radar-release-backups/2026-11-10-pre-scheduler-promotion/`
  with SHA256SUMS.
- Both replacement containers reached HTTP 200 health and were running with zero restarts.
- The earlier audit showed all 10 board schedules successful in connector QA; dev had successful live polls and remaining schedules running/queued. Repeat the read-only audit if needed; do not change config or send notifications.
- Dev and QA share the same provider/board allowlist; QA intentionally uses a slower 60-minute cadence than dev. Notifications are disabled.

### GitHub cleanup
- PRs #65 and #66 merged.
- Six stale/unmergeable draft PRs #59–#64 closed with explanatory comments.
- Their exact heads preserved as annotated tags under `archive/deferred-prs-20261110/pr-59-...` through `pr-64-...`.
- Their remote feature branches deleted only after tagging.
- PR #65/#66 feature branches deleted after merge.
- GitHub open-PR inventory was zero at the end of cleanup. Recheck before opening the next PR.

## Current task — company-agnostic ATS discovery candidates
- Branch/worktree created from the merged integration head:
  - Branch: `feat/company-agnostic-ats-discovery-20261110`
  - Worktree: `/tmp/job-radar-company-discovery-20261110`
- The new module `v2/global_ats_discovery.py` has been written but is **not yet integrated, tested, committed or pushed**.
- It contains:
  1. Common Crawl catalogue refresh and one-provider-at-a-time CDX requests for Workday, Keka and Darwinbox.
  2. A persistent SQLite lease, 60-second minimum request interval, 24-hour cooldown on HTTP 429/503, bounded response sizes and rotating provider state.
  3. Public sitemap and career-link discovery with robots.txt checks, same-host redirects only, bounded documents/pages, per-host request budgets and cooldown.
  4. Candidate-only import callback; no source activation or direct employer creation by the module.
  5. Status/history reporting without exposing lease tokens.
- Existing discovery contracts inspected in `v2/board_discovery.py`, existing candidate scan integration inspected in `v2/radar.py`, and SQLite helper inspected in `v2/sqlite_store.py`.
- Current worktree was clean before the new module was written; verify exact status and diff.

## Immediate next steps (do not skip)
1. Confirm remote `v2-live-radar` head and current worktree status; retain the existing branch.
2. Inspect the new module for correctness, simplify/fix any defects, and write focused tests:
   - Common Crawl catalogue parsing, provider rotation, throttle/lease/cooldown, 429/503.
   - CDX candidate validation and truncation.
   - robots.txt, sitemap index/urlset, same-host redirects, cross-host rejection, SSRF/private-host rejection, host cooldown, malformed/oversized XML.
   - importer only stages candidates; it must not activate a provider or send notifications.
3. Wire explicit admin-triggered/manual discovery into existing candidate importer/status surfaces only if the current authorization and candidate staging contracts support it. Do not add an uncontrolled startup scan or broad background crawler.
4. Run focused tests, then the full V2 suite. Fix functional failures; ignore UI polish.
5. Document test results and operational safety limits in this file before pushing.
6. Commit and push the feature branch; open one PR to `v2-live-radar`.
7. Merge only after CI passes and diff is limited to this task. Deploy dev first, verify health, DB integrity, and candidate-only behavior; then connector QA. Keep production untouched unless explicitly requested.
8. Clean merged branch and any superseded branches only after preserving required work.

## Safety / release invariants
- Discovery produces low-confidence candidates only; it must never silently activate a board or enable a source.
- Respect robots.txt and host request budgets; no cross-host redirects for sitemap crawling.
- No notification sends from discovery.
- No unbounded crawling, response reads, redirects, or concurrent Common Crawl requests.
- Keep dev/QA live-feed configurations identical in provider/board coverage; preserve their intended cadence differences.
- Preserve rollback containers and backups until post-deploy checks pass.

## 2026-11-10 continuation checkpoint
- Recovery handover committed and pushed first as `6d9390f`.
- Added `v2/global_ats_discovery.py` and integrated it into `v2/radar.py`:
  - startup only initializes schema; no automatic network scan is launched;
  - three admin-only endpoints expose status, one Common Crawl request, and one public sitemap scan;
  - both paths use the existing global candidate importer.
- Added `v2/test_global_ats_discovery.py`.
- Focused tests: **12/12 passed** in an isolated container created from the current dev image. Host Python lacks the test dependencies, so tests ran against the same Python/runtime dependencies as the deployed app.
- Functional fixes from review:
  - Common Crawl batch cap is 200 to match the existing importer contract;
  - optional missing sitemap documents (404) are skipped rather than failing the host scan;
  - Common Crawl request errors are recorded and the lease is released instead of being left until lease expiry.
- `python -m py_compile` passed for the discovery module, its tests and `radar.py`; `git diff --check` passed.
- Full V2 pytest suite is currently running in the isolated test container. Do not deploy or merge until it completes and CI passes.
- Added an API integration test for the new admin-only discovery endpoints: status works for admins, member access is denied, invalid sitemap payloads return 422, and manual Common Crawl/sitemap calls delegate to the candidate importer. The test passed independently in the app runtime.
- PR #67 is open against `v2-live-radar`. Its first GitHub V2 CI run passed, including the full V2 unittest suite. The API integration test was added after that run and is being pushed for a fresh CI pass.
- To avoid spending further time on a redundant local full-suite run, the long local pytest discovery run was stopped after 24% progress; the authoritative GitHub V2 CI full unittest suite had already passed on the implementation commit. A fresh full CI run is now in progress for the follow-up API test commit `1628d05`.
- Focused pytest for both discovery and global-candidate integration files is running in the isolated app container; the standalone API test passed (1/1), and discovery unit tests passed (12/12).
