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
        self.assertEqual(len(manual), 8)
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


class AtsAdapterTests(unittest.TestCase):
    def test_workday_adapter_reads_public_cxs_jobs_and_description(self):
        company = {
            "name": "Example Workday",
            "careers_url": "https://example.wd1.myworkdayjobs.com/en-US/External",
            "scan_mode": "workday",
        }
        list_response = Mock()
        list_response.json.return_value = {
            "total": 1,
            "jobPostings": [{
                "title": "Software Engineer",
                "locationsText": "Bengaluru, India",
                "externalPath": "/job/Bengaluru/Software-Engineer_R123",
            }],
        }
        detail_response = Mock()
        detail_response.json.return_value = {
            "jobPostingInfo": {
                "title": "Software Engineer",
                "location": "Bengaluru, India",
                "jobDescription": "<p>React and JavaScript. 1 year experience.</p>",
                "externalUrl": "https://example.wd1.myworkdayjobs.com/en-US/External/job/123",
            }
        }
        client = Mock()
        client.post.return_value = list_response
        client.get.return_value = detail_response

        jobs = scan._workday(company, client)

        self.assertEqual(len(jobs), 1)
        self.assertIn("React", jobs[0]["description"])
        self.assertEqual(jobs[0]["source"], "workday")
        self.assertFalse(jobs[0]["generic"])
        self.assertIn("/wday/cxs/example/External/jobs", client.post.call_args.args[0])

    def test_workable_adapter_reads_public_widget_jobs(self):
        company = {
            "name": "Caxton Associates",
            "careers_url": "https://apply.workable.com/caxton/",
            "scan_mode": "workable",
        }
        response = Mock()
        response.json.return_value = {
            "jobs": [{
                "title": "Software Engineer",
                "shortcode": "ABC123",
                "description": "<p>Python and React. 1 year experience.</p>",
                "locations": [{"city": "Bengaluru", "country": "India", "hidden": False}],
            }]
        }
        client = Mock()
        client.get.return_value = response

        jobs = scan._workable(company, client)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["location"], "Bengaluru, India")
        self.assertIn("/caxton/j/ABC123/", jobs[0]["url"])
        self.assertIn("Python", jobs[0]["description"])

    def test_smartrecruiters_fetches_public_job_ad_details(self):
        company = {
            "name": "Example SmartRecruiters",
            "careers_url": "https://careers.smartrecruiters.com/example",
            "scan_mode": "smartrecruiters",
        }
        list_response = Mock()
        list_response.json.return_value = {
            "totalFound": 1,
            "content": [{
                "id": "123",
                "name": "Software Engineer",
                "location": {"city": "Bengaluru", "region": "Karnataka", "country": "in"},
            }],
        }
        detail_response = Mock()
        detail_response.json.return_value = {
            "postingUrl": "https://jobs.smartrecruiters.com/example/123",
            "jobAd": {"sections": {
                "jobDescription": {"text": "Build React applications."},
                "qualifications": {"text": "1 year of experience."},
            }},
        }
        client = Mock()
        client.get.side_effect = [list_response, detail_response]

        jobs = scan._smartrecruiters(company, client)

        self.assertEqual(len(jobs), 1)
        self.assertIn("React", jobs[0]["description"])
        self.assertIn("123", jobs[0]["url"])
        self.assertFalse(jobs[0]["generic"])

    def test_failure_classifier_distinguishes_access_denied_and_not_found(self):
        forbidden = scan.requests.Response()
        forbidden.status_code = 403
        not_found = scan.requests.Response()
        not_found.status_code = 404

        blocked = scan.classify_failure(scan.requests.HTTPError("403", response=forbidden))
        missing = scan.classify_failure(scan.requests.HTTPError("404", response=not_found))

        self.assertEqual(blocked["failure_category"], "blocked")
        self.assertEqual(missing["failure_category"], "not_found")
        self.assertEqual(blocked["status_code"], 403)



if __name__ == "__main__":
    unittest.main(verbosity=2)