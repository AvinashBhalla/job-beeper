# Google Alerts — production-origin correction and implementation gate

**Date:** 21 November 2026  
**Applies to:** `v2-live-radar`, production acceptance and P0 Google Alerts Discovery Engine  
**Purpose:** Correct an invalid domain assumption introduced during the first implementation attempt.

## 1. Confirmed production environment from repository records

The authoritative `docs/PRODUCTION_ACCEPTANCE_2026-11-20.md` and current handover identify the project's production as:

- Browser/admin production origin: `https://130.210.27.197/`
- Host: Oracle Cloud Ubuntu VM `job-radar`
- Reverse proxy: host Nginx configured for `130.210.27.197`
- Application: FastAPI V2 listening internally on `127.0.0.1:8000`
- Container: `v2-radar-1`
- Production image: `job-radar-prod-release:dda6d57`
- Database: persistent SQLite on the production VM

The November 20 audit confirmed public-IP HTTPS `/health` returned HTTP 200 and that Nginx proxies to the local FastAPI listener.

**There is no evidence in the project handover that the owner controls `jobbeeper.com`, or any other custom domain for this deployment. Do not use `jobbeeper.com` as a JobBeeper-owned production domain, create Cloudflare Email Routing there, alter its MX records, or configure a custom-domain Worker route.** The November 20 browser-to-backend audit mentioned that hostname only as a separate member-facing site whose relationship to this VM and database was explicitly unresolved.

## 2. Invalid branch and changes to quarantine

The branch `feat/google-alerts-email-routing` was created using the unsupported assumption that the owner could configure Cloudflare on `jobbeeper.com`. It contains a Cloudflare Email Worker, Wrangler/Queue configuration, and a backend webhook/intake prototype.

- The branch is **not merged** into `v2-live-radar`.
- No pull request was opened.
- No Cloudflare resource, DNS record, Email Routing rule, Gmail filter, Gmail forwarding rule, production configuration, production service or production database was changed.
- The branch must be treated as **superseded / do not merge / do not deploy**. Its Worker config refers to a domain the owner has not said they control. It is not production-ready.
- Do not copy or cherry-pick the Cloudflare Worker or domain-specific configuration into the release branch.
- The backend HMAC/SQLite code on that branch is a prototype only. Review its design and tests independently before reusing any part.

## 3. Correct implementation target

The target webhook must be served by the documented production application, if its public HTTPS ingress meets the external provider's requirements:

`https://130.210.27.197/api/webhooks/google-pubsub` (proposed route; not yet implemented or verified).

The endpoint must be routed by the existing Nginx configuration to FastAPI on `127.0.0.1:8000`. It must not depend on `jobbeeper.com`, Cloudflare custom-domain routing, or a hostname that the project does not own.

The preferred original architecture to evaluate is:

1. Owner-controlled Gmail mailbox with a dedicated `JobBeeper/GoogleAlerts` label.
2. Owner-only Gmail authorization for the minimum permitted Gmail scope, separate from existing Google OIDC member sign-in.
3. Gmail API `users.watch` scoped to the dedicated label and a Google Cloud Pub/Sub topic.
4. Authenticated Pub/Sub push to the real IP-based production HTTPS origin, only if Google Cloud accepts that endpoint and its TLS certificate is valid for the IP literal.
5. Webhook persists the notification and history cursor/task before acknowledging. A worker uses Gmail `history.list` and `messages.get` to retrieve new messages under the label.
6. Durable idempotent message/result queue, safe redirect resolution, per-host budget/backoff, verified job extraction and source=`google_alerts` ingestion.
7. Reuse existing `upsert_jobs()`, `canonical_opportunities`, and per-user evaluation path. Do not build separate member matching.

This is a design to validate, not an assertion that Gmail or Pub/Sub has been configured. The label is an application-level processing filter; it does not narrow the OAuth grant to that label. Confirm Google Workspace API permitted-use-case and restricted-scope approval requirements before requesting Gmail access or making the OAuth app external/production.

## 4. Required preflight before further coding

### A. Confirm external HTTPS push compatibility
- Inspect the actual TLS certificate presented by `130.210.27.197:443` and verify the IP address is present as an IP Subject Alternative Name, not merely a DNS Common Name.
- Confirm the certificate chain is trusted and has not expired.
- Verify from current Google Pub/Sub documentation whether authenticated push supports an IP-literal HTTPS endpoint, rather than assuming DNS-hostname support.
- Do not change Nginx, DNS, certificates or production config during this check.

If IP-literal push is not supported, stop and identify an endpoint the owner actually controls or an approved provider-managed relay. Do not invent a custom domain or use a third-party hostname as though it belongs to the owner.

### B. Confirm Gmail API policy and OAuth
- Confirm this product use case is allowed by Google's Workspace API user-data policy.
- Determine the applicable OAuth audience and verification/security-assessment route for `gmail.readonly`.
- Keep existing member sign-in `openid email profile` scopes unchanged.
- Never request Gmail credentials or refresh tokens in chat; use owner-controlled configuration.

### C. Confirm event format
- Obtain one representative Google Alert email, sanitized of the owner's address and tracking identifiers, to validate sender, subject, HTML structure, link redirect shape and rule identification.
- Do not claim the Gmail parser works until this fixture is tested.

### D. Keep release gates
- The November 20 member browser/API/database mapping issue remains unresolved. Do not treat the unrelated member-facing hostname as an alias for the IP-based production host.
- Per-user notifications remain unverified; do not enable Telegram as part of this work.
- Preserve the existing 10-board ATS allowlist, Workday/LinkedIn cooldowns and intentionally paused Naukri relay.
- Develop and test in a fresh isolated workspace/DB. The production checkout is stale and must not be used.
- No production deployment, live OAuth consent, Gmail watch registration, Pub/Sub provisioning, DB migration, or Nginx changes without the relevant explicit approval and separate release gate.

## 5. Estimate and current status

The previous estimate of 5–7 days was based on the invalid Cloudflare route and is withdrawn. Return a revised estimate only after confirming the certificate/IP endpoint compatibility, Gmail OAuth policy path and sample Alert email. The earlier 6–9 day Gmail API estimate is also provisional until those exact deployment constraints are checked.

**Current state:** documentation correction only. No production changes. The Cloudflare branch is quarantined as superseded and must not be merged/deployed.

## 6. Source documents

- `docs/NEXT_AGENT_START_HERE.md`
- `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`
- `docs/PRODUCTION_ACCEPTANCE_2026-11-20.md`
- `docs/RELEASE_QUALIFICATION_2026-11-18.md`
- `v2/README.md`

