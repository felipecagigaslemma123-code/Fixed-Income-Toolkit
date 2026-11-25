# Research R-011 — TAMAR projection and coupon windows

# Objective

Transfer the existing Cartera implementation unchanged into the installable
Fixed Income Toolkit 0.2.0, with traceable approved methodology.

# Research Scope

Private-bank TAMAR TNA (BCRA id 44), TAMAR coupons, capitalizable TAMAR flows
and the TAMAR leg of explicitly contracted MIN/MAX duals. Other floating-rate
indices remain unsupported. Contractual margins, lags, floor and coupon bases
are inputs, never inferred from a ticker.

# Research Questions and Financial Interpretation

Use published TNA divided by 100 first. For future months use REM medians,
linear monthly interpolation to the month of its 12-month horizon, then keep the
last rate constant. Monthly manual assumptions override estimates only.

For a coupon, average business-day observations in **[start - lag, payment - lag)**:
include the start, exclude the end. Within the published segment count only dates
with BCRA observations: never carry a missing observation forward into the
average. After that segment use projected TAMAR on weekdays excluding supplied
holidays. Apply the margin, then the optional floor:
`interest = IAMC_coupon_base * max(mean_TAMAR + margin, floor)`.
The base `f[j][3]` already contains the instrument's day-count fraction.

For the current coupon, start at the last contractual prior payment supplied in
`_pagos_previos`. If unavailable, preserve `base * v.vig` and its original label
`definitivo · IAMC publicado`. This fallback is known to be unreliable and has
not been silently relabelled or corrected during migration.

For capitalizables retain
`TEM = (1 + (TAMAR + margin)*32/365)**(365/384) - 1`, and
`payment = mv * product(((1 + TEM_k)/(1 + tem))**e_k)` for `n - me` months,
with a final fractional month. Month k follows the settlement calendar month.
A constant implied TEM reproduces IAMC `mv`. Duals compare the TAMAR and A3500
legs under the supplied MIN/MAX rule, then multiply by `fxc`; preserve winner
and absolute difference.

# Methodology Validation and Limits

The 13 November check compared TAMAR **23.5625 percent on 04 November** with
IAMC and observed IAMC's constant-rate projection: BAF27 uses its coupon base
and `v.vig`. The 16 November review supersedes its earlier calendar-day average:
**12 of 12** BAM27/RVS1O paid coupons in 2025–2026 match notices (MAE/CNV) to
0.0001 with the business-day half-open window; the old method matched **0 of 12**
and deviated up to **0.19 per VN 100**. On 24 and 31 December 2025 BCRA published
no TAMAR. These absences must be respected. At 13 November IAMC's current-coupon
fallback gave **4.55 / 2.20** for BAM27/RVS1O versus **3.69 / 1.77** from the
contractual window. RVS1O's contractual floor is zero.
The source review's early 'known limits' paragraph is historical and is
superseded by its later corrections 8–9 and floor section. The engine already
contains those corrections; the migration adds none.

# Validation Matrix and Traceability

- Specification: this document and `docs/financial_specification.md` migration scope.
- Implementation: `financial_engine/indexed.py`, `indexed_payments.py`.
- Cases: `tests/test_indexed.py` (TNA, TEM, capitalizable reference),
  `tests/test_indexed_payments.py` (window, current coupon, fallback, floor).
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

Research ID: R-011
