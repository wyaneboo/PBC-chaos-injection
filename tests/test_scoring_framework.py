import csv
import json

from typer.testing import CliRunner

from pbc_chaos.cli import app
from pbc_chaos.scoring import compare_extraction, compare_extraction_files


def sample_groundtruth():
    rows = [
        {
            "client_id": "client_001",
            "financial_year": 2025,
            "period_end": "2025-12-31",
            "account_code": "1000",
            "account_name": "Cash",
            "closing_balance": 123.45,
        },
        {
            "client_id": "client_001",
            "financial_year": 2025,
            "period_end": "2025-12-31",
            "account_code": "2000",
            "account_name": "AP",
            "closing_balance": -50.0,
        },
    ]
    return {
        "workbook_id": "wb_test",
        "company_name": "ABC Sdn Bhd",
        "document_types_included": ["trial_balance"],
        "sheet_names": ["Trial Balance"],
        "injected_discrepancies": [
            {
                "discrepancy_id": "DISC-00001",
                "source_document": "general_ledger",
                "target_document": "trial_balance",
                "affected_field": "closing_balance",
                "reason": "controlled_variance",
                "relationship_name": "general_ledger_to_trial_balance",
            }
        ],
        "sheets": [
            {
                "sheet_name": "Trial Balance",
                "document_type": "trial_balance",
                "clean_canonical_schema": [
                    "client_id",
                    "financial_year",
                    "period_end",
                    "account_code",
                    "account_name",
                    "closing_balance",
                ],
                "original_clean_row_count": 2,
                "final_messy_row_count": 2,
                "table_location": {
                    "start_row": 3,
                    "start_column": 2,
                    "end_row": 5,
                    "end_column": 7,
                    "header_row": 3,
                },
                "expected_extraction_output": rows,
            }
        ],
    }


def test_compare_perfect_extraction_scores_one():
    groundtruth = sample_groundtruth()
    sheet = groundtruth["sheets"][0]
    extraction = {
        "documents": [
            {
                "document_type": "trial_balance",
                "sheet_name": "Trial Balance",
                "table_location": sheet["table_location"],
                "headers": sheet["clean_canonical_schema"],
                "rows": sheet["expected_extraction_output"],
            }
        ],
        "detected_discrepancies": groundtruth["injected_discrepancies"],
    }

    report = compare_extraction(groundtruth, extraction)

    assert report.overall_score == 1.0
    assert report.summary_metrics["numeric_value_accuracy"].score == 1.0
    assert report.summary_metrics["date_normalization_accuracy"].score == 1.0
    assert report.summary_metrics["discrepancy_detection_accuracy"].score == 1.0


def test_compare_scores_fuzzy_headers_and_numeric_tolerance():
    groundtruth = sample_groundtruth()
    extraction = {
        "documents": [
            {
                "document_type": "trial_balance",
                "sheet_name": "Trial Balance",
                "table_bounds": {
                    "start_cell": "B3",
                    "end_cell": "G6",
                    "header_row": 3,
                },
                "rows": [
                    {
                        "Client ID": "client_001",
                        "Financial Year": "2025",
                        "Period End": "31/12/2025",
                        "Account Code": "1000",
                        "Account Name": "Cash",
                        "Closing Balance": "123.456",
                    },
                    {
                        "Client ID": "client_001",
                        "Financial Year": "2025",
                        "Period End": "31/12/2025",
                        "Account Code": "2000",
                        "Account Name": "AP",
                        "Closing Balance": "(50.00)",
                    },
                ],
            }
        ],
        "detected_discrepancies": [
            {
                "source_document": "general_ledger",
                "target_document": "trial_balance",
                "affected_field": "closing_balance",
                "reason": "controlled_variance",
                "relationship_name": "general_ledger_to_trial_balance",
            }
        ],
    }

    report = compare_extraction(groundtruth, extraction)

    assert report.summary_metrics["column_mapping_accuracy"].score == 1.0
    assert report.summary_metrics["numeric_value_accuracy"].score == 1.0
    assert report.summary_metrics["date_normalization_accuracy"].score == 1.0
    assert 0 < report.summary_metrics["table_boundary_detection_accuracy"].score < 1


def test_compare_extraction_files_writes_reports(tmp_path):
    groundtruth = sample_groundtruth()
    extraction = {
        "documents": [
            {
                "document_type": "trial_balance",
                "sheet_name": "Trial Balance",
                "table_location": groundtruth["sheets"][0]["table_location"],
                "headers": groundtruth["sheets"][0]["clean_canonical_schema"],
                "rows": groundtruth["sheets"][0]["expected_extraction_output"],
            }
        ],
        "detected_discrepancies": groundtruth["injected_discrepancies"],
    }
    groundtruth_path = tmp_path / "sample.groundtruth.json"
    extraction_path = tmp_path / "extraction.json"
    json_report_path = tmp_path / "score_report.json"
    markdown_report_path = tmp_path / "score_report.md"
    groundtruth_path.write_text(json.dumps(groundtruth), encoding="utf-8")
    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")

    report = compare_extraction_files(
        groundtruth_path=groundtruth_path,
        extraction_output_path=extraction_path,
        json_report_path=json_report_path,
        markdown_report_path=markdown_report_path,
    )

    assert report.overall_score == 1.0
    assert json_report_path.exists()
    assert markdown_report_path.exists()
    assert "Extraction Score Report" in markdown_report_path.read_text(encoding="utf-8")


def test_cli_score_command_writes_reports(tmp_path):
    groundtruth = sample_groundtruth()
    sheet = groundtruth["sheets"][0]
    groundtruth_path = tmp_path / "sample.groundtruth.json"
    extraction_path = tmp_path / "extraction.csv"
    json_report_path = tmp_path / "score_report.json"
    markdown_report_path = tmp_path / "score_report.md"
    groundtruth_path.write_text(json.dumps(groundtruth), encoding="utf-8")
    with extraction_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sheet["clean_canonical_schema"])
        writer.writeheader()
        writer.writerows(sheet["expected_extraction_output"])

    result = CliRunner().invoke(
        app,
        [
            "score",
            "--groundtruth",
            str(groundtruth_path),
            "--extraction",
            str(extraction_path),
            "--output-json",
            str(json_report_path),
            "--output-md",
            str(markdown_report_path),
        ],
    )

    assert result.exit_code == 0
    assert "Overall score:" in result.output
    assert json_report_path.exists()
    assert markdown_report_path.exists()
