"""Batch pipeline contract and orchestration shell."""

from __future__ import annotations

from dataclasses import dataclass

from pbc_chaos.chaos.engine import ChaosEngine
from pbc_chaos.config.settings import SimulatorSettings
from pbc_chaos.financial_model.builder import FinancialModelBuilder
from pbc_chaos.generators.registry import DocumentGeneratorRegistry
from pbc_chaos.metadata.records import RunManifest
from pbc_chaos.metadata.writer import MetadataWriter
from pbc_chaos.workbook.renderer import WorkbookRenderer


@dataclass
class BatchSimulationPipeline:
    settings: SimulatorSettings
    financial_model_builder: FinancialModelBuilder
    generator_registry: DocumentGeneratorRegistry
    chaos_engine: ChaosEngine
    renderer: WorkbookRenderer
    metadata_writer: MetadataWriter

    def run(self) -> RunManifest:
        raise NotImplementedError("Batch simulation orchestration is not implemented yet.")

