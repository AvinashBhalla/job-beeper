"""The async scheduler must pass one exact board to run_source and persist it."""
from __future__ import annotations

import asyncio
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v2 import board_scheduler, radar
from v2.sqlite_store import connect

UTC = dt.timezone.utc


class BoardSchedulerOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "orchestration.sqlite3"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.db_patch.start()
        with connect(self.db_path) as conn:
            conn.execute("CREATE TABLE source_runs(source TEXT,outcome TEXT)")
            conn.execute("CREATE TABLE ats_board_registry(id INTEGER PRIMARY KEY,baseline_pending INTEGER,review_status TEXT)")
        board_scheduler.init_schema(str(self.db_path))
        self.config = {
            "source_enabled": {"greenhouse": True},
            "poll_seconds": {"greenhouse": 900},
            "greenhouse_boards": [
                {"token": "alpha", "company": "Alpha"},
                {"token": "beta", "company": "Beta"},
            ],
            "target_roles": [], "skills": [], "locations": [],
            "notifications_enabled": False,
        }
        self.now = dt.datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
        board_scheduler.sync_config(str(self.db_path), self.config, self.now)
        self.original_runtime = dict(radar.source_state.get("greenhouse", {}))

    def tearDown(self):
        radar.source_state["greenhouse"] = self.original_runtime
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_worker_calls_collector_with_single_board_and_persists_outcome(self):
        claim = board_scheduler.claim_due_board(str(self.db_path), at=self.now)
        self.assertEqual(claim["source"], "greenhouse")
        captured = {}

        def fake_run_source(source, scoped_config, scheduled_board=None):
            captured["source"] = source
            captured["boards"] = scoped_config["greenhouse_boards"]
            captured["scheduled_board"] = scheduled_board
            radar.source_state[source] = {
                "run_id": "orchestration-run-1",
                "last_run_outcome": "success",
                "jobs_seen": 12,
                "new_jobs": 2,
                "last_run_duration_seconds": 4.2,
                "cooldown_seconds": None,
                "running": False,
            }

        with patch.object(radar, "run_source", side_effect=fake_run_source):
            asyncio.run(radar._run_scheduled_board(claim, self.config))

        self.assertEqual(captured["source"], "greenhouse")
        self.assertEqual(captured["boards"], [{"token": "alpha", "company": "Alpha"}])
        self.assertEqual(captured["scheduled_board"]["board_key"], "alpha")
        self.assertTrue(captured["scheduled_board"]["baseline_pending"])
        row = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["board_key"] == "alpha")
        self.assertEqual(row["last_outcome"], "success")
        self.assertEqual(row["last_jobs_seen"], 12)
        self.assertEqual(row["last_jobs_new"], 2)
        beta = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["board_key"] == "beta")
        self.assertIsNone(beta["last_outcome"])


if __name__ == "__main__":
    unittest.main()
