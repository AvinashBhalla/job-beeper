from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from v2 import google_alerts_job_verifier as verifier


def job_html(**overrides):
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Senior Backend Engineer",
        "description": "<p>Build reliable Python services and REST APIs for customers.</p>",
        "datePosted": "2026-11-20",
        "validThrough": "2026-12-20T23:59:59Z",
        "hiringOrganization": {"@type": "Organization", "name": "ExampleCo"},
        "jobLocation": [{
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Gurugram",
                "addressRegion": "Haryana",
                "addressCountry": "IN",
            },
        }],
        "url": "https://jobs.example.test/roles/backend",
    }
    posting.update(overrides)
    return (
        "<html><head><link rel='canonical' href='https://jobs.example.test/roles/backend'>"
        "</head><body><script type='application/ld+json'>"
        + json.dumps(posting)
        + "</script></body></html>"
    )


class PublicJobVerifierTests(unittest.TestCase):
    def test_extracts_job_fields_from_public_jobposting_jsonld(self):
        def fake_fetch(url):
            if url.endswith("/robots.txt"):
                return url, "User-agent: *\nAllow: /\n"
            return url, job_html()

        with patch.object(verifier.board_discovery, "_public_https_url", side_effect=lambda value: value), patch.object(verifier.board_discovery, "_safe_fetch", side_effect=fake_fetch):
            result = verifier.verify_public_job_posting(
                "https://jobs.example.test/roles/backend?utm_source=alert"
            )
        self.assertEqual(result["title"], "Senior Backend Engineer")
        self.assertEqual(result["company"], "ExampleCo")
        self.assertEqual(result["location"], "Gurugram, Haryana, IN")
        self.assertIn("Python services", result["description"])
        self.assertEqual(result["verification_basis"], "public_jsonld_jobposting")
        self.assertEqual(result["url"], "https://jobs.example.test/roles/backend")

    def test_untrusted_jsonld_url_cannot_replace_validated_final_url(self):
        def fake_fetch(url):
            if url.endswith("/robots.txt"):
                return url, "User-agent: *\\nAllow: /\\n"
            return url, job_html(url="https://127.0.0.1/private")

        with patch.object(verifier.board_discovery, "_public_https_url", side_effect=lambda value: value), patch.object(verifier.board_discovery, "_safe_fetch", side_effect=fake_fetch):
            result = verifier.verify_public_job_posting(
                "https://jobs.example.test/roles/backend"
            )
        self.assertEqual(result["url"], "https://jobs.example.test/roles/backend")

    def test_rejects_robots_disallowed_destination_without_fetching_page(self):
        calls = []

        def fake_fetch(url):
            calls.append(url)
            return url, "User-agent: *\nDisallow: /roles/\n"

        with patch.object(verifier.board_discovery, "_public_https_url", side_effect=lambda value: value), patch.object(verifier.board_discovery, "_safe_fetch", side_effect=fake_fetch):
            with self.assertRaises(verifier.PublicJobVerificationError) as caught:
                verifier.verify_public_job_posting("https://jobs.example.test/roles/backend")
        self.assertEqual(caught.exception.code, "robots_policy_denied_or_unavailable")
        self.assertEqual(len(calls), 1)

    def test_rejects_expired_posting(self):
        def fake_fetch(url):
            if url.endswith("/robots.txt"):
                return url, "User-agent: *\nAllow: /\n"
            return url, job_html(validThrough="2020-01-01T00:00:00Z")

        with patch.object(verifier.board_discovery, "_public_https_url", side_effect=lambda value: value), patch.object(verifier.board_discovery, "_safe_fetch", side_effect=fake_fetch):
            with self.assertRaises(verifier.PublicJobVerificationError) as caught:
                verifier.verify_public_job_posting("https://jobs.example.test/roles/backend")
        self.assertEqual(caught.exception.code, "active_jobposting_evidence_missing")

    def test_rejects_posting_without_employer_or_title(self):
        def fake_fetch(url):
            if url.endswith("/robots.txt"):
                return url, "User-agent: *\nAllow: /\n"
            return url, job_html(hiringOrganization={"name": ""})

        with patch.object(verifier.board_discovery, "_public_https_url", side_effect=lambda value: value), patch.object(verifier.board_discovery, "_safe_fetch", side_effect=fake_fetch):
            with self.assertRaises(verifier.PublicJobVerificationError):
                verifier.verify_public_job_posting("https://jobs.example.test/roles/backend")

    def test_rejects_non_public_or_non_https_destination_before_fetch(self):
        with patch.object(verifier.board_discovery, "_safe_fetch") as safe_fetch:
            for url in (
                "http://jobs.example.test/roles/backend",
                "https://127.0.0.1/private",
                "https://localhost/private",
            ):
                with self.assertRaises(verifier.PublicJobVerificationError):
                    verifier.verify_public_job_posting(url)
            safe_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
