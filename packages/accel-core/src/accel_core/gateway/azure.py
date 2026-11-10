"""The real transport: the `openai` package's AzureOpenAI client with API key auth.

This is the only module in product code that imports `openai` (spec/06, ADR-0008).
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import openai
from openai import AzureOpenAI, omit

from accel_core.errors import ExternalCallError
from accel_core.gateway.config import AzureOpenAISettings
from accel_core.gateway.types import ChatRequest, ChatResult, ToolCall, Usage


class AzureTransport:
    """Sends chat completions to the configured Azure OpenAI deployment."""

    def __init__(
        self,
        settings: AzureOpenAISettings,
        *,
        http_client: httpx.Client | None = None,
        max_retries: int = 2,
        timeout_seconds: float = 300.0,
    ) -> None:
        self._client = AzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key.get_secret_value(),
            api_version=settings.api_version,
            max_retries=max_retries,
            timeout=timeout_seconds,
            http_client=http_client,
        )

    def complete(self, request: ChatRequest) -> ChatResult:
        """Send one non-streaming chat-completions request."""
        try:
            response = self._client.chat.completions.create(
                model=request.deployment,
                messages=cast(Any, request.messages),
                tools=cast(Any, request.tools) if request.tools else omit,
                tool_choice=cast(Any, request.tool_choice) if request.tool_choice else omit,
                response_format=cast(Any, request.response_format)
                if request.response_format
                else omit,
                reasoning_effort=request.reasoning_effort or omit,
                max_completion_tokens=request.max_completion_tokens or omit,
                stream=False,
            )
        except openai.APIStatusError as error:
            raise ExternalCallError(
                f"Azure OpenAI returned HTTP {error.status_code} ({type(error).__name__}). "
                "Check the endpoint, deployment name, API version and key."
            ) from None
        except openai.APIError as error:
            raise ExternalCallError(
                f"Azure OpenAI call failed ({type(error).__name__}). "
                "Check the network connection and AZURE_OPENAI_ENDPOINT."
            ) from None

        if not response.choices:
            raise ExternalCallError("Azure OpenAI returned no choices")
        choice = response.choices[0]
        calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in choice.message.tool_calls or []
            if call.type == "function"
        ]
        usage = response.usage
        return ChatResult(
            content=choice.message.content,
            tool_calls=calls,
            finish_reason=choice.finish_reason,
            usage=Usage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            ),
        )
