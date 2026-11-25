# Research R-012 — A3500 projection for dollar-linked bond cash flows

# Objective

Transfer the existing Cartera implementation unchanged into the installable
Fixed Income Toolkit 0.2.0, with traceable approved methodology.

# Research Scope

ARS cash-flow projections for explicitly contracted A3500-linked bonds and the
FX leg of MIN/MAX duals, starting from IAMC schedules. No LELINK secondary-market
price conversion, yield methodology or FX total-return activation under R-006.
The compatibility route for indexed IAMC instruments is preserved unchanged.

# Research Questions and Financial Interpretation

A published reference takes priority; a missing date within the observed range
uses the latest prior published value. After the last observation, geometrically
interpolate to future REM monthly medians placed on the **15th**, ignoring points
on or before that observation. Add the 12-month median on the 15th of month +12;
extrapolate using the last geometric segment. These are estimates. Manual points
retain `manual` provenance, including interpolated segments touching them.

IAMC `f` is in initial `fxc` units. Recover the linked cash flow as
`linked_flow = f * fxc / A3500_IAMC` and project
`ARS_payment = linked_flow * A3500(payment_reference)`.
Use BCRA A3500 at the date in **macro.vars[k=a3500].f**, falling back to the
close date only if absent; do not substitute the close-date FX unconditionally.
The reference subtracts the contractual business-day lag and supplied holidays.
For an ordinary single redemption this is `100 * A3500(reference)`.
If an optional initial value differs from `fxc` by more than 0.0001, preserve
the warning. Dual FX leg is `mv_DL * A3500(reference) / A3500_IAMC`; multiply the
winning MIN/MAX leg by `fxc`.

# Methodology Validation and Limits

The verification dated 13 November gives A3500 **1545.3974 on 05 November**.
API gaps on 06, 09 and 10 November show why a calendar day cannot imply a new
observation: IAMC repeated the 05 November value. The source's initial claim that
all were business days is superseded by its later holiday review for 09–10.
IAMC TZV28 on 12 November: **110.967584 * 1394.9234 / 100 = 1547.9128**
at source precision, corresponding to **11 November**, not **1544.4320** on
12 November. The 16 November correction checks this macro-date relationship
across five saved closes; the wrong base caused approximately **0.2 percent**
errors. The public D30S6 pilot recorded **1523.9662 ARS/USD on 25 September**
and a three-business-day reference lag under its resolution; that observation
does not approve R-006 or settle its conversion-rate question.
The REM monthly FX value is a business-day average. The 15th is Felipe's
approved representation; it is not an exact realized daily forecast.

# Validation Matrix and Traceability

- Specification: this document and `docs/financial_specification.md` migration scope.
- Implementation: `financial_engine/indexed.py`, `indexed_payments.py`, `cash_flows.py`.
- Cases: `tests/test_indexed.py` (REM points, geometric interpolation, gaps),
  `tests/test_indexed_payments.py` (macro-date base).
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

Research ID: R-012
