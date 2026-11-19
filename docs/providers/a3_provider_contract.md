# A3 / MAE MarketData API — Provider Contract

| Field | Value |
|-------|-------|
| Document | Provider data contract (canonical) |
| Provider | A3 Mercados — **MAE MarketData API** |
| API type | REST, authenticated with an `x-api-key` header |
| Status | 🟡 Partially confirmed from official docs; some items pending |
| Consumed by | `src/market_data/providers/a3mae/` |
| Related research | R-009 (spot/forward) — **not** closed by this document |
| Owner | Felipe Cagigas |
| Last Updated | Tuesday, 11 August 2026 |

> **Scope of this document.** This contract describes **only** the A3 / MAE
> MarketData API (authenticated by `x-api-key`). It does **not** describe the
> Matba Rofex / Primary API (user + password + account), which is a separate
> venue for futures — see `docs/providers/futures_provider_rofex_notes.md`. The
> two sources are intentionally kept in separate documents.
>
> **No credentials appear in this file.** Keys live only in the local, git-ignored
> `.env`.
>
> **Governance.** This document records API facts only. It does not implement any
> financial formula, does not close R-009 and does not promote any Research Gate.

---

## 1. Identification

- **Provider / market:** A3 Mercados (integration of Mercado Abierto Electrónico
  and Matba Rofex). The MarketData service is served from the MAE domain.
- **Product:** MAE MarketData API (OpenAPI title `MAE-APIDATA-MD`).
- **Authentication type:** API key sent as an HTTP header. This is the API whose
  keys we received (`API Key Producción` / `API Key UAT`).
- **Official docs:** https://marketdata.mae.com.ar/documentacionAPI
- **Swagger / OpenAPI:** https://marketdata.mae.com.ar/swagger/api-documentacion.html
  (spec: `https://marketdata.mae.com.ar/swagger/marketdata.json`, OpenAPI 3.0.1)
- **Support:** atencionalcliente@a3mercados.com.ar

Status: **Confirmed** (from the official docs page and Swagger).

## 2. Environments

Both environments exist and we hold a key for each:

- **UAT** (test) — retained for development and offline-contract checks.
- **Production** — approved for the local Toolkit's read-only market refreshes.
  No order-entry or write endpoint is used.

Status: **Confirmed**.

## 3. Base URLs

| Environment | Base URL (per official curl) |
|-------------|------------------------------|
| Production | `https://api.mae.com.ar/MarketData/v1/` |
| UAT | `https://apiuat.mae.com.ar/MarketData/v1/` |

The official curl path `.../MarketData/v1/mercado/...` was confirmed by a
successful read-only UAT smoke test on 10 August 2026. The alternative Swagger
path `/api/v1/mercado/...` is not used by the current provider configuration.

Status: **Confirmed in UAT and Production** for authenticated read-only access.

## 4. Authentication

- HTTP header: `x-api-key: {API_KEY}`.
- No username/password/account, no token exchange, no OAuth.

Status: **Confirmed**.

## 5. Endpoints (all GET)

| Endpoint | Purpose |
|----------|---------|
| `mercado/cotizaciones/rentafija` | Fixed-income traded securities |
| `mercado/cotizaciones/cauciones` | Cauciones |
| `mercado/cotizaciones/forex` | Forex operations |
| `mercado/cotizaciones/repo` (a.k.a. `mercado/repo`) | Repo operations within a date range |
| `mercado/boletin/ReporteResumenFinal?fecha={fecha}` | Final summary report for a date |

Status: **Confirmed** (from docs). Exact `repo` path and its date-range params
**pending** confirmation.

## 6. Query parameters

For the `cotizaciones/*` endpoints (all optional):

| Param | Type | Notes |
|-------|------|-------|
| `segmento` | string | Segment filter |
| `plazo` | string | Settlement term filter (e.g. `000`, `001`) |
| `moneda` | string | Currency filter |
| `ticker` | string | Ticker filter |
| `pageNumber` | integer | Pagination index |

`ReporteResumenFinal` takes `fecha`. Status: **Confirmed** (from Swagger).

## 7. Pagination

- Via one-based `pageNumber` (integer).
- A live Production check on 11 August 2026 returned 50 rows on each full page,
  a shorter final page and an empty response after the end.
- The Toolkit now requests successive pages until the first page shorter than
  50 rows. Repeated boundary records are consolidated by their stored quote
  identity; a 100-page safety limit prevents an unbounded loop.

Status: parameter and current Production behavior **confirmed**. A3 does not
publish total-count metadata, so the client still terminates from page length.

## 8. Instruments and segments available

| Segment | Available? |
|---------|-----------|
| Fixed income (renta fija) | **Yes** |
| Cauciones | **Yes** |
| Forex / spot | **Yes** |
| Repo | **Yes** |
| **Dollar futures** | **No** (different venue: Matba Rofex / Primary) |

Status: **Confirmed**.

## 9. Response schema (unified quote object)

`rentafija`, `cauciones` and `forex` return the **same** object. Fields (source
name → meaning):

| Field | Type | Meaning |
|-------|------|---------|
| `fecha` | datetime | Observation / market date |
| `ticker` | string | Instrument ticker |
| `descripcion` | string | Description |
| `tipoEmision` | string | Issue/segment type (`TPN`, `CAU`, `FOR`, …) |
| `segmento` | string/null | Segment name |
| `codigoSegmento` | string | Segment code |
| `plazo` | string | Settlement term (`000`, `001`, …) |
| `codigoPlazo` | string/null | Term code |
| `moneda` | string | Currency code (`$`, `T`, …) |
| `fechaLiquidacion` | datetime | Settlement date (`0001-01-01` = N/A) |
| `volumenAcumulado` | number | Accumulated volume |
| `montoAcumulado` | number | Accumulated amount |
| `precioUltimo` | number | Last price |
| `ultimaTasa` | number | Last rate (provider-published; raw) |
| `precioCierreAnterior` | number | Previous close |
| `precioMinimo` | number | Minimum price |
| `precioMaximo` | number | Maximum price |
| `openInterest` | number | Open interest |
| `precioCierre` | number/null | Close price |
| `variacion` | number | Change |

Status: **Confirmed** (from the Swagger response example). Numeric types are
parsed as `Decimal` (never float) in `providers/a3mae/normalization.py`.

### Observed ticker identity for 24-hour settlement

Production observations on 11 August 2026 confirm that A3 identifies the
24-hour settlement twice: `plazo="001"` and a `/24hs` suffix in the raw ticker
(for example, `S30S6/24hs`). The provider record and SQLite evidence retain that
raw ticker. For contract reconciliation only, the Toolkit maps it to `S30S6`
when — and only when — the same observation explicitly declares term `001`.
Other prefixes (for example `X30S6`) remain different instruments, and no
suffix is removed for another settlement term.

The same live response also contains unsuffixed TPN rows with `plazo="001"`
whose numeric scale differs materially from the `/24hs` rows. For example,
`S30S6` was `1.1377`, while `S30S6/24hs` was `113.85`. Because A3's formal
quotation-unit table remains unavailable, the LECAP/BONCAP calculator accepts
only the explicit `/24hs` row for a current T+1 price. Unsuffixed observations
remain stored as raw evidence and are never multiplied by 100 or silently
converted.

## 10. Price semantics

- `precioUltimo` = last traded price.
- `precioCierre` = close price; `precioCierreAnterior` = previous close.
- `precioMinimo` / `precioMaximo` = session min/max.
- `ultimaTasa` = a **provider-published rate**, stored as raw market data. It is
  **not** a Toolkit-calculated TNA/TEA and opens no Research Gate.
- **No bid/ask** and **no settlement/adjustment price** are provided (there is a
  settlement *date*, `fechaLiquidacion`, not a settlement *price*).

Status: field-level meaning **confirmed** by names/examples; formal market
definitions (e.g. how `precioCierre` is determined per segment) **pending**.

### Observed data gap — `precioUltimo` (A3-side, 11 August 2026)

As observed on 11 August 2026, A3 populates `precioUltimo` (last traded price)
for only a subset of instruments (e.g. S30N6, S30O6); for most instruments it
comes back empty. This is an **A3-side data condition**, not a Toolkit defect.
`precioCierre` (close) is the reliable price field. The normalization preserves
this faithfully: `last_price` is `None` when absent, with no silent substitution.

**Price-selection policy for the yield calculator (when wired):** use
`precioUltimo` when present, otherwise fall back to `precioCierre`, and always
label which price was used (an explicit `PriceType`, not a silent swap). This is
consistent with R-003's "last or close" input decision.

## 11. Currency and quotation unit

- `moneda` carries the currency code (`$` observed for ARS; `T` observed in
  forex). The full code table is **pending**.
- **Quotation unit** (e.g. price per 100 nominal for bonds) is **not stated** in
  the spec and is **pending** confirmation.

## 12. Dates, timestamps, timezone

- `fecha` = market date; the examples are date-level (`T00:00:00`).
- `fechaLiquidacion` = settlement date (`0001-01-01` → treated as `None`).
- **Timezone is not documented** (Argentina presumably); **pending**.
- Whether intraday updates carry an intraday time component is **pending**.

## 13. Update frequency and delay

- **Not documented.** Whether `cotizaciones/*` is real-time, delayed or
  end-of-day is **pending** confirmation.

## 14. Historical data

- `cotizaciones/*` endpoints take no date parameter → likely **current session
  only** (to confirm).
- `ReporteResumenFinal?fecha=` returns a **per-date** daily report.
- `repo` is documented as returning operations **within a date range**.
- Historical depth/coverage is **pending**.

## 15. Rate limits

- **Not documented**; **pending**.

## 16. Error handling

- Standard HTTP status codes expected. The client maps `401/403` → auth error,
  other non-2xx → response error, connection failures → connection error.
- Exact error-body shape is **pending**.

## 17. Storage / redistribution restrictions

- **Not reviewed.** Terms of use regarding storage and redistribution of the data
  must be checked with A3 before any redistribution. **Pending.**

## 18. Official request / response examples

Request (UAT):

```bash
curl -X GET \
  "https://apiuat.mae.com.ar/MarketData/v1/mercado/cotizaciones/rentafija" \
  -H "x-api-key: {API_KEY}"
```

Response (example row, from the official Swagger):

```json
[
  {
    "fecha": "2024-11-15T00:00:00",
    "ticker": "AE38",
    "descripcion": "AE38  (BONO USD STEP UP 2038 L.A.)",
    "tipoEmision": "TPN",
    "segmento": "Bilateral TRD",
    "codigoSegmento": "BT",
    "plazo": "000",
    "codigoPlazo": "000",
    "moneda": "$",
    "fechaLiquidacion": "0001-01-01T00:00:00",
    "volumenAcumulado": 14811266,
    "montoAcumulado": 11235165909,
    "precioUltimo": 759.65,
    "ultimaTasa": 0,
    "precioCierreAnterior": 0,
    "precioMinimo": 755,
    "precioMaximo": 759.65,
    "openInterest": 0,
    "precioCierre": 759.65,
    "variacion": 0.07
  }
]
```

---

## 19. Confirmed vs pending checklist

| Capability | Available? | Source |
|------------|-----------|--------|
| Renta fija | ✅ Yes | Official docs / Swagger |
| Cauciones | ✅ Yes | Official docs / Swagger |
| Forex / spot | ✅ Yes | Official docs / Swagger |
| Repos | ✅ Yes | Official docs |
| Dollar futures | ❌ No | Not in this API (Matba Rofex venue) |
| Bid & ask | ❌ No | Absent from response schema |
| Last price (`precioUltimo`) | ✅ Yes | Swagger example |
| Close price (`precioCierre`) | ✅ Yes | Swagger example |
| Settlement/adjustment price | ❌ No | Only settlement *date* (`fechaLiquidacion`) |
| Volume (`volumenAcumulado`) | ✅ Yes | Swagger example |
| Open interest (`openInterest`) | ✅ Yes (field present; may be 0 for cash) | Swagger example |

**Still pending official confirmation:** pagination behavior, currency code
table, quotation unit, timezone,
update frequency/delay, historical depth of `cotizaciones/*`, rate limits, error
body shape, storage/redistribution terms.

## 20. UAT smoke-test evidence — 10 August 2026

A read-only GET was executed against:

```text
https://apiuat.mae.com.ar/MarketData/v1/mercado/cotizaciones/rentafija
```

Results:

- authentication with the UAT `x-api-key` was accepted;
- the `/MarketData/v1` base path was confirmed;
- the response was valid JSON and normalized without schema errors;
- three fixed-income observations were returned for market date
  10 August 2026;
- observed tickers included AL30 and GD30 settlement variants;
- financial numeric fields were parsed as `Decimal`;
- no production endpoint was queried;
- no API key was printed, logged or written to documentation.

This test validates connectivity and the basic response contract only. It does
not validate quotation units, price methodology, pagination, historical depth
or any Toolkit financial formula.

## 21. Production read-only evidence — 11 August 2026

The owner-approved local lifecycle synchronization queried the Production fixed
income endpoint using `GET` only. Authentication and response normalization
succeeded. The endpoint returned an empty list at the time of the check, so no
instrument was promoted to `ACTIVE_FOR_ANALYSIS`; the official candidates
remained pending. An empty pre-market response is not treated as evidence that
an instrument is absent from the secondary market, and the approved 15-minute
schedule will check again.

The macOS launcher now makes the Production selection and safety
acknowledgement explicit. UAT remains the command-line default. No credential
was printed, stored in code or added to documentation.

---

**Version:** 1.4 (canonical MAE MarketData contract)

**Last Updated:** Tuesday, 11 August 2026

---

## 20. Requirement raised to the internal API — dollar-linked price basis (2026-10-26)

**Status: requested, not yet confirmed.**

Dollar-linked Treasury instruments (LELINK and DLK bonds) are quoted on screen in
**pesos**, while the instrument's unit of account is the **USD-linked** unit.
Converting one into the other requires an exchange rate that this contract does
not document, and §11 already records that the **quotation unit is not stated**
by the provider.

Research R-006 (2026-10-26) reconciled the published market yields and found the
implied conversion rate does **not** match the BCRA A3500 of the closing date:
+0.034% against the BYMA-sourced report of 30-Sep-2026 and +0.203% against the
IAMC report of 05-Oct-2026. In the short end that gap is worth about **1.3 pp of
annualized yield**, so the rule cannot be guessed.

Requested, in order of preference:

1. **Price already expressed in USD-linked units per VN 100** for dollar-linked
   instruments, in a dedicated field, with the unit declared.
2. Failing that, the peso price **plus** the conversion rate actually used, with:
   its value at full precision, its reference date and time, and its identity
   (BCRA A3500 under Com. "A" 3500 / Com. "A" 8359, or wholesale closing spot).
3. In both cases: the **quotation unit per instrument** (per VN 100 or per VN
   1.000), declared explicitly rather than inferred.

Until one of these is answered, dollar-linked instruments stay outside the
production engine (R-006 Research Gate closed).
