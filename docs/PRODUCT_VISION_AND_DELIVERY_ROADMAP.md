# JobBeeper — Product Vision, Architecture and Delivery Roadmap

**Owner direction:** Build an end-to-end job-search product, not only a job alert bot.
**Last reviewed:** 2026-11-09 (Asia/Kolkata)
**Status:** Living source of truth. This document supersedes conflicting feature-order recommendations in older roadmaps; those files remain useful for implementation detail and engineering history.

## 1. Product vision

JobBeeper should help a candidate through the complete job-search loop:

1. **Discover:** Find relevant, fresh jobs across job boards and public employer career sites.
2. **Decide:** Explain fit, freshness and evidence; flag closed, stale or reposted jobs.
3. **Prepare:** Tailor a truthful resume and supporting answers to the specific job.
4. **Apply:** Reduce repetition with reusable profile facts and assisted form filling.
5. **Progress:** Track applications, interviews, outcomes, referrals and follow-ups.
6. **Learn:** Use user feedback and outcomes to improve matching, resume positioning and search strategy.

The product promise is **relevance and actionability, not the largest raw job count**.

### Product principles

- **Human authority:** AI researches, scores, drafts and prepares. The user approves consequential actions.
- **Truthful representation:** Resume and form answers must be grounded in user-provided facts. Never invent employers, degrees, dates, metrics or skills.
- **Evidence before confidence:** Show sources, timestamp precision, match reasons and contact provenance. Label inferred information.
- **One shared discovery engine:** Fetch a public job once and evaluate it independently for each user. Never run a scraper/scheduler per user.
- **Private by default:** Candidate profiles, resumes, answer banks, applications, contacts and notification destinations are user-owned.
- **Permission-aware automation:** Use public endpoints, official integrations or user-authorized browser actions. Never bypass login walls, CAPTCHAs, rate limits or access controls.
- **Small, reversible engineering:** Prefer a few well-tested modules and explicit adapters over speculative frameworks, microservices and dependencies.
- **Fast but safe releases:** Ship independently verifiable slices. Never enable an unverified source or send historical inventory as a new-job alert.

## 2. What the reference repositories teach us

### Career-Ops — evaluation and application preparation

Reference: https://github.com/career-ops-hq/career-ops

Career-Ops is a local-first AI job-search agent. Adopt these patterns:

- Re-check whether a posting is still open and record repost observations before the user spends time tailoring a CV.
- Separate hard blockers from weighted role-fit evidence. Explain requirements sourced from the JD versus inferred/estimated criteria; keep scores explainable and overrideable.
- Connect job evaluation to tailored ATS-readable CVs, cover letters and application answers.
- Ground generated CV claims in the user's source resume/profile. Make each version reviewable.
- Research relevant hiring managers, recruiters or team peers; explain why a contact may be relevant.
- Draft referral/outreach messages; do not send automatically.
- Learn from rejection patterns, interview conversion and application outcomes.
- Adopt privacy/data-minimization. JobBeeper is hosted, so enforce tenant isolation, secure storage, export and deletion rather than pretending it is local-first.

**Do not copy its runtime architecture wholesale.** Its CLI/local-file design is not a substitute for JobBeeper's hosted, continuously running, multi-user architecture.

### Career-Ops Extension / Apply Factory — browser-assisted applications and learning

Reference: https://github.com/itshoax/career-ops-extension

The inspected README describes an extension around Career-Ops that adds assisted form filling, a persistent question/answer knowledge base, learning events for new/reused/corrected answers, a review queue, and a human checkpoint: the user reviews the form and clicks Submit.

Adopt:
1. A per-user **Application Answer Bank** with canonical question intent, answer, type, confidence, source, last-confirmed date and usage history.
2. User corrections override old answers.
3. Inferred answers remain pending until confirmed.
4. Job/company-specific free-text answers are not reusable generic facts.
5. A first-party browser companion may fill supported fields and capture a pre-submit snapshot, but must pause for review.

Do not make JobBeeper depend on Kimi Webbridge prompts, brittle LinkedIn CSS selectors or unofficial scraping. Build a small Manifest V3 companion only after the web app's application and answer-bank APIs are stable.

### Combined lesson

Career-Ops improves the **quality of the candidate's decision and application**. Apply Factory improves the **repetitive mechanics and memory of form completion**. JobBeeper should connect both to its shared discovery engine and per-user application history. Adopt patterns, not copied code; perform a separate license/dependency review before any code reuse.

## 3. Architecture — keep the good foundation

    Public/permitted source adapters
                |
                v
    Shared normalized jobs + canonical opportunities
                |
                +--> User A preferences --> evaluations --> alerts
                +--> User B preferences --> evaluations --> alerts
                +--> User C preferences --> evaluations --> alerts

    User-owned applications / resume versions / answer bank / contacts / follow-ups

### Shared/system-owned data

Employer/ATS board registry and verification evidence; source adapters, schedules, rate limits and health; normalized job observations and canonical opportunities; public job details and original apply URLs; aggregate operational metrics.

### User-owned data

Account/profile/preferences; per-user evaluations and feedback; applications/status/notes/follow-ups/outcomes; source resume, parsed facts and tailored versions; answer bank/correction history; referral/contact notes and outreach drafts; Telegram connection and future email integrations.

Every user-owned query must scope by authenticated session user ID. Never trust a user ID supplied by the browser.

### Architecture decisions

| Area | Current decision | Revisit when |
|---|---|---|
| Job collection | Shared collectors; one fetch serves all users | Not changed for user growth alone |
| ATS integrations | Explicit provider registry + provider-specific adapters/tests | A real second use justifies a shared helper |
| Employer discovery | Global automated public-board discovery and provider-specific verification; manual scan is an exception tool | Improve recall without violating access controls or misrepresenting coverage |
| Runtime | Existing FastAPI application | Split only for demonstrated independent scaling/deployment needs |
| Database | SQLite WAL, serialized writes and busy timeout for single-host beta | PostgreSQL before lock contention, multi-instance deployment or recovery needs exceed SQLite's safe envelope |
| Browser automation | Optional companion, separate from collectors | After server-side answer-bank/application APIs exist |
| AI | Deterministic matcher remains authoritative; LLM enrichment shadow/opt-in | Promote only with measurable evaluation lift |

Do not migrate to PostgreSQL, Redis, Kafka, Celery or microservices just because the future product is ambitious. The immediate architectural correction is data ownership and API contracts, not more infrastructure. Measure lock waits, source-run concurrency, DB size and recovery time first.

## 4. Current implementation truth

| Area | Status | Gap |
|---|---|---|
| Ingestion | LinkedIn, Naukri, Instahyre, Greenhouse, Ashby, Lever, Workday, SmartRecruiters, Workable, Keka and Darwinbox collectors exist in integration candidate | Per-employer boards still need verification/activation; availability is not universal |
| Employer discovery | Public careers scan, ATS detection, board registry, verify/review/activate | Some discovered ATS families have no collector |
| Source safety | Request budgets, rate limits, dedupe, telemetry, first-board baseline | Production yield/latency soak remains |
| Matching | Deterministic match + per-user preferences/evaluations | Improve role taxonomy, hard blockers, explainability and calibrated confidence |
| Authentication | Cookie sessions, Argon2id, roles, CSRF, login limits | Production admin bootstrap and real two-user test remain |
| Telegram | Per-user linking and notification ledger exist in candidate | Real production link/delivery test remains |
| Resume parsing | PDF/DOCX parser returns conservative preference suggestions | No resume vault or tailored-CV generation |
| Application tracker | Basic server-owned per-user application records and CRUD released 2026-11-09 | Richer interview stages, follow-ups, reminders and outcome learning remain P2 |
| Referrals | Design only | Contact discovery/provenance, drafts and follow-ups not implemented |
| Assisted apply | Design only | No answer bank or browser companion |
| Auto-apply | Not implemented | Must remain off pending a separate permission/safety gate |

The mainline V2 collector registry includes 11 sources: LinkedIn, Naukri, Instahyre, Greenhouse, Ashby, Lever, Workday, SmartRecruiters, Workable, Keka and Darwinbox. Per-employer board verification and recurring coverage remain separate from having a provider adapter. Recruitee (draft PR #59), Personio (draft PR #60), Teamtailor (draft PR #61) and Breezy HR (local feature branch) have default-off candidate adapters, not mainline/deployed integrations. BambooHR and Rippling remain discovery-only. See the global discovery design and source-health guide linked in the documents section below.

## 5. Owner-approved priorities — 2026-11-09

This priority order was explicitly confirmed by the owner from the product-priority screenshot on 2026-11-09. It supersedes conflicting ordering in older notes. Work should be parallelized where independent, but a P1/P2 feature must not displace unresolved P0 reliability and discovery work.

| Priority | Feature | Intended outcome |
|---|---|---|
| P0 | Reliable notifications and better matching | Fresh, relevant notifications delivered only to the matching user; robust no-backlog and per-user isolation. |
| P0 | Source health, latency and rate-limit handling | Explainable operational health, board-level freshness, persisted cooldown and visible coverage gaps. |
| P1 | Job legitimacy, stale posting and repost detection | Verify employer/public posting evidence, recheck open/closed state, detect reposts and suppress stale/duplicate opportunities. |
| P1 | Explainable job-fit scoring | Show hard blockers, evidence-based fit factors, sources and uncertainty instead of an unexplained percentage. |
| P1 | Resume vault and job-specific resume customisation | Private user-owned source resumes, fact provenance and truthful reviewed tailored versions. |
| P1 | Reusable application answer bank | Per-user answers with source, confirmation, confidence and correction history; inferred/sensitive answers require review. |
| P2 | Referral discovery and outreach drafts | Evidence-backed contact relevance and editable drafts; no fabricated identity/contact details or automatic sending. |
| P2 | Browser-assisted application filling | Fill only supported fields on a user-authorized page, show preview and stop before Submit. |
| P2 | Application tracking, interview follow-ups and outcome learning | Track applications, stages, notes, reminders and outcomes; learn only from user-authorized feedback. |

**Auto-apply remains human-approved initially.** The system may prepare and fill, but each application must be reviewed and explicitly approved by the user before submission. It must never bypass CAPTCHA, login/access controls, employer constraints or rate limits, and must not submit legal, visa, salary or demographic declarations without direct review.

### P0 — Reliable notifications, matching and source operations

- Prove the complete source → normalized job → canonical dedupe → per-user evaluation → per-user notification path with two independent user contexts.
- Preserve the silent first-inventory baseline. Never replay old jobs after enabling a board or a user's notification opt-in.
- Verify match explanations, hard exclusions, profile changes, notification idempotency, retry safety and no cross-user leakage.
- Measure publication-to-discovery, discovery-to-match and match-to-notification separately. Only calculate posting latency where the provider supplies a defensible published timestamp; keep first-seen and update timestamps distinct.
- Move to global public employer-board discovery so new companies are found without manual company-by-company configuration. Keep manual add/correct as a fallback only.
- Schedule verified boards independently with jitter, bounded concurrency, host budgets, persisted next-poll/cooldown and provider-specific retry handling.
- Preserve 429 handling and never increase request volume to chase an arbitrary two-minute target. Show overdue/blocked boards explicitly.
- Run a 24–72 hour source/DB soak and record errors, duplicates, false matches, coverage and delivery.

**P0 acceptance:** every active board has provenance, verification evidence, a silent first poll, at least two successful deduplicating polls, observable freshness and rate-limit state. A user can confirm they receive only their own matching notification in a dedicated test channel. The dashboard reports coverage limits rather than implying complete platform-wide coverage.

### P1 — Trustworthy jobs and explainable decisions

**Job legitimacy, stale and repost detection**
- Retain original employer/ATS source URL and discovery evidence.
- Recheck that the public board still lists a job; distinguish closed, stale, temporarily inaccessible and removed listings.
- Compare title/company/location/description/posting identity and dates to identify edits, duplicates and reposts.
- Never call a listing legitimate solely because an HTTP request succeeded. Record the evidence and last verification time.

**Explainable job-fit scoring**
- Separate hard blockers from weighted evidence.
- Explain JD-stated requirements versus inferred criteria; preserve provenance and confidence.
- Show why the role matches or fails the saved profile and allow user feedback without hiding the underlying evidence.

**Resume vault and truthful job-specific customisation**
- Add private per-user source resume documents and structured candidate facts.
- Extract employers, titles, dates, education, skills, projects and quantified achievements with provenance.
- Let the user correct/confirm facts without overwriting the original.
- Generate ATS-readable versions from the job description and confirmed facts; show a change summary and unsupported/missing requirements.
- Save reviewed versions against the relevant application and support export/deletion, private storage and retention controls.

**Reusable answer bank**
- Store canonical questions, answers, type, confidence, evidence/source, confirmation date and use history per user.
- User corrections override earlier answers. Inferred values remain unconfirmed until approved.
- Keep company/job-specific answers separate from generic reusable facts.
- Unknown answers remain blank. Sensitive/legal questions require direct confirmation.

### P2 — Application progress, referrals and assisted applications

- Extend the server-owned application tracker with interview stages, status history, notes, dates, outcomes and follow-up tasks.
- Identify public professional contacts with role, employer, evidence URL, source, confidence and last-checked timestamp.
- Draft referral and follow-up messages; user edits and sends. Add email OAuth only with explicit consent and minimal scopes; start with drafts, not send actions.
- Build browser assistance after application and answer-bank APIs are stable. Fill the user's active, authorized form and preview every field; never click Submit in the initial release.
- Learn from user-confirmed corrections and outcomes with a transparent purpose and consent.

### Existing application tracker status

The basic server-owned application tracker (per-user application records and browser API migration) was previously released according to the 2026-11-09 P0.5 release note below. The owner's P2 priority refers to the broader lifecycle: interview follow-ups, outcome learning and a richer history, not a reason to rebuild the basic CRUD feature.

## 6. Suggested data model evolution

- Existing shared layer: jobs, canonical opportunities, source runs/board registry.
- Existing identity/profile layer: users, sessions, user_preferences, user_job_evaluations.
- Existing alerts: user_notification_settings, user_notification_ledger, Telegram link tables.
- Released basic application table: `user_applications(user_id, canonical_opportunity_id, job_id, applied_at, status, notes, created_at, updated_at)`. Richer lifecycle history, interview follow-ups and outcome learning remain future work. Canonical ID is reconciled through retained job_id after a dedupe rebuild; unique user+canonical key prevents duplicate app rows.
- Later: user_resumes, resume_facts, resume_versions, application_answer_bank, answer_learning_events.
- Later: followup_tasks, contacts, application_contacts, outreach_drafts, outreach_events, email_integrations.

Use foreign keys, user-scoped indexes, unique constraints and additive migrations. Add a table for a distinct responsibility; do not build a generic workflow engine for one feature.

## 7. Product quality metrics

Track source success/429/cooldown; unique jobs per successful poll; duplicate/canonical merge rate; posting-to-discovery latency with timestamp precision; discovery-to-alert latency; match feedback; saved/applied conversion; application-stage conversion/time; resume correction rate; referral draft/response rate; form-fill correction rate.

Report sample size and timestamp precision. A source returning 1,000 old jobs is not necessarily better than one returning 20 new, relevant jobs.

## 8. Supporting architecture and operational guides

- [Global ATS discovery and coverage architecture](GLOBAL_ATS_DISCOVERY_AND_COVERAGE_ARCHITECTURE_2026-11-09.md) — removes routine per-company board configuration while documenting real public-feed limitations.
- [Source Health explained and UX redesign](SOURCE_HEALTH_EXPLAINED_AND_UX_REDESIGN_2026-11-09.md) — plain-English explanation of the existing metrics and proposed coverage/health separation.
- [36-platform source coverage roadmap](ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md) — provider-by-provider implementation and evidence.

## 9. Engineering and release rules

- Keep the current integration branch as source of truth until reviewed merge/deploy.
- Commit one coherent feature/fix at a time; keep worktree clean after pushes.
- Run focused tests, full V2 suite and GitHub CI on exact pushed SHA.
- Keep production/dev databases, notification credentials and ports isolated.
- Before production: online SQLite backup, checksum, integrity check, migration rehearsal on copy, tagged image, rollback image/config and health check.
- New source flow: discover → verify public endpoint → admin review → activate → silent first inventory → second-poll dedupe → alert eligibility → telemetry.
- Never use production Telegram to test unverified connectors.
- Apply Ponytail after a feature stabilizes: understand code/tests first, simplify only changed scope, preserve behavior, separate refactors from feature commits.
- Avoid speculative factories, generic frameworks, extra packages, duplicate job stores, per-user scrapers and premature infrastructure.
- Update this roadmap and both handover files whenever plans/status change.

## 10. Current next actions (historical checkpoint, reviewed 2026-11-08)

1. Production release is deployed: config v15, seven added ATS sources active across 10 verified boards, silent initial baseline complete, and notifications restored. Continue a measured source/DB soak; preserve provider rate limits.
2. Provision the first production admin interactively using `python -m v2.auth_admin create-admin --email bawejaavichal01@gmail.com` inside the live container. This copies the existing global candidate preferences exactly once. Do not store the password in shell history or docs.
3. Confirm the actual HTTPS public origin. Google OAuth remains disabled until the owner supplies a Google client ID/secret and registered callback. OAuth must create member accounts only.
4. Configure per-user Telegram bot username, webhook secret and public webhook URL; link the owner's private chat and test only after explicit user opt-in. Legacy global Telegram credentials do not prove per-user delivery.
5. Board-level disable UI is deployed (PR #54, image `00820f0`). Use it from admin Source Health; no board was disabled during rollout.
6. Finish the server-owned Application Tracker P0.5 branch before a wider beta. It replaces browser-only Applied state, imports legacy localStorage idempotently, and is awaiting full-suite/exact-SHA CI and production-data canary; not yet deployed.
7. Design resume vault/tailoring using fact provenance and human review, then the answer bank before the browser companion. Keep auto-submit gated and off.

**Reminder:** a source adapter in code is not a verified active production connector. A roadmap feature is not implemented until API, UI, tenant tests and release evidence exist.

### Latest release state — 2026-11-08

- Production release `00820f0` is deployed. The admin workspace now supports per-board disable, preserving other boards under the same ATS. All 10 verified production boards remain active; no board configuration was changed during deployment.
- The first-admin account is not yet created; use the secure interactive bootstrap recorded in `JOB_RADAR_HANDOVER.md`. Google OAuth and member Telegram are not configured until owner-supplied credentials/public HTTPS routing are available.
- Continue measured source soak and prioritize P0.5 server-owned application tracking next.

### P0.5 implementation checkpoint — 2026-11-09

The current feature branch adds per-user server-owned application records and the dashboard API migration. It is not in production until exact full V2 tests, GitHub CI, data-copy canary and a separate backup-backed deploy have passed. The local full V2 suite has passed 400 tests in 307.495s; exact-head GitHub CI and production-data canary are still pending. The feature is not deployed. Detailed implementation/release notes are in `JOB_RADAR_HANDOVER.md`.

### 2026-11-09 — P0.5 verification boundary

- PR #55 exact-head CI passed and the local full V2 suite passed 400 tests. The production-data copy canary started successfully with collectors/notifications off; schema created, health/dashboard 200, unauthenticated application API 401, DB counts preserved and SQLite integrity `ok`.
- A dedicated two-synthetic-user canary API smoke was blocked by the remote execution safety gate. Matching owner-isolation/CRUD tests passed in local and GitHub suites. PR #55 is still open/not deployed; do not promote without an approved release decision and a documented way to complete or waive that canary smoke.

### 2026-11-09 — P0.5 tracker released

- PR #55 is merged and production image `job-radar-prod-canary:6e5becb` is live. The Applied tracker is now server-owned and per-user, with idempotent localStorage import and canonical dedupe reconciliation. Local and exact-head CI passed 400 tests; production table migration/data integrity/auth boundary verified.
- Production currently has zero accounts. Owner must run the secure interactive first-admin CLI command documented in `JOB_RADAR_HANDOVER.md` before signing in. Google OAuth and per-user Telegram need owner-supplied public HTTPS routing and credentials; they remain disabled.
- Next priorities: finish owner onboarding, verify legacy Applied import in the owner browser, source soak/Workday page depth, then resume vault/factual tailoring and answer bank.

### Workday source scope note — 2026-11-09

The production NVIDIA Workday connector currently ingests one 20-job page per 120-second poll and fetches at most 20 details. It is active and healthy but intentionally partial. The public CXS endpoint is undocumented; empirical behaviour suggests 20 is a hard page size and some tenants cap totals or repeat data. Do not increase request volume until offsets 20/40, duplicate-page detection, 429 handling and short-page termination have been verified. Details and references are in `JOB_RADAR_HANDOVER.md`.

### 2026-11-09 — HTTPS authentication transport fixed

Production now has a Let's Encrypt IP certificate for `130.210.27.197`, Nginx HTTPS reverse proxy, HTTP-to-HTTPS redirect, secure cookies retained, and app port 8000 bound to loopback. Health/dashboard return 200; owner login must be confirmed over `https://130.210.27.197/dashboard/`. Certbot auto-renew timer and Nginx deploy hook are installed. Operational details in `JOB_RADAR_HANDOVER.md`.


## 2026-11-09 — Owner priority confirmation and global ATS discovery requirement

The owner explicitly confirmed the priority table in Section 5. The earlier P0.5 application tracker sequence is historical and must not overrule the 2026-11-09 table. Basic server-owned application tracking has a prior release note; richer interview/follow-up/outcome capabilities remain P2.

The owner also rejected routine company-by-company ATS configuration. JobBeeper must continuously discover public employer boards across supported ATS platforms, including new companies that appear later. Global discovery, board verification and per-board polling are now P0 source architecture. The manual company form is a fallback/admin correction path, not the normal way to add coverage. Do not claim all employers can be found: search-index exclusion, private portals and employer-authenticated recruitment APIs create known coverage gaps. See GLOBAL_ATS_DISCOVERY_AND_COVERAGE_ARCHITECTURE_2026-11-09.md.

The production Source Health page is a technical telemetry table with a manual company discovery form; it is not a source-confidence model. See SOURCE_HEALTH_EXPLAINED_AND_UX_REDESIGN_2026-11-09.md before redesigning the page.
