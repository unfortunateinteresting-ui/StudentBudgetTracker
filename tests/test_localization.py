from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from Offline_budget_tracker.localization import translated_category


def test_translated_category_switches_between_english_and_french():
    assert translated_category("rent", "EN") == "Rent"
    assert translated_category("rent", "FR") == "Loyer"
    assert translated_category("food", "EN") == "Food"
    assert translated_category("food", "FR") == "Nourriture"


def test_translated_category_preserves_custom_categories():
    assert translated_category("custom category", "EN") == "custom category"
    assert translated_category("custom category", "FR") == "custom category"
