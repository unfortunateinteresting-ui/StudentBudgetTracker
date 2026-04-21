mod models;

use std::{
    collections::{HashMap, HashSet},
    fs,
    path::{Path, PathBuf},
    sync::Mutex,
};

use anyhow::{anyhow, Context, Result};
use chrono::{Datelike, Duration, Local, NaiveDate};
use models::*;
use rusqlite::{params, Connection, OptionalExtension};
use serde::Deserialize;
use serde_json::{json, Value};
use tauri::{Manager, State};
use uuid::Uuid;

const APP_NAME: &str = "StudentBudgetTracker";
const LEGACY_APP_NAME: &str = "OfflineBudgetTracker";
const DB_NAME: &str = "budget.db";
const DEFAULT_BACKUP_RETENTION: u32 = 50;
const CURRENT_MIGRATION_VERSION: u32 = 2;
const DEFAULT_SCHOOL_YEAR_START_MONTH: u32 = 9;
const DEFAULT_SCHOOL_YEAR_MONTHS: u32 = 9;

const INIT_SCHEMA_SQL: &str = r#"
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
  created_at TEXT NOT NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id)
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
  last_applied_local TEXT,
  FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS monthly_caps (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  amount REAL NOT NULL,
  month_key TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_monthly_caps_unique ON monthly_caps(category, month_key);
CREATE INDEX IF NOT EXISTS idx_entries_account ON ledger_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_entries_occurred ON ledger_entries(occurred_at_local);
CREATE INDEX IF NOT EXISTS idx_entries_recurring ON ledger_entries(recurring_rule_id);
CREATE INDEX IF NOT EXISTS idx_recurring_status ON recurring_rules(status, start_date);
"#;

type AppResult<T> = Result<T>;

#[derive(Debug, Clone)]
struct AppEnv {
    data_dir: PathBuf,
    db_path: PathBuf,
    backups_dir: PathBuf,
    legacy_db_path: PathBuf,
}

#[derive(Debug, Default)]
struct RuntimeState {
    validated: bool,
    recovery_notice: Option<String>,
    undo_stack: Vec<UndoAction>,
}

#[derive(Debug)]
struct AppState {
    env: AppEnv,
    runtime: Mutex<RuntimeState>,
}

#[derive(Debug, Clone)]
enum InsightRangeSpec {
    SchoolYear,
    CurrentMonth,
    Month(String),
}

impl InsightRangeSpec {
    fn label(&self) -> String {
        match self {
            Self::SchoolYear => "school_year".to_string(),
            Self::CurrentMonth => "current_month".to_string(),
            Self::Month(month) => month.clone(),
        }
    }
}

#[derive(Debug, Clone)]
struct SnapshotQuery {
    filters: EntryFilters,
    range: InsightRangeSpec,
    focus_month: String,
    reference_date: NaiveDate,
    range_months: Vec<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct BreakdownContextPayload {
    range: Option<String>,
    filters: Option<EntryFilters>,
    month_key: Option<String>,
    account_id: Option<String>,
    category: Option<String>,
}

#[derive(Debug, Clone)]
enum UndoAction {
    ReplaceEntry {
        entry_id: String,
        previous: Option<LedgerEntry>,
    },
    DeleteEntry {
        entry: LedgerEntry,
    },
    DeleteEntries {
        entry_ids: Vec<String>,
    },
    ReplaceRecurring {
        rule_id: String,
        previous: Option<RecurringRule>,
    },
    ReplaceCap {
        cap_id: String,
        previous: Option<MonthlyCap>,
    },
    ReplaceAccount {
        account_id: String,
        previous: Option<Account>,
    },
    RestoreSnapshot {
        payload: String,
    },
}

impl AppEnv {
    fn discover() -> AppResult<Self> {
        let app_data_override = std::env::var("STUDENT_BUDGET_TRACKER_DATA_DIR").ok();
        let app_data_root =
            if let Some(path) = app_data_override.filter(|value| !value.trim().is_empty()) {
                PathBuf::from(path)
            } else {
                let appdata = std::env::var_os("APPDATA")
                    .map(PathBuf::from)
                    .ok_or_else(|| anyhow!("APPDATA is not available on this system."))?;
                appdata.join(APP_NAME)
            };

        let legacy_root = if let Some(path) = std::env::var("OFFLINE_BUDGET_TRACKER_DATA_DIR")
            .ok()
            .filter(|value| !value.trim().is_empty())
        {
            PathBuf::from(path)
        } else {
            let appdata = std::env::var_os("APPDATA")
                .map(PathBuf::from)
                .ok_or_else(|| anyhow!("APPDATA is not available on this system."))?;
            appdata.join(LEGACY_APP_NAME)
        };

        Ok(Self {
            db_path: app_data_root.join(DB_NAME),
            backups_dir: app_data_root.join("backups"),
            data_dir: app_data_root,
            legacy_db_path: legacy_root.join(DB_NAME),
        })
    }
}

impl AppState {
    fn new(env: AppEnv) -> Self {
        Self {
            env,
            runtime: Mutex::new(RuntimeState::default()),
        }
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let env = AppEnv::discover()?;
            app.manage(AppState::new(env));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            bootstrap_state,
            list_accounts,
            create_account,
            update_account,
            archive_account,
            list_entries,
            create_entry,
            update_entry,
            delete_entry,
            create_transfer,
            reconcile_account,
            list_recurring_rules,
            create_recurring_rule,
            update_recurring_rule,
            delete_recurring_rule,
            apply_recurring_rule_now,
            list_monthly_caps,
            set_monthly_cap,
            delete_monthly_cap,
            get_insights,
            get_calculation_breakdown,
            run_startup_recurring_check,
            apply_missed_recurring,
            export_json_v2,
            import_json,
            run_legacy_migration,
            list_backups,
            update_app_settings,
            create_backup_now,
            restore_backup,
            reset_all_data,
            undo_last_action
        ])
        .run(tauri::generate_context!())
        .expect("error while running Student Budget Tracker");
}

fn ensure_environment(state: &AppState) -> AppResult<()> {
    fs::create_dir_all(&state.env.data_dir)?;
    fs::create_dir_all(&state.env.backups_dir)?;

    let mut runtime = state.runtime.lock().expect("runtime lock poisoned");
    if !runtime.validated {
        runtime.recovery_notice = validate_or_recover_db(&state.env)?;
        runtime.validated = true;
    }
    drop(runtime);

    let conn = open_connection(&state.env.db_path)?;
    init_schema(&conn)?;

    if should_auto_migrate(&conn, &state.env)? {
        run_legacy_migration_internal(state)?;
    }

    Ok(())
}

fn validate_or_recover_db(env: &AppEnv) -> AppResult<Option<String>> {
    if !env.db_path.exists() {
        return Ok(None);
    }

    let validation_result = Connection::open(&env.db_path).and_then(|conn| {
        conn.query_row("SELECT COUNT(*) FROM sqlite_master", [], |_row| Ok(()))?;
        Ok(())
    });

    match validation_result {
        Ok(()) => Ok(None),
        Err(_) => recover_corrupt_db(env),
    }
}

fn recover_corrupt_db(env: &AppEnv) -> AppResult<Option<String>> {
    let stamp = timestamp_for_file();
    let corrupt_copy = env.data_dir.join(format!("budget_corrupt_{stamp}.db"));
    let _ = fs::rename(&env.db_path, corrupt_copy);
    let latest_backup = latest_backup_path(&env.backups_dir)?;
    if let Some(backup) = latest_backup {
        fs::copy(&backup, &env.db_path)?;
        Ok(Some(format!(
            "The main database was corrupted and was restored from backup {}.",
            backup.display()
        )))
    } else {
        Ok(Some(
            "The main database was corrupted and no backup was available; a fresh database will be created."
                .to_string(),
        ))
    }
}

fn open_connection(path: &Path) -> AppResult<Connection> {
    let conn = Connection::open(path)?;
    conn.pragma_update(None, "foreign_keys", "ON")?;
    Ok(conn)
}

fn init_schema(conn: &Connection) -> AppResult<()> {
    conn.execute_batch(INIT_SCHEMA_SQL)?;
    conn.execute(
        "INSERT OR IGNORE INTO app_settings (singleton_id) VALUES (1)",
        [],
    )?;
    Ok(())
}

fn now_local_iso() -> String {
    Local::now().format("%Y-%m-%dT%H:%M:%S").to_string()
}

fn timestamp_for_file() -> String {
    Local::now().format("%Y%m%d_%H%M%S").to_string()
}

fn stringify_account_type(value: &AccountType) -> &'static str {
    match value {
        AccountType::Checking => "checking",
        AccountType::Savings => "savings",
        AccountType::Cash => "cash",
        AccountType::Other => "other",
    }
}

fn parse_account_type(value: String) -> AppResult<AccountType> {
    match value.as_str() {
        "checking" => Ok(AccountType::Checking),
        "savings" => Ok(AccountType::Savings),
        "cash" => Ok(AccountType::Cash),
        "other" => Ok(AccountType::Other),
        _ => Err(anyhow!("Unsupported account type: {value}")),
    }
}

fn stringify_entry_kind(value: &EntryKind) -> &'static str {
    match value {
        EntryKind::Expense => "expense",
        EntryKind::Funding => "funding",
        EntryKind::RentCredit => "rent_credit",
        EntryKind::Transfer => "transfer",
        EntryKind::Adjustment => "adjustment",
    }
}

fn parse_entry_kind(value: String) -> AppResult<EntryKind> {
    match value.as_str() {
        "expense" => Ok(EntryKind::Expense),
        "funding" => Ok(EntryKind::Funding),
        "rent_credit" => Ok(EntryKind::RentCredit),
        "transfer" => Ok(EntryKind::Transfer),
        "adjustment" => Ok(EntryKind::Adjustment),
        _ => Err(anyhow!("Unsupported entry kind: {value}")),
    }
}

fn stringify_frequency(value: &RecurringFrequency) -> &'static str {
    match value {
        RecurringFrequency::Daily => "daily",
        RecurringFrequency::Weekly => "weekly",
        RecurringFrequency::Monthly => "monthly",
    }
}

fn parse_frequency(value: String) -> AppResult<RecurringFrequency> {
    match value.as_str() {
        "daily" => Ok(RecurringFrequency::Daily),
        "weekly" => Ok(RecurringFrequency::Weekly),
        "monthly" => Ok(RecurringFrequency::Monthly),
        _ => Err(anyhow!("Unsupported recurring frequency: {value}")),
    }
}

fn stringify_status(value: &RecurringStatus) -> &'static str {
    match value {
        RecurringStatus::Automatic => "automatic",
        RecurringStatus::Manual => "manual",
        RecurringStatus::Paused => "paused",
    }
}

fn parse_status(value: String) -> AppResult<RecurringStatus> {
    match value.as_str() {
        "automatic" => Ok(RecurringStatus::Automatic),
        "manual" => Ok(RecurringStatus::Manual),
        "paused" => Ok(RecurringStatus::Paused),
        _ => Err(anyhow!("Unsupported recurring status: {value}")),
    }
}

fn parse_bool(value: i64) -> bool {
    value != 0
}

fn date_portion(value: &str) -> Option<&str> {
    value.get(0..10)
}

fn month_key(value: &str) -> Option<&str> {
    value.get(0..7)
}

fn parse_date(value: &str) -> AppResult<NaiveDate> {
    date_portion(value)
        .ok_or_else(|| anyhow!("Missing date portion in value: {value}"))
        .and_then(|part| NaiveDate::parse_from_str(part, "%Y-%m-%d").map_err(|err| err.into()))
}

fn today_local() -> NaiveDate {
    Local::now().date_naive()
}

fn date_to_occurrence_iso(date: NaiveDate) -> String {
    format!("{}T09:00:00", date.format("%Y-%m-%d"))
}

fn school_year_month_keys(settings: &AppSettings, reference: NaiveDate) -> Vec<String> {
    let start_month = settings.school_year_start_month as i32;
    let total_months = settings.school_year_months as i32;
    let start_year = if reference.month() as i32 >= start_month {
        reference.year()
    } else {
        reference.year() - 1
    };
    let mut months = Vec::new();
    let mut year = start_year;
    let mut month = start_month;
    for _ in 0..total_months {
        months.push(format!("{year}-{month:02}"));
        month += 1;
        if month > 12 {
            month = 1;
            year += 1;
        }
    }
    months
}

fn forward_month_keys(start: NaiveDate, total_months: u32) -> Vec<String> {
    let mut months = Vec::new();
    let mut month_start = start;
    for _ in 0..total_months.max(1) {
        months.push(format!(
            "{}-{:02}",
            month_start.year(),
            month_start.month()
        ));
        month_start = add_months(month_start, 1);
    }
    months
}

fn is_rent_like(entry: &str) -> bool {
    let text = entry.trim().to_lowercase();
    text.contains("rent") || text.contains("loyer")
}

#[cfg(test)]
fn entry_effect(entry: &LedgerEntry) -> f64 {
    match entry.entry_kind {
        EntryKind::Expense => -entry.amount.abs(),
        EntryKind::Funding | EntryKind::RentCredit => entry.amount.abs(),
        EntryKind::Adjustment => entry.amount,
        EntryKind::Transfer => entry.amount,
    }
}

fn normalize_amount(kind: &EntryKind, amount: f64) -> f64 {
    match kind {
        EntryKind::Expense | EntryKind::Funding | EntryKind::RentCredit => amount.abs(),
        EntryKind::Transfer | EntryKind::Adjustment => amount,
    }
}

fn latest_backup_path(backups_dir: &Path) -> AppResult<Option<PathBuf>> {
    if !backups_dir.exists() {
        return Ok(None);
    }
    let mut entries: Vec<PathBuf> = fs::read_dir(backups_dir)?
        .filter_map(|entry| entry.ok().map(|item| item.path()))
        .filter(|path| path.extension().and_then(|ext| ext.to_str()) == Some("db"))
        .collect();
    entries.sort();
    Ok(entries.pop())
}

fn should_auto_migrate(conn: &Connection, env: &AppEnv) -> AppResult<bool> {
    let accounts_count: i64 =
        conn.query_row("SELECT COUNT(*) FROM accounts", [], |row| row.get(0))?;
    let migration_version: i64 = conn.query_row(
        "SELECT last_migration_version FROM app_settings WHERE singleton_id = 1",
        [],
        |row| row.get(0),
    )?;
    Ok(accounts_count == 0 && migration_version == 0 && env.legacy_db_path.exists())
}

fn account_from_row(
    conn: &Connection,
    id: String,
    name: String,
    type_raw: String,
    opening_balance: f64,
    archived: i64,
    created_at: String,
) -> AppResult<Account> {
    let balance_delta: f64 = conn.query_row(
        "SELECT COALESCE(SUM(CASE entry_kind WHEN 'expense' THEN -ABS(amount) WHEN 'funding' THEN ABS(amount) WHEN 'rent_credit' THEN ABS(amount) WHEN 'adjustment' THEN amount ELSE amount END), 0) FROM ledger_entries WHERE account_id = ?1",
        [id.clone()],
        |row| row.get(0),
    )?;
    Ok(Account {
        id,
        name,
        r#type: parse_account_type(type_raw)?,
        opening_balance,
        archived: parse_bool(archived),
        created_at,
        current_balance: opening_balance + balance_delta,
    })
}

fn fetch_accounts(conn: &Connection) -> AppResult<Vec<Account>> {
    let mut stmt = conn.prepare(
        "SELECT id, name, type, opening_balance, archived, created_at FROM accounts ORDER BY archived ASC, created_at ASC",
    )?;
    let rows = stmt.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, f64>(3)?,
            row.get::<_, i64>(4)?,
            row.get::<_, String>(5)?,
        ))
    })?;
    let mut accounts = Vec::new();
    for row in rows {
        let (id, name, type_raw, opening_balance, archived, created_at) = row?;
        accounts.push(account_from_row(
            conn,
            id,
            name,
            type_raw,
            opening_balance,
            archived,
            created_at,
        )?);
    }
    Ok(accounts)
}

fn fetch_account_by_id(conn: &Connection, account_id: &str) -> AppResult<Option<Account>> {
    let values = conn
        .query_row(
            "SELECT id, name, type, opening_balance, archived, created_at FROM accounts WHERE id = ?1",
            [account_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, f64>(3)?,
                    row.get::<_, i64>(4)?,
                    row.get::<_, String>(5)?,
                ))
            },
        )
        .optional()?;

    values
        .map(
            |(id, name, type_raw, opening_balance, archived, created_at)| {
                account_from_row(
                    conn,
                    id,
                    name,
                    type_raw,
                    opening_balance,
                    archived,
                    created_at,
                )
            },
        )
        .transpose()
}

fn require_active_account(conn: &Connection, account_id: &str) -> AppResult<Account> {
    let account = fetch_account_by_id(conn, account_id)?
        .ok_or_else(|| anyhow!("Account not found: {account_id}"))?;
    if account.archived {
        return Err(anyhow!("Archived accounts cannot receive new activity."));
    }
    Ok(account)
}

fn active_account_ids(conn: &Connection) -> AppResult<HashSet<String>> {
    Ok(fetch_accounts(conn)?
        .into_iter()
        .filter(|account| !account.archived)
        .map(|account| account.id)
        .collect())
}

fn fetch_entry_by_id(conn: &Connection, entry_id: &str) -> AppResult<Option<LedgerEntry>> {
    let values = conn
        .query_row(
            "SELECT id, account_id, entry_kind, amount, occurred_at_local, label, category, notes, recurring_rule_id, transfer_group_id, exclude_from_insights FROM ledger_entries WHERE id = ?1",
            [entry_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, f64>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, String>(7)?,
                    row.get::<_, Option<String>>(8)?,
                    row.get::<_, Option<String>>(9)?,
                    row.get::<_, i64>(10)?,
                ))
            },
        )
        .optional()?;
    values.map(entry_from_row_values).transpose()
}

fn fetch_entries_by_transfer_group(
    conn: &Connection,
    transfer_group_id: &str,
) -> AppResult<Vec<LedgerEntry>> {
    Ok(fetch_entries(conn)?
        .into_iter()
        .filter(|entry| entry.transfer_group_id.as_deref() == Some(transfer_group_id))
        .collect())
}

fn entry_from_row_values(
    values: (
        String,
        String,
        String,
        f64,
        String,
        String,
        String,
        String,
        Option<String>,
        Option<String>,
        i64,
    ),
) -> AppResult<LedgerEntry> {
    Ok(LedgerEntry {
        id: values.0,
        account_id: values.1,
        entry_kind: parse_entry_kind(values.2)?,
        amount: values.3,
        occurred_at_local: values.4,
        label: values.5,
        category: values.6,
        notes: values.7,
        recurring_rule_id: values.8,
        transfer_group_id: values.9,
        exclude_from_insights: parse_bool(values.10),
    })
}

fn fetch_entries(conn: &Connection) -> AppResult<Vec<LedgerEntry>> {
    let mut stmt = conn.prepare(
        "SELECT id, account_id, entry_kind, amount, occurred_at_local, label, category, notes, recurring_rule_id, transfer_group_id, exclude_from_insights FROM ledger_entries ORDER BY occurred_at_local DESC, created_at DESC",
    )?;
    let rows = stmt.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, f64>(3)?,
            row.get::<_, String>(4)?,
            row.get::<_, String>(5)?,
            row.get::<_, String>(6)?,
            row.get::<_, String>(7)?,
            row.get::<_, Option<String>>(8)?,
            row.get::<_, Option<String>>(9)?,
            row.get::<_, i64>(10)?,
        ))
    })?;
    let mut entries = Vec::new();
    for row in rows {
        entries.push(entry_from_row_values(row?)?);
    }
    Ok(entries)
}

fn fetch_recurring_rules(conn: &Connection) -> AppResult<Vec<RecurringRule>> {
    let mut stmt = conn.prepare(
        "SELECT id, label, entry_kind, amount, account_id, category, notes, start_date, end_date, frequency, status, last_applied_local FROM recurring_rules ORDER BY start_date ASC, label ASC",
    )?;
    let rows = stmt.query_map([], |row| {
        Ok(RecurringRule {
            id: row.get(0)?,
            label: row.get(1)?,
            entry_kind: parse_entry_kind(row.get::<_, String>(2)?).map_err(|err| {
                rusqlite::Error::FromSqlConversionFailure(
                    2,
                    rusqlite::types::Type::Text,
                    Box::new(std::io::Error::other(err.to_string())),
                )
            })?,
            amount: row.get(3)?,
            account_id: row.get(4)?,
            category: row.get(5)?,
            notes: row.get(6)?,
            start_date: row.get(7)?,
            end_date: row.get(8)?,
            frequency: parse_frequency(row.get::<_, String>(9)?).map_err(|err| {
                rusqlite::Error::FromSqlConversionFailure(
                    9,
                    rusqlite::types::Type::Text,
                    Box::new(std::io::Error::other(err.to_string())),
                )
            })?,
            status: parse_status(row.get::<_, String>(10)?).map_err(|err| {
                rusqlite::Error::FromSqlConversionFailure(
                    10,
                    rusqlite::types::Type::Text,
                    Box::new(std::io::Error::other(err.to_string())),
                )
            })?,
            last_applied_local: row.get(11)?,
        })
    })?;
    let mut rules = Vec::new();
    for row in rows {
        rules.push(row?);
    }
    Ok(rules)
}

fn fetch_monthly_caps(conn: &Connection) -> AppResult<Vec<MonthlyCap>> {
    let mut stmt = conn.prepare(
        "SELECT id, category, amount, month_key FROM monthly_caps ORDER BY month_key ASC, category ASC",
    )?;
    let rows = stmt.query_map([], |row| {
        Ok(MonthlyCap {
            id: row.get(0)?,
            category: row.get(1)?,
            amount: row.get(2)?,
            month_key: row.get(3)?,
        })
    })?;
    let mut caps = Vec::new();
    for row in rows {
        caps.push(row?);
    }
    Ok(caps)
}

fn fetch_settings(conn: &Connection) -> AppResult<AppSettings> {
    conn.query_row(
        "SELECT school_year_start_month, school_year_months, language, backup_retention, last_migration_version FROM app_settings WHERE singleton_id = 1",
        [],
        |row| {
            Ok(AppSettings {
                school_year_start_month: row.get::<_, i64>(0)? as u32,
                school_year_months: row.get::<_, i64>(1)? as u32,
                language: row.get(2)?,
                backup_retention: row.get::<_, i64>(3)? as u32,
                last_migration_version: row.get::<_, i64>(4)? as u32,
            })
        },
    )
    .map_err(Into::into)
}

fn update_settings_row(conn: &Connection, settings: &AppSettings) -> AppResult<()> {
    conn.execute(
        "UPDATE app_settings SET school_year_start_month = ?1, school_year_months = ?2, language = ?3, backup_retention = ?4, last_migration_version = ?5 WHERE singleton_id = 1",
        params![
            settings.school_year_start_month,
            settings.school_year_months,
            settings.language,
            settings.backup_retention,
            settings.last_migration_version,
        ],
    )?;
    Ok(())
}

fn validate_settings_input(input: &UpdateSettingsInput) -> AppResult<()> {
    if !(1..=12).contains(&input.school_year_start_month) {
        return Err(anyhow!("School-year start month must be between 1 and 12."));
    }
    if !(1..=12).contains(&input.school_year_months) {
        return Err(anyhow!(
            "School-year length must be between 1 and 12 months."
        ));
    }
    if !(1..=200).contains(&input.backup_retention) {
        return Err(anyhow!(
            "Backup retention must be between 1 and 200 copies."
        ));
    }
    Ok(())
}

fn list_backups_internal(env: &AppEnv) -> AppResult<Vec<BackupFile>> {
    fs::create_dir_all(&env.backups_dir)?;
    let mut backups: Vec<BackupFile> = fs::read_dir(&env.backups_dir)?
        .filter_map(|entry| entry.ok())
        .filter_map(|entry| {
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) != Some("db") {
                return None;
            }
            let metadata = entry.metadata().ok()?;
            if !metadata.is_file() {
                return None;
            }
            let modified = metadata.modified().ok()?;
            let modified: chrono::DateTime<Local> = modified.into();
            Some(BackupFile {
                file_name: path.file_name()?.to_string_lossy().to_string(),
                created_at: modified.format("%Y-%m-%d %H:%M:%S").to_string(),
                full_path: path.to_string_lossy().to_string(),
            })
        })
        .collect();
    backups.sort_by(|left, right| right.file_name.cmp(&left.file_name));
    Ok(backups)
}

fn backup_database(env: &AppEnv, retention: u32) -> AppResult<Option<BackupFile>> {
    if !env.db_path.exists() {
        return Ok(None);
    }
    fs::create_dir_all(&env.backups_dir)?;
    let file_name = format!("budget_{}.db", timestamp_for_file());
    let destination = env.backups_dir.join(&file_name);
    fs::copy(&env.db_path, &destination)?;

    let backups = list_backups_internal(env)?;
    for old in backups.iter().skip(retention as usize) {
        let _ = fs::remove_file(&old.full_path);
    }

    Ok(Some(BackupFile {
        file_name,
        created_at: now_local_iso(),
        full_path: destination.to_string_lossy().to_string(),
    }))
}

fn snapshot_payload(conn: &Connection) -> AppResult<String> {
    let payload = json!({
        "app": "StudentBudgetTracker",
        "schema_version": 2,
        "exported_at": now_local_iso(),
        "settings": fetch_settings(conn)?,
        "accounts": fetch_accounts(conn)?,
        "ledger_entries": fetch_entries(conn)?,
        "recurring_rules": fetch_recurring_rules(conn)?,
        "monthly_caps": fetch_monthly_caps(conn)?,
    });
    Ok(serde_json::to_string_pretty(&payload)?)
}

fn validate_restore_backup_path(env: &AppEnv, backup_path: &Path) -> AppResult<PathBuf> {
    if backup_path.extension().and_then(|ext| ext.to_str()) != Some("db") {
        return Err(anyhow!("Only .db backup files can be restored."));
    }

    if !backup_path.exists() {
        return Err(anyhow!(
            "Backup file was not found: {}",
            backup_path.display()
        ));
    }

    let canonical_backup = backup_path.canonicalize()?;
    let canonical_backups_dir = env.backups_dir.canonicalize()?;

    if !canonical_backup.starts_with(&canonical_backups_dir) {
        return Err(anyhow!(
            "Backup restore is restricted to files inside {}.",
            canonical_backups_dir.display()
        ));
    }

    if canonical_backup == env.db_path.canonicalize()? {
        return Err(anyhow!(
            "The live database cannot be restored as a backup source."
        ));
    }

    Ok(canonical_backup)
}

fn replace_all_data(conn: &mut Connection, payload: &Value) -> AppResult<()> {
    let tx = conn.transaction()?;
    tx.execute("DELETE FROM ledger_entries", [])?;
    tx.execute("DELETE FROM recurring_rules", [])?;
    tx.execute("DELETE FROM monthly_caps", [])?;
    tx.execute("DELETE FROM accounts", [])?;

    if let Some(settings) = payload.get("settings") {
        let settings: AppSettings = serde_json::from_value(settings.clone())?;
        update_settings_row(&tx, &settings)?;
    }

    if let Some(accounts) = payload.get("accounts").and_then(|value| value.as_array()) {
        for account in accounts {
            let account: Account = serde_json::from_value(account.clone())?;
            tx.execute(
                "INSERT INTO accounts (id, name, type, opening_balance, archived, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    account.id,
                    account.name,
                    stringify_account_type(&account.r#type),
                    account.opening_balance,
                    account.archived as i64,
                    account.created_at,
                ],
            )?;
        }
    }

    if let Some(entries) = payload
        .get("ledger_entries")
        .and_then(|value| value.as_array())
    {
        for entry in entries {
            let entry: LedgerEntry = serde_json::from_value(entry.clone())?;
            tx.execute(
                "INSERT INTO ledger_entries (id, account_id, entry_kind, amount, occurred_at_local, label, category, notes, recurring_rule_id, transfer_group_id, exclude_from_insights, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
                params![
                    entry.id,
                    entry.account_id,
                    stringify_entry_kind(&entry.entry_kind),
                    entry.amount,
                    entry.occurred_at_local,
                    entry.label,
                    entry.category,
                    entry.notes,
                    entry.recurring_rule_id,
                    entry.transfer_group_id,
                    entry.exclude_from_insights as i64,
                    now_local_iso(),
                ],
            )?;
        }
    }

    if let Some(rules) = payload
        .get("recurring_rules")
        .and_then(|value| value.as_array())
    {
        for rule in rules {
            let rule: RecurringRule = serde_json::from_value(rule.clone())?;
            tx.execute(
                "INSERT INTO recurring_rules (id, label, entry_kind, amount, account_id, category, notes, start_date, end_date, frequency, status, last_applied_local) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
                params![
                    rule.id,
                    rule.label,
                    stringify_entry_kind(&rule.entry_kind),
                    rule.amount,
                    rule.account_id,
                    rule.category,
                    rule.notes,
                    rule.start_date,
                    rule.end_date,
                    stringify_frequency(&rule.frequency),
                    stringify_status(&rule.status),
                    rule.last_applied_local,
                ],
            )?;
        }
    }

    if let Some(caps) = payload
        .get("monthly_caps")
        .and_then(|value| value.as_array())
    {
        for cap in caps {
            let cap: MonthlyCap = serde_json::from_value(cap.clone())?;
            tx.execute(
                "INSERT INTO monthly_caps (id, category, amount, month_key, created_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![cap.id, cap.category, cap.amount, cap.month_key, now_local_iso()],
            )?;
        }
    }

    tx.commit()?;
    Ok(())
}

fn push_undo(state: &AppState, action: UndoAction) {
    let mut runtime = state.runtime.lock().expect("runtime lock poisoned");
    runtime.undo_stack.push(action);
    if runtime.undo_stack.len() > 30 {
        let _ = runtime.undo_stack.remove(0);
    }
}

fn insert_entry_raw(conn: &Connection, entry: &LedgerEntry) -> AppResult<()> {
    conn.execute(
        "INSERT OR REPLACE INTO ledger_entries (id, account_id, entry_kind, amount, occurred_at_local, label, category, notes, recurring_rule_id, transfer_group_id, exclude_from_insights, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, COALESCE((SELECT created_at FROM ledger_entries WHERE id = ?1), ?12))",
        params![
            entry.id,
            entry.account_id,
            stringify_entry_kind(&entry.entry_kind),
            entry.amount,
            entry.occurred_at_local,
            entry.label,
            entry.category,
            entry.notes,
            entry.recurring_rule_id.as_deref(),
            entry.transfer_group_id.as_deref(),
            entry.exclude_from_insights as i64,
            now_local_iso(),
        ],
    )?;
    Ok(())
}

fn insert_rule_raw(conn: &Connection, rule: &RecurringRule) -> AppResult<()> {
    conn.execute(
        "INSERT OR REPLACE INTO recurring_rules (id, label, entry_kind, amount, account_id, category, notes, start_date, end_date, frequency, status, last_applied_local) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![
            rule.id,
            rule.label,
            stringify_entry_kind(&rule.entry_kind),
            rule.amount,
            rule.account_id,
            rule.category,
            rule.notes,
            rule.start_date,
            rule.end_date.as_deref(),
            stringify_frequency(&rule.frequency),
            stringify_status(&rule.status),
            rule.last_applied_local.as_deref(),
        ],
    )?;
    Ok(())
}

fn insert_cap_raw(conn: &Connection, cap: &MonthlyCap) -> AppResult<()> {
    conn.execute(
        "INSERT OR REPLACE INTO monthly_caps (id, category, amount, month_key, created_at) VALUES (?1, ?2, ?3, ?4, COALESCE((SELECT created_at FROM monthly_caps WHERE id = ?1), ?5))",
        params![cap.id, cap.category, cap.amount, cap.month_key, now_local_iso()],
    )?;
    Ok(())
}

fn insert_account_raw(conn: &Connection, account: &Account) -> AppResult<()> {
    conn.execute(
        "INSERT OR REPLACE INTO accounts (id, name, type, opening_balance, archived, created_at) VALUES (?1, ?2, ?3, ?4, ?5, COALESCE((SELECT created_at FROM accounts WHERE id = ?1), ?6))",
        params![
            account.id,
            account.name,
            stringify_account_type(&account.r#type),
            account.opening_balance,
            account.archived as i64,
            now_local_iso(),
        ],
    )?;
    Ok(())
}

fn delete_entry_raw(conn: &Connection, entry_id: &str) -> AppResult<()> {
    conn.execute("DELETE FROM ledger_entries WHERE id = ?1", [entry_id])?;
    Ok(())
}

fn delete_rule_raw(conn: &Connection, rule_id: &str) -> AppResult<()> {
    conn.execute("DELETE FROM recurring_rules WHERE id = ?1", [rule_id])?;
    Ok(())
}

fn delete_cap_raw(conn: &Connection, cap_id: &str) -> AppResult<()> {
    conn.execute("DELETE FROM monthly_caps WHERE id = ?1", [cap_id])?;
    Ok(())
}

fn delete_account_raw(conn: &Connection, account_id: &str) -> AppResult<()> {
    conn.execute("DELETE FROM accounts WHERE id = ?1", [account_id])?;
    Ok(())
}
fn month_end_day(year: i32, month: u32) -> u32 {
    let mut day = 31;
    while NaiveDate::from_ymd_opt(year, month, day).is_none() {
        day -= 1;
    }
    day
}

fn add_months(date: NaiveDate, months: i32) -> NaiveDate {
    let total_months = date.year() * 12 + (date.month() as i32 - 1) + months;
    let year = total_months.div_euclid(12);
    let month = (total_months.rem_euclid(12) + 1) as u32;
    let day = date.day().min(month_end_day(year, month));
    NaiveDate::from_ymd_opt(year, month, day).expect("valid calendar date")
}

fn scheduled_dates(
    rule: &RecurringRule,
    from: NaiveDate,
    until: NaiveDate,
) -> AppResult<Vec<NaiveDate>> {
    let start = parse_date(&rule.start_date)?;
    let effective_from = if from > start { from } else { start };
    let end_bound = if let Some(end_date) = &rule.end_date {
        parse_date(end_date)?
    } else {
        until
    };
    if effective_from > until || effective_from > end_bound {
        return Ok(Vec::new());
    }

    let until = until.min(end_bound);
    let mut dates = Vec::new();
    match rule.frequency {
        RecurringFrequency::Daily => {
            let mut cursor = start;
            while cursor <= until {
                if cursor >= effective_from {
                    dates.push(cursor);
                }
                cursor += Duration::days(1);
            }
        }
        RecurringFrequency::Weekly => {
            let mut cursor = start;
            while cursor <= until {
                if cursor >= effective_from {
                    dates.push(cursor);
                }
                cursor += Duration::days(7);
            }
        }
        RecurringFrequency::Monthly => {
            let mut index = 0;
            loop {
                let cursor = add_months(start, index);
                if cursor > until {
                    break;
                }
                if cursor >= effective_from {
                    dates.push(cursor);
                }
                index += 1;
            }
        }
    }
    Ok(dates)
}

fn existing_rule_occurrences(conn: &Connection, rule_id: &str) -> AppResult<HashSet<String>> {
    let mut stmt =
        conn.prepare("SELECT occurred_at_local FROM ledger_entries WHERE recurring_rule_id = ?1")?;
    let rows = stmt.query_map([rule_id], |row| row.get::<_, String>(0))?;
    let mut dates = HashSet::new();
    for row in rows {
        if let Some(date) = date_portion(&row?) {
            dates.insert(date.to_string());
        }
    }
    Ok(dates)
}

fn due_dates_for_rule(
    conn: &Connection,
    rule: &RecurringRule,
    from: NaiveDate,
    until: NaiveDate,
) -> AppResult<Vec<NaiveDate>> {
    let existing = existing_rule_occurrences(conn, &rule.id)?;
    let scheduled = scheduled_dates(rule, from, until)?;
    Ok(scheduled
        .into_iter()
        .filter(|date| !existing.contains(&date.format("%Y-%m-%d").to_string()))
        .collect())
}

fn apply_rule_dates(
    conn: &mut Connection,
    rule: &RecurringRule,
    dates: &[NaiveDate],
) -> AppResult<usize> {
    let tx = conn.transaction()?;
    for due_date in dates {
        let entry = LedgerEntry {
            id: Uuid::new_v4().to_string(),
            account_id: rule.account_id.clone(),
            entry_kind: rule.entry_kind.clone(),
            amount: rule.amount,
            occurred_at_local: date_to_occurrence_iso(*due_date),
            label: rule.label.clone(),
            category: rule.category.clone(),
            notes: if rule.notes.is_empty() {
                format!("Applied from recurring rule {}", rule.id)
            } else {
                rule.notes.clone()
            },
            recurring_rule_id: Some(rule.id.clone()),
            transfer_group_id: None,
            exclude_from_insights: false,
        };
        insert_entry_raw(&tx, &entry)?;
    }
    if let Some(last) = dates.last() {
        tx.execute(
            "UPDATE recurring_rules SET last_applied_local = ?1 WHERE id = ?2",
            params![date_to_occurrence_iso(*last), rule.id],
        )?;
    }
    tx.commit()?;
    Ok(dates.len())
}

fn apply_due_today_internal(conn: &mut Connection, today: NaiveDate) -> AppResult<usize> {
    let rules = fetch_recurring_rules(conn)?;
    let active_accounts = active_account_ids(conn)?;
    let mut applied = 0usize;
    for rule in rules.iter().filter(|rule| {
        rule.status == RecurringStatus::Automatic && active_accounts.contains(&rule.account_id)
    }) {
        let due = due_dates_for_rule(conn, rule, today, today)?;
        applied += apply_rule_dates(conn, rule, &due)?;
    }
    Ok(applied)
}

fn preview_missed_internal(
    conn: &Connection,
    today: NaiveDate,
) -> AppResult<Vec<MissedRecurringOccurrence>> {
    let rules = fetch_recurring_rules(conn)?;
    let active_accounts = active_account_ids(conn)?;
    let cutoff = today - Duration::days(1);
    if cutoff < today.with_day(1).unwrap_or(today) - Duration::days(3650) {
        return Ok(Vec::new());
    }

    let mut missed = Vec::new();
    for rule in rules.iter().filter(|rule| {
        rule.status == RecurringStatus::Automatic && active_accounts.contains(&rule.account_id)
    }) {
        let dates = due_dates_for_rule(conn, rule, parse_date(&rule.start_date)?, cutoff)?;
        if !dates.is_empty() {
            missed.push(MissedRecurringOccurrence {
                recurring_rule_id: rule.id.clone(),
                label: rule.label.clone(),
                frequency: rule.frequency.clone(),
                dates: dates
                    .into_iter()
                    .map(|date| date.format("%Y-%m-%d").to_string())
                    .collect(),
            });
        }
    }
    Ok(missed)
}

fn apply_missed_internal(
    conn: &mut Connection,
    today: NaiveDate,
    only_ids: Option<HashSet<String>>,
) -> AppResult<usize> {
    let rules = fetch_recurring_rules(conn)?;
    let active_accounts = active_account_ids(conn)?;
    let cutoff = today - Duration::days(1);
    let mut applied = 0usize;
    for rule in rules.iter().filter(|rule| {
        rule.status == RecurringStatus::Automatic && active_accounts.contains(&rule.account_id)
    }) {
        if let Some(ids) = &only_ids {
            if !ids.contains(&rule.id) {
                continue;
            }
        }
        let due = due_dates_for_rule(conn, rule, parse_date(&rule.start_date)?, cutoff)?;
        applied += apply_rule_dates(conn, rule, &due)?;
    }
    Ok(applied)
}

fn current_month_key() -> String {
    today_local().format("%Y-%m").to_string()
}

fn parse_month_start(value: &str) -> AppResult<NaiveDate> {
    NaiveDate::parse_from_str(&format!("{value}-01"), "%Y-%m-%d")
        .map_err(|_| anyhow!("Invalid month key: {value}. Expected YYYY-MM."))
}

fn parse_insight_range(range: Option<&str>) -> AppResult<InsightRangeSpec> {
    match range.map(str::trim).filter(|value| !value.is_empty()) {
        None | Some("school_year") => Ok(InsightRangeSpec::SchoolYear),
        Some("current_month") => Ok(InsightRangeSpec::CurrentMonth),
        Some(month) => {
            let _ = parse_month_start(month)?;
            Ok(InsightRangeSpec::Month(month.to_string()))
        }
    }
}

fn resolve_snapshot_query(
    settings: &AppSettings,
    range: Option<String>,
    filters: Option<EntryFilters>,
) -> AppResult<SnapshotQuery> {
    let today = today_local();
    let filters = filters.unwrap_or_default();
    let range = parse_insight_range(range.as_deref())?;

    let focus_month = if let Some(month) = filters.month_key.clone() {
        let _ = parse_month_start(&month)?;
        month
    } else if let InsightRangeSpec::Month(month) = &range {
        month.clone()
    } else {
        current_month_key()
    };

    let reference_date =
        if filters.month_key.is_some() || matches!(range, InsightRangeSpec::Month(_)) {
            parse_month_start(&focus_month)?
        } else {
            today
        };

    let range_months = match &range {
        InsightRangeSpec::SchoolYear => {
            let planning_start = parse_month_start(&focus_month)?;
            forward_month_keys(planning_start, settings.school_year_months)
        }
        InsightRangeSpec::CurrentMonth => vec![focus_month.clone()],
        InsightRangeSpec::Month(month) => vec![month.clone()],
    };

    Ok(SnapshotQuery {
        filters,
        range,
        focus_month,
        reference_date,
        range_months,
    })
}

fn entry_matches_filters(entry: &LedgerEntry, filters: &EntryFilters) -> bool {
    let matches_search = filters
        .search
        .as_ref()
        .map(|search| {
            let haystack = format!(
                "{} {} {} {}",
                entry.label,
                entry.category,
                entry.notes,
                stringify_entry_kind(&entry.entry_kind)
            )
            .to_lowercase();
            haystack.contains(&search.to_lowercase())
        })
        .unwrap_or(true);
    let matches_month = filters
        .month_key
        .as_ref()
        .map(|month| month_key(&entry.occurred_at_local) == Some(month.as_str()))
        .unwrap_or(true);
    let matches_account = filters
        .account_id
        .as_ref()
        .map(|account_id| entry.account_id == *account_id)
        .unwrap_or(true);

    matches_search && matches_month && matches_account
}

fn recurring_rule_matches_filters(rule: &RecurringRule, filters: &EntryFilters) -> bool {
    let matches_search = filters
        .search
        .as_ref()
        .map(|search| {
            let haystack = format!(
                "{} {} {} {} {}",
                rule.label,
                rule.category,
                rule.notes,
                stringify_entry_kind(&rule.entry_kind),
                stringify_status(&rule.status)
            )
            .to_lowercase();
            haystack.contains(&search.to_lowercase())
        })
        .unwrap_or(true);
    let matches_account = filters
        .account_id
        .as_ref()
        .map(|account_id| rule.account_id == *account_id)
        .unwrap_or(true);

    matches_search && matches_account
}

fn cap_matches_filters(cap: &MonthlyCap, filters: &EntryFilters) -> bool {
    filters
        .search
        .as_ref()
        .map(|search| cap.category.to_lowercase().contains(&search.to_lowercase()))
        .unwrap_or(true)
}

fn snapshot_context_lines(query: &SnapshotQuery) -> Vec<String> {
    let mut lines = vec![
        format!("Focus month = {}", query.focus_month),
        format!("Range = {}", query.range.label()),
    ];
    if let Some(account_id) = query.filters.account_id.as_ref() {
        lines.push(format!("Account filter = {account_id}"));
    }
    if let Some(search) = query
        .filters
        .search
        .as_ref()
        .filter(|value| !value.trim().is_empty())
    {
        lines.push(format!("Search filter = {}", search.trim()));
    }
    lines
}

fn calculate_snapshot_with_query(
    conn: &Connection,
    settings: &AppSettings,
    query: &SnapshotQuery,
) -> AppResult<InsightSnapshot> {
    let accounts = fetch_accounts(conn)?;
    let entries = fetch_entries(conn)?;
    let rules = fetch_recurring_rules(conn)?;
    let caps = fetch_monthly_caps(conn)?;

    let active_accounts = accounts
        .iter()
        .filter(|account| {
            !account.archived
                && query
                    .filters
                    .account_id
                    .as_ref()
                    .map(|account_id| account.id == *account_id)
                    .unwrap_or(true)
        })
        .collect::<Vec<_>>();
    let active_account_ids = active_accounts
        .iter()
        .map(|account| account.id.clone())
        .collect::<HashSet<_>>();
    let active_rules = rules
        .into_iter()
        .filter(|rule| {
            active_account_ids.contains(&rule.account_id)
                && recurring_rule_matches_filters(rule, &query.filters)
        })
        .collect::<Vec<_>>();
    let filtered_caps = caps
        .into_iter()
        .filter(|cap| cap_matches_filters(cap, &query.filters))
        .collect::<Vec<_>>();
    let filtered_entries = entries
        .into_iter()
        .filter(|entry| {
            active_account_ids.contains(&entry.account_id)
                && entry_matches_filters(entry, &query.filters)
        })
        .collect::<Vec<_>>();

    let range_month_set = query.range_months.iter().cloned().collect::<HashSet<_>>();
    let range_entries = filtered_entries
        .iter()
        .filter(|entry| {
            month_key(&entry.occurred_at_local)
                .map(|month| range_month_set.contains(month))
                .unwrap_or(false)
        })
        .cloned()
        .collect::<Vec<_>>();

    let total_available_cash = active_accounts
        .iter()
        .map(|account| account.current_balance)
        .sum::<f64>();
    let this_month_spend = filtered_entries
        .iter()
        .filter(|entry| {
            entry.entry_kind == EntryKind::Expense
                && !entry.exclude_from_insights
                && month_key(&entry.occurred_at_local) == Some(query.focus_month.as_str())
        })
        .map(|entry| entry.amount.abs())
        .sum::<f64>();
    let this_month_cap = filtered_caps
        .iter()
        .filter(|cap| cap.month_key == query.focus_month)
        .map(|cap| cap.amount)
        .sum::<f64>();

    let remaining_fixed_bills = active_rules
        .iter()
        .filter(|rule| {
            rule.status != RecurringStatus::Paused && rule.entry_kind == EntryKind::Expense
        })
        .map(|rule| {
            let future_dates = scheduled_dates(
                rule,
                query.reference_date,
                add_months(query.reference_date, settings.school_year_months as i32),
            )
            .unwrap_or_default();
            future_dates.len() as f64 * rule.amount
        })
        .sum::<f64>();

    let remaining_caps = filtered_caps
        .iter()
        .filter(|cap| {
            range_month_set.contains(&cap.month_key)
                && cap.month_key.as_str() >= query.focus_month.as_str()
        })
        .map(|cap| cap.amount)
        .sum::<f64>();

    let school_year_runway_remaining = total_available_cash - remaining_fixed_bills;
    let projected_end_of_year_cushion =
        total_available_cash - remaining_fixed_bills - remaining_caps;

    let focus_month_start = parse_month_start(&query.focus_month)?;
    let focus_month_end = add_months(focus_month_start, 1) - Duration::days(1);
    let rent_due_this_month = active_rules
        .iter()
        .filter(|rule| {
            rule.status != RecurringStatus::Paused
                && rule.entry_kind == EntryKind::Expense
                && is_rent_like(&format!("{} {} {}", rule.label, rule.category, rule.notes))
        })
        .map(|rule| {
            scheduled_dates(rule, focus_month_start, focus_month_end)
                .unwrap_or_default()
                .len() as f64
                * rule.amount
        })
        .sum::<f64>();

    let rent_paid_this_month = filtered_entries
        .iter()
        .filter(|entry| {
            entry.entry_kind == EntryKind::Expense
                && !entry.exclude_from_insights
                && month_key(&entry.occurred_at_local) == Some(query.focus_month.as_str())
                && is_rent_like(&format!(
                    "{} {} {}",
                    entry.label, entry.category, entry.notes
                ))
        })
        .map(|entry| entry.amount)
        .sum::<f64>();
    let rent_credit_this_month = filtered_entries
        .iter()
        .filter(|entry| {
            entry.entry_kind == EntryKind::RentCredit
                && !entry.exclude_from_insights
                && month_key(&entry.occurred_at_local) == Some(query.focus_month.as_str())
        })
        .map(|entry| entry.amount)
        .sum::<f64>();
    let rent_net_this_month = (rent_paid_this_month - rent_credit_this_month).max(0.0);

    let upcoming_obligations = active_rules
        .iter()
        .filter(|rule| rule.status != RecurringStatus::Paused)
        .filter_map(|rule| {
            let due = due_dates_for_rule(
                conn,
                rule,
                query.reference_date,
                query.reference_date + Duration::days(30),
            )
            .ok()?
            .into_iter()
            .next()?;
            Some(UpcomingObligation {
                recurring_rule_id: rule.id.clone(),
                label: rule.label.clone(),
                account_id: rule.account_id.clone(),
                category: rule.category.clone(),
                amount: rule.amount,
                due_date: due.format("%Y-%m-%d").to_string(),
                entry_kind: rule.entry_kind.clone(),
            })
        })
        .collect::<Vec<_>>();

    let mut category_map: HashMap<String, f64> = HashMap::new();
    for entry in filtered_entries.iter().filter(|entry| {
        entry.entry_kind == EntryKind::Expense
            && !entry.exclude_from_insights
            && month_key(&entry.occurred_at_local) == Some(query.focus_month.as_str())
    }) {
        *category_map.entry(entry.category.clone()).or_insert(0.0) += entry.amount;
    }
    let mut category_spend_this_month: Vec<ChartPoint> = category_map
        .into_iter()
        .map(|(label, value)| ChartPoint { label, value })
        .collect();
    category_spend_this_month.sort_by(|left, right| {
        right
            .value
            .partial_cmp(&left.value)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    let recent_activity = range_entries.iter().take(8).cloned().collect::<Vec<_>>();
    let account_balances = active_accounts
        .iter()
        .map(|account| ChartPoint {
            label: account.name.clone(),
            value: account.current_balance,
        })
        .collect::<Vec<_>>();

    let mut activity_groups_map: HashMap<String, Vec<LedgerEntry>> = HashMap::new();
    for entry in range_entries.iter().cloned() {
        let key = month_key(&entry.occurred_at_local)
            .unwrap_or("unknown")
            .to_string();
        activity_groups_map.entry(key).or_default().push(entry);
    }
    let mut activity_groups = activity_groups_map
        .into_iter()
        .map(|(month_key, group_entries)| ActivityGroup {
            total_expense: group_entries
                .iter()
                .filter(|entry| {
                    entry.entry_kind == EntryKind::Expense && !entry.exclude_from_insights
                })
                .map(|entry| entry.amount)
                .sum(),
            total_funding: group_entries
                .iter()
                .filter(|entry| {
                    entry.entry_kind == EntryKind::Funding && !entry.exclude_from_insights
                })
                .map(|entry| entry.amount)
                .sum(),
            total_rent_credit: group_entries
                .iter()
                .filter(|entry| {
                    entry.entry_kind == EntryKind::RentCredit && !entry.exclude_from_insights
                })
                .map(|entry| entry.amount)
                .sum(),
            entries: group_entries,
            month_key,
        })
        .collect::<Vec<_>>();
    activity_groups.sort_by(|left, right| right.month_key.cmp(&left.month_key));

    let mut runway_balance = total_available_cash;
    let monthly_series = query
        .range_months
        .iter()
        .map(|month| {
            let spent = filtered_entries
                .iter()
                .filter(|entry| {
                    entry.entry_kind == EntryKind::Expense
                        && !entry.exclude_from_insights
                        && month_key(&entry.occurred_at_local) == Some(month.as_str())
                })
                .map(|entry| entry.amount)
                .sum::<f64>();
            let cap_total = filtered_caps
                .iter()
                .filter(|cap| &cap.month_key == month)
                .map(|cap| cap.amount)
                .sum::<f64>();
            let fixed = active_rules
                .iter()
                .filter(|rule| {
                    rule.status != RecurringStatus::Paused && rule.entry_kind == EntryKind::Expense
                })
                .filter_map(|rule| {
                    scheduled_dates(
                        rule,
                        parse_month_start(month).ok()?,
                        add_months(parse_month_start(month).ok()?, 1) - Duration::days(1),
                    )
                    .ok()
                    .map(|dates| dates.len() as f64 * rule.amount)
                })
                .sum::<f64>();
            runway_balance -= fixed + cap_total;
            MonthlySeriesPoint {
                month_key: month.clone(),
                spent,
                cap: cap_total,
                runway_balance,
            }
        })
        .collect::<Vec<_>>();

    let context_lines = snapshot_context_lines(query);
    let build_lines = |metric_lines: Vec<String>| {
        let mut lines = metric_lines;
        lines.extend(context_lines.clone());
        lines
    };

    let mut breakdowns = HashMap::new();
    breakdowns.insert(
        "total_available_cash".to_string(),
        build_lines(vec![
            format!("Active accounts total = {}", total_available_cash),
            "Each account balance = opening balance + signed ledger effects.".to_string(),
            "Search and month filters do not change current balances; only account filters do."
                .to_string(),
        ]),
    );
    breakdowns.insert(
        "this_month_spend".to_string(),
        build_lines(vec![
            format!("This month expense total = {}", this_month_spend),
            format!("This month cap total = {}", this_month_cap),
            "Excluded entries are ignored here.".to_string(),
        ]),
    );
    breakdowns.insert(
        "school_year_runway_remaining".to_string(),
        build_lines(vec![
            format!("Total available cash = {}", total_available_cash),
            format!("Remaining fixed bills = {}", remaining_fixed_bills),
            format!(
                "Balance after remaining fixed bills in the planning window = {}",
                school_year_runway_remaining
            ),
        ]),
    );
    breakdowns.insert(
        "projected_end_of_year_cushion".to_string(),
        build_lines(vec![
            format!("Total available cash = {}", total_available_cash),
            format!("Remaining fixed bills = {}", remaining_fixed_bills),
            format!("Remaining monthly caps = {}", remaining_caps),
            format!(
                "Projected end balance for the planning window = {}",
                projected_end_of_year_cushion
            ),
        ]),
    );
    breakdowns.insert(
        "rent_net_this_month".to_string(),
        build_lines(vec![
            format!("Rent paid this month = {}", rent_paid_this_month),
            format!("Rent credit this month = {}", rent_credit_this_month),
            format!("Rent net this month = {}", rent_net_this_month),
        ]),
    );

    Ok(InsightSnapshot {
        total_available_cash,
        this_month_spend,
        this_month_cap,
        school_year_runway_remaining,
        projected_end_of_year_cushion,
        rent_due_this_month,
        rent_paid_this_month,
        rent_credit_this_month,
        rent_net_this_month,
        upcoming_obligations,
        recent_activity,
        account_balances,
        category_spend_this_month,
        monthly_series,
        activity_groups,
        breakdowns,
    })
}

fn calculate_snapshot_for_query(
    conn: &Connection,
    range: Option<String>,
    filters: Option<EntryFilters>,
) -> AppResult<InsightSnapshot> {
    let settings = fetch_settings(conn)?;
    let query = resolve_snapshot_query(&settings, range, filters)?;
    calculate_snapshot_with_query(conn, &settings, &query)
}

fn calculate_snapshot(conn: &Connection) -> AppResult<InsightSnapshot> {
    calculate_snapshot_for_query(conn, None, None)
}

fn breakdown_for_metric(
    conn: &Connection,
    metric_id: &str,
    context: Option<Value>,
) -> AppResult<BreakdownResult> {
    let payload = context
        .map(serde_json::from_value::<BreakdownContextPayload>)
        .transpose()?
        .unwrap_or_default();
    let mut filters = payload.filters.unwrap_or_default();
    if filters.month_key.is_none() {
        filters.month_key = payload.month_key.clone();
    }
    if filters.account_id.is_none() {
        filters.account_id = payload.account_id.clone();
    }

    let settings = fetch_settings(conn)?;
    let query = resolve_snapshot_query(&settings, payload.range.clone(), Some(filters))?;
    let snapshot = calculate_snapshot_with_query(conn, &settings, &query)?;

    let title = match metric_id {
        "monthly_spend" | "monthly_cap" | "monthly_runway_balance" => {
            format!("Monthly detail ({})", query.focus_month)
        }
        "category_spend" => payload
            .category
            .as_ref()
            .map(|category| format!("Category detail ({category})"))
            .unwrap_or_else(|| breakdown_title(metric_id)),
        _ => breakdown_title(metric_id),
    };

    let lines = match metric_id {
        "monthly_spend" | "monthly_cap" | "monthly_runway_balance" => {
            let month_activity = snapshot
                .activity_groups
                .iter()
                .find(|group| group.month_key == query.focus_month);
            let month_point = snapshot
                .monthly_series
                .iter()
                .find(|point| point.month_key == query.focus_month);
            let mut lines = snapshot_context_lines(&query);
            lines.extend([
                format!(
                    "Graph spend = {}",
                    month_point.map(|point| point.spent).unwrap_or(0.0)
                ),
                format!(
                    "Ledger expense = {}",
                    month_activity
                        .map(|group| group.total_expense)
                        .unwrap_or(0.0)
                ),
                format!(
                    "Funding = {}",
                    month_activity
                        .map(|group| group.total_funding)
                        .unwrap_or(0.0)
                ),
                format!(
                    "Rent credit = {}",
                    month_activity
                        .map(|group| group.total_rent_credit)
                        .unwrap_or(0.0)
                ),
                format!(
                    "Cap = {}",
                    month_point.map(|point| point.cap).unwrap_or(0.0)
                ),
                format!(
                    "Runway balance = {}",
                    month_point.map(|point| point.runway_balance).unwrap_or(0.0)
                ),
            ]);
            lines
        }
        "category_spend" => {
            let mut lines = snapshot_context_lines(&query);
            let category = payload.category.unwrap_or_else(|| "unknown".to_string());
            let category_total = snapshot
                .category_spend_this_month
                .iter()
                .find(|point| point.label == category)
                .map(|point| point.value)
                .unwrap_or(0.0);
            lines.extend([
                format!("Category = {category}"),
                format!("Category spend = {}", category_total),
                format!("This month expense total = {}", snapshot.this_month_spend),
            ]);
            lines
        }
        _ => snapshot
            .breakdowns
            .get(metric_id)
            .cloned()
            .unwrap_or_else(|| vec!["No calculation available.".to_string()]),
    };

    Ok(BreakdownResult {
        metric_id: metric_id.to_string(),
        title,
        lines,
    })
}

fn breakdown_title(metric_id: &str) -> String {
    match metric_id {
        "total_available_cash" => "Total available cash".to_string(),
        "this_month_spend" => "This month spend".to_string(),
        "school_year_runway_remaining" => "Planning window balance".to_string(),
        "projected_end_of_year_cushion" => "Projected end balance".to_string(),
        "rent_net_this_month" => "Rent net this month".to_string(),
        other => format!("Calculation details: {other}"),
    }
}

fn migration_status(conn: &Connection, env: &AppEnv) -> AppResult<MigrationStatus> {
    let last_run_at = conn
        .query_row(
            "SELECT value FROM app_meta WHERE key = 'legacy_migration_run_at'",
            [],
            |row| row.get::<_, String>(0),
        )
        .optional()?;
    Ok(MigrationStatus {
        has_legacy_db: env.legacy_db_path.exists(),
        has_run: last_run_at.is_some(),
        legacy_path: env
            .legacy_db_path
            .exists()
            .then(|| env.legacy_db_path.to_string_lossy().to_string()),
        last_run_at,
    })
}

fn create_primary_account(conn: &Connection, opening_balance: f64) -> AppResult<Account> {
    let account = Account {
        id: Uuid::new_v4().to_string(),
        name: "Primary Account".to_string(),
        r#type: AccountType::Checking,
        opening_balance,
        archived: false,
        created_at: now_local_iso(),
        current_balance: opening_balance,
    };
    insert_account_raw(conn, &account)?;
    Ok(account)
}
fn legacy_kind(tx_type: &str, label: &str, category: &str, notes: &str) -> EntryKind {
    let combined = format!("{label} {category} {notes}").to_lowercase();
    if combined.contains("adjustment") || combined.contains("reconcile") {
        EntryKind::Adjustment
    } else if tx_type == "expense" {
        EntryKind::Expense
    } else if is_rent_like(&combined) {
        EntryKind::RentCredit
    } else {
        EntryKind::Funding
    }
}

fn legacy_entry_amount(kind: &EntryKind, tx_type: &str, amount: f64) -> f64 {
    match kind {
        EntryKind::Expense | EntryKind::Funding | EntryKind::RentCredit => amount.abs(),
        EntryKind::Transfer => amount,
        EntryKind::Adjustment => {
            if tx_type == "expense" {
                -amount.abs()
            } else {
                amount.abs()
            }
        }
    }
}

fn legacy_app_settings(language: String, school_year_months: u32) -> AppSettings {
    AppSettings {
        school_year_start_month: DEFAULT_SCHOOL_YEAR_START_MONTH,
        school_year_months: school_year_months.max(1),
        language,
        backup_retention: DEFAULT_BACKUP_RETENTION,
        last_migration_version: CURRENT_MIGRATION_VERSION,
    }
}

fn apply_legacy_planning_defaults(
    conn: &Connection,
    account_id: &str,
    settings: &AppSettings,
    saw_rent_rule: bool,
    reference: NaiveDate,
    rent_monthly_manual: f64,
    rent_base_monthly: f64,
    food_house: f64,
    misc: f64,
    medical: f64,
    school: f64,
    household: f64,
    health: f64,
) -> AppResult<()> {
    let months = school_year_month_keys(settings, reference);
    let cap_templates = [
        ("food", food_house),
        ("misc", misc),
        ("medical", medical),
        ("school", school),
        ("household", household),
        ("health", health),
    ];

    for month in months {
        for (category, amount) in cap_templates {
            if amount > 0.0 {
                insert_cap_raw(
                    conn,
                    &MonthlyCap {
                        id: Uuid::new_v4().to_string(),
                        category: category.to_string(),
                        amount,
                        month_key: month.clone(),
                    },
                )?;
            }
        }
    }

    if !saw_rent_rule {
        let amount = if rent_monthly_manual > 0.0 {
            rent_monthly_manual
        } else {
            rent_base_monthly
        };
        if amount > 0.0 {
            insert_rule_raw(
                conn,
                &RecurringRule {
                    id: Uuid::new_v4().to_string(),
                    label: "Migrated Rent Plan".to_string(),
                    entry_kind: EntryKind::Expense,
                    amount,
                    account_id: account_id.to_string(),
                    category: "rent".to_string(),
                    notes: "Created during legacy migration from manual rent settings.".to_string(),
                    start_date: format!(
                        "{}-09-01",
                        if reference.month() >= 9 {
                            reference.year()
                        } else {
                            reference.year() - 1
                        }
                    ),
                    end_date: None,
                    frequency: RecurringFrequency::Monthly,
                    status: RecurringStatus::Automatic,
                    last_applied_local: None,
                },
            )?;
        }
    }

    Ok(())
}

fn run_legacy_migration_internal(state: &AppState) -> AppResult<MigrationStatus> {
    if !state.env.legacy_db_path.exists() {
        let conn = open_connection(&state.env.db_path)?;
        return migration_status(&conn, &state.env);
    }

    let mut conn = open_connection(&state.env.db_path)?;
    init_schema(&conn)?;
    let backup_payload = snapshot_payload(&conn)?;
    push_undo(
        state,
        UndoAction::RestoreSnapshot {
            payload: backup_payload,
        },
    );

    let legacy_copy = state
        .env
        .backups_dir
        .join(format!("legacy_budget_{}.db", timestamp_for_file()));
    let _ = fs::copy(&state.env.legacy_db_path, legacy_copy);

    let legacy = Connection::open(&state.env.legacy_db_path).with_context(|| {
        format!(
            "Failed to open legacy database at {}",
            state.env.legacy_db_path.display()
        )
    })?;

    let defaults = (
        0.0,
        9,
        "EN".to_string(),
        0.0,
        650.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    );
    let (starting_balance, plan_months_total, language, rent_monthly_manual, rent_base_monthly, food_house, misc, medical, school, household, health) = legacy
        .query_row(
            "SELECT starting_balance, plan_months_total, language, rent_monthly_manual, rent_base_monthly, food_house_monthly, misc_monthly, medical_monthly, school_monthly, household_monthly, health_monthly FROM settings LIMIT 1",
            [],
            |row| {
                Ok((
                    row.get::<_, f64>(0).unwrap_or(0.0),
                    row.get::<_, i64>(1).unwrap_or(9),
                    row.get::<_, String>(2).unwrap_or_else(|_| "EN".to_string()),
                    row.get::<_, f64>(3).unwrap_or(0.0),
                    row.get::<_, f64>(4).unwrap_or(650.0),
                    row.get::<_, f64>(5).unwrap_or(0.0),
                    row.get::<_, f64>(6).unwrap_or(0.0),
                    row.get::<_, f64>(7).unwrap_or(0.0),
                    row.get::<_, f64>(8).unwrap_or(0.0),
                    row.get::<_, f64>(9).unwrap_or(0.0),
                    row.get::<_, f64>(10).unwrap_or(0.0),
                ))
            },
        )
        .optional()?
        .unwrap_or(defaults);

    let tx = conn.transaction()?;
    tx.execute("DELETE FROM ledger_entries", [])?;
    tx.execute("DELETE FROM recurring_rules", [])?;
    tx.execute("DELETE FROM monthly_caps", [])?;
    tx.execute("DELETE FROM accounts", [])?;

    let primary_account = Account {
        id: Uuid::new_v4().to_string(),
        name: "Primary Account".to_string(),
        r#type: AccountType::Checking,
        opening_balance: starting_balance,
        archived: false,
        created_at: now_local_iso(),
        current_balance: starting_balance,
    };
    insert_account_raw(&tx, &primary_account)?;

    let mut tx_stmt = legacy.prepare(
        "SELECT id, datetime_local, amount, type, label, category, notes, recurring_id, excluded_from_averages FROM transactions ORDER BY datetime_local ASC",
    )?;
    let rows = tx_stmt.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, f64>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, String>(4).unwrap_or_default(),
            row.get::<_, String>(5).unwrap_or_default(),
            row.get::<_, String>(6).unwrap_or_default(),
            row.get::<_, Option<String>>(7).ok().flatten(),
            row.get::<_, i64>(8).unwrap_or(0),
        ))
    })?;
    for row in rows {
        let (id, datetime_local, amount, tx_type, label, category, notes, recurring_id, excluded) =
            row?;
        let entry_kind = legacy_kind(&tx_type, &label, &category, &notes);
        let entry = LedgerEntry {
            id,
            account_id: primary_account.id.clone(),
            entry_kind: entry_kind.clone(),
            amount: legacy_entry_amount(&entry_kind, &tx_type, amount),
            occurred_at_local: datetime_local,
            label,
            category,
            notes,
            recurring_rule_id: recurring_id,
            transfer_group_id: None,
            exclude_from_insights: parse_bool(excluded),
        };
        insert_entry_raw(&tx, &entry)?;
    }

    let mut recurring_stmt = legacy.prepare(
        "SELECT id, label, amount, type, category, notes, start_date, end_date, status, frequency, last_applied FROM recurring_charges ORDER BY start_date ASC",
    )?;
    let recurring_rows = recurring_stmt.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, f64>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, String>(4).unwrap_or_default(),
            row.get::<_, String>(5).unwrap_or_default(),
            row.get::<_, String>(6)?,
            row.get::<_, Option<String>>(7).ok().flatten(),
            row.get::<_, String>(8)
                .unwrap_or_else(|_| "automatic".to_string()),
            row.get::<_, String>(9)
                .unwrap_or_else(|_| "monthly".to_string()),
            row.get::<_, Option<String>>(10).ok().flatten(),
        ))
    })?;
    let mut saw_rent_rule = false;
    for row in recurring_rows {
        let (
            id,
            label,
            amount,
            tx_type,
            category,
            notes,
            start_date,
            end_date,
            status,
            frequency,
            last_applied,
        ) = row?;
        let entry_kind = legacy_kind(&tx_type, &label, &category, &notes);
        if is_rent_like(&format!("{label} {category} {notes}")) {
            saw_rent_rule = true;
        }
        insert_rule_raw(
            &tx,
            &RecurringRule {
                id,
                label,
                entry_kind,
                amount: amount.abs(),
                account_id: primary_account.id.clone(),
                category,
                notes,
                start_date,
                end_date,
                frequency: parse_frequency(frequency).unwrap_or(RecurringFrequency::Monthly),
                status: parse_status(status).unwrap_or(RecurringStatus::Automatic),
                last_applied_local: last_applied,
            },
        )?;
    }

    let settings = legacy_app_settings(language, plan_months_total.max(1) as u32);
    update_settings_row(&tx, &settings)?;

    let reference = today_local();
    apply_legacy_planning_defaults(
        &tx,
        &primary_account.id,
        &settings,
        saw_rent_rule,
        reference,
        rent_monthly_manual,
        rent_base_monthly,
        food_house,
        misc,
        medical,
        school,
        household,
        health,
    )?;

    tx.execute(
        "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('legacy_migration_run_at', ?1)",
        [now_local_iso()],
    )?;
    tx.commit()?;

    let retention = fetch_settings(&conn)?.backup_retention;
    let _ = backup_database(&state.env, retention)?;
    migration_status(&conn, &state.env)
}

fn import_json_internal(state: &AppState, path: &str) -> AppResult<()> {
    let payload = fs::read_to_string(path).with_context(|| format!("Failed to read {path}"))?;
    let value: Value = serde_json::from_str(&payload)?;

    ensure_environment(state)?;
    let mut conn = open_connection(&state.env.db_path)?;
    let previous = snapshot_payload(&conn)?;
    push_undo(state, UndoAction::RestoreSnapshot { payload: previous });

    if value.get("schema_version").and_then(Value::as_u64) == Some(2) {
        replace_all_data(&mut conn, &value)?;
    } else {
        let settings_value = value.get("settings");
        let starting_balance = settings_value
            .and_then(|item| item.get("starting_balance"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let plan_months_total = settings_value
            .and_then(|item| item.get("plan_months_total"))
            .and_then(Value::as_u64)
            .map(|raw| raw as u32)
            .unwrap_or(DEFAULT_SCHOOL_YEAR_MONTHS);
        let language = settings_value
            .and_then(|item| item.get("language"))
            .and_then(Value::as_str)
            .unwrap_or("EN")
            .to_string();
        let rent_monthly_manual = settings_value
            .and_then(|item| item.get("rent_monthly_manual"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let rent_base_monthly = settings_value
            .and_then(|item| item.get("rent_base_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(650.0);
        let food_house = settings_value
            .and_then(|item| item.get("food_house_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let misc = settings_value
            .and_then(|item| item.get("misc_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let medical = settings_value
            .and_then(|item| item.get("medical_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let school = settings_value
            .and_then(|item| item.get("school_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let household = settings_value
            .and_then(|item| item.get("household_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let health = settings_value
            .and_then(|item| item.get("health_monthly"))
            .and_then(Value::as_f64)
            .unwrap_or(0.0);

        let settings = legacy_app_settings(language, plan_months_total);
        replace_all_data(
            &mut conn,
            &json!({
                "settings": settings,
                "accounts": [],
                "ledger_entries": [],
                "recurring_rules": [],
                "monthly_caps": []
            }),
        )?;

        let account = create_primary_account(&conn, starting_balance)?;
        if let Some(entries) = value.get("transactions").and_then(Value::as_array) {
            for item in entries {
                let tx_type = item
                    .get("type")
                    .and_then(Value::as_str)
                    .unwrap_or("expense");
                let label = item.get("label").and_then(Value::as_str).unwrap_or("");
                let category = item
                    .get("category")
                    .and_then(Value::as_str)
                    .unwrap_or("misc");
                let notes = item.get("notes").and_then(Value::as_str).unwrap_or("");
                let entry_kind = legacy_kind(tx_type, label, category, notes);
                let occurred = item
                    .get("datetime_local")
                    .and_then(Value::as_str)
                    .map(|text| text.to_string())
                    .unwrap_or_else(now_local_iso);
                let entry = LedgerEntry {
                    id: item
                        .get("id")
                        .and_then(Value::as_str)
                        .map(|text| text.to_string())
                        .unwrap_or_else(|| Uuid::new_v4().to_string()),
                    account_id: account.id.clone(),
                    entry_kind: entry_kind.clone(),
                    amount: legacy_entry_amount(
                        &entry_kind,
                        tx_type,
                        item.get("amount").and_then(Value::as_f64).unwrap_or(0.0),
                    ),
                    occurred_at_local: occurred,
                    label: label.to_string(),
                    category: category.to_string(),
                    notes: notes.to_string(),
                    recurring_rule_id: item
                        .get("recurring_id")
                        .and_then(Value::as_str)
                        .map(|text| text.to_string()),
                    transfer_group_id: None,
                    exclude_from_insights: item
                        .get("excluded_from_averages")
                        .and_then(Value::as_bool)
                        .unwrap_or(false),
                };
                insert_entry_raw(&conn, &entry)?;
            }
        }

        let mut saw_rent_rule = false;
        if let Some(rules) = value.get("recurring_charges").and_then(Value::as_array) {
            for item in rules {
                let tx_type = item
                    .get("type")
                    .and_then(Value::as_str)
                    .unwrap_or("expense");
                let label = item.get("label").and_then(Value::as_str).unwrap_or("");
                let category = item
                    .get("category")
                    .and_then(Value::as_str)
                    .unwrap_or("misc");
                let notes = item.get("notes").and_then(Value::as_str).unwrap_or("");
                let entry_kind = legacy_kind(tx_type, label, category, notes);
                if is_rent_like(&format!("{label} {category} {notes}")) {
                    saw_rent_rule = true;
                }
                let rule = RecurringRule {
                    id: item
                        .get("id")
                        .and_then(Value::as_str)
                        .map(|text| text.to_string())
                        .unwrap_or_else(|| Uuid::new_v4().to_string()),
                    label: label.to_string(),
                    entry_kind,
                    amount: item
                        .get("amount")
                        .and_then(Value::as_f64)
                        .unwrap_or(0.0)
                        .abs(),
                    account_id: account.id.clone(),
                    category: category.to_string(),
                    notes: notes.to_string(),
                    start_date: item
                        .get("start_date")
                        .and_then(Value::as_str)
                        .unwrap_or("2026-09-01")
                        .to_string(),
                    end_date: item
                        .get("end_date")
                        .and_then(Value::as_str)
                        .map(|text| text.to_string()),
                    frequency: item
                        .get("frequency")
                        .and_then(Value::as_str)
                        .map(|raw| {
                            parse_frequency(raw.to_string()).unwrap_or(RecurringFrequency::Monthly)
                        })
                        .unwrap_or(RecurringFrequency::Monthly),
                    status: item
                        .get("status")
                        .and_then(Value::as_str)
                        .map(|raw| {
                            parse_status(raw.to_string()).unwrap_or(RecurringStatus::Automatic)
                        })
                        .unwrap_or(RecurringStatus::Automatic),
                    last_applied_local: item
                        .get("last_applied")
                        .and_then(Value::as_str)
                        .map(|text| text.to_string()),
                };
                insert_rule_raw(&conn, &rule)?;
            }
        }

        apply_legacy_planning_defaults(
            &conn,
            &account.id,
            &settings,
            saw_rent_rule,
            today_local(),
            rent_monthly_manual,
            rent_base_monthly,
            food_house,
            misc,
            medical,
            school,
            household,
            health,
        )?;
    }
    let retention = fetch_settings(&conn)?.backup_retention;
    let _ = backup_database(&state.env, retention)?;
    Ok(())
}

fn restore_backup_internal(state: &AppState, backup_path: &str) -> AppResult<()> {
    ensure_environment(state)?;
    let backup_path = validate_restore_backup_path(&state.env, Path::new(backup_path))?;

    let backup_conn = open_connection(&backup_path)?;
    let backup_payload = snapshot_payload(&backup_conn)?;
    let backup_value: Value = serde_json::from_str(&backup_payload)?;

    let mut conn = open_connection(&state.env.db_path)?;
    let previous = snapshot_payload(&conn)?;
    push_undo(state, UndoAction::RestoreSnapshot { payload: previous });
    replace_all_data(&mut conn, &backup_value)?;

    let retention = fetch_settings(&conn)?.backup_retention;
    let _ = backup_database(&state.env, retention)?;
    Ok(())
}

fn bootstrap_state_internal(state: &AppState) -> AppResult<BootstrapState> {
    ensure_environment(state)?;
    let mut conn = open_connection(&state.env.db_path)?;
    let auto_applied = apply_due_today_internal(&mut conn, today_local())?;
    let settings = fetch_settings(&conn)?;
    if auto_applied > 0 {
        let _ = backup_database(&state.env, settings.backup_retention)?;
    }
    Ok(BootstrapState {
        accounts: fetch_accounts(&conn)?,
        entries: fetch_entries(&conn)?,
        recurring_rules: fetch_recurring_rules(&conn)?,
        monthly_caps: fetch_monthly_caps(&conn)?,
        settings,
        insight_snapshot: calculate_snapshot(&conn)?,
        backup_files: list_backups_internal(&state.env)?,
        migration_status: migration_status(&conn, &state.env)?,
        recovery_notice: state
            .runtime
            .lock()
            .expect("runtime lock poisoned")
            .recovery_notice
            .clone(),
    })
}
#[tauri::command]
fn bootstrap_state(state: State<'_, AppState>) -> Result<BootstrapState, String> {
    bootstrap_state_internal(&state).map_err(|err| err.to_string())
}

#[tauri::command]
fn list_accounts(state: State<'_, AppState>) -> Result<Vec<Account>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    fetch_accounts(&conn).map_err(|err| err.to_string())
}

#[tauri::command]
fn create_account(
    state: State<'_, AppState>,
    input: CreateAccountInput,
) -> Result<Account, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let account = Account {
        id: Uuid::new_v4().to_string(),
        name: input.name,
        r#type: input.r#type,
        opening_balance: input.opening_balance,
        archived: false,
        created_at: now_local_iso(),
        current_balance: input.opening_balance,
    };
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    insert_account_raw(&conn, &account).map_err(|err| err.to_string())?;
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    push_undo(
        &state,
        UndoAction::ReplaceAccount {
            account_id: account.id.clone(),
            previous: None,
        },
    );
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(account)
}

#[tauri::command]
fn update_account(
    state: State<'_, AppState>,
    account_id: String,
    input: UpdateAccountInput,
) -> Result<Account, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let current = fetch_accounts(&conn)
        .map_err(|err| err.to_string())?
        .into_iter()
        .find(|account| account.id == account_id)
        .ok_or_else(|| "Account not found".to_string())?;
    let updated = Account {
        name: input.name.unwrap_or(current.name.clone()),
        r#type: input.r#type.unwrap_or(current.r#type.clone()),
        archived: input.archived.unwrap_or(current.archived),
        current_balance: current.current_balance,
        ..current.clone()
    };
    insert_account_raw(&conn, &updated).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceAccount {
            account_id,
            previous: Some(current),
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(updated)
}

#[tauri::command]
fn archive_account(state: State<'_, AppState>, account_id: String) -> Result<Account, String> {
    update_account(
        state,
        account_id,
        UpdateAccountInput {
            archived: Some(true),
            ..Default::default()
        },
    )
}

#[tauri::command]
fn list_entries(
    state: State<'_, AppState>,
    filters: EntryFilters,
) -> Result<Vec<LedgerEntry>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let entries = fetch_entries(&conn).map_err(|err| err.to_string())?;
    Ok(entries
        .into_iter()
        .filter(|entry| entry_matches_filters(entry, &filters))
        .collect())
}

#[tauri::command]
fn create_entry(
    state: State<'_, AppState>,
    input: CreateEntryInput,
) -> Result<LedgerEntry, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    if input.entry_kind == EntryKind::Transfer {
        return Err("Use create_transfer for linked transfers between accounts.".to_string());
    }
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    require_active_account(&conn, &input.account_id).map_err(|err| err.to_string())?;
    let entry = LedgerEntry {
        id: Uuid::new_v4().to_string(),
        account_id: input.account_id,
        entry_kind: input.entry_kind.clone(),
        amount: normalize_amount(&input.entry_kind, input.amount),
        occurred_at_local: input.occurred_at_local,
        label: input.label,
        category: input.category,
        notes: input.notes,
        recurring_rule_id: input.recurring_rule_id,
        transfer_group_id: None,
        exclude_from_insights: input.exclude_from_insights.unwrap_or(false),
    };
    insert_entry_raw(&conn, &entry).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::DeleteEntries {
            entry_ids: vec![entry.id.clone()],
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(entry)
}

#[tauri::command]
fn update_entry(
    state: State<'_, AppState>,
    entry_id: String,
    input: UpdateEntryInput,
) -> Result<LedgerEntry, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let previous = fetch_entry_by_id(&conn, &entry_id)
        .map_err(|err| err.to_string())?
        .ok_or_else(|| "Entry not found".to_string())?;
    if previous.entry_kind == EntryKind::Transfer {
        return Err(
            "Transfers must be deleted and recreated so both sides stay linked.".to_string(),
        );
    }
    if input.entry_kind == EntryKind::Transfer {
        return Err(
            "Transfers must be deleted and recreated so both sides stay linked.".to_string(),
        );
    }
    if input.account_id != previous.account_id {
        require_active_account(&conn, &input.account_id).map_err(|err| err.to_string())?;
    }
    let updated = LedgerEntry {
        account_id: input.account_id,
        entry_kind: input.entry_kind.clone(),
        amount: normalize_amount(&input.entry_kind, input.amount),
        occurred_at_local: input.occurred_at_local,
        label: input.label,
        category: input.category,
        notes: input.notes,
        exclude_from_insights: input.exclude_from_insights,
        ..previous.clone()
    };
    insert_entry_raw(&conn, &updated).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceEntry {
            entry_id,
            previous: Some(previous),
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(updated)
}

#[tauri::command]
fn delete_entry(state: State<'_, AppState>, entry_id: String) -> Result<(), String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let mut conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let previous = fetch_entry_by_id(&conn, &entry_id)
        .map_err(|err| err.to_string())?
        .ok_or_else(|| "Entry not found".to_string())?;
    if let Some(group_id) = previous.transfer_group_id.clone() {
        let snapshot = snapshot_payload(&conn).map_err(|err| err.to_string())?;
        let transfer_entries =
            fetch_entries_by_transfer_group(&conn, &group_id).map_err(|err| err.to_string())?;
        let tx = conn.transaction().map_err(|err| err.to_string())?;
        for transfer_entry in transfer_entries {
            delete_entry_raw(&tx, &transfer_entry.id).map_err(|err| err.to_string())?;
        }
        tx.commit().map_err(|err| err.to_string())?;
        push_undo(&state, UndoAction::RestoreSnapshot { payload: snapshot });
    } else {
        delete_entry_raw(&conn, &entry_id).map_err(|err| err.to_string())?;
        push_undo(&state, UndoAction::DeleteEntry { entry: previous });
    }
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(())
}

#[tauri::command]
fn create_transfer(
    state: State<'_, AppState>,
    input: CreateTransferInput,
) -> Result<Vec<LedgerEntry>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    if input.from_account_id == input.to_account_id {
        return Err("Transfer source and destination must be different accounts.".to_string());
    }
    if input.amount <= 0.0 {
        return Err("Transfer amount must be greater than zero.".to_string());
    }
    let mut conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    require_active_account(&conn, &input.from_account_id).map_err(|err| err.to_string())?;
    require_active_account(&conn, &input.to_account_id).map_err(|err| err.to_string())?;
    let group_id = Uuid::new_v4().to_string();
    let out_entry = LedgerEntry {
        id: Uuid::new_v4().to_string(),
        account_id: input.from_account_id,
        entry_kind: EntryKind::Transfer,
        amount: -input.amount.abs(),
        occurred_at_local: input.occurred_at_local.clone(),
        label: input.label.clone(),
        category: "transfer".to_string(),
        notes: input.notes.clone(),
        recurring_rule_id: None,
        transfer_group_id: Some(group_id.clone()),
        exclude_from_insights: true,
    };
    let in_entry = LedgerEntry {
        id: Uuid::new_v4().to_string(),
        account_id: input.to_account_id,
        entry_kind: EntryKind::Transfer,
        amount: input.amount.abs(),
        occurred_at_local: input.occurred_at_local,
        label: input.label,
        category: "transfer".to_string(),
        notes: input.notes,
        recurring_rule_id: None,
        transfer_group_id: Some(group_id),
        exclude_from_insights: true,
    };
    let tx = conn.transaction().map_err(|err| err.to_string())?;
    insert_entry_raw(&tx, &out_entry).map_err(|err| err.to_string())?;
    insert_entry_raw(&tx, &in_entry).map_err(|err| err.to_string())?;
    tx.commit().map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::DeleteEntries {
            entry_ids: vec![out_entry.id.clone(), in_entry.id.clone()],
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(vec![out_entry, in_entry])
}

#[tauri::command]
fn reconcile_account(
    state: State<'_, AppState>,
    input: ReconcileAccountInput,
) -> Result<LedgerEntry, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let account =
        require_active_account(&conn, &input.account_id).map_err(|err| err.to_string())?;
    let delta = input.actual_balance - account.current_balance;
    if delta.abs() < 0.005 {
        return Err("Account already matches the provided balance.".to_string());
    }
    let entry = LedgerEntry {
        id: Uuid::new_v4().to_string(),
        account_id: input.account_id,
        entry_kind: EntryKind::Adjustment,
        amount: delta,
        occurred_at_local: input.occurred_at_local,
        label: "Reconcile adjustment".to_string(),
        category: "adjustment".to_string(),
        notes: input.notes,
        recurring_rule_id: None,
        transfer_group_id: None,
        exclude_from_insights: true,
    };
    insert_entry_raw(&conn, &entry).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::DeleteEntries {
            entry_ids: vec![entry.id.clone()],
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(entry)
}
#[tauri::command]
fn list_recurring_rules(state: State<'_, AppState>) -> Result<Vec<RecurringRule>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    fetch_recurring_rules(&conn).map_err(|err| err.to_string())
}

#[tauri::command]
fn create_recurring_rule(
    state: State<'_, AppState>,
    input: RecurringRuleInput,
) -> Result<RecurringRule, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    if input.entry_kind == EntryKind::Transfer {
        return Err("Transfers cannot be created as recurring rules.".to_string());
    }
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    require_active_account(&conn, &input.account_id).map_err(|err| err.to_string())?;
    let rule = RecurringRule {
        id: Uuid::new_v4().to_string(),
        label: input.label,
        entry_kind: input.entry_kind,
        amount: input.amount.abs(),
        account_id: input.account_id,
        category: input.category,
        notes: input.notes,
        start_date: input.start_date,
        end_date: input.end_date,
        frequency: input.frequency,
        status: input.status,
        last_applied_local: None,
    };
    insert_rule_raw(&conn, &rule).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceRecurring {
            rule_id: rule.id.clone(),
            previous: None,
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(rule)
}

#[tauri::command]
fn update_recurring_rule(
    state: State<'_, AppState>,
    rule_id: String,
    input: RecurringRuleInput,
) -> Result<RecurringRule, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    if input.entry_kind == EntryKind::Transfer {
        return Err("Transfers cannot be created as recurring rules.".to_string());
    }
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    require_active_account(&conn, &input.account_id).map_err(|err| err.to_string())?;
    let current = fetch_recurring_rules(&conn)
        .map_err(|err| err.to_string())?
        .into_iter()
        .find(|rule| rule.id == rule_id)
        .ok_or_else(|| "Recurring rule not found".to_string())?;
    let updated = RecurringRule {
        id: current.id.clone(),
        label: input.label,
        entry_kind: input.entry_kind,
        amount: input.amount.abs(),
        account_id: input.account_id,
        category: input.category,
        notes: input.notes,
        start_date: input.start_date,
        end_date: input.end_date,
        frequency: input.frequency,
        status: input.status,
        last_applied_local: current.last_applied_local.clone(),
    };
    insert_rule_raw(&conn, &updated).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceRecurring {
            rule_id,
            previous: Some(current),
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(updated)
}

#[tauri::command]
fn delete_recurring_rule(state: State<'_, AppState>, rule_id: String) -> Result<(), String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let current = fetch_recurring_rules(&conn)
        .map_err(|err| err.to_string())?
        .into_iter()
        .find(|rule| rule.id == rule_id)
        .ok_or_else(|| "Recurring rule not found".to_string())?;
    delete_rule_raw(&conn, &rule_id).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceRecurring {
            rule_id,
            previous: Some(current),
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(())
}

#[tauri::command]
fn apply_recurring_rule_now(state: State<'_, AppState>, rule_id: String) -> Result<usize, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let mut conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let rule = fetch_recurring_rules(&conn)
        .map_err(|err| err.to_string())?
        .into_iter()
        .find(|rule| rule.id == rule_id)
        .ok_or_else(|| "Recurring rule not found".to_string())?;
    require_active_account(&conn, &rule.account_id).map_err(|err| err.to_string())?;
    let applied =
        apply_rule_dates(&mut conn, &rule, &[today_local()]).map_err(|err| err.to_string())?;
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(applied)
}

#[tauri::command]
fn list_monthly_caps(state: State<'_, AppState>) -> Result<Vec<MonthlyCap>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    fetch_monthly_caps(&conn).map_err(|err| err.to_string())
}

#[tauri::command]
fn set_monthly_cap(
    state: State<'_, AppState>,
    input: MonthlyCapInput,
) -> Result<MonthlyCap, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let current = fetch_monthly_caps(&conn)
        .map_err(|err| err.to_string())?
        .into_iter()
        .find(|cap| cap.category == input.category && cap.month_key == input.month_key);
    let cap = MonthlyCap {
        id: current
            .as_ref()
            .map(|item| item.id.clone())
            .unwrap_or_else(|| Uuid::new_v4().to_string()),
        category: input.category,
        amount: input.amount,
        month_key: input.month_key,
    };
    insert_cap_raw(&conn, &cap).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceCap {
            cap_id: cap.id.clone(),
            previous: current,
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(cap)
}

#[tauri::command]
fn delete_monthly_cap(state: State<'_, AppState>, cap_id: String) -> Result<(), String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let current = fetch_monthly_caps(&conn)
        .map_err(|err| err.to_string())?
        .into_iter()
        .find(|cap| cap.id == cap_id)
        .ok_or_else(|| "Monthly cap not found".to_string())?;
    delete_cap_raw(&conn, &cap_id).map_err(|err| err.to_string())?;
    push_undo(
        &state,
        UndoAction::ReplaceCap {
            cap_id,
            previous: Some(current),
        },
    );
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_insights(
    state: State<'_, AppState>,
    range: Option<String>,
    filters: Option<EntryFilters>,
) -> Result<InsightSnapshot, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    calculate_snapshot_for_query(&conn, range, filters).map_err(|err| err.to_string())
}

#[tauri::command]
fn get_calculation_breakdown(
    state: State<'_, AppState>,
    metric_id: String,
    context: Option<Value>,
) -> Result<BreakdownResult, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    breakdown_for_metric(&conn, &metric_id, context).map_err(|err| err.to_string())
}

#[tauri::command]
fn run_startup_recurring_check(
    state: State<'_, AppState>,
) -> Result<Vec<MissedRecurringOccurrence>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    preview_missed_internal(&conn, today_local()).map_err(|err| err.to_string())
}

#[tauri::command]
fn apply_missed_recurring(
    state: State<'_, AppState>,
    recurring_rule_ids: Option<Vec<String>>,
) -> Result<usize, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let mut conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let ids = recurring_rule_ids.map(|list| list.into_iter().collect::<HashSet<_>>());
    let applied =
        apply_missed_internal(&mut conn, today_local(), ids).map_err(|err| err.to_string())?;
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(applied)
}

#[tauri::command]
fn export_json_v2(state: State<'_, AppState>, path: String) -> Result<(), String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let payload = snapshot_payload(&conn).map_err(|err| err.to_string())?;
    fs::write(path, payload).map_err(|err| err.to_string())
}

#[tauri::command]
fn import_json(state: State<'_, AppState>, path: String) -> Result<(), String> {
    import_json_internal(&state, &path).map_err(|err| err.to_string())
}

#[tauri::command]
fn run_legacy_migration(state: State<'_, AppState>) -> Result<MigrationStatus, String> {
    run_legacy_migration_internal(&state).map_err(|err| err.to_string())
}

#[tauri::command]
fn list_backups(state: State<'_, AppState>) -> Result<Vec<BackupFile>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    list_backups_internal(&state.env).map_err(|err| err.to_string())
}

#[tauri::command]
fn update_app_settings(
    state: State<'_, AppState>,
    input: UpdateSettingsInput,
) -> Result<AppSettings, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    validate_settings_input(&input).map_err(|err| err.to_string())?;

    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let current = fetch_settings(&conn).map_err(|err| err.to_string())?;
    let updated = AppSettings {
        school_year_start_month: input.school_year_start_month,
        school_year_months: input.school_year_months,
        language: current.language,
        backup_retention: input.backup_retention,
        last_migration_version: current.last_migration_version,
    };

    update_settings_row(&conn, &updated).map_err(|err| err.to_string())?;
    let _ = backup_database(&state.env, updated.backup_retention).map_err(|err| err.to_string())?;
    Ok(updated)
}

#[tauri::command]
fn create_backup_now(state: State<'_, AppState>) -> Result<Option<BackupFile>, String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    backup_database(&state.env, retention).map_err(|err| err.to_string())
}

#[tauri::command]
fn restore_backup(state: State<'_, AppState>, backup_path: String) -> Result<(), String> {
    restore_backup_internal(&state, &backup_path).map_err(|err| err.to_string())
}

#[tauri::command]
fn reset_all_data(state: State<'_, AppState>) -> Result<(), String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let mut conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    let previous = snapshot_payload(&conn).map_err(|err| err.to_string())?;
    push_undo(&state, UndoAction::RestoreSnapshot { payload: previous });
    replace_all_data(
        &mut conn,
        &json!({
            "settings": AppSettings {
                school_year_start_month: DEFAULT_SCHOOL_YEAR_START_MONTH,
                school_year_months: DEFAULT_SCHOOL_YEAR_MONTHS,
                language: "EN".to_string(),
                backup_retention: DEFAULT_BACKUP_RETENTION,
                last_migration_version: CURRENT_MIGRATION_VERSION,
            },
            "accounts": [],
            "ledger_entries": [],
            "recurring_rules": [],
            "monthly_caps": []
        }),
    )
    .map_err(|err| err.to_string())?;
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(())
}

#[tauri::command]
fn undo_last_action(state: State<'_, AppState>) -> Result<(), String> {
    ensure_environment(&state).map_err(|err| err.to_string())?;
    let action = {
        let mut runtime = state.runtime.lock().expect("runtime lock poisoned");
        runtime.undo_stack.pop()
    };
    let Some(action) = action else {
        return Ok(());
    };
    let mut conn = open_connection(&state.env.db_path).map_err(|err| err.to_string())?;
    match action {
        UndoAction::ReplaceEntry { entry_id, previous } => {
            if let Some(entry) = previous {
                insert_entry_raw(&conn, &entry).map_err(|err| err.to_string())?;
            } else {
                delete_entry_raw(&conn, &entry_id).map_err(|err| err.to_string())?;
            }
        }
        UndoAction::DeleteEntry { entry } => {
            insert_entry_raw(&conn, &entry).map_err(|err| err.to_string())?;
        }
        UndoAction::DeleteEntries { entry_ids } => {
            for entry_id in entry_ids {
                delete_entry_raw(&conn, &entry_id).map_err(|err| err.to_string())?;
            }
        }
        UndoAction::ReplaceRecurring { rule_id, previous } => {
            if let Some(rule) = previous {
                insert_rule_raw(&conn, &rule).map_err(|err| err.to_string())?;
            } else {
                delete_rule_raw(&conn, &rule_id).map_err(|err| err.to_string())?;
            }
        }
        UndoAction::ReplaceCap { cap_id, previous } => {
            if let Some(cap) = previous {
                insert_cap_raw(&conn, &cap).map_err(|err| err.to_string())?;
            } else {
                delete_cap_raw(&conn, &cap_id).map_err(|err| err.to_string())?;
            }
        }
        UndoAction::ReplaceAccount {
            account_id,
            previous,
        } => {
            if let Some(account) = previous {
                insert_account_raw(&conn, &account).map_err(|err| err.to_string())?;
            } else {
                delete_account_raw(&conn, &account_id).map_err(|err| err.to_string())?;
            }
        }
        UndoAction::RestoreSnapshot { payload } => {
            let value: Value = serde_json::from_str(&payload).map_err(|err| err.to_string())?;
            replace_all_data(&mut conn, &value).map_err(|err| err.to_string())?;
        }
    }
    let retention = fetch_settings(&conn)
        .map_err(|err| err.to_string())?
        .backup_retention;
    let _ = backup_database(&state.env, retention).map_err(|err| err.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value as JsonValue;

    fn make_test_env(base_dir: &Path) -> AppEnv {
        AppEnv {
            data_dir: base_dir.to_path_buf(),
            db_path: base_dir.join("budget.db"),
            backups_dir: base_dir.join("backups"),
            legacy_db_path: base_dir.join("legacy.db"),
        }
    }

    fn make_test_state(base_dir: &Path) -> AppState {
        AppState::new(make_test_env(base_dir))
    }

    fn temp_test_dir(prefix: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("{prefix}_{}", Uuid::new_v4()));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn normalize_export_payload(payload: &str) -> JsonValue {
        let mut value: JsonValue = serde_json::from_str(payload).unwrap();
        if let Some(object) = value.as_object_mut() {
            object.remove("exported_at");
        }
        value
    }

    fn seed_legacy_fixture_db(path: &Path) {
        let conn = Connection::open(path).unwrap();
        conn.execute_batch(include_str!("../tests/fixtures/legacy_budget_fixture.sql"))
            .unwrap();
    }

    #[derive(Debug, Default, PartialEq, Eq)]
    struct KindTally {
        expense: usize,
        funding: usize,
        rent_credit: usize,
        adjustment: usize,
    }

    fn bump_tally(tally: &mut KindTally, kind: &EntryKind) {
        match kind {
            EntryKind::Expense => tally.expense += 1,
            EntryKind::Funding => tally.funding += 1,
            EntryKind::RentCredit => tally.rent_credit += 1,
            EntryKind::Adjustment => tally.adjustment += 1,
            EntryKind::Transfer => {}
        }
    }

    fn tally_entries(entries: &[LedgerEntry]) -> KindTally {
        let mut tally = KindTally::default();
        for entry in entries {
            bump_tally(&mut tally, &entry.entry_kind);
        }
        tally
    }

    fn tally_rules(rules: &[RecurringRule]) -> KindTally {
        let mut tally = KindTally::default();
        for rule in rules {
            bump_tally(&mut tally, &rule.entry_kind);
        }
        tally
    }

    #[test]
    fn expense_reduces_balance() {
        let entry = LedgerEntry {
            id: "1".into(),
            account_id: "a".into(),
            entry_kind: EntryKind::Expense,
            amount: 42.0,
            occurred_at_local: "2026-04-19T10:00:00".into(),
            label: "groceries".into(),
            category: "food".into(),
            notes: "".into(),
            recurring_rule_id: None,
            transfer_group_id: None,
            exclude_from_insights: false,
        };
        assert_eq!(entry_effect(&entry), -42.0);
    }

    #[test]
    fn rent_credit_increases_balance() {
        let entry = LedgerEntry {
            id: "1".into(),
            account_id: "a".into(),
            entry_kind: EntryKind::RentCredit,
            amount: 200.0,
            occurred_at_local: "2026-04-19T10:00:00".into(),
            label: "room rent".into(),
            category: "rent".into(),
            notes: "".into(),
            recurring_rule_id: None,
            transfer_group_id: None,
            exclude_from_insights: false,
        };
        assert_eq!(entry_effect(&entry), 200.0);
    }

    #[test]
    fn adjustment_keeps_signed_effect() {
        let entry = LedgerEntry {
            id: "1".into(),
            account_id: "a".into(),
            entry_kind: EntryKind::Adjustment,
            amount: -35.5,
            occurred_at_local: "2026-04-19T10:00:00".into(),
            label: "reconcile".into(),
            category: "adjustment".into(),
            notes: "".into(),
            recurring_rule_id: None,
            transfer_group_id: None,
            exclude_from_insights: true,
        };
        assert_eq!(entry_effect(&entry), -35.5);
        assert_eq!(normalize_amount(&EntryKind::Adjustment, -35.5), -35.5);
    }

    #[test]
    fn legacy_adjustment_amount_follows_legacy_transaction_direction() {
        assert_eq!(
            legacy_entry_amount(&EntryKind::Adjustment, "expense", 40.0),
            -40.0
        );
        assert_eq!(
            legacy_entry_amount(&EntryKind::Adjustment, "income", 40.0),
            40.0
        );
    }

    #[test]
    fn monthly_schedule_keeps_same_day_when_possible() {
        let rule = RecurringRule {
            id: "rule-1".into(),
            label: "Rent".into(),
            entry_kind: EntryKind::Expense,
            amount: 650.0,
            account_id: "a".into(),
            category: "rent".into(),
            notes: "".into(),
            start_date: "2026-01-31".into(),
            end_date: None,
            frequency: RecurringFrequency::Monthly,
            status: RecurringStatus::Automatic,
            last_applied_local: None,
        };
        let dates = scheduled_dates(
            &rule,
            parse_date("2026-01-01").unwrap(),
            parse_date("2026-03-31").unwrap(),
        )
        .unwrap();
        assert_eq!(dates[0].format("%Y-%m-%d").to_string(), "2026-01-31");
        assert_eq!(dates[1].format("%Y-%m-%d").to_string(), "2026-02-28");
    }

    #[test]
    fn school_year_months_default_to_september_start() {
        let settings = AppSettings {
            school_year_start_month: 9,
            school_year_months: 9,
            language: "EN".into(),
            backup_retention: 50,
            last_migration_version: 2,
        };
        let months = school_year_month_keys(&settings, parse_date("2026-04-19").unwrap());
        assert_eq!(months.first().unwrap(), "2025-09");
        assert_eq!(months.last().unwrap(), "2026-05");
    }

    #[test]
    fn planning_window_months_follow_the_focus_month_forward() {
        let settings = AppSettings {
            school_year_start_month: 9,
            school_year_months: 5,
            language: "EN".into(),
            backup_retention: 50,
            last_migration_version: 2,
        };

        let query = resolve_snapshot_query(
            &settings,
            None,
            Some(EntryFilters {
                month_key: Some("2026-04".into()),
                ..Default::default()
            }),
        )
        .unwrap();

        assert_eq!(
            query.range_months,
            vec![
                "2026-04".to_string(),
                "2026-05".to_string(),
                "2026-06".to_string(),
                "2026-07".to_string(),
                "2026-08".to_string()
            ]
        );
    }

    #[test]
    fn settings_validation_rejects_out_of_range_values() {
        assert!(validate_settings_input(&UpdateSettingsInput {
            school_year_start_month: 0,
            school_year_months: 9,
            backup_retention: 50,
        })
        .is_err());
        assert!(validate_settings_input(&UpdateSettingsInput {
            school_year_start_month: 9,
            school_year_months: 13,
            backup_retention: 50,
        })
        .is_err());
        assert!(validate_settings_input(&UpdateSettingsInput {
            school_year_start_month: 9,
            school_year_months: 9,
            backup_retention: 0,
        })
        .is_err());
    }

    #[test]
    fn require_active_account_rejects_archived_accounts() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "archived-account".into(),
                name: "Archived".into(),
                r#type: AccountType::Checking,
                opening_balance: 100.0,
                archived: true,
                created_at: "2026-04-20T10:00:00".into(),
                current_balance: 100.0,
            },
        )
        .unwrap();

        let result = require_active_account(&conn, "archived-account");

        assert!(result.is_err());
    }

    #[test]
    fn list_backups_internal_only_returns_db_files() {
        let base_dir = std::env::temp_dir().join(format!("sbt_backup_test_{}", Uuid::new_v4()));
        let backups_dir = base_dir.join("backups");
        fs::create_dir_all(&backups_dir).unwrap();
        fs::write(backups_dir.join("budget_1.db"), b"db").unwrap();
        fs::write(backups_dir.join("notes.txt"), b"text").unwrap();
        fs::create_dir_all(backups_dir.join("nested")).unwrap();

        let env = AppEnv {
            data_dir: base_dir.clone(),
            db_path: base_dir.join("budget.db"),
            backups_dir,
            legacy_db_path: base_dir.join("legacy.db"),
        };

        let backups = list_backups_internal(&env).unwrap();

        assert_eq!(backups.len(), 1);
        assert_eq!(backups[0].file_name, "budget_1.db");
        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn validate_or_recover_db_accepts_existing_valid_database() {
        let base_dir = temp_test_dir("sbt_validate_existing_db");
        let env = make_test_env(&base_dir);
        let conn = open_connection(&env.db_path).unwrap();
        init_schema(&conn).unwrap();
        drop(conn);

        let notice = validate_or_recover_db(&env).unwrap();

        assert!(notice.is_none());
        assert!(env.db_path.exists());

        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn validate_or_recover_db_restores_backup_after_query_failure() {
        let base_dir = temp_test_dir("sbt_validate_recover_db");
        let env = make_test_env(&base_dir);
        fs::create_dir_all(&env.backups_dir).unwrap();

        let backup_path = env.backups_dir.join("budget_20990101_000000.db");
        let backup_conn = open_connection(&backup_path).unwrap();
        init_schema(&backup_conn).unwrap();
        insert_account_raw(
            &backup_conn,
            &Account {
                id: "recovered-account".into(),
                name: "Recovered Checking".into(),
                r#type: AccountType::Checking,
                opening_balance: 410.0,
                archived: false,
                created_at: "2026-04-20T08:00:00".into(),
                current_balance: 410.0,
            },
        )
        .unwrap();
        drop(backup_conn);

        fs::write(&env.db_path, b"not-a-sqlite-database").unwrap();

        let notice = validate_or_recover_db(&env).unwrap();

        assert!(notice.is_some());
        assert!(notice.unwrap().contains("restored from backup"));

        let live_conn = open_connection(&env.db_path).unwrap();
        let recovered_accounts = fetch_accounts(&live_conn).unwrap();
        drop(live_conn);

        assert_eq!(recovered_accounts.len(), 1);
        assert_eq!(recovered_accounts[0].name, "Recovered Checking");
        assert!(
            fs::read_dir(&base_dir)
                .unwrap()
                .filter_map(|entry| entry.ok().map(|item| item.file_name()))
                .any(|name| name.to_string_lossy().starts_with("budget_corrupt_")),
            "Expected the corrupt live database to be preserved alongside recovery"
        );

        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn preview_missed_internal_ignores_archived_account_rules() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "archived-account".into(),
                name: "Archived".into(),
                r#type: AccountType::Checking,
                opening_balance: 0.0,
                archived: true,
                created_at: "2026-01-01T09:00:00".into(),
                current_balance: 0.0,
            },
        )
        .unwrap();
        insert_rule_raw(
            &conn,
            &RecurringRule {
                id: "rule-1".into(),
                label: "Archived rent".into(),
                entry_kind: EntryKind::Expense,
                amount: 500.0,
                account_id: "archived-account".into(),
                category: "rent".into(),
                notes: "".into(),
                start_date: "2026-01-01".into(),
                end_date: None,
                frequency: RecurringFrequency::Monthly,
                status: RecurringStatus::Automatic,
                last_applied_local: None,
            },
        )
        .unwrap();

        let missed = preview_missed_internal(&conn, parse_date("2026-04-20").unwrap()).unwrap();

        assert!(missed.is_empty());
    }

    #[test]
    fn calculate_snapshot_ignores_archived_account_rules_in_rent_due() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "archived-account".into(),
                name: "Archived".into(),
                r#type: AccountType::Checking,
                opening_balance: 1000.0,
                archived: true,
                created_at: "2026-01-01T09:00:00".into(),
                current_balance: 1000.0,
            },
        )
        .unwrap();
        insert_rule_raw(
            &conn,
            &RecurringRule {
                id: "rule-1".into(),
                label: "Archived rent".into(),
                entry_kind: EntryKind::Expense,
                amount: 500.0,
                account_id: "archived-account".into(),
                category: "rent".into(),
                notes: "".into(),
                start_date: "2026-01-01".into(),
                end_date: None,
                frequency: RecurringFrequency::Monthly,
                status: RecurringStatus::Automatic,
                last_applied_local: None,
            },
        )
        .unwrap();

        let snapshot = calculate_snapshot(&conn).unwrap();

        assert_eq!(snapshot.rent_due_this_month, 0.0);
    }

    #[test]
    fn calculate_snapshot_excludes_archived_accounts_from_live_cash() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "active-account".into(),
                name: "Checking".into(),
                r#type: AccountType::Checking,
                opening_balance: 125.0,
                archived: false,
                created_at: "2026-01-01T09:00:00".into(),
                current_balance: 125.0,
            },
        )
        .unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "archived-account".into(),
                name: "Old account".into(),
                r#type: AccountType::Savings,
                opening_balance: 900.0,
                archived: true,
                created_at: "2026-01-02T09:00:00".into(),
                current_balance: 900.0,
            },
        )
        .unwrap();

        let snapshot = calculate_snapshot(&conn).unwrap();

        assert_eq!(snapshot.total_available_cash, 125.0);
        assert_eq!(snapshot.account_balances.len(), 1);
        assert_eq!(snapshot.account_balances[0].label, "Checking");
        assert_eq!(snapshot.account_balances[0].value, 125.0);
        assert_eq!(
            snapshot.breakdowns["total_available_cash"][0],
            "Active accounts total = 125"
        );
    }

    #[test]
    fn validate_restore_backup_path_rejects_files_outside_backups_dir() {
        let base_dir = std::env::temp_dir().join(format!("sbt_restore_test_{}", Uuid::new_v4()));
        let backups_dir = base_dir.join("backups");
        let outside_file = base_dir.join("outside.db");
        fs::create_dir_all(&backups_dir).unwrap();
        fs::write(base_dir.join("budget.db"), b"live-db").unwrap();
        fs::write(&outside_file, b"backup-db").unwrap();

        let env = AppEnv {
            data_dir: base_dir.clone(),
            db_path: base_dir.join("budget.db"),
            backups_dir,
            legacy_db_path: base_dir.join("legacy.db"),
        };

        let result = validate_restore_backup_path(&env, &outside_file);

        assert!(result.is_err());
        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn validate_restore_backup_path_accepts_db_files_in_backups_dir() {
        let base_dir = std::env::temp_dir().join(format!("sbt_restore_test_{}", Uuid::new_v4()));
        let backups_dir = base_dir.join("backups");
        let backup_file = backups_dir.join("budget_20260420_100000.db");
        fs::create_dir_all(&backups_dir).unwrap();
        fs::write(base_dir.join("budget.db"), b"live-db").unwrap();
        fs::write(&backup_file, b"backup-db").unwrap();

        let env = AppEnv {
            data_dir: base_dir.clone(),
            db_path: base_dir.join("budget.db"),
            backups_dir,
            legacy_db_path: base_dir.join("legacy.db"),
        };

        let result = validate_restore_backup_path(&env, &backup_file);

        assert!(result.is_ok());
        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn calculate_snapshot_for_query_respects_account_filter_and_range() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "account-a".into(),
                name: "Checking".into(),
                r#type: AccountType::Checking,
                opening_balance: 100.0,
                archived: false,
                created_at: "2026-01-01T09:00:00".into(),
                current_balance: 100.0,
            },
        )
        .unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "account-b".into(),
                name: "Travel".into(),
                r#type: AccountType::Savings,
                opening_balance: 50.0,
                archived: false,
                created_at: "2026-01-02T09:00:00".into(),
                current_balance: 50.0,
            },
        )
        .unwrap();
        insert_entry_raw(
            &conn,
            &LedgerEntry {
                id: "a-funding".into(),
                account_id: "account-a".into(),
                entry_kind: EntryKind::Funding,
                amount: 500.0,
                occurred_at_local: "2026-03-01T10:00:00".into(),
                label: "Support".into(),
                category: "income".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_entry_raw(
            &conn,
            &LedgerEntry {
                id: "a-expense-march".into(),
                account_id: "account-a".into(),
                entry_kind: EntryKind::Expense,
                amount: 60.0,
                occurred_at_local: "2026-03-05T10:00:00".into(),
                label: "Groceries".into(),
                category: "food".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_entry_raw(
            &conn,
            &LedgerEntry {
                id: "a-rent-credit-march".into(),
                account_id: "account-a".into(),
                entry_kind: EntryKind::RentCredit,
                amount: 100.0,
                occurred_at_local: "2026-03-06T10:00:00".into(),
                label: "Tenant".into(),
                category: "rent".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_entry_raw(
            &conn,
            &LedgerEntry {
                id: "a-expense-feb".into(),
                account_id: "account-a".into(),
                entry_kind: EntryKind::Expense,
                amount: 40.0,
                occurred_at_local: "2026-02-05T10:00:00".into(),
                label: "Books".into(),
                category: "school".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_entry_raw(
            &conn,
            &LedgerEntry {
                id: "b-expense-march".into(),
                account_id: "account-b".into(),
                entry_kind: EntryKind::Expense,
                amount: 200.0,
                occurred_at_local: "2026-03-07T10:00:00".into(),
                label: "Trip".into(),
                category: "travel".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_rule_raw(
            &conn,
            &RecurringRule {
                id: "rent-rule-a".into(),
                label: "Rent".into(),
                entry_kind: EntryKind::Expense,
                amount: 300.0,
                account_id: "account-a".into(),
                category: "rent".into(),
                notes: "".into(),
                start_date: "2026-01-01".into(),
                end_date: None,
                frequency: RecurringFrequency::Monthly,
                status: RecurringStatus::Automatic,
                last_applied_local: None,
            },
        )
        .unwrap();
        insert_cap_raw(
            &conn,
            &MonthlyCap {
                id: "march-food".into(),
                category: "food".into(),
                amount: 150.0,
                month_key: "2026-03".into(),
            },
        )
        .unwrap();

        let snapshot = calculate_snapshot_for_query(
            &conn,
            Some("2026-03".into()),
            Some(EntryFilters {
                account_id: Some("account-a".into()),
                ..Default::default()
            }),
        )
        .unwrap();

        assert_eq!(snapshot.total_available_cash, 600.0);
        assert_eq!(snapshot.this_month_spend, 60.0);
        assert_eq!(snapshot.rent_credit_this_month, 100.0);
        assert_eq!(snapshot.monthly_series.len(), 1);
        assert_eq!(snapshot.monthly_series[0].month_key, "2026-03");
        assert_eq!(snapshot.monthly_series[0].spent, 60.0);
        assert_eq!(snapshot.monthly_series[0].cap, 150.0);
        assert_eq!(snapshot.rent_due_this_month, 300.0);
        assert_eq!(snapshot.account_balances.len(), 1);
        assert_eq!(snapshot.account_balances[0].label, "Checking");
        assert_eq!(snapshot.activity_groups.len(), 1);
        assert_eq!(snapshot.activity_groups[0].month_key, "2026-03");
        assert_eq!(snapshot.activity_groups[0].total_expense, 60.0);
    }

    #[test]
    fn breakdown_for_metric_uses_month_context() {
        let conn = Connection::open_in_memory().unwrap();
        init_schema(&conn).unwrap();
        insert_account_raw(
            &conn,
            &Account {
                id: "account-a".into(),
                name: "Checking".into(),
                r#type: AccountType::Checking,
                opening_balance: 100.0,
                archived: false,
                created_at: "2026-01-01T09:00:00".into(),
                current_balance: 100.0,
            },
        )
        .unwrap();
        insert_entry_raw(
            &conn,
            &LedgerEntry {
                id: "march-expense".into(),
                account_id: "account-a".into(),
                entry_kind: EntryKind::Expense,
                amount: 85.0,
                occurred_at_local: "2026-03-05T10:00:00".into(),
                label: "Groceries".into(),
                category: "food".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_cap_raw(
            &conn,
            &MonthlyCap {
                id: "march-food".into(),
                category: "food".into(),
                amount: 120.0,
                month_key: "2026-03".into(),
            },
        )
        .unwrap();

        let breakdown = breakdown_for_metric(
            &conn,
            "monthly_spend",
            Some(serde_json::json!({
                "range": "2026-03",
                "month_key": "2026-03",
                "account_id": "account-a"
            })),
        )
        .unwrap();

        assert_eq!(breakdown.title, "Monthly detail (2026-03)");
        assert!(breakdown
            .lines
            .iter()
            .any(|line| line == "Graph spend = 85"));
        assert!(breakdown
            .lines
            .iter()
            .any(|line| line == "Ledger expense = 85"));
        assert!(breakdown.lines.iter().any(|line| line == "Cap = 120"));
    }

    #[test]
    fn legacy_json_import_fixture_preserves_kind_mapping_and_exclusions() {
        let base_dir = temp_test_dir("sbt_legacy_json_fixture");
        let state = make_test_state(&base_dir);
        ensure_environment(&state).unwrap();

        let json_path = base_dir.join("legacy_import.json");
        fs::write(
            &json_path,
            include_str!("../tests/fixtures/legacy_import_mixed.json"),
        )
        .unwrap();

        import_json_internal(&state, &json_path.to_string_lossy()).unwrap();

        let conn = open_connection(&state.env.db_path).unwrap();
        let accounts = fetch_accounts(&conn).unwrap();
        let entries = fetch_entries(&conn).unwrap();
        let rules = fetch_recurring_rules(&conn).unwrap();

        assert_eq!(accounts.len(), 1);
        assert_eq!(accounts[0].name, "Primary Account");
        assert_eq!(accounts[0].opening_balance, 320.0);
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == "legacy-json-funding")
                .unwrap()
                .entry_kind,
            EntryKind::Funding
        );
        let rent_credit = entries
            .iter()
            .find(|entry| entry.id == "legacy-json-rent-credit")
            .unwrap();
        assert_eq!(rent_credit.entry_kind, EntryKind::RentCredit);
        assert!(rent_credit.exclude_from_insights);
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == "legacy-json-adjustment")
                .unwrap()
                .amount,
            -13.5
        );
        assert_eq!(rules.len(), 3);
        assert_eq!(
            rules
                .iter()
                .find(|rule| rule.id == "legacy-json-rec-funding")
                .unwrap()
                .entry_kind,
            EntryKind::Funding
        );
        assert_eq!(
            rules
                .iter()
                .find(|rule| rule.id == "legacy-json-rec-rent-credit")
                .unwrap()
                .entry_kind,
            EntryKind::RentCredit
        );

        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn legacy_db_migration_fixture_creates_primary_account_and_rent_plan() {
        let base_dir = temp_test_dir("sbt_legacy_db_fixture");
        let state = make_test_state(&base_dir);
        fs::create_dir_all(&state.env.backups_dir).unwrap();
        seed_legacy_fixture_db(&state.env.legacy_db_path);

        let status = run_legacy_migration_internal(&state).unwrap();
        let conn = open_connection(&state.env.db_path).unwrap();
        let accounts = fetch_accounts(&conn).unwrap();
        let entries = fetch_entries(&conn).unwrap();
        let rules = fetch_recurring_rules(&conn).unwrap();
        let caps = fetch_monthly_caps(&conn).unwrap();

        assert!(status.has_legacy_db);
        assert!(status.has_run);
        assert_eq!(accounts.len(), 1);
        assert_eq!(accounts[0].name, "Primary Account");
        assert_eq!(accounts[0].opening_balance, 915.25);
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == "legacy-funding-1")
                .unwrap()
                .entry_kind,
            EntryKind::Funding
        );
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == "legacy-rent-credit-1")
                .unwrap()
                .entry_kind,
            EntryKind::RentCredit
        );
        assert!(
            entries
                .iter()
                .find(|entry| entry.id == "legacy-rent-credit-1")
                .unwrap()
                .exclude_from_insights
        );
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == "legacy-adjustment-1")
                .unwrap()
                .amount,
            -23.75
        );
        assert_eq!(
            rules
                .iter()
                .find(|rule| rule.id == "legacy-rec-funding-1")
                .unwrap()
                .entry_kind,
            EntryKind::Funding
        );
        assert!(rules.iter().any(|rule| rule.label == "Migrated Rent Plan"));
        assert!(caps.iter().any(|cap| cap.category == "food"));
        assert!(caps.iter().any(|cap| cap.category == "school"));

        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn schema_v2_export_roundtrip_preserves_budget_data() {
        let source_dir = temp_test_dir("sbt_export_source");
        let source_state = make_test_state(&source_dir);
        ensure_environment(&source_state).unwrap();

        let source_conn = open_connection(&source_state.env.db_path).unwrap();
        update_settings_row(
            &source_conn,
            &AppSettings {
                school_year_start_month: 9,
                school_year_months: 9,
                language: "EN".into(),
                backup_retention: 50,
                last_migration_version: CURRENT_MIGRATION_VERSION,
            },
        )
        .unwrap();
        insert_account_raw(
            &source_conn,
            &Account {
                id: "primary".into(),
                name: "Primary Account".into(),
                r#type: AccountType::Checking,
                opening_balance: 250.0,
                archived: false,
                created_at: "2026-01-01T09:00:00".into(),
                current_balance: 250.0,
            },
        )
        .unwrap();
        insert_entry_raw(
            &source_conn,
            &LedgerEntry {
                id: "entry-expense".into(),
                account_id: "primary".into(),
                entry_kind: EntryKind::Expense,
                amount: 65.0,
                occurred_at_local: "2026-03-04T10:00:00".into(),
                label: "Food".into(),
                category: "food".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: false,
            },
        )
        .unwrap();
        insert_entry_raw(
            &source_conn,
            &LedgerEntry {
                id: "entry-rent-credit".into(),
                account_id: "primary".into(),
                entry_kind: EntryKind::RentCredit,
                amount: 120.0,
                occurred_at_local: "2026-03-05T10:00:00".into(),
                label: "Tenant share".into(),
                category: "rent".into(),
                notes: "".into(),
                recurring_rule_id: None,
                transfer_group_id: None,
                exclude_from_insights: true,
            },
        )
        .unwrap();
        insert_rule_raw(
            &source_conn,
            &RecurringRule {
                id: "rule-rent".into(),
                label: "Rent".into(),
                entry_kind: EntryKind::Expense,
                amount: 650.0,
                account_id: "primary".into(),
                category: "rent".into(),
                notes: "".into(),
                start_date: "2026-01-01".into(),
                end_date: None,
                frequency: RecurringFrequency::Monthly,
                status: RecurringStatus::Automatic,
                last_applied_local: Some("2026-03-01T00:00:00".into()),
            },
        )
        .unwrap();
        insert_cap_raw(
            &source_conn,
            &MonthlyCap {
                id: "cap-food".into(),
                category: "food".into(),
                amount: 200.0,
                month_key: "2026-03".into(),
            },
        )
        .unwrap();

        let exported_payload = snapshot_payload(&source_conn).unwrap();
        let export_path = source_dir.join("roundtrip.json");
        fs::write(&export_path, &exported_payload).unwrap();

        let target_dir = temp_test_dir("sbt_export_target");
        let target_state = make_test_state(&target_dir);
        ensure_environment(&target_state).unwrap();
        import_json_internal(&target_state, &export_path.to_string_lossy()).unwrap();
        let target_conn = open_connection(&target_state.env.db_path).unwrap();
        let roundtrip_payload = snapshot_payload(&target_conn).unwrap();

        assert_eq!(
            normalize_export_payload(&exported_payload),
            normalize_export_payload(&roundtrip_payload)
        );

        let _ = fs::remove_dir_all(source_dir);
        let _ = fs::remove_dir_all(target_dir);
    }

    #[test]
    #[ignore = "manual validation against a real legacy database copy"]
    fn manual_real_legacy_db_validation() {
        let legacy_path = match std::env::var("REAL_LEGACY_DB_PATH")
            .ok()
            .map(PathBuf::from)
            .filter(|path| path.exists())
        {
            Some(path) => path,
            None => return,
        };

        let base_dir = temp_test_dir("sbt_real_legacy_db");
        let state = make_test_state(&base_dir);
        fs::create_dir_all(&state.env.backups_dir).unwrap();
        fs::copy(&legacy_path, &state.env.legacy_db_path).unwrap();

        let legacy = Connection::open(&state.env.legacy_db_path).unwrap();
        let source_transaction_count: usize = legacy
            .query_row("SELECT COUNT(*) FROM transactions", [], |row| row.get(0))
            .unwrap();
        let source_rule_count: usize = legacy
            .query_row("SELECT COUNT(*) FROM recurring_charges", [], |row| {
                row.get(0)
            })
            .unwrap();
        let defaults = (
            0.0,
            9,
            "EN".to_string(),
            0.0,
            650.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        );
        let (
            starting_balance,
            plan_months_total,
            language,
            rent_monthly_manual,
            rent_base_monthly,
            food_house,
            misc,
            medical,
            school,
            household,
            health,
        ) = legacy
            .query_row(
                "SELECT starting_balance, plan_months_total, language, rent_monthly_manual, rent_base_monthly, food_house_monthly, misc_monthly, medical_monthly, school_monthly, household_monthly, health_monthly FROM settings LIMIT 1",
                [],
                |row| {
                    Ok((
                        row.get::<_, f64>(0).unwrap_or(0.0),
                        row.get::<_, i64>(1).unwrap_or(9),
                        row.get::<_, String>(2).unwrap_or_else(|_| "EN".to_string()),
                        row.get::<_, f64>(3).unwrap_or(0.0),
                        row.get::<_, f64>(4).unwrap_or(650.0),
                        row.get::<_, f64>(5).unwrap_or(0.0),
                        row.get::<_, f64>(6).unwrap_or(0.0),
                        row.get::<_, f64>(7).unwrap_or(0.0),
                        row.get::<_, f64>(8).unwrap_or(0.0),
                        row.get::<_, f64>(9).unwrap_or(0.0),
                        row.get::<_, f64>(10).unwrap_or(0.0),
                    ))
                },
            )
            .optional()
            .unwrap()
            .unwrap_or(defaults);

        let mut expected_entry_ids = HashSet::new();
        let mut expected_entry_tally = KindTally::default();
        let mut expected_excluded_count = 0usize;
        let mut entry_stmt = legacy
            .prepare(
                "SELECT id, type, label, category, notes, excluded_from_averages FROM transactions",
            )
            .unwrap();
        let entry_rows = entry_stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2).unwrap_or_default(),
                    row.get::<_, String>(3).unwrap_or_default(),
                    row.get::<_, String>(4).unwrap_or_default(),
                    row.get::<_, i64>(5).unwrap_or(0),
                ))
            })
            .unwrap();
        for row in entry_rows {
            let (id, tx_type, label, category, notes, excluded) = row.unwrap();
            expected_entry_ids.insert(id);
            bump_tally(
                &mut expected_entry_tally,
                &legacy_kind(&tx_type, &label, &category, &notes),
            );
            if parse_bool(excluded) {
                expected_excluded_count += 1;
            }
        }

        let mut expected_rule_ids = HashSet::new();
        let mut expected_rule_tally = KindTally::default();
        let mut saw_rent_rule = false;
        let mut rule_stmt = legacy
            .prepare("SELECT id, label, type, category, notes FROM recurring_charges")
            .unwrap();
        let rule_rows = rule_stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3).unwrap_or_default(),
                    row.get::<_, String>(4).unwrap_or_default(),
                ))
            })
            .unwrap();
        for row in rule_rows {
            let (id, label, tx_type, category, notes) = row.unwrap();
            expected_rule_ids.insert(id);
            if is_rent_like(&format!("{label} {category} {notes}")) {
                saw_rent_rule = true;
            }
            bump_tally(
                &mut expected_rule_tally,
                &legacy_kind(&tx_type, &label, &category, &notes),
            );
        }

        let expected_cap_count = [food_house, misc, medical, school, household, health]
            .into_iter()
            .filter(|amount| *amount > 0.0)
            .count()
            * plan_months_total.max(1) as usize;
        let expected_rent_plan = !saw_rent_rule
            && if rent_monthly_manual > 0.0 {
                rent_monthly_manual
            } else {
                rent_base_monthly
            } > 0.0;

        let status = run_legacy_migration_internal(&state).unwrap();
        let conn = open_connection(&state.env.db_path).unwrap();
        let accounts = fetch_accounts(&conn).unwrap();
        let entries = fetch_entries(&conn).unwrap();
        let rules = fetch_recurring_rules(&conn).unwrap();
        let caps = fetch_monthly_caps(&conn).unwrap();
        let settings = fetch_settings(&conn).unwrap();
        let backups = list_backups_internal(&state.env).unwrap();

        assert!(status.has_legacy_db);
        assert!(status.has_run);
        assert_eq!(accounts.len(), 1);
        assert_eq!(accounts[0].name, "Primary Account");
        assert_eq!(accounts[0].opening_balance, starting_balance);
        assert_eq!(settings.school_year_months, plan_months_total.max(1) as u32);
        assert_eq!(settings.language, language);

        assert_eq!(entries.len(), source_transaction_count);
        let actual_entry_ids = entries
            .iter()
            .map(|entry| entry.id.clone())
            .collect::<HashSet<_>>();
        assert_eq!(actual_entry_ids, expected_entry_ids);
        assert_eq!(tally_entries(&entries), expected_entry_tally);
        assert_eq!(
            entries
                .iter()
                .filter(|entry| entry.exclude_from_insights)
                .count(),
            expected_excluded_count
        );
        assert!(entries
            .iter()
            .all(|entry| entry.account_id == accounts[0].id));

        let migrated_rules = rules
            .iter()
            .filter(|rule| expected_rule_ids.contains(&rule.id))
            .cloned()
            .collect::<Vec<_>>();
        assert_eq!(migrated_rules.len(), source_rule_count);
        assert_eq!(tally_rules(&migrated_rules), expected_rule_tally);
        assert!(migrated_rules
            .iter()
            .all(|rule| rule.account_id == accounts[0].id));
        if expected_rent_plan {
            assert!(rules.iter().any(|rule| rule.label == "Migrated Rent Plan"));
        } else {
            assert!(!rules.iter().any(|rule| rule.label == "Migrated Rent Plan"));
        }

        assert_eq!(
            caps.len(),
            expected_cap_count,
            "Migrated caps should match positive legacy planning categories across the school-year horizon"
        );
        assert!(
            backups
                .iter()
                .any(|backup| backup.file_name.starts_with("budget_")),
            "Expected a migrated live backup to be created"
        );
        assert!(
            fs::read_dir(&state.env.backups_dir)
                .unwrap()
                .flatten()
                .any(|entry| entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with("legacy_budget_")),
            "Expected the original legacy database to be copied into backups"
        );

        println!(
            "Validated legacy migration from {}: {} transactions -> {} ledger entries, {} recurring rules -> {} rules, {} caps, opening balance {}.",
            legacy_path.display(),
            source_transaction_count,
            entries.len(),
            source_rule_count,
            rules.len(),
            caps.len(),
            starting_balance
        );

        let _ = fs::remove_dir_all(base_dir);
    }
}
