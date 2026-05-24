"""Formatting mutations for manually maintained audit PBC workbooks."""

from __future__ import annotations

from random import Random

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from pbc_chaos.workbook.workbook_mutations import TableBounds


STATUS_STYLES: dict[str, str] = {
    "Reviewed": "C6E0B4",
    "Pending support": "FFF2CC",
    "Needs follow-up": "F8CBAD",
    "Client updated": "BDD7EE",
}


def apply_inconsistent_formatting(worksheet: Worksheet, table: TableBounds, *, rng: Random) -> None:
    """Apply small, plausible formatting inconsistencies across the table."""

    header_fill = PatternFill("solid", fgColor=rng.choice(["1F4E78", "5B9BD5", "70AD47"]))
    for col in range(table.min_col, table.max_col + 1):
        cell = worksheet.cell(table.header_row, col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal=rng.choice(["center", "left"]))

    thin_gray = Side(style="thin", color="BFBFBF")
    dotted_gray = Side(style="hair", color="D9D9D9")
    for row in range(table.min_row + 1, table.max_row + 1):
        if row % rng.choice([5, 7, 9]) == 0:
            worksheet.row_dimensions[row].height = rng.choice([18, 21, 24])
        for col in range(table.min_col, table.max_col + 1):
            cell = worksheet.cell(row, col)
            cell.border = Border(bottom=rng.choice([thin_gray, dotted_gray]))
            if isinstance(cell.value, int | float):
                cell.number_format = rng.choice(["#,##0.00", "#,##0", "$#,##0.00"])
            if rng.random() < 0.035:
                cell.fill = PatternFill("solid", fgColor=rng.choice(["FFF2CC", "E2F0D9", "DDEBF7"]))
            if rng.random() < 0.02:
                cell.font = Font(italic=True, color="666666")

    for col in range(table.min_col, table.max_col + 1):
        worksheet.column_dimensions[worksheet.cell(table.header_row, col).column_letter].width = rng.choice(
            [10, 12, 14, 18, 22]
        )


def apply_status_cells(worksheet: Worksheet, table: TableBounds, *, rng: Random) -> TableBounds:
    """Add a color-coded audit status column adjacent to the table."""

    status_col = table.max_col + 1
    worksheet.cell(table.header_row, status_col, "Audit status")
    worksheet.cell(table.header_row, status_col).font = Font(bold=True, color="FFFFFF")
    worksheet.cell(table.header_row, status_col).fill = PatternFill("solid", fgColor="7F7F7F")

    statuses = tuple(STATUS_STYLES)
    for row in range(table.min_row + 1, table.max_row + 1):
        status = rng.choice(statuses)
        cell = worksheet.cell(row, status_col, status)
        cell.fill = PatternFill("solid", fgColor=STATUS_STYLES[status])
        cell.alignment = Alignment(horizontal="center")

    worksheet.column_dimensions[worksheet.cell(table.header_row, status_col).column_letter].width = 16
    return TableBounds(table.min_row, table.min_col, table.max_row, status_col)

