import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createBackupNow,
  discoverLanPeers,
  exportJsonV2,
  exportSyncPacketForLocalSend,
  exportSyncPacket,
  importJson,
  importSyncPacket,
  openSyncInboxFolder,
  processSyncInbox,
  resetAllData,
  restoreBackup,
  runLegacyMigration,
  syncWithLanPeer,
  undoLastAction,
  updateAppSettings,
  updateLocalSyncDeviceName,
} from "../lib/api";
import {
  chooseJsonExportPath,
  chooseJsonImportPath,
  chooseSyncPacketExportPath,
  chooseSyncPacketImportPath,
} from "../lib/dialogs";
import { monthLabel, shiftMonthKey } from "../lib/format";
import type {
  AppSettings,
  BackupFile,
  LanPeerCandidate,
  LocalSyncState,
  MigrationStatus,
} from "../lib/types";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import styles from "./Page.module.css";

const isMonthKey = (value: string) => /^\d{4}-(0[1-9]|1[0-2])$/.test(value);

interface SettingsPageProps {
  backups: BackupFile[];
  localSync: LocalSyncState;
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
  localSync,
  migrationStatus,
  recoveryNotice,
  settings,
  onRefresh,
}: SettingsPageProps) {
  const [exportPath, setExportPath] = useState("");
  const [importPath, setImportPath] = useState("");
  const [syncExportPath, setSyncExportPath] = useState("");
  const [syncImportPath, setSyncImportPath] = useState("");
  const [resetPhrase, setResetPhrase] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const [planningStartMonthKey, setPlanningStartMonthKey] = useState(
    settings.planning_start_month_key,
  );
  const [deviceName, setDeviceName] = useState(localSync.device_name);
  const [schoolYearMonths, setSchoolYearMonths] = useState(settings.school_year_months);
  const [backupRetention, setBackupRetention] = useState(settings.backup_retention);
  const [pendingRestore, setPendingRestore] = useState<BackupFile | null>(null);
  const [restorePhrase, setRestorePhrase] = useState("");
  const [discoveredPeers, setDiscoveredPeers] = useState<LanPeerCandidate[]>([]);
  const [manualLanAddress, setManualLanAddress] = useState("");
  const [manualLanPort, setManualLanPort] = useState(
    localSync.lan_sync_port ? String(localSync.lan_sync_port) : "38256",
  );

  const recentBackups = useMemo(() => backups.slice(0, 10), [backups]);
  const planningWindowStart = settings.planning_start_month_key;
  const planningWindowEnd = shiftMonthKey(planningWindowStart, settings.school_year_months - 1);
  const formPlanningWindowEnd = isMonthKey(planningStartMonthKey)
    ? shiftMonthKey(planningStartMonthKey, schoolYearMonths - 1)
    : planningStartMonthKey;
  const settingsChanged =
    planningStartMonthKey !== settings.planning_start_month_key ||
    schoolYearMonths !== settings.school_year_months ||
    backupRetention !== settings.backup_retention;
  const deviceNameChanged = deviceName.trim() !== localSync.device_name;
  const settingsValid =
    isMonthKey(planningStartMonthKey) &&
    schoolYearMonths >= 1 &&
    schoolYearMonths <= 12 &&
    backupRetention >= 1 &&
    backupRetention <= 200;
  const singleDetectedPeer = discoveredPeers.length === 1 ? discoveredPeers[0] : null;

  const refreshLanPeers = useCallback(
    async (silent = false) => {
      if (!silent) {
        setBusyAction("lan-discover");
      }
      try {
        const peers = await discoverLanPeers();
        setDiscoveredPeers(peers);
        if (!silent) {
          setNotice({
            kind: "success",
            text: peers.length
              ? `Found ${peers.length} device(s) on the local network.`
              : "No student budget tracker devices responded on the local network.",
          });
        }
        return peers;
      } catch (error) {
        if (!silent) {
          setNotice({ kind: "error", text: String(error) });
        }
        return [];
      } finally {
        if (!silent) {
          setBusyAction(null);
        }
      }
    },
    [],
  );

  useEffect(() => {
    setPlanningStartMonthKey(settings.planning_start_month_key);
    setSchoolYearMonths(settings.school_year_months);
    setBackupRetention(settings.backup_retention);
  }, [
    settings.backup_retention,
    settings.planning_start_month_key,
    settings.school_year_months,
  ]);

  useEffect(() => {
    setDeviceName(localSync.device_name);
  }, [localSync.device_name]);

  useEffect(() => {
    if (localSync.lan_sync_port) {
      setManualLanPort(String(localSync.lan_sync_port));
    }
  }, [localSync.lan_sync_port]);

  useEffect(() => {
    if (!localSync.lan_direct_available) {
      setDiscoveredPeers([]);
      return;
    }
    void refreshLanPeers(true);
  }, [localSync.lan_direct_available, refreshLanPeers]);

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

  const handleChooseSyncExportPath = async () => {
    const selectedPath = await chooseSyncPacketExportPath(syncExportPath);
    if (selectedPath) {
      setSyncExportPath(selectedPath);
    }
  };

  const handleChooseSyncImportPath = async () => {
    const selectedPath = await chooseSyncPacketImportPath(syncImportPath);
    if (selectedPath) {
      setSyncImportPath(selectedPath);
    }
  };

  const handleExportSyncPacket = async () => {
    setBusyAction("sync-export");
    try {
      const result = await exportSyncPacket(syncExportPath.trim());
      setNotice({
        kind: "success",
        text: `Exported ${result.operation_count} sync operations to ${result.path}.`,
      });
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleImportSyncPacket = async () => {
    setBusyAction("sync-import");
    try {
      const result = await importSyncPacket(syncImportPath.trim());
      setNotice({
        kind: "success",
        text: `Imported ${result.imported_operations} sync operations from ${result.source_device_name}.`,
      });
      await onRefresh();
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleExportForLocalSend = async () => {
    setBusyAction("localsend");
    try {
      const result = await exportSyncPacketForLocalSend();
      setNotice({
        kind: "success",
        text: `Exported ${result.operation_count} sync operations, opened LocalSend, and revealed ${result.path}.`,
      });
      await onRefresh();
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleOpenSyncInbox = async () => {
    setBusyAction("sync-inbox-open");
    try {
      const openedPath = await openSyncInboxFolder();
      setNotice({
        kind: "success",
        text: `Opened sync inbox at ${openedPath}.`,
      });
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleProcessSyncInbox = async () => {
    setBusyAction("sync-inbox-process");
    try {
      const result = await processSyncInbox();
      setNotice({
        kind: "success",
        text: `Scanned ${result.scanned_files} inbox files, processed ${result.processed_files}, failed ${result.failed_files}.`,
      });
      await onRefresh();
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
    }
  };

  const handleDiscoverLanPeers = async () => {
    await refreshLanPeers(false);
  };

  const handleLanSync = async (address: string, port: number) => {
    setBusyAction("lan-sync");
    try {
      const result = await syncWithLanPeer({ address, port });
      setNotice({
        kind: "success",
        text: `Synced with ${result.peer_device_name}. Sent ${result.sent_operations} queued operations; peer imported ${result.peer_imported_operations}. This device imported ${result.local_imported_operations}.`,
      });
      await onRefresh();
      await refreshLanPeers(true);
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
    } finally {
      setBusyAction(null);
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
          note={`${monthLabel(planningWindowStart)} to ${monthLabel(planningWindowEnd)}.`}
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
              <span>Planning window start</span>
              <input
                className={styles.input}
                onChange={(event) => setPlanningStartMonthKey(event.target.value)}
                type="month"
                value={planningStartMonthKey}
              />
            </label>

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
                <span className={styles.inlineValue}>
                  {isMonthKey(planningStartMonthKey)
                    ? monthLabel(planningStartMonthKey)
                    : planningStartMonthKey || "Invalid"}
                </span>
              </div>
              <div className={styles.summaryRow}>
                <span>Window ends</span>
                <span className={styles.inlineValue}>
                  {isMonthKey(formPlanningWindowEnd)
                    ? monthLabel(formPlanningWindowEnd)
                    : formPlanningWindowEnd || "Invalid"}
                </span>
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
              Charts keep the months from the selected start, while balance projections switch from
              historical months to current and future months automatically. If rent continues
              through summer, extend the recurring rent rule to the contract end date.
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
                        planning_start_month_key: planningStartMonthKey,
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
                  setPlanningStartMonthKey(settings.planning_start_month_key);
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
        <SectionCard eyebrow="Local sync" title="Sync between devices">
          <div className={styles.stack}>
            <label className={styles.field}>
              <span>Device name</span>
              <input
                className={styles.input}
                onChange={(event) => setDeviceName(event.target.value)}
                value={deviceName}
              />
            </label>

            <div className={styles.summaryList}>
              <div className={styles.summaryRow}>
                <span>Device ID</span>
                <span className={styles.inlineValue}>{localSync.device_id}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Local IPv4</span>
                <span className={styles.inlineValue}>
                  {localSync.local_ipv4_addresses.length
                    ? localSync.local_ipv4_addresses.join(", ")
                    : "Not detected"}
                </span>
              </div>
              <div className={styles.summaryRow}>
                <span>Queued local operations</span>
                <span className={styles.inlineValue}>{localSync.pending_operations}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Inbox packets</span>
                <span className={styles.inlineValue}>{localSync.inbox_packet_count}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Trusted devices</span>
                <span className={styles.inlineValue}>{localSync.trusted_peers.length}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>Last sync</span>
                <span className={styles.inlineValue}>
                  {localSync.last_sync_at_utc ?? "Not synced yet"}
                </span>
              </div>
              <div className={styles.summaryRow}>
                <span>Transport mode</span>
                <span className={styles.inlineValue}>{localSync.transport_mode}</span>
              </div>
              <div className={styles.summaryRow}>
                <span>LocalSend</span>
                <span className={styles.inlineValue}>
                  {localSync.localsend_available ? "Detected" : "Not found"}
                </span>
              </div>
              <div className={styles.summaryRow}>
                <span>Inbox watcher</span>
                <span className={styles.inlineValue}>
                  {localSync.inbox_watch_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className={styles.summaryRow}>
                <span>Direct LAN sync</span>
                <span className={styles.inlineValue}>
                  {localSync.lan_direct_available
                    ? `Ready on port ${localSync.lan_sync_port ?? "?"}`
                    : "Unavailable"}
                </span>
              </div>
            </div>

            <div className={styles.rowActions}>
              <button
                className={styles.primaryButton}
                disabled={!deviceName.trim() || !deviceNameChanged || busyAction === "device"}
                onClick={() =>
                  void runAction(
                    "device",
                    () =>
                      updateLocalSyncDeviceName({
                        device_name: deviceName.trim(),
                      }),
                    "Device name updated.",
                  )
                }
                type="button"
              >
                Save device name
              </button>
              <button
                className={styles.secondaryButton}
                disabled={!deviceNameChanged || busyAction === "device"}
                onClick={() => setDeviceName(localSync.device_name)}
                type="button"
              >
                Reset device name
              </button>
            </div>

            <div className={styles.subsection}>
              <div className={styles.subsectionHeader}>
                <div className={styles.stackCompact}>
                  <h2 className={styles.subsectionTitle}>Send updates to another device</h2>
                  <div className={styles.helperText}>
                    This page now looks for nearby devices automatically. When one appears below,
                    click <strong>Send updates</strong> on this device to push your latest data to
                    it.
                  </div>
                  {singleDetectedPeer ? (
                    <div className={styles.helperText}>
                      Quick target found: <strong>{singleDetectedPeer.device_name}</strong>.
                    </div>
                  ) : null}
                </div>
                <button
                  className={styles.secondaryButton}
                  disabled={!localSync.lan_direct_available || busyAction === "lan-discover"}
                  onClick={() => void handleDiscoverLanPeers()}
                  type="button"
                >
                  Refresh devices
                </button>
              </div>

              {discoveredPeers.length ? (
                <div className={styles.deviceGrid}>
                  {discoveredPeers.map((peer) => (
                    <div
                      className={styles.deviceCard}
                      key={`${peer.device_id}-${peer.address}-${peer.port}`}
                    >
                      <div className={styles.deviceCardHeader}>
                        <div className={styles.stackCompact}>
                          <div className={styles.deviceCardTitle}>{peer.device_name}</div>
                          <div className={styles.minor}>
                            {peer.address}:{peer.port}
                          </div>
                        </div>
                        <span
                          className={`${styles.deviceStatus} ${
                            peer.trusted ? styles.deviceStatusTrusted : styles.deviceStatusDetected
                          }`}
                        >
                          {peer.trusted ? "Trusted" : "Detected"}
                        </span>
                      </div>
                      <div className={styles.deviceMeta}>
                        <div className={styles.deviceMetaRow}>
                          <span>Status</span>
                          <span>
                            {peer.trusted
                              ? peer.last_sync_at_utc
                                ? "Seen before"
                                : "Trusted"
                              : "Ready for first sync"}
                          </span>
                        </div>
                        <div className={styles.deviceMetaRow}>
                          <span>Last sync</span>
                          <span>{peer.last_sync_at_utc ?? "Never"}</span>
                        </div>
                      </div>
                      <div className={styles.rowActions}>
                        <button
                          className={styles.primaryButton}
                          disabled={busyAction === "lan-sync"}
                          onClick={() => void handleLanSync(peer.address, peer.port)}
                          type="button"
                        >
                          Send updates
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyPanel}>
                  <strong>No detected devices yet</strong>
                  <div className={styles.minor}>
                    Keep the app open on the other device, then click <strong>Refresh devices</strong>.
                  </div>
                  <div className={styles.minor}>
                    If nothing appears, use the manual address fallback below.
                  </div>
                </div>
              )}
            </div>

            <div className={styles.subsection}>
              <div className={styles.stackCompact}>
                <h2 className={styles.subsectionTitle}>Manual address fallback</h2>
                <div className={styles.helperText}>
                  Use this only when the other device does not show above. Enter the receiving
                  device's Wi-Fi IPv4 address. This device currently reports:{" "}
                  {localSync.local_ipv4_addresses.length
                    ? localSync.local_ipv4_addresses.join(", ")
                    : "no local IPv4 addresses detected"}
                  .
                </div>
              </div>
              <div className={styles.pathPicker}>
                <input
                  aria-label="Manual LAN address"
                  className={styles.input}
                  onChange={(event) => setManualLanAddress(event.target.value)}
                  placeholder="192.168.1.24"
                  value={manualLanAddress}
                />
                <input
                  aria-label="Manual LAN port"
                  className={styles.input}
                  onChange={(event) => setManualLanPort(event.target.value)}
                  placeholder="38256"
                  type="number"
                  value={manualLanPort}
                />
              </div>
              <div className={styles.rowActions}>
                <button
                  className={styles.secondaryButton}
                  disabled={
                    !manualLanAddress.trim() ||
                    !manualLanPort.trim() ||
                    Number(manualLanPort) <= 0 ||
                    busyAction === "lan-sync"
                  }
                  onClick={() =>
                    void handleLanSync(manualLanAddress.trim(), Number(manualLanPort))
                  }
                  type="button"
                >
                  Send to address
                </button>
              </div>
            </div>

            <div className={styles.subsection}>
              <div className={styles.stackCompact}>
                <h2 className={styles.subsectionTitle}>Trusted devices</h2>
                <div className={styles.helperText}>
                  These are devices that have already synced with this one before.
                </div>
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Trusted device</th>
                      <th>Paired</th>
                      <th>Last seen</th>
                      <th>Last sync</th>
                    </tr>
                  </thead>
                  <tbody>
                    {localSync.trusted_peers.length ? (
                      localSync.trusted_peers.map((peer) => (
                        <tr key={peer.peer_device_id}>
                          <td>{peer.device_name}</td>
                          <td>{peer.paired_at_utc}</td>
                          <td>{peer.last_seen_at_utc ?? "Never"}</td>
                          <td>{peer.last_sync_at_utc ?? "Never"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td className={styles.emptyState} colSpan={4}>
                          No trusted devices yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={styles.subsection}>
              <div className={styles.stackCompact}>
                <h2 className={styles.subsectionTitle}>Packet and LocalSend fallback</h2>
                <div className={styles.helperText}>
                  Use packet export and import only if direct device-to-device sync is not working.
                </div>
                <div className={styles.helperText}>
                  Drop received sync packets into the inbox folder. The app scans that folder on
                  startup and while it stays open, and <strong>Scan inbox now</strong> forces it
                  immediately.
                </div>
                {localSync.localsend_path ? (
                  <div className={styles.helperText}>
                    LocalSend path: {localSync.localsend_path}
                  </div>
                ) : null}
                <div className={styles.helperText}>Sync inbox: {localSync.sync_inbox_path}</div>
                <div className={styles.helperText}>Sync archive: {localSync.sync_archive_path}</div>
                <div className={styles.helperText}>Sync failed: {localSync.sync_failed_path}</div>
                {localSync.last_error ? (
                  <div className={styles.helperText}>Last sync error: {localSync.last_error}</div>
                ) : null}
              </div>

              <div className={styles.rowActions}>
                <button
                  className={styles.primaryButton}
                  disabled={!localSync.localsend_available || busyAction === "localsend"}
                  onClick={() => void handleExportForLocalSend()}
                  type="button"
                >
                  Export and open LocalSend
                </button>
                <button
                  className={styles.secondaryButton}
                  disabled={busyAction === "sync-inbox-process"}
                  onClick={() => void handleProcessSyncInbox()}
                  type="button"
                >
                  Scan inbox now
                </button>
                <button
                  className={styles.secondaryButton}
                  disabled={busyAction === "sync-inbox-open"}
                  onClick={() => void handleOpenSyncInbox()}
                  type="button"
                >
                  Open sync inbox
                </button>
              </div>

              <div className={styles.pathPicker}>
                <input
                  aria-label="Export sync packet path"
                  className={styles.input}
                  onChange={(event) => setSyncExportPath(event.target.value)}
                  placeholder="C:\\Path\\To\\student-budget-sync.json"
                  value={syncExportPath}
                />
                <button
                  className={styles.secondaryButton}
                  disabled={busyAction === "sync-export"}
                  onClick={() => void handleChooseSyncExportPath()}
                  type="button"
                >
                  Choose packet export location
                </button>
              </div>

              <div className={styles.rowActions}>
                <button
                  className={styles.primaryButton}
                  disabled={!syncExportPath.trim() || busyAction === "sync-export"}
                  onClick={() => void handleExportSyncPacket()}
                  type="button"
                >
                  Export sync packet
                </button>
              </div>

              <div className={styles.pathPicker}>
                <input
                  aria-label="Import sync packet path"
                  className={styles.input}
                  onChange={(event) => setSyncImportPath(event.target.value)}
                  placeholder="C:\\Path\\To\\student-budget-sync.json"
                  value={syncImportPath}
                />
                <button
                  className={styles.secondaryButton}
                  disabled={busyAction === "sync-import"}
                  onClick={() => void handleChooseSyncImportPath()}
                  type="button"
                >
                  Choose sync packet file
                </button>
              </div>

              <div className={styles.rowActions}>
                <button
                  className={styles.secondaryButton}
                  disabled={!syncImportPath.trim() || busyAction === "sync-import"}
                  onClick={() => void handleImportSyncPacket()}
                  type="button"
                >
                  Import sync packet
                </button>
              </div>
            </div>
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
