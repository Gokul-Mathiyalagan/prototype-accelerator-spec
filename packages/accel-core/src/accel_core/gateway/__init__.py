"""The Azure OpenAI gateway: the only way product code calls a model (C1, ADR-0008)."""

from accel_core.gateway.budget import Budget, RunBudget
from accel_core.gateway.config import AzureOpenAISettings, Pricing, load_settings
from accel_core.gateway.gateway import Gateway, response_format_for
from accel_core.gateway.types import (
    ChatRequest,
    ChatResult,
    Message,
    ReasoningEffort,
    ToolCall,
    ToolSpec,
    Transport,
    Usage,
)

__all__ = [
    "AzureOpenAISettings",
    "Budget",
    "ChatRequest",
    "ChatResult",
    "Gateway",
    "Message",
    "Pricing",
    "ReasoningEffort",
    "RunBudget",
    "ToolCall",
    "ToolSpec",
    "Transport",
    "Usage",
    "load_settings",
    "response_format_for",
]
