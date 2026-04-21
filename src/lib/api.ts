import { invoke } from "@tauri-apps/api/core";

import type {
  BootstrapState,
  BreakdownContext,
  BreakdownResult,
  CreateAccountInput,
  CreateEntryInput,
  CreateTransferInput,
  EntryFilters,
  InsightSnapshot,
  MonthlyCap,
  MonthlyCapInput,
  RecurringRule,
  RecurringRuleInput,
  ReconcileAccountInput,
  UpdateAccountInput,
  UpdateEntryInput,
  UpdateSettingsInput,
} from "./types";

export const bootstrapState = () =>
  invoke<BootstrapState>("bootstrap_state");

export const listEntries = (filters: EntryFilters) =>
  invoke("list_entries", { filters });

export const createAccount = (input: CreateAccountInput) =>
  invoke("create_account", { input });

export const updateAccount = (accountId: string, input: UpdateAccountInput) =>
  invoke("update_account", { accountId, input });

export const archiveAccount = (accountId: string) =>
  invoke("archive_account", { accountId });

export const createEntry = (input: CreateEntryInput) =>
  invoke("create_entry", { input });

export const updateEntry = (entryId: string, input: UpdateEntryInput) =>
  invoke("update_entry", { entryId, input });

export const deleteEntry = (entryId: string) =>
  invoke("delete_entry", { entryId });

export const createTransfer = (input: CreateTransferInput) =>
  invoke("create_transfer", { input });

export const reconcileAccount = (input: ReconcileAccountInput) =>
  invoke("reconcile_account", { input });

export const listRecurringRules = () =>
  invoke<RecurringRule[]>("list_recurring_rules");

export const createRecurringRule = (input: RecurringRuleInput) =>
  invoke("create_recurring_rule", { input });

export const updateRecurringRule = (ruleId: string, input: RecurringRuleInput) =>
  invoke("update_recurring_rule", { ruleId, input });

export const deleteRecurringRule = (ruleId: string) =>
  invoke("delete_recurring_rule", { ruleId });

export const applyRecurringRuleNow = (ruleId: string) =>
  invoke("apply_recurring_rule_now", { ruleId });

export const listMonthlyCaps = () =>
  invoke<MonthlyCap[]>("list_monthly_caps");

export const setMonthlyCap = (input: MonthlyCapInput) =>
  invoke("set_monthly_cap", { input });

export const deleteMonthlyCap = (capId: string) =>
  invoke("delete_monthly_cap", { capId });

export const getInsights = (range?: string | null, filters?: EntryFilters | null) =>
  invoke<InsightSnapshot>("get_insights", {
    range: range ?? null,
    filters: filters ?? null,
  });

export const getCalculationBreakdown = (
  metricId: string,
  context?: BreakdownContext | null,
) =>
  invoke<BreakdownResult>("get_calculation_breakdown", {
    metricId,
    context: context ?? null,
  });

export const runStartupRecurringCheck = () =>
  invoke("run_startup_recurring_check");

export const applyMissedRecurring = (recurringRuleIds?: string[]) =>
  invoke("apply_missed_recurring", { recurringRuleIds });

export const exportJsonV2 = (path: string) =>
  invoke("export_json_v2", { path });

export const importJson = (path: string) =>
  invoke("import_json", { path });

export const runLegacyMigration = () =>
  invoke("run_legacy_migration");

export const listBackups = () =>
  invoke("list_backups");

export const updateAppSettings = (input: UpdateSettingsInput) =>
  invoke("update_app_settings", { input });

export const createBackupNow = () =>
  invoke("create_backup_now");

export const restoreBackup = (backupPath: string) =>
  invoke("restore_backup", { backupPath });

export const resetAllData = () =>
  invoke("reset_all_data");

export const undoLastAction = () =>
  invoke("undo_last_action");
