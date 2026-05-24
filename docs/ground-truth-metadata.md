# Ground Truth Metadata

Every exported workbook can be paired with a `.groundtruth.json` file. The sidecar
is designed for objective scoring of AI extraction systems.

## Export API

```python
from pbc_chaos.metadata import export_pbc_workbook

exported = export_pbc_workbook(
    company,
    period,
    output_dir="outputs",
    config="config/nightmare.yaml",
    seed=42,
)
```

The exporter writes:

- `*.xlsx`
- `*.groundtruth.json`

## Metadata Contents

Workbook-level metadata includes:

- `workbook_id`
- `company_id`
- `company_name`
- `financial_period`
- `generated_at`
- `seed`
- `chaos_level`
- `document_types_included`
- `sheet_names`
- `clean_canonical_schemas`
- `injected_discrepancies`
- `intentional_errors`
- `expected_extraction_output`

Each document sheet includes:

- clean canonical schema
- original clean row count
- final messy row count
- main table start/end coordinates
- header row location
- renamed column mapping
- hidden rows and columns
- merged cell ranges
- inserted notes
- intentional errors
- clean expected extraction records

