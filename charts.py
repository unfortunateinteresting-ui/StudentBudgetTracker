import io
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import calculations
from .db import Settings, Transaction
from .localization import translated_category


CATEGORY_COLORS = [
    "#2A9D8F",
    "#457B9D",
    "#E76F51",
    "#F4A261",
    "#3D405B",
    "#90BE6D",
    "#F2CC8F",
    "#8E7DBE",
    "#6C757D",
    "#BC6C25",
]
LINE_PRIMARY = "#1B2A41"
LINE_ACCENT = "#E76F51"
LINE_BALANCE = "#2A9D8F"
LINE_MUTED = "#6C757D"
CHART_TEXT = {
    "EN": {
        "uncategorized": "Uncategorized",
        "monthly_spending_title": "Monthly Spending by Category",
        "no_expense_data": "No expense data",
        "monthly_total": "Monthly total",
        "average_to_date": "Average to date",
        "amount_axis": "Amount",
        "balance_axis": "Balance",
        "cumulative_title": "Cumulative Spending vs Plan",
        "cumulative_expenses": "Cumulative expenses",
        "planned_total": "Planned total",
        "predicted_total": "Predicted total",
        "running_balance_title": "Running Balance",
        "starting_point": "Starting point",
        "zero_line": "Zero line",
        "category_average_title": "Average Monthly Spend by Category",
        "no_category_history": "No category history",
        "average_per_month": "Average per month",
    },
    "FR": {
        "uncategorized": "Sans categorie",
        "monthly_spending_title": "Depenses mensuelles par categorie",
        "no_expense_data": "Aucune depense",
        "monthly_total": "Total mensuel",
        "average_to_date": "Moyenne a ce jour",
        "amount_axis": "Montant",
        "balance_axis": "Solde",
        "cumulative_title": "Depenses cumulatives vs plan",
        "cumulative_expenses": "Depenses cumulatives",
        "planned_total": "Total planifie",
        "predicted_total": "Total predit",
        "running_balance_title": "Solde cumulatif",
        "starting_point": "Point de depart",
        "zero_line": "Ligne zero",
        "category_average_title": "Depense mensuelle moyenne par categorie",
        "no_category_history": "Aucun historique par categorie",
        "average_per_month": "Moyenne par mois",
    },
}


def _fig_to_png_bytes(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=165, bbox_inches="tight", pad_inches=0.24)
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()


def _chart_text(language: str = "EN") -> Dict[str, str]:
    return CHART_TEXT.get((language or "EN").upper(), CHART_TEXT["EN"])


def _category_name(value: str, language: str = "EN") -> str:
    text = (value or "").strip()
    if not text:
        return _chart_text(language)["uncategorized"]
    return translated_category(text, language)


def _rent_chart_category_name(tx: Transaction, language: str = "EN") -> str:
    if calculations._is_rent_text(tx.category or ""):
        return _category_name(tx.category, language)
    return translated_category("rent", language)


def _monthly_category_totals(
    transactions: List[Transaction],
    language: str = "EN",
) -> Dict[str, Dict[str, float]]:
    monthly: Dict[str, Dict[str, float]] = {}
    for tx in transactions:
        if calculations._is_adjustment_tx(tx):
            continue
        tx_dt = calculations._try_parse_datetime(tx.datetime_local)
        if tx_dt is None:
            continue
        month_key = tx_dt.strftime("%Y-%m")
        monthly.setdefault(month_key, {})
        if tx.type == "expense":
            category = _category_name(tx.category, language)
            monthly[month_key][category] = monthly[month_key].get(category, 0.0) + tx.amount
        elif calculations._is_rent_credit_tx(tx):
            category = _rent_chart_category_name(tx, language)
            monthly[month_key][category] = monthly[month_key].get(category, 0.0) - tx.amount
    for month_data in monthly.values():
        for category, amount in list(month_data.items()):
            month_data[category] = max(0.0, amount)
    return monthly


def _sorted_categories(monthly: Dict[str, Dict[str, float]]) -> List[str]:
    category_totals: Dict[str, float] = {}
    for month_data in monthly.values():
        for category, amount in month_data.items():
            category_totals[category] = category_totals.get(category, 0.0) + amount
    return sorted(
        category_totals.keys(), key=lambda key: category_totals[key], reverse=True
    )


def render_monthly_spending(
    transactions: List[Transaction],
    language: str = "EN",
) -> bytes:
    labels = _chart_text(language)
    monthly = _monthly_category_totals(transactions, language)
    months = sorted(monthly.keys())
    if not months:
        fig, ax = plt.subplots(figsize=(7.6, 4.1))
        ax.set_title(labels["monthly_spending_title"])
        ax.text(0.5, 0.5, labels["no_expense_data"], ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        return _fig_to_png_bytes(fig)

    categories = _sorted_categories(monthly)

    monthly_totals = [sum(monthly[month].values()) for month in months]
    running_total = 0.0
    rolling_average: List[float] = []
    for index, total in enumerate(monthly_totals, start=1):
        running_total += total
        rolling_average.append(running_total / index)

    legend_columns = 1 if len(categories) <= 8 else 2
    figure_height = min(6.4, max(4.0, 2.2 + (0.24 * len(categories))))
    fig, ax = plt.subplots(figsize=(7.6, figure_height))
    bottoms = [0.0 for _ in months]
    for idx, category in enumerate(categories):
        values = [monthly[month].get(category, 0.0) for month in months]
        ax.bar(
            months,
            values,
            bottom=bottoms,
            color=CATEGORY_COLORS[idx % len(CATEGORY_COLORS)],
            label=category,
        )
        bottoms = [bottoms[i] + values[i] for i in range(len(values))]
    ax.plot(
        months,
        monthly_totals,
        color=LINE_PRIMARY,
        marker="o",
        linewidth=2.2,
        label=labels["monthly_total"],
    )
    ax.plot(
        months,
        rolling_average,
        color=LINE_MUTED,
        linestyle="--",
        linewidth=2.0,
        label=labels["average_to_date"],
    )
    ax.set_title(labels["monthly_spending_title"])
    ax.set_ylabel(labels["amount_axis"])
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", linestyle=":", alpha=0.25)
    ax.legend(
        ncol=legend_columns,
        fontsize=8,
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )
    fig.subplots_adjust(right=0.76 if legend_columns == 1 else 0.66)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def _budget_cumulative_series(
    monthly_stats: List[dict],
    key: str,
    fallback_key: str = "monthly_budget",
) -> tuple[List[str], List[float]]:
    months: List[str] = []
    cumulative: List[float] = []
    running_total = 0.0
    for item in monthly_stats:
        month_key = str(item.get("month", "")).strip()
        if not month_key:
            continue
        running_total += float(item.get(key, item.get(fallback_key, 0.0)) or 0.0)
        months.append(month_key)
        cumulative.append(running_total)
    return months, cumulative


def _planned_cumulative_series(monthly_stats: List[dict]) -> tuple[List[str], List[float]]:
    return _budget_cumulative_series(monthly_stats, "monthly_budget_planned")


def render_cumulative_vs_plan(
    monthly_stats: List[dict],
    language: str = "EN",
) -> bytes:
    labels = _chart_text(language)
    months, cumulative = calculations.cumulative_expenses_by_month(monthly_stats)
    plan_months, planned_cumulative = _planned_cumulative_series(monthly_stats)
    predicted_months, predicted_cumulative = _budget_cumulative_series(
        monthly_stats, "monthly_budget_predicted"
    )
    fig, ax = plt.subplots(figsize=(7.6, 4.1))
    ax.plot(
        months,
        cumulative,
        marker="o",
        color=LINE_PRIMARY,
        label=labels["cumulative_expenses"],
    )
    if plan_months:
        ax.plot(
            plan_months,
            planned_cumulative,
            linestyle="--",
            color=LINE_ACCENT,
            label=labels["planned_total"],
        )
    if predicted_months:
        ax.plot(
            predicted_months,
            predicted_cumulative,
            linestyle=":",
            linewidth=2.2,
            color=LINE_BALANCE,
            label=labels["predicted_total"],
        )
    ax.set_title(labels["cumulative_title"])
    ax.set_ylabel(labels["amount_axis"])
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", linestyle=":", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def render_running_balance(
    transactions: List[Transaction],
    settings: Settings,
    language: str = "EN",
) -> bytes:
    labels = _chart_text(language)
    dates, balances = calculations.running_balance_series(
        transactions, settings.starting_balance, settings.refunds_total
    )
    fig, ax = plt.subplots(figsize=(7.6, 4.1))
    ax.plot(dates, balances, color=LINE_BALANCE, linewidth=2.2)
    ax.axhline(
        settings.starting_balance + settings.refunds_total,
        color=LINE_MUTED,
        linestyle="--",
        linewidth=1.5,
        label=labels["starting_point"],
    )
    ax.axhline(
        0.0,
        color=LINE_ACCENT,
        linestyle=":",
        linewidth=1.3,
        label=labels["zero_line"],
    )
    ax.set_title(labels["running_balance_title"])
    ax.set_ylabel(labels["balance_axis"])
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", linestyle=":", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def render_category_averages(
    transactions: List[Transaction],
    language: str = "EN",
) -> bytes:
    labels = _chart_text(language)
    stats = calculations.calculate_category_average_rows(transactions)
    rows = list(stats.get("rows", []))
    if not rows:
        fig, ax = plt.subplots(figsize=(7.6, 4.1))
        ax.set_title(labels["category_average_title"])
        ax.text(0.5, 0.5, labels["no_category_history"], ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        return _fig_to_png_bytes(fig)

    categories = [
        translated_category(str(row.get("category", "")), language)
        for row in reversed(rows)
    ]
    averages = [float(row.get("average_monthly", 0.0) or 0.0) for row in reversed(rows)]

    figure_height = max(4.0, 2.0 + (0.42 * len(categories)))
    fig, ax = plt.subplots(figsize=(7.6, figure_height))
    colors = [CATEGORY_COLORS[index % len(CATEGORY_COLORS)] for index in range(len(categories))]
    ax.barh(categories, averages, color=colors)
    for index, value in enumerate(averages):
        ax.text(value, index, f" {value:.0f}", va="center", ha="left", fontsize=8)
    ax.set_title(labels["category_average_title"])
    ax.set_xlabel(labels["average_per_month"])
    ax.grid(axis="x", linestyle=":", alpha=0.25)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)
