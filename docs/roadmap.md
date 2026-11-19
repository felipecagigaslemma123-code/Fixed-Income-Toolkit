# Fixed Income Toolkit

## Roadmap

This document defines the planned evolution of the Fixed Income Toolkit project.

The roadmap is organized into development phases. Each phase introduces new functionality while preserving the modular architecture of the system.

---

# Phase 1 — Minimum Viable Product (MVP)

Objective:

Build a reliable calculation engine for Argentine Treasury Bills.

Features:

- Discount Treasury Bills
- Fixed-rate Treasury Bills
- Manual data input
- Transparent calculations
- Validation against IAMC calculators
- Unit testing

---

# Phase 2 — Financial Engine Expansion

Objective:

Expand the pricing engine to support additional fixed-income instruments.

Planned features:

- Capitalizable Treasury Bills (LECAP)
- Fixed-rate Bonds
- Inflation-linked Bonds (CER)
- Dollar-linked Bonds
- Hard Currency Bonds
- Corporate Bonds (ON)

---

# Phase 3 — Market Data

Objective:

Replace manual inputs with market data sources.

Planned features:

- CSV import
- Excel import
- API integration
- Historical prices
- Automatic market updates

---

# Phase 4 — Portfolio Analytics

Objective:

Provide portfolio-level analysis.

Planned features:

- Portfolio valuation
- Performance calculation
- Yield comparison
- Cash flow analysis
- Duration
- Modified Duration
- Convexity

---

# Phase 5 — Reporting

Objective:

Generate professional reports.

Planned features:

- Excel export
- PDF reports
- Charts
- Summary dashboards

---

# Phase 6 — Professional Platform

Objective:

Transform the project into a complete fixed-income toolkit.

Planned features:

- Web interface
- User authentication
- Cloud deployment
- Real-time market data
- Portfolio management
- Risk analytics

---

# Development Status by Component

This section tracks real progress per component, distinguishing research,
exploratory prototype, and production. It complements — it does not replace — the
phase plan above.

## Maturity Value (VPV)

- Research: Methodology validated and implementation approved (R-001).
- Visual prototype: Implemented in HTML / Excel.
- Production engine: Implemented Decimal-only in `maturity_value.py`.
- Automated tests: Implemented, including February month-end boundaries.

## Effective return / TEM / TEA / TNA

- Research: the IAMC-reconciled ACT/365 convention is validated for
  compound-equivalent TEA/TEM and `TNA = TEM * 12` (R-003/R-004); HPR is
  retained under R-002. The former simple 30/360 TNA is rejected.
- Visual prototype: implemented in HTML with current-price temporal alignment;
  stale embedded prices cannot produce current yield metrics.
- Production engine: implemented Decimal-only in `letras_yield.py`.
- Automated tests: implemented for formulas, invalid inputs and the dashboard's
  temporal-alignment policy.

## Duration & Modified Duration

- Research: R-005 validated for the single-payment prototype scope. Macaulay and
  the Modified Duration formula are validated; Modified results require an
  explicit compounding frequency and a valid yield input.
- Visual prototype: Implemented in HTML.
- Production engine: Implemented for single-payment letras in `duration.py`.
- Automated tests: Implemented for the approved single-payment scope.

## Market Data Integration (A3 / MAE MarketData)

- UAT provider integration: Implemented with `x-api-key`; production activation
  remains an explicit operational decision.
- Decimal-safe SQLite persistence: Implemented for fixed-income observations.
- Local HTML bridge: Implemented as a loopback-only, read-only service over the
  existing `outputs/modelo_lecap_boncap.html` dashboard.
- Price selection: Explicit last or close; no silent bid/ask or cross-field
  substitution.
- Browser refresh: Immediate and every 15 minutes, plus manual refresh.
- Reliability, limits and redistribution terms not documented by the provider:
  remain pending in the provider contract.

## Treasury Bill Discovery and Operational Activation

- Official result source: Secretaría de Finanzas public result pages.
- Source contract: `docs/providers/treasury_auction_source.md`.
- Candidate ingestion: Implemented for Treasury Bill rows with raw evidence
  preservation and Decimal-safe normalization of unambiguous source numbers.
- Secondary-market confirmation: Implemented against A3 fixed-income quotes.
- Activation rule: Exact ticker when available; otherwise a unique match by
  explicit family, currency and maturity date.
- Ambiguous identity: Remains pending; manual fallback retained with provenance.
- Financial validation: Unchanged and independent from operational activation.
- Approved refresh policy: Secretaría every 24 hours; A3 fixed income every
  15 minutes, with independent schedules and an immediate first run.
- Scheduler implementation: Complete as a process-agnostic service plus a
  foreground runner. On the owner's Mac, a LaunchAgent starts the continuous
  Production scheduler every day at 09:30 local time; an OS-level lock prevents
  duplicate processes when the dashboard is opened separately.
- Local dashboard: Connected to SQLite and lifecycle state; operationally active
  tickers without complete contractual inputs are displayed as pending those
  inputs and are not inserted into financial calculations.
- Current-universe boundary: National Treasury Letras and Bonos are visible in
  the operational universe; provincial/corporate issuers are excluded. Matured
  instruments are retained historically but hidden from current calculator
  selectors, tables and charts.
- Methodology boundary: Visibility does not generalize the LECAP/BONCAP formula
  to CER, dollar-linked, fixed-rate or other Treasury families. Unsupported or
  contractually incomplete rows remain explicitly non-calculable.
- Current-rate policy: only an explicitly selected A3 T+1 price whose provider
  market date matches the selected purchase date can produce HPR/TNA/TEA/TEM.
  Historical IAMC snapshots stay dated and never act as a silent current-price
  substitute.

## Observed Dollar Futures Prototype

- Source: A3 / Matba Rofex public price viewer, documented as a provisional
  application endpoint rather than a confirmed stable API.
- Scope: standard and mini DLR contract references plus recent observed trades.
- Storage: Decimal-safe SQLite history, with daily contract refresh and
  15-minute recent-trade refresh while the local process is running.
- Dashboard: local HTML table at `/futures`, visually aligned with the market
  screen while preserving explicit missing values.
- Excluded: spot, forward points, implied devaluation, annualized rates,
  settlement substitution and all theoretical calculations.
- Governance: R-009 remains `Under Review`; the prototype does not close or
  bypass its Research Gate.

## Research Governance Snapshot

- Central status register: `docs/research/README.md`.
- Last administrative synchronization: Wednesday, 12 August 2026.
- R-001 through R-005 are approved only within their individually documented
  LECAP/BONCAP scopes; R-009 remains closed.
- The visual dashboards are exploratory and must disclose the status of every
  metric they display.

---

**Version:** 1.6

**Last Updated:** Wednesday, 12 August 2026
