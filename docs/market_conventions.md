# Market Conventions

## Purpose

This document records market conventions used or investigated by the Fixed
Income Toolkit. A convention is not approved for the production engine merely
because it appears in a reference workbook or exploratory prototype.

## General Principles

- Official market documentation has priority over observed implementations.
- Observed conventions remain explicitly marked as unvalidated.
- The exact convention variant, units and rounding rules must be documented
  before production use.

## Default Market Assumptions (MVP)

Unless explicitly specified otherwise:

- Valuation date is the current system date.
- Settlement convention is T+1 (24-hour settlement).
- Settlement date is the next business day according to the Argentine market calendar.
- Market price corresponds to the latest available price for T+1 settlement.

---

## Day Count Convention

Status:

Validated as the project convention for LECAP/BONCAP maturity-value and
residual-term calculations.

Source:

The Secretaría de Finanzas publication dated 20 March 2024 specifies a 30/360
basis for determining elapsed time between issue and maturity for capitalizable
Treasury bills, then converts the year fraction to months by multiplying by 12:

https://www.argentina.gob.ar/noticias/metodologia-de-calculo-para-la-letra-capitalizable-en-pesos

Approved operational implementation:

- The reference workbook uses Excel `DAYS360`.
- The project preserves the observed U.S./NASD-style handling of calendar day
  31: a starting day 31 becomes 30, and an ending day 31 becomes 30 when the
  adjusted starting day is 30.
- The project adds an explicit Treasury-compatible February rule: the last day
  of February becomes day 30, both as a starting date and as an ending date.
  This covers 28 February in a non-leap year and 29 February in a leap year.
- Ordinary dates on day 30 remain day 30. In particular, the rule does not roll
  an ending 30 September into October.
- This operational rule is used both for issue-to-maturity time and for the
  remaining settlement-to-maturity term in the exploratory calculator.

Rationale and scope:

The Secretaría de Finanzas establishes months of 30 days and years of 360 days
but does not name an algorithmic variant. The rule above is the human-approved
project adaptation: it preserves the existing reference cases and closes the
previous February gap. Because it intentionally makes the February treatment
explicit, it must not be described as exact Excel equivalence for every possible
date pair and must not be silently generalized to other instrument families.

References:

- Secretaría de Finanzas, “Metodología de cálculo para la letra capitalizable
  en pesos”, 20 March 2024.
- Microsoft Support, `DAYS360` U.S. (NASD) method definition.

---

## Settlement Convention

Status:

Validated — Implementation Approved (owner, 2026-10-26).

Convention:

- T+1 (24-hour settlement), the next business day of the Argentine market
  calendar.
- `D` is the actual number of calendar days from the settlement date to
  maturity.

Evidence:

Reconciled empirically against published market reports, by solving for the
settlement term that reproduces the published yields:

| Report | Close | T+0 | **T+1** | T+2 |
|--------|-------|-----|---------|-----|
| IAMC, *Informe Diario Títulos Públicos* (dollar-linked section) | 05-Oct-2026 | 0.123 pp | **0.003 pp** | 0.129 pp |
| *Informe de Renta Fija* (base BYMA), dollar-linked section | 30-Sep-2026 | 0.034 pp | **0.005 pp** | 0.042 pp |

(mean absolute error against the published annualized yields, five letras each)

This is independent of, and consistent with, the LECAP/BONCAP reconciliation of
11 August 2026, where the IAMC report printed 66 actual days for S16O6 under a
T+1 settlement date (`docs/research/iamc_yield_methodology_validation_2026-08-11.md`).

Scope and limits:

- The term convention is validated. The **business-day calendar itself is not**:
  holidays remain hardcoded in the exploratory HTML dashboard and still require a
  governed market-calendar source. A wrong holiday shifts the settlement date and
  therefore `D`.
- Validated for National Treasury letras and bonds quoted for 24-hour settlement.
  It is not generalized to other settlement terms or instrument families.

Source:

- IAMC, *Informe Diario Títulos Públicos*, 05-Oct-2026
  (`examples/8461d895-3558-4320-a500-f7c5698fda3d.pdf`).
- *Informe de Renta Fija* (Robles Alvarez Jesús, en base a BYMA), 30-Sep-2026
  (`examples/1790870714941.pdf`).
- Reconciliation detail: `docs/research/006_dollar_linked_letras.md` §Step 2.

---

## Face Value Convention

Status:

Validated for CASE-001 and CASE-002 contractual data.

Convention:

- Contractual and displayed maturity values are expressed per VN 100 unless a
  source explicitly states another nominal basis.

Source:

- Official Treasury issuance datasets recorded in the validation cases.
- The Treasury methodology publication illustrates the formula using another
  nominal basis; the formula itself is proportional to VNO.

---

## Rate Format

Status:

Contractual representation and the current LECAP/BONCAP secondary-market yield
convention are validated for their documented scopes.

Convention:

- Monthly issue rates are stored as decimal financial values.
- Percentage formatting belongs to presentation layers.

---

## Price Basis

Status:

Observed; market-data provider validation pending.

Convention used by the reference workbook and exploratory outputs:

- ARS per VN 100.

This observation must not be treated as a validated provider contract for the
future API.

---

## Secondary-Market Yield Convention (LECAP / BONCAP)

Status:

Validated and implementation approved by the project owner on 11 August 2026.

Convention:

- HPR uses maturity value divided by the explicitly selected secondary-market
  price, minus one.
- `D` is the actual number of calendar days from settlement to maturity.
- TEA uses ACT/365 compound annualization: `(1 + HPR)^(365 / D) - 1`.
- TEM is the monthly compound-equivalent rate: `(1 + TEA)^(1 / 12) - 1`.
- TNA is the nominal annual rate with monthly compounding: `TEM * 12`.
- The Treasury-adapted 30/360 convention applies to contractual VPV from issue
  to maturity; it does not apply to these residual secondary-market yields.
- Financial-engine calculations preserve Decimal precision. Rounding belongs to
  the presentation layer.

Operational price contract:

- Source: A3 fixed income.
- Settlement term: 24 hours (`plazo` 001).
- Price field: explicitly selected `last_price` or `close_price`; no silent
  substitution between them.
- The provider market date and settlement date remain attached to the price.
- A current-rate view must not combine a historical price-observation date with
  a later purchase or calculation date.
- If the current selected price is unavailable, HPR, TNA, TEA, TEM and yield-
  dependent metrics are unavailable. A dated historical snapshot may remain
  visible but must not be relabeled or calculated as current.

Source:

- IAMC, *Glosario de Indicadores y Metodologias de Renta Fija*.
- R-002, R-003 and R-004.
- `docs/research/iamc_yield_methodology_validation_2026-08-11.md`.

---

**Version:** 1.6

**Last Updated:** Monday, 26 October 2026
