"""Tests for the SQLite repository: round-trip, Decimal integrity, upsert, history."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from market_data.models.enums import InstrumentClass, ProviderName
from market_data.models.quote import MarketQuote
from market_data.storage import MarketDataRepository, SqliteRepository


def _quote(ticker="AE38", market_date=date(2024, 11, 15), last="759.65", term="000"):
    return MarketQuote(
        ticker=ticker,
        description="desc",
        issue_type="TPN",
        segment="Bilateral TRD",
        segment_code="BT",
        term=term,
        term_code=term,
        currency="$",
        market_date=market_date,
        settlement_date=None,
        last_price=Decimal(last),
        close_price=Decimal(last),
        previous_close=Decimal("0"),
        min_price=Decimal("755"),
        max_price=Decimal(last),
        provider_rate=Decimal("0"),
        accumulated_volume=Decimal("14811266"),
        accumulated_amount=Decimal("11235165909"),
        open_interest=Decimal("0"),
        variation=Decimal("0.07"),
        bid=None,
        ask=None,
        instrument_class=InstrumentClass.FIXED_INCOME,
        provider=ProviderName.A3,
        retrieved_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def repo():
    r = SqliteRepository(":memory:")
    r.initialize()
    yield r
    r.close()


def test_satisfies_protocol(repo):
    assert isinstance(repo, MarketDataRepository)


def test_round_trip_preserves_decimal(repo):
    saved = repo.save_quotes([_quote()])
    assert saved == 1
    result = repo.get_quotes("AE38", date(2024, 11, 1), date(2024, 11, 30))
    assert len(result) == 1
    q = result[0]
    assert q.last_price == Decimal("759.65")
    assert isinstance(q.last_price, Decimal)
    assert q.accumulated_amount == Decimal("11235165909")
    assert q.variation == Decimal("0.07")
    assert q.settlement_date is None
    assert q.term == "000"
    assert q.instrument_class is InstrumentClass.FIXED_INCOME
    assert q.provider is ProviderName.A3


def test_upsert_same_natural_key_replaces(repo):
    repo.save_quotes([_quote(last="759.65")])
    repo.save_quotes([_quote(last="761.00")])  # same ticker/term/date/provider
    result = repo.get_quotes("AE38", date(2024, 11, 1), date(2024, 11, 30))
    assert len(result) == 1  # not duplicated
    assert result[0].last_price == Decimal("761.00")


def test_history_accumulates_across_dates(repo):
    repo.save_quotes(
        [
            _quote(market_date=date(2024, 11, 15), last="759.65"),
            _quote(market_date=date(2024, 11, 18), last="762.00"),
            _quote(market_date=date(2024, 11, 19), last="763.50"),
        ]
    )
    result = repo.get_quotes("AE38", date(2024, 11, 1), date(2024, 11, 30))
    assert [q.market_date for q in result] == [
        date(2024, 11, 15),
        date(2024, 11, 18),
        date(2024, 11, 19),
    ]


def test_date_range_filter(repo):
    repo.save_quotes(
        [
            _quote(market_date=date(2024, 11, 15)),
            _quote(market_date=date(2024, 11, 25)),
        ]
    )
    result = repo.get_quotes("AE38", date(2024, 11, 20), date(2024, 11, 30))
    assert len(result) == 1
    assert result[0].market_date == date(2024, 11, 25)


def test_get_latest_quotes_returns_most_recent_per_ticker(repo):
    repo.save_quotes(
        [
            _quote(ticker="AE38", market_date=date(2024, 11, 15), last="700"),
            _quote(ticker="AE38", market_date=date(2024, 11, 19), last="763.50"),
            _quote(ticker="AL30", market_date=date(2024, 11, 18), last="500"),
        ]
    )
    latest = repo.get_latest_quotes(InstrumentClass.FIXED_INCOME)
    by_ticker = {q.ticker: q for q in latest}
    assert by_ticker["AE38"].last_price == Decimal("763.50")
    assert by_ticker["AL30"].last_price == Decimal("500")


def test_get_tickers(repo):
    repo.save_quotes([_quote(ticker="AE38"), _quote(ticker="AL30")])
    assert repo.get_tickers(InstrumentClass.FIXED_INCOME) == ("AE38", "AL30")


def test_save_empty_is_noop(repo):
    assert repo.save_quotes([]) == 0


def test_persists_to_file(tmp_path):
    db = tmp_path / "market.sqlite"
    r1 = SqliteRepository(str(db))
    r1.initialize()
    r1.save_quotes([_quote()])
    r1.close()

    r2 = SqliteRepository(str(db))  # reopen same file
    result = r2.get_quotes("AE38", date(2024, 11, 1), date(2024, 11, 30))
    r2.close()
    assert len(result) == 1
    assert result[0].last_price == Decimal("759.65")
