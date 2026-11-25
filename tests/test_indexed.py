import datetime as dt
import json
import pathlib
import unittest
from decimal import Decimal

from market_data.providers.bcra import read_rem
from financial_engine.indexed import (a3500_index, cer_index, monthly_inflation, bcra_series,
                             daily_tamar, tamar_monthly_rate, project_capitalizing)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
REM = read_rem(RAIZ / "fixtures/bcra/rem-tablas-2026-10.xlsx")
CAPTURA = json.loads((RAIZ / "fixtures/bcra/bcra-2026-11-13.json").read_text(encoding="utf-8"))
CER = bcra_series(CAPTURA, "cer")
A3500 = bcra_series(CAPTURA, "a3500")
TAMAR = bcra_series(CAPTURA, "tamar_tna")
INFL = monthly_inflation(REM, dt.date(2029, 12, 1))
d = dt.date


def producto(valores):
    total = Decimal(1)
    for valor in valores:
        total *= 1 + valor
    return total


class LeerRem(unittest.TestCase):
    def test_mes_y_valores_explicitos(self):
        self.assertEqual(REM.mes, d(2026, 10, 1))
        self.assertEqual(REM.ipc[d(2026, 10, 1)], Decimal("0.018"))
        self.assertEqual(REM.ipc[d(2026, 11, 1)], Decimal("0.017"))
        self.assertEqual(len(REM.ipc), 7)
        self.assertEqual(REM.tamar[d(2026, 11, 1)], Decimal("0.239"))
        self.assertEqual(REM.tc[d(2026, 12, 1)], Decimal("1590"))

    def test_horizontes(self):
        self.assertEqual(REM.ipc_12m, Decimal("0.218"))
        self.assertAlmostEqual(float(REM.ipc_24m), 0.1729578974, places=9)
        self.assertAlmostEqual(float(REM.tamar_12m), 0.2627040108488353, places=12)
        self.assertAlmostEqual(float(REM.tc_12m), 1984.906562289537, places=6)


class Inflacion(unittest.TestCase):
    def test_meses_explicitos(self):
        self.assertEqual(INFL[d(2026, 10, 1)], Decimal("0.018"))
        self.assertEqual(INFL[d(2027, 4, 1)], REM.ipc[d(2027, 4, 1)])

    def test_resto_del_primer_anio_completa_los_12_meses(self):
        meses = [d(2026, 11, 1)] + [d(2027, m, 1) for m in range(1, 11)] + [d(2026, 12, 1)]
        self.assertAlmostEqual(float(producto(INFL[m] for m in meses)), 1.218, places=12)
        self.assertEqual(INFL[d(2027, 5, 1)], INFL[d(2027, 10, 1)])

    def test_segundo_anio_y_despues(self):
        meses = [d(2027, 11, 1), d(2027, 12, 1)] + [d(2028, m, 1) for m in range(1, 11)]
        self.assertAlmostEqual(float(producto(INFL[m] for m in meses)), float(1 + REM.ipc_24m), places=12)
        self.assertEqual(INFL[d(2029, 12, 1)], INFL[d(2028, 10, 1)])


class Cer(unittest.TestCase):
    def test_publicado(self):
        valor = cer_index(CER, INFL, d(2026, 12, 10))
        self.assertEqual(valor.origen, "publicado")
        self.assertEqual(valor.valor, CER[d(2026, 12, 10)])

    def test_la_inflacion_de_noviembre_mueve_el_cer_del_16_12_al_15_01(self):
        base = CER[d(2026, 12, 15)]
        enero = cer_index(CER, INFL, d(2027, 1, 15))
        self.assertEqual(enero.origen, "proyectado")
        self.assertAlmostEqual(float(enero.valor / base), 1.017, places=12)
        medio = cer_index(CER, INFL, d(2026, 12, 31))
        self.assertAlmostEqual(float(medio.valor / base), 1.017 ** (16 / 31), places=12)

    def test_encadena_meses(self):
        base = CER[d(2026, 12, 15)]
        febrero = cer_index(CER, INFL, d(2027, 2, 15))
        esperado = (1 + INFL[d(2026, 11, 1)]) * (1 + INFL[d(2026, 12, 1)])
        self.assertAlmostEqual(float(febrero.valor / base), float(esperado), places=12)


class TipoCambio(unittest.TestCase):
    def test_publicado_y_dia_sin_dato(self):
        self.assertEqual(a3500_index(A3500, REM, d(2026, 11, 12)).valor, A3500[d(2026, 11, 12)])
        sabado = a3500_index(A3500, REM, d(2026, 11, 7))
        self.assertEqual(sabado.origen, "publicado")
        self.assertEqual(sabado.valor, A3500[d(2026, 11, 5)])  # sin datos del 06 al 10/11

    def test_puntos_del_rem_a_mitad_de_mes(self):
        nov = a3500_index(A3500, REM, d(2026, 11, 15))
        self.assertEqual(nov.origen, "proyectado")
        self.assertAlmostEqual(float(nov.valor), float(REM.tc[d(2026, 11, 1)]), places=9)
        self.assertAlmostEqual(float(a3500_index(A3500, REM, d(2026, 12, 15)).valor), 1590, places=9)

    def test_interpolacion_geometrica(self):
        a, b = REM.tc[d(2026, 11, 1)], REM.tc[d(2026, 12, 1)]
        valor = a3500_index(A3500, REM, d(2026, 12, 1)).valor
        self.assertAlmostEqual(float(valor), float(a) * (float(b) / float(a)) ** (16 / 30), places=6)

    def test_desde_el_ultimo_publicado_hasta_el_primer_punto(self):
        ultimo = A3500[d(2026, 11, 12)]
        nov = REM.tc[d(2026, 11, 1)]
        valor = a3500_index(A3500, REM, d(2026, 11, 13)).valor
        self.assertAlmostEqual(float(valor), float(ultimo) * (float(nov) / float(ultimo)) ** (1 / 3), places=6)


class Tamar(unittest.TestCase):
    def test_publicada(self):
        valor = daily_tamar(TAMAR, REM, d(2026, 11, 11))
        self.assertEqual((valor.valor, valor.origen), (Decimal("0.24437500000000"), "publicado"))

    def test_rem_del_mes(self):
        valor = daily_tamar(TAMAR, REM, d(2026, 11, 20))
        self.assertEqual((valor.valor, valor.origen), (Decimal("0.239"), "proyectado"))

    def test_interpolacion_hasta_12_meses_y_luego_constante(self):
        abril, octubre = REM.tamar[d(2027, 4, 1)], REM.tamar_12m
        julio = daily_tamar(TAMAR, REM, d(2027, 7, 15)).valor
        self.assertAlmostEqual(float(julio), float(abril + (octubre - abril) / 2), places=12)
        self.assertEqual(daily_tamar(TAMAR, REM, d(2028, 3, 3)).valor, REM.tamar_12m)


class Capitalizable(unittest.TestCase):
    def test_tem_desde_tamar(self):
        tem = tamar_monthly_rate(Decimal("0.24"), Decimal("0.065"))
        self.assertAlmostEqual(float(tem), (1 + 0.305 * 32 / 365) ** (365 / 384) - 1, places=12)

    def test_tasa_constante_reproduce_iamc(self):
        # TMF27 del cierre del 12/11/2026: mv 137,083114, TEM 2,56932 %, 12,433333 meses, 9 transcurridos.
        mv, tem = Decimal("137.083114"), Decimal("0.0256932")
        tnas = [tem] * 4
        self.assertAlmostEqual(float(project_capitalizing(mv, tem, Decimal("12.433333"),
                                                             Decimal("9.0"), tnas)), 137.083114, places=9)

    def test_tasa_mayor_sube_el_pago(self):
        mv, tem = Decimal("137.083114"), Decimal("0.0256932")
        tems = [Decimal("0.03")] * 4
        esperado = 137.083114 * (1.03 / 1.0256932) ** 3.433333
        self.assertAlmostEqual(float(project_capitalizing(mv, tem, Decimal("12.433333"), Decimal("9.0"), tems)),
                               esperado, places=6)


if __name__ == "__main__":
    unittest.main()
