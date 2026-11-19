# Research 006 — Dollar-Linked Treasury Letras (LELINK)

| Field | Value |
|-------|-------|
| Research ID | R-006 |
| Topic | Secondary-market yield of dollar-linked zero-coupon Treasury letras |
| Instrument Family | LELINK (Letra del Tesoro vinculada al dólar, cero cupón a descuento) |
| Status | **Under Review — Q3 resolved; Q5 delegated to the data provider; Implementation NOT approved** |
| Owner | Felipe Cagigas |
| Reviewer | Pending |
| Created | Thursday, 20 August 2026 |
| Last Updated | Monday, 26 October 2026 |

> **Correction (2026-08-20):** the official emission resolution establishes that
> LELINK are **zero-coupon, issued at a discount (`cero cupón (0) -a descuento-`),
> amortized in full at maturity (`íntegra al vencimiento`)**. They are **not
> capitalizable** and the redemption value in USD-linked units is **par (100)**.
> The intuition that the instrument "can be worth more than 100 at maturity" is
> correct only in **pesos**: the peso payoff is `VN × tipo de cambio aplicable`,
> which exceeds 100 because of the exchange rate, not because of any capitalization.

---

# Purpose and Governance Note

This document opens the Research Gate for **dollar-linked** Treasury letras. It is
a research artifact only. Under the project Research First Policy
(`CLAUDE.md`, `docs/ai_agent.md`), **no production financial formula may be
implemented for this instrument family** until this document reaches
`Validation Status: 🟢 Validated` and `Implementation Approved: Yes`.

The accompanying calculator and yield curve produced alongside this research are
**exploratory prototypes explicitly marked UNVALIDATED**. They live outside
`src/financial_engine/` and must not be treated as validated production output.
This mirrors the governance already applied to the R-009 futures/forward
prototype.

This research is opened **separately** from the LECAP/BONCAP research (R-001…R-005)
by owner instruction, to avoid mixing peso and dollar-linked methodologies.

---

# Objective

Validate the methodology used to compute the secondary-market return of
dollar-linked Treasury letras (LELINK) before any production implementation.

Two distinct return measures are in scope, at owner request, and must remain
explicitly separated:

1. **Yield in dollar-linked terms (TIR en dólares / "linked")** — the return
   measured in the USD-linked unit of account, independent of any future
   exchange-rate assumption.
2. **Total return in pesos** — the linked return combined with the variation of
   the official exchange rate (Com. "A" 3500) between settlement and maturity.
   This return depends on a **devaluation assumption** and therefore inherits the
   open governance of R-009 (FX forward / devaluation), which remains without
   production approval.

---

# Instrument Description (from official Treasury data)

Source: Secretaría de Finanzas, *Colocaciones de Títulos Públicos*, workbooks in
`data/` (`colocaciones_31-5-26.xlsx`, `colocaciones_30-06-26_a_publicar.xlsx`,
`colocaciones_31-12-2025_0.xlsx`), sheet `Letras`.

Observed contractual attributes of the LELINK family:

| Attribute | Observed value |
|-----------|----------------|
| Instrument name pattern | `LELINK/U$D/<dd-mm-aaaa>` |
| Coupon | `Cupón cero` |
| Amortization | `Íntegra al vencimiento` (bullet at maturity) |
| `Tipo Moneda` | `MONEDA NACIONAL` (settles in pesos) |
| `Moneda de Origen` | `USD` (denominated / linked to USD) |
| Issue price observed (`Precio de emisión`, /1000 basis) | ≈ 956–1000 → ≈ 95.6–100.0 per 100 |

## Official financial conditions (PRIMARY SOURCE — validated)

Source: **Resolución Conjunta SF/SH 31/2025** (RESFC-2025-31-APN-SH#MEC),
Boletín Oficial N° 35702, 08/07/2025 — full text at
https://www.argentina.gob.ar/normativa/nacional/norma-414934/texto
(emission of `LELINK vto. 31-10-2025`, representative of the family). Cross-checked
against the official licitación announcements and the colocaciones data above.

| Condition | Official term |
|-----------|---------------|
| Moneda de denominación | Dólares estadounidenses (USD) |
| Moneda de suscripción | Pesos, al A3500 del **día hábil previo a la fecha de licitación (T-1)** |
| Moneda de pago | Pesos, al **tipo de cambio aplicable** |
| **Tipo de cambio aplicable** | A3500 (BCRA Com. "A" 3500) del **tercer (3°) día hábil previo a la fecha de pago de la amortización** |
| Intereses | **Cero cupón (0), a descuento** |
| Amortización | **Íntegra al vencimiento**, al tipo de cambio aplicable |
| Denominación mínima | VNO USD 1 |
| Precio de licitación | En USD por cada VNO USD 1.000, dos decimales |
| Colocación | Res. Conjunta 9/2019 |
| Negociación | A3 Mercados S.A. y bolsas/mercados del país |
| Ley aplicable | Argentina |

Resolved reading (validated against the primary source):

- The letra is **denominated in USD** and **settled/paid in pesos**. The peso
  amount at maturity is `VN(USD-linked) × TC_aplicable`, where `TC_aplicable` is
  the A3500 of the **3rd business day before the maturity payment date**.
- It is **zero-coupon, issued at a discount**, redeemed **at par (100) in
  USD-linked units** at maturity. There is **no capitalization**; the redemption
  value parameter is fixed at `redemption_value_linked = 100`.

Note — canje/conversión mechanism (out of scope here): the default-delivery and
Decreto 846/24 art. 2 conversion settlement uses a distinct formula with a `× 1,20`
factor (`MONTO EFECTIVO = VNO × PRECIO / 1000 × 1,20 × TCR`). That factor belongs
to the conversion/penalty mechanism and **must not** be applied to the ordinary
secondary-market valuation or redemption.

## Instruments currently active (updated 2026-10-26)

Source: `data/colocaciones_30-09-26.xlsx`, sheet `Letras` (Secretaría de Finanzas,
retrieved 2026-10-26). Ticker is not carried by this dataset; the mapping below is
by family + currency + maturity date, per `contractual_colocaciones_source.md`.

| Ticker | Instrument | Issue date | Maturity | Issue price /1000 | Resolution | Issued (IAMC) |
|---|---|---|---|---|---|---|
| D30O6 | LELINK/U$D/30-10-2026 | 2026-08-14 | 2026-10-30 | 986.00 | 48/2026 (+52, 55) | 221M |
| D30N6 | LELINK/U$D/30-11-2026 | 2026-09-15 | 2026-11-30 | 985.20 | 55/2026 (+58) | 63M |
| D15E7 | LELINK/U$D/15-01-2027 | 2026-07-31 | 2027-01-15 | 975.70 | 46/2026 | 911M |
| D31M7 | LELINK/U$D/31-03-2027 | 2026-05-29 | 2027-03-31 | 956.11 | 28/2026 (+55) | 787M |
| D10Y7 | LELINK/U$D/10-05-2027 | 2026-07-17 | 2027-05-10 | 975.00 | 44/2026 | 604M |

Cross-check: the issued amounts reported by IAMC match the original tranche of each
placement in the colocaciones workbook, within rounding. Reopenings are recorded in
the workbook and do not alter the contractual terms.

**Minor discrepancy — D10Y7 issue date.** The colocaciones workbook records
2026-07-17; the IAMC report prints 16-Jul-26. One calendar day, most likely auction
date versus settlement/issue date. It does not affect the yield calculation, which
runs from settlement to maturity, but it must not be resolved silently if the
contractual registry ever keys on issue date.

Matured LELINK instruments (retained historically only): 31-10-2025, 28-11-2025,
16-1-2026, 30-01-2026, 27-02-2026, 30-04-2026, 31-07-2026, 31-08-2026, 30-09-2026.

---

# Candidate Methodology (to validate — NOT approved)

The following is the working hypothesis under review. It intentionally reuses the
LECAP/BONCAP IAMC math for the **linked leg** as a starting point, but this reuse
is **not** authorized until validated against official sources for this family.

## 1. Linked-terms yield

Let `P` be the secondary-market price in linked units (per VN 100) and `R` the
redemption value in linked units (per VN 100; default 100).

```text
HPR_linked = R / P - 1
D          = actual calendar days from settlement_date to maturity_date
TEA_linked = (1 + HPR_linked)^(365 / D) - 1
TEM_linked = (1 + TEA_linked)^(1 / 12) - 1
TNA_linked = TEM_linked * 12
```

This is the peso IAMC ACT/365 convention (R-002/R-003/R-004) applied to the
USD-linked cashflows. **Open question:** whether the official/market convention
for dollar-linked instruments uses ACT/365, 30/360 or ACT/360, and whether the
market quotes an effective annual TIR directly rather than `TNA = TEM * 12`.

## 2. Total return in pesos

Let `FX_s` be the official exchange rate applicable at settlement and `FX_m` the
official reference exchange rate at maturity (Com. "A" 3500). Define the
settlement-to-maturity official-FX variation `g = FX_m / FX_s - 1`.

```text
HPR_pesos = (1 + HPR_linked) * (FX_m / FX_s) - 1
          = (1 + HPR_linked) * (1 + g) - 1
```

`g` is **not** observable ex-ante; it is a user-supplied **devaluation
assumption**. The peso annualizations (TEA/TEM/TNA in pesos) would follow the
same ACT/365 structure applied to `HPR_pesos`. Because `g` is an assumption, the
peso column is a scenario, not a market-observed yield, and is subject to the
R-009 governance.

---

# Research Questions

1. **RESOLVED.** Conversion rule at maturity: peso payment = `VN × tipo de cambio
   aplicable`, where `tipo de cambio aplicable` = A3500 of the **3rd business day
   prior to the amortization payment date** (Res. Conjunta 31/2025).
2. **RESOLVED.** Redemption is **par (100)** in USD-linked units; zero-coupon at a
   discount, no capitalization (Res. Conjunta 31/2025).
3. **RESOLVED (2026-10-26).** The published dollar-linked secondary-market
   yield is an **effective annual rate on actual days over 365 (ACT/365)**,
   measured from **T+1 settlement** to maturity against a redemption value of
   **100** in linked units. Reconciled against two independent published
   reports on two different dates (see *Reconciliation* below): mean absolute
   error 0.003–0.005 pp across 10 instrument-observations. Neither report
   publishes TEM or TNA for this family; both publish only the effective annual
   yield (`YTM` / `TIR`) and Modified Duration.
4. **RESOLVED.** Price is quoted in **USD (linked) per VNO USD 1.000, two
   decimals** at issuance (Res. Conjunta 31/2025 + licitación announcements). The
   A3 secondary-market price basis must still be confirmed field-by-field.
5. **STILL OPEN — now the only blocker.** Subscription uses the A3500 of T-1
   before the auction. For a current secondary valuation, the screen price is
   published **in pesos**, so a conversion rate is required to express it in
   linked units. The reconciliation below shows the implied conversion rate is
   **not** the BCRA A3500 of the closing date: it exceeds it by +0.034% (BYMA,
   30-Sep-2026) and +0.203% (IAMC, 05-Oct-2026). The working hypothesis is the
   **wholesale closing spot** rather than the BCRA A3500 published for that day
   (whose calculation method changed under Com. "A" 8359, effective 2026). This
   must be confirmed before implementation: in the short end a 0.20% FX
   difference moves the annualized yield by ~1.3 pp.

---

# Reconciliation Against Published Market Reports (2026-10-26)

Two independent published reports were reconciled, on two different dates, using
the same method applied to R-003/R-004: the convention is identified as the one
that reproduces the published yields **with a single consistent FX** across all
instruments in the table.

Sources:

- **IAMC**, *Informe Diario Títulos Públicos*, close **05-Oct-2026**, section
  `LETRAS Y BONOS VINCULADOS AL USD — DOLLAR LINKED`
  (`examples/8461d895-3558-4320-a500-f7c5698fda3d.pdf`).
- **Informe de Renta Fija** (Robles Alvarez Jesús, en base a BYMA), close
  **30-Sep-2026**, section `Dollar Linked` (`examples/1790870714941.pdf`).
  Accepted by the owner as a reconciliation source on 2026-10-26; it is a
  third-party report, not an official publication.

## Step 1 — Convention discrimination

For each candidate convention the implied FX was solved from the published peso
price and published yield. The correct convention is the one yielding the same
FX for every instrument. Dispersion of the implied FX across the five letras:

| Convention | IAMC 05-Oct (T+1) | BYMA 30-Sep (T+1) |
|---|---|---|
| **ACT/365 effective** | **0.05 (0.003%)** | **0.04 (0.003%)** |
| 30/360 effective | 0.21 (0.014%) | 0.15 (0.010%) |
| ACT/360 effective | 0.27 (0.018%) | 0.28 (0.018%) |
| ACT/365 simple | 0.38 (0.025%) | 0.15 (0.010%) |
| 30/360 simple | 0.53 (0.035%) | 0.21 (0.014%) |

ACT/365 effective is 4x to 16x more consistent than any alternative.

## Step 2 — Settlement term

Mean absolute error against the published yields, by assumed settlement date:

| Settlement | IAMC 05-Oct | BYMA 30-Sep |
|---|---|---|
| T+0 | 0.123 pp | 0.034 pp |
| **T+1** | **0.003 pp** | **0.005 pp** |
| T+2 | 0.129 pp | 0.042 pp |

**T+1 is confirmed** for this family, consistent with the LECAP/BONCAP term and
resolving the pending note in `market_conventions.md`.

## Step 3 — Full rate set reproduced (IAMC, close 05-Oct-2026, settlement 06-Oct-2026)

Implied FX 1523.09. Linked price = peso close / FX, per VN 100. Redemption 100.

| Ticker | Maturity | Days | P (USD-linked) | HPR % | TEA % | TEM % | TNA % | MacD | MD | IAMC YTM / DM |
|---|---|---|---|---|---|---|---|---|---|---|
| D30O6 | 30-Oct-26 | 24 | 99.358 | 0.646 | 10.29 | 0.82 | 9.84 | 0.07 | 0.06 | 10.30% / 0.1 |
| D30N6 | 30-Nov-26 | 55 | 99.141 | 0.866 | 5.89 | 0.48 | 5.74 | 0.15 | 0.14 | 5.89% / 0.1 |
| D15E7 | 15-Jan-27 | 101 | 99.141 | 0.866 | 3.17 | 0.26 | 3.12 | 0.28 | 0.27 | 3.17% / 0.3 |
| D31M7 | 31-Mar-27 | 176 | 98.091 | 1.946 | 4.08 | 0.33 | 4.00 | 0.48 | 0.46 | 4.08% / 0.5 |
| D10Y7 | 10-May-27 | 216 | 98.485 | 1.539 | 2.61 | 0.22 | 2.58 | 0.59 | 0.58 | 2.61% / 0.6 |

Corroboration — BYMA, close 30-Sep-2026, settlement 01-Oct-2026, implied FX 1517.52:

| Ticker | Days | TEA % (engine) | TIR % (published) | MD (engine) | MD (published) |
|---|---|---|---|---|---|
| D30O6 | 29 | 2.46 | 2.45 | 0.08 | 0.08 |
| D30N6 | 60 | 3.70 | 3.69 | 0.16 | 0.16 |
| D15E7 | 106 | 1.59 | 1.59 | 0.29 | 0.29 |
| D31M7 | 181 | 3.02 | 3.02 | 0.48 | 0.48 |
| D10Y7 | 221 | 1.94 | 1.94 | 0.59 | 0.59 |

TEM and TNA are **not published** by either source for this family; they are
derived here under the R-004 relationships (`TEM = (1+TEA)^(1/12) - 1`,
`TNA = TEM x 12`) by owner decision of 2026-10-26, so the dollar-linked report
exposes the same rate set as the peso instruments. Modified Duration follows
R-005 (`MD = Macaulay / (1 + TEA)`) and reproduces the published DM exactly at
the published precision.

## Step 4 — FX cross-check against the BCRA (open item)

Official A3500 (BCRA, `estadisticascambiarias` API):

| Date | A3500 |
|---|---|
| 29-Sep-2026 | 1522.00 |
| 30-Sep-2026 | 1517.00 |
| 01-Oct-2026 | 1524.50 |
| 02-Oct-2026 | 1520.00 |
| 05-Oct-2026 | 1520.00 |
| 06-Oct-2026 | 1520.00 |
| 07-Oct-2026 | 1517.00 |

| Report | Implied FX (T+1) | A3500 of closing date | Difference |
|---|---|---|---|
| BYMA 30-Sep-2026 | 1517.52 | 1517.00 | +0.034% |
| IAMC 05-Oct-2026 | 1523.09 | 1520.00 | +0.203% |

Neither implied FX matches the A3500 of the closing date, the settlement date or
any adjacent publication. Using the BCRA A3500 of the closing date instead of the
implied rate raises the mean absolute error to 0.181 pp (BYMA) and 1.260 pp
(IAMC). **Consequence:** the yield convention is settled, but the peso-to-linked
conversion rule is not, and it is material in the short end. This is Q5 and it is
now the only item blocking the gate.

## Step 5 — Owner decision on Q5 (2026-10-26)

The owner resolved **not** to adopt a reconstructed conversion rate. Instead the
requirement is pushed to the data provider: the internal market-data API must
deliver the dollar-linked price **already expressed in USD-linked units per VN
100**, or, failing that, deliver the peso price **together with the exact
conversion rate used, its reference date/time, and its identity** (BCRA A3500 vs
wholesale closing spot).

Rationale: every alternative reconstructs a rate the project cannot source
authoritatively. A3 publishes `moneda` as a currency code and leaves the
**quotation unit undocumented** (`a3_provider_contract.md` §11), so converting
in the engine would embed an unvalidated assumption into a production path, in
breach of the Research First Policy.

Consequences while this is pending:

- Q5 stays open and the gate stays closed. R-006 cannot be implementation-approved.
- Any exploratory dollar-linked output must disclose the conversion rate it used
  and that the rate is **not** validated.
- Requirement recorded in `docs/providers/a3_provider_contract.md` §20 and in the
  internal-API delivery spec (`outputs/entrega_api_interna/`).

---

# Evidence Collected

| Source | Evidence | Status |
|--------|----------|--------|
| **Res. Conjunta SF/SH 31/2025** (BORA 35702) | Full financial conditions: zero-coupon a descuento, íntegra al vencimiento, `tipo de cambio aplicable` = A3500 3rd business day prior to maturity, subscription A3500 T-1, price in USD per VNO USD 1.000 | ✅ **Validated (primary source)** |
| Treasury colocaciones data (`data/*.xlsx`) | Contractual attributes of LELINK confirmed (cupón cero, íntegra al vencimiento, moneda nacional / origen USD, issue prices, tickers D‹ddmmy›) | ✅ Observed |
| Official licitación announcements (argentina.gob.ar) | Bid by price in USD per VNO USD 1.000, two decimals; family naming | ✅ Corroborated |
| **IAMC, Informe Diario Títulos Públicos, 05-Oct-2026** | Dollar-linked secondary-market yield reconciled: ACT/365 effective, T+1, redemption 100; MD per R-005 | ✅ **Validated (reconciled, 0.003 pp)** |
| **Informe de Renta Fija (Robles Alvarez / BYMA), 30-Sep-2026** | Independent corroboration on a second date (0.005 pp); owner-accepted source | ✅ Corroborated |
| **BCRA A3500 official series** | Published A3500 does **not** reproduce the implied conversion rate (+0.034% / +0.203%) | ⚠️ **Open (Q5)** |
| BYMA / A3 fixed income | A3 secondary-market price basis, field-by-field | ⏳ Pending review |
| BCRA Com. "A" 3500 | Official FX reference definition and publication timing | ✅ Referenced (definition confirmed) |

---

# Validation Cases

All five reconciled instruments now have a validation case recording the
05-Oct-2026 observation, with contractual data from `colocaciones_30-09-26.xlsx`:

| Case | Ticker | Engine TEA | Published YTM | Engine MD | Published DM |
|---|---|---|---|---|---|
| CASE-003 | D31M7 | 4.08% | 4.08% | 0.46 | 0.5 |
| CASE-004 | D30O6 | 10.30% | 10.30% | 0.06 | 0.1 |
| CASE-005 | D30N6 | 5.90% | 5.89% | 0.14 | 0.1 |
| CASE-006 | D15E7 | 3.17% | 3.17% | 0.27 | 0.3 |
| CASE-007 | D10Y7 | 2.61% | 2.61% | 0.58 | 0.6 |

Published DM is rounded to one decimal, which is why the short end looks coarse;
at the precision BYMA publishes (two decimals, 30-Sep-2026) the engine reproduces
it exactly. Every case carries the implied FX and flags it as unvalidated (Q5).
`LELINK/U$D/30-09-2026` has matured and is retained historically only.
A JSON validation case must follow the schema in
`examples/03_validation_cases/` and record: contractual data, the A3500 reference
rule, the price basis, and independently reproduced expected results.

---

# Current Implementation Decision

**Do not implement any production calculation for dollar-linked letras.**

Reasons (updated 2026-10-26):

- ~~No official convention documented for the dollar-linked yield.~~ **Resolved:
  ACT/365 effective, T+1, redemption 100 — reconciled against two sources.**
- The **peso-to-linked conversion rate (Q5) is not documented**, and the error it
  introduces reaches ~1.3 pp of annualized yield in the short end.
- The peso total return depends on a devaluation assumption governed by R-009,
  which has no production approval.
- Five validation cases now exist (`CASE-003` … `CASE-007`), one per reconciled
  instrument, all with contractual data from the official colocaciones workbook.

Exploratory prototypes may be produced for exploration only, clearly marked
UNVALIDATED and kept outside `src/financial_engine/`.

---

# Open Questions and Risks

- Reusing the peso IAMC ACT/365 convention for the linked leg is a **hypothesis**,
  not a validated fact for this family.
- The A3500 reference-date rule materially affects the peso payoff and is not yet
  documented.
- Mixing a linked price observation with a later valuation date must be blocked,
  exactly as in R-003 (no historical/current date mixing).
- The peso column must always disclose the devaluation assumption it used.

---

# Progress Summary (2026-08-20)

**Validated against the primary emission resolution (Res. Conjunta 31/2025):**

- LELINK structure: zero-coupon, issued at a discount, `íntegra al vencimiento`.
- Redemption at par (100) in USD-linked units; **no capitalization**.
- Maturity peso payoff = `VN × A3500(3rd business day before maturity)`.
- Subscription in pesos at A3500 of T-1 before the auction.
- Issue/secondary price quoted in USD (linked) per VNO USD 1.000.
- The `× 1,20` factor belongs to the conversion/default mechanism only — excluded
  from ordinary valuation.

**Resolved on 2026-10-26 (see Reconciliation section):**

- Q3: the secondary-market yield convention is **ACT/365 effective, T+1
  settlement, redemption 100**. The peso IAMC convention is no longer a
  hypothesis for the linked leg — it is reconciled against IAMC (05-Oct-2026)
  and BYMA (30-Sep-2026) within 0.003–0.005 pp.
- `CASE-003` (D31M7) produced and independently reproduced.

**Still blocking production approval:**

- Q5: the peso-to-linked **conversion rate** for current valuation is not
  documented and does not match the BCRA A3500 of the closing date. **Owner
  decision 2026-10-26: resolved by requiring the provider to deliver the price
  in USD-linked units (or the conversion rate explicitly). Pending provider
  response.**
- The peso total-return column depends on a devaluation assumption governed by
  R-009 (no production approval).
- ~~Contractual data for D30O6, D30N6, D15E7 and D10Y7 is not yet in the
  repository.~~ **Resolved 2026-10-26: `colocaciones_30-09-26.xlsx` incorporated;
  all five instruments have contractual data and a validation case.**

# Final Decision

Validation Status

🟡 Under Review — instrument structure and maturity FX-settlement rule validated
against the primary source (Res. Conjunta 31/2025); **secondary-market yield
convention (Q3) resolved and reconciled on 2026-10-26**; peso-to-linked
conversion rate for current valuation (Q5) still pending.

Implementation Approved

No

# References

- Resolución Conjunta SF/SH 31/2025 (RESFC-2025-31-APN-SH#MEC), Boletín Oficial
  N° 35702, 08/07/2025:
  https://www.argentina.gob.ar/normativa/nacional/norma-414934/texto
- Secretaría de Finanzas, llamados a licitación de LELINK (argentina.gob.ar).
- Secretaría de Finanzas, Colocaciones de Títulos Públicos (`data/colocaciones_*.xlsx`).
- BCRA, Tipo de Cambio de Referencia Comunicación "A" 3500.
- Reference peso convention: R-002 / R-003 / R-004 and
  `docs/research/iamc_yield_methodology_validation_2026-08-11.md`.

---

**Status:** Research in Progress — awaiting provider confirmation on Q5

**Priority:** High

**Version:** 0.5

**Last Updated:** Monday, 26 October 2026
