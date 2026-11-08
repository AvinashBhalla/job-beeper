# ATS Source Capability Audit — 2026-11-08

## Scope and interpretation

This audit distinguishes the active V2 application's collector registry from the older single-user/legacy job watcher, public-index discovery, config snapshots and historical collected records. A platform name in a config file, saved `source_state.json`, dashboard data or domain list does not by itself prove that V2 has a dedicated working collector.

## Active V2 collector registry

`v2/radar.py` registers exactly six sources in `COLLECTORS`:

| Source | V2 adapter | Default in `v2/config.json` | Notes |
|---|---|---|---|
| LinkedIn | Yes | Enabled | Request pacing/backoff safeguards present |
| Naukri | Yes | Enabled | Relay/collector ingestion |
| Instahyre | Yes | Disabled | Registered adapter |
| Greenhouse | Yes | Disabled | Public Job Board API adapter, explicit board allowlist |
| Ashby | Yes | Disabled | Public Job Posting API adapter, explicit board allowlist |
| Lever | Yes | Disabled | Public Postings API adapter; global/EU instance, bounded board/page limits; repository board list currently empty |

Repository defaults are not the candidate QA runtime configuration. The isolated candidate QA service deliberately overrides all collector flags to disabled and has no external collector credentials.

## Other platform references found

| Platform/source | What exists in repository | V2 status | Assessment |
|---|---|---|---|
| Workday | Legacy `job_watch.py` adapter using tenant-specific CXS endpoints; several configured public tenants | Not in `v2/radar.py` registry | Legacy integration only; prior saved source state contains HTTP 422 failures for some tenant/site combinations. Requires V2 port, tenant validation and live canaries. |
| SmartRecruiters | Legacy `job_watch.py` adapter using `api.smartrecruiters.com` postings endpoint | Not in V2 registry | Legacy integration only; needs V2 isolation, tests and live canary. |
| Darwinbox | Domain/platform recognition in `web_job_discovery.py` generic search-index discovery list | No dedicated V2 collector | Discovery hint only, not a structured adapter or guaranteed source ingestion. |
| Workable | Legacy `job_watch.py` adapter | Not in V2 registry | Legacy integration only. |
| Remotive, RemoteOK, Arbeitnow | Legacy flag-source functions in `job_watch.py` | Not in V2 registry | Legacy integration only. |
| Avature, BambooHR, Cutshort, Eightfold, Hirist, iCIMS, Keka, PeopleStrong, Recruitee, SAP SuccessFactors, Teamtailor, UKG, Zoho Recruit and others | Domain entries in `web_job_discovery.py` | No dedicated V2 adapters identified | Generic indexed-page discovery targets only; coverage/completeness and reliable structured extraction are not established. |

## Release recommendation

The current multi-user V2 candidate can be considered a six-source V2 release, subject to QA and deployment gates. Do not describe Workday, SmartRecruiters, Darwinbox or generic discovery domains as completed V2 adapters.

Recommended expansion order:
1. Migrate SmartRecruiters into V2 with config validation, source health, dedupe/freshness behavior and tenant-isolation-compatible ingestion.
2. Port Workday with per-tenant canaries. Treat the observed HTTP 422 tenant/site failures as unresolved until individually validated.
3. Evaluate Darwinbox by identifying the public job listing mechanism for specific employer tenants; build a structured adapter only where a stable public endpoint/schema is proven.
4. Decide separately whether Workable, Remotive, RemoteOK, Arbeitnow and additional generic discovery platforms merit migration.

No source should be enabled just because its adapter is merged. New sources stay opt-in until a bounded, read-only canary validates endpoint behavior, normalization, duplicates, timestamps, source health and failure handling.

## 2026-11-08 follow-up — Keka/Darwinbox connector candidate (isolated worktree)

An uncommitted candidate feature branch at `feat/darwinbox-keka-20261108` now contains dedicated Keka and Darwinbox V2 collectors, company-board discovery/probe support, admin activation mapping, opt-in config fields and focused regression tests. This changes the **candidate code status**, not the production status. The production container is still on build `7b1a80d`; Keka/Darwinbox are not in that image and are not production-enabled.

- Keka public Bridgestone tenant: endpoint probe HTTP 200, 109 postings. Two `run_source` polls on a disposable SQLite DB gave 109 baseline jobs then 0 new; notifications disabled; integrity `ok`.
- Darwinbox JG Summit candidate endpoint: endpoint probe HTTP 200, 18 postings. Two `run_source` polls gave 18 baseline jobs then 0 new; notifications disabled; integrity `ok`. This proves this employer endpoint only, not universal tenant coverage.
- Full local V2 suite on the candidate: 387 passed, 215.671s, zero failures. Python compile, config JSON and diff checks pass.
- Remaining release gates: push the final worktree SHA, pass exact-SHA GitHub CI, do admin browser QA on an isolated feature environment, review redirect/SSRF behavior and measure live request latency. Both source switches remain false by default.
