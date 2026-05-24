"""Metadata records for generated runs and files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pbc_chaos.chaos.events import ChaosEvent
from pbc_chaos.core.types import DocumentType


@dataclass(frozen=True)
class GeneratedFileRecord:
    file_id: str
    path: Path
    client_id: str
    client_name: str
    financial_year: int
    document_type: DocumentType
    seed: int
    chaos_events: tuple[ChaosEvent, ...] = field(default_factory=tuple)
    relationship_expectations: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    seed: int
    output_dir: Path
    files: tuple[GeneratedFileRecord, ...] = field(default_factory=tuple)
    summary: dict[str, Any] = field(default_factory=dict)

