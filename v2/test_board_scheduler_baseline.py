"""Per-board first-inventory suppression must not affect neighbouring boards."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v2 import radar


class PerBoardBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "baseline.sqlite3"
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.db_patch = patch.object(radar, "DB_PATH", self.db_path)
        self.config_patch = patch.object(radar, "RUNTIME_CONFIG_PATH", self.config_path)
        self.db_patch.start()
        self.config_patch.start()
        with patch.object(radar, "DEFAULT_CONFIG_PATH", Path(radar.__file__).with_name("config.json")):
            radar.init_db()

    def tearDown(self):
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_initial_snapshot_is_suppressed_for_one_board_only(self):
        config = radar.get_config()
        config.update({
            "target_roles": ["Python Engineer"],
            "skills": ["python"],
            "locations": ["Bengaluru, India"],
            "notifications_enabled": False,
        })
        started_at = radar.now()
        jobs = [
            radar.normalize_job(
                "greenhouse", "greenhouse-alpha-1", "Alpha", "Python Engineer",
                "Bengaluru, India", "https://boards.greenhouse.io/alpha/jobs/1",
                None, "unknown", "Build Python services.",
                source_details={"board_key": "alpha"},
            ),
            radar.normalize_job(
                "greenhouse", "greenhouse-beta-1", "Beta", "Python Engineer",
                "Bengaluru, India", "https://boards.greenhouse.io/beta/jobs/1",
                None, "unknown", "Build Python services.",
                source_details={"board_key": "beta"},
            ),
        ]
        radar.upsert_jobs(jobs, config, source_run_started_at=started_at)
        radar.refresh_job_evaluations(config)
        radar.refresh_notification_decisions(config)

        suppressed = radar.suppress_initial_board_snapshot_alerts(
            "greenhouse", "alpha",
        )
        self.assertEqual(suppressed, 1)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT source_job_id,source_initial_baseline,source_details_json,canonical_opportunity_id FROM jobs ORDER BY source_job_id").fetchall()
            by_id = {row["source_job_id"]: row for row in rows}
            self.assertEqual(by_id["greenhouse-alpha-1"]["source_initial_baseline"], 1)
            self.assertEqual(by_id["greenhouse-beta-1"]["source_initial_baseline"], 0)
            alpha_ledger = conn.execute(
                "SELECT baseline_suppressed,status FROM notification_ledger WHERE canonical_opportunity_id=?",
                (by_id["greenhouse-alpha-1"]["canonical_opportunity_id"],),
            ).fetchone()
            beta_ledger = conn.execute(
                "SELECT baseline_suppressed,status FROM notification_ledger WHERE canonical_opportunity_id=?",
                (by_id["greenhouse-beta-1"]["canonical_opportunity_id"],),
            ).fetchone()
        self.assertEqual(alpha_ledger["baseline_suppressed"], 1)
        self.assertEqual(beta_ledger["baseline_suppressed"], 0)

    def test_reactivated_board_suppresses_existing_unattempted_inventory(self):
        config = radar.get_config()
        timestamp = radar.iso(radar.now() - radar.dt.timedelta(days=2))
        job = radar.normalize_job(
            "greenhouse", "greenhouse-alpha-old", "Alpha", "Python Engineer",
            "Bengaluru, India", "https://boards.greenhouse.io/alpha/jobs/old",
            None, "unknown", "Build Python services.",
            source_details={"board_key": "alpha"},
        )
        job["first_seen_at"] = timestamp
        job["discovered_at"] = timestamp
        job["last_seen_at"] = timestamp
        radar.upsert_jobs([job], config)
        radar.refresh_job_evaluations(config)
        radar.refresh_notification_decisions(config)
        with sqlite3.connect(self.db_path) as conn:
            job_row = conn.execute(
                "SELECT id,canonical_opportunity_id FROM jobs WHERE source_job_id='greenhouse-alpha-old'"
            ).fetchone()
            self.assertIsNotNone(job_row)
            job_id, canonical_id = job_row
            conn.execute(
                """UPDATE notification_ledger SET status='queued',candidate_job_id=?,
                   baseline_suppressed=0,attempt_count=0,sent_at=NULL
                   WHERE canonical_opportunity_id=?""",
                (job_id, canonical_id),
            )
            conn.commit()

        suppressed = radar.suppress_initial_board_snapshot_alerts("greenhouse", "alpha")
        self.assertEqual(suppressed, 1)
        with sqlite3.connect(self.db_path) as conn:
            baseline = conn.execute(
                "SELECT source_initial_baseline FROM jobs WHERE id=?", (job_id,)
            ).fetchone()[0]
            ledger = conn.execute(
                "SELECT status,baseline_suppressed,candidate_job_id FROM notification_ledger WHERE canonical_opportunity_id=?",
                (canonical_id,),
            ).fetchone()
        self.assertEqual(baseline, 1)
        self.assertEqual(ledger, ("suppressed", 1, None))


if __name__ == "__main__":
    unittest.main()
