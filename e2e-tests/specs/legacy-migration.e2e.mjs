import { bodyText, openWorkspace, waitForAppReady, waitForText, waitForVisible } from "./helpers.mjs";

describe("Student Budget Tracker legacy migration", () => {
  it("auto-migrates a seeded legacy database into the new workspace", async () => {
    await waitForAppReady();

    await openWorkspace("Accounts", "Work with real pockets of money.");
    await waitForVisible("//td[normalize-space()='Primary Account']");

    await openWorkspace("Activity", "Every movement, grouped and searchable.");
    await waitForText("Scholarship payment");
    await waitForText("Roommate rent");

    await openWorkspace("Plan", "Turn pressure into a plan you can audit.");
    await waitForText("Migrated Rent Plan");
    await waitForText("Utilities");

    await openWorkspace("Settings", "Local data, explicit controls, recoverable state.");
    const text = await bodyText();
    if (!text.includes("Legacy DB detected") || !text.includes("Migration already run")) {
      throw new Error(`Migration status summary did not render as expected.\n\n${text}`);
    }
    if (text.includes("Migration already runNo")) {
      throw new Error(`Legacy migration did not execute automatically.\n\n${text}`);
    }
  });
});
