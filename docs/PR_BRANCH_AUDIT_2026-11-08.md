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
