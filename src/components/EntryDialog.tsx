import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useMemo, useState } from "react";

import { createEntry, updateEntry } from "../lib/api";
import { localNowIso } from "../lib/format";
import { categoryOptions, labelOptions } from "../lib/suggestions";
import type { Account, EntryKind, LedgerEntry, MonthlyCap, RecurringRule } from "../lib/types";
import styles from "./Dialog.module.css";

interface EntryDialogProps {
  accounts: Account[];
  entries?: LedgerEntry[];
  entry?: LedgerEntry | null;
  monthlyCaps?: MonthlyCap[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => Promise<void>;
  recurringRules?: RecurringRule[];
}

const ENTRY_KINDS: Exclude<EntryKind, "transfer">[] = [
  "expense",
  "funding",
  "rent_credit",
  "adjustment",
];

const defaultCategoryForKind = (kind: Exclude<EntryKind, "transfer">) => {
  if (kind === "funding") return "income";
  if (kind === "rent_credit") return "rent";
  if (kind === "adjustment") return "adjustment";
  return "misc";
};

export function EntryDialog({
  accounts,
  entries = [],
  entry,
  monthlyCaps = [],
  open,
  onOpenChange,
  onSaved,
  recurringRules = [],
}: EntryDialogProps) {
  const activeAccounts = useMemo(
    () => accounts.filter((account) => !account.archived),
    [accounts],
  );
  const [accountId, setAccountId] = useState(activeAccounts[0]?.id ?? "");
  const [entryKind, setEntryKind] = useState<Exclude<EntryKind, "transfer">>("expense");
  const [amount, setAmount] = useState("0");
  const [occurredAt, setOccurredAt] = useState(localNowIso());
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState("misc");
  const [notes, setNotes] = useState("");
  const [exclude, setExclude] = useState(false);
  const labelChoices = useMemo(
    () => labelOptions(entries, recurringRules),
    [entries, recurringRules],
  );
  const categoryChoices = useMemo(
    () => categoryOptions(entries, recurringRules, monthlyCaps, entryKind),
    [entries, entryKind, monthlyCaps, recurringRules],
  );
  const accountOptions = useMemo(() => {
    const options = [...activeAccounts];
    const selectedAccount = accounts.find((account) => account.id === accountId);
    if (
      entry &&
      selectedAccount &&
      selectedAccount.archived &&
      !options.some((account) => account.id === selectedAccount.id)
    ) {
      options.unshift(selectedAccount);
    }
    return options;
  }, [accountId, accounts, activeAccounts, entry]);

  useEffect(() => {
    if (entry) {
      setAccountId(entry.account_id);
      setEntryKind(entry.entry_kind === "transfer" ? "expense" : entry.entry_kind);
      setAmount(String(entry.amount));
      setOccurredAt(entry.occurred_at_local);
      setLabel(entry.label);
      setCategory(entry.category || "misc");
      setNotes(entry.notes);
      setExclude(entry.exclude_from_insights);
      return;
    }

    setAccountId(activeAccounts[0]?.id ?? "");
    setEntryKind("expense");
    setAmount("0");
    setOccurredAt(localNowIso());
    setLabel("");
    setCategory(defaultCategoryForKind("expense"));
    setNotes("");
    setExclude(false);
  }, [activeAccounts, entry, open]);

  const handleKindChange = (kind: Exclude<EntryKind, "transfer">) => {
    setEntryKind(kind);
    if (!entry && ["misc", "income", "rent", "adjustment", ""].includes(category)) {
      setCategory(defaultCategoryForKind(kind));
    }
  };

  const handleSubmit = async () => {
    if (!entry && !accountId) {
      return;
    }

    if (entry) {
      await updateEntry(entry.id, {
        account_id: accountId,
        entry_kind: entryKind,
        amount: Number(amount),
        occurred_at_local: occurredAt,
        label,
        category,
        notes,
        exclude_from_insights: exclude,
      });
    } else {
      await createEntry({
        account_id: accountId,
        entry_kind: entryKind,
        amount: Number(amount),
        occurred_at_local: occurredAt,
        label,
        category,
        notes,
        exclude_from_insights: exclude,
      });
    }

    await onSaved();
    onOpenChange(false);
  };

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.content}>
          <Dialog.Title className={styles.title}>
            {entry ? "Edit entry" : "Guided entry"}
          </Dialog.Title>
          <Dialog.Description asChild>
            <p className={styles.note}>
              Use guided entry for funding, rent credits, manual exclusions, or adjustments.
            </p>
          </Dialog.Description>
          {!entry && !activeAccounts.length ? (
            <p className={styles.note}>
              Create or restore an active account before adding a new entry.
            </p>
          ) : null}
          {entry &&
          accountId &&
          !activeAccounts.some((account) => account.id === accountId) ? (
            <p className={styles.note}>
              This entry still belongs to an archived account. Reassign it to an active
              account before saving if you need to move it.
            </p>
          ) : null}
          <div className={styles.grid}>
            <label className={styles.field}>
              <span>Account</span>
              <select
                className={styles.select}
                onChange={(event) => setAccountId(event.target.value)}
                value={accountId}
              >
                {accountOptions.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                    {account.archived ? " (archived)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.field}>
              <span>Entry kind</span>
              <select
                className={styles.select}
                onChange={(event) =>
                  handleKindChange(event.target.value as Exclude<EntryKind, "transfer">)
                }
                value={entryKind}
              >
                {ENTRY_KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {kind}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.field}>
              <span>Amount</span>
              <input
                className={styles.input}
                onChange={(event) => setAmount(event.target.value)}
                type="number"
                value={amount}
              />
            </label>
            <label className={styles.field}>
              <span>Occurred at</span>
              <input
                className={styles.input}
                onChange={(event) => setOccurredAt(event.target.value)}
                type="datetime-local"
                value={occurredAt.slice(0, 16)}
              />
            </label>
            <label className={styles.field}>
              <span>Label</span>
              <input
                className={styles.input}
                list="entry-label-options"
                onChange={(event) => setLabel(event.target.value)}
                placeholder="Pick or type a label"
                value={label}
              />
              <datalist id="entry-label-options">
                {labelChoices.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
            </label>
            <label className={styles.field}>
              <span>Category</span>
              <input
                className={styles.input}
                list="entry-category-options"
                onChange={(event) => setCategory(event.target.value)}
                placeholder="Pick or type a category"
                value={category}
              />
              <datalist id="entry-category-options">
                {categoryChoices.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
            </label>
            <label className={`${styles.field} ${styles.fieldWide}`}>
              <span>Notes</span>
              <textarea
                className={styles.textarea}
                onChange={(event) => setNotes(event.target.value)}
                value={notes}
              />
            </label>
            <label className={`${styles.field} ${styles.fieldWide}`}>
              <span>
                <input
                  checked={exclude}
                  onChange={(event) => setExclude(event.target.checked)}
                  type="checkbox"
                />{" "}
                Exclude from totals and charts
              </span>
            </label>
          </div>

          <div className={styles.actions}>
            <Dialog.Close asChild>
              <button className={styles.ghost} type="button">
                Cancel
              </button>
            </Dialog.Close>
            <button
              className={styles.button}
              disabled={!accountId}
              onClick={handleSubmit}
              type="button"
            >
              Save
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
