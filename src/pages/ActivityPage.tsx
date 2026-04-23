import { useMemo, useState } from "react";

import { deleteEntry } from "../lib/api";
import { QuickAddBar } from "../components/QuickAddBar";
import { compactDate, currency, monthLabel } from "../lib/format";
import type { Account, LedgerEntry, MonthlyCap, RecurringRule } from "../lib/types";
import { MetricCard } from "../components/MetricCard";
import styles from "./Page.module.css";

interface ActivityPageProps {
  accounts: Account[];
  entries: LedgerEntry[];
  monthlyCaps: MonthlyCap[];
  onCreate: () => void;
  onEdit: (entry: LedgerEntry) => void;
  onRefresh: () => Promise<void>;
  recurringRules: RecurringRule[];
}

type ActivityTotals = {
  expense: number;
  funding: number;
  rentCredit: number;
  adjustment: number;
  excluded: number;
};

const zeroTotals = (): ActivityTotals => ({
  expense: 0,
  funding: 0,
  rentCredit: 0,
  adjustment: 0,
  excluded: 0,
});

export function ActivityPage({
  accounts,
  entries,
  monthlyCaps,
  onCreate,
  onEdit,
  onRefresh,
  recurringRules,
}: ActivityPageProps) {
  const [search, setSearch] = useState("");
  const [monthKey, setMonthKey] = useState("");
  const [accountId, setAccountId] = useState("");

  const accountNameById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account.name])),
    [accounts],
  );

  const monthOptions = useMemo(
    () =>
      Array.from(
        new Set(
          entries.map((entry) => entry.occurred_at_local.slice(0, 7)).filter(Boolean),
        ),
      ).sort((left, right) => right.localeCompare(left)),
    [entries],
  );

  const filtered = useMemo(() => {
    return entries.filter((entry) => {
      if (monthKey && !entry.occurred_at_local.startsWith(monthKey)) return false;
      if (accountId && entry.account_id !== accountId) return false;
      if (!search) return true;
      const haystack =
        `${entry.label} ${entry.category} ${entry.notes} ${entry.entry_kind}`.toLowerCase();
      return haystack.includes(search.toLowerCase());
    });
  }, [accountId, entries, monthKey, search]);

  const filteredTotals = useMemo(() => {
    return filtered.reduce((totals, entry) => {
      if (entry.entry_kind === "expense") totals.expense += entry.amount;
      if (entry.entry_kind === "funding") totals.funding += entry.amount;
      if (entry.entry_kind === "rent_credit") totals.rentCredit += entry.amount;
      if (entry.entry_kind === "adjustment") totals.adjustment += entry.amount;
      if (entry.exclude_from_insights) totals.excluded += 1;
      return totals;
    }, zeroTotals());
  }, [filtered]);

  const grouped = useMemo(() => {
    const byMonth = new Map<
      string,
      {
        entries: LedgerEntry[];
        totals: ActivityTotals;
      }
    >();

    filtered.forEach((entry) => {
      const key = entry.occurred_at_local.slice(0, 7) || "Unknown";
      const current = byMonth.get(key) ?? {
        entries: [],
        totals: zeroTotals(),
      };

      current.entries.push(entry);

      if (entry.entry_kind === "expense") current.totals.expense += entry.amount;
      if (entry.entry_kind === "funding") current.totals.funding += entry.amount;
      if (entry.entry_kind === "rent_credit") current.totals.rentCredit += entry.amount;
      if (entry.entry_kind === "adjustment") current.totals.adjustment += entry.amount;
      if (entry.exclude_from_insights) current.totals.excluded += 1;

      byMonth.set(key, current);
    });

    return Array.from(byMonth.entries()).sort(([left], [right]) => right.localeCompare(left));
  }, [filtered]);

  const handleDelete = async (entryId: string) => {
    await deleteEntry(entryId);
    await onRefresh();
  };

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Activity</p>
          <h1 className={styles.heroTitle}>Transaction history</h1>
          <p className={styles.heroText}>
            Search, filter, edit, and review entries by month and account.
          </p>
        </div>
        <button className={styles.primaryButton} onClick={onCreate} type="button">
          Guided entry
        </button>
      </div>

      <QuickAddBar
        accounts={accounts}
        entries={entries}
        monthlyCaps={monthlyCaps}
        onSaved={onRefresh}
        recurringRules={recurringRules}
      />

      <div className={styles.grid3}>
        <MetricCard
          eyebrow="Filtered expense"
          note={`${filtered.length} entry or entries in the current result set.`}
          title="Expenses"
          value={currency(filteredTotals.expense)}
        />
        <MetricCard
          eyebrow="Filtered inflow"
          note="Funding and rent credit stay separated in ledger math."
          title="Funding"
          value={currency(filteredTotals.funding)}
        />
        <MetricCard
          eyebrow="Rent offset"
          note={`${filteredTotals.excluded} excluded entr${filteredTotals.excluded === 1 ? "y" : "ies"} in view.`}
          title="Rent credit"
          value={currency(filteredTotals.rentCredit)}
        />
      </div>

      <div className={styles.filters}>
        <input
          aria-label="Search activity"
          className={styles.input}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search label, notes, category, kind"
          value={search}
        />
        <select
          aria-label="Filter by month"
          className={styles.select}
          onChange={(event) => setMonthKey(event.target.value)}
          value={monthKey}
        >
          <option value="">All months</option>
          {monthOptions.map((item) => (
            <option key={item} value={item}>
              {monthLabel(item)}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by account"
          className={styles.select}
          onChange={(event) => setAccountId(event.target.value)}
          value={accountId}
        >
          <option value="">All accounts</option>
          {accounts.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <button
          className={styles.secondaryButton}
          onClick={() => {
            setSearch("");
            setMonthKey("");
            setAccountId("");
          }}
          type="button"
        >
          Reset filters
        </button>
      </div>

      {grouped.length ? (
        grouped.map(([groupMonth, monthState]) => (
          <section className={styles.stack} key={groupMonth}>
            <div className={styles.groupHeader}>
              <div>
                <div className={styles.kicker}>{monthLabel(groupMonth)}</div>
                <strong>{monthState.entries.length} ledger entries</strong>
              </div>
              <div className={styles.groupTotals}>
                <span className={styles.groupTotal}>Expense {currency(monthState.totals.expense)}</span>
                <span className={styles.groupTotal}>Funding {currency(monthState.totals.funding)}</span>
                <span className={styles.groupTotal}>
                  Rent credit {currency(monthState.totals.rentCredit)}
                </span>
                <span className={styles.groupTotal}>
                  Adjustment {currency(monthState.totals.adjustment)}
                </span>
              </div>
            </div>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Account</th>
                    <th>Label</th>
                    <th>Kind</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Flags</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {monthState.entries.map((entry) => (
                    <tr key={entry.id}>
                      <td>{compactDate(entry.occurred_at_local)}</td>
                      <td>{accountNameById.get(entry.account_id) ?? entry.account_id}</td>
                      <td>{entry.label}</td>
                      <td>{entry.entry_kind}</td>
                      <td>{entry.category}</td>
                      <td>{currency(entry.amount)}</td>
                      <td>{entry.exclude_from_insights ? "Excluded" : ""}</td>
                      <td>
                        <div className={styles.rowActions}>
                          {entry.entry_kind !== "transfer" ? (
                            <button
                              className={styles.pillButton}
                              onClick={() => onEdit(entry)}
                              type="button"
                            >
                              Edit
                            </button>
                          ) : null}
                          <button
                            className={styles.dangerButton}
                            onClick={() => handleDelete(entry.id)}
                            type="button"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))
      ) : (
        <div className={styles.emptyPanel}>
          <strong>No entries match the current filters.</strong>
          <div className={styles.minor}>
            Reset the filters or create a new guided entry to populate the ledger.
          </div>
        </div>
      )}
    </div>
  );
}
