"""Registry for pluggable document generators."""

from __future__ import annotations

from dataclasses import dataclass, field

from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.base import DocumentGenerator


@dataclass
class DocumentGeneratorRegistry:
    generators: dict[DocumentType, DocumentGenerator] = field(default_factory=dict)

    def register(self, generator: DocumentGenerator) -> None:
        self.generators[generator.document_type] = generator

    def get(self, document_type: DocumentType) -> DocumentGenerator:
        try:
            return self.generators[document_type]
        except KeyError as exc:
            raise KeyError(f"No generator registered for {document_type.value}") from exc

    def enabled(self, document_types: tuple[DocumentType, ...]) -> tuple[DocumentGenerator, ...]:
        return tuple(self.get(document_type) for document_type in document_types)

