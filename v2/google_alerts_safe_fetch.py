"""SSRF-resistant fetcher for public job pages discovered by Google Alerts.

The URL is resolved and all returned IP addresses are validated before the
connection is created. The connection is then pinned to one validated address
while TLS still verifies the original hostname. Redirects are handled manually
and every new host is resolved and validated again.
"""
from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 5
MAX_BODY_BYTES = 2_000_000
DEFAULT_TIMEOUT_SECONDS = 12
ALLOWED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "text/plain",
}


class SafeFetchError(Exception):
    """Sanitized fetch failure that never includes the source URL."""

    def __init__(self, code: str, *, http_status: int | None = None) -> None:
        self.code = code
        self.http_status = http_status
        super().__init__(code)


@dataclass(frozen=True)
class FetchedPublicPage:
    final_url: str
    http_status: int
    content_type: str
    body: bytes
    text: str


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that connects to a previously validated numeric IP."""

    def __init__(
        self,
        hostname: str,
        pinned_ip: str,
        *,
        timeout: int,
    ) -> None:
        super().__init__(
            hostname,
            port=443,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        if self._tunnel_host:
            raise OSError("Proxy tunnels are not supported for public job fetches.")
        sock = socket.create_connection(
            (self._pinned_ip, self.port),
            self.timeout,
            self.source_address,
        )
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _parse_public_https_url(value: str) -> tuple[str, str, str]:
    if not isinstance(value, str) or not value or len(value) > MAX_URL_LENGTH:
        raise SafeFetchError("invalid_url")
    if any(ord(ch) < 33 for ch in value) or "\\" in value:
        raise SafeFetchError("invalid_url")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise SafeFetchError("invalid_url") from None

    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise SafeFetchError("url_not_public_https")

    host = hostname.rstrip(".").lower()
    if (
        host == "localhost"
        or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid"))
    ):
        raise SafeFetchError("private_or_reserved_host")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            host_ascii = host.encode("idna").decode("ascii")
        except UnicodeError:
            raise SafeFetchError("invalid_hostname") from None
        if not re.fullmatch(r"[a-z0-9.-]+", host_ascii):
            raise SafeFetchError("invalid_hostname")
    else:
        if not ip.is_global:
            raise SafeFetchError("private_or_reserved_ip")
        host_ascii = host

    path = parsed.path or "/"
    target = path + (f"?{parsed.query}" if parsed.query else "")
    # Fragments never reach the HTTP server.
    return host_ascii, target, parsed.netloc


def _resolve_public_addresses(host: str, resolver=None) -> tuple[str, ...]:
    resolve = resolver or socket.getaddrinfo
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            records = resolve(host, 443, type=socket.SOCK_STREAM)
        except OSError:
            raise SafeFetchError("dns_resolution_failed") from None
        addresses = {
            str(ipaddress.ip_address(record[4][0].split("%", 1)[0]))
            for record in records
            if record and len(record) > 4 and record[4]
        }
    else:
        addresses = {str(ip)}

    if not addresses:
        raise SafeFetchError("dns_no_addresses")
    parsed_addresses = []
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            raise SafeFetchError("dns_invalid_address") from None
        if not parsed.is_global:
            # Reject the entire answer if even one address is private/reserved.
            raise SafeFetchError("dns_private_or_reserved_address")
        parsed_addresses.append((parsed.version, address))
    parsed_addresses.sort()
    return tuple(address for _, address in parsed_addresses)


def _header(headers, name: str) -> str | None:
    value = headers.get(name)
    if value is None:
        value = headers.get(name.lower())
    return str(value) if value is not None else None


def _decode_text(body: bytes, content_type: str) -> str:
    match = re.search(r"charset\s*=\s*['\"]?([^;'\"\s]+)", content_type, re.IGNORECASE)
    encoding = match.group(1) if match else "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _read_bounded(response, max_bytes: int) -> bytes:
    content_length = _header(response.headers, "Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise SafeFetchError("page_too_large", http_status=response.status)
        except ValueError:
            # A malformed length header is ignored; the streamed cap still applies.
            pass

    chunks: list[bytes] = []
    total = 0
    while total <= max_bytes:
        chunk = response.read(min(64 * 1024, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise SafeFetchError("page_too_large", http_status=response.status)
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_public_job_page(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_BODY_BYTES,
    resolver=None,
    connection_factory=None,
) -> FetchedPublicPage:
    """Fetch one public HTTPS page while pinning each validated IP connection.

    No proxies, cookies, credentials or automatic redirects are used. The
    function returns bytes/text and makes no claim that the page is a job
    posting; extraction/verification is a separate stage.
    """
    if not 1 <= int(timeout) <= 60 or not 1 <= int(max_bytes) <= 10_000_000:
        raise ValueError("Invalid fetch timeout or size limit.")

    current = str(url or "").strip()
    seen: set[str] = set()
    for redirect_count in range(MAX_REDIRECTS + 1):
        if current in seen:
            raise SafeFetchError("redirect_loop")
        seen.add(current)

        host, target, original_netloc = _parse_public_https_url(current)
        addresses = _resolve_public_addresses(host, resolver=resolver)
        last_error = None
        response = None
        conn = None

        for pinned_ip in addresses:
            try:
                factory = connection_factory or _PinnedHTTPSConnection
                conn = factory(host, pinned_ip, timeout=timeout)
                conn.request(
                    "GET",
                    target,
                    headers={
                        "Host": original_netloc,
                        "User-Agent": "JobBeeper-GoogleAlerts/1.0",
                        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
                        "Accept-Encoding": "identity",
                        "Connection": "close",
                    },
                )
                response = conn.getresponse()
                break
            except SafeFetchError:
                raise
            except (OSError, ssl.SSLError, http.client.HTTPException):
                last_error = "connection_failed"
                if conn is not None:
                    conn.close()
                conn = None
                response = None

        if response is None:
            raise SafeFetchError(last_error or "connection_failed")

        try:
            status = int(response.status)
            headers = response.headers

            if status in {301, 302, 303, 307, 308}:
                location = _header(headers, "Location")
                if not location:
                    raise SafeFetchError("redirect_missing_location", http_status=status)
                if redirect_count >= MAX_REDIRECTS:
                    raise SafeFetchError("redirect_limit", http_status=status)
                current = urljoin(current, location)
                continue

            if status != 200:
                raise SafeFetchError(
                    "upstream_http_error",
                    http_status=status,
                )

            content_type_header = _header(headers, "Content-Type") or ""
            content_type = content_type_header.split(";", 1)[0].strip().lower()
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise SafeFetchError("unexpected_content_type", http_status=status)

            body = _read_bounded(response, max_bytes)
            return FetchedPublicPage(
                final_url=current,
                http_status=status,
                content_type=content_type,
                body=body,
                text=_decode_text(body, content_type_header),
            )
        finally:
            if conn is not None:
                conn.close()

    raise SafeFetchError("redirect_limit")
