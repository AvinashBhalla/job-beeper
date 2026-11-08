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
- Next: user_applications(user_id, canonical_opportunity_id, job_id, applied_at, status, notes, created_at, updated_at).
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

## 9. Current next actions

1. Finish production DB migration rehearsal and deploy verified source set without historical Telegram backfill.
2. Provision first production admin securely and verify a member login.
3. Link owner's private Telegram chat, intentionally enable notifications and send a real test alert.
4. Observe feed/latency and fix bugs.
5. Implement server-backed application tracking before wider beta.
6. Design resume vault/tailoring using fact provenance and human review.
7. Build answer bank before browser companion; do not start with brittle LinkedIn scraping or automatic submissions.

**Reminder:** a source adapter in code is not a verified active production connector. A roadmap feature is not implemented until API, UI, tenant tests and release evidence exist.
