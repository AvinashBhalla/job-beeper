import datetime as dt
import unittest
from unittest.mock import Mock, patch

from v2 import hirebase


class HirebaseClientTests(unittest.TestCase):
    def setUp(self):
        self._key_patch = patch.dict("os.environ", {"HIREBASE_API_KEY": "test-key-not-a-real-secret"})
        self._key_patch.start()
        self.payload = hirebase.provider_query("workday", limit=4)

    def tearDown(self):
        self._key_patch.stop()

    def test_provider_query_is_global_not_user_specific_and_is_capped(self):
        self.assertEqual(self.payload["job_board"], ["workday"])
        self.assertEqual(self.payload["geo_locations"], [{"country": "India"}])
        self.assertNotIn("job_titles", self.payload)
        self.assertNotIn("keywords", self.payload)
        self.assertEqual(self.payload["limit"], 4)
        with self.assertRaises(ValueError):
            hirebase.provider_query("workday", limit=5)
        with self.assertRaises(ValueError):
            hirebase.provider_query("unsupported", limit=1)

    def test_provider_query_uses_incremental_first_ingested_cursor(self):
        first = hirebase.provider_query("workday", limit=4)
        self.assertEqual(first["days_ago"], 7)
        self.assertEqual(first["sort_by"], "date_posted")
        self.assertNotIn("ingested_after", first)
        incremental = hirebase.provider_query(
            "workday", limit=3, ingested_after="2026-11-09T10:00:00+00:00"
        )
        self.assertNotIn("days_ago", incremental)
        self.assertEqual(incremental["ingested_after"], "2026-11-09T10:00:00+00:00")
        self.assertEqual(incremental["sort_by"], "first_ingested")
        self.assertEqual(incremental["sort_order"], "asc")
        self.assertEqual(incremental["limit"], 3)
        paged = hirebase.provider_query(
            "workday", limit=4, ingested_after="2026-11-09T10:00:00+00:00", page=5
        )
        self.assertEqual(paged["page"], 5)

    @patch.object(hirebase.requests, "request")
    def test_estimate_uses_non_metered_estimate_endpoint(self, request):
        response = Mock()
        response.status_code = 200
        response.is_redirect = False
        response.ok = True
        response.json.return_value = {"cost": 3}
        request.return_value = response
        self.assertEqual(hirebase.estimate(self.payload), 3)
        args, kwargs = request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "https://api.hirebase.org/v2/jobs/estimate")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertNotIn("x-api-key", str(kwargs["json"]))

    @patch.object(hirebase.requests, "request")
    def test_usage_summary_requires_jobs_meter_and_active_plan(self, request):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.is_redirect = False
        response.json.return_value = {
            "subscription_status": "active",
            "period_start": "2026-11-01T00:00:00Z",
            "period_end": "2026-12-01T00:00:00Z",
            "meters": [{
                "event_name": "m_jobs_api_calls", "used": 12,
                "included": 500, "remaining": 488, "overage_mode": "block",
            }],
        }
        request.return_value = response
        summary = hirebase.usage_summary()
        self.assertEqual(summary["remaining"], 488)
        self.assertEqual(summary["period_start"], "2026-11-01T00:00:00Z")

    @patch.object(hirebase.requests, "request")
    def test_usage_summary_supports_free_plan_with_calendar_month_utc(self, request):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.is_redirect = False
        response.json.return_value = {
            "subscription_status": None,
            "period_start": None,
            "period_end": None,
            "meters": [{
                "event_name": "m_jobs_api_calls", "used": 17,
                "included": 500, "remaining": 483, "overage_mode": "block",
            }],
        }
        request.return_value = response
        summary = hirebase.usage_summary()
        self.assertEqual(summary["subscription_status"], "free")
        self.assertEqual(summary["included"], 500)
        self.assertEqual(summary["remaining"], 483)
        start = dt.datetime.fromisoformat(summary["period_start"])
        end = dt.datetime.fromisoformat(summary["period_end"])
        self.assertEqual(start.day, 1)
        self.assertIn((end - start).days, {28, 29, 30, 31})
        self.assertEqual(start.tzinfo, dt.timezone.utc)

    @patch.object(hirebase.requests, "request")
    def test_usage_summary_fails_closed_when_meter_missing(self, request):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.is_redirect = False
        response.json.return_value = {"subscription_status": "active", "meters": []}
        request.return_value = response
        with self.assertRaisesRegex(hirebase.HirebaseError, "Jobs meter"):
            hirebase.usage_summary()

    @patch.object(hirebase.requests, "request")
    def test_search_requires_jobs_list_and_reads_usage_headers(self, request):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.is_redirect = False
        response.json.return_value = {
            "jobs": [{"_id": "abc"}], "page": 1, "limit": 4,
            "total_pages": 2, "total_count": 5,
        }
        response.headers = {
            "Hirebase-Usage-Meter": "m_jobs_api_calls",
            "Hirebase-Usage-Included-Used": "20",
            "Hirebase-Usage-Included-Remaining": "480",
        }
        request.return_value = response
        jobs, usage, pagination = hirebase.search(self.payload)
        self.assertEqual(jobs, [{"_id": "abc"}])
        self.assertEqual(usage["included_remaining"], 480)
        self.assertEqual(pagination["total_pages"], 2)
        self.assertEqual(pagination["total_count"], 5)

    @patch.object(hirebase.requests, "request")
    def test_redirect_and_quota_429_are_rejected_without_following(self, request):
        response = Mock()
        response.ok = False
        response.is_redirect = True
        response.status_code = 302
        request.return_value = response
        with self.assertRaisesRegex(hirebase.HirebaseError, "redirect"):
            hirebase.estimate(self.payload)
        response.is_redirect = False
        response.status_code = 429
        response.headers = {"X-Billing-Code": "limit_exceeded"}
        with self.assertRaisesRegex(hirebase.HirebaseError, "allowance"):
            hirebase.estimate(self.payload)

    def test_usage_headers_unknown_fails_closed(self):
        self.assertIsNone(hirebase.usage_from_headers({}))
        self.assertIsNone(hirebase.usage_from_headers({"Hirebase-Usage-Meter": "other"}))

    def test_local_budget_is_capped_by_provider_global_and_hirebase_remaining(self):
        summary = {"remaining": 485}
        self.assertEqual(hirebase.provider_allowance(
            summary, local_monthly_used=10, local_daily_used=2, provider_daily_used=1,
        ), 3)
        self.assertEqual(hirebase.provider_allowance(
            {"remaining": 0}, local_monthly_used=0, local_daily_used=0, provider_daily_used=0,
        ), 0)

    def test_parses_date_only_and_timezone_aware_timestamps(self):
        date_value, precision = hirebase.parse_posted_at("2026-11-09")
        self.assertEqual(precision, "date")
        self.assertEqual(date_value.date(), dt.date(2026, 11, 9))
        timestamp, precision = hirebase.parse_posted_at("2026-11-09T11:30:00Z")
        self.assertEqual(precision, "minute")
        self.assertEqual(timestamp.tzinfo, dt.timezone.utc)

    def test_normalizes_provider_job_and_rejects_invalid_application_links(self):
        item = {
            "_id": "id123", "job_title": "Python Engineer",
            "company_name": "Example", "application_link": "https://jobs.example.com/apply/1",
            "job_board": "workday", "location_raw": "Bengaluru",
            "locations": [{"city": "Bengaluru", "region": "Karnataka", "country": "India"}],
            "date_posted": "2026-11-09", "description": "<p>Python role</p>",
        }
        job = hirebase.normalize_provider_job(item)
        self.assertEqual(job["source"], "hirebase")
        self.assertEqual(job["source_job_id"], "workday:id123")
        self.assertEqual(job["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(job["posted_precision"], "date")
        self.assertIsNotNone(job["posted_at"])
        item["application_link"] = "http://jobs.example.com/apply/1"
        self.assertIsNone(hirebase.normalize_provider_job(item))
        item["application_link"] = "https://user:pass@jobs.example.com/apply/1"
        self.assertIsNone(hirebase.normalize_provider_job(item))
        item["application_link"] = "https://jobs.example.com:8443/apply/1"
        self.assertIsNone(hirebase.normalize_provider_job(item))
        item["application_link"] = "https://jobs.example.com/apply/1"
        item["description"] = "<p>Build <strong>reliable</strong> Python services.</p>"
        normalized = hirebase.normalize_provider_job(item)
        self.assertEqual(normalized["description"], "Build reliable Python services.")

    @patch.dict("os.environ", {"HIREBASE_API_KEY": ""})
    def test_missing_key_is_reported_without_network_call(self):
        with self.assertRaisesRegex(hirebase.HirebaseError, "not configured"):
            hirebase.usage_summary()


if __name__ == "__main__":
    unittest.main()
