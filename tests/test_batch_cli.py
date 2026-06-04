import csv
import json

from openpyxl import Workbook
from typer.testing import CliRunner

from pbc_chaos.batch.pipeline import (
    MANIFEST_COLUMNS,
    generate_mixed_chaos_dataset,
    generate_single_workbook,
    validate_generated_directory,
)
from pbc_chaos.cli import app


def test_generate_single_workbook_writes_manifest_and_validates(tmp_path):
    result = generate_single_workbook(
        company_name="ABC Sdn Bhd",
        period_label="FY2025",
        chaos_level=0,
        output_dir=tmp_path,
        seed=42,
    )

    assert len(result.records) == 1
    assert result.records[0].exported.workbook_path.exists()
    assert result.records[0].exported.ground_truth_path.exists()
    assert result.manifest_path.exists()

    rows = list(csv.DictReader(result.manifest_path.open(encoding="utf-8")))
    assert rows
    assert rows[0].keys() == set(MANIFEST_COLUMNS)
    assert rows[0]["company_name"] == "ABC Sdn Bhd"
    assert rows[0]["period"] == "FY2025"
    assert rows[0]["chaos_level"] == "0"
    assert "trial_balance" in rows[0]["document_types"]
    assert int(rows[0]["row_count"]) > 0

    report = validate_generated_directory(tmp_path)
    assert report.passed


def test_generate_mixed_dataset_cycles_requested_chaos_levels(tmp_path):
    result = generate_mixed_chaos_dataset(
        company_count=3,
        period_label="FY2025",
        min_chaos=0,
        max_chaos=2,
        output_dir=tmp_path,
        seed=1,
    )

    rows = list(csv.DictReader(result.manifest_path.open(encoding="utf-8")))
    assert len(rows) == 3
    assert {row["chaos_level"] for row in rows} == {"0", "1", "2"}


def test_cli_generate_dataset_accepts_unreproducible_nightmare_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = CliRunner().invoke(
        app,
        [
            "generate-dataset",
            "--companies",
            "1",
            "--min-chaos",
            "0",
            "--max-chaos",
            "0",
            "--output",
            str(tmp_path),
            "--unreproducible-nightmare",
        ],
    )

    assert result.exit_code == 0
    sidecar_path = next(tmp_path.glob("*.groundtruth.json"))
    metadata = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert metadata["chaos_level"]["unreproducible_nightmare_mode"]["enabled"]
    assert any(
        error["type"] == "unreproducible_nightmare_plan"
        for error in metadata["intentional_errors"]
    )


def test_validate_reports_missing_groundtruth(tmp_path):
    workbook_path = tmp_path / "missing_sidecar.xlsx"
    Workbook().save(workbook_path)

    report = validate_generated_directory(tmp_path)

    assert not report.passed
    assert any(issue.code == "missing_groundtruth" for issue in report.issues)


def test_cli_rejects_invalid_chaos_level(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate-batch",
            "--companies",
            "1",
            "--period",
            "FY2025",
            "--chaos-level",
            "9",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "chaos-level must be an integer from 0 to 5" in result.output
