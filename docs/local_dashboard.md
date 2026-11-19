# Local HTML Dashboard Contract

| Field | Value |
|-------|-------|
| Dashboards | `outputs/modelo_lecap_boncap.html`; `outputs/futuros_dolar.html` |
| Database | SQLite (`data/market/market_data.sqlite`) |
| Browser target | Google Chrome on the local computer |
| Network exposure | Loopback only (`127.0.0.1`) |
| Status | Approved for local implementation |
| Owner | Felipe Cagigas |
| Last Updated | Monday, 26 October 2026 |

## Purpose

Keep the existing LECAP/BONCAP HTML dashboard as the user's visual interface
while replacing its external `data912` price request with the Toolkit's local
SQLite data populated by A3 / MAE MarketData.

HTML and SQLite have separate responsibilities:

- SQLite stores normalized market observations and lifecycle evidence.
- The HTML renders the existing exploratory dashboard.
- A loopback-only HTTP service exposes read-only JSON to the HTML because a
browser must not open or query a SQLite file directly.

The same loopback service also exposes the approved observed-only DLR futures
screen. Its data source, limits and refresh policy are governed by
`docs/providers/a3_public_futures_viewer_contract.md`.

## Local data flow

```text
Secretaría de Finanzas (daily) ─┐
                               ├─> SQLite ─> local HTTP ─> existing HTML ─> Chrome
A3 / MAE MarketData (15 min) ──┘
```

## Endpoints

- `GET /` — existing `outputs/modelo_lecap_boncap.html`.
- `GET /api/market/quotes` — latest fixed-income observations from SQLite.
- `GET /api/lifecycle` — national-Treasury discovery and activation states.
- `GET /api/metrics` — engine-computed metrics for one instrument evaluation
  (maturity value, HPR, TNA, TEA, TEM, Macaulay and Modified Duration), from
  contractual data, the selected price and the selected dates passed as query
  parameters. Read-only: nothing is written and no database is touched.
- `GET /api/health` — local service/database health metadata.
- `GET /futures` — observed dollar-futures dashboard.
- `GET /api/futures` — active DLR contract references and each contract's most
  recent stored trade. Unsupported viewer fields are explicit JSON `null`.

All financial values in JSON are strings or `null`; no server response passes a
financial value through binary floating point.

## Price-selection policy

The dashboard requests an explicit price field:

- `last_price` for the intraday/latest view; or
- `close_price` for the close view.

The dashboard does not silently substitute one price type for another. Because
the calculator declares T+1 settlement, only A3 observations whose normalized
term is explicitly `001` or an equivalent documented 24-hour label are applied.
When A3 additionally encodes that same term in the raw ticker (for example,
`S30S6/24hs`), the dashboard reconciles it with contract ticker `S30S6`; the raw
provider ticker remains visible in the price source and stored evidence.
For current LECAP/BONCAP calculations, the raw `/24hs` suffix is also required:
A3 currently returns some unsuffixed TPN rows on a different, undocumented
numeric scale (for example `1.1377` alongside `113.85`). These rows remain in
SQLite but cannot feed a price or rate. The Toolkit does not infer a ×100
conversion.
If the selected field or settlement term is unavailable, the embedded snapshot
remains visible with its actual market date and the status message reports the
gap. HPR, TNA, TEA, TEM and yield-dependent Modified Duration are calculated
only when the price market date equals the selected purchase date. There is no
silent historical-to-current rate fallback. Since 26 October 2026 this guard is
enforced in the service (`src/local_dashboard/metrics.py`), which returns the
yield fields as `null` with an explicit `yield_unavailable_reason`; the maturity
value and the residual terms are still returned, as before.

## Lifecycle presentation

An A3 match may mark an instrument `ACTIVE_FOR_ANALYSIS`. This is an operational
state only. It does not validate contractual data or any formula.

An active ticker not yet present in the dashboard's contractual dataset is
shown as awaiting complete contractual inputs; it is not inserted into a
financial calculation with invented issue dates or rates.

The dashboard exposes a separate national-Treasury universe sourced from the
official lifecycle records. It may contain LECAP, BONCAP and other national
Treasury families, but never provincial or corporate issuers. Every row states
whether it is active in A3, still pending secondary-market identification,
ready for the current LECAP/BONCAP comparison, awaiting contractual inputs or
outside this calculator's methodology.

Current selectors, comparison rows and charts exclude an instrument on and
after its explicit maturity date. Embedded historical records are preserved in
the file for audit and historical work; they are not shown as current species.
Operationally active new LECAP/BONCAP tickers may appear as non-calculable rows
until official issue date and contractual rate evidence is complete.

S16O6 is included with contractual data documented by the 10 August 2026
BYMA/IAMC report. Its embedded report price remains dated 10 August; A3 replaces
it operationally when an explicitly selected T+1 observation is available.

## Refresh behavior

- The scheduler writes A3 observations to SQLite every 15 minutes.
- The open HTML requests the local API immediately and every 15 minutes.
- The existing manual refresh button remains available.
- Secretaría lifecycle information is refreshed in the same page request.
- `tools/run_local_toolkit.py` starts the scheduler and dashboard together for
  normal local use. Its CLI keeps UAT as the safe default, while the approved
  macOS launcher selects A3 Production explicitly for real secondary-market
  visibility. This access is GET/read-only.
- The purchase/trade date defaults to the computer's current local date. A
  manual price refresh selects the latest A3 market date actually available;
  when it is earlier than today, the UI displays an explicit warning. Automatic
  15-minute refreshes and price-basis changes preserve a date explicitly
  selected by the user.
- On the owner's Mac, the `com.fixedincome.morningsync` LaunchAgent starts the
  Production scheduler every day at 09:30 local time. The process then keeps A3
  on its 15-minute interval and Treasury discovery on its 24-hour interval,
  independently of the browser. Because macOS blocks direct launchd execution
  from OneDrive CloudStorage, LaunchServices opens a minimal Terminal bridge;
  the worker detaches immediately and remains in the real repository. An
  OS-level lock prevents duplicate schedulers. The macOS dashboard launcher
  serves the HTML with `--external-scheduler` so it does not create a second
  updater.
- The UI reports the A3 market-observation date and SQLite retrieval timestamp
  separately from the purchase date. It never labels any embedded IAMC snapshot
  as a current observation or computes a current rate from it.
- Opening the HTML directly through `file://` cannot reach the loopback JSON
  endpoints. `Abrir Modelo LECAP BONCAP.command` is the normal macOS entry point
  and starts the updater, loopback service and Chrome together.

## Security

- Bind only to `127.0.0.1`; never `0.0.0.0`.
- Serve only the approved dashboard and fixed JSON endpoints.
- Do not expose `.env`, credentials, arbitrary files or raw database access.
- Do not place API keys in HTML, JavaScript, logs or query parameters.
- The macOS launcher contains the explicit production acknowledgement; no
  write/trading endpoint exists in this integration.

## Formula governance

**Changed on 26 October 2026 by owner decision; supersedes the previous rule.**

The validated Decimal engine is the single calculation path. The HTML contains
no financial formula: it requests `/api/metrics` and renders the result. The
service applies R-001 (maturity value), R-002 (HPR), R-003 (TNA), R-004
(TEA/TEM) and R-005 (Duration) by calling `src/financial_engine`, and nothing
else computes them.

Why the previous rule was reversed: the dashboard re-implemented the same
formulas in JavaScript with binary floating point, in parallel with the engine.
Two implementations of one methodology drift — the 11 August 2026 TNA correction
had to be applied on both sides — and the HTML copy was never the validated one.
The reversal removes the second implementation; it does not widen what the
service is allowed to do. The service still performs no calculation of its own:
it orchestrates the engine and applies two presentation rules that are not
financial methodology, both disclosed on every response:

- the settlement date (provider-reported when the price is aligned, otherwise
  T+1 from the business-day calendar); and
- the temporal-alignment guard below.

Numbers crossing the boundary are strings or `null`, never binary floats. The
HTML converts them to `Number` only to display and sort; the exact value is the
string the service returns. TNA, TEA and TEM continue to follow the official
IAMC glossary.

### Holiday calendar

The hand-entered holiday list moved from the HTML to
`src/local_dashboard/market_calendar.py`. Moving it does not validate it: there
is still **no governed market-calendar source**, coverage is 2026 plus
1 January 2027, and a settlement date outside that window is reported as
`outside_hand_entered_calendar_coverage` rather than presented as reliable. A
wrong holiday shifts the settlement date and therefore the residual term.

### Consequence for offline use

The calculator no longer works without the local service: with the service down
the dashboard shows no rates and states why. This was accepted on 26 October
2026 — the page already depended on the service for prices, and opening it
through `file://` was already degraded.

The futures screen is unchanged and remains stricter: it contains no financial
formula and calls no calculation endpoint.


The futures screen does not request spot or calculate forward points, implied
devaluation, annualized rates or a theoretical forward. R-009 remains
`Under Review` and unapproved for production implementation.

---

**Version:** 1.8

**Last Updated:** Monday, 26 October 2026
