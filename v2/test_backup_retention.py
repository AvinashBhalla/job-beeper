from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from unittest import mock
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "backup"))
from retention import rotate_snapshots  # noqa: E402


class BackupRetentionTests(unittest.TestCase):
    def test_keeps_seven_newest_in_each_family_and_removes_only_exact_dated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            start = date(2026, 11, 1)
            for offset in range(10):
                stamp = (start + timedelta(days=offset)).strftime("%Y%m%d")
                (root / f"production-jobs-{stamp}.sqlite3").write_bytes(f"db-{offset}".encode())
                (root / f"production-config-{stamp}.json").write_text("{}")
                (root / f"production-config-token-{stamp}").write_text("token")
            (root / "production-jobs.sqlite3").write_bytes(b"current alias")
            (root / "production-before-release.sqlite3").write_bytes(b"rollback")
            (root / "production-jobs-legacy-pre-retention.sqlite3").write_bytes(b"legacy")
            (root / "pre-reboot-20261118.sqlite3").write_bytes(b"pre reboot")
            (root / "development-jobs.sqlite3").write_bytes(b"dev")
            (root / "production-jobs-20260230.sqlite3").write_bytes(b"invalid date")

            removed = rotate_snapshots(root, keep=7)

            self.assertEqual(removed, {"database": 3, "config": 3, "config_token": 3})
            self.assertFalse((root / "production-jobs-20261101.sqlite3").exists())
            self.assertTrue((root / "production-jobs-20261110.sqlite3").exists())
            self.assertTrue((root / "production-jobs.sqlite3").exists())
            self.assertTrue((root / "production-before-release.sqlite3").exists())
            self.assertTrue((root / "pre-reboot-20261118.sqlite3").exists())
            self.assertTrue((root / "development-jobs.sqlite3").exists())
            self.assertTrue((root / "production-jobs-20260230.sqlite3").exists())

            manifest = (root / "SHA256SUMS").read_text()
            expected = hashlib.sha256(b"db-9").hexdigest()
            self.assertIn(f"{expected}  production-jobs-20261110.sqlite3", manifest)
            legacy_hash = hashlib.sha256(b"rollback").hexdigest()
            reboot_hash = hashlib.sha256(b"pre reboot").hexdigest()
            legacy_hash = hashlib.sha256(b"legacy").hexdigest()
            self.assertIn(f"{legacy_hash}  production-jobs-legacy-pre-retention.sqlite3", manifest)
            self.assertIn(f"{reboot_hash}  pre-reboot-20261118.sqlite3", manifest)
            self.assertNotIn("production-jobs.sqlite3", manifest)
            self.assertEqual((root / "SHA256SUMS").stat().st_mode & 0o777, 0o600)

    def test_rejects_zero_or_negative_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            for keep in (0, -1):
                with self.subTest(keep=keep), self.assertRaises(ValueError):
                    rotate_snapshots(temp, keep=keep)

    def test_hash_failure_does_not_prune_old_recovery_points(self):
        import retention

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for offset in range(9):
                stamp = f"202611{offset + 1:02d}"
                (root / f"production-jobs-{stamp}.sqlite3").write_text(str(offset))
            stale = root / "production-jobs-20261101.sqlite3"
            with mock.patch.object(retention, "_sha256", side_effect=OSError("read failed")):
                with self.assertRaises(OSError):
                    rotate_snapshots(root, keep=7)
            self.assertTrue(stale.exists())
            self.assertFalse((root / "SHA256SUMS").exists())

    def test_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                rotate_snapshots(Path(temp) / "missing", keep=7)


class BackupScriptContractTests(unittest.TestCase):
    def test_snapshot_script_uses_verified_online_backup_and_expected_volume(self):
        script = (Path(__file__).resolve().parents[1] / "deploy" / "backup" / "job-radar-sqlite-snapshot.sh").read_text()
        self.assertIn("v2_radar-data/_data", script)
        self.assertIn("source.backup(destination", script)
        self.assertGreaterEqual(script.count('PRAGMA integrity_check'), 2)
        self.assertIn("mode=ro&immutable=1", script)
        self.assertIn('"$staged-wal" "$staged-shm"', script)
        self.assertIn('"$inside-wal" "$inside-shm"', script)
        self.assertIn("production-jobs-legacy-pre-retention.sqlite3", script)
        self.assertIn('RETENTION_HELPER=/usr/local/lib/job-radar-backup/retention.py', script)

    def test_snapshot_script_keeps_legacy_snapshot_as_hard_link_before_replacing_alias(self):
        script = (Path(__file__).resolve().parents[1] / "deploy" / "backup" / "job-radar-sqlite-snapshot.sh").read_text()
        self.assertLess(
            script.index('ln "$current_db" "$legacy_tmp"'),
            script.index('mv -f "$alias_staged" "$current_db"'),
        )
        self.assertIn('ln "$dated_db" "$alias_staged"', script)


if __name__ == "__main__":
    unittest.main()
