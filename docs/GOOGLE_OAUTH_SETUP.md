# Google OAuth beta signup setup

This enables open beta registration with Google. Every new Google identity is provisioned as role=user. Public signup cannot create an administrator.

## Google Cloud setup

1. Open Google Cloud Console and select the project that will own Job Beeper sign-in.
2. Configure the OAuth consent screen. Choose the audience appropriate for the beta and add the authorized test users if the app remains in Testing.
3. Create an OAuth Client ID with application type **Web application**.
4. Add the exact browser origin under Authorized JavaScript origins:
   - Isolated SSH-tunnel dev: `http://localhost:18002`
   - Production: the final HTTPS Job Beeper origin, once selected.
5. Add the exact callback URI under Authorized redirect URIs:
   - Isolated SSH-tunnel dev: `http://localhost:18002/api/auth/google/callback`
   - Production: `https://YOUR_PRODUCTION_HOST/api/auth/google/callback`
6. Keep the generated client secret private. Do not commit it, paste it into chat, or put it in dashboard JavaScript.

Google requires the redirect URI to match exactly. The dev HTTP callback is permitted because it is a loopback address; production must use HTTPS.

## Environment variables

Set these in the environment file used by the relevant Compose service:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`

For the older shared-dev Compose project, the env file is `/home/ubuntu/job-beeper-dev/.env`. Do not print the file or its values in logs or chat. For the current PR #46 isolated feature Compose project, use `/tmp/job-radar-user-preferences/.env.feature` as documented in the dedicated section below; do not configure shared dev for this feature test.

If any value is missing or the redirect URI is invalid, the API reports Google sign-in disabled and the login page hides the Google signup control. Password login continues to work.

## Isolated feature branch configuration

The current auth/resume/Telegram implementation is being tested in the isolated Compose project `job-radar-user-preferences` on loopback port 8002. Its `v2/docker-compose.feature.yml` now passes `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` and `GOOGLE_OAUTH_REDIRECT_URI` from the private `.env.feature` file. The values are optional; Google signup stays hidden while any is blank.

Before enabling Google sign-in, decide the actual browser-visible local origin used to reach port 8002 (for example, an SSH tunnel forwarding remote 8002 to local 18002). Register that exact origin and callback in Google Cloud. The redirect URI must be exactly `<browser-origin>/api/auth/google/callback`, and for local HTTP it must use `localhost` or `127.0.0.1`; do not assume the earlier shared-dev `18001` callback is correct for this separate feature service. Add all three values to `/tmp/job-radar-user-preferences/.env.feature`, then recreate only the feature Compose service using the command in `docs/TELEGRAM_PER_USER_SETUP.md`. Do not put OAuth credentials in chat or Git.

## Flow and security controls

- Authorization Code flow with OpenID Connect scopes `openid email profile`.
- Cryptographically random state and nonce; state is stored hashed in SQLite and is one-time, short-lived, and bound to an HttpOnly, SameSite=Lax browser cookie.
- PKCE S256 verifier/challenge.
- Authorization code exchanged server-side; client secret never reaches the browser.
- Google ID token signature, issuer, audience and expiry are verified by Google's maintained `google-auth` library. Only `email_verified=true` identities are accepted.
- A stable Google subject is linked to one Job Beeper account. A verified Google email can link to an existing same-email account; a subject cannot be attached to another account. Disabled accounts are rejected.
- New accounts receive role=user, a random unusable password hash, and empty user preferences. Existing password login remains available.
- Existing opaque Job Beeper session and CSRF cookies are issued after successful Google sign-in.
- OAuth state is validated against the HttpOnly browser cookie and consumed before handling either a successful callback or a provider cancellation/error. Mismatched, missing or replayed state fails closed. State is also consumed before later configuration/token/account-link checks, so failures cannot leave a reusable authorization attempt. Browser-visible errors are generic; logs record only the exception type.

## Routes

- `GET /api/auth/google/status` — indicates whether all required settings are configured.
- `GET /api/auth/google/start` — creates state/nonce/PKCE and redirects to Google.
- `GET /api/auth/google/callback` — validates state, exchanges code, verifies identity, links/creates a user and issues a session.

## Rollout checklist

- [ ] Add OAuth client ID, secret and exact callback URI to the dev environment file.
- [ ] Recreate only the isolated dev service; do not change production.
- [ ] Confirm `/api/auth/google/status` returns `{"enabled":true}`.
- [ ] Test a brand-new Google account and confirm role=user and incomplete preferences.
- [ ] Test an existing account with the same verified email and confirm identity linking.
- [ ] Test state mismatch/replay and unverified email rejection.
- [ ] Test a disabled account and a subject/email collision.
- [ ] Confirm admin-only controls remain hidden for the new member.
- [ ] Only after dev smoke test approval, configure the production HTTPS callback and separately plan a production deployment.

No real Google OAuth credentials or live Google authorization flow have been configured or tested as part of this code change.

## 2026-11-07 — Isolated OAuth smoke-test result and remaining product notes

The owner completed the live Google OAuth smoke test against the isolated feature instance using the localhost:18002 tunnel.

- The client ID, client secret and callback URL are saved only in the server-side /tmp/job-radar-user-preferences/.env.feature file (mode 600, git-ignored). The feature Compose passes them to the container. Do not copy the values into Git, chat, screenshots or logs.
- The OAuth status endpoint returned enabled, and the OAuth start route redirected to Google's authorization host with the expected callback URI.
- The owner confirmed the end-to-end OAuth sign-in succeeded and the resume parser worked in the same test session.
- Production (8000) and shared development (8001) were not changed. Only the isolated feature instance (8002) has Google OAuth configured.
- Google's consent page displayed "n8nApp" rather than "JobBeeper". The OAuth client's internal name is not the public consent-screen brand. Before public rollout, update Google Auth Platform Branding/app name and review logo, support email, privacy policy and terms URLs. This is cosmetic/configuration backlog, not a blocker for the isolated test.
- The local test callback is http://localhost:18002/api/auth/google/callback; do not reuse it for a remotely hosted production origin. Production needs its own HTTPS origin, callback registration and separately managed credentials.

### Owner UAT backlog (not fixed in this pass)

1. Email/password signup page — product backlog, not current priority. The login UI currently exposes "Continue with Google" but no public email/password registration flow. Existing password login is not the same as a self-service signup page. Design email registration, verification, password reset and abuse controls as a separate scope.
2. Preferences-save error not surfaced — UI bug to reproduce. During the owner's save test, the Network panel showed a preferences request response with detail: "At least one target role is required before accessing the job feed." The UI visibly contained a "Graphic designer" target-role chip, but the frontend did not show an error. The screenshot does not establish the HTTP status or request payload, so the root cause is unconfirmed. Reproduce with a redacted request/response, determine why the backend validation sees no role, and display actionable field-level/global feedback on failure.
3. Google consent branding — cosmetic backlog. Replace the visible "n8nApp" label with "JobBeeper" through Google Auth Platform Branding settings before broader beta rollout.

These items are intentionally recorded, not changed as part of the current ingestion-priority work.
