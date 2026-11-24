from __future__ import annotations

import sqlite3
import tempfile
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from v2 import user_notifications
from v2 import sqlite_store, telegram, radar


class UserNotificationServiceTests(unittest.TestCase):
    def setUp(self):
        self.clock_patcher = patch.object(
            user_notifications,
            "_now",
            return_value=datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc),
        )
        self.clock_patcher.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'notifications.sqlite3'
        with user_notifications._connect(self.db) as conn:
            conn.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE users(id INTEGER PRIMARY KEY);
            CREATE TABLE jobs(id INTEGER PRIMARY KEY, canonical_opportunity_id INTEGER, discovered_at TEXT,
              title TEXT, company TEXT, location TEXT, url TEXT, source TEXT,
              source_initial_baseline INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE canonical_opportunities(id INTEGER PRIMARY KEY);
            CREATE TABLE notification_ledger(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              canonical_opportunity_id INTEGER NOT NULL,
              baseline_suppressed INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'suppressed',
              candidate_job_id INTEGER,
              attempt_count INTEGER NOT NULL DEFAULT 0,
              next_attempt_at TEXT,
              claimed_at TEXT,
              sent_at TEXT,
              updated_at TEXT,
              last_error TEXT,
              decision_reason_json TEXT
            );
            CREATE TABLE user_preferences(user_id INTEGER PRIMARY KEY, preferences_json TEXT);
            CREATE TABLE user_job_evaluations(user_id INTEGER, job_id INTEGER, preference_fingerprint TEXT, match INTEGER, score INTEGER, reasons_json TEXT);
            CREATE TABLE user_telegram_chats(user_id INTEGER PRIMARY KEY, chat_id TEXT, chat_type TEXT);
            INSERT INTO users VALUES(1),(2);
            INSERT INTO canonical_opportunities VALUES(101),(102),(103);
            INSERT INTO jobs VALUES(1,101,'2026-11-07T10:00:00+00:00','Python Dev','Acme','Pune','https://example.com/1','naukri',0);
            INSERT INTO jobs VALUES(2,102,'2026-11-07T10:00:00+00:00','QA Dev','Beta','Delhi','https://example.com/2','naukri',0);
            INSERT INTO jobs VALUES(3,103,'2026-11-06T10:00:00+00:00','Old Dev','OldCo','Pune','https://example.com/3','naukri',0);
            INSERT INTO user_preferences VALUES(1,'{"match_threshold":55}'),(2,'{"match_threshold":55}');
            INSERT INTO user_telegram_chats VALUES(1,'111','private'),(2,'222','private');
            ''')
        with user_notifications._connect(self.db) as conn:
            conn.execute("ALTER TABLE jobs ADD COLUMN source_owner_user_id INTEGER")
            for column in (
                "source_posted_at TEXT", "posted_precision TEXT", "description TEXT NOT NULL DEFAULT ''",
                "source_details_json TEXT", "experience_min_years REAL", "experience_max_years REAL",
                "experience_provenance TEXT",
            ):
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {column}")
            conn.execute("""
                CREATE TABLE google_alerts_gmail_opportunities (
                    user_id INTEGER NOT NULL,
                    canonical_opportunity_id INTEGER NOT NULL,
                    candidate_job_id INTEGER NOT NULL,
                    history_backfill INTEGER NOT NULL DEFAULT 0,
                    first_observed_at TEXT NOT NULL DEFAULT '',
                    last_observed_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(user_id,canonical_opportunity_id)
                )
            """)
        user_notifications.init_schema(self.db)
        from v2 import user_preferences
        for uid in (1, 2):
            fingerprint = user_preferences.preferences_fingerprint({**user_preferences.PREFERENCE_DEFAULTS, "match_threshold": 55}, 3)
            with user_notifications._connect(self.db) as conn:
                job_id = 1 if uid == 1 else 2
                score = 90 if uid == 1 else 88
                conn.execute("INSERT INTO user_job_evaluations VALUES(?,?,?,?,?,?)", (uid, job_id, fingerprint, 1, score, '[]'))
        fingerprint = user_preferences.preferences_fingerprint({**user_preferences.PREFERENCE_DEFAULTS, "match_threshold": 55}, 3)
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_job_evaluations VALUES(?,?,?,?,?,?)", (1, 3, fingerprint, 1, 99, '[]'))
            for column in ("experience_min_years REAL", "experience_max_years REAL"):
                conn.execute(f"ALTER TABLE user_job_evaluations ADD COLUMN {column}")

    def tearDown(self):
        self.clock_patcher.stop()
        self.tmp.cleanup()

    def test_dispatch_does_not_open_claim_write_transaction_without_opted_in_users(self):
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN': 'test-token'}):
            with patch.object(user_notifications, "_claim_one") as claim:
                self.assertEqual(user_notifications.dispatch(self.db, 5), 0)
        claim.assert_not_called()

    def test_member_claim_and_legacy_recovery_share_one_writer_lock(self):
        self.assertIs(telegram.db_lock, sqlite_store.DB_LOCK)
        self.assertIs(radar.db_lock, sqlite_store.DB_LOCK)
        barrier = threading.Barrier(3)

        def claim_repeatedly():
            barrier.wait(timeout=3)
            for _ in range(30):
                user_notifications._claim_one(self.db)

        def recover_repeatedly():
            with patch.object(telegram, "DB_PATH", self.db):
                barrier.wait(timeout=3)
                for _ in range(30):
                    telegram.recover_stale_claims()

        with ThreadPoolExecutor(max_workers=2) as executor:
            claim_future = executor.submit(claim_repeatedly)
            recovery_future = executor.submit(recover_repeatedly)
            barrier.wait(timeout=3)
            claim_future.result(timeout=10)
            recovery_future.result(timeout=10)

    def test_default_is_off_and_explicit_enable_sets_baseline(self):
        self.assertFalse(user_notifications.get_settings(self.db, 1)['enabled'])
        enabled = user_notifications.set_enabled(self.db, 1, True)
        self.assertTrue(enabled['enabled'])
        self.assertIsNotNone(enabled['enabled_at'])
        self.assertFalse(user_notifications.set_enabled(self.db, 1, False)['enabled'])

    def test_queue_is_user_scoped_and_never_replays_pre_opt_in_jobs(self):
        # Baseline is after the old job and before the two fresh jobs.
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(2,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
        with user_notifications._connect(self.db) as conn:
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00'), 1)
            self.assertEqual(user_notifications._queue_new_matches(conn, 2, '2026-11-07T00:00:00+00:00'), 1)
            rows = [tuple(row) for row in conn.execute('SELECT user_id,candidate_job_id FROM user_notification_ledger ORDER BY user_id').fetchall()]
        self.assertEqual(rows, [(1, 1), (2, 2)])

    def test_disconnect_or_disable_cancels_pending_work_and_turns_off(self):
        user_notifications.set_enabled(self.db, 1, True)
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_ledger(user_id,canonical_opportunity_id,candidate_job_id,status,created_at,updated_at) VALUES(1,101,1,'queued','x','x')")
        user_notifications.set_enabled(self.db, 1, False)
        with user_notifications._connect(self.db) as conn:
            status = conn.execute('SELECT status FROM user_notification_ledger WHERE user_id=1').fetchone()[0]
        self.assertEqual(status, 'cancelled')

    def test_historical_gmail_result_bypasses_only_enabled_at_cutoff(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T11:00:00+00:00','2026-11-07T11:00:00+00:00')"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_opportunities
                   (user_id,canonical_opportunity_id,candidate_job_id,history_backfill,
                    first_observed_at,last_observed_at)
                   VALUES(1,101,1,1,'2026-11-07T11:30:00+00:00','2026-11-07T11:30:00+00:00')"""
            )
            queued = user_notifications._queue_new_matches(
                conn, 1, "2026-11-07T11:00:00+00:00"
            )
            row = conn.execute(
                "SELECT backlog_override FROM user_notification_ledger WHERE user_id=1"
            ).fetchone()
        self.assertEqual(queued, 1)
        self.assertEqual(row["backlog_override"], 1)

    def test_historical_gmail_override_does_not_bypass_max_age(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "UPDATE user_preferences SET preferences_json=? WHERE user_id=1",
                ('{"match_threshold":55,"max_age_hours":1}',),
            )
            conn.execute(
                "UPDATE jobs SET discovered_at=? WHERE id=1",
                ("2026-11-07T10:00:00+00:00",),
            )
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T11:00:00+00:00','2026-11-07T11:00:00+00:00')"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_opportunities
                   (user_id,canonical_opportunity_id,candidate_job_id,history_backfill)
                   VALUES(1,101,1,1)"""
            )
            queued = user_notifications._queue_new_matches(
                conn, 1, "2026-11-07T11:00:00+00:00"
            )
        self.assertEqual(queued, 0)

    def test_gmail_history_override_still_requires_owner_visibility(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("UPDATE jobs SET source_owner_user_id=2 WHERE id=1")
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T11:00:00+00:00','2026-11-07T11:00:00+00:00')"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_opportunities
                   (user_id,canonical_opportunity_id,candidate_job_id,history_backfill)
                   VALUES(1,101,1,1)"""
            )
            queued = user_notifications._queue_new_matches(
                conn, 1, "2026-11-07T11:00:00+00:00"
            )
        self.assertEqual(queued, 0)

    def test_historical_override_survives_claim_and_final_send_revalidation(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T11:00:00+00:00','2026-11-07T11:00:00+00:00')"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_opportunities
                   (user_id,canonical_opportunity_id,candidate_job_id,history_backfill)
                   VALUES(1,101,1,1)"""
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, "2026-11-07T11:00:00+00:00"
                ),
                1,
            )
        item = user_notifications._claim_one(self.db)
        self.assertIsNotNone(item)
        self.assertEqual(item["backlog_override"], 1)
        self.assertTrue(user_notifications._still_deliverable(self.db, item))

    def test_gmail_historical_delivery_pause_and_resume(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T11:00:00+00:00','2026-11-07T11:00:00+00:00')"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_opportunities
                   (user_id,canonical_opportunity_id,candidate_job_id,history_backfill)
                   VALUES(1,101,1,1)"""
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, "2026-11-07T11:00:00+00:00"
                ),
                1,
            )
        paused = user_notifications.set_gmail_backfill_paused(self.db, 1, True)
        self.assertTrue(paused["gmail_backfill_paused"])
        self.assertIsNone(user_notifications._claim_one(self.db))
        self.assertEqual(
            user_notifications.gmail_historical_delivery_summary(self.db, 1),
            {"queued": 1},
        )
        resumed = user_notifications.set_gmail_backfill_paused(self.db, 1, False)
        self.assertFalse(resumed["gmail_backfill_paused"])
        item = user_notifications._claim_one(self.db)
        self.assertIsNotNone(item)
        self.assertTrue(user_notifications._still_deliverable(self.db, item))

    def test_retry_only_requeues_gmail_historical_delivery_rows(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T11:00:00+00:00','2026-11-07T11:00:00+00:00')"
            )
            conn.execute(
                """INSERT INTO google_alerts_gmail_opportunities
                   (user_id,canonical_opportunity_id,candidate_job_id,history_backfill)
                   VALUES(1,101,1,1)"""
            )
            conn.execute(
                """INSERT INTO user_notification_ledger(
                     user_id,canonical_opportunity_id,candidate_job_id,status,
                     backlog_override,created_at,updated_at
                   ) VALUES(1,101,1,'dead',1,'x','x')"""
            )
            conn.execute(
                """INSERT INTO user_notification_ledger(
                     user_id,canonical_opportunity_id,candidate_job_id,status,
                     backlog_override,created_at,updated_at
                   ) VALUES(1,102,2,'dead',0,'x','x')"""
            )
        self.assertEqual(
            user_notifications.retry_gmail_historical_notifications(self.db, 1), 1
        )
        with user_notifications._connect(self.db) as conn:
            rows = dict(conn.execute(
                "SELECT canonical_opportunity_id,status FROM user_notification_ledger"
            ).fetchall())
        self.assertEqual(rows[101], "queued")
        self.assertEqual(rows[102], "dead")

    def test_initial_source_baseline_jobs_are_not_queued_for_any_member(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("UPDATE jobs SET source_initial_baseline=1 WHERE id=1")
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, '2026-11-07T00:00:00+00:00'
                ),
                0,
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 2, '2026-11-07T00:00:00+00:00'
                ),
                1,
            )
            rows = [
                tuple(row)
                for row in conn.execute(
                    "SELECT user_id,candidate_job_id FROM user_notification_ledger ORDER BY user_id"
                ).fetchall()
            ]
        self.assertEqual(rows, [(2, 2)])

    def test_baseline_marker_blocks_a_previously_queued_item_before_send(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')"
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, '2026-11-07T00:00:00+00:00'
                ),
                1,
            )
            conn.execute("UPDATE jobs SET source_initial_baseline=1 WHERE id=1")

        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch.dict(
            "os.environ", {"JOB_RADAR_TELEGRAM_BOT_TOKEN": "test-token"}
        ), patch.object(
            user_notifications.requests, "post", return_value=response
        ) as post:
            self.assertEqual(user_notifications.dispatch(self.db, 5), 0)
        post.assert_not_called()
        with user_notifications._connect(self.db) as conn:
            status = conn.execute(
                "SELECT status FROM user_notification_ledger WHERE user_id=1"
            ).fetchone()[0]
        self.assertEqual(status, "cancelled")

    def test_canonical_baseline_marker_excludes_cross_source_opportunity_from_member_queue(self):
        with user_notifications._connect(self.db) as conn:
            # The Lever source row can be a baseline row while the canonical
            # opportunity originated earlier from Naukri. Its canonical-level
            # marker must still suppress the member notification.
            conn.execute(
                "INSERT INTO notification_ledger(canonical_opportunity_id,baseline_suppressed,status) VALUES(101,1,'suppressed')"
            )
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')"
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, '2026-11-07T00:00:00+00:00'
                ),
                0,
            )
            count=conn.execute("SELECT COUNT(*) FROM user_notification_ledger").fetchone()[0]
        self.assertEqual(count,0)

    def test_canonical_baseline_marker_cancels_previously_queued_member_item(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')"
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, '2026-11-07T00:00:00+00:00'
                ),
                1,
            )
            conn.execute(
                "INSERT INTO notification_ledger(canonical_opportunity_id,baseline_suppressed,status) VALUES(101,1,'suppressed')"
            )
        item=user_notifications._claim_one(self.db)
        self.assertIsNone(item)
        with user_notifications._connect(self.db) as conn:
            row=conn.execute(
                "SELECT status,last_error FROM user_notification_ledger WHERE user_id=1"
            ).fetchone()
        self.assertEqual(row["status"],"cancelled")
        self.assertEqual(row["last_error"],"initial_source_baseline")

    def test_canonical_baseline_marker_blocks_final_send_revalidation(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')"
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, '2026-11-07T00:00:00+00:00'
                ),
                1,
            )
        item=user_notifications._claim_one(self.db)
        self.assertIsNotNone(item)
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO notification_ledger(canonical_opportunity_id,baseline_suppressed,status) VALUES(101,1,'suppressed')"
            )
        self.assertFalse(user_notifications._still_deliverable(self.db,item))

    def test_max_age_window_excludes_only_jobs_older_than_the_limit(self):
        with user_notifications._connect(self.db) as conn:
            # Frozen clock is 2026-11-07 12:00 UTC; the default max age is 72h.
            conn.execute(
                "UPDATE jobs SET discovered_at=? WHERE id IN (1,3)",
                ("2026-11-04T11:59:59+00:00",),
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, "2026-11-04T00:00:00+00:00"
                ),
                0,
            )
            conn.execute(
                "UPDATE jobs SET discovered_at=? WHERE id=1",
                ("2026-11-04T12:00:00+00:00",),
            )
            self.assertEqual(
                user_notifications._queue_new_matches(
                    conn, 1, "2026-11-04T00:00:00+00:00"
                ),
                1,
            )

    def test_stale_preference_evaluation_is_not_queued(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("UPDATE user_job_evaluations SET preference_fingerprint='stale' WHERE user_id=1 AND job_id=1")
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00'), 0)

    def test_queue_is_idempotent_for_same_user_and_opportunity(self):
        with user_notifications._connect(self.db) as conn:
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00'), 1)
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00'), 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM user_notification_ledger WHERE user_id=1').fetchone()[0], 1)

    def test_transient_delivery_failure_is_recorded_for_retry(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
            user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00')
        response = unittest.mock.Mock(status_code=503)
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN':'test-token'}), patch.object(user_notifications.requests, 'post', return_value=response):
            self.assertEqual(user_notifications.dispatch(self.db, 1), 0)
        with user_notifications._connect(self.db) as conn:
            row = conn.execute('SELECT status,attempt_count,next_attempt_at,last_error FROM user_notification_ledger').fetchone()
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['attempt_count'], 1)
        self.assertIsNotNone(row['next_attempt_at'])
        self.assertEqual(row['last_error'], 'RuntimeError')

    def test_zero_dispatch_limit_is_a_true_noop(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute(
                "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')"
            )
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN': 'test-token'}):
            with patch.object(user_notifications, "_queue_new_matches") as queue:
                with patch.object(user_notifications, "_claim_one") as claim:
                    self.assertEqual(user_notifications.dispatch(self.db, 0), 0)
        queue.assert_not_called()
        claim.assert_not_called()

    def test_dispatch_queues_each_enabled_user_once_per_cycle(self):
        with user_notifications._connect(self.db) as conn:
            for uid in (1, 2):
                conn.execute(
                    "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(?,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')",
                    (uid,),
                )
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN': 'test-token'}):
            with patch.object(user_notifications, "_queue_new_matches", wraps=user_notifications._queue_new_matches) as queue:
                with patch.object(user_notifications, "_claim_one", return_value=None):
                    self.assertEqual(user_notifications.dispatch(self.db, 5), 0)
        self.assertEqual(queue.call_count, 2)

    def test_dispatch_sends_only_to_owner_chat_and_marks_sent(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("""UPDATE jobs SET source='instahyre', experience_min_years=3,
                experience_max_years=5, experience_provenance='description', source_details_json=? WHERE id=1""",
                ('{"key_skills":["React Native","TypeScript"],"listing_experience":"4-7 Years"}',))
            conn.execute("UPDATE user_job_evaluations SET reasons_json=? WHERE user_id=1 AND job_id=1", ('["target location"]',))
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
            user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00')
        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = {'ok': True}
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN':'test-token'}), patch.object(user_notifications.requests, 'post', return_value=response) as post:
            self.assertEqual(user_notifications.dispatch(self.db, 5), 1)
        self.assertEqual(post.call_args.kwargs['json']['chat_id'], '111')
        text = post.call_args.kwargs['json']['text']
        for field in (
            "Posted: Unknown", "Discovered: 07 Nov 2026, 3:30 PM IST",
            "Experience: 3-5 years (JD) · Listing header: 4-7 Years",
            "Key skills: React Native, TypeScript", "✓ target location", "Apply → https://example.com/1",
        ):
            self.assertIn(field, text)
        with user_notifications._connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT status FROM user_notification_ledger').fetchone()[0], 'sent')

    def test_instahyre_waits_for_source_backed_experience_before_claiming(self):
        enabled_at = '2026-11-07T00:00:00+00:00'
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,?,?)",
                         (enabled_at, enabled_at))
            conn.execute("UPDATE jobs SET source='instahyre', experience_provenance='inferred', experience_min_years=4 WHERE id=1")
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, enabled_at), 0)
            # Also cover an incomplete job already queued by a previous build.
            conn.execute("UPDATE jobs SET source='naukri' WHERE id=1")
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, enabled_at), 1)
            conn.execute("UPDATE jobs SET source='instahyre' WHERE id=1")
        self.assertIsNone(user_notifications._claim_one(self.db))
        with user_notifications._connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT status FROM user_notification_ledger").fetchone()[0], "queued")
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, enabled_at), 0)
            conn.execute("UPDATE jobs SET experience_provenance='employer_stated' WHERE id=1")
        self.assertIsNotNone(user_notifications._claim_one(self.db))

    def test_repeated_enable_preserves_the_original_no_backlog_boundary(self):
        first = user_notifications.set_enabled(self.db, 1, True)
        with patch.object(user_notifications, "_stamp", return_value="2099-01-01T00:00:00+00:00"):
            repeated = user_notifications.set_enabled(self.db, 1, True)
        self.assertEqual(repeated["enabled_at"], first["enabled_at"])
        user_notifications.set_enabled(self.db, 1, False)
        with patch.object(user_notifications, "_stamp", return_value="2099-01-01T00:00:00+00:00"):
            reenabled = user_notifications.set_enabled(self.db, 1, True)
        self.assertEqual(reenabled["enabled_at"], "2099-01-01T00:00:00+00:00")

    def test_preference_change_cancels_a_queued_job_that_no_longer_has_a_fresh_evaluation(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00'), 1)
            conn.execute("UPDATE user_preferences SET preferences_json=? WHERE user_id=1", ('{"match_threshold":95}',))
        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN':'test-token'}), patch.object(user_notifications.requests, 'post', return_value=response) as post:
            self.assertEqual(user_notifications.dispatch(self.db, 5), 0)
        post.assert_not_called()
        with user_notifications._connect(self.db) as conn:
            status = conn.execute("SELECT status FROM user_notification_ledger WHERE user_id=1").fetchone()[0]
        self.assertEqual(status, "cancelled")

    def test_current_nonmatching_evaluation_cancels_previously_queued_notification(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
            self.assertEqual(user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00'), 1)
            conn.execute("UPDATE user_job_evaluations SET match=0 WHERE user_id=1 AND job_id=1")
        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN':'test-token'}), patch.object(user_notifications.requests, 'post', return_value=response) as post:
            self.assertEqual(user_notifications.dispatch(self.db, 5), 0)
        post.assert_not_called()
        with user_notifications._connect(self.db) as conn:
            status = conn.execute("SELECT status FROM user_notification_ledger WHERE user_id=1").fetchone()[0]
        self.assertEqual(status, "cancelled")

    def test_two_users_receive_only_their_own_matching_job_and_chat(self):
        with user_notifications._connect(self.db) as conn:
            for uid in (1, 2):
                conn.execute(
                    "INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(?,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')",
                    (uid,),
                )
        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN':'test-token'}), patch.object(user_notifications.requests, 'post', return_value=response) as post:
            self.assertEqual(user_notifications.dispatch(self.db, 5), 2)
        delivered = {
            (call.kwargs["json"]["chat_id"], call.kwargs["json"]["text"].splitlines()[2])
            for call in post.call_args_list
        }
        self.assertEqual(delivered, {("111", "Python Dev"), ("222", "QA Dev")})
        with user_notifications._connect(self.db) as conn:
            rows = conn.execute("SELECT user_id,status FROM user_notification_ledger ORDER BY user_id").fetchall()
        self.assertEqual([(row["user_id"], row["status"]) for row in rows], [(1, "sent"), (2, "sent")])

    def test_permanent_telegram_client_error_is_not_retried(self):
        with user_notifications._connect(self.db) as conn:
            conn.execute("INSERT INTO user_notification_settings(user_id,enabled,enabled_at,updated_at) VALUES(1,1,'2026-11-07T00:00:00+00:00','2026-11-07T00:00:00+00:00')")
            user_notifications._queue_new_matches(conn, 1, '2026-11-07T00:00:00+00:00')
        response = unittest.mock.Mock(status_code=400)
        response.raise_for_status.side_effect = user_notifications.requests.HTTPError("bad request", response=response)
        with patch.dict('os.environ', {'JOB_RADAR_TELEGRAM_BOT_TOKEN':'test-token'}), patch.object(user_notifications.requests, 'post', return_value=response):
            self.assertEqual(user_notifications.dispatch(self.db, 1), 0)
        with user_notifications._connect(self.db) as conn:
            row = conn.execute("SELECT status,next_attempt_at,attempt_count FROM user_notification_ledger").fetchone()
        self.assertEqual(row["status"], "dead")
        self.assertIsNone(row["next_attempt_at"])
        self.assertEqual(row["attempt_count"], 1)


if __name__ == '__main__':
    unittest.main()
