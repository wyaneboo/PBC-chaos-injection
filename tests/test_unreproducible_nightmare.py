import json
import os

from openpyxl import Workbook

from pbc_chaos.chaos import unreproducible_nightmare as nightmare
from pbc_chaos.config_loader import UnreproducibleNightmareModeConfig


def make_workbook():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Trial Balance"
    worksheet.append(["account_code", "closing_balance"])
    worksheet.append(["1000", 125.0])
    worksheet.append(["2000", -125.0])
    return workbook


def test_llm_planner_response_is_sanitized_and_used(monkeypatch):
    workbook = make_workbook()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_post_gemini_generate_content(*, model, payload, api_key, timeout):
        assert model == "gemma-4-31b-it"
        assert api_key == "test-key"
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["responseJsonSchema"]["required"] == ["plan"]
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
                                                "tool": "human_residue_notation",
                                                "sheet": "Trial Balance",
                                                "count": 2,
                                                "texts": ["pls confirm final TB", "old version?"],
                                            },
                                            {
                                                "tool": "formula_errors",
                                                "sheet": "Trial Balance",
                                                "count": 1,
                                            },
                                            {
                                                "tool": "delete_rows",
                                                "sheet": "Trial Balance",
                                                "count": 99,
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

    monkeypatch.setattr(
        nightmare,
        "_post_gemini_generate_content",
        fake_post_gemini_generate_content,
    )
    config = UnreproducibleNightmareModeConfig(
        enabled=True,
        use_llm_planner=True,
        notation_count=2,
        extra_tool_count=1,
    )

    result = nightmare.UnreproducibleNightmareAgent(config).plan(
        workbook,
        allowed_sheet_names=("Trial Balance",),
    )

    assert result.provider == "langgraph_gemini_generate_content"
    assert result.error is None
    assert result.plan == (
        {
            "tool": "human_residue_notation",
            "sheet": "Trial Balance",
            "count": 2,
            "texts": ("pls confirm final TB", "old version?"),
        },
        {"tool": "formula_errors", "sheet": "Trial Balance", "count": 1},
    )


def test_langgraph_path_uses_llm_planner_when_available(monkeypatch):
    workbook = make_workbook()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_post_gemini_generate_content(*, model, payload, api_key, timeout):
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"plan": []})}]}}]}

    monkeypatch.setattr(
        nightmare,
        "_post_gemini_generate_content",
        fake_post_gemini_generate_content,
    )
    config = UnreproducibleNightmareModeConfig(
        enabled=True,
        use_llm_planner=True,
        notation_count=1,
        extra_tool_count=0,
    )

    result = nightmare.UnreproducibleNightmareAgent(config).plan(
        workbook,
        allowed_sheet_names=("Trial Balance",),
    )

    assert result.provider == "langgraph_gemini_generate_content"
    assert result.plan == (
        {"tool": "human_residue_notation", "sheet": "Trial Balance", "count": 1},
    )


def test_llm_planner_loads_api_key_from_dotenv(tmp_path, monkeypatch):
    workbook = make_workbook()
    env_var = "PBC_CHAOS_TEST_GEMINI_API_KEY"
    monkeypatch.delenv(env_var, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"{env_var}=dotenv-key\n", encoding="utf-8")

    def fake_post_gemini_generate_content(*, model, payload, api_key, timeout):
        assert api_key == "dotenv-key"
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"plan": []})}]}}]}

    monkeypatch.setattr(
        nightmare,
        "_post_gemini_generate_content",
        fake_post_gemini_generate_content,
    )
    config = UnreproducibleNightmareModeConfig(
        enabled=True,
        use_llm_planner=True,
        gemini_api_key_env=env_var,
        notation_count=1,
        extra_tool_count=0,
    )

    result = nightmare.UnreproducibleNightmareAgent(config).plan(
        workbook,
        allowed_sheet_names=("Trial Balance",),
    )

    os.environ.pop(env_var, None)
    assert result.provider == "langgraph_gemini_generate_content"


def test_llm_plan_falls_back_when_api_key_is_missing(tmp_path, monkeypatch):
    workbook = make_workbook()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config = UnreproducibleNightmareModeConfig(
        enabled=True,
        use_llm_planner=True,
        notation_count=2,
        extra_tool_count=0,
    )

    result = nightmare.UnreproducibleNightmareAgent(config).plan(
        workbook,
        allowed_sheet_names=("Trial Balance",),
    )

    assert result.provider == "langgraph_heuristic_fallback"
    assert "GEMINI_API_KEY is not set" in (result.error or "")
    assert sum(action.get("count", 0) for action in result.plan) >= 2


def test_sanitize_plan_repairs_unknown_sheets_and_missing_notation_budget():
    plan = nightmare._sanitize_plan(
        [
            {"tool": "human_residue_notation", "sheet": "Old Copy", "count": 1},
            {"tool": "secondary_table", "sheet": "Trial Balance", "count": 1},
            {"tool": "formula_errors", "sheet": "Trial Balance", "count": 1},
        ],
        summary={"visible_sheet_names": ["Trial Balance"]},
        notation_count=3,
        extra_tool_count=1,
    )

    assert plan[0]["sheet"] == "Trial Balance"
    assert sum(
        action["count"]
        for action in plan
        if action["tool"] == "human_residue_notation"
    ) >= 3
    assert [action["tool"] for action in plan].count("secondary_table") == 1
    assert [action["tool"] for action in plan].count("formula_errors") == 0


def test_sanitize_plan_fills_missing_extra_tool_budget():
    plan = nightmare._sanitize_plan(
        [],
        summary={"visible_sheet_names": ["Trial Balance"]},
        notation_count=1,
        extra_tool_count=2,
    )

    assert plan == [
        {"tool": "human_residue_notation", "sheet": "Trial Balance", "count": 1},
        {"tool": "formula_errors", "sheet": "Trial Balance", "count": 1},
        {"tool": "stringified_numbers", "sheet": "Trial Balance", "count": 1},
    ]
