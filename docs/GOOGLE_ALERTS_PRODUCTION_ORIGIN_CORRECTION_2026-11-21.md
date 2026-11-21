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

**Current state:** production preflight and a Let’s Encrypt staging renewal simulation completed; no production runtime/configuration/database changes. The staging test left the live certificate serial unchanged. Documentation is updated with the evidence below. The Cloudflare branch remains quarantined as superseded and must not be merged/deployed.

## 6. Source documents

- `docs/NEXT_AGENT_START_HERE.md`
- `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`
- `docs/PRODUCTION_ACCEPTANCE_2026-11-20.md`
- `docs/RELEASE_QUALIFICATION_2026-11-18.md`
- `v2/README.md`



## 7. Live VM preflight — 21 November 2026

Read-only checks were run through the connected Terminal Commands device `job-radar`. No Nginx configuration, certificate files, application files, environment values, database, Docker container, DNS, Gmail setting, or production service was changed.

### TLS and Certbot

- Live origin: `https://130.210.27.197/`.
- The certificate served on port 443 has an **IP Subject Alternative Name** for `130.210.27.197`. It is issued by Let's Encrypt (intermediate `YE2`); `curl` certificate verification returned `ssl_verify_result=0`.
- Observed live certificate validity: `2026-11-19 23:09:23 UTC` through `2026-11-26 15:09:22 UTC`. This is expected for a Let's Encrypt IP-address certificate using the `shortlived` profile (approximately 160 hours / six days), not a conventional 90-day DNS certificate.
- Certbot version: `5.10.0`. Renewal config has `preferred_profile = shortlived`, `authenticator = webroot`, and maps the IP to `/var/www/letsencrypt`.
- Snap Certbot systemd timer is scheduled twice daily, at `00:00 UTC` and `16:19 UTC`. The November 21 `00:00 UTC` timer service completed successfully.
- Executable root-owned deploy hook exists at `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh`; it runs `systemctl reload nginx`.
- A staging-only challenge test passed:
  `sudo certbot renew --dry-run --force-renewal --cert-name jobbeeper-ip-prod`.
  Certbot reported: `Congratulations, all simulated renewals succeeded`.
- After the staging test, the live certificate serial/fingerprint remained unchanged, HTTPS `/health` still returned HTTP 200, and `nginx -t` passed.

Let’s Encrypt documents that IP-address certificates must use its short-lived profile, and recommends reliable automation. The current configuration has a twice-daily renewal timer and a deploy hook; no manual production renewal was needed during this audit.

### Pub/Sub IP-literal endpoint compatibility

Current Google Cloud Pub/Sub documentation requires a publicly accessible HTTPS endpoint with a valid CA-signed certificate. The documentation reviewed does **not** explicitly state whether an IPv4-literal URL is accepted or rejected. The production certificate and HTTPS checks satisfy the certificate-name/trust part of that requirement, but this is **not proof** that the Pub/Sub API will accept or successfully deliver to an IP-literal push endpoint.

The connected VM has no `gcloud` CLI or configured GCP project. No Pub/Sub topic/subscription was created and no real push delivery was attempted. The proposed route `/api/webhooks/google-pubsub` is not implemented. Actual Google-side URL acceptance/delivery remains an open preflight gate.

### Runtime state after the checks

- Nginx is active and its configuration test passes.
- Container `v2-radar-1` remains up on image `job-radar-prod-release:dda6d57`.
- Public-IP HTTPS `/health` returns HTTP 200 with certificate verification successful.
- No live certificate serial change occurred during the staging dry run.

### Remaining gates

1. Verify actual Pub/Sub endpoint URL acceptance and authenticated push delivery in the owner's Google Cloud project after the webhook route is built in an isolated development workspace.
2. Confirm Google's current Gmail restricted-scope permitted-use-case and OAuth verification/security-assessment path for this owner-only mailbox use.
3. Obtain one sanitized representative Google Alert email to validate the parser and redirect-link handling.
4. Keep the production checkout out of development; use a fresh isolated workspace and database for implementation/testing.
5. No production webhook, OAuth consent, Gmail watch, Pub/Sub resource, DB migration, or application deployment has been made.
