"""The `ui-spec` contract: screens inferred from an HTML wireframe."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from accel_core.contracts._base import Contract, Part, RelPath, Slug, Text

Route = Annotated[str, StringConstraints(pattern=r"^/[A-Za-z0-9_:./-]*$")]
ScreenState = Literal["loading", "empty", "error", "no-access"]


class UiSource(Part):
    """The wireframe the spec came from. HTML only (C6)."""

    kind: Literal["html"]
    path: RelPath


class ComponentMapping(Part):
    """A wireframe element mapped to an approved component."""

    wireframe: Text = Field(description="CSS selector in the wireframe")
    maps_to: Text
    confidence: float = Field(ge=0, le=1)


class DataNeed(Part):
    """An entity a screen shows or edits."""

    entity: Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9]*$")]
    fields: list[Text] = Field(min_length=1)


class Action(Part):
    """A button or link on a screen."""

    label: Text
    kind: Slug


class Screenshots(Part):
    """Wireframe screenshots at desktop (1440 px) and mobile (390 px) widths."""

    desktop: RelPath
    mobile: RelPath


class Screen(Part):
    """One screen of the wireframe."""

    id: Slug
    route: Route
    pattern: Slug
    regions: list[Slug] = Field(default_factory=list[str])
    components: list[ComponentMapping] = Field(default_factory=list[ComponentMapping])
    data: list[DataNeed] = Field(default_factory=list[DataNeed])
    actions: list[Action] = Field(default_factory=list[Action])
    states: list[ScreenState] = Field(default_factory=list[ScreenState])
    open_questions: list[Text] = Field(default_factory=list[str])
    screenshots: Screenshots


class UiSpec(Contract):
    """`aisdlc/03-design/ui-spec.json`."""

    source: UiSource
    screens: list[Screen] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_screens(self) -> UiSpec:
        ids = [screen.id for screen in self.screens]
        if len(set(ids)) != len(ids):
            raise ValueError("screen ids must be unique")
        return self
