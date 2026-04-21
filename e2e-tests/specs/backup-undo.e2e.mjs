import { bodyText, openWorkspace, waitForAppReady, waitForNoText, waitForText, waitForVisible } from "./helpers.mjs";

describe("Student Budget Tracker backup and undo", () => {
  it("creates a backup and undoes the most recent mutation", async () => {
    await waitForAppReady();

    await openWorkspace("Accounts", "Work with real pockets of money.");
    await (await $("//input[@placeholder='Account name']")).setValue("Undo Checking");
    await (await $("//input[@placeholder='Opening balance']")).setValue("250");
    await (await $("//button[normalize-space()='Create']")).click();
    await waitForText("Created Undo Checking.");

    await openWorkspace("Activity", "Every movement, grouped and searchable.");
    await (await $("//button[normalize-space()='Guided entry']")).click();
    await waitForVisible("//div[@role='dialog']");

    await (await $("(//div[@role='dialog']//input[@type='number'])[1]")).setValue("12");
    const textInputs = await $$(
      "//div[@role='dialog']//input[not(@type='number') and not(@type='datetime-local')]",
    );
    await textInputs[0].setValue("Undo lunch");
    await textInputs[1].setValue("food");
    await (await $("//button[normalize-space()='Save']")).click();

    await waitForVisible("//td[normalize-space()='Undo lunch']");

    await openWorkspace("Settings", "Local data, explicit controls, recoverable state.");
    await (await $("//button[normalize-space()='Create backup now']")).click();
    await waitForText("Backup created.");
    await waitForVisible("//td[contains(normalize-space(.), 'budget_')]");

    await (await $("//button[normalize-space()='Undo last action']")).click();
    await waitForText("Last action undone.");

    await openWorkspace("Activity", "Every movement, grouped and searchable.");
    await waitForNoText("Undo lunch");

    const text = await bodyText();
    if (text.includes("Undo lunch")) {
      throw new Error(`Undo did not remove the most recent entry.\n\n${text}`);
    }
  });
});
