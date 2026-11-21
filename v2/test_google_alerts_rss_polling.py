from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from v2.google_alerts_rss import parse_google_alerts_atom
from v2.google_alerts_rss_polling import (
    FeedCheckpoint,
    FeedPollResult,
    GoogleAlertsFeedError,
    _validate_feed_url,
    get_feed_checkpoint,
    init_google_alerts_rss_schema,
    load_google_alerts_feed_configs,
    poll_google_alerts_feed,
    record_feed_failure,
    record_feed_success,
)
from v2.test_google_alerts_rss import SAMPLE_FEED


FEED_URL = "https://www.google.com/alerts/feeds/12345678901234567890/12345678901234567890"
FIXED_NOW = datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, status_code, headers=None, body=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.closed = False

    def iter_content(self, chunk_size=65536):
        yield self.body

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected additional HTTP request.")
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class GoogleAlertsFeedConfigTests(unittest.TestCase):
    def _write_config(self, directory, document, mode=0o600):
        path = Path(directory) / "feeds.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        os.chmod(path, mode)
        return path

    def test_loads_owner_only_feed_config_and_hides_url_from_repr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(
                directory,
                {
                    "feeds": [{
                        "id": "software-engineer-react",
                        "label": "Software Engineer India React TypeScript",
                        "url": FEED_URL,
                    }]
                },
            )
            feeds = load_google_alerts_feed_configs(path)
        self.assertEqual(len(feeds), 1)
        self.assertEqual(feeds[0].feed_id, "software-engineer-react")
        self.assertEqual(feeds[0].label, "Software Engineer India React TypeScript")
        self.assertNotIn("12345678901234567890", repr(feeds[0]))

    def test_rejects_group_or_world_readable_feed_config(self):
        if os.name != "posix":
            self.skipTest("POSIX file permission check")
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(
                directory, {"feeds": [{"id": "feed-1", "label": "test", "url": FEED_URL}]},
                mode=0o644,
            )
            with self.assertRaises(GoogleAlertsFeedError) as caught:
                load_google_alerts_feed_configs(path)
        self.assertEqual(caught.exception.code, "feed_config_permissions_too_open")

    def test_rejects_duplicate_feed_ids_without_echoing_feed_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(
                directory,
                {"feeds": [
                    {"id": "same", "label": "first", "url": FEED_URL},
                    {"id": "same", "label": "second", "url": FEED_URL},
                ]},
            )
            with self.assertRaises(GoogleAlertsFeedError) as caught:
                load_google_alerts_feed_configs(path)
        self.assertEqual(caught.exception.code, "feed_config_invalid_entry")
        self.assertNotIn("12345678901234567890", str(caught.exception))

    def test_rejects_external_feed_url_without_echoing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_url = "https://attacker.example/private-feed"
            path = self._write_config(
                directory,
                {"feeds": [{"id": "bad", "label": "bad", "url": secret_url}]},
            )
            with self.assertRaises(GoogleAlertsFeedError) as caught:
                load_google_alerts_feed_configs(path)
        self.assertEqual(caught.exception.code, "invalid_feed_url")
        self.assertNotIn(secret_url, str(caught.exception))

    def test_rejects_config_path_inside_repository(self):
        repo_config = Path(__file__).resolve().parent / "test-rejected-feed-config.json"
        repo_config.write_text('{"feeds":[]}', encoding="utf-8")
        os.chmod(repo_config, 0o600)
        try:
            with self.assertRaises(GoogleAlertsFeedError) as caught:
                load_google_alerts_feed_configs(repo_config)
            self.assertEqual(
                caught.exception.code, "feed_config_must_be_outside_repository"
            )
        finally:
            repo_config.unlink(missing_ok=True)

    def test_rejects_missing_config_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "does-not-exist.json"
            with self.assertRaises(GoogleAlertsFeedError) as caught:
                load_google_alerts_feed_configs(missing)
        self.assertEqual(caught.exception.code, "feed_config_not_found")


class GoogleAlertsPollingTests(unittest.TestCase):
    def test_fetches_atom_feed_with_response_validators(self):
        response = FakeResponse(
            200,
            {
                "Content-Type": "application/atom+xml; charset=utf-8",
                "ETag": '"feed-v1"',
                "Last-Modified": "Sat, 21 Nov 2026 10:00:00 GMT",
            },
            SAMPLE_FEED.encode("utf-8"),
        )
        session = FakeSession(response)
        result = poll_google_alerts_feed(
            FEED_URL, session=session, now=FIXED_NOW
        )

        self.assertEqual(result.status, "modified")
        self.assertEqual(result.http_status, 200)
        self.assertEqual(len(result.entries), 2)
        self.assertEqual(result.etag, '"feed-v1"')
        self.assertEqual(
            result.last_modified, "Sat, 21 Nov 2026 10:00:00 GMT"
        )
        self.assertEqual(len(session.calls), 1)
        request = session.calls[0][1]
        self.assertFalse(request["allow_redirects"])
        self.assertTrue(request["stream"])
        self.assertIn("application/atom+xml", request["headers"]["Accept"])
        self.assertTrue(response.closed)

    def test_uses_conditional_headers_and_handles_304(self):
        response = FakeResponse(304, {"Cache-Control": "private, max-age=0"})
        session = FakeSession(response)
        result = poll_google_alerts_feed(
            FEED_URL,
            FeedCheckpoint(etag='"known"', last_modified="Sat, 21 Nov 2026 09:00:00 GMT"),
            session=session,
            now=FIXED_NOW,
        )

        request_headers = session.calls[0][1]["headers"]
        self.assertEqual(request_headers["If-None-Match"], '"known"')
        self.assertEqual(
            request_headers["If-Modified-Since"],
            "Sat, 21 Nov 2026 09:00:00 GMT",
        )
        self.assertEqual(result.status, "not_modified")
        self.assertEqual(result.entries, ())
        self.assertEqual(result.etag, '"known"')
        self.assertTrue(response.closed)

    def test_allows_same_origin_google_redirect(self):
        redirect = FakeResponse(302, {"Location": "/alerts/feeds/12345678901234567890/12345678901234567891"})
        content = FakeResponse(
            200, {"Content-Type": "application/xml"}, SAMPLE_FEED.encode("utf-8")
        )
        session = FakeSession(redirect, content)
        result = poll_google_alerts_feed(FEED_URL, session=session, now=FIXED_NOW)
        self.assertEqual(result.status, "modified")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(
            session.calls[1][0],
            "https://www.google.com/alerts/feeds/12345678901234567890/12345678901234567891",
        )

    def test_rejects_redirect_to_external_host(self):
        response = FakeResponse(
            302, {"Location": "https://attacker.example/collect"}
        )
        session = FakeSession(response)
        with self.assertRaises(GoogleAlertsFeedError) as caught:
            poll_google_alerts_feed(FEED_URL, session=session, now=FIXED_NOW)
        self.assertEqual(caught.exception.code, "invalid_feed_url")
        self.assertEqual(len(session.calls), 1)
        self.assertTrue(response.closed)

    def test_rejects_non_google_feed_url_without_requesting_it(self):
        session = FakeSession()
        with self.assertRaises(GoogleAlertsFeedError) as caught:
            poll_google_alerts_feed(
                "https://attacker.example/alerts/feeds/123456/123456",
                session=session,
                now=FIXED_NOW,
            )
        self.assertEqual(caught.exception.code, "invalid_feed_url")
        self.assertEqual(session.calls, [])

    def test_rejects_invalid_feed_path_and_query_parameters(self):
        for value in (
            "https://www.google.com/alerts/feeds/1234",
            FEED_URL + "?token=leak",
            "http://www.google.com/alerts/feeds/123456/123456",
            "https://user:pass@www.google.com/alerts/feeds/123456/123456",
            "https://www.google.com:8443/alerts/feeds/123456/123456",
        ):
            with self.subTest(value=value), self.assertRaises(GoogleAlertsFeedError):
                _validate_feed_url(value)

    def test_rate_limit_exposes_retry_after_without_url(self):
        response = FakeResponse(429, {"Retry-After": "90"})
        session = FakeSession(response)
        with self.assertRaises(GoogleAlertsFeedError) as caught:
            poll_google_alerts_feed(FEED_URL, session=session, now=FIXED_NOW)
        self.assertEqual(caught.exception.code, "rate_limited")
        self.assertEqual(caught.exception.http_status, 429)
        self.assertEqual(caught.exception.retry_after_seconds, 90)
        self.assertNotIn("12345678901234567890", str(caught.exception))

    def test_rejects_unexpected_content_type(self):
        response = FakeResponse(200, {"Content-Type": "text/html"}, b"<html/>")
        with self.assertRaises(GoogleAlertsFeedError) as caught:
            poll_google_alerts_feed(FEED_URL, session=FakeSession(response), now=FIXED_NOW)
        self.assertEqual(caught.exception.code, "unexpected_content_type")

    def test_enforces_streamed_response_size_limit(self):
        response = FakeResponse(
            200, {"Content-Type": "application/atom+xml"}, b"x" * 21
        )
        with self.assertRaises(GoogleAlertsFeedError) as caught:
            poll_google_alerts_feed(
                FEED_URL, session=FakeSession(response), max_bytes=20, now=FIXED_NOW
            )
        self.assertEqual(caught.exception.code, "feed_too_large")

    def test_rejects_malformed_atom_response(self):
        response = FakeResponse(
            200, {"Content-Type": "application/atom+xml"}, b"<feed/>"
        )
        with self.assertRaises(GoogleAlertsFeedError) as caught:
            poll_google_alerts_feed(FEED_URL, session=FakeSession(response), now=FIXED_NOW)
        self.assertEqual(caught.exception.code, "invalid_atom_feed")


class GoogleAlertsFeedStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_google_alerts_rss_schema(self.conn)
        self.feed = parse_google_alerts_atom(SAMPLE_FEED)

    def tearDown(self):
        self.conn.close()

    def _result(self, *, status="modified", fetched_at="2026-11-21T10:00:00+00:00", etag='"v1"', feed=None):
        return FeedPollResult(
            status=status,
            http_status=200 if status == "modified" else 304,
            fetched_at=fetched_at,
            etag=etag,
            last_modified="Sat, 21 Nov 2026 10:00:00 GMT",
            feed=self.feed if feed is None and status == "modified" else feed,
        )

    def test_persists_entries_and_checkpoints_without_feed_url(self):
        result = record_feed_success(
            self.conn,
            feed_id="feed-001",
            feed_label="software-engineer-india",
            result=self._result(),
        )
        self.assertEqual(result.new_entries, 2)
        self.assertEqual(result.total_entries, 2)
        self.assertEqual(get_feed_checkpoint(self.conn, "feed-001").etag, '"v1"')

        columns = {
            row[1] for row in self.conn.execute(
                "PRAGMA table_info(google_alert_rss_feed_state)"
            )
        }
        self.assertNotIn("feed_url", columns)
        row = self.conn.execute(
            "SELECT title, destination_url, processing_status FROM google_alert_rss_entries ORDER BY entry_id LIMIT 1"
        ).fetchone()
        self.assertEqual(row[2], "queued")
        self.assertIn("https://", row[1])

    def test_repoll_is_idempotent_and_does_not_reset_processing_state(self):
        first = self._result()
        record_feed_success(
            self.conn, feed_id="feed-001", feed_label="test", result=first
        )
        self.conn.execute(
            "UPDATE google_alert_rss_entries SET processing_status='verified' "
            "WHERE feed_id='feed-001'"
        )
        second = self._result(fetched_at="2026-11-21T10:05:00+00:00", etag='"v2"')
        recorded = record_feed_success(
            self.conn, feed_id="feed-001", feed_label="test", result=second
        )
        self.assertEqual(recorded.new_entries, 0)
        self.assertEqual(recorded.total_entries, 2)
        statuses = {
            row[0] for row in self.conn.execute(
                "SELECT DISTINCT processing_status FROM google_alert_rss_entries"
            )
        }
        self.assertEqual(statuses, {"verified"})
        self.assertEqual(get_feed_checkpoint(self.conn, "feed-001").etag, '"v2"')

    def test_304_keeps_existing_validators(self):
        record_feed_success(
            self.conn, feed_id="feed-001", feed_label="test", result=self._result()
        )
        not_modified = self._result(
            status="not_modified",
            fetched_at="2026-11-21T10:10:00+00:00",
            etag=None,
            feed=None,
        )
        saved = record_feed_success(
            self.conn, feed_id="feed-001", feed_label="test", result=not_modified
        )
        self.assertEqual(saved.new_entries, 0)
        checkpoint = get_feed_checkpoint(self.conn, "feed-001")
        self.assertEqual(checkpoint.etag, '"v1"')
        self.assertEqual(
            checkpoint.last_modified, "Sat, 21 Nov 2026 10:00:00 GMT"
        )

    def test_failure_stores_error_code_and_backoff_not_exception_text(self):
        error = GoogleAlertsFeedError(
            "rate_limited", http_status=429, retry_after_seconds=60
        )
        record_feed_failure(
            self.conn,
            feed_id="feed-001",
            feed_label="test",
            error=error,
            checked_at="2026-11-21T10:00:00+00:00",
        )
        row = self.conn.execute(
            """
            SELECT last_error_code, consecutive_failures, retry_after_at,
                   last_http_status
            FROM google_alert_rss_feed_state WHERE feed_id='feed-001'
            """
        ).fetchone()
        self.assertEqual(row[0], "rate_limited")
        self.assertEqual(row[1], 1)
        self.assertEqual(row[2], "2026-11-21T10:01:00+00:00")
        self.assertEqual(row[3], 429)


if __name__ == "__main__":
    unittest.main()
