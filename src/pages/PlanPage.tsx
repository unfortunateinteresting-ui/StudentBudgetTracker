import { useEffect, useMemo, useState } from "react";

import {
  applyRecurringRuleNow,
  createRecurringRule,
  deleteMonthlyCap,
  deleteRecurringRule,
  setMonthlyCap,
  updateRecurringRule,
} from "../lib/api";
import { currentMonthKey, currency, monthLabel } from "../lib/format";
import type {
  Account,
  AppSettings,
  EntryKind,
  InsightSnapshot,
  MonthlyCap,
  RecurringFrequency,
  RecurringRule,
  RecurringStatus,
} from "../lib/types";
import { MetricCard } from "../components/MetricCard";
import { SectionCard } from "../components/SectionCard";
import styles from "./Page.module.css";

interface PlanPageProps {
  accounts: Account[];
  recurringRules: RecurringRule[];
  monthlyCaps: MonthlyCap[];
  settings: AppSettings;
  snapshot: InsightSnapshot;
  onWhy: (metricId: string) => void;
  onRefresh: () => Promise<void>;
}

interface RuleFormState {
  label: string;
  entry_kind: Exclude<EntryKind, "transfer">;
  amount: string;
  account_id: string;
  category: string;
  notes: string;
  start_date: string;
  end_date: string;
  frequency: RecurringFrequency;
  status: RecurringStatus;
}

type NoticeState = {
  kind: "success" | "error";
  text: string;
};

type CapFormState = {
  category: string;
  amount: string;
  month_key: string;
};

type EditingCapState = {
  id: string;
  category: string;
  month_key: string;
};

const monthName = (month: number) =>
  new Intl.DateTimeFormat("en-US", { month: "long" }).format(new Date(2024, month - 1, 1));

const emptyRuleForm = (accountId = ""): RuleFormState => ({
  label: "",
  entry_kind: "expense",
  amount: "",
  account_id: accountId,
  category: "rent",
  notes: "",
  start_date: new Date().toISOString().slice(0, 10),
  end_date: "",
  frequency: "monthly",
  status: "automatic",
});

const emptyCapForm = (): CapFormState => ({
  category: "food",
  amount: "",
  month_key: currentMonthKey(),
});

export function PlanPage({
  accounts,
  recurringRules,
  monthlyCaps,
  settings,
  snapshot,
  onWhy,
  onRefresh,
}: PlanPageProps) {
  const activeAccounts = useMemo(
    () => accounts.filter((account) => !account.archived),
    [accounts],
  );
  const [rule, setRule] = useState<RuleFormState>(emptyRuleForm(activeAccounts[0]?.id ?? ""));
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [cap, setCap] = useState<CapFormState>(emptyCapForm);
  const [editingCap, setEditingCap] = useState<EditingCapState | null>(null);
  const [notice, setNotice] = useState<NoticeState | null>(null);

  useEffect(() => {
    if (
      !editingRuleId &&
      (!rule.account_id || !activeAccounts.some((account) => account.id === rule.account_id))
    ) {
      setRule((value) => ({ ...value, account_id: activeAccounts[0]?.id ?? "" }));
    }
  }, [activeAccounts, editingRuleId, rule.account_id]);

  const accountNameById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account.name])),
    [accounts],
  );
  const ruleAccountOptions = useMemo(() => {
    const options = [...activeAccounts];
    const selectedAccount = accounts.find((account) => account.id === rule.account_id);
    if (
      editingRuleId &&
      selectedAccount &&
      selectedAccount.archived &&
      !options.some((account) => account.id === selectedAccount.id)
    ) {
      options.unshift(selectedAccount);
    }
    return options;
  }, [accounts, activeAccounts, editingRuleId, rule.account_id]);

  const currentMonth = currentMonthKey();

  const sortedRules = useMemo(
    () =>
      [...recurringRules].sort((left, right) => {
        if (left.status !== right.status) return left.status.localeCompare(right.status);
        if (left.start_date !== right.start_date) {
          return left.start_date.localeCompare(right.start_date);
        }
        return left.label.localeCompare(right.label);
      }),
    [recurringRules],
  );

  const sortedCaps = useMemo(
    () =>
      [...monthlyCaps].sort((left, right) => {
        if (left.month_key !== right.month_key) {
          return right.month_key.localeCompare(left.month_key);
        }
        return left.category.localeCompare(right.category);
      }),
    [monthlyCaps],
  );

  const currentMonthCaps = useMemo(
    () => sortedCaps.filter((item) => item.month_key === currentMonth),
    [currentMonth, sortedCaps],
  );

  const spendByCategory = useMemo(
    () => new Map(snapshot.category_spend_this_month.map((item) => [item.label, item.value])),
    [snapshot.category_spend_this_month],
  );

  const upcomingObligationTotal = useMemo(
    () =>
      snapshot.upcoming_obligations.reduce((sum, item) => {
        return sum + item.amount;
      }, 0),
    [snapshot.upcoming_obligations],
  );

  const recurringSummary = useMemo(() => {
    const active = recurringRules.filter((item) => item.status === "automatic").length;
    const manual = recurringRules.filter((item) => item.status === "manual").length;
    const paused = recurringRules.filter((item) => item.status === "paused").length;
    const monthlyFixed = recurringRules
      .filter((item) => item.status !== "paused" && item.frequency === "monthly")
      .reduce((sum, item) => sum + item.amount, 0);

    return { active, manual, paused, monthlyFixed };
  }, [recurringRules]);

  const schoolYearMonths = useMemo(() => {
    if (snapshot.monthly_series.length) {
      return snapshot.monthly_series.slice(0, settings.school_year_months);
    }

    const today = new Date();
    return Array.from({ length: settings.school_year_months }, (_, index) => {
      const year = today.getFullYear() + Math.floor((settings.school_year_start_month - 1 + index) / 12);
      const month = ((settings.school_year_start_month - 1 + index) % 12) + 1;
      return {
        month_key: `${year}-${String(month).padStart(2, "0")}`,
        spent: 0,
        cap: 0,
        runway_balance: snapshot.total_available_cash,
      };
    });
  }, [
    settings.school_year_months,
    settings.school_year_start_month,
    snapshot.monthly_series,
    snapshot.total_available_cash,
  ]);

  const schoolYearEndMonth =
    ((settings.school_year_start_month - 1 + settings.school_year_months - 1) % 12) + 1;
  const schoolYearTitle = `${monthName(settings.school_year_start_month)} to ${monthName(
    schoolYearEndMonth,
  )}`;

  const runAction = async (work: () => Promise<unknown>, successText: string) => {
    try {
      await work();
      setNotice({ kind: "success", text: successText });
      await onRefresh();
      return true;
    } catch (error) {
      setNotice({ kind: "error", text: String(error) });
      return false;
    }
  };

  const resetRuleForm = () => {
    setEditingRuleId(null);
    setRule(emptyRuleForm(activeAccounts[0]?.id ?? ""));
  };

  const resetCapForm = () => {
    setEditingCap(null);
    setCap(emptyCapForm());
  };

  const handleRuleSave = async () => {
    if (!rule.label.trim()) {
      setNotice({ kind: "error", text: "Recurring rules need a label." });
      return;
    }
    if (!rule.account_id) {
      setNotice({ kind: "error", text: "Pick an account before saving a recurring rule." });
      return;
    }
    if (!activeAccounts.some((account) => account.id === rule.account_id)) {
      setNotice({ kind: "error", text: "Recurring rules must use an active account." });
      return;
    }
    if (Number(rule.amount) <= 0) {
      setNotice({ kind: "error", text: "Recurring amount must be greater than zero." });
      return;
    }

    const payload = {
      ...rule,
      label: rule.label.trim(),
      category: rule.category.trim() || "uncategorized",
      notes: rule.notes.trim(),
      amount: Number(rule.amount),
      end_date: rule.end_date || null,
    };

    const saved = await runAction(
      () =>
        editingRuleId
          ? updateRecurringRule(editingRuleId, payload)
          : createRecurringRule(payload),
      editingRuleId ? "Recurring rule updated." : "Recurring rule saved.",
    );

    if (saved) {
      resetRuleForm();
    }
  };

  const handleCapSave = async () => {
    if (!cap.category.trim()) {
      setNotice({ kind: "error", text: "Monthly caps need a category." });
      return;
    }
    if (Number(cap.amount) <= 0) {
      setNotice({ kind: "error", text: "Monthly cap amount must be greater than zero." });
      return;
    }

    const saved = await runAction(
      () =>
        setMonthlyCap({
          category: cap.category.trim(),
          amount: Number(cap.amount),
          month_key: cap.month_key,
        }),
      editingCap ? "Monthly cap updated." : "Monthly cap saved.",
    );

    if (saved) {
      resetCapForm();
    }
  };

  const startRuleEdit = (item: RecurringRule) => {
    setEditingRuleId(item.id);
    setRule({
      label: item.label,
      entry_kind: item.entry_kind,
      amount: String(item.amount),
      account_id: item.account_id,
      category: item.category,
      notes: item.notes,
      start_date: item.start_date,
      end_date: item.end_date ?? "",
      frequency: item.frequency,
      status: item.status,
    });
    setNotice(null);
  };

  const startCapEdit = (item: MonthlyCap) => {
    setEditingCap({
      id: item.id,
      category: item.category,
      month_key: item.month_key,
    });
    setCap({
      category: item.category,
      amount: String(item.amount),
      month_key: item.month_key,
    });
    setNotice(null);
  };

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Plan</p>
          <h1 className={styles.heroTitle}>Recurring bills and monthly caps</h1>
          <p className={styles.heroText}>
            Use recurring rules for fixed bills and monthly caps for spending targets. Rent
            credit only affects rent totals.
          </p>
        </div>
      </div>

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
          eyebrow="Fixed bills"
          note={`${snapshot.upcoming_obligations.length} obligation(s) currently queued.`}
          title="Upcoming obligations"
          value={currency(upcomingObligationTotal)}
        />
        <MetricCard
          eyebrow="Caps"
          note={`Current month cap total ${currency(snapshot.this_month_cap)}.`}
          title="Total caps"
          value={currency(
            sortedCaps.reduce((sum, item) => {
              return sum + item.amount;
            }, 0),
          )}
        />
        <MetricCard
          eyebrow="School year"
          note="Remaining fixed bills and caps come from the Rust snapshot."
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
              onClick={() => onWhy("school_year_runway_remaining")}
              type="button"
            >
              Why?
            </button>
          }
          eyebrow="School year"
          title={schoolYearTitle}
        >
          <div className={styles.statGrid}>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Remaining balance</div>
              <div className={styles.statValue}>
                {currency(snapshot.school_year_runway_remaining)}
              </div>
            </div>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Projected end balance</div>
              <div className={styles.statValue}>
                {currency(snapshot.projected_end_of_year_cushion)}
              </div>
            </div>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Recurring monthly load</div>
              <div className={styles.statValue}>{currency(recurringSummary.monthlyFixed)}</div>
            </div>
            <div className={styles.statBlock}>
              <div className={styles.statLabel}>Planning months loaded</div>
              <div className={styles.statValue}>{schoolYearMonths.length}</div>
            </div>
          </div>

          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Spent</th>
                  <th>Cap</th>
                  <th>Cap room</th>
                  <th>End balance</th>
                </tr>
              </thead>
              <tbody>
                {schoolYearMonths.map((item) => {
                  const capRoom = item.cap - item.spent;
                  return (
                    <tr key={item.month_key}>
                      <td>{monthLabel(item.month_key)}</td>
                      <td>{currency(item.spent)}</td>
                      <td>{currency(item.cap)}</td>
                      <td className={capRoom >= 0 ? styles.positive : styles.negative}>
                        {currency(capRoom)}
                      </td>
                      <td>{currency(item.runway_balance)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

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
              <div className={styles.statLabel}>Net rent</div>
              <div className={styles.statValue}>{currency(snapshot.rent_net_this_month)}</div>
            </div>
          </div>

          <div className={styles.summaryList}>
            <div className={styles.summaryRow}>
              <span>Rent logic</span>
              <span className={styles.inlineValue}>Credit offsets rent only</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Automatic rules</span>
              <span className={styles.inlineValue}>{recurringSummary.active}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Manual rules</span>
              <span className={styles.inlineValue}>{recurringSummary.manual}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Paused rules</span>
              <span className={styles.inlineValue}>{recurringSummary.paused}</span>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className={styles.grid2}>
        <section className={styles.stack}>
          <h2>{editingRuleId ? "Edit recurring rule" : "Recurring rules"}</h2>
          <div className={styles.filters}>
            <input
              className={styles.input}
              onChange={(event) => setRule({ ...rule, label: event.target.value })}
              placeholder="Rule label"
              value={rule.label}
            />
            <select
              className={styles.select}
              onChange={(event) =>
                setRule({
                  ...rule,
                  entry_kind: event.target.value as Exclude<EntryKind, "transfer">,
                })
              }
              value={rule.entry_kind}
            >
              <option value="expense">expense</option>
              <option value="funding">funding</option>
              <option value="rent_credit">rent_credit</option>
              <option value="adjustment">adjustment</option>
            </select>
            <select
              className={styles.select}
              onChange={(event) => setRule({ ...rule, account_id: event.target.value })}
              value={rule.account_id}
            >
              <option value="">Select account</option>
              {ruleAccountOptions.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                  {account.archived ? " (archived)" : ""}
                </option>
              ))}
            </select>
            <button
              className={styles.primaryButton}
              disabled={!ruleAccountOptions.length}
              onClick={handleRuleSave}
              type="button"
            >
              {editingRuleId ? "Update rule" : "Save rule"}
            </button>
          </div>
          <div className={styles.filters}>
            <input
              className={styles.input}
              onChange={(event) => setRule({ ...rule, category: event.target.value })}
              placeholder="Category"
              value={rule.category}
            />
            <input
              className={styles.input}
              onChange={(event) => setRule({ ...rule, amount: event.target.value })}
              placeholder="Amount"
              type="number"
              value={rule.amount}
            />
            <select
              className={styles.select}
              onChange={(event) =>
                setRule({
                  ...rule,
                  frequency: event.target.value as RecurringFrequency,
                })
              }
              value={rule.frequency}
            >
              <option value="daily">daily</option>
              <option value="weekly">weekly</option>
              <option value="monthly">monthly</option>
            </select>
            <select
              className={styles.select}
              onChange={(event) =>
                setRule({
                  ...rule,
                  status: event.target.value as RecurringStatus,
                })
              }
              value={rule.status}
            >
              <option value="automatic">automatic</option>
              <option value="manual">manual</option>
              <option value="paused">paused</option>
            </select>
          </div>
          <div className={styles.grid2}>
            <input
              className={styles.input}
              onChange={(event) => setRule({ ...rule, start_date: event.target.value })}
              type="date"
              value={rule.start_date}
            />
            <input
              className={styles.input}
              onChange={(event) => setRule({ ...rule, end_date: event.target.value })}
              type="date"
              value={rule.end_date}
            />
          </div>
          <textarea
            className={styles.textarea}
            onChange={(event) => setRule({ ...rule, notes: event.target.value })}
            placeholder="Notes for reconciliation or context"
            value={rule.notes}
          />
          {!editingRuleId && !activeAccounts.length ? (
            <div className={styles.helperText}>
              Create or restore an active account before adding recurring rules.
            </div>
          ) : null}
          {editingRuleId &&
          rule.account_id &&
          !activeAccounts.some((account) => account.id === rule.account_id) ? (
            <div className={styles.helperText}>
              This rule is still tied to an archived account. Reassign it to an active account
              before saving.
            </div>
          ) : null}
          {editingRuleId ? (
            <div className={styles.rowActions}>
              <button
                className={styles.secondaryButton}
                onClick={resetRuleForm}
                type="button"
              >
                Cancel edit
              </button>
            </div>
          ) : null}

          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Kind</th>
                  <th>Account</th>
                  <th>Schedule</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {sortedRules.length ? (
                  sortedRules.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div>{item.label}</div>
                        <div className={styles.minor}>{item.category}</div>
                      </td>
                      <td>{item.entry_kind}</td>
                      <td>{accountNameById.get(item.account_id) ?? item.account_id}</td>
                      <td>
                        <div>{item.frequency}</div>
                        <div className={styles.minor}>
                          {item.start_date}
                          {item.end_date ? ` -> ${item.end_date}` : ""}
                        </div>
                      </td>
                      <td>{currency(item.amount)}</td>
                      <td>
                        <span
                          className={`${styles.badge} ${
                            item.status === "automatic"
                              ? styles.badgeAutomatic
                              : item.status === "manual"
                                ? styles.badgeManual
                                : styles.badgePaused
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td>
                        <div className={styles.rowActions}>
                          <button
                            className={styles.pillButton}
                            onClick={() => startRuleEdit(item)}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className={styles.pillButton}
                            onClick={() =>
                              void runAction(
                                () => applyRecurringRuleNow(item.id),
                                `Applied ${item.label}.`,
                              )
                            }
                            type="button"
                          >
                            Apply now
                          </button>
                          <button
                            className={styles.dangerButton}
                            onClick={() =>
                              void runAction(
                                () => deleteRecurringRule(item.id),
                                `Deleted ${item.label}.`,
                              )
                            }
                            type="button"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className={styles.emptyState} colSpan={7}>
                      No recurring rules yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className={styles.stack}>
          <h2>{editingCap ? "Adjust monthly cap" : "Monthly caps"}</h2>
          <div className={styles.filters}>
            <input
              className={styles.input}
              disabled={Boolean(editingCap)}
              onChange={(event) => setCap({ ...cap, category: event.target.value })}
              placeholder="Category"
              value={cap.category}
            />
            <input
              className={styles.input}
              onChange={(event) => setCap({ ...cap, amount: event.target.value })}
              placeholder="Amount"
              type="number"
              value={cap.amount}
            />
            <input
              className={styles.input}
              disabled={Boolean(editingCap)}
              onChange={(event) => setCap({ ...cap, month_key: event.target.value })}
              placeholder="YYYY-MM"
              value={cap.month_key}
            />
            <button className={styles.primaryButton} onClick={handleCapSave} type="button">
              {editingCap ? "Update cap" : "Save cap"}
            </button>
          </div>
          {editingCap ? (
            <div className={styles.stack}>
              <div className={styles.helperText}>
                Category and month stay locked while editing because the current cap command
                keys updates by that pair.
              </div>
              <div className={styles.rowActions}>
                <button
                  className={styles.secondaryButton}
                  onClick={resetCapForm}
                  type="button"
                >
                  Cancel edit
                </button>
              </div>
            </div>
          ) : null}

          <SectionCard eyebrow="Current month" title={`${monthLabel(currentMonth)} cap coverage`}>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Cap</th>
                    <th>Spent</th>
                    <th>Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {currentMonthCaps.length ? (
                    currentMonthCaps.map((item) => {
                      const spent = spendByCategory.get(item.category) ?? 0;
                      const variance = item.amount - spent;
                      return (
                        <tr key={item.id}>
                          <td>{item.category}</td>
                          <td>{currency(item.amount)}</td>
                          <td>{currency(spent)}</td>
                          <td className={variance >= 0 ? styles.positive : styles.negative}>
                            {currency(variance)}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td className={styles.emptyState} colSpan={4}>
                        No caps saved for {monthLabel(currentMonth)}.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {sortedCaps.length ? (
                  sortedCaps.map((item) => (
                    <tr key={item.id}>
                      <td>{monthLabel(item.month_key)}</td>
                      <td>{item.category}</td>
                      <td>{currency(item.amount)}</td>
                      <td>
                        <div className={styles.rowActions}>
                          <button
                            className={styles.pillButton}
                            onClick={() => startCapEdit(item)}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className={styles.dangerButton}
                            onClick={() =>
                              void runAction(
                                () => deleteMonthlyCap(item.id),
                                `Deleted ${item.category} cap for ${item.month_key}.`,
                              )
                            }
                            type="button"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className={styles.emptyState} colSpan={4}>
                      No monthly caps yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
