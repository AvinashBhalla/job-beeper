from __future__ import annotations

import datetime as dt
import json
import sqlite3
import unittest

from v2.google_alerts_pipeline import process_google_alert_rss_queue
from v2.google_alerts_rss_polling import (
    GoogleAlertsFeedError,
    init_google_alerts_rss_schema,
)
from v2.google_alerts_safe_fetch import FetchedPublicPage, SafeFetchError

UTC = dt.timezone.utc
FIXED_NOW = dt.datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
PAGE_URL = "https://jobs.example.com/posting/123"


def job_page(
    *,
    title="Software Engineer",
    company="Example Labs",
    date_posted="2026-11-20",
    valid_through="2026-12-31T23:59:00Z",
):
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "hiringOrganization": {"@type": "Organization", "name": company},
        "description": "<p>Build backend APIs with Python.</p>",
        "datePosted": date_posted,
        "validThrough": valid_through,
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Bengaluru",
                "addressRegion": "Karnataka",
                "addressCountry": "India",
            },
        },
    }
    text = (
        '<html><script type="application/ld+json">'
        + json.dumps(posting)
        + "</script></html>"
    )
    return FetchedPublicPage(
        final_url=PAGE_URL,
        http_status=200,
        content_type="text/html",
        body=text.encode("utf-8"),
        text=text,
    )


class FakeFetcher:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if not self.outcomes:
            raise AssertionError("Unexpected fetch.")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class GoogleAlertsPipelineTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        init_google_alerts_rss_schema(self.conn)
        self._add_feed("feed-one", "Software Engineer India")

    def tearDown(self):
        self.conn.close()

    def _add_feed(self, feed_id, label):
        self.conn.execute(
            """
            INSERT INTO google_alert_rss_feed_state (
                feed_id, feed_label, created_at, updated_at
            ) VALUES (?, ?, ?, ?)
            """,
            (feed_id, label, FIXED_NOW.isoformat(), FIXED_NOW.isoformat()),
        )
        self.conn.commit()

    def _add_entry(
        self,
        *,
        feed_id="feed-one",
        entry_id="entry-1",
        url=PAGE_URL,
        canonical_url=PAGE_URL,
        attempt_count=0,
        status="queued",
    ):
        self.conn.execute(
            """
            INSERT INTO google_alert_rss_entries (
                feed_id, entry_id, title, snippet, destination_url,
                canonical_url, first_seen_at, last_seen_at,
                processing_status, attempt_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feed_id, entry_id, "Software Engineer", "snippet", url,
                canonical_url, FIXED_NOW.isoformat(), FIXED_NOW.isoformat(),
                status, attempt_count,
            ),
        )
        self.conn.commit()

    def _run(self, fetcher, *, upsert=None, normalize=None, **kwargs):
        inserted_jobs = []
        if upsert is None:
            def upsert(jobs):
                inserted_jobs.extend(jobs)
                return len(jobs)
        if normalize is None:
            normalize = lambda **values: values
        result = process_google_alert_rss_queue(
            self.conn,
            normalize_job_fn=normalize,
            upsert_jobs_fn=upsert,
            fetcher=fetcher,
            now=FIXED_NOW,
            **kwargs,
        )
        return result, inserted_jobs

    def _entry_state(self, feed_id="feed-one", entry_id="entry-1"):
        return self.conn.execute(
            """
            SELECT processing_status, attempt_count, last_error_code,
                   last_http_status, next_attempt_at
            FROM google_alert_rss_entries
            WHERE feed_id=? AND entry_id=?
            """,
            (feed_id, entry_id),
        ).fetchone()

    def test_verified_posting_flows_to_existing_upsert_callback(self):
        self._add_entry()
        fetcher = FakeFetcher([job_page()])
        result, jobs = self._run(fetcher)

        self.assertEqual(result.claimed, 1)
        self.assertEqual(result.verified, 1)
        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.needs_review, 0)
        self.assertEqual(len(fetcher.calls), 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["source"], "google_alerts")
        self.assertEqual(jobs[0]["company"], "Example Labs")
        self.assertEqual(jobs[0]["title"], "Software Engineer")
        self.assertEqual(jobs[0]["posted_precision"], "day")
        self.assertEqual(
            jobs[0]["source_details"]["google_alerts"]["observations"][0]["feed_id"],
            "feed-one",
        )
        self.assertEqual(self._entry_state()[0], "verified")

    def test_same_canonical_feed_url_is_fetched_once_for_multiple_alert_entries(self):
        self._add_feed("feed-two", "React Software Engineer")
        self._add_entry(feed_id="feed-one", entry_id="entry-one")
        self._add_entry(feed_id="feed-two", entry_id="entry-two")
        fetcher = FakeFetcher([job_page()])
        result, jobs = self._run(fetcher)

        self.assertEqual(result.claimed, 2)
        self.assertEqual(result.verified, 2)
        self.assertEqual(result.duplicate_entries_collapsed, 1)
        self.assertEqual(len(fetcher.calls), 1)
        self.assertEqual(len(jobs), 1)
        observations = jobs[0]["source_details"]["google_alerts"]["observations"]
        self.assertEqual({item["feed_id"] for item in observations}, {"feed-one", "feed-two"})
        self.assertEqual(self._entry_state("feed-one", "entry-one")[0], "verified")
        self.assertEqual(self._entry_state("feed-two", "entry-two")[0], "verified")

    def test_forbidden_page_is_blocked_without_retry_or_upsert(self):
        self._add_entry()
        fetcher = FakeFetcher([
            SafeFetchError("upstream_http_error", http_status=403)
        ])
        result, jobs = self._run(fetcher)

        self.assertEqual(result.blocked, 1)
        self.assertEqual(result.verified, 0)
        self.assertEqual(jobs, [])
        state = self._entry_state()
        self.assertEqual(state[0], "blocked")
        self.assertEqual(state[2], "upstream_http_error")
        self.assertEqual(state[3], 403)
        self.assertIsNone(state[4])

    def test_robots_disallow_is_blocked_without_bypass(self):
        self._add_entry()
        fetcher = FakeFetcher([SafeFetchError("robots_disallowed")])
        result, jobs = self._run(fetcher)
        self.assertEqual(result.blocked, 1)
        self.assertEqual(jobs, [])
        self.assertEqual(self._entry_state()[0], "blocked")

    def test_not_found_listing_is_rejected(self):
        self._add_entry()
        fetcher = FakeFetcher([
            SafeFetchError("upstream_http_error", http_status=404)
        ])
        result, jobs = self._run(fetcher)
        self.assertEqual(result.rejected, 1)
        self.assertEqual(jobs, [])
        self.assertEqual(self._entry_state()[0], "rejected")

    def test_rate_limit_is_retried_after_retry_after(self):
        self._add_entry()
        fetcher = FakeFetcher([
            SafeFetchError(
                "upstream_rate_limited",
                http_status=429,
                retry_after_seconds=180,
            )
        ])
        result, jobs = self._run(fetcher)
        self.assertEqual(result.retryable, 1)
        self.assertEqual(jobs, [])
        state = self._entry_state()
        self.assertEqual(state[0], "retryable_error")
        self.assertEqual(state[4], "2026-11-21T12:03:00+00:00")

    def test_retry_exhaustion_moves_to_dead_letter(self):
        self._add_entry(attempt_count=4, status="retryable_error")
        fetcher = FakeFetcher([
            SafeFetchError("connection_failed")
        ])
        result, jobs = self._run(fetcher, max_attempts=5)
        self.assertEqual(result.dead_letter, 1)
        self.assertEqual(jobs, [])
        self.assertEqual(self._entry_state()[0], "dead_letter")

    def test_expired_jobposting_is_rejected(self):
        self._add_entry()
        fetcher = FakeFetcher([
            job_page(valid_through="2026-11-20T23:59:00Z")
        ])
        result, jobs = self._run(fetcher)
        self.assertEqual(result.rejected, 1)
        self.assertEqual(jobs, [])
        self.assertEqual(self._entry_state()[0], "rejected")
        self.assertEqual(self._entry_state()[2], "posting_expired")

    def test_page_without_jobposting_is_needs_review(self):
        self._add_entry()
        page = FetchedPublicPage(
            final_url=PAGE_URL,
            http_status=200,
            content_type="text/html",
            body=b"<html><title>Search results</title></html>",
            text="<html><title>Search results</title></html>",
        )
        result, jobs = self._run(FakeFetcher([page]))
        self.assertEqual(result.needs_review, 1)
        self.assertEqual(jobs, [])
        self.assertEqual(self._entry_state()[0], "needs_review")
        self.assertEqual(self._entry_state()[2], "jobposting_jsonld_not_found")

    def test_unexpected_fetch_exception_is_retryable_and_sanitized(self):
        self._add_entry()
        fetcher = FakeFetcher([RuntimeError("private URL or token should not appear")])
        result, jobs = self._run(fetcher)
        self.assertEqual(result.retryable, 1)
        self.assertEqual(jobs, [])
        state = self._entry_state()
        self.assertEqual(state[0], "retryable_error")
        self.assertEqual(state[2], "fetcher_unexpected_error")

    def test_empty_queue_is_noop(self):
        result, jobs = self._run(FakeFetcher([]))
        self.assertEqual(result.claimed, 0)
        self.assertEqual(result.verified, 0)
        self.assertEqual(jobs, [])


if __name__ == "__main__":
    unittest.main()
