"""Safe parser for owner-controlled Google Alerts email notifications.

The parser accepts an RFC 5322 message (for example, Gmail API format=raw),
validates the sender/subject, and extracts each result from the HTML JSON
metadata, the visible HTML cards, or the plain-text body. It does not perform
network requests, retain raw email content, or expose the alert query.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from typing import Iterable
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from v2.dedupe import canonicalize_url


GOOGLE_ALERTS_SENDER = "googlealerts-noreply@google.com"
GOOGLE_ALERTS_SUBJECT_PREFIX = "google alert -"
GOOGLE_REDIRECT_HOSTS = {
    "google.com",
    "www.google.com",
    "google.co.in",
    "www.google.co.in",
}
MAX_RAW_EMAIL_BYTES = 2 * 1024 * 1024
MAX_BODY_BYTES = 1024 * 1024
MAX_RESULTS_PER_EMAIL = 100
MAX_REDIRECT_UNWRAPS = 3


class GoogleAlertEmailError(ValueError):
    """Sanitized parse error. Never includes message content or private URLs."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GoogleAlertEmailResult:
    title: str
    snippet: str
    destination_url: str
    canonical_url: str
    source_domain: str
    extraction_method: str


@dataclass(frozen=True)
class ParsedGoogleAlertEmail:
    message_fingerprint: str
    sent_at: str | None
    results: tuple[GoogleAlertEmailResult, ...]


def _message_fingerprint(raw_message: bytes, message_id: str | None) -> str:
    material = (message_id or "").strip().encode("utf-8")
    if not material:
        material = raw_message
    return hashlib.sha256(material).hexdigest()


def _sender_is_google_alerts(value: str | None) -> bool:
    addresses = [
        address.strip().casefold()
        for _, address in getaddresses([value or ""])
        if address.strip()
    ]
    # A trusted address mixed with another From address is ambiguous.
    return len(addresses) == 1 and addresses[0] == GOOGLE_ALERTS_SENDER


def _is_alert_subject(value: str | None) -> bool:
    return bool(
        isinstance(value, str)
        and value.strip().casefold().startswith(GOOGLE_ALERTS_SUBJECT_PREFIX)
    )


def _google_authentication_passes(message) -> bool:
    """Require one unambiguous Gmail authentication result, not just From."""
    values = message.get_all("Authentication-Results", [])
    if len(values) != 1:
        return False
    result = re.sub(r"\s+", " ", str(values[0])).casefold()
    return bool(
        result.startswith("mx.google.com;")
        and re.search(
            r"\bdkim=pass\b.*?header\.i=@google\.com(?=$|[\\s;])",
            result,
        )
        and re.search(
            r"\bdmarc=pass\b.*?header\.from=google\.com(?=$|[\\s;])",
            result,
        )
    )


def _clean_text(value: object, limit: int = 4000) -> str:
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _unwrap_destination(value: str) -> str:
    """Unwrap Google redirect links without making a network request."""
    current = str(value or "").strip()
    for _ in range(MAX_REDIRECT_UNWRAPS + 1):
        try:
            parsed = urlsplit(current)
            port = parsed.port
        except ValueError:
            raise GoogleAlertEmailError("invalid_result_url") from None

        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
        ):
            raise GoogleAlertEmailError("invalid_result_url")

        host = parsed.hostname.lower()
        if host in GOOGLE_REDIRECT_HOSTS and parsed.path.rstrip("/") == "/url":
            destination = parse_qs(parsed.query, keep_blank_values=False).get("url")
            if not destination or not destination[0]:
                raise GoogleAlertEmailError("invalid_google_redirect")
            current = destination[0].strip()
            continue

        return current

    raise GoogleAlertEmailError("too_many_google_redirects")


def _make_result(
    title: object,
    snippet: object,
    url: object,
    extraction_method: str,
) -> GoogleAlertEmailResult | None:
    clean_title = _clean_text(title, 500)
    raw_url = url.strip() if isinstance(url, str) else ""
    if not clean_title or not raw_url:
        return None

    try:
        destination = _unwrap_destination(raw_url)
    except GoogleAlertEmailError:
        return None

    canonical = canonicalize_url(destination)
    parsed = urlsplit(destination)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not canonical or not host:
        return None

    return GoogleAlertEmailResult(
        title=clean_title,
        snippet=_clean_text(snippet, 4000),
        destination_url=destination,
        canonical_url=canonical,
        source_domain=host,
        extraction_method=extraction_method,
    )


def _dedupe_results(
    results: Iterable[GoogleAlertEmailResult],
) -> tuple[GoogleAlertEmailResult, ...]:
    ordered: dict[str, GoogleAlertEmailResult] = {}
    for result in results:
        ordered.setdefault(result.canonical_url, result)
        if len(ordered) > MAX_RESULTS_PER_EMAIL:
            raise GoogleAlertEmailError("too_many_results")
    return tuple(ordered.values())


def _extract_structured_html(html: str) -> tuple[GoogleAlertEmailResult, ...]:
    soup = BeautifulSoup(html, "html.parser")
    extracted: list[GoogleAlertEmailResult] = []

    for script in soup.find_all("script", attrs={"data-scope": "inboxmarkup"}):
        if (script.get("type") or "").casefold() != "application/json":
            continue
        try:
            document = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        publisher = document.get("publisher", {}) if isinstance(document, dict) else {}
        if not isinstance(publisher, dict) or str(publisher.get("name", "")).casefold() != "google alerts":
            continue

        cards = document.get("cards", [])
        if not isinstance(cards, list):
            continue
        for card in cards:
            if not isinstance(card, dict):
                continue
            widgets = card.get("widgets", [])
            if not isinstance(widgets, list):
                continue
            for widget in widgets:
                if not isinstance(widget, dict) or str(widget.get("type", "")).upper() != "LINK":
                    continue
                result = _make_result(
                    widget.get("title"),
                    widget.get("description"),
                    widget.get("url"),
                    "structured_html_json",
                )
                if result:
                    extracted.append(result)

    return _dedupe_results(extracted)


def _extract_html_links(html: str) -> tuple[GoogleAlertEmailResult, ...]:
    soup = BeautifulSoup(html, "html.parser")
    extracted: list[GoogleAlertEmailResult] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        try:
            parsed = urlsplit(href)
        except ValueError:
            continue
        if (
            (parsed.hostname or "").lower() not in GOOGLE_REDIRECT_HOSTS
            or parsed.path.rstrip("/") != "/url"
        ):
            continue
        title = anchor.get_text(" ", strip=True)
        result = _make_result(title, "", href, "html_link")
        if result:
            extracted.append(result)
    return _dedupe_results(extracted)


def _extract_plain_text(plain: str) -> tuple[GoogleAlertEmailResult, ...]:
    """Fallback for Google Alerts messages that contain no HTML alternative."""
    extracted: list[GoogleAlertEmailResult] = []
    # Drop the Google-generated result-count/query banner so it is never
    # mistaken for the first job title.
    plain = re.sub(r"(?m)^={3}[^\r\n]*?={3}\s*", "", plain, count=1)
    link_pattern = re.compile(r"<(https://[^<>\s]+)>", flags=re.IGNORECASE)
    previous_end = 0

    for match in link_pattern.finditer(plain):
        raw_url = match.group(1)
        try:
            parsed = urlsplit(raw_url)
        except ValueError:
            previous_end = match.end()
            continue
        if (
            (parsed.hostname or "").lower() not in GOOGLE_REDIRECT_HOSTS
            or parsed.path.rstrip("/") != "/url"
        ):
            previous_end = match.end()
            continue

        block = plain[previous_end:match.start()].strip()
        previous_end = match.end()
        if not block:
            continue

        lines = [re.sub(r"\s+", " ", line).strip() for line in block.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue

        # The plain-text representation wraps long titles. Keep the first
        # line as the title and the rest as supporting snippet text; the
        # verified destination page remains the authoritative job source.
        title = lines[0]
        snippet = " ".join(lines[1:])
        result = _make_result(title, snippet, raw_url, "plain_text")
        if result:
            extracted.append(result)

    return _dedupe_results(extracted)


def _sent_at(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.isoformat()


def parse_google_alert_email(
    raw_message: bytes,
    *,
    max_raw_bytes: int = MAX_RAW_EMAIL_BYTES,
    max_body_bytes: int = MAX_BODY_BYTES,
) -> ParsedGoogleAlertEmail:
    """Parse one RFC 5322 Google Alerts message and extract every result card.

    The function deliberately does not return the sender, recipient, subject,
    alert query, Gmail IDs, raw headers, or raw MIME body. The message
    fingerprint is a SHA-256 digest suitable for idempotency bookkeeping.
    """
    if not isinstance(raw_message, bytes) or not raw_message:
        raise GoogleAlertEmailError("empty_message")
    if len(raw_message) > max_raw_bytes:
        raise GoogleAlertEmailError("message_too_large")

    try:
        message = BytesParser(policy=policy.default).parsebytes(raw_message)
    except Exception:
        raise GoogleAlertEmailError("invalid_mime_message") from None

    from_headers = message.get_all("From", [])
    if len(from_headers) != 1 or not _sender_is_google_alerts(from_headers[0]):
        raise GoogleAlertEmailError("unrecognized_sender")
    subject_headers = message.get_all("Subject", [])
    if len(subject_headers) != 1 or not _is_alert_subject(subject_headers[0]):
        raise GoogleAlertEmailError("unrecognized_subject")
    if not _google_authentication_passes(message):
        raise GoogleAlertEmailError("sender_authentication_failed")

    html_body = ""
    plain_body = ""
    total_body_bytes = 0
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type().lower()
        if content_type not in {"text/html", "text/plain"}:
            continue
        try:
            payload = part.get_payload(decode=True) or b""
            total_body_bytes += len(payload)
            if total_body_bytes > max_body_bytes:
                raise GoogleAlertEmailError("message_body_too_large")
            content = part.get_content()
        except GoogleAlertEmailError:
            raise
        except Exception:
            continue
        if not isinstance(content, str):
            continue
        if content_type == "text/html" and not html_body:
            html_body = content
        elif content_type == "text/plain" and not plain_body:
            plain_body = content

    results: tuple[GoogleAlertEmailResult, ...] = ()
    if html_body:
        results = _extract_structured_html(html_body)
        if not results:
            results = _extract_html_links(html_body)
    if not results and plain_body:
        results = _extract_plain_text(plain_body)
    if not results:
        raise GoogleAlertEmailError("no_alert_results_found")

    return ParsedGoogleAlertEmail(
        message_fingerprint=_message_fingerprint(
            raw_message, message.get("Message-ID")
        ),
        sent_at=_sent_at(message.get("Date")),
        results=results,
    )
