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
- [ ] Add idempotent `user_preferences` and `user_job_evaluations` migrations with indexes/constraints.
- [ ] Add schema validation/defaults for new user profiles (empty roles and locations).
- [ ] Add admin-only migration/backfill from current global candidate config to first admin only.
- [ ] Test first-admin backfill, repeat startup idempotency, new-user isolation, invalid payloads and DB upgrade from legacy schema.

## Phase 2 — explicit per-user matcher/evaluator (TDD)
- [ ] Refactor matcher entry points to accept explicit preferences; retain global config behavior for admin/legacy Telegram path.
- [ ] Add profile-completeness gate: target role and location both required.
- [ ] Add deterministic preference/rules fingerprint and per-user evaluation upsert.
- [ ] Re-evaluate a user's stored jobs after preference save without invoking source collectors.
- [ ] Evaluate new ingested jobs for all active, configured users while preserving global admin evaluation/notification behavior.
- [ ] Test two users with opposing roles/locations and prove no cross-user writes or reads.

## Phase 3 — user-scoped API (TDD)
- [ ] Add `GET/PUT /api/preferences` scoped from authenticated session.
- [ ] Make jobs, daily summary, opportunity list/detail and job detail available to authenticated users with user-specific evaluation joins.
- [ ] Remove global notification-ledger details from normal-user payloads.
- [ ] Keep source/config/telemetry/notification-queue routes admin-only.
- [ ] Update route registration/auth tests and add cross-tenant endpoint matrix.

## Phase 4 — dashboard onboarding and feed
- [ ] Track authenticated user/role in dashboard bootstrap.
- [ ] Admin uses existing global config/operational UI; ordinary users use preferences API.
- [ ] Incomplete user sees role/location onboarding and makes no jobs-feed request.
- [ ] Configured user sees their personalized feed and evaluation details.
- [ ] Hide admin-only operational UI for normal users.
- [ ] Namespace local applied/saved state by user ID; only migrate legacy key for first admin.
- [ ] Add Node dashboard tests for role routing, onboarding gate, feed isolation and storage namespace.

## Phase 5 — validation, docs and PR
- [ ] Run full V2 Python suite, Node dashboard suite, JS syntax checks, py_compile and Compose config validation.
- [ ] Test migration on synthetic DB and disposable verified snapshot copy.
- [ ] Review auth/tenant boundaries manually; request automated PR review and resolve all actionable findings.
- [ ] Update README, roadmap, handover and knowledge-transfer docs with exact code/test/PR/runtime state.
- [ ] Open one focused PR targeting `v2-live-radar`; wait for green CI/review before merge.
- [ ] Do not deploy or mutate the existing dev/prod runtime without explicit approval and a verified backup.
