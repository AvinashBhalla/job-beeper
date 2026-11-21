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



## 8. RSS delivery alternative — evaluate before Gmail API

A lower-permission alternative is to consume Google Alerts' own Atom feed rather than reading Gmail:

- Current independent 2026 guides report that Google Alerts still exposes a `Deliver to → RSS feed` option when editing/creating an alert while signed in. The feed is an Atom XML document with a URL resembling `https://www.google.com/alerts/feeds/<id>/<id>`.
- Google's current official Google Alerts Help page documents email notifications and the alert settings but does **not** document the RSS option or guarantee feed availability/retention. Treat RSS as an observed UI feature, not a supported API contract.
- Recent independent observations found entries with HTML title/snippet fields and Google redirect-wrapper links where the publisher URL is embedded in the `url=` query parameter. Two independent reports observed feeds containing about 20 recent entries; this is an observation, not a guaranteed universal cap or retention contract.
- The feed URL may be fetchable without Google login. Treat it as a bearer secret: do not paste the real URL into tickets, logs, chat, source control or public dashboards.
- RSS delivery appears to be mutually exclusive with email delivery for an individual alert. If the existing 98 alerts are changed to RSS, email delivery may stop. Preserving email could require a separate near-equivalent duplicate alert; duplicate-query constraints and whether a duplicate produces equivalent coverage are not established.

### Safe proof of concept

1. Do not edit or switch any of the existing 98 production alert rules.
2. Create a separate low-risk test alert in the owner's account with a query likely to yield a result. Set `Deliver to = RSS feed` and `How many = All results` if that option exists. Leave current email rules untouched.
3. Copy/export one representative Atom XML item into a local file, redacting the private feed URL and feed IDs. Preserve the Atom element structure, entry ID, Google link host/path/query keys, embedded `url=` destination, title markup and snippet markup. Remove/replace owner identifiers and tracking token values.
4. Record response headers (status, content-type, ETag, Last-Modified, Cache-Control, Date) with the feed URL itself removed. Do not share the actual feed URL.
5. Check whether conditional GET works, whether the feed retains entries, and whether repeated polling misses items. Use stable Atom entry IDs for deduplication.
6. Evaluate a modest conditional polling interval only after observing the update cadence and item turnover. A feed that exposes only a rolling set of recent entries can lose results when polling is too infrequent. With 98 feeds, request volume and Google's undocumented rate limits must be considered; do not assume a one-minute polling loop is acceptable.

RSS would replace the Gmail/Pub/Sub ingestion leg with polling, not create an inbound webhook. It may avoid the Gmail restricted-scope question but introduces feed-secret handling, polling latency, retention/capacity and no official availability guarantee. Do not migrate the existing 98 alerts until the pilot proves that the coverage and delivery trade-offs are acceptable.

Sources reviewed 21 November 2026:
- Google's [Create an alert Help page](https://support.google.com/websearch/answer/4815696/create-an-alert?hl=en) (official; describes email, does not document RSS).
- [Feeder's Google Alerts instructions](https://feeder.co/help/rss/add-google-alerts-to-feeder/) (third-party integration guidance; says to disable digest and set `How often` to `As-it-happens` to enable RSS).
- [Feedmarkdown's October 8, 2026 test](https://feedmarkdown.com/blog/google-alerts-rss-feed/) (third-party empirical observation; Atom structure, URL parsing, sample entry window and redirect wrapper).
- [Hushread's October 23, 2026 test](https://hushread.com/blog/google-alerts-rss-feed) (third-party empirical observation; confirms destination selection, Atom feed and rolling result examples).
- Google's [Workspace user-data policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy) (Gmail scopes only for approved use cases).

**Recommended order:** first test RSS with one separate test alert. Do not start Gmail restricted-scope work until the use case is accepted under Google's policy. Keep authenticated Pub/Sub as a fallback only if Google confirms the policy route and the IP-literal push endpoint is actually accepted.

## 9. Source documents

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
3. **Completed for one feed:** owner supplied an Atom sample and the live feed returned HTTP 200 with two parsed entries. Retention/entry turnover and update cadence remain unmeasured.
4. Keep the production checkout out of development; use a fresh isolated workspace and database for implementation/testing.
5. No production webhook, OAuth consent, Gmail watch, Pub/Sub resource, DB migration, or application deployment has been made.



## 10. Sample-based parser and live RSS pilot — 21 November 2026

The owner supplied a Google Alerts Atom sample titled `Google Alert - "Software Engineer" India React TypeScript`. It contains two entries (Shine and Foundit), each with:
- stable Atom `entry/id`;
- HTML `title` and `content`;
- UTC `published` and `updated` timestamps;
- a Google `/url` link whose `url=` query parameter contains the destination job URL.

The root feed ID includes account/Alert identifiers and the root `rel="self"` href is the private feed URL. Neither is stored in the test fixture or parser output. The feed URL is not committed to GitHub and is not part of the SQLite schema.

### Implementation in draft PR #101

Branch: `feat/google-alerts-rss-atom-parser`.

- `v2/google_alerts_rss.py`: Atom parser, HTML-to-text conversion (ignores script/style), Google redirect unwrapping, size limit, UTF-8 requirement, DTD/entity rejection, and static HTTPS/public-host checks. Uses existing `v2.dedupe.canonicalize_url`.
- `v2/google_alerts_rss_polling.py`: one-feed conditional poller, bounded streamed reads, Google-only feed redirects, HTTP 304 handling, sanitized 429/503 Retry-After handling, idempotent SQLite state/entry persistence, a sequential one-shot batch runner with persisted retry-backoff skips and configurable inter-request spacing, and a protected external JSON feed-config loader. The loader requires an owner-only regular file outside the repository and validates each feed URL; it hides URLs from repr/error strings. The config is plaintext protected by filesystem permissions, not encrypted.
- `v2/google_alerts_safe_fetch.py`: DNS-pinned HTTPS fetcher that validates all DNS answers before connecting, pins the chosen IP while retaining TLS hostname verification, manually revalidates each redirect hop, enforces robots.txt on every hop, caps response size and content types, and honours Retry-After on 429/503.
- `v2/google_alerts_job_extract.py`: conservative Schema.org `JobPosting` JSON-LD extraction. It requires title and hiring organization, rejects expired postings, and routes missing/ambiguous structured data to review.
- `v2/google_alerts_pipeline.py`: one-shot queue processor that collapses duplicate canonical result URLs within a batch, fetches and verifies destinations, records blocked/rejected/retryable/dead-letter/review states, and passes verified jobs into the existing V2 normalizer and `upsert_jobs()` callback.
- `v2/radar.py`: adds `process_google_alert_rss_queue()` and `run_google_alerts_rss_batch()` manual entry points. The latter loads the protected config path from `JOB_RADAR_GOOGLE_ALERTS_CONFIG`, polls once, then processes a bounded result batch. No timer or public endpoint is enabled.
- `v2/radar.py`: V2 `init_db()` now calls the additive schema initializer so feed-state and result-queue tables will be created on a future application deployment.
- `v2/test_google_alerts_rss.py`, `v2/test_google_alerts_rss_polling.py`, `v2/test_google_alerts_safe_fetch.py`, `v2/test_google_alerts_job_extract.py`, and `v2/test_google_alerts_pipeline.py`: 73 focused tests.
- `.github/workflows/v2-ci.yml`: adds the new files to the syntax-check list.

The new schema stores opaque feed IDs, labels, ETag/Last-Modified values, timestamps, error codes and parsed result metadata. **It does not store feed URLs, root feed IDs or self links.** It does store resolved external job destination URLs and parsed titles/snippets as work-queue data.

### Read-only live test of the supplied feed

The feed was fetched once through the poller in the isolated feature workspace. The result was:
- HTTP 200.
- Content-Type: `text/xml; charset=UTF-8` (accepted by the poller).
- Cache-Control: `no-cache, must-revalidate`.
- Expires: `Fri, 01 Jan 1990 00:00:00 GMT`.
- No ETag, Last-Modified or Content-Length response header.
- Two entries parsed, with destination hosts `www.shine.com` and `www.foundit.in`.
- Atom feed `updated`: `2026-11-20T05:10:07Z`.

**Implication:** conditional requests cannot currently save bandwidth for this feed because Google returned neither ETag nor Last-Modified. Each poll is likely to download the full (small) feed response. Keep the initial cadence conservative; do not enable frequent polling across all 98 feeds until request volume, update cadence and entry retention have been measured. This one response contained two entries; it does not establish a universal retention limit.

### Validation and remaining limitations

- Python 3.10.12 in a fresh isolated clone: `py_compile` passed for `radar.py`, parser, poller and both test files.
- Focused tests: **73/73 passed** after adding protected config, batch pacing, DNS pinning, robots, JobPosting extraction and shared-ingestion pipeline cases.
- The full `v2.test_radar` suite could not be imported in this clean VM workspace because `bs4` is not installed there. I did not install project dependencies on the production VM.
- Latest GitHub Actions run ended before runner assignment (`runner_id=0`, zero steps). No CI checks executed; repository CI remains unverified.
- PR #101 remains draft and unmerged.
- No feed scheduler/timer or automatic poll interval is enabled. The protected config loader exists, but the actual feed config file (including the remaining 97 URLs) has not been created or installed on the VM. The one-shot manual batch entrypoint is not configured or executed against all feeds.
- The safe fetcher, robots check, JobPosting extractor and V2 shared-ingestion pipeline exist only in the feature branch. They have not been deployed; no result queue has been populated in production.
- The additive schema initializer exists in code but has **not** been applied to the production database. The external feed-config loader has not been integrated into service startup or a systemd job.

The supplied RSS URL remains a private bearer-like link. Do not place it in tickets, logs, source control, public dashboards or copied diagnostics.


## 11. RSS protected-config and one-shot batch foundation — 21 November 2026

The polling module now also exposes:
- `load_google_alerts_feed_configs(path)`: loads a JSON file outside the repository, rejects symlinks/non-regular files, requires POSIX owner-only mode (0400/0600), caps file size and feed count at 98, validates Google Alerts feed URL host/path and unique opaque IDs, and avoids including the URL in object repr/error messages.
- `poll_google_alerts_feed_batch(conn, feeds)`: processes a configured list sequentially with one HTTP session, persists every success/failure, continues to later feeds after one feed fails, and skips feeds until their persisted Retry-After deadline passes.

Expected config shape (use placeholders only; never commit actual feed URLs):

```json
{
  "feeds": [
    {
      "id": "alert-software-engineer-india",
      "label": "Software Engineer India React TypeScript",
      "url": "https://www.google.com/alerts/feeds/REDACTED/REDACTED"
    }
  ]
}
```

**The actual file has not been created** and should be provided through a separate owner-only deployment secret/configuration path, not GitHub or chat. The loader is not yet wired into service startup. The batch helper is a one-shot function only; no schedule, timer, 98-feed import or automatic polling cadence has been enabled.

After adding config loader and batch/backoff tests, the focused parser/poller suite is **35/35 passing** in the clean isolated workspace. GitHub Actions remains unverified because the runner is not assigned (`runner_id=0`, no steps). The full V2 test suite could not be run on this workspace due missing `bs4`; no packages were installed on the production VM.

## 12. Destination verification and V2 shared-ingestion pipeline — 21 November 2026

The latest feature-branch increment implements the downstream result-processing path without creating a separate jobs database:

1. A bounded queue batch claims due RSS result rows and groups entries sharing the same canonical destination URL.
2. The safe fetcher resolves the destination host, rejects the entire DNS answer if any returned address is private/reserved, and connects to a validated IP while preserving the original host for TLS verification.
3. It disables automatic redirects, manually validates every redirect destination, and checks the destination host's robots.txt policy before each hop. A missing robots file is treated as no policy; 401/403 deny; an unavailable robots response fails closed. Response content types and size are bounded.
4. It parses Schema.org `JobPosting` JSON-LD. A listing needs a title and hiring organization; expired jobs are rejected; no/ambiguous structured evidence goes to review.
5. Verified records are normalized through the existing V2 `normalize_job()` and passed to existing `upsert_jobs()`. The existing path creates/updates shared jobs, assigns canonical opportunities and refreshes configured users' preference evaluations. No parallel job store or matching implementation is added.
6. Feed observations are retained as provenance in `source_details`; canonical URL determines the Google Alerts source ID. Multiple Alert rules with the same posting collapse to one destination fetch per batch, while existing DB uniqueness/canonical rules handle cross-batch/cross-source dedupe.
7. 403/robots-denied records become `blocked` (not retried), 404/410 and expired postings become `rejected`, 429/503/network failures are retried with Retry-After/backoff and eventually dead-lettered, while missing structured data becomes `needs_review`.

### Observed destination outcomes using the supplied sample

- Shine destination: robots.txt allowed access; the page returned HTTP 200 and a Schema.org `JobPosting` record. Extracted title: **Software Engineering - React & Node - Associate (India)**; employer: **PwC Acceleration Centers in India**; location: **All India, IN**; description present. This was a single read-only test from the isolated workspace.
- Foundit destination: returned **HTTP 403**. The fetcher stopped; no proxy, alternate identity or bypass was attempted.

### Latest isolated validation

- Python 3.10.12: `py_compile` passed for the parser, poller, fetcher, extractor, queue pipeline, V2 `radar.py`, and five focused test modules.
- Focused unit tests: **73/73 passed**.
- GitHub Actions V2 CI remains unverified because the job terminates before runner assignment (`runner_id=0`, zero steps). This is a runner/infrastructure failure, not a test report.
- The full existing `v2.test_radar` regression suite could not be imported in the clean workspace because `bs4` is not installed. I did not install project dependencies on the production VM.
- PR #101 remains draft and unmerged.

**Still not enabled:** no feed-config file is installed, the remaining 97 RSS URLs are not loaded, no automatic scheduler/timer exists, and no production DB migration/service deployment has occurred. The manual `run_google_alerts_rss_batch()` entrypoint exists but has not been called against all owner alerts.
