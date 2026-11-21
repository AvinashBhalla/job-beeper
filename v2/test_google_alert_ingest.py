"""Tests for authenticated, idempotent Google Alert event intake."""
from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import time
import unittest
from pathlib import Path

from v2 import google_alert_ingest


class GoogleAlertIngestTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "alerts.sqlite3"
        google_alert_ingest.init_schema(self.db_path)
        self.secret = "test-secret-that-is-long-enough-for-hmac-256"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _event(self, event_id="message-id-0001", urls=None):
        return {
            "schema_version": 1,
            "event_id": event_id,
            "message_id": f"<{event_id}@mail.example>",
            "envelope_from": "forwarder@gmail.com",
            "envelope_to": "google-alerts@alerts-in.example.com",
            "header_from": "Google Alerts <googlealerts-noreply@google.com>",
            "subject": "Google Alert - Example role",
            "received_at": "2026-11-21T10:00:00Z",
            "links": [
                {"url": url, "title": "Example Software Engineer", "snippet": "Remote role"}
                for url in (urls or ["https://careers.example.com/jobs/123"])
            ],
        }

    def _body(self, payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _signature(self, body, timestamp=None):
        stamp = str(int(time.time()) if timestamp is None else int(timestamp))
        signed = stamp.encode("ascii") + b"." + body
        signature = hmac.new(self.secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        return stamp, signature

    def test_signature_accepts_exact_body_and_rejects_tampering(self):
        body = self._body(self._event())
        stamp, signature = self._signature(body)
        self.assertTrue(google_alert_ingest.verify_request_signature(
            body, stamp, signature, self.secret
        ))
        self.assertFalse(google_alert_ingest.verify_request_signature(
            body + b" ", stamp, signature, self.secret
        ))

    def test_signature_rejects_stale_timestamp_and_short_secret(self):
        body = self._body(self._event())
        stamp, signature = self._signature(body, timestamp=100)
        self.assertFalse(google_alert_ingest.verify_request_signature(
            body, stamp, signature, self.secret, now=1000, max_skew_seconds=300
        ))
        self.assertFalse(google_alert_ingest.verify_request_signature(
            body, stamp, signature, "short"
        ))

    def test_ingest_persists_message_url_and_observation(self):
        payload = self._event()
        body = self._body(payload)
        result = google_alert_ingest.ingest_event(self.db_path, body, payload)
        self.assertEqual(result, {"accepted": True, "duplicate": False, "result_count": 1})

        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM google_alert_messages").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM google_alert_urls").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM google_alert_url_observations").fetchone()[0], 1)

    def test_duplicate_delivery_is_idempotent(self):
        payload = self._event()
        body = self._body(payload)
        first = google_alert_ingest.ingest_event(self.db_path, body, payload)
        second = google_alert_ingest.ingest_event(self.db_path, body, payload)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["result_count"], second["result_count"])

    def test_duplicate_delivery_is_independent_of_json_key_order(self):
        payload = self._event()
        sorted_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        insertion_order_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        first = google_alert_ingest.ingest_event(self.db_path, sorted_body, payload)
        second = google_alert_ingest.ingest_event(self.db_path, insertion_order_body, payload)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])

    def test_repeated_url_across_messages_has_one_fetch_candidate_two_observations(self):
        first_payload = self._event("message-id-0001")
        second_payload = self._event("message-id-0002")
        first_body = self._body(first_payload)
        second_body = self._body(second_payload)
        google_alert_ingest.ingest_event(self.db_path, first_body, first_payload)
        google_alert_ingest.ingest_event(self.db_path, second_body, second_payload)

        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM google_alert_urls").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM google_alert_url_observations").fetchone()[0], 2)

    def test_reusing_event_id_with_different_payload_is_rejected(self):
        original = self._event()
        google_alert_ingest.ingest_event(self.db_path, self._body(original), original)
        altered = self._event()
        altered["subject"] = "Different message using same ID"
        with self.assertRaisesRegex(ValueError, "different payload"):
            google_alert_ingest.ingest_event(self.db_path, self._body(altered), altered)

    def test_local_or_non_http_urls_are_rejected(self):
        for url in ("file:///etc/passwd", "http://127.0.0.1/admin", "http://localhost/", "http://10.0.0.2/"):
            payload = self._event(urls=[url])
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    google_alert_ingest.validate_event(payload)

    def test_url_fragment_is_removed_from_dedupe_fingerprint(self):
        first, first_hash = google_alert_ingest.normalized_public_url(
            "https://example.com/jobs/123#apply"
        )
        second, second_hash = google_alert_ingest.normalized_public_url(
            "https://example.com/jobs/123"
        )
        self.assertEqual(first, second)
        self.assertEqual(first_hash, second_hash)

    def test_event_link_count_is_bounded(self):
        payload = self._event(urls=[f"https://example.com/jobs/{i}" for i in range(101)])
        with self.assertRaisesRegex(ValueError, "at most 100"):
            google_alert_ingest.validate_event(payload)

    def test_boolean_schema_version_is_rejected(self):
        payload = self._event()
        payload["schema_version"] = True
        with self.assertRaisesRegex(ValueError, "schema version"):
            google_alert_ingest.validate_event(payload)

    def test_default_https_port_and_ipv6_are_normalized_safely(self):
        default_port, default_hash = google_alert_ingest.normalized_public_url(
            "https://example.com:443/jobs/123"
        )
        implicit_port, implicit_hash = google_alert_ingest.normalized_public_url(
            "https://example.com/jobs/123"
        )
        self.assertEqual(default_port, implicit_port)
        self.assertEqual(default_hash, implicit_hash)

        ipv6_url, _ = google_alert_ingest.normalized_public_url(
            "https://[2001:4860:4860::8888]/jobs/123"
        )
        self.assertTrue(ipv6_url.startswith("https://[2001:4860:4860::8888]/"))


if __name__ == "__main__":
    unittest.main()
