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
- `pbc_request_list`: applies a dedicated PBC request tracker layout with
  instruction blocks, owner/status columns, filters, and wrapped tracker rows.
- `tracker_status_noise`: varies client and audit workflow statuses such as
  `Done`, `done`, `received`, `partial`, `not yet`, `pending`, and `Under review`.
- `tracker_deadline_noise`: varies due dates, received dates, and follow-up
  flags with values like `15/5`, `16-May`, `??`, `???`, `Y?`, and blanks.
- `tracker_visible_comments`: adds visible row comments such as missing pages,
  hardcopy-only support, blurry scans, and quantity mismatches.
- `tracker_update_highlights`: highlights rows or cells that look new or updated.
- `tracker_instruction_blocks`: adds prominent client instructions such as PIC,
  submit-by deadline, template reminders, contact notes, and late-submission
  warnings.

## Unreproducible Nightmare Mode

`unreproducible_nightmare_mode` is an optional post-pass for cases where exact
seed reproducibility is less important than realistic human mess.

When enabled, the generator first creates the normal configured workbook, then
runs a non-deterministic LangGraph review agent. If `GEMINI_API_KEY` is set, the
planning node asks the configured Gemma model through the Gemini API to choose
the chaos plan using structured JSON output. If credentials or the API call are
not available, the LangGraph node uses the validated local planner as a
fallback.

The agent chooses extra chaos tool types such as:

- `human_residue_notation`: adds visible notes or Excel comments in random cells.
- `formula_errors`: adds a few extra broken formulas.
- `stringified_numbers`: converts a few more numeric cells into text.
- `hide_rows_columns`: hides extra rows or columns.
- `secondary_table`: adds another small working table.
- `old_version_tab`: adds another old-version copy.
- `hidden_reconciliation_tab`: adds another hidden working tab.
- `add_visible_tracker_comment`: adds a bounded visible tracker comment.
- `apply_tracker_status_variant`: changes a tracker row status to a human-style variant.
- `apply_tracker_deadline_noise`: changes a tracker due date to a mixed or ambiguous value.
- `highlight_tracker_update_row`: highlights a tracker row as new or updated.
- `apply_tracker_follow_up_noise`: changes a tracker follow-up flag.

Example:

```yaml
severity: 5

unreproducible_nightmare_mode:
  enabled: true
  use_llm_planner: true
  llm_model: gemma-4-31b-it
  gemini_api_key_env: GEMINI_API_KEY
  llm_timeout_seconds: 180
  notation_count: 30
  extra_tool_count: 5
  max_notation_length: 96
```

Put the Gemini API key in a local `.env` file in the directory where you run
`pbc-chaos` to enable the Gemma-backed planner:

```dotenv
GEMINI_API_KEY=your-api-key
```

Without `GEMINI_API_KEY`, the feature still runs, but the sidecar metadata will
show `agent_provider: langgraph_heuristic_fallback`.

## API

```python
from config_loader import load_config
from pbc_chaos.pbc_workbook import generate_pbc_workbook

config = load_config("config/unreproducible-nightmare.yaml")
workbook = generate_pbc_workbook(company, period, config=config, seed=42)
```
