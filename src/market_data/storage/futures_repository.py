"""SQLite persistence for observed dollar-futures contracts and trades.

Financial values are stored as ``TEXT`` and reconstructed directly as
``Decimal``. The repository keeps raw observations only; it does not aggregate
or calculate financial metrics.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence, Tuple

from market_data.models.enums import ProviderName
from market_data.models.exceptions import RepositoryIntegrityError, StorageError
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS futures_contracts (
    security_id           TEXT PRIMARY KEY,
    ticker                TEXT NOT NULL UNIQUE,
    description           TEXT,
    cfi_code              TEXT NOT NULL,
    market_id             TEXT,
    market_segment_id     TEXT,
    currency              TEXT,
    maturity_month_year   TEXT,
    source_end_date       TEXT,
    days_to_expiration    INTEGER,
    contract_multiplier   TEXT,
    price_precision       INTEGER,
    size_precision        INTEGER,
    min_price_increment   TEXT,
    settlement_type       TEXT,
    underlying_id         TEXT,
    underlying_symbol     TEXT,
    first_seen_at         TEXT NOT NULL,
    last_seen_at          TEXT NOT NULL,
    is_active             INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_futures_contracts_active_expiry
    ON futures_contracts (is_active, days_to_expiration, ticker);

CREATE TABLE IF NOT EXISTS futures_trades (
    trade_id              TEXT NOT NULL,
    security_id           TEXT NOT NULL,
    ticker                TEXT NOT NULL,
    provider_timestamp    TEXT NOT NULL,
    provider_timezone     TEXT NOT NULL,
    timestamp_utc         TEXT NOT NULL,
    price                 TEXT,
    volume                TEXT,
    trade_type            TEXT,
    side_codes_json       TEXT NOT NULL,
    seller_party          TEXT,
    buyer_party           TEXT,
    provider              TEXT NOT NULL,
    received_at           TEXT NOT NULL,
    PRIMARY KEY (trade_id, security_id),
    FOREIGN KEY (security_id) REFERENCES futures_contracts (security_id)
);

CREATE INDEX IF NOT EXISTS idx_futures_trades_security_timestamp
    ON futures_trades (security_id, timestamp_utc DESC);
"""

_CONTRACT_COLUMNS = (
    "security_id",
    "ticker",
    "description",
    "cfi_code",
    "market_id",
    "market_segment_id",
    "currency",
    "maturity_month_year",
    "source_end_date",
    "days_to_expiration",
    "contract_multiplier",
    "price_precision",
    "size_precision",
    "min_price_increment",
    "settlement_type",
    "underlying_id",
    "underlying_symbol",
    "first_seen_at",
    "last_seen_at",
    "is_active",
)

_TRADE_COLUMNS = (
    "trade_id",
    "security_id",
    "ticker",
    "provider_timestamp",
    "provider_timezone",
    "timestamp_utc",
    "price",
    "volume",
    "trade_type",
    "side_codes_json",
    "seller_party",
    "buyer_party",
    "provider",
    "received_at",
)


def _decimal_to_text(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else format(value, "f")


def _text_to_decimal(value: Optional[str]) -> Optional[Decimal]:
    return None if value is None else Decimal(value)


class SqliteFuturesRepository:
    """Persist complete contract snapshots and immutable trade observations."""

    def __init__(self, database_path: str) -> None:
        try:
            self._conn = sqlite3.connect(database_path, timeout=10)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA busy_timeout = 10000;")
        except sqlite3.Error as exc:
            raise StorageError("Cannot open futures database: {}".format(exc)) from exc

    def __enter__(self) -> "SqliteFuturesRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def initialize(self) -> None:
        try:
            with self._conn:
                self._conn.executescript(_SCHEMA)
                self._conn.execute("PRAGMA optimize;")
        except sqlite3.Error as exc:
            raise StorageError("Cannot initialize futures schema: {}".format(exc)) from exc

    @staticmethod
    def _contract_values(contract: FuturesContractReference) -> Tuple[object, ...]:
        first_seen = contract.first_seen_at or contract.retrieved_at
        return (
            contract.security_id,
            contract.ticker,
            contract.description,
            contract.cfi_code,
            contract.market_id,
            contract.market_segment_id,
            contract.currency,
            contract.maturity_month_year,
            contract.source_end_date,
            contract.days_to_expiration,
            _decimal_to_text(contract.contract_multiplier),
            contract.price_precision,
            contract.size_precision,
            _decimal_to_text(contract.min_price_increment),
            contract.settlement_type,
            contract.underlying_id,
            contract.underlying_symbol,
            first_seen.isoformat(),
            contract.retrieved_at.isoformat(),
            1,
        )

    def save_contract_snapshot(
        self, contracts: Sequence[FuturesContractReference]
    ) -> int:
        """Upsert a complete non-empty listing and deactivate absent rows."""
        if not contracts:
            return 0
        placeholders = ", ".join("?" for _ in _CONTRACT_COLUMNS)
        mutable_columns = _CONTRACT_COLUMNS[1:17] + ("last_seen_at", "is_active")
        assignments = ", ".join(
            "{0}=excluded.{0}".format(column) for column in mutable_columns
        )
        sql = (
            "INSERT INTO futures_contracts ({columns}) VALUES ({placeholders}) "
            "ON CONFLICT(security_id) DO UPDATE SET {assignments}"
        ).format(
            columns=", ".join(_CONTRACT_COLUMNS),
            placeholders=placeholders,
            assignments=assignments,
        )
        try:
            with self._conn:
                self._conn.execute("UPDATE futures_contracts SET is_active = 0")
                self._conn.executemany(
                    sql, [self._contract_values(contract) for contract in contracts]
                )
            return len(contracts)
        except sqlite3.Error as exc:
            raise RepositoryIntegrityError(
                "Failed to persist futures contracts: {}".format(exc)
            ) from exc

    @staticmethod
    def _row_to_contract(row: sqlite3.Row) -> FuturesContractReference:
        data = dict(row)
        return FuturesContractReference(
            security_id=data["security_id"],
            ticker=data["ticker"],
            description=data["description"],
            cfi_code=data["cfi_code"],
            market_id=data["market_id"],
            market_segment_id=data["market_segment_id"],
            currency=data["currency"],
            maturity_month_year=data["maturity_month_year"],
            source_end_date=data["source_end_date"],
            days_to_expiration=data["days_to_expiration"],
            contract_multiplier=_text_to_decimal(data["contract_multiplier"]),
            price_precision=data["price_precision"],
            size_precision=data["size_precision"],
            min_price_increment=_text_to_decimal(data["min_price_increment"]),
            settlement_type=data["settlement_type"],
            underlying_id=data["underlying_id"],
            underlying_symbol=data["underlying_symbol"],
            retrieved_at=datetime.fromisoformat(data["last_seen_at"]),
            is_active=bool(data["is_active"]),
            first_seen_at=datetime.fromisoformat(data["first_seen_at"]),
        )

    def get_contracts(
        self, active_only: bool = True
    ) -> Tuple[FuturesContractReference, ...]:
        sql = "SELECT * FROM futures_contracts"
        params: Tuple[object, ...] = ()
        if active_only:
            sql += " WHERE is_active = ?"
            params = (1,)
        sql += " ORDER BY COALESCE(days_to_expiration, 2147483647), ticker"
        try:
            return tuple(
                self._row_to_contract(row)
                for row in self._conn.execute(sql, params).fetchall()
            )
        except sqlite3.Error as exc:
            raise StorageError("Futures contract query failed: {}".format(exc)) from exc

    @staticmethod
    def _trade_values(trade: FuturesTradeObservation) -> Tuple[object, ...]:
        return (
            trade.trade_id,
            trade.security_id,
            trade.ticker,
            trade.provider_timestamp,
            trade.provider_timezone,
            trade.timestamp_utc.isoformat(),
            _decimal_to_text(trade.price),
            _decimal_to_text(trade.volume),
            trade.trade_type,
            json.dumps(
                list(trade.side_codes), ensure_ascii=False, separators=(",", ":")
            ),
            trade.seller_party,
            trade.buyer_party,
            trade.provider.value,
            trade.received_at.isoformat(),
        )

    def save_trades(self, trades: Sequence[FuturesTradeObservation]) -> int:
        """Insert new immutable trades and ignore provider duplicates."""
        if not trades:
            return 0
        placeholders = ", ".join("?" for _ in _TRADE_COLUMNS)
        sql = "INSERT OR IGNORE INTO futures_trades ({}) VALUES ({})".format(
            ", ".join(_TRADE_COLUMNS), placeholders
        )
        before = self._conn.total_changes
        try:
            with self._conn:
                self._conn.executemany(sql, [self._trade_values(t) for t in trades])
            return self._conn.total_changes - before
        except sqlite3.Error as exc:
            raise RepositoryIntegrityError(
                "Failed to persist futures trades: {}".format(exc)
            ) from exc

    @staticmethod
    def _row_to_trade(row: sqlite3.Row) -> FuturesTradeObservation:
        data = dict(row)
        return FuturesTradeObservation(
            trade_id=data["trade_id"],
            security_id=data["security_id"],
            ticker=data["ticker"],
            provider_timestamp=data["provider_timestamp"],
            provider_timezone=data["provider_timezone"],
            timestamp_utc=datetime.fromisoformat(data["timestamp_utc"]),
            price=_text_to_decimal(data["price"]),
            volume=_text_to_decimal(data["volume"]),
            trade_type=data["trade_type"],
            side_codes=tuple(json.loads(data["side_codes_json"])),
            seller_party=data["seller_party"],
            buyer_party=data["buyer_party"],
            provider=ProviderName(data["provider"]),
            received_at=datetime.fromisoformat(data["received_at"]),
        )

    def get_trade_history(
        self, security_id: str, limit: Optional[int] = None
    ) -> Tuple[FuturesTradeObservation, ...]:
        sql = (
            "SELECT * FROM futures_trades WHERE security_id = ? "
            "ORDER BY timestamp_utc DESC, trade_id DESC"
        )
        params: Tuple[object, ...] = (security_id,)
        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be positive")
            sql += " LIMIT ?"
            params = (security_id, limit)
        try:
            return tuple(
                self._row_to_trade(row)
                for row in self._conn.execute(sql, params).fetchall()
            )
        except sqlite3.Error as exc:
            raise StorageError("Futures trade query failed: {}".format(exc)) from exc

    def get_latest_trade(
        self, security_id: str
    ) -> Optional[FuturesTradeObservation]:
        history = self.get_trade_history(security_id, limit=1)
        return history[0] if history else None

    def trade_count(self) -> int:
        try:
            row = self._conn.execute("SELECT COUNT(*) FROM futures_trades").fetchone()
            return int(row[0])
        except sqlite3.Error as exc:
            raise StorageError("Futures trade count failed: {}".format(exc)) from exc
