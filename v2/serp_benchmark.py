"""Fixed, opt-in 50-pair DataForSEO vs Serper benchmark.

The plan contains exactly 50 matched (ATS provider, keyword) pairs. Running it
makes 100 paid/API requests (50 per vendor); it never imports candidates into
the application database. Results are written as JSONL for reproducibility.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path
from typing import Any

from v2 import serp_board_discovery as serp

BENCHMARK_QUERY_COUNT = 50
ROLE_SEEDS = (
    "software engineer", "software developer", "backend engineer",
    "frontend engineer", "full stack engineer", "python developer",
    "automation engineer", "QA engineer", "DevOps engineer",
    "site reliability engineer",
)


def build_benchmark_plan() -> list[dict[str, str]]:
    providers = list(serp.SERP_PROVIDER_ORDER)
    plan = []
    for index in range(BENCHMARK_QUERY_COUNT):
        plan.append({
            "provider": providers[index % len(providers)],
            "keyword": f"{ROLE_SEEDS[index % len(ROLE_SEEDS)]} India",
        })
    return plan


def _result_row(engine: str, provider: str, keyword: str, result: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    candidates = result.get("candidates", [])
    return {
        "engine": engine,
        "provider": provider,
        "keyword": keyword,
        "query": result.get("query"),
        "latency_ms": round(elapsed_ms, 2),
        "organic_results": int(result.get("organic_results", 0) or 0),
        "candidate_count": len(candidates) if isinstance(candidates, list) else 0,
        "actual_cost_usd": result.get("actual_cost_usd"),
        "candidates": candidates if isinstance(candidates, list) else [],
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "error_type": None,
    }


def run_benchmark(
    output_path: str,
    *,
    confirm_paid: bool = False,
    requester: Any = None,
) -> dict[str, Any]:
    if not confirm_paid:
        raise ValueError("Pass --confirm-paid to authorize the 100-request benchmark.")
    if not os.getenv("DATAFORSEO_LOGIN") or not os.getenv("DATAFORSEO_PASSWORD"):
        raise ValueError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required.")
    if not os.getenv("SERPER_API_KEY"):
        raise ValueError("SERPER_API_KEY is required.")
    plan = build_benchmark_plan()
    if len(plan) != BENCHMARK_QUERY_COUNT:
        raise RuntimeError("Benchmark plan must contain exactly 50 matched queries.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    totals = {"requests_attempted": 0, "successes": 0, "failures": 0}
    with output.open("w", encoding="utf-8") as handle:
        for item in plan:
            provider, keyword = item["provider"], item["keyword"]
            for engine in ("dataforseo_live", "serper"):
                started = time.monotonic()
                try:
                    kwargs: dict[str, Any] = {
                        "provider": provider,
                        "engine": engine,
                        "keyword": keyword,
                        "role_terms": (keyword.removesuffix(" India"),),
                        "username": os.getenv("DATAFORSEO_LOGIN"),
                        "password": os.getenv("DATAFORSEO_PASSWORD"),
                        "api_key": os.getenv("SERPER_API_KEY"),
                    }
                    if requester is not None:
                        kwargs["requester"] = requester
                    result = serp.discover_provider_candidates(**kwargs)
                    row = _result_row(engine, provider, keyword, result, (time.monotonic() - started) * 1000)
                    totals["successes"] += 1
                except Exception as exc:
                    row = {
                        "engine": engine, "provider": provider, "keyword": keyword,
                        "latency_ms": round((time.monotonic() - started) * 1000, 2),
                        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "error_type": type(exc).__name__,
                    }
                    totals["failures"] += 1
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                totals["requests_attempted"] += 1
    totals["query_pairs"] = len(plan)
    totals["output_path"] = str(output)
    return totals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the opt-in 50-query SERP provider benchmark")
    parser.add_argument("--confirm-paid", action="store_true")
    parser.add_argument("--output", default="data/serp-provider-benchmark.jsonl")
    args = parser.parse_args(argv)
    try:
        result = run_benchmark(args.output, confirm_paid=args.confirm_paid)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
