> **QUARANTINED — DO NOT DEPLOY OR MERGE.** This worker scaffold was created after an incorrect assumption that the owner controls `jobbeeper.com`. The project's documented production origin is `https://130.210.27.197/` on VM `job-radar`; the repository does not establish owner control of `jobbeeper.com`. No Cloudflare zone, DNS, email routing or Gmail forwarding setup has been authorized. This branch is superseded; see [production-origin correction](../../docs/GOOGLE_ALERTS_PRODUCTION_ORIGIN_CORRECTION_2026-11-21.md) on `v2-live-radar`. Do not deploy, merge, cherry-pick or create resources from this scaffold.

# JobBeeper Google Alerts Email Worker

This Worker is the inbound email adapter for the owner-controlled Google Alerts mailbox. It does not connect to Gmail APIs. Gmail selectively forwards only Alert messages into a dedicated Cloudflare Email Routing address. The Worker parses MIME, validates the sender/recipient, extracts candidate links and writes compact events to Cloudflare Queues. The queue consumer signs each event and posts it to JobBeeper.

## Current status

Code scaffold only. Do not deploy or create Cloudflare resources until the owner confirms access to the Cloudflare zone for jobbeeper.com, the exact public JobBeeper API origin, and a redacted representative Alert email.

The proposed inbound address is google-alerts@alerts-in.jobbeeper.com. This is a proposal, not a configured address. Confirm the subdomain is available and not already used for mail before enabling it.

## Requirements

- Cloudflare account with the jobbeeper.com DNS zone and Email Routing enabled.
- A dedicated inbound subdomain, configured in Cloudflare Email Routing. Do not edit the apex MX records or existing mail routes.
- One Cloudflare Queue named job-beeper-google-alert-events and a dead-letter queue named job-beeper-google-alert-events-dlq.
- JobBeeper API deployed behind a public HTTPS origin that can reach the same database used by the member app.
- A generated random webhook secret of at least 32 characters. Store it as a Worker secret and in the JobBeeper runtime environment only.

## Local setup

Install dependencies in a development environment, not on the production VM:

    npm install
    npx wrangler queues create job-beeper-google-alert-events
    npx wrangler queues create job-beeper-google-alert-events-dlq

Set the exact public API origin only after the member API/database mapping is established:

    npx wrangler secret put JOB_BEEPER_WEBHOOK_SECRET
    npx wrangler secret put JOB_BEEPER_WEBHOOK_URL

The webhook URL must be the HTTPS origin followed by /api/webhooks/google-alerts. The webhook secret must match JOB_BEEPER_GOOGLE_ALERTS_WEBHOOK_SECRET in the JobBeeper runtime environment.

Set GOOGLE_ALERTS_ALLOWED_FROM to the verified RFC 5322 From address of Google Alerts after inspecting a real sample message. Do not guess or permit an unrestricted sender set. Set GOOGLE_ALERTS_INBOUND_TO to the exact Cloudflare inbound alias. These non-secret values are in wrangler.toml or Worker variables.

Run:

    npm run typecheck

The backend intake unit tests are in the repository's V2 unittest suite and can be run in a safe development checkout with:

    python -m unittest v2.test_google_alert_ingest

Do not run the application startup path or these tests against the production database.

Deployment is intentionally not included in automated scripts. Review the Cloudflare configuration and deploy manually only after the owner approves the exact resources and routing.

## Cloudflare Email Routing setup sequence

1. In the Cloudflare dashboard, confirm jobbeeper.com is in the owner's account.
2. Enable Email Routing only on a new dedicated subdomain such as alerts-in.jobbeeper.com. Review every proposed DNS record before accepting; do not change apex/root mail records.
3. Add the owner's existing Gmail address as a Cloudflare verified destination and complete Cloudflare's destination verification.
4. Temporarily route the proposed JobBeeper inbound alias to that already-verified Gmail destination. This makes it possible for Gmail's own forwarding-address verification email to be received.
5. In Gmail, add the inbound alias as a forwarding address and complete Google's verification link.
6. Change the Cloudflare route for the alias to this Email Worker. Confirm the Worker route is active.
7. In Gmail, create a filter matching only the confirmed Google Alerts sender and message format. Configure the filter to apply the JobBeeper/GoogleAlerts label and forward only those matching messages. Do not enable global forwarding.
8. Keep Gmail's original copy in the Inbox. Confirm the filter is scoped using Gmail's search preview before saving.

Do not activate the Gmail filter until Worker routing, backend webhook, queue consumer and a test email have all passed.

## Event and retry model

- One email can produce multiple compact event batches. Each batch has a deterministic event identifier derived from message metadata and its contained links.
- Queue delivery is at-least-once; the backend deduplicates by event ID and normalized URL fingerprint.
- The Worker does not fetch destination career pages. URL resolution, SSRF-safe fetch, host budgets, posting verification and shared job ingestion happen in the backend.
- The backend webhook persists the event and link observations to SQLite before returning 2xx. Queue delivery retries non-2xx responses and routes exhausted failures to the dead-letter queue.
- Free-plan Queue retention is 24 hours, and event size must remain below 128 KB. This Worker caps its own JSON event payload at 96 KB.
- The Worker logs status and error class only. Never log full email content, owner mailbox details or secrets.

## Privacy and scope

The owner retains the original email in Gmail. JobBeeper does not sign in to Gmail, read unrelated email, mark mail read, or change mailbox state. Members do not connect Gmail and never receive the owner's Alert queries or mailbox metadata.
