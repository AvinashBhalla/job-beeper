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

## Current release gates — updated 2026-11-08

- **QA-001: PASS.** Final browser regression on candidate port 18005 verified member desktop/mobile Source Health hidden, direct member `#sources` redirect to Jobs, no member telemetry polling for 35 seconds, member source-health GETs returning 403, and admin desktop/mobile visibility plus API GETs returning 200. See `docs/QA/desktop-final-candidate-verification-2026-11-08.md` and `docs/QA/QA001_CSS_HIDDEN_ROOT_CAUSE_2026-11-08.md`.
- **QA-002 responsive layout: PASS.** Member/admin were measured at 1536×900, 1280×800, 768×1024, 390×844, 375×812 and 320×740. No horizontal overflow or metric overlap was reported. “Discovered” wraps below “Today” at 320px but remains visible.
- **QA-002 mobile bottom-navigation occlusion: BLOCKED.** The browser session could not provide a reliable archival obstruction rectangle or exported screenshot proving that the final content is not obscured by the mobile navigation.
- **QA-002 screenshot artifact delivery: BLOCKED.** Inline captures were taken, but no PNG/JPEG files could be exported from the browser control surface. Re-run the evidence-only portion with a capture-capable local browser harness; do not fabricate screenshot files.
- **QA-003 console smoke: PASS.** No member/admin console errors or warnings were observed.
- **Manual CSRF negative mutation checks: UNKNOWN.** No state-changing request was sent in the read-only acceptance pass.
- **Manual session/logout/expiry mutation checks: UNKNOWN.** These were also excluded by design. Automated CSRF/logout-protection tests passed in the previously recorded V2 CI run; that does not convert the manual browser checks to PASS.
- **Candidate code validation:** GitHub Actions V2 CI run `42468551208` completed successfully on `cf778c1f1da33c773f820cafea991fb084c58da8`, with 337 tests passed. Subsequent documentation-only commits must not be described as independently CI-verified until the current branch status is checked.
- **Promotion status:** no shared-dev promotion, service restart, config edit, database migration, feature-flag change, or production action has occurred. PR #51 remains draft. The existing preflight database snapshot is not a substitute for a fresh backup immediately before a future promotion.

## Updated release blockers — final visual evidence follow-up

- **320px interaction: FAIL for both roles.** At 320×740, member `Mark Applied` hit-testing returned the “Newest First” button; admin hit-testing returned `.feed-status-strip`. At 390×844 and 375×812, both roles passed. The target button rectangles are above the 56px bottom bar, whose top is y=684; exact overlay/cause is unconfirmed. See `docs/QA/desktop-final-visual-evidence-2026-11-08.md`.
- **Screenshot export: BLOCKED.** In-memory browser screenshot bytes were returned but could not be written to the requested local screenshot directory. No PNG files exist. A local Playwright runner with `page.screenshot({path: ...})` or equivalent is required.
- **QA-001 remains PASS** and responsive metric layout remains PASS. The new 320px failure is a separate hit-testing/accessibility issue and must not be conflated with the earlier layout result.
- **Manual CSRF/session mutation: UNKNOWN** as previously recorded.

## Required next actions before promotion

1. Obtain exact 320px hit-test x/y, `elementsFromPoint()` stack, bounds and computed styles for the intended and returned elements in both roles. Confirm the target button remains connected and coordinates use viewport CSS pixels.
2. Apply a minimal root-cause fix only after the diagnostic identifies the overlap or coordinate issue. Add a regression test covering the relevant DOM/CSS contract and recheck 320px, 375px and 390px.
3. Use a capture-capable local Playwright runner to export and validate PNG screenshots.
4. Decide how to close manual CSRF/session UNKNOWNs through isolated synthetic testing or owner/security acceptance.
5. Re-check CI for the latest code head and obtain explicit owner approval before any shared-dev promotion. Take a fresh online SQLite backup immediately before promotion and follow the runbook above.

Workday/SmartRecruiters remain legacy-only and Darwinbox is generic discovery only; they are not part of the six-source V2 release scope.


1. Obtain screenshot files through a capture-capable harness and archive redacted desktop/member/admin-mobile evidence.
2. Verify bottom-nav occlusion with stable geometry and hit-testing at the bottom of scrolled mobile content; retain actual measurements and screenshots.
3. Decide how to close the manual CSRF/session checks: run them only in a separately scoped synthetic QA pass, or explicitly record them as accepted release unknowns after owner/security review. Never target shared dev or production with these mutation checks.
4. Re-check CI against the final candidate code state and ensure the PR is still based on `v2-live-radar`.
5. Obtain explicit owner approval before any shared-dev promotion. Immediately before promotion, take and integrity-check a fresh SQLite online backup, preserve the live Compose/env/config invariants, build an immutable candidate image, and follow the targeted rollback procedure above.

Workday/SmartRecruiters remain legacy-only and Darwinbox is generic discovery only; they are not part of the six-source V2 release scope.
