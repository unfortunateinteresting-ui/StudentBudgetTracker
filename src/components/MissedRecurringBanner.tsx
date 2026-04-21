import type { MissedRecurringOccurrence } from "../lib/types";
import styles from "./MissedRecurringBanner.module.css";

interface MissedRecurringBannerProps {
  busy?: boolean;
  missedRecurring: MissedRecurringOccurrence[];
  onApply: (recurringRuleIds?: string[]) => void | Promise<void>;
  onDismiss: () => void;
}

const formatDates = (dates: string[]) => {
  if (!dates.length) return "No missed dates";
  if (dates.length <= 3) return dates.join(", ");
  return `${dates.slice(0, 2).join(", ")}, +${dates.length - 2} more`;
};

export function MissedRecurringBanner({
  busy = false,
  missedRecurring,
  onApply,
  onDismiss,
}: MissedRecurringBannerProps) {
  if (!missedRecurring.length) {
    return null;
  }

  const totalOccurrences = missedRecurring.reduce((sum, item) => sum + item.dates.length, 0);

  return (
    <section className={styles.banner}>
      <div className={styles.header}>
        <div>
          <div className={styles.title}>Missed recurring activity detected</div>
          <div className={styles.subtitle}>
            {missedRecurring.length} rule(s), {totalOccurrences} unapplied occurrence(s) before
            today.
          </div>
        </div>
        <div className={styles.actions}>
          <button className={styles.ghost} onClick={onDismiss} type="button">
            Dismiss
          </button>
          <button
            className={styles.button}
            disabled={busy}
            onClick={() => onApply()}
            type="button"
          >
            Apply all
          </button>
        </div>
      </div>

      <div className={styles.list}>
        {missedRecurring.map((item) => (
          <div className={styles.item} key={item.recurring_rule_id}>
            <div className={styles.meta}>
              <div className={styles.label}>{item.label}</div>
              <div className={styles.detail}>
                {item.frequency} rule • {item.dates.length} missed date
                {item.dates.length === 1 ? "" : "s"}
              </div>
              <div className={styles.detail}>{formatDates(item.dates)}</div>
            </div>
            <button
              className={styles.ghost}
              disabled={busy}
              onClick={() => onApply([item.recurring_rule_id])}
              type="button"
            >
              Apply rule
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
