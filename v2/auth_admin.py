"""Out-of-band account provisioning for the invite-only JobBeeper beta."""
from __future__ import annotations

import argparse
import getpass
import os
import sqlite3
import sys
from pathlib import Path

from v2 import auth


def _db_path() -> Path:
    return Path(os.getenv("JOB_RADAR_DB", Path(__file__).resolve().parent / "jobs.db"))


def _admin_count(db_path: Path) -> int:
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()
    return int(row[0])


def _prompt_password() -> str:
    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Provision JobBeeper beta accounts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin_parser = subparsers.add_parser("create-admin", help="Create the first administrator account")
    admin_parser.add_argument("--email", required=True)
    user_parser = subparsers.add_parser("create-user", help="Create an ordinary beta user account")
    user_parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    db_path = _db_path()
    auth.init_auth_schema(db_path)
    try:
        admin_count = _admin_count(db_path)
        if args.command == "create-admin":
            if admin_count:
                print("An administrator account already exists; bootstrap is disabled.", file=sys.stderr)
                return 1
            role = "admin"
        else:
            if not admin_count:
                print("Create the first administrator before provisioning beta users.", file=sys.stderr)
                return 1
            role = "user"

        password = _prompt_password()
        user = auth.create_user(db_path, args.email, password, role=role)
    except (ValueError, sqlite3.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created {user['role']} account: {user['email']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
