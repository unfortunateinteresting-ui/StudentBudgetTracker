from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
import math
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from .db import RecurringCharge, Settings, Transaction


def _try_parse_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _parse_datetime(value: str) -> datetime:
    parsed = _try_parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid datetime value: {value!r}")
    return parsed


def _local_today() -> date:
    return datetime.now().date()


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _add_months(year: int, month: int, increment: int) -> Tuple[int, int]:
    total_months = month - 1 + increment
    new_year = year + total_months // 12
    new_month = total_months % 12 + 1
    return new_year, new_month


def _month_iter(start_year: int, start_month: int, count: int) -> List[Tuple[int, int]]:
    months: List[Tuple[int, int]] = []
    current_year, current_month = start_year, start_month
    for _ in range(max(count, 0)):
        months.append((current_year, current_month))
        current_year, current_month = _add_months(current_year, current_month, 1)
    return months


def _coverage_months(balance: float, monthly_budgets: List[float]) -> float:
    covered = 0.0
    remaining = balance
    for budget in monthly_budgets:
        if budget < 0:
            # A negative monthly budget means net surplus for that month.
            remaining -= budget
            covered += 1.0
            continue
        if budget == 0:
            covered += 1.0
            continue
        if remaining >= budget:
            remaining -= budget
            covered += 1.0
            continue
        covered += max(remaining, 0.0) / budget
        return covered
    return covered


def _format_coverage_value(value: float, sigfigs: int = 2) -> str:
    if not math.isfinite(value):
        return str(value)
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    order = math.floor(math.log10(value))
    shift = sigfigs - 1 - order
    rounded = round(value, shift)
    if shift > 0:
        text = f"{rounded:.{shift}f}"
        text = text.rstrip("0").rstrip(".")
    else:
        text = f"{rounded:.0f}"
    return f"{sign}{text}"


def _month_bounds(year: int, month: int) -> Tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _month_offset(
    start_year: int, start_month: int, year: int, month: int
) -> int:
    return (year - start_year) * 12 + (month - start_month)


SCHOOL_YEAR_START_MONTH = 9
RENT_KEYWORDS = ("rent", "loyer")
ADJUSTMENT_CATEGORIES = {"adjustment", "ajustement"}
FOOD_KEYWORDS = ("food", "grocery", "grocer", "restaurant", "meal", "cafe", "diner")
MISC_KEYWORDS = ("misc", "miscellaneous", "other", "extra")
MEDICAL_KEYWORDS = ("medical", "med", "doctor", "clinic", "hospital", "pharmacy", "therapy", "dental", "dentist")
SCHOOL_KEYWORDS = ("school", "tuition", "class", "course", "book", "textbook", "supplies", "campus", "lab")
HOUSEHOLD_KEYWORDS = ("household", "home", "clean", "cleaning", "supplies", "furniture", "appliance")
HEALTH_KEYWORDS = ("health", "gym", "fitness", "insurance", "wellness", "healthcare")


def _contains_keywords(value: str, keywords: Tuple[str, ...]) -> bool:
    lowered = (value or "").strip().lower()
    return any(keyword in lowered for keyword in keywords)


def _is_rent_text(value: str) -> bool:
    lowered = (value or "").strip().lower()
    if not lowered:
        return False
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", lowered)
        for keyword in RENT_KEYWORDS
    )


def _is_food_text(value: str) -> bool:
    return _contains_keywords(value, FOOD_KEYWORDS)


def _is_misc_text(value: str) -> bool:
    return _contains_keywords(value, MISC_KEYWORDS)


def _is_medical_text(value: str) -> bool:
    return _contains_keywords(value, MEDICAL_KEYWORDS)


def _is_school_text(value: str) -> bool:
    return _contains_keywords(value, SCHOOL_KEYWORDS)


def _is_household_text(value: str) -> bool:
    return _contains_keywords(value, HOUSEHOLD_KEYWORDS)


def _is_health_text(value: str) -> bool:
    return _contains_keywords(value, HEALTH_KEYWORDS)


def _is_essential_text(value: str) -> bool:
    return any(
        (
            _is_food_text(value),
            _is_medical_text(value),
            _is_school_text(value),
            _is_household_text(value),
            _is_health_text(value),
        )
    )


def _is_rent_charge(charge: RecurringCharge) -> bool:
    return any(
        _is_rent_text(value)
        for value in [charge.category, charge.label, charge.notes or ""]
    )


def _is_rent_tx(tx: Transaction) -> bool:
    return any(
        _is_rent_text(value)
        for value in [tx.category, tx.label, tx.notes or ""]
    )


def _is_rent_credit_tx(tx: Transaction) -> bool:
    return tx.type == "income" and _is_rent_tx(tx)


def _rent_category_key(tx: Optional[Transaction] = None) -> str:
    if tx and _is_rent_text(tx.category or ""):
        normalized = _normalize_category(tx.category)
        if normalized:
            return normalized
    return "rent"


def _rent_category_display(tx: Optional[Transaction] = None) -> str:
    if tx and _is_rent_text(tx.category or ""):
        display = (tx.category or "").strip()
        if display:
            return display.title()
    return "Rent"


def _is_food_tx(tx: Transaction) -> bool:
    return (
        _is_food_text(tx.category)
        or _is_food_text(tx.label)
        or _is_food_text(tx.notes or "")
    )


def _is_essential_tx(tx: Transaction) -> bool:
    return any(
        _is_essential_text(value)
        for value in [tx.category, tx.label, tx.notes or ""]
    )


def _scheduled_monthly_date(start_date: date, year: int, month: int) -> date:
    _, month_end = _month_bounds(year, month)
    day = min(start_date.day, month_end.day)
    return date(year, month, day)


def _count_occurrences_in_range(
    charge: RecurringCharge, period_start: date, period_end: date
) -> int:
    if charge.status == "paused":
        return 0
    start_date = _parse_date(charge.start_date)
    end_date = _parse_date(charge.end_date)
    if start_date is None:
        return 0
    effective_start = max(start_date, period_start)
    effective_end = min(end_date, period_end) if end_date else period_end
    if effective_start > effective_end:
        return 0

    frequency = (charge.frequency or "monthly").strip().lower()
    if frequency == "daily":
        return (effective_end - effective_start).days + 1
    if frequency == "weekly":
        delta_days = (effective_start - start_date).days
        if delta_days <= 0:
            first = start_date
        else:
            offset = delta_days % 7
            first = (
                effective_start
                if offset == 0
                else effective_start + timedelta(days=7 - offset)
            )
        if first > effective_end:
            return 0
        return 1 + (effective_end - first).days // 7

    scheduled = _scheduled_monthly_date(
        start_date, period_start.year, period_start.month
    )
    if scheduled < effective_start or scheduled > effective_end:
        return 0
    return 1


def _count_occurrences_in_month(
    charge: RecurringCharge, month_start: date, month_end: date
) -> int:
    return _count_occurrences_in_range(charge, month_start, month_end)


def _rent_schedule(
    recurring_charges: Iterable[RecurringCharge],
    months: List[Tuple[int, int]],
) -> Dict[str, float]:
    schedule: Dict[str, float] = {}
    rent_charges = [
        charge
        for charge in recurring_charges
        if _is_rent_charge(charge)
    ]
    for year, month in months:
        month_start, month_end = _month_bounds(year, month)
        total = 0.0
        for charge in rent_charges:
            occurrences = _count_occurrences_in_month(charge, month_start, month_end)
            if occurrences:
                total += float(charge.amount) * occurrences
        schedule[_month_key(year, month)] = total
    return schedule


def _recurring_expense_schedule(
    recurring_charges: Iterable[RecurringCharge],
    months: List[Tuple[int, int]],
) -> Dict[str, float]:
    schedule: Dict[str, float] = {}
    expense_charges = [
        charge for charge in recurring_charges if charge.type == "expense"
    ]
    for year, month in months:
        month_start, month_end = _month_bounds(year, month)
        total = 0.0
        for charge in expense_charges:
            occurrences = _count_occurrences_in_month(charge, month_start, month_end)
            if occurrences:
                total += float(charge.amount) * occurrences
        schedule[_month_key(year, month)] = total
    return schedule


def _legacy_rent_schedule(
    months: List[Tuple[int, int]],
    settings: Settings,
    plan_start_year: int,
    plan_start_month: int,
) -> Dict[str, float]:
    schedule: Dict[str, float] = {}
    for year, month in months:
        offset = _month_offset(plan_start_year, plan_start_month, year, month)
        if offset < 0 or offset >= settings.plan_months_total:
            schedule[_month_key(year, month)] = 0.0
            continue
        rent_amount = settings.rent_base_monthly
        if offset < settings.rent_surcharge_months:
            rent_amount += settings.rent_surcharge_amount
        schedule[_month_key(year, month)] = rent_amount
    return schedule


def _plan_start(settings: Settings, today: date) -> Tuple[int, int]:
    start_month = SCHOOL_YEAR_START_MONTH
    start_year = today.year if today.month >= start_month else today.year - 1
    return start_year, start_month


def _normalize_category(value: str) -> str:
    return (value or "").strip().lower()


def _is_adjustment_tx(tx: Transaction) -> bool:
    return _normalize_category(tx.category) in ADJUSTMENT_CATEGORIES


def _adjustment_balance_effect(tx: Transaction) -> float:
    if tx.type == "expense":
        return -float(tx.amount)
    return float(tx.amount)


def _plan_month_context(settings: Settings, today: date) -> Dict[str, object]:
    plan_start_year, plan_start_month = _plan_start(settings, today)
    plan_months = _month_iter(
        plan_start_year, plan_start_month, settings.plan_months_total
    )
    offset = None
    remaining_months: List[Tuple[int, int]] = []
    if plan_months:
        offset = _month_offset(
            plan_start_year, plan_start_month, today.year, today.month
        )
        if offset < 0:
            remaining_months = plan_months
        elif offset >= len(plan_months):
            remaining_months = []
        else:
            remaining_months = plan_months[offset:]
    months_remaining = len(remaining_months)
    months_elapsed_auto = max(
        0, min(settings.plan_months_total, settings.plan_months_total - months_remaining)
    )
    plan_months_to_date: List[Tuple[int, int]] = []
    if plan_months and offset is not None:
        if offset < 0:
            plan_months_to_date = []
        elif offset >= len(plan_months):
            plan_months_to_date = plan_months
        else:
            plan_months_to_date = plan_months[: offset + 1]
    return {
        "plan_start_year": plan_start_year,
        "plan_start_month": plan_start_month,
        "plan_months": plan_months,
        "remaining_months": remaining_months,
        "months_remaining": months_remaining,
        "months_elapsed_auto": months_elapsed_auto,
        "plan_months_to_date": plan_months_to_date,
    }


def _history_month_info(
    transactions: List[Transaction],
    today: date,
    window_months: int,
    plan_months_to_date: Optional[List[Tuple[int, int]]] = None,
    include_current_month: bool = True,
) -> Tuple[int, List[str], Optional[date]]:
    def _filter_current(keys: List[str]) -> List[str]:
        if include_current_month:
            return keys
        current_key = _month_key(today.year, today.month)
        return [key for key in keys if key != current_key]

    window = max(int(window_months or 0), 0)
    if window:
        start_year, start_month = _add_months(
            today.year, today.month, -(window - 1)
        )
        months = _month_iter(start_year, start_month, window)
        keys = _filter_current([_month_key(year, month) for year, month in months])
        return len(keys), keys, date(start_year, start_month, 1)
    if plan_months_to_date:
        keys = _filter_current(
            [_month_key(year, month) for year, month in plan_months_to_date]
        )
        start_year, start_month = plan_months_to_date[0]
        return len(keys), keys, date(start_year, start_month, 1)
    if not transactions:
        return 0, [], None
    valid_dates = [
        parsed.date()
        for tx in transactions
        for parsed in [_try_parse_datetime(tx.datetime_local)]
        if parsed is not None
    ]
    if not valid_dates:
        return 0, [], None
    earliest = min(valid_dates)
    start_year, start_month = earliest.year, earliest.month
    offset = _month_offset(start_year, start_month, today.year, today.month)
    if offset < 0:
        return 0, [], earliest
    months = _month_iter(start_year, start_month, offset + 1)
    keys = _filter_current([_month_key(year, month) for year, month in months])
    return len(keys), keys, earliest


def _month_weight(
    year: int,
    month: int,
    today: date,
    weighted: bool,
    half_life_months: int,
) -> float:
    if not weighted:
        return 1.0
    half_life = max(int(half_life_months or 1), 1)
    age = _month_offset(year, month, today.year, today.month)
    age = max(age, 0)
    return 0.5 ** (age / half_life)


def _auto_category_stats(
    transactions: List[Transaction],
    settings: Settings,
    today: date,
    include_recurring: bool,
    window_months: int,
    weighted: bool,
    half_life_months: int,
    include_current_month: bool = True,
) -> Dict[str, object]:
    selected_raw = [
        str(item).strip()
        for item in settings.auto_misc_categories
        if str(item).strip()
    ]
    selected_map: Dict[str, str] = {}
    for name in selected_raw:
        key = _normalize_category(name)
        if not key:
            continue
        if key not in selected_map:
            selected_map[key] = name
    selected = list(selected_map.values())
    plan_months_to_date = _plan_month_context(settings, today)["plan_months_to_date"]
    months_count, month_keys, earliest = _history_month_info(
        transactions,
        today,
        window_months,
        plan_months_to_date=plan_months_to_date,
        include_current_month=include_current_month,
    )
    month_key_set = set(month_keys)
    totals = {name: 0.0 for name in selected}
    month_category_totals: Dict[str, Dict[str, float]] = {
        month_key: defaultdict(float) for month_key in month_keys
    }
    if selected_map and month_key_set:
        for tx in transactions:
            if _is_adjustment_tx(tx):
                continue
            if tx.type != "expense":
                continue
            if not include_recurring and tx.recurring_id:
                continue
            if getattr(tx, "excluded_from_averages", False):
                continue
            tx_dt = _try_parse_datetime(tx.datetime_local)
            if tx_dt is None:
                continue
            tx_month_key = tx_dt.strftime("%Y-%m")
            if tx_month_key not in month_key_set:
                continue
            category_key = _normalize_category(tx.category)
            if category_key in selected_map:
                display = selected_map[category_key]
                totals[display] += tx.amount
                month_category_totals[tx_month_key][display] += tx.amount
    if not month_keys or not selected:
        monthly = {name: 0.0 for name in selected}
    elif weighted:
        weight_sum = 0.0
        weights_by_month: Dict[str, float] = {}
        for month_key in month_keys:
            year, month = map(int, month_key.split("-"))
            weight = _month_weight(
                year, month, today, weighted, half_life_months
            )
            weights_by_month[month_key] = weight
            weight_sum += weight
        monthly = {}
        for name in selected:
            weighted_total = 0.0
            for month_key in month_keys:
                month_total = month_category_totals.get(month_key, {}).get(name, 0.0)
                weighted_total += month_total * weights_by_month.get(month_key, 0.0)
            monthly[name] = weighted_total / weight_sum if weight_sum else 0.0
    else:
        month_count = len(month_keys)
        monthly = {}
        for name in selected:
            total = 0.0
            for month_key in month_keys:
                total += month_category_totals.get(month_key, {}).get(name, 0.0)
            monthly[name] = total / month_count if month_count else 0.0
    monthly_total = sum(monthly.values())
    total_selected = sum(totals.values())
    return {
        "selected": selected,
        "totals": totals,
        "monthly": monthly,
        "monthly_total": monthly_total,
        "total_selected": total_selected,
        "months_count": months_count,
        "history_month_keys": month_keys,
        "history_start": earliest,
        "history_end": today,
        "include_recurring": include_recurring,
        "weighted": weighted,
        "half_life_months": max(int(half_life_months or 1), 1),
        "window_months": max(int(window_months or 0), 0),
    }


def _auto_keyword_monthly_average(
    transactions: List[Transaction],
    settings: Settings,
    today: date,
    include_recurring: bool,
    window_months: int,
    weighted: bool,
    half_life_months: int,
    matcher,
    credit_matcher=None,
    include_current_month: bool = True,
) -> float:
    plan_months_to_date = _plan_month_context(settings, today)["plan_months_to_date"]
    months_count, month_keys, _ = _history_month_info(
        transactions,
        today,
        window_months,
        plan_months_to_date=plan_months_to_date,
        include_current_month=include_current_month,
    )
    if not month_keys or months_count == 0:
        return 0.0
    month_key_set = set(month_keys)
    month_totals = {month_key: 0.0 for month_key in month_keys}
    for tx in transactions:
        if _is_adjustment_tx(tx):
            continue
        if not include_recurring and tx.recurring_id:
            continue
        if getattr(tx, "excluded_from_averages", False):
            continue
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        tx_month_key = tx_dt.strftime("%Y-%m")
        if tx_month_key not in month_key_set:
            continue
        if tx.type == "expense":
            if matcher(tx):
                month_totals[tx_month_key] += tx.amount
        elif credit_matcher and credit_matcher(tx):
            month_totals[tx_month_key] -= tx.amount
    for month_key, total in list(month_totals.items()):
        month_totals[month_key] = max(0.0, total)
    if not weighted:
        return sum(month_totals.values()) / len(month_keys)
    weight_sum = 0.0
    weighted_total = 0.0
    for month_key in month_keys:
        year, month = map(int, month_key.split("-"))
        weight = _month_weight(year, month, today, weighted, half_life_months)
        weight_sum += weight
        weighted_total += month_totals.get(month_key, 0.0) * weight
    return weighted_total / weight_sum if weight_sum else 0.0


def group_transactions_by_month(transactions: Iterable[Transaction]) -> Dict[str, List[Transaction]]:
    grouped: Dict[str, List[Transaction]] = defaultdict(list)
    for tx in transactions:
        if _is_adjustment_tx(tx):
            continue
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        month_key = tx_dt.strftime("%Y-%m")
        grouped[month_key].append(tx)
    return dict(grouped)


def calculate_category_average_rows(
    transactions: Iterable[Transaction],
) -> Dict[str, Union[int, List[Dict[str, Union[float, int, str]]], List[str]]]:
    monthly_category_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    display_names: Dict[str, str] = {}

    for tx in transactions:
        if _is_adjustment_tx(tx):
            continue
        if getattr(tx, "excluded_from_averages", False):
            continue
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        month_key = tx_dt.strftime("%Y-%m")
        if tx.type == "expense":
            normalized = _normalize_category(tx.category)
            display = (tx.category or "").strip() or "Uncategorized"
            display_names.setdefault(normalized, display.title() if display else "Uncategorized")
            monthly_category_totals[month_key][normalized] += tx.amount
        elif _is_rent_credit_tx(tx):
            normalized = _rent_category_key(tx)
            display_names.setdefault(normalized, _rent_category_display(tx))
            monthly_category_totals[month_key][normalized] -= tx.amount

    for month_data in monthly_category_totals.values():
        for category_key, amount in list(month_data.items()):
            month_data[category_key] = max(0.0, amount)

    month_keys = sorted(monthly_category_totals.keys())
    months_count = len(month_keys)
    if months_count == 0:
        return {
            "months_count": 0,
            "month_keys": [],
            "rows": [],
        }

    totals: Dict[str, float] = defaultdict(float)
    months_with_spend: Dict[str, int] = defaultdict(int)
    latest_month_key = month_keys[-1]

    for month_key in month_keys:
        for category_key, amount in monthly_category_totals[month_key].items():
            totals[category_key] += amount
            if amount > 0.0:
                months_with_spend[category_key] += 1

    rows: List[Dict[str, Union[float, int, str]]] = []
    for category_key, total in totals.items():
        average_monthly = total / months_count if months_count else 0.0
        rows.append(
            {
                "category": display_names.get(category_key, category_key.title()),
                "average_monthly": average_monthly,
                "total": total,
                "months_with_spend": months_with_spend.get(category_key, 0),
                "latest_month": monthly_category_totals.get(latest_month_key, {}).get(
                    category_key, 0.0
                ),
            }
        )
    rows.sort(
        key=lambda item: (
            -float(item.get("average_monthly", 0.0) or 0.0),
            str(item.get("category", "")).lower(),
        )
    )
    return {
        "months_count": months_count,
        "month_keys": month_keys,
        "rows": rows,
    }


def calculate_summary(
    transactions: List[Transaction],
    settings: Settings,
    recurring_charges: Optional[List[RecurringCharge]] = None,
) -> Dict[str, Union[float, str, None]]:
    total_expenses = sum(tx.amount for tx in transactions if tx.type == "expense")
    total_income = sum(tx.amount for tx in transactions if tx.type == "income")
    total_income += settings.refunds_total
    adjustments_total = sum(
        _adjustment_balance_effect(tx) for tx in transactions if _is_adjustment_tx(tx)
    )
    category_average_stats = calculate_category_average_rows(transactions)
    category_average_rows = list(category_average_stats.get("rows", []))
    category_average_months_count = int(category_average_stats.get("months_count", 0) or 0)

    estimated_balance = settings.starting_balance - total_expenses + total_income

    recurring_charges = recurring_charges or []
    today = _local_today()
    plan_context = _plan_month_context(settings, today)
    plan_start_year = int(plan_context["plan_start_year"])
    plan_start_month = int(plan_context["plan_start_month"])
    plan_months = list(plan_context["plan_months"])
    remaining_months = list(plan_context["remaining_months"])
    months_remaining = int(plan_context["months_remaining"])
    months_elapsed_auto = int(plan_context["months_elapsed_auto"])
    plan_months_to_date = list(plan_context["plan_months_to_date"])
    plan_months_to_date_keys = {
        _month_key(year, month) for year, month in plan_months_to_date
    }
    months_covered_to_date = len(plan_months_to_date)
    auto_stats = _auto_category_stats(
        transactions,
        settings,
        today,
        include_recurring=bool(settings.auto_include_recurring),
        include_current_month=bool(getattr(settings, "auto_include_current_month", True)),
        window_months=int(settings.auto_window_months),
        weighted=bool(settings.auto_weighted),
        half_life_months=int(settings.auto_weight_half_life_months),
    )
    auto_categories = list(auto_stats.get("selected", []))
    auto_category_monthly = dict(auto_stats.get("monthly", {}))
    auto_category_totals = dict(auto_stats.get("totals", {}))
    auto_category_monthly_total = float(auto_stats.get("monthly_total", 0.0))
    auto_category_total_selected = float(auto_stats.get("total_selected", 0.0))
    auto_category_months_count = int(auto_stats.get("months_count", 0) or 0)
    auto_category_history_start = auto_stats.get("history_start")
    auto_category_history_end = auto_stats.get("history_end")
    auto_category_includes_recurring = bool(auto_stats.get("include_recurring", False))
    auto_category_weighted = bool(auto_stats.get("weighted", False))
    auto_category_half_life = int(auto_stats.get("half_life_months", 1) or 1)
    auto_category_window_months = int(auto_stats.get("window_months", 0) or 0)
    windowed_avg_monthly = _auto_keyword_monthly_average(
        transactions,
        settings,
        today,
        include_recurring=True,
        window_months=int(settings.auto_window_months),
        weighted=bool(settings.auto_weighted),
        half_life_months=int(settings.auto_weight_half_life_months),
        include_current_month=bool(getattr(settings, "auto_include_current_month", True)),
        matcher=lambda _tx: True,
    )
    rent_auto_monthly = _auto_keyword_monthly_average(
        transactions,
        settings,
        today,
        include_recurring=bool(settings.auto_include_recurring),
        window_months=int(settings.auto_window_months),
        weighted=bool(settings.auto_weighted),
        half_life_months=int(settings.auto_weight_half_life_months),
        include_current_month=bool(getattr(settings, "auto_include_current_month", True)),
        matcher=_is_rent_tx,
        credit_matcher=_is_rent_credit_tx,
    )
    auto_mode_active = bool(settings.auto_misc_enabled)
    manual_variable_monthly_total = (
        settings.food_house_monthly
        + settings.misc_monthly
        + settings.medical_monthly
        + settings.school_monthly
        + settings.household_monthly
        + settings.health_monthly
    )
    rent_manual_monthly = float(getattr(settings, "rent_monthly_manual", 0.0) or 0.0)
    essential_manual_monthly_total = (
        settings.food_house_monthly
        + settings.medical_monthly
        + settings.school_monthly
        + settings.household_monthly
        + settings.health_monthly
    )
    auto_selected_food = any(_is_food_text(name) for name in auto_categories)
    auto_selected_misc = any(_is_misc_text(name) for name in auto_categories)
    auto_selected_medical = any(_is_medical_text(name) for name in auto_categories)
    auto_selected_school = any(_is_school_text(name) for name in auto_categories)
    auto_selected_household = any(_is_household_text(name) for name in auto_categories)
    auto_selected_health = any(_is_health_text(name) for name in auto_categories)
    auto_food_has_data = any(
        _is_food_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_misc_has_data = any(
        _is_misc_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_medical_has_data = any(
        _is_medical_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_school_has_data = any(
        _is_school_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_household_has_data = any(
        _is_household_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_health_has_data = any(
        _is_health_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    manual_fallback_food = (
        settings.food_house_monthly
        if (not auto_selected_food or (auto_mode_active and not auto_food_has_data))
        else 0.0
    )
    manual_fallback_misc = (
        settings.misc_monthly
        if (not auto_selected_misc or (auto_mode_active and not auto_misc_has_data))
        else 0.0
    )
    manual_fallback_medical = (
        settings.medical_monthly
        if (not auto_selected_medical or (auto_mode_active and not auto_medical_has_data))
        else 0.0
    )
    manual_fallback_school = (
        settings.school_monthly
        if (not auto_selected_school or (auto_mode_active and not auto_school_has_data))
        else 0.0
    )
    manual_fallback_household = (
        settings.household_monthly
        if (not auto_selected_household or (auto_mode_active and not auto_household_has_data))
        else 0.0
    )
    manual_fallback_health = (
        settings.health_monthly
        if (not auto_selected_health or (auto_mode_active and not auto_health_has_data))
        else 0.0
    )
    predicted_variable_monthly_total_raw = (
        auto_category_monthly_total
        + manual_fallback_food
        + manual_fallback_misc
        + manual_fallback_medical
        + manual_fallback_school
        + manual_fallback_household
        + manual_fallback_health
    )
    auto_history_available = auto_category_months_count > 0
    predicted_variable_monthly_total = predicted_variable_monthly_total_raw
    if auto_mode_active and not auto_history_available:
        predicted_variable_monthly_total = manual_variable_monthly_total
    variable_monthly_effective = (
        predicted_variable_monthly_total if auto_mode_active else manual_variable_monthly_total
    )
    auto_food_monthly = sum(
        value for name, value in auto_category_monthly.items() if _is_food_text(name)
    )
    auto_food_categories = {
        _normalize_category(name)
        for name in auto_category_monthly
        if _is_food_text(name)
    }
    food_monthly_effective = settings.food_house_monthly
    if auto_mode_active:
        food_monthly_effective = (
            auto_food_monthly if auto_selected_food else settings.food_house_monthly
        )
    rent_schedule = _rent_schedule(recurring_charges, plan_months)
    rent_from_legacy = False
    if sum(rent_schedule.values()) <= 0.0:
        rent_schedule = _legacy_rent_schedule(
            plan_months, settings, plan_start_year, plan_start_month
        )
        rent_from_legacy = True
    rent_schedule_total = sum(rent_schedule.values())
    rent_manual_total = (
        rent_manual_monthly * settings.plan_months_total if rent_manual_monthly > 0 else 0.0
    )
    base_rent_total = rent_manual_total if rent_manual_monthly > 0 else rent_schedule_total
    food_total = food_monthly_effective * settings.plan_months_total
    medical_total = settings.medical_monthly * settings.plan_months_total
    school_total = settings.school_monthly * settings.plan_months_total
    household_total = settings.household_monthly * settings.plan_months_total
    health_total = settings.health_monthly * settings.plan_months_total
    misc_total = settings.misc_monthly * settings.plan_months_total
    planned_variable_total = manual_variable_monthly_total * settings.plan_months_total
    variable_total = planned_variable_total
    auto_essential_monthly_total = sum(
        value for name, value in auto_category_monthly.items() if _is_essential_text(name)
    )
    predicted_essential_monthly_total_raw = (
        auto_essential_monthly_total
        + manual_fallback_food
        + manual_fallback_medical
        + manual_fallback_school
        + manual_fallback_household
        + manual_fallback_health
    )
    predicted_essential_monthly_total = predicted_essential_monthly_total_raw
    if auto_mode_active and not auto_history_available:
        predicted_essential_monthly_total = essential_manual_monthly_total
    essential_budget_total_planned = (
        essential_manual_monthly_total * settings.plan_months_total
    )
    essential_budget_total_predicted = (
        predicted_essential_monthly_total * settings.plan_months_total
    )
    essential_budget_total = essential_budget_total_planned
    rent_expenses_by_month: Dict[str, float] = defaultdict(float)
    rent_credits_by_month: Dict[str, float] = defaultdict(float)
    for tx in transactions:
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        tx_month_key = tx_dt.strftime("%Y-%m")
        if tx_month_key not in plan_months_to_date_keys:
            continue
        if _is_adjustment_tx(tx):
            continue
        if tx.type == "expense" and _is_rent_tx(tx):
            rent_expenses_by_month[tx_month_key] += tx.amount
        elif _is_rent_credit_tx(tx):
            rent_credits_by_month[tx_month_key] += tx.amount
    rent_budget_to_date = 0.0
    for year, month in plan_months_to_date:
        month_key = _month_key(year, month)
        scheduled = rent_schedule.get(month_key, 0.0)
        actual = max(
            0.0,
            rent_expenses_by_month.get(month_key, 0.0)
            - rent_credits_by_month.get(month_key, 0.0),
        )
        rent_budget_to_date += scheduled if scheduled > 0.0 else actual
    food_budget_to_date = food_monthly_effective * months_covered_to_date
    essential_budget_to_date_planned = (
        essential_manual_monthly_total * months_covered_to_date
    )
    essential_budget_to_date_predicted = (
        predicted_essential_monthly_total * months_covered_to_date
    )

    rent_paid_to_date_gross = sum(rent_expenses_by_month.values())
    rent_income_offset_to_date = sum(rent_credits_by_month.values())
    rent_paid_to_date = max(0.0, rent_paid_to_date_gross - rent_income_offset_to_date)
    essential_expenses_to_date = 0.0
    for tx in transactions:
        if _is_adjustment_tx(tx):
            continue
        if tx.type != "expense":
            continue
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        tx_month_key = tx_dt.strftime("%Y-%m")
        if tx_month_key not in plan_months_to_date_keys:
            continue
        if _is_rent_tx(tx):
            continue
        if _is_essential_tx(tx):
            essential_expenses_to_date += tx.amount

    essential_used_pct_planned = (
        (essential_expenses_to_date / essential_budget_to_date_planned) * 100
        if essential_budget_to_date_planned
        else 0.0
    )
    essential_used_pct_predicted = (
        (essential_expenses_to_date / essential_budget_to_date_predicted) * 100
        if essential_budget_to_date_predicted
        else 0.0
    )
    rent_budget_to_date_planned = (
        rent_manual_monthly * months_covered_to_date
        if rent_manual_monthly > 0
        else rent_budget_to_date
    )
    rent_budget_to_date_predicted = (
        rent_auto_monthly * months_covered_to_date if rent_auto_monthly > 0.0 else 0.0
    )
    rent_used_pct_planned = (
        (rent_paid_to_date / rent_budget_to_date_planned) * 100
        if rent_budget_to_date_planned
        else 0.0
    )
    rent_used_pct_predicted = (
        (rent_paid_to_date / rent_budget_to_date_predicted) * 100
        if rent_budget_to_date_predicted
        else 0.0
    )

    recurring_expense_schedule = _recurring_expense_schedule(
        recurring_charges, plan_months
    )
    if rent_from_legacy:
        for month_key, value in rent_schedule.items():
            recurring_expense_schedule[month_key] = (
                recurring_expense_schedule.get(month_key, 0.0) + value
            )
    recurring_nonrent_schedule = {}
    for month_key, total in recurring_expense_schedule.items():
        recurring_nonrent_schedule[month_key] = max(
            0.0, total - rent_schedule.get(month_key, 0.0)
        )
    rent_manual_active = rent_manual_monthly > 0
    plan_recurring_schedule = (
        recurring_nonrent_schedule if rent_manual_active else recurring_expense_schedule
    )
    predicted_recurring_schedule = recurring_nonrent_schedule
    recurring_schedule_for_coverage = (
        predicted_recurring_schedule if auto_mode_active else plan_recurring_schedule
    )
    recurring_plan_total = sum(plan_recurring_schedule.values())
    recurring_remaining_total = sum(
        recurring_schedule_for_coverage.get(_month_key(year, month), 0.0)
        for year, month in remaining_months
    )
    food_remaining_total = food_monthly_effective * months_remaining
    variable_remaining_total = variable_monthly_effective * months_remaining
    misc_remaining_total = max(variable_remaining_total - food_remaining_total, 0.0)
    extra_remaining_total = 0.0
    recurring_avg_per_month = (
        recurring_remaining_total / months_remaining if months_remaining else None
    )

    cap_nonrent_per_month = None
    coverage_display = None
    coverage_12mo_display = None
    coverage_month_keys: List[str] = []
    coverage_month_budgets: List[float] = []
    current_month_expenses = 0.0
    current_month_income = 0.0
    current_month_adjustments = 0.0
    essential_month_expenses = 0.0
    rent_month_paid_gross = 0.0
    rent_month_income_offset = 0.0
    current_month_budget = None
    current_month_remaining_budget = None
    current_month_budget_to_date = None
    current_month_remaining_to_date = None
    current_month_key = _month_key(today.year, today.month)
    expenses_to_date_plan = 0.0
    for tx in transactions:
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        tx_month_key = tx_dt.strftime("%Y-%m")
        if tx_month_key == current_month_key:
            if _is_adjustment_tx(tx):
                current_month_adjustments += _adjustment_balance_effect(tx)
                continue
            if tx.type == "expense":
                current_month_expenses += tx.amount
                if _is_rent_tx(tx):
                    rent_month_paid_gross += tx.amount
                elif _is_essential_tx(tx):
                    essential_month_expenses += tx.amount
            else:
                current_month_income += tx.amount
                if _is_rent_credit_tx(tx):
                    rent_month_income_offset += tx.amount
        if tx_month_key in plan_months_to_date_keys:
            if tx.type == "expense" and not _is_adjustment_tx(tx):
                expenses_to_date_plan += tx.amount
    rent_month_paid = max(0.0, rent_month_paid_gross - rent_month_income_offset)
    average_expenses = (
        expenses_to_date_plan / months_covered_to_date
        if months_covered_to_date
        else 0.0
    )
    planned_remaining_total = 0.0
    current_month_start, current_month_end = _month_bounds(today.year, today.month)
    current_recurring_to_date = 0.0
    rent_override_active = rent_manual_active or rent_auto_monthly > 0.0
    for charge in recurring_charges:
        if charge.type != "expense":
            continue
        if rent_override_active and _is_rent_charge(charge):
            continue
        occurrences = _count_occurrences_in_range(
            charge, current_month_start, today
        )
        if occurrences:
            current_recurring_to_date += float(charge.amount) * occurrences

    if months_remaining > 0:
        cap_nonrent_per_month = (
            (estimated_balance - recurring_remaining_total) / months_remaining
        )
        remaining_budgets = []
        planned_remaining_budgets = []
        predicted_remaining_budgets = []
        for year, month in remaining_months:
            month_key = _month_key(year, month)
            recurring_plan_budget = plan_recurring_schedule.get(month_key, 0.0)
            recurring_predicted_budget = predicted_recurring_schedule.get(month_key, 0.0)
            recurring_budget = (
                recurring_predicted_budget
                if auto_mode_active
                else recurring_plan_budget
            )
            rent_plan_budget = (
                rent_manual_monthly
                if rent_manual_active
                else rent_schedule.get(month_key, 0.0)
            )
            rent_predicted_budget = rent_auto_monthly if rent_auto_monthly > 0.0 else 0.0
            rent_budget = rent_predicted_budget if auto_mode_active else rent_plan_budget
            monthly_budget = recurring_budget + rent_budget + variable_monthly_effective
            planned_monthly_budget = (
                recurring_plan_budget + rent_plan_budget + manual_variable_monthly_total
            )
            predicted_monthly_budget = (
                recurring_predicted_budget
                + rent_predicted_budget
                + predicted_variable_monthly_total
            )
            if month_key == current_month_key:
                current_month_budget = monthly_budget
                current_month_remaining_budget = monthly_budget - current_month_expenses
                if rent_override_active:
                    current_month_budget_to_date = (
                        current_recurring_to_date
                        + rent_month_paid
                        + variable_monthly_effective
                    )
                else:
                    current_month_budget_to_date = (
                        current_recurring_to_date + variable_monthly_effective
                    )
                current_month_remaining_to_date = (
                    current_month_budget_to_date - current_month_expenses
                )
                remaining_budgets.append(current_month_remaining_budget)
                coverage_month_budgets.append(current_month_remaining_budget)
                planned_remaining_budgets.append(
                    max(0.0, planned_monthly_budget - current_month_expenses)
                )
                predicted_remaining_budgets.append(
                    max(0.0, predicted_monthly_budget - current_month_expenses)
                )
            else:
                remaining_budgets.append(monthly_budget)
                coverage_month_budgets.append(monthly_budget)
                planned_remaining_budgets.append(planned_monthly_budget)
                predicted_remaining_budgets.append(predicted_monthly_budget)
            coverage_month_keys.append(month_key)
        planned_remaining_total = sum(planned_remaining_budgets)
        predicted_remaining_total = sum(predicted_remaining_budgets)
        if remaining_budgets:
            coverage_months_exact = _coverage_months(
                estimated_balance, remaining_budgets
            )
            coverage_display = (
                f"{_format_coverage_value(coverage_months_exact)}/{months_remaining}"
            )
    else:
        predicted_remaining_total = 0.0

    planned_final_expenses = expenses_to_date_plan + planned_remaining_total
    plan_budget_total = planned_final_expenses
    projected_final_expenses = expenses_to_date_plan + predicted_remaining_total
    savings_vs_campus_planned = settings.campus_reference_total - (
        expenses_to_date_plan + planned_remaining_total
    )
    savings_vs_campus_predicted = settings.campus_reference_total - (
        expenses_to_date_plan + predicted_remaining_total
    )
    savings_vs_campus = savings_vs_campus_predicted

    extra_months_total = max(0, 12 - settings.plan_months_total)
    if plan_months:
        plan_end_year, plan_end_month = plan_months[-1]
    else:
        plan_end_year, plan_end_month = today.year, today.month
    extra_start_year, extra_start_month = _add_months(
        plan_end_year, plan_end_month, 1
    )
    extra_months_all = _month_iter(
        extra_start_year, extra_start_month, extra_months_total
    )
    extra_months_12_list = [
        (year, month)
        for year, month in extra_months_all
        if _month_offset(today.year, today.month, year, month) >= 0
    ]
    months_12 = remaining_months + extra_months_12_list
    recurring_schedule_12 = _recurring_expense_schedule(recurring_charges, months_12)
    rent_schedule_12 = _rent_schedule(recurring_charges, months_12)
    if rent_from_legacy:
        legacy_schedule_12 = _legacy_rent_schedule(
            months_12, settings, plan_start_year, plan_start_month
        )
        for month_key, value in legacy_schedule_12.items():
            recurring_schedule_12[month_key] = (
                recurring_schedule_12.get(month_key, 0.0) + value
            )
            rent_schedule_12[month_key] = rent_schedule_12.get(month_key, 0.0) + value
    recurring_nonrent_schedule_12 = {}
    for month_key, total in recurring_schedule_12.items():
        recurring_nonrent_schedule_12[month_key] = max(
            0.0, total - rent_schedule_12.get(month_key, 0.0)
        )
    budgets_12 = []
    coverage_12_month_keys: List[str] = []
    coverage_12_budgets: List[float] = []
    extra_months_12 = len(extra_months_12_list)
    extra_months_12_set = set(extra_months_12_list)
    for year, month in months_12:
        month_key = _month_key(year, month)
        if auto_mode_active:
            recurring_budget = recurring_nonrent_schedule_12.get(month_key, 0.0)
            rent_budget = rent_auto_monthly if rent_auto_monthly > 0.0 else 0.0
        else:
            if rent_manual_active:
                recurring_budget = recurring_nonrent_schedule_12.get(month_key, 0.0)
                rent_budget = rent_manual_monthly
            else:
                recurring_budget = recurring_schedule_12.get(month_key, 0.0)
                rent_budget = rent_schedule_12.get(month_key, 0.0)
        extra_budget = settings.extra_monthly if (year, month) in extra_months_12_set else 0.0
        monthly_budget = (
            recurring_budget
            + rent_budget
            + variable_monthly_effective
            + extra_budget
        )
        if month_key == current_month_key:
            adjusted_budget = max(0.0, monthly_budget - current_month_expenses)
            budgets_12.append(adjusted_budget)
            coverage_12_budgets.append(adjusted_budget)
        else:
            budgets_12.append(monthly_budget)
            coverage_12_budgets.append(monthly_budget)
        coverage_12_month_keys.append(month_key)
    predicted_12_total = sum(budgets_12)
    extra_12_total = settings.extra_monthly * extra_months_12
    if budgets_12:
        coverage_12_exact = _coverage_months(estimated_balance, budgets_12)
        coverage_12mo_display = (
            f"{_format_coverage_value(coverage_12_exact)}/{len(budgets_12)}"
        )

    essential_month_budget_planned = essential_manual_monthly_total
    essential_month_budget_predicted = predicted_essential_monthly_total
    rent_month_budget_planned = (
        rent_manual_monthly if rent_manual_monthly > 0 else rent_schedule.get(current_month_key, 0.0)
    )
    rent_month_budget_predicted = rent_auto_monthly if rent_auto_monthly > 0.0 else 0.0

    essential_year_budget_planned = essential_budget_total_planned
    essential_year_budget_predicted = essential_budget_total_predicted
    rent_year_budget_planned = (
        rent_manual_monthly * settings.plan_months_total
        if rent_manual_monthly > 0
        else base_rent_total
    )
    rent_year_budget_predicted = (
        rent_auto_monthly * settings.plan_months_total if rent_auto_monthly > 0.0 else 0.0
    )

    essential_month_used_pct_planned = (
        (essential_month_expenses / essential_month_budget_planned) * 100
        if essential_month_budget_planned
        else 0.0
    )
    essential_month_used_pct_predicted = (
        (essential_month_expenses / essential_month_budget_predicted) * 100
        if essential_month_budget_predicted
        else 0.0
    )
    essential_year_used_pct_planned = (
        (essential_expenses_to_date / essential_year_budget_planned) * 100
        if essential_year_budget_planned
        else 0.0
    )
    essential_year_used_pct_predicted = (
        (essential_expenses_to_date / essential_year_budget_predicted) * 100
        if essential_year_budget_predicted
        else 0.0
    )
    rent_month_used_pct_planned = (
        (rent_month_paid / rent_month_budget_planned) * 100
        if rent_month_budget_planned
        else 0.0
    )
    rent_month_used_pct_predicted = (
        (rent_month_paid / rent_month_budget_predicted) * 100
        if rent_month_budget_predicted
        else 0.0
    )
    rent_year_used_pct_planned = (
        (rent_paid_to_date / rent_year_budget_planned) * 100
        if rent_year_budget_planned
        else 0.0
    )
    rent_year_used_pct_predicted = (
        (rent_paid_to_date / rent_year_budget_predicted) * 100
        if rent_year_budget_predicted
        else 0.0
    )

    auto_category_history_start_text = (
        auto_category_history_start.isoformat()
        if isinstance(auto_category_history_start, date)
        else None
    )
    auto_category_history_end_text = (
        auto_category_history_end.isoformat()
        if isinstance(auto_category_history_end, date)
        else None
    )

    return {
        "total_expenses": total_expenses,
        "total_income": total_income,
        "estimated_balance": estimated_balance,
        "adjustments_total": adjustments_total,
        "base_rent_total": base_rent_total,
        "food_total": food_total,
        "misc_total": misc_total,
        "variable_total": variable_total,
        "variable_monthly_effective": variable_monthly_effective,
        "food_monthly_effective": food_monthly_effective,
        "manual_variable_monthly_total": manual_variable_monthly_total,
        "auto_history_available": auto_history_available,
        "predicted_variable_monthly_total_raw": predicted_variable_monthly_total_raw,
        "predicted_variable_monthly_total": predicted_variable_monthly_total,
        "auto_mode_active": auto_mode_active,
        "auto_category_monthly_total": auto_category_monthly_total,
        "auto_category_total_selected": auto_category_total_selected,
        "auto_category_totals": auto_category_totals,
        "auto_category_monthly": auto_category_monthly,
        "auto_category_categories": auto_categories,
        "auto_category_months_count": auto_category_months_count,
        "windowed_avg_monthly": windowed_avg_monthly,
        "auto_category_history_start": auto_category_history_start_text,
        "auto_category_history_end": auto_category_history_end_text,
        "auto_category_history_keys": auto_stats.get("history_month_keys", []),
        "auto_category_includes_recurring": auto_category_includes_recurring,
        "auto_category_weighted": auto_category_weighted,
        "auto_category_half_life_months": auto_category_half_life,
        "auto_category_window_months": auto_category_window_months,
        "rent_manual_monthly": rent_manual_monthly,
        "rent_auto_monthly": rent_auto_monthly,
        "essential_manual_monthly_total": essential_manual_monthly_total,
        "predicted_essential_monthly_total_raw": predicted_essential_monthly_total_raw,
        "predicted_essential_monthly_total": predicted_essential_monthly_total,
        "essential_budget_total": essential_budget_total,
        "essential_budget_total_planned": essential_budget_total_planned,
        "essential_budget_total_predicted": essential_budget_total_predicted,
        "essential_budget_to_date_planned": essential_budget_to_date_planned,
        "essential_budget_to_date_predicted": essential_budget_to_date_predicted,
        "essential_month_budget_planned": essential_month_budget_planned,
        "essential_month_budget_predicted": essential_month_budget_predicted,
        "essential_year_budget_planned": essential_year_budget_planned,
        "essential_year_budget_predicted": essential_year_budget_predicted,
        "food_budget_to_date": food_budget_to_date,
        "rent_budget_to_date": rent_budget_to_date,
        "rent_month_budget_planned": rent_month_budget_planned,
        "rent_month_budget_predicted": rent_month_budget_predicted,
        "rent_year_budget_planned": rent_year_budget_planned,
        "rent_year_budget_predicted": rent_year_budget_predicted,
        "essential_expenses_to_date": essential_expenses_to_date,
        "essential_month_expenses": essential_month_expenses,
        "recurring_plan_total": recurring_plan_total,
        "plan_budget_total": plan_budget_total,
        "planned_remaining_total": planned_remaining_total,
        "savings_vs_campus": savings_vs_campus,
        "savings_vs_campus_planned": savings_vs_campus_planned,
        "savings_vs_campus_predicted": savings_vs_campus_predicted,
        "rent_paid_to_date": rent_paid_to_date,
        "rent_paid_to_date_gross": rent_paid_to_date_gross,
        "rent_income_offset_to_date": rent_income_offset_to_date,
        "rent_month_paid": rent_month_paid,
        "rent_month_paid_gross": rent_month_paid_gross,
        "rent_month_income_offset": rent_month_income_offset,
        "rent_budget_to_date_planned": rent_budget_to_date_planned,
        "rent_budget_to_date_predicted": rent_budget_to_date_predicted,
        "essential_used_pct": essential_used_pct_planned,
        "rent_used_pct": rent_used_pct_planned,
        "essential_used_pct_planned": essential_used_pct_planned,
        "essential_used_pct_predicted": essential_used_pct_predicted,
        "rent_used_pct_planned": rent_used_pct_planned,
        "rent_used_pct_predicted": rent_used_pct_predicted,
        "essential_month_used_pct_planned": essential_month_used_pct_planned,
        "essential_month_used_pct_predicted": essential_month_used_pct_predicted,
        "essential_year_used_pct_planned": essential_year_used_pct_planned,
        "essential_year_used_pct_predicted": essential_year_used_pct_predicted,
        "rent_month_used_pct_planned": rent_month_used_pct_planned,
        "rent_month_used_pct_predicted": rent_month_used_pct_predicted,
        "rent_year_used_pct_planned": rent_year_used_pct_planned,
        "rent_year_used_pct_predicted": rent_year_used_pct_predicted,
        "months_remaining": months_remaining,
        "months_elapsed_auto": months_elapsed_auto,
        "rent_remaining_total": recurring_remaining_total,
        "recurring_remaining_total": recurring_remaining_total,
        "food_remaining_total": food_remaining_total,
        "misc_remaining_total": misc_remaining_total,
        "variable_remaining_total": variable_remaining_total,
        "extra_remaining_total": extra_remaining_total,
        "predicted_remaining_total": predicted_remaining_total,
        "expenses_to_date_plan": expenses_to_date_plan,
        "months_covered_to_date": months_covered_to_date,
        "projected_final_expenses": projected_final_expenses,
        "average_expenses": average_expenses,
        "predicted_12_total": predicted_12_total,
        "extra_months_12": extra_months_12,
        "extra_12_total": extra_12_total,
        "coverage_month_keys": coverage_month_keys,
        "coverage_month_budgets": coverage_month_budgets,
        "coverage_12_month_keys": coverage_12_month_keys,
        "coverage_12_budgets": coverage_12_budgets,
        "coverage_current_month_expenses": current_month_expenses,
        "current_month_expenses": current_month_expenses,
        "current_month_income": current_month_income,
        "current_month_adjustments": current_month_adjustments,
        "coverage_current_month_budget": current_month_budget,
        "coverage_current_month_remaining_budget": current_month_remaining_budget,
        "current_month_budget_to_date": current_month_budget_to_date,
        "current_month_remaining_to_date": current_month_remaining_to_date,
        "category_average_rows": category_average_rows,
        "category_average_months_count": category_average_months_count,
        "recurring_avg_per_month": recurring_avg_per_month,
        "cap_nonrent_per_month": cap_nonrent_per_month,
        "coverage_display": coverage_display,
        "coverage_12mo_display": coverage_12mo_display,
        "settings": asdict(settings),
    }


def calculate_monthly_stats(
    transactions: List[Transaction],
    settings: Settings,
    recurring_charges: Optional[List[RecurringCharge]] = None,
) -> List[Dict[str, Union[float, str]]]:
    grouped: Dict[str, List[Transaction]] = defaultdict(list)
    for tx in transactions:
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        grouped[tx_dt.strftime("%Y-%m")].append(tx)
    recurring_charges = recurring_charges or []
    today = _local_today()
    plan_context = _plan_month_context(settings, today)
    plan_start_year = int(plan_context["plan_start_year"])
    plan_start_month = int(plan_context["plan_start_month"])
    plan_months = list(plan_context["plan_months"])
    auto_stats = _auto_category_stats(
        transactions,
        settings,
        today,
        include_recurring=bool(settings.auto_include_recurring),
        include_current_month=bool(getattr(settings, "auto_include_current_month", True)),
        window_months=int(settings.auto_window_months),
        weighted=bool(settings.auto_weighted),
        half_life_months=int(settings.auto_weight_half_life_months),
    )
    auto_categories = list(auto_stats.get("selected", []))
    auto_category_months_count = int(auto_stats.get("months_count", 0) or 0)
    auto_category_totals = dict(auto_stats.get("totals", {}))
    auto_category_monthly_total = float(auto_stats.get("monthly_total", 0.0))
    auto_mode_active = bool(settings.auto_misc_enabled)
    manual_variable_monthly_total = (
        settings.food_house_monthly
        + settings.misc_monthly
        + settings.medical_monthly
        + settings.school_monthly
        + settings.household_monthly
        + settings.health_monthly
    )
    auto_selected_food = any(_is_food_text(name) for name in auto_categories)
    auto_selected_misc = any(_is_misc_text(name) for name in auto_categories)
    auto_selected_medical = any(_is_medical_text(name) for name in auto_categories)
    auto_selected_school = any(_is_school_text(name) for name in auto_categories)
    auto_selected_household = any(_is_household_text(name) for name in auto_categories)
    auto_selected_health = any(_is_health_text(name) for name in auto_categories)
    auto_food_has_data = any(
        _is_food_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_misc_has_data = any(
        _is_misc_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_medical_has_data = any(
        _is_medical_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_school_has_data = any(
        _is_school_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_household_has_data = any(
        _is_household_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    auto_health_has_data = any(
        _is_health_text(name) and float(auto_category_totals.get(name, 0.0)) > 0.0
        for name in auto_categories
    )
    manual_fallback_food = (
        settings.food_house_monthly
        if (not auto_selected_food or (auto_mode_active and not auto_food_has_data))
        else 0.0
    )
    manual_fallback_misc = (
        settings.misc_monthly
        if (not auto_selected_misc or (auto_mode_active and not auto_misc_has_data))
        else 0.0
    )
    manual_fallback_medical = (
        settings.medical_monthly
        if (not auto_selected_medical or (auto_mode_active and not auto_medical_has_data))
        else 0.0
    )
    manual_fallback_school = (
        settings.school_monthly
        if (not auto_selected_school or (auto_mode_active and not auto_school_has_data))
        else 0.0
    )
    manual_fallback_household = (
        settings.household_monthly
        if (not auto_selected_household or (auto_mode_active and not auto_household_has_data))
        else 0.0
    )
    manual_fallback_health = (
        settings.health_monthly
        if (not auto_selected_health or (auto_mode_active and not auto_health_has_data))
        else 0.0
    )
    predicted_variable_monthly_total_raw = (
        auto_category_monthly_total
        + manual_fallback_food
        + manual_fallback_misc
        + manual_fallback_medical
        + manual_fallback_school
        + manual_fallback_household
        + manual_fallback_health
    )
    predicted_variable_monthly_total = predicted_variable_monthly_total_raw
    if auto_mode_active and auto_category_months_count <= 0:
        predicted_variable_monthly_total = manual_variable_monthly_total
    variable_monthly_effective = (
        predicted_variable_monthly_total if auto_mode_active else manual_variable_monthly_total
    )
    rent_manual_monthly = float(getattr(settings, "rent_monthly_manual", 0.0) or 0.0)
    rent_auto_monthly = _auto_keyword_monthly_average(
        transactions,
        settings,
        today,
        include_recurring=bool(settings.auto_include_recurring),
        window_months=int(settings.auto_window_months),
        weighted=bool(settings.auto_weighted),
        half_life_months=int(settings.auto_weight_half_life_months),
        matcher=_is_rent_tx,
        credit_matcher=_is_rent_credit_tx,
    )
    rent_schedule = _rent_schedule(recurring_charges, plan_months)
    rent_from_legacy = False
    if sum(rent_schedule.values()) <= 0.0:
        rent_schedule = _legacy_rent_schedule(
            plan_months, settings, plan_start_year, plan_start_month
        )
        rent_from_legacy = True
    recurring_expense_schedule = _recurring_expense_schedule(
        recurring_charges, plan_months
    )
    if rent_from_legacy:
        for month_key, value in rent_schedule.items():
            recurring_expense_schedule[month_key] = (
                recurring_expense_schedule.get(month_key, 0.0) + value
            )
    stats: List[Dict[str, Union[float, str]]] = []
    plan_month_keys = [_month_key(year, month) for year, month in plan_months]
    all_month_keys = sorted(set(grouped.keys()) | set(plan_month_keys))
    for month_key in all_month_keys:
        year, month = map(int, month_key.split("-"))
        if month_key not in recurring_expense_schedule:
            month_schedule = _recurring_expense_schedule(recurring_charges, [(year, month)])
            if rent_from_legacy:
                legacy_schedule = _legacy_rent_schedule(
                    [(year, month)], settings, plan_start_year, plan_start_month
                )
                month_schedule[month_key] = (
                    month_schedule.get(month_key, 0.0)
                    + legacy_schedule.get(month_key, 0.0)
                )
            recurring_expense_schedule.update(month_schedule)
        if month_key not in rent_schedule:
            month_rent_schedule = _rent_schedule(recurring_charges, [(year, month)]).get(
                month_key, 0.0
            )
            if rent_from_legacy:
                legacy_schedule = _legacy_rent_schedule(
                    [(year, month)], settings, plan_start_year, plan_start_month
                )
                month_rent_schedule += legacy_schedule.get(month_key, 0.0)
            rent_schedule[month_key] = month_rent_schedule
        monthly_recurring = recurring_expense_schedule.get(month_key, 0.0)
        monthly_rent = rent_schedule.get(month_key, 0.0)
        monthly_nonrent = max(0.0, monthly_recurring - monthly_rent)
        monthly_budget_predicted = (
            monthly_nonrent
            + (rent_auto_monthly if rent_auto_monthly > 0.0 else 0.0)
            + predicted_variable_monthly_total
        )
        monthly_budget_planned = (
            monthly_nonrent
            + (rent_manual_monthly if rent_manual_monthly > 0 else monthly_rent)
            + manual_variable_monthly_total
        )
        if auto_mode_active:
            recurring_budget = monthly_nonrent
            rent_budget = rent_auto_monthly if rent_auto_monthly > 0.0 else 0.0
        else:
            if rent_manual_monthly > 0:
                recurring_budget = monthly_nonrent
                rent_budget = rent_manual_monthly
            else:
                recurring_budget = monthly_recurring
                rent_budget = 0.0
        monthly_target = recurring_budget + rent_budget + variable_monthly_effective
        month_total = 0.0
        adjustment_total = 0.0
        rent_credit_total = 0.0
        rent_expense_total = 0.0
        for tx in grouped.get(month_key, []):
            if _is_adjustment_tx(tx):
                adjustment_total += _adjustment_balance_effect(tx)
                continue
            if tx.type == "expense":
                month_total += tx.amount
                if _is_rent_tx(tx):
                    rent_expense_total += tx.amount
            elif _is_rent_credit_tx(tx):
                rent_credit_total += tx.amount
        rent_net_total = max(0.0, rent_expense_total - rent_credit_total)
        delta_amount = month_total - monthly_target
        delta_pct = (delta_amount / monthly_target * 100) if monthly_target else 0.0
        stats.append(
            {
                "month": month_key,
                "total_expenses": month_total,
                "adjustments_total": adjustment_total,
                "rent_expenses": rent_expense_total,
                "rent_income_offset": rent_credit_total,
                "rent_net": rent_net_total,
                "monthly_budget": monthly_target,
                "monthly_budget_planned": monthly_budget_planned,
                "monthly_budget_predicted": monthly_budget_predicted,
                "delta_amount": delta_amount,
                "delta_pct": delta_pct,
            }
        )
    return stats


def running_balance_series(
    transactions: List[Transaction],
    starting_balance: float,
    refunds_total: float,
) -> Tuple[List[str], List[float]]:
    ordered = []
    for tx in transactions:
        tx_dt = _try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        ordered.append((tx_dt, tx))
    ordered.sort(key=lambda item: item[0])
    balance = starting_balance + refunds_total
    dates: List[str] = []
    values: List[float] = []
    for tx_dt, tx in ordered:
        if tx.type == "expense":
            balance -= tx.amount
        else:
            balance += tx.amount
        dates.append(tx_dt.strftime("%Y-%m-%d"))
        values.append(balance)
    return dates, values


def cumulative_expenses_by_month(
    monthly_stats: List[Dict[str, Union[float, str]]]
) -> Tuple[List[str], List[float]]:
    months: List[str] = []
    cumulative: List[float] = []
    running = 0.0
    for item in monthly_stats:
        months.append(item["month"])
        running += float(item["total_expenses"])
        cumulative.append(running)
    return months, cumulative
