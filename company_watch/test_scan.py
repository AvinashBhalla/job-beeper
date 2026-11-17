import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from company_watch import scan


class FilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.filters = scan.load_filters()

    def test_junior_india_role_is_match(self):
        job = {
            "title": "Frontend Software Engineer I",
            "location": "Bengaluru, Karnataka, India",
            "description": "Build React and TypeScript interfaces. 0-2 years of experience.",
        }
        verdict, reasons = scan.judge(job, self.filters)
        self.assertEqual(verdict, "match")
        self.assertTrue(reasons)

    def test_senior_title_is_rejected(self):
        job = {
            "title": "Senior Frontend Engineer",
            "location": "Bengaluru, India",
            "description": "React, TypeScript, 0-2 years experience.",
        }
        verdict, _ = scan.judge(job, self.filters)
        self.assertEqual(verdict, "reject")

    def test_non_india_location_is_rejected(self):
        job = {
            "title": "Software Engineer",
            "location": "Seattle, Washington, USA",
            "description": "JavaScript and React, 0-2 years experience.",
        }
        verdict, _ = scan.judge(job, self.filters)
        self.assertEqual(verdict, "reject")

    def test_generic_link_is_review_not_match(self):
        job = {
            "title": "Frontend Developer",
            "location": "",
            "description": "",
            "generic": True,
        }
        verdict, reasons = scan.judge(job, self.filters)
        self.assertEqual(verdict, "review")
        self.assertTrue(reasons)

    def test_explicit_three_year_minimum_is_rejected(self):
        job = {
            "title": "Software Developer",
            "location": "Bengaluru, India",
            "description": "React developer. 3-5 years of experience.",
        }
        verdict, _ = scan.judge(job, self.filters)
        self.assertEqual(verdict, "reject")

    def test_unspecified_years_are_review(self):
        job = {
            "title": "Software Engineer",
            "location": "Bengaluru, India",
            "description": "Build web applications using JavaScript and TypeScript.",
        }
        verdict, _ = scan.judge(job, self.filters)
        self.assertEqual(verdict, "review")

    def test_year_parser_handles_ranges_and_plus(self):
        self.assertEqual(scan.required_years("0-2 years of experience"), 0)
        self.assertEqual(scan.required_years("2+ years experience"), 2)
        self.assertEqual(scan.required_years("3 to 5 years required"), 3)
        self.assertIsNone(scan.required_years("experience preferred"))


class RegistryTests(unittest.TestCase):
    def test_all_hundred_urls_are_populated_and_manual_rows_disabled(self):
        rows = scan.load_companies()
        self.assertEqual(len(rows), 100)
        self.assertTrue(all(row["careers_url"].strip() for row in rows))
        manual = [row for row in rows if row["scan_enabled"].lower() != "true"]
        self.assertEqual(len(manual), 10)
        self.assertTrue(all(row["scan_mode"] == "manual_review" for row in manual))

    def test_search_pointers_are_not_scanned(self):
        rows = scan.load_companies()
        search_rows = [row for row in rows if "google.com/search" in row["careers_url"]]
        self.assertTrue(search_rows)
        self.assertTrue(all(row["scan_enabled"].lower() == "false" for row in search_rows))

    def test_state_load_migrates_legacy_url_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seen.json"
            path.write_text(json.dumps(["https://example.com/job/1"]), encoding="utf-8")
            state = scan.load_state(path)
            self.assertIn("https://example.com/job/1", state["seen_urls"])

    def test_jsonld_jobposting_is_extracted(self):
        from bs4 import BeautifulSoup
        html = '''<script type="application/ld+json">
        {"@context":"https://schema.org","@type":"JobPosting","title":"Software Engineer",
         "url":"https://example.com/jobs/1","description":"React, JavaScript, 0-2 years experience",
         "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":"Bengaluru","addressCountry":"India"}}}
        </script>'''
        soup = BeautifulSoup(html, "html.parser")
        company = {"name": "Example", "careers_url": "https://example.com/careers"}
        jobs = scan._jsonld_jobs(soup, company)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Software Engineer")
        self.assertIn("India", jobs[0]["location"])


if __name__ == "__main__":
    unittest.main(verbosity=2)