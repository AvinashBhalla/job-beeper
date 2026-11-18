#!/usr/bin/env bash
# Daily production-only SQLite snapshot with seven dated local recovery points.
# Safe while JobBeeper is live: SQLite's online backup API reads a consistent view.
set -Eeuo pipefail
umask 077

BACKUP_DIR=/var/backups/job-radar-daily
DATA_DIR=/var/lib/docker/volumes/v2-radar-data/_data
CONTAINER=v2-radar-1
RETENTION_HELPER=/usr/local/lib/job-radar-backup/retention.py
KEEP_DAILY=7
TODAY=$(date -u +%Y%m%d)

install -d -m 0700 -o root -g root "$BACKUP_DIR"
[[ -f "$DATA_DIR/config.json" ]] || { echo "missing production config.json" >&2; exit 1; }
[[ -f "$DATA_DIR/config_token" ]] || { echo "missing production config_token" >&2; exit 1; }
docker inspect "$CONTAINER" >/dev/null
[[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" == "true" ]]
docker exec "$CONTAINER" true >/dev/null

inside="/tmp/production-jobs-$TODAY.$$"
staged="$BACKUP_DIR/.production-jobs-$TODAY.sqlite3.tmp.$$"
alias_staged="$BACKUP_DIR/.production-jobs.sqlite3.tmp.$$"
cleanup() {
  if [[ -n "$inside" ]]; then
    docker exec "$CONTAINER" rm -f "$inside" >/dev/null 2>&1 || true
  fi
  rm -f "$staged" "$alias_staged"
}
trap cleanup EXIT

# SQLite's online backup API includes committed WAL content without copying a
# live database file or taking the application offline.
docker exec -i "$CONTAINER" python3 - "$inside" <<'PY'
import os
import sqlite3
import sys

target = sys.argv[1]
source = sqlite3.connect("file:/data/jobs.db?mode=ro", uri=True, timeout=30)
destination = sqlite3.connect(target, timeout=30)
try:
    source.backup(destination, pages=256, sleep=0.05)
    integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
    jobs = destination.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    print(f"integrity={integrity} jobs={jobs} bytes={os.path.getsize(target)}")
finally:
    destination.close()
    source.close()
PY

docker cp "$CONTAINER:$inside" "$staged" >/dev/null
chown root:root "$staged"
chmod 0600 "$staged"

# Verify the copied host-side bytes as well before publishing either filename.
python3 - "$staged" <<'PY'
import os
import sqlite3
import sys

path = sys.argv[1]
db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
try:
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    jobs = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"host snapshot integrity check failed: {integrity}")
    print(f"host_integrity={integrity} jobs={jobs} bytes={os.path.getsize(path)}")
finally:
    db.close()
PY

dated_db="$BACKUP_DIR/production-jobs-$TODAY.sqlite3"
current_db="$BACKUP_DIR/production-jobs.sqlite3"
mv -f "$staged" "$dated_db"
ln "$dated_db" "$alias_staged"
mv -f "$alias_staged" "$current_db"
docker exec "$CONTAINER" rm -f "$inside" >/dev/null
inside=""

snapshot_file() {
  local source="$1"
  local dated_name="$2"
  local current_name="$3"
  local tmp="$BACKUP_DIR/.$dated_name.tmp.$$"
  local alias_tmp="$BACKUP_DIR/.$current_name.tmp.$$"
  cp -- "$source" "$tmp"
  chown root:root "$tmp"
  chmod 0600 "$tmp"
  mv -f "$tmp" "$BACKUP_DIR/$dated_name"
  ln "$BACKUP_DIR/$dated_name" "$alias_tmp"
  mv -f "$alias_tmp" "$BACKUP_DIR/$current_name"
}

# Pair the DB snapshot with the runtime configuration and its token.
snapshot_file "$DATA_DIR/config.json" "production-config-$TODAY.json" "production-config.json"
python3 -m json.tool "$BACKUP_DIR/production-config-$TODAY.json" >/dev/null
snapshot_file "$DATA_DIR/config_token" "production-config-token-$TODAY" "production-config-token"

# Prune only the three exact dated production families, never old rollbacks.
python3 "$RETENTION_HELPER" --directory "$BACKUP_DIR" --keep "$KEEP_DAILY"

# Preserve the existing pre-release checksum record for historical rollback files.
MANIFEST_TMP=/var/backups/.job-radar-pre-release-20261106.SHA256SUMS.tmp
(
  cd /var/backups
  find job-radar-pre-release-20261106 job-radar-daily -type f \
    ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) > "$MANIFEST_TMP"
chown root:root "$MANIFEST_TMP"
chmod 0600 "$MANIFEST_TMP"
mv -f "$MANIFEST_TMP" /var/backups/job-radar-pre-release-20261106/SHA256SUMS

echo "snapshot_ok container=$CONTAINER file=$dated_db bytes=$(stat -c %s "$dated_db")"
echo "current_alias=$current_db"
echo "config_snapshot=production-config-$TODAY.json"
echo "retention_keep=$KEEP_DAILY"
echo "snapshot_manifest=$BACKUP_DIR/SHA256SUMS"
