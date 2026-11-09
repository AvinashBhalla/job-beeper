from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from v2 import auth, board_discovery, radar, recruitee


FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<jobs>
  <job>
    <reference>REQ-100</reference><title>Python Engineer</title><company>Acme BV</company>
    <company_id>company-7</company_id>
    <description_requirements><![CDATA[<p>Build <strong>Python</strong> services.</p>]]></description_requirements>
    <locations><location><city>Amsterdam</city><country>NL</country></location></locations>
    <remote>true</remote><hybrid>false</hybrid><on_site>false</on_site>
    <experience>3+ years</experience><education>Bachelor</education><contract_type>Full time</contract_type>
    <category>Engineering</category><salary>EUR 60,000 - 75,000</salary>
    <url>https://acme.recruitee.com/o/python-engineer</url>
    <apply_url>https://acme.recruitee.com/o/python-engineer/apply</apply_url>
    <posted>2026-11-09T06:30:00Z</posted><updated>2026-11-09T06:55:00Z</updated>
    <credentials><partner_secret>DO-NOT-PERSIST-THIS</partner_secret></credentials>
  </job>
  <job>
    <reference>REQ-101</reference><title>Backend Engineer</title>
    <url>https://acme.recruitee.com/o/backend-engineer</url>
    <posted>2026-11-08</posted><updated>2026-11-09</updated><city>Utrecht</city><country>NL</country>
  </job>
</jobs>'''


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class RecruiteeFeedParserTests(unittest.TestCase):
    def test_extracts_allowlisted_fields_and_never_returns_credentials(self):
        rows = recruitee.parse_public_offers(FEED, tenant="acme", company="Configured Acme")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["reference"], "REQ-100")
        self.assertEqual(rows[0]["company"], "Acme BV")
        self.assertEqual(rows[0]["location"], "Amsterdam, NL")
        self.assertIn("Python services", rows[0]["description"])
        self.assertEqual(rows[0]["posted"], "2026-11-09T06:30:00Z")
        self.assertEqual(rows[0]["updated"], "2026-11-09T06:55:00Z")
        serialized = json.dumps(rows)
        self.assertNotIn("DO-NOT-PERSIST-THIS", serialized)
        self.assertNotIn("credentials", serialized.lower())

    def test_rejects_dtd_entities_oversized_malformed_and_wrong_root(self):
        with self.assertRaisesRegex(ValueError, "DTD or entity"):
            recruitee.parse_public_offers(b'<!DOCTYPE jobs [<!ENTITY x "bad">]><jobs/>', tenant="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "size limit"):
            recruitee.parse_public_offers(b" " * (recruitee.MAX_FEED_BYTES + 1), tenant="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "malformed"):
            recruitee.parse_public_offers(b"<jobs><job>", tenant="acme", company="Acme")
        with self.assertRaisesRegex(ValueError, "root"):
            recruitee.parse_public_offers(b"<unexpected/>", tenant="acme", company="Acme")

    def test_skips_non_https_or_off_tenant_job_urls(self):
        payload = b'<jobs><job><reference>1</reference><title>Bad</title><url>http://attacker.example/apply</url></job></jobs>'
        self.assertEqual(recruitee.parse_public_offers(payload, tenant="acme", company="Acme"), [])

    def test_allows_safe_employer_https_link_but_rejects_localhost_ip_and_credentials(self):
        safe = b'<offers><offer><id>100</id><title>Good</title><careers_url>https://careers.acme.example/o/100</careers_url></offer></offers>'
        self.assertEqual(len(recruitee.parse_public_offers(safe, tenant="acme", company="Acme")), 1)
        for url in ("http://careers.acme.example/job/1", "https://localhost/job/1", "https://127.0.0.1/job/1", "https://user:pass@careers.acme.example/job/1", "https://careers.acme.example:8443/job/1"):
            payload = f'<offers><offer><id>100</id><title>Bad</title><careers_url>{url}</careers_url></offer></offers>'.encode()
            self.assertEqual(recruitee.parse_public_offers(payload, tenant="acme", company="Acme"), [], url)

    def test_parses_observed_offers_root_and_raw_hash_wrapper_shape(self):
        offer = b'''<offer>
          <id>offer-900</id><slug>python-developer</slug><title>Python Developer</title>
          <company_name>Acme BV</company_name>
          <description><![CDATA[<p>Build platform services.</p>]]></description>
          <requirements><![CDATA[<p>Python experience.</p>]]></requirements>
          <location>Amsterdam</location><city>Amsterdam</city><country>NL</country>
          <careers_url>https://careers.acme.example/o/python-developer</careers_url>
          <apply_url>https://careers.acme.example/o/python-developer/apply</apply_url>
          <published_at>2026-11-09T06:00:00Z</published_at>
          <updated_at>2026-11-09T06:30:00Z</updated_at>
          <mailbox_email>do-not-persist@example.test</mailbox_email>
        </offer>'''
        for payload in (b"<offers>" + offer + b"</offers>", b"<hash><offers>" + offer + b"</offers></hash>"):
            rows = recruitee.parse_public_offers(payload, tenant="acme", company="Configured Acme")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["reference"], "offer-900")
            self.assertEqual(rows[0]["company"], "Acme BV")
            self.assertEqual(rows[0]["posted"], "2026-11-09T06:00:00Z")
            self.assertEqual(rows[0]["updated"], "2026-11-09T06:30:00Z")
            self.assertIn("Python experience", rows[0]["description"])
            self.assertNotIn("do-not-persist@example.test", json.dumps(rows))
            self.assertEqual(rows[0]["url"], "https://careers.acme.example/o/python-developer")


class RecruiteeCollectorTests(unittest.TestCase):
    def test_collector_maps_posted_not_updated_and_keeps_metadata_safe(self):
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            return FakeResponse(FEED)
        with patch.object(radar, "_tracked_source_get", side_effect=tracked), patch.object(radar, "source_state", {}):
            jobs = radar.recruitee_collect({"recruitee_boards": [{
                "careers_url": "https://acme.recruitee.com", "company": "Configured Acme", "registry_id": 14,
            }]})
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["source_job_id"], "recruitee-acme-REQ-100")
        self.assertEqual(jobs[0]["posted_precision"], "minute")
        self.assertEqual(jobs[1]["posted_precision"], "date")
        self.assertEqual(jobs[0]["source_details"]["board_registry_id"], 14)
        self.assertEqual(jobs[0]["source_details"]["updated_at"], "2026-11-09T06:55:00Z")
        self.assertEqual(jobs[0]["source_details"]["apply_url"], "https://acme.recruitee.com/o/python-engineer/apply")
        self.assertNotIn("DO-NOT-PERSIST-THIS", json.dumps(jobs))
        self.assertEqual(calls[0][1], "https://acme.recruitee.com/api/feeds/offers.xml")
        self.assertFalse(calls[0][2]["allow_redirects"])

    def test_429_honours_retry_after_and_stops_before_next_board(self):
        limited = FakeResponse(b"", 429, {"Retry-After": "120"})
        boards = [
            {"careers_url": "https://acme.recruitee.com", "company": "Acme"},
            {"careers_url": "https://other.recruitee.com", "company": "Other"},
        ]
        calls = []
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_get", side_effect=lambda *a, **kw: calls.append(a[1]) or limited
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured Recruitee boards failed"):
                radar.recruitee_collect({"recruitee_boards": boards})
            self.assertEqual(radar.source_state["recruitee"]["rate_limit_retry_after_seconds"], 120.0)
            self.assertGreater(radar._source_cooldown_remaining("recruitee"), 100)
        self.assertEqual(len(calls), 1)

    def test_config_is_opt_in_and_migrates_prior_version_off(self):
        base = radar._default_config()
        validated = radar.validate_config({
            **base,
            "recruitee_boards": [{"careers_url": "https://acme.recruitee.com", "company": "Acme", "registry_id": 7}],
        })
        self.assertFalse(validated["source_enabled"]["recruitee"])
        self.assertEqual(validated["poll_seconds"]["recruitee"], 120)
        self.assertEqual(validated["recruitee_boards"][0]["registry_id"], 7)
        with self.assertRaises(radar.HTTPException):
            radar.validate_config({**base, "source_enabled": {"recruitee": True}})
        migrated = radar._merge_config(
            {"config_version": 16, "source_enabled": {"recruitee": False}},
            {"config_version": 15, "source_enabled": {"recruitee": True}},
        )
        self.assertFalse(migrated["source_enabled"]["recruitee"])

    def test_board_discovery_detects_and_probes_recruitee_public_xml_feed(self):
        candidate = board_discovery.detect_ats_board("https://acme.recruitee.com")
        self.assertEqual(candidate["provider"], "recruitee")
        self.assertEqual(candidate["board_key"], "acme")
        self.assertTrue(candidate["collector_available"])
        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(FEED)) as get:
            result = board_discovery.probe_public_board({
                "provider": "recruitee", "board_url": "https://acme.recruitee.com", "company": "Acme",
            })
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["jobs_observed"], 2)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])


class RecruiteeDiscoveryLifecycleTests(unittest.TestCase):
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
        auth.create_user(self.db_path, "recruitee-admin@example.com", "a sufficiently strong test password", role="admin")
        self.client = TestClient(radar.app, base_url="https://testserver")
        login = self.client.post("/api/auth/login", json={
            "email": "recruitee-admin@example.com", "password": "a sufficiently strong test password",
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
                "provider": "recruitee", "board_key": "acme",
                "board_url": "https://acme.recruitee.com", "discovered_from": "https://acme.example/",
                "confidence": "high", "collector_source": "recruitee", "collector_available": True,
            }],
        }
        with patch.object(radar.board_discovery, "discover_public_careers", return_value=fake_result):
            scanned = self.client.post("/api/discovery/companies/scan", json={
                "company_name": "Acme", "website_url": "https://acme.example",
            }, headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(scanned.status_code, 200, scanned.text)
        board_id = scanned.json()["board_ids"][0]
        self.assertFalse(radar.get_config()["source_enabled"]["recruitee"])

        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(FEED)):
            verified = self.client.post(
                f"/api/discovery/boards/{board_id}/verify", headers={"X-CSRF-Token": self.csrf}
            )
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertFalse(verified.json()["scheduler_enabled"])
        self.assertFalse(radar.get_config()["source_enabled"]["recruitee"])

        activated = self.client.post(
            f"/api/discovery/boards/{board_id}/activate", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertTrue(activated.json()["source_enabled"])
        self.assertTrue(activated.json()["baseline_pending"])
        self.assertTrue(radar.get_config()["source_enabled"]["recruitee"])
        self.assertEqual(radar.get_config()["recruitee_boards"][0]["registry_id"], board_id)

        deactivated = self.client.post(
            f"/api/discovery/boards/{board_id}/deactivate", headers={"X-CSRF-Token": self.csrf}
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(radar.get_config()["source_enabled"]["recruitee"])
        self.assertEqual(radar.get_config()["recruitee_boards"], [])


if __name__ == "__main__":
    unittest.main()
