#!/usr/bin/env python3
"""Inspect an existing Excel calculator without modifying the source workbook.

This is a read-only development utility. It opens a workbook twice with
``openpyxl`` -- once to read formulas (``data_only=False``) and once to read the
values Excel last cached for those formulas (``data_only=True``) -- then walks
every worksheet and every non-empty cell to build a full inventory.

Two artefacts are produced under ``outputs/``:

* ``excel_workbook_inventory.json`` -- workbook-level metadata, per-worksheet
  metadata and defined (named) ranges.
* ``excel_cells_inventory.csv`` -- one row per non-empty cell.

The utility never writes to, or otherwise mutates, the source workbook, and it
deliberately implements no financial formulas or market conventions -- it only
reports what is already stored in the file.

Usage::

    python tools/inspect_excel.py path/to/workbook.xlsx
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import openpyxl
    from openpyxl.workbook.workbook import Workbook
    from openpyxl.worksheet.worksheet import Worksheet
except ImportError as exc:  # pragma: no cover - dependency guard
    sys.exit(
        "Missing dependency 'openpyxl'. Install it with:\n"
        "    pip install openpyxl\n"
        f"(original import error: {exc})"
    )


# Column order used for the flat per-cell CSV export.
CELL_CSV_FIELDS: List[str] = [
    "worksheet",
    "coordinate",
    "row",
    "column",
    "column_letter",
    "raw_value",
    "formula",
    "cached_value",
    "number_format",
    "data_type",
]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Inspect an Excel calculator (read-only) and export an inventory.",
    )
    parser.add_argument(
        "workbook",
        type=Path,
        help="Path to the .xlsx/.xlsm workbook to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for the generated inventory files (default: ./outputs).",
    )
    return parser.parse_args(argv)


def load_workbooks(path: Path) -> tuple[Workbook, Workbook]:
    """Load the workbook twice: formulas view and cached-values view.

    The workbook is opened read-only in intent (openpyxl never writes back
    unless ``save`` is called, which this tool never does).
    """
    # data_only=False keeps formula strings intact.
    formula_wb = openpyxl.load_workbook(path, data_only=False, keep_vba=False)
    # data_only=True exposes the values Excel cached the last time it calculated.
    value_wb = openpyxl.load_workbook(path, data_only=True, keep_vba=False)
    return formula_wb, value_wb


def _extract_defined_names(workbook: Workbook) -> List[Dict[str, Any]]:
    """Return workbook-level named ranges, tolerating openpyxl version differences."""
    named_ranges: List[Dict[str, Any]] = []
    defined_names = getattr(workbook, "defined_names", None)
    if not defined_names:
        return named_ranges

    # openpyxl >= 3.1 exposes a dict-like mapping; older versions are iterable.
    try:
        items = defined_names.items()  # type: ignore[union-attr]
    except AttributeError:  # pragma: no cover - legacy openpyxl
        items = [(dn.name, dn) for dn in defined_names]  # type: ignore[attr-defined]

    for name, defn in items:
        named_ranges.append(
            {
                "name": name,
                "value": getattr(defn, "value", None),
                "is_absolute": bool(getattr(defn, "absolute_ref", False)) or None,
                "comment": getattr(defn, "comment", None),
            }
        )
    return named_ranges


def inspect_worksheet(
    formula_ws: Worksheet,
    value_ws: Optional[Worksheet],
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Inspect a single worksheet.

    Returns a tuple of (worksheet metadata, list of non-empty cell records).
    """
    merged_ranges = [str(rng) for rng in formula_ws.merged_cells.ranges]

    cells: List[Dict[str, Any]] = []
    for row in formula_ws.iter_rows():
        for cell in row:
            # Skip genuinely empty cells to keep the inventory focused.
            if cell.value is None:
                continue

            # A cell holds a formula when openpyxl types it as 'f'.
            is_formula = cell.data_type == "f"
            formula = cell.value if is_formula else None

            # Pull the cached calculated value from the parallel data_only workbook.
            cached_value: Any = None
            if value_ws is not None:
                cached_value = value_ws[cell.coordinate].value

            cells.append(
                {
                    "worksheet": formula_ws.title,
                    "coordinate": cell.coordinate,
                    "row": cell.row,
                    "column": cell.column,
                    "column_letter": cell.column_letter,
                    "raw_value": cell.value,
                    "formula": formula,
                    "cached_value": cached_value,
                    "number_format": cell.number_format,
                    "data_type": cell.data_type,
                }
            )

    metadata: Dict[str, Any] = {
        "name": formula_ws.title,
        "visibility": formula_ws.sheet_state,  # 'visible' | 'hidden' | 'veryHidden'
        "used_range": formula_ws.dimensions,
        "max_row": formula_ws.max_row,
        "max_column": formula_ws.max_column,
        "merged_cell_ranges": merged_ranges,
        "non_empty_cells": len(cells),
        "formula_cells": sum(1 for c in cells if c["formula"] is not None),
    }
    return metadata, cells


def _json_safe(value: Any) -> Any:
    """Coerce values openpyxl may return (datetimes, etc.) into JSON-friendly forms."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # datetime, time, Decimal and similar -> readable string representation.
    return str(value)


def build_inventory(
    workbook_path: Path,
    formula_wb: Workbook,
    value_wb: Workbook,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Assemble the workbook-level inventory and the flat list of cell records."""
    worksheets_meta: List[Dict[str, Any]] = []
    all_cells: List[Dict[str, Any]] = []

    for formula_ws in formula_wb.worksheets:
        # The cached-values workbook should mirror sheet names; guard defensively.
        value_ws = (
            value_wb[formula_ws.title] if formula_ws.title in value_wb.sheetnames else None
        )
        meta, cells = inspect_worksheet(formula_ws, value_ws)
        worksheets_meta.append(meta)
        all_cells.extend(cells)

    inventory: Dict[str, Any] = {
        "workbook": {
            "filename": workbook_path.name,
            "path": str(workbook_path.resolve()),
            "worksheet_count": len(worksheets_meta),
            "worksheet_names": [m["name"] for m in worksheets_meta],
            "total_non_empty_cells": len(all_cells),
            "total_formula_cells": sum(1 for c in all_cells if c["formula"] is not None),
        },
        "named_ranges": _extract_defined_names(formula_wb),
        "worksheets": worksheets_meta,
    }
    return inventory, all_cells


def write_json(inventory: Dict[str, Any], destination: Path) -> None:
    """Write the workbook inventory as UTF-8 JSON."""
    with destination.open("w", encoding="utf-8", newline="") as fh:
        json.dump(inventory, fh, ensure_ascii=False, indent=2, default=_json_safe)


def write_csv(cells: List[Dict[str, Any]], destination: Path) -> None:
    """Write the per-cell inventory as UTF-8 CSV."""
    with destination.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CELL_CSV_FIELDS)
        writer.writeheader()
        for cell in cells:
            # Stringify complex values so the CSV stays flat and readable.
            writer.writerow({key: _json_safe(cell.get(key)) for key in CELL_CSV_FIELDS})


def print_summary(
    workbook_path: Path,
    inventory: Dict[str, Any],
    json_path: Path,
    csv_path: Path,
) -> None:
    """Print the required terminal summary."""
    wb_meta = inventory["workbook"]
    print("Excel inspection complete")
    print(f"  Workbook filename    : {wb_meta['filename']}")
    print(f"  Worksheets           : {wb_meta['worksheet_count']}")
    print(f"  Non-empty cells      : {wb_meta['total_non_empty_cells']}")
    print(f"  Formulas             : {wb_meta['total_formula_cells']}")
    print(f"  JSON inventory       : {json_path}")
    print(f"  CSV inventory        : {csv_path}")


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point. Returns a process exit code."""
    args = parse_args(argv)
    workbook_path: Path = args.workbook
    output_dir: Path = args.output_dir

    # --- Validate input -----------------------------------------------------
    if not workbook_path.exists():
        print(f"Error: workbook not found: {workbook_path}", file=sys.stderr)
        return 1
    if not workbook_path.is_file():
        print(f"Error: not a file: {workbook_path}", file=sys.stderr)
        return 1

    # --- Load (read-only intent) -------------------------------------------
    try:
        formula_wb, value_wb = load_workbooks(workbook_path)
    except Exception as exc:  # openpyxl raises varied exception types.
        print(f"Error: failed to open workbook: {exc}", file=sys.stderr)
        return 1

    try:
        # --- Inspect --------------------------------------------------------
        inventory, cells = build_inventory(workbook_path, formula_wb, value_wb)

        # --- Ensure the output directory exists -----------------------------
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "excel_workbook_inventory.json"
        csv_path = output_dir / "excel_cells_inventory.csv"

        # --- Export ---------------------------------------------------------
        write_json(inventory, json_path)
        write_csv(cells, csv_path)
    except Exception as exc:
        print(f"Error: inspection failed: {exc}", file=sys.stderr)
        return 1
    finally:
        # Release file handles without ever saving back to disk.
        formula_wb.close()
        value_wb.close()

    print_summary(workbook_path, inventory, json_path, csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
