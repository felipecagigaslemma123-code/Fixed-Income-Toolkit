import copy
import datetime as dt
import json
import pathlib
import unittest
from decimal import Decimal

from financial_engine.cash_flows import purchase_schedule, iamc_schedule, purchase_yield

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CIERRE = json.loads((RAIZ / "fixtures/iamc/cierres/2026-11-05.json").read_text(encoding="utf-8"))
LIQ = dt.date(2026, 11, 6)


def instrumento(cierre, ticker):
    for fila in cierre["calculadora_bonos"]["ins"]:
        if fila["tk"] == ticker:
            return fila
    raise KeyError(ticker)


def cierre_sintetico(fecha, liq, pagos, ticker="BON1"):
    liq_d = dt.date.fromisoformat(liq)
    f = [[(dt.date.fromisoformat(d) - liq_d).days, a, r, 0.0] for d, a, r in pagos]
    return {
        "fecha_cierre": fecha,
        "fecha_liquidacion": liq,
        "calculadora_bonos": {
            "liq": liq,
            "fx": {},
            "ins": [{"tk": ticker, "g": "tp", "seg": "sob", "k": "fix", "cur": "USD", "fxc": 1.0,
                     "fxr": "MEP", "px": 50.0, "pxa": 50.0, "liq": liq, "f": f}],
        },
    }


class CronogramaIamc(unittest.TestCase):
    def test_al30_usa_la_calculadora_y_no_el_informe(self):
        c = iamc_schedule(CIERRE, "AL30", "tp")
        self.assertTrue(c.habilitado)
        self.assertEqual((c.familia, c.moneda, c.plaza), ("fix", "USD", "MEP"))
        self.assertEqual(c.fecha_cierre, dt.date(2026, 11, 5))
        self.assertEqual(c.liquidacion, LIQ)
        self.assertEqual(len(c.pagos), 8)
        self.assertEqual(c.pagos[0].fecha, dt.date(2027, 1, 9))
        self.assertEqual(c.pagos[-1].fecha, dt.date(2030, 7, 9))
        enero_2028 = [p for p in c.pagos if p.fecha == dt.date(2028, 1, 9)][0]
        self.assertEqual(enero_2028.renta, Decimal("0.42"))
        self.assertEqual(enero_2028.amortizacion, Decimal("8.0"))
        self.assertEqual(enero_2028.origen, "iamc 2026-11-05")
        self.assertEqual(sum(p.amortizacion for p in c.pagos), Decimal("64"))

    def test_on_en_cable(self):
        c = iamc_schedule(CIERRE, "YM34O", "on")
        self.assertTrue(c.habilitado)
        self.assertEqual(c.plaza, "CCL")
        self.assertEqual(c.pagos[0].renta, Decimal("4.125"))

    def test_dual_no_habilitado_no_trae_pagos(self):
        c = iamc_schedule(CIERRE, "TMVE8", "tp")
        self.assertFalse(c.habilitado)
        self.assertEqual(c.familia, "capv")
        self.assertEqual(c.pagos, [])

    def test_cer_no_habilitado(self):
        self.assertFalse(iamc_schedule(CIERRE, "TZXS7", "tp").habilitado)

    def test_ausente_o_grupo_equivocado(self):
        self.assertIsNone(iamc_schedule(CIERRE, "TX26", "tp"))
        self.assertIsNone(iamc_schedule(CIERRE, "AL30", "on"))

    def test_no_modifica_el_cierre(self):
        antes = copy.deepcopy(CIERRE)
        iamc_schedule(CIERRE, "AL30", "tp")
        self.assertEqual(CIERRE, antes)


class TirCompra(unittest.TestCase):
    def reproduce(self, ticker, grupo, publicada):
        c = iamc_schedule(CIERRE, ticker, grupo)
        precio = Decimal(str(instrumento(CIERRE, ticker)["px"]))
        tir = purchase_yield(precio, LIQ, c.pagos)
        self.assertLess(abs(float(tir) - publicada), 1e-6)  # 0,01 pb

    def test_reproduce_al30(self):
        self.reproduce("AL30", "tp", 0.143033)

    def test_reproduce_ym34o(self):
        self.reproduce("YM34O", "on", 0.086296)

    def test_ignora_pagos_hasta_la_liquidacion(self):
        c = iamc_schedule(CIERRE, "AL30", "tp")
        precio = Decimal(str(instrumento(CIERRE, "AL30")["px"]))
        sin_primero = purchase_yield(precio, dt.date(2027, 1, 9), c.pagos)
        solo_resto = purchase_yield(precio, dt.date(2027, 1, 9), c.pagos[1:])
        self.assertEqual(sin_primero, solo_resto)

    def test_sin_pagos_es_none(self):
        self.assertIsNone(purchase_yield(Decimal("50"), LIQ, []))

    def test_precio_igual_a_la_suma_da_cero(self):
        c = iamc_schedule(CIERRE, "AL30", "tp")
        total = sum(p.amortizacion + p.renta for p in c.pagos)
        self.assertLess(abs(float(purchase_yield(total, LIQ, c.pagos))), 1e-8)


A = cierre_sintetico("2026-01-02", "2026-01-05",
                     [("2026-07-09", 8.0, 0.27), ("2026-12-09", 0.0, 0.10), ("2027-01-09", 8.0, 0.24)])
B = cierre_sintetico("2026-11-05", "2026-11-06", [("2027-01-09", 8.0, 0.25)])


class PurchaseSchedule(unittest.TestCase):
    def test_pago_pasado_del_cierre_viejo_y_futuro_del_nuevo(self):
        r = purchase_schedule([B, A], "BON1", "tp", dt.date(2026, 2, 1))
        self.assertTrue(r.completo)
        por_fecha = {p.fecha: p for p in r.pagos}
        self.assertEqual(por_fecha[dt.date(2026, 7, 9)].renta, Decimal("0.27"))
        self.assertEqual(por_fecha[dt.date(2026, 7, 9)].origen, "iamc 2026-01-02")
        self.assertEqual(por_fecha[dt.date(2027, 1, 9)].renta, Decimal("0.25"))
        self.assertEqual(por_fecha[dt.date(2027, 1, 9)].origen, "iamc 2026-11-05")

    def test_pago_que_desaparece_no_se_cuenta_y_se_advierte(self):
        r = purchase_schedule([A, B], "BON1", "tp", dt.date(2026, 2, 1))
        self.assertNotIn(dt.date(2026, 12, 9), [p.fecha for p in r.pagos])
        self.assertTrue(r.advertencias)

    def test_compra_anterior_al_cierre_mas_viejo_queda_incompleta(self):
        r = purchase_schedule([A, B], "BON1", "tp", dt.date(2025, 12, 1))
        self.assertFalse(r.completo)
        self.assertEqual(r.faltante_hasta, dt.date(2026, 1, 5))

    def test_pagos_manuales_cubren_el_hueco_y_se_controlan(self):
        manuales = [(dt.date(2026, 1, 3), Decimal("0"), Decimal("0.05")),
                    (dt.date(2026, 7, 9), Decimal("8"), Decimal("0.30"))]
        r = purchase_schedule([A, B], "BON1", "tp", dt.date(2025, 12, 1), pagos_manuales=manuales)
        self.assertTrue(r.completo)
        por_fecha = {p.fecha: p for p in r.pagos}
        self.assertEqual(por_fecha[dt.date(2026, 1, 3)].origen, "manual")
        self.assertEqual(por_fecha[dt.date(2026, 7, 9)].renta, Decimal("0.27"))
        self.assertTrue(any("2026-07-09" in a for a in r.advertencias))

    def test_solo_pagos_posteriores_a_la_liquidacion(self):
        r = purchase_schedule([A, B], "BON1", "tp", dt.date(2026, 7, 9))
        self.assertEqual([p.fecha for p in r.pagos], [dt.date(2027, 1, 9)])


if __name__ == "__main__":
    unittest.main()
