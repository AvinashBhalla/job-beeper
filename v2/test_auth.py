import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

AUTH_AVAILABLE = importlib.util.find_spec("v2.auth") is not None
if AUTH_AVAILABLE:
    from v2 import auth


@unittest.skipUnless(AUTH_AVAILABLE, "v2.auth has not been implemented yet")
class AuthPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "auth-test.sqlite3"
        auth.init_auth_schema(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_auth_schema_is_additive_to_existing_job_data(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
            conn.execute("INSERT INTO jobs (title) VALUES ('Existing job')")
        auth.init_auth_schema(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT title FROM jobs").fetchone()[0], "Existing job")
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "sessions", "login_attempts"}.issubset(tables))

    def test_email_is_normalized_and_duplicate_accounts_are_rejected(self):
        user = auth.create_user(self.db_path, "  Person@Example.COM ", "correct horse battery staple")
        self.assertEqual(user["email"], "person@example.com")
        with self.assertRaises(ValueError):
            auth.create_user(self.db_path, "PERSON@example.com", "another correct horse battery staple")

    def test_password_is_argon2id_hashed_and_verified(self):
        auth.create_user(self.db_path, "person@example.com", "correct horse battery staple")
        with sqlite3.connect(self.db_path) as conn:
            stored_hash = conn.execute("SELECT password_hash FROM users").fetchone()[0]
        self.assertNotEqual(stored_hash, "correct horse battery staple")
        self.assertTrue(stored_hash.startswith("$argon2id$"))
        self.assertEqual(auth.verify_user(self.db_path, "PERSON@example.com", "correct horse battery staple")["email"], "person@example.com")
        self.assertIsNone(auth.verify_user(self.db_path, "person@example.com", "incorrect password value"))
        self.assertIsNone(auth.verify_user(self.db_path, "missing@example.com", "correct horse battery staple"))

    def test_password_and_role_validation_reject_weak_or_unknown_values(self):
        with self.assertRaises(ValueError):
            auth.create_user(self.db_path, "person@example.com", "short")
        with self.assertRaises(ValueError):
            auth.create_user(self.db_path, "person@example.com", "correct horse battery staple", role="owner")
        self.assertEqual(auth.create_user(self.db_path, "admin@example.com", "correct horse battery staple", role="admin")["role"], "admin")

    def test_session_and_csrf_tokens_are_stored_only_as_hashes(self):
        user = auth.create_user(self.db_path, "person@example.com", "correct horse battery staple")
        session_token, csrf_token, expires_at = auth.create_session(self.db_path, user["id"])
        self.assertTrue(expires_at)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT token_hash, csrf_token_hash FROM sessions").fetchone()
        self.assertNotEqual(row[0], session_token)
        self.assertNotEqual(row[1], csrf_token)
        self.assertEqual(auth.get_session_user(self.db_path, session_token)["id"], user["id"])
        self.assertTrue(auth.validate_csrf(self.db_path, session_token, csrf_token))
        self.assertFalse(auth.validate_csrf(self.db_path, session_token, "wrong-csrf-token"))

    def test_expired_session_is_rejected(self):
        user = auth.create_user(self.db_path, "person@example.com", "correct horse battery staple")
        session_token, _, _ = auth.create_session(self.db_path, user["id"], ttl_seconds=60)
        with patch("v2.auth.time.time", return_value=1_800_000_061):
            self.assertIsNone(auth.get_session_user(self.db_path, session_token))

    def test_revoked_session_is_rejected_and_cannot_pass_csrf(self):
        user = auth.create_user(self.db_path, "person@example.com", "correct horse battery staple")
        session_token, csrf_token, _ = auth.create_session(self.db_path, user["id"])
        self.assertTrue(auth.revoke_session(self.db_path, session_token))
        self.assertIsNone(auth.get_session_user(self.db_path, session_token))
        self.assertFalse(auth.validate_csrf(self.db_path, session_token, csrf_token))
        self.assertFalse(auth.revoke_session(self.db_path, session_token))

    def test_disabled_user_cannot_reuse_an_existing_session(self):
        user = auth.create_user(self.db_path, "person@example.com", "correct horse battery staple")
        session_token, _, _ = auth.create_session(self.db_path, user["id"])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE users SET status='disabled' WHERE id=?", (user["id"],))
        self.assertIsNone(auth.get_session_user(self.db_path, session_token))

    def test_login_rate_limit_persists_and_resets_after_success(self):
        identity = ("person@example.com", "192.0.2.15")
        with patch("v2.auth.time.time", return_value=1_800_000_000):
            self.assertFalse(auth.check_login_rate_limit(self.db_path, *identity))
            for _ in range(5):
                auth.record_login_attempt(self.db_path, *identity, success=False)
            self.assertTrue(auth.check_login_rate_limit(self.db_path, *identity))
        # Reopening the same database must retain the throttle.
        auth.init_auth_schema(self.db_path)
        with patch("v2.auth.time.time", return_value=1_800_000_899):
            self.assertTrue(auth.check_login_rate_limit(self.db_path, *identity))
        with patch("v2.auth.time.time", return_value=1_800_000_900):
            self.assertFalse(auth.check_login_rate_limit(self.db_path, *identity))
            for _ in range(5):
                auth.record_login_attempt(self.db_path, *identity, success=False)
            auth.record_login_attempt(self.db_path, *identity, success=True)
            self.assertFalse(auth.check_login_rate_limit(self.db_path, *identity))


class AuthModuleAvailabilityTests(unittest.TestCase):
    def test_auth_persistence_module_is_available(self):
        self.assertTrue(AUTH_AVAILABLE, "v2.auth must provide the SQLite identity and session primitives")


if __name__ == "__main__":
    unittest.main()
