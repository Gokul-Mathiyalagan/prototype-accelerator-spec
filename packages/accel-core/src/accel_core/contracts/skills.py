"""The `catalog-entry`, `skills-lock` and `provenance` contracts for Engine 2."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import Field, model_validator

from accel_core.contracts._base import (
    Commit,
    Confidence,
    Contract,
    Handle,
    Part,
    SemVer,
    Signal,
    Slug,
    Text,
)
from accel_core.contracts.finding import FindingId

Group = Literal["foundation", "ui", "api", "security", "backend", "ai", "delivery", "sdlc"]
Nature = Literal["standard", "workflow", "generator", "reference", "review"]


class EmitWhen(Part):
    """When the skills planner emits a skill.

    Either `always`, or a playbook finding and/or an inventory signal at or above
    `min_confidence`.
    """

    always: bool = False
    playbook: Slug | None = None
    inventory: list[Signal] = Field(default_factory=list[str])
    min_confidence: Confidence = "medium"

    @model_validator(mode="after")
    def _one_rule(self) -> EmitWhen:
        has_signal = self.playbook is not None or bool(self.inventory)
        if self.always and has_signal:
            raise ValueError("'always' cannot be combined with playbook or inventory")
        if not self.always and not has_signal:
            raise ValueError("set 'always', or name a playbook or inventory signal")
        return self


class CatalogEntry(Contract):
    """One skill in `catalog/taxonomy.yaml`."""

    skill: Slug
    group: Group
    nature: list[Nature] = Field(min_length=1)
    emit_when: EmitWhen
    owner: Slug
    checks: list[Text] = Field(default_factory=list[str])


class LockedSkill(Part):
    """One skill pinned by version and registry commit."""

    version: SemVer
    commit: Commit


class SkillsLock(Contract):
    """A project's `skills.lock`, written by `accel skills sync`."""

    registry: Text
    skills: dict[Slug, LockedSkill]


class ProvenanceSource(Part):
    """A reference repo and the findings a skill was drafted from."""

    repo: Slug
    commit: Commit
    findings: list[FindingId] = Field(min_length=1)


class GeneratedBy(Part):
    """The tool and model that drafted the skill."""

    tool: Slug
    version: SemVer
    model: Text


class ApprovedBy(Part):
    """The owner's approval in the registry."""

    github: Handle
    pr: int = Field(gt=0)
    date: dt.date


class Provenance(Contract):
    """`skills/<name>/provenance.yaml`."""

    skill: Slug
    version: SemVer
    catalog_version: int = Field(ge=1)
    owner: Slug
    sources: list[ProvenanceSource] = Field(
        default_factory=list[ProvenanceSource],
        description="Empty for authored skills.",
    )
    generated_by: GeneratedBy
    approved_by: ApprovedBy | None = Field(default=None, description="Null until approved.")
