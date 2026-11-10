"""The `install-check` and `versions-lock` contracts for `/accel-setup`."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, StringConstraints, model_validator

from accel_core.contracts._base import (
    PLATFORMS,
    Contract,
    FullCommit,
    Part,
    Platform,
    Sha256,
)

Component = Literal["node", "jdk", "ghidra", "ghidra-arm64-decompiler", "rea", "env"]
Version = Annotated[str, StringConstraints(pattern=r"^\d+(\.\d+)*$")]


class ComponentCheck(Part):
    """The state of one installed component."""

    name: Component
    status: Literal["missing", "ok", "wrong_version"]
    detail: str = ""


class InstallCheck(Contract):
    """The JSON object `install.sh --check --json` prints."""

    ok: bool
    platform: Platform
    components: list[ComponentCheck] = Field(min_length=1)
    next_action: str = ""

    @model_validator(mode="after")
    def _ok_matches_components(self) -> InstallCheck:
        all_ok = all(component.status == "ok" for component in self.components)
        if self.ok != all_ok:
            raise ValueError("ok must be true exactly when every component is ok")
        if not self.ok and not self.next_action.strip():
            raise ValueError("next_action is required when ok is false")
        return self


def _check_platforms(value: dict[Platform, str]) -> None:
    missing = [platform for platform in PLATFORMS if platform not in value]
    if missing:
        raise ValueError(f"missing checksums for: {', '.join(missing)}")


class ReaPin(Part):
    """REA has no tagged releases, so it is pinned by full commit."""

    repo: AnyHttpUrl
    commit: FullCommit


class NodePin(Part):
    """Node, at the version in REA's `.nvmrc` at the pinned commit."""

    version: Version
    sha256: dict[Platform, Sha256]

    @model_validator(mode="after")
    def _all_platforms(self) -> NodePin:
        _check_platforms(self.sha256)
        return self


class JdkPin(Part):
    """Temurin JDK 21."""

    vendor: Literal["temurin"]
    version: Annotated[str, StringConstraints(pattern=r"^21(\.\d+)*$")]
    sha256: dict[Platform, Sha256]

    @model_validator(mode="after")
    def _all_platforms(self) -> JdkPin:
        _check_platforms(self.sha256)
        return self


class GhidraPin(Part):
    """Ghidra 12.1.x; 12.2 needs JDK 25."""

    version: Annotated[str, StringConstraints(pattern=r"^12\.1\.\d+$")]
    url: AnyHttpUrl
    sha256: Sha256


class VersionsLock(Contract):
    """`setup/versions.lock`."""

    rea: ReaPin
    node: NodePin
    jdk: JdkPin
    ghidra: GhidraPin
