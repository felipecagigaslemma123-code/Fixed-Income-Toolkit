"""Offline regression tests for A3 fixed-income pagination."""

from __future__ import annotations

import json
import os
import unittest
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from market_data.config.settings import A3ApiConfig
from market_data.models.enums import ApiEnvironment, InstrumentClass
from market_data.providers.a3mae.provider import A3MaeProvider
from market_data.providers.base import QuoteQuery


def _row(ticker: str, price: str) -> dict:
    return {
        "fecha": "2026-08-11T00:00:00",
        "ticker": ticker,
        "descripcion": "LECAP",
        "tipoEmision": "TPN",
        "segmento": "Garantizado PPT",
        "codigoSegmento": "GP",
        "plazo": "001",
        "codigoPlazo": "001",
        "moneda": "$",
        "fechaLiquidacion": "0001-01-01T00:00:00",
        "volumenAcumulado": "1",
        "montoAcumulado": "1",
        "precioUltimo": price,
        "ultimaTasa": "0",
        "precioCierreAnterior": "0",
        "precioMinimo": price,
        "precioMaximo": price,
        "openInterest": "0",
        "precioCierre": None,
        "variacion": "0",
    }


class _PagedTransport:
    def __init__(self) -> None:
        self.pages = {
            1: [_row("P{:02d}/24hs".format(i), "100") for i in range(50)],
            2: [
                _row("P49/24hs", "101"),
                _row("S15S6/24hs", "104.9000000000"),
            ],
        }
        self.requested_pages = []

    def __call__(self, url, headers, timeout):
        page = int(parse_qs(urlparse(url).query)["pageNumber"][0])
        self.requested_pages.append(page)
        return json.dumps(self.pages.get(page, []))


class A3PaginationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_key = os.environ.get("A3_MARKETDATA_API_KEY_UAT")
        os.environ["A3_MARKETDATA_API_KEY_UAT"] = "test-key"

    def tearDown(self) -> None:
        if self.previous_key is None:
            os.environ.pop("A3_MARKETDATA_API_KEY_UAT", None)
        else:
            os.environ["A3_MARKETDATA_API_KEY_UAT"] = self.previous_key

    def test_omitted_page_fetches_until_short_page_and_deduplicates_boundary(self):
        transport = _PagedTransport()
        provider = A3MaeProvider(
            A3ApiConfig(environment=ApiEnvironment.UAT), transport=transport
        )

        quotes = provider.fetch_quotes(
            QuoteQuery(instrument_class=InstrumentClass.FIXED_INCOME)
        )

        self.assertEqual(transport.requested_pages, [1, 2])
        self.assertEqual(len(quotes), 51)
        by_ticker = {quote.ticker: quote for quote in quotes}
        self.assertEqual(by_ticker["P49/24hs"].last_price, Decimal("101"))
        self.assertEqual(
            by_ticker["S15S6/24hs"].last_price, Decimal("104.9000000000")
        )

    def test_explicit_page_requests_only_that_page(self):
        transport = _PagedTransport()
        provider = A3MaeProvider(
            A3ApiConfig(environment=ApiEnvironment.UAT), transport=transport
        )

        quotes = provider.fetch_quotes(
            QuoteQuery(
                instrument_class=InstrumentClass.FIXED_INCOME, page_number=2
            )
        )

        self.assertEqual(transport.requested_pages, [2])
        self.assertEqual(len(quotes), 2)


if __name__ == "__main__":
    unittest.main()
