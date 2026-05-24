"""Workbook planning objects used before rendering to `.xlsx`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pbc_chaos.core.types import DocumentType


@dataclass(frozen=True)
class StyleSpec:
    number_format: str | None = None
    font_name: str | None = None
    font_size: int | None = None
    bold: bool | None = None
    italic: bool | None = None
    fill_color: str | None = None
    font_color: str | None = None
    alignment: str | None = None


@dataclass(frozen=True)
class ColumnSpec:
    key: str
    label: str
    concept: str | None = None
    width: float | None = None
    style: StyleSpec | None = None


@dataclass(frozen=True)
class CellSpec:
    row: int
    column: int
    value: Any
    style: StyleSpec | None = None
    comment: str | None = None
    formula: str | None = None


@dataclass(frozen=True)
class FormulaSpec:
    row: int
    column: int
    expression: str
    expected_value: Any | None = None


@dataclass(frozen=True)
class TablePlan:
    table_id: str
    anchor_row: int
    anchor_column: int
    columns: tuple[ColumnSpec, ...]
    rows: tuple[dict[str, Any], ...]
    title: str | None = None
    subtotal_rows: tuple[int, ...] = field(default_factory=tuple)
    style: StyleSpec | None = None


@dataclass(frozen=True)
class SheetPlan:
    name: str
    tables: tuple[TablePlan, ...] = field(default_factory=tuple)
    cells: tuple[CellSpec, ...] = field(default_factory=tuple)
    formulas: tuple[FormulaSpec, ...] = field(default_factory=tuple)
    merged_ranges: tuple[str, ...] = field(default_factory=tuple)
    hidden_rows: tuple[int, ...] = field(default_factory=tuple)
    hidden_columns: tuple[str, ...] = field(default_factory=tuple)
    freeze_panes: str | None = None
    tab_color: str | None = None
    hidden: bool = False


@dataclass(frozen=True)
class WorkbookPlan:
    document_type: DocumentType
    client_id: str
    financial_year: int
    suggested_filename: str
    sheets: tuple[SheetPlan, ...]
    properties: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)

