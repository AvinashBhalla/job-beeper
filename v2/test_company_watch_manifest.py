from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v2 import company_watch_manifest, radar


class CompanyWatchManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "jobs.sqlite3"
        self.db_patch = patch.object(radar, "DB_PATH", self.db)
        self.db_patch.start()
        with patch.object(
            radar, "DEFAULT_CONFIG_PATH",
            Path(radar.__file__).with_name("config.json"),
        ):
            radar.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_pinned_manifest_validates_all_rows_and_classifies_review_only(self):
        manifest = company_watch_manifest.parse_manifest(
            radar.COMPANY_WATCH_MANIFEST_PATH,
            radar._normalise_global_ats_candidate_url,
        )
        self.assertEqual(manifest["rows_total"], 100)
        self.assertEqual(manifest["manifest_sha256"], "146582ae4f3d68a9f13eff23b90bcf2ef5f28c9ab2020948d1ffaf82a5e7e4bd")
        self.assertEqual(manifest["counts"], {
            "candidate_staged": 19,
            "manual_review": 81,
        })
        self.assertEqual(sum(row["scan_enabled"] for row in manifest["rows"]), 92)
        self.assertEqual(sum(not row["scan_enabled"] for row in manifest["rows"]), 8)
        self.assertTrue(all(row["candidate"] for row in manifest["rows"] if row["classification"] == "candidate_staged"))
        self.assertTrue(all(not row["candidate"] for row in manifest["rows"] if row["classification"] == "manual_review"))
        self.assertTrue(all(
            row["review_reason"] != "manifest_disabled"
            for row in manifest["rows"] if row["classification"] == "candidate_staged"
        ))

    def test_provider_and_identity_mismatches_remain_manual(self):
        manifest = company_watch_manifest.parse_manifest(
            radar.COMPANY_WATCH_MANIFEST_PATH,
            radar._normalise_global_ats_candidate_url,
        )
        by_number = {row["row_number"]: row for row in manifest["rows"]}
        self.assertEqual(by_number[24]["classification"], "manual_review")
        self.assertIn("manifest_disabled", by_number[24]["review_reason"])
        self.assertIn("manifest_manual_review", by_number[24]["review_reason"])
        self.assertIn("identity", by_number[24]["review_reason"])
        self.assertEqual(by_number[32]["classification"], "manual_review")
        self.assertIn("identity", by_number[32]["review_reason"])
        self.assertEqual(by_number[36]["classification"], "candidate_staged")
        self.assertEqual(by_number[43]["classification"], "manual_review")
        self.assertEqual(by_number[51]["classification"], "manual_review")

    def test_corrected_company_watch_rows_use_current_official_board_evidence(self):
        manifest = company_watch_manifest.parse_manifest(
            radar.COMPANY_WATCH_MANIFEST_PATH,
            radar._normalise_global_ats_candidate_url,
        )
        by_number = {row["row_number"]: row for row in manifest["rows"]}

        mistral = by_number[2]
        self.assertEqual(mistral["company_name"], "Mistral AI")
        self.assertEqual(mistral["candidate"]["provider"], "ashby")
        self.assertEqual(mistral["candidate"]["board_key"], "mistral.ai")
        self.assertEqual(mistral["verification_source"], "https://mistral.ai/careers/")

        soundhound = by_number[13]
        self.assertEqual(soundhound["classification"], "manual_review")
        self.assertIsNone(soundhound["candidate"])
        self.assertEqual(soundhound["careers_url"], "https://www.soundhound.com/careers")

        self.assertEqual(by_number[36]["candidate"]["provider"], "workday")
        self.assertIsNone(by_number[43]["candidate"])
        self.assertEqual(by_number[64]["classification"], "manual_review")
        self.assertEqual(by_number[70]["classification"], "manual_review")

    def test_manifest_rejects_wrong_row_count_and_unsafe_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text("no,name,sector,country,careers_url,board_type,scan_mode,scan_enabled,verification_status,verification_source,verification_note\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Expected 100"):
                company_watch_manifest.parse_manifest(
                    path, radar._normalise_global_ats_candidate_url
                )

            path.write_text(
                "no,name,sector,country,careers_url,board_type,scan_mode,scan_enabled,verification_status,verification_source,verification_note\n"
                "1,Example,IT,US,http://example.com/jobs,greenhouse,greenhouse,True,verified_ats_board,https://example.com,official\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "HTTPS URL"):
                company_watch_manifest.parse_manifest(
                    path, radar._normalise_global_ats_candidate_url, expected_rows=1
                )

            for unsafe in ("https://127.0.0.1/jobs", "https://localhost/jobs", "https://example.com/a b"):
                path.write_text(
                    "no,name,sector,country,careers_url,board_type,scan_mode,scan_enabled,verification_status,verification_source,verification_note\\n"
                    f"1,Example,IT,US,{unsafe},greenhouse,greenhouse,True,verified_ats_board,https://example.com,official\\n",
                    encoding="utf-8",
                )
                with self.subTest(url=unsafe), self.assertRaises(ValueError):
                    company_watch_manifest.parse_manifest(
                        path, radar._normalise_global_ats_candidate_url, expected_rows=1
                    )

    def test_duplicate_board_identity_across_companies_is_held_for_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "no,name,sector,country,careers_url,board_type,scan_mode,scan_enabled,verification_status,verification_source,verification_note\n"
                "1,Employer One,IT,US,https://jobs.lever.co/one,lever,lever,True,provided_url_needs_live_validation,https://employer-one.example,\n"
                "2,Employer Two,IT,US,https://jobs.lever.co/two,lever,lever,True,provided_url_needs_live_validation,https://employer-two.example,\n",
                encoding="utf-8",
            )
            def same_board(_url):
                return {
                    "provider": "lever", "candidate_host": "jobs.lever.co",
                    "board_key": "shared", "board_url": "https://jobs.lever.co/shared",
                }
            manifest = company_watch_manifest.parse_manifest(
                path, same_board, expected_rows=2
            )
        self.assertEqual(manifest["counts"], {"manual_review": 2})
        self.assertTrue(all(row["candidate"] is None for row in manifest["rows"]))
        self.assertTrue(all(
            "duplicate_ats_board_identity_across_companies" in row["review_reason"]
            for row in manifest["rows"]
        ))

    def test_supported_ats_url_normalization_is_provider_specific_and_safe(self):
        examples = {
            "https://job-boards.greenhouse.io/anthropic/jobs/123": ("greenhouse", "anthropic", "https://job-boards.greenhouse.io/anthropic"),
            "https://jobs.lever.co/mistral/123": ("lever", "mistral", "https://jobs.lever.co/mistral"),
            "https://careers.smartrecruiters.com/Canva/job/123": ("smartrecruiters", "Canva", "https://careers.smartrecruiters.com/Canva"),
            "https://apply.workable.com/example/jobs/123": ("workable", "example", "https://apply.workable.com/example"),
            "https://jobs.ashbyhq.com/example/123": ("ashby", "example", "https://jobs.ashbyhq.com/example"),
        }
        for url, expected in examples.items():
            with self.subTest(url=url):
                candidate = radar._normalise_global_ats_candidate_url(url)
                self.assertEqual(
                    (candidate["provider"], candidate["board_key"], candidate["board_url"]),
                    expected,
                )
        for url in (
            "http://boards.greenhouse.io/example",
            "https://user@boards.greenhouse.io/example",
            "https://boards.greenhouse.io/example?preview=1",
            "https://boards.greenhouse.io/",
            "https://example.com/careers",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    radar._normalise_global_ats_candidate_url(url)

    def test_import_is_atomic_idempotent_and_never_links_or_activates(self):
        first = radar.import_company_watch_manifest({})
        self.assertEqual(first["candidate_inserted"], 19)
        self.assertEqual(first["manual_review_rows"], 81)
        self.assertEqual(first["company_records_created"], 0)
        self.assertEqual(first["boards_linked"], 0)
        self.assertEqual(first["verified"], 0)
        self.assertEqual(first["activated"], 0)
        self.assertEqual(first["scheduled"], 0)
        self.assertEqual(first["network_requests"], 0)
        self.assertEqual(first["notifications_sent"], 0)

        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM company_watch_manifest_rows").fetchone()[0], 100)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ats_global_discovery_candidates").fetchone()[0], 19)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employer_companies").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ats_board_registry").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ats_board_poll_schedule").fetchone()[0], 0)
            conn.execute(
                "UPDATE ats_global_discovery_candidates SET review_status='rejected' WHERE id=(SELECT MIN(id) FROM ats_global_discovery_candidates)"
            )
            conn.commit()

        second = radar.import_company_watch_manifest({})
        self.assertEqual(second["candidate_inserted"], 0)
        self.assertEqual(second["candidate_updated"], 18)
        self.assertEqual(second["candidate_preserved_terminal"], 1)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM company_watch_manifest_rows").fetchone()[0], 100)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ats_global_discovery_candidates").fetchone()[0], 19)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM ats_global_discovery_candidates WHERE review_status='rejected'").fetchone()[0],
                1,
            )
        status = radar.company_watch_manifest_status()
        self.assertEqual(status["classification_counts"], {
            "candidate_staged": 19, "manual_review": 79,
        })
        self.assertEqual(len(status["manual_review_rows"]), 81)
        candidates = radar.list_global_ats_candidates(limit=50)["candidates"]
        self.assertEqual(len(candidates), 19)
        self.assertTrue(all(row["manifest_company_name"] for row in candidates))
        self.assertTrue(all(row["manifest_careers_url"] for row in candidates))
        self.assertTrue(all(row["manifest_sha256"] == radar.COMPANY_WATCH_MANIFEST_SHA256 for row in candidates))
        self.assertTrue(all(row["manifest_scan_enabled"] == 1 for row in candidates))
        self.assertTrue(all(row["review_status"] in {"discovered", "rejected"} for row in candidates))

    def test_import_preserves_existing_candidate_discovery_provenance(self):
        manifest = company_watch_manifest.parse_manifest(
            radar.COMPANY_WATCH_MANIFEST_PATH,
            radar._normalise_global_ats_candidate_url,
        )
        row = next(row for row in manifest["rows"] if row["candidate"])
        candidate = row["candidate"]
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """INSERT INTO ats_global_discovery_candidates(
                       provider,board_key,board_url,candidate_host,discovery_method,
                       source_reference,first_discovered_at,last_seen_at,confidence,
                       review_status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,'discovered',?,?)""",
                (
                    candidate["provider"], candidate["board_key"], candidate["board_url"],
                    candidate["candidate_host"], "commoncrawl_cdx",
                    "https://index.commoncrawl.org/CC-MAIN-2026-43-index", "2026-11-01T00:00:00Z",
                    "2026-11-01T00:00:00Z", "low", "2026-11-01T00:00:00Z",
                    "2026-11-01T00:00:00Z",
                ),
            )
            conn.commit()

        result = radar.import_company_watch_manifest({})
        self.assertEqual(result["candidate_inserted"], 18)
        self.assertEqual(result["candidate_updated"], 1)
        with sqlite3.connect(self.db) as conn:
            stored = conn.execute(
                """SELECT discovery_method,source_reference,review_status
                   FROM ats_global_discovery_candidates
                   WHERE provider=? AND candidate_host=? AND board_key=?""",
                (candidate["provider"], candidate["candidate_host"], candidate["board_key"]),
            ).fetchone()
            self.assertEqual(stored, (
                "commoncrawl_cdx",
                "https://index.commoncrawl.org/CC-MAIN-2026-43-index",
                "discovered",
            ))
            linked = conn.execute(
                """SELECT COUNT(*) FROM company_watch_manifest_rows
                   WHERE candidate_id IS NOT NULL""",
            ).fetchone()[0]
            self.assertEqual(linked, 19)

    def test_admin_source_health_ui_exposes_import_and_manual_review_evidence(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        js = (root / "dashboard" / "app.js").read_text(encoding="utf-8")
        for element_id in (
            "companyWatchManifestPanel",
            "importCompanyWatchManifestBtn",
            "companyWatchManifestStatus",
            "companyWatchManualReviewBody",
        ):
            with self.subTest(element_id=element_id):
                self.assertEqual(html.count(f'id="{element_id}"'), 1)
        self.assertIn("loadCompanyWatchManifest()", js)
        self.assertIn("importCompanyWatchManifest(event.currentTarget)", js)
        self.assertIn("'/discovery/company-watch/manifest'", js)
        self.assertIn("'/discovery/company-watch/import'", js)
        self.assertIn("window.confirm(message)", js)
        self.assertIn("candidate.manifest_company_name", js)
        self.assertIn("candidate.manifest_review_reason", js)

    def test_dry_run_does_not_write_manifest_or_candidates(self):
        result = radar.import_company_watch_manifest({"dry_run": True})
        self.assertTrue(result["dry_run"])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM company_watch_manifest_rows").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ats_global_discovery_candidates").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM company_watch_manifest_imports").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
