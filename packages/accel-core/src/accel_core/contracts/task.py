"""The `task` contract: one entry in a generated project's `aisdlc/05-plan/tasks.yaml`.

This is the product's task format, not this repo's own `tasks/tasks.yaml`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from accel_core.contracts._base import Contract, Slug, Text

TaskId = Annotated[str, StringConstraints(pattern=r"^T-\d{3,}$")]
TaskStatus = Literal["ready", "claimed", "in_review", "done", "blocked"]
_CLAIMED_STATES: tuple[TaskStatus, ...] = ("claimed", "in_review")


class Task(Contract):
    """One task. The claim fields act as the lock between Copilot sessions."""

    id: TaskId
    title: Text
    depends_on: list[TaskId] = Field(default_factory=list[str])
    skills: list[Slug] = Field(default_factory=list[str])
    inputs: list[Text] = Field(default_factory=list[str])
    acceptance: list[Text] = Field(min_length=1)
    done_when: list[Text] = Field(min_length=1)
    status: TaskStatus
    claimed_by: Text | None = None
    claimed_at: AwareDatetime | None = None
    branch: Text | None = None
    pr: Text | None = None
    blocked_reason: Text | None = None

    @model_validator(mode="after")
    def _status_fields(self) -> Task:
        claim = (self.claimed_by, self.claimed_at, self.branch)
        if self.status == "ready" and any(value is not None for value in claim):
            raise ValueError("a ready task must have no claimed_by, claimed_at or branch")
        if self.status in _CLAIMED_STATES and any(value is None for value in claim):
            raise ValueError(f"a {self.status} task needs claimed_by, claimed_at and branch")
        if self.status == "in_review" and self.pr is None:
            raise ValueError("an in_review task needs pr")
        if self.status == "blocked" and self.blocked_reason is None:
            raise ValueError("a blocked task needs blocked_reason")
        if self.branch is not None and not self.branch.startswith(f"task/{self.id}-"):
            raise ValueError(f"branch must be task/{self.id}-<slug>")
        if self.id in self.depends_on:
            raise ValueError("a task cannot depend on itself")
        return self
