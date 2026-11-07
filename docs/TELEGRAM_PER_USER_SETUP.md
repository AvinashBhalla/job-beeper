# Telegram account linking — setup and operations

## Current implementation boundary

The feature branch implements account linking plus a separate, explicit per-user notification opt-in and delivery path. Linking alone never enables notifications. Member alerts default off and use their own settings/ledger and linked private chat; the legacy global Telegram destination remains reserved for admin/operational alerts. The owner supplied the intended dedicated development bot handle `@YourJobBeeperDevBot`; the BotFather token and webhook secret are not configured yet. A real-bot end-to-end smoke test also requires a public HTTPS webhook endpoint. Quiet hours, per-user time zones, configurable frequency controls and delivery history are not implemented yet.

## Server configuration

Configure these variables in the deployment's private environment/secret store; never commit them or paste their values into chat:

- `JOB_RADAR_TELEGRAM_BOT_TOKEN` — bot token from BotFather. The existing production bot token is already configured for the legacy admin/operational outbound notifier. The same bot can technically be reused for member linking and member DMs; Telegram's webhook handles inbound updates while `sendMessage` continues to handle outbound messages.
- `JOB_BEEPER_TELEGRAM_BOT_USERNAME` — public bot username, without `@`. Owner-supplied value: `YourJobBeeperDevBot` (public handle `@YourJobBeeperDevBot`).
- `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET` — random 1–256 character value using only letters, digits, `_` or `-`. Generate a strong value with Python `secrets.token_urlsafe(32)` or `openssl rand -hex 32`. It is a separate secret from the BotFather token.

### Existing production bot discovery (2026-11-07)

- Read-only `getMe` against the token already present in `/home/ubuntu/job-beeper/.env` confirmed the existing bot username is **`Qdhorvbot`**. The token itself was never printed or copied into this repository/chat.
- Read-only `getWebhookInfo` reported **no webhook currently configured**, zero pending updates and no last webhook error. This means there is no existing Telegram webhook URL to preserve or migrate.
- The production `.env` currently contains both `JOB_RADAR_TELEGRAM_BOT_TOKEN` and `JOB_RADAR_TELEGRAM_CHAT_ID`. The old production Compose file currently passes only those two variables; it does not yet pass `JOB_BEEPER_TELEGRAM_BOT_USERNAME` or `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET`.
- Searches across the known production, dev and feature checkouts found no `getUpdates`, `setWebhook`, or `deleteWebhook` consumer. The existing `v2/telegram.py` notifier only calls outbound `sendMessage` and continues to use the global admin chat ID. Thus reuse of the same bot is technically compatible with the code paths inspected: inbound `/start` updates will be handled by the new webhook, while admin/member outbound messages use `sendMessage`.
- **Not configured or changed:** no webhook was registered, no production environment variable was added, no production Compose file/container was modified, and no live bot message was sent as part of this inspection. The production checkout is stale (613 commits behind the active branch), so do not deploy from it or treat it as containing the new webhook endpoint.
- **Decision:** reuse of the existing production bot is a viable option for the eventual production release. Do not repoint it yet. First deploy and smoke-test the webhook endpoint through an approved release. If a separate development smoke test is needed, use a dedicated test bot so production bot updates are not diverted to an unfinished/dev endpoint. Before registering the production webhook, set the public username to `Qdhorvbot`, add a newly generated webhook secret to the private production environment, ensure the deployed production Compose/app passes both values, then register the webhook to the deployed HTTPS `/api/telegram/webhook` endpoint. Preserve the existing global admin chat ID and verify its outbound notifications still work after release.

The application requires all three values before it exposes the connect action. Development and isolated feature Compose files default to blank values. The isolated feature Compose now accepts the three dev-bot values through a private `--env-file`; use the tracked `.env.feature.example` as a template, copy it to the ignored `.env.feature`, and never commit that private file. The currently deployed production checkout is older and does not yet pass the two new values; update them only as part of an approved release. No live configuration has been made by this change.

## Isolated dev-bot environment

The isolated feature project is `job-radar-user-preferences`, using `v2/docker-compose.feature.yml`, the separate `radar-feature-data` volume and loopback-only host port `127.0.0.1:8002`. Its Compose file reads `JOB_RADAR_TELEGRAM_BOT_TOKEN`, `JOB_BEEPER_TELEGRAM_BOT_USERNAME` and `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET` from a private environment file. From the repository root, after securely creating `.env.feature` from `.env.feature.example`, run:

```bash
sudo docker compose --env-file .env.feature -p job-radar-user-preferences -f v2/docker-compose.feature.yml up -d --build
```

The `.env.feature` file is git-ignored. Keep `JOB_RADAR_TELEGRAM_CHAT_ID` blank in this feature environment so legacy admin messages cannot be routed to a production chat. The app is intentionally bound to loopback; port 8002 is not a public Telegram webhook. Do not register `setWebhook` until an approved public HTTPS endpoint has been configured for this isolated service.

### Create and configure the dev bot

1. In Telegram, open the official **@BotFather** account and send `/newbot`. Enter a display name, then a unique username ending in `bot`. The intended handle supplied by the owner is `@YourJobBeeperDevBot`; BotFather must confirm that it is available and create it.
2. BotFather returns a bot token. Keep it private. Do not paste it into this chat, screenshots, GitHub or repository files. Open `@YourJobBeeperDevBot` and press **Start** once the bot has been created.
3. Generate the separate webhook secret on Windows PowerShell (on the owner's PC):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

If `python` is not on PATH, try `py -c "import secrets; print(secrets.token_urlsafe(32))"`. The command can also be run on the Ubuntu server as `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. It works from any directory. Save the output privately; do not send it in chat.

4. On the Ubuntu server, from the feature checkout, create the private file and edit it:

Run these commands in an Ubuntu server shell where the feature checkout exists (not in Telegram and not in a Windows-only local folder):

```bash
cd /tmp/job-radar-user-preferences
cp .env.feature.example .env.feature
chmod 600 .env.feature
nano .env.feature
```

Set `JOB_RADAR_TELEGRAM_BOT_TOKEN` to the BotFather token, leave `JOB_BEEPER_TELEGRAM_BOT_USERNAME=YourJobBeeperDevBot` (no `@`), and set `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET` to the random value generated above. Leave `JOB_RADAR_TELEGRAM_CHAT_ID` out of the file; Compose forces it blank. Leave the three `GOOGLE_OAUTH_*` values blank until Google OAuth is separately configured. Save the file and exit.

5. Recreate only the isolated feature service so it receives the private values:

```bash
sudo docker compose --env-file .env.feature -p job-radar-user-preferences -f v2/docker-compose.feature.yml up -d --build
```

The file is ignored by Git. Never display it with `cat`, commit it, or send its contents in chat. Verify only that the variables are present (not their values) and that the dashboard's Telegram connection status reports configured.

6. Do **not** set the webhook yet. The feature service currently listens only on `127.0.0.1:8002`, which Telegram cannot reach. First arrange an approved, temporary public HTTPS route to this isolated service; only then register the dev bot webhook using the secret header mechanism below. Never point the production bot at a development tunnel.

## Webhook registration

The deployment must have a publicly reachable HTTPS origin. Register this endpoint with Telegram:

`https://YOUR_PUBLIC_HOST/api/telegram/webhook`

Use Telegram's `setWebhook` API with the bot token, the HTTPS URL, and `secret_token` equal to `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET`. Do not put the token or secret in a repository, issue, screenshot, or chat message. Do not configure a webhook to a loopback-only dev port. For development, create a separate test bot and use a dedicated HTTPS tunnel/domain; never repoint the production bot to a temporary tunnel.

After registration, verify the webhook configuration using Telegram's `getWebhookInfo` API from the secured server environment. Inspect only URL, pending update count and last error fields; do not print bot token or secret. Telegram sends `X-Telegram-Bot-Api-Secret-Token`; the application compares it in constant time before parsing the update.

## User flow

1. Member signs in and opens Matching Preferences.
2. The optional Telegram panel requests a short-lived one-time token from `POST /api/telegram/link`.
3. The UI displays a deep link to `https://t.me/BOT_USERNAME?start=OPAQUE_TOKEN`.
4. Member opens the private bot chat and presses Start. Telegram posts `/start OPAQUE_TOKEN` to the webhook.
5. The server hashes tokens at rest, expires them after 10 minutes, invalidates previous pending tokens when a new one is requested, and consumes a token atomically. Only private chats are accepted. A Telegram chat ID can be linked to only one Job Beeper account; each Job Beeper user has one active chat mapping.
6. Member can disconnect from the same panel. Relinking replaces their own prior chat mapping. Disconnect does not affect other users.

## API surface

- `GET /api/telegram/status` — authenticated member connection state and whether server configuration is complete.
- `POST /api/telegram/link` — authenticated + CSRF; creates a one-time deep link.
- `DELETE /api/telegram/link` — authenticated + CSRF; disconnects the current member's chat.
- `POST /api/telegram/webhook` — Telegram server-to-server endpoint protected by the secret header; accepts private-chat `/start TOKEN` only.

The webhook caps request bodies at 64 KiB, does not trust browser-supplied chat IDs, rejects expired/replayed/unknown tokens, and never logs raw Telegram updates or tokens. The DB stores only SHA-256 token hashes. Link tokens and chat mappings are tenant-owned and cascade-delete with the account.

## Secret rotation / disconnect

To rotate the webhook secret, set a new value in the private deployment environment, update Telegram's `setWebhook` `secret_token` to the same value, then restart/redeploy the application through the approved deployment process. Coordinate the change to avoid a mismatch window. To rotate the bot token, update BotFather and the private environment, then re-register the webhook and verify it. Do not expose token values in logs or diagnostics.

A member disconnect removes only their chat mapping. If a chat is compromised, disconnect it in the dashboard and revoke/rotate the bot token or webhook secret as appropriate. The application does not currently provide an admin interface for inspecting member chat IDs.

## Tests and deployment status

Automated tests cover valid linking, hashed token storage, expiry, replay, old-token invalidation, private-chat-only behavior, duplicate chat ownership, relink, disconnect, authentication, CSRF, webhook secret rejection, and cross-user isolation. The code has not been deployed or tested against a real Telegram bot yet. A bot username, bot token, webhook secret, and public HTTPS webhook origin are required for a live end-to-end smoke test. Configure them privately; never send secrets in this conversation.

## Per-user notification delivery — implemented on feature branch; live E2E pending (2026-11-07)

The opt-in delivery slice is implemented on the feature branch and running in the isolated feature environment; it is **not deployed to shared dev or production**.

- `v2/user_notifications.py` owns a separate `user_notification_settings` table and tenant-scoped `user_notification_ledger`. It does not reuse or mutate the legacy global `notification_ledger`.
- Member settings default to off. `PUT /api/notifications/settings` accepts only `{ "enabled": true|false }`, requires the authenticated member session and CSRF protection, and refuses opt-in until a private Telegram chat is linked.
- Enabling records `enabled_at`; only matching jobs whose `discovered_at` is at or after that activation boundary and within the user's `max_age_hours` window are queued. Previously discovered jobs are not backfilled. The user's saved `match_threshold` is applied.
- Queue identity is `(user_id, canonical_opportunity_id)`, preventing duplicate delivery to the same member while allowing the same opportunity to be independently evaluated for another member.
- Dispatch resolves the recipient only by joining the ledger owner to that owner's private `user_telegram_chats` mapping. The chat ID is never accepted from a browser request or returned by the settings API.
- Disconnecting Telegram turns member alerts off and cancels queued/retryable/in-flight ledger rows. Turning alerts off does the same. Re-enabling creates a fresh activation boundary.
- Delivery attempts are claimed transactionally, use bounded exponential retry for transient failures, stop after six attempts, and recover stale claims after a process restart. The worker runs member delivery independently of the legacy admin chat ID requirement. A final pre-send check revalidates that opt-in remains enabled, the same private chat is still linked, the job is within the activation/freshness window, and the stored evaluation fingerprint/match/score still satisfy current preferences. Repeated enable requests preserve the original no-backlog boundary; turning off and back on starts a new boundary.
- Dashboard now exposes an explicit opt-in checkbox, disabled until Telegram is connected. Link and notification opt-in remain distinct actions.
- The production bot token is used only as an outbound API credential by this code; no webhook, production config, or production service was changed during implementation.

### Verification and remaining work

- Twelve focused service tests pass in the rebuilt isolated feature container. They cover default-off, activation boundary, stale evaluation cancellation, no historical replay, cross-user delivery isolation, idempotent queueing and opt-in, owner-chat delivery, disable/cancel, retry scheduling and permanent Telegram errors.
- Latest complete V2 suite in the isolated feature container: **272 passed, 1 skipped**. Focused suites: `v2.test_user_notifications` **12/12**, `v2.test_resume_parser` **15/15**, and `v2.test_google_oauth` **15/15**. New OAuth tests verify that a matching Google cancellation consumes one-time state and mismatched cancellation state is rejected. `httpx2` test dependencies were installed temporarily inside the container because the production image intentionally ships runtime dependencies only. The test process set `JOB_BEEPER_COOKIE_SECURE=true` to satisfy the secure-cookie contract; this did not alter the running app environment. Frontend syntax is covered by GitHub CI.
- Before real-bot dev smoke test: configure a dedicated dev bot privately through `.env.feature`, expose the isolated app through an approved public HTTPS endpoint, and register only the dev bot webhook. Then test link → opt-in → newly discovered matching job → delivery → opt-out/disconnect. Do not register the production bot webhook or send production member alerts before an approved production release.
- Quiet hours, per-user time zones, configurable frequency limits, and a user-facing delivery history are intentionally not included in this first slice and should be assessed before enabling member notifications broadly.

### Isolated feature environment checkpoint (2026-11-07)

- Built and restarted only the isolated feature Compose project `job-radar-user-preferences` from this branch. It binds to `127.0.0.1:8002`; it is separate from shared dev and production.
- Verified `GET /health` returns `status=ok`, `/api/notifications/settings` returns 401 to an anonymous request (route exists and is protected), and `/dashboard/` serves the new `telegramNotificationsEnabled` control.
- GitHub V2 CI passed on commit `8e7bc28ca5978f8a3c949d99f7039e4a9b9f785c`, including the full V2 suite and dashboard syntax check.
- Earlier checkpoints: **257**, **262**, then **270 tests passed (1 skipped)**. Latest checkpoint after Google OAuth cancellation-state hardening: **272 passed, 1 skipped**. Test-only `httpx2` dependencies are installed temporarily inside the running feature container; the feature Compose runtime still sets `JOB_BEEPER_COOKIE_SECURE=false` for local HTTP while the test process overrides it to `true`. The running app environment was not changed.
- The owner supplied the intended public dev bot handle `@YourJobBeeperDevBot`. The BotFather token and webhook secret are not yet configured in this isolated environment. No real Telegram message was sent and the production bot was not used. Full external Telegram E2E remains pending private credential setup and an approved public HTTPS route.
- Current readiness: code is pushed to the feature branch, CI green, feature instance healthy, full suite green. Promote to shared dev after a dedicated test bot is configured and the real link → opt-in → delivery → disable/disconnect smoke test passes. Production remains untouched.

## Priority status update (2026-11-07)

Per-user Telegram linking and notification delivery are implemented and unit-tested on the isolated feature branch. The owner subsequently requested that this existing feature work continue in parallel with the ingestion-first investigation. Keep PR #46 draft and the feature service isolated; do not promote to shared dev or production. Configure a separate dev bot privately and complete the real E2E smoke test when the public HTTPS dev endpoint is ready. Keep production bot `Qdhorvbot` reserved for an approved production release.


## 2026-11-07 — Parallel feature work resumed; notification safety hardening

- Owner requested two parallel tracks: continue the existing authentication, resume-assisted onboarding and Telegram feature branch while the owner investigates JobBeeper network behavior in a separate Codex `@Chrome`/CDP session. Ingestion-first work remains active when the sanitized HAR/report arrives; it no longer blocks isolated feature development. PR #46 remains draft and isolated.
- Hardened `v2/user_notifications.py`: repeated enable requests preserve the original `enabled_at` boundary; final pre-send validation now checks active opt-in, unchanged private-chat ownership, activation/freshness windows, current preferences fingerprint, current match state and current score threshold. A stale or no-longer-matching queued item is cancelled rather than delivered.
- Added five service regression tests: idempotent enable boundary, changed-preference stale queue cancellation, non-matching reevaluation cancellation, two-user recipient/content isolation, and permanent Telegram 4xx terminal handling. `v2.test_user_notifications`: **12 tests passed** in the rebuilt feature container.
- Updated isolated feature Compose to accept only dedicated dev bot token/username/webhook secret through an explicit private `--env-file`; the legacy admin chat ID remains blank. Added `.env.feature.example` and ignored `.env.feature`. Do not place the production token in this file.
- Rebuilt the isolated feature service using the correct `v2/docker-compose.feature.yml`; confirmed it is healthy on `127.0.0.1:8002` and mounted to the existing `job-radar-user-preferences_radar-feature-data` volume. Shared dev on 8001 and production on 8000 were not changed.
- Full suite on this rebuilt image: **262 tests passed, 1 skipped**. The feature image contains runtime dependencies only, so `httpx2` is installed temporarily inside the running container for tests. `JOB_BEEPER_COOKIE_SECURE=true` is set only on the test process; the feature app stays HTTP/local with secure cookies disabled. GitHub CI for the new head is still pending.
- Owner is creating a dedicated BotFather test bot. Required private environment values: `JOB_RADAR_TELEGRAM_BOT_TOKEN`, `JOB_BEEPER_TELEGRAM_BOT_USERNAME`, `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET`. Only the public username should be shared in chat. No webhook registration or external Telegram sends until a public HTTPS route is available.
- Outstanding real-world validation: public HTTPS dev endpoint; bot webhook registration; private-chat link confirmation; opt-in; a newly discovered matching job sent to the correct chat; opt-out/disconnect; no cross-user leakage. Quiet hours, time zones, frequency controls and delivery history remain future scope.


## 2026-11-07 — Resume parser boundary coverage expanded

- Expanded `v2/test_resume_parser.py` from 7 to 15 tests. Added coverage for PDF page count and encryption; DOCX table extraction; ZIP entry count, aggregate uncompressed size, compression ratio and zero compressed-size defenses; and extracted-text truncation. These tests exercise existing limits in `v2/resume_parser.py`; no parser behavior was changed in this follow-up.
- Focused parser suite: **15 tests passed**. Full V2 suite in the isolated feature container: **270 tests passed, 1 skipped**. Test process used `JOB_BEEPER_COOKIE_SECURE=true` only for the secure-cookie contract and temporary `httpx2` dependencies from `requirements-dev.txt`.
- These parser tests are now included in the branch's next GitHub V2 CI run. The previous feature hardening commit `7088319` already passed CI run `42369403418`.


## 2026-11-07 — Google OAuth cancellation-state hardening

- Updated `/api/auth/google/callback` to validate the returned state against the HttpOnly browser state cookie and consume the state record before processing either provider success or provider cancellation/error. Missing, mismatched or replayed state fails closed. Failures after state validation cannot leave the one-time state reusable.
- Added two `v2/test_google_oauth.py` API regressions: matching `access_denied` consumes the one-time state and redirects to the cancellation UX; an error callback with an unbound/mismatched state is treated as failure. Removed a duplicate test import and corrected the auth CLI module description.
- Focused Google OAuth suite: **15 tests passed**. Full V2 suite on the isolated feature container: **272 passed, 1 skipped**. `httpx2` installed temporarily for tests; `JOB_BEEPER_COOKIE_SECURE=true` used only by test process.
- OAuth credentials are still not configured for a live sign-in test. The feature branch's Google OAuth setup guide remains the source for exact redirect-origin/callback configuration. No client secret or production OAuth configuration has been changed.


## 2026-11-07 — Development bot identity and secret-generation handover

- Owner provided the intended public development bot handle: `@YourJobBeeperDevBot` (Compose/env value is `YourJobBeeperDevBot`, without `@`). This is owner-provided information; it has not been verified with BotFather because no token is available. BotFather must confirm the username was actually created and issue its token.
- Owner asked where to run `python -c "import secrets; print(secrets.token_urlsafe(32))"`. It can run in Windows PowerShell on the owner's PC; use `py -c ...` if `python` is not on PATH. It can also run in an Ubuntu shell as `python3 -c ...`. It does not need to run inside Telegram or in the Python application. The output is a separate webhook secret and must remain private.
- `.env.feature` is currently absent on the server. `.env.feature.example` is tracked; `.env.feature` is ignored by `.gitignore`. After receiving the BotFather token, create the private server file with `cp .env.feature.example .env.feature`, edit it with `nano .env.feature`, and place the token/webhook secret there. Never paste either secret into ChatGPT.
- The feature Compose service now passes `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` and `GOOGLE_OAUTH_REDIRECT_URI` from the same private `--env-file`, in addition to the three Telegram variables. All are empty until privately configured. This fixes the previous gap where Google OAuth values in an env file would not reach the feature container.
- The feature service remains loopback-only on `127.0.0.1:8002`; no Telegram webhook can be registered yet. A dedicated public HTTPS route must be approved and configured before `setWebhook`. No token was configured, no webhook registered, and no messages sent.


## 2026-11-07 — Owner configured isolated development bot environment

- The owner supplied intended public bot handle @YourJobBeeperDevBot and has now created the private .env.feature file on the feature VM with mode 600.
- Read-only container inspection confirmed the Telegram bot token, username and webhook secret environment variables are populated. Secret values were not printed or copied into the repository.
- The feature container was rebuilt/recreated and is healthy on 127.0.0.1:8002 (/health returned ok). The server's outbound request to Telegram getMe timed out, so BotFather/API token acceptance and the bot identity are not yet independently verified. Retry only after outbound connectivity is available; do not share the token.
- No webhook was registered and no Telegram message was sent. The service remains loopback-only; a public HTTPS route is still required before setWebhook.
- Still pending: successful getMe, approved HTTPS routing, webhook registration, member account link, explicit opt-in, fresh matching-job delivery to the correct private chat, opt-out and disconnect. Production bot and ports remain untouched.
- Google OAuth environment variables remain empty; live Google sign-in is not yet configured.
