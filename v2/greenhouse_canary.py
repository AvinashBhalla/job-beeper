"""Run a read-only, one-board Greenhouse two-poll canary.

This utility calls the public Greenhouse board endpoint twice and compares the
returned source IDs. It does not initialize/write the radar database, run
matching, send notifications, or change source_enabled configuration.
Run from the repository root with: python -m v2.greenhouse_canary
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from typing import Any

from v2 import radar


def snapshot(board_token: str, company: str) -> list[dict[str, Any]]:
    """Fetch one board through the production collector's normalization path."""
    return radar.greenhouse_collect({
        "greenhouse_boards": [{"token": board_token, "company": company}]
    })


def job_ids(jobs: list[dict[str, Any]]) -> set[str]:
    """Return non-empty normalized source IDs from a collector snapshot."""
    return {
        str(job["source_job_id"])
        for job in jobs
        if job.get("source_job_id") not in (None, "")
    }


def build_report(
    first: list[dict[str, Any]], second: list[dict[str, Any]]
) -> dict[str, Any]:
    """Summarize two snapshots without persisting job data."""
    first_ids = job_ids(first)
    second_ids = job_ids(second)
    second_with_published_time = sum(
        1 for job in second if job.get("source_posted_at") not in (None, "")
    )
    return {
        "status": "completed",
        "source": "greenhouse",
        "polls": 2,
        "first_poll_jobs": len(first),
        "second_poll_jobs": len(second),
        "first_poll_unique_ids": len(first_ids),
        "second_poll_unique_ids": len(second_ids),
        "stable_ids": len(first_ids & second_ids),
        "new_ids_on_second_poll": len(second_ids - first_ids),
        "missing_ids_on_second_poll": len(first_ids - second_ids),
        "second_poll_published_timestamp_coverage": {
            "with_timestamp": second_with_published_time,
            "unknown_timestamp": len(second) - second_with_published_time,
        },
        "database_writes": 0,
        "matching_executed": False,
        "notifications_sent": False,
    }


def run_canary(
    board_token: str,
    company: str,
    interval_seconds: int = 900,
    collect: Callable[[str, str], list[dict[str, Any]]] = snapshot,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Run two snapshots at least one minute apart; never write application state."""
    token = board_token.strip()
    label = company.strip()
    if not token or not label:
        raise ValueError("A non-empty board token and company label are required.")
    if interval_seconds < 60:
        raise ValueError("interval_seconds must be at least 60 seconds.")

    first = collect(token, label)
    sleep(interval_seconds)
    second = collect(token, label)
    return build_report(first, second)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Greenhouse canary: fetch one public board twice and "
            "report ID stability, new/removed IDs, and timestamp coverage."
        )
    )
    parser.add_argument("--board-token", required=True, help="Public Greenhouse board slug")
    parser.add_argument("--company", required=True, help="Human-readable company label")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=900,
        help="Delay between polls; minimum 60, default 900 (15 minutes)",
    )
    args = parser.parse_args(argv)

    try:
        report = run_canary(args.board_token, args.company, args.interval_seconds)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    except Exception as exc:
        # Do not print request payloads, job descriptions, or credentials.
        print(json.dumps({
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": "A poll failed; inspect application logs for the board-level error.",
        }, indent=2))
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
