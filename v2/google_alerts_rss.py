"""Parse Google Alerts Atom feeds without retaining mailbox/feed credentials."""
from __future__ import annotations

import html
import ipaddress
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from v2.dedupe import canonicalize_url

ATOM_NS = "http://www.w3.org/2005/Atom"
ATOM = f"{{{ATOM_NS}}}"
DEFAULT_MAX_FEED_BYTES = 1_048_576
MAX_REDIRECT_UNWRAPS = 3
_PRIVATE_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".test", ".invalid")


class _TextExtractor(HTMLParser):
    """Extract readable text from HTML fragments without executing markup."""

    _BLOCK_TAGS = {
        "address", "article", "br", "dd", "div", "dl", "dt", "h1", "h2",
        "h3", "h4", "h5", "h6", "li", "ol", "p", "section", "td", "th",
        "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(value or ""))
    parser.close()
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def _safe_public_https_url(value: str) -> str:
    """Apply static URL checks; DNS resolution/redirect-hop checks belong to fetcher."""
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid result URL.") from exc

    if parsed.scheme.lower() != "https" or not hostname:
        raise ValueError("Result URL must use HTTPS and include a hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Result URL must not contain embedded credentials.")
    if port not in (None, 443):
        raise ValueError("Result URL must use the default HTTPS port.")

    host = hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(_PRIVATE_HOST_SUFFIXES):
        raise ValueError("Result URL must not target a local or reserved hostname.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
            raise ValueError("Result URL hostname is not a valid public DNS name.")
    else:
        if not ip.is_global:
            raise ValueError("Result URL must not target a non-public IP address.")

    return raw


def unwrap_google_alert_url(value: str) -> str:
    """Unwrap Google's /url redirect and validate the final HTTPS destination.

    This function does not make network requests. Callers must still enforce
    DNS/IP SSRF checks on every resolved address and every redirect hop before
    fetching the destination.
    """
    candidate = str(value or "").strip()
    if not candidate:
        raise ValueError("Alert entry has no result URL.")

    seen: set[str] = set()
    for _ in range(MAX_REDIRECT_UNWRAPS + 1):
        candidate = urljoin("https://www.google.com/", candidate)
        parsed = urlsplit(candidate)
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() != "https" or not host:
            raise ValueError("Google Alert link must use HTTPS.")

        is_google = host == "google.com" or host.endswith(".google.com")
        if not (is_google and parsed.path.rstrip("/") == "/url"):
            return _safe_public_https_url(candidate)

        if candidate in seen:
            raise ValueError("Google Alert redirect contains a loop.")
        seen.add(candidate)
        query = parse_qs(parsed.query, keep_blank_values=False)
        targets = query.get("url") or query.get("q") or []
        if len(targets) != 1 or not targets[0].strip():
            raise ValueError(
                "Google Alert redirect does not contain one destination URL."
            )
        candidate = targets[0].strip()

    raise ValueError("Google Alert redirect exceeded the unwrap limit.")


def _child_text(parent: ET.Element, name: str) -> str:
    node = parent.find(f"{ATOM}{name}")
    return "" if node is None else "".join(node.itertext()).strip()


def _render_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    raw = "".join(node.itertext())
    if (node.attrib.get("type") or "").lower() in {"html", "xhtml"}:
        return _html_to_text(raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def _entry_link(entry: ET.Element) -> str:
    links = entry.findall(f"{ATOM}link")
    # Google's current Alerts Atom sample omits rel; Atom's default is alternate.
    candidates = [
        link for link in links
        if (link.attrib.get("rel") or "alternate").lower() == "alternate"
        and link.attrib.get("href")
    ]
    if not candidates:
        raise ValueError("Alert entry has no alternate link.")
    return candidates[0].attrib["href"]


@dataclass(frozen=True)
class GoogleAlertEntry:
    entry_id: str
    title: str
    snippet: str
    destination_url: str
    canonical_url: str
    published_at: str | None
    updated_at: str | None


@dataclass(frozen=True)
class GoogleAlertsFeed:
    title: str
    updated_at: str | None
    entries: tuple[GoogleAlertEntry, ...]

    def to_dict(self) -> dict:
        """Return only safe parsed fields; never include feed IDs or self URL."""
        return {
            "title": self.title,
            "updated_at": self.updated_at,
            "entries": [asdict(entry) for entry in self.entries],
        }


def parse_google_alerts_atom(
    payload: str | bytes,
    *,
    max_bytes: int = DEFAULT_MAX_FEED_BYTES,
) -> GoogleAlertsFeed:
    """Parse an Atom feed and return unique, validated result destinations.

    The caller should supply the feed body only. Do not persist the feed URL,
    root feed ID, self link, or raw XML; Google Alerts feed URLs may be bearer
    credentials. Feed polling/ETag handling and safe network fetching are
    intentionally outside this pure parser.
    """
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        raw = payload
    else:
        raise TypeError("Feed payload must be text or bytes.")

    if len(raw) > max_bytes:
        raise ValueError("Google Alerts feed exceeds the configured size limit.")
    if re.search(br"<!\s*(DOCTYPE|ENTITY)\b", raw, flags=re.IGNORECASE):
        raise ValueError("DTD and entity declarations are not allowed in Alert feeds.")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("Google Alerts feed is not valid XML.") from exc
    if root.tag != f"{ATOM}feed":
        raise ValueError("Expected an Atom 1.0 feed.")

    feed_title_node = root.find(f"{ATOM}title")
    feed_title = _render_text(feed_title_node)
    feed_updated = _child_text(root, "updated") or None

    entries: list[GoogleAlertEntry] = []
    seen_ids: set[str] = set()
    for node in root.findall(f"{ATOM}entry"):
        entry_id = _child_text(node, "id")
        if not entry_id:
            raise ValueError("Alert entry is missing its stable Atom ID.")
        if entry_id in seen_ids:
            continue

        title = _render_text(node.find(f"{ATOM}title"))
        snippet = _render_text(node.find(f"{ATOM}content"))
        destination = unwrap_google_alert_url(_entry_link(node))
        canonical = canonicalize_url(destination)

        entries.append(
            GoogleAlertEntry(
                entry_id=entry_id,
                title=title,
                snippet=snippet,
                destination_url=destination,
                canonical_url=canonical,
                published_at=_child_text(node, "published") or None,
                updated_at=_child_text(node, "updated") or None,
            )
        )
        seen_ids.add(entry_id)

    return GoogleAlertsFeed(
        title=feed_title,
        updated_at=feed_updated,
        entries=tuple(entries),
    )
