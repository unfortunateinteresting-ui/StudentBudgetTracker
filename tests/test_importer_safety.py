from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from Offline_budget_tracker import importer, reports
from Offline_budget_tracker import db as db_module
from Offline_budget_tracker.db import DEFAULT_SETTINGS, RecurringCharge, Transaction


class StubDB:
    def __init__(self) -> None:
        self.transactions = []
        self.recurring_charges = []
        self.categories = set()
        self.settings_updates = {}
        self.backed_up = False

    def list_transactions(self):
        return list(self.transactions)

    def add_transactions_bulk(self, transactions, backup=True, preserve_ids=False):
        for raw in transactions:
            tx_id = str(raw.get("id") or f"generated-{len(self.transactions) + 1}")
            self.transactions.append(
                Transaction(
                    id=tx_id,
                    datetime_local=str(raw["datetime_local"]),
                    amount=float(raw["amount"]),
                    type=str(raw["type"]),
                    label=str(raw.get("label", "")),
                    category=str(raw.get("category", "")),
                    notes=str(raw.get("notes", "")),
                    recurring_id=str(raw.get("recurring_id") or "").strip() or None,
                    excluded_from_averages=bool(
                        raw.get("excluded_from_averages", False)
                    ),
                )
            )
        return len(transactions)

    def list_recurring_charges(self):
        return list(self.recurring_charges)

    def insert_recurring_charge_with_id(self, charge, backup=True):
        self.recurring_charges.append(charge)

    def ensure_categories(self, names, backup=True):
        before = len(self.categories)
        for name in names:
            text = str(name).strip()
            if text:
                self.categories.add(text)
        return len(self.categories) - before

    def update_settings(self, updates, backup=True):
        self.settings_updates = dict(updates)

    def backup_now(self):
        self.backed_up = True


def _sample_summary() -> dict:
    return {
        "estimated_balance": 100.0,
        "total_expenses": 10.0,
        "total_income": 25.0,
        "plan_budget_total": 120.0,
        "projected_final_expenses": 110.0,
        "planned_remaining_total": 50.0,
        "predicted_remaining_total": 40.0,
        "base_rent_total": 900.0,
        "food_total": 200.0,
        "essential_budget_total_planned": 900.0,
        "essential_budget_total_predicted": 850.0,
        "savings_vs_campus_planned": 100.0,
        "savings_vs_campus_predicted": 120.0,
        "rent_paid_to_date": 900.0,
        "essential_month_used_pct_planned": 10.0,
        "essential_month_used_pct_predicted": 12.0,
        "essential_year_used_pct_planned": 10.0,
        "essential_year_used_pct_predicted": 12.0,
        "rent_month_used_pct_planned": 50.0,
        "rent_month_used_pct_predicted": 50.0,
        "rent_year_used_pct_planned": 50.0,
        "rent_year_used_pct_predicted": 50.0,
        "months_remaining": 6,
        "rent_remaining_total": 5400.0,
        "cap_nonrent_per_month": 100.0,
        "coverage_display": "ok",
        "coverage_12mo_display": "ok12",
    }


def test_normalize_datetime_invalid_raises_value_error():
    try:
        importer._normalize_datetime("not-a-datetime")
    except ValueError as exc:
        assert "datetime_local" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid datetime to raise ValueError")


def test_normalize_transaction_invalid_amount_does_not_raise():
    tx = importer._normalize_transaction(
        {
            "datetime_local": "2026-01-05T09:30:00",
            "amount": "abc",
            "type": "weird",
            "label": "x",
            "category": "misc",
            "notes": "",
        }
    )
    assert tx["amount"] == 0.0
    assert tx["type"] == "expense"


def test_import_from_files_skips_invalid_dates_and_preserves_transaction_ids(tmp_path):
    payload = {
        "transactions": [
            {
                "id": "tx-keep",
                "datetime_local": "2026-01-05T09:30:00",
                "amount": 25.0,
                "type": "expense",
                "label": "Groceries",
                "category": "food",
                "notes": "",
                "recurring_id": "rec-1",
            },
            {
                "id": "tx-bad",
                "datetime_local": "bad-date",
                "amount": 13.0,
                "type": "expense",
                "label": "Broken",
                "category": "misc",
                "notes": "",
            },
        ]
    }
    json_path = tmp_path / "budget_history_export.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    db = StubDB()
    result = importer.import_from_files(db, json_path=json_path)

    assert result.added == 1
    assert result.invalid_transactions == 1
    assert db.transactions[0].id == "tx-keep"
    assert db.transactions[0].recurring_id == "rec-1"
    assert db.transactions[0].notes == ""
    assert db.backed_up is True


def test_import_from_files_keeps_same_amount_rows_when_notes_differ(tmp_path):
    payload = {
        "transactions": [
            {
                "datetime_local": "2026-01-05T09:30:00",
                "amount": 12.5,
                "type": "expense",
                "label": "Coffee",
                "category": "food",
                "notes": "morning",
            },
            {
                "datetime_local": "2026-01-05T09:30:00",
                "amount": 12.5,
                "type": "expense",
                "label": "Coffee",
                "category": "food",
                "notes": "afternoon",
            },
        ]
    }
    json_path = tmp_path / "budget_history_export.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    db = StubDB()
    result = importer.import_from_files(db, json_path=json_path)

    assert result.added == 2
    assert [tx.notes for tx in db.transactions] == ["morning", "afternoon"]


def test_import_from_directory_accepts_single_excel_export(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    workbook = openpyxl.Workbook()
    settings_sheet = workbook.active
    settings_sheet.title = "Settings"
    settings_sheet.append(["Field", "Value"])
    settings_sheet.append(["Starting balance", 125.5])
    settings_sheet.append(["Language", "EN"])

    tx_sheet = workbook.create_sheet("Transactions")
    tx_sheet.append(["Date", "Type", "Amount", "Label", "Category", "Notes"])
    tx_sheet.append(["2026-02-01T12:00:00", "Expense", 18.0, "Lunch", "Food", ""])
    tx_sheet.append(["bad-date", "Expense", 9.0, "Broken", "Misc", ""])

    excel_path = tmp_path / "budget_export_20260201.xlsx"
    workbook.save(excel_path)
    workbook.close()

    db = StubDB()
    result = importer.import_from_directory(db, tmp_path)

    assert result.added == 1
    assert result.invalid_transactions == 1
    assert db.transactions[0].type == "expense"
    assert db.transactions[0].category == "food"
    assert db.settings_updates["starting_balance"] == 125.5
    assert db.settings_updates["language"] == "EN"


def test_import_from_files_reads_french_excel_export(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    workbook = openpyxl.Workbook()
    settings_sheet = workbook.active
    settings_sheet.title = "Reglages"
    settings_sheet.append(["Champ", "Valeur"])
    settings_sheet.append(["Solde initial", 44.25])
    settings_sheet.append(["Langue", "FR"])

    tx_sheet = workbook.create_sheet("Transactions")
    tx_sheet.append(["Date", "Type", "Montant", "Libelle", "Categorie", "Notes"])
    tx_sheet.append(["2026-03-05T09:30:00", "Depense", 25.0, "Epicerie", "Nourriture", ""])
    tx_sheet.append(["2026-03-06T10:00:00", "Revenu", 10.0, "Remboursement", "Revenu", ""])

    excel_path = tmp_path / "budget_export_fr.xlsx"
    workbook.save(excel_path)
    workbook.close()

    db = StubDB()
    result = importer.import_from_files(db, excel_path=excel_path)

    assert result.added == 2
    assert db.transactions[0].type == "expense"
    assert db.transactions[0].category == "food"
    assert db.transactions[1].type == "income"
    assert db.transactions[1].category == "income"
    assert db.settings_updates["starting_balance"] == 44.25
    assert db.settings_updates["language"] == "FR"


def test_export_excel_round_trip_preserves_full_data(tmp_path):
    pytest.importorskip("openpyxl")

    settings = replace(
        DEFAULT_SETTINGS,
        counted_balance=321.5,
        refunds_total=25.0,
        auto_misc_enabled=True,
        auto_misc_categories=["fees", "travel"],
        auto_include_recurring=True,
        auto_include_current_month=False,
        auto_window_months=5,
        auto_weighted=True,
        auto_weight_half_life_months=4,
        extra_monthly=33.0,
        language="FR",
        theme="Ocean",
        font_family="Aptos",
        accent_color="#123456",
    )
    transactions = [
        Transaction(
            id="tx-1",
            datetime_local="2026-03-01T09:00:00",
            amount=10.0,
            type="expense",
            label="Cafe",
            category="food",
            notes="note",
            recurring_id="rec-1",
            excluded_from_averages=True,
        ),
        Transaction(
            id="tx-2",
            datetime_local="2026-03-02T10:00:00",
            amount=20.0,
            type="income",
            label="Pay",
            category="income",
            notes="salary",
        ),
    ]
    recurring = [
        RecurringCharge(
            id="rec-1",
            label="Rent",
            amount=900.0,
            type="expense",
            category="rent",
            notes="lease",
            start_date="2026-01-01",
            end_date=None,
            status="automatic",
            frequency="monthly",
            last_applied="2026-03-01",
        )
    ]
    monthly_stats = [
        {"month": "2026-03", "total_expenses": 10.0, "delta_amount": 0.0, "delta_pct": 0.0}
    ]
    excel_path = tmp_path / "budget_export.xlsx"

    reports.export_excel(
        str(excel_path),
        settings,
        transactions,
        _sample_summary(),
        monthly_stats,
        recurring,
        ["food", "income", "rent", "custom"],
    )

    db = StubDB()
    result = importer.import_from_files(db, excel_path=excel_path)

    assert result.added == 2
    assert result.recurring_added == 1
    assert result.settings_updated is True
    assert [tx.id for tx in db.transactions] == ["tx-1", "tx-2"]
    assert db.transactions[0].recurring_id == "rec-1"
    assert db.transactions[0].excluded_from_averages is True
    assert db.recurring_charges[0].id == "rec-1"
    assert db.recurring_charges[0].category == "rent"
    assert db.settings_updates["counted_balance"] == 321.5
    assert db.settings_updates["auto_misc_categories"] == ["fees", "travel"]
    assert db.settings_updates["auto_include_recurring"] is True
    assert db.settings_updates["auto_include_current_month"] is False
    assert db.settings_updates["theme"] == "Ocean"
    assert db.settings_updates["font_family"] == "Aptos"
    assert db.settings_updates["accent_color"] == "#123456"
    assert "custom" in db.categories


def test_export_excel_round_trip_preserves_large_hidden_payload(tmp_path):
    pytest.importorskip("openpyxl")

    settings = replace(
        DEFAULT_SETTINGS,
        starting_balance=9287.0,
        counted_balance=2900.0,
        language="EN",
        theme="Dune",
    )
    long_note = "x" * 900
    transactions = [
        Transaction(
            id=f"tx-{index}",
            datetime_local=f"2026-03-{(index % 28) + 1:02d}T09:{index % 60:02d}:00",
            amount=float(index + 1),
            type="expense" if index % 3 else "income",
            label=f"Entry {index}",
            category="food" if index % 2 else "misc",
            notes=f"note-{index}-{long_note}",
            recurring_id="rec-large" if index % 5 == 0 else None,
            excluded_from_averages=bool(index % 4 == 0),
        )
        for index in range(60)
    ]
    recurring = [
        RecurringCharge(
            id="rec-large",
            label="Large recurring",
            amount=500.0,
            type="expense",
            category="rent",
            notes="big payload",
            start_date="2026-01-01",
            end_date=None,
            status="automatic",
            frequency="monthly",
            last_applied="2026-03-01",
        )
    ]
    monthly_stats = [
        {"month": "2026-03", "total_expenses": 10.0, "delta_amount": 0.0, "delta_pct": 0.0}
    ]
    excel_path = tmp_path / "budget_export_large.xlsx"

    reports.export_excel(
        str(excel_path),
        settings,
        transactions,
        _sample_summary(),
        monthly_stats,
        recurring,
        ["food", "misc", "rent"],
    )

    db = StubDB()
    result = importer.import_from_files(db, excel_path=excel_path)

    assert result.added == len(transactions)
    assert result.recurring_added == 1
    assert db.transactions[0].id == "tx-0"
    assert db.transactions[0].recurring_id == "rec-large"
    assert db.transactions[0].excluded_from_averages is True
    assert db.transactions[-1].id == "tx-59"
    assert db.recurring_charges[0].id == "rec-large"
    assert db.settings_updates["starting_balance"] == 9287.0
    assert db.settings_updates["counted_balance"] == 2900.0


def test_database_does_not_migrate_legacy_source_data_without_opt_in(tmp_path, monkeypatch):
    legacy_dir = tmp_path / "legacy_data"
    target_dir = tmp_path / "fresh_data"
    monkeypatch.delenv(db_module.LEGACY_SOURCE_MIGRATION_ENV_VAR, raising=False)
    monkeypatch.setenv(db_module.DATA_DIR_ENV_VAR, str(legacy_dir))

    legacy_db = db_module.Database()
    legacy_db.update_settings({"starting_balance": 4321.0}, backup=False)
    legacy_db.add_transactions_bulk(
        [
            {
                "id": "legacy-tx",
                "datetime_local": "2026-03-01T09:00:00",
                "amount": 50.0,
                "type": "expense",
                "label": "Legacy row",
                "category": "misc",
                "notes": "",
            }
        ],
        backup=False,
        preserve_ids=True,
    )
    legacy_db._conn.close()

    monkeypatch.setenv(db_module.DATA_DIR_ENV_VAR, str(target_dir))
    monkeypatch.setattr(db_module, "_legacy_source_data_dir", lambda: legacy_dir)

    fresh_db = db_module.Database()
    try:
        assert fresh_db.list_transactions() == []
        assert (
            fresh_db.get_settings().starting_balance
            == db_module.DEFAULT_SETTINGS.starting_balance
        )
    finally:
        fresh_db._conn.close()


def test_import_updates_settings_in_legacy_singleton_database(tmp_path, monkeypatch):
    data_dir = tmp_path / "legacy_singleton_data"
    data_dir.mkdir()
    monkeypatch.setenv(db_module.DATA_DIR_ENV_VAR, str(data_dir))
    monkeypatch.delenv(db_module.LEGACY_SOURCE_MIGRATION_ENV_VAR, raising=False)

    legacy_db_path = data_dir / "budget.db"
    conn = sqlite3.connect(legacy_db_path)
    conn.execute(
        """
        CREATE TABLE settings (
            id TEXT PRIMARY KEY CHECK (id = 'singleton'),
            starting_balance REAL NOT NULL,
            refunds_total REAL NOT NULL,
            plan_months_total INTEGER NOT NULL,
            months_elapsed INTEGER NOT NULL,
            rent_base_monthly REAL NOT NULL,
            food_house_monthly REAL NOT NULL,
            rent_surcharge_amount REAL NOT NULL,
            rent_surcharge_months INTEGER NOT NULL,
            campus_reference_total REAL NOT NULL,
            language TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO settings (
            id,
            starting_balance,
            refunds_total,
            plan_months_total,
            months_elapsed,
            rent_base_monthly,
            food_house_monthly,
            rent_surcharge_amount,
            rent_surcharge_months,
            campus_reference_total,
            language
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("singleton", 0.0, 0.0, 9, 0, 650.0, 200.0, 144.0, 3, 17256.0, "EN"),
    )
    conn.commit()
    conn.close()

    payload = {
        "settings": {"starting_balance": 9287.0, "language": "EN"},
        "transactions": [
            {
                "id": "imported-tx",
                "datetime_local": "2026-03-01T09:00:00",
                "amount": 50.0,
                "type": "expense",
                "label": "Groceries",
                "category": "food",
                "notes": "",
            }
        ],
    }
    json_path = tmp_path / "legacy_singleton_import.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    real_db = db_module.Database()
    try:
        result = importer.import_from_files(real_db, json_path=json_path)
        settings = real_db.get_settings()
        row = real_db._conn.execute(
            "SELECT CAST(id AS TEXT) AS id_text, starting_balance FROM settings"
        ).fetchone()

        assert result.settings_updated is True
        assert result.added == 1
        assert settings.starting_balance == 9287.0
        assert row["id_text"] == "1"
        assert row["starting_balance"] == 9287.0
        assert len(real_db.list_transactions()) == 1
    finally:
        real_db._conn.close()
