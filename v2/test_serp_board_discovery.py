"""Tests for licensed SERP-to-ATS candidate normalization."""
import datetime as dt
import unittest
from unittest.mock import patch

from v2 import radar, serp_board_discovery as serp


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeRequester:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


class SerpBoardDiscoveryTests(unittest.TestCase):
    def test_serper_query_is_provider_scoped_and_bounded(self):
        query = serp.build_serper_query(
            "workday", role_terms=["Software Engineer", "Python Developer"]
        )
        self.assertIn('site:myworkdayjobs.com', query)
        self.assertIn('"Software Engineer" OR "Python Developer"', query)
        with self.assertRaises(ValueError):
            serp.build_serper_query("workday", role_terms=[])

    def test_dataforseo_live_uses_structured_target_not_site_operator(self):
        payload = serp.build_dataforseo_live_payload("ashby")
        self.assertEqual(payload["target"], "*ashbyhq.com*")
        self.assertNotIn("site:", payload["keyword"])
        self.assertEqual(payload["location_code"], 2356)

    def test_normalizes_serper_results_to_unique_supported_board_candidates(self):
        payload = {"organic": [
            {"link": "https://jobs.ashbyhq.com/acme", "title": "Software Engineer"},
            {"link": "https://jobs.ashbyhq.com/acme/job-123", "title": "Role detail"},
            {"link": "https://example.com/careers", "title": "Careers"},
            {"link": "http://jobs.ashbyhq.com/not-secure", "title": "Bad scheme"},
            {"link": "https://jobs.lever.co/other", "title": "Wrong provider"},
        ]}
        captured = dt.datetime(2026, 11, 18, tzinfo=dt.timezone.utc)
        candidates = serp.normalize_serp_candidates(
            payload, "ashby", engine="serper",
            query='("Software Engineer") India site:ashbyhq.com',
            fetched_at=captured,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["board_url"], "https://jobs.ashbyhq.com/acme")
        self.assertEqual(candidates[0]["discovery_method"], "search_engine_serp")
        self.assertIn("rank=1", candidates[0]["source_reference"])
        self.assertEqual(candidates[0]["source_captured_at"], captured.isoformat())

    def test_normalizes_dataforseo_organic_items(self):
        payload = {"tasks": [{"result": [{"items": [
            {"type": "organic", "url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"},
            {"type": "paid", "url": "https://other.wd5.myworkdayjobs.com/en-US/Jobs"},
        ]}]}]}
        candidates = serp.normalize_serp_candidates(
            payload, "workday", engine="dataforseo_live",
            query="software engineer India",
        )
        self.assertEqual(len(candidates), 1)
        self.assertIn("NVIDIAExternalCareerSite", candidates[0]["board_url"])

    def test_only_google_url_redirects_are_unwrapped(self):
        payload = {"organic": [
            {"link": "https://www.google.com/url?q=https%3A%2F%2Fjobs.lever.co%2Facme"},
            {"link": "https://attacker.example/redirect?url=https://jobs.lever.co/evil"},
            {"link": "https://www.google.com/url?q=http%3A%2F%2Fjobs.lever.co%2Finsecure"},
        ]}
        candidates = serp.normalize_serp_candidates(
            payload, "lever", engine="serper", query="site:lever.co engineer",
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["board_url"], "https://jobs.lever.co/acme")

    def test_dataforseo_client_uses_secret_credentials_and_one_live_request(self):
        requester = FakeRequester({"tasks": []})
        result = serp.search_dataforseo_live(
            "workday", username="user", password="secret", requester=requester
        )
        self.assertEqual(result, {"tasks": []})
        self.assertEqual(len(requester.calls), 1)
        url, kwargs = requester.calls[0]
        self.assertEqual(url, serp.DATAFORSEO_LIVE_ENDPOINT)
        self.assertEqual(kwargs["auth"], ("user", "secret"))
        self.assertEqual(kwargs["json"][0]["target"], "*myworkdayjobs.com*")
        self.assertEqual(kwargs["timeout"], serp.SEARCH_TIMEOUT_SECONDS)

    def test_serper_client_uses_secret_key_and_india_english_locale(self):
        requester = FakeRequester({"organic": []})
        result = serp.search_serper(
            "ashby", api_key="test-key", requester=requester
        )
        self.assertEqual(result, {"organic": []})
        self.assertEqual(len(requester.calls), 1)
        url, kwargs = requester.calls[0]
        self.assertEqual(url, serp.SERPER_ENDPOINT)
        self.assertEqual(kwargs["headers"]["X-API-KEY"], "test-key")
        self.assertEqual(kwargs["json"]["gl"], "in")
        self.assertEqual(kwargs["json"]["hl"], "en")
        self.assertIn("site:ashbyhq.com", kwargs["json"]["q"])

    def test_provider_clients_fail_without_credentials_and_do_not_send_requests(self):
        requester = FakeRequester({"organic": []})
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                serp.search_serper("ashby", requester=requester)
            with self.assertRaises(RuntimeError):
                serp.search_dataforseo_live("ashby", requester=requester)
        self.assertEqual(requester.calls, [])

    def test_candidate_importer_accepts_serp_provenance_method(self):
        self.assertIn("search_engine_serp", radar.GLOBAL_DISCOVERY_METHODS)

    def test_invalid_provider_and_engine_fail_closed(self):
        with self.assertRaises(ValueError):
            serp.build_dataforseo_live_payload("linkedin")
        with self.assertRaises(ValueError):
            serp.normalize_serp_candidates(
                {}, "ashby", engine="browser_scrape", query="engineer",
            )


if __name__ == "__main__":
    unittest.main()
