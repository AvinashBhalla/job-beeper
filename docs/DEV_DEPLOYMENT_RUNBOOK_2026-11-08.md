# Shared Dev Promotion Runbook — 2026-11-08

## Target and boundaries

- Shared dev dashboard: `http://127.0.0.1:8001/dashboard/` (SSH tunnel only)
- Container: `job-radar-dev`
- Current rollback image: `job-radar-dev-multitenant:f43cd4a`
- External persistent volume: `job-radar-dev_radar-dev-data` mounted at `/data`
- Live compose file: `/tmp/job-radar-dev-live.yml`
- Dev config bind mount: `/home/ubuntu/job-beeper-dev/v2/config.dev.json` to `/app/v2/config.json` (read-only)
- Environment file: `/home/ubuntu/job-beeper-dev/.env` (do not print, replace or overwrite its values)
- Live data database: `/data/jobs.db`

Production port 8000, the feature service on 8002, old QA service on 8004 and candidate QA service on 8005 are separate and must remain untouched by the dev promotion.

## Preflight evidence collected

- Port 8001 health returned HTTP 200.
- Existing dev database snapshot contains 8,368 jobs, 1 user, 1 user-preferences row, 8,368 canonical opportunities, 8,368 notification-ledger rows and 7,829 source runs.
- A consistent online SQLite snapshot was copied to `/tmp/job-radar-dev-before-candidate-20261108.sqlite3`.
- Candidate `radar.init_db()` was run with `JOB_RADAR_DB` pointing only at a disposable copy of that snapshot. All listed row counts remained unchanged, canonical identity versions stayed `(2, 2)`, and SQLite `PRAGMA integrity_check` returned `ok` both before and after.
- The previous dev image tag remains locally available for rollback.
- Dev configuration has LinkedIn disabled, Naukri enabled, Instahyre/Greenhouse/Ashby disabled. Candidate V2 adds Lever as opt-in; migration forces it off. Do not turn on new sources as part of deployment.
- Telegram credentials are explicitly blanked by the live dev compose file. Keep this invariant.

The preflight snapshot is evidence, not the final deployment backup. Take a fresh backup immediately before promotion because dev ingestion may continue changing the database.

## Promotion procedure — only after explicit owner approval

1. Confirm PR #51 head and CI are green; re-check candidate SHA before building.
2. Take a fresh SQLite online backup from the running dev container to a dated host backup path. Record byte size and run `PRAGMA integrity_check` on the backup.
3. Back up `/home/ubuntu/job-beeper-dev/v2/config.dev.json` and `/tmp/job-radar-dev-live.yml` without exposing the `.env` contents. Preserve the `.env` file in place.
4. Build the candidate image from the exact candidate checkout using `v2/Dockerfile` and a unique immutable tag (for example `job-radar-dev-multitenant:f22616c`). Do not overwrite the existing rollback image tag.
5. Create a separate candidate Compose file by copying `/tmp/job-radar-dev-live.yml` and changing only the `image:` tag. Preserve the project name, container name, port binding, external named volume, config bind mount, environment file, Telegram blanking, and all current feature/LLM flags.
6. Validate the Compose file before applying it. Do not use `docker compose down` and do not remove/prune volumes.
7. Recreate only `job-radar-dev` with the candidate Compose file. Do not target production or any other container.
8. Verify `/health`, dashboard/static assets, DB integrity, row counts, auth tables, source flags and source status. Confirm collectors remain in their previous safe state and no Telegram credentials are present.
9. Ask owner to verify member/admin login and key workflows through the SSH tunnel. Do not copy production credentials into dev.

## Rollback

- Use the original `/tmp/job-radar-dev-live.yml` (with `job-radar-dev-multitenant:f43cd4a`) to recreate only `job-radar-dev`.
- Keep the external data volume attached. Do not delete it.
- Restore the pre-deploy config bind-mounted file only if it was changed; normally it should remain unchanged.
- Restore the fresh database backup only if candidate initialization caused a confirmed data/schema issue and only after stopping the dev container and validating the backup. Do not restore merely because an HTTP smoke check failed.
- Verify old-image health and row counts after rollback.

## Core-functionality status — real-data dry run 2026-11-08

- Candidate code commit: `cf778c1f1da33c773f820cafea991fb084c58da8`. Current candidate PR head may be newer because subsequent commits are documentation-only; verify exact current head/CI before promotion.
- Real-data functional report: `docs/QA/real-data-pipeline-dry-run-2026-11-08.md`.
- Using a disposable copy of the 44 MB shared-dev snapshot, candidate `radar.init_db()` preserved the existing 8,368 jobs, users/preferences, canonical opportunities, global evaluations, per-user evaluations and notification-ledger rows. SQLite integrity remained `ok`.
- Candidate recomputed all 8,368 global and all 8,368 per-user evaluations; 130 matched the stored profile. A user-role feed query returned 40 matched jobs in the previous seven days; an admin all-jobs query returned 2,193. The role-specific query was invoked directly against the existing stored profile row; this was not a real member authentication test.
- Candidate Naukri ingestion fetched one fresh public relay snapshot: HTTP 200, 318 jobs, feed age 351.46 seconds, one request/one successful page, seven new jobs. On the disposable DB the totals became 8,375 jobs/canonical opportunities/evaluation rows, with 130 matches and integrity `ok`.
- Notification delivery remained disabled. Global ledger contained 24 pending items explicitly marked “Telegram notifications disabled; awaiting future re-evaluation” and 8,351 suppressed items. No member Telegram settings/chat were enabled, no Telegram token or Gemini key was configured, and no message was sent.
- **Scope:** real-data dry run verifies the Naukri → normalize/upsert → canonical linkage → deterministic matching → feed/decision ledger path using a real shared-dev snapshot and one fresh public Naukri relay poll. It does not prove all six adapters or a candidate run against the live shared-dev volume. Historical Ashby records are present but stale/disabled in shared dev; only Naukri was actively exercised.

## Deferred UI finding — deliberately not on the critical path

- The 320px hit-test diagnostic is now complete: actual overlap is confirmed. Member card buttons sit underneath `.feed-filter-toolbar`; admin card button center is underneath `.feed-status-strip`. At 375px both contexts pass. See `docs/QA/desktop-320px-hit-test-diagnostics-2026-11-08.md`.
- Per owner priority, no UI code fix is being attempted in this phase. Treat this as a known narrow-mobile usability defect, not a blocker for a desktop/shared-dev real-data ingestion canary. Do not represent the 320px path as passing.
- Screenshot file export remains blocked by the connected browser harness; it is not a data-pipeline blocker.
- Manual CSRF/session mutation tests remain UNKNOWN (they were intentionally not run); automated CSRF/logout-protection tests pass in CI. Keep this distinction in any later release/security review.

## Recommended next push — shared dev only, not production

The core Naukri pipeline has passed a real-data dry run. The next useful step is a controlled candidate promotion to shared dev port 8001, then a live Naukri soak on the real persistent database. This has **not** happened yet.

Promotion invariants:

1. Obtain explicit owner approval before deployment.
2. Take a fresh SQLite online backup from the running `job-radar-dev` container immediately before promotion; record file size and `PRAGMA integrity_check`.
3. Build an immutable candidate image from the exact reviewed code commit; do not overwrite `job-radar-dev-multitenant:f43cd4a` rollback image.
4. Preserve `/tmp/job-radar-dev-live.yml`, project/container identity, named volume `job-radar-dev_radar-dev-data`, config mount, `.env` in place, and current Telegram-blanking invariants.
5. Keep Naukri enabled, LinkedIn disabled, Instahyre/Greenhouse/Ashby/Lever disabled, all Telegram/notification delivery disabled, and Gemini/LLM disabled. Do not expand source scope during this first canary.
6. Recreate only `job-radar-dev` (port 8001); production port 8000 and feature/QA ports remain untouched.
7. Observe at least two real Naukri scheduler cycles and compare `source_runs`, jobs added, canonical linkage, evaluation counts/matches, feed API output and notification ledgers. Confirm zero sends.
8. Only after the shared-dev soak succeeds, review a separate production promotion. Do not merge/deploy production as part of this step.

## Current operational blocker

The Termalin connection can reach the VM and read the disposable snapshot, but its `docker` command returns `permission denied` on `/var/run/docker.sock`. No `sudo`, Docker group change or permission workaround was attempted. Therefore I cannot build/recreate the shared-dev container through the current Termalin session. An authorized Docker operator/session is required for the promotion. The live shared-dev health endpoint returned HTTP 200; protected unauthenticated API calls returned 401. No live app, volume, database, config or runtime changes were made.

Workday/SmartRecruiters remain legacy-only and Darwinbox is generic discovery only; they are not part of the six-source V2 release scope.
