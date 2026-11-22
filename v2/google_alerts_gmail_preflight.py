"""Read-only preflight for the personal Google Alerts Gmail integration.

Run inside the app container after the private environment is installed:
    python -m v2.google_alerts_gmail_preflight

This validates configuration and the configured owner account without making
OAuth, Gmail, Telegram, or database writes. It never prints secret values.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from v2 import google_alerts_gmail


class PreflightError(RuntimeError):
    pass


def check_owner_account(db_path: Path, owner_user_id: int) -> None:
    """Require the configured owner to be an active administrator account."""
    if not db_path.is_file():
        raise PreflightError("configured_database_not_found")
    uri = db_path.resolve().as_uri() + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=5) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            row = conn.execute(
                "SELECT id, role, status FROM users WHERE id=?",
                (int(owner_user_id),),
            ).fetchone()
    except sqlite3.Error:
        raise PreflightError("owner_database_check_failed") from None
    if row is None:
        raise PreflightError("configured_owner_account_not_found")
    if str(row["role"]) != "admin" or str(row["status"]) != "active":
        raise PreflightError("configured_owner_must_be_active_admin")


def run_preflight(db_path: Path, *, require_live_enabled: bool = False) -> list[str]:
    config = google_alerts_gmail.load_config()
    if config is None:
        raise PreflightError("gmail_configuration_missing")
    if config.sync_mode != "polling":
        raise PreflightError("personal_setup_requires_polling_mode")
    if config.pubsub_topic or config.pubsub_subscription:
        raise PreflightError("polling_mode_must_not_configure_pubsub")
    if not config.redirect_uri.startswith("http://localhost:"):
        raise PreflightError("personal_setup_requires_localhost_callback")
    check_owner_account(db_path, config.owner_user_id)
    if require_live_enabled and not config.live_access_enabled:
        raise PreflightError("gmail_live_access_switch_is_disabled")

    state = "enabled" if config.live_access_enabled else "disabled (safe default)"
    return [
        "PASS: Gmail OAuth settings are present and syntactically valid.",
        "PASS: callback is a localhost URI using the Gmail integration route.",
        f"PASS: polling mode is configured at {config.poll_interval_seconds} seconds; Pub/Sub is not configured.",
        "PASS: configured owner ID maps to an active administrator account.",
        f"INFO: Gmail live-access switch is {state}.",
        "PASS: no credentials, OAuth grants, Gmail requests, Telegram sends, or database writes were performed.",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", default=os.environ.get("JOB_RADAR_DB", ""),
        help="Application SQLite database path (defaults to JOB_RADAR_DB).",
    )
    parser.add_argument(
        "--require-live-enabled", action="store_true",
        help="Fail unless JOB_RADAR_GMAIL_ENABLE_LIVE_ACCESS is true.",
    )
    args = parser.parse_args(argv)
    if not args.db:
        print("FAIL: JOB_RADAR_DB is not configured.", file=sys.stderr)
        return 2
    try:
        lines = run_preflight(Path(args.db), require_live_enabled=args.require_live_enabled)
    except PreflightError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    except google_alerts_gmail.GoogleAlertsGmailError as exc:
        print(f"FAIL: {exc.code}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
