# Telegram account linking — setup and operations

## Current implementation boundary

This milestone implements **account linking only**. It does not send job alerts to member chats, and linking a Telegram account does not enable notifications. The existing global Telegram destination remains reserved for admin/operational alerts. Per-user opt-in, preference-matched dispatch, quiet hours, deduplication and disconnect-aware delivery must be implemented and tested separately before member notifications are enabled.

## Server configuration

Configure these variables in the deployment's private environment/secret store; never commit them or paste their values into chat:

- `JOB_RADAR_TELEGRAM_BOT_TOKEN` — bot token from BotFather. The existing production bot token is already configured for the legacy admin/operational outbound notifier. The same bot can technically be reused for member linking and member DMs; Telegram's webhook handles inbound updates while `sendMessage` continues to handle outbound messages.
- `JOB_BEEPER_TELEGRAM_BOT_USERNAME` — public bot username, without `@`.
- `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET` — random 1–256 character value using only letters, digits, `_` or `-`. Generate a strong value, e.g. `openssl rand -hex 32`.

### Existing production bot discovery (2026-11-07)

- Read-only `getMe` against the token already present in `/home/ubuntu/job-beeper/.env` confirmed the existing bot username is **`Qdhorvbot`**. The token itself was never printed or copied into this repository/chat.
- Read-only `getWebhookInfo` reported **no webhook currently configured**, zero pending updates and no last webhook error. This means there is no existing Telegram webhook URL to preserve or migrate.
- The production `.env` currently contains both `JOB_RADAR_TELEGRAM_BOT_TOKEN` and `JOB_RADAR_TELEGRAM_CHAT_ID`. The old production Compose file currently passes only those two variables; it does not yet pass `JOB_BEEPER_TELEGRAM_BOT_USERNAME` or `JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET`.
- Searches across the known production, dev and feature checkouts found no `getUpdates`, `setWebhook`, or `deleteWebhook` consumer. The existing `v2/telegram.py` notifier only calls outbound `sendMessage` and continues to use the global admin chat ID. Thus reuse of the same bot is technically compatible with the code paths inspected: inbound `/start` updates will be handled by the new webhook, while admin/member outbound messages use `sendMessage`.
- **Not configured or changed:** no webhook was registered, no production environment variable was added, no production Compose file/container was modified, and no live bot message was sent as part of this inspection. The production checkout is stale (613 commits behind the active branch), so do not deploy from it or treat it as containing the new webhook endpoint.
- **Decision:** reuse of the existing production bot is a viable option for the eventual production release. Do not repoint it yet. First deploy and smoke-test the webhook endpoint through an approved release. If a separate development smoke test is needed, use a dedicated test bot so production bot updates are not diverted to an unfinished/dev endpoint. Before registering the production webhook, set the public username to `Qdhorvbot`, add a newly generated webhook secret to the private production environment, ensure the deployed production Compose/app passes both values, then register the webhook to the deployed HTTPS `/api/telegram/webhook` endpoint. Preserve the existing global admin chat ID and verify its outbound notifications still work after release.

The application requires all three values before it exposes the connect action. Development and isolated feature Compose files deliberately set these values blank by default. The active feature branch Compose passes the username and webhook secret from its private environment. The currently deployed production checkout is older and does not yet pass the two new values; update them only as part of an approved release. No live configuration has been made by this change.

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

## Per-user notification delivery — implementation in progress (2026-11-07)

The first opt-in delivery slice is now implemented on the feature branch; it is **not yet pushed to the dev deployment or production**.

- `v2/user_notifications.py` owns a separate `user_notification_settings` table and tenant-scoped `user_notification_ledger`. It does not reuse or mutate the legacy global `notification_ledger`.
- Member settings default to off. `PUT /api/notifications/settings` accepts only `{ "enabled": true|false }`, requires the authenticated member session and CSRF protection, and refuses opt-in until a private Telegram chat is linked.
- Enabling records `enabled_at`; only matching jobs whose `discovered_at` is at or after that activation boundary and within the user's `max_age_hours` window are queued. Previously discovered jobs are not backfilled. The user's saved `match_threshold` is applied.
- Queue identity is `(user_id, canonical_opportunity_id)`, preventing duplicate delivery to the same member while allowing the same opportunity to be independently evaluated for another member.
- Dispatch resolves the recipient only by joining the ledger owner to that owner's private `user_telegram_chats` mapping. The chat ID is never accepted from a browser request or returned by the settings API.
- Disconnecting Telegram turns member alerts off and cancels queued/retryable/in-flight ledger rows. Turning alerts off does the same. Re-enabling creates a fresh activation boundary.
- Delivery attempts are claimed transactionally, use bounded exponential retry for transient failures, stop after six attempts, and recover stale claims after a process restart. The worker runs member delivery independently of the legacy admin chat ID requirement.
- Dashboard now exposes an explicit opt-in checkbox, disabled until Telegram is connected. Link and notification opt-in remain distinct actions.
- The production bot token is used only as an outbound API credential by this code; no webhook, production config, or production service was changed during implementation.

### Verification and remaining work

- Seven focused service tests pass locally: default-off, explicit activation, no historical replay, per-user isolation, idempotent queueing, owner-chat delivery, disable/cancel, and retry scheduling.
- The host Python environment does not have the application's FastAPI/argon2 dependencies, and Docker access is denied to the development SSH user. Therefore the API integration suite and full project suite still need to run in CI or an authorized dev runtime. The host's Node runtime is also too old for existing optional-chaining/nullish-coalescing syntax in `dashboard/app.js`; this is an environment limitation, not a new syntax regression.
- Before dev rollout: run the complete Python suite and frontend checks in the project's supported container/runtime; review retry/disable race behavior; confirm the dev environment has a separate test bot token and webhook configuration; then deploy to dev and smoke-test link → opt-in → new matching job → delivery → disable/disconnect. Do not register the production bot webhook or send production member alerts before an approved production release.
- Quiet hours, per-user time zones, configurable frequency limits, and a user-facing delivery history are intentionally not included in this first slice and should be assessed before enabling member notifications broadly.

### Isolated feature environment checkpoint (2026-11-07)

- Built and restarted only the isolated feature Compose project `job-radar-user-preferences` from this branch. It binds to `127.0.0.1:8002`; it is separate from shared dev and production.
- Verified `GET /health` returns `status=ok`, `/api/notifications/settings` returns 401 to an anonymous request (route exists and is protected), and `/dashboard/` serves the new `telegramNotificationsEnabled` control.
- GitHub V2 CI passed on commit `8e7bc28ca5978f8a3c949d99f7039e4a9b9f785c`, including the full V2 suite and dashboard syntax check.
- Ran the full suite in the feature container: **257 tests passed, 1 skipped**. The test-only `httpx2` dependencies were temporarily installed because the runtime image intentionally contains production requirements only, then removed after the run. The feature Compose runtime sets `JOB_BEEPER_COOKIE_SECURE=false` for local HTTP; the test process used `JOB_BEEPER_COOKIE_SECURE=true` to match the secure-cookie test contract. This was a test-process override only and did not change the running app's environment.
- No Telegram test bot is configured in this isolated environment. No real Telegram message was sent and the production bot was not used. Full external Telegram E2E remains pending a dedicated dev bot token and webhook secret configured privately in the feature environment.
- Current readiness: code is pushed to the feature branch, CI green, feature instance healthy, full suite green. Promote to shared dev after a dedicated test bot is configured and the real link → opt-in → delivery → disable/disconnect smoke test passes. Production remains untouched.
