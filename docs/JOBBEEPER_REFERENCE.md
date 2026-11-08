# JobBeeper Reference: Engineering Guardrails

This document records **publicly observable JobBeeper product behavior** that we use as a reference when evolving this personal job watcher. It is not a claim about JobBeeper's private implementation.

## Reference behaviors

Based on JobBeeper's public product pages:

1. **Broad source coverage**
   - JobBeeper publicly lists LinkedIn, Naukri, Workday, Greenhouse, Lever, Ashby, SmartRecruiters, Darwinbox, Instahyre, Hirist, Cutshort and company career pages.
   - Our source roadmap should therefore prioritize source-specific adapters rather than one generic scraper.

2. **Freshness is a product feature**
   - JobBeeper says it checks sources throughout the day and sends matching jobs within minutes.
   - Public job pages expose publishing/discovery timing.
   - Our pipeline must preserve source timestamps, discovery timestamps and avoid repeatedly treating old jobs as new.

3. **Match before notification**
   - Public messaging describes matching role, location, experience and company preferences before delivery.
   - Our architecture should fetch/normalize first, then match locally, then notify.

4. **Explainable matching**
   - Public examples show a preference-match percentage and reasons such as role, location and followed-company matches.
   - Every alert should carry deterministic match reasons. AI can enrich later, but should not be required for basic correctness.

5. **Daily active-feed lifecycle**
   - JobBeeper publicly describes a live/recent feed and continuous daily monitoring, but the public pages do not establish a literal midnight deletion rule.
   - For our personal implementation, the active dashboard/feed should reset at India local midnight: yesterday's jobs leave the visible daily feed and today's counts start from zero.
   - Historical observations remain in SQLite for deduplication, alert history, auditability and analytics.

6. **Direct application**
   - JobBeeper sends the original/direct employer link and does not automatically apply.
   - We preserve canonical source URLs and never automate application submission.

7. **Company-level aggregation**
   - Public company pages aggregate roles across multiple sources (for example LinkedIn, Naukri, Instahyre, Greenhouse and SmartRecruiters).
   - Our normalized job model must support source + company identity + canonical job identity so cross-source duplicates can be merged.

8. **Newest-first feeds**
   - Public browse/company pages present newest openings first.
   - Dashboard ordering should prioritize freshness, while retaining a separate match score.

9. **Source health**
   - Public coverage spans many heterogeneous sources. Our implementation must therefore tolerate individual source failures without stopping the entire run.
   - Failed sources use persistent exponential backoff; manual runs may bypass cooldowns for debugging.

## Engineering rules for this repository

### Before changing a source
- Identify the source's best available structured/public interface.
- Prefer API/JSON feeds over rendered HTML.
- Determine pagination, freshness fields, stable job IDs and rate limits.
- Add source-specific backoff before increasing request volume.

### Before increasing polling volume
Measure:
- requests/run
- jobs fetched/run
- relevant jobs/run
- new jobs/run
- 429/4xx/5xx rate
- median discovery lag

Never increase request volume merely because a source returned zero jobs.

### Before changing matching
Check:
- title include/exclude
- geography
- remote semantics
- experience
- company rules
- posting age

Keep geography and eligibility deterministic. Do not use substring matching where it can turn "Remote - United States" into an India match.

### Before adding a new source
The adapter should expose:
- stable job ID
- canonical URL
- company
- title
- location
- posted/updated timestamp
- description where available
- source name
- source health/error

### Target pipeline

```
source registry
  -> source-specific fetch
  -> normalize
  -> canonical identity
  -> deduplicate
  -> new/changed detection
  -> deterministic preference match
  -> score + reasons
  -> dashboard / Telegram
```

## What we know vs. what we infer

**Publicly supported:** source coverage, matching concepts, freshness/discovery presentation, direct links, newest-first feeds and company aggregation.

**Inference only:** JobBeeper's exact internal crawler, database, scheduling algorithm, queues, proxy strategy, incremental cursor implementation or infrastructure. We should not copy an imagined implementation; we should reproduce the observable product properties with a simpler personal architecture.

## Current source roadmap and platform inventory

### Current status
- LinkedIn: low-volume guest search with paced requests and global stop-on-429/backoff. The labeled experience metadata regression fix is committed on v2-live-radar; await dev verification before production promotion.
- Naukri: active separate public relay, polled by the app.
- Greenhouse: adapter implemented with three configured boards; previously dry-run validated ~298 entries without writes/alerts. Disabled; next run a one-board development canary.
- Instahyre: adapter exists but is disabled; verify its live response schema, stable IDs, posting timestamps and useful yield before enabling.

### Priority 1: documented public structured ATS feeds
1. Greenhouse Job Board API. Public GET data is available without authentication: https://docs.greenhouse.io/job-board.html
2. Ashby Public Job Posting API, requires an employer board name/slug: https://developers.ashbyhq.com/docs/public-job-posting-api
3. Lever published postings API, requires an employer site: https://github.com/lever/postings-api
4. SmartRecruiters Posting API, uses an employer company identifier: https://developers.smartrecruiters.com/docs/endpoints
5. Workable and Recruitee only after confirming a permitted public endpoint; their documented API integrations may need tenant tokens: https://help.workable.com/hc/en-us/articles/115012771647-Using-the-Workable-API-to-create-a-careers-page and https://support.recruitee.com/en/articles/1066282-api-documentation

### Priority 2: job boards / aggregators
Current: LinkedIn and Naukri; Instahyre adapter exists but is disabled.
To evaluate: Cutshort, Hirist, Wellfound and Y Combinator jobs. Prefer a public/searchable feed or documented API where available; do not assume a platform has an unauthenticated global API.

### Priority 3: employer-tenant ATS platforms
Requested inventory: Ashby, Avature, BambooHR, Breezy HR, Cutshort, Darwinbox, Eightfold AI, Freshteam, Greenhouse, Hireology, Hirist, HRsmart, iCIMS, Instahyre, Jibe (iCIMS), Jobvite, Keka, Lever, LinkedIn, Naukri, Oracle Cloud Recruiting, Paycom, PeopleStrong, Phenom People, Recruitee, Rippling ATS, SmartRecruiters, SAP SuccessFactors, Oracle Taleo, Teamtailor, UKG Pro/UltiPro, Wellfound, Workable, Workday, Y Combinator and Zoho Recruit.
Many named vendors are ATS products rather than globally searchable public job boards. An adapter alone is insufficient: support requires finding real employer board URLs/tenant identifiers, allowed public endpoints, pagination and stable job IDs. Prioritize India/remote developer employers and measure useful yield rather than merely counting integrated vendor names.

### Rollout acceptance gates
For every source: identify allowed endpoint and board discovery method; stable source ID and original apply URL; posted/updated and discovered timestamps; pagination/incremental fetch; normalization/dedupe fixtures; request budgets/backoff; per-source health/error isolation; fetched/unique/new/relevant counts; matching/ledger/delivery consistency; and no historical alert replay.

### Next implementation order
1. Verify LinkedIn experience parser patch on the dev container; then promote it to main.
2. Enable Greenhouse in dev on one board only with notifications disabled; pass two-poll timestamp/dedupe/yield/backoff checks before adding boards or turning it on in production.
3. Validate Instahyre endpoint/schema/freshness in dev, then enable only if it has useful new-job yield and reliable data.
4. Add Ashby, Lever and SmartRecruiters one at a time; evaluate Workable/Recruitee public interfaces and then tenant-specific sources.
5. Improve per-source observability and continue low-pressure LinkedIn monitoring over 24-72 hours.

Do not enable every provider simultaneously, and do not use proxy/IP rotation or CAPTCHA bypass to evade LinkedIn rate limits.

## Gemini JD extraction and opt-in matcher use (development)

- `v2/gemini_extractor.py` makes bounded Gemini requests only when deterministic extraction is missing/ambiguous or skills are missing from a sufficiently long JD. It validates structured output and exact quoted evidence before caching results keyed to a hash of the current JD inputs; raw JD text is not stored in the Gemini cache.
- Extraction is still a separate cache-writing pass and does not mutate the source job dictionary directly. A distinct, network-free bridge, `cached_matcher_experience(job, conn)`, lets persisted evaluations consume a cache result only when the JD hash and configured model match, the entry is fresh (30-day success TTL), revalidation passes, the requirement is explicitly `required` and `total_professional`, exact evidence exists, confidence is at least 0.85, and at least one range bound is present. Preferred, tool-specific, ambiguous-scope, low-confidence, invalid, expired or wrong-model results fall back to the deterministic parser.
- `GEMINI_MATCHER_ENABLED` is an explicit rollout gate and defaults off. The dev Compose file passes it through with a false default. The production flag must remain off until the isolated dev pipeline is runtime-verified and the user explicitly approves production enablement.
- Extraction is also disabled by default. In dev, use `GEMINI_EXTRACTION_ENABLED=true` only after a VM-local `GEMINI_API_KEY` and the actual isolated database volume are verified. The model defaults to `gemini-3.5-flash-lite`; override it with `GEMINI_MODEL`. Never display or commit the key. Use the ignored VM-local `.env` or an exported environment variable; do not paste the secret into chat.
- Limits: at most 3 calls per source run and 20 per day by default; bounded JD length, short timeout, hash-keyed SQLite cache, short-lived error cache, strict schema/semantic validation. The matcher never calls Gemini over the network.
- `GET /api/llm-shadow-status` reports whether extraction and key configuration are present, the effective model, call counts, cache success/error counts and recent structured results. When sharing terminal output, sanitize it so no job title/ID, JD evidence text, API key, token or other secret is printed.
- The development Compose project uses a separate named volume `job-radar-dev_radar-dev-data` mounted at `/data`, with SQLite at `/data/jobs.db`. Keep Telegram credentials empty, notifications disabled and LinkedIn disabled during this validation; dev defaults enable only the Naukri relay.
- Passing tests does not prove extraction or matcher use in the running service. Verify the effective container variables, actual `/data` mount, fresh model-aligned cache result, and persisted evaluation before proposing production rollout. Do not replay historical notifications.

### Dev validation follow-up — 2026-10-12
- User-reported Gemini synthetic API smoke test passed; dev and production health were OK; notifications were disabled; 3/20 daily calls were used with 3 successful cached results.
- The full test suite failed because \`v2/test_gemini_extractor.py\` contained a malformed mock response literal. Fixed in commit \`7941a99129614ffb03a7406e8fd002e1535fb05d\`.
- Prompt clarified experience scope; role/domain experience without explicit overall-vs-tool scope should be \`unknown\`. Commit \`def76ed2fe1f181b8501f25c09098161ef669b87\`.
- Rerun the full test suite on dev before any further evaluation. Keep feature shadow-only and notifications disabled.


## Greenhouse two-poll development canary

- Utility: `v2/greenhouse_canary.py`; tests: `v2/test_greenhouse_canary.py`.
- Run from the repository root with an explicit single public board token and company label:
  `python -m v2.greenhouse_canary --board-token <board-slug> --company "<company>" --interval-seconds 900`
- It performs two GET-only polls through the existing Greenhouse collector, separated by 15 minutes by default (minimum allowed interval 60 seconds). It reports job counts, unique/stable/new/missing source IDs, and known/unknown publication timestamp coverage.
- It does not read or write the radar database, run matching, change source enablement, or send notifications. A successful report is evidence for that board and those two snapshots only; it does not authorize enabling Greenhouse in the scheduler or production.
- Keep the development config's `source_enabled.greenhouse` false while using the utility. Choose one board from the existing dev config; do not add or activate boards for this test.
- Acceptance review: check request success, stable ID behavior, duplicate counts, timestamp coverage, useful job yield, and any board errors; retain the JSON report. Repeat or investigate before considering scheduler activation.


## Optional multi-provider LLM router
- Runbook: [LLM_PROVIDER_ROUTER.md](LLM_PROVIDER_ROUTER.md).
- Implementation: `v2/llm_router.py`, integrated with the shadow extractor in `v2/gemini_extractor.py`.
- Providers supported: Groq, Gemini, OpenRouter, NVIDIA NIM. Router is opt-in with `LLM_ROUTER_ENABLED=false` by default; provider-specific model IDs and keys are supplied through the VM-local Compose environment, never committed.
- Keep `LLM_ROUTER_MATCHER_ENABLED=false` while reviewing routed extraction output. Telegram notifications remain disabled. Mocked tests were added but have not yet been executed; verify focused and full test suites after pulling before rebuilding the development container.


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


## Historical handoff — 2026-10-16 — Router review / rollout update (superseded by the 2026-10-28 validation below)
- Multi-provider router code reviewed on `v2-live-radar` head `b635b8969247c483bdfae7c2c9d0cb9a38895a61`. CI run [38934696862](https://github.com/AvinashBhalla/job-beeper/actions/runs/38934696862) succeeded with full V2 unittest discovery. This is not a VM-local execution and does not prove live provider/model/account compatibility.
- Legacy Gemini-only behavior is retained when `LLM_ROUTER_ENABLED=false`; router mode uses the strict extractor validator for each provider attempt. Cache identity excludes secrets and routes are still hard-matcher gated by default.
- Keep run/day LLM limits described as **job** limits, not total HTTP/token/cost limits. Fallbacks can attempt multiple providers for one job. No live requests, secrets, database schema change, container restart or production change is authorized by the CI result alone.
- Review limitation: direct request/response mocks are missing for Gemini/OpenRouter/NVIDIA and some aggregate error/budget cases. VM focused and full-suite test execution remains a required next step before rebuilding dev.

 
## 2026-10-28 — Multi-provider router hardening and CI validation

- Router error logging now accepts only allowlisted, stable validation error codes; arbitrary validator exception text is mapped to invalid_result to avoid leaking job descriptions, evidence or private content.
- Added mocked provider parsing/fallback/error-redaction tests and a per-run job-budget integration test. The test workflow now runs the focused router/extractor modules before full V2 discovery.
- [CI #40651562286](https://github.com/AvinashBhalla/job-beeper/actions/runs/40651562286): focused tests 32 passed in 0.061 seconds; full V2 suite 134 passed in 17.009 seconds. This is CI evidence only, not VM or live-provider validation.
- Keep LLM_ROUTER_ENABLED=false and LLM_ROUTER_MATCHER_ENABLED=false until a separate rollout is approved. Keep Telegram credentials blank and notifications disabled; no VM, DB, named volume or production-like service was changed.
- Next: read-only inspect/fetch of /home/ubuntu/job-beeper-dev and explicit ahead/behind/path assessment before any fast-forward. Preserve local v2/config.json, .venv/, .env, and job-radar-dev_radar-dev-data.


## 2026-11-07 — Current-system comparison and browser evidence required

The public product claims remain reference points, not verified implementation details. The latest read-only audit is in `docs/INGESTION_FIRST_ROADMAP.md`. In brief: our current code has five collectors, production enables two, shared dev enables one; LinkedIn is receiving repeated HTTP 429 responses; Naukri is a five-minute external relay with date-only posting dates. We cannot currently claim parity with JobBeeper's breadth or freshness.

Next reverse-engineering pass should use the user's authorized logged-in browser session to capture sanitized Network metadata for initial load, background refresh, filters, pagination, job detail loading, timestamps and source labels. Record observed facts separately from inferences. Do not extract private backend code, replay authenticated endpoints, expose session tokens, bypass access controls or evade rate limits. The evidence report belongs in `docs/JOBBEEPER_NETWORK_EVIDENCE_YYYY-MM-DD.md`.

The product priority remains ingestion reliability and source expansion. However, on 2026-11-07 the owner explicitly asked to continue existing authentication, resume-parser and Telegram feature work in parallel on isolated PR #46 while the JobBeeper browser/network investigation proceeds. Keep that branch draft and isolated; do not merge or promote it until explicit approval and release gates. The ingestion-first strategy still governs production priorities.


## 2026-11-07 — Parallel feature work confirmation

- The owner's Codex `@Chrome`/CDP JobBeeper network investigation is a separate workstream. Await its sanitized report/HAR; do not claim private backend behavior from frontend network evidence.
- Continue auth/Google signup, resume parser and per-user Telegram feature development on `feat/user-preferences-evaluations-20261106` in parallel. PR #46 stays draft.
- Current checkpoint: commit `51db2f9`, CI run `42370884022` green; isolated full suite **272 passed, 1 skipped**. Dedicated Telegram dev bot and public HTTPS webhook E2E remain pending.
- Keep shared dev (8001) and production (8000) untouched absent explicit approval.


## Authenticated browser evidence — 2026-11-07

See JOBBEEPER_NETWORK_EVIDENCE_2026-11-07.md for the full sanitized request inventory and observation windows. This section supplements the public product reference above; it does not reveal or establish JobBeeper's private backend design.

Observed in the owner's authenticated browser: browser-fetched list API with numeric page and page size 20; server-requested keyword search; separate metadata and tracker requests on detail open; a view-marking POST; source labels LinkedIn, Ashby, Naukri, Lever and Hirist; and experience provenance labels for employer-stated vs description-derived values. Ten minutes of idle observation in an expired-subscription account produced no feed-related Fetch/XHR, WebSocket or SSE events. Active-account refresh behavior remains unknown.

Implications for this repository: implement stable server-side pagination; preserve experience provenance; keep source-posted and discovered timestamps distinct; measure each source's unique-job yield; and avoid adding detail-tracker endpoints without a user-facing requirement. Current local code already has server-side keyword search, newest-first ordering and separate source-posted/discovered timestamps, but still loads up to 500 jobs in one request and does not expose numeric page metadata. The dashboard feed refresh cadence has been reduced from 10 seconds to 60 seconds while visible.
