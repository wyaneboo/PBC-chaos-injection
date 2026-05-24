"""Create a small messy PBC workbook using the Phase 4 layout engine."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from pbc_chaos.workbook import layout_engine


def build_clean_workbook() -> Workbook:
    """Build a simple clean worksheet for the layout-chaos demo."""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "TB"
    worksheet.append(["Account", "Description", "Debit", "Credit", "Owner"])
    rows = [
        ("1000", "Cash at bank", 125000.25, 0, "AR team"),
        ("1100", "Trade receivables", 98000.00, 0, "AR team"),
        ("2000", "Trade payables", 0, 73000.45, "AP team"),
        ("3000", "Share capital", 0, 50000.00, "Controller"),
        ("4000", "Revenue", 0, 450000.00, "FP&A"),
        ("5000", "Payroll expense", 210000.00, 0, "HR finance"),
        ("6100", "Rent expense", 48000.00, 0, "Operations"),
    ]
    for row in rows:
        worksheet.append(row)
    return workbook


def main() -> None:
    workbook = build_clean_workbook()
    worksheet = workbook["TB"]
    layout_engine.apply_layout_chaos(
        workbook=workbook,
        worksheet=worksheet,
        config={
            "client_name": "Contoso Manufacturing Sdn Bhd",
            "prepared_by": "Finance close team",
            "reviewer_name": "Audit Senior",
            "financial_year": 2025,
            "title": "Trial Balance PBC - Draft v3",
        },
        seed=42,
    )
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    workbook.save(output_dir / "demo_layout_chaos.xlsx")


if __name__ == "__main__":
    main()
