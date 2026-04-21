import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import * as dialogs from "../lib/dialogs";
import { SettingsPage } from "./SettingsPage";

vi.mock("../lib/api", () => ({
  createBackupNow: vi.fn(),
  exportJsonV2: vi.fn(),
  importJson: vi.fn(),
  resetAllData: vi.fn(),
  restoreBackup: vi.fn(),
  runLegacyMigration: vi.fn(),
  undoLastAction: vi.fn(),
  updateAppSettings: vi.fn(),
}));

vi.mock("../lib/dialogs", () => ({
  chooseJsonExportPath: vi.fn(),
  chooseJsonImportPath: vi.fn(),
}));

const settings = {
  school_year_start_month: 9,
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

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.createBackupNow).mockResolvedValue(undefined);
    vi.mocked(api.exportJsonV2).mockResolvedValue(undefined);
    vi.mocked(api.importJson).mockResolvedValue(undefined);
    vi.mocked(api.resetAllData).mockResolvedValue(undefined);
    vi.mocked(api.restoreBackup).mockResolvedValue(undefined);
    vi.mocked(api.runLegacyMigration).mockResolvedValue(undefined);
    vi.mocked(api.undoLastAction).mockResolvedValue(undefined);
    vi.mocked(api.updateAppSettings).mockResolvedValue(undefined);
    vi.mocked(dialogs.chooseJsonExportPath).mockResolvedValue(null);
    vi.mocked(dialogs.chooseJsonImportPath).mockResolvedValue(null);
  });

  it("updates school-year and backup settings and refreshes derived state", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingsPage
        backups={[]}
        migrationStatus={migrationStatus}
        onRefresh={onRefresh}
        settings={settings}
      />,
    );

    await user.selectOptions(screen.getByLabelText("School-year start month"), "1");
    await user.clear(screen.getByLabelText("School-year length in months"));
    await user.type(screen.getByLabelText("School-year length in months"), "8");
    await user.clear(screen.getByLabelText("Backup retention copies"));
    await user.type(screen.getByLabelText("Backup retention copies"), "24");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => {
      expect(api.updateAppSettings).toHaveBeenCalledWith({
        school_year_start_month: 1,
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
});
