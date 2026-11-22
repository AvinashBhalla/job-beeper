# Telegram owner-admin setup — live handoff

**Updated:** 22 November 2026
**Repository:** `AvinashBhalla/job-beeper`
**Scope:** Owner-only Telegram connection for the personal Google Alerts Gmail integration; notification delivery remains explicit opt-in.

## Current live status

- PR [#107](https://github.com/AvinashBhalla/job-beeper/pull/107) is merged as `e9e521a93aa19f76f92f9b7d25c2440004604066`.
- Production image: `job-radar-prod-release:telegram-owner-20261122`; image ID `sha256:69385fb40ca2d93a4a101d01484c8c25f1a030083366bfe0bb5f7230b2486834`.
- Container: `v2-radar-1`; host binding remains `127.0.0.1:8000`; external volume `v2_radar-data` remains mounted at `/data`; container restart count 0 and OOM false at post-deploy verification.
- `/health`, `/dashboard/` and `/openapi.json` return HTTP 200.
- The private environment `/home/ubuntu/job-beeper/.env` remains mode `0600`, owned by `ubuntu:ubuntu`. It contains the pre-existing bot token, username `Qdhorvbot`, and a newly generated webhook secret. Secret values are not stored in Git, documentation or chat.
- Telegram Bot API `getMe` confirmed the existing bot username `Qdhorvbot`. `setWebhook` completed successfully with `https://130.210.27.197/api/telegram/webhook`, `allowed_updates=["message"]`, `max_connections=5`, and `drop_pending_updates=false`. `getWebhookInfo` confirmed exact URL, zero pending updates, and no last webhook error. The webhook secret is delivered by Telegram in `X-Telegram-Bot-Api-Secret-Token` and checked by the application.
- The HTTPS endpoint is publicly reachable and its active certificate has an IP SAN for `130.210.27.197`; certificate renewal is managed by the host's existing certbot timer. No DNS, custom domain or new certificate resource was created.
- No Telegram private chat has been linked through the new owner-specific account flow; no per-user notification setting is enabled and `user_notification_ledger` has zero rows. **Separate legacy behaviour:** the old global Telegram notifier remains enabled (`JOB_RADAR_TELEGRAM_CHAT_ID` and bot token are configured, and `notifications_enabled=true` in app config). It delivered three legacy LinkedIn alerts after this deployment: 2 at 07:51:58 UTC and 1 at 07:57:37 UTC on 22 November. These were sent to the pre-existing static global chat ID and are not evidence that the new owner-specific link or per-user opt-in succeeded. The legacy notifier was left unchanged.

## Code changes

### Owner-admin Telegram access

Before this change, every administrator was blocked from the Telegram APIs and the dashboard hid the Telegram panel from all admins. The Gmail integration is explicitly bound to one configured owner administrator, so the new authorization helper permits the Telegram operations only when the authenticated administrator's user ID matches `JOB_RADAR_GMAIL_OWNER_USER_ID` from the valid Gmail integration configuration.

Allowed for the configured owner admin: Telegram status, one-time link creation, private chat linking through the webhook, disconnect, reading notification settings and changing the explicit enabled flag. Other admins remain `403`; ordinary members retain their existing behavior. The UI initially keeps the Telegram panel hidden and only displays it after the API confirms server-side access for the current account.

Notifications remain opt-in. Enabling is rejected until a private Telegram chat is linked. Disconnecting the chat disables notifications and cancels eligible pending delivery state. Merely connecting Gmail or registering the bot webhook does not enable notifications.

### Admin preference re-evaluation

A production read-only check found that the owner had added `india` to saved locations, but the existing PwC Gmail-derived job evaluation still carried an old preferences fingerprint and score 0. The admin `/api/config` save route updated the saved preferences but did not refresh the first-admin's existing job evaluations. The route now schedules `refresh_user_job_evaluations` for that active admin after preferences are synchronized, so existing jobs are evaluated under the updated profile.

After deployment/startup, the PwC job's location now matches `All India, IN`, and its score increased to **44**. It still reports no configured target-role match and remains below the current default match threshold; it is not eligible for Telegram delivery. Do not bypass the role or score checks and do not send this record as an alert.

## Validation evidence

- Three newly added targeted tests passed: admin config preference refresh; non-owner admin denied for all Telegram/link/settings operations; configured Gmail owner admin can link a private chat, cannot enable without a link, can explicitly enable only after linking, and unlink resets notifications off.
- Complete `v2.test_user_preferences_api` module run exited **0** in the isolated host test environment.
- `v2.test_dashboard_auth_contract`, `v2.test_user_notifications` and the focused admin CSRF regression: **42 tests passed**.
- Python compile checks, `node --check dashboard/app.js`, and `git diff --check` passed.
- The candidate Python 3.12 image passed runtime Gmail configuration validation and Python compile checks. The slim production image does not include the dev-only `httpx2` test-client dependency, so the API suites were run in the isolated development venv instead of the production image.

## Production backup and deployment

Fresh backup before the Telegram-owner rollout:

`/var/backups/job-radar-daily/release-telegram-owner-20261122T074641Z`

The directory is `root:root` mode `0700`; files are `root:root` mode `0600`. `SHA256SUMS` was verified. SQLite snapshot integrity is `ok`; it contains 28,734 jobs, 1 Gmail credential, 0 Telegram chats and 0 enabled notification settings. The backup contains the private runtime env, pre-deploy container inspection, old image ID/tag, candidate image ID and Compose definitions. The existing external data volume was retained; the backup is rollback evidence, not a reason to restore it.

## Current Gmail and alert state

- Gmail remains connected with 1 encrypted credential.
- 4 Gmail messages are processed, all from the historical backfill; 8 alert results were parsed; no Gmail message processing errors.
- Sync state reports `backfill_state=complete`, an active history cursor, and no sync error.
- The user reports creating three role-based Google Alerts with settings `As-it-happens`, source `Web`, English, region India, and all results. Exact queries are recorded in the Gmail activity log. No new email from these newly created queries has yet been confirmed; keep the first new-email end-to-end check open.
- The Gmail label `JobBeeper/GoogleAlerts` exists. The user-created Gmail filter's final save/application to existing and future conversations still needs explicit confirmation. Ensure every new Google Alerts email receives the label before expecting JobBeeper to ingest it.
- The most recent imported PwC job is currently not a match (score 44; reason `no configured target-role match`). Notification eligibility still depends on the current owner roles, match threshold, freshness and verified public posting.

## Owner's next steps

1. Keep the SSH tunnel open and open `http://localhost:8080/dashboard/`; hard-refresh with Ctrl+Shift+R.
2. Open Preferences/Settings and locate **Connect Telegram (optional)**. The panel should now appear for the configured Gmail owner admin because server-side authorization permits this exact account.
3. Click **Generate Telegram connection link**, then open the returned `https://t.me/Qdhorvbot?start=...` link. In Telegram, press **Start** in a private chat with Qdhorvbot. The bot's connection-confirmation reply is expected; this is not a job alert.
4. Return to JobBeeper and click **Refresh connection status**. Verify Telegram is connected. The job-alert checkbox should remain off.
5. Before enabling notifications, the owner should decide whether `Software Engineering`/`Associate Software Engineer` belongs in saved target roles or whether the matcher should add a controlled `software engineering` alias for the existing `software engineer` target. Do not widen roles automatically. Then save preferences and allow the admin evaluation refresh to update existing jobs.
6. Confirm the Gmail filter applies `JobBeeper/GoogleAlerts` to new messages. Wait for a new email from the new role-based Google Alerts, then verify it is labelled, processed, and its public posting is independently verified and matched before considering notification delivery.
7. Only when the owner explicitly checks **Send matching new-job alerts to my connected Telegram chat** should delivery become enabled. Current preference matching, score threshold, freshness, posting verification, private chat, rate limiting, idempotency and retry protections remain enforced. Historical Gmail rows use the Gmail-specific backfill marker but are still subject to those checks.

## Explicitly not done

- No Telegram chat linked through the new owner-specific account flow. The user-facing `t.me` page did not open the Telegram app; the pending token remained unconsumed, and no `/api/telegram/webhook` POST was received.
- No job-alert notification enabled.
- No job-alert message sent through the new owner-specific per-user channel. Three legacy global LinkedIn alerts were sent through the pre-existing static chat configuration at 07:51:58 and 07:57:37 UTC; see live-state note above.
- No user preference was automatically changed by this release.
- No Gmail scope or label restriction changed, and no new Gmail sync/backfill was triggered by the code release.
- No first email from the newly created Google Alerts has yet been confirmed.

## Telegram start-button troubleshooting — 22 November 2026

- The owner opened the generated `https://t.me/Qdhorvbot?start=...` link in Chrome and reported that clicking **START BOT** did nothing. The screenshot shows Telegram's web landing page, not the private bot chat.
- Server evidence: `POST /api/telegram/link` succeeded at `08:05:03 UTC`, creating the one-time token for the configured owner. The latest DB check found the token unconsumed and unexpired (10-minute TTL; last checked with approximately 200 seconds remaining). No `POST /api/telegram/webhook` was logged after creation. Telegram `getWebhookInfo` still reported the configured HTTPS endpoint, zero pending updates and no last error.
- Conclusion: the browser did not hand the `tg://` link off to a Telegram client; there is no evidence of a broken server webhook or a received `/start` update.
- Owner workaround: open Telegram Desktop or Telegram mobile, search `@Qdhorvbot` / **Jobwatcher**, open the private chat, and send `/start <payload>` using the exact payload copied from the generated URL after `start=`. Sending bare `/start` is insufficient. If the one-time token expires, generate a fresh link in JobBeeper and use the new payload. Do not share the full start link publicly.
- After the bot receives the payload, expect one private account-link confirmation. Then refresh Telegram connection status in JobBeeper. Notification settings should still be off until the owner explicitly opts in.
- Separate legacy delivery correction: the old global Telegram sender remains configured (`JOB_RADAR_TELEGRAM_CHAT_ID` and bot token set; app `notifications_enabled=true`). Application logs show 2 legacy global LinkedIn notifications delivered at `07:51:58 UTC` and 1 at `07:57:37 UTC` on 22 November. This path uses the pre-existing static chat ID and does not create `user_telegram_chats` rows or `user_notification_ledger` rows. It was not disabled during the owner-link rollout. Ask the owner before changing the existing global notification switch.

## 22 November 2026 — owner Telegram private chat connected and opt-in enabled

- Owner reported successful Telegram connection. Read-only production verification confirms exactly one private user_telegram_chats row for the configured Gmail owner admin, and the webhook log shows the latest successful POST /api/telegram/webhook at 08:21:58 UTC (13:51:58 IST).
- The per-user notification setting is enabled. The server recorded PUT /api/notifications/settings with HTTP 200 at 08:22:13 UTC (13:52:13 IST), 15 seconds after webhook receipt. This is the UI opt-in checkbox “Send matching new-job alerts to my connected Telegram chat”, distinct from merely linking Telegram.
- enabled_at is 2026-11-22T08:22:13.655197+00:00. The application only considers jobs discovered after enabled_at eligible; historical Gmail backfill rows are not automatically delivered. At verification, user_notification_ledger had 0 rows and 0 pending deliveries. The Gmail historical PwC job remains match=0, score 44, reason “no configured target-role match”.
- Gmail still has 4 processed historical messages (all history_backfill=1, 8 parsed results), 0 non-backfill messages, completed backfill and active incremental history reconciliation with no sync error. Thus there is not yet an end-to-end new Google Alert email to validate.
- Existing legacy global Telegram notifications remain a separate path. The legacy global chat ID/token and notifications_enabled=true remain configured; three legacy LinkedIn alerts were sent after the owner-admin release (two at 07:51:58 UTC and one at 07:57:37 UTC). These are not per-user ledger deliveries. Do not disable the legacy notifier without owner approval.
- No code, credentials, Telegram bot settings or Gmail preferences were changed in this checkpoint. No new alert was manually sent. Per-user notifications are on for future eligible discoveries; match, score threshold, freshness, public-posting verification, rate limit, idempotency and delivery safeguards continue to apply.

### Next acceptance checks

1. Confirm the Gmail filter applies JobBeeper/GoogleAlerts to each of the new Google Alerts, including future messages. Label creation was confirmed; final filter application still has not been explicitly confirmed in the conversation.
2. On the next new Google Alerts email, verify it is received in Gmail, carries the dedicated label, is ingested by the Gmail history poller and creates only independently verified public-job candidates.
3. Confirm the candidate job is discovered after the notification opt-in timestamp and passes title/role, skills, location, score threshold and freshness checks. Do not bypass the current “no configured target-role match” failure on the PwC record.
4. If a qualifying new job is found, verify exactly one per-user queue/ledger record and the expected private Telegram delivery. Avoid using historical backfill as a send test.
5. Keep the legacy global notifier distinction visible when reviewing Telegram messages; it uses the static legacy chat configuration, independently of the owner-specific chat/opt-in.
