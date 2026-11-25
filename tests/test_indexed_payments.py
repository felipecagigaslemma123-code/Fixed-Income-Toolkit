"""Indexed-payment regressions moved from Cartera; original expected values retained."""

import copy
import json
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from financial_engine.cash_flows import iamc_schedule
from financial_engine.indexed import bcra_series
from market_data.providers.bcra import read_rem

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HOY = date(2026, 11, 13)


class Base(unittest.TestCase):
    def setUp(self):
        capture = json.loads((FIXTURES / "bcra/bcra-2026-11-13.json").read_text())
        self.indices = {key: bcra_series(capture, key) for key in ("cer", "a3500", "tamar_tna")}
        self.indices.update(rem=read_rem(FIXTURES / "bcra/rem-tablas-2026-10.xlsx"),
                            feriados={}, inflacion={}, tamar={}, tc={})
        self.cierre = json.loads((FIXTURES / "iamc/cierres/2026-11-05.json").read_text())


class BaseDelA3500(Base):
    """IAMC expresa los flujos DL al A3500 de su bloque macro, no siempre el del día del cierre."""

    def cierre_tzv28(self, fecha_macro):
        cierre = copy.deepcopy(self.cierre)
        fila = next(f for f in cierre["calculadora_bonos"]["ins"] if f["tk"] == "TZV28")
        fila["f"] = [[3, 100.0, 0.0, 0.0]]  # liquidación 06/11, pago 09/11, referencia 04/11
        for variable in cierre["macro"]["vars"]:
            if variable["k"] == "a3500":
                variable["f"] = fecha_macro
        return cierre, Decimal(str(fila["fxc"]))

    def pago(self, cierre):
        contrato = {"tipo": "A3500", "rezago_habiles": 3, "fuente": "fixture"}
        return iamc_schedule(cierre, "TZV28", "tp", contrato=contrato, indices=self.indices, avisos=[]).pagos[0]

    def test_usa_el_a3500_de_la_fecha_que_informa_iamc(self):
        cierre, fxc = self.cierre_tzv28("2026-11-04")
        self.assertAlmostEqual(self.pago(cierre).total, 100 * fxc, places=20)

    def test_con_la_fecha_del_cierre_aplica_la_variacion(self):
        cierre, fxc = self.cierre_tzv28("2026-11-05")
        a = self.indices["a3500"]
        esperado = 100 * fxc * a[date(2026, 11, 4)] / a[date(2026, 11, 5)]
        self.assertAlmostEqual(self.pago(cierre).total, esperado, places=20)



class ControlCerInicial(Base):
    """El flujo CER de IAMC está al CER de la liquidación menos el rezago: el control es exacto."""

    def avisos(self, valor_inicial):
        avisos = []
        contrato = {"tipo": "CER", "valor_inicial": valor_inicial, "rezago_habiles": 10, "fuente": "fixture"}
        iamc_schedule(self.cierre, "X29E7", "tp", contrato=contrato, indices=self.indices, avisos=avisos)
        return [a for a in avisos if a.startswith("revisar valor inicial del CER")]

    def test_cer_inicial_contractual_no_avisa(self):
        # Resolución Conjunta 48/2026: CER del 31/07/2026, diez días hábiles antes de la emisión.
        self.assertEqual(self.avisos("815.43451086916"), [])

    def test_cer_inicial_corrido_tres_dias_avisa(self):
        # CER del 03/08/2026: el pago cambia 0,2 % y el control anterior (0,5 %) no lo detectaba.
        self.assertEqual(len(self.avisos("816.92114579699")), 1)



class VentanaTamar(Base):
    """Cupón TAMAR: promedio de los días hábiles con dato de [inicio − rezago, pago − rezago).

    Así se reproducen al centésimo de diezmilésimo los 12 cupones pagados de BAM27 y RVS1O en
    2025 y 2026 (avisos de MAE y CNV). El motor anterior excluía el inicio e incluía el fin.
    """

    def contrato(self, **extra):
        return dict({"tipo": "TAMAR", "rezago_habiles": 7, "fuente": "fixture",
                     "_pagos_previos": (date(2026, 5, 27), date(2026, 8, 27))}, **extra)

    def primer_pago(self, contrato):
        return iamc_schedule(self.cierre, "RVS1O", "on", contrato=contrato, indices=self.indices,
                               avisos=[]).pagos[0]

    def test_ventana_incluye_el_inicio_y_excluye_el_fin(self):
        from financial_engine.indexed_payments import _ventana_tamar
        indices = {"tamar_tna": {date(2026, 8, 3): Decimal("0.30"), date(2026, 8, 4): Decimal("0.20"),
                                 date(2026, 8, 6): Decimal("0.10"), date(2026, 8, 7): Decimal("0.90")},
                   "feriados": {}, "tamar": {}, "rem": None}
        valores = _ventana_tamar(indices, date(2026, 8, 3), date(2026, 8, 7))
        # El 05/08 no tiene dato publicado: no cuenta ni arrastra el anterior.
        self.assertEqual([v.valor for v in valores], [Decimal("0.30"), Decimal("0.20"), Decimal("0.10")])

    def test_cupon_en_curso_se_calcula_desde_el_ultimo_pago(self):
        pago = self.primer_pago(self.contrato())
        self.assertEqual(pago.fecha, date(2026, 11, 27))
        serie = self.indices["tamar_tna"]
        # 7 hábiles antes del 27/08 y del 27/11 (sin feriados cargados en el fixture).
        ultimo = max(serie)
        publicados = [serie[d] for d in serie if date(2026, 8, 18) <= d < date(2026, 11, 18)]
        # Los hábiles posteriores al último dato van con la mediana del REM de noviembre.
        proyectados = [d for d in (date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 16), date(2026, 11, 17))
                       if d > ultimo]
        self.assertEqual(ultimo, date(2026, 11, 11))
        valores = publicados + [Decimal("0.239")] * len(proyectados)
        promedio = sum(valores) / len(valores)
        self.assertTrue(pago.origen.startswith("estimado · REM"))
        self.assertAlmostEqual(pago.renta, Decimal("6.30137") * (promedio + Decimal("0.0389")), places=20)
        self.assertNotAlmostEqual(float(pago.renta), 2.201816, places=2)  # IAMC con v.vig

    def test_sin_pagos_previos_usa_la_tasa_vigente_de_iamc(self):
        contrato = self.contrato()
        del contrato["_pagos_previos"]
        pago = self.primer_pago(contrato)
        self.assertAlmostEqual(float(pago.renta), 2.201816, places=5)
        self.assertEqual(pago.origen, "definitivo · IAMC publicado")

    def test_piso_de_la_tasa(self):
        pago = self.primer_pago(self.contrato(piso="0.9"))
        self.assertEqual(pago.renta, Decimal("6.30137") * Decimal("0.9"))



class ProyeccionesIntegradas(Base):
    def cronograma(self, ticker, tipo, **datos):
        avisos = []
        contrato = {"tipo": tipo, "fuente": "fixture", "rezago_habiles": 3, **datos}
        return iamc_schedule(self.cierre, ticker, "tp", contrato=contrato, indices=self.indices, avisos=avisos)


    def test_familias_en_pesos_y_pago_estimado_proveniente_del_rem(self):
        for ticker, tipo, adicionales in (
            ("TZV28", "A3500", {}), ("X29E7", "CER", {"valor_inicial": "850"}),
            ("TMF27", "TAMAR", {}), ("TMVE8", "DUAL", {}),
        ):
            with self.subTest(ticker=ticker):
                flujo = self.cronograma(ticker, tipo, **adicionales)
                self.assertEqual(flujo.moneda, "ARS")
                self.assertGreater(flujo.pagos[0].total, Decimal(0))
                self.assertIn("estimado · REM 2026-10", flujo.pagos[0].origen)
        self.assertIn(self.cronograma("TMVE8", "DUAL").pagos[0].dual[0], ("TAMAR", "A3500", "empate"))


    def test_cupon_tamar_vigente_y_proyectado(self):
        flujo = self.cronograma("BAF27", "TAMAR")
        self.assertEqual(flujo.pagos[0].renta, Decimal("8.333333") * Decimal("0.31666126"))
        self.assertTrue(flujo.pagos[0].origen.startswith("definitivo"))
        self.assertTrue(flujo.pagos[1].origen.startswith("estimado"))


    def test_pago_cer_estimado_identifica_el_ultimo_dato_oficial(self):
        flujo = self.cronograma("X29E7", "CER", valor_inicial="850")
        self.assertIn("CER publicado hasta 2026-12-15", flujo.pagos[0].origen)


    def test_referencia_cer_cubierta_aunque_sea_posterior_a_la_captura(self):
        fila = next(fila for fila in self.cierre["calculadora_bonos"]["ins"] if fila["tk"] == "X29E7")
        # Liquidación 06/11, pago 08/12, referencia 03/12 con 3 días hábiles de rezago.
        fila["f"] = [[32, 105, 0, 0]]
        flujo = self.cronograma("X29E7", "CER", valor_inicial="850")
        pago = flujo.pagos[0]
        self.assertEqual(pago.origen, "definitivo · BCRA publicado")
        self.assertAlmostEqual(pago.total, 100 * self.indices["cer"][date(2026, 12, 3)] / 850, places=24)

