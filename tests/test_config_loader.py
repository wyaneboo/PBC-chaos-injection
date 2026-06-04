from pathlib import Path

from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.config_loader import config_from_mapping, load_config
from pbc_chaos.pbc_workbook import generate_pbc_workbook, generate_pbc_workbook_with_ground_truth


def company_and_period():
    return (
        CompanyProfile(company_id="client_001", company_name="Example Sdn Bhd"),
        FinancialPeriod.calendar_year(2025),
    )


def test_load_config_applies_severity_defaults_for_missing_probabilities():
    config = config_from_mapping(
        {
            "severity": 2,
            "probabilities": {
                "formula_errors": 0.0,
            },
        }
    )

    assert config.severity == 2
    assert config.probabilities.formula_errors == 0.0
    assert config.probabilities.inserted_notes > 0


def test_config_loader_accepts_unreproducible_nightmare_mode():
    config = config_from_mapping(
        {
            "severity": 5,
            "unreproducible_nightmare_mode": {
                "enabled": True,
                "notation_count": 7,
                "extra_tool_count": 2,
            },
        }
    )

    assert config.unreproducible_nightmare_mode.enabled
    assert config.unreproducible_nightmare_mode.notation_count == 7
    assert config.unreproducible_nightmare_mode.extra_tool_count == 2


def test_config_loader_rejects_invalid_values():
    invalid_configs = (
        {"severity": 6},
        {"severity": 2.5},
        {"severity": 2, "probabilities": {"hidden_rows": 1.5}},
        {"severity": 2, "probabilities": {"not_a_probability": 0.1}},
        {"severity": 2, "unexpected": True},
        {"severity": 5, "unreproducible_nightmare_mode": {"notation_count": -1}},
    )

    for raw in invalid_configs:
        try:
            config_from_mapping(raw)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid config to fail: {raw}")


def test_clean_config_generates_plain_workbook():
    company, period = company_and_period()
    config = load_config(Path("config/clean.yaml"))

    workbook = generate_pbc_workbook(company, period, config=config, seed=42)
    worksheet = workbook["Trial Balance"]

    assert worksheet["A1"].value == "client_id"
    assert not worksheet.merged_cells.ranges
    assert all(not name.endswith("_old_v1") for name in workbook.sheetnames)
    assert all(sheet.sheet_state == "visible" for sheet in workbook.worksheets)


def test_nightmare_config_applies_all_chaos_categories():
    company, period = company_and_period()
    config = load_config(Path("config/nightmare.yaml"))

    workbook = generate_pbc_workbook(company, period, config=config, seed=42)
    worksheet = workbook["Trial Balance"]

    assert worksheet.merged_cells.ranges
    assert any(name.endswith("_old_v1") for name in workbook.sheetnames)
    assert any(sheet.sheet_state == "hidden" for sheet in workbook.worksheets)
    assert any(dimension.hidden for dimension in worksheet.row_dimensions.values())
    assert any(dimension.hidden for dimension in worksheet.column_dimensions.values())
    assert any(
        isinstance(cell.value, str) and cell.value.startswith("=")
        for row in worksheet.iter_rows()
        for cell in row
    )


def test_unreproducible_nightmare_mode_adds_ai_notations_and_plan_metadata():
    company, period = company_and_period()
    config = config_from_mapping(
        {
            "severity": 1,
            "unreproducible_nightmare_mode": {
                "enabled": True,
                "use_llm_planner": False,
                "notation_count": 6,
                "extra_tool_count": 0,
            },
        }
    )

    generated = generate_pbc_workbook_with_ground_truth(company, period, config=config, seed=42)
    metadata = generated.ground_truth.as_dict()
    notes = [
        note
        for sheet in metadata["sheets"]
        for note in sheet["inserted_notes"]
        if note["type"] == "ai_random_notation"
    ]

    assert metadata["chaos_level"]["unreproducible_nightmare_mode"]["enabled"]
    assert notes
    assert any(
        error["type"] == "unreproducible_nightmare_plan"
        for error in metadata["intentional_errors"]
    )


def test_unreproducible_nightmare_mode_changes_identity_for_same_seed():
    company, period = company_and_period()
    config = config_from_mapping(
        {
            "severity": 1,
            "unreproducible_nightmare_mode": {
                "enabled": True,
                "use_llm_planner": False,
                "notation_count": 1,
                "extra_tool_count": 0,
            },
        }
    )

    first = generate_pbc_workbook_with_ground_truth(company, period, config=config, seed=42)
    second = generate_pbc_workbook_with_ground_truth(company, period, config=config, seed=42)

    assert first.ground_truth.workbook_id != second.ground_truth.workbook_id
