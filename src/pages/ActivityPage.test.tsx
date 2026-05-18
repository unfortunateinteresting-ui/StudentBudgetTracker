import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import { ActivityPage } from "./ActivityPage";

vi.mock("../lib/api", () => ({
  deleteEntry: vi.fn(),
}));

const accounts = [
  {
    id: "account-1",
    name: "Checking",
    type: "checking" as const,
    opening_balance: 1000,
    archived: false,
    created_at: "2026-01-01T10:00:00",
    current_balance: 1325,
  },
  {
    id: "account-2",
    name: "Cash",
    type: "cash" as const,
    opening_balance: 200,
    archived: false,
    created_at: "2026-01-02T10:00:00",
    current_balance: 85,
  },
];

const entries = [
  {
    id: "entry-1",
    account_id: "account-1",
    entry_kind: "expense" as const,
    amount: 42,
    occurred_at_local: "2026-11-05T10:00:00",
    label: "Groceries",
    category: "food",
    notes: "",
    recurring_rule_id: null,
    transfer_group_id: null,
    exclude_from_insights: false,
  },
  {
    id: "entry-2",
    account_id: "account-1",
    entry_kind: "funding" as const,
    amount: 500,
    occurred_at_local: "2026-11-06T10:00:00",
    label: "Scholarship",
    category: "income",
    notes: "",
    recurring_rule_id: null,
    transfer_group_id: null,
    exclude_from_insights: false,
  },
  {
    id: "entry-3",
    account_id: "account-2",
    entry_kind: "rent_credit" as const,
    amount: 150,
    occurred_at_local: "2026-11-07T10:00:00",
    label: "Roommate share",
    category: "rent",
    notes: "",
    recurring_rule_id: null,
    transfer_group_id: null,
    exclude_from_insights: false,
  },
  {
    id: "entry-5",
    account_id: "account-1",
    entry_kind: "expense" as const,
    amount: 600,
    occurred_at_local: "2026-11-01T10:00:00",
    label: "Rent",
    category: "rent",
    notes: "",
    recurring_rule_id: null,
    transfer_group_id: null,
    exclude_from_insights: false,
  },
  {
    id: "entry-4",
    account_id: "account-2",
    entry_kind: "adjustment" as const,
    amount: -20,
    occurred_at_local: "2026-10-10T10:00:00",
    label: "Cash correction",
    category: "reconcile",
    notes: "",
    recurring_rule_id: null,
    transfer_group_id: null,
    exclude_from_insights: false,
  },
];

describe("ActivityPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.deleteEntry).mockResolvedValue(undefined);
  });

  it("shows grouped month totals and account context", () => {
    render(
      <ActivityPage
        accounts={accounts}
        entries={entries}
        monthlyCaps={[]}
        onCreate={vi.fn()}
        onEdit={vi.fn()}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        recurringRules={[]}
      />,
    );

    expect(screen.getByText("Net spend $492.00")).toBeInTheDocument();
    expect(screen.getByText("Expense $642.00")).toBeInTheDocument();
    expect(screen.getByText("Funding $500.00")).toBeInTheDocument();
    expect(screen.getByText("Rent credit $150.00")).toBeInTheDocument();
    expect(screen.getByText("Adjustment -$20.00")).toBeInTheDocument();
    expect(screen.getAllByText("Checking").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Cash").length).toBeGreaterThan(0);
  });

  it("filters by search and account", async () => {
    const user = userEvent.setup();

    render(
      <ActivityPage
        accounts={accounts}
        entries={entries}
        monthlyCaps={[]}
        onCreate={vi.fn()}
        onEdit={vi.fn()}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        recurringRules={[]}
      />,
    );

    await user.type(screen.getByPlaceholderText("Search label, notes, category, kind"), "roommate");
    expect(screen.getByText("Roommate share")).toBeInTheDocument();
    expect(screen.queryByText("Groceries")).not.toBeInTheDocument();

    const accountSelect = screen.getByLabelText("Filter by account");
    await user.selectOptions(accountSelect, "account-2");
    expect(screen.getByText("Roommate share")).toBeInTheDocument();
    expect(screen.queryByText("Scholarship")).not.toBeInTheDocument();
    expect(screen.getByText("Rent credit $150.00")).toBeInTheDocument();
  });

  it("deletes entries from the ledger table", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <ActivityPage
        accounts={accounts}
        entries={entries}
        monthlyCaps={[]}
        onCreate={vi.fn()}
        onEdit={vi.fn()}
        onRefresh={onRefresh}
        recurringRules={[]}
      />,
    );

    const roommateRow = screen.getByText("Roommate share").closest("tr");
    expect(roommateRow).not.toBeNull();

    await user.click(
      within(roommateRow as HTMLTableRowElement).getByRole("button", { name: "Delete" }),
    );

    await waitFor(() => {
      expect(api.deleteEntry).toHaveBeenCalledWith("entry-3");
    });
    expect(onRefresh).toHaveBeenCalled();
  });
});
