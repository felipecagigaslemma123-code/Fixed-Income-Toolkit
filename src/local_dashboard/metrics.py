"""Dashboard metrics computed by the validated financial engine.

The dashboard HTML used to re-implement the R-001 to R-005 formulas in
JavaScript with binary floating point, in parallel with the Decimal engine in
``src/financial_engine``. That second implementation is removed: this module is
the single calculation path, and the HTML only renders what it returns.

This module performs no IO. It orchestrates the engine and applies two
dashboard-level rules that are presentation policy rather than financial
methodology:

* the settlement date (provider-reported when the price is aligned, otherwise
  T+1 from the business-day calendar); and
* the temporal-alignment guard of ``docs/local_dashboard.md``: yield metrics
  exist only when the price observation date equals the selected trade date.

No formula is defined here. Every financial value comes from the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, Optional

from financial_engine.day_count import days_30_360_treasury
from financial_engine.duration import DurationInput, calculate_duration
from financial_engine.letras_yield import LetraYieldInput, calculate_letra_yield
from financial_engine.maturity_value import (
    InstrumentType,
    MaturityValueInput,
    calculate_maturity_value,
)
from local_dashboard.market_calendar import calendar_status, next_business_day

_DAYS_YEAR_30_360 = Decimal(360)

#: Research records behind each exposed value, disclosed on every response.
METHODOLOGY = {
    "maturity_value": "R-001",
    "holding_period_return": "R-002",
    "tna": "R-003",
    "tea": "R-004",
    "tem": "R-004",
    "duration": "R-005",
}


class MetricsRequestError(ValueError):
    """Raised when a metrics request cannot be interpreted."""


@dataclass(frozen=True)
class DashboardMetricsInput:
    """Immutable inputs for one dashboard row or calculator evaluation.

    Attributes:
        instrument_type: LECAP or BONCAP.
        issue_date: Contractual issue date.
        maturity_date: Contractual maturity date.
        monthly_issue_rate: Monthly capitalization rate from the auction.
        market_price: Selected secondary-market price, per VN 100.
        trade_date: Purchase date selected by the user.
        price_date: Observation date of the selected price, when known.
        provider_settlement_date: Settlement date reported by the provider.
        compounding_frequency: Periods per year for Modified Duration.
    """

    instrument_type: InstrumentType
    issue_date: date
    maturity_date: date
    monthly_issue_rate: Decimal
    market_price: Decimal
    trade_date: date
    price_date: Optional[date] = None
    provider_settlement_date: Optional[date] = None
    compounding_frequency: int = 12


@dataclass(frozen=True)
class DashboardMetricsResult:
    """Immutable result for one dashboard row.

    Yield-dependent values are ``None`` when the temporal-alignment guard is not
    satisfied; ``yield_unavailable_reason`` always states why.
    """

    settlement_date: date
    settlement_source: str
    settlement_calendar_status: str
    life_days_30_360: int
    residual_days_30_360: int
    residual_days_actual: int
    maturity_value: Decimal
    macaulay_years: Optional[Decimal]
    yield_available: bool
    yield_unavailable_reason: Optional[str]
    holding_period_return: Optional[Decimal] = None
    tea: Optional[Decimal] = None
    tem: Optional[Decimal] = None
    tna: Optional[Decimal] = None
    modified_duration: Optional[Decimal] = None
    periodic_yield: Optional[Decimal] = None


def compute_dashboard_metrics(data: DashboardMetricsInput) -> DashboardMetricsResult:
    """Compute one row's metrics through the validated engine.

    Args:
        data: Contractual data, the selected price and the selected dates.

    Returns:
        DashboardMetricsResult: Maturity value and residual terms always;
        yield and Modified Duration only when price and trade dates align.

    Raises:
        MetricsRequestError: If settlement is not before maturity, or the
            engine rejects the contractual inputs.
    """
    aligned = data.price_date is not None and data.price_date == data.trade_date
    if aligned and data.provider_settlement_date is not None:
        settlement = data.provider_settlement_date
        settlement_source = "provider"
    else:
        settlement = next_business_day(data.trade_date, 1)
        settlement_source = "calendar_t_plus_1"

    try:
        maturity = calculate_maturity_value(
            MaturityValueInput(
                instrument_type=data.instrument_type,
                issue_date=data.issue_date,
                maturity_date=data.maturity_date,
                monthly_issue_rate=data.monthly_issue_rate,
                reference_face_value=Decimal(100),
                # The dashboard has no published official VPV to compare against;
                # only `maturity_value` is consumed from this result.
                official_maturity_value=Decimal(0),
                source_reference="local dashboard contractual dataset",
            )
        )
    except Exception as exc:  # engine validation is the authority
        raise MetricsRequestError(str(exc)) from exc

    life_days = days_30_360_treasury(data.issue_date, data.maturity_date)
    residual_30_360 = days_30_360_treasury(settlement, data.maturity_date)
    residual_actual = (data.maturity_date - settlement).days

    if not aligned:
        reason = (
            "price observation date does not match the selected trade date"
            if data.price_date is not None
            else "selected price has no observation date"
        )
    elif residual_actual <= 0:
        reason = "instrument matured on or before the settlement date"
    else:
        reason = None

    macaulay: Optional[Decimal] = None
    if residual_30_360 > 0 and settlement < data.maturity_date:
        # Macaulay duration of a single final payment is the residual term; it
        # does not depend on the yield. Calling the engine with TEA = 0 returns
        # it without re-deriving `days_30_360 / 360` here. The accompanying
        # modified duration is meaningless at TEA = 0 and is discarded.
        macaulay = calculate_duration(
            DurationInput(
                settlement_date=settlement,
                maturity_date=data.maturity_date,
                tea=Decimal(0),
                compounding_frequency=data.compounding_frequency,
                source_reference="local dashboard — Macaulay only",
            )
        ).macaulay_years

    if reason is not None:
        return DashboardMetricsResult(
            settlement_date=settlement,
            settlement_source=settlement_source,
            settlement_calendar_status=calendar_status(settlement),
            life_days_30_360=life_days,
            residual_days_30_360=residual_30_360,
            residual_days_actual=residual_actual,
            maturity_value=maturity.maturity_value,
            macaulay_years=macaulay,
            yield_available=False,
            yield_unavailable_reason=reason,
        )

    try:
        yield_result = calculate_letra_yield(
            LetraYieldInput(
                market_price=data.market_price,
                settlement_date=settlement,
                maturity_date=data.maturity_date,
                maturity_value=maturity.maturity_value,
                source_reference="local dashboard selected price",
            )
        )
        duration_result = calculate_duration(
            DurationInput(
                settlement_date=settlement,
                maturity_date=data.maturity_date,
                tea=yield_result.tea,
                compounding_frequency=data.compounding_frequency,
                source_reference="local dashboard selected price",
            )
        )
    except Exception as exc:  # engine validation is the authority
        raise MetricsRequestError(str(exc)) from exc

    return DashboardMetricsResult(
        settlement_date=settlement,
        settlement_source=settlement_source,
        settlement_calendar_status=calendar_status(settlement),
        life_days_30_360=life_days,
        residual_days_30_360=residual_30_360,
        residual_days_actual=yield_result.residual_days_actual,
        maturity_value=maturity.maturity_value,
        macaulay_years=duration_result.macaulay_years,
        yield_available=True,
        yield_unavailable_reason=None,
        holding_period_return=yield_result.holding_period_return,
        tea=yield_result.tea,
        tem=yield_result.tem,
        tna=yield_result.tna,
        modified_duration=duration_result.modified_duration,
        periodic_yield=duration_result.periodic_yield,
    )


def _text(value: Optional[Decimal]) -> Optional[str]:
    """Serialize a Decimal at full precision; never through binary float."""
    return None if value is None else format(value, "f")


def _required(params: Mapping[str, str], name: str) -> str:
    value = params.get(name)
    if value is None or value == "":
        raise MetricsRequestError("missing parameter: {}".format(name))
    return value


def _as_date(raw: str, name: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise MetricsRequestError("invalid date for {}".format(name)) from exc


def _as_decimal(raw: str, name: str) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise MetricsRequestError("invalid number for {}".format(name)) from exc


def metrics_payload(params: Mapping[str, str]) -> Dict[str, Any]:
    """Build the ``/api/metrics`` JSON payload from query parameters.

    Every financial value is serialized as a string or ``null``; no financial
    value passes through binary floating point, per the dashboard contract.

    Raises:
        MetricsRequestError: If a parameter is missing or cannot be parsed.
    """
    type_raw = params.get("type", "LECAP").strip().upper()
    try:
        instrument_type = InstrumentType[type_raw]
    except KeyError as exc:
        raise MetricsRequestError("unsupported instrument type") from exc

    frequency_raw = params.get("m", "12")
    try:
        frequency = int(frequency_raw)
    except ValueError as exc:
        raise MetricsRequestError("invalid compounding frequency") from exc

    price_date_raw = params.get("price_date") or None
    settlement_raw = params.get("settlement") or None

    result = compute_dashboard_metrics(
        DashboardMetricsInput(
            instrument_type=instrument_type,
            issue_date=_as_date(_required(params, "issue"), "issue"),
            maturity_date=_as_date(_required(params, "maturity"), "maturity"),
            monthly_issue_rate=_as_decimal(_required(params, "tem"), "tem"),
            market_price=_as_decimal(_required(params, "price"), "price"),
            trade_date=_as_date(_required(params, "trade"), "trade"),
            price_date=_as_date(price_date_raw, "price_date") if price_date_raw else None,
            provider_settlement_date=(
                _as_date(settlement_raw, "settlement") if settlement_raw else None
            ),
            compounding_frequency=frequency,
        )
    )

    return {
        "settlement_date": result.settlement_date.isoformat(),
        "settlement_source": result.settlement_source,
        "settlement_calendar_status": result.settlement_calendar_status,
        "life_days_30_360": result.life_days_30_360,
        "residual_days_30_360": result.residual_days_30_360,
        "residual_days_actual": result.residual_days_actual,
        "maturity_value": _text(result.maturity_value),
        "holding_period_return": _text(result.holding_period_return),
        "tea": _text(result.tea),
        "tem": _text(result.tem),
        "tna": _text(result.tna),
        "macaulay_years": _text(result.macaulay_years),
        "modified_duration": _text(result.modified_duration),
        "periodic_yield": _text(result.periodic_yield),
        "compounding_frequency": frequency,
        "yield_available": result.yield_available,
        "yield_unavailable_reason": result.yield_unavailable_reason,
        "methodology": METHODOLOGY,
    }
