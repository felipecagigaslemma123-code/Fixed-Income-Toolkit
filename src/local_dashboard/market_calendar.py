"""Business-day calendar used to derive the dashboard's settlement date.

This module holds the holiday set that previously lived in the dashboard HTML.
It is **not** a governed market-calendar source: the dates below were entered by
hand and are pending a documented provider, exactly as recorded in
``docs/market_conventions.md``. Moving the list here does not validate it; it
removes the second copy so a correction is applied in one place.

A wrong or missing holiday shifts the settlement date and therefore the residual
term, so the gap is material and is reported by :func:`calendar_status`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import FrozenSet

# Hand-entered national holidays, transcribed verbatim from the dashboard HTML
# (2026 plus 1 January 2027). Pending a governed calendar source.
HOLIDAYS: FrozenSet[date] = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 2, 16),
        date(2026, 2, 17),
        date(2026, 3, 24),
        date(2026, 4, 2),
        date(2026, 4, 3),
        date(2026, 5, 1),
        date(2026, 5, 25),
        date(2026, 6, 15),
        date(2026, 6, 20),
        date(2026, 7, 9),
        date(2026, 8, 17),
        date(2026, 10, 12),
        date(2026, 11, 23),
        date(2026, 12, 8),
        date(2026, 12, 25),
        date(2027, 1, 1),
    }
)

CALENDAR_STATUS = (
    "Hand-entered holiday list (2026 and 1 January 2027); no governed calendar "
    "source. Settlement dates outside this coverage are not reliable."
)

_COVERAGE_START = date(2026, 1, 1)
_COVERAGE_END = date(2027, 1, 1)


def is_business_day(day: date) -> bool:
    """Return whether ``day`` is a weekday that is not a listed holiday."""
    return day.weekday() < 5 and day not in HOLIDAYS


def next_business_day(start: date, offset: int = 1) -> date:
    """Return the business day ``offset`` days after ``start``.

    Args:
        start: The reference date (not itself counted).
        offset: Number of business days to advance. Must be >= 1.

    Returns:
        date: The resulting business day.

    Raises:
        ValueError: If ``offset`` is not a positive integer.
    """
    if offset < 1:
        raise ValueError("offset must be a positive number of business days")
    current = start
    counted = 0
    while counted < offset:
        current = current + timedelta(days=1)
        if is_business_day(current):
            counted += 1
    return current


def calendar_status(day: date) -> str:
    """Return an explicit status string for a settlement date.

    The dashboard displays this so a settlement date derived outside the
    hand-entered coverage window is never presented as if it were governed.
    """
    if _COVERAGE_START <= day <= _COVERAGE_END:
        return "covered_by_hand_entered_calendar"
    return "outside_hand_entered_calendar_coverage"
