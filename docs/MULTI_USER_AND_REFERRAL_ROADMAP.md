# JobBeeper Multi-User and Referral Intelligence Roadmap

**Status:** Product/architecture decision recorded; implementation not started
**Date:** 2026-11-06
**Priority:** Multi-user foundation is the next product milestone
**Repository:** AvinashBhalla/job-beeper
**Development branch/worktree:** `feat/naukri-rich-descriptions-20261106`, `/tmp/job-radar-naukri-location-v3`

## 1. Product direction

JobBeeper is moving from a personal job radar to a multi-user job discovery and job-search workflow product.

The immediate product objective is to let multiple real users create accounts, define independent job-search preferences, receive their own relevant matches, and connect their own Telegram destination. This enables a small beta and real user feedback before expanding the product.

The long-term direction includes a HAPPPY-like referral-intelligence workflow inspired by Uplers HAPPPY: after a user applies to a job, help identify relevant people at that employer, prepare referral/follow-up outreach, and track the follow-up process using authorized LinkedIn research and a user-authorized email integration.

**Priority order is explicit:**
1. Finish and safely promote the current search/description work.
2. Build secure multi-user identity, roles, per-user preferences and per-user Telegram delivery.
3. Run a small user beta and use feedback to improve matching, coverage and product UX.
4. Build application tracking and referral intelligence as a separate, permissioned workflow.
5. Consider hiring-post discovery and other broader features later.

Do not start referral automation before the multi-user foundation and application tracking are reliable.

## 2. Existing architecture: shared ingestion, personal evaluation

Do not create a separate scraper or scheduler for every user.

### Shared system data
- Source collectors and their schedules.
- Raw/source observations and normalized jobs.
- Canonical opportunities and cross-source identity.
- Source health, backoff, timestamps and ingestion diagnostics.
- Public job descriptions and original application URLs.

### User-owned data
- Account identity, role and session.
- Candidate profile and job preferences.
- Per-user match/evaluation results and match explanations.
- Saved jobs, application status, notes and follow-up tasks.
- Telegram connection and notification preferences.
- Later, email integrations, discovered contacts, outreach drafts and outreach history.

The intended flow becomes:

```
Shared source collectors
        |
        v
Normalized jobs + canonical opportunities
        |
        +----> User A preferences -> User A evaluations -> User A alerts
        |
        +----> User B preferences -> User B evaluations -> User B alerts
        |
        +----> User C preferences -> User C evaluations -> User C alerts
```

One source fetch should serve every user. Matching, alert eligibility, saved state and delivery are user-scoped. A preference update should re-evaluate the user's existing relevant jobs without forcing another source scrape.

## 3. Identity, roles and authentication

### Initial roles
- `admin`: product owner; can manage users, account status, beta access and global source/runtime controls.
- `user`: can manage only their own profile, preferences, applications, notification destinations and integrations.

Keep authorization checks server-side. Hiding admin controls in the UI is not authorization.

### Recommended initial authentication
- Email + password for the first beta, with invite-only account creation or admin-provisioned accounts.
- Hash passwords with Argon2id; never store plaintext passwords.
- Use opaque, cryptographically random server-side sessions. Store only a hash of the session token in the database.
- Deliver the session in an HttpOnly, Secure, SameSite cookie over HTTPS.
- Rotate the session after login and privilege changes; support expiry, logout and server-side revocation.
- Protect state-changing requests with CSRF protection.
- Rate-limit login and password-reset attempts; use generic authentication errors.
- Keep CORS origins explicit. Do not combine wildcard origins with credentialed cookies.
- Do not use the current global config token as a substitute for user authentication.

OAuth/social login can be considered after the first beta; it is not a prerequisite for multi-user isolation.

### Suggested schema (adapt after inspecting the complete current schema)
- `users(id, email_normalized, password_hash, role, status, created_at, updated_at, last_login_at)`
- `sessions(id, user_id, token_hash, created_at, expires_at, last_seen_at, revoked_at)`
- `user_preferences(user_id, preferences_json, version, updated_at)`
- `user_integrations(id, user_id, provider, encrypted_credentials, status, created_at, updated_at)` for later OAuth integrations; do not put secrets in preferences JSON.
- `telegram_connections(user_id, chat_id, verified_at, connected_at, disconnected_at)`

Use unique constraints and indexes for normalized email, active session token hashes, user/provider integration and Telegram identity. Add timestamps and migration/version handling. The schema above is a proposal, not a claim that these tables already exist.

## 4. Per-user preferences and matching

Move candidate-specific values out of the global runtime config. Preferences should include, where relevant:
- Target role families and titles.
- Skills and skill groups.
- Locations, remote/hybrid/on-site rules.
- Candidate experience, minimum/maximum job experience and unknown-experience policy.
- Excluded titles, companies or role families.
- Job age/freshness limits.
- Match threshold and notification threshold.
- Source visibility preferences, where these are genuinely user-level rather than global source health controls.
- Alert channels and quiet hours.

Keep engineering constants, source request budgets, API credentials, collector schedules and global safety gates in system configuration.

### Evaluation model
The existing `job_evaluations` is global and keyed by `job_id`; that cannot represent multiple candidate profiles. Introduce user-scoped evaluations, for example:

`user_job_evaluations(user_id, job_id, preference_fingerprint, evaluated_at, match, score, reasons_json, experience_min_years, experience_max_years, alertable, alertability_reasons_json)`

Use a unique key such as `(user_id, job_id)` for the current evaluation, retaining the fingerprint so preference/rule changes invalidate stale evaluations. If historical evaluation audit is needed later, add a separate history table rather than complicating the first beta.

The matcher must receive an explicit user preference object. It must not read a global candidate profile implicitly. The same normalized job may match one user and be rejected for another.

### Tenant isolation requirements
- Every user-owned read/write query must be scoped by the authenticated `user_id`.
- Never accept a client-supplied user ID as proof of ownership.
- Admin-only endpoints must enforce role checks on the backend.
- Add cross-user tests for preferences, job evaluations, saved jobs, application notes, Telegram links and integrations.
- A user must not be able to enumerate another user's records by changing a URL ID or request payload.
- Test unauthenticated, user-role and admin-role access separately.

## 5. Per-user Telegram connection

### Recommended first-beta approach: one JobBeeper bot, separate user destinations
Use one platform-owned Telegram bot token stored only in server-side environment/secret storage. Each user links their own Telegram chat to their JobBeeper account.

Proposed linking flow:
1. Authenticated user clicks **Connect Telegram** in account settings.
2. Backend creates a high-entropy, single-use, short-lived linking nonce bound to that user.
3. UI opens the official JobBeeper bot deep link with that nonce as the start parameter.
4. User starts the bot. The bot webhook validates the nonce and binds the Telegram `chat_id` to the authenticated user.
5. Mark the connection verified and allow the user to send a test message.
6. User can disconnect/revoke the connection at any time.

The platform bot token is global infrastructure, not a per-user credential. The user's Telegram chat ID and connection state are user-owned data. Do not ask users to paste bot tokens into the browser.

If product requirements later mean each user must bring their own Telegram bot token, treat that as a separate BYO-bot feature: encrypt tokens at rest with a server-side key-management mechanism, never return them to the client, and isolate delivery failures per user. Do not implement BYO bot tokens in the first beta without evidence that users need them.

### Notification ledger
The existing `notification_ledger` is global and keyed only by canonical opportunity. It must become user-scoped before multiple users receive alerts.

Suggested key: `(user_id, canonical_opportunity_id, channel)`.

Persist decision reason, status, attempt count, next retry, claim time, sent time and last error. One user's send failure must not block another user's delivery. Do not replay historical jobs to newly registered users: establish a per-user notification start/baseline and alert only on eligible new opportunities after activation.

## 6. Safe migration from the personal product

Before enabling multi-user accounts:
1. Back up production and development databases and verify integrity.
2. Inventory every global setting and every table/query that assumes one candidate.
3. Create the first admin account and migrate the existing global preferences to that account's `user_preferences`.
4. Associate any existing user-owned tracker/notification state with that owner only.
5. Preserve shared job/source history; do not duplicate raw jobs per user.
6. Preserve existing canonical IDs and source IDs.
7. Suppress historical notification replay for all newly created users.
8. Run migration tests against a copy of the real database.
9. Keep the old config-token path available only as a controlled rollback during migration; remove it after authenticated account flows are verified.
10. Do not switch production until tenant-isolation, notification and rollback gates pass.

The current SQLite database can support an initial small beta if writes are serialized and indexes are added deliberately. Multi-user support does not automatically require microservices or a queue. Reassess PostgreSQL when concurrent write volume, operational needs or scale justify it.

## 7. Beta product scope and feedback loop

First beta should be deliberately small:
- Login/logout and account settings.
- Admin/user roles.
- Individual preference setup/editing.
- Shared job feed with user-specific match score and reasons.
- Server-side search and existing filters.
- Per-user saved/applied state.
- Telegram connect/disconnect and per-user alerts.
- A simple feedback action on a job: relevant, not relevant, wrong seniority, wrong location, poor description, duplicate, already closed.
- Basic admin view of active users and aggregate product/source quality metrics without exposing private user data unnecessarily.

Measure:
- Signup-to-first-preference completion.
- Telegram connection success.
- Jobs seen and relevant jobs per user.
- False-positive/false-negative feedback.
- Time from source publication/discovery to user alert where timestamp precision permits.
- Notification delivery and failure rates.
- User retention and preference edits.

Do not optimize for raw job count. User feedback should improve source coverage, matching quality and usefulness.

## 8. HAPPPY-like referral intelligence — later phase

This is a planned product capability, not currently implemented. The existing `PRODUCT_REVERSE_ENGINEERING_PLAN.md` already names Uplers HAPPPY and a referral-intelligence subsystem, but this document adds the concrete workflow and sequencing.

### Proposed user journey
1. User saves a job and marks it **Applied** (or records an application with date/status).
2. JobBeeper creates an application record tied to that user and canonical opportunity.
3. The system identifies the employer, likely team and relevant people: recruiter, hiring manager, team engineer, alumni or potential referral contact.
4. It gathers contact candidates from public or explicitly authorized sources and records provenance, source, confidence and last-checked time.
5. It ranks people by relevance to the job/company/team and explains why each person may be useful.
6. It drafts a personalized referral request or follow-up using the job details and the user's approved profile context.
7. User reviews and edits the draft.
8. With a user-authorized email integration, create a Gmail/Outlook draft. Do not send automatically in the first release.
9. Track the user's manual send/response status and create a follow-up reminder only when appropriate.
10. Show the contact, message and follow-up history on the application record.

### Future entities
- `applications`: user, canonical opportunity, applied_at, status, resume/version reference, notes.
- `contacts`: normalized identity and public professional profile.
- `application_contacts`: application/contact relationship, role, relevance score, evidence and provenance.
- `contact_sources`: source URL/provider, capture time, confidence and permissions.
- `outreach_drafts`: user, application, contact, channel, draft content, approval state.
- `outreach_events`: draft, created/approved/saved/sent/replied/follow-up events.
- `followup_tasks`: due date, status and user-visible reminder.
- `email_integrations`: provider, OAuth account, encrypted refresh token, scopes, status and revocation state.

All these records must be user-scoped. A contact may be shared/canonicalized across the system only after privacy, provenance and access rules are designed.

### Email and LinkedIn boundaries
- Email integration must use explicit user OAuth consent and least-privilege scopes.
- Start with draft creation, not automatic sending. Require explicit user approval for every outbound message in the first release.
- Store OAuth refresh tokens encrypted server-side; never expose them to the browser or logs.
- LinkedIn research must use public or user-authorized data and permitted official integrations. Do not bypass login walls, CAPTCHA, rate limits or access controls.
- Do not automate LinkedIn connection requests or messages. Present a profile/link and suggested message for the user to act on unless a permitted official API explicitly supports the action.
- Record source provenance and confidence for every contact. Do not invent email addresses or assert that a person is connected to a company without evidence.
- Respect opt-outs, data deletion requests and applicable privacy requirements.

### Phased delivery
- R1: application tracker and manual contact notes.
- R2: authorized people discovery and explainable ranking; no outreach actions.
- R3: email OAuth and draft creation with human approval.
- R4: follow-up reminders and response tracking.
- R5: evaluate permitted LinkedIn integrations and additional contact providers based on demonstrated user value and cost.

The future hiring-post stream (recruiter/employee posts announcing openings) remains separate and later than job ingestion and referral intelligence.

## 9. Immediate engineering sequence

### Gate 0 — finish current work safely
- Preserve commits `093c475` and `727bdb9`.
- Re-run the V2 test suite against the exact feature worktree/image; the running `job-radar-dev-rich-jd:20261106` image passed 149 tests in 18.723 seconds with Docker networking disabled on 2026-11-06.
- Preserve the existing pending handover/benchmark changes in the feature worktree.
- Push the tested feature branch and open/review a development PR; do not deploy production.
- Reconcile GitHub branch head with the feature worktree. The remote `v2-live-radar` and ordinary dev checkout were stale at the time of this audit.

### Gate 1 — multi-user discovery/design (next priority)
- Inventory current schema, global config consumers, API routes, dashboard state and Telegram delivery.
- Produce an endpoint-by-endpoint tenant isolation matrix.
- Finalize migration/backfill plan and session/cookie/CSRF design.
- Add a database migration design and test fixtures before implementing login.

### Gate 2 — authentication and roles
- Implement users, password hashing, sessions, login/logout/current-user endpoints, admin provisioning and backend role enforcement.
- Replace the access-token page with login/account UI.
- Add security and cross-tenant tests.

### Gate 3 — per-user preferences and matching
- Move candidate preferences to user scope.
- Introduce user evaluations and preference fingerprints.
- Update feed, search, job detail and application tracker APIs to use the authenticated user's evaluations.
- Verify preference changes reevaluate that user's jobs only.

### Gate 4 — Telegram fan-out and beta
- Implement one-time Telegram linking.
- Add per-user notification ledger and delivery worker.
- Test one user cannot receive another user's job or notification.
- Invite a small beta cohort and gather structured feedback.

### Gate 5 — application and referral workflow
- Add application tracking before contact discovery.
- Research permitted people/contact sources.
- Add user-authorized email OAuth and draft-only messaging.
- Add reminders and human-reviewed follow-up tracking.

## 10. Current implementation facts and non-facts

**Verified in the 2026-11-06 audit**
- The live development container is `job-radar-dev`, loopback port 8001, image `job-radar-dev-rich-jd:20261106`, image ID `sha256:ef11d75c176f74e4f2d2b0f964582b4f45d0dd416fb7aa7ccffed360c7454941`.
- Production container `v2-radar-1` on port 8000 was running with its prior image and was not changed.
- Live dev `/health` returned OK. Naukri was enabled; LinkedIn, Instahyre, Greenhouse and Ashby were disabled in saved dev config. Notifications were disabled and Telegram credentials were blank.
- Live dev OpenAPI exposes `q` on `GET /api/jobs`; live dashboard sends it. SQLite filters before LIMIT.
- Live dev stores `description_format` and renders Markdown in the job inspector.
- Image file hashes match feature worktree files for `v2/radar.py`, `dashboard/app.js` and `dashboard/index.html`.
- The full V2 unit suite in a throwaway `--network none` container passed 149 tests in 18.723 seconds.

**Not implemented**
- No user registration/login/session system.
- No user roles/RBAC.
- No per-user preferences or per-user job evaluations.
- No per-user Telegram linking or per-user notification ledger.
- No multi-tenant isolation.
- No HAPPPY-like people discovery, email OAuth, outreach drafting, follow-up engine or LinkedIn integration for referrals.

**Operational cautions**
- The remote `v2-live-radar` head was `9c56322c76958bceec65af3d15bd85553e30de53`; the feature branch has since been pushed to GitHub at `c1004955fb2fe394e56f01f5015634d442aa3c5a` and is under draft PR #44 targeting `v2-live-radar` (latest documented PR head at the time of this note: `ab1862714939ad9a51d81b93c235c70c6cae713e`). Do not merge to `main` or deploy production from this PR.
- The ordinary development checkout `/home/ubuntu/job-beeper-dev` is behind the remote branch and has protected local changes/artifacts: `M v2/config.json`, `?? .env.save`, `?? .venv/`, and a config backup. Do not reset, clean, overwrite, or use it as the feature source.
- The feature worktree `/tmp/job-radar-naukri-location-v3` currently has pending documentation modifications and untracked matcher benchmark files. Preserve these; inspect `git status` before staging.
- Production checkout `/home/ubuntu/job-beeper` was observed at `61d8271`, 613 commits behind the fetched `origin/v2-live-radar` ref; the running production container remains on its old image. Never assume the checkout and runtime match. Production remains a separate release gate. Do not pull, rebuild, restart, migrate or send production notifications as part of multi-user implementation planning.
- Termalin encrypted backup job remains DRAFT; local verified snapshots do not mean an off-host encrypted backup exists.

## 11. Read-only tenant-readiness audit — 2026-11-06

The following was verified against the feature worktree and the live development SQLite schema. This is a code/schema inventory, not a migration.

### Current tables and ownership
- Live dev tables: `jobs`, `canonical_opportunities`, `job_evaluations`, `notification_ledger`, `source_runs`, `gemini_shadow_cache`, plus SQLite's `sqlite_sequence`.
- No table currently contains a `user_id` column; there are no `users`, `sessions`, `user_preferences`, `telegram_connections` or application/contact tables.
- `job_evaluations` is keyed by `job_id`; it stores one global match decision per job.
- `notification_ledger` is keyed by `canonical_opportunity_id`; it stores one global notification decision per opportunity.
- `source_runs`, `jobs`, `canonical_opportunities` and `gemini_shadow_cache` are naturally shared/system-level data and should remain so unless a later privacy requirement says otherwise.

### Current config/auth boundary
- Candidate preferences and runtime flags are loaded from one global `/data/config.json` (or the configured DB parent) through `get_config()` and `save_config()`.
- The backend creates/reads one global config token from `JOB_RADAR_CONFIG_TOKEN` or `/data/config_token`; `PUT /api/config` requires `X-Config-Token`.
- `GET /api/config` currently returns the global config without user authentication. Protect this before external beta access; it can disclose the current candidate profile and system settings.
- The frontend stores the config token in browser `sessionStorage`. This is not a user session and must be retired after cookie-session auth is implemented and tested.
- There are no login, logout, current-user, signup/invite, session-refresh, password-reset or role-management routes in the current API.

### Current Telegram boundary
- `v2/telegram.py` obtains both `JOB_RADAR_TELEGRAM_BOT_TOKEN` and one global `JOB_RADAR_TELEGRAM_CHAT_ID` from process environment.
- `credentials_available()` requires both global values. `_claim_one()` selects from the global `notification_ledger` and joins the global `job_evaluations`; delivery has no user dimension.
- The notification worker and source-triggered delivery call this shared module. Per-user fan-out therefore requires a redesigned claim/query/delivery contract, not just adding a chat ID field to the UI.

### Current applied-job boundary
- The dashboard's Applied Jobs feature is stored in browser `localStorage` under `job_beeper_applied_jobs_v1`; it is not persisted in SQLite or associated with a server account.
- This means applied state is browser/device-specific today. Before the referral workflow, migrate it to an authenticated server-side `applications` table, preserving a safe export/import path for the existing browser data.

### API surface to protect and scope
Current API routes include `/api/config`, `/api/jobs`, `/api/opportunities`, `/api/opportunities/{id}`, `/api/jobs/{id}`, `/api/notification-queue`, `/api/daily-summary`, `/api/source-status`, `/api/latency-summary`, `/api/dedupe-candidates` and `/api/llm-shadow-status`, plus `/health`.
- User-facing job/feed/detail routes must join the authenticated user's evaluation and saved/application state.
- Global operational routes (health, source status, latency, LLM diagnostics, dedupe) should be admin-only or return a deliberately sanitized public subset. Do not expose global source internals or another user's diagnostics to ordinary accounts.
- Configuration must be split into user preferences and admin-only system/source configuration. Do not keep returning the full global config to ordinary users.

### First implementation cut suggested by this audit
1. Add auth/session dependencies and role guards without changing collector behavior.
2. Add `users`, `sessions` and `user_preferences`; bootstrap the existing owner/admin and backfill their current global preferences.
3. Protect config and operational routes; move candidate config reads to an explicit user context.
4. Add `user_job_evaluations` and `user_notification_ledger`; keep shared ingestion unchanged.
5. Replace the single chat ID with `telegram_connections` and per-user delivery claims.
6. Move Applied Jobs from browser localStorage to an `applications` API, with a one-time client-side import/export transition.

Do not combine this with a production database migration. Build and test on a copy of the isolated dev DB first, with Telegram delivery disabled.
