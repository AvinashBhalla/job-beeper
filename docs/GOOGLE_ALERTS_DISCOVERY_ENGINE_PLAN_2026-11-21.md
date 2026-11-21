# Updated implementation gate — 21 November 2026

## Owner clarification — multi-feed Atom contract (21 November 2026)

The owner confirmed that the remaining Google Alerts RSS feeds follow the same Atom 1.0 output format as the supplied sample; only the search string configured in each alert differs. Treat every feed as an instance of the same integration. There is no per-alert parser, result schema, scraper or ingestion path.

The implementation contract is one protected configuration record per alert: `id`, non-sensitive `label`, and private `url`. The search query remains configured in Google Alerts and is not duplicated into the runtime config. The same parser, sequential batch poller, per-feed checkpoint store, safe destination fetcher, JobPosting verification and V2 shared `normalize_job()`/`upsert_jobs()` path apply to all feeds. Duplicate canonical postings across different alert queries should be fetched once while preserving each feed observation as provenance.

See [Google Alerts RSS multi-feed operating guide](GOOGLE_ALERTS_RSS_MULTI_FEED_OPERATING_GUIDE_2026-11-21.md) for the exact config contract, security requirements, no-cost validation sequence and release gates.

**Current execution decision:** GitHub Actions quota is exhausted by owner choice. Do not trigger or pay for Actions runs. The reported isolated PR validation remains 73/73 focused RSS tests passed plus Python compilation; the full V2 regression suite remains unverified because the earlier clean workspace lacked `bs4`. Complete that suite locally in a fresh non-production virtual environment using the declared development requirements. No production VM, live database, configuration, timer or service is to be changed for this step.

**Outstanding:** install the owner-only feed file through a secure file-transfer path when the multi-feed pilot is ready; measure actual retention and batch duration before choosing cadence; keep the recurring scheduler and production rollout disabled until the full validation/release gates pass. No owner input is required immediately.


This is the initial architecture proposal. Before implementation, read [Google Alerts production-origin correction](GOOGLE_ALERTS_PRODUCTION_ORIGIN_CORRECTION_2026-11-21.md). The only documented project production origin is `https://130.210.27.197/` on the Oracle VM `job-radar`. Do not assume the owner controls `jobbeeper.com`; do not configure Cloudflare Email Routing or custom-domain workers there.

Live VM preflight on 21 November confirmed that `130.210.27.197` presents a trusted Let's Encrypt certificate with the IP in its IP SAN, HTTPS verification succeeds, and `/health` returns HTTP 200. Certbot 5.10.0 is configured for the shortlived profile with a twice-daily Snap timer and an Nginx reload deploy hook; a forced staging renewal simulation passed and did not change the live certificate. Google Pub/Sub documentation requires a publicly accessible HTTPS endpoint with a CA-signed certificate but does not explicitly settle IPv4-literal URL acceptance. Actual Pub/Sub API acceptance/delivery remains untested because the VM has no `gcloud` CLI/project and the webhook route is not implemented. Gmail `gmail.readonly` remains a restricted scope with a policy/verification gate, and a sanitized Alert fixture is still required. The previously created Cloudflare feature branch is quarantined, unmerged, and must not be deployed or cherry-picked.

**Previous 6–9 day estimate withdrawn** pending these checks. No Gmail OAuth, watch, Pub/Sub resource or production webhook has been configured.

---

# Google Alerts Discovery Engine — Architecture, Delivery Plan and Priority

**Planning date:** 21 November 2026  
**Priority:** P0 — next major discovery-source increment  
**Status:** Partially implemented in draft PR #101; not deployed  
**Scope decision confirmed by owner:** 98 Google Alert rules; all Alert messages arrive in one owner-controlled Gmail mailbox. Members do not connect Gmail. Valid jobs are stored once in the shared JobBeeper database and evaluated independently against each member's preferences.

> This document records the approved product direction and proposed engineering plan. It does not authorize code changes, Google Cloud resource creation, OAuth consent, or production deployment. Those remain separate execution/release actions.



## Alternative intake path discovered — test RSS before Gmail OAuth

Current independent reports from October 2026 show that Google Alerts exposes a `Deliver to → RSS feed` option for signed-in alert rules and returns Atom XML. Google's official Alerts Help page currently documents email delivery, not RSS, so this is an observed UI behavior, not a guaranteed official API contract.

**Proof-of-concept progress:** the owner supplied one live RSS URL and an Atom sample for one alert, without changing the remaining rules. A read-only poll returned HTTP 200 and two entries; the response had `Cache-Control: no-cache, must-revalidate`, but no ETag, Last-Modified or Content-Length. This means the current feed cannot use HTTP conditional validators and each poll downloads the full (small) response. Its Atom `<updated>` was `2026-11-20T05:10:07Z`. One fetch does not establish cadence, entry retention or a universal entry cap. Do not migrate or change any of the 98 rules until a controlled retention/cadence pilot demonstrates coverage equivalence and the impact on email delivery.

RSS is polling, not webhook delivery. It may avoid the Gmail `gmail.readonly` restricted-scope and Pub/Sub gates, but RSS has undocumented support/retention behavior, secret feed URLs, update latency and potential request volume across 98 feeds. See the correction document's RSS evaluation section for the pilot protocol and sources.

Gmail API remains blocked pending a Google policy decision: the current approved Gmail-scope use cases are email clients, email backup, productivity enhancements to email, or reporting/monitoring services that improve the email experience. Job-discovery extraction for a multi-member product is not an obvious fit. Do not request `gmail.readonly` until this specific use is confirmed as permitted.


**Parser/polling foundation in draft PR #101 — 21 November 2026:** the supplied sample is Atom 1.0 with two entries (Shine and Foundit), stable entry IDs, HTML title/content, UTC timestamps and Google `/url?url=` destination wrappers. The private root feed ID and `rel="self"` URL are excluded from source and parser output. PR #101 now contains the Atom parser, one-feed conditional poller, sanitized rate-limit/error handling, idempotent SQLite feed-state/result tables, and V2 `init_db()` initialization. The database stores no feed URL. A live read-only fetch of the supplied feed returned HTTP 200, `text/xml; charset=UTF-8`, two entries, no ETag/Last-Modified, and `Cache-Control: no-cache, must-revalidate`. The feed's Atom `updated` was `2026-11-20T05:10:07Z`. The 25 focused tests and syntax compilation passed in the isolated workspace. GitHub Actions run 44898068226 failed before runner assignment (`runner_id=0`, zero steps); no CI steps ran. The V2 radar regression suite could not import because `bs4` is not installed in the clean VM workspace; dependencies were not installed on production. PR #101 remains draft/unmerged. No schedule, 98-feed configuration, result-page fetch/SSRF protection, job verification, shared ingestion or production deployment exists.

## 1. Product outcome

Add Google Alerts as a new shared discovery source. The owner maintains the 98 Google Alert queries and receives their results in one Gmail account. JobBeeper reacts when a new result email arrives, extracts candidate job links, verifies the underlying posting, and ingests valid jobs into the existing shared jobs/canonical-opportunity pipeline.

Members never connect their own Gmail accounts and never see the owner's mailbox, alert emails, query list, or mailbox metadata. Each valid job is evaluated against every member's JobBeeper preferences. A member sees an opportunity only when it satisfies that member's saved filters and matching threshold.

Google Alerts is a supplemental discovery channel, not a replacement for ATS APIs and not a way around destination-site access controls or rate limits. The current MVP preference is to consume each alert's Atom RSS feed with conservative polling; Gmail API/PubSub remains a deferred fallback, not the default implementation.

## 2. Proposed event-driven architecture

### 2.1 Gmail label and filter

Create a dedicated Gmail label, for example `JobBeeper/GoogleAlerts`. Set a Gmail filter for the Google Alerts sender and/or the known alert-message pattern so matching messages receive this label automatically.

The label is the source boundary. Do not subscribe to a broad Gmail tab such as Promotions or Updates. The Gmail API watch will use the exact label ID with `labelFilterBehavior=INCLUDE`, so unrelated mailbox changes do not trigger the JobBeeper ingestion flow.

**Least-privilege choice:** ask the owner to create the label and Gmail filter in Gmail's UI. JobBeeper should not need permission to create labels, change filters, mark mail read, archive messages, or modify the mailbox.

### 2.2 Push notification path

1. The owner authorizes a separate, owner-only Gmail connection using a dedicated OAuth flow and the read-only Gmail scope.
2. JobBeeper registers a Gmail `users.watch` on the dedicated label.
3. Gmail publishes mailbox-change notifications to a Cloud Pub/Sub topic.
4. A Pub/Sub push subscription sends an authenticated HTTPS POST to the JobBeeper webhook, proposed route: `POST /api/webhooks/google-pubsub`.
5. The webhook validates the Pub/Sub push identity/token and expected project/audience, decodes the notification, checks the configured owner mailbox, and durably queues a mailbox-sync task. It returns HTTP 2xx only after the notification has been accepted for processing.
6. The worker calls Gmail `history.list` using the last committed history cursor, selects newly added messages carrying the configured label, then fetches those messages for parsing.
7. Message parsing extracts each result's title, snippet, displayed source and destination URL. Each result is queued independently for safe URL resolution and posting verification.

**Important:** a Gmail push notification is a change signal, not an email payload. It carries the mailbox identity and a new history ID. JobBeeper must use Gmail history to discover the message IDs. A notification may represent multiple mailbox changes; never assume one notification equals one alert email or one job.

### 2.3 Watch lifecycle and recovery

- Renew `users.watch` once per day. Gmail stops sending updates if a watch is not renewed at least once every seven days.
- Persist the last successfully processed Gmail history ID. Advance it only after all corresponding message IDs have been durably recorded for processing.
- Make notification receipt, history pages, message ingestion and result processing idempotent.
- Use a low-frequency reconciliation task (proposed every 15 minutes) to call `history.list` after the last cursor. This is a safety net for delayed or dropped push notifications, not the primary trigger.
- If Gmail returns HTTP 404 because the stored history cursor is too old, run a bounded full sync for the labelled-message window, deduplicate, and record the new cursor.
- Handle Pub/Sub redelivery safely. Acknowledge quickly after durable queueing; do not parse pages or crawl destination sites inside the webhook request.

Gmail documents push delivery as typically occurring within seconds, but warns that notifications can be delayed or dropped. The product should be event-driven, with reconciliation for correctness—not marketed as a hard real-time SLA.

### 2.4 RSS polling path — current preferred MVP

The owner supplies one private Google Alerts feed URL per rule through a secure runtime configuration file. JobBeeper does not authenticate to Gmail and members do not connect mailboxes.

1. The worker reads an enabled feed's URL from the protected configuration source. Feed URLs are bearer-like secrets; do not commit them, store them in SQLite, print them, or include them in error messages.
2. Each feed is identified in the database by an opaque stable ID and a non-sensitive label. The URL remains only in the runtime configuration.
3. The worker requests the feed over HTTPS from the Google Alerts feed endpoint, with a strict host/path allowlist, bounded timeout, streamed response-size limit and redirects disabled by default.
4. If Google redirects, follow only a small bounded number of redirects that remain Google Alerts feed URLs. Never forward the private feed URL to another host.
5. Parse Atom 1.0, extract stable entry IDs and readable title/snippet/date fields, unwrap the Google `/url` destination, and normalize it through the existing canonical URL helper.
6. Persist the feed checkpoint and new entries atomically. Repeated Atom IDs update `last_seen_at` but do not create duplicate queue rows or reset processing state.
7. Process result rows asynchronously in a separate safe destination-fetch/verification stage. Never fetch arbitrary result URLs inside the polling request.

**Prototype status in draft PR #101:** `v2/google_alerts_rss.py` and `v2/google_alerts_rss_polling.py` implement Atom parsing, single-feed polling, ETag/Last-Modified support, HTTP 304, bounded reads, Google-only feed redirects, Retry-After handling and idempotent SQLite checkpoint/result storage. `poll_google_alerts_feed_batch()` adds a one-shot sequential batch with persisted backoff and configurable request spacing. `load_google_alerts_feed_configs()` reads a JSON file outside the repository, requires a regular non-symlink file with POSIX owner-only permissions (0400/0600), validates Google feed URLs and hides URLs from repr/errors. The config is plaintext protected by filesystem permissions, not encrypted.

The branch also adds `v2/google_alerts_safe_fetch.py` (DNS-pinned HTTPS, per-hop revalidation, robots.txt enforcement, bounded response), `v2/google_alerts_job_extract.py` (conservative Schema.org JobPosting extraction), and `v2/google_alerts_pipeline.py` (bounded result queue, status/backoff, canonical-URL grouping and shared V2 upsert callback). `v2/radar.py` exposes manual one-shot `run_google_alerts_rss_batch()` via `JOB_RADAR_GOOGLE_ALERTS_CONFIG`; no public route or scheduler exists. `v2/radar.py:init_db()` initializes the additive tables on a future deployment. The actual config file and remaining 97 feed URLs have not been installed/imported.

**Live behavior observed on the supplied feed:** HTTP 200; `text/xml; charset=UTF-8`; `Cache-Control: no-cache, must-revalidate`; no ETag, Last-Modified or Content-Length; two entries. Therefore HTTP conditional validators are not currently available for this feed. Polling cadence must stay conservative until feed update cadence and entry retention are measured. Do not assume independent reports of a 20-entry feed window apply to every alert.

## 3. Message and job processing

### 3.1 Alert-rule identification

Keep a catalogue for the 98 queries. Each rule should have a stable ID and fields such as query text, role family, skill/technology tags, seniority, location/region, priority, and enabled state.

The Google Alert subject/body is a hint for mapping an email back to its rule. Rule metadata helps classify the result, but it is not proof that a link is a valid job. One email may contain multiple results; process each URL independently.

### 3.2 URL resolution and safety

- Resolve Google redirect links to their destination and normalize tracking parameters before fingerprinting.
- The feature-branch safe fetcher resolves each destination host before connecting and rejects the entire DNS answer if any returned address is non-global (private, loopback, link-local, multicast or reserved).
- Pin the connection to a validated numeric IP while retaining the original hostname for TLS SNI/certificate verification and the HTTP Host header. Disable automatic redirects and repeat URL validation, DNS checks and robots.txt policy checks on every redirect hop.
- Apply a bounded redirect count, 12-second default timeout, 2 MB response cap, and HTML/XHTML/plain-text content types only. No cookies, credentials or proxies are used. Never download executables or fetch internal network resources.
- Robots policy is cached in memory for one hour per host. Missing robots.txt is treated as no rules; 401/403 denies; unavailable robots data fails closed. A 403 or robots denial is recorded as blocked; do not bypass access controls.
- Use a stable normalized-URL fingerprint so the same posting found by several queries or emails is fetched once, while each query/email observation remains available as provenance.

### 3.3 Verification and extraction tiers

A Google Alert snippet is incomplete evidence. Only publish a job after checking the destination posting.

Current MVP:
1. Schema.org `JobPosting` JSON-LD extraction (implemented on the feature branch).
2. Otherwise route to `needs_review`; do not infer a job from the Alert snippet alone.

A later increment may add recognized public ATS APIs or permitted HTML extraction as separately reviewed tiers. Blocked/robots-denied destinations are never retried using alternate identities or proxies. Expired postings are rejected. Missing title or hiring organization is insufficient evidence and goes to review.

Capture title, employer, location, description, source URL, application URL, posted/updated/expiry dates when present, employment type, experience when present, extraction method and confidence. Distinguish an actual job detail page from a search page, company homepage, aggregator page, expired posting or irrelevant article.

A page returning 403/429 remains blocked/deferred or needs review; it is not a verified job. Honour Retry-After, host cooldowns and bounded retries. No proxy rotation, CAPTCHA bypass, identity rotation or rate-limit circumvention. A failed fetch must not silently become a valid job based only on the Google snippet.

### 3.4 Shared ingestion and member matching

- The feature-branch queue worker normalizes verified records through existing V2 `normalize_job()` and delegates to `upsert_jobs()`. It uses the same shared `jobs` store and canonical-opportunity path as the existing sources.
- The normalized source is `google_alerts`; `source_job_id` is derived from the final canonical URL. Provenance in `source_details` records opaque feed ID/label and Atom entry ID, plus the original Alert snippet and extraction method.
- Existing `upsert_jobs()` performs canonical deduplication and calls `refresh_configured_user_evaluations(affected_job_ids)`. Each verified posting is evaluated against configured users' own preferences.
- Multiple Alert entries with the same canonical destination URL are grouped for one fetch per processing batch. Existing source uniqueness and canonical linking handle replays and cross-source dedupe.
- Do not use the owner's Google Alert query catalogue as a member filter. The owner's queries control discovery coverage; each member's own preferences control visibility.
- Keep source ingestion and member notification delivery separate. A job can be stored and matched even while Telegram is disabled or unverified.

### 3.5 Candidate states

Suggested processing states:

`received` → `parsed` → `queued` → `resolved` → `verified` → `published`

Terminal/recoverable states include `duplicate`, `irrelevant`, `expired`, `blocked_rate_limited`, `needs_review`, and `error_retryable`.

Retain minimal message metadata and processing provenance. Do not persist complete raw email bodies indefinitely. Store Gmail message IDs/history cursor and the smallest content fragments needed for audit/replay. Encrypt refresh tokens at rest, keep them out of logs and never store them in source control.

## 4. OAuth, privacy and Google Cloud requirements

### 4.1 Separate Gmail authorization from member sign-in

The current `v2/google_oauth.py` is an OpenID Connect sign-in flow using only `openid email profile`. It is not Gmail mailbox access.

Implement a distinct owner-only connection flow with its own state, PKCE, callback, token storage and disconnect/revoke path. Do not expand the member sign-in scopes and do not ask JobBeeper members to connect Gmail.

The intended Gmail permission is `https://www.googleapis.com/auth/gmail.readonly`. It is restricted by Google's scope classification. It allows broad read access to Gmail messages/settings; the dedicated label is an application-side filter, not an OAuth permission boundary. The consent screen must plainly explain that JobBeeper reads alert messages from the owner's mailbox and does not modify or send email.

Before implementing this path, confirm that this product use case is permitted under Google's Workspace API user-data policy—not just that the OAuth flow technically works. Google's Gmail-scope policy limits access to approved use cases, including certain user-benefiting productivity and email-based monitoring/reporting services. If the use case is not accepted, stop before requesting the restricted scope and reassess the intake architecture rather than attempting to work around Google's policy.

Google's current policy indicates that restricted-scope apps accessing restricted data from or through a third-party server may need restricted-scope verification and a security assessment. The exact path depends on how the owner-only OAuth project is classified and configured. Confirm this before production; do not assume that a single-mailbox deployment automatically waives every requirement.

### 4.2 Pub/Sub setup

Provision one topic in the Google Cloud project used by this Gmail watch. Grant the Gmail API push service identity permission to publish to that topic. Configure a Pub/Sub push subscription to the stable public HTTPS webhook URL, with authenticated push/OIDC and a dedicated audience/service identity. Keep the webhook secret-free in its URL and validate the token server-side.

Gmail requires the topic to exist and have publish permission before `users.watch` succeeds. The webhook endpoint must be publicly reachable over valid HTTPS from Google Cloud. The final production hostname and routing must be resolved first.

### 4.3 Cost posture

This design avoids a permanent two-minute full mailbox poll and uses Gmail history only after a push or reconciliation tick. Pub/Sub pricing currently includes 10 GiB/month of basic message delivery throughput free; actual billing depends on usage, region/data transfer and the billing configuration of the Google Cloud project. At one mailbox and small push payloads, expected traffic should be tiny, but verify the account's billing setup before provisioning anything. No paid scraping API, LLM API or proxy service is required for the MVP.

## 5. Proposed data model

Extend the existing SQLite database with owner-scoped source-control and work-queue tables. Final schema must be designed against the current migrations and DB initialization path; these are conceptual entities, not instructions to create tables verbatim.

| Entity | Purpose |
|---|---|
| `google_alert_mailbox` | Single owner mailbox connection, encrypted token reference, label ID, last history cursor, watch expiration, last successful sync and connection state |
| `google_alert_rules` | The 98 stable query records and their role/skill/location/priority metadata |
| `google_alert_messages` | Gmail message ID, thread ID, internal date, matched rule, parser version and processing status |
| `google_alert_results` | One row per result link, normalized URL fingerprint, title/snippet/domain, source message/rule and result status |
| `external_url_fetch_queue` | Deduplicated URL fetch jobs, host key, attempts, due time, retry-after/cooldown, response metadata and extraction outcome |
| Existing `jobs` / `canonical_opportunities` | Shared verified job observations and cross-source canonical dedupe |
| Existing per-user evaluations | Visibility/match decisions for each member |

Unique constraints should cover Gmail message IDs, message/result identity and normalized URL fingerprints. Queue leasing must prevent duplicate parallel fetches and allow safe retry after worker/container restarts.

## 6. Admin visibility and operations

Add an Admin area under Discovery → Google Alerts showing:
- Gmail connection state, label and last successful sync.
- Gmail watch expiration and next renewal.
- Last Pub/Sub notification time and last reconciliation time.
- Alert rules enabled/disabled and number classified.
- Messages received, messages parsed and results/URLs extracted.
- URLs fetched, verified jobs published, duplicates merged, expired/irrelevant results, blocked/rate-limited results and needs-review backlog.
- Extraction success rate and per-host cooldown/backoff state.
- Latest error class without message bodies, OAuth tokens, message contents or private mailbox data.

Add structured logs keyed by hashed message/result identifiers, not raw email content or secrets. Alert on expired watch, stale history cursor, repeated webhook authentication failures, queue age, dead-letter growth and prolonged absence of successful syncs.

## 7. Delivery estimate

**A revised delivery estimate is intentionally withheld.** The previous 6–9 focused engineering day estimate and the 2–3 day proof-of-flow estimate are withdrawn. They were issued before verifying the real IP-based production origin and before establishing the Gmail restricted-scope policy route.

The VM-side certificate/renewal preflight is now **PASS**. The remaining schedule-driving items are:
- actual Pub/Sub API acceptance and authenticated delivery to an IP-literal endpoint (or selecting an owner-controlled alternative if Google rejects it);
- confirmation of the applicable Gmail restricted-scope permitted-use-case, OAuth verification and any required security assessment;
- one sanitized Google Alert message fixture;
- a clean isolated development workspace and test database;
- the unresolved member browser/API/database mapping acceptance gate.

Re-estimate after those items are resolved. Do not treat a working TLS certificate or a successful Certbot staging renewal as proof that the full Gmail/Pub/Sub integration is launch-ready.

## 8. Rollout and acceptance gates

### Gate A — preflight
- Confirm representative email format, sender, subject and result-link structure.
- Inventory all 98 query rules and map them to stable IDs/categories.
- Confirm dedicated Gmail label/filter, target OAuth project/audience and owner-only consent.
- Confirm public HTTPS host, Pub/Sub topic ownership, authenticated push subscription and billing posture.
- Review privacy notice, data minimization and token encryption.

### Gate B — isolated integration
- Complete one mailbox authorization without changing member sign-in.
- Demonstrate label-scoped `users.watch`, Pub/Sub delivery, token verification and history sync.
- Demonstrate daily renewal, duplicate notification handling, reconciliation, expired-cursor recovery and queue recovery after restart.
- Prove webhook does not parse or crawl synchronously and acknowledges only after durable acceptance.

### Gate C — pilot
- Process a silent historical window (proposed last seven days) without sending member notifications.
- Enable 5–10 representative Alert rules first.
- Manually audit a sample of verified, duplicate, expired, irrelevant, blocked and needs-review results.
- Confirm that a single posting discovered by multiple rules or ATS sources creates one canonical opportunity with multiple provenance observations.
- Confirm one member's match does not leak to another member and the owner mailbox/query details are never exposed to members.

### Gate D — production
- Enable all 98 rules after pilot quality passes.
- Verify webhook, watch-renewal, reconciliation, queue and source-health telemetry.
- Confirm new jobs are stored once and evaluated against every member's own preferences.
- Verify the correct member API origin consumes the same shared database before declaring member-facing visibility accepted.
- Keep Telegram/per-user push notifications off until the separate per-user notification path is proven in production and an approved test is completed.
- Release with rollback plan; no change to existing ATS allowlist, Workday/LinkedIn cooldowns or the intentionally paused Naukri relay.

### Production acceptance criteria

1. A new message receiving the dedicated Gmail label creates a Pub/Sub event and is picked up without waiting for a periodic mailbox scan.
2. Push events and message processing are safe under duplicate/out-of-order deliveries.
3. Reconciliation recovers changes after a simulated missed notification; daily watch renewal keeps the subscription active.
4. Every result link is either verified, explicitly rejected/classified, or placed in a retry/review state—never silently treated as a job.
5. Repeated result URLs and cross-source observations do not create duplicate canonical opportunities.
6. Verified jobs are shared in storage; member visibility is determined by that member's preference evaluation only.
7. Gmail credentials, email bodies, alert queries and mailbox metadata are not exposed to members or logs.
8. No production rate limit, cooldown, robots/access restriction or CAPTCHA is bypassed.
9. Admin health counters and release/rollback evidence are available.

## 9. Priority against the existing JobBeeper backlog

This feature becomes the **P0 next discovery-source priority**, ahead of the older member-submitted-URL enhancement. It does not cancel the release-acceptance items or authorize unrelated source changes.

| Priority | Work item | Current constraint / direction |
|---|---|---|
| **P0** | Google Alerts Discovery Engine | New focus. One owner Gmail mailbox, label-scoped Pub/Sub push, shared verified ingestion and per-member preference evaluation. |
| **P1 gate** | Resolve member browser/API/database mapping | The 20 November audit could not prove that the member site and inspected VM share the same jobs backend. Resolve before claiming end-to-end member visibility for Google Alerts. |
| **P1 gate** | Source Health accuracy | Preserve meaningful degraded states for Workday/LinkedIn rate limits, Keka partial failures and intentional Naukri pause. Do not force retries or bypass cooldowns. |
| **P1 gate** | Per-user notification readiness | The audit found zero rows in per-user notification settings and ledger. Keep Telegram delivery separate and unverified until it has a safe end-to-end acceptance test. |
| **P2** | Member-submitted shared career URLs / canonical feed | Existing issue #99 remains planned. Google Alerts URL resolution and shared dedupe may provide reusable components, but do not expand scope in this increment. |
| **Deferred** | Additional ATS board activation / paid SERP discovery / Naukri relay reactivation | No change without a separately reviewed and approved plan. |

Do not modify the existing 10-board allowlist or use Google Alerts to bypass Workday/LinkedIn cooldowns. Keep the Naukri relay intentionally paused and retain its freshness guard.

## 10. Relevant repository components and external references

Existing code to reuse or integrate carefully:
- `v2/google_oauth.py` and `docs/GOOGLE_OAUTH_SETUP.md`: current OIDC member sign-in only; create a separate Gmail mailbox authorization flow.
- `v2/board_scheduler.py`: persistent per-board scheduling and host-lease/backoff patterns; extend/shared-host policy should be designed deliberately for arbitrary result URLs.
- `v2/sqlite_store.py`: shared SQLite connection and write-lock conventions.
- `v2/radar.py`: existing FastAPI app, job ingestion and normalization entry points.
- `v2/user_preferences.py`: member-specific preferences and evaluations.
- `v2/telegram_linking.py`: per-user Telegram linking; delivery is a separate concern.
- `docs/PRODUCTION_ACCEPTANCE_2026-11-20.md`: production constraints and unresolved member-host mapping.

Google documentation:
- [Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push)
- [Gmail users.watch reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/watch)
- [Gmail synchronization and history cursor recovery](https://developers.google.com/workspace/gmail/api/guides/sync)
- [Gmail API OAuth scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [Google Workspace user-data and restricted-scope policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy)
- [Cloud Pub/Sub pricing](https://cloud.google.com/pubsub/pricing)

---

**Execution status:** partial implementation in draft PR #101. The branch contains Atom parsing, protected external feed config loading, one-shot feed polling/batching, DNS-pinned robots-aware destination fetching, Schema.org JobPosting extraction, a result queue and a manual wrapper into existing V2 shared ingestion/per-user evaluation. The supplied feed has been fetched once read-only; Shine returned a verified JobPosting and Foundit returned HTTP 403 (blocked). The actual config file has not been created; the remaining 97 URLs are not loaded; no scheduler/timer or public endpoint is enabled. Focused tests pass 73/73 and py_compile passes in the clean Python 3.10.12 workspace. GitHub Actions remains blocked before runner assignment (runner_id=0, zero steps); the full V2 radar suite remains unverified because bs4 is missing from the clean workspace. No production database migration or deployment has occurred.


## 11. Live VM preflight — 21 November 2026

See [Google Alerts production-origin correction](GOOGLE_ALERTS_PRODUCTION_ORIGIN_CORRECTION_2026-11-21.md#7-live-vm-preflight--21-november-2026) for the full command evidence.

**VM-side certificate/renewal gate: PASS.** The live IP certificate includes the production IP in its IP SAN and passes CA validation. Certbot 5.10.0 is configured with the Let's Encrypt `shortlived` profile, a webroot challenge on `/var/www/letsencrypt`, a twice-daily Snap renewal timer (`00:00` and `16:19 UTC`), and a deploy hook that reloads Nginx. A forced staging renewal simulation succeeded. The live certificate serial remained unchanged; Nginx config test and production health check passed; the production container remained up.

**Google Pub/Sub endpoint gate: NOT YET PROVEN.** The current official documentation says the endpoint must be publicly accessible over HTTPS with a valid CA-signed certificate, but does not explicitly clarify IPv4-literal URL support. No GCP project or `gcloud` CLI is available on the VM, no Pub/Sub resources were provisioned, and the webhook route is not implemented. Verify actual API acceptance/delivery in the owner's GCP project before treating this design as approved.

**No production application, database, Nginx, certificate, Gmail, DNS, Cloudflare or Pub/Sub configuration was changed.** The only external challenge activity was the Certbot staging dry run.


## 12. Verification pipeline — implementation status, 21 November 2026

The draft implementation calls the existing V2 `normalize_job()` and `upsert_jobs()` functions; it does not create a parallel job store or preference matcher. Verified records are inserted/updated in the shared jobs table, canonical linking runs through existing functions, and existing `upsert_jobs()` refreshes configured-user evaluations for affected job IDs. Alert rule/feed provenance remains on the shared row in `source_details`.

One read-only sample-destination test through the safe fetcher returned:
- Shine: robots allowed; HTTP 200; Schema.org JobPosting verified as Software Engineering - React & Node - Associate (India), PwC Acceleration Centers in India, All India, IN.
- Foundit: HTTP 403; classified blocked and not bypassed.

The feature branch now has **73/73 focused tests passing** and passes syntax compilation. GitHub Actions remains unverified (runner ID 0/no steps), and the full V2 suite was not run due missing bs4. PR #101 remains draft/unmerged. There is no installed config file, no remaining-97 import, no scheduler/timer and no production migration or deployment.
