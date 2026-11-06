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


from contextlib import redirect_stderr, redirect_stdout
import io
import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from v2 import radar


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "api-auth.sqlite3"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.db_patch.start()
        auth.init_auth_schema(self.db_path)
        self.admin = auth.create_user(self.db_path, "admin@example.com", "correct horse battery staple", role="admin")
        self.user = auth.create_user(self.db_path, "user@example.com", "another correct horse battery staple")
        self.client = TestClient(radar.app, base_url="https://testserver")

    def tearDown(self):
        self.client.close()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def login(self, email="user@example.com", password="another correct horse battery staple"):
        return self.client.post("/api/auth/login", json={"email": email, "password": password})

    def test_login_sets_secure_opaque_session_and_readable_csrf_cookies(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"], {"id": self.user["id"], "email": "user@example.com", "role": "user", "status": "active"})
        self.assertNotIn("token", response.json())
        set_cookie = response.headers.get_list("set-cookie")
        session_cookie = next(value for value in set_cookie if value.startswith("job_beeper_session="))
        csrf_cookie = next(value for value in set_cookie if value.startswith("job_beeper_csrf="))
        self.assertIn("httponly", session_cookie.lower())
        self.assertIn("secure", session_cookie.lower())
        self.assertIn("samesite=lax", session_cookie.lower())
        self.assertNotIn("httponly", csrf_cookie.lower())
        self.assertIn("secure", csrf_cookie.lower())
        self.assertIn("samesite=lax", csrf_cookie.lower())

    def test_failed_login_does_not_revoke_the_current_valid_session(self):
        self.assertEqual(self.login().status_code, 200)
        existing_session = self.client.cookies.get("job_beeper_session")
        failed = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "incorrect password value"})
        self.assertEqual(failed.status_code, 401)
        self.assertIsNotNone(auth.get_session_user(self.db_path, existing_session))

    def test_login_revokes_an_existing_session_before_issuing_a_new_one(self):
        self.assertEqual(self.login().status_code, 200)
        old_session = self.client.cookies.get("job_beeper_session")
        self.assertIsNotNone(auth.get_session_user(self.db_path, old_session))
        self.assertEqual(self.login().status_code, 200)
        self.assertIsNone(auth.get_session_user(self.db_path, old_session))
        self.assertIsNotNone(auth.get_session_user(self.db_path, self.client.cookies.get("job_beeper_session")))

    def test_current_user_endpoint_returns_safe_session_identity(self):
        self.assertEqual(self.login().status_code, 200)
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "user@example.com")
        self.assertNotIn("password_hash", response.text)

    def test_unknown_email_and_wrong_password_share_generic_failure(self):
        unknown = self.client.post("/api/auth/login", json={"email": "missing@example.com", "password": "incorrect password value"})
        wrong = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "incorrect password value"})
        self.assertEqual((unknown.status_code, wrong.status_code), (401, 401))
        self.assertEqual(unknown.json(), wrong.json())
        self.assertEqual(unknown.json()["detail"], "Invalid email or password.")

    def test_login_is_rate_limited_after_five_failed_attempts(self):
        for _ in range(5):
            response = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "incorrect password value"})
            self.assertEqual(response.status_code, 401)
        limited = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "another correct horse battery staple"})
        self.assertEqual(limited.status_code, 429)

    def test_successful_login_clears_failed_attempt_counter(self):
        for _ in range(4):
            self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "incorrect password value"})
        self.assertEqual(self.login().status_code, 200)
        for _ in range(4):
            response = self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "incorrect password value"})
            self.assertEqual(response.status_code, 401)

    def test_logout_requires_csrf_and_revokes_replayed_session(self):
        self.assertEqual(self.login().status_code, 200)
        session_token = self.client.cookies.get("job_beeper_session")
        missing_csrf = self.client.post("/api/auth/logout")
        self.assertEqual(missing_csrf.status_code, 403)
        csrf_token = self.client.cookies.get("job_beeper_csrf")
        logged_out = self.client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
        self.assertEqual(logged_out.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertIsNone(auth.get_session_user(self.db_path, session_token))

    def test_application_database_initialization_creates_auth_tables(self):
        uninitialized_db = Path(self.temp_dir.name) / "uninitialized.sqlite3"
        with patch.object(radar, "DB_PATH", uninitialized_db):
            radar.init_db()
        with sqlite3.connect(uninitialized_db) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "sessions", "login_attempts", "jobs"}.issubset(tables))

    def test_public_health_response_contains_only_liveness_metadata(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"status", "version", "uptime_seconds"})

    def test_health_and_login_are_public_but_legacy_api_requires_admin(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "incorrect password value"}).status_code, 401)
        self.assertEqual(self.client.get("/api/config").status_code, 401)

    def test_every_legacy_api_endpoint_rejects_anonymous_and_user_sessions(self):
        endpoints = [
            ("GET", "/api/config"),
            ("PUT", "/api/config", {}),
            ("GET", "/api/latency-summary"),
            ("GET", "/api/source-status"),
            ("GET", "/api/dedupe-candidates"),
            ("GET", "/api/opportunities"),
            ("GET", "/api/jobs"),
            ("GET", "/api/notification-queue"),
            ("GET", "/api/opportunities/1"),
            ("GET", "/api/llm-shadow-status"),
            ("GET", "/api/daily-summary"),
            ("GET", "/api/jobs/1"),
        ]
        for method, path, *body in endpoints:
            kwargs = {"json": body[0]} if body else {}
            anonymous = self.client.request(method, path, **kwargs)
            self.assertEqual(anonymous.status_code, 401, f"anonymous {method} {path}: {anonymous.status_code}")
        self.assertEqual(self.login().status_code, 200)
        for method, path, *body in endpoints:
            kwargs = {"json": body[0]} if body else {}
            response = self.client.request(method, path, **kwargs)
            self.assertEqual(response.status_code, 403, f"user {method} {path}: {response.status_code}")

    def test_admin_can_read_legacy_config_after_session_login(self):
        with patch.object(radar, "get_config", return_value={"target_roles": ["software engineer"]}):
            response = self.client.post("/api/auth/login", json={"email": "admin@example.com", "password": "correct horse battery staple"})
            self.assertEqual(response.status_code, 200)
            config = self.client.get("/api/config")
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json()["config"]["target_roles"], ["software engineer"])

    def test_admin_state_changing_legacy_route_requires_csrf(self):
        with patch.object(radar, "get_config", return_value={"target_roles": []}), patch.object(radar, "save_config", return_value={"target_roles": []}), patch.object(radar, "refresh_job_evaluations"), patch.object(radar, "refresh_notification_decisions"):
            self.assertEqual(self.client.post("/api/auth/login", json={"email": "admin@example.com", "password": "correct horse battery staple"}).status_code, 200)
            denied = self.client.put("/api/config", json={}, headers={})
            self.assertEqual(denied.status_code, 403)
            csrf = self.client.cookies.get("job_beeper_csrf")
            allowed = self.client.put("/api/config", json={}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(allowed.status_code, 200)


class AuthAdminCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "cli-auth.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_bootstraps_only_one_admin_and_can_provision_users(self):
        from v2 import auth_admin
        output = io.StringIO()
        with patch.dict(os.environ, {"JOB_RADAR_DB": str(self.db_path)}), patch("getpass.getpass", side_effect=["correct horse battery staple", "correct horse battery staple"]), redirect_stdout(output):
            self.assertEqual(auth_admin.main(["create-admin", "--email", "admin@example.com"]), 0)
        output = io.StringIO()
        with patch.dict(os.environ, {"JOB_RADAR_DB": str(self.db_path)}), redirect_stderr(output):
            self.assertEqual(auth_admin.main(["create-admin", "--email", "second@example.com"]), 1)
        self.assertIn("already exists", output.getvalue().lower())
        with patch.dict(os.environ, {"JOB_RADAR_DB": str(self.db_path)}), patch("getpass.getpass", side_effect=["another correct horse battery staple", "another correct horse battery staple"]), redirect_stdout(io.StringIO()):
            self.assertEqual(auth_admin.main(["create-user", "--email", "user@example.com"]), 0)
        with sqlite3.connect(self.db_path) as conn:
            roles = dict(conn.execute("SELECT email, role FROM users"))
        self.assertEqual(roles, {"admin@example.com": "admin", "user@example.com": "user"})
