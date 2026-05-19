import { useMemo } from "react";

import { BarChart } from "../components/BarChart";
import { MetricCard } from "../components/MetricCard";
import { QuickAddBar } from "../components/QuickAddBar";
import { SectionCard } from "../components/SectionCard";
import { compactDate, currency, monthLabel } from "../lib/format";
import type { Account, InsightSnapshot, LedgerEntry, MonthlyCap, RecurringRule } from "../lib/types";
import styles from "./Page.module.css";

interface HomePageProps {
  accounts: Account[];
  entries: LedgerEntry[];
  monthlyCaps: MonthlyCap[];
  snapshot: InsightSnapshot;
  onRefresh: () => Promise<void>;
  onWhy: (metricId: string) => void;
  recurringRules: RecurringRule[];
}

export function HomePage({
  accounts,
  entries,
  monthlyCaps,
  snapshot,
  onRefresh,
  onWhy,
  recurringRules,
}: HomePageProps) {
  const accountNameById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account.name])),
    [accounts],
  );
  const monthlySpendBars = useMemo(
    () =>
      snapshot.monthly_spending_totals.map((point) => ({
        ...point,
        label: monthLabel(point.label),
      })),
    [snapshot.monthly_spending_totals],
  );

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Overview</p>
          <h1 className={styles.heroTitle}>Budget overview</h1>
        </div>
      </div>

      <QuickAddBar
        accounts={accounts}
        entries={entries}
        monthlyCaps={monthlyCaps}
        onSaved={onRefresh}
        recurringRules={recurringRules}
      />

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
          note={`Total net spend ${currency(snapshot.this_month_spend)}. Remaining cap room ${currency(
            snapshot.this_month_cap_remaining,
          )}.`}
          onWhy={() => onWhy("this_month_spend")}
          title="Capped spend"
          value={`${currency(snapshot.this_month_capped_spend)} / ${currency(snapshot.this_month_cap)}`}
        />
        <MetricCard
          eyebrow="Planning"
          note="Money left after remaining recurring bills in the planning window."
          onWhy={() => onWhy("school_year_runway_remaining")}
          title="Planning balance"
          value={currency(snapshot.school_year_runway_remaining)}
        />
        <MetricCard
          eyebrow="Planning"
          note="Estimated balance after remaining bills and caps in the planning window."
          onWhy={() => onWhy("projected_end_of_year_cushion")}
          title="Projected end balance"
          value={currency(snapshot.projected_end_of_year_cushion)}
        />
      </div>

      <div className={styles.grid3}>
        <MetricCard
          eyebrow="School year"
          note={`Average ${currency(snapshot.average_monthly_spend)} per elapsed month.`}
          onWhy={() => onWhy("spending_to_date")}
          title="Spending to date"
          value={currency(snapshot.spending_to_date)}
        />
        <MetricCard
          eyebrow="Plan"
          note={`Remaining planned spend ${currency(snapshot.planned_remaining_spending)}.`}
          onWhy={() => onWhy("planned_total_spending")}
          title="Planned total spending"
          value={currency(snapshot.planned_total_spending)}
        />
        <MetricCard
          eyebrow="Prediction"
          note={`Remaining predicted spend ${currency(snapshot.predicted_remaining_spending)}.`}
          onWhy={() => onWhy("predicted_total_spending")}
          title="Predicted total spending"
          value={currency(snapshot.predicted_total_spending)}
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
        <SectionCard eyebrow="School year" title="Spending by month">
          <BarChart color="var(--color-forest)" data={monthlySpendBars} />
        </SectionCard>
        <SectionCard eyebrow="School year" title="Average spend by category">
          <BarChart data={snapshot.category_average_spend} />
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
