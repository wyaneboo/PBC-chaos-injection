Here’s a strong prompt you can give to GPT 5.5 / Codex / Claude Code to build a realistic enterprise-grade PBC Chaos Simulator.

---

Build a production-style “PBC Chaos Simulator” system that generates highly realistic messy audit/customer-submitted Excel files for testing AI-powered audit workflows, document intelligence systems, and financial ETL pipelines.

The system should simulate real-world enterprise audit PBC (Prepared By Client) submissions from chaotic finance departments.

Core Objective:
Generate intentionally messy, inconsistent, human-created financial Excel workbooks that resemble real audit evidence received by auditors from clients.

The generated files should look operationally accumulated over years of human workflows — not randomly corrupted.

The simulator must create realistic chaos patterns commonly seen in:

* audit engagements,
* accounting departments,
* insurance operations,
* finance shared services,
* SME finance teams,
* ERP exports,
* manually maintained spreadsheets.

The simulator should output:

* messy Excel workbooks (.xlsx),
* multiple tabs,
* random formatting,
* inconsistent schemas,
* human comments,
* broken structures,
* duplicated data,
* operational residue.

The system should support batch generation of many simulated clients.

---

# Core Concepts

The simulator must emulate:

* human operational mess,
* inconsistent financial exports,
* poor spreadsheet hygiene,
* evolving file versions,
* audit coordination chaos,
* semi-structured financial evidence.

The files should feel like:
“real files sent by stressed finance teams during audit season.”

---

# Required Financial Document Types

Generate realistic variants of:

* Trial Balance
* General Ledger
* AP Aging
* AR Aging
* Bank Reconciliation
* Payroll Summary
* Payroll Detail
* Fixed Asset Register
* Inventory Listing
* Tax Computation
* SST/GST Report
* Commission Statement
* Insurance Production Report
* Customer Confirmation List
* Supplier Confirmation List
* Cash Flow Summary
* Journal Entry Listing
* Expense Claim Listing

---

# Required Chaos Patterns

Implement configurable chaos injection.

## Structural Chaos

* merged cells,
* hidden rows,
* hidden columns,
* multiple tables in one sheet,
* random blank rows,
* subtotal rows,
* nested headers,
* inconsistent tab layouts,
* shifted tables,
* frozen panes,
* duplicated sheets,
* password-like fake sheet names,
* footer notes inside tables.

## Semantic Chaos

Randomly rename columns:

* “GL”
* “Ledger”
* “Acc Code”
* “A/C”
* “Account”
* “GL No”
* “Account Number”

All should sometimes represent the same concept.

Randomly mix:

* English,
* Malay,
* abbreviations,
* finance shorthand,
* inconsistent terminology.

Example:

* “Amount”
* “Amt”
* “RM”
* “Value”
* “Bal”
* “Closing Balance”

---

## Human Workflow Residue

Add realistic operational residue:

* “pls ignore old version”
* “FINAL FINAL v2”
* “updated after Jason review”
* “pending client confirmation”
* “not tally”
* “revised based on audit query”

Inject:

* comments,
* highlighted cells,
* manual color coding,
* inconsistent fonts,
* accidental notes,
* copied email snippets,
* reminders,
* unresolved remarks.

---

## Data Quality Problems

Generate:

* missing values,
* duplicated rows,
* inconsistent date formats,
* stringified numbers,
* bracket negatives,
* formula errors,
* broken formulas,
* rounding mismatches,
* inconsistent currency formatting,
* mixed decimal separators,
* malformed account codes.

Example:

* RM 1,200.00
* (1,200.00)
* 1.200,00
* 1200
* “1,200 CR”

---

## File Naming Chaos

Generate realistic filenames:

* TB_FINAL.xlsx
* TB_FINAL_v2.xlsx
* TB_FINAL_FINAL.xlsx
* TB_latest_USETHIS.xlsx
* New TB Dec FINAL 2.xlsx
* GL_adj_updated_edited.xlsx

---

# Cross-Document Relationships

The simulator must maintain partially realistic accounting relationships.

Example:

* Trial Balance totals should roughly align with GL totals.
* Bank Reconciliation should almost reconcile but include small discrepancies.
* Inventory listing may intentionally mismatch summary totals.
* Payroll detail should aggregate near payroll summary.

Allow configurable discrepancy injection.

---

# Output Requirements

The system should:

* generate hundreds of files,
* simulate multiple companies,
* simulate different financial years,
* support configurable messiness levels,
* export real .xlsx files,
* preserve formatting and formulas,
* generate metadata describing injected chaos.

---

# Technical Requirements

Use Python.

Preferred libraries:

* openpyxl
* pandas
* numpy
* faker

Architecture Requirements:

* modular chaos injection engine,
* pluggable document generators,
* configurable chaos severity,
* deterministic random seed support,
* extensible schema system.

---

# Advanced Features

Implement:

* multi-sheet workbook relationships,
* fake ERP export patterns,
* fake scanned-sheet style formatting,
* simulated manual adjustments,
* fake audit review marks,
* simulated reviewer annotations,
* hidden reconciliation tabs,
* duplicate-but-slightly-different versions.

---

# AI Testing Goal

The generated datasets should be specifically designed to test:

* document intelligence systems,
* table extraction systems,
* AI audit agents,
* financial ETL pipelines,
* schema normalization engines,
* reconciliation systems,
* layout understanding models,
* semantic column mapping systems.

---

# Deliverables

Generate:

1. Complete Python project structure
2. Chaos injection architecture
3. Workbook generator engine
4. Sample generated workbooks
5. Configurable YAML settings
6. Metadata logging system
7. Example CLI usage
8. Batch simulation pipeline
9. Validation scripts
10. Documentation

The final system should feel like an internal enterprise-grade synthetic audit data generation platform.
