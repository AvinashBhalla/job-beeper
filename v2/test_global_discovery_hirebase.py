from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from fastapi.testclient import TestClient

from v2 import ats_directory, auth, hirebase, radar


class HirebaseLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "jobs.sqlite3"
        self.db_patch = patch.object(radar, "DB_PATH", self.db)
        self.db_patch.start()
        with patch.object(radar, "DEFAULT_CONFIG_PATH", Path(radar.__file__).with_name("config.json")):
            radar.init_db()
        self.usage = {
            "subscription_status": "active",
            "period_start": "2026-11-01T00:00:00Z",
            "period_end": "2026-12-01T00:00:00Z",
            "used": 0, "included": 500, "remaining": 500,
        }

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_reservation_enforces_monthly_daily_and_provider_caps(self):
        reservation = radar._hirebase_reserve("workday", 4, self.usage)
        self.assertIsNotNone(reservation)
        self.assertIsNone(radar._hirebase_reserve("workday", 1, self.usage))
        second = radar._hirebase_reserve("keka", 4, self.usage)
        third = radar._hirebase_reserve("darwinbox", 4, self.usage)
        self.assertIsNotNone(second)
        self.assertIsNotNone(third)
        self.assertIsNone(radar._hirebase_reserve("workday", 1, self.usage))

    def test_monthly_cap_keeps_one_hundred_credit_safety_buffer(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """INSERT INTO hirebase_usage_ledger
                   (provider,created_at,period_start,period_end,estimated_jobs,returned_jobs,
                    reserved_jobs,status,included_used,included_remaining,response_verified)
                   VALUES(?,?,?,?,?,NULL,?,'reserved',NULL,NULL,0)""",
                ("workday", radar.iso(radar.now()), self.usage["period_start"],
                 self.usage["period_end"], 400, 400),
            )
        self.assertIsNone(radar._hirebase_reserve("keka", 1, self.usage))

    def test_unknown_search_outcome_retains_full_reservation(self):
        reservation = radar._hirebase_reserve("workday", 4, self.usage)
        radar._hirebase_finish_reservation(
            reservation, jobs_returned=None, usage_headers=None, uncertain=True
        )
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT status,reserved_jobs,returned_jobs FROM hirebase_usage_ledger WHERE id=?",
                (reservation,),
            ).fetchone()
        self.assertEqual(row, ("unknown", 4, None))
        self.assertIsNone(radar._hirebase_reserve("workday", 1, self.usage))

    def test_verified_search_replaces_estimate_with_actual_return_count(self):
        reservation = radar._hirebase_reserve("workday", 4, self.usage)
        radar._hirebase_finish_reservation(
            reservation, jobs_returned=3,
            usage_headers={"included_used": 3, "included_remaining": 497},
        )
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT status,reserved_jobs,returned_jobs,included_remaining,response_verified "
                "FROM hirebase_usage_ledger WHERE id=?", (reservation,)
            ).fetchone()
        self.assertEqual(row, ("complete", 0, 3, 497, 1))

    def test_hirebase_collector_estimates_before_search_and_stores_normalized_jobs(self):
        item = {
            "_id": "job-1", "company_name": "Example", "job_title": "Python Engineer",
            "application_link": "https://jobs.example.com/apply/1", "job_board": "workday",
            "location_raw": "Bengaluru", "locations": [
                {"city": "Bengaluru", "region": "Karnataka", "country": "India"}
            ], "date_posted": "2026-11-09T12:00:00Z",
            "first_ingested": "2026-11-09T12:05:00Z", "description": "Python services",
        }
        radar._hirebase_set_window(
            "workday", last_polled_at="2026-11-09T10:00:00+00:00",
            window_start="2026-11-09T08:00:00+00:00", next_page=3,
        )
        calls = []
        state = {}

        def estimate(payload, requester=None):
            calls.append(("estimate", payload["job_board"][0], dict(payload)))
            return 1 if payload["job_board"] == ["workday"] else 0

        def search(payload, requester=None):
            calls.append(("search", payload["job_board"][0], dict(payload)))
            self.assertEqual(payload["limit"], 4)  # fixed page size preserves page boundaries
            return [item], {"included_used": 1, "included_remaining": 499}, {
                "page": 3, "total_pages": 5, "total_count": 18,
            }

        with patch.object(hirebase, "api_key_configured", return_value=True), \
             patch.object(hirebase, "usage_summary", return_value=dict(self.usage)), \
             patch.object(hirebase, "estimate", side_effect=estimate), \
             patch.object(hirebase, "search", side_effect=search), \
             patch.object(radar, "source_state", state), \
             patch.object(radar, "_record_source_page"), \
             patch.object(radar, "_record_source_board"):
            jobs = radar.hirebase_collect({})
            watermark = calls[0][2]
            self.assertEqual(watermark["ingested_after"], "2026-11-09T08:00:00+00:00")
            self.assertEqual(watermark["page"], 3)
            self.assertNotIn("days_ago", watermark)
            self.assertEqual(watermark["sort_by"], "first_ingested")
            self.assertEqual(watermark["sort_order"], "asc")
            self.assertIn("pending_watermarks", state["hirebase"])
            # Cursor is committed only after the caller has persisted/upserted jobs.
            radar._hirebase_commit_pending_watermarks()

        self.assertEqual([x[0] for x in calls], ["estimate", "search", "estimate", "estimate"])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["source"], "hirebase")
        self.assertEqual(jobs[0]["source_job_id"], "workday:job-1")
        self.assertEqual(jobs[0]["company"], "Example")
        self.assertEqual(jobs[0]["source_details"]["first_ingested"], "2026-11-09T12:05:00Z")
        stored = radar._hirebase_get_window("workday")
        self.assertEqual(stored["next_page"], 4)
        self.assertEqual(stored["window_start"], "2026-11-09T08:00:00+00:00")
        self.assertNotEqual(stored["last_polled_at"], "2026-11-09T10:00:00+00:00")
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT provider,estimated_jobs,returned_jobs,status FROM hirebase_usage_ledger"
            ).fetchone()
        self.assertEqual(row, ("workday", 1, 1, "complete"))

    def test_zero_estimate_advances_provider_watermark_without_metered_search(self):
        calls = []
        with patch.object(hirebase, "api_key_configured", return_value=True), \
             patch.object(hirebase, "usage_summary", return_value=dict(self.usage)), \
             patch.object(hirebase, "estimate", side_effect=lambda payload, requester=None: calls.append(payload["job_board"][0]) or 0), \
             patch.object(hirebase, "search", side_effect=AssertionError("search must not run for zero estimate")), \
             patch.object(radar, "source_state", {}), \
             patch.object(radar, "_record_source_page"), \
             patch.object(radar, "_record_source_board"):
            jobs = radar.hirebase_collect({})
        self.assertEqual(jobs, [])
        self.assertEqual(calls, ["workday", "keka", "darwinbox"])
        for provider in ("workday", "keka", "darwinbox"):
            cursor = radar._hirebase_get_window(provider)
            self.assertIsNotNone(cursor)
            self.assertEqual(cursor["next_page"], 1)

    def test_collector_stops_all_provider_searches_after_429(self):
        response = Mock(status_code=429, headers={"Retry-After": "300"})
        response.status_code = 429
        exc = hirebase.HirebaseError("Hirebase request rate limit reached.", response=response)
        calls = []
        def estimate(payload, requester=None):
            calls.append(payload["job_board"][0])
            return 1
        with patch.object(hirebase, "api_key_configured", return_value=True),              patch.object(hirebase, "usage_summary", return_value=dict(self.usage)),              patch.object(hirebase, "estimate", side_effect=estimate),              patch.object(hirebase, "search", side_effect=exc),              patch.object(radar, "_set_source_rate_limit") as set_limit,              patch.object(radar, "_record_source_page"),              patch.object(radar, "_record_source_board"):
            jobs = radar.hirebase_collect({})
        self.assertEqual(jobs, [])
        self.assertEqual(calls, ["workday"])
        set_limit.assert_called_once()

    def test_default_config_has_optional_hirebase_off_and_daily_poll(self):
        base = radar._default_config()
        self.assertFalse(base["source_enabled"]["hirebase"])
        self.assertEqual(base["poll_seconds"]["hirebase"], 86400)
        with patch.object(hirebase, "api_key_configured", return_value=False):
            with self.assertRaisesRegex(radar.HTTPException, "HIREBASE_API_KEY"):
                radar.validate_config({
                    **base, "source_enabled": {**base["source_enabled"], "hirebase": True}
                })
        with patch.object(hirebase, "api_key_configured", return_value=True):
            accepted = radar.validate_config({
                **base, "source_enabled": {**base["source_enabled"], "hirebase": True}
            })
        self.assertTrue(accepted["source_enabled"]["hirebase"])

    def test_status_reports_only_the_current_hirebase_billing_period(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """INSERT INTO hirebase_usage_ledger
                   (provider,created_at,period_start,period_end,estimated_jobs,returned_jobs,
                    reserved_jobs,status,included_used,included_remaining,response_verified)
                   VALUES(?,?,?,?,?,NULL,?,'reserved',NULL,NULL,0)""",
                ("workday", "2026-10-01T00:00:00+00:00", "2026-10-01T00:00:00Z",
                 "2026-11-01T00:00:00Z", 120, 120),
            )
            conn.execute(
                """INSERT INTO hirebase_usage_ledger
                   (provider,created_at,period_start,period_end,estimated_jobs,returned_jobs,
                    reserved_jobs,status,included_used,included_remaining,response_verified)
                   VALUES(?,?,?,?,?,NULL,?,'reserved',NULL,NULL,0)""",
                ("keka", "2026-11-05T00:00:00+00:00", self.usage["period_start"],
                 self.usage["period_end"], 4, 4),
            )
        with patch.object(hirebase, "api_key_configured", return_value=False):
            status = radar.hirebase_status()
        self.assertEqual(status["budget"]["locally_counted_period_jobs"], 4)
        self.assertEqual(status["budget"]["last_metered_remaining"], None)

    def test_config_version_migration_forces_hirebase_off(self):
        migrated = radar._merge_config(
            {"config_version": 17, "source_enabled": {"hirebase": False}},
            {"config_version": 16, "source_enabled": {"hirebase": True}},
        )
        self.assertFalse(migrated["source_enabled"]["hirebase"])


class GlobalDirectoryApiTests(unittest.TestCase):
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
        auth.create_user(self.db, "global-admin@example.com", "a sufficiently strong test password", role="admin")
        auth.create_user(self.db, "global-member@example.com", "another sufficiently strong password", role="user")
        self.client = TestClient(radar.app, base_url="https://testserver")
        response = self.client.post("/api/auth/login", json={
            "email": "global-admin@example.com", "password": "a sufficiently strong test password",
        })
        self.assertEqual(response.status_code, 200)
        self.csrf = self.client.cookies.get("job_beeper_csrf")

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_admin_can_import_ccby_directory_as_discovered_candidates_only(self):
        seed = [
            {
                "provider": "greenhouse", "company_name": "Example",
                "board_key": "example", "board_url": "https://job-boards.greenhouse.io/example",
                "last_crawled": "2026-08-01", "collector_source": "greenhouse",
                "collector_available": True,
            },
            {
                "provider": "ashby", "company_name": "Other",
                "board_key": "other", "board_url": "https://jobs.ashbyhq.com/other",
                "last_crawled": "2026-07-12", "collector_source": "ashby",
                "collector_available": True,
            },
        ]
        with patch.object(ats_directory, "load_directory", return_value=seed):
            response = self.client.post(
                "/api/discovery/directories/last-round/import",
                headers={"X-CSRF-Token": self.csrf},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["boards_added"], 2)
        self.assertEqual(response.json()["review_status"], "discovered")
        self.assertEqual(response.json()["activation"], "none; imported candidates are not verified or scheduled")
        boards = self.client.get("/api/discovery/boards?limit=10").json()["boards"]
        self.assertEqual(len(boards), 2)
        self.assertTrue(all(board["review_status"] == "discovered" for board in boards))
        self.assertTrue(all(board["confidence"] == "low" for board in boards))
        self.assertEqual({board["directory_last_crawled"] for board in boards}, {"2026-08-01", "2026-07-12"})
        self.assertFalse(radar.get_config()["source_enabled"]["greenhouse"])
        self.assertFalse(radar.get_config()["source_enabled"]["ashby"])
        # A repeated import refreshes the existing provider/slug records; it must
        # not create duplicate employer rows or activate any source.
        with patch.object(ats_directory, "load_directory", return_value=seed):
            repeated = self.client.post(
                "/api/discovery/directories/last-round/import",
                headers={"X-CSRF-Token": self.csrf},
            )
        self.assertEqual(repeated.status_code, 200, repeated.text)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employer_companies").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ats_board_registry").fetchone()[0], 2)
        summary = self.client.get("/api/discovery/coverage-summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["employer_boards_known"], 2)
        self.assertEqual(summary.json()["directory_seed_candidates"], 2)
        self.assertIsNone(summary.json()["market_coverage_percentage"])

    def test_directory_import_is_admin_only_and_hirebase_status_never_exposes_key(self):
        member = TestClient(radar.app, base_url="https://testserver")
        try:
            login = member.post("/api/auth/login", json={
                "email": "global-member@example.com", "password": "another sufficiently strong password",
            })
            self.assertEqual(login.status_code, 200)
            self.assertEqual(member.post("/api/discovery/directories/last-round/import").status_code, 403)
            self.assertEqual(member.get("/api/hirebase/status").status_code, 403)
        finally:
            member.close()
        status = self.client.get("/api/hirebase/status")
        self.assertEqual(status.status_code, 200, status.text)
        body = status.json()
        self.assertIn("api_key_configured", body)
        self.assertNotIn("api_key", body)
        self.assertFalse(body["source_enabled"])
        self.assertEqual(body["budget"]["monthly_hard_cap"], 400)

    @patch.object(radar.hirebase, "estimate", return_value=2)
    def test_admin_hirebase_estimate_is_zero_job_credit_and_small_bounded(self, estimate):
        response = self.client.post(
            "/api/hirebase/estimate",
            json={"provider": "workday", "limit": 4},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["estimated_job_credits"], 2)
        self.assertEqual(response.json()["estimate_costs_job_credits"], 0)
        estimate.assert_called_once()
        self.assertEqual(estimate.call_args.args[0]["job_board"], ["workday"])
        self.assertEqual(estimate.call_args.args[0]["limit"], 4)
        invalid = self.client.post(
            "/api/hirebase/estimate", json={"provider": "workday", "limit": 5},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
