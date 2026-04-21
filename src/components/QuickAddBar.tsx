import { useEffect, useMemo, useState } from "react";

import { createEntry } from "../lib/api";
import { parseQuickAdd } from "../lib/quickAdd";
import type { Account } from "../lib/types";
import styles from "./QuickAddBar.module.css";

interface QuickAddBarProps {
  accounts: Account[];
  onSaved: () => Promise<void>;
}

export function QuickAddBar({ accounts, onSaved }: QuickAddBarProps) {
  const activeAccounts = useMemo(
    () => accounts.filter((account) => !account.archived),
    [accounts],
  );
  const [value, setValue] = useState("");
  const [accountId, setAccountId] = useState("");
  const [status, setStatus] = useState("");
  const activeAccount =
    activeAccounts.find((item) => item.id === accountId) ?? activeAccounts[0];

  useEffect(() => {
    if (!activeAccount?.id) {
      if (accountId) {
        setAccountId("");
      }
      return;
    }

    if (!accountId || !activeAccounts.some((item) => item.id === accountId)) {
      setAccountId(activeAccount.id);
    }
  }, [accountId, activeAccount?.id, activeAccounts]);

  const handleSave = async () => {
    if (!activeAccount) {
      setStatus("Create an active account before using quick add.");
      return;
    }

    const input = parseQuickAdd(value, activeAccount);
    if (!input) {
      setStatus("Use the quick format: 42 groceries");
      return;
    }

    try {
      await createEntry(input);
      setValue("");
      setStatus(`Saved to ${activeAccount.name}.`);
      await onSaved();
    } catch (error) {
      setStatus(String(error));
    }
  };

  return (
    <div>
      <div className={styles.wrap}>
        <input
          aria-label="Quick add expense"
          className={styles.input}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Quick add: 42 groceries"
          value={value}
        />
        <select
          aria-label="Quick add account"
          className={styles.select}
          onChange={(event) => setAccountId(event.target.value)}
          value={accountId}
        >
          {activeAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        <button
          className={styles.button}
          disabled={!activeAccounts.length}
          onClick={handleSave}
          type="button"
        >
          Add expense
        </button>
      </div>
      <div className={styles.help}>
        {status ||
          (!activeAccounts.length
            ? "Create at least one active account to enable quick add."
            : null) ||
          "Quick add is expense-only. Use guided entry for funding, rent credits, transfers, adjustments, or exclusions."}
      </div>
    </div>
  );
}
