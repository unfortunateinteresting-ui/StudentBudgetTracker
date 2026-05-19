import type { LedgerEntry } from "./types";

export const isRentLike = (value: string) => {
  const text = value.trim().toLowerCase();
  return text.includes("rent") || text.includes("loyer");
};

const entryText = (entry: LedgerEntry) => `${entry.label} ${entry.category} ${entry.notes}`;

export const isRentExpense = (entry: LedgerEntry) =>
  entry.entry_kind === "expense" && isRentLike(entryText(entry));

export const categoryKey = (category: string) => category.trim().toLowerCase();

export function categorySpendValue(totals: Map<string, number>, category: string) {
  const target = categoryKey(category);
  let total = 0;
  totals.forEach((value, key) => {
    if (categoryKey(key) === target) {
      total += value;
    }
  });
  return total;
}

export function netSpendingTotal(entries: LedgerEntry[]) {
  let nonRentExpense = 0;
  let rentExpense = 0;
  let rentCredit = 0;

  entries.forEach((entry) => {
    if (entry.exclude_from_insights) return;
    if (isRentExpense(entry)) {
      rentExpense += Math.abs(entry.amount);
    } else if (entry.entry_kind === "expense") {
      nonRentExpense += Math.abs(entry.amount);
    } else if (entry.entry_kind === "rent_credit") {
      rentCredit += Math.abs(entry.amount);
    }
  });

  return nonRentExpense + Math.max(rentExpense - rentCredit, 0);
}

export function netSpendingByCategory(entries: LedgerEntry[]) {
  const totals = new Map<string, number>();
  let rentExpense = 0;
  let rentCredit = 0;

  entries.forEach((entry) => {
    if (entry.exclude_from_insights) return;
    if (isRentExpense(entry)) {
      rentExpense += Math.abs(entry.amount);
    } else if (entry.entry_kind === "expense") {
      totals.set(entry.category, (totals.get(entry.category) ?? 0) + Math.abs(entry.amount));
    } else if (entry.entry_kind === "rent_credit") {
      rentCredit += Math.abs(entry.amount);
    }
  });

  if (rentExpense > 0 || rentCredit > 0) {
    totals.set("rent", Math.max(rentExpense - rentCredit, 0));
  }

  return totals;
}
