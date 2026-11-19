"""Local observed-futures JSON and HTML tests."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

from local_dashboard.data import futures_payload
from local_dashboard.server import create_server
from market_data.models.enums import ProviderName
from market_data.models.futures import (
    FuturesContractReference,
    FuturesTradeObservation,
)
from market_data.storage.futures_repository import SqliteFuturesRepository

_NOW = datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc)


def _seed(database):
    contract = FuturesContractReference(
        security_id="rx_DDF_DLR_AGO26",
        ticker="DLR/AGO26",
        description="Futuro de Dólar Agosto 2026",
        cfi_code="FXXXSX",
        market_id="ROFX",
        market_segment_id="DDF",
        currency="ARS",
        maturity_month_year="202608",
        source_end_date="2026-08-10",
        days_to_expiration=21,
        contract_multiplier=Decimal("1000"),
        price_precision=1,
        size_precision=0,
        min_price_increment=Decimal("0.5000"),
        settlement_type="Cash",
        underlying_id="USD",
        underlying_symbol="DLR",
        retrieved_at=_NOW,
    )
    trade = FuturesTradeObservation(
        trade_id="987654",
        security_id=contract.security_id,
        ticker=contract.ticker,
        provider_timestamp="2026-08-10T17:32:10.123Z",
        provider_timezone="UTC",
        timestamp_utc=datetime(
            2026, 8, 10, 17, 32, 10, 123000, tzinfo=timezone.utc
        ),
        price=Decimal("1509.5000"),
        volume=Decimal("2.00"),
        trade_type="Trade",
        side_codes=("Buy", "Sell"),
        seller_party=None,
        buyer_party=None,
        provider=ProviderName.A3_PUBLIC_VIEWER,
        received_at=_NOW,
    )
    with SqliteFuturesRepository(str(database)) as repository:
        repository.initialize()
        repository.save_contract_snapshot([contract])
        repository.save_trades([trade])


def test_payload_is_decimal_safe_and_does_not_substitute_missing_fields(tmp_path):
    database = tmp_path / "market.sqlite"
    _seed(database)
    payload = futures_payload(str(database))
    row = payload["contracts"][0]
    assert row["last_trade_price"] == "1509.5000"
    assert row["last_trade_volume"] == "2.00"
    assert row["contract_multiplier"] == "1000"
    assert row["settlement_price"] is None
    assert row["bid_price"] is None
    assert row["open_interest"] is None
    assert payload["financial_calculations_included"] is False
    assert payload["research_status"] == "Under Review"


def test_server_exposes_futures_page_and_api(tmp_path):
    root = Path(__file__).resolve().parent.parent
    database = tmp_path / "market.sqlite"
    _seed(database)
    server = create_server(
        root / "outputs" / "modelo_lecap_boncap.html",
        database,
        port=0,
        futures_dashboard_path=root / "outputs" / "futuros_dolar.html",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:{}".format(server.server_address[1])
    try:
        with urlopen(base + "/futures", timeout=2) as response:
            html = response.read().decode("utf-8")
        assert "Futuros de dólar" in html
        assert "/api/futures" in html
        with urlopen(base + "/api/futures", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["contracts"][0]["ticker"] == "DLR/AGO26"
        assert payload["contracts"][0]["last_trade_price"] == "1509.5000"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_html_keeps_manual_and_fifteen_minute_refresh_without_formulas():
    root = Path(__file__).resolve().parent.parent
    html = (root / "outputs" / "futuros_dolar.html").read_text(encoding="utf-8")
    assert 'id="refreshBtn"' in html
    assert "const REFRESH_INTERVAL_MS = 15*60*1000" in html
    assert "setInterval(refreshFutures,REFRESH_INTERVAL_MS)" in html
    assert "ARS por USD 1" in html
    assert "R-009 · Under Review" in html
    assert "forward_points" not in html
    assert "implied_rate" not in html
