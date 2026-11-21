"""Tests for generic owner-only Google Alerts email parsing."""
from __future__ import annotations

import json
import unittest
from email.message import EmailMessage
from urllib.parse import urlencode

from v2.google_alerts_email import (
    GoogleAlertEmailError,
    parse_google_alert_email,
)


SENDER = "Google Alerts <googlealerts-noreply@google.com>"


def make_email(*, html_body=None, plain_body=None, sender=SENDER, subject="Google Alert - example query"):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "owner@example.test"
    message["Subject"] = subject
    message["Date"] = "Fri, 20 Nov 2026 06:19:10 -0800"
    message["Message-ID"] = "<message-123@example.test>"
    if plain_body is not None:
        message.set_content(plain_body)
    if html_body is not None:
        if plain_body is None:
            message.set_content("Google Alert")
        message.add_alternative(html_body, subtype="html")
    return message.as_bytes()


def structured_html(items):
    document = {
        "api_version": "1.0",
        "publisher": {"name": "Google Alerts"},
        "cards": [{
            "widgets": [
                {
                    "type": "LINK",
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "url": item["url"],
                }
                for item in items
            ]
        }],
    }
    return (
        '<html><body><script data-scope="inboxmarkup" type="application/json">'
        + json.dumps(document)
        + "</script></body></html>"
    )


def google_redirect(destination):
    return "https://www.google.com/url?" + urlencode({"rct": "j", "sa": "t", "url": destination})


class GoogleAlertsEmailParserTests(unittest.TestCase):
    def test_extracts_every_result_from_structured_json_in_multipart_email(self):
        items = [
            {
                "title": "Senior Software Engineer at ExampleCo",
                "description": "Python backend and REST APIs.",
                "url": google_redirect("https://jobs.example.test/roles/one"),
            },
            {
                "title": "Python Data Engineer at DataCo",
                "description": "Build Python data services.",
                "url": google_redirect("https://careers.example.test/roles/two"),
            },
            {
                "title": "Software Engineer at WebCo",
                "description": "Node.js and AWS.",
                "url": google_redirect("https://jobs.example.test/roles/three"),
            },
        ]
        raw = make_email(
            plain_body="Three new results",
            html_body=structured_html(items),
        )
        parsed = parse_google_alert_email(raw)

        self.assertEqual(len(parsed.results), 3)
        self.assertEqual(
            [item.title for item in parsed.results],
            [item["title"] for item in items],
        )
        self.assertEqual(
            [item.extraction_method for item in parsed.results],
            ["structured_html_json"] * 3,
        )
        self.assertEqual(len(parsed.message_fingerprint), 64)
        self.assertEqual(parsed.sent_at, "2026-11-20T06:19:10-08:00")

    def test_canonical_duplicate_results_are_collapsed(self):
        destination = "https://jobs.example.test/roles/one"
        raw = make_email(
            html_body=structured_html([
                {"title": "Role One", "url": destination + "?utm_source=alert"},
                {"title": "Role One duplicate", "url": destination},
            ])
        )
        parsed = parse_google_alert_email(raw)
        self.assertEqual(len(parsed.results), 1)
        self.assertEqual(parsed.results[0].canonical_url, destination)

    def test_html_link_fallback_unwraps_google_redirect(self):
        destination = "https://jobs.example.test/roles/one?source=publisher"
        html = (
            "<html><body>"
            f'<a href="{google_redirect(destination)}">Role at ExampleCo</a>'
            "</body></html>"
        )
        parsed = parse_google_alert_email(make_email(html_body=html))
        self.assertEqual(len(parsed.results), 1)
        self.assertEqual(parsed.results[0].destination_url, destination)
        self.assertEqual(parsed.results[0].extraction_method, "html_link")

    def test_plain_text_fallback_ignores_alert_banner_and_footer_links(self):
        destination = "https://jobs.example.test/roles/one"
        plain = (
            "=== Web - 1 new result for [example query] ===\\n\\n"
            "Backend Engineer at ExampleCo\\n"
            "Python and REST API work.\\n"
            f"<{google_redirect(destination)}>\\n\\n"
            "- - - - - - - - - - - - - - - - - -\\n"
            "Unsubscribe from this Google Alert:\\n"
            "<https://www.google.co.in/alerts/remove?msgid=private>\\n"
        )
        parsed = parse_google_alert_email(make_email(plain_body=plain))
        self.assertEqual(len(parsed.results), 1)
        self.assertEqual(parsed.results[0].title, "Backend Engineer at ExampleCo")
        self.assertIn("Python and REST API", parsed.results[0].snippet)
        self.assertEqual(parsed.results[0].extraction_method, "plain_text")

    def test_rejects_non_google_sender(self):
        raw = make_email(
            sender="Attacker <attacker@example.test>",
            html_body=structured_html([{
                "title": "Role",
                "url": "https://jobs.example.test/role",
            }]),
        )
        with self.assertRaises(GoogleAlertEmailError) as caught:
            parse_google_alert_email(raw)
        self.assertEqual(caught.exception.code, "unrecognized_sender")

    def test_rejects_non_alert_subject(self):
        raw = make_email(
            subject="Weekly report",
            html_body=structured_html([{
                "title": "Role",
                "url": "https://jobs.example.test/role",
            }]),
        )
        with self.assertRaises(GoogleAlertEmailError) as caught:
            parse_google_alert_email(raw)
        self.assertEqual(caught.exception.code, "unrecognized_subject")

    def test_rejects_google_redirect_without_destination(self):
        raw = make_email(
            html_body=structured_html([{
                "title": "Role",
                "url": "https://www.google.com/url?rct=j",
            }])
        )
        with self.assertRaises(GoogleAlertEmailError) as caught:
            parse_google_alert_email(raw)
        self.assertEqual(caught.exception.code, "no_alert_results_found")

    def test_rejects_oversized_raw_message(self):
        with self.assertRaises(GoogleAlertEmailError) as caught:
            parse_google_alert_email(b"x" * 100, max_raw_bytes=10)
        self.assertEqual(caught.exception.code, "message_too_large")


if __name__ == "__main__":
    unittest.main()
