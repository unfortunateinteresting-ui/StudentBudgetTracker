use std::collections::HashMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AccountType {
    Checking,
    Savings,
    Cash,
    Other,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EntryKind {
    Expense,
    Funding,
    RentCredit,
    Transfer,
    Adjustment,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RecurringFrequency {
    Daily,
    Weekly,
    Monthly,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RecurringStatus {
    Automatic,
    Manual,
    Paused,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Account {
    pub id: String,
    pub name: String,
    pub r#type: AccountType,
    pub opening_balance: f64,
    pub archived: bool,
    pub created_at: String,
    pub current_balance: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEntry {
    pub id: String,
    pub account_id: String,
    pub entry_kind: EntryKind,
    pub amount: f64,
    pub occurred_at_local: String,
    pub label: String,
    pub category: String,
    pub notes: String,
    pub recurring_rule_id: Option<String>,
    pub transfer_group_id: Option<String>,
    pub exclude_from_insights: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurringRule {
    pub id: String,
    pub label: String,
    pub entry_kind: EntryKind,
    pub amount: f64,
    pub account_id: String,
    pub category: String,
    pub notes: String,
    pub start_date: String,
    pub end_date: Option<String>,
    pub frequency: RecurringFrequency,
    pub status: RecurringStatus,
    pub last_applied_local: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonthlyCap {
    pub id: String,
    pub category: String,
    pub amount: f64,
    pub month_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub school_year_start_month: u32,
    pub school_year_months: u32,
    pub language: String,
    pub backup_retention: u32,
    pub last_migration_version: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpcomingObligation {
    pub recurring_rule_id: String,
    pub label: String,
    pub account_id: String,
    pub category: String,
    pub amount: f64,
    pub due_date: String,
    pub entry_kind: EntryKind,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartPoint {
    pub label: String,
    pub value: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonthlySeriesPoint {
    pub month_key: String,
    pub spent: f64,
    pub cap: f64,
    pub runway_balance: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityGroup {
    pub month_key: String,
    pub total_expense: f64,
    pub total_funding: f64,
    pub total_rent_credit: f64,
    pub entries: Vec<LedgerEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InsightSnapshot {
    pub total_available_cash: f64,
    pub this_month_spend: f64,
    pub this_month_cap: f64,
    pub school_year_runway_remaining: f64,
    pub projected_end_of_year_cushion: f64,
    pub rent_due_this_month: f64,
    pub rent_paid_this_month: f64,
    pub rent_credit_this_month: f64,
    pub rent_net_this_month: f64,
    pub upcoming_obligations: Vec<UpcomingObligation>,
    pub recent_activity: Vec<LedgerEntry>,
    pub account_balances: Vec<ChartPoint>,
    pub category_spend_this_month: Vec<ChartPoint>,
    pub monthly_series: Vec<MonthlySeriesPoint>,
    pub activity_groups: Vec<ActivityGroup>,
    pub breakdowns: HashMap<String, Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackupFile {
    pub file_name: String,
    pub created_at: String,
    pub full_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MissedRecurringOccurrence {
    pub recurring_rule_id: String,
    pub label: String,
    pub frequency: RecurringFrequency,
    pub dates: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationStatus {
    pub has_legacy_db: bool,
    pub has_run: bool,
    pub legacy_path: Option<String>,
    pub last_run_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BootstrapState {
    pub accounts: Vec<Account>,
    pub entries: Vec<LedgerEntry>,
    pub recurring_rules: Vec<RecurringRule>,
    pub monthly_caps: Vec<MonthlyCap>,
    pub settings: AppSettings,
    pub insight_snapshot: InsightSnapshot,
    pub backup_files: Vec<BackupFile>,
    pub migration_status: MigrationStatus,
    pub recovery_notice: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BreakdownResult {
    pub metric_id: String,
    pub title: String,
    pub lines: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct EntryFilters {
    pub search: Option<String>,
    pub month_key: Option<String>,
    pub account_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateAccountInput {
    pub name: String,
    pub r#type: AccountType,
    pub opening_balance: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UpdateAccountInput {
    pub name: Option<String>,
    pub r#type: Option<AccountType>,
    pub archived: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateEntryInput {
    pub account_id: String,
    pub entry_kind: EntryKind,
    pub amount: f64,
    pub occurred_at_local: String,
    pub label: String,
    pub category: String,
    pub notes: String,
    pub recurring_rule_id: Option<String>,
    pub exclude_from_insights: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateEntryInput {
    pub account_id: String,
    pub entry_kind: EntryKind,
    pub amount: f64,
    pub occurred_at_local: String,
    pub label: String,
    pub category: String,
    pub notes: String,
    pub exclude_from_insights: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateTransferInput {
    pub from_account_id: String,
    pub to_account_id: String,
    pub amount: f64,
    pub occurred_at_local: String,
    pub label: String,
    pub notes: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReconcileAccountInput {
    pub account_id: String,
    pub actual_balance: f64,
    pub occurred_at_local: String,
    pub notes: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurringRuleInput {
    pub label: String,
    pub entry_kind: EntryKind,
    pub amount: f64,
    pub account_id: String,
    pub category: String,
    pub notes: String,
    pub start_date: String,
    pub end_date: Option<String>,
    pub frequency: RecurringFrequency,
    pub status: RecurringStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonthlyCapInput {
    pub category: String,
    pub amount: f64,
    pub month_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateSettingsInput {
    pub school_year_start_month: u32,
    pub school_year_months: u32,
    pub backup_retention: u32,
}
