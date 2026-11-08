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
- Python `py_compile` and `compileall` passed. `git diff --check` to be checked before commit. GitHub CI remains required.

## Operational boundary / next gate

- No Lever board has been added to the repository allowlist. The endpoint is covered by official docs and fixtures, but no employer-specific board has been selected or live-polled.
- Lever remains disabled in both repository configs and every existing runtime via opt-out migration. No source request, database write, matching run, notification or app service restart occurred as part of this implementation.
- Next step after CI: select a small explicit board allowlist based on role/location fit, perform a bounded GET-only read-only canary of one or two boards, assess posting count, ID stability across two snapshots, location/India/remote yield, timestamp limitations and useful new-job yield. Do not enable the source or notifications based on structural API success alone.
- No production/shared-dev deployment, source activation, schedule change or Telegram send is authorized by this PR.