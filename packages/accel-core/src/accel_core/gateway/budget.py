"""Token and cost budgets, per call and per run."""

from __future__ import annotations

from dataclasses import dataclass

from accel_core.errors import BudgetExceeded


@dataclass(frozen=True)
class Budget:
    """Limits on tokens (prompt plus completion) and cost in US dollars. None means no limit."""

    max_tokens: int | None = None
    max_cost_usd: float | None = None

    def __post_init__(self) -> None:
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.max_cost_usd is not None and self.max_cost_usd <= 0:
            raise ValueError("max_cost_usd must be positive")


def check(budget: Budget, tokens: int, cost_usd: float, scope: str) -> None:
    """Raise BudgetExceeded if `tokens` or `cost_usd` is over `budget`."""
    if budget.max_tokens is not None and tokens > budget.max_tokens:
        raise BudgetExceeded(f"{scope} used {tokens} tokens; the budget is {budget.max_tokens}")
    if budget.max_cost_usd is not None and cost_usd > budget.max_cost_usd:
        raise BudgetExceeded(
            f"{scope} cost ${cost_usd:.4f}; the budget is ${budget.max_cost_usd:.4f}"
        )


class RunBudget:
    """Tracks spend across every call in one run, such as one batch playbook."""

    def __init__(self, budget: Budget) -> None:
        self.budget = budget
        self.tokens = 0
        self.cost_usd = 0.0

    def remaining_tokens(self) -> int | None:
        """Tokens left, or None if tokens are unlimited."""
        if self.budget.max_tokens is None:
            return None
        return max(self.budget.max_tokens - self.tokens, 0)

    def ensure_available(self) -> None:
        """Raise BudgetExceeded if the run has nothing left to spend."""
        if self.remaining_tokens() == 0:
            raise BudgetExceeded(f"The run has used its {self.budget.max_tokens}-token budget")
        if self.budget.max_cost_usd is not None and self.cost_usd >= self.budget.max_cost_usd:
            raise BudgetExceeded(f"The run has used its ${self.budget.max_cost_usd:.4f} budget")

    def add(self, tokens: int, cost_usd: float) -> None:
        """Record one call's spend, then raise BudgetExceeded if the run is over budget."""
        self.tokens += tokens
        self.cost_usd += cost_usd
        check(self.budget, self.tokens, self.cost_usd, "The run")
