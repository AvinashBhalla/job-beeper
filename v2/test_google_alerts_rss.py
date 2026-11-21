from __future__ import annotations

import unittest

from v2.google_alerts_rss import parse_google_alerts_atom, unwrap_google_alert_url


SAMPLE_FEED = \'\'\'<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:idx="urn:atom-extension:indexing">
  <id>tag:google.com,2005:reader/user/REDACTED/state/com.google/alerts/REDACTED</id>
  <title>Google Alert - "Software Engineer" India React TypeScript</title>
  <link href="https://www.google.com/alerts/feeds/REDACTED/REDACTED" rel="self"/>
  <updated>2026-11-20T05:10:07Z</updated>
  <entry>
    <id>tag:google.com,2013:googlealerts/feed:ENTRY_ONE</id>
    <title type="html">Software Engineering - &lt;b&gt;React&lt;/b&gt; &amp;amp; Node - Associate (&lt;b&gt;India&lt;/b&gt;) - Shine</title>
    <link href="https://www.google.com/url?rct=j&amp;sa=t&amp;url=https://www.shine.com/jobs/software-engineering-react-node-associate-india/pwc-acceleration-centers-in-india/20106180&amp;ct=ga&amp;cd=REDACTED&amp;usg=REDACTED"/>
    <published>2026-11-20T05:10:07Z</published>
    <updated>2026-11-20T05:10:07Z</updated>
    <content type="html">... Early Applicant. &lt;b&gt;Software Engineer&lt;/b&gt; (&lt;b&gt;React&lt;/b&gt;, &lt;b&gt;TypeScript&lt;/b&gt; &amp;amp; Web Platform). 0 to 4 Yrs Not Disclosed All &lt;b&gt;India&lt;/b&gt;. Required:JavaScript·PHP·&lt;b&gt;React&lt;/b&gt;·&lt;b&gt;TypeScript&lt;/b&gt;</content>
    <author><name/></author>
  </entry>
  <entry>
    <id>tag:google.com,2013:googlealerts/feed:ENTRY_TWO</id>
    <title type="html">Sr &lt;b&gt;Software Engineer&lt;/b&gt; - &lt;b&gt;ReactJS&lt;/b&gt;, Redux, &lt;b&gt;React&lt;/b&gt; Router &amp;amp; &lt;b&gt;TypeScript&lt;/b&gt; with 0 - foundit</title>
    <link href="https://www.google.com/url?rct=j&amp;sa=t&amp;url=https://www.foundit.in/job/sr-software-engineer-reactjs-redux-react-router-typescript-blue-yonder-hyderabad-secunderabad-telangana-69871791&amp;ct=ga&amp;cd=REDACTED&amp;usg=REDACTED"/>
    <published>2026-11-20T04:31:52Z</published>
    <updated>2026-11-20T04:31:52Z</updated>
    <content type="html">... &lt;b&gt;India&lt;/b&gt;. Explore required skills, salary, responsibilities &amp;amp; similar ... Sr &lt;b&gt;Software Engineer&lt;/b&gt; - &lt;b&gt;ReactJS&lt;/b&gt;, Redux, &lt;b&gt;React&lt;/b&gt; Router &amp;amp; &lt;b&gt;TypeScript&lt;/b&gt;. Blue&amp;amp;nbsp;...</content>
    <author><name/></author>
  </entry>
</feed>
\'\'\'


class GoogleAlertsAtomTests(unittest.TestCase):
    def test_parses_both_sample_entries_and_unwraps_destinations(self):
        feed = parse_google_alerts_atom(SAMPLE_FEED)
        self.assertEqual(feed.title, 'Google Alert - "Software Engineer" India React TypeScript')
        self.assertEqual(feed.updated_at, "2026-11-20T05:10:07Z")
        self.assertEqual(len(feed.entries), 2)

        shine, foundit = feed.entries
        self.assertEqual(shine.title, "Software Engineering - React & Node - Associate (India) - Shine")
        self.assertIn("Software Engineer (React, TypeScript & Web Platform)", shine.snippet)
        self.assertEqual(
            shine.destination_url,
            "https://www.shine.com/jobs/software-engineering-react-node-associate-india/pwc-acceleration-centers-in-india/20106180",
        )
        self.assertEqual(shine.published_at, "2026-11-20T05:10:07Z")

        self.assertIn("Sr Software Engineer - ReactJS, Redux", foundit.title)
        self.assertIn("foundit.in/job/sr-software-engineer", foundit.destination_url)
        self.assertEqual(foundit.published_at, "2026-11-20T04:31:52Z")

    def test_deduplicates_repeated_atom_entry_id(self):
        duplicated = SAMPLE_FEED.replace(
            "  </entry>\\n  <entry>\\n    <id>tag:google.com,2013:googlealerts/feed:ENTRY_TWO</id>",
            "  </entry>\\n  <entry>\\n    <id>tag:google.com,2013:googlealerts/feed:ENTRY_ONE</id>",
        )
        self.assertEqual(len(parse_google_alerts_atom(duplicated).entries), 1)

    def test_feed_credentials_and_self_link_are_not_returned(self):
        parsed = parse_google_alerts_atom(SAMPLE_FEED).to_dict()
        serialized = repr(parsed)
        self.assertNotIn("REDACTED", serialized)
        self.assertNotIn("google.com/alerts/feeds", serialized)
        self.assertNotIn("usg=", serialized)

    def test_rejects_non_atom_xml(self):
        with self.assertRaisesRegex(ValueError, "Atom 1.0"):
            parse_google_alerts_atom("<root/>")

    def test_rejects_malformed_xml(self):
        with self.assertRaisesRegex(ValueError, "valid XML"):
            parse_google_alerts_atom("<feed><entry></feed>")

    def test_rejects_dtd_and_entity_declarations(self):
        payload = '<!DOCTYPE feed [<!ENTITY x "boom">]><feed xmlns="http://www.w3.org/2005/Atom"/>'
        with self.assertRaisesRegex(ValueError, "DTD and entity"):
            parse_google_alerts_atom(payload)

    def test_rejects_private_or_non_https_destinations(self):
        for url in (
            "http://example.com/job",
            "https://127.0.0.1/job",
            "https://192.168.1.2/job",
            "https://localhost/job",
            "https://service.internal/job",
            "https://user:pass@example.com/job",
            "https://example.com:8443/job",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                unwrap_google_alert_url(url)

    def test_rejects_google_redirect_without_destination(self):
        with self.assertRaisesRegex(ValueError, "does not contain one destination"):
            unwrap_google_alert_url("https://www.google.com/url?rct=j")

    def test_rejects_feed_over_size_limit(self):
        with self.assertRaisesRegex(ValueError, "size limit"):
            parse_google_alerts_atom(SAMPLE_FEED, max_bytes=20)


if __name__ == "__main__":
    unittest.main()
