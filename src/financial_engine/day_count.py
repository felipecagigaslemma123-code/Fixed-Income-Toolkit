"""Treasury-adapted 30/360 day-count convention.

Implements the project-approved convention documented in
``docs/market_conventions.md`` (v1.3), which is the human-approved adaptation of
the U.S./NASD 30/360 rule for Argentine capitalizable Treasury instruments:

- a starting day 31 becomes 30;
- an ending day 31 becomes 30 when the adjusted starting day is 30;
- the last calendar day of February (28 in a non-leap year, 29 in a leap year)
  becomes conventional day 30, both as a starting date and as an ending date;
- ordinary day-30 dates remain day 30 (an ending 30 is not rolled into the next
  month).

This convention is validated for LECAP/BONCAP residual-term and maturity-value
calculations. It must not be silently generalized to other instrument families.
"""

from __future__ import annotations

import calendar
from datetime import date


def _is_last_day_of_february(day: date) -> bool:
    """Return ``True`` if ``day`` is the last calendar day of February."""
    if day.month != 2:
        return False
    last_day = 29 if calendar.isleap(day.year) else 28
    return day.day == last_day


def days_30_360_treasury(start: date, end: date) -> int:
    """Return the number of days between two dates under Treasury 30/360.

    Args:
        start: The earlier date (inclusive lower bound).
        end: The later date (exclusive upper bound in the count sense).

    Returns:
        The signed day count ``360*(y2-y1) + 30*(m2-m1) + (d2-d1)`` after applying
        the day-adjustment rules. Positive when ``end`` is after ``start``.
    """
    d1 = start.day
    d2 = end.day

    # Starting-date adjustments.
    if _is_last_day_of_february(start):
        d1 = 30
    elif d1 == 31:
        d1 = 30

    # Ending-date adjustments.
    if _is_last_day_of_february(end):
        d2 = 30
    elif d2 == 31 and d1 == 30:
        d2 = 30

    return 360 * (end.year - start.year) + 30 * (end.month - start.month) + (d2 - d1)
