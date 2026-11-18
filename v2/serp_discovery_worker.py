"""Operator-invoked SERP discovery worker.

No scheduler is installed by this module. The persistent coordinator remains
disabled until an operator explicitly configures a positive monthly cap.
Credentials are read from environment variables and never printed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from v2 import serp_board_discovery as serp
from v2 import serp_discovery_coordinator as coordinator


def _db_path() -> str:
    return os.getenv("JOB_RADAR_DB", str(Path(__file__).with_name("jobs.db")))


def run_once(db_path: str | None = None) -> dict[str, Any]:
    """Run a single due cycle; disabled/missing-cap state makes zero requests."""
    state = coordinator.status(db_path or _db_path())["control"]
    if not state.get("enabled"):
        return coordinator.run_once(
            db_path or _db_path(),
            searcher=lambda _provider: {},
            importer=lambda _payload: {},
        )
    if not os.getenv("DATAFORSEO_LOGIN") or not os.getenv("DATAFORSEO_PASSWORD"):
        raise ValueError("SERP discovery is enabled but DataForSEO credentials are missing.")
    from v2 import radar

    def searcher(provider: str) -> dict[str, Any]:
        return serp.discover_provider_candidates(
            provider,
            engine="dataforseo_live",
            username=os.getenv("DATAFORSEO_LOGIN"),
            password=os.getenv("DATAFORSEO_PASSWORD"),
        )

    def importer(payload: dict[str, Any]) -> dict[str, Any]:
        # Reuse the guarded candidate-only importer. This creates no employers,
        # board-registry entries, schedules, job rows or notifications.
        return radar.import_global_ats_candidates(payload)

    return coordinator.run_once(
        db_path or _db_path(), searcher=searcher, importer=importer,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Disabled-by-default ATS SERP discovery worker")
    parser.add_argument("command", choices=("status", "enable", "disable", "run-once"))
    parser.add_argument("--monthly-cap-usd", type=float)
    args = parser.parse_args(argv)
    db_path = _db_path()

    if args.command == "status":
        print(json.dumps(coordinator.status(db_path), indent=2, sort_keys=True))
        return 0
    if args.command == "enable":
        state = coordinator.configure(
            db_path, enabled=True, monthly_cap_usd=args.monthly_cap_usd,
        )
        print(json.dumps({"enabled": bool(state["enabled"]), "monthly_cap_usd": state["monthly_cap_usd"]}))
        return 0
    if args.command == "disable":
        state = coordinator.configure(
            db_path, enabled=False, monthly_cap_usd=args.monthly_cap_usd,
        )
        print(json.dumps({"enabled": bool(state["enabled"]), "monthly_cap_usd": state["monthly_cap_usd"]}))
        return 0
    result = run_once(db_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("outcome") in {"success", "disabled", "throttled", "leased", "budget_exhausted", "no_requests"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
