import styles from "./Card.module.css";

interface MetricCardProps {
  eyebrow: string;
  title: string;
  value: string;
  note: string;
  onWhy?: () => void;
  valueTone?: "default" | "cap" | "planned" | "predicted";
}

export function MetricCard({
  eyebrow,
  title,
  value,
  note,
  onWhy,
  valueTone = "default",
}: MetricCardProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardTitle}>
        <div>
          <div className={styles.eyebrow}>{eyebrow}</div>
          <div className={styles.title}>{title}</div>
        </div>
        {onWhy ? (
          <button className={styles.subtleButton} onClick={onWhy} type="button">
            Why?
          </button>
        ) : null}
      </div>
      <div className={`${styles.metricValue} ${styles[`metricValue_${valueTone}`]}`}>
        {value}
      </div>
      <div className={styles.metricNote}>{note}</div>
    </section>
  );
}
