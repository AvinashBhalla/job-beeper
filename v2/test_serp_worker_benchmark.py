"""Offline tests for the SERP worker and benchmark harness."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v2 import serp_benchmark, serp_discovery_coordinator as coordinator


class SerpBenchmarkTests(unittest.TestCase):
    def test_plan_has_fifty_matched_provider_keyword_pairs(self):
        plan = serp_benchmark.build_benchmark_plan()
        self.assertEqual(len(plan), 50)
        self.assertEqual(len({(row["provider"], row["keyword"]) for row in plan}), 50)

    def test_paid_benchmark_requires_explicit_confirmation(self):
        with self.assertRaisesRegex(ValueError, "confirm-paid"):
            serp_benchmark.run_benchmark("/tmp/unused.jsonl")

    def test_paid_benchmark_requires_both_provider_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DATAFORSEO_LOGIN"):
                serp_benchmark.run_benchmark("/tmp/unused.jsonl", confirm_paid=True)


class SerpWorkerTests(unittest.TestCase):
    def test_run_once_uses_disabled_coordinator_without_credentials_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "jobs.sqlite3")
            coordinator.init_schema(db)
            with patch.dict(os.environ, {}, clear=True):
                result = serp_discovery_coordinator_worker_run(db)
            self.assertEqual(result["outcome"], "disabled")
            self.assertEqual(result["requests_attempted"], 0)


def serp_discovery_coordinator_worker_run(db: str):
    from v2.serp_discovery_worker import run_once
    return run_once(db)


if __name__ == "__main__":
    unittest.main()
