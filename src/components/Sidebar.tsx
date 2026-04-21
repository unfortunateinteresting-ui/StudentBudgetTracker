import clsx from "clsx";

import type { ThemeMode } from "../lib/theme";
import type { Workspace } from "../lib/types";
import styles from "./Sidebar.module.css";

const WORKSPACES: Array<{ id: Workspace; label: string }> = [
  { id: "home", label: "Home" },
  { id: "activity", label: "Activity" },
  { id: "plan", label: "Plan" },
  { id: "accounts", label: "Accounts" },
  { id: "insights", label: "Insights" },
  { id: "settings", label: "Settings" },
];

interface SidebarProps {
  workspace: Workspace;
  theme: ThemeMode;
  onSelect: (workspace: Workspace) => void;
  onToggleTheme: () => void;
}

export function Sidebar({ workspace, theme, onSelect, onToggleTheme }: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div className={styles.brandTitle}>Budget Tracker</div>
        <div className={styles.brandSubtitle}>Local desktop budgeting</div>
      </div>

      <nav className={styles.nav}>
        {WORKSPACES.map((item) => (
          <button
            key={item.id}
            className={clsx(styles.button, workspace === item.id && styles.active)}
            onClick={() => onSelect(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className={styles.footer}>
        <button className={styles.themeButton} onClick={onToggleTheme} type="button">
          {theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        </button>
        <br />
        Saved on this computer
        <br />
        Desktop app
      </div>
    </aside>
  );
}
