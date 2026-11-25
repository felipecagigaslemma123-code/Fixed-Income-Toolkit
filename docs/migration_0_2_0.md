# Separación de renta fija — 0.2.0

Fecha: 2026-11-25. Decisión y aprobación: Felipe, ENCARGO.md.
Versión del documento: 1.0. Last Updated: 2026-11-25.

## Alcance

La dependencia es Cartera → Toolkit instalado, fijado a `v0.2.0` desde GitHub
privado. Se elimina `_motor_letras/`. El Toolkit recibe fuentes públicas BCRA y
REM, cálculos de índices, pagos indexados, cronogramas IAMC y TIR de compra.
Cartera conserva lotes, precios manuales y huellas, datos en `--datos`, flujo por
cliente (`calcular_flujo`, `_separar_capital` y auxiliares por cliente), informe,
riesgo, alertas y dashboard. `iamc.py` no se modifica ni se mueve: cubre también
acciones y CEDEARs.

El motor no importa proveedores de red/Excel ni Cartera. `RemSurvey` y
`BCRAError` se definen en `financial_engine.indexed_types` y se reexportan en el
proveedor para compartir tipos sin introducir una dependencia inversa.
`IndexedValue` también se define en ese módulo puro y se reexporta en `indexed`.
Las funciones/clases exportadas nuevas usan nombres ingleses. Para conservar
el contrato, los campos de dataclasses (`mes`, `valor`, `fecha`, `pagos`, etc.),
keywords (`contrato`, `avisos`, `hasta_cer`, etc.), claves de JSON, mensajes y
auxiliares privados trasladados conservan su escritura original. Son aliases,
no conversiones ni una segunda implementación financiera. Esto incluye la
identidad de las excepciones compartidas y la mutabilidad de los cronogramas.

## Tabla de nombres

| Nombre anterior | Destino / nombre actual |
|---|---|
| `cartera.indices.extraer` | `market_data.providers.bcra.extract` |
| `cartera.indices.ErrorBCRA` | `market_data.providers.bcra.BCRAError` |
| `cartera.indices.URL / SERIES` | `market_data.providers.bcra.URL / SERIES` |
| `cartera.indices._guardar` | `market_data.providers.bcra.save_capture` |
| `cartera.indices.leer_rem / Rem` | `market_data.providers.bcra.read_rem / RemSurvey` |
| `cartera.indices.Valor` | `financial_engine.indexed.IndexedValue` |
| `cartera.indices.serie_bcra` | `financial_engine.indexed.bcra_series` |
| `cartera.indices.inflacion_mensual` | `financial_engine.indexed.monthly_inflation` |
| `cartera.indices.indice_cer` | `financial_engine.indexed.cer_index` |
| `cartera.indices.indice_a3500` | `financial_engine.indexed.a3500_index` |
| `cartera.indices.tamar_diaria` | `financial_engine.indexed.daily_tamar` |
| `cartera.indices.tem_tamar` | `financial_engine.indexed.tamar_monthly_rate` |
| `cartera.indices.proyectar_capitalizable` | `financial_engine.indexed.project_capitalizing` |
| `cartera.pagos_indexados.proyectar_pagos` | `financial_engine.indexed_payments.project_indexed_payments` |
| `cartera.flujo_fondos.Pago` | `financial_engine.cash_flows.Payment` |
| `cartera.flujo_fondos.Cronograma` | `financial_engine.cash_flows.CashFlowSchedule` |
| `cartera.flujo_fondos.CronogramaCompra` | `financial_engine.cash_flows.PurchaseSchedule` |
| `cartera.flujo_fondos.cronograma_iamc` | `financial_engine.cash_flows.iamc_schedule` |
| `cartera.flujo_fondos.cronograma_compra` | `financial_engine.cash_flows.purchase_schedule` |
| `cartera.flujo_fondos.tir_compra` | `financial_engine.cash_flows.purchase_yield` |
| `cartera.letras.ErrorLetra` | `financial_engine._common.FinancialInputError` |
| `cartera.letras._decimal / _fecha / _texto_decimal` | `financial_engine._common.parse_decimal / parse_date / decimal_text` |
| `cartera.indices._fecha` | `financial_engine._common.parse_bcra_date` |
| `cartera._motor_letras.day_count` | `financial_engine.day_count` |
| `cartera._motor_letras.maturity_value` | `financial_engine.maturity_value` |
| `cartera._motor_letras.letras_yield` | `financial_engine.letras_yield` |
| `cartera/tools/bcra_extraer.py` | `toolkit/tools/bcra_extract.py → market_data.bcra_cli.main` |

Los auxiliares de índices `_mes`, `_precision`, `_distancia_meses` pasan a
`financial_engine._common`; `_publicado` y `_geometrica`, a `indexed`.
Los auxiliares de pagos (`_referencia`, `_origen`, `_etiqueta`, `_cer`, `_dolar`,
`_tamar`, `_ventana_tamar`, `_tasa`, `_cer_real`, `_capitalizable`) pasan a
`indexed_payments`. Los de cronogramas (`_fecha_cierre`, `_fecha_a3500_iamc`,
`_serie`, `_manuales`, `_fusionar_pagos`, `_para_compra`) pasan a `cash_flows`.
El CLI compartido recibe la raíz del proyecto que lo invoca para conservar la
restricción original de escritura fuera de ese proyecto y las mismas opciones.

## Investigación y evidencia

- [R-010 CER](research/010_cer_projection.md).
- [R-011 TAMAR](research/011_tamar_projection.md): ventana semiabierta con datos
  publicados, cupón en curso y piso, incluidas las correcciones revisadas.
- [R-012 A3500](research/012_a3500_bond_projection.md): base macro de IAMC y
  estimaciones REM para flujos en pesos de bonos y patas de duales.

Las tres tienen `Validation Status: 🟢 Validated` y
`Implementation Approved: Yes`, por Felipe el 2026-11-25. Las fuentes son los
documentos preexistentes de Cartera en el commit
`0cbf48e7d80d91717af9f0f02295d66c9baa51f4`: `PROYECCIONES.md`, `FUENTE_BCRA.md`,
`REVISION_ETAPA11.md`. No se hizo una nueva comprobación por red. Se documentan
la verificación del 13/11, las correcciones del 16/11 y los límites: la
inconsistencia contractual de TZXM7 sigue abierta; los 12 avisos de cupón TAMAR
están descritos en la revisión, sin estar todos archivados como fixtures.
**R-006 permanece sin aprobación**, incluidos Q5 y el cálculo LELINK de
rendimientos/conversión. No se cambia su documento ni la elegibilidad del panel.

## Auditoría de pruebas

Se trasladan **56** pruebas existentes. Los cuerpos de pruebas y valores
esperados quedan idénticos tras adaptar imports/nombres; los fixtures BCRA/REM y
el cierre IAMC usado se copian sin modificar. En `test_indexed_payments.py`, el
setup prepara esos mismos índices desde los fixtures mediante el proveedor y las
funciones del Toolkit, para no importar la capa de archivos de Cartera.

| Archivo de prueba de Cartera | Antes | Después | Cambio / destino en Toolkit |
|---|---:|---:|---|
| `tests/test_extra_bcra.py` | 10 | 0 | Se traslada completo a `tests/test_bcra.py`; imports/nombres y ruta `bcra_extract.py`. |
| `tests/test_etapa11_indices.py` | 18 | 0 | Se traslada completo a `tests/test_indexed.py`; imports y nombres ingleses. |
| `tests/test_etapa9_flujo.py` | 16 | 0 | Se traslada completo a `tests/test_cash_flows.py`; imports y nombres ingleses. |
| `tests/test_extra_etapa11_revision.py` | 18 | 10 | Se retiran solo `BaseDelA3500` (2), `ControlCerInicial` (2) y `VentanaTamar` (4), trasladadas a `tests/test_indexed_payments.py`. |
| `tests/test_extra_etapa11_integracion.py` | 7 | 3 | Se retiran solo 4 métodos de cálculo (familias/duales, cupón TAMAR, etiqueta CER, referencia cubierta), trasladados a `tests/test_indexed_payments.py`. |

En el Toolkit se agregan solamente estos archivos de prueba:

| Archivo nuevo | Cantidad | Procedencia |
|---|---:|---|
| `tests/test_bcra.py` | 10 | Extractor y CLI BCRA |
| `tests/test_indexed.py` | 18 | REM y cálculos de índices/capitalizables |
| `tests/test_cash_flows.py` | 16 | Cronogramas, fusión, huecos y TIR |
| `tests/test_indexed_payments.py` | 12 | 8 de revisión y 4 de integración pura |

No se toca ningún otro archivo de prueba, ni ningún destino de `mock.patch`:
los puntos de parcheo de Cartera se conservan. La cuenta incluye las pruebas
heredadas que descubre unittest. Total conjunto: **1272 antes y 1272 después**.

| Suite | Antes del traslado | Después |
|---|---|---|
| Cartera | 1083 aprobadas | 1027 aprobadas |
| Toolkit | 189: 185 aprobadas, 4 bloqueadas por sockets | 245: 241 aprobadas, las mismas 4 bloqueadas por sockets |

Antes de retirar las pruebas transferidas también se ejecutaron las **1083**
originales de Cartera contra el nuevo Toolkit: todas aprobadas.

## Verificación de invariancia y empaquetado

Se comparan por AST las **50 definiciones** trasladadas contra el commit fuente,
normalizando solo nombres/imports. Coinciden operadores, constantes, contextos
Decimal, tolerancias, fechas, redondeos y textos de error/avisos. Los cuerpos
retenidos en `letras.py` y `flujo_fondos.py` y los tres módulos del motor de
letras también coinciden; solo cambia el import de `day_count` que ya distinguía
la antigua copia. Los cuerpos de las 56 pruebas y sus valores esperados coinciden.

`pyproject.toml` declara descubrimiento de paquetes bajo `src/`, con `namespaces =
false` y los grupos `financial_engine*`, `market_data*`, `local_dashboard*`.
Hay **12 paquetes** con `__init__.py`; los **8 módulos** importados directamente
por Cartera pertenecen a ellos. El CLI instalado vive en `market_data.bcra_cli`,
sin importar `tools/`. La biblioteca no importa `cartera`.
Se ejecutan también las **1027 pruebas de Cartera**, todas aprobadas, usando
exclusivamente un árbol temporal formado por esos paquetes declarados, sin el
`src` del Toolkit en PYTHONPATH. Esto comprueba cobertura de los imports; no
sustituye la instalación real con pip y el backend de construcción.

La verificación real de `pip install .` queda limitada por el entorno sin red:
el venv trae setuptools **58.0.4**, inferior al mínimo declarado **61**, y no
trae `wheel`. El intento local `pip install --no-build-isolation --no-deps
--no-cache-dir --target ... ./toolkit` falla por `invalid command bdist_wheel`;
ese setuptools tampoco interpreta la metadata PEP 621. No se alteran los
requisitos de construcción ni se simula una instalación exitosa. La
configuración declarada y la cobertura de paquetes/imports quedan auditadas;
falta ejecutar la instalación con las herramientas de construcción requeridas.

## Límites del entorno y commits

Los cuatro fallos de la suite completa del Toolkit son preexistentes y ocurren
al hacer `socket.bind` en 127.0.0.1 con puerto automático: `PermissionError:
[Errno 1] Operation not permitted`. Son dos casos de `TestMetricsEndpoint` en
`test_dashboard_metrics.py`, `test_server_exposes_futures_page_and_api` en
`test_futures_dashboard.py` y `test_server_exposes_only_allowlisted_routes` en
`test_local_dashboard.py`. No se modifica código ni se omiten pruebas para
ocultar esos fallos.

Ambos clones quedan en `separacion-renta-fija`. ENCARGO.md condiciona los commits
a que pasen ambas suites; por ahora no se hicieron commits, ni push, ni tags,
ni amend. Hace falta una corrida con sockets locales permitidos o la decisión
explícita de Felipe de aceptar los cuatro bloqueos preexistentes para confirmar
los cambios. La instalación desde GitHub también requiere que `v0.2.0` exista
más adelante; su publicación no forma parte de este encargo.
