# Google Alerts Gmail — Live Acceptance Handoff

**Updated:** 22 November 2026 (latest OAuth attempt)
**Repository:** `AvinashBhalla/job-beeper`
**Current production container:** `v2-radar-1`
**Purpose:** Record what was built, what was learned during live setup, the exact Google OAuth blocker, and the next safe actions.

## Current status

The JobBeeper account login now works through the localhost SSH tunnel. The Gmail Account page and consent endpoint work. The consent POST succeeds, the server consumes its one-time consent when OAuth starts, and Google receives the authorization request. Google then blocks the authorization with **403 `access_denied`** because the OAuth app is still in Testing and the Google account is not currently allowed as a developer-approved test user (or the configured Cloud project/client audience is not the one expected).

**This is a Google Cloud OAuth audience/publishing-state blocker, not a remaining dashboard CORS or JSON-payload error.** The screenshot explicitly says the app has not completed Google's verification process and is currently being tested; only developer-approved testers may access it.

No Google authorization code was returned to the callback. No Gmail grant or refresh token was stored, no Gmail message was read, and no Gmail sync/backfill began.

## Learning and implementation activities

### 1. Owner mailbox preparation

- The owner created the Gmail label `JobBeeper/GoogleAlerts`.
- The intended Gmail filter is from `googlealerts-noreply@google.com`, applying that label to matching conversations. Confirm it is saved and includes existing matching conversations before the first successful sync.
- JobBeeper does not create or edit labels/filters. Gmail processing is intended to use only the dedicated label and the narrow `gmail.readonly` grant.

### 2. SSH tunnel and same-origin login

- The local browser connects to `http://localhost:8080`; SSH forwards local port 8080 to the VM's loopback-only app listener `127.0.0.1:8000`.
- The first sign-in failed with `403 Cross-origin login is not allowed`. The browser `Origin` was `http://localhost:8080`, but Docker source-NATed the host connection to the app container as bridge gateway `172.18.0.1`. The login guard had trusted only loopback source addresses.
- PR [#103](https://github.com/AvinashBhalla/job-beeper/pull/103) added a narrow `172.18.0.1` allowance only for plain-HTTP `localhost` requests with no forwarded/proxy headers. Public and proxied requests still use the configured public origin and secure cookies.
- Focused regression in an isolated Python 3.12 container: **5 tests passed**. The updated image was deployed, and `/health`, `/dashboard/`, and `/openapi.json` returned HTTP 200. The app port remains bound only to `127.0.0.1:8000`.
- The user then signed in successfully. The tunnel must stay open throughout OAuth because both the redirect URI and callback use localhost.

### 3. Dashboard consent 422 and `[object Object]`

- The first consent POST returned `422 Unprocessable Entity`; the screen rendered the validation array as `[object Object]`.
- Root cause: `dashboard/app.js` passed a plain JavaScript object as `fetch`'s `body`. The shared `dashboard/auth.js` client did not JSON-encode object payloads or set `Content-Type: application/json`.
- PR [#104](https://github.com/AvinashBhalla/job-beeper/pull/104) now serializes plain object/array bodies as JSON, preserves existing headers and the CSRF header, and provides readable formatting for FastAPI validation errors.
- Regression: `v2/test_dashboard_auth_contract.py` **12 passed**. The test covers the exact `{accepted: true, disclosure_version: ...}` consent body, JSON content type, CSRF header and readable validation errors. `node --check` passed for `dashboard/auth.js` and `dashboard/app.js`.
- A candidate image also passed the 5 Gmail/radar integration tests and Python compilation. PR #104 was merged and the image deployed. The running container was checked to contain the new `auth.js` code; dashboard assets return HTTP 200.

### 4. Server-side consent and OAuth flow

- The disclosure version is `2026-11-22-v2`.
- Consent is recorded server-side, expires after 10 minutes and is consumed once when OAuth starts. Direct, expired or replayed OAuth-start requests are rejected.
- The latest browser attempt produced these server logs: consent POST **200**, OAuth connect endpoint **302**. This confirms the browser/client reached JobBeeper correctly and JobBeeper redirected to Google.
- The Google error happened after that redirect and before the callback. The server has one consent record and one OAuth state from the attempt. Those are not evidence of a connected Gmail account. Confirm the consent row’s `consumed_at`/expiry if diagnosing a repeat attempt; a fresh UI consent action should create a new current consent.

### 5. Intended Gmail processing design

- Separate Gmail OAuth client from the JobBeeper member sign-in OAuth client.
- Request only `https://www.googleapis.com/auth/gmail.readonly`.
- OAuth callback: `http://localhost:8080/api/integrations/google-alerts/gmail/callback`.
- Current sync mode: Gmail history polling, default interval 180 seconds; Pub/Sub, `users.watch`, public webhook and a custom domain are not required for this personal localhost-tunnel setup.
- The intended worker checks metadata/authentication first, fetches raw MIME only for authenticated messages carrying the dedicated label, parses in memory, extracts destination URLs, then independently fetches/verifies public job postings. Raw email bodies, snippets, alert search text, subject and sender are not intended to be persisted. Message-key digests and sync/processing metadata are retained for dedupe/recovery.
- Gmail connection alone does not turn Telegram notifications on. Telegram is a separate service and requires its own enabled setting and linked private chat. Do not enable it as a side effect of OAuth testing.

## Exact Google OAuth error observed

Screenshot from 22 November 2026 shows:

- Page message: `Access blocked: JobBeeper has not completed the Google verification process. The app is currently being tested and can only be accessed by developer-approved testers.`
- Dialog: `Error 403: access_denied`.
- `access_type=offline`.
- Scope: `https://www.googleapis.com/auth/gmail.readonly`.
- `response_type=code`.
- Redirect URI: `http://localhost:8080/api/integrations/google-alerts/gmail/callback`.
- PKCE is enabled (`code_challenge_method=S256`); prompt is `consent`.

Interpretation: Google has blocked the user at the OAuth authorization stage because the app is in Testing and the account is not currently allowlisted for this OAuth project/client. First verify the Google Cloud project selected in the console is the one that owns the OAuth client ID configured on the VM. Then inspect the app's audience/publishing status.

## Current production/runtime state (read-only verified)

- Container: `v2-radar-1`.
- Image: `job-radar-prod-release:gmail-consent-20261122`.
- Image ID: `sha256:c53b0894aabad47e4119e4294d1a785c62c69cac0ef89a91a851b3e7ce1e65d2`.
- Host port: `127.0.0.1:8000` only.
- Existing external data volume: `v2_radar-data` mounted at `/data`.
- Container restarts: 0; OOM: false; `/health`: HTTP 200, `status=ok`; dashboard and OpenAPI also HTTP 200.
- `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=true` in the running container. Do not assume this means Gmail is connected. Keep the gate as currently configured; do not change it as part of fixing the Google test-user allowlist.
- Post-error read-only SQLite counts: integrity `ok`; jobs `28,731`; Gmail credentials `0`; Gmail consent records `1`; Gmail OAuth state rows `1`; Gmail messages `0`; Gmail sync rows `0`; Gmail opportunities `0`.
- The consent record and OAuth state are residual setup-flow records. No Gmail token/grant, message ingestion or sync is present. Check expiry/cleanup semantics before manually changing or deleting them; a normal fresh consent action should create a new current consent when the user retries.

Root-only snapshots were created before both app-only hotfix deployments. The latest pre-PR-104 snapshot is under `/var/backups/job-radar-daily/release-gmail-consent-20261122T062255Z`; its manifest was checksum-verified, database integrity was `ok`, and the snapshot contained 28,731 jobs and 2 users. Preserve the existing volume; do not restore a backup unless a real data-integrity issue is proven.

## Next steps — Google Cloud Console (owner action)

1. Open Google Cloud Console and select the exact project that owns the Gmail OAuth Web application client ID already configured on the JobBeeper VM. Do not edit the separate JobBeeper login client/project by mistake.
2. Open **Google Auth Platform → Audience** (older console layout: **APIs & Services → OAuth consent screen**).
3. Inspect **User type** and **Publishing status**. The observed error indicates the project is in a Testing/developer-approved-testers state.
4. If the app is **External** and in **Testing**, add the exact Google account that owns the Google Alerts mailbox under **Test users → Add users**, then Save. The Gmail account used during the next OAuth attempt must be the same one configured as the Gmail owner and receiving the Alerts label. If the app is Internal, confirm the account belongs to the same Google Workspace organization. If it is Personal mode or no Test users section exists, stop and inspect the Audience page rather than changing the app type.
5. Reopen `http://localhost:8080/dashboard/#access` through the still-running SSH tunnel, hard-refresh, check the disclosure again and select **Connect personal Gmail**. Sign in with the allowlisted mailbox. At the Google permission screen, verify the app identity and that the only Gmail permission requested is `gmail.readonly`. Do not authorize unexpected broader scopes.
6. If Google still blocks access after saving the test user, capture the exact new error and inspect Audience, app publishing status, project/client ID pairing and account selected in Google's account chooser. Do not change scopes or create another OAuth client as a guess.

### Testing-mode limitations and production readiness

- Google's current guidance says External apps in Testing can have up to 100 test users; authorizations for test users expire after seven days. That is suitable for a short test only, not a durable 180-second polling integration.
- `gmail.readonly` is classified by Google as a **Restricted** Gmail scope, not merely a basic sign-in scope. Publishing a public/production app that uses restricted scopes requires Google's restricted-scope verification. Google also states a server-side security assessment is required when restricted-scope data is stored on or transmitted through servers. Treat the VM-hosted integration accordingly unless Google confirms an applicable exception in writing.
- Do not equate a prior report of personal-use approval or a successful test-user grant with completion of OAuth restricted-scope verification or a CASA/security assessment. The current screenshot is evidence that the current OAuth app has not completed the verification process.
- Do not publish the app to Production merely to remove the test-user restriction. Complete scope justification, privacy-policy/data-use disclosures, permitted-use-case review and applicable security assessment first.

Official references:

- [Manage app audience and testing-mode limits](https://support.google.com/cloud/answer/15549945)
- [When OAuth verification is not needed](https://support.google.com/cloud/answer/13464323)
- [Gmail API scope classifications](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [Google Workspace user data and developer policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy)
- [Submit an app for OAuth verification](https://support.google.com/cloud/answer/13461325)

## After Google allows the test account

1. Confirm Google redirects back to the exact localhost callback and JobBeeper reports Gmail connected.
2. Read the Gmail status endpoint/UI and verify the connected account matches the configured owner mailbox. The callback must verify the owner identity and that the user-created `JobBeeper/GoogleAlerts` label exists.
3. Confirm credentials are stored encrypted and sync state is created. Then monitor the initial label-scoped historical backfill and incremental history catch-up. Verify that no unlabelled messages are fetched or processed.
4. Inspect counts/progress only; do not expose message bodies, subjects, sender addresses, access tokens or refresh tokens in logs/screenshots.
5. Keep Telegram notifications off unless the owner separately confirms the Telegram account/link and explicitly enables notifications. Gmail OAuth alone must not send messages.
6. Record whether test mode grants are temporary. Do not call the integration production-ready while the 7-day test authorization expiry applies.

## Do not do

- Do not bypass Google access restrictions by changing requested scopes, using another user's OAuth client, or broadening the audience without review.
- Do not store Gmail credentials manually, paste OAuth codes/tokens into chat, or inspect/log raw mailbox content.
- Do not run Gmail sync/backfill until Google authorization succeeds and the expected account/label are verified.
- Do not send Telegram alerts during OAuth smoke testing.
- Do not turn off authentication/CSRF/CORS or alter the loopback-only binding.
- Do not replace the production database volume or restore a snapshot for this OAuth denial.


## 22 November 2026 — successful Google OAuth and initial Gmail backfill

### Owner-reported milestone

The owner added two developer-approved test accounts in Google Auth Platform and was then able to complete Google login/OAuth. The dashboard reports: **Initial backfill complete; incremental history reconciliation is active; 4 processed**. This is the first successful live Gmail authorization and backfill checkpoint.

The Gmail integration remains single-owner. Adding two Google OAuth test users only allows those identities to pass Google's Testing audience gate; it does not enable two Gmail mailboxes in JobBeeper. The deployed integration credential is bound to the configured owner administrator. Keep only that intended owner mailbox connected and confirm it is the mailbox carrying `JobBeeper/GoogleAlerts`.

### Read-only production verification after the successful backfill

Checked against the live SQLite database in read-only mode; no token or mailbox contents were printed:

- Gmail credentials: **1** encrypted owner credential present.
- Gmail data-use consent records: **1**.
- Gmail messages: **4**, all with `status='processed'`, `history_backfill=1`, four processing attempts total, **0 rows with an error code**.
- Parsed Google Alert results: **8** total across the four processed messages.
- Gmail-derived opportunities: **1**, tagged as historical backfill.
- Gmail sync state: **1**, `backfill_state='complete'`, non-empty label binding and incremental history cursor, no `last_error_code`; `last_reconciled_at` was updated at the verification checkpoint.
- Jobs table: **28,732**, one more than the prior pre-Gmail checkpoint of 28,731.
- SQLite `PRAGMA integrity_check`: **ok**.

The one retained Gmail-derived job is titled **Software Engineering – React & Node – Associate**, company **PwC Acceleration Centers in India**, location **All India, IN**. Current owner evaluation is `match=0`, `score=0`, reason: **location outside configured targets**. This explains why this historical record does not currently qualify for a Telegram notification; do not change the user's location preferences automatically.

### Telegram state and role limitation discovered

Read-only production counts for the configured Gmail owner account:

- linked Telegram private chats: **0**;
- per-user notification settings rows: **0**;
- enabled notification settings: **0**;
- notification ledger rows: **0**.

The Gmail owner is the active **administrator** account. Current dashboard code deliberately hides `telegramConnectPanel` for administrators, and `/api/telegram/status`, `/api/telegram/link`, and `/api/notifications/settings` reject administrator accounts (403). Therefore this owner cannot currently link a Telegram chat or explicitly opt in from the existing UI. This is not a Gmail sync failure. Do not try to work around it by connecting another OAuth tester mailbox or by assigning a different JobBeeper owner ID.

Before Telegram can be used for this personal Gmail owner, implement and test a narrow owner-admin Telegram linking/opt-in path bound to the configured Gmail owner account, preserving the current private-chat requirement, explicit opt-in, preferences/freshness/match checks, rate limits, retry/idempotency and Gmail historical-backfill marker. Do not create a link, enable notifications, or send Telegram messages as part of that code change. The owner must still complete the separate affirmative UI opt-in.

### Next steps

1. In the Jobs Feed, verify the retained PwC Gmail-sourced job and confirm it is appropriately visible in the owner's account. Keep the current preference filters unless the owner explicitly chooses to include India-wide locations.
2. Confirm the Gmail filter is saved for future Google Alerts and applies the label to matching new conversations. Label existence is confirmed; filter creation/application to future messages and historic conversations has not been explicitly confirmed.
3. Continue read-only monitoring of the 180-second incremental history polling. New messages should be processed only when carrying the configured label.
4. Decide whether `All India` should be included in the owner's saved target locations. Do not widen location preferences silently.
5. Implement the owner-admin Telegram connection/opt-in path before any Telegram notification test. Keep Telegram disabled until the owner links a private chat and explicitly checks the notification setting. Historical alerts should only be queued if current match, score threshold, freshness and all other delivery checks pass.
6. Retain evidence that this OAuth authorization was granted while the app is in Testing. Testing-mode authorizations are temporary and must not be treated as durable production approval; continue the Restricted-scope verification and server-side security-assessment/policy gates in the existing Google handoff.

No Telegram chat was linked, no notification setting was enabled, no Telegram message was sent, and no preferences were changed as part of this checkpoint.

## 22 November 2026 — Telegram owner-admin path deployed

PR #107 is merged and deployed. Only the configured Gmail owner admin can view/link/disconnect Telegram and access notification settings; ordinary admins remain blocked and member flows remain unchanged. The owner must still start the private link in Telegram and explicitly opt in. Bot `Qdhorvbot` has an HTTPS webhook registered at `https://130.210.27.197/api/telegram/webhook` for message updates only. `getWebhookInfo` confirms the endpoint, no pending updates and no last error. Notification settings remain disabled, there is no linked chat and no job alert has been sent.

The admin config-save route now schedules refresh of existing first-admin job evaluations after syncing profile preferences. The PwC job now recognizes India as a target location, but score is 44 and `no configured target-role match` remains; it is not eligible for notification. The owner should decide whether to add `Software Engineering` / `Associate Software Engineer` role equivalents or ask for a controlled matcher alias before expecting this job to match.

Current production release is `job-radar-prod-release:telegram-owner-20261122`, container `v2-radar-1`, external data volume `v2_radar-data`, loopback binding `127.0.0.1:8000`, health/dashboard/OpenAPI 200. Fresh root-only backup: `/var/backups/job-radar-daily/release-telegram-owner-20261122T074641Z` (checksum verified; integrity ok; 28,734 jobs; 1 Gmail credential; zero Telegram chats/notification opt-ins). Detailed test evidence and owner steps: `docs/TELEGRAM_OWNER_ADMIN_SETUP_HANDOFF_2026-11-22.md`.
