"""Safe helpers for immutable workbook-plan mutations.

Chaos injectors should use these helpers instead of editing plan internals in
place. The workbook plan dataclasses are frozen, but nested dictionaries can still
be mutable, so helpers copy touched structures before returning replacements.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from pbc_chaos.workbook.plan import CellSpec, SheetPlan, TablePlan, WorkbookPlan


def replace_workbook(plan: WorkbookPlan, **changes: Any) -> WorkbookPlan:
    return replace(plan, **changes)


def update_workbook_properties(plan: WorkbookPlan, **properties: Any) -> WorkbookPlan:
    return replace(plan, properties={**plan.properties, **properties})


def update_workbook_lineage(plan: WorkbookPlan, **lineage: Any) -> WorkbookPlan:
    return replace(plan, lineage={**plan.lineage, **lineage})


def replace_sheet(plan: WorkbookPlan, sheet_name: str, new_sheet: SheetPlan) -> WorkbookPlan:
    replaced = False
    sheets: list[SheetPlan] = []

    for sheet in plan.sheets:
        if sheet.name == sheet_name:
            sheets.append(new_sheet)
            replaced = True
        else:
            sheets.append(sheet)

    if not replaced:
        raise KeyError(f"Sheet not found: {sheet_name}")

    return replace(plan, sheets=tuple(sheets))


def update_sheet(plan: WorkbookPlan, sheet_name: str, **changes: Any) -> WorkbookPlan:
    sheet = get_sheet(plan, sheet_name)
    return replace_sheet(plan, sheet_name, replace(sheet, **changes))


def get_sheet(plan: WorkbookPlan, sheet_name: str) -> SheetPlan:
    for sheet in plan.sheets:
        if sheet.name == sheet_name:
            return sheet
    raise KeyError(f"Sheet not found: {sheet_name}")


def replace_table(sheet: SheetPlan, table_id: str, new_table: TablePlan) -> SheetPlan:
    replaced = False
    tables: list[TablePlan] = []

    for table in sheet.tables:
        if table.table_id == table_id:
            tables.append(new_table)
            replaced = True
        else:
            tables.append(table)

    if not replaced:
        raise KeyError(f"Table not found: {table_id}")

    return replace(sheet, tables=tuple(tables))


def update_table(sheet: SheetPlan, table_id: str, **changes: Any) -> SheetPlan:
    table = get_table(sheet, table_id)
    return replace_table(sheet, table_id, replace(table, **changes))


def get_table(sheet: SheetPlan, table_id: str) -> TablePlan:
    for table in sheet.tables:
        if table.table_id == table_id:
            return table
    raise KeyError(f"Table not found: {table_id}")


def map_table_rows(
    sheet: SheetPlan,
    table_id: str,
    mapper: Callable[[dict[str, Any]], dict[str, Any]],
) -> SheetPlan:
    table = get_table(sheet, table_id)
    rows = tuple(mapper(dict(row)) for row in table.rows)
    return replace_table(sheet, table_id, replace(table, rows=rows))


def append_sheet_cells(sheet: SheetPlan, cells: tuple[CellSpec, ...]) -> SheetPlan:
    return replace(sheet, cells=sheet.cells + cells)


def append_merged_ranges(sheet: SheetPlan, ranges: tuple[str, ...]) -> SheetPlan:
    return replace(sheet, merged_ranges=sheet.merged_ranges + ranges)


def append_hidden_rows(sheet: SheetPlan, rows: tuple[int, ...]) -> SheetPlan:
    return replace(sheet, hidden_rows=sheet.hidden_rows + rows)


def append_hidden_columns(sheet: SheetPlan, columns: tuple[str, ...]) -> SheetPlan:
    return replace(sheet, hidden_columns=sheet.hidden_columns + columns)

