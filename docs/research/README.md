# Research Status Register

This register provides the administrative view of the financial research used
by the Fixed Income Toolkit. The individual research document remains the
authoritative record for each methodology.

## Status as of Monday, 26 October 2026

| Research ID | Topic | Validation status | Implementation approved | Current use |
|-------------|-------|-------------------|-------------------------|-------------|
| R-001 | LECAP/BONCAP maturity value (VPV) | Validated | Yes (owner, 2026-08-10) | Production: `financial_engine/maturity_value.py` |
| R-002 | Holding Period Return (HPR) | Validated (owner decision) | Yes (owner, 2026-08-10) | Production: `financial_engine/letras_yield.py` |
| R-003 | Nominal Annual Rate (TNA) | Validated against official IAMC glossary | Yes (owner, 2026-08-11) | Production: `financial_engine/letras_yield.py`; stale-date use blocked |
| R-004 | TEM/TEA compound equivalence | Validated against official IAMC glossary | Yes (owner, 2026-08-11) | Production: `financial_engine/letras_yield.py` |
| R-005 | Macaulay and Modified Duration | Validated (single-payment letras) | Yes (owner, 2026-08-11) | Production: `financial_engine/duration.py` (single-payment letras) |
| R-006 | Dollar-linked Treasury letras (LELINK) yield + FX total return | Under review — **Q3 resolved** (yield convention reconciled 2026-10-26); Q5 open | No | Research only; prototype UNVALIDATED outside `src/financial_engine/` |
| R-009 | FX forward and provisional futures proxy | Under review | No | Research only |

## Consolidated Decisions

### Validated methodology or formula

- R-001 validates the official Treasury maturity-value relationship for
  LECAP/BONCAP and the project-approved Treasury-adapted 30/360 rule, including
  the last day of February.
- R-003/R-004 validate the secondary-market yield convention reconciled against
  the official IAMC report: actual residual days, ACT/365 compound
  annualization, `TEM = (1 + TEA)^(1/12) - 1`, and `TNA = TEM x 12`. The
  former S14G6 output near 258.44% is rejected because it mixed a historical
  price with a later calculation date; it is not an alternative methodology.
- R-005 validates Macaulay Duration for a single final cash flow and validates
  the Modified Duration formula when the periodic-yield frequency and valid
  yield input are explicit.
- R-006 (2026-10-26) reconciles the **dollar-linked secondary-market yield** as
  ACT/365 effective from T+1 settlement against a redemption value of 100 in
  linked units, with `MD = Macaulay / (1 + TEA)`. Evidence: IAMC *Informe Diario
  Títulos Públicos* of 05-Oct-2026 (mean absolute error 0.003 pp over five
  letras) and the BYMA-sourced *Informe de Renta Fija* of 30-Sep-2026 (0.005 pp).
  T+1 settlement is confirmed by the same reconciliation. By owner decision of
  2026-10-26 the dollar-linked report also derives TEM and TNA under the R-004
  relationships, even though neither source publishes them for this family.
  This resolves Q3 only; it does **not** approve implementation, which remains
  blocked by Q5 (the peso-to-linked conversion rate, which does not match the
  BCRA A3500 of the closing date and is worth ~1.3 pp of annualized yield in the
  short end).

### Input controls and research boundaries

- R-002 retains `HPR = VPV / Market Price - 1`; the market-price definition,
  transaction-cost treatment and external market validation remain open.
- R-003 explicitly rejects the former simple 30/360 annualization and prohibits
  historical/current date mixing.
- R-009 records the forward formula family and keeps the use of a forward price
  as a futures proxy explicitly under review because daily settlement can make
  the prices differ.

## Governance Note

Validation of a mathematical relationship, a prototype convention or an
instrument methodology does not, by itself, authorize production implementation.
Under the project Research First Policy, production requires both a validated
research record and an explicit `Implementation Approved: Yes`.

On 2026-08-11 the project owner confirmed the official IAMC glossary as the
methodology source for R-003 and R-004. Current prices come from A3 rather than
the IAMC daily report, and the dashboard must suppress current yield metrics
when the selected price and market date are not aligned.
R-005 is approved only for the documented single-payment scope. R-009 remains
without production approval.

## Supporting Review

See `bibliography_review_2026-08-06.md` for the source-by-source audit and the
candidate research topics proposed for the future bond phase.

---

**Version:** 1.3

**Last Updated:** Monday, 26 October 2026
