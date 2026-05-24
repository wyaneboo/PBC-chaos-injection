"""Typed configuration contracts for simulator runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pbc_chaos.core.types import ChaosSeverity, DocumentType


@dataclass(frozen=True)
class RunSettings:
    seed: int
    output_dir: Path
    run_name: str | None = None


@dataclass(frozen=True)
class BatchSettings:
    client_count: int
    financial_years: tuple[int, ...]
    locale: str
    currency: str


@dataclass(frozen=True)
class DocumentSettings:
    include: tuple[DocumentType, ...]
    duplicate_versions: bool


@dataclass(frozen=True)
class ChaosSettings:
    severity: ChaosSeverity
    injectors: dict[str, bool] = field(default_factory=dict)
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipSettings:
    discrepancy_mode: str
    max_trial_balance_gl_difference_pct: float
    max_bank_recon_difference_amount: float
    max_payroll_summary_difference_pct: float
    max_inventory_summary_difference_pct: float


@dataclass(frozen=True)
class MetadataSettings:
    write_manifest: bool
    write_per_file_sidecars: bool
    format: str


@dataclass(frozen=True)
class ValidationSettings:
    open_workbooks: bool
    check_metadata_consistency: bool
    check_controlled_relationships: bool


@dataclass(frozen=True)
class SimulatorSettings:
    run: RunSettings
    batch: BatchSettings
    documents: DocumentSettings
    chaos: ChaosSettings
    relationships: RelationshipSettings
    metadata: MetadataSettings
    validation: ValidationSettings
    erp_profiles: dict[str, Any] = field(default_factory=dict)


def load_settings(path: Path) -> SimulatorSettings:
    """Load simulator settings from YAML.

    This is intentionally minimal architecture plumbing. Full config merging and
    validation belongs in the implementation phase.
    """
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install PyYAML to load simulator configuration.") from exc

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return settings_from_mapping(raw)


def settings_from_mapping(raw: dict[str, Any]) -> SimulatorSettings:
    """Build typed settings from a mapping."""
    run = raw["run"]
    batch = raw["batch"]
    documents = raw["documents"]
    chaos = raw["chaos"]
    relationships = raw["relationships"]
    metadata = raw["metadata"]
    validation = raw["validation"]

    return SimulatorSettings(
        run=RunSettings(
            seed=int(run["seed"]),
            output_dir=Path(run["output_dir"]),
            run_name=run.get("run_name"),
        ),
        batch=BatchSettings(
            client_count=int(batch["client_count"]),
            financial_years=tuple(int(year) for year in batch["financial_years"]),
            locale=str(batch["locale"]),
            currency=str(batch["currency"]),
        ),
        documents=DocumentSettings(
            include=tuple(DocumentType(value) for value in documents["include"]),
            duplicate_versions=bool(documents["duplicate_versions"]),
        ),
        chaos=ChaosSettings(
            severity=ChaosSeverity(chaos["severity"]),
            injectors=dict(chaos.get("injectors", {})),
            probabilities=dict(chaos.get("probabilities", {})),
        ),
        relationships=RelationshipSettings(
            discrepancy_mode=str(relationships["discrepancy_mode"]),
            max_trial_balance_gl_difference_pct=float(
                relationships["max_trial_balance_gl_difference_pct"]
            ),
            max_bank_recon_difference_amount=float(
                relationships["max_bank_recon_difference_amount"]
            ),
            max_payroll_summary_difference_pct=float(
                relationships["max_payroll_summary_difference_pct"]
            ),
            max_inventory_summary_difference_pct=float(
                relationships["max_inventory_summary_difference_pct"]
            ),
        ),
        metadata=MetadataSettings(
            write_manifest=bool(metadata["write_manifest"]),
            write_per_file_sidecars=bool(metadata["write_per_file_sidecars"]),
            format=str(metadata["format"]),
        ),
        validation=ValidationSettings(
            open_workbooks=bool(validation["open_workbooks"]),
            check_metadata_consistency=bool(validation["check_metadata_consistency"]),
            check_controlled_relationships=bool(validation["check_controlled_relationships"]),
        ),
        erp_profiles=dict(raw.get("erp_profiles", {})),
    )

