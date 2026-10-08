# Job Radar V2 — Agent Handover & Product Source of Truth

> **Purpose:** This document is the durable handover for Job Radar V2.
> A future agent should read this file before making architectural or product changes.
> Do not depend on chat history being available.

**Last updated: 2026-10-08 (43-test suite green; hardened deployment verified against BlueOptima JD parsing)
**Active branch:** `v2-live-radar`  
**Repository:** `AvinashBhalla/job-beeper`

> **Reconciliation note:** This document is the durable source of truth for the current V2 direction. Telegram delivery is active and has delivered real fresh alerts; the notification path now requires recent discovery for queued alerts so old backlog cannot trigger unexpectedly; deterministic matcher improvements are validated by the current 43-test Docker suite; the Naukri relay remains the Oracle-safe acquisition path; and Agent-Reach is recorded only as a future source-access optimisation, not a current dependency.

---

## 1. PRODUCT GOAL

Job Radar is a **personal, always-on job discovery and matching system**.

### Product benchmark and intended target

JobBeeper is the explicit product benchmark for this project. We use its publicly observable behavior as the baseline, while building a personal implementation optimized for Avinash's needs: lower noise, configurable preferences, persistent state, transparent matching, broad multi-source coverage over time, and reliable Telegram-first delivery.

The goal is not to claim that this system is universally "better than JobBeeper." The goal is to make it **better suited to this user's workflow**, with measurable improvements in relevance, control, freshness, deduplication and delivery reliability.

The objective is not to build a generic scraper or a dashboard full of jobs.

The intended experience is:

```
Continuously discover fresh jobs
        ↓
Maintain a daily active feed
        ↓
Normalize and store them
        ↓
Deduplicate the same opportunity across sources
        ↓
Apply the user's configurable job preferences
        ↓
Reject irrelevant / unsuitable jobs
        ↓
Rank genuinely relevant jobs
        ↓
Explain why each job matched
        ↓
Send only worthwhile new matches to Telegram
        ↓
Provide a simple live frontend for review and configuration
```

### Product priorities

1. **Freshness**
2. **Correctness of matching**
3. **Low-noise Telegram alerts**
4. **Persistence / reliability**
5. **Cross-source deduplication**
6. **Simple useful frontend**

The UI is secondary to the backend job radar.

The system must never invent a posting timestamp just to make a job appear fresh.

---

## 2. CANDIDATE PROFILE / DEFAULT TARGET

Current candidate experience:

- 2 years

Current maximum acceptable experience:

- 3 years

Current target locations:

- Bengaluru / Bangalore
- Gurugram / Gurgaon
- Delhi
- Remote India

Current target role families include:

- Software Engineer / Software Developer
- Full Stack Engineer / Developer
- Frontend Engineer / Developer
- Backend Engineer / Developer
- React / React Native
- Python
- Node / Next
- Automation Engineering
- AI / ML
- LLM
- Forward-Deployed Engineering

Current skill vocabulary includes:

- React
- React Native
- Next.js
- Node.js
- Python
- FastAPI
- Django
- JavaScript / TypeScript
- Automation
- n8n
- API
- LLM
- AI
- OpenAI
- Gemini
- Workflow
- Orchestration

These are **defaults, not permanent hardcoded product rules**.

User preferences must ultimately be configurable from the frontend.

---

## 3. DESIRED ARCHITECTURE

```
                 ┌──────── LinkedIn
                 │
                 ├──────── Naukri
                 │            ↑
                 │       GitHub relay
                 │
                 ├──────── Instahyre
                 │
                 └──────── ATS / career sources
                              │
                              ▼
                       Source adapters
                              │
                              ▼
                         Normalize
                              │
                              ▼
                   Canonical job identity
                              │
                              ▼
                     Cross-source dedupe
                              │
                              ▼
                       Persistent SQLite
                              │
                              ▼
                     New / changed detection
                              │
                              ▼
                    Deterministic matching
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                 Telegram           Frontend
```

### Infrastructure

Primary persistent runtime:

- Oracle Cloud Always Free VM
- Ubuntu
- Docker
- SQLite on a persistent Docker volume

GitHub Actions is **not** the persistent scheduler/runtime.

GitHub Actions is currently used as the Naukri acquisition environment because direct Naukri access from Oracle was unreliable.

---

## 4. WHY V1 WAS ABANDONED

V1 relied heavily on:

- GitHub Actions as a scheduler
- JSON state
- broad web discovery
- manually curated ATS/company lists
- fragile Naukri/browser scraping
- weak matching
- stale frontend data

Problems included:

- scheduled workflows were unreliable
- LinkedIn freshness was inconsistent
- Naukri was fragile
- matching was weak
- frontend data became stale
- manual scan behavior defeated the idea of a continuous radar

V1 remains useful as reference/fallback only.

Do not recreate the V1 architecture unless there is a specific, justified reason.

---

## 5. IMPORTANT SOURCE DECISIONS

### LinkedIn

Current approach:

- public logged-out guest jobs endpoint
- low-volume polling
- newest-first
- six-hour safety window
- deduplicate using stable LinkedIn job IDs
- record source posting time separately from discovery time
- retry/backoff on 429 and transient 5xx errors

Current V2 LinkedIn freshness target:

- poll every 60 seconds
- fast lane scans `start=0` every poll with LinkedIn low-applicant filtering (`f_EA=true`) and a one-hour recency window
- scan `start=0` on every poll
- scan `start=10` as a deeper six-hour sweep every 5 minutes, without the low-applicant filter
- run LinkedIn search requests concurrently with a bounded worker pool
- fetch only plausible alert candidates for JD enrichment, also concurrently
- prefer the public LinkedIn guest job-detail endpoint for enrichment
- parse one job per actual LinkedIn job-card link instead of iterating every nested `<li>`, preventing duplicate/nested-list explosions

This is intended to reduce discovery lag without blindly multiplying request volume. The target is to make a newly surfaced LinkedIn posting reach the matcher/Telegram path within a few minutes under normal source behavior. Actual median/p95 latency must be measured from runtime logs before declaring that target met.

LinkedIn direct collection from Oracle has been **proven**.

### Naukri

Direct Naukri access from Oracle was abandoned after:

- JobSpy Naukri API returned 406
- Playwright / Chromium hung
- Python requests hung
- curl timed out

Do **not** restart Oracle-side Chromium/Naukri scraping.

Current architecture:

```
Oracle systemd timer
        ↓
gh workflow run naukri-relay.yml
        ↓
GitHub Actions runner
        ↓
Naukri
        ↓
naukri-relay branch
        ↓
naukri_relay.json
        ↓
Oracle V2
```

The corrected relay was successfully proven on 2026-10-08.

Example successful relay properties:

- workflow run succeeded
- `naukri_relay.json` was published
- count = 150 jobs
- real Naukri JSON was accessible from the relay branch

### Instahyre

Currently experimental and **disabled by default in V2**.

The current public JSON probe returned HTTP 400 for the tested request. We do not treat this as a reliable source until its current interface is verified.

Repository defaults and the V2 runtime migration now make Instahyre opt-in. Config schema version 3 disables Instahyre when migrating a pre-v3 runtime config.

Zero results or request errors must not automatically justify increasing polling or scraping volume.

### Agent-Reach — future optimisation, not current dependency

The repository `Panniantong/agent-reach` was evaluated conceptually as a possible source-access optimisation.

Decision:

- **Do not replace the current V2 collectors with Agent-Reach now.**
- Keep LinkedIn direct ingestion and the Naukri GitHub relay as the working production paths.
- Revisit Agent-Reach after the V2 MVP is stable.
- The first future experiment should benchmark it against the existing LinkedIn collector on freshness, job-detail quality, latency, failure/429 rate, and Oracle CPU/RAM impact.
- Treat Naukri support as unverified until a real end-to-end Naukri retrieval test proves it.
- Potential later use: generic web/ATS access for structured career sources, but source-specific adapters remain preferred where stable APIs exist.
### Future ATS sources

The product should progressively prioritize structured/source-specific adapters such as:

- Greenhouse
- Lever
- Ashby
- SmartRecruiters
- Workday
- other useful ATS/career systems

Do not build one generic scraper for all sources.

---

## 6. NARROWING THE MATCHING PHILOSOPHY

Matching must be deterministic and explainable before any AI enrichment.

The target pipeline is:

```
source
 → normalize
 → canonical identity
 → deduplicate
 → new/changed detection
 → deterministic preference match
 → score + reasons
 → dashboard / Telegram
```

### Current matcher checks

- title exclusions
- location
- target role
- configured skills
- experience
- match score
- match reasons
- separate alertability policy

### Current matcher lessons and fixes

The matcher previously had two important problems in real runtime data:

1. It treated job-title vocabulary too literally. Variants such as `Software Development Engineer 2` and `Javascript Developer` could fail the configured role test even though they were clearly relevant.
2. Unknown experience could leave an otherwise strong profile match below the alert threshold.

The current matcher now includes:

- phrase-aware configured-term matching rather than naive substring matching
- role-family aliases for `Software Engineer` / `Software Development Engineer` / `SDE`
- full-stack spelling variants
- a generic developer/engineer + configured-skill signal for titles such as `Javascript Developer`
- direct title-role scoring high enough to clear the existing 55 baseline when the source omits experience
- strict rejection when stated experience exceeds the candidate or configured maximum
- unknown experience treated as **neutral for matching**
- alertability evaluated separately from matching

The separate alertability policy currently allows unknown experience because the runtime setting is:

```
require_explicit_experience_for_alerts = false
```

That is intentional and configurable.

### Regression coverage

The full V2 Docker regression suite now has:

```
43 tests — ALL GREEN
```

Important regression cases now include:

- `Software Development Engineer 2` → matches
- `Javascript Developer` → matches when JavaScript is configured
- direct `Software Engineer` with unknown experience → matches
- senior/lead/principal/intern exclusions remain enforced
- explicit experience above the 3-year maximum remains rejected

### Important policy principle

**Eligibility, score, and alertability are different concepts.**

A job can be:

- relevant enough to show in the frontend
- but not sufficiently verified to send to Telegram automatically

The policy must remain configurable rather than being silently inferred from score alone.
## 7. CURRENT CONFIGURATION PRINCIPLE

The current V2 implementation reads `v2/config.json`.

That is useful as a code-level default, but it is **not yet the final product behavior**.

### Required end state

The V2 runtime configuration layer is now implemented in the repository.

The frontend must allow the user to configure, without editing Python:

- target roles
- keywords
- skills
- locations
- remote preference
- candidate experience
- minimum job experience
- maximum acceptable experience
- excluded titles
- excluded role/category types
- maximum job age
- minimum match score / threshold
- whether explicit experience is required for alerts
- Telegram enabled/disabled
- source enable/disable where appropriate

User preferences should be persisted on the VM, not committed back into GitHub on every UI change.

Implemented direction:

```
Frontend
  ↓
V2 configuration API
  ↓
persistent /data/config.json
  ↓
matcher + alertability policy
```

Configuration updates are protected by a generated token stored at `/data/config_token` unless `JOB_RADAR_CONFIG_TOKEN` is supplied as an environment variable.

Application code and personal preferences remain separate.

The repository now exposes:
- `GET /api/config`
- `PUT /api/config` with `X-Config-Token`
- runtime config migration/default seeding
- validation for user-owned configuration
- live matching against runtime configuration without a rebuild

---

## 8. CURRENT FRONTEND STATUS

A dashboard already exists under:

- `dashboard/index.html`
- `dashboard/app.js`
- `dashboard/styles.css`

It includes:

- Jobs
- Applied
- Filters
- Settings
- Sources
- job detail view

The dashboard has now been rewritten to use the V2 local APIs for jobs, source status and configuration.

Current repository direction:

- configuration reads/writes through /api/config
- config token is held in browser session storage
- job feed reads from /api/jobs
- source health reads from /api/source-status
- V2 runtime serves the dashboard directly

Oracle deployment is now complete; browser/product verification remains pending.

---

### Observation 27 — Repository cleanup after UI PR

The merged UI PR accidentally committed runtime/generated artifacts:

- `v2/jobs.db`
- `v2/config_token`
- ten tracked `__pycache__/*.pyc` files, including UI skill cache files

These artifacts have now been removed from the current `v2-live-radar` branch tip, and `.gitignore` now covers:

```
__pycache__/
*.pyc
*.pyo
v2/jobs.db
v2/config_token
```

A branch-tree verification confirms none of those artifact paths remain in the current branch.

Security rule: removing a credential from the current branch does not erase it from Git history. Because `v2/config_token` was committed, the live Oracle configuration token should be rotated immediately. Full history scrubbing is a separate optional cleanup and should be coordinated with the production branch before force-pushing.

## 9. CURRENT INFRASTRUCTURE STATE — VERIFIED

### Oracle VM

VM:

- `job-radar`
- Oracle Always Free
- approximately 1 GB RAM
- 2 GB swap

The VM previously suffered from 208 zombie Chromium processes and very high CPU steal.

That issue was resolved.

Current V2 deliberately uses no Chromium.

### Docker

V2 container is running:

- service: `radar`
- container currently named similar to `v2-radar-1`
- port: `8000`
- database: `/data/jobs.db`

The deployed service is verified through its root redirect and V2 APIs. There is no `/api/health` endpoint in the current implementation; `/` redirects to `/dashboard/`.

### Naukri systemd scheduler

The following units exist:

- `job-radar-naukri-relay.service`
- `job-radar-naukri-relay.timer`

The timer is enabled and runs every five minutes.

The service executes:

```
/usr/bin/gh workflow run naukri-relay.yml --repo AvinashBhalla/job-beeper --ref main
```

GitHub CLI is authenticated for the `ubuntu` user.

The scheduler has successfully triggered the relay automatically.

### Do not manually trigger the relay during normal operation

With the five-minute systemd timer enabled, manual dispatches can create unnecessary overlapping relay runs.

Use manual dispatch only for debugging/recovery.

---

## 10. CURRENT LIVE INGESTION STATUS

The running V2 service has successfully demonstrated:

### Naukri

- 150 jobs obtained from relay during a run
- data persisted to SQLite
- source marked successful

### LinkedIn

- 177 jobs seen in the tested run
- 36 new jobs in that run
- source marked successful

### Instahyre

- 0 jobs
- currently experimental

The system is therefore **ingesting real jobs continuously**.

---

## 11. CURRENT RELEASE CHECKPOINT

### Completed

```
✅ Persistent Oracle VM
✅ Docker V2 runtime
✅ SQLite persistence
✅ LinkedIn direct ingestion
✅ Naukri GitHub relay
✅ Naukri corrected relay execution proven
✅ Oracle → GitHub workflow dispatch proven
✅ Oracle 5-minute Naukri scheduler
✅ V2 Naukri relay consumption
✅ Freshness/discovery timestamps separated
✅ Initial deterministic matcher
✅ Experience false-positive correction
✅ Phrase-aware skill/title matching
✅ V2 persistent runtime configuration API implemented
✅ Frontend connected to V2 configuration API in repository
✅ Config validation + generated configuration token
✅ LinkedIn freshness acceleration implemented: 60-second fast polling, bounded concurrency, five-minute deeper pagination, bounded concurrent JD enrichment
✅ Experience-range parser fixed to preserve hyphen/en-dash ranges
✅ Runtime config migration hardened: pre-v3 configs disable unverified Instahyre
✅ Canonical opportunity schema and conservative cross-source linking implemented
✅ Canonical opportunity API and dedupe diagnostics implemented
✅ Persistent job evaluation state with score/reasons/experience/alertability
✅ Persistent notification ledger per canonical opportunity
✅ Telegram claim/retry/recovery path implemented
✅ Telegram credentials verified on Oracle and real delivery verified
✅ Telegram timestamps render in human-readable IST; Naukri keeps date-only posting precision
✅ Daily active feed resets at India local midnight without deleting historical SQLite data
✅ V1 job-watch Telegram workflow is inactive/disabled; V2 is the intended alert path
✅ Real-time Telegram eligibility gate implemented: queued alerts require discovery within the last 10 minutes
✅ Queued opportunities are revalidated against current match/alertability state before delivery
✅ Previously suppressed opportunities can be reconsidered only when a genuinely recent new source observation appears
✅ Old backlog is suppressed rather than replayed by a notification refresh
✅ Failed Telegram deliveries remain retryable after the fresh-queue window so transient delivery failures do not lose a valid alert
✅ Matcher role-family aliases added for Software Engineer / Software Development Engineer / SDE variants
✅ Configured-skill + developer/engineer title fallback added for variants such as Javascript Developer
✅ Unknown experience made neutral for matching while alertability remains a separate policy
✅ V2 regression suite expanded to 43 tests; Docker execution is now green after JD-hardening and today-only feed coverage
✅ Updated 43-test suite passes in Docker (39 baseline + 3 JD-hardening tests + 1 today-only feed test)
✅ Production fresh-job validation completed after matcher deployment: a latest 10-minute diagnostic showed 20 matching job rows, all 20 alertable, no queued backlog, and 17 rows whose canonical notification ledger state was sent
✅ Repository .gitignore now ignores Python __pycache__ artifacts
✅ Agent-Reach evaluated as a possible future source-access optimisation and deliberately parked until core V2 MVP stability
✅ BlueOptima-style LinkedIn JD extraction incident reproduced and JD retrieval/parser hardened for overall/total experience wording, JSON-LD, description selectors, HTML entities/non-breaking spaces and Unicode dash variants
✅ Corrupted direct test-file update repaired by restoring the last known-good 39-test suite and adding three focused JD-extraction regression tests
✅ V2 CI strengthened to run py_compile on both production/test Python and the full unittest suite, preventing structurally broken test files from reaching the branch undetected
✅ Repaired a second test-file corruption incident: the branch temporarily contained only a truncated tail of `v2/test_radar.py`; the file was restored from the known-good 39-test commit and all four required new regression cases were reapplied cleanly, restoring the expected 43-test suite
✅ Corrected the today-only regression test after discovering the restored version had not actually moved `discovered_at` across IST midnight; the production contract remains correct and the test now models it correctly
✅ Found and fixed a separate `/api/jobs?today_only=true` bug: the endpoint accepted the flag but previously ignored it, and `/api/opportunities` referenced an undefined `today_only` variable; today-only filtering is now explicitly driven by India-local midnight and covered by regression tests
✅ Fixed the first today-only regression test itself: it had moved only source posting timestamps across midnight while discovery timestamps remained current; the corrected test now moves `discovered_at` across IST midnight and verifies both `/api/jobs` and `/api/opportunities`
```

### Currently in progress

> **MVP implementation status:** Core V2 MVP development is complete. Remaining work is acceptance validation and bug fixing only; new feature development should wait for MVP sign-off.

```
✅ Pulled the latest branch to Oracle, verified all 43 tests pass in Docker, and recreated the V2 container with the hardened JD extraction/retrieval and today-only feed fixes
⏳ Verify the strengthened V2 CI run passes the same 43-test suite on GitHub Actions
✅ Verified the BlueOptima-style 5–7-year JD case after deployment: fetched detail contains the explicit requirement, evaluation stores 5–7, and current 3-year policy rejects it
⏳ MVP blocker: make LinkedIn experience acquisition reliable for poster-added requirements, or enforce explicit-experience-only Telegram alerts until a reliable source-access path exists
⏳ Re-test LinkedIn freshness after the role-query coverage correction and measure 429 rate / discovery lag
⏳ Manual acceptance test: measure true end-to-end alert latency from source posting/discovery through evaluation/JD enrichment, queue and Telegram send
⏳ Manual acceptance test: classify the two non-sent opportunities from the latest one-hour matching window and verify their notification decisions
⏳ Manual acceptance test: validate persistent runtime configuration changes end-to-end from frontend/API through evaluation and notification reconsideration
⏳ Manual acceptance test: validate restart/recovery behavior with persisted config, evaluations and notification ledger
⏳ Manual acceptance test: finish browser verification of the live dashboard against real V2 API data
⏳ Post-MVP enhancement: complete changed-opportunity detection so materially changed requirements can be reconsidered without duplicate alerts
⏳ Manual acceptance test: validate source-health UI and remaining convenience features
⏳ Final V2 MVP sign-off after manual acceptance checks pass
```
### V1 status

The legacy `job-watch.yml` Telegram workflow is no longer active. GitHub reports it as inactive/not listed in the active workflows; V2 is now the sole intended Telegram alert path. Other active workflows such as `check-sources`, `naukri-relay`, `deploy-dashboard`, and `V2 CI` do not replace the V2 Telegram worker.
## 12. IMMEDIATE NEXT STEPS

### Step A — Hardened LinkedIn JD extraction end-to-end — VERIFIED

With the latest container running, verify a real LinkedIn posting whose browser JD explicitly states:

```
5 to 7 years of overall software engineering experience
```

The system must capture:

```
experience_min_years = 5
experience_max_years = 7
```

and reject the posting for the current 3-year maximum before Telegram delivery.

### Step B — Verify canonical-level alert deduplication and non-sent classification

On a fresh production window, count fresh matching rows, distinct canonical opportunities, distinct sent canonical opportunities and duplicate observations per canonical opportunity. The latest one-hour sample has 3/3 distinct canonical opportunities and 0 duplicate observations; the two non-sent opportunities still need decision-state classification.

Do not interpret source-row count as alert count.

### Step C — Measure end-to-end alert latency and LinkedIn freshness

Measure both alert latency and source freshness:

```
source posting
 → source discovery
 → normalization/evaluation
 → JD enrichment when required
 → notification decision
 → queue
 → Telegram send
```

Record median and p95 latency.

### Step D — Validate runtime configuration + recovery

Verify frontend/API changes persist in /data/config.json, trigger evaluation/notification reconsideration correctly and survive container restart.

### Step E — Finish frontend verification

Validate live refresh, current-day feed, daily counters, filters/settings, job details, source health and direct apply links.

### Step F — Changed-opportunity detection

Define material changes including experience requirements, description/requirements, location/work mode and application URL changes, then reconsider without duplicate alerts.

### Step G — Source-access optimisation evaluation

Only after the core V2 path is stable, benchmark Agent-Reach against the current LinkedIn collector for freshness, detail quality, latency, 429/failure rate and Oracle resource usage.

### Step H — MVP sign-off

Core implementation is complete. The current architecture becomes the stable V2 MVP baseline after manual acceptance checks pass for alert correctness, latency, canonical dedupe, configuration persistence/recovery and frontend behavior.

## 13. ENGINEERING RULES FOR FUTURE AGENTS

### Before changing a source

First inspect:

- structured/public interface
- pagination
- stable job IDs
- posting timestamp
- update timestamp
- rate limits
- failure modes

Prefer JSON/API over rendered HTML.

### Before increasing polling

Measure:

- requests/run
- jobs fetched/run
- relevant jobs/run
- new jobs/run
- 429/4xx/5xx rate
- median discovery lag

Never increase polling merely because a source returned zero jobs.

### Freshness

Always preserve:

- source posting time
- our discovery time
- precision of the source timestamp
- discovery latency when valid

Never invent exact times from date-only information.

### Matching

Keep geography and eligibility deterministic.

Do not use naive substring matching if it can create semantic false positives.

### Source failure isolation

One failing source must not stop other sources.

### Security

Never ask the user to paste:

- GitHub tokens
- SSH private keys
- Naukri passwords
- Telegram bot secrets

Use existing authenticated mechanisms and environment/secret storage.

### Applications

Never automate application submission.

Preserve canonical application links.

---

## 14. CURRENT IMPORTANT OBSERVATIONS

### Observation 1 — JobBeeper is the public product benchmark, not the private implementation source

The repository contains docs/JOBBEEPER_REFERENCE.md, which records only publicly observable JobBeeper behavior. The project goal is to reproduce those useful product properties with a simpler personal architecture, then optimize specifically for this user's workflow rather than claim generic superiority.

### Observation 2 — Freshness is now the main ingestion risk

The first real Telegram alert observed on 2026-10-08 had a source posting time around 1:16 PM IST and discovery around 1:38 PM IST. The ~22-minute lag is too slow for competitive job hunting. The root cause was not only the two-minute scheduler interval: the LinkedIn collector performed 32 search requests sequentially (query × location × pagination) and then performed candidate JD enrichment sequentially before upserting/evaluating the batch. The collector has now been changed to a 60-second fast lane with bounded concurrent search requests, periodic deep pagination, and concurrent candidate JD enrichment.

The next gate is measured runtime latency, not merely a shorter configured interval. A bad acceleration build briefly caused the matcher symbols to disappear and the broad `<li>` parser to over-count one collection run; that build was repaired before further rollout.

### Observation 3 — Ingestion is otherwise functioning

### Observation 4 — Real cross-source overlap is currently ambiguous, not safely deduplicable

The latest Oracle diagnostic considered 1,206 jobs and found 38 cross-source candidates, with 0 auto-link candidates. The observed same-title/company/location examples include materially different explicit experience ranges, so the system correctly keeps them separate.

### Observation 5 — Daily feed reset is a presentation lifecycle, not data deletion

The active user-facing feed resets at India local midnight. Historical job observations remain in SQLite so deduplication, notification history and auditability are not lost. The API now exposes a current-day feed and daily summary without deleting historical data.

### Observation 6 — Persistent state is now the foundation for new-only alerting

Job-level evaluation state is persisted separately from source observations, while notification state is persisted once per canonical opportunity. Historical opportunities are suppressed during ledger backfill; newly created canonical opportunities enter a pending state. A fresh opportunity that is currently non-alertable remains pending so later preference changes can reconsider it. Configuration changes recompute persisted evaluations before reconsidering the notification queue.

### Observation 7 — LinkedIn card data is not sufficient for experience

LinkedIn search cards do not reliably expose the experience requirement even when the full job page does. New LinkedIn jobs without a parsed card-level experience now receive one public JD fetch before matching. Explicit requirements such as "5+ years of full-time software development experience" are extracted into the stored description, allowing the normal experience eligibility rules to reject unsuitable roles before Telegram.

### Observation 8 — Telegram is now the next external integration

The V2 Telegram layer consumes only queued canonical opportunities, atomically claims delivery work, formats an explainable direct-apply alert, records sent or failed, retries only explicitly retryable failures, and recovers interrupted claims after restart. Credentials are supplied through container environment variables and are never stored in the repository. The first real credentialed run successfully delivered three job alerts.

### Observation 9 — Matcher quality matters more than raw job count

The objective is not to maximize jobs stored.

The objective is to maximize the ratio:

```
worthwhile alerts / total alerts
```

Noise is a product failure.

### Observation 10 — Unknown data must remain unknown

If LinkedIn does not expose experience, do not manufacture one.

The system should represent uncertainty and make policy decisions from that explicit state.

### Observation 11 — Frontend configuration must be real

A UI control that only changes an old V1 config is not a V2 feature.

### Observation 12 — Same-source isolation must be enforced at candidate retrieval time

The canonical layer now carries the representative source through metadata candidate queries, so same-source listings cannot be merged merely from company/title/location similarity. Exact canonical URL evidence remains eligible for linking.

### Observation 13 — Experience ranges reveal real requisition variants

Real IBM examples showed identical company/title/location across LinkedIn and Naukri with different explicit Naukri ranges such as 5–7, 6–7, and 6–8 years, and IBM Cloud FullStack variants at 15–20, 14–20, and 18–20 years. These are not safe duplicate merges. Canonical matching now treats incompatible explicit experience ranges as distinct opportunities.

### Observation 14 — The current source roadmap is broader than the first three sources

The long-term goal includes useful ATS/career sources.

Do not expand source count aggressively until the core normalization, dedupe, matching, alerting and configuration architecture is solid.

### Observation 15 — The first real-time reactivation fix caused backlog alerts and required a discovery-time gate

The initial fix that allowed suppressed opportunities to reactivate correctly also created a failure mode where older opportunities could become Telegram alerts when a refresh was run.

The corrective rule is now:

```
queued Telegram alert eligibility
    requires
job.discovered_at within the last 10 minutes
```

This is intentionally separate from the normal job matching age window of 72 hours.

A failed Telegram delivery can still retry after that 10-minute discovery window, because it represents an already-valid fresh alert whose delivery temporarily failed.

### Observation 16 — Production matching is now materially better than the previous literal role matcher

The live diagnostic showed relevant roles such as automation engineering and AI engineering reaching match/alertable state, and the matcher now recognizes common role variants that previously scored too low.

A latest 10-minute diagnostic showed:

- 20 matching job rows
- 20 alertable rows
- 0 fresh queued rows remaining at query time
- 17 rows whose linked canonical notification state was `sent`

This is evidence that the pipeline is functioning, but it is **not yet a distinct-alert count**. Canonical-level dedupe must be checked before calling alert quality proven.

### Observation 17 — Recent source ingestion is healthy enough for continued measurement

The latest source activity window showed:

- LinkedIn continuing roughly minute-level polls with multiple successful runs and newly discovered jobs
- Naukri continuing five-minute relay-driven source runs without a source error in the latest window
- no recent Telegram delivery/error log entries after the successful fresh-alert sample

Historical LinkedIn rate-limit pressure remains a known risk; polling should be optimized from measured 429/failure rate rather than increased blindly.

### Observation 18 — Oracle host Python is not the project test environment

The host Ubuntu Python does not have the V2 dependencies such as `bs4` installed, and `python3 -m pip` is unavailable.

The canonical test path is therefore the project Docker environment:

```
docker compose ... run --rm --no-deps radar python3 -m unittest discover -s v2 -p 'test_*.py' -v
```

Do not install ad-hoc host Python dependencies just to run the suite.

### Observation 20 — LinkedIn JD experience can be present in the browser while missing from Telegram

A real BlueOptima LinkedIn posting exposed a correctness gap:

```
Browser JD:
5 to 7 years of overall software engineering experience.

Telegram from the pre-hardening runtime:
Experience: Not stated
```

The subsequent live DB inspection after the hardened deployment confirms the parser now captures the requirement correctly:

```
experience_min_years = 5
experience_max_years = 7
match = 0
alertable = 0
```

The historical notification ledger for this same posting is still `sent`, but that send occurred at 11:19 UTC, before the hardened container was deployed/recreated at approximately 13:16 UTC. Therefore this row is evidence of the old-runtime incident, not a post-deployment regression.

Corrective rule:

```
LinkedIn card has no experience
        ↓
preliminary profile match
        ↓
fetch public job detail
        ↓
prefer explicit overall/total experience statements
        ↓
persist min/max experience
        ↓
re-evaluate before notification
```

Supported JD wording must include phrases such as `5 to 7 years of overall software engineering experience`, common Unicode dash variants, HTML entities/non-breaking spaces and common minimum/at-least experience wording.

A known experience requirement must not be hidden merely because the search card omitted it.

For future production validation, use a posting first discovered after the hardened deployment when verifying the end-to-end notification gate.

During direct GitHub maintenance, a second test-file corruption was discovered after an earlier repair: the branch contained only a truncated 2,943-character tail of `v2/test_radar.py`, causing `IndentationError` at file line 1 on Oracle. The safe recovery procedure is now to restore the last known-good complete test file and reapply new tests, rather than attempting line-range reconstruction from a potentially truncated current file.

The first automated attempt to add regression coverage directly to the test file corrupted the file structure and caused a syntax error. The file was repaired by restoring the last known-good test suite and reapplying the new tests as a clean append before the existing JD-experience test block. Future direct GitHub file edits must prefer reconstruction from a verified-good version when a patch has already become structurally suspect.

### Observation 23 — The today-only regression test initially failed because discovery time was not actually moved

The production endpoint correctly filters `discovered_at` against the India-local midnight boundary. A restored test fixture initially moved only `source_posted_at`, leaving `discovered_at` at the current time, so the old synthetic job was correctly included.

The test has now been corrected to move `discovered_at` itself across the IST-midnight boundary. This is a test-fixture correction, not a production logic correction.

### Observation 22 — The daily feed API had a latent today-only parameter bug

The dashboard requests `/api/jobs?today_only=true`, but the endpoint previously calculated its cutoff from the default `minutes` parameter instead of the India-local midnight boundary. Separately, `/api/opportunities` referenced `today_only` without declaring it as a parameter.

Corrective rule:

```
/api/jobs?today_only=true
    → current India-local midnight cutoff

/api/opportunities?today_only=true
    → current India-local midnight cutoff
```

The fix is now on `v2-live-radar`; the regression test now correctly models the product lifecycle by moving discovery timestamps across IST midnight and verifies both `/api/jobs` and `/api/opportunities`. Future agents must treat frontend query parameters as backend contracts and verify that every advertised parameter changes behavior as intended.


### Observation 26 — The merged UI enhancement PR did not contain a major visual frontend redesign

The merged pull request `#3` ("Ui enhancement") was inspected after local Git was proven to match `v2-live-radar` at merge commit `33b3c410`.

The PR's effective changed-file list contains only:

```
dashboard/index.html
```

Its patch is primarily HTML reformatting/indentation plus the configuration-access section. It does **not** modify:

- `dashboard/styles.css`
- `dashboard/app.js`

Therefore, a substantially different visual frontend cannot appear in the current `v2-live-radar` merely by checking out the merged PR. The local checkout is correct; a larger redesign would require the friend/client-side UI changes to be committed to GitHub, including the relevant CSS/JS/assets.

Do not treat the current branch's merged PR as evidence that a full visual redesign was delivered.

### Observation 25 — Manual acceptance found a one-hour LinkedIn discovery lag for a Full Stack Engineer posting

A real Telegram alert for ReqPedia's `Full Stack Engineer` posting showed approximately:

```
Posted:     6:28 PM IST
Discovered: 7:28 PM IST
```

The LinkedIn browser page showed the posting at about one hour old with over 100 applicants. This is outside the intended freshness goal for the radar.

Inspection of the current repository configuration showed that the LinkedIn fast-lane query vocabulary previously included `full stack developer` but not `full stack engineer`, even though `full stack engineer` is a configured target role. The fast-lane query has now been broadened to cover engineer/developer variants without increasing the number of LinkedIn query families:

- full stack developer / engineer
- frontend developer / engineer
- backend developer / engineer
- React developer / engineer
- Python developer / engineer
- automation engineer

This is a targeted freshness/coverage correction. It may reduce misses for role-name variants, but it does not by itself prove that all fresh LinkedIn jobs will arrive within the desired latency. LinkedIn 429 responses remain a known operational constraint and must be measured after this change rather than solved by blindly increasing request volume.

Acceptance rule:

```
fresh suitable job
→ should surface within a few minutes under normal source conditions
```

A one-hour discovery lag is a failed freshness acceptance case and must remain visible in future runtime validation.

### Observation 24 — LinkedIn authenticated page can expose poster-added requirements that the public guest detail fetch does not expose

A second real LinkedIn production check used an Ampstek posting whose logged-in browser page visibly showed:

```
8+ years of work experience with Core Java
8+ years of work experience with Python
```

The same posting's current production database record originally had no captured experience and the pre-fix Telegram alert therefore showed `Experience: Not stated`.

After deploying the hardened JD parser, a read-only re-fetch of the live LinkedIn URL was performed from the Oracle container. The public guest/detail acquisition returned a short description without the poster-added `8+ years` requirements:

```
contains "8+ years": False
extract_jd_experience = (None, None)
extract_experience = (None, None)
```

The non-persisting simulation then remained:

```
match = True
alertable = True
experience = unknown
```

This proves an important limitation: the parser can only extract requirements that the production source-access layer actually retrieves. The current public logged-out LinkedIn fetch does not reliably expose every requirement visible in an authenticated browser session, especially LinkedIn's "Requirements added by the job poster" section.

Corrective implication:

- Do not claim the JD hardening solves all LinkedIn experience extraction.
- Treat the current parser as correct for the text it receives, but the acquisition layer remains incomplete.
- Before calling experience-based Telegram filtering fully trustworthy, either obtain a reliable production-access path to those poster-added requirements or require explicit captured experience for Telegram alerts.
- Keep unknown experience available for matching/dashboard review unless product policy is deliberately changed.
- A safer interim alert policy is `require_explicit_experience_for_alerts=true`, which prevents unknown-experience LinkedIn jobs from reaching Telegram while preserving them for dashboard review.

This is now an MVP acceptance blocker for **Telegram precision**, not a reason to discard the overall V2 architecture.
### Observation 21 — Canonical duplication has no duplicates in the latest one-hour matching window

A post-deployment one-hour audit found:

- 3 fresh matching source rows
- 3 distinct canonical opportunities
- 3 alertable source rows
- 1 distinct sent canonical opportunity
- 0 canonical opportunities with multiple observations in that window

This is a positive small-sample result for canonical deduplication, but it is not sufficient to declare dedupe fully proven. The two matching opportunities that were not sent still need classification (for example, already-sent/suppressed/not-new state) before evaluating alert completeness.

The daily notification ledger currently contains 785 rows for the day:

- 43 sent
- 742 suppressed
- 0 queued

The daily summary reports 1,070 jobs discovered, 52 matched, 52 alertable and 43 alerts sent. These are different layers and must not be conflated: source jobs, evaluations and canonical notification records represent different units of measurement.


### Observation 19 — Agent-Reach is a candidate optimisation, not a dependency

Agent-Reach may reduce the amount of bespoke web-access code for some future sources, particularly LinkedIn or generic web/ATS discovery.

It is deliberately parked until:

- current ingestion/matching/alerting is stable
- alert latency and dedupe are measured
- resource impact on the tiny Oracle VM is understood

Do not introduce it into production source flow merely because it supports more platforms on paper.

---

## 15. WHAT NOT TO DO

Do not:

- restart Chromium scraping on Oracle for Naukri
- turn GitHub Actions into the primary scheduler
- rebuild V1 JSON-state architecture
- hardcode user preferences into Python
- send Telegram alerts before dedupe/newness checks
- treat every keyword hit as a good match
- invent posting timestamps
- increase source polling just because a source returns zero
- add AI matching before deterministic matching is reliable
- build elaborate frontend UI before alert quality is trustworthy
- disable V1 alerts before V2 Telegram works
- ask the user for credentials that are already configured on the VM

---

## 16. HOW TO UPDATE THIS DOCUMENT

This file is the project's durable handover.

**Update it whenever any of the following changes:**

- product goal
- target candidate profile
- source architecture
- source status
- infrastructure
- matching policy
- alerting policy
- frontend role
- important failure / lesson
- release checkpoint
- immediate next step

After a significant milestone, update the relevant section and especially:

- **Current release checkpoint**
- **Current important observations**
- **Immediate next steps**

Do not let the code and this document drift apart.

If a future agent discovers that this document contradicts the actual repository, the agent should:

1. inspect the repository
2. determine the actual current state
3. reconcile the document
4. only then continue development

---

## 17. HANDOVER SUMMARY FOR A NEW AGENT

If you have only a minute, read this section.

```
PRODUCT:
Personal always-on Job Radar.
Fresh jobs + accurate matching + low-noise Telegram alerts.

RUNTIME:
Oracle Always Free VM + Docker + SQLite.

LINKEDIN:
Direct ingestion from Oracle. Proven.
Polling is approximately every 60 seconds with bounded fast/deep scanning.
Historical 429/rate-limit pressure exists and must be measured, not solved by blindly increasing request volume.
JD enrichment is required for cards missing experience; detail retrieval/parsing has a known BlueOptima-style incident under hardening.

NAUKRI:
Do NOT scrape from Oracle.
Oracle systemd timer → GitHub workflow → Naukri → relay branch → V2.
Proven and running every 5 minutes.

INSTAHYRE:
Experimental and disabled by default.

V2:
Running on port 8000.
No Chromium.

MATCHER:
Deterministic and phrase-aware.
Supports Software Engineer / Software Development Engineer / SDE variants.
Supports skill + generic developer/engineer title matching such as Javascript Developer.
Unknown experience is neutral for matching.
Configured maximum experience remains strict.
39 regression tests were green before the latest JD-hardening change; the latest branch now contains JD and today-only feed coverage and must pass the updated 43-test suite.

TELEGRAM:
Working.
Queued alerts require match + alertability + recent discovery.
The recent-discovery queue window is 10 minutes; failed delivery retries are still allowed after that window.
Fresh alert diagnostics must be counted by canonical opportunity, not source rows.

DEDUPLICATION:
Canonical opportunity layer is implemented conservatively.
Ambiguous cross-source overlap stays separate.
Do not count source rows as distinct alerts.

FRONTEND:
Dashboard uses V2 APIs and can target the deployed Oracle API during local development.
Friend's frontend work remains in progress; browser/product verification is still required.

V1:
Legacy job-watch Telegram workflow is inactive/disabled.

AGENT-REACH:
Parked as a future source-access optimisation.
Do not make it a runtime dependency until the core V2 MVP is stable and benchmarked.

NEXT:
Deploy JD hardening → verify 5–7-year extraction end-to-end → verify canonical alert counts → measure end-to-end latency → validate config persistence/recovery → finish frontend verification → changed-opportunity detection → MVP sign-off → benchmark Agent-Reach and expand sources.
```

## 18. SOURCE OF TRUTH HIERARCHY

When information conflicts, use this order:

1. **Actual deployed/repository code and observed runtime behavior**
2. **This handover document**
3. Older chat history / prototype notes

But when code changes intentionally, **update this document in the same milestone** so the next agent does not have to reverse-engineer the project again.

---

## 19. SUCCESS CRITERIA

Do not call Job Radar V2 successful merely because the API returns jobs.

V2 is successful when it can continuously:

1. detect fresh LinkedIn jobs repeatedly
2. detect fresh Naukri jobs repeatedly
3. preserve source posting and discovery timestamps separately
4. survive worker restarts without losing job history
5. identify genuinely new opportunities
6. deduplicate the same opportunity across sources
7. apply configurable deterministic preferences
8. reject obvious unsuitable jobs
9. provide explainable match reasons
10. send only worthwhile new matches to Telegram
11. expose the same useful information in the frontend
12. allow preference changes from the frontend without editing code
13. reset the visible daily feed and daily counts at India local midnight while retaining backend history
14. tolerate an individual source failing without taking down the radar

The final test is not "does it scrape?"

The final test is:

> **Can the user leave it running and trust that when Telegram rings, the job is probably worth opening?**


---

## 29. HISTORICAL DEBUGGING / OPERATIONS NOTES

These details are intentionally preserved because they explain why several architectural decisions must not be casually reversed.

### Oracle VM browser incident

The tiny Oracle VM previously reached approximately:

- load average ~15
- ~69% CPU steal
- ~13% iowait
- 208 zombie processes
- many Chromium / chrome_crashpad children

Stopping the old Docker runtime cleared the zombie buildup and returned the VM to a healthy idle state.

**Conclusion:** production V2 must remain browser-free unless there is compelling measured evidence otherwise.

### GitHub scheduler reliability

The project initially relied on frequent GitHub cron execution. Actual observed workflow history later showed long gaps, so a five-minute cron expression must not be described as guaranteed five-minute execution.

**Conclusion:** persistent scheduling belongs on the VM. GitHub Actions is a relay/acquisition worker where useful.

### V1 `seen.json` warning

V1 could add a rejected job to `seen.json`. This means a later configuration change could fail to reconsider it.

**Conclusion:** V2 must maintain separate observation/evaluation/alert state.

### Oracle host Python dependency note

The V2 suite should be executed inside the Docker image. The host Ubuntu Python may not have V2 dependencies such as `bs4`, and pip may not be installed.

Use the Docker test command documented in Observation 18 rather than modifying the host Python environment.

### GitHub CLI compatibility

The Ubuntu VM had an older GitHub CLI where `gh auth login --git-protocol ...` was unsupported. The working authentication path was:

```
gh auth login --hostname github.com --web
```

For run watching, use:

```
gh run watch <run-id> --repo AvinashBhalla/job-beeper --exit-status
```

Do not assume newer flags such as `--compact` exist.

---

## 30. DOCUMENTATION MAINTENANCE RULE


### Proactive documentation rule

This handover is not a passive artifact. Any significant code, runtime, architecture, source, alerting, matching, configuration, frontend or operational change must be reflected here during the same milestone. The active agent should inspect the current repository/runtime and update this file proactively; the user should not need to remind the agent.


After every significant milestone, update:

- Current release checkpoint
- Current important observations
- Immediate next steps
- Source status
- Runtime/deployment status if changed

When a feature is visually present but backend-incomplete, mark it incomplete.

When a source is present in code but unverified, mark it unverified.

When a scheduler exists only manually on the VM, do not describe it as repository-reproducible.

The repository and this file should be kept in sync deliberately.

## Dashboard UI Transplant — 2026-10-08

- Updated the three dashboard files on `v2-live-radar` using the friend fork's mature `frontend-live-dev` UI.
- Backend, collectors, matcher, notification pipeline, and runtime artifacts were not transplanted.
- The new dashboard adds the premium feed/inspector workspace, richer filters, theme control, applied tracking, preference editing, source health, responsive navigation, and match intelligence.
- Frontend API resolution was adapted so the dashboard uses an explicitly supplied API endpoint when present, otherwise the local relative API path.
- Commits: `e22e113`, `dd1c021`, `9612f21`.
- Next validation: run the browser against the Oracle API, then verify the deployed container and responsive UI.

## Dashboard Live-Feed Mismatch Diagnosis & Fix — 2026-10-08

- Browser validation exposed a real mismatch: the dashboard was displaying the friend's bundled `dashboard/data/jobs.json` static snapshot instead of the Oracle V2 feed.
- Direct cause: the local dashboard URL did not include `?api=<Oracle API>`; after the transplant, the frontend intentionally no longer hardcodes a remote API, so `/api` from a localhost static server is unavailable.
- The transplanted UI had inherited a static fallback. That fallback contained 57 jobs from 2026-10-07 across six sources: Arbeitnow, Greenhouse, LinkedIn, Naukri, Remotive, Smartrecruiters. These were not added to V2 source configuration.
- V2 repository configuration still has exactly three source controls: LinkedIn enabled, Naukri enabled, Instahyre disabled.
- The same fallback also fabricated source-health timestamps as current and labeled the sources operational, which could make an offline dashboard look live. This has been removed.
- `dashboard/app.js` now has no static job fallback, shows the feed as offline when the live API is unavailable, removes fake source-health success data, and constrains the source filter to exactly LinkedIn, Naukri, and Instahyre.
- This restores the product rule that the dashboard must represent the same live backend state that drives Telegram alerts; no alternate/static job dataset is permitted in the live radar UI.
- Telegram continued showing current alerts because the Oracle backend/notification worker was still running independently of the localhost dashboard.
- New fix commit: `5daaea7`.
- Local dashboard must be opened with the Oracle API query parameter, e.g. `http://localhost:5500/?api=http://<ORACLE_IP>:8000/api`.

## Freshness Investigation & Pre-Main Fix — 2026-10-08

- Manual Telegram acceptance found a Millennium LinkedIn alert with `Posted: 10:31 PM IST` and `Discovered: 10:38 PM IST`, a roughly 7-minute publication-age-at-discovery gap.
- This timestamp gap does not by itself prove a 7-minute polling delay: LinkedIn exposes a relative/approximate posting time and the system only knows the exact time it first observes the job. The correct operational goal is therefore low discovery latency, not falsifying timestamps to make posted and discovered identical.
- The existing LinkedIn scheduler already runs the fast lane at a 60-second minimum, but the fast lane was restricted with `f_EA=true`, while the slower deep scan is run every 5 minutes without that filter. This could defer non-Easy-Apply postings to the deep lane.
- Corrective change: removed `f_EA=true` from the LinkedIn fast lane so every fast scan searches the full result set. This should reduce avoidable multi-minute discovery delays and improve fresh-job coverage.
- Added regression coverage so the fast lane must not reintroduce an Easy-Apply-only filter.
- Also fixed Source Health semantics: the API now explicitly reports the three configured sources (LinkedIn, Naukri, Instahyre) with an `enabled` flag, and the dashboard no longer treats an old disabled-source run as ACTIVE.
- New commits: `4e26aa5` (backend freshness + source health), `1fa8b50` (regression test).
- Before moving `v2-live-radar` to `main`, CI must pass and the live Oracle deployment must be updated with the freshness fix. After deployment, measure actual LinkedIn discovery-age distribution instead of relying on a single posting.
