import * as Dialog from "@radix-ui/react-dialog";

import type { BreakdownResult } from "../lib/types";
import styles from "./Dialog.module.css";

interface WhyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  breakdown?: BreakdownResult | null;
}

export function WhyDialog({ open, onOpenChange, breakdown }: WhyDialogProps) {
  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.content}>
          <Dialog.Title className={styles.title}>
            {breakdown?.title || "Calculation details"}
          </Dialog.Title>
          <p className={styles.note}>
            This surface comes directly from the backend breakdown lines.
          </p>
          <div className={styles.grid}>
            <div className={styles.fieldWide}>
              {(breakdown?.lines || ["No breakdown available."]).map((line) => (
                <p key={line} className={styles.note}>
                  {line}
                </p>
              ))}
            </div>
          </div>
          <div className={styles.actions}>
            <Dialog.Close asChild>
              <button className={styles.button} type="button">
                Close
              </button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
