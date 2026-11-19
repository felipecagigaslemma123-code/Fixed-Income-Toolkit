# Research R-001 — Maturity Value (VPV)

## Objective

The objective of this research is to validate the methodology used to determine the **Maturity Value (Valor de Pago al Vencimiento, VPV)** of Argentine Treasury capitalizable instruments before implementing the production pricing engine.

This document does **not** define the production implementation.

Its purpose is to collect contractual evidence, compare methodologies, validate assumptions, and document the rationale supporting the future implementation.

---

# Research Scope

Instrument family:

- LECAP
- BONCAP

Out of scope:

- Discount Treasury Bills
- CER-linked Bonds
- Floating-rate Bonds
- Dollar-linked Bonds
- Corporate Bonds

---

# Financial Context

LECAPs and BONCAPs are capitalizable Treasury securities.

Unlike traditional coupon bonds, these instruments generate their return through capitalization from the issue date until maturity.

The investor receives a single payment at maturity equal to the **Maturity Value (VPV)**.

The VPV represents the redemption value corresponding to a reference nominal value of VN 100.

---

# Research Questions

This research aims to answer the following questions:

1. How is VPV officially defined?
2. Is VPV contractually specified or calculated?
3. Which capitalization methodology is officially used?
4. Which day-count convention applies?
5. Which interest-rate convention applies?
6. Which official sources support the methodology?

---

# Reference Workbook

Workbook:

`examples/01_calculators/Calculadora de letras 17.07.26.xlsx`

Inspection utility:

`tools/inspect_excel.py`

Inspection outputs:

- `outputs/excel_workbook_inventory.json`
- `outputs/excel_cells_inventory.csv`

---

# Excel Observation

Observed worksheet:

`Lecap y Boncap`

Observed methodology:

VPV = 100 × (1 + Monthly Issue Rate) ^ ( DAYS360(Issue Date, Maturity Date) / 30 )

Observed variables:

- Monthly Issue Rate
- Issue Date
- Maturity Date
- Reference Face Value = VN 100
- Excel DAYS360 function

Current status:

Validated. The reference workbook, the official Treasury methodology and the
human-approved operational day-count rule are consistent for the project scope.

---

# Financial Interpretation

The Excel workbook suggests that the maturity value corresponds to the future value of VN 100 capitalized from the original issue date until maturity using the contractual monthly issue rate.

This interpretation is consistent with the official Treasury methodology
publication dated 20 March 2024.

Approved operational details:

- The day-count implementation preserves the observed U.S./NASD-style day-31
  rules and adds the project-approved Treasury adaptation for the last day of
  February.
- Both 28 February in non-leap years and 29 February in leap years are treated
  as conventional day 30 when they are a starting or ending date.
- The calculated full-precision value is preserved internally. Rounding is a
  presentation or source-publication concern and must not alter the calculation.
- Official published values and recalculated values remain distinct validation
  fields whenever both are available.
- Applicability remains subject to each instrument's contractual documentation.

---

# Contractual Validation

## Argentine Treasury

Status:

✅ Contractual Data Validated

Evidence collected:

Official Treasury issuance documentation provides:

- Instrument type.
- Issue date.
- Maturity date.
- Effective monthly issue rate.
- Reference face value (VN 100).
- Auction resolution.

Validated instruments:

- CASE-001 — S30S6
- CASE-002 — S31G6

Current conclusion:

The contractual characteristics required by the pricing engine have been validated using official Treasury documentation.

No inconsistencies have been identified.

---

# Methodology Validation

Status:

🟢 Validated

Current observations:

The Treasury publication “Metodología de cálculo para la letra capitalizable en
pesos”, dated 20 March 2024, explicitly publishes:

- `VPV = VNO × (1 + Tem) ^ t`;
- `Tem` as the effective monthly rate;
- `t` as elapsed time from issue to maturity;
- a 30/360 basis converted to months by multiplying the year fraction by 12;
- applicability of the described formula to future placements of this
  instrument type.

This is authoritative evidence for the capitalization methodology. The
Secretaría de Finanzas does not name the algorithmic 30/360 variant, so the
project records the exact operational rule in `docs/market_conventions.md`. The
Treasury-adapted February behavior was approved by the project owner on 5 August
2026 while preserving the existing reference cases.

The methodology is validated. Production implementation remains a separate
approval step; this research validation does not by itself authorize or assert
that production code exists.

---

# Evidence Collected

| Source | Evidence | Status |
|---------|----------|--------|
| Excel Calculator | VPV methodology observed | ✅ |
| Argentine Treasury Issuance Files | Contractual parameters validated | ✅ |
| Treasury Auction Documentation | Contractual information validated | ✅ |
| Treasury Methodology Publication (20-Mar-2024) | VPV formula, effective monthly rate and 30/360 basis officially published | ✅ Validated |
| Microsoft `DAYS360` documentation | Baseline U.S. (NASD) day-31 behavior | ✅ Supporting reference |
| A3 Academia – Bonds | Zero-coupon/bullet instruments have a single maturity cash flow | ✅ Contextual evidence |
| Financial Modeling – Bonds | Redemption value is payable at maturity; zero-coupon duration equals maturity | ✅ Contextual evidence |
| Pignataro – Financial Modeling and Valuation | Corporate debt maturity schedules; no LECAP VPV methodology | Not applicable to formula validation |
| IAMC Methodology | Pending review | ⏳ |
| Bodie – Investments | Pending review | ⏳ |
| Fabozzi – Fixed Income Analysis | Pending review | ⏳ |

---

# Bibliographic Validation

## Additional bibliography review — 6 August 2026

The A3 `Bonos-2025.pdf` material classifies zero-coupon and bullet instruments as
single-payment structures at maturity. The reviewed *Financial Modeling* bond
chapter likewise distinguishes maturity date, redemption value and the final
cash flow. These sources support the single-payment interpretation used by the
Toolkit, but they do not define the Argentine contractual capitalization rate or
the Treasury's VPV calculation.

Paul Pignataro's *Financial Modeling and Valuation* was also reviewed for
relevance. Its maturity discussion concerns corporate debt schedules and
refinancing projections, not the contractual maturity-value formula for LECAP or
BONCAP instruments. It is therefore recorded as reviewed but is not used to
promote or alter R-001.

No new source contradicts the official Secretaría de Finanzas formula. The
official Treasury publication remains the primary authority for VPV.

## Bodie – Investments

Status:

Pending review.

Topics:

- Compound Interest
- Fixed Income Securities
- Treasury Instruments
- Holding Period Return

Current conclusion:

Pending.

---

## Fabozzi – Fixed Income Analysis

Status:

Pending review.

Topics:

- Zero-Coupon Securities
- Capitalizable Instruments
- Redemption Value
- Fixed Income Valuation

Current conclusion:

Pending.

---

# Validation Matrix

| Source | Contractual Data | Methodology | Status |
|---------|-----------------:|------------:|--------|
| Excel Calculator | — | Observed | ✅ |
| Argentine Treasury | Validated | Official formula and general 30/360 basis published | ✅ |
| Project convention | — | Treasury-adapted February month-end behavior | ✅ Human approved |
| A3 / Financial Modeling | — | Single-payment structure only; not the Argentine VPV formula | Supporting |
| IAMC | Pending | Pending | ⏳ |
| Bodie | Pending | Pending | ⏳ |
| Fabozzi | Pending | Pending | ⏳ |

---

# Current Implementation Decision

Current decision:

The contractual inputs, VPV formula, 30/360 basis and Treasury-adapted
month-end behavior are validated for LECAP/BONCAP maturity-value calculations.

Validation Status:

🟢 Validated

Approved Formula:

`VPV = VNO × (1 + TEM_issue) ^ (DAYS360_TREASURY(issue, maturity) / 30)`

Approved Market Convention:

Treasury-adapted 30/360, annualization basis 360 days and conventional month of
30 days, including the documented last-day-of-February rules.

Rounding Policy:

No intermediate rounding. Preserve the recalculated value at available
precision; compare an official published value at the precision supplied by its
source and keep presentation rounding separate.

Implementation Approved:

Yes — approved for production by the project owner on 2026-08-10. Implemented in
`src/financial_engine/maturity_value.py`, using the Treasury-adapted 30/360 day
count in `src/financial_engine/day_count.py`. Regression tests:
`tests/test_maturity_value.py`, `tests/test_day_count.py`.

---

# References

- Secretaría de Finanzas, “Metodología de cálculo para la letra capitalizable
  en pesos”, 20 March 2024:
  https://www.argentina.gob.ar/noticias/metodologia-de-calculo-para-la-letra-capitalizable-en-pesos
- Microsoft Support, `DAYS360` function (U.S./NASD method):
  https://support.microsoft.com/en-us/excel/functions/days360-function
- Reference workbook:
  `examples/01_calculators/Calculadora de letras 17.07.26.xlsx`

---

**Last Updated:** Thursday, 6 August 2026

Primary references:

- Argentine Treasury official issuance documentation.
- Argentine Treasury auction documentation.
- Secretaría de Finanzas, “Metodología de cálculo para la letra capitalizable
  en pesos”, 20 March 2024:
  https://www.argentina.gob.ar/noticias/metodologia-de-calculo-para-la-letra-capitalizable-en-pesos
- Investments (Bodie, Kane & Marcus).
- Fabozzi – Fixed Income Analysis.
- IAMC methodology.
- Reference Excel workbook.

---

# Research Status

Research ID:

R-001

Status:

🟢 Validated

Contractual Validation:

✅ Completed

Methodology Validation:

✅ Completed

Implementation Approved:

✅ Yes — owner decision, 2026-08-10

Version:

1.5

Last Updated:

Monday, 10 August 2026
