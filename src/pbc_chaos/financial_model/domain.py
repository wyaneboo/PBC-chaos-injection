"""Canonical accounting domain objects.

These objects represent clean source truth before document-specific layout and chaos
are applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Account:
    account_id: str
    code: str
    name: str
    category: str
    normal_balance: str


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    posting_date: date
    account_code: str
    description: str
    debit: Decimal
    credit: Decimal
    source_module: str
    reference: str | None = None


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    name: str
    tax_id: str | None = None


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    tax_id: str | None = None


@dataclass(frozen=True)
class Employee:
    employee_id: str
    name: str
    department: str


@dataclass(frozen=True)
class BankAccount:
    bank_account_id: str
    bank_name: str
    account_number: str
    currency: str


@dataclass(frozen=True)
class InventoryItem:
    item_id: str
    sku: str
    description: str
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class FixedAsset:
    asset_id: str
    description: str
    acquisition_date: date
    cost: Decimal
    accumulated_depreciation: Decimal


@dataclass(frozen=True)
class CanonicalDataset:
    client_id: str
    financial_year: int
    accounts: tuple[Account, ...] = field(default_factory=tuple)
    ledger_entries: tuple[LedgerEntry, ...] = field(default_factory=tuple)
    vendors: tuple[Vendor, ...] = field(default_factory=tuple)
    customers: tuple[Customer, ...] = field(default_factory=tuple)
    employees: tuple[Employee, ...] = field(default_factory=tuple)
    bank_accounts: tuple[BankAccount, ...] = field(default_factory=tuple)
    inventory_items: tuple[InventoryItem, ...] = field(default_factory=tuple)
    fixed_assets: tuple[FixedAsset, ...] = field(default_factory=tuple)

