"""The gateway: redaction on every call, tools, structured output, budgets and audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from accel_core.audit import FileAuditLog, ModelCallRecord, default_audit_dir
from accel_core.contracts import Playbook
from accel_core.errors import (
    AccelError,
    BudgetExceeded,
    ConfigError,
    ExternalCallError,
    StructuredOutputError,
)
from accel_core.gateway import Budget, ChatResult, Gateway, Pricing, RunBudget, ToolCall, Usage
from accel_core.testing import FakeGateway, fake_settings

ROOT = Path(__file__).resolve().parents[2]
RECORDING = ROOT / "tests" / "fixtures" / "gateway" / "tool-round-trip.json"
ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two integers.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
}
PRICING = Pricing(input_usd_per_mtok=10.0, output_usd_per_mtok=30.0)


def _reply(text: str = "ok", prompt: int = 100, completion: int = 20) -> ChatResult:
    return ChatResult(
        content=text,
        finish_reason="stop",
        usage=Usage(prompt_tokens=prompt, completion_tokens=completion),
    )


def test_every_outbound_message_is_redacted_and_the_audit_has_no_content() -> None:
    gateway = FakeGateway([_reply("MODEL-REPLY-TEXT")])
    messages = [
        {"role": "system", "content": "You review code."},
        {"role": "user", "content": "Ask jane@example.com; key fake-key-for-tests-only"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": '{"password": "hunter2-secret"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "Phone +1 415-555-0123"},
    ]
    gateway.chat(messages, caller="accel_skills.writer", purpose="draft sso-auth")

    sent = json.dumps(gateway.requests[0].messages)
    for secret in ("jane@example.com", "fake-key-for-tests-only", "hunter2-secret", "555-0123"):
        assert secret not in sent
    assert "[REDACTED_EMAIL_1]" in sent and "[REDACTED_AZURE_OPENAI_KEY_1]" in sent
    assert gateway.requests[0].messages[3]["tool_call_id"] == "call_1"

    (record,) = gateway.audit_records
    assert record.redactions == {"azure_openai_key": 1, "email": 1, "phone": 1, "secret": 1}
    assert (record.caller, record.purpose, record.outcome) == (
        "accel_skills.writer",
        "draft sso-auth",
        "ok",
    )
    audited = record.model_dump_json()
    for content in ("You review code", "[REDACTED", "jane", "lookup", "MODEL-REPLY-TEXT"):
        assert content not in audited


def test_tool_calling_round_trip_from_a_recording() -> None:
    gateway = FakeGateway(RECORDING)
    messages = [{"role": "user", "content": "What is 2 + 3? Use the add tool."}]
    first = gateway.chat(
        messages, caller="test", purpose="tools", tools=[ADD_TOOL], tool_choice="required"
    )
    assert first.tool_calls == [ToolCall(id="call_1", name="add", arguments='{"a": 2, "b": 3}')]
    assert gateway.requests[0].tools == [ADD_TOOL]
    assert gateway.requests[0].tool_choice == "required"

    arguments = json.loads(first.tool_calls[0].arguments)
    messages += [
        first.assistant_message(),
        {"role": "tool", "tool_call_id": "call_1", "content": str(arguments["a"] + arguments["b"])},
    ]
    second = gateway.chat(messages, caller="test", purpose="tools", tools=[ADD_TOOL])
    assert second.content == "2 + 3 = 5"
    assert gateway.requests[1].messages[1]["tool_calls"][0]["function"]["name"] == "add"
    assert [r.prompt_tokens for r in gateway.audit_records] == [120, 150]


def test_reasoning_effort_is_passed_and_nothing_streams() -> None:
    gateway = FakeGateway([_reply()])
    gateway.chat(
        [{"role": "user", "content": "hi"}], caller="t", purpose="p", reasoning_effort="high"
    )
    request = gateway.requests[0]
    assert request.reasoning_effort == "high"
    assert request.deployment == "gpt-6.1-sol"
    assert "stream" not in request.model_dump()


def test_structured_output_uses_the_contract_schema_and_validates_the_reply() -> None:
    playbook = {
        "id": "auth-sso",
        "questions": ["How does sign-in work?"],
        "evidence": ["static"],
        "tools": ["read_file"],
        "budget": {"max_turns": 5, "max_cost_usd": 1},
        "output": "finding",
        "feeds": ["sso-auth"],
    }
    gateway = FakeGateway([_reply(json.dumps(playbook))])
    result = gateway.structured(
        [{"role": "user", "content": "Draft a playbook"}], Playbook, caller="t", purpose="p"
    )
    assert result == Playbook.model_validate(playbook)
    response_format = gateway.requests[0].response_format
    assert response_format is not None
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "Playbook"
    assert response_format["json_schema"]["schema"] == Playbook.model_json_schema()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "The model returned no Playbook content"),
        ('{"id": "Not A Slug"}', "The model's Playbook failed validation at: budget, evidence"),
        ("not json", "failed validation at: <root>"),
    ],
)
def test_bad_structured_output_raises_a_typed_error(content: str | None, message: str) -> None:
    gateway = FakeGateway([ChatResult(content=content)])
    with pytest.raises(StructuredOutputError) as caught:
        gateway.structured([{"role": "user", "content": "x"}], Playbook, caller="t", purpose="p")
    assert message in caught.value.message
    assert caught.value.exit_code == 4


def test_per_call_token_budget_raises_after_auditing_the_call() -> None:
    gateway = FakeGateway([_reply(prompt=900, completion=200)])
    with pytest.raises(BudgetExceeded, match="The call used 1100 tokens; the budget is 1000"):
        gateway.chat(
            [{"role": "user", "content": "x"}],
            caller="t",
            purpose="p",
            budget=Budget(max_tokens=1000),
        )
    assert gateway.requests[0].max_completion_tokens == 1000
    (record,) = gateway.audit_records
    assert (record.outcome, record.error_code) == ("budget_exceeded", "budget_exceeded")


def test_per_call_cost_budget_uses_pricing() -> None:
    gateway = FakeGateway(
        [_reply(prompt=1000, completion=1000)], settings=fake_settings(pricing=PRICING)
    )
    with pytest.raises(BudgetExceeded, match=r"The call cost \$0.0400; the budget is \$0.0100"):
        gateway.chat(
            [{"role": "user", "content": "x"}],
            caller="t",
            purpose="p",
            budget=Budget(max_cost_usd=0.01),
        )
    assert gateway.audit_records[0].cost_usd == pytest.approx(0.04)


def test_a_cost_budget_without_pricing_fails_before_any_call() -> None:
    gateway = FakeGateway([_reply()], run_budget=RunBudget(Budget(max_cost_usd=1.0)))
    with pytest.raises(ConfigError, match="A cost budget needs pricing"):
        gateway.chat([{"role": "user", "content": "x"}], caller="t", purpose="p")
    assert gateway.requests == []


def test_run_budget_accumulates_and_then_blocks_further_calls() -> None:
    run = RunBudget(Budget(max_tokens=250))
    gateway = FakeGateway(
        [_reply(prompt=100, completion=20), _reply(prompt=100, completion=40)], run_budget=run
    )
    message = [{"role": "user", "content": "x"}]
    gateway.chat(message, caller="t", purpose="p", budget=Budget(max_tokens=500))
    assert (run.tokens, run.remaining_tokens()) == (120, 130)
    assert gateway.requests[0].max_completion_tokens == 250

    with pytest.raises(BudgetExceeded, match="The run used 260 tokens; the budget is 250"):
        gateway.chat(message, caller="t", purpose="p")
    assert gateway.requests[1].max_completion_tokens == 130

    with pytest.raises(BudgetExceeded, match="The run has used its 250-token budget"):
        gateway.chat(message, caller="t", purpose="p")
    assert len(gateway.requests) == 2


def test_run_cost_budget_blocks_once_spent() -> None:
    run = RunBudget(Budget(max_cost_usd=0.05))
    gateway = FakeGateway(
        [_reply(prompt=1000, completion=1000), _reply(prompt=1000, completion=1000)],
        settings=fake_settings(pricing=PRICING),
        run_budget=run,
    )
    message = [{"role": "user", "content": "x"}]
    gateway.chat(message, caller="t", purpose="p")
    with pytest.raises(BudgetExceeded, match=r"The run cost \$0.0800"):
        gateway.chat(message, caller="t", purpose="p")
    with pytest.raises(BudgetExceeded, match=r"The run has used its \$0.0500 budget"):
        gateway.chat(message, caller="t", purpose="p")


@pytest.mark.parametrize("budget", [{"max_tokens": 0}, {"max_cost_usd": -1.0}])
def test_budgets_must_be_positive(budget: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        Budget(**budget)  # type: ignore[arg-type]


def test_a_failed_call_is_audited_and_re_raised() -> None:
    gateway = FakeGateway([ExternalCallError("Azure OpenAI returned HTTP 500")])
    with pytest.raises(ExternalCallError):
        gateway.chat([{"role": "user", "content": "x"}], caller="t", purpose="p")
    (record,) = gateway.audit_records
    assert (record.outcome, record.error_code, record.prompt_tokens) == (
        "error",
        "external_call_failed",
        0,
    )


def test_fake_transport_complains_when_the_recording_runs_out() -> None:
    gateway = FakeGateway([])
    with pytest.raises(AssertionError, match="no more recorded responses"):
        gateway.chat([{"role": "user", "content": "x"}], caller="t", purpose="p")


def test_file_audit_log_appends_sorted_json_lines(tmp_path: Path) -> None:
    log = FileAuditLog(tmp_path / "audit")
    gateway = Gateway(fake_settings(), transport=FakeGateway([]).transport, audit=log)
    gateway._transport = FakeGateway([_reply(), _reply()]).transport  # pyright: ignore[reportPrivateUsage]
    for _ in range(2):
        gateway.chat([{"role": "user", "content": "secret plans"}], caller="t", purpose="p")
    lines = log.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert list(first) == sorted(first)
    assert ModelCallRecord.model_validate(first).outcome == "ok"
    assert "secret plans" not in log.path.read_text(encoding="utf-8")


def test_default_audit_dir_follows_accel_home(tmp_path: Path) -> None:
    assert default_audit_dir({"ACCEL_HOME": str(tmp_path)}) == tmp_path / "audit"
    assert default_audit_dir({}) == Path.home() / ".accel" / "audit"


def test_default_construction_uses_azure_and_the_accel_home_audit_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text(
        "AZURE_OPENAI_ENDPOINT=https://unit.openai.azure.com/\nAZURE_OPENAI_API_KEY=unit-key-123\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ACCEL_HOME", str(tmp_path / "home"))
    for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    gateway = Gateway.from_environment(root=tmp_path)
    assert type(gateway._transport).__name__ == "AzureTransport"  # pyright: ignore[reportPrivateUsage]
    assert gateway._audit.path == tmp_path / "home" / "audit" / "model-calls.jsonl"  # type: ignore[attr-defined]  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]


def test_errors_carry_stable_codes_and_exit_codes() -> None:
    assert (AccelError("x").code, AccelError("x").exit_code) == ("accel_error", 1)
    assert (ConfigError.code, ConfigError.exit_code) == ("config_invalid", 3)
    assert (BudgetExceeded.code, BudgetExceeded.exit_code) == ("budget_exceeded", 1)
    assert (ExternalCallError.code, ExternalCallError.exit_code) == ("external_call_failed", 4)
    assert issubclass(StructuredOutputError, ExternalCallError)
