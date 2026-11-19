# Validation Cases

## Purpose

This directory contains the official validation cases used to verify the financial engine.

Each validation case represents a complete and reproducible scenario based on a real market instrument.

The objective is to ensure that every financial calculation implemented by the engine produces the expected result.

---

## Contents

Each validation case should include:

- Instrument identification
- Contractual instrument data
- Market data
- Expected financial outputs
- Data source
- Validation status

---

## Validation Policy

Validation cases are considered the reference for automated testing.

Every production calculation should be validated against one or more cases stored in this directory.

Whenever possible, expected results should be confirmed using:

- Argentine Treasury documentation
- IAMC methodology
- Reference Excel calculator
- Independent manual calculations

---

## Current Status

Version 1 will initially include validation cases for:

- LECAP
- BONCAP

Additional instruments may be incorporated in future versions.