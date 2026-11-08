# PR and Branch Audit — 2026-11-08

## Decisions and merge results

| PR | Repository | Result | Reason / remaining gate |
|---|---|---|---|
| [#41 matcher quality benchmark](https://github.com/AvinashBhalla/job-beeper/pull/41) | job-beeper | **Merged** to v2-live-radar (squash `4e48836`) | The benchmark fixture, deterministic runner and 2 regression tests were already present in the V2 branch. This PR contributed the missing 31-line methodology note. The 2 tests passed against current V2; 4/4 scored seed cases passed, with 1 explicitly review-only. |
| [#47 source health and Naukri freshness](https://github.com/AvinashBhalla/job-beeper/pull/47) | job-beeper | **Merged** to v2-live-radar (squash `dd4d21e`) | GitHub V2 CI #1314 / run `42442324585` passed: dashboard syntax, focused tests, full suite **207 passed**. Branch merge only; no service deployment. |
| [#46 user preferences and personalized feed](https://github.com/AvinashBhalla/job-beeper/pull/46) | job-beeper | **Open draft; not merge-ready** | Google OAuth and resume parser live smoke tests succeeded on isolated port 8002. Preferences-save error is not surfaced by UI; email/password signup and Google branding remain backlog; per-user Telegram webhook/delivery E2E is incomplete. |
| [#35 V2 to main](https://github.com/AvinashBhalla/job-beeper/pull/35) | job-beeper | **Open draft; not merge-ready** | Retitled from the obsolete Gemini label. Head is v2-live-radar, base is main. This is a large promotion/release gate with a diverged/dirty base; requires explicit main/V2 reconciliation and a production migration/release checklist. |
| [#4 relay last-good and observation timestamps](https://github.com/AvinashBhalla/job-beeper-naukri-relay/pull/4) | job-beeper-naukri-relay | **Open draft; CI passed** | Relay validation run `42442285937` passed (YAML/embedded collector syntax + 3 tests). It changes the publisher used by the VM's five-minute timer and therefore the public feed consumed by production/dev. Keep draft until explicit approval of that live publisher change. |
| [#37 job intelligence foundation](https://github.com/AvinashBhalla/job-beeper/pull/37) | job-beeper | **Closed unmerged** | The source registry fix is already present (`SOURCE_NAMES = tuple(COLLECTORS)`, including Ashby); remaining static architecture documents were based on an older snapshot and superseded. Branch was 70 commits behind. |
| [#3 structured Naukri details](https://github.com/AvinashBhalla/job-beeper-naukri-relay/pull/3) | job-beeper-naukri-relay | **Closed unmerged; deferred** | Uses a JobSpy 1.2.0 internal-method patch, had no independent automated suite/CI and overlaps the relay workflow changed by #4. Keep its patch as historical PR evidence; do not merge without a focused compatibility test. |

## Remote branch cleanup

### job-beeper
Kept: `main`, `v2-live-radar`, `feat/user-preferences-evaluations-20261106`, `fix/linkedin-experience-parser`.

Deleted: `feat/matcher-quality-benchmark-20261106` (after #41 merge), `feat/source-observability-20261107` (after #47 merge), `work/job-intelligence-foundation` (after #37 closure), and `work/source-run-telemetry-clean` (older duplicate telemetry work superseded by #47).

`fix/linkedin-experience-parser` is intentionally retained. It contains a focused LinkedIn labelled-experience parser fix and regression tests, but its branch also contains unrelated changes from an older main/V2 lineage. **Do not merge the branch wholesale.** When prioritized, transplant only the focused experience-parser and test commits onto current v2-live-radar, then run the full suite and CI.

### job-beeper-naukri-relay
Kept: `main`, `naukri-relay` (published feed branch), and `feat/relay-first-seen-preserve-last-good-20261107` (draft PR #4).

Deleted: `feat/structured-naukri-details-20261106` (after #3 closure), `fix/relay-schedule-offset` and `fix/vm-only-relay-scheduling` (their changes are already in relay main).

## Deployment boundary

- PR #41 and #47 were merged into the **v2-live-radar source branch only**. No container rebuild/restart or deployment took place.
- Shared development port 8001 and production port 8000 were not changed.
- Relay PR #4 has not been merged, dispatched or published. The public feed remains on its prior schema until approval.
- OAuth secrets remain in the isolated feature VM's private `.env.feature`; no secrets were copied to Git or chat.
- PR #46 and PR #4 remain drafts. PR #35 remains a WIP main-promotion/release gate.

## Local workspace cleanup / preservation

- Temporary worktrees for the merged PR #41 and #47 branches are candidates for removal after their remote branches were deleted.
- The old source-observability worktree contains an uncommitted cooldown-metadata experiment; preserve it for later review rather than silently discarding it.
- The main dev checkout under `/home/ubuntu/job-beeper-dev` has local `.env.save`, `.venv`, config backup and config changes; do not clean or overwrite those files.
- The parser-fix worktree is retained for its focused, unreviewed change.
- The user-preferences worktree remains for open draft PR #46.
- The relay feature worktree remains for open draft PR #4.

## Follow-up after relay PR #4 merge — 2026-11-08

- Relay PR #4 was merged to relay main as `359df41c22f1dd5d696fedbd926d813692c28728`. Its first natural VM timer run after merge was GitHub Actions run `42445116273`; it succeeded and published 323 jobs at `2026-11-08T04:03:47.799190+00:00`. Every item had `relay_first_observed_at` and `relay_last_observed_at`, with valid ordering. No manual dispatch occurred.
- Relay PR #4 is now closed/merged; the remaining relay PR inventory is empty. Delete its now-merged feature branch after preserving the merge commit in main. Relay branches should then be only `main` and `naukri-relay`.
- Open app PR inventory remains #35 (V2-to-main release gate) and #46 (user preferences). A new isolated LinkedIn backoff branch is being tested separately; it is not yet merged or deployed.

## 2026-11-08 — LinkedIn backoff and persistence merges; final branch cleanup

- PR #48 `Reduce repeated LinkedIn 429s with longer conservative cooldowns` was squash-merged to `v2-live-radar` as `5b4b2fa`. GitHub CI run `42445585602` passed the full V2 suite (**209 tests**) and dashboard syntax. The 5m base is retained; fallback escalates to a 4h cap; escalation resets only after 24h without a 429; larger Retry-After is still honored.
- PR #49 `Persist LinkedIn rate-limit cooldown across restarts` was squash-merged as `596bbbe`. GitHub CI run `42446515750` passed the full V2 suite (**215 tests**) and dashboard syntax. An additive source_runs detection timestamp and startup restoration now preserve the 24h streak/cooldown across process restarts.
- Deployment boundary: both PRs are code merges into `v2-live-radar` only. No production 8000 or shared dev 8001 container was rebuilt/restarted. Production's old SQLite source_runs table still has no structured request-level 429 history; first deployment will start without backfilling the existing 27 log-only 429s. Future actual 429 rows are persisted.
- The old `fix/linkedin-experience-parser` branch was verified redundant: current `v2-live-radar` already contains `extract_linkedin_labeled_experience` and its two regression tests; those tests are included in the 215-test CI suite. It can be removed without losing parser functionality.
- Remove merged remote branches `fix/linkedin-429-longer-backoff-20261108` and `fix/linkedin-cooldown-persistence-20261108`, plus redundant `fix/linkedin-experience-parser`. Retain the `fix/linkedin-429-longer-backoff-20261108` local worktree only because the isolated 8003 preview is serving static assets from it; do not delete/restart that preview without moving it first.
- Current planned app branches after cleanup: `main`, `v2-live-radar`, and `feat/user-preferences-evaluations-20261106` (open draft PR #46). PR #35 remains the V2-to-main release gate and is not merge-ready.
- The isolated 8003 preview is restored: health/dashboard/assets return HTTP 200, source-status remains admin-only (401 anonymously), and all five collector switches and notifications remain disabled with synthetic source-run examples only.
- Next prioritized feature task: diagnose the PR #46 preferences-save validation/UI error before considering the multi-user branch merge. Do not merge PR #46 or promote to shared dev/production until preference save and per-user Telegram E2E are verified.

## 2026-11-08 — PR #46 local V2 integration candidate

- A local-only integration worktree `/tmp/job-radar-pr46-integration` merges `feat/user-preferences-evaluations-20261106` onto the latest `v2-live-radar` base at `a719138`. This is a rebase/conflict-resolution candidate only; it has not been pushed and does not alter the 8002 feature service or 8004 desktop QA service.
- Shared conflict in `v2/radar.py` was resolved by combining both implementations: preserve monotonic `last_seen_at`, safe source-posted timestamp handling and description-change-only global reevaluation; retain experience provenance/confidence ranking, min/max persistence and per-user evaluation refresh for only touched/new jobs.
- `dashboard/app.js` and `dashboard/index.html` auto-merged. Six conflict files were originally detected; the docs conflicts are being resolved by keeping the newer V2 handover/roadmap/audit and appending current PR #46/browser QA status. Feature-only docs and tests (OAuth, resume parser, Telegram, local browser QA) remain included from PR #46.
- Important next integration: ensure `user_notification_ledger` enqueue/delivery excludes global `notification_ledger.baseline_suppressed=1` opportunities before Lever or other first-snapshot ATS inventory is enabled for member Telegram. The user notification path must not bypass the initial-inventory baseline.
- This local candidate must pass the full V2 suite and user-preferences/OAuth/resume/Telegram focused suites. Keep PR #46 remote draft unchanged until owner desktop Browser report is returned and this candidate has full green CI.
- No push/deploy/runtime changes.
