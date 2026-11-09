from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from v2 import auth, board_discovery, personio, radar


FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
  <position>
    <id>4103</id><office>Munich</office>
    <additionalOffices><additionalOffice>Berlin</additionalOffice></additionalOffices>
    <department>Engineering</department><recruitingCategory>Technology</recruitingCategory>
    <name>Python Engineer</name>
    <jobDescriptions>
      <jobDescription><name>What you will do</name><value><![CDATA[<p>Build <strong>Python</strong> services.</p>]]></value></jobDescription>
      <jobDescription><name>Your profile</name><value><![CDATA[<p>Experience with APIs.</p>]]></value></jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType><seniority>experienced</seniority>
    <schedule>full-time</schedule><yearsOfExperience>2-5</yearsOfExperience>
    <keywords>Python, API, automation</keywords><occupation>software_engineering</occupation>
    <occupationCategory>engineering</occupationCategory><createdAt>2026-11-08T12:14:07+0200</createdAt>
  </position>
  <position>
    <id>4104</id><name>Frontend Engineer</name><office>Berlin</office>
    <jobDescriptions><jobDescription><name>Description</name><value><![CDATA[<p>React experience.</p>]]></value></jobDescription></jobDescriptions>
  </position>
</workzag-jobs>'''


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class PersonioFeedParserTests(unittest.TestCase):
    def test_extracts_position_fields_and_constructs_public_job_url(self):
        rows = personio.parse_public_positions(FEED, tenant="acme", extension="de")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["reference"], "4103")
        self.assertEqual(rows[0]["title"], "Python Engineer")
        self.assertEqual(rows[0]["location"], "Munich; Berlin")
        self.assertEqual(rows[0]["url"], "https://acme.jobs.personio.de/job/4103")
        self.assertIn("Python services", rows[0]["description"])
        self.assertIn("Experience with APIs", rows[0]["description"])
        self.assertEqual(rows[0]["employment_type"], "permanent")
        self.assertEqual(rows[0]["years_of_experience"], "2-5")
        self.assertEqual(rows[0]["created_at"], "2026-11-08T12:14:07+0200")

    def test_rejects_dtd_entities_oversized_malformed_wrong_root_and_invalid_tenant(self):
        with self.assertRaisesRegex(ValueError, "DTD or entity"):
            personio.parse_public_positions(b'<!DOCTYPE jobs [<!ENTITY x "bad">]><workzag-jobs/>', tenant="acme", extension="de")
        with self.assertRaisesRegex(ValueError, "size limit"):
            personio.parse_public_positions(b" " * (personio.MAX_FEED_BYTES + 1), tenant="acme", extension="de")
        with self.assertRaisesRegex(ValueError, "malformed"):
            personio.parse_public_positions(b"<workzag-jobs><position>", tenant="acme", extension="de")
        with self.assertRaisesRegex(ValueError, "root"):
            personio.parse_public_positions(b"<jobs/>", tenant="acme", extension="de")
        with self.assertRaisesRegex(ValueError, "tenant"):
            personio.parse_public_positions(FEED, tenant="acme.example", extension="de")

    def test_skips_missing_or_invalid_position_ids_and_duplicate_ids(self):
        payload = b'''<workzag-jobs>
          <position><id>1</id><name>First</name></position>
          <position><id>1</id><name>Duplicate</name></position>
          <position><id>../2</id><name>Invalid</name></position>
          <position><id>3</id></position>
        </workzag-jobs>'''
        rows = personio.parse_public_positions(payload, tenant="acme", extension="com")
        self.assertEqual([row["reference"] for row in rows], ["1"])


class PersonioCollectorTests(unittest.TestCase):
    def test_collector_preserves_created_at_as_metadata_not_posted_at(self):
        calls = []

        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            return FakeResponse(FEED)

        with patch.object(radar, "_tracked_source_get", side_effect=tracked), patch.object(radar, "source_state", {}):
            jobs = radar.personio_collect({"personio_boards": [{
                "careers_url": "https://acme.jobs.personio.de", "company": "Acme", "extension": "de", "registry_id": 19,
            }]})
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["source"], "personio")
        self.assertEqual(jobs[0]["source_job_id"], "personio-acme-4103")
        self.assertIsNone(jobs[0]["source_posted_at"])
        self.assertEqual(jobs[0]["posted_precision"], "unknown")
        self.assertEqual(jobs[0]["source_details"]["created_at"], "2026-11-08T12:14:07+0200")
        self.assertEqual(jobs[0]["source_details"]["board_registry_id"], 19)
        self.assertEqual(calls[0][1], "https://acme.jobs.personio.de/xml")
        self.assertEqual(calls[0][2]["params"], {"language": "en"})
        self.assertFalse(calls[0][2]["allow_redirects"])

    def test_429_honours_retry_after_and_stops_before_next_board(self):
        limited = FakeResponse(b"", 429, {"Retry-After": "180"})
        boards = [
            {"careers_url": "https://acme.jobs.personio.de", "company": "Acme"},
            {"careers_url": "https://other.jobs.personio.com", "company": "Other"},
        ]
        calls = []
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_get", side_effect=lambda *a, **kw: calls.append(a[1]) or limited
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured Personio boards failed"):
                radar.personio_collect({"personio_boards": boards})
            self.assertEqual(radar.source_state["personio"]["rate_limit_retry_after_seconds"], 180.0)
            self.assertGreater(radar._source_cooldown_remaining("personio"), 150)
        self.assertEqual(len(calls), 1)

    def test_config_is_opt_in_and_migrates_prior_version_off(self):
        base = radar._default_config()
        validated = radar.validate_config({
            **base,
            "personio_boards": [{"careers_url": "https://acme.jobs.personio.de", "company": "Acme", "extension": "de", "registry_id": 5}],
        })
        self.assertFalse(validated["source_enabled"]["personio"])
        self.assertEqual(validated["poll_seconds"]["personio"], 300)
        self.assertEqual(validated["personio_boards"][0]["registry_id"], 5)
        with self.assertRaises(radar.HTTPException):
            radar.validate_config({**base, "source_enabled": {"personio": True}})
        migrated = radar._merge_config(
            {"config_version": 16, "source_enabled": {"personio": False}},
            {"config_version": 15, "source_enabled": {"personio": True}},
        )
        self.assertFalse(migrated["source_enabled"]["personio"])

    def test_board_discovery_detects_and_probes_public_xml_feed(self):
        candidate = board_discovery.detect_ats_board("https://acme.jobs.personio.de")
        self.assertEqual(candidate["provider"], "personio")
        self.assertEqual(candidate["board_key"], "acme")
        self.assertTrue(candidate["collector_available"])
        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(FEED)) as get:
            result = board_discovery.probe_public_board({
                "provider": "personio", "board_url": "https://acme.jobs.personio.de",
            })
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["jobs_observed"], 2)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])


if __name__ == "__main__":
    unittest.main()


class PersonioDiscoveryLifecycleTests(unittest.TestCase):
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
        auth.create_user(self.db_path, "personio-admin@example.com", "a sufficiently strong test password", role="admin")
        self.client = TestClient(radar.app, base_url="https://testserver")
        login = self.client.post("/api/auth/login", json={
            "email": "personio-admin@example.com", "password": "a sufficiently strong test password",
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
                "provider": "personio", "board_key": "acme",
                "board_url": "https://acme.jobs.personio.de", "discovered_from": "https://acme.example/",
                "confidence": "high", "collector_source": "personio", "collector_available": True,
            }],
        }
        with patch.object(radar.board_discovery, "discover_public_careers", return_value=fake_result):
            scanned = self.client.post("/api/discovery/companies/scan", json={
                "company_name": "Acme", "website_url": "https://acme.example",
            }, headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(scanned.status_code, 200, scanned.text)
        board_id = scanned.json()["board_ids"][0]
        self.assertFalse(radar.get_config()["source_enabled"]["personio"])

        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(FEED)):
            verified = self.client.post(
                f"/api/discovery/boards/{board_id}/verify", headers={"X-CSRF-Token": self.csrf}
            )
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertFalse(verified.json()["scheduler_enabled"])
        self.assertFalse(radar.get_config()["source_enabled"]["personio"])

        activated = self.client.post(
            f"/api/discovery/boards/{board_id}/activate", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertTrue(activated.json()["source_enabled"])
        self.assertTrue(activated.json()["baseline_pending"])
        self.assertTrue(radar.get_config()["source_enabled"]["personio"])
        self.assertEqual(radar.get_config()["personio_boards"][0]["registry_id"], board_id)

        deactivated = self.client.post(
            f"/api/discovery/boards/{board_id}/deactivate", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(radar.get_config()["source_enabled"]["personio"])
        self.assertEqual(radar.get_config()["personio_boards"], [])
