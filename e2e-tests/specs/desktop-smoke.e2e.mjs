import {
  assertBodyMatches,
  bodyText,
  openWorkspace,
  waitForAppReady,
  waitForText,
  waitForVisible,
} from "./helpers.mjs";

describe("Student Budget Tracker desktop smoke", () => {
  it("creates an account, records a guided entry, and navigates insights", async () => {
    await waitForAppReady();

    await openWorkspace("Accounts", "Work with real pockets of money.");

    await (await $("//input[@placeholder='Account name']")).setValue("Daily Checking");
    await (await $("//input[@placeholder='Opening balance']")).setValue("500");
    await (await $("//button[normalize-space()='Create']")).click();

    await waitForVisible("//*[contains(normalize-space(.), 'Created Daily Checking.')]");
    await waitForVisible("//td[normalize-space()='Daily Checking']");

    await openWorkspace("Activity", "Every movement, grouped and searchable.");

    await (await $("//button[normalize-space()='Guided entry']")).click();
    await waitForVisible(
      "//p[contains(normalize-space(.), 'Use guided entry for funding, rent credits, manual exclusions, or adjustments.')]",
    );

    const entryKindSelect = await $("(//div[@role='dialog']//select)[2]");
    await entryKindSelect.selectByVisibleText("funding");
    await (await $("(//div[@role='dialog']//input[@type='number'])[1]")).setValue("125");
    const textInputs = await $$(
      "//div[@role='dialog']//input[not(@type='number') and not(@type='datetime-local')]",
    );
    await textInputs[0].setValue("Setup funding");
    await textInputs[1].setValue("income");
    await (await $("//button[normalize-space()='Save']")).click();

    await waitForVisible("//td[normalize-space()='Setup funding']");

    await openWorkspace("Insights", "Every chart resolves back to ledger math.");
    await waitForVisible("//th[normalize-space()='Graph spend']");

    const pageText = await bodyText();
    await waitForText("Rent net this month");
    await assertBodyMatches(/Runway remaining/i);
    await assertBodyMatches(/Rent net this month/i);
    if (!pageText.includes("Graph spend")) {
      throw new Error("Insights table did not render the monthly snapshot header.");
    }
  });
});
