# Free local recovery snapshots

## Decision

The owner does not want a paid backup service. Termalin's confirmation flow has repeatedly become unresponsive, and the owner has chosen not to subscribe. The existing Termalin draft is not retried and is not treated as an active backup. No paid provider, subscription, API or storage is required for the local recovery path.

GitHub Actions is blocked from starting private-repository CI while the account billing/spending gate remains unresolved. Engineering validation continues independently on the existing VM. Local test passes are recorded separately, not represented as hosted CI.

## Current production snapshot

The production VM has approximately 34 GB free disk space at the last check. The production database is approximately 138 MB. The daily timer \`job-radar-sqlite-snapshot.timer\` runs at 02:45 UTC and uses SQLite's online backup API from inside \`v2-radar-1\`. It does not stop or restart JobBeeper.

The currently installed script writes one fixed filename, \`production-jobs.sqlite3\`, replacing the previous file each day. This is a consistent local snapshot but only one daily recovery point. The active database's WAL is included by SQLite's online backup API; copying the live \`jobs.db\` file would not be safe.

## Proposed seven-day local retention

The PR's \`deploy/backup/job-radar-sqlite-snapshot.sh\`:
- Creates a dated \`production-jobs-YYYYMMDD.sqlite3\` snapshot and preserves the compatibility alias \`production-jobs.sqlite3\` as a hard link to the same inode.
- Verifies SQLite integrity and the jobs row count inside the container and again after copying the file to the host.
- Captures the matching production \`config.json\` and \`config_token\` as dated files with mode 0600; the backup directory remains root-only (0700).
- Retains the newest seven dated production database/config/token snapshots.
- Writes SHA-256 checksums for retained dated snapshots to \`SHA256SUMS\`.
- Prunes only exact filenames matching the three production snapshot patterns. Development databases, the pre-reboot recovery point and historical rollback snapshots are never selected for deletion.
- Removes the optional development-container snapshot from the production backup's success path, so a stopped development container cannot turn a valid production snapshot into a failed backup job.
- Preserves the existing pre-release checksum manifest.

Retention logic is isolated in \`deploy/backup/retention.py\` and covered by unit tests. Seven 138 MB database snapshots require roughly 966 MB, plus small configuration files. The one-time legacy hard link preserves the previous recovery point without an extra database copy; the current alias is also a hard link and does not create an eighth daily copy.

## Installation / rollback

The repository files are templates. Production installation is a separate change and has not been performed:
1. Save the current \`/usr/local/sbin/job-radar-sqlite-snapshot.sh\` with its permissions and SHA-256.
2. Install the script as root mode 0750 and the helper at \`/usr/local/lib/job-radar-backup/retention.py\` mode 0640. Create the helper directory root:root mode 0750.
3. Run \`bash -n\` on the script and the retention unit tests before installation.
4. Run one snapshot manually while the app remains online; inspect both integrity checks, job count, dated files, aliases and checksum manifest.
5. Check \`systemctl status job-radar-sqlite-snapshot.service\`, then allow a later scheduled run and inspect its journal.
6. Roll back by restoring the saved original script/helper if any verification fails. No app service restart is required.

Do not treat local snapshots as off-site disaster recovery. A VM or volume loss can destroy both the app and these snapshots. Without a free external destination, there is no true off-site copy; this design intentionally does not pretend otherwise.

## Verification

\`\`\`bash
sudo python3 /usr/local/lib/job-radar-backup/retention.py --directory /var/backups/job-radar-daily --keep 7
cd /var/backups/job-radar-daily && sudo sha256sum -c SHA256SUMS
sudo sqlite3 /var/backups/job-radar-daily/production-jobs.sqlite3 'PRAGMA integrity_check; SELECT COUNT(*) FROM jobs;'
\`\`\`

Never claim off-site protection exists until an archive is independently observed at a separate destination.
