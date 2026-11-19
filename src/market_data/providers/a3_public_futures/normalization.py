"""Pure JSON normalization for A3's provisional public futures viewer."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from market_data.models.enums import ProviderName
from market_data.models.exceptions import NormalizationError
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)

_DLR_FUTURE = re.compile(r"^DLR/[A-Z]{3}\d{2}M?$")
_FUTURES_CFI = "FXXXSX"


def _to_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_text(value: Any, field: str) -> str:
    text = _to_text(value)
    if text is None:
        raise NormalizationError("Missing required futures field: {}".format(field))
    return text


def _to_decimal(value: Any) -> Optional[Decimal]:
    text = _to_text(value)
    if text is None:
        return None
    try:
        return Decimal(text)
    except (ArithmeticError, ValueError) as exc:
        raise NormalizationError(
            "Cannot convert futures value to Decimal: {!r}".format(value)
        ) from exc


def _to_int(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise NormalizationError("Boolean is not a valid integer count")
    try:
        decimal_value = Decimal(str(value))
        integer_value = int(decimal_value)
    except (ArithmeticError, ValueError) as exc:
        raise NormalizationError(
            "Cannot convert futures count to integer: {!r}".format(value)
        ) from exc
    if decimal_value != integer_value:
        raise NormalizationError("Expected an integer count, got {!r}".format(value))
    return integer_value


def _records(payload: Any, keys: Iterable[str], label: str) -> List[Dict[str, Any]]:
    """Extract one explicitly named record list from the observed envelopes."""
    candidate = payload
    if isinstance(candidate, dict):
        for key in keys:
            if isinstance(candidate.get(key), list):
                candidate = candidate[key]
                break
            if isinstance(candidate.get(key), dict):
                nested = candidate[key]
                for nested_key in keys:
                    if isinstance(nested.get(nested_key), list):
                        candidate = nested[nested_key]
                        break
                if isinstance(candidate, list):
                    break
    if not isinstance(candidate, list):
        raise NormalizationError("Expected a JSON list of {}".format(label))
    if not all(isinstance(row, dict) for row in candidate):
        raise NormalizationError("Every {} row must be a JSON object".format(label))
    return candidate


def _load(raw_body: str) -> Any:
    try:
        return json.loads(raw_body, parse_float=Decimal)
    except json.JSONDecodeError as exc:
        raise NormalizationError("Futures response body is not valid JSON") from exc


def _is_dlr_future(row: Dict[str, Any]) -> bool:
    ticker = _to_text(row.get("symbol"))
    return row.get("cfiCode") == _FUTURES_CFI and bool(
        ticker and _DLR_FUTURE.fullmatch(ticker)
    )


def parse_contracts(
    raw_body: str, retrieved_at: datetime
) -> Tuple[FuturesContractReference, ...]:
    """Return standard and mini DLR futures from the reference payload."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    rows = _records(
        _load(raw_body),
        ("securities", "instruments", "data", "content"),
        "contract reference",
    )
    contracts = []
    for row in rows:
        if not _is_dlr_future(row):
            continue
        contracts.append(
            FuturesContractReference(
                security_id=_required_text(row.get("id"), "id"),
                ticker=_required_text(row.get("symbol"), "symbol"),
                description=_to_text(row.get("description")),
                cfi_code=_required_text(row.get("cfiCode"), "cfiCode"),
                market_id=_to_text(row.get("marketId")),
                market_segment_id=_to_text(row.get("marketSegmentId")),
                currency=_to_text(row.get("currency")),
                maturity_month_year=_to_text(row.get("maturityMonthYear")),
                source_end_date=_to_text(row.get("endDate")),
                days_to_expiration=_to_int(row.get("daysToExpiration")),
                contract_multiplier=_to_decimal(row.get("contractMultiplier")),
                price_precision=_to_int(row.get("pricePrecision")),
                size_precision=_to_int(row.get("sizePrecision")),
                min_price_increment=_to_decimal(row.get("minPriceIncrement")),
                settlement_type=_to_text(row.get("settlementType")),
                underlying_id=_to_text(row.get("underlying")),
                underlying_symbol=_to_text(row.get("underlyingSymbol")),
                retrieved_at=retrieved_at,
            )
        )
    return tuple(
        sorted(
            contracts,
            key=lambda contract: (
                contract.days_to_expiration
                if contract.days_to_expiration is not None
                else 10**9,
                contract.ticker,
            ),
        )
    )


def _timestamp(value: Any) -> Tuple[str, datetime]:
    original = _required_text(value, "timestamp")
    normalized = original[:-1] + "+00:00" if original.endswith("Z") else original
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise NormalizationError(
            "Invalid futures trade timestamp: {!r}".format(original)
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NormalizationError("Futures trade timestamp must include a timezone")
    return original, parsed.astimezone(timezone.utc)


def _side_codes(value: Any) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        values = []
        for item in value:
            text = _to_text(item)
            if text is not None:
                values.append(text)
        return tuple(values)
    text = _to_text(value)
    return () if text is None else (text,)


def parse_trades(
    raw_body: str,
    contract: FuturesContractReference,
    received_at: datetime,
) -> Tuple[FuturesTradeObservation, ...]:
    """Normalize recent trades without deriving a daily market snapshot."""
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("received_at must be timezone-aware")
    rows = _records(_load(raw_body), ("trades", "data", "content"), "trade")
    trades = []
    for row in rows:
        provider_timestamp, timestamp_utc = _timestamp(row.get("timestamp"))
        security_id = _required_text(
            row.get("securityId") or contract.security_id, "securityId"
        )
        if security_id != contract.security_id:
            raise NormalizationError(
                "Trade securityId does not match requested contract"
            )
        trades.append(
            FuturesTradeObservation(
                trade_id=_required_text(row.get("id"), "id"),
                security_id=security_id,
                ticker=contract.ticker,
                provider_timestamp=provider_timestamp,
                provider_timezone="UTC",
                timestamp_utc=timestamp_utc,
                price=_to_decimal(row.get("price")),
                volume=_to_decimal(row.get("volume")),
                trade_type=_to_text(row.get("type")),
                side_codes=_side_codes(row.get("sides")),
                seller_party=_to_text(row.get("sellerParty")),
                buyer_party=_to_text(row.get("buyerParty")),
                provider=ProviderName.A3_PUBLIC_VIEWER,
                received_at=received_at,
            )
        )
    return tuple(sorted(trades, key=lambda trade: trade.timestamp_utc))
