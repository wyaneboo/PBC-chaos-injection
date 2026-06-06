"""Progress event contracts for the local web runner."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


SEVERITY_LABELS: dict[int, str] = {
    0: "Clean export",
    1: "Minor formatting mess",
    2: "Common finance team mess",
    3: "Messy audit season file",
    4: "Highly chaotic client submission",
    5: "Nightmare PBC file",
}

PROBABILITY_KEYS: tuple[str, ...] = (
    "merged_cells",
    "hidden_rows",
    "hidden_columns",
    "duplicated_headers",
    "inserted_notes",
    "subtotal_rows",
    "wrong_period_rows",
    "renamed_columns",
    "stringified_numbers",
    "formula_errors",
    "multiple_tables_in_one_sheet",
    "old_version_tabs",
    "hidden_reconciliation_tabs",
    "pbc_request_list",
    "tracker_status_noise",
    "tracker_deadline_noise",
    "tracker_visible_comments",
    "tracker_update_highlights",
    "tracker_instruction_blocks",
)

GENERATION_STAGES: tuple[dict[str, Any], ...] = (
    {
        "id": "validate_options",
        "label": "Validate options",
        "weight": 5,
        "notes": "Check required fields, ranges, paths, and command shape",
    },
    {
        "id": "resolve_config",
        "label": "Resolve config",
        "weight": 5,
        "notes": "Load severity defaults, YAML config, and nightmare-mode settings",
    },
    {
        "id": "prepare_companies",
        "label": "Prepare companies",
        "weight": 5,
        "notes": "Build deterministic simulated company profiles",
    },
    {
        "id": "parse_period",
        "label": "Parse period",
        "weight": 5,
        "notes": "Accept FY2025 or 2025",
    },
    {
        "id": "build_financial_truth",
        "label": "Build financial truth",
        "weight": 15,
        "notes": "Create reconciliation context and canonical accounting data",
    },
    {
        "id": "generate_documents",
        "label": "Generate clean documents",
        "weight": 20,
        "notes": "Build PBC tracker and supporting schedules",
    },
    {
        "id": "render_workbook",
        "label": "Render workbook sheets",
        "weight": 15,
        "notes": "Create .xlsx workbook and sheets",
    },
    {
        "id": "apply_layout_chaos",
        "label": "Apply layout chaos",
        "weight": 15,
        "notes": "Insert layout, formatting, tracker, and workbook-level mess",
    },
    {
        "id": "nightmare_post_pass",
        "label": "Apply nightmare post-pass",
        "weight": 10,
        "notes": "Run only when unreproducible nightmare mode is enabled",
    },
    {
        "id": "record_ground_truth",
        "label": "Record ground truth",
        "weight": 5,
        "notes": "Build metadata sidecar content",
    },
    {
        "id": "save_artifacts",
        "label": "Save artifacts",
        "weight": 5,
        "notes": "Write workbook and .groundtruth.json",
    },
    {
        "id": "write_manifest",
        "label": "Write manifest",
        "weight": 3,
        "notes": "Write or rebuild manifest.csv",
    },
    {
        "id": "complete",
        "label": "Complete",
        "weight": 2,
        "notes": "Show artifacts, summary, warnings, and next actions",
    },
)

UTILITY_STAGES: tuple[dict[str, Any], ...] = (
    {"id": "validate_options", "label": "Validate options", "weight": 10},
    {"id": "validate_outputs", "label": "Validate outputs", "weight": 80},
    {"id": "write_manifest", "label": "Write manifest", "weight": 80},
    {"id": "score_extraction", "label": "Score extraction", "weight": 80},
    {"id": "complete", "label": "Complete", "weight": 10},
)


def now_iso() -> str:
    """Return an ISO timestamp in the user's workspace timezone."""

    return datetime.now(ZoneInfo("Asia/Singapore")).isoformat(timespec="seconds")


def generation_stage_index() -> dict[str, dict[str, Any]]:
    """Return generation stages keyed by stable ID."""

    return {stage["id"]: stage for stage in GENERATION_STAGES}

