# Contractual Source — Treasury Colocaciones (authoritative maturities)

| Field | Value |
|-------|-------|
| Document | Contractual data source (authoritative) |
| Source | Official Treasury issuance datasets `data/colocaciones_*.xlsx` |
| Consumed by | `src/market_data/contractual/` |
| Purpose | Authoritative instrument maturities for letras desenlace |
| Owner | Felipe Cagigas |
| Last Updated | 10 August 2026 |

## Why

Instrument desenlace (maturity) must not depend on scraping free text. The
official Colocaciones workbooks are contractual data: the `Letras` sheet lists
each issued bill with an authoritative `Vencimiento` (maturity) column. This is
the reliable source of maturity, per the project rule to distinguish contractual
data from market data.

## What is loaded

From the `Letras` sheet, per instrument:

- `name` — contractual instrument name, e.g. `LECAP/$/27-02-2026` (encodes family
  and maturity in the wording);
- `family` — inferred from explicit wording (LECAP / LECER / LELINK / LEDE);
- `currency` — `ARS` or `USD`, inferred from the name;
- `issue_date` — from `Fecha de emisión`;
- `maturity_date` — from the authoritative `Vencimiento` column;
- `resolution` — auction resolution reference.

The registry (`ContractualMaturityRegistry`) deduplicates by name (reopenings)
and reports any inconsistent maturities via `conflicts()` instead of resolving
them silently. Verified on `colocaciones_31-5-26.xlsx`: 23 distinct instruments,
zero conflicts.

## Important scope note — no ticker in this dataset

The Colocaciones dataset provides an authoritative **name → maturity** mapping.
It does **not** carry the A3 secondary-market ticker (e.g. `S30S6`), so it is not
a direct `ticker → maturity` map. The project deliberately does **not** decode
the maturity from a ticker.

The bridge is `resolve_maturity()`:

1. use an explicit maturity already parsed from the source (`EXPLICIT`);
2. else, an unambiguous match against this registry by family + currency + a
   date/name token found in the description (`CONTRACTUAL_UNIQUE`);
3. else `UNRESOLVED` — the caller must surface the instrument as
   maturity-unknown rather than leaving it silently active.

## Recommended integration (next step)

Wire `resolve_maturity()` into the Treasury result candidate flow so a candidate
whose maturity could not be parsed from prose is enriched from this authoritative
registry, and mark `UNRESOLVED` candidates visibly (they must not become
active-for-analysis indefinitely). For an exact `ticker → maturity` map, the
authoritative pairing of ticker and maturity lives in the Treasury result
articles (ticker in the description, maturity in the result table's Vencimiento
column) or an official instrument reference list (BYMA/IAMC); this registry
cross-validates those.

---

**Version:** 1.0

**Last Updated:** 10 August 2026
