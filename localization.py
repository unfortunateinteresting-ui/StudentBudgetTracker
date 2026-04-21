from __future__ import annotations

from typing import Dict


CATEGORY_TEXT: Dict[str, Dict[str, str]] = {
    "rent": {"EN": "Rent", "FR": "Loyer"},
    "utilities": {"EN": "Utilities", "FR": "Services"},
    "food": {"EN": "Food", "FR": "Nourriture"},
    "transport": {"EN": "Transport", "FR": "Transport"},
    "internet": {"EN": "Internet", "FR": "Internet"},
    "phone": {"EN": "Phone", "FR": "Telephone"},
    "insurance": {"EN": "Insurance", "FR": "Assurance"},
    "medical": {"EN": "Medical", "FR": "Medical"},
    "school": {"EN": "School", "FR": "Ecole"},
    "household": {"EN": "Household", "FR": "Maison"},
    "health": {"EN": "Health", "FR": "Sante"},
    "subscriptions": {"EN": "Subscriptions", "FR": "Abonnements"},
    "entertainment": {"EN": "Entertainment", "FR": "Loisirs"},
    "travel": {"EN": "Travel", "FR": "Voyage"},
    "clothing": {"EN": "Clothing", "FR": "Vetements"},
    "gifts": {"EN": "Gifts", "FR": "Cadeaux"},
    "pets": {"EN": "Pets", "FR": "Animaux"},
    "debt": {"EN": "Debt", "FR": "Dettes"},
    "fees": {"EN": "Fees", "FR": "Frais"},
    "income": {"EN": "Income", "FR": "Revenu"},
    "adjustment": {"EN": "Adjustment", "FR": "Ajustement"},
    "misc": {"EN": "Misc", "FR": "Divers"},
}


def translated_category(value: str, language: str = "EN") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    labels = CATEGORY_TEXT.get(text.lower())
    if not labels:
        return text
    lang = (language or "EN").upper()
    return labels.get(lang, labels.get("EN", text))
