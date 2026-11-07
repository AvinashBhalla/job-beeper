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

    def test_explicit_work_location_overrides_broad_feed_location(self):
        job = make_job(
            "Software Engineer",
            "Work Location: Pune INTERVIEW VENUE: Pune, Maharashtra. "
            "Build Python services. 2 years experience.",
            "Pune, Chennai, Bengaluru, India",
        )
        details = match_details(job, BASE_CONFIG)
        self.assertFalse(details["match"])
        self.assertEqual(
            details["reasons"],
            ["location outside configured targets"],
        )

    def test_explicit_work_location_can_correct_stale_feed_location(self):
        job = make_job(
            "Software Engineer",
            "Work Location: Bengaluru, Karnataka, India. "
            "Build Python services. 2 years experience.",
            "Pune, Chennai, India",
        )
        details = match_details(job, BASE_CONFIG)
        self.assertTrue(details["match"])

    def test_work_location_parser_does_not_use_interview_venue(self):
        self.assertEqual(
            radar.extract_explicit_work_location(
                "Work Location: Pune INTERVIEW VENUE: Koramangala, Bengaluru"
            ),
            "Pune",
        )

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

    def test_matcher_rules_version_changes_evaluation_fingerprint(self):
        baseline = radar._config_fingerprint(BASE_CONFIG)
        with patch.object(
            radar,
            "MATCHER_RULES_VERSION",
            radar.MATCHER_RULES_VERSION + 1,
        ):
            upgraded = radar._config_fingerprint(BASE_CONFIG)
        self.assertNotEqual(baseline, upgraded)

    def test_description_role_mention_does_not_match_non_engineering_title(self):
        config = {
            **BASE_CONFIG,
            "target_roles": ["software engineer", "forward deployed engineer"],
            "skills": ["llm", "ai"],
        }
        details = match_details(
            make_job(
                "Conversation Quality Analyst",
                "Verify LLM evaluations and collaborate with forward deployed engineers.",
                "Bengaluru, India",
            ),
            config,
        )
        self.assertFalse(details["match"])
        self.assertIn("no configured target-role match", details["reasons"])

    def test_description_role_fallback_is_kept_for_engineering_title(self):
        config = {
            **BASE_CONFIG,
            "target_roles": ["software engineer"],
            "skills": ["python"],
        }
        details = match_details(
            make_job(
                "Product Engineer",
                "Work with a software engineer to build Python services.",
                "Bengaluru, India",
            ),
            config,
        )
        self.assertTrue(details["match"])
        self.assertIn("role (description): software engineer", details["reasons"])

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
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                updated_at = radar.iso(radar.now() - radar.dt.timedelta(minutes=1))

                class Response:
                    status_code = 200

                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "updated_at": updated_at,
                            "count": 1,
                            "jobs": [{
                                "id": "n-1",
                                "url": "https://www.naukri.com/job-listings-n-1",
                                "title": "Software Engineer",
                                "company": "Example",
                                "location": "Bengaluru",
                                "posted": "2026-11-07",
                            }],
                        }

                with patch.object(radar.requests, "get", return_value=Response()) as request:
                    jobs = radar.naukri_collect()

                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0]["discovered_at"], updated_at)
                self.assertIsNone(jobs[0]["discovery_latency_seconds"])
                request.assert_called_once()
                args, kwargs = request.call_args
                self.assertEqual(args[0], radar.NAUKRI_RELAY_URL)
                self.assertIsInstance(kwargs["params"]["t"], int)
                self.assertNotIn("Authorization", kwargs["headers"])
                self.assertEqual(kwargs["headers"]["Accept"], "application/json")
                self.assertEqual(kwargs["timeout"], 20)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    state = conn.execute(
                        "SELECT feed_updated_at, jobs_count FROM source_feed_state WHERE source='naukri'"
                    ).fetchone()
                self.assertEqual(state, (updated_at, 1))
            finally:
                radar.DB_PATH = original_db


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
    def test_greenhouse_alert_freshness_requires_valid_recent_first_published(self):
        from datetime import timedelta

        cases = (
            ("unknown", None, False),
            ("stale", radar.now() - timedelta(hours=73), False),
            ("recent", radar.now() - timedelta(minutes=30), True),
        )
        original_db = radar.DB_PATH
        try:
            for label, posted_at, should_queue in cases:
                with self.subTest(publication_time=label), TemporaryDirectory() as tmp:
                    radar.DB_PATH = Path(tmp) / "jobs.db"
                    radar.init_db()
                    job = normalize_job(
                        "greenhouse",
                        f"gh-freshness-{label}",
                        "Acme",
                        "Software Engineer",
                        "Bengaluru, India",
                        f"https://boards.greenhouse.io/acme/jobs/{label}",
                        posted_at,
                        "minute" if posted_at is not None else "unknown",
                        "Build Python services. 2 years experience.",
                    )
                    self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                    self.assertEqual(
                        radar.refresh_notification_decisions(BASE_CONFIG), 1
                    )
                    with sqlite3.connect(radar.DB_PATH) as conn:
                        status, reasons = conn.execute(
                            "SELECT status, decision_reason_json FROM notification_ledger"
                        ).fetchone()

                    if should_queue:
                        self.assertEqual(status, "queued")
                    else:
                        self.assertEqual(status, "suppressed")
                        self.assertIn("no matching observation within 72 hour age window", reasons)
        finally:
            radar.DB_PATH = original_db

    def test_greenhouse_malformed_publication_timestamp_is_not_fresh(self):
        original_db = radar.DB_PATH
        try:
            with TemporaryDirectory() as tmp:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                job = normalize_job(
                    "greenhouse", "gh-malformed-date", "Acme", "Software Engineer",
                    "Bengaluru, India", "https://boards.greenhouse.io/acme/jobs/malformed",
                    None, "unknown", "Build Python services. 2 years experience.",
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute(
                        "UPDATE jobs SET source_posted_at='not-a-timestamp'"
                    )
                    conn.commit()

                self.assertEqual(
                    radar.refresh_notification_decisions(BASE_CONFIG), 1
                )
                with sqlite3.connect(radar.DB_PATH) as conn:
                    status, reasons = conn.execute(
                        "SELECT status, decision_reason_json FROM notification_ledger"
                    ).fetchone()
                self.assertEqual(status, "suppressed")
                self.assertIn(
                    "no matching observation within 72 hour age window", reasons
                )
        finally:
            radar.DB_PATH = original_db

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
                    "updated_at": radar.iso(radar.now() - radar.dt.timedelta(seconds=90)),
                    "jobs": [{
                        "id": "naukri-1",
                        "url": "https://www.naukri.com/job-listings-example",
                        "company": "Example Co",
                        "title": "Software Engineer",
                        "location": "Bengaluru",
                        "posted": "2026-10-08",
                    }],
                }

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                with patch.object(radar.requests, "get", return_value=Response()):
                    jobs = radar.naukri_collect()
            finally:
                radar.DB_PATH = original_db

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["posted_precision"], "date")
        self.assertIsNone(jobs[0]["discovery_latency_seconds"])

    def test_naukri_relay_preserves_markdown_and_structured_listing_details(self):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "updated_at": radar.iso(radar.now() - radar.dt.timedelta(seconds=90)),
                    "jobs": [{
                        "id": "nk-051126503145",
                        "url": "https://www.naukri.com/job-listings-example",
                        "company": "Novisync Solutions India",
                        "title": "Python Developer",
                        "location": "Bengaluru, India",
                        "posted": "2026-11-05",
                        "description": "* Build Python APIs.\\n\\n0-2 Yrs",
                        "description_format": "markdown",
                        "source_details": {
                            "role": "Back End Developer",
                            "role_category": "Software Development",
                            "industry_type": "IT Services & Consulting",
                            "department": "Engineering - Software & QA",
                            "employment_type": "Full Time, Permanent",
                            "education": {"ug": ["Any Graduate"], "pg": ["Any Postgraduate"], "ppg": []},
                            "key_skills": ["python", "django", "pandas"],
                        },
                    }],
                }

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                with patch.object(radar.requests, "get", return_value=Response()):
                    jobs = radar.naukri_collect()
            finally:
                radar.DB_PATH = original_db

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["description_format"], "markdown")
        self.assertIn("* Build Python APIs.", jobs[0]["description"])
        self.assertEqual(jobs[0]["source_details"]["role"], "Back End Developer")
        self.assertEqual(
            jobs[0]["source_details"]["education"]["ug"],
            ["Any Graduate"],
        )
        self.assertEqual(
            jobs[0]["source_details"]["key_skills"],
            ["python", "django", "pandas"],
        )

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
        original_cursor = radar.linkedin_fast_target_cursor
        radar.source_state = {}
        radar.linkedin_fast_target_cursor = 0
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
            # This test targets round-robin coverage, not the global rate-limit
            # mechanism; isolate it so a process-level cooldown cannot hide
            # whether the cursor advances to the next two targets.
            with patch.object(radar, "_linkedin_cooldown_remaining", return_value=0), patch.object(
                radar, "_linkedin_request", side_effect=fake_request
            ):
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
            radar.linkedin_fast_target_cursor = original_cursor


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
            # Keep this collector test hermetic: parsed LinkedIn cards are marked
            # for JD enrichment, which must not make real network requests here.
            with patch.object(radar, "_linkedin_request", side_effect=fake_request), patch.object(
                radar,
                "enrich_linkedin_job",
                side_effect=lambda job: {**job, "needs_jd_enrichment": False},
            ):
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



    def test_jd_experience_prefers_total_requirement_over_earlier_skill_years(self):
        jd = (
            "3+ years of Python experience. "
            "1+ years of AWS experience. "
            "5+ years of total professional experience required."
        )
        self.assertEqual(radar.extract_jd_experience(jd), (5.0, None))

    def test_shadow_requires_strong_experience_evidence_before_skipping_gemini(self):
        self.assertFalse(radar._experience_is_reliably_known_for_shadow({
            "source": "naukri",
            "description": "5+ years of software development experience with Python.",
        }))
        self.assertFalse(radar._experience_is_reliably_known_for_shadow({
            "source": "ashby",
            "description": "3+ years of Python experience.",
        }))
        self.assertTrue(radar._experience_is_reliably_known_for_shadow({
            "source": "greenhouse",
            "description": "5+ years of overall professional experience required.",
        }))
        self.assertTrue(radar._experience_is_reliably_known_for_shadow({
            "source": "linkedin",
            "description": "Experience: 4-6 years",
        }))

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

    def test_jobs_search_runs_before_limit_and_is_case_insensitive(self):
        from datetime import timedelta

        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                day_start = radar.current_day_start_utc()

                older_match = normalize_job(
                    "naukri",
                    "nk-novisync-older",
                    "Novisync Solutions India",
                    "Python Developer",
                    "Bengaluru, India",
                    "https://example.com/novisync-python",
                    None,
                    "unknown",
                    "Build Python services.",
                )
                newer_nonmatch = normalize_job(
                    "naukri",
                    "nk-other-newer",
                    "Another Company",
                    "Software Engineer",
                    "Bengaluru, India",
                    "https://example.com/another-role",
                    None,
                    "unknown",
                    "Build backend services.",
                )
                # The match is from the previous India-local calendar day,
                # but remains inside the dashboard's advertised 72-hour window.
                older_match["discovered_at"] = radar.iso(
                    day_start - timedelta(hours=4)
                )
                newer_nonmatch["discovered_at"] = radar.iso(
                    day_start + timedelta(minutes=20)
                )

                self.assertEqual(
                    upsert_jobs([older_match, newer_nonmatch], BASE_CONFIG),
                    2,
                )

                result = radar.jobs(
                    minutes=4320,
                    limit=1,
                    q="NOVISYNC",
                )

                self.assertEqual(len(result["jobs"]), 1)
                self.assertEqual(
                    result["jobs"][0]["source_job_id"],
                    "nk-novisync-older",
                )

                description_result = radar.jobs(
                    minutes=4320,
                    limit=10,
                    q="backend services",
                )
                self.assertEqual(
                    [item["source_job_id"] for item in description_result["jobs"]],
                    ["nk-other-newer"],
                )
            finally:
                radar.DB_PATH = original_db

    def test_jobs_search_treats_like_wildcards_as_literal_text(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                literal_percent = normalize_job(
                    "naukri",
                    "nk-percent-literal",
                    "100% Labs",
                    "Python Developer",
                    "Bengaluru, India",
                    "https://example.com/100-percent",
                    None,
                    "unknown",
                    "Build Python services.",
                )
                no_percent = normalize_job(
                    "naukri",
                    "nk-percent-plain",
                    "1000 Labs",
                    "Python Developer",
                    "Bengaluru, India",
                    "https://example.com/1000",
                    None,
                    "unknown",
                    "Build Python services.",
                )
                self.assertEqual(
                    upsert_jobs([literal_percent, no_percent], BASE_CONFIG),
                    2,
                )

                result = radar.jobs(
                    minutes=4320,
                    limit=10,
                    q="100%",
                )
                self.assertEqual(
                    [item["source_job_id"] for item in result["jobs"]],
                    ["nk-percent-literal"],
                )
            finally:
                radar.DB_PATH = original_db

    def test_jobs_preserve_markdown_and_naukri_source_details(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                source_details = {
                    "role": "Back End Developer",
                    "role_category": "Software Development",
                    "industry_type": "IT Services & Consulting",
                    "department": "Engineering - Software & QA",
                    "employment_type": "Full Time, Permanent",
                    "education": {
                        "ug": ["Any Graduate"],
                        "pg": ["Any Postgraduate"],
                    },
                    "key_skills": ["python", "django", "pandas"],
                }
                job = normalize_job(
                    "naukri",
                    "nk-rich-description-1",
                    "Example Company",
                    "Python Developer",
                    "Bengaluru, India",
                    "https://example.com/rich-description",
                    None,
                    "unknown",
                    "### Job Description\\n\\n* Build Python APIs.",
                    description_format="markdown",
                    source_details=source_details,
                )
                self.assertEqual(upsert_jobs([job], BASE_CONFIG), 1)

                with patch.object(radar, "get_config", return_value=BASE_CONFIG):
                    result = radar.jobs(minutes=10080, limit=10, q="pandas")

                item = next(
                    entry for entry in result["jobs"]
                    if entry["source_job_id"] == "nk-rich-description-1"
                )
                self.assertEqual(item["description_format"], "markdown")
                self.assertEqual(item["source_details"], source_details)

                # A later legacy/plain relay record must not downgrade an
                # already enriched Markdown description or erase metadata.
                older_payload = normalize_job(
                    "naukri",
                    "nk-rich-description-1",
                    "Example Company",
                    "Python Developer",
                    "Bengaluru, India",
                    "https://example.com/rich-description",
                    None,
                    "unknown",
                    "A longer plain text description that should not replace the structured Markdown body.",
                )
                self.assertEqual(upsert_jobs([older_payload], BASE_CONFIG), 0)

                with patch.object(radar, "get_config", return_value=BASE_CONFIG):
                    result_after = radar.jobs(minutes=10080, limit=10, q="pandas")
                item_after = next(
                    entry for entry in result_after["jobs"]
                    if entry["source_job_id"] == "nk-rich-description-1"
                )
                self.assertEqual(item_after["description_format"], "markdown")
                self.assertEqual(item_after["description"], job["description"])
                self.assertEqual(item_after["source_details"], source_details)
            finally:
                radar.DB_PATH = original_db

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



    def test_canonical_evaluation_ledger_and_dashboard_api_stay_consistent_when_delivery_disabled(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                config = {
                    **BASE_CONFIG,
                    "notifications_enabled": False,
                    "require_explicit_experience_for_alerts": False,
                }
                job = normalize_job(
                    "naukri",
                    "naukri-consistency-1",
                    "Acme Technologies",
                    "Software Engineer",
                    "Bengaluru, Karnataka, India",
                    "https://example.test/jobs/consistency-1",
                    None,
                    "unknown",
                    "Build Python services. 2 years experience.",
                )

                self.assertEqual(upsert_jobs([job], config), 1)
                self.assertEqual(radar.refresh_notification_decisions(config), 1)

                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    persisted = conn.execute(
                        """
                        SELECT j.id, j.canonical_opportunity_id,
                               e.match, e.score, e.reasons_json,
                               e.experience_min_years, e.experience_max_years,
                               nl.status, nl.candidate_job_id,
                               nl.decision_reason_json
                        FROM jobs j
                        JOIN job_evaluations e ON e.job_id=j.id
                        JOIN notification_ledger nl
                          ON nl.canonical_opportunity_id=j.canonical_opportunity_id
                        WHERE j.source='naukri'
                          AND j.source_job_id='naukri-consistency-1'
                        """
                    ).fetchone()

                self.assertIsNotNone(persisted)
                opportunity_id = persisted["canonical_opportunity_id"]
                api_job = next(
                    item for item in radar.jobs(minutes=10080, limit=500)["jobs"]
                    if item["source_job_id"] == "naukri-consistency-1"
                )
                api_opportunity = next(
                    item for item in radar.opportunities(minutes=10080, limit=500)["opportunities"]
                    if item["id"] == opportunity_id
                )
                detail = radar.opportunity_detail(opportunity_id)
                queue = radar.notification_queue(limit=500)["notifications"]

                expected_match_reasons = json.loads(persisted["reasons_json"])
                expected_decision_reasons = json.loads(persisted["decision_reason_json"])

                self.assertTrue(bool(persisted["match"]))
                self.assertEqual(api_job["canonical_opportunity_id"], opportunity_id)
                self.assertTrue(api_job["likely_match"])
                self.assertEqual(api_job["match_score"], persisted["score"])
                self.assertEqual(api_job["match_reasons"], expected_match_reasons)
                self.assertEqual(
                    api_job["experience_min_years"],
                    persisted["experience_min_years"],
                )
                self.assertEqual(
                    api_job["experience_max_years"],
                    persisted["experience_max_years"],
                )
                self.assertEqual(persisted["status"], "pending")
                self.assertIsNone(persisted["candidate_job_id"])
                self.assertEqual(api_job["notification_status"], "pending")
                self.assertEqual(
                    api_job["notification_decision_reasons"],
                    expected_decision_reasons,
                )
                self.assertTrue(any(
                    "notifications disabled" in reason.lower()
                    for reason in expected_decision_reasons
                ))
                self.assertEqual(api_opportunity["id"], opportunity_id)
                self.assertEqual(api_opportunity["observation_count"], 1)
                self.assertEqual(detail["opportunity"]["id"], opportunity_id)
                self.assertEqual(len(detail["observations"]), 1)
                self.assertEqual(
                    detail["observations"][0]["source_job_id"],
                    "naukri-consistency-1",
                )
                self.assertFalse(any(
                    item["canonical_opportunity_id"] == opportunity_id
                    for item in queue
                ))
            finally:
                radar.DB_PATH = original_db




class DedupeCandidatesSourceCoverageTests(unittest.TestCase):
    def test_dedupe_candidates_includes_ashby_from_collector_registry(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("""
                        CREATE TABLE jobs (
                            id INTEGER PRIMARY KEY,
                            source TEXT NOT NULL,
                            source_job_id TEXT,
                            company TEXT,
                            title TEXT,
                            location TEXT,
                            url TEXT,
                            description TEXT
                        )
                    """)
                    conn.executemany(
                        "INSERT INTO jobs "
                        "(id, source, source_job_id, company, title, location, url, description) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            (1, "linkedin", "li-1", "Acme", "Software Engineer",
                             "Bengaluru", "https://example.com/jobs/1", "Python"),
                            (2, "ashby", "ashby-openai-1", "Acme", "Software Engineer",
                             "Bengaluru", "https://example.com/jobs/2", "Python"),
                        ],
                    )
                payload = radar.dedupe_candidates()
                self.assertEqual(payload["jobs_considered"], 2)
                self.assertTrue(any(
                    {item["source_a"], item["source_b"]} == {"linkedin", "ashby"}
                    for item in payload["candidates"]
                ))
            finally:
                radar.DB_PATH = original_db


class SourceRequestMetricsTests(unittest.TestCase):
    def test_tracked_requests_count_statuses_retries_exceptions_and_logical_work(self):
        responses = [
            type("Response", (), {"status_code": 503})(),
            type("Response", (), {"status_code": 200})(),
        ]
        original_metrics = dict(radar.active_source_metrics)
        try:
            with patch.object(
                radar.requests,
                "get",
                side_effect=[*responses, radar.requests.ConnectionError("private-value")],
            ):
                radar._begin_source_run_metrics("test-source")
                radar._tracked_source_get(
                    "test-source", "https://example.test/feed", params={"token": "private-value"}
                )
                radar._tracked_source_get(
                    "test-source", "https://example.test/feed", retry_attempt=True
                )
                with self.assertRaises(radar.requests.ConnectionError):
                    radar._tracked_source_get(
                        "test-source", "https://example.test/detail", retry_attempt=True
                    )
                radar._record_source_page("test-source", True)
                radar._record_source_page("test-source", False)
                radar._record_source_board("test-source", True)
                metrics = radar._finish_source_run_metrics("test-source")

            self.assertEqual(metrics["requests_attempted"], 3)
            self.assertEqual(metrics["responses_received"], 2)
            self.assertEqual(metrics["request_exceptions"], 1)
            self.assertEqual(metrics["http_2xx"], 1)
            self.assertEqual(metrics["http_5xx"], 1)
            self.assertEqual(metrics["retry_attempts"], 2)
            self.assertEqual(metrics["http_status_counts"], {"503": 1, "200": 1})
            self.assertGreaterEqual(metrics["request_duration_ms_total"], 0.0)
            self.assertEqual((metrics["pages_attempted"], metrics["pages_succeeded"], metrics["pages_failed"]), (2, 1, 1))
            self.assertEqual((metrics["boards_attempted"], metrics["boards_succeeded"], metrics["boards_failed"]), (1, 1, 0))
            self.assertNotIn("private-value", repr(metrics))
        finally:
            radar.active_source_metrics.clear()
            radar.active_source_metrics.update(original_metrics)

    def test_record_run_persists_request_metrics_and_source_status_aggregates_24h(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                finished = radar.now()
                metrics = {
                    **{field: 0 for field in radar.SOURCE_METRIC_FIELDS},
                    "requests_attempted": 4,
                    "responses_received": 4,
                    "http_2xx": 3,
                    "http_4xx": 1,
                    "http_429": 1,
                    "retry_attempts": 1,
                    "request_duration_ms_total": 125.5,
                    "pages_attempted": 2,
                    "pages_succeeded": 2,
                    "boards_attempted": 1,
                    "boards_succeeded": 1,
                    "http_status_counts": {"200": 3, "429": 1},
                }
                radar.record_run(
                    "linkedin", finished - radar.dt.timedelta(seconds=2), finished,
                    jobs_seen=25, new_jobs=4, request_metrics=metrics,
                )
                with (
                    patch.object(radar, "get_config", return_value={"source_enabled": {"linkedin": True}}),
                    patch.object(radar, "source_state", {}),
                ):
                    payload = radar.source_status()
                linkedin = next(item for item in payload["sources"] if item["source"] == "linkedin")
                self.assertEqual(linkedin["last_request_metrics"]["requests_attempted"], 4)
                self.assertEqual(linkedin["last_request_metrics"]["http_status_counts"], {"200": 3, "429": 1})
                self.assertEqual(linkedin["last_24h"]["runs"], 1)
                self.assertEqual(linkedin["last_24h"]["measured_runs"], 1)
                self.assertEqual(linkedin["last_24h"]["requests_attempted"], 4)
                self.assertEqual(linkedin["last_24h"]["http_429"], 1)
                self.assertEqual(linkedin["last_24h"]["jobs_seen"], 25)
                self.assertEqual(linkedin["last_24h"]["new_jobs"], 4)
                self.assertEqual(linkedin["last_24h"]["http_status_counts"], {"200": 3, "429": 1})
            finally:
                radar.DB_PATH = original_db

    def test_run_source_marks_mixed_employer_board_results_as_partial_failure(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                radar.init_db()
                def partial_collector(_config):
                    radar._record_source_board("greenhouse", True)
                    radar._record_source_board("greenhouse", False)
                    return [{"source": "greenhouse", "source_job_id": "g-1", "title": "Backend Engineer"}]

                collectors = dict(radar.COLLECTORS)
                collectors["greenhouse"] = partial_collector
                runtime_state = {}
                with (
                    patch.object(radar, "COLLECTORS", collectors),
                    patch.object(radar, "source_state", runtime_state),
                    patch.object(radar, "title_allowed", return_value=False),
                    patch.object(radar, "shadow_extract_jobs"),
                    patch.object(radar, "upsert_jobs", return_value=1),
                    patch.object(radar, "refresh_job_evaluations"),
                    patch.object(radar, "refresh_notification_decisions"),
                    patch("v2.telegram.credentials_available", return_value=False),
                ):
                    radar.run_source("greenhouse", {})
                with sqlite3.connect(radar.DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT outcome, boards_attempted, boards_succeeded, boards_failed "
                        "FROM source_runs WHERE source='greenhouse'"
                    ).fetchone()
                self.assertEqual(row, ("partial_failed", 2, 1, 1))
                self.assertEqual(runtime_state["greenhouse"]["last_run_outcome"], "partial_failed")
            finally:
                radar.DB_PATH = original_db


class NaukriRelayFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_db = radar.DB_PATH
        radar.DB_PATH = Path(self.temp_dir.name) / "jobs.db"
        self.addCleanup(setattr, radar, "DB_PATH", self.original_db)
        radar.init_db()

    def _payload(self, *, age_seconds=60, jobs=None, count=None, updated_at=None):
        jobs = jobs if jobs is not None else [{
            "id": "naukri-1",
            "url": "https://www.naukri.com/job-listings-naukri-1",
            "title": "Software Engineer",
            "company": "Example Labs",
            "location": "Bengaluru",
            "posted": "2026-11-07",
            "description": "Python services",
        }]
        return {
            "updated_at": updated_at or radar.iso(radar.now() - radar.dt.timedelta(seconds=age_seconds)),
            "count": len(jobs) if count is None else count,
            "jobs": jobs,
        }

    def _collect(self, payload):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return payload

        radar._begin_source_run_metrics("naukri")
        with patch.object(radar.requests, "get", return_value=Response()):
            return radar.naukri_collect()

    def test_rejects_stale_snapshot_and_keeps_last_good_feed_metadata(self):
        first = self._payload(age_seconds=60)
        self._collect(first)
        with sqlite3.connect(radar.DB_PATH) as conn:
            before = conn.execute(
                "SELECT feed_updated_at, payload_sha256, jobs_count FROM source_feed_state WHERE source='naukri'"
            ).fetchone()

        stale = self._payload(age_seconds=radar.NAUKRI_RELAY_MAX_AGE_SECONDS + 600)
        with self.assertRaisesRegex(RuntimeError, "snapshot is stale"):
            self._collect(stale)

        with sqlite3.connect(radar.DB_PATH) as conn:
            after = conn.execute(
                "SELECT feed_updated_at, payload_sha256, jobs_count FROM source_feed_state WHERE source='naukri'"
            ).fetchone()
        self.assertEqual(after, before)

    def test_rejects_relay_timestamp_too_far_in_the_future(self):
        future = radar.iso(
            radar.now() + radar.dt.timedelta(seconds=radar.NAUKRI_RELAY_FUTURE_TOLERANCE_SECONDS + 1)
        )
        with self.assertRaisesRegex(RuntimeError, "too far in the future"):
            self._collect(self._payload(updated_at=future))

    def test_rejects_empty_or_count_mismatched_snapshot(self):
        with self.assertRaisesRegex(RuntimeError, "snapshot is empty"):
            self._collect(self._payload(jobs=[], count=0))

        payload = self._payload(count=2)
        with self.assertRaisesRegex(RuntimeError, "count does not match"):
            self._collect(payload)

    def test_persists_snapshot_hash_and_reports_unchanged_feed(self):
        jobs = self._payload(age_seconds=30)["jobs"]
        jobs.append({
            "id": "naukri-2",
            "url": "https://www.naukri.com/job-listings-naukri-2",
            "title": "Python Developer",
            "company": "Example Two",
            "location": "Remote - India",
            "posted": "2026-11-07",
        })
        payload = self._payload(age_seconds=30, jobs=jobs)
        self._collect(payload)
        same_jobs_new_relay_run = {
            **payload,
            "updated_at": radar.iso(radar.now() - radar.dt.timedelta(seconds=10)),
            "jobs": list(reversed(jobs)),
        }
        self._collect(same_jobs_new_relay_run)

        with sqlite3.connect(radar.DB_PATH) as conn:
            state = conn.execute(
                "SELECT jobs_count, snapshot_unchanged, feed_age_seconds "
                "FROM source_feed_state WHERE source='naukri'"
            ).fetchone()
        self.assertEqual(state[0], 2)
        self.assertEqual(state[1], 1)
        self.assertGreaterEqual(state[2], 0)

        with (
            patch.object(radar, "get_config", return_value={"source_enabled": {"naukri": True}}),
            patch.object(radar, "source_state", {}),
        ):
            status = radar.source_status()
        naukri = next(item for item in status["sources"] if item["source"] == "naukri")
        self.assertEqual(naukri["last_feed"]["jobs_count"], 2)
        self.assertTrue(naukri["last_feed"]["snapshot_unchanged"])
        self.assertTrue(naukri["last_feed"]["fresh"])

    def test_unchanged_markdown_observation_does_not_recompute_evaluation(self):
        job = radar.normalize_job(
            "naukri", "naukri-markdown", "Example", "Software Engineer", "Bengaluru, India",
            "https://www.naukri.com/job-listings-naukri-markdown", None, "unknown",
            "Build Python APIs", description_format="markdown",
        )
        radar.upsert_jobs([job], BASE_CONFIG)
        with patch.object(radar, "_persist_job_evaluation") as evaluate:
            radar.upsert_jobs([job], BASE_CONFIG)
            evaluate.assert_not_called()

        changed = {**job, "description": "Build Python APIs and distributed services"}
        with patch.object(radar, "_persist_job_evaluation") as evaluate:
            radar.upsert_jobs([changed], BASE_CONFIG)
            evaluate.assert_called_once()


    def test_unchanged_existing_job_skips_matcher_write_but_updates_last_seen(self):
        first_seen = radar.now() - radar.dt.timedelta(minutes=2)
        job = radar.normalize_job(
            "naukri", "naukri-2", "Example", "Software Engineer", "Bengaluru, India",
            "https://www.naukri.com/job-listings-naukri-2", None, "unknown",
            "Build Python services",
        )
        job["discovered_at"] = radar.iso(first_seen)
        radar.upsert_jobs([job], BASE_CONFIG)

        next_seen = radar.iso(radar.now())
        repeated = {**job, "discovered_at": next_seen}
        with patch.object(radar, "_persist_job_evaluation") as evaluate:
            radar.upsert_jobs([repeated], BASE_CONFIG)
            evaluate.assert_not_called()

        with sqlite3.connect(radar.DB_PATH) as conn:
            last_seen = conn.execute(
                "SELECT last_seen_at FROM jobs WHERE source='naukri' AND source_job_id='naukri-2'"
            ).fetchone()[0]
        self.assertEqual(last_seen, next_seen)

        changed = {**repeated, "description": "Build Python services and resilient distributed systems"}
        with patch.object(radar, "_persist_job_evaluation") as evaluate:
            radar.upsert_jobs([changed], BASE_CONFIG)
            evaluate.assert_called_once()


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
                            error TEXT,
                            run_id TEXT,
                            outcome TEXT,
                            duration_seconds REAL,
                            error_type TEXT,
                            http_status INTEGER,
                            retry_after_seconds REAL,
                        cooldown_seconds INTEGER,
                        requests_attempted INTEGER,
                        responses_received INTEGER,
                        request_exceptions INTEGER,
                        http_2xx INTEGER,
                        http_3xx INTEGER,
                        http_4xx INTEGER,
                        http_5xx INTEGER,
                        http_429 INTEGER,
                        retry_attempts INTEGER,
                        request_duration_ms_total REAL,
                        http_status_counts_json TEXT,
                        pages_attempted INTEGER,
                        pages_succeeded INTEGER,
                        pages_failed INTEGER,
                        boards_attempted INTEGER,
                        boards_succeeded INTEGER,
                        boards_failed INTEGER
                        )
                    """)
                    for row in rows:
                        if len(row) == 6:
                            conn.execute(
                                "INSERT INTO source_runs "
                                "(source, started_at, finished_at, jobs_seen, new_jobs, error) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                row,
                            )
                        elif len(row) == 13:
                            conn.execute(
                                """
                                INSERT INTO source_runs (
                                    source, started_at, finished_at, jobs_seen, new_jobs, error,
                                    run_id, outcome, duration_seconds, error_type, http_status,
                                    retry_after_seconds, cooldown_seconds
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                row,
                            )
                        else:
                            raise AssertionError(f"Unsupported source_runs fixture row length: {len(row)}")
                with patch.object(
                    radar,
                    "get_config",
                    return_value={"source_enabled": {"linkedin": False, "naukri": True, "ashby": False}},
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

    def test_source_status_includes_ashby_from_collector_registry(self):
        payload = self._source_status_for_rows([
            (
                "ashby",
                "2026-10-12T10:00:00+00:00",
                "2026-10-12T10:01:00+00:00",
                12,
                3,
                None,
            )
        ])
        ashby = next(item for item in payload["sources"] if item["source"] == "ashby")
        self.assertFalse(ashby["enabled"])
        self.assertEqual(ashby["last_run"], "2026-10-12T10:01:00+00:00")
        self.assertEqual(ashby["jobs_seen"], 12)
        self.assertEqual(ashby["new_jobs"], 3)


    def test_source_status_includes_structured_run_metadata(self):
        payload = self._source_status_for_rows([
            (
                "linkedin",
                "2026-11-05T10:00:00+00:00",
                "2026-11-05T10:00:02+00:00",
                7,
                3,
                "HTTP 429",
                "run-abc123",
                "partial_rate_limited",
                2.0,
                "HTTPError",
                429,
                600.0,
                600,
            )
        ])
        linkedin = next(item for item in payload["sources"] if item["source"] == "linkedin")
        self.assertEqual(linkedin["last_run_id"], "run-abc123")
        self.assertEqual(linkedin["last_run_outcome"], "partial_rate_limited")
        self.assertEqual(linkedin["last_run_duration_seconds"], 2.0)
        self.assertEqual(linkedin["last_error_type"], "HTTPError")
        self.assertEqual(linkedin["last_http_status"], 429)
        self.assertEqual(linkedin["last_retry_after_seconds"], 600.0)
        self.assertEqual(linkedin["last_cooldown_seconds"], 600)

class SourceLatencySummaryTests(unittest.TestCase):
    def test_latency_summary_includes_ashby_samples(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("""
                        CREATE TABLE jobs (
                            source TEXT NOT NULL,
                            discovery_latency_seconds INTEGER,
                            discovered_at TEXT NOT NULL
                        )
                    """)
                    conn.executemany(
                        "INSERT INTO jobs (source, discovery_latency_seconds, discovered_at) VALUES (?, ?, ?)",
                        [
                            ("ashby", 60, "2026-10-12T10:00:00+00:00"),
                            ("ashby", 120, "2026-10-12T10:30:00+00:00"),
                            ("naukri", 30, "2026-10-12T10:30:00+00:00"),
                        ],
                    )
                fixed_now = radar.dt.datetime(2026, 10, 12, 12, tzinfo=radar.UTC)
                with patch.object(radar, "now", return_value=fixed_now):
                    payload = radar.latency_summary(hours=24)
                ashby = payload["sources"]["ashby"]
                self.assertEqual(ashby["samples"], 2)
                self.assertEqual(ashby["max_seconds"], 120)
                self.assertEqual(ashby["under_60_seconds"], 1)
            finally:
                radar.DB_PATH = original_db


    def test_init_db_migrates_legacy_source_run_table(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            with sqlite3.connect(db_path) as conn:
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
                conn.execute(
                    """INSERT INTO source_runs
                       (source, started_at, finished_at, jobs_seen, new_jobs, error)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("naukri", "2026-11-05T10:00:00+00:00", "2026-11-05T10:01:00+00:00", 12, 3, None),
                )
            with patch.object(radar, "DB_PATH", db_path):
                radar.init_db()
                with sqlite3.connect(db_path) as conn:
                    columns = {
                        row[1] for row in conn.execute("PRAGMA table_info(source_runs)")
                    }
                    preserved = conn.execute(
                        "SELECT source, jobs_seen, new_jobs, error FROM source_runs"
                    ).fetchone()
            self.assertTrue({
                "run_id", "outcome", "duration_seconds", "error_type",
                "http_status", "retry_after_seconds", "cooldown_seconds",
                "requests_attempted", "http_status_counts_json", "pages_attempted",
                "boards_attempted", "request_duration_ms_total",
            }.issubset(columns))
            self.assertEqual(preserved, ("naukri", 12, 3, None))

    def test_run_source_records_429_caught_inside_collector_as_partial_success(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE source_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT NOT NULL,
                        jobs_seen INTEGER NOT NULL,
                        new_jobs INTEGER NOT NULL,
                        error TEXT,
                        run_id TEXT,
                        outcome TEXT,
                        duration_seconds REAL,
                        error_type TEXT,
                        http_status INTEGER,
                        retry_after_seconds REAL,
                        cooldown_seconds INTEGER,
                        requests_attempted INTEGER,
                        responses_received INTEGER,
                        request_exceptions INTEGER,
                        http_2xx INTEGER,
                        http_3xx INTEGER,
                        http_4xx INTEGER,
                        http_5xx INTEGER,
                        http_429 INTEGER,
                        retry_attempts INTEGER,
                        request_duration_ms_total REAL,
                        http_status_counts_json TEXT,
                        pages_attempted INTEGER,
                        pages_succeeded INTEGER,
                        pages_failed INTEGER,
                        boards_attempted INTEGER,
                        boards_succeeded INTEGER,
                        boards_failed INTEGER
                    )
                """)
            original_rate_state = (
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
            response = type(
                "Response",
                (),
                {"status_code": 429, "headers": {"Retry-After": "600"}},
            )()
            job = {
                "title": "Backend Engineer",
                "description": "Python backend role",
                "location": "Bengaluru, India",
            }

            def collector(_config):
                radar._activate_linkedin_rate_limit(response)
                return [job]

            collectors = dict(radar.COLLECTORS)
            collectors["linkedin"] = collector
            cooldown_values = iter([0.0, 575.0])
            try:
                with (
                    patch.object(radar, "DB_PATH", db_path),
                    patch.object(radar, "COLLECTORS", collectors),
                    patch.object(
                        radar,
                        "source_state",
                        {"linkedin": {"last_success": "2026-11-05T09:00:00+00:00"}},
                    ),
                    patch.object(
                        radar,
                        "_linkedin_cooldown_remaining",
                        side_effect=lambda: next(cooldown_values),
                    ),
                    patch.object(radar, "title_allowed", return_value=False),
                    patch.object(radar, "shadow_extract_jobs"),
                    patch.object(radar, "upsert_jobs", return_value=1),
                    patch.object(radar, "refresh_job_evaluations"),
                    patch.object(radar, "refresh_notification_decisions"),
                    patch("v2.telegram.credentials_available", return_value=False),
                ):
                    radar.run_source("linkedin", {})
                    with sqlite3.connect(db_path) as conn:
                        row = conn.execute(
                            """
                            SELECT jobs_seen, new_jobs, outcome, http_status,
                                   retry_after_seconds, cooldown_seconds, error
                            FROM source_runs WHERE source='linkedin'
                            """
                        ).fetchone()
                    runtime = radar.source_state["linkedin"]
                self.assertEqual(row[:4], (1, 1, "partial_rate_limited", 429))
                self.assertEqual(row[4], 600.0)
                self.assertEqual(row[5], 600)
                self.assertEqual(row[6], "HTTP 429")
                self.assertEqual(runtime["last_run_outcome"], "partial_rate_limited")
                self.assertEqual(runtime["last_success"], "2026-11-05T09:00:00+00:00")
                self.assertEqual(runtime["rate_limit_retry_after_seconds"], 600.0)
                self.assertGreater(runtime["rate_limit_cooldown_seconds"], 0)
            finally:
                (
                    radar.linkedin_last_http_request_monotonic,
                    radar.linkedin_rate_limited_until_monotonic,
                    radar.linkedin_last_rate_limit_monotonic,
                    radar.linkedin_rate_limit_streak,
                    radar.linkedin_rate_limit_generation,
                ) = original_rate_state

    def test_run_source_persists_sanitized_429_and_preserves_cooldown(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE source_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT NOT NULL,
                        jobs_seen INTEGER NOT NULL,
                        new_jobs INTEGER NOT NULL,
                        error TEXT,
                        run_id TEXT,
                        outcome TEXT,
                        duration_seconds REAL,
                        error_type TEXT,
                        http_status INTEGER,
                        retry_after_seconds REAL,
                        cooldown_seconds INTEGER,
                        requests_attempted INTEGER,
                        responses_received INTEGER,
                        request_exceptions INTEGER,
                        http_2xx INTEGER,
                        http_3xx INTEGER,
                        http_4xx INTEGER,
                        http_5xx INTEGER,
                        http_429 INTEGER,
                        retry_attempts INTEGER,
                        request_duration_ms_total REAL,
                        http_status_counts_json TEXT,
                        pages_attempted INTEGER,
                        pages_succeeded INTEGER,
                        pages_failed INTEGER,
                        boards_attempted INTEGER,
                        boards_succeeded INTEGER,
                        boards_failed INTEGER
                    )
                """)
            response = type(
                "Response",
                (),
                {"status_code": 429, "headers": {"Retry-After": "600"}},
            )()
            error = radar.requests.HTTPError(
                "429 Too Many Requests for https://example.test/jobs?token=must-not-persist",
                response=response,
            )
            original_generation = radar.linkedin_rate_limit_generation
            try:
                radar.linkedin_rate_limit_generation = 0
                source_runtime = {
                    "rate_limited_until": "2026-11-05T10:10:00+00:00",
                    "rate_limit_cooldown_seconds": 600,
                    "rate_limit_retry_after_seconds": 600.0,
                }
                collectors = dict(radar.COLLECTORS)
                collectors["linkedin"] = lambda _config: (_ for _ in ()).throw(error)
                with (
                    patch.object(radar, "DB_PATH", db_path),
                    patch.object(radar, "COLLECTORS", collectors),
                    patch.object(radar, "source_state", {"linkedin": source_runtime}),
                    patch.object(radar, "_linkedin_cooldown_remaining", return_value=599.0),
                ):
                    radar.run_source("linkedin", {})
                    with sqlite3.connect(db_path) as conn:
                        row = conn.execute(
                            """
                            SELECT error, run_id, outcome, duration_seconds, error_type,
                                   http_status, retry_after_seconds, cooldown_seconds
                            FROM source_runs
                            WHERE source='linkedin'
                        """
                        ).fetchone()
                    runtime = radar.source_state["linkedin"]
                self.assertEqual(row[0], "HTTP 429")
                self.assertTrue(row[1])
                self.assertEqual(row[2], "rate_limited")
                self.assertGreaterEqual(row[3], 0.0)
                self.assertEqual(row[4], "HTTPError")
                self.assertEqual(row[5], 429)
                self.assertEqual(row[6], 600.0)
                self.assertEqual(row[7], 600)
                self.assertNotIn("must-not-persist", row[0])
                rate_limited_until = radar.parse_relative(runtime["rate_limited_until"])
                remaining_seconds = (rate_limited_until - radar.now()).total_seconds()
                self.assertGreaterEqual(remaining_seconds, 598)
                self.assertLessEqual(remaining_seconds, 600)
                self.assertEqual(runtime["rate_limit_cooldown_seconds"], 600)
                self.assertFalse(runtime["running"])
                self.assertEqual(runtime["run_id"], row[1])
            finally:
                radar.linkedin_rate_limit_generation = original_generation


class SourceRegistryApiCoverageTests(unittest.TestCase):
    def test_source_status_includes_every_registered_collector(self):
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
                            error TEXT,
                            run_id TEXT,
                            outcome TEXT,
                            duration_seconds REAL,
                            error_type TEXT,
                            http_status INTEGER,
                            retry_after_seconds REAL,
                            cooldown_seconds INTEGER,
                        requests_attempted INTEGER,
                        responses_received INTEGER,
                        request_exceptions INTEGER,
                        http_2xx INTEGER,
                        http_3xx INTEGER,
                        http_4xx INTEGER,
                        http_5xx INTEGER,
                        http_429 INTEGER,
                        retry_attempts INTEGER,
                        request_duration_ms_total REAL,
                        http_status_counts_json TEXT,
                        pages_attempted INTEGER,
                        pages_succeeded INTEGER,
                        pages_failed INTEGER,
                        boards_attempted INTEGER,
                        boards_succeeded INTEGER,
                        boards_failed INTEGER
                        )
                    """)
                with patch.object(
                    radar,
                    "get_config",
                    return_value={"source_enabled": {}},
                ), patch.object(radar, "source_state", {}):
                    payload = radar.source_status()
                self.assertEqual(
                    {item["source"] for item in payload["sources"]},
                    set(radar.COLLECTORS),
                )
                self.assertIn("ashby", {item["source"] for item in payload["sources"]})
            finally:
                radar.DB_PATH = original_db

    def test_latency_summary_includes_ashby(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("""
                        CREATE TABLE jobs (
                            source TEXT NOT NULL,
                            discovery_latency_seconds INTEGER,
                            discovered_at TEXT NOT NULL
                        )
                    """)
                    conn.execute(
                        "INSERT INTO jobs (source, discovery_latency_seconds, discovered_at) "
                        "VALUES (?, ?, ?)",
                        ("ashby", 125, radar.iso(radar.now())),
                    )
                payload = radar.latency_summary(hours=24)
                self.assertIn("ashby", payload["sources"])
                self.assertEqual(payload["sources"]["ashby"]["samples"], 1)
                self.assertEqual(payload["sources"]["ashby"]["p50_seconds"], 125)
            finally:
                radar.DB_PATH = original_db

    def test_dedupe_candidates_includes_ashby_observations(self):
        with TemporaryDirectory() as tmp:
            original_db = radar.DB_PATH
            try:
                radar.DB_PATH = Path(tmp) / "jobs.db"
                with sqlite3.connect(radar.DB_PATH) as conn:
                    conn.execute("""
                        CREATE TABLE jobs (
                            id INTEGER PRIMARY KEY,
                            source TEXT NOT NULL,
                            source_job_id TEXT NOT NULL,
                            company TEXT NOT NULL,
                            title TEXT NOT NULL,
                            location TEXT NOT NULL,
                            url TEXT NOT NULL,
                            description TEXT NOT NULL
                        )
                    """)
                    conn.executemany(
                        """
                        INSERT INTO jobs
                        (id, source, source_job_id, company, title, location, url, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                1, "linkedin", "li-123", "Example Corp",
                                "Backend Engineer", "Bengaluru, India",
                                "https://www.linkedin.com/jobs/view/123", "Python backend role",
                            ),
                            (
                                2, "ashby", "ashby-example-123", "Example Corp",
                                "Backend Engineer", "Bengaluru, India",
                                "https://jobs.example.com/backend-engineer", "Python backend role",
                            ),
                        ],
                    )
                payload = radar.dedupe_candidates(limit=100)
                self.assertEqual(payload["jobs_considered"], 2)
            finally:
                radar.DB_PATH = original_db


class AshbyCollectorTests(unittest.TestCase):
    def _response(self, payload):
        class Response:
            def raise_for_status(self): return None
            def json(self): return payload
        return Response()

    def _job(self, **overrides):
        item={"id":"role-123","title":"Software Engineer","location":{"name":"Remote - India"},
              "jobUrl":"https://jobs.ashbyhq.com/openai/role-123","descriptionHtml":"<p>Build Python systems.</p>",
              "publishedAt":"2026-10-12T10:20:30.123Z"}
        item.update(overrides)
        return item

    def test_valid_job_normalizes_id_url_and_description(self):
        with patch.object(radar.requests,"get",return_value=self._response({"jobs":[self._job()]})) as req:
            jobs=radar.ashby_collect({"ashby_boards":[{"board":"openai","company":"OpenAI"}]})
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]["source"],"ashby")
        self.assertEqual(jobs[0]["source_job_id"],"ashby-openai-role-123")
        self.assertEqual(jobs[0]["company"],"OpenAI")
        self.assertEqual(jobs[0]["title"],"Software Engineer")
        self.assertEqual(jobs[0]["location"],"Remote - India")
        self.assertEqual(jobs[0]["url"],"https://jobs.ashbyhq.com/openai/role-123")
        self.assertIn("Build Python systems.",jobs[0]["description"])
        self.assertEqual(jobs[0]["posted_precision"],"minute")
        self.assertEqual(req.call_args.kwargs["timeout"],15)

    def test_empty_jobs_list_returns_empty(self):
        with patch.object(radar.requests,"get",return_value=self._response({"jobs":[]})):
            self.assertEqual(radar.ashby_collect({"ashby_boards":[{"board":"openai","company":"OpenAI"}]}),[])

    def test_malformed_board_payload_does_not_discard_good_board(self):
        cfg={"ashby_boards":[{"board":"bad","company":"Bad"},{"board":"good","company":"Good"}]}
        def get(url,**kwargs):
            return self._response({"bad":True}) if "/bad" in url else self._response({"jobs":[self._job(id="ok")]})
        with patch.object(radar.requests,"get",side_effect=get):
            jobs=radar.ashby_collect(cfg)
        self.assertEqual([x["source_job_id"] for x in jobs],["ashby-good-ok"])

    def test_duplicate_ids_are_skipped(self):
        item=self._job()
        with patch.object(radar.requests,"get",return_value=self._response({"jobs":[item,item]})):
            jobs=radar.ashby_collect({"ashby_boards":[{"board":"openai","company":"OpenAI"}]})
        self.assertEqual(len(jobs),1)

    def test_missing_or_invalid_published_at_stays_unknown(self):
        self.assertEqual(radar._parse_ashby_published_at(None),(None,"unknown"))
        self.assertEqual(radar._parse_ashby_published_at("bad"),(None,"unknown"))
        item=self._job(publishedAt=None,updatedAt="2026-10-12T10:20:30Z")
        with patch.object(radar.requests,"get",return_value=self._response({"jobs":[item]})):
            jobs=radar.ashby_collect({"ashby_boards":[{"board":"openai","company":"OpenAI"}]})
        self.assertIsNone(jobs[0]["source_posted_at"])
        self.assertEqual(jobs[0]["posted_precision"],"unknown")

    def test_all_boards_failed_raises_source_error(self):
        with patch.object(radar.requests,"get",side_effect=RuntimeError("fixture failure")):
            with self.assertRaisesRegex(RuntimeError,"All configured Ashby boards failed"):
                radar.ashby_collect({"ashby_boards":[{"board":"bad","company":"Bad"}]})

    def test_v11_migration_forces_ashby_off(self):
        defaults={"config_version":11,"source_enabled":{"linkedin":True,"naukri":True,"instahyre":False,"greenhouse":False,"ashby":False},
                  "poll_seconds":{"linkedin":180,"naukri":300,"instahyre":600,"greenhouse":900,"ashby":1800},
                  "ashby_boards":[{"board":"openai","company":"OpenAI"}]}
        old={"config_version":10,"source_enabled":{"linkedin":True,"naukri":True,"instahyre":False,"greenhouse":False,"ashby":True},
             "poll_seconds":{"ashby":90}}
        migrated=_merge_config(defaults,old)
        self.assertEqual(migrated["config_version"],11)
        self.assertFalse(migrated["source_enabled"]["ashby"])
        self.assertEqual(migrated["ashby_boards"],defaults["ashby_boards"])

    def test_board_allowlist_rejects_duplicate_or_unsafe_names(self):
        base={**BASE_CONFIG,"source_enabled":{"linkedin":True,"naukri":True,"instahyre":False,"greenhouse":False,"ashby":False},
              "ashby_boards":[{"board":"safe","company":"OpenAI"},{"board":"SAFE","company":"Duplicate"}]}
        with self.assertRaises(radar.HTTPException): radar.validate_config(base)
        with self.assertRaises(radar.HTTPException):
            radar.validate_config({**BASE_CONFIG,"ashby_boards":[{"board":"../unsafe","company":"Bad"}]})


if __name__ == "__main__":
    unittest.main()
