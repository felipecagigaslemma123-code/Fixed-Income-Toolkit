"""SQLite implementation of :class:`MarketDataRepository`.

Uses only the standard-library ``sqlite3`` module (no extra dependency).

Decimal integrity: every price/amount is stored as ``TEXT`` and read back with
``Decimal(str(...))``. No ``REAL``/binary float is ever used, honoring the
project Decimal-only policy end to end.

History model: one row per natural key
``(ticker, instrument_class, term, market_date, provider)``. Re-saving the same
key replaces it with the newer observation (the daily figures accumulate during
the session), so history builds up across market dates without duplicates.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Sequence, Tuple

from market_data.models.enums import InstrumentClass, ProviderName
from market_data.models.exceptions import RepositoryIntegrityError, StorageError
from market_data.models.quote import MarketQuote

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    ticker             TEXT NOT NULL,
    instrument_class   TEXT NOT NULL,
    term               TEXT NOT NULL DEFAULT '',
    market_date        TEXT NOT NULL,          -- ISO date
    provider           TEXT NOT NULL,
    description        TEXT,
    issue_type         TEXT,
    segment            TEXT,
    segment_code       TEXT,
    term_code          TEXT,
    currency           TEXT,
    settlement_date    TEXT,                   -- ISO date or NULL
    last_price         TEXT,                   -- Decimal as TEXT
    close_price        TEXT,
    previous_close     TEXT,
    min_price          TEXT,
    max_price          TEXT,
    provider_rate      TEXT,
    accumulated_volume TEXT,
    accumulated_amount TEXT,
    open_interest      TEXT,
    variation          TEXT,
    bid                TEXT,
    ask                TEXT,
    retrieved_at       TEXT NOT NULL,          -- ISO datetime
    PRIMARY KEY (ticker, instrument_class, term, market_date, provider)
);
CREATE INDEX IF NOT EXISTS idx_quotes_class_date
    ON quotes (instrument_class, market_date);
"""

# Column order used for both INSERT and SELECT round-trips.
_COLUMNS = (
    "ticker", "instrument_class", "term", "market_date", "provider",
    "description", "issue_type", "segment", "segment_code", "term_code",
    "currency", "settlement_date", "last_price", "close_price", "previous_close",
    "min_price", "max_price", "provider_rate", "accumulated_volume",
    "accumulated_amount", "open_interest", "variation", "bid", "ask",
    "retrieved_at",
)


def _dec_to_text(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else str(value)


def _text_to_dec(value: Optional[str]) -> Optional[Decimal]:
    return None if value is None else Decimal(value)


def _date_to_text(value: Optional[date]) -> Optional[str]:
    return None if value is None else value.isoformat()


def _text_to_date(value: Optional[str]) -> Optional[date]:
    return None if value is None else date.fromisoformat(value)


class SqliteRepository:
    """Persist and query market quotes in a SQLite database."""

    def __init__(self, database_path: str):
        """Initialize the repository with a single persistent connection.

        A persistent connection keeps ``:memory:`` databases usable across calls
        and avoids leaking connections. Not shared across threads.

        Args:
            database_path: Filesystem path to the SQLite file, or ``":memory:"``.
        """
        self._database_path = database_path
        try:
            self._conn = sqlite3.connect(database_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as exc:
            raise StorageError("Cannot open database: {}".format(exc)) from exc

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> "SqliteRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def initialize(self) -> None:
        """Create the schema if it does not exist (idempotent)."""
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def _row_values(self, q: MarketQuote) -> Tuple:
        return (
            q.ticker,
            q.instrument_class.value,
            q.term or "",
            q.market_date.isoformat(),
            q.provider.value,
            q.description,
            q.issue_type,
            q.segment,
            q.segment_code,
            q.term_code,
            q.currency,
            _date_to_text(q.settlement_date),
            _dec_to_text(q.last_price),
            _dec_to_text(q.close_price),
            _dec_to_text(q.previous_close),
            _dec_to_text(q.min_price),
            _dec_to_text(q.max_price),
            _dec_to_text(q.provider_rate),
            _dec_to_text(q.accumulated_volume),
            _dec_to_text(q.accumulated_amount),
            _dec_to_text(q.open_interest),
            _dec_to_text(q.variation),
            _dec_to_text(q.bid),
            _dec_to_text(q.ask),
            q.retrieved_at.isoformat(),
        )

    def save_quotes(self, quotes: Sequence[MarketQuote]) -> int:
        """Upsert quotes by natural key. Returns the number written."""
        if not quotes:
            return 0
        placeholders = ", ".join(["?"] * len(_COLUMNS))
        sql = "INSERT OR REPLACE INTO quotes ({cols}) VALUES ({ph})".format(
            cols=", ".join(_COLUMNS), ph=placeholders
        )
        rows = [self._row_values(q) for q in quotes]
        try:
            with self._conn:
                self._conn.executemany(sql, rows)
            return len(rows)
        except sqlite3.Error as exc:
            raise RepositoryIntegrityError(
                "Failed to persist quotes: {}".format(exc)
            ) from exc

    def _row_to_quote(self, row: sqlite3.Row) -> MarketQuote:
        d = dict(row)
        return MarketQuote(
            ticker=d["ticker"],
            description=d["description"],
            issue_type=d["issue_type"],
            segment=d["segment"],
            segment_code=d["segment_code"],
            term=d["term"] or None,
            term_code=d["term_code"],
            currency=d["currency"],
            market_date=_text_to_date(d["market_date"]),
            settlement_date=_text_to_date(d["settlement_date"]),
            last_price=_text_to_dec(d["last_price"]),
            close_price=_text_to_dec(d["close_price"]),
            previous_close=_text_to_dec(d["previous_close"]),
            min_price=_text_to_dec(d["min_price"]),
            max_price=_text_to_dec(d["max_price"]),
            provider_rate=_text_to_dec(d["provider_rate"]),
            accumulated_volume=_text_to_dec(d["accumulated_volume"]),
            accumulated_amount=_text_to_dec(d["accumulated_amount"]),
            open_interest=_text_to_dec(d["open_interest"]),
            variation=_text_to_dec(d["variation"]),
            bid=_text_to_dec(d["bid"]),
            ask=_text_to_dec(d["ask"]),
            instrument_class=InstrumentClass(d["instrument_class"]),
            provider=ProviderName(d["provider"]),
            retrieved_at=datetime.fromisoformat(d["retrieved_at"]),
        )

    def _query(self, sql: str, params: Tuple) -> Tuple[MarketQuote, ...]:
        try:
            cursor = self._conn.execute(sql, params)
            return tuple(self._row_to_quote(r) for r in cursor.fetchall())
        except sqlite3.Error as exc:
            raise StorageError("Query failed: {}".format(exc)) from exc

    def get_quotes(
        self,
        ticker: str,
        start: date,
        end: date,
        instrument_class: Optional[InstrumentClass] = None,
    ) -> Tuple[MarketQuote, ...]:
        """Return stored quotes for a ticker within a market-date range."""
        sql = (
            "SELECT * FROM quotes WHERE ticker = ? "
            "AND market_date >= ? AND market_date <= ?"
        )
        params = [ticker, start.isoformat(), end.isoformat()]
        if instrument_class is not None:
            sql += " AND instrument_class = ?"
            params.append(instrument_class.value)
        sql += " ORDER BY market_date ASC"
        return self._query(sql, tuple(params))

    def get_latest_quotes(
        self, instrument_class: InstrumentClass
    ) -> Tuple[MarketQuote, ...]:
        """Return the most recent quote per ticker for a segment."""
        sql = (
            "SELECT * FROM quotes WHERE instrument_class = ? "
            "AND market_date = (SELECT MAX(market_date) FROM quotes q2 "
            "WHERE q2.ticker = quotes.ticker "
            "AND q2.instrument_class = quotes.instrument_class) "
            "ORDER BY ticker ASC"
        )
        return self._query(sql, (instrument_class.value,))

    def get_tickers(self, instrument_class: InstrumentClass) -> Tuple[str, ...]:
        """Return the distinct tickers stored for a segment."""
        try:
            cursor = self._conn.execute(
                "SELECT DISTINCT ticker FROM quotes WHERE instrument_class = ? "
                "ORDER BY ticker ASC",
                (instrument_class.value,),
            )
            return tuple(r[0] for r in cursor.fetchall())
        except sqlite3.Error as exc:
            raise StorageError("Query failed: {}".format(exc)) from exc
