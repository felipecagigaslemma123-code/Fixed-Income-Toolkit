# Research R-005 — Duration

| Field | Value |
|-------|-------|
| Research ID | R-005 |
| Topic | Macaulay Duration and Modified Duration |
| Instrument Family | LECAP / BONCAP |
| Status | Validated — Implementation Approved for single-payment letras (owner, 2026-08-11) |
| Owner | Felipe Cagigas |
| Reviewer | Pending |
| Last Updated | Thursday, 6 August 2026 |

---

# Objective

Validate the duration measures shown by the exploratory LECAP/BONCAP calculator
without extending Duration into the Version 1 production engine.

# Instrument Structure

For this research, a LECAP or BONCAP is treated as a single-payment instrument:
the holder receives one cash flow, the maturity value, at maturity. No interim
coupon cash flows are assumed.

# Bibliographic Evidence

Bodie, Kane and Marcus, *Investments*, 10th edition, Chapter 16:

- define Macaulay duration as the present-value-weighted time to cash flows;
- state that the duration of a zero-coupon bond equals its time to maturity;
- define modified duration as `D* = D / (1 + y)` when `y` is the effective yield
  per payment period;
- give the general nominal-yield form `D* = D / (1 + y_BEY / n)` for `n`
  payment periods per year.

For one final cash flow, the single weight is 1. Therefore:

```text
Macaulay Duration = time from settlement to maturity
```

Under the approved project day-count convention:

```text
Macaulay Duration (years)
  = DAYS360_TREASURY(settlement_date, maturity_date) / 360
```

# Validation Decision

## Macaulay Duration

Validation Status:

🟢 Validated for single-payment LECAP/BONCAP instruments.

Approved Formula:

`D_Mac = remaining_days_30_360 / 360`

Human Approval:

Yes, 5 August 2026.

## Modified Duration

Validation Status:

🟢 Formula validated when the periodic-yield convention is explicit.

Both A3 Academia and the reviewed financial-modeling reference publish the
standard relationship:

```text
Modified Duration = Macaulay Duration / (1 + YTM / n)
```

where `YTM / n` is the yield per compounding/payment period. The prototype uses
the equivalent effective-period form:

```text
periodic_yield = (1 + TEA)^(1 / m) - 1
Modified Duration = Macaulay Duration / (1 + periodic_yield)
```

The two forms are equivalent when `periodic_yield` represents the same periodic
yield as `YTM / n`. Therefore the formula is validated, while every result must
retain the disclosed frequency `m`. Availability or market validation of the TEA
input remains an R-004 dependency and is not silently inferred by R-005.

Implementation Approved:

Yes — approved for production by the project owner on 2026-08-11, for
**single-payment letras only**. Implemented in
`src/financial_engine/duration.py` (Macaulay + Modified), building on
`day_count.py` and the TEA input from `letras_yield.py`. Regression tests in
`tests/test_duration.py`. Coupon-bearing bonds (multi-cash-flow, PV-weighted
duration) remain out of scope and unapproved.

# Prototype Status

- Macaulay Duration may be labeled “Validated — single payment”.
- Modified Duration may be labeled “Validated formula — frequency and TEA input
  required”.
- Neither status closes a production Research Gate for portfolio-risk analytics.

# References

- Bodie, Z.; Kane, A.; Marcus, A., *Investments*, 10th edition, Chapter 16,
  textbook pages 520–522 (PDF pages 549–551):
  `bibliography/Libros/Investments 10th edition_Bodie_Keane_Marcus.pdf`
- A3 Academia, `Tasas-de-interes-y-medidas-de-sensibilidad-2025.pdf`, pages
  11–14.
- *Financial Modeling*, Chapter 14, PDF pages 207–214, especially the zero-coupon
  and modified-duration discussion on pages 213–214.
- `docs/market_conventions.md`
- `docs/research/004_tea.md`

---

**Version:** 1.2

**Last Updated:** Thursday, 6 August 2026
