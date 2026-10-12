import json
import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from v2 import gemini_extractor as gemini


class GeminiValidationTests(unittest.TestCase):
    def setUp(self):
        self.description = "Required experience: 4-6 years of professional experience. Python and FastAPI are required."
        self.payload = {
            "experience_min_years": 4,
            "experience_max_years": 6,
            "experience_type": "required",
            "experience_evidence": "4-6 years of professional experience",
            "required_skills": ["Python", "FastAPI", "Python"],
            "preferred_skills": ["Kubernetes"],
            "confidence": 0.94,
        }

    def test_validates_and_deduplicates_skills(self):
        result = gemini._validate_result(self.payload, self.description)
        self.assertEqual(result["experience_min_years"], 4.0)
        self.assertEqual(result["experience_max_years"], 6.0)
        self.assertEqual(result["required_skills"], ["Python", "FastAPI"])
        self.assertEqual(result["experience_evidence"], self.payload["experience_evidence"])

    def test_rejects_inverted_experience_range(self):
        with self.assertRaisesRegex(ValueError, "invalid_experience_range"):
            gemini._validate_result({**self.payload, "experience_min_years": 7}, self.description)

    def test_rejects_implausible_experience(self):
        with self.assertRaisesRegex(ValueError, "invalid_experience_value"):
            gemini._validate_result({**self.payload, "experience_max_years": 100}, self.description)

    def test_unverifiable_evidence_is_removed(self):
        result = gemini._validate_result({**self.payload, "experience_evidence": "10 years guaranteed"}, self.description)
        self.assertIsNone(result["experience_evidence"])

    def test_skips_when_feature_disabled_without_network(self):
        with TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"GEMINI_EXTRACTION_ENABLED": "false", "GEMINI_API_KEY": "not-used"}):
                with patch.object(gemini.requests, "post") as request:
                    result = gemini.shadow_extract_jobs(
                        [{"source": "naukri", "source_job_id": "1", "title": "Engineer", "description": self.description}],
                        Path(tmp) / "jobs.db",
                        experience_known=lambda job: False,
                        configured_skills=["Python"],
                    )
                    request.assert_not_called()
                    self.assertEqual(result["called"], 0)

    def test_shadow_call_caches_result_and_does_not_mutate_job(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            job = {
                "source": "naukri", "source_job_id": "1", "title": "Software Engineer",
                "company": "Example", "description": self.description,
            }
            mock_response = type("Response", (), {
                "status_code": 200,
                "json": lambda self: {"candidates": [{"content": {"parts": [{"text": json.dumps(self_payload)}] }]},
            })()
            self_payload = self.payload
            with patch.dict(os.environ, {
                "GEMINI_EXTRACTION_ENABLED": "true",
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL": "gemini-test",
                "GEMINI_MAX_CALLS_PER_RUN": "3",
                "GEMINI_MAX_CALLS_PER_DAY": "20",
            }):
                with patch.object(gemini.requests, "post", return_value=mock_response) as request:
                    before = dict(job)
                    first = gemini.shadow_extract_jobs([job], db_path, experience_known=lambda item: False, configured_skills=["Python"])
                    second = gemini.shadow_extract_jobs([job], db_path, experience_known=lambda item: False, configured_skills=["Python"])
                    request.assert_called_once()
                    self.assertEqual(first["called"], 1)
                    self.assertEqual(second["cached"], 1)
                    self.assertEqual(job, before)
            with sqlite3.connect(db_path) as conn:
                row = conn.execute("SELECT status, result_json FROM gemini_shadow_cache").fetchone()
            self.assertEqual(row[0], "ok")
            self.assertEqual(json.loads(row[1])["experience_max_years"], 6.0)


if __name__ == "__main__":
    unittest.main()
