import { currentMonthKey, localNowIso } from "./format";
import type { Account, CreateEntryInput } from "./types";

const QUICK_ENTRY_PATTERN = /^\s*(\d+(?:\.\d+)?)\s+(.+)\s*$/;

export function parseQuickAdd(
  value: string,
  account: Account | undefined,
  category = "misc",
): CreateEntryInput | null {
  const match = QUICK_ENTRY_PATTERN.exec(value);
  if (!match || !account) {
    return null;
  }

  const amount = Number(match[1]);
  const label = match[2].trim();
  if (!amount || !label) {
    return null;
  }

  return {
    account_id: account.id,
    entry_kind: "expense",
    amount,
    occurred_at_local: localNowIso(),
    label,
    category: category.trim() || "misc",
    notes: `Quick capture for ${currentMonthKey()}`,
    exclude_from_insights: false,
  };
}
