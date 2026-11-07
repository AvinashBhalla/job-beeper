# Job Radar V2 — Agent Handover & Product Source of Truth

> **Purpose:** This document is the durable handover for Job Radar V2.
> A future agent should read this file before making architectural or product changes.
> Do not depend on chat history being available.

**Last updated: 2026-11-07 (resume parser/API and onboarding upload UI implemented; 237 tests green; no deployment)**
**Release integration branch:** `v2-live-radar`

**Active feature branch:** `feat/user-preferences-evaluations-20261106`
**Repository:** `AvinashBhalla/job-beeper`

> ## Mandatory agent handover rule — every prompt
> **Every user prompt must end with an update to this handover and the linked `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, before the agent considers the turn/session complete.** This applies even when a prompt only changes the plan or adds an observation; record “no code change” explicitly when applicable. After any code/config change, update both documents in the same PR where practical, or immediately afterward if runtime evidence arrives later.
>
> Each update must connect the work to the overarching goal (reliable, fresh, multi-source job discovery → normalization/deduplication → one consistent preference/match decision → explainable dashboard and Telegram delivery), and record: evidence received; diagnosis and confidence; code/config/docs paths; PR/commit and CI results; whether deployed (with actual runtime proof, not assumption); what changed and deliberately did not change; remaining risks; the exact next action; copyable commands/output expected from the user; and a continuation prompt for the next chat. Cross-link the detailed chronological handover, the compact knowledge transfer, and `docs/JOBBEEPER_REFERENCE.md` where relevant. **The latest dated handoff supersedes older instructions/checklists**; label superseded entries historical rather than leaving conflicting “next task” instructions active. Never expose secrets. One issue at a time, evidence first, verify after deploy.
>
> ## Historical handoff — 2026-10-16 (superseded by the 2026-10-28 multi-provider router review appended below)
- **Goal:** verify the isolated-dev Gemini experience path from fresh extraction through trusted cache, matcher bridge, persisted evaluation, and notification policy. Overarching product goal remains reliable multi-source job discovery, normalization/deduplication, consistent explainable matching, and low-noise delivery.
- **Live evidence from the user's redacted diagnostic:** `diagnostic_status=candidate_verified`; configured model `gemini-3.5-flash-lite`; exact current-input hash matched; successful cache row matched model and was 538 seconds old (30-day success TTL); the job was last seen 606 seconds earlier and within the 24-hour candidate window. Trusted result: required `total_professional`, 3–5 years, confidence 0.95, verifiable evidence and at least one range bound.
- **Isolated bridge/persistence proof:** a temporary DB copy passed through real `_job_for_canonical` with `jd_experience_source=gemini_verified`; real `_persist_job_evaluation` wrote 3–5 years, matching the cache. Diagnostic guarantees shown in user output: source DB read-only, source DB unmodified, zero Gemini API calls, and zero notifications.
- **Activation and health (2026-10-15):** first `curl /health` returned connection reset and SSH disconnected after Compose reported `Started`, but follow-up read-only inspection resolved this: container running, `restart_count=0`, `exit_code=0`, `oom_killed=false`, not restarting, no container error; existing `job-radar-dev_radar-dev-data:/data` mount intact. A bounded health retry returned `status=ok`, version `2.0.0`, one source and no source errors. Effective `matcher=true`, `extraction=true`; Telegram token/chat absent; notifications and LinkedIn false. The redacted diagnostic then confirmed live evaluation bounds/reasons match the trusted cache as detailed below. Treat the connection reset as transient, not an unresolved crash.
- **Live persisted evaluation now matches:** diagnostic `candidate_verified`, exact current input hash matched, successful cache for configured model `gemini-3.5-flash-lite`, cache age 3008 seconds within 30-day TTL, job last-seen age 616 seconds within 24 hours. Trusted result is `required` + `total_professional`, 3.0–5.0 years, confidence 0.95, verifiable verbatim evidence present, range bound present. Live `job_evaluations` row is present with min 3.0/max 5.0, `live_evaluation_bounds_match_cache=true`, one match reason and `live_evaluation_experience_reason_present=true`. The temporary bridge/persistence check also passed with source `gemini_verified`, aligned bounds and an experience reason. Source DB was read-only/unmodified for the diagnostic, with zero Gemini API calls and no notifications. `job_evaluations` still does not persist `jd_experience_source`.
- **Schema/reason caveats:** `job_evaluations` does not contain `jd_experience_source`; only the transient bridge object exposes `gemini_verified`. The sandbox evaluation's regular match reasons include an experience reason. `sandbox_alertability_experience_reason_present=False` is not itself a failure: the current alertability policy returns notification-disabled/not-profile-match reasons, and experience reasons are stored in the separate match-reasons list. Notifications remain disabled.
- **Code/tests:** `v2/gemini_experience_diagnostic.py` and `v2/test_gemini_experience_diagnostic.py`; user previously reported 4 diagnostic tests passing in 0.336s, plus 14 extractor and 88 Radar tests passing. The latest live diagnostic itself made zero Gemini API calls and performed no live DB write; it read source SQLite read-only. No source-code/schema change or full test run occurred in this turn. CI has not been independently verified for this diagnostic.
- **Safety/current runtime:** verified current dev flags are extraction=true and matcher=true; Telegram token/chat absent; notifications disabled and LinkedIn disabled. Dev health returned OK after bounded retries. Production was not touched. Gemini API usage limits remain 3 calls/source run and 20/day; the diagnostic itself made no network calls. Preserve VM-local `M v2/config.json` and untracked `.venv/`; never stage, overwrite, reset, or clean them.
- **Standing autonomy instruction (user directive, 2026-10-15):** proceed with routine, reversible work inside the established Job Radar V2 scope without step-by-step confirmation, including code/docs/tests and isolated-dev configuration/restarts required for this validated Gemini matcher task. User has explicitly approved enabling `GEMINI_MATCHER_ENABLED=true` in isolated dev. Do not repeatedly ask permission for these scoped steps. Hard boundaries remain: keep production matcher/deployment unchanged, never send/replay notifications, never expose or commit secrets, never delete/recreate volumes or reset/clean local files, and do not perform destructive DB/schema or other irreversible/security-sensitive changes without a clearly scoped safe plan. If no tool can reach the VM, say so plainly and provide an exact narrow command rather than claiming completion.
- **Exact next action:** the Gemini experience matcher/cache-to-live-evaluation acceptance criterion is now met in isolated dev. Continue with read-only verification that this evaluation is consistently reflected by canonical opportunity/API/dashboard output while notification dispatch remains disabled. Next perform a safe backend test run after reviewing the exact current checkout (`git status --short`, branch/HEAD; preserve VM-local `M v2/config.json` and `?? .venv/`; pull only with `git pull --ff-only` if behind and don't overwrite either local file). Then review end-to-end canonicalization, persisted notification-ledger decisions under notifications-off policy, and dashboard/API representation. Do not send any Telegram alerts. Afterwards, progress through the existing reference roadmap one scoped issue at a time: Greenhouse stale-board/freshness guard and two-poll one-board canary (GET-only, notifications off), then Ashby → Lever → SmartRecruiters individually, observability improvements, and only then prepare a reviewed promotion PR. Production cutover, production matcher activation, and any real alert send remain separate gates. Keep existing volume, local config and `.venv/`; do not perform destructive operations.
- **Continuation prompt:** “Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`. Dev matcher is true and the earlier transient health reset recovered. Container is running with restart_count=0, not OOM-killed, health status OK, existing /data volume retained, Telegram credentials blank, notifications/LinkedIn disabled. The exact-hash/current-model/TTL Gemini result is required total_professional 3–5 years, confidence 0.95, evidence present; the LIVE persisted evaluation now matches 3–5 years and has an experience match reason. The diagnostic itself made no Gemini calls or notifications. Continue autonomously with API/dashboard/ledger consistency tests and then the reference roadmap one safe phase at a time; don't send alerts or change production. Preserve config/.venv and update both handovers every turn.” 
- **Cross-reference:** `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` is the compact state; `docs/JOBBEEPER_REFERENCE.md` remains the architecture/rollout guardrail.
## Historical handoff — 2026-10-12 (superseded by the 2026-10-14 Gemini matcher follow-up)
- **Goal:** verify Gemini JD experience end-to-end in isolated development: extraction → evidence validation → fresh/model-matched cache → opt-in matcher → persisted evaluation → notification decision.
- **Matcher code:** cached integration is already on this branch in commits `1b667e4`, `c3cc276`, `ce69cec`, `14516a0`, `0b74444`. User previously reported 11 targeted Gemini tests and 88 Radar tests passing; neither suite was rerun this turn.
- **New config wiring:** `v2/docker-compose.dev.yml` passes `GEMINI_MATCHER_ENABLED`, default false, in commit `7ea83e024f2da4923633c23221ea8085a3643a10`. The product reference was synchronized in `6828153f485e5e247e984a2a735f813ff6ef1d84`. No application code, production Compose, or production settings were changed.
- **Latest VM output from user:** branch pulled successfully to `b27de42` and retained `M v2/config.json` and `?? .venv/`. Compose syntax check passed. Docker commands for `ps`, `inspect` and `exec` returned permission denied at `/var/run/docker.sock`; do not use sudo or change Docker permissions. The API endpoint on `127.0.0.1:8001/api/llm-shadow-status` was reachable and reported `enabled=false`, `api_key_configured=false`, model `gemini-3.5-flash-lite`, `calls_today=0`, `cache_successes=14`, `cache_errors=6`. Among ten recent cache samples, a few matched a preliminary structural shape, but this does not verify current JD hash, trusted bridge acceptance, or persisted evaluation. The pasted in-container environment command was malformed and then blocked by Docker permissions; effective env and actual volume mount remain unverified.
- **Storage intent, not actual mount proof:** dev Compose declares `JOB_RADAR_DB=/data/jobs.db`, `radar-dev-data:/data`; expected named volume under project `job-radar-dev` is `job-radar-dev_radar-dev-data`. Never assume it is mounted until Docker metadata can be read. Do not create a database or use checkout-relative SQLite files as a substitute.
- **Exact next action:** pull latest docs, then run the socket/group check and the filtered host-side Compose interpolation check at the bottom of this document. They print no secret values and don't require container exec. Return output. If current account lacks Docker socket access, do not try privileged commands/permission changes; first establish whether a new login would activate an existing group membership or whether the VM administrator must run Docker commands. Do not enable extraction before this is resolved.
- **Credential handling:** the running API says its Gemini key is not configured. If the host-side Compose check also says the key is absent, configure `GEMINI_API_KEY` only in the ignored VM-local `.env` (hidden prompt; do not echo/print/paste it), or through the existing environment injection. A key in `.env` won't change a running container until the service can be safely recreated. Keep extraction and matcher gates false, notifications disabled, and LinkedIn off.
- **Status/deployment:** no tests rerun, CI success not confirmed, no runtime restart/rebuild, no database mutation, no production rollout and no notification replay. Preserve local `v2/config.json` and `.venv/`; never stage, overwrite, reset or delete them.
- **Cross-reference:** detailed history is in this file; compact state is in `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`; architecture constraints are in `docs/JOBBEEPER_REFERENCE.md`.

## Historical handoff — 2026-10-14 (superseded by the exact current-hash cache diagnostic above)
- **Goal:** verify the Gemini JD experience path end-to-end in the isolated dev runtime: extraction → evidence validation → fresh/model-matched cache → opt-in matcher → persisted evaluation → notification decision. Keep this scoped to experience matching; do not widen into collectors or UI.
- **Code state:** commits already present on `v2-live-radar`: `1b667e4`, `c3cc276`, `ce69cec`, `14516a0`, `0b74444`. User previously reported 11 Gemini tests and 88 Radar tests passing. This turn made no application-code change and ran no tests.
- **Configuration fix:** `v2/docker-compose.dev.yml` now forwards `GEMINI_MATCHER_ENABLED` with a default of `false`, commit `7ea83e024f2da4923633c23221ea8085a3643a10`. Previously this rollout gate was absent from the dev container environment map. Extraction still defaults off; Telegram token/chat ID remain forced blank.
- **Runtime evidence remains incomplete:** previous VM checks found extraction/matcher/model vars unset, no key detected by the checked environment, and no SQLite file in the searched checkout. These are not proof of the running container env or data-volume location. Do not state that extraction, fresh-cache use, or persisted Gemini-backed evaluation has been runtime-verified until output is received.
- **Storage/config path:** the dev Compose service declares `JOB_RADAR_DB=/data/jobs.db` and `radar-dev-data:/data`; with project `job-radar-dev`, the expected volume name is `job-radar-dev_radar-dev-data`. Verify the actual container mount before inspecting any database. Never create a replacement database.
- **Exact next action:** run the safe VM checks under the latest chronological entry at the bottom of this file. Confirm effective container flags/key-presence/model, dev health/API status, and the actual `/data` mount. If the API key is absent, ask the user to set it through the local VM-only `.env`/environment mechanism; never request or display its value. Then enable extraction only in dev, keep notifications disabled, and verify a fresh accepted cache result and persisted evaluation before considering the matcher gate in dev.
- **CI/deployment:** no CI result for commit `7ea83e0` has been independently verified here. No dev restart/rebuild or runtime change was performed in this turn. No production checkout, flag, DB, volume, or notification state was changed. Production remains approval-gated; matcher flag must stay off there.
- **Cross-reference:** `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` is the compact current state. `docs/JOBBEEPER_REFERENCE.md` was synchronized in commit `8b71918468e41084f363cc1eb4a5250757e85b74` so it documents the opt-in cached matcher rather than the older shadow-only state.

## Historical handoff — 2026-10-12 (superseded by the 2026-10-14 Gemini matcher follow-up)
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
Use Gemini for job-description extraction; the user will enter the API key directly on the dev VM. Work stays on `v2-live-radar`; do not merge or deploy this feature to production.

### Code changes
- Added `v2/gemini_extractor.py`: bounded Gemini REST integration with strict structured JSON output and local semantic validation for overall experience range/type/evidence, required skills, preferred skills, and confidence.
- Default model is `gemini-3.5-flash-lite` (configurable via `GEMINI_MODEL`). Google’s current pricing page lists a free tier for this model and a 1M-token context window; free-tier content may be used to improve Google products. Confirm current model quota/terms in AI Studio before enabling.
- Wired extraction into `run_source` as shadow-only. Extracted values are stored separately in SQLite table `gemini_shadow_cache`; they do not modify jobs, matching, scores, notification decisions, or Telegram delivery.
- Added `GET /api/llm-shadow-status`, returning enabled/key-configured booleans, model, usage caps, cache summary, and recent structured results. It never returns the key or raw JD.
- Dev Compose accepts `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_EXTRACTION_ENABLED`, `GEMINI_MAX_CALLS_PER_RUN`, and `GEMINI_MAX_CALLS_PER_DAY`. Defaults: disabled, 3 calls per source run, 20 calls/day. Output is capped and cached by source/job/JD hash; errors are briefly cached. API key is passed only through runtime environment, never committed.
- Added `v2/test_gemini_extractor.py` for validation, evidence checks, cache behavior, disabled-by-default behavior, and no mutation of source job data.

### Verification status
- Code/config committed directly to `v2-live-radar`; latest known application patch commit: `5a73bd041bbf5455b1fa9c0a0828ce21a39ecab3` (later doc commits follow).
- The new Gemini test suite and the full 78-test existing suite have **not yet been run on the dev VM**. Do not describe this as verified or production-ready until the dev rebuild, full test suite, API smoke test (with key kept hidden), status endpoint, and production health check pass.
- Production must remain unchanged at port 8000. Dev remains loopback-only at port 8001, with notifications disabled and Naukri as the only enabled source.
- No key, secret, raw JD, or full model request/response should be copied into GitHub, handover docs, logs, or chat. Avoid sending candidate PII; only public job-posting text is in scope.

### Next steps
1. On the VM, fetch `v2-live-radar`, enter the key through a hidden prompt, export the Gemini environment variables, rebuild only `job-radar-dev`, run the full unit suite, and verify `/health`, `/api/config`, `/api/llm-shadow-status`, and port 8000 health. Keep notifications off.
2. Review the first shadow outputs for explicit overall experience vs skill-specific experience, required vs preferred skills, null handling, and confidence. Confirm no matcher/alert output changes.
3. Fix any failures before further work. Keep Gemini shadow-only until accuracy is measured on representative fixtures. Do not promote or merge as part of this VM smoke test.

### Continuation prompt
“Continue Job Radar V2. First read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; update both handover docs after every prompt. Gemini extraction has now been implemented on `v2-live-radar` as a disabled-by-default, separately cached, shadow-only feature. Default model is `gemini-3.5-flash-lite`; runtime env key is `GEMINI_API_KEY`, feature toggle `GEMINI_EXTRACTION_ENABLED=true`, limits 3 calls/run and 20/day. New tests are not yet verified on the dev VM. Next: hidden-input API key, rebuild only dev port 8001, run all tests, check `/api/llm-shadow-status`, keep notifications off, and confirm production port 8000 remains healthy. Do not merge or deploy. Never log or commit secrets.”


### Follow-up hardening — 2026-10-12
- Added explicit `experience_scope` (`total_professional`, `skill_specific`, `unknown`) to the structured result so skill-specific years cannot be silently treated as total experience.
- Corrected nullable Gemini schema fields and broadened detection of skill-specific experience wording.
- Wrapped the shadow pass fail-open so cache/LLM errors cannot block normal source ingestion.
- Default model is `gemini-3.5-flash-lite`, selected for structured extraction and free-tier availability listed on Google’s current pricing page. Free-tier data-use terms and model quotas still apply; verify the selected project/model in AI Studio before enabling.
- Draft validation PR: https://github.com/AvinashBhalla/job-beeper/pull/35. It is not merged and must not be merged until dev VM tests and shadow review pass. The GitHub connector reported no status checks/workflow runs for the latest head at the time of this update; this is not evidence of passing CI.
- Latest app-code commit at this point: `cd3a8a694e08b451d738d6fbc789b86c323c4f5b`. New and existing tests have not yet been executed on the VM.



## 2026-10-12 — Dev VM feedback: test syntax fixed; rerun required

### User-reported evidence
- The Gemini API smoke test succeeded with the synthetic posting and returned 4–6 years, required Python/FastAPI, preferred Kubernetes, and `total_professional` scope.
- Dev health was OK; Naukri was the only enabled source. Dev config confirmed `notifications_enabled=false`; production port 8000 remained healthy.
- `/api/llm-shadow-status` showed Gemini enabled/configured, 3 calls today, 3 successful cached results, 0 errors. Recent Naukri results included several role/domain experience ranges incorrectly or ambiguously labeled `skill_specific`; treat this as an extraction-quality issue, not a matcher input, because mode remains shadow-only.

### Fixes made on `v2-live-radar`
- Fixed malformed dictionary/list brackets in `v2/test_gemini_extractor.py` that caused a SyntaxError during unittest discovery. Fix commit: `7941a99129614ffb03a7406e8fd002e1535fb05d`.
- Tightened the prompt in `v2/gemini_extractor.py`: `total_professional` requires explicit overall/total/professional/work wording; named technology experience is `skill_specific`; role/domain-only phrases such as “Java Full Stack Development experience” should be `unknown` unless scope is explicit. Prompt change commit: `def76ed2fe1f181b8501f25c09098161ef669b87`.
- The previously reported full test run is **failed**, not passed: 79 tests discovered, with one import-time SyntaxError. No new full test run has yet confirmed the fix.

### Immediate next steps
1. Fetch latest `origin/v2-live-radar` on `/home/ubuntu/job-beeper-dev`.
2. Rebuild only `job-radar-dev`, rerun the full unittest discovery. Do not continue if any tests fail.
3. Recheck dev health/config, `/api/llm-shadow-status`, and production port 8000. Keep notifications disabled.
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


## Exact CI command passes locally; environment comparison next — 2026-10-12
- User ran the exact GitHub Actions unittest discovery command inside the disposable container against `fix/linkedin-experience-parser`: `python -m unittest discover -s v2 -p "test_*.py" -v` (without `-t .`), from `/app`, source mounted read-only and container network disabled.
- Result: `Ran 78 tests in 53.319s — OK`. All five tests previously failing in CI run #543 passed in this exact-command local run. The output shows the four LinkedIn scan tests and JD enrichment test passing; cooldown/rate-limit tests also pass.
- This disproves the simple hypothesis that omitting `-t .` alone reproduces the CI failure. Import/discovery mode differs from the earlier local command, but the exact CI command still passes in the available container. Root cause remains unresolved; do not label CI flaky or change application code without evidence.
- CI environment previously confirmed as Ubuntu 24.04.5 / CPython 3.12.15 with fresh installs from `v2/requirements.txt`; local container's Python and installed dependency versions have not yet been compared. Likely next diagnostic: report `python --version`, `python -m pip freeze`, OS release, and the exact dependency constraints from `v2/requirements.txt` inside the same test container, then compare against CI log/install output. If practical, reproduce CI's Python 3.12.15 and fresh dependency resolution in a disposable container; preserve network-disabled test execution after dependencies are available.
- No code change, push, merge, or deployment in this turn. PR #36 remains open/unmerged. Production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 remains separate.
- Next user action: run the environment fingerprint command in the latest chat response and paste the output. Then compare with the CI job log and decide whether a dependency/runtime mismatch or order-dependent nondeterminism is supported.


## Runtime/dependency comparison received; inspect earlier cooldown mutation — 2026-10-12
- User supplied the local isolated-container fingerprint: CPython 3.12.15, pip 25.0.1, Debian GNU/Linux 13 (trixie). Installed packages include FastAPI 0.143.0, Starlette 1.7.0, requests 2.34.2, BeautifulSoup 4.15.0, tzdata 2026.5 and the same other versions reported in the prior CI log. Requirements are broad ranges in `v2/requirements.txt`, so they do not pin reproducible dependency versions. CI ran CPython 3.12.15 on Ubuntu 24.04.5; Python and visible dependency versions align, but the OS differs (Debian 13 vs Ubuntu 24.04).
- Re-read Actions run #543 logs. Before the four scan failures, each scan reports `linkedin scan skipped; rate-limit cooldown has 299s remaining`; the JD enrichment test then fails because no `JD:` enrichment was appended. This confirms the failures share a pre-existing cooldown state in the CI process, not five independent assertions. The exact local CI command passes 78/78, so root cause still needs order/state reproduction.
- Important test isolation issue to investigate: tests mutate module-level LinkedIn cooldown state (`linkedin_rate_limited_until_monotonic`, `linkedin_last_rate_limit_monotonic`, `linkedin_rate_limit_streak`, `linkedin_rate_limit_generation`). Some tests save/restore this state, but CI's cooldown is already active before the four scan tests run. Identify the earliest preceding test or import/runtime behavior that activates it; do not merely suppress cooldown checks.
- No source change, push, merge or deployment in this turn. PR #36 remains open/unmerged; production 8000 untouched, dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 separate.
- Next diagnostic: run the exact CI suite repeatedly in fresh disposable processes to check whether the early cooldown state is intermittent, and inspect the CI log from the first occurrence of `HTTP 429`/cooldown activation and the tests immediately preceding it. Prefer a minimal test-order reproduction and explicit cleanup of test-owned global state if proven; do not change production rate-limit behavior without evidence.


## Root cause found: scan test leaked a real LinkedIn 429 — 2026-10-12
- Re-inspected Actions run #543 and source around the failure. The log shows `test_linkedin_fast_lane_and_periodic_deep_scan` completing its mocked search scans, then `linkedin JD enrichment stopped after HTTP 429`, followed by the next fast-lane tests seeing a 299-second global cooldown. The JD-enrichment test also fails because cooldown prevents the detail request.
- Root cause: the pagination test mocks `_linkedin_request` but not `enrich_linkedin_job`. The parser fix correctly no longer trusts a generic search snippet like `2 years experience` as authoritative labeled metadata, so `linkedin_collect` now queues a matching candidate for JD enrichment. In GitHub Actions (network-enabled), the test unexpectedly performs a real LinkedIn detail request and gets HTTP 429; the process-global cooldown then cascades into later tests. The no-network local container did not reproduce the real 429, explaining the green local suite.
- Evidence-based test-only fix committed directly to `fix/linkedin-experience-parser`: `572f56573fa8f66a532ee676c2aa66b25a843d0a` (`test: prevent live LinkedIn enrichment in scan pagination test`). In `v2/test_radar.py`, `test_linkedin_fast_lane_and_periodic_deep_scan` now also mocks `enrich_linkedin_job` to return the job unchanged, keeping a pagination test hermetic and preventing live HTTP/cooldown leakage. The exact replacement was fetched back and verified. Production application code was not changed by this follow-up.
- Validation is pending: local focused/full tests and the new GitHub Actions run have not yet been confirmed green. PR #36 remains open/unmerged; do not merge/deploy until checks pass. No production impact.
- Next user action: in `/home/ubuntu/job-beeper-parser-fix`, fast-forward the local branch to the new commit, run the focused pagination test and the full suite in the same isolated `--network none` container, then inspect PR #36 CI. If CI remains red, use the new exact failure/log sequence rather than assuming this fully resolved all failures.
- Safety unchanged: production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 separate/unmerged.


## Validation received: hermetic test fix passes locally — 2026-10-12
- User fast-forwarded `/home/ubuntu/job-beeper-parser-fix` cleanly to `572f56573fa8f66a532ee676c2aa66b25a843d0a` (`test: prevent live LinkedIn enrichment in scan pagination test`); the shown `git status --short` produced no changes before the pull.
- Focused test passed in the disposable `job-radar-dev-radar` container with `--network none`: `v2.test_radar.MatcherTests.test_linkedin_fast_lane_and_periodic_deep_scan` (1/1).
- Full suite passed in that same network-disabled container: `python -m unittest discover -s v2 -p "test_*.py" -v`, 78/78 in 37.205s. Output confirms the previously affected scan tests and JD enrichment test pass without live LinkedIn requests.
- GitHub Actions run #592 (ID `38284476851`) for this head is completed/success, but the connected job listing exposes only a successful job named `syntax`. Do **not** describe the complete CI test suite as green based on that run alone; local full suite is green, prior run #543 had failed, and CI coverage needs confirmation if a dedicated test job is expected.
- PR #36 is still OPEN and UNMERGED, head `572f56573fa8f66a532ee676c2aa66b25a843d0a`, base `main`. No merge/deploy authorized or performed.
- Next: inspect PR checks/workflow configuration to establish whether the successful `syntax` job is the only configured check or whether the test job did not run. If the test job is absent, verify why before considering merge. Keep production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 remains separate.


## CI fully verified; next step is PR review, not another local run — 2026-10-12
- Follow-up repo check resolved the earlier ambiguity: `.github/workflows/v2-ci.yml` on `fix/linkedin-experience-parser` defines one job named `syntax`, and that job explicitly runs both `python -m py_compile v2/radar.py v2/test_radar.py` and `python -m unittest discover -s v2 -p 'test_*.py' -v`. The job name is misleadingly broad; it is not syntax-only.
- GitHub Actions run #592, ID `38284476851`, completed with conclusion `success`. Job `syntax` step 6 (`python -m unittest discover -s v2 -p 'test_*.py' -v`) is completed/success. Run URL: https://github.com/AvinashBhalla/job-beeper/actions/runs/38284476851. The earlier run #543 failed specifically at this full-suite step before the test isolation fix.
- PR #36 remains OPEN, UNMERGED, mergeable, targeting `main`; head `572f56573fa8f66a532ee676c2aa66b25a843d0a`. The reviewed diff contains only `v2/radar.py` and `v2/test_radar.py` (156 additions, 4 deletions). Local focused test and local full suite both pass; GitHub Actions full suite also passes. No further test command is required now.
- Recommended next step: review the PR diff and repository policy/required approvals, then merge PR #36 only with the user's explicit authorization. Do not deploy production as part of this parser fix unless separately requested. Preserve safety: production port 8000 untouched; dev LinkedIn disabled, notifications off, Gemini shadow disabled; PR #35 remains separate.


## PR #36 final review checkpoint — 2026-10-12
- User asked “what next?”; no code changes requested or made in this turn.
- Rechecked PR #36: https://github.com/AvinashBhalla/job-beeper/pull/36 remains open, not merged, mergeable, base `main`, head `fix/linkedin-experience-parser` at `572f56573fa8f66a532ee676c2aa66b25a843d0a`. Scope remains `v2/radar.py` and `v2/test_radar.py`; 156 additions, 4 deletions.
- Current GitHub review submissions: none returned. Inline review threads: none returned. This means there are no recorded reviews or inline threads in those endpoints; it does not establish that an external approval policy is unnecessary.
- Prior verified validation remains: isolated local suite 78/78 passed and GitHub Actions run #592 passed on the PR head. No merge or deployment performed.
- Recommended next action: inspect the current PR checks/branch protection and request an authorized maintainer review if required. Then, after explicit user authorization and any required approval, merge PR #36 into `main`. Keep deployment separate and preserve production DB/volume/env; do not enable LinkedIn or notifications as part of merge.
- Safety and goal: maintain reliable source discovery and accurate matching while avoiding live LinkedIn requests during tests and protecting production. No code/config/runtime changes in this turn.
- Continuation prompt: “Read the latest dated handoff sections in `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`. Recheck PR #36 status, current required checks and branch protection. Do not merge or deploy without explicit authorization. If approved, merge only PR #36 to main; keep PR #35 separate and production rollout separate.”


## PR #36 merged — 2026-10-12
- User confirmed “merged”; live GitHub verification confirms PR #36 is `closed` and `merged: true`, merged at 2026-10-12T17:45:33Z.
- PR: https://github.com/AvinashBhalla/job-beeper/pull/36
- Merge commit on `main`: `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. PR head: `572f56573fa8f66a532ee676c2aa66b25a843d0a`. Scope: `v2/radar.py` and `v2/test_radar.py`.
- Before merge, isolated local tests passed 78/78 and PR-head GitHub Actions run #592 was green. Check CI on the merge commit before any release action; do not infer it from PR-head CI.
- No production deployment was performed or verified in this turn. Keep production DB/volume/env unchanged, keep dev LinkedIn disabled and notifications off, and do not trigger live LinkedIn scans as a smoke test.
- Next action: verify CI for merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; then inspect clean git state, production/development checkout and Compose/volume identity, take a verified backup, and only then plan a separately authorized controlled deployment.
- Goal remains reliable multi-source discovery and correct matching with isolated tests and production-safe rollout. No runtime/deployment changes in this turn.
- Continuation prompt: “Read the latest dated sections in `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`. PR #36 was merged to main at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. Check merge-commit CI first, then prepare a production-safe deployment checklist. Do not deploy, enable LinkedIn, or enable notifications without explicit authorization and verified backups/volume identity.”


## Merge-commit CI verification and rollout preparation — 2026-10-12
- User asked the assistant to carry out the next step after PR #36 merged.
- Rechecked PR #36 directly: closed and merged; merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; PR head `572f56573fa8f66a532ee676c2aa66b25a843d0a`. PR-head Actions run #592 (`38284476851`) had passed the full suite before merge (78 tests).
- Checked the merge commit through the connected commit-workflow-runs and combined-status endpoints. The workflow-runs wrapper only returns PR-triggered runs and returned no merge-commit run; combined commit status returned an empty status list for both merge commit and PR head. GitHub web access was unavailable in this session. Therefore **merge-commit CI remains unverified**; do not claim it passed or failed.
- No production VM/shell connection is available in this task context, so the current production/development checkout, containers, Compose project, database volume, env, and live health have not been inspected. No backup was taken and no deployment/restart/config change was performed.
- Safety: do not switch production or run live LinkedIn requests as a smoke test. Preserve production DB/volume/env; dev LinkedIn stays disabled; notifications and Gemini shadow stay off; PR #35 remains separate.
- Exact next action: obtain CI run/check evidence for merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` from GitHub Actions; then use a shell session on the Oracle VM to inspect git status, current commit/branch, Compose project/service/container and mounted volume identity, and health endpoints without changing runtime. Only after identity and clean state are verified should a timestamped DB/config backup be taken and validated. Deployment remains a separate explicit decision.
- Continuation prompt: “Read the newest sections of `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`. PR #36 is merged at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. PR-head CI passed, but merge-commit CI is still unverified because available endpoints returned no runs/statuses. First obtain Actions evidence for the merge commit. Then inspect production/development VM state read-only; do not deploy, restart, enable LinkedIn, or enable notifications without verified backup/volume identity and explicit authorization.”


## Read-only production inspection commands — 2026-10-12
- User requested the shell commands needed to continue the post-PR #36 checks. No code change and no production action taken.
- First command block checks hostname, time, user, repository branch/status/HEAD in `/home/ubuntu/job-beeper` and `/home/ubuntu/job-beeper-dev`.
- Second block should inspect running containers, Compose projects/services, container image/health/restart state, and mounts without printing environment variables or secrets. Do not use `docker inspect .Config.Env`, `env`, `printenv`, or `cat .env`.
- Third block should inspect Compose configuration and relevant health endpoints only after confirming the service names/ports from the prior output. Do not run pull/build/up/down/restart, migrations, scans, or notification sends.
- User should paste command output back, redacting IPs/tokens/passwords and any private values. Continue evidence-first. Do not deploy until merge-commit CI, exact production container/volume identity, and validated backup are confirmed; production changes need explicit authorization.
- Continuation prompt: “Review the read-only SSH output for Job Beeper. Identify production vs dev by Compose project, container names, ports, image and mounts. Do not deploy or restart. Check GitHub Actions status for merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; available commit status endpoint returned no entries, so CI is still unverified. Decide the next read-only check and update both handover docs.”


## Oracle VM read-only inspection results — 2026-10-12 17:58 UTC
- User ran the requested inspection commands on host `job-radar` as user `ubuntu`, timestamp `2026-10-12T17:58:43+00:00`, working directory `/home/ubuntu`.
- Production checkout `/home/ubuntu/job-beeper`: branch `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, working tree reported clean, local branch reported `behind 19` relative to `origin/v2-live-radar`.
- Development checkout `/home/ubuntu/job-beeper-dev`: branch `v2-live-radar`, HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`, working tree reported clean, local branch reported `behind 69` relative to `origin/v2-live-radar`.
- Docker commands failed with `permission denied while trying to connect to the Docker API at unix:///var/run/docker.sock`. This establishes a permissions barrier for the current account; it does **not** establish that Docker is stopped or that containers are absent. Container, Compose project, health and mount identity remain unknown.
- Root filesystem is 45 GB total, 7.4 GB used, 38 GB available (17% used). Docker disk usage, volumes and recent events could not be read because of the same Docker socket permission failure.
- No pull/fetch/reset, container change, deployment, restart, backup, scan or database action was performed. Do not sync either checkout yet: first inspect the remote-vs-local commit ranges and identify which remote commits account for the 19/69-behind reports. Never assume the production and dev checkout roles solely from directory names.
- Next safe action: retry Docker inspection using `sudo docker ps --no-trunc --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'`, `sudo docker compose ls`, and read-only `sudo docker inspect` on running container IDs to inspect only name, image, state, health, restart count, Compose labels and mount source/destination. If sudo is unavailable, report the exact error and stop rather than changing permissions/groups. Do not print container environment variables or secrets.
- In parallel, use read-only Git commands in each checkout: `git remote -v`, `git status --porcelain=v1`, `git log --oneline --decorate HEAD..origin/v2-live-radar`, `git log --oneline --decorate origin/v2-live-radar..HEAD`, and `git diff --stat HEAD...origin/v2-live-radar`. These inspect commit divergence without changing refs or files; do not run `git pull`, reset, checkout, or deployment commands.
- Merge-commit CI for PR #36 merge SHA `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` remains unverified; PR-head run #592 passed but must not be treated as proof of merge-commit CI. No production deployment has been performed or verified. Keep production DB/volume/env unchanged, dev LinkedIn disabled, notifications off, Gemini shadow off; PR #35 stays separate.
- Continuation prompt: “Read the latest dated sections of both handover docs. On the Oracle VM, use sudo only for read-only Docker inspection and collect local-vs-remote Git commit ranges in both checkouts; do not fetch/pull/reset/deploy/restart or expose secrets. Confirm merge-commit CI for `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` separately. Update and re-fetch both handover docs after this prompt.”


## Merge-commit CI confirmed; VM admin access is the current blocker — 2026-10-12
- User supplied the full GitHub Actions log for workflow run checking out exact merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`. Evidence in the log: checkout line reports that SHA; dependencies installed successfully; `python -m py_compile v2/radar.py v2/test_radar.py` passed; the exact configured full suite `python -m unittest discover -s v2 -p 'test_*.py' -v` ran 78 tests and ended `OK`. This now verifies CI on the merge commit; replace the earlier “merge-commit CI unverified” status with “verified green, 78/78”.
- Latest SSH output from host `job-radar`: production checkout `/home/ubuntu/job-beeper` is on `v2-live-radar` at `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, reported clean and 19 commits behind cached `origin/v2-live-radar`; dev checkout `/home/ubuntu/job-beeper-dev` is on `v2-live-radar` at `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`, reported clean and 69 behind cached `origin/v2-live-radar`. These are cached-ref comparisons, not proof of current remote divergence. Do not pull or reset either checkout yet.
- Docker API inspection failed with socket permission denied. `sudo -v` prompted for a password that the user does not have, so Docker container/Compose/volume identities remain unknown. Do not change Docker socket permissions, add groups, or alter sudoers as a workaround. Use the VM provider's authorized console/cloud-shell/recovery path or an already-authorized administrative account to restore admin access; otherwise continue GitHub-only work without touching runtime.
- Current status: PR #36 is merged to `main`; merge SHA `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; merge-commit CI green 78/78. No production deployment, container restart, backup, source enablement, or database change has been performed/verified. Root disk had 38 GB free. Production-vs-dev runtime and persistent volume identity are still unverified.
- Product roadmap after the parser fix: (1) regain authorized read-only VM/Docker visibility and identify production/dev Compose projects, ports, health and mounts; (2) inspect local-vs-remote commit ranges with a fresh fetch only when safe/authorized, then plan a reviewed, backed-up production branch/runtime transition as a separate authorized action; (3) in isolated dev, run the already-implemented Greenhouse adapter as a one-board canary with notifications off, verify two polls, stable IDs/deduplication, first_published timestamp behavior, request/error isolation, and useful yield; (4) validate Instahyre schema/freshness/yield before enabling; (5) add Ashby, Lever and SmartRecruiters one at a time; (6) improve per-source observability and monitor low-pressure LinkedIn for 24–72 hours. Do not enable multiple new sources at once. Keep LinkedIn low-volume with stop-on-429/backoff; no proxy/IP rotation or CAPTCHA bypass. Gemini remains shadow-only/off until dev validation; PR #35 remains separate.
- Immediate next action for the user: resolve VM administrative access through the cloud provider's supported console/recovery or authorized administrator. Do not repeat sudo Docker commands until access is fixed. Meanwhile the next development task should be a code-review/acceptance checklist for the existing Greenhouse one-board dev canary—not enabling it or changing production. Do not expose environment variables or tokens.
- Continuation prompt: “Read the newest dated sections of both handover docs. Merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` has confirmed green merge-commit CI (78/78). VM Docker inspection is blocked because ubuntu has no sudo password; do not weaken permissions or guess. Help restore authorized admin access through the cloud provider, then inspect runtime/mount identity read-only. Separately prepare the existing Greenhouse adapter's one-board dev canary acceptance checklist; do not enable it until runtime is verified and do not deploy or change production without explicit authorization.”


## No-sudo read-only diagnostics — 2026-10-12
- User asked to run the VM inspection commands without sudo. The assistant cannot execute commands inside the user's SSH session; provided copyable commands for the user to run.
- Safe no-sudo checks: `hostname`, `whoami`, `id`, `groups`, `ls -l /var/run/docker.sock`, `docker ps --no-trunc --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'`, and `docker compose ls`. Docker may still return permission denied; that is expected given prior evidence and does not show containers are stopped. Do not chmod the socket, add groups, alter sudoers, or otherwise bypass the permission barrier.
- Safe Git-only checks in both `/home/ubuntu/job-beeper` and `/home/ubuntu/job-beeper-dev`: `git status --short --branch`, `git log -1 --oneline --decorate`, `git remote -v`, `git log --oneline HEAD..origin/v2-live-radar`, `git log --oneline origin/v2-live-radar..HEAD`, and `git diff --stat HEAD...origin/v2-live-radar`. These compare against cached refs; they do not refresh remote refs. Do not fetch/pull/reset/checkout/deploy yet.
- No VM command was executed by the assistant, and no runtime or repository state was changed in this turn. Production deployment and runtime/mount identity remain unverified. PR #36 merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` has confirmed green merge-commit CI (78/78).
- Next action: user runs the no-sudo diagnostics and shares output, redacting any private remote URL if desired. If Docker access remains denied, use the cloud provider's supported console/recovery path or an already-authorized administrator. Continue GitHub-only review meanwhile; do not enable the Greenhouse canary or change production.
- Continuation prompt: “Read the newest dated sections of both handover docs. Review the no-sudo VM diagnostics. Do not bypass Docker permissions or mutate the VM. If Docker is still inaccessible, help restore authorized admin access through OCI's supported recovery path; otherwise continue read-only runtime identification. Keep production unchanged and prepare a Greenhouse one-board dev acceptance checklist without enabling it.”


## No-sudo diagnostics received: Docker group barrier and clean Git checkouts — 2026-10-12
- User supplied no-sudo diagnostics from host `job-radar`, user `ubuntu`, UID/GID `1001`. `id` shows membership in `sudo` and `lxd`, but **not** `docker`. Socket is `root:docker`, mode `srw-rw----` (0660). Both `docker ps` and `docker compose ls` fail with permission denied. This is consistent with the account lacking access to the Docker socket; it does not reveal whether containers are running. Do not attempt LXD-based privilege escalation, change socket mode, add groups, or alter sudoers. Use an authorized VM admin/cloud-console recovery path.
- Git checks in `/home/ubuntu/job-beeper`: clean `v2-live-radar` at `61d8271`, 19 commits behind the **cached** `origin/v2-live-radar`; no local-only commits shown. Diff summary versus cached ref: README, both handover docs, `v2/config.dev.json`, and `v2/docker-compose.dev.yml` (492 insertions, 85 deletions).
- Git checks in `/home/ubuntu/job-beeper-dev`: clean `v2-live-radar` at `54fc75c`, 69 commits behind the **cached** `origin/v2-live-radar`; no local-only commits shown. The output entered a pager (`(END)`); use `GIT_PAGER=cat` or `git --no-pager` on future output to avoid that. These counts compare cached refs only and do not establish current remote state.
- No Git fetch/pull/reset/checkout, Docker action, deployment, restart, backup, scan, or database change was performed. The assistant did not execute commands on the VM. Production runtime/container/volume identity remains unknown.
- Next safe action without sudo: query live remote branch SHAs without updating local refs using `git ls-remote origin refs/heads/main refs/heads/v2-live-radar`; then compare those SHAs with local `git rev-parse` values and inspect branch ancestry only after confirming the intended refs. Do not fetch or synchronize either checkout yet. For Docker visibility, obtain authorized admin access via OCI-supported console/recovery or an existing administrator; no permission workaround.
- CI/release status unchanged: PR #36 merged to main at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, merge-commit CI verified green (78/78). No production deployment has been performed or verified. Keep production unchanged, dev LinkedIn disabled, notifications off, Gemini shadow off, and PR #35 separate.
- Continuation prompt: “Read the newest dated sections of both handover docs. No-sudo checks confirm ubuntu is not in the docker group and cannot access the root:docker 0660 socket. Both checkouts are clean but 19/69 commits behind cached origin/v2-live-radar, with no local-only commits shown. First use git ls-remote to check live branch SHAs without fetching, then compare safely; do not sync or deploy. Restore authorized Docker admin visibility through OCI-supported access, not permission workarounds. Production remains untouched.”


## Live remote SHA and ancestry verification — 2026-10-12
- User ran read-only `git ls-remote`: live `main` is `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; live `v2-live-radar` is `816946c27248e0002df6aaacab7dd1caff56db79` (the docs-only commit recording the previous diagnostics).
- Local production checkout: HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; cached `origin/main` `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`; cached `origin/v2-live-radar` `232aeef1b7e4b294d38314297b730b6548b87622`.
- Local development checkout: HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`; cached `origin/main` `a1db74fdb10d5fa8a654ee3cd438fb86f7f50ff2`; cached `origin/v2-live-radar` `58aa277eb5d84bab4989618730927ba02a14e8bb`. Therefore both local remote-tracking namespaces are stale; do not use their ahead/behind counts as current truth.
- GitHub compare API confirms live `main...v2-live-radar` is **diverged**: v2 branch is 160 commits ahead and 8 behind main; merge base is `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`. This is not a safe basis for merging or deploying without reviewing the eight main-only commits and full branch diff.
- The production checkout HEAD is an ancestor of live `v2-live-radar` (172 commits ahead from that base); the development checkout HEAD is also an ancestor (89 commits ahead). These are GitHub-side comparisons against the supplied local commit SHAs and do not establish which checkout, Compose project, image, bind mount, database, or volume is actually running.
- No fetch, pull, reset, checkout, merge, deploy, Docker action, restart, backup, or database change was performed. No VM commands were executed by the assistant. Production runtime/container/volume identity remains unverified, and Docker socket access remains blocked for `ubuntu`.
- Next step: keep both checkouts untouched. Obtain authorized Docker visibility through OCI-supported console/recovery or an existing administrator. After runtime identity and a verified backup are established, separately plan Git synchronization; first review the 8 commits on `main` not in v2 and resolve the intended release/merge strategy. Do not merge/deploy v2 into production merely because its branch has a higher commit count.
- Keep PR #36 merge commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` as the known green CI baseline (78/78). No production deployment has been performed or verified. Greenhouse canary remains a later isolated dev task with notifications off; dev LinkedIn and Gemini shadow stay disabled.
- Continuation prompt: “Read the latest dated sections of both handover docs. Live refs: main=`58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, v2-live-radar=`816946c27248e0002df6aaacab7dd1caff56db79`. GitHub says the branches diverged: v2 is 160 ahead / 8 behind main, merge base `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`. Local prod/dev HEADs are ancestors of live v2, but local origin refs are stale. Do not fetch/sync/merge/deploy. First restore authorized Docker visibility and identify actual runtime/mounts with a verified backup plan; review the 8 main-only commits before choosing any release strategy.” 


## Execution preference and next action clarified — 2026-10-12
- User explicitly asked that the assistant either perform work directly through GitHub or provide exact executable commands for VM-only actions. Do not respond with a vague task list alone; distinguish what can be completed through GitHub from what requires the user's authorized SSH/OCI access.
- Current confirmed Git state remains: live `main` = `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; live `v2-live-radar` = `816946c27248e0002df6aaacab7dd1caff56db79`; GitHub comparison says v2 is 160 commits ahead and 8 behind main. Do not merge, pull, reset, or deploy while the eight main-only commits and actual runtime/mounts remain unreviewed/unverified.
- Next: use GitHub-only read operations to inspect the branch difference and review the main-only changes where possible. For VM-only diagnostics, provide a minimal copy-paste command block with explicit expected output and redact-secret guidance. Docker access for `ubuntu` is denied by the current root:docker 0660 socket; do not suggest permission bypasses. Authorized OCI console/recovery or an existing administrator is required.
- No VM command was executed and no runtime/production state changed in this turn.


## Runtime containers confirmed; main-only parser fix reviewed — 2026-10-12
- User supplied successful authorized sudo docker read-only output from host job-radar: job-radar-dev is Up 8 hours, image job-radar-dev-radar, bound only to 127.0.0.1:8001->8000/tcp and Compose config /home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml; v2-radar-1 is Up 15 hours, image ID 97368934ed14, exposed on 0.0.0.0:8000 and Compose project v2 using /home/ubuntu/job-beeper/v2/docker-compose.yml. This confirms both containers are running and port separation is in place. It does not yet identify source revision baked into each image, mounts/volume identities, or prove the production container corresponds to its checkout.
- Both local checkouts report clean v2-live-radar working trees and stale cached tracking refs: production checkout is 19 behind cached origin/v2-live-radar; dev checkout is 69 behind cached origin/v2-live-radar. Do not infer current live-remote divergence from these counts.
- GitHub compare of v2-live-radar...main confirms the branches remain diverged. The current net main-only code difference is limited to v2/radar.py and v2/test_radar.py (70 changes in radar, 90 in tests). Reviewed commits 9b9cbf1 and 715b94d: main contains a LinkedIn structured Experience-label parser that prioritizes explicit fields like “Experience: 4.00-6.00 Years” over incidental JD mentions, plus regression tests. Commit 572f565 also makes the pagination test hermetic by mocking enrichment, avoiding real LinkedIn requests/429 cooldown contamination. Merge commit 58fdff1 is CI-green (78/78) per earlier verified run. This looks like a relevant parser correctness fix, but it must still be applied/reviewed against the live V2 branch in a controlled way; do not merge or deploy without checking branch ancestry and runtime/volume backup.
- No pull/fetch/reset/checkout/merge/deploy/restart, DB change, or backup was performed in this turn. Container identity is partially confirmed; exact image source SHA and persistent mount identities remain unknown.
- Immediate next action: use sudo docker inspect read-only to collect each container's image ID, Compose labels, mounts (names/source/destination only), and safe revision labels if present; do not print environment variables. Then inspect Compose rendered configuration carefully with secret values redacted, verify named volume mappings, and plan a backup before any source change. Keep production running untouched.
- Copyable command for the user (read-only; inspect output before sharing and redact any private host paths if needed):
```bash
for c in job-radar-dev v2-radar-1; do
  echo "===== $c ====="
  sudo docker inspect --format 'container={{.Name}} image={{.Config.Image}} image_id={{.Image}} created={{.Created}}' "$c"
  sudo docker inspect --format '{{range .Config.Labels}}{{println .}}{{end}}' "$c" | grep -E 'com.docker.compose.(project|service|project.config_files|image|version)' || true
  sudo docker inspect --format '{{range .Mounts}}{{println .Type .Name .Source "->" .Destination}}{{end}}' "$c"
done
```
- Continuation prompt: “Read the newest dated sections of both handover docs. VM confirms job-radar-dev on loopback port 8001 and v2-radar-1 on public port 8000 are running in separate Compose projects. Both checkouts are clean but cached tracking refs are stale. GitHub review shows main-only parser fix in v2/radar.py and regression tests, including explicit LinkedIn Experience-label extraction and a hermetic pagination test; merge commit CI passed 78/78. Next inspect container image IDs, Compose labels and mounts read-only, without printing env vars. Do not change production, sync branches, or deploy until image source SHA and DB/volume identity are verified and backup plan is ready. Update both handover docs after every prompt.”


## Runtime image and volume identities captured — 2026-10-12
- User ran read-only `docker inspect` for both services. Development: container `/job-radar-dev`, image `job-radar-dev-radar`, container image ID `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`, created `2026-10-12T10:03:31Z`, Compose project `job-radar-dev`, config `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`, working dir `/home/ubuntu/job-beeper-dev/v2`; named volume `job-radar-dev_radar-dev-data` mounted at `/data`; bind-mounted `/home/ubuntu/job-beeper-dev/v2/config.dev.json` at `/app/v2/config.json`.
- Production-facing V2: container `/v2-radar-1`, image `v2-radar`, container image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, created `2026-10-12T03:44:43Z`, Compose project `v2`, config `/home/ubuntu/job-beeper/v2/docker-compose.yml`, working dir `/home/ubuntu/job-beeper/v2`, Compose environment file path `/home/ubuntu/job-beeper/.env` (path only; no environment values read); named volume `v2_radar-data` mounted at `/data`. The volume names differ, confirming distinct named volumes; do not assume either volume contains a valid restorable backup without checking.
- Runtime container image IDs and Compose/mount labels are now known, but the labels shown do not expose the Git source SHA used to build either image. Need inspect image-level labels/metadata and the non-secret Compose build/image declarations next. Do not dump `.Config.Env`, `.env`, config contents, or rendered Compose output that might contain secrets.
- No runtime state changed and no production deployment/restart/backup was performed. Do not pull/reset/merge/rebuild/deploy yet. Next use read-only image inspection to look for OCI revision/source labels and inspect Compose files for only `build:`/`image:` lines and Dockerfile revision-label conventions; if no revision label exists, report that source SHA is not embedded and plan to compare image creation metadata / running app version before any change.
- Suggested read-only command: `for i in job-radar-dev-radar v2-radar; do echo "===== $i ====="; sudo docker image inspect --format 'id={{.Id}} created={{.Created}} digests={{json .RepoDigests}} labels={{json .Config.Labels}}' "$i"; done` then `grep -nE '^[[:space:]]*(build:|image:|dockerfile:)|org.opencontainers.image.revision|org.opencontainers.image.source|VCS_REF|GIT_SHA' /home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml /home/ubuntu/job-beeper-dev/v2/Dockerfile /home/ubuntu/job-beeper/v2/docker-compose.yml /home/ubuntu/job-beeper/v2/Dockerfile 2>/dev/null` (missing Dockerfiles may simply be in another path; do not infer from grep absence).
- Continuation prompt: “Read the latest dated sections of both handover docs. Runtime separation is confirmed: dev image ID sha256:13b233... uses named volume job-radar-dev_radar-dev-data and dev config bind mount; V2 image ID sha256:973689... uses named volume v2_radar-data and its .env file path. Different volume names establish separation, not backup validity. Next inspect image-level OCI revision/source labels and only safe build/image/Dockerfile declarations, never environment values or secrets. Source SHA is still unknown. Keep both containers untouched and update both docs after every prompt.”


## Image provenance check — 2026-10-12

Latest VM output confirms both runtime images have only Docker Compose labels and no OCI source/revision, `VCS_REF`, or `GIT_SHA` labels. The image IDs differ from the previously captured dev image/container identity: dev image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`, created `2026-10-12T10:03:24Z`; production-facing V2 image `sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`, created `2026-10-12T03:44:38Z`. Both Compose files declare a build and `dockerfile: v2/Dockerfile`, but the grep output did not establish the build context or locate the Dockerfile. Therefore the source commit baked into either running image remains unknown. No runtime, image, or persistent data was changed.

### Next safe step

Inspect only the Compose build context, Dockerfile path/content, checkout HEADs and worktree status, and image history metadata. Do not pull, rebuild, recreate, restart, merge, deploy, reset, or modify database volumes until source provenance and backup/rollback details are understood. Never print `.env` contents or environment-variable values.


## Running image identity and checkout check — 2026-10-12

Latest read-only VM output confirms `job-radar-dev` is running image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f` and `v2-radar-1` is running `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`. The latter image ID is no longer inspectable as a local image (`No such image`), although the existing container still reports it as its runtime image. The current `v2-radar` image tag previously inspected points to a different image ID, `sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`; do not infer that the running production container has changed to that tag's image. Both Compose files use build context `..` and Dockerfile `v2/Dockerfile`. Dockerfiles exist in both checkouts. Production checkout HEAD is `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; dev checkout HEAD is `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`. Their reported `behind 19` and `behind 69` counts are against local cached tracking refs and are not reliable indicators of current remote state. No runtime or repository state was changed.

### Next safe step

Read the two Dockerfiles and relevant Git history without exposing `.env` values, inspect `docker history` for the current dev and `v2-radar` tagged images, and inspect the running production container's mount/config metadata. The missing local production image object means image provenance is still unresolved; do not recreate or restart the running container, prune images, pull, rebuild, or deploy. Before any deployment, confirm the database backup and rollback strategy.


## Runtime image identity follow-up — 2026-10-12

VM output: `job-radar-dev` runs image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`; `v2-radar-1` runs `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`. Docker cannot inspect the latter as a local image (`No such image`), although the existing container remains running with that image ID. The `v2-radar` tag points to a different image (`sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`). Both Compose files use build context `..` and `v2/Dockerfile`. Production checkout HEAD: `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; dev checkout HEAD: `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2`. Behind counts rely on cached refs and are not authoritative. No runtime or checkout changes were made. Next: inspect Dockerfile/history and container mounts/config without exposing secrets; do not restart, recreate, prune, pull, rebuild, or deploy until image provenance, database backup, and rollback are understood.


## Dockerfile and image history review — 2026-10-13

Read-only VM output shows the production and development Dockerfiles are currently identical: Python 3.12 slim base, install `v2/requirements.txt`, copy `v2` and `dashboard`, set `/data/jobs.db`, run Uvicorn on port 8000. Their Dockerfile Git histories match through the displayed last four commits. Both Compose build contexts are `..` and Dockerfile is `v2/Dockerfile`. Current dev image `sha256:13b233...` and current `v2-radar:latest` image `sha256:a0c38e...` were built from layers with differing copied `v2` sizes (324kB vs 369kB), so the copied application contents differ. Crucially, the running production container `v2-radar-1` still points to `sha256:973689...`, whose image metadata is unavailable locally; it must not be conflated with the current `v2-radar:latest` tag. Persistent volumes remain distinct: dev `job-radar-dev_radar-dev-data` mounted at `/data`, production `v2_radar-data` mounted at `/data`. No services or data were changed.

### Next safe step

Compare hashes of selected application files in each checkout and inside each running container, and collect container health/restart status plus a non-mutating listing of database file metadata (not contents). Do not restart/recreate/prune/pull/build/deploy or run migrations. Before any rollout, verify a tested backup and rollback method for `v2_radar-data`.


## Runtime source-hash and database metadata verification — 2026-10-13

Read-only VM checks compared SHA-256 hashes of application files in both checkouts and running containers, inspected container state, and read only database file metadata from the named Docker volumes. Findings:

- Production checkout `/home/ubuntu/job-beeper/v2/radar.py` and running container `v2-radar-1:/app/v2/radar.py` match exactly: `bba3558aa293e6729ba431d72e61fcf298f6ad845ad86fda335c4847b3863bfe`.
- Development checkout `/home/ubuntu/job-beeper-dev/v2/radar.py` and running container `job-radar-dev:/app/v2/radar.py` match exactly: `ef3ce0e99f1527afc306227043478e53780bab1da235fcd6173f692f97e0a8f6`.
- Both checkouts and containers have matching `v2/requirements.txt` hash `9904eb1672148185b976a1e4228123eeacb012c864948414243b3259e6fd431b`.
- Production `/app/v2/config.json` matches the production checkout config hash `2a4faf5710cf36829646be3c91dda8da35e914e60937d07488d6d4367f3000b5`. Development `/app/v2/config.json` matches the development config bind-mounted from `v2/config.dev.json`, hash `c8961f5b288ec6b808163f1c4fc91b52237b60b1d1a4c1a4b5ccbe71c637d201`.
- Both containers were running with restart count 0; health checks are not configured. This establishes running state, not application-level health.
- Separate database volumes remain in use. Read-only metadata showed dev `jobs.db` size 3,960,832 bytes (modified 2026-10-12 18:59:03 UTC) and production `jobs.db` size 17,670,144 bytes (modified 2026-10-12 19:00:39 UTC). No database contents were read or changed.
- The diagnostic command pulled `python:3.12-slim` because it was not locally available, then mounted each database volume read-only for metadata inspection. No app containers or database data were modified.
- The command output was slightly malformed at the shell loop boundary, but both volume metadata checks completed and returned the above results.

Interpretation and next safe step: the current source files inside each running container match their respective checkout files, and dev/prod app code differs as expected. This does not prove which Git commit or image build produced the production container, because image provenance labels are absent and its reported image ID was not found in local image metadata. Before any rollout, read-only inspect each checkout's current branch, HEAD, working-tree status, and the Git commit(s) containing the exact `radar.py` blob; separately capture container image IDs and available image metadata. Do not rebuild, retag, restart, pull application code, or deploy, and do not query or mutate database contents until provenance and rollback/backup are established.


## Git blob and image-reference provenance audit — 2026-10-13

Read-only VM output adds these provenance findings:

- Production checkout `/home/ubuntu/job-beeper` is on `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` (`Document free-first LinkedIn strategy and release cleanup`, 2026-10-12 00:08:42 +05:30); its working tree is clean and `v2/radar.py` has no unstaged/staged diff. Its current file blob is `db405442e706af778a2a1e927864629a6e699d3e`; local history reports blob introduction at commit `6c93473844cd469493a0c61acf1477ba20252d69` (`Reduce LinkedIn request pressure with free-first pacing`, 2026-10-11).
- Development checkout `/home/ubuntu/job-beeper-dev` is on `v2-live-radar`, HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2` (`docs: record source status CI success`, 2026-10-12 15:31:19 +05:30); its working tree is clean and `v2/radar.py` has no unstaged/staged diff. Its current file blob is `e1b30717bfeac33fa9e0973ab5ad7d426ccf7085`; local history reports blob introduction at commit `150d2878ac7b66d11ff0f5b81e991210c7f413a8` (`Expose persisted last source error in status API`, 2026-10-12).
- Both local checkouts show their local `origin/v2-live-radar` tracking refs ahead of the checked-out HEAD by stale/unfetched counts (production behind 19, dev behind 69). No fetch was performed in this audit; these counts are not proof of the current remote delta.
- Running production container `/v2-radar-1` references image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, created 2026-10-12T03:44:43Z. That image ID is absent from `docker image ls`; the current `v2-radar:latest` tag points to a different image, `sha256:a0c38e435cbc64f13d028c040f25962586eb5050a83ac4b0d72673acd6a7a08d`, created 2026-10-12T03:44:38Z. The tag's labels contain Compose project/service/version only, with no source SHA or build revision. Do not assume the current tag is the image the running production container started from.
- Development container uses the locally available `job-radar-dev-radar:latest` image ID `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`, created 2026-10-12T10:03:31Z. Its runtime source hash matches the dev checkout.

Interpretation: runtime `radar.py` files match their corresponding checkout files, but neither the production source commit nor image provenance is fully attested by image labels. The reported `git log --find-object` commits identify local history entries associated with those blobs, not by themselves a full reproducible build attestation. The production running image's missing local image metadata and different current tag are important uncertainties. Next safe step is a read-only remote-ref comparison (e.g. `git ls-remote origin refs/heads/v2-live-radar` from each checkout) plus local `git show`/commit metadata for the identified blob-introduction commits and the commit that the container code is expected to correspond to. Do not fetch, pull, build, retag, restart, deploy, prune, or alter databases until the remote state, backup, and rollback image/source are understood.


## Remote-ref and container writable-layer audit — 2026-10-13

Read-only VM output reports `git ls-remote origin` returned the same refs from both checkouts: `main` at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` and `v2-live-radar` at `4f21c219244bfe5c490c1e3536de0a7c9bf6a921`. The latter is the latest docs-only commit created during this workflow, so local `behind 19` / `behind 69` tracking indicators are stale; do not treat them as accurate current remote deltas. No fetch was performed.

Local `git show` confirmed production HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` and its blob-introduction commit `6c93473844cd469493a0c61acf1477ba20252d69` both resolve `v2/radar.py` to blob `db405442e706af778a2a1e927864629a6e699d3e`. Dev HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2` and its blob-introduction commit `150d2878ac7b66d11ff0f5b81e991210c7f413a8` both resolve `v2/radar.py` to blob `e1b30717bfeac33fa9e0973ab5ad7d426ccf7085`.

`docker diff v2-radar-1` showed only runtime-generated Python `__pycache__`/`.pyc` changes under Python libraries and `/app/v2`; no source-file modifications were listed. This is consistent with normal Python bytecode caching, not evidence of manual source edits. The final container inspect output still identifies production image `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f` and dev image `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f`.

Next: compare each local HEAD to remote `v2-live-radar` via GitHub's compare API (read-only) and inspect the changed-file summary. Since the remote head includes the recent docs-only commits, separate those from code changes. Do not fetch, pull, rebuild, retag, restart, deploy, prune, or touch DB contents until source provenance and backup/rollback safety are understood.


## GitHub remote compare against both VM checkouts — 2026-10-13

Used GitHub's read-only compare endpoint against remote branch head `a158b9bf73a26a3309ac6ef801581c19981be790` (current `v2-live-radar` after the latest handover-note commits). No VM fetch or checkout changes were made.

- Production local HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` is an ancestor of the remote branch head; compare reports remote head 193 commits ahead and 0 behind, with merge base equal to the production HEAD. Diff summary includes `v2/radar.py` (143 changed lines: 139 additions, 4 deletions), `v2/test_radar.py` (157 additions), new `v2/gemini_extractor.py` (411 additions), new `v2/test_gemini_extractor.py` (110 additions), dev config/compose files, plus README/dashboard/docs. This establishes that production checkout is older than the current remote code and must not be assumed to be current.
- Development local HEAD `54fc75cbfd6ad92b7b3a63fdc381473c34f459d2` is an ancestor of the same remote head; compare reports remote head 110 commits ahead and 0 behind, with merge base equal to the development HEAD. The compare endpoint's file summary lists only `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`; it lists no application source, tests, config, or dashboard changes between dev HEAD and remote head. This suggests the dev checkout's tracked application code matches the remote branch's code at this compare point, with the remaining differences in the two handover documents. Verify this before treating it as a candidate release.
- These counts supersede stale local tracking indicators (`behind 19` and `behind 69`), which were based on outdated remote-tracking refs. They do not indicate the branch is behind remote; both local HEADs are ancestors of remote.
- `docker diff v2-radar-1` showed only Python-generated `.pyc`/`__pycache__` paths under runtime Python packages and `/app/v2`; no source modifications were listed. This is expected runtime cache behavior and does not by itself suggest source tampering.

Next safe work: inspect exact source/test diffs between the production code baseline and the candidate remote branch through read-only GitHub commit/file inspection, then review CI/test evidence and current dev runtime behavior. Do not deploy or restart production until a database backup and rollback path are explicitly verified and the production image provenance gap is resolved. No production or database changes were made during this comparison.


## Exact production-versus-remote source review — 2026-10-13

Read-only GitHub file inspection compared `v2/radar.py`, `v2/test_radar.py`, `v2/gemini_extractor.py`, `v2/test_gemini_extractor.py`, and `v2/requirements.txt` at production baseline commit `61d8271480eaf48b0a6442b62b1b0bb9a032df34` versus remote `v2-live-radar`.

- Production `v2/radar.py` blob is `db405442e706af778a2a1e927864629a6e699d3e` (114,244 chars, 2,991 lines); remote blob is `e1b30717bfeac33fa9e0973ab5ad7d426ccf7085` (120,033 chars, 3,126 lines). Remote `radar.py` blob matches the previously measured dev checkout/container SHA-1 Git blob identity, confirming dev code matches the current remote file at this path.
- The 143 changed lines in `radar.py` comprise 139 additions and 4 deletions. Reviewed hunks show: a new LinkedIn structured `Experience:` parser; prioritization of labeled experience metadata over incidental JD year counts; additional LinkedIn JD selection/enrichment handling; Gemini LLM shadow-only extraction integration with fail-open exception handling; `/api/llm-shadow-status`; and persistence/exposure of latest source errors as `last_error` in source status.
- Production baseline lacks `v2/gemini_extractor.py` and `v2/test_gemini_extractor.py`; both exist on remote (16,708 and 5,491 characters respectively). `v2/test_radar.py` also differs (production blob `3b6d0eef70683c8ccb95d4730da36c671b679365`, remote blob `8a739fa3f5f1d8c09a5e80501e25a2d2f625c892`). `v2/requirements.txt` is byte-identical at both refs (blob `77919a4fcd76ebc09137e54e46b9be5aa0f37922`).
- The code review confirms that current remote/dev code is functionally newer than production code. It does not, by itself, prove end-to-end test success, production compatibility, Gemini credentials/limits, or a safe release. No application or database changes were made.

Next safe step: inspect CI/check status for the code-bearing commit(s), then run or review the project's test suite against the dev checkout with explicit confirmation tests use isolated temporary databases/config. Do not run tests against production DB, deploy, restart, or change database state until backup and rollback are verified.


## Development test-isolation audit — 2026-10-13

Read-only output from `/home/ubuntu/job-beeper-dev` shows a clean worktree (local `origin/v2-live-radar` tracking status still reports `[behind 69]`, known stale tracking metadata; current remote head was separately checked via `git ls-remote`). Grep inspection of `v2/test_radar.py` and `v2/test_gemini_extractor.py` found extensive use of `TemporaryDirectory`, reassignment of `radar.DB_PATH` to a temporary `jobs.db`, and temporary SQLite paths for Gemini shadow-cache tests. Gemini tests mock `gemini.requests.post` and use test-only API-key/model values in the matched test snippets. Test files use standard-library `unittest`; requirements listing showed `fastapi>=0.115,<1` as the only displayed dependency line. Development volume `job-radar-dev_radar-dev-data` currently has `/inspect/jobs.db` metadata size 4,104,192 bytes, modified 2026-10-12 19:09:05 UTC; metadata only, no DB contents read.

Safety qualification: grep output is a partial static audit, not proof that every test is isolated or cannot invoke network/source collectors, startup hooks, or default DB paths. Before running the full suite, inspect test module setup/import side effects and the relevant functions in `v2/radar.py`, especially module-level DB initialization and collector/enrichment entry points. If any risk remains, run the suite in a separate process with a temporary `JOB_RADAR_DB` path and network calls patched/disabled; do not run against production or the persistent dev volume. No tests were run and no application/database state was changed in this step.


## Isolated test execution plan — 2026-10-13

Follow-up static inspection of current remote `v2/radar.py` confirms `DB_PATH` is set from `JOB_RADAR_DB` (defaulting to `ROOT / jobs.db`) and FastAPI startup calls `init_db()`. Therefore tests should not be run directly in the long-running development container or against its persistent `/data/jobs.db` volume. The test modules use standard-library `unittest`; the Gemini test's HTTP POST is patched in its network-related test. Many radar DB tests explicitly replace `radar.DB_PATH` with a `TemporaryDirectory` database, but the suite as a whole was not executed during this audit and no claim is made that every test is isolated.

Recommended next validation is a disposable one-off container from the dev image, with `--network none`, no persistent data-volume mounts, `JOB_RADAR_DB=/tmp/jobs.db`, and the dev config bind-mounted read-only at `/app/v2/config.json`. Run `python -m unittest v2.test_radar v2.test_gemini_extractor` from `/app` in that container. This isolates any startup-created DB to the disposable container and prevents external network calls; it does not change the long-running dev or production containers or their database volumes. Do not use production container/image or production database for tests.


## Isolated test suite passed — 2026-10-13

- The user reported the isolated test run completed successfully: `Ran 88 tests in 53.320s`, `OK`.
- Record this as a successful 88-test run; the short result alone does not identify individual test names or independently prove the exact invocation/environment.
- Next: preserve the full test command/output if available, then continue with read-only verification of current remote branch/CI state and production-versus-development source/image provenance.
- No production deployment, container restart, database mutation, or persistent-volume test was authorized or performed as part of this result. Keep production changes blocked until image/source provenance and a backup/rollback plan are verified.


## 88 isolated tests pass; inspect intermittent PR workflow failures — 2026-10-13

- User supplied the complete isolated command output: `python -m unittest v2.test_radar v2.test_gemini_extractor` ran with Docker `--network none`, a disposable `/tmp/jobs.db`, and the development config mounted read-only. Result: `Ran 88 tests in 53.320s`, `OK`.
- The accompanying Actions screenshot shows docs-only workflow runs #689 and #691 passing, while the “Draft: Gemini JD extraction shadow mode” PR #35 synchronize workflow has both failures (#688 and #692) and a pass (#690). This screenshot alone does not reveal the failing step or root cause.
- Next: inspect the failed run/job logs for #692 (and compare #688 with passing #690) before changing code or rerunning anything. Treat the local 88-test success and PR CI status as separate evidence.
- No production deployment, restart, or persistent database operation was performed or authorized. Keep production unchanged pending source/image provenance and backup/rollback verification.


## Diagnose CI failures from uploaded full test log — 2026-10-13

- User provided the full failed GitHub Actions test log. Workflow run #694 failed with 6 test failures out of 88; run #696 subsequently passed (per user's latest Actions screenshot), so the issue appears intermittent/order-sensitive rather than a deterministic failure on every run.
- Failure cluster: five LinkedIn scan tests see zero calls/results because an earlier test `test_linkedin_fast_lane_and_periodic_deep_scan` triggers HTTP 429 and leaves a 299-second global cooldown active; subsequent tests log “linkedin scan skipped; rate-limit cooldown has 299s remaining.” The six failures are: `test_linkedin_fast_lane_and_periodic_deep_scan`, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, `test_linkedin_fast_scan_staggers_all_query_location_pairs`, `test_linkedin_fast_scan_uses_broader_recency_window`, `test_linkedin_skips_deep_scan_after_fast_lane_rate_limit`, and `test_new_linkedin_job_is_enriched_from_jd_before_matching`.
- This points to shared LinkedIn rate-limit/cooldown state leaking across tests and/or test fixtures not resetting it, with a separate affected JD-enrichment assertion as a downstream consequence of the scan being skipped. Confirm exact setup/teardown and workflow command before changing implementation.
- The local user's isolated command `python -m unittest v2.test_radar v2.test_gemini_extractor` passed 88 tests in 53.320s. CI log shows `python -m unittest discover -s v2 -p 'test_*.py' -v` and 6 failures in 12.375s. These differ in test invocation/order/environment, so local pass does not invalidate CI failure.
- Latest screenshot shows run #696 passed and #694 failed for PR #35; compare logs and test invocation, then run targeted failing tests and the full discovery command in a disposable offline environment. No production changes, restarts, or database writes.


## Resume roadmap after green tests; clarify branch and release gates — 2026-10-13

- User reports the isolated module invocation passes all 88 tests in 53.323s. The latest provided Actions screenshot shows PR #35 workflow run #700 green; the docs commit workflow #699 is green too. The earlier full-discovery failure was intermittent/order-sensitive; the latest green CI is useful evidence but does not erase the need to avoid claiming every invocation/environment is permanently stable.
- Current branch state was checked through GitHub compare: `main` at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`; `v2-live-radar` is reported as 195 ahead and 8 behind, status `diverged`, merge base `cefc185a58387ebc21544e1d3b2e1a9ac07f654b`. Therefore do not say all V2 work is pushed/merged to main; PR #35 remains separate and the branch has not been reconciled. No merge/pull/deploy performed.
- Re-read `docs/JOBBEEPER_REFERENCE.md`: Greenhouse adapter already exists, is disabled, and next planned source step is a one-board development canary with notifications off; acceptance criteria include two polls, stable IDs/deduplication, first_published timestamp behavior, request/error isolation, and useful yield. Instahyre schema/freshness validation follows; Ashby, Lever, and SmartRecruiters are later one-at-a-time adapters.
- Recommended next work: resume planned roadmap, starting with a concise Greenhouse one-board canary acceptance checklist and read-only verification that current dev runtime/config and authorized Docker visibility support a safe isolated test. Do not enable the source until runtime/config are verified and the user explicitly authorizes the canary. Keep notifications off, Gemini shadow-only/disabled until its quality gate is satisfied, and production untouched.
- Production image/source provenance, named-volume identity, and verified backup/rollback remain unresolved gates. No production deployment, restart, source activation, or database modification occurred.


## Implement read-only Greenhouse two-poll canary — 2026-10-13

- Implemented directly on `v2-live-radar`:
  - Added `v2/greenhouse_canary.py`, a read-only CLI that fetches one explicitly selected public Greenhouse board twice through the existing collector and reports total/unique IDs, stable/new/missing IDs, and second-poll first-published timestamp coverage.
  - The default gap is 900 seconds; intervals under 60 seconds are rejected. It does not write the radar DB, run matching, change `source_enabled`, or send notifications.
  - Added `v2/test_greenhouse_canary.py` with tests for report metrics, two-poll sequencing, input validation, and no collector call for an invalid interval.
  - Added usage and safety/acceptance notes to `docs/JOBBEEPER_REFERENCE.md`. The existing dev config keeps Greenhouse disabled.
- GitHub commits on `v2-live-radar`: script `14c74222751a4bb466bf4d05f2ffe39a370954c6`; tests `30b85ad1c494a452f464909b045da66d9892d09e`; reference docs `fea5b112492e85f071e211370d4eba7728610821`.
- CI run #708 for the test commit was observed in progress at handover time; do not record it as passed until checked. No live Greenhouse poll has been run yet, so no canary yield/timestamp result is claimed.
- Next: confirm CI #708 result; then pull the branch in the development checkout and build only the development Compose image. Run the CLI against one selected configured board with notifications still disabled, retain the JSON output, and evaluate two-poll acceptance before any scheduler activation.
- Production was not changed. Do not build/deploy production or enable Greenhouse in production as part of this task.


## Greenhouse canary quality metrics and CI compilation — 2026-10-13

- User authorized direct GitHub development on `v2-live-radar` and requested VM pull/build commands plus handover updates.
- Updated `v2/greenhouse_canary.py` to report per-poll missing source IDs, duplicate source IDs, and published-timestamp coverage for both polls, in addition to stable/new/missing IDs. The utility remains GET-only and does not activate Greenhouse, write the radar DB, run matching, or send notifications.
- Expanded `v2/test_greenhouse_canary.py` assertions for duplicate IDs and timestamp coverage; updated `.github/workflows/v2-ci.yml` py_compile step to include the canary utility and its tests.
- Commits on `v2-live-radar`: canary `7966ae423a44ff04cbf2bc26a6f417a52365fc4b`; tests `030adf62fe0cdc913d977c7e52e182c94dc11c9f`; CI workflow `aff4fd7e5dc6bd6be536c491bf46d2bfd059f4b6`. Workflow status must be checked before VM build; these edits have not been deployed.
- Next: wait for/check V2 CI on the latest branch head. On the VM, first verify clean status and branch; fetch and fast-forward only (no force reset). Build only the isolated development image using `docker compose -f v2/docker-compose.dev.yml build`. Do not restart production or activate Greenhouse. For the actual canary, keep dev `source_enabled.greenhouse=false`, choose one already-configured public board, and run `python -m v2.greenhouse_canary --board-token <board-slug> --company "<company>" --interval-seconds 900` from the repo root; this requires outbound network and takes at least 15 minutes. Save the JSON report and review yield, IDs, timestamps and errors before any scheduler activation.
- Production source/image provenance, backup and rollback are still unverified; no deployment, service restart, source activation, or database mutation occurred.


## Greenhouse canary command blocked by host Python lookup — 2026-10-13

- User ran a build from the development checkout; terminal reported `[+] build 1/1 ✔ Image v2-radar Built`. The selected canary command then failed immediately with `Command 'python' not found`. Therefore **the canary did not execute and no Greenhouse HTTP polls or report were produced**.
- Attempted command: `python -m v2.greenhouse_canary --board-token coinbase --company "Coinbase" --interval-seconds 900` from `/home/ubuntu/job-beeper-dev`. The missing `python` executable is a host-shell issue, not a demonstrated canary-code failure. Do not assume `python3` has the application dependencies; prior host-Python tests failed import due to missing `bs4`.
- GitHub config inspection confirms `v2/config.dev.json` contains the public Greenhouse board token `coinbase` / company `Coinbase` and `source_enabled.greenhouse=false`. The canary helper at `v2/greenhouse_canary.py` is designed to make two GET-only polls, default gap 900 seconds, and emit JSON metrics without DB writes, matching, scheduler activation or notifications.
- Important image-tag caution: the build output names `v2-radar`, whereas the dedicated dev Compose file's expected image is project-derived (`job-radar-dev-radar`). Because the exact build command was not included, inspect `docker image inspect` for image tags/IDs and read-only `docker inspect` of `v2-radar-1` and `job-radar-dev` before using any image. Do not run/recreate/restart either service, retag/prune/pull images, or build with production Compose. A build by itself does not prove the running production container changed, but the local tag may have been moved; verify rather than assume.
- Next agent must: read this note plus both handovers and `docs/JOBBEEPER_REFERENCE.md`; check GitHub Actions for the latest `v2-live-radar` head and canary CI; inspect the exact VM command that produced the `v2-radar` build if available; check branch/clean-tree state; fast-forward only if safe; then build only with `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml build`. Use an isolated one-off container from the verified dev image to run `python -m v2.greenhouse_canary --board-token coinbase --company "Coinbase" --interval-seconds 900`; outbound network is needed, so do not use `--network none`. Do not mount any persistent DB volume. Keep source disabled and notifications off. Retain the JSON output and review both polls, job yield, stable/duplicate/new/missing IDs, timestamp coverage and failure status. If image provenance/compose target is unclear, stop and ask for the read-only inspect output before running the canary.
- No evidence that the canary ran, no source activation, no service restart or deployment is reported. Production source/image provenance and backup/rollback gates remain unresolved.


## CI failure review and canary blocked — 2026-10-13

- Re-read this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`. Current GitHub branch head at review: `5915f53c4292f1d6c444eab8a16c6aa55b5b74fd`.
- Latest V2 CI runs #727 (`38354348835`) and #726 (`38354343794`) failed at the full unittest step; syntax compilation passed and the new Greenhouse canary tests shown in logs passed. Run #718 (`38353753805`) passed at earlier CI commit `aff4fd7e5dc6bd6be536c491bf46d2bfd059f4b6`. Failed suite currently reports 5–6 LinkedIn scan/enrichment tests, so CI is not green and the dev image build/canary must not proceed yet. Investigate these failures against the current test/source state; do not dismiss as flaky without evidence.
- VM command evidence remains only: host `python` was missing, so the live canary did not execute and no JSON report/polls exist. The preceding build output called the image `v2-radar`, whose provenance is ambiguous. No claim that a running container changed is justified.
- No code/config change in this review. Production was not intentionally touched; no service restart, database write/migration, source activation, or notification enablement is evidenced. Greenhouse stays disabled and notifications remain off.
- Exact next action: first resolve the failing CI tests and obtain a passing latest-head CI run. Then ask for these read-only VM outputs before any build: `git status --short --branch`; `git rev-parse HEAD`; `git ls-remote origin refs/heads/v2-live-radar`; `sudo docker image inspect v2-radar:latest job-radar-dev-radar:latest --format '{{.Id}} {{.Created}} {{json .RepoTags}}'`; `sudo docker inspect v2-radar-1 job-radar-dev --format '{{.Name}} image={{.Image}}'`. Never print environment values. Only after clean checkout/fast-forward eligibility and image provenance are clear, build the dedicated dev image, run isolated tests, then the network-enabled disposable canary. Review and record its complete JSON before any acceptance decision.
- Continuation: diagnose CI failures first; do not run production Compose or enable Greenhouse. Cross-reference `docs/JOBBEEPER_REFERENCE.md` canary acceptance gates.


## VM identity check and latest CI recheck — 2026-10-13

- User-provided VM checkout is clean at `eeb59eb4cbe3cc9771572b5bd73c69e3245124bf`; remote `origin/v2-live-radar` is `b58c2acc603d412d8bcfda18365046655e139c38`. GitHub compare confirms the local checkout is the ancestor/base of remote, so fast-forward is structurally possible, but do not update/build yet while latest-head CI fails.
- Image identities from read-only inspection: `v2-radar:latest` = `sha256:6300862b5d8071221343dc5c95006d73a90a22db42983aecf3b6e0215cc9fee3` (created 2026-10-13 05:55Z); `job-radar-dev-radar:latest` = `sha256:13b233998d70787483762a563484aad8a38a6e21ecac49917f3ca913557f4c9f` (created 2026-10-12 10:03Z). Running `v2-radar-1` uses `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, distinct from the current `v2-radar:latest` tag. Running `job-radar-dev` uses the same image ID as `job-radar-dev-radar:latest`. Do not infer that either running container changed from the build alone.
- Latest-head CI recheck: run #730 / `38354820920` on `b58c2acc603d412d8bcfda18365046655e139c38` failed full unit discovery (92 tests; 5 LinkedIn scan/enrichment failures). Run #731 / `38354814782` on the same head succeeded. CI is therefore mixed, not cleanly green; investigate the failed run/test behavior before proceeding. Greenhouse canary tests themselves passed in the failed run's log.
- The live canary remains NOT RUN: host `python` was unavailable. No report, polls, or acceptance decision exist. Greenhouse stays disabled, notifications remain off; no production restart/deploy, persistent DB access, or migration was performed in this step.
- Next: investigate why same-head CI runs disagree and get reliable passing full-suite evidence. Then, if safe, fast-forward only (never reset/force); build only via `sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml build`; verify resulting image ID; run full tests in a network-isolated disposable container; only then run the network-enabled two-poll canary in a disposable container with no persistent DB volume. Keep production untouched and record/review the complete JSON.


## LinkedIn unit-test isolation fix — 2026-10-13

- Investigated CI run #735 on commit `5a71fc18060d5eb790b202e20ef5e339482ebf7b`: five failures were clustered around LinkedIn scans being skipped by a shared ~300-second 429 cooldown; JD enrichment also did not execute, consistent with the same cooldown short-circuit.
- Committed test-only isolation in `v2/test_radar.py` as `a3ae210a099576717913aa6aec7a7c1dae8bd6c7`: `MatcherTests.setUp/tearDown` now resets and restores the module-level LinkedIn request/cooldown/streak/generation values so one test's synthetic rate limit cannot contaminate another test.
- Latest-head CI run #736 (`38355269626`) was still in progress at the time of this note; this change is NOT yet confirmed by a completed green full suite. Review its final result and, if necessary, diagnose remaining failures before any dev VM build or canary.
- No canary was run, no production container/database was touched, Greenhouse remains disabled, and notifications remain off.


## Hermetic LinkedIn collector test follow-up — 2026-10-13

- CI run #736 after the rate-state isolation change reduced the suite from five failures to one. The remaining failure was `test_linkedin_fast_lane_and_periodic_deep_scan`: its parsed listing triggered JD enrichment that was not mocked, and the CI log showed a real HTTP 429 during the second scan, which activated the process-wide cooldown and caused the test to fail.
- Follow-up commit `6aa2e020a0898d660abb57fc5488203738dc3444` mocks `radar.enrich_linkedin_job` in that test so it remains offline/hermetic; the test's purpose is scan cadence, not JD extraction or live LinkedIn behavior.
- Full-suite confirmation for this latest code is still pending. Do not fast-forward/build/run the canary until latest-head CI is green and the VM safety checks are revalidated. Greenhouse remains disabled, notifications off, and production/persistent DB untouched.


## Latest-head CI verified; VM validation still pending — 2026-10-13

- Verified GitHub Actions run #744 (`38355415401`) for branch head `b51d3f8b2aa0bee6e66ac932fd32b599df1893e8`: completed successfully. Job `syntax` passed dependency install, `py_compile`, and full `python -m unittest discover -s v2 -p 'test_*.py' -v`; log reports `Ran 92 tests in 16.864s` and `OK`.
- Also verified runs #742 (`6aa2e020a0898d660abb57fc5488203738dc3444`) and #743 (`dc9d8f2335d1d380d287b1634baa7bafce209051`) completed successfully with the full-suite step passing.
- GitHub branch head matched the SHA tested by run #744 at verification time. This proves CI on GitHub only; no SSH/remote-shell tool is available in this session, so VM checkout fast-forward, dedicated dev-image rebuild, isolated container suite, and canary have NOT been executed or verified.
- Next action when on the VM: confirm clean checkout and ancestry; fast-forward only if safe; build only `job-radar-dev` using `v2/docker-compose.dev.yml`; verify exact image ID; run the full test suite in a `--network none` disposable container; only if that passes, run the read-only disposable two-poll Greenhouse canary. Do not touch production Compose/container or persistent database; keep Greenhouse disabled in config/scheduler and notifications off.


## VM isolated suite passed; CI found cursor-isolation issue — 2026-10-13

- User reported the VM disposable-container suite completed with `Ran 92 tests in 18.255s` and `OK`. The exact VM checkout SHA and image ID used for that run were not included, so do not yet treat it as validation of current branch head/image identity.
- Rechecked GitHub Actions run #746 for commit `fdf9654eddec287ac8b5f32a4d227b57ddafcd55`: it failed one test, `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations`, because the process-wide `linkedin_fast_target_cursor` could be left at a nonzero value by earlier tests. This is test-state leakage; the failure was `second_cycle` length 0 rather than 2.
- Fixed the test to save, reset to zero, and restore `linkedin_fast_target_cursor` in commit `82d1082df84f7028822692a739949d65c879d8e2`. CI for this fix must pass before canary execution.
- Do not run the Greenhouse canary yet. Confirm the new commit's latest-head CI passes, and establish VM checkout/image identity before any canary. Production container/database untouched; Greenhouse remains disabled in config/scheduler; notifications remain off.


## Latest-head CI green; VM checkout needs safe fast-forward — 2026-10-13

- Verified current GitHub branch head `60c337f964f4b7b040d33c4f0c23773fc4c0a788`; latest-head Actions run #749 (`38365552304`) completed successfully. Run #747 for the test-cursor isolation fix (`82d1082df84f7028822692a739949d65c879d8e2`) also passed the full suite.
- User-provided VM output shows checkout `fdf9654eddec287ac8b5f32a4d227b57ddafcd55` and dev image `sha256:57a6a204922201f70e226116bb107ef0a82ac9b3da428b50f542e55809668364`, created at `2026-10-13T07:49:32Z`. This is behind current GitHub head; prior reported 92-test success therefore does not validate the latest commit.
- Next: on the VM fetch latest branch, confirm working tree clean and fast-forward ancestry, fast-forward only, then rebuild only the dedicated dev image, inspect its image ID, and rerun the full suite in a disposable `--network none` container. Do not run canary until that passes. No production container/database touched; Greenhouse remains disabled and notifications remain off.


## VM head/image and isolated tests verified; Greenhouse canary next — 2026-10-13

- User reports the dev VM checkout is `c15c40b699a89a78d4440d86eecd5ef8b4eff8f8`, clean on `v2-live-radar`; dev image is `sha256:10587b0403ade778c5f0bc844d6984da2a251789b0ae7545512a03e68d1febb5`, created `2026-10-13T07:57:37Z`; disposable image test suite passed `Ran 92 tests in 17.992s / OK`. The reported checkout matches GitHub branch head.
- Verified latest GitHub Actions run #751 for this head succeeded: https://github.com/AvinashBhalla/job-beeper/actions/runs/38365680132. Reviewed current `v2/config.dev.json` and `v2/greenhouse_canary.py`: notifications are false, Greenhouse source is disabled, and the canary makes two public-board polls without DB writes, matching, or notifications.
- Next action: run a disposable canary for one existing dev-config board (Coinbase) with 900 seconds between polls, using the rebuilt dev image and a network-enabled disposable container. Capture the JSON report and review ID stability, timestamp coverage, request errors, and job yield. This is a dev-only observation, not permission to enable Greenhouse or deploy. Production Compose/container and persistent database remain untouched.


## Coinbase canary first poll confirmed; waiting for second snapshot — 2026-10-13

- User screenshot shows the disposable canary command running on the verified dev image and log `boards=1 successful=1 failed=0 jobs=225`. This confirms the first Coinbase Greenhouse poll succeeded with 225 jobs; the final report is expected only after the configured 900-second interval and second poll.
- Advise the user not to interrupt the process yet; wait for the final JSON report. No production Compose/container or persistent DB touched; Greenhouse remains disabled in scheduler config and notifications remain off.


## Coinbase Greenhouse two-poll canary passed — 2026-10-13

- User supplied the final JSON report from the disposable two-poll canary on the verified dev image. Both polls completed with 225 jobs and 225 unique source IDs each; `stable_ids=225`, `new_ids_on_second_poll=0`, `missing_ids_on_second_poll=0`, duplicate IDs 0, and jobs without source IDs 0.
- Publication timestamps were present for all 225 jobs in both snapshots (unknown timestamp count 0). Report explicitly confirms `database_writes=0`, `matching_executed=false`, `notifications_sent=false`, `status=completed`.
- Conclusion: successful two-snapshot validation for the existing Coinbase board only. Do not enable Greenhouse in the scheduler or production based on this single-board canary. Any next step requires separate review of scope, board coverage, and operational acceptance. Production Compose/container and persistent database remain untouched; notifications remain disabled.


## User decision: close Coinbase canary and move to product roadmap — 2026-10-13

- User explicitly chose not to run more Greenhouse board tests after the Coinbase two-poll canary passed. Accepted evidence: 225 jobs in each poll, 225 stable unique IDs, zero duplicates/new/missing IDs, full publication timestamp coverage, no database writes/matching/notifications. No further Greenhouse polling is planned unless a concrete issue emerges.
- No code/config change this turn. Greenhouse stays disabled in scheduler config; notifications remain disabled; production Compose/container and persistent DB remain untouched.
- Reviewed docs/JOBBEEPER_REFERENCE.md: next implementation priority is the LinkedIn experience-parser patch validation/promotion, followed by the broader source roadmap. However, GitHub compare reports main...v2-live-radar as diverged (v2 ahead by 232 commits and behind by 8); v2/radar.py has different blob SHAs on the two branches. Do not merge or promote the diverged branch wholesale. Before the next code change, inspect the existing parser patch and isolate its minimal intended diff against current main, then use a safe focused promotion path with CI.
- Next action: inspect parser-specific changes/tests and branch history, determine whether the parser patch is already present on main, and propose/prepare a narrow change only if still needed. Preserve all existing production safety constraints.


## Next action: inspect isolated LinkedIn parser diff before safe promotion — 2026-10-13

- User asked to proceed with minimal explanation and wants only VM commands; assistant handles GitHub-side review. No code/config changes or VM mutations in this turn.
- Re-read the three source-of-truth docs before acting. Coinbase canary is accepted as complete; no additional Greenhouse board tests. Keep Greenhouse disabled, notifications off, production container and persistent database untouched.
- GitHub compare confirms `main...v2-live-radar` is diverged (v2 ahead by 234 and behind by 8); never merge or promote the branch wholesale. The current `v2/radar.py` parser patch adds `extract_linkedin_labeled_experience` and metadata parsing, while main has a different `v2/radar.py` blob. Next action is read-only local inspection on the VM of branch SHAs, relevant parser diff, parser-focused tests, and CI before deciding on a narrow cherry-pick/patch. Do not modify branches or deploy until the diff and target main state are established.
- User command requested: run the read-only Git inspection block supplied in chat and return all output. This is not a deployment command and does not touch runtime state.


## Inspection update: parser logic already exists on main — 2026-10-13

- Re-read handover, knowledge transfer, and reference docs. The user's VM output confirms the local checkout is clean but behind the latest remote v2 branch; remote heads are main `a1db74f...` and v2 `4e70f9c...`, with divergence reported as 4 main-only commits and 236 v2-only commits at that fetch.
- GitHub read-only review shows current `main` already contains `extract_linkedin_labeled_experience` and the focused LinkedIn structured-experience tests (`test_linkedin_structured_experience_metadata_outside_description_is_captured`, `test_linkedin_generic_experience_snippet_does_not_skip_jd_enrichment`, and overall-experience extraction tests). Therefore, do not cherry-pick the entire v2 branch or assume the parser is absent from main. Next step is compare the exact parser/enrichment/collector sections on both refs and inspect main CI to establish whether any small missing fix remains.
- No code changes or VM runtime changes made. Greenhouse remains disabled, notifications off, production container and persistent database untouched.


## VM comparison corrected: parser patch is missing from main — 2026-10-13

- User-provided VM output is authoritative for the checked refs: worktree clean on local `c15c40b...`; refreshed remote heads were `main=a1db74f...` and `v2-live-radar=c79d636...`, with divergence `4 main-only / 236 v2-only`. The second fetch advanced v2 after the first command block, so use the latest remote head rather than the earlier `4e70f9c...`.
- Correction to the prior note: `git show origin/main:v2/radar.py | grep ... extract_linkedin_labeled_experience` returned no match. Main has general overall-experience extraction tests, but not the new LinkedIn-labeled metadata parser or the two focused regression tests shown in the v2 diff. The v2 patch also contains unrelated Gemini shadow extraction and source-status observability changes, which must not be promoted with it.
- Decision: do not merge/cherry-pick the diverged v2 branch wholesale. Next step is a narrowly scoped promotion branch from current main containing only the LinkedIn labeled-experience parser/enrichment/collector fix and its focused regression tests; inspect dependencies and run CI before opening a PR. No production or VM runtime changes made. Greenhouse remains disabled; notifications remain off; persistent production database untouched.
- Expected evidence: focused diff against current main, PR/CI result, then only if CI passes provide VM commands for dev-only validation. Never deploy directly from v2-live-radar.


## Recheck after user asked next step — 2026-10-13

- Re-fetched the three required docs and compared current GitHub refs. Current GitHub compare now reports `main=58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, `v2-live-radar` 240 commits ahead and 8 behind. This differs from earlier VM-reported refs, so those earlier conclusions must not be applied without a fresh fetch.
- Current fetched `main:v2/radar.py` contains `extract_linkedin_labeled_experience`; current `main:v2/test_radar.py` also contains the LinkedIn structured-metadata and generic-snippet regression tests. Thus a parser promotion branch is not justified yet. Next action is to fetch refs on the VM and inspect the current exact diff; do not create a promotion branch, merge, or deploy based on stale refs.
- No code or runtime changes made. Greenhouse stays disabled, notifications off, production and persistent database untouched.


## VM ref comparison: refresh remote-tracking main explicitly — 2026-10-13

- User's VM diff confirms the LinkedIn labeled-experience parser and focused tests exist on the fetched v2 branch relative to its reported `origin/main=a1db74f...`. However, `git fetch origin main v2-live-radar` reported main only as `FETCH_HEAD`; it advanced `origin/v2-live-radar` but did not refresh `origin/main`. Thus the displayed main SHA is likely a stale remote-tracking ref and is not valid evidence for promotion.
- Current GitHub API compare reports main `58fdff19...`, v2-live-radar 242 commits ahead and 8 behind; fetching current GitHub main confirms it already contains `extract_linkedin_labeled_experience` and the structured-metadata regression test. Do not promote parser code or merge the diverged branch.
- Next VM step is read-only: explicitly fetch `refs/heads/main:refs/remotes/origin/main` and `refs/heads/v2-live-radar:refs/remotes/origin/v2-live-radar`, then compare the updated refs. No code/runtime changes. Greenhouse remains disabled, notifications off, production and persistent database untouched.


## Parser comparison closed; next roadmap item is isolated Instahyre validation — 2026-10-13

- User refreshed both remote-tracking refs correctly: `origin/main=58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, `origin/v2-live-radar=55c3a3adf76c5fa39ba99f59c8e379ceec0dc8fa`. The exact diff shows no LinkedIn parser/enrichment change missing from main; v2-only `radar.py` hunks are Gemini shadow extraction and persisted source-error observability. Test diff is mostly rate-limit isolation and source-status error tests. Do not merge or promote the diverged branch.
- Main's Instahyre collector currently calls `https://www.instahyre.com/api/v1/job_search/`, uses a location and limit 35, accepts several possible payload shapes, and normalizes IDs/URLs/timestamps. Instahyre remains disabled by default. Next roadmap step is a bounded, read-only dev validation of its live response/schema/freshness and useful yield, without database writes, matching, notifications, or changing source enablement; only then decide whether adapter fixes are needed.
- No code, runtime, production container, or persistent database changes. Greenhouse remains disabled and notifications remain off.


## Instahyre validation preparation — 2026-10-13

- User VM output confirms `extract_linkedin_labeled_experience` is already present on `origin/main`; both inspected configs keep `instahyre` and `greenhouse` disabled. The local `v2-live-radar` checkout is clean but 18 commits behind its remote; do not run app code from this stale checkout or merge branches.
- Next step is a bounded direct GET-only probe of Instahyre's public search endpoint using `curl` and `jq`, saving only a temporary response under `/tmp` and summarizing payload shape, available fields, IDs, posting timestamps, and result count. This avoids importing the app, touching any database, matching jobs, changing source enablement, or sending notifications.
- No runtime/code/config/production changes. Greenhouse remains disabled and notifications remain off.


## Instahyre probe returned HTTP 400 — 2026-10-13

- User's bounded direct GET to `https://www.instahyre.com/api/v1/job_search/?jobLocations=Bengaluru&limit=35` returned HTTP 400, so no response JSON/schema, IDs, timestamps, or useful-yield evidence was obtained. Treat the endpoint as unvalidated; do not enable Instahyre or repeat broad probing. A single bounded diagnostic may inspect status/body only if needed; otherwise move to the next documented public ATS source.
- The command failed before writing `/tmp/instahyre_probe.json`; VM `git status` remains clean on `v2-live-radar`, 18 commits behind `origin/v2-live-radar`. No code/config/runtime/database changes; notifications remain off and Greenhouse remains disabled.


## Ashby PostHog board probe — 2026-10-13

- Read-only public Ashby endpoint returned 10 listed jobs with 10 unique IDs and no missing IDs, titles, URLs, or publication timestamps. Sample roles are mixed and many are region-specific; one board is not enough evidence to enable a source. Keep scheduler flags unchanged, notifications off, and production untouched. VM checkout remains clean but 24 commits behind `origin/v2-live-radar`; do not run app code from this stale checkout.


## Ashby OpenAI board probe — 2026-10-13

- User-provided read-only VM output for the public Ashby OpenAI board shows 808 listed jobs, 808 unique IDs, and no missing IDs, titles, job URLs, or published timestamps. The payload is structurally promising, but the sample contains postings dated as far back as 2023 and is globally distributed; structure alone does not establish freshness or useful India/remote yield.
- Next step: summarize the already-downloaded /tmp/ashby_openai_probe.json locally by publication-age buckets and India/remote locations; do not repeat the network request, run app code from the stale checkout, enable Ashby, change scheduler/config, run matching, send notifications, or touch production/database volumes.
- No repository code, config, runtime, production, or database changes. Greenhouse and Instahyre remain disabled; notifications stay disabled for all validation work.


## Ashby OpenAI timestamp parsing correction — 2026-10-13

- The first local summary command failed because jq `fromdateiso8601` rejected fractional seconds with a `+00:00` timezone suffix (example: `2026-03-12T16:38:15.322+00:00`). The corrected read-only jq command strips fractional seconds, normalizes `+00:00` to `Z`, and safely counts unparseable timestamps.
- Next step remains local analysis of the already-downloaded `/tmp/ashby_openai_probe.json`; do not repeat the network request, run app code from the stale checkout, enable Ashby, alter scheduler/config, run matching, send notifications, or touch production/database volumes.
- No repository code, config, runtime, production, or database changes. Greenhouse and Instahyre remain disabled; notifications stay disabled for this validation.


## Ashby OpenAI freshness and geography summary — 2026-10-13

- User-provided local jq summary of the already-downloaded public Ashby OpenAI board payload `/tmp/ashby_openai_probe.json`: 808 total jobs; 8 India-location matches; 30 remote-location matches; 35 matching India OR remote (sets overlap); 237 published within 30 days; 532 within 90 days; 59 older than one year; 0 unparseable publication timestamps.
- Timestamp parser issue is resolved. The initial `jq fromdateiso8601` failed on fractional seconds and `+00:00`; the corrected summary successfully parsed all timestamps. Do not repeat the network request just for this summary.
- Interpretation: payload structure and timestamps are complete, and the board has a substantial fresh pool overall, but only 35/808 (4.3%) match the broad India-or-remote location text filter, including just 8 explicit India matches. The remote text match does not establish remote eligibility for India; location semantics and role relevance still need inspection. This is promising enough to consider an isolated Ashby adapter implementation with a narrow board allowlist, but is not evidence to enable the source in the scheduler.
- Next work: inspect current `v2-live-radar` docs and source code again; design a minimal Ashby public posting API adapter behind a default-off feature flag, with stable job IDs, canonical apply URLs, company/title/location/description/publishedAt normalization, pagination/board configuration, bounded requests/backoff, per-source error isolation, and fixture-based tests. Start with a small explicit board allowlist and assess useful India-eligible/remote-eligible developer-role yield before expanding. Keep Ashby disabled, notifications disabled for validation, and do not run matching or touch production/persistent database volumes until a separately reviewed dev validation plan is approved.
- Other source outcomes remain: PostHog Ashby board returned 10 structurally complete jobs but mixed regional relevance; Instahyre endpoint returned HTTP 400 with `{"job_locations":["Invalid location"]}` and remains unvalidated/disabled; Coinbase Greenhouse two-poll canary passed with 225 stable jobs per poll and no duplicates/new/missing IDs, but Greenhouse remains disabled.
- No code, config, runtime, production, or database changes were made for this summary. Never merge the diverged `v2-live-radar` branch wholesale into `main`; do not enable sources or notifications as a side effect of adapter development.


## Ashby adapter implementation readiness — 2026-10-13

- Re-fetched the current three required documents from `v2-live-radar` and inspected the current source/config files directly on GitHub. This was GitHub-side inspection only; no VM commands were run.
- Current `v2/radar.py` has collectors for LinkedIn, Naukri, Instahyre, and Greenhouse only. No Ashby collector or Ashby entry exists in `COLLECTORS`; current config validation recognizes only those four sources. The current V2 config is version 10, and Ashby is not yet represented in either `v2/config.json` or `v2/config.dev.json`.
- Current development config is safely isolated in configuration: notifications are disabled; LinkedIn, Instahyre, and Greenhouse are disabled; Naukri alone is enabled. Preserve that state. Root `config.json` is a different legacy/configuration surface and must not be changed for this V2 adapter task.
- The Ashby OpenAI public-board summary remains the latest measured payload evidence: 808 jobs; 8 India text matches; 30 remote text matches; 35 in the overlapping India OR remote union; 237 published within 30 days; 532 within 90 days; 59 older than one year; zero unparseable timestamps. The broad text filter does not prove remote eligibility in India or role relevance. Do not repeat this request.
- Next implementation: add a minimal public Ashby posting API collector behind a new explicit `ashby_boards` allowlist and a default-off `source_enabled.ashby` flag; bump config version and migrate existing persisted configs so Ashby cannot become enabled implicitly; add a conservative poll interval; normalize stable IDs, company/title/location, direct job URL, description and `publishedAt`; handle malformed payloads, partial board failures, duplicate IDs and unknown timestamps; add deterministic fixture-based unit tests for valid/empty/malformed/failed-board payloads and default-off migration.
- Validation must remain synthetic/unit-test first. Do not run matching, persist jobs, send notifications, enable Ashby in either scheduler config, touch production services or persistent volumes, or run app code from the stale VM checkout. Verify current refs and exact diff before any commit. Use CI evidence only after the workflow actually completes; no test or CI result is claimed in this entry.
- No code/config/runtime/production/database changes were made in this inspection turn. Greenhouse and Instahyre remain disabled; notification safety restrictions remain in force. Never merge the diverged `v2-live-radar` branch wholesale into `main`.


## Engineering continuation — 2026-10-13 (Ashby adapter implementation)
- Inspected current `v2-live-radar` and all three required documents. No Ashby collector, registry entry, config validation, or migration existed; schema was v10. Implementation reuses `normalize_job`, `COLLECTORS`, and the existing `run_source` source health/error isolation.
- Added a public Ashby collector with a validated explicit `ashby_boards` allowlist (max 20; narrow seed entries OpenAI and PostHog), one GET per board with a 15-second timeout, board-scoped IDs, direct job URL, company/title/location/description normalization, duplicate suppression, partial-board failure isolation, strict `publishedAt` parsing, and unknown timestamps left unknown. All-board failure raises into existing source health. Config v11 migration forces Ashby off for persisted configs older than v11; poll interval 1800 seconds.
- Code/config/test/docs commits so far: `ea7b02b35b4667a91aca6bb7f5428c607b0be6f9` (collector + migration + validation + registry), `7e69799e650e09ba00fee98397bed4c959ab429f` (main V2 config), `04cae9034a7d084319989b1f63df2c648d1ba981` (development config), `1b5f1ff93d4d88040b028b32c6eb895a15ad5eec` (fixture tests), and `a00e00ec5ac2f1da48db75b27938506001ccd1ca` (V2 README). Work remains in progress; documentation updates and verification commits follow.
- Tests were authored for valid results, empty jobs, malformed payload / partial failure, duplicate IDs, missing/invalid timestamp without `updatedAt` fallback, total board failure, migration and allowlist validation. Tests have **not** been run locally (no local repository shell/VM attached); CI status must be checked after documentation commits. No deployment or VM runtime test is claimed.
- Ashby remains explicitly disabled in both V2 configs. Development notifications remain disabled. Root `config.json`, production services/database/volumes, `main`, Greenhouse, Instahyre, matching behavior and notification behavior were not changed. No board probe was repeated, no matching/notification run took place, and no deployment was performed.
- Remaining risks: actual public schema variation, publication timestamp coverage, India / remote applicant eligibility, relevant developer-role yield and historical-alert replay safety are unvalidated. Next action: complete the handover updates, re-fetch/verify all modified files, then check CI for the latest branch head; if green, plan a separate read-only development validation with notifications disabled and Ashby still off. Never merge the diverged dev branch wholesale into `main`.


## Follow-up validation — 2026-10-13
- GitHub Actions run `38413031061` and the subsequent documentation-triggered runs `38413124663` and `38413220587` executed the test suite: 100 tests ran, with one unrelated existing failure in `test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations` (the second cycle yielded zero calls because the rotation test did not isolate process-level cooldown state). This is not a green CI result.
- Tightened the test isolation only: `v2/test_radar.py` now patches `_linkedin_cooldown_remaining` to zero within that rotation test, so it measures round-robin cursor behavior independently of rate-limit state. Commit: `7d6c3d3df76b9c269608a83173b08e331077b67e`. The new branch CI run `38413635868` was queued when this note was written; outcome is not yet known here.
- Ashby remains disabled, both configs are version 11, development notifications remain disabled. No local tests, VM commands or deployment were performed. Next: inspect run `38413635868` and verify docs/config/source registry after CI completes. Do not activate Ashby or modify production.


## Final verification — 2026-10-13
- Verified current branch `v2-live-radar` head: `83a2de2a042209f4267fc98e22f859c4e9d7c899`.
- GitHub Actions run `38413707935` completed with conclusion `success`; job `syntax` passed and its log reports `Ran 100 tests ... OK`. Run URL: https://github.com/AvinashBhalla/job-beeper/actions/runs/38413707935
- Re-fetched both handover docs and both V2 configs from the branch. Both docs contain dated updates. Both configs are version 11, Ashby is false, Ashby poll target is 1800 seconds, and development notifications remain false.
- No deployment, VM command, production interaction, matching run, notification send, or live Ashby probe was performed. Root `config.json`, `main`, Greenhouse and Instahyre activation were not changed.
- Next action: prepare a read-only development-checkout validation command only after the user confirms their local checkout path/state; keep all sources and notifications disabled during validation. After that, inspect the results and separately review historical-listing/notification replay safeguards before proposing any Ashby activation.


## Development checkout test verification — 2026-10-13
- User ran the test suite from `/home/ubuntu/job-beeper-dev` after fast-forwarding branch `v2-live-radar` to `a9dd83953d06f360ca707ba207387961818241d9`.
- The project runtime dependencies installed from `v2/requirements.txt`; that requirements file did not install pytest, so the user installed pytest into the checkout-local `.venv` only. No repository dependency files were changed.
- Verified user-reported command: `python -m pytest -q v2/test_radar.py v2/test_greenhouse_canary.py v2/test_gemini_extractor.py` → **100 passed, 4 warnings, 2 subtests passed in 12.56s**.
- The four warnings are FastAPI `on_event` startup/shutdown deprecations in `v2/radar.py` / FastAPI; they did not fail tests. This is unit-test evidence only, not a runtime/deployment check.
- No service was started; no matching, source polling, database writes, or notifications were run. Ashby, Greenhouse, and Instahyre remain disabled; notifications must remain disabled in dev.
- Next: verify the local checkout branch/HEAD/working tree and inspect `v2/config.dev.json` to confirm source flags and notification state. If safe, proceed only with explicitly read-only validation; do not run the service or change source enablement as part of this step. Record the exact output before planning the next canary.


## Dev checkout status follow-up — 2026-10-13
- User verified the local development checkout at `/home/ubuntu/job-beeper-dev`: branch `v2-live-radar`, HEAD `a9dd83953d06f360ca707ba207387961818241d9`.
- `git status --short` reports ` M v2/config.json` and untracked `.venv/`. The changed root V2 config is not yet inspected; preserve it and do not reset/checkout it until its diff is reviewed. The untracked virtual environment is expected local tooling and must not be committed.
- Parsed `v2/config.dev.json`: `config_version=11`; LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, Ashby=false; `notifications_enabled=false`.
- User-reported unit tests on this checkout passed: 100 passed, 4 FastAPI deprecation warnings, 2 subtests passed in 12.56s. No service, matching, polling, database writes or notifications were run.
- Next exact action: from `~/job-beeper-dev`, run `git diff -- v2/config.json` and `git diff --stat`; inspect output before deciding whether the local config modification is an intentional local-only change. Do not include `.venv/` in commits. Keep production, `main`, services, source flags and notification settings untouched.


## Local checkout fast-forward — 2026-10-13
- User restored only the formatting-only changes in `v2/config.json`; `git status --short` showed only the local untracked `.venv/`, which must remain uncommitted.
- User fetched `origin/v2-live-radar`; local branch was reported four commits behind, then `git pull --ff-only origin v2-live-radar` completed successfully as a fast-forward from `a9dd839` to `48e921a`, updating only `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` (17 lines each).
- Next: verify with `git status -sb` and `git rev-parse HEAD`. No services, polling, matching, DB writes, or notifications were run; keep source flags and notifications unchanged.


## Checkout synchronized — 2026-10-13
- User fast-forwarded local `~/job-beeper-dev` from `48e921a` to `cab194b1c62dc2cbe07e0c1673813000b67b2601`, matching `origin/v2-live-radar` at the time of verification.
- `git status -sb` shows branch aligned with origin and only `?? .venv/`; retain the virtual environment locally and do not commit it.
- Next safe step: run a read-only check of `v2/config.dev.json` source flags and notification setting, plus JSON syntax validation. Do not start services, poll sources, run matching, write to the DB, or send notifications.


## Read-only config validation confirmed — 2026-10-13
- User ran the sync successfully; local `v2-live-radar` was aligned with `origin/v2-live-radar` at `cc98d62be1fd78a3266dd813f6a8029ae64f0d7a`. `git status -sb` showed only `?? .venv/`; keep it local and uncommitted.
- User's Python check confirmed both `v2/config.json` and `v2/config.dev.json` are valid JSON. Development config is version 11 with LinkedIn=false, Naukri=true, Instahyre=false, Greenhouse=false, Ashby=false, and `notifications_enabled=false`.
- No application/service was started; no source polling, matching, DB writes, or notifications were run. Combined commit status lookup for `cc98d62` returned no status checks, so do not describe that commit as CI-verified.
- Next: if continuing, inspect the existing read-only Greenhouse canary utility and its usage/tests, without executing network polling or starting the radar service. Preserve disabled sources/notifications and production isolation.


## Greenhouse canary code review — 2026-10-13
- User fast-forwarded `/home/ubuntu/job-beeper-dev` to `3db196dfd07fce316ad501d310c7f86c4fcd61e8`, matching `origin/v2-live-radar`. `git status -sb` showed only untracked `.venv/`; retain locally and do not commit.
- User supplied read-only inspection output for `v2/greenhouse_canary.py` and `v2/test_greenhouse_canary.py`. Code implements two snapshots of one explicit board, enforces a minimum 60-second interval (default 900 seconds), reports unique/stable/new/missing IDs, duplicate and missing source IDs, and published timestamp coverage. Tests cover report arithmetic, two collection calls/sleep, and invalid inputs before collection.
- This is a static review of supplied source plus mocked unit tests, not evidence of a live request or board yield. No canary execution, service startup, scheduler polling, matching, DB writes, source activation, or notifications occurred.
- Keep `source_enabled.greenhouse=false` and `notifications_enabled=false` in development. Do not activate Greenhouse or touch production/main. Before any separate canary run, inspect the existing `greenhouse_boards` allowlist read-only and select exactly one already-configured board; use the utility directly, not the radar service. Review the JSON report for failures, duplicate/missing IDs, timestamp coverage and useful yield. Preserve the local `.venv/`.
- Next exact action: read-only inspect the current `greenhouse_boards` entries in `v2/config.dev.json` and verify the local branch/HEAD/status. No code changes or runtime validation claimed. Continuation: select one existing board for an explicitly bounded read-only canary only after reviewing its config entry; do not enable the source or notifications.


## Greenhouse board allowlist reviewed — 2026-10-13
- User reported local `~/job-beeper-dev` branch `v2-live-radar`, HEAD `3db196dfd07fce316ad501d310c7f86c4fcd61e8), aligned with origin before pulling the prior handover notes. Working tree showed only untracked `.venv/`. User then successfully fast-forwarded from `3db196d` to `ff44a6466529ea80b36e2a6d8345962f955e1b11`, updating only the two handover docs.
- Read-only parse of `v2/config.dev.json` reported Greenhouse disabled and notifications disabled. Existing configured boards are `coinbase` / Coinbase, `gravitonresearchcapital` / Graviton Research Capital, and `zocdoc` / Zocdoc. No config was changed.
- Earlier documented Coinbase two-poll canary returned 225 jobs in each poll with all 225 IDs stable, no new/missing/duplicate IDs and timestamp coverage present; this is historical evidence for those two snapshots only. For a distinct board-level payload check, propose a one-board Zocdoc canary, using only its existing allowlist entry.
- No live canary was run in this turn; no service startup, scheduler polling, matching, DB writes, source activation or notifications. Preserve `.venv/` locally; do not commit it. Keep Greenhouse false and notifications false; production and `main` untouched.
- Next action: from repository root with the local virtual environment active, run `python -m v2.greenhouse_canary --board-token zocdoc --company "Zocdoc" --interval-seconds 900`, which performs two public GET polls 15 minutes apart. Retain the JSON report and review request success, counts, ID stability, duplicate/missing IDs, timestamp coverage and useful yield. This does not authorize scheduler activation. After the report, record evidence and decide next step separately.


## Zocdoc Greenhouse two-poll canary result — 2026-10-13
- User ran `python -m v2.greenhouse_canary --board-token zocdoc --company "Zocdoc" --interval-seconds 900` from the dev checkout and supplied the completed JSON report.
- Live collector logs reported `boards=1 successful=1 failed=0 jobs=58` on both polls. Report: 58 jobs and 58 unique IDs in each poll; 58 stable IDs; zero new IDs and zero missing IDs on poll two; zero duplicate source IDs; zero jobs without source IDs; 58/58 published timestamps present in each poll. Status completed.
- Assessment: clean two-snapshot stability and timestamp/ID coverage for this Zocdoc board during this test window. This does not establish longer-term freshness, relevant-job yield, or unseen/new-job discovery. Treat as board-and-window-specific evidence only.
- Report states `database_writes=0`, `matching_executed=false`, `notifications_sent=false`. No service/scheduler was started and no source toggle was changed as part of this canary. Keep Greenhouse disabled in dev and notifications disabled; do not touch production or main.
- No code/config change. Existing local `.venv/` remains local and must not be committed.
- Next: record this canary as passed for the two-poll stability gate; before any scheduler activation, separately review relevant/new-job yield and source health strategy, then obtain explicit approval for any config activation. Do not enable Greenhouse merely because this canary passed.
- Continuation: start by reading this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; inspect only evidence relevant to the next explicitly approved step.


## Local handover sync reported — 2026-10-13
- User confirmed they completed the requested `git pull --ff-only origin v2-live-radar` after the Zocdoc canary. Pull output/HEAD was not pasted, so this is user-reported rather than independently verified local-state evidence.
- Read the latest handover, knowledge-transfer, and JobBeeper reference documents from `v2-live-radar`; no repository code/config changes were made in this turn.
- Zocdoc two-poll canary evidence remains: 58 jobs in each poll; all 58 IDs stable; no duplicates, missing IDs, missing source IDs, or unknown published timestamps. The test did not establish relevant-job yield.
- Next exact action: run one additional read-only Zocdoc public-board sample and print only a compact summary of job titles, locations, publication timestamps, and source URLs (no descriptions), so useful yield can be assessed. Do not start the app/scheduler, change source toggles, write the database, run matching, or send notifications. Keep Greenhouse and notifications disabled; leave production and `main` untouched. Preserve local `.venv/` untracked.
- Continuation: review the compact sample for relevant/new-job yield before proposing any source activation; this does not itself authorize activation.


## Zocdoc job-yield sample reviewed — 2026-10-13
- User supplied one live read-only sample from `snapshot("zocdoc", "Zocdoc")`: 58 jobs returned; first 15 shown with titles, locations, posted timestamps and URLs. This was one public-board request, not a scheduler run.
- Sample contains many US-based sales/manager/director roles and several old general-interest/application postings. India-based examples include Analyst, Quality Assurance (Pune), Coordinator, Workplace Experience (Pune), Enterprise Support Associate (Pune), and General Interest Technology/Operations roles. This sample shows some India presence but weak apparent fit against dev target roles (software/full-stack/frontend/backend/Python/AI/LLM engineering) and configured locations (Bengaluru, Gurugram, Delhi, Remote India); Pune is not in the configured location list. Since only 15 of 58 were inspected and no matcher was run, do not generalize to all 58 or claim a definitive relevance count.
- Assessment: Zocdoc passed the two-poll ID/timestamp stability check, but the visible sample is not compelling evidence of useful yield for the current target profile. Do not activate Greenhouse on the strength of this board alone.
- Next: inspect a compact sample from the existing Coinbase board using one public GET, with no descriptions, matching, database writes, source activation, scheduler startup or notifications. Compare the sample against target roles/locations before deciding whether to evaluate Graviton Research Capital. Keep Greenhouse and notifications disabled; production and `main` untouched; preserve local `.venv/` untracked.


## Coinbase Greenhouse job-yield sample reviewed — 2026-10-13
- User supplied one live read-only sample from `snapshot("coinbase", "Coinbase")`: collector log reports one board successful, zero failed, and 226 jobs returned. The first 20 titles/locations/timestamps/URLs were shown; no descriptions, matcher output, DB writes, source activation, scheduler startup, or notifications were involved.
- The visible sample is dominated by non-target finance/accounting, legal, operations, management and internship roles, with locations in the US, Europe, Canada and other non-target geographies. It is sorted alphabetically, so this first-20 slice does not determine the presence or total yield of software/AI roles later in the 226-job list. Do not infer a definitive relevant-job count.
- Assessment: collection endpoint works for this board, but the sample alone does not establish useful yield for the current target profile (software/full-stack/frontend/backend/Python/AI/LLM roles; Bengaluru, Gurugram, Delhi, Remote India). Keep `source_enabled.greenhouse=false` and `notifications_enabled=false`; do not activate Greenhouse from this evidence. Production and `main` untouched; preserve local `.venv/` untracked.
- No code/config changes; no CI or deployment performed. Next: if further source evaluation is approved, inspect a compact title/location summary of the entire Coinbase payload or a role-filtered count against configured targets, without starting the app/scheduler or writing the DB; otherwise consider the next existing board only after documenting the decision. This sample is not a scheduler/activation approval.
- Continuation: reread this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`; keep all source toggles and notifications disabled until relevant/new-job yield and operational safety are separately assessed.


## Coinbase full-payload relevance summary proposed — 2026-10-13
- User confirmed they pulled the latest `v2-live-radar` documentation updates. Local HEAD/pull output was not pasted, so this remains user-reported.
- Re-read the current handover, knowledge-transfer and JobBeeper reference docs, plus `v2/config.dev.json`. Config still shows Greenhouse disabled and notifications disabled; target locations are Bengaluru, Gurugram, Delhi and Remote India, with software/full-stack/frontend/backend/Python/Node/React/automation/AI/LLM roles.
- Based on the Coinbase sample (226 jobs returned; first 20 shown), the current evidence is insufficient to estimate engineering-role yield because output is alphabetically sorted. No code/config changes, matching, DB writes, scheduler run, notifications, CI or deployment occurred. Production and `main` untouched; preserve local `.venv/` untracked.
- Next exact action: run a single-GET, read-only analysis over the full Coinbase payload and report role-keyword, location-keyword, likely overlap and exclusions plus a small sample. This is a heuristic yield estimate only, not matcher output or proof of eligible jobs. Keep Greenhouse and notifications disabled; do not start the app/scheduler.
- Continuation: interpret counts conservatively; if role/location yield is weak or ambiguous, do not enable Greenhouse. Re-read this file, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` before any further source action.


## Coinbase full-payload keyword analysis reviewed — 2026-10-13
- User ran the documented single-GET read-only analysis and supplied output: 226 jobs fetched; 82 title keyword hits; 9 target-location keyword hits; 7 role+location overlap; 174 titles contained configured exclusion terms. The 25-title sample includes many senior/staff/manager roles, remote USA roles and one Machine Learning Engineer listing marked Remote - India posted 2026-06-22. These counts are heuristic and overlapping, not actual matcher output; overlap may include exclusions and stale listings. Do not treat 7 as eligible jobs.
- Assessment: Coinbase retrieval works, but apparent current-profile yield is low/uncertain and likely poor after 72-hour freshness and title exclusions. Keep `source_enabled.greenhouse=false` and `notifications_enabled=false`; do not enable based on this sample. No code/config change, matcher, DB write, scheduler, notifications, CI or deployment occurred. Production and `main` untouched; preserve local `.venv/` untracked.
- Next exact action: inspect the next already-allowlisted Greenhouse board, Graviton Research Capital, with one public GET and a compact title/location/posted/URL sample or role/location keyword summary. This is source evaluation only; do not start scheduler/app, write DB, run matching, or change source toggles.
- Continuation: compare its likely relevant and fresh yield against configured target roles/locations and exclusion terms. Keep Greenhouse and notifications disabled unless separately approved after evidence review. Re-read this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` before next substantive action.


## Graviton Research Capital yield sample reviewed — 2026-10-13
- User supplied a one-GET read-only sample from the existing allowlisted board `gravitonresearchcapital`; collector log: `boards=1 successful=1 failed=0 jobs=20`. The 20 returned listings include Application Reliability Engineer (Gurugram, posted 2026-09-04), Data Center Engineer (Noida, posted 2026-10-06), Machine Learning Researcher (Gurugram, posted 2026-03-10), Software Engineer (Gurugram, posted 2021-02-23), Software Engineer (2027 Graduate) (Gurugram, posted 2026-09-01), and Software Engineer- Python (Gurugram, posted 2025-09-01), among other roles. As of 2026-10-13, none of the displayed likely software/ML target examples demonstrates a posting within the configured 72-hour freshness window; the recent Data Center Engineer is not clearly a target software/AI role. The sample does not prove whether old postings are closed or still open.
- Assessment: structured retrieval works, but useful fresh-job yield for the configured profile remains unproven and appears weak in this sample. Combined with Coinbase and Zocdoc evidence, do not enable Greenhouse based on API accessibility or raw job count. Keep `source_enabled.greenhouse=false` and `notifications_enabled=false`; production and `main` untouched.
- Project status: core V2 architecture and several sources/integrations exist; remaining MVP-critical work is evidence-based fresh/relevant source yield, end-to-end matcher/deduplication/alert correctness, isolated dev verification, and safe production rollout/acceptance. Do not assign a completion percentage without a complete acceptance checklist and current runtime evidence.
- No code/config changes, matching, DB writes, scheduler startup, notifications, CI, or deployment occurred in this evaluation. Preserve local `.venv/` untracked.
- Next: stop evaluating low-yield boards by raw count alone; inspect source-posted timestamps and matcher eligibility for candidates using bounded read-only analysis, then prioritize sources/boards with demonstrable fresh India/Remote-India software/AI roles. Before the next local command, sync these docs with `git pull --ff-only origin v2-live-radar`. Keep all source toggles and notifications disabled unless separately approved.
- Continuation: reread this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`; review the overall acceptance checklist and decide the next evidence-gathering step without touching production or `main`.


## MVP fast-track plan — 2026-10-13
- User wants to launch the MVP soon and prefers focused, efficient delivery. Freeze scope around the existing core pipeline; defer experimental ATS expansion and non-blocking features. Keep Greenhouse, Ashby, and Instahyre disabled; keep development notifications disabled.
- Release gates: verify isolated dev runtime/health; run existing tests; inspect Naukri and source health; verify freshness, normalization, deduplication, match explanations, and notification idempotency through safe tests; verify production backups and persistent volume before any cutover; smoke-test and observe after an approved release.
- No code/config/runtime changes, service starts, DB writes, notifications, CI, or deployment occurred. Production and main untouched; preserve local .venv untracked.
- Next action: user runs read-only dev diagnostics from ~/job-beeper-dev: git status -sb; git log -1 --oneline; sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml ps; curl -fsS http://127.0.0.1:8001/health; sudo docker compose -p job-radar-dev -f v2/docker-compose.dev.yml logs --tail=60 radar. This diagnostic does not start/rebuild services or change toggles. Review results before choosing the next step.


## MVP decision rule and dev diagnostics — 2026-10-13
- **Mandatory scope rule:** Every task must either (1) remove a launch blocker, (2) verify a launch requirement, or (3) improve the usefulness of the MVP. If it does none of these, defer it. Apply this rule before starting work; state which of the three outcomes a proposed task serves. Do not expand scope just because a feature/source is available.
- User-provided read-only dev diagnostics: branch is `v2-live-radar`, HEAD `8992ac8` (`Record Graviton yield review`), aligned with `origin/v2-live-radar`; only `.venv/` is untracked. Dev container `job-radar-dev` is up for 30 hours on loopback `127.0.0.1:8001`; `/health` returned status `ok`, version `2.0.0`, DB `/data/jobs.db`. Naukri last success `2026-10-13T16:04:43.501022+00:00`, `jobs_seen=351`, `new_jobs=0`, `error=null`; recent logs show repeated successful polls with varying counts and occasional new jobs. A zero-new poll alone is not a failure.
- This verifies basic dev process/health and Naukri poll activity only; it does not prove freshness/relevance quality, matcher/dedupe correctness, notification idempotency, test-suite status, or production readiness. No tests, DB inspection, matching, notification, config changes, service restart, CI, or deployment occurred in this turn. Production and `main` remain untouched. Preserve `.venv/` as untracked.
- Next task under the decision rule: run the existing automated test suite in the dev checkout (launch requirement verification), then fix only actual test blockers. Keep source toggles and notifications unchanged/off in dev. After tests, verify one bounded path from stored jobs through freshness/eligibility/match explanations and notification-ledger safeguards using safe tests or read-only checks; then plan production backup/volume verification and cutover gates.
- Before the next local command, sync updated docs with `git pull --ff-only origin v2-live-radar`. Never start or alter production, enable Greenhouse/Ashby/Instahyre, or activate notifications without separate approval.


## Next MVP gate: run existing CI checks — 2026-10-13
- User confirmed the updated docs were pulled. This task verifies a launch requirement; unrelated work is deferred under the MVP decision rule.
- Current `.github/workflows/v2-ci.yml` specifies: `python -m py_compile v2/radar.py v2/test_radar.py v2/greenhouse_canary.py v2/test_greenhouse_canary.py`, then `python -m unittest discover -s v2 -p 'test_*.py' -v` after dependencies are installed. Agent has not run these commands on the VM.
- Next action: from `~/job-beeper-dev` in the active `.venv`, run both commands in that order and paste complete output, especially any traceback/failing test. Do not restart services, alter config, activate sources, send notifications, or touch production. Preserve `.venv/` untracked.


## Existing test suite passed — 2026-10-13
- User reports `python -m unittest discover -s v2 -p 'test_*.py' -v` completed with `Ran 100 tests in 19.302s` and `OK`. This is user-supplied evidence; the agent did not execute the suite on the VM and has not seen the full output.
- This verifies the existing unit-test suite only; it does not prove live source relevance/freshness, end-to-end matching/deduplication, notification idempotency, or production readiness. No code/config/service/production changes were made in this turn.
- Next exact action: confirm the preceding CI compile check also passed: `python -m py_compile v2/radar.py v2/test_radar.py v2/greenhouse_canary.py v2/test_greenhouse_canary.py`. If not yet run, execute it from `~/job-beeper-dev` with `.venv` active and report output. Then continue with a bounded safe review of MVP acceptance gates, not feature expansion. Keep experimental sources and dev notifications disabled; preserve `.venv/` untracked; do not touch `main` or production.


## MVP test gate passed and next-agent contract — 2026-10-13
- **Goal clarity:** ship a dependable, low-noise Job Radar MVP that discovers fresh India/Remote-India software/AI roles, preserves truthful timestamps and stable IDs, deduplicates opportunities, explains deterministic match decisions, and sends only eligible new matches reliably. Do not confuse raw source count or a healthy process with useful job yield or launch readiness.
- **Mandatory task filter:** before any task, explicitly state whether it removes a launch blocker, verifies a launch requirement, or improves MVP usefulness. If none apply, defer it. Freeze scope; do not add features or expand source coverage without evidence that it serves one of these outcomes.
- **User-provided verification (2026-10-13):** from `~/job-beeper-dev` with `.venv` active, `python -m py_compile v2/radar.py v2/test_radar.py v2/greenhouse_canary.py v2/test_greenhouse_canary.py` completed with no error output; user then ran `git pull --ff-only origin v2-live-radar`, so compile is treated as passed based on shell flow. The pull fast-forwarded local origin tracking from `a3034cb` to `1284b0a` and updated only the two handover docs. User reports `python -m unittest discover -s v2 -p 'test_*.py' -v` completed with `Ran 100 tests in 19.302s` and `OK`. These are user-supplied results; agent did not execute commands on the VM.
- **What is achieved / current position:** basic isolated dev runtime and health previously verified; Naukri polling observed with no reported error; compile check passed; existing test suite passed (100 tests). Greenhouse two-poll checks established ID/timestamp stability for sampled boards but source samples did not establish strong fresh target-role yield, so Greenhouse remains disabled. This is meaningful progress, not a declaration of production readiness.
- **Still unverified launch gates:** actual freshness/relevance yield for the target profile; end-to-end normalization and cross-source deduplication; matcher eligibility/explanations and exclusions; notification-ledger idempotency/no historical replay; backup and persistent-volume identity; production cutover, post-cutover smoke test, and 24–72-hour observation. Do not claim these passed without evidence.
- **Next action:** no need to rerun the 100 tests unless code changes or a failure warrants it. After syncing the newest documentation, review the existing tests and code paths for the next single MVP-critical gap, preferring safe tests or read-only inspection of freshness → normalization/dedupe → deterministic match → notification ledger. Do not inspect/write the live DB or send alerts unless the selected check explicitly requires it and is separately approved. Ask the user to run only the specific copy-paste commands needed and review the complete output before proposing a fix.
- **Safety:** do not restart/rebuild the dev container unless diagnostics prove it necessary; do not touch `main` or production; do not enable Greenhouse, Ashby, Instahyre, Gemini shadow extraction, or notifications without explicit separate approval. Preserve `.venv/` as local untracked. No code/config/service/database/notification/deployment changes were made in this verification turn.
- **Required update contract for every future agent:** before substantive work, read this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` on `v2-live-radar`. At the end of every turn, update BOTH this handover and knowledge transfer, even for evidence-only/no-code turns. Each update must carry forward (1) product goal and MVP decision rule, (2) what was achieved, (3) exact evidence and whether user-reported or independently verified, (4) current branch/runtime/deployment state when known, (5) paths/commits/tests/CI/deployment status, (6) what deliberately did not change, (7) unresolved acceptance gates and risks, (8) one exact next action with copy-paste commands and expected output, (9) a continuation prompt for the next agent. Update the reference doc only when architecture/engineering guardrails change. Fetch latest full content and blob SHA before each sequential documentation write, then re-fetch both files to verify notes. Never claim a command, test, or deployment was run unless its output proves it.
- **Next-chat instruction:** the next model must read the three documents first and use them as the source of truth, not rely on chat history. The user wants practical, concise assistance: provide only the exact commands to run and a brief explanation of what output to paste; put broader project context and history in the handover docs. One task at a time, evidence first, no speculative changes.
- **Before the next local command:** pull the newest docs because this note was committed after the user's reported pull: `git pull --ff-only origin v2-live-radar`. Then run only the selected read-only/test-based MVP verification command(s), and paste full output.


## MVP acceptance review — 2026-10-13 (current agent turn)
- **Product goal:** deliver a reliable, low-noise Job Radar MVP for fresh/relevant India and Remote-India software/AI jobs, with truthful timestamps, stable IDs, canonical cross-source dedupe, deterministic/explainable matching, and safe alert delivery.
- **Mandatory scope rule:** every task must remove a launch blocker, verify a launch requirement, or improve MVP usefulness; otherwise defer it. This turn serves **verification of a launch requirement**.
- **Documents reviewed:** this handover, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` were fetched from `v2-live-radar` via GitHub on 2026-10-13. The previously fetched blob SHAs were handover `6c896ed39f581eae5925c2e3552dbc35391054b2`, knowledge transfer `18ed2193b65a3360d36035aea3576f05c8c6bb4d`, reference `1d06ece64cc5abe296953776a79dedf654b95485`. Raw URL fetches returned 404, but GitHub repository-file retrieval on the specified branch succeeded.
- **Current evidence (user-reported, not independently run on VM):** development checkout is `~/job-beeper-dev`, branch `v2-live-radar`; `127.0.0.1:8001/health` was healthy, Naukri polling had no reported error, compile check completed without errors, and existing tests reported 100 passed in 19.302 seconds (`OK`). Greenhouse board samples demonstrated basic two-poll ID/timestamp stability but not useful fresh target-profile yield. The agent did not run these commands on the user's VM.
- **Most important remaining MVP acceptance gap:** demonstrate actual **fresh and relevant job yield for the target profile**. Process health and total jobs seen do not prove the feed is useful. End-to-end normalization/dedupe, deterministic match reasons/exclusions, notification-ledger idempotency/no historical replay, production backup/volume identity, and approved cutover remain unverified.
- **What changed / deliberately unchanged:** documentation only; no application code, configuration, DB, service, scheduler, source enablement, notification, CI, deployment, `main`, or production change. Keep Greenhouse/Ashby/Instahyre and development notifications disabled. Preserve local `.venv/` as untracked and never delete or commit it.
- **Next exact action:** user must synchronize the newly updated handovers before any further local command: `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`. Expected output is a fast-forward (or “Already up to date”) with handover-doc changes only; paste the complete output. After confirming sync, select one bounded read-only/test-based check of fresh/relevant yield without rerunning the passing suite, mutating the DB, restarting containers, or sending notifications.
- **Continuation instructions:** read all three documents on `v2-live-radar`; work one issue at a time; provide copy-paste commands and briefly state purpose/expected output; review returned evidence before deciding next step. At every turn end, update both handovers sequentially using freshly fetched content/blob SHA and verify both updates. Do not touch `main` or production without explicit approval.


## User confirmed handover sync; next read-only yield audit — 2026-10-13
- **Product goal / scope rule:** prove useful, fresh India/Remote-India software/AI job discovery for the target profile. Every task must remove a launch blocker, verify a launch requirement, or improve MVP usefulness; this task verifies the fresh/relevant-yield launch gate.
- **User-reported evidence:** user ran `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`; it fast-forwarded local tracking from `f2ed8b5` to `566e6f5`, changing only `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` (22 insertions). This confirms the previous documentation updates are synced locally.
- **Next action:** run a bounded read-only audit against the isolated dev API on `127.0.0.1:8001`: fetch `/api/daily-summary`, `/api/source-status`, and `/api/jobs?today_only=true&limit=100`; print only aggregate counts and selected job fields (source/title/company/location, posted/discovered timestamps, match score/reasons, alertable/status) so no URLs or secrets are exposed. This checks whether today's feed has fresh, relevant target-profile yield and shows its existing persisted decisions; it must not trigger matching, mutate the DB, or send notifications.
- **Expected output:** JSON summary, source enabled/last-run/new-job/error status, and a compact list of today's observed jobs. A lack of today's jobs is evidence to investigate, not proof of a code defect. Paste the complete output for review.
- **Known state / unchanged:** user previously reported dev health OK, Naukri polling without error, compile clean, and 100 tests passing in 19.302s; not independently executed by agent. Do not rerun passing tests without a reason. Keep Greenhouse/Ashby/Instahyre and dev notifications disabled; do not restart/rebuild services or touch production/main. Preserve `.venv/` untracked. Fresh/relevant yield, cross-source dedupe, deterministic matcher explanations, notification-ledger idempotency/no replay, production backup/volume identity and approved cutover remain open gates.
- **Continuation:** review full audit output before selecting the next step. At every turn end, update both handovers sequentially after fetching current content/blob SHA, then refetch and verify. Ask the user to pull updated docs before their next local command.


## 2026-10-13 — Read-only API audit command correction
- User attempted the previously supplied audit snippet, but the shell reported `python: command not found`; the pasted command also appears duplicated/corrupted. There is no audit output yet, so no API/DB/source/yield conclusions can be drawn.
- Supplied a clean heredoc version using `python3`, querying only `/api/daily-summary`, `/api/source-status`, and `/api/jobs?today_only=true&limit=100` from the isolated dev API at `127.0.0.1:8001`. It prints selected job fields and catches request errors. This is read-only; it does not trigger matching, alter the DB, send notifications, enable sources, or restart services.
- **Next:** wait for the complete output. If connection refused/timeout, report the exact error and diagnose service status without restarting anything. If output is returned, assess timestamps, relevant yield, source status, persisted matcher explanations and notification state. Do not treat no jobs in a day as proof of a defect.
- Keep all existing guardrails: no production/main changes or cutover without explicit approval; keep Greenhouse/Ashby/Instahyre and development notifications disabled; preserve `.venv/` untracked. After these docs are updated, user must `git pull --ff-only origin v2-live-radar` before the next local command.


## 2026-10-13 — Read-only audit results received
- User supplied output from the isolated dev API audit. Daily summary: 523 jobs discovered, 16 matched, 0 alertable, 0 alerts sent. Naukri enabled; latest run 2026-10-13T17:20:06.355539+00:00, 357 jobs seen, 2 new, no reported error; LinkedIn/Instahyre/Greenhouse disabled. These are user-provided runtime results, not independently observed by agent.
- The 100 returned job rows contain some profile matches (examples include Java React Developer, Python Developer (Django + AWS), Software Engineer) but all shown matching rows are non-alertable because Telegram notifications are disabled. Keep notifications disabled; zero alerts is consistent with the current safety configuration.
- Visible Naukri `source_posted_at` values are consistently `2026-10-13T00:00:00+00:00`; discovery timestamps have finer precision. This may be date-only source precision or normalization behavior and is not yet explained. Need inspect more rows and the source adapter/parser before making a claim.
- The API caps `/api/jobs` and `/api/opportunities` at 500 rows. Code review confirms `/api/jobs` reads persisted evaluations and ledger fields without re-running the matcher; `/api/opportunities` aggregates canonical opportunity observations and source counts. Next safe diagnostic: after pulling docs, run a read-only Python 3 audit of `/api/jobs?today_only=true&limit=500` and `/api/opportunities?today_only=true&limit=500`, print aggregate match/alert/source/timestamp statistics and canonical opportunity observation/source-count distributions only (no canonical URLs). This should quantify the timestamp pattern and existing cross-source aggregation without DB mutation or notification side effects.
- Do not infer cross-source dedupe success merely from canonical opportunity aggregates; currently only Naukri is enabled, so live cross-source evidence may be absent. No code/config changes, matching run, notification, or service restart was performed.
- Guardrails unchanged: keep Greenhouse/Ashby/Instahyre and notifications disabled; preserve `.venv/` untracked; no production/main changes or cutover without explicit approval. Pull latest branch docs before the next local command.


## 2026-10-13 — Expanded job/canonical audit reviewed
- User-provided read-only audit returned 500 jobs, all Naukri; 484 had `likely_match=false`, 16 true; all 500 had `alertable=false`; notification status was `suppressed` for 484 and `pending` for 16. These are ledger states, not evidence that an alert was sent. Next inspect persisted alertability and notification decision reasons for the 16 pending records before interpreting the apparent discrepancy.
- The first 500 canonical opportunity records all had `source_count=1` and `observation_count=1`. Because the source status showed only Naukri enabled, this cannot verify cross-source dedupe and is not by itself evidence of a dedupe defect.
- Reviewed `v2/radar.py` Naukri adapter: it parses the relay's `posted` field and passes `posted_precision="date"` when a date is present, else `unknown`. It uses relay `updated_at` as collection/discovery time. Thus midnight UTC timestamps fit date-only precision and do not alone prove artificial time or broken freshness. Need inspect persisted `posted_precision` distribution and relay's freshness only if needed.
- Next safe action: after syncing these notes locally, run a read-only API aggregation over `/api/jobs?today_only=true&limit=500` to count `posted_precision`, group `alertability_reasons`, `notification_decision_reasons`, and `notification_status`, and summarize those fields for the 16 matched rows. Do not print URLs, run matching, mutate the DB, enable sources, send notifications, or restart services.
- Guardrails unchanged: keep Greenhouse/Ashby/Instahyre and development notifications disabled; preserve `.venv/` untracked; no production/main changes or cutover without explicit approval. Pull latest branch before next local command.


## 2026-10-13 — Alertability and posting precision diagnostic
- User-provided read-only diagnostic for today's first 500 rows: `posted_precision` was `date` for all 500. No minute-precision timestamps in this sample, so exact posting-time freshness cannot be established from these records; midnight UTC is consistent with date-only precision.
- Alertability reasons: 484 `not a profile match`, 16 `Telegram notifications disabled`. Notification decision reasons: 484 `no profile-matching observation`, 16 `Telegram notifications disabled; awaiting future re-evaluation`. All 16 matched records remain `pending`; this is expected with Telegram disabled and does not indicate sent alerts.
- Next safe diagnostic: inspect only the 16 matched rows' title, company, location, match score/reasons, experience fields, discovery time, posting precision, and alertability/notification reasons. Do not print URLs or full descriptions. Goal is to assess target-profile fit and explainability without changing matcher, config, DB, or notification state.
- Guardrails unchanged: sources Greenhouse/Ashby/Instahyre and dev notifications stay disabled; preserve `.venv/` untracked; no production/main changes or cutover without explicit approval. Pull latest branch before next local command.


## 2026-10-13 — Matched-job quality review
- User-provided matched-row output showed 16 profile matches with scores 70–100; all remain pending/non-alertable solely because Telegram is disabled. All posting timestamps have date precision, so exact posting time/freshness remains unverified.
- Four separate records share company/title/location `Accenture / Custom Software Engineer / Bengaluru, India`, with scores 70, 76, 76, 82 and different discovery times. This may represent distinct postings or duplicate relay/query records; output did not include source IDs or canonical IDs, so do not conclude dedupe failure yet.
- Matched rows show `experience_min`, `experience_max`, and `experience_text` as null even though `match_reasons` contain phrases such as candidate 2 years/job 2+. Determine whether matcher uses other fields or API projection is not exposing the extracted values.
- Next safe action: read-only API check for repeated company/title/location groups, output only stable `source_job_id`, canonical opportunity ID, canonical match method/confidence, match score/reasons and available experience fields; never print URLs/descriptions. Preserve source/notification guardrails; no code/config/DB/notification changes without evidence and approval.
- Both handover docs updated on `v2-live-radar`; pull latest before next local command. No production cutover.


## 2026-10-13 — Repeated identity audit results
- **Goal / scope rule:** verify canonical dedupe and matcher reliability for the MVP; this is a launch-requirement audit. User supplied output from a read-only grouping of `/api/jobs?today_only=true&limit=500`; the agent did not run it against the VM.
- **Key evidence:** 15 repeated company/title/location groups, covering 206 rows in the displayed groups. The largest is `Accenture / Custom Software Engineer / Bengaluru, India` with 172 rows. In the supplied output, those 206 rows have 206 distinct `source_job_id` values and 206 distinct `canonical_opportunity_id` values; every shown `canonical_match_method` is `new` and confidence is 0. Several rows discovered in the same poll timestamp have different source IDs and distinct canonical IDs. This is a strong signal of possible query-variant/source-relay duplication or an overly strict canonical identity key, but the output alone does not prove all are the same underlying vacancy. Do not merge records or change dedupe logic without inspecting identity inputs and source adapter/query behavior.
- **Additional evidence:** `experience_min`, `experience_max`, and `experience_text` are null across the displayed rows, while match reasons refer to specific experience thresholds (for example, minimum 3, 5, 7.5, 12, or 15 years) and compatibility. The API projection may not expose the fields used by the matcher, or those values may be derived elsewhere; verify schema and matcher inputs before drawing a conclusion.
- **What changed / unchanged:** docs only. No app code, config, database, service, source toggles, notifications, CI, deployment, `main`, or production changes. Keep Greenhouse/Ashby/Instahyre and dev notifications disabled; preserve local `.venv/` untracked.
- **Next exact action:** pull updated docs, then run a bounded read-only audit against the local dev API/database schema to compare repeated IDs with the actual source identity fields, raw normalized title/company/location, canonicalization key inputs, and relay/query provenance. Avoid printing URLs or full descriptions. Inspect existing code first to determine the smallest safe diagnostic; do not run any write operation or trigger polling.
- **Expected interpretation:** distinct source IDs alone are not proof of distinct vacancies. If the Naukri relay exposes the same underlying listing through multiple query variants with distinct IDs, fix identity upstream only after confirming a reliable stable source key. If IDs represent genuinely separate requisitions, preserve them.
- **Continuation prompt:** investigate possible duplicate Naukri ingestion/canonicalization and the experience-field/API-projection discrepancy, evidence first; no code fix until root cause is established. Keep production untouched.
- **Before next local command:** `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`.


## 2026-10-13 — Source inspection command fallback
- User successfully pulled the latest `v2-live-radar` handover updates. The planned source inspection stopped immediately because `rg` (ripgrep) is not installed; no source-code inspection or application change occurred.
- Use standard `grep -n -E -C 3` instead of installing a package. Inspect canonical identity/dedupe and experience extraction/matching in `v2/radar.py`; output should be reviewed before any proposed code changes.
- Next exact user action: run the equivalent read-only grep command from `~/job-beeper-dev`, paste complete output, then diagnose identity inputs and API experience-field projection. Do not mutate the database, trigger polling, enable sources/notifications, restart services, or touch production/main.
- Docs-only update; preserve `.venv/` untracked. User must pull latest docs before any later local command if another docs update occurs.


## 2026-10-13 — Canonical and experience code-path inspection
- User supplied read-only grep output from `v2/radar.py`.
- Canonical identity implementation is imported from `v2/dedupe.py`: `auto_link_allowed`, `canonical_identity`, `canonical_match_score`, and `canonicalize_url`. `ensure_canonical_opportunity` returns an existing canonical ID if present; otherwise it scores candidates and links only when `auto_link_allowed(best_score, best_method)` is true. If not linked, the code creates a new canonical opportunity. Inspect `v2/dedupe.py` and the surrounding candidate-selection/creation block before proposing a change.
- `rebuild_canonical_opportunities` clears canonical IDs and deletes the notification ledger before rebuilding; do not run or recommend it casually because it is destructive to notification state.
- Experience fields are persisted in `job_evaluations.experience_min_years/max_years`, populated from matcher `details`, and exposed by `/api/jobs` through aliases `evaluation_experience_min_years/max_years`. User-observed matched rows had compatibility reasons but null experience values. Root cause remains unconfirmed; investigate persistence/evaluation refresh and exact SQL projection before changes.
- Next read-only local inspection: `grep -n -E -C 5 'def canonical_identity|def canonical_match_score|def auto_link_allowed|def canonicalize_url|ensure_canonical_opportunity|INSERT INTO canonical_opportunities|evaluation_experience_min_years|def evaluate_job|def evaluate' v2/dedupe.py v2/radar.py`, plus a focused view of the complete `ensure_canonical_opportunity` function. Do not print URLs or descriptions from job data.
- No application code, runtime, database, notification, or production changes were made. Before next local command, pull docs with `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`.


## 2026-10-13 — Deduplication restriction confirmed from source
- Latest user-provided grep output shows `auto_link_allowed(score, method)` requires score >= 95 and method != "none". In `_assign_canonical`, a candidate from the same source is skipped when its canonical URL differs from the incoming job's normalized URL. `canonical_match_score` gives exact canonical URL score 100; metadata-description/probable scores are 93/88. Consequently, same-source records with different canonical URLs cannot link through this candidate loop, even if company/title/location are the same. This is a confirmed code behavior and a plausible cause of the repeated Naukri groups, not proof that every repeated row is the same vacancy.
- Do not loosen the threshold or merge records yet. First inspect `v2/dedupe.py` in full and perform a read-only, privacy-safe sample comparison of source IDs and canonical URL shapes for the Accenture group (do not print full URLs or descriptions); establish whether distinct URLs are variants of the same vacancy or distinct postings.
- Experience nulls are not necessarily a defect: `match_details` may add candidate/configured-profile compatibility reasons when the job's explicit experience range is unknown. Null stored job-experience values alone do not prove a persistence or API projection bug.
- Next local command should inspect `v2/dedupe.py` and matcher logic around lines 1790–1895, then design a safe audit; no database writes, source/notification enablement, rebuilds, restarts, or production changes.
- Both handover documents must be pulled before subsequent local commands: `cd ~/job-beeper-dev && git pull --ff-only origin v2-live-radar`. No application code or runtime changes made.


## 2026-10-13 — Full dedupe rules and experience semantics reviewed
- Full `v2/dedupe.py` output confirms canonical URL equality scores 100; same-source candidates are skipped before scoring when canonical URLs differ in `_assign_canonical`. Metadata matching requires company and normalized location equality and title similarity >= 0.88; explicit different experience signatures reject a candidate; identical experience can score 95/98; metadata-description can score 97 or 93; probable metadata scores 88. Auto-link threshold is >=95.
- Safe next step: inspect `_candidate_canonical_groups`, `_job_for_canonical`, and insertion/assignment call sites. Then audit a limited repeated-title/company/location sample without printing full URLs/descriptions; compare host/path shape or hashed URL identity, source IDs, normalized metadata, descriptions' token similarity, experience signatures, and discovery timestamps. Do not infer that every repeated title is a duplicate.
- Experience matcher adds “experience compatible” only when an experience range is detected; its returned range and reasons are persisted together by `_persist_job_evaluation`. A record with a saved reason that explicitly cites a job range but null stored range may reflect stale/inconsistent evaluation data or a different evaluation lifecycle; the current snippets alone do not establish which. Inspect the same records' `evaluated_at`, `config_fingerprint`, and stored evaluation row via read-only query before any repair.
- No code/config/database/runtime/notification changes. Never run `rebuild_canonical_opportunities` as a diagnostic because it deletes notification ledger rows. Pull latest docs before the next local command.


## 2026-10-13 follow-up: canonical candidate selection and evaluation lifecycle

### Evidence received
- The displayed excerpt of _candidate_canonical_groups() shows candidate selection using canonical URL when the incoming job has a normalized URL; the excerpt does not include the complete fallback/query logic.
- _assign_canonical() skips a candidate when it has the same source as the incoming job and a different canonical URL. Therefore same-source listings cannot be linked by metadata similarity alone in that branch. This is a confirmed code limitation and a plausible contributor to repeated Naukri company/title/location groups, but it does not prove those rows are the same real vacancy.
- _persist_job_evaluation() calculates match_details() and alertability_details(), then persists reasons and experience bounds in the same upsert. refresh_job_evaluations() re-evaluates only rows with no evaluation or a different config fingerprint. backfill_job_evaluations() fills only missing evaluations.
- A persisted match reason that states a specific experience range while the same evaluation row has null experience bounds needs record-level verification; do not assume API mapping is the root cause.
- Do not run rebuild_canonical_opportunities() as a diagnostic: the inspected implementation deletes notification-ledger rows while rebuilding canonical groups.

### Next read-only verification
1. Inspect the full _candidate_canonical_groups() implementation (around lines 527–575) to understand URL and metadata candidate selection.
2. Inspect representative persisted job/evaluation rows together: job ID, source, company/title/location, source URL host/path only (avoid printing full URLs), evaluation timestamp, config fingerprint, reasons JSON, and persisted experience bounds.
3. Compare each suspicious record's stored evaluation with a fresh in-memory match_details(job, config) result without persisting it. If the stored row and fresh result differ, investigate evaluation refresh/config lifecycle; if both are null but reasons claim a range, inspect parsing and the exact job payload.
4. No code fix or dedupe rebuild until candidate query semantics and real-vacancy evidence are understood. Keep Naukri/other canaries and notifications disabled as currently guarded.

### User-provided terminal evidence
The user supplied grep output from the dev checkout showing _persist_job_evaluation() upserts reasons_json, experience_min_years, and experience_max_years together; refresh_job_evaluations() compares config_fingerprint; and canonical assignment includes the same-source/different-URL skip described above. These are terminal excerpts, not independently executed tests by the assistant.


## 2026-10-13 follow-up: full candidate query and API evaluation fields

### Additional user-provided source excerpts
- _candidate_canonical_groups() first queries canonical_opportunities by exact normalized canonical URL and returns those rows if found. If none are found, it falls back to groups with matching company_norm and location_norm, ordered by last_seen_at descending, limited to 100.
- _assign_canonical() then skips any candidate whose representative source matches the incoming job source unless canonical URLs match. This means the company/location fallback does not enable same-source metadata matching when URLs differ. This strengthens the hypothesis that same-source query-variant Naukri results may form separate groups, but does not establish that every repeated listing is the same vacancy.
- /api/jobs selects persisted job_evaluations fields and maps evaluation_experience_min_years / evaluation_experience_max_years to the response. The handler explicitly documents that it returns the persisted matcher/ledger decisions rather than independently running the matcher at request time.
- The displayed matcher excerpt returns experience_min_years and experience_max_years alongside reasons. _persist_job_evaluation() upserts those values and reasons_json together. Thus a saved reason naming a specific range with null saved bounds warrants a record-level comparison between the stored evaluation and a fresh in-memory match_details() result.

### Next safe step
Use a read-only SQLite/Python diagnostic against the isolated dev database. For a small sample of suspicious job IDs, print only job ID, source, company/title/location, URL host/path (not query strings or full URLs), evaluation timestamp, fingerprint prefix, saved reasons, and saved experience bounds; then compute match_details() in memory using the same loaded config and compare results without calling _persist_job_evaluation(). Do not update evaluations, rebuild canonical groups, or alter the notification ledger during this diagnostic.


## 2026-10-13 follow-up: diagnostic command did not run

- User pulled the latest branch successfully, but the read-only diagnostic stopped immediately because Ubuntu has no `python` command (`python3` is available per the shell hint). The Python diagnostic itself did not execute, so no result was produced and no database mutation occurred.
- Next attempt should prefer the already-existing project interpreter at `.venv/bin/python` if executable; otherwise use `python3`. Do not install packages or change the environment solely to address the command alias. Preserve `.venv/` as untracked and never delete or commit it.


## 2026-10-13 follow-up: read-only SQLite diagnostic could not open DB

- User successfully ran the diagnostic with the existing project interpreter at /home/ubuntu/job-beeper-dev/.venv/bin/python.
- The app reports DB_PATH as /home/ubuntu/job-beeper-dev/v2/jobs.db, but sqlite3.connect(file:...jobs.db?mode=ro, uri=True) failed immediately with OperationalError: unable to open database file. No rows were read, the fresh matcher comparison did not run, and no database writes occurred.
- Next step is filesystem-only verification: check whether the DB path exists and is a regular file, inspect parent directory permissions and the configured DB_PATH source. Do not create the DB, change permissions, copy databases, or fall back to a different DB until the path/runtime setup is understood. Keep the next diagnostic read-only.


## 2026-10-13 follow-up: expected DB file absent from checkout

- User ran the filesystem diagnostic after pulling the latest branch. The repository checkout directory and v2/ directory are accessible, but `v2/jobs.db` does not exist in the checkout. Because the command used `&&`, `stat` and the DB_PATH grep did not run. The earlier import printed `radar.DB_PATH` as `/home/ubuntu/job-beeper-dev/v2/jobs.db`; SQLite's read-only open error is consistent with that file being absent, though the intended live DB may be elsewhere (for example, in a container-mounted path).
- Do not create a DB, change permissions, or point diagnostics at a guessed file. Next step: read the DB_PATH definition, search only the checkout for SQLite files, inspect running app/container process metadata, and check whether Docker is available. Avoid environment dumps or printing secrets. Only after locating the actual isolated dev DB should the read-only evaluation comparison be retried.


## 2026-10-13 follow-up: checkout DB absent; live process discovery

- User's latest read-only diagnostics show `v2/radar.py` defines `DB_PATH = Path(os.getenv("JOB_RADAR_DB", ROOT / "jobs.db"))`; no `.db`, `.sqlite`, or `.sqlite3` files were found within five levels of the checkout. Two Uvicorn processes run `/usr/local/bin/python3.12 /usr/local/bin/uvicorn v2.radar:app --host 0.0.0.0 --port 8000` (PIDs reported as 157883 and 165424). Docker API access returned permission denied for the current user.
- This supports the conclusion that the prior diagnostic targeted a missing checkout-relative database; it does not identify the live DB path or establish whether the service uses `JOB_RADAR_DB`. Next safe step is to inspect each process's `/proc/<pid>/cwd`, command line, and only the `JOB_RADAR_DB` environment entry, then request the local `/health` endpoint on port 8000. Do not dump full process environments, use sudo, alter permissions, restart services, create/copy a DB, or guess the database location.


## 2026-10-13 follow-up: live health confirms container DB path

- User's latest `/health` output from `http://127.0.0.1:8000/health` reports `status=ok`, `version=2.0.0`, and DB path `/data/jobs.db`. It reports Naukri last success `2026-10-13T17:46:27.677899+00:00`, 355 jobs seen, 0 new, no error; LinkedIn is not running and has a rate-limit cooldown. Treat these as user-provided runtime observations, not independently verified.
- Reading `/proc/<pid>/cwd` yielded no path, and process environments were not readable for the current user, so `JOB_RADAR_DB` remains unconfirmed. Do not access `/data/jobs.db` as a host path or assume it is available in the checkout. Docker socket access remains denied.
- Next safe step: inspect repository runtime manifests and `/api/jobs` route parameters to determine whether the intended isolated dev service exposes enough persisted evaluation data through its local API, and how the container volume maps to host storage. Keep reads bounded and redact job URLs/descriptions. Do not use sudo, restart, rebuild, create/copy databases, or write to the DB.


## 2026-10-13 follow-up: why DB-path investigation is part of matcher audit

- User asked whether locating the database is part of the process. Clarify that it is only a prerequisite to the active launch-gate investigation, not a separate product task: determine whether persisted job evaluation experience bounds/reasons match a fresh in-memory `match_details()` result, and investigate potentially irrelevant skill reasons without writing to the DB.
- User-provided source inspection confirms `GET /api/jobs` joins `jobs`, `job_evaluations`, and `notification_ledger`, then returns persisted evaluation decisions rather than re-running the matcher. The runtime manifests `v2/docker-compose.yml`, `v2/docker-compose.dev.yml`, and `v2/Dockerfile` all set `JOB_RADAR_DB=/data/jobs.db`. The live `/health` endpoint reports `/data/jobs.db`; checkout-relative `v2/jobs.db` is absent. Docker socket access is denied, so direct host-side DB inspection is not currently available.
- Next step should be narrowly focused: inspect the dev compose file and the read-only API output shape, then choose the least-invasive way to compare a few specific persisted evaluations against fresh in-memory matcher output in the same isolated dev runtime. Do not alter DB, restart/rebuild, use sudo, or expose full job URLs/descriptions. No diagnosis or fix has been established yet.


## 2026-10-13 follow-up: user prioritizes shipping experience parser fix

- User explicitly asks to move quickly and ship the experience-parser fix to production, preferring a minimal/smart path over extended investigation.
- Current evidence only establishes the runtime DB path and that `/api/jobs` returns persisted evaluations. It does not establish the exact code diff, whether the parser fix is committed/pushed, whether targeted tests pass, or whether production deployment is approved. Keep the path short: inspect `git status` and diff for parser/matcher/test files, run the narrow relevant tests, push only the verified fix to `v2-live-radar`, and report the exact commit. Do not deploy/cut over production without explicit approval; do not touch production DB or trigger historical notification replay. Note dev Compose uses port 8001 and a separate `radar-dev-data` volume; prior health response on port 8000 is not proof of the dev instance.


## 2026-10-13 follow-up: worktree check for experience parser release

- User's latest `git status --short --branch` shows `v2/config.json` modified and `.venv/` untracked; neither is an experience-parser code change. Preserve both, especially `.venv/`, and do not stage or commit config. `git diff -- v2/radar.py v2/test_radar.py` is empty.
- Existing `v2/test_radar.py` contains experience-related tests around lines 1754-2200, but this output alone does not prove the production fix is present or passed. The recent commit list is dominated by handover-document commits, so inspect `git log --oneline -- v2/radar.py v2/test_radar.py`, identify the test class names, and run targeted parser/matcher tests before deciding whether any code change is needed. Do not push docs-only commits as if they were the parser fix; no production deployment yet.


## 2026-10-13 follow-up: full test suite passed; verify exact parser fix

- User reports `python -m unittest v2.test_radar` completed successfully: 88 tests in 10.552s, `OK`. This is current branch test evidence, but does not alone prove the intended experience-parser fix is included.
- `git status --short --branch` showed only user-local `v2/config.json` modification and untracked `.venv/`; preserve both and never stage either. No diff for `v2/radar.py` or `v2/test_radar.py`. Recent code history includes commit `cd3a8a6` titled `Detect more skill-specific experience phrases for shadowing`, whose relevance to the user-requested production experience-parser fix must be checked before claiming readiness.
- Next fast path: inspect `git log --all --oneline --grep='experience\|parser'` and `git show --stat`/diff for `cd3a8a6`, then identify whether the exact matcher/parser fix and a regression test exist. Do not create a docs-only release commit or deploy production without verifying the intended code change. No production cutover or database changes.


## 2026-10-13: Production Gemini JD-experience parsing issue

- User clarifies the release goal: production still reports `experience not stated` when JD text contains an experience requirement, despite a Gemini-based JD parsing development they made; they want that development promoted to production.
- Commit `cd3a8a6` (`Detect more skill-specific experience phrases for shadowing`) only changes the regex used for skill-specific shadow extraction in `run_source`; it does not alone demonstrate that Gemini extraction feeds the persisted matcher fields in production.
- Full current test run reported by user: `python -m unittest v2.test_radar` — 88 tests, 10.552s, `OK`. Still must establish that these tests cover the Gemini path and its persistence into `experience_min_years` / `experience_max_years` and saved evaluation records.
- Next action: inspect local history and current implementation for Gemini JD experience extraction, its invocation, persistence, and config gating. Preserve local `v2/config.json` modification and untracked `.venv/`; do not stage either. Keep Telegram disabled in dev and do not replay historical alerts. User explicitly wants production promotion, but deploy only after identifying the actual code path and passing targeted regression checks; verify the production image/commit and health after rollout, without altering the production DB.


## 2026-10-13: Root cause narrowed to shadow-only Gemini path

- User's current code search shows `v2/radar.py` imports `shadow_extract_jobs, shadow_status` from `v2.gemini_extractor`; normal `match_details` at approximately lines 1808–1813 uses `jd_experience_min_years`/`jd_experience_max_years`, then regex extraction. The Gemini call is around lines 2664–2715 in the source-ingestion path and is explicitly described as shadow-only.
- This explains why Gemini shadow output can exist without populating the normal matcher’s persisted `experience_min_years`/`experience_max_years` fields; must inspect `v2/gemini_extractor.py` output schema, validation, and cache/persistence before implementing the smallest safe promotion.
- Current branch test run reported by user: 88 tests pass. Worktree has modified `v2/config.json` and untracked `.venv/`; preserve both and never stage them. No parser code diff in worktree. Do not deploy until the validated Gemini result is wired into matching and targeted regression tests pass. Keep historical alert replay disabled and do not alter production DB.


## 2026-10-13: Latest VM output confirms Gemini remains shadow-only; check branch promotion

- User's uploaded command output confirms `run_source` labels Gemini deliberately shadow-only and calls `shadow_extract_jobs` before `upsert_jobs`/`refresh_job_evaluations`; normal `match_details` reads `jd_experience_min_years` / `jd_experience_max_years` and regexes only. Thus shadow extraction does not populate the production matcher path in the shown code.
- The `--all` history also shows `58fdff1` on `origin/main` merging PR #36 and `9b9cbf1` `Fix LinkedIn labeled experience extraction before alert decisions`; do not assume those commits are in `v2-live-radar`. Next inspect `v2/gemini_extractor.py` validation/result/cache and check whether `58fdff1` is an ancestor of current HEAD before deciding the minimal promotion.
- User's full suite report remains 88 tests passing. Worktree still has modified `v2/config.json` and untracked `.venv/`; preserve them. No staging/reset/deletion, no production DB mutation, and no replay of historical notifications. Before production rollout, ensure the intended Gemini result is validated, integrated into matcher inputs, covered by regression tests, and deployed from the correct branch/commit.


## 2026-10-13: Gemini experience extraction remains shadow-only
- VM inspection confirms `v2/gemini_extractor.py` explicitly documents and implements shadow-only extraction: validated Gemini output is cached in `gemini_shadow_cache` but `shadow_extract_jobs()` does not mutate job dictionaries or matcher inputs.
- `v2/radar.py` experience matching still falls back to regex extraction and can emit `experience not stated in captured source data`; this explains why a JD with an explicit experience range can still be treated as unstated when the regex misses it.
- Branch check `git merge-base --is-ancestor 58fdff1 HEAD` returned exit code 1: the `main` merge containing LinkedIn labeled-experience fix `9b9cbf1` is not an ancestor of `v2-live-radar`. Do not merge `main` wholesale as a shortcut.
- Next implementation focus: inspect the remainder of `run_source`, matcher/evaluation persistence, and existing Gemini tests; add a tested, bounded path that applies only validated, evidence-backed Gemini overall-experience values to matcher inputs before evaluations/alerts, with deterministic parser fallback on Gemini error/low-confidence/ambiguous scope. Keep dev notifications disabled and do not replay historical alerts.
- No parser code has been changed or promoted by this inspection. Preserve local `v2/config.json` changes and `.venv/`; never stage/reset/clean them. Before any production cutover, test the normal matcher path and request explicit approval.


## 2026-10-13: Matcher integration points confirmed
- VM output confirms `match_details()` reads `jd_experience_min_years`/`jd_experience_max_years`, then regex parsers; it does not read `gemini_shadow_cache`.
- `run_source()` currently invokes `shadow_extract_jobs()` before `upsert_jobs()`, `refresh_job_evaluations()`, and `refresh_notification_decisions()`. That ordering provides an integration point, but the current shadow function returns stats only and intentionally leaves each job unchanged.
- Existing VM test grep did not reveal a Gemini-to-matcher regression test in `v2/test_radar.py`; inspect `v2/test_gemini_extractor.py` and cache result samples before wiring this into the hard matcher. Only apply Gemini experience when schema validation and verbatim evidence pass, scope is `total_professional`, type is `required`, and confidence meets an explicit threshold; avoid turning skill-specific or preferred years into hard eligibility rules.
- Worktree safety confirmed: local `v2/config.json` is modified and `.venv/` is untracked; preserve both. No production changes, notification replay, or parser deployment performed.


## 2026-10-13: Gemini cached experience wired into persisted matching (tests pending)
- Added `cached_matcher_experience(job, conn)` to read the fresh, model-matched Gemini cache entry for the exact current JD hash and revalidate its structured result. It only returns an experience range when the result is required, `total_professional`, has verbatim evidence, and confidence >= 0.85; preferred, skill-specific, unknown-scope, low-confidence, stale, wrong-model, or invalid results are ignored.
- `_job_for_canonical()` now adds accepted Gemini values as `jd_experience_min_years`/`jd_experience_max_years` before `match_details()` evaluates persisted jobs. Existing deterministic parsing remains the fallback; the extractor still stores cache results separately and no API request is made from the matcher.
- Added three regression tests covering accepted cached values, rejection of unsafe results, and the persisted-job loading bridge. These tests have been committed but not yet run in the VM; next run the targeted Gemini tests and full radar suite.
- Commits on `v2-live-radar`: extractor bridge `1b667e489f9ebfee808ada8601e39fdee1df6c59`, matcher integration `c3cc27640b6ddf044e2d776f148bbc15ab7b2361`, regression tests `ce69cecc67d2bbb19c694cbb7be79628caa0f931`. This is code-only development, not a production deployment. Protect local `v2/config.json` and `.venv/`; do not replay historical notifications.


## 2026-10-13: Explicit matcher rollout gate added
- Gemini-to-matcher integration is now guarded by `GEMINI_MATCHER_ENABLED` (must be `1`, `true`, or `yes`). It defaults off, so deploying the code alone does not change eligibility or alerts. When enabled, only fresh exact-JD cache results that pass evidence/type/scope/confidence checks are applied.
- Regression tests now set `GEMINI_MATCHER_ENABLED=true` for trusted-cache integration cases. Latest code/test commits: `14516a0` and `0b74444`; run tests in VM before considering release. Production environment has not been changed.


## 2026-10-13: Gemini matcher tests passed
- User ran `python -m unittest -v v2.test_gemini_extractor`: 11 tests passed. Full `python -m unittest v2.test_radar`: 88 tests passed. No failures reported.
- Trusted cached Gemini experience integration is now regression-tested. `GEMINI_MATCHER_ENABLED` defaults off, so production matcher behavior does not change unless explicitly enabled.
- Next: verify production deployment target, extraction enablement/auth, current cache quality, database backup/persistent volume, and notification-ledger safety. Deploy with matcher flag off first; health-check and inspect cache before explicit controlled enablement. Never replay historical alerts. User's local `v2/config.json` and `.venv/` must be preserved.


## Gemini matcher validation update (2026-10-14)
- VM validation passed: `v2.test_gemini_extractor` (11 tests) and full `v2.test_radar` suite (88 tests), both `OK`.
- The Gemini matcher integration remains opt-in via `GEMINI_MATCHER_ENABLED`; default is off. Passing tests do not mean production is enabled or deployed.
- Next gate: inspect safe dev environment/config and confirm relevant fresh cache entries/model alignment before considering a controlled rollout. Preserve local `v2/config.json` and `.venv/`; do not deploy or replay notifications without explicit approval.


### Gemini matcher validation update — 2026-10-14
- VM validation passed: `v2.test_gemini_extractor` ran 11 tests successfully; full `v2.test_radar` suite ran 88 tests successfully.
- This confirms automated tests only; no production rollout or production environment change has occurred.
- Keep `GEMINI_MATCHER_ENABLED` off until development cache/configuration checks are reviewed and explicit production cutover approval is given.


### Gemini matcher validation update — 2026-10-14 (latest VM evidence)
- User reports targeted Gemini tests passed: 11 tests, OK; full v2.test_radar suite passed: 88 tests, OK. Expected collector warnings/429 behavior appeared in tests; no failures reported.
- User pulled latest v2-live-radar; branch matched origin/v2-live-radar after fast-forwarding docs. Worktree status is M v2/config.json and ?? .venv/. Preserve both; never stage, reset, or delete them.
- Read-only environment check found GEMINI_MATCHER_ENABLED, GEMINI_EXTRACTION_ENABLED, and GEMINI_MODEL unset; no Gemini API key was detected in the inspected environment. No .db, .sqlite, or .sqlite3 files were found within the checkout search depth. These observations do not prove what the running container environment or mounted DB contains.
- Matcher integration is committed on v2-live-radar but is guarded by GEMINI_MATCHER_ENABLED, default off. Tests passing is not a production rollout. No production environment change, deployment, DB mutation, or notification replay occurred.
- Next action: inspect only the isolated dev runtime's documented Compose/env wiring and secret/config source, without printing secret values; determine how Gemini extraction is intended to be configured and where the dev persistent DB volume lives. If no API key/config exists, ask the user to configure it through the existing secure mechanism rather than inventing or exposing credentials. Then verify extraction produces fresh cache rows for the configured model and relevant JDs, with Telegram disabled. Do not enable matcher or change production until cache/model/DB/notification-ledger safeguards are verified and user explicitly approves rollout.
- Continuation prompt: read this handover, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, and docs/JOBBEEPER_REFERENCE.md; continue the single Gemini JD-experience matcher issue. Make GitHub code/docs changes directly as needed, give the user copyable commands to run on the VM, wait for real output before claiming runtime success, preserve local v2/config.json and .venv/, and update both handover documents at the end of every turn. Do not deploy production without explicit approval.


## 2026-10-14: Dev Compose matcher-gate wiring; runtime checks pending

- **No application code changed.** Fixed the isolated development Compose manifest so `GEMINI_MATCHER_ENABLED` is explicitly passed through, defaulting to false. Commit: `7ea83e024f2da4923633c23221ea8085a3643a10`. Production Compose is unchanged.
- Existing user-reported test evidence remains 11/11 `v2.test_gemini_extractor` and 88/88 `v2.test_radar`; neither suite was rerun for this Compose-only edit. GitHub Actions result for the new commit has not been independently checked.
- Dev extraction credentials and runtime flags remain unverified. Earlier checks found env variables unset and no key detected in the checked shell; that does not establish the actual container environment. The running container's DB must be confirmed from the actual `/data` mount, not by searching the checkout.
- **Do not start or recreate the service yet.** First pull the documentation/Compose fix and capture read-only runtime output using the commands below. They print only whether a key is configured, never its value; the API summary script intentionally omits raw job titles, identifiers and evidence quotes.

```bash
cd ~/job-beeper-dev || exit 1
printf '%s\\n' '--- worktree before pull ---'
git status --short --branch
git pull --ff-only origin v2-live-radar || exit 1
printf '%s\\n' '--- worktree after pull / latest commit ---'
git status --short --branch
git log -1 --format='HEAD=%h %s'

printf '%s\\n' '--- dev Compose service status ---'
docker compose -p job-radar-dev -f v2/docker-compose.dev.yml ps || true
printf '%s\\n' '--- declared dev volume names ---'
docker compose -p job-radar-dev -f v2/docker-compose.dev.yml config --volumes || true
printf '%s\\n' '--- actual /data mount on dev container ---'
docker inspect job-radar-dev --format 'data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}' 2>&1 || true
printf '%s\\n' '--- actual environment inside running dev container (no secrets printed) ---'
docker compose -p job-radar-dev -f v2/docker-compose.dev.yml exec -T radar python -c 'import os; yes={"1","true","yes"}; flag=lambda n: str(os.getenv(n,"").strip().lower() in yes).lower(); print("db_path="+os.getenv("JOB_RADAR_DB","<unset>")); print("gemini_api_key_configured="+str(bool(os.getenv("GEMINI_API_KEY","").strip())).lower()); print("gemini_model="+os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite").strip()); print("gemini_extraction_enabled="+flag("GEMINI_EXTRACTION_ENABLED")); print("gemini_matcher_enabled="+flag("GEMINI_MATCHER_ENABLED")); print("telegram_credentials_empty="+str(not any(os.getenv(n,"").strip() for n in ("JOB_RADAR_TELEGRAM_BOT_TOKEN","JOB_RADAR_TELEGRAM_CHAT_ID"))).lower())' 2>&1 || true
```

Then run this read-only API check. It reports flags, cache counts and sanitized cache eligibility indicators only; it does not print secrets, titles, source IDs, raw descriptions or evidence text.

```bash
python3 - <<'PY'
import datetime as dt
import json
import urllib.request

url = "http://127.0.0.1:8001/api/llm-shadow-status"
try:
    with urllib.request.urlopen(url, timeout=5) as response:
        status = json.load(response)
except Exception as exc:
    print("llm_shadow_status=unavailable")
    print("error_type=" + type(exc).__name__)
    raise SystemExit(0)

print("llm_shadow_status=reachable")
for key in ("enabled", "api_key_configured", "model", "mode",
            "daily_limit", "calls_today", "cache_successes", "cache_errors"):
    print(f"{key}={status.get(key)}")
now = dt.datetime.now(dt.timezone.utc)
for index, row in enumerate(status.get("recent_results", [])[:10], 1):
    result = row.get("result") or {}
    created = None
    try:
        created = dt.datetime.fromisoformat(row.get("created_at", "").replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        pass
    fresh = created is not None and dt.timedelta(0) <= now - created < dt.timedelta(days=30)
    candidate_shape_precheck = (
        row.get("status") == "ok"
        and row.get("model") == status.get("model")
        and fresh
        and result.get("experience_type") == "required"
        and result.get("experience_scope") == "total_professional"
        and bool(result.get("experience_evidence"))
        and (result.get("experience_min_years") is not None or result.get("experience_max_years") is not None)
        and isinstance(result.get("confidence"), (int, float))
        and result.get("confidence", 0) >= 0.85
    )
    print(f"cache_sample_{index}: status={row.get('status')} model_match={row.get('model') == status.get('model')} fresh_30d={fresh} candidate_shape_precheck={candidate_shape_precheck}")
PY
```

**Interpretation caution:** `candidate_shape_precheck` is only a structural screen; it does not prove the cache input hash still matches a current JD or that a persisted evaluation consumed the cached result. That requires a separate read-only DB/evaluation check. **Expected output to return:** branch/HEAD and worktree status (the local `v2/config.json` modification and `.venv/` must remain); dev container status; volume name and mount destination; DB path; booleans for key configured, extraction flag, matcher flag and empty Telegram credentials; API enabled/model/cache counts; sanitized per-cache-row indicators. Docker permission errors can be returned as-is; do not use `sudo`, print `.env`, run `docker inspect` without the format filter, or paste any key/token.

**Next step after evidence:** if the key is absent, configure it only on the dev VM through the existing ignored `.env` or exported-environment mechanism without showing the value. Keep extraction and matcher disabled until the container's config and mount are confirmed. Then enable bounded extraction in dev, keep Telegram disabled, let at most the configured request budget run, and inspect cache/evaluation through read-only operations. Never switch/enable production or replay old alerts without explicit approval.


## 2026-10-14: Architecture reference synchronized with cached matcher

- Updated `docs/JOBBEEPER_REFERENCE.md` in commit `8b71918468e41084f363cc1eb4a5250757e85b74` to clarify that extraction itself only writes validated cache entries, while the separate network-free matcher bridge may consume fresh, exact-JD/model-matched results when `GEMINI_MATCHER_ENABLED` is explicitly on.
- This avoids the old reference section contradicting the current gated matcher implementation. No application code, production config, database, volume or container was changed in this turn; no tests were run. The development Compose gate wiring remains commit `7ea83e024f2da4923633c23221ea8085a3643a10`.
- CI status for these direct branch commits was not exposed by the combined commit-status query; do not claim that CI or runtime validation passed. No production deployment or historical notification replay occurred.
- Exact next action remains the read-only/sanitized dev VM check in the preceding section. Preserve the local `v2/config.json` modification and untracked `.venv/`; do not use `sudo`, print any secret, restart/rebuild before the baseline is captured, or infer DB location from checkout files.


## 2026-10-14: VM check results — Docker access is the blocker

- User pulled the development branch and handover updates; their checkout was `b27de42` at the time of output. Worktree stayed `M v2/config.json`, `?? .venv/`. Compose syntax validation passed.
- `docker compose ps`, filtered `docker inspect`, and `docker compose exec` all failed with `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`. No `sudo` or permission repair was attempted. The attempted container environment command was malformed and did not provide environment values.
- The read-only `127.0.0.1:8001/api/llm-shadow-status` output was reachable: extraction `false`; key configured `false`; model `gemini-3.5-flash-lite`; daily limit 20; calls today 0; cache successes 14; cache errors 6. Several recent successful entries matched a preliminary required/overall/evidence/confidence shape, but these samples do not establish current JD hash alignment or persisted evaluation consumption.
- Diagnosis: extraction is not configured/enabled in the service answering on port 8001. Confidence is high for that endpoint's reported status, but actual container env, service identity, volume mapping, matcher gate and exact cache-to-evaluation path remain unverified. No code change this turn; no tests run; no restart, DB write, production change or alert replay.
- Next command: use the host-side Compose interpolation script below to report whether the local Compose inputs contain Gemini credentials/flags without printing their values; report current Unix group membership and Docker socket owner/group/mode. Do not attempt `sudo`, `chmod`, group modifications, or Docker commands requiring daemon access. If the user is already in the authorized Docker group but the current login has stale supplementary groups, a fresh login may fix it without permission changes; otherwise Docker actions require the VM administrator/authorized account.
- After the access baseline, if no key is configured, ask the user to set it only through local ignored `.env` using a hidden prompt; then, only after Docker access is established, recreate the isolated dev service with extraction/matcher still off for the initial configuration verification. Keep Telegram empty and LinkedIn disabled. Inspect actual `/data` volume before any SQLite reads. Then enable bounded extraction in dev and verify fresh exact-JD/model-matched cache values flow into persisted evaluation. Production remains off and requires explicit approval.

### Safe next VM command

```bash
cd ~/job-beeper-dev || exit 1
git pull --ff-only origin v2-live-radar || exit 1

printf '%s\\n' '--- account and Docker socket access metadata ---'
id
stat -c 'docker_socket_owner=%U docker_socket_group=%G mode=%a' /var/run/docker.sock 2>&1 || true
printf 'docker_context='
docker context show 2>&1 || true

printf '%s\\n' '--- host-side Compose-resolved Gemini config (no secret values) ---'
python3 - <<'PY'
import json, subprocess
cmd = [
    "docker", "compose", "-p", "job-radar-dev",
    "-f", "v2/docker-compose.dev.yml", "config", "--format", "json"
]
p = subprocess.run(cmd, text=True, capture_output=True)
print("compose_config_exit=" + str(p.returncode))
if p.returncode:
    print("compose_config_error_type=ComposeConfigError")
    raise SystemExit(0)
try:
    config = json.loads(p.stdout)
    env = config.get("services", {}).get("radar", {}).get("environment", {})
except (ValueError, AttributeError):
    print("compose_config_json=unavailable")
    raise SystemExit(0)
print("compose_api_key_configured=" + str(bool(str(env.get("GEMINI_API_KEY") or "").strip())).lower())
for name in ("GEMINI_EXTRACTION_ENABLED", "GEMINI_MATCHER_ENABLED"):
    print(name.lower() + "=" + str(env.get(name, "<unset>")).lower())
print("gemini_model=" + str(env.get("GEMINI_MODEL", "gemini-3.5-flash-lite")))
print("telegram_credentials_empty=" + str(not any(str(env.get(k) or "").strip() for k in ("JOB_RADAR_TELEGRAM_BOT_TOKEN", "JOB_RADAR_TELEGRAM_CHAT_ID"))).lower())
PY
```

Compose interpolation reports what a new container would receive, not the running container's current environment. It is a safe prerequisite while the Docker API is inaccessible. Return the output verbatim; it contains no secret values.

## 2026-10-14: Compose input confirms missing key; Docker group is absent

- Latest VM output: `id` lists `ubuntu` and standard groups but not `docker`. Socket metadata is `root:docker` mode `660`; Compose commands requiring the Docker API are denied. Do not use `sudo`, change permissions, or modify group membership; use an already-authorized account/session or ask the VM administrator to run Docker-dependent inspections.
- Host-side `docker compose ... config --format json` succeeded without printing secret values and showed `compose_api_key_configured=false`, `gemini_extraction_enabled=false`, `gemini_matcher_enabled=false`, model `gemini-3.5-flash-lite`, and `telegram_credentials_empty=true`. The API also reports `enabled=false`, `api_key_configured=false`, calls today zero, 14 successful cache records and 6 errors.
- Historical recent-cache shape checks do not establish that any result belongs to the current JD hash or is consumed by a persisted evaluation. Actual container environment, current data-volume mount and service identity remain unverified.
- No application-code change and no tests run this turn. No restart/rebuild, DB mutation, production change, or historical alert replay.

### Configure the key locally without displaying it (only when you have the key)

Run from `~/job-beeper-dev`. It verifies `.env` is ignored, preserves all other existing entries, prompts with input hidden, stores the key, and forces both Gemini gates off. It does not contact Docker or recreate the service.

```bash
cd ~/job-beeper-dev || exit 1
git check-ignore -q .env || { echo '.env is not ignored; refusing to write'; exit 1; }
python3 - <<'PY'
from getpass import getpass
from pathlib import Path

path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
key = getpass('Gemini API key (input hidden): ').strip()
if not key or any(ch.isspace() for ch in key):
    print('No valid key entered; file unchanged.')
    raise SystemExit(1)

managed = {'GEMINI_API_KEY', 'GEMINI_EXTRACTION_ENABLED', 'GEMINI_MATCHER_ENABLED'}
kept = [line for line in lines if line.partition('=')[0].strip() not in managed]
kept.extend([
    'GEMINI_API_KEY=' + key,
    'GEMINI_EXTRACTION_ENABLED=false',
    'GEMINI_MATCHER_ENABLED=false',
])
path.write_text('\n'.join(kept) + '\n', encoding='utf-8')
path.chmod(0o600)
print('dev_gemini_key_saved=true')
print('gemini_extraction_enabled=false')
print('gemini_matcher_enabled=false')
PY

python3 - <<'PY'
import json, subprocess
p = subprocess.run([
    'docker', 'compose', '-p', 'job-radar-dev',
    '-f', 'v2/docker-compose.dev.yml', 'config', '--format', 'json'
], capture_output=True, text=True)
print('compose_config_exit=' + str(p.returncode))
if p.returncode:
    print('compose_config_error_type=ComposeConfigError')
    raise SystemExit(0)
env = json.loads(p.stdout)['services']['radar'].get('environment', {})
print('compose_api_key_configured=' + str(bool(str(env.get('GEMINI_API_KEY') or '').strip())).lower())
print('gemini_extraction_enabled=' + str(env.get('GEMINI_EXTRACTION_ENABLED', '<unset>')).lower())
print('gemini_matcher_enabled=' + str(env.get('GEMINI_MATCHER_ENABLED', '<unset>')).lower())
print('telegram_credentials_empty=' + str(not any(str(env.get(k) or '').strip() for k in ('JOB_RADAR_TELEGRAM_BOT_TOKEN', 'JOB_RADAR_TELEGRAM_CHAT_ID'))).lower())
PY
```

Do not run `docker compose up` until the actual mount and container environment can be checked through an authorized Docker session. A VM administrator/authorized account must handle the container inspection; no permissions should be weakened. After the mount is verified, recreate only the isolated dev service with the gates still false, inspect its actual environment/mount, then enable bounded extraction for testing. Enable matcher later only after fresh cache eligibility is proved. No production change without explicit approval.

## 2026-10-14: Gemini key saved locally; rollout remains gated

- User ran the ignored `.env` hidden-input command and received `dev_gemini_key_saved=true`, `gemini_extraction_enabled=false`, and `gemini_matcher_enabled=false`. The secret was not included in the output. No value was printed or requested in chat.
- This confirms the local config write script ran, not that Compose resolves the key or that the running service has received it. Verify Compose interpolation next with a redacted `docker compose config --format json` check only; it does not require access to Docker daemon.
- Docker socket remains `root:docker` mode 660 and the user's `id` omitted the `docker` group. Do not use sudo or change groups/permissions. The container/volume must be checked by an already-authorized Docker session/account or VM administrator before any recreate/restart.
- No code change, tests, container lifecycle action, database mutation, production change or notification replay. Preserve modified `v2/config.json` and untracked `.venv/`. Keep both Gemini gates false and Telegram disabled.

### Next safe verification command

```bash
cd ~/job-beeper-dev || exit 1
git check-ignore -q .env || { echo '.env is not ignored; refusing to inspect config'; exit 1; }
python3 - <<'PY'
import json, subprocess
p = subprocess.run([
    'docker', 'compose', '-p', 'job-radar-dev',
    '-f', 'v2/docker-compose.dev.yml', 'config', '--format', 'json'
], capture_output=True, text=True)
print('compose_config_exit=' + str(p.returncode))
if p.returncode:
    print('compose_config_error_type=ComposeConfigError')
    raise SystemExit(0)
env = json.loads(p.stdout)['services']['radar'].get('environment', {})
print('compose_api_key_configured=' + str(bool(str(env.get('GEMINI_API_KEY') or '').strip())).lower())
for k in ('GEMINI_EXTRACTION_ENABLED', 'GEMINI_MATCHER_ENABLED'):
    print(k.lower() + '=' + str(env.get(k, '<unset>')).lower())
print('telegram_credentials_empty=' + str(not any(str(env.get(k) or '').strip() for k in ('JOB_RADAR_TELEGRAM_BOT_TOKEN', 'JOB_RADAR_TELEGRAM_CHAT_ID'))).lower())
PY
```

Expected: `compose_api_key_configured=true`, both flags false, and `telegram_credentials_empty=true`. This still says nothing about the running container. After returning that redacted output, arrange an already-authorized Docker session/administrator to inspect the actual dev mount and current container environment before any recreate. Production remains approval-gated.

## 2026-10-14: Explicit key write reported, but default Compose interpolation still false

- User ran the hidden-input `.env` writer and got `dev_gemini_key_saved=true`, both Gemini gates false. Subsequent default `docker compose ... config --format json` succeeded but reported `compose_api_key_configured=false`; extraction/matcher remained false and Telegram credentials empty.
- This means the successful file-write output and Compose's default environment resolution disagree. Do not infer the key is loaded or recreate the service yet. Potential causes include Compose env-file discovery/override settings or the key line not being interpreted as expected; distinguish them using a direct `.env` presence check and a side-by-side, redacted comparison of default Compose interpolation versus explicit `--env-file .env`.
- The diagnostic must never print key text or full Compose output. It may print only whether the local file has exactly one non-empty `GEMINI_API_KEY` line; whether Compose recognizes a key with default discovery; whether it recognizes one with an explicit env-file; whether `COMPOSE_DISABLE_ENV_FILE` / `COMPOSE_ENV_FILES` are set; the two gate values; and Telegram-credential emptiness.
- Docker daemon access is still denied for the current account; the user is not in group `docker`, and the socket is `root:docker` mode 660. Do not use sudo or change permissions/groups. Even if explicit Compose interpolation sees the key, the actual running container and `/data` mount remain unverified and must be inspected by an authorized session/account or VM administrator before recreate.
- No code change, tests, service lifecycle action, DB mutation, production change or alert replay. Preserve the modified `v2/config.json` and untracked `.venv/`. Both Gemini gates stay false; notifications/Telegram remain off.

### Next safe env-resolution diagnostic

```bash
cd ~/job-beeper-dev || exit 1
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path

path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
key_lines = [line for line in lines if line.partition('=')[0].strip() == 'GEMINI_API_KEY']
nonempty_key_lines = [line for line in key_lines if line.partition('=')[2].strip()]
print('dotenv_file_exists=' + str(path.is_file()).lower())
print('dotenv_ignored_by_git=' + str(subprocess.run(['git','check-ignore','-q','.env']).returncode == 0).lower())
print('dotenv_key_line_count=' + str(len(key_lines)))
print('dotenv_nonempty_key_line_count=' + str(len(nonempty_key_lines)))
print('compose_disable_env_file_set=' + str(bool(os.getenv('COMPOSE_DISABLE_ENV_FILE'))).lower())
print('compose_env_files_set=' + str(bool(os.getenv('COMPOSE_ENV_FILES'))).lower())

def check(extra):
    cmd = ['docker','compose', *extra, '-p','job-radar-dev','-f','v2/docker-compose.dev.yml','config','--format','json']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    label = 'explicit_env_file' if extra else 'default_discovery'
    print(label + '_config_exit=' + str(proc.returncode))
    if proc.returncode:
        print(label + '_config_error_type=ComposeConfigError')
        return
    try:
        env = json.loads(proc.stdout)['services']['radar'].get('environment', {})
    except (ValueError, KeyError, TypeError):
        print(label + '_config_json=unavailable')
        return
    print(label + '_api_key_configured=' + str(bool(str(env.get('GEMINI_API_KEY') or '').strip())).lower())
    print(label + '_extraction_enabled=' + str(env.get('GEMINI_EXTRACTION_ENABLED','<unset>')).lower())
    print(label + '_matcher_enabled=' + str(env.get('GEMINI_MATCHER_ENABLED','<unset>')).lower())
    print(label + '_telegram_credentials_empty=' + str(not any(str(env.get(k) or '').strip() for k in ('JOB_RADAR_TELEGRAM_BOT_TOKEN','JOB_RADAR_TELEGRAM_CHAT_ID'))).lower())

check([])
check(['--env-file','.env'])
PY
```

Expected file check: `.env` exists, is ignored, one non-empty key line. If default says false but explicit env file says true, use `--env-file .env` consistently for the isolated dev Compose commands after an authorized operator verifies the volume/container; do not silently restart. If both say false, stop and inspect only dotenv line syntax/count without exposing its value; re-enter key hidden if needed. Never paste or print the credential.

## 2026-10-14: Explicit env-file resolves the key; default discovery does not

- User diagnostic output: `.env` exists, Git-ignored, one key line and one non-empty key line. `COMPOSE_DISABLE_ENV_FILE` and `COMPOSE_ENV_FILES` were unset. Default Compose resolution succeeded but showed key absent; `docker compose --env-file .env ... config --format json` showed key configured. Both extraction/matcher flags false; Telegram credentials empty.
- Diagnosis confidence: high that explicit `--env-file .env` is required for this Compose invocation. This is config interpolation evidence only, not running-container proof. The development Compose commands in root README were corrected in commit `f3df8d6330797a582b7e0a50f117c84a2482899a` to pass the ignored env file explicitly and to require volume verification before a create/recreate.
- Docker access blocker remains: current ubuntu account not in group `docker`; socket metadata `root:docker`, mode `660`. Do not use sudo, change permissions or add group membership. User should ask an already-authorized Docker session/account or VM administrator for read-only inspection; this turn does not authorize or perform any service lifecycle change.
- Immediate next step: inspect the existing container and named volume with filtered output only; report whether container exists, its Compose project/service labels, and `/data` mount type/name/source/destination. Do not print all inspect output or the env. Confirm the mount corresponds to the existing dev volume, not production. If no dev container/volume exists, report that rather than creating a replacement automatically.
- Only once the existing dev volume and service identity are confirmed, an authorized operator may rebuild the isolated dev project with `docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f /home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml up -d --build`, maintaining default extraction/matcher false and Telegram blank. Afterward inspect effective env using a Python command that prints booleans/model only and inspect `/data` mount again. Do not enable extraction until these checks pass.
- No code change, tests, database writes, container lifecycle actions, production switch/flag/DB changes or notification replay in this turn. Preserve `v2/config.json` modification and `.venv/` in dev checkout.

### Read-only Docker inspection for an authorized account/session

```bash
docker ps -a --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'
docker inspect job-radar-dev --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}' 2>&1
```

This is read-only and prints no environment values. Do not proceed to `up`, `down`, volume creation/removal, or SQLite inspection until this proves which dev volume is mounted.

## 2026-10-14: Authorized Docker access still required

- Latest user output: `docker volume ls --filter name=job-radar-dev_radar-dev-data --format 'volume={{.Name}}'` returned `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock` twice. This confirms the current shell still cannot query Docker; it does not establish whether the named dev volume exists.
- The shell prompt was `ubuntu@job-radar:~$`, not the development checkout prompt. For this read-only Docker command the working directory does not matter; the socket access denial is the blocker. Prior `id` output showed current ubuntu account not in group `docker`, socket owner/group `root:docker`, mode `660`.
- Do not retry with sudo, chmod, group changes or privileged workarounds. No volume/container/database change was performed; do not infer volume absence and do not create a replacement volume/database.
- Exact next action: an already-authorized Docker session/account or VM administrator runs the filtered read-only `docker ps -a`, `docker inspect job-radar-dev --format ...`, and `docker volume ls --filter name=job-radar-dev_radar-dev-data` commands already documented above, then returns only container state, Compose project/service labels and `/data` mount metadata. If the container does not exist, report that fact without creating it.
- Compose env-file diagnosis remains established: default interpolation missed `GEMINI_API_KEY`, explicit `--env-file .env` resolved it. Keep using explicit `--env-file .env`; both Gemini gates remain false, Telegram blank, notifications off and LinkedIn disabled. Even after Docker access is resolved, verify the existing dev volume before any recreate.
- No code changes or tests this turn. No container lifecycle action, DB mutation, production setting/deployment, notification replay, or local worktree changes. Preserve modified `v2/config.json` and untracked `.venv/`.

## 2026-10-14: Docker volume query repeated; access denial unchanged

- User repeated `docker volume ls --filter name=job-radar-dev_radar-dev-data --format 'volume={{.Name}}'`; it again returned `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock` twice. This is the same blocker as the previous turn and does not establish whether the dev volume exists.
- Do not ask the user to repeat Docker CLI queries from this account. The prior `id`/socket evidence already shows the account is not in group `docker` and the socket is `root:docker` mode `660`. No sudo, chmod, group changes, or privileged workarounds.
- Exact next step remains an already-authorized Docker session/account or VM administrator running the previously documented filtered read-only `docker ps -a`, `docker inspect` and `docker volume ls` commands, then returning container identity and `/data` mount metadata. If the user cannot access such an account, stop here and ask them to have the VM administrator perform those commands. Do not recreate the service or volume.
- No code change, tests, container lifecycle action, database mutation, production change, or notification replay this turn. Gemini API key remains local in ignored `.env`; explicit Compose env file resolves it. Both Gemini flags remain false and Telegram credentials empty. Preserve local `v2/config.json` modification and untracked `.venv/`.

## 2026-10-14: Same Docker volume permission denial repeated again

- User again submitted `docker volume ls --filter name=job-radar-dev_radar-dev-data --format 'volume={{.Name}}'` from `ubuntu@job-radar:~`; Docker returned permission denied for `/var/run/docker.sock` three times. This is not new evidence about volume existence; volume status remains unknown.
- Do not request another retry from this same account. Known prior checks show this account is not in the `docker` group and the socket is `root:docker` mode `660`. Do not use sudo, change socket permissions/groups, or attempt privileged workarounds.
- Next action is external to this account: have an already-authorized Docker account/session or VM administrator run the filtered read-only container/volume inspection commands in this handover, then share output including the actual `/data` mount. Until the mount is identified, do not create a volume, start/recreate containers, remove anything, or inspect/write the SQLite database.
- No code or test changes, Docker lifecycle operations, database changes, production rollout/config changes, or notification replay this turn. Preserve `v2/config.json` local modification and untracked `.venv/`; the Gemini key remains in ignored `.env`, explicit `--env-file .env` is required for Compose interpolation, both Gemini gates remain false, and Telegram credentials remain empty.

## 2026-10-14: User confirms OCI admin access and has key pair; explain SSH entry

- User clarified they are the Oracle Cloud administrator and have a secret/private key file plus public key file. The practical first step is to SSH to the existing Ubuntu VM, not use OCI console commands as if they ran on the host.
- For Windows, in OCI Console open Compute → Instances → select the `job-radar` instance → copy its Public IP address (if one is assigned). In PowerShell run `ssh -i "$env:USERPROFILE\Downloads\<private-key-filename>.key" ubuntu@<PUBLIC_IP>` with actual local key path and IP substituted; `.pem` may be the private-key extension instead. Accept the host fingerprint only if connecting to the expected instance. Never ask for or disclose either key. `ubuntu` is confirmed by the prior VM prompt.
- Distinguish an SSH private key (`.key`/`.pem` that pairs with a `.pub`) from an OCI API signing key/secret; the latter is not an SSH login key. If SSH times out, verify public IP and TCP/22 ingress only from the intended trusted client IP; if `Permission denied (publickey)`, verify matching key and username. A VM without public IP needs a supported private-network path such as OCI Bastion or a suitable Cloud Shell VCN connection.
- Successful SSH login does NOT automatically grant Docker socket permission. Prior evidence still says user `ubuntu` is not in the `docker` group and `/var/run/docker.sock` is `root:docker` mode 660. Existing task guardrails prohibit sudo, socket permission changes, and group membership changes. Do not run privileged workarounds or recreate containers/volumes; use a pre-authorized Docker session/account or get explicit approval for a new access approach, then collect the existing read-only container/mount evidence.
- No code/test/runtime/db/production changes in this turn. Gemini gates stay false, Telegram empty; preserve local `v2/config.json` and `.venv/`.

## 2026-10-14: SSH connection established; Docker permission approach must be explicit

- User reports they are now connected to the VM over SSH and asks what to do next. This establishes host access but does not change the known Docker socket restriction: `ubuntu` is not in group `docker`; `/var/run/docker.sock` is owned by `root:docker` with mode `660`.
- Do not ask them to repeat the volume listing; do not have them run sudo, chmod, group membership edits, or privileged workarounds yet. Existing handover specifically forbids those approaches. Read-only Docker metadata is still needed to identify the existing development container and `/data` mount, but changing the access method requires an explicit user decision to supersede that guardrail.
- Next conversational step: explain the blocker plainly and ask whether they explicitly authorize using `sudo` for read-only Docker inspection commands only (no container/volume lifecycle commands, no DB access or writes), or want to retain the no-sudo rule and stop pending an already-authorized Docker session. Do not infer this authorization merely from their admin role or SSH connection.
- No code or test changes, Docker lifecycle action, database inspection/change, production change, or notification replay. Preserve local `v2/config.json` and `.venv/`; both Gemini gates false and Telegram credentials empty.

## 2026-10-14: User explicitly authorizes sudo for read-only Docker inspection

- User explicitly approved: `sudo` may be used for read-only Docker inspection commands only. This narrowly overrides the earlier no-sudo guardrail for metadata inspection, not for service/volume lifecycle actions, database access/writes, production changes, or notification replay.
- Next ask user to run from their connected SSH terminal, one at a time: `sudo docker ps -a --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'`; `sudo docker volume ls --filter name=job-radar-dev_radar-dev-data --format 'volume={{.Name}}'`; then `sudo docker inspect <ACTUAL_CONTAINER_NAME_FROM_PS_OUTPUT> --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}'` replacing placeholder with literal name reported by `ps` (no angle brackets). These commands read container/volume metadata only and do not emit environment variables or database contents.
- If `sudo` prompts for a password, enter it only in their local SSH terminal. If they get a sudo authorization error or `No such object`, send that non-secret output; don't work around it with permission/group edits. If the filtered `ps` output is empty, report that without creating a container. Do not use `compose up/down`, start/stop/recreate, volume create/remove, or SQLite commands.
- Need to verify actual `/data` mount and ensure it is the isolated dev volume before any next step. No code/test changes, DB access, production change, or notification replay in this turn; both Gemini gates false, Telegram empty, preserve `v2/config.json` and `.venv/`.

## 2026-10-14: Dev container and volume found; mount inspection command used placeholder literally

- User ran the authorized read-only checks and reported `container=job-radar-dev status=Up 46 hours image=13b233998d70`, plus `volume=job-radar-dev_radar-dev-data`. This confirms the existing dev container is running and the expected named volume exists in Docker.
- Their inspect attempt returned `error: no such object: ACTUAL_CONTAINER_NAME` because the placeholder text was used literally. No change was made. The actual container name from the previous command is `job-radar-dev`; next command must use that exact name.
- Next read-only command: `sudo docker inspect job-radar-dev --format 'project={{index .Config.Labels "com.docker.compose.project"}} service={{index .Config.Labels "com.docker.compose.service"}} data_mount={{range .Mounts}}{{if eq .Destination "/data"}}type={{.Type}} name={{.Name}} source={{.Source}} destination={{.Destination}}{{end}}{{end}}'`. Inspect output must confirm `/data` uses `job-radar-dev_radar-dev-data` before proceeding.
- Scope of user's sudo authorization remains read-only Docker metadata inspection only. Do not run lifecycle actions, read/write SQLite, expose env values, change production, or replay notifications. Both Gemini gates remain false, Telegram empty, preserve local `v2/config.json` and `.venv/`. No tests/code/runtime changes this turn.

## 2026-10-14: Verified dev container is mounted to the expected isolated volume

- User's `sudo docker inspect job-radar-dev` output: `project=job-radar-dev service=radar data_mount=type=volume name=job-radar-dev_radar-dev-data source=/var/lib/docker/volumes/job-radar-dev_radar-dev-data/_data destination=/data`.
- This verifies the running `job-radar-dev` service mounts the expected named dev volume at `/data`. Combined with prior output it is Up 46 hours and the named volume exists. This removes the uncertainty about a missing/new database volume; it does not prove the running container has current code or Gemini environment.
- Next read-only step is to check only whitelisted non-secret environment settings on the existing container. Command: `sudo docker inspect job-radar-dev --format '{{range .Config.Env}}{{if eq (index (split . "=") 0) "GEMINI_API_KEY"}}gemini_key={{if gt (len (index (split . "=") 1)) 0}}configured{{else}}empty{{end}} {{end}}{{if eq (index (split . "=") 0) "GEMINI_EXTRACTION_ENABLED"}}extraction={{index (split . "=") 1}} {{end}}{{if eq (index (split . "=") 0) "GEMINI_MATCHER_ENABLED"}}matcher={{index (split . "=") 1}} {{end}}{{if eq (index (split . "=") 0) "GEMINI_MODEL"}}model={{index (split . "=") 1}}{{end}}{{end}}'`. It must not print the API-key value or all `.Config.Env` items. Share only this filtered output.
- Sudo authorization remains strictly read-only inspection. No container/volume lifecycle commands, SQLite access, notifications, production changes or env dumps. If env settings are missing/stale, ask for separate explicit permission before restarting/recreating the dev container, after confirming current checkout/Compose configuration. Keep both Gemini gates false until actual isolated runtime validation and explicit future rollout authorization; Telegram blank, notifications off and LinkedIn disabled. Preserve local `v2/config.json` and `.venv/`. No code/test/DB changes this turn.

## 2026-10-14: Running dev container has no Gemini key configured

- User's safely filtered inspect output was `model=gemini-3.5-flash-liteextraction=false gemini_key=empty`; it did not print a `matcher=` value, which indicates `GEMINI_MATCHER_ENABLED` was absent from the container's `.Config.Env` (the filter prints a label only when the variable exists). Interpret carefully: this reports the currently running container environment, not current `.env` file contents. Model is set; extraction is false; API key is absent/empty in the container; matcher variable not present.
- The existing container and named dev volume are verified and `/data` maps to `job-radar-dev_radar-dev-data`. The VM-local ignored `.env` previously contained a non-empty key line, and explicit Compose `--env-file .env` resolved the key in a local config interpolation diagnostic; however the 46-hour-old running container has not received that configuration. Do not print the actual key or full `.Config.Env`.
- Next step before any lifecycle operation is read-only checkout/config validation in SSH: `cd ~/job-beeper-dev && printf 'branch=' && git branch --show-current && printf 'head=' && git rev-parse --short HEAD && git status --short && docker compose --env-file .env -f v2/docker-compose.dev.yml config --quiet`. Share the branch/head/status and whether config validation succeeded. This should not output secret values; preserve local `v2/config.json` and `.venv/`. It validates configuration only and does not apply it to the running container.
- To apply changed env to an existing service, a container recreation may be required, but user has authorized sudo only for read-only metadata inspection; do not run `up`, `down`, restart/recreate, volume operations, DB access, production changes or notifications without separate explicit authorization. If validation succeeds, explain exactly what recreation would do and ask permission before taking any lifecycle step. Keep both Gemini flags false until separate validation plan and approval; Telegram blank, LinkedIn disabled, notifications off.

## 2026-10-14: Dev checkout and Compose configuration validated

- User's VM check from `~/job-beeper-dev`: `branch=v2-live-radar`, `head=c40e5d7`, status `M v2/config.json` and `?? .venv/`, `compose_config=valid` from `docker compose --env-file .env -f v2/docker-compose.dev.yml config --quiet`. Preserve both local items exactly; do not stage, overwrite, reset, or clean them.
- GitHub compare for `c40e5d7...v2-live-radar` reports 25 commits ahead, zero behind, with changes only in `README.md`, `docs/JOB_RADAR_HANDOVER.md`, and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`; application/Compose code is unchanged between the VM's reported commit and current branch tip. The container has been Up 46 hours and currently lacks `GEMINI_API_KEY` and the matcher env variable; `GEMINI_EXTRACTION_ENABLED=false`, model `gemini-3.5-flash-lite`. The local `.env` has a non-empty key and explicit Compose env-file is required.
- Actual dev DB mount is verified: project `job-radar-dev`, service `radar`, named volume `job-radar-dev_radar-dev-data` at `/data`. The existing code/docs specify dev launch via `docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build`. This is a lifecycle action; current approval is only read-only Docker inspection, not build/recreate. Next ask explicit permission to rebuild/recreate only the dev `radar` service, using explicit env file and same project/volume; no `down`, no volume changes, no SQLite commands, no production service changes or notification replay. Keep Gemini gates false; Telegram blank, notifications off and LinkedIn disabled.
- Caution: no `.dockerignore` exists in the branch root or `v2/`; build context is the checkout root, while Dockerfile only copies `v2/` and `dashboard/`. The local `.venv/` may be transmitted as part of the build context (though not copied into the image); mention this before obtaining build/recreate approval, and do not delete or modify `.venv/`. No code/test/runtime/db/production changes this turn.

## 2026-10-14: User approves dev-only radar rebuild/recreation

- User explicitly approved rebuilding and recreating only the development `radar` service, using the VM-local `.env` and preserving the existing named development DB volume. This authorizes the narrowly scoped Compose command `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`; it does not authorize any `down`, volume operation, production service change, SQLite command, live notification or enabling the Gemini matcher.
- Confirmed preconditions: checkout branch `v2-live-radar` HEAD `c40e5d7`; `M v2/config.json`, `?? .venv/` (preserve both); Compose validation passed with explicit env file; current running `job-radar-dev` uses project `job-radar-dev`, service `radar`, and existing volume `job-radar-dev_radar-dev-data` mounted at `/data`. GitHub compare to latest branch showed only README and handover docs changed beyond the checkout, not app or Compose code.
- Build context is repository root and there is no root `.dockerignore`; local `.venv/` and `.env` may be included in the local daemon's build context, though the Dockerfile copies only `v2/` and `dashboard/` into the image. Do not delete/change them. Continue only with the approved dev service command and do not run `down` or modify the volume.
- After command returns, perform read-only checks: container status; filtered environment presence (only print `gemini_key=configured|empty`, `model=...`, `extraction=...`, `matcher=...`, never actual key/full env); health at `http://127.0.0.1:8001/health`; then use dev-only shadow-status and logs as needed. Ensure both flags remain false until separate validation and explicit matcher-enable approval. Do not claim successful behavior solely from env/status checks. No production change, database manipulation or notification replay.

## 2026-10-14: Dev radar rebuild completed; runtime verification pending

- User's Compose output confirms build succeeded (`[+] Building 9.7s (14/14) FINISHED`), image `job-radar-dev-radar:latest` built, and `job-radar-dev` container started. They ran the approved command from `~/job-beeper-dev`. No errors shown.
- BuildKit reports a `.dockerignore` was loaded (2 B) and build context transfer was 579.56 kB. This is the concrete build output; do not make a claim about exact ignore rules without reading that local file. Existing local `v2/config.json` modification and untracked `.venv/` must remain untouched.
- Verified preconditions remain: current named database volume `job-radar-dev_radar-dev-data` mounted at `/data`; Compose config validated with explicit `.env`; source tree VM HEAD reported `c40e5d7` on `v2-live-radar`; key was absent from previous running container. Rebuild/recreate was explicitly approved for dev radar only, not any volume changes.
- Next ask for read-only runtime verification: (1) `sudo docker ps --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'`; (2) safe filtered runtime environment using `sudo docker exec job-radar-dev sh -c 'if [ -n "$GEMINI_API_KEY" ]; then echo gemini_key=configured; else echo gemini_key=empty; fi; printf "model=%s\nextraction=%s\nmatcher=%s\n" "${GEMINI_MODEL:-unset}" "${GEMINI_EXTRACTION_ENABLED:-unset}" "${GEMINI_MATCHER_ENABLED:-unset}"'`; (3) `curl -fsS http://127.0.0.1:8001/health`; (4) `curl -fsS http://127.0.0.1:8001/api/llm-shadow-status`. The second command must never print actual key. Share outputs. Do not enable extraction or matcher, do not replay alerts, and do not change production or DB. Verify status endpoint evidence before a controlled shadow extraction test; keep both flags false and Telegram blank.

## 2026-10-14: Rebuilt dev runtime is healthy and key is present; shadow extraction still disabled

- User-reported post-rebuild checks: container `job-radar-dev` is Up for 4 minutes using `job-radar-dev-radar`; runtime key presence `configured`; model `gemini-3.5-flash-lite`; `GEMINI_EXTRACTION_ENABLED=false`; `GEMINI_MATCHER_ENABLED=false`. `/health` returned status `ok`, version `2.0.0`, DB `/data/jobs.db`, and Naukri has previous successful ingestion state. This confirms runtime env and app health, not new Gemini extraction or matcher behavior.
- `/api/llm-shadow-status` is reachable and reports `enabled=false`, API key configured, model `gemini-3.5-flash-lite`, `mode=shadow_only`, `daily_limit=20`, `calls_today=0`, `cache_successes=14`, `cache_errors=6`. The returned examples are dated 2026-10-12, before this 2026-10-14 rebuild; they do not prove a fresh post-rebuild extraction, current exact-JD hash match, or persisted evaluation consumption. Do not copy raw job titles/IDs/description/evidence into handovers or share full raw status JSON again.
- Existing reference workflow says enable bounded extraction only after key and actual isolated `/data` volume are verified. Both preconditions are now satisfied. The next step requires an explicit user decision to change the dev-only ignored `.env` setting `GEMINI_EXTRACTION_ENABLED=true` and recreate only dev `radar` to apply it. Leave `GEMINI_MATCHER_ENABLED=false`, Telegram blank, notifications disabled, LinkedIn disabled. This uses the Gemini API (bounded by existing `GEMINI_MAX_CALLS_PER_RUN=3` and `GEMINI_MAX_CALLS_PER_DAY=20`) and writes shadow cache rows to the existing dev DB; do not perform without approval. No production, volume lifecycle, or historical notification replay.
- After approved extraction-only enablement, validate with sanitized `/api/llm-shadow-status` indicators (do not dump raw `recent_results` because it exposes source IDs/titles/evidence), and then inspect exact-JD/model/hash cache eligibility and persisted evaluation via a carefully read-only, redacted check. Do not enable matcher until fresh cache eligibility is demonstrated and a separate explicit approval is received. Preserve `v2/config.json` and `.venv/`.

## 2026-10-14: Runtime healthy; sanitized Gemini diagnostics committed; next step is fresh shadow extraction

### Current runtime evidence from user

- The approved command `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar` completed successfully: 14/14 build steps, image `job-radar-dev-radar` built, development container started.
- User verified container `job-radar-dev` Up for 4 minutes. Safe environment output: `gemini_key=configured`, `model=gemini-3.5-flash-lite`, `extraction=false`, `matcher=false`.
- `curl -fsS http://127.0.0.1:8001/health` returned status `ok`, version `2.0.0`, database `/data/jobs.db`. Naukri showed `running=false`, prior `last_success=2026-10-14T08:40:46.188540+00:00`, `jobs_seen=366`, `new_jobs=1`, `error=null`. Do not infer scheduler failure only from `running=false`; it describes the instant of the status call.
- `/api/llm-shadow-status` returned `enabled=false`, `api_key_configured=true`, model `gemini-3.5-flash-lite`, mode `shadow_only`, daily limit 20, calls_today 0, cache successes 14, cache errors 6. All visible recent cache timestamps were 2026-10-12, before today's run. This is stale historical cache and does not prove fresh exact-JD/model cache eligibility or persisted matcher consumption. The old endpoint response included source job IDs, titles, and verbatim JD evidence; do not copy or share those raw records again.
- Isolated persistence is verified: Compose project `job-radar-dev`, service `radar`, named volume `job-radar-dev_radar-dev-data` mounted at `/data`. No production changes, database inspection/writes, or alert replay occurred. Keep `v2/config.json` modified and `.venv/` untracked exactly as they are.

### Direct GitHub code changes in this continuation

- Commit `10d9c49d08d050c5639902166f697961328ab81b` updates `v2/gemini_extractor.py`: `/api/llm-shadow-status` recent samples no longer expose source, source job ID, job title, raw extraction JSON, raw evidence quotation, or extracted skills. It instead returns a summary of status/model/time/error code plus validated experience bounds/type/scope/confidence, an evidence-present boolean, and an `experience_shape_eligible` boolean. The latter is a shape-only indicator, not proof of an exact current JD hash or matcher consumption.
- Commit `872bae496d3df7e501b7e5179c0a76376c42ea93` adds `test_shadow_status_redacts_job_identity_and_raw_extraction` in `v2/test_gemini_extractor.py`.
- Follow-up commits `c1c2412e20b56538fcb10a1f5ee492b40611e27f` and `36db6b40c1aad80e7e6d0ae8ce6203bae381a030` harden status serialization against malformed cache field types and add `test_shadow_status_handles_malformed_cached_payload`.
- These GitHub changes are committed directly on `v2-live-radar`. Automated tests have NOT been run after these new commits yet. A combined GitHub status lookup for test commit `36db6b40c1aad80e7e6d0ae8ce6203bae381a030` returned no status entries, so no remote CI result is available from that check. The running dev container was built before these diagnostic-redaction commits and therefore does not yet serve the sanitized response. Do not claim this code is VM-validated until user pulls and runs tests.

### Next steps for the next chat/model

1. Start by reading this file, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`. Continue this single task; do not start a new implementation from scratch. Make code/document changes directly on GitHub branch `v2-live-radar` using the installed GitHub tools and current file blob SHA values; do not ask the user to manually edit Python files.
2. Give the user these commands and wait for their actual output:
```bash
cd ~/job-beeper-dev
git status --short
git pull --ff-only
printf 'branch=' && git branch --show-current
printf 'head=' && git rev-parse --short HEAD
git status --short
./.venv/bin/python -m unittest v2.test_gemini_extractor
./.venv/bin/python -m unittest v2.test_radar
```
Preserve existing local `M v2/config.json` and untracked `.venv/`; never stage either, use `git add .`, reset hard, or clean. If pull refuses due to conflict or local Python path is absent, stop and inspect the error rather than overwriting local data.
3. The core matcher bridge is already implemented and gated by `GEMINI_MATCHER_ENABLED=false`. Do NOT enable matcher. Fresh cache cannot be validated while `GEMINI_EXTRACTION_ENABLED=false`. Ask user for explicit approval before changing VM-local ignored `.env` to turn on only `GEMINI_EXTRACTION_ENABLED=true`. Explain this makes at most 3 Gemini calls per source run and up to 20/day and persists structured shadow-cache rows in dev DB. It does not change match decisions while matcher remains false, but it calls Gemini API and writes dev DB.
4. After approval, set extraction true and matcher false in `.env` without printing the API key or any `.env` lines. Then recreate only development `radar` with `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar`; never use `down`, change volume, or touch production. After startup, verify status/key-presence/model/flags with a sanitized command, check `/health`, and inspect only redacted `/api/llm-shadow-status`. Ensure at least one fresh cache record is created with matching configured model and successful status.
5. Verify exact-job cache eligibility using a narrowly scoped read-only/redacted diagnostic based on `_input_hash(job)`, active model, cache age and the `job_evaluations` row. Do not print JD body, source IDs, titles, evidence text, API key, config token, or complete SQLite rows. Require a fresh exact-JD/model result with required total-professional experience, verbatim evidence, confidence >= 0.85, and a range bound, then confirm `_job_for_canonical` returns `jd_experience_source=gemini_verified` and the persisted `job_evaluations` row contains expected experience bounds/reasons. Important: `job_evaluations` currently has no source column, so do not claim the source marker itself is persisted. If persistent source attribution is required, propose a separate schema migration and regression test before changing it.
6. Only after all evidence, ask separately whether to enable `GEMINI_MATCHER_ENABLED=true` in development. Keep Telegram blank, notifications off, LinkedIn disabled, and production untouched. No historical notification replay or deployment without separate explicit approval.

### Correction on Docker build-context observation

- BuildKit output from the successful user rebuild explicitly said it loaded `.dockerignore` (transfer size 2 B) and transferred a 579.56 kB build context. Earlier notes that `.dockerignore` was absent came from GitHub file-fetch attempts returning 404; those observations conflict and should not be treated as confirmed file absence. The content of the VM's `.dockerignore` has not been directly reviewed. No need to delete or modify `.venv/`/`.env` to proceed.

## 2026-10-14: Runtime verified; GitHub fixes need fast-forward pull and retest

- User confirmed after the approved dev-only rebuild: `job-radar-dev` is Up 4 minutes, image `job-radar-dev-radar`; safe runtime check reports `gemini_key=configured`, model `gemini-3.5-flash-lite`, `extraction=false`, `matcher=false`. `/health` responded `{"status":"ok","version":"2.0.0",...}` with DB `/data/jobs.db`. Actual volume remains the verified `job-radar-dev_radar-dev-data` at `/data`; no DB/volume operations were done.
- `/api/llm-shadow-status` reports extraction disabled, API key configured, shadow-only mode, daily limit 20, calls_today 0, 14 successful cache rows and 6 errors. All displayed sample timestamps were dated 2026-10-12, so there is no evidence of fresh cache output. The user's deployed endpoint response included raw job/source identifiers, titles, skill lists and literal evidence quotations; avoid repeating or storing those values. This response came from the currently running image built before the latest GitHub redaction commits, not proof the current source code still exposes those fields.
- VM checkout is on `v2-live-radar` at `c40e5d7`. A GitHub compare showed the remote strictly ahead with no divergence (a refresh before the latest handover writes counted 50 commits ahead); the number moves as direct commits continue, so do not rely on a hardcoded count. Use `git pull --ff-only origin v2-live-radar`. Changed files include README, both handovers, `v2/gemini_extractor.py`, and `v2/test_gemini_extractor.py`. Keep local `M v2/config.json` and untracked `.venv/`; never stage/reset/clean or overwrite them.
- Direct GitHub code/test changes on `v2-live-radar`: `10d9c49d08d050c5639902166f697961328ab81b` removes source IDs, titles, raw result JSON, evidence quotes and skill lists from `/api/llm-shadow-status`; `872bae496d3df7e501b7e5179c0a76376c42ea93` tests the redaction; `c1c2412e20b56538fcb10a1f5ee492b40611e27f` and `36db6b40c1aad80e7e6d0ae8ce6203bae381a030` harden malformed cached data handling and test it. New diagnostic commit `2eba968e29f74f442c675b1a7107f8f96a9bb199` adds safe `matcher_enabled` to status output; test commits `d1c5813ac419c2cd4fd036ac0e43f810925cfeea` and `50e2e5422fe9ff1a400bb8fdf3e21dc3246ef022` cover its behavior. These test changes have not been executed on the VM yet; do not claim tests pass.
- Immediate VM steps: run `cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD`. The only expected local changes remain `M v2/config.json` and `?? .venv/`. If pull fails or indicates conflict, stop; never reset/clean. Then run `./.venv/bin/python -m unittest v2.test_gemini_extractor` and `./.venv/bin/python -m unittest v2.test_radar`; report actual results and stop on failure. Because user previously approved rebuild/recreation of only dev `radar`, after both test commands pass run `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar` to deploy the already reviewed code-redaction/diagnostic fix. Same verified DB volume; no `down` or volume modifications.
- After this refresh, check container state, safe-filtered environment, `/health`, and `/api/llm-shadow-status`. Ensure API status does not include `source`, `source_job_id`, `title`, `result`, `experience_evidence`, `required_skills` or `preferred_skills`, and now reports `matcher_enabled=false`. Do not print secrets or repeat raw cache examples.
- Next gated step is still separate explicit user approval to set only `GEMINI_EXTRACTION_ENABLED=true` and keep `GEMINI_MATCHER_ENABLED=false`. This will incur bounded Gemini API use (up to 3 calls per source run, max 20/day) and persist cache rows to the isolated dev DB; this has not yet been authorized. After approval, edit the local ignored `.env` without echoing secrets, rebuild only the dev service, wait for live shadow extraction via existing scheduler/approved refresh path, and inspect only redacted status. Do not enable matcher until fresh exact-JD/current-model cache eligibility is proven, `_job_for_canonical` returns `jd_experience_source=gemini_verified`, and persisted evaluation carries expected experience bounds/reasons. Do not say the source marker itself is persisted: `job_evaluations` has no such source column. No production, Telegram, LinkedIn, historical notification replay, DB volume operations, or schema migration without separate explicit approval.

### CI status check for current code commits

- Checked combined GitHub status for matcher-status source commit `2eba968e29f74f442c675b1a7107f8f96a9bb199`, latest status-gate test commit `50e2e5422fe9ff1a400bb8fdf3e21dc3246ef022`, and current handover head as of the check (`e2ed2244ad0da93d662117f03e44158d5040a3ae`); each returned an empty status list. Treat this as no reported checks, not as a CI pass or failure. VM-local tests must be run after fast-forward pull; do not claim green tests before seeing results.

## 2026-10-14: Post-rebuild runtime verified; next gate is source pull/tests

- Latest user-reported checks: container `job-radar-dev` Up 4 minutes, image `job-radar-dev-radar`; inside-container safe check says `gemini_key=configured`, model `gemini-3.5-flash-lite`, `extraction=false`, `matcher=false`. `/health` returned `status=ok`, version `2.0.0`, DB `/data/jobs.db`, Naukri prior state `jobs_seen=366`, `new_jobs=1`, no reported error at that instant.
- `/api/llm-shadow-status` returned `enabled=false`, `api_key_configured=true`, model `gemini-3.5-flash-lite`, mode `shadow_only`, daily limit 20, calls_today 0, cache successes 14/errors 6. Visible recent entries dated 2026-10-12, before this rebuild/date. This does not prove a fresh extraction, current exact-JD/model cache hit, or persisted matcher consumption. The output exposed raw IDs/titles/evidence; never repeat/copy raw records. A stray malformed curl token preceded the valid status request, but the endpoint itself returned JSON.
- User's checkout was last reported branch `v2-live-radar`, HEAD `c40e5d7`, status `M v2/config.json` and `?? .venv/`; Compose config valid. Approved dev-only rebuild completed, verified mount remains `job-radar-dev_radar-dev-data` at `/data`. Keep local config and `.venv/` untouched.
- Immediate next action: ask user to run `cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD`. GitHub contains additional code/tests after their old HEAD, including status endpoint redaction and matcher status diagnostics. Expected local changes are `M v2/config.json` and `?? .venv/`; preserve them. Stop on pull conflict/failure; never reset/clean.
- After fast-forward succeeds, run and report separately: `./.venv/bin/python -m unittest v2.test_gemini_extractor` then `./.venv/bin/python -m unittest v2.test_radar`. Stop on failure and fix code directly on GitHub using fresh blob SHA, update both handovers, pull and rerun. If both pass, use previously approved dev-only rebuild `sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar` to apply latest code. Same volume; never `down` or change volume.
- Then verify health and safe-filtered flags; use the redacted `/api/llm-shadow-status` from latest source, ensuring it does not expose `source`, `source_job_id`, `title`, raw `result`, `experience_evidence`, `required_skills` or `preferred_skills`, and shows `matcher_enabled=false`. The running image currently predates those source redaction commits. Do not dump raw JSON again.
- After code/test/runtime hardening, ask separately for approval to enable only development shadow extraction by changing the ignored local `.env` flag `GEMINI_EXTRACTION_ENABLED=true` while keeping `GEMINI_MATCHER_ENABLED=false`. This invokes Gemini with configured caps (up to 3 calls per source run, 20/day) and writes shadow-cache rows into existing dev DB. No fresh extraction until enabled. After approval, rebuild only dev radar, then inspect sanitized status and run a redacted read-only exact-JD/current-model/hash/TTL and persisted evaluation check. Required evidence: fresh cache hit for exact job hash/current model, `required`, `total_professional`, verbatim evidence, confidence >= 0.85, at least one bound; `_job_for_canonical` returns `jd_experience_source=gemini_verified`; persisted `job_evaluations` contains expected experience bounds/reasons. Schema does not persist source marker itself.
- Only after evidence, ask separately for approval to enable `GEMINI_MATCHER_ENABLED=true` in development. Never enable both gates by assumption. Keep Telegram empty, notifications off, LinkedIn disabled; no production change, historical notification replay, DB/volume lifecycle operation, or schema migration without separate explicit approval. Never print API keys/config tokens/full env, job identifiers/titles/JD/evidence, or complete SQLite rows.


## 2026-10-14: Pull-first continuation confirmed; preserve VM-local files

**This is the latest authoritative continuation note and supersedes older next-action instructions above where they conflict.**

- **Objective:** continue the existing Gemini required-total-professional-experience path; do not start from scratch or expand scope. Prove extraction → strict validation → fresh exact-current-JD/model cache → _job_for_canonical with jd_experience_source=gemini_verified → persisted evaluation bounds/reasons. The current job_evaluations schema does not persist the source marker; do not imply otherwise.
- **Required reading completed for this turn:** docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, and docs/JOBBEEPER_REFERENCE.md on v2-live-radar. The reference's matching and rollout guardrails remain applicable.
- **Latest VM state supplied in the current user instructions:** checkout path ~/job-beeper-dev, branch v2-live-radar, last reported VM HEAD c40e5d7; local status has M v2/config.json and untracked .venv/. Preserve both exactly; never stage them, overwrite them, reset, or clean. Dev container job-radar-dev is running under Compose project job-radar-dev, service radar, image job-radar-dev-radar; database path /data/jobs.db, named volume job-radar-dev_radar-dev-data mounted at /data.
- **Runtime state supplied by user:** health at http://127.0.0.1:8001/health is ok; Gemini key presence is configured (never display its value); model gemini-3.5-flash-lite; GEMINI_EXTRACTION_ENABLED=false; GEMINI_MATCHER_ENABLED=false. The shadow endpoint showed 0 calls today, 14 cache successes and 6 errors, with displayed samples dated 2026-10-12. This is not proof of a fresh exact-current-JD cache or matcher consumption. Older endpoint output exposed raw job identifiers/titles/skills/evidence; do not repeat, store, or request raw job records.
- **GitHub changes already on this branch:** status endpoint redaction, malformed-cache hardening, and matcher_enabled diagnostics/tests are committed, but the VM has not yet confirmed pulling them or running the current tests. No test success is claimed in this note.
- **Exact next action for the user (pull only; stop if it fails):**

      cd ~/job-beeper-dev && git status --short && git pull --ff-only origin v2-live-radar && git rev-parse --short HEAD

  Expected pre-pull local changes are M v2/config.json and ?? .venv/; keep them untouched. If the command fails, refuses a fast-forward, or reports conflicts, stop and return the complete output; do not try a reset, clean, force pull, or manual source edit.
- **After a successful pull, request the test outputs as a separate next step:** run ./.venv/bin/python -m unittest v2.test_gemini_extractor and ./.venv/bin/python -m unittest v2.test_radar separately. Do not claim passing until the actual output confirms it. On failure, diagnose/fix source or tests directly on GitHub with fresh blob SHAs, update both handovers, pull and rerun.
- **Only after both suites pass:** the previously approved development-only rebuild may use sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar. This approval is only for the dev radar service and existing volume; never run down, create/remove volumes, touch production, inspect or mutate SQLite broadly, or replay notifications. Verify health, effective safe-filtered flags/key presence/model, and sanitized endpoint behavior; do not print full JSON or secrets.
- **Extraction remains a separate approval gate:** after pull/tests/runtime redaction are confirmed, obtain explicit approval before changing only the VM-local ignored .env value GEMINI_EXTRACTION_ENABLED=true; keep matcher false. This uses Gemini API calls, capped by current config at up to 3 per source run and 20/day, and writes shadow-cache rows to the existing dev database without changing matching decisions while matcher remains false. Wait for actual fresh activity; aggregate counts and stale samples are insufficient.
- **Matcher remains a further separate approval gate:** prove a fresh successful cache record matches the exact current input/hash and configured model within TTL; is classified required and total_professional; includes verbatim evidence; confidence is at least 0.85; has at least one experience-range bound; and is consumed by _job_for_canonical with source gemini_verified. Then verify persisted job_evaluations bounds/reasons without exposing IDs, titles, descriptions, evidence, keys, tokens, or full rows. Only after that proof, ask separately for approval to set GEMINI_MATCHER_ENABLED=true in development.
- **No scope changes:** no production actions, no source flag changes, no notification replay, Telegram remains blank/disabled, LinkedIn remains disabled, no DB schema migration. If persistent source attribution is later required, propose a separate migration and regression test first.
- **Turn record:** documentation-only reconciliation; no application code change, no tests run here, no runtime action performed. Cross-reference: docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md (compact state) and docs/JOBBEEPER_REFERENCE.md (architecture/rollout guardrails).


## 2026-10-14: VM fast-forward succeeded; Gemini extractor tests next

- User supplied actual SSH output confirming git pull --ff-only origin v2-live-radar fast-forwarded the VM checkout from c40e5d7 to bcb8cfc without a reported conflict. The pull updated README, both handovers, v2/gemini_extractor.py, and v2/test_gemini_extractor.py.
- The pasted output did not include the preceding git status --short lines, so do not claim from this output alone that the local M v2/config.json and ?? .venv/ were printed; continue to preserve them and never stage/reset/clean/overwrite them.
- No test has been run or proven by this output. No rebuild, environment change, cache inspection, DB operation, or runtime change occurred this turn.
- Immediate next action: ask the user to run only this first test, returning complete output:
  cd ~/job-beeper-dev
  git status --short
  ./.venv/bin/python -m unittest v2.test_gemini_extractor
  Wait for output before deciding whether to run the Radar suite. If the command fails because the interpreter is missing or test failures occur, stop and diagnose from the actual output; do not proceed to rebuild or enable extraction.
- If the Gemini suite passes, request the separate command ./.venv/bin/python -m unittest v2.test_radar next and wait for its actual output. If either suite fails, fix code/tests directly on GitHub using freshly fetched blob SHAs, update/re-fetch both handovers, pull the fix, and rerun.
- Scope remains the trusted required-total-professional-experience path. Matcher and extraction remain false; the only runtime evidence so far is the previously reported healthy dev service and stale cache samples. Do not claim fresh exact-JD cache or matcher behavior. Preserve the no-source-marker-persistence caveat for job_evaluations.
- Cross-reference: compact status is in docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md; architecture/rollout guardrails are in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-14: Gemini extractor unit suite passed; Radar suite next

- User supplied the actual local output from ~/job-beeper-dev after fast-forward to bcb8cfc: git status showed M v2/config.json and ?? .venv/; preserve both exactly. The command ./.venv/bin/python -m unittest v2.test_gemini_extractor completed with 14 tests in 0.108s, result OK.
- The test log included one INFO line for a shadow-extraction test case. This is unit-test output, not evidence of live Gemini API activity, current-JD cache eligibility, runtime matcher usage, or persisted evaluation. GEMINI_EXTRACTION_ENABLED and GEMINI_MATCHER_ENABLED remain false based on the last verified runtime state; no runtime change occurred this turn.
- No code change, rebuild, cache/database read, flag change, notification replay, or production operation occurred this turn.
- **Next action:** run only the Radar unit suite and return its complete output:
  ```bash
  cd ~/job-beeper-dev
  ./.venv/bin/python -m unittest v2.test_radar
  ```
- If the Radar suite fails, stop before rebuilding, capture complete output, diagnose the failure, and make a justified code/test fix directly on GitHub with fresh blob SHAs; then update/re-fetch both handovers, pull safely, and rerun the affected suites. If it passes, proceed only to the previously approved development-only radar rebuild; do not enable extraction yet.
- Continue preserving v2/config.json and .venv/: never stage either, use git add ., reset hard, clean, or overwrite. The current source-marker caveat remains: job_evaluations does not persist jd_experience_source. End-to-end fresh exact-JD/model/cache proof is still outstanding.
- Cross-reference docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md for compact state and docs/JOBBEEPER_REFERENCE.md for matching/rollout constraints.


## 2026-10-14: Both local target test suites passed; dev-only rebuild next

- User supplied actual SSH output for the Radar suite: `./.venv/bin/python -m unittest v2.test_radar` completed with 88 tests in 18.796s, result OK. Test logs include expected warning/log paths for intentionally failed ATS-board fixtures and simulated LinkedIn 429/backoff cases; the suite's final result is successful.
- The preceding Gemini extractor suite passed 14 tests in 0.108s with result OK. These are local unit-test results from the VM checkout after the fast-forward to bcb8cfc. Together, the two requested suites passed. The docs-only commits added after that checkout may advance the remote branch but do not affect the already-run app code; don't misstate these results as testing later application changes if new code is added.
- User's latest visible status had `M v2/config.json` and `?? .venv/`; preserve both. No runtime rebuild, environment flag change, DB/cache inspection, schema change, or notification action has occurred in this turn.
- **Next exact action:** run the previously approved development-only rebuild using the existing explicit environment file and named volume:
  ```bash
  cd ~/job-beeper-dev
  sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar
  ```
  This approval covers only the isolated dev `radar` service and existing volume `job-radar-dev_radar-dev-data` mounted at `/data`. Do not run `docker compose down`, create/remove volumes, access or broadly mutate SQLite, change production, or replay historical notifications. If the command errors or authorization differs, stop and return the complete output.
- After the rebuild, gather read-only evidence: container status, key presence only (never key value), model and extraction/matcher flags, health at `http://127.0.0.1:8001/health`, and a sanitized `/api/llm-shadow-status`. Do not print full status JSON or source/job identifiers, titles, descriptions, evidence quotes, skill lists, API keys, config tokens, or complete DB rows. Confirm `matcher_enabled=false` and sanitized response redaction.
- Both feature gates remain false. Once redaction and runtime flags are verified, ask separately for explicit approval to enable only shadow extraction; do not flip either flag automatically. The goal remains fresh exact-current-JD/model/hash/TTL cache proof, accepted only for required total-professional experience with exact evidence, confidence >= 0.85, and at least one range bound, then bridge and persisted evaluation verification. Current `job_evaluations` schema does not persist `jd_experience_source`.
- Turn record: no app code change; both requested local suites passed; handovers updated directly on GitHub. Cross-reference the compact state in `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and engineering/rollout guardrails in `docs/JOBBEEPER_REFERENCE.md`.


## 2026-10-14 late update: Dev image rebuilt; safe runtime verification pending

- User supplied actual output for the previously approved command from ~/job-beeper-dev: the dev image job-radar-dev-radar built successfully (BuildKit reported 14/14 steps FINISHED; new image manifest exported), and Compose reported the job-radar-dev container Started. The build context was 68.52 kB and .dockerignore was loaded. This is evidence the image build and container start command completed; it is not yet proof of post-start health, effective container environment, status endpoint redaction, fresh extraction, or matcher behavior.
- Both local suites had passed before this rebuild: v2.test_gemini_extractor (14 tests, 0.108s, OK) and v2.test_radar (88 tests, 18.796s, OK). User checkout had fast-forwarded to bcb8cfc before the docs-only commits recorded later on GitHub. No source-code commits were added by those subsequent handover updates.
- Next action: request read-only verification output from the current dev runtime. Do not enable extraction or matcher. Use the commands below; do not print full status JSON or secrets:
  1. Container state: sudo docker ps --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'
  2. Safe env allowlist only: sudo docker exec job-radar-dev sh -c 'if [ -n "$GEMINI_API_KEY" ]; then echo gemini_key=configured; else echo gemini_key=empty; fi; printf "model=%s\nextraction=%s\nmatcher=%s\n" "${GEMINI_MODEL:-unset}" "${GEMINI_EXTRACTION_ENABLED:-unset}" "${GEMINI_MATCHER_ENABLED:-unset}"'
  3. Health: curl -fsS http://127.0.0.1:8001/health
  4. For the status endpoint, return only whitelisted fields and whether forbidden/raw keys occur; do not print raw JSON. A redacted checking script is supplied to the user in the current conversation.
- Expected/required runtime checks: key presence only (never value), model gemini-3.5-flash-lite, extraction=false, matcher=false, health status=ok, and status endpoint redaction (no source identifiers, job IDs, titles, raw extraction payload/result, verbatim evidence, or skill lists). The status endpoint should report matcher_enabled=false. A successful health response or configured key does not prove extraction/cache/matcher behavior.
- No extraction/matcher flag was changed by the rebuild. No database rows were read or modified, no volume action was performed, and production/notifications/Telegram/LinkedIn remain untouched. Preserve VM-local M v2/config.json and ?? .venv/; never stage, overwrite, reset, or clean them.
- Once these checks pass, ask separately for explicit permission to set only GEMINI_EXTRACTION_ENABLED=true in VM-local ignored .env. Keep matcher false. This uses the Gemini API (current cap up to 3 calls/source run and 20/day) and writes shadow-cache rows to the existing isolated development DB. Do not proceed until approval. End-to-end cache/matcher proof and any matcher approval remain outstanding. The current job_evaluations schema does not persist jd_experience_source.
- Cross-reference: compact status in docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md; architecture and rollout guardrails in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-14 late update: Rebuilt runtime and status redaction verified; extraction approval gate next

- User supplied live post-rebuild verification: container `job-radar-dev` is Up using image `job-radar-dev-radar`; filtered runtime output confirms Gemini key is configured (value not printed), model `gemini-3.5-flash-lite`, `GEMINI_EXTRACTION_ENABLED=false`, and `GEMINI_MATCHER_ENABLED=false`.
- `http://127.0.0.1:8001/health` returned status `ok`, version `2.0.0`, and database path `/data/jobs.db`. The source status snapshot showed no error at that instant. This is health evidence only; it does not prove Gemini extraction, current-JD cache eligibility, or matcher behavior.
- Sanitized `/api/llm-shadow-status` fields returned: `enabled=False`, `matcher_enabled=False`, `api_key_configured=True`, model `gemini-3.5-flash-lite`, mode `shadow_only`, daily limit 20, calls_today 0, cache successes 14, cache errors 6. Recursive forbidden-key check returned `forbidden_fields_present=none` and `shadow_status_check=ok`. This verifies the observed endpoint response contains none of the checked identity/title/raw-extraction/evidence/skill field names; do not use stale sample counts as proof of fresh extraction.
- Test evidence remains: user ran `v2.test_gemini_extractor` with 14 tests in 0.108s, OK; and `v2.test_radar` with 88 tests in 18.796s, OK, on the VM code pulled to `bcb8cfc`. The later GitHub changes this turn are handover-only; no application source code was changed.
- **Current status:** development build/recreate and safe runtime verification completed. No API call was made for extraction because the extraction gate remains false. No DB/cache row inspection, cache write, schema modification, production action, notification replay, or volume operation occurred. Preserve local `M v2/config.json` and `?? .venv/` exactly.
- **Next gate requires explicit user approval:** ask whether to enable shadow extraction only by setting `GEMINI_EXTRACTION_ENABLED=true` in the VM-local ignored `.env`, while explicitly keeping `GEMINI_MATCHER_ENABLED=false`. It will use the Gemini API and may make up to 3 calls per source run and 20 per day under current configuration, and it writes structured shadow-cache records to the existing development DB. Matching decisions remain unchanged while matcher is false. Do not alter `.env` or recreate the container until user approves.
- If approved, update only the extraction flag in the ignored local `.env` without echoing the file/secrets, ensure the matcher flag remains false, recreate only the dev `radar` service using the existing explicit env file/project/volume, then verify safe settings and wait for actual fresh extraction activity. Use sanitized diagnostics only.
- Before requesting matcher approval later, prove a fresh successful cache entry for exact current job input/hash and configured model within TTL, classified `required` + `total_professional`, with verbatim evidence, confidence >= 0.85, and at least one range bound. Prove `_job_for_canonical` returns `jd_experience_source=gemini_verified` and the persisted `job_evaluations` contains expected experience bounds/reasons. The schema does not persist the source marker; do not claim it does.
- Cross-reference `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` for compact operational state and `docs/JOBBEEPER_REFERENCE.md` for matcher and rollout guardrails.


## 2026-10-14 late update: User approved development shadow extraction

- User explicitly approved enabling shadow extraction in the isolated development environment only. This authorizes setting only GEMINI_EXTRACTION_ENABLED=true in the VM-local ignored .env while preserving GEMINI_MATCHER_ENABLED=false, followed by recreating only the dev radar service with the explicit env file and existing project/volume.
- This is an approval record, not proof that the VM-local file or running service has been changed yet. The agent cannot directly edit the VM filesystem in this chat; the next step is to provide a guarded SSH command for the user to execute and wait for its output.
- Safety/usage impact: calls the configured Gemini API and writes structured shadow-cache rows into the existing isolated development DB. Existing caps are up to 3 calls per source run and 20 per day. Matching decisions must remain unchanged while the matcher gate is false. Do not print .env contents or the key; do not change any other env setting.
- Guard command requirements: stop if .env is missing; reject duplicate extraction/matcher assignments or a matcher assignment other than explicit false; change/append only GEMINI_EXTRACTION_ENABLED=true; suppress inherited shell flag overrides for the Compose invocation so the .env extraction setting and default-false matcher gate take effect; use only the approved sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build radar command. Do not use down or volume commands.
- After execution, await output and then request safe read-only checks: container status, Gemini key presence only, model and both flags, health, sanitized shadow status, and absence of source IDs/titles/JD/evidence/skills. Do not claim extraction success from startup, key configuration, health, or aggregate counters. Wait for actual new shadow extraction activity.
- Required later proof before matcher approval remains a fresh exact-current-JD/hash/model/TTL cache success, required total_professional scope, verbatim evidence, confidence >= 0.85, a range bound, bridge source jd_experience_source=gemini_verified, and persisted evaluation bounds/reasons. job_evaluations does not persist the source marker. Matcher activation still requires a separate explicit approval.
- No VM .env change or runtime action has yet been confirmed from this approval alone. Preserve VM-local M v2/config.json and ?? .venv/. No production changes, historical notifications, Telegram/LinkedIn enablement, DB schema or volume changes.
- Cross-reference docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md and docs/JOBBEEPER_REFERENCE.md.


## 2026-10-14 late update: Shadow extraction enabled in dev .env; new container started, verify before assuming flags

- User ran the guarded SSH command after explicitly approving development shadow extraction. Its local guard output was extraction_flag=true, matcher_flag=explicit_false, env_contents=not_printed. It updated only GEMINI_EXTRACTION_ENABLED in the VM-local ignored .env; the matcher assignment was confirmed false and no secrets were printed.
- The approved explicit-env Compose command then completed: BuildKit reported 14/14 steps FINISHED, the job-radar-dev-radar image built, and Compose reported job-radar-dev Started. The build used the current source tree and existing dev project. This is command/build evidence only; post-start runtime values, health, and actual new shadow extraction still need fresh observation.
- No output yet confirms inside-container GEMINI_EXTRACTION_ENABLED=true or actual Gemini activity. Do not infer extraction success from .env content or container startup. Do not enable matcher.
- **Next action:** run read-only post-start checks: container status; safe environment check showing Gemini key presence only plus model/extraction/matcher; GET health; and Python sanitizer for /api/llm-shadow-status that prints only allowlisted summary and safe recent-result fields (status, model, timestamp, error code, experience bounds/type/scope/confidence, evidence-present boolean, shape-eligible boolean). Never print raw response JSON, source/job IDs, titles, JD descriptions, verbatim evidence, skills, key, token, or DB rows. Expected: container Up, key configured, model gemini-3.5-flash-lite, extraction true, matcher false, health ok, endpoint enabled=true/matcher_enabled=false, forbidden private fields absent.
- After verification, wait for genuine fresh shadow-extraction activity. Calls are capped at up to 3 per source run and 20 per day, and successes write structured shadow-cache rows to the existing dev DB volume. Do not infer activity from previous totals (14 successes/6 errors) or stale timestamps. Report changes in calls_today/cache totals and sanitized recent result timestamps/status only; do not dump raw status output.
- End-to-end target still not proven: freshness and eligibility need exact current JD input/hash, configured model and TTL, required + total_professional type/scope, verbatim evidence present, confidence >=0.85, at least one range bound, bridge consumption via _job_for_canonical with jd_experience_source=gemini_verified, and persisted job_evaluations bounds/reasons. The job_evaluations schema does not persist jd_experience_source. Only after that proof ask separately for matcher activation approval.
- No matcher change, production change, notification replay, volume lifecycle, broad DB inspection, or schema migration occurred. Preserve M v2/config.json and ?? .venv/. Cross-reference the compact knowledge transfer and JOBBEEPER_REFERENCE.md.


## 2026-10-14 late update: Fresh shadow cache observed; exact-hash diagnostic added

- User's post-enable safe runtime output confirms job-radar-dev Up, Gemini key configured (value never exposed), model gemini-3.5-flash-lite, extraction true, matcher false, health ok, and sanitized shadow endpoint redaction passed with forbidden_fields_present=none.
- Fresh activity is now observed: calls_today=6, cache_successes increased from 14 to 20, cache_errors=6. Several new successful results have timestamps on 2026-10-14. One recent shape-eligible sample is required + total_professional, has verbatim evidence present, confidence 0.95, and at least one bound. Other recent results are skill-specific or unknown-scope and therefore correctly shape-ineligible. This is evidence of fresh extraction calls/cache writes and a trusted-shape candidate, but the status endpoint does not prove the cache input hash corresponds to the exact current job row or that the matcher consumed it.
- Implemented a safe network-free diagnostic directly on v2-live-radar: v2/gemini_experience_diagnostic.py, with regression tests v2/test_gemini_experience_diagnostic.py. It opens the live DB via SQLite read-only URI; selects only a job seen within the last 24h whose recomputed exact _input_hash matches a successful current-model cache row; applies the current model, TTL and trusted result/evidence gates; checks the existing live evaluation by booleans/numeric bounds only; then copies just the selected job/cache row into a disposable temporary DB and runs _job_for_canonical plus _persist_job_evaluation there while matcher=true is scoped to this diagnostic process only. The temporary DB is deleted afterward. No Gemini API call is made, the running container env is unchanged, no live DB write or notification is performed, and output omits job IDs/titles/JD/evidence/skills/secrets.
- Regression tests cover a fresh exact-hash trusted result (including bridge marker and sandbox evaluation bounds/reason), mismatched JD hash, expired cache, and skill-specific result rejection. Test assertions ensure no API call occurs. These new tests have NOT been run yet; don't claim they pass.
- GitHub compare from the VM's prior code revision bcb8cfc to the current branch shows only the two handover docs plus these diagnostic utility/test files changed; app core modules did not change since the tested/rebuilt code.
- Next user step: fast-forward the checkout without disturbing local files, then run the new focused test:
  
      cd ~/job-beeper-dev
      git status --short
      git pull --ff-only origin v2-live-radar
      git rev-parse --short HEAD
      ./.venv/bin/python -m unittest v2.test_gemini_experience_diagnostic

  Preserve M v2/config.json and ?? .venv/. Stop on pull failure/conflict or test failure. Do not rebuild merely to use the diagnostic: after the test passes, execute the checked-in diagnostic source through stdin inside the current app container so it imports the already-deployed core code:
  
      sudo docker exec -i -w /app job-radar-dev python - < v2/gemini_experience_diagnostic.py

  It reads /data/jobs.db read-only and writes only a disposable temporary SQLite file. Return complete output, which contains redacted flags/evidence booleans and numeric bounds only; no raw JSON or job details.
- Acceptance for candidate: diagnostic_status=candidate_verified, exact_current_input_hash_match=true, cache_status=ok, cache_model_matches=true, cache_age_within_ttl=true, required + total_professional, evidence present, confidence >=0.85, at least one bound; sandbox bridge source verified, sandbox evaluation row written, persisted sandbox bounds match cache, and experience reason present. Review live_evaluation_bounds_match_cache and live_evaluation_experience_reason_present separately: these refer to the original existing persisted row, not the sandbox. If the original row doesn't reflect the expected bounds/reasons, do not claim the real DB evaluation is proven.
- Matcher remains disabled globally. Only after the exact-hash and evaluation diagnostics are reviewed can we decide whether all preconditions are met and ask separately for approval to enable GEMINI_MATCHER_ENABLED=true. Do not set it automatically. Existing job_evaluations schema has no jd_experience_source column; the diagnostic reports schema presence dynamically and does not change it.
- Keep existing 3-calls-per-source-run and 20-calls/day caps; current observed calls_today is 6, so the configured daily cap has not been hit. No production, Telegram/LinkedIn, notification replay, live DB write, or schema migration occurred. Preserve local v2/config.json and .venv/.
- Cross-reference docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md and docs/JOBBEEPER_REFERENCE.md.


## 2026-10-14 late update: Exact-hash diagnostic regression tests passed; live read-only probe next

- User supplied actual VM output after fast-forward: checkout advanced from bcb8cfc to b427bab with no reported conflict; the new diagnostic suite `./.venv/bin/python -m unittest v2.test_gemini_experience_diagnostic` completed with 4 tests in 0.336s, result OK.
- The initial git status lines were not visible in the pasted output; preserve `v2/config.json` and `.venv/` if present and never stage, reset, clean, or overwrite them.
- No live diagnostic has yet been run. The new diagnostic's unit tests confirm its fixtures for a trusted exact-hash fresh result and rejection of mismatched hashes, expired entries and skill-specific scope. This is test evidence, not proof the actual development database contains a qualifying current job.
- **Next command:** execute the local diagnostic script through stdin inside the existing running app container. The script source comes from the checked-out VM file; Python imports `v2.radar` and `v2.gemini_extractor` from the already-running image. It opens `/data/jobs.db` read-only, identifies at most one eligible candidate by re-computing the exact current job input hash and model/TTL checks, inspects persisted evaluation summaries, and invokes the bridge/persistence writer only on a temporary one-job SQLite database that is deleted afterward:
  
      cd ~/job-beeper-dev
      sudo docker exec -i -w /app job-radar-dev python - < v2/gemini_experience_diagnostic.py

  This command makes no Gemini API call, performs no write to the source database and triggers no notification. Return complete output; expected output contains only diagnostic status, booleans, model/timestamps/ages and numeric experience bounds, never IDs, titles, description, evidence, skills, secrets or whole rows.
- If the command returns no candidate (exit 3 with reason_code=no_fresh_trusted_exact_hash_candidate), don't infer a defect from counts alone; we'll inspect sanitized reasons and current job/cache coverage and decide the smallest justified next diagnostic. If it returns an error, stop and share only the diagnostic's own sanitized output.
- Acceptance requires exact hash match, current configured model, success status, cache age within TTL, job recently seen, required + total_professional classification, evidence present, confidence >= 0.85, one range bound, sandbox bridge source verified and bounds aligned, and sandbox evaluation row/bounds/experience reasons verified. Separately check the existing live evaluation values/reason booleans: sandbox evaluation is not itself proof that the live row already contains these bounds/reasons.
- Matcher remains false globally. Only after reviewing this output may we ask for separate matcher-enable approval. Current job_evaluations schema does not persist jd_experience_source. No app code changes or runtime/DB writes occurred in this turn.
- Cross-reference: compact operational state is in docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md; rollout guardrails are in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-14 — Exact current-hash Gemini candidate and isolated persistence verified

- User-provided redacted diagnostic selected a recent job/cache pair and returned `candidate_verified`: exact recomputed current input hash, cache status `ok`, correct model, cache age 538 seconds of a 30-day success TTL, and job last seen 606 seconds earlier. The trusted validated payload was required `total_professional`, minimum 3.0 and maximum 5.0 years, confidence 0.95, evidence present, and a range bound present.
- The diagnostic ran the actual bridge and persistence writer against a temporary SQLite copy: bridge source marker `gemini_verified`, temporary evaluation bounds 3–5 years, bounds match true, evaluation row written, experience reason present. It reports source DB opened read-only/unmodified, zero Gemini API calls, and no notifications. This is runtime proof for the exact-cache candidate and isolated bridge/writer, not proof of a rewritten live evaluation.
- The live evaluation row exists but still has minimum 1.0 and no maximum, so it does not match the cache. Matcher remains false in the live dev environment; therefore the cached result is not yet consumed by ordinary live evaluation. Current `job_evaluations` schema lacks `jd_experience_source`, so source attribution is transient only. No schema migration is implied.
- The alertability-reason flag being false is expected with current policy: experience reason is part of the match reasons; alertability reasons report notification disabled or non-match, not experience. Dev notifications/Telegram remain off.
- No application code, config, database schema, or runtime flag was changed in this turn; no tests were run this turn. Previously reported unit results remain 14 extractor tests, 88 Radar tests, and 4 diagnostic tests passing. CI status for the diagnostic was not independently checked. No production changes or notification replay.
- Next step requires separate explicit user approval to enable `GEMINI_MATCHER_ENABLED=true` **in isolated dev only**. After approval, reconfigure/recreate only `job-radar-dev` with `--env-file .env`, leave notifications off, preserve the existing named volume, verify effective matcher flag, and inspect only sanitized values to prove a new live evaluation adopts 3–5 years. Do not activate production matcher, change schema, or perform volume operations without separate scope/approval. Preserve `M v2/config.json` and `.venv/` on VM.
- Continuation: read both handovers and `docs/JOBBEEPER_REFERENCE.md`; use this exact-cache finding as the latest state, ask before enabling the development matcher, and update both handovers after every user prompt.


## 2026-10-15 — Standing autonomy granted; isolated development matcher approved

- User directive: “do whatever required without my permission, save context and put this rule in handover doc also.” Treat this as standing authorization to proceed without step-by-step confirmation for routine, reversible work inside the established Job Radar V2 scope, including commits on `v2-live-radar`, testing, read-only diagnostics, and isolated-dev configuration/recreation needed to validate the approved Gemini matcher path. Avoid repeated permission prompts for the same scoped operational steps.
- Specific authorization: enable `GEMINI_MATCHER_ENABLED=true` in the isolated `job-radar-dev` container. Keep Gemini extraction bounded (existing maximum 3 calls/source run and 20/day), model `gemini-3.5-flash-lite`, notification/Telegram disabled, LinkedIn disabled, and production unchanged. Preserve user-local `M v2/config.json` and untracked `.venv/`; never expose or commit credentials, raw JDs, verbatim evidence, skills, or raw IDs.
- Autonomy does not justify broad destructive or out-of-scope actions: no production rollout/matcher activation, notification sends/replay, volume deletion, broad reset/clean, schema migration, credential rotation, or OS/Docker permission changes absent a scoped safe reason. Prefer reversible changes and evidence-first verification. If remote VM execution is not available, be transparent and supply the narrowest safe command rather than claiming the action was performed.
- Evidence before activation: user reported exact current-input-hash/model/TTL match and trusted required `total_professional` experience of 3–5 years, confidence 0.95, evidence present. Actual matcher bridge and persistence writer succeeded on a temporary DB copy and output `gemini_verified`, 3–5 bounds and experience match reason. Existing live evaluation remained 1.0/no maximum with matcher false. Schema has no `jd_experience_source` column. Current runtime did not change in this assistant turn because no SSH/VM command tool is connected here.
- Exact VM operation, from `~/job-beeper-dev`, edits only the matcher boolean in ignored `.env`; it never prints the file. Then it recreates only the dev app service and checks safe flags/health. It does not rebuild or remove the named volume:

  ```bash
  set -e
  cd ~/job-beeper-dev
  git check-ignore -q .env || { echo 'STOP: .env is not git-ignored; no changes made'; exit 1; }
  python3 - <<'PY'
  from pathlib import Path
  p = Path('.env')
  if not p.is_file():
      raise SystemExit('STOP: .env not found; no changes made')
  lines = p.read_text().splitlines()
  key = 'GEMINI_MATCHER_ENABLED'
  matches = [i for i, value in enumerate(lines) if value.split('=', 1)[0].strip() == key]
  if len(matches) > 1:
      raise SystemExit('STOP: duplicate matcher settings; no changes made')
  new_line = f'{key}=true'
  if matches:
      lines[matches[0]] = new_line
  else:
      lines.append(new_line)
  p.write_text('\n'.join(lines) + '\n')
  print('GEMINI_MATCHER_ENABLED=true; .env contents not displayed')
  PY
  sudo docker compose --env-file .env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --force-recreate radar
  sudo docker exec job-radar-dev sh -lc 'printf "matcher="; printenv GEMINI_MATCHER_ENABLED; printf "extraction="; printenv GEMINI_EXTRACTION_ENABLED; printf "telegram_token_present="; test -n "$JOB_RADAR_TELEGRAM_BOT_TOKEN" && echo true || echo false; printf "telegram_chat_present="; test -n "$JOB_RADAR_TELEGRAM_CHAT_ID" && echo true || echo false'
  sudo docker exec job-radar-dev python -c "import json; d=json.load(open('/data/config.json')); print('notifications_enabled='+str(bool(d.get('notifications_enabled', True))).lower()); print('linkedin_enabled='+str(bool(d.get('source_enabled',{}).get('linkedin',False))).lower())"
  curl -fsS http://127.0.0.1:8001/health
  sudo docker exec -i -w /app job-radar-dev python - < v2/gemini_experience_diagnostic.py
  ```

- After safe config/health checks, continue without asking again: inspect allowlisted/sanitized LLM status and verify the actual live evaluation for the eligible candidate using only booleans/bounds/reason presence. If normal source scheduling must recompute evaluation, identify the lowest-risk existing path first; do not trigger extra Gemini calls unnecessarily, and do not infer success from the flag alone. Require persisted 3–5 bounds/reason proof. If verification fails, roll back only the dev matcher flag while preserving extraction and the existing volume; record the observed failure category without exposing sensitive content.
- Change in that prior turn: documentation only; VM/app source was not changed by the assistant session. The user's subsequent actual VM output confirms matcher enablement and live evaluation. No full test run in that turn; CI was not independently verified. Cross-reference `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md`.


## 2026-10-15 — Matcher flag applied; health probe reset; live verification pending

- User's actual VM output: the ignored `.env` update completed with matcher set to true (no secrets printed). Dev Compose said `Container job-radar-dev Started`. Effective in-container flags were `matcher=true`, `extraction=true`; Telegram token/chat presence were both false; config checks showed `notifications_enabled=false` and `linkedin_enabled=false`.
- The immediate health request then failed with `curl: (56) Recv failure: Connection reset by peer`, and SSH disconnected. The shell used `set -e`, so it exited at the failed health check and never ran the read-only Gemini diagnostic. No evidence yet distinguishes slow app startup, process/container restart/crash, OOM, or a VM/SSH issue. Do not claim health or end-to-end persisted evaluation passed.
- Next: reconnect and run read-only `docker inspect`/`docker ps` state, restart count, exit code, OOMKilled and health checks; if available, print only counts/booleans for relevant log patterns, not raw log lines; re-check safe environment/config flags. Probe `/health` with bounded retry/backoff in a shell that does not exit on one failed probe. If healthy, run the redacted exact-cache diagnostic through stdin and inspect live evaluation bounds/reasons. Do not force-recreate/rebuild again until the observed state is understood.
- Preserve the existing volume. Keep extraction and matcher as currently configured unless diagnosis shows an actual failure; if rollback is necessary, change only the dev matcher flag and keep notifications disabled. No production or notification activity occurred according to the supplied output. The exact cache was previously 3–5 years with confidence 0.95; isolated persistence passed in a temporary DB, but live persistence is unverified.
- No application source code or schema change in this turn. Handover only; no tests run. CI for diagnostic remains unverified. User's standing directive authorizes routine reversible project work without repeated confirmation, within guardrails in this document. Cross-reference `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` and `docs/JOBBEEPER_REFERENCE.md`.


### Safe follow-up commands — reconnect after health probe reset

Do not run another Compose lifecycle command yet. Reconnect to SSH, enter `~/job-beeper-dev`, and run the block below. It intentionally omits `set -e`: a failed health probe should not terminate the shell before the remaining read-only checks. Container logs are reduced to indicators/exception class names; raw lines are never printed.

```bash
cd ~/job-beeper-dev
echo '=== container status ==='
sudo docker ps -a --filter name=job-radar-dev --format 'container={{.Names}} status={{.Status}} image={{.Image}}'
sudo docker inspect job-radar-dev --format 'state={{.State.Status}} restarting={{.State.Restarting}} restart_count={{.RestartCount}} exit_code={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} error_present={{if .State.Error}}true{{else}}false{{end}} started={{.State.StartedAt}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
sudo docker inspect job-radar-dev --format 'mounts={{range .Mounts}}{{.Name}}:{{.Destination}};{{end}}'
echo '=== safe effective flags ==='
sudo docker exec job-radar-dev sh -lc 'printf "matcher="; printenv GEMINI_MATCHER_ENABLED; printf "extraction="; printenv GEMINI_EXTRACTION_ENABLED; printf "telegram_token_present="; test -n "$JOB_RADAR_TELEGRAM_BOT_TOKEN" && echo true || echo false; printf "telegram_chat_present="; test -n "$JOB_RADAR_TELEGRAM_CHAT_ID" && echo true || echo false' || echo 'effective_flag_check=unavailable_container_not_running'
echo '=== sanitized recent log indicators ==='
sudo docker logs --since 10m --tail 200 job-radar-dev 2>&1 | python3 -c 'import re,sys; s=sys.stdin.read(); print("recent_log_lines="+str(len(s.splitlines()))); pats={"traceback_present":r"Traceback \(most recent call last\)","error_marker_present":r"\bERROR\b","startup_complete_present":r"Application startup complete|Uvicorn running","sqlite_error_present":r"sqlite3?\.(?:OperationalError|DatabaseError)|database is locked|no such table","import_error_present":r"ModuleNotFoundError|ImportError","oom_marker_present":r"OOM|Killed process|out of memory"}; [print(k+"="+str(bool(re.search(v,s,re.I))).lower()) for k,v in pats.items()]; types=sorted(set(re.findall(r"\b[A-Za-z][A-Za-z0-9_]*(?:Error|Exception)\b",s))); print("exception_types="+(",".join(types[:10]) if types else "none"))'
echo '=== health retry (bounded; no shell-wide exit on failure) ==='
health_ok=0
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if curl --silent --show-error --connect-timeout 2 --max-time 4 -fsS http://127.0.0.1:8001/health -o /tmp/job-radar-health.json; then
    python3 -c 'import json; d=json.load(open("/tmp/job-radar-health.json")); s=d.get("sources") or {}; print("health_status="+str(d.get("status"))); print("version="+str(d.get("version"))); print("source_count="+str(len(s))); print("source_errors_present="+str(any(bool(v.get("error")) for v in s.values() if isinstance(v,dict))).lower())'
    health_ok=1
    break
  fi
  echo "health_attempt_${attempt}=failed"
  sleep 2
done
if [ "$health_ok" -eq 1 ]; then
  echo '=== redacted exact-cache/live-evaluation diagnostic ==='
  sudo docker exec -i -w /app job-radar-dev python - < v2/gemini_experience_diagnostic.py
else
  echo 'health_recovered=false; diagnostic_skipped=true'
fi
rm -f /tmp/job-radar-health.json
```

Return the state summary, sanitized log indicators, health result and diagnostic output. If container is restarting/OOM-killed/stopped, stop before any further restart and use the observed indicators to choose the smallest reversible recovery. If the health probe succeeds, the diagnostic will tell us whether the live evaluation now adopts 3–5 bounds and matching reasons. Never paste `.env`, raw logs, raw JSON endpoint payloads, job IDs/titles/JDs/evidence, or credentials.


- Command safety note: the current follow-up block reports only the presence (not contents) of Docker state errors and only boolean/count/exception-type log indicators; it never emits raw application log lines. It uses bounded health retries and deliberately has no `set -e`.

- Follow-up command correction: fixed the sanitized log-indicator expression to evaluate each pattern against the captured log text; it still emits no raw log messages.


## 2026-10-15 — Gemini matcher live evaluation verified after transient health reset

- User's follow-up runtime output confirmed `job-radar-dev` running and stable: status Up 14 minutes, `restart_count=0`, `exit_code=0`, `oom_killed=false`, `restarting=false`, no container error, existing `job-radar-dev_radar-dev-data:/data` mount retained.
- Effective flags `GEMINI_MATCHER_ENABLED=true`, `GEMINI_EXTRACTION_ENABLED=true`; Telegram token/chat absent, `/data/config.json` has `notifications_enabled=false` and `linkedin_enabled=false`. The previous health connection reset was transient: bounded retry returned `health_status=ok`, version 2.0.0, one configured source and no source errors.
- Read-only exact-cache diagnostic returned `candidate_verified`, configured model `gemini-3.5-flash-lite`, exact current input hash, cache status `ok`, model match, age 3008 seconds within the 30-day TTL, job last seen 616 seconds earlier within 24 hours. Trusted required total-professional bounds are 3.0–5.0 years, confidence 0.95, evidence present and range bound present.
- Crucially, live evaluation is now proven to match the cache: row present; min=3.0/max=5.0; `live_evaluation_bounds_match_cache=true`; one evaluation reason and `live_evaluation_experience_reason_present=true`. The sandbox bridge source `gemini_verified` and temporary persistence also remain verified. The diagnostic reports source DB read-only/unmodified, zero Gemini API calls and no notifications. Current evaluation schema still has no `jd_experience_source` column; do not claim source attribution persisted.
- This completes the specific dev acceptance target: exact-current-input trusted Gemini extraction → gated matcher → live persisted experience bounds/reason. It does NOT prove a Telegram send and no alert is to be sent: notifications and Telegram credentials are intentionally off.
- Next: autonomously run safe tests and inspect current VM Git status/branch/HEAD without touching local `M v2/config.json` or `?? .venv/`; fast-forward only if behind and safe. Review canonical opportunity/notification-ledger/dashboard API consistency while keeping dispatch disabled; then follow `docs/JOBBEEPER_REFERENCE.md`: Greenhouse freshness guard + GET-only two-poll one-board canary, then Ashby, Lever, SmartRecruiters individually, observability. Production promotion/activation requires separate controlled review. User's standing-autonomy directive remains active for routine reversible in-scope work; never ask the user to relay routine VM output when Claude Code has direct SSH access. Preserve volumes, secrets, config and local virtualenv.
- No source-code change or tests were run by this diagnostic turn; runtime evidence came from user output. Latest docs-only updates must be mirrored in `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`; production remains untouched.


## 2026-10-16 — Claude Code execution plan, status, and independent review worksheet
**This is the latest authoritative section.** It supplements, and where conflicts exist supersedes, older next-step instructions and continuation prompts below it. Keep the historical chronology; do not delete it to make the history look consistent.

### Roles and working agreement
- **Project goal:** deliver a stable, accurate, low-noise, always-on personal job radar: discover fresh roles from multiple sources → normalize and deduplicate → apply deterministic configurable matching with explainable reasons → persist canonical opportunity/evaluation/notification state → show consistent dashboard/API data → deliver only eligible, new alerts when explicitly enabled.
- **Claude Code is the implementer/operator.** Work from the user's local Windows machine. For VM tasks use the supplied local SSH identity directly:
  ```powershell
  ssh -i "C:\Users\avibh\Downloads\ssh-key-2026-10-07.key" ubuntu@130.210.27.197
  ```
  Keep the private key on the user's machine. Never copy, print, commit, or upload it or any secret. Do not use insecure SSH bypasses. When SSH works, Claude should execute commands itself and inspect outputs rather than asking the user to relay routine commands/results.
- **ChatGPT is the independent orchestrator/reviewer.** Check Claude's pushed handover replies, compare them with the source code, tests, GitHub commits/PRs and actual sanitized VM evidence. Flag drift, unsupported claims, unsafe actions, weak tests, or changes that undermine freshness, match correctness, dedupe, alert safety, and maintainability. Review findings and suggested fixes should be written back here (and the compact knowledge transfer) so Claude can respond in the same shared record.
- **Standing authorization:** the user authorizes routine in-scope reversible engineering, test, documentation and dev-VM work without asking permission at every step. This specifically includes the already-approved matcher flag in isolated dev. This does not authorize production cutover, real notification sends/replay, volume deletion, broad reset/clean, secrets disclosure, bypassing host key checks, or other destructive/security-sensitive/out-of-scope changes. Keep production untouched and Telegram/notifications off unless separately reviewed and explicitly authorized. Preserve VM-local `M v2/config.json` and untracked `.venv/`; never stage/reset/clean/overwrite them.
- **Communication rule:** do not make the user an intermediary between Claude and the VM. Surface material blockers, unsafe conditions, or genuine decision points early. Do not report an operation/test/deployment as complete without actual command output or equivalent authoritative evidence.
- **Required documentation cadence:** before closing every task, Claude must update both `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, recording exact evidence, paths, commits/PRs, tests/CI, deployment status, risks, next action and continuation prompt. Push to `v2-live-radar`; do not promote/merge production changes as part of routine development. Re-fetch both pushed files to verify. Keep this worksheet and Claude's answers in the same detailed handover file, not a separate untracked note.

### Verified current state — distinguish completed from remaining
**Completed for the narrow Gemini experience objective (user VM output, 2026-10-15):**
- Isolated dev container `job-radar-dev` running, existing volume `job-radar-dev_radar-dev-data:/data` retained, no restart/OOM indication in the latest supplied output.
- `GEMINI_EXTRACTION_ENABLED=true`, `GEMINI_MATCHER_ENABLED=true`; model `gemini-3.5-flash-lite`; Telegram token/chat absent; `notifications_enabled=false`, LinkedIn disabled. Health check eventually returned OK, version 2.0.0, no source error. An earlier connection reset was transient; bounded retry recovered without a further restart.
- The read-only live diagnostic selected a fresh exact-current-input-hash/model-matched cache entry within TTL. It was `required`, `total_professional`, 3–5 years, confidence 0.95, evidence present and had a bound. The **live** `job_evaluations` row then had min=3.0, max=5.0, bounds matched the cache and an experience reason. The diagnostic made zero Gemini API calls and no source DB changes/notifications.
- The isolated temporary-database bridge test also passed with transient `jd_experience_source=gemini_verified`. The production DB/service was not touched. Current `job_evaluations` schema still does not persist `jd_experience_source`.

**Not yet completed:**
- A coherent end-to-end verification of canonical opportunity → evaluation → notification ledger/API/dashboard payload with all delivery disabled; no claim that a Telegram send was tested.
- Safe verification that the current VM checkout, local development checkout and GitHub `v2-live-radar` point to known commits; preservation of local config/venv must be confirmed, not assumed.
- Greenhouse one-board, two-poll dev canary with reliable source posting-time validation and no historical backlog alerts.
- Ashby, Lever and SmartRecruiters adapters/canaries; source-health observability.
- Reviewed production-promotion PR, CI, and controlled cutover. Keep these behind separate review gates; do not perform production cutover as a side effect of dev work.

### Roadmap / execution order
1. **Reconcile current reality first:** read this file, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`; inspect current GitHub branch/head/open PRs and compare with the local checkout and VM deployment. Connect via the SSH command above. Report the VM branch/HEAD/status and container/image status without secret output. Never overwrite local `v2/config.json` or `.venv/`.
2. **Test the current baseline:** run the focused Gemini suites and full unit suite on the exact checkout; report actual commands and complete exit/result summaries. Check GitHub CI for the exact commit. Investigate failures; do not skip/falsely summarize them.
3. **Validate decision consistency with dispatch disabled:** trace one eligible canonical opportunity through stored job → `job_evaluations` → canonical opportunity selection → notification ledger decision → API → dashboard rendering. Use dry-run/test fixtures or read-only inspection. Never add real Telegram credentials, enable dispatch, send a message or replay historical alerts to prove this path.
4. **Greenhouse freshness guard and canary:** inspect the existing adapter, its actual upstream timestamp semantics, and current tests first. Implement a trustworthy publication-time guard only using a genuine upstream posted/published timestamp; do not use discovery/first-seen time as a substitute. If timestamp is missing/ambiguous, keep freshness unknown and do not present it as newly posted. Use only GET requests for one configured dev board, at least two polls, notifications disabled, and prove stable IDs, timestamp behavior, no duplicate/old-job alerting and useful yield. Keep the source globally disabled until the evidence-based canary gate is met.
5. **Add ATS sources individually:** Ashby, Lever, then SmartRecruiters as a starting order, subject to documented public endpoint availability and expected value. For each adapter require fixtures/tests, stable IDs, direct URL, timestamps, pagination, rate-limit/backoff, source health, normalization, dedupe, relevance yield and a disabled-by-default/two-poll canary. Do not implement all three at once or enable them globally without separate measured acceptance.
6. **Observability:** add source-level fetched/normalized/relevant/new/deduplicated/error/429 metrics and freshness-lag measurements before increasing polling volume. Preserve LinkedIn stop-on-429/cooldown behavior.
7. **Schema/source attribution proposal:** decide whether storing `jd_experience_source` is materially needed for auditing/UI/debugging now that the main Gemini path is proven. Analyze migration safety, backwards compatibility, all schema/init/migration paths, current readers/writers/API/dashboard impact and tests first. Do not add a column only because it was suggested in an initial analysis; provide evidence and a design proposal in the worksheet for independent review before a schema migration.
8. **Production promotion:** only prepare a reviewed PR after dev tests, canaries, fresh-data correctness, dashboard/ledger coherence and rollback plan pass. No production ref switch/rebuild, alert replay or real Telegram test as part of this sequence. Keep `main` and `v2-live-radar` roles explicit and confirm exact commit/CI/runtime diffs before any later controlled cutover.

### Claude Code — reply to this questionnaire in this same file
**Instructions for Claude:** fill in each `CLAUDE RESPONSE` area beneath its question. Keep the original questions and prior handover facts. Be concrete: cite file paths/functions/tests/commit hashes or PR links, quote safe output summaries, distinguish observed facts from assumptions, and list trade-offs. Then push the edited handover plus compact knowledge transfer directly to `v2-live-radar` and report the commit SHA. Do not claim ChatGPT accepted your answers; the orchestrator will independently review the pushed version. You may perform read-only checks while preparing answers, but do not start a schema migration, globally enable another source, or touch production before this review.

#### Q1 — Source-of-truth and deployment alignment
Which exact GitHub branch/head, local Windows checkout branch/head/status, and VM checkout/deployed image/commit were observed? Are there local modifications, open PRs, unpushed commits, or code differences between checkout, image and branch? How will you update safely without touching `M v2/config.json` or `.venv/`?
- **CLAUDE RESPONSE:** Pending — answer with command summaries and SHAs; redact secrets.

#### Q2 — End-to-end goal coverage
For the pipeline `source → normalized job → canonical opportunity/dedupe → job_evaluation → notification ledger decision → API → dashboard`, which segments have real evidence today, which have only unit/sandbox evidence, and what is the smallest test plan to close gaps while notifications remain disabled? What exactly is the dashboard's freshness/ranking behavior and is it consistent with persisted state?
- **CLAUDE RESPONSE:** Pending — cite functions, API handlers, frontend paths and tests. Do not send an alert.

#### Q3 — Should `jd_experience_source` become a persisted DB field?
What real user-facing/debugging/observability need would the column solve, given current live bounds/reasons already match Gemini but the transient source marker is not stored? Describe benefits versus migration complexity, schema/version/init/migration paths, old-database compatibility, API/dashboard consumers and rollback. Recommend one of: (a) keep the current schema, (b) add the field in a separate reviewed migration, or (c) store provenance elsewhere. Do not implement the migration before posting the analysis here.
- **CLAUDE RESPONSE:** Pending — include a minimal migration/test design if you recommend (b).

#### Q4 — Greenhouse freshness guard
Which exact upstream Greenhouse timestamp field is available, and how do you establish its semantics from current API response/fixtures? How will old existing postings be kept from looking new when first imported? How will missing/invalid timestamps be handled without inventing freshness or dropping them into the alertable feed as new?
- **CLAUDE RESPONSE:** Pending — cite collector function, source fields and fixtures; no live writes/alerts.

#### Q5 — Two-poll one-board canary acceptance
Define a deterministic two-poll protocol and pass/fail thresholds for stable IDs, direct URLs, posted-time coverage, duplicate prevention, older-than-72-hour filtering, unknown-date behavior, source errors, relevant/new yield and rate limits. What exactly is isolated to dev and how do we prove Telegram cannot dispatch?
- **CLAUDE RESPONSE:** Pending — commands, metrics and sanitized output shape.

#### Q6 — ATS adapter order / source feasibility
For Ashby, Lever and SmartRecruiters, identify documented public read endpoints, required company/board identifiers, pagination, timestamp fields, stable ID/URL fields, request limits and expected maintenance burden. Why is your order best for this project's free-first relevance goals? Define one-source-at-a-time completion criteria.
- **CLAUDE RESPONSE:** Pending — document sources/uncertainties; do not assume unauthenticated global access.

#### Q7 — LinkedIn stability and experience parser changes
What is the current status of the labeled-experience parsing fix/PR (including PR #36 if relevant), has it been tested on the actual `v2-live-radar` commit and deployed dev image, and does any change risk a live request in unit tests? How are 429 stop/cooldown semantics protected? Are dates and experience taken from true source metadata?
- **CLAUDE RESPONSE:** Pending — list tests actually run and live-call guards.

#### Q8 — Production promotion / acceptance gates
What objective gates must pass before a PR from `v2-live-radar` to `main` is proposed? Include current tests/CI, source canaries, DB/config compatibility, dashboard, rollback, secret separation, production volume preservation and notification safety. Which steps are intentionally excluded from this phase?
- **CLAUDE RESPONSE:** Pending — production stays unchanged; no switch/rebuild/alerts.

#### Q9 — Current risks and drift check
Compare your original analysis and plan against this authoritative handover. Which recommendations are accepted as-is, revised, or rejected (and why)? Call out any plan duplication/inconsistency, unsupported facts, stale handover claims, unnecessary scope or implementation that could cause old/stale jobs to alert as new.
- **CLAUDE RESPONSE:** Pending — give risk ranking and exact files/functions to address.

#### Q10 — Next increment
Based on the verified state and answers above, what is the **single smallest, highest-value next development increment**? State the hypothesis, exact files, tests first, implementation, expected observable outcome, rollback, and why this comes before the remaining roadmap. Do not list multiple parallel projects.
- **CLAUDE RESPONSE:** Pending — choose one increment only and justify it.

### Orchestrator review checklist — independent review, 2026-10-16

- **Repository/commit reviewed:** Confirmed `v2-live-radar` exists and fetched all three required documents from that ref. Handover blob SHA before this review: `88837452dc26d24ec18d8873b2cf2f23f79ad948`; knowledge-transfer blob SHA observed before this review: `3d9c889bca46329a3ad65d0e201e0a2fccf8a5a7`; reference blob SHA: `4c7d51e2b429958bbe552e760b8c3de1b6c7025b`. The connected GitHub branch-search response exposes the branch name but not its current commit SHA, and the commit-search response did not establish the current ref head. Therefore the previously observed head `694c0a3b4e3b64677783414a5f6f1d49aca3f822` is **not independently confirmed as current**; do not claim a head-level review or CI result until the branch head is obtained from GitHub. The fetched current handover still has Q1–Q10 all marked **CLAUDE RESPONSE: Pending**. No pushed Claude answers were present in the content fetched for this review. This is a blocking evidence gap, not proof that Claude did no work locally.
- **Claude's answers evaluated against current source and actual VM evidence:** **Not yet possible for Q1–Q10** because there are no answers in the fetched document. The reviewer independently inspected the current checked-in versions of `v2/gemini_experience_diagnostic.py`, `v2/test_gemini_experience_diagnostic.py`, `v2/greenhouse_canary.py`, and `v2/docker-compose.dev.yml`. The diagnostic is explicitly read-only against its source DB and exercises the real bridge/persistence writer only in a disposable DB; its four tests cover accepted fresh/exact-hash/model-matched cache, hash mismatch, expiry, and skill-specific scope. The canary is a two-snapshot ID/timestamp-coverage report only: it does **not** itself implement a freshness guard, reject postings older than 72 hours, validate timestamp semantics, or prove dispatch is disabled. The dev Compose file binds port 8001 to loopback, mounts a separate named volume at `/data`, and hard-blanks Telegram credentials; it defaults Gemini flags off unless VM-local environment overrides them. User-provided sanitized VM output recorded above is accepted as reported runtime evidence, not a direct VM inspection by this reviewer. No SSH shell was available; no tests were run in this review; CI for the current branch head was not verified.
- **Goal alignment:** The narrow Gemini experience objective is supported by the recorded user diagnostic and the code's disposable-database test design. The overall product acceptance criterion remains **incomplete**: there is no independent evidence in this turn for canonical opportunity → persisted evaluation → notification ledger → API → dashboard consistency. Greenhouse freshness and the two-poll canary are not yet proven by the existence of a canary utility alone.
- **Q1 verdict — source-of-truth/deployment alignment:** **Unanswered / unsupported.** Need exact remote branch HEAD SHA, Windows checkout branch/HEAD/status, VM checkout HEAD/status, container image/revision, open PRs and CI. Never overwrite `M v2/config.json` or untracked `.venv/`; use read-only status/diff first and only fast-forward when safe.
- **Q2 verdict — end-to-end goal coverage:** **Unanswered / not proven.** Diagnostic verifies a cache-to-evaluation segment, not the full canonical opportunity/ledger/API/dashboard chain. Require fixture-backed integration coverage and sanitized read-only runtime corroboration with delivery off.
- **Q3 verdict — `jd_experience_source` persistence:** **Unanswered.** Current schema absence is confirmed by the fetched diagnostic test asserting `source_marker_in_job_evaluations_schema == false` and by the handover. Recommendation for now: **keep schema unchanged** until a concrete audit/debugging consumer is identified. If later justified, propose a separate migration with old-DB startup/upgrade/rollback tests and API/dashboard compatibility analysis; no migration now.
- **Q4 verdict — Greenhouse freshness guard:** **Unanswered; implementation not demonstrated by the canary utility.** `v2/greenhouse_canary.py` reports whether normalized jobs have `source_posted_at`, but does not establish the upstream field's semantics or enforce freshness. Inspect `radar.greenhouse_collect`, real sanitized fixture shape and existing tests. Never substitute discovery/first-seen time for publication time. Missing/invalid dates must remain unknown/non-fresh and must not be advertised as newly posted.
- **Q5 verdict — two-poll canary acceptance:** **Unanswered / incomplete if presented as an acceptance gate.** The utility performs two calls and reports stable/new/missing IDs and timestamp coverage, but the report alone has no pass/fail thresholds, 72-hour filter, duplicate-alert proof, relevance/new yield, latency, rate-limit metrics, or proof of the running service's dispatch gate. Define these checks before interpreting a report as a pass. The utility itself reports no DB writes, matching or notifications; that is useful but not equivalent to proving the scheduler cannot dispatch.
- **Q6 verdict — ATS feasibility/order:** **Unanswered.** Do not implement all adapters together. Verify each documented public endpoint, board/company identifier, timestamp and pagination semantics, stable IDs, backoff, health isolation and measured relevant/new yield before starting the next.
- **Q7 verdict — LinkedIn parser/stability:** **Unanswered in the worksheet.** Search returned historical PR/commit evidence for PR #36 and commit `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d`, but that alone does not establish current branch head, dev deployment, or that tests avoid real network calls. Inspect the actual current commit and targeted tests/CI; retain stop-on-429/cooldown behavior.
- **Q8 verdict — production gates:** **Unanswered.** Keep production unchanged. Promotion must require exact-head CI, current-checkout tests, fresh-source canary evidence, ledger/API/dashboard consistency, DB/config compatibility, secret separation, volume preservation, and documented rollback. No production ref switch/rebuild, real notification, or replay in this phase.
- **Q9 verdict — drift/risk review:** **Unanswered.** Key risks to investigate are stale jobs being treated as new, conflating discovery time with posted time, claiming canary acceptance from timestamp coverage alone, unverified deployed revision, and treating the Gemini one-candidate result as whole-pipeline acceptance.
- **Q10 verdict — single next increment:** **Unanswered.** Independent recommendation: add/execute a narrowly scoped, delivery-disabled integration test for one canonical opportunity through persisted evaluation, notification-ledger decision, API payload and dashboard-facing fields. First inspect current routes/ledger/UI contracts and existing fixtures; assert one consistent canonical ID, evaluation/reasons and freshness fields; assert dispatch remains disabled and no network send is possible. This closes a current product-integrity gap before adding sources or schema fields.
- **Accepted recommendations:** Keep schema unchanged pending demonstrated need; continue one issue at a time; maintain delivery disabled; use real upstream publication timestamps only; test one ATS adapter at a time; preserve local config, virtualenv and volume.
- **Modified recommendations:** Treat `v2/greenhouse_canary.py` as a diagnostic snapshot comparator, not a freshness guard or a pass/fail canary gate. Add explicit acceptance criteria and separate upstream timestamp semantics validation.
- **Rejected for now:** Any schema migration without a concrete consumer and rollback analysis; any additional globally enabled source before the first-source canary; any production rollout, notification send/replay, volume deletion or broad reset.
- **Required changes/tests before continuing:** (1) Claude must populate Q1–Q10 with evidence in this same file and push both handovers; (2) obtain actual current branch HEAD and compare it with `694c0a3b4e3b64677783414a5f6f1d49aca3f822`; (3) run focused Gemini tests plus full unit suite on that exact checkout and capture exit codes; (4) fetch CI/status for the exact head; (5) implement/test the canonical opportunity → evaluation → ledger → API/dashboard consistency increment with notifications off; (6) separately specify Greenhouse timestamp field semantics and canary pass/fail criteria. Do not claim CI or tests passed without results.
- **Decision on provenance schema proposal:** **Defer; no column or migration now.** The current live bounds/reasons meet the narrow matching target. Source attribution is transient, but no concrete user-facing/debugging requirement has yet justified the migration cost.
- **Decision on Greenhouse freshness/canary proposal:** **Do not treat as accepted yet.** Review the collector's actual upstream timestamp mapping and add old/missing/invalid timestamp fixtures. The existing two-poll utility is read-only and useful for ID stability/coverage, but it is not itself a freshness guard and does not enforce the roadmap's >72-hour/unknown-date criteria.
- **Approval-gated actions kept out of scope:** production cutover, real notifications/replay, volume deletion, secret/permission handling.
- **ChatGPT review response / next exact action:** Current GitHub content still has Q1–Q10 pending, so Claude's claimed responses cannot be reviewed yet. Claude should first push completed answers and report the commit SHA plus exact test/CI evidence. Meanwhile the single next development increment is delivery-disabled canonical decision consistency; no production changes, sends, schema migration, or source activation.
### Follow-up review request — 2026-10-16 (answers still absent; supersedes no prior evidence)

**Status after re-fetch:** Q1–Q10 remain `CLAUDE RESPONSE: Pending`. The prior orchestrator review is still valid as an assessment of the evidence that was available, but it is not a review of Claude answers. Latest commit search surfaced `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` (LinkedIn parser merge) and `572f56573fa8f66a532ee676c2aa66b25a843d0a` (test guard), but commit search alone does not prove either is the current `v2-live-radar` head or that the VM is running them. Claude must establish the exact branch HEAD using `git ls-remote`/GitHub API and correlate local checkout, PR, CI, and deployed image.

#### Required follow-up questions for Claude (answer inline in the existing Q1–Q10 slots or directly beneath each answer)

1. **Q1 / revision identity:** What exact SHA is `refs/heads/v2-live-radar` now? Provide redacted output for `git status --short --branch`, `git rev-parse HEAD`, `git ls-remote origin refs/heads/v2-live-radar`, `git log -5 --oneline --decorate`, and VM checkout/container revision. Are the local and remote trees aligned? If not, explain before modifying anything. Preserve `M v2/config.json` and untracked `.venv/`.
2. **Q2 / end-to-end integrity:** Name the exact source-normalization, canonical ID/dedupe, evaluation persistence, notification-ledger, API, and dashboard files/functions. Which edges have automated integration tests versus only manual evidence? Add a minimal test proving one canonical opportunity's identity and evaluation/reason fields remain consistent through ledger/API/dashboard-facing output, with notification delivery mocked or disabled and no live network.
3. **Q3 / schema:** Confirm the recommendation is to defer `jd_experience_source` persistence. If disagreeing, state the specific consumer/audit question that cannot be answered today, and attach a migration/old-DB/backward-compatibility/rollback test plan. Do not implement a schema change in this increment.
4. **Q4 / timestamps:** Cite the exact Greenhouse upstream response key mapped to `source_posted_at`, collector function, sample fixture shape (sanitized), timezone/parse behavior, and evidence that the field is publication time rather than first-seen/discovery time. Add or identify tests for old (>72h), recent, missing, malformed and timezone-offset timestamps. Unknown must not be fabricated as fresh.
5. **Q5 / canary:** Provide a deterministic two-poll command and sanitized report. Separate *snapshot diagnostics* from actual acceptance. State explicit thresholds for ID stability, direct URLs, timestamp coverage, old/unknown dates, duplicate prevention, source errors, rate limiting, and relevant/new yield. Demonstrate dispatch is impossible in the isolated dev configuration without sending anything; inspect the code path/config gate, do not use a real Telegram test.
6. **Q6 / ATS order:** For Ashby, Lever, and SmartRecruiters, cite official endpoint documentation and verified field/pagination/ID semantics or label unknowns. Recommend only the first adapter to investigate after current pipeline integrity is tested. Do not activate multiple sources or claim free/global availability without evidence.
7. **Q7 / LinkedIn:** Confirm whether `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` is ancestor of the actual current branch head, which parser regression tests ran, whether they are network-isolated, and how HTTP 429 halts requests and starts cooldown. Show exact CI run/result or say unverified.
8. **Q8 / release gates:** List explicit no-go gates and rollback command/steps. Confirm no production cutover, production rebuild, Telegram send/replay, volume deletion, secret output, or broad reset occurred. Show delivery-disabled state using sanitized configuration/status only.
9. **Q9 / drift:** Compare the latest code/docs against the roadmap and call out any superseded handover claims, accidental scope drift, stale jobs appearing new, and canary wording that overstates freshness validation. Mark each proposal accept/modify/reject with code/test evidence.
10. **Q10 / execution choice:** Recommend exactly one next increment, with hypothesis, paths, test-first sequence, observable pass criteria, rollback, and why it outranks the rest. Default is canonical opportunity → evaluation → notification-ledger decision → API/dashboard consistency, delivery disabled. If the current code shows a more urgent correctness/safety blocker, stop and justify the alternative before coding.

#### Development may begin after the evidence/plan checkpoint

- First fetch/review this file, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` from the actual current `v2-live-radar` head; inspect `git status` before any checkout or update.
- Populate Q1–Q10 with answers, evidence and uncertainty labels. Then revise the execution plan if the answers or source/tests show the current plan is stale; record accepted/modified/rejected roadmap items and why.
- After the plan is recorded, begin **only the single selected development increment**. Preserve local changes and the VM-local config/venv/volume. Use test-first changes, run focused tests then the full relevant suite, capture exact commands and exit statuses, and inspect CI for the exact commit. Keep notifications, Telegram, LinkedIn and production actions off unless a separately approved scope explicitly changes them.
- At the end of that work unit, update both `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, including changed files, test/CI evidence, commit/PR, deployment status, risks, rollback, and next continuation prompt. Push to `v2-live-radar`, then re-fetch both documents and verify the resulting blob SHAs. Do not overwrite concurrent edits: re-fetch and reconcile if a SHA changes before writing.
- Stop before development if the branch/VM revision is unclear, local changes may be overwritten, any secret/raw job description/verbatim model evidence would be exposed, the plan requires production changes or real notification delivery, or a migration/destructive operation is proposed without a separate reviewed plan.

**Claude completion contract:** Push the filled Q1–Q10, revised plan (if needed), and post-work evidence to `v2-live-radar`. Reply with the commit SHA, exact current branch HEAD, files changed, tests/CI with results, deployment state, and any unresolved questions. The independent orchestrator will re-fetch and review before treating any claim as accepted.
### Standard report Claude must append after each work unit
```text
Date/time:
Goal and current phase:
Branch / local HEAD / remote HEAD / VM checkout or image revision:
Changes made (files + purpose):
Commands/tests run (exact command, exit status, duration):
CI/PR/commit:
Dev deployment evidence (or explicitly not deployed):
Safety evidence (volume identity; notifications/Telegram off; source flags):
Observed outcome versus expected:
Risks / unresolved questions / rollback:
Handover + knowledge-transfer blob SHAs re-fetched:
Single next action:
```

**Continuation rule:** after Claude pushes answers, the next ChatGPT session should read the latest versions of this file, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`, review Claude's exact commit against source/CI/PRs and the plan, write an independent response under the Orchestrator review checklist above, update both handovers, and flag any drift to the user. Do not rubber-stamp Claude's self-assessment.

- Orchestrator review worksheet created/updated for the user-requested Claude Code collaboration. Claude must answer Q1–Q10 in this same handover and push it; do not erase questions. ChatGPT must independently assess the responses and write the decision into the Orchestrator review checklist. Knowledge-transfer doc points to this exact process.


## 2026-10-16 — Direct GitHub development workflow (ChatGPT-managed)

- **Workflow correction from user:** Claude Code is not working. ChatGPT will edit and commit code/docs directly to GitHub on `v2-live-radar`; the user will execute provided commands over SSH in the development VM and return redacted output. Do not ask Claude Code to run work or claim VM access.
- **Selected increment:** add an integration-style regression test for the delivery-disabled path across one Naukri observation → canonical opportunity → persisted evaluation → notification ledger → API/dashboard-facing job and opportunity payloads.
- **Code change:** added `test_canonical_evaluation_ledger_and_dashboard_api_stay_consistent_when_delivery_disabled` in `v2/test_radar.py`, commit [`bb88885698316b70dcb7b4319aad9d345041e710`](https://github.com/AvinashBhalla/job-beeper/commit/bb88885698316b70dcb7b4319aad9d345041e710). It uses a temporary SQLite DB and disables notifications; asserts canonical identity, match/reason/experience fields, pending ledger status, the disabled-notifications decision reason, API/detail consistency, and absence from the queued/failed delivery queue.
- **Verification status:** test has been committed to GitHub but has **not yet been executed** in the VM or locally by ChatGPT. CI for this commit is not verified. Do not treat the test as passing until the user returns the command output. No app logic, config, database schema, VM state, production state, or notification delivery was changed.
- **Safety:** preserve VM-local `M v2/config.json`, untracked `.venv/`, and `job-radar-dev_radar-dev-data:/data`. Do not run a broad reset/clean, delete/recreate the volume, enable notifications, or send/replay Telegram alerts.
- **Next action:** user should inspect the checkout branch/status/HEAD and remote head, then fast-forward only if safe; run the focused new test and relevant existing tests. If Git reports local divergence or the expected local modifications could be overwritten, stop and return the redacted output instead of forcing anything. After results, ChatGPT will review/fix code directly in GitHub, then give the next SSH commands.


## 2026-10-16 — Greenhouse freshness regression fix (VM-confirmed focused tests)

- **Reproduced defect:** with the first attempted fix, missing/invalid Greenhouse publication times were still queued. The downstream freshness predicate explicitly treated a missing age timestamp as fresh, so fixing timestamp extraction alone was insufficient.
- **Fixes on `v2-live-radar`:** `a977d8f796b50d5d79693b70c9542be87549e20e` restricts Greenhouse age timestamp extraction to `source_posted_at`; `dba073683bf96c89f9f2342fd731fbee8c5daf48` additionally requires a non-null, in-window timestamp for Greenhouse freshness. Other sources retain their existing missing-timestamp behavior.
- **VM evidence supplied by user:** fetched and fast-forwarded from `a977d8f` to `dba0736`; four focused Greenhouse tests passed (`Ran 4 tests in 0.288s — OK`). They cover first_published vs updated_at, missing publication time, recent valid publication time, and malformed publication time. This confirms the focused regression tests only; full suite after the fix is still pending.
- **Scope/safety:** only `v2/radar.py` changed in the two fix commits. No schema migration, config change, Docker rebuild/restart, production cutover, notification send/replay, or volume operation was performed. Preserve local `v2/config.json`, `.venv/`, and `job-radar-dev_radar-dev-data:/data`; notifications remain disabled.
- **Next action:** run the complete `v2` test suite on the updated VM checkout, then report exit status and redacted `git status --short --branch` / `git rev-parse HEAD`. Do not rebuild/restart Docker or run the Greenhouse canary as part of this test step. After the suite, inspect `v2/greenhouse_canary.py` and its acceptance criteria before proposing a separate safe canary step.

## 2026-10-16 — Greenhouse canary timestamp-quality diagnostics (verification pending)

- **Development increment:** extend the read-only two-poll report with timestamp quality counts per snapshot: within the 72-hour window, stale, unknown, invalid, and future. Existing ID stability, missing/duplicate ID, and timestamp-coverage fields remain.
- **Commits:** test-first regression 7f89f0f99f37bfd1cddff7eadc6a720db4d0d8c0, implementation 53a799e53bcfced95c98a3cde26b49624ab1926a. Files changed: v2/test_greenhouse_canary.py, v2/greenhouse_canary.py.
- **Intent/limitation:** these counts are diagnostics, not a pass/fail acceptance gate. They do not establish upstream timestamp semantics, relevant/new-job yield, or that the scheduler cannot dispatch. The canary has not been run and Greenhouse remains disabled.
- **Verification:** VM tests for this increment are pending; no test/CI pass is claimed for these commits. Combined GitHub status query returned no statuses, so CI result is unverified.
- **Safety:** no live network poll, DB write, matching run, notification, schema/config change, Docker rebuild/restart, production change, or volume operation. Existing VM-local v2/config.json, untracked .venv/, and dev data volume must be preserved.
- **Next action:** fetch/fast-forward to the latest branch only, run python -m unittest v2.test_greenhouse_canary, then the full ./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py' suite. Report exit codes and git rev-parse HEAD; do not run the canary or rebuild Docker yet.

## 2026-10-16 — Experience parsing / Gemini review-gate fix (VM verification pending)

- **User-reported blocker:** job descriptions visibly state experience requirements, but matching sometimes selects unrelated years or alerts jobs whose requirements do not fit. User also wants platform-specific parsing rather than one parser assuming every source has the same payload.
- **Root causes found in branch code:** `extract_jd_experience` considered generic “N+ years of … experience” before explicit total/professional experience, so an earlier skill-specific requirement could win. Separately, the Gemini shadow gate could treat a generic regex hit as “known” and skip review for jobs whose title/description already contained configured skills. Gemini matcher use is additionally gated by runtime flags, exact description hash, model/TTL, required overall-professional scope, verbatim evidence and confidence >= 0.85.
- **Changes pushed:** test-first regression commit `e99dbca7098af7689a636c076b179cd6347357ec` adds tests that an explicit total-professional requirement wins over earlier Python/AWS years and that generic/tool-specific regex hits remain Gemini-reviewable. Implementation commit `44c4cc0aebd194d7a9885216de5b8759a438ea79` prioritizes explicit total/overall/professional/work evidence and moves the shadow review-quality predicate to a separately testable helper. The LinkedIn structured “Experience:” label remains a trusted deterministic source.
- **Verification:** the user has not yet run tests on these commits; test/CI status is unverified. Do not claim the fix is proven until focused tests and the full V2 suite pass on the VM.
- **Important limitation:** this improves deterministic precedence and Gemini review selection; it does not yet prove that the deployed production container is on this branch or that `GEMINI_EXTRACTION_ENABLED` and `GEMINI_MATCHER_ENABLED` are true there. Runtime flags/revision must be checked using redacted, read-only diagnostics. No secrets, full job descriptions, titles, IDs or model evidence should be exposed.
- **Safety:** no VM command, Docker rebuild/restart, production rollout, config/schema change, live Gemini call, notification send/replay or volume operation was performed by this commit. Preserve VM-local `M v2/config.json`, untracked `.venv/`, and `job-radar-dev_radar-dev-data:/data`; notifications/Telegram and production remain unchanged.
- **Architecture decision:** proceed with source-specific, independently testable parsing adapters inside the existing app first; keep a shared canonical job contract and shared matching/ledger/API pipeline. Do not split into deployed microservices until measured isolation/scaling needs justify the operational cost.
- **Next action:** user should fast-forward only to the latest branch, run focused parser/Gemini tests and then the full V2 suite. If green, inspect sanitized runtime revision/flag state to distinguish a parser bug from production drift, then add the next source-specific parsing regression set. No production cutover or notification test.


## 2026-10-16 — Dev Gemini key environment-file resolution (verification pending)

- VM evidence: development container rebuilt from the current v2-live-radar checkout and now contains the expected v2/radar.py SHA-256 c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2. Health recovered after a brief startup connection reset; /health returned OK, and the existing job-radar-dev_radar-dev-data:/data mount remains intact.
- Current root .env has populated GEMINI_API_KEY, GEMINI_EXTRACTION_ENABLED, and GEMINI_MATCHER_ENABLED. The running container reports the Gemini key empty/unset. The Compose file maps GEMINI_API_KEY from variable substitution, but Compose was invoked without an explicit --env-file .env, and the resulting effective config reported the key empty. Likely env-file resolution/interpolation issue; verify via an explicit root env-file path without printing values.
- v2/docker-compose.dev.yml deliberately sets Telegram token and chat ID to empty strings. Keep those values blank; never add the root .env as a container env_file because it could inject unrelated credentials. Use root .env only for Compose interpolation via --env-file /home/ubuntu/job-beeper-dev/.env.
- No secret value was printed or committed. No Telegram notification was sent. Production/other v2 project were not touched; the named dev DB volume was not deleted or recreated.
- Next action: run a filtered docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml config --format json check that prints only key-presence, Gemini flags/call limits, and that Telegram token/chat are blank. If safe and GEMINI_API_KEY is populated in the effective config, recreate only dev radar using the same --env-file argument, then verify health, key-presence only, and volume mount. Do not print raw config output, raw environment values, job payloads, or logs containing secrets.
- Evidence/confidence: high confidence that the current running container lacks the Gemini API key; medium confidence that explicit --env-file will resolve it, pending effective-config check. The service is currently healthy. Do not claim Gemini requests work until a safe runtime status check confirms key configured and the extraction path produces verified results.
- Cross-reference: docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, docs/JOB_RADAR_HANDOVER.md, and architecture guardrails in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-16 — Dev Gemini key injection applied; runtime verification pending

- User ran the filtered Compose interpolation check with the explicit root env file. Output: GEMINI_API_KEY=present; GEMINI_EXTRACTION_ENABLED=true; GEMINI_MATCHER_ENABLED=true; GEMINI_MAX_CALLS_PER_RUN=3; GEMINI_MAX_CALLS_PER_DAY=20; JOB_RADAR_TELEGRAM_BOT_TOKEN=blank; JOB_RADAR_TELEGRAM_CHAT_ID=blank. No secret values were shown.
- User then ran `docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --no-deps radar`; Compose reported `Container job-radar-dev Started`. This is evidence of the dev service start command completing, not yet proof that the running container received the key or is healthy.
- Next: perform read-only checks for container state/health, Gemini key presence only (never value), Telegram variables blank, and existing `/data` volume mount. Then inspect a safe status endpoint for extraction/cache counts without printing job titles, IDs, evidence, raw payloads or secrets. Do not trigger job processing, send/replay notifications, or touch the separate production-ish `v2` Compose project. Preserve VM-local `v2/config.json`, `.venv/`, and `job-radar-dev_radar-dev-data:/data`.
- No code changes, test run, production change, notification, DB/schema change or volume operation in this turn. CI status remains unverified. The only runtime action was the user-reported recreation/start of the isolated dev `radar` service with the explicit root env file.
- Overarching goal remains reliable multi-source discovery, normalization/deduplication, explainable matching, consistent dashboard/ledger and safe low-noise delivery. Cross-reference this handover, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md and architecture/rollout guardrails in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-16 — Dev Gemini key and service runtime verified; status endpoint next

- User-reported read-only VM output: container job-radar-dev is running, restart_count=0, health check is not configured in Docker metadata (health is checked via HTTP); runtime GEMINI_API_KEY=present, extraction=true, matcher=true, Telegram token/chat blank. /data is mounted from existing named volume job-radar-dev_radar-dev-data; /health returned status=ok, DB /data/jobs.db, Naukri error=null, jobs_seen=327, new_jobs=1. The user pasted a mangled retry loop but the health request succeeded; do not infer a Docker healthcheck exists.
- This confirms configuration injection and basic service health, but not yet a successful Gemini API call, successful fresh extraction/cache use, or correct preference matching. No processing endpoint was called, and no notification was sent.
- Next: call only the read-only GET /api/llm-shadow-status and print a strict whitelist of aggregate fields (enabled flags, api_key_configured, model, calls today, cache success/error counts); omit recent sample records and all job titles, IDs, evidence, raw payloads and secrets. If the status reports the key configured and cache/flags look plausible, decide whether an existing safe diagnostic can verify current cache/evaluation without network calls or notifications. Do not trigger polling or alert dispatch. Keep Telegram blank, preserve v2/config.json, .venv/, the named dev volume, and do not touch the separate v2 Compose instance.
- No code changes, tests, schema/config changes, production actions, notifications or volume operations this turn. CI remains unverified. Overarching goal remains reliable multi-source discovery, normalization/dedupe, explainable matching and safe low-noise delivery. Cross-reference docs/JOB_RADAR_HANDOVER.md, docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md, and architecture/rollout rules in docs/JOBBEEPER_REFERENCE.md.


## 2026-10-16 — Gemini shadow-status counts verified; diagnostic next

- User-reported filtered GET /api/llm-shadow-status output: enabled=True, api_key_configured=True, model=gemini-3.5-flash-lite, calls_today=20, cache_successes=74, cache_errors=6. This confirms the status endpoint reports the key configured and the daily call counter at the configured 20-call cap; it does not by itself prove the latest extraction or experience matching is correct. Avoid any action that could cause additional Gemini API calls until the counter/reset semantics and current cache state are reviewed.
- Read-only diagnostic source reviewed at v2/gemini_experience_diagnostic.py (current branch file SHA 5347ab501372caaf344027fb6bba15c0f013d56; use actual Git blob SHA from repository metadata when needed). Its documented flow opens the source SQLite DB read-only, selects one fresh current job with a trusted exact-input-hash/model-matched successful cache entry, copies that candidate into a disposable temporary DB, and exercises the bridge/evaluation persistence only in that sandbox. The script reports aggregate/experience-bound diagnostics, makes zero Gemini API calls and triggers no notifications. Tests in v2/test_gemini_experience_diagnostic.py cover exact fresh trusted result, hash mismatch, expired cache, and skill-specific scope.
- Next action: run this existing diagnostic only against the isolated dev container/database, after verifying its container working directory/module path and the runtime config path. Share only its key=value diagnostic output; do not share raw database content, job titles/IDs, descriptions/evidence text, environment values or secrets. If it says not_verified, report reason_code and stop—do not trigger polling or extraction to manufacture a candidate.
- Runtime safeguards unchanged: keep Telegram credentials blank, notifications disabled, Gemini matcher shadow-only, production-ish v2 Compose untouched, and preserve /data volume job-radar-dev_radar-dev-data plus VM-local v2/config.json and .venv/. No code, test, config, schema, production, notification or volume changes were made this turn. CI remains unverified.


## 2026-10-16 — Read-only Gemini experience diagnostic candidate verified

- User-reported output from `sudo docker exec job-radar-dev python -m v2.gemini_experience_diagnostic`: `diagnostic_status=candidate_verified`; model `gemini-3.5-flash-lite`; source DB read-only and unmodified; 0 Gemini API calls; no notifications. Exact current-input hash matched; cache status `ok`; model matched; cache age 50,781 seconds within 30-day TTL; selected job last seen 49,543 seconds ago (within 24 hours). Trusted experience was `required` / `total_professional`, 5.0–10.0 years, confidence 0.95, with evidence present and range bounds present.
- Existing live evaluation row was present, bounds matched cache (5.0–10.0), and an experience/year reason was present. In disposable sandbox, bridge source was verified, bounds matched, evaluation row was written with matching bounds and one reason. `source_marker_in_job_evaluations_schema=False` is consistent with the design: the diagnostic uses the existing bridge and does not add a source marker to the live schema.
- Investigated `sandbox_alertability_experience_reason_present=False`: current `alertability_details()` intentionally returns `not a profile match` when there is no match and returns `Telegram notifications disabled` when notifications are disabled; otherwise it returns `passes match threshold and notification policy`. Alertability reasons are therefore policy outcomes, not a copy of the regular match reasons. The false experience-reason flag is not by itself evidence of a defect; in this diagnostic the regular evaluation experience reason is present. Do not change alertability or enable notifications based on this flag.
- Combined with the previously reported status endpoint (`calls_today=20` at configured daily limit, 74 cache successes, 6 cache errors), do not trigger extraction/polling just to gather more Gemini results. Keep extraction calls paused until the daily counter reset/limits are understood and the current result is reviewed. No production cutover, notifications, schema/database changes, volume operations, code edits, or tests were performed this turn. CI remains unverified.
- Next safe step: inspect aggregate shadow-status and cache-error categories only if a dedicated endpoint/query can avoid exposing job titles, IDs, descriptions/evidence, raw payloads or secrets; otherwise stop here and retain this as a successful one-candidate validation. Keep Gemini matcher shadow-only, Telegram blank, the dev named volume intact, VM-local `v2/config.json` and `.venv/` untouched, and do not touch the separate production-ish Compose project.


## 2026-10-16 — Multi-provider LLM planning
- User asked whether Job Radar V2 can use Groq, Gemini, OpenRouter, and NVIDIA API access to reduce dependence on Gemini's limits, with API keys entered directly on the VM.
- Feasible in principle, but the current code is Gemini-specific: `v2/gemini_extractor.py` owns the Gemini endpoint, request schema, model-keyed cache and bounded-call settings; `v2/docker-compose.dev.yml` currently injects only Gemini variables. No multi-provider router exists yet, and no code/config/runtime changes were made for this request.
- Recommended architecture: a small provider adapter/router with explicit per-task provider/model allowlists, normalized structured output, shared validation, provider-specific rate/cost budgets, timeout/retry rules, cache keys including provider/model/prompt version, and safe fallback only for retryable provider errors. Do not broadcast every job to every provider; route one call at a time to avoid multiplied costs and duplicated data exposure.
- Keep all credentials VM-local via environment or a permission-restricted ignored secrets file; never commit keys, print them, include them in diagnostics, or paste them into chat. Verify each provider's model access, endpoint, rate limits, pricing and data-retention terms before enabling it. OpenRouter is an additional gateway to models, not an independent pool of guaranteed free capacity; provider quotas remain separate and can change.
- Preserve current safety posture while designing: Gemini shadow extraction/matching must remain non-authoritative until tested, Telegram notifications stay disabled, no production cutover, no database/schema migration, and no provider calls during this planning step. Add unit tests with mocked HTTP responses and a dry-run/config validation path before any live API test.


## 2026-10-16 — Multi-provider LLM router implementation
- Added `v2/llm_router.py` for Groq, Gemini, OpenRouter, and NVIDIA NIM JSON extraction, with ordered single-provider attempts, sanitized fallback errors, shared semantic validation, and cache identity derived from configured provider/model names (never keys).
- Integrated the optional router into `v2/gemini_extractor.py`; existing Gemini-only behavior remains when `LLM_ROUTER_ENABLED=false`. Development Compose now passes the router flags, provider keys/model IDs, and bounded job budgets. Router is disabled by default; `LLM_ROUTER_MATCHER_ENABLED=false` gates routed outputs from hard matching until explicitly validated.
- Added mocked tests in `v2/test_llm_router.py` and an integration-path test in `v2/test_gemini_extractor.py`. Tests have been added but were not executed in this environment; no live provider API calls were made, and CI/test results remain unverified.
- Added `docs/LLM_PROVIDER_ROUTER.md` with VM-local environment setup, provider endpoints, cache/budget behavior, security guidance, and staged rollout steps. `docs/JOBBEEPER_REFERENCE.md` also references the runbook.
- No API keys were added to GitHub. No VM environment, container, SQLite data, named volume, production service, or Telegram setting was changed. No database schema migration was introduced. Next: fast-forward the dev checkout, run focused and full unit tests, then enter provider keys and account-valid model IDs only in the VM-local `.env`; review sanitized configuration and tests before rebuilding only `job-radar-dev`.


## 2026-10-16 — Multi-provider router implementation checkpoint and continuation
- Implemented an initial opt-in provider router in `v2/llm_router.py` and integrated it into the existing shadow extractor in `v2/gemini_extractor.py`. Supported adapters: Groq, Gemini native API, OpenRouter, and NVIDIA NIM using their configured endpoints. OpenAI-compatible providers request JSON-object output; all results pass the existing extraction validator. Provider fallback is sequential, not parallel, and includes request/rate-limit, timeout, malformed JSON, and semantic-validation failures.
- Added development Compose variables for provider keys/model IDs, order, router toggle, separate job-per-run/day caps, and a matcher safety gate. Defaults are safe/off: `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`; Telegram credentials remain blank as before. No secrets are in source control.
- Added mocked router tests in `v2/test_llm_router.py` for provider configuration, cache identity secret exclusion, legacy identity behavior, request construction, rate-limit fallback, semantic-validation fallback, sanitized failures, and timeout handling. **Tests have not yet been executed**; do not claim test success until the dev VM runs focused tests and the full suite.
- Added `docs/LLM_PROVIDER_ROUTER.md` with environment setup, provider endpoints, budgets/cache behavior, key hygiene, safety defaults, and staged rollout. Updated `docs/JOBBEEPER_REFERENCE.md` with the new router/runbook pointers.
- Cache identity when router mode is enabled includes the ordered provider/model set but not API keys; daily counts are scoped to that identity. Existing SQLite cache is reused; no schema migration. The job cap bounds jobs, not total provider requests: fallback attempts can mean more than one request per job, so each provider's rate limits/pricing and a global budget must be considered.
- Important implementation limitation: the router is an initial integration, not production-validated. Provider-specific model IDs/account access, structured JSON compatibility, timeout/retry behavior, and real output quality remain unverified. Mocked tests cannot establish live provider availability, pricing, quota, or quality. Do not enter keys or enable router on the VM until the checkout is fast-forwarded and tests/review pass. Then configure secrets and account-valid model IDs in the VM-local development `.env` only; verify allowlisted fields without printing secrets.
- Current repository branch: `v2-live-radar`, repo `AvinashBhalla/job-beeper`. Recent implementation commits include router `dd464720f1697602d03fca1cab417a66aa63554b`, extractor integration `6ccd0f1578899da97674c6b79f6a4184240ced6a`, dev Compose settings `1d960515122fcdba5ea4f8ce80c771083d7b6441`, mocked tests `44b6621438ed13ebb9591d6bb74295569a85da5d`, validation-fallback support `ee20bda74ebceae15c083adb004e1e00570cb694`, active-cache budget scoping `87befd65b442e0443286a002f75122251c53fe76`, semantic-fallback test `10c20427370fa98d9eb14083dba9291644e98799`, matcher safety gate `c9d2cfe01dbed968c9ec8fe984cfdaa5a15bc114`, and Compose matcher gate `de700fc64cf67030174c16f99f16a6f7418e1aee`. The runbook commit is `299a6f2513f54df173c40cc74ec2c80a50408619`; subsequent documentation commits may follow.
- Next steps: (1) review current router/extractor code for correctness and run focused tests, (2) fix all failures and run the full `v2` unittest suite, (3) inspect final diffs and document test results, (4) only then provide safe VM commands to fetch and fast-forward `v2-live-radar` without resetting/cleaning or overwriting local `v2/config.json`, `.venv/`, or the `job-radar-dev_radar-dev-data` volume, (5) configure keys locally after tests pass, (6) rebuild/recreate only `job-radar-dev` if explicitly needed, and (7) keep router matcher disabled and Telegram notifications disabled during shadow validation. Do not trigger live provider calls or job-processing endpoints during tests.


## 2026-10-16 — Multi-provider LLM router implementation checkpoint

### User request
The user asked to implement and document a multi-provider LLM fallback for Groq, Gemini, OpenRouter, and NVIDIA, with API keys to be entered directly on the VM after the code is pulled. The user now asks for a continuation prompt and for this handover/progress record to be updated.

### Changes pushed to `v2-live-radar`
- Added `v2/llm_router.py` (initial commit `dd464720f1697602d03fca1cab417a66aa63554b`, follow-up hardening `ee20bda74ebceae15c083adb004e1e00570cb694`). Supports sequential, configurable provider fallback for Groq, Gemini, OpenRouter, and NVIDIA NIM; sanitized error categories; bounded HTTP timeouts; JSON parsing; and optional shared semantic validation before accepting a provider result.
- Updated `v2/gemini_extractor.py` to optionally use the router when `LLM_ROUTER_ENABLED=true`; preserves legacy Gemini-only behavior when disabled. Cache identity reflects ordered provider/model IDs without keys, and daily cache-budget counting is scoped to that identity. Matcher bridge refuses router-produced cache by default unless `LLM_ROUTER_MATCHER_ENABLED=true` in addition to existing matcher gating.
- Updated `v2/docker-compose.dev.yml` with opt-in router variables, model IDs and key environment variables for Groq/OpenRouter/NVIDIA, ordered providers, per-run/per-day job budgets, and a matcher-disabled default. Telegram token/chat ID remain explicitly blank.
- Added `v2/test_llm_router.py` with mocked configuration, parsing, fallback, semantic-validation, timeout, and secret-redaction tests. These tests have NOT been executed in a real VM or CI as part of this work; do not claim they pass.
- Added `docs/LLM_PROVIDER_ROUTER.md` with VM-local configuration, endpoints, safety defaults, testing/pull instructions, budget caveats, and staged rollout guidance.

### Current commit trail
- `dd464720f1697602d03fca1cab417a66aa63554b` — add router
- `6ccd0f1578899da97674c6b79f6a4184240ced6a` — integrate router into shadow extraction
- `1d960515122fcdba5ea4f8ce80c771083d7b6441` — Compose environment settings
- `44b6621438ed13ebb9591d6bb74295569a85da5d` — initial router tests
- `ee20bda74ebceae15c083adb004e1e00570cb694` — fallback on semantic validation errors
- `87befd65b442e0443286a002f75122251c53fe76` — scope daily cache budget/status to active model identity
- `10c20427370fa98d9eb14083dba9291644e98799` — semantic-invalid-output fallback test
- `c9d2cfe01dbed968c9ec8fe984cfdaa5a15bc114` — keep router results out of matcher by default
- `de700fc64cf67030174c16f99f16a6f7418e1aee` — Compose matcher gate
- `299a6f2513f54df173c40cc74ec2c80a50408619` — router runbook

### Important status and constraints
- This is repository code, not a verified working deployment. No VM pull, test execution, Docker rebuild, live provider API call, database write, schema migration, or notification was performed in this implementation turn.
- Current defaults are safe/off: `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`; the router must be explicitly enabled in the development VM environment after tests pass. Do not ask the user to share any API key in chat.
- The current VM may have local modifications to `v2/config.json`, untracked `.venv/`, and a named volume `job-radar-dev_radar-dev-data`; preserve them. Do not use `git reset`, `git clean`, destructive checkout, or volume removal. Only update the isolated development service `job-radar-dev`, never the separate `v2-radar-1` project.
- Keep Telegram credentials blank and notifications disabled. Do not run endpoints that process jobs just to trigger calls. No further Gemini calls should be made during initial validation; previous status showed the Gemini daily counter at 20.
- Test quality gates before enabling: run focused tests `./.venv/bin/python -m unittest v2.test_llm_router` and relevant extractor tests, then the full suite `./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py'`. First check current tree/status and fetch updates safely. If any tests fail, fix and document before rebuilding.
- After tests pass, user can add keys/model IDs locally in `/home/ubuntu/job-beeper-dev/.env`; verify only allowlisted booleans/provider names/model IDs and key-present booleans, never echo values. Recreate only development container using `sudo docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --build --no-deps radar` only after confirming tests and intended config; do not run this yet.
- The current router's daily/run budget is a job budget, not a per-provider request/token quota; fallbacks can make more than one request per job. Provider account billing/rate limits still apply. Model IDs and endpoint compatibility must be checked for the user's actual accounts before live smoke tests.
- Follow-up review should inspect code for integration issues, run mocked tests, then verify status. Specifically ensure provider-specific errors never leak raw response content, strict extractor validation is used as the router validator, the cache model identity behaves correctly, and the existing extraction job cap cannot exceed the intended budget. Do not enable routed matcher until a separate quality review approves it.

### Next actions
1. Continue from the latest `v2-live-radar` branch and re-read the latest versions of the handover, knowledge-transfer, reference, and router runbook docs before acting.
2. Review the router/extractor integration and run the focused mocked tests; fix any issues and record exact outcomes.
3. Give the user safe, non-destructive VM pull commands only after confirming test results and checking how to preserve local changes.
4. Ask the user to enter keys directly in the VM only after code/tests are ready; never request keys in chat.
5. Keep all runtime tests development-only, shadow-only, no schema migration, no production cutover, and no Telegram sends.


## 2026-10-16 — Multi-provider router review and CI evidence

### Work performed in this review
- Re-fetched the latest versions of the router, extractor, tests, development Compose file, provider runbook, handover, knowledge transfer and product reference from `v2-live-radar`. Current branch head reviewed: `b635b8969247c483bdfae7c2c9d0cb9a38895a61` (`docs: record multi-provider router implementation checkpoint`).
- Reviewed the router/extractor signatures and the shared strict validator. `_call_llm_router(job)` matches the current call site; the router validator invokes `_validate_result(payload, description)`, so malformed experience ranges (including boolean/non-numeric/out-of-range or inverted bounds), invalid confidence, invalid type/scope, and unverifiable evidence are rejected and cause provider fallback. With `LLM_ROUTER_ENABLED=false`, the extractor continues through the legacy `_call_gemini` path.
- Reviewed request payloads: Gemini uses native `generateContent`; Groq, OpenRouter and NVIDIA NIM use the OpenAI-compatible chat-completions shape with JSON-object response format. Provider model IDs, live account availability and request-format compatibility are not proven by mocked tests.
- Verified the CI run attached to the exact head: V2 CI run [38934696862](https://github.com/AvinashBhalla/job-beeper/actions/runs/38934696862), job `syntax`, completed `success` on 2026-10-16. Its steps installed `v2/requirements.txt`, compiled the existing CI-listed modules, and ran `python -m unittest discover -s v2 -p 'test_*.py' -v` successfully. This is CI evidence for that revision; it is not a test run in the development VM and the CI py_compile command does not explicitly list `v2/llm_router.py`.
- No local shell/VM access was available in this review, so the requested focused command `./.venv/bin/python -m unittest v2.test_llm_router` was not executed here. No new code was committed during this review, and no test result is claimed from a local execution.

### Findings and remaining review points
- Positive: model/cache identity consists of ordered configured provider/model names and never API keys. On router-disabled mode it returns the legacy Gemini model identity. The extractor applies shared strict validation after generation. Raw HTTP response bodies and exception text are not deliberately logged; failure logs use provider plus sanitized category. Router output remains excluded from hard matching unless both the existing Gemini matcher gate and `LLM_ROUTER_MATCHER_ENABLED` permit it.
- Budget caveat: `LLM_MAX_JOBS_PER_RUN` / `LLM_MAX_JOBS_PER_DAY` count extraction jobs/cache rows for the active model identity, not provider requests or tokens. A job can generate several HTTP requests due to fallback. They do not implement a separate aggregate per-provider request or spend budget. Keep the caps low; provider-specific account limits and billing still apply.
- Validation coverage is not exhaustive: focused mocked tests cover configuration, the Groq request shape, HTTP 429 fallback, semantic-invalid fallback, error-body/key redaction, and a timeout surface. There is no direct mocked router test yet for native Gemini, OpenRouter or NVIDIA payload/response variants; malformed/empty content, connection errors, 5xx, all-providers-fail, and multiple fallback attempts against the configured job budget could use dedicated assertions. Existing extractor tests cover range, confidence, evidence and safe matcher gates, and CI's full discovery passed.
- Router fallback catches provider exceptions and continues. Request exceptions are sanitized in fallback logs. If every provider fails, the raised summary contains provider names and sanitized categories; the extractor records a generic `request_failed` for the aggregated failure, rather than persisting raw response text.
- No runtime/API call, VM environment/config edit, container rebuild/restart, source or cache DB mutation, schema migration, volume change, Telegram notification or production action occurred.

### Next safe step
1. On the VM, inspect the development checkout before fetching: `cd /home/ubuntu/job-beeper-dev && git status --short && git branch --show-current && git rev-parse HEAD && git fetch origin v2-live-radar`. Do not proceed to merge until local status and ahead/behind state have been reviewed. Preserve `M v2/config.json`, untracked `.venv/`, `.env`, and the named volume; no reset/clean/overwrite.
2. After a safe fast-forward, run focused router and extractor tests and full discovery from the checkout. CI succeeded on `b635b896`, but this does not replace the VM run.
3. Keep all keys inside the VM-local `.env`, router and matcher gates off until tests finish, Telegram credentials blank, notifications disabled, and do not trigger job processing or any Gemini calls during initial validation.
4. Only after local tests pass, inspect allowlisted environment metadata without printing values. A live provider smoke test is a separate explicitly chosen cost/rate-limit step.

### Current verified references
- Reviewed branch head: `b635b8969247c483bdfae7c2c9d0cb9a38895a61`.
- CI: [V2 CI run 38934696862](https://github.com/AvinashBhalla/job-beeper/actions/runs/38934696862) — success on that head.
- No change to the implementation was made in this review, so there is no new commit ID for this review entry.


## 2026-10-28 — Continuation handoff after multi-provider router implementation
- User asked for a reusable prompt for the next ChatGPT conversation and requested that progress/learning be captured in the handover documents. Re-read the latest versions of all three project reference docs and the current router, extractor, dev Compose file, tests, and router runbook before updating this note.
- Current documented branch head is `b635b8969247c483bdfae7c2c9d0cb9a38895a61`; CI run [38934696862](https://github.com/AvinashBhalla/job-beeper/actions/runs/38934696862) is documented as successful for full V2 unittest discovery on that exact head. This is CI evidence only; focused tests and full suite have not yet been run on the user's VM. Do not claim live provider compatibility or VM validation.
- Current implementation includes `v2/llm_router.py`, integration in `v2/gemini_extractor.py`, optional provider environment variables in `v2/docker-compose.dev.yml`, mocked tests in `v2/test_llm_router.py`, and `docs/LLM_PROVIDER_ROUTER.md`. Providers are Groq, Gemini, OpenRouter, NVIDIA, tried in configured order with shared strict extraction validation and sanitized failure logging. Router defaults off; routed matcher gate defaults off; Telegram remains disabled. No DB schema migration was added.
- Key learning: `LLM_MAX_JOBS_PER_RUN` / `LLM_MAX_JOBS_PER_DAY` limit jobs/cache entries, not aggregate HTTP requests, tokens, or spend. A fallback can call multiple providers for one job; provider billing/rate limits remain in force. Cache identity is the ordered configured provider/model list and excludes keys. API keys and model IDs must be entered/verified on the VM only.
- Remaining coverage gaps documented by review: direct mocked native Gemini, OpenRouter and NVIDIA response variants; malformed/empty response; connection error; 5xx; all-provider failure; and fallback attempts versus job budget. The next model should inspect latest files and run/review CI or local mocked tests before giving VM instructions, then fix issues and update these docs with exact test results.
- Safe next VM step, after reviewing current status: read-only `git status --short`, branch, HEAD and fetch for `origin/v2-live-radar` from `/home/ubuntu/job-beeper-dev`. Preserve VM-local modified `v2/config.json`, untracked `.venv/`, ignored `.env`, and named volume `job-radar-dev_radar-dev-data`. Do not reset/clean/stash blindly or touch the separate production-ish Compose project. Only use `git pull --ff-only` if the tree/branch/ahead-behind state proves it is safe.
- Do not ask the user to paste keys in chat. Do not enable the router, run job-processing endpoints, trigger Gemini/provider requests, rebuild/restart containers, change DB/volume state, enable matcher use, or send notifications until test results and an explicit staged rollout are agreed. If safe to proceed after tests, give exact VM-local secret-entry steps and verify only allowlisted booleans/provider names/model IDs, never secret values.

 
## Current handoff — 2026-10-28 — Multi-provider router hardening and CI verification

- **Goal:** continue the existing Job Radar V2 multi-provider shadow-extraction router safely, preserving fresh multi-source discovery, strict experience validation, explainable matching and low-noise delivery.
- **Code/test commit:** db331cac992a0d433bad119ae3b1fe483831f71e updated v2/llm_router.py, v2/test_llm_router.py and v2/test_gemini_extractor.py. Commit edc5b92404f94c2de84381407c7ed103bdda5f60 added a dedicated focused-test step to .github/workflows/v2-ci.yml.
- **Finding and fix:** generate_with_fallback previously accepted any ValueError message starting with invalid_ as a safe code. A generic caller could append job text or evidence to such a message, causing it to appear in warnings and the aggregated failure. The router now logs/aggregates only an explicit allowlist of stable validation codes; any other validator message becomes invalid_result. No credentials, job descriptions, model response bodies or evidence are logged by this path.
- **Mocked coverage added:** direct native Gemini, OpenRouter and NVIDIA request/response tests; malformed, empty and missing response content; HTTP 5xx and connection-error fallback; all-provider exhaustion with error/body redaction assertions; unsafe validator-exception redaction; and extractor integration showing one job may trigger three provider HTTP attempts while consuming one per-run job slot.
- **CI evidence:** [run #40651350087](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651350087), code/test commit db331cac992a0d433bad119ae3b1fe483831f71e, passed full V2 discovery: 134 tests in 12.864 seconds. The focused-first pipeline at [run #40651562286](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651562286), commit edc5b92404f94c2de84381407c7ed103bdda5f60, passed the focused router/extractor step (32 tests in 0.061 seconds) and the full V2 suite (134 tests in 17.009 seconds); both reported OK. These are GitHub Actions results, not VM-local test results.
- **Configuration/doc correction:** docs/LLM_PROVIDER_ROUTER.md now keeps LLM_ROUTER_ENABLED=false in its example environment block so an example cannot accidentally enable the router before the rollout is approved. The existing GEMINI_EXTRACTION_ENABLED gate must also be enabled for extraction to run; no feature flag was changed in the VM.
- **What did not change:** provider requests remained mocked; no live provider API calls or API keys were used. The router and routed matcher remain disabled by default; Telegram stays blank/disabled; no VM pull, Docker operation, DB write, schema migration, volume change, production-like service change or notification occurred.
- **Remaining risks:** CI does not prove account-specific model IDs, live API compatibility, quotas, cost, data-handling terms or output quality. LLM_MAX_JOBS_PER_RUN and LLM_MAX_JOBS_PER_DAY bound processed cache/job entries, not total HTTP requests, tokens or spend; fallback attempts can multiply requests. No live smoke test is authorized by these CI passes.
- **Exact next safe action:** on /home/ubuntu/job-beeper-dev, run only the read-only checkout review and fetch below; return the output for assessment before any pull. Preserve the modified v2/config.json, untracked .venv/ and ignored .env; never print .env or use reset/clean/blind-stash operations.
    cd /home/ubuntu/job-beeper-dev
    git status --short
    git branch --show-current
    git rev-parse HEAD
    git fetch origin v2-live-radar
    git status -sb
    git rev-list --left-right --count HEAD...origin/v2-live-radar
    git diff --name-only HEAD..origin/v2-live-radar
  Decide whether a fast-forward is safe only after reviewing the branch, ahead/behind counts, local changes and changed path list. Do not pull yet based solely on this note.
- **Tests to run on the VM after a verified safe fast-forward:** ./.venv/bin/python -m unittest v2.test_llm_router -v, then ./.venv/bin/python -m unittest v2.test_gemini_extractor -v, then ./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py' -v. No live provider request is needed.
- **Cross-links:** architecture/rollout constraints remain in docs/JOBBEEPER_REFERENCE.md; provider-specific setup and test commands are in docs/LLM_PROVIDER_ROUTER.md; compact transfer is docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md.


## 2026-11-05 — Product reverse-engineering kickoff (current)

- **User goal:** investigate public/accessible behavior of JobBeeper and Uplers HAPPPY, then design a personal multi-source job-discovery and referral-intelligence system. The current scope is product research and evidence collection; no implementation or deployment change is authorized by this note.
- **Repository evidence:** inspected `v2-live-radar` at `ef73b3c8bee77b14c4b0ebd7ac319ab7cf94fc7a`. GitHub Actions V2 CI run [#40651863587](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651863587) succeeded on that exact head on 2026-10-28. This is CI evidence, not Oracle VM deployment evidence. `main` is at `58fdff19aa6c4e5c53c402fc0af8d2642ceb467d` and is behind the active V2 branch; continue V2 work from `v2-live-radar`.
- **Initial LinkedIn latency diagnosis (code-based estimate):** current tracked config has 4 LinkedIn queries × 4 locations = 16 first-page query/location targets. `linkedin_collect` scans up to 2 targets per scan and scheduler target is 180 seconds, so a complete uninterrupted fast-lane rotation is nominally 8 × 180 = 1,440 seconds (24 minutes). This is a theoretical scheduling calculation, not measured live latency. The HTTP wrapper paces calls at least 4 seconds apart, uses a 25-second timeout, and applies a global escalating cooldown after HTTP 429; fallback cooldown starts at 300 seconds and caps at 1,800 seconds while honoring Retry-After. Do not reduce intervals or increase request pressure before measuring source-specific yield and rate limits.
- **Source inventory:** collector registry contains LinkedIn, Naukri, Instahyre, Greenhouse and Ashby. Tracked `v2/config.json` enables LinkedIn/Naukri and disables the other three; isolated `v2/config.dev.json` enables Naukri only and notifications off. Treat these as repository configuration only: runtime `/data/config.json` may override production settings and must be checked on the VM before any state claim.
- **Observability gap:** current `/api/latency-summary`, `/api/source-status` and `/api/dedupe-candidates` enumerate LinkedIn, Naukri, Instahyre and Greenhouse but omit Ashby despite Ashby being in `COLLECTORS`. Verify the intended API contract and add regression tests before changing it.
- **Runtime status:** Oracle container/commit, effective runtime config, source last-success/errors, actual LinkedIn cooldown history and Telegram delivery timings have not been verified in this turn. The checked-in `source_state.json` is an old static snapshot and is not live health evidence.
- **REA research:** official project is [morluto/rea](https://github.com/morluto/rea), MIT-licensed. Current docs require Node.js 22.23.4+, 24.22.1+ or 26.12.1+. It supports passive website observation by attaching to a user-owned Chrome-family browser via CDP on loopback and offline inspection of HAR 1.2 captures. REA is not a general browser automation surface. Use a dedicated browser profile; do not expose the debugging port beyond loopback. Redact HAR cookies, authorization headers, tokens, inbox content and other personal information before sharing.
- **Next actions:** (1) verify local Node/npm versions; (2) install latest REA using `npx rea-agents@latest setup`, review its exact setup plan, select the intended coding agent and restart it; (3) launch a separate Chrome profile with CDP bound to `127.0.0.1:9222`; (4) inspect JobBeeper public/accessible pages, capture passive page/script/network metadata, and export a sanitized HAR; (5) separately capture HAPPPY workflow/consent screens; (6) request read-only Oracle runtime diagnostics before any code/deploy work.
- **Safety and scope:** inspect only publicly accessible or account-authorized product behavior. Do not attempt to access private SaaS backend source, bypass authentication/access controls, evade LinkedIn rate limits, automate prohibited LinkedIn activity, or disclose cookies/session tokens. Referral workflows should use authorized data providers and human-approved account activity.
- **Code/config/runtime changes:** none. No collectors were triggered; no VM command, container restart, DB write, schema migration, source setting, Telegram notification, provider API call or deployment was performed.


## 2026-11-05 — REA setup host clarification

- User ran `node -v` and `npm -v` at the Oracle prompt `ubuntu@job-radar:~$`; reported Node.js `v12.22.9` and npm `8.5.1`.
- This is the Oracle application host, not the Windows workstation selected for REA/browser investigation. Do not upgrade Node on Oracle just to install REA; the existing Job Radar V2 backend is Python/FastAPI and does not need this change for the planned investigation.
- Next action: on the Windows development workstation, open PowerShell (not the SSH terminal) and run `node -v; npm -v`. REA requires Node.js 22.23.4+, 24.22.1+ or 26.12.1+. Then follow the reviewed local setup instructions. The previously remembered Windows Node version (26.7.0) is historical and must be rechecked.
- No VM package installation, Node upgrade, collector run, service restart or application change was performed.


## 2026-11-05 — Windows REA Node prerequisite

- User's Windows PowerShell reports Node.js `v27.0.0-alpha.0.0.0`, npm `12.1.0`, executable `C:\\Program Files\\nodejs\\node.exe`. This is a prerelease and is unsupported by REA.
- Current REA docs require Node 22.23.4+, 24.22.1+ or 26.12.1+ and explicitly exclude prereleases. REA's Windows getting-started guide recommends installing Node 24 LTS with `winget install --exact --id OpenJS.NodeJS.LTS`; see https://morluto.github.io/rea/get-started/.
- Recommended next step: in a NEW Windows PowerShell session, run `winget install --exact --id OpenJS.NodeJS.LTS`. Reopen PowerShell and verify `node -v`, `npm -v`, and `where.exe node`. Do not uninstall the currently installed Node 27 alpha or manually delete `C:\\Program Files\\nodejs` if winget reports a conflict; capture the exact installer error and assess a version-manager route instead.
- Do not run the REA installation from the Oracle SSH session; no Node change is required on Oracle for the Python/FastAPI app.
- No Windows or Oracle installation was performed by the assistant; no application code, server runtime or source config was changed.


## 2026-11-05 — JobBeeper public homepage HAR and runtime API findings

### Evidence collected
- User supplied a sanitized Chrome DevTools HAR from the isolated REA Chrome profile, capturing a public homepage load and a short idle window. Browser: Chrome 156.0.8078.80. Capture starts 2026-11-05T10:56:51.520Z; first API activity follows shortly after page load.
- HAR contains 50 HTTP entries: 47 to jobbeeper.com, 1 Google Tag Manager script load, and 2 Google Analytics collection POSTs. Statuses: 46 x 200, 2 x 401 (unauthenticated session lookups), 2 x 204 (analytics). No failed static asset responses were observed.
- The sanitized HAR contains no Cookie/Authorization/Set-Cookie headers and no request postData. Do not reproduce public plan response payment-routing values in documentation, tickets, code or reports. The /api/auth/plan response included UPI routing fields; values intentionally omitted.
- Request headers show X-Client-Timezone: Asia/Calcutta. The HAR was captured with DevTools Disable cache and Preserve log enabled; request Cache-Control: no-cache / Pragma: no-cache therefore should not be used to infer normal browser cache behavior.

### OBSERVED — runtime HTTP endpoints
- GET /api/public/pulse -> 200, application/json, response time approx. 84 ms on first request and 99 ms on the second.
- GET /api/auth/plan -> 200, application/json.
- GET /api/auth/plans -> 200, application/json.
- GET /api/auth/user/me -> 401, response body reports missing authorization token.
- GET /api/auth/me -> 401, response body reports missing authorization token.
- The two 401s occurred in an unauthenticated public homepage session. No authenticated/private account behavior was exercised.
- /api/public/pulse response headers included Cache-Control: public, max-age=60. The auth plan endpoints returned private/no-store cache directives.
- /api/public/pulse was requested twice, approximately 14.5 seconds apart. This is only two requests and must not be described as a proven 15-second polling interval.

### OBSERVED — public pulse response shape and snapshot
- JSON top-level fields: generated_at, locked, open, stats, sufficient, window.
- locked items in the captured response included age_minutes, found_after_minutes, location, source and title; captured locked records did not include company or share_path.
- open items included age_minutes, company, found_after_minutes, location, share_path, source and title.
- Snapshot had 3 locked and 3 open records. Locked sample ages were 2–3 minutes; open sample ages were 362–363 minutes. open records had share_path values; locked records had found_after_minutes null and no share_path in the captured objects.
- stats snapshot (time-bound, not a stable product constant): companies_tracked=79,469; jobs_24h=77,742; jobs_last_hour=2,839; jobs_week=452,780; median_alert_minutes=10; portals_watched=89,905; share_delay_hours=6. Response window was "hour" and sufficient=true.
- generated_at values of the two pulse responses were approximately one minute apart even though the two client requests were approximately 14.5 seconds apart. Preserve as observed; generation/cache cadence is not yet explained.
- The captured record structure is consistent with the public-page statement that newer jobs are subscriber-first and held from the public feed for six hours. Treat this as a well-supported inference, not proof of the private subscriber delivery path.

### OBSERVED — static frontend code from HAR/REA bundle analysis
- API client module api-B1bIDMMX.js defines API base path /api and a fetch wrapper using credentials: include. It adds X-Client-Timezone from Intl.DateTimeFormat().resolvedOptions().timeZone; non-GET methods attach X-CSRF-Token from the jn_csrf cookie. Static code contains a 401 refresh fallback trying POST /auth/user/refresh and then /auth/refresh before retrying unless noRetry is set. Those POST refresh requests were NOT observed in this unauthenticated HAR; this is source-code evidence only.
- LiveJobFeed-DGhOmHyc.js calls the API client with GET /public/pulse. Its hook default interval is 90,000 ms; it fetches immediately on mount and has a visibilitychange handler which fetches again when document.visibilityState becomes visible. Thus, the 14.5-second separation in the HAR must not be interpreted as the normal polling interval; a visibility event or another trigger is plausible but the exact cause was not captured. Confirm with a longer stable Network recording if needed.
- The LiveJobFeed component calculates/display-formats job ages client-side and uses stats from the pulse response (jobs_last_hour or jobs_24h depending on window, median_alert_minutes, portals_watched, companies_tracked).
- portalLabels-tSl-pka_.js contains labels for many ATS/source families including LinkedIn, Greenhouse, Ashby, Lever, Workday, SmartRecruiters, Darwinbox, SuccessFactors, iCIMS, Naukri, Cutshort, Instahyre, Hirist, Oracle Cloud Recruiting, Wellfound, Workable, PeopleStrong, Phenom, Eightfold, Zoho Recruit, Keka, Freshteam, Taleo, Avature, BambooHR, BrassRing, Jobvite, Breezy, Recruitee, Rippling, Teamtailor, UKG, LinkedIn Hiring Posts, X Hiring Posts and others. This is a frontend label registry, not proof that every listed integration is active or currently collecting.
- portalLabels module contains static code paths for GET /companies/platforms and fallback GET /auth/user/portals; neither request appeared in this HAR, so runtime behavior remains unverified.
- REA's static bundle analysis retained 29 script sources and parsed most sources, but the 293 KB index bundle exceeded REA's per-script deadline. The HAR itself includes the fetched JavaScript response bodies, enabling targeted offline inspection of specific bundles if required.

### INFERRED — architecture implications
- /api/public/pulse is a public, aggregate feed/statistics endpoint and should be treated separately from authenticated user/job preference APIs.
- Public job access is staged: records in locked are newer and omit company/link fields in the observed representation; open records are older and include company/share_path. The six-hour delay matches the product's public statement.
- The frontend API utility centralizes the /api prefix, credentialed fetches, timezone header, CSRF behavior for mutations and a refresh/retry path. Do not imitate refresh endpoints or private APIs; only use documented/public behavior in the user's own design.
- The 90-second LiveJobFeed interval is source-code evidence. Validate actual runtime cadence with longer recording and page-visibility controlled before using it as a performance benchmark.

### UNKNOWN / not established by this HAR
- No logged-in behavior, private user feed, saved preferences, Telegram delivery, alert rules or subscriber-first notification path was observed.
- No search/filter queries, company directory requests, job-detail API calls, pagination cursors or source-specific feeds were captured.
- No backend framework, database schema, ingestion architecture, collector schedule, deduplication mechanism or exact meaning of found_after_minutes has been established.
- The 401 auth lookups do not establish the complete authentication design.
- The HAR's two pulse requests do not independently establish the 90-second interval; static bundle source contains that interval, and a longer runtime test remains desirable.

### Next exact investigation step
- Continue read-only public investigation. Navigate the isolated Chrome profile to /browse/hiring-this-week and capture a sanitized HAR with Preserve log; examine actual browse API calls, response shape, filter parameters, pagination and job IDs. Then open one public /j/{id}-{slug} detail page and capture its requests.
- Do not sign in, change settings, submit applications, create alerts, automate interactions, or access private account data during this public investigation.
- No Job Radar application code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed as part of this research.


## 2026-11-05 — JobBeeper browse, company and public job-detail HAR findings

### Capture overview
- User supplied a sanitized Chrome DevTools HAR captured while navigating the isolated browser through the homepage, `/browse/hiring-this-week`, `/browse/company/domino-s`, and `/j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s`.
- HAR contained 137 HTTP entries across four page groups. 81 requests were to jobbeeper.com and 56 to Google-related hosts/services.
- Overall statuses: 92 x 200, 22 x 301, 12 x 404, 7 x 204, 4 x 401.
- JobBeeper-only statuses: 77 x 200, 4 x 401. The 4 JobBeeper 401s were unauthenticated homepage lookups to /api/auth/user/me and /api/auth/me; the public browse/company/job-detail documents returned 200.
- The 22 HTTP 301 responses were Google favicon lookup redirects (/s2/favicons); the 12 HTTP 404 responses were gstatic favicon lookups (/faviconV2), not JobBeeper application routes. The 7 HTTP 204 responses were Google Analytics /g/collect POSTs.
- HAR contains 4 page records: homepage, hiring-this-week, Domino's company page, and one Domino's job detail. The main public routes were navigated as distinct pages.
- The capture did not include Cookie, Authorization, Set-Cookie, Proxy-Authorization or X-API-Key headers. HAR response objects had MIME type and body size but no response body text for the public HTML documents. Do not infer HTML content from byte sizes alone.

### OBSERVED — public page routing and delivery
- `GET /` -> 200 text/html.
- `GET /browse/hiring-this-week` -> 200 text/html, response content size 85,920 bytes; document request about 580 ms. HAR page timing: onContentLoad ~869 ms; onLoad ~1,200 ms.
- `GET /browse/company/domino-s` -> 200 text/html, response content size 176,280 bytes; document request about 321 ms. HAR page timing: onContentLoad ~494 ms; onLoad ~687 ms.
- `GET /j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s` -> 200 text/html, response content size 67,639 bytes; document request about 198 ms. HAR page timing: onContentLoad ~339 ms; onLoad ~576 ms.
- The browse, company and detail pages each loaded shared assets: `/static/jobpage.js`, `/static/publicpage-theme.js`, and `/static/publicpage-ui.js`. The job detail page additionally loaded `/static/public-job.css`. CSS and JavaScript resources returned 200.
- Each of the four page paths (including homepage) had a document request and a near-immediate duplicate Fetch request for the same URL. The second request's initiator stack points to `https://jobbeeper.com/sw.js` at line 58 (HAR lineNumber 57), confirming service-worker involvement in the duplicate fetch. The service-worker script body was not captured, so cache strategy, navigation preload behavior and purpose of this duplicate are unknown.
- On the three browse/company/detail page groups, no same-origin JSON API endpoints appeared in the HAR. The only observed same-origin API JSON traffic in this HAR was on the homepage: `/api/public/pulse`, `/api/auth/plan`, `/api/auth/plans`, `/api/auth/user/me`, and `/api/auth/me`.
- The 81 JobBeeper requests included the homepage's SPA bundles and pulse/plan endpoints, and the separate public-page static assets. This appears to be a distinct public HTML page delivery path for browse/company/job-detail routes, but implementation boundary needs source/runtime confirmation.

### INFERRED — public browsing architecture
- Large HTML documents plus shared public-page JavaScript/CSS, with no observed JSON API calls on the browse/company/detail pages, are consistent with server-rendered HTML or content embedded in delivered HTML. This is not proven because the sanitized HAR omitted response bodies.
- The `/sw.js`-initiated duplicate Fetch requests indicate the service worker participates in navigation handling or follow-up fetch behavior. Do not label the strategy as cache-first, network-first or stale-while-revalidate without observing the service-worker source or controlled runtime behavior.
- The public browsing pages may use a different implementation path from the homepage SPA. The homepage uses hashed `/assets/*.js` modules and /api JSON endpoints; the public browse/detail pages load `/static/*.js` and larger HTML documents.

### UNKNOWN / not established by this capture
- Actual HTML text, job-card data, company metadata, job description fields, filters, pagination, page size, and application outbound URL are unknown because HAR response bodies were not included.
- No filter form submission, query change, next-page action, detail CTA click, logged-in flow, or private job preference behavior was observed.
- No backend route handlers, database schema, template system, service-worker caching policy, source collection schedule, job ingestion or deduplication behavior were established.
- No same-origin JSON API calls for browse/company/detail appeared in this capture. This does not prove that those pages never call APIs; lazy loading, user interaction, scroll-triggered activity or a different state may initiate additional calls.

### Next exact investigation step
- Use REA `inspect-web-page` against the currently selected public job-detail or browse page, after refreshing target discovery, with accessibility text enabled; this should capture actual visible labels and page structure without relying on HAR response bodies. Keep the page stable during the capture.
- Then inspect `/static/jobpage.js` and `/static/publicpage-ui.js` as public, loaded scripts using REA bundle/source observation. Avoid executing unknown page code outside the site's normal browser context.
- After page content is understood, test public filtering and pagination manually in Chrome while recording a sanitized HAR. Record which controls were used and compare URL/query changes and network requests. Do not sign in, submit applications, create alerts, or access private data.
- No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed during this capture or its analysis.


## 2026-11-05 — Public Domino's job-detail page inspection

### Capture identity and completeness
- User supplied REA `inspect-web-page` capture for target `545C6994ACD1807FE62AFF719D41E56C`, URL `https://jobbeeper.com/j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s`, page title `Delivery Driver(02202) - 1027 W Hunter St at Domino's — JobBeeper`.
- Observation window: 2026-11-05T11:10:21.605Z through 11:10:22.672Z (about 1 second). Accessibility capture enabled; network requests and script source capture were not included, and observation begins after REA attaches.
- DOM contains 623 nodes; accessibility tree contains 313 nodes. Three first-party scripts were observed: `/static/publicpage-theme.js` (2,842 bytes), `/static/jobpage.js` (2,651 bytes by script metadata; resource size 2,653 bytes), and `/static/publicpage-ui.js` (5,259 bytes). No source maps reported.
- DOM URL metadata exposes public internal links and login/signup redirect paths. Four URLs were excluded because destination origins were outside the approved origin policy; their actual destinations were not disclosed. Do not infer or attempt to recover excluded external destinations.
- Network request list was empty due attach-limited timing; this does not mean page has no network activity.

### OBSERVED — job-detail content and fields
- Public listing title: `Delivery Driver(02202) - 1027 W Hunter St`.
- Company: Domino's.
- Location: Logan, OH, United States.
- Summary metadata:
  - Work mode: `No` (retain literal source value; field semantics require further interpretation).
  - Employment: `Full-time`.
  - Listed: `Posted 9 hours ago`.
  - Source: `Smartrecruiters`.
- Role description section says: `Only a short excerpt is available here.` and `The full responsibilities and requirements may be missing.`
- A public link says `Sign in to open the original listing` and another page message says to sign in to open the employer's application link and track the application.
- Application panel has CTA `Log in to apply` plus `Create free account`. Public href for login includes redirect to `/user/job/28752345` and UTM attribution. Signup href includes `next=/user/job/28752345` and UTM attribution.
- No salary or explicit experience requirement was exposed in the captured public accessibility tree. This does not prove the original employer listing has no such information.
- Public page contains a `Copy job link` button and `Browse openings` link.
- Related section `More openings worth a look` says `6 roles` and lists six other Domino's public job pages. Examples include Assistant Manager, Customer Service Rep and Delivery Driver roles in US locations.
- Footer/header include Create an alert, Sign in, Get App, JobBeeper home, How it works and Pricing navigation.

### OBSERVED — promotional metrics displayed on this individual page
- `31 min`: from SmartRecruiters publishing this role to JobBeeper finding it.
- `14 min`: median time from a role going live to a subscriber being told.
- `6 hours`: subscribers had this role before this page existed.
- `76,954`: roles found in the last 24 hours.
- These are page-displayed claims / a captured snapshot, not independently verified measurements; the 24-hour count is dynamic and differs from the homepage HAR snapshot.

### INFERRED — public preview and conversion model
- Public detail page is deliberately incomplete: it exposes title, company, location, a few normalized fields, listing age/source and a short description excerpt, but directs unauthenticated visitors to sign in to view the original listing and employer application URL.
- The `/user/job/28752345` redirect path suggests authentication gates a user-specific job/application view, but authenticated behavior has not been tested.
- The related-jobs module appears to connect opportunities within the same company and includes six alternative postings on the detail page.
- The metric labels distinguish source publishing -> JobBeeper discovery -> subscriber notification -> public-page availability. These should be separate timestamps/stages in our own latency model; definitions and measurement methodology remain unverified.
- The page uses a separate public-page rendering path from the homepage SPA, based on server-delivered HTML and three standalone public-page scripts; exact backend implementation remains unknown.

### UNKNOWN / not established
- Full employer description, original application URL, pay, benefits, skills, experience requirements, qualifications and complete canonical job object are unavailable from this public preview.
- Values `Work mode = No` and exact field semantics need inspection in more job examples before defining enum mappings.
- No evidence whether job detail data is embedded in HTML, retrieved by hidden/lazy scripts, or assembled by a server-side template; response body was not captured in HAR.
- No actual click behavior for Copy job link, sign-in, create account, apply, create alert or related-job links was tested. No account was created and no application submitted.
- No logged-in private listing, subscriber alert, tracking workflow, or original employer ATS redirect was observed.
- Four external DOM destinations were policy-excluded. Their targets remain unknown and will not be bypassed.

### Implications for our own canonical job model
- Public/basic fields to model: title, company, normalized location, employment type, work-mode source value, source/ATS label, listed_at or source-listed display, discovered_at, description_excerpt, description_completeness/visibility, public_detail_url, canonical job ID, related-company jobs.
- Keep separate source-posted, discovered, subscriber-notified and public-release timestamps; don't substitute page display claims for system timestamps.
- Preserve unknown/null values explicitly; don't map `Work mode = No` to onsite or remote until validated.
- Keep source application URL separately from our own application redirect/tracking. Decide access policy independently; no need to replicate JobBeeper's account gate.

### Next exact investigation step
- Run REA `analyze-web-bundle` on the current public job-detail target (and then, separately, on a browse target) to capture/analyze the three first-party public-page scripts. Focus on jobpage.js and publicpage-ui.js. Record any data-field names, outbound URL handling, analytics events and UI behavior as static-code evidence, distinct from runtime observations.
- Next, inspect the `/browse/hiring-this-week` page accessibility tree to identify visible filters, cards, sort controls, pagination and empty states; then manually exercise one public filter or pagination control while recording a sanitized HAR. Do not access the original employer application URL or private account data.
- No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed.


## 2026-11-05 — Static analysis of public job-detail JavaScript

### Capture and parser result
- User supplied REA `analyze-web-bundle` output for public Domino's job detail URL `https://jobbeeper.com/j/28752345-delivery-driver-02202-1027-w-hunter-st-domino-s`.
- Three first-party scripts were observed and all three parsed successfully:
  - `/static/publicpage-theme.js` — 2,842 bytes; SHA-256 `fedefd1627cfacc80c2fb9cfd8129ec8b7af820162339880eb9c4cc44e6555c8`.
  - `/static/jobpage.js` — 2,653 bytes; SHA-256 `628090b59538f7d42ff1bad4b13d6f0b236a172acba0e3d65e4395b251471b0e`.
  - `/static/publicpage-ui.js` — 5,259 bytes; SHA-256 `fbd77391e95e9232cf8b5a382f97e58c7ed625f3a7b62306d0211d3518a813d4`.
- REA analysis completeness: 3 parsed scripts, 0 parse failures, 1,520 AST nodes visited. Static source analysis only; scripts were not executed by REA.
- Source-map fetching was not requested; no source-map findings can be inferred.
- Route inventory found zero route patterns and zero route occurrences within these 3 provided sources. This is not proof that no routes exist elsewhere.

### OBSERVED — static call candidate
- REA identified one low-confidence static endpoint candidate in `jobpage.js` at line 38, column 2: `/api/auth/user/me`, mechanism `call:fetch`.
- The exact static call candidate is a fetch to the current-user/session endpoint. This is consistent with the earlier HAR's unauthenticated request to `GET /api/auth/user/me` returning 401 when no authorization token was present.
- No additional endpoint candidates, route strings, source-map references or import edges were identified in the three parsed scripts.

### INFERRED — public-page script responsibilities
- `publicpage-theme.js` and `publicpage-ui.js` appear to support shared theme and public-page UI behavior based on their filenames and DOM usage. Their detailed function-level responsibilities are not established by the static route/endpoint inventory.
- `jobpage.js` appears to include session-aware behavior, potentially toggling user-specific controls or sign-in state based on `/api/auth/user/me`. Exact response fields and resulting behavior remain unverified.
- Given the public page's detail content was already present in the DOM accessibility capture and no job-data fetch candidate was found in these three scripts, a plausible model is that the job content is delivered with the HTML while client JavaScript enhances the page and checks user session. This is only an inference; server templates or inline serialized data were not directly inspected in this bundle analysis.
- The lack of public job-content API candidates in these scripts is not evidence that no such API exists elsewhere or is never called by other code paths.

### UNKNOWN / not established
- No complete job schema, original application link, pay or experience extraction behavior was recovered from these three scripts.
- No event handler behavior for Copy job link, Apply/Log in, Create account, alert or related openings was behaviorally tested.
- Static analyzer did not enumerate dynamically constructed URLs or route names, hidden server-side routes, or network operations in other scripts.
- No source maps were requested; original source modules remain unavailable.
- The `/api/auth/user/me` candidate was previously observed in runtime HAR only on the homepage, not specifically exercised by this static analysis on the job page.

### Next exact investigation step
- Navigate the isolated Chrome profile to `/browse/hiring-this-week`; rediscover its target ID; capture accessibility text with `inspect-web-page`. Identify visible filters, sorting, job cards, pagination and links.
- Then manually use one public browse control (prefer a filter that changes the URL) with Network Preserve log enabled and export a sanitized HAR. Do not submit forms that create accounts, alerts or applications.
- If additional source analysis is needed, inspect public-page script source only within the normal page scope, and focus next on the hiring-this-week page's loaded scripts rather than re-running the detail-page bundle analysis.
- No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls or deployment were changed.


## JobBeeper hiring-this-week feed inspection — 2026-11-05

### OBSERVED — passive REA accessibility/DOM capture
- Page: `https://jobbeeper.com/browse/hiring-this-week`; title: `Who is hiring this week — JobBeeper`.
- REA evidence ID: `ev_ab4ed5862048380655d9421dbfeccd63eb35f12e9a877546a181ada8e6a1635a`; capture window: `2026-11-05T11:17:48.745Z` to `11:17:49.814Z` (1-second observation).
- Captured DOM: 1,175 nodes. Accessibility tree: 545 nodes. 61 anchor elements in DOM; 13 BUTTON elements in raw DOM, but only one accessible button exposed in the captured tree: `Color theme: System`. No INPUT, SELECT, or FORM elements were present.
- Public browse navigation links: Companies, Hiring this week, Backend, Frontend, Data. These are route links, not evidence of an interactive in-page filter control.
- Sections: `Top hiring companies` (20 company links with live-opening counts) and `Freshest openings` (label `Latest 20`, with 20 job links).
- Snapshot metrics shown in the page: 5,873 active companies and 20,000 recent public openings. The page explicitly says this is a sample of the latest 20,000 public openings and that counts describe the sample, not the whole job market. Treat all such counts as dynamic, time-bound marketing/page data, not durable platform totals.
- Example top-company counts in this capture: Domino's 844; Accenture India 413; jobgether 263; CVS Health 194; Winners Merchants International, L.P. 166. All 20 company entries have `/browse/company/{slug}` links.
- Each of the 20 freshest job links follows `/j/{job-id}-{slug}`. The captured accessibility labels consistently expose title, company, and location. Examples: Senior Product Manager, Growth — Motive — Hybrid - Bangalore; Senior Product Designer — Motive — Bangalore, India; Software Engineer 1 — New Relic — Hyderabad, India; Mechanical Engineer – HVAC/Building Systems — Farnsworth Group — Phoenix, AZ; Mission Designer — Absurd Ventures — Santa Monica.
- The observed job IDs in this one snapshot range from 28757581 down through 28757562. This is a single page sample, not proof of a permanent ID or pagination scheme.
- No visible keyword search, location filter, experience filter, employment-type filter, sorting selector, or pagination/load-more control was present in this capture. No pay, experience, source/ATS label, or posted-age field appeared in the accessible job-card labels. This only establishes what the public cards expose in this capture; it does not establish that the underlying job records lack those fields.
- The same three first-party scripts were loaded on this browse page: `/static/jobpage.js` (2,653 bytes), `/static/publicpage-theme.js` (2,842 bytes), and `/static/publicpage-ui.js` (5,259 bytes). Source text was not included in this inspection.
- Capture was policy-filtered and attach-limited. REA began observation after page load; it reports zero network requests in its short observation window and explicitly says prior network activity is unavailable. Do not interpret that as proof of no requests during page load.
- Separate earlier sanitized HAR across hiring feed, company page, and job detail recorded no same-origin JSON API calls for those page loads. That is a bounded observation only, not proof that no other public/interactive page state uses APIs.

### INFERRED — keep separate from observed facts
- The public feed appears to be delivered as HTML with lightweight shared public-page scripts, consistent with earlier browse/company/detail HAR observations. Server-side rendering is plausible but not proven from this capture alone.
- The visible Backend, Frontend, and Data links are the best next candidate for testing category-specific browse routes. They should not be described as query filters until a route transition and its resulting content are compared.
- The `Latest 20` label and 20 visible job links suggest a fixed-size public preview on this route; they do not establish whether authenticated pages expose more jobs or whether pagination exists elsewhere.

### UNKNOWN / not established
- Whether the Backend/Frontend/Data routes accept query parameters, how they select jobs, and whether they share the same template.
- Whether any filter, sorting, or pagination controls exist on authenticated browse pages or other routes.
- Whether job-card metadata such as salary, experience, ATS/source, or posted time is available only on the detail page or behind authentication.
- The feed's ranking algorithm and exact relationship between job IDs, discovery times, and ordering.

### Next exact investigation step
- Test one public category route only: click the visible `Backend` link (`/browse/role/backend`) while Chrome DevTools Network has Preserve log enabled. Compare the URL, page title, visible job count, card fields, and page navigation with the hiring-this-week capture; export a sanitized HAR with cookies, authorization headers, and personal data removed.
- Do not create an alert, account, or application. No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls, or deployment were changed by this inspection.


## Backend category-route HAR inspection — 2026-11-05

### OBSERVED
- User supplied a sanitized HAR for navigation to `https://jobbeeper.com/browse/role/backend`, from the `/browse/hiring-this-week` page. HAR page title/analytics title: `Latest Backend jobs | JobBeeper`.
- HAR contains 10 entries: 8 to `jobbeeper.com`, one Google Tag Manager script, and one Google Analytics event. All 8 first-party requests returned 200.
- Backend route requested `GET /browse/role/backend` as `text/html`; response was HTTP 200. There are two HAR records for the same document URL: one document request and one Fetch request initiated by `https://jobbeeper.com/sw.js` at line 57. Both record HTTP 200. The actual fetch response headers include `Cache-Control: public, max-age=3600`, `Content-Type: text/html; charset=utf-8`, `Content-Encoding: zstd`, `X-Cache-Status: MISS`, and `Date: Thu, 05 Nov 2026 11:21:58 GMT`.
- The page's load timing in HAR: onContentLoad about 660 ms; onLoad about 859 ms. The main document request duration was about 558 ms.
- The other first-party page resources were `/fonts/poppins.css`, `/static/jobpage.js` (2,653 bytes), `/static/publicpage-theme.js` (2,842 bytes), `/static/publicpage-ui.js` (5,259 bytes), `/fonts/poppins-700.woff2` (50,668 bytes), and `/fonts/poppins-400.woff2` (51,172 bytes). All returned 200.
- One Google Tag Manager JS request returned 200; one Google Analytics `/g/collect` page-view POST returned 204. Google Analytics event title was `Latest Backend jobs | JobBeeper`, referrer was `/browse/hiring-this-week`, and document location was `/browse/role/backend`.
- No first-party JSON/XHR/API endpoint appears in this 10-entry HAR capture.

### INFERRED — not proof
- The Backend route is presented as its own public HTML page, not an in-page client-side filter visible in this navigation capture.
- The Fetch request initiated by `sw.js` is consistent with service-worker involvement in public-page navigation. The HAR's `_fetchedViaServiceWorker` fields are null, so do not claim the response was definitively served from service-worker cache or that the cache strategy is known.
- The `Cache-Control` and `X-Cache-Status` headers indicate that the HTML response is publicly cacheable for up to one hour and that the observed origin/cache status was MISS on this request. This is only this response's cache metadata.

### UNKNOWN / not established
- The HAR does not retain response text, so job titles, company names, locations, number of visible cards, page controls, sorting, and filters on the Backend page are not available from this file.
- It is not proven whether the Backend route is generated from a separate curated dataset, a server-side category query, or a common template with a route parameter.
- The 10-entry capture cannot rule out API requests on other interactions, authenticated pages, or different browse routes.

### Next exact investigation step
- Keep Chrome on `https://jobbeeper.com/browse/role/backend`; rediscover its target ID with `list-browser-targets` and run `inspect-web-page` with `--include-accessibility-text --observation-ms 1000 --json`. Compare the visible Backend card count, titles, companies, locations, controls, links and ordering with the prior `/browse/hiring-this-week` capture.
- Only after the DOM comparison, choose one clearly visible public navigation/control for a second controlled test. Do not create alerts, accounts, or applications. No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls, or deployment were changed by this investigation.


## Backend category DOM inspection — 2026-11-05

### OBSERVED
- REA evidence ID: `ev_c220ac81730bb00fc4720d535b3e1f69a40f858cb7c423e0d63ba7a6933a04a0`; target remained `https://jobbeeper.com/browse/role/backend`, title `Latest Backend jobs | JobBeeper`.
- 1-second accessibility capture; 3,797 DOM nodes and 2,057 accessibility nodes.
- Page headline: `Fresh Backend roles, without the noise.`; section heading: `Latest Backend openings`; supporting text says the shortlist is ordered by freshness.
- Result count displayed: `200 found`; `200 roles`. The page explicitly states: `Showing the latest 200 public results, up to 200. Search filters this displayed list.`
- Exactly 200 accessible job links share one result-list parent. Each link's accessible name exposes job title, employer, and location, and includes work-mode text such as Remote, Hybrid, or On-site when available. Detail links follow `/j/{id}-{slug}`.
- Search field: accessible role `searchbox`, label `Search Backend roles`; corresponding DOM input has `data-filter-input`. Each of the 200 job anchors has `data-filter-item` and `data-filter-text`. This markup aligns with the page's own statement that search filters the displayed list.
- Separate location form: one `FORM` with a searchbox labelled `City, country, or remote` and a button labelled `Filter location`. Form action resolves to the same Backend route. No behavior of the location submit was tested.
- Accessibility tree exposes no sort selector or pagination/load-more control. Accessible buttons are `Filter location` and `Color theme: System`. Searchboxes are the role-search and location fields.
- This is unlike the `/browse/hiring-this-week` public snapshot, which had a `Latest 20` set without visible search or location forms. Backend category route exposes a 200-result public set.
- The 200 Backend entries are not all clearly Backend-specific based on their visible titles. Examples in the captured first 20 include `Actuarial Internship Program 2027`, `DSRD Global Pathology Quality Control Scientist`, and `Frontend Software Developer`. Additional visible entries farther in the 200-card sample include Chemistry Expert, Mathematics Specialist, Biology Researcher, and Population Health Informaticist. This is direct evidence of category relevance noise in this snapshot, not proof of how the category was assigned.
- Page category and card metadata are public preview values. No job age, salary, explicit experience, or ATS/source label was found in the accessible job-card names; this does not establish that those fields are absent from hidden/server-side job records.
- The separate one-second REA capture began after load; network request list is empty with prior activity unavailable. The earlier sanitized HAR remains the bounded network evidence: HTML route, shared first-party scripts, no first-party JSON/XHR/API request in that capture.

### INFERRED — confidence bounded by DOM structure
- Client-side in-list search is strongly indicated by the `data-filter-input` field, 200 `data-filter-item` anchors, and explicit text saying search filters the displayed list. Treat it as filtering the loaded 200-result DOM list until a controlled interaction shows otherwise; do not assume it searches the whole JobBeeper corpus.
- Location selection appears to be a separate form submission to the same category URL, likely a server/navigation filter, but actual query parameters and result behavior remain untested.
- The page appears to use a fixed public preview cap of 200 results. Pagination or deeper public retrieval is not exposed in this capture.
- Role category should be treated as a noisy discovery bucket rather than a strict normalized job family until precision is measured.

### UNKNOWN / not established
- Actual search matching logic (title only vs title/company/location/full card), debounce behavior, clear/reset behavior, and whether search state changes the URL.
- Location input autocomplete/suggestion mechanism, allowed values, form method/query parameters, and the resulting URL/result set after submit.
- How the 200 results are selected and ranked beyond the page's freshness claim; whether older roles are reachable on a later page or in an authenticated session.
- Whether any further sort/pagination controls are available outside the captured public state.
- How category assignment works and why visibly non-backend roles are included.

### Next exact investigation step
- Manually test only the `Search Backend roles` field with a unique short term already visible in a card (e.g. `Cognizant`) while DevTools Network Preserve log is enabled. Observe whether the visible count/cards change immediately, whether URL changes, and whether any request is sent. Do not submit location yet; isolate the search behavior first.
- After that, test the `City, country, or remote` form with a grounded location only if necessary, recording the URL, visible count/cards, and HAR. Do not create alerts, accounts, or applications. No Job Radar app code/config, Oracle runtime, SQLite database, collectors, Telegram notifications, provider API calls, or deployment were changed by this inspection.


## Backend search interaction and research-to-build decision — 2026-11-05

### OBSERVED — search interaction
- New REA evidence ID: `ev_fdb8b7bbb29e59ff3bb337775db569496bdb1d4df043e0108461bd84e9a9988a`; capture at `2026-11-05T11:33:01Z`; same Backend public route.
- Searchbox is focused and its accessible value is `Cognizant`.
- The DOM still contains 200 job-card anchors marked `data-filter-item`; 199 carry the `hidden` attribute and one remains visible.
- The visible matching item is `Engineering Manager Cognizant · Bengaluru, Karnataka, India (Hybrid)`.
- Page count text retains `200 found`, while the dynamic filter-count text is `1 role`.
- The search interaction's DOM state therefore demonstrates filtering among the 200 already-rendered cards. This is strong evidence of client-side filtering of the loaded preview, not a fresh query across the complete job corpus.
- REA observation started after the interaction; no prior network activity is available. The capture reports no requests during its short 1-second observation, but cannot prove no request was issued during the keypress before capture began.

### Research boundary / conclusion
- Public UI + sanitized HAR have established the public browse surfaces, a 20-card Hiring-this-week preview, a 200-card role-category preview, role-page search behavior, a location form, public HTML delivery, shared page scripts, and a one-hour public HTML cache header observed on the Backend route.
- JobBeeper's private collection architecture is not exposed by these observations. The public pages do not reveal scheduler design, worker count, queue, source credentials/agreements, per-source rate limits, source fetch intervals, retry policy, or database/index architecture. These are UNKNOWN, not inferable from a fast UI.
- Public JobBeeper claims (homepage as reviewed 2026-11-05): it checks LinkedIn, Naukri, Workday and company career pages; sources presented include Greenhouse, Lever and Ashby; its site says availability and detection times vary by source. Treat stated coverage numbers and per-job discovery-time displays as vendor claims/snapshots, not independently verified measurements. Do not assume it avoids rate limits.
- Important distinction: fast public page render/search is not proof of fast upstream collection. The captured role page already contains 200 result cards, and its search hides/show cards locally. Public HTML caching and precomputed/rendered results can explain the fast UI independently of how frequently sources are polled.

### Decision: stop open-ended JobBeeper reverse engineering and begin product development
- Do not block our product on discovering JobBeeper's private backend. Exact internal architecture is not recoverable from public browser evidence. Keep any later reverse engineering narrowly targeted to a specific unresolved product decision.
- Existing Job Radar v2 remains the foundation; preserve it and extend it incrementally rather than replacing it. Current documented foundation: FastAPI, SQLite, Docker on Oracle VM, separate source collectors, Telegram notifications, and dashboard APIs. Reconfirm actual checkout/runtime state before first code change; this documentation alone is not a production health check.
- Start with a short architecture/PRD baseline for a reliable ingestion system:
  1. Source registry and capability contract per adapter: canonical source, endpoint/feed/page type, allowed access method, poll interval, concurrency, freshness expectation, last success, last error, retry/backoff, rate-limit state.
  2. Per-source scheduler with jitter, bounded concurrency, host-level request budgets, conditional requests where supported (ETag/If-Modified-Since), incremental cursors, and 429/Retry-After-aware exponential backoff. Respect provider policies; no login bypass, CAPTCHA bypass, proxy/account rotation or rate-limit circumvention.
  3. Collect → retain raw evidence → normalize canonical job → deduplicate/merge → upsert → classify/match → notify. Keep source-specific raw provenance for audit and reparsing.
  4. Explicit freshness/latency metrics: source-published time (when supplied), first-seen time, last-seen time, collection lag, processing lag, notification lag, run duration, status/429 counts, and stale/closed detection. Do not conflate UI latency with ingestion latency.
  5. Source priority: stable public ATS endpoints/feeds and official career-page integrations first; compliant partner/provider APIs or board integrations next; less stable public pages only where permitted and operationally justified. Evaluate LinkedIn/Naukri access paths separately rather than making them a critical dependency for all other collectors.
- Phase order: (A) read-only repo and production baseline; (B) source inventory + adapter contract + end-to-end sequence diagram; (C) PRD/acceptance criteria; (D) implement instrumentation and one reliable new adapter end to end; (E) expand adapters and matching; (F) referral intelligence after discovery and notification reliability are measured.
- No implementation changes were made as part of this research update.

### Next exact development step
- Perform a read-only audit of the current `v2-live-radar` checkout and Oracle runtime, confirm exact commit, enabled collectors, real per-source scan/last-success/429 state, DB counts, and Telegram configuration presence (never reveal secrets). Use the previously supplied read-only Oracle diagnostic command. Then produce a source inventory/architecture baseline from current code before editing.


## JobBeeper collection architecture — current public evidence and LinkedIn boundary (2026-11-05)

### OBSERVED — public product evidence
- JobBeeper homepage says it checks LinkedIn, Naukri, Workday and company career pages; its source list names Greenhouse, Lever and Ashby, and the homepage says availability and detection times vary by source.
- The homepage shows 11 job sources in a demonstration and a snapshot of 89,849 career pages/job boards watched and 79,424 companies tracked (snapshot dated 4 Nov 2026). These are JobBeeper's own claims and dynamic snapshot values, not independently audited metrics.
- The homepage says matching jobs go to subscribers privately first and jobs that can be shared appear on the public site after the private window. It displays a 6-hour subscriber head start.
- The public company page for LinkedIn shows an 18-role shortlist and source logos/labels for Greenhouse, Instahyre, Lever, LinkedIn, Naukri, own, SmartRecruiters and Workable. This demonstrates that JobBeeper's public surface associates roles with multiple source types; it does not reveal whether it obtained any particular role from the company ATS, LinkedIn, a licensed partner, or multiple origins.
- A public JobBeeper detail page labels its source LinkedIn and claims a 32-minute interval from LinkedIn publishing to JobBeeper finding it; another JobBeeper page claims 14 minutes for a different role. Such per-role displayed intervals are vendor claims and page snapshots, not an independent measurement of their collection method.
- The role-category page preloads up to 200 jobs into the DOM. A user search for `Cognizant` left one visible card and 199 hidden cards without replacing the 200-card collection. Strong evidence for client-side local filtering of the already-loaded page results, not global source search.
- The Backend route HAR recorded public HTML with `Cache-Control: public, max-age=3600` and `X-Cache-Status: MISS` on that request. This is a single page response, not evidence of internal job-ingestion caching strategy.

### VERIFIED — LinkedIn public API/policy boundary (checked 2026-11-05)
- LinkedIn's official Job Posting API documentation states the API is for approved third parties such as clients, ATS systems and job distributors to post jobs to LinkedIn on behalf of customers. It is not documented as a general public API for searching/reading the full LinkedIn job catalogue.
- The same documentation says API access is restricted to developers approved by LinkedIn and requires a partner/API agreement. It states LinkedIn is not accepting new Job Posting API partnerships and directs access applicants to Apply Connect. The Microsoft Learn page records last updated 2026-06-03.
- LinkedIn help documentation prohibits third-party crawlers, bots, browser extensions and other tools that scrape or automate LinkedIn, and says circumventing access controls or usage limits is prohibited. See official references: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview?view=li-lts-2026-04 ; https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions
- Do not assume that a public Job Posting API provides inbound job-search access. The documented API is for job submission/publishing.
- No public evidence establishes that JobBeeper is exempt from LinkedIn rate limits or that it uses an undisclosed bypass.

### INFERRED — conceptual product architecture only
- Most plausible high-level flow: independent source adapters → collection/scheduling → normalization and provenance → deduplication/entity resolution → central job store/index → profile matching → private subscriber notifications → delayed public catalogue.
- Source-specific collectors likely need independent schedules, rate budgets, retry/backoff and health state. This is a sensible architectural pattern for a multi-source job product, not a verified JobBeeper internal design.
- The speed of the public experience is plausibly due to pre-collected job records, pre-rendered/cached HTML, and client-side filtering. This is distinct from the speed and access method of upstream LinkedIn collection.
- The large career-page count does not establish that every page is fetched every minute or at the same frequency. The product itself says detection times vary by source.

### UNKNOWN / not established
- JobBeeper's actual LinkedIn job acquisition method: authorized/private access, third-party licensed feed, public-page access, employer ATS mirrors, or a combination.
- Whether JobBeeper has any direct LinkedIn partnership or approved API arrangement.
- Its workers, queues, scheduler, polling cadence, account/API topology, request budgets, database/index, retry policy and uptime/latency SLOs.
- Whether any source is polled continuously; how it discovers and prioritizes the 89k+ advertised pages; how it detects changes efficiently.
- Whether a given LinkedIn-origin-labeled listing is uniquely obtained from LinkedIn or independently seen at another source.
- Whether the advertised detection metrics are measured from publication timestamps accurately across all providers.

### Product design decision
- Do not attempt to reproduce or circumvent LinkedIn anti-abuse systems. No account rotation, proxy rotation, CAPTCHA bypass, login-wall bypass, or unauthorized scraping.
- Build a resilient multi-source architecture: independently scheduled source adapters with allowed access modes, source-specific concurrency and request budgets, conditional/incremental polling where supported, jitter, Retry-After-aware backoff, idempotent ingest, canonical job records, source provenance and cross-source deduplication.
- Prefer public/official ATS endpoints and employer career pages; evaluate licensed data feeds or formal partner access for sources that need them. Treat LinkedIn as optional and isolated so LinkedIn unavailability cannot stop other collection.
- Keep private matching/alerts and public delayed catalogue as distinct delivery layers; don't copy the exact 6-hour delay as a requirement without validating our product needs.
- No Job Radar application code/config, Oracle runtime, SQLite database, collector behavior, Telegram notifications, or deployment was changed by this research update.


## Follow-through — 2026-11-05 — Ashby observability coverage

- **Goal:** continue the Job Radar V2 development path after the public JobBeeper evidence review: reliable multi-source discovery, canonical normalization/deduplication, explainable matching, and safe dashboard/Telegram delivery.
- **Evidence reviewed:** latest `README.md`, `v2/README.md`, `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `docs/JOBBEEPER_REFERENCE.md`, and `docs/LLM_PROVIDER_ROUTER.md` on `v2-live-radar`; inspected current `v2/radar.py`, `v2/test_radar.py`, dev Compose/config, and LLM router/extractor integration. Latest documented reverse-engineering result already confirms Cognizant search hides 199 of 200 preloaded Backend cards; stop open-ended reverse engineering and proceed with our product.
- **Repo-only architecture findings:** five registered collectors exist: LinkedIn, Naukri relay, Instahyre, Greenhouse, and Ashby. The scheduler uses per-source configured intervals, a 60-second floor and a 180-second LinkedIn floor; it prevents overlapping runs of the same source. The current development config enables only Naukri, with notifications disabled and LinkedIn/Instahyre/Greenhouse/Ashby off. Greenhouse and Ashby use explicit public-board allowlists and isolate per-board failures. The app uses FastAPI, SQLite, canonical opportunities, persisted evaluations/notification ledger, and a shared Telegram delivery path. This is a code/config read, not a live runtime audit.
- **Diagnosis:** `COLLECTORS` already registered Ashby, but `source_status()` and `latency_summary()` used hard-coded four-source lists that omitted it. Consequently the Ashby collector could run and persist `source_runs`/job latency while the source-status and latency-summary APIs silently omitted its telemetry. Confidence: high; directly visible in current branch code.
- **Code change:** `v2/radar.py` now derives `SOURCE_NAMES` from `COLLECTORS`; source status iterates that registry and the latency query uses parameterized placeholders for the same complete source list. Ashby is therefore included without a second manually maintained list.
- **Regression coverage:** `v2/test_radar.py` adds a source-status test for Ashby enablement/latest run/counts and a latency-summary test proving Ashby samples are included. Existing collector behavior and source enablement were not changed.
- **Commits:** `6f6c62dba78538ecefd94aa1242487a80b80c8a2` — observability fix; `4f73e73b0e7fcc6a4ec103bf8ee846c3324dc46d` — regression tests. Both were committed directly to `v2-live-radar`, consistent with the repository's documented workflow. No PR was created.
- **CI/tests:** the repository CI workflow runs syntax checks, focused router/extractor tests, and full V2 unittest discovery. GitHub's combined commit status returned no status entries for the test commit, and the commit-workflow lookup returned no PR-triggered runs. No local checkout/VM execution is available in this session; tests are added but are **not claimed to have run or passed**. Recheck Actions/commit status or run the documented commands in the dev checkout before deployment.
- **Deployment/runtime:** no VM pull, Docker operation, container restart, database/volume/config mutation, live provider call, Telegram send, or production change occurred. The Oracle runtime and its exact commit/source state remain unverified. Preserve VM-local `v2/config.json`, `.venv/`, `.env`, and `job-radar-dev_radar-dev-data`; do not reset/clean or recreate volumes.
- **Deliberately not changed:** no collector, scheduler cadence, LinkedIn behavior, source enablement, matcher/router flags, notifications, database schema, or production configuration. Reverse engineering is considered complete enough for the current product decision; do not resume broad private-internals probing.
- **Remaining risks:** runtime state still needs the read-only VM audit. The scheduler currently has fixed interval scheduling without the planned jitter/global per-host budgets; source freshness/coverage observability can be improved further. LinkedIn's documented Job Posting API is a restricted posting/partner API, not a general public job-search API; keep LinkedIn isolated and do not implement scraping/login/rate-limit circumvention. Public JobBeeper evidence does not reveal its private acquisition mechanism.
- **Exact next action:** on the development VM, first perform a read-only checkout comparison before pulling or rebuilding. From `/home/ubuntu/job-beeper-dev`, run:
  ```bash
  git status --short
  git branch --show-current
  git rev-parse HEAD
  git fetch origin v2-live-radar
  git rev-list --left-right --count HEAD...origin/v2-live-radar
  ```
  Return the output. Do not pull if the tree has local changes or is not simply behind; preserve the files/volume above. Once the fast-forward is confirmed safe, run `./.venv/bin/python -m py_compile v2/radar.py v2/test_radar.py`, `./.venv/bin/python -m unittest v2.test_radar.SourceStatusPersistenceTests v2.test_radar.SourceLatencySummaryTests -v`, then the full documented suite `./.venv/bin/python -m unittest discover -s v2 -p 'test_*.py' -v`. Do not rebuild or deploy until those results are reviewed.
- **Continuation prompt:** “Continue Job Radar V2 on `v2-live-radar`. Read both handovers and the reference docs first. Cognizant search confirmed browser-local filtering over 200 preloaded Backend cards; stop open-ended JobBeeper reverse engineering. A repo-only audit found five collectors and an observability omission for Ashby; commits `6f6c62d` and `4f73e73` fix source-status/latency coverage and add tests. CI and VM tests are not yet verified. First compare the dev checkout with origin using the exact read-only commands in the latest handover; preserve local config, .venv, .env and the named volume. Then run targeted and full tests before considering any dev rebuild. Keep notifications off and production untouched.”
- **Cross-reference:** compact status is in `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`; product/architecture guardrails are in `docs/JOBBEEPER_REFERENCE.md`; router rollout constraints remain in `docs/LLM_PROVIDER_ROUTER.md`.


## Latest user prompt follow-through — 2026-11-06 — deployment checkout and volume identity clarified

### Goal and evidence
- Goal remains reliable, fresh multi-source discovery → normalization/canonical deduplication → consistent matching/notification decisions → dashboard and Telegram delivery. This turn was an evidence-only deployment-safety investigation; no application code/config was changed.
- Development checkout `/home/ubuntu/job-beeper-dev`: branch `v2-live-radar`, HEAD `7ebc38b321847e74895557551478c3ff11bd4a`. User reported the four focused Ashby observability tests passed, then the full suite passed: **136 tests in 19.323s, OK**. `py_compile` also completed before the suite. These tests ran against the checkout, not the running container.
- Development checkout still has local state that must be preserved: modified `v2/config.json`; untracked `.env.save`, `.venv/`, and `v2/config.json.backup.20261105-183321`. Do not stage, overwrite, reset, clean, or delete these.
- Runtime API on port 8000 returned `status=ok`, version 2.0.0, DB `/data/jobs.db`; health showed LinkedIn and Naukri enabled, neither running at the instant sampled, no reported errors; Instahyre and Greenhouse disabled. `/api/source-status` listed LinkedIn, Naukri, Instahyre and Greenhouse, but **not Ashby**. This is consistent with the old runtime image, not proof of an Ashby collector failure in the new source.
- Runtime daily summary for 2026-11-06 (Asia/Kolkata): 5 jobs discovered, 0 matched, 0 alertable, 0 alerts sent. Last-hour latency: LinkedIn 19 samples, p50 2,520s (42m), p90 14,400s (4h), max 18,000s (5h), 4/19 under 300s; Naukri 0 usable samples. Treat these as one point-in-time runtime snapshot, not a stable SLO.
- Docker access without privilege failed with permission denied. With `sudo`, read-only inspection succeeded. Container `v2-radar-1` uses image `v2-radar`, image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, created 2026-10-12T03:44:43Z, and was Up about three weeks. Its Compose project label is `v2`; Compose config path label is `/home/ubuntu/job-beeper/v2/docker-compose.yml`.
- Actual mount is Docker named volume `v2_radar-data` at `/data`, host path `/var/lib/docker/volumes/v2_radar-data/_data`. This is the existing runtime database/config volume. Preserve it; never use `down -v`, volume prune/remove, or a different Compose project for this service.
- Original deployment checkout `/home/ubuntu/job-beeper`: branch `v2-live-radar`, HEAD `61d8271` (`Document free-first LinkedIn strategy and release cleanup`). Its Compose file resolves service `radar`. User's `git status --short` printed no entries, but explicitly re-check before any change rather than assuming it is clean.
- Critical path distinction: `/home/ubuntu/job-beeper-dev` is the tested, updated checkout; `/home/ubuntu/job-beeper` is the checkout path recorded in the currently running container's Compose labels. Do not run Compose from the dev directory for the port-8000 service. Doing so may create another project/volume. Do not pull/rebuild the original checkout until its role (production/live deployment versus a development target) and commit relationship are explicitly established.
- A YAML fragment (`volumes: - radar-data:/data`) was mistakenly pasted at the shell prompt and produced `command not found`; YAML belongs in a Compose file, not executed as shell commands. No harm to the repository or service was evidenced.

### Diagnosis and confidence
- High confidence: port-8000 container is an old image created on 12 Oct and is not running the just-tested **6 Nov 2026** checkout source at `7ebc38b`. The missing Ashby API row is consistent with this old image. No image rebuild/recreate has occurred.
- High confidence: current persistent runtime volume identity is `v2_radar-data` mounted at `/data`.
- Not established: whether the original checkout at `61d8271` is production, staging, or a separate intended dev target; whether it has uncommitted changes (the status command emitted no lines but must be rechecked); whether its Git history can fast-forward to the tested commit; whether the image can be safely recreated under the intended release policy.
- CI for `7ebc38b` remains unverified. User-run local tests are the evidence above.

### What changed / what did not
- No source/config edits, database writes, Docker builds, container restarts, Compose up/down, source enablement, notification sends, provider requests, or production changes.
- No Git commit was created by this runtime investigation. The preceding Ashby code/test commits and handover updates remain as recorded above.

### Exact next action — do not deploy yet
1. Confirm with the user whether `/home/ubuntu/job-beeper` on port 8000 is the live/production service or the intended development service. Treat it as production/live until clarified.
2. Read-only, from `/home/ubuntu/job-beeper`, run:
   ```bash
   cd /home/ubuntu/job-beeper
   git status --short
   git branch --show-current
   git rev-parse HEAD
   git remote -v
   git fetch origin v2-live-radar
   git rev-list --left-right --count HEAD...origin/v2-live-radar
   ```
   Do not pull, checkout, build, or recreate the service as part of this inspection. Do not print `.env`, `/data/config_token`, tokens, or private feed credentials.
3. Compare the original checkout history to `7ebc38b321847e74895557551478c3ff11bd4a`. If the original checkout is the live/production service, prepare a separately reviewed backup/rollback plan and obtain explicit deployment approval before touching it. If a dedicated dev service is desired, use its own Compose project name, loopback-only port and separate volume; never reuse `v2_radar-data` for a second instance.
4. Before any future recreate, verify Compose resolves the intended project and exact existing volume. Preserve `v2_radar-data`, runtime `/data/config.json`, generated `/data/config_token`, local `v2/config.json`, `.env.save`, and `.venv/`.

### Continuation prompt
“Read `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md` first. Latest evidence dated 2026-11-06: dev checkout `/home/ubuntu/job-beeper-dev` is at `7ebc38b`; 136 V2 tests pass. It has local modified `v2/config.json` and untracked `.env.save`, `.venv/`, config backup; preserve them. Port 8000 container is old (created 2026-10-12), Compose project `v2`, Compose file path `/home/ubuntu/job-beeper/v2/docker-compose.yml`, persistent named volume `v2_radar-data:/data`. Original checkout `/home/ubuntu/job-beeper` is branch `v2-live-radar` at `61d8271`; its role as production/live vs development is not yet clarified. Runtime API did not list Ashby; this is consistent with old image. No rebuild/restart/deploy occurred. First clarify service role, then do read-only status/fetch/commit comparison in original checkout. Do not pull or rebuild until release target and rollback plan are clear. Never remove/recreate volumes, send notifications, expose secrets, or modify production without explicit approval. Update both handovers after every prompt.”


## User clarification — 2026-11-06 — port 8000 checkout is production/live

- User explicitly confirmed that `/home/ubuntu/job-beeper` and its port-8000 service are the **production/live instance**. This resolves the previous ambiguity. Treat this checkout, container `v2-radar-1`, Compose project `v2`, and volume `v2_radar-data` as production assets.
- **Hard deployment boundary:** no pull, checkout, build, Compose recreate/restart, environment/config change, database operation, source enablement, or notification action against this instance without a separate explicit deployment authorization and reviewed backup/rollback plan. The user's confirmation identifies the environment; it is not approval to deploy.
- The tested checkout remains the separate development directory `/home/ubuntu/job-beeper-dev`, at `7ebc38b321847e74895557551478c3ff11bd4a`, with 136 reported passing tests. Its local modified config and untracked environment/venv files must remain untouched.
- **Next exact action is read-only only:** from `/home/ubuntu/job-beeper`, inspect `git status --short`, branch, HEAD, remotes; fetch `origin/v2-live-radar`; compare `HEAD...origin/v2-live-radar` using `git rev-list --left-right --count`. Fetch updates remote-tracking metadata only; do not pull. Do not print secrets or `.env`.
- The purpose of this comparison is to understand production checkout drift and prepare a safe, reviewed release plan. It must not change the running production container or its `v2_radar-data` volume.
- No production code, config, DB, container, image, volume, or notifications were changed in this turn.
- **Continuation prompt:** “User confirmed `/home/ubuntu/job-beeper` on port 8000 is production/live. Do not deploy or mutate it. Read all three Job Radar docs. The tested dev checkout is `/home/ubuntu/job-beeper-dev` at `7ebc38b`, 136 tests pass. Production container `v2-radar-1` uses Compose project `v2`, compose file under `/home/ubuntu/job-beeper`, and persistent `v2_radar-data:/data`. First perform read-only git status/branch/HEAD/remotes/fetch/commit comparison in production checkout. Keep all production assets intact; ask for separate deployment approval only after a reviewed backup/rollback plan.”

## Production release-drift audit — 2026-11-06 — 611 commits behind origin

- User supplied read-only command output from `/home/ubuntu/job-beeper`: `git status --short` was empty; branch `v2-live-radar`; HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34` (`Document free-first LinkedIn strategy and release cleanup`); remote `origin https://github.com/AvinashBhalla/job-beeper.git`.
- `git fetch origin v2-live-radar` completed and advanced the remote-tracking ref from `232aeef` to `f4f61b8`. `git rev-list --left-right --count HEAD...origin/v2-live-radar` returned `0 611`: production has zero unique commits and is 611 commits behind the fetched branch.
- Independent GitHub comparison (base production HEAD, head `f4f61b8d55d6a52c05e1dd9d98510ccea12ad77a`) reports status `ahead`, `ahead_by=611`, `behind_by=0`, `total_commits=611`; merge base equals production HEAD. This confirms a straight-line ancestry relationship, not that fast-forwarding is a safe release.
- Compare reports net changes across 22 paths: CI workflow, README/dashboard, three docs, new LLM/provider and reverse-engineering docs, V2 README/config/dev Compose, modified `v2/config.json` (+15/-3), `v2/radar.py` (+313/-13), `v2/test_radar.py` (+528/-2), and new Gemini diagnostic/extractor/router plus tests and Greenhouse canary plus tests. These are aggregate compare stats, not review of every intermediate commit.
- Notable release risk: `v2/config.json` changed. Do not assume branch config should replace production configuration. Inspect its semantics and preserve live `/data` config/volume.
- Diagnosis: high confidence production checkout is a clean ancestor of the remote branch and has 611 commits of release drift. This is not a reviewed production release; commit history and critical diffs, intended production config, and CI/test evidence still require review.
- Only Git fetch updated remote-tracking metadata. No working-tree change, pull, merge, checkout, build, Compose action, restart, config/env/DB/volume mutation, source enablement, provider request, or Telegram send occurred. Production container `v2-radar-1` and volume `v2_radar-data:/data` remain untouched.
- Release boundary: identifying port 8000 as production is not deployment authorization. Do not pull/fast-forward, cherry-pick, build, recreate, restart, or alter production until a commit/file-level release review, backup/rollback plan, and separate explicit deployment approval are in place.
- Exact next action: read-only inspect the 611-commit range and critical diffs, beginning with ordered commit subjects and `v2/config.json`, `v2/radar.py`, production/dev Compose, CI workflow, source and notification configuration. Do not print secrets. Establish whether live volume config is authoritative and what release config must be retained. Then propose a bounded release candidate and backup/rollback checklist; do not deploy.
- Continuation prompt: “Read the three Job Radar docs first. Production is `/home/ubuntu/job-beeper`, port 8000, clean branch `v2-live-radar`, HEAD `61d8271480eaf48b0a6442b62b1b0bb9a032df34`; after read-only fetch it is 0 ahead / 611 behind `origin/v2-live-radar` at `f4f61b8d55d6a52c05e1dd9d98510ccea12ad77a`. GitHub compare confirms 611 commits and 22 changed paths, notably config, radar, tests, CI, Compose, Gemini/router/Greenhouse. Only fetch metadata changed. Do not pull or deploy. Review commit subjects and critical diffs, especially config and source/notification flags; prepare release and backup/rollback plan, then wait for explicit deployment approval. Preserve `v2-radar-1` and `v2_radar-data:/data`; no notifications.”

## Release diff review — 2026-11-06 — configuration, source gates, AI gates, and review finding

- User fetched the remote again; `origin/v2-live-radar` advanced from `f4f61b8` to `a21e2f2`. Production HEAD remains `61d8271`; `git rev-list --count HEAD..origin/v2-live-radar` is now 613. User-provided log shows first commits from 2026-10-12 and newest docs-only commits from 2026-11-06. `git diff --stat`: 22 paths, 9,694 insertions, 120 deletions. The large total is dominated by accumulated handover docs and tests; do not treat it as 9,694 lines of production runtime changes.
- User's critical numstat: `.github/workflows/v2-ci.yml` +5/-2; `v2/config.json` +15/-3; `v2/radar.py` +313/-13; `v2/docker-compose.dev.yml` +44; `v2/docker-compose.yml` unchanged. Independently fetched both Compose versions: production Compose is unchanged, retains service `radar`, host port 8000, `/data` named volume, and Telegram env mapping. Dev Compose is a separate project/volume, binds only `127.0.0.1:8001`, mounts `config.dev.json`, blanks Telegram credentials and has optional AI env gates.
- Config review: production repository default moves from config version 10 to 11. It adds Ashby poll interval 1,800s, two board definitions (OpenAI and PostHog), and `source_enabled.ashby=false`. Existing default LinkedIn/Naukri remain true; Instahyre/Greenhouse remain false; repository default `notifications_enabled=true`. Dev config is deliberately different: notifications false, Naukri only enabled, LinkedIn/Instahyre/Greenhouse/Ashby disabled. Never copy `v2/config.json` over the live `/data/config.json` or assume repository defaults are the effective live config.
- Migration review: `_merge_config` explicitly forces Ashby false for configs below version 11 after persisted source flags are merged, preventing a new source from being enabled by migration. Existing persisted source flags and notification setting are otherwise retained by merge. Production's previously observed runtime config was version 10, so a future app startup with version 11 would write the migrated runtime config and add Ashby disabled. This is a production DB-volume config write and must be part of any reviewed deployment/rollback plan, not performed now.
- AI feature gates: `gemini_extractor.py` requires `GEMINI_EXTRACTION_ENABLED`; cached hard-matcher bridge requires `GEMINI_MATCHER_ENABLED`; routed providers require `LLM_ROUTER_ENABLED`, and router-based matching additionally requires `LLM_ROUTER_MATCHER_ENABLED`. These gates default false in code. Production `v2/docker-compose.yml` does not pass these variables or provider credentials; dev Compose passes them as explicit optional variables defaulting false. Therefore the reviewed Compose definition does not opt production into Gemini/LLM extraction or matcher. Still verify actual live container environment without printing values before any deployment.
- Other reviewed runtime changes: LinkedIn structured `Experience:` label extraction is added; Gemini extraction is bounded/cached, validates evidence and is separate from matcher inputs unless the matcher gate is explicitly enabled; Greenhouse freshness handling keeps unknown publication timestamps unknown rather than treating first-seen time as publish time; Ashby collector reads an explicit public-board allowlist, validates records, and is opt-in. `SOURCE_NAMES = tuple(COLLECTORS)` makes source status/latency include Ashby.
- **Review finding / release blocker:** `v2/radar.py`'s `/api/dedupe-candidates` query still hard-codes `source IN ('linkedin', 'naukri', 'instahyre', 'greenhouse')` and omits Ashby, despite Ashby now being a registered collector. Ashby observations will not appear in that endpoint's candidate set. This does not disable ingestion or canonical dedupe pipeline generally, but makes this diagnostic endpoint incomplete. Add Ashby to the source filter (prefer registry-driven parameterized placeholders) and a regression test before calling the Ashby observability slice complete.
- CI evidence: updated workflow compiles Greenhouse canary/tests, runs focused LLM-router/Gemini-extractor tests and full V2 unittest discovery. GitHub combined status lookup returned no status rows for the reviewed Ashby test commit; lookup for the previously recorded dev SHA returned Ref not found. Do not claim GitHub CI passed. User-reported local dev suite remains 136 tests passing plus `py_compile`; this is checkout test evidence, not runtime proof.
- No production action occurred: user ran only Git fetch and diff/log inspection; our GitHub review was read-only. No pull, checkout, build, Compose restart, config/DB/volume write, source enablement, provider request or Telegram send. Production `v2-radar-1` and `v2_radar-data:/data` remain protected.
- **Exact next action:** first inspect current live runtime config via read-only `GET /api/config`, projecting only `config_version`, `notifications_enabled`, `source_enabled`, `poll_seconds`, `match_threshold`, `candidate_experience_years`, `max_experience_years`, and `require_explicit_experience_for_alerts` (do not print config token or secrets). Also check only boolean presence of `GEMINI_EXTRACTION_ENABLED`, `GEMINI_MATCHER_ENABLED`, `LLM_ROUTER_ENABLED`, and `LLM_ROUTER_MATCHER_ENABLED` in the live container; never print values or credentials. Separately prepare a small code/test fix for Ashby omission in `/api/dedupe-candidates`. Do not deploy.
- **Continuation prompt:** “Read all three Job Radar docs. Production is `/home/ubuntu/job-beeper`, port 8000, HEAD `61d8271`, clean, 613 commits behind `origin/v2-live-radar` at `a21e2f2`; do not pull/deploy. Review found v2 config version 11 adds Ashby boards and 1,800s cadence but migrates Ashby disabled; current source flags/notifications should be preserved. Production Compose is unchanged and does not pass AI env gates; dev Compose is loopback-only port 8001, separate volume, notifications off. Gemini extraction/matcher/router are feature-gated false by default. Greenhouse timestamp freshness guard and Ashby public allowlist are present. Bug: `/api/dedupe-candidates` hard-coded source filter omits Ashby; fix + regression test before release. GitHub CI status not confirmed; dev local tests 136 passed. Next read only: inspect live `/api/config` projected safe fields and AI-gate boolean presence, then patch/test endpoint in dev/branch. Preserve production container/volume; no notifications.”

## Live config verification and Ashby dedupe follow-up — 2026-11-06

- User supplied a read-only projection of production `GET /api/config`: `config_version=10`; notifications enabled; LinkedIn/Naukri enabled; Instahyre/Greenhouse disabled; poll intervals LinkedIn 180s, Naukri 300s, Instahyre 600s, Greenhouse 900s; match threshold 55; candidate experience 2 years; max job experience 3 years; `require_explicit_experience_for_alerts=false`. Ashby is absent from this v10 runtime config.
- User supplied live container feature-gate booleans: `GEMINI_EXTRACTION_ENABLED=false`, `GEMINI_MATCHER_ENABLED=false`, `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`. This confirms those gates are not enabled in the running container. Do not change alert policy or source flags as part of release work.
- Consequence: v11 migration is expected to preserve the live LinkedIn/Naukri settings and notifications flag while adding Ashby disabled. The current production alert policy does not require explicit experience; this is existing user configuration and is not being changed.
- Follow-up implementation: replace the hard-coded source list in `/api/dedupe-candidates` with parameterized placeholders derived from `SOURCE_NAMES`; add regression coverage proving an Ashby + LinkedIn same-identity pair appears in dedupe candidates. This is a code/test-only change on the development branch; it does not alter live production.
- Exact next action: validate the new focused test and full V2 test suite in `/home/ubuntu/job-beeper-dev`, then report the test output. Do not pull/build/restart production or mutate `/data`. CI remains unverified.

## User prompt follow-through — 2026-11-06 — isolated worktree uses python3

- User fetched origin/v2-live-radar and created the isolated detached worktree /tmp/job-beeper-ashby-dedupe-test at commit c93f041 (the latest fetched branch tip at that moment). This worktree does not overwrite the existing /home/ubuntu/job-beeper-dev checkout or its local config/env/venv files.
- The three attempted commands using python did not execute because this VM has no python executable; shell suggested python3. No focused tests, full-suite tests, or compilation result is available from this attempt.
- Next exact action, from /tmp/job-beeper-ashby-dedupe-test:

  python3 -m unittest v2.test_radar.DedupeCandidatesSourceCoverageTests -v
  python3 -m unittest discover -s v2 -p 'test_*.py' -v
  python3 -m py_compile v2/radar.py v2/test_radar.py

- Record actual output before judging the Ashby dedupe registry fix. If any command fails, diagnose from its output; do not claim tests passed. Do not remove the worktree without checking whether it is still in use.
- The patch remains repository-only. Production /home/ubuntu/job-beeper, port 8000, container v2-radar-1, and volume v2_radar-data:/data remain untouched; no deployment approval was given. No config, DB, source toggle, or notification state changed.
- Overarching goal remains reliable multi-source discovery → normalization/deduplication → consistent explainable matching → dashboard and Telegram delivery. The Ashby endpoint fix only closes registry coverage in dedupe candidate discovery; it does not activate Ashby or prove collection/runtime health.
- Continuation: run the three python3 commands above in the isolated worktree and return complete output. Then review failures or confirm test evidence, check CI, and update both handover documents. No production mutation or notification send.
## User prompt follow-through — 2026-11-06 — test import blocked by missing dependency

- User ran the focused Ashby regression test, full V2 unittest discovery, and py_compile from /tmp/job-beeper-ashby-dedupe-test at c93f041 using python3.
- Focused test did not load: importing v2.radar failed with ModuleNotFoundError: No module named 'bs4'. Full discovery loaded and passed 17 LLM-router tests, but four test modules failed to import (Radar, Gemini experience diagnostic, Gemini extractor, Greenhouse canary) for the same missing bs4 dependency. Therefore the full suite is BLOCKED/INCOMPLETE, not a code-test failure and not a pass.
- py_compile was the final command and emitted no error output; this is consistent with syntax compilation success, but the user did not separately show an exit code. Compilation does not validate imports or behavior.
- Repository-declared runtime dependencies are in v2/requirements.txt: FastAPI, Uvicorn, requests, beautifulsoup4, tzdata. The missing import maps to the declared beautifulsoup4 package.
- Next exact action, still inside /tmp/job-beeper-ashby-dedupe-test: create an isolated virtual environment and install the V2 requirements, without changing system Python or production:

  python3 -m venv .venv
  .venv/bin/python -m pip install -r v2/requirements.txt
  .venv/bin/python -m unittest v2.test_radar.DedupeCandidatesSourceCoverageTests -v
  .venv/bin/python -m unittest discover -s v2 -p 'test_*.py' -v
  .venv/bin/python -m py_compile v2/radar.py v2/test_radar.py

- If venv creation fails because python3-venv is unavailable, stop and return that error; do not install OS packages or modify the VM globally without a separate decision. If dependency installation fails, return the complete pip error. Preserve the temporary worktree until test results are reviewed.
- No application code/config change, test result validating the Ashby fix, CI confirmation, production deployment, DB/volume mutation, source activation, or Telegram send occurred. Production /home/ubuntu/job-beeper, port 8000, v2-radar-1, and v2_radar-data:/data remain untouched.
- Product goal remains reliable multi-source discovery → normalization/deduplication → explainable matching → dashboard and Telegram delivery. This is a test-environment setup issue; Ashby remains opt-in and this endpoint fix remains repository-only.
- Continuation: set up only the isolated worktree venv from v2/requirements.txt, rerun focused and full tests, report complete output. Then diagnose actual test failures, check CI, and keep production approval-gated.
## User prompt follow-through — 2026-11-06 — V2 suite passes with Ashby dedupe regression

- User supplied the completed unittest output from the isolated worktree /tmp/job-beeper-ashby-dedupe-test, code checkout at c93f041. Full V2 discovery completed: 137 tests in 18.998 seconds, result OK, zero failures/errors.
- Crucial regression test test_dedupe_candidates_includes_ashby_from_collector_registry passed in the full suite. This validates the registry-derived, parameterized source filter in /api/dedupe-candidates for the Ashby + LinkedIn candidate pair.
- Ashby collector tests also passed, including opt-in migration behavior and handling of invalid/missing published_at. Source status and latency-summary Ashby coverage tests passed. Gemini extractor/diagnostic, Greenhouse canary, LLM-router and broader matcher tests in the displayed run also passed.
- The user-supplied output contains the full-suite run only. It does not show a separate focused-only test invocation or the py_compile command's output/exit status; do not claim those separate commands completed based solely on this attachment. Full suite did include and pass the Ashby regression test.
- CI remains unverified: GitHub combined commit status returned no status rows for c93f041 and the commit workflow-runs lookup returned no PR-triggered runs. Local VM test pass is not CI evidence.
- No application code changed in this turn. No deployment, production pull/build/restart, config/DB/volume mutation, source activation, external provider call, or Telegram send occurred. Production /home/ubuntu/job-beeper, port 8000, container v2-radar-1, and volume v2_radar-data:/data remain untouched.
- The missing-bs4 import blocker from the prior attempt is resolved in the isolated test environment; the full suite now ran. Do not infer which installation method was used unless the user supplies that command.
- Goal remains reliable multi-source discovery → normalization/deduplication → explainable matching → dashboard and Telegram delivery. This test closes the code-level Ashby dedupe endpoint coverage check, but does not enable Ashby or establish collector/runtime health.
- Next exact action: confirm the isolated worktree's current HEAD and status, then inspect the code/test diff and CI workflow behavior if needed. Preserve all production gates. Before any release, prepare backup/rollback and isolated runtime validation; separate explicit production deployment approval remains mandatory.
## User prompt follow-through — 2026-11-06 — Ashby dedupe patch review and worktree verification pending

- Reviewed the two code commits directly: 0a09162d06fcd2ca6880bfbc9eb012132c0b2582 changes /api/dedupe-candidates to build parameter placeholders from SOURCE_NAMES and bind the registry tuple as SQLite parameters; 6dc6ac8c5e96938c7a39bf10b3fb3ba4359d5cf4 adds a temporary-SQLite regression test with matching LinkedIn and Ashby rows.
- Read the current v2/radar.py source around COLLECTORS and dedupe_candidates: SOURCE_NAMES = tuple(COLLECTORS), and Ashby is registered in COLLECTORS. The parameterized query is consistent with the existing registry-driven latency-summary query. No source values are interpolated into SQL; only placeholder count is generated, and source values are bound.
- Read the regression test: it patches radar.DB_PATH to a TemporaryDirectory DB, creates a minimal jobs table, inserts LinkedIn/Ashby same-company/title rows, asserts jobs_considered=2 and asserts a cross-source pair. User's full suite output confirms this test passed.
- Test class is currently placed after the module's if __name__ == '__main__': unittest.main() guard. Discovery/import-based test execution (the reported full suite) still discovers and runs it, but direct execution of test_radar.py would call unittest.main before defining this class. This is a test-file organization nit, not a failure in the tested discovery path; consider moving the class above the main guard in a later tidy-up only if useful.
- The user-created detached worktree was last confirmed at c93f041. Current local HEAD and uncommitted status cannot be read through GitHub; no VM shell access is available to the assistant. Exact next action for user, from /tmp/job-beeper-ashby-dedupe-test:

  git status --short
  git rev-parse HEAD
  git branch --show-current
  git diff --stat
  git diff -- v2/radar.py v2/test_radar.py

- Expected branch output is empty because the worktree was created detached. Confirm HEAD remains c93f0414e8f99540d6004f012e8cb286e32bf1f6 and that the code/test diff is clean; if status/diff shows local changes, stop and inspect rather than reset/clean. The branch has since received documentation-only follow-through commits; do not assume the old detached worktree includes those docs updates.
- User-provided full V2 suite result: 137 tests in 18.998s, OK. GitHub CI lookup for c93f041 returned no status rows and no PR-triggered workflow runs; CI is unverified. No separate focused-only output or py_compile exit code was supplied in the attachment.
- No application code was changed in this review. No production pull/build/restart, config/DB/volume mutation, source activation, provider call or Telegram send. Production /home/ubuntu/job-beeper, port 8000, v2-radar-1 and v2_radar-data:/data remain untouched.
- Goal remains reliable multi-source discovery → normalization/deduplication → explainable matching → dashboard and Telegram delivery. The endpoint code fix and regression are validated by the local full suite, but no runtime/deployment claim follows. Keep production approval-gated.
- Continuation: verify the isolated worktree status/HEAD/diff with the exact commands above. Then review CI availability and prepare an isolated runtime/release plan only after the code state is clean. Do not deploy or send notifications.

## 2026-11-06 follow-through — clean code diff
- User verified detached worktree HEAD c93f0414e8f99540d6004f012e8cb286e32bf1f6; no branch name is expected.
- `git status --short`: modified `v2/config.json`, untracked `.venv/`. `git diff --stat`: only config, 2 insertions/2 deletions. `git diff -- v2/radar.py v2/test_radar.py` was empty. Ashby fix and regression-test files are clean; preserve config and venv, do not reset/clean/stage/commit them.
- Full V2 suite previously passed: 137 tests in 18.998s, including the Ashby dedupe regression. CI remains unverified. No production change/deployment, source activation, DB/volume mutation, provider call, or Telegram send.
- Next: retain the isolated worktree and prepare a non-mutating isolated runtime/release checklist. Production deployment still requires separate explicit approval and backup/rollback review.


## 2026-11-06 follow-through — verify isolated development Docker service
- User asked to verify whether the isolated development Docker service on port 8001 is still running. The assistant cannot inspect the VM directly; requested read-only VM checks: `sudo docker ps -a --filter 'publish=8001' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'`, `sudo docker compose ls`, `sudo ss -ltnp | grep ':8001' || ...`, and from `/home/ubuntu/job-beeper-dev`, `git status --short` plus `git rev-parse --short HEAD`.
- Await user-supplied command output before declaring service status. Do not start/stop/rebuild containers or change configuration. Keep production port 8000 and production checkout/container/volume untouched.


## 2026-11-06 follow-through — isolated development service verified running
- User supplied read-only VM output: container `job-radar-dev`, image `job-radar-dev-radar`, status `Up 2 weeks`, binding `127.0.0.1:8001->8000/tcp`. Compose project `job-radar-dev` is running from `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`; production project `v2` is separate and uses `/home/ubuntu/job-beeper/v2/docker-compose.yml`.
- `ss` confirms only `127.0.0.1:8001` listener via docker-proxy. Dev API is loopback-bound, not directly exposed on public interfaces. Service is running, but its two-week-old container is not proof it reflects current checkout code; no health endpoint or code/container parity check was performed yet.
- Dev checkout `/home/ubuntu/job-beeper-dev` is at `7ebc38b`. Preserve local changes: modified `v2/config.json`; untracked `.env.save`, `.venv/`, and `v2/config.json.backup.20261105-183321`. Do not reset, clean, stage, overwrite, or delete these.
- No container start/stop/rebuild/restart, config/DB/volume mutation, production operation, source activation, or notification send occurred.
- Suggested next read-only check, if continuing: query `http://127.0.0.1:8001/health` and `/api/source-status` from the VM, then inspect dev container image/config metadata to determine runtime health and code/config parity. Do not change service state.


## 2026-11-06 follow-through — dev API health and source registry
- User supplied read-only `GET /health` from port 8001: status `ok`, version `2.0.0`, uptime `1,732,027` seconds, DB `/data/jobs.db`. Runtime health reports only Naukri; it is not running, last success `2026-11-05T19:18:27.101126+00:00`, jobs_seen 335, new_jobs 0, error null.
- `GET /api/source-status` reports only LinkedIn, Naukri, Instahyre and Greenhouse; LinkedIn/Instahyre/Greenhouse disabled, Naukri enabled. Ashby is absent from the response. This is evidence that the running dev API does not expose the expected current five-source registry; likely stale container/code, but confirm before concluding exact cause. Version `2.0.0` is not a commit identifier. Health `ok` does not establish Ashby readiness.
- Do not enable sources or rebuild/restart the dev service yet. Next read-only diagnostics: inspect `job-radar-dev` image ID, container creation timestamp, working directory and Compose labels; locate the application file inside the container and compare its SHA256 with `/home/ubuntu/job-beeper-dev/v2/radar.py`. Also record the current dev checkout HEAD/status without modifying anything. Preserve dev local files/config. Production remains untouched.


## 2026-11-06 follow-through — container application path identified
- User confirms dev Compose labels: project `job-radar-dev`, Compose file `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`. Inside the running container, working directory is `/app`; application file is `./v2/radar.py` and config is `./v2/config.json`.
- Dev checkout HEAD is `7ebc38b7c321847e74895557551478c3ff11bd4a`; host checkout `sha256sum v2/radar.py` is `9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55`.
- The provided output did not include container `Created`, `ImageID`, or `WorkingDir` inspect fields, and did not yet include a checksum from `/app/v2/radar.py`. Exact host/container code parity remains unverified. Runtime API source-status still omits Ashby, despite the inspected newer registry containing it.
- Next read-only check: `sudo docker exec job-radar-dev sha256sum /app/v2/radar.py`; compare directly with the host hash above. Also capture `sudo docker inspect job-radar-dev --format 'Created={{.Created}} ImageID={{.Image}} WorkingDir={{.Config.WorkingDir}}'`. No rebuild/restart or config/source changes. Preserve dev checkout local files; production stays untouched.


## 2026-11-06 follow-through — dev container code mismatch confirmed
- User supplied container file checksum: `/app/v2/radar.py` = `c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2`.
- Host dev checkout checksum from the prior turn: `/home/ubuntu/job-beeper-dev/v2/radar.py` = `9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55`. Hashes differ, so running `job-radar-dev` does not use the same `radar.py` bytes as the current development checkout. Container metadata: Created `2026-10-16T18:15:03.877936825Z`, image ID `sha256:c41b89e3ee05ba5abe3de2612b8d86d51322baa47ceeaaab2b53f98e3eedba92`, working directory `/app`.
- Correlates with dev API `/api/source-status` exposing only LinkedIn/Naukri/Instahyre/Greenhouse and omitting Ashby. Therefore port 8001 is HTTP-healthy but not yet validated as running the current Ashby-capable checkout. Exact image source commit/build provenance is not established by this evidence alone; do not assert which commit the image contains.
- Next safe step: read-only inspect Compose labels, image labels, image creation metadata and Git commit details for host checkout; optionally inspect container's source registry using grep. Do not rebuild/recreate/restart or modify config/DB/volume yet. Keep production port 8000 and its assets untouched. Preserve local dev config, `.env.save`, `.venv/`, and timestamped config backup.


## 2026-11-06 follow-through — nuance: Ashby code exists in dev container
- User supplied image inspect: image Created 2026-10-16T17:13:11.778204261Z; RepoDigests reports local image digest job-radar-dev-radar@sha256:c41b89e3ee05ba5abe3de2612b8d86d51322baa47ceeaaab2b53f98e3eedba92. Labels identify Compose project job-radar-dev, service radar, Compose version 5.6.0; no source revision/commit label is present.
- User grep from container /app/v2/radar.py shows Ashby config migration/validation, Ashby board normalization, ashby_collect(), public API endpoint https://api.ashbyhq.com/posting-api/job-board/{name}, and COLLECTORS registration entry ashby: ashby_collect (line 2710). Thus Ashby collector code IS present in the running container. Correct earlier overstatement: the /api/source-status omission does not mean Ashby collector is absent.
- Hash mismatch remains proven: container c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2 vs host checkout 9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55. Image created 2026-10-16; host checkout HEAD 7ebc38b7c321847e74895557551478c3ff11bd4a dated 2026-11-05. Therefore container file differs from checkout, but exact source commit of image is unknown.
- Outstanding inconsistency: dev /api/source-status returns only linkedin, naukri, instahyre, greenhouse while container COLLECTORS includes ashby. Likely endpoint builds its own hardcoded source list or returns legacy structure; inspect exact endpoint and any SOURCE_NAMES definition in both container and host checkout before concluding or rebuilding.
- Next read-only command: run grep -nE 'SOURCE_NAMES|source-status|source_status|COLLECTORS' against /app/v2/radar.py inside container and v2/radar.py in /home/ubuntu/job-beeper-dev separately, then inspect nearby code with sed. No rebuild/restart or config/DB/volume mutation. Preserve all dev local changes; production untouched.
## 2026-11-06 follow-through — correct interpretation of dev container Ashby code

- User compared grep output from running `job-radar-dev` at `/app/v2/radar.py` with host checkout `/home/ubuntu/job-beeper-dev/v2/radar.py`.
- Running container file contains Ashby config validation/migration (lines 155-171, 254-298), `ashby_collect()` (2614-2698), Ashby in `COLLECTORS` (2705), and scheduler iteration over `COLLECTORS` (2823, 2830). Thus the Ashby collector implementation is present in the container and registered with the scheduler. The earlier interpretation that Ashby code itself was absent was incorrect.
- Running container grep did not show `SOURCE_NAMES`; its `/api/source-status` route begins at line 2946. The host checkout at `7ebc38b` defines `SOURCE_NAMES = tuple(COLLECTORS)` at line 2712, uses `source_placeholders` and registry-driven source loops for latency/source-status at lines 2907, 2930 and 2976. This explains the four-source response: the container's source observability code is older and does not expose Ashby even though the collector is registered.
- The running container's `radar.py` hash is `c404ccff19da643f935b0f41c8ef44035f00b569fdc13ddcc0a093648b7520b2`; host checkout hash at `7ebc38b` is `9cb9d8f892748722138c07c3100cc0643608d5ef7a24d231863e8a7793c9ea55`. Container image created `2026-10-16T17:13:11.778204261Z`, image ID `sha256:c41b89e3ee05ba5abe3de2612b8d86d51322baa47ceeaaab2b53f98e3eedba92`; labels do not identify source commit. Code is not byte-identical to host, and observability improvements are missing in the container.
- Correct conclusion: dev container is HTTP healthy and has Ashby collector code registered, but its source-status/latency observability is stale relative to host checkout. The API omitting Ashby is not evidence that Ashby collector code is missing. Whether Ashby is enabled/configured in the container's effective dev config is not established by this grep; inspect via read-only `/api/config` projection before testing any collection. Ashby should remain disabled until a controlled test is planned.
- No rebuild/restart or config/DB/volume mutation occurred. Production port 8000 remains untouched; dev port 8001 remains loopback-bound. Preserve host local config/env/venv/backup files.
- Next read-only verification: on port 8001, inspect only `config_version`, `source_enabled`, `ashby_boards`, `notifications_enabled`, `poll_seconds` from `/api/config`; inspect the running file's source-status and dedupe query code around the endpoint with `sed -n '2940,3010p' /app/v2/radar.py`. Then decide whether a development-only rebuild is useful to align observability and dedupe code with the tested checkout. Never point a dev recreation at production volume `v2_radar-data`.


## Termalin direct SSH access verified — 2026-11-06 — host health snapshot

- User explicitly invoked Termalin and asked whether direct SSH commands are now possible. `hosts_list` returned a reachable host `job-radar` (Ubuntu 22.04), online, default execution user `ubuntu`, policy `full`. Termalin keyless connector is online. Direct SSH-equivalent shell commands were executed successfully via Termalin; no SSH key or inbound port access was needed.
- Monitoring `server_metrics` (only one sample in preceding 6h, timestamp 2026-11-05 19:33 UTC): 2 CPU cores; load1 0.19, load5 0.07, load15 0.04; memory 57.4% used; root disk 17.4% used; 3.2% inode use; uptime about 29 days; swap had about 507MB used in the monitor sample. `alerts_list` reported no open alerts.
- Live read-only SSH checks at 2026-11-05T19:33:49Z: `/` 45G size, 7.9G used, 38G free (18%); inode usage 4%; memory 956MiB total, 389MiB used, 429MiB available, swap 490MiB used / 2.0GiB total; load averages 0.30/0.12/0.06; 146 processes, 0 zombies; NTP OK. `systemctl --failed` empty. `sshd` on port 22, production Radar on `0.0.0.0:8000`, development Radar on `127.0.0.1:8001`.
- Both containers are up: `v2-radar-1` (production) and `job-radar-dev` (development). Both report `RestartCount=0`, `OOMKilled=false`; started 2026-10-12 and 2026-10-16 respectively. Container stats at sample: dev 31.83MiB RAM, 0.21% CPU; prod 102.1MiB RAM, 7.88% CPU. Compose projects/config paths are separate: `v2` at `/home/ubuntu/job-beeper/v2/docker-compose.yml`; `job-radar-dev` at `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`.
- Both `/health` endpoints returned `status=ok`, version 2.0.0, DB `/data/jobs.db`. Production at sample: LinkedIn/Naukri last successful runs Nov 5 19:33 and 19:30 UTC; LinkedIn reported 3 new jobs in run, Naukri 0. Dev at sample: Naukri enabled, last success 19:33 UTC, 0 new jobs. These are individual snapshots, not a full freshness/SLO analysis.
- `journalctl -p warning --since '24 hours ago'` showed repeated SSH `kex_exchange_identification: Connection closed by remote host` and one reset-by-peer. This is not evidence of successful authentication or compromise; likely incomplete/aborted connection attempts but correlate with auth logs / firewall / expected client IPs if they continue. Do not disable SSH or alter firewall without evidence.
- `last -x reboot` showed two boot records on Oct 7 (14:33 and 18:44) still marked running; may reflect one boot replacing another due to log format/clock or multiple wtmp entries. Not enough evidence to call repeated unexpected reboots; corroborate with `uptime`, `who -b`, and journal boot IDs if needed.
- Overall: host is online and responsive; disk/load/service/container health looks good. Main capacity caution: only ~956MiB RAM total; about 429MiB available and ~490MiB swap used. No current alert. Continue monitoring memory/swap during builds or two-service activity. Current metrics history in Termalin only had one sample in 6h, so trend confidence is limited.
- Direct Termalin access is available and verified. Use `hosts_list` first, heed owner note/policy, prefer metrics/alerts then read-only `ssh_exec`; long installs/builds/backups should use job_start. Production mutations still require explicit user approval and reviewed backup/rollback; do not conflate SSH access with deployment authorization.
- This check made no file/config/DB/volume changes, no service restart, no container operation, no update, no provider network call and no Telegram send.

## 2026-11-06 — Backup established locally; encrypted Termalin job awaiting owner confirmation

### Backup inventory and scope
- Read all current Job Radar docs before acting. Termalin host `job-radar` is online with full command policy as `ubuntu`; direct Termalin shell is available. No pre-existing backup jobs or archives existed.
- Confirmed production container `v2-radar-1` volume `v2_radar-data:/data`; dev container `job-radar-dev` volume `job-radar-dev_radar-dev-data:/data`. Dev also bind-mounts `/home/ubuntu/job-beeper-dev/v2/config.dev.json` to `/app/v2/config.json`.
- Runtime data sizes: production volume approx 65 MB, dev volume approx 32 MB. Jobs databases are active SQLite files; do not copy the live `jobs.db` file directly as a consistency strategy. Use Python sqlite3 `Connection.backup()` against a read-only source connection from inside each container.
- Built `/var/backups/job-radar-pre-release-20261106/` (mode 0700) containing consistent initial SQLite snapshots (`production-jobs.sqlite3`, `development-jobs.sqlite3`), copied runtime `config.json` and `config_token` for each volume (secrets were not displayed), and exact running container images as `running-images.tar`. Initial snapshot and both later snapshots passed `PRAGMA integrity_check`. Initial job row counts at final snapshot: production 19,846; development 7,158. Initial DB sizes: 68,014,080 and 33,169,408 bytes. Exact running image IDs exported: production `sha256:6300862b5d8071221343dc5c95006d73a90a22db42983aecf3b6e0215cc9fee3`; dev `sha256:c41b89e3ee05ba5abe3de2618b2d86d51322baa47ceeaaab2b53f98e3eedba92`. Tar size 61,245,440 bytes. `docker image load -i` parsed the tar successfully.
- Created `/var/backups/job-radar-daily/` containing separate production/dev SQLite snapshots. Added root-owned script `/usr/local/sbin/job-radar-sqlite-snapshot.sh`, systemd service `/etc/systemd/system/job-radar-sqlite-snapshot.service`, and enabled timer `/etc/systemd/system/job-radar-sqlite-snapshot.timer` scheduled daily at 02:45 UTC (persistent, up to 30s random delay). The service snapshots production then dev DB using SQLite online backup API, verifies integrity/count, copies to host and atomically replaces the snapshot files. It also refreshes the SHA256 manifest.
- Initial script authoring had two bugs that were caught before relying on the result: (1) an over-escaped Bash variable caused a literal `${filename}` target and both snapshots collided; (2) checksum manifest generation included its own temporary file and verification ran from the wrong current directory. Both were corrected. Final service execution: `Result=success`, `ExecMainStatus=0`; distinct production and dev files exist with correct sizes/counts and pass integrity. Manifest verification from `/var/backups` returned OK for all 9 artifacts. The stray literal-name file was removed. Do not repeat earlier failed method; use final script on host as source of truth.
- Snapshot staging currently occupies about 155 MB in the initial pre-release directory plus 100 MB in the daily directory, leaving about 37 GB free on root. Snapshot directories and secret copies are permission-restricted. SHA manifest at `/var/backups/job-radar-pre-release-20261106/SHA256SUMS` contains checksums for both database snapshots, runtime config/token copies and image tar; daily script refreshes it after each scheduled snapshot.

### Encrypted Termalin archive — not yet complete
- `backup_list` before setup reported no jobs and no archives. Created Termalin backup job draft `Job Radar production and dev daily backup`, ID `ae51ea55-d396-417e-8792-8ddfc1cd66c7`. Confirmation link: `https://termal.in/account#backup-draft=ae51ea55-d396-417e-8792-8ddfc1cd66c7`.
- Draft scope: `/home/ubuntu/job-beeper`, `/home/ubuntu/job-beeper-dev`, both volume `_data` directories, pre-release staging directory, daily SQLite snapshot directory, snapshot script, and its systemd service/timer. Excludes: `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `node_modules`, `jobs.db`, `jobs.db-wal`, `jobs.db-shm`. Thus it backs up repo/env/config content (encrypted by Termalin) and volume config/token, while consistent sqlite snapshots are archived as separate `.sqlite3` files.
- Draft schedule is daily at 03:00 UTC, keep last 7, Termalin storage. This is one hour? correction: 15 minutes after 02:45 UTC snapshot timer, allowing snapshot completion before scheduled archive. No SQLite database dump option was supplied because Termalin database dump helper supports postgres/mysql only; separate SQLite online snapshots are included as files.
- `backup_list` confirms job remains DRAFT waiting for owner confirmation. **No encrypted Termalin archive exists yet.** Owner must open the link and confirm it to create the encryption key. After confirmation, call `backup_create` immediately for a first archive with label `Initial pre-release backup of production and development Job Radar`; then verify success and archive size with `backup_list`. Daily schedule then runs at 03:00 UTC. Do not claim off-host encrypted backup complete until this succeeds.

### Safety and next action
- This backup work did not modify application source, runtime config, live databases, source enablement, container images in use, container lifecycle, or send notifications. Production `v2-radar-1` and dev `job-radar-dev` remained running; volumes were only read for online snapshots and config copies.
- Production still requires a separate, explicit deployment approval. This backup is preparation only, not permission to deploy.
- Exact next action: user confirms the Termalin draft using the link above. Then assistant calls `backup_create` to generate the initial encrypted archive and verifies it in `backup_list`. Until confirmation/archive success, state is: consistent local snapshots + daily local snapshot timer installed; encrypted off-host archive pending.
- Continuation: read this handover first. Use Termalin `hosts_list`, metrics/alerts, then `ssh_exec` directly on host `job-radar`; do not ask user to run commands when Termalin can safely run them. Inspect output after every operation. Do not modify production unless separately approved. Keep updating both handovers with each new learning and exact operation/result.



## 2026-11-06 follow-through — user reviewed backup settings; Termalin still reports DRAFT
- User shared a screenshot of the Termalin 'Confirm backup' form for `Job Radar production and dev daily backup` and said the configs were confirmed. Screenshot displays the proposed paths/excludes, daily schedule at 03:00 UTC, retention 7, Termalin storage and a visible `Confirm` button; it does not show a success/completion state after clicking.
- Assistant re-queried `backup_list` twice after the user's message. Termalin still reports job `ae51ea55-d396-417e-8792-8ddfc1cd66c7` as `DRAFT, waiting for the owner to confirm`; recent archives: none. Therefore the encrypted backup job is NOT yet confirmed and no encrypted archive has been created. Do not call `backup_create` while status remains DRAFT.
- Next step: user must click the final Confirm button in that Termalin form and complete any cabinet confirmation step. Afterward, re-run `backup_list`; only when the job is no longer DRAFT should `backup_create` be called for the initial archive, then verify successful archive in `backup_list`.
- Local backups remain established: production/dev SQLite online snapshots, runtime configs/token copies, running image tar, SHA256 manifest, daily 02:45 UTC systemd snapshot timer. Final local snapshot service succeeded, both DBs passed `PRAGMA integrity_check`, and all 9 manifest entries verified. The Termalin encrypted off-host layer remains pending.
- No production service/config/database/container mutation occurred in this turn. Do not claim full backup complete until the encrypted archive succeeds.

## 2026-11-06 follow-through — confirmation click did not change Termalin backup state

- User reported clicking Confirm in the Termalin backup-draft dialog; UI button then appeared disabled/stuck and dialog remained visible in screenshot.
- Assistant re-queried `mcp__Termalin__backup_list` for host `job-radar` after the click. Authoritative response still reports backup job `ae51ea55-d396-417e-8792-8ddfc1cd66c7` as `DRAFT, waiting for the owner to confirm`; recent archives list is empty. Therefore confirmation has NOT completed and encrypted archive has NOT run. Do not call `backup_create` while still DRAFT.
- Screenshot shows the confirmation modal still open. Button appears orange in the captured frame, but no success toast/page state is visible. Possible browser request/UI hang is only an inference; do not treat disabled button as successful confirmation.
- Safe next troubleshooting: keep existing draft; don't create a duplicate. Wait briefly, then refresh the Termalin cabinet page and re-open the same draft link `https://termal.in/account#backup-draft=ae51ea55-d396-417e-8792-8ddfc1cd66c7`. Check whether job appears in confirmed backup jobs or remains draft. If still draft, try confirmation in a fresh browser tab/window, allow pop-ups/session, and inspect any visible inline error/toast; user can report exact error text. Do not repeatedly click rapidly. If UI still hangs, use Termalin support/UI or reconnect and then check `backup_list` again.
- Local backup prep remains valid: snapshot service and daily 02:45 UTC timer installed; both SQLite online snapshots passed integrity checks; all 9 checksum manifest entries verified. No encrypted off-host archive exists yet.
- No production application or database was changed by this confirmation troubleshooting. No container restart/build, config mutation, source activation, or notification send. Keep production and dev services untouched.
- Next agent must first call `backup_list` before attempting `backup_create`; only execute first archive after Termalin reports job status is confirmed (not DRAFT). After run, verify archive result and size with `backup_list`.


## 2026-11-06 follow-through — rechecked backup draft after user retry
- User asked to check again after reporting that the Confirm button appeared disabled/stuck. Re-read the latest handover and knowledge-transfer instructions first, then queried Termalin `backup_list` for host `job-radar`.
- Authoritative status is unchanged: `Job Radar production and dev daily backup` (`ae51ea55-d396-417e-8792-8ddfc1cd66c7`) remains `DRAFT, waiting for the owner to confirm`; recent archives: none. No encrypted backup has run.
- Do not call `backup_create` until `backup_list` reports a confirmed/active backup job. Do not create a duplicate draft. Owner should retry same draft link in a fresh tab/session or inspect visible inline errors; confirmation appears to remain client-side/UI-pending even after click. Link: `https://termal.in/account#backup-draft=ae51ea55-d396-417e-8792-8ddfc1cd66c7`.
- Local snapshot system remains established and previously verified: daily timer at 02:45 UTC; consistent production/dev SQLite snapshots passed integrity checks; checksum manifest verified. Encrypted off-host backup is still pending.

## 2026-11-06 — Development container rebuilt from tested Ashby patch; end-to-end Ashby dev ingestion passed

### Why the rebuild was needed
- User chose to continue development despite Termalin's encrypted-backup confirmation dialog being stuck. Encrypted off-host archive remains pending; this does not block dev-only work.
- Read current handover/knowledge transfer/reference before operations. The dev service is Compose project `job-radar-dev`, config `/home/ubuntu/job-beeper-dev/v2/docker-compose.dev.yml`, loopback binding `127.0.0.1:8001->8000`, and separate named volume `job-radar-dev_radar-dev-data:/data`. Production is separate project `v2`, container `v2-radar-1`, public port 8000, volume `v2_radar-data:/data`.
- Older dev container was created 2026-10-16, image ID `sha256:c41b89e3ee05ba5abe3de2618b2d86d51322baa47ceeaaab2b53f98e3eedba92`. Its Ashby collector was present and registered, but `source_status()` and `latency_summary()` used hard-coded four-source loops; `dedupe_candidates()` also had a hard-coded filter excluding Ashby. Host checkout at `7ebc38b` was newer than the image but still older than tested patch.

### Source and build provenance
- Tested source worktree: `/tmp/job-beeper-ashby-dedupe-test`, detached commit `c93f0414e8f99540d6004f012e8cb286e32bf1f6`. It has local `M v2/config.json` and `?? .venv/`; preserve both. Its `v2/radar.py` and `v2/test_radar.py` diffs are empty. Its modified `v2/config.json` is NOT copied into build; tracked files are built from `git archive HEAD`.
- Clean tracked-only source context: `/opt/job-radar-dev-release-c93f041`, created using `git archive`. Context size 3.4 MB, Docker transferred 771.56 KB. No `.env` or `.venv` in build context. Source `radar.py` hash in context/worktree: `b87bc0a2aaceb29df6ebdc58174d5f910b8fa060b64449e6adb8e07ee56423da`.
- Compose and dev config hashes in release context match the existing home checkout exactly: compose `969f7dde98ba60abc60095bae17511869d0affe4d24c386fca6d5dff1f6258d8`; `config.dev.json` `fe3b4e5a32a484cb0abbc9fee8faf3377dab26b5eb414725618309bcb520d348`. Therefore existing Compose and config were reused unchanged.
- Previous dev image kept under rollback tag `job-radar-dev-radar:pre-c93f041-20261106` (old image ID `sha256:c41b89e3ee05ba5abe3de2618b2d86d51322baa47ceeaaab2b53f98e3eedba92`). New candidate built as `job-radar-dev-radar:c93f041`; new image ID `sha256:dee60f11b6364abb1457695d5f74e6faf247ab6e0e4f824767ed4eebd0bc56f3`; `radar.py` hash inside image equals release source hash above.
- New image was built with `Dockerfile` from the clean context. Python syntax compile passed. Full V2 test suite ran inside the actual Python 3.12 image with Docker network disabled: **137 tests in 20.819 seconds, OK**, including `test_dedupe_candidates_includes_ashby_from_collector_registry`, all Ashby collector tests, source status and latency tests, Greenhouse tests, and LLM router/extractor tests. This verifies the exact image code without making live provider requests.
- The first background build attempt exited before running Docker because Termalin shell is `/bin/sh` and `set -o pipefail` is unsupported. Re-ran with POSIX `set -eu`; build/test job `gn4za1n81k` finished exit code 0. No application changes resulted from first attempt.

### Dev-only container recreation and preserved runtime settings
- Promoted candidate to `job-radar-dev-radar:latest`, then recreated only dev service with `sudo docker compose --env-file /home/ubuntu/job-beeper-dev/.env -p job-radar-dev -f v2/docker-compose.dev.yml up -d --no-deps --no-build --force-recreate radar` from `/home/ubuntu/job-beeper-dev`. No Compose build was invoked from the older checkout; the image was built from the clean tested worktree source.
- New dev container uses image ID `sha256:dee60f11b6364abb1457695d5f74e6faf247ab6e0e4f824767ed4eebd0bc56f3`, still binds `127.0.0.1:8001->8000`, still uses named volume `job-radar-dev_radar-dev-data:/data`, and still mounts `/home/ubuntu/job-beeper-dev/v2/config.dev.json` read-only to `/app/v2/config.json`. Project remains `job-radar-dev`.
- Effective dev config after recreate: version 11; notifications false; LinkedIn false; Naukri true; Instahyre/Greenhouse/Ashby false; Ashby allowlist contains OpenAI and PostHog; poll interval Ashby 1800s. Telegram bot token and chat ID are blank.
- Actual environment flags were preserved from `/home/ubuntu/job-beeper-dev/.env`: `GEMINI_EXTRACTION_ENABLED=true`, `GEMINI_MATCHER_ENABLED=true`, `LLM_ROUTER_ENABLED=true`, `LLM_ROUTER_MATCHER_ENABLED=false`. Config/API shadow status showed provider router enabled, matcher enabled, `calls_today=20`, daily limit 20, configured providers Groq/Gemini/OpenRouter. Do not echo any provider key. For the controlled Ashby one-shot run below, all four AI gates were disabled only for that `docker exec` subprocess via `-e`; persistent container env and `.env` were not changed. Daily quota already at limit, and no additional LLM call was made by the smoke tests.
- Dev `/health`: status ok, version 2.0.0. `/api/source-status` and `/api/latency-summary` now both list all five registered sources including Ashby. Ashby `enabled=false` as expected before the one-shot run; last_run initially null. Dedupe route source filter in running file now uses `SOURCE_NAMES` and bound SQL parameters.

### Ashby live dev smoke and ingestion
- Direct public GET-only smoke from container: OpenAI board returned 815 jobs, all 815 with published timestamps; PostHog board returned 8 jobs, all 8 with timestamps. Calls used only explicit configured public boards; no database write, scheduler enablement or notification.
- Controlled one-shot end-to-end test invoked `run_source('ashby', config)` inside `job-radar-dev`, with in-memory `ashby_boards` narrowed to OpenAI only. It did NOT change persisted config or scheduler source-enabled flag. The subprocess had `GEMINI_EXTRACTION_ENABLED=false`, `GEMINI_MATCHER_ENABLED=false`, `LLM_ROUTER_ENABLED=false`, `LLM_ROUTER_MATCHER_ENABLED=false`; runtime config asserted notifications false, LinkedIn false; `credentials_available()` asserted false. Thus no LLM provider call or Telegram delivery was possible for this one-shot run.
- Result: OpenAI Ashby collector returned 815; `run_source` recorded 815 jobs seen and 815 new; zero source error. Development DB jobs rose from 7,158 to 7,973 (815 added). `PRAGMA integrity_check` returned `ok`. The persisted config still keeps `source_enabled.ashby=false`; API source status shows Ashby disabled with last run and 815/815 counts. This is a one-time validation, NOT scheduler activation.
- Daily summary after the run: total jobs discovered 817 for 2026-11-06 Asia/Kolkata; matched 0, alertable 0, alerts sent 0. Dedupe endpoint considered 7,973 jobs, 4,678 identity groups and returned 0 real cross-source candidates in this dataset. This means no real duplicates were surfaced in the current data, not that endpoint is broken; the focused regression test proves the Ashby+LinkedIn synthetic candidate path.

### Backup / rollback state after dev release
- Fresh pre-ingestion snapshot taken before one-shot run. After run, the daily snapshot service was executed again; both current snapshots pass integrity: production 19,853 jobs / 68,042,752 bytes; dev 7,973 jobs / 40,157,184 bytes.
- Exported new current dev image and previous rollback image to `/var/backups/job-radar-pre-release-20261106/dev-release-c93f041.tar` (61,205,504 bytes); archive contents inspected with `sudo tar -tf`. Existing `running-images.tar` retains previously running prod + old dev image. The new dev release tar is separately included in the SHA manifest.
- Daily SQLite snapshot timer remains enabled at 02:45 UTC. Snapshot service final result success. `sha256sum -c /var/backups/job-radar-pre-release-20261106/SHA256SUMS` verified all 10 entries (current and pre-release snapshots/config/token copies/images). Disk: 45 GB total, approx 8.2 GB used, 37 GB free (19%).
- Termalin encrypted backup draft `ae51ea55-d396-417e-8792-8ddfc1cd66c7` remains DRAFT because the confirmation UI did not complete; no off-host encrypted archive yet. User explicitly chose to proceed with dev work despite this. Do not claim encrypted backup complete. Local backups and old image tag support dev rollback.

### Production safety and exact next actions
- Production container remains unchanged: image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, original StartedAt `2026-10-12T03:44:45.989462781Z`, RestartCount 0. Port 8000, Compose project `v2`, volume `v2_radar-data:/data` untouched. All operations/recreates above were scoped to `job-radar-dev` and port 8001.
- No production code/config/database/volume change, no source enablement, no Telegram send, no deployment. Do not confuse successful dev validation with production approval.
- Next product step: review Ashby run's jobs/match quality using aggregate, privacy-safe breakdowns, then plan a limited dev scheduler soak. Keep Ashby disabled in saved config until user decides to enable it on dev. Keep notifications off, Telegram credentials blank, LinkedIn off; keep LLM calls off or capped during soak. Monitor source freshness, new-job yield, dedupe, alertability and CPU/memory. Only after successful dev soak and reviewed backup/rollback can production release be proposed; separate explicit production authorization required.
- Handover instruction for next model: read this file, `JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `JOBBEEPER_REFERENCE.md`, and `LLM_PROVIDER_ROUTER.md` first. Termalin is connected; prefer direct `hosts_list`/metrics/alerts/`ssh_exec`, inspect results after each command, and update both handovers after each task. Never touch production unless explicitly approved.
## 2026-11-06 — Matcher false-positive fix, fingerprint invalidation, and dev runtime validation

### False positive diagnosis and fix
- After the dev Ashby one-shot Bolna run, `Conversation Quality Analyst` had persisted as a profile match (score 62) because its job description mentioned “forward deployed engineer” plus LLM/AI skills, despite the title being a non-engineering analyst/internship role. This was a confirmed false positive from `match_details()` description-based role fallback.
- Changed `match_details()` so description-derived target-role fallback is permitted only when the title itself includes a generic `developer` or `engineer` signal. Direct title-role hits, Software Development Engineer/SDE aliases, full-stack aliases, and skill+generic developer/engineer title matches remain unchanged.
- Added regression tests: (1) `Conversation Quality Analyst` with “forward deployed engineers” in the description must not match; (2) `Product Engineer` can still match through a target-role phrase in description; existing JavaScript Developer and Software Development Engineer tests continue passing.
- A test fixture initially used plural “software engineers”, while `phrase_hits` matches configured singular phrase “software engineer” exactly; corrected the fixture to singular rather than broadening the matcher. Targeted test suite then passed.

### Persisted evaluation stale-cache issue found and fixed
- First one-shot call to `refresh_job_evaluations(config)` returned 0 because the evaluation invalidation key was only a hash of config JSON. A matcher code change with unchanged config does not invalidate stored rows, so `Conversation Quality Analyst` remained match=true in persisted evaluations even though `match_details()` now returned false.
- Added `MATCHER_RULES_VERSION = 2` into `_config_fingerprint()` payload, with a code comment instructing developers to increment it whenever deterministic matching/alertability rules change. This forces `refresh_job_evaluations()` to re-evaluate persisted jobs after a matcher rules version bump, even if config itself is unchanged.
- Added test `test_matcher_rules_version_changes_evaluation_fingerprint`.
- Important rollout implication: matcher rules version bump causes an entire database's stored jobs to be re-evaluated on the next `refresh_job_evaluations()` call. In production, this may change match/alertability decisions and notification ledger states; do not deploy without a reviewed release/notification plan. The version bump has only been exercised on dev in this session.

### Test evidence and source commits
- Commits on `v2-live-radar`: `4e81d82987f041b7d8c9b5f41bb9578d50bb3967` (role fallback fix); `e1fad74eb622a3d01bf6dc481eda8e83c3620915` (false-positive test); `99e661e6418bf2752d504a82dd01f6408fad0f0a` (singular phrase test fixture); `f4d56b198dbc89ef98f73ce2191efc55d44c8186` (matcher version in fingerprint); `f2a7998ce92641a5e7e62122d7c7a6ba2b71b35d` (fingerprint test).
- Targeted five matcher/fingerprint tests passed under the isolated Python 3.10 test venv.
- Full V2 suite passed twice after the code changes: 140 tests in 18.924s in the isolated worktree, then 140 tests in 20.409s inside the new Python 3.12 Docker image with Docker networking disabled. `py_compile` passed in the Docker image. No live LLM provider requests were possible in the image test (`--network none`).

### Dev-only image deployment
- Clean tracked-only build context `/opt/job-radar-matcher-version-2-f2a7998`, sourced by `git archive` from clean detached worktree `/tmp/job-radar-match-fingerprint` at `f2a7998ce92641a5e7e62122d7c7a6ba2b71b35d`. Host source hashes: `v2/radar.py` `31a4cad595dfb78593093b483208e432df04fde5f50fb93614c8c4feb2202b3d`; `v2/test_radar.py` `3a2c419c3e8e316aa57ea813b02e9b7140018fb95a15e83019380c803e32c955`. Hashes inside built image match exactly.
- New image tag `job-radar-dev-radar:f2a7998`, image ID `sha256:84f3f2c0ede06ef4bcef97a409617ba528d4b8bf3a14e798b3ef7b504d134b8d`. Container `job-radar-dev` was recreated using only dev Compose project `job-radar-dev`, with same loopback binding `127.0.0.1:8001`, same dev named volume `job-radar-dev_radar-dev-data:/data`, and same bind-mounted `config.dev.json`. Rollback image preserved as `job-radar-dev-radar:pre-fingerprint-f2a7998` (previous dev image ID `sha256:5db9d3f712c198492eeac6229072258f1827b7ecd63578da352503a21eeb2740`). Earlier c93 rollback images also remain tagged/exported.
- Initial health request immediately after recreate returned a connection reset while Uvicorn was still in application startup. Container was running with no restart/OOM; after a short wait application startup completed and `/health` returned OK. This was startup timing, not an app crash.

### Dev database reevaluation and Bolna outcome
- At startup, the enabled dev Naukri source completed its first cycle (`seen=335`, `new=0`, `error=null`). This ran `refresh_job_evaluations()` under matcher rules version 2 and recalculated the existing 7,979 development jobs. Evaluation rows all have one current fingerprint; their evaluation timestamps span `2026-11-05T20:25:12.675200+00:00` to `2026-11-05T20:25:37.673249+00:00`. Hence a later explicit `refresh_job_evaluations()` call returned 0: startup had already completed the full reevaluation. The explicit `refresh_notification_decisions()` call then adjusted 18 development ledger decisions.
- After reevaluation, six stored Bolna jobs: `AI Solutions Engineer` remains match=true, score 73; `Conversation Quality Analyst` is now match=false, score 32, reasons include `no configured target-role match`; remaining four jobs are non-matches. All six alertable=false because dev notifications are disabled. Total Ashby evaluation counts: 820 match=false / alertable=false; 1 match=true / alertable=false (AI Solutions Engineer).
- Dev config remains version 11, notifications false; LinkedIn false, Naukri true, Instahyre false, Greenhouse false, Ashby false. Ashby boards OpenAI/PostHog remain configured but scheduler-disabled. Telegram token/chat ID remain blank. AI gates persist as before: Gemini extraction true, Gemini matcher true, LLM router true, routed matcher false; daily LLM count was previously 20/20. No new provider calls were performed in the one-shot matcher reevaluation (the process explicitly disabled all four AI gates).
- Dev health: `status=ok`; API source status lists all five sources, Ashby disabled with last one-shot test counts 6/6; Naukri startup run seen 335/new 0. DB has 7,979 jobs and 7,979 evaluation rows; `PRAGMA integrity_check=ok`. Production image ID, StartedAt and RestartCount remain unchanged (`sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, StartedAt `2026-10-12T03:44:45.989462781Z`, RestartCount 0).

### Backup and next action
- Refreshed local snapshots after the new image/reevaluation: production DB 19,853 jobs / 68,042,752 bytes, dev DB 7,979 jobs / 40,194,048 bytes, both `PRAGMA integrity_check=ok`. Exported final matcher image plus previous dev rollback image to `/var/backups/job-radar-pre-release-20261106/dev-release-f2a7998.tar`; SHA256 manifest now has 11 entries and every entry verified OK. Daily local snapshot timer remains enabled at 02:45 UTC.
- Termalin encrypted backup job `ae51ea55-d396-417e-8792-8ddfc1cd66c7` remains DRAFT after repeated UI confirmation attempts; user chose to continue dev regardless. Local snapshots are verified; off-host encrypted archive remains pending. Do not claim remote encrypted backup succeeded.
- Production untouched. All code deployment, database reevaluation and source testing in this milestone were confined to dev port 8001 / dev volume. Do not enable Ashby scheduler or notifications without user direction.
- Exact next step: run a short dev-only observation period with Ashby still disabled, Naukri active, notification false. Review current matcher distribution and relevance of Bolna/other candidates using aggregate safe metrics. Consider a follow-on matching test set before enabling any ATS source. Do not trigger LLM calls while daily cap remains exhausted. Keep production release gated due matcher version 2 potentially recalculating all production jobs/notification decisions.



### Clarification — explicit dev refresh was already complete
- After container startup, a separately invoked `refresh_job_evaluations(config)` returned `0` because the Naukri startup `run_source()` had already refreshed all 7,979 evaluations under matcher rules version 2. This was confirmed by identical current fingerprints across all rows and evaluation timestamps clustered between 20:25:12 and 20:25:37 UTC. `refresh_notification_decisions(config)` then changed 18 dev ledger decisions; notifications remained disabled and Telegram credentials blank, so no delivery occurred.

## 2026-11-06 — Naukri title/description mismatch investigation and matcher quality seed

### Evidence and diagnosis
- Continued the Naukri quality review from the deployed dev build, using exact source worktree `/tmp/job-radar-naukri-location-v3` at `5e96599e01ea0a605f43f9a46991d6ecd64bd971`. Do not use ordinary checkout `/home/ubuntu/job-beeper-dev` as the source of truth: it is still at `7ebc38b7c321847e74895557551478c3ff11bd4a` and has protected local config/environment artifacts.
- Confirmed the active Naukri feed is in the separate public repository `AvinashBhalla/job-beeper-naukri-relay`, branch `naukri-relay`, file `dashboard/data/naukri_relay.json`. It returned `updated_at=2026-11-05T20:54:25.142767+00:00`, `count=330`, blob SHA `61b7cd70d4b0b8d9a0f8185620aedd42b8dcfb49`. A first attempted URL against the private app repository returned 404; this was the wrong repository path, not a relay outage.
- The Novisync source record `nk-nk-051126503145` (Python Developer; Bengaluru) appears in the relay JSON with a business-strategy/client-relationship/partnerships/market-analysis/customer-service responsibility body, followed by the aggregator disclaimer and a trailing `0-2 Yrs SQL, Cs, Javascript, Intelligence, CSS, Processing, Natural language processing, Django` keyword tail. The relay item has no separate `skills_detected` field. The persisted dev row (id 7113) has the same source ID and description, score 88, match=true, reasons for target location, title-role hit, Python/Django/JavaScript skills and compatible 0–2 experience. This establishes the mismatch is already present in the feed payload; the V2 collector preserves the supplied description and does not independently invent the text.
- The original Naukri employer posting could not be independently verified in this step. Therefore classify Novisync as **review required / suspected title-description mismatch**, not a confirmed negative, and do not add a broad rejection heuristic based on this one item.
- Compared the relay examples: Ashok Maheshwary & Associates — AI Automation Engineer — contains concrete AI/LLM/Power Automate/RPA/API/workflow implementation responsibilities and 2+ years (positive); Iqvia Biotech — QA Automation Engineer — contains concrete test-script/framework/CI/CD automation responsibilities and 2+ years (soft-positive/adjacent). These two support retaining automation roles, including QA automation, as relevant categories for the configured profile.

### Anonymized benchmark seed added (no runtime deployment)
- Added `v2/fixtures/matcher_quality_benchmark.json`, `v2/matcher_quality_benchmark.py`, and `v2/test_matcher_quality_benchmark.py` in the clean 5e96599 worktree. The seed has five anonymized examples: AI Automation Engineer positive; QA Automation Engineer soft-positive; Python Developer/business-description mismatch review-only; explicit Pune work-location negative; and Conversation Quality Analyst with incidental engineer mention negative.
- The benchmark calls the existing deterministic `match_details()` with `v2/config.dev.json`. It excludes the unresolved review case from pass/fail precision scoring, but reports its actual match and score so quality regressions are visible. It does not modify matching, stored evaluations, config, sources, alerts, or the live database.
- Benchmark output: 5 cases; 4 scored; 1 review-only; **4/4 scored cases passed; 0 failures**. Novisync remains review-required and currently matches at score 88. QA Automation Engineer matches at 76; AI Automation Engineer matches at 88; both negatives are rejected.
- New focused tests: 2 passed. Full V2 unit discovery in a throwaway container based on the deployed Python 3.12 image, with Docker network disabled and the three new files mounted read-only: **145 tests passed in 18.402 seconds**. The benchmark report itself was also run with network disabled. Mocked LLM tests in the suite do not make live provider calls; no provider API, LLM extraction endpoint, or Telegram send was invoked.
- This is a provisional seed, not a statistically representative precision estimate. Keep adding manually reviewed, source-diverse examples before tuning a more general quality gate. Next investigation should verify the original employer posting for the Novisync listing or capture a second independently confirmed title/body mismatch, then evaluate any upstream relay parser/field-separation correction rather than penalizing all developer titles.

### Runtime and release boundaries
- Development container remained the deployed image `sha256:c4076ee204c64164b5db72e6de92c1f26075ee4b012093e38251dc1e53cf1a6f`, running on the dev volume/port 8001. No container restart, image rebuild, runtime config edit, database write, or scheduler/source-enable change was made for this benchmark.
- Dev notifications remain false; Telegram credentials remain blank; Naukri remains enabled; LinkedIn/Instahyre/Greenhouse/Ashby remain disabled. LLM daily allowance had been exhausted at 20/20; no additional provider call was made.
- Production remains untouched and no production deployment is authorized by this milestone. Termalin encrypted backup draft `ae51ea55-d396-417e-8792-8ddfc1cd66c7` remains DRAFT; local snapshots remain verified, but no off-host encrypted archive has been created.
- Worktree change is limited to the three benchmark files plus these handover additions. No matcher logic change. Before any code push, verify exact remote branch head and preserve the protected ordinary checkout state.

## 2026-11-06 — Multi-user product priority and HAPPPY-like roadmap

- User changed the next product priority: JobBeeper should now serve multiple users with independent candidate preferences, roles/permissions and their own Telegram destinations, enabling a small beta and real user feedback. The previous "multi-user later" roadmap item is superseded; preserve it as historical context only.
- Added the detailed architecture/implementation plan in [MULTI_USER_AND_REFERRAL_ROADMAP.md](MULTI_USER_AND_REFERRAL_ROADMAP.md). Read it with this handover, the compact knowledge transfer, [JOBBEEPER_REFERENCE.md](JOBBEEPER_REFERENCE.md), and [PRODUCT_REVERSE_ENGINEERING_PLAN.md](PRODUCT_REVERSE_ENGINEERING_PLAN.md).
- Core architectural decision: keep source collectors, normalized jobs, canonical opportunities and source health shared. Scope candidate preferences, evaluations, saved/applied state, notification ledger and Telegram destination by authenticated user. Do not scrape each source separately for every user.
- Current global `job_evaluations` (keyed by job_id), global `notification_ledger` (keyed by canonical opportunity), global config and single config-token authorization are not multi-tenant. They must not be reused unchanged for multiple users.
- Proposed first-beta roles: `admin` and `user`; use backend authorization on every protected route. Proposed auth: Argon2id password hashes, opaque server-side sessions with hashed token storage, HttpOnly/Secure/SameSite cookies, CSRF protection, login rate limits and explicit CORS origins. Remove the repeated X-Config-Token/sessionStorage workflow only after login/session tests pass.
- Telegram recommendation: one platform-owned JobBeeper bot token stored server-side, with a one-time, expiring, single-use deep-link nonce that binds each user's Telegram chat_id to their account. This is per-user Telegram delivery without asking each user for a bot token. BYO bot tokens are a separate later option, not first-beta scope.
- New notification identity must include user and channel, e.g. `(user_id, canonical_opportunity_id, channel)`. Establish a new user's notification baseline so onboarding does not replay historical jobs. Delivery failures must be isolated per user.
- Migration must preserve shared jobs/canonical IDs, backfill the existing personal preferences and existing notification state to the initial admin/owner only, and run against a database copy before any production migration. SQLite may serve a small pilot with deliberate serialized writes; do not introduce microservices merely to support first beta.
- HAPPPY-like workflow is already named at a high level in PRODUCT_REVERSE_ENGINEERING_PLAN.md, but it was not yet a detailed implementation plan. New roadmap defines: application tracker -> relevant contact discovery from public/authorized sources -> explainable contact ranking -> personalized outreach draft -> user approval -> Gmail/Outlook draft creation -> follow-up reminders and response tracking. Email OAuth is user-authorized and least-privilege; first release is draft-only, not automatic send. Do not automate LinkedIn connection requests/messages or bypass access controls/rate limits.
- Explicit sequence: finish/push current search+description work -> multi-user auth/RBAC -> user preferences/evaluations -> Telegram linking/fan-out -> beta feedback -> application tracker -> referral intelligence. Hiring-post discovery remains later.
- This is a product/architecture plan only; no auth, multi-user schema, Telegram linking, email OAuth, referral workflow or production migration has been implemented by this entry.
## 2026-11-06 — Six-minute Naukri dev soak and explicit-work-location quality fix

### Read-only dev soak
- Re-read the latest handover, knowledge-transfer, reference and router runbook before this task. Only dev service `job-radar-dev` at `127.0.0.1:8001` and dev volume were used; production service `v2-radar-1` stayed untouched.
- Captured six-minute read-only observation from 2026-11-05T20:35:47Z through 20:41:59Z, sampling health, source-status and Docker stats every 60 seconds. Uptime remained continuous; health returned ok in all seven samples; container CPU ranged 0.13–0.50%, memory 30.95–51.12 MiB. One scheduled Naukri poll completed at 20:40:41Z: jobs_seen=336, new_jobs=0, error=null. Last seven minutes contained two Naukri runs, 668 total jobs_seen, zero new jobs, zero failed runs; DB integrity ok. This is a short soak, not a multi-day reliability claim.
- Metrics/alerts check: no open Termalin alerts. Latest server sample at 20:33 UTC: CPU 0.9%, memory 50.2%, disk 18.3%, load1 0.02; over 6h CPU average 16.6% (peak 60.5), memory average 52.85% (peak 58.2), disk average 17.97% (peak 18.3), CPU steal average 10.98% (peak 40.1%). No action was taken on the host.

### Corrected source-trend audit
- Earlier exploratory SQL used SQLite `datetime('now', ...)` with a space separator against ISO timestamps containing `T`, which lexically over-counted records from the cutoff date. Re-ran with timezone-aware ISO cutoff strings; use these corrected numbers only.
- Naukri last 24h: 288 source runs, 95,467 jobs_seen, 176 new jobs, zero failed runs; median run interval over last 6h was 5.00 minutes. Last 6h: 72 runs, 24,050 seen, 26 new, zero failed. Last 1h: 12 runs, 4,046 seen, zero new, zero failed. Latest recorded job scan is 338 seen / 0 new with no error.
- Of the 176 Naukri jobs newly discovered over 24h, publication dates (date-level precision) were 104 in the last day, 65 one-to-three days old and 7 three-to-seven days old. This means 169/176 were dated within 3 days. These are date-only timestamps, not exact posting times; discovery latency is intentionally NULL for Naukri.
- Before the location-quality fix, the current profile matcher passed 4/176 Naukri jobs from the 24h window; after version 3 reevaluation it passes 3/176. The last 6h cohort had 26 new Naukri jobs and zero matches; primary rejection reasons were 16 above candidate experience, 4 excluded titles, 4 above configured max experience and 2 outside target location. These outcomes align with the configured 2-year candidate / max-3-year profile; no evidence justified loosening the experience filter.
- Ashby remains historical one-shot data only: 821 jobs, 1 match (the Bolna AI Solutions Engineer), 820 non-matches. Ashby is still disabled in saved config. OpenAI board remains a poor match for the India-focused profile; Bolna yielded one plausible AI/automation match after the description-role false positive was removed.
- `/api/latency-summary` contains 821 Ashby samples and zero Naukri samples. Naukri is date precision and deliberately excluded from exact seconds; Ashby samples reflect published-to-first-discovery age on first import (including old historical OpenAI postings), not just the scheduled polling interval. Do not interpret this as scan cadence; source-runs timestamps are the measure for poll cadence.

### Naukri matching-quality findings and code fix
- Manual review of four Naukri matches in the 24h cohort found two data-quality problems: (1) Karnex `Software Engineer` listing source metadata said `Pune, Chennai, Bengaluru, India`, while its description explicitly said `Work Location: Pune`; (2) Novisync `Python Developer` had a business-development/client-relationship description with a trailing detected-skill list, despite matching at scores 88 and 82. The latter remains flagged for upstream feed/description-quality investigation; no broad heuristic was added because the evidence set is too small and could suppress legitimate technical jobs.
- Implemented `extract_explicit_work_location()` and `job_location_for_matching()` in `v2/radar.py`. A clearly labelled `Work Location:` in the description takes precedence for profile matching and shadow-candidate filtering; an interview venue is not mistaken for work location. The persisted `jobs.location` field is intentionally not rewritten, preserving original source metadata and canonical identity. The rule applies only when an explicit label is found; otherwise original source location remains the fallback.
- Added three tests: broad multi-city feed metadata overridden by explicit Pune location (must reject), explicit Bengaluru location overrides stale Pune feed metadata (must match), and parser stops at `INTERVIEW VENUE` rather than using it as work location. Matcher rules version incremented to `MATCHER_RULES_VERSION = 3`, ensuring persisted evaluations are recalculated under the new deterministic location rule.
- Regression evidence: targeted location tests 3/3 passed; full V2 suite 143/143 passed under isolated test venv and again inside the actual Python 3.12 Docker image with networking disabled; py_compile passed. Image unit tests made no provider HTTP calls.
- Confirmed live stored Karnex record after reevaluation remains source location `Pune, Chennai, Bengaluru, India` but now `match=0`, score=0, reason `location outside configured targets`. This removes one known false match. Novisync business-description listing remains match=true (two source records) and is intentionally documented for follow-up rather than silently suppressed.

### Source commits and deployment
- Branch `v2-live-radar` now includes commits `7a0258029f8ad6691b31be1c58b34e16e99be0da` (explicit work-location matching and shadow filter), `786c1b735b6afd39387561cbdd2532322cd4e128` (three location regression tests), `80542be3af9e0618003dad08d7938bcf7837a5f6` (corrected regex escaping discovered by tests), and `5e96599e01ea0a605f43f9a46991d6ecd64bd971` (matcher version 3).
- Clean tracked-only build context `/opt/job-radar-naukri-location-v3-5e96599` came from detached worktree `/tmp/job-radar-naukri-location-v3` at commit `5e96599e01ea0a605f43f9a46991d6ecd64bd971`; no `.env` or `.venv` in context. Source hashes: `v2/radar.py` `6484e88edbbf773c271e94871994c73281b0ca5a7cfd2b01ae4f9af39cca3143`; `v2/test_radar.py` `3a463866337113fec049afa1a3da1702966f55dc5eb8230b17b4228550516f55`. Hashes inside image matched.
- New image `job-radar-dev-radar:5e96599`, image ID `sha256:c4076ee204c64164b5db72e6de92c1f26075ee4b012093e38251dc1e53cf1a6f`. Recreated only `job-radar-dev` with same Compose project, `127.0.0.1:8001` binding, named volume `job-radar-dev_radar-dev-data:/data`, bind-mounted dev config, and VM `.env`. Existing dev image retained as rollback tag `job-radar-dev-radar:pre-work-location-v3` (image ID `sha256:84f3f2c0ede06ef4bcef97a409617ba528d4b8bf3a14e798b3ef7b504d134b8d`).
- Startup initially returned connection resets while performing version-3 reevaluation; container stayed running, no OOM/restart, then Uvicorn completed startup. Health is now ok. Startup Naukri run seen=338/new=0/error=null. Database contains 7,979 jobs and 7,979 evaluations, one current fingerprint, PRAGMA integrity_check=ok.
- Final match totals: Naukri 274 matches / 7,158 jobs, zero alertable; last 24h 3 matches / 176 newly discovered. Ashby 1/821. Daily summary for 2026-11-06 Asia/Kolkata: 823 discovered, 1 matched, 0 alertable, 0 sent. Dev notifications false; Telegram token/chat ID blank; LinkedIn false; Ashby false; Naukri true. LLM call counter remains 20/20; do not trigger new model calls until budget resets. No matcher rule sends Telegram.

### Backups and production safety
- Pre-deploy snapshot taken; post-deploy snapshot refreshed successfully. Final snapshots: production 19,857 jobs / 68,063,232 bytes; development 7,979 jobs / 40,194,048 bytes; both PRAGMA integrity_check=ok. Production's count advanced while its normal service continued; no production restart or change was made.
- Exported final dev image plus previous dev rollback image to `/var/backups/job-radar-pre-release-20261106/dev-release-5e96599.tar` (61,079,040 bytes), inspected tar entries. Added its SHA-256 to manifest. `sha256sum -c /var/backups/job-radar-pre-release-20261106/SHA256SUMS` passed all 13 entries. Disk 45 GB total, 8.3 GB used, 37 GB free (19%).
- Production remains image `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, StartedAt `2026-10-12T03:44:45.989462781Z`, RestartCount 0. No production code, config, DB, volume, source, or notification change. Termalin encrypted backup remains a draft; local verified backups exist, off-host encryption still pending.

### Next actions
- Continue source observation. Keep Naukri active, Ashby/LinkedIn/Greenhouse/Instahyre disabled, notifications off, Telegram credentials blank, and LLM provider calls at zero until quota resets.
- Investigate Novisync's title/description mismatch at the Naukri relay layer. Inspect the public relay item's separate `description`, `skills_detected`, title and location fields; consider adding a conservative quality-review flag/test dataset, not a broad description keyword rejection based on one example.
- Build a small anonymized human-reviewed matcher benchmark from recent true positives and false positives (including AI Automation Engineer, QA Automation Engineer, Novisync Python Developer, Karnex explicit work-location case, and the Bolna Conversation Quality Analyst) before tuning role/skill thresholds.
- Consider discovering a broader set of India-focused public ATS boards only after reviewing board relevance and freshness. Do not enable any ATS source or change the dev config without staged testing; production release still requires a separate explicit approval.
- Handover for next run: read the latest versions of this handover, `JOB_RADAR_KNOWLEDGE_TRANSFER.md`, `JOBBEEPER_REFERENCE.md`, and `LLM_PROVIDER_ROUTER.md` before action.

## 2026-11-06 — Feature branch published; draft development PR opened
- Published feature branch `feat/naukri-rich-descriptions-20261106` to GitHub at head `c1004955fb2fe394e56f01f5015634d442aa3c5a`. It contains server-side search commit `093c475`, rich Naukri Markdown/structured details commit `727bdb9`, matcher benchmark additions, and the multi-user/referral roadmap documentation. The branch was merged with the latest `v2-live-radar` documentation commits before push; merge base now includes the current remote dev head `9c56322`.
- Opened draft PR #44 targeting `v2-live-radar`: https://github.com/AvinashBhalla/job-beeper/pull/44. This is a development-branch PR, not a production PR. Do not merge until review and CI complete; do not retarget to `main`.
- Local verification: full V2 unit discovery in a throwaway `--network none` container based on `job-radar-dev-rich-jd:20261106`: 149 tests passed in 18.723s. Focused benchmark tests: 2 passed; benchmark output 4 scored cases passed, 1 review-only unresolved case. `git diff --check` passed before commit.
- At first check after PR creation, GitHub's `syntax` check was in progress. Re-check PR #44 checks before treating CI as complete. The local 149-test run is separate from GitHub CI.
- Final feature commit after merge/publish: `c1004955fb2fe394e56f01f5015634d442aa3c5a`. No production container/config/database/volume or Telegram notification was changed. Current dev image remains the same matching build; no container recreation was performed during this documentation/PR operation.

## 2026-11-06 — Multi-user tenant-readiness code/schema audit
- Read-only inspection of feature worktree `/tmp/job-radar-naukri-location-v3`, live dev OpenAPI and live dev SQLite schema confirmed there are no users/sessions/preferences tables and no `user_id` columns in current records. Live tables are `jobs`, `canonical_opportunities`, `job_evaluations`, `notification_ledger`, `source_runs`, `gemini_shadow_cache` and `sqlite_sequence`.
- `job_evaluations` is globally keyed by `job_id`; `notification_ledger` by `canonical_opportunity_id`. Current match and notification decisions are therefore single-profile/global.
- Config is one global `/data/config.json`; `PUT /api/config` is protected by a global `X-Config-Token` read from env or `/data/config_token`, but `GET /api/config` currently returns the profile/config without authentication. Protect it before external beta access. Frontend stores this token in `sessionStorage`; no login/session/role endpoints exist.
- `v2/telegram.py` reads one global bot token and one global chat ID from environment; delivery worker claims the global ledger and joins the global evaluation. Per-user Telegram requires redesigning the delivery contract and ledger, not merely a settings form.
- Applied Jobs currently lives in browser `localStorage` key `job_beeper_applied_jobs_v1`, not server DB; multi-device use and future referral workflow require a server-side user-owned `applications` table and import/export migration.
- Current API route inventory and a recommended first implementation cut are recorded in section 11 of `MULTI_USER_AND_REFERRAL_ROADMAP.md`. Operational routes such as source health, latency, dedupe and LLM status should be admin-only or sanitized for ordinary users.
- Audit was read-only: no DB writes, source runs, notification sends, config changes, container restarts or production operations.

## 2026-11-06 — Production checkout drift observed during read-only audit
- Read-only host audit found `/home/ubuntu/job-beeper` (the production checkout) on `v2-live-radar` at `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, reported **613 commits behind** its fetched `origin/v2-live-radar` ref. This checkout was not pulled or modified.
- The running production container `v2-radar-1` remains on its prior image ID `sha256:97368934ed144f3441a6271459adbd38a689d64c741081cc6382a53ba274b35f`, port 8000, Compose project `v2`, restart count 0. This is a runtime observation; it does not mean the production checkout is safe to update.
- Treat production checkout and runtime as separate states. Do not pull, reset, rebuild, restart, migrate, switch branches or change production source/config until the user explicitly approves a reviewed release and rollback plan. Continue feature work only in `/tmp/job-radar-naukri-location-v3` and the draft PR targeting `v2-live-radar`.


## 2026-11-06 — Multi-user authentication foundation implemented (not deployed)

### Code and security boundary
- Started from the post-PR-#44 `v2-live-radar` base (`7b61d74`) in the isolated worktree `/tmp/job-radar-naukri-location-v3`, branch `feat/multi-user-foundation-20261106`. No production or running dev checkout was used as the feature source.
- Commits on the feature branch: `9ffed3f` — SQLite identity/session primitives; `93dea33` — login/session endpoints, CLI and admin route guards; `44a052f` — dashboard cookie-session login/account UX; `27a77cd` — atomic first-admin bootstrap, concurrency-safe hashed login throttling, login-Origin validation, no-store API responses and development cookie settings; `ea463cb` — same-origin API-base enforcement and account-wide throttling across IPs. CI dependency update is `8b7f210`; docs/test workflow update is `a5d8b42`. The branch is pushed and PR #45 is open against `v2-live-radar`; latest head `ea463cb` is awaiting CI and automated re-review.
- Added `v2/auth.py`: additive `users`, `sessions`, `login_attempts`, `login_account_attempts` schema; normalized unique email; Argon2id password hashes; admin/user roles and active/disabled status; seven-day opaque sessions; SHA-256 token/CSRF hashes; expiry and revocation; five atomic attempt reservations per email/IP plus twenty per account across all IPs in a 15-minute window (hashed email/IP keys; malformed addresses are throttled too), reset on successful login.
- Added `POST /api/auth/login`, `GET /api/auth/me`, and `POST /api/auth/logout`. Session cookie is HttpOnly; CSRF cookie is readable by same-origin JS; both are Secure by default, SameSite=Lax, Path=/, seven-day max age. Unsafe admin requests require matching CSRF cookie/header and stored hash. Successful login revokes the prior presented session; failed login does not.
- All existing legacy `/api/*` routes require an admin session; user-role accounts receive 403. `/health` and login remain public; `/health` now returns only status/version/uptime. Admin state-changing routes also require CSRF, and all API responses are no-store. The old config-token helper remains unused by the browser path; `PUT /api/config` now relies on admin session + CSRF. Login rejects supplied cross-origin Origin headers; configure `JOB_BEEPER_PUBLIC_ORIGIN` when a TLS proxy origin differs from the origin Uvicorn sees. The loopback-only dev Compose service defaults Secure cookies off for SSH-tunnel development; production remains Secure=true.
- Added operator CLI `python -m v2.auth_admin create-admin --email ...` (first admin only) and `create-user --email ...` (ordinary beta users only). Passwords are prompted with `getpass`, not accepted as CLI arguments. In the app container, `JOB_RADAR_DB=/data/jobs.db` is already configured.
- Dashboard now loads `auth.js` before `app.js`, authenticates before initializing any job feed or polling, uses same-origin cookies and CSRF headers, rejects cross-origin `?api=` overrides before credentials are sent, and has login/account/logout and ordinary-user holding panels. Browser config-token/sessionStorage flow is removed. The old global config and job evaluations remain admin-only; user-specific preferences/evaluations are the next milestone.

### Tests and verification
- Added persistence, session, password, rate-limit, CLI, API role/CSRF and dashboard auth-client contract tests.
- Final V2 suite passed **189 tests in 79.321 seconds** in a throwaway Docker container with `--network none` (one Node-only dashboard test was skipped inside the Python image). The separate Node-enabled dashboard contract suite passed **4/4** on the VM host in 0.655 seconds. Dashboard JS parsed/built with esbuild 0.19.12; Python compile, Compose config resolution and `git diff --check` passed.
- No LLM/provider requests, Telegram sends, source changes, runtime config changes, database writes to live dev/prod, container rebuilds/restarts, or deployment occurred.

### Runtime and release gates
- Live development remains on `job-radar-dev-rich-jd:20261106` (loopback port 8001); the auth feature is not in that image and its live DB has not been migrated. Production `v2-radar-1` on port 8000 remains unchanged.
- `JOB_BEEPER_COOKIE_SECURE` defaults to true; HTTPS is required. The loopback-only dev Compose service defaults it to false for SSH-tunnel development; production remains true. Set `JOB_BEEPER_PUBLIC_ORIGIN` if the TLS reverse proxy origin differs from Uvicorn’s request base URL. Do not disable Secure publicly.
- The Termalin encrypted backup job remains DRAFT. Local snapshots do not prove an off-host encrypted archive exists.
- Next: verify CI and automated re-review on PR #45, merge into `v2-live-radar` when all checks/review threads are clear, then continue with user-scoped preferences/evaluations. No production deployment is authorized.

## 2026-11-06 — PR #45 merged; user preferences milestone approved; branch audit and dev access

### Authentication foundation status
- PR #45 [Add secure multi-user authentication foundation](https://github.com/AvinashBhalla/job-beeper/pull/45) is **merged** into `v2-live-radar` as `dd7aeb1eea4790564a73367df90f7d4a07e012ea`. It is a code merge only; no dev/prod container, database, config, volume or source runtime was changed.
- Final PR head was `366028d`; full V2 suite was 189 passed (one Node-only test skipped in Python-only Docker image), Node dashboard auth contract 4/4 passed, esbuild/Python compile/Compose validation/diff check passed, and GitHub CI was green. Codex re-review remained stuck in "running"; manual review, resolved review threads and CI were used.
- The former `feat/multi-user-foundation-20261106` remote branch is already absent from GitHub. A stale local remote-tracking ref was pruned.

### Product decision confirmed by user
- User confirmed that a new account must configure a target job role and location before it can browse its personalized feed. Both fields are required; do not show the shared/global job feed or an empty feed to incomplete users. Show a clear onboarding state instead.
- New accounts must start with empty preferences; never clone the first admin's candidate profile into new users. Existing global candidate preferences migrate only into the first admin's `user_preferences` row.
- Shared collectors, normalized jobs, canonical opportunities and source health remain shared. Candidate preferences and evaluation rows are per-user. Source controls and the current global Telegram pipeline remain admin-only for now.
- Design: `docs/superpowers/specs/2026-11-06-user-preferences-evaluations-design.md`.
- Plan: `docs/superpowers/plans/2026-11-06-user-preferences-evaluations-plan.md`.
- Roadmap updated: `docs/MULTI_USER_AND_REFERRAL_ROADMAP.md`.

### Current worktree and test baseline
- Active feature branch/worktree: `feat/user-preferences-evaluations-20261106`, `/tmp/job-radar-user-preferences`, based on `dd7aeb1`. Initial baseline before implementation passed 189 tests; latest implementation validation is recorded in the 2026-11-06 progress section below.
- The active feature worktree is clean at the point this note was written, before the docs/spec/plan updates in this commit.
- Existing dev checkout `/home/ubuntu/job-beeper-dev` is dirty and protected: `M v2/config.json`, `.env.save`, `.venv/`, and `v2/config.json.backup.20261105-183321`; HEAD `7ebc38b`, local `v2-live-radar` branch appears 66 commits behind refreshed remote. Do not reset, clean, checkout, or overwrite this checkout.
- Production checkout `/home/ubuntu/job-beeper` remains stale/protected; do not touch it.
- Active dev container `job-radar-dev` is running on loopback `127.0.0.1:8001`; production `v2-radar-1` is separate on port `8000`. Termalin confirmed both containers are Up. Docker access required `sudo -n docker`; no container was changed. The existing dev container is an older image and does not contain PR #45.
- No active database migration, DB write, container restart/rebuild, config change, Telegram send or LLM request was performed. The Termalin encrypted backup draft `ae51ea55-d396-417e-8792-8ddfc1cd66c7` is still DRAFT; do not claim an off-host encrypted backup.

### Windows PowerShell access to the currently running dev service
Use this only to inspect the **existing older dev build**, not to validate PR #45 or the new preferences feature:
```powershell
# Terminal 1: keep this SSH tunnel open
ssh -L 18001:127.0.0.1:8001 ubuntu@130.210.27.197

# Terminal 2: open the dashboard
Start-Process "http://127.0.0.1:18001/dashboard/"

# Terminal 2: health check
Invoke-RestMethod "http://127.0.0.1:18001/health" | ConvertTo-Json -Depth 5
```
If SSH requires a key or host alias, retain the exact working SSH identity/options and add only the `-L 18001:127.0.0.1:8001` argument. Do not expose port 8001 publicly. Do not rebuild the existing service from the dirty dev checkout. The new feature must be tested in an isolated project/volume/port or a disposable container before considering any migration.

### Branch audit and cleanup (2026-11-06)
- Integration branch: `v2-live-radar`; production release branch: `main`. Keep both.
- Active/needed remote branches retained:
  - `feat/matcher-quality-benchmark-20261106` — open PR #41, keep.
  - `work/job-intelligence-foundation` — open draft PR #37, keep.
  - `work/source-run-telemetry-clean` — open PR #40, keep.
  - `fix/linkedin-experience-parser` — PR #36 merged to `main`, but its 70-line parser/test delta is not in `v2-live-radar`; keep until this fix is deliberately ported or explicitly retired.
  - `feat/user-preferences-evaluations-20261106` — current active multi-user milestone branch; keep until its PR is reviewed/merged.
- Deleted remote branches `validation/source-run-telemetry` and `work/source-run-telemetry`: their PRs #39/#38 were closed without merge and their code changes are present in the retained clean telemetry branch; comparison against `work/source-run-telemetry-clean` showed only handover-document differences. PR #40's clean branch remains.
- Archived the unique, unreviewed SSE experiment as tag `archive/sse-infrastructure-20261106`, then deleted remote branch `feature/sse-infrastructure`. This keeps the exact source commit recoverable without leaving an inactive branch.
- `feat/multi-user-foundation-20261106` was already deleted remotely after PR #45 merge; its stale local remote-tracking ref was pruned.
- Remote branches are now 7: `main`, `v2-live-radar`, `feat/matcher-quality-benchmark-20261106`, `feat/user-preferences-evaluations-20261106`, `work/job-intelligence-foundation`, `work/source-run-telemetry-clean`, `fix/linkedin-experience-parser`. The SSE branch is preserved only as the archive tag above.
- Local branch list remains three: current user-preferences feature branch, protected `v2-live-radar` checkout in dirty dev worktree, and parser-fix branch in its own worktree.
- After individual audit, removed two clean detached worktrees whose HEADs were already reachable from the retained integration/production branches: `/tmp/job-beeper-main-baseline` (reachable from `origin/main`) and `/tmp/job-radar-explicit-location` (reachable from `origin/v2-live-radar`). Eight worktrees remain: three branch-attached and five detached. Preserve the remaining detached worktrees: several contain uncommitted local config/venv artifacts, and `/tmp/job-radar-naukri-location-v3` contains the ignored Superpowers progress ledger. The count of worktrees is not the same as active Git branches.

### Next exact steps
1. Continue from `/tmp/job-radar-user-preferences` on `feat/user-preferences-evaluations-20261106`; read the design and plan above before coding.
2. Implement additive preferences/evaluations schema with TDD; test on synthetic/disposable DB only.
3. Refactor matching to explicit user preferences; require role+location for feed access; scope all feed/evaluation endpoints by authenticated session.
4. Update dashboard onboarding and user-scoped feed; keep admin global operations intact; namespace local applied state.
5. Run full test suites, security/tenant review and CI; update these handover docs and roadmap with every material change.
6. Open a focused PR targeting `v2-live-radar`. No production deploy; no rebuild/restart of the existing dev service until a separate isolated test environment and backup gate are verified.
7. User does not need to supply anything for implementation/design. When isolated auth testing is ready, the user may need to set the first admin password interactively inside the disposable test environment; never ask them to send a password in chat.

## 2026-11-06 — user preferences implementation progress (feature branch, not merged)

### Implemented in the current working tree
- New `v2/user_preferences.py`:
  - Idempotent `user_preferences` and `user_job_evaluations` tables, foreign keys, unique `(user_id, job_id)`, and feed/fingerprint indexes.
  - Empty defaults for ordinary users; strict field allowlist and type/range validation.
  - Both target role and target location are required to mark onboarding complete.
  - First-admin-only candidate profile migration and admin config synchronization. System/source/notification fields are excluded.
  - The account-provisioning CLI performs first-admin migration immediately, even if the API process is already running; normal users are provisioned with an empty row.
  - Deterministic SHA-256 preference + matcher-rules fingerprint.
- `v2/radar.py`:
  - DB initialization creates preference/evaluation schema and migrates the first admin's legacy candidate profile.
  - `require_authenticated` enforces session auth and CSRF for unsafe methods; `require_admin` builds on it.
  - `GET/PUT /api/preferences` are session-scoped; writes require CSRF.
  - User-specific evaluation rows are created on preference save, startup and for touched jobs after shared ingestion. Preference edits do not start collectors. If the first admin is provisioned after app startup, the first feed request lazily initializes their evaluations without a process restart.
  - `GET /api/jobs`, `GET /api/jobs/{job_id}`, and `GET /api/daily-summary` are user-scoped and blocked until onboarding is complete.
  - Job feed uses only the session owner's evaluation row and filters normal-user matches before applying LIMIT, so newer non-matches cannot hide older matches. Normal users receive no global notification-ledger status, sent timestamp or last error. Admin continues to see the existing global alertability/notification state.
  - New users default to a permissive 30-year experience ceiling until experience-range controls are exposed; a hidden three-year cap would silently exclude senior roles.
  - Existing global `job_evaluations` and `notification_ledger` are preserved for the admin Telegram worker.
- `dashboard/index.html`, `dashboard/styles.css`, `dashboard/app.js`:
  - Separate minimal user workspace; normal users do not load the admin app shell or operational controls.
  - Onboarding form for comma/newline-separated target roles and locations, optional skills, save/edit, refresh, and personalized matching cards.
  - Incomplete users do not request the jobs feed. Configured users see only likely matches and their own scores/reasons.
  - User workspace does not use the admin localStorage applied/saved state.
- New isolated smoke-test environment:
  - `v2/docker-compose.feature.yml`, `v2/config.feature.json`.
  - Port 8002 bound to loopback only, independent `radar-feature-data` volume, unique container name, generic non-personal candidate defaults, all collectors/Telegram/LLM providers disabled.
  - Compose config validated and Docker image built successfully. **The feature container has not been started.**
  - `v2/seed_feature_demo.py` inserts four synthetic listings for repeatable feed testing and refuses to run unless `JOB_BEEPER_FEATURE_DEMO=true`; the feature Compose file sets that flag. A guard test confirmed the script exits before DB initialization when the flag is absent.
  - Root README has exact Windows PowerShell commands to start the feature instance, bootstrap an admin, create a beta user, seed demo jobs, open SSH tunnel `18002`, check health and stop the container. It does not share existing dev port 8001 or production port 8000.

### Automated PR review follow-up
- Codex review identified two P2 issues: the user feed applied LIMIT before the frontend filtered matches, and the new-user default max experience of three years was too restrictive.
- Both are fixed in the current follow-up: SQL filters normal-user rows with `e.match=1` before LIMIT (admin remains unchanged), and the ordinary-user default max experience is now 30 years. Regression tests cover a one-row limit with a newer non-match and the permissive default.
- Full V2 suite rerun after the fixes: **209 tests passed** in **128.014s**.
- Follow-up fix commit `a1620a8` is pushed. Both Codex inline review threads were replied to and resolved. GitHub Actions CI run #1225 is running on this head: Python compile, JS syntax and focused tests have passed; full suite is currently running.

### Tests and validation
- Full V2 Python suite: **209 tests passed** in **121.559s**.
- Focused preference, API, feed, auth and dashboard contract tests passed.
- Dashboard contract suite includes the Node auth-client contract; Node 12 on the VM cannot parse the app's existing optional-chaining/nullish syntax, so app.js syntax was checked with cached esbuild 0.19.12 instead (passed).
- Python compile passed for `v2/user_preferences.py`, `v2/auth_admin.py`, `v2/radar.py`.
- esbuild syntax checks passed for `dashboard/app.js` and `dashboard/auth.js`.
- `docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml config` passed.
- Isolated Docker image build passed: `job-radar-user-preferences-radar:latest`. No container was started.
- `git diff --check` passed.
- Test coverage includes role+location gate, admin-only legacy migration, new-user no-inheritance, preferences validation, user isolation, preference-change reevaluation, per-user match scores, job detail, daily summary, and no global notification status leakage.

### Explicit remaining gaps before PR
1. Opportunity list/detail endpoints remain admin-only. Keep them hidden from normal users until tenant-scoped.
2. Add any desired additional preference controls (experience range, exclusions, remote-only) to the user form; current UI collects role, location and optional skills only. Backend accepts the full candidate preference allowlist.
3. Manual browser smoke test in the isolated feature Compose environment has not yet been performed; the image is built but the service is not running.
4. Manual tenant/security review and automated PR review are still required.
5. Open a focused PR against `v2-live-radar`; do not merge until CI/review pass.

### Exact isolated feature commands (Windows PowerShell)
The root README contains the full sequence. Key commands:
```powershell
ssh ubuntu@130.210.27.197 "cd /tmp/job-radar-user-preferences && sudo docker compose -p job-radar-user-preferences -f v2/docker-compose.feature.yml up -d --build"
ssh -L 18002:127.0.0.1:8002 ubuntu@130.210.27.197
Start-Process "http://127.0.0.1:18002/dashboard/"
Invoke-RestMethod "http://127.0.0.1:18002/health" | ConvertTo-Json -Depth 5
```
Use `ssh -t` and `docker compose exec radar python -m v2.auth_admin create-admin/create-user` to provision accounts. Password entry is interactive; never put passwords in command arguments or chat. Stop with `docker compose down` (no `-v`) to preserve the disposable DB volume.

### Current branch/runtime state
- Feature branch: `feat/user-preferences-evaluations-20261106`; base `dd7aeb1`; implementation commit `cf9d69c`, workflow commits `11476b0`/`4c0af18`, and follow-up commits `f93ab65`, `c5e11ce`, `c5201ce` are pushed. Draft PR #46 is open against `v2-live-radar`: https://github.com/AvinashBhalla/job-beeper/pull/46. CI run #1222 passed on code head `c5201ce` (compile, dashboard JS, focused tests and full V2 suite). `@codex review` was requested twice; the bot's summary still referenced `f93ab65` and remained running, so do not claim automated review completion.
- Remote branches: 7; includes this feature branch, integration/production branches, three active PR branches and the parser-fix branch. SSE branch was archived as `archive/sse-infrastructure-20261106` and removed from active branch list. Exact inventory is above.
- Existing dev `job-radar-dev` and production `v2-radar-1` were not restarted/rebuilt/modified. The image build above created only a new image; no new feature container exists.
- Existing dirty dev checkout, production checkout, old detached/dirty worktrees and draft encrypted backup remain protected as described above.

## 2026-11-06 — Beta sign-in usability follow-up

- Sign-in email is trimmed and lowercased by the API before account lookup and rate-limit identity calculation; regression test now covers leading/trailing spaces and mixed case.
- Password provisioning minimum is now 5 characters (maximum remains 1024 UTF-8 bytes). This is intentionally a beta usability choice requested by the project owner; it is weaker than the recommended 12+ character passphrase. Argon2id hashing and login throttling remain enabled.
- Sign-in form now includes an accessible Show/Hide password toggle and HTML `minlength=5`; asset query versions were bumped to prevent stale browser cache.
- Provisioning CLI prompt now reflects the 5-character minimum.
- Regression coverage accepts a 5-character password and rejects 4 characters.


## 2026-11-06 — Shared production dashboard for all account roles (PR #46 follow-up)

- Product decision: ordinary members and administrators use the existing production Job Beeper dashboard shell. The separate simplified member workspace has been removed.
- Member sessions now initialize the same Jobs Feed, Applied, Matching Preferences, Source Health, Account, navigation, filters, job inspector, and refresh controls as admins.
- Admins continue using `/api/config` and the full operational controls. Members load/save only their own `/api/preferences`; source enablement and Telegram/global operational controls remain hidden and server-protected.
- Members use `/api/source-status/summary`, which exposes enabled/running/last-success and aggregate discovery counts but deliberately omits collector errors/diagnostics. Detailed `/api/source-status` remains admin-only.
- Applied-job browser storage is now namespaced by authenticated user ID so accounts sharing a browser do not see one another's local application records. This remains browser-local (not cross-device/server-synced), matching the pre-existing dashboard behavior.
- Onboarding is integrated into the existing Matching Preferences page; incomplete users are routed there and the feed polling loop waits until target role and location are saved.
- User-specific matching criteria include target roles, locations, skills, exclusions, experience range, match threshold, max age, and remote-only preference. Source toggles and Telegram policy remain administrator-only.
- Regression coverage confirms shared dashboard shell, per-user preferences/evaluations, safe source-health access, and admin-only diagnostics. Full V2 suite: 212 tests passed; one optional Node test skipped in the Python test image. Dashboard JS syntax checks passed with Node 22.
- Shared-dashboard follow-up commit `f43cd4af27a8cc68e97b5260b233299047a34245` is pushed to draft PR #46; CI run #1228 passed. It is not merged.


## 2026-11-06 — Shared-dashboard build deployed to isolated dev

- Deployed CI-green shared-dashboard PR head `f43cd4a` to the existing isolated dev service on loopback port 8001 (`job-radar-dev`).
- Built image: `job-radar-dev-multitenant:f43cd4a`; temporary compose file: `/tmp/job-radar-dev-live.yml`.
- Preserved existing dev volume and mounted config at `/home/ubuntu/job-beeper-dev/v2/config.dev.json`; preserved its `.env` provider configuration. Telegram bot token/chat ID remain blank in dev.
- Pre-replacement SQLite backup: `/home/ubuntu/job-radar-dev-pre-shared-ui-20261106.db` (integrity ok, 8,009 jobs, 0 accounts at backup time).
- Post-start dev DB integrity ok; 8,009 jobs; auth/preferences/evaluation tables initialized; zero users pending first-admin provisioning.
- Health endpoint returned status ok. HTML served `obsidian_v4`, `auth_v3`, `shared_workspace_v1`. Anonymous `/api/source-status/summary` correctly returned 401.
- Naukri polling is active and has successful source runs; current dev config has LinkedIn disabled, Naukri enabled, and notifications disabled. Do not enable LinkedIn or notifications without explicit approval.
- Production container `v2-radar-1` on port 8000 and synthetic feature container on 8002 remain untouched.
- Next: provision first dev admin using the user's confirmed email; CLI migrates existing global candidate preferences from mounted `config.json` into that first admin. Then create a separate ordinary beta account and test same-shell UI, user-specific feed/preferences, source health, and applied-state isolation.
- Dev-only cookie settings: `JOB_BEEPER_COOKIE_SECURE=false` and empty `JOB_BEEPER_PUBLIC_ORIGIN` in `/tmp/job-radar-dev-live.yml`, so HttpOnly session cookies work through the local HTTP SSH tunnel. This override is confined to loopback-only dev port 8001; production remains unchanged and should retain Secure cookies.


## 2026-11-06 — Shared-dashboard beta feedback, SQLite contention, and open Google signup (active)

- **User acceptance:** The user signed into the isolated shared-dashboard dev deployment at `http://127.0.0.1:18001/dashboard/#preferences` and confirmed the UI looks good. They report preference saves are slow, browser console shows repeated HTTP 500s for `GET /api/jobs?minutes=4320&limit=500` and `GET /api/daily-summary`, and the login screen has no self-service sign-up. They approved open Google signup for beta, with all self-registered accounts assigned the ordinary `user` role. They asked for Ponytail code simplification while writing/refactoring.
- **Runtime evidence / diagnosis:** Read-only tail of `job-radar-dev` logs shows both endpoint failures originate in `v2/user_preferences.py:get_user_preferences()` at the per-request `INSERT ... ON CONFLICT DO NOTHING`, raising `sqlite3.OperationalError: database is locked`. Later requests succeeded (200), consistent with intermittent SQLite write contention. This is confirmed, not inferred from the browser screenshot. Dashboard `savePreferences()` currently awaits `loadJobsFeed()` after saving; that makes the save interaction wait for jobs + daily summary and couples preference persistence to feed refresh. Preference reads should be read-only; create preference rows during user provisioning instead. Evaluate short transactions, WAL/busy timeout and evaluation initialization writes before changing database pragmas.
- **Code state at start:** branch `feat/user-preferences-evaluations-20261106`, worktree `/tmp/job-radar-user-preferences`, clean at `5b68dee3b339ff99fc967028d0c98336bce8545d`. Draft PR #46 remains open against `v2-live-radar`; no merge or production deploy. Isolated dev service is `job-radar-dev` on loopback port 8001 (browser via local tunnel port 18001); production port 8000 is untouched. Synthetic feature service port 8002 is untouched.
- **Relevant current implementation:** `get_user_preferences()` in `v2/user_preferences.py` writes on every read. `dashboard/app.js:savePreferences()` awaits a complete `loadJobsFeed()` after a successful save. Login UI in `dashboard/index.html` currently only supports email/password; `dashboard/auth.js` exposes login/currentUser/logout, no registration or OAuth. Source toggles and Telegram controls are rendered in the shared Preferences form and must be hidden/disabled for normal users; global source/Telegram policy stays admin-only. Do not expose admin controls by moving them into user preference payloads.
- **Approved product direction:** open beta registration through Google OAuth (no invite requirement); every Google self-registration creates only a normal `user`. Keep password login for existing accounts; consider email/password signup only if email verification is implemented safely, not as an unverified fallback. Use server-side Google authorization-code flow with cryptographically random state, strict redirect URI, verified ID token (issuer, audience, expiry, signature via Google JWKS or a maintained OIDC library), verified email requirement, unique normalized email linking policy, and existing opaque cookie session/CSRF model. Never trust browser-supplied profile claims. Do not allow public role selection or first-admin bootstrap through signup. OAuth client ID/secret and exact callback URI are environment configuration only; never commit or print secrets. If provider credentials are not configured, show a clear unavailable state and retain password login.
- **Ponytail requirement:** read `skills://plugins/engineering-suite-ponytail/code-simplification/skill.md` before code changes. Follow its scope rule: understand call graph/tests first; simplify only touched code; preserve behavior; keep feature/bug-fix changes separate from behavior-preserving refactors; run tests after each incremental change; do not optimize line count or introduce speculative abstractions.
- **Current test/runtime evidence:** existing full V2 suite before this feedback was 212 passed, 1 skipped; JS syntax checks passed. Those results do not cover the new lock fix or OAuth. Dev container currently runs image `job-radar-dev-multitenant:f43cd4a`; source branch has later docs commits through `5b68dee`. No code fix or OAuth implementation has yet been made for this feedback. No production config, DB, service or credentials were changed. Notifications remain disabled; LinkedIn remains disabled in dev.
- **Next implementation order:** (1) inspect account provisioning, preference initialization, evaluation initialization, and relevant tests; change preference reads to SELECT-only and ensure defaults are inserted at account creation/first-admin migration; add concurrency regression coverage. (2) decouple preference save from full feed reload and show explicit saved state; preserve onboarding navigation behavior without blocking save. (3) remove member-facing admin-only source/Telegram controls from ordinary-user form; test both roles. (4) implement Google OAuth as a separate security-reviewed slice with state/nonce, ID-token signature/claims validation, account collision/linking rules, callback/session issuance, CSRF/session tests, and no admin escalation. (5) update both handovers and reference docs, run focused tests then full suite, JS syntax checks, CI; build/deploy only to isolated dev after tests pass. Keep PR #46 draft until user smoke test and review; no production deployment or merge without explicit authorization.
- **Exact current next action:** inspect `v2/auth_admin.py`, auth route definitions in `v2/radar.py`, `ensure_user_job_evaluations_initialized`, preferences form rendering and tests. Confirm how ordinary user creation and first-admin creation initialize preferences. Then implement the read-only preference getter with tests first. For Google OAuth, first check installed OIDC/JWT dependencies and repository conventions; do not hand-roll JWT signature verification.
- **Continuation prompt:** “Read the latest tail of `docs/JOB_RADAR_HANDOVER.md`, `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, and `docs/JOBBEEPER_REFERENCE.md`. Continue PR #46 on `feat/user-preferences-evaluations-20261106` in `/tmp/job-radar-user-preferences`. User accepted shared dashboard, reports slow preference saves and 500s, and approved open beta Google OAuth signup with all self-registered accounts as ordinary users. Logs confirm SQLite database lock at the INSERT in get_user_preferences; savePreferences waits for loadJobsFeed. Read and apply Ponytail skill. Fix SELECT-only preference reads/provisioning initialization first with tests, then decouple save UI, hide admin-only settings for members, and implement secure Google OIDC authorization-code flow only with proper JWT/JWKS verification. Update both handover docs after every material step. Keep PR draft, dev isolated on 8001, production 8000 untouched, notifications disabled, no secrets in chat or repo.”


## 2026-11-06 — First contention fix committed; verification pending

- **Ponytail applied:** read the code-simplification skill and traced the preference read path, provisioning CLI, API save path, and existing unit tests before changing code. Kept the change narrowly scoped and behavior-preserving for initialized accounts.
- **Code commits:** `f2b8e44` makes `get_user_preferences()` SELECT-only and adds explicit `ensure_user_preferences()` for provisioning; `537f1a3` updates the CLI ordinary-user provisioning path to initialize preferences explicitly; `3d93883` updates test account setup and adds a regression test proving reads do not create rows; `bfc55e4` moves user evaluation refresh after preference save into FastAPI `BackgroundTasks`; `77121f2` removes the frontend's await on the full feed reload after save so preference save status is not held by feed loading.
- **Expected effect:** remove the write-on-read lock contention observed in `/api/jobs` and `/api/daily-summary`; avoid synchronous evaluation refresh inside the preference PUT request; do not block the save UX on the subsequent feed request. These are code-level expected effects, not yet runtime verified.
- **Important verification gap:** Termalin SSH tool became unavailable during the edit/test attempt (agent not found). No local tests, JS syntax checks, full V2 suite, CI, container rebuild, or dev deployment have run for these commits. Do not describe this fix as tested or deployed. The dev runtime still runs its previous image until a controlled test/build/redeploy is completed. Production is untouched.
- **Follow-up still required:** audit all account creation paths (especially future Google OAuth) to call `ensure_user_preferences()`; first-admin migration already creates the admin preference row. Inspect evaluation initialization to avoid duplicate concurrent refreshes when the background task and a feed request overlap. Verify admin behavior and ordinary-user onboarding. Google OAuth is approved but not implemented yet. No OAuth dependencies are currently confirmed; inspect requirements and use maintained OIDC/JWKS verification rather than custom JWT verification. Member-only UI controls (source toggles/Telegram) still need role-conditional rendering.
- **Exact next action:** restore safe access to the feature worktree, pull the GitHub commits fast-forward, run `python -m unittest v2.test_user_preferences`, focused API tests, full V2 tests and Node syntax checks. Fix any failures before rebuilding only `job-radar-dev` on loopback port 8001. Then inspect provider dependencies and implement Google OIDC in a separate reviewable security slice.
- **PR/deployment boundary:** PR #46 remains draft against `v2-live-radar`; no merge, production deploy, notification send, LinkedIn activation, or secrets change. Keep the dev service and port 8000 production separate.


## 2026-11-06 — Contention fix verification update

- Pulled latest branch through commit `8202ba6`. Focused preference suite: **10 tests passed** in 7.398s using an isolated `docker run --network none` from image `job-radar-dev-multitenant:f43cd4a`. Python AST parsing passed for `v2/user_preferences.py`, `v2/auth_admin.py`, `v2/radar.py`, and `v2/test_user_preferences.py`.
- Full discovery attempted in the same isolated image: 166 tests executed, 1 skipped, but discovery ended with **2 import errors** because the image lacks `httpx2`, which current Starlette TestClient requires. The failures are in importing `v2.test_auth` and `v2.test_user_preferences_api`; they are environment/dependency-image errors, not assertion failures. This is not a passing full suite. Prior baseline 212/1 skipped does not cover these commits.
- The first focused run exposed a preference revision semantic regression: explicit provisioning initialized revision 1, causing the first save to become revision 2. Corrected in `8202ba6` so provisioned empty defaults start at revision 0; the focused suite then passed. This keeps the first real save at version 1.
- Host Node is too old for the existing JS optional-chaining/nullish-coalescing syntax (`node --check` failed at `??`), so it cannot validate the changed dashboard JS. Need use supported Node (project/CI or user's Node 26) for syntax checks.
- No dev container rebuild/restart/deploy occurred; port 8001 still runs the prior image. Production 8000 untouched. Next: provide correct test dependency environment (`httpx2`) and modern Node; inspect `requirements.txt`/CI dependency installation; rerun focused API/auth + full suite and dashboard JS syntax before dev deployment. Google OAuth and member role-based settings remain unimplemented.


## 2026-11-06 — Preference read fallback and full suite green

- The full test run with v2/requirements-dev.txt first exposed that tests and potential legacy accounts can exist without a preference row because some tests/accounts call auth.create_user() directly. The read-only getter now returns safe empty defaults (onboarding incomplete, version 0, no DB write) when no row exists. This preserves read-only semantics and avoids a 500 for authenticated accounts with missing preference state. Provisioning still explicitly initializes rows where appropriate.
- Commit 4369e6c: return empty preference defaults for missing rows. Commit 5e5e737: update regression test to assert defaults are returned and no row is created.
- Focused auth/preferences/API suite: 59 tests passed in 117.179s.
- Full V2 suite: 213 tests passed, 1 skipped in 162.321s using isolated docker run with pip install -r v2/requirements-dev.txt. This is local VM container evidence; CI run still to be checked separately.
- Admin-only UI settings were inspected: source toggles and Telegram alert controls are wrapped in .admin-only-setting, and applyUserAccess() sets hidden = !state.isAdmin. This is already implemented; do not duplicate it. Confirm browser member view after next dev deployment.
- Current branch now includes through 5e5e737; dev runtime remains old image and has not been rebuilt/restarted. Production 8000 untouched.
- Next: check Node syntax with a modern Node runtime (host Node is too old); implement secure Google OIDC registration using maintained Google token verification (google-auth), one-time state/nonce/PKCE, strict callback URI, verified email, identity linking by verified email, new account always role=user, preference initialization, existing opaque session cookies. OAuth config variables should be GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and GOOGLE_OAUTH_REDIRECT_URI; do not commit values. Keep sign-in button hidden/disabled until configured.


## 2026-11-06 — Google beta signup and next onboarding/Telegram phase handover

### Branch / deployment truth
- Feature branch: `feat/user-preferences-evaluations-20261106`; PR #46 remains draft.
- Google OIDC implementation and supporting tests have been pushed to this branch. Latest code before this handover update includes browser-bound OAuth state, one-time hashed state storage, nonce, PKCE S256, verified Google ID token, verified email, user-only account provisioning, identity linking, preference initialization, and shared Job Beeper session cookies.
- **Not deployed to dev yet.** Isolated dev service on loopback port 8001 is still running image `job-radar-dev-multitenant:f43cd4a`. Production port 8000 remains untouched. Do not report a push as a deployment.
- Google credentials are not configured; no live Google OAuth test has occurred. Setup is documented in `docs/GOOGLE_OAUTH_SETUP.md`. OAuth CTA is hidden unless all three env variables are valid.
- Most recent focused verification before the browser-state hardening: 60 tests passed (121.890s) across Google OAuth, auth and preference API; Node 22 syntax checks were included in that command. Re-run focused and full V2 suite on latest HEAD before deploying. A later full-suite command was started but its result was not captured in chat; verify it rather than assuming it passed.
- Existing earlier baseline: 213 V2 tests passed, 1 skipped before Google OAuth was added.

### New product requirement from owner — post-signup resume onboarding
After successful signup/login for a newly registered user, provide a guided onboarding step to upload their resume and automatically prefill matching preferences. The user must be able to review/edit every extracted value; do not force manual entry of the entire profile.

**Proposed UX and behavior**
1. New Google/password account lands in onboarding, not an empty feed. Existing accounts with completed onboarding go straight to the shared dashboard.
2. On the Matching Preferences/onboarding page, show a prominent optional resume upload control (PDF/DOCX initially; validate extension, MIME and file signature; enforce a documented size/page limit). Explain what will be extracted and how it is used.
3. Parse resume server-side. Extract candidate name (if useful), target job titles/roles, skills, years/level of experience, locations only when explicitly present, remote preference only if stated, and relevant keywords. Map only to supported preference schema fields. Never infer sensitive traits or invent preferences. Treat resume text as untrusted input, not instructions.
4. Show a structured editable review form prefilled with confidence/unknown handling. Preserve user-entered values when re-parsing. Do not silently overwrite saved preferences. The user explicitly confirms the proposed profile before it is saved through the existing per-user `PUT /api/preferences` validation path.
5. If parsing fails or no resume is supplied, retain the current manual onboarding path. User can skip upload and fill preferences themselves; upload is assistance, not a hard requirement.
6. Keep the existing role/location minimum required for feed activation, but explain missing required fields and focus the form on only those fields. Keep all other values optional.
7. Store resume files privately outside the public dashboard/static directory, keyed by user ID with randomized names and strict ownership checks. Do not expose file paths or raw resume text to other users/admin dashboard. Define retention/deletion behavior; safest beta default is delete the original after parsing unless the user explicitly opts to retain it. Do not log resume contents or extracted personal data. Add file deletion endpoint/UI if retained.
8. Add parser unit tests for PDF/DOCX, malformed/empty files, unsupported format, size limit, prompt/injection-like resume content, missing fields, and ownership/isolation. Add API tests for auth, CSRF on writes, cross-user file access denial, and preferences not being saved until explicit confirmation.
9. Prefer deterministic extraction first (text parsing + conservative rules). If an LLM is later used, send only the minimum required text, treat it as untrusted, validate output against strict schema, never let the model directly write preferences, and document provider/data retention implications.

### New product requirement — connect Telegram bot per user
On the same onboarding page, show a Telegram connection panel/link that opens the Job Beeper bot conversation. The user should be able to connect their Telegram account to their Job Beeper user account and receive only notifications matching their own preferences.

**Proposed secure linking flow**
1. UI calls an authenticated endpoint to request a short-lived, single-use link token. Store only a hash, with user ID, expiry, creation time and consumed timestamp. Token must be cryptographically random and never reused.
2. Render a deep link to the official Job Beeper bot, e.g. `https://t.me/<configured_bot_username>?start=<opaque_token>`. Bot username is public config; bot token remains server-side only. Do not invent/commit the username or token.
3. Telegram user opens bot dialogue and presses Start. Telegram sends `/start <token>` to the webhook. Validate webhook using Telegram's configured `secret_token` header (and optionally source network validation only as defense-in-depth). Consume token atomically; link Telegram chat ID to the authenticated Job Beeper user. Reject expired/replayed tokens. Never trust a user-supplied chat ID from the browser.
4. Enforce unique Telegram chat ID and one active mapping per Job Beeper user unless product owner explicitly chooses multi-chat support. Provide authenticated disconnect/relink controls and audit timestamps.
5. The same onboarding page displays connection state and offers reconnect/disconnect. Telegram linking is optional and must not block onboarding/feed access.
6. Notification delivery must be per-user: match jobs using that user's saved preferences, then send only that user's opted-in alerts to their linked chat ID. Respect per-user notification enablement, frequency/quiet hours, deduplication and opt-out. Do not route ordinary member notifications through the existing single global admin chat ID. Keep the admin/global Telegram configuration for operational alerts separate.
7. Add tests for valid link, expired token, replay, wrong/unknown token, Telegram webhook secret rejection, duplicate chat ID, cross-user isolation, disconnected user, disabled notifications, per-user matching and no duplicate delivery. Add rate limits and safe error handling.
8. Store bot token and webhook secret only in server environment. Add a documented webhook setup runbook, secret rotation procedure and dev-only test bot guidance. Never print secrets.

### Suggested implementation order for next agent
- Phase A: verify latest branch CI and all tests; inspect latest diff for OAuth state/cookie path, callback errors and Google token verification dependency in `v2/requirements.txt`. Fix before dev deployment.
- Phase B: configure a dedicated Google OAuth client for loopback dev only, after owner supplies/configures credentials privately; deploy only isolated dev port 8001 and smoke test new account, existing-email link, replay/mismatch rejection, admin/member role and preferences. Production remains off-limits.
- Phase C: implement resume parser module + upload API + private temp storage + editable review UI + explicit save + deletion/retention policy. Keep parser behind auth and per-user ownership.
- Phase D: implement per-user Telegram link-token table/API, bot webhook handler, connection UI and per-user notification dispatcher. Keep operational/global admin Telegram path separate.
- Phase E: integration tests, security review, documentation, owner smoke test. Only then discuss merge/deploy; no production deployment without explicit owner approval.

### Files to read first
- `docs/GOOGLE_OAUTH_SETUP.md` — OAuth setup and current implementation constraints.
- `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` — concise continuation notes.
- `v2/google_oauth.py`, `v2/auth.py`, `v2/radar.py`, `v2/test_google_oauth.py` — Google OIDC implementation and tests.
- `v2/user_preferences.py` — validated per-user preferences schema and defaults.
- `dashboard/app.js`, `dashboard/index.html` — shared dashboard, auth and onboarding entry points.


## 2026-11-07 — Continuation checkpoint: OAuth review and full-suite revalidation

- **Owner instruction:** continue this project in this conversation and update both handover documents with completed work, learnings and next steps before ending each task. This checkpoint records the current continuation state; no new application feature was implemented in this turn.
- **Canonical worktree:** `/tmp/job-radar-user-preferences`, branch `feat/user-preferences-evaluations-20261106`. Initial HEAD was `7a1928997ba57286c4d7d1d4955db691014d12df`; remote branch had advanced to `49389a322952a3255d15291d269f15a6bfe9ebbd` with four documentation-only commits. The first push was correctly rejected as non-fast-forward. Reconcile by rebasing the single new documentation commit on the fetched remote tip; never force-push. Reconciled and pushed documentation commit: `69d79cf9425a91fe059f91d7a415776b43b79bbf`. Worktree is clean after push. Do not switch to `/home/ubuntu/job-beeper-dev` or `/home/ubuntu/job-beeper`; the former has local config/backup/.venv files and is 66 commits behind; the latter is the stale production checkout and 613 commits behind. Preserve both.
- **Verification:** installed the declared `v2/requirements-dev.txt` into the dedicated disposable venv `/tmp/job-radar-user-preferences-venv` (not the dev checkout). Full V2 unittest discovery on the exact feature worktree completed with exit code 0: **226 tests passed, 0 failures/errors** in 130.509 seconds. This is local VM venv evidence, not a Docker run or CI run. GitHub Actions V2 CI run **#1265** for code commit `2e78e01e0979963ce4e485871ad7f26acf36e7bd` completed successfully (run ID `42189400335`). Later local commits after that code commit are documentation-only; do not misstate the run as executing the current docs HEAD.
- **OAuth review:** inspected `v2/google_oauth.py`, callback in `v2/radar.py`, `v2/auth.py`, and `v2/test_google_oauth.py`. Flow uses Authorization Code + OIDC scopes, cryptographic state/nonce, PKCE S256, SHA-256 state storage, 10-minute one-time state consumption, browser-bound HttpOnly SameSite=Lax state cookie, Google-maintained `google-auth` token verification, verified email requirement, unique Google subject mapping, normal-user-only account creation, existing session issuance, and preference initialization. HTTP redirect URI is allowed only for localhost/127.0.0.1; non-local callback requires HTTPS. OAuth CTA is gated on valid configuration. No credential values were read or printed. Existing tests cover nonce, PKCE, state replay, token verification, verified email, identity collision, disabled account and callback session behavior. No live Google OAuth transaction was tested because credentials are not configured.
- **OAuth follow-up:** callback error/cancel paths clear the browser state cookie; persisted state is cleaned by its 10-minute expiry cleanup rather than consumed on provider cancellation. This is bounded stale-row cleanup, not a demonstrated authentication bypass; consider adding a regression test that cancellation cannot be replayed into a successful callback. Recheck Google token verification behavior when upgrading `google-auth`.
- **Tool/runtime limitation:** Termalin can run host commands, but `ubuntu` is not in the `docker` group and cannot access `/var/run/docker.sock`. Do not use sudo, change socket permissions, or alter group membership to work around this. Consequently no dev container inspection/rebuild/deploy or production operation was performed. Isolated dev port 8001 and production port 8000 remain unverified in this turn and must be treated as unchanged; the last known state is dev on older image `f43cd4a`, production untouched. No Telegram notifications, LinkedIn collection or OAuth requests were triggered.
- **Current product milestone:** resume-assisted onboarding and per-user Telegram connection/notification work remain requirements only; no parser, upload API, file storage, Telegram link token, webhook, or per-user dispatcher exists yet. Existing manual onboarding and per-user preferences remain the fallback. Resume must be optional, PDF/DOCX, bounded, parsed server-side, shown as editable suggestions, and only saved after explicit user confirmation. Original files should be deleted after parsing by default unless retention is explicitly opted into; never log resume text. Telegram must use short-lived one-time hashed tokens, a verified webhook secret, browser-independent chat linking, per-user preference-matched delivery, dedupe/opt-in/disconnect, and keep admin operational alerts separate.
- **Documentation discrepancy fixed:** the top-level active branch labels were stale (`feat/multi-user-foundation-20261106`); the actual feature branch is `feat/user-preferences-evaluations-20261106`. The older sections below are chronological history, not current implementation instructions.
- **Exact next action:** (1) push the updated handover docs; (2) verify current PR #46 checks/review threads against its latest remote head; (3) begin resume support as one reviewable slice: define parser limits and deterministic extraction contract, add PDF/DOCX parsing module and tests, then authenticated upload/parse endpoint with CSRF, ownership, private temporary storage and delete-after-parse; next add editable review UI and call existing `PUT /api/preferences` only after explicit confirmation. Do not start Telegram until the resume slice is tested and documented. Keep PR #46 draft, do not merge, do not deploy, and do not touch production.
- **Continuation prompt:** “Read the latest dated sections of `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md`, plus `docs/GOOGLE_OAUTH_SETUP.md`. Continue on `/tmp/job-radar-user-preferences`, branch `feat/user-preferences-evaluations-20261106`. Full suite just passed 226/226 in the dedicated venv; CI #1265 passed for code commit 2e78e01. OAuth flow was reviewed but not live-tested because no credentials are configured. Update docs on every turn. Implement resume parser/upload/review/save first, with strict PDF/DOCX limits, private user-scoped handling, delete-after-parse by default, no silent preference writes, and explicit confirmation. Keep Telegram per-user linking after that. Docker access is unavailable to ubuntu; don't bypass it. No merge or deployment; production untouched.”


## 2026-11-07 — Resume-assisted onboarding: first implementation slice

- **Implemented (not deployed):** added `v2/resume_parser.py` with deterministic allowlisted extraction from PDF and DOCX. It suggests supported target roles, skills, explicit allowlisted locations, candidate experience years only when clearly labelled total/overall/professional experience, and `remote_only` only for explicit exclusive remote wording. Unknown fields remain empty; it does not infer a candidate's name, seniority, sensitive attributes, or admin/account permissions. Resume text is treated as untrusted data and never interpreted as instructions.
- **Input safety:** 5 MB upload cap; PDF signature check, encrypted PDF rejection, maximum 10 PDF pages; DOCX ZIP signature/structure check, 1,000-entry limit, 20 MB uncompressed limit and compression-ratio check; extraction text bounded to 100,000 characters. Extension and MIME type must agree (or MIME may be `application/octet-stream`). Parser rejects empty, malformed, unsupported and unreadable files with safe user-facing errors.
- **API:** added authenticated, CSRF-protected `POST /api/preferences/resume` accepting multipart field `file`. Only active ordinary users may use it; admins are rejected because admin candidate preferences remain on `/api/config`. The handler reads only up to limit+1, parses in memory, closes upload, stores no original file, returns only structured suggestions and missing required fields, and does not write `user_preferences`. User must review/edit and click the existing Save Preferences action, which persists via `PUT /api/preferences`.
- **UI:** optional upload panel is shown for incomplete member onboarding and hidden for admins/completed profiles. User chooses PDF/DOCX and clicks Extract Suggestions. Extracted role/location/skill tags are merged with existing tags rather than replacing user edits; experience is filled only when blank; remote-only can be enabled only when explicitly extracted. UI explains the 5 MB/10-page limits and that nothing is saved until the user explicitly clicks Save Preferences. Manual onboarding remains available.
- **Dependencies:** added `pypdf>=5,<7`, `python-docx>=1.1,<2`, and `python-multipart>=0.0.9,<1` to `v2/requirements.txt`. During editing a literal escaped newline briefly caused a malformed requirements line; it was corrected and the final file now has one dependency per line. Test venv packages installed successfully.
- **Tests added:** `v2/test_resume_parser.py` covers DOCX extraction, PDF text path (PdfReader isolated in test), injection-like text, missing fields, unsupported extension, invalid signatures, empty/oversized input and unreadable documents. `v2/test_user_preferences_api.py` covers anonymous rejection, CSRF rejection, successful suggestion response without preference persistence, invalid file and MIME mismatch. `v2/test_auth.py` route-auth inventory now explicitly classifies `/api/preferences/resume` as member-authenticated. Focused parser/API/auth route suite: **19 tests passed** in 26.016s.
- **Full-suite verification:** first full run executed 237 tests and exposed one expected route-inventory test omission for the new endpoint (the route itself was correctly protected by `require_authenticated`). Updated the route inventory test. Second full V2 suite completed with exit code 0: **237 tests passed, 0 failures/errors** in 150.197s using `/tmp/job-radar-user-preferences-venv` and `v2/requirements-dev.txt` plus the new runtime dependencies. Focused parser/API/auth route suite also passed: 19 tests. This is local VM evidence; GitHub Actions for the new commit has not yet been observed.
- **Frontend syntax limitation:** server has Node v12.22.9, too old for the existing dashboard optional chaining/nullish-coalescing syntax, so `node --check dashboard/app.js` fails at pre-existing `??` syntax and cannot validate this UI change. Python AST syntax checks and `git diff --check` passed. GitHub Actions CI uses the supported modern Node runtime and should validate JS after push.
- **No deployment:** Docker socket remains inaccessible to `ubuntu`; no dev image rebuilt, no dev or production deployment, no secrets/config changed, no notifications or collectors triggered. Production port 8000 untouched. PR #46 remains draft.
- **Known remaining scope:** this is the first deterministic parser/upload/review slice, not the full onboarding milestone. Add robust extraction fixtures for real-world PDF/DOCX layouts, page-limit/ZIP-bomb regression tests, UX validation in a browser with a modern Node/browser environment, and potentially an explicit reset/clear-suggestions action. The uploaded source file is not retained; no file deletion endpoint is needed under this default. No resume persistence/ownership table exists because no file is stored. Telegram linking and per-user notification delivery are still entirely unimplemented.
- **Commit/push:** implementation and handover changes were committed and pushed as `7065cc6abb1d2d5a2d4ccab6db2a0c8f95e85cae` (`feat: add resume-assisted onboarding suggestions`). Worktree was clean immediately after push. GitHub Actions lookup immediately after push returned no workflow run yet; check again before claiming CI status. PR #46 remains draft.
- **Next:** inspect CI for commit `7065cc6`; use a modern Node runtime for `dashboard/app.js` syntax validation; browser-smoke the resume upload on isolated dev only when an authorized Docker/deploy path is available. Add realistic parser fixtures and explicit PDF page-limit/DOCX ZIP-limit tests. After resume phase passes, implement Telegram token issuance, webhook verification/atomic consume, chat mapping/disconnect and per-user notifier. No merge or production deployment without explicit approval.
