"""The gateway: the only path from product code to a model (C1)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from accel_core.audit import AuditSink, FileAuditLog, ModelCallRecord, Outcome, default_audit_dir
from accel_core.errors import AccelError, BudgetExceeded, ConfigError, StructuredOutputError
from accel_core.gateway.budget import Budget, RunBudget, check
from accel_core.gateway.config import AzureOpenAISettings, load_settings
from accel_core.gateway.types import (
    ChatRequest,
    ChatResult,
    Message,
    ReasoningEffort,
    ToolSpec,
    Transport,
)
from accel_core.redaction import Redactor

ModelT = TypeVar("ModelT", bound=BaseModel)
log = logging.getLogger("accel.core.gateway")


def response_format_for(model: type[BaseModel]) -> dict[str, Any]:
    """Build a JSON Schema response format from a contract model.

    `strict` is off because Azure's strict mode needs every field required; the
    gateway validates the reply against the model instead.
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "schema": model.model_json_schema(),
            "strict": False,
        },
    }


class Gateway:
    """Redacts, sends, costs, budgets and audits every model call."""

    def __init__(
        self,
        settings: AzureOpenAISettings,
        *,
        transport: Transport | None = None,
        redactor: Redactor | None = None,
        audit: AuditSink | None = None,
        run_budget: RunBudget | None = None,
    ) -> None:
        if transport is None:
            from accel_core.gateway.azure import AzureTransport

            transport = AzureTransport(settings)
        self.settings = settings
        self.run_budget = run_budget
        self._transport = transport
        self._redactor = (redactor or Redactor()).with_literal(
            "azure_openai_key", settings.api_key.get_secret_value()
        )
        self._audit = audit if audit is not None else FileAuditLog(default_audit_dir())

    @classmethod
    def from_environment(
        cls, *, root: Path | None = None, run_budget: RunBudget | None = None
    ) -> Gateway:
        """Build a gateway from the environment, `.env` and `accel.toml` in `root`."""
        return cls(load_settings(root=root), run_budget=run_budget)

    def chat(
        self,
        messages: Sequence[Message],
        *,
        caller: str,
        purpose: str,
        tools: Sequence[ToolSpec] = (),
        tool_choice: str | dict[str, Any] | None = None,
        response_model: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        budget: Budget | None = None,
    ) -> ChatResult:
        """Send one non-streaming chat completion and return the first choice.

        Every message is redacted first. Raises BudgetExceeded when the call or the run
        goes over budget, and ExternalCallError when Azure OpenAI fails.
        """
        self._require_pricing(budget)
        if self.run_budget is not None:
            self.run_budget.ensure_available()

        session = self._redactor.session()
        redacted: list[Message] = [session.value(message) for message in messages]
        request = ChatRequest(
            deployment=self.settings.deployment,
            messages=redacted,
            tools=list(tools),
            tool_choice=tool_choice,
            response_format=response_format_for(response_model) if response_model else None,
            reasoning_effort=reasoning_effort,
            max_completion_tokens=self._completion_cap(budget),
        )
        redactions = dict(session.counts)

        try:
            result = self._transport.complete(request)
        except AccelError as error:
            self._record(caller, purpose, "error", None, 0.0, redactions, error.code)
            raise

        cost = self._cost(result)
        try:
            if budget is not None:
                check(budget, result.usage.total_tokens, cost, "The call")
            if self.run_budget is not None:
                self.run_budget.add(result.usage.total_tokens, cost)
        except BudgetExceeded as error:
            self._record(caller, purpose, "budget_exceeded", result, cost, redactions, error.code)
            raise
        self._record(caller, purpose, "ok", result, cost, redactions, None)
        return result

    def structured(
        self,
        messages: Sequence[Message],
        model: type[ModelT],
        *,
        caller: str,
        purpose: str,
        reasoning_effort: ReasoningEffort | None = None,
        budget: Budget | None = None,
    ) -> ModelT:
        """Ask for output matching `model`'s JSON Schema, and return it validated."""
        result = self.chat(
            messages,
            caller=caller,
            purpose=purpose,
            response_model=model,
            reasoning_effort=reasoning_effort,
            budget=budget,
        )
        if not result.content:
            raise StructuredOutputError(f"The model returned no {model.__name__} content")
        try:
            return model.model_validate_json(result.content)
        except ValidationError as error:
            locations = {".".join(str(part) for part in item["loc"]) for item in error.errors()}
            fields = sorted(location or "<root>" for location in locations)
            raise StructuredOutputError(
                f"The model's {model.__name__} failed validation at: {', '.join(fields)}"
            ) from None

    def _require_pricing(self, budget: Budget | None) -> None:
        wants_cost = any(
            b is not None and b.max_cost_usd is not None
            for b in (budget, self.run_budget.budget if self.run_budget else None)
        )
        if wants_cost and self.settings.pricing is None:
            raise ConfigError(
                "A cost budget needs pricing. Set input_usd_per_mtok and output_usd_per_mtok "
                "under [azure_openai] in accel.toml."
            )

    def _completion_cap(self, budget: Budget | None) -> int | None:
        caps = [
            cap
            for cap in (
                budget.max_tokens if budget else None,
                self.run_budget.remaining_tokens() if self.run_budget else None,
            )
            if cap is not None
        ]
        return min(caps) if caps else None

    def _cost(self, result: ChatResult) -> float:
        pricing = self.settings.pricing
        if pricing is None:
            return 0.0
        return pricing.cost(result.usage.prompt_tokens, result.usage.completion_tokens)

    def _record(
        self,
        caller: str,
        purpose: str,
        outcome: Outcome,
        result: ChatResult | None,
        cost: float,
        redactions: dict[str, int],
        error_code: str | None,
    ) -> None:
        usage = result.usage if result else None
        record = ModelCallRecord(
            time=datetime.now(UTC),
            caller=caller,
            purpose=purpose,
            deployment=self.settings.deployment,
            outcome=outcome,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            cost_usd=cost,
            redactions=redactions,
            error_code=error_code,
        )
        self._audit.write(record)
        log.info(
            "model call %s/%s: %s, %d tokens, %d redactions",
            caller,
            purpose,
            outcome,
            usage.total_tokens if usage else 0,
            sum(redactions.values()),
        )
