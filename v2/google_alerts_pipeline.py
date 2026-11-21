"""One-shot Google Alerts result verification and shared-job ingestion worker.

This module has no scheduler. It claims due queue rows, safely fetches public
pages (including robots.txt and DNS pinning), accepts only Schema.org
JobPosting records, then delegates normalized jobs to the existing V2
upsert_jobs() callback. The callback retains existing canonical dedupe and
per-user preference evaluation behavior.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

from v2.google_alerts_job_extract import extract_jobposting_jsonld
from v2.google_alerts_safe_fetch import SafeFetchError, fetch_public_job_page

UTC = dt.timezone.utc
DEFAULT_LEASE_SECONDS = 900
DEFAULT_MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class GoogleAlertsProcessingSummary:
    claimed: int
    verified: int
    inserted: int
    rejected: int
    blocked: int
    needs_review: int
    retryable: int
    dead_letter: int
    duplicate_entries_collapsed: int


def _utc_now(value: dt.datetime | None = None) -> dt.datetime:
    current = value or dt.datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _retry_delay(error: SafeFetchError, attempts: int) -> int:
    if error.retry_after_seconds is not None:
        return max(1, min(86_400, error.retry_after_seconds))
    return min(6 * 60 * 60, 60 * (2 ** max(0, attempts - 1)))


def _failure_disposition(error: SafeFetchError) -> str:
    if error.code in {
        "robots_disallowed",
        "robots_redirect_cross_host",
        "private_or_reserved_host",
        "private_or_reserved_ip",
        "dns_private_or_reserved_address",
        "dns_invalid_address",
        "url_not_public_https",
        "invalid_url",
        "invalid_hostname",
    } or error.http_status in (401, 403):
        return "blocked"
    if error.http_status in (404, 410):
        return "rejected"
    if (
        error.code in {
            "robots_unavailable",
            "connection_failed",
            "dns_resolution_failed",
            "dns_no_addresses",
            "upstream_rate_limited",
            "upstream_unavailable",
        }
        or error.http_status == 429
        or (error.http_status is not None and error.http_status >= 500)
    ):
        return "retryable_error"
    return "needs_review"


def _update_group_status(
    conn: sqlite3.Connection,
    keys: list[tuple[str, str]],
    *,
    status: str,
    error_code: str | None,
    http_status: int | None,
    next_attempt_at: str | None = None,
    last_seen_at: str | None = None,
) -> None:
    timestamp = last_seen_at or _iso(_utc_now())
    with conn:
        for feed_id, entry_id in keys:
            conn.execute(
                """
                UPDATE google_alert_rss_entries
                SET processing_status=?,
                    last_error_code=?,
                    last_http_status=?,
                    next_attempt_at=?,
                    last_seen_at=?
                WHERE feed_id=? AND entry_id=?
                """,
                (
                    status, error_code, http_status, next_attempt_at,
                    timestamp, feed_id, entry_id,
                ),
            )


def process_google_alert_rss_queue(
    conn: sqlite3.Connection,
    *,
    normalize_job_fn: Callable[..., dict[str, Any]],
    upsert_jobs_fn: Callable[[list[dict[str, Any]]], int],
    fetcher: Callable[..., Any] = fetch_public_job_page,
    extractor: Callable[..., Any] = extract_jobposting_jsonld,
    limit: int = 10,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: dt.datetime | None = None,
) -> GoogleAlertsProcessingSummary:
    """Process a bounded queue batch and hand verified jobs to V2 upsert.

    The caller owns the connection. No network request is made while holding a
    database write transaction. If the process stops after upsert but before
    marking queue rows verified, replay is safe because source_job_id is the
    SHA-256 fingerprint of the final canonical URL and upsert_jobs is idempotent.
    """
    if not 1 <= int(limit) <= 100:
        raise ValueError("limit must be between 1 and 100.")
    if not 1 <= int(max_attempts) <= 10:
        raise ValueError("max_attempts must be between 1 and 10.")
    if not 60 <= int(lease_seconds) <= 3600:
        raise ValueError("lease_seconds must be between 60 and 3600.")

    current = _utc_now(now)
    timestamp = _iso(current)
    lease_until = _iso(current + dt.timedelta(seconds=lease_seconds))

    with conn:
        rows = conn.execute(
            """
            SELECT
                e.feed_id, e.entry_id, s.feed_label, e.snippet,
                e.destination_url, e.canonical_url, e.attempt_count
            FROM google_alert_rss_entries e
            JOIN google_alert_rss_feed_state s ON s.feed_id=e.feed_id
            WHERE (
                e.processing_status IN ('queued', 'retryable_error')
                AND (e.next_attempt_at IS NULL OR e.next_attempt_at<=?)
            ) OR (
                e.processing_status='processing'
                AND (e.next_attempt_at IS NULL OR e.next_attempt_at<=?)
            )
            ORDER BY e.first_seen_at, e.feed_id, e.entry_id
            LIMIT ?
            """,
            (timestamp, timestamp, limit),
        ).fetchall()

        claimed_rows = []
        for row in rows:
            feed_id, entry_id, feed_label, snippet, destination, canonical, attempts = row
            next_attempts = int(attempts or 0) + 1
            conn.execute(
                """
                UPDATE google_alert_rss_entries
                SET processing_status='processing',
                    attempt_count=?,
                    next_attempt_at=?,
                    last_error_code=NULL,
                    last_http_status=NULL
                WHERE feed_id=? AND entry_id=?
                """,
                (next_attempts, lease_until, feed_id, entry_id),
            )
            claimed_rows.append({
                "feed_id": feed_id,
                "entry_id": entry_id,
                "feed_label": feed_label,
                "snippet": snippet or "",
                "destination_url": destination,
                "canonical_url": canonical,
                "attempt_count": next_attempts,
            })

    if not claimed_rows:
        return GoogleAlertsProcessingSummary(
            claimed=0, verified=0, inserted=0, rejected=0, blocked=0,
            needs_review=0, retryable=0, dead_letter=0,
            duplicate_entries_collapsed=0,
        )

    # Entries with the same canonical feed destination share one page fetch.
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in claimed_rows:
        key = row["canonical_url"] or row["destination_url"]
        groups.setdefault(key, []).append(row)

    verified_groups: list[tuple[list[dict[str, Any]], dict[str, Any], Any]] = []
    counts = {
        "verified": 0,
        "rejected": 0,
        "blocked": 0,
        "needs_review": 0,
        "retryable": 0,
        "dead_letter": 0,
    }
    duplicates_collapsed = sum(max(0, len(group) - 1) for group in groups.values())

    for group in groups.values():
        representative = group[0]
        keys = [(item["feed_id"], item["entry_id"]) for item in group]
        attempts = max(int(item["attempt_count"]) for item in group)
        try:
            page = fetcher(representative["destination_url"])
        except SafeFetchError as exc:
            disposition = _failure_disposition(exc)
            if disposition == "retryable_error" and attempts >= max_attempts:
                disposition = "dead_letter"
            retry_at = None
            if disposition in {"retryable_error", "dead_letter"}:
                delay = _retry_delay(exc, attempts)
                retry_at = _iso(current + dt.timedelta(seconds=delay))
            _update_group_status(
                conn,
                keys,
                status=disposition,
                error_code=exc.code,
                http_status=exc.http_status,
                next_attempt_at=retry_at,
                last_seen_at=timestamp,
            )
            count_key = "retryable" if disposition == "retryable_error" else disposition
            counts[count_key] += len(group)
            continue
        except Exception:
            _update_group_status(
                conn,
                keys,
                status="retryable_error" if attempts < max_attempts else "dead_letter",
                error_code="fetcher_unexpected_error",
                http_status=None,
                next_attempt_at=(
                    _iso(current + dt.timedelta(seconds=_retry_delay(
                        SafeFetchError("connection_failed"), attempts
                    )))
                    if attempts < max_attempts else None
                ),
                last_seen_at=timestamp,
            )
            counts["retryable" if attempts < max_attempts else "dead_letter"] += len(group)
            continue

        try:
            extracted = extractor(page.text, page.final_url, now=current)
        except Exception:
            _update_group_status(
                conn,
                keys,
                status="needs_review",
                error_code="extractor_error",
                http_status=page.http_status,
                last_seen_at=timestamp,
            )
            counts["needs_review"] += len(group)
            continue

        if extracted.status == "rejected":
            _update_group_status(
                conn,
                keys,
                status="rejected",
                error_code=extracted.reason or "posting_rejected",
                http_status=page.http_status,
                last_seen_at=timestamp,
            )
            counts["rejected"] += len(group)
            continue
        if extracted.status != "verified" or not extracted.job:
            _update_group_status(
                conn,
                keys,
                status="needs_review",
                error_code=extracted.reason or "posting_needs_review",
                http_status=page.http_status,
                last_seen_at=timestamp,
            )
            counts["needs_review"] += len(group)
            continue

        job = extracted.job
        observations = [
            {
                "feed_id": item["feed_id"],
                "entry_id": item["entry_id"],
                "feed_label": item["feed_label"],
            }
            for item in group
        ]
        source_details = {
            **(job.get("source_details") or {}),
            "google_alerts": {
                "observations": observations,
                "feed_snippet": representative["snippet"],
                "source_extraction": "schema.org/JobPosting",
            },
        }
        try:
            normalized = normalize_job_fn(
                source="google_alerts",
                source_id=str(job["source_job_id"]),
                company=str(job["company"]),
                title=str(job["title"]),
                location=str(job.get("location") or ""),
                url=str(job["url"]),
                posted_at=job.get("source_posted_at"),
                posted_precision=str(job.get("posted_precision") or "unknown"),
                description=str(job.get("description") or ""),
                description_format="plain",
                source_details=source_details,
            )
        except Exception:
            _update_group_status(
                conn,
                keys,
                status="needs_review",
                error_code="normalization_error",
                http_status=page.http_status,
                last_seen_at=timestamp,
            )
            counts["needs_review"] += len(group)
            continue

        verified_groups.append((group, normalized, page.http_status))

    inserted = 0
    if verified_groups:
        jobs = [job for _, job, _ in verified_groups]
        # upsert_jobs owns its own transaction and triggers V2's existing
        # canonical linking plus per-user preference evaluation.
        inserted = int(upsert_jobs_fn(jobs))
        for group, _, http_status in verified_groups:
            keys = [(item["feed_id"], item["entry_id"]) for item in group]
            _update_group_status(
                conn,
                keys,
                status="verified",
                error_code=None,
                http_status=http_status,
                next_attempt_at=None,
                last_seen_at=timestamp,
            )
            counts["verified"] += len(group)

    return GoogleAlertsProcessingSummary(
        claimed=len(claimed_rows),
        verified=counts["verified"],
        inserted=inserted,
        rejected=counts["rejected"],
        blocked=counts["blocked"],
        needs_review=counts["needs_review"],
        retryable=counts["retryable"],
        dead_letter=counts["dead_letter"],
        duplicate_entries_collapsed=duplicates_collapsed,
    )
