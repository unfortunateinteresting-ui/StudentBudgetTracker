import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";

import {
  applyMissedRecurring,
  bootstrapState,
  getCalculationBreakdown,
  processSyncInbox,
  runStartupRecurringCheck,
} from "./lib/api";
import {
  dismissMissedRecurring,
  dismissSyncAlert,
  filterDismissedMissedRecurring,
  isSyncAlertDismissed,
} from "./lib/dismissals";
import { applyThemeMode, readThemeMode } from "./lib/theme";
import type { ThemeMode } from "./lib/theme";
import type {
  BootstrapState,
  BreakdownResult,
  LedgerEntry,
  MissedRecurringOccurrence,
  Workspace,
} from "./lib/types";
import { Sidebar } from "./components/Sidebar";
import { EntryDialog } from "./components/EntryDialog";
import { MissedRecurringBanner } from "./components/MissedRecurringBanner";
import { WhyDialog } from "./components/WhyDialog";
import { AccountsPage } from "./pages/AccountsPage";
import { ActivityPage } from "./pages/ActivityPage";
import { HomePage } from "./pages/HomePage";
import { InsightsPage } from "./pages/InsightsPage";
import { PlanPage } from "./pages/PlanPage";
import { SettingsPage } from "./pages/SettingsPage";
import styles from "./App.module.css";

const SYNC_EVENT_UPDATED = "sync-updated";
const SYNC_EVENT_ATTENTION = "sync-attention";

export function App() {
  const [workspace, setWorkspace] = useState<Workspace>("home");
  const [theme, setTheme] = useState<ThemeMode>(() => readThemeMode());
  const [bootstrap, setBootstrap] = useState<BootstrapState | null>(null);
  const [error, setError] = useState<string>("");
  const [entryDialogOpen, setEntryDialogOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<LedgerEntry | null>(null);
  const [whyOpen, setWhyOpen] = useState(false);
  const [breakdown, setBreakdown] = useState<BreakdownResult | null>(null);
  const [missedRecurring, setMissedRecurring] = useState<MissedRecurringOccurrence[]>([]);
  const [applyingMissedRecurring, setApplyingMissedRecurring] = useState(false);
  const [syncInboxAlert, setSyncInboxAlert] = useState<string>("");
  const syncInboxBusyRef = useRef(false);
  const refreshInFlightRef = useRef<Promise<void> | null>(null);
  const refreshQueuedRef = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshInFlightRef.current) {
      refreshQueuedRef.current = true;
      await refreshInFlightRef.current;
      return;
    }

    do {
      refreshQueuedRef.current = false;
      refreshInFlightRef.current = (async () => {
        try {
          const data = await bootstrapState();
          setBootstrap(data);
          setError("");
        } catch (err) {
          setError(String(err));
        }
      })();
      await refreshInFlightRef.current;
      refreshInFlightRef.current = null;
    } while (refreshQueuedRef.current);
  }, []);

  const showSyncInboxAlert = useCallback((message: string) => {
    if (!message || isSyncAlertDismissed(message)) {
      return;
    }
    setSyncInboxAlert(message);
  }, []);

  const loadMissedRecurring = useCallback(async () => {
    try {
      const missed = (await runStartupRecurringCheck()) as MissedRecurringOccurrence[];
      setMissedRecurring(filterDismissedMissedRecurring(missed));
    } catch {
      setMissedRecurring([]);
    }
  }, []);

  const scanSyncInbox = useCallback(
    async (showFailureAlert = true) => {
      if (syncInboxBusyRef.current) {
        return;
      }
      syncInboxBusyRef.current = true;
      try {
        const result = await processSyncInbox();
        if (result.failed_files > 0) {
          if (showFailureAlert) {
            showSyncInboxAlert(
              `Sync inbox moved ${result.failed_files} file(s) to the failed folder. Open Settings > Local sync to review the paths.`,
            );
          }
          await refresh();
          return;
        }
        if (result.processed_files > 0) {
          await refresh();
        }
      } catch {
        if (showFailureAlert) {
          showSyncInboxAlert(
            "Automatic sync inbox scan failed. Open Settings > Local sync and run Scan inbox now.",
          );
        }
      } finally {
        syncInboxBusyRef.current = false;
      }
    },
    [refresh, showSyncInboxAlert],
  );

  useEffect(() => {
    applyThemeMode(theme);
  }, [theme]);

  useEffect(() => {
    void refresh();
    void loadMissedRecurring();

    const interval = window.setInterval(() => {
      void loadMissedRecurring();
      void refresh();
    }, 60 * 60 * 1000);

    return () => window.clearInterval(interval);
  }, [loadMissedRecurring, refresh]);

  useEffect(() => {
    const handleFocus = () => {
      void scanSyncInbox(true);
    };

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        void scanSyncInbox(true);
      }
    };

    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [scanSyncInbox]);

  useEffect(() => {
    let unlistenUpdated: (() => void) | undefined;
    let unlistenAttention: (() => void) | undefined;

    void (async () => {
      unlistenUpdated = await listen(SYNC_EVENT_UPDATED, async () => {
        await refresh();
        await loadMissedRecurring();
      });
      unlistenAttention = await listen<{ message?: string }>(SYNC_EVENT_ATTENTION, async (event) => {
        const message =
          typeof event.payload?.message === "string"
            ? event.payload.message
            : "Sync attention is required. Open Settings > Local sync for details.";
        showSyncInboxAlert(message);
        await refresh();
      });
    })();

    return () => {
      unlistenUpdated?.();
      unlistenAttention?.();
    };
  }, [loadMissedRecurring, refresh, showSyncInboxAlert]);

  const openGuidedCreate = useCallback(() => {
    setEditingEntry(null);
    setEntryDialogOpen(true);
  }, []);

  const openGuidedEdit = useCallback((entry: LedgerEntry) => {
    setEditingEntry(entry);
    setEntryDialogOpen(true);
  }, []);

  const handleWhy = useCallback(async (metricId: string) => {
    const result = await getCalculationBreakdown(metricId);
    setBreakdown(result);
    setWhyOpen(true);
  }, []);

  const handleApplyMissed = useCallback(
    async (recurringRuleIds?: string[]) => {
      setApplyingMissedRecurring(true);
      try {
        await applyMissedRecurring(recurringRuleIds);
        await refresh();
        await loadMissedRecurring();
      } finally {
        setApplyingMissedRecurring(false);
      }
    },
    [loadMissedRecurring, refresh],
  );

  const content = useMemo(() => {
    if (!bootstrap) return null;
    switch (workspace) {
      case "activity":
        return (
          <ActivityPage
            accounts={bootstrap.accounts}
            entries={bootstrap.entries}
            monthlyCaps={bootstrap.monthly_caps}
            onCreate={openGuidedCreate}
            onEdit={openGuidedEdit}
            onRefresh={refresh}
            recurringRules={bootstrap.recurring_rules}
          />
        );
      case "plan":
        return (
          <PlanPage
            accounts={bootstrap.accounts}
            monthlyCaps={bootstrap.monthly_caps}
            onWhy={handleWhy}
            onRefresh={refresh}
            recurringRules={bootstrap.recurring_rules}
            settings={bootstrap.settings}
            snapshot={bootstrap.insight_snapshot}
          />
        );
      case "accounts":
        return <AccountsPage accounts={bootstrap.accounts} onRefresh={refresh} />;
      case "insights":
        return <InsightsPage onWhy={handleWhy} snapshot={bootstrap.insight_snapshot} />;
      case "settings":
        return (
          <SettingsPage
            backups={bootstrap.backup_files}
            localSync={bootstrap.local_sync}
            migrationStatus={bootstrap.migration_status}
            onRefresh={refresh}
            recoveryNotice={bootstrap.recovery_notice}
            settings={bootstrap.settings}
          />
        );
      case "home":
      default:
        return (
          <HomePage
            accounts={bootstrap.accounts}
            entries={bootstrap.entries}
            monthlyCaps={bootstrap.monthly_caps}
            onRefresh={refresh}
            onWhy={handleWhy}
            recurringRules={bootstrap.recurring_rules}
            snapshot={bootstrap.insight_snapshot}
          />
        );
    }
  }, [bootstrap, handleWhy, openGuidedCreate, openGuidedEdit, refresh, workspace]);

  return (
    <div className={styles.shell}>
      <Sidebar
        onSelect={setWorkspace}
        onToggleTheme={() => setTheme((value) => (value === "dark" ? "light" : "dark"))}
        theme={theme}
        workspace={workspace}
      />
      <main className={styles.content}>
        <div className={styles.frame}>
          {syncInboxAlert ? (
            <div className={styles.topBanner}>
              <div>
                <div className={styles.topBannerTitle}>Sync inbox attention needed</div>
                <div>{syncInboxAlert}</div>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.ghost}
                  onClick={() => {
                    dismissSyncAlert(syncInboxAlert);
                    setSyncInboxAlert("");
                  }}
                  type="button"
                >
                  Dismiss
                </button>
                <button
                  className={styles.button}
                  onClick={() => setWorkspace("settings")}
                  type="button"
                >
                  Open settings
                </button>
              </div>
            </div>
          ) : null}

          <MissedRecurringBanner
            busy={applyingMissedRecurring}
            missedRecurring={missedRecurring}
            onApply={handleApplyMissed}
            onDismiss={() => {
              dismissMissedRecurring(missedRecurring);
              setMissedRecurring([]);
            }}
          />

          {error ? (
            <div className={styles.error}>{error}</div>
          ) : content || (
            <div className={styles.status}>Loading...</div>
          )}
        </div>
      </main>

      <EntryDialog
        accounts={bootstrap?.accounts ?? []}
        entries={bootstrap?.entries ?? []}
        entry={editingEntry}
        monthlyCaps={bootstrap?.monthly_caps ?? []}
        onOpenChange={setEntryDialogOpen}
        onSaved={refresh}
        open={entryDialogOpen}
        recurringRules={bootstrap?.recurring_rules ?? []}
      />
      <WhyDialog breakdown={breakdown} onOpenChange={setWhyOpen} open={whyOpen} />
    </div>
  );
}
