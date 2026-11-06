"""Security-focused tests for Google OIDC state and account linking."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from v2 import auth, google_oauth


class GoogleOAuthStateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "oauth.sqlite3"
        auth.init_auth_schema(self.db_path)
        self.config = google_oauth.GoogleOAuthConfig(
            "client-id", "client-secret",
            "https://jobs.example/api/auth/google/callback",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_authorization_uses_state_nonce_and_pkce(self):
        url = google_oauth.create_authorization_url(self.db_path, self.config)
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["client_id"], ["client-id"])
        self.assertEqual(params["scope"], ["openid email profile"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertTrue(params["state"][0])
        self.assertTrue(params["nonce"][0])
        self.assertTrue(params["code_challenge"][0])

    def test_state_is_one_time_and_returns_nonce_and_verifier(self):
        url = google_oauth.create_authorization_url(self.db_path, self.config)
        state = parse_qs(urlsplit(url).query)["state"][0]
        consumed = google_oauth.consume_authorization_state(self.db_path, state)
        self.assertIsNotNone(consumed)
        nonce, verifier = consumed
        self.assertTrue(nonce)
        self.assertGreaterEqual(len(verifier), 64)
        self.assertIsNone(google_oauth.consume_authorization_state(self.db_path, state))

    def test_nonce_must_match_exactly(self):
        self.assertTrue(google_oauth.validate_nonce({"nonce": "expected"}, "expected"))
        self.assertFalse(google_oauth.validate_nonce({"nonce": "other"}, "expected"))
        self.assertFalse(google_oauth.validate_nonce({}, "expected"))

    def test_redirect_uri_rejects_non_https_and_wrong_callback_path(self):
        with unittest.mock.patch.dict("os.environ", {
            "GOOGLE_OAUTH_CLIENT_ID": "id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "secret",
            "GOOGLE_OAUTH_REDIRECT_URI": "http://jobs.example/callback",
        }):
            with self.assertRaises(ValueError):
                google_oauth.load_config()


class GoogleIdentityLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "identity.sqlite3"
        auth.init_auth_schema(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_new_google_identity_creates_only_a_normal_user(self):
        user = auth.create_or_link_google_user(
            self.db_path, "Beta.User@example.com", "google-sub-1"
        )
        self.assertEqual(user["email"], "Beta.User@example.com")
        self.assertEqual(user["role"], "user")
        self.assertEqual(
            auth.create_or_link_google_user(
                self.db_path, "beta.user@example.com", "google-sub-1"
            )["id"],
            user["id"],
        )

    def test_verified_google_email_links_existing_account(self):
        existing = auth.create_user(
            self.db_path, "existing@example.com", "long-password-for-test"
        )
        linked = auth.create_or_link_google_user(
            self.db_path, "existing@example.com", "google-sub-existing"
        )
        self.assertEqual(linked["id"], existing["id"])
        self.assertEqual(linked["role"], "user")

    def test_google_subject_cannot_be_linked_to_two_emails(self):
        auth.create_or_link_google_user(self.db_path, "first@example.com", "shared-sub")
        with self.assertRaisesRegex(ValueError, "already linked"):
            auth.create_or_link_google_user(
                self.db_path, "second@example.com", "shared-sub"
            )

    def test_disabled_account_cannot_sign_in_with_google(self):
        user = auth.create_user(
            self.db_path, "disabled@example.com", "long-password-for-test"
        )
        with __import__("sqlite3").connect(self.db_path) as conn:
            conn.execute("UPDATE users SET status='disabled' WHERE id=?", (user["id"],))
        with self.assertRaisesRegex(ValueError, "disabled"):
            auth.create_or_link_google_user(
                self.db_path, "disabled@example.com", "google-sub-disabled"
            )


if __name__ == "__main__":
    unittest.main()
