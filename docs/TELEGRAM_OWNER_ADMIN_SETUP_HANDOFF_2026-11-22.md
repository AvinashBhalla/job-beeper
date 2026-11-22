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
- No Telegram private chat has been linked; no notification settings have been enabled; no notification ledger rows exist; no job-alert Telegram messages have been sent.

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

- No Telegram chat linked by the owner.
- No job-alert notification enabled.
- No job-alert Telegram message sent.
- No user preference was automatically changed by this release.
- No Gmail scope or label restriction changed, and no new Gmail sync/backfill was triggered by the code release.
- No first email from the newly created Google Alerts has yet been confirmed.
