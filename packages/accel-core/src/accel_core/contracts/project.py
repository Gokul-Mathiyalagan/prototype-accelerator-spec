"""The `project` contract: a generated project's `aisdlc/project.yaml`."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from accel_core.contracts._base import Contract, Handle, Level, Part, Slug, Text

BlueprintRef = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*@\d+(\.\d+){0,2}$")
]
_REAL_ADAPTER_LEVELS: tuple[Level, ...] = ("pilot", "production")


class Owners(Part):
    """Who approves each kind of gate."""

    product: Handle
    tech: Handle
    design: Handle


class Adapters(Part):
    """Mock adapters until pilot; real ones from pilot onward."""

    auth: Literal["mock-idp", "oidc"]
    data: Literal["sample-data", "postgres", "databricks-sql"]


class Project(Contract):
    """`aisdlc/project.yaml`."""

    name: Slug
    blueprint: BlueprintRef = Field(description="<blueprint>@<version>")
    level: Level
    assistant: Literal["github-copilot"]
    copilot_model: Text
    design_source: Literal["html"]
    owners: Owners
    adapters: Adapters

    @model_validator(mode="after")
    def _real_adapters_from_pilot(self) -> Project:
        if self.level in _REAL_ADAPTER_LEVELS:
            if self.adapters.auth != "oidc":
                raise ValueError(f"level {self.level} needs auth adapter 'oidc'")
            if self.adapters.data == "sample-data":
                raise ValueError(f"level {self.level} needs a real data adapter")
        return self
