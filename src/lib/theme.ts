export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "student-budget-tracker-theme";

export const readThemeMode = (): ThemeMode => {
  if (typeof window === "undefined") {
    return "light";
  }
  return window.localStorage.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
};

export const applyThemeMode = (theme: ThemeMode) => {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = theme;
  }
  if (typeof window !== "undefined") {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }
};
