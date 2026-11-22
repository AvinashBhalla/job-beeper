# Google Alerts Gmail Inbox Integration

**Date:** 21 November 2026  
**Repository:** `AvinashBhalla/job-beeper`  
**Target branch:** `v2-live-radar`  
**Planning branch:** `feat/google-alerts-gmail-ingestion`  
**Status (22 November 2026):** Parser, public-posting verifier, label-scoped Gmail OAuth/sync backend, owner-only notification controls and account UI are implemented in the isolated feature checkout. The personal no-domain mode now supports a localhost OAuth callback over an SSH tunnel and periodic Gmail history polling without Pub/Sub. Draft PR #102 remains unmerged. No Gmail authorization, Pub/Sub resources or production changes.

## 0. Implementation checkpoint and corrected personal scope — 22 November 2026

The owner has clarified that this is for **one personal Job Beeper account only**. There are no additional users to support, no planned member onboarding and no near-term hosted SaaS deployment. Do not build account switching, per-customer Gmail grants, tenant administration, or a generalized multi-member Gmail product. The existing Job Beeper `users.id` is retained only as the signed-in owner identity required by the current authentication, preferences and private Telegram data model; it is not a request to productize multi-user Gmail.

The owner does not currently own a domain and does not want to buy one. The current personal-use path is **localhost OAuth through an SSH local-port-forward tunnel plus periodic Gmail history polling**. Google explicitly permits `http://localhost:<port>` redirect URIs for web-server OAuth clients; the callback host is localhost in the browser, while the SSH tunnel forwards it to the VM application. Polling uses the Gmail `users.getProfile` history cursor and `users.history.list`; no `users.watch`, public callback hostname, Pub/Sub topic, subscription, OIDC push endpoint or paid Google Cloud resource is needed. Poll interval defaults to 180 seconds and is configurable from 60 to 3600 seconds. Pub/Sub push remains an optional future hosted mode, not the personal default. Notifications continue to use the owner's existing dashboard and Telegram chat. **Deployment/activation is deferred until the owner is ready and the release gates below are closed.** Code work and a feature-branch push are not authorization to enable Gmail access, provision GCP resources or alter the running service.

For the local tunnel, the browser must access JobBeeper through `http://localhost:8080` (not the VM IP) so the login and Gmail OAuth state cookies are scoped to localhost. The VM's application listener was verified read-only at `127.0.0.1:8000` and its `/health` endpoint returned `status=ok`. After the feature branch is released to the VM under separate deployment approval, the exact tunnel command is `ssh -N -L 8080:127.0.0.1:8000 ubuntu@130.210.27.197`; then open `http://localhost:8080`. The tunnel must remain open throughout login and the Google consent callback. Only a direct HTTP request to `localhost` arriving from loopback without proxy headers gets a non-Secure cookie; public/proxied requests remain Secure. Never set the global cookie-secure setting to false to make this work.

Implementation now present in the isolated branch checkout:
- `v2/google_alerts_email.py`: generic Google Alerts parser with metadata preflight and bounded extraction.
- `v2/google_alerts_gmail.py`: Personal Mode OAuth/PKCE, encrypted refresh-token storage, label-scoped Gmail API, full backfill/history recovery, optional OIDC Pub/Sub push and durable processing queue. Polling mode initializes from `users.getProfile.historyId` and performs incremental history sync at the configured cadence without calling `users.watch`. Access tokens are cached only in process memory; refresh tokens remain encrypted at rest.
- `v2/google_alerts_job_verifier.py`: safe public HTTPS posting verification, robots policy and active Schema.org JobPosting checks.
- `v2/radar.py` and `v2/user_notifications.py`: verified opportunity ingestion and owner Telegram historical-backfill behavior. Historical Gmail delivery still observes current preferences, freshness, Telegram opt-in, private-chat routing, throttling, retries and idempotency. Other sources' backlog behavior is unchanged.
- `dashboard/index.html` and `dashboard/app.js`: owner-only Gmail connect/disconnect, status, sync progress and historical Telegram pause/resume/retry controls. The UI does not display mailbox addresses, alert search terms, snippets, message IDs or credentials.
- `v2/requirements.txt`: explicit `cryptography` dependency for Fernet token encryption.

The `.venv/` is an isolated local environment and is excluded from Git. Continue to use the configured feature branch and leave draft PR #102 unmerged until the full release review is complete.

### Production-readiness gates — must close before activating Gmail

1. Read `docs/GOOGLE_GMAIL_RESTRICTED_SCOPE_POLICY_ASSESSMENT_2026-11-22.md`. The personal-use exception appears to cover the OAuth verification submission for this one-owner app only. Google's approved Gmail use-case categories do not explicitly name job discovery from Alerts; obtain Google's classification for this workflow. Because the backend accesses Restricted Gmail data through a VM-hosted server, assume the security assessment/CASA applies unless Google confirms otherwise. Also resolve Limited Use and derived-data treatment, Telegram transfer consent, retention/encryption, and privacy/help publication before live access.
2. The localhost/polling-mode backend changes passed the complete **34-module V2 regression: 616 tests, zero failures**, across nine bounded local batches. After the dashboard disclosure/consent UI change, the focused dashboard/Gmail regression passed **59/59**; `node --check dashboard/app.js`, Python compilation and `git diff --check` passed. The reviewed feature branch is pushed at `62989e8e2bbfc7c5642ee1a8ce724eb04c00a3e1`; PR #102 remains draft/open/unmerged. Neither offline suite replaces controlled live Gmail acceptance.
3. Verify the VM's actual loopback application port and SSH tunnel path without changing the public reverse proxy. With a controlled owner mailbox, confirm localhost login/callback, label/filter setup, metadata-first/raw-only-after-authentication behavior, race-free historical backfill, incremental polling recovery, owner Telegram delivery, pause/resume/retry and disconnect deletion. The private `.eml` fixture must remain outside Git and logs.
4. No Pub/Sub or public HTTPS callback is required for the personal polling mode. If push mode is ever reintroduced, validate public HTTPS and authenticated OIDC delivery and confirm GCP billing/pricing before creating resources. No paid resource or billing change has been authorized.
5. Prepare a production migration backup, rollback and service restart plan. Do not deploy to or restart production until a separate go-live action is explicitly requested after these gates pass.

The current isolated checkout is `/home/ubuntu/job-beeper-google-alerts-dev` on `feat/google-alerts-gmail-ingestion`. It is a separate clone and venv on the connected `job-radar` host; do not infer that the live app, database, Nginx or containers were changed. Prefer a non-production machine for future test runs. No Gmail OAuth, real mailbox access, Telegram external send, GCP provisioning or production deploy has been performed.

For the 22 November deployment-readiness audit, read `docs/GOOGLE_ALERTS_GMAIL_ACTIVITY_LOG_2026-11-22.md` and `docs/GOOGLE_GMAIL_RESTRICTED_SCOPE_POLICY_ASSESSMENT_2026-11-22.md`. The activity log records source-control state, the 616-test full V2 regression, read-only production container/Compose inspection, why the port-8002 demo Compose file is unsuitable, the stale 18 November backup bundle, the localhost SSH command, and the explicit non-deployment boundaries. The policy assessment records the unresolved allowed-use-case and CASA questions, data-flow review and consent/privacy/help requirements.

### Offline validation snapshot — 22 November 2026

After the localhost/polling-mode code changes, all **34 V2 test modules passed: 616 tests, zero failures**, in nine bounded local batches (107, 28, 51, 53, 49, 191, 42, 26 and 69 tests). Coverage included authentication, board discovery/scheduling, ATS and global discovery, Gemini/LLM, Gmail parsing/OAuth/history polling, source radar, SERP, SQLite, Telegram, applications and user preferences/notifications. Python compilation and `git diff --check` passed. This remains offline synthetic validation: no real Gmail OAuth/API request, actual Pub/Sub OIDC push, external Telegram send, or production service was exercised.

---

## 1. Corrected owner requirement — authoritative

The owner has multiple Google Alerts rules. Each rule uses a different search string to broaden job discovery. Google sends the resulting alert messages to one existing owner-controlled Gmail inbox.

The messages have the same Google Alerts email structure. Their content differs because each Alert uses a different search string. One email may contain multiple matching items, and each item must be extracted and processed independently.

JobBeeper must:

- Read the owner's existing Gmail inbox directly; no manual forwarding is required.
- Connect exactly one owner-controlled mailbox through a dedicated owner-only OAuth authorization.
- Detect Google Alerts emails and parse every result item from each message.
- Treat all alert emails as the same format; do not build one parser or feed per search string.
- Verify each destination posting, deduplicate repeated postings across alerts and send valid job records through the existing V2 shared ingestion path.
- Evaluate each stored job against the owner's saved preferences. The connection is bound to this one local account; mailbox contents, alert queries and Gmail metadata are never exposed in the dashboard or Telegram.

**This requirement supersedes the RSS/Atom direction in the earlier planning notes and PR #101. No RSS feed URLs are required for this email-based design.**

## 2. Architecture decision for the MVP

### 1.1 Sample email inspection — uploaded owner fixture

One owner-supplied `.eml` file was inspected on 21 November 2026. The raw file is **not** committed because it contains the mailbox address, message/thread identifiers, alert-management URLs, tracking tokens and an RSS footer link. The parser must not retain or export those values.

Observed structure:

- RFC 5322 message with `From: Google Alerts <googlealerts-noreply@google.com>`.
- Subject begins with `Google Alert - ` followed by the alert's search string. Treat the full subject/search string as private metadata; the parser validates only the prefix and does not return it.
- `multipart/alternative` with a UTF-8 plain-text part (base64 transfer encoding) and UTF-8 HTML part (quoted-printable transfer encoding).
- HTML includes a `script[data-scope="inboxmarkup"]` element with `type="application/json"`. The object identifies publisher `Google Alerts` and contains `cards[].widgets[]` entries of type `LINK`, with `title`, `description` and `url`.
- The same three result cards also appear in visible HTML anchors and in the plain-text alternative.
- Each result URL is a Google `/url` redirect with its publisher destination embedded in the `url` query parameter.
- The sample includes three job result items from two publisher domains. The email footer also contains non-result links such as alert settings, unsubscribe and RSS; these must not be treated as job results.

The primary extraction path is the structured JSON block, validated by the exact Google Alerts sender, the subject prefix, one unambiguous Gmail `mx.google.com` DKIM/DMARC authentication result, and the embedded publisher name. If that block is missing/invalid, the parser falls back to Google result anchors in the HTML. If there is no usable HTML result, it falls back to wrapped links in the plain-text part. The plain-text format wraps long titles across lines, so this is a lower-confidence fallback; final job title/employer/location are always verified from the destination posting.

**Parser implementation added in draft PR #102:**
- `v2/google_alerts_email.py` accepts raw RFC 5322 bytes (Gmail API `format=raw` response after base64url decoding).
- Validates sender and subject prefix, MIME/body size limits, HTTPS destinations and a bounded number of Google redirect unwrappings.
- Extracts all structured `LINK` widgets (up to the configured per-message limit), removes canonical duplicate destinations and returns only minimal result fields plus a SHA-256 message fingerprint.
- Does not perform network requests or persist raw email, recipient, query, message ID, Google tracking tokens, alert settings links or RSS footer URL.

Focused parser tests cover multi-result structured HTML, canonical duplicate collapse, HTML and plain-text fallbacks, sender/subject/authentication rejection, invalid redirect handling, raw-size limits and rejection (rather than silent truncation) when a message exceeds the per-email result cap. The current parser suite has 18 passing tests.


Use Gmail API read-only access with **periodic Gmail history polling** for the personal no-domain mode. The application performs an initial label-scoped backfill from a `users.getProfile.historyId` baseline, catches up history after the scan, and then calls `users.history.list` at the configured interval. The cursor is durably advanced only after all pages and discovered message IDs are staged. A stale cursor (HTTP 404) triggers a fresh profile baseline and a full label-scoped resynchronization. Optional Pub/Sub push remains available only when explicitly configured as `JOB_RADAR_GMAIL_SYNC_MODE=push`; it is not needed for the owner's current setup. Do not provision GCP resources or change the public endpoint for polling mode.

### 2.1 Separate owner-only authorization

The existing `v2/google_oauth.py` flow is for JobBeeper account/member sign-in and requests only `openid email profile`. Keep it unchanged.

This first release is **strictly personal and single-account**. Create a separate Google Cloud project using Google's **Personal Mode** onboarding, then create a **Web application** OAuth client with the localhost callback `http://localhost:8080/api/integrations/google-alerts/gmail/callback` (or the exact chosen local tunnel port). Google documents localhost redirect URIs as an exception to its HTTPS-only redirect rule. Do not use the VM's raw IP as the OAuth redirect host. Personal Mode restricts authorization to the Google Account that created the project, removes OAuth app verification and the unverified-app screen for that creator, and avoids the External-app testing cap/token expiry. It is a one-way project choice: it cannot later be converted to External/Internal or shared. If JobBeeper ever becomes multi-member for Gmail, create a separate OAuth project and complete its own policy/verification process; do not widen this personal client.

Implement a dedicated Gmail connection with its own:
- Personal Mode OAuth client ID/secret and redirect URI;
- authorization state and PKCE verifier;
- owner-only connect/disconnect controls and account-identity binding;
- encrypted refresh-token storage and key separation;
- connection status, token refresh, revocation and disconnect cleanup.

Request only `https://www.googleapis.com/auth/gmail.readonly`. Do not request `gmail.modify`, `mail.google.com`, `gmail.labels`, or any broader/additional scope. The owner creates the label/filter in Gmail; the application only reads labels and messages. Keep Gmail authorization entirely separate from member OIDC. No OAuth secret, access token or refresh token may enter GitHub, chat, browser storage, logs or plaintext DB columns. The refresh token is encrypted at rest using a key held separately from the SQLite volume (VM secret/environment file with restrictive permissions or a dedicated secret store).

**Owner consent recorded (21 November 2026):** the owner explicitly agrees to personal Gmail authorization and Telegram notifications. On 22 November, the owner selected localhost OAuth + SSH tunnel + polling instead of purchasing a domain or provisioning Pub/Sub. This is not permission to expose Gmail-derived discovery metadata or job observations to other JobBeeper accounts.

Never add Gmail scopes to ordinary member sign-in. Never expose owner OAuth start/callback/status/refresh-token data to ordinary member accounts.

### 2.2 Inbox filtering

**Required owner setup:** create a Gmail user label named `JobBeeper/GoogleAlerts` and a Gmail filter that adds this label to matching Google Alerts messages. Use sender `googlealerts-noreply@google.com` and subject phrase `"Google Alert -"` as candidate filter criteria. In Gmail's filter UI, select **Apply the label: JobBeeper/GoogleAlerts** and **Also apply filter to matching conversations** so existing matching messages are labelled for the full historical backfill as well as future arrivals. Review the matching set in Gmail before applying. Do not include Spam or Trash.

JobBeeper will use read-only `users.labels.list` to resolve the exact label ID, then use `users.messages.list(labelIds=[label_id], includeSpamTrash=false)` for the initial backfill and `users.history.list(labelId=label_id)` for incremental synchronization. Follow all page tokens. Do not use an unlabelled mailbox-wide message list or a broader Gmail search in the application. The application must still validate every candidate's exact sender, subject prefix, and unambiguous Gmail authentication headers before requesting `format=raw`. The label is a selection filter, not an OAuth security boundary: `gmail.readonly` remains a Restricted scope with broad technical read capability. Therefore, enforce label-ID scoping in one shared Gmail client wrapper, add tests proving all list/history calls carry that label ID, and never fetch raw bodies for any unlabelled message.

Do not add the `gmail.labels` scope or programmatically create/change the Gmail filter. The owner does this once in Gmail UI; the app is read-only. Google documents that `messages.list` accepts `labelIds` and that `history.list` accepts `labelId`, both with pagination.

### 2.3 Optional future Gmail push mode (not used by personal polling)

The following push-mode design is retained for a future hosted setup only. The current personal path uses the localhost OAuth callback and periodic `users.history.list` polling; it does not call `users.watch`, create Pub/Sub resources or expose a public webhook. If push mode is explicitly selected later, the flow is **Gmail push → Cloud Pub/Sub → authenticated HTTPS webhook → durable sync queue → Gmail history reconciliation**. The Pub/Sub notification is a change pointer, not an email body. The webhook must never parse or fetch mail inline.

**Cloud setup:**
1. Create one Pub/Sub topic in the personal-mode project (or a separate small GCP project explicitly linked to it) and one push subscription targeting the JobBeeper webhook.
2. Grant `gmail-api-push@system.gserviceaccount.com` Publisher permission on the topic.
3. Configure authenticated Pub/Sub push using a dedicated user-managed service account and OIDC JWT audience. Validate the JWT signature, issuer, audience, expiry and expected service-account identity at the webhook.
4. The push endpoint must be publicly reachable over HTTPS with a valid CA-signed certificate. The Oracle VM currently sits behind Nginx; before creating the subscription, inspect the actual certificate chain and SAN and confirm the exact callback route is reachable from Google. If the present IP-based HTTPS origin does not meet the public TLS requirements, use a domain with a valid certificate. Do not relax TLS or expose an unauthenticated webhook to make it work.
5. Create the topic/subscription only after checking the GCP project billing state and current Pub/Sub free-tier/pricing. No paid resource or billing change is authorized by the architecture choice alone.

**Watch configuration:**
- Resolve `JobBeeper/GoogleAlerts` to its Gmail label ID using read-only `users.labels.list`.
- Register Gmail `users.watch` with `topicName`, `labelIds=[label_id]` and `labelFilterBehavior=INCLUDE`. The Gmail API requires the Gmail push service account to be able to publish to the topic.
- Persist the returned `historyId` and `expiration`. The returned history ID is the sync baseline for changes after watch registration. A successful watch also emits an immediate notification, which is harmless and must be processed idempotently.
- Renew `users.watch` daily; Gmail requires renewal at least every seven days. Store the current expiration and alert/log if renewal fails.

**Race-free initial synchronization — owner-selected all available emails:**
1. Ensure the Pub/Sub topic/subscription and durable webhook queue are ready first.
2. Call `users.watch` with the dedicated label filter and persist the returned history ID as the backfill baseline **before** scanning historical mail.
3. Enumerate every message carrying `labelIds=[label_id]` with `includeSpamTrash=false`, follow every `nextPageToken`, and apply no date cutoff. This includes matching labelled messages in Inbox and archived/All Mail; Spam and Trash remain excluded.
4. Durably stage each message ID and page progress before advancing. Resume interrupted scans from the last committed page/checkpoint.
5. Run the metadata-only preflight below, then retrieve `format=raw` only for messages whose exact sender, subject prefix and unambiguous Gmail `Authentication-Results` pass.
6. After the enumeration is staged, call `users.history.list` from the watch response's baseline history ID, filtered with `labelId=label_id`, and page through all records. Include `messageAdded` and `labelAdded` change types; enqueue messages that are added to or receive the dedicated label while the full scan is running.
7. Commit the resulting history cursor only after every page and every discovered message ID is durably staged. Process all message IDs idempotently; do not declare backfill complete while any candidate is pending or retryable.

**Push event handling and ongoing sync:**
- The webhook accepts only the configured Pub/Sub subscription and a valid OIDC-authenticated push. Decode the Pub/Sub `message.data` payload to obtain the authorized mailbox identity and new `historyId`; validate the identity against the one owner account bound during OAuth.
- Persist a compact notification/outbox record (Pub/Sub message ID, high-water history ID, receive time and processing status), then return HTTP 2xx. Acknowledge only after durable persistence. Do not log the payload, token, mailbox address or any email content.
- A worker coalesces notifications and calls `users.history.list(startHistoryId=last_committed_history_id, labelId=label_id)`, pages every result, collects `messageAdded` and `labelAdded` message IDs, and stages them before advancing the cursor.
- For every candidate, call `messages.get(format=metadata)` with only `From`, `Subject` and `Authentication-Results`. Drop unlabelled/non-Google Alerts messages without requesting their bodies. For authenticated candidates only, call `messages.get(format=raw)`, base64url-decode, parse in memory and enqueue each result.
- Gmail notifications can be delayed or dropped and are capped at one notification event per second per watched user. Run a low-frequency periodic `history.list` reconciliation (for example, every 15 minutes) as a safety net in addition to push. Push is a latency optimization, not the source of truth.
- If Gmail returns HTTP 404 for an expired history cursor, run a full label-scoped resynchronization with an overlap, deduplicate against the processing ledger, then establish a new cursor. Do not silently skip the gap.

The worker runs inside the existing V2 service/runtime on the Oracle VM after separate isolated validation. GitHub Actions are not part of the runtime path.

### 2.4 Email parsing

The parser is generic for Google Alerts emails, not query-specific.

- Handle Gmail message payloads containing multipart MIME structures.
- Decode nested `text/html` and `text/plain` bodies safely.
- Prefer the HTML structure for result cards when both parts exist, while retaining plaintext fallback.
- Extract all result items, not just the first item in a message.
- For each result, collect only the minimum transient data needed: title, snippet, destination link and any available date/source text.
- Resolve Google redirect/tracking links safely; canonicalize the final public destination URL.
- Do not trust the email snippet as proof that a posting exists.
- Isolate malformed result cards so one malformed item does not discard other valid items in the same message.
- Treat email content and links as untrusted input; enforce URL scheme/host checks, DNS/SSRF protection, redirect limits, response-size limits, robots policy and per-host backoff when fetching destinations.

The owner supplied a representative Google Alerts `.eml` containing multiple result items. Its MIME structure, sender/subject pattern, structured HTML cards and destination redirect shape were inspected; the raw fixture remains outside GitHub. Do not claim the committed parser is validated until the sanitized fixture and synthetic edge cases have been exercised by the committed test module in an isolated non-production environment.

### 2.5 Shared job verification and personal ingestion

For each extracted result:

1. Normalize and canonicalize the destination URL.
2. Collapse duplicate destinations found in the same email, across different alert emails, or across different alert search strings.
3. Fetch the public job posting through the reviewed safe-fetch implementation. Do not bypass 403/429, robots denial, login walls, CAPTCHAs or other access controls.
4. Verify that the destination is still an active/current public posting. Prefer structured `JobPosting` evidence and validate required fields such as title and employer. Route uncertain, removed or closed pages to review/rejection rather than inventing a job.
5. Normalize verified records through existing V2 `normalize_job()` and store them with existing `upsert_jobs()`.
6. Link to an existing public canonical opportunity where the public posting is already known; otherwise persist the discovery with an explicit owner-only source visibility marker.
7. Evaluate the job against the owner's saved `user_preferences` and create a per-user notification-ledger entry for eligible matches.

**Owner-approved historical notifications:** the owner explicitly wants Telegram notifications for jobs discovered from the initial historical backfill as well as future alerts. Do not silently suppress the historical batch. Add a Gmail-source-specific historical-backfill delivery mode that bypasses only the generic no-backlog/notification-enabled-at cutoff for messages discovered by this one-time sync. It must still enforce current saved role/location/skill/experience preferences, verified active posting status, canonical deduplication, the owner's Telegram opt-in and linked private chat, retry limits, rate limits and delivery ledger idempotency. Do not change no-backlog behavior for other job sources. Queue the historical batch durably and send in controlled batches respecting Telegram throttling; expose counts/progress and allow pause/retry without re-importing or duplicating notifications. The default must be to send notifications for all verified eligible historical matches, not to flood with unverified email cards.

Telegram message content must be generated from the verified public job posting only. Never include the Google Alert email body, alert search string, recipient, message/thread IDs or Gmail metadata.

Do not store raw email bodies, whole MIME payloads, attachments, unrelated message headers, or Gmail snippets in the jobs database. The Gmail message processing ledger should retain only minimum identifiers/checkpoints/status needed for idempotency, under a documented retention policy. Fetch public posting details from the public destination rather than treating the email itself as the durable source of job content.

## 3. Personal-use OAuth and Restricted-data guardrails

This is now a **single-user personal integration**, not a multi-member mailbox product.

- Google's documented personal-use exception covers an app used only by its creator or a few personally known users; that use case does not need to be submitted for OAuth verification. Confirm the exact publishing/testing configuration and user cap in the Google Auth Platform project before connecting. The integration remains single-owner regardless of any future product plans.
- `gmail.readonly` is still classified as a **Restricted** Gmail scope. Personal Mode removes the OAuth app verification step for the creator, but does not remove the obligation to follow Google's Workspace User Data Policy and Limited Use requirements.
- Google's Gmail approved-use examples include personal productivity features and email-derived reporting/monitoring for the user's benefit. This personal job-alert tracker is designed as a productivity/monitoring feature for the owner only. Job discovery itself is not explicitly named in Google's examples, so do not expand it into a shared/member service, advertising, resale, profiling or model training without a fresh policy review.
- **Server-side security assessment is a separate gate:** Google's current restricted-scope guidance says that if restricted-scope data is stored/transmitted on servers, or the app can access it from/through a third-party server, a security assessment is required. The same page separately lists personal use as an exception to the OAuth verification process. It does not state that the personal-use verification exception also waives the server-side assessment. The Oracle VM architecture is server-side; get a definitive applicability answer for this creator-only deployment before enabling persistent production token/mail access. If an assessment is required, complete it or redesign the integration so the restricted-data server requirement is not triggered.
- Do not add Gmail scopes to member OIDC or allow any other JobBeeper account to connect/authorize Gmail. Personal Mode must remain bound to the owner account.
- Data minimization: fetch only label-scoped candidate IDs, validate metadata before body retrieval, parse raw MIME in memory, discard raw email/snippets/query/headers and keep only minimal sync metadata and publicly verified posting data. Do not send email-derived content to Telegram. Telegram messages must be built from the independently fetched public job posting only.
- Encrypt the refresh token at rest and keep its encryption key separate from the database; restrict file/process access; redact OAuth and webhook data from logs; support revoke/disconnect and deletion of tokens/checkpoints/processing metadata.
- If the intended use changes to shared members, customer accounts or another Gmail account, stop and create a new OAuth/security/policy design. Do not reuse the personal-mode client.

The personal-use verification exception is grounded in Google's current Personal Mode and restricted-scope documentation. The separate security-assessment question remains an explicit pre-production control, not a reason to mislabel the app as multi-member.

## 4. Current code baseline and boundaries

- Existing member OAuth: `v2/google_oauth.py`, `v2/test_google_oauth.py`; member sign-in scope remains `openid email profile` and must not be modified.
- Existing ingestion/evaluation: `v2/radar.py` provides `normalize_job()`, `upsert_jobs()`, canonical opportunities and per-user job evaluations. Gmail must not bypass destination verification.
- Existing per-user Telegram delivery: `v2/user_notifications.py` uses `user_notification_settings`, `user_notification_ledger`, `user_job_evaluations` and a private `user_telegram_chats` link from `v2/telegram_linking.py`. Use this path for the owner's personal Telegram delivery. Do **not** use legacy global `v2/telegram.py` / `notification_ledger` for Gmail-originated notifications.
- **Implemented private-source boundary:** public ATS jobs remain shared; a Gmail-only job carries the configured owner marker and the Gmail opportunity observation records the owner. A known public URL reuses its public canonical opportunity. Preserve the narrow owner check because it protects this personal account's private discovery records; do not expand it into member administration or a multi-user Gmail product.
- Owner Gmail jobs must be evaluated against the owner's `user_preferences`, visible in the owner's dashboard, and queued only to the owner's linked private Telegram chat after per-user opt-in. Keep Telegram alertability/freshness and no-backlog rules intact.
- **Owner decision: send Telegram notifications for eligible verified jobs from the initial historical backfill as well as future arrivals.** Use a Gmail-source-specific historical-backfill delivery marker that bypasses only the generic no-backlog/`enabled_at` cutoff. Preserve current preferences, active-public-posting validation, canonical deduplication, per-user Telegram opt-in, linked private chat, rate limits, retry policy and delivery-ledger idempotency. Send in controlled batches. Do not change backlog policy for other sources or notify from email snippets.
- The previous RSS work in PR #101 is superseded and must not be merged. The Cloudflare Email Routing branch remains quarantined.
- Runtime target: Oracle VM `job-radar`, FastAPI behind Nginx. The application listener currently responds on `127.0.0.1:8000`; the personal OAuth flow reaches it through an SSH local-port-forward and does not require DNS, certificates or Nginx changes. Do not modify production, OAuth or DB during architecture review. A separate deployment approval is required before releasing the feature branch.
- Keep code and test data in the isolated feature checkout/database. The current isolated clone is physically on the connected `job-radar` VM but is separate from the live checkout/service/database; prefer a genuinely non-production machine for any further broad regression run.
- Do not trigger GitHub Actions or incur paid runner spend. Check GCP Pub/Sub current pricing/billing before resource provisioning; no billing enablement or billable resource creation is implied by the architecture selection.

## 5. Validation plan

1. Owner creates the `JobBeeper/GoogleAlerts` label/filter and applies it to all existing matches; verify future Alerts receive the label.
2. Build the Personal Mode OAuth client for a Web application callback; keep credentials outside GitHub/chat and test state, PKCE, account binding, token refresh, revoke and encrypted token storage with a mock token service first.
3. Mock-test Pub/Sub webhook OIDC validation, wrong audience/service account rejection, durable acknowledgement, duplicate delivery, notification coalescing and rate handling.
4. Mock-test polling baseline capture from `users.getProfile.historyId`, initial backfill race catch-up, label-scoped `history.list` pagination, cursor expiry/404 recovery and configured periodic reconciliation. Optional future push-mode tests also cover `users.watch` label filtering, watch expiry/renewal, and `messageAdded`/`labelAdded` notifications.
5. Add assertions that every list/watch/history API call carries the dedicated label ID and every message-body retrieval follows a passing metadata preflight. A non-Google or unlabelled message must never receive `format=raw`.
6. Verify public job destination fetch, normalized fields, canonical dedupe and private owner-only source visibility. Confirm no Gmail-only row is visible to another account/admin feed or evaluated/queued by another user's notification worker.
7. Verify that the owner's per-user Telegram setting/private chat receives notifications for eligible jobs from both historical backfill and future arrivals. Historical backfill must use a Gmail-source-specific override for only the generic no-backlog/notification-enabled-at cutoff; preserve preferences, current-live-posting validation, deduplication, opt-in, private-chat routing, throttling, retries and delivery-ledger idempotency. Do not alter other sources' backlog policy. Legacy global Telegram sender/ledger must remain untouched by this source.
8. **Completed offline (22 November 2026):** after the localhost/polling-mode edits, all 34 V2 test modules passed in nine segmented local batches (616 tests, zero failures). `py_compile` for the changed Python modules and `git diff --check` passed. Record the exact reviewed/pushed commit SHA for future acceptance; do not use the production database or paid GitHub Actions. Live Gmail, Telegram delivery and production acceptance remain separate gates.
9. Read-only preflight the VM callback's public HTTPS certificate chain/SAN/firewall/Nginx path. Only then create Pub/Sub resources with authenticated OIDC push. Confirm project billing/pricing before provisioning.
10. Determine whether creator-only Personal Mode exception also affects the separate security-assessment rule for restricted data processed on the Oracle VM. Do not store production tokens or enable the live mailbox until the requirement is resolved and all security/data-minimization controls pass.

## 6. Owner input required

No credentials, OAuth secrets, Gmail password, app password, refresh token, or access token should be sent in chat.

The owner has supplied a representative Google Alerts `.eml` with multiple results and expressly consented to a personal owner-only Gmail connection. The raw fixture remains outside GitHub and must not be copied into logs or durable application storage.

The owner has selected:
- Eventual hosting target: existing Oracle VM `job-radar`; deployment is deferred and no near-term hosted launch is planned.
- Trigger: periodic Gmail history polling every 180 seconds by default for personal use; optional Pub/Sub push remains a future hosted mode.
- Results: existing owner dashboard plus Telegram, using only the owner's per-user private Telegram chat.
- Backfill: all available labelled Google Alerts emails, no date cutoff; Spam and Trash excluded.
- Mailbox boundary: only the `JobBeeper/GoogleAlerts` label. The owner creates the label/filter in Gmail; the app never lists unlabelled mailbox messages or retrieves unlabelled bodies.
- Product boundary: creator-only personal instance for the first release. No other JobBeeper user may connect Gmail or see Gmail-only discoveries.

The owner must still create the Personal Mode OAuth project/client and configure the Gmail label/filter. The webhook endpoint's CA-signed public HTTPS requirements and the restricted-data server-side security-assessment applicability must be checked before live OAuth and Pub/Sub activation. Do not request secrets in chat; use a secure local/VM credential handoff only after implementation and controls are ready.

## 7. Official references reviewed on 21 November 2026

- [Gmail API users.history.list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) — incremental mailbox history, optional label filter, pagination, history cursor and HTTP 404/full-sync recovery.
- [Synchronize clients with Gmail](https://developers.google.com/workspace/gmail/api/guides/sync) — full sync, partial sync and history expiration.
- [Gmail API users.messages.get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get) — full message retrieval.
- [Gmail API message format reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/Format) — full/raw vs metadata-only behavior.
- [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) — `gmail.readonly` scope classification.
- [Google Workspace user data and developer policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy) — approved Gmail use cases, Limited Use, data transfer and security requirements.
- [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) — verification exceptions and server-side restricted-data security-assessment requirements.
- [Google Auth Platform Personal Mode](https://support.google.com/cloud/answer/15544987?hl=en) — creator-only personal projects, Web OAuth client setup, no OAuth verification and one-way project configuration.
- [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) — personal-use verification exception and separate security-assessment language for restricted data processed through servers.
- [Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push) — label-filtered watch, Pub/Sub topic permissions, watch expiry/renewal, notification payload and history reconciliation.
- [Pub/Sub push subscriptions](https://cloud.google.com/pubsub/docs/create-push-subscription) — publicly accessible HTTPS endpoint, CA-signed TLS certificate and authenticated push configuration.
- [Gmail history.list reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) — labelId, historyTypes, pagination, messageAdded/labelAdded records and HTTP 404 recovery.



**Current official Google references checked 22 November 2026:**
- [Restricted scope verification and personal-use exception](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) — personal use is listed under exceptions to verification (section “Personal use”); the page separately states that restricted-scope data stored/transmitted on servers or accessed from/through third-party servers requires a security assessment (sections “Understand restricted scopes” and “Security assessment”).
- [Google Cloud list of restricted scopes](https://support.google.com/cloud/answer/13464325) — confirms `https://www.googleapis.com/auth/gmail.readonly` is restricted.
- [Gmail `users.watch`](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/watch) and [push notifications guide](https://developers.google.com/workspace/gmail/api/guides/push) — confirms label filtering and renewal at least every seven days; this implementation renews daily.
- [Gmail `users.history.list`](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) — confirms paginated history, `labelId`, and that stale history cursors can return 404 and require a full sync.
