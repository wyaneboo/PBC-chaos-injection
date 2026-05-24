"""Workbook renderer contract."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pbc_chaos.workbook.plan import WorkbookPlan


class WorkbookRenderer(Protocol):
    """Render workbook plans to physical files."""

    def render(self, plan: WorkbookPlan, output_dir: Path) -> Path:
        """Render a workbook and return the generated file path."""
        ...


class OpenPyxlWorkbookRenderer:
    """Default `.xlsx` renderer placeholder."""

    def render(self, plan: WorkbookPlan, output_dir: Path) -> Path:
        raise NotImplementedError("OpenPyXL rendering is not implemented yet.")

