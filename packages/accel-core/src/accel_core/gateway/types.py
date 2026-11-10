"""Provider-neutral request and result types shared by the gateway and its transports."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

Message = dict[str, Any]
"""One chat message in the OpenAI chat-completions shape."""

ToolSpec = dict[str, Any]
"""One tool definition in the OpenAI chat-completions shape."""

ReasoningEffort = Literal["low", "medium", "high"]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolCall(_Frozen):
    """A function call the model asked for. `arguments` is a JSON string."""

    id: str
    name: str
    arguments: str


class Usage(_Frozen):
    """Token counts for one call."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int:
        """Prompt plus completion tokens."""
        return self.prompt_tokens + self.completion_tokens


class ChatRequest(_Frozen):
    """What the gateway sends a transport, after redaction."""

    deployment: str
    messages: list[Message]
    tools: list[ToolSpec] = Field(default_factory=list[ToolSpec])
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    reasoning_effort: ReasoningEffort | None = None
    max_completion_tokens: int | None = None


class ChatResult(_Frozen):
    """What a transport returns: the first choice and the usage."""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list[ToolCall])
    finish_reason: str | None = None
    usage: Usage = Field(default_factory=Usage)

    def assistant_message(self) -> Message:
        """Return this result as an assistant message to append to the conversation."""
        message: Message = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in self.tool_calls
            ]
        return message


class Transport(Protocol):
    """Sends one chat-completions request. Raises ExternalCallError on failure."""

    def complete(self, request: ChatRequest) -> ChatResult:
        """Send `request` and return the first choice."""
        ...
