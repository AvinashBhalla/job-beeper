from __future__ import annotations

import base64
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

from v2 import google_alerts_gmail as gmail


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected Gmail API request")
        response = self.responses.pop(0)
        return response if hasattr(response, "status_code") else FakeResponse(response)


def valid_metadata():
    return {
        "id": "msg-1",
        "labelIds": ["Label_123", "INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Google Alerts <googlealerts-noreply@google.com>"},
                {"name": "Subject", "value": "Google Alert - example"},
                {
                    "name": "Authentication-Results",
                    "value": (
                        "mx.google.com; dkim=pass header.i=@google.com; "
                        "dmarc=pass header.from=google.com"
                    ),
                },
            ]
        },
    }


def raw_bytes():
    return b"From: Google Alerts <googlealerts-noreply@google.com>\r\n"


class GmailIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "gmail.sqlite3"
        with sqlite3.connect(self.db) as conn:
            conn.executescript("""
                CREATE TABLE users(id INTEGER PRIMARY KEY);
                CREATE TABLE canonical_opportunities(id INTEGER PRIMARY KEY);
                CREATE TABLE jobs(
                    id INTEGER PRIMARY KEY,
                    canonical_opportunity_id INTEGER,
                    source TEXT,
                    source_owner_user_id INTEGER
                );
                INSERT INTO users(id) VALUES(7);
            """)
        gmail.init_schema(self.db)
        self.key = Fernet.generate_key().decode("ascii")
        self.config = gmail.GmailIntegrationConfig(
            client_id="personal-client.apps.googleusercontent.com",
            client_secret="secret-not-real",
            redirect_uri="https://jobs.example.test" + gmail.CALLBACK_PATH,
            owner_user_id=7,
            owner_email="owner@example.test",
            token_encryption_key=self.key,
            pubsub_topic="projects/example/topics/google-alerts",
            pubsub_subscription="projects/example/subscriptions/google-alerts",
            push_audience="https://jobs.example.test" + gmail.CALLBACK_PATH,
            push_service_account_email="push@example.iam.gserviceaccount.com",
            sync_mode="push",
        )

    def tearDown(self):
        gmail.clear_access_token_cache(self.db)
        self.tmp.cleanup()

    def test_data_use_consent_is_owner_only_versioned_and_single_use(self):
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.record_data_use_consent(
                self.db, 7, self.config, accepted=False,
                disclosure_version=gmail.DATA_USE_DISCLOSURE_VERSION,
            )
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.record_data_use_consent(
                self.db, 7, self.config, accepted=True,
                disclosure_version="old-disclosure",
            )
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.record_data_use_consent(
                self.db, 8, self.config, accepted=True,
                disclosure_version=gmail.DATA_USE_DISCLOSURE_VERSION,
            )

        gmail.record_data_use_consent(
            self.db, 7, self.config, accepted=True,
            disclosure_version=gmail.DATA_USE_DISCLOSURE_VERSION,
        )
        gmail.record_data_use_consent(
            self.db, 7, self.config, accepted=True,
            disclosure_version=gmail.DATA_USE_DISCLOSURE_VERSION,
        )
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM google_alerts_gmail_data_use_consents"
                ).fetchone()[0],
                1,
            )
        self.assertTrue(gmail.consume_data_use_consent(self.db, 7, self.config))
        self.assertFalse(gmail.consume_data_use_consent(self.db, 7, self.config))
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT disclosure_version,accepted_at,expires_at,consumed_at "
                "FROM google_alerts_gmail_data_use_consents"
            ).fetchone()
        self.assertEqual(row[0], gmail.DATA_USE_DISCLOSURE_VERSION)
        self.assertTrue(row[1])
        self.assertGreater(row[2], int(time.time()))
        self.assertTrue(row[3])

        gmail.record_data_use_consent(
            self.db, 7, self.config, accepted=True,
            disclosure_version=gmail.DATA_USE_DISCLOSURE_VERSION,
        )
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE google_alerts_gmail_data_use_consents "
                "SET expires_at=0 WHERE consumed_at IS NULL"
            )
        self.assertFalse(gmail.consume_data_use_consent(self.db, 7, self.config))

        # An expired unused record is retired, retained for audit and must not
        # block a fresh affirmative consent.
        gmail.record_data_use_consent(
            self.db, 7, self.config, accepted=True,
            disclosure_version=gmail.DATA_USE_DISCLOSURE_VERSION,
        )
        with sqlite3.connect(self.db) as conn:
            records = conn.execute(
                "SELECT consumed_at,expired_at FROM google_alerts_gmail_data_use_consents "
                "ORDER BY id"
            ).fetchall()
        self.assertEqual(len(records), 3)
        self.assertIsNotNone(records[1][1])
        self.assertIsNone(records[2][1])
        self.assertTrue(gmail.consume_data_use_consent(self.db, 7, self.config))


    def test_sync_cycle_is_inert_when_live_access_is_not_enabled(self):
        result = gmail.run_sync_cycle(
            self.db,
            self.config,
            lambda owner_id, posting, historical: self.fail("worker must remain inert"),
        )
        self.assertEqual(result, {"enabled": False, "stage": "disabled"})

    def test_config_is_disabled_when_empty_and_rejects_partial_values(self):
        self.assertIsNone(gmail.load_config({}))
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_config({"JOB_RADAR_GMAIL_OAUTH_CLIENT_ID": "only-one"})

    def test_config_rejects_non_https_callback_and_invalid_encryption_key(self):
        env = {
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_ID": "id",
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_SECRET": "secret",
            "JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI": "http://example.test" + gmail.CALLBACK_PATH,
            "JOB_RADAR_GMAIL_OWNER_USER_ID": "7",
            "JOB_RADAR_GMAIL_OWNER_EMAIL": "owner@example.test",
            "JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY": self.key,
            "JOB_RADAR_GMAIL_PUBSUB_TOPIC": "projects/x/topics/y",
            "JOB_RADAR_GMAIL_PUBSUB_SUBSCRIPTION": "projects/x/subscriptions/y",
            "JOB_RADAR_GMAIL_PUSH_AUDIENCE": "https://example.test/push",
            "JOB_RADAR_GMAIL_PUSH_SERVICE_ACCOUNT_EMAIL": "push@example.test",
        }
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_config(env)
        env["JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI"] = "https://example.test" + gmail.CALLBACK_PATH
        env["JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY"] = "not-a-fernet-key"
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_config(env)

    def test_polling_config_accepts_localhost_and_requires_no_pubsub_resources(self):
        env = {
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_ID": "id",
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_SECRET": "secret",
            "JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI": "http://localhost:8080" + gmail.CALLBACK_PATH,
            "JOB_RADAR_GMAIL_OWNER_USER_ID": "7",
            "JOB_RADAR_GMAIL_OWNER_EMAIL": "owner@example.test",
            "JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY": self.key,
            "JOB_RADAR_GMAIL_POLL_INTERVAL_SECONDS": "240",
        }
        config = gmail.load_config(env)
        self.assertEqual(config.sync_mode, "polling")
        self.assertEqual(config.poll_interval_seconds, 240)
        self.assertIsNone(config.pubsub_topic)
        self.assertFalse(config.live_access_enabled)

        env["JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI"] = "https://130.210.27.197" + gmail.CALLBACK_PATH
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_config(env)
        env["JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI"] = "http://localhost:8080" + gmail.CALLBACK_PATH
        env["JOB_RADAR_GMAIL_SYNC_MODE"] = "push"
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_config(env)

    def test_polling_interval_is_bounded(self):
        env = {
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_ID": "id",
            "JOB_RADAR_GMAIL_OAUTH_CLIENT_SECRET": "secret",
            "JOB_RADAR_GMAIL_OAUTH_REDIRECT_URI": "http://localhost:8080" + gmail.CALLBACK_PATH,
            "JOB_RADAR_GMAIL_OWNER_USER_ID": "7",
            "JOB_RADAR_GMAIL_OWNER_EMAIL": "owner@example.test",
            "JOB_RADAR_GMAIL_TOKEN_ENCRYPTION_KEY": self.key,
            "JOB_RADAR_GMAIL_POLL_INTERVAL_SECONDS": "5",
        }
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_config(env)

    def test_authorization_url_uses_only_readonly_scope_and_pkce(self):
        url = gmail.create_authorization_url(self.db, 7, self.config, now_seconds=1000)
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["scope"], [gmail.GMAIL_SCOPE])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(params["access_type"], ["offline"])
        self.assertEqual(params["prompt"], ["consent"])
        self.assertNotIn("gmail.modify", url)
        state = params["state"][0]
        consumed = gmail.consume_authorization_state(self.db, state, now_seconds=1001)
        self.assertIsNotNone(consumed)
        self.assertEqual(consumed[0], 7)
        self.assertTrue(consumed[1])
        self.assertIsNone(gmail.consume_authorization_state(self.db, state, now_seconds=1001))

    def test_authorization_state_is_owner_only_and_expires(self):
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.create_authorization_url(self.db, 8, self.config, now_seconds=1000)
        url = gmail.create_authorization_url(self.db, 7, self.config, now_seconds=1000)
        state = parse_qs(urlsplit(url).query)["state"][0]
        self.assertIsNone(
            gmail.consume_authorization_state(
                self.db, state, now_seconds=1000 + gmail.STATE_TTL_SECONDS + 1
            )
        )

    def test_refresh_token_is_encrypted_and_bound_to_owner(self):
        gmail.save_credentials(
            self.db, 7, "Owner@example.test", "refresh-secret",
            gmail.GMAIL_SCOPE, self.config,
        )
        with sqlite3.connect(self.db) as conn:
            cipher = conn.execute(
                "SELECT encrypted_refresh_token FROM google_alerts_gmail_credentials"
            ).fetchone()[0]
        self.assertNotIn(b"refresh-secret", bytes(cipher))
        self.assertEqual(gmail.load_refresh_token(self.db, 7, self.config), "refresh-secret")
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.load_refresh_token(self.db, 8, self.config)
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.save_credentials(
                self.db, 7, "other@example.test", "refresh-secret",
                gmail.GMAIL_SCOPE, self.config,
            )

    def test_access_token_is_cached_until_expiry_safety_window_then_refreshed(self):
        gmail.save_credentials(
            self.db, 7, "owner@example.test", "refresh-secret",
            gmail.GMAIL_SCOPE, self.config,
        )
        first = Mock(status_code=200)
        first.json.return_value = {"access_token": "access-one", "expires_in": 3600}
        second = Mock(status_code=200)
        second.json.return_value = {"access_token": "access-two", "expires_in": 3600}
        session = Mock()
        session.post.side_effect = [first, second]

        self.assertEqual(
            gmail.refresh_access_token(self.db, self.config, session=session, now_seconds=100),
            "access-one",
        )
        self.assertEqual(
            gmail.refresh_access_token(self.db, self.config, session=session, now_seconds=101),
            "access-one",
        )
        self.assertEqual(session.post.call_count, 1)

        # 100 + (3600 - 60s safety margin) is the end of the cache window.
        self.assertEqual(
            gmail.refresh_access_token(self.db, self.config, session=session, now_seconds=3640),
            "access-two",
        )
        self.assertEqual(session.post.call_count, 2)

    def test_gmail_api_retries_once_after_401_with_forced_access_token_refresh(self):
        session = FakeSession([
            FakeResponse({"error": "expired"}, status_code=401),
            FakeResponse({"emailAddress": "owner@example.test", "historyId": "123"}),
        ])
        refresh = Mock(return_value="fresh-access-token")
        client = gmail.GmailApiClient(
            "stale-access-token", session=session, refresh_access_token=refresh
        )

        self.assertEqual(client.get_profile()["email_address"], "owner@example.test")
        self.assertEqual(refresh.call_count, 1)
        self.assertEqual(session.calls[0][2]["headers"]["Authorization"], "Bearer stale-access-token")
        self.assertEqual(session.calls[1][2]["headers"]["Authorization"], "Bearer fresh-access-token")

    def test_gmail_api_does_not_retry_repeated_401_responses(self):
        session = FakeSession([
            FakeResponse({"error": "expired"}, status_code=401),
            FakeResponse({"error": "still unauthorized"}, status_code=401),
        ])
        refresh = Mock(return_value="fresh-access-token")
        client = gmail.GmailApiClient(
            "stale-access-token", session=session, refresh_access_token=refresh
        )
        with self.assertRaises(gmail.GoogleAlertsGmailError) as raised:
            client.get_profile()
        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(refresh.call_count, 1)
        self.assertEqual(len(session.calls), 2)

    def test_access_token_cache_is_cleared_when_owner_replaces_credentials(self):
        gmail.save_credentials(
            self.db, 7, "owner@example.test", "refresh-one",
            gmail.GMAIL_SCOPE, self.config,
        )
        session = Mock()
        response = Mock(status_code=200)
        response.json.return_value = {"access_token": "access-one", "expires_in": 3600}
        session.post.return_value = response
        self.assertEqual(
            gmail.refresh_access_token(self.db, self.config, session=session, now_seconds=100),
            "access-one",
        )
        self.assertEqual(session.post.call_count, 1)

        gmail.save_credentials(
            self.db, 7, "owner@example.test", "refresh-two",
            gmail.GMAIL_SCOPE, self.config,
        )
        session.post.return_value = FakeResponse({"access_token": "access-two", "expires_in": 3600})
        self.assertEqual(
            gmail.refresh_access_token(self.db, self.config, session=session, now_seconds=101),
            "access-two",
        )
        self.assertEqual(session.post.call_count, 2)

    def test_token_exchange_requires_exact_readonly_scope_and_refresh_token(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
            "scope": gmail.GMAIL_SCOPE,
        }
        session = Mock()
        session.post.return_value = response
        result = gmail.exchange_authorization_code(
            "auth-code", "verifier", self.config, session=session
        )
        self.assertEqual(result["access_token"], "access")
        self.assertEqual(result["scopes"], gmail.GMAIL_SCOPE)
        response.json.return_value["scope"] += " https://www.googleapis.com/auth/gmail.modify"
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.exchange_authorization_code(
                "auth-code", "verifier", self.config, session=session
            )

    def test_label_lookup_is_read_only_and_requires_exact_dedicated_label(self):
        session = FakeSession([{
            "labels": [
                {"id": "Label_123", "name": gmail.GOOGLE_ALERTS_LABEL_NAME, "type": "user"},
                {"id": "Label_456", "name": "Other", "type": "user"},
            ]
        }])
        client = gmail.GmailApiClient("access", session=session)
        self.assertEqual(client.resolve_alert_label_id(), "Label_123")
        self.assertEqual(session.calls[0][0], "GET")
        self.assertTrue(session.calls[0][1].endswith("/users/me/labels"))

    def test_watch_list_and_history_calls_are_forced_to_dedicated_label(self):
        session = FakeSession([
            {"historyId": "12345", "expiration": "1999999999999"},
            {"messages": [{"id": "msg-1"}], "nextPageToken": "next"},
            {"history": [], "historyId": "12346"},
        ])
        client = gmail.GmailApiClient("access", session=session)
        watched = client.watch("Label_123", self.config.pubsub_topic)
        listed = client.list_message_page("Label_123")
        history = client.list_history_page("Label_123", "12345")
        self.assertEqual(watched["history_id"], "12345")
        watch_body = session.calls[0][2]["json"]
        self.assertEqual(watch_body["labelIds"], ["Label_123"])
        self.assertEqual(watch_body["labelFilterBehavior"], "INCLUDE")
        list_params = session.calls[1][2]["params"]
        self.assertIn(("labelIds", "Label_123"), list_params)
        self.assertIn(("includeSpamTrash", "false"), list_params)
        history_params = session.calls[2][2]["params"]
        self.assertIn(("labelId", "Label_123"), history_params)
        self.assertIn(("historyTypes", "messageAdded"), history_params)
        self.assertIn(("historyTypes", "labelAdded"), history_params)
        self.assertEqual(listed["messages"][0]["id"], "msg-1")
        self.assertEqual(history["historyId"], "12346")

    def test_message_body_is_not_requested_without_label_and_authenticated_metadata(self):
        metadata = valid_metadata()
        metadata["labelIds"] = ["INBOX"]
        session = FakeSession([metadata])
        client = gmail.GmailApiClient("access", session=session)
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            client.get_verified_raw_message("msg-1", "Label_123")
        self.assertEqual(len(session.calls), 1)
        self.assertIn(("format", "metadata"), session.calls[0][2]["params"])

    def test_message_body_is_not_requested_when_metadata_authentication_fails(self):
        metadata = valid_metadata()
        metadata["payload"]["headers"][2]["value"] = (
            "mx.google.com; dkim=pass header.i=@google.com.attacker; "
            "dmarc=pass header.from=google.com"
        )
        session = FakeSession([metadata])
        client = gmail.GmailApiClient("access", session=session)
        self.assertIsNone(client.get_verified_raw_message("msg-1", "Label_123"))
        self.assertEqual(len(session.calls), 1)

    def test_raw_message_is_requested_only_after_metadata_passes(self):
        raw = raw_bytes()
        encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        session = FakeSession([valid_metadata(), {"raw": encoded}])
        client = gmail.GmailApiClient("access", session=session)
        self.assertEqual(
            client.get_verified_raw_message("msg-1", "Label_123"),
            raw,
        )
        self.assertEqual(len(session.calls), 2)
        self.assertIn(("format", "metadata"), session.calls[0][2]["params"])
        self.assertEqual(session.calls[1][2]["params"], [("format", "raw")])

    def test_polling_sync_uses_profile_history_cursor_without_watch_or_pubsub(self):
        from dataclasses import replace

        class PollingClient:
            def __init__(self):
                self.watch_calls = 0

            def get_profile(self):
                return {"email_address": "owner@example.test", "history_id": "900"}

            def resolve_alert_label_id(self):
                return "Label_123"

            def list_message_page(self, label_id, *, page_token=None, max_results=500):
                self.assert_label(label_id)
                return {"messages": []}

            def list_history_page(self, label_id, start_history_id, *, page_token=None):
                self.assert_label(label_id)
                if start_history_id != "900":
                    raise AssertionError("polling baseline history cursor was not preserved")
                return {"history": [], "historyId": "901"}

            def watch(self, *args, **kwargs):
                self.watch_calls += 1
                raise AssertionError("polling mode must not call users.watch")

            @staticmethod
            def assert_label(label_id):
                if label_id != "Label_123":
                    raise AssertionError("label scope lost")

        client = PollingClient()
        config = replace(self.config, sync_mode="polling", live_access_enabled=True, pubsub_topic=None)
        with patch.object(gmail, "refresh_access_token", return_value="access-token"), patch.object(
            gmail, "GmailApiClient", return_value=client
        ):
            result = gmail.run_sync_cycle(
                self.db, config,
                lambda owner_id, posting, historical: self.fail("no message should be processed"),
            )
        self.assertTrue(result["enabled"])
        self.assertEqual(result["sync_mode"], "polling")
        self.assertEqual(result["stage"], "complete")
        self.assertEqual(client.watch_calls, 0)
        with sqlite3.connect(self.db) as conn:
            state = conn.execute(
                "SELECT history_id,initial_history_id,watch_expiration_ms,backfill_state "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
        self.assertEqual(state, ("901", "900", None, "complete"))

    def test_polling_baseline_and_expired_cursor_recovery_do_not_require_watch_expiry(self):
        gmail.save_sync_baseline(self.db, 7, "Label_123", "700")
        gmail.restart_full_backfill(self.db, 7, "Label_123", {"history_id": "800"})
        with sqlite3.connect(self.db) as conn:
            state = conn.execute(
                "SELECT history_id,initial_history_id,watch_expiration_ms,backfill_state "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
        self.assertEqual(state, ("800", "800", None, "scanning"))

    def test_watch_baseline_and_full_backfill_history_catchup_stage_ids(self):
        gmail.save_watch_baseline(
            self.db, 7, "Label_123",
            {"history_id": "500", "expiration_ms": 1999999999999},
        )

        class BackfillClient:
            def __init__(self):
                self.list_calls = 0
                self.history_calls = []

            def list_message_page(self, label_id, *, page_token=None, max_results=500):
                self.assert_label(label_id)
                self.list_calls += 1
                if page_token is None:
                    return {"messages": [{"id": "old-1"}], "nextPageToken": "p2"}
                return {"messages": [{"id": "old-2"}]}

            def list_history_page(self, label_id, start_history_id, *, page_token=None):
                self.assert_label(label_id)
                self.history_calls.append((label_id, start_history_id, page_token))
                if page_token is None:
                    return {
                        "history": [{"messagesAdded": [{"message": {"id": "new-1"}}]}],
                        "historyId": "503",
                        "nextPageToken": "history-p2",
                    }
                return {
                    "history": [{"labelsAdded": [{"message": {"id": "new-2"}}]}],
                    "historyId": "505",
                }

            @staticmethod
            def assert_label(label_id):
                if label_id != "Label_123":
                    raise AssertionError("label scope lost")

        client = BackfillClient()
        first = gmail.stage_initial_backfill_page(self.db, client)
        second = gmail.stage_initial_backfill_page(self.db, client)
        self.assertFalse(first["complete"])
        self.assertTrue(second["complete"])
        catchup_first = gmail.stage_history_catchup(self.db, client)
        self.assertFalse(catchup_first["complete"])
        with sqlite3.connect(self.db) as conn:
            checkpoint = conn.execute(
                "SELECT history_id,history_page_token,backfill_state "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
        self.assertEqual(checkpoint, ("500", "history-p2", "history_catchup"))
        catchup = gmail.stage_history_catchup(self.db, client)
        self.assertTrue(catchup["complete"])
        self.assertEqual(client.history_calls, [
            ("Label_123", "500", None),
            ("Label_123", "500", "history-p2"),
        ])
        with sqlite3.connect(self.db) as conn:
            rows = conn.execute(
                "SELECT gmail_message_id,history_backfill FROM google_alerts_gmail_messages ORDER BY gmail_message_id"
            ).fetchall()
            cursor = conn.execute(
                "SELECT history_id,history_page_token,backfill_state "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
        self.assertEqual(rows, [
            ("new-1", 1), ("new-2", 1), ("old-1", 1), ("old-2", 1)
        ])
        self.assertEqual(cursor, ("505", None, "draining"))

    def test_incremental_history_stages_each_page_and_preserves_arrival_classification(self):
        gmail.save_watch_baseline(
            self.db, 7, "Label_123",
            {"history_id": "700", "expiration_ms": 1999999999999},
        )
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE google_alerts_gmail_sync_state SET backfill_state='complete'"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_messages(
                     message_id_hash,gmail_message_id,history_backfill,status,
                     attempt_count,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                ("hash-live", "live-1", 0, "queued", 0, "2026-11-21", "2026-11-21"),
            )

        class IncrementalClient:
            def __init__(self):
                self.calls = []

            def list_history_page(self, label_id, start_history_id, *, page_token=None):
                self.calls.append((label_id, start_history_id, page_token))
                if page_token is None:
                    return {
                        "history": [{"messagesAdded": [{"message": {"id": "live-1"}}]}],
                        "historyId": "701",
                        "nextPageToken": "next-live",
                    }
                return {
                    "history": [{"messagesAdded": [{"message": {"id": "live-2"}}]}],
                    "historyId": "702",
                }

        client = IncrementalClient()
        first = gmail.stage_incremental_history(self.db, client)
        self.assertFalse(first["complete"])
        with sqlite3.connect(self.db) as conn:
            checkpoint = conn.execute(
                "SELECT history_id,history_page_token,history_start_id "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
        self.assertEqual(checkpoint, ("700", "next-live", "700"))

        second = gmail.stage_incremental_history(self.db, client)
        self.assertTrue(second["complete"])
        self.assertEqual(second["history_id"], "702")
        self.assertEqual(client.calls, [
            ("Label_123", "700", None),
            ("Label_123", "700", "next-live"),
        ])
        with sqlite3.connect(self.db) as conn:
            cursor = conn.execute(
                "SELECT history_id,history_page_token,history_start_id "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
            history_flags = dict(conn.execute(
                "SELECT gmail_message_id,history_backfill "
                "FROM google_alerts_gmail_messages"
            ).fetchall())
        self.assertEqual(cursor, ("702", None, None))
        self.assertEqual(history_flags["live-1"], 0)
        self.assertEqual(history_flags["live-2"], 0)

    def test_restart_full_backfill_updates_existing_sync_state(self):
        gmail.save_watch_baseline(
            self.db, 7, "Label_123",
            {"history_id": "700", "expiration_ms": 1999999999999},
        )
        gmail.restart_full_backfill(
            self.db, 7, "Label_123",
            {"history_id": "800", "expiration_ms": 1999999999999},
        )
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT history_id,initial_history_id,backfill_state "
                "FROM google_alerts_gmail_sync_state"
            ).fetchone()
        self.assertEqual(row, ("800", "800", "scanning"))

    def test_push_payload_is_decoded_and_event_storage_is_idempotent(self):
        notification = json.dumps(
            {"emailAddress": "owner@example.test", "historyId": "123456"}
        ).encode("utf-8")
        payload = {
            "subscription": self.config.pubsub_subscription,
            "message": {
                "messageId": "pubsub-1",
                "data": base64.urlsafe_b64encode(notification).decode("ascii").rstrip("="),
            },
        }
        decoded = gmail.decode_pubsub_push(json.dumps(payload).encode("utf-8"))
        self.assertEqual(decoded["history_id"], "123456")
        args = {
            "subscription": decoded["subscription"],
            "expected_subscription": self.config.pubsub_subscription,
            "pubsub_message_id": decoded["pubsub_message_id"],
            "history_id": decoded["history_id"],
            "email_address": decoded["email_address"],
        }
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.store_pubsub_push(self.db, **args)
        gmail.save_credentials(
            self.db, 7, "owner@example.test", "refresh",
            gmail.GMAIL_SCOPE, self.config,
        )
        self.assertTrue(gmail.store_pubsub_push(self.db, **args))
        self.assertFalse(gmail.store_pubsub_push(self.db, **args))
        args["subscription"] = "wrong"
        with self.assertRaises(gmail.GoogleAlertsGmailError):
            gmail.store_pubsub_push(self.db, **args)

    def test_disconnect_removes_gmail_only_queued_alerts_but_keeps_public_jobs(self):
        from v2 import user_notifications

        user_notifications.init_schema(self.db)
        with user_notifications._connect(self.db) as conn:
            conn.executemany(
                "INSERT INTO canonical_opportunities(id) VALUES(?)",
                [(201,), (202,)],
            )
            conn.executemany(
                """INSERT INTO jobs(
                     id,canonical_opportunity_id,source,source_owner_user_id
                   ) VALUES(?,?,?,?)""",
                [
                    (11, 201, "google_alerts_gmail", 7),
                    (12, 202, "workday", None),
                ],
            )
            conn.executemany(
                """INSERT INTO google_alerts_gmail_opportunities(
                     user_id,canonical_opportunity_id,candidate_job_id,history_backfill,
                     first_observed_at,last_observed_at
                   ) VALUES(?,?,?,?,?,?)""",
                [
                    (7, 201, 11, 0, "2026-11-22T00:00:00+00:00", "2026-11-22T00:00:00+00:00"),
                    (7, 202, 12, 1, "2026-11-22T00:00:00+00:00", "2026-11-22T00:00:00+00:00"),
                ],
            )
            conn.executemany(
                """INSERT INTO user_notification_ledger(
                     user_id,canonical_opportunity_id,candidate_job_id,status,
                     backlog_override,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                [
                    (7, 201, 11, "queued", 0, "2026-11-22T00:00:00+00:00", "2026-11-22T00:00:00+00:00"),
                    (7, 202, 12, "queued", 1, "2026-11-22T00:00:00+00:00", "2026-11-22T00:00:00+00:00"),
                ],
            )

        gmail.save_credentials(
            self.db, 7, "owner@example.test", "refresh",
            gmail.GMAIL_SCOPE, self.config,
        )
        session = Mock()
        session.post.return_value = Mock(status_code=200)
        with patch.object(gmail, "refresh_access_token", return_value="access-token"):
            with patch.object(gmail, "GmailApiClient") as api_client:
                gmail.disconnect(self.db, self.config, session=session)
        api_client.return_value.stop_watch.assert_called_once_with()

        with user_notifications._connect(self.db) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM jobs WHERE id=11").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM jobs WHERE id=12").fetchone()[0],
                1,
            )
            # The FK cascade removes the future Gmail-only queue row together
            # with its private candidate job.
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM user_notification_ledger WHERE candidate_job_id=11"
                ).fetchone()[0],
                0,
            )
            # Historical Gmail delivery for an independently public ATS job is
            # explicitly cancelled, while the public job itself is preserved.
            public_delivery = conn.execute(
                """SELECT status,backlog_override FROM user_notification_ledger
                   WHERE candidate_job_id=12"""
            ).fetchone()
        self.assertEqual(tuple(public_delivery), ("cancelled", 0))


    def test_disconnect_erases_gmail_credentials_and_sync_state(self):
        gmail.save_credentials(
            self.db, 7, "owner@example.test", "refresh",
            gmail.GMAIL_SCOPE, self.config,
        )
        gmail.save_watch_baseline(
            self.db, 7, "Label_123",
            {"history_id": "500", "expiration_ms": 123},
        )
        session = Mock()
        session.post.return_value = Mock(status_code=200)
        with patch.object(gmail, "refresh_access_token", return_value="access-token") as refresh:
            with patch.object(gmail, "GmailApiClient") as api_client:
                gmail.disconnect(self.db, self.config, session=session)
        refresh.assert_called_once_with(self.db, self.config, session=session)
        api_client.assert_called_once_with("access-token")
        api_client.return_value.stop_watch.assert_called_once_with()
        session.post.assert_called_once()
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM google_alerts_gmail_credentials").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM google_alerts_gmail_sync_state").fetchone()[0],
                0,
            )


if __name__ == "__main__":
    unittest.main()
