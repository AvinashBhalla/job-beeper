import json
import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from v2 import gemini_extractor as gemini
from v2 import radar


class GeminiValidationTests(unittest.TestCase):
    def setUp(self):
        self.description = "Required experience: 4-6 years of professional experience. Python and FastAPI are required. Build and maintain production APIs, collaborate with product teams, and write automated tests."
        self.payload = {
            "experience_min_years": 4,
            "experience_max_years": 6,
            "experience_type": "required",
            "experience_scope": "total_professional",
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

    def test_verbatim_evidence_survives_whitespace_line_wraps(self):
        description = "Required experience: 4-6 years of professional\n experience. Python and FastAPI are required."
        result = gemini._validate_result(self.payload, description)
        self.assertEqual(result["experience_evidence"], "4-6 years of professional experience")

    def test_prompt_requires_verbatim_evidence_and_conservative_scope(self):
        self.assertIn("exact, contiguous quote copied verbatim", gemini.PROMPT_PREFIX)
        self.assertIn('focus on Salesforce', gemini.PROMPT_PREFIX)
        self.assertIn("use unknown", gemini.PROMPT_PREFIX)

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
                "json": lambda self: {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": json.dumps(self_payload)}]
                            }
                        }
                    ]
                },
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


    def test_cached_matcher_experience_requires_required_overall_evidence(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            job = {
                "source": "naukri", "source_job_id": "safe-1",
                "title": "Software Engineer", "company": "Example",
                "description": self.description,
            }
            with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-test", "GEMINI_MATCHER_ENABLED": "true"}):
                with sqlite3.connect(db_path) as conn:
                    gemini._ensure_cache(conn)
                    conn.execute(
                        """INSERT INTO gemini_shadow_cache
                        (input_hash, source, source_job_id, title, status, result_json,
                         model, created_at, error_code)
                        VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, NULL)""",
                        (
                            gemini._input_hash(job), job["source"], job["source_job_id"],
                            job["title"], json.dumps(gemini._validate_result(self.payload, self.description)),
                            "gemini-test", gemini._iso(gemini._utc_now()),
                        ),
                    )
                    result = gemini.cached_matcher_experience(job, conn)
            self.assertEqual(result["experience_min_years"], 4.0)
            self.assertEqual(result["experience_max_years"], 6.0)
            self.assertEqual(result["experience_evidence"], self.payload["experience_evidence"])

    def test_cached_matcher_experience_rejects_unsafe_results(self):
        unsafe_payloads = [
            {**self.payload, "experience_type": "preferred"},
            {**self.payload, "experience_scope": "skill_specific"},
            {**self.payload, "confidence": 0.70},
            {**self.payload, "experience_evidence": None},
        ]
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-test", "GEMINI_MATCHER_ENABLED": "true"}):
                for index, payload in enumerate(unsafe_payloads):
                    job = {
                        "source": "naukri", "source_job_id": f"unsafe-{index}",
                        "title": "Software Engineer", "company": "Example",
                        "description": self.description,
                    }
                    with sqlite3.connect(db_path) as conn:
                        gemini._ensure_cache(conn)
                        conn.execute(
                            """INSERT INTO gemini_shadow_cache
                            (input_hash, source, source_job_id, title, status, result_json,
                             model, created_at, error_code)
                            VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, NULL)""",
                            (
                                gemini._input_hash(job), job["source"], job["source_job_id"],
                                job["title"], json.dumps(gemini._validate_result(payload, self.description)),
                                "gemini-test", gemini._iso(gemini._utc_now()),
                            ),
                        )
                        result = gemini.cached_matcher_experience(job, conn)
                    self.assertIsNone(result, msg=f"unsafe payload {index} was accepted")

    def test_persisted_job_evaluation_loads_trusted_gemini_experience(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            job = {
                "source": "naukri", "source_job_id": "integration-1",
                "company": "Example", "title": "Software Engineer",
                "location": "India", "url": "https://example.test/job/1",
                "source_posted_at": None, "posted_precision": "unknown",
                "discovered_at": "2026-10-13T10:00:00+00:00",
                "discovery_latency_seconds": None, "description": self.description,
                "first_seen_at": "2026-10-13T10:00:00+00:00",
                "last_seen_at": "2026-10-13T10:00:00+00:00",
                "canonical_opportunity_id": None, "canonical_match_method": None,
                "canonical_match_confidence": None,
            }
            with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-test", "GEMINI_MATCHER_ENABLED": "true"}):
                with sqlite3.connect(db_path) as conn:
                    conn.execute("""CREATE TABLE jobs (
                        id INTEGER PRIMARY KEY, source TEXT, source_job_id TEXT, company TEXT,
                        title TEXT, location TEXT, url TEXT, source_posted_at TEXT,
                        posted_precision TEXT, discovered_at TEXT, discovery_latency_seconds INTEGER,
                        description TEXT, first_seen_at TEXT, last_seen_at TEXT,
                        canonical_opportunity_id INTEGER, canonical_match_method TEXT,
                        canonical_match_confidence INTEGER
                    )""")
                    columns = ", ".join(job.keys())
                    placeholders = ", ".join("?" for _ in job)
                    conn.execute(
                        f"INSERT INTO jobs (id, {columns}) VALUES (?, {placeholders})",
                        (1, *job.values()),
                    )
                    gemini._ensure_cache(conn)
                    conn.execute(
                        """INSERT INTO gemini_shadow_cache
                        (input_hash, source, source_job_id, title, status, result_json,
                         model, created_at, error_code)
                        VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, NULL)""",
                        (
                            gemini._input_hash(job), job["source"], job["source_job_id"],
                            job["title"], json.dumps(gemini._validate_result(self.payload, self.description)),
                            "gemini-test", gemini._iso(gemini._utc_now()),
                        ),
                    )
                    loaded = radar._job_for_canonical(conn, 1)
            self.assertEqual(loaded["jd_experience_min_years"], 4.0)
            self.assertEqual(loaded["jd_experience_max_years"], 6.0)
            self.assertEqual(loaded["jd_experience_source"], "gemini_verified")


    def test_shadow_status_handles_malformed_cached_payload(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            malformed = {
                "experience_min_years": [],
                "experience_max_years": None,
                "experience_type": [],
                "experience_scope": {},
                "experience_evidence": ["not a quote"],
                "confidence": "invalid",
            }
            with sqlite3.connect(db_path) as conn:
                gemini._ensure_cache(conn)
                conn.execute(
                    """INSERT INTO gemini_shadow_cache
                    (input_hash, source, source_job_id, title, status, result_json,
                     model, created_at, error_code)
                    VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, NULL)""",
                    (
                        "malformed-hash", "naukri", "private-id",
                        "Private title", json.dumps(malformed), "gemini-test",
                        gemini._iso(gemini._utc_now()),
                    ),
                )

            with patch.dict(os.environ, {
                "GEMINI_EXTRACTION_ENABLED": "false",
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL": "gemini-test",
            }):
                status = gemini.shadow_status(db_path)

        sample = status["recent_results"][0]
        self.assertEqual(sample["experience_type"], "unknown")
        self.assertEqual(sample["experience_scope"], "unknown")
        self.assertIsNone(sample["experience_min_years"])
        self.assertIsNone(sample["confidence"])
        self.assertFalse(sample["experience_evidence_present"])
        self.assertFalse(sample["experience_shape_eligible"])

    def test_shadow_status_redacts_job_identity_and_raw_extraction(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            validated = gemini._validate_result(self.payload, self.description)
            with sqlite3.connect(db_path) as conn:
                gemini._ensure_cache(conn)
                conn.execute(
                    """INSERT INTO gemini_shadow_cache
                    (input_hash, source, source_job_id, title, status, result_json,
                     model, created_at, error_code)
                    VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, NULL)""",
                    (
                        "test-hash", "naukri", "private-job-id",
                        "Private job title", json.dumps(validated), "gemini-test",
                        gemini._iso(gemini._utc_now()),
                    ),
                )

            with patch.dict(os.environ, {
                "GEMINI_EXTRACTION_ENABLED": "false",
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL": "gemini-test",
                "GEMINI_MAX_CALLS_PER_DAY": "20",
            }):
                status = gemini.shadow_status(db_path)

        self.assertFalse(status["enabled"])
        self.assertTrue(status["api_key_configured"])
        self.assertEqual(len(status["recent_results"]), 1)
        sample = status["recent_results"][0]
        self.assertTrue(sample["experience_shape_eligible"])
        self.assertTrue(sample["experience_evidence_present"])
        self.assertEqual(sample["experience_min_years"], 4.0)
        self.assertEqual(sample["experience_max_years"], 6.0)

        for private_key in (
            "source", "source_job_id", "title", "result",
            "experience_evidence", "required_skills", "preferred_skills",
        ):
            self.assertNotIn(private_key, sample)
        serialized = json.dumps(status)
        self.assertNotIn("private-job-id", serialized)
        self.assertNotIn("Private job title", serialized)
        self.assertNotIn(self.payload["experience_evidence"], serialized)

    def test_shadow_status_reports_matcher_gate_without_database(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "missing.db"
            with patch.dict(os.environ, {
                "GEMINI_EXTRACTION_ENABLED": "false",
                "GEMINI_MATCHER_ENABLED": "false",
                "GEMINI_API_KEY": "",
                "GEMINI_MODEL": "gemini-test",
            }):
                disabled = gemini.shadow_status(db_path)
            with patch.dict(os.environ, {
                "GEMINI_EXTRACTION_ENABLED": "false",
                "GEMINI_MATCHER_ENABLED": "true",
                "GEMINI_API_KEY": "",
                "GEMINI_MODEL": "gemini-test",
            }):
                enabled = gemini.shadow_status(db_path)

        self.assertFalse(disabled["enabled"])
        self.assertFalse(disabled["matcher_enabled"])
        self.assertFalse(enabled["enabled"])
        self.assertTrue(enabled["matcher_enabled"])
        self.assertFalse(disabled["api_key_configured"] or enabled["api_key_configured"])


if __name__ == "__main__":
    unittest.main()
