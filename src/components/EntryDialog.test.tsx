import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import { EntryDialog } from "./EntryDialog";

vi.mock("../lib/api", () => ({
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
}));

const archivedAccount = {
  id: "archived-1",
  name: "Archived savings",
  type: "savings" as const,
  opening_balance: 400,
  archived: true,
  created_at: "2026-01-01T10:00:00",
  current_balance: 550,
};

const activeAccount = {
  id: "active-1",
  name: "Checking",
  type: "checking" as const,
  opening_balance: 1000,
  archived: false,
  created_at: "2026-01-02T10:00:00",
  current_balance: 1280,
};

describe("EntryDialog", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.createEntry).mockResolvedValue(undefined);
    vi.mocked(api.updateEntry).mockResolvedValue(undefined);
  });

  it("shows active accounts only for new entries", () => {
    render(
      <EntryDialog
        accounts={[archivedAccount, activeAccount]}
        entry={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn().mockResolvedValue(undefined)}
        open
      />,
    );

    expect(screen.queryByRole("option", { name: "Archived savings" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Checking" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
  });

  it("disables saving when there are no active accounts", () => {
    render(
      <EntryDialog
        accounts={[archivedAccount]}
        entry={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn().mockResolvedValue(undefined)}
        open
      />,
    );

    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(
      screen.getByText("Create or restore an active account before adding a new entry."),
    ).toBeInTheDocument();
  });
});
