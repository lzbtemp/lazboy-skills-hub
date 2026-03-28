/**
 * La-Z-Boy BasePage — extend this for every Page Object in the project.
 *
 * Usage:
 *   import { BasePage } from "../base-page";
 *
 *   export class CheckoutPage extends BasePage {
 *     async placeOrder(): Promise<void> { ... }
 *   }
 */
import { Page, Locator, expect } from "@playwright/test";

export class BasePage {
  constructor(protected readonly page: Page) {}

  // --- Navigation ---

  /** Navigate to a path and wait for the page to fully load. */
  async goto(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState("networkidle");
  }

  /** Wait until the URL matches the given pattern. */
  async waitForUrl(urlPattern: string | RegExp): Promise<void> {
    await this.page.waitForURL(urlPattern);
    await this.page.waitForLoadState("networkidle");
  }

  // --- Common UI Interactions ---

  /** Close any dismissible toast/notification if one is visible. */
  async dismissToast(): Promise<void> {
    const toast = this.page.getByRole("alert");
    if (await toast.isVisible()) {
      const closeBtn = toast.getByRole("button", { name: /close|dismiss/i });
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
      }
    }
  }

  /** Wait for and accept a browser dialog (alert/confirm). */
  async acceptDialog(): Promise<void> {
    this.page.once("dialog", (dialog) => dialog.accept());
  }

  /** Scroll an element into view before interacting with it. */
  async scrollTo(locator: Locator): Promise<void> {
    await locator.scrollIntoViewIfNeeded();
  }

  // --- Common Assertions ---

  /** Assert the page title matches. */
  async assertTitle(expected: string | RegExp): Promise<void> {
    await expect(this.page).toHaveTitle(expected);
  }

  /** Assert the current URL matches. */
  async assertUrl(expected: string | RegExp): Promise<void> {
    await expect(this.page).toHaveURL(expected);
  }

  /** Assert a success message or toast is visible. */
  async assertSuccessMessage(text: string | RegExp): Promise<void> {
    await expect(
      this.page.getByRole("alert").filter({ hasText: text })
    ).toBeVisible();
  }

  /** Assert an error message is visible. */
  async assertErrorMessage(text: string | RegExp): Promise<void> {
    await expect(
      this.page.getByRole("alert", { name: /error|warning/i }).filter({ hasText: text })
    ).toBeVisible();
  }

  // --- Debugging Helpers (remove before committing) ---

  /** Take a named screenshot for debugging. */
  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `debug-screenshots/${name}-${Date.now()}.png`,
      fullPage: true,
    });
  }

  /** Log the current page URL and title — useful during test development. */
  async logPageInfo(): Promise<void> {
    console.log(`URL: ${this.page.url()}`);
    console.log(`Title: ${await this.page.title()}`);
  }
}
