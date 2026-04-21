import type { ReactNode } from "react";

import styles from "./Card.module.css";

interface SectionCardProps {
  eyebrow?: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ eyebrow, title, action, children }: SectionCardProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardTitle}>
        <div>
          {eyebrow ? <div className={styles.eyebrow}>{eyebrow}</div> : null}
          <div className={styles.title}>{title}</div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
