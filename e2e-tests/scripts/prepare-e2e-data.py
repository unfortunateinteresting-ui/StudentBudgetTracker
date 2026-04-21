from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path


CURRENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
  singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
  school_year_start_month INTEGER NOT NULL DEFAULT 9,
  school_year_months INTEGER NOT NULL DEFAULT 9,
  language TEXT NOT NULL DEFAULT 'EN',
  backup_retention INTEGER NOT NULL DEFAULT 50,
  last_migration_version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  opening_balance REAL NOT NULL DEFAULT 0,
  archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  entry_kind TEXT NOT NULL,
  amount REAL NOT NULL,
  occurred_at_local TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  recurring_rule_id TEXT,
  transfer_group_id TEXT,
  exclude_from_insights INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_rules (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  entry_kind TEXT NOT NULL,
  amount REAL NOT NULL,
  account_id TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  start_date TEXT NOT NULL,
  end_date TEXT,
  frequency TEXT NOT NULL,
  status TEXT NOT NULL,
  last_applied_local TEXT
);

CREATE TABLE IF NOT EXISTS monthly_caps (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  amount REAL NOT NULL,
  month_key TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def previous_month_start(today: date) -> date:
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def ensure_clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def init_current_db(path: Path) -> sqlite3.Connection:
    ensure_clean_dir(path.parent)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(CURRENT_SCHEMA_SQL)
    conn.execute(
        """
        INSERT INTO app_settings (
          singleton_id,
          school_year_start_month,
          school_year_months,
          language,
          backup_retention,
          last_migration_version
        ) VALUES (1, 9, 9, 'EN', 50, 2)
        """
    )
    conn.commit()
    return conn


def seed_legacy_fixture(repo_root: Path, legacy_dir: Path) -> None:
    ensure_clean_dir(legacy_dir)
    legacy_db = legacy_dir / "budget.db"
    if legacy_db.exists():
        legacy_db.unlink()
    conn = sqlite3.connect(legacy_db)
    fixture_sql = (repo_root / "src-tauri" / "tests" / "fixtures" / "legacy_budget_fixture.sql").read_text(
        encoding="utf-8"
    )
    conn.executescript(fixture_sql)
    conn.commit()
    conn.close()


def seed_missed_recurring(data_dir: Path) -> None:
    conn = init_current_db(data_dir / "budget.db")
    created_at = now_iso()
    account_id = "account-catchup"
    start_date = previous_month_start(date.today()).strftime("%Y-%m-%d")
    conn.execute(
        """
        INSERT INTO accounts (id, name, type, opening_balance, archived, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (account_id, "Catch-up Checking", "checking", 600.0, 0, created_at),
    )
    conn.execute(
        """
        INSERT INTO recurring_rules (
          id, label, entry_kind, amount, account_id, category, notes, start_date, end_date,
          frequency, status, last_applied_local
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "rule-catchup",
            "Catch-up Utilities",
            "expense",
            55.0,
            account_id,
            "utilities",
            "Seeded E2E recurring rule",
            start_date,
            None,
            "monthly",
            "automatic",
            None,
        ),
    )
    conn.commit()
    conn.close()


def create_recovery_backup(path: Path) -> None:
    conn = init_current_db(path)
    created_at = now_iso()
    account_id = "account-recovered"
    conn.execute(
        """
        INSERT INTO accounts (id, name, type, opening_balance, archived, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (account_id, "Recovered Checking", "checking", 410.0, 0, created_at),
    )
    conn.execute(
        """
        INSERT INTO ledger_entries (
          id, account_id, entry_kind, amount, occurred_at_local, label, category, notes,
          recurring_rule_id, transfer_group_id, exclude_from_insights, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "entry-recovered-funding",
            account_id,
            "funding",
            90.0,
            created_at,
            "Recovered funding",
            "income",
            "Recovered from backup",
            None,
            None,
            0,
            created_at,
        ),
    )
    conn.commit()
    conn.close()


def seed_corrupt_with_backup(data_dir: Path) -> None:
    ensure_clean_dir(data_dir)
    backups_dir = data_dir / "backups"
    ensure_clean_dir(backups_dir)
    backup_path = backups_dir / "budget_20990101_000000.db"
    create_recovery_backup(backup_path)
    (data_dir / "budget.db").write_bytes(b"not-a-sqlite-database")


def seed_real_legacy_copy(legacy_dir: Path, source_path: Path) -> None:
    ensure_clean_dir(legacy_dir)
    shutil.copy2(source_path, legacy_dir / "budget.db")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--legacy-dir", required=True)
    parser.add_argument("--source-db")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    data_dir = Path(args.data_dir)
    legacy_dir = Path(args.legacy_dir)

    if args.mode == "legacy_fixture":
        seed_legacy_fixture(repo_root, legacy_dir)
        return
    if args.mode == "missed_recurring":
        seed_missed_recurring(data_dir)
        return
    if args.mode == "corrupt_with_backup":
        seed_corrupt_with_backup(data_dir)
        return
    if args.mode == "legacy_copy":
        if not args.source_db:
            raise SystemExit("--source-db is required for legacy_copy mode")
        seed_real_legacy_copy(legacy_dir, Path(args.source_db))
        return

    raise SystemExit(f"Unsupported seed mode: {args.mode}")


if __name__ == "__main__":
    main()
