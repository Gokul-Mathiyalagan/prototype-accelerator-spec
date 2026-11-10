# Handoff

- **Updated:** 2026-11-10 19:53 IST
- **Agent:** claude-code
- **Active task:** T-004 Azure OpenAI gateway, redaction and audit log
- **Task status:** review
- **Branch:** task/T-004-azure-gateway
- **Last commit:** 98ae2ac T-004: add Azure OpenAI gateway, redaction, audit and FakeGateway

## Summary

The gateway is built and tested offline. It uses API key auth per ADR-0008, redacts every outbound message, audits every call without content, and enforces budgets. The one live test (a tool-calling round trip against Azure) is written but hasn't run, because no `.env` exists yet. `make check` passes with 253 tests.

## Acceptance criteria

- [x] Gateway uses openai.AzureOpenAI with API key auth (ADR-0008), reading the four variables with their defaults: `gateway/azure.py` and `gateway/config.py`. `test_gateway_azure.py` checks the URL, `api-key` header and api-version through the real SDK over `httpx.MockTransport`.
- [x] A missing endpoint or key raises a typed config error naming the variable; an api_key in accel.toml is rejected; the key never appears in logs, audit lines or error messages: `test_gateway_config.py`. The gateway also redacts the key itself if it shows up in content.
- [x] .env.example lists the four variables with placeholder values only: `test_env_example_lists_the_four_variables_with_placeholders`.
- [x] Supports chat completions with tool calling and structured output (JSON Schema from a contract model), reasoning effort, and streaming off by default: `Gateway.chat` and `Gateway.structured`. `stream=False` is always sent.
- [x] Redaction runs on every outbound message: `accel_core/redaction/`, with 12 rule kinds and typed placeholders such as `[REDACTED_EMAIL_1]` (`test_redaction.py`, plus the first test in `test_gateway.py`).
- [x] Per-call and per-run budgets (tokens, cost) raise BudgetExceeded: `gateway/budget.py`.
- [x] Every call writes an audit line, never the content: `accel_core/audit/`, to `$ACCEL_HOME/audit/model-calls.jsonl`.
- [x] FakeGateway in accel_core.testing replays recorded responses for unit tests: `accel_core/testing/gateway.py`, with a recording in `tests/fixtures/gateway/tool-round-trip.json`.
- [ ] A live_azure test makes one tool-calling round trip against gpt-6.1-sol: written in `tests/core/test_gateway_live.py`, **not yet run**.

## State of the active task

- `accel_core/errors.py` (new): `AccelError` plus `ConfigError` (exit 3), `BudgetExceeded` (1), `ExternalCallError` (4) and `StructuredOutputError` (4), each with a stable `code`.
- `accel_core/gateway/`: `config.py` resolves settings (precedence: environment, `.env`, `accel.toml`, defaults), `types.py` holds the provider-neutral types and the `Transport` protocol, `azure.py` is the only module that imports `openai`, and `budget.py` and `gateway.py` are the rest.
- `openai>=2,<3` was added to `accel-core` (2.54.0 is locked).

## Next step

1. Gokul copies `.env.example` to `.env`, fills in the endpoint, key and deployment, then runs `uv run make test-live NEEDS=azure`. Expect 1 passed (about 2 calls and under 4,000 tokens).
2. If it passes, Gokul merges `task/T-004-azure-gateway` and sets T-004 `done`. If the API version rejects `reasoning_effort` or `tool_choice`, raise `OPENAI_API_VERSION` in `.env`; nothing else should need to change.

## How to verify

```bash
uv run make check                        # 253 passed, 1 skipped (symlink test on Windows), 1 deselected (live)
uv run make test-live NEEDS=azure        # needs .env; fails with "AZURE_OPENAI_ENDPOINT is not set" without it
```

## Decisions and assumptions

- Structured output sends `json_schema` with `strict: false`, because Azure's strict mode needs every field required and contract models have defaults. The gateway validates the reply against the model and raises `StructuredOutputError` naming the failing fields.
- Budgets: a per-call or run token limit also caps `max_completion_tokens`. The overrun check runs after the call, which is still audited (`outcome: budget_exceeded`). A cost budget without prices raises `ConfigError` before any call.
- The employee-ID pattern defaults to `EMP-1234`-style IDs. A real format can be passed in through `Redactor(rules=...)`.
- Each redaction session gives the same value the same placeholder, so the model can still see which values repeat.

## Spec changes

- spec/01 config table: added the token-price row (`accel.toml` `input_usd_per_mtok` and `output_usd_per_mtok`), which cost budgets need. `accel.toml.example` matches.
- ADR-0008 (accepted earlier this session, on `main`) covers the auth change.

## Open questions for Gokul

- What format do employee IDs use? The default rule only catches `EMP`-prefixed IDs.
- What are the per-million-token prices for `gpt-6.1-sol`? Cost budgets can't be enforced until they're set in `accel.toml`.

## Watch out

- `main` has one unpushed commit (`a6d3562`, ADR-0008), and this branch is built on it.
- Ruff sorts `accel_core` imports in `tests/` as third-party (no blank line after `pytest`). That's the existing config, so don't fight it.
