import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import { AccountsPage } from "./AccountsPage";

vi.mock("../lib/api", () => ({
  archiveAccount: vi.fn(),
  createAccount: vi.fn(),
  createTransfer: vi.fn(),
  reconcileAccount: vi.fn(),
  updateAccount: vi.fn(),
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
    name: "Savings",
    type: "savings" as const,
    opening_balance: 500,
    archived: true,
    created_at: "2026-01-02T10:00:00",
    current_balance: 640,
  },
];

describe("AccountsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.archiveAccount).mockResolvedValue(undefined);
    vi.mocked(api.createAccount).mockResolvedValue(undefined);
    vi.mocked(api.createTransfer).mockResolvedValue(undefined);
    vi.mocked(api.reconcileAccount).mockResolvedValue(undefined);
    vi.mocked(api.updateAccount).mockResolvedValue(undefined);
  });

  it("loads an account into edit mode and updates it", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(<AccountsPage accounts={accounts} onRefresh={onRefresh} />);

    const checkingRow = screen
      .getAllByText("Checking")
      .map((node) => node.closest("tr"))
      .find((row) => row && within(row).queryByRole("button", { name: "Edit" }));
    expect(checkingRow).not.toBeNull();

    await user.click(within(checkingRow as HTMLTableRowElement).getByRole("button", { name: "Edit" }));

    const nameInput = screen.getByPlaceholderText("Account name");
    await user.clear(nameInput);
    await user.type(nameInput, "Main checking");
    await user.click(screen.getByRole("button", { name: "Update" }));

    await waitFor(() => {
      expect(api.updateAccount).toHaveBeenCalledWith("account-1", {
        name: "Main checking",
        type: "checking",
      });
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it("archives active accounts and restores archived ones", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(<AccountsPage accounts={accounts} onRefresh={onRefresh} />);

    const checkingRow = screen
      .getAllByText("Checking")
      .map((node) => node.closest("tr"))
      .find((row) => row && within(row).queryByRole("button", { name: "Archive" }));
    const savingsRow = screen
      .getAllByText("Savings")
      .map((node) => node.closest("tr"))
      .find((row) => row && within(row).queryByRole("button", { name: "Restore" }));
    expect(checkingRow).not.toBeNull();
    expect(savingsRow).not.toBeNull();

    await user.click(
      within(checkingRow as HTMLTableRowElement).getByRole("button", { name: "Archive" }),
    );
    await waitFor(() => {
      expect(api.archiveAccount).toHaveBeenCalledWith("account-1");
    });

    await user.click(
      within(savingsRow as HTMLTableRowElement).getByRole("button", { name: "Restore" }),
    );
    await waitFor(() => {
      expect(api.updateAccount).toHaveBeenCalledWith("account-2", {
        archived: false,
      });
    });
  });
});
