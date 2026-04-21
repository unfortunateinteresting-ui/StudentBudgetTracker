import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MissedRecurringBanner } from "./MissedRecurringBanner";

const missedRecurring = [
  {
    recurring_rule_id: "rule-1",
    label: "Rent",
    frequency: "monthly" as const,
    dates: ["2026-04-01", "2026-05-01", "2026-06-01"],
  },
  {
    recurring_rule_id: "rule-2",
    label: "Phone bill",
    frequency: "monthly" as const,
    dates: ["2026-06-04"],
  },
];

describe("MissedRecurringBanner", () => {
  it("shows per-rule detail and supports selective apply", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();

    render(
      <MissedRecurringBanner
        missedRecurring={missedRecurring}
        onApply={onApply}
        onDismiss={vi.fn()}
      />,
    );

    expect(screen.getByText("Missed recurring activity detected")).toBeInTheDocument();
    expect(
      screen.getByText("2 rule(s), 4 unapplied occurrence(s) before today."),
    ).toBeInTheDocument();
    expect(screen.getByText("Rent")).toBeInTheDocument();
    expect(screen.getByText("monthly rule • 3 missed dates")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Apply rule" })[0]);

    expect(onApply).toHaveBeenCalledWith(["rule-1"]);
  });

  it("supports dismissing and applying all", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    const onDismiss = vi.fn();

    render(
      <MissedRecurringBanner
        missedRecurring={missedRecurring}
        onApply={onApply}
        onDismiss={onDismiss}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Apply all" }));
    expect(onApply).toHaveBeenCalledWith();

    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalled();
  });
});
