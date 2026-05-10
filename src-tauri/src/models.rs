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
    #[serde(default)]
    pub planning_start_month_key: String,
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
    pub spending_to_date: f64,
    pub average_monthly_spend: f64,
    pub planned_remaining_spending: f64,
    pub predicted_remaining_spending: f64,
    pub planned_total_spending: f64,
    pub predicted_total_spending: f64,
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
    pub category_average_spend: Vec<ChartPoint>,
    pub monthly_spending_totals: Vec<ChartPoint>,
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
pub struct SyncPeerSummary {
    pub peer_device_id: String,
    pub device_name: String,
    pub paired_at_utc: String,
    pub last_seen_at_utc: Option<String>,
    pub last_sync_at_utc: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalSyncState {
    pub device_id: String,
    pub device_name: String,
    pub local_ipv4_addresses: Vec<String>,
    pub pending_operations: u32,
    pub inbox_packet_count: u32,
    pub trusted_peers: Vec<SyncPeerSummary>,
    pub last_sync_at_utc: Option<String>,
    pub last_error: Option<String>,
    pub transport_mode: String,
    pub localsend_available: bool,
    pub localsend_path: Option<String>,
    pub inbox_watch_active: bool,
    pub lan_direct_available: bool,
    pub lan_sync_port: Option<u16>,
    pub sync_inbox_path: String,
    pub sync_archive_path: String,
    pub sync_failed_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncDeviceIdentity {
    pub device_id: String,
    pub device_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncOperationRecord {
    pub op_seq: i64,
    pub device_id: String,
    pub entity_type: String,
    pub entity_id: String,
    pub operation_type: String,
    pub payload_json: serde_json::Value,
    pub created_at_utc: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SyncPacketDependencies {
    #[serde(default)]
    pub accounts: Vec<Account>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SyncSnapshot {
    pub settings: Option<AppSettings>,
    #[serde(default)]
    pub accounts: Vec<Account>,
    #[serde(default)]
    pub ledger_entries: Vec<LedgerEntry>,
    #[serde(default)]
    pub recurring_rules: Vec<RecurringRule>,
    #[serde(default)]
    pub monthly_caps: Vec<MonthlyCap>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPacket {
    pub app: String,
    pub schema_version: u32,
    pub generated_at_utc: String,
    pub source: SyncDeviceIdentity,
    #[serde(default)]
    pub snapshot: SyncSnapshot,
    #[serde(default)]
    pub dependencies: SyncPacketDependencies,
    pub operations: Vec<SyncOperationRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPacketExportResult {
    pub path: String,
    pub operation_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPacketImportResult {
    pub source_device_id: String,
    pub source_device_name: String,
    pub imported_operations: u32,
    pub skipped_operations: u32,
    pub trusted_peer_added: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPacketLaunchResult {
    pub path: String,
    pub operation_count: u32,
    pub localsend_path: String,
    pub explorer_revealed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncInboxProcessResult {
    pub inbox_path: String,
    pub archive_path: String,
    pub failed_path: String,
    pub scanned_files: u32,
    pub processed_files: u32,
    pub failed_files: u32,
    pub imported_operations: u32,
    pub skipped_operations: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanPeerCandidate {
    pub device_id: String,
    pub device_name: String,
    pub address: String,
    pub port: u16,
    pub trusted: bool,
    pub last_sync_at_utc: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanSyncSendInput {
    pub address: String,
    pub port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LanSyncSendResult {
    pub peer_device_id: String,
    pub peer_device_name: String,
    pub address: String,
    pub port: u16,
    pub sent_operations: u32,
    pub peer_imported_operations: u32,
    pub peer_skipped_operations: u32,
    pub local_imported_operations: u32,
    pub local_skipped_operations: u32,
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
    pub local_sync: LocalSyncState,
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
    pub opening_balance: Option<f64>,
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
    pub planning_start_month_key: String,
    pub school_year_months: u32,
    pub backup_retention: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateLocalSyncDeviceNameInput {
    pub device_name: String,
}
