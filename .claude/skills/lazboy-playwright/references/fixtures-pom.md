# Fixtures, Page Objects, and Auth Patterns

Read this when setting up Page Object classes, custom fixtures, or multi-role authentication patterns.

---

## Table of Contents
1. [Page Object Model](#1-page-object-model)
2. [Custom Fixtures with test.extend()](#2-custom-fixtures-with-testextend)
3. [Multi-Role Auth Fixtures](#3-multi-role-auth-fixtures)
4. [Helpers and Data Generation](#4-helpers-and-data-generation)

---

## 1. Page Object Model

Every page (or major section) gets a Page Object class. Page Objects encapsulate how to interact with that page — tests use them without knowing about selectors.

### BasePage (copy from `assets/base-page.ts`)

```typescript
import { Page, Locator } from "@playwright/test";

export class BasePage {
  constructor(protected page: Page) {}

  async goto(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState("networkidle");
  }

  async getTitle(): Promise<string> {
    return this.page.title();
  }

  async takeScreenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `screenshots/${name}.png` });
  }
}
```

### Example Page Object — Product Detail Page

```typescript
import { Page, Locator, expect } from "@playwright/test";
import { BasePage } from "../base-page";

export class ProductDetailPage extends BasePage {
  private readonly addToCartButton: Locator;
  private readonly productPrice: Locator;
  private readonly productTitle: Locator;
  private readonly cartCount: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.getByRole("button", { name: "Add to Cart" });
    this.productPrice = page.getByTestId("product-price");
    this.productTitle = page.getByRole("heading", { level: 1 });
    this.cartCount = page.getByTestId("cart-count");
  }

  async gotoProduct(sku: string): Promise<void> {
    await this.goto(`/products/${sku}`);
  }

  async addToCart(): Promise<void> {
    await this.addToCartButton.click();
    // Wait for cart to update before returning
    await expect(this.cartCount).not.toHaveText("0");
  }

  async getPrice(): Promise<string> {
    return (await this.productPrice.textContent()) ?? "";
  }

  async verifyProductLoaded(expectedName: string): Promise<void> {
    await expect(this.productTitle).toContainText(expectedName, { ignoreCase: true });
    await expect(this.addToCartButton).toBeVisible();
    await expect(this.productPrice).toBeVisible();
  }
}
```

### What goes in BasePage vs. page-specific classes

| Move to `BasePage` | Keep in page-specific class |
|---|---|
| Common navigation (`goto`) | Page-specific locators |
| Shared UI patterns (toast, modal, nav) | Business actions (`addToCart`, `checkout`) |
| Common assertions (page title, URL) | Page-specific assertions |
| Error handling and retry wrappers | — |

---

## 2. Custom Fixtures with test.extend()

Custom fixtures compose Playwright's built-in fixtures with your own setup. Import from `fixtures.ts` in every test file — never from `@playwright/test` directly.

```typescript
// tests/fixtures.ts
import { test as base, Page } from "@playwright/test";
import { ProductDetailPage } from "./products/product-detail-page";
import { CheckoutPage } from "./checkout/checkout-page";
import { CartPage } from "./cart/cart-page";

type Fixtures = {
  productPage: ProductDetailPage;
  checkoutPage: CheckoutPage;
  cartPage: CartPage;
};

export const test = base.extend<Fixtures>({
  productPage: async ({ page }, use) => {
    await use(new ProductDetailPage(page));
  },
  checkoutPage: async ({ page }, use) => {
    await use(new CheckoutPage(page));
  },
  cartPage: async ({ page }, use) => {
    await use(new CartPage(page));
  },
});

export { expect } from "@playwright/test";
```

Using in a test:

```typescript
import { test, expect } from "../fixtures";

test("add product and view cart", async ({ productPage, cartPage }) => {
  await productPage.gotoProduct("lzb-barcelona-001");
  await productPage.addToCart();

  await cartPage.goto("/cart");
  await expect(cartPage.getItemByName("Barcelona Recliner")).toBeVisible();
});
```

---

## 3. Multi-Role Auth Fixtures

Different tests need different auth states — guest, logged-in customer, store associate, admin. Use `storageState` to create pre-authenticated browser contexts for each role.

```typescript
// global-setup.ts — runs once before the entire test suite
import { chromium, FullConfig } from "@playwright/test";

async function globalSetup(config: FullConfig): Promise<void> {
  const { baseURL } = config.projects[0].use;
  const browser = await chromium.launch();

  // Save customer auth state
  const customerPage = await browser.newPage();
  await customerPage.goto(`${baseURL}/login`);
  await customerPage.getByLabel("Email").fill(process.env.TEST_CUSTOMER_EMAIL!);
  await customerPage.getByLabel("Password").fill(process.env.TEST_CUSTOMER_PASSWORD!);
  await customerPage.getByRole("button", { name: "Sign In" }).click();
  await customerPage.waitForURL("**/account");
  await customerPage.context().storageState({ path: ".auth/customer.json" });

  // Save admin auth state
  const adminPage = await browser.newPage();
  await adminPage.goto(`${baseURL}/admin/login`);
  await adminPage.getByLabel("Email").fill(process.env.TEST_ADMIN_EMAIL!);
  await adminPage.getByLabel("Password").fill(process.env.TEST_ADMIN_PASSWORD!);
  await adminPage.getByRole("button", { name: "Sign In" }).click();
  await adminPage.waitForURL("**/admin/dashboard");
  await adminPage.context().storageState({ path: ".auth/admin.json" });

  await browser.close();
}

export default globalSetup;
```

```typescript
// tests/fixtures.ts — expose role-specific page fixtures
type AuthFixtures = {
  customerPage: Page;   // authenticated as customer
  adminPage: Page;      // authenticated as admin
  guestPage: Page;      // no auth (default)
};

export const test = base.extend<AuthFixtures>({
  customerPage: async ({ browser }, use) => {
    const ctx = await browser.newContext({ storageState: ".auth/customer.json" });
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },
  adminPage: async ({ browser }, use) => {
    const ctx = await browser.newContext({ storageState: ".auth/admin.json" });
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },
  guestPage: async ({ browser }, use) => {
    const ctx = await browser.newContext();  // no storageState
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },
});
```

---

## 4. Helpers and Data Generation

```typescript
// tests/helpers.ts

/** Generate a unique test email that won't collide between parallel runs */
export function testEmail(prefix = "test"): string {
  const timestamp = Date.now();
  return `${prefix}+${timestamp}@lazboy-test.com`;
}

/** Assert a response is OK and return its JSON body */
export async function assertApiOk<T>(response: Response): Promise<T> {
  if (!response.ok()) {
    throw new Error(`API call failed: ${response.status()} ${response.url()}`);
  }
  return response.json() as Promise<T>;
}

/** Seed a test product via API and return its SKU */
export async function seedProduct(
  request: APIRequestContext,
  overrides: Partial<ProductPayload> = {}
): Promise<string> {
  const payload: ProductPayload = {
    name: "Test Recliner",
    price: 999.99,
    category: "seating",
    ...overrides,
  };
  const response = await request.post("/api/test/products", {
    data: payload,
    headers: { Authorization: `Bearer ${process.env.TEST_API_TOKEN}` },
  });
  const { sku } = await assertApiOk<{ sku: string }>(response);
  return sku;
}
```
