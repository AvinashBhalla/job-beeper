import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from v2.discovery_pilot import build_report


class DiscoveryPilotTest(unittest.TestCase):
    def test_only_public_post_baseline_jobs_count_and_empty_delivery_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            with closing(sqlite3.connect(path)) as conn:
                conn.executescript("""
                    CREATE TABLE jobs (id INTEGER PRIMARY KEY, source TEXT, source_posted_at TEXT,
                      posted_precision TEXT, discovered_at TEXT, source_initial_baseline INTEGER,
                      source_owner_user_id INTEGER);
                    CREATE TABLE source_runs (source TEXT, started_at TEXT, outcome TEXT, http_429 INTEGER);
                    CREATE TABLE user_notification_ledger (candidate_job_id INTEGER, created_at TEXT,
                      sent_at TEXT, status TEXT, backlog_override INTEGER);
                    INSERT INTO jobs VALUES
                      (1,'greenhouse','2026-11-23T12:01:00Z','minute','2026-11-23T17:32:30+05:30',0,NULL),
                      (2,'greenhouse','2026-11-23','date','2026-11-23T12:04:00Z',0,NULL),
                      (3,'greenhouse','2026-11-23T12:20:00Z','minute','2026-11-23T12:05:00Z',0,NULL),
                      (4,'greenhouse',NULL,'unknown','2026-11-23T12:05:00Z',1,NULL),
                      (5,'greenhouse',NULL,'unknown','2026-11-23T12:05:00Z',0,42),
                      (6,'greenhouse',NULL,'unknown','2026-11-23T11:59:00Z',0,NULL),
                      (7,'ashby',NULL,'unknown','2026-11-23T12:05:00Z',0,NULL);
                    INSERT INTO source_runs VALUES
                      ('greenhouse','2026-11-23T12:01:00Z','success',0),
                      ('greenhouse','2026-11-23T12:03:00Z','rate_limited',1),
                      ('ashby','2026-11-23T12:03:00Z','rate_limited',1);
                    INSERT INTO user_notification_ledger VALUES
                      (1,'2026-11-23T12:02:33Z',NULL,'queued',0),
                      (2,'2026-11-23T12:04:05Z','2026-11-23T12:04:14Z','sent',1),
                      (4,'2026-11-23T12:05:02Z','2026-11-23T12:05:20Z','sent',0);
                """)
                conn.commit()

            cutoff = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
            observed = build_report(path, "greenhouse", cutoff)
            self.assertEqual(observed["new_public_jobs"], 3)
            self.assertEqual(observed["jobs_without_measurable_publication_lag"], 2)
            self.assertEqual(observed["published_to_discovered"]["p95_seconds"], 90)
            self.assertEqual(observed["http_429_responses"], 1)
            self.assertEqual(observed["source_runs"], {"success": 1, "rate_limited": 1})
            self.assertEqual(observed["alerts_by_status"], {"queued": 1})
            self.assertEqual(observed["discovered_to_alert_queued"]["p95_seconds"], 3)
            self.assertEqual(observed["discovered_to_telegram_accepted"]["samples"], 0)
            self.assertIsNone(observed["discovered_to_telegram_accepted"]["p95_seconds"])

            with closing(sqlite3.connect(path)) as conn:
                conn.execute("UPDATE user_notification_ledger SET status='sent',sent_at=? WHERE candidate_job_id=1",
                             ("2026-11-23T12:02:44Z",))
                conn.commit()
            observed = build_report(path, "greenhouse", cutoff)
            self.assertEqual(observed["alerts_by_status"], {"sent": 1})
            self.assertEqual(observed["discovered_to_telegram_accepted"]["p95_seconds"], 14)
