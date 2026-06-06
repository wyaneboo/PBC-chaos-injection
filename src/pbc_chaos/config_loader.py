"""YAML loader for configurable chaos severity."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from random import Random
from typing import Any, Mapping

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import CompanyProfile, FinancialPeriod
from pbc_chaos.workbook.layout_engine import LayoutChaosConfig


SEVERITY_DESCRIPTIONS: dict[int, str] = {
    0: "clean export",
    1: "minor formatting mess",
    2: "common finance team mess",
    3: "messy audit season file",
    4: "highly chaotic client submission",
    5: "nightmare PBC file",
}


@dataclass(frozen=True)
class ChaosProbabilities:
    """Per-sheet probability controls for workbook messiness."""

    merged_cells: float
    hidden_rows: float
    hidden_columns: float
    duplicated_headers: float
    inserted_notes: float
    subtotal_rows: float
    wrong_period_rows: float
    renamed_columns: float
    stringified_numbers: float
    formula_errors: float
    multiple_tables_in_one_sheet: float
    old_version_tabs: float
    hidden_reconciliation_tabs: float
    pbc_request_list: float
    tracker_status_noise: float
    tracker_deadline_noise: float
    tracker_visible_comments: float
    tracker_update_highlights: float
    tracker_instruction_blocks: float

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ChaosProbabilities":
        allowed = {field.name for field in fields(cls)}
        unknown = set(raw) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown probability config keys: {names}")

        values: dict[str, float] = {}
        for key in allowed:
            if key not in raw:
                raise ValueError(f"Missing probability config key: {key}")
            value = raw[key]
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"{key} must be a number between 0 and 1.")
            value = float(value)
            if not 0 <= value <= 1:
                raise ValueError(f"{key} must be between 0 and 1.")
            values[key] = value
        return cls(**values)

    def as_dict(self) -> dict[str, float]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class UnreproducibleNightmareModeConfig:
    """Optional non-deterministic post-pass for extra realistic workbook mess."""

    enabled: bool = False
    use_llm_planner: bool = True
    llm_model: str = "gemma-4-31b-it"
    gemini_api_key_env: str = "GEMINI_API_KEY"
    llm_timeout_seconds: int = 180
    notation_count: int = 24
    extra_tool_count: int = 4
    max_notation_length: int = 96

    @classmethod
    def from_raw(cls, raw: Any) -> "UnreproducibleNightmareModeConfig":
        if raw is None:
            return cls()
        if isinstance(raw, bool):
            return cls(enabled=raw)
        if not isinstance(raw, Mapping):
            raise ValueError("unreproducible_nightmare_mode must be a boolean or mapping.")

        allowed = {field.name for field in fields(cls)}
        unknown = set(raw) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown unreproducible_nightmare_mode config keys: {names}")

        defaults = cls()
        values = {}
        for field_info in fields(cls):
            values[field_info.name] = raw.get(field_info.name, getattr(defaults, field_info.name))
        if not isinstance(values["enabled"], bool):
            raise ValueError("unreproducible_nightmare_mode.enabled must be true or false.")
        if not isinstance(values["use_llm_planner"], bool):
            raise ValueError("unreproducible_nightmare_mode.use_llm_planner must be true or false.")
        for key in ("llm_model", "gemini_api_key_env"):
            value = values[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"unreproducible_nightmare_mode.{key} must be a non-empty string.")
            values[key] = value.strip()
        for key in (
            "notation_count",
            "extra_tool_count",
            "max_notation_length",
            "llm_timeout_seconds",
        ):
            value = values[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"unreproducible_nightmare_mode.{key} must be a non-negative integer.")
        if values["llm_timeout_seconds"] == 0:
            raise ValueError("unreproducible_nightmare_mode.llm_timeout_seconds must be greater than 0.")
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class ChaosWorkbookConfig:
    """Validated Phase 7 config used by workbook generation."""

    severity: int
    probabilities: ChaosProbabilities
    unreproducible_nightmare_mode: UnreproducibleNightmareModeConfig = (
        field(default_factory=UnreproducibleNightmareModeConfig)
    )

    @property
    def severity_description(self) -> str:
        return SEVERITY_DESCRIPTIONS[self.severity]

    def layout_config(
        self,
        *,
        company: CompanyProfile,
        period: FinancialPeriod,
        title: str,
        seed: int | None,
        sheet_index: int,
        hidden_recon_allowed: bool,
        document_type: DocumentType | None = None,
    ) -> LayoutChaosConfig:
        """Convert probability controls into concrete layout mutations for one sheet."""

        if self.severity == 0:
            return LayoutChaosConfig(
                enabled=False,
                client_name=company.company_name,
                financial_year=period.financial_year,
                title=title,
            )

        rng = Random(_sheet_seed(seed, sheet_index))
        p = self.probabilities
        is_tracker = document_type == DocumentType.PBC_REQUEST_LIST
        return LayoutChaosConfig(
            enabled=True,
            client_name=company.company_name,
            prepared_by="Finance close team",
            reviewer_name="Audit Senior",
            financial_year=period.financial_year,
            title=title,
            max_top_shift=max(1, self.severity + 1),
            max_left_shift=max(0, min(4, self.severity)),
            blank_row_count=_count_from_probability(p.inserted_notes, self.severity, rng, max_count=3),
            blank_column_count=_count_from_probability(p.inserted_notes, self.severity, rng, max_count=2),
            merge_cells=_roll(p.merged_cells, rng),
            duplicate_header_count=_count_from_probability(
                p.duplicated_headers,
                self.severity,
                rng,
                max_count=3,
            ),
            subtotal_row_count=_count_from_probability(p.subtotal_rows, self.severity, rng, max_count=3),
            hidden_row_count=_count_from_probability(p.hidden_rows, self.severity, rng, max_count=5),
            hidden_column_count=_count_from_probability(p.hidden_columns, self.severity, rng, max_count=3),
            reviewer_comment_count=_count_from_probability(
                p.inserted_notes,
                self.severity,
                rng,
                max_count=6,
            ),
            add_title_block=_roll(p.inserted_notes, rng),
            add_client_notes_block=_roll(p.inserted_notes, rng),
            add_footer_notes_block=_roll(p.inserted_notes, rng),
            rename_column_count=_count_from_probability(p.renamed_columns, self.severity, rng, max_count=4),
            stringified_number_count=_count_from_probability(
                p.stringified_numbers,
                self.severity,
                rng,
                max_count=8,
            ),
            formula_error_count=_count_from_probability(p.formula_errors, self.severity, rng, max_count=4),
            wrong_period_row_count=_count_from_probability(
                p.wrong_period_rows,
                self.severity,
                rng,
                max_count=3,
            ),
            secondary_table_count=_count_from_probability(
                p.multiple_tables_in_one_sheet,
                self.severity,
                rng,
                max_count=2,
            ),
            add_old_version_tabs=_roll(p.old_version_tabs, rng),
            old_version_tab_count=max(1, min(3, self.severity // 2 + 1)),
            add_hidden_reconciliation_tabs=hidden_recon_allowed
            and _roll(p.hidden_reconciliation_tabs, rng),
            pbc_request_list_layout=is_tracker and _roll(p.pbc_request_list, rng),
            tracker_status_noise=_roll(p.tracker_status_noise, rng),
            tracker_deadline_noise=_roll(p.tracker_deadline_noise, rng),
            tracker_visible_comments=_roll(p.tracker_visible_comments, rng),
            tracker_update_highlights=_roll(p.tracker_update_highlights, rng),
            tracker_instruction_blocks=_roll(p.tracker_instruction_blocks, rng),
        )


DEFAULT_PROBABILITIES_BY_SEVERITY: dict[int, ChaosProbabilities] = {
    0: ChaosProbabilities(
        merged_cells=0.0,
        hidden_rows=0.0,
        hidden_columns=0.0,
        duplicated_headers=0.0,
        inserted_notes=0.0,
        subtotal_rows=0.0,
        wrong_period_rows=0.0,
        renamed_columns=0.0,
        stringified_numbers=0.0,
        formula_errors=0.0,
        multiple_tables_in_one_sheet=0.0,
        old_version_tabs=0.0,
        hidden_reconciliation_tabs=0.0,
        pbc_request_list=0.0,
        tracker_status_noise=0.0,
        tracker_deadline_noise=0.0,
        tracker_visible_comments=0.0,
        tracker_update_highlights=0.0,
        tracker_instruction_blocks=0.0,
    ),
    1: ChaosProbabilities(
        merged_cells=0.10,
        hidden_rows=0.02,
        hidden_columns=0.01,
        duplicated_headers=0.02,
        inserted_notes=0.15,
        subtotal_rows=0.05,
        wrong_period_rows=0.00,
        renamed_columns=0.03,
        stringified_numbers=0.04,
        formula_errors=0.00,
        multiple_tables_in_one_sheet=0.00,
        old_version_tabs=0.05,
        hidden_reconciliation_tabs=0.02,
        pbc_request_list=0.40,
        tracker_status_noise=0.20,
        tracker_deadline_noise=0.15,
        tracker_visible_comments=0.20,
        tracker_update_highlights=0.15,
        tracker_instruction_blocks=0.35,
    ),
    2: ChaosProbabilities(
        merged_cells=0.25,
        hidden_rows=0.08,
        hidden_columns=0.05,
        duplicated_headers=0.08,
        inserted_notes=0.35,
        subtotal_rows=0.18,
        wrong_period_rows=0.04,
        renamed_columns=0.10,
        stringified_numbers=0.12,
        formula_errors=0.03,
        multiple_tables_in_one_sheet=0.05,
        old_version_tabs=0.15,
        hidden_reconciliation_tabs=0.10,
        pbc_request_list=0.65,
        tracker_status_noise=0.40,
        tracker_deadline_noise=0.35,
        tracker_visible_comments=0.40,
        tracker_update_highlights=0.35,
        tracker_instruction_blocks=0.60,
    ),
    3: ChaosProbabilities(
        merged_cells=0.45,
        hidden_rows=0.18,
        hidden_columns=0.12,
        duplicated_headers=0.20,
        inserted_notes=0.55,
        subtotal_rows=0.35,
        wrong_period_rows=0.10,
        renamed_columns=0.22,
        stringified_numbers=0.25,
        formula_errors=0.08,
        multiple_tables_in_one_sheet=0.15,
        old_version_tabs=0.35,
        hidden_reconciliation_tabs=0.25,
        pbc_request_list=0.85,
        tracker_status_noise=0.62,
        tracker_deadline_noise=0.55,
        tracker_visible_comments=0.62,
        tracker_update_highlights=0.55,
        tracker_instruction_blocks=0.80,
    ),
    4: ChaosProbabilities(
        merged_cells=0.65,
        hidden_rows=0.35,
        hidden_columns=0.25,
        duplicated_headers=0.38,
        inserted_notes=0.75,
        subtotal_rows=0.55,
        wrong_period_rows=0.22,
        renamed_columns=0.40,
        stringified_numbers=0.45,
        formula_errors=0.18,
        multiple_tables_in_one_sheet=0.35,
        old_version_tabs=0.55,
        hidden_reconciliation_tabs=0.45,
        pbc_request_list=1.0,
        tracker_status_noise=0.85,
        tracker_deadline_noise=0.78,
        tracker_visible_comments=0.82,
        tracker_update_highlights=0.75,
        tracker_instruction_blocks=1.0,
    ),
    5: ChaosProbabilities(
        merged_cells=0.90,
        hidden_rows=0.60,
        hidden_columns=0.45,
        duplicated_headers=0.65,
        inserted_notes=0.95,
        subtotal_rows=0.80,
        wrong_period_rows=0.45,
        renamed_columns=0.70,
        stringified_numbers=0.70,
        formula_errors=0.35,
        multiple_tables_in_one_sheet=0.65,
        old_version_tabs=0.80,
        hidden_reconciliation_tabs=0.70,
        pbc_request_list=1.0,
        tracker_status_noise=1.0,
        tracker_deadline_noise=1.0,
        tracker_visible_comments=1.0,
        tracker_update_highlights=1.0,
        tracker_instruction_blocks=1.0,
    ),
}


def load_config(path: str | Path) -> ChaosWorkbookConfig:
    """Load and validate a Phase 7 chaos config YAML file."""

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install PyYAML to load chaos configuration files.") from exc

    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a YAML mapping.")
    return config_from_mapping(raw)


def config_from_mapping(raw: Mapping[str, Any]) -> ChaosWorkbookConfig:
    """Build a validated config, applying severity defaults for omitted values."""

    allowed = {"severity", "probabilities", "unreproducible_nightmare_mode"}
    unknown = set(raw) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown config keys: {names}")

    severity = raw.get("severity", 2)
    if isinstance(severity, bool) or not isinstance(severity, int):
        raise ValueError("severity must be an integer from 0 to 5.")
    if severity not in SEVERITY_DESCRIPTIONS:
        raise ValueError("severity must be an integer from 0 to 5.")

    defaults = DEFAULT_PROBABILITIES_BY_SEVERITY[severity].as_dict()
    overrides = raw.get("probabilities") or {}
    if not isinstance(overrides, dict):
        raise ValueError("probabilities must be a mapping.")
    unknown_probabilities = set(overrides) - set(defaults)
    if unknown_probabilities:
        names = ", ".join(sorted(unknown_probabilities))
        raise ValueError(f"Unknown probability config keys: {names}")

    merged = defaults | dict(overrides)
    return ChaosWorkbookConfig(
        severity=severity,
        probabilities=ChaosProbabilities.from_mapping(merged),
        unreproducible_nightmare_mode=UnreproducibleNightmareModeConfig.from_raw(
            raw.get("unreproducible_nightmare_mode")
        ),
    )


def _sheet_seed(seed: int | None, sheet_index: int) -> int:
    base = 0 if seed is None else int(seed)
    return base + sheet_index * 10_003


def _roll(probability: float, rng: Random) -> bool:
    return rng.random() < probability


def _count_from_probability(
    probability: float,
    severity: int,
    rng: Random,
    *,
    max_count: int,
) -> int:
    if not _roll(probability, rng):
        return 0
    if severity <= 1:
        return 1
    upper = max(1, min(max_count, 1 + severity // 2))
    return rng.randint(1, upper)
