"""Tests for licensed SERP-to-ATS candidate normalization."""
import datetime as dt
import unittest

from v2 import radar, serp_board_discovery as serp


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
