import json

from pbc_chaos.web.runner import (
    _nightmare_agent_details,
    _nightmare_progress_details,
    metadata_payload,
)


def test_metadata_payload_detects_gemini_key_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=dotenv-key\n", encoding="utf-8")

    payload = metadata_payload()

    assert payload["geminiConfigured"] is True


def test_nightmare_agent_details_are_loaded_from_groundtruth(tmp_path):
    groundtruth_path = tmp_path / "sample.groundtruth.json"
    groundtruth_path.write_text(
        json.dumps(
            {
                "intentional_errors": [
                    {"type": "layout_noise"},
                    {
                        "type": "unreproducible_nightmare_plan",
                        "agent_provider": "langgraph_gemini_generate_content",
                        "agent_error": None,
                        "planned_actions": [
                            {
                                "tool": "human_residue_notation",
                                "sheet": "Trial Balance",
                                "count": 2,
                                "reason": "Sparse staff notes.",
                            }
                        ],
                        "applied_actions": [
                            {
                                "tool": "human_residue_notation",
                                "sheet": "Trial Balance",
                                "count": 2,
                                "cells": ["B12", "C18"],
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    details = _nightmare_agent_details(groundtruth_path)

    assert details is not None
    assert details["agent_provider"] == "langgraph_gemini_generate_content"
    assert details["planned_action_count"] == 1
    assert details["applied_action_count"] == 1
    assert details["planned_actions"][0]["reason"] == "Sparse staff notes."


def test_nightmare_progress_details_are_compacted_for_streaming():
    details = _nightmare_progress_details(
        {
            "phase": "applied",
            "agent_provider": "langgraph_gemini_generate_content",
            "agent_error": None,
            "planned_actions": (
                {"tool": "human_residue_notation", "sheet": "Trial Balance", "count": 1},
            ),
            "applied_actions": (
                {
                    "tool": "human_residue_notation",
                    "sheet": "Trial Balance",
                    "count": 1,
                    "cells": ("B12",),
                },
            ),
            "current_action": {"tool": "human_residue_notation", "sheet": "Trial Balance"},
            "action_index": 1,
            "action_total": 1,
        }
    )

    assert details["phase"] == "applied"
    assert details["planned_action_count"] == 1
    assert details["applied_action_count"] == 1
    assert details["current_action"]["tool"] == "human_residue_notation"
