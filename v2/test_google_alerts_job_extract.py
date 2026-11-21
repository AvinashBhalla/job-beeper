from __future__ import annotations

import datetime as dt
import json
import unittest

from v2.google_alerts_job_extract import extract_jobposting_jsonld

UTC = dt.timezone.utc
FIXED_NOW = dt.datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
PAGE_URL = "https://jobs.example.com/postings/software-engineer-123"


def html_with_jsonld(document):
    return (
        "<!doctype html><html><head><title>Search page title</title>"
        '<script type="application/ld+json">'
        + json.dumps(document)
        + "</script></head><body><h1>Visible title</h1></body></html>"
    )


class GoogleAlertsJobPostingExtractionTests(unittest.TestCase):
    def test_extracts_valid_jobposting_from_jsonld(self):
        html = html_with_jsonld({
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Software Engineer",
            "description": "<p>Build APIs with <b>Python</b> &amp; React.</p>",
            "datePosted": "2026-11-20",
            "validThrough": "2026-12-31T23:59:00Z",
            "employmentType": ["FULL_TIME", "FULL_TIME"],
            "hiringOrganization": {"@type": "Organization", "name": "Example Labs"},
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Bengaluru",
                    "addressRegion": "Karnataka",
                    "addressCountry": {"@type": "Country", "name": "India"},
                },
            },
        })

        result = extract_jobposting_jsonld(html, PAGE_URL, now=FIXED_NOW)

        self.assertEqual(result.status, "verified")
        self.assertIsNone(result.reason)
        job = result.job
        self.assertEqual(job["title"], "Software Engineer")
        self.assertEqual(job["company"], "Example Labs")
        self.assertEqual(job["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(job["description"], "Build APIs with Python & React.")
        self.assertEqual(job["source_posted_at"], dt.datetime(2026, 11, 20, tzinfo=UTC))
        self.assertEqual(job["posted_precision"], "day")
        self.assertEqual(job["source_details"]["employment_type"], "FULL_TIME")
        self.assertEqual(job["url"], PAGE_URL)
        self.assertEqual(len(job["source_job_id"]), 40)

    def test_supports_graph_and_telecommute_location_requirements(self):
        html = html_with_jsonld({
            "@graph": [
                {"@type": "Organization", "name": "Employer"},
                {
                    "@type": "https://schema.org/JobPosting",
                    "title": "Remote Backend Engineer",
                    "hiringOrganization": {"name": "Graph Labs"},
                    "jobLocationType": "TELECOMMUTE",
                    "applicantLocationRequirements": {
                        "@type": "Country",
                        "name": "India",
                    },
                },
            ]
        })
        result = extract_jobposting_jsonld(html, PAGE_URL, now=FIXED_NOW)
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.job["location"], "Remote - India")
        self.assertEqual(result.job["company"], "Graph Labs")

    def test_expired_posting_is_rejected(self):
        html = html_with_jsonld({
            "@type": "JobPosting",
            "title": "Expired Engineer",
            "hiringOrganization": {"name": "Old Corp"},
            "validThrough": "2026-11-20T23:59:59Z",
        })
        result = extract_jobposting_jsonld(html, PAGE_URL, now=FIXED_NOW)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.reason, "posting_expired")
        self.assertIsNone(result.job)

    def test_missing_company_is_needs_review_not_guessed(self):
        html = html_with_jsonld({
            "@type": "JobPosting",
            "title": "Engineer",
            "description": "A plausible job but no hiring organization.",
        })
        result = extract_jobposting_jsonld(html, PAGE_URL, now=FIXED_NOW)
        self.assertEqual(result.status, "needs_review")
        self.assertEqual(result.reason, "jobposting_missing_required_fields")
        self.assertIsNone(result.job)

    def test_no_jobposting_jsonld_goes_to_review(self):
        html = html_with_jsonld({
            "@type": "Organization",
            "name": "Not a job",
        })
        result = extract_jobposting_jsonld(html, PAGE_URL, now=FIXED_NOW)
        self.assertEqual(result.status, "needs_review")
        self.assertEqual(result.reason, "jobposting_jsonld_not_found")

    def test_rejects_non_https_or_invalid_final_page_url(self):
        html = html_with_jsonld({
            "@type": "JobPosting",
            "title": "Engineer",
            "hiringOrganization": {"name": "Example"},
        })
        for url in ("http://jobs.example.com/1", "https://user:pass@jobs.example.com/1", "not-a-url"):
            with self.subTest(url=url):
                result = extract_jobposting_jsonld(html, url, now=FIXED_NOW)
                self.assertEqual(result.status, "needs_review")
                self.assertEqual(result.reason, "invalid_final_url")

    def test_ignores_malformed_jsonld_and_continues(self):
        html = (
            '<script type="application/ld+json">{broken json}</script>'
            + html_with_jsonld({
                "@type": "JobPosting",
                "title": "Engineer",
                "hiringOrganization": {"name": "Valid Org"},
            })
        )
        result = extract_jobposting_jsonld(html, PAGE_URL, now=FIXED_NOW)
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.job["company"], "Valid Org")


if __name__ == "__main__":
    unittest.main()
