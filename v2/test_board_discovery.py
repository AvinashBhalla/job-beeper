import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from v2 import auth, board_discovery, radar


class ATSBoardPatternTests(unittest.TestCase):
    def test_recognises_common_ats_board_links(self):
        examples = {
            "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite": ("workday", "nvidia:NVIDIAExternalCareerSite"),
            "https://boards.greenhouse.io/stripe": ("greenhouse", "stripe"),
            "https://job-boards.eu.greenhouse.io/example": ("greenhouse", "example"),
            "https://jobs.ashbyhq.com/posthog": ("ashby", "posthog"),
            "https://jobs.lever.co/palantir": ("lever", "palantir"),
            "https://jobs.eu.lever.co/palantir": ("lever", "palantir"),
            "https://jobs.smartrecruiters.com/BoschGroup": ("smartrecruiters", "BoschGroup"),
            "https://apply.workable.com/huggingface": ("workable", "huggingface"),
            "https://bunq.recruitee.com": ("recruitee", "bunq"),
            "https://breezy.breezy.hr": ("breezy", "breezy"),
            "https://career.teamtailor.com": ("teamtailor", "career"),
            "https://acme.bamboohr.com/careers": ("bamboohr", "acme"),
            "https://ats.rippling.com/rippling/jobs": ("rippling", "rippling"),
            "https://personio.jobs.personio.de": ("personio", "personio"),
        }
        for url, expected in examples.items():
            with self.subTest(url=url):
                detected = board_discovery.detect_ats_board(url)
                self.assertIsNotNone(detected)
                self.assertEqual((detected["provider"], detected["board_key"]), expected)

    def test_rejects_malformed_and_non_https_board_urls(self):
        for url in (
            "http://boards.greenhouse.io/stripe",
            "https://user@boards.greenhouse.io/stripe",
            "https://boards.greenhouse.io/",
            "https://nvidia.wd5.myworkdayjobs.com/en-US/",
            "https://evil.example/jobs",
        ):
            with self.subTest(url=url):
                self.assertIsNone(board_discovery.detect_ats_board(url))

    def test_direct_ats_careers_url_is_registered_even_without_outbound_link(self):
        board_url = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        html = "<html><body>Public career portal</body></html>"
        with patch.object(board_discovery, "_public_https_url", side_effect=lambda value: value), patch.object(
            board_discovery, "_safe_fetch", return_value=(board_url, html)
        ):
            result = board_discovery.discover_public_careers(
                "NVIDIA", "https://nvidia.com", board_url
            )
        self.assertEqual(len(result["boards"]), 1)
        self.assertEqual(result["boards"][0]["provider"], "workday")

    def test_workday_candidate_contains_derived_tenant_cluster_and_site(self):
        candidate = board_discovery.detect_ats_board(
            "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        )
        self.assertEqual(candidate["tenant"], "nvidia")
        self.assertEqual(candidate["cluster"], "5")
        self.assertEqual(candidate["site"], "NVIDIAExternalCareerSite")

    def test_public_url_guard_rejects_internal_ip_and_non_https(self):
        with self.assertRaises(ValueError):
            board_discovery._public_https_url("http://example.com/careers")
        with self.assertRaises(ValueError):
            board_discovery._public_https_url("https://127.0.0.1/careers")
        with patch.object(board_discovery.socket, "getaddrinfo", return_value=[
            (2, 1, 6, "", ("10.1.2.3", 443))
        ]):
            with self.assertRaisesRegex(ValueError, "private or reserved"):
                board_discovery._public_https_url("https://private.example/careers")

    def test_discovery_follows_company_careers_link_and_detects_multiple_boards(self):
        homepage = '''<html><body>
          <a href="/careers">Careers</a>
          <a href="https://boards.greenhouse.io/acme">Open roles</a>
        </body></html>'''
        careers = '''<html><body>
          <a href="https://acme.wd5.myworkdayjobs.com/en-US/ExternalJobs">Global careers</a>
          <script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting","title":"Engineer"}</script>
        </body></html>'''
        def fetch(url):
            if url.endswith("/careers"):
                return url, careers
            return url, homepage
        with patch.object(board_discovery, "_public_https_url", side_effect=lambda value: value.rstrip("/") if value.endswith("/") else value), patch.object(
            board_discovery, "_safe_fetch", side_effect=fetch
        ):
            result = board_discovery.discover_public_careers(
                "Acme", "https://acme.example", "https://acme.example/careers"
            )
        self.assertEqual(result["pages_checked"], 2)
        providers = {item["provider"] for item in result["boards"]}
        self.assertEqual(providers, {"greenhouse", "workday", "jobposting_jsonld"})
        self.assertEqual(result["discovery_status"], "boards_found")


class BoardDiscoveryApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "discovery.sqlite3"
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.config_patch = patch.object(radar, "RUNTIME_CONFIG_PATH", self.config_path)
        self.db_patch.start()
        self.config_patch.start()
        with patch.object(radar, "DEFAULT_CONFIG_PATH", Path(radar.__file__).with_name("config.json")):
            radar.init_db()
        auth.create_user(self.db_path, "discovery-admin@example.com", "a sufficiently strong test password", role="admin")
        self.client = TestClient(radar.app, base_url="https://testserver")
        login = self.client.post("/api/auth/login", json={
            "email": "discovery-admin@example.com",
            "password": "a sufficiently strong test password",
        })
        self.assertEqual(login.status_code, 200)
        self.csrf = self.client.cookies.get("job_beeper_csrf")

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_admin_can_scan_and_review_discovered_board_without_enabling_source(self):
        fake_result = {
            "company_name": "Acme", "website_url": "https://acme.example/",
            "careers_url": "https://acme.example/", "pages_checked": 1,
            "discovery_status": "boards_found", "errors": [],
            "boards": [{
                "provider": "greenhouse", "board_key": "acme",
                "board_url": "https://boards.greenhouse.io/acme",
                "discovered_from": "https://acme.example/", "confidence": "high",
                "collector_source": "greenhouse", "collector_available": True,
            }],
        }
        with patch.object(radar.board_discovery, "discover_public_careers", return_value=fake_result):
            response = self.client.post("/api/discovery/companies/scan", json={
                "company_name": "Acme", "website_url": "https://acme.example",
            }, headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(response.status_code, 200, response.text)
        board_id = response.json()["board_ids"][0]
        self.assertEqual(self.client.get("/api/discovery/companies").json()["companies"][0]["board_count"], 1)
        board = self.client.get("/api/discovery/boards").json()["boards"][0]
        self.assertEqual(board["provider"], "greenhouse")
        reviewed = self.client.post(
            f"/api/discovery/boards/{board_id}/review", json={"status": "reviewed"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["review_status"], "reviewed")
        self.assertFalse(radar.get_config()["source_enabled"]["greenhouse"])

    def test_verify_board_persists_status_but_does_not_enable_source(self):
        fake_result = {
            "company_name": "Acme", "website_url": "https://acme.example/",
            "careers_url": "https://acme.example/", "pages_checked": 1,
            "discovery_status": "boards_found", "errors": [],
            "boards": [{
                "provider": "greenhouse", "board_key": "acme",
                "board_url": "https://boards.greenhouse.io/acme",
                "discovered_from": "https://acme.example/", "confidence": "high",
                "collector_source": "greenhouse", "collector_available": True,
            }],
        }
        with patch.object(radar.board_discovery, "discover_public_careers", return_value=fake_result):
            scanned = self.client.post("/api/discovery/companies/scan", json={
                "company_name": "Acme", "website_url": "https://acme.example",
            }, headers={"X-CSRF-Token": self.csrf})
        board_id = scanned.json()["board_ids"][0]
        with patch.object(radar.board_discovery, "probe_public_board", return_value={
            "provider": "greenhouse", "verified": True, "http_status": 200,
            "jobs_observed": 12, "verification_method": "public_board_endpoint_probe",
        }):
            verified = self.client.post(
                f"/api/discovery/boards/{board_id}/verify",
                headers={"X-CSRF-Token": self.csrf},
            )
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertEqual(verified.json()["jobs_observed"], 12)
        self.assertFalse(verified.json()["scheduler_enabled"])
        board = self.client.get("/api/discovery/boards?status=verified").json()["boards"][0]
        self.assertEqual(board["review_status"], "verified")
        self.assertFalse(radar.get_config()["source_enabled"]["greenhouse"])

    def _insert_verified_greenhouse_board(self):
        timestamp = radar.iso(radar.now())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT INTO employer_companies
                (company_name,domain,website_url,careers_url,discovery_status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)""",
                ("Acme", "acme.example", "https://acme.example/", "https://acme.example/careers", "boards_found", timestamp, timestamp))
            company_id = conn.execute("SELECT id FROM employer_companies WHERE domain='acme.example'").fetchone()[0]
            conn.execute("""INSERT INTO ats_board_registry
                (company_id,provider,board_key,board_url,discovered_from,confidence,collector_source,collector_available,review_status,last_verified_at,last_seen_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,1,'verified',?,?,?,?)""",
                (company_id, "greenhouse", "acme", "https://boards.greenhouse.io/acme", "https://acme.example/careers", "high", "greenhouse", timestamp, timestamp, timestamp, timestamp))
            board_id = conn.execute("SELECT id FROM ats_board_registry WHERE company_id=?", (company_id,)).fetchone()[0]
            conn.commit()
        return board_id

    def test_verified_board_activation_enables_only_its_collector_and_sets_baseline(self):
        board_id = self._insert_verified_greenhouse_board()
        with patch.object(radar, "refresh_job_evaluations"), patch.object(radar, "refresh_notification_decisions"), patch.object(radar, "refresh_configured_user_evaluations"):
            response = self.client.post(
                f"/api/discovery/boards/{board_id}/activate",
                headers={"X-CSRF-Token": self.csrf},
            )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["collector_source"], "greenhouse")
        self.assertTrue(result["source_enabled"])
        self.assertTrue(result["baseline_pending"])
        config = radar.get_config()
        self.assertTrue(config["source_enabled"]["greenhouse"])
        self.assertIn({"token": "acme", "company": "Acme", "registry_id": board_id}, config["greenhouse_boards"])
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT review_status,baseline_pending FROM ats_board_registry WHERE id=?", (board_id,)).fetchone()
        self.assertEqual(row, ("active", 1))

    def test_activation_links_preconfigured_greenhouse_board_without_duplicate(self):
        board_id = self._insert_verified_greenhouse_board()
        config = radar._default_config()
        config["greenhouse_boards"] = [{"token": "acme", "company": "Acme"}]
        with patch.object(radar, "get_config", return_value=config), patch.object(
            radar, "save_config", side_effect=lambda value: value
        ), patch.object(radar, "refresh_job_evaluations"), patch.object(
            radar, "refresh_notification_decisions"
        ), patch.object(radar, "refresh_configured_user_evaluations"):
            response = self.client.post(
                f"/api/discovery/boards/{board_id}/activate",
                headers={"X-CSRF-Token": self.csrf},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(config["greenhouse_boards"]), 1)
        self.assertEqual(config["greenhouse_boards"][0]["registry_id"], board_id)
        self.assertTrue(config["source_enabled"]["greenhouse"])

    def test_verified_keka_board_activation_maps_registry_to_public_careers_url(self):
        timestamp = radar.iso(radar.now())
        careers_url = "https://bridgestone1.keka.com/careers"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT INTO employer_companies
                (company_name,domain,website_url,careers_url,discovery_status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)""",
                ("Bridgestone", "bridgestone.example", "https://bridgestone.com/", careers_url, "boards_found", timestamp, timestamp))
            company_id = conn.execute("SELECT id FROM employer_companies WHERE domain='bridgestone.example'").fetchone()[0]
            conn.execute("""INSERT INTO ats_board_registry
                (company_id,provider,board_key,board_url,discovered_from,confidence,collector_source,collector_available,review_status,last_verified_at,last_seen_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,1,'verified',?,?,?,?)""",
                (company_id, "keka", "bridgestone1", careers_url, careers_url, "high", "keka", timestamp, timestamp, timestamp, timestamp))
            board_id = conn.execute("SELECT id FROM ats_board_registry WHERE company_id=?", (company_id,)).fetchone()[0]
            conn.commit()
        with patch.object(radar, "refresh_job_evaluations"), patch.object(radar, "refresh_notification_decisions"), patch.object(radar, "refresh_configured_user_evaluations"):
            response = self.client.post(
                f"/api/discovery/boards/{board_id}/activate",
                headers={"X-CSRF-Token": self.csrf},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["collector_source"], "keka")
        self.assertTrue(response.json()["baseline_pending"])
        config = radar.get_config()
        self.assertTrue(config["source_enabled"]["keka"])
        self.assertIn({"careers_url": careers_url, "company": "Bridgestone", "registry_id": board_id}, config["keka_boards"])

    def test_unverified_board_cannot_be_activated(self):
        board_id = self._insert_verified_greenhouse_board()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE ats_board_registry SET review_status='discovered' WHERE id=?", (board_id,))
        response = self.client.post(
            f"/api/discovery/boards/{board_id}/activate",
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(radar.get_config()["source_enabled"]["greenhouse"])

    def test_new_board_baseline_suppresses_only_jobs_attached_to_that_registry_row(self):
        board_id = self._insert_verified_greenhouse_board()
        timestamp = radar.iso(radar.now())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE ats_board_registry SET review_status='active',baseline_pending=1 WHERE id=?", (board_id,))
            conn.execute("""INSERT INTO canonical_opportunities
                (company_norm,title_norm,location_norm,representative_job_id,first_seen_at,last_seen_at)
                VALUES('acme','engineer','remote',1,?,?)""", (timestamp,timestamp))
            canonical_id = conn.execute("SELECT id FROM canonical_opportunities ORDER BY id DESC LIMIT 1").fetchone()[0]
            conn.execute("""INSERT INTO jobs
                (source,source_job_id,company,title,location,url,posted_precision,discovered_at,source_details_json,first_seen_at,last_seen_at,canonical_opportunity_id)
                VALUES('greenhouse','gh-acme-1','Acme','Engineer','Remote','https://boards.greenhouse.io/acme/1','unknown',?,?,?,?,?)""",
                (timestamp, json.dumps({"board_registry_id": board_id}), timestamp, timestamp, canonical_id))
            conn.execute("""INSERT INTO notification_ledger
                (canonical_opportunity_id,status,candidate_job_id,created_at,updated_at)
                VALUES(?,'queued',1,?,?)""", (canonical_id,timestamp,timestamp))
            conn.commit()
        suppressed = radar.suppress_activated_board_inventory("greenhouse")
        self.assertEqual(suppressed, 1)
        with sqlite3.connect(self.db_path) as conn:
            job = conn.execute("SELECT source_initial_baseline FROM jobs WHERE source_job_id='gh-acme-1'").fetchone()
            ledger = conn.execute("SELECT status,baseline_suppressed,candidate_job_id FROM notification_ledger WHERE canonical_opportunity_id=?", (canonical_id,)).fetchone()
            baseline_pending = conn.execute("SELECT baseline_pending FROM ats_board_registry WHERE id=?", (board_id,)).fetchone()[0]
        self.assertEqual(job[0], 1)
        self.assertEqual(ledger, ("suppressed", 1, None))
        self.assertEqual(baseline_pending, 0)

    def test_discovery_post_requires_csrf(self):
        denied = self.client.post("/api/discovery/companies/scan", json={
            "company_name": "Acme", "website_url": "https://acme.example",
        })
        self.assertEqual(denied.status_code, 403)

    def test_discovery_routes_are_admin_only_and_post_requires_csrf(self):
        self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.csrf})
        anonymous = self.client.get("/api/discovery/boards")
        self.assertEqual(anonymous.status_code, 401)

        # The other authenticated role cannot inspect or mutate the admin registry.
        auth.create_user(self.db_path, "discovery-user@example.com", "another sufficiently strong password")
        user = self.client.post("/api/auth/login", json={
            "email": "discovery-user@example.com",
            "password": "another sufficiently strong password",
        })
        self.assertEqual(user.status_code, 200)
        self.assertEqual(self.client.get("/api/discovery/boards").status_code, 403)


class PublicATSCollectorTests(unittest.TestCase):
    class Response:
        status_code = 200
        headers = {}
        def __init__(self, payload, status_code=200, headers=None):
            self.payload = payload
            self.status_code = status_code
            self.headers = headers or {}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise board_discovery.requests.HTTPError(
                    f"HTTP {self.status_code}", response=self
                )
        def json(self):
            return self.payload

    def test_smartrecruiters_maps_public_listing_and_detail(self):
        listings = {
            "totalFound": 2,
            "content": [
                {
                    "id": "REQ-100", "name": "Python Engineer",
                    "releasedDate": "2026-11-08T10:20:30.000Z",
                    "postingUrl": "https://jobs.smartrecruiters.com/Acme/REQ-100-python-engineer",
                    "location": {"city": "Bengaluru", "region": "Karnataka", "country": "in", "remote": True},
                    "company": {"name": "Acme"}, "function": {"label": "Engineering"},
                    "typeOfEmployment": {"label": "Full-time"},
                    "experienceLevel": {"label": "Associate"},
                    "refNumber": "A-100",
                },
                {
                    "id": "REQ-101", "name": "Backend Developer",
                    "releasedDate": "2026-11-07T09:00:00.000Z",
                    "location": {"fullLocation": "Remote, India"},
                    "company": {"name": "Acme"},
                },
            ],
        }
        detail = {"jobAd": {"sections": {
            "jobDescription": {"text": "<p>Build Python services.</p>"},
            "qualifications": {"text": "<ul><li>FastAPI</li></ul>"},
        }}, "postingUrl": "https://jobs.smartrecruiters.com/Acme/REQ-100-python-engineer"}
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            if endpoint.endswith("/postings"):
                return self.Response(listings)
            return self.Response(detail)
        with patch.object(radar, "_tracked_source_get", side_effect=tracked), patch.object(radar.time, "sleep"):
            jobs = radar.smartrecruiters_collect({
                "smartrecruiters_boards": [{"company_identifier": "Acme", "company": "Acme", "registry_id": 27}],
            })
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first["source_job_id"], "smartrecruiters-Acme-REQ-100")
        self.assertEqual(first["posted_precision"], "minute")
        self.assertEqual(first["source_details"]["board_registry_id"], 27)
        self.assertIn("Build Python services", first["description"])
        self.assertIn("FastAPI", first["description"])
        self.assertTrue(first["source_details"]["details_fetched"])
        self.assertEqual(calls[0][2]["params"]["destination"], "PUBLIC")
        self.assertEqual(calls[0][2]["params"]["limit"], 100)
        self.assertEqual(len(calls), 3)

    def test_smartrecruiters_429_honours_retry_after(self):
        limited = self.Response({}, 429, {"Retry-After": "90"})
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_get", return_value=limited
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured SmartRecruiters boards failed"):
                radar.smartrecruiters_collect({
                    "smartrecruiters_boards": [{"company_identifier": "Acme", "company": "Acme"}],
                })
            self.assertEqual(radar.source_state["smartrecruiters"]["rate_limit_retry_after_seconds"], 90.0)
            self.assertGreater(radar._source_cooldown_remaining("smartrecruiters"), 80)

    def test_workable_maps_full_public_widget(self):
        payload = {
            "name": "Acme",
            "jobs": [
                {
                    "title": "Python Engineer", "shortcode": "ABC123",
                    "employment_type": "Full-time", "telecommuting": True,
                    "department": "Engineering", "function": "Engineering",
                    "url": "https://apply.workable.com/j/ABC123",
                    "published_on": "2026-11-08", "created_at": "2026-11-08",
                    "country": "India", "city": "Bengaluru", "state": "Karnataka",
                    "locations": [{"country": "India", "city": "Bengaluru", "region": "Karnataka"}],
                    "description": "<h2>Role</h2><p>Build Python APIs.</p>",
                },
                {
                    "title": "Backend Developer", "shortcode": "DEF456",
                    "employment_type": "Contract", "telecommuting": False,
                    "url": "https://apply.workable.com/j/DEF456",
                    "published_on": "2026-11-07", "description": "<p>Build backend services.</p>",
                },
            ],
        }
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            return self.Response(payload)
        with patch.object(radar, "_tracked_source_get", side_effect=tracked):
            jobs = radar.workable_collect({
                "workable_boards": [{"account": "acme", "company": "Acme", "registry_id": 41}],
            })
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first["source_job_id"], "workable-acme-ABC123")
        self.assertEqual(first["posted_precision"], "date")
        self.assertEqual(first["source_details"]["board_registry_id"], 41)
        self.assertIn("Build Python APIs", first["description"])
        self.assertIn("Remote", first["location"])
        self.assertTrue(first["source_details"]["details_fetched"])
        self.assertEqual(calls[0][2]["params"], {"details": "true"})

    def test_new_sources_are_opt_in_and_config_arrays_are_validated(self):
        base = radar._default_config()
        validated = radar.validate_config({
            **base,
            "smartrecruiters_boards": [{"company_identifier": "Acme", "company": "Acme", "registry_id": 1}],
            "workable_boards": [{"account": "acme", "company": "Acme", "registry_id": 2}],
        })
        self.assertFalse(validated["source_enabled"]["smartrecruiters"])
        self.assertFalse(validated["source_enabled"]["workable"])
        self.assertEqual(validated["smartrecruiters_boards"][0]["registry_id"], 1)
        self.assertEqual(validated["workable_boards"][0]["registry_id"], 2)
        with self.assertRaises(radar.HTTPException):
            radar.validate_config({**base, "source_enabled": {"workable": True}})
        migrated = radar._merge_config(
            {"config_version": 14, "source_enabled": {"smartrecruiters": False, "workable": False}},
            {"config_version": 13, "source_enabled": {"smartrecruiters": True, "workable": True}},
        )
        self.assertFalse(migrated["source_enabled"]["smartrecruiters"])
        self.assertFalse(migrated["source_enabled"]["workable"])

    def test_discovery_verification_probes_smartrecruiters_and_workable(self):
        with patch.object(board_discovery.requests, "get", return_value=self.Response({"content": [{"id": 1}]})):
            result = board_discovery.probe_public_board({
                "provider": "smartrecruiters", "board_url": "https://jobs.smartrecruiters.com/Acme",
            })
        self.assertEqual(result["jobs_observed"], 1)
        with patch.object(board_discovery.requests, "get", return_value=self.Response({"jobs": [{"shortcode": "1"}]})):
            result = board_discovery.probe_public_board({
                "provider": "workable", "board_url": "https://apply.workable.com/acme",
            })
        self.assertEqual(result["jobs_observed"], 1)


if __name__ == "__main__":
    unittest.main()


class KekaDarwinboxCollectorTests(unittest.TestCase):
    class Response(PublicATSCollectorTests.Response):
        def __init__(self, payload=None, status_code=200, headers=None, text=None):
            super().__init__(payload, status_code, headers)
            self.text = text if text is not None else ""
            self.content = self.text.encode("utf-8") if text is not None else json.dumps(payload).encode("utf-8")

    def test_discovery_recognises_keka_and_darwinbox_board_paths(self):
        keka = board_discovery.detect_ats_board("https://bridgestone1.keka.com/careers")
        self.assertEqual((keka["provider"], keka["board_key"]), ("keka", "bridgestone1"))
        darwin = board_discovery.detect_ats_board(
            "https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/a6a67448e9a280"
        )
        self.assertEqual((darwin["provider"], darwin["board_key"]), ("darwinbox", "main"))
        self.assertIsNone(board_discovery.detect_ats_board(
            "https://jgsummit.darwinbox.com/ms/candidatev2/a6373b98b30596/careers/allJobs"
        ))

    def test_keka_maps_public_embed_feed_with_stable_ids_and_publication_time(self):
        careers_html = '''<html><body>
          <script src="/ats/documents/af8a241d-4ca4-4c8e-8e85-df4ccf00ea56/careerportal/main.js"></script>
        </body></html>'''
        payload = [
            {
                "id": 94681, "title": "Process Excellence Manager",
                "publishedOn": "2026-11-04T10:34:15.250Z", "publishedSinceDays": 4,
                "description": "<div><strong>Lead operations</strong> and build Python services.</div>",
                "excerpt": "Lead operations", "experience": "7+ Years",
                "departmentIdentifier": "dept-1", "departmentName": "Engineering",
                "jobLocations": [{"id": 13171, "name": "Bengaluru, Karnataka", "countryCode": "IN", "countryName": "India"}],
                "jobNumber": "KEK-94681", "jobType": 2,
                "salaryRange": {"currency": "INR", "salaryPeriod": 0},
                "salaryRangeFormat": "", "skillNames": ["Python"],
            },
            {
                "id": 94682, "title": "Backend Developer", "publishedOn": "2026-11-03T08:00:00Z",
                "description": "<p>Build platform services.</p>",
                "jobLocations": [{"city": "Pune", "state": "MH", "countryName": "India"}],
            },
        ]
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            if endpoint.endswith("/careers"):
                return self.Response(text=careers_html, headers={"Content-Type": "text/html"})
            return self.Response(payload, headers={"Content-Type": "application/json"})
        with patch.object(radar, "_tracked_source_get", side_effect=tracked):
            jobs = radar.keka_collect({
                "keka_boards": [{
                    "careers_url": "https://bridgestone1.keka.com/careers",
                    "company": "Bridgestone",
                    "registry_id": 72,
                }]
            })
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first["source_job_id"], "keka-bridgestone1-94681")
        self.assertEqual(first["posted_precision"], "minute")
        self.assertEqual(first["source_details"]["board_registry_id"], 72)
        self.assertEqual(first["location"], "Bengaluru, Karnataka")
        self.assertEqual(first["url"], "https://bridgestone1.keka.com/careers/jobdetails/94681")
        self.assertIn("Python services", first["description"])
        self.assertEqual(len(calls), 2)
        self.assertFalse(calls[0][2]["allow_redirects"])
        self.assertFalse(calls[1][2]["allow_redirects"])

    def test_keka_rejects_feed_missing_from_careers_page(self):
        html = "<html><body>Careers page without public feed</body></html>"
        with patch.object(radar, "_tracked_source_get", return_value=self.Response(text=html)):
            with self.assertRaisesRegex(RuntimeError, "All configured Keka boards failed"):
                radar.keka_collect({
                    "keka_boards": [{
                        "careers_url": "https://bridgestone1.keka.com/careers",
                        "company": "Bridgestone",
                    }]
                })

    def test_keka_429_persists_source_cooldown(self):
        limited = self.Response({}, 429, {"Retry-After": "120"})
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_get", return_value=limited
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured Keka boards failed"):
                radar.keka_collect({
                    "keka_boards": [{
                        "careers_url": "https://bridgestone1.keka.com/careers",
                        "company": "Bridgestone",
                    }]
                })
            self.assertEqual(radar.source_state["keka"]["rate_limit_retry_after_seconds"], 120.0)
            self.assertGreater(radar._source_cooldown_remaining("keka"), 100)

    def test_darwinbox_maps_public_candidate_endpoint_response(self):
        payload = {
            "status": "success", "job_counts": 2,
            "data": [
                {
                    "id": 501, "title": "Python Engineer", "posted_on": 1793788455,
                    "internal_job_code": "DB-501", "locations": "Bengaluru",
                    "tool_tip_locations": ["Bengaluru, India"],
                    "jd": "<p>Build Python APIs.</p>", "experience": "3+ Years",
                },
                {
                    "id": 502, "title": "Backend Engineer",
                    "created_on": "2026-11-07T10:00:00Z",
                    "locations": "Remote", "jd": "<p>Build backend services.</p>",
                },
            ],
        }
        calls = []
        def tracked(source, endpoint, **kwargs):
            calls.append((source, endpoint, kwargs))
            return self.Response(payload)
        board = "https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/a6a67448e9a280"
        with patch.object(radar, "_tracked_source_post", side_effect=tracked):
            jobs = radar.darwinbox_collect({
                "darwinbox_boards": [{
                    "careers_url": board, "company": "J G Summit", "registry_id": 91,
                }]
            })
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first["source_job_id"], "darwinbox-arvind-main-501")
        self.assertEqual(first["posted_precision"], "minute")
        self.assertEqual(first["source_details"]["board_registry_id"], 91)
        self.assertIn("Python APIs", first["description"])
        self.assertEqual(first["url"], "https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/501")
        self.assertEqual(calls[0][2]["json_body"]["limit"], 50)
        self.assertFalse(calls[0][2]["allow_redirects"])

    def test_darwinbox_403_is_not_misclassified_as_rate_limit(self):
        denied = self.Response({}, 403)
        with patch.object(radar, "source_state", {}), patch.object(
            radar, "_tracked_source_post", return_value=denied
        ):
            with self.assertRaisesRegex(RuntimeError, "All configured Darwinbox boards failed"):
                radar.darwinbox_collect({
                    "darwinbox_boards": [{
                        "careers_url": "https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/a6a67448e9a280",
                        "company": "J G Summit",
                    }]
                })
            self.assertEqual(radar._source_cooldown_remaining("darwinbox"), 0)

    def test_discovery_probe_uses_keka_feed_and_darwinbox_candidate_endpoint(self):
        board = "https://bridgestone1.keka.com/careers"
        html = '<script src="/ats/documents/af8a241d-4ca4-4c8e-8e85-df4ccf00ea56/careerportal/main.js"></script>'
        with patch.object(board_discovery, "_safe_fetch", return_value=(board, html)), patch.object(
            board_discovery.requests, "get", return_value=self.Response([{"id": 1}])
        ):
            result = board_discovery.probe_public_board({"provider": "keka", "board_url": board})
        self.assertEqual(result["jobs_observed"], 1)

        darwin = "https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/a6a67448e9a280"
        with patch.object(
            board_discovery.requests, "post",
            return_value=self.Response({"status": "success", "data": [{"id": 1}]}),
        ) as darwin_post:
            result = board_discovery.probe_public_board({"provider": "darwinbox", "board_url": darwin})
        self.assertEqual(result["jobs_observed"], 1)
        self.assertEqual(darwin_post.call_args.kwargs["headers"]["Referer"], darwin)

    def test_new_connectors_are_opt_in_and_config_migration_disables_them(self):
        base = radar._default_config()
        config = radar.validate_config({
            **base,
            "keka_boards": [{
                "careers_url": "https://bridgestone1.keka.com/careers",
                "company": "Bridgestone", "registry_id": 72,
            }],
            "darwinbox_boards": [{
                "careers_url": "https://arvind.darwinbox.in/ms/candidatev2/main/careers/jobDetails/a6a67448e9a280",
                "company": "J G Summit", "registry_id": 91,
            }],
        })
        self.assertFalse(config["source_enabled"]["keka"])
        self.assertFalse(config["source_enabled"]["darwinbox"])
        self.assertEqual(config["keka_boards"][0]["registry_id"], 72)
        self.assertEqual(config["darwinbox_boards"][0]["registry_id"], 91)
        with self.assertRaises(radar.HTTPException):
            radar.validate_config({**base, "source_enabled": {"darwinbox": True}})
        migrated = radar._merge_config(
            {"config_version": 15, "source_enabled": {"keka": False, "darwinbox": False}},
            {"config_version": 14, "source_enabled": {"keka": True, "darwinbox": True}},
        )
        self.assertFalse(migrated["source_enabled"]["keka"])
        self.assertFalse(migrated["source_enabled"]["darwinbox"])

    def test_keka_career_page_redirect_cannot_change_host(self):
        redirect = self.Response({}, 302, {"Location": "https://attacker.example/careers"})
        with patch.object(radar, "_tracked_source_get", return_value=redirect), patch.object(
            radar.board_discovery, "_public_https_url", side_effect=lambda value: value
        ):
            with self.assertRaisesRegex(ValueError, "different host"):
                radar._keka_fetch_careers_page("keka", "https://bridgestone1.keka.com/careers")
