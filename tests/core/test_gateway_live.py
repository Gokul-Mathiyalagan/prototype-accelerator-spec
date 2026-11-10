"""Live: one tool-calling round trip against the configured Azure OpenAI deployment.

Run with `make test-live NEEDS=azure` after filling in `.env` (see `.env.example`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from accel_core.gateway import Budget, Gateway, Message
from accel_core.testing import MemoryAuditLog

ROOT = Path(__file__).resolve().parents[2]
ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two integers and return the sum.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
}


@pytest.mark.live_azure
def test_tool_calling_round_trip_against_azure() -> None:
    audit = MemoryAuditLog()
    live = Gateway.from_environment(root=ROOT)
    gateway = Gateway(live.settings, audit=audit)
    budget = Budget(max_tokens=4000)
    messages: list[Message] = [
        {"role": "system", "content": "Use the add tool for arithmetic."},
        {"role": "user", "content": "What is 17 + 25?"},
    ]

    first = gateway.chat(
        messages,
        caller="tests.live",
        purpose="tool round trip",
        tools=[ADD_TOOL],
        tool_choice="required",
        reasoning_effort="low",
        budget=budget,
    )
    assert first.tool_calls and first.tool_calls[0].name == "add"
    arguments = json.loads(first.tool_calls[0].arguments)
    assert {arguments["a"], arguments["b"]} == {17, 25}

    messages += [
        first.assistant_message(),
        {
            "role": "tool",
            "tool_call_id": first.tool_calls[0].id,
            "content": str(arguments["a"] + arguments["b"]),
        },
    ]
    second = gateway.chat(
        messages,
        caller="tests.live",
        purpose="tool round trip",
        tools=[ADD_TOOL],
        reasoning_effort="low",
        budget=budget,
    )
    assert second.content is not None and "42" in second.content
    assert [record.outcome for record in audit.records] == ["ok", "ok"]
