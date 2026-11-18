"""Tests for the disabled-by-default SERP discovery coordinator."""
from __future__ import annotations

import datetime as dt
import math
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v2 import serp_discovery_coordinator as coordinator

UTC = dt.timezone.utc


class SerpDiscoveryCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "jobs.sqlite3")
        self.now = dt.datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
        coordinator.init_schema(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute(
                "SELECT enabled,monthly_cap_usd,monthly_spend_usd,budget_month,provider_cursor,last_outcome FROM serp_discovery_control WHERE id=1"
            ).fetchone()

    def test_coordinator_is_disabled_by_default_and_makes_no_request(self):
        calls = []
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: calls.append(provider) or {},
            importer=lambda payload: {},
            at=self.now,
        )
        self.assertEqual(result, {"outcome": "disabled", "requests_attempted": 0})
        self.assertEqual(calls, [])
        self.assertEqual(self.state()[0], 0)

    def test_enable_requires_an_explicit_positive_monthly_cap(self):
        with self.assertRaisesRegex(ValueError, "positive monthly spend cap"):
            coordinator.configure(self.db, enabled=True, monthly_cap_usd=None)
        with self.assertRaises(ValueError):
            coordinator.configure(self.db, enabled=True, monthly_cap_usd=0)
        self.assertEqual(self.state()[0], 0)

    def test_enable_rejects_non_finite_and_boolean_monthly_caps(self):
        for invalid in (float("nan"), float("inf"), float("-inf"), True):
            with self.subTest(cap=invalid), self.assertRaisesRegex(ValueError, "finite number"):
                coordinator.configure(self.db, enabled=True, monthly_cap_usd=invalid)
        self.assertEqual(self.state()[0], 0)

    def test_run_once_fails_closed_on_non_finite_stored_cap_or_spend(self):
        calls = []
        coordinator.configure(self.db, enabled=False, monthly_cap_usd=None)
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE serp_discovery_control SET enabled=1,monthly_cap_usd=? WHERE id=1",
                (float("inf"),),
            )
            conn.commit()
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: calls.append(provider) or {},
            importer=lambda payload: {},
            at=self.now,
        )
        self.assertEqual(result["outcome"], "budget_not_configured")
        self.assertEqual(calls, [])

        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE serp_discovery_control SET monthly_cap_usd=6,monthly_spend_usd=? WHERE id=1",
                (float("inf"),),
            )
            conn.commit()
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: calls.append(provider) or {},
            importer=lambda payload: {},
            at=self.now,
        )
        self.assertEqual(result["outcome"], "budget_invalid")
        self.assertEqual(calls, [])

    def test_non_finite_provider_cost_keeps_conservative_reservation(self):
        coordinator.configure(self.db, enabled=True, monthly_cap_usd=6.0)
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: {
                "candidates": [], "actual_cost_usd": math.inf,
            },
            importer=lambda payload: {},
            at=self.now,
            providers_per_cycle=1,
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(result["runs"][0]["actual_cost_usd"])
        self.assertEqual(self.state()[2], 0.002)

    def test_enabled_cycle_rotates_two_providers_and_imports_review_candidates(self):
        coordinator.configure(self.db, enabled=True, monthly_cap_usd=6.0)
        calls = []
        imported = []

        def searcher(provider):
            calls.append(provider)
            return {
                "query": "software engineer India",
                "organic_results": 4,
                "actual_cost_usd": 0.002,
                "candidates": [{
                    "board_url": f"https://jobs.ashbyhq.com/{provider}",
                    "discovery_method": "search_engine_serp",
                    "source_reference": f"provider={provider}",
                    "source_captured_at": self.now.isoformat(),
                }],
            }

        def importer(payload):
            imported.extend(payload["candidates"])
            return {"inserted": len(payload["candidates"])}

        result = coordinator.run_once(
            self.db, searcher=searcher, importer=importer, at=self.now,
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["requests_attempted"], 2)
        self.assertEqual(calls, list(coordinator.serp.SERP_PROVIDER_ORDER[:2]))
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(len(imported), 2)
        self.assertEqual(result["import_result"]["inserted"], 2)
        self.assertEqual(self.state()[2], 0.004)
        self.assertEqual(self.state()[4], 2)

        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM serp_discovery_runs").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM serp_discovery_runs WHERE outcome='success'").fetchone()[0], 2)

    def test_cycle_throttles_until_thirty_minutes_have_elapsed(self):
        coordinator.configure(self.db, enabled=True, monthly_cap_usd=6.0)
        calls = []
        searcher = lambda provider: calls.append(provider) or {
            "candidates": [], "actual_cost_usd": 0.002,
        }
        importer = lambda payload: {}

        first = coordinator.run_once(
            self.db, searcher=searcher, importer=importer, at=self.now,
        )
        second = coordinator.run_once(
            self.db, searcher=searcher, importer=importer,
            at=self.now + dt.timedelta(minutes=29),
        )
        third = coordinator.run_once(
            self.db, searcher=searcher, importer=importer,
            at=self.now + dt.timedelta(minutes=30),
        )
        self.assertEqual(first["outcome"], "success")
        self.assertEqual(second["outcome"], "throttled")
        self.assertEqual(second["requests_attempted"], 0)
        self.assertEqual(third["outcome"], "success")
        self.assertEqual(calls, list(coordinator.serp.SERP_PROVIDER_ORDER[:4]))

    def test_monthly_cap_stops_before_the_next_paid_request(self):
        coordinator.configure(self.db, enabled=True, monthly_cap_usd=0.003)
        calls = []
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: calls.append(provider) or {
                "candidates": [], "actual_cost_usd": 0.002,
            },
            importer=lambda payload: {},
            at=self.now,
        )
        self.assertEqual(result["outcome"], "budget_exhausted")
        self.assertEqual(result["requests_attempted"], 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.state()[2], 0.002)

    def test_new_month_resets_spend_before_budget_check(self):
        coordinator.configure(self.db, enabled=True, monthly_cap_usd=0.003)
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE serp_discovery_control SET monthly_spend_usd=0.003,budget_month='2026-10' WHERE id=1"
            )
            conn.commit()
        calls = []
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: calls.append(provider) or {
                "candidates": [], "actual_cost_usd": 0.002,
            },
            importer=lambda payload: {},
            at=self.now,
        )
        self.assertEqual(result["requests_attempted"], 1)
        self.assertEqual(self.state()[2], 0.002)
        self.assertEqual(self.state()[3], "2026-11")

    def test_search_failure_keeps_conservative_reserved_cost_and_records_error(self):
        coordinator.configure(self.db, enabled=True, monthly_cap_usd=6.0)
        result = coordinator.run_once(
            self.db,
            searcher=lambda provider: (_ for _ in ()).throw(TimeoutError()),
            importer=lambda payload: {},
            at=self.now,
            providers_per_cycle=1,
        )
        self.assertEqual(result["outcome"], "partial_failure")
        self.assertEqual(result["runs"][0]["error_type"], "TimeoutError")
        self.assertEqual(self.state()[2], 0.002)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(
                conn.execute("SELECT outcome,error_type FROM serp_discovery_runs").fetchone(),
                ("request_error", "TimeoutError"),
            )


if __name__ == "__main__":
    unittest.main()
