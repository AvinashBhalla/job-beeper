"""Run the small, anonymized matcher quality seed against the dev profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from v2.radar import match_details


HERE = Path(__file__).resolve().parent
FIXTURE_PATH = HERE / "fixtures" / "matcher_quality_benchmark.json"
PROFILE_PATH = HERE / "config.dev.json"


def run_benchmark() -> dict[str, Any]:
    """Evaluate deterministic cases; keep unresolved review cases out of scores."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    config = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []

    for case in fixture["cases"]:
        job = {
            "source": case["source"],
            "title": case["title"],
            "location": case["location"],
            "description": case["description"],
        }
        actual = match_details(job, config)
        label = case["review_label"]
        expected = case.get("expected_match")
        review_required = label == "review"
        passed = None if review_required else bool(actual["match"]) == bool(expected)
        results.append({
            "case_id": case["case_id"],
            "review_label": label,
            "review_required": review_required,
            "expected_match": expected,
            "actual_match": bool(actual["match"]),
            "score": int(actual.get("score") or 0),
            "reasons": list(actual.get("reasons") or []),
            "status": "review_required" if review_required else ("pass" if passed else "fail"),
        })

    scored = [item for item in results if not item["review_required"]]
    summary = {
        "case_count": len(results),
        "scored_case_count": len(scored),
        "review_case_count": len(results) - len(scored),
        "passed": sum(item["status"] == "pass" for item in scored),
        "failed": sum(item["status"] == "fail" for item in scored),
        "review_cases_currently_matching": sum(
            item["review_required"] and item["actual_match"] for item in results
        ),
    }
    return {
        "fixture_version": fixture["version"],
        "annotation_status": fixture["annotation_status"],
        "profile_config": fixture["profile_config"],
        "summary": summary,
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2, ensure_ascii=False))
