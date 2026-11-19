"""Tests for DLR futures expiry resolution (provider endDate -> convention -> none)."""
from __future__ import annotations

from datetime import date

from market_data.futures_expiry import (
    CONVENTION_LAST_BUSINESS_DAY,
    PROVIDER_END_DATE,
    UNRESOLVED,
    last_business_day_of_month,
    resolve_futures_expiry,
)


def test_last_business_day_weekday_end():
    # 31 Aug 2026 is a Monday -> unchanged.
    assert last_business_day_of_month(2026, 8) == date(2026, 8, 31)


def test_last_business_day_steps_back_over_weekend():
    # 28 Feb 2026 is a Saturday -> 27 Feb (Friday).
    assert last_business_day_of_month(2026, 2) == date(2026, 2, 27)
    # 31 May 2026 is a Sunday -> 29 May (Friday).
    assert last_business_day_of_month(2026, 5) == date(2026, 5, 29)


def test_provider_end_date_takes_priority():
    expiry, method = resolve_futures_expiry("202608", "2026-08-31T00:00:00")
    assert expiry == date(2026, 8, 31)
    assert method == PROVIDER_END_DATE


def test_provider_end_date_used_even_if_differs_from_convention():
    # If the provider publishes an exact date, it wins over the month convention.
    expiry, method = resolve_futures_expiry("202605", "2026-05-28")
    assert expiry == date(2026, 5, 28)
    assert method == PROVIDER_END_DATE


def test_convention_fallback_when_no_end_date():
    expiry, method = resolve_futures_expiry("202605", None)
    assert expiry == date(2026, 5, 29)
    assert method == CONVENTION_LAST_BUSINESS_DAY


def test_convention_accepts_dashed_month_year():
    expiry, method = resolve_futures_expiry("2027-01", None)
    assert expiry == date(2027, 1, 29)
    assert method == CONVENTION_LAST_BUSINESS_DAY


def test_unresolved_when_nothing_parseable():
    expiry, method = resolve_futures_expiry(None, None)
    assert expiry is None
    assert method == UNRESOLVED

    expiry, method = resolve_futures_expiry("garbage", "also-garbage")
    assert expiry is None
    assert method == UNRESOLVED
