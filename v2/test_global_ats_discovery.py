from __future__ import annotations

import asyncio
import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from v2 import global_ats_discovery as discovery
from v2 import board_discovery, radar


UTC = dt.timezone.utc


class FakeResponse:
    def __init__(self, status_code: int, body: bytes | str = b"", headers: dict | None = None):
        self.status_code = status_code
        self._body = body.encode("utf-8") if isinstance(body, str) else body
        self.headers = headers or {"Content-Type": "application/json"}
        self.closed = False

    def iter_content(self, chunk_size=65536):
        for index in range(0, len(self._body), chunk_size):
            yield self._body[index:index + chunk_size]

    def close(self):
        self.closed = True


class FakeRequester:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected network request.")
        return self.responses.pop(0)


def cdx_record(url: str, timestamp: str = "20261109120000", provider: str | None = None):
    return {
        "url": url,
        "timestamp": timestamp,
        "status": "200",
        "mime": "text/html",
        "filename": "crawl.warc.gz",
        "offset": "123",
        "length": "456",
    }


class GlobalDiscoveryWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_runs_an_existing_discovery_cycle_on_startup(self):
        stop = asyncio.Event()
        def run_cycle():
            stop.set()

        with (
            patch.object(radar, "stop_event", stop),
            patch.object(radar, "run_commoncrawl_candidate_discovery", side_effect=run_cycle) as run,
        ):
            await asyncio.wait_for(radar.global_ats_discovery_worker(), timeout=2)
        run.assert_called_once_with()


class GlobalDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "jobs.sqlite3"
        discovery.init_schema(str(self.db))
        self.now = dt.datetime.now(UTC).replace(microsecond=0)

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM global_ats_discovery_state WHERE id=1").fetchone()
            return dict(row)

    def run_rows(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute(
                "SELECT method,provider,crawl_id,http_status,outcome,response_records,candidate_count,"
                "inserted_count,skipped_count,truncated,error_type FROM global_ats_discovery_runs ORDER BY id"
            ).fetchall()

    def test_catalogue_refresh_is_separate_then_provider_queries_rotate(self):
        catalogue = [{
            "id": "CC-MAIN-2026-43",
            "from": "2026-10-05T00:00:00",
            "to": "2026-10-18T23:59:59",
            "cdx-api": "https://index.commoncrawl.org/CC-MAIN-2026-43-index",
        }]
        workday = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        keka = "https://bridgestone1.keka.com/careers/"
        darwinbox = "https://arvind.darwinbox.in/ms/candidatev2/12345/careers"
        records = [
            cdx_record(workday, "20261109120000"),
            cdx_record(workday, "20261110100000"),
            cdx_record(keka),
            cdx_record(darwinbox),
            cdx_record("https://example.com/jobs"),
        ]
        body = "\n".join(json.dumps(item) for item in records)
        requester = FakeRequester([
            FakeResponse(200, json.dumps(catalogue)),
            FakeResponse(200, body),
            FakeResponse(200, json.dumps(cdx_record(keka))),
        ])
        imported = []

        def importer(payload):
            imported.extend(payload["candidates"])
            return {"inserted": len(payload["candidates"]), "updated": 0, "skipped": 0}

        first = discovery.run_commoncrawl_once(str(self.db), importer=importer, requester=requester, at=self.now)
        self.assertEqual(first["outcome"], "catalogue_refreshed")
        self.assertEqual(first["crawl_id"], "CC-MAIN-2026-43")
        self.assertEqual(len(requester.calls), 1)

        too_soon = discovery.run_commoncrawl_once(
            str(self.db), importer=importer, requester=requester,
            at=self.now + dt.timedelta(seconds=59),
        )
        self.assertEqual(too_soon["outcome"], "throttled")
        self.assertEqual(len(requester.calls), 1)

        second = discovery.run_commoncrawl_once(
            str(self.db), importer=importer, requester=requester,
            at=self.now + dt.timedelta(seconds=60),
        )
        self.assertEqual(second["provider"], "workday")
        self.assertEqual(second["candidate_count"], 1)
        self.assertEqual(second["imported"]["inserted"], 1)
        self.assertTrue(second["truncated"] is False)
        self.assertEqual(imported[0]["source_captured_at"], "20261110100000")
        self.assertEqual(imported[0]["discovery_method"], "commoncrawl_cdx")
        self.assertIn("CC-MAIN-2026-43", imported[0]["source_reference"])

        third = discovery.run_commoncrawl_once(
            str(self.db), importer=importer, requester=requester,
            at=self.now + dt.timedelta(seconds=120),
        )
        self.assertEqual(third["provider"], "keka")
        self.assertEqual(third["candidate_count"], 1)
        self.assertEqual(len(requester.calls), 3)
        self.assertEqual(self.state()["cdx_next_provider"], "darwinbox")
        self.assertEqual([row[0] for row in self.run_rows()], [
            "commoncrawl_catalogue", "commoncrawl_cdx", "commoncrawl_cdx",
        ])

    def test_http_503_sets_a_global_24_hour_cooldown(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """UPDATE global_ats_discovery_state
                   SET cdx_crawl_id=?,cdx_catalogue_fetched_at=?,cdx_next_provider='workday'
                   WHERE id=1""",
                ("CC-MAIN-2026-43", self.now.isoformat()),
            )
        requester = FakeRequester([FakeResponse(503, "rate limited")])
        result = discovery.run_commoncrawl_once(
            str(self.db), requester=requester, at=self.now,
        )
        self.assertEqual(result["outcome"], "global_cooldown")
        self.assertEqual(result["http_status"], 503)
        cooldown = dt.datetime.fromisoformat(self.state()["cdx_cooldown_until"])
        self.assertGreaterEqual(cooldown, self.now + dt.timedelta(hours=23, minutes=59))
        blocked = discovery.run_commoncrawl_once(
            str(self.db), requester=requester, at=self.now + dt.timedelta(hours=12),
        )
        self.assertEqual(blocked["outcome"], "cooldown")
        self.assertEqual(len(requester.calls), 1)

    def test_provider_http_error_does_not_block_the_rotation(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """UPDATE global_ats_discovery_state
                   SET cdx_crawl_id=?,cdx_catalogue_fetched_at=? WHERE id=1""",
                ("CC-MAIN-2026-43", self.now.isoformat()),
            )
        requester = FakeRequester([FakeResponse(504), FakeResponse(200)])
        first = discovery.run_commoncrawl_once(str(self.db), requester=requester, at=self.now)
        second = discovery.run_commoncrawl_once(
            str(self.db), requester=requester, at=self.now + dt.timedelta(hours=1),
        )
        self.assertEqual((first["outcome"], first["provider"]), ("cdx_http_error", "workday"))
        self.assertEqual((second["outcome"], second["provider"]), ("no_candidates", "keka"))

    def test_429_also_uses_the_conservative_global_cooldown(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """UPDATE global_ats_discovery_state
                   SET cdx_crawl_id=?,cdx_catalogue_fetched_at=? WHERE id=1""",
                ("CC-MAIN-2026-43", self.now.isoformat()),
            )
        requester = FakeRequester([FakeResponse(429, "too many requests")])
        result = discovery.run_commoncrawl_once(
            str(self.db), requester=requester, at=self.now,
        )
        self.assertEqual(result["outcome"], "global_cooldown")
        self.assertEqual(result["http_status"], 429)

    def test_record_cap_is_marked_truncated_and_candidates_are_deduplicated(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """UPDATE global_ats_discovery_state
                   SET cdx_crawl_id=?,cdx_catalogue_fetched_at=? WHERE id=1""",
                ("CC-MAIN-2026-43", self.now.isoformat()),
            )
        url = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        body = "\n".join(json.dumps(cdx_record(url, f"20261110{index:06d}")) for index in range(200))
        requester = FakeRequester([FakeResponse(200, body)])
        result = discovery.run_commoncrawl_once(
            str(self.db), requester=requester, at=self.now,
        )
        self.assertEqual(result["provider"], "workday")
        self.assertEqual(result["candidate_count"], 1)
        self.assertTrue(result["truncated"])

    def test_invalid_catalogue_fails_closed_and_releases_lease(self):
        requester = FakeRequester([FakeResponse(200, json.dumps([{"id": "not-a-crawl"}]))])
        result = discovery.run_commoncrawl_once(
            str(self.db), requester=requester, at=self.now,
        )
        self.assertEqual(result["outcome"], "request_error")
        self.assertEqual(result["error_type"], "ValueError")
        self.assertIsNone(self.state()["cdx_lease_token"])

    def test_discovery_status_does_not_expose_lease_token(self):
        status = discovery.discovery_status(str(self.db))
        self.assertNotIn("cdx_lease_token", status["commoncrawl"])
        self.assertEqual(status["host_budgets"], [])
        self.assertEqual(status["recent_runs"], [])

    def test_sitemap_scan_stages_direct_ats_urls_and_career_links_only(self):
        robots = """User-agent: *
Allow: /
Sitemap: https://example.com/sitemap.xml
"""
        sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
 <url><loc>https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite</loc></url>
 <url><loc>https://example.com/careers</loc></url>
</urlset>"""
        careers_page = '<html><a href="https://bridgestone1.keka.com/careers/">Careers portal</a></html>'
        requester = FakeRequester([
            FakeResponse(200, robots, {"Content-Type": "text/plain"}),
            FakeResponse(200, sitemap, {"Content-Type": "application/xml"}),
            FakeResponse(200, careers_page, {"Content-Type": "text/html"}),
        ])
        imported = []

        def importer(payload):
            imported.extend(payload["candidates"])
            return {"inserted": len(payload["candidates"]), "updated": 0, "skipped": 0}

        with patch.object(board_discovery, "_public_https_url", side_effect=lambda value: value):
            result = discovery.discover_public_sitemaps(
                str(self.db), "https://example.com/",
                importer=importer, requester=requester, at=self.now,
            )
        self.assertEqual(result["outcome"], "candidates_imported")
        self.assertEqual(result["sitemaps_checked"], 1)
        self.assertEqual(result["requests_attempted"], 3)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual({item["discovery_method"] for item in imported}, {"sitemap", "career_link"})
        self.assertEqual({item["source_captured_at"] for item in imported}, {None})
        self.assertEqual(len(requester.calls), 3)
        budget = sqlite3.connect(self.db).execute(
            "SELECT last_outcome,request_count,candidate_count FROM global_ats_discovery_host_budget WHERE host_key='example.com'"
        ).fetchone()
        self.assertEqual(budget, ("candidates_imported", 3, 2))

        throttled = discovery.discover_public_sitemaps(
            str(self.db), "https://example.com/",
            importer=importer, requester=requester, at=self.now + dt.timedelta(minutes=5),
        )
        self.assertEqual(throttled["outcome"], "host_throttled")
        self.assertEqual(len(requester.calls), 3)

    def test_sitemap_404_is_treated_as_optional_not_a_scan_failure(self):
        robots = "User-agent: *\nAllow: /\n"
        requester = FakeRequester([
            FakeResponse(200, robots, {"Content-Type": "text/plain"}),
            FakeResponse(404, b"", {"Content-Type": "text/plain"}),
        ])
        with patch.object(board_discovery, "_public_https_url", side_effect=lambda value: value):
            result = discovery.discover_public_sitemaps(
                str(self.db), "https://example.com/",
                requester=requester, at=self.now,
            )
        self.assertEqual(result["outcome"], "no_candidates")
        self.assertEqual(result["sitemaps_checked"], 1)
        self.assertEqual(result["requests_attempted"], 2)
        self.assertEqual(len(requester.calls), 2)

    def test_commoncrawl_batch_never_exceeds_candidate_importer_limit(self):
        self.assertEqual(discovery.COMMONCRAWL_MAX_RECORDS, 200)
        url = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        body = "\n".join(
            json.dumps(cdx_record(
                f"https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job-{index}",
                f"20261110{index:06d}",
            ))
            for index in range(250)
        )
        candidates, records, truncated = discovery._candidate_records(
            body.encode("utf-8"), "workday", "CC-MAIN-2026-43",
            response_truncated=False,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(records, 200)
        self.assertTrue(truncated)

    def test_sitemap_disallow_is_respected(self):
        robots = """User-agent: *
Disallow: /sitemap.xml
Sitemap: https://example.com/sitemap.xml
"""
        requester = FakeRequester([FakeResponse(200, robots, {"Content-Type": "text/plain"})])
        imported = []
        with patch.object(board_discovery, "_public_https_url", side_effect=lambda value: value):
            result = discovery.discover_public_sitemaps(
                str(self.db), "https://example.com/",
                importer=lambda payload: imported.extend(payload["candidates"]) or {},
                requester=requester, at=self.now,
            )
        self.assertEqual(result["outcome"], "no_candidates")
        self.assertEqual(len(requester.calls), 1)
        self.assertEqual(imported, [])

    def test_sitemap_503_sets_host_cooldown(self):
        requester = FakeRequester([FakeResponse(503, "temporarily unavailable")])
        with patch.object(board_discovery, "_public_https_url", side_effect=lambda value: value):
            result = discovery.discover_public_sitemaps(
                str(self.db), "https://example.com/", requester=requester, at=self.now,
            )
        self.assertEqual(result["outcome"], "host_cooldown")
        self.assertEqual(result["error_type"], "http_503")
        retry = discovery.discover_public_sitemaps(
            str(self.db), "https://example.com/", requester=requester,
            at=self.now + dt.timedelta(hours=2),
        )
        self.assertEqual(retry["outcome"], "host_cooldown")
        self.assertEqual(len(requester.calls), 1)

    def test_sitemap_xml_rejects_dtd_and_parses_index(self):
        with self.assertRaisesRegex(ValueError, "DTD/entity"):
            discovery._parse_sitemap_xml(b"<!DOCTYPE foo [<!ENTITY x 'oops'>]><urlset/>")
        nested, pages = discovery._parse_sitemap_xml(
            b'<sitemapindex><sitemap><loc>https://example.com/sitemap-jobs.xml</loc></sitemap></sitemapindex>'
        )
        self.assertEqual(nested, ["https://example.com/sitemap-jobs.xml"])
        self.assertEqual(pages, [])


if __name__ == "__main__":
    unittest.main()
