import unittest

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

import v2.radar as radar
from v2.dedupe import auto_link_allowed, canonical_match_score, canonicalize_url, normalize_company, normalize_location
from v2.radar import _merge_config, alertability_details, extract_experience, match_details, normalize_job, upsert_jobs
from v2.telegram import format_notification, send_message


BASE_CONFIG = {
    "target_roles": ["software engineer", "ai engineer", "automation engineer"],
    "skills": ["python", "react", "ai"],
    "locations": ["Bengaluru, Karnataka, India", "Remote, India"],
    "title_exclude": ["senior", "lead", "staff", "principal", "manager"],
    "excluded_role_terms": [],
    "candidate_experience_years": 2,
    "min_experience_years": None,
    "max_experience_years": 3,
    "match_threshold": 55,
    "remote_only": False,
    "require_explicit_experience_for_alerts": True,
    "notifications_enabled": True,
}


def make_job(title, description="", location="Bengaluru, India"):
    return {
        "title": title,
        "description": description,
        "location": location,
    }


class MatcherTests(unittest.TestCase):
    def test_database_links_strong_cross_source_duplicate(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                common = {
                    "company": "Acme Technologies Pvt Ltd",
                    "title": "Software Engineer - AI",
                    "location": "Bengaluru, Karnataka",
                    "url": "https://example.com/apply/123",
                    "description": "Build Python services. 0-2 years experience.",
                }
                first = normalize_job(
                    "linkedin", "li-1", common["company"], common["title"],
                    common["location"], common["url"], None, "unknown", common["description"],
                )
                second = normalize_job(
                    "naukri", "nk-1", "Acme Technologies", "Software Engineer AI",
                    "Bangalore", common["url"], None, "unknown",
                    "Build Python services. Experience: 0 to 2 years.",
                )
                self.assertEqual(upsert_jobs([first]), 1)
                self.assertEqual(upsert_jobs([second]), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    rows = conn.execute("""
                        SELECT source, canonical_opportunity_id
                        FROM jobs
                        ORDER BY id
                    """).fetchall()
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0][1], rows[1][1])
                ledger = conn.execute(
                    "SELECT count(*), min(status) FROM notification_ledger"
                ).fetchone()
                self.assertEqual(ledger[0], 1)
                self.assertEqual(ledger[1], "pending")
            finally:
                radar.DB_PATH = original_db

    def test_existing_jobs_can_be_backfilled_into_evaluation_state(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()

                job = normalize_job(
                    "linkedin", "li-1", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/1", None,
                    "unknown", "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([job]), 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("DELETE FROM job_evaluations")
                    conn.commit()

                count = radar.backfill_job_evaluations(BASE_CONFIG)
                self.assertEqual(count, 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT match, score, alertable
                        FROM job_evaluations
                        WHERE job_id=1
                    """).fetchone()

                self.assertIsNotNone(row)
                self.assertEqual(row[0], 1)
                self.assertGreaterEqual(row[1], 55)
                self.assertEqual(row[2], 1)
            finally:
                radar.DB_PATH = original_db

    def test_new_opportunity_gets_pending_notification_state(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-1", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/1", None,
                    "unknown", "same listing metadata",
                )
                self.assertEqual(upsert_jobs([job]), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("SELECT status FROM notification_ledger").fetchone()
                self.assertEqual(row[0], "pending")
            finally:
                radar.DB_PATH = original_db

    def test_telegram_message_format_contains_core_fields(self):
        item = {
            "score": 88,
            "title": "Software Engineer - AI",
            "company": "Acme",
            "location": "Bengaluru",
            "source": "linkedin",
            "source_posted_at": "2026-10-08T07:00:00+00:00",
            "discovered_at": "2026-10-08T07:05:00+00:00",
            "experience_min_years": 2,
            "experience_max_years": 3,
            "url": "https://example.com/apply/123",
            "match_reasons_json": "[\"role (title): software engineer\", \"skills: python, ai\"]",
        }
        message = format_notification(item)
        self.assertIn("88% MATCH", message)
        self.assertIn("Software Engineer - AI", message)
        self.assertIn("Acme", message)
        self.assertIn("Bengaluru", message)
        self.assertIn("Apply → https://example.com/apply/123", message)

    def test_telegram_send_success(self):
        original_post = __import__("v2.telegram", fromlist=["requests"]).requests.post
        class Response:
            status_code = 200
            def json(self):
                return {"ok": True, "result": {"message_id": 1}}
        module = __import__("v2.telegram", fromlist=["requests"])
        module.requests.post = lambda *args, **kwargs: Response()
        try:
            send_message("token", "chat", "hello")
        finally:
            module.requests.post = original_post

    def test_telegram_rejects_auth_error_without_retry(self):
        module = __import__("v2.telegram", fromlist=["requests"])
        original_post = module.requests.post
        class Response:
            status_code = 401
            def json(self):
                return {"ok": False, "description": "Unauthorized"}
        module.requests.post = lambda *args, **kwargs: Response()
        try:
            with self.assertRaises(Exception) as ctx:
                send_message("token", "chat", "hello")
            self.assertFalse(getattr(ctx.exception, "retryable", True))
        finally:
            module.requests.post = original_post

    def test_alertable_new_opportunity_moves_to_queue(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-queue", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/queue", None,
                    "unknown", "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                self.assertEqual(radar.refresh_notification_decisions(BASE_CONFIG), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT status, candidate_job_id FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(row[0], "queued")
                self.assertEqual(row[1], 1)
            finally:
                radar.DB_PATH = original_db

    def test_unknown_experience_new_opportunity_is_suppressed(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-unknown", "Acme", "AI Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/unknown", None,
                    "unknown", "Build AI systems with Python.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                self.assertEqual(radar.refresh_notification_decisions(BASE_CONFIG), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT status, decision_reason_json FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(row[0], "pending")
                self.assertIn("awaiting future re-evaluation", row[1])

                relaxed = {
                    **BASE_CONFIG,
                    "require_explicit_experience_for_alerts": False,
                }
                self.assertEqual(radar.refresh_job_evaluations(relaxed), 1)
                self.assertEqual(radar.refresh_notification_decisions(relaxed), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT status, candidate_job_id FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(row[0], "queued")
                self.assertEqual(row[1], 1)
            finally:
                radar.DB_PATH = original_db

    def test_config_change_re_evaluates_existing_jobs(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-config", "Acme", "AI Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/config", None,
                    "unknown", "Build AI systems with Python.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT alertable FROM job_evaluations WHERE job_id=1"
                    ).fetchone()
                self.assertEqual(row[0], 0)

                relaxed = {
                    **BASE_CONFIG,
                    "require_explicit_experience_for_alerts": False,
                }
                self.assertEqual(radar.refresh_job_evaluations(relaxed), 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT alertable FROM job_evaluations WHERE job_id=1"
                    ).fetchone()
                self.assertEqual(row[0], 1)
            finally:
                radar.DB_PATH = original_db

    def test_stale_alertable_opportunity_is_suppressed(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-stale", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/stale", None,
                    "unknown", "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    old = "2026-10-01T00:00:00+00:00"
                    conn.execute(
                        "UPDATE jobs SET source_posted_at=?, posted_precision=? WHERE id=1",
                        (old, "minute"),
                    )
                    conn.commit()
                self.assertEqual(radar.refresh_notification_decisions(BASE_CONFIG), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT status FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(row[0], "suppressed")
            finally:
                radar.DB_PATH = original_db

    def test_existing_opportunity_can_be_backfilled_as_suppressed(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-1", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/1", None,
                    "unknown", "same listing metadata",
                )
                self.assertEqual(upsert_jobs([job]), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("DELETE FROM notification_ledger")
                    conn.commit()
                radar.backfill_notification_ledger()
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("SELECT status FROM notification_ledger").fetchone()
                self.assertEqual(row[0], "suppressed")
            finally:
                radar.DB_PATH = original_db

    def test_same_source_distinct_listings_stay_separate(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                first = normalize_job(
                    "linkedin", "li-1", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/1", None,
                    "unknown", "same listing metadata",
                )
                second = normalize_job(
                    "linkedin", "li-2", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/2", None,
                    "unknown", "same listing metadata",
                )
                self.assertEqual(upsert_jobs([first, second]), 2)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    ids = [row[0] for row in conn.execute(
                        "SELECT canonical_opportunity_id FROM jobs ORDER BY id"
                    ).fetchall()]
                self.assertNotEqual(ids[0], ids[1])
            finally:
                radar.DB_PATH = original_db

    def test_database_keeps_ambiguous_duplicate_separate(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                first = normalize_job(
                    "linkedin", "li-1", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/1", None,
                    "unknown", "Be an early applicant",
                )
                second = normalize_job(
                    "naukri", "nk-1", "Acme", "Software Engineer",
                    "Bangalore", "https://naukri.com/job-listings/2", None,
                    "unknown", "Experience with distributed systems and APIs.",
                )
                self.assertEqual(upsert_jobs([first, second]), 2)
                with __import__("sqlite3").connect(radar.DB_PATH) as conn:
                    ids = [row[0] for row in conn.execute(
                        "SELECT canonical_opportunity_id FROM jobs ORDER BY id"
                    ).fetchall()]
                self.assertNotEqual(ids[0], ids[1])
            finally:
                radar.DB_PATH = original_db

    def test_canonical_url_normalization_removes_tracking(self):
        self.assertEqual(
            canonicalize_url("https://WWW.example.com/jobs/123/?utm_source=x&ref=abc&b=2&a=1"),
            "https://example.com/jobs/123?a=1&b=2",
        )

    def test_company_and_location_aliases_normalize(self):
        self.assertEqual(normalize_company("Acme Technologies Pvt. Ltd."), "acme technologies")
        self.assertEqual(normalize_location("Bengaluru, Karnataka"), "bangalore")
        self.assertEqual(normalize_location("Gurugram, Haryana"), "gurgaon")

    def test_cross_source_exact_experience_match_is_auto_linked(self):
        left = {
            "company": "Acme Technologies Pvt Ltd",
            "title": "Software Engineer - AI",
            "location": "Bengaluru, Karnataka",
            "url": "https://linkedin.com/jobs/view/123",
            "description": "Build Python services. 0-2 years experience.",
        }
        right = {
            "company": "Acme Technologies",
            "title": "Software Engineer AI",
            "location": "Bangalore",
            "url": "https://naukri.com/job-listings/456",
            "description": "Build Python services. Experience: 0 to 2 years.",
            "canonical_url": "",
        }
        score, method = canonical_match_score(left, right)
        self.assertGreaterEqual(score, 95)
        self.assertEqual(method, "metadata_experience")
        self.assertTrue(auto_link_allowed(score, method))

    def test_incompatible_experience_ranges_are_not_duplicate_candidates(self):
        left = {
            "company": "IBM",
            "title": "Application Developer-Java & Web Technologies",
            "location": "Bengaluru, Karnataka",
            "url": "https://linkedin.com/jobs/view/123",
            "description": "Application Developer-Java & Web Technologies. 2-4 years experience.",
        }
        right = {
            "company": "IBM",
            "title": "Application Developer-Java & Web Technologies",
            "location": "Bengaluru, India",
            "url": "https://naukri.com/job-listings/456",
            "description": "5 to 7 years experience.",
            "canonical_url": "",
        }
        score, method = canonical_match_score(left, right)
        self.assertEqual(score, 0)
        self.assertEqual(method, "none")
        self.assertFalse(auto_link_allowed(score, method))

    def test_same_company_title_location_without_corroboration_is_not_auto_linked(self):
        left = {
            "company": "Acme Technologies",
            "title": "Software Engineer",
            "location": "Bengaluru",
            "url": "https://linkedin.com/jobs/view/123",
            "description": "Be an early applicant",
        }
        right = {
            "company": "Acme Technologies",
            "title": "Software Engineer",
            "location": "Bangalore",
            "url": "https://naukri.com/job-listings/456",
            "description": "Experience with distributed systems and APIs.",
            "canonical_url": "",
        }
        score, method = canonical_match_score(left, right)
        self.assertEqual(score, 88)
        self.assertFalse(auto_link_allowed(score, method))

    def test_legacy_config_migrates_instahyre_to_opt_in(self):
        defaults = {
            "config_version": 3,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": False,
            },
            "poll_seconds": {
                "linkedin": 120,
                "naukri": 600,
                "instahyre": 600,
            },
        }
        legacy = {
            "config_version": 2,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": True,
            },
        }
        merged = _merge_config(defaults, legacy)
        self.assertEqual(merged["config_version"], 3)
        self.assertFalse(merged["source_enabled"]["instahyre"])

    def test_extracts_experience_range(self):
        self.assertEqual(extract_experience("0-2 years"), (0.0, 2.0))
        self.assertEqual(extract_experience("3 to 8 yrs"), (3.0, 8.0))

    def test_rejects_range_above_configured_maximum(self):
        result = match_details(
            make_job("Software Engineer", "Experience: 2-8 years"),
            BASE_CONFIG,
        )
        self.assertFalse(result["match"])
        self.assertEqual(result["experience_min_years"], 2.0)
        self.assertEqual(result["experience_max_years"], 8.0)

    def test_rejects_minimum_above_candidate(self):
        result = match_details(
            make_job("Software Engineer", "Experience: 3-5 years"),
            BASE_CONFIG,
        )
        self.assertFalse(result["match"])

    def test_skill_matching_is_phrase_aware(self):
        result = match_details(
            make_job("Software Engineer", "Maintain existing services."),
            {**BASE_CONFIG, "skills": ["ai"]},
        )
        self.assertNotIn("skills: ai", result["reasons"])

    def test_unknown_experience_can_match_but_is_not_alertable(self):
        result = match_details(
            make_job("AI Engineer", "Build AI systems with Python."),
            BASE_CONFIG,
        )
        self.assertTrue(result["match"])
        alert = alertability_details(make_job("AI Engineer", "Build AI systems with Python."), result, BASE_CONFIG)
        self.assertFalse(alert["alertable"])
        self.assertIn("explicit experience required for alerts", alert["reasons"])

    def test_excluded_role_category_is_configurable(self):
        config = {**BASE_CONFIG, "excluded_role_terms": ["quality assurance"]}
        result = match_details(
            make_job("Quality Assurance Automation Engineer", "2 years experience"),
            config,
        )
        self.assertFalse(result["match"])


if __name__ == "__main__":
    unittest.main()
