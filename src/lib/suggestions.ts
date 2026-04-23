import type { LedgerEntry, MonthlyCap, RecurringRule } from "./types";

export const STARTER_CATEGORIES = [
  "rent",
  "food",
  "groceries",
  "transport",
  "school",
  "medical",
  "household",
  "subscriptions",
  "utilities",
  "misc",
];

const cleanOption = (value: string) => value.trim();

export function uniqueOptions(values: string[]) {
  return Array.from(
    new Set(values.map(cleanOption).filter((value) => value.length > 0)),
  ).sort((left, right) => left.localeCompare(right));
}

export function categoryOptions(
  entries: LedgerEntry[] = [],
  recurringRules: RecurringRule[] = [],
  monthlyCaps: MonthlyCap[] = [],
) {
  return uniqueOptions([
    ...STARTER_CATEGORIES,
    ...entries.map((entry) => entry.category),
    ...recurringRules.map((rule) => rule.category),
    ...monthlyCaps.map((cap) => cap.category),
  ]);
}

export function labelOptions(entries: LedgerEntry[] = [], recurringRules: RecurringRule[] = []) {
  return uniqueOptions([
    ...entries.map((entry) => entry.label),
    ...recurringRules.map((rule) => rule.label),
  ]);
}
