import re
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from typing import Dict, List, Optional, Union

import importlib
from PySide6 import QtCore, QtGui, QtWidgets

APP_TITLE = "Offline Budget Tracker"
APP_PACKAGE = "Offline_budget_tracker"
APP_ORGANIZATION = "OfflineBudgetTracker"

if __package__ is None or __package__ == "":
    if not getattr(sys, "frozen", False):
        package_root = Path(__file__).resolve().parent.parent
        if str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))
    calculations = importlib.import_module(f"{APP_PACKAGE}.calculations")
    charts = importlib.import_module(f"{APP_PACKAGE}.charts")
    reports = importlib.import_module(f"{APP_PACKAGE}.reports")
    importer = importlib.import_module(f"{APP_PACKAGE}.importer")
    app_state_mod = importlib.import_module(f"{APP_PACKAGE}.app_state")
    db_mod = importlib.import_module(f"{APP_PACKAGE}.db")
    localization_mod = importlib.import_module(f"{APP_PACKAGE}.localization")
    DEFAULT_SETTINGS = db_mod.DEFAULT_SETTINGS
    Database = db_mod.Database
    RecurringCharge = db_mod.RecurringCharge
    Settings = db_mod.Settings
    Transaction = db_mod.Transaction
    translated_category = localization_mod.translated_category
    local_now_iso = db_mod.local_now_iso
    load_computed_app_state = app_state_mod.load_computed_app_state
else:
    from . import calculations, charts, reports, importer
    from .app_state import load_computed_app_state
    from .db import (
        DEFAULT_SETTINGS,
        Database,
        RecurringCharge,
        Settings,
        Transaction,
        local_now_iso,
    )
    from .localization import translated_category


def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base_path = Path(__file__).resolve().parent
    return base_path.joinpath(*parts)


def load_app_icon() -> QtGui.QIcon:
    icon_path = resource_path("assets", "app_icon.png")
    if not icon_path.exists():
        return QtGui.QIcon()
    return QtGui.QIcon(str(icon_path))


def load_app_brand_pixmap(size: int = 88) -> QtGui.QPixmap:
    icon_path = resource_path("assets", "app_icon.png")
    if not icon_path.exists():
        return QtGui.QPixmap()
    pixmap = QtGui.QPixmap(str(icon_path))
    if pixmap.isNull():
        return QtGui.QPixmap()
    return pixmap.scaled(
        size,
        size,
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )


CATEGORY_DEFAULTS = [
    "rent",
    "utilities",
    "food",
    "transport",
    "internet",
    "phone",
    "insurance",
    "medical",
    "school",
    "household",
    "health",
    "subscriptions",
    "entertainment",
    "travel",
    "clothing",
    "gifts",
    "pets",
    "debt",
    "fees",
    "income",
    "adjustment",
    "misc",
]
RECURRING_STATUSES = ["automatic", "manual", "paused"]
RECURRING_FREQUENCIES = ["monthly", "weekly", "daily"]
UI_TEXT = {
    "EN": {
        "app_title": "Offline Budget Tracker",
        "tab_add": "Add Entry",
        "tab_transactions": "Transactions",
        "tab_dashboard": "Dashboard",
        "tab_recurring": "Recurring",
        "tab_report": "Report",
        "tab_welcome": "Welcome",
        "welcome_title": "Welcome",
        "welcome_subtitle": "Customize your view and jump to any section.",
        "welcome_customize_title": "Customize",
        "welcome_customize_hint": "Choose a theme, font, and accent color.",
        "welcome_theme_label": "Theme",
        "welcome_font_label": "Font",
        "welcome_accent_label": "Accent color",
        "welcome_pick_accent": "Pick color",
        "welcome_reset_accent": "Reset color",
        "welcome_nav_title": "Navigate",
        "nav_add": "Add Entry",
        "nav_transactions": "Transactions",
        "nav_dashboard": "Dashboard & Settings",
        "nav_recurring": "Recurring",
        "nav_report": "Reports",
        "theme_applied": "Theme applied.",
        "add_title": "Add Entry",
        "add_subtitle": "Quick capture or detailed entry, saved instantly.",
        "quick_title": "Quick Entry",
        "quick_hint": "Type amount then label. Example: 42 Walmart",
        "quick_button": "Quick Save",
        "details_title": "Details",
        "save_entry": "Save Entry",
        "add_placeholder": "Quick entry: 42 Walmart",
        "field_amount": "Amount",
        "field_label": "Label",
        "field_category": "Category",
        "field_type": "Type",
        "field_notes": "Notes",
        "field_date": "Date",
        "exclude_from_averages": "Exclude from auto averages",
        "tx_title": "Transactions",
        "tx_search": "Search label, notes, category",
        "tx_edit": "Edit",
        "tx_delete": "Delete",
        "dash_title": "Dashboard",
        "dash_subtitle": "The clearest view of your money right now, this month, and what comes next.",
        "dashboard_helper": "Start with Current balance, Left this month, and Net rent. The tables below break down the rest.",
        "summary_title": "Key details",
        "summary_search_placeholder": "Find a metric...",
        "reconcile_title": "Fix balance",
        "reconcile_hint": "If the balance looks wrong, enter the real balance and the app will add one adjustment entry.",
        "reconcile_button": "Fix Balance",
        "settings_title": "Settings",
        "monthly_title": "Monthly plan vs actual",
        "charts_title": "Charts",
        "category_average_title": "Category averages",
        "category_average_headers": ["Category", "Avg / month", "Total", "Months used"],
        "chart_titles": [
            "Monthly spending by category",
            "Cumulative vs plan",
            "Running balance",
            "Category averages",
        ],
        "chart_click_hint": "Click a chart to open a larger view.",
        "chart_preview_title": "Chart preview",
        "dashboard_nav_title": "Quick actions",
        "advanced_notes_show": "Show advanced details",
        "advanced_notes_hide": "Hide advanced details",
        "report_title": "Reports",
        "report_subtitle": "Export a polished PDF summary with tables and charts.",
        "report_info": "Export a PDF or Excel report with tables and graphs.",
        "report_pdf_language_label": "PDF language",
        "report_pdf_language_hint": "Choose whether the PDF is generated in English or French.",
        "export_title": "Export",
        "import_title": "Import",
        "import_hint": "Import JSON, CSV, or Excel files.",
        "export_pdf": "Export PDF",
        "export_excel": "Export Excel",
        "export_json": "Export JSON",
        "import_button": "Import Data",
        "reset_data_button": "Reset Data",
        "reset_data_title": "Reset current data?",
        "reset_data_confirm": "This will clear the current app data, including transactions, recurring charges, categories, and budget settings. A backup is created automatically. Your language and theme stay the same. Continue?",
        "reset_data_done": "Current app data was reset.",
        "recurring_title": "Recurring Charges",
        "recurring_subtitle": "Automatic, manual, or paused charges that apply on a schedule.",
        "recurring_form_title": "Add recurring charge",
        "recurring_table_title": "Recurring list",
        "recurring_save": "Save Recurring",
        "recurring_apply": "Apply Selected",
        "recurring_edit": "Edit",
        "recurring_delete": "Delete",
        "recurring_label": "Label",
        "recurring_amount": "Amount",
        "recurring_type": "Type",
        "recurring_category": "Category",
        "recurring_notes": "Notes",
        "recurring_start": "Start date",
        "recurring_end": "Has end date",
        "recurring_frequency": "Frequency",
        "recurring_status": "Status",
        "export_pdf_title": "Export PDF",
        "export_excel_title": "Export Excel",
        "export_json_title": "Export JSON",
        "import_dialog_title": "Import Data",
        "import_dialog_filter": "Import Files (*.json *.csv *.xlsx *.xlsm);;JSON Files (*.json);;CSV Files (*.csv);;Excel Files (*.xlsx *.xlsm);;All Files (*)",
        "export_pdf_default": "budget_report",
        "export_excel_default": "budget_export",
        "export_json_default": "budget_history_export",
        "export_pdf_saved": "Report saved: {path}",
        "export_excel_saved": "Excel saved: {path}",
        "export_json_saved": "JSON saved: {path}",
        "export_failed": "Export failed: {error}",
        "import_failed": "Import failed: {error}",
        "import_result": "Imported {added} transactions, skipped {skipped} ({settings_text}).",
        "import_partial_warning": "Some rows were skipped. Hover for details.",
        "import_multiple_same_type": "Pick at most one JSON, one CSV, and one Excel file per import.",
        "settings_updated": "settings updated",
        "settings_unchanged": "settings unchanged",
        "settings_applied": "Settings applied.",
        "settings_pending": "Pending changes",
        "no_selection_edit": "Select a transaction to edit.",
        "no_selection_delete": "Select a transaction to delete.",
        "recurring_select_edit": "Select a recurring charge to edit.",
        "recurring_select_delete": "Select a recurring charge to delete.",
        "recurring_select_apply": "Select a recurring charge to apply.",
        "recurring_saved": "Recurring saved.",
        "recurring_updated": "Recurring updated.",
        "recurring_deleted": "Recurring deleted.",
        "recurring_applied": "Applied to transactions.",
        "recurring_nothing": "Nothing to apply yet.",
        "recurring_label_required": "Label is required.",
        "recurring_amount_required": "Amount must be greater than 0.",
        "recurring_end_after": "End date must be after start date.",
        "tx_deleted": "Deleted.",
        "tx_updated": "Updated.",
        "tx_saved": "Saved.",
        "amount_required": "Amount must be greater than 0.",
        "quick_entry_invalid": "Quick entry needs a number and label.",
        "monthly_avg_last": "Monthly average (last {months} mo)",
        "monthly_avg_school_year": "Monthly average (school year)",
        "apply_settings": "Apply Settings",
        "add_category_button": "Add",
        "mode_manual": "Manual",
        "mode_auto": "Auto",
        "calc_title": "Calculation notes",
        "auto_calc_title": "Auto calculation notes",
        "category_placeholder": "New category",
        "category_status_empty": "Enter a category.",
        "category_status_added": "Category added.",
        "category_status_exists": "Category already exists.",
        "reconcile_apply_first": "Apply settings before reconciling.",
        "reconcile_no_change": "Balance already matches.",
        "reconcile_posted": "Posted adjustment {delta}.",
        "no_data": "No data",
        "all_months": "All",
        "invalid_date_group": "Invalid date",
        "month_total_label": "{month} total",
        "total_label": "Total",
        "school_year": "School year",
        "month_suffix": " mo",
        "remaining_to_date_tooltip": "Budget to date {budget:.2f} - spent {spent:.2f} = left {remaining:.2f}",
        "remaining_full_tooltip": "Full-month budget {budget:.2f} - spent {spent:.2f} = left {remaining:.2f}\nIncludes recurring charges still scheduled later this month.",
        "dialog_save": "Save",
        "dialog_cancel": "Cancel",
        "dialog_close": "Close",
        "edit_transaction_title": "Edit Transaction",
        "edit_recurring_title": "Edit Recurring Charge",
        "missed_recurring_title": "Apply missed recurring charges?",
        "missed_recurring_summary": "Found {total} missed recurring transactions.\nApply them now?\n\n{details}",
        "missed_recurring_item": "- {label} ({frequency}): {count} ({date_range})",
        "missed_recurring_more": "- ... and {extra} more",
        "missed_recurring_applied": "Applied {count} missed recurring charges.",
        "missed_recurring_skipped": "Missed recurring charges not applied.",
        "recurring_default_label": "Recurring",
        "undo_label": "Undo",
        "undo_empty": "Nothing to undo.",
        "undo_applied": "Undid: {label}",
        "undo_add_tx": "Add transaction",
        "undo_edit_tx": "Edit transaction",
        "undo_delete_tx": "Delete transaction",
        "undo_add_recurring": "Add recurring",
        "undo_edit_recurring": "Edit recurring",
        "undo_delete_recurring": "Delete recurring",
        "undo_reconcile": "Reconcile adjustment",
        "plan_complete": "Plan complete",
        "category_average_hint_data": (
            "Average monthly spend across {months_count} months with expense history. "
            "Transactions excluded from averages are skipped."
        ),
        "category_average_hint_empty": (
            "Add a few expense transactions to see category averages."
        ),
        "summary_labels": {
            "estimated_balance": "Current balance",
            "total_expenses": "Spent so far",
            "total_income": "Income so far",
            "adjustments_total": "Adjustments total",
            "current_month_expenses": "Spent this month",
            "current_month_income": "Income this month",
            "current_month_adjustments": "Adjustments this month",
            "rent_month_paid": "Net rent this month",
            "rent_month_income_offset": "Rent credits this month",
            "plan_budget_total": "Planned total",
            "projected_final_expenses": "Predicted total",
            "planned_remaining_total": "Planned remaining",
            "predicted_remaining_total": "Predicted remaining",
            "windowed_avg_monthly": "Recent monthly average",
            "average_expenses": "Average per month",
            "essential_month_used_pct_planned": "Essential % used (month, planned)",
            "essential_month_used_pct_predicted": "Essential % used (month, predicted)",
            "essential_year_used_pct_planned": "Essential % used (year, planned)",
            "essential_year_used_pct_predicted": "Essential % used (year, predicted)",
            "rent_month_used_pct_planned": "Rent % used (month, planned)",
            "rent_month_used_pct_predicted": "Rent % used (month, predicted)",
            "rent_year_used_pct_planned": "Rent % used (year, planned)",
            "rent_year_used_pct_predicted": "Rent % used (year, predicted)",
            "savings_vs_campus_planned": "Savings vs campus (planned)",
            "savings_vs_campus_predicted": "Savings vs campus (predicted)",
            "current_month_remaining": "Left this month",
            "current_month_remaining_full": "Current month remaining (full schedule)",
            "coverage_display": "Months covered",
            "coverage_12mo_display": "12-month runway",
        },
        "dashboard_highlights": {
            "estimated_balance": "Current balance",
            "current_month_remaining": "Left this month",
            "rent_month_paid": "Net rent this month",
            "average_expenses": "Average per month",
        },
        "summary_sections": {
            "snapshot": "Right now",
            "month_focus": "This month",
            "forecast_view": "Looking ahead",
            "avg_view": "Averages & runway",
            "budget_health": "Budget health",
        },
        "settings_labels": {
            "starting_balance": "Starting balance",
            "refunds_total": "Refunds total",
            "plan_months_total": "Plan months total",
            "months_elapsed": "Months elapsed (auto)",
            "months_remaining": "Months remaining (auto)",
            "rent_manual": "Rent monthly (manual)",
            "food_manual": "Food monthly (manual)",
            "medical_manual": "Medical monthly (manual)",
            "school_manual": "School monthly (manual)",
            "household_manual": "Household monthly (manual)",
            "health_manual": "Health monthly (manual)",
            "projection_mode": "Projection mode",
            "misc_manual": "Misc monthly (manual)",
            "add_category": "Add category",
            "extra_monthly": "Extra monthly (12 mo)",
            "campus_reference": "Campus reference total",
            "language": "Language",
        },
        "auto_labels": {
            "title": "Auto projection",
            "include_recurring": "Include recurring",
            "include_current_month": "Include current month",
            "window_months": "Window months",
            "weighted": "Weighted",
            "half_life": "Weight half-life",
            "categories": "Auto categories",
            "monthly_total": "Auto monthly total",
        },
        "auto_recurring_excluded": "Recurring categories excluded from auto averages: {categories}",
        "tx_table_headers": [
            "Date",
            "Type",
            "Amount",
            "Label",
            "Category",
            "Notes",
            "Over % (proj)",
        ],
        "monthly_table_headers": [
            "Month",
            "Budget (plan)",
            "Budget (proj)",
            "Total expenses",
            "Adjustments",
            "Delta $",
            "Delta %",
        ],
        "recurring_table_headers": [
            "Label",
            "Type",
            "Amount",
            "Category",
            "Frequency",
            "Start",
            "End",
            "Status",
            "Last applied",
        ],
    },
    "FR": {
        "app_title": "Suivi Budget Hors Ligne",
        "tab_add": "Ajouter",
        "tab_transactions": "Transactions",
        "tab_dashboard": "Tableau",
        "tab_recurring": "Recurrent",
        "tab_report": "Rapport",
        "tab_welcome": "Accueil",
        "welcome_title": "Bienvenue",
        "welcome_subtitle": "Personnalisez et allez a n'importe quelle section.",
        "welcome_customize_title": "Personnaliser",
        "welcome_customize_hint": "Choisissez un theme, une police, et une couleur.",
        "welcome_theme_label": "Theme",
        "welcome_font_label": "Police",
        "welcome_accent_label": "Couleur accent",
        "welcome_pick_accent": "Choisir",
        "welcome_reset_accent": "Reinitialiser",
        "welcome_nav_title": "Navigation",
        "nav_add": "Ajouter",
        "nav_transactions": "Transactions",
        "nav_dashboard": "Tableau & reglages",
        "nav_recurring": "Recurrent",
        "nav_report": "Rapports",
        "theme_applied": "Theme applique.",
        "add_title": "Ajouter",
        "add_subtitle": "Saisie rapide ou detaillee, enregistre instantanement.",
        "quick_title": "Saisie rapide",
        "quick_hint": "Tapez montant puis libelle. Exemple: 42 Walmart",
        "quick_button": "Sauver rapide",
        "details_title": "Details",
        "save_entry": "Sauver",
        "add_placeholder": "Saisie rapide: 42 Walmart",
        "field_amount": "Montant",
        "field_label": "Libelle",
        "field_category": "Categorie",
        "field_type": "Type",
        "field_notes": "Notes",
        "field_date": "Date",
        "exclude_from_averages": "Exclure des moyennes auto",
        "tx_title": "Transactions",
        "tx_search": "Chercher libelle, notes, categorie",
        "tx_edit": "Modifier",
        "tx_delete": "Supprimer",
        "dash_title": "Tableau de bord",
        "dash_subtitle": "La vue la plus simple de votre argent maintenant, ce mois-ci, et pour la suite.",
        "dashboard_helper": "Commencez par le solde actuel, le reste du mois, et le loyer net. Les tableaux ci-dessous montrent le detail.",
        "summary_title": "Details cles",
        "summary_search_placeholder": "Trouver une mesure...",
        "reconcile_title": "Corriger le solde",
        "reconcile_hint": "Si le solde semble faux, entrez le vrai solde et l'application ajoutera un ajustement.",
        "reconcile_button": "Corriger le solde",
        "settings_title": "Reglages",
        "monthly_title": "Plan mensuel vs reel",
        "charts_title": "Graphiques",
        "category_average_title": "Moyennes par categorie",
        "category_average_headers": ["Categorie", "Moy / mois", "Total", "Mois utilises"],
        "chart_titles": [
            "Depenses par categorie",
            "Cumul vs plan",
            "Solde cumulatif",
            "Moyennes par categorie",
        ],
        "chart_click_hint": "Cliquez sur un graphique pour l'ouvrir en grand.",
        "chart_preview_title": "Apercu du graphique",
        "dashboard_nav_title": "Actions rapides",
        "advanced_notes_show": "Afficher les details avances",
        "advanced_notes_hide": "Masquer les details avances",
        "report_title": "Rapports",
        "report_subtitle": "Exporter un PDF avec tableaux et graphiques.",
        "report_info": "Exporter un rapport PDF ou Excel avec tableaux et graphiques.",
        "report_pdf_language_label": "Langue du PDF",
        "report_pdf_language_hint": "Choisissez si le PDF est genere en anglais ou en francais.",
        "export_title": "Exporter",
        "import_title": "Importer",
        "import_hint": "Importer des fichiers JSON, CSV, ou Excel.",
        "export_pdf": "Exporter PDF",
        "export_excel": "Exporter Excel",
        "export_json": "Exporter JSON",
        "import_button": "Importer",
        "reset_data_button": "Reinitialiser les donnees",
        "reset_data_title": "Reinitialiser les donnees actuelles ?",
        "reset_data_confirm": "Cela supprimera les donnees actuelles de l'application, y compris les transactions, charges recurrentes, categories, et reglages budgetaires. Une sauvegarde est creee automatiquement. Votre langue et votre theme restent les memes. Continuer ?",
        "reset_data_done": "Les donnees actuelles ont ete reinitialisees.",
        "recurring_title": "Charges recurrentes",
        "recurring_subtitle": "Charges automatiques, manuelles, ou en pause.",
        "recurring_form_title": "Ajouter charge recurrente",
        "recurring_table_title": "Liste recurrente",
        "recurring_save": "Sauver recurrent",
        "recurring_apply": "Appliquer",
        "recurring_edit": "Modifier",
        "recurring_delete": "Supprimer",
        "recurring_label": "Libelle",
        "recurring_amount": "Montant",
        "recurring_type": "Type",
        "recurring_category": "Categorie",
        "recurring_notes": "Notes",
        "recurring_start": "Date debut",
        "recurring_end": "Date fin",
        "recurring_frequency": "Frequence",
        "recurring_status": "Statut",
        "export_pdf_title": "Exporter PDF",
        "export_excel_title": "Exporter Excel",
        "export_json_title": "Exporter JSON",
        "import_dialog_title": "Importer",
        "import_dialog_filter": "Fichiers d'importation (*.json *.csv *.xlsx *.xlsm);;Fichiers JSON (*.json);;Fichiers CSV (*.csv);;Fichiers Excel (*.xlsx *.xlsm);;Tous les fichiers (*)",
        "export_pdf_default": "rapport_budget",
        "export_excel_default": "export_budget",
        "export_json_default": "historique_budget_export",
        "export_pdf_saved": "Rapport sauvegarde: {path}",
        "export_excel_saved": "Excel sauvegarde: {path}",
        "export_json_saved": "JSON sauvegarde: {path}",
        "export_failed": "Export echoue: {error}",
        "import_failed": "Import echoue: {error}",
        "import_result": "Importe {added} transactions, ignore {skipped} ({settings_text}).",
        "import_partial_warning": "Certaines lignes ont ete ignorees. Survolez pour les details.",
        "import_multiple_same_type": "Choisissez au plus un fichier JSON, un CSV et un fichier Excel par importation.",
        "settings_updated": "reglages mis a jour",
        "settings_unchanged": "reglages inchanges",
        "settings_applied": "Reglages appliques.",
        "settings_pending": "Changements en attente",
        "no_selection_edit": "Selectionnez une transaction.",
        "no_selection_delete": "Selectionnez une transaction.",
        "recurring_select_edit": "Selectionnez une charge.",
        "recurring_select_delete": "Selectionnez une charge.",
        "recurring_select_apply": "Selectionnez une charge.",
        "recurring_saved": "Recurrent sauvegarde.",
        "recurring_updated": "Recurrent mis a jour.",
        "recurring_deleted": "Recurrent supprime.",
        "recurring_applied": "Applique aux transactions.",
        "recurring_nothing": "Rien a appliquer.",
        "recurring_label_required": "Libelle requis.",
        "recurring_amount_required": "Montant doit etre > 0.",
        "recurring_end_after": "La fin doit etre apres le debut.",
        "tx_deleted": "Supprime.",
        "tx_updated": "Mis a jour.",
        "tx_saved": "Sauve.",
        "amount_required": "Montant doit etre > 0.",
        "quick_entry_invalid": "La saisie rapide doit avoir un nombre et un libelle.",
        "monthly_avg_last": "Moyenne mensuelle (dernier {months} mois)",
        "monthly_avg_school_year": "Moyenne mensuelle (annee scolaire)",
        "apply_settings": "Appliquer",
        "add_category_button": "Ajouter",
        "mode_manual": "Manuel",
        "mode_auto": "Auto",
        "calc_title": "Notes de calcul",
        "auto_calc_title": "Notes de calcul auto",
        "category_placeholder": "Nouvelle categorie",
        "category_status_empty": "Entrez une categorie.",
        "category_status_added": "Categorie ajoutee.",
        "category_status_exists": "Categorie existe deja.",
        "reconcile_apply_first": "Appliquez les reglages avant reconciliation.",
        "reconcile_no_change": "Le solde correspond deja.",
        "reconcile_posted": "Ajustement ajoute {delta}.",
        "no_data": "Aucune donnee",
        "all_months": "Tous",
        "invalid_date_group": "Date invalide",
        "month_total_label": "Total {month}",
        "total_label": "Total",
        "school_year": "Annee scolaire",
        "month_suffix": " mois",
        "remaining_to_date_tooltip": "Budget a ce jour {budget:.2f} - depense {spent:.2f} = reste {remaining:.2f}",
        "remaining_full_tooltip": "Budget du mois complet {budget:.2f} - depense {spent:.2f} = reste {remaining:.2f}\nInclut les charges recurrentes encore prevues plus tard ce mois-ci.",
        "dialog_save": "Sauver",
        "dialog_cancel": "Annuler",
        "dialog_close": "Fermer",
        "edit_transaction_title": "Modifier transaction",
        "edit_recurring_title": "Modifier charge recurrente",
        "missed_recurring_title": "Appliquer les charges ratees?",
        "missed_recurring_summary": "Trouve {total} charges recurrentes ratees.\nAppliquer maintenant?\n\n{details}",
        "missed_recurring_item": "- {label} ({frequency}) : {count} ({date_range})",
        "missed_recurring_more": "- ... et {extra} de plus",
        "missed_recurring_applied": "Applique {count} charges ratees.",
        "missed_recurring_skipped": "Charges ratees non appliquees.",
        "recurring_default_label": "Recurrent",
        "undo_label": "Annuler",
        "undo_empty": "Rien a annuler.",
        "undo_applied": "Annule : {label}",
        "undo_add_tx": "Ajouter transaction",
        "undo_edit_tx": "Modifier transaction",
        "undo_delete_tx": "Supprimer transaction",
        "undo_add_recurring": "Ajouter recurrent",
        "undo_edit_recurring": "Modifier recurrent",
        "undo_delete_recurring": "Supprimer recurrent",
        "undo_reconcile": "Ajustement reconciliation",
        "plan_complete": "Plan termine",
        "category_average_hint_data": (
            "Moyenne mensuelle sur {months_count} mois avec historique de depenses. "
            "Les transactions exclues des moyennes sont ignorees."
        ),
        "category_average_hint_empty": (
            "Ajoutez quelques depenses pour afficher les moyennes par categorie."
        ),
        "summary_labels": {
            "estimated_balance": "Solde actuel",
            "total_expenses": "Depenses a ce jour",
            "total_income": "Revenus a ce jour",
            "adjustments_total": "Total ajustements",
            "current_month_expenses": "Depenses du mois",
            "current_month_income": "Revenus du mois",
            "current_month_adjustments": "Ajustements du mois",
            "rent_month_paid": "Loyer net du mois",
            "rent_month_income_offset": "Credits loyer du mois",
            "plan_budget_total": "Total planifie",
            "projected_final_expenses": "Total predit",
            "planned_remaining_total": "Reste planifie",
            "predicted_remaining_total": "Reste predit",
            "windowed_avg_monthly": "Moyenne mensuelle recente",
            "average_expenses": "Moyenne par mois",
            "essential_month_used_pct_planned": "% essentiel utilise (mois, planifie)",
            "essential_month_used_pct_predicted": "% essentiel utilise (mois, predit)",
            "essential_year_used_pct_planned": "% essentiel utilise (annee, planifie)",
            "essential_year_used_pct_predicted": "% essentiel utilise (annee, predit)",
            "rent_month_used_pct_planned": "% loyer utilise (mois, planifie)",
            "rent_month_used_pct_predicted": "% loyer utilise (mois, predit)",
            "rent_year_used_pct_planned": "% loyer utilise (annee, planifie)",
            "rent_year_used_pct_predicted": "% loyer utilise (annee, predit)",
            "savings_vs_campus_planned": "Economie vs campus (planifie)",
            "savings_vs_campus_predicted": "Economie vs campus (predite)",
            "current_month_remaining": "Reste du mois",
            "current_month_remaining_full": "Reste mois (tout planifie)",
            "coverage_display": "Mois couverts",
            "coverage_12mo_display": "Couverture sur 12 mois",
        },
        "dashboard_highlights": {
            "estimated_balance": "Solde actuel",
            "current_month_remaining": "Reste du mois",
            "rent_month_paid": "Loyer net du mois",
            "average_expenses": "Moyenne par mois",
        },
        "summary_sections": {
            "snapshot": "Vue rapide",
            "month_focus": "Ce mois",
            "forecast_view": "Pour la suite",
            "avg_view": "Moyennes et couverture",
            "budget_health": "Sante du budget",
        },
        "settings_labels": {
            "starting_balance": "Solde initial",
            "refunds_total": "Total remboursements",
            "plan_months_total": "Total mois plan",
            "months_elapsed": "Mois ecoules (auto)",
            "months_remaining": "Mois restants (auto)",
            "rent_manual": "Loyer mensuel (manuel)",
            "food_manual": "Nourriture mensuel (manuel)",
            "medical_manual": "Medical mensuel (manuel)",
            "school_manual": "Ecole mensuel (manuel)",
            "household_manual": "Maison mensuel (manuel)",
            "health_manual": "Sante mensuel (manuel)",
            "projection_mode": "Mode de projection",
            "misc_manual": "Divers mensuel (manuel)",
            "add_category": "Ajouter categorie",
            "extra_monthly": "Extra mensuel (12 mois)",
            "campus_reference": "Reference campus",
            "language": "Langue",
        },
        "auto_labels": {
            "title": "Projection auto",
            "include_recurring": "Inclure recurrent",
            "include_current_month": "Inclure mois actuel",
            "window_months": "Fenetre (mois)",
            "weighted": "Pondere",
            "half_life": "Demi-vie",
            "categories": "Categories auto",
            "monthly_total": "Total mensuel auto",
        },
        "auto_recurring_excluded": "Categories recurrentes exclues des moyennes auto : {categories}",
        "tx_table_headers": [
            "Date",
            "Type",
            "Montant",
            "Libelle",
            "Categorie",
            "Notes",
            "% depasse (proj)",
        ],
        "monthly_table_headers": [
            "Mois",
            "Budget (plan)",
            "Budget (proj)",
            "Total depenses",
            "Ajustements",
            "Delta $",
            "Delta %",
        ],
        "recurring_table_headers": [
            "Libelle",
            "Type",
            "Montant",
            "Categorie",
            "Frequence",
            "Debut",
            "Fin",
            "Statut",
            "Derniere",
        ],
    },
}
VALUE_TEXT = {
    "type": {
        "expense": {"EN": "Expense", "FR": "Depense"},
        "income": {"EN": "Income", "FR": "Revenu"},
    },
    "language_choice": {
        "EN": {"EN": "English", "FR": "Anglais"},
        "FR": {"EN": "French", "FR": "Francais"},
    },
    "frequency": {
        "monthly": {"EN": "Monthly", "FR": "Mensuel"},
        "weekly": {"EN": "Weekly", "FR": "Hebdomadaire"},
        "daily": {"EN": "Daily", "FR": "Quotidien"},
    },
    "status": {
        "automatic": {"EN": "Automatic", "FR": "Automatique"},
        "manual": {"EN": "Manual", "FR": "Manuel"},
        "paused": {"EN": "Paused", "FR": "En pause"},
    },
}


def translated_value(group: str, value: str, language: str = "EN") -> str:
    raw = str(value or "").strip()
    key = raw.lower()
    label_map = VALUE_TEXT.get(group, {}).get(key)
    if not label_map:
        label_map = VALUE_TEXT.get(group, {}).get(raw)
    if not label_map:
        return str(value)
    lang = (language or "EN").upper()
    return label_map.get(lang, label_map.get("EN", str(value)))


def combo_value(combo: QtWidgets.QComboBox) -> str:
    data = combo.currentData()
    if data is None:
        return combo.currentText().strip()
    return str(data).strip()


def set_combo_value(combo: QtWidgets.QComboBox, value: str) -> None:
    text = str(value or "").strip()
    if not text:
        if combo.count():
            combo.setCurrentIndex(0)
        return
    index = combo.findData(text)
    if index < 0:
        index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)
        return
    combo.addItem(text, text)
    combo.setCurrentIndex(combo.count() - 1)


def populate_value_combo(
    combo: QtWidgets.QComboBox,
    group: str,
    language: str = "EN",
    current_value: Optional[str] = None,
) -> None:
    current = current_value if current_value is not None else combo_value(combo)
    combo.blockSignals(True)
    combo.clear()
    for value in VALUE_TEXT.get(group, {}):
        combo.addItem(translated_value(group, value, language), value)
    set_combo_value(combo, current)
    combo.blockSignals(False)


def populate_category_combo(
    combo: QtWidgets.QComboBox,
    categories: List[str],
    language: str = "EN",
    current_value: Optional[str] = None,
) -> None:
    current = current_value if current_value is not None else combo_value(combo)
    combo.blockSignals(True)
    combo.clear()
    for category in categories:
        combo.addItem(translated_category(category, language), category)
    if current and combo.findData(current) < 0:
        combo.addItem(translated_category(current, language), current)
    set_combo_value(combo, current)
    combo.blockSignals(False)


THEMES = {
    "Dune": {
        "text": "#1b2a41",
        "bg": "#f4f2ef",
        "page_bg": "#f4f2ef",
        "dialog_bg": "#f4f2ef",
        "tab_bg": "#e3e8ee",
        "tab_text": "#1b2a41",
        "tab_hover": "#d6dde5",
        "tab_selected_bg": "#1b2a41",
        "tab_selected_text": "#fdfbf7",
        "hero_start": "#1b2a41",
        "hero_end": "#2a9d8f",
        "card_bg": "#ffffff",
        "card_border": "#e3e6ea",
        "hero_title": "#fdfbf7",
        "hero_subtitle": "#edf2f4",
        "section_title": "#1b2a41",
        "key_text": "#6b7280",
        "value_text": "#1b2a41",
        "accent_text": "#2a9d8f",
        "status_text": "#2a9d8f",
        "input_bg": "#f9fafb",
        "input_border": "#d7dce1",
        "input_focus": "#2a9d8f",
        "dropdown_bg": "#ffffff",
        "dropdown_text": "#1b2a41",
        "selection_bg": "#2a9d8f",
        "selection_text": "#ffffff",
        "checkbox_border": "#9aa5b1",
        "checkbox_checked_bg": "#2a9d8f",
        "list_bg": "#ffffff",
        "list_border": "#d7dce1",
        "list_selected_bg": "#dce8f0",
        "calendar_header_bg": "#edf2f4",
        "calendar_nav_bg": "#1b2a41",
        "button_bg": "#e3e8ee",
        "button_hover": "#d6dde5",
        "button_pressed": "#e8edf2",
        "primary_bg": "#2a9d8f",
        "primary_hover": "#238b7f",
        "primary_pressed": "#35a899",
        "warning_bg": "#e76f51",
        "warning_hover": "#d65f43",
        "warning_pressed": "#ea7c62",
        "group_bg": "#ffffff",
        "group_border": "#e3e6ea",
        "group_title": "#1b2a41",
        "table_bg": "#ffffff",
        "table_border": "#e3e6ea",
        "table_grid": "#eef2f5",
        "table_alt_bg": "#f7f9fc",
        "table_header_bg": "#1b2a41",
        "table_header_text": "#ffffff",
        "table_selected_bg": "#dce8f0",
        "table_selected_text": "#1b2a41",
    },
    "Mint": {
        "text": "#12333b",
        "bg": "#eef5f2",
        "page_bg": "#eef5f2",
        "dialog_bg": "#eef5f2",
        "tab_bg": "#dfeae6",
        "tab_text": "#12333b",
        "tab_hover": "#d3e2dd",
        "tab_selected_bg": "#12333b",
        "tab_selected_text": "#f6fffb",
        "hero_start": "#12333b",
        "hero_end": "#1b9aaa",
        "card_bg": "#ffffff",
        "card_border": "#d7e3df",
        "hero_title": "#f6fffb",
        "hero_subtitle": "#e2f5f1",
        "section_title": "#12333b",
        "key_text": "#6a7a80",
        "value_text": "#12333b",
        "accent_text": "#1b9aaa",
        "status_text": "#1b9aaa",
        "input_bg": "#f7fbfa",
        "input_border": "#c9d8d4",
        "input_focus": "#1b9aaa",
        "dropdown_bg": "#ffffff",
        "dropdown_text": "#12333b",
        "selection_bg": "#1b9aaa",
        "selection_text": "#ffffff",
        "checkbox_border": "#91a6a4",
        "checkbox_checked_bg": "#1b9aaa",
        "list_bg": "#ffffff",
        "list_border": "#c9d8d4",
        "list_selected_bg": "#d7ece8",
        "calendar_header_bg": "#e4f0ed",
        "calendar_nav_bg": "#12333b",
        "button_bg": "#dfeae6",
        "button_hover": "#d3e2dd",
        "button_pressed": "#e7f0ed",
        "primary_bg": "#1b9aaa",
        "primary_hover": "#178c9a",
        "primary_pressed": "#24a9b9",
        "warning_bg": "#e76f51",
        "warning_hover": "#d65f43",
        "warning_pressed": "#ea7c62",
        "group_bg": "#ffffff",
        "group_border": "#d7e3df",
        "group_title": "#12333b",
        "table_bg": "#ffffff",
        "table_border": "#d7e3df",
        "table_grid": "#edf4f2",
        "table_alt_bg": "#f6fbf9",
        "table_header_bg": "#12333b",
        "table_header_text": "#ffffff",
        "table_selected_bg": "#d7ece8",
        "table_selected_text": "#12333b",
    },
    "Slate": {
        "text": "#1f2937",
        "bg": "#f1f3f7",
        "page_bg": "#f1f3f7",
        "dialog_bg": "#f1f3f7",
        "tab_bg": "#e1e6ee",
        "tab_text": "#1f2937",
        "tab_hover": "#d6dde8",
        "tab_selected_bg": "#111827",
        "tab_selected_text": "#f8fafc",
        "hero_start": "#111827",
        "hero_end": "#3b82f6",
        "card_bg": "#ffffff",
        "card_border": "#dde2ea",
        "hero_title": "#f8fafc",
        "hero_subtitle": "#e2e8f0",
        "section_title": "#1f2937",
        "key_text": "#6b7280",
        "value_text": "#1f2937",
        "accent_text": "#3b82f6",
        "status_text": "#3b82f6",
        "input_bg": "#f8fafc",
        "input_border": "#d1d5db",
        "input_focus": "#3b82f6",
        "dropdown_bg": "#ffffff",
        "dropdown_text": "#1f2937",
        "selection_bg": "#3b82f6",
        "selection_text": "#ffffff",
        "checkbox_border": "#9ca3af",
        "checkbox_checked_bg": "#3b82f6",
        "list_bg": "#ffffff",
        "list_border": "#d1d5db",
        "list_selected_bg": "#e5effc",
        "calendar_header_bg": "#e5e7eb",
        "calendar_nav_bg": "#111827",
        "button_bg": "#e1e6ee",
        "button_hover": "#d6dde8",
        "button_pressed": "#e9edf4",
        "primary_bg": "#3b82f6",
        "primary_hover": "#2f6fe0",
        "primary_pressed": "#4d8cf8",
        "warning_bg": "#f97316",
        "warning_hover": "#ea6a10",
        "warning_pressed": "#ff7f2a",
        "group_bg": "#ffffff",
        "group_border": "#dde2ea",
        "group_title": "#1f2937",
        "table_bg": "#ffffff",
        "table_border": "#dde2ea",
        "table_grid": "#edf1f6",
        "table_alt_bg": "#f6f8fb",
        "table_header_bg": "#111827",
        "table_header_text": "#ffffff",
        "table_selected_bg": "#e5effc",
        "table_selected_text": "#1f2937",
    },
    "Snow": {
        "text": "#111827",
        "bg": "#ffffff",
        "page_bg": "#ffffff",
        "dialog_bg": "#ffffff",
        "tab_bg": "#f1f5f9",
        "tab_text": "#111827",
        "tab_hover": "#e2e8f0",
        "tab_selected_bg": "#111827",
        "tab_selected_text": "#ffffff",
        "hero_start": "#111827",
        "hero_end": "#0ea5e9",
        "card_bg": "#ffffff",
        "card_border": "#e5e7eb",
        "hero_title": "#ffffff",
        "hero_subtitle": "#e2e8f0",
        "section_title": "#111827",
        "key_text": "#6b7280",
        "value_text": "#111827",
        "accent_text": "#0ea5e9",
        "status_text": "#0ea5e9",
        "input_bg": "#ffffff",
        "input_border": "#d1d5db",
        "input_focus": "#0ea5e9",
        "dropdown_bg": "#ffffff",
        "dropdown_text": "#111827",
        "selection_bg": "#0ea5e9",
        "selection_text": "#ffffff",
        "checkbox_border": "#9ca3af",
        "checkbox_checked_bg": "#0ea5e9",
        "list_bg": "#ffffff",
        "list_border": "#d1d5db",
        "list_selected_bg": "#e0f2fe",
        "calendar_header_bg": "#f1f5f9",
        "calendar_nav_bg": "#111827",
        "button_bg": "#f1f5f9",
        "button_hover": "#e2e8f0",
        "button_pressed": "#e5e7eb",
        "primary_bg": "#0ea5e9",
        "primary_hover": "#0284c7",
        "primary_pressed": "#38bdf8",
        "warning_bg": "#f97316",
        "warning_hover": "#ea6a10",
        "warning_pressed": "#ff7f2a",
        "group_bg": "#ffffff",
        "group_border": "#e5e7eb",
        "group_title": "#111827",
        "table_bg": "#ffffff",
        "table_border": "#e5e7eb",
        "table_grid": "#eef2f7",
        "table_alt_bg": "#f9fafb",
        "table_header_bg": "#111827",
        "table_header_text": "#ffffff",
        "table_selected_bg": "#e0f2fe",
        "table_selected_text": "#111827",
    },
    "Night": {
        "text": "#e2e8f0",
        "bg": "#0b1220",
        "page_bg": "#0f172a",
        "dialog_bg": "#0f172a",
        "tab_bg": "#1e293b",
        "tab_text": "#e2e8f0",
        "tab_hover": "#334155",
        "tab_selected_bg": "#38bdf8",
        "tab_selected_text": "#0b1220",
        "hero_start": "#111827",
        "hero_end": "#2563eb",
        "card_bg": "#0f172a",
        "card_border": "#1f2937",
        "hero_title": "#e2e8f0",
        "hero_subtitle": "#cbd5f5",
        "section_title": "#e2e8f0",
        "key_text": "#94a3b8",
        "value_text": "#e2e8f0",
        "accent_text": "#38bdf8",
        "status_text": "#38bdf8",
        "input_bg": "#0f172a",
        "input_border": "#1f2937",
        "input_focus": "#38bdf8",
        "dropdown_bg": "#0f172a",
        "dropdown_text": "#e2e8f0",
        "selection_bg": "#38bdf8",
        "selection_text": "#0b1220",
        "checkbox_border": "#475569",
        "checkbox_checked_bg": "#38bdf8",
        "list_bg": "#0f172a",
        "list_border": "#1f2937",
        "list_selected_bg": "#1f2937",
        "calendar_header_bg": "#1e293b",
        "calendar_nav_bg": "#111827",
        "button_bg": "#1e293b",
        "button_hover": "#334155",
        "button_pressed": "#0b1220",
        "primary_bg": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "primary_pressed": "#7dd3fc",
        "warning_bg": "#f97316",
        "warning_hover": "#ea6a10",
        "warning_pressed": "#ff7f2a",
        "group_bg": "#0f172a",
        "group_border": "#1f2937",
        "group_title": "#e2e8f0",
        "table_bg": "#0f172a",
        "table_border": "#1f2937",
        "table_grid": "#1f2937",
        "table_alt_bg": "#111827",
        "table_header_bg": "#111827",
        "table_header_text": "#e2e8f0",
        "table_selected_bg": "#1f2937",
        "table_selected_text": "#e2e8f0",
    },
    "Mono": {
        "text": "#0f172a",
        "bg": "#f8fafc",
        "page_bg": "#f8fafc",
        "dialog_bg": "#f8fafc",
        "tab_bg": "#e2e8f0",
        "tab_text": "#0f172a",
        "tab_hover": "#cbd5f5",
        "tab_selected_bg": "#0f172a",
        "tab_selected_text": "#f8fafc",
        "hero_start": "#0f172a",
        "hero_end": "#64748b",
        "card_bg": "#ffffff",
        "card_border": "#e2e8f0",
        "hero_title": "#f8fafc",
        "hero_subtitle": "#e2e8f0",
        "section_title": "#0f172a",
        "key_text": "#64748b",
        "value_text": "#0f172a",
        "accent_text": "#64748b",
        "status_text": "#64748b",
        "input_bg": "#ffffff",
        "input_border": "#cbd5f5",
        "input_focus": "#475569",
        "dropdown_bg": "#ffffff",
        "dropdown_text": "#0f172a",
        "selection_bg": "#0f172a",
        "selection_text": "#f8fafc",
        "checkbox_border": "#64748b",
        "checkbox_checked_bg": "#0f172a",
        "list_bg": "#ffffff",
        "list_border": "#cbd5f5",
        "list_selected_bg": "#e2e8f0",
        "calendar_header_bg": "#e2e8f0",
        "calendar_nav_bg": "#0f172a",
        "button_bg": "#e2e8f0",
        "button_hover": "#cbd5f5",
        "button_pressed": "#d1d5db",
        "primary_bg": "#0f172a",
        "primary_hover": "#1f2937",
        "primary_pressed": "#334155",
        "warning_bg": "#f97316",
        "warning_hover": "#ea6a10",
        "warning_pressed": "#ff7f2a",
        "group_bg": "#ffffff",
        "group_border": "#e2e8f0",
        "group_title": "#0f172a",
        "table_bg": "#ffffff",
        "table_border": "#e2e8f0",
        "table_grid": "#eef2f7",
        "table_alt_bg": "#f8fafc",
        "table_header_bg": "#0f172a",
        "table_header_text": "#f8fafc",
        "table_selected_bg": "#e2e8f0",
        "table_selected_text": "#0f172a",
    },
}

STYLE_TEMPLATE = Template(
    """
* {
    font-family: $font_family;
    font-size: 10pt;
    color: $text;
}
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $window_start, stop:0.65 $bg, stop:1 $window_end);
}
QWidget[page="true"] {
    background: transparent;
}
QDialog, QMessageBox {
    background-color: $dialog_bg;
}
QMessageBox QLabel {
    color: $text;
}
QToolTip {
    color: $text;
    background: $card_top;
    border: 1px solid $card_outline;
    border-radius: 8px;
    padding: 6px 8px;
}
QTabWidget::pane {
    border: none;
    background: transparent;
    margin-top: 4px;
}
QTabBar::tab {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $tab_bg, stop:1 $tab_bg_alt);
    color: $tab_text;
    padding: 10px 18px;
    margin: 8px 8px 0 0;
    border-radius: 14px;
    border: 1px solid $tab_border;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $tab_selected_bg, stop:1 $tab_selected_bg_alt);
    color: $tab_selected_text;
    border: 1px solid $tab_selected_bg;
}
QTabBar::tab:hover {
    background: $tab_hover;
}
QFrame[hero="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $hero_start, stop:1 $hero_end);
    border: 1px solid $hero_outline;
    border-radius: 24px;
}
QFrame[card="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $card_top, stop:1 $card_bottom);
    border: 1px solid $card_outline;
    border-radius: 20px;
}
QFrame[card="true"][feature="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $feature_top, stop:1 $feature_bottom);
    border: 1px solid $feature_outline;
}
QFrame[card="true"][highlight="true"] {
    border: 2px solid $accent_text;
}
QLabel#HeroTitle {
    color: $hero_title;
    font-size: 22pt;
    font-weight: 800;
}
QLabel#HeroSubtitle {
    color: $hero_subtitle;
    font-size: 10.5pt;
}
QLabel[sectionTitle="true"] {
    font-size: 12.6pt;
    font-weight: 800;
    color: $section_title;
}
QLabel[key="true"] {
    color: $key_text;
    font-size: 8.5pt;
    font-weight: 600;
}
QLabel[value="true"] {
    color: $value_text;
    font-size: 14.2pt;
    font-weight: 800;
}
QLabel[valueAccent="true"] {
    color: $accent_text;
    font-size: 15pt;
}
QLabel[status="true"] {
    color: $status_text;
    font-weight: 600;
}
QLineEdit, QComboBox, QDateTimeEdit, QSpinBox, QDoubleSpinBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $input_bg, stop:1 $input_bg_alt);
    border: 1px solid $input_border;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: $selection_bg;
    selection-color: $selection_text;
    min-height: 18px;
}
QLineEdit:hover, QComboBox:hover, QDateTimeEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border: 1px solid $input_hover;
}
QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid $input_focus;
}
QComboBox QAbstractItemView {
    background: $dropdown_bg;
    color: $dropdown_text;
    selection-background-color: $selection_bg;
    selection-color: $selection_text;
    border: 1px solid $card_outline;
    border-radius: 10px;
    padding: 4px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
}
QCheckBox, QRadioButton {
    color: $text;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
QCheckBox::indicator:unchecked {
    background: $card_bg;
    border: 1px solid $checkbox_border;
    border-radius: 5px;
}
QCheckBox::indicator:checked {
    background: $checkbox_checked_bg;
    border: 1px solid $checkbox_checked_bg;
    border-radius: 5px;
}
QListWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $list_bg, stop:1 $card_bottom);
    color: $text;
    border: 1px solid $list_outline;
    border-radius: 12px;
    padding: 6px;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 8px;
}
QListWidget::item:selected {
    background: $list_selected_bg;
    color: $text;
}
QCalendarWidget QAbstractItemView {
    background: $dropdown_bg;
    color: $dropdown_text;
    selection-background-color: $selection_bg;
    selection-color: $selection_text;
}
QCalendarWidget QAbstractItemView:disabled {
    color: $checkbox_border;
}
QCalendarWidget QHeaderView::section {
    background: $calendar_header_bg;
    color: $text;
    padding: 4px;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background: $calendar_nav_bg;
    color: $selection_text;
}
QCalendarWidget QToolButton {
    color: $selection_text;
    background: transparent;
}
QCalendarWidget QSpinBox {
    background: $dropdown_bg;
    color: $dropdown_text;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $button_bg, stop:1 $button_bg_alt);
    border: 1px solid $button_outline;
    border-radius: 12px;
    padding: 9px 16px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background: $button_hover;
}
QPushButton:pressed {
    background: $button_pressed;
}
QPushButton[primary="true"] {
    background: $primary_bg;
    color: $selection_text;
}
QPushButton[primary="true"]:hover {
    background: $primary_hover;
}
QPushButton[primary="true"]:pressed {
    background: $primary_pressed;
}
QPushButton[warning="true"] {
    background: $warning_bg;
    color: $selection_text;
}
QPushButton[warning="true"]:hover {
    background: $warning_hover;
}
QPushButton[warning="true"]:pressed {
    background: $warning_pressed;
}
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $group_top, stop:1 $group_bottom);
    border: 1px solid $group_border;
    border-radius: 20px;
    margin-top: 24px;
    padding: 16px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 10px;
    color: $group_title;
}
QTableWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $table_bg, stop:1 $table_alt_bg);
    border: 1px solid $table_border;
    border-radius: 14px;
    gridline-color: $table_grid;
    alternate-background-color: $table_alt_bg;
}
QHeaderView::section {
    background: $table_header_bg;
    color: $table_header_text;
    padding: 10px 12px;
    border: none;
    font-weight: 700;
}
QTableCornerButton::section {
    background: $table_header_bg;
    border: none;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:hover {
    background: $table_row_hover;
}
QTableWidget::item:selected {
    background: $table_selected_bg;
    color: $table_selected_text;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 4px 2px 4px 2px;
}
QScrollBar::handle:vertical {
    background: $scrollbar_handle;
    min-height: 28px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: $scrollbar_handle_hover;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px 4px 2px 4px;
}
QScrollBar::handle:horizontal {
    background: $scrollbar_handle;
    min-width: 28px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal:hover {
    background: $scrollbar_handle_hover;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""
)

def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _adjust_color(hex_value: str, delta: int) -> str:
    try:
        value = hex_value.lstrip("#")
        if len(value) != 6:
            return hex_value
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
    except ValueError:
        return hex_value
    r = _clamp(r + delta)
    g = _clamp(g + delta)
    b = _clamp(b + delta)
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(hex_value: str) -> Optional[tuple[int, int, int]]:
    try:
        value = hex_value.lstrip("#")
        if len(value) != 6:
            return None
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except ValueError:
        return None


def _is_dark_color(hex_value: str) -> bool:
    rgb = _hex_to_rgb(hex_value)
    if rgb is None:
        return False
    r, g, b = rgb
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return luminance < 0.52


def _mode_adjust(hex_value: str, light_delta: int, dark_delta: int) -> str:
    return _adjust_color(hex_value, dark_delta if _is_dark_color(hex_value) else light_delta)


def _rgba_color(hex_value: str, alpha: int) -> str:
    rgb = _hex_to_rgb(hex_value)
    if rgb is None:
        return hex_value
    r, g, b = rgb
    return f"rgba({r}, {g}, {b}, {max(0, min(255, alpha))})"


def build_stylesheet(
    theme_name: str,
    font_family: Optional[str] = None,
    accent_color: Optional[str] = None,
) -> str:
    theme = THEMES.get(theme_name, THEMES["Dune"])
    theme_values = dict(theme)
    if font_family:
        theme_values["font_family"] = font_family
    else:
        theme_values["font_family"] = "Aptos, Manrope, Montserrat, Segoe UI"
    if accent_color:
        accent = accent_color
        theme_values["accent_text"] = accent
        theme_values["status_text"] = accent
        theme_values["input_focus"] = accent
        theme_values["selection_bg"] = accent
        theme_values["checkbox_checked_bg"] = accent
        theme_values["primary_bg"] = accent
        theme_values["primary_hover"] = _adjust_color(accent, -16)
        theme_values["primary_pressed"] = _adjust_color(accent, 18)
    theme_values["window_start"] = _mode_adjust(theme_values["hero_start"], 84, 16)
    theme_values["window_end"] = _mode_adjust(theme_values["page_bg"], -6, 12)
    theme_values["tab_bg_alt"] = _mode_adjust(theme_values["tab_bg"], 8, -8)
    theme_values["tab_border"] = _rgba_color(theme_values["card_border"], 205)
    theme_values["tab_selected_bg_alt"] = _mode_adjust(
        theme_values["tab_selected_bg"], 18, -12
    )
    theme_values["hero_outline"] = _rgba_color(theme_values["hero_end"], 170)
    theme_values["card_top"] = _mode_adjust(theme_values["card_bg"], 8, 12)
    theme_values["card_bottom"] = _mode_adjust(theme_values["card_bg"], -6, -6)
    theme_values["card_outline"] = _rgba_color(theme_values["card_border"], 225)
    theme_values["feature_outline"] = _rgba_color(theme_values["accent_text"], 150)
    theme_values["feature_top"] = _rgba_color(
        theme_values["accent_text"], 26 if not _is_dark_color(theme_values["bg"]) else 40
    )
    theme_values["feature_bottom"] = _rgba_color(
        theme_values["hero_end"], 10 if not _is_dark_color(theme_values["bg"]) else 24
    )
    theme_values["input_bg_alt"] = _mode_adjust(theme_values["input_bg"], 4, -8)
    theme_values["input_hover"] = _mode_adjust(theme_values["input_focus"], -18, 18)
    theme_values["button_bg_alt"] = _mode_adjust(theme_values["button_bg"], 8, -10)
    theme_values["button_outline"] = _rgba_color(theme_values["card_border"], 190)
    theme_values["group_top"] = _mode_adjust(theme_values["group_bg"], 6, 10)
    theme_values["group_bottom"] = _mode_adjust(theme_values["group_bg"], -6, -8)
    theme_values["list_outline"] = _rgba_color(theme_values["list_border"], 200)
    theme_values["table_row_hover"] = _mode_adjust(
        theme_values["table_alt_bg"], -10, 12
    )
    theme_values["scrollbar_handle"] = _rgba_color(
        theme_values["accent_text"], 150 if not _is_dark_color(theme_values["bg"]) else 190
    )
    theme_values["scrollbar_handle_hover"] = _rgba_color(
        theme_values["accent_text"], 215
    )
    return STYLE_TEMPLATE.substitute(**theme_values)


def apply_theme(
    app: QtWidgets.QApplication,
    theme_name: str = "Dune",
    font_family: Optional[str] = None,
    accent_color: Optional[str] = None,
) -> None:
    app.setStyle("Fusion")
    font = QtGui.QFont()
    font.setPointSize(10)
    if font_family:
        font.setFamily(font_family)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet(theme_name, font_family, accent_color))


def parse_datetime(value: str) -> Optional[datetime]:
    return calculations._try_parse_datetime(value)


@dataclass
class UndoAction:
    label: str
    undo: callable


class TransactionDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent,
        transaction: Transaction,
        categories: List[str],
        text_lookup=None,
    ) -> None:
        super().__init__(parent)
        self._text = text_lookup or (lambda key: UI_TEXT["EN"].get(key, key))
        self._language = getattr(parent, "_current_language", lambda: "EN")()
        self.setWindowTitle(self._text("edit_transaction_title"))
        self.transaction = transaction

        self.amount_input = QtWidgets.QDoubleSpinBox()
        self.amount_input.setRange(0, 1_000_000_000)
        self.amount_input.setDecimals(2)
        self.amount_input.setValue(transaction.amount)

        self.type_input = QtWidgets.QComboBox()
        populate_value_combo(
            self.type_input,
            "type",
            self._language,
            transaction.type,
        )

        self.label_input = QtWidgets.QLineEdit(transaction.label)
        self.category_input = QtWidgets.QComboBox()
        self.category_input.setEditable(True)
        populate_category_combo(
            self.category_input,
            categories or CATEGORY_DEFAULTS,
            self._language,
            transaction.category,
        )

        self.notes_input = QtWidgets.QLineEdit(transaction.notes)

        self.date_input = QtWidgets.QDateTimeEdit()
        self.date_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.date_input.setCalendarPopup(True)
        dt_value = QtCore.QDateTime.fromString(
            transaction.datetime_local, "yyyy-MM-ddTHH:mm:ss"
        )
        if not dt_value.isValid():
            dt_value = QtCore.QDateTime.currentDateTime()
        self.date_input.setDateTime(dt_value)

        form = QtWidgets.QFormLayout()
        form.addRow(self._text("field_amount"), self.amount_input)
        form.addRow(self._text("field_type"), self.type_input)
        form.addRow(self._text("field_label"), self.label_input)
        form.addRow(self._text("field_category"), self.category_input)
        form.addRow(self._text("field_notes"), self.notes_input)
        form.addRow(self._text("field_date"), self.date_input)
        self.exclude_from_averages = QtWidgets.QCheckBox(
            self._text("exclude_from_averages")
        )
        self.exclude_from_averages.setChecked(
            bool(getattr(transaction, "excluded_from_averages", False))
        )
        form.addRow(self.exclude_from_averages)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        save_button = buttons.button(QtWidgets.QDialogButtonBox.Save)
        if save_button is not None:
            save_button.setText(self._text("dialog_save"))
        cancel_button = buttons.button(QtWidgets.QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setText(self._text("dialog_cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self) -> Dict[str, Union[str, float]]:
        return {
            "amount": float(self.amount_input.value()),
            "type": combo_value(self.type_input),
            "label": self.label_input.text().strip(),
            "category": self.category_input.currentText().strip(),
            "notes": self.notes_input.text().strip(),
            "datetime_local": self.date_input.dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
            "excluded_from_averages": self.exclude_from_averages.isChecked()
            if hasattr(self, "exclude_from_averages")
            else False,
        }


class RecurringDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent,
        charge: RecurringCharge,
        categories: List[str],
        text_lookup=None,
    ) -> None:
        super().__init__(parent)
        self._text = text_lookup or (lambda key: UI_TEXT["EN"].get(key, key))
        self._language = getattr(parent, "_current_language", lambda: "EN")()
        self.setWindowTitle(self._text("edit_recurring_title"))
        self.charge = charge

        self.label_input = QtWidgets.QLineEdit(charge.label)

        self.amount_input = QtWidgets.QDoubleSpinBox()
        self.amount_input.setRange(0, 1_000_000_000)
        self.amount_input.setDecimals(2)
        self.amount_input.setValue(charge.amount)

        self.type_input = QtWidgets.QComboBox()
        populate_value_combo(self.type_input, "type", self._language, charge.type)

        self.category_input = QtWidgets.QComboBox()
        self.category_input.setEditable(True)
        populate_category_combo(
            self.category_input,
            categories or CATEGORY_DEFAULTS,
            self._language,
            charge.category,
        )

        self.notes_input = QtWidgets.QLineEdit(charge.notes)

        self.start_date_input = QtWidgets.QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        start_date = QtCore.QDate.fromString(charge.start_date, "yyyy-MM-dd")
        if not start_date.isValid():
            start_date = QtCore.QDate.currentDate()
        self.start_date_input.setDate(start_date)

        self.end_date_enabled = QtWidgets.QCheckBox(self._text("recurring_end"))
        self.end_date_input = QtWidgets.QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        if charge.end_date:
            end_date = QtCore.QDate.fromString(charge.end_date, "yyyy-MM-dd")
            if not end_date.isValid():
                end_date = QtCore.QDate.currentDate()
            self.end_date_input.setDate(end_date)
            self.end_date_enabled.setChecked(True)
            self.end_date_input.setEnabled(True)
        else:
            self.end_date_input.setDate(QtCore.QDate.currentDate())
            self.end_date_enabled.setChecked(False)
            self.end_date_input.setEnabled(False)
        self.end_date_enabled.toggled.connect(self.end_date_input.setEnabled)

        self.frequency_input = QtWidgets.QComboBox()
        populate_value_combo(
            self.frequency_input,
            "frequency",
            self._language,
            charge.frequency or "monthly",
        )

        self.status_input = QtWidgets.QComboBox()
        populate_value_combo(
            self.status_input,
            "status",
            self._language,
            charge.status,
        )

        form = QtWidgets.QFormLayout()
        form.addRow(self._text("recurring_label"), self.label_input)
        form.addRow(self._text("recurring_amount"), self.amount_input)
        form.addRow(self._text("recurring_type"), self.type_input)
        form.addRow(self._text("recurring_category"), self.category_input)
        form.addRow(self._text("recurring_notes"), self.notes_input)
        form.addRow(self._text("recurring_start"), self.start_date_input)
        form.addRow(self.end_date_enabled, self.end_date_input)
        form.addRow(self._text("recurring_frequency"), self.frequency_input)
        form.addRow(self._text("recurring_status"), self.status_input)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        save_button = buttons.button(QtWidgets.QDialogButtonBox.Save)
        if save_button is not None:
            save_button.setText(self._text("dialog_save"))
        cancel_button = buttons.button(QtWidgets.QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setText(self._text("dialog_cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self) -> Dict[str, Union[str, float, None]]:
        end_date = None
        if self.end_date_enabled.isChecked():
            end_date = self.end_date_input.date().toString("yyyy-MM-dd")
        return {
            "label": self.label_input.text().strip(),
            "amount": float(self.amount_input.value()),
            "type": combo_value(self.type_input),
            "category": self.category_input.currentText().strip(),
            "notes": self.notes_input.text().strip(),
            "start_date": self.start_date_input.date().toString("yyyy-MM-dd"),
            "end_date": end_date,
            "frequency": combo_value(self.frequency_input),
            "status": combo_value(self.status_input),
        }


class ClickableImageLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class ChartPreviewDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent,
        title: str,
        pixmap: QtGui.QPixmap,
        text_lookup=None,
    ) -> None:
        super().__init__(parent)
        self._text = text_lookup or (lambda key: UI_TEXT["EN"].get(key, key))
        self.setWindowTitle(f"{title} - {self._text('chart_preview_title')}")
        self.setMinimumSize(820, 620)
        self.resize(1100, 780)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title_label = QtWidgets.QLabel(title)
        title_label.setProperty("sectionTitle", True)
        title_label.setWordWrap(True)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(QtCore.Qt.AlignCenter)

        image_label = QtWidgets.QLabel()
        image_label.setAlignment(QtCore.Qt.AlignCenter)
        image_label.setPixmap(pixmap)
        image_label.setMinimumSize(pixmap.size())
        scroll.setWidget(image_label)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        close_button = buttons.button(QtWidgets.QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._text("dialog_close"))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.db = Database()
        self.transactions: List[Transaction] = []
        self.recurring_charges: List[RecurringCharge] = []
        self.settings: Optional[Settings] = None
        self.categories: List[str] = self.db.list_categories() or list(CATEGORY_DEFAULTS)
        self.summary: Dict[str, Union[float, str, None]] = {}
        self.monthly_stats: List[Dict[str, Union[float, str]]] = []
        self.loading = False
        self._intro_animation = None
        self.settings_dirty = False
        self._last_recurring_check = None
        self._recurring_timer = None
        self.undo_stack: List[UndoAction] = []
        self.undo_limit = 30
        self._undoing = False

        self.setWindowTitle(APP_TITLE)
        app_icon = load_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.resize(1200, 800)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setCursor(QtCore.Qt.PointingHandCursor)
        self.setCentralWidget(self.tabs)

        self._build_welcome_tab()
        self._build_add_entry_tab()
        self._build_transactions_tab()
        self._build_dashboard_tab()
        self._build_recurring_tab()
        self._build_report_tab()

        self.undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence.Undo, self)
        self.undo_shortcut.activated.connect(self.handle_undo)

        self._check_missed_recurring()
        self.reload_all()
        self._start_recurring_timer()
        self._animate_in()

    def _apply_theme(self, theme_name: Optional[str] = None) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        theme_value = theme_name or getattr(self.settings, "theme", "Dune")
        font_family = getattr(self.settings, "font_family", "") if self.settings else ""
        accent_color = getattr(self.settings, "accent_color", "") if self.settings else ""
        apply_theme(app, theme_value, font_family or None, accent_color or None)

    def _build_welcome_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_welcome = tab
        tab.setProperty("page", True)
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        hero = QtWidgets.QFrame()
        hero.setProperty("hero", True)
        hero_layout = QtWidgets.QVBoxLayout(hero)
        hero_layout.setSpacing(10)
        self.welcome_brand = QtWidgets.QLabel()
        self.welcome_brand.setObjectName("BrandMark")
        self.welcome_brand.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.welcome_brand.setFixedSize(88, 88)
        brand_pixmap = load_app_brand_pixmap(88)
        if brand_pixmap.isNull():
            self.welcome_brand.hide()
        else:
            self.welcome_brand.setPixmap(brand_pixmap)
        hero_layout.addWidget(self.welcome_brand, 0, QtCore.Qt.AlignLeft)
        self.welcome_hero_title = QtWidgets.QLabel("Welcome")
        self.welcome_hero_title.setObjectName("HeroTitle")
        self.welcome_hero_subtitle = QtWidgets.QLabel(
            "Customize your view and jump to any section."
        )
        self.welcome_hero_subtitle.setObjectName("HeroSubtitle")
        hero_layout.addWidget(self.welcome_hero_title)
        hero_layout.addWidget(self.welcome_hero_subtitle)

        content_layout = QtWidgets.QHBoxLayout()

        customize_card = QtWidgets.QFrame()
        customize_card.setProperty("card", True)
        customize_card.setProperty("feature", "true")
        customize_layout = QtWidgets.QVBoxLayout(customize_card)
        customize_layout.setContentsMargins(18, 18, 18, 18)
        self.welcome_customize_title = QtWidgets.QLabel("Customize")
        self.welcome_customize_title.setProperty("sectionTitle", True)
        self.welcome_customize_hint = QtWidgets.QLabel("Choose a theme to match your mood.")
        self.welcome_customize_hint.setProperty("key", True)
        self.welcome_theme_label = QtWidgets.QLabel("Theme")
        self.welcome_theme_combo = QtWidgets.QComboBox()
        self.welcome_theme_combo.addItems(list(THEMES.keys()))
        self.welcome_theme_combo.currentTextChanged.connect(self.handle_theme_change)
        self.welcome_font_label = QtWidgets.QLabel("Font")
        self.welcome_font_combo = QtWidgets.QComboBox()
        self.welcome_font_combo.setEditable(False)
        font_db = QtGui.QFontDatabase()
        font_families = [family for family in font_db.families() if family]
        if not font_families:
            font_families = ["Segoe UI"]
        self.welcome_font_combo.addItem("System Default")
        self.welcome_font_combo.addItems(font_families)
        self.welcome_font_combo.currentTextChanged.connect(self.handle_font_change)
        self.welcome_accent_label = QtWidgets.QLabel("Accent color")
        self.welcome_accent_button = QtWidgets.QPushButton("Pick color")
        self.welcome_accent_button.clicked.connect(self.handle_pick_accent_color)
        self.welcome_accent_reset = QtWidgets.QPushButton("Reset color")
        self.welcome_accent_reset.clicked.connect(self.handle_reset_accent_color)
        accent_row = QtWidgets.QHBoxLayout()
        accent_row.addWidget(self.welcome_accent_button)
        accent_row.addWidget(self.welcome_accent_reset)
        accent_row.addStretch()
        accent_row_widget = QtWidgets.QWidget()
        accent_row_widget.setLayout(accent_row)
        self.theme_status_label = QtWidgets.QLabel("")
        self.theme_status_label.setProperty("status", True)

        customize_layout.addWidget(self.welcome_customize_title)
        customize_layout.addWidget(self.welcome_customize_hint)
        customize_layout.addSpacing(6)
        customize_layout.addWidget(self.welcome_theme_label)
        customize_layout.addWidget(self.welcome_theme_combo)
        customize_layout.addSpacing(6)
        customize_layout.addWidget(self.welcome_font_label)
        customize_layout.addWidget(self.welcome_font_combo)
        customize_layout.addSpacing(6)
        customize_layout.addWidget(self.welcome_accent_label)
        customize_layout.addWidget(accent_row_widget)
        customize_layout.addWidget(self.theme_status_label)
        customize_layout.addStretch()

        nav_card = QtWidgets.QFrame()
        nav_card.setProperty("card", True)
        nav_layout = QtWidgets.QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(18, 18, 18, 18)
        self.welcome_nav_title = QtWidgets.QLabel("Navigate")
        self.welcome_nav_title.setProperty("sectionTitle", True)
        nav_layout.addWidget(self.welcome_nav_title)

        nav_grid = QtWidgets.QGridLayout()
        nav_grid.setSpacing(10)
        self.nav_buttons: Dict[str, QtWidgets.QPushButton] = {}
        nav_items = [
            ("tab_add_entry", "Add Entry"),
            ("tab_transactions", "Transactions"),
            ("tab_dashboard", "Dashboard & Settings"),
            ("tab_recurring", "Recurring"),
            ("tab_report", "Reports"),
        ]
        for idx, (target, label) in enumerate(nav_items):
            button = QtWidgets.QPushButton(label)
            button.setProperty("primary", True)
            button.setMinimumHeight(44)
            button.clicked.connect(lambda _checked=False, key=target: self._navigate_to(key))
            nav_grid.addWidget(button, idx // 2, idx % 2)
            self.nav_buttons[target] = button
        nav_layout.addLayout(nav_grid)
        nav_layout.addStretch()

        content_layout.addWidget(customize_card, 1)
        content_layout.addWidget(nav_card, 2)

        layout.addWidget(hero)
        layout.addLayout(content_layout)
        layout.addStretch()

        self.tabs.addTab(tab, "Welcome")

    def _build_add_entry_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_add_entry = tab
        tab.setProperty("page", True)
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        hero = QtWidgets.QFrame()
        hero.setProperty("hero", True)
        hero_layout = QtWidgets.QVBoxLayout(hero)
        self.add_hero_title = QtWidgets.QLabel("Add Entry")
        self.add_hero_title.setObjectName("HeroTitle")
        self.add_hero_subtitle = QtWidgets.QLabel(
            "Quick capture or detailed entry, saved instantly."
        )
        self.add_hero_subtitle.setObjectName("HeroSubtitle")
        hero_layout.addWidget(self.add_hero_title)
        hero_layout.addWidget(self.add_hero_subtitle)
        hero_layout.addStretch()

        self.quick_entry_input = QtWidgets.QLineEdit()
        self.quick_entry_input.setPlaceholderText("Quick entry: 42 Walmart")

        form = QtWidgets.QFormLayout()
        self.add_form_labels: Dict[str, QtWidgets.QLabel] = {}
        self.amount_input = QtWidgets.QDoubleSpinBox()
        self.amount_input.setRange(0, 1_000_000_000)
        self.amount_input.setDecimals(2)

        self.label_input = QtWidgets.QLineEdit()

        self.category_input = QtWidgets.QComboBox()
        self.category_input.setEditable(True)
        populate_category_combo(
            self.category_input,
            self.categories,
            self._current_language(),
        )

        self.type_input = QtWidgets.QComboBox()
        populate_value_combo(self.type_input, "type", self._current_language(), "expense")

        self.notes_input = QtWidgets.QLineEdit()

        self.date_input = QtWidgets.QDateTimeEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.date_input.dateTimeChanged.connect(self.on_date_changed)
        self.date_manual = False
        self._reset_date_to_now()

        self.exclude_from_averages_checkbox = QtWidgets.QCheckBox(
            self._text("exclude_from_averages")
        )

        amount_label = QtWidgets.QLabel("Amount")
        label_label = QtWidgets.QLabel("Label")
        category_label = QtWidgets.QLabel("Category")
        type_label = QtWidgets.QLabel("Type")
        notes_label = QtWidgets.QLabel("Notes")
        date_label = QtWidgets.QLabel("Date")
        self.add_form_labels.update(
            {
                "amount": amount_label,
                "label": label_label,
                "category": category_label,
                "type": type_label,
                "notes": notes_label,
                "date": date_label,
            }
        )
        form.addRow(amount_label, self.amount_input)
        form.addRow(label_label, self.label_input)
        form.addRow(category_label, self.category_input)
        form.addRow(type_label, self.type_input)
        form.addRow(notes_label, self.notes_input)
        form.addRow(date_label, self.date_input)
        form.addRow(self.exclude_from_averages_checkbox)

        self.save_button = QtWidgets.QPushButton("Save Entry")
        self.save_button.setProperty("primary", True)
        self.save_button.clicked.connect(self.handle_add_entry)

        self.add_status_label = QtWidgets.QLabel("")
        self.add_status_label.setProperty("status", True)

        self.quick_entry_input.returnPressed.connect(self.handle_add_entry)
        self.label_input.returnPressed.connect(self.handle_add_entry)

        quick_card = QtWidgets.QFrame()
        quick_card.setProperty("card", True)
        quick_card.setProperty("feature", "true")
        quick_layout = QtWidgets.QVBoxLayout(quick_card)
        quick_layout.setContentsMargins(18, 18, 18, 18)
        self.quick_title = QtWidgets.QLabel("Quick Entry")
        self.quick_title.setProperty("sectionTitle", True)
        self.quick_hint = QtWidgets.QLabel("Type amount then label. Example: 42 Walmart")
        self.quick_hint.setProperty("key", True)
        self.quick_button = QtWidgets.QPushButton("Quick Save")
        self.quick_button.setProperty("primary", True)
        self.quick_button.clicked.connect(self.handle_add_entry)
        quick_layout.addWidget(self.quick_title)
        quick_layout.addWidget(self.quick_entry_input)
        quick_layout.addWidget(self.quick_hint)
        quick_layout.addWidget(self.quick_button)
        quick_layout.addStretch()

        form_card = QtWidgets.QFrame()
        form_card.setProperty("card", True)
        form_layout = QtWidgets.QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 18, 18, 18)
        self.details_title = QtWidgets.QLabel("Details")
        self.details_title.setProperty("sectionTitle", True)
        form_layout.addWidget(self.details_title)
        form_layout.addLayout(form)
        action_layout = QtWidgets.QHBoxLayout()
        action_layout.addWidget(self.save_button)
        action_layout.addWidget(self.add_status_label)
        action_layout.addStretch()
        form_layout.addLayout(action_layout)

        cards_layout = QtWidgets.QHBoxLayout()
        cards_layout.setSpacing(18)
        cards_layout.addWidget(quick_card, 1)
        cards_layout.addWidget(form_card, 2)

        layout.addWidget(hero)
        layout.addLayout(cards_layout)
        layout.addStretch()

        self.tabs.addTab(tab, "Add Entry")

    def _build_transactions_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_transactions = tab
        tab.setProperty("page", True)
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QtWidgets.QFrame()
        toolbar.setProperty("card", True)
        toolbar_layout = QtWidgets.QHBoxLayout(toolbar)
        self.tx_title_label = QtWidgets.QLabel("Transactions")
        self.tx_title_label.setProperty("sectionTitle", True)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search label, notes, category")
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self.refresh_transactions_table)

        self.month_filter = QtWidgets.QComboBox()
        self.month_filter.setMinimumWidth(140)
        self.month_filter.currentTextChanged.connect(self.refresh_transactions_table)

        self.edit_button = QtWidgets.QPushButton("Edit")
        self.delete_button = QtWidgets.QPushButton("Delete")
        self.delete_button.setProperty("warning", True)
        self.edit_button.clicked.connect(self.handle_edit_transaction)
        self.delete_button.clicked.connect(self.handle_delete_transaction)
        self.undo_button = QtWidgets.QPushButton("Undo")
        self.undo_button.setToolTip("Ctrl+Z")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.handle_undo)

        toolbar_layout.addWidget(self.tx_title_label)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(self.month_filter)
        toolbar_layout.addWidget(self.undo_button)
        toolbar_layout.addWidget(self.edit_button)
        toolbar_layout.addWidget(self.delete_button)

        self.transactions_table = QtWidgets.QTableWidget(0, 7)
        self.transactions_table.setHorizontalHeaderLabels(
            ["Date", "Type", "Amount", "Label", "Category", "Notes", "Over % (proj)"]
        )
        self.transactions_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.transactions_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.verticalHeader().setVisible(False)
        self.transactions_table.horizontalHeader().setStretchLastSection(True)

        self.tx_status_label = QtWidgets.QLabel("")
        self.tx_status_label.setProperty("status", True)

        layout.addWidget(toolbar)
        layout.addWidget(self.transactions_table)
        layout.addWidget(self.tx_status_label)

        self.tabs.addTab(tab, "Transactions")

    def _build_dashboard_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_dashboard = tab
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        tab.setProperty("page", True)
        container.setProperty("page", True)
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        hero = QtWidgets.QFrame()
        hero.setProperty("hero", True)
        hero_layout = QtWidgets.QVBoxLayout(hero)
        self.dashboard_hero_title = QtWidgets.QLabel("Dashboard")
        self.dashboard_hero_title.setObjectName("HeroTitle")
        self.dashboard_hero_subtitle = QtWidgets.QLabel(
            "Balances, plan health, and monthly trends at a glance."
        )
        self.dashboard_hero_subtitle.setObjectName("HeroSubtitle")
        self.dashboard_helper_label = QtWidgets.QLabel(
            "Start with Current balance, Left this month, and Net rent. The tables below break down the rest."
        )
        self.dashboard_helper_label.setProperty("key", True)
        self.dashboard_helper_label.setWordWrap(True)
        hero_layout.addWidget(self.dashboard_hero_title)
        hero_layout.addWidget(self.dashboard_hero_subtitle)
        hero_layout.addWidget(self.dashboard_helper_label)

        self.dashboard_highlight_labels: Dict[str, QtWidgets.QLabel] = {}
        self.dashboard_highlight_titles: Dict[str, QtWidgets.QLabel] = {}
        highlight_row = QtWidgets.QHBoxLayout()
        highlight_row.setSpacing(10)
        highlight_specs = [
            ("estimated_balance", "Current balance"),
            ("current_month_remaining", "Left this month"),
            ("rent_month_paid", "Net rent this month"),
            ("average_expenses", "Average per month"),
        ]
        for key, title in highlight_specs:
            card = QtWidgets.QFrame()
            card.setProperty("card", True)
            card.setProperty("feature", "true")
            card.setMinimumHeight(86)
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(4)
            title_label = QtWidgets.QLabel(title)
            title_label.setProperty("key", True)
            value_label = QtWidgets.QLabel("-")
            value_label.setProperty("value", True)
            value_label.setProperty("valueAccent", True)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card_layout.addStretch()
            highlight_row.addWidget(card, 1)
            self.dashboard_highlight_titles[key] = title_label
            self.dashboard_highlight_labels[key] = value_label

        self.summary_title_label = QtWidgets.QLabel("Details")
        self.summary_title_label.setProperty("sectionTitle", True)
        summary_header_row = QtWidgets.QHBoxLayout()
        summary_header_row.setSpacing(12)
        summary_header_row.addWidget(self.summary_title_label)
        summary_header_row.addStretch()

        summary_container = QtWidgets.QWidget()
        summary_layout = QtWidgets.QVBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)

        self.summary_labels: Dict[str, QtWidgets.QLabel] = {}
        self.summary_key_labels: Dict[str, QtWidgets.QLabel] = {}
        self.summary_cards: Dict[str, QtWidgets.QFrame] = {}
        self.summary_section_groups: Dict[str, QtWidgets.QGroupBox] = {}
        summary_sections = [
            (
                "snapshot",
                "Right now",
                [
                    ("estimated_balance", "Current balance", True),
                    ("total_expenses", "Spent so far", False),
                    ("total_income", "Income so far", False),
                    ("adjustments_total", "Adjustments total", False),
                ],
            ),
            (
                "month_focus",
                "This month",
                [
                    ("current_month_expenses", "Spent this month", False),
                    ("current_month_income", "Income this month", False),
                    ("current_month_adjustments", "Adjustments this month", False),
                    ("current_month_remaining", "Left this month", True),
                    ("rent_month_paid", "Net rent this month", True),
                    ("rent_month_income_offset", "Rent credits this month", False),
                ],
            ),
            (
                "forecast_view",
                "Looking ahead",
                [
                    ("plan_budget_total", "Planned total", True),
                    ("projected_final_expenses", "Predicted total", True),
                    ("windowed_avg_monthly", "Recent monthly average", False),
                    ("average_expenses", "Average per month", False),
                    ("coverage_display", "Months covered", True),
                    ("coverage_12mo_display", "12-month runway", True),
                ],
            ),
        ]

        for section_key, section_title, fields in summary_sections:
            group = QtWidgets.QGroupBox(section_title)
            self.summary_section_groups[section_key] = group
            group_layout = QtWidgets.QGridLayout(group)
            group_layout.setHorizontalSpacing(12)
            group_layout.setVerticalSpacing(12)
            columns = 3 if len(fields) >= 3 else 2
            for index, (key, label, accent) in enumerate(fields):
                card = QtWidgets.QFrame()
                card.setProperty("card", True)
                card.setProperty("metricCard", True)
                if accent:
                    card.setProperty("feature", "true")
                card.setMinimumHeight(84)
                card_layout = QtWidgets.QVBoxLayout(card)
                card_layout.setContentsMargins(12, 11, 12, 11)
                card_layout.setSpacing(3)
                key_label = QtWidgets.QLabel(label)
                key_label.setProperty("key", True)
                key_label.setWordWrap(True)
                value_label = QtWidgets.QLabel("-")
                value_label.setProperty("value", True)
                if accent:
                    value_label.setProperty("valueAccent", True)
                card_layout.addWidget(key_label)
                card_layout.addWidget(value_label)
                card_layout.addStretch()
                row = index // columns
                col = index % columns
                group_layout.addWidget(card, row, col)
                self.summary_labels[key] = value_label
                self.summary_key_labels[key] = key_label
                self.summary_cards[key] = card
            summary_layout.addWidget(group)

        self.reconcile_group = QtWidgets.QGroupBox("Fix balance")
        reconcile_layout = QtWidgets.QVBoxLayout(self.reconcile_group)
        self.reconcile_hint = QtWidgets.QLabel(
            "If the balance looks wrong, enter the real balance and the app will add one adjustment entry."
        )
        self.reconcile_hint.setProperty("key", True)
        self.reconcile_balance_input = QtWidgets.QDoubleSpinBox()
        self.reconcile_balance_input.setRange(-1_000_000_000, 1_000_000_000)
        self.reconcile_balance_input.setDecimals(2)
        self.reconcile_button = QtWidgets.QPushButton("Fix Balance")
        self.reconcile_button.setProperty("primary", True)
        self.reconcile_button.clicked.connect(self.handle_reconcile_balance)
        self.reconcile_status = QtWidgets.QLabel("")
        self.reconcile_status.setProperty("key", True)
        reconcile_layout.addWidget(self.reconcile_hint)
        reconcile_layout.addWidget(self.reconcile_balance_input)
        reconcile_layout.addWidget(self.reconcile_button)
        reconcile_layout.addWidget(self.reconcile_status)
        reconcile_layout.addStretch()

        self.settings_group = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout(self.settings_group)

        self.setting_widgets: Dict[str, QtWidgets.QWidget] = {}
        self.settings_labels: Dict[str, QtWidgets.QLabel] = {}

        self.setting_widgets["starting_balance"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["refunds_total"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["plan_months_total"] = self._int_spin_box(0, 120)
        self.setting_widgets["months_elapsed"] = self._int_spin_box(0, 120)
        self.setting_widgets["rent_monthly_manual"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["food_house_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["misc_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["medical_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["school_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["household_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["health_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["extra_monthly"] = self._spin_box(0, 1_000_000_000, 2)
        self.setting_widgets["campus_reference_total"] = self._spin_box(0, 1_000_000_000, 2)

        self.misc_mode_combo = QtWidgets.QComboBox()
        self.misc_mode_combo.addItem("Manual", "manual")
        self.misc_mode_combo.addItem("Auto", "auto")
        self.misc_mode_combo.currentTextChanged.connect(self.on_misc_mode_changed)

        self.auto_include_recurring_checkbox = QtWidgets.QCheckBox(
            "Include recurring"
        )
        self.auto_include_recurring_checkbox.toggled.connect(self.on_settings_changed)
        self.auto_include_current_month_checkbox = QtWidgets.QCheckBox(
            "Include current month"
        )
        self.auto_include_current_month_checkbox.toggled.connect(
            self.on_settings_changed
        )

        self.auto_window_months_input = QtWidgets.QSpinBox()
        self.auto_window_months_input.setRange(0, 120)
        self.auto_window_months_input.setSpecialValueText("School year")
        self.auto_window_months_input.setSuffix(" mo")
        self.auto_window_months_input.valueChanged.connect(self.on_settings_changed)

        self.auto_weighted_checkbox = QtWidgets.QCheckBox("Weighted averages")
        self.auto_weighted_checkbox.toggled.connect(self.on_settings_changed)
        self.auto_weighted_checkbox.toggled.connect(self._update_auto_weight_controls)

        self.auto_weight_half_life_input = QtWidgets.QSpinBox()
        self.auto_weight_half_life_input.setRange(1, 120)
        self.auto_weight_half_life_input.setValue(6)
        self.auto_weight_half_life_input.setSuffix(" mo")
        self.auto_weight_half_life_input.valueChanged.connect(self.on_settings_changed)

        self.auto_misc_category_list = QtWidgets.QListWidget()
        self.auto_misc_category_list.setSelectionMode(
            QtWidgets.QAbstractItemView.NoSelection
        )
        self.auto_misc_category_list.setMinimumHeight(90)
        self.auto_misc_category_list.itemChanged.connect(self.on_settings_changed)

        self.auto_misc_value_label = QtWidgets.QLabel("-")
        self.auto_misc_value_label.setProperty("key", True)
        self.auto_recurring_excluded_label = QtWidgets.QLabel("")
        self.auto_recurring_excluded_label.setProperty("key", True)
        self.auto_recurring_excluded_label.setWordWrap(True)

        self.new_category_input = QtWidgets.QLineEdit()
        self.new_category_input.setPlaceholderText("New category")
        self.add_category_button = QtWidgets.QPushButton("Add")
        self.add_category_button.clicked.connect(self.handle_add_category)
        self.category_status_label = QtWidgets.QLabel("")
        self.category_status_label.setProperty("key", True)
        category_row = QtWidgets.QHBoxLayout()
        category_row.addWidget(self.new_category_input)
        category_row.addWidget(self.add_category_button)
        category_row.addWidget(self.category_status_label)
        category_row.addStretch()
        category_container = QtWidgets.QWidget()
        category_container.setLayout(category_row)

        self.auto_settings_group = QtWidgets.QGroupBox("Auto projection")
        self.auto_settings_labels: Dict[str, QtWidgets.QLabel] = {}
        auto_settings_layout = QtWidgets.QFormLayout(self.auto_settings_group)
        auto_include_label = QtWidgets.QLabel("Include recurring")
        auto_include_current_label = QtWidgets.QLabel("Include current month")
        auto_window_label = QtWidgets.QLabel("Window months")
        auto_weighted_label = QtWidgets.QLabel("Weighted")
        auto_half_life_label = QtWidgets.QLabel("Weight half-life")
        auto_categories_label = QtWidgets.QLabel("Auto categories")
        auto_monthly_label = QtWidgets.QLabel("Auto monthly total")
        self.auto_settings_labels.update(
            {
                "include_recurring": auto_include_label,
                "include_current_month": auto_include_current_label,
                "window_months": auto_window_label,
                "weighted": auto_weighted_label,
                "half_life": auto_half_life_label,
                "categories": auto_categories_label,
                "monthly_total": auto_monthly_label,
            }
        )
        auto_settings_layout.addRow(auto_include_label, self.auto_include_recurring_checkbox)
        auto_settings_layout.addRow(
            auto_include_current_label, self.auto_include_current_month_checkbox
        )
        auto_settings_layout.addRow(auto_window_label, self.auto_window_months_input)
        auto_settings_layout.addRow(auto_weighted_label, self.auto_weighted_checkbox)
        auto_settings_layout.addRow(auto_half_life_label, self.auto_weight_half_life_input)
        auto_settings_layout.addRow(auto_categories_label, self.auto_misc_category_list)
        auto_settings_layout.addRow(self.auto_recurring_excluded_label)
        auto_settings_layout.addRow(auto_monthly_label, self.auto_misc_value_label)

        language_combo = QtWidgets.QComboBox()
        language_combo.addItems(["EN", "FR"])
        self.setting_widgets["language"] = language_combo

        self.settings_labels["starting_balance"] = QtWidgets.QLabel("Starting balance")
        self.settings_labels["refunds_total"] = QtWidgets.QLabel("Refunds total")
        self.settings_labels["plan_months_total"] = QtWidgets.QLabel("Plan months total")
        self.settings_labels["months_elapsed"] = QtWidgets.QLabel("Months elapsed (auto)")
        self.settings_labels["months_remaining"] = QtWidgets.QLabel("Months remaining (auto)")
        self.settings_labels["rent_manual"] = QtWidgets.QLabel("Rent monthly (manual)")
        self.settings_labels["food_manual"] = QtWidgets.QLabel("Food monthly (manual)")
        self.settings_labels["medical_manual"] = QtWidgets.QLabel("Medical monthly (manual)")
        self.settings_labels["school_manual"] = QtWidgets.QLabel("School monthly (manual)")
        self.settings_labels["household_manual"] = QtWidgets.QLabel("Household monthly (manual)")
        self.settings_labels["health_manual"] = QtWidgets.QLabel("Health monthly (manual)")
        self.settings_labels["projection_mode"] = QtWidgets.QLabel("Projection mode")
        self.settings_labels["misc_manual"] = QtWidgets.QLabel("Misc monthly (manual)")
        self.settings_labels["add_category"] = QtWidgets.QLabel("Add category")
        self.settings_labels["extra_monthly"] = QtWidgets.QLabel("Extra monthly (12 mo)")
        self.settings_labels["campus_reference"] = QtWidgets.QLabel("Campus reference total")
        self.language_label = QtWidgets.QLabel("Language")

        settings_layout.addRow(self.settings_labels["starting_balance"], self.setting_widgets["starting_balance"])
        settings_layout.addRow(self.settings_labels["refunds_total"], self.setting_widgets["refunds_total"])
        self.setting_widgets["months_elapsed"].setEnabled(False)
        settings_layout.addRow(self.settings_labels["plan_months_total"], self.setting_widgets["plan_months_total"])
        settings_layout.addRow(self.settings_labels["months_elapsed"], self.setting_widgets["months_elapsed"])
        self.months_remaining_label = QtWidgets.QLabel("-")
        self.months_remaining_label.setProperty("key", True)
        settings_layout.addRow(self.settings_labels["months_remaining"], self.months_remaining_label)
        settings_layout.addRow(self.settings_labels["rent_manual"], self.setting_widgets["rent_monthly_manual"])
        settings_layout.addRow(self.settings_labels["food_manual"], self.setting_widgets["food_house_monthly"])
        settings_layout.addRow(self.settings_labels["medical_manual"], self.setting_widgets["medical_monthly"])
        settings_layout.addRow(self.settings_labels["school_manual"], self.setting_widgets["school_monthly"])
        settings_layout.addRow(self.settings_labels["household_manual"], self.setting_widgets["household_monthly"])
        settings_layout.addRow(self.settings_labels["health_manual"], self.setting_widgets["health_monthly"])
        settings_layout.addRow(self.settings_labels["projection_mode"], self.misc_mode_combo)
        settings_layout.addRow(self.settings_labels["misc_manual"], self.setting_widgets["misc_monthly"])
        settings_layout.addRow(self.auto_settings_group)
        settings_layout.addRow(self.settings_labels["add_category"], category_container)
        settings_layout.addRow(self.settings_labels["extra_monthly"], self.setting_widgets["extra_monthly"])
        settings_layout.addRow(
            self.settings_labels["campus_reference"], self.setting_widgets["campus_reference_total"]
        )
        settings_layout.addRow(self.language_label, self.setting_widgets["language"])

        self.settings_apply_button = QtWidgets.QPushButton("Apply Settings")
        self.settings_apply_button.setProperty("primary", True)
        self.settings_apply_button.setEnabled(False)
        self.settings_apply_button.clicked.connect(self.handle_apply_settings)
        self.settings_status_label = QtWidgets.QLabel("")
        self.settings_status_label.setProperty("key", True)
        settings_button_row = QtWidgets.QHBoxLayout()
        settings_button_row.addWidget(self.settings_status_label)
        settings_button_row.addStretch()
        settings_button_row.addWidget(self.settings_apply_button)
        settings_layout.addRow(settings_button_row)

        self.advanced_notes_toggle = QtWidgets.QPushButton(
            self._text("advanced_notes_show")
        )
        self.advanced_notes_toggle.setCheckable(True)
        self.advanced_notes_toggle.toggled.connect(self._set_advanced_notes_visible)
        settings_layout.addRow(self.advanced_notes_toggle)

        self.advanced_notes_container = QtWidgets.QWidget()
        advanced_notes_layout = QtWidgets.QVBoxLayout(self.advanced_notes_container)
        advanced_notes_layout.setContentsMargins(0, 0, 0, 0)
        advanced_notes_layout.setSpacing(10)

        self.calc_title_label = QtWidgets.QLabel("Calculation notes")
        self.calc_title_label.setProperty("key", True)
        self.settings_calc_label = QtWidgets.QLabel("")
        self.settings_calc_label.setProperty("key", True)
        self.settings_calc_label.setWordWrap(True)
        advanced_notes_layout.addWidget(self.calc_title_label)
        advanced_notes_layout.addWidget(self.settings_calc_label)

        self.auto_calc_title_label = QtWidgets.QLabel("Auto calculation notes")
        self.auto_calc_title_label.setProperty("key", True)
        self.auto_calc_label = QtWidgets.QLabel("")
        self.auto_calc_label.setProperty("key", True)
        self.auto_calc_label.setWordWrap(True)
        advanced_notes_layout.addWidget(self.auto_calc_title_label)
        advanced_notes_layout.addWidget(self.auto_calc_label)
        settings_layout.addRow(self.advanced_notes_container)
        self._set_advanced_notes_visible(False)

        for key, widget in self.setting_widgets.items():
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                widget.valueChanged.connect(self.on_settings_changed)
            elif isinstance(widget, QtWidgets.QSpinBox):
                widget.valueChanged.connect(self.on_settings_changed)
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.currentTextChanged.connect(self.on_settings_changed)

        self.monthly_group = QtWidgets.QGroupBox("Monthly plan vs actual")
        self.monthly_group.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        monthly_layout = QtWidgets.QVBoxLayout(self.monthly_group)
        self.monthly_table = QtWidgets.QTableWidget(0, 7)
        self.monthly_table.setHorizontalHeaderLabels(
            ["Month", "Budget (plan)", "Budget (proj)", "Total expenses", "Adjustments", "Delta $", "Delta %"]
        )
        self.monthly_table.horizontalHeader().setStretchLastSection(True)
        self.monthly_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.monthly_table.setAlternatingRowColors(True)
        self.monthly_table.verticalHeader().setVisible(False)
        self.monthly_table.setMinimumHeight(180)
        self.monthly_table.setMaximumHeight(320)
        monthly_layout.addWidget(self.monthly_table)

        self.category_average_group = QtWidgets.QGroupBox("Category averages")
        category_average_layout = QtWidgets.QVBoxLayout(self.category_average_group)
        self.category_average_hint = QtWidgets.QLabel("")
        self.category_average_hint.setProperty("key", True)
        self.category_average_hint.setWordWrap(True)
        self.category_average_table = QtWidgets.QTableWidget(0, 4)
        self.category_average_table.setHorizontalHeaderLabels(
            ["Category", "Avg / month", "Total", "Months used"]
        )
        self.category_average_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.category_average_table.setAlternatingRowColors(True)
        self.category_average_table.verticalHeader().setVisible(False)
        self.category_average_table.horizontalHeader().setStretchLastSection(True)
        self.category_average_table.setMinimumHeight(220)
        category_average_layout.addWidget(self.category_average_hint)
        category_average_layout.addWidget(self.category_average_table)

        self.charts_group = QtWidgets.QGroupBox("Charts")
        self.charts_group.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self.charts_group.setMinimumHeight(760)
        charts_layout = QtWidgets.QGridLayout(self.charts_group)
        charts_layout.setSpacing(14)
        charts_layout.setColumnStretch(0, 1)
        charts_layout.setColumnStretch(1, 1)
        charts_layout.setRowStretch(0, 1)
        charts_layout.setRowStretch(1, 1)
        self.chart_labels = []
        self.chart_source_pixmaps: List[QtGui.QPixmap] = []
        self.chart_title_labels: List[QtWidgets.QLabel] = []
        chart_specs = [
            "Monthly spending by category",
            "Cumulative vs plan",
            "Running balance",
            "Category averages",
        ]
        for index, title in enumerate(chart_specs):
            chart_card = QtWidgets.QFrame()
            chart_card.setProperty("card", True)
            chart_card.setMinimumWidth(360)
            chart_card.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            )
            chart_card_layout = QtWidgets.QVBoxLayout(chart_card)
            chart_card_layout.setContentsMargins(12, 12, 12, 12)
            chart_card_layout.setSpacing(8)
            title_label = QtWidgets.QLabel(title)
            title_label.setProperty("sectionTitle", True)
            image_label = ClickableImageLabel(self._text("no_data"))
            image_label.setAlignment(QtCore.Qt.AlignCenter)
            image_label.setMinimumHeight(290)
            image_label.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            )
            image_label.setWordWrap(True)
            image_label.clicked.connect(
                lambda idx=index: self._open_chart_preview(idx)
            )
            chart_card_layout.addWidget(title_label)
            chart_card_layout.addWidget(image_label, 1)
            charts_layout.addWidget(chart_card, index // 2, index % 2)
            self.chart_labels.append(image_label)
            self.chart_title_labels.append(title_label)

        self._update_chart_label_hints()

        self.dashboard_nav_group = QtWidgets.QGroupBox("Quick actions")
        dashboard_nav_layout = QtWidgets.QGridLayout(self.dashboard_nav_group)
        dashboard_nav_layout.setHorizontalSpacing(10)
        dashboard_nav_layout.setVerticalSpacing(10)
        self.dashboard_nav_buttons: Dict[str, QtWidgets.QPushButton] = {}
        dashboard_nav_items = [
            ("tab_add_entry", "Add Entry"),
            ("tab_transactions", "Transactions"),
            ("tab_recurring", "Recurring"),
            ("tab_report", "Reports"),
        ]
        for index, (target, title) in enumerate(dashboard_nav_items):
            button = QtWidgets.QPushButton(title)
            button.setProperty("primary", True)
            button.setMinimumHeight(42)
            button.clicked.connect(
                lambda _checked=False, key=target: self._navigate_to(key)
            )
            dashboard_nav_layout.addWidget(button, index // 2, index % 2)
            self.dashboard_nav_buttons[target] = button

        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(18)
        left_column = QtWidgets.QVBoxLayout()
        left_column.setSpacing(18)
        right_column = QtWidgets.QVBoxLayout()
        right_column.setSpacing(18)
        left_column.addWidget(self.monthly_group)
        left_column.addWidget(self.category_average_group)
        left_column.addWidget(self.charts_group)
        left_column.addStretch()
        right_column.addWidget(self.dashboard_nav_group)
        right_column.addWidget(self.reconcile_group, 1)
        right_column.addWidget(self.settings_group, 3)
        right_column.addStretch()

        body_layout.addLayout(left_column, 3)
        body_layout.addLayout(right_column, 1)

        layout.addWidget(hero)
        layout.addLayout(highlight_row)
        layout.addLayout(summary_header_row)
        layout.addWidget(summary_container)
        layout.addLayout(body_layout)

        scroll.setWidget(container)
        wrapper_layout = QtWidgets.QVBoxLayout(tab)
        wrapper_layout.addWidget(scroll)

        self.tabs.addTab(tab, "Dashboard")

    def _build_report_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_report = tab
        tab.setProperty("page", True)
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        hero = QtWidgets.QFrame()
        hero.setProperty("hero", True)
        hero_layout = QtWidgets.QVBoxLayout(hero)
        self.report_hero_title = QtWidgets.QLabel("Reports")
        self.report_hero_title.setObjectName("HeroTitle")
        self.report_hero_subtitle = QtWidgets.QLabel(
            "Export a polished PDF summary with tables and charts."
        )
        self.report_hero_subtitle.setObjectName("HeroSubtitle")
        hero_layout.addWidget(self.report_hero_title)
        hero_layout.addWidget(self.report_hero_subtitle)

        self.report_info = QtWidgets.QLabel(
            "Export a PDF or Excel report with tables and graphs."
        )
        self.report_pdf_language_label = QtWidgets.QLabel("PDF language")
        self.report_pdf_language_label.setProperty("key", True)
        self.report_pdf_language_hint = QtWidgets.QLabel(
            "Choose whether the PDF is generated in English or French."
        )
        self.report_pdf_language_hint.setProperty("key", True)
        self.report_pdf_language_hint.setWordWrap(True)
        self.report_pdf_language_combo = QtWidgets.QComboBox()
        populate_value_combo(
            self.report_pdf_language_combo,
            "language_choice",
            self._current_language(),
            self._current_language(),
        )
        self.export_button = QtWidgets.QPushButton("Export PDF")
        self.export_button.setProperty("primary", True)
        self.export_button.clicked.connect(self.handle_export_pdf)
        self.export_excel_button = QtWidgets.QPushButton("Export Excel")
        self.export_excel_button.clicked.connect(self.handle_export_excel)
        self.export_json_button = QtWidgets.QPushButton("Export JSON")
        self.export_json_button.clicked.connect(self.handle_export_json)
        self.import_button = QtWidgets.QPushButton("Import Data")
        self.import_button.setProperty("primary", True)
        self.import_button.clicked.connect(self.handle_import_data)
        self.reset_data_button = QtWidgets.QPushButton("Reset Data")
        self.reset_data_button.setProperty("warning", True)
        self.reset_data_button.clicked.connect(self.handle_reset_data)
        self.report_status = QtWidgets.QLabel("")
        self.report_status.setProperty("status", True)

        card = QtWidgets.QFrame()
        card.setProperty("card", True)
        card.setProperty("feature", "true")
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        self.report_export_title = QtWidgets.QLabel("Export")
        self.report_export_title.setProperty("sectionTitle", True)
        card_layout.addWidget(self.report_export_title)
        card_layout.addWidget(self.report_info)
        card_layout.addWidget(self.report_pdf_language_label)
        card_layout.addWidget(self.report_pdf_language_combo)
        card_layout.addWidget(self.report_pdf_language_hint)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.export_button)
        button_row.addWidget(self.export_excel_button)
        button_row.addWidget(self.export_json_button)
        button_row.addStretch()
        card_layout.addLayout(button_row)
        card_layout.addWidget(self.report_status)
        card_layout.addStretch()

        import_card = QtWidgets.QFrame()
        import_card.setProperty("card", True)
        import_layout = QtWidgets.QVBoxLayout(import_card)
        import_layout.setContentsMargins(18, 18, 18, 18)
        self.report_import_title = QtWidgets.QLabel("Import")
        self.report_import_title.setProperty("sectionTitle", True)
        self.report_import_hint = QtWidgets.QLabel(
            "Import JSON, CSV, or Excel files."
        )
        self.report_import_hint.setProperty("key", True)
        import_layout.addWidget(self.report_import_title)
        import_layout.addWidget(self.report_import_hint)
        import_button_row = QtWidgets.QHBoxLayout()
        import_button_row.addWidget(self.import_button)
        import_button_row.addWidget(self.reset_data_button)
        import_button_row.addStretch()
        import_layout.addLayout(import_button_row)
        import_layout.addStretch()

        layout.addWidget(hero)
        body_row = QtWidgets.QHBoxLayout()
        body_row.setSpacing(18)
        body_row.addWidget(card, 2)
        body_row.addWidget(import_card, 1)
        layout.addLayout(body_row)
        layout.addStretch()

        self.tabs.addTab(tab, "Report")

    def _build_recurring_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_recurring = tab
        tab.setProperty("page", True)
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        hero = QtWidgets.QFrame()
        hero.setProperty("hero", True)
        hero_layout = QtWidgets.QVBoxLayout(hero)
        self.recurring_hero_title = QtWidgets.QLabel("Recurring Charges")
        self.recurring_hero_title.setObjectName("HeroTitle")
        self.recurring_hero_subtitle = QtWidgets.QLabel(
            "Automatic, manual, or paused charges that apply on a schedule."
        )
        self.recurring_hero_subtitle.setObjectName("HeroSubtitle")
        hero_layout.addWidget(self.recurring_hero_title)
        hero_layout.addWidget(self.recurring_hero_subtitle)

        form_card = QtWidgets.QFrame()
        form_card.setProperty("card", True)
        form_card.setProperty("feature", "true")
        form_layout = QtWidgets.QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 18, 18, 18)
        self.recurring_form_title = QtWidgets.QLabel("Add recurring charge")
        self.recurring_form_title.setProperty("sectionTitle", True)
        form_layout.addWidget(self.recurring_form_title)

        form = QtWidgets.QFormLayout()
        self.recurring_label_input = QtWidgets.QLineEdit()
        self.recurring_amount_input = QtWidgets.QDoubleSpinBox()
        self.recurring_amount_input.setRange(0, 1_000_000_000)
        self.recurring_amount_input.setDecimals(2)
        self.recurring_type_input = QtWidgets.QComboBox()
        populate_value_combo(
            self.recurring_type_input,
            "type",
            self._current_language(),
            "expense",
        )
        self.recurring_category_input = QtWidgets.QComboBox()
        self.recurring_category_input.setEditable(True)
        populate_category_combo(
            self.recurring_category_input,
            self.categories,
            self._current_language(),
        )
        self.recurring_notes_input = QtWidgets.QLineEdit()
        self.recurring_start_date_input = QtWidgets.QDateEdit()
        self.recurring_start_date_input.setCalendarPopup(True)
        self.recurring_start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.recurring_start_date_input.setDate(QtCore.QDate.currentDate())

        self.recurring_end_enabled = QtWidgets.QCheckBox("Has end date")
        self.recurring_end_date_input = QtWidgets.QDateEdit()
        self.recurring_end_date_input.setCalendarPopup(True)
        self.recurring_end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.recurring_end_date_input.setDate(QtCore.QDate.currentDate())
        self.recurring_end_date_input.setEnabled(False)
        self.recurring_end_enabled.toggled.connect(
            self.recurring_end_date_input.setEnabled
        )

        self.recurring_frequency_input = QtWidgets.QComboBox()
        populate_value_combo(
            self.recurring_frequency_input,
            "frequency",
            self._current_language(),
            "monthly",
        )

        self.recurring_status_input = QtWidgets.QComboBox()
        populate_value_combo(
            self.recurring_status_input,
            "status",
            self._current_language(),
            "automatic",
        )

        self.recurring_form_labels: Dict[str, QtWidgets.QLabel] = {}
        recurring_label_label = QtWidgets.QLabel("Label")
        recurring_amount_label = QtWidgets.QLabel("Amount")
        recurring_type_label = QtWidgets.QLabel("Type")
        recurring_category_label = QtWidgets.QLabel("Category")
        recurring_notes_label = QtWidgets.QLabel("Notes")
        recurring_start_label = QtWidgets.QLabel("Start date")
        recurring_frequency_label = QtWidgets.QLabel("Frequency")
        recurring_status_label = QtWidgets.QLabel("Status")
        self.recurring_form_labels.update(
            {
                "label": recurring_label_label,
                "amount": recurring_amount_label,
                "type": recurring_type_label,
                "category": recurring_category_label,
                "notes": recurring_notes_label,
                "start": recurring_start_label,
                "frequency": recurring_frequency_label,
                "status": recurring_status_label,
            }
        )
        form.addRow(recurring_label_label, self.recurring_label_input)
        form.addRow(recurring_amount_label, self.recurring_amount_input)
        form.addRow(recurring_type_label, self.recurring_type_input)
        form.addRow(recurring_category_label, self.recurring_category_input)
        form.addRow(recurring_notes_label, self.recurring_notes_input)
        form.addRow(recurring_start_label, self.recurring_start_date_input)
        form.addRow(self.recurring_end_enabled, self.recurring_end_date_input)
        form.addRow(recurring_frequency_label, self.recurring_frequency_input)
        form.addRow(recurring_status_label, self.recurring_status_input)
        form_layout.addLayout(form)

        form_buttons = QtWidgets.QHBoxLayout()
        self.recurring_add_button = QtWidgets.QPushButton("Save Recurring")
        self.recurring_add_button.setProperty("primary", True)
        self.recurring_add_button.clicked.connect(self.handle_add_recurring)
        form_buttons.addWidget(self.recurring_add_button)
        form_buttons.addStretch()
        form_layout.addLayout(form_buttons)

        self.recurring_status_label = QtWidgets.QLabel("")
        self.recurring_status_label.setProperty("key", True)
        form_layout.addWidget(self.recurring_status_label)

        table_card = QtWidgets.QFrame()
        table_card.setProperty("card", True)
        table_layout = QtWidgets.QVBoxLayout(table_card)
        table_layout.setContentsMargins(18, 18, 18, 18)
        self.recurring_table_title = QtWidgets.QLabel("Recurring list")
        self.recurring_table_title.setProperty("sectionTitle", True)
        table_layout.addWidget(self.recurring_table_title)

        self.recurring_table = QtWidgets.QTableWidget(0, 9)
        self.recurring_table.setHorizontalHeaderLabels(
            [
                "Label",
                "Type",
                "Amount",
                "Category",
                "Frequency",
                "Start",
                "End",
                "Status",
                "Last applied",
            ]
        )
        self.recurring_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.recurring_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.recurring_table.setAlternatingRowColors(True)
        self.recurring_table.verticalHeader().setVisible(False)
        self.recurring_table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.recurring_table)

        action_row = QtWidgets.QHBoxLayout()
        self.recurring_apply_button = QtWidgets.QPushButton("Apply Selected")
        self.recurring_apply_button.setProperty("primary", True)
        self.recurring_edit_button = QtWidgets.QPushButton("Edit")
        self.recurring_delete_button = QtWidgets.QPushButton("Delete")
        self.recurring_delete_button.setProperty("warning", True)
        self.recurring_apply_button.clicked.connect(self.handle_apply_recurring_now)
        self.recurring_edit_button.clicked.connect(self.handle_edit_recurring)
        self.recurring_delete_button.clicked.connect(self.handle_delete_recurring)
        action_row.addWidget(self.recurring_apply_button)
        action_row.addWidget(self.recurring_edit_button)
        action_row.addWidget(self.recurring_delete_button)
        action_row.addStretch()
        table_layout.addLayout(action_row)

        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(18)
        body_layout.addWidget(form_card, 1)
        body_layout.addWidget(table_card, 2)

        layout.addWidget(hero)
        layout.addLayout(body_layout)
        layout.addStretch()

        self.tabs.addTab(tab, "Recurring")

    def _animate_in(self) -> None:
        effect = QtWidgets.QGraphicsOpacityEffect(self.tabs)
        self.tabs.setGraphicsEffect(effect)
        animation = QtCore.QPropertyAnimation(effect, b"opacity")
        animation.setDuration(450)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        animation.start()
        self._intro_animation = animation

    def _current_language(self) -> str:
        if hasattr(self, "setting_widgets"):
            widget = self.setting_widgets.get("language")
            if isinstance(widget, QtWidgets.QComboBox):
                text = widget.currentText().strip()
                if text:
                    return text
        if self.settings and getattr(self.settings, "language", None):
            return str(self.settings.language)
        return "EN"

    def _selected_pdf_language(self) -> str:
        if hasattr(self, "report_pdf_language_combo"):
            value = combo_value(self.report_pdf_language_combo)
            if value in {"EN", "FR"}:
                return value
        return self._current_language()

    def _text(self, key: str) -> str:
        language = self._current_language()
        lang_map = UI_TEXT.get(language, UI_TEXT["EN"])
        return lang_map.get(key, UI_TEXT["EN"].get(key, key))

    def _apply_language(self, language: Optional[str] = None) -> None:
        lang = language or self._current_language()
        lang_map = UI_TEXT.get(lang, UI_TEXT["EN"])
        summary_labels = lang_map.get("summary_labels", {})
        summary_sections = lang_map.get("summary_sections", {})
        language_widget = self.setting_widgets.get("language") if hasattr(self, "setting_widgets") else None
        if isinstance(language_widget, QtWidgets.QComboBox):
            current_choice = language_widget.currentText().strip().upper()
            if current_choice != lang:
                language_widget.blockSignals(True)
                language_widget.setCurrentText(lang)
                language_widget.blockSignals(False)
        self.setWindowTitle(lang_map.get("app_title", "Offline Budget Tracker"))
        if hasattr(self, "tabs"):
            if hasattr(self, "tab_add_entry"):
                index = self.tabs.indexOf(self.tab_add_entry)
                if index >= 0:
                    self.tabs.setTabText(index, lang_map.get("tab_add", "Add Entry"))
            if hasattr(self, "tab_transactions"):
                index = self.tabs.indexOf(self.tab_transactions)
                if index >= 0:
                    self.tabs.setTabText(index, lang_map.get("tab_transactions", "Transactions"))
            if hasattr(self, "tab_dashboard"):
                index = self.tabs.indexOf(self.tab_dashboard)
                if index >= 0:
                    self.tabs.setTabText(index, lang_map.get("tab_dashboard", "Dashboard"))
            if hasattr(self, "tab_recurring"):
                index = self.tabs.indexOf(self.tab_recurring)
                if index >= 0:
                    self.tabs.setTabText(index, lang_map.get("tab_recurring", "Recurring"))
            if hasattr(self, "tab_report"):
                index = self.tabs.indexOf(self.tab_report)
                if index >= 0:
                    self.tabs.setTabText(index, lang_map.get("tab_report", "Report"))
            if hasattr(self, "tab_welcome"):
                index = self.tabs.indexOf(self.tab_welcome)
                if index >= 0:
                    self.tabs.setTabText(index, lang_map.get("tab_welcome", "Welcome"))

        if hasattr(self, "welcome_hero_title"):
            self.welcome_hero_title.setText(lang_map.get("welcome_title", "Welcome"))
        if hasattr(self, "welcome_hero_subtitle"):
            self.welcome_hero_subtitle.setText(
                lang_map.get(
                    "welcome_subtitle",
                    "Customize your view and jump to any section.",
                )
            )
        if hasattr(self, "welcome_customize_title"):
            self.welcome_customize_title.setText(
                lang_map.get("welcome_customize_title", "Customize")
            )
        if hasattr(self, "welcome_customize_hint"):
            self.welcome_customize_hint.setText(
                lang_map.get("welcome_customize_hint", "Choose a theme, font, and accent color.")
            )
        if hasattr(self, "welcome_theme_label"):
            self.welcome_theme_label.setText(
                lang_map.get("welcome_theme_label", "Theme")
            )
        if hasattr(self, "welcome_font_label"):
            self.welcome_font_label.setText(
                lang_map.get("welcome_font_label", "Font")
            )
        if hasattr(self, "welcome_accent_label"):
            self.welcome_accent_label.setText(
                lang_map.get("welcome_accent_label", "Accent color")
            )
        if hasattr(self, "welcome_accent_button"):
            self.welcome_accent_button.setText(
                lang_map.get("welcome_pick_accent", "Pick color")
            )
        if hasattr(self, "welcome_accent_reset"):
            self.welcome_accent_reset.setText(
                lang_map.get("welcome_reset_accent", "Reset color")
            )
        if hasattr(self, "welcome_nav_title"):
            self.welcome_nav_title.setText(
                lang_map.get("welcome_nav_title", "Navigate")
            )
        if hasattr(self, "nav_buttons"):
            nav_labels = {
                "tab_add_entry": "nav_add",
                "tab_transactions": "nav_transactions",
                "tab_dashboard": "nav_dashboard",
                "tab_recurring": "nav_recurring",
                "tab_report": "nav_report",
            }
            for key, button in self.nav_buttons.items():
                text_key = nav_labels.get(key)
                if text_key:
                    button.setText(lang_map.get(text_key, button.text()))

        if hasattr(self, "add_hero_title"):
            self.add_hero_title.setText(lang_map.get("add_title", "Add Entry"))
        if hasattr(self, "add_hero_subtitle"):
            self.add_hero_subtitle.setText(
                lang_map.get("add_subtitle", "Quick capture or detailed entry, saved instantly.")
            )
        if hasattr(self, "quick_entry_input"):
            self.quick_entry_input.setPlaceholderText(
                lang_map.get("add_placeholder", "Quick entry: 42 Walmart")
            )
        if hasattr(self, "quick_title"):
            self.quick_title.setText(lang_map.get("quick_title", "Quick Entry"))
        if hasattr(self, "quick_hint"):
            self.quick_hint.setText(lang_map.get("quick_hint", "Type amount then label. Example: 42 Walmart"))
        if hasattr(self, "quick_button"):
            self.quick_button.setText(lang_map.get("quick_button", "Quick Save"))
        if hasattr(self, "details_title"):
            self.details_title.setText(lang_map.get("details_title", "Details"))
        if hasattr(self, "save_button"):
            self.save_button.setText(lang_map.get("save_entry", "Save Entry"))
        if hasattr(self, "add_form_labels"):
            label_map = {
                "amount": "field_amount",
                "label": "field_label",
                "category": "field_category",
                "type": "field_type",
                "notes": "field_notes",
                "date": "field_date",
            }
            for key, label in self.add_form_labels.items():
                text_key = label_map.get(key)
                if text_key:
                    label.setText(lang_map.get(text_key, label.text()))
        if hasattr(self, "exclude_from_averages_checkbox"):
            self.exclude_from_averages_checkbox.setText(
                lang_map.get("exclude_from_averages", "Exclude from auto averages")
            )
        if hasattr(self, "type_input"):
            populate_value_combo(
                self.type_input,
                "type",
                lang,
                combo_value(self.type_input),
            )

        if hasattr(self, "tx_title_label"):
            self.tx_title_label.setText(lang_map.get("tx_title", "Transactions"))
        if hasattr(self, "search_input"):
            self.search_input.setPlaceholderText(lang_map.get("tx_search", "Search label, notes, category"))
        if hasattr(self, "edit_button"):
            self.edit_button.setText(lang_map.get("tx_edit", "Edit"))
        if hasattr(self, "delete_button"):
            self.delete_button.setText(lang_map.get("tx_delete", "Delete"))
        if hasattr(self, "transactions_table"):
            headers = lang_map.get("tx_table_headers")
            if isinstance(headers, list) and len(headers) == 7:
                self.transactions_table.setHorizontalHeaderLabels(headers)
        if hasattr(self, "month_filter"):
            self.update_month_filter_options()
        if hasattr(self, "transactions_table"):
            self.refresh_transactions_table()

        if hasattr(self, "dashboard_hero_title"):
            self.dashboard_hero_title.setText(lang_map.get("dash_title", "Dashboard"))
        if hasattr(self, "dashboard_hero_subtitle"):
            self.dashboard_hero_subtitle.setText(
                lang_map.get("dash_subtitle", "Balances, plan health, and monthly trends at a glance.")
            )
        if hasattr(self, "dashboard_helper_label"):
            self.dashboard_helper_label.setText(
                lang_map.get(
                    "dashboard_helper",
                    "Start with Current balance, Left this month, and Net rent. The tables below break down the rest.",
                )
            )
        if hasattr(self, "dashboard_highlight_titles"):
            highlight_text = lang_map.get("dashboard_highlights", {})
            for key, label in self.dashboard_highlight_titles.items():
                label.setText(highlight_text.get(key, label.text()))
        if hasattr(self, "summary_title_label"):
            self.summary_title_label.setText(lang_map.get("summary_title", "Key details"))
        if hasattr(self, "summary_key_labels"):
            for key, label in self.summary_key_labels.items():
                if key in summary_labels:
                    label.setText(summary_labels[key])
            window_label = self.summary_key_labels.get("windowed_avg_monthly")
            if window_label is not None:
                window_months = int(getattr(self.settings, "auto_window_months", 0) or 0)
                if window_months > 0:
                    window_label.setText(
                        self._text("monthly_avg_last").format(months=window_months)
                    )
                else:
                    window_label.setText(self._text("monthly_avg_school_year"))
        if hasattr(self, "summary_section_groups"):
            for key, group in self.summary_section_groups.items():
                if key in summary_sections:
                    group.setTitle(summary_sections[key])
        if hasattr(self, "reconcile_group"):
            self.reconcile_group.setTitle(lang_map.get("reconcile_title", "Balance reconcile"))
        if hasattr(self, "reconcile_hint"):
            self.reconcile_hint.setText(lang_map.get("reconcile_hint", "Enter actual balance to post a reconcile adjustment."))
        if hasattr(self, "reconcile_button"):
            self.reconcile_button.setText(lang_map.get("reconcile_button", "Apply Balance"))
        if hasattr(self, "settings_group"):
            self.settings_group.setTitle(lang_map.get("settings_title", "Settings"))
        settings_labels = lang_map.get("settings_labels", {})
        if hasattr(self, "settings_labels"):
            for key, label in self.settings_labels.items():
                if key in settings_labels:
                    label.setText(settings_labels[key])
        if hasattr(self, "language_label"):
            if "language" in settings_labels:
                self.language_label.setText(settings_labels["language"])
            else:
                self.language_label.setText("Language" if lang == "EN" else "Langue")
        if hasattr(self, "settings_apply_button"):
            self.settings_apply_button.setText(lang_map.get("apply_settings", "Apply Settings"))
        if hasattr(self, "new_category_input"):
            self.new_category_input.setPlaceholderText(
                lang_map.get("category_placeholder", "New category")
            )
        if hasattr(self, "add_category_button"):
            self.add_category_button.setText(lang_map.get("add_category_button", "Add"))
        if hasattr(self, "calc_title_label"):
            self.calc_title_label.setText(lang_map.get("calc_title", "Calculation notes"))
        if hasattr(self, "auto_calc_title_label"):
            self.auto_calc_title_label.setText(
                lang_map.get("auto_calc_title", "Auto calculation notes")
            )
        if hasattr(self, "advanced_notes_toggle"):
            self._set_advanced_notes_visible(self.advanced_notes_toggle.isChecked())
        auto_labels = lang_map.get("auto_labels", {})
        if hasattr(self, "auto_settings_group"):
            self.auto_settings_group.setTitle(auto_labels.get("title", "Auto projection"))
        if hasattr(self, "auto_settings_labels"):
            for key, label in self.auto_settings_labels.items():
                if key in auto_labels:
                    label.setText(auto_labels[key])
        if hasattr(self, "auto_include_recurring_checkbox"):
            self.auto_include_recurring_checkbox.setText(
                auto_labels.get("include_recurring", "Include recurring")
            )
        if hasattr(self, "auto_include_current_month_checkbox"):
            self.auto_include_current_month_checkbox.setText(
                auto_labels.get("include_current_month", "Include current month")
            )
        if hasattr(self, "auto_weighted_checkbox"):
            self.auto_weighted_checkbox.setText(auto_labels.get("weighted", "Weighted"))
        if hasattr(self, "auto_window_months_input"):
            self.auto_window_months_input.setSpecialValueText(
                lang_map.get("school_year", "School year")
            )
            self.auto_window_months_input.setSuffix(
                lang_map.get("month_suffix", " mo")
            )
        if hasattr(self, "auto_weight_half_life_input"):
            self.auto_weight_half_life_input.setSuffix(
                lang_map.get("month_suffix", " mo")
            )
        if hasattr(self, "misc_mode_combo"):
            manual_text = lang_map.get("mode_manual", "Manual")
            auto_text = lang_map.get("mode_auto", "Auto")
            for index in range(self.misc_mode_combo.count()):
                data = self.misc_mode_combo.itemData(index)
                if data == "manual":
                    self.misc_mode_combo.setItemText(index, manual_text)
                elif data == "auto":
                    self.misc_mode_combo.setItemText(index, auto_text)
        if hasattr(self, "recurring_type_input"):
            populate_value_combo(
                self.recurring_type_input,
                "type",
                lang,
                combo_value(self.recurring_type_input),
            )
        if hasattr(self, "recurring_frequency_input"):
            populate_value_combo(
                self.recurring_frequency_input,
                "frequency",
                lang,
                combo_value(self.recurring_frequency_input),
            )
        if hasattr(self, "recurring_status_input"):
            populate_value_combo(
                self.recurring_status_input,
                "status",
                lang,
                combo_value(self.recurring_status_input),
            )
        if hasattr(self, "monthly_group"):
            self.monthly_group.setTitle(
                lang_map.get("monthly_title", "Monthly plan vs actual")
            )
        if hasattr(self, "monthly_table"):
            headers = lang_map.get("monthly_table_headers")
            if isinstance(headers, list) and len(headers) == 6:
                self.monthly_table.setHorizontalHeaderLabels(headers)
        if hasattr(self, "category_average_group"):
            self.category_average_group.setTitle(
                lang_map.get("category_average_title", "Category averages")
            )
        if hasattr(self, "category_average_table"):
            headers = lang_map.get("category_average_headers")
            if isinstance(headers, list) and len(headers) == 4:
                self.category_average_table.setHorizontalHeaderLabels(headers)
        if hasattr(self, "charts_group"):
            self.charts_group.setTitle(lang_map.get("charts_title", "Charts"))
        if hasattr(self, "chart_title_labels") and len(self.chart_title_labels) == 4:
            chart_titles = lang_map.get("chart_titles", [])
            if len(chart_titles) == 4:
                for label, title in zip(self.chart_title_labels, chart_titles):
                    label.setText(title)
        if hasattr(self, "chart_labels"):
            self._update_chart_label_hints()
        if hasattr(self, "dashboard_nav_group"):
            self.dashboard_nav_group.setTitle(
                lang_map.get("dashboard_nav_title", "Quick actions")
            )
        if hasattr(self, "dashboard_nav_buttons"):
            nav_map = {
                "tab_add_entry": lang_map.get("nav_add", "Add Entry"),
                "tab_transactions": lang_map.get("nav_transactions", "Transactions"),
                "tab_recurring": lang_map.get("nav_recurring", "Recurring"),
                "tab_report": lang_map.get("nav_report", "Reports"),
            }
            for key, button in self.dashboard_nav_buttons.items():
                button.setText(nav_map.get(key, button.text()))

        if hasattr(self, "report_hero_title"):
            self.report_hero_title.setText(lang_map.get("report_title", "Reports"))
        if hasattr(self, "report_hero_subtitle"):
            self.report_hero_subtitle.setText(
                lang_map.get("report_subtitle", "Export a polished PDF summary with tables and charts.")
            )
        if hasattr(self, "report_info"):
            self.report_info.setText(lang_map.get("report_info", "Export a PDF or Excel report with tables and graphs."))
        if hasattr(self, "report_pdf_language_label"):
            self.report_pdf_language_label.setText(
                lang_map.get("report_pdf_language_label", "PDF language")
            )
        if hasattr(self, "report_pdf_language_hint"):
            self.report_pdf_language_hint.setText(
                lang_map.get(
                    "report_pdf_language_hint",
                    "Choose whether the PDF is generated in English or French.",
                )
            )
        if hasattr(self, "report_pdf_language_combo"):
            populate_value_combo(
                self.report_pdf_language_combo,
                "language_choice",
                lang,
                lang,
            )
        if hasattr(self, "report_export_title"):
            self.report_export_title.setText(lang_map.get("export_title", "Export"))
        if hasattr(self, "report_import_title"):
            self.report_import_title.setText(lang_map.get("import_title", "Import"))
        if hasattr(self, "report_import_hint"):
            self.report_import_hint.setText(lang_map.get("import_hint", "Import JSON, CSV, or Excel files."))
        if hasattr(self, "export_button"):
            self.export_button.setText(lang_map.get("export_pdf", "Export PDF"))
        if hasattr(self, "export_excel_button"):
            self.export_excel_button.setText(lang_map.get("export_excel", "Export Excel"))
        if hasattr(self, "export_json_button"):
            self.export_json_button.setText(lang_map.get("export_json", "Export JSON"))
        if hasattr(self, "import_button"):
            self.import_button.setText(lang_map.get("import_button", "Import Data"))
        if hasattr(self, "reset_data_button"):
            self.reset_data_button.setText(lang_map.get("reset_data_button", "Reset Data"))

        if hasattr(self, "recurring_hero_title"):
            self.recurring_hero_title.setText(lang_map.get("recurring_title", "Recurring Charges"))
        if hasattr(self, "recurring_hero_subtitle"):
            self.recurring_hero_subtitle.setText(
                lang_map.get("recurring_subtitle", "Automatic, manual, or paused charges that apply on a schedule.")
            )
        if hasattr(self, "recurring_form_title"):
            self.recurring_form_title.setText(lang_map.get("recurring_form_title", "Add recurring charge"))
        if hasattr(self, "recurring_table_title"):
            self.recurring_table_title.setText(lang_map.get("recurring_table_title", "Recurring list"))
        if hasattr(self, "recurring_add_button"):
            self.recurring_add_button.setText(lang_map.get("recurring_save", "Save Recurring"))
        if hasattr(self, "recurring_apply_button"):
            self.recurring_apply_button.setText(lang_map.get("recurring_apply", "Apply Selected"))
        if hasattr(self, "recurring_edit_button"):
            self.recurring_edit_button.setText(lang_map.get("recurring_edit", "Edit"))
        if hasattr(self, "recurring_delete_button"):
            self.recurring_delete_button.setText(lang_map.get("recurring_delete", "Delete"))
        if hasattr(self, "recurring_form_labels"):
            label_map = {
                "label": "recurring_label",
                "amount": "recurring_amount",
                "type": "recurring_type",
                "category": "recurring_category",
                "notes": "recurring_notes",
                "start": "recurring_start",
                "frequency": "recurring_frequency",
                "status": "recurring_status",
            }
            for key, label in self.recurring_form_labels.items():
                text_key = label_map.get(key)
                if text_key:
                    label.setText(lang_map.get(text_key, label.text()))
        if hasattr(self, "recurring_end_enabled"):
            self.recurring_end_enabled.setText(lang_map.get("recurring_end", "Has end date"))
        if hasattr(self, "recurring_table"):
            headers = lang_map.get("recurring_table_headers")
            if isinstance(headers, list) and len(headers) == 9:
                self.recurring_table.setHorizontalHeaderLabels(headers)
            self.refresh_recurring_table()
        self._refresh_category_widgets()
        self._refresh_auto_misc_categories()
        if hasattr(self, "summary_labels"):
            self.update_dashboard()
        if hasattr(self, "undo_button"):
            self.undo_button.setText(lang_map.get("undo_label", "Undo"))
        if hasattr(self, "chart_labels"):
            self.update_charts()

    def _navigate_to(self, tab_attr: str) -> None:
        if not hasattr(self, "tabs"):
            return
        target = getattr(self, tab_attr, None)
        if target is None:
            return
        index = self.tabs.indexOf(target)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "chart_labels"):
            QtCore.QTimer.singleShot(0, self._refresh_chart_pixmaps)

    def handle_theme_change(self, theme_name: str) -> None:
        if not theme_name:
            return
        self.db.update_settings({"theme": theme_name})
        if self.settings:
            self.settings = replace(self.settings, theme=theme_name)
        self._apply_theme(theme_name)
        if hasattr(self, "theme_status_label"):
            self.theme_status_label.setText(self._text("theme_applied"))

    def handle_font_change(self, font_name: str) -> None:
        if not font_name:
            return
        if font_name == "System Default":
            value = ""
        else:
            value = font_name
        self.db.update_settings({"font_family": value})
        if self.settings:
            self.settings = replace(self.settings, font_family=value)
        self._apply_theme()
        if hasattr(self, "theme_status_label"):
            self.theme_status_label.setText(self._text("theme_applied"))

    def handle_pick_accent_color(self) -> None:
        current = ""
        if self.settings:
            current = getattr(self.settings, "accent_color", "") or ""
        if current:
            initial = QtGui.QColor(current)
        else:
            initial = QtGui.QColor()
        color = QtWidgets.QColorDialog.getColor(
            initial,
            self,
            self._text("welcome_accent_label"),
        )
        if not color.isValid():
            return
        hex_value = color.name()
        self.db.update_settings({"accent_color": hex_value})
        if self.settings:
            self.settings = replace(self.settings, accent_color=hex_value)
        self._apply_theme()
        if hasattr(self, "theme_status_label"):
            self.theme_status_label.setText(self._text("theme_applied"))

    def handle_reset_accent_color(self) -> None:
        self.db.update_settings({"accent_color": ""})
        if self.settings:
            self.settings = replace(self.settings, accent_color="")
        self._apply_theme()
        if hasattr(self, "theme_status_label"):
            self.theme_status_label.setText(self._text("theme_applied"))

    def _filter_summary_cards(self, text: str) -> None:
        if not hasattr(self, "summary_cards"):
            return
        query = (text or "").strip().lower()
        for key, card in self.summary_cards.items():
            label = self.summary_key_labels.get(key)
            label_text = label.text().strip().lower() if label else ""
            match = bool(query) and (query in label_text or query in key.lower())
            card.setProperty("highlight", "true" if match else "false")
            card.style().unpolish(card)
            card.style().polish(card)

    def _set_advanced_notes_visible(self, visible: bool) -> None:
        if hasattr(self, "advanced_notes_container"):
            self.advanced_notes_container.setVisible(visible)
        if hasattr(self, "advanced_notes_toggle"):
            self.advanced_notes_toggle.setText(
                self._text("advanced_notes_hide" if visible else "advanced_notes_show")
            )

    def _update_chart_label_hints(self) -> None:
        if not hasattr(self, "chart_labels") or not hasattr(self, "chart_title_labels"):
            return
        hint = self._text("chart_click_hint")
        for label, title_label in zip(self.chart_labels, self.chart_title_labels):
            label.setToolTip(f"{title_label.text()}\n{hint}")

    def _open_chart_preview(self, index: int) -> None:
        if not hasattr(self, "chart_source_pixmaps"):
            return
        if index < 0 or index >= len(self.chart_source_pixmaps):
            return
        pixmap = self.chart_source_pixmaps[index]
        if pixmap.isNull():
            return
        title = self._text("charts_title")
        if hasattr(self, "chart_title_labels") and index < len(self.chart_title_labels):
            title = self.chart_title_labels[index].text()
        dialog = ChartPreviewDialog(self, title, pixmap, self._text)
        dialog.exec()

    def _refresh_chart_pixmaps(self) -> None:
        if not hasattr(self, "chart_labels") or not hasattr(self, "chart_source_pixmaps"):
            return
        for label, pixmap in zip(self.chart_labels, self.chart_source_pixmaps):
            if pixmap.isNull():
                label.clear()
                label.setText(self._text("no_data"))
                continue
            target_size = label.size()
            if target_size.width() <= 0 or target_size.height() <= 0:
                continue
            label.setText("")
            label.setPixmap(
                pixmap.scaled(
                    target_size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
            )

    def _update_undo_ui(self) -> None:
        if hasattr(self, "undo_button"):
            self.undo_button.setEnabled(bool(self.undo_stack))

    def _push_undo(self, label: str, undo_callable) -> None:
        if self._undoing:
            return
        self.undo_stack.append(UndoAction(label=label, undo=undo_callable))
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack.pop(0)
        self._update_undo_ui()

    def handle_undo(self) -> None:
        if not self.undo_stack:
            if hasattr(self, "tx_status_label"):
                self.tx_status_label.setText(self._text("undo_empty"))
            return
        action = self.undo_stack.pop()
        self._update_undo_ui()
        self._undoing = True
        try:
            action.undo()
        finally:
            self._undoing = False
        self.reload_all()
        if hasattr(self, "tx_status_label"):
            self.tx_status_label.setText(
                self._text("undo_applied").format(label=action.label)
            )

    def _spin_box(self, minimum: float, maximum: float, decimals: int) -> QtWidgets.QDoubleSpinBox:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(decimals)
        return widget

    def _int_spin_box(self, minimum: int, maximum: int) -> QtWidgets.QSpinBox:
        widget = QtWidgets.QSpinBox()
        widget.setRange(minimum, maximum)
        return widget

    def _reset_date_to_now(self) -> None:
        now_iso = local_now_iso()
        dt_value = QtCore.QDateTime.fromString(now_iso, "yyyy-MM-ddTHH:mm:ss")
        if not dt_value.isValid():
            dt_value = QtCore.QDateTime.currentDateTime()
        self.date_input.blockSignals(True)
        self.date_input.setDateTime(dt_value)
        self.date_input.blockSignals(False)
        self.date_manual = False

    def on_date_changed(self) -> None:
        self.date_manual = True

    def _start_recurring_timer(self) -> None:
        if self._recurring_timer is None:
            self._recurring_timer = QtCore.QTimer(self)
            self._recurring_timer.setInterval(60 * 60 * 1000)
            self._recurring_timer.timeout.connect(self._auto_apply_recurring_today)
        self._recurring_timer.start()

    def _auto_apply_recurring_today(self) -> None:
        today = self.db.indiana_today()
        if self._last_recurring_check == today:
            return
        self._last_recurring_check = today
        added = self.db.apply_recurring_charges(
            today=today,
            apply_until=today,
            apply_from=today,
        )
        if added:
            self.reload_all()

    def _format_missed_summary(self, missed: List[tuple]) -> str:
        total = sum(len(dates) for _, dates in missed)
        lines: List[str] = []
        for charge, dates in missed:
            label = charge.label or self._text("recurring_default_label")
            frequency = charge.frequency or "monthly"
            date_range = f"{dates[0].isoformat()} to {dates[-1].isoformat()}"
            lines.append(
                self._text("missed_recurring_item").format(
                    label=label,
                    frequency=frequency,
                    count=len(dates),
                    date_range=date_range,
                )
            )
        if len(lines) > 6:
            extra = len(lines) - 6
            lines = lines[:6]
            lines.append(self._text("missed_recurring_more").format(extra=extra))
        details = "\n".join(lines)
        return self._text("missed_recurring_summary").format(
            total=total,
            details=details,
        )

    def _check_missed_recurring(self) -> None:
        try:
            today = self.db.indiana_today()
            cutoff = today - timedelta(days=1)
            missed = self.db.preview_recurring_charges(
                today=today,
                apply_until=cutoff,
            )
            if not missed:
                return
            message = self._format_missed_summary(missed)
            reply = QtWidgets.QMessageBox.question(
                self,
                self._text("missed_recurring_title"),
                message,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                applied = self.db.apply_recurring_charges(
                    today=today,
                    apply_until=cutoff,
                )
                if hasattr(self, "recurring_status_label"):
                    self.recurring_status_label.setText(
                        self._text("missed_recurring_applied").format(count=applied)
                    )
            else:
                if hasattr(self, "recurring_status_label"):
                    self.recurring_status_label.setText(
                        self._text("missed_recurring_skipped")
                    )
        except Exception as exc:
            if hasattr(self, "recurring_status_label"):
                self.recurring_status_label.setText(f"Recurring warning: {exc}")

    def reload_all(self) -> None:
        reload_warning = ""
        try:
            today = self.db.indiana_today()
            self.db.apply_recurring_charges(
                today=today,
                apply_until=today,
                apply_from=today,
            )
            self._last_recurring_check = today
        except Exception as exc:
            reload_warning = f"Recurring sync warning: {exc}"

        try:
            self.transactions = self.db.list_transactions()
        except Exception as exc:
            self.transactions = []
            reload_warning = (
                f"{reload_warning} | " if reload_warning else ""
            ) + f"Transactions warning: {exc}"
        try:
            self.recurring_charges = self.db.list_recurring_charges()
        except Exception as exc:
            self.recurring_charges = []
            reload_warning = (
                f"{reload_warning} | " if reload_warning else ""
            ) + f"Recurring list warning: {exc}"
        try:
            self.settings = self.db.get_settings()
        except Exception as exc:
            self.settings = replace(DEFAULT_SETTINGS)
            reload_warning = (
                f"{reload_warning} | " if reload_warning else ""
            ) + f"Settings warning: {exc}"

        self._sanitize_auto_categories()
        try:
            computed = load_computed_app_state(self.db, CATEGORY_DEFAULTS)
            self.settings = computed.settings
            self.transactions = computed.transactions
            self.recurring_charges = computed.recurring_charges
            self.summary = computed.summary
            self.monthly_stats = computed.monthly_stats
            self.categories = list(computed.categories)
        except Exception as exc:
            # Keep the app usable even if imported data is partially malformed.
            try:
                self.settings = self.db.get_settings()
            except Exception:
                self.settings = replace(DEFAULT_SETTINGS)
            try:
                self.transactions = self.db.list_transactions()
            except Exception:
                self.transactions = []
            try:
                self.recurring_charges = self.db.list_recurring_charges()
            except Exception:
                self.recurring_charges = []
            try:
                self.categories = self.db.list_categories() or list(CATEGORY_DEFAULTS)
            except Exception:
                self.categories = list(CATEGORY_DEFAULTS)
            try:
                self.summary = calculations.calculate_summary(
                    self.transactions, self.settings, self.recurring_charges
                )
                self.monthly_stats = calculations.calculate_monthly_stats(
                    self.transactions, self.settings, self.recurring_charges
                )
            except Exception:
                self.summary = calculations.calculate_summary(
                    [], replace(DEFAULT_SETTINGS), []
                )
                self.monthly_stats = []
            reload_warning = (
                f"{reload_warning} | " if reload_warning else ""
            ) + f"Data warning: {exc}"
        self._refresh_category_widgets()
        self._refresh_auto_misc_categories()
        self.settings_dirty = False
        if hasattr(self, "settings_apply_button"):
            self.settings_apply_button.setEnabled(False)
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.setText(reload_warning)
        self.update_dashboard()
        self.update_month_filter_options()
        self.refresh_transactions_table()
        if hasattr(self, "recurring_table"):
            self.refresh_recurring_table()
        self.update_charts()
        self._apply_language(self._current_language())
        self._apply_theme()
        self._update_undo_ui()

    def _refresh_categories(self) -> None:
        candidates: List[str] = []
        for tx in self.transactions:
            if tx.category:
                candidates.append(tx.category)
        for charge in self.recurring_charges:
            if charge.category:
                candidates.append(charge.category)
        if self.settings and getattr(self.settings, "auto_misc_categories", None):
            candidates.extend(self.settings.auto_misc_categories)
        if candidates:
            self.db.ensure_categories(candidates, backup=False)
        self.categories = self.db.list_categories() or list(CATEGORY_DEFAULTS)
        self._refresh_category_widgets()
        self._refresh_auto_misc_categories()

    def _recurring_expense_categories(self) -> set:
        categories = set()
        for charge in self.recurring_charges:
            if charge.type != "expense":
                continue
            if charge.category:
                categories.add(charge.category.strip().lower())
        return categories

    def _sanitize_auto_categories(self) -> None:
        if not self.settings:
            return
        recurring_categories = self._recurring_expense_categories()
        if not recurring_categories:
            return
        existing = list(getattr(self.settings, "auto_misc_categories", []) or [])
        filtered = [
            name for name in existing
            if str(name).strip().lower() not in recurring_categories
        ]
        if filtered == existing:
            return
        self.db.update_settings({"auto_misc_categories": filtered}, backup=False)
        self.settings = replace(self.settings, auto_misc_categories=filtered)

    def _update_category_combo(self, combo: QtWidgets.QComboBox) -> None:
        populate_category_combo(
            combo,
            self.categories,
            self._current_language(),
        )

    def _refresh_category_widgets(self) -> None:
        if hasattr(self, "category_input"):
            self._update_category_combo(self.category_input)
        if hasattr(self, "recurring_category_input"):
            self._update_category_combo(self.recurring_category_input)

    def _refresh_auto_misc_categories(self) -> None:
        if not hasattr(self, "auto_misc_category_list"):
            return
        selected = []
        if self.settings and getattr(self.settings, "auto_misc_categories", None):
            selected = list(self.settings.auto_misc_categories)
        selected_lower = {value.lower() for value in selected}
        recurring_categories = self._recurring_expense_categories()
        self.auto_misc_category_list.blockSignals(True)
        self.auto_misc_category_list.clear()
        for category in self.categories:
            item = QtWidgets.QListWidgetItem(
                translated_category(category, self._current_language())
            )
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setData(QtCore.Qt.UserRole, category)
            is_recurring = category.lower() in recurring_categories
            if is_recurring:
                item.setCheckState(QtCore.Qt.Unchecked)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(
                    QtCore.Qt.ForegroundRole,
                    QtGui.QBrush(QtGui.QColor("#9aa5b1")),
                )
            elif category.lower() in selected_lower:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
            self.auto_misc_category_list.addItem(item)
        self.auto_misc_category_list.blockSignals(False)
        if hasattr(self, "auto_recurring_excluded_label"):
            if recurring_categories:
                excluded = ", ".join(
                    translated_category(name, self._current_language())
                    for name in sorted(recurring_categories)
                )
                self.auto_recurring_excluded_label.setText(
                    self._text("auto_recurring_excluded").format(categories=excluded)
                )
                self.auto_recurring_excluded_label.setVisible(True)
            else:
                self.auto_recurring_excluded_label.setText("")
                self.auto_recurring_excluded_label.setVisible(False)

    def _selected_auto_misc_categories(self) -> List[str]:
        if not hasattr(self, "auto_misc_category_list"):
            return []
        selected: List[str] = []
        for index in range(self.auto_misc_category_list.count()):
            item = self.auto_misc_category_list.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                raw_value = item.data(QtCore.Qt.UserRole)
                selected.append(str(raw_value or item.text()))
        return selected

    def _update_misc_mode_controls(self) -> None:
        if not hasattr(self, "misc_mode_combo"):
            return
        mode_data = self.misc_mode_combo.currentData()
        if mode_data is None:
            auto_enabled = self.misc_mode_combo.currentText().strip().lower() == "auto"
        else:
            auto_enabled = mode_data == "auto"
        misc_widget = self.setting_widgets.get("misc_monthly")
        food_widget = self.setting_widgets.get("food_house_monthly")
        medical_widget = self.setting_widgets.get("medical_monthly")
        school_widget = self.setting_widgets.get("school_monthly")
        household_widget = self.setting_widgets.get("household_monthly")
        health_widget = self.setting_widgets.get("health_monthly")
        if misc_widget is not None:
            misc_widget.setEnabled(True)
        if food_widget is not None:
            food_widget.setEnabled(True)
        if medical_widget is not None:
            medical_widget.setEnabled(True)
        if school_widget is not None:
            school_widget.setEnabled(True)
        if household_widget is not None:
            household_widget.setEnabled(True)
        if health_widget is not None:
            health_widget.setEnabled(True)
        if hasattr(self, "auto_settings_group"):
            self.auto_settings_group.setEnabled(auto_enabled)
        self._update_auto_weight_controls()

    def _update_auto_weight_controls(self) -> None:
        if not hasattr(self, "auto_weighted_checkbox"):
            return
        weighted = self.auto_weighted_checkbox.isChecked()
        if hasattr(self, "auto_weight_half_life_input"):
            self.auto_weight_half_life_input.setEnabled(weighted)

    def on_misc_mode_changed(self, _value=None) -> None:
        self._update_misc_mode_controls()
        self.on_settings_changed()

    def handle_add_category(self) -> None:
        name = self.new_category_input.text().strip()
        if not name:
            self.category_status_label.setText(self._text("category_status_empty"))
            return
        added = self.db.ensure_categories([name])
        if added:
            self.category_status_label.setText(self._text("category_status_added"))
            self.new_category_input.clear()
        else:
            self.category_status_label.setText(self._text("category_status_exists"))
        self._refresh_categories()

    def update_month_filter_options(self) -> None:
        current = self.month_filter.currentData()
        if current is None:
            current = self.month_filter.currentText()
        months = sorted(
            {
                parsed.strftime("%Y-%m")
                for tx in self.transactions
                if not calculations._is_adjustment_tx(tx)
                for parsed in [parse_datetime(tx.datetime_local)]
                if parsed is not None
            }
        )
        self.month_filter.blockSignals(True)
        self.month_filter.clear()
        self.month_filter.addItem(self._text("all_months"), "all")
        for month_key in months:
            self.month_filter.addItem(month_key, month_key)
        if current in months:
            index = self.month_filter.findData(current)
        else:
            index = self.month_filter.findData("all")
        if index >= 0:
            self.month_filter.setCurrentIndex(index)
        self.month_filter.blockSignals(False)

    def refresh_transactions_table(self) -> None:
        search_term = self.search_input.text().strip().lower()
        selected_month = self.month_filter.currentData()
        if selected_month is None:
            selected_month = self.month_filter.currentText()

        invalid_date_group = self._text("invalid_date_group")
        filtered = []
        language = self._current_language()
        for tx in self.transactions:
            if calculations._is_adjustment_tx(tx):
                continue
            parsed = parse_datetime(tx.datetime_local)
            month_key = parsed.strftime("%Y-%m") if parsed is not None else None
            if selected_month and selected_month != "all":
                if month_key != selected_month:
                    continue
            if search_term:
                tx_type_label = translated_value("type", tx.type, language)
                tx_category_label = translated_category(tx.category, language)
                haystack = " ".join(
                    [tx.label, tx.category, tx_category_label, tx.notes, tx.type, tx_type_label]
                ).lower()
                if search_term not in haystack:
                    continue
            filtered.append((tx, month_key))

        grouped: Dict[str, List[Transaction]] = {}
        for tx, month_key in filtered:
            grouped.setdefault(month_key or invalid_date_group, []).append(tx)

        month_stats = {item["month"]: item for item in self.monthly_stats}

        self.transactions_table.setRowCount(0)
        for month_key in sorted(
            grouped.keys(), key=lambda item: (item == invalid_date_group, item)
        ):
            month_transactions = sorted(
                grouped[month_key], key=lambda item: item.datetime_local
            )
            month_total = 0.0
            for tx in month_transactions:
                row = self.transactions_table.rowCount()
                self.transactions_table.insertRow(row)
                date_item = QtWidgets.QTableWidgetItem(tx.datetime_local)
                date_item.setData(QtCore.Qt.UserRole, tx.id)
                self.transactions_table.setItem(row, 0, date_item)
                self.transactions_table.setItem(
                    row,
                    1,
                    QtWidgets.QTableWidgetItem(
                        translated_value("type", tx.type, language)
                    ),
                )
                self.transactions_table.setItem(
                    row, 2, QtWidgets.QTableWidgetItem(f"{tx.amount:.2f}")
                )
                self.transactions_table.setItem(
                    row, 3, QtWidgets.QTableWidgetItem(tx.label)
                )
                self.transactions_table.setItem(
                    row,
                    4,
                    QtWidgets.QTableWidgetItem(
                        translated_category(tx.category, language)
                    ),
                )
                self.transactions_table.setItem(
                    row, 5, QtWidgets.QTableWidgetItem(tx.notes)
                )
                self.transactions_table.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
                if tx.type == "expense":
                    month_total += tx.amount

            budget = 0.0
            if month_key in month_stats:
                budget = float(month_stats[month_key]["monthly_budget"])
            over_pct = ((month_total - budget) / budget * 100.0) if budget else 0.0

            row = self.transactions_table.rowCount()
            self.transactions_table.insertRow(row)
            label_text = (
                invalid_date_group
                if month_key == invalid_date_group
                else self._text("month_total_label").format(month=month_key)
            )
            total_label = QtWidgets.QTableWidgetItem(label_text)
            total_label.setFlags(total_label.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.transactions_table.setItem(row, 0, total_label)
            self.transactions_table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
            self.transactions_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(f"{month_total:.2f}")
            )
            self.transactions_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(self._text("total_label"))
            )
            self.transactions_table.setItem(
                row, 4, QtWidgets.QTableWidgetItem("")
            )
            self.transactions_table.setItem(
                row, 5, QtWidgets.QTableWidgetItem("")
            )
            self.transactions_table.setItem(
                row, 6, QtWidgets.QTableWidgetItem(f"{over_pct:.2f}%")
            )

        self.transactions_table.resizeColumnsToContents()

    def refresh_recurring_table(self) -> None:
        self.recurring_table.setRowCount(0)
        language = self._current_language()
        for charge in self.recurring_charges:
            row = self.recurring_table.rowCount()
            self.recurring_table.insertRow(row)
            label_item = QtWidgets.QTableWidgetItem(charge.label)
            label_item.setData(QtCore.Qt.UserRole, charge.id)
            self.recurring_table.setItem(row, 0, label_item)
            self.recurring_table.setItem(
                row,
                1,
                QtWidgets.QTableWidgetItem(
                    translated_value("type", charge.type, language)
                ),
            )
            self.recurring_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(f"{charge.amount:.2f}")
            )
            self.recurring_table.setItem(
                row,
                3,
                QtWidgets.QTableWidgetItem(
                    translated_category(charge.category, language)
                ),
            )
            self.recurring_table.setItem(
                row,
                4,
                QtWidgets.QTableWidgetItem(
                    translated_value("frequency", charge.frequency, language)
                ),
            )
            self.recurring_table.setItem(
                row, 5, QtWidgets.QTableWidgetItem(charge.start_date)
            )
            self.recurring_table.setItem(
                row, 6, QtWidgets.QTableWidgetItem(charge.end_date or "")
            )
            self.recurring_table.setItem(
                row,
                7,
                QtWidgets.QTableWidgetItem(
                    translated_value("status", charge.status, language)
                ),
            )
            self.recurring_table.setItem(
                row, 8, QtWidgets.QTableWidgetItem(charge.last_applied or "")
            )
        self.recurring_table.resizeColumnsToContents()

    def update_dashboard(self) -> None:
        if not self.settings:
            return
        self.loading = True
        try:
            currency_keys = (
                "estimated_balance",
                "total_expenses",
                "total_income",
                "adjustments_total",
                "plan_budget_total",
                "projected_final_expenses",
                "windowed_avg_monthly",
                "planned_remaining_total",
                "predicted_remaining_total",
                "average_expenses",
                "current_month_adjustments",
            )
            for key in currency_keys:
                if key in self.summary_labels:
                    self.summary_labels[key].setText(
                        f"{self.summary.get(key, 0.0):.2f}"
                    )
            if "current_month_expenses" in self.summary_labels:
                self.summary_labels["current_month_expenses"].setText(
                    f"{self.summary.get('current_month_expenses', 0.0):.2f}"
                )
            if "current_month_income" in self.summary_labels:
                self.summary_labels["current_month_income"].setText(
                    f"{self.summary.get('current_month_income', 0.0):.2f}"
                )
            if "rent_month_paid" in self.summary_labels:
                self.summary_labels["rent_month_paid"].setText(
                    f"{self.summary.get('rent_month_paid', 0.0):.2f}"
                )
            if "rent_month_income_offset" in self.summary_labels:
                self.summary_labels["rent_month_income_offset"].setText(
                    f"{self.summary.get('rent_month_income_offset', 0.0):.2f}"
                )
            for key in (
                "essential_month_used_pct_planned",
                "essential_month_used_pct_predicted",
                "essential_year_used_pct_planned",
                "essential_year_used_pct_predicted",
                "rent_month_used_pct_planned",
                "rent_month_used_pct_predicted",
                "rent_year_used_pct_planned",
                "rent_year_used_pct_predicted",
            ):
                if key in self.summary_labels:
                    self.summary_labels[key].setText(
                        f"{self.summary.get(key, 0.0):.2f}%"
                    )
            if "savings_vs_campus_planned" in self.summary_labels:
                self.summary_labels["savings_vs_campus_planned"].setText(
                    f"{self.summary.get('savings_vs_campus_planned', 0.0):.2f}"
                )
            if "savings_vs_campus_predicted" in self.summary_labels:
                self.summary_labels["savings_vs_campus_predicted"].setText(
                    f"{self.summary.get('savings_vs_campus_predicted', 0.0):.2f}"
                )
            full_remaining = self.summary.get("coverage_current_month_remaining_budget")
            to_date_remaining = self.summary.get("current_month_remaining_to_date")
            current_spent = self.summary.get("coverage_current_month_expenses")
            current_budget_full = self.summary.get("coverage_current_month_budget")
            current_budget_to_date = self.summary.get("current_month_budget_to_date")

            if to_date_remaining is None:
                self.summary_labels["current_month_remaining"].setText("-")
                self.summary_labels["current_month_remaining"].setToolTip("")
            else:
                display_value = float(to_date_remaining)
                self.summary_labels["current_month_remaining"].setText(f"{display_value:.2f}")
                if current_budget_to_date is not None and current_spent is not None:
                    tooltip = self._text("remaining_to_date_tooltip").format(
                        budget=float(current_budget_to_date),
                        spent=float(current_spent),
                        remaining=display_value,
                    )
                    self.summary_labels["current_month_remaining"].setToolTip(tooltip)
                else:
                    self.summary_labels["current_month_remaining"].setToolTip("")

            if "current_month_remaining_full" in self.summary_labels:
                if full_remaining is None:
                    self.summary_labels["current_month_remaining_full"].setText("-")
                    self.summary_labels["current_month_remaining_full"].setToolTip("")
                else:
                    full_value = float(full_remaining)
                    self.summary_labels["current_month_remaining_full"].setText(f"{full_value:.2f}")
                    if current_budget_full is not None and current_spent is not None:
                        tooltip = self._text("remaining_full_tooltip").format(
                            budget=float(current_budget_full),
                            spent=float(current_spent),
                            remaining=full_value,
                        )
                        self.summary_labels["current_month_remaining_full"].setToolTip(tooltip)
                    else:
                        self.summary_labels["current_month_remaining_full"].setToolTip("")
            coverage_text = self.summary.get("coverage_display") or "-"
            if self.summary.get("months_remaining") == 0:
                coverage_text = self._text("plan_complete")
            self.summary_labels["coverage_display"].setText(coverage_text)
            self.summary_labels["coverage_12mo_display"].setText(
                self.summary.get("coverage_12mo_display") or "-"
            )
            if hasattr(self, "dashboard_highlight_labels"):
                highlight_values = {
                    "estimated_balance": f"{self.summary.get('estimated_balance', 0.0):.2f}",
                    "current_month_remaining": (
                        "-"
                        if to_date_remaining is None
                        else f"{float(to_date_remaining):.2f}"
                    ),
                    "rent_month_paid": f"{self.summary.get('rent_month_paid', 0.0):.2f}",
                    "average_expenses": f"{self.summary.get('average_expenses', 0.0):.2f}",
                }
                for key, label in self.dashboard_highlight_labels.items():
                    label.setText(highlight_values.get(key, "-"))

            if hasattr(self, "reconcile_balance_input") and not self.reconcile_balance_input.hasFocus():
                self.reconcile_balance_input.blockSignals(True)
                self.reconcile_balance_input.setValue(
                    float(self.summary.get("estimated_balance", 0.0))
                )
                self.reconcile_balance_input.blockSignals(False)

            self._set_spin_value("starting_balance", self.settings.starting_balance)
            self._set_spin_value("refunds_total", self.settings.refunds_total)
            self._set_spin_value("plan_months_total", self.settings.plan_months_total)
            months_elapsed_auto = int(self.summary.get("months_elapsed_auto", 0) or 0)
            self._set_spin_value("months_elapsed", months_elapsed_auto)
            if hasattr(self, "months_remaining_label"):
                self.months_remaining_label.setText(
                    str(self.summary.get("months_remaining", 0) or 0)
                )
            self._set_spin_value("rent_monthly_manual", getattr(self.settings, "rent_monthly_manual", 0.0))
            self._set_spin_value("food_house_monthly", self.settings.food_house_monthly)
            self._set_spin_value("misc_monthly", self.settings.misc_monthly)
            self._set_spin_value("medical_monthly", self.settings.medical_monthly)
            self._set_spin_value("school_monthly", self.settings.school_monthly)
            self._set_spin_value("household_monthly", self.settings.household_monthly)
            self._set_spin_value("health_monthly", self.settings.health_monthly)
            self._set_spin_value("extra_monthly", self.settings.extra_monthly)
            self._set_spin_value(
                "campus_reference_total", self.settings.campus_reference_total
            )
            if hasattr(self, "misc_mode_combo"):
                self.misc_mode_combo.blockSignals(True)
                self.misc_mode_combo.setCurrentIndex(
                    1 if getattr(self.settings, "auto_misc_enabled", False) else 0
                )
                self.misc_mode_combo.blockSignals(False)
            if hasattr(self, "auto_include_recurring_checkbox"):
                self.auto_include_recurring_checkbox.blockSignals(True)
                self.auto_include_recurring_checkbox.setChecked(
                    bool(getattr(self.settings, "auto_include_recurring", False))
                )
                self.auto_include_recurring_checkbox.blockSignals(False)
            if hasattr(self, "auto_include_current_month_checkbox"):
                self.auto_include_current_month_checkbox.blockSignals(True)
                self.auto_include_current_month_checkbox.setChecked(
                    bool(getattr(self.settings, "auto_include_current_month", True))
                )
                self.auto_include_current_month_checkbox.blockSignals(False)
            if hasattr(self, "auto_window_months_input"):
                self.auto_window_months_input.blockSignals(True)
                self.auto_window_months_input.setValue(
                    int(getattr(self.settings, "auto_window_months", 0) or 0)
                )
                self.auto_window_months_input.blockSignals(False)
            if hasattr(self, "auto_weighted_checkbox"):
                self.auto_weighted_checkbox.blockSignals(True)
                self.auto_weighted_checkbox.setChecked(
                    bool(getattr(self.settings, "auto_weighted", False))
                )
                self.auto_weighted_checkbox.blockSignals(False)
            if hasattr(self, "auto_weight_half_life_input"):
                self.auto_weight_half_life_input.blockSignals(True)
                self.auto_weight_half_life_input.setValue(
                    int(getattr(self.settings, "auto_weight_half_life_months", 6) or 6)
                )
                self.auto_weight_half_life_input.blockSignals(False)
            if hasattr(self, "auto_misc_value_label"):
                auto_value = float(self.summary.get("auto_category_monthly_total", 0.0))
                self.auto_misc_value_label.setText(f"{auto_value:.2f}")
            self._update_misc_mode_controls()
            language_widget = self.setting_widgets["language"]
            if isinstance(language_widget, QtWidgets.QComboBox):
                language_value = self.settings.language
                if self.settings_dirty:
                    preview_value = language_widget.currentText().strip()
                    if preview_value:
                        language_value = preview_value
                language_widget.blockSignals(True)
                language_widget.setCurrentText(language_value)
                language_widget.blockSignals(False)
            if hasattr(self, "welcome_theme_combo"):
                theme_value = getattr(self.settings, "theme", "Dune")
                if self.welcome_theme_combo.findText(theme_value) < 0:
                    self.welcome_theme_combo.addItem(theme_value)
                self.welcome_theme_combo.blockSignals(True)
                self.welcome_theme_combo.setCurrentText(theme_value)
                self.welcome_theme_combo.blockSignals(False)
            if hasattr(self, "welcome_font_combo"):
                font_value = getattr(self.settings, "font_family", "") if self.settings else ""
                display_value = font_value if font_value else "System Default"
                if self.welcome_font_combo.findText(display_value) < 0:
                    self.welcome_font_combo.addItem(display_value)
                self.welcome_font_combo.blockSignals(True)
                self.welcome_font_combo.setCurrentText(display_value)
                self.welcome_font_combo.blockSignals(False)

            self.monthly_table.setRowCount(0)
            for item in self.monthly_stats:
                row = self.monthly_table.rowCount()
                self.monthly_table.insertRow(row)
                month = str(item.get("month", ""))
                planned = float(item.get("monthly_budget_planned", 0.0) or 0.0)
                predicted = float(item.get("monthly_budget_predicted", 0.0) or 0.0)
                total_expenses = float(item.get("total_expenses", 0.0) or 0.0)
                adjustments_total = float(item.get("adjustments_total", 0.0) or 0.0)
                delta_amount = float(item.get("delta_amount", 0.0) or 0.0)
                delta_pct = float(item.get("delta_pct", 0.0) or 0.0)
                self.monthly_table.setItem(row, 0, QtWidgets.QTableWidgetItem(month))
                self.monthly_table.setItem(
                    row, 1, QtWidgets.QTableWidgetItem(f"{planned:.2f}")
                )
                self.monthly_table.setItem(
                    row, 2, QtWidgets.QTableWidgetItem(f"{predicted:.2f}")
                )
                self.monthly_table.setItem(
                    row, 3, QtWidgets.QTableWidgetItem(f"{total_expenses:.2f}")
                )
                self.monthly_table.setItem(
                    row, 4, QtWidgets.QTableWidgetItem(f"{adjustments_total:.2f}")
                )
                self.monthly_table.setItem(
                    row, 5, QtWidgets.QTableWidgetItem(f"{delta_amount:.2f}")
                )
                self.monthly_table.setItem(
                    row, 6, QtWidgets.QTableWidgetItem(f"{delta_pct:.2f}%")
                )
            self.monthly_table.resizeColumnsToContents()
            if hasattr(self, "category_average_table"):
                rows = list(self.summary.get("category_average_rows", []))
                months_count = int(
                    self.summary.get("category_average_months_count", 0) or 0
                )
                self.category_average_table.setRowCount(0)
                for item in rows:
                    row = self.category_average_table.rowCount()
                    self.category_average_table.insertRow(row)
                    self.category_average_table.setItem(
                        row,
                        0,
                        QtWidgets.QTableWidgetItem(
                            translated_category(
                                str(item.get("category", "")),
                                self._current_language(),
                            )
                        ),
                    )
                    self.category_average_table.setItem(
                        row,
                        1,
                        QtWidgets.QTableWidgetItem(
                            f"{float(item.get('average_monthly', 0.0) or 0.0):.2f}"
                        ),
                    )
                    self.category_average_table.setItem(
                        row,
                        2,
                        QtWidgets.QTableWidgetItem(
                            f"{float(item.get('total', 0.0) or 0.0):.2f}"
                        ),
                    )
                    self.category_average_table.setItem(
                        row,
                        3,
                        QtWidgets.QTableWidgetItem(
                            str(int(item.get("months_with_spend", 0) or 0))
                        ),
                    )
                self.category_average_table.resizeColumnsToContents()
                if hasattr(self, "category_average_hint"):
                    if months_count > 0:
                        self.category_average_hint.setText(
                            self._text("category_average_hint_data").format(
                                months_count=months_count
                            )
                        )
                    else:
                        self.category_average_hint.setText(
                            self._text("category_average_hint_empty")
                        )
            self._update_settings_calc_label()
        except Exception as exc:
            if hasattr(self, "settings_status_label"):
                self.settings_status_label.setText(f"UI warning: {exc}")
        finally:
            self.loading = False

    def _update_settings_calc_label(self) -> None:
        if not hasattr(self, "settings_calc_label") or not self.settings:
            return
        try:
            total_expenses = float(self.summary.get("total_expenses", 0.0))
            total_income = float(self.summary.get("total_income", 0.0))
            starting = float(self.settings.starting_balance)
            months_remaining = int(self.summary.get("months_remaining", 0) or 0)
            months_elapsed_auto = int(
                self.summary.get("months_elapsed_auto", 0) or 0
            )
            food_monthly = float(self.settings.food_house_monthly)
            misc_monthly = float(getattr(self.settings, "misc_monthly", 0.0))
            medical_monthly = float(getattr(self.settings, "medical_monthly", 0.0))
            school_monthly = float(getattr(self.settings, "school_monthly", 0.0))
            household_monthly = float(getattr(self.settings, "household_monthly", 0.0))
            health_monthly = float(getattr(self.settings, "health_monthly", 0.0))
            manual_variable_monthly_total = float(
                self.summary.get("manual_variable_monthly_total", food_monthly + misc_monthly)
            )
            essential_manual_monthly_total = float(
                self.summary.get(
                    "essential_manual_monthly_total",
                    food_monthly + medical_monthly + school_monthly + household_monthly + health_monthly,
                )
            )
            predicted_variable_monthly_total = float(
                self.summary.get("predicted_variable_monthly_total", 0.0)
            )
            predicted_essential_monthly_total = float(
                self.summary.get("predicted_essential_monthly_total", 0.0)
            )
            variable_monthly_effective = float(
                self.summary.get("variable_monthly_effective", food_monthly + misc_monthly)
            )
            variable_remaining_total = float(
                self.summary.get("variable_remaining_total", 0.0)
            )
            food_monthly_effective = float(
                self.summary.get("food_monthly_effective", food_monthly)
            )
            auto_mode_active = bool(self.summary.get("auto_mode_active", False))
            auto_category_monthly_total = float(
                self.summary.get("auto_category_monthly_total", 0.0)
            )
            auto_category_totals = dict(
                self.summary.get("auto_category_totals", {})
            )
            auto_category_total_selected = float(
                self.summary.get("auto_category_total_selected", 0.0)
            )
            auto_category_monthly = dict(
                self.summary.get("auto_category_monthly", {})
            )
            auto_category_categories = list(
                self.summary.get("auto_category_categories", [])
            )
            auto_category_months_count = int(
                self.summary.get("auto_category_months_count", 0) or 0
            )
            auto_category_history_start = self.summary.get("auto_category_history_start")
            auto_category_history_end = self.summary.get("auto_category_history_end")
            auto_category_history_keys = list(
                self.summary.get("auto_category_history_keys", [])
            )
            auto_category_includes_recurring = bool(
                self.summary.get("auto_category_includes_recurring", False)
            )
            auto_category_weighted = bool(
                self.summary.get("auto_category_weighted", False)
            )
            auto_category_half_life = int(
                self.summary.get("auto_category_half_life_months", 1) or 1
            )
            auto_category_window_months = int(
                self.summary.get("auto_category_window_months", 0) or 0
            )
            rent_manual_monthly = float(self.summary.get("rent_manual_monthly", 0.0))
            rent_auto_monthly = float(self.summary.get("rent_auto_monthly", 0.0))
            extra_monthly = float(getattr(self.settings, "extra_monthly", 0.0))
            plan_months = int(self.settings.plan_months_total)
            recurring_plan_total = float(self.summary.get("recurring_plan_total", 0.0))
            plan_budget_total = float(self.summary.get("plan_budget_total", 0.0))
            essential_budget_total_planned = float(
                self.summary.get("essential_budget_total_planned", 0.0)
            )
            essential_budget_total_predicted = float(
                self.summary.get("essential_budget_total_predicted", 0.0)
            )
            essential_month_budget_planned = float(
                self.summary.get("essential_month_budget_planned", 0.0)
            )
            essential_month_budget_predicted = float(
                self.summary.get("essential_month_budget_predicted", 0.0)
            )
            essential_year_budget_planned = float(
                self.summary.get("essential_year_budget_planned", 0.0)
            )
            essential_year_budget_predicted = float(
                self.summary.get("essential_year_budget_predicted", 0.0)
            )
            campus_reference = float(self.settings.campus_reference_total)
            savings_vs_campus_planned = float(
                self.summary.get("savings_vs_campus_planned", 0.0)
            )
            savings_vs_campus_predicted = float(
                self.summary.get("savings_vs_campus_predicted", 0.0)
            )
            essential_budget_to_date_planned = float(
                self.summary.get("essential_budget_to_date_planned", 0.0)
            )
            essential_budget_to_date_predicted = float(
                self.summary.get("essential_budget_to_date_predicted", 0.0)
            )
            essential_expenses_to_date = float(
                self.summary.get("essential_expenses_to_date", 0.0)
            )
            essential_month_expenses = float(
                self.summary.get("essential_month_expenses", 0.0)
            )
            essential_month_used_pct_planned = float(
                self.summary.get("essential_month_used_pct_planned", 0.0)
            )
            essential_month_used_pct_predicted = float(
                self.summary.get("essential_month_used_pct_predicted", 0.0)
            )
            essential_year_used_pct_planned = float(
                self.summary.get("essential_year_used_pct_planned", 0.0)
            )
            essential_year_used_pct_predicted = float(
                self.summary.get("essential_year_used_pct_predicted", 0.0)
            )
            rent_paid_to_date = float(self.summary.get("rent_paid_to_date", 0.0))
            rent_month_paid = float(self.summary.get("rent_month_paid", 0.0))
            rent_budget_to_date_planned = float(
                self.summary.get("rent_budget_to_date_planned", 0.0)
            )
            rent_budget_to_date_predicted = float(
                self.summary.get("rent_budget_to_date_predicted", 0.0)
            )
            rent_month_budget_planned = float(
                self.summary.get("rent_month_budget_planned", 0.0)
            )
            rent_month_budget_predicted = float(
                self.summary.get("rent_month_budget_predicted", 0.0)
            )
            rent_year_budget_planned = float(
                self.summary.get("rent_year_budget_planned", 0.0)
            )
            rent_year_budget_predicted = float(
                self.summary.get("rent_year_budget_predicted", 0.0)
            )
            rent_month_used_pct_planned = float(
                self.summary.get("rent_month_used_pct_planned", 0.0)
            )
            rent_month_used_pct_predicted = float(
                self.summary.get("rent_month_used_pct_predicted", 0.0)
            )
            rent_year_used_pct_planned = float(
                self.summary.get("rent_year_used_pct_planned", 0.0)
            )
            rent_year_used_pct_predicted = float(
                self.summary.get("rent_year_used_pct_predicted", 0.0)
            )
            recurring_remaining_total = float(
                self.summary.get("recurring_remaining_total", 0.0)
            )
            planned_remaining_total = float(
                self.summary.get("planned_remaining_total", 0.0)
            )
            predicted_remaining_total = float(
                self.summary.get("predicted_remaining_total", 0.0)
            )
            expenses_to_date_plan = float(
                self.summary.get("expenses_to_date_plan", 0.0)
            )
            months_covered_to_date = int(
                self.summary.get("months_covered_to_date", 0) or 0
            )
            projected_final_expenses = float(
                self.summary.get("projected_final_expenses", 0.0)
            )
            average_expenses = float(self.summary.get("average_expenses", 0.0))
            extra_months_12 = int(self.summary.get("extra_months_12", 0) or 0)
            extra_12_total = float(self.summary.get("extra_12_total", 0.0))
            coverage_month_keys = list(self.summary.get("coverage_month_keys", []))
            coverage_month_budgets = list(self.summary.get("coverage_month_budgets", []))
            coverage_12_month_keys = list(self.summary.get("coverage_12_month_keys", []))
            coverage_12_budgets = list(self.summary.get("coverage_12_budgets", []))
            current_month_spent = float(
                self.summary.get("coverage_current_month_expenses", 0.0)
            )
            current_month_budget = self.summary.get("coverage_current_month_budget")
            current_month_remaining = self.summary.get(
                "coverage_current_month_remaining_budget"
            )
            current_month_budget_to_date = self.summary.get("current_month_budget_to_date")
            current_month_remaining_to_date = self.summary.get("current_month_remaining_to_date")
        except (TypeError, ValueError):
            self.settings_calc_label.setText("")
            if hasattr(self, "auto_calc_label"):
                self.auto_calc_label.setText("")
            return

        def _format_budget_items(months, budgets, limit=6) -> str:
            if not months or not budgets:
                return "-"
            items = [
                f"{month}:{budget:.2f}"
                for month, budget in zip(months, budgets)
            ]
            if len(items) > limit:
                return ", ".join(items[:limit]) + f", +{len(items) - limit} more"
            return ", ".join(items)

        def _format_month_keys(keys, limit=12) -> str:
            if not keys:
                return "-"
            if len(keys) > limit:
                return ", ".join(keys[:limit]) + f", +{len(keys) - limit} more"
            return ", ".join(keys)

        def _category_detail_lines(
            names, totals, monthly, months_count, weighted
        ) -> List[str]:
            if not names:
                return ["- (no categories selected)"]
            lines = []
            for name in names:
                total_value = float(totals.get(name, 0.0))
                monthly_value = float(monthly.get(name, 0.0))
                if weighted:
                    lines.append(
                        f"- {name}: total {total_value:.2f}, weighted monthly {monthly_value:.2f}"
                    )
                elif months_count:
                    lines.append(
                        f"- {name}: {total_value:.2f} / {months_count} = {monthly_value:.2f}"
                    )
                else:
                    lines.append(f"- {name}: {total_value:.2f} / 0 = 0.00")
            return lines
        def _section(title: str) -> List[str]:
            return [f"== {title} =="]

        def _line(text: str) -> str:
            return f"- {text}"

        lines: List[str] = []
        lines.extend(_section("Plan context"))
        lines.append(
            _line(
                "School year start month = "
                f"{getattr(calculations, 'SCHOOL_YEAR_START_MONTH', 9)}"
            )
        )
        lines.append(_line(f"Months elapsed (auto) = {months_elapsed_auto}"))
        lines.append(_line(f"Months remaining (auto) = {months_remaining}"))
        lines.append("")

        lines.extend(_section("Balance"))
        lines.append(_line("Estimated balance = starting - expenses + income"))
        lines.append(
            f"  = {starting:.2f} - {total_expenses:.2f} + {total_income:.2f}"
        )
        lines.append("")

        lines.extend(_section("Projection mode"))
        mode_label = "Auto (category averages)" if auto_mode_active else "Manual (settings)"
        lines.append(_line(f"Mode = {mode_label}"))
        lines.append(_line(f"Manual variable monthly = {manual_variable_monthly_total:.2f}"))
        lines.append(_line(f"Predicted variable monthly (auto avg) = {predicted_variable_monthly_total:.2f}"))
        lines.append(_line(f"Variable monthly used for coverage = {variable_monthly_effective:.2f}"))
        lines.append("")

        lines.extend(_section("Planned totals (manual + recurring)"))
        lines.append(_line(f"Recurring plan total (full plan) = {recurring_plan_total:.2f}"))
        lines.append(
            _line(
                "Essential monthly (manual) = "
                f"{food_monthly:.2f} + {medical_monthly:.2f} + {school_monthly:.2f} + "
                f"{household_monthly:.2f} + {health_monthly:.2f} = {essential_manual_monthly_total:.2f}"
            )
        )
        lines.append(
            _line(
                f"Essential total (planned) = {essential_manual_monthly_total:.2f} * "
                f"{plan_months} = {essential_budget_total_planned:.2f}"
            )
        )
        lines.append(
            _line("Planned remaining total = sum(remaining recurring + manual, current month adjusted)")
        )
        lines.append(f"  = {planned_remaining_total:.2f}")
        lines.append(_line("Planned total (9 mo) = expenses to date + planned remaining total"))
        lines.append(
            f"  = {expenses_to_date_plan:.2f} + {planned_remaining_total:.2f} = {plan_budget_total:.2f}"
        )
        lines.append("")

        lines.extend(_section("Predicted totals (auto averages)"))
        lines.append(
            _line("Predicted remaining total = sum(remaining recurring + auto avg, current month adjusted)")
        )
        lines.append(f"  = {predicted_remaining_total:.2f}")
        lines.append(
            _line(
                f"Essential monthly (predicted) = {predicted_essential_monthly_total:.2f}"
            )
        )
        lines.append(
            _line(
                f"Essential total (predicted) = {predicted_essential_monthly_total:.2f} * "
                f"{plan_months} = {essential_budget_total_predicted:.2f}"
            )
        )
        lines.append(_line("Projected final expenses = expenses to date + predicted remaining total"))
        lines.append(
            f"  = {expenses_to_date_plan:.2f} + {predicted_remaining_total:.2f} = {projected_final_expenses:.2f}"
        )
        if months_covered_to_date:
            lines.append(_line("Average monthly expenses = expenses to date / months covered"))
            lines.append(
                f"  = {expenses_to_date_plan:.2f} / {months_covered_to_date} = {average_expenses:.2f}"
            )
        else:
            lines.append(_line("Average monthly expenses = - (no months yet)"))
        lines.append("")

        lines.extend(_section("Savings vs campus"))
        lines.append(
            _line("Planned savings = campus reference - (expenses + planned remaining total)")
        )
        lines.append(
            f"  = {campus_reference:.2f} - ({total_expenses:.2f} + "
            f"{planned_remaining_total:.2f}) = {savings_vs_campus_planned:.2f}"
        )
        lines.append(
            _line("Predicted savings = campus reference - (expenses + predicted remaining total)")
        )
        lines.append(
            f"  = {campus_reference:.2f} - ({total_expenses:.2f} + "
            f"{predicted_remaining_total:.2f}) = {savings_vs_campus_predicted:.2f}"
        )
        lines.append("")

        lines.extend(_section("Essential % used"))
        if essential_month_budget_planned:
            lines.append(
                _line(
                    "Planned (month) = essential spent this month / planned essential monthly budget"
                )
            )
            lines.append(
                f"  = {essential_month_expenses:.2f} / {essential_month_budget_planned:.2f} = "
                f"{essential_month_used_pct_planned:.2f}%"
            )
        else:
            lines.append(_line("Planned (month) = - (no essential monthly budget)"))
        if essential_month_budget_predicted:
            lines.append(
                _line(
                    "Predicted (month) = essential spent this month / predicted essential monthly budget"
                )
            )
            lines.append(
                f"  = {essential_month_expenses:.2f} / {essential_month_budget_predicted:.2f} = "
                f"{essential_month_used_pct_predicted:.2f}%"
            )
        else:
            lines.append(_line("Predicted (month) = - (no predicted monthly budget)"))
        if essential_year_budget_planned:
            lines.append(
                _line(
                    "Planned (year) = essential spent to date / planned essential year budget"
                )
            )
            lines.append(
                f"  = {essential_expenses_to_date:.2f} / {essential_year_budget_planned:.2f} = "
                f"{essential_year_used_pct_planned:.2f}%"
            )
        else:
            lines.append(_line("Planned (year) = - (no essential year budget)"))
        if essential_year_budget_predicted:
            lines.append(
                _line(
                    "Predicted (year) = essential spent to date / predicted essential year budget"
                )
            )
            lines.append(
                f"  = {essential_expenses_to_date:.2f} / {essential_year_budget_predicted:.2f} = "
                f"{essential_year_used_pct_predicted:.2f}%"
            )
        else:
            lines.append(_line("Predicted (year) = - (no predicted year budget)"))
        lines.append("")

        lines.extend(_section("Rent % used"))
        if rent_month_budget_planned:
            lines.append(
                _line("Planned (month) = rent paid this month / planned rent monthly budget")
            )
            lines.append(
                f"  = {rent_month_paid:.2f} / {rent_month_budget_planned:.2f} = "
                f"{rent_month_used_pct_planned:.2f}%"
            )
        else:
            lines.append(_line("Planned (month) = - (no rent monthly budget)"))
        if rent_month_budget_predicted:
            lines.append(
                _line(
                    "Predicted (month) = rent paid this month / predicted rent monthly budget"
                )
            )
            lines.append(
                f"  = {rent_month_paid:.2f} / {rent_month_budget_predicted:.2f} = "
                f"{rent_month_used_pct_predicted:.2f}%"
            )
        else:
            lines.append(_line("Predicted (month) = - (no predicted rent monthly budget)"))
        if rent_year_budget_planned:
            lines.append(
                _line("Planned (year) = rent paid to date / planned rent year budget")
            )
            lines.append(
                f"  = {rent_paid_to_date:.2f} / {rent_year_budget_planned:.2f} = "
                f"{rent_year_used_pct_planned:.2f}%"
            )
        else:
            lines.append(_line("Planned (year) = - (no rent year budget)"))
        if rent_year_budget_predicted:
            lines.append(
                _line(
                    "Predicted (year) = rent paid to date / predicted rent year budget"
                )
            )
            lines.append(
                f"  = {rent_paid_to_date:.2f} / {rent_year_budget_predicted:.2f} = "
                f"{rent_year_used_pct_predicted:.2f}%"
            )
        else:
            lines.append(_line("Predicted (year) = - (no predicted rent year budget)"))
        lines.append("")

        lines.extend(_section("Coverage (projected)"))
        if months_remaining > 0:
            lines.append(_line("Coverage uses remaining monthly budgets (recurring + variable)"))
            lines.append(_line(f"Remaining recurring total = {recurring_remaining_total:.2f}"))
            lines.append(
                _line(
                    f"Remaining variable total = {variable_monthly_effective:.2f} * "
                    f"{months_remaining} = {variable_remaining_total:.2f}"
                )
            )
            if current_month_budget is not None and current_month_remaining is not None:
                lines.append(
                    _line(
                        f"Current month remaining = {current_month_budget:.2f} - "
                        f"{current_month_spent:.2f} = {float(current_month_remaining):.2f}"
                    )
                )
            if current_month_budget_to_date is not None and current_month_remaining_to_date is not None:
                lines.append(
                    _line(
                        f"Current month remaining (to-date recurring) = "
                        f"{float(current_month_budget_to_date):.2f} - "
                        f"{current_month_spent:.2f} = {float(current_month_remaining_to_date):.2f}"
                    )
                )
            lines.append(
                _line(
                    f"School year budgets = {_format_budget_items(coverage_month_keys, coverage_month_budgets)}"
                )
            )
            lines.append(_line(f"School year coverage = {self.summary.get('coverage_display') or '-'}"))
            lines.append(
                _line(
                    f"12-month extra months = {extra_months_12} @ "
                    f"{extra_monthly:.2f} = {extra_12_total:.2f}"
                )
            )
            lines.append(
                _line(
                    f"12-month budgets = {_format_budget_items(coverage_12_month_keys, coverage_12_budgets)}"
                )
            )
            lines.append(
                _line(f"12-month coverage = {self.summary.get('coverage_12mo_display') or '-'}")
            )
        else:
            lines.append(_line("Coverage = plan complete"))

        self.settings_calc_label.setText("\n".join(lines))

        if not hasattr(self, "auto_calc_label"):
            return

        auto_lines: List[str] = []
        auto_lines.append("== Auto projection ==")
        if auto_mode_active:
            auto_lines.append("- Auto projection = enabled")
        else:
            auto_lines.append("- Auto projection = disabled (manual settings drive projections)")
            auto_lines.append("- Auto preview (based on current selections)")
        if auto_category_window_months:
            auto_lines.append(f"- Window = last {auto_category_window_months} months")
        else:
            auto_lines.append("- Window = school year to date")
        auto_lines.append(
            f"- Include recurring = {'yes' if auto_category_includes_recurring else 'no'}"
        )
        auto_lines.append(
            f"- Include current month = {'yes' if self.settings.auto_include_current_month else 'no'}"
        )
        auto_lines.append(
            f"- Weighted averages = {'on' if auto_category_weighted else 'off'}"
        )
        if auto_category_weighted:
            auto_lines.append(f"- Weight half-life = {auto_category_half_life} months")
        if auto_category_months_count:
            history_text = f"{auto_category_months_count} months"
            if auto_category_history_start:
                history_text += f" from {auto_category_history_start}"
            if auto_category_history_end:
                history_text += f" to {auto_category_history_end}"
            auto_lines.append(f"- History range = {history_text}")
            auto_lines.append(
                f"- History months = {_format_month_keys(auto_category_history_keys)}"
            )
        else:
            auto_lines.append("- History range = - (no history yet)")
            auto_lines.append("- Monthly averages default to 0.00")

        auto_lines.append("")
        auto_lines.append("== Per-category averages ==")
        auto_lines.extend(
            _category_detail_lines(
                auto_category_categories,
                auto_category_totals,
                auto_category_monthly,
                auto_category_months_count,
                auto_category_weighted,
            )
        )
        if auto_category_categories:
            auto_lines.append(
                f"- Total selected (history) = {auto_category_total_selected:.2f}"
            )
            if auto_category_months_count and not auto_category_weighted:
                auto_lines.append(
                    (
                        f"- Monthly total = {auto_category_total_selected:.2f} / "
                        f"{auto_category_months_count} = {auto_category_monthly_total:.2f}"
                    )
                )
            else:
                auto_lines.append(
                    (
                        f"- Monthly total (sum of category averages) = "
                        f"{auto_category_monthly_total:.2f}"
                    )
                )
        auto_lines.append("")
        auto_lines.append("== Manual fallback when unchecked ==")
        auto_lines.append(
            f"- Food fallback = {food_monthly:.2f} "
            f"(selected: {'yes' if any(calculations._is_food_text(name) for name in auto_category_categories) else 'no'})"
        )
        auto_lines.append(
            f"- Medical fallback = {medical_monthly:.2f} "
            f"(selected: {'yes' if any(calculations._is_medical_text(name) for name in auto_category_categories) else 'no'})"
        )
        auto_lines.append(
            f"- School fallback = {school_monthly:.2f} "
            f"(selected: {'yes' if any(calculations._is_school_text(name) for name in auto_category_categories) else 'no'})"
        )
        auto_lines.append(
            f"- Household fallback = {household_monthly:.2f} "
            f"(selected: {'yes' if any(calculations._is_household_text(name) for name in auto_category_categories) else 'no'})"
        )
        auto_lines.append(
            f"- Health fallback = {health_monthly:.2f} "
            f"(selected: {'yes' if any(calculations._is_health_text(name) for name in auto_category_categories) else 'no'})"
        )
        auto_lines.append(
            f"- Misc fallback = {misc_monthly:.2f} "
            f"(selected: {'yes' if any(calculations._is_misc_text(name) for name in auto_category_categories) else 'no'})"
        )
        auto_lines.append("")
        auto_lines.append(
            f"- Auto monthly total used in projections = {auto_category_monthly_total:.2f}"
        )
        auto_lines.append(f"- Rent auto average (history) = {rent_auto_monthly:.2f}")
        auto_lines.append(f"- Rent manual (plan) = {rent_manual_monthly:.2f}")
        if not auto_category_categories:
            auto_lines.append(
                "- Select categories in Auto projection to calculate averages."
            )

        self.auto_calc_label.setText("\n".join(auto_lines))

    def _set_spin_value(self, key: str, value: Union[float, int]) -> None:
        widget = self.setting_widgets.get(key)
        if widget is None:
            return
        widget.blockSignals(True)
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(value))
        widget.blockSignals(False)

    def update_setting(self, field: str, value) -> None:
        if self.loading:
            return
        self.db.update_settings({field: value})
        self.reload_all()

    def on_settings_changed(self, _value=None) -> None:
        if self.loading:
            return
        self.settings_dirty = True
        if hasattr(self, "settings_apply_button"):
            self.settings_apply_button.setEnabled(True)
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.setText(self._text("settings_pending"))
        language_widget = self.setting_widgets.get("language") if hasattr(self, "setting_widgets") else None
        if language_widget is not None and self.sender() is language_widget:
            self._apply_language(language_widget.currentText())

    def update_charts(self) -> None:
        if not self.settings:
            return
        if not self.monthly_stats:
            for label in self.chart_labels:
                label.clear()
                label.setText(self._text("no_data"))
            self.chart_source_pixmaps = []
            return
        language = self._current_language()
        chart_bytes = [
            charts.render_monthly_spending(self.transactions, language),
            charts.render_cumulative_vs_plan(self.monthly_stats, language),
            charts.render_running_balance(self.transactions, self.settings, language),
            charts.render_category_averages(self.transactions, language),
        ]
        self.chart_source_pixmaps = []
        for label, data in zip(self.chart_labels, chart_bytes):
            image = QtGui.QImage.fromData(data)
            pixmap = QtGui.QPixmap.fromImage(image)
            self.chart_source_pixmaps.append(pixmap)
            label.clear()
            label.setText("")
        self._refresh_chart_pixmaps()

    def handle_add_entry(self) -> None:
        quick_text = self.quick_entry_input.text().strip()
        amount = float(self.amount_input.value())
        label = self.label_input.text().strip()
        category = self.category_input.currentText().strip() or "misc"
        notes = self.notes_input.text().strip()
        tx_type = combo_value(self.type_input)
        excluded = (
            self.exclude_from_averages_checkbox.isChecked()
            if hasattr(self, "exclude_from_averages_checkbox")
            else False
        )
        if self.date_manual:
            datetime_local = self.date_input.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        else:
            datetime_local = local_now_iso()

        if quick_text:
            match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(.*)$", quick_text)
            if not match:
                self.add_status_label.setText(self._text("quick_entry_invalid"))
                return
            amount = float(match.group(1))
            label = match.group(2).strip()
            tx_type = "expense"
            if not label:
                label = ""

        if amount <= 0:
            self.add_status_label.setText(self._text("amount_required"))
            return

        tx_id = self.db.add_transaction(
            amount=amount,
            tx_type=tx_type,
            label=label,
            category=category,
            notes=notes,
            datetime_local=datetime_local,
            excluded_from_averages=excluded,
        )
        self._push_undo(
            self._text("undo_add_tx"),
            lambda tx_id=tx_id: self.db.delete_transaction(tx_id),
        )
        self.quick_entry_input.clear()
        self.amount_input.setValue(0.0)
        self.label_input.clear()
        self.notes_input.clear()
        self._reset_date_to_now()
        if hasattr(self, "exclude_from_averages_checkbox"):
            self.exclude_from_averages_checkbox.setChecked(False)
        self.add_status_label.setText(self._text("tx_saved"))
        self.reload_all()

    def handle_add_recurring(self) -> None:
        label = self.recurring_label_input.text().strip()
        amount = float(self.recurring_amount_input.value())
        category = self.recurring_category_input.currentText().strip() or "misc"
        notes = self.recurring_notes_input.text().strip()
        tx_type = combo_value(self.recurring_type_input)
        start_date = self.recurring_start_date_input.date().toString("yyyy-MM-dd")
        end_date = (
            self.recurring_end_date_input.date().toString("yyyy-MM-dd")
            if self.recurring_end_enabled.isChecked()
            else None
        )
        frequency = combo_value(self.recurring_frequency_input)
        status = combo_value(self.recurring_status_input)

        if not label:
            self.recurring_status_label.setText(self._text("recurring_label_required"))
            return
        if amount <= 0:
            self.recurring_status_label.setText(self._text("recurring_amount_required"))
            return
        if end_date and end_date < start_date:
            self.recurring_status_label.setText(self._text("recurring_end_after"))
            return

        charge_id = self.db.add_recurring_charge(
            label=label,
            amount=amount,
            tx_type=tx_type,
            category=category,
            notes=notes,
            start_date=start_date,
            end_date=end_date,
            status=status,
            frequency=frequency,
        )
        self._push_undo(
            self._text("undo_add_recurring"),
            lambda charge_id=charge_id: self.db.delete_recurring_charge(charge_id),
        )
        self.recurring_label_input.clear()
        self.recurring_amount_input.setValue(0.0)
        self.recurring_notes_input.clear()
        self.recurring_end_enabled.setChecked(False)
        self.recurring_status_label.setText(self._text("recurring_saved"))
        self.reload_all()

    def _selected_transaction(self) -> Optional[Transaction]:
        selected_indexes = self.transactions_table.selectedIndexes()
        if not selected_indexes:
            row = self.transactions_table.currentRow()
            if row < 0:
                return None
        else:
            row = selected_indexes[0].row()
        date_item = self.transactions_table.item(row, 0)
        if date_item is None:
            return None
        tx_id = date_item.data(QtCore.Qt.UserRole)
        if not tx_id:
            return None
        for tx in self.transactions:
            if tx.id == tx_id:
                return tx
        return None

    def handle_edit_transaction(self) -> None:
        tx = self._selected_transaction()
        if not tx:
            self.tx_status_label.setText(self._text("no_selection_edit"))
            return
        dialog = TransactionDialog(self, tx, self.categories, self._text)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            data = dialog.get_data()
            original = Transaction(
                id=tx.id,
                datetime_local=tx.datetime_local,
                amount=tx.amount,
                type=tx.type,
                label=tx.label,
                category=tx.category,
                notes=tx.notes,
                recurring_id=tx.recurring_id,
                excluded_from_averages=bool(getattr(tx, "excluded_from_averages", False)),
            )
            self.db.update_transaction(
                tx.id,
                amount=float(data["amount"]),
                tx_type=str(data["type"]),
                label=str(data["label"]),
                category=str(data["category"]),
                notes=str(data["notes"]),
                datetime_local=str(data["datetime_local"]),
                excluded_from_averages=bool(data.get("excluded_from_averages", False)),
            )
            self._push_undo(
                self._text("undo_edit_tx"),
                lambda original=original: self.db.update_transaction(
                    original.id,
                    amount=original.amount,
                    tx_type=original.type,
                    label=original.label,
                    category=original.category,
                    notes=original.notes,
                    datetime_local=original.datetime_local,
                    excluded_from_averages=bool(
                        getattr(original, "excluded_from_averages", False)
                    ),
                ),
            )
            self.tx_status_label.setText(self._text("tx_updated"))
            self.reload_all()

    def handle_delete_transaction(self) -> None:
        tx = self._selected_transaction()
        if not tx:
            self.tx_status_label.setText(self._text("no_selection_delete"))
            return
        self.db.delete_transaction(tx.id)
        self._push_undo(
            self._text("undo_delete_tx"),
            lambda tx=tx: self.db.insert_transaction_with_id(tx),
        )
        self.tx_status_label.setText(self._text("tx_deleted"))
        self.reload_all()

    def _selected_recurring_charge(self) -> Optional[RecurringCharge]:
        selected_indexes = self.recurring_table.selectedIndexes()
        if not selected_indexes:
            row = self.recurring_table.currentRow()
            if row < 0:
                return None
        else:
            row = selected_indexes[0].row()
        id_item = self.recurring_table.item(row, 0)
        if id_item is None:
            return None
        charge_id = id_item.data(QtCore.Qt.UserRole)
        if not charge_id:
            return None
        for charge in self.recurring_charges:
            if charge.id == charge_id:
                return charge
        return None

    def handle_edit_recurring(self) -> None:
        charge = self._selected_recurring_charge()
        if not charge:
            self.recurring_status_label.setText(self._text("recurring_select_edit"))
            return
        dialog = RecurringDialog(self, charge, self.categories, self._text)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            data = dialog.get_data()
            end_date = data["end_date"]
            if end_date and str(end_date) < str(data["start_date"]):
                self.recurring_status_label.setText(self._text("recurring_end_after"))
                return
            original = RecurringCharge(
                id=charge.id,
                label=charge.label,
                amount=charge.amount,
                type=charge.type,
                category=charge.category,
                notes=charge.notes,
                start_date=charge.start_date,
                end_date=charge.end_date,
                status=charge.status,
                frequency=charge.frequency,
                last_applied=charge.last_applied,
            )
            self.db.update_recurring_charge(
                charge.id,
                label=str(data["label"]),
                amount=float(data["amount"]),
                tx_type=str(data["type"]),
                category=str(data["category"]),
                notes=str(data["notes"]),
                start_date=str(data["start_date"]),
                end_date=end_date if end_date else None,
                status=str(data["status"]),
                frequency=str(data["frequency"]),
            )
            self._push_undo(
                self._text("undo_edit_recurring"),
                lambda original=original: self.db.update_recurring_charge(
                    original.id,
                    label=original.label,
                    amount=original.amount,
                    tx_type=original.type,
                    category=original.category,
                    notes=original.notes,
                    start_date=original.start_date,
                    end_date=original.end_date,
                    status=original.status,
                    frequency=original.frequency,
                ),
            )
            self.recurring_status_label.setText(self._text("recurring_updated"))
            self.reload_all()

    def handle_delete_recurring(self) -> None:
        charge = self._selected_recurring_charge()
        if not charge:
            self.recurring_status_label.setText(self._text("recurring_select_delete"))
            return
        self.db.delete_recurring_charge(charge.id)
        self._push_undo(
            self._text("undo_delete_recurring"),
            lambda charge=charge: self.db.insert_recurring_charge_with_id(charge),
        )
        self.recurring_status_label.setText(self._text("recurring_deleted"))
        self.reload_all()

    def handle_apply_recurring_now(self) -> None:
        charge = self._selected_recurring_charge()
        if not charge:
            self.recurring_status_label.setText(self._text("recurring_select_apply"))
            return
        applied = self.db.apply_recurring_charge_once(charge.id)
        if not applied:
            self.recurring_status_label.setText(self._text("recurring_nothing"))
        else:
            self.recurring_status_label.setText(self._text("recurring_applied"))
        self.reload_all()

    def handle_export_pdf(self) -> None:
        if not self.settings:
            return
        export_settings = self.settings
        pdf_lang = self._selected_pdf_language()
        if export_settings.language != pdf_lang:
            export_settings = replace(export_settings, language=pdf_lang)
        export_lang_map = UI_TEXT.get(pdf_lang, UI_TEXT["EN"])
        default_base = export_lang_map.get(
            "export_pdf_default", self._text("export_pdf_default")
        )
        default_name = f"{default_base}_{datetime.now().strftime('%Y%m%d')}.pdf"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self._text("export_pdf_title"),
            default_name,
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path = f"{path}.pdf"
        try:
            reports.export_pdf(
                path,
                export_settings,
                self.transactions,
                self.summary,
                self.monthly_stats,
            )
        except Exception as exc:  # pragma: no cover
            self.report_status.setText(
                self._text("export_failed").format(error=exc)
            )
            return
        self.report_status.setText(
            self._text("export_pdf_saved").format(path=path)
        )

    def handle_export_excel(self) -> None:
        if not self.settings:
            return
        export_settings = self.settings
        current_lang = self._current_language()
        if export_settings.language != current_lang:
            export_settings = replace(export_settings, language=current_lang)
        default_base = self._text("export_excel_default")
        default_name = f"{default_base}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self._text("export_excel_title"),
            default_name,
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path = f"{path}.xlsx"
        try:
            reports.export_excel(
                path,
                export_settings,
                self.transactions,
                self.summary,
                self.monthly_stats,
                self.recurring_charges,
                self.categories,
            )
        except Exception as exc:  # pragma: no cover
            self.report_status.setText(
                self._text("export_failed").format(error=exc)
            )
            return
        self.report_status.setText(
            self._text("export_excel_saved").format(path=path)
        )

    def handle_export_json(self) -> None:
        if not self.settings:
            return
        export_settings = self.settings
        current_lang = self._current_language()
        if export_settings.language != current_lang:
            export_settings = replace(export_settings, language=current_lang)
        default_base = self._text("export_json_default")
        default_name = f"{default_base}.json"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self._text("export_json_title"),
            default_name,
            "JSON Files (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path = f"{path}.json"
        try:
            reports.export_json(
                path,
                export_settings,
                self.transactions,
                self.recurring_charges,
                self.categories,
            )
        except Exception as exc:  # pragma: no cover
            self.report_status.setText(
                self._text("export_failed").format(error=exc)
            )
            return
        self.report_status.setText(
            self._text("export_json_saved").format(path=path)
        )

    def handle_apply_settings(self) -> None:
        if self.loading:
            return
        updates = self._collect_settings()
        self.db.update_settings(updates)
        self.reload_all()
        if hasattr(self, "settings_status_label"):
            self.settings_status_label.setText(self._text("settings_applied"))

    def handle_reconcile_balance(self) -> None:
        if self.loading or not self.settings:
            return
        if self.settings_dirty:
            self.reconcile_status.setText(self._text("reconcile_apply_first"))
            return
        actual = float(self.reconcile_balance_input.value())
        estimated = float(self.summary.get("estimated_balance", 0.0))
        delta = actual - estimated
        if abs(delta) < 0.005:
            self.reconcile_status.setText(self._text("reconcile_no_change"))
            return
        tx_type = "income" if delta > 0 else "expense"
        amount = abs(delta)
        tx_id = self.db.add_transaction(
            amount=amount,
            tx_type=tx_type,
            label="Reconcile adjustment",
            category="adjustment",
            notes="adjusted due to reconcile after counting",
            datetime_local=local_now_iso(),
        )
        self._push_undo(
            self._text("undo_reconcile"),
            lambda tx_id=tx_id: self.db.delete_transaction(tx_id),
        )
        self.reload_all()
        self.reconcile_status.setText(
            self._text("reconcile_posted").format(delta=f"{delta:+.2f}")
        )

    def handle_import_data(self) -> None:
        selected_files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            self._text("import_dialog_title"),
            str(Path.home() / "Downloads"),
            self._text("import_dialog_filter"),
        )
        if not selected_files:
            return

        json_path: Optional[Path] = None
        csv_path: Optional[Path] = None
        excel_path: Optional[Path] = None
        for raw_path in selected_files:
            path = Path(raw_path)
            suffix = path.suffix.lower()
            if suffix == ".json":
                if json_path is not None:
                    self.report_status.setText(self._text("import_multiple_same_type"))
                    return
                json_path = path
            elif suffix == ".csv":
                if csv_path is not None:
                    self.report_status.setText(self._text("import_multiple_same_type"))
                    return
                csv_path = path
            elif suffix in {".xlsx", ".xlsm"}:
                if excel_path is not None:
                    self.report_status.setText(self._text("import_multiple_same_type"))
                    return
                excel_path = path

        try:
            result = importer.import_from_files(
                self.db,
                json_path=json_path,
                csv_path=csv_path,
                excel_path=excel_path,
            )
        except Exception as exc:  # pragma: no cover
            self.report_status.setText(
                self._text("import_failed").format(error=exc)
            )
            return
        self.reload_all()
        self.undo_stack.clear()
        self._update_undo_ui()
        settings_text = (
            self._text("settings_updated")
            if result.settings_updated
            else self._text("settings_unchanged")
        )
        self.report_status.setText(
            self._text("import_result").format(
                added=result.added,
                skipped=result.skipped,
                settings_text=settings_text,
            )
            )
        if result.invalid_transactions or result.invalid_recurring:
            self.report_status.setText(
                f"{self.report_status.text()} | {self._text('import_partial_warning')}"
            )
        self.report_status.setToolTip("\n".join(result.messages))

    def handle_reset_data(self) -> None:
        reply = QtWidgets.QMessageBox.question(
            self,
            self._text("reset_data_title"),
            self._text("reset_data_confirm"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.db.reset_all_data()
        except Exception as exc:  # pragma: no cover
            self.report_status.setText(
                self._text("import_failed").format(error=exc)
            )
            return

        self.undo_stack.clear()
        self._update_undo_ui()
        self.reload_all()
        self.report_status.setText(self._text("reset_data_done"))
        self.report_status.setToolTip("")

    def _collect_settings(self) -> Dict[str, object]:
        updates: Dict[str, object] = {}
        for key, widget in self.setting_widgets.items():
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                updates[key] = float(widget.value())
            elif isinstance(widget, QtWidgets.QSpinBox):
                updates[key] = int(widget.value())
            elif isinstance(widget, QtWidgets.QComboBox):
                updates[key] = widget.currentText()
        if hasattr(self, "misc_mode_combo"):
            mode_data = self.misc_mode_combo.currentData()
            if mode_data is None:
                mode_data = self.misc_mode_combo.currentText().strip().lower()
            updates["auto_misc_enabled"] = mode_data == "auto"
        if hasattr(self, "auto_misc_category_list"):
            updates["auto_misc_categories"] = self._selected_auto_misc_categories()
        if hasattr(self, "auto_include_recurring_checkbox"):
            updates["auto_include_recurring"] = self.auto_include_recurring_checkbox.isChecked()
        if hasattr(self, "auto_include_current_month_checkbox"):
            updates["auto_include_current_month"] = (
                self.auto_include_current_month_checkbox.isChecked()
            )
        if hasattr(self, "auto_window_months_input"):
            updates["auto_window_months"] = int(self.auto_window_months_input.value())
        if hasattr(self, "auto_weighted_checkbox"):
            updates["auto_weighted"] = self.auto_weighted_checkbox.isChecked()
        if hasattr(self, "auto_weight_half_life_input"):
            updates["auto_weight_half_life_months"] = int(
                self.auto_weight_half_life_input.value()
            )
        if "auto_misc_categories" in updates:
            recurring_categories = self._recurring_expense_categories()
            updates["auto_misc_categories"] = [
                name
                for name in updates["auto_misc_categories"]
                if str(name).strip().lower() not in recurring_categories
            ]
        return updates


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationDisplayName(APP_TITLE)
    app.setOrganizationName(APP_ORGANIZATION)
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
