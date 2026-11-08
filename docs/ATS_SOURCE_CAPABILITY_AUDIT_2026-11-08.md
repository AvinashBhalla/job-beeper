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
