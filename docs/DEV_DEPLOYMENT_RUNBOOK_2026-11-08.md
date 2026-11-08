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


## 2026-11-08 — Owner-approved promotion execution attempt

Owner explicitly approved shared-dev promotion. Candidate PR head before this record was `e299efdb228b4a05fdc106a0e5e70b9344adf607`; V2 CI run `42471400933` passed against that exact head. The candidate real-data Naukri dry run is recorded in `docs/QA/real-data-pipeline-dry-run-2026-11-08.md`.

**Execution is blocked, not completed.** The only available Termalin shell runs as `ubuntu` (uid 1001), is not in the Docker group, and cannot access the `root:docker` mode-0660 socket. `docker ps` returns permission denied. No sudo, Docker group change or socket permission modification was used. The repository has no self-hosted deploy runner/workflow. The configured Termalin backup is an unconfirmed DRAFT; the previous 09:44 UTC snapshot is too old to serve as immediate pre-promotion backup.

Live health reads returned HTTP 200 on shared dev port 8001 and production port 8000. No new backup, candidate image build/load, container restart, config/volume/DB mutation, collector-flag change, merge or deployment occurred. Production is untouched.

Full execution record: `docs/QA/shared-dev-promotion-execution-2026-11-08.md`.

**Handoff:** resume only from an existing Docker-authorized operator session. Take a fresh SQLite online backup from the live shared-dev volume immediately before promotion, preserve the current volume/compose/env/config/rollback image, keep Naukri-only ingestion and Telegram/Gemini off, recreate only shared dev, then verify and observe at least two Naukri cycles. Do not ask the user to paste credentials into chat.
Additional check: the existing `job-radar-sqlite-snapshot.service` last succeeded at 02:45:43 UTC (dev snapshot integrity `ok`, 8,333 jobs then), which is too old for this promotion. A non-privileged `systemctl start --no-block` request was denied with `Interactive authentication required`; no new backup was created.

## 2026-11-08 — Oracle VM sudo and candidate image access correction

**This section supersedes the earlier assumption above that the connected `ubuntu` account could not use sudo.** The earlier checks tested Docker and systemd without sudo; they did not establish that the account lacked administrative authorization.

The owner checked the existing SSH account on the Oracle Cloud VM with:

```bash
sudo -n -l
```

The host returned:

```text
User ubuntu may run the following commands on job-radar:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: ALL
```

Therefore the existing SSH-key-only `ubuntu` login has full passwordless sudo authorization. A second SSH account or account password is not required for these privileged operations. The Docker socket is still not directly accessible to plain `ubuntu`; invoke Docker with `sudo` (for example, `sudo docker ps`, `sudo docker build ...`, and `sudo docker compose ...`). Do not change Docker socket permissions or add broad group access as a workaround.

**Candidate image evidence supplied by the owner:** the host successfully returned the following from `sudo docker image inspect job-radar-dev-multitenant:cf778c1`:

- Image tag: `job-radar-dev-multitenant:cf778c1`
- Image ID: `sha256:843f86af0c40b1aab90d43b5d5bc15c0c1eac29aadc48e56eb580bb9dbbe866a`
- Docker image Created timestamp: `2026-11-08T10:46:45.873218279Z` (UTC)

This confirms that the tagged image is present and inspectable with sudo on the Oracle VM. Preserve this exact image ID/tag for verification. The image inspection alone is not a deployment: no evidence has yet been provided that the shared-dev container was recreated or that the candidate is serving on port 8001.

**Next step:** use the same SSH session and prefix privileged operations with `sudo`. Before replacing the shared-dev container, create a fresh online SQLite snapshot immediately before promotion using the existing approved snapshot service, e.g. `sudo systemctl start --no-block job-radar-sqlite-snapshot.service`, then verify the service completion, snapshot timestamp/path/size and `PRAGMA integrity_check`. Do not reuse the older 09:44 UTC snapshot. After the fresh backup is verified, continue with the shared-dev-only runbook above. Keep production port 8000 untouched.


## 2026-11-08 — Shared-dev candidate deployed and live source integrations exercised

**This is the current operational state and supersedes earlier notes saying the connected `ubuntu` session could not use Docker.** The owner confirmed `sudo -n -l` permits `(ALL : ALL) ALL` and `(ALL) NOPASSWD: ALL`; all privileged operations below used `sudo`.

### Candidate currently serving on shared dev

- PR #51 branch: `integration/pr46-v2-rebase-20261108`.
- Exact deployed branch head: `754809fe406e8c5cb09f8e36140ac5cf3e4f7238`.
- V2 CI run `42474145630`: completed successfully, including py_compile, dashboard JavaScript syntax, focused tests and the full V2 unittest suite.
- Current image tag: `job-radar-dev-multitenant:b16fb83`.
- Current image ID: `sha256:75f8855338f150a79794d388c32733305e548165f71dd417cfa04e6443c8c917`.
- Container `job-radar-dev` was recreated at `2026-11-08T11:07:58.298331082Z`, serving only `127.0.0.1:8001->8000/tcp`; health returned HTTP 200.
- The first candidate `cf778c1` remains as a locally retained intermediate rollback artifact. Original rollback image `f43cd4a` also remains.
- Production container `v2-radar-1` on port 8000 was not recreated or restarted. Its health remained HTTP 200 during dev rollout.
- The external persistent volume `job-radar-dev_radar-dev-data`, read-only config bind mount, project/container identity and `.env` location were preserved.

### Fresh online SQLite backups

1. Before first candidate recreation: `/var/backups/job-radar-daily/development-pre-candidate-20261108T105233Z.sqlite3`; 8,383 jobs; 13 tables; 45,342,720 bytes; `PRAGMA integrity_check=ok`; SHA-256 `412a9232f60f1e25703061f95b370e34d31136170d5eac05ff78533830d9b85a`.
2. Before the Instahyre parser fix recreation: `/var/backups/job-radar-daily/development-pre-instahyre-fix-20261108T110723Z.sqlite3`; 8,386 jobs; 20 tables; 45,588,480 bytes; integrity `ok`; SHA-256 `295f839e9954ae6ed0edaf928ee91f00f0ab74f6aba2b0b36f92e59326a38216`.

Both are root-owned mode 0600 backups. They were created using SQLite's online backup API from the live dev container and separately integrity-checked after copy.

### Adapter live end-to-end results

The following one-off `radar.run_source` invocations used the live shared-dev DB and exercised source GET → parser/normalization → upsert → canonical opportunity linkage → global/per-user matching/evaluations → notification decision ledger. They did not turn on background scheduler flags. Telegram/Gemini/LLM delivery/enrichment remained off.

| Source | Live outcome | Request/board evidence | DB inserts |
|---|---|---|---:|
| Naukri | Successful scheduler cycles; latest observed 302 jobs, no error. Earlier post-deploy cycle observed 307 and inserted 3. | Public relay HTTP 200; one request/one page per poll. | 3 total over the observed polls |
| Instahyre | Success; 140 jobs observed | 4 requests, 4 HTTP 200 pages, 0 failed; 140 unique IDs | 140 |
| Greenhouse | Success; 369 jobs observed | 3/3 configured boards successful; 3 HTTP 200; 0 failed | 369 |
| Ashby | Success; 828 jobs observed, all 828 timestamped | 2/2 configured boards successful; 2 HTTP 200; 0 failed | 34 (the others already existed/deduplicated) |
| Lever | Success; 500 jobs observed | One-off public board `paytmpayments`; 5/5 HTTP 200 pages; bounded five-page cap reached | 500 |

The initial Instahyre attempt exposed a genuine integration mismatch: the current endpoint returned `objects` and nested `employer.company_name`, `public_url`, and `locations`; its location validation rejected `Bengaluru` and accepted `Bangalore`. The parser was fixed, aliases were added, four-page pagination is bounded, and three regression tests were added. The fixed candidate was rebuilt as `b16fb83`; the full V2 CI run passed and a real Instahyre poll returned 140 unique rows across four successful pages.

Lever's `paytmpayments` board was passed only to this one-off test invocation; `lever_boards` remains empty in persisted dev config and Lever remains disabled in the scheduler. Do not infer that Lever is configured for recurring collection.

### Live DB and delivery safety after all four one-off adapter pipelines

At the final post-run check:
- SQLite integrity: `ok`.
- `jobs`, `canonical_opportunities`, `job_evaluations`, `user_job_evaluations`, and `notification_ledger`: 9,429 rows each.
- `users`: 1; `user_preferences`: 1; `source_runs`: 7,851.
- Notification ledger: 56 pending, 9,373 suppressed; zero rows with a non-null `sent_at`. Per-user notification ledger was empty; no Telegram credential/chat was set.
- Persisted scheduler config remains Naukri only: LinkedIn/Instahyre/Greenhouse/Ashby/Lever all disabled, Naukri enabled. Notifications disabled.
- Gemini extraction/matcher and LLM router/matcher all explicitly false.
- No Telegram messages were sent.

### Remaining gates / limitations

- LinkedIn live verification has **not** been performed. Production health reports an active LinkedIn rate-limit cooldown until `2026-11-08T11:25:12.064175+00:00`. Do not probe before that timestamp; after it expires, if proceeding, use a single small paced request and stop immediately on 429. LinkedIn's unit/CI coverage is green, but that is not a live-source pass.
- Naukri is the only source enabled by the persisted scheduler config. Instahyre/Greenhouse/Ashby/Lever were verified by controlled one-off application runs, not left enabled continuously.
- Lever sample board has a 500-post bounded cap and is not in persisted config.
- Protected APIs returned 401 when queried without a session, as expected. Owner must log in through the SSH-tunnel browser to verify admin/member interactive flows; this run did not establish a real member login.
- The known 320px hit-test overlap remains deferred by owner priority; do not report the 320px flow as passing.
- Shared dev is deployed and tested; **production has not been promoted**. PR #51 remains draft/open. Production requires a separate explicit promotion decision after remaining gates are reviewed.


## 2026-11-08 — final dev verification and expanded 36-platform owner scope

Latest shared-dev check at 2026-11-08 11:39:59 UTC:
- Health HTTP 200, dashboard HTTP 200, version 2.0.0; image job-radar-dev-multitenant:b16fb83, ID sha256:75f8855338f150a79794d388c32733305e548165f71dd417cfa04e6443c8c917.
- Production port 8000 HTTP 200 and unchanged old container/image; no production deployment.
- Dev SQLite integrity ok; jobs/canonical/global evaluations/per-user evaluations/global notification ledger = 9,444; source_runs=7,858. One admin user, one profile preference row, per-user notification ledger empty. Every global notification ledger row is suppressed; sent_at non-null count zero.
- Latest result by source: Naukri scheduler success; LinkedIn one-off 10 seen/10 inserted; Instahyre 140/140; Greenhouse 369/369; Ashby 828 seen/34 new; Lever 500/500 from one-off board. Only Naukri remains enabled in the persisted dev scheduler.
- Delivery remains disabled in shared dev; Telegram token/chat blank; Gemini/LLM flags false.
- A transient/recurring sqlite3.OperationalError database is locked appeared in notification_worker -> recover_stale_claims under concurrent ingestion. Production gate: fix and stress-test.
- Production preflight was performed only on disposable /tmp copy; no write to the live prod volume. Prod has global Telegram credentials and notification delivery on; queue currently has 1,482 sent, 10 failed, 19,168 suppressed. Preserve behaviour/queue in any future promotion.
- Production LinkedIn cooldown must always be re-read; latest seen was through 2026-11-08T12:01:13.950862Z.

Owner's full 36-platform source requirement is recorded in docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md. It distinguishes ATS vendors from marketplace sources, identifies Workday and Darwinbox as first missing connectors, requires company/board discovery and per-user Telegram outbox, and defines a 2-minute high-priority poll target where endpoints/terms permit. The V2 runtime currently has six adapters; five non-Naukri source pipelines have one-off live evidence but are not scheduler-enabled. Do not claim all 36 work.

Next agent order: P0 notification-worker DB-lock fix + member/admin auth and per-user Telegram test; P1 Workday then Darwinbox; implement employer/career-site discovery; continue through the 36-row roadmap. No production promotion until these gates, a formal fresh prod backup and separate explicit approval.
