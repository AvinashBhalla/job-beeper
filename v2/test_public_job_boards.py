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
PUBLIC_DNS_RESULT = [(None, None, None, None, ("1.1.1.1", 443))]


class PublicJobBoardTests(unittest.TestCase):
    def test_teamtailor_uses_the_same_board_for_discovery_scheduler_and_collection(self):
        candidate = board_discovery.detect_ats_board("https://drdoctor.teamtailor.com/jobs/123-example?ref=public")
        self.assertEqual(candidate["board_url"], "https://drdoctor.teamtailor.com/jobs")
        self.assertEqual(candidate["collector_source"], "teamtailor")
        with patch.object(board_discovery.socket, "getaddrinfo", return_value=PUBLIC_DNS_RESULT), patch.object(
            board_discovery.requests, "get", return_value=response(RSS),
        ):
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

    def test_oracle_uses_site_scoped_requests_and_preserves_day_precision(self):
        board = public_job_boards.detect(
            "https://tenant.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/0123"
        )
        listing = {"items": [{"requisitionList": [
            {"Id": "0123", "Title": "Backend Engineer", "PostedDate": "2026-11-22", "PrimaryLocation": "Pune, India"},
        ]}]}
        detail = {"items": [{
            "Id": "0123", "ExternalDescriptionStr": "<p>Build with Go.</p>",
            "ExternalQualificationsStr": "<p>Three years of software development.</p>",
            "InternalQualificationsStr": "internal data excluded",
        }]}
        with patch.object(requests, "get", side_effect=[response(listing), response(detail)]) as get:
            job, = public_job_boards.list_jobs(board, get)
            public_job_boards.hydrate(board, job, get)
        self.assertEqual(job.id, "0123")
        self.assertEqual(job.precision, "date")
        self.assertEqual(job.locations, ["Pune, India"])
        self.assertIn("Three years", job.description)
        self.assertNotIn("internal data", job.description)
        self.assertIn("siteNumber=CX_1", get.call_args.kwargs["params"]["finder"])

    def test_avature_follows_advertised_offsets_without_changing_host(self):
        board = public_job_boards.detect("https://employer.avature.net/careers/SearchJobs")
        first = """<article><h3><a href="/careers/JobDetail/Engineer/1">Engineer</a></h3>
            <span class="list-item-location">Pune, India</span></article>
            <a href="/careers/SearchJobs/?jobRecordsPerPage=12&amp;jobOffset=12">2</a>"""
        second = '<h3><a href="/careers/JobDetail/Analyst/2">Analyst</a></h3>'
        with patch.object(requests, "get", side_effect=[response(first), response(second)]) as get:
            jobs = public_job_boards.list_jobs(board, get)
        self.assertEqual([job.id for job in jobs], ["1", "2"])
        self.assertEqual(jobs[0].locations, ["Pune, India"])
        self.assertEqual(get.call_args.args[0], board.url + "/")
        self.assertEqual(get.call_args.kwargs["params"]["jobOffset"], 12)

    def test_cutshort_keeps_employer_skills_and_explicit_experience(self):
        slug = "software-engineering-jobs"
        document = {"props": {"pageProps": {"dehydratedState": {"queries": [{
            "queryKey": ["jobListData", slug],
            "state": {"data": {"data": {"pageData": {"jobs": [{
                "_id": "a" * 24, "headline": "Backend Engineer", "publicUrl": "https://cutshort.io/job/sample-posting",
                "companyDetails": {"name": "Example"}, "expRange": {"min": 3, "max": 5},
                "allSkills": ["Go", "SQL"], "locations": ["Bengaluru"], "sanitizedComment": "<p>Build services.</p>",
            }]}}}},
        }]}}}}
        page = '<script type="application/json" id="__NEXT_DATA__">' + json.dumps(document) + "</script>"
        config = {"cutshort_boards": [{"careers_url": f"https://cutshort.io/jobs/{slug}", "company": "Cutshort"}]}
        with patch.object(radar, "_tracked_source_get", return_value=response(page)):
            job, = radar.COLLECTORS["cutshort"](config)
        self.assertEqual(job["company"], "Example")
        self.assertEqual(job["source_details"]["key_skills"], ["Go", "SQL"])
        self.assertEqual(radar._experience_provenance_details(job), {
            "min_years": 3, "max_years": 5, "provenance": "employer_stated", "confidence": "high",
        })

    def test_hrsmart_submits_only_the_public_search_form_on_the_verified_host(self):
        board = public_job_boards.detect("https://example.hua.hrsmart.com/hr/ats/Posting/view/15")
        form = ('<form id="jobSearchForm" action="/hr/ats/JobSearch/search">'
                '<input type="hidden" name="submittedFormId" value="public-form">'
                '<input type="text" name="with_all" value="ignored"></form>')
        results = '<a href="/hr/ats/Posting/view/15?ref=example">Analyst</a>'
        with patch.object(board_discovery.socket, "getaddrinfo", return_value=PUBLIC_DNS_RESULT), patch.object(
            requests.Session, "get", return_value=response(form),
        ), patch.object(
            requests.Session, "post", return_value=response(results),
        ) as post:
            candidate = board_discovery.detect_ats_board(board.url)
            verified = board_discovery.probe_public_board(candidate)
        self.assertEqual(verified["jobs_observed"], 1)
        self.assertEqual(post.call_args.args[0], "https://example.hua.hrsmart.com/hr/ats/JobSearch/search")
        self.assertEqual(post.call_args.kwargs["data"], {"submittedFormId": "public-form", "with_all": ""})
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

    def test_ukg_keeps_board_host_posting_timestamp_and_braces_in_description(self):
        url = "https://recruiting2.ultipro.ca/SAMPLE/JobBoard/5ff80775-069d-4e87-9adc-94455820b5c9"
        board = public_job_boards.detect(url)
        job_id = "5cdb53c0-4ac2-42ff-8deb-64c8c4d4f364"
        listing = {"totalCount": 1, "opportunities": [{
            "Id": job_id, "Title": "Business Systems Owner", "PostedDate": "2026-11-20T20:21:15.106Z",
        }]}
        details = {"Id": job_id, "Description": "<p>Use templates with {variables}.</p>"}
        html = "<script>new US.Opportunity.CandidateOpportunityDetail(" + json.dumps(details) + ");</script>"
        with patch.object(requests, "get", side_effect=[response(listing), response(html)]) as get:
            job, = public_job_boards.list_jobs(board, get)
            self.assertEqual(get.call_args.kwargs["json_body"]["opportunitySearch"]["Top"], 50)
            public_job_boards.hydrate(board, job, get)
        self.assertEqual(job.url, f"{url}/OpportunityDetail?opportunityId={job_id}")
        self.assertEqual(job.precision, "minute")
        self.assertEqual(job.description, "Use templates with {variables}.")

    def test_phenom_uses_verified_employer_host_and_date_only_list_value(self):
        board = public_job_boards.detect("https://www.careers.philips.com/global/en/search-results")
        data = {"eagerLoadRefineSearch": {"data": {"jobs": [{
            "jobSeqNo": "PHILUS123ENGLOBAL", "title": "Engineer", "postedDate": "2026-11-18T00:00:00.000+0000",
            "cityStateCountry": "Pune, Maharashtra, India", "remote": "Hybrid",
        }]}}}
        page = "<script>phApp.ddo=" + json.dumps(data) + ";</script>"
        with patch.object(requests, "get", return_value=response(page)) as get:
            job, = public_job_boards.list_jobs(board, get, probe=True)
        self.assertEqual(job.url, "https://www.careers.philips.com/global/en/job/PHILUS123ENGLOBAL")
        self.assertEqual(job.precision, "date")
        self.assertEqual(job.locations, ["Pune, Maharashtra, India"])
        self.assertEqual(job.details["workplace_type"], "hybrid")
        self.assertIsNone(public_job_boards.detect("https://unverified.example/global/en/search-results"))

    def test_zoho_preserves_page_name_and_only_keeps_public_job_fields(self):
        url = "https://sample.zohorecruit.com/jobs/Engineering"
        board = public_job_boards.detect(url + "/1234/Data-Engineer")
        listing = {"data": [
            {"id": "1234", "Posting_Title": "Data Engineer", "Publish": True, "City": "Pune",
             "Country": "India", "$url": "https://unexpected.example/"},
            {"id": "9999", "Posting_Title": "Draft", "Publish": False},
        ]}
        detail = {"data": [{
            "id": "1234", "Posting_Title": "Data Engineer", "Publish": True,
            "Date_Opened": "2026-11-18", "Job_Description": "<p>Three years with Python.</p>",
            "Remote_Job": "Yes", "Assigned_Recruiter": {"email": "recruiter@example.invalid"},
        }]}
        with patch.object(requests, "get", side_effect=[response(listing), response(detail)]) as get:
            job, = public_job_boards.list_jobs(board, get)
            self.assertEqual(get.call_args.kwargs["params"], {"pagename": "Engineering"})
            public_job_boards.hydrate(board, job, get)
        self.assertEqual(job.url, url + "/1234")
        self.assertEqual(job.locations, ["Pune, India"])
        self.assertEqual(job.description, "Three years with Python.")
        self.assertEqual(job.details["workplace_type"], "remote")
        self.assertEqual(job.details["date_opened"], "2026-11-18")
        self.assertIsNone(job.published_at)
        self.assertNotIn("recruiter@", str(job))

    def test_taleo_replays_the_anonymous_listing_and_detail_with_the_session(self):
        board = public_job_boards.detect("https://example.taleo.net/careersection/100/jobdetail.ftl?job=1234")
        form = ('<form id="ftlform"><input name="ftlpageid" type="hidden" value="public-page">'
                '<input name="csrftoken" type="hidden" value="anonymous-form-state"></form>')
        listing = "Ignored!$!requisitionListInterface!|!validateTimeZoneId!$!" + "!|!".join([
            "1234", "Software Engineer", "1234", "Software Engineer", *["1234"] * 5,
            "", "Nov 22, 2026", "REQ-42",
        ])
        description = (
            "!*!%3Cp%3ELocation%3A Chicago, Illinois%3C/p%3E%3Cp%3EBuild with Python.%3C/p%3E"
            "%3Cp%3ENine (9) years of work experience are required.%3C/p%3E"
        )
        detail = "Ignored!$!requisitionDescriptionInterface!|!validateTimeZoneId!$!" + "!|!".join([
            "Software Engineer", description, description,
        ])
        with patch.object(requests, "get", side_effect=[
            response(form), response(listing), response(form), response(detail),
        ]) as get:
            job, = public_job_boards.list_jobs(board, get)
            landing, search = get.call_args_list[:2]
            self.assertIs(landing.kwargs["session"], search.kwargs["session"])
            self.assertEqual(search.args[0], "https://example.taleo.net/careersection/100/jobsearch.ajax")
            public_job_boards.hydrate(board, job, get)
        self.assertEqual(job.url, "https://example.taleo.net/careersection/100/jobdetail.ftl?job=1234")
        self.assertEqual(job.precision, "date")
        self.assertEqual(job.locations, ["Chicago, Illinois"])
        self.assertEqual(job.description.count("Build with Python."), 1)
        self.assertEqual(job.details, {"requisition_number": "REQ-42"})
        self.assertEqual(radar._experience_provenance_details({
            "source": "taleo", "title": job.title, "description": job.description,
        }), {"min_years": 9, "max_years": 9, "provenance": "description", "confidence": "medium"})

    def test_successfactors_preserves_public_identity_and_uses_day_precision(self):
        url = "https://jobs.lubrizol.com/search/"
        board = public_job_boards.detect(url)
        self.assertIsNone(public_job_boards.detect("https://unverified.example/search/"))
        listing = """
          <link href="//rmkcdn.successfactors.com/site.css" rel="stylesheet">
          <table>
            <tr class="data-row">
              <td><a class="jobTitle-link" href="/job/Corona-Process-Engineer/123/?tracking=x">Process Engineer</a></td>
              <td class="jobLocation">Corona, CA</td><td class="jobDate">Nov 23, 2026</td>
            </tr>
            <tr class="data-row">
              <td><a class="jobTitle-link" href="/job/Bengaluru-Engineer/456/">Engineer</a></td>
            </tr>
            <tr class="data-row">
              <td><a class="jobTitle-link" href="https://other.example/job/Outside/321/">Outside</a></td>
            </tr>
          </table>
        """
        detail = """
          <link rel="canonical" href="https://jobs.lubrizol.com/job/Bengaluru-Engineer/456/">
          <section itemtype="https://schema.org/JobPosting">
            <meta itemprop="datePosted" content="Mon Nov 23 08:00:00 UTC 2026">
            <div itemprop="jobLocation"><div itemprop="address">
              <span itemprop="addressLocality">Bengaluru</span><span itemprop="addressCountry">IN</span>
            </div></div>
            <article itemprop="description"><p>Requires three (3) years of Python.</p></article>
          </section>
          <form>Candidate information</form>
        """
        jobs = public_job_boards.list_jobs(board, lambda *a, **k: response(listing))
        first, second = jobs
        self.assertEqual(first.url, "https://jobs.lubrizol.com/job/Corona-Process-Engineer/123/")
        self.assertEqual((first.title, first.locations, first.precision), ("Process Engineer", ["Corona, CA"], "date"))
        self.assertEqual(second.precision, "unknown")
        with self.assertRaises(ValueError):
            public_job_boards.hydrate(board, first, lambda *a, **k: response(detail))
        public_job_boards.hydrate(board, second, lambda *a, **k: response(detail))
        self.assertEqual(second.description, "Requires three (3) years of Python.")
        self.assertEqual(second.locations, ["Bengaluru, IN"])
        self.assertEqual((second.published_at.isoformat(), second.precision), ("2026-11-23T00:00:00+00:00", "date"))

    def test_peoplestrong_collects_candidate_fields_and_keeps_zero_years(self):
        host = "https://mpgcareers.peoplestrong.com"
        public_url = host + "/job/detail/MFL_BDO_123"
        candidate = board_discovery.detect_ats_board(public_url)
        self.assertEqual(candidate["board_url"], host + "/job/joblist")
        self.assertEqual(candidate["collector_source"], "peoplestrong")
        row = {
            "jobDetailUrl": public_url, "jobTitle": "Engineer", "organizationUnit": "Employer",
            "locationHierarchy": "Kochi", "expRange": "0-4 years", "jobPostedDate": "2026-11-23",
            "skills": {"mustTohave": ["Python"], "goodtohave": ["Python", "SQL"]},
        }
        listing = {"messageCode": {"code": 200}, "response": [
            row, {**row, "jobDetailUrl": "https://outside.example/job/detail/other"},
        ]}
        detail = {"messageCode": {"code": 200}, "response": {
            "jobDescription": "<p>Build services.</p>", "internalJobDescription": "internal field",
        }}
        config = {"peoplestrong_boards": [{"careers_url": candidate["board_url"], "company": "Example"}]}
        with (
            patch.object(radar, "connect_sqlite"),
            patch.object(radar, "_tracked_source_post", return_value=response(listing)) as post,
            patch.object(radar, "_tracked_source_get", return_value=response(detail)) as get,
        ):
            job, = radar.COLLECTORS["peoplestrong"](config)
        self.assertEqual(post.call_args.kwargs["json_body"], {})
        self.assertEqual(get.call_args.kwargs["params"], {"part": "descriprion", "isReqId": "false"})
        self.assertEqual((job["url"], job["company"], job["location"]), (public_url, "Employer", "Kochi"))
        self.assertEqual(job["description"], "Build services.")
        self.assertEqual(job["source_details"]["key_skills"], ["Python", "SQL"])
        self.assertEqual(job["posted_precision"], "date")
        self.assertEqual(radar._experience_provenance_details(job), {
            "min_years": 0, "max_years": 4, "provenance": "employer_stated", "confidence": "high",
        })

    def test_eightfold_follows_newest_page_offsets_and_rejects_unverified_tenants(self):
        host = "https://app.eightfold.ai"
        self.assertIsNone(public_job_boards.detect(host + "/careers/search?domain=other.example"))
        board = public_job_boards.detect(host + "/careers/job/100")
        first_page = [
            {
                "id": number, "positionUrl": f"/careers/job/{number}", "name": "Platform Engineer",
                "locations": ["Bengaluru, India", "Noida, India"], "workLocationOption": "hybrid",
                "postedTs": 1795201949,
            }
            for number in range(100, 110)
        ]
        second_page = [{**first_page[0], "id": 110, "positionUrl": "/careers/job/110"}]
        with patch.object(requests, "get", side_effect=[
            response({"status": 200, "data": {"count": 11, "sortBy": "timestamp", "positions": page}})
            for page in (first_page, second_page)
        ] + [response({"status": 200, "data": {"id": 100, "jobDescription": "<p>Work with Python.</p>"}})]) as get:
            jobs = public_job_boards.list_jobs(board, get)
            job = jobs[0]
            public_job_boards.hydrate(board, job, get)
        self.assertEqual(len(jobs), 11)
        self.assertEqual([call.kwargs["params"]["start"] for call in get.call_args_list[:2]], [0, 10])
        self.assertEqual(get.call_args_list[0].kwargs["params"]["sort_by"], "timestamp")
        self.assertEqual(get.call_args_list[-1].kwargs["params"]["position_id"], "100")
        self.assertEqual((job.url, job.precision, job.description),
                         (host + "/careers/job/100", "minute", "Work with Python."))
        self.assertEqual(job.locations, ["Bengaluru, India", "Noida, India"])
        self.assertEqual(job.details["workplace_type"], "hybrid")

    def test_jibe_reads_the_filtered_public_board_and_keeps_qualifications(self):
        url = "https://www.pepsicojobs.com/main/jobs?country=India"
        board = public_job_boards.detect(url)
        self.assertEqual(board.key, "www.pepsicojobs.com:india")
        self.assertEqual(board_discovery.detect_ats_board(url)["board_url"], url)
        self.assertIsNone(public_job_boards.detect("https://outside.example/main/jobs?country=India"))
        self.assertIsNone(public_job_boards.detect(url + "&country=Canada"))
        self.assertIsNone(board_discovery.detect_ats_board(url + "&country=Canada"))
        item = {
            "req_id": "123", "slug": "P1-123", "title": "Data Engineer", "searchable": True,
            "posted_date": "2026-11-23T08:00:00+0000", "city": "Hyderabad", "country": "India",
            "description": "<p>Build data pipelines.</p>", "qualifications": "<p>3+ years of experience with Python.</p>",
            "apply_url": "https://example.icims.com/jobs/123/login",
        }
        rows = [item, {**item, "req_id": "456", "internal": True}, {**item, "req_id": "789", "slug": "../other"}]
        with patch.object(requests, "get", return_value=response({
            "jobs": [{"data": row} for row in rows], "totalCount": len(rows),
        })) as get:
            job, = public_job_boards.list_jobs(board, get)
        self.assertEqual(get.call_args.args[0], "https://www.pepsicojobs.com/api/jobs")
        self.assertEqual(get.call_args.kwargs["params"], {"limit": 100, "country": "India", "page": 1})
        self.assertEqual((job.id, job.url, job.locations, job.precision),
                         ("123", "https://www.pepsicojobs.com/main/jobs/P1-123", ["Hyderabad, India"], "minute"))
        self.assertIn("3+ years of experience with Python", job.description)

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
