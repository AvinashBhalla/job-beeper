# Job Radar V2 — Agent Handover & Product Source of Truth

> **Purpose:** This document is the durable handover for Job Radar V2.
> A future agent should read this file before making architectural or product changes.
> Do not depend on chat history being available.

**Last updated: 2026-10-09 (Greenhouse public-board source merged as opt-in; PR CI #286 passed; Oracle deployment still at the verified Naukri cache-busting release)**
**Active branch:** `v2-live-radar`  
**Repository:** `AvinashBhalla/job-beeper`

> **Current-state reconciliation (2026-10-09):** The latest confirmed Oracle deployment is still commit `f91f047ca6e71c69492a03f0bafaf7b18362f613` (`Bust cache when polling public Naukri relay`). The cache-busting change was reviewed in [PR #5](https://github.com/AvinashBhalla/job-beeper/pull/5); PR CI [run #283](https://github.com/AvinashBhalla/job-beeper/actions/runs/37925152682) and post-merge CI [run #284](https://github.com/AvinashBhalla/job-beeper/actions/runs/37925221172) passed. The Oracle container was rebuilt and `/health` returned `status=ok`, version `2.0.0`. The public relay [run #16](https://github.com/AvinashBhalla/job-beeper-naukri-relay/actions/runs/37924632737) published a valid feed with 359 jobs; the next radar scan reported `jobs_seen=359`, `new_jobs=0`, and `error=null`. The cache-busting change reconciled the prior 345-versus-359 mismatch; stale caching was the plausible cause, not proven in isolation. The old VM user-crontab entry that dispatched the private repository relay every five minutes was removed after backing up the crontab. Its untracked `logs/` and `scripts/` were moved to `/home/ubuntu/job-beeper-local-backup-20261009`. The public relay continues on its own five-minute GitHub Actions schedule. PR #6 added the Greenhouse collector and dashboard integration in repository commit `1cfd55b28b4409d71aee3ca3fe1db314d9aa766f`, with pre-merge CI [run #286](https://github.com/AvinashBhalla/job-beeper/actions/runs/37927758499) passing. **That Greenhouse change is not yet deployed on Oracle and remains disabled by default.** Telegram delivery is active; Agent-Reach remains parked and is not a production dependency.

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

Current production approach (verified after deployment of commit `3e5b51b`):

- public logged-out guest jobs endpoint; do not rely on authenticated MCP/browser execution in production
- stable LinkedIn job IDs for deduplication
- source-posted time kept separate from first-discovery time; never invent timestamp precision
- six-hour search recency window (`f_TPR=r21600`)
- search requests are sequential/bounded with `LINKEDIN_SEARCH_WORKERS = 1`
- `LINKEDIN_FAST_TARGETS_PER_SCAN = 4`: the default 4-query × 4-location configuration is visited in four scan cycles, not two
- fast target cursor advances round-robin across query/location pairs; cursor is process-local and resets on container restart
- deep scan interval is `LINKEDIN_DEEP_SCAN_SECONDS = 900` (15 minutes)
- deep pagination is limited to one extra page (`start=10`) for the current four fast-lane targets; a normal deep cycle therefore reports 8 requests (4 first-page + 4 deep-page requests)
- a 429 on any fast-lane request suppresses deep pagination for that same scan; do not compound rate limiting with more requests
- plausible alert candidates may be enriched with the bounded detail worker pool; public guest detail responses can still omit poster-added experience requirements
- persistent runtime query lists are repaired by config-version migration so stale `/data/config.json` query families do not silently remove important role variants

The polling interval is a scheduling target, not a guarantee of job-discovery latency. Search visibility, scan duration, target rotation and source-side throttling all affect actual freshness. Measure current p50/p90/max with a short window after rollout and inspect the logs for `requests`, `failed_requests`, `unique_jobs`, and `new` before changing settings.

Production evidence after the latest deployment: the supplied 30-minute log sample showed nine scans with `failed_requests=0`, one deep scan at `requests=8, elapsed=4.3s`, and subsequent fast scans at `requests=4, elapsed≈1.9–2.6s`. This is encouraging but only a small observation window; do not claim zero ongoing 429 risk based on it.

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

### Agent-Reach — experiment completed and parked

Agent-Reach was evaluated and then actually exercised on the Oracle VM so the project could make a decision from runtime evidence rather than documentation claims.

Experiment environment:

- Agent-Reach v1.5.0 installed in the isolated `~/.agent-reach-venv`
- Agent-Reach was **not** installed into the Job Radar repository or V2 Docker image
- LinkedIn MCP Server v4.26.2 was run through `uvx mcp-server-linkedin@4.26.2`
- Lightweight TigerVNC + Openbox was used only to provide an X display for the headed browser on Oracle
- Node.js 22.23.3 was installed with `nvm` for MCP Inspector tooling; the existing system Node runtime was not replaced

Authentication experiment:

1. A fresh `--login` from the Oracle datacenter browser stalled at LinkedIn's security-check page.
2. LinkedIn login was completed successfully through the managed MCP browser on Windows.
3. Windows `--status` confirmed a valid source session.
4. The portable MCP session artifacts were transferred to Oracle.
5. Oracle `--status` recognized the Windows-authenticated source as a foreign-runtime profile and prepared a fresh Linux bridge.

End-to-end bridge result:

- MCP `initialize` succeeded on Oracle.
- `tools/list` succeeded and exposed LinkedIn job capabilities including `search_jobs` and `get_job_details`.
- During the first real authenticated tool execution, the Linux browser was created successfully and imported 5 LinkedIn bridge cookies, including `li_at`.
- The VNC browser visibly reached the authenticated LinkedIn feed.
- Therefore **Windows authentication → portable session → Linux Chromium bridge → authenticated LinkedIn page is proven**.

Failure boundary:

- Real read-only MCP tool calls such as `get_my_profile` and `search_jobs` did not complete.
- The MCP Inspector client timed out after 60 seconds, while the MCP server eventually hit its own 180-second tool timeout.
- The server logged that the optional remember-me container did not appear, but the source code gives that selector check a bounded 3-second timeout and returns `False`; this is not sufficient evidence that the remember-me check itself is the root cause.
- The remaining failure is therefore in the post-bridge browser/tool execution path (navigation/extraction/runtime interaction), and it was **not fully resolved** during the experiment.
- After the failed tool execution, the browser was cleaned up, so it disappearing from VNC is expected.

Decision:

- **Do not integrate Agent-Reach or authenticated LinkedIn MCP into V2 production now.**
- Do not replace the current LinkedIn guest collector because of this experiment.
- Do not make Agent-Reach a scheduler, source, or runtime dependency.
- Keep the isolated Oracle Agent-Reach environment available only for future controlled benchmarking.
- Revisit only after core V2 MVP acceptance is complete, and preferably with a fresh upstream/runtime benchmark rather than continuing indefinite debugging on the current Oracle setup.

The main learning is important: **Agent-Reach can solve access/authentication mechanics, but that does not prove fast, reliable production job acquisition. Source completeness, tool reliability, latency, rate-limit behavior, and resource cost still need empirical validation.**

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

- target roles- keywords
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

### Agent-Reach experiment runtime (isolated)

Agent-Reach is not part of the V2 Docker runtime. The Oracle experiment used:

- `~/.agent-reach-venv`
- `uvx mcp-server-linkedin@4.26.2`
- TigerVNC + Openbox only to provide a private X display
- Node.js 22 via `nvm` for MCP Inspector tooling

No Agent-Reach process, browser session, or credentials are required by the production V2 service.


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
✅ LinkedIn conservative polling deployed: 4 first-page targets per scan, one search worker, 15-minute deep-scan interval, one extra page only for current fast targets, and a 429 guard that skips deep pagination
✅ Experience-range parser fixed to preserve hyphen/en-dash ranges
✅ Runtime config migration hardened: pre-v3 configs disable unverified Instahyre
✅ Canonical opportunity schema and conservative cross-source linking implemented✅ Canonical opportunity API and dedupe diagnostics implemented
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
✅ Latest V2 GitHub Actions run #281 passed on commit `3e5b51b`: 53 unit tests green
✅ Latest 53-test V2 suite is green in GitHub Actions; includes LinkedIn 429/deep-scan guard and date-only Naukri latency regression coverage
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
✅ Agent-Reach v1.5.0 evaluated in an isolated Oracle environment without coupling it to V2 production
✅ LinkedIn MCP v4.26.2 authenticated session bridge proven end-to-end from Windows source session to Oracle Linux Chromium
✅ MCP initialization and tool discovery proven on Oracle; `search_jobs` / `get_job_details` exposed
✅ Agent-Reach experiment stopped at the real-tool execution boundary because authenticated read operations still hang; integration is deliberately parked rather than promoted to production
```

### Currently in progress

> **MVP implementation status:** Core V2 implementation is feature-complete. Remaining work is acceptance validation, operational hardening and bug fixing only. Agent-Reach is parked and is not part of MVP delivery.

```
✅ Latest V2 code path uses a 60-second LinkedIn fast poll, six-hour fast/deep recency, full query/location coverage, 2 bounded search workers and 4 JD-detail workers
✅ Persistent runtime config is version 5 with expanded LinkedIn/Naukri query families and Instahyre disabled
✅ Naukri relay artifact verified on the private `naukri-relay` branch (150 jobs, updated 2026-10-09 05:04 UTC); production 404 traced to unauthenticated raw URL access after repo privatization; collector now uses authenticated Contents API with `JOB_RADAR_GITHUB_READ_TOKEN` and fails fast on 401/403/404
✅ 43-test V2 Docker regression suite is green on the hardened branch
✅ BlueOptima-style 5–7-year JD extraction is hardened and verified at the parser/evaluation layer
✅ Agent-Reach/authenticated LinkedIn experiment completed to a decision point and deliberately parked
✅ LinkedIn fast-lane burst reduction restored: with 4 configured locations, fast cycles now cover 2 rotating locations per minute (8 search requests/minute across 4 query families), while the 5-minute deep scan still covers all locations; CI run 37844340637 is green
⏳ Re-test LinkedIn freshness using a short post-fix window and measure discovery-age distribution plus 429/failure rate
⏳ Verify Naukri relay reliability across several normal five-minute cycles after the transient-404 retry change
⏳ Manual acceptance: measure true end-to-end alert latency from source discovery through evaluation/JD enrichment/queue/Telegram
⏳ Manual acceptance: classify currently non-sent matching opportunities and verify canonical-level notification decisions
⏳ Manual acceptance: validate runtime configuration changes from frontend/API through reevaluation and notification reconsideration
⏳ Manual acceptance: validate restart/recovery with persisted config, evaluations and notification ledger
⏳ Manual acceptance: finish browser verification of the live dashboard against real V2 API data
⏳ Manual acceptance: validate source-health UI and remaining convenience features
⏳ Final V2 MVP sign-off after manual acceptance checks pass
⏸️ Agent-Reach: no further debugging during MVP; revisit only for controlled post-MVP benchmarking
```
### V1 status

The legacy `job-watch.yml` Telegram workflow is no longer active. GitHub reports it as inactive/not listed in the active workflows; V2 is now the sole intended Telegram alert path. Other active workflows such as `check-sources`, `naukri-relay`, `deploy-dashboard`, and `V2 CI` do not replace the V2 Telegram worker.
## 12. IMMEDIATE NEXT STEPS


### Current priority override — post-deploy source strategy (2026-10-09)

The earlier checklist below remains useful product acceptance work, but this priority order reflects the latest verified runtime and supersedes stale polling/deployment steps in historical sections 40–42.

1. **Observe the current deployment before tuning again.** Commit `3e5b51b` is on the VM and the container is healthy. Recheck logs/source status after another short window; compare request count, failed requests/429s, elapsed time, unique jobs and new jobs. Do not change scan settings if the reduced-pressure behavior holds.
2. **Measure freshness honestly.** Use recent samples and inspect individual job timestamps. The currently supplied 24-hour aggregate was LinkedIn p50=900s, p90=7200s, max=21600s; Naukri p50=115407s. These are mixed historical samples, not a current post-deploy SLA. Date-only Naukri posting timestamps now have `discovery_latency_seconds=null` because exact latency cannot be inferred from a date-only value.
3. **Expand independent sources, starting with structured ATS feeds.** Build and test source-specific adapters for Greenhouse, Lever and Ashby before adding broad HTML/browser scraping. Keep each collector isolated so a failing source cannot stop another.
4. **Preserve the existing normalize → canonical identity/dedupe → match/alertability → notification-ledger pipeline.** New sources must use it rather than adding a second alert path. Validate full descriptions/experience extraction before allowing a source to generate Telegram alerts.
5. **Treat aggregators as a controlled experiment, not a dependency.** Compare an optional Google-for-Jobs discovery API/provider (e.g. OpenWeb Ninja) and/or a small Apify scraper trial against direct sources on freshness, relevant-new-jobs yield, description completeness, duplicates, stability, monthly request allowance and actual cost. Provider tiers and terms change; re-check them before use.
6. **Do not implement proxy rotation, CAPTCHA workarounds, or a headless-browser cluster to evade LinkedIn controls.** Public descriptions do not establish JobBeeper’s private implementation details. Prefer independent permitted sources and lower-volume collection.
7. **Keep privacy and cost boundaries intact.** The application repository and user preferences remain private. The separate public Naukri relay may publish only its intended job feed and setup/workflow files; never publish app code, secrets, user config or SQLite state.

Acceptance gate before expanding production scope: stable consecutive source runs, last-good data preserved on failures, measured freshness and 429 rate, validated job experience where needed for alerts, correct canonical notification state, and green CI plus a verified VM deployment.


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

Measure both alert latency and source freshness (the current API exposes p50/p90/max source-discovery latency):

```
source posting
 → source discovery
 → normalization/evaluation
 → JD enrichment when required
 → notification decision
 → queue
 → Telegram send
```

Record median, p90 and max latency.

### Step D — Validate runtime configuration + recovery

Verify frontend/API changes persist in /data/config.json, trigger evaluation/notification reconsideration correctly and survive container restart.

### Step E — Finish frontend verification

Validate live refresh, current-day feed, daily counters, filters/settings, job details, source health and direct apply links.

### Step F — Changed-opportunity detection

Define material changes including experience requirements, description/requirements, location/work mode and application URL changes, then reconsider without duplicate alerts.

### Step G — Keep Agent-Reach parked during MVP acceptance

The initial Agent-Reach experiment is complete enough to make the current decision. Do not spend more MVP time debugging the authenticated MCP browser path. After V2 sign-off, a new controlled benchmark may compare Agent-Reach/LinkedIn MCP against the guest collector for freshness, JD completeness, latency, 429/failure rate, session reliability and Oracle resource usage.

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
Posted:     6:28 PM ISTDiscovered: 7:28 PM IST
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


### Observation 19 — Agent-Reach was taken from theory to a controlled runtime experiment

The project did not stop at documentation-level evaluation. Agent-Reach v1.5.0 plus LinkedIn MCP v4.26.2 were actually exercised on Oracle.

The experiment proved the authentication bridge path:

```
Windows authenticated LinkedIn session
        ↓
portable MCP source session
        ↓
Oracle foreign-runtime bridge
        ↓
Linux Patchright Chromium
        ↓
LinkedIn authenticated feed
```

The experiment then failed at the next boundary: real MCP read operations such as `get_my_profile` and `search_jobs` hung until the server-side 180-second tool timeout.

The source inspection also showed the logged "remember-me container did not appear in time" message is only a bounded 3-second selector wait that returns `False`; it should not be treated as the proven root cause. The exact post-bridge navigation/extraction hang remains unresolved.

Product conclusion:

- Authentication portability is feasible.
- Agent-Reach does **not** currently provide a reliable production LinkedIn acquisition path on this Oracle environment.
- This experiment is enough evidence to park the integration rather than spend more MVP time debugging it.
- The correct future evaluation is a controlled benchmark against the existing collector, not a production replacement motivated by platform breadth alone.

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
Current deployed scan settings: 4 first-page query/location targets per scan, one search worker, six-hour recency filter, 15-minute deep-scan interval, and at most one extra page for the current batch. With the default 16 pairs, a full first-page pass takes 4 cycles.
The deployed commit is `3e5b51b`; CI run #281 passed all 53 tests. The initial post-deploy log window showed nine scans with zero failed requests, but continued observation is required. Historical 429/rate-limit pressure must not be solved by blindly increasing request volume.
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
The latest V2 GitHub Actions run passed 53 tests, including the LinkedIn round-robin, 429/deep-scan guard and date-only Naukri latency regressions.

TELEGRAM:
Working.
Queued alerts require match + alertability + recent discovery.
The recent-discovery queue window is 10 minutes; failed delivery retries are still allowed after that window.
Fresh alert diagnostics must be counted by canonical opportunity, not source rows.

DEDUPLICATION:
Canonical opportunity layer is implemented conservatively.
Ambiguous cross-source overlap stays separate.
Do not count source rows as distinct alerts.
FRESHNESS / SOURCE ROADMAP:
Prioritize structured ATS/career feeds (Greenhouse, Lever, Ashby) as independent adapters. Keep aggregator providers as measured optional POCs, not assumptions of instant or free coverage. JobBeeper’s private use of multi-tenant pooling, proxy pools, or headless clusters is not publicly verified.
Do not add proxies/CAPTCHA workarounds to evade source controls. Measure actual freshness and request failures.

FRONTEND:
Dashboard uses V2 APIs and can target the deployed Oracle API during local development.
Friend's frontend work remains in progress; browser/product verification is still required.

V1:
Legacy job-watch Telegram workflow is inactive/disabled.

AGENT-REACH:
Experiment completed. Windows-authenticated session → Oracle foreign-runtime browser bridge works, but real LinkedIn MCP read tools still hang on Oracle. Parked; not a V2 dependency.
Do not resume during MVP acceptance.

NEXT:
Verify post-fix LinkedIn freshness/429 behavior → verify Naukri relay reliability → verify canonical alert counts → measure end-to-end latency → validate config persistence/recovery → finish frontend verification → changed-opportunity detection → MVP sign-off → only then benchmark Agent-Reach and expand sources.
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

## Pre-Main Repository Hygiene — 2026-10-08

- Before promoting V2 to `main`, identified two repository-level inconsistencies.
- The legacy `.github/workflows/job-watch.yml` still had a five-minute schedule even though the handover described V1 scheduled polling as inactive. The schedule is now disabled; the workflow remains manual-only for recovery/debugging.
- The production Naukri relay workflow was present on `main` but absent from `v2-live-radar`. It has now been carried into V2 so promotion to `main` does not accidentally remove the relay scheduler contract.
- The Naukri relay still publishes its data to the dedicated `naukri-relay` branch and V2 reads that relay; generated relay data on `main` is not part of the V2 runtime source of truth.
- These changes are part of the pre-main cleanup. V2 CI must be green on the final branch head before promotion.

## Main Promotion — 2026-10-08

- Job Radar V2 has now been promoted to `main`.
- Main is now the production development/source-of-truth branch for V2. The `v2-live-radar` branch remains as the pre-promotion implementation checkpoint.
- Promotion was performed as an explicit merge commit so the V2 tree became the main tree while preserving the Naukri relay workflow contract.
- The legacy V1 scheduled `job-watch` workflow is disabled; only its manual recovery path remains.
- The Naukri relay workflow is present on main and continues to publish the relay to the dedicated `naukri-relay` branch.
- The premium dashboard, live-feed mismatch fix, three-source UI restriction, Source Health correction, LinkedIn fast-lane freshness fix, and related regression coverage are included in main.
- Next operational step: update the Oracle Docker deployment from the old runtime to this main revision, then measure LinkedIn discovery latency on real fresh postings. Development after this point should branch from/main-track `main`.

## Post-Main Runtime Findings & LinkedIn Burst Reduction — 2026-10-08

- After rebuilding `main` on Oracle, the V2 container is healthy and the live API responds correctly.
- Runtime inspection exposed configuration drift: Instahyre was disabled in repository defaults but the persistent `/data/config.json` still allowed it, so the scheduler attempted Instahyre and received HTTP 400. This was not a new production source decision; it was stale runtime configuration.
- V2 config migration was advanced to version 4. Runtimes upgraded from pre-v4 configuration now force Instahyre back to the intended disabled-by-default state while preserving other settings. Added regression coverage for this migration.
- LinkedIn still shows 429 pressure. The previous fast lane removed the Easy Apply restriction, but it was still issuing 4 query families × 4 locations every minute (16 search requests/minute), plus retries and periodic deep scans.
- Corrective change: the fast lane now rotates through two of the configured four locations per 60-second cycle, so every target location is covered across two cycles while reducing the fast search burst from 16 requests to 8 per cycle. Search/detail worker concurrency was also reduced from 6 to 4 to reduce burst pressure on LinkedIn.
- The 5-minute deep scan still covers the complete configured location set.
- This is a measured compromise between freshness and rate-limit pressure: target location coverage remains within roughly two fast cycles under normal runtime conditions, while request bursts are materially smaller.
- New commits on `main`: `520da25` (scan-burst reduction + config migration), `6bf496c` (config version), `8b6f558` (migration regression test).
- Next Oracle action after CI passes: rebuild the container again so the v4 migration and reduced-burst LinkedIn collector become active. Then inspect `/api/config` to confirm Instahyre is false and inspect LinkedIn source runs/latency over several fresh postings.

## Critical LinkedIn Delay Root Cause — 2026-10-08
- Manual acceptance found a severe case: Infosys `AI-Driven - Full Stack Engineer` was shown by LinkedIn as posted around 6:13 PM IST but was first discovered/alerted around 11:13 PM IST.
- Runtime `/data/config.json` exposed the root cause: although repository `v2/config.json` had the broadened LinkedIn query families, the persistent runtime configuration had an older narrowed set that did not include `full stack engineer`, `react engineer`, `python engineer`, `frontend engineer`, `backend engineer`, or other required variants. Therefore the live Oracle collector was not actually searching the same query vocabulary as the repository.
- The alert was delayed because the posting did not enter the fast lane through the missing query variant; the slower/deeper scan eventually found it. The timestamp gap therefore represented a real acquisition/coverage failure, not a Telegram delivery delay.
- V5 config migration now treats LinkedIn/Naukri query families as repository-owned configuration and repairs stale persisted runtime query sets when upgrading from a pre-v5 runtime. This keeps the deployed collector aligned with the GitHub source of truth.
- LinkedIn fast recency window is now 6 hours instead of 1 hour, so a job missed by a transient query/source condition can still be found by the fast lane without waiting for the periodic deep scan.
- Existing fast-lane Easy Apply restriction was already removed. Search concurrency is bounded to reduce 429 pressure.
- CI on the latest `main` head is green after correcting the V5 migration test semantics.
- The next production validation must rebuild Oracle from latest `main`, confirm the live runtime query list contains the full repository vocabulary, then measure fresh LinkedIn discovery latency and 429 frequency over multiple cycles.

## Runtime Validation — 2026-10-08

- Oracle was rebuilt successfully and the persisted runtime configuration is now version 5 with the intended expanded LinkedIn/Naukri query sets and Instahyre disabled.
- The 24-hour latency sample is not a current-SLA measurement: LinkedIn p50 is 44 minutes and p90/max are 6 hours, while Naukri p50 is about 33 hours. These values include historical first-discovery samples gathered before the latest query/config fixes and therefore should not be treated as the post-fix latency baseline.
- Current runtime logs after the rebuild showed LinkedIn succeeding without a 429 in the sampled window, including a cycle with 131 jobs seen and 13 new jobs; Telegram delivered 4 alerts.
- Naukri returned HTTP 404 from an unauthenticated `raw.githubusercontent.com` URL after the repository was made private. The relay artifact itself exists on `naukri-relay`: the authenticated GitHub connection verified `dashboard/data/naukri_relay.json`, with 150 jobs and `updated_at=2026-10-09T05:04:08Z`. This makes private-content access the high-confidence root cause, not a missing workflow output path.
- The Naukri collector was changed to fetch through GitHub's authenticated Contents API (`Accept: application/vnd.github.raw+json`) using a fine-grained `JOB_RADAR_GITHUB_READ_TOKEN` restricted to this repository and Contents:read. The Docker Compose service passes that environment variable from the ignored VM `.env`. HTTP 401/403/404 are configuration/permission failures and are not retried; 429/5xx/network failures retain bounded retries.
- Deployment remains pending until the VM creates a least-privilege token, adds it to `.env`, pulls the branch, and rebuilds the container.
- CI is green for the Naukri retry change.
- Next validation should use `/api/latency-summary?hours=1` after several fresh LinkedIn cycles and compare new Telegram alerts against dashboard jobs. Do not use the 24-hour aggregate as the post-fix SLA baseline.
- Platform expansion remains blocked until this short-window freshness check and LinkedIn experience acquisition are validated.
## 31. AGENT-REACH EXPERIMENT — FINAL LEARNING & HANDOVER

This section records the exact decision boundary so a future agent does not repeat the same setup from scratch.

### What was proven

- Agent-Reach can be installed and kept completely isolated from the Job Radar repository.
- LinkedIn MCP v4.26.2 can create a valid authenticated source session on Windows.
- That session can be recognized on Linux as a foreign-runtime source profile.
- Oracle can create the Linux Patchright Chromium runtime from that foreign profile.
- The bridge can import the required LinkedIn cookies, including `li_at`.
- The bridged browser can visibly reach the authenticated LinkedIn feed in VNC.
- MCP HTTP transport, `initialize`, and `tools/list` all work.

### What was not proven

- `get_my_profile` did not complete.
- `search_jobs` did not complete.
- Therefore reliable authenticated LinkedIn job acquisition through the MCP tool layer is **not proven**.

### Why this matters to Job Radar

The original reasons for exploring Agent-Reach were speed, richer authenticated JD content, future source coverage and reduced bespoke scraping. The experiment only established the access/authentication half. It did **not** establish the operational half needed by a continuously running job radar: predictable tool latency, robust navigation/extraction, controlled request volume, and stable long-running sessions on the small Oracle VM.

### Decision

```
CURRENT V2 COLLECTORS
    ↓
remain production

AGENT-REACH / LINKEDIN MCP
    ↓
parked after controlled experiment
    ↓
revisit only post-MVP via benchmark
```

Do not modify `main` or `v2-live-radar` source ingestion code solely because of this experiment. The production LinkedIn collector remains the guest/API-style collector already implemented in V2, and Naukri remains the GitHub relay path.

### Future benchmark, when justified

A future benchmark should compare the two paths over the same controlled time window and record:

- fresh-job discovery latency
- JD completeness, especially poster-added experience requirements
- tool failure/timeout rate
- LinkedIn 429/failure frequency
- duplicate rate
- session persistence/re-authentication frequency
- CPU/RAM impact on Oracle
- number of source requests per useful job

Only a measured win should justify replacing or augmenting the production collector.



## 32. Live acceptance checkpoint and scraper strategy — 2026-10-09

### Live evidence

The latest Oracle health response reports V2 healthy, config version 5, LinkedIn enabled, Naukri enabled but failing its relay fetch, and Instahyre disabled. The failing request was the anonymous raw URL; the relay branch artifact exists and contains 150 records. The private-repo 404 is addressed in code with the authenticated GitHub Contents API, but production is not considered fixed until the VM has a read-only token configured and the next source run succeeds. Commit `66145ba49696981201500c3184d9ae94c7ee386d` has passed V2 CI with 50 tests; deployment still needs the VM token and rebuild.

The latest `/api/latency-summary?hours=1` observed LinkedIn `p50=2040s` (34 minutes), `p90=3600s` (60 minutes), `max=21600s` (6 hours), and only 7 samples under five minutes out of 43. In code this field is the difference between source-posted time and first discovery when the source posting precision supports it; it is not merely the collector's internal processing duration. Treat it as an estimated posted-to-discovery metric and keep its source timestamp precision in mind.

### Correct order of work

1. Restore authenticated Naukri relay access without making the repository public. Add a fine-grained token with only this repository's Contents:read permission to the VM's ignored `.env` as `JOB_RADAR_GITHUB_READ_TOKEN`; never put it in git or chat. Rebuild and verify `/api/source-status`, relay update time, and Naukri rows ingested.
2. Resolve the GitHub Actions budget before accepting the relay schedule. Recent relay runs trigger about every five minutes and take ~1m45s–2m33s. At ~8,640 runs per 30-day month, that is roughly 15,000–22,000 runner-minutes if the cadence continues. GitHub Free includes 2,000 minutes/month for private-repository GitHub-hosted runners. Do not leave the five-minute private-repo cadence running indefinitely without checking usage/billing. Decision approved 2026-10-09: create a separate public relay-only repository `AvinashBhalla/job-beeper-naukri-relay`, while keeping `AvinashBhalla/job-beeper` private. The public repo will expose only a small scheduled Naukri collector workflow, its setup notes and the generated public job feed. It will read the private repo's `config.json` using a fine-grained `PRIVATE_APP_READ_TOKEN` secret limited to Contents: read on `AvinashBhalla/job-beeper`; it must not mirror or publish private application files. The private app will read the generated public raw JSON URL without a runtime GitHub token. The connected GitHub tool cannot create a repository, so a human must first create an empty public repo with that exact name; then populate it, verify one successful feed publication, switch/verify the consumer on the VM, and stop the old private workflow timer.
3. Improve LinkedIn freshness without increasing request volume blindly. There are observed HTTP 429s on deep `start=10` scans. Keep the location rotation, measure the next 1–2 hours, and tune deep-page frequency/rotation only with source-run and latency measurements. Do not use the authenticated MCP browser experiment in production: its login bridge worked, but real tool calls still hung.
4. Test one alternative source adapter in isolation, not all sources at once. JobSpy is a plausible low-cost benchmark and already powers the Naukri relay, but upstream docs note LinkedIn rate-limit sensitivity and issue reports include incomplete descriptions. Compare actual jobs found, complete-JD rate, freshness, 429s, run duration and cost before enabling Telegram alerts from a new adapter.
5. Make ATS job feeds the first expansion candidate. Greenhouse, Lever and Ashby publish structured job-board endpoints, and SmartRecruiters has a public postings API. This is a better fit for the tiny Oracle VM than running a browser farm; the trade-off is curated company coverage rather than whole-market discovery.
6. Do not put Firecrawl or Crawl4AI in the critical collector path yet. Firecrawl's current hosted free tier is 1,000 credits/month and a normal page scrape uses one credit; self-hosting loses the managed anti-bot/proxy layer and adds infrastructure. Crawl4AI is an open-source browser crawler but consumes the same constrained VM resources. Keep these as limited evaluation tools for awkward ATS pages, not a fix for LinkedIn/Naukri blocking.
7. Acceptance criteria before adding more production sources: Naukri succeeds on consecutive relay cycles; source errors are visible and do not wipe last-good data; Telegram matches the canonical ledger; experience extraction is verified against full descriptions; p50/p90/max freshness and 429 rates improve over a measured window; restart/config persistence is verified.

### Platform and budget cautions

- LinkedIn's own help documentation says third-party scraping/automation is not permitted and can risk account restrictions. Agent-Reach/MCP remains parked; do not reattempt CAPTCHA workarounds or use the authenticated account browser as a production crawler.
- GitHub's standard runner usage is free for public repositories; private repositories have plan-specific included minutes and may incur usage over the free allowance. Keep the repository private and do not move the entire application public merely to save runner minutes. If an isolated public relay is ever considered, document exactly which workflow/source code and generated job data would become public before changing anything.



## 33. External references reviewed for source strategy — 2026-10-09

- JobSpy supported sources and upstream limitations: https://github.com/speedyapply/JobSpy
- JobSpy reports LinkedIn as its most restrictive source and notes rate limiting around deeper pages; treat this as project guidance, not an independent benchmark.
- Firecrawl current billing/free-tier information: https://github.com/firecrawl/firecrawl-docs/blob/main/billing.mdx
- Firecrawl current rate-limit information: https://github.com/firecrawl/firecrawl-docs/blob/main/rate-limits.mdx
- Firecrawl open-source versus hosted service limitations: https://www.firecrawl.dev/crawl
- Crawl4AI self-hosted options and license: https://github.com/unclecode/crawl4ai
- Greenhouse public Job Board API: https://docs.greenhouse.io/job-board.html
- Lever public Postings API: https://github.com/lever/postings-api
- Ashby public Job Posting API: https://developers.ashbyhq.com/docs/public-job-posting-api
- LinkedIn official policy on prohibited scraping/automation: https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software
- GitHub Actions limits and included minutes: https://docs.github.com/en/actions/reference/limits
- GitHub Actions billing/public versus private repo guidance: https://docs.github.com/en/billing/concepts/product-billing/github-actions

Decision remains: repair relay delivery and validate existing sources before adding another production dependency. Firecrawl/Crawl4AI are not proposed as the primary LinkedIn/Naukri ingestion path; ATS public APIs and a controlled JobSpy alternative-source POC are the preferred next experiments.


## 34. Approved isolated Naukri relay decision — 2026-10-09

- **Private app repo remains private:** `AvinashBhalla/job-beeper`, active branch `v2-live-radar`. Never change its visibility.
- **New public relay repo:** `AvinashBhalla/job-beeper-naukri-relay` exists and is public. Its default branch is `main`; the scheduled workflow and setup README are committed.
- **Purpose of public repo:** run the JobSpy Naukri collection workflow on a scheduled public GitHub-hosted runner and publish only `dashboard/data/naukri_relay.json` to its orphan `naukri-relay` branch. The default branch should contain only relay workflow/setup documentation. Do not copy the private app repository into this repository.
- **Private source access:** add a fine-grained PAT as repository secret `PRIVATE_APP_READ_TOKEN` in the new public repo. Scope it to only `AvinashBhalla/job-beeper` with Contents: read permission. Do not paste the token into chat or commit it. The workflow checks out only `v2/config.json` from the private repo's `v2-live-radar` branch into a temporary runner directory; all workflow execution stays in the public repo for its public-runner budget.
- **Consumer code committed, not yet deployed:** `v2/radar.py` now reads `https://raw.githubusercontent.com/AvinashBhalla/job-beeper-naukri-relay/naukri-relay/dashboard/data/naukri_relay.json` anonymously, and the GitHub read-token environment variable was removed from `v2/docker-compose.yml`. Public feed URL will 404 until the new repository's first successful relay run; do not deploy/force-recreate the production container before verifying that URL returns a valid JSON payload with `updated_at` and `jobs`.
- **Remaining cutover steps:** configure the `PRIVATE_APP_READ_TOKEN` repository Actions secret with read-only access to the private app; run the public workflow manually; check feed timestamp/count and public raw URL; then deploy/verify the private app consumer and only then disable the old VM systemd timer that dispatches the private repo's relay workflow. Identify the exact timer name using `systemctl list-timers --all --no-pager | grep -i naukri`; disable only the matching relay timer. After cutover, retire the old private relay workflow to prevent duplicate runs.
- **Cost goal:** retain the roughly five-minute relay freshness on GitHub's public runner without making the main app repository public or spending private-repository runner minutes for recurring Naukri collection. Public feed visibility is intentional; credentials, user preference files, SQLite DB and the rest of the app must remain private.


## 35. Telegram precision safeguard — 2026-10-09

- **Decision:** require explicit captured job experience for Telegram alerts until the LinkedIn acquisition layer reliably captures poster-added requirements. Public guest job details can omit requirements shown in authenticated browser sessions; parser improvements cannot recover text that was never fetched.
- **Behavior:** jobs with unknown experience can still appear in the dashboard and match results, but are not eligible for Telegram alerts. Jobs with explicit experience continue through the existing configured experience-fit rules.
- **Implementation:** v2/config.json now uses config version 6 and sets require_explicit_experience_for_alerts=true. The V6 runtime-config migration forcibly applies this safeguard to persisted configurations from V5 or earlier, rather than leaving the live VM's saved false value in place. A unit test covers this migration.
- **Operational note:** this changes the live effective preference on next application startup/config reload. It does not delete stored jobs or historical notification records. Existing queued notifications are revalidated against current alertability before delivery.
- **Acceptance gate:** keep this safeguard until production tests demonstrate reliable capture of explicit experience from the actual source acquisition path. Do not claim the acquisition limitation is solved by parser-only changes.


## 36. Naukri relay last-good-feed guard — 2026-10-09

The private relay workflow now fails rather than publishing a zero-job feed. This protects the existing public relay artifact from being replaced by an empty result when Naukri blocks the runner or collection silently fails. Validate the workflow run after relay isolation is completed; this guard is not deployed to the public relay because that repository still needs to be created.


## 37. Relay bootstrap staged — 2026-10-09

Prepared the isolated public relay workflow and setup README under `docs/relay-bootstrap/` on `v2-live-radar`. The workflow runs every five minutes on a public runner, checks out only `v2/config.json` from the private app using `PRIVATE_APP_READ_TOKEN`, publishes only the generated Naukri feed to the relay branch, and refuses to replace the last-good feed with an empty result. V2 CI passed after the empty-feed guard commit. The public repository now exists, and `.github/workflows/naukri-relay.yml` plus its README are committed. The workflow reads only the private config file from `v2-live-radar`, uses the configured Naukri queries and locations, and publishes only the generated feed. The repository currently has no workflow runs, so configure `PRIVATE_APP_READ_TOKEN`, run the workflow manually, and verify fresh JSON at the raw feed URL before changing production timers. No production deployment or timer change has been made.


## 38. Public relay repository created — 2026-10-09

- Repository: `AvinashBhalla/job-beeper-naukri-relay` (public), default branch `main`.
- Added `.github/workflows/naukri-relay.yml`: five-minute schedule and manual dispatch; sparse-checks out only `v2/config.json` from private branch `v2-live-radar`; collects configured Naukri queries across configured locations; fails on empty results; publishes only `dashboard/data/naukri_relay.json` to branch `naukri-relay` without force-pushing.
- Added README with setup and validation instructions. GitHub API currently reports zero workflow runs, so the feed has not yet been generated/validated.
- **Still required:** add repository Actions secret `PRIVATE_APP_READ_TOKEN` with read-only access to the private app, run workflow manually, validate raw JSON and freshness, deploy/recreate the V2 app on the Oracle VM and verify `/api/source-status`, then disable the old private-repo relay timer only after the new path is confirmed working. The Oracle VM and its timer have not been changed from this chat.


## 39. Public Naukri relay first-run verified — 2026-10-09

- **Successful manual run:** [public-naukri-relay run 37902413775](https://github.com/AvinashBhalla/job-beeper-naukri-relay/actions/runs/37902413775), completed successfully on 2026-10-09 at 08:03 UTC. All collection and publish steps succeeded.
- **Published feed:** https://raw.githubusercontent.com/AvinashBhalla/job-beeper-naukri-relay/naukri-relay/dashboard/data/naukri_relay.json
- **Feed validation:** JSON returned successfully with `updated_at=2026-10-09T08:03:27.351028+00:00` and `count=226`; `jobs` is populated. Private config checkout succeeded and the workflow used the configured Naukri query/location keys.
- **Remaining production cutover:** the public feed is confirmed, but the Oracle VM consumer deployment and old private-repo timer have not been changed or verified from this chat. On the VM, update the working tree to the intended `v2-live-radar` commit, recreate the V2 container, and verify `/api/source-status` shows Naukri healthy/fresh. Only after this check, identify the exact old relay timer with `systemctl list-timers --all --no-pager | grep -i naukri` and disable that timer. Do not disable unrelated timers. Then confirm a subsequent public relay run updates the feed and confirm the app still reads it.
- **Security note:** public feed data intentionally contains job listings and descriptions. The private application repo remains private; no application source was copied into the public relay repo.



## 40. LinkedIn discovery CI fixes and throttling lessons — 2026-10-09

### Current branch and commits
- Active implementation branch for this work: `v2-live-radar`.
- Fixed stale location-rotation tests in `v2/test_radar.py`: commit `06a6179429d077042578a8dc54975bbde04b7128`. The production code no longer uses `linkedin_fast_location_cursor`; tests must verify every configured query/location is scanned each fast cycle, not expect rotation.
- Bounded deep-scan request bursts: commit `092a07187b8dca9ad33ad5f1cc7ed4967cffe285`.
- Updated deep-pagination test: commit `ac22c8845426184bfb84c06d5723edbf94502fe6`.
- Fixed telemetry after scan batching: commit `4c13835fcd98db3bd21d354d65f1dadb6ad1d000`. CI run [37913344863](https://github.com/AvinashBhalla/job-beeper/actions/runs/37913344863) passed, including Python compilation and the full V2 unit-test suite.
- Latest throttling mitigation commit: `60b14ba197772e5b0c569d99056458d44fb3e210` — reduce `LINKEDIN_SEARCH_WORKERS` from 3 to 2, reduce `LINKEDIN_DEEP_PAGE_BATCH` from 4 to 1, and stop retrying HTTP 429 inside the same scan. **At the time this handover note was written, its CI run was still in progress; verify CI before deploying.**

### Production observations from Oracle VM logs
The user supplied live logs from `sudo docker compose -f v2/docker-compose.yml logs --since=10m radar`:
- Deep scan: `queries=4 locations=4 requests=80 deep=True unique_jobs=217 failed_requests=5 elapsed=61.3s`; it added 47 new jobs.
- Fast scans: typically `requests=16`, `unique_jobs=83–84`, and `elapsed=2.8–3.2s` when successful.
- HTTP 429s occurred on several query/location/page combinations. One fast scan took 15.3s with one 429.
- Naukri log showed `seen=226 new=0`; this alone does not prove the feed is fresh or stale. Inspect the public relay JSON `updated_at` to verify freshness.

### Decisions and lessons — read before changing discovery
1. **Do not increase LinkedIn concurrency as the default response to slow discovery.** The 429 evidence shows the source is already throttling. More parallel requests can increase failures and reduce successful coverage.
2. **Protect the fast lane.** It searches the first/newest page for all configured query/location combinations. It is the reliable low-latency path; deep pagination should be bounded and must not delay every fast cycle.
3. **Keep deep scans small and separate.** The observed deep scan issued 80 requests and took 61.3 seconds, versus 16 requests and around 3 seconds for successful fast scans. The latest mitigation limits deep pagination to one additional page per query/location and uses two workers.
4. **Do not retry HTTP 429 immediately inside the same scan.** That multiplies traffic while the source is rejecting requests. Let a future scheduled scan retry; continue to honor sensible retry handling for transient 5xx errors. Revisit only with measured evidence and a rate-limit-aware design.
5. **Do not claim a one-minute scan interval guarantees one-minute discovery.** Search endpoint visibility, request duration, source throttling, and scheduling affect real discovery lag. Measure actual logs and job timestamps.
6. **Keep scan telemetry aligned with implementation.** When replacing a `targets` list with separate `fast_targets` and `deep_targets`, update request counts and tests in the same commit. A previous CI failure was caused by telemetry referencing the deleted `targets` variable.
7. **Update tests alongside behavior changes.** Old tests that asserted location rotation failed after rotation was intentionally removed. Update tests to assert full query/location coverage and bounded deep-page starts; do not restore obsolete production state just to satisfy stale tests.
8. **Historical red GitHub Actions runs remain red.** Judge current health from the latest commit's run, not whether the Actions history page contains old failed runs.
9. **No deployment should be claimed from a GitHub commit or green CI alone.** The Oracle VM must pull the intended commit and rebuild the Docker container. Confirm deployed commit and live logs separately.

### Next steps
- Check CI for commit `60b14ba197772e5b0c569d99056458d44fb3e210`. If red, fetch the job logs and fix the exact failing test/code before deployment.
- After CI passes, on `ubuntu@job-radar` in `~/job-beeper`, pull `v2-live-radar`, rebuild/recreate with `sudo docker compose -f v2/docker-compose.yml up -d --build`, then inspect the next 10 minutes of logs.
- Compare `elapsed`, `requests`, `failed_requests`, `unique_jobs`, and `new` across fast/deep scans. Confirm the deep scan no longer causes a long request burst and whether 429 frequency decreases.
- If 429s persist, reduce request frequency or use a compliant, permitted source/API rather than increasing parallelism. Respect LinkedIn's applicable terms and access controls.
- Stay focused on discovery until this is stable; do not start dashboard or Telegram feature work unless the user explicitly changes priority.



## 41. Follow-up: production still throttled; deep-page test mismatch — 2026-10-09

- New VM logs after the previous rollout still show widespread HTTP 429 responses across first-page searches and deep pages. The deep scan reported `requests=32 deep=True unique_jobs=75 failed_requests=15 elapsed=6.6s`, adding 2 new jobs. A fast scan later reported `requests=16 deep=False unique_jobs=82 failed_requests=0 elapsed=4.7s`, adding 4 new jobs; another fast scan had 6 failed requests. This indicates throttling remains intermittent and is not solved solely by reducing concurrency.
- The user may not have deployed the latest commit when sharing logs; always verify the running container's code/commit before attributing logs to a specific mitigation.
- CI for throttling mitigation commit `60b14ba` failed because `test_linkedin_fast_lane_and_periodic_deep_scan` still expected deep starts `[0, 10, 20, 30, 40]`, but the intended one-extra-page cap produces `[0, 10]`. Fixed assertion in commit `07973594927c7867d4ca4a4e0228556683871ecb`; check the latest CI run before deployment.
- Important lesson: when changing `LINKEDIN_DEEP_PAGE_BATCH`, update test expectations to reflect the cap. Do not leave a test expecting the previous four-page setting.
- Continue prioritizing fast scan coverage and measure 429s after deployment. If throttling persists, reduce how often all query/location pairs are hit (e.g. spread them across staggered cycles while keeping the most valuable/newest queries first) rather than increasing concurrency. Avoid evasion techniques; prefer a permitted API/source if LinkedIn continues rejecting automated requests.


## 42. Stagger LinkedIn discovery requests to reduce 429s — 2026-10-09

- Implemented commit `f3be91d`: LinkedIn no longer fires all 16 configured query/location first-page requests in every 60-second cycle. It rotates through an 8-target batch per cycle, so the default 16 pairs are covered across roughly two cycles.
- Deep pagination now applies only to the current small fast batch instead of every query/location pair. With the default 8-target batch and one extra page, a deep cycle targets at most 16 requests rather than 32, before any request retries for transient 5xx errors.
- Kept two search workers and the no-immediate-retry behavior for HTTP 429. This is a reduction in request pressure, not a guarantee that LinkedIn will stop throttling.
- Added a unit test in commit `962f09d` to assert that two consecutive fast cycles cover all configured query/location pairs without duplicate first-page targets in that two-cycle window.
- Next: verify CI for the latest branch commit. If green, deploy on the Oracle VM with `git pull origin v2-live-radar` followed by `sudo docker compose -f v2/docker-compose.yml up -d --build`. Confirm the container's behavior from logs: each fast scan should report 8 requests by default; a deep scan should report 16 total requests; check whether 429s decrease over at least 10 minutes.
- Caveat: the round-robin cursor is process-local and resets on container restart. This only affects which batch is scanned first after a restart; all pairs should still be covered across two cycles.


### CI follow-up for section 42
- The first staggered-scan test failed because its fixture contained only 8 query/location pairs, equal to the configured batch size, so two cycles correctly repeated the same full set. The test fixture now uses 4 queries × 4 locations (16 pairs) to model the default setup and verify two disjoint 8-pair cycles. Fix commit: `fb9945d0ef30b85907945912bfaa9432729bf3ce`.
- Do not deploy until the latest CI run for this fix completes successfully.



## 43. Research learnings, current deployed state, and goals — 2026-10-09

### What the research is useful for

The shared research about JobBeeper's apparent architecture is useful as a source-strategy hypothesis, not as verified knowledge of its private backend. The public JobBeeper website describes monitoring LinkedIn, Naukri, Workday, Greenhouse, Lever, Ashby, SmartRecruiters, Darwinbox, Instahyre, Hirist, Cutshort and company career pages. It does not publicly establish that its internal implementation specifically uses thousands of residential/mobile proxies, a headless-browser cluster, or the exact aggregated-polling/CDC design described in the research.

References:
- Public JobBeeper product/source description: https://jobbeeper.com/
- OpenWeb Ninja Job Scraper API: https://www.openwebninja.com/api/job-scraper
- Apify scraper example: https://apify.com/silentflow/linkedin-jobs-scraper
- Greenhouse public Job Board API: https://docs.greenhouse.io/job-board.html
- Lever Postings API: https://github.com/lever/postings-api
- Ashby public Job Posting API: https://developers.ashbyhq.com/docs/public-job-posting-api

### Adopted architectural principles

1. **Separate acquisition from matching.** Collect broad-enough source results, normalize them, persist them, then apply the user's private filters locally. Query consolidation is worth testing where role variants overlap, but only if relevant-job coverage remains acceptable.
2. **Prefer multiple independent source adapters over more pressure on one source.** Build structured ATS collectors first (Greenhouse, Lever, Ashby), then consider SmartRecruiters, Workday or individual company career pages. Avoid a single generic scraper as the main architecture.
3. **Keep one ingestion and alerting path.** Every new source must pass through stable source IDs, timestamp/precision handling, canonical opportunity linking, deduplication, deterministic matching, alertability checks, notification ledger and Telegram delivery.
4. **Use change detection rather than repeated full reprocessing when the source supports stable IDs/updated-at fields.** Do not infer exact posting times from date-only fields. Preserve source-posted time, discovery time, precision and valid discovery latency separately.
5. **Use aggregators only after a controlled POC.** Google-for-Jobs/aggregator APIs are third-party providers rather than a guarantee of a universal, unlimited official Google Jobs feed. Test OpenWeb Ninja or a small Apify trial against the same saved sample/criteria; record relevant new jobs, duplicate rate, description completeness, update lag, HTTP failures, free-tier allowance and projected cost. Pricing, quotas and terms can change; verify them on the provider site before committing.
6. **Do not recreate claims we cannot validate.** Treat JobBeeper's multi-tenant polling, proxy rotation, headless clusters and CDC details as hypotheses unless supported by direct public evidence. Do not use proxy rotation, CAPTCHA workarounds, or simulated human activity to evade LinkedIn controls. The safer high-value move is independent sources + bounded, observable polling.

### Latest CI and deployment checkpoint

- Commit deployed on `v2-live-radar`: `3e5b51bce9e471dc839daa3842e4a5e8e1cc1e35` — “Fix LinkedIn staggered polling test for four-cycle rotation”.
- CI: [run #281 / 37921218421](https://github.com/AvinashBhalla/job-beeper/actions/runs/37921218421) completed successfully; `py_compile` passed and the full suite reported `Ran 53 tests`, `OK`.
- VM: `git log -1` matched `3e5b51b`; Docker Compose showed the V2 radar container up; `/health` returned `status=ok`.
- Post-deploy scan sample: one deep scan reported `requests=8 deep=True unique_jobs=59 failed_requests=0 elapsed=4.3s`; the following eight fast scans shown reported `requests=4 deep=False`, `failed_requests=0`, and roughly 1.9–2.6 seconds each. This is encouraging evidence from one 30-minute sample, not a guarantee against future 429s.
- Latest source-status sample: LinkedIn was enabled, `last_success=2026-10-09T11:14:10Z`, `jobs_seen=25`, `new_jobs=0`, `error=null`; Naukri was enabled, `last_success=2026-10-09T11:12:06Z`, `jobs_seen=347`, `new_jobs=10`, `error=null`. The LinkedIn response happened to report `running=true`, which can be transient if a scan is in progress.
- The shared 24-hour latency API output showed LinkedIn p50=900 seconds, p90=7200 seconds and max=21600 seconds; Naukri p50=115407 seconds, p90=288207 seconds and max=305275 seconds. These aggregates include historical samples and are not a post-deploy SLA. Because Naukri's relay often supplies date-only timestamps, the collector now sets discovery latency to null for those records; existing historical values are not retroactively corrected.
- Do not rebuild or tune solely because scans report `new=0`; that means that run inserted no new job rows, not that the source is offline.

### Current goals, in priority order

**Goal 1 — Complete short-window observation of the conservative LinkedIn release**
- Check at least one more 10-minute window of scan logs and source status.
- Track `requests`, `failed_requests`, any HTTP 429, `elapsed`, `unique_jobs`, and `new`.
- Do not widen concurrency or target batch size unless the evidence shows a need and an explicit safe test supports it.
- Use `/api/latency-summary?hours=1` only after enough fresh, valid-precision samples exist; do not use the historical 24-hour summary as the release baseline.

**Goal 2 — Verify freshness and end-to-end delivery**
- Compare a newly posted source listing's available posted time, first-seen time, job row, match/alertability decision and notification-ledger state.
- Check whether eligible new jobs reach Telegram promptly and only once per canonical opportunity.
- Validate that a date-only Naukri record has `posted_precision=date` and `discovery_latency_seconds=null`.
- Keep the explicit-experience alert safeguard until source acquisition reliably captures real required experience; parser-only improvements cannot recover missing source text.

**Goal 3 — Add structured ATS sources one at a time**
- Start with public Greenhouse, Lever and Ashby job-board endpoints, each behind an independent collector and feature/source flag.
- Prefer configured employer board IDs/domains and explicit coverage over broad scraping.
- Test fixtures, timestamp precision, dedupe, last-good-data preservation and source-specific freshness before enabling alerts.
- Expand later to SmartRecruiters, Workday and company career pages after the first adapters are stable.

**Goal 4 — Benchmark one aggregator as an optional source**
- Evaluate OpenWeb Ninja's Job Scraper API or a tightly capped Apify run with a fixed set of roles/locations and saved comparison window.
- Compare source coverage versus existing LinkedIn/Naukri/ATS records, relevant-new-job yield, posting-date precision, description completeness, duplicate rate, latency, 429/5xx behavior, request quota and actual cost.
- Do not add it as a required dependency until its incremental value is measured. Free-tier allowances are limited and subject to provider changes.

**Goal 5 — Preserve the current operational boundaries**
- Main application repo remains private; the isolated Naukri relay repo may publish only its intentionally public feed/workflow/documentation.
- No secrets, `/data/config.json`, config tokens, SQLite DB, or application source should be copied into the public relay.
- Oracle V2 remains browser-free in its production collector path.
- Keep CI green and verify the deployed VM commit/container after each production change.

### Definition of progress

A goal is complete only when there is a reproducible code change or an observed operational result, regression tests pass, the deployment is confirmed when relevant, and the evidence is recorded here. Architecture ideas from external product descriptions are not treated as facts until independently verified.

## 44. Public Naukri relay cutover completed; cache-busting fix verified — 2026-10-09

### Change and validation
- Added `params={"t": int(time.time())}` to the public relay request in `v2/radar.py`. The timestamp query parameter reduces the chance of GitHub's raw-content CDN returning an older feed after the relay branch advances.
- Updated `test_naukri_relay_reads_public_feed_without_a_token` in `v2/test_radar.py` to assert that the cache-busting `t` parameter is present and retain the no-Authorization-header assertion.
- Merged as commit `f91f047ca6e71c69492a03f0bafaf7b18362f613`. [PR #5](https://github.com/AvinashBhalla/job-beeper/pull/5), [pre-merge CI #283](https://github.com/AvinashBhalla/job-beeper/actions/runs/37925152682), and [post-merge CI #284](https://github.com/AvinashBhalla/job-beeper/actions/runs/37925221172) all passed.
- Oracle VM fast-forwarded `v2-live-radar` from `3e5b51b` to `f91f047` and rebuilt the `radar` Docker service. An initial health curl immediately after the restart received a connection reset as the container was starting; after reconnecting and rechecking, the container was running normally and `/health` returned `status=ok`.

### Observed end state
- Public relay repository: `AvinashBhalla/job-beeper-naukri-relay`; its scheduled workflow runs every five minutes independently of the private app repository.
- [Public relay workflow run #16](https://github.com/AvinashBhalla/job-beeper-naukri-relay/actions/runs/37924632737) completed successfully and published `updated_at=2026-10-09T11:37:11.483292+00:00`, `count=359`, with 359 records in `jobs`.
- The rebuilt Oracle radar consumed the refreshed feed. Naukri status reported `jobs_seen=359`, `new_jobs=0`, `error=null`; the `0` means no new database rows were inserted by that poll, not that collection failed.
- At the same health check, LinkedIn also reported a successful recent scan with `new_jobs=1` and no error.
- Removed the Ubuntu user's old `*/5 * * * * /home/ubuntu/job-beeper/scripts/trigger-naukri-relay.sh` crontab entry to stop dispatching the private repository's relay workflow. The previous crontab was saved as `/home/ubuntu/crontab.backup.20261009-113638`.
- Preserved the old local operational files outside the Git working tree at `/home/ubuntu/job-beeper-local-backup-20261009/` (`logs/` and `scripts/`) instead of deleting them. No local backups or operational files were committed.
- The old `job-radar-naukri-relay.service` is a static oneshot service and was inactive/dead at inspection time; no matching system timer was found. The removed user cron entry was the active five-minute trigger found during inspection.

### Supersession note
This section and the current-state reconciliation above supersede earlier historical checklist statements that the isolated public relay had not yet been deployed, that the old private-repository trigger still needed removal, or that the consumer lacked cache busting. Those earlier notes are retained as historical context, not current instructions.

### Next priorities
1. Continue observing consecutive public relay refreshes and Oracle consumption without reintroducing a private-repo polling trigger.
2. Track source freshness honestly, including LinkedIn 429/failure rates and date-only Naukri timestamp precision.
3. Keep the application repository private and keep the public relay repository limited to its workflow/setup documentation and intentionally public generated job feed.
4. Proceed next with an independent structured ATS adapter (Greenhouse, Lever, or Ashby) once normal relay stability is confirmed.

## 45. Greenhouse public ATS source implemented, opt-in, pending Oracle deployment — 2026-10-09

### Implementation and validation
- Merged [PR #6](https://github.com/AvinashBhalla/job-beeper/pull/6) as code commit `1cfd55b28b4409d71aee3ca3fe1db314d9aa766f`. V2 CI [run #286](https://github.com/AvinashBhalla/job-beeper/actions/runs/37927758499) passed: Python compilation and the full unit-test suite completed successfully.
- Added `greenhouse_collect(config)` to the V2 collector registry. It fetches each configured public board through `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`; the official [Greenhouse Job Board API documentation](https://developers.greenhouse.io/job-board.html) says public GET data does not require authentication and `content=true` includes the full description, department, and office.
- Five starting board tokens are configured in `v2/config.json`: `coinbase`, `clarifai`, `gravitonresearchcapital`, `as` (Veradigm Asia), and `zocdoc`. These are seed candidates based on publicly indexed Greenhouse job-board pages, not a guarantee that each endpoint is currently reachable; validate the live API on activation. The board registry is capped at 50 entries and tokens are validated before being interpolated into the fixed Greenhouse API host URL.
- Each job uses a board-scoped stable ID (`gh-{token}-{id}`), retains the published application URL and location, converts HTML description into text, and appends public department metadata. Source IDs avoid collisions when different companies reuse the same numeric job ID.
- Posting freshness is deliberately conservative: Greenhouse's documented `updated_at` field may be a modification timestamp, not the original posting time. The adapter leaves `source_posted_at=null`, `posted_precision=unknown`, and discovery latency null unless a true posting timestamp is available. Discovery time remains recorded normally by the common normalizer.
- Board failures are isolated. A failed board logs a warning while successful boards continue to contribute jobs. If every configured board fails (or none is configured while the source is enabled), the collector raises an error so source health shows the failure; the common ingestion path does not insert an empty feed to replace saved jobs.
- Added `greenhouse` to the configured source flags, source polling settings (900-second target), source-health API, latency-summary/dedupe source filters, dashboard settings checkbox, source filter, and source-health label. Disabled sources now show a DISABLED badge rather than looking ACTIVE.
- Added regression tests for normalization and HTML parsing, no invented posting time, per-board failure isolation, empty-board configuration, unsafe token rejection, and V6-to-V7 opt-in migration.

### Activation and deployment boundary
- Source is **disabled by default** in repository defaults. Config schema version 7 explicitly forces `source_enabled.greenhouse=false` while migrating older runtime config; user must turn it on explicitly after deployment.
- The source implementation has not been deployed to Oracle yet. The VM remains at the last confirmed healthy commit `f91f047`; no Greenhouse requests or Greenhouse Telegram alerts should be expected before the code is deployed and the feature is enabled.
- After deployment, first verify health and the `greenhouse` row in `/api/source-status`. Enable Greenhouse through the V2 preferences UI only when ready, then inspect `greenhouse: boards=...` and any per-board warnings in Docker logs. If all boards fail, leave it disabled until the registry is corrected. Do not infer success solely from a successful CI run; live endpoint availability still needs runtime proof.
- Keep the current LinkedIn and Naukri sources untouched while validating this independent source. Compare the resulting relevant-new-job yield, description completeness, deduplication, and age precision before treating the adapter as a valuable ongoing source.



## 46. Greenhouse live endpoint validation and seed registry cleanup — 2026-10-09

### Oracle VM result
- The deployed V2 app is healthy at commit `39847b8`; `/health` returned HTTP 200 and the runtime configuration reports schema version 7, Greenhouse disabled, and a 900-second poll target.
- The user tested all five seed URLs from the VM using the exact public Job Board API collector endpoint:
  - `coinbase`: HTTP 200, 220 jobs returned.
  - `gravitonresearchcapital`: HTTP 200, 21 jobs returned; sample included an Application Reliability Engineer in Gurugram.
  - `zocdoc`: HTTP 200, 57 jobs returned; sample included an Analyst, Quality Assurance in Pune.
  - `clarifai`: HTTP 404. Indexed legacy job pages exist, but the tested public jobs endpoint is not currently usable; do not treat this as a validated board token.
  - `as` (Veradigm Asia): HTTP 404. Veradigm's current official careers page now sends job seekers to its Workday job site, so remove it from the Greenhouse registry rather than assuming the old Greenhouse board is active.
- The failed board URLs do not affect LinkedIn/Naukri. The collector's per-board isolation is intended to preserve jobs from successful boards even when a configured board fails, but failed tokens should not remain in the starter registry.

### Follow-up and activation boundary
- Repository defaults are being narrowed to the three VM-validated boards: `coinbase`, `gravitonresearchcapital`, and `zocdoc`.
- Runtime config is persisted separately at `/data/config.json` in the Docker named volume. Updating `v2/config.json` alone does not replace the persisted board list on an existing VM; update the runtime config via the protected API or preferences UI as a separate step.
- Greenhouse remains disabled until the runtime registry is cleaned and the operator explicitly enables it. After activation, inspect source status and logs for one full 15-minute poll cycle and confirm jobs are inserted and evaluated. Do not assume freshness latency for these jobs: the adapter intentionally leaves posting time unknown.
- Clarifai may be re-added only after its current public listing endpoint and board token are verified from the VM. Do not replace it with guessed API URLs. Consider a separate Workday adapter for Veradigm later; do not mix Workday URLs into the Greenhouse collector.


## 47. Greenhouse dry run exposed and fixed remote-country matching — 2026-10-09

### Live preview result
- On the Oracle VM, the actual Greenhouse collector fetched 298 jobs from the three validated boards (Coinbase 220, Graviton Research Capital 21, Zocdoc 57), with no failed boards.
- The current matcher returned five profile matches. Four were Coinbase jobs labelled `Remote - USA` and passed the alert policy; one Graviton Research Capital role was in Gurugram and not alertable under the explicit-experience safeguard.
- The saved location config is Bengaluru, Gurugram, Delhi, and `Remote, India`. These US-remote results exposed a location-filter bug: the matcher split `Remote, India` at the comma and treated `remote` as a global wildcard. The dry-run script itself performed no database writes or Telegram sends; Greenhouse stayed disabled.

### Corrective change
- Implemented and merged as [PR #8](https://github.com/AvinashBhalla/job-beeper/pull/8), commit `2074bdab`. The matcher now requires the configured country qualifier for `Remote, India`, while deliberately plain `Remote` remains global.
- Tests cover India remote acceptance, US/Cyprus remote rejection, and unqualified global remote behavior. CI passed and the fix is deployed to the Oracle VM.
- The subsequent live preview rejected 190 remote postings outside configured location targets. Greenhouse remains disabled pending the separate ingestion/dashboard freshness safety gate.

## 48. Greenhouse first-published timestamp support — 2026-10-09

### Evidence from Oracle VM
- The corrected location dry run fetched 298 jobs from the three validated Greenhouse boards with no board failures. The location fix rejected 190 remote postings outside the configured India targets; one job matched the profile and zero passed the current explicit-experience alert policy.
- Read-only checks of the public list responses found `first_published` on Coinbase 220/220, Graviton Research Capital 20/21, and Zocdoc 57/57. The separate `updated_at` field existed on all 298 listings.
- Official Greenhouse Job Board API documentation shows `first_published` as a job post's first publication timestamp in the retrieve-job response; `updated_at` is a separate value. The live list response exposes `first_published`, so the adapter can use it without extra per-job requests.

### Implementation
- Collector parses `first_published` when present and stores it as `source_posted_at`; timestamps with hour/minute use `posted_precision=minute`, while date-only values use `date`. Missing or invalid values remain `unknown`.
- Never fall back to `updated_at`: later edits must not make an old posting look newly posted.
- Regression tests cover valid first-publication timestamps and a fallback guard (missing `first_published` plus present `updated_at` remains unknown).
- PR #9 is merged and the first-published timestamp implementation is deployed to the Oracle VM; post-merge CI passed. The latest dry run reported 298 jobs, 297 with minute-precision timestamps and 1 unknown; 10 were posted within 72 hours, 287 were older, and none had future timestamps. The only profile match was the September 1 Gurugram graduate role, which is stale and not alertable. Greenhouse remains disabled pending the ingestion/dashboard freshness fix; keep the explicit-experience policy unchanged.


## 49. Current employee knowledge transfer — 2026-10-09

The maintained, current operating summary is [`docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`](JOB_RADAR_KNOWLEDGE_TRANSFER.md). It records deployment evidence, source status, architecture, merged PRs, repository/branch purposes, cleanup notes, blockers, next tasks and the release checklist.

Important current-state corrections to older historical sections above:
- Active release branch is `v2-live-radar`; latest code merge at this snapshot is `c2f2ce65`. Post-merge CI passed, and the VM health/dry-run output reflects the updated timestamp parser.
- Remote-country matching and Greenhouse first-published timestamp parsing are implemented, merged and deployed.
- Greenhouse remains disabled. The current blocker is ingestion/dashboard freshness semantics: the collector returns all public listings while the dashboard's existing "today" lifecycle is discovery-based, so old board listings may look newly discovered. Resolve this before activation.
- `main` is still the GitHub default but is 59 commits behind the active V2 branch. Keep it until there is an explicit promotion/default-branch decision.
- Five topic branches for merged PRs #5–#9 are stale and safe to prune. The private repo's `naukri-relay` branch is a legacy one-file snapshot still referenced by the older `main` code and its manual `naukri-relay.yml` workflow. Keep it until that legacy path is retired or redirected; the active V2 relay remains the separate `AvinashBhalla/job-beeper-naukri-relay` repository.

Use the knowledge-transfer document for the next work session; this file remains the detailed chronological record.


## 50. Remote topic branch cleanup verified — 2026-10-09

- The user fast-forwarded the VM working tree from `c2f2ce6` to `0327c74` (`Keep legacy Naukri snapshot until main is retired`). The commit contained documentation changes, so the running container did not need a rebuild for that documentation-only sync.
- The user then successfully deleted seven remote branches: the five merged topic branches for PRs #5–#9 plus `docs/current-job-radar-knowledge-transfer` and `docs/keep-legacy-relay-branch-safe`.
- After `git fetch --prune`, the confirmed remote refs were `origin/HEAD -> origin/main`, `origin/main`, `origin/naukri-relay`, and `origin/v2-live-radar`.
- `main` and `naukri-relay` were intentionally retained. The old `main` collector reads the private orphan feed branch, and its manual workflow can republish it; removing it before a planned migration would break the legacy path.
- Current release branch HEAD is `0327c746`; latest application-code merge is `c2f2ce65`. The VM's latest supplied health response was HTTP 200, LinkedIn and Naukri scans succeeded, and Greenhouse remains disabled.
- Next release work is not branch cleanup: fix the dashboard/ingestion semantics for old Greenhouse board imports before enabling the source.
