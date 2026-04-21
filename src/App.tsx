import { useCallback, useEffect, useMemo, useState } from "react";

import {
  applyMissedRecurring,
  bootstrapState,
  getCalculationBreakdown,
  runStartupRecurringCheck,
} from "./lib/api";
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

export function App() {
  const [workspace, setWorkspace] = useState<Workspace>("home");
  const [bootstrap, setBootstrap] = useState<BootstrapState | null>(null);
  const [error, setError] = useState<string>("");
  const [entryDialogOpen, setEntryDialogOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<LedgerEntry | null>(null);
  const [whyOpen, setWhyOpen] = useState(false);
  const [breakdown, setBreakdown] = useState<BreakdownResult | null>(null);
  const [missedRecurring, setMissedRecurring] = useState<MissedRecurringOccurrence[]>([]);
  const [applyingMissedRecurring, setApplyingMissedRecurring] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await bootstrapState();
      setBootstrap(data);
      setError("");
    } catch (err) {
      setError(String(err));
    }
  }, []);

  const loadMissedRecurring = useCallback(async () => {
    try {
      const missed = (await runStartupRecurringCheck()) as MissedRecurringOccurrence[];
      setMissedRecurring(missed);
    } catch {
      setMissedRecurring([]);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void loadMissedRecurring();

    const interval = window.setInterval(() => {
      void loadMissedRecurring();
      void refresh();
    }, 60 * 60 * 1000);

    return () => window.clearInterval(interval);
  }, [loadMissedRecurring, refresh]);

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
            onCreate={openGuidedCreate}
            onEdit={openGuidedEdit}
            onRefresh={refresh}
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
            onRefresh={refresh}
            onWhy={handleWhy}
            snapshot={bootstrap.insight_snapshot}
          />
        );
    }
  }, [bootstrap, handleWhy, openGuidedCreate, openGuidedEdit, refresh, workspace]);

  return (
    <div className={styles.shell}>
      <Sidebar onSelect={setWorkspace} workspace={workspace} />
      <main className={styles.content}>
        <div className={styles.frame}>
          <MissedRecurringBanner
            busy={applyingMissedRecurring}
            missedRecurring={missedRecurring}
            onApply={handleApplyMissed}
            onDismiss={() => setMissedRecurring([])}
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
        entry={editingEntry}
        onOpenChange={setEntryDialogOpen}
        onSaved={refresh}
        open={entryDialogOpen}
      />
      <WhyDialog breakdown={breakdown} onOpenChange={setWhyOpen} open={whyOpen} />
    </div>
  );
}
