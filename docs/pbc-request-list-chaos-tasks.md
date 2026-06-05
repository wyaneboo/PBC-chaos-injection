# PBC Request List Chaos Tasks

This task list adds the spreadsheet chaos style seen in client-maintained PBC
request trackers: dense request rows, visible workflow status, inconsistent due
dates, follow-up notes, highlighted updates, and human instruction blocks.

## Goal

Add a `pbc_request_list` sheet type that behaves like a messy audit workflow
tracker, while keeping canonical data, layout chaos, agent planning, and ground
truth responsibilities separated.

## Architecture Decision

Implement the first version through the existing openpyxl workbook path:

- Generate a clean `pbc_request_list` document.
- Render it as the first workbook sheet.
- Apply dedicated tracker-layout chaos after clean data is written.
- Let the unreproducible nightmare agent propose bounded human-language actions.
- Keep workbook structure, formulas, metadata, and validation deterministic in
  Python.

Do not start by refactoring the placeholder `chaos/` injector framework. Once
the feature works end to end, tracker chaos can be moved into formal injectors.

## Core Tasks

1. Add the document type.
   - Add `PBC_REQUEST_LIST = "pbc_request_list"` to `DocumentType`.
   - Register display name `PBC Request List`.
   - Add it to CLI `list-doc-types` automatically through the enum.

2. Add the normalized schema.
   - Add `PBC_REQUEST_LIST_SCHEMA` in `schemas/documents.py`.
   - Include fields:
     - `request_id`
     - `request_description`
     - `detail_remark`
     - `purpose`
     - `period_label`
     - `file_type_requested`
     - `owner_pic`
     - `due_date`
     - `status`
     - `date_received`
     - `review_status`
     - `auditor_comment`
     - `follow_up_required`
     - `update_flag`
   - Add the schema to `ALL_DOCUMENT_SCHEMAS`.

3. Build the clean tracker generator.
   - Create `src/pbc_chaos/generators/pbc_request_list.py`.
   - Generate one row per requested support schedule.
   - Include requests that map to existing generated documents such as Trial
     Balance, General Ledger, AP Aging, AR Aging, Bank Recon, Payroll, Fixed
     Assets, Inventory, Journal Entries, and Expense Claims.
   - Add extra common requests that may not have matching support tabs, such as
     Bank Statement, Customer Confirmation, Supplier Confirmation, Tax
     Computation, GST/SST Report, Related Party Listing, Minutes of Meeting, and
     Subsequent Events Request.
   - Keep clean values normalized before chaos.

4. Insert the tracker into workbook generation.
   - Add the sheet name to `SHEET_NAMES` in `pbc_workbook.py`.
   - Generate the request list before the evidence schedules.
   - Render it as the first visible sheet.
   - Keep evidence sheets unchanged unless explicitly linked by metadata later.

5. Add dedicated tracker layout chaos.
   - Add a tracker-specific path in `layout_engine.apply_layout_chaos`.
   - Prefer a dedicated helper module if the code grows, for example
     `workbook/pbc_tracker_layout.py`.
   - Add top instruction blocks:
     - client name
     - prepared-by-client title
     - period or "as at" label
     - submit-by reminder
     - PIC block
     - contact / question note
     - template reminder
     - late submission warning
   - Add merged cells, wrapped text, borders, and mixed column widths.
   - Freeze panes at the request-table header row.
   - Add AutoFilter on the request table.

6. Add tracker-specific chaos features.
   - `status_variant_noise`: mix `Done`, `done`, `received`, `partial`,
     `not yet`, `not started`, `in progress`, `N/A`, `-`, and blank values.
   - `deadline_noise`: mix real dates, `15/05`, `16-May`, `??`, `???`, blanks,
     and late dates.
   - `received_date_noise`: mix received dates, blanks, dashes, and mismatches
     against status.
   - `review_status_noise`: mix `ok`, `OK`, `pending`, `Under review`,
     misspellings, blanks, and dashes.
   - `follow_up_noise`: mix `Y`, `N`, `Y?`, `Y (remind)`, dashes, and blanks.
   - `request_id_format_noise`: mix `A.1`, `A-3`, `A11`, and `A-12`.
   - `file_type_noise`: mix `Excel`, `xlsx / csv`, `.pdf`, `PDF`,
     `Word / Excel`, `email copy`, `Excel??`, and `Hardcopy only`.
   - `visible_comment_noise`: add short notes in visible auditor/comment
     columns.
   - `updated_row_highlights`: yellow-highlight new or changed rows.
   - `cell_level_emphasis`: add red, green, and purple text, underlines,
     partial bold, and inconsistent capitalization.

7. Keep ground truth useful.
   - Record the final table location starting at the actual request-list header.
   - Track renamed/noisy values where they affect extraction.
   - Record highlighted rows and visible comments as inserted notes.
   - Record ambiguous dates, statuses, and follow-up flags as intentional
     tracker errors.
   - Keep the clean expected extraction output normalized.

8. Extend the nightmare agent with bounded tracker tools.
   - Add allowed planner tools:
     - `add_visible_tracker_comment`
     - `apply_tracker_status_variant`
     - `apply_tracker_deadline_noise`
     - `highlight_tracker_update_row`
     - `apply_tracker_follow_up_noise`
   - The agent should only choose row targets, wording, and small variants.
   - Python should apply all workbook edits and metadata updates.
   - Reject unknown rows, unknown tools, overlong text, and excessive counts.

9. Update configuration.
   - Add probability keys for tracker chaos:
     - `pbc_request_list`
     - `tracker_status_noise`
     - `tracker_deadline_noise`
     - `tracker_visible_comments`
     - `tracker_update_highlights`
     - `tracker_instruction_blocks`
   - Enable them strongly for severity 4 and 5.
   - Enable them by default in `unreproducible-nightmare.yaml`.

10. Add tests.
    - Schema registry includes `pbc_request_list`.
    - Generator produces clean request rows with required columns.
    - Workbook generation includes `PBC Request List` as the first visible sheet.
    - Tracker sheet has instruction blocks, filters, freeze panes, and table
      metadata.
    - Severity 5 applies status/date/follow-up/comment chaos.
    - Nightmare mode records tracker actions in the sidecar.
    - `pbc-chaos validate` passes on a generated nightmare workbook.

## Agent Responsibility Boundary

Good agent responsibilities:

- Write informal comments and reminders.
- Choose which rows look late, unclear, updated, or under review.
- Pick human wording style for finance/audit notes.
- Generate small typo, casing, and phrasing variations.

Bad agent responsibilities:

- Creating workbook structure.
- Setting merged cells, widths, filters, freeze panes, and formulas directly.
- Defining canonical schema.
- Editing arbitrary cells without bounded tool names.
- Creating or mutating ground truth directly.

## Suggested Implementation Order

1. Add enum and schema.
2. Add clean generator.
3. Insert sheet into workbook generation.
4. Add tracker layout rendering.
5. Add deterministic tracker chaos.
6. Add metadata recording.
7. Add bounded nightmare-agent tracker tools.
8. Update configs and docs.
9. Run tests and generate one nightmare workbook for visual inspection.
