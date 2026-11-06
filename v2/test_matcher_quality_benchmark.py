"""Tests for the anonymized matcher quality seed benchmark."""

import unittest

from v2.matcher_quality_benchmark import run_benchmark


class MatcherQualityBenchmarkTests(unittest.TestCase):
    def test_seed_cases_match_provisional_positive_and_negative_labels(self):
        report = run_benchmark()
        summary = report["summary"]

        self.assertEqual(report["annotation_status"], "provisional_seed_review")
        self.assertEqual(summary["case_count"], 5)
        self.assertEqual(summary["scored_case_count"], 4)
        self.assertEqual(summary["review_case_count"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["passed"], 4)

    def test_description_mismatch_is_visible_but_excluded_from_precision_score(self):
        report = run_benchmark()
        cases = {item["case_id"]: item for item in report["results"]}
        mismatch = cases["naukri_python_title_description_mismatch_01"]

        self.assertTrue(mismatch["review_required"])
        self.assertEqual(mismatch["status"], "review_required")
        self.assertTrue(mismatch["actual_match"])
        self.assertEqual(mismatch["score"], 88)
        self.assertEqual(report["summary"]["review_cases_currently_matching"], 1)


if __name__ == "__main__":
    unittest.main()
