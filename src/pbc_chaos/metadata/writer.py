"""Metadata writer contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pbc_chaos.metadata.records import GeneratedFileRecord, RunManifest


class MetadataWriter(Protocol):
    def write_file_record(self, record: GeneratedFileRecord, output_dir: Path) -> Path:
        """Write sidecar metadata for one generated workbook."""
        ...

    def write_manifest(self, manifest: RunManifest) -> Path:
        """Write run-level manifest metadata."""
        ...


class JsonMetadataWriter:
    """JSON metadata writer placeholder."""

    def write_file_record(self, record: GeneratedFileRecord, output_dir: Path) -> Path:
        raise NotImplementedError("File metadata writing is not implemented yet.")

    def write_manifest(self, manifest: RunManifest) -> Path:
        raise NotImplementedError("Manifest writing is not implemented yet.")

