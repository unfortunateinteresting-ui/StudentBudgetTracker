export type Workspace =
  | "home"
  | "activity"
  | "plan"
  | "accounts"
  | "insights"
  | "settings";

export type AccountType = "checking" | "savings" | "cash" | "other";

export type EntryKind =
  | "expense"
  | "funding"
  | "rent_credit"
  | "transfer"
  | "adjustment";

export type RecurringFrequency = "daily" | "weekly" | "monthly";
export type RecurringStatus = "automatic" | "manual" | "paused";

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  opening_balance: number;
  archived: boolean;
  created_at: string;
  current_balance: number;
}

export interface LedgerEntry {
  id: string;
  account_id: string;
  entry_kind: EntryKind;
  amount: number;
  occurred_at_local: string;
  label: string;
  category: string;
  notes: string;
  recurring_rule_id?: string | null;
  transfer_group_id?: string | null;
  exclude_from_insights: boolean;
}

export interface RecurringRule {
  id: string;
  label: string;
  entry_kind: Exclude<EntryKind, "transfer">;
  amount: number;
  account_id: string;
  category: string;
  notes: string;
  start_date: string;
  end_date?: string | null;
  frequency: RecurringFrequency;
  status: RecurringStatus;
  last_applied_local?: string | null;
}

export interface MonthlyCap {
  id: string;
  category: string;
  amount: number;
  month_key: string;
}

export interface AppSettings {
  school_year_start_month: number;
  planning_start_month_key: string;
  school_year_months: number;
  language: string;
  backup_retention: number;
  last_migration_version: number;
}

export interface UpcomingObligation {
  recurring_rule_id: string;
  label: string;
  account_id: string;
  category: string;
  amount: number;
  due_date: string;
  entry_kind: Exclude<EntryKind, "transfer">;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface MonthlySeriesPoint {
  month_key: string;
  spent: number;
  cap: number;
  runway_balance: number;
}

export interface ActivityGroup {
  month_key: string;
  total_expense: number;
  total_funding: number;
  total_rent_credit: number;
  entries: LedgerEntry[];
}

export interface InsightSnapshot {
  total_available_cash: number;
  this_month_spend: number;
  this_month_cap: number;
  school_year_runway_remaining: number;
  projected_end_of_year_cushion: number;
  rent_due_this_month: number;
  rent_paid_this_month: number;
  rent_credit_this_month: number;
  rent_net_this_month: number;
  upcoming_obligations: UpcomingObligation[];
  recent_activity: LedgerEntry[];
  account_balances: ChartPoint[];
  category_spend_this_month: ChartPoint[];
  monthly_series: MonthlySeriesPoint[];
  activity_groups: ActivityGroup[];
  breakdowns: Record<string, string[]>;
}

export interface BackupFile {
  file_name: string;
  created_at: string;
  full_path: string;
}

export interface MissedRecurringOccurrence {
  recurring_rule_id: string;
  label: string;
  frequency: RecurringFrequency;
  dates: string[];
}

export interface MigrationStatus {
  has_legacy_db: boolean;
  has_run: boolean;
  legacy_path?: string | null;
  last_run_at?: string | null;
}

export interface SyncPeerSummary {
  peer_device_id: string;
  device_name: string;
  paired_at_utc: string;
  last_seen_at_utc?: string | null;
  last_sync_at_utc?: string | null;
}

export interface LocalSyncState {
  device_id: string;
  device_name: string;
  pending_operations: number;
  inbox_packet_count: number;
  trusted_peers: SyncPeerSummary[];
  last_sync_at_utc?: string | null;
  last_error?: string | null;
  transport_mode: string;
  localsend_available: boolean;
  localsend_path?: string | null;
  inbox_watch_active: boolean;
  lan_direct_available: boolean;
  lan_sync_port?: number | null;
  sync_inbox_path: string;
  sync_archive_path: string;
  sync_failed_path: string;
}

export interface SyncPacketExportResult {
  path: string;
  operation_count: number;
}

export interface SyncPacketImportResult {
  source_device_id: string;
  source_device_name: string;
  imported_operations: number;
  skipped_operations: number;
  trusted_peer_added: boolean;
}

export interface SyncPacketLaunchResult {
  path: string;
  operation_count: number;
  localsend_path: string;
  explorer_revealed: boolean;
}

export interface SyncInboxProcessResult {
  inbox_path: string;
  archive_path: string;
  failed_path: string;
  scanned_files: number;
  processed_files: number;
  failed_files: number;
  imported_operations: number;
  skipped_operations: number;
}

export interface LanPeerCandidate {
  device_id: string;
  device_name: string;
  address: string;
  port: number;
  trusted: boolean;
  last_sync_at_utc?: string | null;
}

export interface LanSyncSendInput {
  address: string;
  port: number;
}

export interface LanSyncSendResult {
  peer_device_id: string;
  peer_device_name: string;
  address: string;
  port: number;
  sent_operations: number;
  peer_imported_operations: number;
  peer_skipped_operations: number;
}

export interface BootstrapState {
  accounts: Account[];
  entries: LedgerEntry[];
  recurring_rules: RecurringRule[];
  monthly_caps: MonthlyCap[];
  settings: AppSettings;
  insight_snapshot: InsightSnapshot;
  backup_files: BackupFile[];
  migration_status: MigrationStatus;
  local_sync: LocalSyncState;
  recovery_notice?: string | null;
}

export interface EntryFilters {
  search?: string;
  month_key?: string;
  account_id?: string;
}

export interface BreakdownContext {
  range?: string | null;
  filters?: EntryFilters;
  month_key?: string;
  account_id?: string;
  category?: string;
}

export interface BreakdownResult {
  metric_id: string;
  title: string;
  lines: string[];
}

export interface CreateAccountInput {
  name: string;
  type: AccountType;
  opening_balance: number;
}

export interface UpdateAccountInput {
  name?: string;
  type?: AccountType;
  archived?: boolean;
}

export interface CreateEntryInput {
  account_id: string;
  entry_kind: EntryKind;
  amount: number;
  occurred_at_local: string;
  label: string;
  category: string;
  notes: string;
  recurring_rule_id?: string | null;
  exclude_from_insights?: boolean;
}

export interface UpdateEntryInput {
  account_id: string;
  entry_kind: Exclude<EntryKind, "transfer">;
  amount: number;
  occurred_at_local: string;
  label: string;
  category: string;
  notes: string;
  exclude_from_insights: boolean;
}

export interface CreateTransferInput {
  from_account_id: string;
  to_account_id: string;
  amount: number;
  occurred_at_local: string;
  label: string;
  notes: string;
}

export interface ReconcileAccountInput {
  account_id: string;
  actual_balance: number;
  occurred_at_local: string;
  notes: string;
}

export interface RecurringRuleInput {
  label: string;
  entry_kind: Exclude<EntryKind, "transfer">;
  amount: number;
  account_id: string;
  category: string;
  notes: string;
  start_date: string;
  end_date?: string | null;
  frequency: RecurringFrequency;
  status: RecurringStatus;
}

export interface MonthlyCapInput {
  category: string;
  amount: number;
  month_key: string;
}

export interface UpdateSettingsInput {
  planning_start_month_key: string;
  school_year_months: number;
  backup_retention: number;
}

export interface UpdateLocalSyncDeviceNameInput {
  device_name: string;
}
