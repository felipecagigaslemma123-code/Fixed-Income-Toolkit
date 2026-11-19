"""Offline tests for official Treasury result-page normalization."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from market_data.models.enums import AuctionValueUnit, TreasuryInstrumentFamily
from market_data.providers.treasury.normalization import (
    parse_result_candidates,
    parse_result_notices,
)

_LISTING = """
<html><body>
  <a href="/noticias/resultado-de-la-licitacion-1">
    <time datetime="2026-07-29 17:27:06">29 de julio de 2026</time>
    <h3>Resultado de la licitación de instrumentos del Tesoro</h3>
  </a>
  <a href="/noticias/llamado-a-licitacion-1">
    <time datetime="2026-07-27 17:19:00">27 de julio de 2026</time>
    <h3>Llamado a licitación de instrumentos del Tesoro</h3>
  </a>
</body></html>
"""

_ARTICLE = """
<html><head>
  <meta property="og:title" content="Resultado oficial de la licitación" />
  <meta property="article:published_time" content="2026-07-29T17:27:06-03:00" />
</head><body>
<table>
  <thead><tr>
    <th>Instrumento a Tasa Fija</th>
    <th>VNO Ofertado (*)</th>
    <th>VNO Adjudicado (*)</th>
    <th>TEM de corte por cada VNO $ 1.000</th>
    <th>TIREA</th>
  </tr></thead>
  <tbody><tr>
    <td>LETRA DEL TESORO NACIONAL CAPITALIZABLE EN PESOS CON VENCIMIENTO 16 DE OCTUBRE DE 2026 (nueva)</td>
    <td>$ 5.079.718</td><td>$ 4.612.305</td><td>2,05 % (**)</td><td>27,57%</td>
  </tr></tbody>
</table>
<table>
  <thead><tr><th>Instrumento Dólar Linked</th><th>Precio de corte</th></tr></thead>
  <tbody>
    <tr><td>LETRA DEL TESORO NACIONAL VINCULADA AL DÓLAR ESTADOUNIDENSE CERO CUPÓN CON VENCIMIENTO 30 DE SEPTIEMBRE DE 2026 (D30S6 - reapertura)</td><td>USD 988,41</td></tr>
    <tr><td>BONO DEL TESORO NACIONAL EN DÓLARES CON VENCIMIENTO 2029 (AO29 - reapertura)</td><td>USD 945,00</td></tr>
    <tr><td>BONO DEL TESORO NACIONAL CAPITALIZABLE EN PESOS CON VENCIMIENTO 30 DE JUNIO DE 2027 (T30J7 - reapertura)</td><td>$ 1.245,50</td></tr>
    <tr><td>BONO DE LA PROVINCIA DE BUENOS AIRES CON VENCIMIENTO 2030 (PBA30)</td><td>$ 900,00</td></tr>
  </tbody>
</table>
</body></html>
"""

_RETRIEVED = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)


class TreasuryNormalizationTests(unittest.TestCase):
    def test_listing_keeps_only_result_notices(self):
        notices = parse_result_notices(
            _LISTING, "https://www.argentina.gob.ar/economia/finanzas/noticias"
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(
            notices[0].title,
            "Resultado de la licitación de instrumentos del Tesoro",
        )
        self.assertEqual(notices[0].publication_date, date(2026, 7, 29))
        self.assertEqual(
            notices[0].url,
            "https://www.argentina.gob.ar/noticias/resultado-de-la-licitacion-1",
        )

    def test_article_extracts_national_treasury_only_and_preserves_raw_fields(self):
        candidates = parse_result_candidates(
            _ARTICLE,
            "https://www.argentina.gob.ar/noticias/resultado-de-la-licitacion-1",
            _RETRIEVED,
        )
        self.assertEqual(len(candidates), 4)

        new_lecap = candidates[0]
        self.assertIsNone(new_lecap.ticker)
        self.assertIs(new_lecap.instrument_family, TreasuryInstrumentFamily.LECAP)
        self.assertEqual(new_lecap.currency, "ARS")
        self.assertEqual(new_lecap.maturity_date, date(2026, 10, 16))
        self.assertEqual(new_lecap.issue_action, "NUEVA")
        self.assertEqual(new_lecap.auction_date, date(2026, 7, 29))
        self.assertEqual(new_lecap.source_title, "Resultado oficial de la licitación")
        self.assertEqual(new_lecap.discovered_at, _RETRIEVED)

        fields = {field.header: field for field in new_lecap.source_fields}
        self.assertEqual(fields["VNO Adjudicado (*)"].raw_value, "$ 4.612.305")
        self.assertEqual(fields["VNO Adjudicado (*)"].decimal_value, Decimal("4612305"))
        self.assertIs(fields["VNO Adjudicado (*)"].unit, AuctionValueUnit.ARS)
        tem = fields["TEM de corte por cada VNO $ 1.000"]
        self.assertEqual(tem.raw_value, "2,05 % (**)")
        self.assertEqual(tem.decimal_value, Decimal("2.05"))
        self.assertIs(tem.unit, AuctionValueUnit.PERCENT)

        reopening = candidates[1]
        self.assertEqual(reopening.ticker, "D30S6")
        self.assertIs(reopening.instrument_family, TreasuryInstrumentFamily.LELINK)
        self.assertEqual(reopening.currency, "USD")
        self.assertEqual(reopening.maturity_date, date(2026, 9, 30))
        self.assertEqual(reopening.issue_action, "REAPERTURA")
        self.assertEqual(reopening.source_fields[1].decimal_value, Decimal("988.41"))
        self.assertEqual(reopening.source_fields[1].raw_value, "USD 988,41")

        generic_bond = candidates[2]
        self.assertEqual(generic_bond.ticker, "AO29")
        self.assertIs(
            generic_bond.instrument_family,
            TreasuryInstrumentFamily.TREASURY_BOND,
        )
        self.assertIsNone(generic_bond.maturity_date)

        boncap = candidates[3]
        self.assertEqual(boncap.ticker, "T30J7")
        self.assertIs(boncap.instrument_family, TreasuryInstrumentFamily.BONCAP)
        self.assertEqual(boncap.currency, "ARS")
        self.assertEqual(boncap.maturity_date, date(2027, 6, 30))
        self.assertNotIn("PROVINCIA", " ".join(item.description for item in candidates))

    def test_no_financial_value_is_a_float(self):
        candidates = parse_result_candidates(
            _ARTICLE, "https://example.test/result", _RETRIEVED
        )
        for candidate in candidates:
            for field in candidate.source_fields:
                self.assertTrue(
                    field.decimal_value is None
                    or isinstance(field.decimal_value, Decimal)
                )
                self.assertNotIsInstance(field.decimal_value, float)


if __name__ == "__main__":
    unittest.main()
