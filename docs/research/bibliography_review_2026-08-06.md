# Bibliography Review — Fixed Income Formula Audit

**Review date:** Thursday, 6 August 2026  
**Scope:** LECAP/BONCAP maturity value, effective rates, bond yields, Duration,
forward rates, forward prices and futures prices.

## Sources Reviewed

### A3 Academia

- `Bonos-2025.pdf`, especially pages 8 and 16–19.
- `Tasas-de-interes-y-medidas-de-sensibilidad-2025.pdf`, especially pages 5 and
  10–19.
- `3.2-Forwards-y-futuros-financieros-2025.pdf`, pages 7–18.

### Financial Modeling

- `A3 mercados/Financial Modeling.pdf`, bond chapter on PDF pages 207–214 and
  foreign-exchange/futures discussion on PDF pages 350–352.
- Paul Pignataro, *Financial Modeling and Valuation*, reviewed for debt-maturity
  relevance. Its maturity material concerns corporate debt schedules and
  refinancing, not LECAP/BONCAP contractual VPV.

### Administración de Carteras

- Bodie, Kane and Marcus, *Investments*, 10th edition, previously reviewed for
  effective annual rates and Duration.
- Course material previously reviewed for total return, simple annualization and
  covered interest parity.
- DeFusco et al., *Quantitative Investment Analysis*, inventoried. The available
  PDF is image-based and did not provide reliable searchable text in this pass;
  no validation claim is based on it.

## Findings by Formula

| Topic | New Evidence | Decision |
|-------|--------------|----------|
| VPV / maturity value | A3 and Financial Modeling support a single final cash flow for zero-coupon/bullet structures | Contextual only; official Treasury formula remains controlling |
| HPR | No new market-specific definition | Keep selected formula; external market validation pending |
| TEM / TEA | A3 gives discrete and continuous compound future-value formulas | Compound equivalence reinforced; market application remains pending |
| TNA | No new evidence establishing the Argentine market label | Keep selected simple-period convention; do not promote |
| Macaulay Duration | A3 and Financial Modeling confirm present-value-weighted time; zero-coupon duration equals maturity | Validated for the single-payment prototype scope |
| Modified Duration | A3 and Financial Modeling give `D_mod = D_mac / (1 + YTM/n)` | Formula validated when periodic-yield frequency is explicit |
| FX forward price | A3 gives discrete carrying-cost formulas; Financial Modeling gives an interest-parity ratio | Formula family supported; quote direction, curves and provider fields remain open |
| Futures vs forward | A3 confirms possible differences caused by daily settlement and rate correlation | Forward-as-futures remains an explicit approximation under review |

## Terminology Separation Required

Three different concepts must not share one ambiguous name:

1. **FX forward price:** future exchange rate derived from spot and two currency
   accumulation factors.
2. **Forward interest rate:** future-period interest rate implied by today's zero
   curve.
3. **Value of an existing forward:** present value of the difference between the
   current delivery price and the contract's original delivery price.

These require separate input contracts and should not be implemented in one
generic `forward_rate` function.

## Candidate Research Items for the Bond Phase

The new material identifies formulas that are relevant to the next stage but are
not yet approved:

- R-011 — Bond pricing from discounted coupons and principal.
- R-012 — Yield to maturity / TIR and reinvestment assumption.
- R-013 — Dollar Duration and DV01.
- R-014 — Convexity and Modified Convexity.
- R-015 — Effective Duration for instruments with embedded options.
- R-016 — Key Rate Duration and non-parallel curve shifts.
- R-017 — Forward interest rates derived from zero rates.

These identifiers are proposed research records only. No production formula,
roadmap gate or implementation approval is created by this review.

## Conclusion

The new bibliography strengthens the existing compound-rate and Duration
decisions and provides direct support for keeping forward and futures distinct.
It does not replace the official Secretaría de Finanzas methodology for
LECAP/BONCAP VPV and does not justify promoting HPR, TNA or the market
application of TEM/TEA.

---

**Version:** 1.1

**Last Updated:** Thursday, 6 August 2026
