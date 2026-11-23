"""Report the live discovery and delivery pilot from an existing database."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp.astimezone(timezone.utc) if stamp.tzinfo is not None else None


def elapsed(start: str | None, finish: str | None) -> float | None:
    start_at, finish_at = parse_timestamp(start), parse_timestamp(finish)
    if start_at is None or finish_at is None or finish_at < start_at:
        return None
    return (finish_at - start_at).total_seconds()


def summarize(samples: list[float | None], target_seconds: int) -> dict:
    values = sorted(sample for sample in samples if sample is not None)
    count = len(values)
    return {
        "samples": count,
        "p50_seconds": round(values[math.ceil(count * 0.50) - 1], 3) if count else None,
        "p95_seconds": round(values[math.ceil(count * 0.95) - 1], 3) if count else None,
        "within_target": sum(value <= target_seconds for value in values),
        "target_seconds": target_seconds,
    }


def build_report(db_path: Path, source: str, since: datetime) -> dict:
    """Use public, post-baseline jobs and their per-user alert ledger entries."""
    if since.utcoffset() is None:
        raise ValueError("The pilot cutoff must include a timezone.")
    window_start = since.astimezone(timezone.utc).isoformat()
    cohort = """j.source=? AND julianday(j.discovered_at)>=julianday(?)
                AND COALESCE(j.source_initial_baseline,0)=0
                AND j.source_owner_user_id IS NULL"""
    with closing(sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        conn.execute("BEGIN")
        jobs = conn.execute(f"""
            SELECT j.source_posted_at,j.posted_precision,j.discovered_at
            FROM jobs j WHERE {cohort}
        """, (source, window_start)).fetchall()
        deliveries = conn.execute(f"""
            SELECT j.discovered_at,l.created_at,l.sent_at,l.status
            FROM user_notification_ledger l JOIN jobs j ON j.id=l.candidate_job_id
            WHERE {cohort} AND COALESCE(l.backlog_override,0)=0
        """, (source, window_start)).fetchall()
        runs = conn.execute("""
            SELECT COALESCE(outcome,'unknown'),COUNT(*),COALESCE(SUM(http_429),0)
            FROM source_runs WHERE source=? AND julianday(started_at)>=julianday(?)
            GROUP BY COALESCE(outcome,'unknown')
        """, (source, window_start)).fetchall()

    publication_lag = [
        elapsed(posted, found) for posted, precision, found in jobs if precision == "minute"
    ]
    accepted = [elapsed(found, sent) for found, _, sent, status in deliveries if status == "sent"]
    return {
        "source": source,
        "since_utc": window_start,
        "source_runs": {outcome: count for outcome, count, _ in runs},
        "http_429_responses": sum(count for _, _, count in runs),
        "new_public_jobs": len(jobs),
        "jobs_without_measurable_publication_lag": len(jobs) - sum(lag is not None for lag in publication_lag),
        "published_to_discovered": summarize(publication_lag, 180),
        "alerts_by_status": dict(sorted(Counter(row[3] for row in deliveries).items())),
        "discovered_to_alert_queued": summarize(
            [elapsed(found, queued) for found, queued, _, _ in deliveries], 30
        ),
        "discovered_to_telegram_accepted": summarize(accepted, 30),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="Existing JobBeeper SQLite database")
    parser.add_argument("--source", default="greenhouse", help="Collector source to report")
    parser.add_argument("--since", required=True, help="ISO 8601 pilot cutoff, including timezone")
    args = parser.parse_args()
    since = parse_timestamp(args.since)
    if since is None:
        parser.error("--since must be an ISO 8601 timestamp with a timezone")
    try:
        report = build_report(args.db, args.source, since)
    except (OSError, sqlite3.Error) as exc:
        parser.exit(1, f"Unable to read the pilot database: {exc}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
