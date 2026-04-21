import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import { QuickAddBar } from "./QuickAddBar";

vi.mock("../lib/api", () => ({
  createEntry: vi.fn(),
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

describe("QuickAddBar", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.createEntry).mockResolvedValue(undefined);
  });

  it("uses active accounts only and recovers after accounts load", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<QuickAddBar accounts={[]} onSaved={onSaved} />);

    expect(screen.getByRole("button", { name: "Add expense" })).toBeDisabled();

    rerender(<QuickAddBar accounts={[archivedAccount, activeAccount]} onSaved={onSaved} />);

    expect(screen.queryByRole("option", { name: "Archived savings" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Checking" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Quick add expense"), "42 groceries");
    await user.click(screen.getByRole("button", { name: "Add expense" }));

    await waitFor(() => {
      expect(api.createEntry).toHaveBeenCalledWith(
        expect.objectContaining({
          account_id: "active-1",
          entry_kind: "expense",
          amount: 42,
          label: "groceries",
        }),
      );
    });
    expect(onSaved).toHaveBeenCalled();
    expect(screen.getByText("Saved to Checking.")).toBeInTheDocument();
  });

  it("stays disabled when there are no active accounts", () => {
    render(<QuickAddBar accounts={[archivedAccount]} onSaved={vi.fn().mockResolvedValue(undefined)} />);

    expect(screen.getByRole("button", { name: "Add expense" })).toBeDisabled();
    expect(
      screen.getByText("Create at least one active account to enable quick add."),
    ).toBeInTheDocument();
  });
});
