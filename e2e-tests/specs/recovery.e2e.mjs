import { bodyText, openWorkspace, waitForAppReady, waitForText, waitForVisible } from "./helpers.mjs";

describe("Student Budget Tracker corruption recovery", () => {
  it("restores from backup and surfaces the recovery notice", async () => {
    await waitForAppReady();

    await openWorkspace("Settings", "Local data, explicit controls, recoverable state.");
    await waitForText("Recovery notice");
    await waitForText("restored from backup");

    await openWorkspace("Accounts", "Work with real pockets of money.");
    await waitForVisible("//td[normalize-space()='Recovered Checking']");

    await openWorkspace("Activity", "Every movement, grouped and searchable.");
    const text = await bodyText();
    if (!text.includes("Recovered funding")) {
      throw new Error(`Recovered ledger entry did not load after backup restore.\n\n${text}`);
    }
  });
});
