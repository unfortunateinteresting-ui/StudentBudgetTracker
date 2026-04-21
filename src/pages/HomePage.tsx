import { useMemo } from "react";

import { BarChart } from "../components/BarChart";
import { MetricCard } from "../components/MetricCard";
import { QuickAddBar } from "../components/QuickAddBar";
import { SectionCard } from "../components/SectionCard";
import { compactDate, currency } from "../lib/format";
import type { Account, InsightSnapshot } from "../lib/types";
import styles from "./Page.module.css";

interface HomePageProps {
  accounts: Account[];
  snapshot: InsightSnapshot;
  onRefresh: () => Promise<void>;
  onWhy: (metricId: string) => void;
}

export function HomePage({ accounts, snapshot, onRefresh, onWhy }: HomePageProps) {
  const accountNameById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account.name])),
    [accounts],
  );

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Overview</p>
          <h1 className={styles.heroTitle}>Budget overview</h1>
          <p className={styles.heroText}>
            Review available cash, this month&apos;s spending, rent totals, and upcoming bills in
            one place.
          </p>
        </div>
      </div>

      <QuickAddBar accounts={accounts} onSaved={onRefresh} />

      <div className={styles.grid4}>
        <MetricCard
          eyebrow="Cash"
          note="Opening balances + funding + rent credits + adjustments - expenses."
          onWhy={() => onWhy("total_available_cash")}
          title="Total available"
          value={currency(snapshot.total_available_cash)}
        />
        <MetricCard
          eyebrow="This month"
          note={`Cap ${currency(snapshot.this_month_cap)} vs spend ${currency(snapshot.this_month_spend)}.`}
          onWhy={() => onWhy("this_month_spend")}
          title="This month spent"
          value={`${currency(snapshot.this_month_spend)} / ${currency(snapshot.this_month_cap)}`}
        />
        <MetricCard
          eyebrow="School year"
          note="Money left after remaining fixed bills for the school year."
          onWhy={() => onWhy("school_year_runway_remaining")}
          title="School-year balance"
          value={currency(snapshot.school_year_runway_remaining)}
        />
        <MetricCard
          eyebrow="School year"
          note="Estimated balance after remaining bills and caps."
          onWhy={() => onWhy("projected_end_of_year_cushion")}
          title="Projected end balance"
          value={currency(snapshot.projected_end_of_year_cushion)}
        />
      </div>

      <div className={styles.grid2}>
        <SectionCard
          action={
            <button
              className={styles.secondaryButton}
              onClick={() => onWhy("rent_net_this_month")}
              type="button"
            >
              Why?
            </button>
          }
          eyebrow="Rent"
          title="Rent this month"
        >
          <div className={styles.grid2}>
            <div>
              <p className={styles.kicker}>Due</p>
              <strong>{currency(snapshot.rent_due_this_month)}</strong>
            </div>
            <div>
              <p className={styles.kicker}>Paid</p>
              <strong>{currency(snapshot.rent_paid_this_month)}</strong>
            </div>
            <div>
              <p className={styles.kicker}>Credit</p>
              <strong>{currency(snapshot.rent_credit_this_month)}</strong>
            </div>
            <div>
              <p className={styles.kicker}>Net</p>
              <strong>{currency(snapshot.rent_net_this_month)}</strong>
            </div>
          </div>
        </SectionCard>
        <SectionCard eyebrow="Upcoming" title="Upcoming bills">
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Due</th>
                <th>Label</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.upcoming_obligations.slice(0, 5).map((item) => (
                <tr key={`${item.recurring_rule_id}-${item.due_date}`}>
                  <td>{compactDate(item.due_date)}</td>
                  <td>{item.label}</td>
                  <td>{currency(item.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </SectionCard>
      </div>

      <div className={styles.grid2}>
        <SectionCard eyebrow="Accounts" title="Account totals">
          <BarChart color="var(--color-forest)" data={snapshot.account_balances} />
        </SectionCard>
        <SectionCard eyebrow="Categories" title="Category totals this month">
          <BarChart data={snapshot.category_spend_this_month} />
        </SectionCard>
      </div>

      <SectionCard eyebrow="Recent activity" title="Recent transactions">
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Account</th>
              <th>Label</th>
              <th>Kind</th>
              <th>Category</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {snapshot.recent_activity.slice(0, 8).map((entry) => (
              <tr key={entry.id}>
                <td>{compactDate(entry.occurred_at_local)}</td>
                <td>{accountNameById.get(entry.account_id) ?? entry.account_id}</td>
                <td>{entry.label}</td>
                <td>{entry.entry_kind}</td>
                <td>{entry.category}</td>
                <td>{currency(entry.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>
    </div>
  );
}
