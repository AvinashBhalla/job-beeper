from __future__ import annotations

import socket
import unittest
from unittest.mock import patch

from v2.google_alerts_safe_fetch import (
    MAX_REDIRECTS,
    SafeFetchError,
    _PinnedHTTPSConnection,
    fetch_public_job_page,
)


def dns_records(*addresses):
    return [
        (socket.AF_INET6 if ":" in address else socket.AF_INET,
         socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 443))
        for address in addresses
    ]


class FakeResponse:
    def __init__(self, status, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self._body = body
        self._offset = 0
        self.closed = False

    def read(self, amount):
        result = self._body[self._offset:self._offset + amount]
        self._offset += len(result)
        return result


class FakeConnection:
    def __init__(self, response, hostname, pinned_ip, timeout):
        self.response = response
        self.hostname = hostname
        self.pinned_ip = pinned_ip
        self.timeout = timeout
        self.request_args = None
        self.closed = False

    def request(self, method, target, *, headers):
        self.request_args = (method, target, headers)

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class FakeConnectionFactory:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.connections = []

    def __call__(self, hostname, pinned_ip, *, timeout):
        if not self.responses:
            raise AssertionError("Unexpected HTTP connection.")
        connection = FakeConnection(
            self.responses.pop(0), hostname, pinned_ip, timeout
        )
        self.connections.append(connection)
        return connection


class PinnedConnectionTests(unittest.TestCase):
    def test_connection_uses_validated_ip_and_original_hostname_for_tls(self):
        class FakeSocket:
            closed = False

            def close(self):
                self.closed = True

        class FakeTLSContext:
            def __init__(self):
                self.server_hostname = None
                self.wrapped = None

            def wrap_socket(self, sock, *, server_hostname):
                self.server_hostname = server_hostname
                self.wrapped = sock
                return sock

        fake_socket = FakeSocket()
        context = FakeTLSContext()
        connection = _PinnedHTTPSConnection(
            "jobs.example.com", "93.184.216.34", timeout=5
        )
        connection._context = context
        with patch(
            "v2.google_alerts_safe_fetch.socket.create_connection",
            return_value=fake_socket,
        ) as create:
            connection.connect()
        self.assertEqual(create.call_args.args[0], ("93.184.216.34", 443))
        self.assertEqual(context.server_hostname, "jobs.example.com")
        self.assertIs(connection.sock, fake_socket)
        connection.close()


class SafePublicFetchTests(unittest.TestCase):
    def _fetch(self, *args, **kwargs):
        kwargs.setdefault("robots_checker", lambda _: True)
        return fetch_public_job_page(*args, **kwargs)

    def _resolver(self, mapping):
        calls = []

        def resolve(host, port, *, type):
            calls.append((host, port, type))
            return dns_records(*mapping[host])

        return resolve, calls

    def test_fetch_pins_public_ip_and_preserves_host_header(self):
        response = FakeResponse(
            200,
            {"Content-Type": "text/html; charset=utf-8"},
            b"<html><title>Software Engineer</title></html>",
        )
        factory = FakeConnectionFactory(response)
        resolver, calls = self._resolver({"jobs.example.com": ["93.184.216.34"]})

        page = self._fetch(
            "https://jobs.example.com/software-engineer?id=123#section",
            resolver=resolver,
            connection_factory=factory,
        )

        self.assertEqual(page.http_status, 200)
        self.assertIn("Software Engineer", page.text)
        self.assertEqual(page.final_url, "https://jobs.example.com/software-engineer?id=123#section")
        self.assertEqual(calls, [("jobs.example.com", 443, socket.SOCK_STREAM)])
        connection = factory.connections[0]
        self.assertEqual(connection.pinned_ip, "93.184.216.34")
        method, target, headers = connection.request_args
        self.assertEqual(method, "GET")
        self.assertEqual(target, "/software-engineer?id=123")
        self.assertEqual(headers["Host"], "jobs.example.com")
        self.assertTrue(connection.closed)

    def test_rejects_mixed_public_and_private_dns_answers_before_connect(self):
        factory = FakeConnectionFactory(
            FakeResponse(200, {"Content-Type": "text/html"}, b"safe")
        )
        resolver, _ = self._resolver(
            {"jobs.example.com": ["93.184.216.34", "10.10.0.5"]}
        )
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/job",
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "dns_private_or_reserved_address")
        self.assertEqual(factory.connections, [])

    def test_rejects_private_literal_and_non_https_url(self):
        for url, expected in (
            ("https://127.0.0.1/job", "private_or_reserved_ip"),
            ("https://192.168.1.2/job", "private_or_reserved_ip"),
            ("http://jobs.example.com/job", "url_not_public_https"),
            ("https://user:pass@jobs.example.com/job", "url_not_public_https"),
            ("https://jobs.example.com:8443/job", "url_not_public_https"),
        ):
            with self.subTest(url=url), self.assertRaises(SafeFetchError) as caught:
                self._fetch(url)
            self.assertEqual(caught.exception.code, expected)

    def test_revalidates_dns_for_each_redirect_hop(self):
        redirect = FakeResponse(
            302, {"Location": "https://careers.example.net/jobs/42"}
        )
        final = FakeResponse(
            200, {"Content-Type": "application/xhtml+xml"}, b"<html>Posting</html>"
        )
        factory = FakeConnectionFactory(redirect, final)
        resolver, calls = self._resolver({
            "jobs.example.com": ["93.184.216.34"],
            "careers.example.net": ["93.184.216.35"],
        })

        page = self._fetch(
            "https://jobs.example.com/outbound",
            resolver=resolver,
            connection_factory=factory,
        )

        self.assertEqual(page.final_url, "https://careers.example.net/jobs/42")
        self.assertEqual([call[0] for call in calls], [
            "jobs.example.com", "careers.example.net"
        ])
        self.assertEqual(
            [connection.pinned_ip for connection in factory.connections],
            ["93.184.216.34", "93.184.216.35"],
        )
        self.assertEqual(
            factory.connections[1].request_args[2]["Host"],
            "careers.example.net",
        )
        self.assertTrue(all(connection.closed for connection in factory.connections))

    def test_redirect_to_private_ip_is_rejected_before_second_connection(self):
        redirect = FakeResponse(302, {"Location": "https://10.0.0.8/private"})
        factory = FakeConnectionFactory(redirect)
        resolver, calls = self._resolver({"jobs.example.com": ["93.184.216.34"]})
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/go",
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "private_or_reserved_ip")
        self.assertEqual(len(factory.connections), 1)

    def test_redirect_to_http_is_rejected(self):
        redirect = FakeResponse(302, {"Location": "http://jobs.example.net/posting"})
        factory = FakeConnectionFactory(redirect)
        resolver, _ = self._resolver({"jobs.example.com": ["93.184.216.34"]})
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/go",
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "url_not_public_https")
        self.assertEqual(len(factory.connections), 1)

    def test_redirect_loop_is_rejected(self):
        factory = FakeConnectionFactory(
            FakeResponse(302, {"Location": "/same"}),
            FakeResponse(302, {"Location": "/same"}),
        )
        resolver, _ = self._resolver({"jobs.example.com": ["93.184.216.34"]})
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/same",
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "redirect_loop")
        self.assertEqual(len(factory.connections), 1)

    def test_redirect_limit_is_enforced(self):
        responses = [
            FakeResponse(302, {"Location": f"/step-{index + 1}"})
            for index in range(MAX_REDIRECTS + 1)
        ]
        factory = FakeConnectionFactory(*responses)
        resolver, _ = self._resolver({"jobs.example.com": ["93.184.216.34"]})
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/step-0",
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "redirect_limit")
        self.assertEqual(len(factory.connections), MAX_REDIRECTS + 1)

    def test_response_size_limit_is_enforced(self):
        response = FakeResponse(
            200, {"Content-Type": "text/html"}, b"x" * 21
        )
        factory = FakeConnectionFactory(response)
        resolver, _ = self._resolver({"jobs.example.com": ["93.184.216.34"]})
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/job",
                max_bytes=20,
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "page_too_large")
        self.assertTrue(factory.connections[0].closed)

    def test_rejects_unexpected_content_type(self):
        response = FakeResponse(200, {"Content-Type": "application/pdf"}, b"%PDF")
        factory = FakeConnectionFactory(response)
        resolver, _ = self._resolver({"jobs.example.com": ["93.184.216.34"]})
        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/job",
                resolver=resolver,
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "unexpected_content_type")

    def test_dns_failure_is_sanitized(self):
        def fail_resolution(host, port, *, type):
            raise OSError("secret internal resolver detail")

        with self.assertRaises(SafeFetchError) as caught:
            self._fetch(
                "https://jobs.example.com/job",
                resolver=fail_resolution,
                connection_factory=FakeConnectionFactory(),
            )
        self.assertEqual(caught.exception.code, "dns_resolution_failed")
        self.assertNotIn("secret", str(caught.exception))


class RobotsPolicyTests(unittest.TestCase):
    def setUp(self):
        from v2 import google_alerts_safe_fetch
        google_alerts_safe_fetch._ROBOTS_CACHE.clear()

    def _resolver(self, host="jobs.example.com"):
        return lambda name, port, *, type: dns_records("93.184.216.34")

    def test_disallow_rule_blocks_page_request(self):
        factory = FakeConnectionFactory(FakeResponse(
            200,
            {"Content-Type": "text/plain"},
            b"User-agent: *\nDisallow: /private",
        ))
        with self.assertRaises(SafeFetchError) as caught:
            fetch_public_job_page(
                "https://jobs.example.com/private/posting",
                resolver=self._resolver(),
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "robots_disallowed")
        self.assertEqual(len(factory.connections), 1)
        self.assertEqual(factory.connections[0].request_args[1], "/robots.txt")

    def test_allow_rule_allows_page_and_caches_policy(self):
        robots = FakeResponse(
            200, {"Content-Type": "text/plain"},
            b"User-agent: *\nDisallow: /private",
        )
        page1 = FakeResponse(200, {"Content-Type": "text/html"}, b"First page")
        page2 = FakeResponse(200, {"Content-Type": "text/html"}, b"Second page")
        factory = FakeConnectionFactory(robots, page1, page2)
        resolver = self._resolver()

        first = fetch_public_job_page(
            "https://jobs.example.com/public/one",
            resolver=resolver,
            connection_factory=factory,
        )
        second = fetch_public_job_page(
            "https://jobs.example.com/public/two",
            resolver=resolver,
            connection_factory=factory,
        )
        self.assertEqual(first.text, "First page")
        self.assertEqual(second.text, "Second page")
        # robots.txt was fetched once; the policy was reused for the second URL.
        self.assertEqual(len(factory.connections), 3)
        self.assertEqual(factory.connections[0].request_args[1], "/robots.txt")

    def test_missing_robots_file_allows_page(self):
        factory = FakeConnectionFactory(
            FakeResponse(404, {"Content-Type": "text/plain"}),
            FakeResponse(200, {"Content-Type": "text/html"}, b"Page"),
        )
        page = fetch_public_job_page(
            "https://jobs.example.com/posting",
            resolver=self._resolver(),
            connection_factory=factory,
        )
        self.assertEqual(page.text, "Page")
        self.assertEqual(len(factory.connections), 2)

    def test_forbidden_robots_file_denies_all(self):
        factory = FakeConnectionFactory(
            FakeResponse(403, {"Content-Type": "text/plain"})
        )
        with self.assertRaises(SafeFetchError) as caught:
            fetch_public_job_page(
                "https://jobs.example.com/posting",
                resolver=self._resolver(),
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "robots_disallowed")
        self.assertEqual(len(factory.connections), 1)

    def test_robots_server_error_fails_closed(self):
        factory = FakeConnectionFactory(
            FakeResponse(503, {"Retry-After": "60"})
        )
        with self.assertRaises(SafeFetchError) as caught:
            fetch_public_job_page(
                "https://jobs.example.com/posting",
                resolver=self._resolver(),
                connection_factory=factory,
            )
        self.assertEqual(caught.exception.code, "robots_unavailable")
        self.assertEqual(len(factory.connections), 1)


if __name__ == "__main__":
    unittest.main()
