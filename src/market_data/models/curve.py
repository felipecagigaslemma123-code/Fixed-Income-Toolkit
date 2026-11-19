"""Curve models: futures curve and FX forward curve.

The FX forward curve is modeled separately from the futures curve to keep the
three forward concepts distinct (per ``bibliography_review_2026-08-06.md``):
FX forward price, forward interest rate and value of an existing forward must not
share one name or one function.

Derived rate fields stay ``None`` with a :class:`MethodologyStatus` until the
relevant Research Gate (R-009) is approved for production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

from market_data.models.enums import MethodologyStatus, ProviderName


@dataclass(frozen=True)
class CurvePoint:
    """One maturity point of a futures curve.

    Attributes:
        ticker: Contract ticker.
        maturity_date: Contract maturity.
        days_to_maturity: Calendar days from the valuation date to maturity.
        price: Selected price for the point (see ``PriceType``).
        implied_rate: Derived rate; ``None`` until the Research Gate is open.
        methodology_status: Research status of ``implied_rate``.
    """

    ticker: str
    maturity_date: date
    days_to_maturity: int
    price: Decimal
    implied_rate: Optional[Decimal]
    methodology_status: MethodologyStatus


@dataclass(frozen=True)
class FuturesCurve:
    """A futures curve ordered by maturity."""

    valuation_date: date
    underlying_asset: str
    points: Tuple[CurvePoint, ...]
    provider: ProviderName


@dataclass(frozen=True)
class FxForwardPoint:
    """One maturity point of the FX forward view (R-009).

    ``forward_points`` is the observed comparison ``future_price - spot`` (trivial
    arithmetic, no interest-rate curves). ``implied_devaluation`` is the
    theoretical-parity result and stays ``None`` + ``UNDER_REVIEW`` until R-009
    closes with production approval.
    """

    ticker: str
    maturity_date: date
    spot: Decimal
    future_price: Decimal
    forward_points: Decimal
    implied_devaluation: Optional[Decimal]
    methodology_status: MethodologyStatus


@dataclass(frozen=True)
class FxForwardCurve:
    """FX forward view over a set of maturities.

    Attributes:
        valuation_date: Valuation date of the view.
        underlying_asset: Underlying identifier, e.g. ``"USD"``.
        points: Forward points ordered by maturity.
        provider: Provider that supplied the futures prices.
        futures_as_forward_disclaimer: Mandatory label — the futures-as-forward
            treatment is an approximation "Under Review" (R-009).
    """

    valuation_date: date
    underlying_asset: str
    points: Tuple[FxForwardPoint, ...]
    provider: ProviderName
    futures_as_forward_disclaimer: str
