"""Typed errors. Each carries a stable `code` and the CLI exit code it maps to (spec/05)."""

from __future__ import annotations

from typing import ClassVar


class AccelError(Exception):
    """Base for every error the platform raises on purpose."""

    code: ClassVar[str] = "accel_error"
    exit_code: ClassVar[int] = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigError(AccelError):
    """Required configuration is missing or invalid. The message says how to fix it."""

    code = "config_invalid"
    exit_code = 3


class BudgetExceeded(AccelError):
    """A per-call or per-run token or cost budget was exceeded."""

    code = "budget_exceeded"
    exit_code = 1


class ExternalCallError(AccelError):
    """A call to an external service (Azure OpenAI, git, REA) failed."""

    code = "external_call_failed"
    exit_code = 4


class StructuredOutputError(ExternalCallError):
    """The model's structured output didn't match the requested contract."""

    code = "structured_output_invalid"
