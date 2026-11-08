> **Current source of truth:** [Product Vision and Delivery Roadmap](PRODUCT_VISION_AND_DELIVERY_ROADMAP.md). This file remains detailed design/history; when priorities conflict, the product vision roadmap is authoritative.

# JobBeeper Multi-User and Referral Intelligence Roadmap

**Status:** Authentication foundation PR #45 merged into `v2-live-radar` as `dd7aeb1`; user preferences, onboarding and user-scoped job evaluations/feed are implemented on `feat/user-preferences-evaluations-20261106` but not yet merged or deployed. Opportunity list/detail tenant scoping and final PR review remain. Telegram fan-out and server-side applications remain later milestones.
**Date:** 2026-11-06 (updated after PR #45 merge)
**Priority:** PAUSED behind ingestion reliability and broad source coverage (priority reset 2026-11-07)
**Repository:** AvinashBhalla/job-beeper
**Integration branch:** `v2-live-radar`
**Current feature branch/worktree:** `feat/user-preferences-evaluations-20261106`, `/tmp/job-radar-user-preferences`

## 1. Product direction

JobBeeper is moving from a personal job radar to a multi-user job discovery and job-search workflow product.

The long-term product objective remains multi-user accounts, independent preferences and per-user alerts. However, the immediate objective is now to make the shared ingestion engine reliably discover fresh jobs from a broad set of permitted sources. Multi-user onboarding and Telegram are paused until the ingestion acceptance gates in `docs/INGESTION_FIRST_ROADMAP.md` pass.

The long-term direction includes a HAPPPY-like referral-intelligence workflow inspired by Uplers HAPPPY: after a user applies to a job, help identify relevant people at that employer, prepare referral/follow-up outreach, and track the follow-up process using authorized LinkedIn research and a user-authorized email integration.

**Priority order (updated 2026-11-07; supersedes the earlier multi-user-first plan):**
1. Audit and improve shared job ingestion: coverage, freshness, request budgets, 429 behavior, timestamp precision, deduplication and source health.
2. Reverse-engineer observable JobBeeper UI/network behavior with a sanitized HAR from the user's authorized session; do not infer or extract private backend implementation.
3. Build a measured source catalog and add permitted public/authorized adapters incrementally toward 100 useful sources.
4. Validate real freshness and unique-job yield over canary windows; do not claim 100-source or instant coverage before evidence.
5. Resume this multi-user roadmap (including PR #46, resume onboarding and Telegram) after ingestion gates pass.
6. Build application tracking and referral intelligence later; hiring-post discovery remains later still.

Do not expand signup, resume parser or Telegram now. Keep PR #46 draft and isolated; no dev bot setup is needed during the ingestion phase.

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

### Gate 0 — current search and description work
- PR #44 was squash-merged into `v2-live-radar` as commit `7b61d74`; its duplicate intermediate PRs #42 and #43 were closed and redundant remote branches deleted.
- The production service was not deployed or changed by that merge.

### Gate 1 — multi-user discovery/design (complete)
- Audited current schema, global config consumers, API routes, dashboard state and Telegram delivery.
- Recorded the endpoint-level tenant boundary and migration/backfill design in this roadmap and the auth design spec.
- Confirmed the old global profile/evaluation/notification model cannot be exposed to ordinary users.

### Gate 2 — authentication and roles (implemented on feature branch; not deployed)
- Added `users`, `sessions`, `login_attempts` and `login_account_attempts` tables; Argon2id password hashing; opaque seven-day cookie sessions with hashed session/CSRF tokens; same-origin login-Origin validation; dashboard rejects external `?api=` overrides before sending credentials; concurrency-safe per-IP and account-wide login-attempt reservations (five per email/IP and twenty per account across IPs per 15 minutes) with hashed email/IP keys; logout/revocation.
- Added `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`, a one-time first-admin CLI and an ordinary-user provisioning CLI.
- All existing legacy `/api/*` endpoints require an admin session; unsafe admin requests require CSRF; every API response is `Cache-Control: no-store`. `/health` is a minimal public liveness endpoint. Login validates browser Origin and supports `JOB_BEEPER_PUBLIC_ORIGIN` behind TLS termination.
- Replaced the dashboard config-token flow with cookie-session login/account UI. Ordinary users see a holding screen and do not load the legacy global job feed.
- Final V2 suite passed 189 tests in 79.321 seconds in a throwaway `--network none` container (one Node-only dashboard contract test is skipped inside that Python image); the Node-enabled dashboard contract suite passed 4/4 separately in 0.655 seconds.
- PR #45 was merged on 2026-11-06 into `v2-live-radar` as squash commit `dd7aeb1eea4790564a73367df90f7d4a07e012ea`. The remote feature branch has been removed. This is a code merge only: no live dev or production container/database/config was changed. CI passed on the final PR head; the Codex re-review remained stuck in running, so the final merge relied on manual review, resolved inline threads and green CI.

### Gate 3 — per-user preferences and matching (implemented on draft PR #46; smoke test pending)
- **Onboarding gate:** a user must configure at least one target role and at least one location before the personalized feed unlocks. Do not show an empty/global feed to incomplete users; show a focused setup screen with the missing fields and save action.
- New users start with empty candidate preferences. Never copy the admin's profile into a new user's account. The first admin's existing global candidate profile is migrated into that admin's preference row only.
- Keep ingestion, normalized jobs, canonical opportunities, source health, polling and provider credentials shared/system-level. Keep source/runtime controls admin-only.
- Introduce `user_preferences` and `user_job_evaluations` keyed by authenticated `user_id`; matcher receives explicit preference data and never falls back to a global candidate profile for a normal user.
- Implemented: preferences, job feed, job detail and daily summary are scoped to the authenticated user. Ordinary users do not receive global notification-ledger details. Opportunity list/detail endpoints remain admin-only and must be tenant-scoped before those views are exposed to users.
- Preference saves re-evaluate the user's stored jobs without triggering another scrape. New shared ingestions evaluate for each active, configured user.
- Implemented: normal users use a separate minimal workspace and never load the admin app shell or its browser-local applied/saved state. Server-side applications remain a later milestone.
- Synthetic migration/tenant tests pass. A read-only copy of the live dev DB was not needed or used; do not run migrations against the live dev or production database in this implementation milestone.
- PR #46 is draft and CI run #1222 passed on code head c5201ce. Manual browser smoke test and final security review remain before marking the PR ready.

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

**Implemented on feature branch `feat/multi-user-foundation-20261106` (not deployed)**
- SQLite identity tables: `users`, `sessions`, `login_attempts`, `login_account_attempts`.
- Argon2id password hashing, normalized email identity, `admin`/`user` roles, active/disabled account status, seven-day opaque sessions, hashed session/CSRF tokens, revocation and atomic five-attempt/15-minute per-email/IP and twenty-attempt/15-minute per-account-across-IPs throttles (email/IP keys are hashed; malformed emails are throttled too).
- Auth endpoints: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`.
- All existing legacy API routes require an admin session; state-changing admin requests require CSRF; all `/api/*` responses are no-store. `/health` is public and returns only liveness metadata.
- Server-side CLI: `python -m v2.auth_admin create-admin --email ...` creates the first admin only; `python -m v2.auth_admin create-user --email ...` provisions ordinary beta users.
- Dashboard cookie-session client, login screen, account/logout controls and non-admin holding screen. No config token is stored in browser sessionStorage or sent by the dashboard.

**Not implemented yet**
- Per-user preferences, `user_preferences`, per-user job evaluations and personalized feed/search/detail responses. The current global config and global evaluation model remain admin-only.
- Per-user Telegram linking, `user_notification_ledger`, fan-out and user-specific notification preferences.
- Server-side applications/saved jobs; Applied Jobs still uses browser localStorage and must be migrated before multi-user use.
- Public signup/invites, password reset, OAuth/MFA, self-service role management, HAPPPY-like contact discovery, email OAuth/drafts, follow-up engine or LinkedIn referral integrations.

**Current runtime is deliberately unchanged**
- The running development image remains `job-radar-dev-rich-jd:20261106`; it does not contain these auth changes and its live SQLite DB has not had the auth tables created. The feature code creates the tables additively at application startup when eventually deployed.
- Production `v2-radar-1` remains on its previous image. No database, config, volume, scheduler, source or notification changes were made by this auth implementation.

**Verification**
- Final V2 suite: 186 tests passed in 87.493 seconds in a throwaway Docker container with networking disabled (one Node-only dashboard test is skipped inside that image).
- Node-enabled dashboard contract: 4/4 passed on the VM host in 0.611 seconds. Both dashboard JS files passed esbuild 0.19.12 parse/build checks. Backend syntax checks passed.
- No live provider/LLM calls, Telegram sends or runtime deployment occurred.

**Operational cautions**
- Base branch `v2-live-radar` includes merged PR #44 at `7b61d74`. Current feature branch is `feat/multi-user-foundation-20261106`, worktree `/tmp/job-radar-naukri-location-v3`, with auth commits `9ffed3f`, `93dea33`, `44a052f`, `27a77cd` and `ea463cb` above that base; CI/documentation commits are also present. The branch is pushed and PR #45 is open against `v2-live-radar`.
- The ordinary development checkout `/home/ubuntu/job-beeper-dev` has protected local changes/artifacts (`M v2/config.json`, `.env.save`, `.venv/` and a config backup); do not reset, clean, overwrite or use it as the feature source.
- Production checkout `/home/ubuntu/job-beeper` was observed at `61d8271`, 613 commits behind its fetched `origin/v2-live-radar` ref. The running production container remains on its old image. Never assume checkout and runtime are synchronized. Do not pull, rebuild, restart, migrate or send production notifications.
- Termalin encrypted backup job remains DRAFT; local verified snapshots do not mean an off-host encrypted backup exists.
- `JOB_BEEPER_COOKIE_SECURE` defaults to `true`; the dashboard must be served over HTTPS. Only set it to `false` in an isolated loopback-only development environment using HTTP. Never disable Secure on a public endpoint.


## 11. Read-only tenant-readiness audit — 2026-11-06 (pre-auth baseline)

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


## 12. Authentication foundation implementation — 2026-11-06

The read-only audit above records the live single-user runtime before the auth feature was implemented. The following code now exists on the isolated feature branch; it is not deployed to either live container.

### Runtime contract when this branch is released
- Auth schema is created additively from `init_db()`; existing `jobs`, canonical opportunities, evaluations and notification tables are not migrated or rewritten by this slice.
- First-admin bootstrap and ordinary-user provisioning are operator-only CLI commands. From the app container (`WORKDIR /app`, `JOB_RADAR_DB=/data/jobs.db`):
  - `python -m v2.auth_admin create-admin --email admin@example.com`
  - `python -m v2.auth_admin create-user --email beta-user@example.com`
  Both commands prompt for the password twice; no password is accepted on the command line. Bootstrap refuses a second admin.
- Login sets `job_beeper_session` (HttpOnly) and `job_beeper_csrf` (readable by same-origin JS) cookies with `Secure`, `SameSite=Lax`, `Path=/` and a seven-day max age. Session and CSRF values are stored only as SHA-256 hashes.
- Login requests with a browser `Origin` header must match the configured/request origin, preventing login CSRF. All API responses carry `Cache-Control: no-store`. The configured `JOB_BEEPER_PUBLIC_ORIGIN` is used when set. If TLS terminates at a reverse proxy, set `JOB_BEEPER_PUBLIC_ORIGIN` to the exact browser-visible origin when Uvicorn does not trust proxy headers. The loopback-only dev Compose service defaults `JOB_BEEPER_COOKIE_SECURE=false` for SSH-tunnel use; production keeps the default `true`. The secure-cookie setting requires HTTPS outside that isolated development service.
- Ordinary `user` accounts can inspect their session and sign out but cannot use legacy global feed/config/diagnostic endpoints. Their holding page intentionally does not fetch job data.
- This is a transitional safety boundary, not complete multi-tenancy: candidate preferences and job evaluations remain global and admin-only until the next milestone adds user-owned preferences/evaluations and re-scopes feed/detail queries.

### Next implementation milestone
Implement `user_preferences` and `user_job_evaluations`, migrate the current global candidate profile to the initial admin on a copied DB, and make job feed/search/detail responses explicitly use the authenticated user's evaluation. Keep source ingestion shared. Do not add per-user Telegram delivery until user-scoped evaluation and notification-ledger tests pass.


## 2026-11-07 — Priority status

The product roadmap continues to prioritize ingestion for production readiness, but the owner requested on 2026-11-07 that ongoing authentication/signup, resume parser and per-user Telegram work continue in parallel on isolated PR #46. Keep it on `feat/user-preferences-evaluations-20261106`, draft and not promoted to shared dev or production. The owner is creating a dedicated dev bot; live Telegram E2E waits for private credentials and an approved public HTTPS webhook endpoint. The JobBeeper network investigation proceeds independently. Ingestion acceptance gates still govern any production release and source expansion.


## 2026-11-07 — Parallel execution checkpoint (supersedes pause above)

The owner explicitly requested parallel execution rather than waiting for the ingestion milestones to finish before continuing the existing feature branch. Continue this roadmap's auth, preferences, resume and Telegram implementation work in parallel with the ingestion-first roadmap. Do not change production priority or deployment boundaries.

- Branch/PR: `feat/user-preferences-evaluations-20261106`, PR #46 draft.
- Latest commit: `51db2f9`; GitHub V2 CI run `42370884022` passed.
- Isolated suite: **272 passed, 1 skipped**; notification tests 12/12; resume parser tests 15/15; Google OAuth tests 15/15.
- Isolated feature runtime healthy on 8002. Shared dev 8001 and production 8000 unchanged.
- Pending: dedicated Telegram bot configuration, public HTTPS webhook and full link/opt-in/new-match/delivery/opt-out smoke test. Production bot remains untouched.
