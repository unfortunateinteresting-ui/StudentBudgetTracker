export async function chooseJsonImportPath(currentPath?: string): Promise<string | null> {
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      title: "Import budget JSON",
      defaultPath: currentPath?.trim() || undefined,
      multiple: false,
      directory: false,
      filters: [{ name: "JSON", extensions: ["json"] }],
    });

    if (Array.isArray(selected)) {
      return selected[0] ?? null;
    }

    return selected ?? null;
  } catch {
    return null;
  }
}

export async function chooseJsonExportPath(currentPath?: string): Promise<string | null> {
  try {
    const { save } = await import("@tauri-apps/plugin-dialog");
    const selected = await save({
      title: "Export budget JSON",
      defaultPath: currentPath?.trim() || "budget-export.json",
      filters: [{ name: "JSON", extensions: ["json"] }],
    });

    return selected ?? null;
  } catch {
    return null;
  }
}
