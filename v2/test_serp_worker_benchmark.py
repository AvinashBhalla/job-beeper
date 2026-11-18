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

    def test_summary_deduplicates_boards_and_reports_manual_verdicts(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            rows = [
                {"engine": "dataforseo_live", "query": "software engineer India", "organic_results": 8, "candidates": [
                    {"board_url": "https://jobs.ashbyhq.com/acme", "manual_verdict": "verified"},
                    {"board_url": "https://jobs.ashbyhq.com/beta", "manual_verdict": "false_positive"},
                ]},
                {"engine": "dataforseo_live", "query": "backend engineer India", "organic_results": 6, "candidates": [
                    {"board_url": "https://jobs.ashbyhq.com/acme"},
                ]},
                {"engine": "serper", "query": '"software engineer" India site:ashbyhq.com', "organic_results": 7, "candidates": [
                    {"board_url": "https://jobs.ashbyhq.com/acme"},
                    {"board_url": "https://jobs.ashbyhq.com/gamma"},
                ]},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            report = serp_benchmark.summarize_benchmark(str(path))
        dataforseo = report["engines"]["dataforseo_live"]
        self.assertEqual(dataforseo["candidate_appearances"], 3)
        self.assertEqual(dataforseo["unique_boards"], 2)
        self.assertEqual(dataforseo["duplicate_appearances"], 1)
        self.assertEqual(dataforseo["manually_verified_unique_boards"], 1)
        self.assertEqual(dataforseo["manually_false_positive_unique_boards"], 1)
        self.assertEqual(report["cross_engine"]["shared_unique_boards"], 1)
        self.assertEqual(report["cross_engine"]["unique_board_union"], 3)
        self.assertFalse(report["matched_pairs_complete"])

    def test_summary_rejects_malformed_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.jsonl"
            path.write_text("{bad json}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid JSON"):
                serp_benchmark.summarize_benchmark(str(path))

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
