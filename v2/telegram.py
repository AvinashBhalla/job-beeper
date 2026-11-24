from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sqlite3
import time
from zoneinfo import ZoneInfo
from typing import Any

import requests

from v2.radar import DB_PATH, UTC, db_lock, iso, now
from v2.sqlite_store import connect as connect_sqlite

log = logging.getLogger("job-radar.telegram")

TELEGRAM_API = "https://api.telegram.org"
SEND_TIMEOUT = 20


class TelegramDeliveryError(RuntimeError):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def credentials_available() -> bool:
    return bool(os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN")) and bool(
        os.getenv("JOB_RADAR_TELEGRAM_CHAT_ID")
    )


def _credentials() -> tuple[str, str] | None:
    token = os.getenv("JOB_RADAR_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("JOB_RADAR_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None
    return token, chat_id


IST = ZoneInfo("Asia/Kolkata")


def _format_timestamp(value: str | None, precision: str | None = None) -> str:
    if not value:
        return "Unknown"
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    local = parsed.astimezone(IST)
    if precision == "date":
        return local.strftime("%d %b %Y") + " (date only)"
    return local.strftime("%d %b %Y, %I:%M %p IST").replace(" 0", " ")


def _parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_notification(item: dict[str, Any]) -> str:
    score = int(item.get("score") or 0)
    title = item.get("title") or "Untitled role"
    company = item.get("company") or "Unknown company"
    location = item.get("location") or "Unknown location"
    source = item.get("source") or "unknown"
    url = item.get("url") or ""

    posted = item.get("source_posted_at")
    posted_precision = item.get("posted_precision")
    discovered = item.get("discovered_at")
    posted_datetime = _parse_timestamp(posted)
    discovered_datetime = _parse_timestamp(discovered)
    if (
        posted_datetime is not None
        and discovered_datetime is not None
        and posted_datetime > discovered_datetime
    ):
        # Defense in depth for any legacy row not yet cleaned by database startup.
        posted = None
        posted_precision = "unknown"
    experience_min = item.get("experience_min_years")
    experience_max = item.get("experience_max_years")

    experience = "Not captured" if item.get("has_description") == 0 else "Not stated"
    if experience_min is not None:
        experience = f"{float(experience_min):g}"
        if experience_max is None:
            experience += "+"
        elif experience_max != experience_min:
            experience += f"-{float(experience_max):g}"
        experience += " years"
    elif experience_max is not None:
        experience = f"Up to {float(experience_max):g} years"

    try:
        details = json.loads(item.get("source_details_json") or "{}")
    except (TypeError, ValueError):
        details = {}
    details = details if isinstance(details, dict) else {}
    key_skills = details.get("key_skills")
    skills = ", ".join(skill[:60] for skill in key_skills[:8] if isinstance(skill, str)) if isinstance(key_skills, list) else ""
    listing_experience = details.get("listing_experience")
    if isinstance(listing_experience, str) and listing_experience.strip():
        header_experience = re.sub(r"\s*[-–—]\s*", "-", listing_experience.strip().casefold())
        if experience_min is None and experience_max is None:
            experience = f"{listing_experience[:40]} (listing header)"
        elif header_experience != experience:
            experience += f" (listing header: {listing_experience[:40]})"

    try:
        reasons = json.loads(item.get("match_reasons_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        reasons = []

    reason_lines = []
    if isinstance(reasons, list):
        reason_lines = [f"✓ {reason[:180]}" for reason in reasons[:5] if isinstance(reason, str)]

    lines = [
        f"🚨 {score}% MATCH",
        "",
        title,
        f"Company: {company}",
        f"📍 {location}",
        f"🕐 Posted: {_format_timestamp(posted, posted_precision)}",
        f"🔎 Discovered: {_format_timestamp(discovered)}",
        f"🧾 Experience: {experience}",
        f"Key skills: {skills or 'Not captured'}",
        f"Source: {source}",
        "",
        *(reason_lines or ["Match reasons: None recorded"]),
        "",
        f"Apply → {url or 'Link unavailable'}",
    ]

    return "\n".join(lines)


def send_message(token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        f"{TELEGRAM_API}/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=SEND_TIMEOUT,
    )

    if response.status_code == 429:
        retry_after = None
        try:
            retry_after = response.json().get("parameters", {}).get("retry_after")
        except ValueError:
            pass
        detail = f"Telegram rate limited"
        if retry_after is not None:
            detail += f" for {retry_after}s"
        raise TelegramDeliveryError(detail, retryable=True)

    if response.status_code >= 500:
        raise TelegramDeliveryError(
            f"Telegram server error: HTTP {response.status_code}",
            retryable=True,
        )

    if response.status_code >= 400:
        raise TelegramDeliveryError(
            f"Telegram rejected message: HTTP {response.status_code}",
            retryable=False,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TelegramDeliveryError("Telegram returned invalid JSON", retryable=True) from exc

    if not payload.get("ok"):
        raise TelegramDeliveryError(
            f"Telegram API error: {payload.get('description', 'unknown error')}",
            retryable=False,
        )


def _next_retry(attempt_count: int) -> str:
    delay = min(3600, 30 * (2 ** max(0, attempt_count - 1)))
    return iso(now() + dt.timedelta(seconds=delay)) or iso(now())


def _claim_one(conn: sqlite3.Connection) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    timestamp = iso(now())
    row = conn.execute("""
        SELECT
            nl.canonical_opportunity_id,
            nl.candidate_job_id,
            nl.attempt_count,
            j.source,
            j.source_job_id,
            j.company,
            j.title,
            j.location,
            j.url,
            j.source_posted_at,
            j.posted_precision,
            j.discovered_at,
            j.source_details_json,
            j.description != '' AS has_description,
            e.score,
            e.reasons_json AS match_reasons_json,
            COALESCE(j.experience_min_years,e.experience_min_years) AS experience_min_years,
            COALESCE(j.experience_max_years,e.experience_max_years) AS experience_max_years
        FROM notification_ledger nl
        JOIN jobs j ON j.id = nl.candidate_job_id
        JOIN job_evaluations e ON e.job_id = nl.candidate_job_id
        WHERE e.match=1
          AND e.alertable=1
          AND (
                nl.status='queued'
                OR (
                    nl.status='failed'
                    AND nl.next_attempt_at IS NOT NULL
                    AND nl.next_attempt_at <= ?
                )
          )
        ORDER BY nl.created_at DESC
        LIMIT 1
    """, (
        timestamp,
    )).fetchone()

    if not row:
        return None

    item = dict(row)
    attempts = int(item.get("attempt_count") or 0) + 1

    updated = conn.execute("""
        UPDATE notification_ledger
        SET status='sending',
            attempt_count=?,
            claimed_at=?,
            updated_at=?,
            last_error=NULL
        WHERE canonical_opportunity_id=?
          AND status IN ('queued', 'failed')
    """, (
        attempts,
        timestamp,
        timestamp,
        int(item["canonical_opportunity_id"]),
    ))
    if updated.rowcount != 1:
        return None

    return item


def recover_stale_claims(max_age_minutes: int = 10) -> int:
    cutoff = iso(now() - dt.timedelta(minutes=max_age_minutes))
    with db_lock, connect_sqlite(DB_PATH) as conn:
        cursor = conn.execute("""
            UPDATE notification_ledger
            SET status='queued',
                updated_at=?,
                claimed_at=NULL,
                next_attempt_at=NULL,
                last_error=COALESCE(last_error, 'Recovered interrupted delivery')
            WHERE status='sending'
              AND claimed_at IS NOT NULL
              AND claimed_at < ?
        """, (iso(now()), cutoff))
        conn.commit()
        return cursor.rowcount


def deliver_queued_notifications(limit: int = 10) -> int:
    credentials = _credentials()
    if not credentials:
        return 0

    delivered = 0
    token, chat_id = credentials

    for _ in range(max(1, min(limit, 50))):
        with db_lock, connect_sqlite(DB_PATH) as conn:
            conn.execute("BEGIN IMMEDIATE")
            item = _claim_one(conn)
            conn.commit()

        if not item:
            break

        message = format_notification(item)

        try:
            send_message(token, chat_id, message)
        except Exception as exc:
            retryable = isinstance(exc, TelegramDeliveryError) and exc.retryable
            error = str(exc)
            with db_lock, connect_sqlite(DB_PATH) as conn:
                if retryable:
                    conn.execute("""
                        UPDATE notification_ledger
                        SET status='failed',
                            next_attempt_at=?,
                            updated_at=?,
                            last_error=?
                        WHERE canonical_opportunity_id=? AND status='sending'
                    """, (
                        _next_retry(int(item["attempt_count"])),
                        iso(now()),
                        error,
                        int(item["canonical_opportunity_id"]),
                    ))
                else:
                    conn.execute("""
                        UPDATE notification_ledger
                        SET status='failed',
                            next_attempt_at=NULL,
                            updated_at=?,
                            last_error=?
                        WHERE canonical_opportunity_id=? AND status='sending'
                    """, (
                        iso(now()),
                        error,
                        int(item["canonical_opportunity_id"]),
                    ))
                conn.commit()
            log.error(
                "telegram delivery failed opportunity=%s retryable=%s error=%s",
                item["canonical_opportunity_id"], retryable, error
            )
            continue

        with db_lock, connect_sqlite(DB_PATH) as conn:
            conn.execute("""
                UPDATE notification_ledger
                SET status='sent',
                    sent_at=?,
                    updated_at=?,
                    next_attempt_at=NULL,
                    last_error=NULL
                WHERE canonical_opportunity_id=? AND status='sending'
            """, (
                iso(now()),
                iso(now()),
                int(item["canonical_opportunity_id"]),
            ))
            conn.commit()

        delivered += 1

    return delivered
