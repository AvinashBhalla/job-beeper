from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from v2 import auth, board_discovery, breezy, radar


JOBS = [
    {
        "id": f"job-{i}", "friendly_id": f"friendly-{i}",
        "name": f"Software Engineer {i}",
        "url": f"https://thirdchannel-inc.breezy.hr/p/{i}",
        "published_date": "2026-11-09T06:30:00Z",
        "type": {"id": "full-time", "name": "Full-time"},
        "location": {"city": "Berlin", "state": "", "country": "Germany",
                     "name": "Berlin, Germany", "is_remote": i % 3 == 0},
        "locations": [{"city": "Berlin", "country": "Germany",
                       "name": "Berlin, Germany", "is_remote": i % 3 == 0}],
        "department": "Engineering", "salary": "EUR 60k-80k",
        "company": {"name": "ThirdChannel", "friendly_id": "thirdchannel-inc"},
    } for i in range(1, 26)
]


def detail_html(i=1):
    payload = {
        "@context": "https://schema.org", "@type": "JobPosting",
        "title": f"Software Engineer {i}",
        "description": "<p>Build <strong>reliable</strong> Python services.</p>",
        "datePosted": "2026-11-09T06:30:00Z", "employmentType": "FULL_TIME",
        "baseSalary": {"@type": "MonetaryAmount", "currency": "EUR"},
        "jobLocation": {"@type": "Place", "name": "Berlin"},
        "url": f"https://thirdchannel-inc.breezy.hr/p/{i}",
    }
    return ("<html><script type='application/ld+json'>" + json.dumps(payload) + "</script></html>").encode()


class FakeResponse:
    def __init__(self, payload=None, content=None, status_code=200, headers=None):
        self._payload = payload
        self.content = content if content is not None else json.dumps(payload).encode()
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload if self._payload is not None else json.loads(self.content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class BreezyParserTests(unittest.TestCase):
    def test_parses_list_location_remote_salary_and_company(self):
        rows = breezy.parse_public_jobs(JOBS, tenant="thirdchannel-inc", company="Configured")
        self.assertEqual(len(rows), 25)
        self.assertEqual(rows[0]["reference"], "job-1")
        self.assertEqual(rows[0]["company"], "ThirdChannel")
        self.assertEqual(rows[0]["location"], "Berlin, Germany")
        self.assertEqual(rows[0]["salary"], "EUR 60k-80k")
        self.assertEqual(rows[0]["employment_type"], "Full-time")
        self.assertFalse(rows[0]["remote"])
        self.assertTrue(rows[2]["remote"])

    def test_rejects_unsafe_urls_bad_tenants_and_payloads(self):
        for url in ("http://thirdchannel-inc.breezy.hr/p/1", "https://evil.example/p/1",
                    "https://localhost/p/1", "https://thirdchannel-inc.breezy.hr:8443/p/1",
                    "https://user:pass@thirdchannel-inc.breezy.hr/p/1"):
            self.assertEqual(breezy.parse_public_jobs(
                [{"id": "1", "name": "Bad", "url": url}],
                tenant="thirdchannel-inc", company="Acme"), [], url)
        with self.assertRaisesRegex(ValueError, "slug"):
            breezy.parse_public_jobs(JOBS, tenant="../bad", company="Acme")
        with self.assertRaisesRegex(ValueError, "JSON list"):
            breezy.parse_public_jobs({"jobs": JOBS}, tenant="thirdchannel-inc", company="Acme")
        with self.assertRaisesRegex(ValueError, "listing limit"):
            breezy.parse_public_jobs(JOBS * 130, tenant="thirdchannel-inc", company="Acme")

    def test_deduplicates_ids_and_skips_invalid_rows(self):
        payload = [
            {"id": "same", "name": "First", "url": "https://thirdchannel-inc.breezy.hr/p/1"},
            {"id": "same", "name": "Duplicate", "url": "https://thirdchannel-inc.breezy.hr/p/2"},
            {"id": "../bad", "name": "Bad", "url": "https://thirdchannel-inc.breezy.hr/p/3"},
            {"id": "missing-title", "url": "https://thirdchannel-inc.breezy.hr/p/4"},
        ]
        rows = breezy.parse_public_jobs(payload, tenant="thirdchannel-inc", company="Acme")
        self.assertEqual([row["title"] for row in rows], ["First"])

    def test_extracts_jobposting_jsonld_allowlist(self):
        parsed = breezy.parse_public_job_detail(detail_html())
        self.assertEqual(parsed["description"], "Build reliable Python services.")
        self.assertEqual(parsed["date_posted"], "2026-11-09T06:30:00Z")
        self.assertEqual(parsed["employment_type"], "FULL_TIME")
        self.assertEqual(parsed["salary_json"]["currency"], "EUR")
        self.assertTrue(parsed["details_fetched"])
        self.assertNotIn("<html", json.dumps(parsed).lower())

    def test_skips_invalid_jsonld_and_rejects_nonbytes_or_oversized(self):
        self.assertIsNone(breezy.parse_public_job_detail(
            b"<html><script type='application/ld+json'>{bad}</script></html>"))
        with self.assertRaisesRegex(ValueError, "bytes"):
            breezy.parse_public_job_detail("not bytes")
        with self.assertRaisesRegex(ValueError, "size limit"):
            breezy.parse_public_job_detail(b" " * (breezy.MAX_DETAIL_BYTES + 1))


class BreezyCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "jobs.db"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE jobs (source TEXT, source_job_id TEXT, description TEXT, first_seen_at TEXT)")
        self.db_patch = patch.object(radar, "DB_PATH", self.db)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_collector_fetches_only_bounded_details(self):
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append(endpoint)
            if endpoint.endswith("/json"):
                return FakeResponse(payload=JOBS)
            return FakeResponse(content=detail_html(int(endpoint.rsplit("/", 1)[-1])))
        with patch.object(radar, "_tracked_source_get", side_effect=tracked), \
             patch.object(radar, "source_state", {}), patch.object(radar.time, "sleep"):
            jobs = radar.breezy_collect({"breezy_boards": [{
                "careers_url": "https://thirdchannel-inc.breezy.hr", "company": "Acme", "registry_id": 11,
            }]})
        detail_calls = [url for url in calls if not url.endswith("/json")]
        self.assertEqual(len(jobs), 25)
        self.assertEqual(len(detail_calls), breezy.MAX_DETAIL_FETCHES_PER_BOARD)
        self.assertEqual(sum(bool(j["description"]) for j in jobs), 20)
        self.assertEqual(jobs[0]["source_posted_at"], "2026-11-09T06:30:00+00:00")
        self.assertEqual(jobs[0]["source_details"]["board_registry_id"], 11)

    def test_backfills_missing_descriptions_before_already_hydrated_jobs(self):
        with sqlite3.connect(self.db) as conn:
            for i in range(1, 13):
                conn.execute("INSERT INTO jobs VALUES (?,?,?,?)",
                             ("breezy", f"breezy-thirdchannel-inc-job-{i}", "", f"2026-11-{i:02d}T00:00:00+00:00"))
            conn.execute("INSERT INTO jobs VALUES (?,?,?,?)",
                         ("breezy", "breezy-thirdchannel-inc-job-13", "Already hydrated", "2026-11-13T00:00:00+00:00"))
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append(endpoint)
            if endpoint.endswith("/json"):
                return FakeResponse(payload=JOBS)
            return FakeResponse(content=detail_html(int(endpoint.rsplit("/", 1)[-1])))
        with patch.object(radar, "_tracked_source_get", side_effect=tracked), \
             patch.object(radar, "source_state", {}), patch.object(radar.time, "sleep"):
            radar.breezy_collect({"breezy_boards": [{
                "careers_url": "https://thirdchannel-inc.breezy.hr", "company": "Acme",
            }]})
        details = [url.rsplit("/", 1)[-1] for url in calls if not url.endswith("/json")]
        self.assertEqual(len(details), 20)
        self.assertNotIn("13", details)
        self.assertEqual(len(details), len(set(details)))

    def test_detail_budget_is_global_across_multiple_boards(self):
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append(endpoint)
            if endpoint.endswith("/json"):
                tenant = endpoint.split("//", 1)[1].split(".", 1)[0]
                rows = copy.deepcopy(JOBS)
                for row in rows:
                    row["url"] = row["url"].replace("thirdchannel-inc", tenant)
                return FakeResponse(payload=rows)
            return FakeResponse(content=detail_html(int(endpoint.rsplit("/", 1)[-1])))
        with patch.object(radar, "_tracked_source_get", side_effect=tracked), \
             patch.object(radar, "source_state", {}), patch.object(radar.time, "sleep"):
            jobs = radar.breezy_collect({"breezy_boards": [
                {"careers_url": "https://thirdchannel-inc.breezy.hr", "company": "First"},
                {"careers_url": "https://secondco.breezy.hr", "company": "Second"},
            ]})
        self.assertEqual(sum(url.endswith("/json") for url in calls), 2)
        self.assertEqual(sum(not url.endswith("/json") for url in calls), breezy.MAX_DETAIL_FETCHES_PER_BOARD)
        self.assertEqual(len(jobs), 50)

    def test_429_honours_retry_after_and_stops_next_board(self):
        limited = FakeResponse(payload={}, status_code=429, headers={"Retry-After": "180"})
        boards = [
            {"careers_url": "https://thirdchannel-inc.breezy.hr", "company": "Acme"},
            {"careers_url": "https://other.breezy.hr", "company": "Other"},
        ]
        calls = []
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_get", side_effect=lambda *a, **kw: calls.append(a[1]) or limited
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured Breezy boards failed"):
                radar.breezy_collect({"breezy_boards": boards})
            self.assertEqual(radar.source_state["breezy"]["rate_limit_retry_after_seconds"], 180.0)
            self.assertGreater(radar._source_cooldown_remaining("breezy"), 150)
        self.assertEqual(len(calls), 1)

    def test_detail_429_honours_retry_after_and_stops_remaining_boards(self):
        calls = []
        limited = FakeResponse(payload={}, status_code=429, headers={"Retry-After": "120"})
        def tracked(source, endpoint, **kwargs):
            calls.append(endpoint)
            if endpoint.endswith("/json"):
                tenant = endpoint.split("//", 1)[1].split(".", 1)[0]
                rows = copy.deepcopy(JOBS)
                for row in rows:
                    row["url"] = row["url"].replace("thirdchannel-inc", tenant)
                return FakeResponse(payload=rows)
            return limited
        with patch.object(radar, "source_state", {}), patch.object(radar, "_tracked_source_get", side_effect=tracked), patch.object(radar.time, "sleep"):
            rows = radar.breezy_collect({"breezy_boards": [
                {"careers_url": "https://thirdchannel-inc.breezy.hr", "company": "First"},
                {"careers_url": "https://secondco.breezy.hr", "company": "Second"},
            ]})
            self.assertGreater(radar._source_cooldown_remaining("breezy"), 100)
        feeds = [url for url in calls if url.endswith("/json")]
        details = [url for url in calls if not url.endswith("/json")]
        self.assertEqual(len(feeds), 1)
        self.assertEqual(len(details), 1)
        self.assertEqual(len(rows), 25)

    def test_default_off_migration_and_board_discovery_probe(self):
        base = radar._default_config()
        validated = radar.validate_config({
            **base, "breezy_boards": [{
                "careers_url": "https://thirdchannel-inc.breezy.hr", "company": "Acme", "registry_id": 7,
            }]
        })
        self.assertFalse(validated["source_enabled"]["breezy"])
        self.assertEqual(validated["poll_seconds"]["breezy"], 300)
        migrated = radar._merge_config(
            {"config_version": 16, "source_enabled": {"breezy": False}},
            {"config_version": 15, "source_enabled": {"breezy": True}},
        )
        self.assertFalse(migrated["source_enabled"]["breezy"])
        candidate = board_discovery.detect_ats_board("https://thirdchannel-inc.breezy.hr")
        self.assertEqual(candidate["provider"], "breezy")
        self.assertEqual(candidate["board_key"], "thirdchannel-inc")
        self.assertTrue(candidate["collector_available"])
        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(payload=JOBS)) as get:
            result = board_discovery.probe_public_board({
                "provider": "breezy", "board_url": "https://thirdchannel-inc.breezy.hr", "company": "Acme",
            })
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["jobs_observed"], 25)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])


class BreezyDiscoveryLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "qa.sqlite3"
        self.config = Path(self.tmp.name) / "config.json"
        self.db_patch = patch.object(radar, "DB_PATH", self.db)
        self.config_patch = patch.object(radar, "RUNTIME_CONFIG_PATH", self.config)
        self.db_patch.start()
        self.config_patch.start()
        with patch.object(radar, "DEFAULT_CONFIG_PATH", Path(radar.__file__).with_name("config.json")):
            radar.init_db()
        auth.create_user(self.db, "breezy-admin@example.com", "a sufficiently strong test password", role="admin")
        self.client = TestClient(radar.app, base_url="https://testserver")
        login = self.client.post("/api/auth/login", json={
            "email": "breezy-admin@example.com", "password": "a sufficiently strong test password",
        })
        self.assertEqual(login.status_code, 200)
        self.csrf = self.client.cookies.get("job_beeper_csrf")

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_discover_verify_activate_deactivate_is_explicit(self):
        fake = {
            "company_name": "Acme", "website_url": "https://acme.example/",
            "careers_url": "https://acme.example/", "pages_checked": 1,
            "discovery_status": "boards_found", "errors": [],
            "boards": [{
                "provider": "breezy", "board_key": "thirdchannel-inc",
                "board_url": "https://thirdchannel-inc.breezy.hr",
                "discovered_from": "https://acme.example/", "confidence": "high",
                "collector_source": "breezy", "collector_available": True,
            }],
        }
        with patch.object(radar.board_discovery, "discover_public_careers", return_value=fake):
            scan = self.client.post("/api/discovery/companies/scan",
                json={"company_name": "Acme", "website_url": "https://acme.example"},
                headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(scan.status_code, 200, scan.text)
        board_id = scan.json()["board_ids"][0]
        self.assertFalse(radar.get_config()["source_enabled"]["breezy"])
        with patch.object(board_discovery.requests, "get", return_value=FakeResponse(payload=JOBS)):
            verify = self.client.post(f"/api/discovery/boards/{board_id}/verify", headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(verify.status_code, 200, verify.text)
        self.assertFalse(verify.json()["scheduler_enabled"])
        activate = self.client.post(f"/api/discovery/boards/{board_id}/activate", headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(activate.status_code, 200, activate.text)
        self.assertTrue(activate.json()["source_enabled"])
        self.assertTrue(activate.json()["baseline_pending"])
        deactivate = self.client.post(f"/api/discovery/boards/{board_id}/deactivate", headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(deactivate.status_code, 200, deactivate.text)
        self.assertFalse(radar.get_config()["source_enabled"]["breezy"])
        self.assertEqual(radar.get_config()["breezy_boards"], [])


if __name__ == "__main__":
    unittest.main()
