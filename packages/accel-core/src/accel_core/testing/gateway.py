"""FakeGateway: the real gateway with a transport that replays recorded responses."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pydantic import SecretStr, TypeAdapter

from accel_core.audit import ModelCallRecord
from accel_core.errors import AccelError
from accel_core.gateway.budget import RunBudget
from accel_core.gateway.config import AzureOpenAISettings, Pricing
from accel_core.gateway.gateway import Gateway
from accel_core.gateway.types import ChatRequest, ChatResult
from accel_core.redaction import Redactor

_RECORDING = TypeAdapter(list[ChatResult])


def load_recording(path: Path) -> list[ChatResult]:
    """Load recorded responses: a JSON list of ChatResult objects."""
    return _RECORDING.validate_json(path.read_bytes())


def fake_settings(*, pricing: Pricing | None = None) -> AzureOpenAISettings:
    """Settings that point nowhere real."""
    return AzureOpenAISettings(
        endpoint="https://fake-resource.openai.azure.com/",
        api_key=SecretStr("fake-key-for-tests-only"),
        deployment="gpt-6.1-sol",
        api_version="2024-10-21",
        pricing=pricing,
    )


class FakeTransport:
    """Returns queued results (or raises queued errors) in order, and records each request."""

    def __init__(self, responses: Iterable[ChatResult | AccelError]) -> None:
        self._responses = list(responses)
        self.requests: list[ChatRequest] = []

    def complete(self, request: ChatRequest) -> ChatResult:
        """Record `request` and return the next queued response."""
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeTransport has no more recorded responses")
        response = self._responses.pop(0)
        if isinstance(response, AccelError):
            raise response
        return response


class MemoryAuditLog:
    """Keeps audit records in a list."""

    def __init__(self) -> None:
        self.records: list[ModelCallRecord] = []

    def write(self, record: ModelCallRecord) -> None:
        """Keep one record."""
        self.records.append(record)


class FakeGateway(Gateway):
    """A real Gateway (redaction, budgets, audit) over a replaying transport.

    `requests` holds what would have been sent, after redaction; `audit_records`
    holds what would have been audited.
    """

    def __init__(
        self,
        responses: Iterable[ChatResult | AccelError] | Path,
        *,
        settings: AzureOpenAISettings | None = None,
        redactor: Redactor | None = None,
        run_budget: RunBudget | None = None,
    ) -> None:
        recorded = load_recording(responses) if isinstance(responses, Path) else responses
        self.transport = FakeTransport(recorded)
        self.audit_log = MemoryAuditLog()
        super().__init__(
            settings or fake_settings(),
            transport=self.transport,
            redactor=redactor,
            audit=self.audit_log,
            run_budget=run_budget,
        )

    @property
    def requests(self) -> list[ChatRequest]:
        """Requests sent so far, after redaction."""
        return self.transport.requests

    @property
    def audit_records(self) -> list[ModelCallRecord]:
        """Audit records written so far."""
        return self.audit_log.records
