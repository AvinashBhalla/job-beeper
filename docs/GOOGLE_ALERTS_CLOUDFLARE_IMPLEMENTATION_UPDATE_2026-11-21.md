# Google Alerts Discovery Engine — Cloudflare ingress implementation update

**Date:** 21 November 2026  
**Branch:** feat/google-alerts-email-routing  
**Decision:** Preferred implementation architecture, pending Cloudflare zone-access and sample-email preflight.

This update supersedes the original Gmail API plus Google Cloud Pub/Sub ingress in the initial plan. Do not implement both paths in parallel.

## 1. Why the design is changing

The original design used Gmail API gmail.readonly and users.watch. That scope is restricted, grants broad mailbox read access, and requires a Google policy/verification assessment. It is not a good default for an owner mailbox feeding a multi-member job-discovery service.

The owner's requirement is event-driven processing of new Google Alert email, not necessarily Gmail API access. Gmail can selectively forward only messages that match a filter. Cloudflare Email Routing can invoke a Worker for inbound messages. This achieves event-driven receipt without JobBeeper signing in to Gmail or requesting Gmail restricted scopes.

## 2. Preferred event path

1. The owner creates a dedicated inbound address on a dedicated subdomain, proposed as google-alerts@alerts-in.jobbeeper.com. This requires confirmation that the owner has access to the Cloudflare account managing jobbeeper.com.
2. Cloudflare Email Routing sends that address to a dedicated Email Worker. Use a separate subdomain so existing apex-domain MX and mail configuration are not changed.
3. The owner adds the Cloudflare address as a Gmail forwarding destination and completes Google's email verification.
4. The owner creates a Gmail filter matching only Google Alerts messages. The filter applies the JobBeeper/GoogleAlerts label and forwards matching new messages to the dedicated Cloudflare address. Disable general forwarding; keep Gmail's copy in the Inbox.
5. The Email Worker validates sender and recipient, parses the raw MIME message using a maintained MIME parser, extracts message metadata and result anchors, and enqueues a compact JSON event. It does not log or enqueue full raw email bodies or attachments.
6. A Cloudflare Queue consumer sends the event to the JobBeeper public HTTPS endpoint using HMAC-SHA256 over the exact request bytes and a timestamp.
7. The JobBeeper webhook verifies the signature, timestamp, recipient, sender, schema and body size; then stores the message and URL candidates in a durable SQLite inbox/processing queue in one transaction before returning success.
8. A backend worker resolves and validates the destination URLs, fetches permitted public pages under per-host budgets, extracts actual job postings, and upserts verified observations as source google_alerts.
9. Existing canonical linking and per-user evaluation remain the shared downstream pipeline. The existing upsert_jobs() function already refreshes configured user evaluations for affected job IDs, so do not duplicate this logic in the new source.

## 3. Important mail-routing details

- Gmail selective forwarding requires the destination address to be verified. The owner can retain the original Gmail copy in the Inbox.
- Filter forwarding is selective; do not enable all-mail forwarding.
- The Cloudflare address must be configured under a dedicated inbound subdomain, not by modifying existing apex MX records.
- Cloudflare Email Routing supports Worker destinations with an email() handler. The Worker can access envelope sender/recipient, headers and raw MIME bytes.
- Cloudflare Email Routing can be enabled for subdomains under the existing zone. Verify the exact setup in the owner's dashboard before creating records or changing routing.
- If the Gmail verification message reaches the Worker, use a tightly scoped temporary verification mode that forwards only that verification message to the owner's verified Gmail address. Disable it immediately after verification. Never create a general forward loop.
- The sender address and Alert subject/body structure must be confirmed from a representative redacted Google Alert email before enabling a production filter.

## 4. Reliability and security

- The Worker must validate the envelope recipient and sender allowlist before parsing. It must not trust a subject line as proof of a Google Alert.
- Parse MIME correctly, ignore attachments, cap raw message size and extracted result count, and queue compact fields only.
- Queue delivery is at-least-once. Deduplicate by original Message-ID when preserved; otherwise use a stable SHA-256 fingerprint of normalized headers and parsed content. Also deduplicate every result URL after safe normalization.
- Cloudflare Queues has a 128 KB message-size limit. Workers Free currently includes 10,000 operations/day and 24-hour message retention. The queue is a short-lived transport, not the durable database. Persist accepted messages and links into JobBeeper promptly and monitor queue age/dead letters.
- Configure bounded retries and a dead-letter queue. A queue consumer should retry transient webhook failures; a permanent HMAC/schema rejection must be observable and not silently discarded.
- HMAC request signature: timestamp plus exact serialized request bytes, signed with HMAC-SHA256 using a dedicated secret shared between the Worker and JobBeeper. Backend checks constant-time equality and a short timestamp window. The secret lives in Cloudflare secrets and the backend runtime environment only.
- Never log raw email, full snippets, credentials, HMAC secret, or private mailbox metadata. Use hashed event identifiers in operational logs.
- URL fetches require SSRF protections: HTTPS by default, block local/private/link-local/reserved addresses, validate every redirect hop, bound redirects/body/timeouts, enforce per-host concurrency and honor 429 Retry-After. No proxy or CAPTCHA/rate-limit bypass.
- Do not auto-activate ATS boards when a Google Alert happens to point to a careers home page. Direct posting pages can become job observations; company/career-board roots should be staged for review.

## 5. Cloudflare cost and limits

Cloudflare Email Routing supports routing to a Worker. Cloudflare Queues is available on Workers Free with 10,000 operations/day included, but a message incurs write/read/delete operations, the queue payload limit is 128 KB, and Free-plan retention is 24 hours. This is expected to be sufficient for a low-volume 98-rule feed if the event payloads are compact, but actual usage and account limits must be monitored. Do not upgrade or add paid services without the owner's explicit approval.

## 6. Implementation packages and revised estimate

**Estimated engineering effort: 5–7 focused working days** after access and sample-email preflight. This is an estimate, not a delivery guarantee.

| Package | Estimate |
|---|---:|
| Cloudflare Worker email handler, MIME parser and validation | 1 day |
| Queue, retry/DLQ, signed HTTP consumer and deploy configuration | 0.5–1 day |
| Backend HMAC webhook, durable inbox/result schema and idempotency | 1–1.5 days |
| Result extraction, rule mapping and parser fixtures | 0.5–1 day |
| URL safety, destination fetch, verification and per-host throttling | 1–1.5 days |
| Shared DB upsert, canonical dedupe, admin metrics and member evaluation | 0.5 day |
| QA, pilot and release readiness | 0.5–1 day |
| **Total** | **5–7 working days** |

A 1–2 day proof-of-flow can demonstrate filtered Gmail forwarding, Cloudflare email receipt, queueing and signed backend acceptance. It is not production readiness.

## 7. Acceptance gates

### Preflight
- Confirm owner controls Cloudflare account/zone for jobbeeper.com.
- Confirm no existing mail routing is using the proposed subdomain.
- Inspect a redacted representative Google Alert message, including sender, subject and link structure.
- Confirm the Gmail destination verification and filter can be configured without changing existing mail delivery.
- Confirm the correct public HTTPS API origin. The production acceptance audit on 20 November did not establish the member browser-to-VM API/database mapping.

### Pilot
- Test one forwarded email and duplicate delivery.
- Test invalid sender/recipient, malformed MIME, oversized email, invalid HMAC, stale timestamp, queue retry and dead-letter handling.
- Test result extraction with representative Alert types from 5–10 rules.
- Test redirect resolution, SSRF rejection, 403/429 cooldown and expired/irrelevant posting states.
- Test duplicate URLs across multiple alerts and ATS sources merge into one canonical opportunity.
- Confirm the owner's alert queries/mailbox identifiers are not exposed to members.
- Run a silent historical/backfill pilot without Telegram notification flood.

### Production
- Enable all 98 rules only after pilot extraction precision and recall are reviewed.
- Verify queue health, webhook success, duplicate suppression, retry/DLQ metrics and durable backend inbox.
- Verify each member sees only opportunities matching their own preferences.
- Keep Telegram delivery separate until the per-user notification path passes production acceptance.
- Roll out with a rollback plan. No changes to ATS allowlist, existing cooldowns or the intentionally paused Naukri relay.

## 8. Current state and immediate next dependency

### Implemented on the isolated feature branch

- Branch: feat/google-alerts-email-routing.
- v2/google_alert_ingest.py: HMAC-SHA256 verification, strict event validation, public-URL syntax checks, SQLite inbox/result URL tables, global URL fingerprints and per-message URL observations.
- v2/radar.py: initializes the Google Alert intake schema and exposes POST /api/webhooks/google-alerts. The endpoint enforces HTTPS deployment expectation, JSON content type, a 96 KiB body bound, a five-minute timestamp window, constant-time HMAC validation, and durable persistence before success.
- v2/test_google_alert_ingest.py: 11 unittest cases covering HMAC, stale signatures, duplicate delivery, event-ID conflict, local/non-HTTP URL rejection, URL deduplication, URL count bounds, boolean schema versions, default ports and IPv6 literals.
- cloudflare/google-alerts-ingress: TypeScript Email Worker using postal-mime; sender/recipient allowlist; candidate anchor extraction; compact, deterministic queue batches; HMAC-signed queue consumer; Wrangler and setup documentation.
- The existing v2 upsert_jobs() path is confirmed to refresh per-user evaluations for affected job IDs. The planned posting processor should hand verified jobs to this path rather than duplicate member-matching logic.

### Not yet completed / not yet proven

- Unit tests and TypeScript typecheck have not been executed. No safe non-production runner is currently connected; the connected machine is the live production VM, and it must not be used as a development/test runner.
- The Worker parser has not yet been validated against a real, redacted Google Alert message. Gmail filter-forwarding may alter MIME wrapping or sender headers; confirm this before enabling the filter.
- Destination URL fetching, redirect-by-redirect SSRF protection, job-page extraction/verification, URL retry leasing, Admin telemetry and a replayable fixture suite remain to be implemented.
- Cloudflare account/zone access to jobbeeper.com has not been confirmed. No Cloudflare resources, DNS records, queues, email routes, Gmail filters, forwarding rules, production settings or services have been changed.
- The webhook public host is not yet selected because the 20 November acceptance audit could not prove which API/database backs the member site. Do not put a guessed host in Wrangler configuration.
- No Gmail OAuth or Google Cloud Pub/Sub resources are required by the preferred path.

### Immediate preflight dependency

The owner must confirm Cloudflare dashboard access to the jobbeeper.com zone and provide one redacted representative Google Alert email (or its complete headers plus the rendered HTML/text body). Remove personal email addresses, tokens, tracking IDs and private content before sharing. Do not share authentication headers or mailbox credentials.

## 9. Documentation and reference sources

Initial plan: docs/GOOGLE_ALERTS_DISCOVERY_ENGINE_PLAN_2026-11-21.md

- Gmail filtered forwarding and verification: https://support.google.com/mail/answer/10957
- Cloudflare Email Worker API: https://developers.cloudflare.com/email-service/api/route-emails/email-handler/
- Cloudflare Email Routing rules: https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/
- Cloudflare Email Routing subdomains: https://developers.cloudflare.com/email-service/configuration/subdomains/
- Cloudflare Queues limits: https://developers.cloudflare.com/queues/platform/limits/
- Cloudflare Queues pricing: https://developers.cloudflare.com/queues/platform/pricing/

**No external resources or production settings have been changed.**
