# Google Alerts Gmail — approved personal configuration and activation runbook

**Updated:** 22 November 2026  
**Scope:** One owner-controlled JobBeeper account, Google Alerts label only, `gmail.readonly`, localhost OAuth callback, periodic history polling.

## Approval record

The owner reported receiving Google approval for the intended personal Gmail workflow on 22 November 2026; the approval correspondence is not copied into this repository and remains in the owner's private records. **That report must not be interpreted as proof that this OAuth client has completed Google's OAuth verification.** A live authorization attempt on 22 November returned Google `403 access_denied`; the page states the app has not completed verification and is in Testing, accessible only to developer-approved testers. The current action is to verify the exact Cloud project's Audience/Test users configuration and add the intended Gmail mailbox as a test user if the project is External/Testing. This implementation remains limited to one owner account and the single `gmail.readonly` scope. Do not add other mailboxes, member accounts, broader scopes, Pub/Sub push, a public SaaS offering, or a materially different data flow.


## Superseding live runtime and OAuth test checkpoint — 22 November 2026

This section supersedes older statements in this runbook that say the production service has not been deployed, the Gmail environment is absent from the container, or Gmail live access remains disabled.

- The Gmail integration and two follow-up fixes are merged and deployed. Current image: `job-radar-prod-release:gmail-consent-20261122`; current container: `v2-radar-1`; host binding: `127.0.0.1:8000`; external data volume: `v2_radar-data`.
- The private Gmail environment is loaded by the active Compose service. `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=true` is currently set. This flag does not mean an account is connected; no Gmail credential/token exists yet.
- Owner successfully signed in through the localhost SSH tunnel. The consent API POST returns 200 and OAuth-start returns 302. Google then denies the OAuth request with 403 `access_denied`, explaining that the app is in Testing and only developer-approved testers may access it.
- Next owner action: select the exact Google Cloud project owning the configured Gmail OAuth Web client. In Google Auth Platform → Audience, verify user type and Publishing status. For External/Testing, add the exact Gmail account receiving the Google Alerts label under Test users and Save. Then retry from `http://localhost:8080/dashboard/#access` over the open SSH tunnel using that same mailbox.
- The attempted request asks only for `gmail.readonly`, with `access_type=offline`, PKCE S256 and the registered localhost callback. Google did not return a code; the callback was not reached.
- Read-only post-error DB counts: Gmail credentials 0; consent records 1; OAuth state rows 1; messages 0; sync rows 0; opportunities 0. SQLite integrity is `ok` and public jobs count remains 28,731. Consent/OAuth state rows do not prove a Gmail grant.
- Google's documentation classifies `gmail.readonly` as a Restricted scope. External/Testing authorizations are temporary (up to 100 test users; seven-day authorization expiry); this is not a durable polling deployment or a substitute for production restricted-scope verification/security assessment. Do not publish the app to Production as a quick workaround.
- Detailed activities, request evidence, exact counts, official Google links and the next safe checks are in `docs/GOOGLE_ALERTS_GMAIL_LIVE_ACCEPTANCE_HANDOFF_2026-11-22.md`.


## What is now wired in code

- `v2/docker-compose.yml` passes the dedicated Gmail OAuth client ID/secret, callback, owner account ID/email, Fernet key, polling mode, polling interval and live-access flag to the application container.
- The defaults are localhost callback `http://localhost:8080/api/integrations/google-alerts/gmail/callback`, polling every 180 seconds, and `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false`.
- `v2/google_alerts_gmail_preflight.py` validates the private configuration, polling-only setup, localhost callback and configured owner account. It reads the SQLite database in read-only mode and requires the owner ID to be an active administrator. It does not contact Google, read Gmail, send Telegram messages, print secret values or write to the database.
- The feature Compose file `v2/docker-compose.feature.yml` is still a disposable demo environment on port 8002, with a separate database, demo mode and a cookie-security override. It is **not** the personal Gmail runtime and does not pass the Gmail variables. Do not use `.env.feature` as the Gmail production configuration file.

## Private environment values

Add the following variables to the private environment file already used by the intended `v2/docker-compose.yml` deployment. Append them without replacing the existing JobBeeper/Telegram settings. Keep that file outside Git and set its permissions to `600`.

```dotenv
JOB_RADAR_GMAIL_OAUTH_CLIENT_ID=
JOB_RADAR_GMAIL_OAUTH_CLIENT_SECRET=
JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI=http://localhost:8080/api/integrations/google-alerts/gmail/callback
JOB_RADAR_GMAIL_OWNER_USER_ID=
JOB_RADAR_GMAIL_OWNER_EMAIL=
JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY=
JOB_RADAR_GMAIL_SYNC_MODE=polling
JOB_RADAR_GMAIL_POLL_INTERVAL_SECONDS=180
JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false
```

The Gmail OAuth client must be separate from the existing JobBeeper member-sign-in OAuth client. Configure only the exact localhost callback above and the `https://www.googleapis.com/auth/gmail.readonly` scope. Do not put credentials in Git, chat, dashboard JavaScript, screenshots or logs.

`JOB_RADAR_GMAIL_OWNER_USER_ID` is the numeric ID of the active JobBeeper administrator account. `JOB_RADAR_GMAIL_OWNER_EMAIL` is the Google mailbox that will be connected; it may differ from the email used to sign in to JobBeeper. The callback rejects a connected mailbox that does not match this configured Gmail address.

Generate a fresh Fernet key locally on the server using the application's installed Python environment, and store it only in the private environment file:

```bash
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode("ascii"))'
```

Do not reuse a key from another service or commit it. Keep a secure backup of this key separate from the SQLite database. Losing or rotating it while an encrypted refresh token remains stored will make that token undecryptable and require disconnect/re-authorization.

## Owner mailbox preparation

In the owner Gmail account, create the label `JobBeeper/GoogleAlerts` and a filter for Google Alerts messages from `googlealerts-noreply@google.com` with subject phrase `Google Alert -`. Select **Apply the label** and **Also apply filter to matching conversations** so historical matches are included. Review the result set before applying. Do not include Spam or Trash. JobBeeper uses read-only Gmail calls and never creates or changes the label/filter.

## Verified environment-file location and production Compose distinction

The owner populated `/home/ubuntu/job-beeper/.env`. At the pre-deployment checkpoint on 22 November, the file was verified as mode 600, owned by ubuntu:ubuntu; all nine Gmail variable names were present with non-empty, non-placeholder values. The feature checkout's configuration parser accepted the values, validated the Fernet key, confirmed the exact localhost callback and 180-second polling mode. At that checkpoint `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false`; the later deployed runtime now has this flag set to `true` (see the superseding live checkpoint above). A read-only query confirmed that the configured numeric owner ID maps to an active administrator. The reviewed Compose file passed:

    docker compose --env-file /home/ubuntu/job-beeper/.env -f v2/docker-compose.yml config --quiet

Historical note from the pre-deployment checkpoint: at that time, the running container had no JOB_RADAR_GMAIL_* variables and the owner .env had not been loaded. This was superseded on 22 November 2026 when the reviewed Gmail Compose release was deployed with `/home/ubuntu/job-beeper/.env`. Current container/runtime and OAuth status are documented in the superseding checkpoint above.

Historical release instruction: never modify an archived release bundle's runtime.env as a workaround. The reviewed deployment explicitly passed `/home/ubuntu/job-beeper/.env` using `--env-file`; the production service has since been recreated and the Gmail live-access flag is currently true. No secret values should appear in shell output. The live mailbox is still **not authorized** because Google denied the OAuth request before callback.

## Production release compatibility checks

The release Compose now explicitly preserves the current deployment contract:
- current deployed image is tagged `job-radar-prod-release:gmail-consent-20261122`; earlier candidate tag `job-radar-prod-release:gmail-20261122` is historical;
- host port remains loopback-only at 127.0.0.1:8000;
- the existing named volume is declared external as v2_radar-data, so the release cannot silently create a new empty DB volume;
- JOB_BEEPER_COOKIE_SECURE and JOB_BEEPER_PUBLIC_ORIGIN continue to flow from the private environment file; and
- the existing Telegram token/chat settings continue to flow from that same file.

Compose was checked using the real private env file with config --quiet; the resolved configuration was not printed. Do not substitute an all-interface port mapping or a new volume name.

The exact-head GitHub Actions V2 CI check for commit 5efa63121816a7cc854267c7d7d9fcbc0ea31ab3 finished failed before starting any steps (steps=[]). It did not execute tests. The local focused regression remains the available test evidence; do not treat the failed hosted check as a code-test failure or trigger extra paid CI attempts. The current focused suites and broader locally recorded regression evidence are in the activity log and PR description.

## Read-only preflight (completed before deployment)

The read-only Gmail configuration preflight was run before deployment with live access disabled and passed. It validated the owner administrator binding, dedicated OAuth settings, localhost callback and polling-only/no-PubSub configuration. The later Google OAuth `access_denied` is an Audience/Test users issue and was returned by Google after the app redirected successfully; it is not a preflight/config parsing failure.

Original preflight command:

```bash
python -m v2.google_alerts_gmail_preflight
```

Expected checks: all six required values parse, the callback is localhost, polling is configured with no Pub/Sub values, and the configured owner ID is an active administrator in the application database. The output deliberately omits client secrets, encryption keys, Gmail address and database contents.

A preflight failure must be corrected before enabling live access. Do not work around a failed owner binding by changing the database or using another account ID without reviewing the target account.

## Historical controlled activation sequence (deployment completed; OAuth grant pending)

Steps 1–5 below were completed as part of the 22 November deployment. Step 6 is currently blocked at Google's OAuth Audience/Test users gate. Do not repeat the deployment or toggle the current live-access setting to work around the Google error.

1. Confirm the private environment file contains the intended dedicated OAuth client, owner ID/mailbox, and separately generated Fernet key. This was completed; the currently deployed runtime has `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=true`.
2. Validate the effective Compose configuration without printing interpolated values or environment output. Build/release the reviewed branch only under the separately approved deployment procedure; this runbook does not authorize a production restart or deployment.
3. Run the read-only preflight with live access still disabled. Confirm the application is using the intended existing JobBeeper database and the configured owner ID maps to the active administrator account.
4. Confirm the owner Gmail label/filter is present. Keep Telegram notification settings separate from Gmail connection consent; connecting Gmail must not enable Telegram notifications.
5. At the owner's explicit go-live action, set `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=true` in the private environment and recreate/restart only the intended application service under the approved release procedure. This starts the 180-second polling worker. The first browser interaction must use the SSH tunnel and `http://localhost:8080`, not the VM IP.
6. Sign in as the configured JobBeeper administrator, review and accept the current in-product data-use disclosure, then connect the exact configured Gmail account. The callback verifies the mailbox identity and required user-created label before retaining an encrypted refresh token.
7. Verify sync status and one controlled backfill batch. Confirm that only verified public postings are retained and that no email body, snippet, alert query or mailbox identifier is sent to Telegram. Separately confirm the owner's Telegram notification setting and linked private chat before permitting delivery.
8. Verify pause/resume/retry and disconnect. Disconnect attempts Google token revocation and removes Gmail credentials, checkpoints and Gmail-only private discoveries; in-flight or already-sent Telegram messages cannot be recalled.

No Pub/Sub topic, subscription, public webhook, domain, DNS, certificate or paid GCP resource is required for this selected polling mode.

## Current configuration blocker

Historical pre-deployment blocker: the isolated PR checkout did not then have a private Gmail environment file. This was later superseded when the owner's private values were validated and loaded by the deployed production Compose service.

Current status is different: the production OAuth attempt reached Google but was rejected with 403 `access_denied` because the app is shown as Testing and only developer-approved testers can use it. No authorization code returned to the callback, no Gmail credential/token was stored, and no mailbox read or sync occurred. See the superseding checkpoint and live-acceptance handoff. The active live-access flag is currently true; it is not proof of authorization.
