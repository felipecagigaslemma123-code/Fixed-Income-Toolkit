"""Duration for single-payment Treasury Bills (letras).

Implements the Research R-005 methodology, approved for production by the project
owner on 2026-08-11, for a letra treated as a single final cash flow:

    Macaulay (years)   = DAYS360_TREASURY(settlement, maturity) / 360
    periodic_yield     = (1 + TEA) ** (1 / m) - 1
    Modified Duration  = Macaulay / (1 + periodic_yield)

For a single-payment instrument the Macaulay duration equals the time to
maturity. ``m`` is the compounding/annualization frequency per year and must be
disclosed on every result (R-005). This module is pure: no IO, Decimal only.

Scope: single-payment letras (LECAP/LEDE-style). Coupon-bearing bonds require a
present-value-weighted, multi-cash-flow duration, which is a separate, not-yet-
approved research item.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

from financial_engine.day_count import days_30_360_treasury

_WORKING_PRECISION = 50
_METHODOLOGY_STATUS = (
    "R-005 Validated — Implementation Approved (owner, 2026-08-11)"
)
_DAYS_YEAR = Decimal(360)


class DurationError(Exception):
    """Base class for all duration domain errors."""


class InvalidDurationDatesError(DurationError):
    """Raised when settlement/maturity dates are missing or inconsistent."""


class InvalidYieldInputError(DurationError):
    """Raised when the effective annual yield is out of range (TEA <= -1)."""


class InvalidFrequencyError(DurationError):
    """Raised when the compounding frequency is not a positive integer."""


@dataclass(frozen=True)
class DurationInput:
    """Immutable inputs to compute a letra's duration.

    Attributes:
        settlement_date: Settlement date of the trade.
        maturity_date: Instrument maturity date.
        tea: Effective annual yield (TEA) as a Decimal, e.g. from
            :mod:`financial_engine.letras_yield`.
        compounding_frequency: Periods per year ``m`` for the modified-duration
            periodic yield (e.g. 1 for annual, 12 for monthly). Disclosed on the
            result.
        source_reference: Human-readable citation for the inputs.
    """

    settlement_date: date
    maturity_date: date
    tea: Decimal
    compounding_frequency: int
    source_reference: str


@dataclass(frozen=True)
class DurationResult:
    """Immutable result of a duration computation.

    Attributes:
        macaulay_years: Macaulay duration in years (time to maturity).
        macaulay_days_30_360: Residual term settlement→maturity (30/360 days).
        modified_duration: Modified duration (years), for the disclosed frequency.
        periodic_yield: The periodic yield ``(1+TEA)^(1/m)-1`` used.
        compounding_frequency: The disclosed frequency ``m``.
        methodology_status: Research status recorded on the result.
    """

    macaulay_years: Decimal
    macaulay_days_30_360: int
    modified_duration: Decimal
    periodic_yield: Decimal
    compounding_frequency: int
    methodology_status: str


def calculate_duration(data: DurationInput) -> DurationResult:
    """Compute Macaulay and Modified duration for a single-payment letra.

    Args:
        data: The validated inputs describing the instrument and its yield.

    Returns:
        DurationResult: Macaulay and Modified duration with the disclosed
        frequency.

    Raises:
        InvalidDurationDatesError: If settlement is not before maturity.
        InvalidYieldInputError: If ``tea <= -1`` (``1 + TEA`` non-positive).
        InvalidFrequencyError: If ``compounding_frequency`` is not >= 1.
    """
    if data.settlement_date >= data.maturity_date:
        raise InvalidDurationDatesError(
            "Settlement date must be earlier than maturity date."
        )
    if data.tea <= Decimal(-1):
        raise InvalidYieldInputError("TEA must be greater than -1.")
    if data.compounding_frequency < 1:
        raise InvalidFrequencyError("Compounding frequency must be >= 1.")

    days = days_30_360_treasury(data.settlement_date, data.maturity_date)
    if days <= 0:
        raise InvalidDurationDatesError("Residual 30/360 term must be positive.")

    with localcontext() as context:
        context.prec = _WORKING_PRECISION
        macaulay_years = Decimal(days) / _DAYS_YEAR
        one_plus_tea = Decimal(1) + data.tea
        periodic_yield = one_plus_tea ** (Decimal(1) / Decimal(data.compounding_frequency)) - Decimal(1)
        modified_duration = macaulay_years / (Decimal(1) + periodic_yield)

    return DurationResult(
        macaulay_years=macaulay_years,
        macaulay_days_30_360=days,
        modified_duration=modified_duration,
        periodic_yield=periodic_yield,
        compounding_frequency=data.compounding_frequency,
        methodology_status=_METHODOLOGY_STATUS,
    )
