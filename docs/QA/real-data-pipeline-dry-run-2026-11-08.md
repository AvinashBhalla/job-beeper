# Candidate V2 — Real-data Core Pipeline Dry Run

**Date:** 2026-11-08 (Asia/Calcutta)  
**Candidate code:** `cf778c1f1da33c773f820cafea991fb084c58da8`  
**Branch:** `integration/pr46-v2-rebase-20261108`  
**Test database:** disposable copy at `/tmp/job-radar-real-data-validation/jobs.db` on `job-radar`  
**Live services:** shared dev port 8001 and production port 8000 were not modified.

## Purpose and safety boundaries

This was a candidate-code functional validation using a real shared-dev SQLite snapshot plus one bounded GET from the public Naukri relay. The original snapshot was kept separate; the candidate's schema migration, rematching, ledger updates and ingestion ran only against a disposable copy. Telegram and Gemini credentials were blank, notifications were disabled, and collectors were not scheduled. One explicit Naukri collector invocation performed one HTTP GET to the public relay. No message was sent, no real account preference was changed, and no live application/database was written.

## Real-data source snapshot

The source snapshot was copied from the existing shared-dev database before candidate deployment (44 MB, captured 2026-11-08 around 09:44 UTC). Initial read-only inspection returned SQLite integrity `ok` and:

| Table / measure | Rows / value |
|---|---:|
| `jobs` | 8,368 |
| `users` | 1 active account (administrator) |
| `user_preferences` | 1 |
| `canonical_opportunities` | 8,368 |
| `job_evaluations` | 8,368 |
| `user_job_evaluations` | 8,368 |
| `notification_ledger` | 8,368 |
| `source_runs` | 7,829 |

Source distribution: 7,547 Naukri jobs and 821 Ashby jobs. Every job had a canonical opportunity ID; at this snapshot the distinct canonical ID count was also 8,368. Ashby records were historical (latest `last_seen_at` 2026-11-05T20:13:07Z); Naukri was the active source in the shared-dev config. LinkedIn was disabled in shared dev; Instahyre, Greenhouse, Ashby and Lever were also disabled there.

## Candidate database initialization and matching

Candidate `radar.init_db()` ran against the disposable copy. Existing row counts for jobs, users, preferences, canonical opportunities, global evaluations, per-user evaluations and notification ledger remained unchanged; SQLite integrity stayed `ok`. Candidate-created per-user notification tables were present and empty.

The stored preference profile was complete (23 target-role entries, 4 locations, 18 skills; threshold 55; max age 72 hours). Actual preference values are intentionally omitted from this report. Candidate matching was forced to recompute all historical rows under the candidate matcher fingerprint:

- Per-user evaluations recomputed: **8,368**.
- Global evaluations recomputed: **8,368**.
- Per-user matches after recompute: **130** (all 130 at/above the configured score threshold).
- Global matches after recompute: **130**.
- Global alertable evaluations: **0** in this run.

The read-only feed function returned 40 matched jobs in the last seven days for the per-user query path, and 2,193 jobs in the last seven days for the admin all-jobs query path. The per-user query was exercised with user-role semantics using the existing stored profile/evaluation row; the database had only an admin identity, so this was not an authenticated login test for a newly created member account. A sample result included a canonical opportunity ID and match reasons.

## Real Naukri relay ingestion using candidate code

One candidate `run_source('naukri', config)` invocation fetched the public Naukri relay and processed it into the disposable database. Exact recorded run:

| Metric | Result |
|---|---:|
| Relay HTTP status | 200 |
| Requests / responses | 1 / 1 |
| Relay jobs in snapshot | 318 |
| Relay feed age on receipt | 351.46 seconds (~5.9 minutes) |
| Candidate freshness limit | 900 seconds (15 minutes) |
| Pages attempted / succeeded / failed | 1 / 1 / 0 |
| HTTP 4xx / 5xx / 429 | 0 / 0 / 0 |
| New jobs inserted | **7** |
| Source run outcome | **success** |

Post-run state on the disposable copy:

- Total jobs: **8,375** (Naukri 7,554; Ashby 821).
- Canonical opportunities: **8,375**; all 8,375 jobs linked to distinct canonical IDs in this snapshot.
- Global evaluations: **8,375**.
- Per-user evaluations: **8,375**.
- Per-user and global matches: **130**.
- Global notification ledger: **24 pending**, **8,351 suppressed**.
- The 24 pending decisions all state `Telegram notifications disabled; awaiting future re-evaluation`.
- Per-user notification settings enabled: **0**; linked chats: **0**; per-user notification ledger rows: **0**.
- SQLite integrity after ingestion/evaluation: `ok`.

No Telegram token or Gemini API key was configured in the test process. The collector's Naukri GET and the subsequent deterministic processing did not contact Telegram or Gemini.

## What this proves — and what it does not

**Demonstrated on real stored records and a fresh real Naukri relay snapshot:** candidate database migration on a copy; deterministic rematching; persisted user/global evaluations; member-role and admin-role feed query paths; real Naukri feed freshness validation; normalization/upsert; canonical linkage; source-run metrics; notification decision ledger with delivery disabled.

**Not demonstrated yet:** a candidate deployment running against the live shared-dev volume; a scheduler soak across multiple cycles; ingestion from the other five V2 adapters; real member authentication for a newly provisioned beta account on this database; Telegram delivery (intentionally disabled); or production behavior. Ashby is present in historical data but not currently enabled in shared dev. Do not describe the real-data dry run as a six-source canary.

## Current live environment observation

Shared-dev `/health` on port 8001 returned HTTP 200, version 2.0.0. Unauthenticated protected API requests returned 401 as expected. The Termalin shell connection could not access `/var/run/docker.sock` (`permission denied`), so container image inspection/build/recreation cannot be performed through that connection. No permission changes or `sudo` workaround were attempted. Existing shared-dev database/config/volume/container remain untouched.

## Recommendation

The core Naukri data path is sufficiently validated to proceed to a **controlled shared-dev candidate promotion and real-data soak**, not production. Before that action:

1. Obtain explicit owner approval for shared-dev promotion.
2. Use an authorized Docker operator/session to execute the runbook; do not weaken Docker socket permissions.
3. Take a fresh online SQLite backup immediately before promotion and verify its integrity.
4. Preserve the shared-dev persistent volume, Compose/env/config mounts, and existing rollback image.
5. Keep Naukri enabled, LinkedIn disabled, all other sources disabled, Telegram blank/notifications disabled, Gemini disabled.
6. After promotion, observe at least two actual Naukri scheduler cycles and verify source-run success, job deltas, canonical linkage, match/evaluation counts, API feed, and zero sends.
7. Keep production port 8000 unchanged until a separate production release review.

## UI work deliberately deferred

The 320px mobile feed overlap is now confirmed and separately documented in `docs/QA/desktop-320px-hit-test-diagnostics-2026-11-08.md`. It does not affect the demonstrated ingestion/matching pipeline. Per the owner's priority, no UI fix is being attempted in this phase; retain it as a known mobile usability defect and revisit after core real-data operation is established. Screenshot-file export also remains a browser-harness limitation, not a data-pipeline failure.