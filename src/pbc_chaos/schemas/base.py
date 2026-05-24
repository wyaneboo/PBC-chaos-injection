"""Contracts for normalized document schemas.

Normalized schemas describe the clean target shape that messy workbook evidence
should map into. They are intentionally independent from workbook layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pbc_chaos.core.types import DocumentType


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    ENUM = "enum"
    PERCENTAGE = "percentage"
    CURRENCY_CODE = "currency_code"
    IDENTIFIER = "identifier"
    JSON = "json"


class FieldRequirement(str, Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    DERIVED = "derived"
    SYSTEM = "system"


@dataclass(frozen=True)
class NormalizedField:
    name: str
    data_type: FieldType
    requirement: FieldRequirement
    description: str
    concept: str | None = None
    aliases: tuple[str, ...] = field(default_factory=tuple)
    allowed_values: tuple[str, ...] = field(default_factory=tuple)
    nullable: bool = True


@dataclass(frozen=True)
class SchemaRelationship:
    name: str
    target_document_type: DocumentType
    description: str
    join_fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    tolerance: str | None = None


@dataclass(frozen=True)
class DocumentSchema:
    document_type: DocumentType
    display_name: str
    grain: str
    primary_key: tuple[str, ...]
    fields: tuple[NormalizedField, ...]
    relationships: tuple[SchemaRelationship, ...] = field(default_factory=tuple)
    quality_rules: tuple[str, ...] = field(default_factory=tuple)

    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)

    def required_field_names(self) -> tuple[str, ...]:
        return tuple(
            field.name
            for field in self.fields
            if field.requirement == FieldRequirement.REQUIRED
        )


def nf(
    name: str,
    data_type: FieldType,
    requirement: FieldRequirement,
    description: str,
    *,
    concept: str | None = None,
    aliases: tuple[str, ...] = (),
    allowed_values: tuple[str, ...] = (),
    nullable: bool = True,
) -> NormalizedField:
    """Compact field factory for static schema definitions."""
    return NormalizedField(
        name=name,
        data_type=data_type,
        requirement=requirement,
        description=description,
        concept=concept,
        aliases=aliases,
        allowed_values=allowed_values,
        nullable=nullable,
    )

