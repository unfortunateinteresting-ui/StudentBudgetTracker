import { useEffect, useMemo, useState } from "react";

import {
  archiveAccount,
  createAccount,
  createTransfer,
  reconcileAccount,
  updateAccount,
} from "../lib/api";
import { currency, localNowIso } from "../lib/format";
import type { Account, AccountType } from "../lib/types";
import { MetricCard } from "../components/MetricCard";
import styles from "./Page.module.css";

interface AccountsPageProps {
  accounts: Account[];
  onRefresh: () => Promise<void>;
}

interface AccountFormState {
  name: string;
  type: AccountType;
  opening_balance: string;
}

type NoticeState = {
  kind: "success" | "error";
  text: string;
};

const emptyAccountForm = (): AccountFormState => ({
  name: "",
  type: "checking",
  opening_balance: "0",
});

export function AccountsPage({ accounts, onRefresh }: AccountsPageProps) {
  const [account, setAccount] = useState<AccountFormState>(emptyAccountForm);
  const [editingAccountId, setEditingAccountId] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const [transfer, setTransfer] = useState({
    from_account_id: "",
    to_account_id: "",
    amount: "",
    label: "Transfer",
    notes: "",
  });
  const [reconcile, setReconcile] = useState({
    account_id: "",
    actual_balance: "",
    notes: "Manual reconcile",
  });

  const activeAccounts = useMemo(
    () => accounts.filter((accountItem) => !accountItem.archived),
    [accounts],
  );
  const archivedAccounts = useMemo(
    () => accounts.filter((accountItem) => accountItem.archived),
    [accounts],
  );
  const totalBalance = useMemo(
    () => activeAccounts.reduce((sum, accountItem) => sum + accountItem.current_balance, 0),
    [activeAccounts],
  );

  useEffect(() => {
    if (!transfer.from_account_id && activeAccounts[0]?.id) {
      setTransfer((value) => ({
        ...value,
        from_account_id: activeAccounts[0].id,
        to_account_id: activeAccounts[1]?.id ?? activeAccounts[0].id,
      }));
    }

    if (
      transfer.from_account_id &&
      !activeAccounts.some((accountItem) => accountItem.id === transfer.from_account_id)
    ) {
      setTransfer((value) => ({
        ...value,
        from_account_id: activeAccounts[0]?.id ?? "",
        to_account_id: activeAccounts[1]?.id ?? activeAccounts[0]?.id ?? "",
      }));
    }

    if (
      transfer.to_account_id &&
      !activeAccounts.some((accountItem) => accountItem.id === transfer.to_account_id)
    ) {
      setTransfer((value) => ({
        ...value,
        to_account_id: activeAccounts[1]?.id ?? activeAccounts[0]?.id ?? "",
      }));
    }

    if (!reconcile.account_id && activeAccounts[0]?.id) {
      setReconcile((value) => ({ ...value, account_id: activeAccounts[0].id }));
    }

    if (
      reconcile.account_id &&
      !activeAccounts.some((accountItem) => accountItem.id === reconcile.account_id)
    ) {
      setReconcile((value) => ({ ...value, account_id: activeAccounts[0]?.id ?? "" }));
    }
  }, [activeAccounts, reconcile.account_id, transfer.from_account_id, transfer.to_account_id]);

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

  const resetAccountForm = () => {
    setAccount(emptyAccountForm());
    setEditingAccountId(null);
  };

  const handleAccountSave = async () => {
    if (!account.name.trim()) {
      setNotice({ kind: "error", text: "Account name is required." });
      return;
    }

    if (editingAccountId) {
      const updated = await runAction(
        () =>
          updateAccount(editingAccountId, {
            name: account.name.trim(),
            type: account.type,
          }),
        `Updated ${account.name.trim()}.`,
      );
      if (updated) resetAccountForm();
      return;
    }

    const created = await runAction(
      () =>
        createAccount({
          name: account.name.trim(),
          type: account.type,
          opening_balance: Number(account.opening_balance || 0),
        }),
      `Created ${account.name.trim()}.`,
    );

    if (created) {
      resetAccountForm();
    }
  };

  const handleTransfer = async () => {
    if (!transfer.from_account_id || !transfer.to_account_id) {
      setNotice({ kind: "error", text: "Select both accounts for the transfer." });
      return;
    }
    if (transfer.from_account_id === transfer.to_account_id) {
      setNotice({ kind: "error", text: "Transfer accounts must be different." });
      return;
    }
    if (Number(transfer.amount) <= 0) {
      setNotice({ kind: "error", text: "Transfer amount must be greater than zero." });
      return;
    }

    const transferred = await runAction(
      () =>
        createTransfer({
          ...transfer,
          label: transfer.label.trim() || "Transfer",
          notes: transfer.notes.trim(),
          amount: Number(transfer.amount),
          occurred_at_local: localNowIso(),
        }),
      "Transfer recorded.",
    );

    if (transferred) {
      setTransfer((value) => ({
        ...value,
        amount: "",
        notes: "",
      }));
    }
  };

  const handleReconcile = async () => {
    if (!reconcile.account_id) {
      setNotice({ kind: "error", text: "Select an account to reconcile." });
      return;
    }
    if (reconcile.actual_balance.trim() === "") {
      setNotice({ kind: "error", text: "Enter the actual account balance." });
      return;
    }

    const reconciled = await runAction(
      () =>
        reconcileAccount({
          account_id: reconcile.account_id,
          actual_balance: Number(reconcile.actual_balance),
          occurred_at_local: localNowIso(),
          notes: reconcile.notes.trim() || "Manual reconcile",
        }),
      "Account reconciled.",
    );

    if (reconciled) {
      setReconcile((value) => ({
        ...value,
        actual_balance: "",
      }));
    }
  };

  const startAccountEdit = (accountItem: Account) => {
    setEditingAccountId(accountItem.id);
    setAccount({
      name: accountItem.name,
      type: accountItem.type,
      opening_balance: String(accountItem.opening_balance),
    });
    setNotice(null);
  };

  const toggleArchive = async (accountItem: Account) => {
    if (accountItem.archived) {
      await runAction(
        () =>
          updateAccount(accountItem.id, {
            archived: false,
          }),
        `Restored ${accountItem.name}.`,
      );
      return;
    }

    await runAction(
      () => archiveAccount(accountItem.id),
      `Archived ${accountItem.name}.`,
    );
  };

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div>
          <p className={styles.kicker}>Accounts</p>
          <h1 className={styles.heroTitle}>Manage accounts</h1>
          <p className={styles.heroText}>
            Create accounts, transfer money between them, and reconcile balances.
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
          eyebrow="Active"
          note="Accounts that can still receive transfers and reconciles."
          title="Live accounts"
          value={String(activeAccounts.length)}
        />
        <MetricCard
          eyebrow="Cash"
          note="Sum of current balances across active accounts."
          title="Active balance"
          value={currency(totalBalance)}
        />
        <MetricCard
          eyebrow="Archived"
          note="Hidden from day-to-day movement but preserved in history."
          title="Archived accounts"
          value={String(archivedAccounts.length)}
        />
      </div>

      <div className={styles.grid2}>
        <section className={styles.stack}>
          <h2>{editingAccountId ? "Edit account" : "Create account"}</h2>
          <div className={styles.filters}>
            <input
              className={styles.input}
              onChange={(event) => setAccount({ ...account, name: event.target.value })}
              placeholder="Account name"
              value={account.name}
            />
            <select
              className={styles.select}
              onChange={(event) =>
                setAccount({
                  ...account,
                  type: event.target.value as AccountType,
                })
              }
              value={account.type}
            >
              <option value="checking">checking</option>
              <option value="savings">savings</option>
              <option value="cash">cash</option>
              <option value="other">other</option>
            </select>
            <input
              className={styles.input}
              disabled={Boolean(editingAccountId)}
              onChange={(event) =>
                setAccount({ ...account, opening_balance: event.target.value })
              }
              placeholder="Opening balance"
              type="number"
              value={account.opening_balance}
            />
            <button
              className={styles.primaryButton}
              onClick={handleAccountSave}
              type="button"
            >
              {editingAccountId ? "Update" : "Create"}
            </button>
          </div>
          {editingAccountId ? (
            <div className={styles.rowActions}>
              <button
                className={styles.secondaryButton}
                onClick={resetAccountForm}
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
                  <th>Account</th>
                  <th>Type</th>
                  <th>Opening</th>
                  <th>Current</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {accounts.length ? (
                  accounts.map((accountItem) => (
                    <tr key={accountItem.id}>
                      <td>{accountItem.name}</td>
                      <td>{accountItem.type}</td>
                      <td>{currency(accountItem.opening_balance)}</td>
                      <td>{currency(accountItem.current_balance)}</td>
                      <td>
                        <span
                          className={`${styles.badge} ${
                            accountItem.archived ? styles.badgePaused : styles.badgeAutomatic
                          }`}
                        >
                          {accountItem.archived ? "archived" : "active"}
                        </span>
                      </td>
                      <td>
                        <div className={styles.rowActions}>
                          <button
                            className={styles.pillButton}
                            onClick={() => startAccountEdit(accountItem)}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            className={styles.secondaryButton}
                            onClick={() => void toggleArchive(accountItem)}
                            type="button"
                          >
                            {accountItem.archived ? "Restore" : "Archive"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className={styles.emptyState} colSpan={6}>
                      No accounts yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className={styles.stack}>
          <h2>Create transfer</h2>
          <div className={styles.filters}>
            <select
              className={styles.select}
              onChange={(event) =>
                setTransfer({ ...transfer, from_account_id: event.target.value })
              }
              value={transfer.from_account_id}
            >
              <option value="">From account</option>
              {activeAccounts.map((accountItem) => (
                <option key={accountItem.id} value={accountItem.id}>
                  {accountItem.name}
                </option>
              ))}
            </select>
            <select
              className={styles.select}
              onChange={(event) =>
                setTransfer({ ...transfer, to_account_id: event.target.value })
              }
              value={transfer.to_account_id}
            >
              <option value="">To account</option>
              {activeAccounts.map((accountItem) => (
                <option key={accountItem.id} value={accountItem.id}>
                  {accountItem.name}
                </option>
              ))}
            </select>
            <input
              className={styles.input}
              onChange={(event) => setTransfer({ ...transfer, amount: event.target.value })}
              placeholder="Amount"
              type="number"
              value={transfer.amount}
            />
            <button
              className={styles.primaryButton}
              disabled={activeAccounts.length < 2}
              onClick={handleTransfer}
              type="button"
            >
              Transfer
            </button>
          </div>
          <div className={styles.grid2}>
            <input
              className={styles.input}
              onChange={(event) => setTransfer({ ...transfer, label: event.target.value })}
              placeholder="Transfer label"
              value={transfer.label}
            />
            <input
              className={styles.input}
              onChange={(event) => setTransfer({ ...transfer, notes: event.target.value })}
              placeholder="Notes"
              value={transfer.notes}
            />
          </div>

          <h2>Reconcile account</h2>
          <div className={styles.filters}>
            <select
              className={styles.select}
              onChange={(event) =>
                setReconcile({ ...reconcile, account_id: event.target.value })
              }
              value={reconcile.account_id}
            >
              <option value="">Select account</option>
              {activeAccounts.map((accountItem) => (
                <option key={accountItem.id} value={accountItem.id}>
                  {accountItem.name}
                </option>
              ))}
            </select>
            <input
              className={styles.input}
              onChange={(event) =>
                setReconcile({ ...reconcile, actual_balance: event.target.value })
              }
              placeholder="Actual balance"
              type="number"
              value={reconcile.actual_balance}
            />
            <input
              className={styles.input}
              onChange={(event) => setReconcile({ ...reconcile, notes: event.target.value })}
              placeholder="Notes"
              value={reconcile.notes}
            />
            <button
              className={styles.primaryButton}
              disabled={!activeAccounts.length}
              onClick={handleReconcile}
              type="button"
            >
              Reconcile
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
