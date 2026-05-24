# Implementation Roadmap

## Phase 1: Foundation

- Complete YAML loading with override/merge support.
- Implement deterministic seed management.
- Add run manifest creation.
- Add basic CLI commands.

## Phase 2: Canonical Financial Model

- Generate client profiles, vendors, customers, employees, accounts, bank accounts, and assets.
- Generate GL entries.
- Derive Trial Balance, AP, AR, payroll, inventory, tax, and cash flow summaries from canonical data.

## Phase 3: Clean Document Generators

- Implement one clean generator per required document type.
- Use `WorkbookPlan` instead of writing `.xlsx` directly.
- Add document-specific validation expectations.

## Phase 4: Chaos Injection

- Implement structural, semantic, formatting, human residue, data quality, formula, versioning,
  and file naming injectors.
- Ensure each injector emits metadata records.

## Phase 5: Rendering and Validation

- Render plans to `.xlsx` using `openpyxl`.
- Validate files can be opened.
- Validate controlled relationships and intentional discrepancies.

## Phase 6: Batch Runs

- Generate multi-client, multi-year datasets.
- Write run summaries and per-file sidecar metadata.
- Add reproducibility tests around seeds.

