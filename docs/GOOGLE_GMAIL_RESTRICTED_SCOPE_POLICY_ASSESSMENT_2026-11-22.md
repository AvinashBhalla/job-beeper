# Google Gmail Restricted-Scope Policy Assessment — 22 November 2026

**Status:** Technical-policy assessment; not legal advice or a CASA assessment. The owner separately reports Google approval for the exact single-owner workflow; this document is not the approval correspondence.
**Application:** JobBeeper personal Google Alerts → private job discovery
**Intended user count:** One account controlled by the owner
**Requested scope in code:** `https://www.googleapis.com/auth/gmail.readonly`
**Current live-access gate:** `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false`; no OAuth grant or mailbox request has been made.

**Owner approval update (22 November 2026):** The owner reports that Google approval has been received for the proposed one-owner personal Gmail workflow and has directed implementation/configuration to proceed. The approval correspondence is retained privately, not in this repository. For this narrowly scoped implementation, the approved-use-case question is recorded as resolved per the owner. Do not infer that the approval extends to additional accounts/scopes or waives any separate CASA/security, retention or data-handling conditions unless the correspondence expressly says so.

## Executive finding

Google's published OAuth policy clearly supports the *personal-use verification exception* for an app used only by its creator (or a few people personally known to them). That exception means the app does not need to submit the normal OAuth app verification request; it does **not** mean all Gmail API and Workspace data policies stop applying. The owner may still encounter Google's unverified-app consent warning.

The requested Gmail scope remains Restricted. Google's published Restricted Scope Verification page describes a separate security-assessment requirement for restricted user data accessed from or through a third-party server. The owner reports receiving Google approval for the complete intended personal workflow and says there is no issue with what is being implemented. The approval correspondence is not available in this repository, so preserve it privately and follow any specific CASA/security-assessment or retention conditions in that response. This assessment does not claim that a CASA assessment was performed.

The approved-use-case question is recorded as resolved per the owner's report of Google approval for this exact owner-only workflow on 22 November 2026. This report does not authorize broader Gmail features or additional users. Keep the implementation within the precise personal use case the owner submitted and retain the approval correspondence privately.

**Updated decision:** the owner reports Google approval for the exact single-owner workflow; proceed with configuration within that boundary. Keep live access disabled until the dedicated OAuth credentials, owner binding and encryption key are installed and the read-only preflight passes. Any separate CASA/security-assessment or retention conditions in the approval correspondence remain binding; do not assume a waiver beyond what Google actually approved.

## 1. What Google's current pages say

### 1.1 Personal-use OAuth verification exception

Google's Restricted Scope Verification page says an app used only by its creator, or by a few users all personally known to the creator, need not be submitted for the normal review. Google's OAuth 2.0 Policies page defines “personal use” for its production-app distinction as not shared with anyone else or used by fewer than 100 people, all personally known to the developer.

For JobBeeper's declared single-owner design this appears to fit the personal-use exception. It is an exception to submitting the normal verification review, not a general permission to use Gmail data for any purpose. Google notes that users may need to proceed through the unverified-app warning screen. Keep the client restricted to the owner; do not add members or public users to this OAuth client.

### 1.2 Restricted scope and server-side assessment

The Gmail API scope reference classifies `gmail.readonly` as Restricted and describes it as permission to view email messages and settings. The Restricted Scope Verification page says every app requesting restricted user data and able to access the data from or through a third-party server must go through a security assessment from a Google-empanelled assessor. It also states that access to verified restricted scopes requires renewed compliance and assessment at least every 12 months after the assessor's Letter of Assessment.

The application has a backend on the `job-radar` VM that exchanges the authorization code, stores an encrypted refresh token, calls Gmail API endpoints, and processes message content. This is not a browser-only local app. The conservative interpretation is that the server-side assessment requirement is relevant. A single personal user and localhost callback do not by themselves remove this question. Obtain Google's written determination about whether an owner-operated VM for this specific single-user app is covered.

Google's Workspace policy separately lists required Restricted Scope security measures, including encryption of user data at rest and in transit, encrypted OAuth tokens, appropriate key management, and CASA security best practices. The refresh token is encrypted in the current code; that alone is not proof of full CASA/security-assessment compliance.

### 1.3 Approved Gmail application types — owner reports approval received

Google's Workspace user data and developer policy lists these approved Gmail-scope use cases:

1. Built-in or web email clients that let users compose, send, read and process email through a UI.
2. Applications that automatically back up email.
3. Applications that enhance email productivity (examples include CRM, delayed sending, mail merge and generative-AI summaries).
4. User-benefiting reporting or monitoring applications that improve the email experience (examples include travel itineraries, flight tracking and package-delivery tracking).

JobBeeper is not an email client or mail-backup product. Its purpose is to turn the owner's Google Alerts into a private job-discovery workflow. The owner reports Google approved this precise personal workflow. Keep the approval correspondence private and preserve any conditions. Do not extrapolate that approval to member access, additional mailboxes, broader scopes, model training, or a different data flow.

### 1.4 Limited Use, derivative data and transfers

Google's Workspace policy says the Limited Use requirements apply to data derived from Sensitive and Restricted scopes. Data use must be limited to the approved user-facing feature; transfers are restricted except where necessary to provide/improve the approved user-facing feature and only with user consent, for security, or for legal compliance. The policy also prohibits selling user data, using it for advertising, and using it to train/generalize AI models beyond the specific user's personalized model for the appropriate feature. Google additionally warns against scraping, building databases from, or keeping permanent copies of Google user data.

This matters for the dashboard and Telegram paths. Any Gmail-derived information sent to Telegram must be limited to the user's feature, visible/prominent and covered by the user's clear affirmative consent. The notification toggle must remain separate from Gmail connection consent. Do not send mailbox identifiers, alert search queries, email snippets, raw message content, or other unnecessary Gmail content to Telegram. Do not use Gmail-derived content for generalized analytics, model training, advertising or resale.

### 1.5 Transparency, consent, help and deletion

Google's Workspace policy requires an in-product disclosure in normal use that explains the application identity, data accessed, why it is accessed, and how it is used or shared. The disclosure must accompany and immediately precede an affirmative consent action; it cannot be buried only in a privacy policy. The policy also requires user help documentation explaining how to manage and delete data. For public availability, the app must publish a privacy policy and configure the privacy-policy URL in the OAuth client.

Before live access, the Account screen therefore needs a clear pre-connect disclosure describing label-scoped Gmail reading, transient body parsing, public job-page fetching/verification, persistent private job records and matching, the separate Telegram opt-in/third-party transfer, retention and disconnect/deletion behavior. The user must take an affirmative action after seeing it. A user-facing data-management guide and a public privacy-policy URL must be ready before any public rollout. The technical handover docs alone should not be treated as the public privacy/help deliverable.

## 2. Code/data-flow findings from the feature checkout

The following describes the current isolated branch; it is not an endorsement that Google's policy accepts the use case.

- The OAuth request currently asks for `gmail.readonly` only. The code is label-scoped to `JobBeeper/GoogleAlerts`, checks message metadata and sender authentication before fetching a raw message, and parses the raw MIME in memory.
- `parse_google_alert_email` validates sender, subject and authentication results. It can transiently return result title, snippet and destination URL, but the Gmail worker passes each result to `_process_google_alert_candidate`, which uses only `destination_url`.
- `_process_google_alert_candidate` fetches and verifies the destination as a public HTTPS JobPosting. `record_google_alert_posting` persists public-page fields (title, company, location, public URL, public description/posting dates and public verification evidence) as a private owner-scoped job when no equivalent globally public job row already exists. It also stores an association between the owner and the canonical opportunity.
- Raw MIME, email body, alert query, subject, sender, and email snippet are not persisted by this processing path. After a Gmail message is processed, the raw Gmail message ID is cleared; a SHA-256 message-key digest and processing metadata remain for deduplication/status. That digest, message status, timestamps, and Gmail-origin association are still Gmail-derived operational metadata and should be included in the policy/data-retention review.
- JobBeeper can send matching job fields and public posting links to the owner's linked private Telegram chat through the separate user notification path. Delivery is controlled by the per-user notification setting and retains preferences, freshness, posting-verification and idempotency checks. Because Telegram is an external provider, the product must disclose this transfer and obtain the required user consent before sending.
- Disconnect attempts to revoke the Gmail grant where possible, clears the access-token cache, deletes Gmail credentials, sync state, OAuth state, Gmail message/hash queue metadata and owner-to-opportunity associations, removes Gmail-only private discoveries and related user evaluation/application rows, and cancels pending Gmail historical notification deliveries. Notification-ledger rows may remain as cancelled history; public job rows independently known from public sources are retained. The UI and help text should describe this distinction accurately.

**Important unresolved classification:** the current persistent job fields are fetched afresh from public job pages rather than copied from Gmail message bodies, but their discovery was initiated by a Gmail-derived destination link and the rows retain Gmail-source provenance. Google's policy explicitly covers data derived from Google scopes. Do not assume these public-page records or the message-key digest are outside the policy without Google's interpretation. Confirm whether these specific fields may be retained as public-source data, what retention applies to Gmail-derived metadata, and whether the existing SQLite storage must encrypt any of these fields at rest.

## 3. Required decisions before live Gmail activation

1. **Google use-case classification — owner reports approval received.** The owner reports Google approved this single-user workflow on 22 November 2026. Keep the approval correspondence privately and preserve its conditions. Do not expand the Gmail use case beyond the approved owner-only workflow.
2. **Follow any server-side assessment/security conditions in Google's approval.** The owner reports Google has approved the described workflow. No CASA assessment has been performed by this code change; do not claim otherwise or broaden the use beyond any conditions in the approval.
3. **Preserve the approved data-handling boundary.** Retain only the documented minimal sync metadata and independently fetched public posting fields; do not add raw email, snippets, alert queries or generalized analytics. Apply any retention/encryption restrictions stated in Google's approval.
4. **Complete in-product disclosure and consent.** Show the data accessed, transient parsing, public-page verification, private job-record persistence, separate Telegram transfer/opt-in, and deletion/retention behavior immediately before the Gmail connection action. Capture affirmative consent server-side for the current disclosure version and require a fresh one-time acceptance for every OAuth start; preserve a separate opt-in for Telegram. This implementation safeguard does not close Google's policy eligibility or assessment gates.
5. **Publish help/privacy content as required.** Provide an easy-to-find help page describing connection management, pause/resume, disconnect and deletion. Provide a privacy-policy URL if the app is made available publicly; explicitly disclose Google data access, purposes, storage, sharing with Telegram and deletion rules. Include the required Google Limited Use compliance statement.
6. **Close security controls.** Confirm CASA/security assessment applicability, encryption for all in-scope persisted data, key management, access control, secure transport, incident handling, deletion verification, and prompt-injection controls. The encrypted refresh token and local test suite are not a substitute for the assessment.

### Consent safeguard added — 22 November 2026

The Account notice now states that the owner accepts a versioned disclosure. The server records the Job Beeper user ID, disclosure version, acceptance timestamp and 10-minute expiry. The OAuth-start route atomically consumes one unused, unexpired acceptance and rejects direct, expired or replayed connect requests. Expired pending attempts are marked with `expired_at`, retained for audit, and excluded from the uniqueness constraint so a fresh acceptance can be recorded. Disconnect does not erase the record; it remains until the Job Beeper account is deleted. The record contains no Gmail data or credentials. This closes the client-only consent bypass but does not replace Google's eligibility, Limited Use or security-assessment determination.

## 4. Decision and activation gate

After the owner-reported approval, continue within the exact single-owner scope. Until private configuration and the read-only preflight are complete:

- Keep `JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS=false`.
- Do not connect an account, request/retain live Gmail tokens, read a real mailbox or start the poller.
- Do not provision Pub/Sub, billing, a domain or public callback infrastructure. The personal polling/localhost SSH tunnel avoids those infrastructure dependencies but does not change OAuth/Workspace policy requirements.
- Do not expand the OAuth client beyond the single known owner.

A branch commit/push and draft PR review can be performed separately from live activation; neither is authorization to connect Gmail or deploy production.

## 5. Official Google sources reviewed

Reviewed 22 November 2026; page update dates are shown where the page states them.

- [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification) — page last updated 10 November 2026. Personal-use verification exception, server-side security assessment, permitted application types and annual assessment.
- [Google Workspace user data and developer policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy) — page last updated 22 July 2026. Approved Gmail use cases, Limited Use (including derived data), permitted transfers, user consent, help documentation, security controls and database-copy restrictions.
- [Choose Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) — classifies `gmail.readonly` as Restricted and describes its access.
- [OAuth 2.0 Policies](https://developers.google.com/identity/protocols/oauth2/policies) — page last modified 5 August 2026. Personal-use definition, client and token handling.
- [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy) — transparency, minimum permissions, Limited Use and secure handling.

---
