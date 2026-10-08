import unittest

from unittest.mock import patch

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

import v2.radar as radar
from v2.dedupe import auto_link_allowed, canonical_match_score, canonicalize_url, normalize_company, normalize_location
from v2.radar import (
    _merge_config,
    alertability_details,
    current_day_start_utc,
    extract_experience,
    match_details,
    normalize_job,
    upsert_jobs,
)
from v2.telegram import _format_timestamp, format_notification, send_message


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

    def test_software_development_engineer_variant_matches(self):
        config = {
            **BASE_CONFIG,
            "require_explicit_experience_for_alerts": False,
        }
        details = match_details(
            make_job(
                "Software Development Engineer 2",
                "",
                "Bengaluru, Karnataka, India",
            ),
            config,
        )
        self.assertTrue(details["match"])
        self.assertGreaterEqual(details["score"], 55)
        self.assertIn("software engineer", " ".join(details["reasons"]).lower())

    def test_javascript_developer_matches_from_skill_plus_title(self):
        config = {
            **BASE_CONFIG,
            "target_roles": ["software engineer", "software developer"],
            "skills": ["javascript", "python"],
            "require_explicit_experience_for_alerts": False,
        }
        details = match_details(
            make_job(
                "Javascript Developer",
                "",
                "Delhi, India",
            ),
            {
                **config,
                "locations": ["Delhi, India"],
            },
        )
        self.assertTrue(details["match"])
        self.assertGreaterEqual(details["score"], 55)
        self.assertIn("javascript", " ".join(details["reasons"]).lower())

    def test_unknown_experience_does_not_block_direct_role_match(self):
        config = {
            **BASE_CONFIG,
            "require_explicit_experience_for_alerts": False,
        }
        details = match_details(
            make_job(
                "Software Engineer",
                "",
                "Bengaluru, Karnataka, India",
            ),
            config,
        )
        self.assertTrue(details["match"])
        self.assertGreaterEqual(details["score"], 55)
        self.assertIn(
            "experience not stated",
            " ".join(details["reasons"]).lower(),
        )

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

    def test_jd_experience_extraction_prefers_experience_text(self):
        jd = """
        Job Qualifications
        Mandatory Skills
        5+ years of full-time software development experience as a Python Developer.
        Expertise in FASTAPI Python framework.
        """
        self.assertEqual(radar.extract_jd_experience(jd), (5.0, None))

    def test_jd_enrichment_is_applied_before_notification_decision(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()

                job = normalize_job(
                    "linkedin",
                    "li-jd-flow",
                    "NTT DATA North America",
                    "Z3_Python developer",
                    "Bangalore Urban, Karnataka, India",
                    "https://in.linkedin.com/jobs/view/z3-python-developer",
                    None,
                    "minute",
                    "Z3_Python developer NTT DATA North America Bangalore",
                )
                job["needs_jd_enrichment"] = True

                class Response:
                    status_code = 200
                    text = """
                    <html><body><main>
                    Job Qualifications
                    Mandatory Skills
                    5+ years of full-time software development experience as a Python Developer.
                    Expertise in FASTAPI Python framework.
                    </main></body></html>
                    """

                with patch.object(radar.requests, "get", return_value=Response()):
                    self.assertEqual(radar.upsert_jobs([job], BASE_CONFIG), 1)

                radar.refresh_notification_decisions(BASE_CONFIG)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT e.match, e.alertable,
                               e.experience_min_years, e.experience_max_years
                        FROM job_evaluations e
                        WHERE e.job_id=1
                    """).fetchone()

                    notification = conn.execute("""
                        SELECT status
                        FROM notification_ledger
                        WHERE canonical_opportunity_id=(
                            SELECT canonical_opportunity_id
                            FROM jobs WHERE id=1
                        )
                    """).fetchone()

                self.assertEqual(row[0], 0)
                self.assertEqual(row[1], 0)
                self.assertEqual(row[2], 5.0)
                self.assertIsNone(row[3])
                self.assertEqual(notification[0], "suppressed")
            finally:
                radar.DB_PATH = original_db

    def test_new_linkedin_job_is_enriched_from_jd_before_matching(self):
        job = normalize_job(
            "linkedin",
            "li-jd",
            "NTT DATA North America",
            "Z3_Python developer",
            "Bangalore Urban, Karnataka, India",
            "https://in.linkedin.com/jobs/view/z3-python-developer",
            None,
            "minute",
            "Z3_Python developer NTT DATA North America Bengaluru",
        )

        class Response:
            status_code = 200
            text = """
            <html><body>
            <main>
            Job Qualifications
            Mandatory Skills
            5+ years of full-time software development experience as a Python Developer.
            Expertise in FASTAPI Python framework.
            </main>
            </body></html>
            """

        with patch.object(radar.requests, "get", return_value=Response()):
            enriched = radar.enrich_linkedin_job(job)

        self.assertIn("JD:", enriched["description"])
        self.assertEqual(
            radar.extract_experience(enriched["description"]),
            (5.0, None),
        )

        result = match_details(enriched, BASE_CONFIG)
        self.assertFalse(result["match"])
        self.assertIn("experience minimum 5 exceeds candidate 2 years", result["reasons"][0])
    def test_existing_job_keeps_original_discovery_latency(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()

                first = radar.normalize_job(
                    "linkedin", "li-latency", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/latency", 
                    radar.now() - timedelta(minutes=10), "minute",
                    "2 years experience",
                )
                first_discovery = first["discovered_at"]
                first_latency = first["discovery_latency_seconds"]

                self.assertEqual(radar.upsert_jobs([first], BASE_CONFIG), 1)

                second = dict(first)
                second["discovered_at"] = radar.iso(radar.now())
                second["source_posted_at"] = radar.iso(radar.now() - timedelta(minutes=1))
                second["discovery_latency_seconds"] = 60

                self.assertEqual(radar.upsert_jobs([second], BASE_CONFIG), 0)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT discovered_at, discovery_latency_seconds FROM jobs WHERE id=1"
                    ).fetchone()

                self.assertEqual(row[0], first_discovery)
                self.assertEqual(row[1], first_latency)
            finally:
                radar.DB_PATH = original_db


    def test_daily_reset_uses_ist_midnight(self):
        start = current_day_start_utc()
        local = start.astimezone(radar.IST)
        self.assertEqual(local.hour, 0)
        self.assertEqual(local.minute, 0)
        self.assertEqual(local.second, 0)

    def test_telegram_timestamp_is_human_readable_ist(self):
        self.assertEqual(
            _format_timestamp("2026-10-08T07:30:50.260596+00:00"),
            "08 Oct 2026, 1:00 PM IST",
        )

    def test_telegram_message_format_contains_core_fields(self):
        item = {
            "score": 88,
            "title": "Software Engineer - AI",
            "company": "Acme",
            "location": "Bengaluru",
            "source": "linkedin",
            "source_posted_at": "2026-10-08T07:00:00+00:00",
            "posted_precision": "minute",
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

    def test_naukri_notification_preserves_date_precision_and_experience(self):
        item = {
            "score": 66,
            "title": "React Developer",
            "company": "Senniper Technologies India",
            "location": "Gurugram, India",
            "source": "naukri",
            "source_posted_at": "2026-10-08T00:00:00+00:00",
            "posted_precision": "date",
            "discovered_at": "2026-10-08T09:00:00+00:00",
            "experience_min_years": 2,
            "experience_max_years": 4,
            "url": "https://www.naukri.com/job-listings/example",
            "match_reasons_json": "[\"react\", \"node.js\", \"location fit\", \"experience fit\"]",
        }

        message = format_notification(item)

        self.assertIn("Posted: 08 Oct 2026 (date only)", message)
        self.assertNotIn("Posted: 08 Oct 2026, 12:00 AM IST", message)
        self.assertIn("🧾 Experience: 2-4", message)
        self.assertIn("Source: naukri", message)
        self.assertIn("React Developer", message)

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

    def test_rejected_new_opportunity_is_suppressed(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-rejected", "Acme", "Senior Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/rejected", None,
                    "unknown", "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                self.assertEqual(radar.refresh_notification_decisions(BASE_CONFIG), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT status, decision_reason_json FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(row[0], "suppressed")
                self.assertIn("no profile-matching observation", row[1])
            finally:
                radar.DB_PATH = original_db

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

    def test_queued_opportunity_reverts_to_pending_when_alertability_is_lost(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()

                relaxed = {
                    **BASE_CONFIG,
                    "require_explicit_experience_for_alerts": False,
                }

                job = normalize_job(
                    "linkedin", "li-queue-revalidate", "Acme", "AI Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/revalidate", None,
                    "unknown", "Build AI systems with Python.",
                )

                self.assertEqual(upsert_jobs([job], relaxed), 1)
                self.assertEqual(
                    radar.refresh_notification_decisions(relaxed),
                    1,
                )

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT status, candidate_job_id
                        FROM notification_ledger
                    """).fetchone()

                self.assertEqual(row[0], "queued")
                self.assertEqual(row[1], 1)

                self.assertEqual(
                    radar.refresh_job_evaluations(BASE_CONFIG),
                    1,
                )
                self.assertEqual(
                    radar.refresh_notification_decisions(BASE_CONFIG),
                    1,
                )

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT status, candidate_job_id
                        FROM notification_ledger
                    """).fetchone()

                self.assertEqual(row[0], "pending")
                self.assertIsNone(row[1])
            finally:
                radar.DB_PATH = original_db

    def test_new_observation_reactivates_suppressed_alertable_opportunity(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()

                shared_url = "https://example.com/jobs/software-engineer"

                old_job = normalize_job(
                    "linkedin",
                    "li-old",
                    "Acme",
                    "Senior Software Engineer",
                    "Bengaluru",
                    shared_url,
                    None,
                    "unknown",
                    "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([old_job], BASE_CONFIG), 1)
                self.assertEqual(
                    radar.refresh_notification_decisions(BASE_CONFIG),
                    1,
                )

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT status, canonical_opportunity_id
                        FROM notification_ledger
                    """).fetchone()

                self.assertEqual(row[0], "suppressed")
                original_canonical_id = row[1]

                new_job = normalize_job(
                    "naukri",
                    "nk-new",
                    "Acme",
                    "Software Engineer",
                    "Bengaluru",
                    shared_url,
                    None,
                    "unknown",
                    "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([new_job], BASE_CONFIG), 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT canonical_opportunity_id
                        FROM jobs
                        WHERE source='naukri' AND source_job_id='nk-new'
                    """).fetchone()

                self.assertEqual(row[0], original_canonical_id)

                changed = radar.refresh_notification_decisions(BASE_CONFIG)
                self.assertEqual(changed, 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute("""
                        SELECT status, candidate_job_id
                        FROM notification_ledger
                        WHERE canonical_opportunity_id=?
                    """, (original_canonical_id,)).fetchone()

                self.assertEqual(row[0], "queued")
                self.assertIsNotNone(row[1])
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
            "config_version": 4,
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
            "config_version": 3,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": True,
            },
        }
        merged = _merge_config(defaults, legacy)
        self.assertEqual(merged["config_version"], 4)
        self.assertFalse(merged["source_enabled"]["instahyre"])

    def test_config_v5_repairs_persisted_source_queries(self):
        defaults = {
            "config_version": 5,
            "linkedin_queries": [
                "software engineer OR software developer",
                "full stack developer OR full stack engineer OR frontend developer OR frontend engineer OR backend developer OR backend engineer",
            ],
            "naukri_queries": ["software engineer", "full stack developer"],
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": False,
            },
            "poll_seconds": {
                "linkedin": 60,
                "naukri": 300,
                "instahyre": 600,
            },
        }
        prior_runtime = {
            "config_version": 4,
            "linkedin_queries": [
                "software engineer OR software developer",
                "full stack developer OR frontend developer OR backend developer",
            ],
            "naukri_queries": ["software engineer"],
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": True,
            },
        }
        merged = _merge_config(defaults, prior_runtime)
        self.assertEqual(merged["config_version"], 5)
        self.assertEqual(merged["linkedin_queries"], defaults["linkedin_queries"])
        self.assertEqual(merged["naukri_queries"], defaults["naukri_queries"])
        # V5 repairs source-query drift only; the V4 migration is responsible
        # for forcing legacy Instahyre enablement back to disabled.
        self.assertTrue(merged["source_enabled"]["instahyre"])

    def test_linkedin_fast_scan_uses_broader_recency_window(self):
        params = []
        class Response:
            status_code = 200
            text = """
            <html><body><ul>
              <li>
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/1234567890">Apply</a>
                <h3 class="base-search-card__title">Software Engineer</h3>
                <h4 class="base-search-card__subtitle">Acme</h4>
                <span class="job-search-card__location">Bengaluru, Karnataka, India</span>
                <time>30 minutes ago</time>
              </li>
            </ul></body></html>
            """
        def fake_request(_endpoint, request_params):
            params.append(dict(request_params))
            return Response()
        config = {
            **BASE_CONFIG,
            "linkedin_queries": ["software engineer"],
            "locations": ["Bengaluru, Karnataka, India"],
        }
        with patch.object(radar, "_linkedin_request", side_effect=fake_request):
            radar.linkedin_collect(config)
        self.assertTrue(params)
        self.assertEqual(params[0]["f_TPR"], "r21600")
        self.assertNotIn("f_EA", params[0])

    def test_config_v4_migrates_instahyre_to_disabled(self):
        defaults = {
            "config_version": 4,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": False,
            },
            "poll_seconds": {
                "linkedin": 60,
                "naukri": 300,
                "instahyre": 600,
            },
        }
        prior_runtime = {
            "config_version": 3,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": True,
            },
        }
        merged = _merge_config(defaults, prior_runtime)
        self.assertEqual(merged["config_version"], 4)
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

    def test_linkedin_fast_lane_and_periodic_deep_scan(self):
        original_state = radar.source_state
        radar.source_state = {}
        config = {
            **BASE_CONFIG,
            "linkedin_queries": ["ai engineer"],
            "locations": ["Bengaluru, Karnataka, India"],
        }
        calls = []
        params_seen = []

        class Response:
            status_code = 200
            text = """
            <html><body><ul>
              <li>
                <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/1234567890">Apply</a>
                <h3 class="base-search-card__title">AI Engineer</h3>
                <h4 class="base-search-card__subtitle">Acme</h4>
                <span class="job-search-card__location">Bengaluru, Karnataka, India</span>
                <time>1 minute ago</time>
                <span>2 years experience</span>
              </li>
            </ul></body></html>
            """

        def fake_request(_endpoint, params):
            calls.append(params["start"])
            params_seen.append(dict(params))
            return Response()

        try:
            with patch.object(radar, "_linkedin_request", side_effect=fake_request):
                first = radar.linkedin_collect(config)
                first_starts = sorted(calls)
                calls.clear()
                second = radar.linkedin_collect(config)
                second_starts = sorted(calls)

            self.assertEqual(len(first), 1)
            self.assertEqual(first_starts, [0, 10])
            fast = next(p for p in params_seen if p["start"] == 0)
            deep = next(p for p in params_seen if p["start"] == 10)
            self.assertEqual(fast["f_TPR"], radar.LINKEDIN_FAST_TPR)
            self.assertNotIn("f_EA", fast)
            self.assertEqual(deep["f_TPR"], radar.LINKEDIN_DEEP_TPR)
            self.assertNotIn("f_EA", deep)
            self.assertEqual(len(second), 1)
            self.assertEqual(second_starts, [0])
        finally:
            radar.source_state = original_state



    def test_jd_experience_extraction_handles_overall_experience_range(self):
        jd = """
        What You Need to Succeed:
        5 to 7 years of overall software engineering experience.
        Minimum Bachelor's degree.
        """
        self.assertEqual(
            radar.extract_jd_experience(jd),
            (5.0, 7.0),
        )

    def test_linkedin_detail_prefers_experience_bearing_candidate(self):
        class Response:
            status_code = 200
            text = """
            <html>
              <head>
                <script type="application/ld+json">
                {
                  "@context": "https://schema.org",
                  "@type": "JobPosting",
                  "description": "5 to 7 years of overall software engineering experience."
                }
                </script>
              </head>
              <body>
                <div class="description__text">Build great products.</div>
              </body>
            </html>
            """

        with patch.object(radar.requests, "get", return_value=Response()):
            detail = radar._linkedin_job_description(
                "https://www.linkedin.com/jobs/view/full-stack-developer-4477150767"
            )

        self.assertIn(
            "5 to 7 years of overall software engineering experience",
            detail,
        )

    def test_linkedin_enrichment_captures_overall_experience_range(self):
        job = normalize_job(
            "linkedin",
            "li-blueoptima",
            "BlueOptima",
            "Full Stack Developer",
            "Bengaluru, Karnataka, India",
            "https://www.linkedin.com/jobs/view/full-stack-developer-4477150767",
            None,
            "minute",
            "Full Stack Developer BlueOptima Bengaluru",
        )

        class Response:
            status_code = 200
            text = """
            <html><body>
            <div class="description__text">
              Responsibilities and qualifications.
              5 to 7 years of overall software engineering experience.
              At least 2 years of web UI development experience.
            </div>
            </body></html>
            """

        with patch.object(radar.requests, "get", return_value=Response()):
            enriched = radar.enrich_linkedin_job(job)

        self.assertEqual(enriched["jd_experience_min_years"], 5.0)
        self.assertEqual(enriched["jd_experience_max_years"], 7.0)
        self.assertIn(
            "5 to 7 years of overall software engineering experience",
            enriched["description"],
        )

    def test_jobs_today_only_filters_before_ist_midnight(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                day_start = radar.current_day_start_utc()

                old_job = normalize_job(
                    "linkedin",
                    "li-old-day",
                    "Acme",
                    "Software Engineer",
                    "Bengaluru",
                    "https://linkedin.com/jobs/view/old-day",
                    day_start - timedelta(minutes=30),
                    "minute",
                    "2 years experience",
                )
                new_job = normalize_job(
                    "linkedin",
                    "li-new-day",
                    "Acme",
                    "Software Engineer",
                    "Bengaluru",
                    "https://linkedin.com/jobs/view/new-day",
                    day_start + timedelta(minutes=30),
                    "minute",
                    "2 years experience",
                )

                # The daily lifecycle is based on discovery time, not source
                # posting time. Move discoveries across the IST-midnight cut.
                old_job["discovered_at"] = radar.iso(
                    day_start - timedelta(minutes=30)
                )
                new_job["discovered_at"] = radar.iso(
                    day_start + timedelta(minutes=30)
                )

                config = {
                    **BASE_CONFIG,
                    "require_explicit_experience_for_alerts": False,
                }

                self.assertEqual(
                    upsert_jobs([old_job, new_job], config),
                    2,
                )

                result = radar.jobs(today_only=True, limit=100)
                ids = {row["source_job_id"] for row in result["jobs"]}

                self.assertNotIn("li-old-day", ids)
                self.assertIn("li-new-day", ids)

                opportunity_result = radar.opportunities(
                    today_only=True,
                    limit=100,
                )
                representative_ids = {
                    row["representative_job_id"]
                    for row in opportunity_result["opportunities"]
                }

                self.assertNotIn(1, representative_ids)
                self.assertIn(2, representative_ids)
            finally:
                radar.DB_PATH = original_db


if __name__ == "__main__":
    unittest.main()
