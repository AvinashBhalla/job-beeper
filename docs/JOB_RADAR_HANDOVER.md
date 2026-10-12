# Job Radar V2 — Agent Handover & Product Source of Truth

> **Purpose:** This document is the durable handover for Job Radar V2.
> A future agent should read this file before making architectural or product changes.
> Do not depend on chat history being available.

**Last updated: 2026-10-12 (Gemini shadow extraction implemented on dev branch; VM verification pending)**
**Active branch:** `v2-live-radar`  
**Repository:** `AvinashBhalla/job-beeper`

> ## Mandatory agent handover rule — every prompt
> **Every user prompt must end with an update to this handover and the linked `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, before the agent considers the turn/session complete.** This applies even when a prompt only changes the plan or adds an observation; record “no code change” explicitly when applicable. After any code/config change, update both documents in the same PR where practical, or immediately afterward if runtime evidence arrives later.
>
> Each update must connect the work to the overarching goal (reliable, fresh, multi-source job discovery → normalization/deduplication → one consistent preference/match decision → explainable dashboard and Telegram delivery), and record: evidence received; diagnosis and confidence; code/config/docs paths; PR/commit and CI results; whether deployed (with actual runtime proof, not assumption); what changed and deliberately did not change; remaining risks; the exact next action; copyable commands/output expected from the user; and a continuation prompt for the next chat. Cross-link the detailed chronological handover, the compact knowledge transfer, and `docs/JOBBEEPER_REFERENCE.md` where relevant. **The latest dated handoff supersedes older instructions/checklists**; label superseded entries historical rather than leaving conflicting “next task” instructions active. Never expose secrets. One issue at a time, evidence first, verify after deploy.
>
> ## Current handoff — 2026-10-12 (authoritative; supersedes historical next-task lists)
> - **Goal:** dependable fresh multi-source discovery → truthful timestamps/stable IDs → canonical dedupe → deterministic matching → one persisted notification decision → consistent dashboard and Telegram delivery. Grow useful coverage without sacrificing accuracy or rate-limit safety. Architecture reference: `docs/JOBBEEPER_REFERENCE.md`.
> - **GitHub release:** PR #30 promoted V2 to main; main CI passed. Production VM has not been switched yet. User wants main for production and v2-live-radar for development. Update docs directly on v2-live-radar; do not create docs-only branches/PRs.
> - **VM model:** production /home/ubuntu/job-beeper -> main, port 8000, existing volume and .env; development /home/ubuntu/job-beeper-dev -> v2-live-radar, isolated Compose project/database/token, loopback-only port 8001, Telegram disabled. Dev clone/container has not yet been verified after the current patch.
> - **Development safety files:** v2/docker-compose.dev.yml commit da81d4bf..., v2/config.dev.json commit d14fb3ec..., root README commit 50293998.... Dev config enables Naukri relay only; notifications off; LinkedIn, Instahyre and Greenhouse disabled.
> - **Prior runtime evidence:** config v10 had threshold 55, LinkedIn poll 180s, Naukri 300s. A 27-minute LinkedIn sample showed 22 requests without visible 429/failures, limited evidence only. Three recent matches (two LinkedIn, one Naukri) were sent without errors in 17-35 seconds. Preserve historical v9 migration suppressions.
> - **Workflow and Naukri:** main retains `.github/workflows/v2-ci.yml` and no longer contains Pages, job-watch, check-sources or private Naukri workflow. Both app branches consume the separate public `AvinashBhalla/job-beeper-naukri-relay` feed. Never delete or alter the public relay branch as part of private repo cleanup.
> - **Current branch inventory:** only main and v2-live-radar remain in the private repo at last audit. Preserve both. Do not create new branches solely for documentation.
> - **Exact next sequence:** (1) remove the temporary docs branch; (2) create `/home/ubuntu/job-beeper-dev` from `v2-live-radar` and start isolated dev Compose; verify health, source toggles, port, and data volume; (3) back up production DB/config and inspect the actual Compose project/volume and clean git status; (4) switch the existing production checkout to `main` and rebuild using the same Compose project/volume; smoke-test health/config/dashboard/source status/Naukri/Telegram; (5) observe LinkedIn request/yield for 24–72 hours; (6) run a guarded Greenhouse single-board canary; then add structured ATS sources one at a time.
> - **Next exact user action:** run the command in the latest chronological handoff below. It leaves the current production container on port 8000 untouched while starting dev on loopback port 8001. Return its health/config/source/resource output. Do not cut production over until dev is healthy and backup/volume identity are verified.
> - **Mandatory handover rule:** update both `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` after every prompt, including evidence-only turns. Record goal, evidence, paths, commits/CI, actual deployment state, risks, exact next action and continuation prompt. Treat this top block as authoritative; later dated items are history. Never expose secrets; one issue at a time; verify after deployment.
> **Historical baseline (2026-10-09; superseded by latest handoff above):** The latest confirmed Oracle deployment is still commit `f91f047ca6e71c69492a03f0bafaf7b18362f613` (`Bust cache when polling public Naukri relay`). The cache-busting change was reviewed in [PR #5](https://github.com/AvinashBhalla/job-beeper/pull/5); PR CI [run #283](https://github.com/AvinashBhalla/job-beeper/actions/runs/37925152682) and post-merge CI [run #284](https://github.com/AvinashBhalla/job-beeper/actions/runs/37925221172) passed. The Oracle container was rebuilt and `/health` returned `status=ok`, version `2.0.0`. The public relay [run #16](https://github.com/AvinashBhalla/job-beeper-naukri-relay/actions/runs/37924632737) published a valid feed with 359 jobs; the next radar scan reported `jobs_seen=359`, `new_jobs=0`, and `error=null`. The cache-busting change reconciled the prior 345-versus-359 mismatch; stale caching was the plausible cause, not proven in isolation. The old VM user-crontab entry that dispatched the private repository relay every five minutes was removed after backing up the crontab. Its untracked `logs/` and `scripts/` were moved to `/home/ubuntu/job-beeper-local-backup-20261009`. The public relay continues on its own five-minute GitHub Actions schedule. PR #6 added the Greenhouse collector and dashboard integration in repository commit `1cfd55b28b4409d71aee3ca3fe1db314d9aa766f`, with pre-merge CI [run #286](https://github.com/AvinashBhalla/job-beeper/actions/runs/37927758499) passing. **That Greenhouse change is not yet deployed on Oracle and remains disabled by default.** Telegram delivery is active; Agent-Reach remains parked and is not a production dependency.

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


## 51. Current operational handoff — 2026-10-11

**Read first:** the newer operational summary is in [`docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`](JOB_RADAR_KNOWLEDGE_TRANSFER.md), under **“Latest operating update — 2026-10-11”**. It includes the full next-agent instructions and a copyable prompt. This section records the detailed chronological evidence and prevents the older Greenhouse/branch-cleanup notes from being mistaken for today's active task.

### Product/workflow goal right now

Restore dependable job discovery without creating noisy or false alerts. Work on one failure at a time, inspect real evidence, make one small change, verify the result, and only then proceed. The immediate blocker is **Naukri relay freshness**. LinkedIn coverage/rate limits are the following separate task. Do not work on Greenhouse in this session and keep it disabled.

### Telegram issue is resolved and verified

- The Oracle VM is `job-radar`; repository path is `~/job-beeper`; the V2 Compose file is `v2/docker-compose.yml`; service/container is `radar` / `v2-radar-1`.
- The repo-root `.env` contains both Telegram environment variables, but Compose resolved them as missing when invoked without explicitly naming the env file. Use the following pattern for Compose commands on this VM:
  `sudo docker compose --env-file .env -f v2/docker-compose.yml ...`
- The user recreated the service container with `--env-file .env`. The two variables were confirmed **SET** in the running container; `/health` returned `status=ok`, `version=2.0.0`.
- The three intentionally retained recent LinkedIn notifications were verified in the ledger as `sent`, `last_error=None`: HealthEdge — Software Development Engineer in Test; Scoutit — Frontend Developer; GeeksGod — Python Developer Job Openings by Gramener | Jobs 2025.
- At the later ledger check: `pending=26`, `sent=78`, `suppressed=3514`. The approved backlog action suppressed 37 older queued ledger entries and preserved the three recent ones; no job records were deleted. An additional older Scoutit ledger entry was already suppressed.
- Do not repeat the backlog cleanup, weaken explicit-experience notification requirements, or print any token/chat ID.

### Evidence: Naukri database is aligned with a stale upstream feed

From the user's read-only checks around 2026-10-11 18:45–18:47 IST:
- `/api/source-status` showed LinkedIn enabled and Naukri enabled, with recent scan runs completing without runtime errors. One latest sample: LinkedIn `jobs_seen=20, new_jobs=0`; Naukri `jobs_seen=328, new_jobs=0`.
- The jobs table contained 2,668 LinkedIn records and 1,227 Naukri rows. In the past 24 hours, 372 LinkedIn records and 83 Naukri records had new `discovered_at` timestamps. In the past hour, LinkedIn had 25 and Naukri had 0. Latest LinkedIn discovery was `2026-10-11T13:11:56.042328Z`; latest Naukri discovery was `2026-10-11T07:05:55.267174Z`.
- The direct request to the public Naukri relay JSON returned `updated_at=2026-10-11T07:05:55.267174Z`, declared count 328, actual entries 328, and 328 unique IDs/URLs. Every feed ID was already in the radar database; 0 IDs were missing. No Naukri rows had a `discovered_at` within six hours of that check. This indicates the private V2 ingestion can match the current feed; the immediately evidenced problem is that the public feed is old.
- The feed's first sample jobs included Epam Systems listings, including some repeated titles with distinct source entries. Do not dedupe only on company/title without first confirming stable IDs and URLs.

### User-supplied GitHub Actions run history to continue from

The user ran a relay workflow listing and a last-12-runs JSON command in repository `AvinashBhalla/job-beeper-naukri-relay`. The user will send this same output to the next agent in the new session. Use it as input and do not ask them to rerun it by default.

- Workflow list: `public-naukri-relay  active  379327541`.
- All 12 returned history entries had `name=public-naukri-relay`, `conclusion=success`, `status=completed`, `event=schedule`, `headBranch=main`, and the same head SHA `9d564e016da2ec50c70ee8bde9f2726539167460`.
- Latest shown run: ID `38120124080`; created `2026-10-11T07:04:06Z`, updated `2026-10-11T07:06:01Z`.
- Earlier shown starts were `2026-10-11T01:01:47Z`, then `2026-10-10T22:13:33Z`, `18:54:55Z`, `14:44:49Z`, `08:39:36Z`, `02:17:55Z`, and earlier timestamps. Observed gaps span roughly 2h48 to 6h21—not a five-minute cadence.
- Latest public JSON `updated_at` equaled the latest workflow's output time (`07:05:55Z)); by 18:47 IST it was more than six hours old. A successful workflow conclusion alone does not prove it fetched fresh jobs or published a new payload.
- The run-history command initially failed only because the requested `gh run list --json` field `workflowName` is not supported by that installed `gh` version. The retry used supported fields such as `name`, `conclusion`, `createdAt`, `databaseId`, `event`, `headBranch`, `headSha`, `status`, `updatedAt`, and `url`. Avoid `workflowName` in future `gh run list --json` queries.

### Archived next steps for the previous Naukri-relay incident (superseded by the latest handoff at the end of this document)

1. Read the top of `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and this section. Consume the workflow-history JSON that the user pastes; continue from that evidence.
2. Inspect the **separate public relay repository** `AvinashBhalla/job-beeper-naukri-relay` on `main`. Read its active workflow YAML (find the actual file rather than guessing its path), exact `schedule.cron`, any job/step `if` conditions, `concurrency`, triggers, collector code, and artifact/commit/publish code. Compare configured cadence with the timestamps above.
3. Inspect all recent workflow runs—not only successful scheduled runs. Check the available CLI's supported `--json` fields first if needed. Examine the latest run logs to answer: did the source collector actually execute, did it fetch current results, did it write the output JSON, did the commit/publish step run, and did `updated_at` advance? Confirm whether other runs are hidden by query filters and whether the cron itself is actually five minutes.
4. Do not assume the schedule is wrong until the YAML is checked. Identify whether this is a low-frequency cron, missing/delayed scheduled events, early job exits, source-side staleness, or a publish/write problem.
5. Only after proving the cause, implement **one small relay-side fix**, ideally on a topic branch/PR with tests. Preserve the JSON contract, stable job IDs and timestamps. Do not patch the private app's ingestion code while all 328 feed IDs already match the database; do not broaden the feed by simply lowering identity thresholds.
6. Validate a single manual dispatch if the workflow supports it and it is safe: wait for the run to finish, review its logs and conclusion, fetch the public JSON again, and verify that `updated_at` advanced and the job set is plausible. Then wait for/trigger the normal radar scan and verify the deployed app consumes the new relay timestamp with no inappropriate Telegram backlog.
7. Only after Naukri freshness is verified, address LinkedIn coverage. Its guest endpoint is repeatedly returning HTTP 429. Current V2 code is conservative: `LINKEDIN_SEARCH_WORKERS=1`, four fast query/location targets per scan, deep scan every ~900 seconds, one deep page batch, no same-scan retry on 429, and deep pagination is skipped when the fast lane receives a 429. Measure 429 rate and useful new jobs before changing schedules or query coverage; increasing concurrency first is not recommended.
8. Do not add/enable sources or redesign the architecture in the same patch. Keep Greenhouse disabled. Do not claim a deployment until the merge/rebuild/health/source-status evidence is actually provided. Avoid printing any secrets.

### Archived continuation prompt for the previous Naukri-relay incident (do not use; superseded by the latest handoff at the end)

> You are taking over Job Radar V2. Read `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and this handover first. Continue from the latest 2026-10-11 update, not from the older Greenhouse or branch-cleanup tasks. I will send you the output showing the active `public-naukri-relay` workflow and its last 12 runs. Use that output, inspect the actual workflow YAML and latest run logs in `AvinashBhalla/job-beeper-naukri-relay`, and establish why the public relay JSON remains at `updated_at=2026-10-11T07:05:55Z` despite successful scheduled runs. All 328 feed IDs already exist in the radar DB, so do not change private ingestion yet. Prove whether the cause is the cron, missing scheduled runs, the collector, or the publish step; then make one minimal relay-side fix and validate the JSON timestamp/count before moving to LinkedIn HTTP 429 coverage. One change at a time, verify before proceeding, keep Greenhouse disabled, and never print secrets.


---

## Latest chronological handoff — 2026-10-11: PR #17 deployed; alert consistency queued

### User instruction: handover is mandatory after every prompt
The user explicitly directed that after every modification—and after every prompt so a context switch never loses the thread—the handover must be updated for the next model. This instruction is itself a repository rule now: update this file and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` every turn; write an explicit no-code-change note when appropriate. The latest handoff entry is authoritative over older sections.

### LinkedIn fix and actual production evidence
- [PR #17](https://github.com/AvinashBhalla/job-beeper/pull/17) merged successfully. Merge SHA: `097131797ddfbdec40c8d9911c6d5bc5b7b8a3bb`.
- CI run [#38156008065](https://github.com/AvinashBhalla/job-beeper/actions/runs/38156008065) passed: compile/syntax check plus 71 unit tests.
- Code change: `v2/radar.py` now paces all LinkedIn HTTP calls at 3s minimum; scheduler applies a minimum 120s LinkedIn poll interval. `v2/config.json` moved to schema/config version 8 and poll target 120s. `_merge_config()` migrates persisted version-7 runtime configs to at least 120s for LinkedIn. Rate-limit streaks persist across otherwise-successful scans and reset only after at least an hour without another 429; cooldown escalates 5→10→20→30 minutes (or longer if Retry-After says so). Logs count attempted search targets rather than the originally planned batch count. New regressions cover persistent escalation, reset after a clean hour, and runtime config migration.
- The user ran `git pull` and Docker rebuild with `--env-file .env`. Supplied output:
  - `/health`: status ok, version 2.0.0, uptime 53 seconds, LinkedIn runtime `running=true`.
  - `/api/config`: config_version 8; poll_seconds LinkedIn=120, Naukri=300, Instahyre=600, Greenhouse=900.
  - `/api/source-status` at the prior check showed Naukri `last_success=2026-10-11T16:39:02.300960+00:00`, 312 jobs seen, 0 new, error null.
- Do not claim sustained LinkedIn behavior is already proven. The supplied event trace predates deployment and showed 429 at `16:20:50.693Z`, a 300s cooldown through `16:25:50.693Z`, and scans resuming only after cooldown. This confirmed the old cooldown was respected but repeated rate limits remained possible after resumption.
- **Next action:** wait ~12 minutes after deployment, then run:
  ```bash
  echo "=== LINKEDIN EVENTS ==="
  sudo docker logs --timestamps --since 15m v2-radar-1 2>&1 \
    | grep -Ei 'linkedin: HTTP 429|cooldown|discovery scan|batch stopped' \
    | tail -n 100
  echo
  echo "=== LINKEDIN STATUS ==="
  curl --max-time 15 -fsS http://127.0.0.1:8000/api/source-status \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps(next(s for s in d["sources"] if s["source"]=="linkedin"),indent=2))'
  ```
  Inspect request cadence, real attempted requests, 429 recurrence, escalation, and whether cooldown prevents further outbound requests. Send those exact outputs back. Do not add concurrency, rotate identities/proxies, or try to evade LinkedIn limits.

### Next bug: dashboard and Telegram must share the same eligibility decisions
- User supplied screenshots showing dashboard Jobs Feed cards and a Telegram alert, and reports the two surfaces are showing different jobs. This is now the next task **after** LinkedIn production verification.
- User’s stated product expectation: with threshold set to 55%, every *fresh, new, profile-matched* opportunity with score ≥ the threshold should be eligible for Telegram; the dashboard should transparently show why an apparently qualifying item was not sent. Preserve canonical deduplication (one notification per opportunity), valid source/experience incompatibility checks, max-age policy, notification setting, and delivery-failure handling. Do not send a flood of historical jobs while correcting the rule.
- Current code/config findings already confirmed:
  - `v2/config.json`: `match_threshold=55`, `require_explicit_experience_for_alerts=true`, `notifications_enabled=true`.
  - `match_details()` marks a match when score meets the threshold **and** a configured role hit exists.
  - `alertability_details()` adds an extra gate: unknown experience can make a matching job non-alertable.
  - `refresh_notification_decisions()` picks eligible observations under age/alertability rules and persists one status per canonical opportunity.
  - Telegram `_claim_one()` requires `job_evaluations.match=1` AND `alertable=1`, plus ledger state queued/eligible retry; dedupe/history/freshness also affect whether an alert sends.
  - Dashboard `/api/jobs` independently calculates `match_details` and `alertability_details`; frontend applies time/score/source/alertable-only filters. Need compare the returned `alertable` status, match reason, ledger status/decision reason, and sent state per canonical opportunity rather than assuming every difference is a bug.
- Proposed investigation/fix order after LinkedIn: inspect `GET /api/jobs?today_only=true&limit=500`, `/api/notification-queue`, `/api/daily-summary`, relevant schema and `notification_ledger`; add deterministic unit tests for threshold boundary, unknown experience, fresh match queueing, stale suppression, canonical duplicate suppression, and dashboard/Telegram consistency. Change the shared decision path so UI and Telegram consume the same persisted evaluation/decision wherever possible. Recompute pending decisions safely on deploy/config update; never automatically replay the historical suppressed backlog. Then deploy and verify with rows/ledger evidence and one genuinely new fresh job.

### Overarching architecture goal and related docs
Target pipeline documented in `docs/JOBBEEPER_REFERENCE.md`: source registry/source-specific collection → normalize and preserve source timestamps/stable IDs → canonical identity and cross-source dedupe → new/changed detection → deterministic preference match with reasons → freshness/alert policy → dashboard + Telegram. Collection should be independent of each individual user's preferences where the source offers broad collection; LinkedIn remains a rate-limited, query-catalog adapter, not a reason to evade access controls. Expand ATS adapters only after ingestion and alert consistency are measured and safe. Keep Greenhouse disabled until its older-board freshness risk has been resolved and explicitly trialed.


---

## Latest chronological handoff — 2026-10-11: PR #19 merged; production deployment pending

### LinkedIn verification result (evidence from the user)
The timestamped post-deployment sequence shows 120-second scan scheduling with a five-minute 429 cooldown that blocks scans:
- `16:39:22.293Z`: deep scan, 8 attempted search targets, 39 unique jobs, 0 failed requests, 21.3 seconds.
- `16:41:10.867Z`: fast scan, 4 attempts, 20 jobs, 0 failed requests.
- `16:43:10.873Z`: fast scan, 4 attempts, 20 jobs, 0 failed requests.
- `16:45:04.912Z`: HTTP 429; only 2 search targets attempted; first 300s cooldown since this deployment.
- `16:50:15.296Z` and `16:52:15.513Z`: scans resumed after cooldown at the new 120s cadence.
- Source status at `16:52:30.482Z`: 22 jobs seen, 1 new, `error=null`.
Conclusion: request pace and cooldown gate work; LinkedIn still rate-limits us. The log does not yet prove 10/20/30-minute escalation because only one post-restart 429 occurred. Never bypass source limits.

### Alert-policy diagnosis and intended behavior
User's screenshot showed a 94% BlackLine opportunity and a 79% Five9 opportunity in the dashboard; the BlackLine alert was present in Telegram while the second high-scoring job was not. Source code showed:
- `v2/config.json`: `match_threshold=55`, `require_explicit_experience_for_alerts=true`, notifications enabled.
- Matcher can classify unknown experience neutrally and return a match score ≥55; then `alertability_details()` separately blocked the alert if explicit experience was not captured.
- Telegram reads persisted `job_evaluations.match/alertable` and `notification_ledger`, but the dashboard's `/api/jobs` endpoint recomputed matching/alertability per request and did not expose the canonical ledger status/reason. That made the dashboard score/badge hard to reconcile with actual Telegram delivery.
- User requirement: true profile matches at/above the configured threshold are alert-eligible even with unknown experience; explicit incompatible experience, excluded role/title, invalid location, disabled notifications, freshness, canonical dedupe and failed delivery remain legitimate explanations. A dashboard time filter (e.g. “Last hour”) is a separate view filter, so a 72-hour-eligible Telegram alert may be older than that dashboard slice; show transparent notification status/reasons instead of implying those filters are identical.

### PR #19 implementation status
[PR #19](https://github.com/AvinashBhalla/job-beeper/pull/19) merged as `05e1a19374b7cca830cb0cd442743b5f3d0468be`; latest-head CI [#38159529440](https://github.com/AvinashBhalla/job-beeper/actions/runs/38159529440) passed all 74 tests. The initial CI run identified two old assertions dependent on the retired gate; those were updated to test threshold-only eligibility and the real notifications-disabled policy. The merged code includes:
- `v2/radar.py`: v9 config migration; remove unknown-experience-only alert gate; at upgrade suppress only pending, never-attempted entries older than 10 minutes whose prior stored alertability reason explicitly names the retired gate; make `/api/jobs` return persisted evaluation and canonical-ledger data.
- `v2/config.json`: config schema 9 and `require_explicit_experience_for_alerts=false` as the documented deprecated setting.
- `dashboard/app.js`: true profile-match filter for 55%+ selection; add per-canonical `TELEGRAM SENT / QUEUED / PENDING / FAILED / NOT ALERTED` status labels with reason tooltips. Data is bound to the persisted API decision.
- `v2/test_radar.py`: regression tests for unknown-experience eligibility, config v9 migration, safe suppression of old pending backlog while preserving recent pending, and dashboard API consistency with the ledger.
- No production deployment of PR #19 confirmed yet. The next action is user `git pull`/Docker rebuild and the health/config/qualifying-jobs diagnostic listed in the current handoff. Confirm schema 9, score threshold, API ledger status and a new qualifying match's Telegram delivery; keep Greenhouse disabled and do not replay the old suppressed queue.

### Copyable continuation prompt
“You are continuing Job Radar V2. Read both handover documents and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handovers after every user prompt. PR #19 merged as `05e1a19374b7cca830cb0cd442743b5f3d0468be`; latest CI [#38159529440](https://github.com/AvinashBhalla/job-beeper/actions/runs/38159529440) passed 74 tests, but production deployment is not yet confirmed. Ask the user to pull `v2-live-radar`, rebuild using `--env-file .env`, and send the health, schema-9 config, and qualifying jobs/ledger diagnostic in the current handoff. Verify a current qualifying match is queued/sent and that the dashboard badge agrees with the Telegram ledger. No historical alert burst; keep incompatible-experience rejection, freshness, canonical dedupe, notifications-enabled policy and Greenhouse disabled.”


---

## Latest chronological handoff — 2026-10-11: v9 deployed, free-first LinkedIn request budget proposed, main/workflow inventory

### Latest deployment evidence
User provided `/health` status ok, version 2.0.0, uptime 32 seconds, LinkedIn running; runtime config version 9; match threshold 55; explicit-experience alert gate false; LinkedIn/Naukri poll targets 120s/300s. Today feed API returned 454 job rows, 26 true profile matches scoring >=55. It showed intentional migration suppressions on older pending entries previously blocked by explicit experience; do not manually queue all of these. Examples of already-sent opportunities were also present. This demonstrates the v9 dashboard response returns the notification ledger status and reasons as intended, but does not yet prove fresh alert end-to-end under v9.

### Free-first rate-limit strategy
The user explicitly prefers free and self-built measures before paid products. Public LinkedIn terms prohibit scraping tools and bypassing usage limits; proxy/IP rotation or CAPTCHA bypass would be evasion, not a durable fix. Current policy is to keep any direct LinkedIn access limited and back off; expand collection from permitted employer ATS/career sources as a separate coverage strategy.
- PR #21 code/test commit `644180cba5a8ccfc17399d7bc0070d319e7c41bf` passed [CI run #38161564620](https://github.com/AvinashBhalla/job-beeper/actions/runs/38161564620), compile plus 76 tests. The first CI run found an old assertion that expected the entire target list after four scans; it was corrected to cover the full list after eight scans with two targets per cycle. This doc edit moves the topic head, so re-check latest CI before merge. It changes spacing to 4s; one JD-enrichment worker; two first-page targets per scan; deep pagination every 30m; and schema v10 migration from 120s to 180s. The 429 cooldown/Retry-After remains. Query/location revisit takes longer; measure useful new jobs over 20–30 minutes.
- Free coverage diversification to prioritize after this trial: one public/authorized ATS/company-careers connector at a time with stable source IDs, exact posted timestamps, health/backoff, dedupe and notification tests. Greenhouse still stays disabled pending its stale-publication freshness guard.
- Paid scraping APIs (Apify etc.) are deferred, not adopted as a way to bypass LinkedIn blocks. If revisited later, review provider/data-source terms and budget; no assertion of identical data quality or legal permission.

### Workflow/branch inventory and main promotion
Inspected YAML from `main` and `v2-live-radar`:
- Keep `.github/workflows/v2-ci.yml`.
- `.github/workflows/pages.yml` deploys static dashboard files from `main` on dashboard changes; V2 API base is relative `/api`, so GitHub Pages would not reach the Oracle service by default. Remove/disable for V2 unless a proper API origin architecture is intentionally designed.
- `.github/workflows/job-watch.yml` is manual-only legacy V1; writes legacy JSON/job state to `main`.
- `.github/workflows/naukri-relay.yml` is manual-only legacy Naukri using root `config.json`; live Naukri relay is the separate `job-beeper-naukri-relay` repo controlled by Oracle systemd timer.
- `.github/workflows/check-sources.yml` is manual-only V1 config pruning of root `config.json`; it does not manage V2 config.
These are candidates for a focused cleanup PR; check any remaining recovery need and ensure they are not the active deployment/scheduler before removal.
- Branch inventory includes active release `v2-live-radar`, default `main`, legacy `naukri-relay`, and six old topic/docs branches. Merged PR branches #15–#20 are cleanup candidates after verifying exact head/base/merge metadata. Keep default/main, active branch and legacy relay until the release promotion has completed. Direct branch deletion is not available through the connected GitHub tool, so use GitHub's merged-PR delete button or verified `gh` commands once safe.
- Do not push everything to `main` immediately. First merge/deploy PR #21 and validate the current threshold→dashboard→ledger→Telegram behavior with at least one fresh qualifying job. Then clean workflow automation on `v2-live-radar`, create a dedicated `v2-live-radar`→`main` promotion PR that deletes obsolete V1 jobs/workflows and updates docs, and validate V2 CI on `main`. Disable/retire GitHub Pages static publishing before this merge because it would publish a dashboard whose relative `/api` points at the GitHub Pages host. Keep Oracle deployment source on `v2-live-radar` until a deliberate cutover is verified.

### Copyable continuation prompt
“You are continuing Job Radar V2. Read `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, the latest section of this detailed handover, and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handover docs after every user prompt. Production v9 was confirmed healthy with threshold 55 and explicit-experience gate false; 26 matches were shown, with some old pending matches intentionally suppressed to avoid a notification flood. PR #21 is the free-first LinkedIn load-reduction work: 4s spacing, one detail worker, 2 target searches per scan, 30-minute deep scan interval, runtime migration to poll 180s, with 429 escalating cooldown retained. Check CI before merge/deploy. LinkedIn terms prohibit scraping and access-limit evasion; avoid IP/proxy/CAPTCHA bypass. Workflow inventory: keep V2 CI; Pages static workflow, manual V1 job-watch, manual legacy private Naukri workflow, and root-config check-sources are obsolete candidates to remove in a separate PR after checking recovery needs. Clean topic refs only after verified merges. Promote to main only after deployed alert path passes and legacy workflows are retired; write a dedicated promotion PR and do not alter Oracle deploy source until validated.”


---

## Historical release note — 2026-10-11: PR #21 merged; PR #22 cleanup complete (current state is in the handoff at the top)

### PR #21 merge and CI
- Merged [PR #21](https://github.com/AvinashBhalla/job-beeper/pull/21) as `6c93473844cd469493a0c61acf1477ba20252d69`.
- Latest-head CI [#38161863816](https://github.com/AvinashBhalla/job-beeper/actions/runs/38161863816) passed compile and **76 tests**. The initial run had one expected stale test assertion about seeing 16 targets after four cycles; the test was corrected to verify full 16-target rotation over eight two-target cycles, then latest CI passed.
- Free-first modifications: 4s global spacing, one-at-a-time detail enrichment, 2 search targets per scan, deep scan every 30m, config version 10 and migration from LinkedIn polling 120s→180s, while retaining the global 429 stop and escalating cooldown (5/10/20/30m / Retry-After). This reduces average query volume at the cost of slower target rotation. It is not yet deployed as of this handover.
- User must run deployment command below, then verify config schema 10 and LinkedIn 180s. Log request attempts, 429, cooldown and useful `new_jobs` over 20–30m; compare the yield, not just success/error counts. If volume/freshness becomes unacceptable or 429 persists, next free-first lever is approved public ATS/career coverage, not proxy evasion.

### Workflow cleanup merged
The audit inspected actual workflow YAML from `main` and `v2-live-radar`. [PR #22](https://github.com/AvinashBhalla/job-beeper/pull/22) merged as `8eae61f2605c14903bccbc25c1a95d438e3a9f79`; CI [#38162375556](https://github.com/AvinashBhalla/job-beeper/actions/runs/38162375556) passed all 76 tests. Only `.github/workflows/v2-ci.yml` remains on `v2-live-radar`; the four workflows below were removed from V2, but remain on `main` until the later promotion:
- `.github/workflows/pages.yml`: static GitHub Pages deployment of `dashboard/`. Current V2 JS API base is relative `/api`, so this static page would query the Pages host, not the Oracle service. Remove to prevent broken static publish on V2 promotion.
- `.github/workflows/job-watch.yml`: manual-only V1 recovery; root `job_watch.py`, uses old secrets, writes legacy root JSON state and the static dashboard feed to `main`.
- `.github/workflows/naukri-relay.yml`: manual-only legacy relay in private repo; active relay is in separate `job-beeper-naukri-relay` repo, driven by Oracle systemd timer.
- `.github/workflows/check-sources.yml`: manual-only V1 tool that edits root `config.json`, unrelated to V2's `v2/config.json` and protected runtime config.
`main` was intentionally not changed by PR #22. It still contains the four legacy workflows, which should disappear when a deliberate V2 promotion PR is reviewed and merged.

### Branch cleanup and main release
Verified merged PR metadata:
- #15 → `fix/prevent-posted-after-discovered`, merge `b3b59b6682c320b869980f75dc7508fa9bdc6e84`
- #16 → `fix/linkedin-rate-limit-backoff`, merge `d59f0372de68c2b0d3c5a912b752463846f288e3`
- #17 → `fix/linkedin-lower-pressure-cooldown`, merge `097131797ddfbdec40c8d9911c6d5bc5b7b8a3bb`
- #18 → `docs/current-handover-rule-20261011`, merge `e895c9363d208dfd35157405bc53ea20c144ded3`
- #19 → `fix/dashboard-telegram-alert-consistency`, merge `05e1a19374b7cca830cb0cd442743b5f3d0468be`
- #20 → `docs/record-alert-consistency-merge-20261011`, merge `4654a01a38dc3384a3a730e13dcd88647ef39000`
- #21 → `fix/linkedin-free-first-request-budget`, merge `6c93473844cd469493a0c61acf1477ba20252d69`
These topic refs are merged and are deletion candidates after checking `git ls-remote --heads origin` and confirming no extra work was pushed. The connected GitHub tool cannot delete refs; use the merged PR's Delete branch button or an authenticated `git push origin --delete <topic-branch>`. Keep `main`, `v2-live-radar`, and legacy `naukri-relay` until main promotion is complete. The PR #22 head branch and current docs-only branch become candidates only after their respective PRs merge.
- **Main promotion timing:** not immediately. Finish deployment/observability for PR #21 and prove fresh alert end-to-end on the v9→v10 alert-consistency release; merge the workflow cleanup PR; then create a separate reviewed `v2-live-radar`→`main` PR, ensure deletions/README/docs are included, verify CI on main, retire static Pages before merge, and keep Oracle deploy source explicitly on `v2-live-radar` until a documented cutover. This avoids an unreviewed all-at-once change to the default branch.

### Copyable deployment command and expected next output
```bash
cd /home/ubuntu/job-beeper
git pull --ff-only origin v2-live-radar
git log -1 --oneline
sudo docker compose --env-file .env -f v2/docker-compose.yml up -d --build radar
sleep 10
echo "=== HEALTH ==="
curl --max-time 15 -fsS http://127.0.0.1:8000/health
echo
echo "=== CONFIG ==="
curl --max-time 15 -fsS http://127.0.0.1:8000/api/config | python3 -c 'import json,sys; d=json.load(sys.stdin); c=d.get("config",d); print(json.dumps({k:c.get(k) for k in ("config_version","match_threshold","require_explicit_experience_for_alerts","poll_seconds")},indent=2))'
```
Expected: `config_version=10`, threshold 55, explicit-experience setting false, LinkedIn 180s, Naukri 300s. Then run after 20–30 minutes:
```bash
echo "=== LINKEDIN RATE / YIELD ==="
sudo docker logs --timestamps --since 30m v2-radar-1 2>&1 | grep -Ei 'linkedin: HTTP 429|cooldown|discovery scan|batch stopped|JD enrichment' | tail -n 120
echo
echo "=== LINKEDIN STATUS ==="
curl --max-time 15 -fsS http://127.0.0.1:8000/api/source-status | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps(next(s for s in d["sources"] if s["source"]=="linkedin"),indent=2))'
```
Do not print secrets. Separately verify one *new, fresh* match in `/api/jobs` with `notification_status`, ledger decision reasons, and sent status before declaring dashboard/Telegram consistency proven.

### Next-session prompt
“You are continuing Job Radar V2. Read the knowledge-transfer doc, this latest handover and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handovers after every user prompt. PR #21 merged as `6c93473844cd469493a0c61acf1477ba20252d69`; CI #38161863816 passed 76 tests; production v9 is healthy but PR #21’s config v10/LinkedIn 180s pacing is not yet deployed. Ask the user to pull/rebuild using the commands above and send health/config. Then observe 20–30m of timestamped request/429/cooldown/new-job yield. A separate branch `chore/remove-legacy-v1-workflows` removes four obsolete V1 workflows from v2-live-radar while retaining V2 CI; check its PR/CI and merge once green. Audit only verified merged topic branches for deletion; no delete-branch tool is available, so use the GitHub PR UI or safe authenticated git command. Promote V2 to main only after alert path is verified and cleanup merges; use a dedicated PR and keep Oracle deploy ref unchanged until cutover. Never use proxy/CAPTCHA evasion; expand free authorized ATS/company feeds first.”


## Latest chronological handoff — 2026-10-12: config v10 live; 20–30 minute observation pending

### Evidence received
- `/health`: `status=ok`, app `2.0.0`, uptime 26s after restart; LinkedIn `running=true`. Naukri last success `2026-10-12T03:45:00.791518+00:00`, 296 jobs seen, 0 new, no error.
- `/api/config`: version 10, threshold 55, old explicit-experience alert setting false, LinkedIn poll 180s, Naukri 300s, Instahyre 600s, Greenhouse 900s.
- Remote stale-branch comparison returned `23 0`: 23 behind and zero commits ahead. Re-run refs/open-PR checks immediately before deletion.
- No application code changed this turn. PR #25 updates the handover docs and must merge before deleting its own topic ref.

### Next 20–30 minute observation
```bash
echo "=== LINKEDIN RATE / YIELD (last 30 minutes) ==="
sudo docker logs --timestamps --since 30m v2-radar-1 2>&1 \
  | grep -Ei 'linkedin: HTTP 429|cooldown|discovery scan|batch stopped|JD enrichment' \
  | tail -n 120
echo
echo "=== LINKEDIN STATUS ==="
curl --max-time 15 -fsS http://127.0.0.1:8000/api/source-status \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps(next(s for s in d["sources"] if s["source"]=="linkedin"),indent=2))'
```
Evaluate attempted request count, cooldown enforcement/escalation, successful scans, and useful `new_jobs`. Do not use proxy/IP rotation, fake accounts or CAPTCHA bypass.

### Promotion / continuation gate
1. Validate one new true match scoring at least 55% across dashboard, persisted notification ledger, and actual Telegram send. Do not requeue entries deliberately suppressed during the v9 migration.
2. After PR #25 merges, re-run `git ls-remote --heads origin`, verify no open PRs and confirm the stale branch remains zero commits ahead.
3. Delete only verified merged topic refs using the command below; preserve `main`, `v2-live-radar`, and `naukri-relay`.
4. Promote to `main` only after v10 observation and fresh-alert validation, with a reviewed PR and CI.

### Continuation prompt for the next chat
“Read both handover documents and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both docs after every user prompt. Oracle config v10 is deployed: health OK, threshold 55, explicit-experience gate false, LinkedIn poll 180s / Naukri 300s. Wait for 20–30 minutes of timestamped LinkedIn request/429/cooldown/new-job logs and source status, then verify one fresh ≥55% match dashboard → persisted ledger → Telegram. Latest stale-branch compare is `23 0`; recheck refs/open PRs before deleting merged topics, preserve main/v2-live-radar/naukri-relay. Promote V2 to main only after runtime and alert validation. Prefer authorized free ATS/company-career sources; no LinkedIn limit evasion.”

## Latest chronological handoff — 2026-10-12: v10 low-pressure observation and topic cleanup complete

### Evidence supplied by the user
- The remote branch deletion command succeeded. Final `git branch -r` showed only `origin/HEAD -> origin/main`, `origin/main`, `origin/naukri-relay`, and `origin/v2-live-radar`. The stale optimization compare before deletion was `26 0` (26 behind, zero ahead). Topic cleanup is complete.
- LinkedIn logs between `2026-10-12T04:15:05Z` and `04:42:05Z` showed ten scan summaries: nine fast scans at two attempted requests each and one deep scan at four attempts, totaling 22 requests. Every shown scan reported `failed_requests=0`; no 429/cooldown warning appeared in the provided filtered output. Latest source status at `04:42:05Z`: `jobs_seen=2`, `new_jobs=0`, `error=null`.
- Interpretation: the v10 lower-pressure setup had a clean approximately 27-minute sample, with no visible 429. This is not a long-term guarantee. Aggregate new-job count over the whole window is not available from these specific logs, and the latest scan added zero jobs. Continue tracking useful yield/freshness.
- No application code or runtime config changed during this prompt. Both handover files are updated. PR #28 carries this documentation update; delete its temporary branch after merge.

### What remains
1. Fetch the API records for jobs discovered in the last 30 minutes and list true matches scoring at least 55 with alertability and notification status:

```bash
echo "=== QUALIFYING JOBS DISCOVERED IN LAST 30 MINUTES ==="
curl --max-time 20 -fsS 'http://127.0.0.1:8000/api/jobs?minutes=30&limit=500' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); js=[j for j in d.get("jobs",[]) if j.get("likely_match") and int(j.get("match_score",0))>=55 and j.get("alertable")]; print(json.dumps({"qualifying_count":len(js),"jobs":[{k:j.get(k) for k in ("id","source","title","company","discovered_at","source_posted_at","match_score","alertable","notification_status","notification_decision_reasons","notification_sent_at","notification_last_error","canonical_opportunity_id")} for j in js[:15]]},indent=2))'
```

Send the output so one fresh job can be traced through dashboard → persisted notification ledger → actual Telegram send. If none were discovered, use a 180-minute window and distinguish low source yield from an alert-routing issue. Do not requeue old entries suppressed during the v9 migration.
2. Only after a fresh qualifying alert is verified, open the reviewed `v2-live-radar`→`main` promotion PR. Keep V2 CI; retire Pages/job-watch/check-sources as part of that promotion; only remove the private Naukri workflow/branch after replacing main's old URL with the current separate public relay URL.

### Continuation prompt
“Continue Job Radar V2. Read both handovers and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handover documents after every user prompt. Config v10 is live (threshold 55, LinkedIn 180s/Naukri 300s). User provided ~27 minutes of LinkedIn scan logs (04:15–04:42 UTC): ten scans, 22 attempted requests, no displayed 429/cooldown warnings, zero failed requests per scan; latest source status had `new_jobs=0`. Treat as positive limited evidence, not a permanent guarantee. All merged topic branches were deleted; final remote refs are only main, naukri-relay and v2-live-radar. Next retrieve jobs discovered in the last 30 minutes, inspect ≥55% true matches and validate a fresh notification through dashboard → persisted ledger → Telegram. Do not requeue old v9 migration suppressions. Promote to main only after fresh-alert proof, with a reviewed PR; keep V2 CI, retire obsolete V1 workflows, and replace main's old private Naukri relay URL before removing its workflow/branch. No LinkedIn limit evasion; prefer permitted free ATS/career sources.”

## Temporary documentation branch cleanup

After PR #28 merges, delete only the temporary docs branch (production/topic cleanup is complete):

```bash
git push origin --delete docs/record-linkedin-v10-observation-20261012
git fetch --prune origin
git branch -r
```

Expected branches: `origin/main`, `origin/naukri-relay`, `origin/v2-live-radar` (and `origin/HEAD`).
---

## Latest handoff — 2026-10-12: fresh alert consistency proven; prepare main promotion

### Fresh alert evidence received
The user ran `GET /api/jobs?minutes=30&limit=500` and got three qualifying new jobs. Each was a true profile match scoring ≥55, `alertable=true`, and `notification_status=sent`, with no `notification_last_error`:

| Source | Opportunity | Score | Discovered (UTC) | Telegram sent (UTC) | Delay |
|---|---|---:|---|---|---:|
| LinkedIn | Back End Developer – Next JS, Talentgigs | 85% | 04:45:02.394 | 04:45:31.156 | 28.8 s |
| LinkedIn | Full Stack Developer, D Square Consulting Services Pvt Ltd | 94% | 04:33:02.005 | 04:33:18.640 | 16.6 s |
| Naukri | Software Engineer, Creative Hands HR | 76% | 04:34:48.604 | 04:35:23.247 | 34.6 s |

All three records have canonical opportunity IDs and distinct ledger entries; this is strong evidence that recent dashboard/API decisions and Telegram delivery agree for both active sources. It does not guarantee every older suppressed record should alert. Preserve the v9 migration suppression and prevent a historical burst.

### Release decision
- The v10 rate-limit observation and fresh alert gate are satisfied at the intended initial level: approximately 27 minutes/22 requests with no displayed 429 or failed request, followed by three fresh ≥55% matches sent in 17–35 seconds. Continue monitoring; one window does not prove zero future 429s.
- Last repository compare showed `v2-live-radar` 93 commits ahead of `main`, 0 behind, with 21 changed files. The observed diff removes `check-sources.yml`, `job-watch.yml`, `naukri-relay.yml`, and `pages.yml`; retains `.github/workflows/v2-ci.yml`; brings the V2 app/matching/tests/docs forward; and replaces the old main private Naukri feed reference with the separate public relay path. Inspect this diff thoroughly before merging.
- Create a dedicated reviewed PR from `v2-live-radar` to `main`. CI on the promotion head must pass. Do not directly push/force-push main. Do not change the Oracle deploy branch until a deliberate cutover plan has passed post-merge smoke tests.
- Main workflows retired by this promotion: static Pages/deploy-dashboard, V1 job-watch, root-config check-sources, and the legacy private Naukri relay workflow. Keep the private data branch `naukri-relay` until the promotion is merged and the old code reference is confirmed gone; the current public relay repo and VM timer are the active path.
- Branch cleanup of merged topics was completed, leaving `main`, `naukri-relay`, `v2-live-radar`. Temporary docs branches should be deleted after their respective docs PRs merge.

### Next action
1. Review [the promotion compare](https://github.com/AvinashBhalla/job-beeper/compare/main...v2-live-radar) (93 commits ahead / 0 behind at the last check) and open a PR from `v2-live-radar` to `main`.
2. Wait for CI, inspect any failures and ensure workflow removal and relay URL replacement are in the same reviewed PR.
3. After merge, verify main CI and smoke tests. Keep production on `v2-live-radar` until separately verified.
4. Clean up temporary docs branch refs after merges, preserving `main`, `naukri-relay`, `v2-live-radar`.

### Continuation prompt
“Continue Job Radar V2. Read both handovers and `docs/JOBBEEPER_REFERENCE.md`; update both after every user prompt. Config v10 is live. User supplied three fresh ≥55% matches from the last 30 minutes: LinkedIn Talentgigs (85%, sent 29s after discovery), LinkedIn D Square Consulting (94%, sent 17s after discovery), and Naukri Creative Hands HR (76%, sent 35s after discovery), all `alertable=true`, `notification_status=sent`, no errors. Together with the prior 27-minute/22-request window with no visible 429/failures, this passes the initial rate-limit and fresh-alert gates. Prepare a reviewed PR from `v2-live-radar` to `main` (93 commits ahead, 0 behind, 21 changed files at last comparison). Inspect the diff: remove Pages/job-watch/check-sources/private legacy Naukri workflow, retain V2 CI, replace main's old private Naukri URL with active separate public relay path. Require CI and post-merge smoke tests; do not direct-push or switch Oracle branch until verified. Keep private Naukri data branch until main's old URL is removed. Free compliant ATS sources before paid tools.”


## Latest handoff — 2026-10-12: fresh alerts verified; main promotion PR #30 open

- User supplied three recent qualifying matches from `/api/jobs?minutes=30&limit=500`. All score ≥55%, `alertable=true`, `notification_status=sent`, and `notification_last_error=null`:
  - LinkedIn Talentgigs, Back End Developer - Next JS: 85%, discovered 04:45:02.394Z, sent 04:45:31.156Z (~28.8s).
  - LinkedIn D Square Consulting Services Pvt Ltd, Full Stack Developer: 94%, discovered 04:33:02.005Z, sent 04:33:18.640Z (~16.6s).
  - Naukri Creative Hands HR, Software Engineer: 76%, discovered 04:34:48.604Z, sent 04:35:23.247Z (~34.6s).
- This confirms fresh dashboard/API-to-notification-ledger-to-Telegram consistency across both active sources for these examples. Do not replay the old v9 migration suppressions.
- PR #30 is open: https://github.com/AvinashBhalla/job-beeper/pull/30. It promotes `v2-live-radar` to `main`; the compare at creation was 94 commits ahead / 0 behind, 21 files. It removes Pages, job-watch, check-sources, and the old private Naukri workflow; preserves V2 CI; and changes the Naukri source URL to the separate public relay. CI #38205996937 passed before this handover advance; recheck CI on the latest branch head.
- Review carefully. No direct push/force push to main and no Oracle deploy-ref change as part of merging. After main merge, verify main CI and runtime smoke tests, then separately plan cutover.
- Temporary topic docs refs `docs/record-linkedin-v10-observation-20261012` and `docs/record-fresh-alerts-main-promotion-20261012` should be removed after this documentation state is stable. Preserve main/naukri-relay/v2-live-radar.


## Latest chronological handoff — 2026-10-12: post-promotion roadmap

### Current facts
- PR #30 merged V2 to `main` (`b384b8d6ae00c48c7765ebf11af407981de3cd35`). Post-merge CI #38206525826 passed. PR #31 merged handover sync (`76d253a4475223df517a3757795e20f15c1b9524`), CI #38207296933 passed. Oracle still deploys `v2-live-radar`; no production cutover was performed.
- Runtime v10: threshold 55, LinkedIn 180s / Naukri 300s, explicit-experience gate false. The sample LinkedIn window was 22 requests over about 27 minutes with no visible 429/failures. Three fresh qualifying matches across LinkedIn/Naukri were alertable and sent with no errors, in about 17–35 seconds. Do not claim zero future 429 risk; continue low-pressure monitoring.
- Workflow cleanup in main is complete; public Naukri relay repo is the live data endpoint. Private `job-beeper/naukri-relay` is now unused and is a branch-cleanup candidate.

### Roadmap, ordered by dependency and risk
1. **Housekeeping now:** remove private `naukri-relay` and temporary branch `docs/record-fresh-alerts-main-promotion-20261012` after checking refs/open PRs; preserve main and v2. Then compare `main` vs `v2-live-radar` app/config/deployment files to confirm only docs/history differ.
2. **Controlled Oracle cutover:** after read-only comparison, move Oracle checkout to `main` only with an explicit snapshot/backup and controlled container rebuild. Validate `/health`, `/api/config` (version 10, threshold 55), `/api/source-status`, `/api/latency-summary`, dashboard feed, public Naukri relay timestamp/job count, and a fresh qualifying notification. Keep rollback command/path to the known `v2-live-radar` commit. Don't conflate GitHub merge with production deployment.
3. **LinkedIn 429 + useful yield observability (24–72h):** keep current conservative settings. Track request attempts, 429s/cooldown time, jobs scanned, unique normalized jobs, truly new jobs, relevant matches, and discovery lag. Tune only from collected yield; do not rotate proxies, evade controls, or increase volume just because a scan returns few jobs.
4. **Greenhouse canary:** source is disabled in config and had an earlier dry-run of about 298 jobs across three boards without DB writes or Telegram. Start with one board, add a repeatable dry-run summary, validate stable IDs, real posted timestamps, dedupe, and source-health/backoff, and prevent historical backfill alert bursts. Enable only after these checks; then expand selected boards.
5. **Structured ATS coverage:** add one connector at a time in this order unless evidence changes it: Lever, Ashby, SmartRecruiters; later evaluate Workday/company career pages; revisit Instahyre only after its current public/structured interface and freshness semantics are verified. Each needs fixtures/tests, pagination/incremental-fetch strategy, truthful timestamps, normalization/dedupe, failure isolation, and alert consistency.
6. **Observability and UX:** expose per-source last success/error/429 cooldown, requests/run, total fetched, new jobs, match counts and discovery lag; show why a qualifying job is sent/suppressed in the same terms across dashboard and Telegram. Extend regression tests for duplicates, retry/idempotency and timestamp ordering.
7. **Multi-user product scope (later):** current project is a personal watcher with a global config. If multiple users are intended, first migrate to per-user preference profiles and an idempotent `(user_id, canonical_opportunity_id)` notification ledger; do this before account/auth rollout. Don't prematurely add distributed infrastructure.

### Exact command for the immediate housekeeping task
```bash
cd /home/ubuntu/job-beeper
git fetch --prune origin
echo "=== PRIVATE REPO BRANCHES ==="
git ls-remote --heads origin
echo "=== OPEN PRS ==="
gh pr list --repo AvinashBhalla/job-beeper --state open
git push origin --delete naukri-relay docs/record-fresh-alerts-main-promotion-20261012
git fetch --prune origin
git branch -r
```
Expected private app branches: `origin/main` and `origin/v2-live-radar` (plus `origin/HEAD`). Do not delete anything in the separate public relay repo.

### Continuation prompt
“Read both handovers and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: update both handover files after every prompt. Main is promoted (`b384b8d6`) and main CI passed (#38206525826); docs sync PR #31 merged (`76d253a4`) and CI #38207296933 passed. Oracle still uses v2-live-radar. v10 has a 27-minute/22-request LinkedIn sample with no visible 429/failures (limited evidence only), and three fresh ≥55% matches from LinkedIn/Naukri were sent without errors in ~17–35 seconds. Next delete unused private repo branches `naukri-relay` and `docs/record-fresh-alerts-main-promotion-20261012` after refs/open-PR check; never touch public relay branch. Then do a read-only main vs v2 runtime-file diff and a carefully backed up Oracle cutover if it is documentation-only. After cutover keep LinkedIn low-pressure for 24–72h and measure useful yield. Next source project: Greenhouse single-board canary; then Lever/Ashby/SmartRecruiters, followed by Workday/career pages. Never increase scraping volume without metrics or evade LinkedIn limits. Don't add distributed infrastructure before justified.”


## Latest chronological handoff — 2026-10-12: branch inventory correction after roadmap PR

A fresh GitHub branch inventory after PR #33 merged returned only `main`, `v2-live-radar`, and the temporary topic branch `docs/next-phase-roadmap-20261012`. Therefore the earlier suggested private `naukri-relay` and `docs/record-fresh-alerts-main-promotion-20261012` branches had already been removed. Do not retry deleting absent refs. After confirming no open PR depends on it (currently none), delete only `docs/next-phase-roadmap-20261012`, then verify that `origin/main` and `origin/v2-live-radar` remain. The public relay repository is separate and unchanged.

### Exact branch cleanup command
```bash
git push origin --delete docs/next-phase-roadmap-20261012
git fetch --prune origin
git branch -r
```

Then do a read-only comparison of runtime paths between main and v2-live-radar before any production cutover. Current comparison has the same `v2/radar.py` blob SHA on both branches; the branches differ only by commit history/docs, but verify runtime/config/deploy files again before switching Oracle.


## Latest chronological handoff — 2026-10-12: isolated development instance plan

### Changes in this prompt
- No production runtime changes. The user requested `main` for production and `v2-live-radar` for development, both on one Oracle VM, and requested that future docs be updated directly on the existing V2 branch without docs-only branches.
- Added `v2/docker-compose.dev.yml` (`da81d4bf…`), `v2/config.dev.json` (`d14fb3ec…`), and refreshed root `README.md` (`50293998…`) on `v2-live-radar`.
- Dev service is named `job-radar-dev`, bound only to `127.0.0.1:8001`, uses a separate named volume under project `job-radar-dev`, and has no Telegram credentials. Dev config enables Naukri relay only and disables LinkedIn, Instahyre, Greenhouse, and Telegram notifications.
- Verified by GitHub blob SHAs that main and v2 have identical app/config/runtime files: `v2/radar.py`, `v2/config.json`, `v2/docker-compose.yml`, `v2/Dockerfile`, `v2/requirements.txt`, `dashboard/index.html`, and V2 CI. This supports a same-volume production branch switch later, but first verify Oracle's actual container/project/volume and back up its database/config.

### Immediate command: remove temporary docs branch and start dev only
```bash
set -e
cd /home/ubuntu/job-beeper
git fetch --prune origin
echo '=== REMOVE TEMPORARY DOCS BRANCH ==='
git push origin --delete docs/next-phase-roadmap-20261012
git fetch --prune origin
echo '=== RUNTIME FILE DIFF (should print nothing) ==='
git diff --exit-code origin/main origin/v2-live-radar -- v2/radar.py v2/config.json v2/docker-compose.yml v2/Dockerfile v2/requirements.txt dashboard/index.html .github/workflows/v2-ci.yml
echo '=== CURRENT REPO STATUS ==='
git status --short
git branch --show-current
echo '=== CURRENT CONTAINER PROJECT/VOLUME (no secrets) ==='
sudo docker inspect v2-radar-1 --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}}'
sudo docker inspect v2-radar-1 --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}'
echo '=== VM RESOURCES ==='
free -h
df -h /
sudo docker stats --no-stream
echo '=== CREATE DEV CLONE ==='
if [ ! -d /home/ubuntu/job-beeper-dev/.git ]; then
  git clone --single-branch --branch v2-live-radar "$(git remote get-url origin)" /home/ubuntu/job-beeper-dev
else
  cd /home/ubuntu/job-beeper-dev
  git fetch origin
  git switch v2-live-radar
  git pull --ff-only origin v2-live-radar
fi
echo '=== START ISOLATED DEV ==='
cd /home/ubuntu/job-beeper-dev
sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build
sleep 5
echo '=== DEV HEALTH ==='
curl --max-time 10 -fsS http://127.0.0.1:8001/health
echo
echo '=== DEV CONFIG ==='
curl --max-time 10 -fsS http://127.0.0.1:8001/api/config
echo
echo '=== DEV SOURCE STATUS ==='
curl --max-time 10 -fsS http://127.0.0.1:8001/api/source-status
echo

Expected: production container still serves port 8000; dev serves only 127.0.0.1:8001. Dev config should report Naukri enabled, LinkedIn/Instahyre/Greenhouse disabled, `notifications_enabled=false`, and config version 10. Compose volume listing must show an independent dev volume and the existing production volume unchanged. Do not output `/data/config_token`, Telegram credentials, or `.env` contents.


### Production cutover plan (do not execute as part of dev setup)
1. Back up the production `jobs.db` and runtime `config.json` from the existing container into a permission-restricted backup directory; do not print or share config tokens.
2. Confirm working tree state, runtime blob equality, and current Compose project/volume name.
3. In `/home/ubuntu/job-beeper`, switch to `main` and run the existing production Compose command using the exact same project name and volume. Do not run `docker compose down -v`, change project name, switch `.env`, or attach the dev volume.
4. Smoke-test health, config v10/threshold 55, source status, latency, dashboard, public Naukri relay, and the next fresh Telegram alert. If anything unexpected occurs, return to the known-good V2 commit and rebuild using the same production volume.
5. Keep `/home/ubuntu/job-beeper-dev` on `v2-live-radar` permanently as the development checkout.


### Continuation prompt
“Read both handovers and `docs/JOBBEEPER_REFERENCE.md`. Mandatory: after every user prompt update both docs directly on `v2-live-radar`; do not create a topic branch/PR just for docs. Target architecture: production `/home/ubuntu/job-beeper` on main/port 8000/existing DB volume; development `/home/ubuntu/job-beeper-dev` on v2-live-radar/loopback port 8001/separate database, config and token. Created `v2/docker-compose.dev.yml` and `v2/config.dev.json`; dev uses Naukri relay only, all notifications off, LinkedIn off so it does not double prod request load. Production still runs existing V2 service; no cutover yet. Next run the command in detailed handover: delete leftover docs branch, verify runtime diff/container volume/resources, clone/start dev and report health/config/source status. Only then back up production DB/config and move the existing prod checkout to main using the same Compose project/volume and run smoke tests. Never print secrets, never run down -v, don't publicly expose dev port. Then 24–72h LinkedIn measurement and Greenhouse single-board canary.”

## Branch inventory correction — 2026-10-12
Latest GitHub branch query after the dev setup and direct documentation commits returned only `main` and `v2-live-radar`; the temporary `docs/next-phase-roadmap-20261012` branch is already absent. No branch cleanup command is needed. This update was committed directly to `v2-live-radar`, not a docs branch. Latest handover CI for the previous current head succeeded at run #38209927504; the next update will require its own CI.


## Latest handoff — 2026-10-12: LinkedIn experience extraction patch on development branch

### Bug and root cause
The screenshots show Cvali's LinkedIn Cloud & AI Engineer posting with the visible metadata field Experience: 4.00-6.00 Years. The dashboard/Telegram instead displayed experience as unspecified and sent a 61% match. With candidate experience 2 years and maximum job experience 3 years, a correctly parsed 4-6 year requirement should reject the job. Root cause: linkedin_collect used generic numeric experience detection to skip JD enrichment when a search snippet contained any years phrase; additionally, _linkedin_job_description selected a description element but did not preserve LinkedIn's separate Experience metadata field when it appeared outside that element.

### Patch and verification
- v2/radar.py commit 6ac58a1d4757c3c545203b84a61f4f8058d4747b adds a strict LinkedIn labeled-experience parser, checks full-page text, preserves that metadata ahead of generic JD content, and prevents a generic snippet number alone from skipping detail enrichment.
- v2/test_radar.py commit 22496f9714a7628d4c93929005a2d10773a753cc adds two regression tests: metadata outside the description element and generic experience snippets still requiring JD enrichment.
- V2 CI run 38211941792 passed compile plus the full unit suite on head 22496f9714a7628d4c93929005a2d10773a753cc.
- Fix is on v2-live-radar only. It has not yet been rebuilt on the Oracle dev instance, merged to main or deployed to production. Do not promote until the dev test command below passes.
- Correctness can require more JD detail requests when snippets contain incidental years; the global 4-second pacing and stop-on-429 cooldown remain in place. Measure request/yield behavior after verification.

### Exact development-only command
Run this on Oracle; only the dev service on port 8001 is rebuilt, and tests use a dev-built image with a temporary DB path:
```bash
set -e
cd /home/ubuntu/job-beeper-dev
git fetch origin
git switch v2-live-radar
git pull --ff-only origin v2-live-radar

echo '=== REBUILD DEV ONLY ==='
sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar
sleep 5

echo '=== FULL UNIT SUITE FROM DEV-BUILT IMAGE ==='
DEV_IMAGE=$(sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml images -q radar | head -n1)
test -n "$DEV_IMAGE"
sudo docker run --rm -e JOB_RADAR_DB=/tmp/job-radar-tests.db "$DEV_IMAGE" python -m unittest discover -s v2 -p 'test_*.py' -v

echo '=== DEV HEALTH ==='
curl --max-time 10 -fsS http://127.0.0.1:8001/health
echo

echo '=== DEV SAFE CONFIG ==='
curl --max-time 10 -fsS http://127.0.0.1:8001/api/config | python3 -c 'import json,sys; c=json.load(sys.stdin)["config"]; print(json.dumps({"config_version":c.get("config_version"),"source_enabled":c.get("source_enabled"),"notifications_enabled":c.get("notifications_enabled")},indent=2))'

echo '=== DEV SOURCE STATUS ==='
curl --max-time 10 -fsS http://127.0.0.1:8001/api/source-status
echo

echo '=== PRODUCTION STILL HEALTHY ==='
curl --max-time 10 -fsS http://127.0.0.1:8000/health
echo
```
Expected: all tests pass; dev health is ok; dev notifications false and only Naukri enabled; port 8000 production remains healthy. Do not paste tokens, .env values or credentials. Once the user returns a green result, promote the tested patch to main via a reviewed PR/merge and confirm main CI; do not switch the Oracle production checkout during this patch promotion.

### Source expansion order
- Current active: LinkedIn low-volume guest search and Naukri public relay.
- Implemented but disabled: Greenhouse public Job Board API adapter (three configured boards; prior dry-run around 298 rows without DB writes), and Instahyre adapter (endpoint schema/freshness must be verified again).
- Next after experience patch is proven: enable Greenhouse in dev on one board only, notifications still off. Validate at least two polls, stable IDs, original posting precision, dedupe/new counts, error/backoff, and no historic alert burst. Then expand selected boards.
- Instahyre: test live response schema, stable IDs, posted timestamp, useful new-job yield and failure behavior in dev before enabling it there. Do not enable directly in production first.
- First new structured ATS adapters: Ashby, Lever, SmartRecruiters. Then assess Workable/Recruitee only after confirming usable public interfaces; their official integrations can require tenant credentials.
- Remaining requested providers requiring per-employer board/domain discovery: Avature, BambooHR, Breezy HR, Darwinbox, Eightfold AI, Freshteam, Hireology, HRsmart, iCIMS/Jibe, Jobvite, Keka, Oracle Cloud Recruiting, Paycom, PeopleStrong, Phenom People, Rippling ATS, SAP SuccessFactors, Oracle Taleo, Teamtailor, UKG Pro/UltiPro, Workday, Zoho Recruit. Separate job boards/aggregators to evaluate: Cutshort, Hirist, Wellfound and Y Combinator jobs.
- Most vendor platforms do not expose a universal global feed. For each integration we need a supported public endpoint or allowed company career page, discovered board identifiers, truthful timestamps, stable IDs, incremental pagination, failure isolation, tests and shared alert-ledger behavior. Do not mark a vendor integrated merely because an adapter shell exists.

### Continuation prompt
Continue Job Radar V2. Read both handovers and docs/JOBBEEPER_REFERENCE.md. Update both handover documents directly on v2-live-radar after every prompt; do not create docs-only branches. The LinkedIn experience parser regression fix is committed on V2 (radar 6ac58a1d; tests 22496f97); CI run 38211941792 passed. User screenshot showed Experience 4.00-6.00 Years but dashboard/Telegram sent an unknown-experience 61% match. Root cause: generic search-snippet years skipped actual JD enrichment and the parser did not preserve a separate labeled Experience field. Next run detailed handover's dev-only command: pull/rebuild job-radar-dev on port 8001, run the full test suite using dev-built image and temporary DB, verify dev safe config plus production health. Not merged to main or deployed yet. After dev passes, promote fix to main through reviewed merge and CI. Then Greenhouse single-board dev canary, then Instahyre endpoint/freshness validation, then Ashby, Lever, SmartRecruiters, and remaining employer-tenant ATS adapters. Keep dev notifications disabled; don't turn on LinkedIn in dev while production queries it. Preserve production volume and do not switch branch as part of the bugfix.

## Interruption recovery record — 2026-10-12

- Code fix is committed on development branch only: `v2/radar.py` `6ac58a1d4757c3c545203b84a61f4f8058d4747b`; tests `v2/test_radar.py` `22496f9714a7628d4c93929005a2d10773a753cc`.
- Full regression suite passed in GitHub Actions run [#38211941792](https://github.com/AvinashBhalla/job-beeper/actions/runs/38211941792). Follow-up CI checks for directly committed documentation updates also passed: [#38212605092](https://github.com/AvinashBhalla/job-beeper/actions/runs/38212605092), [#38212615004](https://github.com/AvinashBhalla/job-beeper/actions/runs/38212615004), [#38212626814](https://github.com/AvinashBhalla/job-beeper/actions/runs/38212626814).
- Current branch inventory: `main` and `v2-live-radar` only; no open PRs. No docs-only branch should be created.
- No VM rebuild/test has been confirmed from user output since the patch. No merge of this fix to main and no production deploy has happened.
- **The next step is exactly the dev-only test command immediately above this record in the handover.** Pull latest V2 in `/home/ubuntu/job-beeper-dev`, rebuild only Compose project `job-radar-dev`, run the full unittest suite in the built image with temporary DB path, check port 8001 health/safe config/source status and confirm port 8000 production remains healthy. Do not enable LinkedIn or Telegram in dev for this test and do not change production.
- After green dev evidence: review/promote the experience fix to main and confirm main CI. Next enable Greenhouse only as a one-board development canary with notifications off; validate Instahyre endpoint/schema/freshness before enabling that source. Continue the ATS rollout list in `docs/JOBBEEPER_REFERENCE.md`.
- Continuity rule reaffirmed: after every user prompt update both handovers directly on `v2-live-radar`.

## Latest handoff — 2026-10-12: dev verification passed; LLM job-description enrichment proposal

### Evidence received from Oracle VM
The user ran the dev-only rebuild/test command in `/home/ubuntu/job-beeper-dev`. Output reports **78 unit tests ran in 53.339 seconds; OK**. Development health returned `status=ok`, version `2.0.0`, database `/data/jobs.db`; Naukri's latest poll completed successfully at `2026-10-12T06:43:53.083706+00:00` with 292 jobs seen, zero new and no error. Safe dev config is version 10; LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, notifications=false. Source status agrees. Production port 8000 remains healthy and continues to report LinkedIn and Naukri status. This closes the stated development verification gate for the experience parser patch; it does not prove that the patch is on the VM's currently running dev image unless the displayed rebuild command was run against the latest branch, but the user supplied the expected full command output and no failures.

### Diagnosis / proposal: deterministic JD parsing needs a bounded LLM assist
The user proposes an LLM to extract required skills and experience from job descriptions because deterministic parsing misses varied formats. This is reasonable as an **enrichment layer**, not a replacement for source normalization, deterministic matching, eligibility rules, dedupe, notification ledger, or delivery policy. No application code changed in this turn. No API provider/model or spend ceiling has been configured; do not add a provider dependency or call any external model until key/config ownership and cost controls are decided.

Recommended implementation contract:
- Input: a bounded, sanitized plain-text job description plus title/source metadata; do not pass secrets, candidate PII, or unrelated page contents. Treat JD text as untrusted data, not model instructions.
- Output strict JSON schema: `experience_min_years`, `experience_max_years` (nullable numbers), `experience_type` (required/preferred/unspecified), `experience_evidence` (short verbatim evidence excerpt or null), `required_skills` (array of normalized skill names), `preferred_skills`, `responsibilities` (optional capped summary), `confidence` per field or an overall confidence, and schema/parser version. Explicitly distinguish total professional experience from experience with a particular tool and distinguish "preferred" from required; preserve ranges and avoid interpreting graduation year, product history, or incidental numbers as experience.
- Validate output locally and reject malformed, overlong, unsupported, contradictory or low-confidence results. Store provider/model, prompt/schema version, extraction timestamp, input content hash, latency, token usage/cost if supplied, and redacted error category; never log API keys or raw private content.
- Deterministic parsing and source-labeled metadata take precedence where confidently present. LLM can fill missing fields and add skill extraction, but must not silently overwrite explicit source metadata. Conflicts should be marked uncertain and may trigger a safe fail-closed experience gate for alerts rather than inferred eligibility.
- Job description is untrusted prompt-injection content: isolate it as data, do not provide tools, do not allow output to control config or network access, and never let it set its own eligibility/match score.
- Call the model only for records that lack essential fields or fail extraction; cache by canonical job ID + description hash + schema/prompt version; use bounded retries, request timeout, per-run budget/rate limit and provider error backoff. Continue gracefully with deterministic results when provider unavailable.
- Establish a labelled evaluation fixture set before rollout: explicit ranges ("4-6 years", "4.00-6.00 Years"), minimum-only, maximum-only, preferred-only, total-vs-skill-specific years, internships/fresher, conflicting metadata, no experience stated, and malicious JD instructions. Gate on exact experience-field accuracy and zero false-eligible alerts on known out-of-range samples, not generic model quality claims.
- Initial deployment should be disabled by default and tested in development with notifications off. Compare deterministic versus LLM extracts without changing matching/alert behavior first (shadow mode); only enable bounded enrichment after evals pass and cost/latency/yield are observed. Do not send historical suppressed notifications.

### Patch and deployment state
- Existing experience parser/test patches: `v2/radar.py` commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`; `v2/test_radar.py` commit `22496f9714a7628d4c93929005a2d10773a753cc`; GitHub CI run [#38211941792](https://github.com/AvinashBhalla/job-beeper/actions/runs/38211941792) passed.
- User's dev output confirms full suite 78 tests passing, dev safe source config and dev health are good, production remains healthy. LLM integration is not implemented. No new source commit, LLM CI run, main merge, or production deployment occurred this turn.
- Follow-up post-patch docs CI must be checked for the new documentation commit; record its result only when actually observed.

### Exact next actions
1. Promote the tested experience-parser fix through a reviewed release PR/merge to `main` and verify main CI. Do **not** switch the production VM checkout as part of this code promotion.
2. Before coding the LLM client, choose provider/API credential location and enforce a small monthly/request budget; store key only in dev/prod secret configuration, never in git/docs/chat. Prefer a provider API with constrained JSON schema output; OpenAI Structured Outputs documentation: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses . Structured schema adherence still needs local validation and application-level correctness evaluation.
3. Implement the extractor as a separate module and tests, disabled by default, then shadow-run only on missing/ambiguous descriptions in dev. No source integrations/Greenhouse canary until the one-current-issue release promotion and LLM choice are handled.
4. Collect metrics: candidate count, model calls/skips, valid/invalid outputs, per-field agreement vs deterministic/source metadata, p50/p95 latency, failure/backoff counts and estimated cost. Do not log secrets or dump full JD content.

### Continuation prompt
“Continue Job Radar V2. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Latest user VM verification: 78 tests passed in 53.339s; dev health OK on 8001, config v10 has Naukri only and notifications off; source status matches; prod 8000 healthy. The LinkedIn experience parser patch can now move through reviewed release PR/merge and main CI (do not switch production checkout during promotion). User proposes an LLM for required skills/experience because deterministic parsing misses formats. No LLM code/provider added yet. Design a separate, disabled-by-default, schema-validated enrichment module; source-labeled deterministic metadata takes precedence, conflicts remain uncertain, LLM never assigns match scores or controls eligibility by itself. Add fixtures for ranges, required/preferred, skill-specific vs total experience, absent/conflicting metadata and prompt-injection text; shadow-mode in dev, cost/latency/error metrics, timeout/backoff/cache. Choose provider and secret/budget configuration before implementation. Do not alter production or enable dev notifications/LinkedIn; then continue Greenhouse one-board canary only after the current fix is promoted.” 


## Latest handoff — 2026-10-12: dev verification passed; LLM job-description enrichment proposal

### User-provided Oracle VM verification
The user reported the full dev-only verification command completed successfully: **78 unit tests ran in 53.339s; OK**. Dev health is `status=ok`, version `2.0.0`, DB path `/data/jobs.db`; Naukri poll completed at `2026-10-12T06:43:53.083706+00:00`, 292 jobs seen, 0 new, no error. Safe dev config version 10: LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, notifications=false. Source status agrees. Production port 8000 remains healthy and reports its existing LinkedIn/Naukri status. Do not infer a production deployment: none occurred.

### User proposal and diagnosis
User wants an LLM to extract JD skills and required experience because deterministic parsing misses varied text formats. No app code changed this turn. The idea is sound as **bounded structured enrichment**, but the model must not become the eligibility/matching authority. Current LLM provider, model, secret location and spending budget are not yet selected; no external provider integration has been implemented.

### Proposed extraction contract and safety boundaries
- Input only a capped, sanitized plain-text job description and minimal source/title metadata. Treat it as untrusted data; job text may contain prompt-injection instructions. No tools or privileged actions exposed to the model.
- Strict JSON fields: `experience_min_years` / `experience_max_years` (nullable), `experience_type` (required/preferred/unspecified), `experience_evidence` (short evidence excerpt/null), normalized `required_skills`, `preferred_skills`, optional capped `responsibilities`, confidence, and schema/prompt version. Distinguish total professional experience from tool-specific years and preferred qualifications from hard requirements.
- Locally validate all output, bounds, ranges and enums. Keep explicit source-labelled metadata / deterministic high-confidence evidence authoritative. If outputs conflict or confidence is low, mark uncertainty; never use the LLM alone to make a job eligible or send an alert.
- New module, disabled by default, called only when important fields are missing/ambiguous. Cache by canonical job ID + JD content hash + extractor schema/prompt version; set strict timeout, bounded retry, cost/request/run caps, provider backoff and graceful deterministic fallback.
- Observe model/provider, schema/prompt version, hash, latency, valid/invalid rates, token/cost data where available, agreement rates and redacted failure categories. Never log API keys, `.env`, credentials or full raw JD. Keep candidate PII out of prompts.
- Build regression/eval fixtures for `4-6 years`, `4.00-6.00 Years`, minimum/maximum only, required vs preferred, total vs skill-specific experience, fresher/intern, no stated experience, conflicting metadata, and adversarial instructions embedded in JD. First run **shadow mode** in dev with notifications disabled; compare extractions without changing scores or delivery. Require high exact-field accuracy and zero known false-eligible alerts before enabling.
- Constrained JSON/schema output is available with supported model APIs; for example OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses . Schema conformance is not a substitute for semantic evaluation.

### Patch, CI, deployment
- Existing parser fix: `v2/radar.py` commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`; regression tests: `v2/test_radar.py` commit `22496f9714a7628d4c93929005a2d10773a753cc`; CI [#38211941792](https://github.com/AvinashBhalla/job-beeper/actions/runs/38211941792) passed.
- Current dev command's complete reported test run is green (78 tests); dev safe config is confirmed and prod health remains OK.
- LLM feature has no code/config/requirements change, no new CI run, no main merge or production deploy this turn. No source integration work performed.
- Handover files were updated directly on `v2-live-radar`, without a docs-only branch/PR. New documentation commits are `cb56269633878df78804363b86ae4e7b0a8aed7f` and `7101b74e19190807fd31c55a4e2dce74aa2ff90a`; latest documentation CI was pending at last check, not yet claimed passed.

### Next action
1. Promote the verified experience parser fix through a reviewed PR/merge to `main` and check main CI. Do not switch the production Oracle checkout as part of promotion.
2. Before implementing LLM code, decide provider/model, secret configuration, and hard spend/request limits. Store keys only in secret configuration, never git/docs/chat.
3. Add an isolated disabled-by-default extraction module and tests; shadow-run only missing/ambiguous descriptions on dev with notifications off. Measure accuracy, confidence, latency, failures and cost.
4. Resume source roadmap only after release gate: Greenhouse one-board dev canary, then Instahyre schema/freshness validation, then Ashby/Lever/SmartRecruiters. Preserve no historical alert replay and no LinkedIn limit evasion.

### Continuation prompt
“Continue Job Radar V2. Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. User supplied successful dev verification: 78 tests pass in 53.339s; dev health OK at port 8001, config v10 is Naukri-only with notifications off, source status agrees, and production port 8000 remains healthy. The LinkedIn experience parser fix is ready for reviewed promotion to main; verify main CI, but do not switch the production VM checkout as part of promotion. User proposed an LLM to extract skills/experience from JDs. No LLM implementation/provider has been chosen. Design it as a separate disabled-by-default strict-schema extractor with local validation, deterministic/source-labelled metadata precedence, uncertainty on conflicts, prompt-injection isolation, cache by JD hash/schema, timeouts/backoff and hard spend caps. Shadow mode first with notifications off; evaluate required/preferred skills, year ranges, skill-specific vs total experience, missing/conflicting fields and malicious text. Select provider and secure budget/secrets before coding. No production change; then Greenhouse one-board dev canary and later Instahyre/ATS roadmap.” 


## 2026-10-12 — Gemini JD extraction implemented in dev branch (not yet VM-verified)

### User decision
Use Gemini for job-description extraction; the user will enter the API key directly on the dev VM. Work stays on \`v2-live-radar\`; do not merge or deploy this feature to production.

### Code changes
- Added \`v2/gemini_extractor.py\`: bounded Gemini REST integration with strict structured JSON output and local semantic validation for overall experience range/type/evidence, required skills, preferred skills, and confidence.
- Default model is \`gemini-3.5-flash-lite\` (configurable via \`GEMINI_MODEL\`). Google’s current pricing page lists a free tier for this model and a 1M-token context window; free-tier content may be used to improve Google products. Confirm current model quota/terms in AI Studio before enabling.
- Wired extraction into \`run_source\` as shadow-only. Extracted values are stored separately in SQLite table \`gemini_shadow_cache\`; they do not modify jobs, matching, scores, notification decisions, or Telegram delivery.
- Added \`GET /api/llm-shadow-status\`, returning enabled/key-configured booleans, model, usage caps, cache summary, and recent structured results. It never returns the key or raw JD.
- Dev Compose accepts \`GEMINI_API_KEY\`, \`GEMINI_MODEL\`, \`GEMINI_EXTRACTION_ENABLED\`, \`GEMINI_MAX_CALLS_PER_RUN\`, and \`GEMINI_MAX_CALLS_PER_DAY\`. Defaults: disabled, 3 calls per source run, 20 calls/day. Output is capped and cached by source/job/JD hash; errors are briefly cached. API key is passed only through runtime environment, never committed.
- Added \`v2/test_gemini_extractor.py\` for validation, evidence checks, cache behavior, disabled-by-default behavior, and no mutation of source job data.

### Verification status
- Code/config committed directly to \`v2-live-radar\`; latest known application patch commit: \`5a73bd041bbf5455b1fa9c0a0828ce21a39ecab3\` (later doc commits follow).
- The new Gemini test suite and the full 78-test existing suite have **not yet been run on the dev VM**. Do not describe this as verified or production-ready until the dev rebuild, full test suite, API smoke test (with key kept hidden), status endpoint, and production health check pass.
- Production must remain unchanged at port 8000. Dev remains loopback-only at port 8001, with notifications disabled and Naukri as the only enabled source.
- No key, secret, raw JD, or full model request/response should be copied into GitHub, handover docs, logs, or chat. Avoid sending candidate PII; only public job-posting text is in scope.

### Next steps
1. On the VM, fetch \`v2-live-radar\`, enter the key through a hidden prompt, export the Gemini environment variables, rebuild only \`job-radar-dev\`, run the full unit suite, and verify \`/health\`, \`/api/config\`, \`/api/llm-shadow-status\`, and port 8000 health. Keep notifications off.
2. Review the first shadow outputs for explicit overall experience vs skill-specific experience, required vs preferred skills, null handling, and confidence. Confirm no matcher/alert output changes.
3. Fix any failures before further work. Keep Gemini shadow-only until accuracy is measured on representative fixtures. Do not promote or merge as part of this VM smoke test.

### Continuation prompt
“Continue Job Radar V2. First read \`docs/JOB_RADAR_HANDOVER.md\`, \`docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md\`, and \`docs/JOBBEEPER_REFERENCE.md\` on \`v2-live-radar\`; update both handover docs after every prompt. Gemini extraction has now been implemented on \`v2-live-radar\` as a disabled-by-default, separately cached, shadow-only feature. Default model is \`gemini-3.5-flash-lite\`; runtime env key is \`GEMINI_API_KEY\`, feature toggle \`GEMINI_EXTRACTION_ENABLED=true\`, limits 3 calls/run and 20/day. New tests are not yet verified on the dev VM. Next: hidden-input API key, rebuild only dev port 8001, run all tests, check \`/api/llm-shadow-status\`, keep notifications off, and confirm production port 8000 remains healthy. Do not merge or deploy. Never log or commit secrets.”


### Follow-up hardening — 2026-10-12
- Added explicit \`experience_scope\` (\`total_professional\`, \`skill_specific\`, \`unknown\`) to the structured result so skill-specific years cannot be silently treated as total experience.
- Corrected nullable Gemini schema fields and broadened detection of skill-specific experience wording.
- Wrapped the shadow pass fail-open so cache/LLM errors cannot block normal source ingestion.
- Default model is \`gemini-3.5-flash-lite\`, selected for structured extraction and free-tier availability listed on Google’s current pricing page. Free-tier data-use terms and model quotas still apply; verify the selected project/model in AI Studio before enabling.
- Draft validation PR: https://github.com/AvinashBhalla/job-beeper/pull/35. It is not merged and must not be merged until dev VM tests and shadow review pass. The GitHub connector reported no status checks/workflow runs for the latest head at the time of this update; this is not evidence of passing CI.
- Latest app-code commit at this point: \`cd3a8a694e08b451d738d6fbc789b86c323c4f5b\`. New and existing tests have not yet been executed on the VM.



## 2026-10-12 — Dev VM feedback: test syntax fixed; rerun required

### User-reported evidence
- The Gemini API smoke test succeeded with the synthetic posting and returned 4–6 years, required Python/FastAPI, preferred Kubernetes, and \`total_professional\` scope.
- Dev health was OK; Naukri was the only enabled source. Dev config confirmed \`notifications_enabled=false\`; production port 8000 remained healthy.
- \`/api/llm-shadow-status\` showed Gemini enabled/configured, 3 calls today, 3 successful cached results, 0 errors. Recent Naukri results included several role/domain experience ranges incorrectly or ambiguously labeled \`skill_specific\`; treat this as an extraction-quality issue, not a matcher input, because mode remains shadow-only.

### Fixes made on \`v2-live-radar\`
- Fixed malformed dictionary/list brackets in \`v2/test_gemini_extractor.py\` that caused a SyntaxError during unittest discovery. Fix commit: \`7941a99129614ffb03a7406e8fd002e1535fb05d\`.
- Tightened the prompt in \`v2/gemini_extractor.py\`: \`total_professional\` requires explicit overall/total/professional/work wording; named technology experience is \`skill_specific\`; role/domain-only phrases such as “Java Full Stack Development experience” should be \`unknown\` unless scope is explicit. Prompt change commit: \`def76ed2fe1f181b8501f25c09098161ef669b87\`.
- The previously reported full test run is **failed**, not passed: 79 tests discovered, with one import-time SyntaxError. No new full test run has yet confirmed the fix.

### Immediate next steps
1. Fetch latest \`origin/v2-live-radar\` on \`/home/ubuntu/job-beeper-dev\`.
2. Rebuild only \`job-radar-dev\`, rerun the full unittest discovery. Do not continue if any tests fail.
3. Recheck dev health/config, \`/api/llm-shadow-status\`, and production port 8000. Keep notifications disabled.
4. Inspect new shadow rows after the next permitted source run. The model output remains observational only; do not connect it to matcher decisions or alerts yet.
5. Do not merge draft PR #35 or deploy to production until full tests and a representative shadow evaluation pass.



## Latest handoff — 2026-10-12: Gemini tests pass; API authentication errors need diagnosis

### User-provided evidence
- Full dev test suite: **84 tests ran in 54.614s; OK**.
- Dev health is healthy on port 8001; Naukri completed successfully, 296 jobs seen, 1 new, no source error.
- Gemini shadow status: enabled, key-present flag true, model `gemini-3.5-flash-lite`, shadow-only, daily limit 20, calls today 6, 3 successful cached results and 3 cached errors.
- The three newest Gemini requests failed with `gemini_http_401`; earlier requests in the same runtime had succeeded. Dev config remains Naukri-only with notifications disabled. Production port 8000 remains healthy.
- No API key was included in the user message. No code changes were made in response to this evidence.

### Diagnosis (high confidence on symptom, root cause unconfirmed)
HTTP 401 indicates Gemini rejected authentication for those calls. `api_key_configured=true` only confirms that a non-empty key was supplied; it does not prove that the key is valid, active, unrestricted for the Generative Language API, or still the same key used for earlier successes. Because earlier calls succeeded and the newest calls failed, check whether the VM environment/container was recreated with a different, malformed, revoked, or API-restricted key; also verify that the Google project/API and selected model are enabled. Do not paste the key into chat, terminal output, logs, or docs. Do not print environment variables or run commands that echo the key.

### Next action — diagnose without exposing credentials
1. On the VM, inspect only safe metadata (container name, configured model, feature toggle and key-present boolean) without printing the key.
2. In Google AI Studio / Google Cloud, confirm the key is active, belongs to the intended project, has access to the Gemini API/Generative Language API, and has no incompatible API/referrer/IP restriction. If uncertain, create a replacement key and enter it through the existing hidden-input prompt.
3. Recreate only the dev `radar` service with the key injected through the hidden prompt; do not change production or enable notifications.
4. Run a single synthetic API smoke test and inspect only HTTP status/error category and whether a structured response was accepted. Avoid triggering another full source scan while troubleshooting, since the 20-call/day cap is active and three calls have already failed.
5. Recheck `/api/llm-shadow-status`; do not delete cached error rows or increase call limits merely to hide the issue. If authentication succeeds, resume a small representative shadow sample and review experience scope quality. Keep PR #35 unmerged and Gemini shadow-only.

### Current release gate
- Unit tests are green: 84 passed.
- Dev app health is green; production health is green.
- Gemini authentication is **not green**: three recent calls failed with HTTP 401.
- Feature remains isolated in dev and shadow-only. No production deployment, matcher mutation, or notification behavior change occurred.
- Do not promote/merge PR #35 until the authentication issue is resolved and shadow quality is reviewed.

### Continuation prompt
“Continue Job Radar V2. First read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every user prompt. Latest VM evidence: 84 tests pass in 54.614s; dev port 8001 healthy, Naukri-only, notifications off; production port 8000 healthy. Gemini shadow status is enabled for `gemini-3.5-flash-lite`, 6 calls today, 3 successful cached results, 3 errors; latest three errors are `gemini_http_401`. Earlier calls succeeded, so verify key validity/API enablement/restrictions using Google AI Studio and hidden-input key entry; never print or share the key. Test one synthetic request only, then recheck status. Do not increase budgets, merge PR #35, alter matcher/alerts, or deploy production until authentication and representative shadow quality pass.”


## Latest handoff — 2026-10-12: Gemini requests succeeding again; shadow quality review remains

### User-provided evidence
- `/api/llm-shadow-status` now reports 12 calls today, 6 successful cached results and 6 cached errors; the newest three results are successful at 08:14 UTC using `gemini-3.5-flash-lite`.
- Three older calls from 08:12 and three from 08:07 remain recorded as `gemini_http_401`. This is consistent with authentication now working for newer requests, but the exact cause of the earlier 401s is unconfirmed. Cached errors are historical and do not by themselves prove the current key is still failing.
- Dev feature remains enabled in `shadow_only` mode. User did not provide fresh health/config output in this message; prior report had 84 tests passing and both dev/prod health healthy.
- No code changes were made. Do not spend the remaining daily request budget just to clear historical error rows.

### Shadow-output quality notes
- The recent successful results demonstrate that structured extraction is working on varied descriptions, including a range (3–8 years), minimum-only experience (6+ years), and a .NET role with a 6–11-year range.
- At least one output has `experience_evidence=null` despite a populated range, and scope classifications are semantic judgments (for example, QA/testing focus versus total professional experience). These results need a labelled manual review before any production integration.
- Do not treat high model confidence as proof of correctness. Results remain isolated from job rows, matcher inputs, scores, eligibility, and Telegram notifications.

### Next action
1. Avoid triggering extra Naukri scans solely for Gemini tests; calls today are already 12/20.
2. On the next naturally occurring permitted shadow calls, confirm new requests continue returning `status=ok` with no new 401s. If a fresh request fails, inspect only the redacted error category and verify key/API restrictions without printing the key.
3. Manually compare a small sample against the original JD for exact ranges, required/preferred classification, evidence excerpt, and `experience_scope`. Flag missing evidence and ambiguous scope as review cases.
4. Keep PR #35 unmerged, Gemini shadow-only, notifications disabled in dev, and production untouched until the representative evaluation is documented and accepted.

### Current release gate
- Full dev test suite: 84 passed (user-provided).
- Latest Gemini requests: successful; six earlier authentication failures remain cached.
- Extraction-quality evaluation: incomplete.
- Production: no deployment or behavior change.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`, and update both handovers after every prompt. Latest Gemini status: 12 calls today, 6 successes, 6 errors; the newest three requests at 08:14 UTC are successful, while earlier cached calls show `gemini_http_401`. Authentication appears to be working again for recent calls, but root cause is unconfirmed. Avoid burning the 20/day budget. Manually evaluate a small representative sample for exact experience range, required/preferred skills, evidence excerpts, and total-vs-skill-specific scope. Keep feature shadow-only, notifications off, PR #35 unmerged, and production unchanged.”


## Latest handoff — 2026-10-12: Dev dashboard access and remaining validation

- User asked how to review dev notifications/dashboard while the app runs on the development VM and asked to continue remaining work.
- Confirmed from `v2/docker-compose.dev.yml`: dev binds only to `127.0.0.1:8001`, persists to isolated `radar-dev-data`, has blank Telegram token/chat ID, and does not expose port 8001 publicly. Production port 8000 remains separate and untouched.
- Dev dashboard should be accessed with an SSH tunnel from the user's computer: `ssh -L 8001:127.0.0.1:8001 ubuntu@YOUR_ORACLE_VM_IP`, then open `http://127.0.0.1:8001`. On VM, check `curl -s http://127.0.0.1:8001/health` and `curl -s http://127.0.0.1:8001/api/llm-shadow-status`.
- Dev Telegram notifications are deliberately disabled. Do not enable them to validate Gemini; Gemini is shadow-only and must not affect matching or delivery. Telegram alerts observed on the user's existing bot are therefore production alerts unless separately routed to a dev-only bot/chat in a future deliberate test.
- Current Gemini evidence remains 12/20 calls, 6 successes and 6 cached historical errors; latest three calls succeeded. Some results need comparison against source JD text, particularly null/missing evidence and scope labels. Do not trigger extra source scans or clear historical error rows just to improve status appearance.
- Code inspection confirmed extractor validates evidence by checking that the returned evidence text is present in the JD, then drops evidence to null when it is not an exact substring. This explains why paraphrased evidence can be null, but does not prove the experience range itself is wrong. No code change in this turn.
- Official Gemini docs now indicate standard API keys are being phased out/rejected from September 2026 and newly created AI Studio keys are auth keys; this may be relevant if fresh 401s recur, but latest requests succeed, so do not rotate/change credentials without new failure evidence. Reference: https://ai.google.dev/gemini-api/docs/api-key?authuser=00 and https://ai.google.dev/gemini-api/docs/api-errors.
- Remaining-work gate: manually evaluate a small labelled sample using original job descriptions and cache outputs; then run any extractor/schema regression tests if a concrete defect is identified. Keep PR #35 unmerged, Gemini shadow-only, notifications disabled, and production unchanged. Greenhouse one-board dev canary remains blocked until this quality gate passes.
- Exact next action: user can access dashboard through SSH tunnel and provide a small sample of job titles/IDs plus the original JD experience sentence(s) (no secrets or personal data) to compare against `/api/llm-shadow-status`. Avoid additional scans while daily Gemini usage is 12/20. After the labelled sample passes, proceed to the guarded Greenhouse one-board dev canary with notifications off.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Dev is isolated on localhost:8001 and Telegram is deliberately disabled; production stays on 8000. Gemini remains shadow-only (12/20 calls, 6 successes, 6 historical cached errors; latest three succeeded). Compare a small sample against original JD evidence before any Greenhouse canary. Do not trigger unnecessary scans, enable dev Telegram, merge PR #35, or deploy production.”


## Latest handoff — 2026-10-12: Dev access clarification and Gemini evidence-quality patch

### Dev dashboard URL correction
- Production dashboard is publicly reachable at `http://130.210.27.197:8000/dashboard/#jobs` (port 8000). The development service binds only to `127.0.0.1:8001`; therefore `http://130.210.27.197:8001` is intentionally not a valid public URL.
- From the user's Windows computer, open a terminal and run `ssh -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197` using their normal SSH key/options; keep the terminal open, then visit `http://127.0.0.1:8001/dashboard/#jobs`. If local port 8001 is already occupied, use `ssh -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197` and open `http://127.0.0.1:18001/dashboard/#jobs`.
- Dev is healthy per latest user output; Naukri last success 2026-10-12T08:54:57Z, 294 jobs seen, zero new in that run, no source error. Production remains separate and was not changed in this turn.

### Latest Gemini status and quality observations
- Latest user status: shadow-only, 20/20 daily calls used, 14 successes and 6 cached errors. Do not trigger scans or further API tests today. Daily cap must not be increased.
- Several recent successful records have populated experience ranges but `experience_evidence=null`; scope labels such as `skill_specific` for “QA/testing with a focus on Salesforce” require conservative treatment. Since original job descriptions were not included, these are review flags rather than confirmed range errors.

### Patch on `v2-live-radar`
- Updated `v2/gemini_extractor.py` to require exact, contiguous verbatim JD evidence, avoid classifying technology focus/role/domain as skill-specific unless the years are directly tied to a named tool, and use unknown for ambiguous scope. Evidence verification now collapses whitespace in both quote and JD before exact-substring comparison, so line wraps do not erase a valid quote.
- Bumped cache extraction version to `gemini-shadow-v2` so prior outputs do not count as results from the revised prompt on future requests.
- Added regression tests for multiline evidence and prompt guidance in `v2/test_gemini_extractor.py`.
- Commits: extractor prompt/logic initially `a9acd2e571760e325ddb9d98441f0924545dade8`, whitespace fix `0e4fd7332e4b8662ef89c500c7124f98e48dd712`, tests `782b2b8c4aead193e275d88adb7e9c98ec3a3c9a`.
- GitHub Actions V2 CI run #435 (run ID 38226790483) was `in_progress` at last check; combined status endpoint returned no status entries. Do not claim CI passed until it completes. No dev VM rebuild/test has yet been reported for this patch.

### Immediate next actions
1. Access the dev dashboard using the SSH tunnel above; never make port 8001 public.
2. Wait for V2 CI run #435; if it fails, inspect the exact failing test and fix on this branch only.
3. Pull the latest `v2-live-radar` in `/home/ubuntu/job-beeper-dev`, rebuild only the dev service, run the full test suite, and check dev health/status. Keep notifications disabled and production port 8000 untouched.
4. Since the 20-call daily cap is exhausted, do not trigger a source run today. After the next UTC daily window, review fresh `gemini-shadow-v2` outputs against original JDs before Greenhouse canary.
5. Keep PR #35 unmerged; Greenhouse canary remains gated on representative extraction quality and passing tests.

### Continuation prompt
“Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Production dashboard is `http://130.210.27.197:8000/dashboard/#jobs`. Dev is loopback-only: SSH tunnel `ssh -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197`, then open `http://127.0.0.1:8001/dashboard/#jobs`. Latest status: Gemini calls 20/20, 14 successes, 6 errors; do not trigger more calls today. Patch on branch bumps extraction version to gemini-shadow-v2, asks for exact verbatim evidence, conservatively labels ambiguous experience scope, normalizes whitespace, and adds regression tests. CI run #435 was in progress; verify it, then rebuild/test dev only. Keep notifications off, production unchanged, PR #35 unmerged, and validate fresh results against source JDs before Greenhouse canary.”


## 2026-10-12 — Dev SSH tunnel authentication blocked
- User ran `ssh -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197` from Windows PowerShell and received `Permission denied (publickey)`. The port-forward syntax is valid, but SSH authentication failed before the tunnel could be established. The previously known context does not identify the user's private-key path or working SSH invocation; do not guess a key or change server SSH settings.
- Next diagnostic: ask the user to run `Get-ChildItem "$env:USERPROFILE\.ssh"` in PowerShell and report filenames only (never paste private-key contents). If they use an Oracle Cloud downloaded `.key`/`.pem` file or a custom key, use that exact local path with `ssh -i "C:\path\to\key.pem" -L 8001:127.0.0.1:8001 ubuntu@130.210.27.197`. If a known working SSH command/host alias exists, preserve its identity/user/options and add only the port-forward flag. Do not alter production, dev service bindings, or server authorized_keys without evidence.
- After SSH auth succeeds, keep the tunnel terminal open and visit `http://127.0.0.1:8001/dashboard/#jobs`; if local 8001 is occupied, forward local 18001 to remote 8001 and use `http://127.0.0.1:18001/dashboard/#jobs`.
- This turn did not change app code, deployment, SSH server configuration, or production. Continue pending CI/dev-only validation of the Gemini evidence-quality patch; do not trigger more Gemini calls while today's 20-call cap is exhausted.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. SSH tunnel command failed with `Permission denied (publickey)` from Windows PowerShell. Ask for SSH key filenames only using `Get-ChildItem \"$env:USERPROFILE\\.ssh\"`, then construct an SSH command using the user's actual key or known working SSH options; never request or expose private-key contents. Keep dev on localhost:8001, production untouched, Gemini shadow-only, and continue CI/dev-only validation.”


## 2026-10-12 — SSH tunnel established; CI green; dev-only validation next
- User confirmed the SSH tunnel is connected and the Job Radar V2 development dashboard opened at `http://127.0.0.1:8001/dashboard/#jobs`. This confirms local forwarding and authentication now work. No runtime health/test output has been supplied yet.
- GitHub Actions V2 CI run #435 (run ID `38226790483`) for commit `782b2b8c4aead193e275d88adb7e9c98ec3a3c9a` is now `completed/success`. This clears the CI gate for updating the isolated dev checkout, not for production release.
- Repo instructions confirm dev checkout `/home/ubuntu/job-beeper-dev`, Compose file `v2/docker-compose.dev.yml`, project `job-radar-dev`, service `radar`, loopback host port 8001, independent volume `job-radar-dev_radar-dev-data`; dev notifications are hard-disabled by blank Telegram environment values. Never run Compose commands against production project or use `down -v`.
- Next safe sequence: (1) from a second SSH session (keep the tunnel session open), inspect `cd /home/ubuntu/job-beeper-dev && git status --short --branch && git rev-parse --short HEAD && git fetch origin v2-live-radar && git log -1 --oneline origin/v2-live-radar`; stop if working tree is dirty or branch is not `v2-live-radar). (2) If clean and correct branch, `git pull --ff-only origin v2-live-radar`. (3) Rebuild/start dev only with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build`. (4) Verify `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml ps`, `curl -fsS http://127.0.0.1:8001/health`, `curl -fsS http://127.0.0.1:8001/api/llm-shadow-status`, and run tests inside the dev container with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml exec -T radar python -m unittest discover -s v2 -p 'test_*.py'`. Never print environment variables or secrets. If any check fails, capture sanitized error output and stop before source scans.
- Gemini quota was 20/20 for the prior reported daily window; do not initiate source scans or extra Gemini API calls as part of this validation. Confirm feature remains shadow-only, Telegram notifications remain disabled, and production port 8000/container/database remain untouched. PR #35 stays unmerged; Greenhouse canary remains gated on reviewed sample quality.
- Continuation prompt: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. SSH tunnel and dev dashboard now work. CI run #435 passed for `782b2b8c4aead193e275d88adb7e9c98ec3a3c9a`. In a second SSH session inspect the dev clone status/branch, fast-forward only if clean and on `v2-live-radar`, rebuild only `job-radar-dev`, then run full unittest discovery and health/shadow status checks. Do not scan jobs or spend Gemini quota, expose secrets, enable notifications, merge PR #35, or touch production.”


## 2026-10-12 — Dev checkout behind branch; runtime tests pass on old image
- User-reported dev checkout: branch `v2-live-radar...origin/v2-live-radar [behind 14]`, local HEAD `aa74445`; fetched remote tip shown as `a800e9d` at time of inspection. This checkout has not yet fast-forwarded to the extractor patch commits.
- User rebuilt/restarted `job-radar-dev` before pulling the branch: container is Up and maps `127.0.0.1:8001->8000/tcp`. Health endpoint is OK; Naukri reports last success `2026-10-12T09:41:56Z`, 294 jobs seen, 0 new, no error.
- Full in-container unittest discovery passed: 86 tests in 53.328s, `OK`. This verifies the currently built checkout only, not the newer Gemini evidence patch.
- `/api/llm-shadow-status` reports `enabled=false`, `api_key_configured=false`, calls_today 20/20, cache 14 successes/6 errors, and recent rows still use `gemini-shadow-v1`. Do not enable Gemini, expose/replace credentials, or trigger scans to test the patch. Old cache rows are not evidence of the new extraction version.
- Safe next step: run `git status --short --branch` and confirm clean working tree and branch `v2-live-radar`; then `git pull --ff-only origin v2-live-radar`. Rebuild only `job-radar-dev` with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build`, verify `ps` and `/health`, then rerun full unittest discovery. Re-check `/api/llm-shadow-status` for feature configuration/version only; do not trigger source scans. Stop if working tree is dirty, branch differs, pull is not fast-forwardable, or rebuild/tests fail.
- Production port 8000, production checkout/database/volume/config, notification settings, and PR #35 remain untouched; do not merge or deploy. Keep Greenhouse canary gated on a reviewed fresh Gemini sample after quota availability and deliberate approval.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Dev checkout was `aa74445`, 14 commits behind origin; container health OK and all 86 current-image tests pass, but Gemini status is disabled/unconfigured and cached rows remain `gemini-shadow-v1`, so new extractor patch is not yet deployed. Verify clean correct branch, fast-forward only, rebuild/test dev only. No scans/API calls, no secrets, notifications stay off, production untouched, PR #35 unmerged.”


## 2026-10-12 — Dev rebuild after fast-forward; tests green, Gemini disabled
- User fast-forwarded `/home/ubuntu/job-beeper-dev` from `a800e9d` to `2e168ad` and rebuilt only `job-radar-dev`. Build completed; container is Up at loopback `127.0.0.1:8001`; `/health` reports OK and Naukri has no error (`295` seen, `3` new in latest run).
- Full test suite passed again: 86 tests in 53.279s, `OK`. The GitHub branch source confirms `v2/gemini_extractor.py` sets `EXTRACTION_VERSION = "gemini-shadow-v2"`, and `v2/test_gemini_extractor.py` contains the whitespace-wrap regression test.
- `/api/llm-shadow-status` still shows `enabled=false`, `api_key_configured=false`, calls_today 20/20, 14 successes/6 cached errors, and historical cached results labeled `gemini-shadow-v1`. Historical cache rows are expected to retain their original version and cannot verify runtime code version. No new Gemini API calls were triggered by the validation.
- Next safe check: run inside the container `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml exec -T radar python -c 'from v2.gemini_extractor import EXTRACTION_VERSION; print(EXTRACTION_VERSION)'`. Expect `gemini-shadow-v2`. Also optionally verify config booleans only; do not print environment values or secrets. Do not enable Gemini or configure credentials without explicit approval and a deliberate plan. No source scan is needed.
- Production remains untouched; notifications remain off; PR #35 remains unmerged; no Greenhouse canary until a reviewed fresh sample is available after quota reset and an approved test plan.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both after every prompt. Dev is rebuilt at HEAD `2e168ad`; health OK; 86 tests pass. Branch source contains `gemini-shadow-v2` and new regression test. API status says Gemini disabled/unconfigured and cache rows are old v1; verify imported runtime version directly inside container without scans/API calls. Keep production untouched, notifications off, PR #35 unmerged.”


## 2026-10-12 — Persistent source-error visibility work started
- No deployment: 150d287 updates v2/radar.py so GET /api/source-status returns the most recent persisted source_runs.error as last_error; 6e78074 updates dashboard/app.js to render persisted source errors; c3f64c6 adds regression tests for an errored latest run and for a later successful run clearing the error.
- CI run #459 (38233473677) was in progress when this entry was prepared. Verify final CI status before deploying.
- No source scan, Gemini API call, source activation, or production change was made. Keep Gemini disabled, dev notifications off, PR #35 unmerged, and production untouched.
- Next: if CI is green, update and rebuild only /home/ubuntu/job-beeper-dev, run full tests and health/source-status checks, then verify the error appears for a failed run and clears after success. Select the next source roadmap item after this validation.
- Continuation: Read both handovers and docs/JOBBEEPER_REFERENCE.md on v2-live-radar; update both after every prompt. Persisted source-error visibility was added to API/dashboard and regression tests; CI was pending. No scans/Gemini calls; production untouched.


## 2026-10-12 — Source-error visibility CI result
- Follow-up to the previous entry: V2 CI run #459 (run ID 38233473677) completed successfully for code commit c3f64c684d47045bcc334e77213d913ad912f67b. PR #35 remains draft/open/unmerged; this is not production approval.
- Documentation updates are on v2-live-radar: knowledge transfer commit da4b0fb42773c2effd6af8b4e6dfed1f3d1dfcf9 and detailed handover commit 65d6825034115cdba8ac183692de37ba8ed80027. Latest branch head after these updates is expected to be 65d6825.
- Next action: in /home/ubuntu/job-beeper-dev, verify clean tree and correct branch, fast-forward only, rebuild only job-radar-dev, run full tests and health/source-status checks. Do not run manual scans, enable Gemini, turn on notifications, or touch production.
- Continuation: Source-error visibility patch passed V2 CI #459. Validate in isolated dev, then continue roadmap one item at a time. Keep production untouched and PR #35 unmerged.


## 2026-10-12 — Dev regression suite result received
- User reports the isolated development test suite completed: `Ran 88 tests in 53.297s` and `OK`. This is a positive test result for the current checkout, but by itself does not confirm the new `/api/source-status` behavior at runtime or dashboard rendering.
- The source-error visibility code is committed on `v2-live-radar` (150d287 API, 6e78074 dashboard, c3f64c6 tests); V2 CI #459 succeeded. No production deployment, source scan, Gemini API call, or source activation.
- Next verification: ask for `curl -fsS http://127.0.0.1:8001/health` and `curl -fsS http://127.0.0.1:8001/api/source-status` output from dev. Confirm `last_error` is present and latest successful run shows null. Then visually check Source Health dashboard. If all good, continue with the reference roadmap’s next item: verify the LinkedIn experience parser patch on dev before considering any main promotion. Keep Gemini disabled, notifications off, and PR #35 unmerged until separately reviewed.
- Continuation: Read both handovers and docs/JOBBEEPER_REFERENCE.md on v2-live-radar; update both handovers after each prompt. Dev reports 88 tests OK in 53.297s. Need health/source-status runtime output and dashboard check before moving to LinkedIn parser validation; production untouched.


## 2026-10-12 — Dev source-status runtime output received
- User ran `curl -fsS http://127.0.0.1:8001/health` and `curl -fsS http://127.0.0.1:8001/api/source-status` in `/home/ubuntu/job-beeper-dev`. Health returned `status=ok`, version `2.0.0`; Naukri was idle after a successful run at `2026-10-12T10:03:49.082163+00:00`, with 292 jobs seen, 2 new, and no runtime error.
- The source-status response includes `last_error` for all four source entries. Naukri has `last_error=null`; LinkedIn, Instahyre, and Greenhouse are disabled and have no run history, as expected. This confirms the patched API response shape and a healthy runtime, but no real persisted error was present to test display/clear behavior.
- Remaining acceptance check: visually inspect the dev Source Health dashboard via the existing SSH tunnel and confirm source errors are rendered when present. Do not induce a real source failure or run a scan solely to test this. Once dashboard rendering is confirmed, proceed to validate the LinkedIn experience-parser patch in dev before any promotion consideration.
- No production deployment, notification change, source activation, manual scan, or Gemini API call. Production port 8000 remains untouched; Gemini remains disabled; dev notifications remain off; PR #35 remains unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar` and update both handovers after every prompt. Dev health is OK and `/api/source-status` includes persisted `last_error`; Naukri had 292 seen / 2 new / no error. Need visual Source Health dashboard confirmation via SSH tunnel, then validate LinkedIn experience parser in dev. No scans or induced failures; keep production untouched, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — Source Health dashboard visually confirmed; LinkedIn parser validation next
- User supplied a screenshot of the dev dashboard at `127.0.0.1:8001/dashboard/#sources` through the SSH tunnel. Source Health table loads correctly: LinkedIn, Instahyre, and Greenhouse show disabled; Naukri Relay shows active; diagnostics display Operational for all four. No visible frontend error or layout issue in the screenshot.
- This completes visual confirmation of the source-status UI in its current healthy/no-error state. Since no source error is present, the screenshot does not prove how a non-null error is rendered; do not force a source failure or run a scan solely for this.
- Start the next roadmap item: validate the committed LinkedIn labeled-experience parser in the isolated dev checkout. The current branch code has `extract_linkedin_labeled_experience` in `v2/radar.py`, documented for labels such as `Experience: 4.00-6.00 Years`. Inspect its call site and regression tests, run targeted tests (then full suite if needed) in dev, and do not enable LinkedIn scanning or promote to main until evidence is green.
- No production deployment, source activation, notification change, scan, or Gemini API call. Production port 8000 remains untouched; Gemini disabled; dev notifications off; PR #35 unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`, update both handovers after every prompt. Dev Source Health screenshot is visually correct (Naukri active; other sources disabled; all diagnostics Operational). Next inspect `extract_linkedin_labeled_experience` call site and regression tests, then validate in dev without enabling LinkedIn or triggering scans. Keep production untouched, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — LinkedIn labeled-experience integration inspected
- User confirmed dev checkout reports clean branch `## v2-live-radar...origin/v2-live-radar`; the grep output shows `extract_linkedin_labeled_experience` supports labeled ranges (`Experience: 4.00-6.00 Years`), plus values and single values. Regression test `test_linkedin_structured_experience_metadata_outside_description_is_captured` in `v2/test_radar.py` mocks the detail HTML, calls `enrich_linkedin_job`, asserts 4.0–6.0 is stored in JD experience fields, and checks matcher rejection for candidate experience 2.
- The detail-fetch call site parses `page_text` for labeled experience before gathering JD description candidates. This is a promising integration regression test; no runtime tests were executed by the assistant and no promotion is approved yet.
- Next command in isolated dev: `python -m unittest v2.test_radar` (or the repository's standard test command) to exercise the focused test and neighboring radar behavior; then run the full suite if green. Do not enable LinkedIn, trigger a source scan, or promote to main as part of this test. Capture exact pass/fail output and investigate any failure before changing code.
- Production port 8000 remains untouched; dev notifications off; Gemini disabled; PR #35 unmerged; no scans or Gemini calls.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. LinkedIn experience parser call site and regression test were inspected. Run `python -m unittest v2.test_radar` in isolated dev, capture output, then full suite if green. Keep LinkedIn disabled, no scans, production untouched, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — Test command adjustment: Python executable
- User attempted `python -m unittest v2.test_radar` from `/home/ubuntu/job-beeper-dev`; the VM shell reports `python: command not found` and suggests `python3`. This is an executable-name/environment issue, not a test failure; no tests ran yet.
- Next try `python3 -m unittest v2.test_radar`. If project dependencies are installed only in its virtual environment, inspect `ls -la` and use the repo's documented venv/test command; do not install packages globally or alter system Python. Capture full output, then run the full test suite if targeted tests pass.
- Keep LinkedIn disabled, do not trigger scans, keep notifications off, Gemini disabled, production untouched, and PR #35 unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. In dev, `python -m unittest v2.test_radar` did not run because `python` executable is missing. Retry using `python3 -m unittest v2.test_radar`; if dependencies are in a venv, use repo's documented environment. No source scan/activation, no production changes, Gemini disabled, notifications off, PR #35 unmerged.”


## 2026-10-12 — Host Python test import failed due to missing dependency
- User ran `python3 -m unittest v2.test_radar` in `/home/ubuntu/job-beeper-dev`; import failed at `from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning` with `ModuleNotFoundError: No module named 'bs4'`. The unittest loader reports one failed import; no radar tests executed.
- Project Docker image installs `v2/requirements.txt` in Python 3.12 container; dev Compose service/container is `radar` / `job-radar-dev`. Prefer testing with the dev container's Python environment (e.g. `sudo docker exec job-radar-dev python -m unittest v2.test_radar` only if the tests are present inside that image; current Dockerfile copies only `v2/radar.py` and related runtime files? Verify test availability before using this exact command). Safer next step is inspect `v2/requirements.txt` and available repo test-run instructions, then use an isolated virtual environment if host tests are needed; do not pip-install into system Python.
- Keep LinkedIn disabled, do not run source scans, notifications off, Gemini disabled, production untouched, PR #35 unmerged.
- Continuation: “Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. Host `python3 -m unittest v2.test_radar` failed during import because host Python lacks `bs4`; no tests ran. Docker dev container installs app requirements but may not contain tests; verify test availability before choosing container or isolated venv. Never install into system Python. Keep LinkedIn disabled, no scans, notifications off, Gemini disabled, production untouched, PR #35 unmerged.”


## 2026-10-12 — Dev radar tests passed
- User reports the radar test module ran inside the dev container: 80 tests in 53.200s, OK. Container confirmed BeautifulSoup and `/app/v2/test_radar.py` are available; earlier host Python lacked `bs4`, so tests should run in container.
- Next run the full project test suite inside dev, including Gemini extractor tests. Do not run live scans or Gemini API calls. If green, review CI and parser patch before any promotion decision.
- LinkedIn remains disabled; notifications off; Gemini disabled; production port 8000 untouched; PR #35 unmerged.
- Continuation: Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`, update both handovers after every prompt. Dev radar module passed 80 tests in 53.200s. Run full suite in container including Gemini tests, no scans/API calls, then review CI. Keep LinkedIn disabled, notifications off, Gemini disabled, production untouched, PR #35 unmerged.


## 2026-10-12 — Release diff blocked by missing local base ref
- User reports dev checkout status clean and aligned: `## v2-live-radar...origin/v2-live-radar`; HEAD `54fc75c` (`docs: record source status CI success`). Recent log shows documentation commits only in the last five entries.
- `git diff origin/main...HEAD -- v2/radar.py v2/test_radar.py` failed with `fatal: bad revision 'origin/main...HEAD'`. This indicates the local clone cannot resolve `origin/main`; it does not prove anything about the parser patch itself.
- Next: run read-only `git remote -v`, `git branch -a`, `git show --stat --oneline HEAD`, and `git log --oneline --all -- v2/radar.py v2/test_radar.py | head -20`. Then fetch the intended remote main ref if appropriate and compare the exact parser/test diff. Do not merge/deploy until reviewed.
- Test evidence: user reported full dev-container suite passed, 88 tests in 53.229s. This is not production validation. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.
- Continuation: Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`, update both handovers after every prompt. Current release review is blocked because `origin/main` is not resolvable in the dev clone. Collect the read-only remote/branch/history output, then fetch/compare safely and review parser/test changes. No production promotion yet.


## 2026-10-12 — Base branch identified; release scope is broad
- User's read-only diagnostics show only `origin` remote URL configured and only `v2-live-radar` plus `origin/v2-live-radar` refs locally. HEAD is `54fc75c`, a docs-only commit. File history confirms LinkedIn experience parser/test commits exist in branch history: `6ac58a1 Fix LinkedIn labeled experience extraction before alert decisions` and `22496f9 Add regression tests for LinkedIn labeled experience metadata`.
- GitHub compare API for `main...v2-live-radar`: status `diverged`, branch is 87 commits ahead and 4 behind; merge base `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`, main SHA `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`. Changed files include README, dashboard, three docs, dev config/compose, Gemini shadow extractor/tests, `v2/radar.py` (139 additions/4 deletions) and `v2/test_radar.py` (157 additions). Therefore do not promote the full branch as one unreviewed change.
- Main versions of `v2/radar.py` and `v2/test_radar.py` do not contain the new `extract_linkedin_labeled_experience` helper / named regression test. Branch does contain them. Workflow lookup for abbreviated parser commit `6ac58a1` returned no PR-triggered workflow runs; CI for the exact parser code commit is not yet verified.
- Next safe step on VM: `git fetch origin main` (updates remote-tracking ref only), then inspect `git diff origin/main...HEAD -- v2/radar.py v2/test_radar.py` and full changed-file list. Keep scope focused; don't merge the entire divergent branch or deploy. Full dev container test suite reported green (88 tests). Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.
- Continuation: Read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handovers after every prompt. The parser fix exists on dev but is absent from main; branch is 87 ahead/4 behind and contains unrelated Gemini/UI/docs work. Fetch main ref safely, review the exact parser/test diff and CI before release. No production promotion.


### Parser diff review follow-up — 2026-10-12
- User ran `git fetch origin main`; it fetched main into `FETCH_HEAD` but did not create `refs/remotes/origin/main`, so `git diff origin/main...HEAD` failed with `fatal: bad revision 'origin/main...HEAD'`.
- Safe correction requested: `git fetch origin main:refs/remotes/origin/main`, verify `git show -s --oneline origin/main` and `HEAD`, then rerun the scoped diff for `v2/radar.py` and `v2/test_radar.py`. No app files changed, no deployment/rebuild, production untouched.
- Await the actual diff before judging or promoting the LinkedIn experience parser fix. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, and PR #35 unmerged.
- Continuation: read both handovers and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar` at the start of the next turn; update both handovers after every user prompt. Review the fetched parser/test diff and confirm relevant CI before any release plan.


### LinkedIn parser diff reviewed — 2026-10-12
- User successfully created `origin/main` locally with `git fetch origin main:refs/remotes/origin/main`; refs: `origin/main=a1db74f`, dev HEAD `54fc75c`. Scoped diff reports `v2/radar.py` +143/-4 and `v2/test_radar.py` +157 lines vs merge-base/main.
- Reviewed parser helper `extract_linkedin_labeled_experience`: parses explicitly labeled numeric ranges, plus values, and single values. Detail enrichment reads full LinkedIn page text for this label and prefixes the selected JD text when needed. Regression test fixture has `Experience: 4.00-6.00 Years` outside description and asserts extracted 4–6 years plus rejection against candidate max 2 years. Also a test checks generic experience snippet does not skip JD enrichment.
- Important scope issue: `v2/radar.py` diff also imports `v2.gemini_extractor`, so this is not a parser-only change. Do not cherry-pick/merge the whole radar/test files or promote the divergent branch. The pasted terminal diff stopped before the rest of the hunk/test diff, but GitHub source inspection confirms the helper and regression fixture. Need isolate the minimum parser-only change from Gemini shadow wiring and run targeted/full tests + CI for that isolated patch.
- Current state unchanged: no deployment, no merge, production untouched. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.
- Next step: inspect the remaining diff for non-parser hunks and CI status, then prepare a narrowly scoped parser-only patch against current `main` (prefer separate clean worktree/branch or explicit patch); run the regression and full dev container suite before any reviewed release.


### Parser patch isolation identified — 2026-10-12
- Full user-provided diff confirms the parser fix is already isolated in two dedicated commits: `22496f9714a7628d4c93929005a2d10773a753cc` adds only `v2/test_radar.py` regression tests; `6ac58a1d4757c3c545203b84a61f4f8058d4747b` changes only `v2/radar.py` for labeled LinkedIn experience extraction. Commit diffs verified via GitHub; unlike aggregate branch diff, neither commit contains Gemini or source-status changes.
- Aggregate diff also includes Gemini shadow extraction/wiring/API and persisted source-health changes, which must not be included in the parser-only release. Main SHA observed by user: `a1db74f`; dev HEAD `54fc75c`. No production changes.
- Recommended isolation path: create a fresh local branch from `origin/main` in a separate worktree or after ensuring the existing dev checkout has no uncommitted changes, cherry-pick the two exact parser commits, inspect the resulting diff, and test before pushing/opening a parser-only PR. Suggested order: test commit `22496f9`, then implementation `6ac58a1`; stop if cherry-pick conflicts rather than resolving blindly. Do not cherry-pick source-status or Gemini commits. Confirm CI for the resulting isolated branch; existing 88-test result was on the aggregate dev branch and is not a substitute for isolated-branch CI.
- Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged. Do not merge or deploy until isolated diff and tests are green.


### Parser worktree cherry-pick paused on Git identity — 2026-10-12
- User created clean worktree `/home/ubuntu/job-beeper-parser-fix` from `origin/main` at `a1db74f`, branch `fix/linkedin-experience-parser`. Original dev checkout `/home/ubuntu/job-beeper-dev` reported clean before worktree creation.
- First cherry-pick (`22496f9714a7628d4c93929005a2d10773a753cc`, tests-only) applied changes but could not create commit because Git committer identity is unset. Second cherry-pick attempt was rejected because the first pick's changes remain in worktree/index. This is not yet a code conflict; likely paused cherry-pick state.
- Recovery: in parser worktree, set repo-local Git identity to the user's intended commit name/email (do not use `--global` and do not invent their email), inspect `git status`, then if the first pick is still in progress and its intended changes are staged, run `git cherry-pick --continue` (do not rerun first cherry-pick). After it succeeds, cherry-pick implementation commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`. Stop and share output if status indicates conflicts or unexpected changes.
- No push, CI, deployment, or production changes. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Git identity check follow-up — 2026-10-12
- User checked `git config user.name` and `git config user.email` in `/home/ubuntu/job-beeper-parser-fix`; both returned blank, confirming repo-local identity is unset. No `git status`/cherry-pick state output provided yet.
- Next: check whether `/home/ubuntu/job-beeper-dev` already has a valid repo-local identity (`git -C /home/ubuntu/job-beeper-dev config user.name` and `... user.email`) and inspect parser worktree state (`git status`, `git diff --cached --stat`, `git rev-parse -q --verify CHERRY_PICK_HEAD`). Do not invent identity values, reset changes, or retry cherry-pick. Set parser worktree identity from user's actual configured identity only, then continue pending pick if confirmed safe.


### Parser cherry-pick ready to continue — 2026-10-12
- Confirmed parser worktree is mid-cherry-pick of `22496f9714a7628d4c93929005a2d10773a753cc`; no conflicts remain and only `v2/test_radar.py` is staged (+82 lines). `CHERRY_PICK_HEAD` matches the expected commit. Existing dev worktree also has no configured user.name/user.email.
- Safe next step is set repository-local identity in parser worktree using the user's actual chosen commit name/email, then run `git cherry-pick --continue`. Do not use guessed identity values. After completion, apply implementation commit `6ac58a1d4757c3c545203b84a61f4f8058d4747b`, stopping if any conflict. No push or deployment yet.


### Parser-only branch created successfully — 2026-10-12
- User reports isolated branch `fix/linkedin-experience-parser` now has two commits: `715b94d Add regression tests for LinkedIn labeled experience metadata` and `9b9cbf1 Fix LinkedIn labeled experience extraction before alert decisions`.
- Reported diff versus `origin/main`: only `v2/radar.py` and `v2/test_radar.py`, 149 insertions and 3 deletions. This matches the intended parser-only scope; full diff content has not yet been reviewed in this conversation.
- Next action: inspect full diff (`git diff origin/main...HEAD -- v2/radar.py v2/test_radar.py`) and working-tree status before running tests. Do not push or deploy yet. Then test in an isolated environment/CI for this branch, not by running the live dev container against the wrong checkout. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Parser diff reviewed; isolated test setup next — 2026-10-12
- User supplied the complete `origin/main...HEAD` diff for `fix/linkedin-experience-parser`; `git status --short` was empty. Diff touches only `v2/radar.py` and `v2/test_radar.py` (149 insertions, 3 deletions), with the expected test and implementation commits.
- Code review: implementation explicitly parses labeled LinkedIn metadata before generic JD experience extraction and avoids treating generic search-snippet year mentions as sufficient to skip JD enrichment. Regression tests cover metadata outside description and incidental snippet years. No obvious scope creep in the shown diff. Testing is still required; edge cases/runtimes are not yet verified.
- Next step: inspect the dev container's image/mount/config so tests can run against the parser worktree in a separate, temporary container/environment. Do not use `docker exec -w /app job-radar-dev` as that tests the live dev checkout, not this worktree. No push/PR/deployment yet. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Isolated parser test environment identified — 2026-10-12
- User reports image `job-radar-dev-radar`; the running dev container mounts only its persistent dev data volume at `/data` and `/home/ubuntu/job-beeper-dev/v2/config.dev.json` at `/app/v2/config.json`. Parser worktree `9b9cbf1` is clean (`git status --short` empty).
- Safe test approach: run a disposable container from the same image with `--network none`, mount `/home/ubuntu/job-beeper-parser-fix` at `/app:ro`, and use `--entrypoint sh` so no app server starts. Run the two focused `v2.test_radar.MatcherTests` regression tests first, then full `python -m unittest discover -s v2 -p 'test_*.py'` only if focused tests pass. Do not mount production/dev data or config; do not execute tests inside `job-radar-dev` because that uses the other checkout. If tests require writable paths, add only temporary container-local/tmpfs paths after examining failure output.
- No push/PR/deployment yet. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Parser regression tests passed; full suite next — 2026-10-12
- User ran both focused regression tests against `/home/ubuntu/job-beeper-parser-fix` in disposable container `job-radar-dev-radar`, with `--network none` and source mounted read-only. Result: `Ran 2 tests in 0.149s`, `OK`; one expected mocked LinkedIn discovery log, no live network.
- Next run full suite in same isolated mode: `sudo docker run --rm --network none --entrypoint sh -v /home/ubuntu/job-beeper-parser-fix:/app:ro -w /app job-radar-dev-radar -lc 'python -m unittest discover -s v2 -p "test_*.py"'`. Capture complete output. If suite passes, inspect test summary and then push branch/open narrow PR for CI/review; no deployment or merge without review. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### Full isolated parser suite passed — 2026-10-12
- User ran the full test suite in the disposable no-network container against `/home/ubuntu/job-beeper-parser-fix` mounted read-only. Result: `Ran 78 tests in 53.319s`, `OK`.
- Focused regression tests also passed earlier (`Ran 2 tests in 0.149s`, `OK`). Isolated patch is two commits and only `v2/radar.py` + `v2/test_radar.py` changed (149 insertions, 3 deletions); clean working tree reported before testing.
- Next: push only `fix/linkedin-experience-parser` and open a narrow PR targeting `main`, then confirm its CI. Do not merge/deploy without review/approval. Keep LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched, PR #35 unmerged.


### PR #35 status rechecked — 2026-10-12
- User shared https://github.com/AvinashBhalla/job-beeper/pull/35. GitHub confirms PR #35 remains open, draft, unmerged; base `main`, head `v2-live-radar` at `c194ef18da03a8472d8af796f813cc6ce5a5b333`; 11 files, 111 commits, broad development integration diff. No submitted reviews or conversation comments were returned.
- Diagnosis: PR #35 is the existing broad Gemini shadow-mode/integration draft and is not a safe vehicle for the narrow LinkedIn experience parser fix. Do not merge PR #35 to ship that fix.
- Latest isolated parser evidence remains: `fix/linkedin-experience-parser`, two commits based on production `main` `a1db74f`, only `v2/radar.py` and `v2/test_radar.py` changed (149 insertions, 3 deletions); focused tests 2/2 and full suite 78/78 passed in a no-network disposable container. The branch has not yet been confirmed pushed and has no dedicated PR/CI result.
- Production impact: none confirmed; no merge/deployment was performed. Keep LinkedIn disabled in dev, notifications off, Gemini shadow disabled, and production port 8000 untouched.
- Next action: user should run the previously supplied push checklist in `/home/ubuntu/job-beeper-parser-fix`: `git status --short`, `git fetch origin main`, `git diff --stat origin/main...HEAD`, `git push -u origin fix/linkedin-experience-parser`. Confirm clean worktree and narrow diff before push; then open a PR targeting `main` and inspect CI. No merge/deploy until review and explicit approval.


### LinkedIn parser fix PR opened — 2026-10-12
- User pushed `fix/linkedin-experience-parser` successfully. Remote branch tracks origin; diff versus `main` is limited to `v2/radar.py` and `v2/test_radar.py`, 149 insertions and 3 deletions; two commits ahead, zero behind, based on `main` SHA `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`.
- Opened dedicated PR #36: https://github.com/AvinashBhalla/job-beeper/pull/36 — title `Fix LinkedIn labeled experience extraction`, base `main`, head `fix/linkedin-experience-parser`, not draft, open and unmerged. GitHub reports mergeable; V2 CI was in progress at last check.
- Validation before push: targeted regression tests 2/2 passed and full isolated no-network suite 78/78 passed. CI still needs to finish; do not treat it as passed yet.
- No production deployment or live LinkedIn scan. Keep dev LinkedIn disabled, notifications off, Gemini disabled, production port 8000 untouched. PR #35 remains a separate broad draft and must not be used to ship this fix.
- Next: inspect PR #36 checks until V2 CI completes; if green, review the exact two-file diff and arrange review/approval before any merge. If CI fails, inspect logs and fix only on `fix/linkedin-experience-parser`, then rerun tests. Do not merge/deploy yet.


### PR #36 CI failure — investigation required — 2026-10-12
- GitHub Actions run #543 for PR #36 (`V2 CI`, run ID `38273658480`) completed with failure. Syntax/compile and dependency install passed; full unittest step failed: 78 tests, 5 failures.
- Failures: `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_linkedin_fast_scan_uses_broader_recency_window`, `test_linkedin_skips_deep_scan_after_fast_lane_rate_limit`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`. New structured-experience regression test passed. Need establish whether these failures are baseline/environmental or caused by patch before changing code.
- CI logs show the fast-scan tests made zero mocked calls and the enrichment test retained its original description. Do not dismiss as flaky without a baseline run and test-isolation review.
- PR #36 remains open/unmerged. No production deployment/live LinkedIn scan. Keep LinkedIn disabled in dev, notifications off, Gemini disabled, production port 8000 untouched; PR #35 remains separate and unmerged.
- Next: compare CI results on `main` baseline and inspect affected tests/LinkedIn cooldown global state; reproduce exact full-suite command on the isolated worktree. Make the smallest evidence-backed fix on `fix/linkedin-experience-parser`, rerun focused and full tests, then push and verify CI. Do not merge/deploy.


### Baseline test comparison — 2026-10-12
- User confirmed `origin/main:v2/test_radar.py` contains at least three of the CI-failing tests: `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_new_linkedin_job_is_enriched_from_jd_before_matching`, and `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`. This only confirms test definitions exist on baseline; it does not show whether baseline CI passes or fails.
- Parser worktree remains at `9b9cbf1` on `fix/linkedin-experience-parser`; output showed two commits and no visible dirty-status lines. CI run #543 still failed 5 tests (four LinkedIn scan/cooldown tests and one JD-enrichment test). Need execute full suite against `origin/main` to separate baseline failures from patch regressions.
- Next action for user: create a separate baseline worktree at `/tmp/job-beeper-main-baseline` from `origin/main`, run the full unittest suite inside the same `job-radar-dev-radar` image with `--network none`, then share the summary/failures. Do not alter or reset the parser branch, and do not merge/deploy. If baseline fails the same tests, investigate shared test environment/global state; if baseline passes, inspect patch/test interaction.


### Parser PR focused-test invocation — 2026-10-12
- Confirmed the separate baseline run on `origin/main` passed: 76 tests, `OK`. PR #36 CI on the parser branch still reports 5 failures (four LinkedIn scan/cooldown tests and `test_new_linkedin_job_is_enriched_from_jd_before_matching`); do not merge or deploy until isolated and fixed.
- First focused-test invocation from `/app` failed to import `test_radar`; second invocation from `/app/v2` found `test_radar.py` but failed because its `import v2.radar` requires repository root on `sys.path`. Neither invocation executed tests.
- Correct focused invocation: mount the isolated parser worktree read-only at `/app`, set container workdir to `/app`, and use fully qualified test names `v2.test_radar.MatcherTests...` in the existing `job-radar-dev-radar` image with `--network none`. Await output before making a code change.
- Production remains untouched (port 8000); dev LinkedIn and notifications remain disabled. PR #36 remains unmerged.
- Next action: run the corrected focused command, inspect the actual test results, then make only evidence-backed changes and rerun focused plus full suites. Keep both handover docs synchronized after each prompt.


### Parser PR focused tests passed — 2026-10-12
- User ran the corrected isolated command from repository root `/app`, with the parser-fix worktree mounted read-only and container networking disabled. Output: `Ran 3 tests in 32.100s — OK`. The three focused tests passed: `test_linkedin_fast_lane_and_periodic_deep_scan`, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`.
- This is useful evidence but does not explain the five failures seen in PR #36 CI's full suite. The scan/cooldown failures may be order-dependent shared state triggered by another test; investigate with deterministic test ordering and isolation before editing. The JD-enrichment failure passed in isolation, so check full-suite interaction/state before changing parser logic.
- Next task: run the complete suite on `fix/linkedin-experience-parser` in the same isolated, no-network container, capture all five failure tracebacks and ordering, then run the implicated tests individually and in combinations to identify shared state. Compare with the already-confirmed `origin/main` baseline (76 tests, OK). Make a minimal evidence-backed fix, rerun focused tests and the full suite, and verify PR #36 CI. Do not merge or deploy while CI is red.
- Keep production port 8000 untouched; dev LinkedIn and notifications remain disabled. PR #36 remains open/unmerged. Correct Python import invocation: workdir `/app`, test names prefixed with `v2.` because tests import `v2.radar`.


### Parser PR focused tests passed; next isolate full-suite CI failures — 2026-10-12
- User ran the corrected focused command in a disposable container with the parser worktree mounted read-only at `/app`, network disabled, workdir `/app`, and test names prefixed with `v2.test_radar`. Result: `Ran 3 tests in 32.100s — OK`. Passing tests: `test_linkedin_fast_lane_and_periodic_deep_scan`, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`.
- This validates the three targeted cases in isolation but does not clear PR #36: GitHub CI run #543 / run ID `38273658480` still reports five full-suite failures. The `origin/main` baseline passed 76 tests, so investigate patch/test interaction and order-dependent shared state.
- Next task: run the full suite on `fix/linkedin-experience-parser` using the same read-only, `--network none` container; capture all failure tracebacks and test order. Then run the implicated tests individually and in combinations to isolate the four scan/cooldown failures and JD-enrichment failure. Do not edit production code until a reproducible cause is identified. Apply the smallest fix, run focused and full suites, and verify PR #36 CI.
- Correct invocation pattern: container workdir `/app`; tests named `v2.test_radar.MatcherTests...` because `test_radar.py` imports `v2.radar`. Do not run from `/app/v2`.
- PR #36 remains open/unmerged; no deployment. Production port 8000 is untouched; dev LinkedIn and notifications remain disabled. Keep PR #35 (Gemini shadow mode) separate and unmerged.

### PR #36 full-suite CI failure diagnosis — 2026-10-12 (evidence from run #543)
- Fetched PR #36 metadata and diff directly from GitHub. PR is open/unmerged, base `main` at `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`, head `9b9cbf1195f57a34f5539b31a06c3ce476bcdcc7`; only `v2/radar.py` and `v2/test_radar.py` changed (149 insertions, 3 deletions). No production deployment occurred.
- Latest confirmed Actions run #543 (ID `38273658480`) checked synthetic merge commit `fcc5141730e118958c3806185956016e0fed02c6`. Install and `py_compile` passed; full suite ran 78 tests and failed 5.
- CI log explicitly reports 299 seconds of remaining LinkedIn rate-limit cooldown immediately before these tests: `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_linkedin_fast_scan_uses_broader_recency_window`, and `test_linkedin_skips_deep_scan_after_fast_lane_rate_limit`. Their scan calls were skipped; downstream assertions failed (0 calls or empty params). This is direct evidence that a module-level cooldown value leaked into test execution, rather than proof of a parser regression. Baseline main passed 76 tests and parser focused tests passed, so hypothesis is strong but root setter/test order still needs reproduction.
- CI's `test_new_linkedin_job_is_enriched_from_jd_before_matching` also failed because the job description remained unchanged (missing `JD:`). In `v2/radar.py`, detail fetch calls `_linkedin_http_get`, whereas this older test patches `radar.requests.get`; inspect `_linkedin_http_get` and test setup to determine whether the patch seam changed in a way that fails only under suite ordering. Do not alter the assertion or broadly refactor until verified.
- Important current evidence still missing: full isolated suite result on `/home/ubuntu/job-beeper-parser-fix` using the requested root-relative command, plus individual/combined reproduction of each failure. Connector access cannot run shell commands on the VM; user must execute that exact isolated Docker command and share full output for empirical confirmation.
- Safety: tests in CI ran hosted Python 3.12; disposable local tests must continue to use `--network none`, parser source mounted read-only at `/app:ro`, workdir `/app`; never use live runtime container or persistent data. Keep production port 8000 untouched, dev LinkedIn disabled, notifications off, Gemini off, PR #35 separate/unmerged.
- Next exact action: run `sudo docker run --rm --network none --entrypoint sh -v "$PWD:/app:ro" -w /app job-radar-dev-radar -lc 'python -m unittest discover -s v2 -t . -p "test_*.py" -v'` from `/home/ubuntu/job-beeper-parser-fix`, share complete output, then isolate test order/state. No application-code change in this turn; CI cause not yet proven/fixed.

### Full-suite isolated reproduction received — 2026-10-12
- User ran the prescribed command from `/home/ubuntu/job-beeper-parser-fix` in Docker with `--network none`, `/app:ro`, and `-w /app`. Exact output: `Ran 78 tests in 53.229s — OK`.
- All five tests previously failing in Actions run #543 pass in this full-suite run, including the four LinkedIn scan/cooldown tests and `test_new_linkedin_job_is_enriched_from_jd_before_matching`. The rate-limit tests run later in the test order (e.g. 429 cooldown tests at output lines 68–82); observed suite order does not leave cooldown state that breaks later tests. This rules against the earlier generalized “cooldown leak causes these four tests” hypothesis for this current isolated run, but it does not explain CI's red run. Environment/runtime differences or intermittent test/order behavior remain to be tested, not assumed.
- No source changes made. PR #36 remains open/unmerged at head `9b9cbf1195f57a34f5539b31a06c3ce476bcdcc7`; run #543 remains failed for that commit. Local green does not supersede CI.
- Next: rerun all five failed tests individually and in relevant combinations, ideally multiple suite repetitions in the same disposable isolated container; capture exact Python/runtime version and dependency versions vs CI workflow. Inspect workflow and CI test logs to understand the ordering/environment difference. Avoid changing code until a failure reproduces. Then push only a justified fix and wait for a new green CI run before recommending merge. Production and dev safety constraints unchanged.

### Next test command clarified — 2026-10-12
- The prior local isolated run passed all 78 tests (`Ran 78 tests in 53.229s — OK`), but CI run #543 remains red. For a clean full-suite rerun from `/home/ubuntu/job-beeper-parser-fix`, use the network-disabled, read-only Docker command documented above. Do not treat grep-filtered full-suite discovery as an individual-test run: it still executes the full discovered suite.
- For individual reproduction, use `unittest` discovery to load the suite and filter to one exact `test._testMethodName`, then execute that selected case in a fresh Python process per test. This avoids falsely labeling a full-suite grep as an isolated test. No application changes until the discrepancy reproduces; PR #36 stays open/unmerged.

### Individual-test diagnostic clarification — 2026-10-12
- User ran a loop whose body invoked `python -m unittest discover -s v2 -t . -p "test_*.py" -v` five times and piped output through `grep`. That executed the full 78-test suite five times; `grep` filtered display only, so this is not isolated per-test evidence. All five repetitions passed (about 53 seconds each), confirming suite stability in that run but not the CI discrepancy.
- Correct isolated command pattern from `/app`: `python -m unittest v2.test_radar.MatcherTests.<exact_test_method> -v`, once per test, using the same network-disabled Docker container and read-only source mount. PR #36 stays open/unmerged; no application changes or deployment.

### CI-versus-local import mode investigation — 2026-10-12
- User ran true isolated method invocations for all five CI-failing tests via `python -m unittest v2.test_radar.MatcherTests.<method> -v`; all five passed individually. The full suite also passed 78/78 repeatedly when invoked with `discover -s v2 -t .`.
- Direct Actions run #543 logs confirm GitHub Actions used Python 3.12.15 on Ubuntu 24.04 and invoked `python -m unittest discover -s v2 -p 'test_*.py' -v` (no `-t .`), yielding 5 failures in 20.472s. Local test invocations used package-qualified `v2.test_radar`; CI's discovery imports `test_radar`. The test module imports `v2.radar as radar`, so module/test import and discovery mode is now a concrete difference to test, not yet proven root cause.
- Next exact diagnostic: reproduce the CI command verbatim in the same isolated container from `/app`, omitting `-t .`: `python -m unittest discover -s v2 -p 'test_*.py' -v`. Keep `--network none` and `/app:ro`. If it fails, preserve the full output and inspect test import/state cleanup; if it passes, compare CI's fresh dependency install/Python 3.12.15 against the local image's versions. No code changes or deployment; PR #36 remains open/unmerged.
