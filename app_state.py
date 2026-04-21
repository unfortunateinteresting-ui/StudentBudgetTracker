from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Union

from . import calculations
from .db import Database, RecurringCharge, Settings, Transaction


@dataclass
class ComputedAppState:
    settings: Settings
    transactions: List[Transaction]
    recurring_charges: List[RecurringCharge]
    categories: List[str]
    summary: Dict[str, Union[float, str, None]]
    monthly_stats: List[Dict[str, Union[float, str]]]


def load_computed_app_state(db: Database, fallback_categories: List[str]) -> ComputedAppState:
    transactions = db.list_transactions()
    recurring_charges = db.list_recurring_charges()
    settings = db.get_settings()

    candidates: List[str] = []
    candidates.extend(fallback_categories)
    candidates.extend(tx.category for tx in transactions if tx.category)
    candidates.extend(charge.category for charge in recurring_charges if charge.category)
    candidates.extend(getattr(settings, "auto_misc_categories", []) or [])
    if candidates:
        db.ensure_categories(candidates, backup=False)
    categories = db.list_categories() or list(fallback_categories)

    summary = calculations.calculate_summary(transactions, settings, recurring_charges)
    monthly_stats = calculations.calculate_monthly_stats(
        transactions, settings, recurring_charges
    )
    return ComputedAppState(
        settings=settings,
        transactions=transactions,
        recurring_charges=recurring_charges,
        categories=categories,
        summary=summary,
        monthly_stats=monthly_stats,
    )
