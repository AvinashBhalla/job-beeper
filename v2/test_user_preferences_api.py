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
        from v2 import telegram_linking
        telegram_linking.init_schema(self.db_path)
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


    def test_preference_save_returns_specific_validation_for_missing_target_role(self):
        self.assertEqual(
            self._login("a@example.com", "user-a-password-long").status_code,
            200,
        )
        csrf = self.client.cookies.get("job_beeper_csrf")
        response = self.client.put(
            "/api/preferences",
            json={"locations": ["Bengaluru"]},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "At least one target role is required before accessing the job feed.",
        )

    def test_job_feed_numeric_pagination_has_stable_pages_and_total(self):
        config = {**radar.get_config(), "notifications_enabled": False}
        extra_jobs = [
            radar.normalize_job(
                "naukri", f"python-extra-{index}", "Acme", "Python Developer",
                "Bengaluru, Karnataka, India", f"https://example.com/python-{index}",
                None, "unknown", "Overall experience required: 1-2 years. Build Python APIs.",
            )
            for index in range(5)
        ]
        radar.upsert_jobs(extra_jobs, config)
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)

        first = self.client.get("/api/jobs?minutes=10080&page=1&per_page=2&status=matched&sort_by=created_at&sort_order=desc&search=python")
        second = self.client.get("/api/jobs?minutes=10080&page=2&per_page=2&status=matched&sort_by=created_at&sort_order=desc&search=python")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        first_data = first.json()
        second_data = second.json()
        self.assertEqual(len(first_data["jobs"]), 2)
        self.assertEqual(len(second_data["jobs"]), 2)
        self.assertEqual(first_data["pagination"]["page"], 1)
        self.assertEqual(first_data["pagination"]["per_page"], 2)
        self.assertEqual(first_data["pagination"]["total"], 6)
        self.assertEqual(first_data["pagination"]["total_pages"], 3)
        self.assertTrue(first_data["pagination"]["has_next"])
        self.assertTrue(second_data["pagination"]["has_previous"])
        self.assertEqual(
            set(job["id"] for job in first_data["jobs"]).intersection(
                job["id"] for job in second_data["jobs"]
            ),
            set(),
        )
        self.assertEqual(self.client.get("/api/jobs?status=all").status_code, 403)
        self.assertEqual(self.client.get("/api/jobs?status=not-a-status").status_code, 422)

    def test_job_feed_exposes_experience_evidence_provenance(self):
        config = {**radar.get_config(), "notifications_enabled": False}
        jobs = [
            radar.normalize_job(
                "linkedin", "python-employer-exp", "Acme", "Python Developer",
                "Bengaluru, Karnataka, India", "https://example.com/linkedin-exp",
                None, "unknown", "Experience: 1-2 Years. Build Python backend services.",
            ),
            radar.normalize_job(
                "naukri", "python-description-exp", "Acme", "Python Developer",
                "Bengaluru, Karnataka, India", "https://example.com/naukri-exp",
                None, "unknown", "Overall experience required: 1-2 years. Build Python APIs.",
            ),
            radar.normalize_job(
                "instahyre", "python-inferred-exp", "Acme", "Python Developer",
                "Bengaluru, Karnataka, India", "https://example.com/instahyre-exp",
                None, "unknown", "Work with Python and Django; 2 years of Python experience preferred.",
            ),
        ]
        radar.upsert_jobs(jobs, config)
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        response = self.client.get("/api/jobs?minutes=10080&page=1&per_page=20&status=matched")
        self.assertEqual(response.status_code, 200, response.text)
        by_source_job_id = {job["source_job_id"]: job for job in response.json()["jobs"]}
        self.assertEqual(by_source_job_id["python-employer-exp"]["experience_provenance"], "employer_stated")
        self.assertEqual(by_source_job_id["python-employer-exp"]["experience_confidence"], "high")
        self.assertEqual(by_source_job_id["python-description-exp"]["experience_provenance"], "description")
        self.assertEqual(by_source_job_id["python-description-exp"]["experience_confidence"], "medium")
        self.assertEqual(by_source_job_id["python-inferred-exp"]["experience_provenance"], "inferred")
        self.assertEqual(by_source_job_id["python-inferred-exp"]["experience_confidence"], "low")

    def test_weaker_experience_observation_does_not_overwrite_stronger_provenance(self):
        config = {**radar.get_config(), "notifications_enabled": False}
        employer_stated = radar.normalize_job(
            "linkedin", "same-source-job", "Acme", "Python Developer",
            "Bengaluru, Karnataka, India", "https://example.com/same-source-job",
            None, "unknown", "Experience: 4-6 Years. Build Python backend services.",
        )
        weaker_snippet = radar.normalize_job(
            "linkedin", "same-source-job", "Acme", "Python Developer",
            "Bengaluru, Karnataka, India", "https://example.com/same-source-job",
            None, "unknown", "2 years of Python experience preferred.",
        )
        radar.upsert_jobs([employer_stated], config)
        radar.upsert_jobs([weaker_snippet], config)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT experience_min_years, experience_max_years, experience_provenance "
                "FROM jobs WHERE source_job_id='same-source-job'"
            ).fetchone()
        self.assertEqual(row, (4.0, 6.0, "employer_stated"))

    def test_job_feed_filters_and_match_sort_apply_before_pagination(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        response = self.client.get(
            "/api/jobs?minutes=10080&page=1&per_page=20&status=matched&source=naukri&min_score=55&sort_by=match_score&sort_order=desc"
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(len(data["jobs"]), 1)
        self.assertEqual(data["jobs"][0]["source"], "naukri")

    def test_telegram_linking_requires_authentication_and_configuration(self):
        response = self.client.post("/api/telegram/link")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        response = self.client.post("/api/telegram/link", headers={"X-CSRF-Token": self.client.cookies.get("job_beeper_csrf")})
        self.assertEqual(response.status_code, 503)

    def test_member_notification_settings_are_opt_in_and_require_linked_chat_and_csrf(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        csrf = self.client.cookies.get("job_beeper_csrf")
        initial = self.client.get("/api/notifications/settings")
        self.assertEqual(initial.status_code, 200)
        self.assertFalse(initial.json()["settings"]["enabled"])
        self.assertFalse(initial.json()["telegram_connected"])
        denied_csrf = self.client.put("/api/notifications/settings", json={"enabled": True})
        self.assertEqual(denied_csrf.status_code, 403)
        not_linked = self.client.put("/api/notifications/settings", json={"enabled": True}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(not_linked.status_code, 409)
        from v2 import telegram_linking
        token, _ = telegram_linking.create_link_token(self.db_path, self.user_a["id"])
        self.assertIsNotNone(telegram_linking.consume_link_token(self.db_path, token, "123456789", "private"))
        enabled = self.client.put("/api/notifications/settings", json={"enabled": True}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(enabled.status_code, 200, enabled.text)
        self.assertTrue(enabled.json()["settings"]["enabled"])
        self.assertIsNotNone(enabled.json()["settings"]["enabled_at"])
        self.assertEqual(self.client.put("/api/notifications/settings", json={"enabled": "yes"}, headers={"X-CSRF-Token": csrf}).status_code, 422)
        disabled = self.client.put("/api/notifications/settings", json={"enabled": False}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()["settings"]["enabled"])

    def test_telegram_link_api_and_webhook_are_secret_protected(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        csrf = self.client.cookies.get("job_beeper_csrf")
        with patch.dict("os.environ", {
            "JOB_BEEPER_TELEGRAM_BOT_USERNAME": "JobBeeperTestBot",
            "JOB_RADAR_TELEGRAM_BOT_TOKEN": "test-bot-token",
            "JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET": "test-webhook-secret-value",
        }):
            status = self.client.get("/api/telegram/status")
            self.assertTrue(status.json()["configured"])
            link = self.client.post("/api/telegram/link", headers={"X-CSRF-Token": csrf})
            self.assertEqual(link.status_code, 200, link.text)
            self.assertIn("https://t.me/JobBeeperTestBot?start=", link.json()["url"])
            token = link.json()["url"].split("start=", 1)[1]
            update = {"update_id": 1, "message": {"text": f"/start {token}", "chat": {"id": 123456, "type": "private"}}}
            denied = self.client.post("/api/telegram/webhook", json=update)
            self.assertEqual(denied.status_code, 403)
            with patch.object(radar, "_send_telegram_link_confirmation") as confirmation:
                linked = self.client.post("/api/telegram/webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret-value"})
                confirmation.assert_called_once()
            self.assertEqual(linked.status_code, 200, linked.text)
            status = self.client.get("/api/telegram/status")
            self.assertTrue(status.json()["connection"]["connected"])
            replay = self.client.post("/api/telegram/webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret-value"})
            self.assertEqual(replay.status_code, 200)
            disconnected = self.client.delete("/api/telegram/link", headers={"X-CSRF-Token": csrf})
            self.assertEqual(disconnected.status_code, 200)
            self.assertFalse(self.client.get("/api/telegram/status").json()["connection"]["connected"])

    def test_telegram_link_endpoints_reject_admin_and_mutations_require_csrf(self):
        admin = auth.create_first_admin(self.db_path, "admin@example.com", "admin-password-long")
        self.assertEqual(self._login("admin@example.com", "admin-password-long").status_code, 200)
        self.assertEqual(self.client.get("/api/telegram/status").status_code, 403)
        self.assertEqual(self.client.delete("/api/telegram/link").status_code, 403)

    def test_telegram_webhook_rejects_non_private_chat_and_unknown_commands(self):
        with patch.dict("os.environ", {
            "JOB_RADAR_TELEGRAM_BOT_TOKEN": "test-bot-token",
            "JOB_BEEPER_TELEGRAM_WEBHOOK_SECRET": "test-webhook-secret-value",
        }):
            update = {"message": {"text": "/start abcdefghijklmnopqrstuvwxyz", "chat": {"id": -100123, "type": "group"}}}
            response = self.client.post("/api/telegram/webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret-value"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"ok": True})

    def test_resume_parse_requires_authentication(self):
        response = self.client.post(
            "/api/preferences/resume",
            files={"file": ("resume.docx", b"PK-invalid", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(response.status_code, 401)

    def test_resume_parse_requires_csrf_and_does_not_save_preferences(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        before = user_preferences.get_user_preferences(self.db_path, self.user_a["id"])
        content = __import__("io").BytesIO()
        from docx import Document
        document = Document()
        document.add_paragraph("Python Developer. Bengaluru. Total experience: 4 years.")
        document.save(content)
        data = content.getvalue()
        without_csrf = self.client.post(
            "/api/preferences/resume",
            files={"file": ("resume.docx", data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(without_csrf.status_code, 403)
        csrf = self.client.cookies.get("job_beeper_csrf")
        parsed = self.client.post(
            "/api/preferences/resume",
            files={"file": ("resume.docx", data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(parsed.status_code, 200, parsed.text)
        self.assertIn("Python Developer", parsed.json()["suggestions"]["target_roles"])
        after = user_preferences.get_user_preferences(self.db_path, self.user_a["id"])
        self.assertEqual(before["version"], after["version"])
        self.assertEqual(before["target_roles"], after["target_roles"])

    def test_resume_parse_rejects_mismatched_mime_type(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        csrf = self.client.cookies.get("job_beeper_csrf")
        response = self.client.post(
            "/api/preferences/resume",
            files={"file": ("resume.pdf", b"%PDF-1.7\ninvalid", "text/plain")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 422)

    def test_resume_parse_rejects_invalid_file_without_leaking_details(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        csrf = self.client.cookies.get("job_beeper_csrf")
        response = self.client.post(
            "/api/preferences/resume",
            files={"file": ("resume.pdf", b"not-a-pdf", "application/pdf")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("/tmp/", response.text)

    def test_each_user_receives_independent_job_evaluations(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        feed_a = self.client.get("/api/jobs?minutes=10080&limit=20")
        self.assertEqual(feed_a.status_code, 200)
        by_title_a = {job["title"]: job for job in feed_a.json()["jobs"]}
        self.assertEqual(set(by_title_a), {"Python Developer"})
        self.assertTrue(by_title_a["Python Developer"]["likely_match"])
        self.assertEqual(by_title_a["Python Developer"]["notification_status"], "not_eligible")
        self.assertIsNone(by_title_a["Python Developer"]["notification_sent_at"])
        self.assertIsNone(by_title_a["Python Developer"]["notification_last_error"])
        # Filter the user's matches in SQL before LIMIT; otherwise the newer
        # non-match can consume the one-row cap and hide this older match.
        capped = self.client.get("/api/jobs?minutes=10080&limit=1")
        self.assertEqual(capped.status_code, 200)
        self.assertEqual([job["title"] for job in capped.json()["jobs"]], ["Python Developer"])

        self.assertEqual(self._login("b@example.com", "user-b-password-long").status_code, 200)
        feed_b = self.client.get("/api/jobs?minutes=10080&limit=20")
        self.assertEqual(feed_b.status_code, 200)
        by_title_b = {job["title"]: job for job in feed_b.json()["jobs"]}
        self.assertEqual(set(by_title_b), {"QA Engineer"})
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
        self.assertEqual(set(by_title), {"QA Engineer"})
        self.assertTrue(by_title["QA Engineer"]["likely_match"])

        # The second user's independent profile/evaluations remain unchanged.
        self.assertEqual(self._login("b@example.com", "user-b-password-long").status_code, 200)
        second = self.client.get("/api/jobs?minutes=10080&limit=20")
        second_by_title = {job["title"]: job for job in second.json()["jobs"]}
        self.assertEqual(set(second_by_title), {"QA Engineer"})
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

    def test_member_can_read_sanitized_source_health_without_collector_errors(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO source_runs(source, started_at, finished_at, jobs_seen, new_jobs, error) VALUES (?, ?, ?, ?, ?, ?)",
                ("naukri", "2026-11-06T00:00:00+00:00", "2026-11-06T00:00:05+00:00", 12, 2, "private collector traceback"),
            )
        response = self.client.get("/api/source-status/summary")
        self.assertEqual(response.status_code, 200)
        naukri = next(item for item in response.json()["sources"] if item["source"] == "naukri")
        self.assertEqual(naukri["jobs_seen"], 12)
        self.assertEqual(naukri["new_jobs"], 2)
        self.assertNotIn("last_error", naukri)
        self.assertNotIn("error", naukri["runtime"])
        self.assertEqual(self.client.get("/api/source-status").status_code, 403)

    def test_user_daily_summary_counts_only_own_matches(self):
        self.assertEqual(self._login("a@example.com", "user-a-password-long").status_code, 200)
        summary = self.client.get("/api/daily-summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["matched_jobs"], 1)
        self.assertEqual(summary.json()["alerts_sent"], 0)


if __name__ == "__main__":
    unittest.main()
