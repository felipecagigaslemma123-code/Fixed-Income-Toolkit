# A3 Public Futures Viewer — Provisional Read-Only Data Contract

| Field | Value |
|-------|-------|
| Provider | A3 / Matba Rofex public price viewer |
| API type | Public application endpoints (no authentication observed) |
| Scope | Dollar futures contract reference data and recent trades |
| Status | Prototype — provisional local integration |
| Owner | Felipe Cagigas |
| Last Updated | 10 August 2026 |

> **Provisional source.** The endpoints below are used by A3's public price
> viewer, but they are not presented as a stable public API contract. They may
> change without notice. This integration is local, read-only and replaceable;
> it is not the credentialed Primary API documented in
> `futures_provider_rofex_notes.md`.

## 1. Source identification

- Public viewer: `https://matbarofex.primary.ventures/`
- Reference-data endpoint observed in the viewer:
  `GET https://matbarofex.primary.ventures/api/v2/ref-data`
- Recent-trades endpoint observed in the viewer:
  `GET https://matbarofex.primary.ventures/api/v2/trades/securities/{security_id}`
- Authentication: none observed for these two read-only endpoints.
- Production order routing: out of scope and never attempted.

The official A3 product guide supports the contract interpretation used by the
Toolkit: DLR is quoted in Argentine pesos per one US dollar and the standard
contract multiplier is USD 1,000. The public payload itself remains the source
of each stored contract's multiplier and minimum price increment.

## 2. Instrument selection

A row is eligible for the first dollar-futures screen only when both conditions
are true:

- `cfiCode` is exactly `FXXXSX` (future, not option); and
- `symbol` matches `DLR/<three-letter month><two-digit year>` with an optional
  trailing `M` for the mini contract.

Examples included: `DLR/AGO26`, `DLR/AGO26M`.

Options, calendar spreads and unrelated futures are excluded. Standard and mini
contracts are both retained. The filter is instrument classification, not a
financial calculation.

## 3. Contract reference fields

The following source fields are preserved when present:

| Source field | Toolkit field | Meaning/status |
|---|---|---|
| `id` | `security_id` | Provider security identifier |
| `symbol` | `ticker` | Market ticker |
| `description` | `description` | Provider description |
| `cfiCode` | `cfi_code` | CFI classification |
| `marketId` | `market_id` | Provider market identifier |
| `marketSegmentId` | `market_segment_id` | Provider segment identifier |
| `currency` | `currency` | Provider currency code |
| `maturityMonthYear` | `maturity_month_year` | Provider month/year value |
| `endDate` | `source_end_date` | Preserved raw date; **not treated as maturity** |
| `daysToExpiration` | `days_to_expiration` | Provider-published integer count |
| `contractMultiplier` | `contract_multiplier` | Decimal-safe source value |
| `pricePrecision` | `price_precision` | Display precision count |
| `sizePrecision` | `size_precision` | Display precision count |
| `minPriceIncrement` | `min_price_increment` | Decimal-safe source value |
| `settlementType` | `settlement_type` | Provider settlement classification |
| `underlying` | `underlying_id` | Provider underlying identifier |
| `underlyingSymbol` | `underlying_symbol` | Provider underlying symbol |

The public reference payload does not safely establish an exact expiry date.
The Toolkit therefore stores `maturity_month_year` and
`days_to_expiration` exactly as supplied and does not invent a date from the
official last-business-day rule.

## 4. Recent trade fields

| Source field | Toolkit field | Meaning/status |
|---|---|---|
| `id` | `trade_id` | Provider trade identifier |
| `securityId` | `security_id` | Contract association |
| `timestamp` | `provider_timestamp` | Original provider timestamp |
| `price` | `price` | Trade price, Decimal-safe |
| `volume` | `volume` | Trade volume, Decimal-safe |
| `sides` | `side_codes` | Source-provided side labels, if any |
| response time | `received_at` | Toolkit reception time in UTC |

Observed timestamps ending in `Z` are interpreted as UTC. The original string
is preserved together with the normalized UTC timestamp. No trade aggregation,
daily high/low or change calculation is performed.

## 5. Units and missing data

- Price basis for the standard DLR contract: `ARS_PER_USD_1`, supported by the
  official A3 product guide.
- Standard contract multiplier: `1000`, also supported by the guide; the stored
  record uses the source payload value and does not overwrite it.
- Financial numeric values are parsed directly as `Decimal` and stored as text
  in SQLite. They never pass through a binary float.
- A missing value is JSON `null` in the local API and an em dash in the HTML.
- No field silently substitutes for another. In particular, last trade is not
  presented as settlement, bid, ask, close, high, low, volume or open interest.

The public endpoints currently do **not** provide a confirmed full-market book,
official settlement series, previous settlement, daily high/low, accumulated
volume or open interest through this integration. Those screen columns remain
unavailable rather than being reconstructed.

## 6. Refresh, retention and lifecycle

- Contract reference refresh: once per day, and immediately when the local
  process starts with an empty contract store.
- Recent trade refresh: every 15 minutes while the local process is running.
- Storage: local SQLite history is retained indefinitely unless a future,
  explicitly approved retention policy changes it.
- A successful non-empty reference snapshot marks listed contracts active and
  contracts absent from the new complete snapshot inactive.
- Failed or empty reference responses never deactivate existing contracts.
- Manual data entry/import remains a future fallback and is not removed by this
  provider.

## 6b. Expiry date resolution (owner amendment, 11 August 2026)

The project owner amended the phase-1 "do not reconstruct" rule for the **expiry
date only** (a contractual/market date, not a rate or forward calculation). The
expiry is resolved by `market_data.futures_expiry.resolve_futures_expiry` with a
transparent, labeled priority:

1. `provider-end-date` — the provider's own `endDate` (`source_end_date`), used
   exactly when present. The contract runs until expiry, so this is authoritative.
2. `convention-last-business-day` — otherwise the last business day of the
   contract month from `maturityMonthYear`. This steps back over weekends only;
   it does **not** yet apply an Argentine holiday calendar, so it can be one or
   two days late on a month ending on a holiday. It is labeled as estimated in
   the screen.
3. `unresolved` — otherwise shown as missing.

This resolves the expiry **date** only. No forward point, implied devaluation,
TNA, TEA, theoretical forward or futures/forward adjustment is derived, and
R-009 remains `Under Review`.

## 7. Governance and limitations

- The dashboard reports **observed data only**.
- No spot price is requested or displayed.
- No forward points, implied devaluation, TNA, TEA, theoretical forward or
  futures/forward adjustment is calculated.
- R-009 remains `Under Review`, with `Implementation Approved: No`.
- The source has no confirmed rate-limit, service-level, historical-depth or
  redistribution contract. For that reason the integration is explicitly
  `Prototype`, local-only and replaceable.
- The future credentialed Primary provider remains the preferred path for a
  supported market-data contract if credentials become available.

---

**Version:** 1.0

**Last Updated:** 10 August 2026
