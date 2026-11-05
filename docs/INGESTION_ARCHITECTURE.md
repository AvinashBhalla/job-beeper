# Job Intelligence Ingestion Architecture

**Status:** Draft v0.1 — static repository audit, 2026-11-05  
**Branch:** `work/job-intelligence-foundation`  
**Basis:** `v2-live-radar` source tree and tracked configuration. The Oracle VM runtime has not yet been audited in this work session. Anything dependent on its persisted `/data/config.json`, current container, or live database remains unverified.

## 1. Architecture decision

Extend Job Radar V2 incrementally. Do not replace the current service or make LinkedIn a critical dependency.

The core system is a **federated, source-specific ingestion pipeline**:

```text
Source registry
   |
Independent source schedules
   |
Source adapters (per-source access and request policy)
   |
Fetch + source-level validation
   |
Normalize -> source observation
   |
Canonical identity / deduplication
   |
Persist job + source provenance
   |
Deterministic eligibility and match evaluation
   |
Notification ledger -> Telegram
   |
Dashboard / search / application workspace
```

A source failure, 429, malformed response, or stale feed must not stop other sources. LinkedIn should be isolated behind its own adapter and access-policy gate.

## 2. Current V2 architecture — repository facts

### Runtime and core modules

- FastAPI application: `v2/radar.py`.
- Persistence: SQLite at `/data/jobs.db` in Docker, using a named persistent volume.
- Runtime preferences: `/data/config.json`; protected config update endpoint uses a token stored in `/data/config_token` unless explicitly injected through the environment.
- Deployment: Docker Compose; production file `v2/docker-compose.yml`; isolated development file `v2/docker-compose.dev.yml`.
- Notifications: `v2/telegram.py`, with a durable notification ledger and retryable delivery handling.
- Canonical identity: `v2/dedupe.py`.
- Optional LLM enrichment: Gemini shadow extractor and provider router. The Gemini extractor is designed to be disabled by default and shadow-only; it must not control matching or delivery until separately evaluated and approved.
- Current API includes health, jobs, config, source status, latency summary, canonical opportunities, dedupe candidates, notification queue, and LLM shadow status.

### Existing SQLite entities

| Table | Current responsibility |
|---|---|
| `jobs` | One row per source observation; unique by `(source, source_job_id)`; stores title/company/location/URL, description, source posting time, discovered/first/last seen times, discovery latency and canonical link |
| `canonical_opportunities` | Cross-source canonical grouping and representative job |
| `job_evaluations` | Persisted deterministic match score, reasons, experience and alertability |
| `notification_ledger` | One delivery state per canonical opportunity, including attempts, next retry, claim, sent time and error |
| `source_runs` | Source run start/finish, seen/new counts and error |

The schema does not currently retain full raw HTTP responses. Keep source provenance and enough evidence to reproduce/inspect parsing; only persist raw payloads where permitted, necessary and subject to a retention policy.

### Existing collector inventory

| Source | Code/access path | Tracked default | Poll target | Notes |
|---|---|---:|---:|---|
| LinkedIn | Public guest jobs endpoint in `linkedin_collect` | Enabled in tracked prod config; disabled in dev config | 180 sec | 4-second minimum between all LinkedIn HTTP requests; 2 search targets per scan; 1 JD worker; 30-minute deep scan; global in-process cooldown after 429 |
| Naukri | Separate public relay JSON feed read by `naukri_collect` | Enabled in tracked prod and dev configs | 300 sec | Acquisition happens outside the API process; app reads the generated relay feed and preserves relay collection time |
| Instahyre | `/api/v1/job_search/` adapter | Disabled | 600 sec | One bounded search request; interface/freshness validation remains required |
| Greenhouse | Public Job Board API | Disabled | 900 sec | Three configured public boards; serial requests; 20-second timeout; board-level partial failure isolation |
| Ashby | Public Job Posting API | Disabled | 1800 sec | Two configured public boards; serial requests; 15-second timeout; board-level partial failure isolation |

The tracked `v2/config.json` has LinkedIn and Naukri enabled and Instahyre, Greenhouse and Ashby disabled. The tracked `v2/config.dev.json` enables Naukri only and disables notifications. **These are repository defaults, not proof of live runtime configuration.** Production runtime preferences persist separately on the VM.

### LinkedIn collection behavior in current code

The LinkedIn adapter currently calls:

`https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`

Current source code includes:

- A global in-process lock and minimum four-second spacing between LinkedIn HTTP requests, including detail enrichment.
- A 180-second minimum search scan interval.
- Four query families crossed with four configured locations (16 fast-search targets).
- Two first-page targets per scan, rotated across consecutive scans. At a clean 180-second cadence, one full rotation takes roughly 24 minutes; this is a schedule calculation, not a discovery guarantee.
- One deep page per fast target during a deep scan, no more often than every 30 minutes.
- A single JD enrichment worker.
- HTTP 429 handling with global cooldown, escalating fallback of 5/10/20/30 minutes, respecting a larger `Retry-After` value.
- The active search batch stops after a 429; deep pagination is skipped for that scan.

This is a conservative pacing strategy, **not evidence that LinkedIn will never rate-limit the collector**. The precise permitted access basis for this guest endpoint has not been established here. Do not add login bypass, CAPTCHA bypass, proxy/account rotation, or other circumvention. The VM audit must confirm whether LinkedIn is currently enabled and what 429 history it has seen.

### Scheduler and processing

- One asynchronous scheduler checks enabled sources every two seconds.
- Due source jobs are launched through `asyncio.to_thread`; a per-source in-memory `running` guard skips overlapping runs for that source.
- Source tasks can run independently; there is no durable general-purpose collection queue or cross-process lease today.
- Each completed collection passes through optional shadow enrichment, upsert/canonical linking, evaluation refresh, alertability refresh, and immediate Telegram delivery. A background notification worker retries the persistent queue.
- Source run history is stored in SQLite. Runtime `source_state` is in memory and resets on process restart.

## 3. Confirmed observability gaps and risks

1. **Ashby is omitted from three API views.** `COLLECTORS` includes Ashby, but `/api/source-status`, `/api/latency-summary`, and `/api/dedupe-candidates` hard-code source lists that omit it. The UI/API can therefore under-report an enabled Ashby collector.
2. **429 state is mostly in memory.** The cooldown clock, escalation streak, and target cursor are process-local. A restart resets them. Persisted `source_runs` does not record individual HTTP status counts or request budgets.
3. **429 API visibility needs a regression check.** The 429 helper adds cooldown details to runtime state, while the enclosing source exception handler replaces that state with a generic error payload. Confirm whether `/health` retains the cooldown fields after a real/test 429.
4. **Source run metrics are coarse.** `source_runs` stores jobs seen/new/error and start/finish timestamps, but not request count, pages/boards attempted, HTTP status distribution, Retry-After, parse rejects, updated-vs-new counts, or per-stage latency.
5. **No shared host-level request policy for all adapters.** LinkedIn has a dedicated global pacer; other adapters make direct HTTP calls with adapter-specific timeouts. Their current small allowlists limit load, but a 20–30-source expansion needs a common policy layer.
6. **No scheduler jitter or persistent due-time/lease.** On startup enabled collectors become due immediately. Single-process source guards do not protect against duplicate scheduling across multiple app replicas.
7. **API source lists drift from the collector registry.** The Ashby omission is a concrete example; source metadata must come from one registry.
8. **Current status is not runtime proof.** Repository config and old handover records cannot establish the deployed commit, live poll settings, current collector health, database counts or Telegram delivery state.

## 4. Target architecture

### 4.1 Source registry

Make one registry the source of truth for source metadata and API enumeration. Each source definition should include:

- Stable source ID and display name.
- Source family (ATS, job board, company career page, relay, licensed provider).
- Adapter function/module.
- Access method and policy/permission status (for example public documented API, partner API, approved provider, relay).
- Enabled/disabled state from runtime config.
- Poll interval and freshness class.
- Per-host request interval, maximum concurrency and maximum requests/pages/boards per run.
- Timeout, retryable status set, Retry-After behavior and maximum backoff.
- Cursor/checkpoint support and conditional-request capability (ETag/If-Modified-Since only when supported).
- Current health, last success, last error category and rate-limit state.

Never infer that an endpoint is permitted merely because it is reachable without authentication. An adapter must have a recorded allowed access method before production enablement.

### 4.2 Scheduler

Keep the first iteration single-instance on the existing VM, but make the scheduler observable and safe:

- Per-source `next_run_at`, scheduled interval and optional jitter.
- One active lease per source; lease expiry and stale-run recovery.
- Bounded global and per-host concurrency.
- Respect source-level request budgets and provider terms.
- Persist cooldown state and Retry-After when safe/appropriate; restart must not immediately forget a rate-limit pause.
- Do not schedule another run when the prior run/lease is still active.
- A source may be manually tested only through a safe, explicit operator action with source policy still respected; no bypass of rate limits.

A distributed queue/worker fleet is not the first step. Add it only when one process/VM becomes a measured bottleneck.

### 4.3 Adapter contract

Each adapter should accept a run context and return a typed result:

- `jobs`: normalized source observations or a raw source-specific DTO passed to a shared normalizer.
- `requests_attempted`, `pages_or_boards_attempted`.
- `http_status_counts`, `rate_limited`, `retry_after_seconds`.
- `source_cursor` / checkpoint when supported.
- `warnings`, `parse_reject_count`, `partial_success`.
- `started_at`, `finished_at`, `source_collected_at` if the upstream/relay supplies it.

Adapter errors must not erase previously discovered data or prevent other collectors from running. Partial success should be retained with per-board detail.

### 4.4 Canonical pipeline and provenance

```text
source schedule
  -> source adapter + request policy
  -> response/schema validation
  -> source observation normalization
  -> stable source key (source_id + source_job_id)
  -> canonical identity candidate matching
  -> upsert source observation + provenance
  -> deterministic role/location/experience eligibility
  -> explainable score and reasons
  -> notification ledger
  -> Telegram/dashboard
```

Keep source observations separate from canonical opportunities. A single opportunity can have multiple observation sources and source URLs. Never overwrite a good original posting time with a later `updated_at`, relative label, or uncertain timestamp. Preserve timestamp precision and distinguish unknown from date-only and exact-minute values.

### 4.5 Deduplication

Keep the current conservative behavior:

- Exact canonical URLs are strong evidence.
- Cross-source company/title/location similarity may suggest a candidate.
- Ambiguous identity remains separate rather than auto-merging.
- Source-specific IDs remain namespaced; identical numeric IDs across two boards must not collide.
- Track why an auto-link happened and allow manual review/repair.

### 4.6 Freshness and observability

Measure separate timestamps and durations:

| Metric | Definition |
|---|---|
| Source published time | Original time supplied by source, with precision |
| Source collected time | Relay/provider acquisition time, if supplied |
| First seen | First time our pipeline observed the job |
| Last seen | Most recent observation |
| Collection lag | First seen minus source published time, only when both are trustworthy |
| Processing lag | Persisted/evaluated time minus first-seen/collection time |
| Notification lag | Telegram sent time minus first-seen time |
| Run duration | Finished minus started |
| Source freshness | Time since most recent successful run |
| Coverage yield | Valid, new and matched observations per source run |
| Reliability | 429, 4xx, 5xx, timeout, parse-reject and partial-failure counts |

Do not infer collection freshness from page render speed or from a source card's marketing metric. Keep p50/p90 and sample counts visible; do not report percentiles from insufficient samples.

### 4.7 Storage evolution

Retain SQLite for the current single-user VM deployment. Add schema only when a specific measurement or capability needs it. Candidate additions:

- `collector_runs` (or an evolved `source_runs`) with run ID, source ID, trigger, scheduled/actual start, finish, outcome, request counters, HTTP status counts, parse counters, inserted/updated/duplicate counts, cooldown and sanitized error category.
- `source_runtime_state` with last success, next due time, cursor, cooldown-until, last error category and lease owner/expiry.
- Optional `source_observations` only if a separate observation table materially improves provenance beyond the current `jobs` table.

Keep API keys and tokens out of these tables and all logs. Never store session cookies or credentials as crawler state.

## 5. Source expansion strategy

Priority order:

1. Stable, documented public ATS job-board endpoints and employer career pages (begin with a small validated board allowlist).
2. Additional ATSs with a documented public interface and predictable stable IDs/timestamps.
3. Relay/aggregator feeds where acquisition permissions and provenance are clear.
4. Licensed data APIs or official partner integrations when coverage justifies their cost.
5. Sources requiring browser automation only after policy, reliability, maintenance and access method are validated.

Potential source families to assess (not yet approved/implemented): Greenhouse, Ashby, Lever, SmartRecruiters, Workable, Recruitee, Teamtailor, Workday, iCIMS, SuccessFactors, Oracle Recruiting, Darwinbox, Keka, Freshteam, BambooHR, Jobvite, Taleo, Avature, Rippling, Instahyre, Hirist, Cutshort, Wellfound and Naukri. Availability, endpoint stability, terms and freshness need separate validation for each.

LinkedIn remains a separately gated source. Do not make product coverage, scheduler progress or notification delivery depend on it.

## 6. Security, compliance and operational controls

- Respect each provider's documented terms, robots/publishing interfaces, request budgets and access requirements.
- No authentication bypass, CAPTCHA bypass, anti-bot evasion, proxy/account rotation or automated account creation.
- Do not publish private app source, runtime config, profile preferences, API keys, session material or candidate private data in the public Naukri relay.
- Restrict config updates and dashboard access; bind development service to loopback and use SSH tunneling.
- Use bounded timeouts, capped retries, jitter and Retry-After. Avoid retry storms.
- Validate payload types and cap descriptions/response sizes.
- Keep optional LLM enrichment disabled/shadow-only until measured quality and cost gates pass. LLM output cannot determine source permissions, directly alter raw observations, or send applications.
- Telegram delivery is at-least-once with an idempotent ledger; avoid duplicate opportunity sends.

## 7. Build sequence and release gates

### Gate 0 — read-only runtime baseline (required before edits to deployed behavior)
Confirm production/dev checkouts and commits, worktree status, container/volume mapping, runtime config safe fields, per-source health, last runs, database counts, notification ledger counts, and whether production/dev are actually isolated. Do not print credentials.

### Gate 1 — observability correctness
- Replace duplicated hard-coded source lists with the central registry.
- Add Ashby to source status, latency and dedupe candidate views.
- Preserve rate-limit status after a 429 in the safe health/status payload.
- Add regression tests for enabled/disabled state, last run, cooldown, and every registered source.
- Keep collector behavior and polling settings unchanged.

### Gate 2 — source/run telemetry and scheduler controls
- Persist structured run statistics and source health state.
- Add jitter, bounded concurrency and per-host request budgets with tests.
- Add conditional/incremental polling only to endpoints that document/support it.
- Do not increase request rates until a measured baseline exists.

### Gate 3 — one additional structured ATS adapter
- Pick one source after live runtime baseline and endpoint/terms validation.
- Dev only, source allowlist small, notifications off.
- Test stable IDs, timestamp precision, pagination/updates, partial board failure, duplicate behavior, and no cross-source collisions.
- Compare actual new jobs, match yield, freshness and errors.

### Gate 4 — expand source coverage
Add one adapter at a time with explicit source validation and per-source acceptance tests. Target 20–30 useful sources only after the maintenance burden and coverage yield are known.

### Gate 5 — improved matching and referral intelligence
Strengthen explainable match reasons, skill extraction and referral discovery only after the ingest/dedupe/freshness pipeline is reliable. Referral outreach remains user-approved; do not automate LinkedIn messaging.

## 8. Current blockers / unknowns

- Oracle production/dev actual checkout and running commit not confirmed in this session.
- Live source enabled flags, poll intervals and Telegram presence not confirmed.
- Actual 24-hour and seven-day discovery/notification lag and source yield are unknown.
- Live LinkedIn 429 history and current cooldown state are unknown.
- PR #35 is an existing open draft validation PR for Gemini shadow mode; it must not be merged/deployed without its own CI/dev verification. Keep this foundation work isolated from that PR.
