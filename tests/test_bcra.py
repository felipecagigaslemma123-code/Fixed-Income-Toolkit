"""Pruebas del extractor de series del BCRA, sin red y con cifras ficticias."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import parse_qs, urlsplit


RUTA = Path(__file__).resolve().parents[1] / "tools" / "bcra_extract.py"
SPEC = importlib.util.spec_from_file_location("bcra_extract_prueba", RUTA)
bcra = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bcra)

DESDE = date(2026, 9, 24)
HASTA = date(2026, 9, 30)
REFERENCIA = "2026-09-25"
PRECISO = "1500.1234567890123456789"

CATALOGO = {
    "cer": ("Coeficiente de estabilización de referencia (base 2.2.02=1)", "Índice base 2.2.02=1"),
    "tamar_tna": ("Tasa de interes TAMAR de bancos privados ", "En porcentaje nominal anual"),
    "a3500": ("Tipo de cambio mayorista de referencia", "Pesos argentinos por dólar estadounidense"),
}


class APIPrueba:
    def __init__(self, observaciones=None, maximo_por_pagina=1000):
        self.observaciones = observaciones or {}
        self.maximo_por_pagina = maximo_por_pagina
        self.llamadas = []
        self.por_id = {identificador: clave for clave, identificador in bcra.SERIES.items()}

    def __call__(self, url):
        self.llamadas.append(url)
        partes = urlsplit(url)
        assert partes.scheme == "https" and partes.netloc == "api.bcra.gob.ar", url
        consulta = parse_qs(partes.query)
        offset = int(consulta.get("offset", [0])[0])
        limite = min(int(consulta.get("limit", [1000])[0]), self.maximo_por_pagina)
        if partes.path.endswith("/monetarias"):
            identificador = int(consulta["idVariable"][0])
            clave = self.por_id[identificador]
            descripcion, unidad = CATALOGO[clave]
            resultados = [{"idVariable": identificador, "descripcion": descripcion,
                           "unidadExpresion": unidad, "periodicidad": "D",
                           "categoria": "Principales Variables", "tipoSerie": "Saldos",
                           "moneda": "ML", "primerFechaInformada": "2024-10-01",
                           "ultFechaInformada": "2026-09-30", "ultValorInformado": 1500}]
            cantidad = 1
        else:
            identificador = int(partes.path.rsplit("/", 1)[1])
            clave = self.por_id[identificador]
            assert consulta["desde"] == [DESDE.isoformat()], url
            assert consulta["hasta"] == [HASTA.isoformat()], url
            detalle = self.observaciones.get(clave, [{"fecha": REFERENCIA, "valor": "VALOR_PRECISO"}])
            cantidad = len(detalle)
            resultados = [{"idVariable": identificador, "detalle": detalle[offset:offset + limite]}]
        metadata = {"resultset": {"count": cantidad, "offset": offset, "limit": limite}}
        respuesta = {"status": 200, "metadata": metadata, "results": resultados}
        return json.dumps(respuesta).replace('"VALOR_PRECISO"', PRECISO).encode("utf-8")


class Extraer(unittest.TestCase):
    def test_preserva_unidades_fechas_y_precision_de_las_tres_series(self):
        api = APIPrueba()
        resultado = bcra.extract(DESDE, HASTA, fetch=api)
        self.assertEqual(resultado["esquema_version"], 1)
        self.assertEqual(resultado["fuente"], "BCRA")
        self.assertEqual((resultado["desde"], resultado["hasta"]), (DESDE.isoformat(), HASTA.isoformat()))
        self.assertIsNotNone(datetime.fromisoformat(resultado["consultado_en"]).utcoffset())
        self.assertEqual(set(resultado["series"]), set(CATALOGO))
        for clave, serie in resultado["series"].items():
            with self.subTest(serie=clave):
                self.assertEqual(serie["id_variable"], bcra.SERIES[clave])
                self.assertEqual(serie["unidad"], CATALOGO[clave][1])
                self.assertEqual(serie["estado"], "publicado")
                self.assertEqual(serie["observaciones"], [{"fecha": REFERENCIA, "valor": PRECISO}])

    def test_recupera_todas_las_paginas_de_observaciones(self):
        fechas = ["2026-09-26", "2026-09-25", "2026-09-24"]
        api = APIPrueba({"cer": [{"fecha": fecha, "valor": 100} for fecha in fechas]}, maximo_por_pagina=1)
        resultado = bcra.extract(DESDE, HASTA, fetch=api)
        observadas = resultado["series"]["cer"]["observaciones"]
        self.assertCountEqual([fila["fecha"] for fila in observadas], fechas)
        paginas = [parse_qs(urlsplit(url).query) for url in api.llamadas
                   if urlsplit(url).path.endswith("/" + str(bcra.SERIES["cer"]))]
        self.assertEqual([int(pagina.get("offset", ["0"])[0]) for pagina in paginas], [0, 1, 2])

    def test_rango_sin_observaciones_se_identifica_sin_rellenar(self):
        api = APIPrueba({"tamar_tna": []})
        resultado = bcra.extract(DESDE, HASTA, fetch=api)
        serie = resultado["series"]["tamar_tna"]
        self.assertEqual(serie["estado"], "sin dato")
        self.assertEqual(serie["observaciones"], [])

    def test_rechaza_fechas_duplicadas_invalidas_o_fuera_del_rango(self):
        for fechas in ((REFERENCIA, REFERENCIA), ("2026-09-31",), ("2026-10-01",)):
            with self.subTest(fechas=fechas):
                api = APIPrueba({"cer": [{"fecha": fecha, "valor": 100} for fecha in fechas]})
                with self.assertRaises(bcra.BCRAError):
                    bcra.extract(DESDE, HASTA, fetch=api)

    def test_rechaza_si_tamar_cambia_a_una_tasa_efectiva(self):
        api = APIPrueba()

        def fetch(url):
            respuesta = api(url)
            if parse_qs(urlsplit(url).query).get("idVariable") == [str(bcra.SERIES["tamar_tna"])]:
                respuesta = respuesta.replace(b"nominal", b"efectiva")
            return respuesta

        with self.assertRaisesRegex(bcra.BCRAError, "unidad"):
            bcra.extract(DESDE, HASTA, fetch=fetch)

    def test_rechaza_rango_invertido_antes_de_consultar(self):
        api = APIPrueba()
        with self.assertRaises(bcra.BCRAError):
            bcra.extract(HASTA, DESDE, fetch=api)
        self.assertEqual(api.llamadas, [])

    def test_rechaza_valores_no_numericos_o_no_finitos(self):
        for valor in (True, None, "NaN", float("inf")):
            with self.subTest(valor=valor):
                api = APIPrueba({"cer": [{"fecha": REFERENCIA, "valor": valor}]})
                with self.assertRaises(bcra.BCRAError):
                    bcra.extract(DESDE, HASTA, fetch=api)


class Comando(unittest.TestCase):
    def test_publica_una_captura_completa(self):
        with TemporaryDirectory() as temporal:
            destino = Path(temporal) / "bcra.json"
            with redirect_stdout(io.StringIO()):
                codigo = bcra.main(["--desde", DESDE.isoformat(), "--hasta", HASTA.isoformat(),
                                    "--salida", str(destino)], fetch=APIPrueba())
            self.assertEqual(codigo, 0)
            datos = json.loads(destino.read_text(encoding="utf-8"))
            self.assertEqual(datos["series"]["cer"]["observaciones"][0]["valor"], PRECISO)

    def test_fallo_en_una_serie_no_publica_una_captura_parcial(self):
        api = APIPrueba()

        def fetch(url):
            if urlsplit(url).path.endswith("/" + str(bcra.SERIES["a3500"])):
                raise OSError("conexión interrumpida")
            return api(url)

        with TemporaryDirectory() as temporal:
            destino = Path(temporal) / "bcra.json"
            with redirect_stderr(io.StringIO()) as errores:
                codigo = bcra.main(["--desde", DESDE.isoformat(), "--hasta", HASTA.isoformat(),
                                    "--salida", str(destino)], fetch=fetch)
            self.assertNotEqual(codigo, 0)
            self.assertIn("conexión interrumpida", errores.getvalue())
            self.assertEqual(list(Path(temporal).iterdir()), [])

    def test_conserva_una_captura_anterior(self):
        with TemporaryDirectory() as temporal:
            destino = Path(temporal) / "bcra.json"
            anterior = b'{"fuente": "BCRA"}\n'
            destino.write_bytes(anterior)
            with redirect_stderr(io.StringIO()):
                codigo = bcra.main(["--desde", DESDE.isoformat(), "--hasta", HASTA.isoformat(),
                                    "--salida", str(destino)], fetch=APIPrueba())
            self.assertNotEqual(codigo, 0)
            self.assertEqual(destino.read_bytes(), anterior)
