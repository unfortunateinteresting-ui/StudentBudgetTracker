from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from Offline_budget_tracker import charts
from Offline_budget_tracker.db import Transaction


def test_planned_cumulative_series_uses_monthly_plan_values():
    months, cumulative = charts._planned_cumulative_series(
        [
            {"month": "2025-09", "monthly_budget_planned": 100.0},
            {"month": "2025-10", "monthly_budget_planned": 250.0},
            {"month": "2025-11", "monthly_budget_planned": 50.0},
        ]
    )

    assert months == ["2025-09", "2025-10", "2025-11"]
    assert cumulative == [100.0, 350.0, 400.0]


def test_render_category_averages_returns_png_bytes():
    data = charts.render_category_averages(
        [
            Transaction(
                id="t1",
                datetime_local="2025-09-01T12:00:00",
                amount=120.0,
                type="expense",
                label="groceries",
                category="food",
                notes="",
            ),
            Transaction(
                id="t2",
                datetime_local="2025-10-01T12:00:00",
                amount=80.0,
                type="expense",
                label="train",
                category="transport",
                notes="",
            ),
        ]
    )

    assert isinstance(data, bytes)
    assert data.startswith(b"\x89PNG")


def test_sorted_categories_keeps_every_transaction_category():
    transactions = [
        Transaction(
            id=f"t{index}",
            datetime_local=f"2025-0{(index % 3) + 1}-01T12:00:00",
            amount=10.0 + index,
            type="expense",
            label=f"item-{index}",
            category=category,
            notes="",
        )
        for index, category in enumerate(
            [
                "food",
                "transport",
                "utilities",
                "school",
                "household",
                "health",
                "pets",
                "fees",
            ],
            start=1,
        )
    ]

    monthly = charts._monthly_category_totals(transactions)
    categories = charts._sorted_categories(monthly)

    assert "Other" not in categories
    assert set(categories) == {
        "Food",
        "Transport",
        "Utilities",
        "School",
        "Household",
        "Health",
        "Pets",
        "Fees",
    }


def test_monthly_category_totals_net_rent_income_against_rent_spending():
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

    monthly = charts._monthly_category_totals(transactions)

    assert round(float(monthly["2026-01"]["Rent"]), 2) == 650.0


def test_monthly_category_totals_translate_default_categories_in_french():
    transactions = [
        Transaction(
            id="food-expense",
            datetime_local="2026-01-02T12:00:00",
            amount=40.0,
            type="expense",
            label="groceries",
            category="food",
            notes="",
        ),
        Transaction(
            id="rent-expense",
            datetime_local="2026-01-03T12:00:00",
            amount=900.0,
            type="expense",
            label="Rent",
            category="rent",
            notes="",
        ),
    ]

    monthly = charts._monthly_category_totals(transactions, "FR")

    assert "Nourriture" in monthly["2026-01"]
    assert "Loyer" in monthly["2026-01"]


def test_monthly_category_totals_ignore_adjustments():
    transactions = [
        Transaction(
            id="food-expense",
            datetime_local="2026-01-02T12:00:00",
            amount=40.0,
            type="expense",
            label="groceries",
            category="food",
            notes="",
        ),
        Transaction(
            id="adjustment-expense",
            datetime_local="2026-01-03T12:00:00",
            amount=900.0,
            type="expense",
            label="Reconcile adjustment",
            category="adjustment",
            notes="",
        ),
    ]

    monthly = charts._monthly_category_totals(transactions)

    assert monthly["2026-01"] == {"Food": 40.0}
