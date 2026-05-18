import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("shows label and category suggestions from existing data", () => {
    render(
      <EntryDialog
        accounts={[activeAccount]}
        entries={[
          {
            id: "entry-1",
            account_id: "active-1",
            entry_kind: "expense",
            amount: 15,
            occurred_at_local: "2026-04-22T10:00:00",
            label: "Groceries",
            category: "food",
            notes: "",
            recurring_rule_id: null,
            transfer_group_id: null,
            exclude_from_insights: false,
          },
        ]}
        entry={null}
        monthlyCaps={[
          {
            id: "cap-1",
            category: "transport",
            amount: 120,
            month_key: "2026-04",
          },
        ]}
        onOpenChange={vi.fn()}
        onSaved={vi.fn().mockResolvedValue(undefined)}
        open
        recurringRules={[]}
      />,
    );

    expect(screen.getByPlaceholderText("Pick or type a label")).toHaveAttribute(
      "list",
      "entry-label-options",
    );
    expect(screen.getByPlaceholderText("Pick or type a category")).toHaveAttribute(
      "list",
      "entry-category-options",
    );
    expect(document.querySelector('datalist#entry-label-options option[value="Groceries"]')).not.toBeNull();
    expect(document.querySelector('datalist#entry-category-options option[value="transport"]')).not.toBeNull();
  });

  it("defaults funding entries to income categories", async () => {
    const user = userEvent.setup();

    render(
      <EntryDialog
        accounts={[activeAccount]}
        entry={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn().mockResolvedValue(undefined)}
        open
      />,
    );

    await user.selectOptions(screen.getByLabelText("Entry kind"), "funding");

    expect(screen.getByPlaceholderText("Pick or type a category")).toHaveValue("income");
    expect(
      document.querySelector('datalist#entry-category-options option[value="other funding"]'),
    ).not.toBeNull();
  });
});
