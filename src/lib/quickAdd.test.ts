import { describe, expect, it } from "vitest";

import { parseQuickAdd } from "./quickAdd";

describe("parseQuickAdd", () => {
  it("parses amount and label into an expense entry", () => {
    const result = parseQuickAdd("42 groceries", {
      id: "acc-1",
      name: "Checking",
      type: "checking",
      opening_balance: 0,
      archived: false,
      created_at: "2026-01-01T00:00:00",
      current_balance: 0,
    });

    expect(result?.amount).toBe(42);
    expect(result?.label).toBe("groceries");
    expect(result?.entry_kind).toBe("expense");
  });
});
