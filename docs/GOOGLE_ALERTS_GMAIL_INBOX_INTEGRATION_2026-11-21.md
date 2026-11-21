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

Focused test module `v2/test_google_alerts_email.py` was added with eleven synthetic tests covering multi-result structured HTML, canonical duplicate collapse, HTML and plain-text fallbacks, sender/subject rejection, invalid redirect handling raw-size limits and rejection (rather than silent truncation) when a message exceeds the per-email result cap. The test file has **not yet been executed** in an isolated project checkout; treat it as added but unverified until the no-cost local test run is completed.


Use Gmail API read-only access with a durable, scheduled incremental history poll. Do not introduce Pub/Sub, a public webhook, Cloudflare, a custom domain, or Gmail watch registration in the first MVP.

### 2.1 Separate owner-only authorization

The existing `v2/google_oauth.py` flow is for member sign-in and requests only `openid email profile`. Keep it unchanged.

Implement a separate Gmail connection with its own:

- OAuth client configuration/environment variables;
- authorization state, PKCE verifier and callback path;
- owner/admin-only connect and disconnect controls;
- token storage, encryption key and refresh handling;
- connection status and account identity checks.

Request only `https://www.googleapis.com/auth/gmail.readonly` if and only if Google confirms the use case is permitted. Do not request `gmail.modify`, `mail.google.com`, or other broader scopes. Reading full message bodies is necessary for parsing, and the Gmail API's `messages.get` full format is not available with `gmail.metadata`; metadata-only access cannot implement the required parser.

Never add Gmail scopes to ordinary member sign-in. Never expose owner OAuth start/callback/status/refresh-token data to ordinary member accounts.

### 2.2 Inbox filtering

The preferred setup is a narrow Gmail label (for example, `JobBeeper/GoogleAlerts`) applied by an owner-created Gmail filter to incoming Google Alerts messages. JobBeeper can list the existing label and use its label ID as the Gmail history filter.

Creating the label/filter through the Gmail UI is optional for the implementation: an initial version can filter inbox additions and inspect headers to match the verified Google Alerts sender/subject. Do not assume a sender address or message layout until a representative email fixture is reviewed.

A Gmail label is a processing filter, not an OAuth security boundary. The `gmail.readonly` scope still grants broad read access to the mailbox. The code must fetch only new candidate messages and must not scan unrelated mail bodies.

### 2.3 Incremental polling and checkpoint recovery

A local JobBeeper worker will poll the Gmail API using `users.history.list` and a durable `startHistoryId` checkpoint:

1. On first connection, establish a baseline history ID from the authenticated mailbox. By default, do not backfill old mail; begin processing messages arriving after connection. Any historical backfill requires a separate, explicit owner decision and a bounded date window.
2. Poll `history.list` on a conservative interval through the existing service runtime, optionally filtering by the dedicated label ID. Use `historyTypes=messageAdded` and page through all results.
3. Collect unique message IDs from the `messagesAdded` records. Stage those IDs durably before advancing the committed history cursor.
4. Read only message headers first when necessary; discard messages that do not match the confirmed Google Alerts sender/subject pattern without downloading their bodies.
5. Fetch the full MIME payload for matching messages, parse the email in memory, and enqueue every result item independently.
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

A sanitized real Google Alerts email is required to establish the exact sender, subject, MIME nesting, HTML card markup, tracking-link shape and multi-item layout. Do not claim the parser is validated until it passes that fixture and synthetic edge cases.

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

1. Obtain one sanitized representative Google Alerts `.eml` sample that contains at least two result items. Preserve MIME boundaries, HTML structure, sender/subject pattern and public destination-link structure; remove the owner's mailbox address, personal tracking identifiers and sensitive message metadata.
2. Build parser tests for HTML-only, plain-text-only, multipart/alternative, nested MIME, encoded text, multiple result cards, missing href, malformed card, duplicate links, Google redirect URLs and unrelated email.
3. Build Gmail API client tests with mocked HTTP responses for OAuth state/PKCE, token refresh, profile lookup, history pagination, message-added extraction, unrelated-sender filtering, duplicate message IDs, checkpoint atomicity, 429/5xx backoff, 401 refresh, revoked authorization, and history 404 recovery.
4. Verify one result item per card enters the existing verified-job pipeline. Verify two emails with different Alert searches that contain the same URL produce one canonical job while retaining only policy-compliant minimal provenance.
5. Run the focused Google Alerts Gmail tests and full V2 regression suite in a fresh non-production virtual environment. Record exact Python version, dependency versions, test count and commit SHA.
6. Measure poll duration and Gmail API quota usage using one owner mailbox and synthetic/local fixtures. Only enable a conservative recurring polling interval after approval and isolated end-to-end validation.
7. Complete Google permitted-use-case review, OAuth verification/security assessment requirements, privacy/data-retention controls and the separate production release checklist before connecting the real mailbox or deploying.

## 6. Owner input required

No credentials, OAuth secrets, Gmail password, app password, refresh token, or access token should be sent in chat.

Before parser implementation, the owner should provide one sanitized Google Alerts email as an `.eml` attachment (or a complete sanitized MIME source file) with multiple results. It is not necessary to provide all search strings, all alert emails, RSS URLs, or credentials.

Before production OAuth work, the product owner must resolve Google's Gmail permitted-use-case question. We will not enable a live connection without that gate. If the owner wants historical alerts processed on first connection, that should be decided separately; the safe default is new emails only.

## 7. Official references reviewed on 21 November 2026

- [Gmail API users.history.list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list) — incremental mailbox history, optional label filter, pagination, history cursor and HTTP 404/full-sync recovery.
- [Synchronize clients with Gmail](https://developers.google.com/workspace/gmail/api/guides/sync) — full sync, partial sync and history expiration.
- [Gmail API users.messages.get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get) — full message retrieval.
- [Gmail API message format reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/Format) — full/raw vs metadata-only behavior.
- [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) — `gmail.readonly` scope classification.
- [Google Workspace user data and developer policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy) — approved Gmail use cases, Limited Use, data transfer and security requirements.
- [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) — verification exceptions and server-side restricted-data security-assessment requirements.
- [Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push) — optional future low-latency Pub/Sub trigger; not required by the polling MVP.

