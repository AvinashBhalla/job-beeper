"""Deterministic tests for persistent employer-board scheduling and host budgets."""
from __future__ import annotations

import datetime as dt
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v2 import board_scheduler

UTC = dt.timezone.utc


class BoardSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "scheduler.sqlite3"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE source_runs(source TEXT NOT NULL,outcome TEXT)")
            conn.execute("""
                CREATE TABLE ats_board_registry(
                    id INTEGER PRIMARY KEY,baseline_pending INTEGER NOT NULL DEFAULT 0,
                    review_status TEXT NOT NULL DEFAULT 'discovered'
                )
            """)
        board_scheduler.init_schema(str(self.db_path))
        self.now = dt.datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

    def tearDown(self):
        self.temp_dir.cleanup()

    def config(self):
        return {
            "source_enabled": {
                "greenhouse": True, "ashby": True, "lever": True,
                "workday": True, "smartrecruiters": True, "workable": True,
                "keka": True, "darwinbox": True,
            },
            "poll_seconds": {"greenhouse": 900, "ashby": 1800, "lever": 1800,
                              "workday": 120, "smartrecruiters": 120,
                              "workable": 120, "keka": 120, "darwinbox": 120},
            "greenhouse_boards": [
                {"token": "alpha", "company": "Alpha"},
                {"token": "beta", "company": "Beta"},
            ],
            "ashby_boards": [{"board": "sample", "company": "Sample"}],
            "lever_boards": [{"site": "acme", "company": "Acme", "instance": "eu"}],
            "workday_boards": [{"url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", "company": "NVIDIA"}],
            "smartrecruiters_boards": [{"company_identifier": "bosch", "company": "Bosch"}],
            "workable_boards": [{"account": "example", "company": "Example"}],
            "keka_boards": [{"careers_url": "https://tenant.keka.com/careers/engineering", "company": "Tenant"}],
            "darwinbox_boards": [{"careers_url": "https://tenant.darwinbox.in/ms/candidatev2/123/careers", "company": "Tenant DB"}],
        }

    def test_configured_boards_have_stable_keys_and_provider_hosts(self):
        entries = board_scheduler.configured_boards(self.config())
        by_source = {entry["source"]: entry for entry in entries if entry["source"] not in {"greenhouse"}}
        self.assertEqual(len(entries), 9)
        self.assertEqual(by_source["ashby"]["host_key"], "api.ashbyhq.com")
        self.assertEqual(by_source["lever"]["board_key"], "eu:acme")
        self.assertEqual(by_source["lever"]["host_key"], "api.eu.lever.co")
        self.assertEqual(by_source["workday"]["board_key"], "nvidia:nvidiaexternalcareersite")
        self.assertEqual(by_source["workday"]["host_key"], "nvidia.wd5.myworkdayjobs.com")
        self.assertEqual(by_source["smartrecruiters"]["host_key"], "api.smartrecruiters.com")
        self.assertEqual(by_source["workable"]["host_key"], "apply.workable.com")
        self.assertEqual(by_source["keka"]["board_key"], "tenant:engineering")
        self.assertEqual(by_source["darwinbox"]["board_key"], "123")

    def test_new_board_baselines_even_when_provider_has_prior_success(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO source_runs(source,outcome) VALUES('greenhouse','success')")
        config = self.config()
        config["greenhouse_boards"] = [{"token": "new-employer", "company": "New Employer"}]
        config["source_enabled"] = {"greenhouse": True}
        board_scheduler.sync_config(str(self.db_path), config, self.now)
        row = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["board_key"] == "new-employer")
        self.assertEqual(row["baseline_pending"], 1)

    def test_reactivated_manual_board_baselines_without_registry_record(self):
        config = self.config()
        config["greenhouse_boards"] = [{"token": "manual-board", "company": "Manual Board"}]
        config["source_enabled"] = {"greenhouse": True}
        board_scheduler.sync_config(str(self.db_path), config, self.now)
        claim = board_scheduler.claim_due_board(str(self.db_path), at=self.now)
        board_scheduler.finish_poll(str(self.db_path), claim, outcome="success", at=self.now + dt.timedelta(seconds=1))
        config["source_enabled"]["greenhouse"] = False
        board_scheduler.sync_config(str(self.db_path), config, self.now + dt.timedelta(seconds=2))
        config["source_enabled"]["greenhouse"] = True
        board_scheduler.sync_config(str(self.db_path), config, self.now + dt.timedelta(seconds=3))
        row = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["board_key"] == "manual-board")
        self.assertEqual(row["baseline_pending"], 1)
        self.assertEqual(row["next_due_at"], (self.now + dt.timedelta(seconds=3)).isoformat())

    def test_sync_creates_only_enabled_board_schedules_and_initial_baselines(self):
        config = self.config()
        config["source_enabled"]["darwinbox"] = False
        created = board_scheduler.sync_config(str(self.db_path), config, self.now)
        self.assertEqual(created, 8)
        status = board_scheduler.status(str(self.db_path))
        self.assertEqual(status["active_boards"], 8)
        self.assertEqual(status["inactive_boards"], 0)
        self.assertTrue(all(row["baseline_pending"] for row in status["boards"]))
        self.assertEqual({row["source"] for row in status["boards"]}, {
            "greenhouse", "ashby", "lever", "workday", "smartrecruiters", "workable", "keka",
        })

    def test_host_lease_prevents_two_boards_on_same_api_host(self):
        board_scheduler.sync_config(str(self.db_path), self.config(), self.now)
        excluded = {"ashby", "lever", "workday", "smartrecruiters", "workable", "keka", "darwinbox"}
        first = board_scheduler.claim_due_board(str(self.db_path), excluded_sources=excluded, at=self.now)
        self.assertEqual(first["source"], "greenhouse")
        # The second Greenhouse board shares boards-api.greenhouse.io and must
        # remain unclaimable until the first board releases that host lease.
        self.assertIsNone(board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources=excluded, at=self.now
        ))
        # Different API hosts can still be claimed while Greenhouse is leased.
        second = board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources={"greenhouse", "lever", "workday", "smartrecruiters", "workable", "keka", "darwinbox"},
            at=self.now,
        )
        self.assertEqual(second["source"], "ashby")
        self.assertNotEqual(first["host_key"], second["host_key"])

    def test_success_persists_next_due_and_clears_baseline(self):
        board_scheduler.sync_config(str(self.db_path), self.config(), self.now)
        claim = board_scheduler.claim_due_board(str(self.db_path), excluded_sources={"greenhouse", "ashby", "darwinbox", "keka", "lever", "smartrecruiters", "workable"}, at=self.now)
        # Workday is the only remaining configured provider after exclusions.
        self.assertEqual(claim["source"], "workday")
        result = board_scheduler.finish_poll(
            str(self.db_path), claim, outcome="success", jobs_seen=20,
            jobs_new=20, duration_seconds=12.5, at=self.now + dt.timedelta(seconds=20),
        )
        self.assertFalse(result["baseline_pending"])
        row = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["source"] == "workday")
        self.assertEqual(row["last_outcome"], "success")
        self.assertEqual(row["last_jobs_seen"], 20)
        self.assertEqual(row["last_jobs_new"], 20)
        self.assertEqual(row["consecutive_failures"], 0)
        self.assertEqual(row["next_due_at"], (self.now + dt.timedelta(seconds=140)).isoformat())

    def test_failure_backoff_is_per_board_and_does_not_block_other_host(self):
        board_scheduler.sync_config(str(self.db_path), self.config(), self.now)
        claim = board_scheduler.claim_due_board(str(self.db_path), excluded_sources={"greenhouse", "ashby", "darwinbox", "keka", "lever", "smartrecruiters", "workable"}, at=self.now)
        self.assertEqual(claim["source"], "workday")
        board_scheduler.finish_poll(
            str(self.db_path), claim, outcome="failed", error_type="HTTPError",
            at=self.now + dt.timedelta(seconds=10),
        )
        row = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["source"] == "workday")
        self.assertEqual(row["consecutive_failures"], 1)
        self.assertEqual(row["last_outcome"], "failed")
        # The backoff is 60 seconds; another provider on a different host can
        # still be claimed immediately.
        other = board_scheduler.claim_due_board(str(self.db_path), excluded_sources={"workday"}, at=self.now + dt.timedelta(seconds=11))
        self.assertIsNotNone(other)
        self.assertNotEqual(other["host_key"], claim["host_key"])
        self.assertIsNone(board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources={"greenhouse", "ashby", "lever", "smartrecruiters", "workable", "keka", "darwinbox"},
            at=self.now + dt.timedelta(seconds=69),
        ))
        retry = board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources={"greenhouse", "ashby", "lever", "smartrecruiters", "workable", "keka", "darwinbox"},
            at=self.now + dt.timedelta(seconds=71),
        )
        self.assertEqual(retry["source"], "workday")

    def test_429_persists_host_cooldown_and_respects_retry_after(self):
        board_scheduler.sync_config(str(self.db_path), self.config(), self.now)
        claim = board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources={"greenhouse", "ashby", "darwinbox", "keka", "lever", "smartrecruiters", "workable"}, at=self.now,
        )
        finished = self.now + dt.timedelta(seconds=5)
        result = board_scheduler.finish_poll(
            str(self.db_path), claim, outcome="rate_limited", cooldown_seconds=600, at=finished,
        )
        self.assertEqual(result["host_cooldown_until"], (finished + dt.timedelta(seconds=600)).isoformat())
        self.assertIsNone(board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources={"greenhouse", "ashby", "darwinbox", "keka", "lever", "smartrecruiters", "workable"},
            at=finished + dt.timedelta(seconds=599),
        ))
        retry = board_scheduler.claim_due_board(
            str(self.db_path), excluded_sources={"greenhouse", "ashby", "darwinbox", "keka", "lever", "smartrecruiters", "workable"},
            at=finished + dt.timedelta(seconds=601),
        )
        self.assertEqual(retry["host_key"], claim["host_key"])

    def test_host_cooldown_on_one_tenant_does_not_pause_same_provider_other_host(self):
        config = self.config()
        config["source_enabled"] = {"workday": True}
        config["workday_boards"] = [
            {"url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", "company": "NVIDIA"},
            {"url": "https://acme.wd3.myworkdayjobs.com/External", "company": "Acme"},
        ]
        board_scheduler.sync_config(str(self.db_path), config, self.now)
        first = board_scheduler.claim_due_board(str(self.db_path), at=self.now)
        self.assertEqual(first["source"], "workday")
        board_scheduler.finish_poll(
            str(self.db_path), first, outcome="rate_limited", cooldown_seconds=600,
            at=self.now + dt.timedelta(seconds=1),
        )
        # The other Workday employer uses a different myworkdayjobs API host;
        # only the throttled host is paused.
        second = board_scheduler.claim_due_board(str(self.db_path), at=self.now + dt.timedelta(seconds=2))
        self.assertEqual(second["source"], "workday")
        self.assertNotEqual(first["host_key"], second["host_key"])
        self.assertNotEqual(second["board_key"], first["board_key"])

    def test_sync_deactivates_removed_or_disabled_board_without_deleting_history(self):
        config = self.config()
        board_scheduler.sync_config(str(self.db_path), config, self.now)
        config["source_enabled"]["workday"] = False
        board_scheduler.sync_config(str(self.db_path), config, self.now + dt.timedelta(seconds=1))
        status = board_scheduler.status(str(self.db_path))
        self.assertEqual(status["active_boards"], 8)
        self.assertEqual(status["inactive_boards"], 1)
        workday = next(item for item in status["boards"] if item["source"] == "workday")
        self.assertEqual(workday["is_active"], 0)
        self.assertEqual(workday["board_key"], "nvidia:nvidiaexternalcareersite")

    def test_registry_reactivation_restarts_baseline_and_due_time(self):
        config = self.config()
        config["greenhouse_boards"] = [{"token": "alpha", "company": "Alpha", "registry_id": 7}]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO ats_board_registry(id,baseline_pending,review_status) VALUES(7,1,'active')")
        board_scheduler.sync_config(str(self.db_path), config, self.now)
        claim = board_scheduler.claim_due_board(str(self.db_path), at=self.now)
        board_scheduler.finish_poll(str(self.db_path), claim, outcome="success", at=self.now + dt.timedelta(seconds=1))
        config["source_enabled"]["greenhouse"] = False
        board_scheduler.sync_config(str(self.db_path), config, self.now + dt.timedelta(seconds=2))
        config["source_enabled"]["greenhouse"] = True
        board_scheduler.sync_config(str(self.db_path), config, self.now + dt.timedelta(seconds=3))
        row = next(item for item in board_scheduler.status(str(self.db_path))["boards"] if item["source"] == "greenhouse")
        self.assertEqual(row["is_active"], 1)
        self.assertEqual(row["baseline_pending"], 1)
        self.assertEqual(row["next_due_at"], (self.now + dt.timedelta(seconds=3)).isoformat())


if __name__ == "__main__":
    unittest.main()
