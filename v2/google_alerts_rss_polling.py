"""Conditional polling and secret-free checkpoints for Google Alerts Atom feeds.

This module does not schedule feeds or fetch destination job pages. Feed URLs
are bearer-like secrets: callers supply them at runtime, while SQLite stores
only a stable opaque feed ID, HTTP validators and parsed result metadata.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests

from v2.google_alerts_rss import (
    DEFAULT_MAX_FEED_BYTES,
    GoogleAlertsFeed,
    parse_google_alerts_atom,
)

ATOM_ACCEPT = "application/atom+xml, application/xml;q=0.9, text/xml;q=0.8"
DEFAULT_TIMEOUT = (5, 20)
MAX_FEED_REDIRECTS = 3
_ALLOWED_FEED_HOSTS = {"google.com", "www.google.com"}
_ALLOWED_FEED_PATH = re.compile(
    r"^/alerts/feeds/[A-Za-z0-9_-]{4,80}/[A-Za-z0-9_-]{4,100}/?$"
)


class GoogleAlertsFeedError(Exception):
    """Sanitized polling error. Never includes the private feed URL or body."""

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
class GoogleAlertsFeedConfig:
    """Runtime feed config; hide the bearer-like URL from repr/logging."""

    feed_id: str
    label: str
    url: str = field(repr=False)


def load_google_alerts_feed_configs(
    config_path: str | Path,
    *,
    max_feeds: int = 98,
    max_file_bytes: int = 262_144,
) -> tuple[GoogleAlertsFeedConfig, ...]:
    """Load private feed URLs from an owner-only file outside the repository.

    Expected JSON shape:
      {"feeds": [{"id": "alert-001", "label": "Software Engineer India",
                  "url": "https://www.google.com/alerts/feeds/..."}]}

    The file should be mounted read-only with mode 0400 or 0600. URLs are
    validated in memory only and are never written to the database.
    """
    path = Path(config_path)
    if not path.is_absolute() or path.is_symlink():
        raise GoogleAlertsFeedError("invalid_feed_config_path")
    try:
        resolved = path.resolve(strict=True)
        repo_root = Path(__file__).resolve().parents[1]
        resolved.relative_to(repo_root)
        raise GoogleAlertsFeedError("feed_config_must_be_outside_repository")
    except ValueError:
        # relative_to raises ValueError when the config is outside the repo.
        pass
    except FileNotFoundError:
        raise GoogleAlertsFeedError("feed_config_not_found") from None

    try:
        metadata = resolved.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise GoogleAlertsFeedError("feed_config_not_regular_file")
        if metadata.st_size > max_file_bytes:
            raise GoogleAlertsFeedError("feed_config_too_large")
        if os.name == "posix" and stat.S_IMODE(metadata.st_mode) & 0o077:
            raise GoogleAlertsFeedError("feed_config_permissions_too_open")
        raw = resolved.read_text(encoding="utf-8")
    except GoogleAlertsFeedError:
        raise
    except (OSError, UnicodeError):
        raise GoogleAlertsFeedError("feed_config_unreadable") from None

    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        raise GoogleAlertsFeedError("feed_config_invalid_json") from None
    if not isinstance(document, dict) or set(document) != {"feeds"}:
        raise GoogleAlertsFeedError("feed_config_invalid_shape")

    items = document.get("feeds")
    if not isinstance(items, list) or not items or len(items) > max_feeds:
        raise GoogleAlertsFeedError("feed_config_invalid_count")

    configs: list[GoogleAlertsFeedConfig] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "label", "url"}:
            raise GoogleAlertsFeedError("feed_config_invalid_entry")
        feed_id = item.get("id")
        label = item.get("label")
        url = item.get("url")
        if (
            not isinstance(feed_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", feed_id)
            or feed_id in seen_ids
            or not isinstance(label, str)
            or not label.strip()
            or len(label.strip()) > 120
            or not isinstance(url, str)
        ):
            raise GoogleAlertsFeedError("feed_config_invalid_entry")
        validated_url = _validate_feed_url(url)
        configs.append(
            GoogleAlertsFeedConfig(
                feed_id=feed_id,
                label=label.strip(),
                url=validated_url,
            )
        )
        seen_ids.add(feed_id)

    return tuple(configs)


@dataclass(frozen=True)
class FeedCheckpoint:
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class FeedPollResult:
    status: str
    http_status: int
    fetched_at: str
    etag: str | None = None
    last_modified: str | None = None
    feed: GoogleAlertsFeed | None = None

    @property
    def entries(self):
        return self.feed.entries if self.feed is not None else ()


@dataclass(frozen=True)
class FeedRecordResult:
    new_entries: int
    total_entries: int


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _utc_iso(value: dt.datetime | None = None) -> str:
    current = value or _utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    return current.astimezone(dt.timezone.utc).isoformat()


def _validate_feed_url(value: str) -> str:
    """Only allow Google Alerts feed URLs, never arbitrary feed locations."""
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        raise GoogleAlertsFeedError("invalid_feed_url") from None

    if (
        parsed.scheme.lower() != "https"
        or (parsed.hostname or "").lower() not in _ALLOWED_FEED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not _ALLOWED_FEED_PATH.fullmatch(parsed.path)
    ):
        raise GoogleAlertsFeedError("invalid_feed_url")
    return raw


def _retry_after_seconds(value: str | None, now: dt.datetime) -> int | None:
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
        return max(
            0,
            min(86_400, int((parsed.astimezone(dt.timezone.utc) - now).total_seconds())),
        )


def _read_bounded(response: Any, max_bytes: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise GoogleAlertsFeedError("feed_too_large", http_status=200)
        except ValueError:
            pass

    chunks: list[bytes] = []
    total = 0
    try:
        iterator = response.iter_content(chunk_size=64 * 1024)
        for chunk in iterator:
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise GoogleAlertsFeedError("feed_too_large", http_status=200)
            chunks.append(chunk)
    except GoogleAlertsFeedError:
        raise
    except Exception:
        raise GoogleAlertsFeedError("feed_read_error", http_status=200) from None
    return b"".join(chunks)


def poll_google_alerts_feed(
    feed_url: str,
    checkpoint: FeedCheckpoint | None = None,
    *,
    session: requests.Session | Any | None = None,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_FEED_BYTES,
    now: dt.datetime | None = None,
) -> FeedPollResult:
    """Fetch one feed with conditional headers and bounded Google-only redirects.

    The returned ETag/Last-Modified values should be persisted only after the
    parsed entries are durably saved. The original URL is never copied into a
    result or exception, and redirects to non-Google hosts are rejected.
    """
    current_time = now or _utc_now()
    fetched_at = _utc_iso(current_time)
    current_url = _validate_feed_url(feed_url)
    validators = checkpoint or FeedCheckpoint()
    headers = {"Accept": ATOM_ACCEPT, "User-Agent": "JobBeeper-GoogleAlerts/1.0"}
    if validators.etag:
        headers["If-None-Match"] = validators.etag
    if validators.last_modified:
        headers["If-Modified-Since"] = validators.last_modified

    client = session or requests.Session()
    owns_session = session is None

    try:
        for redirect_count in range(MAX_FEED_REDIRECTS + 1):
            try:
                response = client.get(
                    current_url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=False,
                    stream=True,
                )
            except requests.RequestException:
                raise GoogleAlertsFeedError("network_error") from None
            except Exception:
                raise GoogleAlertsFeedError("network_error") from None

            try:
                status = int(response.status_code)
                response_headers = response.headers

                if status in {301, 302, 303, 307, 308}:
                    location = response_headers.get("Location")
                    if not location or redirect_count >= MAX_FEED_REDIRECTS:
                        raise GoogleAlertsFeedError("invalid_feed_redirect", http_status=status)
                    next_url = urljoin(current_url, location)
                    current_url = _validate_feed_url(next_url)
                    continue

                if status == 304:
                    return FeedPollResult(
                        status="not_modified",
                        http_status=status,
                        fetched_at=fetched_at,
                        etag=response_headers.get("ETag") or validators.etag,
                        last_modified=(
                            response_headers.get("Last-Modified")
                            or validators.last_modified
                        ),
                    )

                if status == 429 or status == 503:
                    raise GoogleAlertsFeedError(
                        "rate_limited" if status == 429 else "upstream_unavailable",
                        http_status=status,
                        retry_after_seconds=_retry_after_seconds(
                            response_headers.get("Retry-After"), current_time
                        ),
                    )
                if status != 200:
                    raise GoogleAlertsFeedError(
                        f"http_{status}" if 400 <= status < 500 else "upstream_error",
                        http_status=status,
                    )

                content_type = (
                    response_headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if content_type not in {
                    "application/atom+xml", "application/xml", "text/xml"
                }:
                    raise GoogleAlertsFeedError(
                        "unexpected_content_type", http_status=status
                    )

                payload = _read_bounded(response, max_bytes)
                try:
                    parsed_feed = parse_google_alerts_atom(payload, max_bytes=max_bytes)
                except (TypeError, ValueError):
                    raise GoogleAlertsFeedError(
                        "invalid_atom_feed", http_status=status
                    ) from None

                return FeedPollResult(
                    status="modified",
                    http_status=status,
                    fetched_at=fetched_at,
                    etag=response_headers.get("ETag"),
                    last_modified=response_headers.get("Last-Modified"),
                    feed=parsed_feed,
                )
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

        raise GoogleAlertsFeedError("too_many_redirects")
    finally:
        if owns_session:
            client.close()


def init_google_alerts_rss_schema(conn: sqlite3.Connection) -> None:
    """Create feed checkpoint and result-queue tables on an existing app DB."""
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS google_alert_rss_feed_state (
            feed_id TEXT PRIMARY KEY,
            feed_label TEXT NOT NULL,
            etag TEXT,
            last_modified TEXT,
            last_checked_at TEXT,
            last_success_at TEXT,
            last_http_status INTEGER,
            retry_after_at TEXT,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            last_error_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS google_alert_rss_entries (
            feed_id TEXT NOT NULL REFERENCES google_alert_rss_feed_state(feed_id)
                ON DELETE CASCADE,
            entry_id TEXT NOT NULL,
            title TEXT NOT NULL,
            snippet TEXT NOT NULL DEFAULT '',
            destination_url TEXT NOT NULL,
            canonical_url TEXT NOT NULL,
            published_at TEXT,
            updated_at TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            processing_status TEXT NOT NULL DEFAULT 'queued'
                CHECK (processing_status IN (
                    'queued', 'processing', 'verified', 'rejected',
                    'needs_review', 'blocked', 'retryable_error', 'dead_letter'
                )),
            attempt_count INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT,
            last_error_code TEXT,
            last_http_status INTEGER,
            PRIMARY KEY (feed_id, entry_id)
        );

        CREATE INDEX IF NOT EXISTS idx_google_alert_rss_entries_queue
            ON google_alert_rss_entries(processing_status, next_attempt_at);
        CREATE INDEX IF NOT EXISTS idx_google_alert_rss_entries_canonical
            ON google_alert_rss_entries(canonical_url);
        """
    )


def get_feed_checkpoint(
    conn: sqlite3.Connection, feed_id: str
) -> FeedCheckpoint:
    row = conn.execute(
        """
        SELECT etag, last_modified
        FROM google_alert_rss_feed_state
        WHERE feed_id=?
        """,
        (feed_id,),
    ).fetchone()
    if row is None:
        return FeedCheckpoint()
    return FeedCheckpoint(etag=row[0], last_modified=row[1])


def record_feed_success(
    conn: sqlite3.Connection,
    *,
    feed_id: str,
    feed_label: str,
    result: FeedPollResult,
) -> FeedRecordResult:
    """Atomically persist parsed entries and validators before acknowledging poll."""
    if not feed_id or len(feed_id) > 128 or not feed_label or len(feed_label) > 120:
        raise ValueError("A bounded feed ID and label are required.")
    now_text = result.fetched_at
    new_entries = 0

    with conn:
        conn.execute(
            """
            INSERT INTO google_alert_rss_feed_state (
                feed_id, feed_label, etag, last_modified, last_checked_at,
                last_success_at, last_http_status, retry_after_at,
                consecutive_failures, last_error_code, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0, NULL, ?, ?)
            ON CONFLICT(feed_id) DO UPDATE SET
                feed_label=excluded.feed_label,
                etag=COALESCE(excluded.etag, google_alert_rss_feed_state.etag),
                last_modified=COALESCE(
                    excluded.last_modified, google_alert_rss_feed_state.last_modified
                ),
                last_checked_at=excluded.last_checked_at,
                last_success_at=excluded.last_success_at,
                last_http_status=excluded.last_http_status,
                retry_after_at=NULL,
                consecutive_failures=0,
                last_error_code=NULL,
                updated_at=excluded.updated_at
            """,
            (
                feed_id, feed_label, result.etag, result.last_modified,
                now_text, now_text, result.http_status, now_text, now_text,
            ),
        )

        for entry in result.entries:
            exists_before = conn.execute(
                """
                SELECT 1 FROM google_alert_rss_entries
                WHERE feed_id=? AND entry_id=?
                """,
                (feed_id, entry.entry_id),
            ).fetchone()
            if exists_before is None:
                new_entries += 1

            conn.execute(
                """
                INSERT INTO google_alert_rss_entries (
                    feed_id, entry_id, title, snippet, destination_url,
                    canonical_url, published_at, updated_at, first_seen_at,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(feed_id, entry_id) DO UPDATE SET
                    title=excluded.title,
                    snippet=excluded.snippet,
                    destination_url=excluded.destination_url,
                    canonical_url=excluded.canonical_url,
                    published_at=COALESCE(
                        excluded.published_at, google_alert_rss_entries.published_at
                    ),
                    updated_at=COALESCE(
                        excluded.updated_at, google_alert_rss_entries.updated_at
                    ),
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    feed_id, entry.entry_id, entry.title, entry.snippet,
                    entry.destination_url, entry.canonical_url,
                    entry.published_at, entry.updated_at, now_text, now_text,
                ),
            )

        total = conn.execute(
            "SELECT COUNT(*) FROM google_alert_rss_entries WHERE feed_id=?",
            (feed_id,),
        ).fetchone()[0]

    return FeedRecordResult(new_entries=new_entries, total_entries=int(total))


def record_feed_failure(
    conn: sqlite3.Connection,
    *,
    feed_id: str,
    feed_label: str,
    error: GoogleAlertsFeedError,
    checked_at: str | None = None,
) -> None:
    """Persist a sanitized failure code and backoff deadline, never exception text."""
    if not feed_id or len(feed_id) > 128 or not feed_label or len(feed_label) > 120:
        raise ValueError("A bounded feed ID and label are required.")
    when = checked_at or _utc_iso()
    retry_at = None
    if error.retry_after_seconds is not None:
        retry_at = _utc_iso(
            dt.datetime.fromisoformat(when)
            + dt.timedelta(seconds=error.retry_after_seconds)
        )
    with conn:
        conn.execute(
            """
            INSERT INTO google_alert_rss_feed_state (
                feed_id, feed_label, last_checked_at, last_http_status,
                retry_after_at, consecutive_failures, last_error_code,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(feed_id) DO UPDATE SET
                feed_label=excluded.feed_label,
                last_checked_at=excluded.last_checked_at,
                last_http_status=excluded.last_http_status,
                retry_after_at=excluded.retry_after_at,
                consecutive_failures=
                    google_alert_rss_feed_state.consecutive_failures + 1,
                last_error_code=excluded.last_error_code,
                updated_at=excluded.updated_at
            """,
            (
                feed_id, feed_label, when, error.http_status, retry_at,
                error.code, when, when,
            ),
        )


@dataclass(frozen=True)
class FeedBatchItem:
    feed_id: str
    status: str
    new_entries: int = 0
    total_entries: int = 0
    error_code: str | None = None


@dataclass(frozen=True)
class FeedBatchSummary:
    checked: int
    modified: int
    not_modified: int
    failed: int
    skipped_backoff: int
    new_entries: int
    items: tuple[FeedBatchItem, ...]


def _parse_utc_timestamp(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def poll_google_alerts_feed_batch(
    conn: sqlite3.Connection,
    feeds: tuple[GoogleAlertsFeedConfig, ...] | list[GoogleAlertsFeedConfig],
    *,
    session: requests.Session | Any | None = None,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_FEED_BYTES,
    now: dt.datetime | None = None,
) -> FeedBatchSummary:
    """Poll a configured feed set sequentially, persisting every result safely.

    This is a one-shot batch primitive, not a scheduler. It respects any stored
    Retry-After deadline, reuses one HTTP session, and returns only opaque feed
    IDs and sanitized status codes. The caller controls when the next batch
    starts and must keep the feed list in a protected runtime configuration.
    """
    current_time = now or _utc_now()
    checked_at = _utc_iso(current_time)
    client = session or requests.Session()
    owns_session = session is None
    items: list[FeedBatchItem] = []

    try:
        for feed in feeds:
            row = conn.execute(
                "SELECT retry_after_at FROM google_alert_rss_feed_state WHERE feed_id=?",
                (feed.feed_id,),
            ).fetchone()
            retry_at = _parse_utc_timestamp(row[0]) if row and row[0] else None
            if retry_at and retry_at > current_time.astimezone(dt.timezone.utc):
                items.append(
                    FeedBatchItem(feed_id=feed.feed_id, status="skipped_backoff")
                )
                continue

            try:
                result = poll_google_alerts_feed(
                    feed.url,
                    get_feed_checkpoint(conn, feed.feed_id),
                    session=client,
                    timeout=timeout,
                    max_bytes=max_bytes,
                    now=current_time,
                )
                saved = record_feed_success(
                    conn,
                    feed_id=feed.feed_id,
                    feed_label=feed.label,
                    result=result,
                )
                items.append(
                    FeedBatchItem(
                        feed_id=feed.feed_id,
                        status=result.status,
                        new_entries=saved.new_entries,
                        total_entries=saved.total_entries,
                    )
                )
            except GoogleAlertsFeedError as exc:
                record_feed_failure(
                    conn,
                    feed_id=feed.feed_id,
                    feed_label=feed.label,
                    error=exc,
                    checked_at=checked_at,
                )
                items.append(
                    FeedBatchItem(
                        feed_id=feed.feed_id,
                        status="failed",
                        error_code=exc.code,
                    )
                )
    finally:
        if owns_session:
            client.close()

    return FeedBatchSummary(
        checked=sum(item.status != "skipped_backoff" for item in items),
        modified=sum(item.status == "modified" for item in items),
        not_modified=sum(item.status == "not_modified" for item in items),
        failed=sum(item.status == "failed" for item in items),
        skipped_backoff=sum(item.status == "skipped_backoff" for item in items),
        new_entries=sum(item.new_entries for item in items),
        items=tuple(items),
    )
