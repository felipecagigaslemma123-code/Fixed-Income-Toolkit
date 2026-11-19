"""Secondary-market yield calculator for Treasury Bills (letras), IAMC convention.

Given a date-aligned secondary-market price and the instrument's maturity value
(VPV), compute the Holding Period Return and its annualizations following the
**official IAMC fixed-income convention**, verified against the BYMA/IAMC daily
report (S16O6, 10 August 2026 — see
``docs/research/iamc_yield_methodology_validation_2026-08-11.md``):

    residual_days = calendar days from settlement to maturity (ACTUAL/365)
    HPR   = maturity_value / market_price - 1
    TEA   = (1 + HPR) ** (365 / residual_days) - 1      (TIREA, effective annual)
    TEM   = (1 + TEA) ** (1 / 12) - 1                    (effective monthly)
    TNA   = TEM * 12                                     (nominal annual, monthly comp.)

Important convention notes:

- The residual term uses **actual calendar days** on a **365-day basis**, which
  is what IAMC/BYMA publish for the secondary-market yield. This is different
  from the Treasury-adapted 30/360 convention, which applies **only** to the
  maturity value (VPV, issue→maturity) in :mod:`financial_engine.maturity_value`.
- ``TNA = TEM * 12`` is the nominal annual rate compounded monthly — this is the
  IAMC definition. The previous "simple annualization" ``HPR * 360 / days30360``
  was found NOT to reproduce the published IAMC TNA and has been replaced.

Temporal alignment between the provider observation and the requested
current-rate date is an orchestration precondition documented in
``docs/financial_specification.md``; a historical price must never be silently
relabeled as current. This module is pure: no IO, no provider access, Decimal
only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

_WORKING_PRECISION = 50
_METHODOLOGY_STATUS = (
    "R-002/R-003/R-004 IAMC convention (ACT/365, TNA=TEMx12) - reproduced against "
    "BYMA/IAMC S16O6 (2026-08-10). Implementation Approved (owner, 2026-08-11)"
)

_DAYS_YEAR_ACTUAL = Decimal(365)
_MONTHS_YEAR = Decimal(12)


class LetrasYieldError(Exception):
    """Base class for all letras-yield domain errors."""


class InvalidPriceError(LetrasYieldError):
    """Raised when the market price is missing or non-positive."""


class InvalidMaturityValueError(LetrasYieldError):
    """Raised when the maturity value is missing or non-positive."""


class InvalidYieldDatesError(LetrasYieldError):
    """Raised when settlement/maturity dates are missing or inconsistent."""


@dataclass(frozen=True)
class LetraYieldInput:
    """Immutable inputs to compute a letra's secondary-market yield.

    Attributes:
        market_price: Current secondary-market price (per the same nominal basis
            as ``maturity_value``), as a Decimal.
        settlement_date: Settlement date of the trade (e.g. the 24h settlement
            date reported by the provider).
        maturity_date: Instrument maturity date.
        maturity_value: Maturity value (VPV) on the same nominal basis as the
            price, as a Decimal.
        source_reference: Human-readable citation for the price/instrument data.
    """

    market_price: Decimal
    settlement_date: date
    maturity_date: date
    maturity_value: Decimal
    source_reference: str


@dataclass(frozen=True)
class LetraYieldResult:
    """Immutable result of a letra yield computation (IAMC convention).

    Attributes:
        holding_period_return: HPR over the residual period.
        tna: Nominal annual rate = ``TEM * 12`` (monthly compounding).
        tea: Effective annual rate / TIREA (ACT/365 compound).
        tem: Effective monthly rate ``(1+TEA)^(1/12)-1``.
        residual_days_actual: Actual calendar days settlement→maturity.
        methodology_status: Research status recorded on the result.
    """

    holding_period_return: Decimal
    tna: Decimal
    tea: Decimal
    tem: Decimal
    residual_days_actual: int
    methodology_status: str


def calculate_letra_yield(data: LetraYieldInput) -> LetraYieldResult:
    """Compute HPR, TNA, TEA and TEM for a letra from its current price (IAMC).

    Args:
        data: The validated inputs describing the trade and instrument.

    Returns:
        LetraYieldResult: The computed returns and residual term.

    Raises:
        InvalidPriceError: If ``market_price`` is not positive.
        InvalidMaturityValueError: If ``maturity_value`` is not positive.
        InvalidYieldDatesError: If ``settlement_date`` is not before
            ``maturity_date`` (non-positive residual term).
    """
    if data.market_price <= 0:
        raise InvalidPriceError("Market price must be positive.")
    if data.maturity_value <= 0:
        raise InvalidMaturityValueError("Maturity value must be positive.")
    if data.settlement_date >= data.maturity_date:
        raise InvalidYieldDatesError(
            "Settlement date must be earlier than maturity date."
        )

    residual_days = (data.maturity_date - data.settlement_date).days
    if residual_days <= 0:
        raise InvalidYieldDatesError("Residual term (actual days) must be positive.")

    with localcontext() as context:
        context.prec = _WORKING_PRECISION
        days_decimal = Decimal(residual_days)
        hpr = data.maturity_value / data.market_price - Decimal(1)
        tea = (Decimal(1) + hpr) ** (_DAYS_YEAR_ACTUAL / days_decimal) - Decimal(1)
        tem = (Decimal(1) + tea) ** (Decimal(1) / _MONTHS_YEAR) - Decimal(1)
        tna = tem * _MONTHS_YEAR

    return LetraYieldResult(
        holding_period_return=hpr,
        tna=tna,
        tea=tea,
        tem=tem,
        residual_days_actual=residual_days,
        methodology_status=_METHODOLOGY_STATUS,
    )
