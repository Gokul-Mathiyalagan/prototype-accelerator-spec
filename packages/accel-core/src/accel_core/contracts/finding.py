"""The `finding` contract: one evidence-backed claim about a target repo."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from accel_core.contracts._base import (
    Commit,
    Confidence,
    Contract,
    Part,
    RelPath,
    Slug,
    Text,
)

FindingId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+(-[a-z0-9]+)*$"),
]
RecordedBy = Annotated[str, StringConstraints(pattern=r"^(copilot|batch):[A-Za-z0-9._-]+$")]


class StaticEvidence(Part):
    """A file and line in the redacted clone at a pinned commit."""

    kind: Literal["static"]
    repo: Slug
    path: RelPath
    line: int = Field(ge=1)
    commit: Commit


class RuntimeEvidence(Part):
    """An observation from the running app: a HAR entry or a screenshot."""

    kind: Literal["runtime"]
    source: Literal["har", "screenshot"]
    entry: int | None = Field(default=None, ge=0, description="HAR entry index")
    path: RelPath | None = Field(default=None, description="Screenshot path")
    note: Text

    @model_validator(mode="after")
    def _source_has_locator(self) -> RuntimeEvidence:
        if self.source == "har" and self.entry is None:
            raise ValueError("HAR evidence needs 'entry'")
        if self.source == "screenshot" and self.path is None:
            raise ValueError("screenshot evidence needs 'path'")
        return self


Evidence = Annotated[StaticEvidence | RuntimeEvidence, Field(discriminator="kind")]


class Finding(Contract):
    """One line of `findings.jsonl`."""

    id: FindingId = Field(description="<playbook>.<slug>, unique per repo")
    playbook: Slug
    claim: Text
    evidence: list[Evidence] = Field(min_length=1)
    confidence: Confidence
    unknowns: list[Text] = Field(default_factory=list[str])
    feeds_skills: list[Slug] = Field(default_factory=list[str])
    recorded_by: RecordedBy

    @model_validator(mode="after")
    def _id_matches_playbook(self) -> Finding:
        prefix = self.id.split(".", 1)[0]
        if prefix != self.playbook:
            raise ValueError(f"id prefix '{prefix}' must equal playbook '{self.playbook}'")
        return self


def check_static_evidence(finding: Finding, repo_root: Path) -> list[str]:
    """Return a problem for each static evidence path or line missing from `repo_root`.

    `repo_root` is the redacted clone, `work/<repo>@<sha>/`. An empty list means every
    static citation resolves. Runtime evidence is not checked here.
    """
    root = repo_root.resolve()
    problems: list[str] = []
    for index, item in enumerate(finding.evidence):
        if not isinstance(item, StaticEvidence):
            continue
        where = f"evidence[{index}] {item.path}"
        target = (root / item.path).resolve()
        if not target.is_relative_to(root):
            problems.append(f"{where}: path leaves the repo root")
        elif not target.is_file():
            problems.append(f"{where}: file not found")
        else:
            line_count = _count_lines(target)
            if item.line > line_count:
                problems.append(f"{where}: line {item.line} is past the end ({line_count} lines)")
    return problems


def _count_lines(path: Path) -> int:
    """Count lines the way an editor numbers them, including a final unterminated line."""
    data = path.read_bytes()
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)
