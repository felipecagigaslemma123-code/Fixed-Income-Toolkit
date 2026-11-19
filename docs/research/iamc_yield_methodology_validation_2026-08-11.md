# IAMC Yield Methodology Validation - 11 August 2026

## Purpose

This record separates the stable yield methodology from the daily market-data
observation used by the Toolkit. IAMC is a methodology and independent
validation source; it is not the operational price feed. Current secondary-
market prices are obtained from A3 for the explicitly selected 24-hour
settlement term (`plazo` 001).

## Sources Reviewed

- IAMC, *Glosario de Indicadores y Metodologias de Renta Fija*, linked by the
  official report at
  `https://www.iamc.com.ar/Informe/GlosarioMetodologicodeRentaFija/`.
- BYMA/IAMC, *Informe Diario Titulos Publicos*, 10 August 2026:
  `examples/02_market_validation/703a03b1-6747-4055-8e88-339c66a04186.pdf`.
- R-001, R-002, R-003 and R-004.

## Approved Methodology

For LECAP/BONCAP, with a market price and maturity value expressed on the same
nominal basis:

```text
D   = actual calendar days from settlement to maturity   (ACT/365)
HPR = maturity_value / market_price - 1
TEA = (1 + HPR) ** (365 / D) - 1        # TIREA, effective annual
TEM = (1 + TEA) ** (1 / 12) - 1         # effective monthly
TNA = TEM * 12                          # nominal annual, monthly compounding
```

**Correction (2026-08-11).** An earlier version of this record used a 30/360,
360-basis simple annualization (`TNA = HPR * 360 / D30/360`) and explicitly
excluded `TNA = TEM * 12`. Empirical reconciliation against the published report
(below) showed that was wrong: IAMC uses **actual days**, an **ACT/365**
effective yield, and defines **TNA = TEM × 12**. The formulas above are the
corrected, approved methodology. The 30/360 convention remains correct **only**
for the maturity value (VPV, issue→maturity, R-001). The engine retains full
precision and rounds only for presentation.

### Empirical reconciliation — S16O6 (report of 10 August 2026)

Inputs: maturity value 105.28, close price 100.7 (rounded display), settlement
2026-08-11 (T+1), maturity 2026-10-16.

| Figure | IAMC published | Engine (ACT/365, TNA=TEM×12) |
|--------|----------------|------------------------------|
| Días   | 66 (actual)    | 66 (actual)                  |
| HPR    | 4.55%          | 4.55%                        |
| TNA    | 24.92%         | 24.85%                       |
| TEA    | 27.97%         | 27.89%                       |
| TEM    | 2.08%          | 2.07%                        |

The residual ~0.07–0.08 pp gap is explained by the rounded published price:
using 100.68 instead of the displayed 100.70 reproduces TNA 24.96% / TEA 28.03%
/ TEM 2.08%. The report prints **66 days**, confirming actual days (the 30/360
value would be 65).

### Multi-instrument reconciliation (same report, 5 cases)

Settlement 2026-08-11 (T+1). Actual days matched the report exactly in all five
cases. The corrected engine tracks the published IAMC TNA within price-rounding
tolerance across the curve, while the previous 30/360 simple formula drifts
**upward with maturity** (up to +2.6 pp on the 323-day T30J7):

| Ticker | Días | TNA IAMC | TNA engine (corrected) | TNA old (30/360 simple) | TEA IAMC | TEA engine |
|--------|------|----------|------------------------|-------------------------|----------|-----------|
| S16O6  | 66   | 24.92%   | 24.85% | 25.19% (+0.27) | 27.97% | 27.89% |
| S13N6  | 94   | 25.81%   | 25.70% | 26.48% (+0.67) | 29.09% | 28.95% |
| S30N6  | 111  | 25.60%   | 25.49% | 26.33% (+0.73) | 28.82% | 28.69% |
| T15E7  | 157  | 25.86%   | 25.71% | 27.04% (+1.18) | 29.16% | 28.97% |
| T30J7  | 323  | 24.65%   | **24.68%** | 27.24% (**+2.59**) | 27.63% | 27.68% |

Conclusion: ACT/365 + `TNA = TEM × 12` reproduces the official IAMC yields; the
30/360 simple annualization does not, and its error grows with the term. S16O6
and T30J7 are pinned as regression cases in `tests/test_letras_yield.py`.

## Explicitly Disapproved Use

The rate output obtained by pairing a historical embedded price with a later
purchase or calculation date is invalid and must not be used. In particular,
the S14G6 TNA near 258.44% was produced by combining the 17 July 2026 embedded
price with an August residual term. It is not an alternative TNA methodology
and it is not an approved result.

The following are prohibited in current-rate views:

- relabeling a historical price as current;
- calculating HPR, TNA, TEA or TEM when the price-observation date differs from
  the selected market/purchase date;
- silently replacing a missing current A3 price with an embedded IAMC price.

Note: `TNA = TEM * 12` is now the **approved** IAMC formula (nominal annual,
monthly compounding). The earlier prohibition of it was incorrect and has been
removed after the S16O6 empirical reconciliation.

When a current, explicitly selected A3 price is unavailable, the current yield
metrics must be reported as unavailable. The historical price may remain
visible only with its actual observation date.

## Daily Report Reconciliation

The 10 August 2026 report confirms the contractual data for the instruments and
provides an independent daily market observation. Its displayed TNA figures are
not used to override the glossary formula. The report contains rounded display
prices, and some displayed TNA values do not reproduce the glossary expression
from those rounded inputs. Per the source-priority rule and the owner's decision
of 11 August 2026, the official glossary formula prevails.

IAMC reports remain suitable for periodic validation, but the Toolkit does not
wait for the next daily report to calculate a current rate.

## S16O6 Evidence

The 10 August 2026 report records:

| Field | Value |
|---|---|
| Ticker | S16O6 |
| Instrument | LECAP |
| Issue date | 31 July 2026 |
| Maturity date | 16 October 2026 |
| Issue TEM | 2.05% |
| Published maturity value | 105.28 per VN 100 |
| Report close price | 100.7 per VN 100 |
| Report observation date | 10 August 2026 |

The report price is an explicitly dated embedded fallback and must not generate
a current rate for another date. A3 remains the operational current-price
source.

## Decision

- Methodology source: official IAMC glossary.
- Current price source: A3, 24-hour settlement, explicit last or close price.
- TNA formula: validated and approved.
- TEA formula: validated and approved.
- TEM formula: validated and approved; the glossary form is used in the engine.
- Historical/current date mixing: disapproved and blocked in the dashboard.

**Status:** Validated - Implementation Approved (owner, 2026-08-11)

**Version:** 1.0

**Last Updated:** Tuesday, 11 August 2026
