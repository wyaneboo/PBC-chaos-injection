"""Export generated workbooks with matching ground-truth JSON sidecars."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from pbc_chaos.config_loader import ChaosWorkbookConfig, load_config
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.metadata.schema import WorkbookGroundTruth


@dataclass(frozen=True)
class ExportedGroundTruthWorkbook:
    workbook: Workbook
    ground_truth: WorkbookGroundTruth
    workbook_path: Path
    ground_truth_path: Path


def export_pbc_workbook(
    company: CompanyProfile,
    period: FinancialPeriod,
    *,
    output_dir: str | Path,
    config: ChaosWorkbookConfig | str | Path | None = None,
    seed: int | None = None,
    filename_stem: str | None = None,
) -> ExportedGroundTruthWorkbook:
    """Generate and save a workbook plus its `.groundtruth.json` sidecar."""

    from pbc_chaos.pbc_workbook import generate_pbc_workbook_with_ground_truth

    resolved_config = load_config(config) if isinstance(config, str | Path) else config
    generated = generate_pbc_workbook_with_ground_truth(
        company,
        period,
        config=resolved_config,
        seed=seed,
    )
    return export_generated_workbook(
        generated.workbook,
        generated.ground_truth,
        output_dir=output_dir,
        filename_stem=filename_stem,
    )


def export_generated_workbook(
    workbook: Workbook,
    ground_truth: WorkbookGroundTruth,
    *,
    output_dir: str | Path,
    filename_stem: str | None = None,
) -> ExportedGroundTruthWorkbook:
    """Save an already-generated workbook and ground-truth object."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    stem = filename_stem or _default_filename_stem(ground_truth)
    workbook_path = output_path / f"{stem}.xlsx"
    ground_truth_path = output_path / f"{stem}.groundtruth.json"
    workbook.save(workbook_path)
    ground_truth_path.write_text(
        json.dumps(ground_truth.as_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ExportedGroundTruthWorkbook(
        workbook=workbook,
        ground_truth=ground_truth,
        workbook_path=workbook_path,
        ground_truth_path=ground_truth_path,
    )


def _default_filename_stem(ground_truth: WorkbookGroundTruth) -> str:
    company = _slug(ground_truth.company_name)
    year = ground_truth.financial_period["financial_year"]
    severity = _slug(_severity_label(ground_truth.chaos_level))
    return f"{company}_PBC_{year}_{severity}"


def _severity_label(chaos_level: dict[str, object]) -> str:
    mode = chaos_level.get("unreproducible_nightmare_mode")
    if isinstance(mode, dict) and mode.get("enabled"):
        return "unreproducible_nightmare"
    severity = chaos_level.get("severity")
    if severity == 0:
        return "clean"
    if severity == 5:
        return "nightmare"
    return f"severity_{severity}"


def _slug(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_")
    return text or "workbook"
