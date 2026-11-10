"""AzureTransport through the real openai client, over an in-process HTTP mock."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from accel_core.errors import ExternalCallError
from accel_core.gateway import ChatRequest, ToolCall
from accel_core.gateway.azure import AzureTransport
from accel_core.testing import fake_settings

COMPLETION = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 1_767_000_000,
    "model": "gpt-6.1-sol",
    "choices": [
        {
            "index": 0,
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_9",
                        "type": "function",
                        "function": {"name": "add", "arguments": '{"a":1,"b":2}'},
                    }
                ],
            },
        }
    ],
    "usage": {"prompt_tokens": 42, "completion_tokens": 7, "total_tokens": 49},
}


def _transport(handler: Any) -> AzureTransport:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AzureTransport(fake_settings(), http_client=client, max_retries=0)


def test_request_goes_to_the_deployment_with_the_api_key_and_no_streaming() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=COMPLETION)

    request = ChatRequest(
        deployment="gpt-6.1-sol",
        messages=[{"role": "user", "content": "1 + 2?"}],
        tools=[{"type": "function", "function": {"name": "add", "parameters": {}}}],
        tool_choice="required",
        response_format={"type": "json_object"},
        reasoning_effort="low",
        max_completion_tokens=500,
    )
    result = _transport(handler).complete(request)

    (sent,) = seen
    assert sent.url.host == "fake-resource.openai.azure.com"
    assert sent.url.path == "/openai/deployments/gpt-6.1-sol/chat/completions"
    assert sent.url.params["api-version"] == "2024-10-21"
    assert sent.headers["api-key"] == "fake-key-for-tests-only"
    body = json.loads(sent.content)
    assert body["stream"] is False
    assert body["reasoning_effort"] == "low"
    assert body["tool_choice"] == "required"
    assert body["max_completion_tokens"] == 500
    assert body["response_format"] == {"type": "json_object"}

    assert result.tool_calls == [ToolCall(id="call_9", name="add", arguments='{"a":1,"b":2}')]
    assert result.finish_reason == "tool_calls"
    assert (result.usage.prompt_tokens, result.usage.completion_tokens) == (42, 7)


def test_optional_fields_are_omitted_when_unset() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        reply = {**COMPLETION, "usage": None}
        reply["choices"] = [
            {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "3"}}
        ]
        return httpx.Response(200, json=reply)

    result = _transport(handler).complete(
        ChatRequest(deployment="gpt-6.1-sol", messages=[{"role": "user", "content": "x"}])
    )
    assert set(bodies[0]) == {"model", "messages", "stream"}
    assert (result.content, result.tool_calls, result.usage.total_tokens) == ("3", [], 0)


def test_http_errors_become_external_call_errors_without_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": "401", "message": "bad key"}})

    with pytest.raises(ExternalCallError) as caught:
        _transport(handler).complete(
            ChatRequest(deployment="gpt-6.1-sol", messages=[{"role": "user", "content": "x"}])
        )
    assert "HTTP 401" in caught.value.message
    assert "fake-key-for-tests-only" not in caught.value.message
    assert caught.value.__cause__ is None


def test_connection_errors_become_external_call_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(ExternalCallError, match="APIConnectionError"):
        _transport(handler).complete(
            ChatRequest(deployment="gpt-6.1-sol", messages=[{"role": "user", "content": "x"}])
        )


def test_an_empty_choice_list_is_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={**COMPLETION, "choices": []})

    with pytest.raises(ExternalCallError, match="no choices"):
        _transport(handler).complete(
            ChatRequest(deployment="gpt-6.1-sol", messages=[{"role": "user", "content": "x"}])
        )
