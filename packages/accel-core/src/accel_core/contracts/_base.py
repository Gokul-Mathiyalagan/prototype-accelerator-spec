"""Shared base model and field types for every contract."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

SCHEMA_VERSION = 1


class Contract(BaseModel):
    """Base for every file-format contract: strict keys, immutable, versioned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = Field(
        default=SCHEMA_VERSION, description="Contract version; bump on breaking changes."
    )


class Part(BaseModel):
    """Base for nested objects inside a contract: strict keys and immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_relative_path(value: str) -> str:
    """Reject absolute paths, backslashes and parent-directory segments."""
    if "\\" in value:
        raise ValueError("use forward slashes in paths")
    if value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        raise ValueError("path must be relative")
    if ".." in PurePosixPath(value).parts:
        raise ValueError("path must not contain '..'")
    return value


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
Signal = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")]
"""An inventory signal name, such as `auth_library_or_middleware`."""
Commit = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{7,40}$")]
FullCommit = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SemVer = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
Handle = Annotated[
    str, StringConstraints(pattern=r"^@[A-Za-z0-9][A-Za-z0-9-]*(/[A-Za-z0-9][A-Za-z0-9-]*)?$")
]
RelPath = Annotated[str, StringConstraints(min_length=1), AfterValidator(_check_relative_path)]

Confidence = Literal["low", "medium", "high"]
Level = Literal["mock", "prototype", "pilot", "production"]
Platform = Literal["darwin-arm64", "darwin-x64", "linux-x64"]
PLATFORMS: tuple[Platform, ...] = ("darwin-arm64", "darwin-x64", "linux-x64")
