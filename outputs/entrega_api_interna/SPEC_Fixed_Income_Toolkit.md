# Fixed Income Toolkit: especificación técnica de implementación

**Versión del spec:** 1.1 (26/10/2026) — ver *Addendum 1* al final; la v1.0 (30/09/2026) no cambió en el resto
**Código de referencia:** `fixed-income-toolkit` v0.1.0 (Python ≥ 3.9)
**Autor del toolkit:** Felipe Cagigas
**Destinatarios:** equipo interno que va a proveer la API de datos de mercado

> Este documento describe lo que **está implementado hoy** en el código del zip adjunto. No propone fórmulas nuevas: cada ecuación sale del código fuente y de su registro de investigación (`docs/research/`). Cuando algo todavía no está validado, se indica de forma explícita.

---

## Índice

1. Qué es y qué alcance tiene
2. Arquitectura y flujo de datos
3. Estructura del repositorio
4. **Datos que consume el toolkit (lo que necesita la API interna)**
5. Modelos de datos
6. Motor financiero: convenciones, ecuaciones y algoritmos
7. Reglas de orquestación (alineación temporal, plazo, precio)
8. Ciclo de vida de instrumentos (algoritmo de matching)
9. Persistencia (SQLite)
10. Scheduler y procesos
11. Dashboard local y endpoints HTTP
12. Metodologías en investigación (no implementadas)
13. Tests y validación
14. Brechas conocidas y puntos de atención
15. Cómo correrlo

---

## 1. Qué es y qué alcance tiene

Es un toolkit de análisis de renta fija enfocado en Letras y Bonos Capitalizables del Tesoro argentino (**LECAP / BONCAP**). Hace cuatro cosas:

1. **Descubre** las letras nuevas a partir de los resultados de licitación de la Secretaría de Finanzas.
2. **Descarga** precios del mercado secundario de A3 Mercados (API MarketData MAE) cada 15 minutos.
3. **Calcula**, con `Decimal` y sin redondeos intermedios, el valor al vencimiento (VPV), HPR, TEA, TEM, TNA y la duration de las letras.
4. **Muestra** los resultados en un dashboard HTML local (`http://127.0.0.1:8765`).

Además tiene una pantalla aparte de **futuros de dólar (DLR)**, que solo muestra datos observados y no calcula nada.

**Principio rector (Research First Policy):** ninguna fórmula entra al motor de producción sin un documento de investigación con estado `Validated` y aprobación explícita (`Implementation Approved: Yes`).

| Métrica | Research | Estado | Módulo |
|---|---|---|---|
| VPV (valor al vencimiento) LECAP/BONCAP | R-001 | ✅ Validada y aprobada (10/08/2026) | `financial_engine/maturity_value.py` |
| HPR | R-002 | ✅ Aprobada (10/08/2026) | `financial_engine/letras_yield.py` |
| TNA | R-003 | ✅ Aprobada (11/08/2026) | `financial_engine/letras_yield.py` |
| TEA / TEM | R-004 | ✅ Aprobada (11/08/2026) | `financial_engine/letras_yield.py` |
| Duration Macaulay / Modificada (letras de pago único) | R-005 | ✅ Aprobada (11/08/2026) | `financial_engine/duration.py` |
| Letras dollar-linked (LELINK) | R-006 | 🟡 En revisión, **no implementada** | prototipo fuera del motor |
| Forward / devaluación implícita con futuros | R-009 | 🟡 En revisión, **no implementada** | `fx_forward_metrics.py` lanza error a propósito |

---

## 2. Arquitectura y flujo de datos

```
                ┌───────────────────────────── FUENTES ─────────────────────────────┐
                │ A3/MAE MarketData API   Secretaría de Finanzas   Colocaciones .xlsx │
                │ (precios, API key)      (HTML de resultados)     (datos contractuales)│
                │ Visor público futuros A3 (sin credencial)                            │
                └───────────────┬───────────────────────┬───────────────────┬──────────┘
                                │                       │                   │
                    providers/* (transporte + normalización a modelos inmutables)
                                │                       │                   │
                                ▼                       ▼                   ▼
                       ┌─────────────────── MARKET DATA LAYER ────────────────────┐
                       │ models/  providers/  services/  storage/ (SQLite)        │
                       │ instrument_identity  calculation_eligibility  contractual│
                       └───────────────────────────┬──────────────────────────────┘
                                                   │ (orquestación: alineación de fechas,
                                                   │  selección explícita de precio)
                                                   ▼
                       ┌──────────────────── FINANCIAL ENGINE ─────────────────────┐
                       │ day_count · maturity_value · letras_yield · duration      │
                       │ Puro: sin IO, sin APIs, sin float. Decimal (prec. 50)     │
                       └───────────────────────────┬──────────────────────────────┘
                                                   ▼
                              Resultados inmutables → dashboard local / exports
```

**Dirección de dependencias (obligatoria):** `Market Data → Orquestación → Financial Engine → Resultados`. El motor financiero nunca importa providers, bases de datos ni UI. Por eso **cambiar A3 por la API interna implica tocar solo `providers/` y `config/`**; el motor no cambia.

---

## 3. Estructura del repositorio

```
src/
  financial_engine/        Motor de cálculo puro (Decimal, sin IO)
    day_count.py           30/360 Tesoro
    maturity_value.py      VPV LECAP/BONCAP (R-001)
    letras_yield.py        HPR/TEA/TEM/TNA convención IAMC (R-002/3/4)
    duration.py            Macaulay + Modificada, pago único (R-005)
    fx_forward_metrics.py  Contrato público; bloqueado hasta aprobar R-009
  market_data/
    models/                Dataclasses inmutables + enums + excepciones
    providers/
      base.py              Protocol MarketDataProvider / FuturesDataProvider
      a3mae/               Cliente API A3/MAE + normalización JSON→MarketQuote
      treasury/            Scraper de resultados de licitación (argentina.gob.ar)
      a3_public_futures/   Visor público de futuros DLR
    contractual/           Lectura de colocaciones_*.xlsx + resolución de vencimientos
    services/              Sync Tesoro/A3, lifecycle, schedulers
    storage/               Repositorios SQLite (quotes, lifecycle, futuros)
    config/settings.py     Configuración (hosts, env vars, intervalos)
    calculation_eligibility.py  Qué familias se pueden calcular
    instrument_identity.py      Normalización de tickers / familias / fechas
    futures_expiry.py
  local_dashboard/         Servidor HTTP loopback + serialización JSON Decimal-safe
tools/                     CLIs: sync, schedulers, servidor, inspección Excel
tests/                     166 tests (pytest)
docs/                      Especificación, convenciones, research, contratos de providers
examples/                  Calculadoras Excel de referencia + casos de validación JSON
data/                      Colocaciones oficiales del Tesoro (.xlsx)
outputs/                   Dashboards HTML (modelo LECAP/BONCAP, futuros)
```

---

## 4. Datos que consume el toolkit (lo que necesita la API interna)

Esta es la sección clave para el equipo que va a proveer la API.

### 4.1 Fuente actual: A3 / MAE MarketData

| Item | Valor actual |
|---|---|
| Hosts | PROD `https://api.mae.com.ar` · UAT `https://apiuat.mae.com.ar` |
| Base path | `MarketData/v1` (configurable; el Swagger usa `api/v1`) |
| Autenticación | Header `x-api-key: <key>`; la key se lee de una variable de entorno, nunca del código |
| Método | `GET`, solo lectura; `accept: application/json` |
| Timeout | 15 s |
| Frecuencia | Cada **15 minutos** (900 s) mientras corre el scheduler; arranque diario 09:30 |
| Paginación | `pageNumber` 1..N, 50 filas por página; se corta cuando una página trae < 50. Límite de seguridad: 100 páginas |
| Deduplicación | Por `(ticker, instrument_class, term, market_date, provider)` |

**Endpoints usados:**

| Segmento | Path | Uso actual |
|---|---|---|
| Renta fija | `mercado/cotizaciones/rentafija` | **Sí (el principal)** |
| Cauciones | `mercado/cotizaciones/cauciones` | Soportado, no usado por el dashboard |
| Forex | `mercado/cotizaciones/forex` | Soportado, no usado por el dashboard |
| Repo | `mercado/repo` | Soportado, no usado |

**Parámetros de query (todos opcionales):** `segmento`, `plazo`, `moneda`, `ticker`, `pageNumber`.

**Formato de respuesta esperado:** un **array JSON** de objetos con estos campos:

| Campo A3 (JSON) | Campo interno | Tipo | ¿Obligatorio para el cálculo? |
|---|---|---|---|
| `ticker` | `ticker` | str | **Sí** (ej. `S30S6/24hs`) |
| `descripcion` | `description` | str | Recomendado (se usa para el matching por atributos) |
| `tipoEmision` | `issue_type` | str | No |
| `segmento` | `segment` | str | No |
| `codigoSegmento` | `segment_code` | str | No |
| `plazo` | `term` | str | **Sí**: el cálculo exige `001` (24 hs) |
| `codigoPlazo` | `term_code` | str | No |
| `moneda` | `currency` | str | Recomendado |
| `fecha` | `market_date` | fecha ISO | **Sí**: si falta, la fila se rechaza |
| `fechaLiquidacion` | `settlement_date` | fecha ISO | **Sí** para tasas (`0001-01-01` = no aplica → `null`) |
| `precioUltimo` | `last_price` | número | **Sí** (o `precioCierre`, elegido explícitamente) |
| `precioCierre` | `close_price` | número | **Sí** (alternativa a último) |
| `precioCierreAnterior` | `previous_close` | número | No |
| `precioMinimo` / `precioMaximo` | `min_price` / `max_price` | número | No |
| `ultimaTasa` | `provider_rate` | número | No (se guarda como dato crudo; **no** se usa como tasa calculada) |
| `volumenAcumulado` | `accumulated_volume` | número | No |
| `montoAcumulado` | `accumulated_amount` | número | No |
| `openInterest` | `open_interest` | número | No |
| `variacion` | `variation` | número | No |
| `bid` / `ask` | `bid` / `ask` | número | No (A3 contado no los publica) |

**Reglas de parseo:** el JSON se parsea con `parse_float=Decimal` y cada número se convierte con `Decimal(str(x))`, así que **nunca pasa por float**. Strings vacíos → `null`. Una fecha inválida o un body que no sea lista → `NormalizationError`.

**Errores HTTP:** 401/403 → `ProviderAuthError`; otros HTTP → `ProviderResponseError`; red/timeout → `ProviderConnectionError`. El scheduler saltea el tick y sigue corriendo.

**Convención de ticker:** en producción, A3 devuelve para plazo `001` tickers con sufijo `/24hs` (ej. `S30S6/24hs`). El toolkit quita ese sufijo **solo** cuando `plazo == "001"` para obtener el ticker contractual (`S30S6`).

### 4.2 Requisitos mínimos para la API interna

Para reemplazar A3 sin tocar el motor, a la API interna le alcanza con cumplir esto:

1. **Precio de mercado secundario** de LECAP/BONCAP, **liquidación 24 hs (T+1)**, en **ARS por VN 100**.
2. Tipo de precio **identificado explícitamente**: último operado y/o cierre. El toolkit no sustituye uno por otro en silencio.
3. **Fecha de la observación** (`market_date`) y **fecha de liquidación** (`settlement_date`) asociadas a cada precio.
4. **Ticker** del instrumento (idealmente el contractual, ej. `S30S6`, o uno documentado con su sufijo).
5. Números como **string o decimal JSON exacto**, sin pasar por float binario del lado del servidor si es posible.
6. Autenticación por **header** (API key/token), porque el toolkit la lee de variables de entorno.
7. Idealmente, también estos **datos contractuales** por instrumento, que hoy salen de Excel del Tesoro o están embebidos en el HTML (ver §14):
   - fecha de emisión, fecha de vencimiento, **TEM de emisión** (tasa mensual de capitalización), VN de referencia y VPV oficial publicado.
8. Opcional: timestamp de la cotización (hora), volumen, cauciones y forex (para investigación futura).

**Cómo se integra:** se agrega un provider nuevo (ej. `providers/interna/`) que implemente el `Protocol`:

```python
class MarketDataProvider(Protocol):
    name: ProviderName
    def fetch_quotes(self, query: QuoteQuery) -> Tuple[MarketQuote, ...]: ...
    def health_check(self) -> bool: ...
```

Devuelve `MarketQuote` inmutables (§5.1). No persiste, no cachea y no calcula. El resto del toolkit no cambia.

### 4.3 Otras fuentes

| Fuente | Qué aporta | Frecuencia | Auth |
|---|---|---|---|
| Secretaría de Finanzas, `https://www.argentina.gob.ar/economia/finanzas/noticias` | Resultados de licitación → candidatos de letras (familia, moneda, vencimiento, ticker si figura) | Cada 24 h | No |
| `data/colocaciones_*.xlsx` (hoja `Letras`) | Registro contractual: nombre, emisión, **vencimiento autoritativo**, resolución | Manual | No |
| Visor público A3 futuros, `https://matbarofex.primary.ventures/api/v2` (`/ref-data`, `/trades/securities/{id}`) | Contratos DLR y últimas operaciones | Contratos 24 h, trades 15 min | No |

---

## 5. Modelos de datos

Todos son `@dataclass(frozen=True)` (inmutables), con `Decimal` para magnitudes y `date`/`datetime` para fechas.

### 5.1 `MarketQuote` (una observación de precio)

`ticker, description, issue_type, segment, segment_code, term, term_code, currency, market_date, settlement_date, last_price, close_price, previous_close, min_price, max_price, provider_rate, accumulated_volume, accumulated_amount, open_interest, variation, bid, ask, instrument_class, provider, retrieved_at (UTC)`

### 5.2 `QuoteQuery`

`instrument_class` (obligatorio) + `segmento, plazo, moneda, ticker, page_number` (opcionales).

### 5.3 Enums principales

- `InstrumentClass`: `FIXED_INCOME, CAUCION, FOREX, REPO, FX_FUTURE, COMMODITY_FUTURE, RATE_FUTURE, INDEX_FUTURE`
- `ProviderName`: `A3, A3_PUBLIC_VIEWER, IOL, CSV, MOCK` (se agrega uno para la API interna)
- `PriceType`: `SETTLEMENT, LAST, BID, ASK, MID`
- `TreasuryInstrumentFamily`: `LECAP, BONCAP, LEDE, LECER, LELINK, TREASURY_BILL, TREASURY_BOND`
- `InstrumentLifecycleStatus`: `PENDING_SECONDARY_MARKET, PENDING_MATCH, ACTIVE_FOR_ANALYSIS, MATURED`
- `InstrumentMatchMethod`: `NONE, EXACT_TICKER, UNIQUE_ATTRIBUTES, AMBIGUOUS, RETAINED_ACTIVE`
- `MethodologyStatus`: `PENDING, UNDER_REVIEW, VALIDATED`

### 5.4 Lifecycle y contractual

- `TreasuryInstrumentCandidate`: `source_id, origin (TREASURY_OFFICIAL|MANUAL), description, ticker?, instrument_family?, currency?, maturity_date?, auction_date, issue_action?, source_url?, source_title, source_fields[], discovered_at, manual_reference?`
- `InstrumentLifecycleDecision`: `candidate, status, match_method, matched_ticker?, activation_evidence?, evaluated_at`
- `ContractualLetra`: `name, family, currency, issue_date, maturity_date, resolution, source_file`

### 5.5 Futuros

- `FuturesContractReference`: `security_id, ticker, description, cfi_code, market_id, …, maturity_month_year, source_end_date, days_to_expiration, contract_multiplier, price_precision, min_price_increment, settlement_type, underlying_*`
- `FuturesTradeObservation`: `trade_id, security_id, ticker, provider_timestamp, provider_timezone, timestamp_utc, price, volume, trade_type, side_codes, seller_party, buyer_party`

---

## 6. Motor financiero: convenciones, ecuaciones y algoritmos

### 6.0 Reglas comunes a todos los módulos

- Una función pública por módulo, que recibe **un** input inmutable y devuelve **un** resultado inmutable.
- **Solo `Decimal`**, con precisión de trabajo de **50 dígitos** (`localcontext().prec = 50`). Prohibido `float`.
- **Sin redondeo intermedio.** El redondeo es solo de presentación y nunca realimenta un cálculo.
- Orden de validación: campos → tipos → valores financieros → fechas → aprobación metodológica → cálculo → resultado.
- Cada resultado lleva un `methodology_status` que referencia su research.
- Cada módulo define una excepción base y excepciones de dominio específicas.

### 6.1 Conteo de días 30/360 Tesoro (`day_count.py`)

Adaptación aprobada del 30/360 US/NASD (Excel `DAYS360`) para capitalizables del Tesoro. Fuente: Secretaría de Finanzas, "Metodología de cálculo para la letra capitalizable en pesos" (20/03/2024).

**Algoritmo** `days_30_360_treasury(start, end)`:

```
d1 = start.day ; d2 = end.day
# Inicio
si start es el último día de febrero (28, o 29 si es bisiesto): d1 = 30
si no, si d1 == 31:                                              d1 = 30
# Fin
si end es el último día de febrero:                              d2 = 30
si no, si d2 == 31 y d1 == 30:                                   d2 = 30
días = 360·(y2 − y1) + 30·(m2 − m1) + (d2 − d1)
```

Notas:

- Un día 30 común se mantiene como 30 (un 30 de septiembre final no pasa a octubre).
- La regla de febrero es una **extensión explícita del proyecto**, así que no equivale exactamente a Excel en todos los pares de fechas.
- Se aplica **solo** a LECAP/BONCAP. No debe generalizarse a otras familias.

### 6.2 Valor al vencimiento, VPV (`maturity_value.py`, R-001)

**Inputs:** `instrument_type` (LECAP|BONCAP), `issue_date`, `maturity_date`, `monthly_issue_rate` (TEM de emisión, decimal: 2,53 % → `0.0253`), `reference_face_value` (VN, normalmente 100), `official_maturity_value` (el VPV publicado, para comparar), `source_reference`.

**Ecuaciones:**

$$
n_{\text{meses}} = \frac{\text{DAYS360}_{\text{Tesoro}}(\text{emisión},\ \text{vencimiento})}{30}
$$

$$
\text{VPV} = \text{VN} \times (1 + \text{TEM}_{\text{emisión}})^{\,n_{\text{meses}}}
$$

**Salida:** `maturity_value`, `reference_face_value`, `official_maturity_value`, `absolute_difference = |VPV_calc − VPV_oficial|`, `methodology_status`.

**Validaciones:** VN > 0 (`InvalidFaceValueError`); TEM ≥ 0 (`InvalidIssueRateError`); emisión < vencimiento (`InvalidInstrumentDatesError`).

**Convención de VN:** los valores se expresan por **VN 100**, salvo que la fuente indique otra base.

### 6.3 Rendimientos de mercado secundario (`letras_yield.py`, R-002/003/004, convención IAMC)

**Inputs:** `market_price` (ARS por VN 100, misma base que el VPV), `settlement_date`, `maturity_date`, `maturity_value` (VPV), `source_reference`.

**Ecuaciones:**

$$
D = \text{días corridos (calendario) entre liquidación y vencimiento} \quad \text{(ACT/365)}
$$

$$
\text{HPR} = \frac{\text{VPV}}{P} - 1
$$

$$
\text{TEA (TIREA)} = (1 + \text{HPR})^{365/D} - 1
$$

$$
\text{TEM} = (1 + \text{TEA})^{1/12} - 1
$$

$$
\text{TNA} = \text{TEM} \times 12 \qquad \text{(nominal anual con capitalización mensual)}
$$

**Salida:** `holding_period_return, tna, tea, tem, residual_days_actual, methodology_status`.

**Validaciones:** P > 0; VPV > 0; liquidación < vencimiento; D > 0.

**Puntos importantes:**

- El plazo residual usa **días reales / 365**, **no** 30/360. El 30/360 se usa solo para el VPV (emisión → vencimiento).
- `TNA = TEM × 12` es la definición del glosario IAMC. La versión anterior (`HPR × 360 / días30360`) **fue rechazada** porque no reproducía la TNA publicada por IAMC.
- Metodología validada contra el Informe Diario BYMA/IAMC del 10/08/2026 (instrumento S16O6).

### 6.4 Duration (`duration.py`, R-005): solo letras de pago único

**Inputs:** `settlement_date`, `maturity_date`, `tea`, `compounding_frequency` *m* (≥ 1; el dashboard usa 12 por defecto), `source_reference`.

**Ecuaciones:**

$$
\text{Macaulay (años)} = \frac{\text{DAYS360}_{\text{Tesoro}}(\text{liquidación},\ \text{vencimiento})}{360}
$$

$$
y_m = (1 + \text{TEA})^{1/m} - 1
$$

$$
\text{Duration modificada} = \frac{\text{Macaulay}}{1 + y_m}
$$

Para un instrumento de un solo flujo, Macaulay = tiempo al vencimiento. La frecuencia *m* se informa siempre en el resultado.

**Validaciones:** liquidación < vencimiento; TEA > −1; *m* ≥ 1; días 30/360 > 0.

**Fuera de alcance:** bonos con cupones, que requieren duration ponderada por valor presente y no está aprobada.

### 6.5 Ejemplo numérico reproducible (S30S6)

Salida real del motor, ejecutada sobre el código del zip:

| Paso | Input | Resultado |
|---|---|---|
| VPV | Emisión 16/03/2026, vto 30/09/2026, TEM 2,53 %, VN 100 | **117,5356258958…** (coincide con CASE-001 y el Excel de referencia; dif. ≈ 7,7e-14) |
| Tasas | Precio 113,70; liquidación 11/08/2026 | D = 50 días; HPR = 3,3735 %; TEA = 27,4049 %; TEM = 2,0388 %; TNA = 24,4661 % |
| Duration | *m* = 12 | 30/360 = 49 días; Macaulay = 0,13611 años; Modificada = 0,13339 |

*(El precio y la fecha de este ejemplo son ilustrativos del cálculo. Los casos formales están en `examples/03_validation_cases/`.)*

### 6.6 Elegibilidad de cálculo por familia (`calculation_eligibility.py`)

| Familia | ¿Se calcula? | Motivo |
|---|---|---|
| LECAP, BONCAP | ✅ | Metodología aprobada (R-001..R-004) |
| LELINK | ❌ | El VPV depende del ajuste por dólar (R-006 en revisión) |
| LECER | ❌ | El VPV depende del coeficiente CER |
| LEDE | ❌ | Fuera del alcance aprobado |
| Genéricas / desconocidas | ❌ | No clasificadas |

Estas familias se **muestran** pero **no se calculan**, siempre con el motivo visible.

---

## 7. Reglas de orquestación

Estas reglas viven entre los datos y el motor, y la API interna debe permitir cumplirlas:

1. **Plazo único:** para tasas solo se usan cotizaciones con `plazo == "001"` (24 hs). No se mezclan `000` y `001`.
2. **Selección explícita de precio:** se usa `last_price` **o** `close_price` según lo que elija el usuario. Si falta el elegido, el instrumento queda "sin precio"; **no** se usa el otro como reemplazo.
3. **Alineación temporal obligatoria:** HPR/TEA/TEM/TNA/Duration modificada se calculan **solo si** `market_date` del precio es igual a la fecha de compra seleccionada. Si no coincide, las tasas corrientes quedan **no disponibles**; un precio histórico nunca se re-etiqueta como actual.
   - Caso real rechazado: una TEA de ≈ 258,44 % para S14G6, que mezclaba un precio histórico con una fecha posterior.
4. **Fecha de liquidación:** si el precio está alineado y el proveedor informa `settlement_date`, se usa esa. Si no, se usa el siguiente día hábil (T+1) según un calendario de feriados argentinos (hoy cargado a mano en el HTML para 2026 y 01/01/2027).
5. **Refresco manual:** el botón ↻ alinea la fecha de compra con la última `market_date` disponible y muestra una advertencia si es anterior a hoy.

---

## 8. Ciclo de vida de instrumentos (`services/instrument_lifecycle.py`)

Separa la **disponibilidad operativa** (¿la letra existe y cotiza?) de la **validación financiera**. `ACTIVE_FOR_ANALYSIS` **no** implica que el cálculo esté validado.

**Algoritmo** `evaluate(candidate, quotes, as_of)`:

```
1. Si candidate.maturity_date <= as_of                   → MATURED
2. Si la decisión previa era ACTIVE_FOR_ANALYSIS         → se mantiene (RETAINED_ACTIVE)
3. Filtrar quotes: provider A3, FIXED_INCOME, ticker normalizable
   (quitar "/24HS" si plazo = 001); quedarse con la observación más temprana por ticker
4. Si la fuente oficial trae ticker:
     ¿existe en A3?  sí → ACTIVE_FOR_ANALYSIS (EXACT_TICKER) + evidencia
                     no → PENDING_SECONDARY_MARKET
5. Si no trae ticker: se exigen familia, moneda y vencimiento explícitos.
     Si falta alguno → PENDING_MATCH
     Buscar tickers A3 cuya descripción tenga exactamente (familia, moneda, vencimiento):
       1 match  → ACTIVE_FOR_ANALYSIS (UNIQUE_ATTRIBUTES)
       >1 match → PENDING_MATCH (AMBIGUOUS)
       0 match  → PENDING_MATCH (NONE)
```

**Nunca** se deduce un ticker ni un vencimiento a partir de una fecha o de otro ticker. Los vencimientos se resuelven en este orden: (1) explícito en la fuente → (2) match único en el registro de colocaciones → (3) `UNRESOLVED`.

---

## 9. Persistencia (SQLite: `data/market/market_data.sqlite`)

Los `Decimal` se guardan como **TEXT** para no perder precisión.

| Tabla | Clave | Contenido |
|---|---|---|
| `quotes` | `(ticker, instrument_class, term, market_date, provider)` | Todas las columnas de `MarketQuote`; se guarda un snapshot por ciclo y se acumula historia diaria |
| `instrument_lifecycle` | `source_id` | Candidato del Tesoro + estado, método de match, ticker y evidencia de activación |
| `futures_contracts` | `security_id` (ticker único) | Referencia de contratos DLR |
| `futures_trades` | `(trade_id, security_id)` | Operaciones observadas |

---

## 10. Scheduler y procesos

| Proceso | Qué hace | Intervalo |
|---|---|---|
| `LifecycleScheduler` (`tools/run_treasury_bill_scheduler.py`) | Tesoro: buscar licitaciones nuevas y actualizar candidatos | Al inicio y cada 24 h |
| Ídem | A3: traer toda la renta fija (todas las páginas), guardar quotes y re-evaluar el lifecycle | Al inicio y cada 15 min |
| Futuros (`tools/run_futures_scheduler.py`) | Contratos DLR / últimos trades | 24 h / 15 min |
| macOS `launchd` (`com.fixedincome.morningsync`) | Arranca el scheduler en PROD | Todos los días a las 09:30 |

- Un fallo de una fuente no frena la otra.
- Timeouts y errores de red se convierten en `ProviderConnectionError` y el tick se saltea.
- Un lock a nivel de sistema operativo evita schedulers duplicados.
- **Producción requiere** `--environment PROD --allow-production`. El default es UAT.

---

## 11. Dashboard local y endpoints HTTP

Servidor `ThreadingHTTPServer` que escucha **solo en loopback** (`127.0.0.1:8765`), con headers de seguridad (CSP, `X-Frame-Options: DENY`, `nosniff`, `no-store`). Solo lee SQLite: no contacta a A3 ni calcula.

| Ruta | Respuesta |
|---|---|
| `/` | `outputs/modelo_lecap_boncap.html` (calculadora LECAP/BONCAP) |
| `/futures` | `outputs/futuros_dolar.html` |
| `/api/market/quotes` | Últimas quotes de renta fija **plazo 001**, con los Decimal como string. Flags: `price_selection_is_explicit: true`, `silent_price_fallback: false` |
| `/api/lifecycle` | Estados del universo de letras, con elegibilidad de cálculo y su motivo |
| `/api/futures` | Contratos DLR + último trade (sin spot ni cálculos, R-009) |
| `/api/health` | Salud del servicio |

---

## 12. Metodologías en investigación (no implementadas)

Se documentan para dar contexto. **No deben usarse en producción.**

### R-006: LELINK (dollar-linked), en revisión

Fórmulas candidatas documentadas (convención de anualización **abierta**):

```
HPR_linked = R / P − 1         (R = valor de rescate linked, fijado en 100)
TEA_linked = (1 + HPR_linked)^(365/D) − 1
TEM_linked = (1 + TEA_linked)^(1/12) − 1
TNA_linked = TEM_linked × 12
HPR_pesos  = (1 + HPR_linked) × (FX_m / FX_s) − 1
```

- Pago al vencimiento en pesos = `VN × A3500` del **3.er día hábil anterior** al vencimiento (Res. Conjunta SF/SH 31/2025).
- Sigue abierto si el mercado cotiza TIR efectiva o TNA, y la base de días.

### R-009: forward de dólar / devaluación implícita, en revisión

- Único valor observado y permitido: `forward_points = precio_futuro − spot`, con disclaimer.
- Familia de fórmulas registrada, **sin aprobar**: `F = S·(1+R)^t`, `F = S·e^{(r_d − r_f)T}`, etc.
- `calculate_fx_forward_metrics()` **lanza `UnvalidatedMethodologyError` a propósito**.
- Pendiente: contrato de spot, campo de precio del proveedor, política temporal y curvas ARS/USD.

---

## 13. Tests y validación

- **166 tests, todos pasan** (`pytest`, ejecutados sobre este paquete).
- Cubren: 30/360 (incluye febrero bisiesto y no bisiesto), VPV, HPR/TNA/TEA/TEM, duration, normalización y paginación A3, transporte con timeouts, repositorios SQLite, activación de instrumentos, scheduler, futuros y alineación temporal del dashboard.
- Todos los tests corren **offline** (transporte HTTP inyectable con fixtures).
- Casos de validación: `examples/03_validation_cases/case001_S30S6.json`, `case002_S31G6.json`.
- Referencias de validación: Informe Diario BYMA/IAMC, Glosario metodológico IAMC, publicación de la Secretaría de Finanzas y calculadoras Excel de referencia en `examples/01_calculators/`.

---

## 14. Brechas conocidas y puntos de atención

Conviene tenerlas en cuenta al diseñar la API interna:

1. **Datos contractuales embebidos en el HTML.** La calculadora del dashboard (`modelo_lecap_boncap.html`) tiene un array `DATA` con emisión, vencimiento y TEM de emisión de 13 LECAP/BONCAP, cargado a mano desde el Informe Diario del 10/08/2026. Las letras nuevas aparecen como "Faltan datos contractuales". **Una API interna que entregue datos contractuales (emisión, vencimiento, TEM de emisión, VPV oficial) resolvería esto.**
2. **Doble implementación en el HTML.** El dashboard recalcula VPV/tasas/duration en JavaScript con `Number` (float) usando las mismas fórmulas. El motor Python (`Decimal`) es la referencia validada. Lo ideal a futuro es que el dashboard consuma resultados del motor.
3. **Feriados hardcodeados** en el HTML (2026 y 01/01/2027) para el T+1. Hace falta una fuente de calendario de mercado.
4. **Convención de liquidación T+1: "pendiente de validación"** en `market_conventions.md`.
5. **Base path de A3 ambiguo** (`MarketData/v1` vs `api/v1`). Se configura en un solo lugar.
6. **Precio en ARS por VN 100:** observado, no validado como contrato de un proveedor. Conviene que la API interna lo documente de forma explícita.
7. `ultimaTasa` del proveedor se guarda como dato crudo y **no** reemplaza las tasas calculadas.
8. **Precio de los instrumentos dollar-linked.** Cotizan en pesos pero su unidad de cuenta es el dólar linked, y la tasa de conversión no está documentada por el proveedor. Es el requerimiento nuevo de esta versión: ver **Addendum 1**.

---

## 15. Cómo correrlo

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"        # dependencias: openpyxl (+ pytest)
pytest                           # 166 tests

# Credenciales (solo para A3 real): copiar .env.example a .env y completar
#   A3_MARKETDATA_API_KEY_UAT=...   A3_MARKETDATA_API_KEY_PROD=...   A3_MARKETDATA_ENV=UAT

python tools/sync_once.py                    # un refresco puntual
python tools/run_treasury_bill_scheduler.py  # scheduler 24 h / 15 min
python tools/serve_local_dashboard.py        # dashboard en http://127.0.0.1:8765
python tools/run_local_toolkit.py            # scheduler + dashboard juntos (UAT por defecto)
python tools/run_futures_toolkit.py          # pantalla de futuros DLR (:8766)
```

**Excluido del zip a propósito:** `.env` (credenciales), `.venv/`, la base SQLite local, logs, PDFs pesados de bibliografía e informes de mercado, y la documentación propietaria de A3 (`archive/`).


---

# Addendum 1 — Precio de instrumentos dollar-linked (26/10/2026)

**Requerimiento nuevo respecto de la v1.0. Es el único cambio.**

## Qué pasa

Las letras y bonos dollar-linked (LELINK, DLK) cotizan **en pesos**, pero su unidad de cuenta es el **dólar linked**. Para calcular cualquier rendimiento hay que pasar el precio de pesos a dólares linked, y eso requiere un tipo de cambio que el feed de A3 hoy no entrega: el contrato del proveedor deja la **unidad de cotización sin declarar**.

## Por qué no lo podemos resolver de nuestro lado

Se reconstruyó el tipo de cambio implícito a partir de dos informes publicados, y **no coincide con el A3500 del BCRA** de la fecha de cierre:

| Informe | Cierre | TC implícito | A3500 BCRA del día | Diferencia |
|---|---|---|---|---|
| Renta Fija (base BYMA) | 30-09-2026 | 1517,52 | 1517,00 | +0,034% |
| IAMC, Informe Diario Títulos Públicos | 05-10-2026 | 1523,09 | 1520,00 | +0,203% |

La hipótesis es que la pantalla convierte con el **spot mayorista de cierre** y no con el A3500 publicado (cuyo método de cálculo cambió con la Com. "A" 8359, vigente desde 2026). No está documentado en ninguna fuente disponible.

El impacto no es cosmético: en el tramo corto, una diferencia de 0,20% en el tipo de cambio mueve la tasa anualizada hasta **1,3 puntos porcentuales**. Por la *Research First Policy* del proyecto, no podemos poner una tasa no validada en el motor de producción.

## Qué necesitamos de la API interna

En orden de preferencia:

1. **El precio ya expresado en dólares linked por VN 100**, en un campo propio y con la unidad declarada.
2. Si solo se puede entregar en pesos: el precio en pesos **más el tipo de cambio efectivamente usado**, con su valor a precisión completa, su fecha y hora de referencia, y su identidad (A3500 del BCRA o spot mayorista de cierre).
3. En cualquiera de los dos casos: la **unidad de cotización por instrumento** (por VN 100 o por VN 1.000), declarada de forma explícita y no inferida.

## Qué desbloquea

Con cualquiera de las dos primeras opciones, la familia dollar-linked entra al motor de producción. La metodología de cálculo ya está validada y reconciliada contra IAMC y BYMA (ACT/365 efectiva, liquidación T+1, rescate a la par 100); lo único que falta es esta pieza de datos.
