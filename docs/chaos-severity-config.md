# Chaos Severity Configuration

Phase 7 uses `config/*.yaml` files to control workbook messiness from 0 to 5.

## Severity

- `0`: clean export
- `1`: minor formatting mess
- `2`: common finance team mess
- `3`: messy audit season file
- `4`: highly chaotic client submission
- `5`: nightmare PBC file

## Probability Options

Each probability must be between `0` and `1`. Missing probability values inherit
from the selected severity profile.

- `merged_cells`: adds merged title/footer cells around the main table.
- `hidden_rows`: hides non-header data rows.
- `hidden_columns`: hides non-key table columns.
- `duplicated_headers`: inserts repeated header rows inside long schedules.
- `inserted_notes`: adds title blocks, client notes, footer notes, blank separators, and comments.
- `subtotal_rows`: inserts manual subtotal rows with formulas.
- `wrong_period_rows`: copies selected rows and shifts date/year fields outside the reporting period.
- `renamed_columns`: replaces canonical headers with finance-team shorthand.
- `stringified_numbers`: converts selected numeric cells to text.
- `formula_errors`: injects broken formulas such as `#REF!`.
- `multiple_tables_in_one_sheet`: adds small side tables below the main support schedule.
- `old_version_tabs`: adds visible old-version copies of selected sheets.
- `hidden_reconciliation_tabs`: adds hidden client working/reconciliation tabs.

## API

```python
from config_loader import load_config
from pbc_chaos.pbc_workbook import generate_pbc_workbook

config = load_config("config/nightmare.yaml")
workbook = generate_pbc_workbook(company, period, config=config, seed=42)
```

