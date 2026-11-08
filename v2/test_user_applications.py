"""API tests for server-owned, tenant-isolated application tracking."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from v2 import auth, radar, user_applications, user_preferences


class UserApplicationsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "applications.sqlite3"
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.config_patch = patch.object(radar, "RUNTIME_CONFIG_PATH", self.config_path)
        self.db_patch.start()
        self.config_patch.start()
        radar.init_db()
        self.user_a = auth.create_user(self.db_path, "a@example.com", "user-a-password-long")
        self.user_b = auth.create_user(self.db_path, "b@example.com", "user-b-password-long")
        user_preferences.save_user_preferences(
            self.db_path, self.user_a["id"],
            {"target_roles": ["Python Developer"], "locations": ["Bengaluru"]},
        )
        user_preferences.save_user_preferences(
            self.db_path, self.user_b["id"],
            {"target_roles": ["QA Engineer"], "locations": ["Pune"]},
        )
        config = {**radar.get_config(), "notifications_enabled": False}
        radar.upsert_jobs([
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
        ], config)
        self.python_job_id = self._job_id("python-1")
        self.qa_job_id = self._job_id("qa-1")
        self.client = TestClient(radar.app, base_url="https://testserver")

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def _job_id(self, source_job_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return int(conn.execute(
                "SELECT id FROM jobs WHERE source_job_id=?", (source_job_id,)
            ).fetchone()[0])

    def _login(self, email: str, password: str) -> str:
        response = self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return self.client.cookies.get("job_beeper_csrf")

    def test_applications_are_private_and_same_job_is_independent_per_user(self):
        csrf_a = self._login("a@example.com", "user-a-password-long")
        created = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id},
            headers={"X-CSRF-Token": csrf_a},
        )
        self.assertEqual(created.status_code, 201, created.text)
        app_a = created.json()["application"]
        self.assertEqual(app_a["job_id"], self.python_job_id)
        self.assertEqual(app_a["status"], "Applied")

        self.assertEqual(len(self.client.get("/api/applications").json()["applications"]), 1)
        csrf_b = self._login("b@example.com", "user-b-password-long")
        self.assertEqual(self.client.get("/api/applications").json()["applications"], [])
        created_b = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id},
            headers={"X-CSRF-Token": csrf_b},
        )
        self.assertEqual(created_b.status_code, 201, created_b.text)
        app_b = created_b.json()["application"]
        self.assertNotEqual(app_a["id"], app_b["id"])
        self.assertEqual(len(self.client.get("/api/applications").json()["applications"]), 1)

        csrf_a = self._login("a@example.com", "user-a-password-long")
        self.assertEqual(self.client.get(f"/api/applications/{app_b['id']}").status_code, 405)

    def test_duplicate_canonical_application_is_idempotent(self):
        csrf = self._login("a@example.com", "user-a-password-long")
        first = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id, "notes": "Applied on company site"},
            headers={"X-CSRF-Token": csrf},
        )
        second = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["application"]["id"], second.json()["application"]["id"])
        self.assertEqual(second.json()["application"]["notes"], "Applied on company site")

    def test_status_notes_and_delete_are_owner_scoped(self):
        csrf_a = self._login("a@example.com", "user-a-password-long")
        created = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id},
            headers={"X-CSRF-Token": csrf_a},
        ).json()["application"]
        application_id = created["id"]

        csrf_b = self._login("b@example.com", "user-b-password-long")
        denied = self.client.patch(
            f"/api/applications/{application_id}",
            json={"status": "Offer"},
            headers={"X-CSRF-Token": csrf_b},
        )
        self.assertEqual(denied.status_code, 404)
        denied_delete = self.client.delete(
            f"/api/applications/{application_id}",
            headers={"X-CSRF-Token": csrf_b},
        )
        self.assertEqual(denied_delete.status_code, 404)

        csrf_a = self._login("a@example.com", "user-a-password-long")
        updated = self.client.patch(
            f"/api/applications/{application_id}",
            json={"status": "Interviewing", "notes": "Recruiter call next week"},
            headers={"X-CSRF-Token": csrf_a},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["application"]["status"], "Interviewing")
        self.assertEqual(updated.json()["application"]["notes"], "Recruiter call next week")
        removed = self.client.delete(
            f"/api/applications/{application_id}",
            headers={"X-CSRF-Token": csrf_a},
        )
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(self.client.get("/api/applications").json()["applications"], [])

    def test_legacy_local_storage_import_is_idempotent_and_skips_missing_jobs(self):
        csrf = self._login("a@example.com", "user-a-password-long")
        payload = {"applications": [
            {"id": str(self.python_job_id), "title": "Python Developer", "company": "Acme",
             "applied_at": "2026-11-01T10:00:00.000Z", "status": "Interviewing", "notes": "Old note"},
            {"id": str(self.python_job_id), "status": "Applied"},
            {"id": "999999", "status": "Applied"},
            {"id": "not-an-int", "status": "Applied"},
        ]}
        first = self.client.post(
            "/api/applications/import", json=payload,
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["imported"], 1)
        self.assertEqual(first.json()["already_present"], 1)
        self.assertEqual(first.json()["skipped"], 2)
        imported = self.client.get("/api/applications").json()["applications"][0]
        self.assertEqual(imported["status"], "Interviewing")
        self.assertEqual(imported["notes"], "Old note")

        second = self.client.post(
            "/api/applications/import", json=payload,
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(second.json()["imported"], 0)
        self.assertEqual(second.json()["already_present"], 2)

    def test_canonical_identity_rebuild_preserves_application_records(self):
        csrf = self._login("a@example.com", "user-a-password-long")
        for job_id, note in ((self.python_job_id, "Python application"), (self.qa_job_id, "QA application")):
            response = self.client.post(
                "/api/applications", json={"job_id": job_id, "notes": note},
                headers={"X-CSRF-Token": csrf},
            )
            self.assertEqual(response.status_code, 201, response.text)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE canonical_opportunities SET identity_version=1")
            conn.commit()

        radar.backfill_canonical_opportunities()
        user_applications.reconcile_canonical_ids(self.db_path)
        records = self.client.get("/api/applications").json()["applications"]
        self.assertEqual(len(records), 2)
        with sqlite3.connect(self.db_path) as conn:
            mismatches = conn.execute("""SELECT COUNT(*) FROM user_applications a
                JOIN jobs j ON j.id=a.job_id
                WHERE a.canonical_opportunity_id<>j.canonical_opportunity_id""").fetchone()[0]
        self.assertEqual(mismatches, 0)

    def test_dedupe_merge_reconciles_two_records_for_same_opportunity(self):
        csrf = self._login("a@example.com", "user-a-password-long")
        first = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id, "notes": "First record"},
            headers={"X-CSRF-Token": csrf},
        )
        second = self.client.post(
            "/api/applications", json={"job_id": self.qa_job_id, "notes": "Second record"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        with sqlite3.connect(self.db_path) as conn:
            canonical_id = conn.execute(
                "SELECT canonical_opportunity_id FROM jobs WHERE id=?", (self.qa_job_id,)
            ).fetchone()[0]
            # The earlier application now points at a canonical ID already
            # used by a later record, exercising the unique-key merge order.
            conn.execute(
                "UPDATE jobs SET canonical_opportunity_id=? WHERE id=?",
                (canonical_id, self.python_job_id),
            )
            conn.commit()
        user_applications.reconcile_canonical_ids(self.db_path)
        records = self.client.get("/api/applications").json()["applications"]
        self.assertEqual(len(records), 1)
        self.assertIn("First record", records[0]["notes"])
        self.assertIn("Second record", records[0]["notes"])

    def test_application_mutations_require_authentication_and_csrf(self):
        denied = self.client.post("/api/applications", json={"job_id": self.python_job_id})
        self.assertEqual(denied.status_code, 401)
        csrf = self._login("a@example.com", "user-a-password-long")
        no_csrf = self.client.post("/api/applications", json={"job_id": self.python_job_id})
        self.assertEqual(no_csrf.status_code, 403)
        bad_status = self.client.post(
            "/api/applications", json={"job_id": self.python_job_id, "status": "Pretending"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(bad_status.status_code, 422)


if __name__ == "__main__":
    unittest.main()

