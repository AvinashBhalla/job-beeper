import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from v2 import gemini_experience_diagnostic as diagnostic
from v2 import gemini_extractor as gemini
from v2 import radar


class GeminiExperienceDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "jobs.db"
        self.config = radar.validate_config(
            radar._merge_config(radar._default_config(), {})
        )
        self.description = (
            "Required experience: 4-6 years of professional experience. "
            "Python and FastAPI are required for production API development."
        )
        self.job = {
            "id": 1,
            "source": "naukri",
            "source_job_id": "diagnostic-test-job",
            "company": "Example Company",
            "title": self.config["target_roles"][0],
            "location": self.config["locations"][0],
            "url": "https://example.test/jobs/one",
            "source_posted_at": None,
            "posted_precision": "unknown",
            "discovered_at": gemini._iso(gemini._utc_now()),
            "discovery_latency_seconds": None,
            "description": self.description,
            "first_seen_at": gemini._iso(gemini._utc_now()),
            "last_seen_at": gemini._iso(gemini._utc_now()),
            "canonical_opportunity_id": None,
            "canonical_match_method": None,
            "canonical_match_confidence": None,
        }
        self.payload = {
            "experience_min_years": 4,
            "experience_max_years": 6,
            "experience_type": "required",
            "experience_scope": "total_professional",
            "experience_evidence": "4-6 years of professional experience",
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": [],
            "confidence": 0.95,
        }
        with sqlite3.connect(self.db_path) as conn:
            diagnostic._create_sandbox_schema(conn)
            self._insert_job(conn, self.job)

    def _insert_job(self, conn, job):
        columns = ", ".join(f'"{key}"' for key in diagnostic.JOB_COLUMNS)
        placeholders = ", ".join("?" for _ in diagnostic.JOB_COLUMNS)
        conn.execute(
            f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
            tuple(job.get(column) for column in diagnostic.JOB_COLUMNS),
        )

    def _insert_cache(self, *, payload=None, input_hash=None, created_at=None):
        payload = payload or self.payload
        validated = gemini._validate_result(payload, self.description)
        created_at = created_at or gemini._iso(gemini._utc_now())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO gemini_shadow_cache
                   (input_hash, source, source_job_id, title, status, result_json,
                    model, created_at, error_code)
                   VALUES (?, ?, ?, ?, 'ok', ?, ?, ?, NULL)""",
                (
                    input_hash or gemini._input_hash(self.job),
                    self.job["source"],
                    self.job["source_job_id"],
                    self.job["title"],
                    json.dumps(validated),
                    "gemini-test",
                    created_at,
                ),
            )

    def test_exact_fresh_trusted_result_uses_bridge_and_sandbox_persistence(self):
        self._insert_cache()

        result = diagnostic.diagnose_database(
            self.db_path, self.config, model="gemini-test"
        )

        self.assertEqual(result["diagnostic_status"], "candidate_verified")
        self.assertTrue(result["source_db_read_only"])
        self.assertFalse(result["source_db_modified"])
        self.assertTrue(result["exact_current_input_hash_match"])
        self.assertEqual(result["cache_status"], "ok")
        self.assertTrue(result["cache_model_matches"])
        self.assertEqual(result["experience_type"], "required")
        self.assertEqual(result["experience_scope"], "total_professional")
        self.assertTrue(result["verbatim_evidence_present"])
        self.assertGreaterEqual(result["confidence"], 0.85)
        self.assertTrue(result["experience_range_bound_present"])
        self.assertTrue(result["sandbox_bridge_source_verified"])
        self.assertTrue(result["sandbox_bridge_bounds_match_cache"])
        self.assertTrue(result["sandbox_evaluation_row_written"])
        self.assertTrue(result["sandbox_evaluation_bounds_match_cache"])
        self.assertTrue(result["sandbox_evaluation_experience_reason_present"])
        self.assertFalse(result["source_marker_in_job_evaluations_schema"])

        # The original DB is not written, even though the same persistence
        # function writes an evaluation row in the disposable sandbox DB.
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM job_evaluations").fetchone()[0]
        self.assertEqual(count, 0)

    def test_rejects_cache_for_mismatched_description_hash(self):
        changed_job = {**self.job, "description": self.description + " More text."}
        self._insert_cache(input_hash=gemini._input_hash(changed_job))

        result = diagnostic.diagnose_database(
            self.db_path, self.config, model="gemini-test"
        )

        self.assertEqual(result["diagnostic_status"], "not_verified")
        self.assertEqual(
            result["reason_code"], "no_fresh_trusted_exact_hash_candidate"
        )
        self.assertFalse(result["source_db_modified"])

    def test_rejects_expired_cache_entry(self):
        created = gemini._utc_now() - dt.timedelta(days=gemini.CACHE_TTL_DAYS + 1)
        self._insert_cache(created_at=gemini._iso(created))

        result = diagnostic.diagnose_database(
            self.db_path, self.config, model="gemini-test"
        )

        self.assertEqual(result["diagnostic_status"], "not_verified")
        self.assertEqual(
            result["reason_code"], "no_fresh_trusted_exact_hash_candidate"
        )

    def test_rejects_skill_specific_experience(self):
        self._insert_cache(payload={
            **self.payload,
            "experience_scope": "skill_specific",
        })

        result = diagnostic.diagnose_database(
            self.db_path, self.config, model="gemini-test"
        )

        self.assertEqual(result["diagnostic_status"], "not_verified")
        self.assertEqual(
            result["reason_code"], "no_fresh_trusted_exact_hash_candidate"
        )


if __name__ == "__main__":
    unittest.main()
