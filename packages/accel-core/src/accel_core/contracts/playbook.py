"""The `playbook` contract: one investigation domain for Engine 1."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from accel_core.contracts._base import Contract, Part, Signal, Slug, Text

EvidenceKind = Literal["static", "runtime"]
Tool = Literal["code_graph", "read_file", "rea", "terminal"]


class IncludeWhen(Part):
    """Inventory signals that make a playbook worth running; any one is enough."""

    inventory: list[Signal] = Field(min_length=1)


class Budget(Part):
    """Limits for one playbook run. Cost applies in batch mode."""

    max_turns: int = Field(gt=0)
    max_cost_usd: float = Field(gt=0)


class Playbook(Contract):
    """`playbooks/<id>.yaml`."""

    id: Slug
    questions: list[Text] = Field(min_length=1)
    evidence: list[EvidenceKind] = Field(min_length=1)
    tools: list[Tool] = Field(min_length=1)
    include_when: IncludeWhen | None = Field(
        default=None, description="Omit to include the playbook for every repo."
    )
    budget: Budget
    output: Literal["finding"]
    feeds: list[Slug] = Field(min_length=1)
