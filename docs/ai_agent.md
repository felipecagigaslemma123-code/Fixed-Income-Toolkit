# AI Agent Instructions

## Purpose

This document defines the rules that every AI coding agent must follow when working on the Fixed Income Toolkit project.

These instructions are model-agnostic and apply to every AI assistant, including (but not limited to):

- Claude Code
- Codex
- ChatGPT
- GitHub Copilot
- Future AI coding assistants

The objective is to guarantee consistency, correctness, maintainability and financial accuracy regardless of which AI generates the implementation.

---

# Project Overview

Fixed Income Toolkit is a professional fixed-income analytics platform initially focused on Argentine Treasury Bills (Letras).

The long-term objective is to build a modular financial analytics platform supporting multiple fixed-income instruments, portfolio analytics, reporting and market data integration.

Financial correctness is always more important than implementation speed.

## Current Project Status

Current phase:

Incremental Implementation and Validation

Approved production components are implemented independently behind their
research gates.

The financial engine architecture has been defined.

VPV methodology is validated in R-001. HPR is approved in R-002. R-003/R-004
validate the secondary-market yield convention reconciled against the official
IAMC report: residual time uses actual calendar days on a 365-day basis,
`TEA = (1 + HPR)^(365 / D) - 1`, `TEM = (1 + TEA)^(1 / 12) - 1`, and
`TNA = TEM * 12`. The Treasury-adapted 30/360 convention remains exclusive to
the contractual VPV calculation. Current-market use requires an explicitly
selected, date-aligned A3 T+1 price; historical/current date mixing is
prohibited.

Production implementation remains gated independently by each corresponding
research document; approval of one calculation does not open another gate.

Current objective:

Maintain validated LECAP/BONCAP calculations with current, traceable A3 market
inputs while researching each additional instrument or formula before
implementation.

---

# Source of Truth

The AI must always follow this priority:

1. Official market documentation.
2. Project documentation.
3. Academic references.
4. Existing implementation.
5. AI assumptions.

Documentation is always considered the source of truth.

If documentation and implementation disagree:

The documentation is assumed to be correct.

---

# Project Documentation

Before implementing any feature, the AI must read the documentation inside the docs folder.

Especially:

- project_vision.md
- roadmap.md
- financial_scope.md
- financial_specification.md
- market_conventions.md
- formulas.md
- validation_cases.md

Never implement financial logic without reading the corresponding documentation.

---

# Human Authority

The human developer has the final decision regarding business requirements, market conventions, and project architecture.

The AI remains responsible for identifying inconsistencies, implementation risks, missing validations, and potential defects.

If the AI detects a conflict between human instructions and documented requirements, it must explicitly report the conflict before implementation.

The AI must never:

- override business decisions
- replace financial conventions
- redefine formulas
- modify documented requirements

If ambiguity exists:

Stop.

Explain the ambiguity.

Request clarification.

Never guess.

---

# Development Workflow

Every new feature follows the same workflow:

1. Business requirement
2. Documentation
3. Architecture
4. Implementation
5. Testing
6. Validation
7. Review

Implementation must never come before documentation.

---

# Architecture Principles

Always keep the project modular.

Separate responsibilities:

- Financial Engine
- Market Data Engine
- Reporting Engine
- User Interface
- Configuration
- Utilities

Business logic must never depend on:

- the user interface
- data providers
- APIs
- Excel files

Financial calculations must be independent from data sources.

---

# Financial Principles

Financial correctness is the highest priority.

Every financial calculation must explicitly define:

- Inputs
- Outputs
- Assumptions
- Market conventions
- Units
- Rounding rules
- Validation rules

If multiple conventions exist:

Never choose one without documentation.

---

# Market Conventions

Never assume:

- day-count conventions
- capitalization
- settlement rules
- pricing conventions
- rounding methods
- holiday calendars

Always use documented conventions.

---

# Coding Standards

Write code that is:

Readable

Modular

Maintainable

Reusable

Prefer:

- pure functions
- descriptive variable names
- small functions
- explicit calculations

Avoid:

- duplicated logic
- hidden assumptions
- magic numbers
- unnecessary complexity

---

# Testing Rules

Every financial calculation requires tests.

Tests should include:

Normal cases

Boundary conditions

Invalid inputs

Known market examples

Regression tests

Whenever possible:

- Validate against official Treasury documentation.
- Validate against IAMC calculators.
- Validate against independently calculated reference cases.
- Document any discrepancies before implementation.

---

# Documentation Rules

Whenever business logic changes:

Update documentation first.

Then update implementation.

Documentation must never lag behind the code.

## Documentation Preservation

The AI must never remove research documents, financial specifications, market conventions, validation cases, or historical documentation unless explicitly instructed.

Whenever possible, preserve historical documentation and update it rather than deleting it.

Documentation is considered a long-term project asset.

---

# AI Collaboration

Multiple AI agents may work on this repository.

Every AI must:

respect previous documentation

respect architectural decisions

avoid unnecessary refactoring

avoid stylistic changes unrelated to the task

leave clear comments when uncertainty exists

This repository is designed for collaborative AI development.

---

# Communication Style

If a requirement is unclear:

Do not invent an answer.

Instead:

Explain the problem.

List possible interpretations.

Ask for clarification.

---

# Forbidden Actions

The AI must never:

Invent financial formulas.

Invent market conventions.

Replace documented logic.

Silently change outputs.

Modify validated calculations.

Ignore validation cases.

Optimize code at the expense of correctness.

Assume undocumented business rules.

---

# Decision Priority

When making decisions, always use this order:

1. Official market rules
2. Project documentation
3. Human instructions
4. Existing architecture
5. Implementation convenience

Implementation convenience is never a sufficient reason to change financial behavior.

---

# Project Philosophy

This project values:

Correctness over speed.

Transparency over cleverness.

Documentation over assumptions.

Financial rigor over implementation shortcuts.

Long-term maintainability over quick solutions.

The objective is not simply to build software.

The objective is to build a reliable financial analytics platform.

## Research-Driven Development

Every financial calculation must follow this sequence:

Research → Specification → Implementation → Testing → Validation

No production financial calculation may be implemented without:

- an approved research document;
- a financial specification;
- validation cases.

---

# Architecture References

These instructions apply to every AI coding agent working on this repository.

External repositories are reference material only.

Do not copy, import, or adapt external code unless explicitly instructed.

Do not transfer formulas, day-count conventions, settlement rules, or market assumptions from foreign markets into the Fixed Income Toolkit.

Any proposed reuse must include:

- source repository;
- exact file and function;
- licence;
- reason for reuse;
- differences from Argentine market requirements;
- approval before implementation.

---

# Code Review

Before considering a task complete, the AI must verify:

- Documentation is still consistent.
- Existing functionality is not affected.
- New code follows project architecture.
- Inputs are validated.
- Outputs are deterministic.
- Error handling is explicit.
- No duplicated business logic was introduced.
- Existing research documents are respected.

The AI should propose improvements when appropriate, but must not implement architectural changes without approval.

## Traceability

Every production financial calculation must be traceable to:

- one research document;
- one financial specification;
- one validation case;
- one implementation module;
- one or more automated tests.

The relationship between these artifacts should remain explicit throughout the project.

Financial behavior must always be explainable from the corresponding documentation.

---

# Optimization Policy

Never simplify or optimize financial calculations solely for shorter code.

Readability, auditability, and traceability are preferred over micro-optimizations.

Financial calculations should be explicit even when equivalent shorter expressions exist.
Financial calculations should prioritize:

1. Correctness
2. Transparency
3. Auditability
4. Reproducibility
5. Performance

Performance optimizations must never change documented financial behavior.

## Versioning

Whenever documentation changes:

- update the corresponding version number;
- update the Last Updated field;
- ensure references remain consistent across documents.

---

# Document Maintenance

This document defines the permanent governance rules of the project.

It should evolve only when a new development policy, architectural principle, or financial governance rule becomes necessary.

Routine implementation decisions should be documented elsewhere and must not increase the complexity of this document.

The objective is to keep this document concise, stable, and authoritative.
