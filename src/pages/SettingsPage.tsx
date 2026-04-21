import { useEffect, useMemo, useState } from "react";

import {
  createBackupNow,
  exportJsonV2,
  importJson,
  resetAllData,
  restoreBackup,
  runLegacyMigration,
  undoLastAction,
  updateAppSettings,
} from "../lib/api";
import { chooseJsonExportPath, chooseJsonImportPath } from "../lib/dialogs";
import { currentMonthKey, monthLabel, shiftMonthKey } from "../lib/format";
import type { AppSettings, BackupFile, MigrationStatus } from "../lib/types";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import styles from "./Page.module.css";

interface SettingsPageProps {
  backups: BackupFile[];
  migrationStatus: MigrationStatus;
  recoveryNotice?: string | null;
  settings: AppSettings;
  onRefresh: () => Promise<void>;
}

type NoticeState = {
  kind: "success" | "error";
  text: string;
};

export function SettingsPage({
  backups,
  migrationStatus,
  recoveryNotice,
  settings,
  onRefresh,
}: SettingsPageProps) {
  const [exportPath, setExportPath] = useState("");
  const [importPath, setImportPath] = useState("");
  const [resetPhrase, setResetPhrase] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const [schoolYearMonths, setSchoolYearMonths] = useState(settings.school_year_months);
  const [backupRetention, setBackupRetention] = useState(settings.backup_retention);
  const [pendingRestore, setPendingRestore] = useState<BackupFile | null>(null);
  const [restorePhrase, setRestorePhrase] = useState("");

  const recentBackups = useMemo(() => backups.slice(0, 10), [backups]);
  const currentMonth = currentMonthKey();
  const planningWindowEnd = shiftMonthKey(currentMonth, settings.school_year_months - 1);
  const formPlanningWindowEnd = shiftMonthKey(currentMonth, schoolYearMonths - 1);
  const settingsChanged =
    schoolYearMonths !== settings.school_year_months ||
    backupRetention !== settings.backup_retention;
  const settingsValid =
    schoolYearMonths >= 1 &&
    schoolYearMonths <= 12 &&
    backupRetention >= 1 &&
    backupRetention <= 200;

  useEffect(() => {
    setSchoolYearMonths(settings.school_year_months);
    setBackupRetention(settings.backup_retention);
  }, [settings.backup_retention, settings.school_year_months]);

  const runAction = async (
    actionKey: string,
    work: () => Promise<unknown>,
    successText: string,
    refreshAfter = true,
  ) => {
    setBusyAction(actionKey);
    try {
      await work();
      setNotice({ kind: "success", text: successText });
      if (refreshAfter) {
        await onRefresh();
      }
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleChooseExportPath = async () => {
    const selectedPath = await chooseJsonExportPath(exportPath);
    if (selectedPath) {
      setExportPath(selectedPath);
    }
  };

  const handleChooseImportPath = async () => {
    const selectedPath = await chooseJsonImportPath(importPath);
    if (selectedPath) {
      setImportPath(selectedPath);
    }
  };

  const queueRestore = (backup: BackupFile) => {
    setPendingRestore(backup);
    setRestorePhrase("");
    setNotice(null);
  };

  const cancelRestore = () => {
    setPendingRestore(null);
    setRestorePhrase("");
  };

  const handleRestore = async () => {
    if (!pendingRestore) return;

    await runAction(
      "restore",
      () => restoreBackup(pendingRestore.full_path),
      `Restored ${pendingRestore.file_name}.`,
    );
    setPendingRestore(null);
    setRestorePhrase("");
  };

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Settings</p>
          <h1 className={styles.heroTitle}>Data and backups</h1>
          <p className={styles.heroText}>
            Manage the planning window, imports, backups, undo, and recovery tools.
          </p>
        </div>
      </div>

      {recoveryNotice ? (
        <div className={`${styles.banner} ${styles.bannerWarning}`}>
          <div>
            <strong>Recovery notice</strong>
            <div className={styles.minor}>{recoveryNotice}</div>
          </div>
        </div>
      ) : null}

      {notice ? (
        <div
          className={`${styles.banner} ${
            notice.kind === "error" ? styles.bannerDanger : styles.bannerSuccess
          }`}
        >
          <div>{notice.text}</div>
        </div>
      ) : null}

      <div className={styles.grid3}>
        <MetricCard
          eyebrow="Planning"
          note={`${monthLabel(currentMonth)} to ${monthLabel(planningWindowEnd)}.`}
          title="Planning window"
          value={`${settings.school_year_months} months`}
        />
        <MetricCard
          eyebrow="Backups"
          note="Timestamped snapshots are pruned automatically."
          title="Retention policy"
          value={`${settings.backup_retention} copies`}
        />
        <MetricCard
          eyebrow="Migration"
          note="Legacy database detection and conversion stay local."
          title="Schema marker"
          value={`v${settings.last_migration_version}`}
        />
      </div>

      <div className={styles.grid2}>
        <SectionCard eyebrow="Planning controls" title="Planning and backup settings">
          <div className={styles.stack}>
            <label className={styles.field}>
              <span>Planning window in months</span>
              <input
                className={styles.input}
                max={12}
                min={1}
                onChange={(event) => setSchoolYearMonths(Number(event.target.value))}
                type="number"
                value={schoolYearMonths}
              />
            </label>

            <label className={styles.field}>
              <span>Backup retention copies</span>
              <input
                className={styles.input}
                max={200}
                min={1}
                onChange={(event) => setBackupRetention(Number(event.target.value))}
                type="number"
                value={backupRetention}
              />
            </label>

            <div className={styles.summaryList}>
              <div className={styles.summaryRow}>
                <span>Window starts</span>
                <span className={styles.inlineValue}>{monthLabel(currentMonth)}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Window ends</span>
                <span className={styles.inlineValue}>{monthLabel(formPlanningWindowEnd)}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Language</span>
                <span className={styles.inlineValue}>{settings.language} (fixed in v1)</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Last migration version</span>
                <span className={styles.inlineValue}>{settings.last_migration_version}</span>
              </div>
            </div>

            <div className={styles.helperText}>
              Forward totals and charts use recurring rules plus this planning window. If rent
              continues through summer, extend the recurring rent rule to the contract end date.
            </div>

            <div className={styles.rowActions}>
              <button
                className={styles.primaryButton}
                disabled={!settingsChanged || !settingsValid || busyAction === "settings"}
                onClick={() =>
                  void runAction(
                    "settings",
                    () =>
                      updateAppSettings({
                        school_year_start_month: settings.school_year_start_month,
                        school_year_months: schoolYearMonths,
                        backup_retention: backupRetention,
                      }),
                    "Settings updated.",
                  )
                }
                type="button"
              >
                Save settings
              </button>
              <button
                className={styles.secondaryButton}
                disabled={!settingsChanged || busyAction === "settings"}
                onClick={() => {
                  setSchoolYearMonths(settings.school_year_months);
                  setBackupRetention(settings.backup_retention);
                }}
                type="button"
              >
                Reset form
              </button>
            </div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Migration" title="Legacy import status">
          <div className={styles.summaryList}>
            <div className={styles.summaryRow}>
              <span>Legacy DB detected</span>
              <span className={styles.inlineValue}>
                {migrationStatus.has_legacy_db ? "Yes" : "No"}
              </span>
            </div>
            <div className={styles.summaryRow}>
              <span>Legacy path</span>
              <span className={styles.inlineValue}>
                {migrationStatus.legacy_path ?? "Not found"}
              </span>
            </div>
            <div className={styles.summaryRow}>
              <span>Migration already run</span>
              <span className={styles.inlineValue}>
                {migrationStatus.has_run ? migrationStatus.last_run_at ?? "Yes" : "No"}
              </span>
            </div>
          </div>
          <div className={styles.rowActions}>
            <button
              className={styles.primaryButton}
              disabled={busyAction === "migration"}
              onClick={() =>
                void runAction(
                  "migration",
                  () => runLegacyMigration(),
                  "Legacy migration completed.",
                )
              }
              type="button"
            >
              Run legacy migration
            </button>
          </div>
        </SectionCard>
      </div>

      <div className={styles.grid2}>
        <section className={styles.stack}>
          <h2>JSON portability</h2>
          <div className={styles.pathPicker}>
            <input
              aria-label="Export JSON path"
              className={styles.input}
              onChange={(event) => setExportPath(event.target.value)}
              placeholder="C:\\Path\\To\\budget-export.json"
              value={exportPath}
            />
            <button
              className={styles.secondaryButton}
              disabled={busyAction === "export"}
              onClick={() => void handleChooseExportPath()}
              type="button"
            >
              Choose export location
            </button>
          </div>
          <div className={styles.helperText}>
            Use the desktop save dialog or paste a full Windows path manually.
          </div>
          <div className={styles.rowActions}>
            <button
              className={styles.primaryButton}
              disabled={!exportPath.trim() || busyAction === "export"}
              onClick={() =>
                void runAction(
                  "export",
                  () => exportJsonV2(exportPath.trim()),
                  `Exported JSON to ${exportPath.trim()}.`,
                  false,
                )
              }
              type="button"
            >
              Export JSON v2
            </button>
          </div>

          <div className={styles.pathPicker}>
            <input
              aria-label="Import JSON path"
              className={styles.input}
              onChange={(event) => setImportPath(event.target.value)}
              placeholder="C:\\Path\\To\\budget-import.json"
              value={importPath}
            />
            <button
              className={styles.secondaryButton}
              disabled={busyAction === "import"}
              onClick={() => void handleChooseImportPath()}
              type="button"
            >
              Choose import file
            </button>
          </div>
          <div className={styles.helperText}>
            Legacy JSON and schema v2 JSON are both accepted. Manual paths still work as a fallback.
          </div>
          <div className={styles.rowActions}>
            <button
              className={styles.secondaryButton}
              disabled={!importPath.trim() || busyAction === "import"}
              onClick={() =>
                void runAction(
                  "import",
                  () => importJson(importPath.trim()),
                  `Imported data from ${importPath.trim()}.`,
                )
              }
              type="button"
            >
              Import JSON
            </button>
          </div>
        </section>

        <section className={styles.stack}>
          <h2>Backups and undo</h2>
          <div className={styles.helperText}>
            Restoring a backup replaces the current database contents, but the current state is
            snapshotted first so undo can roll it back.
          </div>
          {pendingRestore ? (
            <div className={`${styles.banner} ${styles.bannerDanger}`}>
              <div className={styles.stack}>
                <strong>Confirm backup restore</strong>
                <div className={styles.minor}>
                  You are about to replace the live database with{" "}
                  <strong>{pendingRestore.file_name}</strong>.
                </div>
                <div className={styles.minor}>{pendingRestore.full_path}</div>
                <label className={styles.field}>
                  <span>Type RESTORE to continue</span>
                  <input
                    aria-label="Restore confirmation phrase"
                    className={styles.input}
                    onChange={(event) => setRestorePhrase(event.target.value)}
                    placeholder="RESTORE"
                    value={restorePhrase}
                  />
                </label>
              </div>
              <div className={styles.rowActions}>
                <button
                  className={styles.secondaryButton}
                  disabled={busyAction === "restore"}
                  onClick={cancelRestore}
                  type="button"
                >
                  Cancel
                </button>
                <button
                  className={styles.dangerButton}
                  disabled={restorePhrase !== "RESTORE" || busyAction === "restore"}
                  onClick={() => void handleRestore()}
                  type="button"
                >
                  Confirm restore
                </button>
              </div>
            </div>
          ) : null}
          <div className={styles.rowActions}>
            <button
              className={styles.secondaryButton}
              disabled={busyAction === "backup"}
              onClick={() =>
                void runAction(
                  "backup",
                  () => createBackupNow(),
                  "Backup created.",
                )
              }
              type="button"
            >
              Create backup now
            </button>
            <button
              className={styles.secondaryButton}
              disabled={busyAction === "undo"}
              onClick={() =>
                void runAction(
                  "undo",
                  () => undoLastAction(),
                  "Last action undone.",
                )
              }
              type="button"
            >
              Undo last action
            </button>
          </div>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Backup file</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {recentBackups.length ? (
                  recentBackups.map((backup) => (
                    <tr key={backup.full_path}>
                      <td>{backup.file_name}</td>
                      <td>{backup.created_at}</td>
                      <td>
                        <button
                          className={styles.secondaryButton}
                          disabled={busyAction === "restore"}
                          onClick={() => queueRestore(backup)}
                          type="button"
                        >
                          Restore
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className={styles.emptyState} colSpan={3}>
                      No backups have been created yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <SectionCard eyebrow="Reset" title="Reset data">
        <div className={styles.summaryList}>
          <div className={styles.summaryRow}>
            <span>Current guard</span>
            <span className={styles.inlineValue}>Type RESET to enable wipe</span>
          </div>
          <div className={styles.summaryRow}>
            <span>Scope</span>
            <span className={styles.inlineValue}>Database contents, plans, and history</span>
          </div>
        </div>
        <input
          className={styles.input}
          onChange={(event) => setResetPhrase(event.target.value)}
          placeholder="Type RESET"
          value={resetPhrase}
        />
        <div className={styles.rowActions}>
          <button
            className={styles.dangerButton}
            disabled={resetPhrase !== "RESET" || busyAction === "reset"}
            onClick={() =>
              void runAction(
                "reset",
                () => resetAllData(),
                "All data reset.",
              )
            }
            type="button"
          >
            Reset all data
          </button>
        </div>
      </SectionCard>
    </div>
  );
}
