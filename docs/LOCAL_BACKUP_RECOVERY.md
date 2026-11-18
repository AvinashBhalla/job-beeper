# Free local recovery snapshots

## Decision and limits

The owner has chosen a no-spend approach. Termalin's browser confirmation flow repeatedly became unresponsive; its existing draft remains unused, no archive exists, and no paid backup plan is being pursued. Private-repository GitHub Actions CI is blocked by the account billing/spending restriction, so all local validation is recorded separately from hosted CI.

The local recovery path is installed and running. It does not use a paid provider, API, hosted runner, subscription or external storage.

**This is local recovery, not off-site disaster recovery.** The snapshots live on the same VM disk as JobBeeper. They protect against database corruption, an accidental bad write, or a need to restore an earlier local state. They do not protect against VM loss, disk failure, account loss or deletion of the whole server.

## Installed production design

- Source database: `/data/jobs.db` inside container `v2-radar-1`.
- Host volume for runtime configuration: `/var/lib/docker/volumes/v2_radar-data/_data`.
- Local snapshot directory: `/var/backups/job-radar-daily`, root:root mode **0700**.
- Daily systemd timer: `job-radar-sqlite-snapshot.timer`, configured for 02:45 UTC.
- Installed script: `/usr/local/sbin/job-radar-sqlite-snapshot.sh`, root:root mode **0750**.
- Retention helper: `/usr/local/lib/job-radar-backup/retention.py`, root:root mode **0640**.
- The script uses SQLite's online backup API while the application remains running. It does not stop the app or copy the live `jobs.db` file directly.

### Snapshot files

Each daily run creates:
- `production-jobs-YYYYMMDD.sqlite3`
- `production-config-YYYYMMDD.json`
- `production-config-token-YYYYMMDD`

The current compatibility names `production-jobs.sqlite3`, `production-config.json`, and `production-config-token` are atomically replaced hard links to the newest dated files. The first upgraded run also preserved the pre-upgrade rolling database as `production-jobs-legacy-pre-retention.sqlite3`, without another database copy. Existing `pre-reboot-YYYYMMDD.sqlite3` snapshots are also retained.

Every database snapshot is checked with `PRAGMA integrity_check` and a job-row count inside the container and again after it is copied to the host. Host-side validation opens the immutable snapshot in read-only immutable mode to avoid creating SQLite WAL/SHM sidecars. The script cleans its staging files and sidecars on success and failure.

The configuration and token snapshots are mode **0600**. The database snapshots, compatibility aliases and checksum manifest are also mode **0600**.

### Retention and integrity

The helper keeps the newest **seven dated files in each production family** (database, config and token). It prunes only exact, validated `production-jobs-YYYYMMDD.sqlite3`, `production-config-YYYYMMDD.json` and `production-config-token-YYYYMMDD` names. It does not prune development snapshots, pre-reboot copies, the one-time legacy copy, or historical rollback files.

Before pruning anything, the helper hashes the retained files plus legacy and pre-reboot recovery points, writes and fsyncs a temporary SHA-256 manifest, and only then deletes stale dated files and atomically publishes `SHA256SUMS`. If a checksum/read operation fails, old recovery points remain untouched.

The script also continues updating the pre-release checksum manifest under `/var/backups/job-radar-pre-release-20261106/SHA256SUMS`.

Seven ~138 MB database snapshots require approximately 966 MB, plus small config/token files. Hard-link compatibility aliases do not create extra database copies.

## 18 November 2026 installation and verification

PR #97 was merged into `v2-live-radar`. The script and helper were installed without an application deployment or restart.

- Original pre-change script preserved at `/var/backups/job-radar-daily/rollback/job-radar-sqlite-snapshot.sh.pre-seven-day-retention-20261118`.
- Original script SHA-256: `0cc31271235590c8c792abe62280a48648333947cd3d0977ed99e9ebc8c2b9f4`.
- Installed script SHA-256: `14a6ca249bc4ae47bdca95d280eabc70fbcb2605990b22d1b8f99bae920555d0`.
- Installed helper SHA-256: `39ab0b085a72caa217ceef5045b2cb309a4f9c882d12b15927564c455f1f0a65`.
- Local backup tests: **6 passed**; shell syntax check and Python compilation passed.
- Snapshot generated: `production-jobs-20261118.sqlite3`, 138,420,224 bytes, 27,891 jobs, integrity `ok`.
- The compatibility alias and dated file share the same inode (hard link).
- Preserved legacy snapshot: 27,656 jobs, integrity `ok`.
- Pre-reboot recovery snapshot: 27,673 jobs, integrity `ok`.
- Dated config and token snapshots created; both mode 0600.
- `SHA256SUMS` contains five entries (pre-reboot DB, legacy DB, new DB and the two dated config files); all five verified with `sha256sum -c`.
- No staging files or SQLite sidecars remained after the final run.
- The installed systemd oneshot `job-radar-sqlite-snapshot.service` was started once after installation and completed with `Result=success`, exit status 0. Journal records both integrity checks as ok and the dated snapshot publication at 10:16:41 UTC.
- The app health endpoint returned HTTP 200 before and after both manual and systemd-triggered snapshots. The application was not restarted.
- The VM had about 33 GB free disk after installation; the local backup directory used about 1.6 GB at the check.
- The daily snapshot timer remains enabled. Naukri's separate relay timer remains intentionally disabled.

This is the first dated snapshot under the seven-day policy. The directory will accumulate up to seven daily snapshots as scheduled runs complete; it does not already contain seven new daily generations.

## Monitoring

The hourly JobBeeper Health Watch should verify read-only:
1. Daily snapshot timer is enabled and waiting, and the last service result is successful.
2. Latest dated production DB snapshot exists and is not older than the expected daily cadence.
3. The SHA-256 manifest verifies and the latest DB passes SQLite integrity check.
4. The backup directory remains root-only and disk usage has adequate headroom.
5. The Naukri relay timer remains disabled unless the owner explicitly requests resumption.

Do not automatically run the snapshot, prune files, enable the relay, or modify production config from the health monitor.

## Rollback

If the new snapshot script fails:
1. Restore the preserved script:
   `sudo install -o root -g root -m 0750 /var/backups/job-radar-daily/rollback/job-radar-sqlite-snapshot.sh.pre-seven-day-retention-20261118 /usr/local/sbin/job-radar-sqlite-snapshot.sh`.
2. The daily systemd unit does not require an application restart. Confirm the next service run succeeds and inspect the journal.
3. Keep dated snapshots already created; do not delete them as part of rollback.
4. The helper can remain installed but is no longer called by the restored script. It can be removed separately after confirming nothing else references it.

## Manual verification commands

```bash
sudo bash -c 'cd /var/backups/job-radar-daily && sha256sum -c SHA256SUMS'
sudo python3 - <<'PY'
import sqlite3
p='/var/backups/job-radar-daily/production-jobs.sqlite3'
db=sqlite3.connect(f'file:{p}?mode=ro&immutable=1', uri=True)
print(db.execute('PRAGMA integrity_check').fetchone()[0])
print(db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0])
db.close()
PY
```

Never describe this as an off-site backup. A true second-site copy would require a separate no-cost destination and owner-controlled credentials; none is configured.
