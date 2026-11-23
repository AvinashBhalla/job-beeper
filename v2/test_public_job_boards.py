import json
import unittest
from unittest.mock import patch

import requests

from v2 import board_discovery, board_scheduler, public_job_boards, radar


def response(content, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = content.encode() if isinstance(content, str) else json.dumps(content).encode()
    result._content_consumed = True
    return result


RSS = """<rss xmlns:tt="https://teamtailor.com/locations"><channel><item>
  <title>Integrations Engineer</title><link>https://drdoctor.teamtailor.com/jobs/123-example</link>
  <guid>sample-uuid</guid><pubDate>Mon, 16 Nov 2026 10:25:07 +0100</pubDate>
  <description><![CDATA[<p>2+ years of Python.</p>]]></description><remoteStatus>hybrid</remoteStatus>
  <tt:locations><tt:location><tt:city>Puducherry</tt:city><tt:country>India</tt:country></tt:location></tt:locations>
</item><item><title>Outside</title><link>https://example.com/jobs/124</link></item></channel></rss>"""


class PublicJobBoardTests(unittest.TestCase):
    def test_teamtailor_uses_the_same_board_for_discovery_scheduler_and_collection(self):
        candidate = board_discovery.detect_ats_board("https://drdoctor.teamtailor.com/jobs/123-example?ref=public")
        self.assertEqual(candidate["board_url"], "https://drdoctor.teamtailor.com/jobs")
        self.assertEqual(candidate["collector_source"], "teamtailor")
        with patch.object(board_discovery.requests, "get", return_value=response(RSS)):
            self.assertEqual(board_discovery.probe_public_board(candidate)["jobs_observed"], 1)
        config = radar._default_config()
        config["source_enabled"] = {"teamtailor": True}
        config["teamtailor_boards"] = [{"careers_url": candidate["board_url"], "company": "DrDoctor"}]
        config = radar.validate_config(config)
        self.assertEqual(board_scheduler.configured_boards(config)[0]["host_key"], "drdoctor.teamtailor.com")
        with patch.object(radar, "_tracked_source_get", return_value=response(RSS)) as get:
            job, = radar.COLLECTORS["teamtailor"](config)
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertEqual(job["source_job_id"], "teamtailor:drdoctor:sample-uuid")
        self.assertEqual(job["location"], "Puducherry, India")
        self.assertEqual(job["source_details"]["workplace_type"], "hybrid")
        self.assertEqual(job["posted_precision"], "minute")
        self.assertIn("2+ years of Python", job["description"])
        self.assertIn("teamtailor", radar.INITIAL_SNAPSHOT_BASELINE_SOURCES)

    def test_bamboohr_detail_reads_job_description_and_ignores_form_fields(self):
        board = public_job_boards.detect("https://example.bamboohr.com/careers/23")
        listing = {"result": [{"id": "23", "jobOpeningName": "Data Engineer"}]}
        detail = {"result": {"jobOpening": {
            "description": "<p>Experience with SQL</p>", "datePosted": "2026-11-22",
            "atsLocation": {"city": "Pune", "province": "Maharashtra", "country": "India"},
        }, "formFields": [{"description": "must not be retained"}]}}
        with patch.object(requests, "get", side_effect=[response(listing), response(detail)]) as get:
            job, = public_job_boards.list_jobs(board, get)
            public_job_boards.hydrate(board, job, get)
        self.assertEqual(job.locations, ["Pune, Maharashtra, India"])
        self.assertEqual(job.precision, "date")
        self.assertEqual(job.description, "Experience with SQL")
        self.assertNotIn("must not be retained", str(job))
        self.assertEqual(get.call_args.args[0], "https://example.bamboohr.com/careers/23/detail")

    def test_shared_hostname_portal_stays_within_employer_path(self):
        board = public_job_boards.detect("https://jobs.jobvite.com/Acme/job/AbCd")
        body = '<a href="/Another/job/AbCd">Other company</a><a href="/Acme/job/AbCd">Analyst</a>'
        with patch.object(requests, "get", return_value=response(body)) as get:
            job, = public_job_boards.list_jobs(board, get)
        self.assertEqual(job.id, "AbCd")
        self.assertEqual(job.url, "https://jobs.jobvite.com/Acme/job/AbCd")
        self.assertEqual(board.host, "jobs.jobvite.com")

    def test_feed_rejects_redirect_dtd_and_oversized_body(self):
        board = public_job_boards.detect("https://career.teamtailor.com/jobs")
        for body, status, message in [
            (RSS, 302, "response status"),
            ("<!DOCTYPE rss><rss/>", 200, "Document type"),
        ]:
            with patch.object(requests, "get", return_value=response(body, status)) as get:
                with self.assertRaisesRegex(ValueError, message):
                    public_job_boards.list_jobs(board, get)
        with patch.object(public_job_boards, "MAX_BODY_BYTES", 8):
            with patch.object(requests, "get", return_value=response(RSS)) as get:
                with self.assertRaisesRegex(ValueError, "response limit"):
                    public_job_boards.list_jobs(board, get)

    def test_invalid_board_and_pending_detail_are_rejected_at_their_boundaries(self):
        for url in ["https://career.teamtailor.com.evil.example/jobs", "https://name@career.teamtailor.com/jobs"]:
            self.assertIsNone(public_job_boards.detect(url))
        result = radar.alertability_details({"source": "jobvite"}, {"match": True}, {})
        self.assertFalse(result["alertable"])
        self.assertIn("employer job description", result["reasons"][0])
