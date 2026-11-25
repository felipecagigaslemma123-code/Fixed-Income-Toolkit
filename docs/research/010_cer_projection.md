# Research R-010 — CER projection

# Objective

Transfer the existing Cartera implementation unchanged into the installable
Fixed Income Toolkit 0.2.0, with traceable approved methodology.

# Research Scope

Projection of CER and CER-indexed cash flows, using explicit initial CER,
contractual business-day lag and real cash flows per original VN 100. No ticker
inference; no automatic correction of disputed contractual inputs.

# Research Questions and Financial Interpretation

Published BCRA values take precedence, including future dates already published.
A missing date within the published range uses the last prior observation. After
the final observation, the interval from the 16th through the next 15th compounds
the IPC of the preceding reference month geometrically over actual calendar days:
`CER(t) = CER(15) * (1 + inflation_m) ** (elapsed_days / period_days)`.
If the last published day is not the 15th, continue the daily geometric rate of
the last two published observations to the next boundary, then chain months.

REM inflation: use explicit monthly medians first; fill missing months in the
next 12-month horizon with the constant monthly rate completing its cumulative
median. For months 13–24 use `(1 + ipc_24m)**(1/12) - 1`; continue that rate beyond.
Manual assumptions may replace estimates, never published values.

Payments are `real_cash_flow * CER(payment_reference) / initial_CER`.
The reference subtracts the contractual business-day lag using supplied holidays;
an absent holiday year retains the existing warning. A single zero-coupon
payment defaults to real principal 100; coupon instruments require explicit real
flows. IAMC is a control, never the CER calculation base.

# Methodology Validation and Limits

The 13 November verification found CER published through 15 December: 16 October
to 15 November accumulates **1.9 percent** (September IPC), 16 November to
15 December **2.2 percent** (October IPC). The 16 November review explains the
previously unresolved IAMC CER date: settlement minus the same contractual lag.
X29E7 and X30N6 match across the five saved closes; compare implied and published
CER within **0.0001** relative tolerance and retain the single latest warning.
TZXM7 remains a contractual discrepancy: IAMC initial CER **357.5665 (03 May
2024)** versus resolution **361.3176 (06 May 2024)**, a **1.05 percent** payment
difference. This approval does not settle that discrepancy or approve a value
for that instrument. The engine continues to warn and does not auto-correct it.

# Validation Matrix and Traceability

- Specification: this document and `docs/financial_specification.md` migration scope.
- Implementation: `financial_engine/indexed.py`, `indexed_payments.py`.
- Cases: `tests/test_indexed.py` (published CER, monthly chaining),
  `tests/test_indexed_payments.py` (initial-CER controls).
- Fixtures: `fixtures/bcra/`, `fixtures/iamc/cierres/2026-11-05.json`.

# Evidence Collected

The evidence is the verification recorded on **2026-11-13**, reviewed and corrected
on 2026-11-16 in Cartera, not a new online verification on 2026-11-25. Monetary
Statistics v4 series 30 (CER), 44 (private-bank TAMAR TNA) and 5 (A3500) were
compared with IAMC closes of 05–12 November: CER **865.4229 on 05 November**,
TAMAR **23.5625 percent on 04 November**, A3500 **1545.3974 on 05 November**.
Only public market observations and synthetic test fixtures are transferred;
no client holdings, purchases or files are included.

Estimates use the **median of the October 2026 REM**, sheet
`Cuadros de resultados`, preserved in `fixtures/bcra/rem-tablas-2026-10.xlsx`.
REM is a survey, not a realized value or contractual guarantee. Its October IPC
estimate was 1.8 percent against the subsequently published 2.2 percent.
The monthly FX survey describes the average over business days; using its 15th
as a curve point is the approved modelling convention, not a BCRA observation.

# Precision and Rounding

Preserve the original Decimal operations and 50-digit local contexts, their
order, dates and comparisons. No new intermediate rounding. The existing CER
warning alone quantizes displayed values to 0.0001; its tolerance stays 1 bp.
Origin values (`publicado`, `proyectado`, `manual`), warning and error text remain
unchanged, including the IAMC current-coupon fallback label.

# References

- Cartera `docs/PROYECCIONES.md` v1.3, 2026-11-16 (verification dated 2026-11-13).
- Cartera `docs/FUENTE_BCRA.md` (public API identity, transport and capture).
- Cartera `docs/REVISION_ETAPA11.md`, 2026-11-16 (subsequent corrections).
- BCRA Monetary Statistics: https://api.bcra.gob.ar/estadisticas/v4.0/monetarias
- REM: https://www.bcra.gob.ar/relevamiento-expectativas-mercado-rem/
- REM survey definitions:
  https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/consideraciones-relevamiento-expectativas-mercado.pdf

The three Cartera source documents are identifiable at source commit
`0cbf48e7d80d91717af9f0f02295d66c9baa51f4`, before their operational summaries
were shortened. This local migration has no network access and does not claim
that external sources were downloaded again. The existing public-data fixtures
allow offline regression; the 12 TAMAR payment notices are described in the
review but are not all archived as fixtures. Validation covers the approved
methodology and preserved evidence, not every instrument's contractual inputs.

# Current Implementation Decision

Validation Status: 🟢 Validated

Implementation Approved: Yes

Approval: **Felipe, 2026-11-25**, explicit instruction in ENCARGO.md to transfer
the already checked projections without changing any result. The approval is
limited to the documented cash-flow projections and requires explicit contract
inputs. **R-006 remains under review and Implementation Approved: No.**
This approval does not activate its LELINK secondary-market yield or FX total
return calculation, change its eligibility gate, or resolve its Q5.

# Research Status

Version: 1.0

Last Updated: 2026-11-25

Research ID: R-010
