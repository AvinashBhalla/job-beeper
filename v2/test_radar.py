import unittest
import json

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

    def setUp(self):
        # These module-level values model a process-wide LinkedIn 429 cooldown.
        # Reset them between tests so a rate-limit test cannot make unrelated
        # collector tests order-dependent or flaky.
        self._linkedin_rate_state = (
            radar.linkedin_last_http_request_monotonic,
            radar.linkedin_rate_limited_until_monotonic,
            radar.linkedin_last_rate_limit_monotonic,
            radar.linkedin_rate_limit_streak,
            radar.linkedin_rate_limit_generation,
        )
        radar.linkedin_last_http_request_monotonic = 0.0
        radar.linkedin_rate_limited_until_monotonic = 0.0
        radar.linkedin_last_rate_limit_monotonic = 0.0
        radar.linkedin_rate_limit_streak = 0
        radar.linkedin_rate_limit_generation = 0

    def tearDown(self):
        (
            radar.linkedin_last_http_request_monotonic,
            radar.linkedin_rate_limited_until_monotonic,
            radar.linkedin_last_rate_limit_monotonic,
            radar.linkedin_rate_limit_streak,
            radar.linkedin_rate_limit_generation,
        ) = self._linkedin_rate_state

    def test_remote_india_location_does_not_match_remote_jobs_in_other_countries(self):
        self.assertTrue(radar.location_allowed("Remote - India", BASE_CONFIG))
        self.assertTrue(radar.location_allowed("Remote, Bengaluru, Karnataka, India", BASE_CONFIG))
        self.assertFalse(radar.location_allowed("Remote - USA", BASE_CONFIG))
        self.assertFalse(radar.location_allowed("Remote - Cyprus", BASE_CONFIG))

    def test_unqualified_remote_location_remains_global(self):
        config = {**BASE_CONFIG, "locations": ["Bengaluru, India", "Remote"]}
        self.assertTrue(radar.location_allowed("Remote - USA", config))

    def test_linkedin_fast_scan_staggers_all_query_location_pairs(self):
        config = {
            "locations": ["Bengaluru, India", "Gurugram, India", "Delhi, India", "Remote, India"],
            "linkedin_queries": ["software engineer", "automation engineer", "ai engineer", "react developer"],
        }
        original_deep_scan = radar.linkedin_last_deep_scan_at
        original_cursor = radar.linkedin_fast_target_cursor
        calls = []
        try:
            radar.linkedin_last_deep_scan_at = radar.iso(radar.now())
            radar.linkedin_fast_target_cursor = 0
            with patch.object(
                radar,
                "_linkedin_search_page",
                side_effect=lambda query, location, start, fast: (
                    calls.append((query, location, start, fast)) or []
                ),
            ):
                first_cycle = []
                cycles = []
                for cycle_index in range(8):
                    calls.clear()
                    radar.linkedin_collect(config)
                    cycle = list(calls)
                    cycles.append(cycle)
                    if cycle_index == 0:
                        first_cycle = cycle
            expected = {
                (query, location, 0, True)
                for query in config["linkedin_queries"]
                for location in config["locations"]
            }
            self.assertEqual(len(first_cycle), radar.LINKEDIN_FAST_TARGETS_PER_SCAN)
            for cycle in cycles:
                self.assertEqual(len(cycle), radar.LINKEDIN_FAST_TARGETS_PER_SCAN)
            observed = [target for cycle in cycles for target in cycle]
            self.assertEqual(set(observed), expected)
            self.assertEqual(len(observed), len(expected))
            for previous, current in zip(cycles, cycles[1:]):
                self.assertTrue(set(previous).isdisjoint(set(current)))
        finally:
            radar.linkedin_last_deep_scan_at = original_deep_scan
            radar.linkedin_fast_target_cursor = original_cursor

    def test_linkedin_http_429_honors_retry_after_and_blocks_followup_requests(self):
        original_state = {
            "last_request": radar.linkedin_last_http_request_monotonic,
            "until": radar.linkedin_rate_limited_until_monotonic,
            "last_rate": radar.linkedin_last_rate_limit_monotonic,
            "streak": radar.linkedin_rate_limit_streak,
            "generation": radar.linkedin_rate_limit_generation,
            "linkedin_source": dict(radar.source_state.get("linkedin", {})),
        }
        try:
            radar.linkedin_last_http_request_monotonic = 0.0
            radar.linkedin_rate_limited_until_monotonic = 0.0
            radar.linkedin_last_rate_limit_monotonic = 0.0
            radar.linkedin_rate_limit_streak = 0
            radar.linkedin_rate_limit_generation = 0

            class RateLimitedResponse:
                status_code = 429
                headers = {"Retry-After": "600"}

                def raise_for_status(self):
                    error = radar.requests.HTTPError("429 Client Error")
                    error.response = self
                    raise error

            with patch.object(
                radar.requests, "get", return_value=RateLimitedResponse()
            ) as request:
                with self.assertRaises(radar.requests.HTTPError):
                    radar._linkedin_http_get("https://www.linkedin.com/jobs-guest/test")
                with self.assertRaises(radar.LinkedInRateLimitCooldown):
                    radar._linkedin_http_get("https://www.linkedin.com/jobs-guest/test")

            self.assertEqual(request.call_count, 1)
            self.assertGreaterEqual(
                radar.linkedin_rate_limited_until_monotonic - radar.time.monotonic(),
                599,
            )
            self.assertEqual(radar.linkedin_rate_limit_streak, 1)
        finally:
            radar.linkedin_last_http_request_monotonic = original_state["last_request"]
            radar.linkedin_rate_limited_until_monotonic = original_state["until"]
            radar.linkedin_last_rate_limit_monotonic = original_state["last_rate"]
            radar.linkedin_rate_limit_streak = original_state["streak"]
            radar.linkedin_rate_limit_generation = original_state["generation"]
            if original_state["linkedin_source"]:
                radar.source_state["linkedin"] = original_state["linkedin_source"]
            else:
                radar.source_state.pop("linkedin", None)

    def test_linkedin_rate_limit_streak_escalates_across_successful_scans(self):
        original_state = {
            "deep_scan": radar.linkedin_last_deep_scan_at,
            "cursor": radar.linkedin_fast_target_cursor,
            "last_request": radar.linkedin_last_http_request_monotonic,
            "until": radar.linkedin_rate_limited_until_monotonic,
            "last_rate": radar.linkedin_last_rate_limit_monotonic,
            "streak": radar.linkedin_rate_limit_streak,
            "generation": radar.linkedin_rate_limit_generation,
            "linkedin_source": dict(radar.source_state.get("linkedin", {})),
        }
        try:
            radar.linkedin_last_deep_scan_at = radar.iso(radar.now())
            radar.linkedin_fast_target_cursor = 0
            radar.linkedin_last_http_request_monotonic = 0.0
            radar.linkedin_rate_limited_until_monotonic = 0.0
            radar.linkedin_last_rate_limit_monotonic = radar.time.monotonic() - 300
            radar.linkedin_rate_limit_streak = 1
            radar.linkedin_rate_limit_generation = 0
            config = {
                "locations": ["Bengaluru", "Gurugram", "Delhi", "Remote, India"],
                "linkedin_queries": ["software engineer", "python developer"],
            }

            with patch.object(radar, "_linkedin_search_page", return_value=[]):
                radar.linkedin_collect(config)

            # A successful scan must not erase a recent 429 streak.
            self.assertEqual(radar.linkedin_rate_limit_streak, 1)

            response = type("Response", (), {"status_code": 429, "headers": {}})()
            cooldown = radar._activate_linkedin_rate_limit(response)
            self.assertEqual(radar.linkedin_rate_limit_streak, 2)
            self.assertGreaterEqual(cooldown, 600)
        finally:
            radar.linkedin_last_deep_scan_at = original_state["deep_scan"]
            radar.linkedin_fast_target_cursor = original_state["cursor"]
            radar.linkedin_last_http_request_monotonic = original_state["last_request"]
            radar.linkedin_rate_limited_until_monotonic = original_state["until"]
            radar.linkedin_last_rate_limit_monotonic = original_state["last_rate"]
            radar.linkedin_rate_limit_streak = original_state["streak"]
            radar.linkedin_rate_limit_generation = original_state["generation"]
            if original_state["linkedin_source"]:
                radar.source_state["linkedin"] = original_state["linkedin_source"]
            else:
                radar.source_state.pop("linkedin", None)

    def test_linkedin_rate_limit_streak_resets_after_one_clean_hour(self):
        original_state = {
            "until": radar.linkedin_rate_limited_until_monotonic,
            "last_rate": radar.linkedin_last_rate_limit_monotonic,
            "streak": radar.linkedin_rate_limit_streak,
            "generation": radar.linkedin_rate_limit_generation,
            "linkedin_source": dict(radar.source_state.get("linkedin", {})),
        }
        try:
            radar.linkedin_rate_limited_until_monotonic = 0.0
            radar.linkedin_last_rate_limit_monotonic = radar.time.monotonic() - 3601
            radar.linkedin_rate_limit_streak = 3
            radar.linkedin_rate_limit_generation = 0
            response = type("Response", (), {"status_code": 429, "headers": {}})()

            cooldown = radar._activate_linkedin_rate_limit(response)

            self.assertEqual(radar.linkedin_rate_limit_streak, 1)
            self.assertGreaterEqual(cooldown, 300)
        finally:
            radar.linkedin_rate_limited_until_monotonic = original_state["until"]
            radar.linkedin_last_rate_limit_monotonic = original_state["last_rate"]
            radar.linkedin_rate_limit_streak = original_state["streak"]
            radar.linkedin_rate_limit_generation = original_state["generation"]
            if original_state["linkedin_source"]:
                radar.source_state["linkedin"] = original_state["linkedin_source"]
            else:
                radar.source_state.pop("linkedin", None)

    def test_linkedin_search_batch_stops_after_first_429(self):
        original_state = {
            "deep_scan": radar.linkedin_last_deep_scan_at,
            "cursor": radar.linkedin_fast_target_cursor,
            "last_request": radar.linkedin_last_http_request_monotonic,
            "until": radar.linkedin_rate_limited_until_monotonic,
            "streak": radar.linkedin_rate_limit_streak,
            "generation": radar.linkedin_rate_limit_generation,
            "linkedin_source": dict(radar.source_state.get("linkedin", {})),
        }
        try:
            radar.linkedin_last_deep_scan_at = radar.iso(radar.now())
            radar.linkedin_fast_target_cursor = 0
            radar.linkedin_last_http_request_monotonic = 0.0
            radar.linkedin_rate_limited_until_monotonic = 0.0
            radar.linkedin_rate_limit_streak = 0
            radar.linkedin_rate_limit_generation = 0

            response = type("Response", (), {"status_code": 429, "headers": {}})()
            error = radar.requests.HTTPError("429 Client Error")
            error.response = response
            config = {
                "locations": ["Bengaluru", "Gurugram", "Delhi", "Remote, India"],
                "linkedin_queries": ["software engineer", "python developer"],
            }

            with patch.object(
                radar, "_linkedin_search_page", side_effect=error
            ) as search:
                jobs = radar.linkedin_collect(config)

            self.assertEqual(jobs, [])
            search.assert_called_once()
            self.assertEqual(radar.linkedin_fast_target_cursor, 0)
            self.assertGreater(radar._linkedin_cooldown_remaining(), 0)
            self.assertEqual(radar.linkedin_rate_limit_streak, 1)
        finally:
            radar.linkedin_last_deep_scan_at = original_state["deep_scan"]
            radar.linkedin_fast_target_cursor = original_state["cursor"]
            radar.linkedin_last_http_request_monotonic = original_state["last_request"]
            radar.linkedin_rate_limited_until_monotonic = original_state["until"]
            radar.linkedin_rate_limit_streak = original_state["streak"]
            radar.linkedin_rate_limit_generation = original_state["generation"]
            if original_state["linkedin_source"]:
                radar.source_state["linkedin"] = original_state["linkedin_source"]
            else:
                radar.source_state.pop("linkedin", None)

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


    def test_normalize_job_rejects_posted_timestamp_after_discovery(self):
        from datetime import timedelta

        observed_at = radar.now()
        with patch.object(radar, "now", return_value=observed_at):
            job = normalize_job(
                "linkedin", "li-future-post", "Acme", "Software Engineer",
                "Bengaluru", "https://linkedin.com/jobs/view/future-post",
                observed_at + timedelta(minutes=5), "minute", "2 years experience",
            )

        self.assertIsNone(job["source_posted_at"])
        self.assertEqual(job["posted_precision"], "unknown")
        self.assertIsNone(job["discovery_latency_seconds"])

    def test_existing_job_does_not_backfill_post_time_after_first_discovery(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                first = normalize_job(
                    "linkedin", "li-late-metadata", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/late-metadata",
                    None, "unknown", "2 years experience",
                )
                self.assertEqual(upsert_jobs([first], BASE_CONFIG), 1)

                original_discovery = radar.parse_relative(first["discovered_at"])
                second = dict(first)
                with patch.object(
                    radar, "now",
                    return_value=original_discovery + timedelta(minutes=10),
                ):
                    second["discovered_at"] = radar.iso(radar.now())
                    second["source_posted_at"] = radar.iso(
                        original_discovery + timedelta(minutes=5)
                    )
                    second["posted_precision"] = "minute"
                    second["discovery_latency_seconds"] = 300
                    self.assertEqual(upsert_jobs([second], BASE_CONFIG), 0)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT source_posted_at, posted_precision FROM jobs WHERE id=1"
                    ).fetchone()
                self.assertIsNone(row[0])
                self.assertEqual(row[1], "unknown")
            finally:
                radar.DB_PATH = original_db

    def test_init_db_clears_legacy_post_times_after_discovery(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-legacy-future-post", "Acme", "Software Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/legacy-future-post",
                    radar.now() - timedelta(minutes=2), "minute", "2 years experience",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                invalid_posted_at = radar.iso(
                    radar.parse_relative(job["discovered_at"]) + timedelta(minutes=5)
                )
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute(
                        "UPDATE jobs SET source_posted_at=?, posted_precision='minute', "
                        "discovery_latency_seconds=0 WHERE id=1",
                        (invalid_posted_at,),
                    )
                    conn.commit()

                radar.init_db()
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT source_posted_at, posted_precision, discovery_latency_seconds "
                        "FROM jobs WHERE id=1"
                    ).fetchone()
                self.assertIsNone(row[0])
                self.assertEqual(row[1], "unknown")
                self.assertIsNone(row[2])
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

    def test_telegram_hides_post_time_after_discovery(self):
        item = {
            "score": 100,
            "title": "Full Stack Developer",
            "company": "Vertigo Media",
            "location": "Greater Bengaluru Area",
            "source": "linkedin",
            "source_posted_at": "2026-10-11T12:31:00+00:00",
            "posted_precision": "minute",
            "discovered_at": "2026-10-11T12:26:00+00:00",
            "experience_min_years": 1,
            "experience_max_years": 1,
            "url": "https://example.com/job/123",
            "match_reasons_json": "[]",
        }

        message = format_notification(item)

        self.assertIn("🕐 Posted: Unknown", message)
        self.assertIn("🔎 Discovered: 11 Oct 2026, 5:56 PM IST", message)
        self.assertNotIn("6:01 PM IST", message)

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

    def test_jobs_api_returns_persisted_match_and_notification_decisions(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "linkedin", "li-api-consistency", "Acme", "Software Engineer",
                    "Bengaluru, India", "https://linkedin.com/jobs/view/api-consistency",
                    None, "unknown", "Build Python services. Experience 1-2 years.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                self.assertEqual(radar.refresh_notification_decisions(BASE_CONFIG), 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    persisted = conn.execute("""
                        SELECT e.match, e.score, e.alertable, nl.status,
                               nl.decision_reason_json
                        FROM jobs j
                        JOIN job_evaluations e ON e.job_id=j.id
                        JOIN notification_ledger nl
                          ON nl.canonical_opportunity_id=j.canonical_opportunity_id
                        WHERE j.source_job_id='li-api-consistency'
                    """).fetchone()

                with patch.object(radar, "get_config", return_value=BASE_CONFIG):
                    response = radar.jobs(minutes=60, limit=100, today_only=True)
                item = next(
                    entry for entry in response["jobs"]
                    if entry["source_job_id"] == "li-api-consistency"
                )

                self.assertEqual(item["likely_match"], bool(persisted[0]))
                self.assertEqual(item["match_score"], persisted[1])
                self.assertEqual(item["alertable"], bool(persisted[2]))
                self.assertEqual(item["notification_status"], persisted[3])
                self.assertEqual(
                    item["notification_decision_reasons"],
                    json.loads(persisted[4]),
                )
                self.assertEqual(item["notification_status"], "queued")
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

                notifications_disabled = {
                    **BASE_CONFIG,
                    "notifications_enabled": False,
                }
                self.assertEqual(
                    radar.refresh_job_evaluations(notifications_disabled),
                    1,
                )
                self.assertEqual(
                    radar.refresh_notification_decisions(notifications_disabled),
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

    def test_unknown_experience_new_opportunity_is_queued_when_match_threshold_passes(self):
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
                        "SELECT status, candidate_job_id FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(row[0], "queued")
                self.assertEqual(row[1], 1)
            finally:
                radar.DB_PATH = original_db

    def test_deprecated_experience_alert_gate_does_not_change_eligibility(self):
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
                self.assertEqual(row[0], 1)

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

    def test_legacy_config_migrates_linkedin_poll_to_120_seconds(self):
        defaults = {
            "config_version": 8,
            "poll_seconds": {"linkedin": 120, "naukri": 300},
            "source_enabled": {
                "linkedin": True, "naukri": True,
                "instahyre": False, "greenhouse": False,
            },
        }
        prior_runtime = {
            "config_version": 7,
            "poll_seconds": {"linkedin": 60, "naukri": 420},
            "source_enabled": {
                "linkedin": True, "naukri": True,
                "instahyre": False, "greenhouse": False,
            },
        }

        merged = _merge_config(defaults, prior_runtime)

        self.assertEqual(merged["poll_seconds"]["linkedin"], 120)
        self.assertEqual(merged["poll_seconds"]["naukri"], 420)

    def test_v9_config_migrates_linkedin_to_free_first_request_budget(self):
        defaults = {
            "config_version": 10,
            "poll_seconds": {"linkedin": 180, "naukri": 300},
            "source_enabled": {
                "linkedin": True, "naukri": True,
                "instahyre": False, "greenhouse": False,
            },
            "require_explicit_experience_for_alerts": False,
        }
        previous = {
            "config_version": 9,
            "poll_seconds": {"linkedin": 120, "naukri": 420},
            "source_enabled": {
                "linkedin": True, "naukri": True,
                "instahyre": False, "greenhouse": False,
            },
            "require_explicit_experience_for_alerts": False,
        }

        merged = _merge_config(defaults, previous)

        self.assertEqual(merged["config_version"], 10)
        self.assertEqual(merged["poll_seconds"]["linkedin"], 180)
        self.assertEqual(merged["poll_seconds"]["naukri"], 420)
        self.assertEqual(merged["require_explicit_experience_for_alerts"], False)

    def test_linkedin_request_budget_defaults_are_conservative(self):
        self.assertEqual(radar.LINKEDIN_MIN_REQUEST_INTERVAL_SECONDS, 4.0)
        self.assertEqual(radar.LINKEDIN_FAST_TARGETS_PER_SCAN, 2)
        self.assertEqual(radar.LINKEDIN_DEEP_SCAN_SECONDS, 1800)
        self.assertEqual(radar.LINKEDIN_DETAIL_WORKERS, 1)

    def test_v8_config_migrates_to_threshold_only_alert_policy(self):
        defaults = {
            "config_version": 9,
            "require_explicit_experience_for_alerts": False,
            "poll_seconds": {"linkedin": 120, "naukri": 300},
            "source_enabled": {
                "linkedin": True, "naukri": True,
                "instahyre": False, "greenhouse": False,
            },
        }
        previous = {
            "config_version": 8,
            "require_explicit_experience_for_alerts": True,
            "poll_seconds": {"linkedin": 120, "naukri": 300},
            "source_enabled": {
                "linkedin": True, "naukri": True,
                "instahyre": False, "greenhouse": False,
            },
        }

        merged = _merge_config(defaults, previous)

        self.assertEqual(merged["config_version"], 9)
        self.assertFalse(merged["require_explicit_experience_for_alerts"])

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

    def test_config_v6_requires_explicit_experience_for_legacy_runtime(self):
        defaults = {
            "config_version": 6,
            "require_explicit_experience_for_alerts": True,
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
            "config_version": 5,
            "require_explicit_experience_for_alerts": False,
        }

        merged = _merge_config(defaults, prior_runtime)

        self.assertEqual(merged["config_version"], 6)
        self.assertTrue(merged["require_explicit_experience_for_alerts"])

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

    def test_naukri_relay_reads_public_feed_without_a_token(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"updated_at": "2026-10-09T05:04:08+00:00", "jobs": []}

        with patch.object(radar.requests, "get", return_value=Response()) as request:
            jobs = radar.naukri_collect()

        self.assertEqual(jobs, [])
        request.assert_called_once()
        args, kwargs = request.call_args
        self.assertEqual(args[0], radar.NAUKRI_RELAY_URL)
        self.assertIsInstance(kwargs["params"]["t"], int)
        self.assertNotIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Accept"], "application/json")
        self.assertEqual(kwargs["timeout"], 20)


    def test_parse_relative_accepts_utc_z_suffix_without_lowercasing_iso_text(self):
        for value in (
            "2026-10-08T10:00:00Z",
            "2026-10-08T10:00:00z",
        ):
            with self.subTest(value=value):
                parsed = radar.parse_relative(value)
                self.assertEqual(radar.iso(parsed), "2026-10-08T10:00:00+00:00")

    def test_greenhouse_collector_uses_first_published_and_does_not_use_updated_at(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "jobs": [{
                        "id": 123,
                        "title": "Software Engineer",
                        "absolute_url": "https://boards.greenhouse.io/example/jobs/123",
                        "location": {"name": "Bengaluru, India"},
                        "first_published": "2026-10-08T10:00:00Z",
                        "updated_at": "2026-10-09T10:00:00Z",
                        "content": "<p>Build Python APIs.</p><p>2+ years experience.</p>",
                        "departments": [{"name": "Engineering"}],
                    }]
                }

        config = {
            "greenhouse_boards": [{"token": "example", "company": "Example Labs"}]
        }
        with patch.object(radar.requests, "get", return_value=Response()) as request:
            jobs = radar.greenhouse_collect(config)

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job["source"], "greenhouse")
        self.assertEqual(job["source_job_id"], "gh-example-123")
        self.assertEqual(job["company"], "Example Labs")
        self.assertEqual(job["location"], "Bengaluru, India")
        self.assertIn("Build Python APIs.", job["description"])
        self.assertIn("Department: Engineering", job["description"])
        self.assertNotIn("<p>", job["description"])
        self.assertEqual(job["source_posted_at"], "2026-10-08T10:00:00+00:00")
        self.assertEqual(job["posted_precision"], "minute")
        self.assertIsNotNone(job["discovery_latency_seconds"])
        self.assertGreaterEqual(job["discovery_latency_seconds"], 0)

        args, kwargs = request.call_args
        self.assertEqual(args[0], "https://boards-api.greenhouse.io/v1/boards/example/jobs")
        self.assertEqual(kwargs["params"], {"content": "true"})
        self.assertNotIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["timeout"], 20)

    def test_greenhouse_collector_keeps_posting_time_unknown_if_first_published_missing(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "jobs": [{
                        "id": 789,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/example/jobs/789",
                        "location": {"name": "Remote - India"},
                        "updated_at": "2026-10-09T10:00:00Z",
                        "content": "<p>Build services.</p>",
                    }]
                }

        config = {
            "greenhouse_boards": [{"token": "example", "company": "Example Labs"}]
        }
        with patch.object(radar.requests, "get", return_value=Response()):
            jobs = radar.greenhouse_collect(config)

        self.assertEqual(len(jobs), 1)
        self.assertIsNone(jobs[0]["source_posted_at"])
        self.assertEqual(jobs[0]["posted_precision"], "unknown")
        self.assertIsNone(jobs[0]["discovery_latency_seconds"])
    def test_greenhouse_collector_keeps_successful_board_when_another_board_fails(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "jobs": [{
                        "id": 456,
                        "title": "Python Developer",
                        "absolute_url": "https://boards.greenhouse.io/good/jobs/456",
                        "location": {"name": "Remote - India"},
                        "content": "<p>Build automation.</p>",
                        "departments": [{"name": "Engineering"}],
                    }]
                }

        def fake_get(url, **kwargs):
            if "/bad/" in url:
                raise radar.requests.HTTPError("404 board not found")
            return Response()

        config = {
            "greenhouse_boards": [
                {"token": "bad", "company": "Bad Board"},
                {"token": "good", "company": "Good Board"},
            ]
        }
        with patch.object(radar.requests, "get", side_effect=fake_get):
            jobs = radar.greenhouse_collect(config)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["company"], "Good Board")
        self.assertEqual(jobs[0]["source_job_id"], "gh-good-456")

    def test_greenhouse_collector_fails_when_no_boards_are_configured(self):
        with self.assertRaises(RuntimeError):
            radar.greenhouse_collect({"greenhouse_boards": []})

    def test_config_v7_keeps_greenhouse_source_opt_in_for_existing_runtime(self):
        defaults = {
            "config_version": 7,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": False,
                "greenhouse": False,
            },
            "poll_seconds": {
                "linkedin": 60,
                "naukri": 300,
                "instahyre": 600,
                "greenhouse": 900,
            },
        }
        prior_runtime = {
            "config_version": 6,
            "source_enabled": {
                "linkedin": True,
                "naukri": True,
                "instahyre": False,
                "greenhouse": True,
            },
            "poll_seconds": {
                "linkedin": 60,
                "naukri": 300,
                "instahyre": 600,
            },
        }

        merged = _merge_config(defaults, prior_runtime)

        self.assertEqual(merged["config_version"], 7)
        self.assertFalse(merged["source_enabled"]["greenhouse"])
        self.assertEqual(merged["poll_seconds"]["greenhouse"], 900)

    def test_config_validation_rejects_unsafe_greenhouse_board_tokens(self):
        config = {
            **BASE_CONFIG,
            "greenhouse_boards": [{"token": "../private", "company": "Example"}],
        }
        with self.assertRaises(radar.HTTPException):
            radar.validate_config(config)

    def test_naukri_date_precision_does_not_claim_exact_discovery_latency(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "updated_at": "2026-10-09T05:04:08+00:00",
                    "jobs": [{
                        "id": "naukri-1",
                        "url": "https://www.naukri.com/job-listings-example",
                        "company": "Example Co",
                        "title": "Software Engineer",
                        "location": "Bengaluru",
                        "posted": "2026-10-08",
                    }],
                }

        with patch.object(radar.requests, "get", return_value=Response()):
            jobs = radar.naukri_collect()

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["posted_precision"], "date")
        self.assertIsNone(jobs[0]["discovery_latency_seconds"])

    def test_naukri_relay_does_not_retry_public_feed_404(self):
        class Response:
            status_code = 404

            def raise_for_status(self):
                raise radar.requests.HTTPError("404 public relay feed not found")

        with patch.object(radar.requests, "get", return_value=Response()) as request:
            with self.assertRaises(radar.requests.HTTPError):
                radar.naukri_collect()

        request.assert_called_once()

    def test_linkedin_skips_deep_scan_after_fast_lane_rate_limit(self):
        config = {
            "locations": ["Bengaluru, India", "Remote, India"],
            "linkedin_queries": ["software engineer", "automation engineer"],
        }
        original_deep_scan = radar.linkedin_last_deep_scan_at
        original_cursor = radar.linkedin_fast_target_cursor
        original_rate_limit_state = (
            radar.linkedin_last_http_request_monotonic,
            radar.linkedin_rate_limited_until_monotonic,
            radar.linkedin_rate_limit_streak,
            radar.linkedin_rate_limit_generation,
            dict(radar.source_state.get("linkedin", {})),
        )
        calls = []

        def fake_search(query, location, start, fast):
            calls.append((query, location, start, fast))
            if len(calls) == 1:
                response = type("Response", (), {"status_code": 429})()
                error = radar.requests.HTTPError("429 Too Many Requests")
                error.response = response
                raise error
            return []

        try:
            radar.linkedin_last_deep_scan_at = None
            radar.linkedin_fast_target_cursor = 0
            with patch.object(radar, "_linkedin_search_page", side_effect=fake_search):
                radar.linkedin_collect(config)
            self.assertTrue(calls)
            self.assertTrue(all(start == 0 and fast for _, _, start, fast in calls))
        finally:
            radar.linkedin_last_deep_scan_at = original_deep_scan
            radar.linkedin_fast_target_cursor = original_cursor
            (
                radar.linkedin_last_http_request_monotonic,
                radar.linkedin_rate_limited_until_monotonic,
                radar.linkedin_rate_limit_streak,
                radar.linkedin_rate_limit_generation,
                original_linkedin_runtime,
            ) = original_rate_limit_state
            if original_linkedin_runtime:
                radar.source_state["linkedin"] = original_linkedin_runtime
            else:
                radar.source_state.pop("linkedin", None)

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

    def test_unknown_experience_match_is_alertable_at_configured_threshold(self):
        job = make_job("AI Engineer", "Build AI systems with Python.")
        result = match_details(job, BASE_CONFIG)
        self.assertTrue(result["match"])
        self.assertGreaterEqual(result["score"], BASE_CONFIG["match_threshold"])
        alert = alertability_details(job, result, BASE_CONFIG)
        self.assertTrue(alert["alertable"])
        self.assertIn("passes match threshold", alert["reasons"][0])

    def test_policy_migration_suppresses_old_gate_backlog_but_keeps_recent_pending(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                old_job = normalize_job(
                    "linkedin", "li-policy-old", "Acme", "AI Engineer",
                    "Bengaluru", "https://linkedin.com/jobs/view/policy-old", None,
                    "unknown", "Build AI systems with Python.",
                )
                recent_job = normalize_job(
                    "linkedin", "li-policy-recent", "Other Acme", "AI Engineer",
                    "Bengaluru, Karnataka, India", "https://linkedin.com/jobs/view/policy-recent", None,
                    "unknown", "Build AI systems with Python.",
                )
                self.assertEqual(upsert_jobs([old_job, recent_job], BASE_CONFIG), 2)

                old_time = radar.iso(radar.now() - timedelta(minutes=20))
                recent_time = radar.iso(radar.now() - timedelta(minutes=5))
                legacy_reason = json.dumps(["explicit experience required for alerts"])
                with sqlite3.connect(radar.DB_PATH) as conn:
                    old_id = conn.execute(
                        "SELECT canonical_opportunity_id FROM jobs WHERE source_job_id='li-policy-old'"
                    ).fetchone()[0]
                    recent_id = conn.execute(
                        "SELECT canonical_opportunity_id FROM jobs WHERE source_job_id='li-policy-recent'"
                    ).fetchone()[0]
                    conn.execute(
                        "UPDATE job_evaluations SET alertable=0, alertability_reasons_json=? "
                        "WHERE job_id=(SELECT id FROM jobs WHERE source_job_id='li-policy-old')",
                        (legacy_reason,),
                    )
                    conn.execute(
                        "UPDATE job_evaluations SET alertable=0, alertability_reasons_json=? "
                        "WHERE job_id=(SELECT id FROM jobs WHERE source_job_id='li-policy-recent')",
                        (legacy_reason,),
                    )
                    conn.execute(
                        "UPDATE notification_ledger SET status='pending', created_at=?, "
                        "candidate_job_id=NULL, attempt_count=0, sent_at=NULL WHERE canonical_opportunity_id=?",
                        (old_time, old_id),
                    )
                    conn.execute(
                        "UPDATE notification_ledger SET status='pending', created_at=?, "
                        "candidate_job_id=NULL, attempt_count=0, sent_at=NULL WHERE canonical_opportunity_id=?",
                        (recent_time, recent_id),
                    )
                    conn.commit()

                self.assertEqual(
                    radar.suppress_preexisting_unknown_experience_pending_notifications(),
                    1,
                )
                with sqlite3.connect(radar.DB_PATH) as conn:
                    rows = dict(conn.execute(
                        "SELECT canonical_opportunity_id, status FROM notification_ledger"
                    ).fetchall())
                    reason = conn.execute(
                        "SELECT decision_reason_json FROM notification_ledger WHERE canonical_opportunity_id=?",
                        (old_id,),
                    ).fetchone()[0]
                self.assertEqual(rows[old_id], "suppressed")
                self.assertEqual(rows[recent_id], "pending")
                self.assertIn("avoid a historical Telegram alert burst", reason)
            finally:
                radar.DB_PATH = original_db

    def test_excluded_role_category_is_configurable(self):
        config = {**BASE_CONFIG, "excluded_role_terms": ["quality assurance"]}
        result = match_details(
            make_job("Quality Assurance Automation Engineer", "2 years experience"),
            config,
        )
        self.assertFalse(result["match"])

    def test_linkedin_fast_lane_rotates_two_targets_and_covers_all_locations(self):
        original_state = radar.source_state
        original_deep = radar.linkedin_last_deep_scan_at
        radar.source_state = {}
        radar.linkedin_last_deep_scan_at = radar.iso(radar.now())
        config = {
            **BASE_CONFIG,
            "linkedin_queries": ["ai engineer"],
            "locations": [
                "Bengaluru, Karnataka, India",
                "Gurugram, Haryana, India",
                "Delhi, India",
                "Remote, India",
            ],
        }
        calls = []

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
            calls.append((params["location"], params["start"]))
            return Response()

        expected = sorted([
            ("Bengaluru, Karnataka, India", 0),
            ("Gurugram, Haryana, India", 0),
            ("Delhi, India", 0),
            ("Remote, India", 0),
        ])
        try:
            with patch.object(radar, "_linkedin_request", side_effect=fake_request):
                radar.linkedin_collect(config)
                first_cycle = sorted(calls)
                calls.clear()
                radar.linkedin_collect(config)
                second_cycle = sorted(calls)

            self.assertEqual(len(first_cycle), 2)
            self.assertEqual(len(second_cycle), 2)
            self.assertEqual(first_cycle, [("Bengaluru, Karnataka, India", 0), ("Gurugram, Haryana, India", 0)])
            self.assertEqual(
                set(first_cycle + second_cycle),
                set(expected),
            )
        finally:
            radar.source_state = original_state
            radar.linkedin_last_deep_scan_at = original_deep


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

    def test_linkedin_structured_experience_metadata_outside_description_is_captured(self):
        job = radar.normalize_job(
            "linkedin",
            "li-cloud-ai-experience-band",
            "Cvali",
            "Cloud & AI Engineer",
            "Bengaluru, Karnataka, India",
            "https://www.linkedin.com/jobs/view/cloud-ai-engineer-at-cvali-4475684372",
            None,
            "unknown",
            "Cloud & AI Engineer Cvali Bengaluru",
        )

        class Response:
            status_code = 200
            text = """
            <html><body>
              <div class="job-details-jobs-unified-top-card__job-insight">
                <span>Experience: 4.00-6.00 Years</span>
              </div>
              <div class="description__text">
                Build cloud AI services using Python and deep learning.
              </div>
            </body></html>
            """

        with patch.object(radar, "_linkedin_http_get", return_value=Response()):
            enriched = radar.enrich_linkedin_job(job)

        self.assertEqual(enriched["jd_experience_min_years"], 4.0)
        self.assertEqual(enriched["jd_experience_max_years"], 6.0)
        result = match_details(enriched, BASE_CONFIG)
        self.assertFalse(result["match"])
        self.assertIn("experience minimum 4 exceeds candidate 2 years", result["reasons"][0])

    def test_linkedin_generic_experience_snippet_does_not_skip_jd_enrichment(self):
        original_deep_scan = radar.linkedin_last_deep_scan_at
        original_cursor = radar.linkedin_fast_target_cursor
        try:
            radar.linkedin_last_deep_scan_at = radar.iso(radar.now())
            radar.linkedin_fast_target_cursor = 0
            job = radar.normalize_job(
                "linkedin",
                "li-generic-experience-snippet",
                "Cvali",
                "Cloud & AI Engineer",
                "Bengaluru, Karnataka, India",
                "https://www.linkedin.com/jobs/view/cloud-ai-engineer-1234567890",
                None,
                "unknown",
                "Cloud & AI Engineer Cvali. 2 years experience building AI services.",
            )
            job["needs_jd_enrichment"] = True
            enriched_ids = []

            def fake_enrich(candidate):
                enriched_ids.append(candidate["source_job_id"])
                candidate["jd_experience_min_years"] = 4.0
                candidate["jd_experience_max_years"] = 6.0
                candidate.pop("needs_jd_enrichment", None)
                return candidate

            config = {
                **BASE_CONFIG,
                "linkedin_queries": ["ai engineer"],
                "locations": ["Bengaluru, Karnataka, India"],
            }
            with (
                patch.object(radar, "_linkedin_cooldown_remaining", return_value=0),
                patch.object(radar, "_linkedin_search_page", return_value=[job]),
                patch.object(radar, "enrich_linkedin_job", side_effect=fake_enrich),
            ):
                result = radar.linkedin_collect(config)

            self.assertEqual(enriched_ids, ["li-generic-experience-snippet"])
            self.assertEqual(result[0]["jd_experience_min_years"], 4.0)
            self.assertEqual(result[0]["jd_experience_max_years"], 6.0)
        finally:
            radar.linkedin_last_deep_scan_at = original_deep_scan
            radar.linkedin_fast_target_cursor = original_cursor


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



class SourceStatusPersistenceTests(unittest.TestCase):
    def _source_status_for_rows(self, rows):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("""
                        CREATE TABLE source_runs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source TEXT NOT NULL,
                            started_at TEXT NOT NULL,
                            finished_at TEXT NOT NULL,
                            jobs_seen INTEGER NOT NULL,
                            new_jobs INTEGER NOT NULL,
                            error TEXT
                        )
                    """)
                    conn.executemany(
                        "INSERT INTO source_runs "
                        "(source, started_at, finished_at, jobs_seen, new_jobs, error) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        rows,
                    )
                with patch.object(
                    radar,
                    "get_config",
                    return_value={"source_enabled": {"linkedin": False, "naukri": True}},
                ), patch.object(radar, "source_state", {}):
                    return radar.source_status()
            finally:
                radar.DB_PATH = original_db

    def test_source_status_exposes_persisted_error_from_latest_run(self):
        payload = self._source_status_for_rows([
            (
                "naukri",
                "2026-10-12T10:00:00+00:00",
                "2026-10-12T10:01:00+00:00",
                0,
                0,
                "HTTP 503 Service Unavailable",
            )
        ])
        naukri = next(item for item in payload["sources"] if item["source"] == "naukri")
        self.assertEqual(naukri["last_error"], "HTTP 503 Service Unavailable")
        self.assertEqual(naukri["last_run"], "2026-10-12T10:01:00+00:00")
        self.assertEqual(naukri["jobs_seen"], 0)

    def test_successful_latest_run_clears_persisted_source_error(self):
        payload = self._source_status_for_rows([
            (
                "naukri",
                "2026-10-12T09:00:00+00:00",
                "2026-10-12T09:01:00+00:00",
                0,
                0,
                "HTTP 503 Service Unavailable",
            ),
            (
                "naukri",
                "2026-10-12T10:00:00+00:00",
                "2026-10-12T10:01:00+00:00",
                18,
                2,
                None,
            ),
        ])
        naukri = next(item for item in payload["sources"] if item["source"] == "naukri")
        self.assertIsNone(naukri["last_error"])
        self.assertEqual(naukri["jobs_seen"], 18)
        self.assertEqual(naukri["new_jobs"], 2)
