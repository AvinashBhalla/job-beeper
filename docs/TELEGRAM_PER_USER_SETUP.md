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
