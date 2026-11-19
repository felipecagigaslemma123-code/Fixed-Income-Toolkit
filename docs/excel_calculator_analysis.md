# Reference Excel Calculator Analysis

## Purpose

This document records a read-only structural and formula inventory of the
reference workbook:

`examples/01_calculators/Calculadora de letras 17.07.26.xlsx`

The workbook is evidence of observed behavior. It is not an authoritative source
for financial formulas or market conventions, and this analysis does not approve
any methodology for production.

The workbook observations below are preserved as historical evidence. Current
methodology status is governed by the corresponding research document and was
administratively synchronized on Wednesday, 12 August 2026.

## Inspection Artifacts

- Utility: `tools/inspect_excel.py`
- Workbook inventory: `outputs/excel_workbook_inventory.json`
- Cell inventory: `outputs/excel_cells_inventory.csv`

The stored inventory reports:

- 2 worksheets;
- 265 non-empty cells;
- 135 formula cells;
- visible worksheet `Lecap y Boncap`;
- hidden worksheet `Sheet2`, containing the observed holiday list.

## Workbook Structure

The visible worksheet contains:

- LECAP instrument columns;
- BONCAP instrument columns;
- a free-form calculator section;
- contractual inputs;
- negotiation and settlement inputs;
- observed VPV, holding-period return, TEA and TNA outputs.

The workbook distinguishes the following inputs:

- issue date;
- maturity date;
- negotiation date;
- settlement term;
- monthly issue rate;
- market price.

## Observed Conventions

The following conventions are present in workbook cells or formulas:

- `DAYS360` for original and residual terms;
- `WORKDAY` for settlement dates;
- `24 h` mapped to one business day after negotiation;
- a hidden holiday range used by `WORKDAY`;
- prices expressed as ARS per VN 100;
- monthly issue rates stored as decimal rates.

These are observations only. The workbook does not establish that the exact
Excel `DAYS360` variant, holiday list, settlement rule or price semantics are
approved project conventions.

## Observed Formula Relationships

### Maturity Value (VPV)

The workbook contains the relationship:

```text
100 × (1 + monthly issue rate) ^
((DAYS360(issue date, maturity date) / 360) × 12)
```

Research owner:

- R-001.

Status:

- General formula and 30/360 basis supported by an official Treasury
  publication.
- R-001 subsequently validated the operational Treasury-adapted 30/360 rule,
  rounding policy and methodology. Production implementation is approved and
  complete.

### Holding Period Return

The workbook contains the relationship:

```text
(VPV / market price) - 1
```

Research owner:

- R-002.

Status:

- Formula approved in R-002 and implemented with the date-aligned A3 T+1
  market-price input contract.

### Effective Annual Rate (TEA)

The workbook contains a compound annualization relationship using:

- holding-period return;
- `DAYS360` between settlement and maturity;
- an observed 360-day annualization basis.

Research owner:

- R-004.

Status:

- The workbook's 30/360 annualization is retained as historical evidence but is
  rejected for production. R-004 validates the ACT/365 secondary-market
  convention implemented with date-aligned A3 T+1 inputs.

### Nominal Annual Rate (TNA)

The workbook contains a simple annualization relationship using:

- holding-period return;
- `DAYS360` between settlement and maturity;
- an observed 360-day annualization basis.

Research owner:

- R-003.

Status:

- The workbook's simple 30/360 TNA is retained as historical evidence but is
  rejected for production. R-003 validates the IAMC-reconciled
  `TNA = TEM x 12` convention.

## Cached Results and Reproducibility

The inventory preserves formula text and the values last cached by Excel. Many
yield outputs are blank because the corresponding market-price or negotiation
inputs were not populated when the workbook was last saved.

Cached results must not be treated as independently validated values. A
reproducible validation case requires:

- explicit contractual data;
- explicit market observation and timestamp;
- source traceability;
- the exact convention set;
- expected results;
- a dimension-specific validation status.

## Duration

No Duration or Modified Duration methodology is documented by this reference
workbook inventory. R-005 was subsequently created and validates Macaulay and
the Modified Duration formula for its documented single-payment prototype
scope. Duration remains outside Version 1 production scope.

## Conclusions

The reference workbook is useful for identifying candidate inputs, outputs and
formula relationships. It is insufficient on its own to:

- approve a production formula;
- establish official market conventions;
- define provider price semantics;
- close a Research Gate;
- establish rounding rules.

## Open Items

1. Complete settlement and holiday-calendar governance beyond the current
   explicit A3 T+1 contract.
2. Continue independent comparisons of current A3-derived rates with IAMC
   reports.
3. Obtain explicit human approval before every additional production
   implementation.

---

**Version:** 1.2

**Last Updated:** Wednesday, 12 August 2026
