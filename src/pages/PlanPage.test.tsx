import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import type { InsightSnapshot } from "../lib/types";
import { PlanPage } from "./PlanPage";

vi.mock("../lib/api", () => ({
  applyRecurringRuleNow: vi.fn(),
  createRecurringRule: vi.fn(),
  deleteMonthlyCap: vi.fn(),
  deleteRecurringRule: vi.fn(),
  setMonthlyCap: vi.fn(),
  updateRecurringRule: vi.fn(),
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
];

const archivedAccount = {
  id: "archived-1",
  name: "Archived savings",
  type: "savings" as const,
  opening_balance: 200,
  archived: true,
  created_at: "2026-01-01T08:00:00",
  current_balance: 240,
};

const recurringRules = [
  {
    id: "rule-1",
    label: "Rent autopay",
    entry_kind: "expense" as const,
    amount: 1200,
    account_id: "account-1",
    category: "rent",
    notes: "Monthly rent",
    start_date: "2026-09-01",
    end_date: null,
    frequency: "monthly" as const,
    status: "automatic" as const,
    last_applied_local: null,
  },
];

const monthlyCaps = [
  {
    id: "cap-1",
    category: "food",
    amount: 250,
    month_key: "2026-11",
  },
  {
    id: "cap-2",
    category: "transport",
    amount: 90,
    month_key: "2026-10",
  },
];

const expenseEntry = (id: string, category: string, amount: number, occurredAt: string) => ({
  id,
  account_id: "account-1",
  entry_kind: "expense" as const,
  amount,
  occurred_at_local: occurredAt,
  label: `${category} spend`,
  category,
  notes: "",
  exclude_from_insights: false,
});

const snapshot: InsightSnapshot = {
  total_available_cash: 1325,
  this_month_spend: 200,
  this_month_cap: 250,
  school_year_runway_remaining: 900,
  projected_end_of_year_cushion: 300,
  rent_due_this_month: 1200,
  rent_paid_this_month: 1200,
  rent_credit_this_month: 0,
  rent_net_this_month: 1200,
  upcoming_obligations: [],
  recent_activity: [],
  account_balances: [],
  category_spend_this_month: [],
  monthly_series: [
    {
      month_key: "2026-11",
      spent: 180,
      cap: 250,
      runway_balance: 1145,
    },
    {
      month_key: "2026-10",
      spent: 60,
      cap: 90,
      runway_balance: 1235,
    },
  ],
  activity_groups: [
    {
      month_key: "2026-11",
      total_expense: 180,
      total_funding: 0,
      total_rent_credit: 0,
      entries: [expenseEntry("entry-1", "food", 180, "2026-11-05T12:00:00")],
    },
    {
      month_key: "2026-10",
      total_expense: 60,
      total_funding: 0,
      total_rent_credit: 0,
      entries: [expenseEntry("entry-2", "transport", 60, "2026-10-08T12:00:00")],
    },
  ],
  breakdowns: {},
};

const settings = {
  school_year_start_month: 9,
  planning_start_month_key: "2026-09",
  school_year_months: 9,
  language: "en",
  backup_retention: 50,
  last_migration_version: 2,
};

describe("PlanPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.applyRecurringRuleNow).mockResolvedValue(1);
    vi.mocked(api.createRecurringRule).mockResolvedValue(undefined);
    vi.mocked(api.deleteMonthlyCap).mockResolvedValue(undefined);
    vi.mocked(api.deleteRecurringRule).mockResolvedValue(undefined);
    vi.mocked(api.setMonthlyCap).mockResolvedValue(undefined);
    vi.mocked(api.updateRecurringRule).mockResolvedValue(undefined);
  });

  it("loads a recurring rule into edit mode and updates it", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <PlanPage
        accounts={accounts}
        monthlyCaps={monthlyCaps}
        onRefresh={onRefresh}
        onWhy={vi.fn()}
        recurringRules={recurringRules}
        settings={settings}
        snapshot={snapshot}
      />,
    );

    const ruleRow = screen.getByText("Rent autopay").closest("tr");
    expect(ruleRow).not.toBeNull();

    await user.click(within(ruleRow as HTMLTableRowElement).getByRole("button", { name: "Edit" }));

    const labelInput = screen.getByDisplayValue("Rent autopay");
    await user.clear(labelInput);
    await user.type(labelInput, "Apartment rent");
    await user.click(screen.getByRole("button", { name: "Update rule" }));

    await waitFor(() => {
      expect(api.updateRecurringRule).toHaveBeenCalledWith("rule-1", {
        label: "Apartment rent",
        entry_kind: "expense",
        amount: 1200,
        account_id: "account-1",
        category: "rent",
        notes: "Monthly rent",
        start_date: "2026-09-01",
        end_date: null,
        frequency: "monthly",
        status: "automatic",
      });
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it("locks cap identity fields during edit and updates the amount", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <PlanPage
        accounts={accounts}
        monthlyCaps={monthlyCaps}
        onRefresh={onRefresh}
        onWhy={vi.fn()}
        recurringRules={recurringRules}
        settings={settings}
        snapshot={snapshot}
      />,
    );

    const capSection = screen.getByText("Nov 2026 cap coverage").closest("section");
    expect(capSection).not.toBeNull();

    const capRow = within(capSection as HTMLElement)
      .getAllByText("food")
      .map((node) => node.closest("tr"))
      .find((row) => row && within(row).queryByRole("button", { name: "Edit" }));
    expect(capRow).not.toBeNull();

    await user.click(within(capRow as HTMLTableRowElement).getByRole("button", { name: "Edit" }));

    expect(screen.getByDisplayValue("food")).toBeDisabled();
    expect(screen.getByDisplayValue("2026-11")).toBeDisabled();

    const amountInput = screen.getByDisplayValue("250");
    await user.clear(amountInput);
    await user.type(amountInput, "320");
    await user.click(screen.getByRole("button", { name: "Update cap" }));

    await waitFor(() => {
      expect(api.setMonthlyCap).toHaveBeenCalledWith({
        category: "food",
        amount: 320,
        month_key: "2026-11",
      });
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it("uses active accounts only when creating a new recurring rule", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <PlanPage
        accounts={[archivedAccount, ...accounts]}
        monthlyCaps={monthlyCaps}
        onRefresh={onRefresh}
        onWhy={vi.fn()}
        recurringRules={recurringRules}
        settings={settings}
        snapshot={snapshot}
      />,
    );

    expect(
      screen.queryByRole("option", { name: "Archived savings (archived)" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Checking" })).toBeInTheDocument();

    const labelInput = screen.getByPlaceholderText("Rule label");
    await user.type(labelInput, "Book stipend");

    const amountInput = screen.getAllByPlaceholderText("Amount")[0];
    await user.clear(amountInput);
    await user.type(amountInput, "85");

    await user.click(screen.getByRole("button", { name: "Save rule" }));

    await waitFor(() => {
      expect(api.createRecurringRule).toHaveBeenCalledWith(
        expect.objectContaining({
          account_id: "account-1",
          label: "Book stipend",
          amount: 85,
        }),
      );
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it("filters the cap table by selected month", async () => {
    const user = userEvent.setup();

    render(
      <PlanPage
        accounts={accounts}
        monthlyCaps={monthlyCaps}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        onWhy={vi.fn()}
        recurringRules={recurringRules}
        settings={settings}
        snapshot={snapshot}
      />,
    );

    let capSection = screen.getByText("Nov 2026 cap coverage").closest("section");
    expect(capSection).not.toBeNull();
    expect(within(capSection as HTMLElement).getByText("food")).toBeInTheDocument();
    expect(within(capSection as HTMLElement).queryByText("transport")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Show month"), "2026-10");

    capSection = screen.getByText("Oct 2026 cap coverage").closest("section");
    expect(capSection).not.toBeNull();
    expect(within(capSection as HTMLElement).getByText("transport")).toBeInTheDocument();
    expect(within(capSection as HTMLElement).queryByText("food")).not.toBeInTheDocument();
  });
});
