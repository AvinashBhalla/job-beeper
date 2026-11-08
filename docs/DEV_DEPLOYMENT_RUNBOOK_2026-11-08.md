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

## Current release blockers

- QA-001 CSS fix is pushed and CI-tested; browser member/admin navigation retest on port 18005 is still required.
- Manual bottom-navigation occlusion remains blocked from prior browser testing.
- Manual CSRF negative mutation tests remain UNKNOWN; automated test coverage exists and passes.
- Workday/SmartRecruiters are legacy-only and Darwinbox is generic discovery only; they are not part of the six-source V2 release scope.

No dev promotion, service restart, config edit, database migration or feature-flag change has been performed as part of preparing this runbook.
