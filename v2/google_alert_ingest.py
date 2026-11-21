"""Durable intake for owner-forwarded Google Alert email events.

Cloudflare Email Workers parse MIME and enqueue compact event JSON. The queue
consumer signs the exact JSON bytes; this module verifies and persists them
before the webhook returns success. Destination fetching is deliberately a
separate processing stage.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from v2.sqlite_store import DB_LOCK, connect

MAX_EVENT_BODY_BYTES = 96 * 1024
MAX_LINKS_PER_EVENT = 100
MAX_TIMESTAMP_SKEW_SECONDS = 300
MAX_EVENT_ID_LENGTH = 256
MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 500
MAX_SNIPPET_LENGTH = 1200
_SIGNATURE_RE = re.compile(r"^[0-9a-f]{64}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: str | Path) -> sqlite3.Connection:
    connection = connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def normalized_public_url(value: Any) -> tuple[str, str]:
    """Validate a syntactically public HTTP(S) URL and return URL + fingerprint.

    DNS resolution and redirect-hop checks must be repeated by the eventual
    fetcher; this function is only an ingress syntax check and is not an SSRF
    boundary for network requests.
    """
    if not isinstance(value, str):
        raise ValueError("result URL must be a string")
    raw = value.strip()
    if not raw or len(raw) > MAX_URL_LENGTH:
        raise ValueError("result URL is empty or too long")
    try:
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        raise ValueError("result URL is malformed") from None
    if scheme not in {"http", "https"} or not host:
        raise ValueError("result URL must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("result URL must not contain embedded credentials")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(
        (".localhost", ".local", ".internal", ".test")
    ):
        raise ValueError("result URL must not target a local hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("result URL must not target a non-public IP address")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("result URL port is invalid")

    # Preserve path/query case; URL paths can be case-sensitive. Remove only
    # fragments, which are not sent to the HTTP server.
    normalized = urlunsplit((
        scheme,
        host if port is None else f"{host}:{port}",
        parsed.path or "/",
        parsed.query,
        "",
    ))
    fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return normalized, fingerprint


def verify_request_signature(
    body: bytes,
    timestamp_header: str,
    signature_header: str,
    secret: str,
    *,
    now: float | None = None,
    max_skew_seconds: int = MAX_TIMESTAMP_SKEW_SECONDS,
) -> bool:
    """Verify timestamped HMAC-SHA256 over '<timestamp>.' + exact body bytes."""
    if not isinstance(secret, str) or len(secret) < 32:
        return False
    if not isinstance(timestamp_header, str) or not timestamp_header.isdigit():
        return False
    if not isinstance(signature_header, str) or not _SIGNATURE_RE.fullmatch(signature_header):
        return False
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        return False
    current = time.time() if now is None else float(now)
    if abs(current - timestamp) > max_skew_seconds:
        return False
    signed = timestamp_header.encode("ascii") + b"." + body
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def init_schema(db_path: str | Path) -> None:
    """Create the owner-scoped inbox and deduplicated result URL work tables."""
    with DB_LOCK, _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS google_alert_messages (
                event_id TEXT PRIMARY KEY,
                message_id TEXT,
                payload_sha256 TEXT NOT NULL,
                envelope_from TEXT NOT NULL DEFAULT '',
                envelope_to TEXT NOT NULL DEFAULT '',
                header_from TEXT NOT NULL DEFAULT '',
                subject TEXT NOT NULL DEFAULT '',
                received_at TEXT,
                result_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'received',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS google_alert_urls (
                url_fingerprint TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                normalized_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                lease_until TEXT,
                last_error_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS google_alert_url_observations (
                event_id TEXT NOT NULL REFERENCES google_alert_messages(event_id) ON DELETE CASCADE,
                url_fingerprint TEXT NOT NULL REFERENCES google_alert_urls(url_fingerprint) ON DELETE CASCADE,
                link_title TEXT NOT NULL DEFAULT '',
                snippet TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY(event_id, url_fingerprint)
            );

            CREATE INDEX IF NOT EXISTS idx_google_alert_urls_due
                ON google_alert_urls(status, next_attempt_at, lease_until);
            CREATE INDEX IF NOT EXISTS idx_google_alert_messages_created
                ON google_alert_messages(created_at);
            """
        )


def _clean_optional_text(value: Any, field: str, maximum: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValueError(f"{field} is too long")
    return cleaned


def validate_event(payload: Any) -> dict[str, Any]:
    """Validate compact, versioned Worker payload before any database writes."""
    if not isinstance(payload, dict):
        raise ValueError("event must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported Google Alert event schema version")

    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not 8 <= len(event_id) <= MAX_EVENT_ID_LENGTH:
        raise ValueError("event_id must contain 8 to 256 characters")
    if any(ord(char) < 33 or ord(char) > 126 for char in event_id):
        raise ValueError("event_id contains invalid characters")

    links = payload.get("links")
    if not isinstance(links, list) or len(links) > MAX_LINKS_PER_EVENT:
        raise ValueError(f"links must be a list containing at most {MAX_LINKS_PER_EVENT} items")

    cleaned_links: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("each result link must be an object")
        normalized_url, fingerprint = normalized_public_url(link.get("url"))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        cleaned_links.append({
            "url": normalized_url,
            "fingerprint": fingerprint,
            "title": _clean_optional_text(link.get("title"), "link title", MAX_TITLE_LENGTH),
            "snippet": _clean_optional_text(link.get("snippet"), "link snippet", MAX_SNIPPET_LENGTH),
        })

    schema = {
        "event_id": event_id,
        "message_id": _clean_optional_text(payload.get("message_id"), "message_id", 512),
        "envelope_from": _clean_optional_text(payload.get("envelope_from"), "envelope_from", 320),
        "envelope_to": _clean_optional_text(payload.get("envelope_to"), "envelope_to", 320),
        "header_from": _clean_optional_text(payload.get("header_from"), "header_from", 512),
        "subject": _clean_optional_text(payload.get("subject"), "subject", 512),
        "received_at": _clean_optional_text(payload.get("received_at"), "received_at", 80),
        "links": cleaned_links,
    }
    for field in ("envelope_from", "envelope_to"):
        if not schema[field] or "@" not in schema[field]:
            raise ValueError(f"{field} must contain an email address")
    return schema


def ingest_event(db_path: str | Path, body: bytes, payload: Any) -> dict[str, Any]:
    """Persist one accepted Worker event atomically; repeated delivery is safe."""
    if not isinstance(body, bytes) or len(body) > MAX_EVENT_BODY_BYTES:
        raise ValueError("event body is too large")
    event = validate_event(payload)
    payload_hash = hashlib.sha256(body).hexdigest()
    created_at = _now_iso()
    inserted = False

    with DB_LOCK, _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT payload_sha256,result_count FROM google_alert_messages WHERE event_id=?",
            (event["event_id"],),
        ).fetchone()
        if existing is not None:
            if not hmac.compare_digest(str(existing["payload_sha256"]), payload_hash):
                raise ValueError("event_id was reused with a different payload")
            return {
                "accepted": True,
                "duplicate": True,
                "result_count": int(existing["result_count"]),
            }

        connection.execute(
            """
            INSERT INTO google_alert_messages (
                event_id,message_id,payload_sha256,envelope_from,envelope_to,
                header_from,subject,received_at,result_count,status,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,'received',?)
            """,
            (
                event["event_id"], event["message_id"], payload_hash,
                event["envelope_from"], event["envelope_to"], event["header_from"],
                event["subject"], event["received_at"] or None,
                len(event["links"]), created_at,
            ),
        )
        for link in event["links"]:
            connection.execute(
                """
                INSERT INTO google_alert_urls (
                    url_fingerprint,original_url,normalized_url,status,
                    attempts,next_attempt_at,lease_until,last_error_type,
                    created_at,updated_at
                ) VALUES (?,?,?,'pending',0,NULL,NULL,NULL,?,?)
                ON CONFLICT(url_fingerprint) DO NOTHING
                """,
                (
                    link["fingerprint"], link["url"], link["url"],
                    created_at, created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO google_alert_url_observations (
                    event_id,url_fingerprint,link_title,snippet,created_at
                ) VALUES (?,?,?,?,?)
                ON CONFLICT(event_id,url_fingerprint) DO NOTHING
                """,
                (
                    event["event_id"], link["fingerprint"],
                    link["title"], link["snippet"], created_at,
                ),
            )
        connection.commit()
        inserted = True

    return {
        "accepted": True,
        "duplicate": not inserted,
        "result_count": len(event["links"]),
    }
