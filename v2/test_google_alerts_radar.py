from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException

from cryptography.fernet import Fernet

from v2 import auth, google_alerts_gmail, radar, user_applications, user_notifications, user_preferences


class GoogleAlertsRadarIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "google-alerts-radar.sqlite3"
        self.original_db = radar.DB_PATH
        radar.DB_PATH = self.db
        radar.init_db()
        self.owner = auth.create_user(
            self.db, "owner@example.test", "owner-password-123", role="admin"
        )
        self.other = auth.create_user(
            self.db, "other@example.test", "other-password-123", role="user"
        )
        preferences = {
            "target_roles": ["Software Engineer"],
            "locations": ["Gurugram", "Remote"],
            "skills": ["Python", "REST API"],
            "candidate_experience_years": 2,
            "min_experience_years": 0,
            "max_experience_years": 10,
            "match_threshold": 0,
            "title_exclude": [],
            "excluded_role_terms": [],
            "remote_only": False,
            "max_age_hours": 72,
        }
        for user in (self.owner, self.other):
            user_preferences.ensure_user_preferences(self.db, user["id"])
            user_preferences.save_user_preferences(self.db, user["id"], preferences)

    def tearDown(self):
        radar.DB_PATH = self.original_db
        self.temp_dir.cleanup()

    @staticmethod
    def _posting(suffix: str) -> dict:
        return {
            "title": "Software Engineer",
            "company": "Example Systems",
            "location": "Gurugram, Haryana, IN",
            "description": (
                "Build Python backend services and REST API integrations. "
                "Work with distributed systems and PostgreSQL."
            ),
            "url": f"https://careers.example.com/jobs/{suffix}",
            "canonical_url": f"https://careers.example.com/jobs/{suffix}",
            "source_posted_at": "2026-11-20T00:00:00+00:00",
            "posted_precision": "day",
            "source_domain": "careers.example.com",
            "verification_basis": "public_jsonld_jobposting",
            "verified_at": "2026-11-21T00:00:00+00:00",
        }

    def test_auth_cookies_are_non_secure_only_on_localhost_tunnel(self):
        local_request = Mock()
        local_request.url.hostname = "localhost"
        local_request.url.scheme = "http"
        local_request.client.host = "127.0.0.1"
        local_request.headers.get.return_value = None
        public_request = Mock()
        public_request.url.hostname = "130.210.27.197"
        self.assertFalse(radar._auth_cookie_secure(local_request))
        self.assertTrue(radar._auth_cookie_secure(public_request))

        spoofed_host_request = Mock()
        spoofed_host_request.url.hostname = "localhost"
        spoofed_host_request.url.scheme = "https"
        spoofed_host_request.client.host = "127.0.0.1"
        spoofed_host_request.headers.get.return_value = None
        self.assertTrue(radar._auth_cookie_secure(spoofed_host_request))

    def test_docker_loopback_publish_is_recognized_as_local_ssh_tunnel(self):
        # Host -> 127.0.0.1:8000 reaches the container from its bridge gateway.
        local_request = Mock()
        local_request.url.hostname = "localhost"
        local_request.url.scheme = "http"
        local_request.client.host = "172.18.0.1"
        local_request.headers.get.return_value = None
        local_request.base_url = "http://localhost:8080/"
        with patch.dict("os.environ", {"JOB_BEEPER_PUBLIC_ORIGIN": "https://130.210.27.197"}):
            expected = radar._expected_login_origin(local_request)
        self.assertEqual(expected.scheme, "http")
        self.assertEqual(expected.netloc, "localhost:8080")
        self.assertFalse(radar._auth_cookie_secure(local_request))

        forwarded_request = Mock()
        forwarded_request.url.hostname = "localhost"
        forwarded_request.url.scheme = "http"
        forwarded_request.client.host = "172.18.0.1"
        forwarded_request.headers.get.side_effect = lambda name: (
            "198.51.100.10" if name == "x-forwarded-for" else None
        )
        self.assertFalse(radar._is_localhost_ssh_tunnel(forwarded_request))

    def test_localhost_login_uses_tunnel_origin_instead_of_public_origin_setting(self):
        local_request = Mock()
        local_request.url.hostname = "localhost"
        local_request.url.scheme = "http"
        local_request.client.host = "127.0.0.1"
        local_request.headers.get.return_value = None
        local_request.base_url = "http://localhost:8080/"
        with patch.dict("os.environ", {"JOB_BEEPER_PUBLIC_ORIGIN": "https://130.210.27.197"}):
            expected = radar._expected_login_origin(local_request)
        self.assertEqual(expected.scheme, "http")
        self.assertEqual(expected.netloc, "localhost:8080")

    def test_disconnect_removes_gmail_private_jobs_but_preserves_public_jobs(self):
        public = radar.normalize_job(
            source="workday",
            source_id="public-keep",
            company="Public Systems",
            title="Backend Engineer",
            location="Remote",
            url="https://careers.example.com/jobs/public-keep",
            posted_at=radar.now() - radar.dt.timedelta(hours=1),
            posted_precision="day",
            description="Build public Python services and REST API integrations.",
        )
        radar.upsert_jobs([public])
        private_job_id = radar.record_google_alert_posting(
            self.owner["id"], self._posting("private-delete"), history_backfill=True
        )
        application, created = user_applications.create(
            self.db, self.owner["id"], private_job_id
        )
        self.assertTrue(created)

        key = Fernet.generate_key().decode("ascii")
        config = google_alerts_gmail.GmailIntegrationConfig(
            client_id="client",
            client_secret="secret",
            redirect_uri="https://jobs.example.test" + google_alerts_gmail.CALLBACK_PATH,
            owner_user_id=self.owner["id"],
            owner_email="owner@example.test",
            token_encryption_key=key,
            pubsub_topic="projects/test/topics/google-alerts",
            pubsub_subscription="projects/test/subscriptions/google-alerts",
            push_audience="https://jobs.example.test" + google_alerts_gmail.CALLBACK_PATH,
            push_service_account_email="push@example.iam.gserviceaccount.com",
        )
        google_alerts_gmail.save_credentials(
            self.db, self.owner["id"], "owner@example.test", "refresh",
            google_alerts_gmail.GMAIL_SCOPE, config,
        )
        user_notifications.init_schema(self.db)
        with user_notifications._connect(self.db) as conn:
            row = conn.execute(
                "SELECT canonical_opportunity_id FROM jobs WHERE id=?",
                (private_job_id,),
            ).fetchone()
            conn.execute(
                """INSERT INTO user_notification_settings
                   (user_id,enabled,enabled_at,updated_at)
                   VALUES(?,1,'2026-11-21T00:00:00+00:00','2026-11-21T00:00:00+00:00')
                   ON CONFLICT(user_id) DO UPDATE SET enabled=1""",
                (self.owner["id"],),
            )
            conn.execute(
                """INSERT INTO user_notification_ledger(
                     user_id,canonical_opportunity_id,candidate_job_id,status,
                     backlog_override,created_at,updated_at
                   ) VALUES(?,?,?,'queued',1,'2026-11-21','2026-11-21')""",
                (self.owner["id"], int(row["canonical_opportunity_id"]), private_job_id),
            )
        session = Mock()
        session.post.return_value = Mock(status_code=200)
        google_alerts_gmail.disconnect(self.db, config, session=session)

        with sqlite3.connect(self.db) as conn:
            private_count = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE id=?",
                (private_job_id,),
            ).fetchone()[0]
            public_count = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE source_job_id='public-keep'"
            ).fetchone()[0]
            app_count = conn.execute(
                "SELECT COUNT(*) FROM user_applications WHERE job_id=?",
                (private_job_id,),
            ).fetchone()[0]
            observation_count = conn.execute(
                "SELECT COUNT(*) FROM google_alerts_gmail_opportunities"
            ).fetchone()[0]
            credential_count = conn.execute(
                "SELECT COUNT(*) FROM google_alerts_gmail_credentials"
            ).fetchone()[0]
            queue_count = conn.execute(
                "SELECT COUNT(*) FROM user_notification_ledger WHERE candidate_job_id=?",
                (private_job_id,),
            ).fetchone()[0]
        self.assertEqual(private_count, 0)
        self.assertEqual(public_count, 1)
        self.assertEqual(app_count, 0)
        self.assertEqual(observation_count, 0)
        self.assertEqual(credential_count, 0)
        self.assertEqual(queue_count, 0)

    def test_gmail_observation_reuses_public_job_and_private_job_is_owner_scoped(self):
        public = radar.normalize_job(
            source="workday",
            source_id="public-1",
            company="Example Systems",
            title="Software Engineer",
            location="Gurugram, Haryana, IN",
            url="https://careers.example.com/jobs/public-1",
            posted_at=radar.now() - radar.dt.timedelta(hours=1),
            posted_precision="day",
            description=(
                "Build Python backend services and REST API integrations. "
                "Work with distributed systems and PostgreSQL."
            ),
        )
        radar.upsert_jobs([public])

        reused_job_id = radar.record_google_alert_posting(
            self.owner["id"], self._posting("public-1"), history_backfill=True
        )
        private_job_id = radar.record_google_alert_posting(
            self.owner["id"], self._posting("private-1"), history_backfill=True
        )

        with sqlite3.connect(self.db) as conn:
            public_count = conn.execute(
                """SELECT COUNT(*) FROM jobs
                   WHERE url LIKE '%/public-1'"""
            ).fetchone()[0]
            private = conn.execute(
                """SELECT id,source,source_owner_user_id,canonical_opportunity_id
                   FROM jobs WHERE id=?""",
                (private_job_id,),
            ).fetchone()
            owner_eval = conn.execute(
                "SELECT 1 FROM user_job_evaluations WHERE user_id=? AND job_id=?",
                (self.owner["id"], private_job_id),
            ).fetchone()
            other_eval = conn.execute(
                "SELECT 1 FROM user_job_evaluations WHERE user_id=? AND job_id=?",
                (self.other["id"], private_job_id),
            ).fetchone()
            observations = conn.execute(
                """SELECT COUNT(*) FROM google_alerts_gmail_opportunities
                   WHERE user_id=? AND history_backfill=1""",
                (self.owner["id"],),
            ).fetchone()[0]

        self.assertEqual(reused_job_id, 1)
        self.assertEqual(public_count, 1)
        self.assertEqual(private[0], private_job_id)
        self.assertEqual(private[1], "google_alerts_gmail")
        self.assertEqual(private[2], self.owner["id"])
        self.assertIsNotNone(private[3])
        self.assertIsNotNone(owner_eval)
        self.assertIsNone(other_eval)
        self.assertEqual(observations, 2)

        owner_feed = radar.jobs(minutes=10080, user=self.owner)
        other_feed = radar.jobs(minutes=10080, user=self.other)
        owner_ids = {item["id"] for item in owner_feed["jobs"]}
        other_ids = {item["id"] for item in other_feed["jobs"]}
        self.assertIn(private_job_id, owner_ids)
        self.assertNotIn(private_job_id, other_ids)
        self.assertIn(reused_job_id, other_ids)

        owner_detail = radar.job_detail(private_job_id, user=self.owner)
        self.assertEqual(owner_detail["id"], private_job_id)
        with self.assertRaises(HTTPException) as caught:
            radar.job_detail(private_job_id, user=self.other)
        self.assertEqual(caught.exception.status_code, 404)

        # Saved applications must obey the same per-user visibility boundary.
        application, created = user_applications.create(
            self.db, self.owner["id"], private_job_id
        )
        self.assertTrue(created)
        self.assertEqual(application["job_id"], private_job_id)
        with self.assertRaises(LookupError):
            user_applications.create(self.db, self.other["id"], private_job_id)
        self.assertEqual(user_applications.list_for_user(self.db, self.other["id"]), [])
        self.assertEqual(len(user_applications.list_for_user(self.db, self.owner["id"])), 1)

        # Admin canonical views may show the caller's own private group only.
        owner_opportunities = radar.opportunities(
            minutes=10080, limit=500, user=self.owner
        )["opportunities"]
        other_opportunities = radar.opportunities(
            minutes=10080, limit=500, user=self.other
        )["opportunities"]
        private_canonical_id = int(private[3])
        self.assertIn(private_canonical_id, {row["id"] for row in owner_opportunities})
        self.assertNotIn(private_canonical_id, {row["id"] for row in other_opportunities})
        with self.assertRaises(HTTPException) as caught:
            radar.opportunity_detail(private_canonical_id, user=self.other)
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
