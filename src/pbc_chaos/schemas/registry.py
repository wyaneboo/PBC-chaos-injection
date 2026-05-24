"""Registry for normalized document schemas."""

from __future__ import annotations

from pbc_chaos.core.types import DocumentType
from pbc_chaos.schemas.base import DocumentSchema
from pbc_chaos.schemas.documents import ALL_DOCUMENT_SCHEMAS

schema_registry: dict[DocumentType, DocumentSchema] = {
    schema.document_type: schema for schema in ALL_DOCUMENT_SCHEMAS
}


def get_schema(document_type: DocumentType) -> DocumentSchema:
    try:
        return schema_registry[document_type]
    except KeyError as exc:
        raise KeyError(f"No normalized schema registered for {document_type.value}") from exc

