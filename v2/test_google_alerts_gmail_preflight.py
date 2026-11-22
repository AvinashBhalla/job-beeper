from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from v2 import google_alerts_gmail_preflight as preflight


class GmailPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "jobs.db"
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO users(id, role, status) VALUES (7, 'admin', 'active')"
            )
        self.env = {
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_ID": "test-client-id",
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_SECRET": "test-client-secret",
            "JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI": (
                "http://localhost:8080" + preflight.google_alerts_gmail.CALLBACK_PATH
            ),
            "JOB_RADAR_GMAIL_OWNER_USER_ID": "7",
            "JOB_RADAR_GMAIL_OWNER_EMAIL": "alerts@example.test",
            "JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
            "JOB_RADAR_GMAIL_SYNC_MODE": "polling",
            "JOB_RADAR_GMAIL_POLL_INTERVAL_SECONDS": "180",
            "JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS": "false",
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_preflight_passes_for_active_admin_and_live_access_off(self):
        with patch.dict("os.environ", self.env, clear=True):
            lines = preflight.run_preflight(self.db)
        self.assertTrue(any("safe default" in line for line in lines))
        self.assertTrue(any("active administrator" in line for line in lines))

    def test_preflight_rejects_non_admin_or_disabled_owner(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE users SET role='user' WHERE id=7")
        with patch.dict("os.environ", self.env, clear=True):
            with self.assertRaisesRegex(preflight.PreflightError, "active_admin"):
                preflight.run_preflight(self.db)

    def test_preflight_can_require_live_access_without_enabling_it(self):
        with patch.dict("os.environ", self.env, clear=True):
            with self.assertRaisesRegex(preflight.PreflightError, "switch_is_disabled"):
                preflight.run_preflight(self.db, require_live_enabled=True)

    def test_preflight_rejects_missing_owner(self):
        with patch.dict("os.environ", self.env, clear=True):
            with self.assertRaisesRegex(preflight.PreflightError, "owner_account_not_found"):
                preflight.check_owner_account(self.db, 99)


if __name__ == "__main__":
    unittest.main()
