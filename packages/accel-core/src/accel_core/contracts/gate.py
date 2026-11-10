"""The `gate-record` contract: a named person's approval between phases."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field

from accel_core.contracts._base import Commit, Contract, Handle, Level, Part, RelPath, Sha256

Gate = Literal["spec", "design", "plan", "review", "release"]


class ApprovedArtifact(Part):
    """A file, or a folder ending in '/', and its content hash at approval."""

    path: RelPath
    sha256: Sha256


class GateRecord(Contract):
    """`aisdlc/gates/<gate>-<level>.yaml`."""

    gate: Gate
    level: Level
    approved_by: Handle
    approved_at: AwareDatetime
    commit: Commit
    artifacts: list[ApprovedArtifact] = Field(min_length=1)
    notes: str = ""
