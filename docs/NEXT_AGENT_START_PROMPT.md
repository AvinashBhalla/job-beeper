# Next-Agent Start Prompt — Personal Job Intelligence Agent

Copy the prompt below into the next ChatGPT/Claude/Codex session. It is written to resume the project from the current repository and runtime state without making the user repeat the history.

---

## PROMPT

You are taking over engineering work on my **Personal Job Intelligence Agent / Job Radar V2**. Continue from the existing implementation; do not restart the project or redesign it from scratch.

### 1. First read these files in this order

Repository: `AvinashBhalla/job-beeper`

Working branch: `work/job-intelligence-foundation`

Read:
1. `docs/JOB_RADAR_HANDOVER.md` — authoritative chronological technical handover and latest production/dev audit. Read the latest dated sections at the end first, then review relevant earlier sections.
2. `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` — condensed continuation notes.
3. `docs/INGESTION_ARCHITECTURE.md` — current V2 and target ingestion architecture.
4. `docs/JOB_INTELLIGENCE_AGENT_PRD.md` — product goals, non-goals, requirements and acceptance criteria.
5. `docs/SOURCE_INVENTORY.md` — current adapters and candidate sources.

Use repository/Files tools to inspect actual code. Do not rely solely on this prompt or older summaries.

### 2. Product goal

Build a reliable, personal, single-user job intelligence system which discovers relevant vacancies across 20–30 permitted sources, normalizes and deduplicates them, matches them to my profile, and sends timely Telegram alerts.

Existing V2 is the base: FastAPI, SQLite, Docker on an Oracle VM, collectors, canonical opportunities, deterministic evaluation/matching, notification ledger, Telegram delivery and dashboard APIs.

Later goals:
- Referral intelligence: find relevant employees/recruiters for a job using permitted data sources and prepare referral outreach for my manual approval.
- Public hiring-post intelligence: identify public posts that indicate hiring, extract role/company/post URL and connect them to canonical job records.
These later capabilities must not compromise the core ingestion and notification pipeline.

### 3. Current Git and PR state

- Work only on `work/job-intelligence-foundation` for this continuation unless you explicitly create a new branch from it.
- Draft PR #37: https://github.com/AvinashBhalla/job-beeper/pull/37
  - Title: “Draft: establish job intelligence architecture and fix source observability”.
  - It contains architecture/PRD/source-inventory docs and a narrow fix making source-status, latency-summary and dedupe-candidates derive sources from the collector registry rather than hard-coded lists.
  - Three regression tests were added for source-status completeness, Ashby latency inclusion and Ashby dedupe inclusion.
  - The full V2 suite previously passed: 137 tests, plus Python compilation and focused Gemini/router tests.
  - It is a draft, not merged and not deployed. Re-check the latest PR head and CI because documentation commits have been added after the initial test run.
- Existing draft PR #35 (Gemini shadow extraction validation) is separate. Do not merge, rebase into, or deploy it as part of this work.
- Do not modify `v2-live-radar`, `main`, production runtime or development runtime from this task.

### 4. Oracle runtime audit — established facts

Two API instances were healthy at the time of the audit:
- Production: `127.0.0.1:8000`, version 2.0.0.
- Development: `127.0.0.1:8001`, version 2.0.0.

Git checkouts:
- Production `/home/ubuntu/job-beeper`: clean `v2-live-radar`, commit `61d8271480eaf48b0a6442b62b1b0bb9a032df34`, dated 2026-10-12, 19 commits behind origin.
- Development `/home/ubuntu/job-beeper-dev`: `v2-live-radar`, commit `296c1a4d261d4a6fe7b3dc2c791c7d159f9cb135`, dated 2026-10-16, 8 commits behind origin. It is dirty:
  - modified tracked file: `v2/config.json`
  - untracked: `.env.save`
  - untracked: `.venv/`
  Preserve all of this. Never pull/reset/clean/switch over/rebuild from these VM checkouts.

Docker containers / ports:
- `job-radar-dev`, image `job-radar-dev-radar`, running, port 127.0.0.1:8001 -> container 8000.
- `v2-radar-1`, image `v2-radar` (docker ps abbreviated image ID `97368934ed14`), running, port 0.0.0.0:8000 -> container 8000.
- Separate Docker data volumes:
  - dev: `job-radar-dev_radar-dev-data:/data`
  - prod: `v2_radar-data:/data`
- Dev also has a mount at `/app/v2/config.json`; the host-side source path was not shown by the earlier inspect format. Use read-only inspect with `Type`, `Source`, and `Destination` if it matters.
- Container/database inspection required `sudo docker`; it then succeeded. Do not change Docker socket permissions or add users to the docker group.

Runtime config/API snapshots:
- Production: config v10; LinkedIn and Naukri enabled; notifications enabled. Poll targets: LinkedIn 180 sec, Naukri 300 sec, Instahyre 600 sec, Greenhouse 900 sec. API source view did not include Ashby because it runs older code.
- Development: config v11; Naukri only enabled; LinkedIn/Instahyre/Greenhouse/Ashby disabled; notifications disabled.
- Production API: daily summary for 2026-11-05 Asia/Kolkata reported 450 discovered, 30 matched, 30 alertable, 30 sent.
- Development API: daily summary reported 153 discovered, 4 matched, 0 alertable, 0 sent.
- Production LinkedIn last-success snapshot: 10 jobs seen, zero new; no cooldown timestamp was reported at that instant. Production Naukri last run: 341 seen, zero new. Dev Naukri: 339 seen, zero new.
- Historical 24-hour production LinkedIn latency summary: 363 minute-precision samples; p50 1,740 seconds (29 minutes), p90 14,400 seconds (4 hours), max 21,600 seconds (6 hours); 17 <=60 sec, 25 <=120 sec, 57 <=300 sec. The metric is posting-to-discovery latency for records whose timestamp precision is minute. It is not request latency. Do not attribute all delay to scheduler cadence; source-side indexing and target rotation may contribute.
- Naukri latency samples = 0 because its relay records date-only posting precision and the app does not invent second-level timing. This does not mean the Naukri collector failed.
- Current API health snapshot did not expose persistent historical 429 counters; no cooldown at snapshot time is not proof that no prior 429s happened.

SQLite counts: the user's message included TWO consecutive count outputs with slightly different numbers. Preserve this inconsistency; do not silently choose one as definitive. The later/second output was:
- Dev: DB 33,046,528 bytes; 7,134 jobs; 7,134 canonical opportunities; 7,134 evaluations; 7,134 ledger rows; 7,026 source runs; 500 Gemini shadow-cache entries; all 7,134 jobs from Naukri; notification ledger: 18 pending, 7,116 suppressed.
- Prod: DB 67,719,168 bytes; 19,751 jobs; 19,442 canonical opportunities; 19,751 evaluations; 19,442 ledger rows; 20,495 source runs; jobs: LinkedIn 11,759, Naukri 7,992; notification ledger: 10 failed, 1,378 sent, 18,054 suppressed.
The immediately preceding output reported dev jobs 7,152 and prod jobs 19,795, with corresponding larger DB sizes and counts. The snapshots lack timestamps. A repeated read-only count may be run if exact current values matter; do not infer data loss/pruning without evidence.

### 5. Static V2 collector baseline

Current `COLLECTORS` registry: LinkedIn, Naukri, Instahyre, Greenhouse, Ashby.

- LinkedIn: code currently calls the public guest jobs search endpoint. 4-second minimum spacing between LinkedIn HTTP requests; 180-second scan target; 4 query families x 4 locations = 16 target combinations; only 2 targets per scan; one JD enrichment worker; deep scan every 30 minutes; escalating cooldown 5/10/20/30 minutes while respecting Retry-After. At clean cadence, full target rotation is about 24 minutes. This is scheduling arithmetic, not an end-to-end freshness guarantee. No rate-limit immunity is claimed.
- Naukri: application consumes a separate relay JSON feed; acquisition occurs outside the API process.
- Instahyre: direct adapter exists but disabled by tracked prod/dev defaults.
- Greenhouse: public Job Board API adapter exists with a small board allowlist, disabled by defaults.
- Ashby: public Job Posting API adapter exists with a small board allowlist, disabled by defaults.
- Scheduler is currently an in-process loop. Due collectors are sent through threads; per-source overlap guards and cooldown/cursor state are in memory. Source-run summaries persist but request-level telemetry and durable scheduler state are incomplete.
- SQLite includes jobs/source observations, canonical opportunities, evaluations, notification ledger, source_runs and optional Gemini shadow cache.
- Telegram delivery uses a persistent ledger/retry mechanism.

### 6. JobBeeper reverse-engineering conclusion

Public evidence is sufficient to stop open-ended reverse engineering:
- Homepage public pulse uses `GET /api/public/pulse`; public feed is pre-collected/cached.
- Public live feed frontend source has a 90-second refresh interval plus refresh-on-visibility behavior.
- Hiring-this-week public page shows a Latest 20 snapshot.
- Role-category public page shows up to 200 cards and client-side search; after entering Cognizant, 199 preloaded cards were hidden and one remained visible.
- Backend category page has a separate location form, but its submission behavior has not been tested.
- Browse/company/job detail routes are HTML-first in captured HARs; no same-origin JSON API calls appeared in those bounded captures. Service-worker involvement was observed.
- Public JobBeeper evidence does NOT disclose its private scheduler, workers, LinkedIn access arrangement, database, licensed feeds or rate-limit strategy. Do not claim we know its secret.
- Do not spend more time on REA unless a specific implementation question cannot be resolved from our own code or documented provider APIs.

### 7. What to do next — continue engineering autonomously

First, inspect the latest branch/PR #37 and run/check CI. Documentation commits happened after the original passing run; confirm current head is green before relying on that result.

Then implement a **small, tested, incremental observability/scheduler foundation**. Recommended order:

1. Review current code in `v2/radar.py`, `v2/test_radar.py`, adapters, SQLite migrations, API response models and compose files on the foundation branch.
2. Keep the source registry authoritative for all source enumeration. Check the PR #37 changes and tests for correctness; do not deploy.
3. Design and implement source/run telemetry without changing request frequency:
   - run ID and source ID
   - trigger/scheduled time/actual start/finish/duration
   - pages/boards/targets attempted and completed
   - request count and per-status counts (2xx/3xx/4xx/429/5xx), timeout count and Retry-After
   - fetched/parsed/rejected/new/updated/duplicate counts
   - partial success vs complete failure
   - sanitized error category (no tokens, cookies, response secrets)
   - per-query target last attempted/last successful/last error
   - source last success, next due time and cooldown state where practical
4. Ensure an exception from one source never stops other sources. Ensure a 429 is retained in status and does not become an opaque generic error. Persist rate-limit/cooldown state across process restart only after migrations and recovery behavior are tested.
5. Add scheduler jitter, durable leases or persisted next-run state only as a small, backward-compatible change. Existing deployment is single VM/single app process; do not prematurely introduce Kafka, Redis, Kubernetes or a distributed worker fleet.
6. Add tests for 429/Retry-After, cooldown persistence/restart, same-source overlap prevention, partial board success, API enumeration for every registry source, and no secret leakage.
7. Select ONE next ATS adapter only after validating current public documentation, access terms, stable IDs, timestamps, pagination and usefulness for my likely target employers. A dev-only canary must have a small board allowlist and notifications disabled. Existing Greenhouse/Ashby adapters may be evaluated before introducing a new source family.
8. Preserve the existing production and dev VM checkouts. Do not use them as development worktrees. Use GitHub branches/PRs or a separate local checkout.
9. Run CI and the full V2 test suite after each coherent slice. Use draft PRs until reviewed.
10. Do not change live poll intervals, enable additional live sources, send Telegram tests, or deploy until I explicitly review the plan and test results.

### 8. Hard safety / access rules

- Respect every source's terms, documented API requirements, access methods and rate limits.
- Do not bypass login/access controls/CAPTCHAs, use proxy or account rotation, or circumvent LinkedIn rate limits.
- LinkedIn is optional and isolated until a permitted access arrangement is established. A source failure must not stop other connectors.
- No automated applications, LinkedIn connection requests or messages. Referral suggestions/drafts require my approval.
- Never print, commit or expose `.env`, `.env.save`, Telegram tokens, API keys, cookies, config tokens or environment dumps.
- Never delete or overwrite the dev checkout's modified `v2/config.json`, `.env.save` or `.venv/`.
- No `git pull`, `reset`, `clean`, checkout over user files, Docker compose down/up/rebuild/restart, DB migration, scan trigger or production deployment unless I explicitly authorize it after reviewing the plan.

### 9. Working style

- Be proactive: inspect repository code, propose a bounded change, implement it on the safe branch, add tests, run CI and report concrete results.
- Do not ask me to repeat facts already in these documents.
- Ask for manual commands only when access to my Oracle VM/Windows machine is genuinely required.
- Before any operation that could change production, data, credentials, or notifications, stop and ask for explicit approval.
- Distinguish observed facts, code facts, assumptions and recommendations.
- Keep both handover documents updated after meaningful milestones.
- The immediate goal is reliable ingestion/observability and one validated ATS canary—not a large rewrite and not more JobBeeper browsing.

Start by confirming the current Git branch/PR head and reading the latest handover. Then continue with the next small engineering slice.


---

## Continuity note — 2026-11-05

For the most portable fresh-chat handoff, use `docs/AGENT_CONTINUATION_PROMPT.md` and paste the latest sanitized command output directly after it. Then read the latest dated entries in both handover documents before editing.

Current PR/CI verification when this note was written:
- PR #37: open, draft, unmerged; base `v2-live-radar`; head `work/job-intelligence-foundation`.
- Head: `bbe98e33a3e131d8d63c753623d384e6ac01ced4`.
- Latest V2 CI for that exact head: run #1125 / ID `42074147311`, completed successfully.
- No application/runtime change or deployment occurred during this documentation update.
- Continue to append new evidence to `docs/JOB_RADAR_HANDOVER.md` and `docs/JOB_RADAR_KNOWLEDGE_TRANSFER.md` on every turn.


---

## Latest engineering continuation — 2026-11-05

A separate source-run telemetry slice is in progress on child branch `work/source-run-telemetry`, based on foundation commit `851fc4d857e7fa811e5a687f6e72fbf02e3125d7`. It extends SQLite `source_runs` with run IDs, outcomes, durations, error type, HTTP status, Retry-After and cooldown metadata; detects LinkedIn 429 even when partial jobs are returned; preserves runtime cooldown state; sanitizes stored errors; and exposes the new fields through `/api/source-status`. Tests were added for legacy schema migration, source status output and partial 429 results. Verification is still pending. Read the latest section of `docs/JOB_RADAR_HANDOVER.md`; open draft PR #38 into `work/job-intelligence-foundation` to run CI. Do not change polling or deploy. The generic fresh-chat prompt is `docs/AGENT_CONTINUATION_PROMPT.md`.


## Verification checkpoint — 2026-11-05

The first source-run telemetry slice has now passed V2 CI. Validation-only PR #39 run #1136 / ID `42078168015` passed on code/test commit `997235c658177b17fc2f9257e039d171841e617b`; syntax, focused router/extractor tests and full suite **141 tests in 17.071s — OK**. Earlier failed runs #1134/#1135 exposed test fixtures which are now fixed. PR #38 remains the actual draft implementation PR targeting `work/job-intelligence-foundation`. PR #39 is only a CI validation vehicle to `v2-live-radar` and should be closed unmerged. Read the latest handover section for exact history. Application/runtime behavior, VM, DB, Docker, polling, source enablement, Telegram and deployment remain unchanged.
