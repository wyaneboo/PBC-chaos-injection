from pathlib import Path

from pbc_chaos.config.settings import settings_from_mapping
from pbc_chaos.core.types import DocumentType
from pbc_chaos.generators.default_registry import build_default_registry
from pbc_chaos.schemas.registry import schema_registry


def test_default_registry_has_all_document_types():
    registry = build_default_registry()

    assert set(registry.generators) == set(DocumentType)


def test_schema_registry_has_all_document_types():
    assert set(schema_registry) == set(DocumentType)


def test_registered_schemas_have_unique_fields_and_valid_primary_keys():
    for schema in schema_registry.values():
        field_names = schema.field_names()

        assert len(field_names) == len(set(field_names)), schema.document_type.value
        assert schema.primary_key, schema.document_type.value
        assert set(schema.primary_key).issubset(field_names), schema.document_type.value
        assert schema.required_field_names(), schema.document_type.value


def test_settings_mapping_loads_required_document_types():
    raw = {
        "run": {"seed": 1, "output_dir": "outputs", "run_name": None},
        "batch": {
            "client_count": 1,
            "financial_years": [2025],
            "locale": "en_MY",
            "currency": "MYR",
        },
        "documents": {"include": ["trial_balance"], "duplicate_versions": True},
        "chaos": {"severity": "medium", "injectors": {}, "probabilities": {}},
        "relationships": {
            "discrepancy_mode": "controlled",
            "max_trial_balance_gl_difference_pct": 0.02,
            "max_bank_recon_difference_amount": 500,
            "max_payroll_summary_difference_pct": 0.015,
            "max_inventory_summary_difference_pct": 0.03,
        },
        "metadata": {
            "write_manifest": True,
            "write_per_file_sidecars": True,
            "format": "json",
        },
        "validation": {
            "open_workbooks": True,
            "check_metadata_consistency": True,
            "check_controlled_relationships": True,
        },
    }

    settings = settings_from_mapping(raw)

    assert settings.run.output_dir == Path("outputs")
    assert settings.documents.include == (DocumentType.TRIAL_BALANCE,)
