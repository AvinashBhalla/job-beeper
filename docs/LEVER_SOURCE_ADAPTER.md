# Lever public postings adapter

**Branch:** `feat/lever-source-adapter-20261108`  
**Base:** `v2-live-radar`  
**Status:** implemented and locally validated; draft PR / GitHub CI pending; not deployed or enabled.

## Official public API contract reviewed

Source documentation: https://github.com/lever/postings-api (Lever's public Postings API documentation).

- Public GET endpoint: `GET https://api.lever.co/v0/postings/{SITE}?mode=json&skip=N&limit=Y`.
- EU public GET endpoint: `GET https://api.eu.lever.co/v0/postings/{SITE}?mode=json&skip=N&limit=Y`.
- Published postings are public; no API key is required. Internal/draft/closed postings are not accessible through this public endpoint.
- The documented list response is a JSON array. Documented data includes unique `id`, title `text`, `categories` (location/team/department/commitment/level/allLocations), `descriptionPlain`, HTML description, `hostedUrl`, `applyUrl`, workplace type, and optional salary data.
- Lever explicitly documents `skip` / `limit` pagination and both global and EU instances.
- The public Postings API does not promise a reliable publication timestamp in its documented list fields. Although a sample payload may contain `createdAt`, its semantics are not a documented published-at contract. The adapter deliberately leaves `source_posted_at` and `posted_precision` unknown instead of treating it as the employer's publication time.
- The API also exposes application submission endpoints, but this adapter never calls them. Users are directed to the original hosted posting.

## Implementation

- New collector: `lever_collect`; registry inclusion is automatic through `COLLECTORS` / `SOURCE_NAMES`, so the source appears in admin Source Health without a separate hard-coded list.
- Explicit allowlist config: `lever_boards: [{site, company, instance}]`; site slug allows only alphanumeric, underscore and hyphen; `instance` is `global` (default) or `eu`; duplicates per instance are rejected.
- Maximum 20 configured boards, maximum 5 pages per board, page size 100, 20-second timeout, no auth/API key, no POST, no automatic retry.
- Default poll target: 1800 seconds. Config version bumped to 12. Version-12 migration forces `source_enabled.lever=false` in older persisted runtimes even if an unknown prior config has Lever on.
- Both `v2/config.json` and `v2/config.dev.json` have `lever=false` and an empty `lever_boards` allowlist. Existing LinkedIn/Naukri/Greenhouse/Ashby flags are unchanged.
- Stable source ID: `lever-{instance}-{site}-{posting_id}`. Duplicate posting IDs within and across configured boards are ignored.
- Uses only HTTPS hosted posting URLs on the matching `jobs.lever.co` or `jobs.eu.lever.co` host and expected site path. If the API field is malformed or points elsewhere, constructs the canonical URL using the configured instance/site and posting ID.
- Normalizes primary/all locations, plain/HTML descriptions, list sections, team/department/commitment/level, workplace type and optional salary-range metadata.
- Every page request is measured with source-level request/page telemetry. Every board is measured. A board or later page can fail without discarding jobs from already successful pages/other boards; generic `run_source` marks mixed success/failure as `partial_failed`.
- A hard bound of five pages (up to 500 postings per site per run) prevents unbounded polling. A full fifth page emits a warning; sites with more than 500 postings require a future cursor/incremental strategy rather than silently increasing request pressure.

## Tests and validation

- 12 focused tests cover global/EU endpoints, URL allowlist/fallback, stable IDs, fields/descriptions, unknown timestamps, pagination and duplicate removal, page failures preserving earlier pages, board failures not discarding good boards, malformed payloads, empty allowlist, board validation and v12 opt-in migration.
- Full V2 suite: **227 tests passed** in 80.051 seconds in isolated Python 3.10 environment (`/tmp/job-radar-observability-venv`).
- Python `py_compile` and `compileall` passed. `git diff --check` to be checked before commit. GitHub V2 CI #42452809803 passed on commit `c8967ac140647409e735b7ea5be18ea7c92f133d`: dashboard JS syntax passed, focused router/extractor tests 32 passed, full V2 suite 227 passed in 27.508 seconds.

## Operational boundary / next gate

- No Lever board has been added to the repository allowlist. The endpoint is covered by official docs and fixtures, but no employer-specific board has been selected or live-polled.
- Lever remains disabled in both repository configs and every existing runtime via opt-out migration. No source request, database write, matching run, notification or app service restart occurred as part of this implementation.
- Next step after CI: select a small explicit board allowlist based on role/location fit, perform a bounded GET-only read-only canary of one or two boards, assess posting count, ID stability across two snapshots, location/India/remote yield, timestamp limitations and useful new-job yield. Do not enable the source or notifications based on structural API success alone.
- No production/shared-dev deployment, source activation, schedule change or Telegram send is authorized by this PR.
## 2026-11-08 — Lever URL and pagination hardening

- Added strict Lever posting ID validation (alphanumeric, underscore and hyphen; max 200 chars) before deriving canonical hosted URLs.
- Hosted URL acceptance now checks HTTPS, exact allowed Lever host and port, configured site path, no userinfo/query/fragment and no dot/backslash traversal segments. Untrusted or malformed URLs fall back to the canonical URL built from the configured site and validated posting ID.
- Added fixture test proving maximum pagination is exactly five full pages / 500 unique postings and never requests a sixth page. Added unsafe-ID skip and hosted path-traversal fallback tests.
- Focused Lever suite: 15 tests passed. Full V2 suite: 230 passed in 80.326 seconds. Python compilation and git diff --check passed locally.
- GitHub CI run 42452809803 passed on the initial implementation (227 tests); a fresh CI run is required after this hardening commit.
- Lever remains disabled with an empty allowlist in both config presets. No live board probe, source request, matching, notification or deployment.
## Read-only Drivetrain board canary — 2026-11-08

- Public Lever board slug: `drivetrain` (discovered from its public careers page; no credentials required). Public page search showed India/remote engineering and automation roles.
- A bounded, unauthenticated GET was sent twice to `https://api.lever.co/v0/postings/drivetrain?mode=json&limit=100&skip=0`, two seconds apart. Both requests returned HTTP 200.
- Both snapshots contained 35 postings and 35 unique IDs. 35/35 IDs overlapped between the two snapshots; union size was 35 and churn was zero over this two-second interval.
- Both snapshots contained 22 records with India location metadata. A deliberately broad title-keyword filter found 9 India-based technical postings (software/backend/frontend/engineer/developer/QA/SDET/automation). This is a smoke-test estimate, not the JobBeeper matcher result.
- Sample relevant roles included Backend Engineer, Frontend Engineer, SDET/QA Manager, SDE Automation & Quality, SRE and Software Engineer (Data Engineering). The official board page also exposes roles that may not match our target experience/role filters.
- The two-second interval only verifies response schema and short-term ID consistency; it is not a long-term ID-stability, publication-freshness or source-yield SLA.
- This was a read-only direct public API probe outside JobBeeper. It did not add a board to either config, enable Lever, run the collector, write to SQLite, evaluate matches or trigger notifications.
- Suggested canary site for future explicit opt-in: `drivetrain`. Keep the runtime source disabled until the first-snapshot notification baseline gate below is implemented and reviewed.
## First-snapshot notification baseline gate — required before enabling Lever

Lever's documented public list API does not guarantee a reliable source publication timestamp. Its first full import could contain many old-but-still-open postings, each with `discovered_at=now`; the current freshness logic can consequently regard them as new and queue eligible alerts. Do not activate the source or notifications until an initial-inventory baseline is handled explicitly.

Required behavior for any timestamp-unknown full-snapshot ATS source:
- The first successful complete snapshot must ingest and evaluate listings but mark those existing canonical opportunities as baseline inventory, not newly discovered alerts.
- The baseline marker must be durable across restarts and later scheduled refreshes, and must not falsify `discovered_at`, `source_posted_at` or `posted_precision`.
- Subsequent genuinely new source IDs on later successful snapshots must remain eligible for the normal matching/notification path.
- A partial or failed first scan must not mark an incomplete inventory as a complete baseline. The source must retry its baseline establishment after a successful complete run.
- The baseline logic must be source-scoped and must not suppress notifications for LinkedIn, Naukri or other already-operational sources.
- Regression tests must cover first complete baseline, repeated unchanged snapshot, partial first run, restart durability, and a new posting after baseline.

Until that gate exists, Lever remains default-off with an empty configured allowlist; the Drivetrain probe above is not an activation.