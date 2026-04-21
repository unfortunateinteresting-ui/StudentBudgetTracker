import { bodyText, openWorkspace, waitForAppReady, waitForNoText, waitForText, waitForVisible } from "./helpers.mjs";

describe("Student Budget Tracker recurring catch-up", () => {
  it("shows missed recurring activity and applies the missed entries", async () => {
    await waitForAppReady();
    await waitForText("Missed recurring activity detected");
    await waitForText("Catch-up Utilities");

    await (await $("//button[normalize-space()='Apply all']")).click();
    await waitForNoText("Missed recurring activity detected");

    await openWorkspace("Activity", "Every movement, grouped and searchable.");
    await waitForVisible("//td[normalize-space()='Catch-up Utilities']");

    const text = await bodyText();
    if (!text.includes("utilities")) {
      throw new Error(`Applied recurring entry did not appear in the ledger.\n\n${text}`);
    }
  });
});
