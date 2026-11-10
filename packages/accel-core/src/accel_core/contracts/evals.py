"""The `eval-case` and `eval-report` contracts for skill evaluation."""

from __future__ import annotations

import math
from typing import Annotated

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from accel_core.contracts._base import Contract, Part, RelPath, SemVer, Slug, Text

EvalCaseId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*-\d{2,}$")]
Score = Annotated[float, Field(ge=0, le=1)]
_TOLERANCE = 1e-6


class RubricItem(Part):
    """One graded criterion and its share of the score."""

    criterion: Text
    weight: float = Field(gt=0, le=1)


class EvalCase(Contract):
    """`skills/<name>/evals/<n>.yaml`: one prompt and its rubric."""

    id: EvalCaseId = Field(description="<skill>-<nn>")
    prompt: Text
    fixture: RelPath = Field(description="Repo state the eval starts from")
    rubric: list[RubricItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> EvalCase:
        total = sum(item.weight for item in self.rubric)
        if not math.isclose(total, 1.0, abs_tol=_TOLERANCE):
            raise ValueError(f"rubric weights must sum to 1, got {total:g}")
        return self


class Thresholds(Part):
    """Publish thresholds from `accel.toml`."""

    pass_score: Score = 0.7
    min_pass_rate: Score = 0.8
    min_lift: float = Field(default=0.15, ge=-1, le=1)


class CaseResult(Part):
    """Grades for one case, with the skill present and absent."""

    case_id: EvalCaseId
    with_skill: Score
    without_skill: Score


class EvalReport(Contract):
    """`evals/reports/<skill>-<version>.json`."""

    skill: Slug
    version: SemVer
    generated_at: AwareDatetime
    thresholds: Thresholds = Field(default_factory=Thresholds)
    cases: list[CaseResult] = Field(min_length=1)
    pass_rate_with: Score
    pass_rate_without: Score
    lift: float = Field(ge=-1, le=1)
    stopped_early: bool = Field(
        default=False, description="True when the credit budget ended the run."
    )
    passed: bool

    @model_validator(mode="after")
    def _totals_match_cases(self) -> EvalReport:
        cut = self.thresholds.pass_score
        count = len(self.cases)
        expected_with = sum(case.with_skill >= cut for case in self.cases) / count
        expected_without = sum(case.without_skill >= cut for case in self.cases) / count
        if not math.isclose(self.pass_rate_with, expected_with, abs_tol=_TOLERANCE):
            raise ValueError(f"pass_rate_with should be {expected_with:g} from the cases")
        if not math.isclose(self.pass_rate_without, expected_without, abs_tol=_TOLERANCE):
            raise ValueError(f"pass_rate_without should be {expected_without:g} from the cases")
        if not math.isclose(self.lift, expected_with - expected_without, abs_tol=_TOLERANCE):
            raise ValueError("lift must equal pass_rate_with minus pass_rate_without")
        meets = (
            expected_with >= self.thresholds.min_pass_rate - _TOLERANCE
            and self.lift >= self.thresholds.min_lift - _TOLERANCE
            and not self.stopped_early
        )
        if self.passed != meets:
            raise ValueError(f"passed should be {str(meets).lower()} for these results")
        ids = [case.case_id for case in self.cases]
        if len(set(ids)) != len(ids):
            raise ValueError("case_id must be unique")
        return self
