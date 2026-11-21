# Updated implementation gate — 21 November 2026

This is the initial architecture proposal. Before implementation, read [Google Alerts production-origin correction](GOOGLE_ALERTS_PRODUCTION_ORIGIN_CORRECTION_2026-11-21.md). The only documented project production origin is `https://130.210.27.197/` on the Oracle VM `job-radar`. Do not assume the owner controls `jobbeeper.com`; do not configure Cloudflare Email Routing or custom-domain workers there.

The Gmail API + Pub/Sub design remains a candidate only after confirming the production IP TLS certificate includes the IP as an IP SAN, Google Pub/Sub authenticated push supports an IP-literal HTTPS endpoint, the Gmail restricted-scope use case is permitted, and a real sanitized Alert fixture can be parsed. The previously created Cloudflare feature branch is quarantined, unmerged, and must not be deployed or cherry-picked.

**Previous 6–9 day estimate withdrawn** pending these checks. No Gmail OAuth, watch, Pub/Sub resource or production webhook has been configured.

---

# Google Alerts Discovery Engine — Architecture, Delivery Plan and Priority

**Planning date:** 21 November 2026  
**Priority:** P0 — next major discovery-source increment  
**Status:** Documented / not implemented  
**Scope decision confirmed by owner:** 98 Google Alert rules; all Alert messages arrive in one owner-controlled Gmail mailbox. Members do not connect Gmail. Valid jobs are stored once in the shared JobBeeper database and evaluated independently against each member's preferences.

> This document records the approved product direction and proposed engineering plan. It does not authorize code changes, Google Cloud resource creation, OAuth consent, or production deployment. Those remain separate execution/release actions.

## 1. Product outcome

Add Google Alerts as a new shared discovery source. The owner maintains the 98 Google Alert queries and receives their results in one Gmail account. JobBeeper reacts when a new result email arrives, extracts candidate job links, verifies the underlying posting, and ingests valid jobs into the existing shared jobs/canonical-opportunity pipeline.

Members never connect their own Gmail accounts and never see the owner's mailbox, alert emails, query list, or mailbox metadata. Each valid job is evaluated against every member's JobBeeper preferences. A member sees an opportunity only when it satisfies that member's saved filters and matching threshold.

Google Alerts is a supplemental discovery channel, not a replacement for ATS APIs and not a way around destination-site access controls or rate limits.

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

## 3. Message and job processing

### 3.1 Alert-rule identification

Keep a catalogue for the 98 queries. Each rule should have a stable ID and fields such as query text, role family, skill/technology tags, seniority, location/region, priority, and enabled state.

The Google Alert subject/body is a hint for mapping an email back to its rule. Rule metadata helps classify the result, but it is not proof that a link is a valid job. One email may contain multiple results; process each URL independently.

### 3.2 URL resolution and safety

- Resolve Google redirect links to their destination and normalize tracking parameters before fingerprinting.
- Allow only valid public web destinations. Reject localhost, private, loopback, link-local and reserved IP ranges; validate each redirect hop and defend against DNS rebinding/SSRF.
- Bound redirects, response size, content types, connection/read timeouts and per-host concurrency.
- Do not follow arbitrary schemes, download executables, or fetch internal network resources.
- Use a stable normalized-URL fingerprint so the same posting found by several queries or emails is fetched once, while each query/email observation remains available as provenance.

### 3.3 Verification and extraction tiers

A Google Alert snippet is incomplete evidence. Only publish a job after checking the destination posting.

Preferred order:
1. Recognized public ATS posting/API when the result resolves to a known supported ATS.
2. Schema.org `JobPosting` JSON-LD.
3. Public RSS/feed/API/sitemap when the site exposes one.
4. Permitted public HTML extraction.
5. Review queue when the page is blocked, ambiguous, stale, or cannot be parsed confidently.

Capture title, employer, location, description, source URL, application URL, posted/updated/expiry dates when present, employment type, experience when present, extraction method and confidence. Distinguish an actual job detail page from a search page, company homepage, aggregator page, expired posting or irrelevant article.

A page returning 403/429 remains blocked/deferred or needs review; it is not a verified job. Honour Retry-After, host cooldowns and bounded retries. No proxy rotation, CAPTCHA bypass, identity rotation or rate-limit circumvention. A failed fetch must not silently become a valid job based only on the Google snippet.

### 3.4 Shared ingestion and member matching

- Write verified observations to the existing shared `jobs` store with source `google_alerts` and provenance linking alert-rule ID, Gmail message ID reference, original result URL and extraction metadata.
- Reuse the current URL canonicalization and `canonical_opportunities` deduplication path. If an ATS collector later discovers the same vacancy, attach another observation to the same canonical opportunity instead of creating a duplicate.
- Evaluate each canonical opportunity independently against each member's saved preferences using the existing user-preference evaluation path.
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

### Engineering estimate

**6–9 focused engineering working days** for a production-ready owner-mailbox MVP, assuming one engineer works in a clean verified checkout, the correct public production hostname is available, the owner can configure the Google Cloud project and authorize the mailbox, and no external Google verification/security-assessment hold blocks launch.

| Work package | Estimate |
|---|---:|
| Preflight: inspect representative Alert email, map all 98 rules, verify Google Cloud/OAuth audience and public HTTPS endpoint | 0.5–1 day |
| Owner-only Gmail OAuth, encrypted token lifecycle, label binding and initial watch | 1 day |
| Pub/Sub topic/subscription integration, authenticated webhook, durable queue, daily watch renewal and reconciliation | 1–1.5 days |
| Gmail history/message sync, parser, per-message/result idempotency and rule mapping | 0.75–1 day |
| Safe URL resolution, host throttling/cache and extraction/verification tiers | 1–1.5 days |
| Shared DB ingestion, canonical dedupe and per-user evaluation integration | 0.75–1 day |
| Admin health/metrics, tests, silent historical backfill, pilot and production release checks | 1–1.5 days |
| **Total** | **6–9 days** |

A constrained proof-of-flow (connect one mailbox, receive one labelled push, parse one email and queue URLs) could be built in roughly **2–3 days**, but that is not production readiness and must not be described as a launch.

### Calendar risk outside engineering

- Gmail `gmail.readonly` is a restricted scope. Verification and/or a security assessment may be required depending on the chosen Google OAuth app classification and server-side data handling. External review time is not included in the 6–8 engineering days and is not under JobBeeper's control.
- Final production HTTPS hostname/routing is unresolved in the 20 November acceptance audit. If DNS/TLS/reverse-proxy work is required, add that work before the webhook can be enabled.
- Google Cloud project permissions/billing and Pub/Sub setup must be available. Do not create paid resources or change the consent screen until the owner has reviewed the setup and cost implications.
- The 98 Alert rules need an inventory and category mapping. If the list is not already exportable, initial manual classification may add time.

**Practical release expectation:** target an internal 5–10-rule pilot after the first 4–5 engineering days, then enable all 98 after 1–3 additional days of quality, duplicate, backfill and production checks. This is a planning estimate, not a guaranteed date.

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

**Execution status:** planning only. No source code, database schema, Gmail authorization, Google Cloud topic/subscription, production configuration or deployment has been changed as part of this plan.
