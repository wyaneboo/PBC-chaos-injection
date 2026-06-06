"""Ground-truth metadata schema for generated PBC workbooks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TableLocation:
    """Main table coordinates after workbook chaos has been applied."""

    start_cell: str
    end_cell: str
    start_row: int
    start_column: int
    end_row: int
    end_column: int
    header_row: int


@dataclass(frozen=True)
class SheetGroundTruth:
    """Machine-readable truth for one generated document sheet."""

    sheet_name: str
    document_type: str
    clean_canonical_schema: tuple[str, ...]
    original_clean_row_count: int
    final_messy_row_count: int
    table_location: TableLocation
    renamed_columns_mapping: dict[str, str] = field(default_factory=dict)
    visible_export_profile: str | None = None
    visible_export_department: str | None = None
    visible_export_erp_style: str | None = None
    visible_table_schema: tuple[str, ...] = ()
    visible_column_headers: tuple[str, ...] = ()
    visible_columns_mapping: dict[str, str] = field(default_factory=dict)
    canonical_to_visible_columns: dict[str, str] = field(default_factory=dict)
    omitted_canonical_fields: tuple[str, ...] = ()
    context_field_locations: dict[str, str] = field(default_factory=dict)
    context_field_values: dict[str, Any] = field(default_factory=dict)
    ambiguous_visible_headers: dict[str, str] = field(default_factory=dict)
    hidden_rows: tuple[int, ...] = ()
    hidden_columns: tuple[str, ...] = ()
    merged_cell_ranges: tuple[str, ...] = ()
    inserted_notes: tuple[dict[str, Any], ...] = ()
    intentional_errors: tuple[dict[str, Any], ...] = ()
    expected_extraction_output: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class WorkbookGroundTruth:
    """Machine-readable truth sidecar for one generated workbook."""

    workbook_id: str
    company_id: str
    company_name: str
    financial_period: dict[str, Any]
    generated_at: str
    seed: int | None
    chaos_level: dict[str, Any]
    document_types_included: tuple[str, ...]
    sheet_names: tuple[str, ...]
    clean_canonical_schemas: dict[str, tuple[str, ...]]
    sheets: tuple[SheetGroundTruth, ...]
    injected_discrepancies: tuple[dict[str, Any], ...] = ()
    intentional_errors: tuple[dict[str, Any], ...] = ()
    expected_extraction_output: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
