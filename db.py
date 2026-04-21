import os
import re
import shutil
import sqlite3
import sys
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

APP_NAME = "OfflineBudgetTracker"
DATA_DIR_ENV_VAR = "OFFLINE_BUDGET_TRACKER_DATA_DIR"
LEGACY_SOURCE_MIGRATION_ENV_VAR = "OFFLINE_BUDGET_TRACKER_MIGRATE_SOURCE_DATA"
TZ_NAME = datetime.now().astimezone().tzname() or "LOCAL"
DEFAULT_BACKUP_KEEP = 50
RECURRING_FREQUENCIES = {"monthly", "weekly", "daily"}
DEFAULT_CATEGORIES = [
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


@dataclass
class Transaction:
    id: str
    datetime_local: str
    amount: float
    type: str
    label: str
    category: str
    notes: str
    recurring_id: Optional[str] = None
    excluded_from_averages: bool = False


@dataclass
class Settings:
    starting_balance: float
    counted_balance: Optional[float]
    refunds_total: float
    plan_months_total: int
    months_elapsed: int
    rent_base_monthly: float
    rent_monthly_manual: float
    food_house_monthly: float
    misc_monthly: float
    medical_monthly: float
    school_monthly: float
    household_monthly: float
    health_monthly: float
    auto_misc_enabled: bool
    auto_misc_categories: List[str]
    auto_include_recurring: bool
    auto_include_current_month: bool
    auto_window_months: int
    auto_weighted: bool
    auto_weight_half_life_months: int
    extra_monthly: float
    rent_surcharge_amount: float
    rent_surcharge_months: int
    campus_reference_total: float
    language: str
    theme: str
    font_family: str
    accent_color: str


@dataclass
class RecurringCharge:
    id: str
    label: str
    amount: float
    type: str
    category: str
    notes: str
    start_date: str
    end_date: Optional[str]
    status: str
    frequency: str
    last_applied: Optional[str]


DEFAULT_SETTINGS = Settings(
    starting_balance=0.0,
    counted_balance=None,
    refunds_total=0.0,
    plan_months_total=9,
    months_elapsed=0,
    rent_base_monthly=650.0,
    rent_monthly_manual=0.0,
    food_house_monthly=200.0,
    misc_monthly=0.0,
    medical_monthly=0.0,
    school_monthly=0.0,
    household_monthly=0.0,
    health_monthly=0.0,
    auto_misc_enabled=False,
    auto_misc_categories=[],
    auto_include_recurring=False,
    auto_include_current_month=True,
    auto_window_months=3,
    auto_weighted=False,
    auto_weight_half_life_months=6,
    extra_monthly=0.0,
    rent_surcharge_amount=144.0,
    rent_surcharge_months=3,
    campus_reference_total=17256.0,
    language="EN",
    theme="Dune",
    font_family="",
    accent_color="",
)

SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    starting_balance REAL NOT NULL,
    counted_balance REAL,
    refunds_total REAL NOT NULL,
    plan_months_total INTEGER NOT NULL,
    months_elapsed INTEGER NOT NULL,
    rent_base_monthly REAL NOT NULL,
    rent_monthly_manual REAL NOT NULL DEFAULT 0,
    food_house_monthly REAL NOT NULL,
    misc_monthly REAL NOT NULL DEFAULT 0,
    medical_monthly REAL NOT NULL DEFAULT 0,
    school_monthly REAL NOT NULL DEFAULT 0,
    household_monthly REAL NOT NULL DEFAULT 0,
    health_monthly REAL NOT NULL DEFAULT 0,
    auto_misc_enabled INTEGER NOT NULL DEFAULT 0,
    auto_misc_categories TEXT NOT NULL DEFAULT '[]',
    auto_include_recurring INTEGER NOT NULL DEFAULT 0,
    auto_include_current_month INTEGER NOT NULL DEFAULT 1,
    auto_window_months INTEGER NOT NULL DEFAULT 0,
    auto_weighted INTEGER NOT NULL DEFAULT 0,
    auto_weight_half_life_months INTEGER NOT NULL DEFAULT 6,
    extra_monthly REAL NOT NULL DEFAULT 0,
    rent_surcharge_amount REAL NOT NULL,
    rent_surcharge_months INTEGER NOT NULL,
    campus_reference_total REAL NOT NULL,
    language TEXT NOT NULL CHECK(language IN ('EN','FR')),
    theme TEXT NOT NULL DEFAULT 'Dune',
    font_family TEXT NOT NULL DEFAULT '',
    accent_color TEXT NOT NULL DEFAULT ''
);
"""


def local_now_iso() -> str:
    now = datetime.now()
    return now.replace(tzinfo=None, microsecond=0).isoformat()


def local_today() -> date:
    return datetime.now().date()


def indiana_now_iso() -> str:
    # Backward-compatible alias; now uses system local time.
    return local_now_iso()


def _platform_data_root() -> Path:
    if os.name == "nt":
        return Path(os.getenv("APPDATA", Path.home()))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path.home() / ".local" / "share"


def _legacy_source_data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


def _legacy_source_migration_enabled() -> bool:
    # Legacy repo-local data migration is opt-in so copied source folders do not
    # silently seed a fresh install with stale budget.db content on another device.
    return _coerce_bool(os.getenv(LEGACY_SOURCE_MIGRATION_ENV_VAR), False)


def get_data_dir() -> Path:
    override = (os.getenv(DATA_DIR_ENV_VAR) or "").strip()
    if override:
        return Path(override).expanduser()
    return _platform_data_root() / APP_NAME


def get_db_path() -> Path:
    return get_data_dir() / "budget.db"


def get_backups_dir() -> Path:
    return get_data_dir() / "backups"


def _parse_json_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    cleaned = []
    for item in data:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _coerce_int(
    value: Any,
    default: int = 0,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    if value is None:
        result = default
    else:
        try:
            result = int(float(value))
        except (TypeError, ValueError):
            result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _coerce_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


class Database:
    def __init__(self) -> None:
        self.data_dir = get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_source_data()
        self.db_path = self.data_dir / "budget.db"
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        try:
            self._init_db()
        except sqlite3.DatabaseError:
            self._conn.close()
            self._recover_db_file()
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._init_db()

    def _migrate_legacy_source_data(self) -> None:
        if getattr(sys, "frozen", False):
            return
        if not _legacy_source_migration_enabled():
            return
        legacy_dir = _legacy_source_data_dir()
        try:
            if legacy_dir.resolve() == self.data_dir.resolve():
                return
        except OSError:
            return
        if not legacy_dir.exists():
            return

        legacy_db = legacy_dir / "budget.db"
        target_db = self.data_dir / "budget.db"
        if legacy_db.exists() and not target_db.exists():
            try:
                shutil.copy2(legacy_db, target_db)
            except OSError:
                pass

        legacy_backups_dir = legacy_dir / "backups"
        target_backups_dir = self.data_dir / "backups"
        if not legacy_backups_dir.exists():
            return
        try:
            target_backups_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        existing_names = {
            item.name for item in target_backups_dir.glob("budget_*.db")
        }
        for backup_path in sorted(legacy_backups_dir.glob("budget_*.db")):
            if backup_path.name in existing_names:
                continue
            try:
                shutil.copy2(backup_path, target_backups_dir / backup_path.name)
            except OSError:
                continue

    def _recover_db_file(self) -> None:
        backups_dir = get_backups_dir()
        backups_dir.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupt_copy = self.data_dir / f"budget_corrupt_{timestamp}.db"
            try:
                shutil.move(self.db_path, corrupt_copy)
            except Exception:
                try:
                    self.db_path.unlink(missing_ok=True)
                except Exception:
                    pass
        backup_candidates = sorted(
            backups_dir.glob("budget_*.db"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if backup_candidates:
            try:
                shutil.copy2(backup_candidates[0], self.db_path)
            except Exception:
                self.db_path.unlink(missing_ok=True)

    def _init_db(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                datetime_local TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('expense','income')),
                label TEXT,
                category TEXT,
                notes TEXT,
                recurring_id TEXT,
                excluded_from_averages INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        cur.execute(SETTINGS_TABLE_SQL)
        self._migrate_legacy_settings_singleton_schema()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY
            );
            """
        )
        cur.execute("SELECT COUNT(*) AS count FROM categories")
        if cur.fetchone()["count"] == 0:
            cur.executemany(
                "INSERT INTO categories (name) VALUES (?)",
                [(name,) for name in DEFAULT_CATEGORIES],
            )
        else:
            self.ensure_categories(DEFAULT_CATEGORIES, backup=False)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_charges (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('expense','income')),
                category TEXT,
                notes TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT NOT NULL CHECK(status IN ('manual','automatic','paused')),
                frequency TEXT NOT NULL DEFAULT 'monthly',
                last_applied TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_datetime_local
            ON transactions(datetime_local);
            """
        )
        self._ensure_column("transactions", "recurring_id", "TEXT")
        self._ensure_column(
            "transactions", "excluded_from_averages", "INTEGER NOT NULL DEFAULT 0"
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_category
            ON transactions(category);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_recurring_id
            ON transactions(recurring_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_type_datetime
            ON transactions(type, datetime_local);
            """
        )
        self._ensure_column(
            "settings", "misc_monthly", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "rent_monthly_manual", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "medical_monthly", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "school_monthly", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "household_monthly", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "health_monthly", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "auto_misc_enabled", "INTEGER NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "auto_misc_categories", "TEXT NOT NULL DEFAULT '[]'"
        )
        self._ensure_column(
            "settings", "auto_include_recurring", "INTEGER NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "auto_include_current_month", "INTEGER NOT NULL DEFAULT 1"
        )
        self._ensure_column(
            "settings", "auto_window_months", "INTEGER NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "auto_weighted", "INTEGER NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "auto_weight_half_life_months", "INTEGER NOT NULL DEFAULT 6"
        )
        self._ensure_column(
            "settings", "extra_monthly", "REAL NOT NULL DEFAULT 0"
        )
        self._ensure_column(
            "settings", "theme", "TEXT NOT NULL DEFAULT 'Dune'"
        )
        self._ensure_column(
            "settings", "font_family", "TEXT NOT NULL DEFAULT ''"
        )
        self._ensure_column(
            "settings", "accent_color", "TEXT NOT NULL DEFAULT ''"
        )
        self._ensure_column(
            "recurring_charges", "frequency", "TEXT NOT NULL DEFAULT 'monthly'"
        )
        cur.execute("SELECT COUNT(*) AS count FROM settings")
        if cur.fetchone()["count"] == 0:
            self._insert_settings_row(self._normalized_settings_payload())
        self._conn.commit()

    def _normalized_settings_payload(
        self, raw: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        raw = raw or {}
        language = _coerce_text(
            raw.get("language"), DEFAULT_SETTINGS.language
        ).upper()
        if language not in {"EN", "FR"}:
            language = DEFAULT_SETTINGS.language
        auto_misc_raw = raw.get(
            "auto_misc_categories", DEFAULT_SETTINGS.auto_misc_categories
        )
        if isinstance(auto_misc_raw, list):
            auto_misc_categories = [
                str(item).strip() for item in auto_misc_raw if str(item).strip()
            ]
        else:
            auto_misc_categories = _parse_json_list(auto_misc_raw)
        return {
            "starting_balance": _coerce_float(
                raw.get("starting_balance"), DEFAULT_SETTINGS.starting_balance
            ),
            "counted_balance": _coerce_optional_float(raw.get("counted_balance")),
            "refunds_total": _coerce_float(
                raw.get("refunds_total"), DEFAULT_SETTINGS.refunds_total
            ),
            "plan_months_total": _coerce_int(
                raw.get("plan_months_total"),
                DEFAULT_SETTINGS.plan_months_total,
                minimum=1,
                maximum=120,
            ),
            "months_elapsed": _coerce_int(
                raw.get("months_elapsed"),
                DEFAULT_SETTINGS.months_elapsed,
                minimum=0,
                maximum=240,
            ),
            "rent_base_monthly": _coerce_float(
                raw.get("rent_base_monthly"), DEFAULT_SETTINGS.rent_base_monthly
            ),
            "rent_monthly_manual": _coerce_float(
                raw.get("rent_monthly_manual"), DEFAULT_SETTINGS.rent_monthly_manual
            ),
            "food_house_monthly": _coerce_float(
                raw.get("food_house_monthly"), DEFAULT_SETTINGS.food_house_monthly
            ),
            "misc_monthly": _coerce_float(
                raw.get("misc_monthly"), DEFAULT_SETTINGS.misc_monthly
            ),
            "medical_monthly": _coerce_float(
                raw.get("medical_monthly"), DEFAULT_SETTINGS.medical_monthly
            ),
            "school_monthly": _coerce_float(
                raw.get("school_monthly"), DEFAULT_SETTINGS.school_monthly
            ),
            "household_monthly": _coerce_float(
                raw.get("household_monthly"), DEFAULT_SETTINGS.household_monthly
            ),
            "health_monthly": _coerce_float(
                raw.get("health_monthly"), DEFAULT_SETTINGS.health_monthly
            ),
            "auto_misc_enabled": _coerce_bool(
                raw.get("auto_misc_enabled"), DEFAULT_SETTINGS.auto_misc_enabled
            ),
            "auto_misc_categories": auto_misc_categories,
            "auto_include_recurring": _coerce_bool(
                raw.get("auto_include_recurring"),
                DEFAULT_SETTINGS.auto_include_recurring,
            ),
            "auto_include_current_month": _coerce_bool(
                raw.get("auto_include_current_month"),
                DEFAULT_SETTINGS.auto_include_current_month,
            ),
            "auto_window_months": _coerce_int(
                raw.get("auto_window_months"),
                DEFAULT_SETTINGS.auto_window_months,
                minimum=0,
                maximum=120,
            ),
            "auto_weighted": _coerce_bool(
                raw.get("auto_weighted"), DEFAULT_SETTINGS.auto_weighted
            ),
            "auto_weight_half_life_months": _coerce_int(
                raw.get("auto_weight_half_life_months"),
                DEFAULT_SETTINGS.auto_weight_half_life_months,
                minimum=1,
                maximum=120,
            ),
            "extra_monthly": _coerce_float(
                raw.get("extra_monthly"), DEFAULT_SETTINGS.extra_monthly
            ),
            "rent_surcharge_amount": _coerce_float(
                raw.get("rent_surcharge_amount"),
                DEFAULT_SETTINGS.rent_surcharge_amount,
            ),
            "rent_surcharge_months": _coerce_int(
                raw.get("rent_surcharge_months"),
                DEFAULT_SETTINGS.rent_surcharge_months,
                minimum=0,
                maximum=120,
            ),
            "campus_reference_total": _coerce_float(
                raw.get("campus_reference_total"),
                DEFAULT_SETTINGS.campus_reference_total,
            ),
            "language": language,
            "theme": _coerce_text(raw.get("theme"), DEFAULT_SETTINGS.theme),
            "font_family": _coerce_text(
                raw.get("font_family"), DEFAULT_SETTINGS.font_family
            ),
            "accent_color": _coerce_text(
                raw.get("accent_color"), DEFAULT_SETTINGS.accent_color
            ),
        }

    def _insert_settings_row(
        self, payload: Dict[str, Any], row_id: int = 1
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO settings (
                id,
                starting_balance,
                counted_balance,
                refunds_total,
                plan_months_total,
                months_elapsed,
                rent_base_monthly,
                rent_monthly_manual,
                food_house_monthly,
                misc_monthly,
                medical_monthly,
                school_monthly,
                household_monthly,
                health_monthly,
                auto_misc_enabled,
                auto_misc_categories,
                auto_include_recurring,
                auto_include_current_month,
                auto_window_months,
                auto_weighted,
                auto_weight_half_life_months,
                extra_monthly,
                rent_surcharge_amount,
                rent_surcharge_months,
                campus_reference_total,
                language,
                theme,
                font_family,
                accent_color
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                payload["starting_balance"],
                payload["counted_balance"],
                payload["refunds_total"],
                payload["plan_months_total"],
                payload["months_elapsed"],
                payload["rent_base_monthly"],
                payload["rent_monthly_manual"],
                payload["food_house_monthly"],
                payload["misc_monthly"],
                payload["medical_monthly"],
                payload["school_monthly"],
                payload["household_monthly"],
                payload["health_monthly"],
                int(bool(payload["auto_misc_enabled"])),
                json.dumps(payload["auto_misc_categories"]),
                int(bool(payload["auto_include_recurring"])),
                int(bool(payload["auto_include_current_month"])),
                payload["auto_window_months"],
                int(bool(payload["auto_weighted"])),
                payload["auto_weight_half_life_months"],
                payload["extra_monthly"],
                payload["rent_surcharge_amount"],
                payload["rent_surcharge_months"],
                payload["campus_reference_total"],
                payload["language"],
                payload["theme"],
                payload["font_family"],
                payload["accent_color"],
            ),
        )

    def _settings_payload_from_settings(self, settings: Settings) -> Dict[str, Any]:
        return self._normalized_settings_payload(asdict(settings))

    def _fetch_settings_row(self) -> Optional[sqlite3.Row]:
        cur = self._conn.cursor()
        queries = [
            ("SELECT * FROM settings WHERE id = ?", (1,)),
            ("SELECT * FROM settings WHERE CAST(id AS TEXT) = ?", ("singleton",)),
            ("SELECT * FROM settings ORDER BY rowid ASC LIMIT 1", ()),
        ]
        for query, params in queries:
            try:
                cur.execute(query, params)
            except sqlite3.DatabaseError:
                continue
            row = cur.fetchone()
            if row is not None:
                return row
        return None

    def _migrate_legacy_settings_singleton_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'settings'"
        )
        table_row = cur.fetchone()
        if table_row is None:
            return

        table_sql = str(table_row["sql"] or "")
        cur.execute("PRAGMA table_info(settings)")
        columns = cur.fetchall()
        id_row = next((row for row in columns if row["name"] == "id"), None)
        if id_row is None:
            return

        id_type = str(id_row["type"] or "").upper()
        needs_migration = "singleton" in table_sql.lower() or "INT" not in id_type
        if not needs_migration:
            try:
                cur.execute(
                    "SELECT 1 FROM settings WHERE CAST(id AS TEXT) = 'singleton' LIMIT 1"
                )
                needs_migration = cur.fetchone() is not None
            except sqlite3.DatabaseError:
                needs_migration = True
        if not needs_migration:
            return

        cur.execute("SELECT * FROM settings LIMIT 1")
        existing_row = cur.fetchone()
        existing_values = dict(existing_row) if existing_row is not None else {}
        payload = self._normalized_settings_payload(existing_values)
        temp_name = f"settings_legacy_{int(datetime.now().timestamp())}"
        self._conn.execute(f'ALTER TABLE settings RENAME TO "{temp_name}"')
        self._conn.execute(SETTINGS_TABLE_SQL)
        self._insert_settings_row(payload)
        self._conn.execute(f'DROP TABLE "{temp_name}"')
        self._conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        cur = self._conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        columns = {row["name"] for row in cur.fetchall()}
        if column in columns:
            return
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _normalize_frequency(self, frequency: Optional[str]) -> str:
        value = (frequency or "monthly").strip().lower()
        if value not in RECURRING_FREQUENCIES:
            return "monthly"
        return value

    def _normalize_category(self, name: Optional[str]) -> Optional[str]:
        if name is None:
            return None
        value = str(name).strip()
        if not value:
            return None
        return value

    def list_categories(self) -> List[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT name FROM categories ORDER BY name ASC")
        return [row["name"] for row in cur.fetchall()]

    def ensure_categories(
        self, names: List[str], backup: bool = True
    ) -> int:
        cleaned = []
        for name in names:
            normalized = self._normalize_category(name)
            if normalized:
                cleaned.append(normalized)
        if not cleaned:
            return 0
        cur = self._conn.cursor()
        cur.execute("SELECT name FROM categories")
        existing = {row["name"].lower() for row in cur.fetchall()}
        to_add = []
        for name in cleaned:
            lowered = name.lower()
            if lowered in existing:
                continue
            existing.add(lowered)
            to_add.append((name,))
        if not to_add:
            return 0
        cur.executemany("INSERT INTO categories (name) VALUES (?)", to_add)
        self._conn.commit()
        if backup:
            self._backup_db()
        return len(to_add)

    def close(self) -> None:
        self._conn.close()

    def list_transactions(self) -> List[Transaction]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM transactions ORDER BY datetime_local ASC")
        rows = cur.fetchall()
        normalized: List[Transaction] = []
        for row in rows:
            tx_type = _coerce_text(row["type"], "expense").lower()
            if tx_type not in {"expense", "income"}:
                tx_type = "expense"
            dt_value = _coerce_text(row["datetime_local"], local_now_iso())
            normalized.append(
                Transaction(
                    id=_coerce_text(row["id"], str(uuid4())),
                    datetime_local=dt_value,
                    amount=_coerce_float(row["amount"], 0.0),
                    type=tx_type,
                    label=_coerce_text(row["label"], ""),
                    category=_coerce_text(row["category"], ""),
                    notes=_coerce_text(row["notes"], ""),
                    recurring_id=_coerce_text(row["recurring_id"], "")
                    or None,
                    excluded_from_averages=_coerce_bool(
                        row["excluded_from_averages"], False
                    ),
                )
            )
        return normalized

    def add_transaction(
        self,
        amount: float,
        tx_type: str,
        label: str,
        category: str,
        notes: str,
        datetime_local: Optional[str] = None,
        recurring_id: Optional[str] = None,
        excluded_from_averages: bool = False,
    ) -> str:
        tx_id = str(uuid4())
        dt_value = datetime_local or local_now_iso()
        self.ensure_categories([category], backup=False)
        self._conn.execute(
            """
            INSERT INTO transactions (
                id, datetime_local, amount, type, label, category, notes, recurring_id, excluded_from_averages
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                dt_value,
                amount,
                tx_type,
                label,
                category,
                notes,
                recurring_id,
                int(bool(excluded_from_averages)),
            ),
        )
        self._conn.commit()
        self._backup_db()
        return tx_id

    def insert_transaction_with_id(
        self, tx: Transaction, backup: bool = True
    ) -> None:
        self.ensure_categories([tx.category], backup=False)
        self._conn.execute(
            """
            INSERT INTO transactions (
                id, datetime_local, amount, type, label, category, notes, recurring_id, excluded_from_averages
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx.id,
                tx.datetime_local,
                tx.amount,
                tx.type,
                tx.label,
                tx.category,
                tx.notes,
                tx.recurring_id,
                int(bool(tx.excluded_from_averages)),
            ),
        )
        self._conn.commit()
        if backup:
            self._backup_db()

    def update_transaction(
        self,
        tx_id: str,
        amount: float,
        tx_type: str,
        label: str,
        category: str,
        notes: str,
        datetime_local: str,
        excluded_from_averages: bool = False,
    ) -> None:
        self.ensure_categories([category], backup=False)
        self._conn.execute(
            """
            UPDATE transactions
            SET datetime_local = ?, amount = ?, type = ?, label = ?, category = ?, notes = ?, excluded_from_averages = ?
            WHERE id = ?
            """,
            (
                datetime_local,
                amount,
                tx_type,
                label,
                category,
                notes,
                int(bool(excluded_from_averages)),
                tx_id,
            ),
        )
        self._conn.commit()
        self._backup_db()

    def delete_transaction(self, tx_id: str) -> None:
        self._conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        self._conn.commit()
        self._backup_db()

    def reset_all_data(self, backup: bool = True) -> None:
        preserved = self.get_settings()
        self._migrate_legacy_settings_singleton_schema()
        reset_settings = self._normalized_settings_payload({
            "starting_balance": DEFAULT_SETTINGS.starting_balance,
            "counted_balance": DEFAULT_SETTINGS.counted_balance,
            "refunds_total": DEFAULT_SETTINGS.refunds_total,
            "plan_months_total": DEFAULT_SETTINGS.plan_months_total,
            "months_elapsed": DEFAULT_SETTINGS.months_elapsed,
            "rent_base_monthly": DEFAULT_SETTINGS.rent_base_monthly,
            "rent_monthly_manual": DEFAULT_SETTINGS.rent_monthly_manual,
            "food_house_monthly": DEFAULT_SETTINGS.food_house_monthly,
            "misc_monthly": DEFAULT_SETTINGS.misc_monthly,
            "medical_monthly": DEFAULT_SETTINGS.medical_monthly,
            "school_monthly": DEFAULT_SETTINGS.school_monthly,
            "household_monthly": DEFAULT_SETTINGS.household_monthly,
            "health_monthly": DEFAULT_SETTINGS.health_monthly,
            "auto_misc_enabled": DEFAULT_SETTINGS.auto_misc_enabled,
            "auto_misc_categories": list(DEFAULT_SETTINGS.auto_misc_categories),
            "auto_include_recurring": DEFAULT_SETTINGS.auto_include_recurring,
            "auto_include_current_month": DEFAULT_SETTINGS.auto_include_current_month,
            "auto_window_months": DEFAULT_SETTINGS.auto_window_months,
            "auto_weighted": DEFAULT_SETTINGS.auto_weighted,
            "auto_weight_half_life_months": DEFAULT_SETTINGS.auto_weight_half_life_months,
            "extra_monthly": DEFAULT_SETTINGS.extra_monthly,
            "rent_surcharge_amount": DEFAULT_SETTINGS.rent_surcharge_amount,
            "rent_surcharge_months": DEFAULT_SETTINGS.rent_surcharge_months,
            "campus_reference_total": DEFAULT_SETTINGS.campus_reference_total,
            # Preserve UI choices so the app does not unexpectedly flip themes/language.
            "language": preserved.language,
            "theme": preserved.theme,
            "font_family": preserved.font_family,
            "accent_color": preserved.accent_color,
        })

        if backup:
            self._backup_db()

        self._conn.execute("DELETE FROM transactions")
        self._conn.execute("DELETE FROM recurring_charges")
        self._conn.execute("DELETE FROM categories")
        self._conn.execute("DELETE FROM settings")
        self._insert_settings_row(reset_settings)
        self._conn.executemany(
            "INSERT INTO categories (name) VALUES (?)",
            [(name,) for name in DEFAULT_CATEGORIES],
        )
        self._conn.commit()

    def get_settings(self) -> Settings:
        row = self._fetch_settings_row()
        if row is None:
            return DEFAULT_SETTINGS
        language = _coerce_text(row["language"], "EN").upper()
        if language not in {"EN", "FR"}:
            language = "EN"
        return Settings(
            starting_balance=_coerce_float(row["starting_balance"], 0.0),
            counted_balance=_coerce_optional_float(row["counted_balance"]),
            refunds_total=_coerce_float(row["refunds_total"], 0.0),
            plan_months_total=_coerce_int(row["plan_months_total"], 9, minimum=1, maximum=120),
            months_elapsed=_coerce_int(row["months_elapsed"], 0, minimum=0, maximum=120),
            rent_base_monthly=_coerce_float(row["rent_base_monthly"], 650.0),
            rent_monthly_manual=_coerce_float(row["rent_monthly_manual"], 0.0),
            food_house_monthly=_coerce_float(row["food_house_monthly"], 200.0),
            misc_monthly=_coerce_float(row["misc_monthly"], 0.0),
            medical_monthly=_coerce_float(row["medical_monthly"], 0.0),
            school_monthly=_coerce_float(row["school_monthly"], 0.0),
            household_monthly=_coerce_float(row["household_monthly"], 0.0),
            health_monthly=_coerce_float(row["health_monthly"], 0.0),
            auto_misc_enabled=_coerce_bool(row["auto_misc_enabled"], False),
            auto_misc_categories=_parse_json_list(row["auto_misc_categories"]),
            auto_include_recurring=_coerce_bool(row["auto_include_recurring"], False),
            auto_include_current_month=_coerce_bool(row["auto_include_current_month"], True),
            auto_window_months=_coerce_int(row["auto_window_months"], 3, minimum=0, maximum=120),
            auto_weighted=_coerce_bool(row["auto_weighted"], False),
            auto_weight_half_life_months=_coerce_int(
                row["auto_weight_half_life_months"], 6, minimum=1, maximum=120
            ),
            extra_monthly=_coerce_float(row["extra_monthly"], 0.0),
            rent_surcharge_amount=_coerce_float(row["rent_surcharge_amount"], 144.0),
            rent_surcharge_months=_coerce_int(row["rent_surcharge_months"], 3, minimum=0, maximum=120),
            campus_reference_total=_coerce_float(row["campus_reference_total"], 17256.0),
            language=language,
            theme=_coerce_text(row["theme"], "Dune"),
            font_family=_coerce_text(row["font_family"], ""),
            accent_color=_coerce_text(row["accent_color"], ""),
        )

    def update_settings(self, updates: Dict[str, Any], backup: bool = True) -> None:
        if not updates:
            return
        self._migrate_legacy_settings_singleton_schema()
        allowed = {
            "starting_balance",
            "counted_balance",
            "refunds_total",
            "plan_months_total",
            "months_elapsed",
            "rent_base_monthly",
            "rent_monthly_manual",
            "food_house_monthly",
            "misc_monthly",
            "medical_monthly",
            "school_monthly",
            "household_monthly",
            "health_monthly",
            "auto_misc_enabled",
            "auto_misc_categories",
            "auto_include_recurring",
            "auto_include_current_month",
            "auto_window_months",
            "auto_weighted",
            "auto_weight_half_life_months",
            "extra_monthly",
            "rent_surcharge_amount",
            "rent_surcharge_months",
            "campus_reference_total",
            "language",
            "theme",
            "font_family",
            "accent_color",
        }
        normalized_updates: Dict[str, Any] = {}
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "auto_misc_enabled":
                normalized_updates[key] = 1 if _coerce_bool(value) else 0
            elif key == "auto_include_recurring":
                normalized_updates[key] = 1 if _coerce_bool(value) else 0
            elif key == "auto_include_current_month":
                normalized_updates[key] = 1 if _coerce_bool(value) else 0
            elif key == "auto_weighted":
                normalized_updates[key] = 1 if _coerce_bool(value) else 0
            elif key == "auto_misc_categories":
                if isinstance(value, list):
                    normalized_updates[key] = json.dumps(value)
                else:
                    normalized_updates[key] = json.dumps(_parse_json_list(str(value)))
            elif key == "counted_balance":
                normalized_updates[key] = _coerce_optional_float(value)
            elif key in {
                "starting_balance",
                "refunds_total",
                "rent_base_monthly",
                "rent_monthly_manual",
                "food_house_monthly",
                "misc_monthly",
                "medical_monthly",
                "school_monthly",
                "household_monthly",
                "health_monthly",
                "extra_monthly",
                "rent_surcharge_amount",
                "campus_reference_total",
            }:
                normalized_updates[key] = _coerce_float(value, 0.0)
            elif key in {
                "plan_months_total",
                "months_elapsed",
                "auto_window_months",
                "auto_weight_half_life_months",
                "rent_surcharge_months",
            }:
                default_values = {
                    "plan_months_total": 9,
                    "months_elapsed": 0,
                    "auto_window_months": 3,
                    "auto_weight_half_life_months": 6,
                    "rent_surcharge_months": 3,
                }
                minimum = 1 if key in {"plan_months_total", "auto_weight_half_life_months"} else 0
                maximum = 120 if key != "months_elapsed" else 240
                normalized_updates[key] = _coerce_int(
                    value,
                    default=default_values.get(key, minimum),
                    minimum=minimum,
                    maximum=maximum,
                )
            elif key == "language":
                text = _coerce_text(value, "EN").upper()
                normalized_updates[key] = text if text in {"EN", "FR"} else "EN"
            elif key in {"theme", "font_family", "accent_color"}:
                normalized_updates[key] = _coerce_text(value, "")
            else:
                normalized_updates[key] = value
        fields = list(normalized_updates.keys())
        if not fields:
            return
        payload = self._settings_payload_from_settings(self.get_settings())
        payload.update(normalized_updates)
        payload = self._normalized_settings_payload(payload)
        assignments = ", ".join(f"{field} = ?" for field in fields)
        values = [normalized_updates[field] for field in fields]
        values.extend([1, "singleton"])
        cursor = self._conn.execute(
            f"UPDATE settings SET {assignments} WHERE id = ? OR CAST(id AS TEXT) = ?",
            values,
        )
        if cursor.rowcount == 0:
            self._conn.execute("DELETE FROM settings")
            self._insert_settings_row(payload)
        self._conn.commit()
        if backup:
            self._backup_db()

    def list_recurring_charges(self) -> List[RecurringCharge]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM recurring_charges ORDER BY label ASC")
        rows = cur.fetchall()
        normalized: List[RecurringCharge] = []
        for row in rows:
            tx_type = _coerce_text(row["type"], "expense").lower()
            if tx_type not in {"expense", "income"}:
                tx_type = "expense"
            status = _coerce_text(row["status"], "automatic").lower()
            if status not in {"manual", "automatic", "paused"}:
                status = "automatic"
            start_date = _coerce_text(
                row["start_date"], local_today().strftime("%Y-%m-%d")
            )
            normalized.append(
                RecurringCharge(
                    id=_coerce_text(row["id"], str(uuid4())),
                    label=_coerce_text(row["label"], "Recurring"),
                    amount=_coerce_float(row["amount"], 0.0),
                    type=tx_type,
                    category=_coerce_text(row["category"], ""),
                    notes=_coerce_text(row["notes"], ""),
                    start_date=start_date,
                    end_date=_coerce_text(row["end_date"], "") or None,
                    status=status,
                    frequency=self._normalize_frequency(_coerce_text(row["frequency"], "monthly")),
                    last_applied=_coerce_text(row["last_applied"], "") or None,
                )
            )
        return normalized

    def add_recurring_charge(
        self,
        label: str,
        amount: float,
        tx_type: str,
        category: str,
        notes: str,
        start_date: str,
        end_date: Optional[str],
        status: str,
        frequency: str,
    ) -> str:
        normalized_frequency = self._normalize_frequency(frequency)
        charge_id = str(uuid4())
        self.ensure_categories([category], backup=False)
        self._conn.execute(
            """
            INSERT INTO recurring_charges (
                id, label, amount, type, category, notes, start_date, end_date, status, frequency, last_applied
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                charge_id,
                label,
                amount,
                tx_type,
                category,
                notes,
                start_date,
                end_date,
                status,
                normalized_frequency,
                None,
            ),
        )
        self._conn.commit()
        self._backup_db()
        return charge_id

    def insert_recurring_charge_with_id(
        self, charge: RecurringCharge, backup: bool = True
    ) -> None:
        normalized_frequency = self._normalize_frequency(charge.frequency)
        self.ensure_categories([charge.category], backup=False)
        self._conn.execute(
            """
            INSERT INTO recurring_charges (
                id, label, amount, type, category, notes, start_date, end_date, status, frequency, last_applied
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                charge.id,
                charge.label,
                charge.amount,
                charge.type,
                charge.category,
                charge.notes,
                charge.start_date,
                charge.end_date,
                charge.status,
                normalized_frequency,
                charge.last_applied,
            ),
        )
        self._conn.commit()
        if backup:
            self._backup_db()

    def update_recurring_charge(
        self,
        charge_id: str,
        label: str,
        amount: float,
        tx_type: str,
        category: str,
        notes: str,
        start_date: str,
        end_date: Optional[str],
        status: str,
        frequency: str,
    ) -> None:
        normalized_frequency = self._normalize_frequency(frequency)
        self.ensure_categories([category], backup=False)
        self._conn.execute(
            """
            UPDATE recurring_charges
            SET label = ?, amount = ?, type = ?, category = ?, notes = ?, start_date = ?, end_date = ?, status = ?, frequency = ?
            WHERE id = ?
            """,
            (
                label,
                amount,
                tx_type,
                category,
                notes,
                start_date,
                end_date,
                status,
                normalized_frequency,
                charge_id,
            ),
        )
        self._conn.commit()
        self._backup_db()

    def delete_recurring_charge(self, charge_id: str) -> None:
        self._conn.execute("DELETE FROM recurring_charges WHERE id = ?", (charge_id,))
        self._conn.commit()
        self._backup_db()

    def preview_recurring_charges(
        self,
        today: Optional[date] = None,
        apply_until: Optional[date] = None,
        apply_from: Optional[date] = None,
    ) -> List[tuple]:
        if today is None:
            today = self._indiana_today()
        if apply_until is None:
            apply_until = today
        preview: List[tuple] = []
        for charge in self.list_recurring_charges():
            if charge.status != "automatic":
                continue
            due_dates = self._collect_due_dates(
                charge=charge,
                apply_until=apply_until,
                apply_from=apply_from,
                manual_once=False,
            )
            if due_dates:
                preview.append((charge, due_dates))
        return preview

    def apply_recurring_charges(
        self,
        today: Optional[date] = None,
        apply_until: Optional[date] = None,
        apply_from: Optional[date] = None,
    ) -> int:
        if today is None:
            today = self._indiana_today()
        if apply_until is None:
            apply_until = today
        charges = self.list_recurring_charges()
        total_added = 0
        for charge in charges:
            added = self._apply_recurring_charge(
                charge, today, apply_until, apply_from=apply_from
            )
            total_added += added
        if total_added:
            self._backup_db()
        return total_added

    def apply_recurring_charge_once(
        self, charge_id: str, today: Optional[date] = None
    ) -> bool:
        if today is None:
            today = self._indiana_today()
        charge = self._get_recurring_charge(charge_id)
        if charge is None:
            return False
        if charge.status == "paused":
            return False
        added = self._apply_recurring_charge(
            charge, today, today, manual_once=True
        )
        if added:
            self._backup_db()
        return added > 0

    def _apply_recurring_charge(
        self,
        charge: RecurringCharge,
        today: date,
        apply_until: date,
        apply_from: Optional[date] = None,
        manual_once: bool = False,
    ) -> int:
        if charge.status == "paused":
            return 0
        if charge.status != "automatic" and not manual_once:
            return 0

        start_date = self._parse_date(charge.start_date)
        end_date = self._parse_date(charge.end_date) if charge.end_date else None
        if end_date and end_date < start_date:
            if today >= end_date and charge.status != "paused":
                self._set_recurring_status(charge.id, "paused")
            return 0

        effective_until = min(apply_until, end_date) if end_date else apply_until
        if effective_until < start_date:
            if end_date and today >= end_date and charge.status != "paused":
                self._set_recurring_status(charge.id, "paused")
            return 0

        due_dates = self._collect_due_dates(
            charge=charge,
            apply_until=effective_until,
            apply_from=apply_from,
            manual_once=manual_once,
        )

        for scheduled_date in due_dates:
            self._insert_recurring_transaction(charge, scheduled_date)

        if due_dates:
            self._set_last_applied(charge.id, due_dates[-1].isoformat())

        if end_date and today >= end_date and charge.status != "paused":
            self._set_recurring_status(charge.id, "paused")

        return len(due_dates)

    def _collect_due_dates(
        self,
        charge: RecurringCharge,
        apply_until: date,
        apply_from: Optional[date],
        manual_once: bool,
    ) -> List[date]:
        start_date = self._parse_date(charge.start_date)
        end_date = self._parse_date(charge.end_date) if charge.end_date else None
        if end_date and apply_until > end_date:
            apply_until = end_date
        if apply_until < start_date:
            return []

        existing_dates = self._existing_recurring_dates(charge.id)
        anchor_date = self._anchor_date(
            charge=charge,
            start_date=start_date,
            apply_until=apply_until,
            existing_dates=existing_dates,
        )

        schedule_start = start_date
        if apply_from and apply_from > schedule_start:
            schedule_start = apply_from
        if anchor_date and anchor_date > schedule_start:
            schedule_start = anchor_date

        scheduled_dates = self._scheduled_dates(
            start_date=start_date,
            end_date=apply_until,
            frequency=charge.frequency,
            start_from=schedule_start,
        )

        due_dates: List[date] = []
        for scheduled in scheduled_dates:
            if apply_from and scheduled < apply_from:
                continue
            if anchor_date and scheduled <= anchor_date:
                continue
            if scheduled in existing_dates:
                continue
            due_dates.append(scheduled)

        if manual_once:
            return [due_dates[-1]] if due_dates else []
        return due_dates

    def _anchor_date(
        self,
        charge: RecurringCharge,
        start_date: date,
        apply_until: date,
        existing_dates: set,
    ) -> Optional[date]:
        last_applied = self._parse_last_applied(
            charge.last_applied, start_date, charge.frequency
        )
        if last_applied and last_applied > apply_until:
            last_applied = None
        existing_before = [item for item in existing_dates if item <= apply_until]
        max_existing = max(existing_before) if existing_before else None
        candidates = [value for value in (last_applied, max_existing) if value]
        return max(candidates) if candidates else None

    def _existing_recurring_dates(self, recurring_id: str) -> set:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT datetime_local FROM transactions WHERE recurring_id = ?",
            (recurring_id,),
        )
        dates = set()
        for row in cur.fetchall():
            dt = row["datetime_local"]
            if not dt:
                continue
            try:
                parsed = datetime.fromisoformat(dt)
            except (TypeError, ValueError):
                continue
            dates.add(parsed.date())
        return dates

    def _insert_recurring_transaction(self, charge: RecurringCharge, scheduled_date: date) -> None:
        dt_value = datetime(
            scheduled_date.year, scheduled_date.month, scheduled_date.day, 12, 0, 0
        ).isoformat()
        self._conn.execute(
            """
            INSERT INTO transactions (
                id, datetime_local, amount, type, label, category, notes, recurring_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                dt_value,
                charge.amount,
                charge.type,
                charge.label,
                charge.category,
                charge.notes,
                charge.id,
            ),
        )
        self._conn.commit()

    def _set_recurring_status(self, charge_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE recurring_charges SET status = ? WHERE id = ?",
            (status, charge_id),
        )
        self._conn.commit()

    def _set_last_applied(self, charge_id: str, date_value: str) -> None:
        self._conn.execute(
            "UPDATE recurring_charges SET last_applied = ? WHERE id = ?",
            (date_value, charge_id),
        )
        self._conn.commit()

    def _get_recurring_charge(self, charge_id: str) -> Optional[RecurringCharge]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM recurring_charges WHERE id = ?", (charge_id,))
        row = cur.fetchone()
        if not row:
            return None
        tx_type = _coerce_text(row["type"], "expense").lower()
        if tx_type not in {"expense", "income"}:
            tx_type = "expense"
        status = _coerce_text(row["status"], "automatic").lower()
        if status not in {"manual", "automatic", "paused"}:
            status = "automatic"
        return RecurringCharge(
            id=_coerce_text(row["id"], str(uuid4())),
            label=_coerce_text(row["label"], "Recurring"),
            amount=_coerce_float(row["amount"], 0.0),
            type=tx_type,
            category=_coerce_text(row["category"], ""),
            notes=_coerce_text(row["notes"], ""),
            start_date=_coerce_text(
                row["start_date"], local_today().strftime("%Y-%m-%d")
            ),
            end_date=_coerce_text(row["end_date"], "") or None,
            status=status,
            frequency=self._normalize_frequency(_coerce_text(row["frequency"], "monthly")),
            last_applied=_coerce_text(row["last_applied"], "") or None,
        )

    def _parse_last_applied(
        self, value: Optional[str], start_date: date, frequency: str
    ) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except (TypeError, ValueError):
            pass
        if re.match(r"^\d{4}-\d{2}$", value or ""):
            try:
                year, month = map(int, value.split("-"))
            except ValueError:
                return None
            return self._scheduled_monthly_date(start_date, year, month)
        return None

    def _scheduled_dates(
        self,
        start_date: date,
        end_date: date,
        frequency: str,
        start_from: Optional[date] = None,
    ) -> List[date]:
        normalized = self._normalize_frequency(frequency)
        if normalized == "daily":
            return self._every_days_schedule(start_date, end_date, 1, start_from)
        if normalized == "weekly":
            return self._every_days_schedule(start_date, end_date, 7, start_from)
        return self._monthly_schedule_dates(start_date, end_date, start_from)

    def _monthly_schedule_dates(
        self, start_date: date, end_date: date, start_from: Optional[date]
    ) -> List[date]:
        dates: List[date] = []
        year, month = start_date.year, start_date.month
        if start_from and start_from > start_date:
            year, month = start_from.year, start_from.month
        end_year, end_month = end_date.year, end_date.month
        while (year, month) <= (end_year, end_month):
            scheduled = self._scheduled_monthly_date(start_date, year, month)
            if start_date <= scheduled <= end_date:
                dates.append(scheduled)
            year, month = self._add_months(year, month, 1)
        return dates

    def _every_days_schedule(
        self,
        start_date: date,
        end_date: date,
        step_days: int,
        start_from: Optional[date],
    ) -> List[date]:
        dates: List[date] = []
        current = start_date
        if start_from and start_from > start_date:
            delta_days = (start_from - start_date).days
            offset = delta_days % step_days
            current = (
                start_from
                if offset == 0
                else start_from + timedelta(days=step_days - offset)
            )
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=step_days)
        return dates

    def _scheduled_monthly_date(self, start_date: date, year: int, month: int) -> date:
        last_day = self._last_day_of_month(year, month)
        day = min(start_date.day, last_day.day)
        return date(year, month, day)

    def _parse_date(self, value: str) -> date:
        if not value:
            return self._local_today()
        try:
            return datetime.fromisoformat(value).date()
        except (TypeError, ValueError):
            return self._local_today()

    def _last_day_of_month(self, year: int, month: int) -> date:
        if month == 12:
            return date(year, 12, 31)
        return date(year, month + 1, 1) - timedelta(days=1)

    def _add_months(self, year: int, month: int, increment: int) -> tuple:
        total_months = month - 1 + increment
        new_year = year + total_months // 12
        new_month = total_months % 12 + 1
        return new_year, new_month

    def _local_today(self) -> date:
        return datetime.now().date()

    def _indiana_today(self) -> date:
        # Backward-compatible alias; now uses system local date.
        return self._local_today()

    def indiana_today(self) -> date:
        return self._local_today()

    def add_transactions_bulk(
        self,
        transactions: List[Dict[str, Any]],
        backup: bool = True,
        preserve_ids: bool = False,
    ) -> int:
        if not transactions:
            return 0
        self.ensure_categories(
            [str(tx.get("category", "")) for tx in transactions],
            backup=False,
        )
        values = []
        for tx in transactions:
            tx_id = (
                _coerce_text(tx.get("id"), str(uuid4()))
                if preserve_ids
                else str(uuid4())
            )
            recurring_id = _coerce_text(tx.get("recurring_id"), "") or None
            values.append(
                (
                    tx_id,
                    tx["datetime_local"],
                    tx["amount"],
                    tx["type"],
                    tx.get("label", ""),
                    tx.get("category", ""),
                    tx.get("notes", ""),
                    recurring_id,
                    int(bool(tx.get("excluded_from_averages", False))),
                )
            )
        self._conn.executemany(
            """
            INSERT INTO transactions (
                id, datetime_local, amount, type, label, category, notes, recurring_id, excluded_from_averages
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        self._conn.commit()
        if backup:
            self._backup_db()
        return len(values)

    def backup_now(self) -> None:
        self._backup_db()

    def _backup_db(self) -> None:
        backups_dir = get_backups_dir()
        backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backups_dir / f"budget_{stamp}.db"
        shutil.copy2(self.db_path, backup_path)
        backups = sorted(backups_dir.glob("budget_*.db"))
        if len(backups) > DEFAULT_BACKUP_KEEP:
            for old in backups[: len(backups) - DEFAULT_BACKUP_KEEP]:
                try:
                    old.unlink()
                except OSError:
                    pass
