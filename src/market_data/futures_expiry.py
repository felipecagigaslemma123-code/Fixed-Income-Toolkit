"""Resolve a DLR futures contract's expiry date.

Priority (most reliable first):

1. the provider's own end date (``endDate`` / ``source_end_date``) — the contract
   runs until expiry, so when the source publishes this date it is used exactly
   (method ``PROVIDER_END_DATE``);
2. otherwise the market convention: the **last business day of the contract
   month** derived from ``maturityMonthYear`` (method
   ``CONVENTION_LAST_BUSINESS_DAY``);
3. otherwise ``None`` (method ``UNRESOLVED``).

Owner decision (2026-08-10, amended): deriving the expiry *date* is permitted —
it is a contractual/market date, not a rate, forward point or any R-009 pricing
calculation, which remain out of scope.

Caveat: the last-business-day fallback steps back over weekends only. It does not
apply a holiday calendar, so on a month ending on a holiday it may be one or two
days late. The provider ``endDate`` (method 1) is exact and always preferred; a
holiday-aware calendar is a future refinement for method 2.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Optional, Tuple

PROVIDER_END_DATE = "provider-end-date"
CONVENTION_LAST_BUSINESS_DAY = "convention-last-business-day"
UNRESOLVED = "unresolved"

_MONTH_YEAR_RE = re.compile(r"^(\d{4})-?(\d{2})$")


def last_business_day_of_month(year: int, month: int) -> date:
    """Return the last weekday (Mon–Fri) of the given month.

    Does not account for holidays; see the module caveat.
    """
    last_day = calendar.monthrange(year, month)[1]
    day = date(year, month, last_day)
    while day.weekday() >= 5:  # Saturday=5, Sunday=6
        day -= timedelta(days=1)
    return day


def _parse_iso_date(text: Optional[str]) -> Optional[date]:
    if not text:
        return None
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def _parse_month_year(text: Optional[str]) -> Optional[Tuple[int, int]]:
    if not text:
        return None
    match = _MONTH_YEAR_RE.match(str(text).strip())
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return year, month


def resolve_futures_expiry(
    maturity_month_year: Optional[str],
    source_end_date: Optional[str],
) -> Tuple[Optional[date], str]:
    """Resolve a contract's expiry date and report how it was resolved.

    Args:
        maturity_month_year: Provider ``maturityMonthYear`` (e.g. ``"202608"``).
        source_end_date: Provider ``endDate`` string, if present.

    Returns:
        ``(expiry_date, method)``. ``method`` is one of ``PROVIDER_END_DATE``,
        ``CONVENTION_LAST_BUSINESS_DAY`` or ``UNRESOLVED``. ``expiry_date`` is
        ``None`` only when ``method`` is ``UNRESOLVED``.
    """
    provider_date = _parse_iso_date(source_end_date)
    if provider_date is not None:
        return provider_date, PROVIDER_END_DATE

    month_year = _parse_month_year(maturity_month_year)
    if month_year is not None:
        return last_business_day_of_month(*month_year), CONVENTION_LAST_BUSINESS_DAY

    return None, UNRESOLVED
