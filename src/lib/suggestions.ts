import type { EntryKind, LedgerEntry, MonthlyCap, RecurringRule } from "./types";

export const SPENDING_CATEGORIES = [
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

export const FUNDING_CATEGORIES = ["income", "other income", "financial aid", "guarantor"];

export const STARTER_CATEGORIES = [...SPENDING_CATEGORIES, ...FUNDING_CATEGORIES, "adjustment"];

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
  entryKind?: Exclude<EntryKind, "transfer">,
) {
  const starterCategories =
    entryKind === "funding"
      ? FUNDING_CATEGORIES
      : entryKind === "rent_credit"
        ? ["rent"]
        : entryKind === "adjustment"
          ? ["adjustment"]
          : SPENDING_CATEGORIES;
  const matchingEntries = entryKind
    ? entries.filter((entry) => entry.entry_kind === entryKind)
    : entries;
  const matchingRules = entryKind
    ? recurringRules.filter((rule) => rule.entry_kind === entryKind)
    : recurringRules;
  const capCategories = !entryKind || entryKind === "expense" ? monthlyCaps : [];

  return uniqueOptions([
    ...starterCategories,
    ...matchingEntries.map((entry) => entry.category),
    ...matchingRules.map((rule) => rule.category),
    ...capCategories.map((cap) => cap.category),
  ]);
}

export function labelOptions(entries: LedgerEntry[] = [], recurringRules: RecurringRule[] = []) {
  return uniqueOptions([
    ...entries.map((entry) => entry.label),
    ...recurringRules.map((rule) => rule.label),
  ]);
}
