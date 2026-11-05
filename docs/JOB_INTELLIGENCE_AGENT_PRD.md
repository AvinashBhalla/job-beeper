# Personal Job Intelligence Agent — Product Requirements Document

**Status:** Draft v0.1  
**Date:** 2026-11-05  
**Project:** Personal, single-user job discovery and referral intelligence platform  
**Implementation foundation:** Existing Job Radar V2 (FastAPI, SQLite, Docker, Oracle VM, Telegram)

## 1. Product summary

Build a personal AI-assisted job intelligence agent that continuously discovers relevant job opportunities across 20–30 permitted job sources, consolidates duplicate listings, explains why each role matches the candidate profile, and delivers fresh, low-noise alerts.

The platform should also help identify relevant employees, recruiters and hiring managers for referral research. A later module may monitor public hiring posts and connect them to canonical job opportunities.

The product is not being monetized at this stage. The first goal is a dependable system for one candidate.

## 2. Problem

Job opportunities are spread across ATS platforms, job boards and individual company career pages. Manually checking many sources is slow; alerts from multiple providers can duplicate the same role; source posting times are inconsistent; role labels and descriptions may be incomplete; and a source outage should not silently stop the entire job search.

The product must optimize for **useful coverage, trustworthy freshness, and relevant delivery**, not raw request volume or a copied JobBeeper UI.

## 3. Product goals

1. Discover relevant jobs independently across multiple source families.
2. Preserve source, original URL, stable source ID and trustworthy source timestamps.
3. Consolidate cross-source duplicates without merging ambiguous jobs incorrectly.
4. Match using deterministic, explainable role/location/experience rules, with skills enrichment as a supporting feature.
5. Measure source-to-discovery, processing and notification latency separately.
6. Send one low-noise Telegram alert per canonical opportunity.
7. Provide a searchable dashboard and source-health view.
8. Keep each collector independent so one provider's errors or rate limits do not stop other sources.
9. Later add referral intelligence and hiring-post intelligence without coupling them to the ingestion path.

## 4. Non-goals for the first milestone

- No automatic job applications or form submission.
- No automated LinkedIn messaging, connection requests or referral outreach.
- No bypass of LinkedIn or any other provider's access controls, CAPTCHA, rate limits or authentication requirements.
- No multi-tenant SaaS, billing, user registration or monetization.
- No large distributed crawler fleet, Kafka, Kubernetes or microservices unless measured scale requires them.
- No LLM authority over source permissions, candidate eligibility, match score, or notification delivery.
- No requirement to reproduce JobBeeper's private implementation.

## 5. Primary user and workflows

### Primary user
One candidate with a configurable role, skills, location, experience and work-mode profile.

### Main workflow
1. Source adapters collect jobs on their own schedules.
2. The pipeline validates and normalizes records.
3. Dedupe logic links cross-source copies into canonical opportunities.
4. Deterministic matching evaluates role, location, experience, freshness and profile skills.
5. The dashboard exposes the job, source links, freshness evidence and match reasons.
6. The notification ledger queues alertable canonical opportunities.
7. Telegram sends the alert and records delivery status.

### Referral workflow (later)
1. User opens a canonical opportunity.
2. The system finds relevant public/professional profiles or hiring signals through approved sources.
3. It ranks likely contacts using role, team, location and hiring relevance.
4. It drafts a referral message from candidate/job/contact context.
5. User reviews and approves any outreach manually.
6. The system tracks user-managed referral status and follow-up.

## 6. Functional requirements

### FR-1 — Source registry
The system shall maintain a registry with source ID, source type, access method, permission/policy state, adapter, enablement, poll interval, concurrency and request budget, timeout, retry/backoff, freshness expectation and health.

Acceptance:
- Every registered source appears consistently in status, latency and dedupe APIs.
- An unknown/unapproved access method cannot be enabled silently.
- Source defaults are opt-in unless a validated migration/explicit configuration says otherwise.

### FR-2 — Independent collection
Each source shall have its own schedule, state, run guard and error handling.

Acceptance:
- A 429 or malformed payload from one source does not stop any other source.
- No source overlaps its own run.
- The scheduler records start, finish, outcome and actual request count.
- Cooldown/Retry-After is honored and observable.
- Retries are bounded, jittered and source-aware.

### FR-3 — Normalized source observation
Every valid job observation shall include:
- source ID and source job ID;
- company and title;
- location and work mode when known;
- canonical/source URL;
- description or summary when available;
- source-published timestamp and precision;
- collected/discovered time and provenance;
- first-seen and last-seen times.

Acceptance:
- Unknown timestamp is stored as unknown, never fabricated.
- Date-only timestamps remain date precision and are not used for second-level latency claims.
- Original apply URL is preserved.

### FR-4 — Cross-source deduplication
The system shall maintain source observations and canonical opportunities separately.

Acceptance:
- Exact canonical URLs can be strongly linked.
- Similar title/company/location candidates require corroborating evidence.
- Ambiguous matches stay separate.
- Duplicate observations do not create duplicate Telegram alerts.
- Each merge/link records a reason and confidence/method.

### FR-5 — Matching and ranking
Matching shall evaluate:
- role/title relevance;
- location and remote-work semantics;
- experience range and required/preferred distinction;
- profile skills;
- recency and source timestamp precision;
- candidate exclusions and preferences.

Acceptance:
- Eligibility gates are deterministic and explainable.
- Every score has reasons.
- Missing/conflicting fields are represented as unknown/uncertain.
- LLM extraction can enrich missing fields in shadow mode but cannot decide eligibility alone.
- Low-confidence matches do not become alerts solely because an LLM produced a high score.

### FR-6 — Freshness and source observability
The system shall show per-source:
- enabled state;
- last run and last success;
- run duration;
- jobs fetched, new, updated, duplicate and rejected;
- 429/4xx/5xx/timeouts and Retry-After;
- next scheduled run and cooldown state;
- p50/p90 collection lag with sample count.

Acceptance:
- LinkedIn UI/render latency is never confused with ingestion freshness.
- A stale source is visibly distinct from a healthy source with zero new jobs.
- Disabled sources are distinguishable from failing sources.
- Ashby and every new adapter are represented in all status/latency APIs.

### FR-7 — Notification delivery
Telegram remains the first delivery channel.

Acceptance:
- One canonical opportunity is sent once unless deliberately reactivated by new evidence/policy.
- Retryable Telegram errors use bounded retry and Telegram Retry-After.
- Invalid credentials do not loop indefinitely.
- Delivery status is persisted and visible.
- A source failure cannot corrupt the notification ledger.

### FR-8 — Dashboard/search
Dashboard shall expose a fresh feed, canonical job detail, all source observations, search, match reasons, source health, notification state and stale/closed indicators.

Acceptance:
- Search operates over the server-side job index or bounded result set, not only a small fixed HTML snapshot.
- The feed can be sorted by discovery freshness and match score independently.
- The UI clearly distinguishes published, discovered, first-seen and last-seen times.

### FR-9 — Referral intelligence (later phase)
Find relevant contacts from permitted public/professional sources and provide explainable rankings.

Acceptance:
- Contact identity confidence and source provenance are displayed.
- No outreach is sent without user approval.
- No unauthorized LinkedIn scraping or messaging automation.

### FR-10 — Public hiring-post intelligence (later phase)
Identify public posts that indicate hiring intent, extract company/role/author/time/link, and connect to existing canonical opportunities.

Acceptance:
- Post source and timestamp are retained.
- Role is not created as a job vacancy without sufficient evidence.
- Author identity/contact claims are never inferred from weak matches.

## 7. Non-functional requirements

- **Reliability:** independent source failure domains; no global collector stop on one adapter exception.
- **Freshness:** measure before promising an SLA; set target bands only after a baseline.
- **Safety/compliance:** documented access method per source; respect request limits and terms.
- **Security:** secrets only in runtime environment/secret storage; no secrets in Git, logs, relay feed or database.
- **Auditability:** source provenance, timestamps, dedupe decisions and notification decisions retained.
- **Cost:** single-user first; pay for external providers only when they materially improve useful coverage/freshness.
- **Maintainability:** typed adapter contract, fixtures for each provider, source-specific tests and clear runbooks.
- **Performance:** SQLite and one VM remain acceptable until measured bottlenecks justify migration.

## 8. MVP scope and delivery phases

### Phase 0 — Runtime baseline
Read-only audit of production and dev: branch/commit, dirty worktrees, running containers, volumes, runtime source settings, recent source runs, database counts, 429 status, notification ledger and Telegram credential presence (boolean only).

Exit criteria: actual production/dev topology is verified; no ambiguous config or data-volume mapping remains.

### Phase 1 — Observability correctness
Central source registry; ensure all sources (including Ashby) appear in status, latency and dedupe APIs; persist/retain cooldown fields; add run/request metrics and regression tests.

Exit criteria: tests cover each registered source and rate-limit/cooldown display; no collection behavior or production poll rate changed.

### Phase 2 — Scheduler and adapter contract
Introduce typed run results, per-source request budgets, jitter, bounded concurrency, persistent run state and incremental checkpoints where available.

Exit criteria: source failure isolation, bounded retry, no overlapping same-source runs, and visible source freshness.

### Phase 3 — One new ATS adapter
Pick one source after endpoint/terms validation. Development only, small allowlist, notifications off.

Exit criteria: end-to-end discovery → normalize → dedupe → persist → evaluate → dashboard, with accurate timestamp provenance and regression fixtures.

### Phase 4 — Expand to 10–15 useful sources, then towards 20–30
Prioritize sources with stable documented interfaces, usable job descriptions, stable IDs and fresh publication metadata. Evaluate coverage yield and maintenance cost per adapter.

### Phase 5 — Matching and product experience
Improve skill/experience enrichment, search, explainability and feed quality after the ingest pipeline is measured.

### Phase 6 — Referral and hiring-post intelligence
Add as separate modules after collection/notification reliability is established.

## 9. Success measures

Do not use request volume as a success metric. Measure:
- unique relevant opportunities per source per day/week;
- source coverage by company/ATS;
- proportion of new observations with trustworthy publication time;
- p50/p90 publish-to-first-seen lag (only timestamped records);
- p50/p90 first-seen-to-notification lag;
- duplicate alert rate;
- false-positive/misclassified-role rate;
- 429 and error rate by source;
- successful-run freshness and stale-source duration;
- manual review workload;
- external provider cost per useful new opportunity.

## 10. Decisions still needed after VM audit

- Current live production and dev configuration and state.
- Whether current LinkedIn guest endpoint should remain enabled given its permitted-access basis; no anti-limit workaround is acceptable.
- First next ATS connector (select based on user target employers and verified API capabilities).
- Whether the first source-registry observability patch should be included as a narrowly scoped PR separate from the draft Gemini PR.
- Whether skill extraction shadow mode has passed its evaluation and should remain disabled, be validated on dev, or be retired.
