"""Tests for tenant-owned candidate preferences and evaluation storage."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from v2 import auth, user_preferences


class UserPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "preferences.db"
        auth.init_auth_schema(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY)")
        user_preferences.init_preferences_schema(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _user(self, email: str, role: str = "user") -> dict:
        user = auth.create_user(self.db_path, email, "a-strong-test-password", role=role)
        user_preferences.ensure_user_preferences(self.db_path, user["id"])
        return user

    def test_new_user_gets_empty_incomplete_preferences(self):
        user = self._user("new@example.com")
        preferences = user_preferences.get_user_preferences(self.db_path, user["id"])
        self.assertEqual(preferences["target_roles"], [])
        self.assertEqual(preferences["locations"], [])
        self.assertEqual(preferences["max_experience_years"], 30.0)
        self.assertFalse(preferences["onboarding_complete"])

    def test_get_preferences_is_read_only_and_missing_row_is_not_created(self):
        user = auth.create_user(
            self.db_path, "read-only@example.com", "a-strong-test-password", role="user"
        )
        defaults = user_preferences.get_user_preferences(self.db_path, user["id"])
        self.assertEqual(defaults["target_roles"], [])
        self.assertEqual(defaults["version"], 0)
        self.assertFalse(defaults["onboarding_complete"])
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM user_preferences WHERE user_id=?", (user["id"],)
            ).fetchone()[0]
        self.assertEqual(count, 0)
        user_preferences.ensure_user_preferences(self.db_path, user["id"])
        self.assertEqual(
            user_preferences.get_user_preferences(self.db_path, user["id"])["target_roles"], []
        )

    def test_role_and_location_are_both_required_to_complete_onboarding(self):
        user = self._user("setup@example.com")
        with self.assertRaisesRegex(ValueError, "target role"):
            user_preferences.save_user_preferences(
                self.db_path, user["id"], {"locations": ["Bengaluru"]}
            )
        with self.assertRaisesRegex(ValueError, "target location"):
            user_preferences.save_user_preferences(
                self.db_path, user["id"], {"target_roles": ["Python Developer"]}
            )
        saved = user_preferences.save_user_preferences(
            self.db_path,
            user["id"],
            {"target_roles": ["Python Developer"], "locations": ["Bengaluru"]},
        )
        self.assertTrue(saved["onboarding_complete"])

    def test_remote_only_can_complete_onboarding_without_a_target_location(self):
        user = self._user("remote-worldwide@example.com")
        saved = user_preferences.save_user_preferences(
            self.db_path,
            user["id"],
            {"target_roles": ["Python Developer"], "locations": [], "remote_only": True},
        )
        self.assertTrue(saved["onboarding_complete"])
        self.assertEqual(saved["locations"], [])
        self.assertTrue(saved["remote_only"])

    def test_remote_only_without_target_role_does_not_complete_onboarding(self):
        user = self._user("remote-no-role@example.com")
        with self.assertRaisesRegex(ValueError, "target role"):
            user_preferences.save_user_preferences(
                self.db_path,
                user["id"],
                {"target_roles": [], "locations": [], "remote_only": True},
            )

    def test_preferences_are_isolated_between_users(self):
        first = self._user("first@example.com")
        second = self._user("second@example.com")
        user_preferences.save_user_preferences(
            self.db_path, first["id"],
            {"target_roles": ["Python Developer"], "locations": ["Bengaluru"]},
        )
        user_preferences.save_user_preferences(
            self.db_path, second["id"],
            {"target_roles": ["QA Engineer"], "locations": ["Pune"]},
        )
        self.assertEqual(
            user_preferences.get_user_preferences(self.db_path, first["id"])["target_roles"],
            ["Python Developer"],
        )
        self.assertEqual(
            user_preferences.get_user_preferences(self.db_path, second["id"])["target_roles"],
            ["QA Engineer"],
        )

    def test_first_admin_migration_copies_only_candidate_fields_once(self):
        admin = auth.create_first_admin(self.db_path, "admin@example.com", "a-strong-test-password")
        global_config = {
            "target_roles": ["Software Engineer"],
            "locations": ["Gurugram"],
            "skills": ["Python"],
            "source_enabled": {"naukri": True},
            "notifications_enabled": True,
            "match_threshold": 67,
        }
        self.assertTrue(
            user_preferences.migrate_first_admin_preferences(self.db_path, global_config)
        )
        self.assertFalse(
            user_preferences.migrate_first_admin_preferences(
                self.db_path,
                {**global_config, "target_roles": ["Changed role"]},
            )
        )
        preferences = user_preferences.get_user_preferences(self.db_path, admin["id"])
        self.assertEqual(preferences["target_roles"], ["Software Engineer"])
        self.assertEqual(preferences["match_threshold"], 67)
        self.assertNotIn("source_enabled", preferences)
        self.assertNotIn("notifications_enabled", preferences)

    def test_new_user_never_inherits_admin_profile(self):
        admin = auth.create_first_admin(self.db_path, "admin@example.com", "a-strong-test-password")
        user_preferences.migrate_first_admin_preferences(
            self.db_path,
            {"target_roles": ["Software Engineer"], "locations": ["Gurugram"]},
        )
        user = self._user("new-user@example.com")
        preferences = user_preferences.get_user_preferences(self.db_path, user["id"])
        self.assertEqual(preferences["target_roles"], [])
        self.assertEqual(preferences["locations"], [])

    def test_evaluation_table_is_unique_per_user_and_job(self):
        user = self._user("eval@example.com")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO jobs (id) VALUES (1)")
            conn.execute("""INSERT INTO user_job_evaluations
                (user_id, job_id, preference_fingerprint, evaluated_at, match, score)
                VALUES (?, 1, 'fingerprint', '2026-11-06T00:00:00+00:00', 1, 80)""", (user["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("""INSERT INTO user_job_evaluations
                    (user_id, job_id, preference_fingerprint, evaluated_at, match, score)
                    VALUES (?, 1, 'other', '2026-11-06T00:00:00+00:00', 0, 0)""", (user["id"],))

    def test_invalid_or_system_owned_fields_are_rejected(self):
        user = self._user("invalid@example.com")
        with self.assertRaisesRegex(ValueError, "Unsupported preference fields"):
            user_preferences.save_user_preferences(
                self.db_path, user["id"],
                {"target_roles": ["Engineer"], "locations": ["Pune"], "source_enabled": {"naukri": True}},
            )
        with self.assertRaisesRegex(ValueError, "remote_only must be a boolean"):
            user_preferences.save_user_preferences(
                self.db_path, user["id"],
                {"target_roles": ["Engineer"], "locations": ["Pune"], "remote_only": "false"},
            )

    def test_save_increments_preference_version(self):
        user = self._user("version@example.com")
        first = user_preferences.save_user_preferences(
            self.db_path, user["id"],
            {"target_roles": ["Python Developer"], "locations": ["Bengaluru"]},
        )
        second = user_preferences.save_user_preferences(
            self.db_path, user["id"],
            {"target_roles": ["Backend Engineer"], "locations": ["Pune"]},
        )
        self.assertEqual(first["version"], 1)
        self.assertEqual(second["version"], 2)

    def test_fingerprint_is_stable_and_changes_with_preferences(self):
        first = {"target_roles": ["Python Developer"], "locations": ["Bengaluru"]}
        second = {"locations": ["Bengaluru"], "target_roles": ["Python Developer"]}
        third = {"target_roles": ["QA Engineer"], "locations": ["Bengaluru"]}
        self.assertEqual(
            user_preferences.preferences_fingerprint(first, 3),
            user_preferences.preferences_fingerprint(second, 3),
        )
        self.assertNotEqual(
            user_preferences.preferences_fingerprint(first, 3),
            user_preferences.preferences_fingerprint(third, 3),
        )


if __name__ == "__main__":
    unittest.main()
