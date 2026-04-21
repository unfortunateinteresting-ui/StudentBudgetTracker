import assert from "node:assert/strict";

export async function waitForVisible(selector, timeout = 30000) {
  const element = await $(selector);
  await element.waitForDisplayed({ timeout });
  return element;
}

export async function bodyText() {
  return (await $("body")).getText();
}

export async function waitForText(text, timeout = 30000) {
  await browser.waitUntil(async () => (await bodyText()).includes(text), {
    timeout,
    interval: 250,
    timeoutMsg: `Timed out waiting for text: ${text}`,
  });
}

export async function waitForNoText(text, timeout = 30000) {
  await browser.waitUntil(async () => !(await bodyText()).includes(text), {
    timeout,
    interval: 250,
    timeoutMsg: `Timed out waiting for text to disappear: ${text}`,
  });
}

export async function attachToAppWindow() {
  await browser.waitUntil(async () => (await browser.getWindowHandles()).length > 0, {
    timeout: 30000,
    timeoutMsg: "Timed out waiting for a browser window handle.",
  });

  await browser.waitUntil(
    async () => {
      const handles = await browser.getWindowHandles();
      for (const handle of handles) {
        await browser.switchToWindow(handle);
        const title = await browser.getTitle().catch(() => "");
        if (!title || title.includes("Student Budget Tracker")) {
          return true;
        }
      }
      return false;
    },
    {
      timeout: 30000,
      interval: 500,
      timeoutMsg: "Timed out waiting for the Tauri app window.",
    },
  );
}

export async function waitForAppReady() {
  await attachToAppWindow();
  try {
    await waitForVisible("//h1[normalize-space()='See the runway before you spend it.']");
  } catch (error) {
    const text = await bodyText().catch(() => "<unavailable>");
    throw new Error(`App did not finish loading the Home workspace.\n\nPage text:\n${text}`, {
      cause: error,
    });
  }
}

export async function openWorkspace(label, heading) {
  const button = await waitForVisible(`//button[normalize-space()='${label}']`);
  await button.click();
  if (heading) {
    await waitForVisible(`//h1[normalize-space()='${heading}']`);
  }
}

export async function assertBodyMatches(pattern) {
  const text = await bodyText();
  assert.match(text, pattern);
}
