# Secretaría de Finanzas — Auction Results Source Contract

| Field | Value |
|-------|-------|
| Document | Public-source data contract |
| Publisher | Secretaría de Finanzas, Ministerio de Economía |
| Source type | Public HTML pages (no stable API documented) |
| Status | 🟡 Live structure confirmed; changes must fail safely |
| Consumed by | `src/market_data/providers/treasury/` |
| Owner | Felipe Cagigas |
| Last Updated | Tuesday, 11 August 2026 |

> This contract governs acquisition and traceability only. It does not define
> or implement any financial formula, market convention, calculation approval
> or Research Gate.

## 1. Purpose

The Secretaría de Finanzas source is the authoritative public source used to
discover Treasury auction results and stage newly issued or reopened national
Treasury Letras and Bonos for the Toolkit. A staged instrument becomes
operationally active only after the A3 / MAE MarketData API exposes it in the
fixed-income segment.

The Toolkit remains a calculation engine. Source acquisition, operational
activation and financial calculation are separate responsibilities.

## 2. Official pages

- Landing page: `https://www.argentina.gob.ar/economia/licitaciones`
- Finance news listing: `https://www.argentina.gob.ar/economia/finanzas/noticias`
- Historical results: `https://www.argentina.gob.ar/economia/finanzas/licitaciones-de-letras-y-bonos-del-tesoro/historico-de-resultados`
- Annual debt placements: `https://www.argentina.gob.ar/economia/finanzas/deudapublica/colocacionesdedeuda`

The finance news listing currently publishes separate entries for calls and
results. Result articles contain HTML tables whose exact columns vary by
instrument family and auction.

## 3. Information preserved from result articles

For every national-Treasury instrument row, the normalizer preserves:

- full published instrument description;
- published ticker, when present;
- issue classification stated as `nueva` or `reapertura`, when present;
- maturity date when it is explicit in the description;
- auction/result publication date;
- source page title and URL;
- every table header and raw cell value, in source order;
- normalized decimal representations only when a source cell contains one
  unambiguous localized number.

The raw value is always retained. Normalization never replaces it and never
applies a financial formula. A percentage sign, currency marker, nominal basis
or footnote remains part of the raw source evidence.

### Universe boundary approved 11 August 2026

- Discovery includes rows explicitly identifying a `LETRA DEL TESORO NACIONAL`
  or `BONO DEL TESORO NACIONAL`.
- Provincial, municipal, corporate and other non-national issuers are excluded.
- Discovery coverage is broader than calculation coverage. An instrument may
  be visible in the national-Treasury universe without being eligible for the
  LECAP/BONCAP calculator.
- The LECAP/BONCAP formula is applied only when the instrument family is
  compatible and all required contractual inputs already have supported source
  evidence. Missing issue date, contractual rate or other inputs remain
  explicit; they are never inferred from auction or market dates.

## 4. Known source limitation

The Secretaría may publish a new instrument as `(nueva)` without publishing its
ticker in the result table. The 29 July 2026 result is an observed example: the
LECAP maturing 16 October 2026 was published without a ticker.

The Toolkit must never derive or invent a ticker from the maturity date.

## 5. Approved identity-matching hierarchy

Approved by Felipe Cagigas on 10 August 2026:

1. When the Secretaría publishes a ticker, require an exact normalized ticker
   match against an A3 fixed-income quote.
2. When no ticker is published, match only if exactly one A3 fixed-income
   instrument has the same explicitly observed instrument family, currency and
   maturity date.
3. Zero matches remain pending.
4. More than one match is ambiguous and remains pending.
5. Manual input remains available as a fallback and must retain explicit manual
   provenance.

Matching is case-insensitive for identifiers and whitespace-insensitive for
text normalization. It does not infer tickers or contractual terms.

## 6. Operational lifecycle

Allowed operational states:

- `PENDING_SECONDARY_MARKET`: an official ticker exists but A3 has not exposed
  it yet.
- `PENDING_MATCH`: the official result has no ticker and no unique safe A3
  identity match is available.
- `ACTIVE_FOR_ANALYSIS`: A3 exposes the ticker, or the approved unique fallback
  match succeeds.
- `MATURED`: the instrument has passed its explicit maturity date.

`ACTIVE_FOR_ANALYSIS` is sticky: a later partial or empty provider response does
not silently deactivate an instrument. Maturity is the only automatic terminal
transition in this contract.

The dashboard also applies the same boundary independently to its historical
embedded dataset: an instrument whose explicit maturity date is on or before
the current local date is hidden from current selectors, comparisons and
charts. Its historical source record is retained; hiding it is not deletion.

## 7. Meaning of A3 visibility

The presence of a row in the A3 fixed-income response is sufficient evidence of
secondary-market visibility. A non-zero price, rate or volume is not required.
This rule follows the owner's explicit definition of the activation event.

The activation evidence records the A3 ticker, market date, provider and
retrieval timestamp.

## 8. Validation separation

Operational activation does not:

- validate contractual data;
- validate a maturity value;
- validate a provider quotation basis;
- validate a financial formula;
- open or close a Research Gate.

These statuses must remain independent in any future dashboard or API response.

## 9. Failure policy

- An unrecognized table structure must return no normalized candidates and
  surface a normalization error; it must not guess column meanings.
- Missing ticker, maturity, family or currency prevents fallback matching.
- A partial A3 response cannot deactivate an already active instrument.
- Source URLs and raw table values must be retained for audit.
- Network access is isolated behind injectable transports so tests remain
  deterministic and offline.

## 10. Approved scheduling policy

Approved by Felipe Cagigas on 10 August 2026:

- Secretaría de Finanzas result discovery: every 24 hours.
- A3 / MAE fixed-income refresh: every 15 minutes.
- Both jobs run immediately when the scheduler starts, then follow their own
  independent interval.

Rationale: Treasury auctions are periodic and do not require intraday polling,
while A3 publishes changing secondary-market observations and also supplies the
operational activation evidence.

Each A3 refresh persists the current normalized quote. Repeated observations
for the same ticker, settlement term, market date and provider update that
day's current record; observations from different market dates accumulate as
daily history. This policy does not claim tick-by-tick intraday history.

The provider itself remains scheduler-agnostic. A separate orchestration service
owns timing, so source acquisition stays independent from financial calculation.
Retention remains unchanged: stored source evidence and lifecycle history are
not deleted automatically.

## 11. UAT lifecycle smoke evidence — 10 August 2026

A read-only integration run checked the two most recent official result
articles and the A3 UAT fixed-income endpoint. It:

- extracted three Treasury Bill candidates from the official HTML;
- preserved two candidates without a published ticker as `PENDING_MATCH`;
- preserved D30S6 as `PENDING_SECONDARY_MARKET` because it was not present in
  the UAT fixed-income response;
- activated no instrument without matching evidence;
- persisted five A3 UAT fixed-income quote rows in the temporary database during
  the post-scheduler verification run;
- wrote only to a temporary SQLite database;
- did not query A3 production and did not execute a financial formula.

---

**Version:** 1.3

**Last Updated:** Tuesday, 11 August 2026
