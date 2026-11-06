# Implementation Plan — User Preferences and Evaluations

**Design:** [2026-11-06-user-preferences-evaluations-design.md](../specs/2026-11-06-user-preferences-evaluations-design.md)  
**Base commit:** `dd7aeb1`  
**Branch/worktree:** `feat/user-preferences-evaluations-20261106` / `/tmp/job-radar-user-preferences`

## Phase 0 — baseline and isolation
- [x] Create a clean feature worktree from merged `origin/v2-live-radar`.
- [x] Run full V2 baseline suite: 189 passed; one Node-only test skipped in Python-only image.
- [x] Confirm current active dev/prod containers and preserve them untouched.
- [ ] Create a disposable, isolated test DB/snapshot; never point tests at active `/data/jobs.db`.

## Phase 1 — database and preferences service (TDD)
- [x] Add idempotent user_preferences and user_job_evaluations tables with indexes/constraints.
- [x] Add schema validation/defaults for new user profiles (empty roles and locations).
- [x] Add first-admin-only migration/backfill from current global candidate config.
- [x] Test first-admin backfill, repeat migration idempotency, new-user isolation, invalid payloads and schema initialization.

## Phase 2 — explicit per-user matcher/evaluator (TDD)
- [x] Matcher evaluation receives an explicit user preference object; existing global matcher/Telegram path remains intact.
- [x] Add profile-completeness gate: target role and location both required.
- [x] Add deterministic preference/rules fingerprint and per-user evaluation upsert.
- [x] Re-evaluate a user’s stored jobs after preference save without invoking source collectors.
- [x] Evaluate touched ingested jobs for active, configured users while preserving global admin evaluation/notification behavior.
- [x] Test two users with opposing roles/locations and prove their match results are independent.

## Phase 3 — user-scoped API (TDD)
- [x] Add GET/PUT /api/preferences scoped from authenticated session, with CSRF on writes.
- [x] Make jobs feed, daily summary and job detail available to authenticated users with user-specific evaluation joins.
- [ ] Opportunity list/detail endpoints remain admin-only for this slice; scope them before exposing opportunity navigation to normal users.
- [x] Remove global notification-ledger details from normal-user job payloads.
- [x] Keep source/config/telemetry/notification-queue routes admin-only.
- [x] Update route registration/auth tests and add user-scoped feed tests.

## Phase 4 — dashboard onboarding and feed
- [x] Track authenticated user/role in dashboard bootstrap.
- [x] Admin uses existing global config/operational UI; ordinary users use preferences API.
- [x] Incomplete user sees role/location onboarding and makes no jobs-feed request.
- [x] Configured user sees their personalized feed and evaluation details in a separate user workspace.
- [x] Normal users never load the admin app shell or operational controls.
- [x] User workspace does not read the legacy applied/saved localStorage key; server-side applications remain deferred.
- [x] Add dashboard contract tests for onboarding controls and user feed routing.
- [x] Filter user match rows before LIMIT and use a permissive experience default until the user-facing range control exists.

## Phase 5 — validation, docs and PR
- [x] Run full V2 Python suite (209 passed), dashboard contract suite, esbuild JS syntax check, Python compile and isolated Compose config validation.
- [x] Test migrations/preferences/evaluations using synthetic databases; no live DB snapshot was required or modified.
- [ ] Review auth/tenant boundaries manually; request automated PR review and resolve all actionable findings.
- [x] Update README, V2 README, roadmap, handover and knowledge-transfer docs with exact code/test/PR/runtime state.
- [ ] Open one focused PR targeting v2-live-radar; wait for green CI/review before merge.
- [x] Keep existing dev/prod runtime untouched; provide a separate isolated feature Compose environment for user-run smoke tests.
