# JobBeeper — Product Vision, Architecture and Delivery Roadmap

**Owner direction:** Build an end-to-end job-search product, not only a job alert bot.
**Last reviewed:** 2026-11-08 (Asia/Kolkata)
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
| Employer discovery | Admin-assisted scan → verify → activate allowlist | Automate after false-positive control is measured |
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
| Application tracker | Applied status, notes and status controls exist | Browser localStorage only; not server-owned/cross-device |
| Referrals | Design only | Contact discovery/provenance, drafts and follow-ups not implemented |
| Assisted apply | Design only | No answer bank or browser companion |
| Auto-apply | Not implemented | Must remain off pending a separate permission/safety gate |

ATS discovery can recognize providers that have no collectors. Current discovery-only families include Recruitee, Breezy HR, Teamtailor, BambooHR, Rippling and Personio. Do not call these active sources until a public/authorized adapter, verified board, tests and safe activation exist. An employer-authenticated recruitment API is not a public job feed.

## 5. Prioritized delivery sequence

Priorities are revisable. New blockers, reference patterns and user test results can move work up or down.

### P0 — Reliable production job radar (release now)

- Finish release review, backups, migration canary and rollback.
- Enable only individually verified boards; current examples are a controlled seed set, not broad platform coverage.
- Keep initial inventory silent; only post-baseline discoveries can alert.
- Verify production scheduler, last-success, request/new-job counts and notification delivery.
- Measure posting → discovery → alert where source timestamps support defensible precision. Never invent exact times from date labels.
- Preserve LinkedIn's 429 breaker/cooldown; do not increase request rate to chase unrealistic latency.
- Run 24–72 hour source/DB soak and record errors, duplicates, false matches and alert delivery.

**Acceptance:** each enabled source has a verified board, at least two successful polls, correct dedupe, silent first inventory, intact DB and an observable per-user test alert. Empty allowlists/unverified tenants cannot be enabled.

### P0.5 — Server-owned application tracker (before wider multi-user beta)

The dashboard tracker is currently in localStorage. It is user-keyed in that browser, but does not sync across devices and can be lost when browser data is cleared.

- Persist applications per user and canonical opportunity.
- Store applied time, status, notes and timestamps.
- Enforce owner-scoped API reads/updates/deletes; never accept client user ID.
- Keep jobs shared; do not duplicate job descriptions per application.
- Prevent duplicate application records for the same canonical opportunity.
- Move dashboard from localStorage to authenticated API calls; decide whether a one-time legacy local-data import is needed.
- Keep schema minimal; add a full activity timeline when reminders require it.

**Acceptance:** two users can track the same job independently; one cannot read/mutate the other's record; changes survive relogin and a second browser; canonical duplicates do not duplicate applications.

### P1 — Resume vault and truthful tailoring

- Add user-owned resume documents and structured candidate facts.
- Extract experience, skills, education, employers, projects and metrics with provenance.
- Let users correct/confirm facts; preserve the original.
- Generate tailored ATS-readable versions from JD + confirmed facts.
- Show a change summary and missing requirements.
- Reject/flag unsupported claims; never silently overwrite the base resume.
- Save versions per application and export PDF/DOCX after user review.
- Enforce private storage, per-user access, export/deletion, retention and encryption at rest.

The current parser is an onboarding suggestion extractor, not a resume-tailoring engine.

### P1 — Application Answer Bank and assisted form preparation

- Create per-user canonical question/answer bank (work authorization, notice period, location, salary expectations, portfolio).
- Track answer type, confidence, source, confirmation date and usage.
- Corrections override prior answers; inferred answers need confirmation.
- Exclude company/job-specific text from reusable generic answers.
- Build a companion extension only after APIs stabilize.
- Fill supported fields on pages the user opened and authorized; show field-to-answer preview/confidence.
- Capture pre-submit snapshot for review; user submits in initial release.

**Acceptance:** no cross-user leakage; unknown answers stay blank; low-confidence/sensitive answers require review; extension never clicks Submit.

### P2 — Application lifecycle, referrals and follow-ups

- Add status history, interview stages, notes, dates and outcomes.
- Add user-created follow-up tasks/reminders grounded in user actions, not guessed response windows.
- Identify public professional contacts with role, employer, evidence URL, source, confidence and last-checked time.
- Rank contacts with explainable relevance; never fabricate identity, affiliation or email.
- Draft referral requests/follow-ups; keep editable.
- Add Gmail/Outlook OAuth only with explicit consent/minimal scopes; start by creating drafts, not sending.
- Record user approval, send/response status and follow-up history; respect privacy/deletion/opt-outs.

### P3 — Interview and search coach

Maintain a user-approved STAR story bank grounded in real experience; create job-specific practice; track application funnel; identify repeated skill gaps; use outcomes/feedback only with transparent purpose and consent.

### P4 — Carefully gated automation

1. **Prepare:** generate CV, cover letter and answers.
2. **Assist:** populate supported form fields in the user's open session.
3. **Review:** show full payload and unanswered/sensitive declarations.
4. **Approve:** user explicitly approves each application.
5. **Submit:** only via supported/permitted interfaces with per-application confirmation and audit record.

Never bypass CAPTCHA, login walls, rate limits, employer controls or terms. Never submit legal, salary/visa or demographic declarations without direct review. Automatic submission stays off until a separate risk/consent/permission/reliability review passes.

## 6. Suggested data model evolution

- Existing shared layer: jobs, canonical opportunities, source runs/board registry.
- Existing identity/profile layer: users, sessions, user_preferences, user_job_evaluations.
- Existing alerts: user_notification_settings, user_notification_ledger, Telegram link tables.
- P0.5 implementation branch: `user_applications(user_id, canonical_opportunity_id, job_id, applied_at, status, notes, created_at, updated_at)`. It is in active implementation/testing, not yet merged/deployed. Canonical ID is reconciled through retained job_id after a dedupe rebuild; unique user+canonical key prevents duplicate app rows.
- Later: user_resumes, resume_facts, resume_versions, application_answer_bank, answer_learning_events.
- Later: followup_tasks, contacts, application_contacts, outreach_drafts, outreach_events, email_integrations.

Use foreign keys, user-scoped indexes, unique constraints and additive migrations. Add a table for a distinct responsibility; do not build a generic workflow engine for one feature.

## 7. Product quality metrics

Track source success/429/cooldown; unique jobs per successful poll; duplicate/canonical merge rate; posting-to-discovery latency with timestamp precision; discovery-to-alert latency; match feedback; saved/applied conversion; application-stage conversion/time; resume correction rate; referral draft/response rate; form-fill correction rate.

Report sample size and timestamp precision. A source returning 1,000 old jobs is not necessarily better than one returning 20 new, relevant jobs.

## 8. Engineering and release rules

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

## 9. Current next actions (reviewed 2026-11-08)

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

## 2026-11-09 — global discovery engineering checkpoint

The feature branch `feat/global-ats-discovery-hirebase-guard-20261109` provides a quota-guarded optional Hirebase sampler and a low-confidence CC BY 4.0 seed import for Greenhouse/Lever/Ashby. It is not the completed Workday/Keka/Darwinbox global discovery engine. Continue first-party company/tenant discovery, public board verification and board-level scheduled polling as P0 source-health work. The Hirebase free API must remain optional and should not be used in commercial multi-user production before written vendor permission. See `GLOBAL_ATS_DISCOVERY_IMPLEMENTATION_2026-11-09.md`.\n

## 2026-11-09 18:10 IST — verified CI and updated research

PR #65 is still **open and draft**, mergeable, based on v2-live-radar. Current head is 999b66543ac162346d42cd3be2c39993c0475a6e. Exact-head GitHub Actions V2 CI run #1427 / ID 42620547252 completed successfully, including dashboard JS syntax, focused tests and the full V2 unittest suite. The local full suite is 430/430 (385.001s); focused new tests are 30/30.

The expanded open-source comparison is in docs/OPEN_SOURCE_JOB_SEARCH_REPO_RESEARCH_2026-11-09.md. New high-value finding: current kalil0321/ats-scrapers has Workday, Keka and Darwinbox adapters. Workday uses facet subdivision to address the 2,000-result query cap; Keka exposes credential-free public career portal JSON endpoints; Darwinbox's adapter uses httpcloak for a Cloudflare-protected endpoint. Do not adopt TLS impersonation to evade an anti-bot control. The library's shared Fetcher does Retry-After-aware 429/5xx retries and explicit 403/406 handling. This makes it the best Python provider reference, but not a dependency we should blindly import.

Job Forager's company-list expansion and Workday pagination are useful to study, but inspected HTTP clients disable TLS certificate validation, broadly swallow exceptions and use fixed concurrency rather than persistent host budgets. Do not copy those transport choices. JobSpy is for supplementary job boards and explicitly warns about 429s; it is not a global ATS discovery source.

### Next priorities

1. Keep PR #65 draft while we review the latest research note and migration ordering across sibling branches.
2. Build an independent, compliant public-board candidate harvester for Workday/Keka/Darwinbox using career-link/sitemap/Common Crawl and trusted directory seeds, with provenance recorded.
3. Reuse/adapt the allowed Keka public portal extraction pattern and Workday facet-aware pagination. Do not enable the Darwinbox Cloudflare-bypass path; require a documented/public authorised route.
4. Turn verified candidate boards into a per-board queue with host-aware concurrency, Retry-After, persistent cooldown, jitter, backpressure and page/facet checkpoints.
5. Run controlled p50/p95, 429, incomplete-page, first-seen-delay and freshness benchmarks before increasing concurrency.
6. Hirebase remains an optional, dev-only sample until the user supplies a key securely and approves estimate-only testing. Do not use its data in a commercial multi-user product without written permission.

Do not merge or deploy this branch as an assertion that JobBeeper now has complete global ATS coverage. It is the quota-safe sampling and candidate-directory foundation; independent Workday/Keka/Darwinbox employer discovery and full board scheduling remain outstanding.\n
## 2026-11-09 19:37 IST — Workday inventory implementation verified locally

Workday now preserves offset 0 on the existing 120-second freshness poll and adds a durable per-board cursor that fetches at most one extra page every 15 minutes. Cursor advances only after upsert; failed pages are throttled without advancing; boards at the 2,000-result cap are explicitly marked incomplete. An admin-only inventory-status API and Coverage & Health panel expose progress. This is not facet-aware full inventory.

Validation: full V2 suite 436 passed in 398.870s (exit code 0); focused Workday/global discovery tests 31 passed. Python compileall, JSON config validation, git diff check and HTML panel wiring passed. Exact-head GitHub CI remains required after push.

Next priorities: Workday facet subdivision; Keka non-default portal slug support; independent public Workday/Keka/Darwinbox employer discovery; per-board scheduler/host budgets; controlled p50/p95 and 429 benchmarks. Darwinbox 403 must remain blocked, with no Cloudflare/TLS bypass.

User action: nothing required now. Hirebase key remains absent and source flags remain off.

Latest checkpoint: docs/RECOVERY_CHECKPOINT_2026-11-09_1937_IST.md. Keka plan: docs/KEKA_PORTAL_RESOLUTION_2026-11-09.md.\n

## 2026-11-10 — bounded company-agnostic ATS discovery delivered

- PR #67 merged as `5d6e2b4`; exact-head GitHub V2 CI passed, including the full V2 unittest suite. The focused discovery/API integration tests passed 34/34 (4 warnings).
- Added a bounded Common Crawl CDX sampler for Workday, Keka and Darwinbox, plus public employer sitemap/careers-link discovery. Results are low-confidence candidates imported through the existing review queue.
- Discovery is manual/admin-only. Startup performs schema initialization only; no crawler starts automatically. Common Crawl uses a persisted global lease, one HTTP request per invocation, 60-second spacing and 24-hour 429/503 cooldown. Sitemap discovery respects robots.txt, same-host redirects, bounded documents/bytes and per-host cooldowns.
- No employer records, board activations or notifications are created by discovery. Initial dev/QA rollout intentionally produced zero discovery runs and zero candidate rows until an admin triggers a scan.
- Image `job-radar-dev-multitenant:5d6e2b4` is deployed to shared dev and connector QA. Both return health 200, have zero restarts, SQLite integrity `ok`, 10/10 active board schedules with successful outcomes, and zero sent notifications. Job counts at verification: dev 10,791; connector QA 2,328.
- Backups/checksums: `/tmp/job-radar-release-backups/2026-11-10-pre-global-discovery/`. Previous scheduler containers retained as `job-radar-dev-pre-global-discovery-20261110` and `job-radar-connectors-qa-pre-global-discovery-20261110`. Production was not changed.
- PR #67's feature branch was deleted after merge; deferred PR tags and prior rollback containers remain intact.

### Next engineering priorities

The following capabilities are already present in the current integration code and have focused tests: Workday facet-aware partitioning (depth/queue bounded, sequential inventory), Keka non-default portal parsing/collection, and the Darwinbox public candidate collector. Current live boards are NVIDIA Workday, Bridgestone default Keka portal and Arvind Darwinbox; these do not prove a Workday 2,000-result facet canary or a live non-default Keka portal.

1. **Source performance profiling (instrumentation delivered)**: PR #68 merged as 1763673 and deployed to dev/connector QA. Phase timings now cover collector, shadow, upsert, evaluation and notification; request min/max and latency histograms are persisted. Collect natural post-deploy samples for Ashby and Greenhouse, compare request latency against collector duration, and add finer parse/detail-enrichment timers only if required. Do not increase concurrency or change poll intervals until the bottleneck is understood.
2. **Workday live facet validation**: use an explicitly approved public tenant that actually reaches the 2,000-result cap; verify child facet metadata, persisted queue resume, dedupe and incomplete-leaf reporting. NVIDIA currently returns only 39 jobs and has not exercised facet subdivision.
3. **Keka non-default live validation**: validate a real public tenant portal slug with the existing collector; keep it separate from the default Bridgestone portal.
4. **Darwinbox coverage**: keep the current Arvind public candidate collector on the approved path. Do not use TLS impersonation, anti-bot bypass or the Cloudflare-protected adapter.

No UI work is required for these tasks. Keep the current rate limits and notification safety unchanged during measurement.

The global discovery implementation is a candidate-discovery capability, not a claim of complete 36-platform coverage. Every discovered board still needs admin review, verification, silent first inventory and a second-poll dedupe check before activation.
