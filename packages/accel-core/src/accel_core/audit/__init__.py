"""The audit trail: one JSON line per model call, never the content (spec/06)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Outcome = Literal["ok", "error", "budget_exceeded"]


class ModelCallRecord(BaseModel):
    """What the audit log keeps about one model call. Content is never recorded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event: Literal["model_call"] = "model_call"
    time: AwareDatetime
    caller: str
    purpose: str
    deployment: str
    outcome: Outcome
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    redactions: dict[str, int] = Field(default_factory=dict[str, int])
    error_code: str | None = None


class AuditSink(Protocol):
    """Anything that can store audit records."""

    def write(self, record: ModelCallRecord) -> None:
        """Store one record."""
        ...


class FileAuditLog:
    """Appends records to `<directory>/model-calls.jsonl`."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "model-calls.jsonl"

    def write(self, record: ModelCallRecord) -> None:
        """Append one record as a sorted-key JSON line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.model_dump(mode="json"), sort_keys=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")


def default_audit_dir(environ: Mapping[str, str] | None = None) -> Path:
    """Return `$ACCEL_HOME/audit`, defaulting `ACCEL_HOME` to `~/.accel`."""
    env = os.environ if environ is None else environ
    home = env.get("ACCEL_HOME")
    return (Path(home).expanduser() if home else Path.home() / ".accel") / "audit"


__all__ = ["AuditSink", "FileAuditLog", "ModelCallRecord", "Outcome", "default_audit_dir"]
