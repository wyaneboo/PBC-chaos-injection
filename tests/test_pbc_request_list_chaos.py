import json
from random import SystemRandom

from typer.testing import CliRunner

from pbc_chaos.chaos import unreproducible_nightmare as nightmare
from pbc_chaos.batch.pipeline import generate_single_workbook, validate_generated_directory
from pbc_chaos.cli import app
from pbc_chaos.config_loader import config_from_mapping, load_config
from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.generators.pbc_request_list import PBCRequestListGenerator
from pbc_chaos.pbc_workbook import generate_pbc_workbook_with_ground_truth
from pbc_chaos.workbook import pbc_tracker_layout


def company_and_period():
    return (
        CompanyProfile(company_id="client_001", company_name="ABC Sdn Bhd"),
        FinancialPeriod.calendar_year(2025),
    )


def test_pbc_request_list_generator_produces_clean_tracker_rows():
    company, period = company_and_period()
    result = PBCRequestListGenerator().generate(company, period, seed=42)

    assert result.document_type == DocumentType.PBC_REQUEST_LIST
    assert len(result.data) >= 20
    assert {
        "request_id",
        "request_description",
        "detail_remark",
        "purpose",
        "period_label",
        "file_type_requested",
        "owner_pic",
        "due_date",
        "status",
        "date_received",
        "review_status",
        "auditor_comment",
        "follow_up_required",
        "update_flag",
    }.issubset(result.data.columns)


def test_nightmare_workbook_includes_messy_pbc_request_list_first():
    company, period = company_and_period()
    generated = generate_pbc_workbook_with_ground_truth(
        company,
        period,
        config=load_config("config/nightmare.yaml"),
        seed=42,
    )
    workbook = generated.workbook
    worksheet = workbook["PBC Request List"]
    metadata = generated.ground_truth.as_dict()
    tracker_truth = next(
        sheet for sheet in metadata["sheets"] if sheet["document_type"] == "pbc_request_list"
    )

    assert workbook.sheetnames[0] == "PBC Request List"
    assert worksheet["D1"].value == "**PREPARED BY CLIENT (PBC) LIST**"
    assert worksheet.auto_filter.ref is not None
    assert worksheet.freeze_panes is not None
    assert tracker_truth["table_location"]["header_row"] > 1
    assert tracker_truth["renamed_columns_mapping"]["request_id"] == "Request ID"
    assert any(note["type"] == "tracker_instruction_blocks" for note in tracker_truth["inserted_notes"])
    assert any(note["type"] == "tracker_update_highlight" for note in tracker_truth["inserted_notes"])
    assert any(
        error["type"] == "tracker_status_variant_noise"
        for error in tracker_truth["intentional_errors"]
    )
    assert any(
        error["type"] == "tracker_deadline_noise"
        for error in tracker_truth["intentional_errors"]
    )


def test_nightmare_agent_records_tracker_actions_when_enabled(monkeypatch):
    company, period = company_and_period()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_post_gemini_generate_content(*, model, payload, api_key, timeout):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "plan": [
                                            {
                                                "tool": "add_visible_tracker_comment",
                                                "sheet": "PBC Request List",
                                                "row_key": "A.7",
                                                "text": "Not provided, remind finance",
                                            },
                                            {
                                                "tool": "apply_tracker_follow_up_noise",
                                                "sheet": "PBC Request List",
                                                "row_key": "A.7",
                                                "style": "Y (remind)",
                                            },
                                        ]
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr(nightmare, "_post_gemini_generate_content", fake_post_gemini_generate_content)
    config = config_from_mapping(
        {
            "severity": 5,
            "unreproducible_nightmare_mode": {
                "enabled": True,
                "use_llm_planner": True,
                "notation_count": 1,
                "extra_tool_count": 2,
            },
        }
    )

    generated = generate_pbc_workbook_with_ground_truth(company, period, config=config, seed=42)
    metadata = generated.ground_truth.as_dict()
    tracker_truth = next(
        sheet for sheet in metadata["sheets"] if sheet["document_type"] == "pbc_request_list"
    )

    assert any(
        note["type"] == "ai_tracker_visible_comment"
        for note in tracker_truth["inserted_notes"]
    )
    assert any(
        error["type"] == "ai_tracker_follow_up_noise"
        for error in tracker_truth["intentional_errors"]
    )
    assert any(
        error["type"] == "unreproducible_nightmare_plan"
        for error in metadata["intentional_errors"]
    )


def test_tracker_agent_action_rejects_unknown_row_key():
    company, period = company_and_period()
    generated = generate_pbc_workbook_with_ground_truth(
        company,
        period,
        config=load_config("config/nightmare.yaml"),
        seed=42,
    )

    applied = pbc_tracker_layout.apply_tracker_agent_action(
        worksheet=generated.workbook["PBC Request List"],
        action={
            "tool": "add_visible_tracker_comment",
            "sheet": "PBC Request List",
            "row_key": "DOES-NOT-EXIST",
            "text": "Should not apply",
        },
        logger=None,
        rng=SystemRandom(),
    )

    assert applied is None


def test_cli_generation_with_tracker_validates(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "generate-one",
            "--company",
            "Tracker Demo Sdn Bhd",
            "--period",
            "FY2025",
            "--chaos-level",
            "5",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    report = validate_generated_directory(tmp_path)
    assert report.passed

    sidecar_path = next(tmp_path.glob("*.groundtruth.json"))
    metadata = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert metadata["document_types_included"][0] == "pbc_request_list"
    assert metadata["sheet_names"][0] == "PBC Request List"


def test_batch_helper_manifest_includes_pbc_request_list(tmp_path):
    result = generate_single_workbook(
        company_name="Tracker Demo Sdn Bhd",
        period_label="FY2025",
        chaos_level=5,
        output_dir=tmp_path,
        seed=42,
    )

    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert "pbc_request_list" in manifest
