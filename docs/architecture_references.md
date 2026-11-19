# Architecture References

## Purpose

This document records external software projects reviewed during the development of the Fixed Income Toolkit.

External repositories are used exclusively as architectural references.

They are not considered authoritative sources for financial formulas, market conventions, or business logic.

No external code may be copied into this project without an explicit review of:

- architecture;
- licence;
- market assumptions;
- implementation differences;
- compatibility with Argentine market conventions.

## Engineering Philosophy

The objective of reviewing external repositories is not to reuse financial formulas or market conventions.

Instead, they are used to evaluate proven engineering solutions for:

- project architecture;
- module organization;
- public API design;
- testing strategies;
- error handling;
- documentation standards;
- maintainability;
- scalability.

Whenever an external implementation provides a better architectural solution, the project should consider adopting the design while independently validating all financial logic.

## Evaluation Criteria

Each repository will be evaluated using the following criteria:

- Architecture
- Modularity
- Readability
- Documentation
- Testing
- Maintainability
- Scalability
- License compatibility
- Relevance for the Fixed Income Toolkit

Each criterion should be rated from 1 to 5.

---

# rateslib

Repository

https://github.com/attack68/rateslib

Primary Language

Python

Purpose

Professional interest-rate and fixed-income analytics library.

Evaluation Status

Pending.

---

## Architecture Review

Items to study:

- Project structure
- Package organization
- Instrument abstraction
- Pricing engine
- Calendars
- Day-count conventions
- Market conventions
- Testing strategy
- Documentation quality

---

## What We Can Learn

- Modular architecture
- Package organization
- Separation between products and pricing
- Convention management
- Public API design

---

## What We Should Not Reuse

- Market conventions
- Pricing formulas
- Day-count assumptions
- Interest-rate conventions

These must always be validated independently for the Argentine market.

---

## Licence

Source-available licence.

The repository may be studied for architecture, software design, testing strategy, and engineering practices.

Source code must not be copied into the Fixed Income Toolkit without verifying the licence terms and obtaining the appropriate permissions when required.

Use as architectural inspiration only.

---

## Review Status

Not started.

## bond_pricing_engine

Use only for:

- small Python project structure
- test organization
- separation of pricing methods
- error handling ideas

Restriction:

- New Zealand market conventions are not applicable by default.
- Any reused code must be reviewed and attributed under the MIT licence.

## DROP

Use only for:

- high-level modular architecture
- separation between products, market data, pricing, validation and numerical infrastructure

Restriction:

- Java implementation.
- Excessively broad for the MVP.
- Do not copy modules wholesale.

## Adoption Log

Repository:

rateslib

Decision:

Adopt modular separation between:

- instruments
- pricing
- calendars
- conventions

Reason:

Improves maintainability and aligns with the long-term architecture of the Fixed Income Toolkit.

Status:

Pending Review

---

# Adoption Criteria

An external design may be adopted if it improves one or more of the following:

- readability;
- maintainability;
- scalability;
- modularity;
- testability;
- documentation quality;
- API consistency.

Financial formulas, market conventions, pricing methodologies, settlement rules, and business logic must always be validated independently before adoption.

---

# Repository Review Workflow

Each reviewed repository should be analyzed according to the following process:

1. Understand the project purpose.
2. Review the overall architecture.
3. Review the package structure.
4. Review naming conventions.
5. Review testing strategy.
6. Review documentation quality.
7. Identify reusable engineering patterns.
8. Identify market-specific assumptions.
9. Decide which patterns should be adopted.
10. Document the decision.