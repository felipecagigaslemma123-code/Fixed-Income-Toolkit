# Development Log

## 12 August 2026 — Owner reconfirmed the split day-count convention

- The owner selected the existing mixed convention as the definitive project
  decision: contractual VPV keeps the Treasury-adapted 30/360 rule, while
  residual secondary-market yields use actual calendar days on a 365-day basis.
- Yield relationships remain `TEA = (1+HPR)^(365/D) - 1`,
  `TEM = (1+TEA)^(1/12) - 1`, and `TNA = TEM x 12`.
- No financial-engine formula changed because Python and the dashboard already
  implemented this convention. Source-of-truth documentation was synchronized;
  the former simple 30/360 TNA remains preserved only as rejected historical
  evidence.

## 11 August 2026 — Letras calculator verified end-to-end (closed)

- Diagnosed "sin precios": not a code/API bug. The local SQLite had current
  prices (287 quotes, 2026-08-11); the local loopback service simply was not
  running, so the browser fell back to the embedded snapshot and the alignment
  guard (correctly) withheld rates. Verified the loopback + `/api/market/quotes`
  serve the data correctly.
- Confirmed A3 returns per-instrument variants across two segments: Bilateral
  (BT, base ticker, quoted per 1 VN) and Garantizado (GT, `.../24hs` and
  `.../CI`, quoted per 100 VN). The dashboard already selects only the
  `/24HS` Garantizado (per-100) price and strips the suffix — matching is
  correct, no fix needed.
- Verified the full chain end-to-end with today's real prices: A3 `/24hs`
  price → VPV (R-001) → yield (IAMC ACT/365, TNA=TEM×12) → Duration (R-005).
  Sensible results (e.g. S16O6 TNA 20.89% at price 101.46). Full suite green (156).
- The letras calculator (HPR, TNA, TEA, TEM, VPV, Macaulay, Modified, with the
  LECAP/BONCAP eligibility gate) is complete for the approved scope. Reconnecting
  is an operational step on the user's machine (run the local toolkit launcher).


## 11 August 2026 — Dashboard yield JS synced to the corrected IAMC convention

- The LECAP/BONCAP dashboard (`outputs/modelo_lecap_boncap.html`) computed its
  rates in JavaScript with the **old** convention (30/360, `TNA = HPR·360/D`),
  independent of the corrected Python engine. It displayed rates that were too
  high (e.g. S16O6 TNA 25.19% vs 24.85%; the long T30J7 27.24% vs 24.68%).
- Synced the dashboard JS to the IAMC convention: residual in **actual calendar
  days**, `TEA = (1+HPR)^(365/D) − 1`, `TEM = (1+TEA)^(1/12) − 1`,
  `TNA = TEM·12`. Verified it now reproduces the Python engine exactly for S16O6.
  VPV and Macaulay/Duration keep 30/360 (R-001 / R-005).
- Updated the dashboard methodology text and the pinned assertions in
  `tests/test_local_dashboard.py`. Full suite green (156).
- **Root cause / follow-up:** the yield formula is duplicated (Python engine +
  dashboard JS), which is why they drifted. The dashboard should eventually
  consume the engine (single source of truth) via the loopback service. Also
  flagged: the yield is ACT/365 while Duration stays 30/360 (R-005) — a
  day-count inconsistency to reconcile in a future R-005 review.


## 11 August 2026 — Explicit calculation-eligibility flag by family

- Added `market_data/calculation_eligibility.py`: a pure gate mapping instrument
  family → `(calculable, reason)`. Only LECAP/BONCAP (fixed-rate capitalizable,
  R-001..R-004 approved) are calculable; LELINK (dollar-linked), LECER
  (CER-adjusted), LEDE (discount) and generic families are **not**, each with an
  explicit reason. This makes the "universe visible ≠ yield calculated"
  separation explicit instead of implicit, so a dollar-linked letra is never
  given a LECAP-style rate.
- Surfaced `calculation_eligible` + `calculation_reason` in the lifecycle
  payload and as a tooltip on the "Fuera del cálculo LECAP/BONCAP" cell of the
  LECAP/BONCAP dashboard.
- Added `tests/test_calculation_eligibility.py`. Full suite green (156).
- Follow-up (not done): open dollar-linked / CER research so LELINK/LECER can
  enter the calculation with their own approved methodology.


## 11 August 2026 — A3 pagination and safe T+1 price identity

- Confirmed that `rentafija` uses one-based pages of 50 records. The prior
  unpaged request omitted valid rows, including `S15S6/24hs`; the provider now
  exhausts every page and consolidates repeated page-boundary records.
- Confirmed that A3 can publish the same contract/term on two undocumented
  numeric scales (`S30S6=1.1377` and `S30S6/24hs=113.85`). The calculator now
  accepts only the explicit `/24hs`, `plazo=001` observation. Unsuffixed rows
  are preserved as market evidence but cannot generate a current yield.
- No ×100 conversion was introduced, and no financial formula or contractual
  datum was changed.

## 11 August 2026 — A3 24-hour ticker reconciliation

- Confirmed in the live Production response that A3 publishes the requested
  T+1 observations with `plazo=001` and tickers such as `S30S6/24hs`.
- Corrected contract reconciliation so the redundant `/24hs` settlement suffix
  is removed only for explicit term `001`. The raw A3 ticker remains preserved
  in SQLite/evidence, and different prefixes such as `X30S6` are not merged.
- Applied the same identity rule to the LECAP/BONCAP panel and Treasury
  lifecycle activation; no financial formula, price or contractual datum was
  changed.

## 11 August 2026 — Letra yield convention corrected to IAMC (ACT/365, TNA=TEM×12)

- Empirically reconciled the letra yield against the BYMA/IAMC daily report for
  **S16O6** (10-Aug-2026). The report prints **66 actual days** (not the 30/360
  value of 65) and its published TNA (24.92%) is reproduced by **TNA = TEM × 12**
  (nominal annual, monthly compounding), not by the previous simple 30/360
  annualization (which gave 25.19%).
- Corrected `financial_engine/letras_yield.py`: residual term now uses **actual
  calendar days on a 365-day basis**; `TEA = (1+HPR)^(365/D) − 1`,
  `TEM = (1+TEA)^(1/12) − 1`, `TNA = TEM × 12`. The 30/360 convention is kept
  **only** for the maturity value (VPV, R-001).
- The previously documented "IAMC-validated" 30/360 simple formula, and the
  explicit exclusion of `TNA = TEM × 12`, were both **wrong** and are corrected
  in R-003, R-004 and `iamc_yield_methodology_validation_2026-08-11.md`, with the
  S16O6 reconciliation table recorded.
- Rewrote `tests/test_letras_yield.py` to anchor on the real S16O6 report values
  (reproduced within price-rounding tolerance) plus the exact `TNA = TEM×12`
  relationship. Full suite green.
- The temporal-mixing safeguards (blocking a historical price relabeled as
  current) are retained — that was the real cause of the earlier gross mismatch.


## 11 August 2026 — Letra duration approved and implemented

- Project owner granted production approval for **R-005 Duration**, scoped to
  **single-payment letras only**. Research record and `docs/research/README.md`
  updated to `Implementation Approved: Yes`.
- Implemented `financial_engine/duration.py`: Macaulay = 30/360 residual term / 360;
  Modified = Macaulay / (1 + (1+TEA)^(1/m) − 1), with the compounding frequency
  `m` disclosed on every result. Decimal-only, builds on `day_count.py` and the
  `letras_yield.py` TEA input. Regression tests in `tests/test_duration.py`.
- Coupon-bearing bonds (multi-cash-flow, PV-weighted duration) remain out of
  scope and unapproved.
- The dollar-**futures** implied rate (TNA / implied devaluation) was **not**
  implemented: it depends on R-009 (still Under Review — spot source, quote
  direction and temporal convention are open) and no spot datum is wired yet.
  Deferred by owner decision until R-009 closes; its Research Gate stays closed.

## 11 August 2026 — Current national-Treasury universe

- Approved the current-dashboard boundary: instruments disappear from current
  selectors, comparisons and charts on their explicit maturity date, while the
  historical embedded record is preserved.
- Expanded official discovery from national Treasury Letras to both Letras and
  Bonos, with an explicit exclusion of provincial, municipal and corporate
  issuers.
- Separated universe visibility from calculation eligibility. Newly detected
  Treasury species become visible with lifecycle and evidence status, but no
  LECAP/BONCAP formula is applied until the family and every contractual input
  are supported.
- Connected the current macOS launcher to the explicitly acknowledged,
  read-only A3 Production environment so secondary-market activation represents
  the real market rather than UAT.
- Loaded seven result publications currently exposed by Secretaría de Finanzas
  into the local lifecycle database: 27 national-Treasury source rows were
  preserved, including reopenings. A3 returned no quotes at the time of the
  check, so no candidate was promoted; the 15-minute schedule will retry.

## 11 August 2026 — Futures review: 3.9 compatibility, cleanup, expiry

- **Runtime target set back to Python 3.9.** Removed `dataclass(slots=True)` from
  the six files that used it and restored `requires-python = ">=3.9"`. Reason:
  `slots=True` (Python 3.10+) was the *only* 3.10-specific construct in the code,
  the owner's working `.venv` is 3.9.6, and the rest of the codebase is already
  3.9-safe. This intentionally reverses the earlier "min runtime 3.10" note; the
  slots micro-optimization was not worth forcing an interpreter upgrade. Moving
  back to 3.10+ later is trivial (re-add slots, bump `requires-python`).
- **Removed the orphaned Stage-0 `FuturesContract`** model (superseded by
  `FuturesContractReference`); `models/contract.py` emptied (deletion blocked by
  the environment).
- **Added DLR futures expiry resolution** (`market_data/futures_expiry.py`):
  provider `endDate` first, else the last-business-day-of-month convention, else
  unresolved. Surfaced `maturity_date`/`maturity_source` in the futures payload
  and the observed-futures screen. Owner-approved as a contractual date only; no
  R-009 formula was implemented and the gate stays closed. Caveat: the
  convention fallback is not yet holiday-aware.
- Added `test_futures_expiry.py`; full suite green.

## 11 August 2026 — LECAP dashboard refresh-date correction

- Separated the user-selected purchase date from the A3 price-observation date.
- The dashboard now defaults the purchase date to the computer's current date;
  pressing the manual refresh button resets it to today.
- Automatic refreshes and price-basis changes preserve a manually selected
  purchase date.
- The status line now reports query time, actual A3 market date and SQLite
  retrieval time independently, while the embedded 17 July snapshot remains
  explicitly historical.
- Added a macOS double-click launcher so the dashboard opens through the
  loopback SQLite service instead of an unconnected `file://` page.

## 10 August 2026 — Letras yield engine approved and implemented

- Project owner granted production approval for R-001 (VPV), R-002 (HPR),
  R-003 (TNA) and R-004 (TEA/TEM). Research records and `docs/research/README.md`
  updated to `Implementation Approved: Yes` with the owner decision recorded.
- Implemented the Treasury-adapted 30/360 day count (`financial_engine/day_count.py`),
  enabled the VPV formula (`financial_engine/maturity_value.py`), and added the
  secondary-market letras yield calculator (`financial_engine/letras_yield.py`)
  computing HPR/TNA/TEA/TEM. Decimal-only, no IO.
- Added regression tests (`test_day_count.py`, `test_maturity_value.py`,
  `test_letras_yield.py`) with hand-computed reference values. Full suite green.
- Note: external IAMC/official cross-validation of the yield labels remains a
  recommended follow-up; approval was by owner decision.

## 10 August 2026 — Observed dollar-futures local prototype

- Documented A3's public futures viewer as a provisional, local-only source,
  separate from both MAE MarketData and the future credentialed Primary API.
- Implemented DLR standard/mini discovery and recent-trade normalization using
  Decimal directly from JSON, without binary-float financial processing.
- Added SQLite contract lifecycle and immutable trade history. Empty or failed
  reference responses retain the last valid active listing.
- Added independent daily contract and 15-minute trade schedules, plus one-shot
  and foreground local commands.
- Added `outputs/futuros_dolar.html`, a compact observed-market table with
  explicit gaps for bid/ask, settlement, high/low and open interest when the
  provisional source does not supply them.
- Excluded spot, TNA, forward points, implied devaluation and every R-009
  formula. R-009 remains under review and its Research Gate remains closed.
- Added navigation between the existing Letras/Bonos dashboard and the new DLR
  view, both served only on loopback.
- Added offline provider, persistence, scheduler, API and HTML tests.

## 10 August 2026 — Treasury-to-A3 lifecycle approved and implemented

- Documented the Secretaría de Finanzas public result-page source contract.
- Added read-only discovery and normalization of Treasury Bill rows, preserving
  article metadata, every raw table cell and Decimal-safe representations of
  unambiguous source numbers.
- Implemented the approved activation hierarchy: exact official ticker first;
  when absent, a unique match by explicit family, currency and maturity date.
- A row present in A3 fixed income activates the instrument for analysis even
  when price or volume is zero.
- Kept operational activation independent from contractual and methodology
  validation; no Research Gate was changed.
- Added sticky active state, maturity transition, SQLite lifecycle persistence,
  explicit manual provenance and an on-demand synchronization command.
- Added 14 deterministic offline tests covering source parsing, Decimal
  preservation, matching, ambiguity, sticky activation, maturity, persistence
  and idempotent synchronization.
- Corrected the declared minimum runtime from Python 3.9 to Python 3.10 because
  the repository's documented `dataclass(slots=True)` contract already requires
  Python 3.10 or newer.
- Completed a read-only lifecycle smoke test against two live Secretaría result
  articles and A3 UAT: three Letras were detected, none was falsely activated,
  and no production endpoint or financial formula was used.
- Recorded the approved source frequencies: Secretaría every 24 hours and A3
  every 15 minutes.
- Split the combined synchronization into independent Treasury-discovery and
  A3-activation operations so either source can run or fail independently.
- Added a non-blocking scheduler service and foreground runner. Both jobs run
  immediately at startup and then follow their own intervals; UAT is the safe
  default and production still requires an explicit flag.
- Connected every A3 refresh to the existing Decimal-safe quote repository: the
  current daily observation is updated by ticker and settlement term, while
  history accumulates across market dates.
- Repeated the read-only UAT smoke after connecting quote persistence; five A3
  fixed-income rows and three lifecycle candidates were stored in a temporary
  SQLite database, with no false activation.
- Expanded the full automated suite to 68 passing tests.

## 10 August 2026 — MAE MarketData UAT connectivity confirmed

- Stored the UAT and production API keys only in the local, git-ignored `.env`;
  production was not queried.
- Executed a read-only smoke test against the MAE MarketData UAT fixed-income
  endpoint.
- Confirmed `https://apiuat.mae.com.ar/MarketData/v1/` as the working UAT base.
- Authentication succeeded and three fixed-income observations for 10 August
  2026 were normalized without schema errors.
- No financial formula was executed, no Research Gate was changed and no API
  credential was written to documentation or logs.

## 6 August 2026 — Research and dashboard synchronization

- Added `docs/research/README.md` as the central administrative register for
  R-001, R-002, R-003, R-004, R-005 and R-009.
- Synchronized the financial specification with R-001: the methodology is
  validated, but production implementation approval remains pending.
- Updated the HTML dashboards so their status labels match the research record,
  particularly the validated prototype scope of R-005.
- Updated the maturity-value module's explanatory text to distinguish validated
  methodology from a closed production-implementation gate.
- Recorded Thursday, 6 August 2026 as the documentation synchronization date.
- No formula was added to the production financial engine and no Research Gate
  was promoted.

## 6 August 2026 — Additional bibliography review

- Reviewed A3 Academia material on bonds, interest rates, Duration, forwards and
  futures, plus the supplied financial-modeling books.
- R-005 was strengthened to validate the Modified Duration formula when the
  periodic-yield frequency is explicit; production scope remains unchanged.
- R-004 now records A3's discrete and continuous capitalization formulas as
  supporting evidence without promoting its market application.
- R-009 now records discrete carrying-cost formulas and the daily-settlement
  reason that futures and forward prices may differ; it remains under review.
- Added `docs/research/bibliography_review_2026-08-06.md` with an applicability
  matrix and candidate research topics for the bond phase.
- No production financial code or Research Gate was opened.

## 5 August 2026 — Formula review decisions

- R-001 methodology was validated using the official Treasury VPV methodology
  and the project-approved February-aware 30/360 convention. Production
  implementation remains a separate pending approval.
- The two HTML prototypes now treat 28/29 February as conventional day 30
  without changing ordinary calendar-day-30 cases.
- HPR was retained; R-003 records simple annualization
  `HPR × 360 / remaining_days` and explicitly excludes `TEM × 12`.
- R-004 records the academically supported compound-equivalence formulas for
  TEM and TEA; market application remains pending.
- R-005 was created. Macaulay Duration is validated for single-payment
  instruments; Modified Duration remains conditional on the yield convention.
- R-009 was created with the forward-as-futures proxy explicitly under review
  and without production implementation.
- CASE-001 and CASE-002 were normalized and now preserve the reference
  workbook's maturity-value outputs as source-observation JSON strings. A
  separate full-precision Decimal result remains `null` until the production
  Decimal implementation exists.

This document records the technical progress of the project, including completed milestones, current status, architectural decisions, and upcoming development tasks.

## 11 August 2026 - IAMC yield methodology and current-price alignment

- Validated the R-003 TNA formula against the official IAMC fixed-income
  methodology glossary: `TNA = HPR x 360 / DAYS360_TREASURY`.
- Validated the R-004 compound formulas for TEA and TEM. The engine expresses
  TEM as the monthly equivalent of TEA, algebraically unchanged from the direct
  HPR formula.
- Explicitly rejected the S14G6 output near 258.44% because it combined the
  17 July embedded price with an August residual term.
- Established A3 T+1 as the operational current-price source. Historical IAMC
  report prices remain dated validation evidence and cannot silently generate
  current rates.
- Added S16O6 contractual data and the 10 August IAMC observation to the local
  dashboard baseline; live calculations use an aligned A3 observation when
  available.

---

## 10 August 2026 — Local HTML dashboard over SQLite

- Confirmed `outputs/modelo_lecap_boncap.html` as the retained local interface.
- Added a loopback-only HTTP bridge at `127.0.0.1`; it serves only the approved
  HTML and fixed JSON views for A3 quotes, lifecycle states and health.
- Replaced the dashboard's `data912` dependency with stored A3 T+1 observations.
- Price choice is explicit between last and close, with no silent substitution;
  unavailable values retain the disclosed 17 July 2026 embedded snapshot.
- Added immediate, manual and 15-minute browser refreshes.
- Added one local entry point that starts both the updater and the Chrome
  dashboard, retaining UAT as the default and the explicit production guard.
- Added lifecycle visibility without equating `ACTIVE_FOR_ANALYSIS` to financial
  validation. New active tickers lacking complete contractual inputs are not
  sent through the calculator.
- No financial formula, Research Gate, credential or production-provider setting
  was changed.

---

## Sprint 0

### Completed

- ✅ Project architecture defined.
- ✅ Repository structure created.
- ✅ Core documentation completed.
- ✅ Initial bibliography organized.
- ✅ First development tool implemented (`tools/inspect_excel.py`).

### Current Status

- Code review completed.
- `inspect_excel.py` approved.
- Virtual environment (`.venv`) created.
- `openpyxl` installed.
- Excel inspection successfully executed.
- Workbook inventory generated.
- Excel calculator analysis documented.

### Next Steps

1. Validate the Excel formulas against official sources.
2. Complete `docs/research/001_maturity_value.md`.
3. Update `market_conventions.md` with validated conventions.
4. Update `financial_specification.md`.
5. Begin implementation of the production financial engine.

---

## Project Status

**Version:** 0.1.0

**Current Milestone:** Project Foundation Completed

**Next Milestone:** Financial Validation Layer

---

## Letras Audit — 30 July 2026

### Evidence incorporated

- The official Treasury publication dated 20 March 2024 explicitly provides
  the general VPV formula, effective monthly rate definition and 30/360 basis
  for capitalizable Treasury bills.
- The reference workbook inventory documents the observed VPV, HPR, TNA and TEA
  formulas without promoting them to production conventions.

### Documentation corrections

- R-001 now distinguishes official general-methodology evidence from the
  unresolved operational day-count variant, rounding rules and human approval.
- R-003 was incomplete and has been restored as a full pending research record.
- `market_conventions.md` now records known evidence and unresolved convention
  details explicitly.
- Exploratory HTML outputs no longer describe VPV or Duration as validated.

### Remaining blockers before production closure

1. Validate the exact 30/360 operational variant and end-of-month behavior.
2. Validate settlement convention and holiday-calendar governance.
3. Complete and approve R-001, R-002, R-003 and R-004.
4. Create research documentation for Duration before any production use.
5. Complete normalized, reproducible validation cases with source traceability.
6. Obtain explicit human approval for every Research Gate.
7. Keep the future external market-data API outside the financial engine and
   document its schema, authentication, timestamps and price semantics when
   supplied.

---

---

## 2026-08-12 — Local service resilience and dashboard date alignment

### Treasury transport: read timeouts no longer crash the scheduler
`TreasuryAuctionProvider._default_transport` caught `HTTPError` and `URLError`
but not a bare `TimeoutError`/`socket.timeout`. A read timeout mid-response
(observed against argentina.gob.ar) therefore propagated out of
`LifecycleScheduler.run_due` — which only catches `MarketDataError` — and
terminated the whole scheduler subprocess, stopping the 15-minute A3 price
sync as collateral. The transport now translates read/connect timeouts into
`ProviderConnectionError` so the scheduler skips that tick and keeps running.
New `tests/test_treasury_provider_transport.py` pins the translation for
`TimeoutError`, `socket.timeout`, `URLError` and `HTTPError`.

### Dashboard: manual refresh aligns "fecha de compra" to latest price date
On manual refresh (↻), the trade date now snaps to the most recent available
price date in the fetched A3 quotes instead of forcing today. This keeps price
and trade date in the same session (alignment guard satisfied) so yields render
even when today's sync has not run yet; falls back to today when no data. A
status note warns when a prior day is being shown. `alignedCount` is computed
after the date is finalized. Existing `tests/test_local_dashboard.py`
assertions unchanged and passing.

### Scheduled daily continuous sync (runs on the user's Mac)

The cloud agent environment has no network egress to A3 (`api.mae.com.ar`) or the
Treasury site, so the recurring sync must run on the user's Mac, where the API
key (`.env`) and connectivity live. Added:

* `tools/sync_once.py` remains available for an explicit one-shot refresh.
* `tools/morning_sync.sh` now starts the perpetual approved scheduler, using the
  repository `.venv` first and accepting the declared Python 3.9 minimum.
* `tools/com.fixedincome.morningsync.plist` starts every day at 09:30 local
  time. A3 runs immediately and every 15 minutes; Treasury runs immediately and
  every 24 hours. The process remains independent of Chrome.
* macOS rejected direct launchd execution from the OneDrive CloudStorage path.
  Added `tools/morning_sync.command`, opened in the background through
  LaunchServices/Terminal, without moving or copying the repository. The
  scheduler now owns an OS-level lock so daily or manual starts cannot overlap.
* The macOS dashboard launcher uses `--external-scheduler` to avoid starting a
  second updater. Its manual refresh button is preserved.
* Added `tests/test_macos_schedule.py` and corrected the dashboard test so it
  asserts the approved latest-available-market-date behavior and warning,
  instead of retaining the obsolete “uses today” name.

Installation is local to the owner's `~/Library/LaunchAgents/` and is verified
with `launchctl` after deployment.

Operational regression executed after deployment: 32 focused tests passing,
including the schedule, source-failure isolation, A3 pagination, ticker
identity, dashboard temporal alignment and loopback route security.

---

**Document Version:** 1.3

**Last Updated:** Wednesday, 12 August 2026
