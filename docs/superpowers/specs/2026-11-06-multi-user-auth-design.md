# Multi-user authentication foundation — design

**Status:** Implemented on isolated feature branch; not deployed; review/PR pending

## Intent

Prepare JobBeeper for an invite-only beta without allowing one account to see or change the current single-candidate profile, matching decisions, notification queue, or operational controls. The existing V2 service has one global `config.json`, `job_evaluations` keyed only by `job_id`, a global notification ledger, and no identity/session layer. Account creation alone would therefore create a data-isolation vulnerability.

## Goals

- Add persistent user identities with `admin` and `user` roles.
- Add secure email/password login, logout, current-session inspection, and server-side session revocation.
- Store only Argon2id password hashes and hashes of opaque random session/CSRF tokens.
- Use an HttpOnly, Secure, SameSite=Lax session cookie and a CSRF token required on state-changing authenticated requests.
- Bootstrap the first admin through a one-time CLI command, not a public registration endpoint or hard-coded credentials.
- Require an authenticated admin session for every existing `/api/*` product/operational endpoint during this transitional slice. Keep `/health`, login, and static assets public. This deliberately prevents ordinary users from accessing the legacy global candidate data until user-scoped matching ships.
- Keep collectors, job ingestion, source schedules, and existing data schema unchanged apart from additive auth tables.
- Keep all work in an isolated branch and test database. No production migration, deployment, Telegram delivery, or source activation.

## Non-goals for this slice

- Public self-registration, email verification, password reset, OAuth, multi-factor auth, or user invitations.
- Per-user preferences, evaluations, saved/applied jobs, Telegram linking/fan-out, or referral workflows. These are subsequent milestones.
- Changing the shared ingestion architecture or migrating existing global preferences in production.
- Making the current dashboard usable by ordinary `user` accounts; only the admin role can access legacy global dashboard APIs until tenant-scoped data is implemented.

## Approaches considered

1. **Cookie-backed server sessions in SQLite (selected).** Fits the existing single-process FastAPI/SQLite service, supports revocation and roles, and avoids putting bearer tokens in browser storage. Add a session table and explicit dependencies. Trade-off: session storage and rate limiting are database-backed and writes must use the existing locking discipline.
2. **JWT access/refresh tokens.** Common for distributed APIs, but adds refresh rotation, signing-key management, revocation complexity, and browser token-storage risks without a current multi-service requirement.
3. **External identity provider.** Reduces password handling but adds provider setup, account-linking and deployment dependencies before the product has a beta. Revisit if social login becomes a requirement.

## Design decisions

- Add `users`, `sessions`, and `login_attempts` tables with foreign keys, unique normalized email, role/status constraints, token-hash uniqueness, expiry/revocation timestamps, and supporting indexes.
- Use Argon2id from `argon2-cffi`; return the same generic 401 for unknown email and wrong password.
- Generate opaque session and CSRF values with `secrets.token_urlsafe(32)`. Store SHA-256 hashes only. Session lifetime is seven days; logout revokes the server-side row and clears both cookies.
- Cookies: `job_beeper_session` is HttpOnly; `job_beeper_csrf` is readable by same-origin JavaScript. Both use Path=/ and SameSite=Lax. Session cookie Secure is true by default; a development-only environment override may disable Secure for loopback HTTP. CSRF-protected writes require matching cookie/header values and a matching stored hash.
- Login attempts are atomically reserved and limited to five attempts per normalized-email/IP pair in a 15-minute fixed window using persisted hashed email/IP keys; a successful login clears that pair’s failure counter. Do not trust arbitrary forwarded-IP headers. Return 429 after the threshold and do not reveal whether an email exists.
- First admin is created with `python3 -m v2.auth_admin create-admin --email ...`; password is prompted with `getpass`, never passed as a command-line argument or logged. The command atomically refuses to create a second bootstrap admin, including concurrent invocations. Until an invitation UI/API is added, the admin can provision ordinary beta users with `python3 -m v2.auth_admin create-user --email ...`; the password is prompted and the command can create only the `user` role.
- Auth helpers live in `v2/auth.py`; FastAPI routes/dependencies and legacy route guards live in `v2/radar.py`; dashboard login/session UX lives in `dashboard/index.html`, `dashboard/app.js`, and `dashboard/styles.css`; tests live in `v2/test_auth.py` and targeted additions to `v2/test_radar.py`.
- `/api/auth/login` is public; `/api/auth/me` requires a valid session; `/api/auth/logout` requires a valid session and CSRF validation. All existing `/api/*` routes require `admin`. `/health` remains public and must not expose config, user, or secret data.
- Do not rely on the existing `X-Config-Token` as identity. Retire its browser UI use; remove the compatibility token only after the session flow is verified and documented. The initial implementation may retain the backend config-token helper temporarily for CLI/rollback, but no ordinary browser API path may use it.

## Security and rollout constraints

- Do not deploy this slice to production. The current global config and evaluation model are not yet tenant-aware.
- Keep source/collector behavior and notification worker disabled/unchanged in tests; no real Telegram sends.
- Use a copied/test SQLite database for all schema and migration tests.
- Before any future production migration, verify a restorable backup and migrate the existing candidate profile to the initial admin's `user_preferences` in a separate, reviewed migration.
- Do not trust client-supplied user IDs. Resolve the user from the server-side session for every protected request.

## Acceptance criteria

- Passwords and session/CSRF secrets are never stored in plaintext.
- Login is generic on failure, rate-limited, and rotates to a new opaque session.
- Logout revokes the session; replaying its old cookie fails.
- Session expiry, disabled users, missing/invalid CSRF, and role denial are tested.
- Every existing API endpoint except explicit auth endpoints and `/health` rejects anonymous access and rejects the `user` role; an `admin` session retains current API behavior.
- No production container, database, config, volume, scheduler, or notification state changes.
