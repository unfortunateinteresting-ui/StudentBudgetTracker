import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import * as dialogs from "../lib/dialogs";
import { SettingsPage } from "./SettingsPage";

vi.mock("../lib/api", () => ({
  createBackupNow: vi.fn(),
  discoverLanPeers: vi.fn(),
  exportJsonV2: vi.fn(),
  exportSyncPacketForLocalSend: vi.fn(),
  exportSyncPacket: vi.fn(),
  importJson: vi.fn(),
  importSyncPacket: vi.fn(),
  openSyncInboxFolder: vi.fn(),
  processSyncInbox: vi.fn(),
  resetAllData: vi.fn(),
  restoreBackup: vi.fn(),
  runLegacyMigration: vi.fn(),
  syncWithLanPeer: vi.fn(),
  undoLastAction: vi.fn(),
  updateAppSettings: vi.fn(),
  updateLocalSyncDeviceName: vi.fn(),
}));

vi.mock("../lib/dialogs", () => ({
  chooseJsonExportPath: vi.fn(),
  chooseJsonImportPath: vi.fn(),
  chooseSyncPacketExportPath: vi.fn(),
  chooseSyncPacketImportPath: vi.fn(),
}));

const settings = {
  school_year_start_month: 9,
  planning_start_month_key: "2025-09",
  school_year_months: 9,
  language: "en",
  backup_retention: 50,
  last_migration_version: 2,
};

const migrationStatus = {
  has_legacy_db: true,
  has_run: false,
  legacy_path: "C:\\Legacy\\budget.db",
  last_run_at: null,
};

const localSync = {
  device_id: "device-1",
  device_name: "Dorm laptop",
  local_ipv4_addresses: ["192.168.1.250"],
  pending_operations: 3,
  inbox_packet_count: 2,
  trusted_peers: [],
  last_sync_at_utc: null,
  last_error: null,
  transport_mode: "localsend_assisted_packet_exchange_v1",
  localsend_available: true,
  localsend_path: "C:\\Program Files\\LocalSend\\localsend_app.exe",
  inbox_watch_active: true,
  lan_direct_available: true,
  lan_sync_port: 38256,
  sync_inbox_path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-inbox",
  sync_archive_path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-archive",
  sync_failed_path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-failed",
};

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.createBackupNow).mockResolvedValue(undefined);
    vi.mocked(api.discoverLanPeers).mockResolvedValue([
      {
        device_id: "device-2",
        device_name: "Dorm desktop",
        address: "192.168.1.44",
        port: 38256,
        trusted: true,
        last_sync_at_utc: "2026-04-21T10:00:00",
      },
    ]);
    vi.mocked(api.exportJsonV2).mockResolvedValue(undefined);
    vi.mocked(api.exportSyncPacketForLocalSend).mockResolvedValue({
      path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-packets\\student-budget-sync_20260421_101500.json",
      operation_count: 3,
      localsend_path: "C:\\Program Files\\LocalSend\\localsend_app.exe",
      explorer_revealed: true,
    });
    vi.mocked(api.exportSyncPacket).mockResolvedValue({
      path: "C:\\Sync\\student-budget-sync.json",
      operation_count: 3,
    });
    vi.mocked(api.importJson).mockResolvedValue(undefined);
    vi.mocked(api.importSyncPacket).mockResolvedValue({
      source_device_id: "device-2",
      source_device_name: "Dorm desktop",
      imported_operations: 2,
      skipped_operations: 1,
      trusted_peer_added: true,
    });
    vi.mocked(api.openSyncInboxFolder).mockResolvedValue(
      "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-inbox",
    );
    vi.mocked(api.processSyncInbox).mockResolvedValue({
      inbox_path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-inbox",
      archive_path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-archive",
      failed_path: "C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-failed",
      scanned_files: 2,
      processed_files: 1,
      failed_files: 1,
      imported_operations: 2,
      skipped_operations: 0,
    });
    vi.mocked(api.resetAllData).mockResolvedValue(undefined);
    vi.mocked(api.restoreBackup).mockResolvedValue(undefined);
    vi.mocked(api.runLegacyMigration).mockResolvedValue(undefined);
    vi.mocked(api.syncWithLanPeer).mockResolvedValue({
      peer_device_id: "device-2",
      peer_device_name: "Dorm desktop",
      address: "192.168.1.44",
      port: 38256,
      sent_operations: 3,
      peer_imported_operations: 2,
      peer_skipped_operations: 1,
    });
    vi.mocked(api.undoLastAction).mockResolvedValue(undefined);
    vi.mocked(api.updateAppSettings).mockResolvedValue(undefined);
    vi.mocked(api.updateLocalSyncDeviceName).mockResolvedValue(undefined);
    vi.mocked(dialogs.chooseJsonExportPath).mockResolvedValue(null);
    vi.mocked(dialogs.chooseJsonImportPath).mockResolvedValue(null);
    vi.mocked(dialogs.chooseSyncPacketExportPath).mockResolvedValue(null);
    vi.mocked(dialogs.chooseSyncPacketImportPath).mockResolvedValue(null);
  });

  it("updates planning and backup settings and refreshes derived state", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.clear(screen.getByLabelText("Planning window in months"));
    await user.type(screen.getByLabelText("Planning window in months"), "8");
    await user.clear(screen.getByLabelText("Backup retention copies"));
    await user.type(screen.getByLabelText("Backup retention copies"), "24");
    await user.clear(screen.getByLabelText("Planning window start"));
    await user.type(screen.getByLabelText("Planning window start"), "2025-08");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(api.updateAppSettings).toHaveBeenCalledWith({
        planning_start_month_key: "2025-08",
        school_year_months: 8,
        backup_retention: 24,
      });
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(screen.getByText("Settings updated.")).toBeInTheDocument();
  });

  it("exports JSON with a trimmed path and does not refresh afterwards", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    const exportButton = screen.getByRole("button", { name: "Export JSON v2" });
    expect(exportButton).toBeDisabled();

    await user.type(
      screen.getByPlaceholderText(/budget-export\.json/i),
      "  C:\\Exports\\budget.json  ",
    );
    expect(exportButton).not.toBeDisabled();

    await user.click(exportButton);

    await waitFor(() => {
      expect(api.exportJsonV2).toHaveBeenCalledWith("C:\\Exports\\budget.json");
    });
    expect(screen.getByText("Exported JSON to C:\\Exports\\budget.json.")).toBeInTheDocument();
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("fills the export path from the file dialog", async () => {
    const user = userEvent.setup();

    vi.mocked(dialogs.chooseJsonExportPath).mockResolvedValue("C:\\Exports\\picked.json");

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Choose export location" }));

    expect(dialogs.chooseJsonExportPath).toHaveBeenCalledWith("");
    expect(screen.getByLabelText("Export JSON path")).toHaveValue("C:\\Exports\\picked.json");
  });

  it("fills the import path from the file dialog and imports it", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    vi.mocked(dialogs.chooseJsonImportPath).mockResolvedValue("C:\\Imports\\picked.json");

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Choose import file" }));

    expect(dialogs.chooseJsonImportPath).toHaveBeenCalledWith("");
    expect(screen.getByLabelText("Import JSON path")).toHaveValue("C:\\Imports\\picked.json");

    await user.click(screen.getByRole("button", { name: "Import JSON" }));

    await waitFor(() => {
      expect(api.importJson).toHaveBeenCalledWith("C:\\Imports\\picked.json");
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(screen.getByText("Imported data from C:\\Imports\\picked.json.")).toBeInTheDocument();
  });

  it("requires explicit confirmation before restoring a listed backup", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[
          {
            file_name: "budget_20260419_194500.db",
            created_at: "2026-04-19 19:45:00",
            full_path: "C:\\Backups\\budget_20260419_194500.db",
          },
        ]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Restore" }));

    expect(api.restoreBackup).not.toHaveBeenCalled();
    expect(screen.getByText("Confirm backup restore")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm restore" })).toBeDisabled();

    await user.type(screen.getByLabelText("Restore confirmation phrase"), "RESTORE");
    expect(screen.getByRole("button", { name: "Confirm restore" })).not.toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Confirm restore" }));

    await waitFor(() => {
      expect(api.restoreBackup).toHaveBeenCalledWith(
        "C:\\Backups\\budget_20260419_194500.db",
      );
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(
      screen.getByText("Restored budget_20260419_194500.db."),
    ).toBeInTheDocument();
  });

  it("keeps reset disabled until RESET is typed and then refreshes after reset", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    const resetButton = screen.getByRole("button", { name: "Reset all data" });
    expect(resetButton).toBeDisabled();

    await user.type(screen.getByPlaceholderText("Type RESET"), "RESET");
    expect(resetButton).not.toBeDisabled();

    await user.click(resetButton);

    await waitFor(() => {
      expect(api.resetAllData).toHaveBeenCalled();
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(screen.getByText("All data reset.")).toBeInTheDocument();
  });

  it("updates the local sync device name and refreshes", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.clear(screen.getByLabelText("Device name"));
    await user.type(screen.getByLabelText("Device name"), "Campus desktop");
    await user.click(screen.getByRole("button", { name: "Save device name" }));

    await waitFor(() => {
      expect(api.updateLocalSyncDeviceName).toHaveBeenCalledWith({
        device_name: "Campus desktop",
      });
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(screen.getByText("Device name updated.")).toBeInTheDocument();
  });

  it("exports a sync packet and opens LocalSend", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Export and open LocalSend" }));

    await waitFor(() => {
      expect(api.exportSyncPacketForLocalSend).toHaveBeenCalled();
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(
      screen.getByText(
        /Exported 3 sync operations, opened LocalSend, and revealed/i,
      ),
    ).toBeInTheDocument();
  });

  it("scans the sync inbox and refreshes state", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Scan inbox now" }));

    await waitFor(() => {
      expect(api.processSyncInbox).toHaveBeenCalled();
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(
      screen.getByText("Scanned 2 inbox files, processed 1, failed 1."),
    ).toBeInTheDocument();
  });

  it("opens the sync inbox folder", async () => {
    const user = userEvent.setup();

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Open sync inbox" }));

    await waitFor(() => {
      expect(api.openSyncInboxFolder).toHaveBeenCalled();
    });
    expect(
      screen.getByText(
        "Opened sync inbox at C:\\Users\\mouzzia\\AppData\\Roaming\\StudentBudgetTracker\\sync-inbox.",
      ),
    ).toBeInTheDocument();
  });

  it("exports a sync packet with the selected path", async () => {
    const user = userEvent.setup();

    vi.mocked(dialogs.chooseSyncPacketExportPath).mockResolvedValue(
      "C:\\Sync\\student-budget-sync.json",
    );

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Choose packet export location" }));

    expect(dialogs.chooseSyncPacketExportPath).toHaveBeenCalledWith("");
    expect(screen.getByLabelText("Export sync packet path")).toHaveValue(
      "C:\\Sync\\student-budget-sync.json",
    );

    await user.click(screen.getByRole("button", { name: "Export sync packet" }));

    await waitFor(() => {
      expect(api.exportSyncPacket).toHaveBeenCalledWith(
        "C:\\Sync\\student-budget-sync.json",
      );
    });
    expect(
      screen.getByText("Exported 3 sync operations to C:\\Sync\\student-budget-sync.json."),
    ).toBeInTheDocument();
  });

  it("imports a sync packet and refreshes state", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    vi.mocked(dialogs.chooseSyncPacketImportPath).mockResolvedValue(
      "C:\\Sync\\incoming-sync.json",
    );

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Choose sync packet file" }));

    expect(dialogs.chooseSyncPacketImportPath).toHaveBeenCalledWith("");
    expect(screen.getByLabelText("Import sync packet path")).toHaveValue(
      "C:\\Sync\\incoming-sync.json",
    );

    await user.click(screen.getByRole("button", { name: "Import sync packet" }));

    await waitFor(() => {
      expect(api.importSyncPacket).toHaveBeenCalledWith("C:\\Sync\\incoming-sync.json");
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(screen.getByText("Imported 2 sync operations from Dorm desktop.")).toBeInTheDocument();
  });

  it("auto-discovers LAN peers and shows send actions for them", async () => {
    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        settings={settings}
      />,
    );

    await waitFor(() => {
      expect(api.discoverLanPeers).toHaveBeenCalled();
    });
    expect(screen.getAllByText("Dorm desktop").length).toBeGreaterThan(0);
    expect(screen.getByText("192.168.1.44:38256")).toBeInTheDocument();
    expect(screen.getByText("Seen before")).toBeInTheDocument();
    expect(screen.getByText("2026-04-21T10:00:00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send updates" })).toBeInTheDocument();
  });

  it("sends updates to a detected device and refreshes state", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await screen.findByRole("button", { name: "Send updates" });
    await user.click(screen.getByRole("button", { name: "Send updates" }));

    await waitFor(() => {
      expect(api.syncWithLanPeer).toHaveBeenCalledWith({
        address: "192.168.1.44",
        port: 38256,
      });
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it("syncs with a manual LAN address and refreshes state", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        localSync={localSync}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.clear(screen.getByLabelText("Manual LAN address"));
    await user.type(screen.getByLabelText("Manual LAN address"), "192.168.1.77");
    await user.clear(screen.getByLabelText("Manual LAN port"));
    await user.type(screen.getByLabelText("Manual LAN port"), "38256");
    await user.click(screen.getByRole("button", { name: "Send to address" }));

    await waitFor(() => {
      expect(api.syncWithLanPeer).toHaveBeenCalledWith({
        address: "192.168.1.77",
        port: 38256,
      });
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(
      screen.getByText(
        "Synced 3 queued operations to Dorm desktop. Peer imported 2 new operations.",
      ),
    ).toBeInTheDocument();
  });
});
