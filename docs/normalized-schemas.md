# Normalized Financial Document Schemas

These schemas define the clean target shape for every messy PBC workbook type.
They are not Excel layouts. They describe the normalized records that downstream
AI extraction, schema mapping, ETL, and validation systems should try to recover.

The executable schema registry lives in `src/pbc_chaos/schemas`.

## Shared Design

Every document schema includes common context and lineage fields:

- `client_id`
- `client_name`
- `financial_year`
- `period_start`
- `period_end`
- `currency`
- `source_file_name`
- `source_sheet_name`
- `source_row_number`
- `raw_row_hash`
- `extraction_confidence`

Field requirements:

- `required`: required to identify or financially interpret the record.
- `recommended`: strongly preferred, but realistic files may omit it.
- `optional`: useful when available.
- `derived`: calculated from other fields.
- `system`: lineage or AI-testing metadata.

## Document Schemas

### Trial Balance

Grain: one account balance per client, financial year, period end, and account code.

Primary key: `client_id`, `financial_year`, `period_end`, `account_code`

Core fields:

- `account_code`
- `account_name`
- `account_category`
- `normal_balance`
- `opening_debit`
- `opening_credit`
- `period_debit`
- `period_credit`
- `closing_debit`
- `closing_credit`
- `closing_balance`
- `comparative_balance`
- `adjustment_amount`
- `final_balance`
- `remarks`

Relationships:

- GL movements grouped by account should roughly tie to TB period movements.
- Cash flow lines may be derived from TB movements.

### General Ledger

Grain: one posted accounting transaction line.

Primary key: `client_id`, `financial_year`, `entry_id`, `line_number`

Core fields:

- `entry_id`
- `journal_id`
- `line_number`
- `posting_date`
- `document_date`
- `period`
- `account_code`
- `account_name`
- `account_category`
- `debit`
- `credit`
- `amount_signed`
- `counterparty_id`
- `counterparty_name`
- `counterparty_type`
- `source_module`
- `document_number`
- `reference`
- `description`
- `cost_center`
- `department`
- `project_code`
- `tax_code`
- `created_by`
- `posted_by`
- `batch_id`
- `reversal_flag`
- `remarks`

Relationships:

- GL grouped by account should tie to Trial Balance movement columns.
- Journal Entry Listing should be a filtered or annotated view of GL lines.

### AP Aging

Grain: one supplier payable open item at the aging date.

Primary key: `client_id`, `financial_year`, `period_end`, `vendor_id`, `invoice_number`

Core fields:

- `vendor_id`
- `vendor_name`
- `invoice_number`
- `invoice_date`
- `due_date`
- `aging_date`
- `days_past_due`
- `aging_bucket`
- `original_amount`
- `outstanding_amount`
- `current_amount`
- `bucket_1_30`
- `bucket_31_60`
- `bucket_61_90`
- `bucket_over_90`
- `payment_terms`
- `purchase_order_number`
- `hold_flag`
- `disputed_flag`
- `remarks`

Relationships:

- AP Aging total should roughly tie to AP control accounts in the TB.
- Supplier confirmations should sample or summarize AP Aging balances.

### AR Aging

Grain: one customer receivable open item at the aging date.

Primary key: `client_id`, `financial_year`, `period_end`, `customer_id`, `invoice_number`

Core fields:

- `customer_id`
- `customer_name`
- `invoice_number`
- `invoice_date`
- `due_date`
- `aging_date`
- `days_past_due`
- `aging_bucket`
- `original_amount`
- `outstanding_amount`
- `current_amount`
- `bucket_1_30`
- `bucket_31_60`
- `bucket_61_90`
- `bucket_over_90`
- `credit_terms`
- `salesperson`
- `collection_status`
- `disputed_flag`
- `remarks`

Relationships:

- AR Aging total should roughly tie to AR control accounts in the TB.
- Customer confirmations should sample or summarize AR Aging balances.

### Bank Reconciliation

Grain: one bank reconciliation summary or reconciling item line.

Primary key: `client_id`, `financial_year`, `period_end`, `bank_account_id`, `recon_item_id`

Core fields:

- `bank_account_id`
- `bank_name`
- `bank_account_number`
- `recon_item_id`
- `recon_item_type`
- `transaction_date`
- `reference`
- `description`
- `bank_amount`
- `book_amount`
- `difference_amount`
- `statement_balance`
- `book_balance`
- `adjusted_bank_balance`
- `adjusted_book_balance`
- `variance`
- `cleared_flag`
- `matched_gl_entry_id`
- `matched_bank_reference`
- `remarks`

Relationships:

- Book balance should roughly tie to GL cash account balances.
- Ending cash can support Cash Flow Summary reconciliation.

### Payroll Summary

Grain: one payroll run summary by department or pay group.

Primary key: `client_id`, `financial_year`, `pay_run_id`, `department`

Core fields:

- `pay_run_id`
- `pay_period_start`
- `pay_period_end`
- `payment_date`
- `department`
- `employee_count`
- `basic_salary`
- `overtime_amount`
- `allowance_amount`
- `bonus_amount`
- `gross_pay`
- `employee_deductions`
- `employer_contributions`
- `tax_withheld`
- `net_pay`
- `remarks`

Relationships:

- Payroll Detail should aggregate near Payroll Summary by pay run and department.
- Payroll amounts should map to payroll GL postings.

### Payroll Detail

Grain: one employee payroll line per pay run.

Primary key: `client_id`, `financial_year`, `pay_run_id`, `employee_id`

Core fields:

- `pay_run_id`
- `employee_id`
- `employee_name`
- `department`
- `position`
- `pay_period_start`
- `pay_period_end`
- `payment_date`
- `basic_salary`
- `overtime_amount`
- `allowance_amount`
- `bonus_amount`
- `commission_amount`
- `gross_pay`
- `epf_employee`
- `socso_employee`
- `eis_employee`
- `pcb_tax`
- `other_deductions`
- `net_pay`
- `epf_employer`
- `socso_employer`
- `eis_employer`
- `payment_method`
- `bank_account_masked`
- `join_date`
- `termination_date`
- `remarks`

Relationships:

- Aggregates to Payroll Summary by pay run and department.

### Fixed Asset Register

Grain: one fixed asset record at the reporting date.

Primary key: `client_id`, `financial_year`, `period_end`, `asset_id`

Core fields:

- `asset_id`
- `asset_class`
- `asset_description`
- `acquisition_date`
- `in_service_date`
- `supplier_name`
- `invoice_number`
- `location`
- `department`
- `cost`
- `additions`
- `disposals`
- `depreciation_method`
- `useful_life_months`
- `residual_value`
- `accumulated_depreciation_opening`
- `depreciation_current_year`
- `accumulated_depreciation_closing`
- `net_book_value`
- `disposal_date`
- `disposal_proceeds`
- `gain_loss_on_disposal`
- `status`
- `remarks`

Relationships:

- Cost, accumulated depreciation, NBV, and depreciation expense should roughly tie to TB/GL accounts.

### Inventory Listing

Grain: one inventory item, location, and lot/serial balance at the count date.

Primary key: `client_id`, `financial_year`, `period_end`, `sku`, `location`, `lot_serial_number`

Core fields:

- `item_id`
- `sku`
- `item_description`
- `category`
- `warehouse`
- `location`
- `lot_serial_number`
- `quantity_on_hand`
- `uom`
- `unit_cost`
- `total_cost`
- `valuation_method`
- `last_movement_date`
- `obsolete_flag`
- `write_down_amount`
- `physical_count_quantity`
- `variance_quantity`
- `variance_amount`
- `remarks`

Relationships:

- Inventory listing total should roughly tie to inventory GL control account.

### Tax Computation

Grain: one tax computation line or adjustment for the tax year.

Primary key: `client_id`, `financial_year`, `tax_year`, `line_code`

Core fields:

- `tax_year`
- `tax_period`
- `line_code`
- `line_description`
- `accounting_profit_before_tax`
- `tax_adjustment_type`
- `tax_adjustment_amount`
- `adjusted_income`
- `capital_allowance`
- `unabsorbed_losses_brought_forward`
- `chargeable_income`
- `tax_rate`
- `tax_payable`
- `instalments_paid`
- `tax_balance`
- `remarks`

Relationships:

- Tax payable or receivable should roughly tie to tax accounts in TB/GL.
- SST/GST reports may support indirect-tax lines.

### SST/GST Report

Grain: one indirect-tax transaction or return box line.

Primary key: `client_id`, `financial_year`, `reporting_period_end`, `tax_line_id`

Core fields:

- `tax_line_id`
- `reporting_period_start`
- `reporting_period_end`
- `tax_type`
- `tax_code`
- `transaction_date`
- `invoice_number`
- `counterparty_name`
- `counterparty_tax_id`
- `taxable_amount`
- `tax_rate`
- `output_tax`
- `input_tax`
- `exempt_amount`
- `zero_rated_amount`
- `total_invoice_amount`
- `return_box`
- `source_module`
- `remarks`

Relationships:

- Input and output tax should reconcile to GL tax accounts.

### Commission Statement

Grain: one commission earning or clawback line.

Primary key: `client_id`, `financial_year`, `statement_id`, `commission_line_id`

Core fields:

- `statement_id`
- `commission_line_id`
- `agent_id`
- `agent_name`
- `sales_rep_id`
- `sales_rep_name`
- `customer_id`
- `customer_name`
- `policy_number`
- `invoice_number`
- `transaction_date`
- `product_line`
- `gross_revenue`
- `commission_rate`
- `commission_amount`
- `override_commission_amount`
- `clawback_amount`
- `net_commission`
- `payment_status`
- `payment_date`
- `remarks`

Relationships:

- Commission basis should link to Insurance Production Report policies or invoices.
- Commission expense or income should appear in GL postings.

### Insurance Production Report

Grain: one insurance policy, endorsement, renewal, or cancellation production transaction.

Primary key: `client_id`, `financial_year`, `production_id`

Core fields:

- `production_id`
- `policy_number`
- `endorsement_number`
- `transaction_type`
- `effective_date`
- `expiry_date`
- `issue_date`
- `agent_id`
- `agent_name`
- `customer_id`
- `customer_name`
- `product_line`
- `gross_written_premium`
- `net_written_premium`
- `sum_insured`
- `commission_amount`
- `premium_tax`
- `fees`
- `branch`
- `status`
- `remarks`

Relationships:

- Insurance production can drive Commission Statement calculations.
- Premium production should map to revenue, receivable, and tax GL entries.

### Customer Confirmation List

Grain: one customer confirmation request and balance.

Primary key: `client_id`, `financial_year`, `period_end`, `confirmation_id`

Core fields:

- `confirmation_id`
- `customer_id`
- `customer_name`
- `contact_name`
- `contact_email`
- `contact_address`
- `balance_date`
- `ar_balance`
- `invoice_count`
- `sample_selected_flag`
- `confirmation_method`
- `sent_date`
- `response_date`
- `response_status`
- `confirmed_amount`
- `difference_amount`
- `auditor_follow_up_required`
- `remarks`

Relationships:

- Customer confirmation balances should trace to AR Aging by customer.

### Supplier Confirmation List

Grain: one supplier confirmation request and balance.

Primary key: `client_id`, `financial_year`, `period_end`, `confirmation_id`

Core fields:

- `confirmation_id`
- `vendor_id`
- `vendor_name`
- `contact_name`
- `contact_email`
- `contact_address`
- `balance_date`
- `ap_balance`
- `invoice_count`
- `sample_selected_flag`
- `confirmation_method`
- `sent_date`
- `response_date`
- `response_status`
- `confirmed_amount`
- `difference_amount`
- `auditor_follow_up_required`
- `remarks`

Relationships:

- Supplier confirmation balances should trace to AP Aging by supplier.

### Cash Flow Summary

Grain: one cash flow line item for the reporting period.

Primary key: `client_id`, `financial_year`, `period_end`, `line_code`

Core fields:

- `line_code`
- `line_description`
- `cash_flow_category`
- `method`
- `amount_current_period`
- `amount_comparative_period`
- `source_account_codes`
- `subtotal_flag`
- `display_order`
- `remarks`

Relationships:

- Cash flow should be derivable from TB movement and cash account changes.
- Ending cash should align with reconciled cash balances.

### Journal Entry Listing

Grain: one journal entry line with preparation and review metadata.

Primary key: `client_id`, `financial_year`, `journal_id`, `line_number`

Core fields:

- `journal_id`
- `line_number`
- `posting_date`
- `journal_date`
- `journal_type`
- `account_code`
- `account_name`
- `debit`
- `credit`
- `amount_signed`
- `description`
- `reference`
- `prepared_by`
- `approved_by`
- `approval_date`
- `manual_entry_flag`
- `recurring_flag`
- `adjustment_flag`
- `source_module`
- `cost_center`
- `department`
- `remarks`

Relationships:

- Journal Entry Listing should map to GL lines.

### Expense Claim Listing

Grain: one employee expense claim line.

Primary key: `client_id`, `financial_year`, `claim_id`, `line_number`

Core fields:

- `claim_id`
- `line_number`
- `employee_id`
- `employee_name`
- `department`
- `claim_date`
- `receipt_date`
- `expense_date`
- `expense_category`
- `merchant`
- `description`
- `amount_gross`
- `tax_amount`
- `amount_net`
- `reimbursement_status`
- `payment_date`
- `approval_status`
- `approved_by`
- `project_code`
- `cost_center`
- `receipt_available_flag`
- `policy_exception_flag`
- `remarks`

Relationships:

- Approved and paid claims should map to expense and cash/AP GL entries.
- Some reimbursements may be paid through payroll and trace to employee IDs.

