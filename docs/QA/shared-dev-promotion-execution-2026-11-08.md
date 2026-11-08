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