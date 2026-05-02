"""Tracks remaining monthly Cloud TTS character budget for a single run."""


class BudgetExceeded(Exception):
    """Raised when the next chapter would exceed the remaining budget."""


class CharBudget:
    """Monotonically-decreasing in-memory budget.

    The Cloud Run Job constructs this as
    ``CharBudget(remaining=settings.MONTHLY_TTS_CHAR_LIMIT - already_used)``
    after reading the persisted monthly usage from GCS."""

    def __init__(self, remaining: int):
        if remaining < 0:
            remaining = 0
        self._initial = remaining
        self._remaining = remaining

    @property
    def remaining(self) -> int:
        return self._remaining

    @property
    def used(self) -> int:
        return self._initial - self._remaining

    def can_afford(self, n: int) -> bool:
        return n <= self._remaining

    def consume(self, n: int) -> None:
        if n > self._remaining:
            raise BudgetExceeded(
                f"requested={n} remaining={self._remaining}"
            )
        self._remaining -= n
