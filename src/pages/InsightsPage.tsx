import { useMemo } from "react";

import { BarChart } from "../components/BarChart";
import { LineChart } from "../components/LineChart";
import { MetricCard } from "../components/MetricCard";
import { MonthlyTotalsChart } from "../components/MonthlyTotalsChart";
import { SectionCard } from "../components/SectionCard";
import { currency, monthLabel } from "../lib/format";
import type { InsightSnapshot } from "../lib/types";
import styles from "./Page.module.css";

interface InsightsPageProps {
  snapshot: InsightSnapshot;
  onWhy: (metricId: string) => void;
}

export function InsightsPage({ snapshot, onWhy }: InsightsPageProps) {
  const monthlyRows = useMemo(() => {
    const activityByMonth = new Map(
      snapshot.activity_groups.map((group) => [group.month_key, group]),
    );

    return snapshot.monthly_series.map((series) => {
      const activity = activityByMonth.get(series.month_key);
      return {
        ...series,
        funding: activity?.total_funding ?? 0,
        net_spend: activity?.total_expense ?? 0,
        rent_credit: activity?.total_rent_credit ?? 0,
      };
    });
  }, [snapshot.activity_groups, snapshot.monthly_series]);

  const overMaxMonths = monthlyRows.filter((row) => row.cap > 0 && row.spent > row.cap);
  const finalMonth = monthlyRows[monthlyRows.length - 1];
  const topCategory = [...snapshot.category_spend_this_month].sort((left, right) => {
    return right.value - left.value;
  })[0];
  const maxDifference = snapshot.this_month_capped_spend - snapshot.this_month_cap;
  const maxStatus =
    snapshot.this_month_cap <= 0
      ? "No monthly max is set."
      : maxDifference > 0
        ? `Over max by ${currency(maxDifference)}.`
        : `Under max by ${currency(Math.abs(maxDifference))}.`;

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Insights</p>
          <h1 className={styles.heroTitle}>Spending and plan totals</h1>
        </div>
      </div>

      <div className={styles.grid3}>
        <MetricCard
          eyebrow="Cash"
          note="Account balances after all persisted flows."
          onWhy={() => onWhy("total_available_cash")}
          title="Total available"
          value={currency(snapshot.total_available_cash)}
        />
        <MetricCard
          eyebrow="Current month"
          note={`Recommended max ${currency(snapshot.this_month_cap)}. ${maxStatus}`}
          onWhy={() => onWhy("this_month_spend")}
          title="Monthly max"
          valueTone="cap"
          value={`${currency(snapshot.this_month_capped_spend)} / ${currency(snapshot.this_month_cap)}`}
        />
        <MetricCard
          eyebrow="Planning"
          note="Money left after remaining recurring bills in the planning window."
          onWhy={() => onWhy("school_year_runway_remaining")}
          title="Planning balance"
          value={currency(snapshot.school_year_runway_remaining)}
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
          valueTone="planned"
          value={currency(snapshot.planned_total_spending)}
        />
        <MetricCard
          eyebrow="Prediction"
          note={`Remaining predicted spend ${currency(snapshot.predicted_remaining_spending)}.`}
          onWhy={() => onWhy("predicted_total_spending")}
          title="Predicted total spending"
          valueTone="predicted"
          value={currency(snapshot.predicted_total_spending)}
        />
      </div>

      <div className={styles.grid2}>
        <MetricCard
          eyebrow="Planning"
          note="Includes remaining recurring bills and monthly maximums."
          onWhy={() => onWhy("projected_end_of_year_cushion")}
          title="Projected end balance"
          value={currency(snapshot.projected_end_of_year_cushion)}
        />
        <MetricCard
          eyebrow="Rent"
          note="Paid minus rent credit, never below zero."
          onWhy={() => onWhy("rent_net_this_month")}
          title="Rent net this month"
          value={currency(snapshot.rent_net_this_month)}
        />
      </div>

      <div className={styles.grid2}>
        <SectionCard
          eyebrow="Planning window"
          title="Spent, planned, predicted, balance"
        >
          <LineChart data={snapshot.monthly_series} />
        </SectionCard>
        <SectionCard eyebrow="School year" title="Spending by month">
          <MonthlyTotalsChart data={snapshot.monthly_series} />
        </SectionCard>
      </div>

      <div className={styles.grid2}>
        <SectionCard eyebrow="School year" title="Average spend by category">
          <BarChart data={snapshot.category_average_spend} />
        </SectionCard>
        <SectionCard eyebrow="This month" title="Category totals this month">
          <BarChart data={snapshot.category_spend_this_month} />
        </SectionCard>
      </div>

      <div className={styles.grid2}>
        <SectionCard eyebrow="Rent" title="Rent summary">
          <div className={styles.statGrid}>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Due</div>
              <div className={styles.statValue}>{currency(snapshot.rent_due_this_month)}</div>
            </div>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Paid</div>
              <div className={styles.statValue}>{currency(snapshot.rent_paid_this_month)}</div>
            </div>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Rent credit</div>
              <div className={styles.statValue}>{currency(snapshot.rent_credit_this_month)}</div>
            </div>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Net</div>
              <div className={styles.statValue}>{currency(snapshot.rent_net_this_month)}</div>
            </div>
          </div>
          <div className={styles.summaryList}>
            <div className={styles.summaryRow}>
              <span>Credit rule</span>
              <span className={styles.inlineValue}>Rent credit offsets rent only</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Upcoming rent obligations</span>
              <span className={styles.inlineValue}>
                {
                  snapshot.upcoming_obligations.filter((item) => item.category === "rent").length
                }
              </span>
            </div>
            <div className={styles.summaryRow}>
              <span>Rent credit status</span>
              <span className={styles.inlineValue}>
                {snapshot.rent_credit_this_month > 0 ? "Credit recorded this month" : "None this month"}
              </span>
            </div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Planning window" title="Summary">
          <div className={styles.summaryList}>
            <div className={styles.summaryRow}>
              <span>Months loaded</span>
              <span className={styles.inlineValue}>{monthlyRows.length}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Over max months</span>
              <span className={styles.inlineValue}>{overMaxMonths.length}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Spending to date</span>
              <span className={styles.inlineValue}>{currency(snapshot.spending_to_date)}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Average monthly spend</span>
              <span className={styles.inlineValue}>{currency(snapshot.average_monthly_spend)}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Largest current category</span>
              <span className={styles.inlineValue}>
                {topCategory ? `${topCategory.label} ${currency(topCategory.value)}` : "No spend yet"}
              </span>
            </div>
            <div className={styles.summaryRow}>
              <span>Final balance</span>
              <span className={styles.inlineValue}>
                {finalMonth ? currency(finalMonth.runway_balance) : currency(0)}
              </span>
            </div>
          </div>
        </SectionCard>
      </div>

      <SectionCard eyebrow="Planning window" title="Month-by-month totals">
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Month</th>
                <th>Spent</th>
                <th>After income/credits</th>
                <th>Planned</th>
                <th>Predicted</th>
                <th>Ledger net</th>
                <th>Income</th>
                <th>Rent credit</th>
                <th>Max</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {monthlyRows.length ? (
                monthlyRows.map((row) => (
                  <tr key={row.month_key}>
                    <td>{monthLabel(row.month_key)}</td>
                    <td>{currency(row.gross_spend)}</td>
                    <td>{currency(row.actual_spend)}</td>
                    <td className={styles.plannedValue}>{currency(row.planned_spend)}</td>
                    <td className={styles.predictedValue}>{currency(row.predicted_spend)}</td>
                    <td>{currency(row.net_spend)}</td>
                    <td>{currency(row.funding)}</td>
                    <td>{currency(row.rent_credit)}</td>
                    <td className={styles.capValue}>{currency(row.cap)}</td>
                    <td>{currency(row.runway_balance)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className={styles.emptyState} colSpan={10}>
                    No monthly insight rows available yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
