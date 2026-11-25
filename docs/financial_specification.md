# Financial Specification

## Contents

1. Scope
2. General Principles
3. Discount Treasury Bills
4. Financial Engine Implementation Rules
5. Versioning

## Scope

This document defines the financial calculations implemented by the Fixed Income Toolkit.

It specifies:

- required inputs;
- expected outputs;
- validation rules;
- implementation constraints;
- production requirements.

This document is the authoritative functional specification for the financial engine.

## General Principles

The Financial Engine shall prioritize:

- correctness over performance;
- readability over cleverness;
- determinism over convenience;
- explicit behavior over implicit assumptions;
- reproducibility over automation.

Whenever a conflict exists between performance and financial correctness, financial correctness shall prevail.

---

# Discount Treasury Bills

## Inputs

- Purchase Price
- Settlement Date
- Maturity Date
- Face Value

## Outputs

- Holding Period Return
- TNA
- TEA
- Profit
- Maturity Value

## Validation Rules

The following conditions must be satisfied before any calculation is performed.

### Dates

- Settlement Date must be earlier than Maturity Date.

### Financial Values

- Monthly Issue Rate >= 0
- Maturity Date > Issue Date
- Settlement Date <= Maturity Date
- Reference Face Value > 0

## Numerical Accuracy

Intermediate calculations must preserve the highest available precision.

Rounding shall occur only when explicitly required by:

- official methodology;
- market convention;
- reporting requirements.

Internal calculations must not round intermediate values for presentation purposes.

## Traceability

Every production calculation must be traceable to:

- the corresponding research document;
- the financial specification;
- at least one validation case;
- the official market convention.

Every implemented methodology must be reproducible from the documented sources.

---

# LECAP / BONCAP Maturity Value

Research reference:

- R-001 — Methodology validated; production implementation approval pending.

## Inputs

- Instrument type: LECAP or BONCAP.
- Issue date.
- Maturity date.
- Effective monthly issue rate as `Decimal`.
- Reference face value as `Decimal`.

## Day Count

Use the Treasury-adapted 30/360 project convention specified in
`docs/market_conventions.md`. It preserves the observed U.S./NASD-style day-31
rules and additionally treats the last day of February as conventional day 30,
both at the start and at the end of the interval.

## Formula

```text
capitalization_months = DAYS360_TREASURY(issue_date, maturity_date) / 30
maturity_value = reference_face_value
                 × (1 + monthly_issue_rate) ^ capitalization_months
```

## Precision and Rounding

- Do not round intermediate values.
- Return the calculated value at the engine's documented Decimal precision.
- Keep a source-published maturity value separate from the recalculated value.
- Presentation rounding must not feed back into financial calculations.

## Validation

- Issue date must precede maturity date.
- Monthly issue rate must be non-negative.
- Reference face value must be positive.
- Regression cases must include ordinary dates and non-leap/leap February
  month-end boundaries.

---

# LECAP / BONCAP Secondary-Market Yields

Research references:

- R-002 - Holding Period Return.
- R-003 - Nominal Annual Rate.
- R-004 - TEM/TEA compound equivalence.
- `docs/research/iamc_yield_methodology_validation_2026-08-11.md`.

Methodology status:

- Validated against the official IAMC fixed-income methodology glossary.
- Implementation approved by the project owner on 11 August 2026.

## Inputs

- A3 secondary-market price for `plazo` 001, explicitly selected as last or
  close.
- Provider market date and settlement date associated with that price.
- Maturity date.
- Maturity value on the same nominal basis as the price.

## Formulas

```text
HPR = maturity_value / market_price - 1
D = actual calendar days from settlement_date to maturity_date
TEA = (1 + HPR)^(365 / D) - 1
TEM = (1 + TEA)^(1 / 12) - 1
TNA = TEM * 12
```

This ACT/365 convention applies to residual secondary-market yields. It is
deliberately distinct from the Treasury-adapted 30/360 convention used to
calculate contractual maturity value (VPV) from issue date to maturity date.

## Temporal Validation

- `market_price`, provider market date and settlement date must describe the
  same provider observation.
- A current-rate consumer must require the provider market date to equal its
  selected purchase/market date.
- A historical embedded price must never be silently combined with a later
  date to produce a current HPR, TNA, TEA or TEM.
- When no aligned current price exists, current yield metrics must be
  unavailable rather than calculated from a fallback.

The historical S14G6 output near 258.44% is explicitly rejected because its
price and calculation dates were not aligned.

## Precision and Rounding

- Use `Decimal` for all financial values in the production engine.
- Do not round intermediate values.
- Presentation rounding must not feed back into any formula.

---

# Shared Index and Cash-flow Migration (0.2.0)

Specification references: R-010, R-011 and R-012. This approved code movement
preserves the complete former Cartera contract: positional/keyword signatures,
Spanish data fields and schema keys, mutable schedule objects, Decimal
operation order and precision, dates, manual assumptions, origin labels,
warning/error messages, tolerances and the ACT/365 solver's interval/termination.
It is an explicit migration exception to the single immutable input/result and
single primary function patterns below. Adopting that pattern here would change
the existing consumer contract and is outside Felipe's instruction.

`financial_engine/indexed.py` contains pure curve calculations;
`indexed_payments.py` pure contractual payment projection;
`cash_flows.py` schedule parsing/merging and purchase yield;
`indexed_types.py` shared data objects; `_common.py` shared validation/precision.
`market_data/providers/bcra.py` owns transport, persistence and REM Excel reading,
and reexports `RemSurvey`/`BCRAError` from the pure shared types to avoid an
engine dependency on a network or spreadsheet provider. No formulas are added.
For fixed-rate schedules, purchase yield preserves the prior solver:
`sum(total / (1+r)**((payment_date-settlement).days/365)) - price = 0`,
`[-0.99, 10]`, 180 bisections, residual tolerance `1e-10`, precision 50 and `None`
for the existing invalid/unbracketed cases. Schedule gaps/manual reconciliation
and every warning are unchanged. The original tests and expected values are
transferred, with pure fixture setup separated from Cartera's file management.
Details and API mapping: [migration_0_2_0.md](migration_0_2_0.md).

R-006 remains unapproved; this scope does not resolve its Q5, change its status
or activate its LELINK yield/FX-return methodology.

---

# Financial Engine Implementation Rules

These rules apply to every module inside:

```text
src/financial_engine/
```

## Public Function Pattern

Every calculation module exposes exactly one primary public function.

Examples:

```text
calculate_maturity_value()
calculate_holding_period_return()
calculate_tna()
calculate_tea()
```

Each function must:

- receive exactly one immutable input object;
- return exactly one immutable result object;
- use complete type hints;
- remain independent from Excel, APIs, databases and user interfaces.

---

## Input Objects

Each calculation defines its own immutable input dataclass.

Examples:

```text
MaturityValueInput
HoldingPeriodReturnInput
TNAInput
TEAInput
```

Requirements:

- `@dataclass(frozen=True)`
- only the required fields
- `Decimal` for every financial value
- `date` for dates
- immutable after creation

---

## Result Objects

Each calculation returns its own immutable result dataclass.

Examples:

```text
MaturityValueResult
HoldingPeriodReturnResult
TNAResult
TEAResult
```

Requirements:

- `@dataclass(frozen=True)`
- raw financial values only
- no formatting
- `Decimal` for every monetary result

---

## Decimal Policy

Financial calculations must always use:

```python
Decimal
```

The engine must never use:

- float
- binary floating-point arithmetic

Correct:

```python
Decimal("100")
Decimal("0.025")
```

Incorrect:

```python
100.0
Decimal(0.025)
```

---

## Enum Policy

Closed domain values must use enums.

Examples:

- InstrumentType
- QuoteType
- SettlementConvention
- MethodologyStatus

---

## Exception Policy

Every module defines:

- one base exception;
- specific domain exceptions.

Examples:

```text
MaturityValueError
InvalidIssueRateError
InvalidFaceValueError
InvalidInstrumentDatesError
UnvalidatedMethodologyError
```

Generic exceptions should not be exposed when a domain exception is available.

---

## Validation Order

Every calculation follows the same sequence.

1. Validate required fields.
2. Validate types.
3. Validate financial values.
4. Validate dates.
5. Validate methodology approval.
6. Execute the calculation.
7. Return an immutable result.

---

## Research Gate

A production formula may only be implemented after:

- research approved;
- market convention documented;
- rounding rules documented;
- at least one validation case completed.

Until then, the public function must raise:

```text
UnvalidatedMethodologyError
```

---

## Module Independence

Financial modules must never:

- read Excel files;
- call APIs;
- write files;
- access databases;
- print results;
- depend on UI components.

---

## Naming Rules

Prefer explicit names.

Examples:

```text
holding_period_return
reference_face_value
monthly_issue_rate
maturity_value
```

Avoid ambiguous abbreviations whenever possible.

---

## Testing Contract

Every calculation module must eventually include tests for:

- valid case;
- at least two independent production instruments;
- boundary case;
- every domain exception;
- Decimal precision;
- regression against validation cases.

---

## Dependency Direction

```text
Market Data
      ↓
Orchestration
      ↓
Financial Engine
      ↓
Immutable Results
```

The financial engine must never depend directly on data providers or presentation layers.

## Versioning

This document is the authoritative specification for Version 1 of the Financial Engine.

Any change affecting:

- formulas;
- financial conventions;
- rounding;
- validation rules;
- public interfaces;

must be reflected in this specification before implementation.

## Out of Scope

Version 1 of the Financial Engine does not include:

- portfolio optimization;
- risk metrics;
- duration;
- convexity;
- derivatives pricing;
- curve construction;
- stochastic models;
- API integrations;
- database persistence;
- graphical interfaces.

## Supported Instruments

Version 1 supports:

- LECAP
- BONCAP

Future versions may incorporate:

- BONCER
- Dollar Linked
- Dual Bonds
- CER Instruments
- Corporate Bonds

## Design Philosophy

The Financial Engine is designed to maximize:

- correctness;
- reproducibility;
- auditability;
- maintainability.

Performance optimizations shall never compromise financial correctness.

---

**Version:** 1.4

**Last Updated:** 2026-11-25
