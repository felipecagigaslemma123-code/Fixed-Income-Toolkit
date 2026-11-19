# Financial Scope

This document defines the functional scope of the Fixed Income Toolkit.

It specifies which financial instruments are supported by the project and defines the scope of each development stage. Pricing formulas, implementation details, and market conventions are documented separately.

The toolkit is developed incrementally. Every financial instrument is implemented only after its market conventions, pricing methodology, and validation cases have been fully documented.

---

## Version 1 (Minimum Viable Product)

The first release focuses exclusively on Argentine Treasury Bills.

### Supported Instruments

#### Discount Treasury Bills

Supported calculations:

- Price calculation
- Purchase amount
- Face value
- Holding Period Return (HPR)
- Annualized Yield (TNA)
- Effective Annual Yield (TEA)
- Days to Maturity
- Profit and Loss

#### Capitalizable Treasury Bills (LECAP)

Supported calculations:

- Price calculation
- Maturity amount
- Holding Period Return (HPR)
- Annualized Yield (TNA)
- Effective Annual Yield (TEA)
- Profit and Loss

---

## Market Conventions

Version 1 follows the conventions used in the Argentine fixed income market.

All market conventions are documented in:

- docs/market_conventions.md

Detailed pricing formulas and calculation requirements are documented in:

- docs/financial_specification.md

Whenever an implementation decision is required, the documented market conventions prevail over implementation assumptions.

---

## Validation Policy

Every calculation implemented by the toolkit must be validated against at least one of the following sources:

- Official Treasury documentation
- IAMC Calculators
- BYMA market information
- Official market reports

No pricing model should be considered complete without successful validation.

---

## Planned Future Modules

The following instruments are planned for future releases:

### Fixed Income Instruments

- CER-linked Bonds
- Fixed-rate Bonds
- Floating-rate Bonds
- Dollar-linked Bonds
- Hard Currency Bonds
- Corporate Bonds (Obligaciones Negociables)

### Analytical Modules

- Yield Curve Analysis
- Duration and Convexity
- Portfolio Analytics
- Risk Metrics
- Performance Attribution

---

## Explicitly Excluded from Version 1

The following products are intentionally excluded from the first release:

- Derivatives
- Options
- Futures
- Swaps
- Structured Products
- Equities
- ETFs
- Mutual Funds

Research or exploratory display of an excluded metric does not move it into
Version 1. R-005 is approved and implemented only for the single final cash
flow of supported LECAP/BONCAP instruments; portfolio and coupon-bearing
multi-cash-flow duration remain future work. R-009 forward/futures work remains
a research artifact without production implementation approval.

---

## Design Principle

The primary objective of Version 1 is correctness rather than feature expansion.

Every new financial instrument must satisfy the following requirements before being added to the toolkit:

- Market conventions documented.
- Pricing methodology documented.
- Official validation examples available.
- Automated tests implemented.

Feature expansion must never compromise pricing accuracy.

---

**Status:** Active

**Version:** 1.3

**Last Updated:** Wednesday, 12 August 2026
