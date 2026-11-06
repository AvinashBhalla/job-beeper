import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from v2 import radar

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
        self.assertTrue({"users", "sessions", "login_attempts", "login_account_attempts"}.issubset(tables))

    def test_first_admin_bootstrap_is_atomic_under_concurrent_calls(self):
        def attempt_create():
            try:
                return auth.create_first_admin(self.db_path, "admin@example.com", "correct horse battery staple")
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt_create(), range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0], 1)

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

    def test_password_validation_accepts_five_characters_and_rejects_four(self):
        user = auth.create_user(self.db_path, "five@example.com", "abcde")
        self.assertEqual(auth.verify_user(self.db_path, "five@example.com", "abcde")["id"], user["id"])
        with self.assertRaises(ValueError):
            auth.create_user(self.db_path, "four@example.com", "abcd")

    def test_password_and_role_validation_reject_weak_or_unknown_values(self):
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

    def test_malformed_email_attempts_are_rate_limited_without_storing_the_email(self):
        identity = ("not-an-email", "192.0.2.25")
        for _ in range(5):
            self.assertFalse(auth.begin_login_attempt(self.db_path, *identity))
        self.assertTrue(auth.begin_login_attempt(self.db_path, *identity))
        with sqlite3.connect(self.db_path) as conn:
            stored_key = conn.execute("SELECT email_key_hash FROM login_attempts").fetchone()[0]
        self.assertNotEqual(stored_key, identity[0])
        self.assertEqual(len(stored_key), 64)

    def test_account_level_login_limit_cannot_be_bypassed_by_rotating_ips(self):
        email = "target@example.com"
        for index in range(20):
            self.assertFalse(auth.begin_login_attempt(self.db_path, email, f"198.51.100.{index + 1}"))
        self.assertTrue(auth.begin_login_attempt(self.db_path, email, "203.0.113.50"))

    def test_concurrent_account_level_reservations_cannot_exceed_the_limit(self):
        email = "parallel-target@example.com"
        with ThreadPoolExecutor(max_workers=12) as pool:
            allowed = list(pool.map(lambda index: auth.begin_login_attempt(self.db_path, email, f"203.0.113.{index + 1}"), range(30)))
        self.assertEqual(allowed.count(False), 20)
        self.assertEqual(allowed.count(True), 10)

    def test_concurrent_login_attempt_reservations_cannot_exceed_the_limit(self):
        identity = ("parallel@example.com", "192.0.2.26")
        with ThreadPoolExecutor(max_workers=8) as pool:
            allowed = list(pool.map(lambda _: auth.begin_login_attempt(self.db_path, *identity), range(12)))
        self.assertEqual(allowed.count(False), 5)
        self.assertEqual(allowed.count(True), 7)

    def test_successful_login_clears_account_throttle_across_all_ips(self):
        email = "reset-account@example.com"
        for index in range(19):
            self.assertFalse(auth.begin_login_attempt(self.db_path, email, f"192.0.2.{index + 1}"))
        self.assertFalse(auth.begin_login_attempt(self.db_path, email, "203.0.113.20"))
        auth.record_login_attempt(self.db_path, email, "203.0.113.20", success=True)
        self.assertFalse(auth.begin_login_attempt(self.db_path, email, "192.0.2.1"))

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


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "api-auth.sqlite3"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.db_patch.start()
        auth.init_auth_schema(self.db_path)
        from v2 import user_preferences
        user_preferences.init_preferences_schema(self.db_path)
        self.admin = auth.create_user(self.db_path, "admin@example.com", "correct horse battery staple", role="admin")
        self.user = auth.create_user(self.db_path, "user@example.com", "another correct horse battery staple")
        self.client = TestClient(radar.app, base_url="https://testserver")

    def tearDown(self):
        self.client.close()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def login(self, email="user@example.com", password="another correct horse battery staple"):
        return self.client.post("/api/auth/login", json={"email": email, "password": password})

    def test_login_uses_configured_public_origin_behind_tls_termination(self):
        with patch.dict(os.environ, {"JOB_BEEPER_PUBLIC_ORIGIN": "https://jobs.example"}):
            response = self.client.post(
                "/api/auth/login",
                json={"email": "user@example.com", "password": "another correct horse battery staple"},
                headers={"Origin": "https://jobs.example"},
            )
        self.assertEqual(response.status_code, 200)

    def test_login_rejects_cross_origin_browser_submission(self):
        cross_origin = self.client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "another correct horse battery staple"},
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(cross_origin.status_code, 403)
        same_origin = self.client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "another correct horse battery staple"},
            headers={"Origin": "https://testserver"},
        )
        self.assertEqual(same_origin.status_code, 200)

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

    def test_authenticated_api_responses_are_not_cacheable(self):
        login = self.login()
        self.assertEqual(login.status_code, 200)
        current = self.client.get("/api/auth/me")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(login.headers.get("cache-control"), "no-store")
        self.assertEqual(current.headers.get("cache-control"), "no-store")

    def test_login_trims_email_whitespace_and_normalizes_case(self):
        response = self.login(email="  USER@EXAMPLE.COM  ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "user@example.com")

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

    def test_malformed_email_login_attempts_are_rate_limited(self):
        for _ in range(5):
            response = self.client.post("/api/auth/login", json={"email": "not-an-email", "password": "incorrect password value"})
            self.assertEqual(response.status_code, 401)
        limited = self.client.post("/api/auth/login", json={"email": "not-an-email", "password": "incorrect password value"})
        self.assertEqual(limited.status_code, 429)

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
        runtime_config = Path(self.temp_dir.name) / "uninitialized-config.json"
        with patch.object(radar, "DB_PATH", uninitialized_db), patch.object(
            radar, "RUNTIME_CONFIG_PATH", runtime_config
        ):
            radar.init_db()
        with sqlite3.connect(uninitialized_db) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({
            "users", "sessions", "login_attempts", "login_account_attempts",
            "user_preferences", "user_job_evaluations", "jobs",
        }.issubset(tables))

    def test_public_health_response_contains_only_liveness_metadata(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"status", "version", "uptime_seconds"})

    def test_health_and_login_are_public_but_legacy_api_requires_admin(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "incorrect password value"}).status_code, 401)
        self.assertEqual(self.client.get("/api/config").status_code, 401)

    def test_every_registered_api_route_has_an_explicit_auth_dependency(self):
        routes = [route for route in radar.app.routes if isinstance(route, APIRoute) and route.path.startswith("/api/")]
        self.assertTrue(routes)
        for route in routes:
            dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
            if route.path == "/api/auth/login":
                self.assertNotIn(radar.require_admin, dependency_calls, route.path)
            elif route.path in {"/api/auth/me", "/api/auth/logout"}:
                self.assertIn(radar.get_current_user, dependency_calls, route.path)
            elif route.path in {
                "/api/preferences", "/api/jobs", "/api/daily-summary", "/api/jobs/{job_id}"
            }:
                self.assertIn(radar.require_authenticated, dependency_calls, route.path)
            else:
                self.assertIn(radar.require_admin, dependency_calls, route.path)

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

    def test_user_preferences_require_authentication_and_role_location_onboarding(self):
        self.assertEqual(self.client.get("/api/preferences").status_code, 401)
        self.assertEqual(self.login().status_code, 200)
        initial = self.client.get("/api/preferences")
        self.assertEqual(initial.status_code, 200)
        self.assertFalse(initial.json()["preferences"]["onboarding_complete"])
        csrf = self.client.cookies.get("job_beeper_csrf")
        missing_role = self.client.put(
            "/api/preferences", json={"locations": ["Bengaluru"]},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(missing_role.status_code, 422)
        missing_location = self.client.put(
            "/api/preferences", json={"target_roles": ["Python Developer"]},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(missing_location.status_code, 422)
        saved = self.client.put(
            "/api/preferences",
            json={"target_roles": ["Python Developer"], "locations": ["Bengaluru"]},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()["preferences"]["onboarding_complete"])

    def test_admin_must_update_candidate_preferences_through_global_config(self):
        with patch.object(radar, "get_config", return_value={
            "target_roles": ["Software Engineer"], "locations": ["Gurugram"]
        }):
            self.assertEqual(
                self.login("admin@example.com", "correct horse battery staple").status_code,
                200,
            )
            csrf = self.client.cookies.get("job_beeper_csrf")
            response = self.client.put(
                "/api/preferences",
                json={"target_roles": ["QA Engineer"], "locations": ["Pune"]},
                headers={"X-CSRF-Token": csrf},
            )
        self.assertEqual(response.status_code, 403)
        self.assertIn("/api/config", response.json()["detail"])

    def test_user_preferences_writes_require_csrf(self):
        self.assertEqual(self.login().status_code, 200)
        denied = self.client.put(
            "/api/preferences",
            json={"target_roles": ["Python Developer"], "locations": ["Pune"]},
        )
        self.assertEqual(denied.status_code, 403)

    def test_admin_preferences_migrate_from_global_config(self):
        with patch.object(radar, "get_config", return_value={
            "target_roles": ["Software Engineer"],
            "locations": ["Gurugram"],
            "skills": ["Python"],
            "match_threshold": 68,
            "source_enabled": {"naukri": True},
        }):
            self.assertEqual(self.login("admin@example.com", "correct horse battery staple").status_code, 200)
            response = self.client.get("/api/preferences")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["preferences"]["target_roles"], ["Software Engineer"])
        self.assertEqual(response.json()["preferences"]["match_threshold"], 68)
        self.assertNotIn("source_enabled", response.json()["preferences"])

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
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.config_path.write_text(
            json.dumps({
                "target_roles": ["Software Engineer"],
                "locations": ["Gurugram"],
                "skills": ["Python"],
                "source_enabled": {"naukri": True},
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_bootstraps_only_one_admin_and_can_provision_users(self):
        from v2 import auth_admin
        output = io.StringIO()
        with patch.dict(os.environ, {"JOB_RADAR_DB": str(self.db_path), "JOB_RADAR_CONFIG_PATH": str(self.config_path)}), patch("getpass.getpass", side_effect=["correct horse battery staple", "correct horse battery staple"]), redirect_stdout(output):
            self.assertEqual(auth_admin.main(["create-admin", "--email", "admin@example.com"]), 0)
        output = io.StringIO()
        with patch.dict(os.environ, {"JOB_RADAR_DB": str(self.db_path), "JOB_RADAR_CONFIG_PATH": str(self.config_path)}), redirect_stderr(output):
            self.assertEqual(auth_admin.main(["create-admin", "--email", "second@example.com"]), 1)
        self.assertIn("already exists", output.getvalue().lower())
        with patch.dict(os.environ, {"JOB_RADAR_DB": str(self.db_path), "JOB_RADAR_CONFIG_PATH": str(self.config_path)}), patch("getpass.getpass", side_effect=["another correct horse battery staple", "another correct horse battery staple"]), redirect_stdout(io.StringIO()):
            self.assertEqual(auth_admin.main(["create-user", "--email", "user@example.com"]), 0)
        with sqlite3.connect(self.db_path) as conn:
            roles = dict(conn.execute("SELECT email, role FROM users"))
            admin_preferences_row = conn.execute(
                "SELECT preferences_json FROM user_preferences WHERE user_id=(SELECT id FROM users WHERE email='admin@example.com')"
            ).fetchone()
            user_preferences_row = conn.execute(
                "SELECT preferences_json FROM user_preferences WHERE user_id=(SELECT id FROM users WHERE email='user@example.com')"
            ).fetchone()
        self.assertEqual(roles, {"admin@example.com": "admin", "user@example.com": "user"})
        self.assertIsNotNone(admin_preferences_row)
        self.assertEqual(json.loads(admin_preferences_row[0])["target_roles"], ["Software Engineer"])
        self.assertIsNotNone(user_preferences_row)
        self.assertEqual(user_preferences_row[0], "{}")


if __name__ == "__main__":
    unittest.main()
