from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from Offline_budget_tracker import calculations
from Offline_budget_tracker.db import Settings, Transaction


def _settings(**updates) -> Settings:
    base = Settings(
        starting_balance=10000.0,
        counted_balance=None,
        refunds_total=0.0,
        plan_months_total=9,
        months_elapsed=0,
        rent_base_monthly=0.0,
        rent_monthly_manual=0.0,
        food_house_monthly=100.0,
        misc_monthly=50.0,
        medical_monthly=0.0,
        school_monthly=0.0,
        household_monthly=0.0,
        health_monthly=0.0,
        auto_misc_enabled=False,
        auto_misc_categories=[],
        auto_include_recurring=False,
        auto_include_current_month=False,
        auto_window_months=3,
        auto_weighted=False,
        auto_weight_half_life_months=6,
        extra_monthly=0.0,
        rent_surcharge_amount=0.0,
        rent_surcharge_months=0,
        campus_reference_total=17000.0,
        language="EN",
        theme="Dune",
        font_family="",
        accent_color="",
    )
    for key, value in updates.items():
        setattr(base, key, value)
    return base


def test_savings_vs_campus_uses_plan_horizon_expenses(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings()
    transactions = [
        Transaction(
            id="t-old",
            datetime_local="2024-01-10T12:00:00",
            amount=2000.0,
            type="expense",
            label="old",
            category="misc",
            notes="",
        ),
        Transaction(
            id="t-plan",
            datetime_local="2025-09-10T12:00:00",
            amount=500.0,
            type="expense",
            label="plan",
            category="food",
            notes="",
        ),
    ]
    summary = calculations.calculate_summary(transactions, settings, [])
    expected = settings.campus_reference_total - (
        float(summary["expenses_to_date_plan"]) + float(summary["planned_remaining_total"])
    )
    assert round(float(summary["savings_vs_campus_planned"]), 2) == round(expected, 2)


def test_monthly_stats_include_all_school_year_months(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings()
    transactions = [
        Transaction(
            id="t-plan",
            datetime_local="2025-09-10T12:00:00",
            amount=500.0,
            type="expense",
            label="plan",
            category="food",
            notes="",
        )
    ]
    stats = calculations.calculate_monthly_stats(transactions, settings, [])
    assert len(stats) == 9
    assert stats[0]["month"] == "2025-09"
    assert stats[-1]["month"] == "2026-05"


def test_auto_mode_falls_back_to_manual_when_no_history(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings(
        auto_misc_enabled=True,
        auto_misc_categories=["food", "misc", "medical"],
        food_house_monthly=120.0,
        misc_monthly=80.0,
        medical_monthly=40.0,
    )
    summary = calculations.calculate_summary([], settings, [])
    assert float(summary["predicted_variable_monthly_total"]) == float(
        summary["manual_variable_monthly_total"]
    )


def test_selected_auto_category_without_data_uses_manual_fallback(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings(
        auto_misc_enabled=True,
        auto_misc_categories=["food", "misc"],
        food_house_monthly=120.0,
        misc_monthly=80.0,
        auto_include_current_month=False,
        auto_window_months=3,
    )
    transactions = [
        Transaction(
            id="t-rent",
            datetime_local="2025-12-12T12:00:00",
            amount=900.0,
            type="expense",
            label="rent",
            category="rent",
            notes="",
        ),
    ]
    summary = calculations.calculate_summary(transactions, settings, [])
    # No food/misc category history in selected window -> manual fallback should remain active.
    assert round(float(summary["predicted_variable_monthly_total"]), 2) == round(
        float(summary["manual_variable_monthly_total"]), 2
    )


def test_invalid_transaction_dates_do_not_count_as_current_month(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings()
    transactions = [
        Transaction(
            id="bad-date",
            datetime_local="not-a-date",
            amount=100.0,
            type="expense",
            label="bad",
            category="food",
            notes="",
        )
    ]

    summary = calculations.calculate_summary(transactions, settings, [])

    assert float(summary["total_expenses"]) == 100.0
    assert float(summary["coverage_current_month_expenses"]) == 0.0
    assert float(summary["expenses_to_date_plan"]) == 0.0


def test_rent_income_offsets_current_month_rent(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings()
    transactions = [
        Transaction(
            id="rent-expense",
            datetime_local="2026-01-02T12:00:00",
            amount=900.0,
            type="expense",
            label="January rent",
            category="rent",
            notes="",
        ),
        Transaction(
            id="rent-credit",
            datetime_local="2026-01-03T12:00:00",
            amount=250.0,
            type="income",
            label="rent reimbursement",
            category="income",
            notes="roommate share",
        ),
    ]

    summary = calculations.calculate_summary(transactions, settings, [])
    monthly_stats = calculations.calculate_monthly_stats(transactions, settings, [])
    january = next(item for item in monthly_stats if item["month"] == "2026-01")

    assert float(summary["rent_month_paid_gross"]) == 900.0
    assert float(summary["rent_month_income_offset"]) == 250.0
    assert float(summary["rent_month_paid"]) == 650.0
    assert float(summary["rent_paid_to_date"]) == 650.0
    assert float(january["rent_net"]) == 650.0


def test_rent_income_offsets_rent_auto_average_and_category_average_rows(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 2, 15))
    settings = _settings(
        auto_misc_enabled=True,
        auto_include_current_month=True,
        auto_window_months=2,
    )
    transactions = [
        Transaction(
            id="jan-rent-expense",
            datetime_local="2026-01-02T12:00:00",
            amount=900.0,
            type="expense",
            label="January rent",
            category="rent",
            notes="",
        ),
        Transaction(
            id="jan-rent-credit",
            datetime_local="2026-01-03T12:00:00",
            amount=250.0,
            type="income",
            label="rent reimbursement",
            category="income",
            notes="roommate share",
        ),
        Transaction(
            id="feb-rent-expense",
            datetime_local="2026-02-02T12:00:00",
            amount=900.0,
            type="expense",
            label="February rent",
            category="rent",
            notes="",
        ),
        Transaction(
            id="feb-rent-credit",
            datetime_local="2026-02-03T12:00:00",
            amount=200.0,
            type="income",
            label="rent reimbursement",
            category="income",
            notes="roommate share",
        ),
    ]

    summary = calculations.calculate_summary(transactions, settings, [])
    averages = calculations.calculate_category_average_rows(transactions)
    rows = {row["category"]: row for row in averages["rows"]}

    assert round(float(summary["rent_auto_monthly"]), 2) == 675.0
    assert round(float(rows["Rent"]["total"]), 2) == 1350.0
    assert round(float(rows["Rent"]["average_monthly"]), 2) == 675.0


def test_parent_text_is_not_mistaken_for_rent(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 3, 15))
    settings = _settings()
    transactions = [
        Transaction(
            id="march-rent",
            datetime_local="2026-03-06T00:00:00",
            amount=871.17,
            type="expense",
            label="Rent",
            category="rent",
            notes="",
        ),
        Transaction(
            id="parent-deposit",
            datetime_local="2026-03-09T00:00:41",
            amount=1900.0,
            type="income",
            label="Zelle",
            category="income",
            notes="Parent deposit",
        ),
        Transaction(
            id="actual-rent-credit",
            datetime_local="2026-03-10T00:00:52",
            amount=343.0,
            type="income",
            label="Zelle",
            category="rent",
            notes="Utsho rent",
        ),
    ]

    summary = calculations.calculate_summary(transactions, settings, [])
    monthly_stats = calculations.calculate_monthly_stats(transactions, settings, [])
    march = next(item for item in monthly_stats if item["month"] == "2026-03")

    assert calculations._is_rent_text("Parents") is False
    assert calculations._is_rent_text("Parent deposit") is False
    assert float(summary["rent_month_paid_gross"]) == 871.17
    assert float(summary["rent_month_income_offset"]) == 343.0
    assert round(float(summary["rent_month_paid"]), 2) == 528.17
    assert round(float(march["rent_net"]), 2) == 528.17


def test_category_average_rows_use_months_with_history(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    transactions = [
        Transaction(
            id="food-sep",
            datetime_local="2025-09-10T12:00:00",
            amount=120.0,
            type="expense",
            label="groceries",
            category="food",
            notes="",
        ),
        Transaction(
            id="food-oct",
            datetime_local="2025-10-10T12:00:00",
            amount=60.0,
            type="expense",
            label="groceries",
            category="food",
            notes="",
        ),
        Transaction(
            id="transport-oct",
            datetime_local="2025-10-11T12:00:00",
            amount=40.0,
            type="expense",
            label="bus pass",
            category="transport",
            notes="",
        ),
        Transaction(
            id="excluded-outlier",
            datetime_local="2025-10-12T12:00:00",
            amount=500.0,
            type="expense",
            label="ignored",
            category="food",
            notes="",
            excluded_from_averages=True,
        ),
        Transaction(
            id="income",
            datetime_local="2025-10-13T12:00:00",
            amount=900.0,
            type="income",
            label="paycheck",
            category="income",
            notes="",
        ),
    ]

    stats = calculations.calculate_category_average_rows(transactions)
    rows = {row["category"]: row for row in stats["rows"]}

    assert int(stats["months_count"]) == 2
    assert round(float(rows["Food"]["average_monthly"]), 2) == 90.0
    assert round(float(rows["Food"]["total"]), 2) == 180.0
    assert int(rows["Food"]["months_with_spend"]) == 2
    assert round(float(rows["Transport"]["average_monthly"]), 2) == 20.0
    assert int(rows["Transport"]["months_with_spend"]) == 1


def test_adjustments_affect_balance_but_not_monthly_spend_views(monkeypatch):
    monkeypatch.setattr(calculations, "_local_today", lambda: date(2026, 1, 15))
    settings = _settings(starting_balance=1000.0)
    transactions = [
        Transaction(
            id="groceries",
            datetime_local="2026-01-05T12:00:00",
            amount=100.0,
            type="expense",
            label="Groceries",
            category="food",
            notes="",
        ),
        Transaction(
            id="reconcile-up",
            datetime_local="2026-01-06T12:00:00",
            amount=250.0,
            type="income",
            label="Reconcile adjustment",
            category="adjustment",
            notes="",
        ),
        Transaction(
            id="older-adjustment",
            datetime_local="2025-12-20T12:00:00",
            amount=40.0,
            type="expense",
            label="Reconcile adjustment",
            category="adjustment",
            notes="",
        ),
    ]

    summary = calculations.calculate_summary(transactions, settings, [])
    monthly_stats = calculations.calculate_monthly_stats(transactions, settings, [])
    january = next(item for item in monthly_stats if item["month"] == "2026-01")
    december = next(item for item in monthly_stats if item["month"] == "2025-12")
    averages = calculations.calculate_category_average_rows(transactions)

    assert float(summary["estimated_balance"]) == 1110.0
    assert float(summary["total_income"]) == 250.0
    assert float(summary["total_expenses"]) == 140.0
    assert float(summary["adjustments_total"]) == 210.0
    assert float(summary["current_month_expenses"]) == 100.0
    assert float(summary["current_month_income"]) == 0.0
    assert float(summary["current_month_adjustments"]) == 250.0
    assert float(summary["expenses_to_date_plan"]) == 100.0
    assert float(summary["average_expenses"]) == 20.0
    assert float(january["total_expenses"]) == 100.0
    assert float(january["adjustments_total"]) == 250.0
    assert float(december["adjustments_total"]) == -40.0
    assert [row["category"] for row in averages["rows"]] == ["Food"]
