import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as api from "./lib/api";

vi.mock("./lib/api", () => ({
  applyMissedRecurring: vi.fn(),
  bootstrapState: vi.fn(),
  getCalculationBreakdown: vi.fn(),
  processSyncInbox: vi.fn(),
  runStartupRecurringCheck: vi.fn(),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

vi.mock("./components/Sidebar", () => ({
  Sidebar: () => <div>Sidebar</div>,
}));

vi.mock("./components/EntryDialog", () => ({
  EntryDialog: () => null,
}));

vi.mock("./components/WhyDialog", () => ({
  WhyDialog: () => null,
}));

vi.mock("./components/MissedRecurringBanner", () => ({
  MissedRecurringBanner: () => null,
}));

vi.mock("./pages/HomePage", () => ({
  HomePage: () => <div>Home page</div>,
}));

vi.mock("./pages/ActivityPage", () => ({
  ActivityPage: () => <div>Activity page</div>,
}));

vi.mock("./pages/PlanPage", () => ({
  PlanPage: () => <div>Plan page</div>,
}));

vi.mock("./pages/AccountsPage", () => ({
  AccountsPage: () => <div>Accounts page</div>,
}));

vi.mock("./pages/InsightsPage", () => ({
  InsightsPage: () => <div>Insights page</div>,
}));

vi.mock("./pages/SettingsPage", () => ({
  SettingsPage: () => <div>Settings page</div>,
}));

const bootstrapFixture = {
  accounts: [],
  entries: [],
  recurring_rules: [],
  monthly_caps: [],
  settings: {
    school_year_start_month: 9,
    planning_start_month_key: "2025-09",
    school_year_months: 9,
    language: "en",
    backup_retention: 50,
    last_migration_version: 2,
  },
  insight_snapshot: {
    total_available_cash: 0,
    this_month_spend: 0,
    this_month_cap: 0,
    school_year_runway_remaining: 0,
    projected_end_of_year_cushion: 0,
    rent_due_this_month: 0,
    rent_paid_this_month: 0,
    rent_credit_this_month: 0,
    rent_net_this_month: 0,
    upcoming_obligations: [],
    recent_activity: [],
    account_balances: [],
    category_spend_this_month: [],
    monthly_series: [],
    activity_groups: [],
    breakdowns: {},
  },
  backup_files: [],
  migration_status: {
    has_legacy_db: false,
    has_run: true,
    legacy_path: null,
    last_run_at: null,
  },
  local_sync: {
    device_id: "device-1",
    device_name: "Dorm laptop",
    local_ipv4_addresses: ["192.168.1.250"],
    pending_operations: 0,
    inbox_packet_count: 0,
    trusted_peers: [],
    last_sync_at_utc: null,
    last_error: null,
    transport_mode: "localsend_assisted_packet_exchange_v1",
    localsend_available: true,
    localsend_path: "C:\\Program Files\\LocalSend\\localsend_app.exe",
    inbox_watch_active: true,
    lan_direct_available: true,
    lan_sync_port: 38256,
    sync_inbox_path: "C:\\Sync\\Inbox",
    sync_archive_path: "C:\\Sync\\Archive",
    sync_failed_path: "C:\\Sync\\Failed",
  },
  recovery_notice: null,
};

describe("App", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.bootstrapState).mockResolvedValue(bootstrapFixture);
    vi.mocked(api.runStartupRecurringCheck).mockResolvedValue([]);
    vi.mocked(api.processSyncInbox).mockResolvedValue({
      inbox_path: "C:\\Sync\\Inbox",
      archive_path: "C:\\Sync\\Archive",
      failed_path: "C:\\Sync\\Failed",
      scanned_files: 0,
      processed_files: 0,
      failed_files: 0,
      imported_operations: 0,
      skipped_operations: 0,
    });
    vi.mocked(api.getCalculationBreakdown).mockResolvedValue({
      metric_id: "metric",
      title: "Metric",
      lines: [],
    });
    vi.mocked(api.applyMissedRecurring).mockResolvedValue(undefined);
  });

  it("bootstraps the app and renders the home workspace", async () => {
    await act(async () => {
      render(<App />);
      await Promise.resolve();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(api.bootstrapState).toHaveBeenCalledTimes(1);
    });
    expect(api.runStartupRecurringCheck).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Home page")).toBeInTheDocument();
  });

  it("shows an alert when automatic inbox processing fails", async () => {
    vi.mocked(api.processSyncInbox).mockRejectedValueOnce(new Error("Scan failed"));

    await act(async () => {
      render(<App />);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(api.bootstrapState).toHaveBeenCalledTimes(1);

    await act(async () => {
      window.dispatchEvent(new Event("focus"));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(
      screen.getByText(
        "Automatic sync inbox scan failed. Open Settings > Local sync and run Scan inbox now.",
      ),
    ).toBeInTheDocument();
  });
});
