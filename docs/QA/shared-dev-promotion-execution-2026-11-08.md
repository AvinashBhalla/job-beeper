# Shared-dev promotion execution — blocked by Docker operator access

**Date:** 2026-11-08 (Asia/Calcutta)  
**Owner approval:** Explicit shared-dev promotion approval received 2026-11-08. Approval scope is shared dev only; production is excluded.  
**Candidate:** `integration/pr46-v2-rebase-20261108`  
**Candidate PR:** #51, base `v2-live-radar`  
**Candidate PR head:** `e299efdb228b4a05fdc106a0e5e70b9344adf607` (documentation-only additions after candidate app code SHA `cf778c1f1da33c773f820cafea991fb084c58da8`).

## Candidate readiness

- GitHub V2 CI run `42471400933` passed against the exact current PR head `e299efdb228b4a05fdc106a0e5e70b9344adf607`.
- Candidate application code passed the real-data dry run described in `docs/QA/real-data-pipeline-dry-run-2026-11-08.md`: full 8,368-row real snapshot rematch, 130 matches, a fresh Naukri relay GET (318 observed, 7 new jobs inserted in a disposable DB copy), canonical linkage, feed query and notification decisions.
- The candidate has not yet been run against the live persistent shared-dev DB or scheduler. The required next stage remains a live shared-dev Naukri soak.

## Live service checks — read only

| Target | Result |
|---|---|
| Shared dev `127.0.0.1:8001/health` | HTTP 200, V2.0.0 |
| Production `127.0.0.1:8000/health` | HTTP 200, V2.0.0 |
| Protected unauthenticated API reads on dev | HTTP 401 as expected |

Production port 8000 was not changed, restarted, or otherwise targeted.

## Exact promotion blocker

The only available Termalin shell identity is `ubuntu` (uid/gid 1001). Its supplementary groups do not include `docker`. The Docker socket is owned by `root:docker` with mode `0660`. `docker ps` returns `permission denied` on `/var/run/docker.sock`. The existing containers/processes are root-owned. The repository has no self-hosted deployment runner or deployment workflow; its only workflow is V2 CI.

The operator session did not use `sudo`, change Docker group membership, alter socket permissions, or attempt a permission workaround. The host's existing Termalin backup job is a DRAFT waiting for owner confirmation and has no archives. A previous 2026-11-08 09:44 UTC database snapshot exists, but it is not sufficiently fresh to use as the promotion backup.

Consequently, this session cannot safely inspect/recreate `job-radar-dev`, build/load its image, or take the required immediate pre-promotion backup from the live Docker volume. This is an access limitation, not an application test failure.

## No deployment actions occurred

- No fresh pre-promotion backup was created.
- No candidate image was built, loaded or tagged on the host.
- No Docker container was recreated or restarted.
- No live SQLite database, config, `.env`, volume or feature flags were changed.
- No collector was enabled or disabled.
- No notification credentials were added and no Telegram message was sent.
- No PR merge or production deployment occurred.

## Safe configuration required when an authorized operator continues

1. Use an existing account/session already authorized for the Docker socket. Do not change socket permissions or grant new broad Docker privileges as a shortcut.
2. Reconfirm PR #51 exact head and passing CI; build the candidate from the reviewed app-code SHA `cf778c1f1da33c773f820cafea991fb084c58da8` or the corresponding code tree on the current docs-only head.
3. Take a fresh SQLite online backup of `/data/jobs.db` from the running dev volume immediately before promotion; record path, size and `PRAGMA integrity_check`.
4. Preserve volume `job-radar-dev_radar-dev-data`, compose project/container identity, config bind mount, `.env` in place, existing rollback image `job-radar-dev-multitenant:f43cd4a` and Telegram blanking.
5. Keep Naukri enabled; LinkedIn, Instahyre, Greenhouse, Ashby and Lever disabled; notifications/Telegram disabled; Gemini disabled.
6. Build an immutable candidate image tag and recreate only `job-radar-dev` on host port 8001. Do not use `down -v`, prune volumes, or touch production port 8000.
7. Verify health, database integrity/counts, source flags, Naukri feed run metadata and zero notification sends; observe at least two actual Naukri scheduler cycles.

## Handoff required

An owner/operator must provide a Termalin or SSH execution session already authorized for Docker management. No password, private key or token should be pasted into chat. Once that authorized session is available, resume from the fresh-backup step; do not reuse the old 09:44 UTC snapshot as the immediate rollback backup.

**Disposition:** Owner approval received; promotion is **not executed** because this connected session lacks Docker authorization and cannot take the required immediate pre-promotion backup. Shared dev and production remain healthy and unchanged.
## Additional backup-service check

The existing root-owned `job-radar-sqlite-snapshot.service` was inspected read-only. Its last successful run was 2026-11-08 02:45:43 UTC; systemd logs show the development snapshot had 8,333 jobs and 45,117,440 bytes at that time, with `integrity=ok`. This predates the current promotion window by several hours and is not an immediate pre-promotion backup.

A normal `systemctl start --no-block job-radar-sqlite-snapshot.service` request as `ubuntu` was denied with `Interactive authentication required`. The service did not run; there was no fresh snapshot. No sudo or permission workaround was used.

## 2026-11-08 — Access finding and candidate image present

This update corrects the earlier access diagnosis in this report. The earlier Termalin checks invoked Docker and systemd as plain `ubuntu` and received permission errors; they did not test the account's sudo policy.

The owner checked `sudo -n -l` from the existing SSH-key-authenticated `ubuntu` session on the Oracle Cloud VM. The host confirmed:

```text
User ubuntu may run the following commands on job-radar:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: ALL
```

Thus, the existing `ubuntu` account has full passwordless sudo. No password, second SSH account, Docker-group change or socket permission change is required. Privileged Docker and snapshot operations should be run with `sudo`; plain `docker ...` remains expected to fail because the account is not directly in the Docker socket's group.

The owner also supplied the successful output of:

```bash
sudo docker image inspect job-radar-dev-multitenant:cf778c1 \
  --format 'Image ID: {{.Id}} | Created: {{.Created}}'
```

Host-reported result:

- Tag: `job-radar-dev-multitenant:cf778c1`
- Image ID: `sha256:843f86af0c40b1aab90d43b5d5bc15c0c1eac29aadc48e56eb580bb9dbbe866a`
- Created: `2026-11-08T10:46:45.873218279Z` (UTC)

This verifies the image tag is present and inspectable on the VM using sudo. It does **not** establish that the container has been recreated or that the candidate is live on port 8001.

**Promotion status remains pending.** No fresh immediate pre-promotion SQLite snapshot has yet been evidenced, and no shared-dev container recreation/soak result has been reported. Next, run the existing snapshot service using sudo, verify the resulting backup's integrity and freshness, then follow the shared-dev-only promotion procedure. Keep Naukri as the only enabled collector, Telegram/notifications and Gemini disabled, preserve the external dev volume and rollback image, and do not touch production port 8000.


## 2026-11-08 — Shared-dev rollout succeeded; live adapter canary results

This section supersedes the earlier access-blocker status. The existing Oracle VM SSH-key account `ubuntu` has passwordless full sudo (confirmed by `sudo -n -l`); Docker/systemd operations were run with `sudo`.

### Deployment

- PR #51 branch head deployed: `754809fe406e8c5cb09f8e36140ac5cf3e4f7238`.
- CI run `42474145630` completed successfully.
- Candidate image: `job-radar-dev-multitenant:b16fb83`, ID `sha256:75f8855338f150a79794d388c32733305e548165f71dd417cfa04e6443c8c917`.
- `job-radar-dev` recreated at `2026-11-08T11:07:58.298331082Z`; HTTP 200 on port 8001.
- The deployment changed only the service image in the validated candidate Compose file. It preserved the external volume `job-radar-dev_radar-dev-data`, config bind, env file and 8001 binding.
- Production port 8000 remained on its pre-existing container and returned HTTP 200; no production change occurred.

### Verified backups

- `/var/backups/job-radar-daily/development-pre-candidate-20261108T105233Z.sqlite3`: 8,383 jobs, 45,342,720 bytes, integrity `ok`; SHA-256 `412a9232f60f1e25703061f95b370e34d31136170d5eac05ff78533830d9b85a`.
- `/var/backups/job-radar-daily/development-pre-instahyme-fix-20261108T110723Z.sqlite3`: 8,386 jobs, 45,588,480 bytes, integrity `ok`; SHA-256 `295f839e9954ae6ed0edaf928ee91f00f0ab74f6aba2b0b36f92e59326a38216`.

### Live application pipelines

The owner-facing adapter tests were run via one-off `radar.run_source` calls with the live dev DB. The scheduler source flags were not changed. All listed runs finished with `outcome=success` and no HTTP 4xx/5xx/429 errors:

- Naukri: periodic scheduler polls succeeded; one poll inserted 3 jobs.
- Instahyre: 140 seen / 140 inserted, 4 HTTP 200 pages.
- Greenhouse: 369 seen / 369 inserted, 3 of 3 public boards successful.
- Ashby: 828 seen / 34 new, 2 of 2 boards successful; all 828 carried timestamps.
- Lever: 500 seen / 500 inserted from one-off board `paytmpayments`; 5 of 5 pages HTTP 200, bounded five-page cap reached. The board was not added to persisted config.

Instahyre live incompatibility was fixed in the candidate: API response `objects` shape, current nested employer/public URL/location fields, Bengaluru/Gurugram/Delhi/remote aliases, and bounded pagination. Three new tests passed and V2 CI run `42474145630` succeeded on the deployed head.

After those tests the live DB reported 9,429 jobs, canonical opportunities, global evaluations, per-user evaluations and notification-ledger rows, SQLite integrity `ok`. Source-run count was 7,851.

### Delivery and integration gates

- Naukri only remains enabled in the recurring scheduler. LinkedIn, Instahyre, Greenhouse, Ashby and Lever remain disabled in the saved config.
- Notifications false; Telegram token/chat blank; Gemini and LLM router flags false.
- 56 global ledger rows pending and 9,373 suppressed; zero non-null `sent_at`. No Telegram messages sent.
- LinkedIn live polling deliberately withheld while production health reported a rate-limit cooldown through `2026-11-08T11:25:12.064175+00:00`. CI/unit coverage passed; live check is outstanding.
- Protected endpoints return 401 without login; a real browser admin/member login was not tested in this pass.
- 320px toolbar overlap remains a known, deliberately deferred UI defect.
- Shared-dev deployment is complete; production remains untouched. PR #51 remains open/draft. Production promotion requires a separate explicit approval after the remaining LinkedIn/auth checks are reviewed.


## 2026-11-08 — final integration checkpoint and 36-platform scope

Final shared-dev verification at 11:39:59 UTC: health and dashboard HTTP 200, image b16fb83. Production health HTTP 200 and production container untouched. Dev SQLite integrity ok; 9,444 jobs, canonical opportunities, global evaluations, per-user evaluations and global ledger rows; 7,858 source runs. Notification sent_at count zero. Persisted config Naukri only, notifications false, Telegram credentials blank, Gemini/LLM false.

Real live source pipeline outcomes:
- Naukri recurring: successful schedule polls.
- Instahyre: 140 seen/new, 4 HTTP 200 pages after live parser repair.
- Greenhouse: 369 seen/new, 3/3 boards successful.
- Ashby: 828 seen / 34 new, 2/2 boards successful.
- Lever: 500 seen/new on one-off paytmpayments board, 5/5 pages 200 and page cap reached; not saved/enabled.
- LinkedIn: one paced request after cooldown, 10 unique jobs / HTTP 200, same fetched rows ingested 10; not saved/enabled.
V2 source registry remains only six adapters; only Naukri on recurring scheduler.

Known production gate: notification worker recover_stale_claims threw sqlite3.OperationalError database is locked during concurrent ingestion (twice observed around tests); investigate/fix and add concurrency coverage before prod. No user Telegram ledger entries exist on dev, so user-specific delivery remains unverified.

Owner added a mandatory source coverage goal covering all 36 systems listed in docs/ATS_SOURCE_COVERAGE_AND_NEAR_REALTIME_ROADMAP.md. Workday and Darwinbox are highest-priority missing ATS integrations. The roadmap defines employer board discovery, vendor-specific polling/webhook behaviour, a 2-minute target where permitted, normalized source records, per-user match/outbox/delivery, and an ordered build plan. Most ATS sources are employer-specific tenants; marketplace sources need separate access/terms review. Do not state 36-platform coverage until each row has validated live evidence.

Production read-only preflight on disposable copy preserved rows, but production has Telegram credentials and notifications enabled. Keep prod untouched; prior approval was dev only. Next agent must fix SQLite contention, prove per-user Telegram with safe test accounts, build Workday/Darwinbox and board discovery, then proceed through the 36-platform roadmap before requesting distinct prod approval.
