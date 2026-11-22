# Google Alerts Gmail — approved personal configuration and activation runbook

**Updated:** 22 November 2026  
**Scope:** One owner-controlled JobBeeper account, Google Alerts label only, `gmail.readonly`, localhost OAuth callback, periodic history polling.

## Approval record

The owner reports that Google approval has been received for the intended personal Gmail workflow on 22 November 2026. The approval correspondence is not copied into this repository and must remain in the owner's private records. This implementation remains restricted to the approved single-owner use case and the single `gmail.readonly` scope. The owner reports no issue with the current workflow. Do not interpret this approval as permission to add other mailboxes, member accounts, broader scopes, Pub/Sub push, a public SaaS offering, or a materially different data flow.

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

The owner has populated /home/ubuntu/job-beeper/.env. On 22 November 2026, the file was verified as mode 600, owned by ubuntu:ubuntu; all nine Gmail variable names are present with non-empty, non-placeholder values. The feature checkout's configuration parser accepted the values, validated the Fernet key, confirmed the exact localhost callback, 180-second polling mode and JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false. A read-only query inside the production container confirmed that the configured numeric owner ID maps to an active administrator. The updated feature-branch Compose file also passed:

    docker compose --env-file /home/ubuntu/job-beeper/.env -f v2/docker-compose.yml config --quiet

**Important:** the currently running production container was created from /var/backups/job-radar-daily/release-dda6d57-20261118T2210IST/candidate-compose.yml, which uses ./runtime.env from that release directory. That separate root-owned runtime.env currently has only the pre-existing runtime keys; the running container has no JOB_RADAR_GMAIL_* variables. /home/ubuntu/job-beeper/.env is therefore prepared for the updated feature-branch Compose release, but it has not been loaded into the running container. The older /home/ubuntu/job-beeper checkout is also behind the feature branch and must not be used as the release source.

Do not manually modify the archived release bundle's runtime.env or restart the service as a workaround. The approved release must explicitly pass /home/ubuntu/job-beeper/.env using --env-file with the reviewed Compose file (or deliberately stage the same values in the new release's protected runtime env file as part of the reviewed release procedure). No secret values should appear in shell output. The current application has not been restarted and live Gmail remains disabled.

## Read-only preflight

After the reviewed code and Compose wiring are present in the target deployment, first keep live access disabled and run the preflight inside the app container:

```bash
python -m v2.google_alerts_gmail_preflight
```

Expected checks: all six required values parse, the callback is localhost, polling is configured with no Pub/Sub values, and the configured owner ID is an active administrator in the application database. The output deliberately omits client secrets, encryption keys, Gmail address and database contents.

A preflight failure must be corrected before enabling live access. Do not work around a failed owner binding by changing the database or using another account ID without reviewing the target account.

## Controlled activation sequence

1. Confirm the private environment file contains the intended dedicated OAuth client, owner ID/mailbox, and separately generated Fernet key. Keep `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false`.
2. Validate the effective Compose configuration without printing interpolated values or environment output. Build/release the reviewed branch only under the separately approved deployment procedure; this runbook does not authorize a production restart or deployment.
3. Run the read-only preflight with live access still disabled. Confirm the application is using the intended existing JobBeeper database and the configured owner ID maps to the active administrator account.
4. Confirm the owner Gmail label/filter is present. Keep Telegram notification settings separate from Gmail connection consent; connecting Gmail must not enable Telegram notifications.
5. At the owner's explicit go-live action, set `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=true` in the private environment and recreate/restart only the intended application service under the approved release procedure. This starts the 180-second polling worker. The first browser interaction must use the SSH tunnel and `http://localhost:8080`, not the VM IP.
6. Sign in as the configured JobBeeper administrator, review and accept the current in-product data-use disclosure, then connect the exact configured Gmail account. The callback verifies the mailbox identity and required user-created label before retaining an encrypted refresh token.
7. Verify sync status and one controlled backfill batch. Confirm that only verified public postings are retained and that no email body, snippet, alert query or mailbox identifier is sent to Telegram. Separately confirm the owner's Telegram notification setting and linked private chat before permitting delivery.
8. Verify pause/resume/retry and disconnect. Disconnect attempts Google token revocation and removes Gmail credentials, checkpoints and Gmail-only private discoveries; in-flight or already-sent Telegram messages cannot be recalled.

No Pub/Sub topic, subscription, public webhook, domain, DNS, certificate or paid GCP resource is required for this selected polling mode.

## Current configuration blocker

At the time this runbook was written, the isolated PR checkout has no `.env`/`.env.feature` Gmail credential file and no Gmail OAuth client ID/secret, owner ID or Fernet key installed in its environment. The tracked example contains placeholders only. The existing feature demo is unsuitable, and its environment file must not be repurposed. Therefore configuration wiring and the preflight are ready, but the Gmail OAuth client/private values still need to be installed in the actual deployment environment before the preflight can pass.

No real OAuth request, Gmail mailbox read, Telegram external send, production DB migration, container restart, deployment or live-access activation is performed by this implementation change.
