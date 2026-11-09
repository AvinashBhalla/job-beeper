from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from v2 import auth, board_discovery, radar, teamtailor


FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:tt="https://teamtailor.com/locations">
  <channel>
    <title>Acme Careers</title>
    <item>
      <title>Python Engineer</title>
      <description><![CDATA[<p>Build <strong>Python</strong> services and APIs.</p>]]></description>
      <pubDate>Mon, 09 Nov 2026 06:30:00 +0000</pubDate>
      <link>https://careers.acme.example/jobs/python-engineer</link>
      <remoteStatus>fully</remoteStatus>
      <guid isPermaLink="false">global-100</guid>
      <tt:locations><tt:location><tt:name>Berlin Office</tt:name><tt:city>Berlin</tt:city><tt:country>Germany</tt:country></tt:location></tt:locations>
      <tt:department>Engineering</tt:department><tt:role>Software Development</tt:role><tt:division>Product</tt:division>
    </item>
    <item>
      <title>Backend Developer</title>
      <description><![CDATA[<p>Develop distributed services.</p>]]></description>
      <pubDate>Sun, 08 Nov 2026 10:00:00 +0000</pubDate>
      <link>https://careers.acme.example/jobs/backend</link>
      <remoteStatus>temporary</remoteStatus>
      <guid isPermaLink="false">global-101</guid>
    </item>
  </channel>
</rss>'''


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class TeamtailorFeedParserTests(unittest.TestCase):
    def test_parses_published_jobs_and_namespace_metadata(self):
        rows = teamtailor.parse_public_rss(FEED, slug="acme", company="Configured Acme")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "Python Engineer")
        self.assertEqual(rows[0]["company"], "Configured Acme")
        self.assertEqual(rows[0]["location"], "Berlin, Germany")
        self.assertEqual(rows[0]["department"], "Engineering")
        self.assertEqual(rows[0]["role"], "Software Development")
        self.assertEqual(rows[0]["division"], "Product")
        self.assertEqual(rows[0]["remote_status"], "fully")
        self.assertEqual(rows[0]["posted"], "Mon, 09 Nov 2026 06:30:00 +0000")
        self.assertIn("Python services", rows[0]["description"])
        self.assertEqual(rows[1]["location"], "Remote")

    def test_rejects_dtd_entities_oversized_malformed_wrong_root_and_bad_slug(self):
        with self.assertRaisesRegex(ValueError, "DTD or entity"):
            teamtailor.parse_public_rss(b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>', slug="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "size limit"):
            teamtailor.parse_public_rss(b" " * (teamtailor.MAX_FEED_BYTES + 1), slug="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "malformed"):
            teamtailor.parse_public_rss(b"<rss><channel>", slug="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "root"):
            teamtailor.parse_public_rss(b"<jobs/>", slug="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "slug"):
            teamtailor.parse_public_rss(FEED, slug="../acme", company="Acme")

    def test_skips_unsafe_job_urls_and_deduplicates_global_ids(self):
        payload = b'''<rss><channel>
          <item><title>Bad</title><link>http://careers.acme.example/job</link><guid>bad</guid></item>
          <item><title>Bad local</title><link>https://127.0.0.1/job</link><guid>bad-local</guid></item>
          <item><title>Good one</title><link>https://careers.acme.example/job/1</link><guid>same-guid</guid></item>
          <item><title>Duplicate</title><link>https://careers.acme.example/job/2</link><guid>same-guid</guid></item>
        </channel></rss>'''
        rows = teamtailor.parse_public_rss(payload, slug="acme", company="Acme")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Good one")


class TeamtailorCollectorTests(unittest.TestCase):
    def test_collector_maps_publication_time_and_source_details(self):
        calls = []

        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            return FakeResponse(FEED)

        with patch.object(radar, "_tracked_source_get", side_effect=tracked), patch.object(radar, "source_state", {}):
            jobs = radar.teamtailor_collect({"teamtailor_boards": [{
                "careers_url": "https://acme.teamtailor.com/jobs", "company": "Acme", "registry_id": 42,
            }]})
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["source"], "teamtailor")
        self.assertEqual(jobs[0]["source_job_id"], "teamtailor-acme-" + teamtailor.parse_public_rss(FEED, slug="acme", company="Acme")[0]["reference"])
        self.assertEqual(jobs[0]["posted_precision"], "minute")
        self.assertEqual(jobs[0]["source_posted_at"], "2026-11-09T06:30:00+00:00")
        self.assertEqual(jobs[0]["source_details"]["board_registry_id"], 42)
        self.assertEqual(jobs[0]["source_details"]["department"], "Engineering")
        self.assertEqual(calls[0][1], "https://acme.teamtailor.com/jobs.rss")
        self.assertEqual(calls[0][2]["params"], {"per_page": 200, "offset": 0})
        self.assertFalse(calls[0][2]["allow_redirects"])

    def test_collector_paginates_until_short_page_and_honours_request_cap(self):
        items = []
        for index in range(200):
            items.append(
                f"<item><title>Role {index}</title><link>https://careers.acme.example/jobs/{index}</link><guid>id-{index}</guid></item>"
            )
        page_one = ("<rss><channel>" + "".join(items) + "</channel></rss>").encode()
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append(kwargs["params"]["offset"])
            return FakeResponse(page_one if len(calls) == 1 else FEED)
        with patch.object(radar, "_tracked_source_get", side_effect=tracked):
            jobs = radar.teamtailor_collect({"teamtailor_boards": [{
                "careers_url": "https://acme.teamtailor.com", "company": "Acme",
            }]})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls, [0, 200])
        self.assertEqual(len(jobs), 202)

    def test_429_honours_retry_after_and_stops_polling_boards(self):
        limited = FakeResponse(b"", 429, {"Retry-After": "120"})
        boards = [
            {"careers_url": "https://acme.teamtailor.com", "company": "Acme"},
            {"careers_url": "https://other.teamtailor.com", "company": "Other"},
        ]
        calls = []
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_get", side_effect=lambda *a, **kw: calls.append(a[1]) or limited
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured Teamtailor boards failed"):
                radar.teamtailor_collect({"teamtailor_boards": boards})
            self.assertEqual(radar.source_state["teamtailor"]["rate_limit_retry_after_seconds"], 120.0)
            self.assertGreater(radar._source_cooldown_remaining("teamtailor"), 100)
        self.assertEqual(len(calls), 1)

    def test_config_is_default_off_and_migrates_prior_version_off(self):
        base = radar._default_config()
        validated = radar.validate_config({
            **base,
            "teamtailor_boards": [{"careers_url": "https://acme.teamtailor.com/jobs", "company": "Acme", "registry_id": 5}],
        })
        self.assertFalse(validated["source_enabled"]["teamtailor"])
        self.assertEqual(validated["poll_seconds"]["teamtailor"], 300)
        self.assertEqual(validated["teamtailor_boards"][0]["registry_id"], 5)
        with self.assertRaises(radar.HTTPException):
            radar.validate_config({**base, "source_enabled": {"teamtailor": True}})
        migrated = radar._merge_config(
            {"config_version": 16, "source_enabled": {"teamtailor": False}},
            {"config_version": 15, "source_enabled": {"teamtailor": True}},
        )
        self.assertFalse(migrated["source_enabled"]["teamtailor"])

    def test_board_discovery_detects_and_probes_public_rss(self):
        candidate = board_discovery.detect_ats_board("https://acme.teamtailor.com/jobs")
        self.assertEqual(candidate["provider"], "teamtailor")
        self.assertEqual(candidate["board_key"], "acme")
        self.assertTrue(candidate["collector_available"])
        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(FEED)) as get:
            result = board_discovery.probe_public_board({
                "provider": "teamtailor", "board_url": "https://acme.teamtailor.com", "company": "Acme",
            })
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["jobs_observed"], 2)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])


class TeamtailorDiscoveryLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "qa.sqlite3"
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.config_patch = patch.object(radar, "RUNTIME_CONFIG_PATH", self.config_path)
        self.db_patch.start()
        self.config_patch.start()
        with patch.object(radar, "DEFAULT_CONFIG_PATH", Path(radar.__file__).with_name("config.json")):
            radar.init_db()
        auth.create_user(self.db_path, "teamtailor-admin@example.com", "a sufficiently strong test password", role="admin")
        self.client = TestClient(radar.app, base_url="https://testserver")
        login = self.client.post("/api/auth/login", json={
            "email": "teamtailor-admin@example.com", "password": "a sufficiently strong test password",
        })
        self.assertEqual(login.status_code, 200)
        self.csrf = self.client.cookies.get("job_beeper_csrf")

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_verified_board_requires_explicit_activation_and_can_be_deactivated(self):
        fake_result = {
            "company_name": "Acme", "website_url": "https://acme.example/",
            "careers_url": "https://acme.example/", "pages_checked": 1,
            "discovery_status": "boards_found", "errors": [],
            "boards": [{
                "provider": "teamtailor", "board_key": "acme",
                "board_url": "https://acme.teamtailor.com/jobs", "discovered_from": "https://acme.example/",
                "confidence": "high", "collector_source": "teamtailor", "collector_available": True,
            }],
        }
        with patch.object(radar.board_discovery, "discover_public_careers", return_value=fake_result):
            scanned = self.client.post("/api/discovery/companies/scan", json={
                "company_name": "Acme", "website_url": "https://acme.example",
            }, headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(scanned.status_code, 200, scanned.text)
        board_id = scanned.json()["board_ids"][0]
        self.assertFalse(radar.get_config()["source_enabled"]["teamtailor"])

        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(FEED)):
            verified = self.client.post(
                f"/api/discovery/boards/{board_id}/verify", headers={"X-CSRF-Token": self.csrf}
            )
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertFalse(verified.json()["scheduler_enabled"])
        self.assertFalse(radar.get_config()["source_enabled"]["teamtailor"])

        activated = self.client.post(
            f"/api/discovery/boards/{board_id}/activate", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertTrue(activated.json()["source_enabled"])
        self.assertTrue(activated.json()["baseline_pending"])
        self.assertTrue(radar.get_config()["source_enabled"]["teamtailor"])

        deactivated = self.client.post(
            f"/api/discovery/boards/{board_id}/deactivate", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(radar.get_config()["source_enabled"]["teamtailor"])
        self.assertEqual(radar.get_config()["teamtailor_boards"], [])


if __name__ == "__main__":
    unittest.main()
