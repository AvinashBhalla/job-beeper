"""API-level tests for personalized evaluation isolation and onboarding."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from v2 import auth, radar, user_preferences


class UserScopedJobFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "user-feed.sqlite3"
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.config_patch = patch.object(radar, "RUNTIME_CONFIG_PATH", self.config_path)
        self.db_patch.start()
        self.config_patch.start()
        radar.init_db()
        user_preferences.init_preferences_schema(self.db_path)
        self.user_a = auth.create_user(self.db_path, "a@example.com", "user-a-password-long")
        self.user_b = auth.create_user(self.db_path, "b@example.com", "user-b-password-long")
        user_preferences.save_user_preferences(
            self.db_path,
            self.user_a["id"],
            {"target_roles": ["Python Developer"], "locations": ["Bengaluru"]},
        )
        user_preferences.save_user_preferences(
            self.db_path,
            self.user_b["id"],
            {"target_roles": ["QA Engineer"], "locations": ["Pune"]},
        )
        config = {**radar.get_config(), "notifications_enabled": False}
        jobs = [
            radar.normalize_job(
                "naukri", "python-1", "Acme", "Python Developer",
                "Bengaluru, Karnataka, India", "https://example.com/python",
                None, "unknown", "Build Python backend services with Django.",
            ),
            radar.normalize_job(
                "naukri", "qa-1", "Acme", "QA Engineer",
                "Pune, Maharashtra, India", "https://example.com/qa",
                None, "unknown", "Test web applications and write automation scripts.",
            ),
        ]
        radar.upsert_jobs(jobs, config)
        # Deliberately mark one global notification as sent. A normal user must
        # still receive only the neutral not_eligible state, never ledger details.
        with sqlite3.connect(self.db_path) as conn:
            opportunity_id = conn.execute(
                "SELECT canonical_opportunity_id FROM jobs WHERE source_job_id='python-1'"
            ).fetchone()[0]
            conn.execute(
                "UPDATE notification_ledger SET status='sent', sent_at='2026-11-06T00:00:00+00:00' WHERE canonical_opportunity_id=?",
                (opportunity_id,),
            )
        self.client = TestClient(radar.app, base_url="https://testserver")

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def _login(self, email: str, password: str):
        return self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )

    def test_incomplete_user_cannot_open_jobs_feed(self):
        user = auth.create_user(self.db_path, "incomplete@example.com", "incomplete-user-password")
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"email": "incomplete@example.com", "password": "incomplete-user-password"},
            ).status_code,
            200,
        )
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 403)
        self.assertIn("target role and location", response.json()["detail"])

    def test_each_user_receives_independent_job_evaluations(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        feed_a = self.client.get("/api/jobs?minutes=10080&limit=20")
        self.assertEqual(feed_a.status_code, 200)
        by_title_a = {job["title"]: job for job in feed_a.json()["jobs"]}
        self.assertTrue(by_title_a["Python Developer"]["likely_match"])
        self.assertFalse(by_title_a["QA Engineer"]["likely_match"])
        self.assertEqual(by_title_a["Python Developer"]["notification_status"], "not_eligible")
        self.assertIsNone(by_title_a["Python Developer"]["notification_sent_at"])
        self.assertIsNone(by_title_a["Python Developer"]["notification_last_error"])

        self.assertEqual(self._login("b@example.com", "user-b-password-long").status_code, 200)
        feed_b = self.client.get("/api/jobs?minutes=10080&limit=20")
        self.assertEqual(feed_b.status_code, 200)
        by_title_b = {job["title"]: job for job in feed_b.json()["jobs"]}
        self.assertFalse(by_title_b["Python Developer"]["likely_match"])
        self.assertTrue(by_title_b["QA Engineer"]["likely_match"])

    def test_preference_update_re_evaluates_only_the_current_user(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        csrf = self.client.cookies.get("job_beeper_csrf")
        saved = self.client.put(
            "/api/preferences",
            json={"target_roles": ["QA Engineer"], "locations": ["Pune"]},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(saved.status_code, 200)
        updated = self.client.get("/api/jobs?minutes=10080&limit=20")
        by_title = {job["title"]: job for job in updated.json()["jobs"]}
        self.assertFalse(by_title["Python Developer"]["likely_match"])
        self.assertTrue(by_title["QA Engineer"]["likely_match"])

        # The second user's independent profile/evaluations remain unchanged.
        self.assertEqual(self._login("b@example.com", "user-b-password-long").status_code, 200)
        second = self.client.get("/api/jobs?minutes=10080&limit=20")
        second_by_title = {job["title"]: job for job in second.json()["jobs"]}
        self.assertFalse(second_by_title["Python Developer"]["likely_match"])
        self.assertTrue(second_by_title["QA Engineer"]["likely_match"])

    def test_job_detail_uses_the_current_users_evaluation(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            python_job_id = conn.execute(
                "SELECT id FROM jobs WHERE source_job_id='python-1'"
            ).fetchone()[0]
        detail = self.client.get(f"/api/jobs/{python_job_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json()["likely_match"])
        self.assertGreater(detail.json()["match_score"], 0)

    def test_first_admin_created_after_app_startup_gets_legacy_profile_and_feed(self):
        admin = auth.create_first_admin(
            self.db_path, "late-admin@example.com", "late-admin-password-long"
        )
        user_preferences.migrate_first_admin_preferences(self.db_path, radar.get_config())
        self.assertEqual(
            self._login("late-admin@example.com", "late-admin-password-long").status_code,
            200,
        )
        response = self.client.get("/api/jobs?minutes=10080&limit=20")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()["jobs"]), 0)
        with sqlite3.connect(self.db_path) as conn:
            self.assertGreater(
                conn.execute(
                    "SELECT COUNT(*) FROM user_job_evaluations WHERE user_id=?",
                    (admin["id"],),
                ).fetchone()[0],
                0,
            )

    def test_user_daily_summary_counts_only_own_matches(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        summary = self.client.get("/api/daily-summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["matched_jobs"], 1)
        self.assertEqual(summary.json()["alerts_sent"], 0)


if __name__ == "__main__":
    unittest.main()
