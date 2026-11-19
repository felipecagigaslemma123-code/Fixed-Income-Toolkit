"""Decimal-safe JSON views over the Toolkit's local SQLite repositories.

This module only serializes stored observations and lifecycle evidence. It does
not select a price, calculate a yield or promote an instrument's validation
state. Decimal values remain strings all the way to the browser.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from market_data.calculation_eligibility import calculation_eligibility
from market_data.futures_expiry import resolve_futures_expiry
from market_data.models.enums import InstrumentClass
from market_data.models.instrument_lifecycle import InstrumentLifecycleDecision
from market_data.models.quote import MarketQuote
from market_data.storage.lifecycle_repository import SqliteLifecycleRepository
from market_data.storage.sqlite_repository import SqliteRepository
from market_data.storage.futures_repository import SqliteFuturesRepository

JsonScalar = Union[str, int, bool, None]
JsonObject = Dict[str, Union[JsonScalar, List[Dict[str, JsonScalar]]]]


def _decimal(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else format(value, "f")


def _quote_view(quote: MarketQuote) -> Dict[str, JsonScalar]:
    return {
        "ticker": quote.ticker,
        "description": quote.description,
        "instrument_class": quote.instrument_class.value,
        "issue_type": quote.issue_type,
        "segment": quote.segment,
        "segment_code": quote.segment_code,
        "term": quote.term,
        "term_code": quote.term_code,
        "currency": quote.currency,
        "market_date": quote.market_date.isoformat(),
        "settlement_date": (
            None if quote.settlement_date is None else quote.settlement_date.isoformat()
        ),
        "last_price": _decimal(quote.last_price),
        "close_price": _decimal(quote.close_price),
        "provider_rate": _decimal(quote.provider_rate),
        "accumulated_volume": _decimal(quote.accumulated_volume),
        "accumulated_amount": _decimal(quote.accumulated_amount),
        "open_interest": _decimal(quote.open_interest),
        "variation": _decimal(quote.variation),
        "provider": quote.provider.value,
        "retrieved_at": quote.retrieved_at.isoformat(),
    }


def _lifecycle_view(
    decision: InstrumentLifecycleDecision,
) -> Dict[str, JsonScalar]:
    candidate = decision.candidate
    evidence = decision.activation_evidence
    calculable, calculation_reason = calculation_eligibility(
        candidate.instrument_family
    )
    return {
        "source_id": candidate.source_id,
        "origin": candidate.origin.value,
        "description": candidate.description,
        "official_ticker": candidate.ticker,
        "instrument_family": (
            None
            if candidate.instrument_family is None
            else candidate.instrument_family.value
        ),
        "calculation_eligible": calculable,
        "calculation_reason": calculation_reason,
        "currency": candidate.currency,
        "maturity_date": (
            None if candidate.maturity_date is None else candidate.maturity_date.isoformat()
        ),
        "auction_date": candidate.auction_date.isoformat(),
        "issue_action": candidate.issue_action,
        "source_url": candidate.source_url,
        "source_title": candidate.source_title,
        "manual_reference": candidate.manual_reference,
        "lifecycle_status": decision.status.value,
        "match_method": decision.match_method.value,
        "matched_ticker": decision.matched_ticker,
        "activation_provider": None if evidence is None else evidence.provider.value,
        "activation_market_date": (
            None if evidence is None else evidence.market_date.isoformat()
        ),
        "activation_retrieved_at": (
            None if evidence is None else evidence.retrieved_at.isoformat()
        ),
        "evaluated_at": decision.evaluated_at.isoformat(),
    }


_REQUIRED_SETTLEMENT_TERM = "001"  # 24h settlement — consistent secondary price/rate


def market_quotes_payload(database_path: str) -> JsonObject:
    """Return latest 24h (`plazo` 001) fixed-income observations, Decimal-safe.

    Only the required settlement term is returned, so consumers never mix
    immediate settlement (`000`) with 24h (`001`) when reading "today's price".
    """
    with SqliteRepository(database_path) as repository:
        repository.initialize()
        quotes = repository.get_latest_quotes(InstrumentClass.FIXED_INCOME)
    quotes = tuple(
        quote for quote in quotes if quote.term == _REQUIRED_SETTLEMENT_TERM
    )
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "price_selection_is_explicit": True,
        "silent_price_fallback": False,
        "required_settlement_term": _REQUIRED_SETTLEMENT_TERM,
        "quotes": [_quote_view(quote) for quote in quotes],
    }


def lifecycle_payload(database_path: str) -> JsonObject:
    """Return stored discovery and activation states without re-evaluating them."""
    with SqliteLifecycleRepository(database_path) as repository:
        repository.initialize()
        decisions = repository.get_all()
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operational_state_is_not_financial_validation": True,
        "instruments": [_lifecycle_view(decision) for decision in decisions],
    }


def futures_payload(database_path: str) -> Dict[str, Any]:
    """Return observed DLR contracts/trades without calculated market fields."""
    with SqliteFuturesRepository(database_path) as repository:
        repository.initialize()
        contracts = repository.get_contracts(active_only=True)
        rows = []
        for contract in contracts:
            trade = repository.get_latest_trade(contract.security_id)
            maturity_date, maturity_source = resolve_futures_expiry(
                contract.maturity_month_year, contract.source_end_date
            )
            rows.append(
                {
                    "security_id": contract.security_id,
                    "ticker": contract.ticker,
                    "description": contract.description,
                    "is_mini": contract.is_mini,
                    "cfi_code": contract.cfi_code,
                    "market_id": contract.market_id,
                    "market_segment_id": contract.market_segment_id,
                    "currency": contract.currency,
                    "price_basis": "ARS_PER_USD_1",
                    "maturity_month_year": contract.maturity_month_year,
                    "source_end_date": contract.source_end_date,
                    "maturity_date": (
                        None if maturity_date is None else maturity_date.isoformat()
                    ),
                    "maturity_source": maturity_source,
                    "days_to_expiration": contract.days_to_expiration,
                    "contract_multiplier": _decimal(contract.contract_multiplier),
                    "price_precision": contract.price_precision,
                    "size_precision": contract.size_precision,
                    "min_price_increment": _decimal(contract.min_price_increment),
                    "settlement_type": contract.settlement_type,
                    "underlying_id": contract.underlying_id,
                    "underlying_symbol": contract.underlying_symbol,
                    "first_seen_at": (
                        None
                        if contract.first_seen_at is None
                        else contract.first_seen_at.isoformat()
                    ),
                    "last_seen_at": contract.retrieved_at.isoformat(),
                    "last_trade_id": None if trade is None else trade.trade_id,
                    "last_trade_price": (
                        None if trade is None else _decimal(trade.price)
                    ),
                    "last_trade_volume": (
                        None if trade is None else _decimal(trade.volume)
                    ),
                    "last_trade_type": None if trade is None else trade.trade_type,
                    "last_trade_timestamp_original": (
                        None if trade is None else trade.provider_timestamp
                    ),
                    "last_trade_timezone": (
                        None if trade is None else trade.provider_timezone
                    ),
                    "last_trade_timestamp_utc": (
                        None if trade is None else trade.timestamp_utc.isoformat()
                    ),
                    "received_at": (
                        None if trade is None else trade.received_at.isoformat()
                    ),
                    "bid_volume": None,
                    "bid_price": None,
                    "ask_price": None,
                    "ask_volume": None,
                    "variation": None,
                    "variation_percent": None,
                    "contract_volume": None,
                    "nominal_volume": None,
                    "settlement_price": None,
                    "previous_settlement_price": None,
                    "low_price": None,
                    "high_price": None,
                    "open_interest": None,
                }
            )
        trade_count = repository.trade_count()
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "A3_PUBLIC_VIEWER",
        "source_status": "Prototype",
        "observation_status": "Observed",
        "research_id": "R-009",
        "research_status": "Under Review",
        "observed_only": True,
        "spot_included": False,
        "financial_calculations_included": False,
        "silent_price_fallback": False,
        "trade_count": trade_count,
        "contracts": rows,
    }
