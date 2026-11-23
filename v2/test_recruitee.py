import unittest
from unittest.mock import patch

import requests

from v2 import board_discovery, board_scheduler, radar, recruitee


def response(content: bytes, status: int = 200) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result._content = content
    result._content_consumed = True
    return result


FORMATTED = b"""<offers>
  <offer><id>123</id><title>Backend Engineer</title><slug>backend-engineer</slug>
    <careers_url>https://tether.recruitee.com/o/backend-engineer?ref=example</careers_url>
    <description><![CDATA[<p>Build Python services.</p>]]></description>
    <requirements><![CDATA[<p>2+ years of experience with PostgreSQL.</p>]]></requirements>
    <published_at>2026-11-23 08:00:00 UTC</published_at><remote>true</remote>
    <locations><location><city>Bengaluru</city><country>India</country></location>
      <location><city>Pune</city><country>India</country></location></locations>
    <credentials><token>never-persist-this</token></credentials>
  </offer>
  <offer><id>123</id><title>Duplicate</title><slug>backend-engineer</slug></offer>
  <offer><id>234</id><title>Draft</title><status>draft</status><slug>draft</slug></offer>
</offers>"""


class RecruiteeTests(unittest.TestCase):
    def test_formatted_feed_reaches_collector_and_scheduler(self):
        config = radar._default_config()
        config["source_enabled"] = {"recruitee": True}
        config["recruitee_boards"] = [{"board": "Tether", "company": "Tether"}]
        config = radar.validate_config(config)
        schedules = board_scheduler.configured_boards(config)
        self.assertEqual(schedules[0]["host_key"], "tether.recruitee.com")
        with patch.object(radar, "_tracked_source_get", return_value=response(FORMATTED)) as get:
            jobs = radar.recruitee_collect(config)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(get.call_args.args[1], "https://tether.recruitee.com/api/feeds/offers.xml")
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        job = jobs[0]
        self.assertEqual(job["source_job_id"], "recruitee-tether-123")
        self.assertEqual(job["url"], "https://tether.recruitee.com/o/backend-engineer")
        self.assertEqual(job["posted_precision"], "minute")
        self.assertEqual(job["source_details"]["workplace_type"], "remote")
        self.assertEqual(job["location"], "Bengaluru, India / Pune, India")
        self.assertIn("2+ years", job["description"])
        self.assertNotIn("never-persist-this", str(job))

    def test_legacy_and_raw_feed_allow_only_safe_link_and_publication_time(self):
        legacy = b"""<jobs><job><reference>old-1</reference><title>Role</title><slug>engineer</slug>
          <url>https://another-domain.example/o/engineer</url><updated>2026-01-01T00:00:00Z</updated>
          <description_requirements><![CDATA[<p>Write TypeScript</p>]]></description_requirements>
          </job></jobs>"""
        item = recruitee.posting(recruitee.read_offers(response(legacy))[0], "tether")
        self.assertEqual(item["url"], "https://tether.recruitee.com/o/engineer")
        self.assertIsNone(item["published_at"])
        raw = b"<hash><offers><offer><status>published</status></offer><offer><status>internal</status></offer></offers></hash>"
        self.assertEqual(len(recruitee.read_offers(response(raw))), 1)

    def test_rejects_dtd_oversize_and_redirect(self):
        with self.assertRaisesRegex(ValueError, "Document type"):
            recruitee.read_offers(response(b"<!DOCTYPE offers><offers/>"))
        with patch.object(recruitee, "MAX_FEED_BYTES", 8), self.assertRaisesRegex(ValueError, "response limit"):
            recruitee.read_offers(response(b"<offers/>"))
        with self.assertRaisesRegex(ValueError, "response status"):
            recruitee.read_offers(response(b"<offers/>", 302))

    def test_registered_board_can_be_verified_using_the_same_feed(self):
        candidate = board_discovery.detect_ats_board("https://tether.recruitee.com/o/backend-engineer")
        self.assertEqual(candidate["collector_source"], "recruitee")
        normalized = radar._normalise_global_ats_candidate_url(candidate["board_url"])
        self.assertEqual(normalized["board_url"], "https://tether.recruitee.com")
        with patch.object(board_discovery.requests, "get", return_value=response(FORMATTED)) as get:
            verified = board_discovery.probe_public_board(candidate)
        self.assertTrue(verified["verified"])
        self.assertEqual(get.call_args.args[0], "https://tether.recruitee.com/api/feeds/offers.xml")
