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

from v2 import board_discovery, serp_board_discovery as serp

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
            "keyword": f"{ROLE_SEEDS[(index // len(providers)) % len(ROLE_SEEDS)]} India",
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



def summarize_benchmark(path: str) -> dict[str, Any]:
    """Summarize paired provider results, dedupe boards, and optional manual labels.

    Reviewers may add candidate.manual_verdict = "verified" or
    "false_positive" to JSONL records after checking employer ownership.
    """
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}.") from exc
            if not isinstance(item, dict):
                raise ValueError(f"Benchmark line {line_number} must be a JSON object.")
            rows.append(item)

    identities_by_engine: dict[str, dict[tuple[str, str, str], set[str]]] = {
        "dataforseo_live": {},
        "serper": {},
    }
    appearances = {"dataforseo_live": 0, "serper": 0}
    organic_queries = {"dataforseo_live": 0, "serper": 0}
    candidate_queries = {"dataforseo_live": 0, "serper": 0}
    engine_rows = {"dataforseo_live": [], "serper": []}
    verdicts: dict[tuple[str, str, str], set[str]] = {}

    for row in rows:
        engine = row.get("engine")
        if engine not in engine_rows:
            continue
        engine_rows[engine].append(row)
        if row.get("error_type"):
            continue
        if int(row.get("organic_results", 0) or 0) > 0:
            organic_queries[engine] += 1
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            continue
        if candidates:
            candidate_queries[engine] += 1
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            detected = board_discovery.detect_ats_board(str(candidate.get("board_url") or ""))
            if not detected:
                continue
            key = (
                str(detected.get("provider") or ""),
                str(detected.get("host") or "").casefold(),
                str(detected.get("board_key") or "").casefold(),
            )
            if not all(key):
                continue
            appearances[engine] += 1
            identities_by_engine[engine].setdefault(key, set()).add(str(row.get("query") or ""))
            verdict = str(candidate.get("manual_verdict") or "").strip().casefold()
            if verdict in {"verified", "false_positive"}:
                verdicts.setdefault(key, set()).add(verdict)

    summaries: dict[str, Any] = {}
    for engine in ("dataforseo_live", "serper"):
        unique = identities_by_engine[engine]
        request_count = len(engine_rows[engine])
        successes = sum(1 for row in engine_rows[engine] if not row.get("error_type"))
        unique_count = len(unique)
        reviewed_verified = sum(1 for key in unique if verdicts.get(key) == {"verified"})
        reviewed_false = sum(1 for key in unique if verdicts.get(key) == {"false_positive"})
        conflicts = sum(1 for key in unique if len(verdicts.get(key, set())) > 1)
        reviewed = reviewed_verified + reviewed_false
        actual_costs = [
            float(row["actual_cost_usd"])
            for row in engine_rows[engine]
            if isinstance(row.get("actual_cost_usd"), (int, float))
        ]
        summaries[engine] = {
            "requests_attempted": request_count,
            "successful_requests": successes,
            "failed_requests": request_count - successes,
            "queries_with_organic_results": organic_queries[engine],
            "queries_with_candidates": candidate_queries[engine],
            "candidate_appearances": appearances[engine],
            "unique_boards": unique_count,
            "duplicate_appearances": appearances[engine] - unique_count,
            "manually_verified_unique_boards": reviewed_verified,
            "manually_false_positive_unique_boards": reviewed_false,
            "unreviewed_unique_boards": unique_count - reviewed,
            "manual_label_conflicts": conflicts,
            "organic_query_coverage_pct": round(100 * organic_queries[engine] / request_count, 2) if request_count else 0,
            "candidate_query_coverage_pct": round(100 * candidate_queries[engine] / request_count, 2) if request_count else 0,
            "unique_boards_per_1000_requests": round(1000 * unique_count / request_count, 2) if request_count else 0,
            "verified_boards_per_1000_requests": round(1000 * reviewed_verified / request_count, 2) if request_count else 0,
            "dataforseo_actual_cost_usd": round(sum(actual_costs), 6) if actual_costs else None,
            "serper_credits_estimated": successes if engine == "serper" else None,
        }

    dataforseo_keys = set(identities_by_engine["dataforseo_live"])
    serper_keys = set(identities_by_engine["serper"])
    shared = dataforseo_keys & serper_keys
    union = dataforseo_keys | serper_keys
    return {
        "rows_read": len(rows),
        "expected_query_pairs": BENCHMARK_QUERY_COUNT,
        "matched_pairs_complete": all(len(engine_rows[name]) == BENCHMARK_QUERY_COUNT for name in engine_rows),
        "engines": summaries,
        "cross_engine": {
            "unique_board_union": len(union),
            "shared_unique_boards": len(shared),
            "dataforseo_only_unique_boards": len(dataforseo_keys - serper_keys),
            "serper_only_unique_boards": len(serper_keys - dataforseo_keys),
        },
        "manual_verdicts": {
            "verified_unique_boards": sum(1 for value in verdicts.values() if value == {"verified"}),
            "false_positive_unique_boards": sum(1 for value in verdicts.values() if value == {"false_positive"}),
            "conflicting_unique_boards": sum(1 for value in verdicts.values() if len(value) > 1),
        },
        "interpretation": "Search results are candidates, not employer ownership proof. Manually label a candidate only after checking the official employer careers page and public ATS board.",
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the opt-in 50-query SERP provider benchmark")
    parser.add_argument("--confirm-paid", action="store_true")
    parser.add_argument("--output", default="data/serp-provider-benchmark.jsonl")
    parser.add_argument("--summarize", help="Summarize an existing JSONL benchmark without making requests")
    args = parser.parse_args(argv)
    if args.summarize:
        print(json.dumps(summarize_benchmark(args.summarize), indent=2, sort_keys=True))
        return 0
    try:
        result = run_benchmark(args.output, confirm_paid=args.confirm_paid)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
