# User Preferences and Per-User Job Evaluations — Design

**Date:** 2026-11-06  
**Status:** Approved product direction; implementation in progress  
**Base:** `v2-live-radar` at `dd7aeb1` (PR #45 merged)  
**Feature worktree:** `/tmp/job-radar-user-preferences`  
**Feature branch:** `feat/user-preferences-evaluations-20261106`

## 1. Product decisions

1. JobBeeper remains a shared-ingestion system, not one scraper per user.
2. Each account has independent candidate preferences and evaluation results.
3. A normal user cannot browse the personalized feed until they have saved:
   - at least one target role; and
   - at least one target location.
4. An incomplete user sees an onboarding/setup state, not the admin's feed, a global feed, or a misleading empty results page.
5. New users start with empty candidate preferences. The first admin's existing global candidate profile is copied only to that admin's preference row during migration.
6. Admin source/runtime controls and shared collector configuration remain admin-only.
7. Per-user Telegram delivery and server-side application tracking are explicitly out of scope for this milestone.

## 2. Shared and tenant-owned data

### Shared/system-owned
- Source collectors, schedules, provider credentials and request budgets.
- Raw source observations, normalized jobs and canonical opportunities.
- Source health, run telemetry, deduplication and ingestion diagnostics.
- Global runtime safety gates and system configuration.

### User-owned
- Target roles, locations, skills and experience range.
- Excluded role/title terms, remote-only preference, freshness and match threshold.
- User-specific job evaluations, scores, explanations and alertability decisions.
- Temporary browser-side saved/applied state, namespaced by user ID until a server-side applications milestone.

No API may accept a client-supplied user ID as the ownership authority. Resolve the owner exclusively from the authenticated session.

## 3. Data model

### `user_preferences`
One row per user. Store validated candidate preferences as JSON initially, with a schema/version and update timestamp. The row must not contain provider secrets or source scheduler controls.

Candidate fields to migrate from the existing config:
- `target_roles`
- `locations`
- `skills`
- `candidate_experience_years`
- `min_experience_years`
- `max_experience_years`
- `match_threshold`
- `title_exclude`
- `excluded_role_terms`
- `remote_only`
- `max_age_hours`

Notification flags that still drive the global admin Telegram worker must remain admin/system controlled for now; do not imply per-user Telegram exists.

### `user_job_evaluations`
One current evaluation per `(user_id, job_id)`, with:
- preference/rules fingerprint and evaluated timestamp;
- match flag, score and reasons;
- parsed experience bounds;
- user-specific alertability and reasons only where they can be computed without sending;
- foreign keys/indexes supporting user-scoped feed queries.

Keep existing `job_evaluations` and `notification_ledger` intact for the current admin/global Telegram path. Do not repurpose or delete them in this milestone.

## 4. API and authorization

- `GET /api/preferences`: return only the authenticated user's preferences and onboarding-complete state.
- `PUT /api/preferences`: validate and save only the authenticated user's preferences; require at least one role and location before marking onboarding complete.
- `GET /api/jobs`, `GET /api/daily-summary`, and `GET /api/jobs/{id}`: authenticated user scope; join only that user's evaluation rows.
- Opportunity list/detail endpoints remain admin-only in this first slice; tenant-scope them before exposing opportunity navigation to normal users.
- Do not include global `notification_ledger` state in user responses.
- `/api/config`, source telemetry, provider diagnostics, notification queue and other operational endpoints remain admin-only.
- Admin preference writes through the legacy global config path must keep the admin's user-preference row synchronized to avoid split-brain behavior.

## 5. Matching and evaluation

- Matcher functions receive an explicit preference dictionary. They must not silently call `get_config()` to obtain a candidate profile for user-scoped evaluation.
- An incomplete profile cannot receive a personalized evaluation or feed.
- Preference saves re-evaluate already-ingested jobs for that user only; no source scan is triggered.
- New ingestion evaluates the new/changed jobs for all active, configured users, without changing the global admin evaluation/Telegram behavior.
- Fingerprints include normalized user preferences and matcher rules version. Stale rows are recomputed deterministically.
- A user's preference edit must not modify another user's evaluation rows.

## 6. Dashboard

- Keep the admin dashboard and operational panels working.
- After authentication, branch UI behavior by role.
- Admins continue using `/api/config` and existing source/notification controls.
- Ordinary users load `/api/preferences`; if incomplete, show onboarding and do not request the jobs feed.
- Once complete, load user-scoped feed, summary and detail.
- Hide admin-only source/telemetry controls from ordinary users; backend authorization remains mandatory.
- Normal users use a separate minimal workspace and never load the admin app shell or its browser-local applied/saved state. Server-side applications remain deferred.

## 7. Migration and safety

- Additive, idempotent SQLite schema migration.
- Existing admin candidate config is copied to the first admin only; do not copy it to newly provisioned users.
- New users get an empty profile and onboarding-complete=false.
- Do not mutate the active dev or production DB during implementation.
- Test migrations against synthetic databases and a separately verified read-only snapshot copy of dev data.
- Do not rebuild/restart the existing dev service or deploy production as part of implementation.
- Production release requires separate explicit authorization, verified backups, tenant-isolation tests and rollback plan.

## 8. Acceptance criteria

1. Anonymous requests cannot access preferences or any job feed.
2. User A cannot read or change User B's preferences/evaluations.
3. New users see onboarding, not a shared/global job feed.
4. Missing role or location is rejected by the API and does not unlock feed access.
5. A configured user sees only their own match scores/reasons.
6. Saving preferences re-evaluates only that user's jobs and does not trigger ingestion.
7. New ingested jobs are evaluated independently for each configured user.
8. Admin global configuration, source controls and current global Telegram ledger continue to work.
9. Existing admin profile migrates to the admin preference row; normal users do not inherit it.
10. Local applied/saved state is isolated by user ID.
11. Full V2 suite, dashboard contract tests, migration tests and CI pass.
12. Existing dev and production containers/databases remain untouched.

## 9. Deferred

- Tenant-scoped opportunity list/detail endpoints.
- Per-user Telegram linking/fan-out and notification ledger.
- Server-side applications, saved jobs, notes and follow-ups.
- Referral intelligence, contacts discovery and email drafts.
- PostgreSQL migration or per-user scraper/scheduler.
