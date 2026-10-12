"""Tests for the read-only Greenhouse canary utility."""
import unittest
from unittest.mock import Mock

from v2.greenhouse_canary import build_report, run_canary


def job(source_id, posted_at=None):
    return {
        "source_job_id": source_id,
        "source_posted_at": posted_at,
    }


class GreenhouseCanaryTests(unittest.TestCase):
    def test_report_compares_unique_ids_and_timestamp_coverage(self):
        first = [job("gh-demo-1", "2026-10-10T10:00:00+00:00"), job("gh-demo-2")]
        second = [
            job("gh-demo-1", "2026-10-10T10:00:00+00:00"),
            job("gh-demo-3"),
            job("gh-demo-3"),
        ]

        report = build_report(first, second)

        self.assertEqual(report["polls"], 2)
        self.assertEqual(report["first_poll_jobs"], 2)
        self.assertEqual(report["second_poll_jobs"], 3)
        self.assertEqual(report["first_poll_unique_ids"], 2)
        self.assertEqual(report["second_poll_unique_ids"], 2)
        self.assertEqual(report["stable_ids"], 1)
        self.assertEqual(report["new_ids_on_second_poll"], 1)
        self.assertEqual(report["missing_ids_on_second_poll"], 1)
        self.assertEqual(
            report["second_poll_published_timestamp_coverage"],
            {"with_timestamp": 1, "unknown_timestamp": 2},
        )
        self.assertEqual(report["database_writes"], 0)
        self.assertFalse(report["matching_executed"])
        self.assertFalse(report["notifications_sent"])

    def test_run_canary_collects_twice_and_sleeps_between_polls(self):
        first = [job("gh-demo-1")]
        second = [job("gh-demo-1"), job("gh-demo-2")]
        collect = Mock(side_effect=[first, second])
        sleep = Mock()

        report = run_canary(" demo ", " Demo Company ", 75, collect, sleep)

        self.assertEqual(collect.call_count, 2)
        collect.assert_any_call("demo", "Demo Company")
        sleep.assert_called_once_with(75)
        self.assertEqual(report["new_ids_on_second_poll"], 1)

    def test_run_canary_rejects_short_interval_before_network_call(self):
        collect = Mock()
        with self.assertRaisesRegex(ValueError, "at least 60"):
            run_canary("demo", "Demo Company", 59, collect, Mock())
        collect.assert_not_called()

    def test_run_canary_rejects_blank_board_details(self):
        collect = Mock()
        with self.assertRaisesRegex(ValueError, "non-empty"):
            run_canary(" ", "Demo Company", 60, collect, Mock())
        collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
