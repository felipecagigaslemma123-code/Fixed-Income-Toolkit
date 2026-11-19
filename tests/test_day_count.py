"""Tests for the Treasury-adapted 30/360 day-count convention."""
from __future__ import annotations

from datetime import date

from financial_engine.day_count import days_30_360_treasury


def test_simple_full_month():
    # 15 Jan -> 15 Feb is one conventional month.
    assert days_30_360_treasury(date(2026, 1, 15), date(2026, 2, 15)) == 30


def test_full_conventional_year():
    assert days_30_360_treasury(date(2026, 1, 1), date(2027, 1, 1)) == 360


def test_starting_day_31_becomes_30():
    # 31 Jan -> 28 Feb (non-leap): d1 31->30, end is last Feb -> 30. 30*1 + 0 = 30.
    assert days_30_360_treasury(date(2025, 1, 31), date(2025, 2, 28)) == 30


def test_ending_day_31_becomes_30_when_start_is_30():
    # 30 Apr -> 31 May: d2 31->30 because d1==30. One month.
    assert days_30_360_treasury(date(2026, 4, 30), date(2026, 5, 31)) == 30


def test_ending_day_31_not_adjusted_when_start_not_30():
    # 15 May -> 31 Jul: d1=15 (not 30), so d2 stays 31. 30*2 + (31-15) = 76.
    assert days_30_360_treasury(date(2026, 5, 15), date(2026, 7, 31)) == 76


def test_last_day_february_non_leap_as_end():
    # 28 Feb 2025 (non-leap) as end -> day 30.
    assert days_30_360_treasury(date(2025, 1, 30), date(2025, 2, 28)) == 30


def test_last_day_february_leap_as_end():
    # 29 Feb 2028 (leap) as end -> day 30.
    assert days_30_360_treasury(date(2028, 1, 30), date(2028, 2, 29)) == 30


def test_last_day_february_as_start():
    # 28 Feb 2026 (non-leap) as start -> day 30; to 28 Mar -> 30*1 + (28-30) = 28.
    assert days_30_360_treasury(date(2026, 2, 28), date(2026, 3, 28)) == 28


def test_ordinary_day_30_end_not_rolled():
    # 15 Sep -> 30 Sep stays within September (no roll to October).
    assert days_30_360_treasury(date(2026, 9, 15), date(2026, 9, 30)) == 15


def test_matches_treasury_case_lecap_s30s6():
    # CASE-001 S30S6: issue 2026-03-16, maturity 2026-09-30.
    # 360*0 + 30*(9-3) + (30-16) = 180 + 14 = 194.
    assert days_30_360_treasury(date(2026, 3, 16), date(2026, 9, 30)) == 194
