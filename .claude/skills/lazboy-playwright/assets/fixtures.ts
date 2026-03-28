/**
 * La-Z-Boy Custom Playwright Fixtures
 *
 * Import `test` and `expect` from this file in ALL test files — never from @playwright/test directly.
 * This ensures every test has access to La-Z-Boy's Page Objects and auth contexts.
 *
 * Usage:
 *   import { test, expect } from "../fixtures";
 *
 * To add a new fixture:
 *   1. Import the Page Object class
 *   2. Add it to the `LazboyFixtures` type
 *   3. Add the fixture definition in test.extend()
 */
import { test as base, Page, Browser } from "@playwright/test";

// Import your Page Object classes here as you create them:
// import { ProductDetailPage } from "./products/product-detail-page";
// import { CheckoutPage } from "./checkout/checkout-page";
// import { CartPage } from "./cart/cart-page";

// ---------------------------------------------------------------------------
// Fixture type definitions
// ---------------------------------------------------------------------------

type AuthFixtures = {
  /** Authenticated customer browser page */
  customerPage: Page;
  /** Authenticated store admin page */
  adminPage: Page;
  /** Unauthenticated guest page */
  guestPage: Page;
};

// type PageFixtures = {
//   productPage: ProductDetailPage;
//   checkoutPage: CheckoutPage;
//   cartPage: CartPage;
// };

// type LazboyFixtures = AuthFixtures & PageFixtures;
type LazboyFixtures = AuthFixtures;

// ---------------------------------------------------------------------------
// Fixture implementations
// ---------------------------------------------------------------------------

export const test = base.extend<LazboyFixtures>({
  /**
   * Authenticated customer page.
   * Uses storageState saved by global-setup.ts.
   * Use for tests that require a logged-in shopper.
   */
  customerPage: async ({ browser }: { browser: Browser }, use: (page: Page) => Promise<void>) => {
    const ctx = await browser.newContext({
      storageState: ".auth/customer.json",
    });
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },

  /**
   * Authenticated admin page.
   * Uses storageState saved by global-setup.ts.
   * Use for tests that require admin/back-office access.
   */
  adminPage: async ({ browser }: { browser: Browser }, use: (page: Page) => Promise<void>) => {
    const ctx = await browser.newContext({
      storageState: ".auth/admin.json",
    });
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },

  /**
   * Unauthenticated guest page.
   * No storageState — fresh browser context.
   * Use for testing login flows, registration, public pages.
   */
  guestPage: async ({ browser }: { browser: Browser }, use: (page: Page) => Promise<void>) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },

  // Uncomment and extend as you build Page Objects:
  //
  // productPage: async ({ page }, use) => {
  //   await use(new ProductDetailPage(page));
  // },
  //
  // checkoutPage: async ({ page }, use) => {
  //   await use(new CheckoutPage(page));
  // },
  //
  // cartPage: async ({ page }, use) => {
  //   await use(new CartPage(page));
  // },
});

// Re-export expect so test files only need one import
export { expect } from "@playwright/test";
