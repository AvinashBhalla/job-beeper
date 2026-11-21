# Google Alerts Gmail Inbox Integration

**Date:** 21 November 2026  
**Repository:** `AvinashBhalla/job-beeper`  
**Target branch:** `v2-live-radar`  
**Planning branch:** `feat/google-alerts-gmail-ingestion`  
**Status:** Owner-confirmed product direction; design and policy gates documented; no Gmail access or production changes

## 1. Corrected owner requirement — authoritative

The owner has multiple Google Alerts rules. Each rule uses a different search string to broaden job discovery. Google sends the resulting alert messages to one existing owner-controlled Gmail inbox.

The messages have the same Google Alerts email structure. Their content differs because each Alert uses a different search string. One email may contain multiple matching items, and each item must be extracted and processed independently.

JobBeeper must:

- Read the owner's existing Gmail inbox directly; no manual forwarding is required.
- Connect exactly one owner-controlled mailbox through a dedicated owner-only OAuth authorization.
- Detect Google Alerts emails and parse every result item from each message.
- Treat all alert emails as the same format; do not build one parser or feed per search string.
- Verify each destination posting, deduplicate repeated postings across alerts and send valid job records through the existing V2 shared ingestion path.
- Evaluate each stored job independently against member preferences. Members do not connect Gmail and must not see the owner's mailbox, raw messages, alert queries or mailbox metadata.

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

Focused test module `v2/test_google_alerts_email.py` was added with twelve synthetic tests covering multi-result structured HTML, canonical duplicate collapse, HTML and plain-text fallbacks, sender/subject rejection, invalid redirect handling raw-size limits and rejection (rather than silent truncation) when a message exceeds the per-email result cap. The test file has **not yet been executed** in an isolated project checkout; treat it as added but unverified until the no-cost local test run is completed.


Use Gmail API read-only access with a durable, scheduled incremental history poll. Do not introduce Pub/Sub, a public webhook, Cloudflare, a custom domain, or Gmail watch registration in the first MVP.

### 2.1 Separate owner-only authorization

The existing `v2/google_oauth.py` flow is for member sign-in and requests only `openid email profile`. Keep it unchanged.

Implement a separate Gmail connection with its own:

- OAuth client configuration/environment variables;
- authorization state, PKCE verifier and callback path;
- owner/admin-only connect and disconnect controls;
- token storage, encryption key and refresh handling;
- connection status and account identity checks.

Request only `https://www.googleapis.com/auth/gmail.readonly` if and only if Google confirms the use case is permitted. Do not request `gmail.modify`, `mail.google.com`, `gmail.labels`, or other additional/broader scopes. `gmail.readonly` permits listing labels and reading message metadata/bodies, which is enough to discover the pre-created label and read only its messages. Do not create or modify labels/filters through the API; the owner configures them in Gmail. Reading full message bodies is necessary for parsing, and the Gmail API's `messages.get` full format is not available with `gmail.metadata`; metadata-only access cannot implement the required parser.

**Owner consent recorded (21 November 2026):** the owner expressly agrees to a separate JobBeeper owner-only Gmail connection, with the application restricted operationally to Google Alerts messages. This is consent to the planned access, not evidence of Google's approval for the multi-member product use case; it does not close the policy gate in Section 3.

Never add Gmail scopes to ordinary member sign-in. Never expose owner OAuth start/callback/status/refresh-token data to ordinary member accounts.

### 2.2 Inbox filtering

**Required owner setup:** create a Gmail user label named `JobBeeper/GoogleAlerts` and a Gmail filter that adds this label to matching Google Alerts messages. Use sender `googlealerts-noreply@google.com` and subject phrase `"Google Alert -"` as candidate filter criteria. In Gmail's filter UI, select **Apply the label: JobBeeper/GoogleAlerts** and **Also apply filter to matching conversations** so existing matching messages are labelled for the full historical backfill as well as future arrivals. Review the matching set in Gmail before applying. Do not include Spam or Trash.

JobBeeper will use read-only `users.labels.list` to resolve the exact label ID, then use `users.messages.list(labelIds=[label_id], includeSpamTrash=false)` for the initial backfill and `users.history.list(labelId=label_id)` for incremental synchronization. Follow all page tokens. Do not use an unlabelled mailbox-wide message list or a broader Gmail search in the application. The application must still validate every candidate's exact sender, subject prefix, and unambiguous Gmail authentication headers before requesting `format=raw`. The label is a selection filter, not an OAuth security boundary: `gmail.readonly` remains a Restricted scope with broad technical read capability. Therefore, enforce label-ID scoping in one shared Gmail client wrapper, add tests proving all list/history calls carry that label ID, and never fetch raw bodies for any unlabelled message.

Do not add the `gmail.labels` scope or programmatically create/change the Gmail filter. The owner does this once in Gmail UI; the app is read-only. Google documents that `messages.list` accepts `labelIds` and that `history.list` accepts `labelId`, both with pagination.

### 2.3 Incremental polling and checkpoint recovery

A local JobBeeper worker will poll the Gmail API using `users.history.list` and a durable `startHistoryId` checkpoint:

1. **Owner-confirmed initial sync: backfill all available Google Alerts emails.** On the first approved owner connection, call `users.getProfile` and persist its returned `historyId` as the initial-sync baseline **before** starting the historical scan. Enumerate the mailbox with `users.messages.list(labelIds=[label_id], includeSpamTrash=false)`. Do not use a mailbox-wide list or `q` query; the dedicated label is the sole API selection boundary. The owner-created filter should have applied the label to all matching historical messages and all future arrivals. Follow every `nextPageToken` until no next page remains; use up to 500 IDs per page and do not impose a date cutoff or recent-window limit. This retrieves labelled messages across Inbox and archived/All Mail locations; Spam and Trash remain excluded by default. Gmail's [messages.list reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list) documents the `q` filter, page token and 500-message maximum; [the list guide](https://developers.google.com/workspace/gmail/api/guides/list-messages) confirms that list results contain message IDs/thread IDs and must be expanded with `messages.get`. The `q` parameter is not available with `gmail.metadata`, so this design remains conditional on approval for the Restricted `gmail.readonly` scope.
   - Persist each discovered message ID and page/progress state before moving to the next page, so an interrupted backfill resumes rather than restarting or skipping pages.
   - Stage all matching candidates through the metadata-only preflight below; fetch `format=raw` only after sender, subject and Authentication-Results pass. Parse in memory and enqueue each result independently.
   - Once the full enumeration has been staged, call `users.history.list` from the pre-scan baseline, page through the entire history response, and durably stage all message-added IDs found during the backfill. This closes the race for new Alerts arriving while the full mailbox scan is running. Only after every history page and discovered ID is safely staged should the worker commit the latest returned history cursor and switch to ordinary incremental polling.
   - The backfill is idempotent across retries and repeated discoveries: the message-processing ledger and canonical destination dedupe prevent duplicate processing/jobs. Do not declare the initial sync complete while an ID is still pending or retryable.
2. Poll `history.list` on a conservative interval through the existing service runtime with the required `labelId=label_id` filter. Use `historyTypes=messageAdded,labelAdded` and page through all results.
3. Collect unique message IDs from `messagesAdded` records and `labelsAdded` records that add the dedicated label. Stage those IDs durably before advancing the committed history cursor.
4. Read only message headers first: request `messages.get(format=metadata)` with `From`, `Subject` and `Authentication-Results` in `metadataHeaders`. Discard messages that do not match the confirmed Google Alerts sender/subject and Gmail authentication pattern without downloading their bodies.
5. For matching messages only, request `messages.get(format=raw)`, base64url-decode the RFC 5322 payload and parse it in memory. Use the Gmail message resource's `internalDate` for mailbox-arrival ordering and recovery windows; the RFC `Date` header is retained only as optional display metadata. Enqueue every result item independently.
6. Commit the new Gmail history cursor only after every page and every discovered message ID has been safely staged. Repeated notifications or poll retries must be idempotent.
7. If Gmail returns HTTP 404 because the checkpoint is no longer valid, run a bounded full resynchronization using the last successful poll time plus an overlap window, deduplicate against the processing ledger, then establish a new checkpoint. Record the recovery event and do not silently skip the gap.

The same local poller runs regardless of whether GitHub Actions is available. GitHub Actions are not a runtime dependency, and no paid hosted runner is required.

**Why polling, not Pub/Sub for the first release:** Gmail documents both full and partial synchronization. Partial sync uses `history.list`; a cursor may expire and return HTTP 404, in which case full sync is required. Gmail push notifications can later trigger the same partial sync if lower latency is justified, but require a Pub/Sub topic and a renewable `users.watch` registration. The existing production IP endpoint and Pub/Sub route do not need to be involved in this polling MVP.

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

### 2.5 Shared job verification and ingestion

For each extracted result:

1. Normalize and canonicalize the destination URL.
2. Collapse duplicate destinations found in the same email, across different alert emails, or across different alert search strings.
3. Fetch the public job posting through the reviewed safe-fetch implementation. Do not bypass 403/429, robots denial, login walls, CAPTCHAs or other access controls.
4. Prefer structured `JobPosting` evidence and validate required fields such as title and employer. Route uncertain pages to review rather than inventing a job.
5. Normalize verified records through existing V2 `normalize_job()` and store them with existing `upsert_jobs()`.
6. Reuse existing canonical opportunity linking and per-member preference evaluations. Keep notifications separate and do not enable Telegram as part of this integration.

Do not store raw email bodies, whole MIME payloads, attachments, unrelated message headers, or Gmail snippets in the jobs database. The Gmail message processing ledger should retain only the minimum identifiers/checkpoints/status needed for idempotency, under a documented retention policy. Fetch public posting details from the public destination rather than treating the email itself as the durable source of job content.

## 3. Google policy and security gate — blocking for production

This feature needs a policy decision before any production OAuth grant.

- `gmail.readonly` is a **Restricted** Gmail scope because it permits reading message bodies and metadata.
- Google's current policy lists approved Gmail use cases such as email clients, email backup, productivity improvements to the email experience, and reporting/monitoring services that improve the email experience. A shared job-discovery product that turns an owner's Google Alerts emails into opportunities for multiple JobBeeper members is **not clearly established as an approved use case** by the published examples.
- Owner consent alone does not establish that the product use is permitted. The product's data flow from the owner's mailbox into shared member-visible records must be described accurately and reviewed against the Limited Use requirements.
- Do not request `gmail.readonly`, initiate live OAuth consent, store a refresh token, or enable production polling until the permitted-use-case question and data-transfer/retention rules are resolved with Google.
- Restricted-scope data accessed through a third-party server may require OAuth verification and an annual third-party security assessment. Exceptions exist for personal, development/testing, internal and other specific cases, but JobBeeper's multi-member product must not assume that a personal-use exception applies.
- The production application will need visible disclosure, a privacy policy, a user-help/deletion process, encrypted tokens and data at rest, key management, least-privilege access, access logging and a documented incident-response path before any restricted-scope production review.

If Google does not approve this use case, stop the Gmail API route. Do not try to circumvent the restriction with IMAP, app passwords, forwarding, another Google account, or another API surface without an independent policy review.

### Data-minimization requirements if approved

- Store access/refresh tokens encrypted at rest; protect the encryption key separately from the database. Never log, print, commit or place tokens in the browser.
- Keep the owner mailbox connection separate from member authentication and authorization.
- Fetch message bodies only after sender/label validation; parse in memory and discard raw content.
- Persist only a short-lived deduplication ledger and the minimum durable history cursor/checkpoint required to synchronize.
- Do not use Gmail content to train or fine-tune models.
- Do not expose alert query text, raw messages, inbox metadata or links that reveal the owner's account.
- Keep public job-page data sourced and re-fetched from the public destination; do not permanently copy email content into the shared jobs store.
- Provide a clear disconnect/revoke path and deletion of stored tokens/checkpoints/processing metadata.

## 4. Current code baseline and boundaries

- Existing member OAuth: `v2/google_oauth.py`, `v2/test_google_oauth.py`; member sign-in scope remains `openid email profile`.
- Existing V2 ingestion: reuse `normalize_job()`, `upsert_jobs()`, canonical opportunity linking and member preference evaluation in `v2/radar.py`.
- The previous RSS work is in PR #101 / branch `feat/google-alerts-rss-atom-parser`. It is a superseded proof of concept and must not be merged or deployed as the requested email integration. Keep it closed/draft for history only.
- The incorrect Cloudflare Email Routing branch remains quarantined and must not be merged or cherry-picked.
- The production target recorded by the current handover is the Oracle VM `job-radar`, origin `https://130.210.27.197/`, with FastAPI behind Nginx. Do not change production, DNS, certificates, Nginx, OAuth, GCP resources or the database during design/fixture work.
- Build and test on a fresh isolated, non-production checkout and database. The only currently connected Terminal Commands machine is the production `job-radar` VM; do not use it for development testing.
- Do not trigger GitHub Actions or spend money on hosted CI. Run local tests in a dedicated non-production environment.

## 5. Validation plan

1. Owner creates the `JobBeeper/GoogleAlerts` label and Gmail filter, applies it to all existing matching conversations and verifies that future Google Alerts are labelled. Record the resolved label ID at connection time; do not store mailbox contents.
2. Build parser tests for HTML-only, plain-text-only, multipart/alternative, nested MIME, encoded text, multiple result cards, missing href, malformed card, duplicate links, Google redirect URLs and unrelated email.
3. Build Gmail API client tests with mocked HTTP responses for OAuth state/PKCE, token refresh, profile lookup, history pagination, message-added extraction, unrelated-sender filtering, duplicate message IDs, checkpoint atomicity, 429/5xx backoff, 401 refresh, revoked authorization, and history 404 recovery.
4. Verify one result item per card enters the existing verified-job pipeline. Verify two emails with different Alert searches that contain the same URL produce one canonical job while retaining only policy-compliant minimal provenance.
5. Run the focused Google Alerts Gmail tests and full V2 regression suite in a fresh non-production virtual environment. Record exact Python version, dependency versions, test count and commit SHA.
6. Measure poll duration and Gmail API quota usage using one owner mailbox and synthetic/local fixtures. Only enable a conservative recurring polling interval after approval and isolated end-to-end validation.
7. Complete Google permitted-use-case review, OAuth verification/security assessment requirements, privacy/data-retention controls and the separate production release checklist before connecting the real mailbox or deploying.

## 6. Owner input required

No credentials, OAuth secrets, Gmail password, app password, refresh token, or access token should be sent in chat.

The owner has supplied a representative Google Alerts `.eml` with multiple results and expressly consented to the owner-only Gmail connection for Google Alerts messages. No further sample is currently required for the parser foundation. The raw fixture must remain outside GitHub and must not be copied into logs or durable application storage.

The owner explicitly decided on 21 November 2026 that the initial Gmail synchronization must backfill **all available Google Alerts emails** (no date cutoff or recent-window limit). The operational scope is only messages with the dedicated `JobBeeper/GoogleAlerts` label across Inbox and archived/All Mail; Spam and Trash remain excluded by default. The owner must apply the label to existing matches and set the Gmail filter to label future arrivals. The app will use `labelIds`/`labelId` on every list/history operation and metadata-first validation before body retrieval. The full-backfill procedure and race-free handoff to incremental history polling are specified in Section 2.3.

Before production OAuth work, the product owner must resolve Google's Gmail permitted-use-case question.

**Policy-status clarification:** the owner has confirmed personal consent and the intended mailbox boundary. This does not, by itself, establish that Google has approved the product's multi-member job-discovery use case under the Workspace User Data policy. Do not initiate live OAuth or retain tokens until the owner supplies the applicable Google approval/verification status or the use case is otherwise cleared through Google's official review process. We will not enable a live connection, request consent or store a refresh token without that gate. No Gmail credentials, OAuth secrets, passwords, access tokens or refresh tokens should be sent in chat.

## 7. Official references reviewed on 21 November 2026

- [Gmail API users.history.list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) — incremental mailbox history, optional label filter, pagination, history cursor and HTTP 404/full-sync recovery.
- [Synchronize clients with Gmail](https://developers.google.com/workspace/gmail/api/guides/sync) — full sync, partial sync and history expiration.
- [Gmail API users.messages.get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get) — full message retrieval.
- [Gmail API message format reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/Format) — full/raw vs metadata-only behavior.
- [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) — `gmail.readonly` scope classification.
- [Google Workspace user data and developer policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy) — approved Gmail use cases, Limited Use, data transfer and security requirements.
- [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) — verification exceptions and server-side restricted-data security-assessment requirements.
- [Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push) — optional future low-latency Pub/Sub trigger; not required by the polling MVP.

