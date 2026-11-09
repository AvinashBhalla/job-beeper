import unittest

from v2.ats_directory import parse_directory_csv, synthetic_domain


class ATSDirectoryTests(unittest.TestCase):
    def test_parses_supported_public_boards_and_preserves_source_date(self):
        content = (
            "ats_vendor,company_name,board_slug,last_crawled\n"
            'greenhouse,"Example Company",example,2026-08-01\n'
            'lever,"Example Two",example-two,2026-07-28\n'
            'ashby,"A Company",a-company,2026-07-12\n'
        )
        rows = parse_directory_csv(content)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["board_url"], "https://job-boards.greenhouse.io/example")
        self.assertEqual(rows[0]["last_crawled"], "2026-08-01")
        self.assertEqual(rows[1]["board_url"], "https://jobs.lever.co/example-two")
        self.assertEqual(rows[2]["board_url"], "https://jobs.ashbyhq.com/a-company")

    def test_filters_invalid_duplicate_and_unavailable_providers(self):
        content = (
            "ats_vendor,company_name,board_slug,last_crawled\n"
            "workday,Workday,acme,2026-08-01\n"
            "greenhouse,Example,example,2026-08-01\n"
            "greenhouse,Duplicate,example,2026-08-01\n"
            "lever,Unsafe,../unsafe,2026-08-01\n"
            "ashby,NoDate,slug,not-a-date\n"
            "ashby,,slug,2026-08-01\n"
        )
        rows = parse_directory_csv(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["board_key"], "example")

    def test_rejects_unexpected_schema_and_oversized_input(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            parse_directory_csv("provider,name,url\n")
        with self.assertRaisesRegex(ValueError, "2 MB"):
            parse_directory_csv("x" * (2_000_001))

    def test_synthetic_domain_key_is_stable_and_namespaced(self):
        self.assertEqual(
            synthetic_domain("greenhouse", "Example"),
            "ats-directory:greenhouse:example",
        )


if __name__ == "__main__":
    unittest.main()
