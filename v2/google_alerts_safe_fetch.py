"""SSRF-resistant fetcher for public job pages discovered by Google Alerts.

The URL is resolved and all returned IP addresses are validated before the
connection is created. The connection is then pinned to one validated address
while TLS still verifies the original hostname. Redirects are handled manually
and every new host is resolved and validated again.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import http.client
import ipaddress
import re
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlsplit

MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 5
MAX_BODY_BYTES = 2_000_000
DEFAULT_TIMEOUT_SECONDS = 12
ROBOTS_CACHE_TTL_SECONDS = 3600
ROBOTS_USER_AGENT = "JobBeeper-GoogleAlerts/1.0"
_ROBOTS_CACHE: dict[str, tuple[float, RobotFileParser]] = {}
_ROBOTS_CACHE_LOCK = threading.Lock()
ALLOWED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "text/plain",
}


class SafeFetchError(Exception):
    """Sanitized fetch failure that never includes the source URL."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.retry_after_seconds = retry_after_seconds
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
    # Construct Host from the validated IDNA hostname, not the untrusted
    # original authority string. Bracket IPv6 literals as required by HTTP.
    authority = f"[{host_ascii}]" if ":" in host_ascii else host_ascii
    # Fragments never reach the HTTP server.
    return host_ascii, target, authority


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


def _retry_after_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return max(0, min(86_400, int(float(value))))
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        delta = parsed.astimezone(dt.timezone.utc) - dt.datetime.now(dt.timezone.utc)
        return max(0, min(86_400, int(delta.total_seconds())))


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


def _robots_allows(
    url: str,
    *,
    timeout: int,
    resolver=None,
    connection_factory=None,
) -> bool:
    """Read/cached robots policy and fail closed if the policy cannot be read."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise SafeFetchError("robots_invalid_target")
    now = time.monotonic()
    with _ROBOTS_CACHE_LOCK:
        cached = _ROBOTS_CACHE.get(host)
        if cached and cached[0] > now:
            return cached[1].can_fetch(ROBOTS_USER_AGENT, url)

    authority = f"[{host}]" if ":" in host else host
    robots_url = f"https://{authority}/robots.txt"
    try:
        page = fetch_public_job_page(
            robots_url,
            timeout=timeout,
            max_bytes=256_000,
            resolver=resolver,
            connection_factory=connection_factory,
            _skip_robots=True,
        )
        if (urlsplit(page.final_url).hostname or "").lower().rstrip(".") != host:
            raise SafeFetchError("robots_redirect_cross_host")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(page.text.splitlines())
    except SafeFetchError as exc:
        if exc.http_status in (404, 410):
            # A missing robots file has no rules; a 401/403 explicitly denies.
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse([])
        elif exc.http_status in (401, 403):
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(["User-agent: *", "Disallow: /"])
        else:
            raise SafeFetchError(
                "robots_unavailable", http_status=exc.http_status
            ) from None

    with _ROBOTS_CACHE_LOCK:
        _ROBOTS_CACHE[host] = (now + ROBOTS_CACHE_TTL_SECONDS, parser)
    return parser.can_fetch(ROBOTS_USER_AGENT, url)


def fetch_public_job_page(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_BODY_BYTES,
    resolver=None,
    connection_factory=None,
    robots_checker=None,
    _skip_robots: bool = False,
) -> FetchedPublicPage:
    """Fetch one public HTTPS page while pinning each validated IP connection.

    No proxies, cookies, credentials or automatic redirects are used. The
    function returns bytes/text and makes no claim that the page is a job
    posting; extraction/verification is a separate stage.
    """
    if not 1 <= int(timeout) <= 60 or not 1 <= int(max_bytes) <= 10_000_000:
        raise ValueError("Invalid fetch timeout or size limit.")

    current = str(url or "").strip()
    _parse_public_https_url(current)
    seen: set[str] = set()
    for redirect_count in range(MAX_REDIRECTS + 1):
        if current in seen:
            raise SafeFetchError("redirect_loop")
        seen.add(current)

        host, target, original_netloc = _parse_public_https_url(current)
        # A redirect may change host; every hop must pass its own robots check
        # before a connection is made to that destination.
        if not _skip_robots:
            try:
                allowed = (
                    robots_checker(current)
                    if robots_checker is not None
                    else _robots_allows(
                        current,
                        timeout=timeout,
                        resolver=resolver,
                        connection_factory=connection_factory,
                    )
                )
            except SafeFetchError:
                raise
            except Exception:
                raise SafeFetchError("robots_unavailable") from None
            if not allowed:
                raise SafeFetchError("robots_disallowed")

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

            if status in {429, 503}:
                raise SafeFetchError(
                    "upstream_rate_limited" if status == 429 else "upstream_unavailable",
                    http_status=status,
                    retry_after_seconds=_retry_after_seconds(
                        _header(headers, "Retry-After")
                    ),
                )
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
