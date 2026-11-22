# Google Alerts Gmail — user data guide

This guide describes the personal Google Alerts connection in Job Beeper. The feature is not available until the server-side live-access gate is enabled after the Google policy and deployment gates are resolved.

## What is accessed

Job Beeper is configured to process messages carrying the Gmail label `JobBeeper/GoogleAlerts`. The owner creates and maintains that label and filter in Gmail; Job Beeper does not edit them. The backend checks message metadata and sender authentication before it fetches an eligible message body.

The message body is parsed in memory to extract destination links. Raw email bodies, email snippets, alert search queries, subjects and sender addresses are not saved by the Gmail processing path. A one-way message-key digest and queue/sync status metadata are retained for deduplication and recovery.

## What is stored in Job Beeper

Job Beeper follows each extracted destination link, fetches the destination page, verifies that it is a public job posting, and stores public posting fields as a private discovery under the owner account. These records can be matched against the owner's Job Beeper preferences and displayed in the dashboard. Gmail-origin associations and a backfill marker support idempotency and notification handling.

Google's policy classification of data derived through this flow, including the public-page fields linked to Gmail-derived destinations and the retained message-key digest, is still awaiting confirmation. The feature must not be enabled while that classification and any required storage controls remain unresolved.

## Consent record

When the owner accepts the pre-connect notice, Job Beeper stores a consent record containing the Job Beeper account ID, disclosure version, acceptance timestamp and a 10-minute expiry. The OAuth-start endpoint requires an unused, unexpired acceptance for the current disclosure version and consumes it once, so a direct or replayed connect request cannot bypass the notice. An abandoned consent expires automatically; the owner must accept again to start a later OAuth attempt. The server marks expired attempts with an expiry timestamp, retains them for audit, and excludes them from the pending-consent uniqueness constraint so they cannot block a fresh acceptance. The record is retained after Gmail disconnect as evidence of the acceptance and is removed when the Job Beeper account is deleted. It contains no Gmail message content, mailbox address, Gmail message ID or token.

## Telegram notifications

Gmail connection does not itself enable Telegram delivery. Job Beeper uses the separate per-user notification setting and linked private Telegram chat. When enabled, eligible job details and public posting links may be delivered to that chat. Telegram is a separate service; the user must clearly opt in after seeing the applicable data-use disclosure.

## Manage or delete the connection

The Account screen provides Gmail status and a disconnect action. Disconnect attempts to revoke the Google grant, clears stored access-token cache, deletes the Gmail credential, OAuth/sync state, push/message queue metadata and Gmail-to-opportunity associations, removes Gmail-only private job rows and related user evaluation/application rows, and cancels pending Gmail historical notification deliveries. Pending member-notification rows tied to Gmail-only private jobs are removed by the job-deletion foreign-key cascade. Historical backfill deliveries attached to independently stored public ATS jobs are marked cancelled; those public job records remain. Revocation can fail if Google's endpoint is unavailable; local deletion still proceeds.

Public job records already present independently of the Gmail-only private source are retained. Minimal notification-ledger history for public-job backfill cancellations may remain. A Telegram send already in progress when disconnect occurs can still complete, and messages already sent cannot be recalled by Job Beeper. To stop future Telegram messages before disconnect, turn off the separate Job Beeper Telegram notifications setting and unlink the Telegram chat as needed.

## Before enabling the feature

The owner must review and affirmatively accept the visible pre-connect disclosure. The server records the disclosure version and acceptance timestamp and requires a fresh one-time acceptance for each OAuth start. This technical safeguard does not constitute Google's approval. The Gmail use-case eligibility, server-side Restricted-scope assessment/CASA requirements, treatment of derived data, encryption-at-rest requirements and public privacy/help publication remain release gates. Do not connect a real mailbox until those gates are explicitly resolved.
