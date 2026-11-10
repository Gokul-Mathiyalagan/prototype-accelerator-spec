"""The `knowledge-manifest` and `extract-plan` contracts for `knowledge/<repo>/`."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from accel_core.contracts._base import Commit, Contract, Part, Slug, Text

Stage = Literal[
    "acquire", "inventory", "static", "runtime", "rea", "investigate", "verify", "knowledge"
]
StageStatus = Literal["ok", "skipped", "failed"]


class StageResult(Part):
    """The outcome of one extraction stage."""

    stage: Stage
    status: StageStatus
    detail: str = ""
    finished_at: AwareDatetime | None = None


class KnowledgeManifest(Contract):
    """`knowledge/<repo>/manifest.json`."""

    repo: Slug
    commit: Commit
    created_at: AwareDatetime
    updated_at: AwareDatetime
    stages: list[StageResult] = Field(default_factory=list[StageResult])
    tool_versions: dict[Slug, Text] = Field(default_factory=dict[str, str])

    @model_validator(mode="after")
    def _consistent(self) -> KnowledgeManifest:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at is earlier than created_at")
        seen = [result.stage for result in self.stages]
        duplicates = sorted({stage for stage in seen if seen.count(stage) > 1})
        if duplicates:
            raise ValueError(f"stage listed more than once: {', '.join(duplicates)}")
        return self


class ExtractPlan(Contract):
    """The YAML header of `knowledge/<repo>/extract-plan.md`.

    The markdown checklist below the header records progress; the header records how
    the plan was prepared and which playbooks it includes.
    """

    repo: Slug
    commit: Commit
    prepared_at: AwareDatetime
    runtime: StageStatus
    rea: StageStatus
    native_binaries: int = Field(default=0, ge=0)
    native_binaries_licensed: int = Field(default=0, ge=0)
    playbooks: list[Slug] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> ExtractPlan:
        if self.native_binaries_licensed > self.native_binaries:
            raise ValueError("native_binaries_licensed exceeds native_binaries")
        if len(set(self.playbooks)) != len(self.playbooks):
            raise ValueError("playbooks must be unique")
        return self
