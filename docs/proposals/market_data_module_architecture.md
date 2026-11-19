# Propuesta de Arquitectura — Market Data Module

| Campo | Valor |
|-------|-------|
| Documento | Propuesta de arquitectura (no aprobada) |
| Módulo | `src/market_data/` |
| Estado | 🟡 Arquitectura activa; implementación incremental |
| Autor | AI Agent (a partir de la documentación del proyecto) |
| Fecha | 6 de agosto de 2026 |
| Revisión | v1.3 — ciclo Secretaría → A3 aprobado (10-ago-2026) |
| Requiere aprobación de | Felipe Cagigas |

> **Naturaleza de este documento.** Es el registro de arquitectura del módulo.
> Su implementación es incremental. Ningún cálculo financiero nuevo se
> habilita aquí: todos los cálculos de tasas continúan detrás del Research Gate
> del proyecto (ver §11 y §12).

> **Nota de alineación (v1.1, 6-ago-2026).** Esta revisión incorpora la nueva
> `docs/research/bibliography_review_2026-08-06.md` y el registro
> `docs/research/README.md`. Cambios principales: (1) se corrige la numeración
> de research — **no se inventan R-006..R-010**; la relación forward/futuro de
> dólar ya está registrada como **R-009** (Under Review) y la tasa forward de
> interés es un tema distinto (candidato R-017); (2) se adopta la **separación
> terminológica obligatoria** entre precio forward FX, tasa forward de interés y
> valor de un forward existente — prohibido unificarlos en una sola función
> `forward_rate`; (3) se refleja que el day-count 30/360 del proyecto ya está
> **validado** para LECAP/BONCAP; (4) el proxy futuro≈forward se rotula
> explícitamente **"Under Review"** según R-009.

> **Nota de decisión (v1.2, 6-ago-2026).** Felipe resolvió los puntos abiertos:
> (1) **§11.8 aprobado** — las fórmulas puras viven en el Financial Engine, pero
> **no** en un `futures_implied_rates.py` genérico: se usan módulos explícitos
> (`fx_forward_metrics.py` para precio forward FX y puntos forward; un módulo
> aparte y futuro para tasa forward de interés bajo R-017; otro para el valor de
> un forward existente si algún día entra en alcance). Prohibida una función
> `forward_rate`. (2) **Modelo de precios sin sustitución silenciosa** — se
> conservan *todos* los precios que entregue el proveedor (settlement/ajuste,
> last, bid, ask, volumen); cada vista declara cuál usa y, si falta el pedido, se
> informa faltante en lugar de sustituir. (3) **Política temporal explícita** —
> se guardan timestamp original, zona horaria original, UTC normalizado, momento
> de recepción, fecha de mercado y antigüedad de la observación; spot y futuro
> solo se comparan si están alineados temporalmente. (4) **Spot sin proveedor
> aprobado** hasta documentar la API. (5) **Etapa 0 aprobada** para avanzar
> (interfaces y estructura, sin red ni cálculos). Los detalles de spot, curvas y
> mapeo de precios se resuelven dentro de **R-009** (8 subsecciones).

> **Nota de decisión (v1.3, 10-ago-2026).** Se aprobó el ciclo de vida para
> Letras: la Secretaría de Finanzas descubre y aporta evidencia de resultados;
> A3 / MAE MarketData confirma la visibilidad secundaria; el Toolkit calcula de
> forma separada. La activación es automática y operativa, no una validación
> financiera. Si el ticker oficial falta, sólo se permite una coincidencia única
> por familia, moneda y vencimiento; una coincidencia ambigua permanece
> pendiente. La carga manual continúa como respaldo con trazabilidad explícita.

> **Nota de frecuencia (10-ago-2026).** Felipe aprobó dos ciclos separados:
> Secretaría de Finanzas cada 24 horas para nuevos resultados y A3 / MAE cada
> 15 minutos para precios y confirmación de visibilidad secundaria. Ambos
> comienzan con una ejecución inmediata. La retención continúa indefinida hasta
> una decisión posterior.

---

## 0. Resumen ejecutivo

Se propone una **capa de Market Data** (`src/market_data/`) desacoplada del
proveedor, del almacenamiento y de la presentación, que se convierte en la
única fuente de datos de mercado para todo el Toolkit. La capa expone una
**API interna estable** (`MarketDataAPI`) que cualquier módulo puede consumir
sin conocer si los datos vienen de A3, IOL, un CSV o un mock.

Decisiones ya confirmadas contigo:

1. **Almacenamiento:** SQLite (relacional, fuente de verdad) + export a
   Parquet/CSV/Excel para análisis.
2. **Dashboard:** se define la capa y los contratos de datos ahora; la
   implementación visual va en una etapa posterior sobre la API interna.
3. **Tasas implícitas:** se definen interfaces y estructuras, pero cada cálculo
   lanza `UnvalidatedMethodologyError` hasta tener research aprobado (mismo
   patrón que `maturity_value.py`). Se apoyan en los research **ya existentes**
   del registro (R-009 forward/futuro FX, y R-002/R-003/R-004 para las
   convenciones de anualización), no en research inventados.

Principio rector: **el Market Data Module obtiene, normaliza, almacena y sirve
datos crudos de mercado. No inventa números financieros.** Toda derivación
(tasas, forwards, devaluación implícita) es un cálculo financiero sujeto a la
governance existente.

---

## 1. Estructura de carpetas

Se agrega un único paquete nuevo, `src/market_data/`. **No se modifica ningún
archivo existente** de `src/financial_engine/`.

```text
src/
├── financial_engine/                 # EXISTENTE — intacto
│   └── maturity_value.py
│
├── market_data/                      # NUEVO paquete
│   ├── __init__.py                   # exporta la API interna (fachada)
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py               # dataclasses de configuración
│   │   └── market_data.example.yaml  # plantilla de config (sin secretos)
│   │
│   ├── models/                       # modelos de dominio (Decimal, frozen/slots)
│   │   ├── __init__.py
│   │   ├── enums.py                  # Market, ProviderName, InstrumentClass, PriceType, SyncStatus, MethodologyStatus
│   │   ├── contract.py               # FuturesContract
│   │   ├── quote.py                  # MarketQuote, DailySnapshot
│   │   ├── curve.py                  # CurvePoint, FuturesCurve
│   │   └── exceptions.py             # jerarquía de excepciones del módulo
│   │
│   ├── providers/                    # DATA PROVIDERS (intercambiables)
│   │   ├── __init__.py
│   │   ├── base.py                   # Protocol MarketDataProvider + DTOs crudos
│   │   ├── normalization.py          # payload crudo del proveedor -> modelos de dominio
│   │   ├── a3_provider.py            # A3 Mercados / Matba Rofex
│   │   ├── iol_provider.py           # (futuro) InvertirOnline
│   │   ├── csv_provider.py           # lee fixtures/exports para pruebas y offline
│   │   └── mock_provider.py          # datos deterministas para tests
│   │
│   ├── storage/                      # PERSISTENCIA (intercambiable)
│   │   ├── __init__.py
│   │   ├── base.py                   # Protocol MarketDataRepository
│   │   ├── schema.sql                # DDL de SQLite
│   │   ├── sqlite_repository.py      # implementación SQLite
│   │   ├── parquet_store.py          # snapshots/series a Parquet
│   │   └── migrations/               # versionado del esquema
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   └── cache.py                  # Protocol Cache + TTLFileCache / InMemoryCache
│   │
│   ├── services/                     # ORQUESTACIÓN (sin fórmulas financieras)
│   │   ├── __init__.py
│   │   ├── sync_service.py           # fetch -> normalizar -> detectar cambios -> persistir
│   │   ├── curve_service.py          # arma curvas ordenadas por vencimiento
│   │   ├── snapshot_service.py       # snapshots diarios de la curva
│   │   └── metrics_service.py        # estadística descriptiva (pendiente, spreads, min/max)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── market_data_api.py        # FACHADA pública del módulo
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   └── exporters.py              # CSV / Excel / Parquet
│   │
│   └── observability/
│       ├── __init__.py
│       └── sync_log.py               # eventos estructurados de sincronización
│
└── financial_engine/
    └── fx_forward_metrics.py          # NUEVO módulo GATED — precio forward FX y puntos forward (R-009)
    # Futuro (fuera de scope hoy, módulos separados por mandato terminológico):
    #   forward_interest_rate.py       # tasa forward de interés — R-017
    #   forward_contract_value.py      # valor de un forward existente — si entra en alcance
```

Documentación y datos asociados (fuera de `src/`):

```text
docs/
├── proposals/
│   └── market_data_module_architecture.md   # este documento
├── research/
│   ├── 009_forward_points_devaluation.md      # EXISTENTE (R-009, Under Review) — controla el proxy forward/futuro FX
│   ├── README.md                              # EXISTENTE — registro de estado de research
│   └── bibliography_review_2026-08-06.md      # EXISTENTE — auditoría bibliográfica
└── providers/
    └── a3_provider_contract.md                # NUEVO — esquema, auth, timestamps, semántica de precio

data/
└── market/
    ├── market_data.sqlite                     # base de datos (gitignored)
    └── exports/                               # Parquet/CSV/Excel generados
```

**Sobre el empaquetado.** Hoy `pyproject.toml` no declara paquetes y `src/` se
importa vía `pythonpath = ["src"]`. Propongo mantener ese esquema para no tocar
la config existente: `market_data` se importa como `from market_data.api import
MarketDataAPI`. Cuando se estabilice la API pública, se declara el paquete
formalmente (decisión diferida, ver §11).

---

## 2. Nuevos módulos

| Módulo | Responsabilidad única | Depende de | Nunca depende de |
|--------|----------------------|------------|------------------|
| `config` | Cargar y validar configuración desacoplada | — | proveedores, IO de mercado |
| `models` | Estructuras de dominio inmutables (Decimal) | `enums` | proveedores, storage, red |
| `providers` | Traer datos crudos y normalizarlos a modelos | `models` | storage, services, dashboard |
| `storage` | Persistir y consultar modelos | `models` | proveedores, red |
| `cache` | Evitar llamadas redundantes al proveedor | — | fórmulas financieras |
| `services` | Orquestar el flujo, detectar altas/bajas, estadística descriptiva | `providers`, `storage`, `cache`, `models` | dashboard, red directa |
| `api` | Fachada estable para el resto del Toolkit | `services`, `storage`, `models` | proveedores concretos |
| `export` | Serializar a CSV/Excel/Parquet | `models`, `storage` | proveedores |
| `observability` | Logging estructurado de sincronización | `models` | fórmulas financieras |
| `financial_engine/fx_forward_metrics` | Fórmulas puras de precio forward FX y puntos forward (GATED, R-009) | `Decimal`, `date` | red, storage, providers, UI |

Regla transversal: **la dirección de dependencia sigue el diagrama del
`financial_specification.md`:**

```text
Providers  ->  Storage  ->  Services  ->  API  ->  (Dashboard / Toolkit)
                                 │
                                 └── (orquesta) ──► financial_engine (fórmulas puras)
```

El financial engine nunca llama hacia arriba: recibe `Decimal` puros y devuelve
resultados inmutables, exactamente como el módulo existente.

---

## 3. Nuevos modelos

Todos con `@dataclass(frozen=True, slots=True)`, `Decimal` para magnitudes
financieras y `date`/`datetime` para tiempo, siguiendo `financial_specification.md`.

### 3.1 Enums (`models/enums.py`)

```python
class Market(Enum):
    A3 = "A3"            # A3 Mercados (ex Matba Rofex)

class ProviderName(Enum):
    A3 = "A3"
    IOL = "IOL"
    CSV = "CSV"
    MOCK = "MOCK"

class InstrumentClass(Enum):
    FX_FUTURE = "FX_FUTURE"          # futuro de dólar (scope inicial)
    COMMODITY_FUTURE = "COMMODITY_FUTURE"
    RATE_FUTURE = "RATE_FUTURE"
    INDEX_FUTURE = "INDEX_FUTURE"
    # extensible sin tocar el resto del sistema

class PriceType(Enum):
    """Qué precio selecciona explícitamente una vista. Sin sustitución silenciosa:
    si el precio pedido no existe en la cotización, la respuesta lo informa como
    faltante en lugar de reemplazarlo por otro."""
    SETTLEMENT = "SETTLEMENT"    # ajuste oficial — preferente para histórico diario
    LAST = "LAST"               # último operado — vista intradiaria
    BID = "BID"                 # mejor compra — precio ejecutable de venta
    ASK = "ASK"                 # mejor venta — precio ejecutable de compra
    MID = "MID"                 # indicativo — se calcula explícito desde bid/ask

class SyncStatus(Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class MethodologyStatus(Enum):
    PENDING = "PENDING"              # sin research aprobado
    UNDER_REVIEW = "UNDER_REVIEW"    # research abierto (p.ej. R-009), no implementable
    VALIDATED = "VALIDATED"          # research validado
    # Nota: "validado" NO implica aprobado para producción. La habilitación de
    # producción requiere además "Implementation Approved: Yes" (Research First).
```

### 3.2 Contrato (`models/contract.py`)

```python
@dataclass(frozen=True, slots=True)
class FuturesContract:
    ticker: str                     # p.ej. "DLR/AGO26"
    instrument_class: InstrumentClass
    underlying_asset: str           # "USD"
    market: Market
    maturity_date: date
    currency: str                   # "ARS"
    first_seen: date                # detección automática de altas
    is_active: bool                 # se marca inactivo al vencer
```

Los campos derivados del tiempo (`days_to_maturity`, `months_to_maturity`,
`year_fraction`) **no se guardan como datos crudos**: se calculan respecto de
una fecha de valuación. Los días/meses son aritmética de calendario neutral. El
`year_fraction` usa el day-count **Treasury-adapted 30/360 ya validado** para
LECAP/BONCAP (`market_conventions.md`, v1.3). Advertencia del propio documento:
esa convención está aprobada para LECAP/BONCAP y **no debe generalizarse
silenciosamente a otras familias**; su aplicación a los futuros de dólar es
justamente un ítem abierto de R-009 (convención de capitalización y year
fraction), así que hasta confirmarlo el `year_fraction` de la curva de futuros
se marca `UNDER_REVIEW`.

### 3.3 Cotización y snapshot (`models/quote.py`)

Se conservan **todos** los precios que entregue el proveedor; ninguno se
descarta ni se sustituye por otro. Un precio ausente es `None` (faltante
explícito), nunca un reemplazo silencioso.

```python
@dataclass(frozen=True, slots=True)
class MarketQuote:
    ticker: str
    # --- Precios: se conserva TODO lo que publique el proveedor; None si falta ---
    settlement_price: Decimal | None    # ajuste / settlement oficial
    last_price: Decimal | None          # último operado (intradiario)
    bid: Decimal | None                 # mejor compra
    ask: Decimal | None                 # mejor venta
    # 'mid' NO se almacena: es indicativo y se calcula explícito desde bid/ask
    #  en la vista que lo pida, dejando registro de que es derivado.
    volume: Decimal | None
    open_interest: Decimal | None
    previous_settlement: Decimal | None
    daily_change: Decimal | None        # dato del proveedor o (last - prev), trivial
    daily_change_pct: Decimal | None
    # --- Política temporal (ver recuadro) ---
    provider_timestamp: datetime        # timestamp original tal como lo da el proveedor
    provider_timezone: str              # zona horaria original declarada
    timestamp_utc: datetime             # normalizado a UTC
    received_at: datetime               # momento de recepción por el módulo
    market_date: date                   # fecha de mercado (rueda)
    provider: ProviderName
    # observation_age (antigüedad) se deriva: received_at - timestamp_utc.

@dataclass(frozen=True, slots=True)
class DailySnapshot:
    snapshot_date: date
    market: Market
    instrument_class: InstrumentClass
    quotes: tuple[MarketQuote, ...]         # inmutable
    provider: ProviderName
```

> **Selección de precio por vista (sin sustitución silenciosa).** El modelo
> guarda el conjunto completo; cada vista declara qué `PriceType` usa: histórico
> diario → `SETTLEMENT`; intradiario → `LAST`; compra ejecutable → `ASK`; venta
> ejecutable → `BID`; indicativo → `MID` (calculado explícito desde bid/ask). Si
> se pide `SETTLEMENT` y no existe, la respuesta indica *faltante*; **no** se
> reemplaza por `LAST`.

> **Política temporal.** Guardar siempre: timestamp original del proveedor, su
> zona horaria, el UTC normalizado, el momento de recepción, la fecha de mercado
> y la antigüedad derivada. Spot y futuro **solo** se comparan cuando están
> alineados temporalmente; mezclar, p.ej., un spot de cierre con un futuro
> intradiario exige una advertencia explícita en la vista.

> `daily_change`/`daily_change_pct` son **datos de mercado** si el proveedor los
> publica; si se derivan, es la aritmética trivial `last - previous`. Cualquier
> cosa con tasas, capitalización o anualización es fórmula financiera y va gated.

### 3.4 Curva (`models/curve.py`)

```python
@dataclass(frozen=True, slots=True)
class CurvePoint:
    ticker: str
    maturity_date: date
    days_to_maturity: int
    price: Decimal
    implied_rate: Decimal | None      # None hasta que el research gate se abra
    methodology_status: MethodologyStatus

@dataclass(frozen=True, slots=True)
class FuturesCurve:
    valuation_date: date
    underlying_asset: str
    points: tuple[CurvePoint, ...]    # ordenados por vencimiento
    provider: ProviderName
```

**Vista forward FX (concepto separado, R-009).** Para no mezclar el precio
forward FX con la tasa forward de interés, se modela aparte:

```python
@dataclass(frozen=True, slots=True)
class FxForwardPoint:
    ticker: str
    maturity_date: date
    spot: Decimal                      # dato crudo (fuente de spot a definir)
    future_price: Decimal              # dato crudo del proveedor
    forward_points: Decimal            # future_price - spot (aritmética trivial)
    implied_devaluation: Decimal | None  # None + UNDER_REVIEW hasta R-009
    methodology_status: MethodologyStatus

@dataclass(frozen=True, slots=True)
class FxForwardCurve:
    valuation_date: date
    underlying_asset: str              # "USD"
    points: tuple[FxForwardPoint, ...]
    provider: ProviderName
    futures_as_forward_disclaimer: str  # rótulo obligatorio: proxy "Under Review" (R-009)
```

> El campo `futures_as_forward_disclaimer` no es decorativo: R-009 exige tratar
> "futuro = forward" como **aproximación** (el settlement diario puede separarlos)
> y el roadmap exige que todo dashboard **divulgue el estado de cada métrica**.

> **Dos cálculos distintos, no confundirlos (R-009).**
> (a) **Comparación observada:** `forward_points = future_price − spot`. Es
> aritmética trivial, **no** requiere curvas de tasas. Se puede exponer como dato
> (con la advertencia de alineación temporal spot/futuro).
> (b) **Forward teórico por paridad:** requiere una curva de financiación en ARS,
> otra en USD y una convención temporal compatible (capitalización, day count,
> fecha/hora de ambas curvas). Es fórmula financiera **gated**: no se selecciona
> ninguna curva sin research específico. Por eso `implied_devaluation` queda
> `None` + `UNDER_REVIEW` hasta que R-009 cierre.

### 3.5 Excepciones (`models/exceptions.py`)

Una base + específicas, según Exception Policy del proyecto:

```text
MarketDataError                      (base)
├── ProviderError
│   ├── ProviderConnectionError
│   ├── ProviderResponseError
│   └── ProviderAuthError
├── NormalizationError
├── StorageError
│   ├── SchemaVersionError
│   └── RepositoryIntegrityError
├── ConfigurationError
└── CacheError
```

Los cálculos gated reutilizan `UnvalidatedMethodologyError` del engine
(patrón ya existente), no se duplica.

---

## 4. Nuevos Data Providers

El punto central de tu pedido. Se define una **interfaz genérica** que
desacopla al Toolkit de cualquier API concreta.

### 4.1 Interfaz (`providers/base.py`)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MarketDataProvider(Protocol):
    """Contrato que todo proveedor de datos de mercado debe cumplir."""

    name: ProviderName

    def list_contracts(
        self, instrument_class: InstrumentClass
    ) -> tuple[FuturesContract, ...]:
        """Descubre contratos disponibles (detecta altas automáticamente)."""

    def fetch_quotes(
        self, tickers: Sequence[str]
    ) -> tuple[MarketQuote, ...]:
        """Últimas cotizaciones para los tickers dados."""

    def fetch_snapshot(
        self, instrument_class: InstrumentClass
    ) -> DailySnapshot:
        """Foto completa del segmento en un momento dado."""

    def health_check(self) -> bool:
        """Disponibilidad del proveedor (para logging y failover futuro)."""
```

Se usa `Protocol` (no herencia) para evitar acoplamiento: un proveedor solo
necesita cumplir la forma, no importar una clase base. `runtime_checkable`
permite validarlo en tests.

### 4.2 Implementaciones

| Provider | Uso | Notas |
|----------|-----|-------|
| `A3Provider` | Producción, futuros de dólar | Consume la API oficial A3 / Matba Rofex. Toda su lógica de red vive aquí y solo aquí. |
| `IOLProvider` | Futuro | Placeholder documentado; se añade sin tocar el resto. |
| `CSVProvider` | Pruebas / offline | Lee exports o fixtures como si fueran el proveedor; permite trabajar sin red. |
| `MockProvider` | Tests unitarios | Datos deterministas en memoria; sin IO. |

**Separación crítica:** cada provider hace *solo* dos cosas: (1) hablar con su
fuente, (2) entregar payload crudo. La conversión payload→dominio está aislada
en `providers/normalization.py`, de modo que la lógica de normalización sea
testeable sin red y compartida entre proveedores donde aplique.

> **Antes de implementar `A3Provider`** hay que documentar su contrato en
> `docs/providers/a3_provider_contract.md`: endpoints, autenticación,
> formato/zona horaria de timestamps, y **semántica exacta del precio**
> (¿último operado? ¿ajuste? ¿VN 100?). El `market_conventions.md` ya advierte
> que la base de precio observada "no debe tratarse como contrato validado del
> proveedor". Esto es un prerequisito de la Etapa 3, no un supuesto.

---

## 5. Nuevos Services (orquestación, sin fórmulas)

Los services coordinan; **no contienen matemática financiera de convención**.

### 5.1 `SyncService`
Flujo: `provider.list_contracts()` → detectar **altas** (ticker nuevo) y
**bajas** (vencidos → `is_active=False`) contra `storage` → `provider.fetch_*`
→ `normalization` → `repository.upsert_*` → registrar evento en `sync_log`.
Nunca mantiene listas manuales de contratos.

### 5.2 `CurveService`
Lee contratos activos + últimas cotizaciones del `storage`, los ordena por
vencimiento y arma `FuturesCurve`. Si el research gate de tasas está cerrado,
`implied_rate=None` y `methodology_status=PENDING`. Si se abre, delega el
cálculo puro en `financial_engine.fx_forward_metrics` (no lo calcula él).

### 5.3 `SnapshotService`
Persiste snapshots diarios de la curva completa para reconstruir su evolución
histórica. Idempotente por `(snapshot_date, market, instrument_class)`.

### 5.4 `MetricsService`
**Solo estadística descriptiva** sobre precios/curvas ya existentes: pendiente
(último − primero), promedio, máximo, mínimo, spread entre vencimientos. Estas
son operaciones aritméticas neutrales, no convenciones de mercado. Cualquier
métrica que dependa de una **tasa** hereda el estado del research gate.

---

## 6. Esquema de almacenamiento histórico

SQLite como fuente de verdad relacional; Parquet como capa de export analítica.

### 6.1 Tablas SQLite (`storage/schema.sql`)

```sql
-- Datos contractuales (una fila por contrato, se actualiza estado)
CREATE TABLE contracts (
    ticker            TEXT PRIMARY KEY,
    instrument_class  TEXT NOT NULL,
    underlying_asset  TEXT NOT NULL,
    market            TEXT NOT NULL,
    maturity_date     TEXT NOT NULL,          -- ISO-8601
    currency          TEXT NOT NULL,
    first_seen        TEXT NOT NULL,
    is_active         INTEGER NOT NULL         -- 0/1
);

-- Precios históricos (append-only; una fila por ticker+timestamp+proveedor).
-- Se conservan TODOS los precios; los ausentes quedan NULL (faltante explícito).
CREATE TABLE price_history (
    ticker             TEXT NOT NULL,
    -- conjunto completo de precios (Decimal como TEXT, sin float)
    settlement_price   TEXT,                    -- ajuste / settlement oficial
    last_price         TEXT,                    -- último operado
    bid                TEXT,                    -- mejor compra
    ask                TEXT,                    -- mejor venta
    previous_settlement TEXT,
    daily_change       TEXT,
    daily_change_pct   TEXT,
    volume             TEXT,
    open_interest      TEXT,
    -- política temporal
    provider_timestamp TEXT NOT NULL,           -- timestamp original del proveedor
    provider_timezone  TEXT NOT NULL,           -- zona horaria original
    timestamp_utc      TEXT NOT NULL,           -- normalizado a UTC
    received_at        TEXT NOT NULL,           -- momento de recepción
    market_date        TEXT NOT NULL,           -- fecha de mercado (rueda)
    provider           TEXT NOT NULL,
    PRIMARY KEY (ticker, timestamp_utc, provider),
    FOREIGN KEY (ticker) REFERENCES contracts(ticker)
);

-- Snapshots diarios de curva (para evolución de la curva completa)
CREATE TABLE curve_snapshots (
    snapshot_date     TEXT NOT NULL,
    underlying_asset  TEXT NOT NULL,
    ticker            TEXT NOT NULL,
    maturity_date     TEXT NOT NULL,
    days_to_maturity  INTEGER NOT NULL,
    price             TEXT NOT NULL,
    implied_rate      TEXT,                    -- NULL mientras el gate esté cerrado
    methodology_status TEXT NOT NULL,
    provider          TEXT NOT NULL,
    PRIMARY KEY (snapshot_date, underlying_asset, ticker)
);

-- Tasas calculadas (poblada solo si el research gate se abre)
CREATE TABLE calculated_rates (
    ticker             TEXT NOT NULL,
    valuation_date     TEXT NOT NULL,
    effective_rate     TEXT,
    implied_tna        TEXT,
    implied_tea        TEXT,
    methodology_status TEXT NOT NULL,          -- PENDING hasta aprobación
    research_ref       TEXT,                   -- p.ej. "R-009" (+ R-002/003/004 anualización)
    PRIMARY KEY (ticker, valuation_date)
);

-- Bitácora de sincronización (observabilidad)
CREATE TABLE sync_log (
    run_id             TEXT PRIMARY KEY,
    started_at         TEXT NOT NULL,
    finished_at        TEXT,
    provider           TEXT NOT NULL,
    contracts_downloaded INTEGER,
    contracts_new      INTEGER,
    contracts_expired  INTEGER,
    response_ms        INTEGER,
    status             TEXT NOT NULL,          -- OK/PARTIAL/FAILED
    error_detail       TEXT
);

CREATE TABLE schema_version (version INTEGER NOT NULL);
```

Puntos clave de diseño:

- **`Decimal` se guarda como `TEXT`**, nunca como `REAL`, para no introducir
  binario flotante (política Decimal del proyecto).
- `price_history` es **append-only**: no se pierde histórico.
- `calculated_rates` existe desde el inicio pero se llena **solo** cuando el
  research correspondiente esté validado; mientras tanto `methodology_status =
  PENDING`.
- Versionado de esquema con `schema_version` + `migrations/` para evolución
  segura.

### 6.2 Capa Parquet
`parquet_store.py` exporta `price_history` y `curve_snapshots` particionados
por `underlying_asset` / año, para análisis y para alimentar herramientas
externas sin golpear SQLite. Es derivada; la fuente de verdad es SQLite.

---

## 7. API interna propuesta (`api/market_data_api.py`)

Fachada única y estable. Cualquier módulo del Toolkit la consume sin conocer
proveedor ni storage. Devuelve siempre modelos de dominio inmutables.

```python
class MarketDataAPI:
    def get_contract(self, ticker: str) -> FuturesContract: ...
    def get_active_contracts(
        self, instrument_class: InstrumentClass
    ) -> tuple[FuturesContract, ...]: ...

    def get_current_curve(
        self, underlying_asset: str, price_type: PriceType = PriceType.SETTLEMENT
    ) -> FuturesCurve:
        """Curva por vencimiento. `price_type` es explícito; si algún contrato no
        tiene ese precio, su punto lo marca faltante (no se sustituye)."""

    def get_fx_forward_curve(self, underlying_asset: str) -> FxForwardCurve:
        """Vista Spot / Futuro / Forward Points / Devaluación implícita.

        Corresponde al concepto **precio forward FX** (R-009): tipo de cambio
        futuro derivado del spot y de dos factores de acumulación de moneda.
        NO es una tasa forward de interés (concepto distinto, candidato R-017) ni
        el valor de un forward existente. Por mandato de la revisión
        bibliográfica del 6-ago-2026 estos tres conceptos no comparten nombre ni
        función. Expone la **comparación observada** (forward_points = futuro −
        spot, sin curvas de tasas); el **forward teórico por paridad** y la
        devaluación implícita quedan en None + UNDER_REVIEW hasta que R-009 cierre
        con Implementation Approved (§11). El spot no tiene proveedor aprobado aún."""

    def get_historical_prices(
        self, ticker: str, start: date, end: date,
        price_type: PriceType = PriceType.SETTLEMENT,
    ) -> tuple[MarketQuote, ...]:
        """Devuelve las cotizaciones completas del rango. `price_type` indica qué
        precio prioriza la vista; el modelo conserva igualmente el conjunto
        completo, sin sustitución silenciosa."""

    def get_latest_snapshot(
        self, underlying_asset: str
    ) -> DailySnapshot: ...

    def get_curve_evolution(
        self, underlying_asset: str, start: date, end: date
    ) -> tuple[FuturesCurve, ...]: ...

    def get_descriptive_metrics(
        self, underlying_asset: str
    ) -> CurveMetrics: ...        # pendiente, promedio, min, max, spreads
```

La fachada es el **único** punto de entrada público; el dashboard es un
consumidor más, igual que una calculadora o un reporte. Esto cumple tu
requisito de "el dashboard no debe ser el único consumidor".

---

## 8. Flujo completo de actualización automática

```text
┌─────────────────────────────────────────────────────────────────┐
│ Scheduler (cron / tarea programada)  — frecuencia configurable    │
└───────────────┬───────────────────────────────────────────────────┘
                │ dispara
                ▼
        SyncService.run()
                │
   1. cache.get()  ──► ¿fresco? ─► sí ─► corta (evita llamada API)
                │ no
   2. provider.list_contracts(FX_FUTURE)      ◄── A3Provider (red)
                │
   3. diff contra storage:
        • ticker no visto        -> alta  (first_seen = hoy)
        • ticker vencido/ausente -> baja  (is_active = 0)
                │
   4. provider.fetch_snapshot()  ◄── payload crudo
                │
   5. normalization.to_domain()  -> FuturesContract / MarketQuote (Decimal)
                │
   6. repository.upsert_contracts() + append price_history
   7. SnapshotService.persist(curve del día)
   8. cache.set(ttl)
   9. sync_log.write(run_id, nuevos, vencidos, ms, status)
                │
                ▼
   API interna sirve datos actualizados a todo el Toolkit
```

Notas: idempotente (reejecutar no duplica), tolerante a fallos (un provider
caído deja `status=FAILED` y conserva el último histórico), y sin listas
manuales (cada vencimiento nuevo aparece solo en el paso 3).

Para la automatización periódica se puede usar cron/systemd/una tarea
programada del sistema; el módulo expone `SyncService.run()` como punto de
entrada, agnóstico al scheduler.

---

## 9. Componentes reutilizados del proyecto

La propuesta **reutiliza y respeta** lo existente en vez de duplicar:

- **Patrón de módulo del engine:** input inmutable → función pública única →
  resultado inmutable. `fx_forward_metrics.py` copia exactamente el patrón
  de `maturity_value.py`.
- **`UnvalidatedMethodologyError`** y la jerarquía de excepciones de dominio:
  mismo enfoque, se reutiliza el patrón (no se reimplementa la política).
- **Política Decimal-only** y `@dataclass(frozen=True, slots=True)` del
  `financial_specification.md`.
- **Research Gate** y trazabilidad research→spec→validación→implementación→test.
- **Registro de research** (`docs/research/README.md`) y **auditoría
  bibliográfica** (`bibliography_review_2026-08-06.md`) como fuente de numeración
  y estado: el módulo referencia R-009 (y R-002/003/004), nunca IDs inventados.
- **Convenciones centralizadas** de `market_conventions.md` (settlement T+1,
  base de precio, day-count) como única fuente para el `year_fraction`.
- **Estructura de repositorio** (`docs/`, `src/`, `tools/`, `tests/`,
  `examples/`, `data/`, `outputs/`) y el estilo de docs con tabla de metadatos
  + estado + versión.
- **`pyproject.toml` / pytest** con `pythonpath = ["src"]`: el nuevo paquete se
  integra sin cambiar la configuración de build.
- **Casos de validación** (`examples/03_validation_cases/`) como formato para
  validar el provider y, más adelante, las tasas.

Nada de esto se re-implementa: el Market Data Module se enchufa a la governance
que ya existe.

---

## 10. Riesgos técnicos

| # | Riesgo | Impacto | Mitigación |
|---|--------|---------|------------|
| R1 | **Semántica del precio A3 no documentada** (último vs ajuste vs VN100) | Alto — datos crudos incorrectos contaminan todo aguas abajo | Documentar `a3_provider_contract.md` y validar contra informe oficial **antes** de implementar el provider |
| R2 | **Cambios/inestabilidad de la API A3** | Medio | Interfaz `MarketDataProvider` aísla el cambio a un archivo; `CSVProvider` permite operar offline |
| R3 | **Zona horaria / timestamps del proveedor** | Medio — corrompe series y "última actualización" | Normalizar a TZ explícita y única en `normalization.py`; guardar TZ en el timestamp |
| R4 | **Tentación de calcular tasas sin research** | Alto — viola la governance | Gate estricto: `UnvalidatedMethodologyError` + `implied_rate=None`; imposible poblar `calculated_rates` sin `research_ref` validado |
| R5 | **`float` filtrándose vía librerías de datos** (pandas/pyarrow) | Alto — rompe Decimal-only | Decimal como `TEXT` en SQLite; conversión a float **solo** en la capa de export/visualización, nunca en dominio |
| R6 | **Autenticación / credenciales del proveedor** | Medio | Config desacoplada + variables de entorno; secretos fuera del repo (`.gitignore`) |
| R7 | **Crecimiento del histórico** | Bajo/Medio | Índices en `price_history`; export a Parquet particionado; retención configurable |
| R8 | **Detección de altas/bajas con datos parciales** | Medio | Marcar bajas por ausencia + fecha de vencimiento, no borrar; `status=PARTIAL` en sync incompleto |
| R9 | **Acoplar el dashboard a estructuras internas** | Medio | El dashboard consume **solo** `MarketDataAPI`; prohibido importar `storage`/`providers` |
| R10 | **Mezclar precio forward FX, tasa forward de interés y valor de forward existente** | Alto — error conceptual que contamina cálculos y reporting | Separación terminológica obligatoria (§11.10): tipos y funciones distintos; prohibida una función genérica `forward_rate` |

---

## 11. Decisiones de diseño

1. **Provider-agnóstico vía `Protocol`.** `MarketDataProvider` + `A3/IOL/CSV/Mock`.
   Cambiar de proveedor = agregar un archivo; el resto del Toolkit no se entera.
   *(Tu requisito explícito; adoptado como pilar.)*
2. **SQLite (verdad) + Parquet (análisis).** Cero servicios externos, un archivo
   versionable, consultas relacionales; Parquet para analítica. *(Confirmado.)*
3. **Dashboard definido ahora, implementado después** sobre `MarketDataAPI`.
   *(Confirmado.)*
4. **Tasas implícitas gated, sobre research existente.** Interfaces y tablas
   existen; los cálculos lanzan `UnvalidatedMethodologyError` hasta research
   aprobado. Se apoyan en los research **ya registrados**: **R-009**
   (forward/futuro FX, *Under Review*) para forward points y devaluación
   implícita, y **R-002/R-003/R-004** para las convenciones de anualización
   (HPR/TNA/TEA). No se inventa numeración nueva; R-006..R-008/R-010 se
   descartan. *(Confirmado.)*
5. **Datos crudos vs. cálculos.** El módulo distingue market data (precio,
   volumen, OI, variación publicada) de valores calculados (tasas, forwards).
   Solo lo segundo pasa por el gate.
6. **Decimal como `TEXT` en persistencia.** Preserva la política Decimal-only
   de punta a punta.
7. **Fachada única (`MarketDataAPI`).** Un solo contrato público; el dashboard
   es un consumidor más.
8. **Ubicación de las fórmulas de tasas — RESUELTO (Felipe, 6-ago-2026).** Las
   fórmulas puras viven en el **Financial Engine**, como módulos nuevos que
   **no modifican** los existentes. Cadena de responsabilidades aprobada:
   `Proveedor/API → datos` · `Market Data → normalización/almacenamiento/consulta`
   · `Engine → cálculos puros` · `Dashboard → visualización`. En vez de un
   `futures_implied_rates.py` genérico (demasiado amplio, reintroduce la mezcla
   que la doc acaba de separar), se usan módulos **explícitos**:
   `fx_forward_metrics.py` (precio forward FX y puntos forward, R-009); a futuro y
   por separado, tasa forward de interés (R-017) y valor de un forward existente.
   **Prohibida** una función genérica `forward_rate`.
9. **Empaquetado diferido.** Se mantiene `pythonpath=["src"]`; se formaliza el
   paquete cuando la API pública esté estable.
10. **Separación terminológica obligatoria (nueva, 6-ago-2026).** Por mandato de
    `bibliography_review_2026-08-06.md`, tres conceptos **no** comparten nombre
    ni función: (a) **precio forward FX** — `get_fx_forward_curve` / `FxForwardCurve`;
    (b) **tasa forward de interés** — fuera de scope del módulo de datos, candidato
    **R-017**; (c) **valor de un forward existente** — no modelado por ahora.
    Queda **prohibida** una función genérica `forward_rate`. El proxy
    futuro≈forward se rotula siempre "Under Review" (R-009).

---

## 12. Roadmap por etapas (pequeñas, revisables, testeables)

Cada etapa es un entregable independiente con tests y un punto de aprobación.
Ninguna etapa implementa fórmulas financieras sin su research validado.

### Etapa 0 — Andamiaje y contratos *(sin red, sin fórmulas)*
- Crear `src/market_data/` con `models/`, `enums`, `exceptions`, `config`.
- Definir `MarketDataProvider` (Protocol) y `MarketDataRepository` (Protocol).
- Tests: inmutabilidad de dataclasses, Decimal-only, contratos de Protocol.
- **Entregable revisable:** esqueleto + interfaces, todo tipado, sin IO.

### Etapa 1 — Storage + MockProvider *(sin red)*
- `schema.sql`, `sqlite_repository.py`, `mock_provider.py`, `csv_provider.py`.
- Tests: round-trip de persistencia, append-only, detección alta/baja con Mock.
- **Entregable:** se puede sincronizar y consultar una curva de prueba end-to-end
  sin tocar internet.

### Etapa 2 — Services + API interna
- `SyncService`, `CurveService`, `SnapshotService`, `MetricsService`, fachada
  `MarketDataAPI`, `cache`, `sync_log`.
- Tests: flujo de sync idempotente, snapshots, métricas descriptivas.
- **Entregable:** API interna funcional sobre datos mock/CSV.

### Etapa 3 — Provider A3 real
- **Prerequisito:** `docs/providers/a3_provider_contract.md` documentado y
  revisado (semántica de precio, auth, timestamps).
- `a3_provider.py` + `normalization.py`; validación contra un informe oficial.
- Tests de integración detrás de flag (no corren offline).
- **Entregable:** futuros de dólar reales entrando al storage.

### Etapa 4 — Forward FX / tasas implícitas *(GATED)*
- **No** implementar hasta que **R-009** pase de *Under Review* a validado **con**
  `Implementation Approved: Yes`, y se cierren sus ítems abiertos (dirección del
  spot y su fuente, curvas de tasa doméstica/foránea y sus timestamps, convención
  de capitalización y year fraction, y semántica del campo del proveedor:
  settlement vs last vs bid/ask). La anualización a TNA/TEA depende además de
  R-002/R-003/R-004.
- Definir `fx_forward_metrics.py` con stubs que lanzan
  `UnvalidatedMethodologyError`; poblar `calculated_rates` solo tras aprobación.
- Respetar la separación terminológica en **módulos distintos**: precio forward
  FX (`fx_forward_metrics.py`) ≠ tasa forward de interés (R-017, módulo aparte,
  fuera de scope) ≠ valor de forward existente (módulo aparte si entra en alcance).
  Prohibida una función genérica `forward_rate`.
- **Entregable:** interfaces listas; números solo cuando el gate se abra.

### Etapa 5 — Export y observabilidad
- `exporters.py` (CSV/Excel/Parquet), `parquet_store.py`, logging estructurado
  completo.
- **Entregable:** exportación y bitácora de sincronización operativas.

### Etapa 6 — Dashboard
- Sobre `MarketDataAPI`: curva de futuros, curva de tasas (solo si gate abierto),
  evolución histórica, evolución de la curva, spot vs futuro, heatmap, métricas.
- **Entregable:** dashboard profesional consumiendo exclusivamente la API interna.

### Etapa 7 — Extensibilidad multi-activo
- Habilitar `COMMODITY_FUTURE`, `RATE_FUTURE`, `INDEX_FUTURE` reutilizando la
  misma maquinaria (solo config + normalización específica).
- **Entregable:** el módulo deja de ser "solo dólar" sin refactor estructural.

---

## Estado de las decisiones

1. **§11.8 — RESUELTO:** fórmulas puras en el Financial Engine, en módulos
   explícitos (`fx_forward_metrics.py`, etc.), sin función genérica `forward_rate`.
2. **Modelo de precios — RESUELTO:** se conservan todos los precios; sin
   sustitución silenciosa; cada vista declara su `PriceType`.
3. **Política temporal — RESUELTA:** timestamp original, TZ, UTC, recepción, fecha
   de mercado y antigüedad; spot/futuro solo se comparan alineados.
4. **Spot, curvas y mapeo de precios — DIFERIDO a R-009** (8 subsecciones), a la
   espera de la documentación de la API de Gastón. Hasta entonces, `spot` sin
   proveedor aprobado y el forward teórico por paridad permanece gated.
5. **Etapa 0 — APROBADA** para avanzar (interfaces y estructura, sin red ni
   cálculos).

**Todavía pendiente de definir (fuera de la ruta crítica de la Etapa 0):**
frecuencia de actualización por defecto y política de retención del histórico
(¿ventana configurable o histórico indefinido?), y el contrato de la API A3
(`docs/providers/a3_provider_contract.md`), prerequisito de la Etapa 3.

Con la Etapa 0 aprobada, se avanza con el andamiaje e interfaces; los detalles de
spot, curvas y precios esperan la documentación de la API y se resuelven en R-009.
