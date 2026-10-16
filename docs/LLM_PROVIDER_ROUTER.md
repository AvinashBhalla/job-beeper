# Multi-provider LLM router (Job Radar V2)

## Purpose and current safety defaults

The optional router allows shadow job-description extraction to try configured providers in order: Groq, Gemini, OpenRouter, and NVIDIA. The default order is `groq,gemini,openrouter,nvidia`. It makes one provider request at a time and falls back after request errors, rate limits, malformed JSON, or output that fails the shared extraction validator. It does not send Telegram notifications.

The router is disabled by default (`LLM_ROUTER_ENABLED=false`). Existing Gemini-only behavior is preserved until explicitly enabled. When the router is enabled, its extraction results remain shadow-only by default: `LLM_ROUTER_MATCHER_ENABLED=false` prevents routed results from entering hard-match evaluation even if the existing `GEMINI_MATCHER_ENABLED` flag is true. Do not enable routed matcher use until a reviewed evaluation demonstrates quality.

## VM-local environment variables

Add these to the VM-local environment file used by the development Compose project (currently `/home/ubuntu/job-beeper-dev/.env`). Never commit this file or paste its secrets into chat. Keep permissions restricted, for example `chmod 600 /home/ubuntu/job-beeper-dev/.env`.

```dotenv
LLM_ROUTER_ENABLED=true
LLM_ROUTER_MATCHER_ENABLED=false
LLM_PROVIDER_ORDER=groq,gemini,openrouter,nvidia
LLM_MAX_JOBS_PER_RUN=3
LLM_MAX_JOBS_PER_DAY=20

# Set a model ID that is available to your own provider account.
GROQ_API_KEY=
GROQ_MODEL=

# Existing Gemini settings remain in use:
# GEMINI_API_KEY=<keep the existing value in the VM file>
# GEMINI_MODEL=gemini-3.5-flash-lite

OPENROUTER_API_KEY=
OPENROUTER_MODEL=

NVIDIA_API_KEY=
NVIDIA_MODEL=
```

Do not paste actual key values into shell commands, commit them, print them, or put them in diagnostics. Edit the VM-local file interactively and save it with restricted permissions. Model IDs are account/provider-specific and must be verified in each provider's console or model catalogue; the router intentionally skips any non-Gemini provider missing either a key or model ID. Gemini uses `GEMINI_MODEL`, defaulting to `gemini-3.5-flash-lite` if blank.

## Provider endpoints and request format

- Groq: OpenAI-compatible chat-completions endpoint at `https://api.groq.com/openai/v1/chat/completions`.
- OpenRouter: OpenAI-compatible endpoint at `https://openrouter.ai/api/v1/chat/completions`.
- NVIDIA: NVIDIA NIM chat-completions endpoint at `https://integrate.api.nvidia.com/v1/chat/completions`.
- Gemini: native `generateContent` endpoint with structured JSON response schema.

The OpenAI-compatible adapters request JSON-object output. Every provider response then goes through the existing strict extraction validator, including numeric range checks, experience type/scope checks, evidence quote verification, skill cleanup, and confidence bounds. A provider's self-reported confidence is not a guarantee of correctness.

## Budgets, cache, and failure behavior

- `LLM_MAX_JOBS_PER_RUN` and `LLM_MAX_JOBS_PER_DAY` bound jobs processed by the router. They are not per-provider token or request quotas; each job may attempt more than one provider if fallbacks are needed.
- Provider-side rate limits and billing still apply. Check each account's limits and pricing before enabling it. Multiple keys do not guarantee extra free capacity; OpenRouter is a model gateway rather than a separate guaranteed quota pool.
- Cache identity includes the ordered configured provider/model list, but never API keys. A provider/model configuration change therefore uses a distinct cache identity.
- The existing SQLite cache table is reused; this change adds no schema migration. Daily job budget counting is scoped to the active cache identity.
- Logs include only provider names and sanitized error categories. They must never include API keys, full job descriptions, raw model responses, or evidence text.
- If no configured provider has both a key and a model, the router skips extraction. If every configured provider fails, the job is recorded as an error through the existing cache flow.

## Pull, test, and enable procedure

1. Fetch and fast-forward only the development checkout on `v2-live-radar`; do not reset or clean the working tree. Preserve VM-local `v2/config.json`, `.venv/`, and the Docker named volume.
2. Run the focused router and extractor tests, then the full test suite. No live provider API calls are needed for these tests.
3. Add provider keys and model IDs to the VM-local environment file, then verify Compose configuration using only allowlisted presence/boolean/model fields. Never print full environment values.
4. Rebuild/recreate only `job-radar-dev` with the development Compose file after tests pass. Do not touch the separate production-ish Compose project.
5. Confirm the container has expected provider names/model IDs, no Telegram credentials, and the same named volume. Review only aggregate shadow status; do not run job-processing endpoints solely to force calls.
6. Keep `LLM_ROUTER_MATCHER_ENABLED=false` and Telegram notifications disabled while reviewing output quality, provider errors, request counts, latency, and cost. Enable matcher use only as a separate, explicit decision after evidence-based validation.

## Limitations

The repository unit tests use mocked HTTP responses and do not prove that a live API key, chosen model ID, account quota, provider availability, pricing, or response quality is valid. A live smoke test should be explicitly approved and budgeted after the mocked suite passes. No production cutover is implied by this feature.
