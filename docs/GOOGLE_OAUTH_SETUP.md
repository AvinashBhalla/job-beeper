# Google OAuth beta signup setup

This enables open beta registration with Google. Every new Google identity is provisioned as role=user. Public signup cannot create an administrator.

## Google Cloud setup

1. Open Google Cloud Console and select the project that will own Job Beeper sign-in.
2. Configure the OAuth consent screen. Choose the audience appropriate for the beta and add the authorized test users if the app remains in Testing.
3. Create an OAuth Client ID with application type **Web application**.
4. Add the exact browser origin under Authorized JavaScript origins:
   - Isolated SSH-tunnel dev: `http://127.0.0.1:18001`
   - Production: the final HTTPS Job Beeper origin, once selected.
5. Add the exact callback URI under Authorized redirect URIs:
   - Isolated SSH-tunnel dev: `http://127.0.0.1:18001/api/auth/google/callback`
   - Production: `https://YOUR_PRODUCTION_HOST/api/auth/google/callback`
6. Keep the generated client secret private. Do not commit it, paste it into chat, or put it in dashboard JavaScript.

Google requires the redirect URI to match exactly. The dev HTTP callback is permitted because it is a loopback address; production must use HTTPS.

## Environment variables

Set these in the environment file used by the relevant Compose service:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`

For the isolated dev Compose project, the env file is `/home/ubuntu/job-beeper-dev/.env`. Do not print the file or its values in logs or chat. After setting values, recreate only the dev radar service with the documented dev Compose command so the container receives the new environment.

If any value is missing or the redirect URI is invalid, the API reports Google sign-in disabled and the login page hides the Google signup control. Password login continues to work.

## Flow and security controls

- Authorization Code flow with OpenID Connect scopes `openid email profile`.
- Cryptographically random state and nonce; state is stored hashed in SQLite and is one-time, short-lived, and bound to an HttpOnly, SameSite=Lax browser cookie.
- PKCE S256 verifier/challenge.
- Authorization code exchanged server-side; client secret never reaches the browser.
- Google ID token signature, issuer, audience and expiry are verified by Google's maintained `google-auth` library. Only `email_verified=true` identities are accepted.
- A stable Google subject is linked to one Job Beeper account. A verified Google email can link to an existing same-email account; a subject cannot be attached to another account. Disabled accounts are rejected.
- New accounts receive role=user, a random unusable password hash, and empty user preferences. Existing password login remains available.
- Existing opaque Job Beeper session and CSRF cookies are issued after successful Google sign-in.
- OAuth state is consumed even when token verification or account linking fails. Browser-visible errors are generic; logs record only the exception type.

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
