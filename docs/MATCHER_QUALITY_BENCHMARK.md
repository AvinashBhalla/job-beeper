# Matcher quality benchmark seed

This is a small, anonymized regression seed for Job Radar V2. It is intended to catch obvious relevance regressions while the manually reviewed sample set is still small; it is **not** a statistically representative precision estimate.

## Cases

- AI Automation Engineer: positive example with concrete AI, workflow and automation responsibilities.
- QA Automation Engineer: soft-positive / adjacent automation example.
- Python Developer with business-development responsibilities and a trailing technical keyword list: review-only. The original employer listing has not yet been independently verified, so this is deliberately excluded from pass/fail precision scoring.
- Software Engineer whose feed lists Bengaluru among multiple locations but whose description explicitly says Work Location: Pune: negative.
- Conversation Quality Analyst whose description incidentally mentions forward-deployed engineers: negative.

## Run

From repository root:

```bash
python -m v2.matcher_quality_benchmark
python -m unittest v2.test_matcher_quality_benchmark -v
```

The runner reads `v2/config.dev.json`, calls the deterministic `match_details()` function, and reports each case's current score/reasons. The review-only case remains visible in output but is not counted as a scored pass/fail result.

## Baseline recorded 2026-11-06

- 5 total examples; 4 scored; 1 review-only.
- 4/4 scored examples passed; 0 failed.
- The Novisync-style mismatch still matches at score 88 and remains flagged for manual review.
- The full V2 suite passed 145 tests in 18.402 seconds inside the Python 3.12 development image with Docker networking disabled.

Do not add a broad title/description rejection rule based on one noisy feed item. Verify the original employer listing or gather independent mismatches first, then expand this benchmark with manually reviewed examples.
