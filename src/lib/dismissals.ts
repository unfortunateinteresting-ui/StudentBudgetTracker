import type { MissedRecurringOccurrence } from "./types";

const DISMISSED_MISSED_RECURRING_KEY = "student-budget-tracker.dismissed-missed-recurring";
const DISMISSED_SYNC_ALERT_KEY = "student-budget-tracker.dismissed-sync-alert";

const readSet = (key: string) => {
  if (typeof window === "undefined") return new Set<string>();
  try {
    const value = window.localStorage.getItem(key);
    const parsed = value ? JSON.parse(value) : [];
    return new Set<string>(Array.isArray(parsed) ? parsed.filter(Boolean) : []);
  } catch {
    return new Set<string>();
  }
};

const writeSet = (key: string, values: Set<string>) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(Array.from(values).slice(-200)));
};

export const missedRecurringKey = (occurrence: MissedRecurringOccurrence) =>
  `${occurrence.recurring_rule_id}:${occurrence.dates.join(",")}`;

export function filterDismissedMissedRecurring(items: MissedRecurringOccurrence[]) {
  const dismissed = readSet(DISMISSED_MISSED_RECURRING_KEY);
  return items.filter((item) => !dismissed.has(missedRecurringKey(item)));
}

export function dismissMissedRecurring(items: MissedRecurringOccurrence[]) {
  const dismissed = readSet(DISMISSED_MISSED_RECURRING_KEY);
  for (const item of items) {
    dismissed.add(missedRecurringKey(item));
  }
  writeSet(DISMISSED_MISSED_RECURRING_KEY, dismissed);
}

export function isSyncAlertDismissed(message: string) {
  return readSet(DISMISSED_SYNC_ALERT_KEY).has(message);
}

export function dismissSyncAlert(message: string) {
  if (!message) return;
  const dismissed = readSet(DISMISSED_SYNC_ALERT_KEY);
  dismissed.add(message);
  writeSet(DISMISSED_SYNC_ALERT_KEY, dismissed);
}
