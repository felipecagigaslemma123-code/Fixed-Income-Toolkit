# Research R-009 — Forward/Futures FX Relationship

| Field | Value |
|-------|-------|
| Research ID | R-009 |
| Topic | FX forward value and provisional futures proxy |
| Status | Under Review |
| Owner | Felipe Cagigas |
| Last Updated | Monday, 10 August 2026 |

---

# Current Decision

For exploratory analysis only, a currency futures price may be treated as the
corresponding forward price. The project will use the forward relationship as a
provisional futures proxy and will keep the result explicitly labeled "Under
Review".

No production formula is approved or implemented by this decision.

## Phase 1 owner decision — observed futures screen

On 10 August 2026 the project owner approved a first local dollar-futures
screen with the following deliberately narrower scope:

- list every observed standard and mini DLR maturity;
- show only contract reference data and recent trades supplied by the public A3
  price viewer;
- exclude spot from this phase;
- do not calculate forward points, implied devaluation, TNA, TEA, theoretical
  forward or any futures-versus-forward adjustment;
- show unavailable fields as missing rather than reconstructing them;
- label the public viewer source and the screen itself `Prototype` / `Observed`.

This is an approval to acquire, retain and display raw observations. It is
**not** approval of any formula in this research and does not change the
Research Gate below. The provisional source contract is recorded in
`docs/providers/a3_public_futures_viewer_contract.md`.

# Structure of this record

Per the project owner's decision of 6 August 2026, this research is organized
into the eight subsections below so that every open definition the Market Data
Module will *consume* (but not decide) is tracked in one place, avoiding
duplicated governance:

1. Spot contract
2. Futures price contract
3. Temporal policy
4. Curves and conventions
5. Observed metrics
6. Theoretical forward
7. Futures ≈ forward approximation
8. Research Gate

The Market Data Module consumes these definitions once approved; it does not
select the spot source, the curves or the price mapping on its own.

---

## 1. Spot contract

The spot observation must define, without ambiguity:

- which currency is in the numerator;
- which currency is in the denominator;
- which market the spot represents;
- the date and time of the observation.

For Argentine dollar futures the expected direction is:

```text
ARS per USD
```

This direction **must not be marked as validated** until it is confirmed against
the instrument contract and the provider API. The source cannot be decided
simply as "dólar spot": it could be an official reference, a tradable spot, a
financial exchange rate, or the exact underlying asset defined by the futures
contract. These alternatives are **not interchangeable**.

Decision: wait for the API documentation (Gastón's API), then record in this
research the exact field, the source and its semantics. Until then, `spot`
remains **without an approved provider**.

Status: Open.

## 2. Futures price contract

The provider may publish several prices for the same contract. The project keeps
**all** of them and does not choose one while discarding the rest:

- settlement / official adjustment (`ajuste`);
- last trade;
- bid;
- ask;
- volume;
- timestamp.

Each view later declares which price it uses (see the Market Data proposal,
`PriceType`). There must be **no silent substitution**: if `settlement` is
requested and not present, the response reports it as missing rather than
replacing it with `last`.

For the approved observed-only screen, the public viewer's trade `price` is
presented explicitly as **last observed trade**. It is not used as settlement,
bid, ask or another reference price. The broader open item remains for any
future calculated view or credentialed provider.

Status: Partially mapped for raw display; open for calculated use.

## 3. Temporal policy

For every observation the project stores:

- the provider's original timestamp;
- the original timezone;
- the timestamp normalized to UTC;
- the moment of reception;
- the market date;
- the age of the observation.

Spot and futures may be compared **only when they are temporally aligned**.
Mixing, for example, a closing spot with an intraday future requires an explicit
warning in the view.

The public viewer's recent-trade payload has been observed with ISO timestamps
ending in `Z`. The phase-1 prototype preserves that original string, records
`UTC`, stores a normalized UTC datetime and records the reception time. This
observation does not establish the timestamp contract of the future
credentialed Primary API.

Status: Policy defined; provisional viewer mapping recorded; credentialed API
still open.

## 4. Curves and conventions

The theoretical forward by parity (subsection 6) requires:

- a curve representing ARS funding;
- a curve representing USD funding;
- whether these are zero-coupon curves or single-tenor rates;
- the compounding convention;
- the day-count convention;
- the date and time of both curves.

No curve is selected without specific research. The project's Treasury-adapted
30/360 convention is validated for LECAP/BONCAP only and must not be generalized
to FX futures without confirmation.

Status: Open. No curve selected.

## 5. Observed metrics

The observed comparison does **not** require interest-rate curves:

```text
forward_points = futures_price - spot
```

This is trivial arithmetic on two observed prices and may be exposed as data,
subject to the temporal-alignment warning of subsection 3. It is not a market
convention and does not, by itself, open a Research Gate.

Status: Available as an observed comparison, with disclosure.

## 6. Theoretical forward

Hull gives covered interest parity for currencies, under continuous
compounding, as:

```text
F0 = S0 × exp((r_domestic - r_foreign) × T)
```

Equivalently, without fixing a compounding convention prematurely:

```text
F0 = S0 × domestic_accumulation_factor(T)
        / foreign_accumulation_factor(T)
```

### Additional evidence — A3 Academia

The reviewed A3 material independently gives, under discrete annual
capitalization:

```text
Asset without income:       F = S × (1 + R)^t
Asset with known income:    F = (S - I) × (1 + R)^t
Asset with known yield Q:   F = S × ((1 + R) / (1 + Q))^t
```

For a currency, the foreign interest rate plays the economic role of the known
yield on the foreign-currency asset. This is consistent with the generic
accumulation-factor ratio recorded above, subject to quote direction and rate
conventions.

A3 also distinguishes the forward delivery price from the value of an existing
long forward contract, shown under its assumptions as:

```text
long_forward_value = (current_forward_price - contracted_price)
                     / (1 + R)^t
```

> **Terminology separation (mandatory).** Per
> `bibliography_review_2026-08-06.md`, three concepts must not share one name or
> one function: (a) FX forward price — this research; (b) forward interest rate
> — a distinct topic, candidate R-017; (c) value of an existing forward — a
> distinct topic. They must not be implemented in a single generic
> `forward_rate` function.

Status: Formula family recorded; not approved. Requires subsections 1, 3 and 4
to be closed first.

## 7. Futures ≈ forward approximation

Hull explains that forward and futures prices are theoretically equal when
short-term risk-free rates are constant or a known function of time. With
unpredictable rates, daily settlement and the correlation between the underlying
and interest rates can create a difference. Taxes, transaction costs, margin,
counterparty risk and liquidity can also matter.

The A3 material likewise states that futures and forward prices can differ
because futures are settled daily and gains/losses are reinvested or financed at
changing interest rates; the sign of the difference depends on the correlation
between the underlying price and interest rates.

Therefore the futures-equals-forward treatment is kept as an **explicit
approximation**, not an identity. Any output derived under this approximation
must carry the "Under Review" disclosure.

Status: Approximation under review.

## 8. Research Gate

Validation Status:

⏳ Under Review

Implementation Approved:

No.

Blocking items before any production implementation:

- close subsection 1 (spot source, direction and semantics);
- close subsection 2 (provider price field);
- confirm subsection 3 (provider timezone and timestamp format);
- close subsection 4 (ARS and USD curves and their conventions);
- annualization to TNA/TEA additionally depends on R-002, R-003 and R-004;
- review the additional book/reference to be supplied by the project owner.

The phase-1 observed futures screen does not close or bypass any blocking item,
because it neither compares with spot nor runs a production financial formula.

---

# References

- Hull, J. C., *Options, Futures, and Other Derivatives*, 10th edition,
  Sections 5.8 and 5.10:
  `bibliography/Libros/AA John C. Hull-Options, Futures, and Other Derivatives-Pearson (2017).pdf`
- A3 Academia, `3.2-Forwards-y-futuros-financieros-2025.pdf`, pages 7–18.
- *Financial Modeling*, foreign-exchange and futures sections, PDF pages
  350–352.
- `docs/research/bibliography_review_2026-08-06.md`
- `docs/proposals/market_data_module_architecture.md`

---

**Version:** 1.4

**Last Updated:** Monday, 10 August 2026
