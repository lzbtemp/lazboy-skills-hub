---
name: lazboy-playwright
description: "Write, run, and maintain Playwright end-to-end tests for La-Z-Boy web applications. Apply this skill whenever writing browser tests, UI automation, or web testing scripts for any La-Z-Boy site or app — even if the user doesn't say 'Playwright'. Trigger on: e2e test, end-to-end, browser test, UI test, Playwright, test automation, selenium replacement, click testing, form testing, checkout flow test, product page test, or any request to automate or verify web UI behavior for La-Z-Boy."
version: "1.0.0"
category: QA/Testing
tags: [testing, qa, playwright, e2e, automation]
---

# La-Z-Boy Playwright Skill

Write reliable, maintainable Playwright tests for La-Z-Boy web applications using TypeScript and `@playwright/test`. This skill covers test structure, selector strategy, authentication, CI/CD, and the agent-specific workflow for discovering and testing live apps.

**Reference files — load when needed:**
- `references/selectors.md` — Selector hierarchy, locator patterns, accessibility-aware querying
- `references/fixtures-pom.md` — Page Object Model, custom fixtures, `storageState` auth reuse
- `references/ci-cd.md` — GitHub Actions config, sharding, Trace Viewer, HTML reports
- `assets/playwright.config.ts` — Standard La-Z-Boy config (copy to new projects)
- `assets/base-page.ts` — BasePage class template
- `assets/fixtures.ts` — Custom fixture setup template

---

## 1. Agent Workflow — Discover Before You Write

Before writing any test, understand the running application. Skipping this step is the most common cause of brittle selectors and false failures.

```
1. Detect the dev server — don't hardcode URLs
2. Navigate to the page under test
3. Wait for networkidle — ensure all dynamic content has loaded
4. Take a screenshot + inspect the DOM to find real selectors
5. Identify interactive elements by role/label/testid
6. Write the test using what you observed
```

### Detect the dev server

```typescript
// Prefer env var; fall back to common La-Z-Boy dev ports
const BASE_URL = process.env.BASE_URL
  ?? process.env.PLAYWRIGHT_BASE_URL
  ?? "http://localhost:3000";
```

Never hardcode `localhost:3000` directly in test files — use `baseURL` from `playwright.config.ts`.

### Inject identifying headers (agent runs only)

When running as an agent, inject a header so the backend can identify automated traffic:

```typescript
await page.setExtraHTTPHeaders({
  "X-Automated-By": "playwright-lazboy",
  "X-Test-Run": process.env.CI ? "ci" : "local",
});
```

---

## 2. Project Structure

Follow this layout for all La-Z-Boy Playwright projects:

```
tests/
├── fixtures.ts                    # Custom test fixtures (extend base `test`)
├── helpers.ts                     # Data generators, API helpers, custom assertions
└── {feature}/
    ├── {feature}-page.ts          # Page Object for this feature
    ├── {feature}.spec.ts          # All tests for this feature
    └── {feature}.md               # Notes on selectors, edge cases, known issues
playwright.config.ts
```

One spec file per feature/page — don't split by test type. Keep related tests together so a developer working on `checkout` finds everything in `tests/checkout/`.

---

## 3. Selector Strategy

Choose selectors in this priority order — the top choices are most resilient to UI refactors:

| Priority | Selector | When to use |
|---|---|---|
| 1 | `getByRole('button', { name: 'Add to Cart' })` | Interactive elements — aligns with accessibility |
| 2 | `getByLabel('Email address')` | Form inputs |
| 3 | `getByTestId('product-card')` | Components without stable roles/labels |
| 4 | `getByText('Live life comfortably')` | Static text that won't change |
| 5 | CSS `.product-title` | Last resort — breaks on class renames |

`getByRole` is preferred for buttons, links, and inputs because it tests accessibility at the same time — if a screen reader can't find the element, neither can the test.

> Read `references/selectors.md` for chaining, filtering, and complex locator patterns.

---

## 4. Writing Tests

### Structure

```typescript
import { test, expect } from "./fixtures";  // always import from local fixtures, not @playwright/test

test.describe("Product Detail Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/products/lzb-recliner-001");
    await page.waitForLoadState("networkidle");
  });

  test("displays product name and price",
    { tag: ["@critical", "@pdp", "@PDP-E2E-001"] },
    async ({ page }) => {
      await expect(page.getByRole("heading", { name: /recliner/i })).toBeVisible();
      await expect(page.getByTestId("product-price")).toContainText("$");
    }
  );

  test("adds product to cart",
    { tag: ["@e2e", "@pdp", "@cart", "@PDP-E2E-002"] },
    async ({ page }) => {
      await page.getByRole("button", { name: "Add to Cart" }).click();
      await expect(page.getByTestId("cart-count")).toHaveText("1");
    }
  );
});
```

### Tag every test

Tags make it easy to run subsets: `npx playwright test --grep @critical`

| Tag type | Format | Examples |
|---|---|---|
| Priority | `@critical`, `@smoke` | Smoke suite for deployments |
| Feature | `@pdp`, `@cart`, `@checkout` | Run only checkout tests |
| Type | `@e2e`, `@visual`, `@a11y` | Run only accessibility tests |
| ID | `@PDP-E2E-001` | Link to ticket/test case |

### Waiting — use `expect` auto-retry, not manual waits

Playwright's `expect` automatically retries assertions until the timeout — manual `waitForTimeout` or sleep loops are almost never needed.

```typescript
// Correct — expect retries automatically
await expect(page.getByTestId("success-banner")).toBeVisible();

// Wrong — hard-coded waits are fragile and slow
await page.waitForTimeout(2000);
```

The only time to use explicit waits is for navigation or network events:
```typescript
await page.waitForLoadState("networkidle");   // after navigation
await page.waitForURL("**/confirmation");      // after form submit
```

---

## 5. Authentication — Reuse Session State

Logging in through the UI for every test is slow and adds flakiness. Playwright's `storageState` saves cookies and localStorage after one login, then all subsequent tests load it instead of re-logging in.

```typescript
// global-setup.ts — runs once before all tests
import { chromium } from "@playwright/test";

async function globalSetup() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(process.env.BASE_URL + "/login");
  await page.getByLabel("Email").fill(process.env.TEST_EMAIL!);
  await page.getByLabel("Password").fill(process.env.TEST_PASSWORD!);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL("**/dashboard");

  // Save authenticated state
  await page.context().storageState({ path: "auth.json" });
  await browser.close();
}

export default globalSetup;
```

```typescript
// playwright.config.ts — load saved auth for all tests
use: {
  storageState: "auth.json",
}
```

Store credentials in env vars, never in code: `TEST_EMAIL`, `TEST_PASSWORD`.

> Read `references/fixtures-pom.md` for fixtures that inject authenticated vs. guest page contexts.

---

## 6. API Setup + UI Assertion

Use Playwright's `request` fixture to seed test data via API, then assert the UI reflects it. This is faster and more reliable than driving everything through the browser.

```typescript
test("order history shows most recent order", async ({ page, request }) => {
  // Seed an order via API (fast, no UI flakiness)
  const order = await request.post("/api/orders", {
    data: { sku: "LZB-001", quantity: 1 },
    headers: { Authorization: `Bearer ${process.env.TEST_API_TOKEN}` },
  });
  expect(order.ok()).toBeTruthy();
  const { orderId } = await order.json();

  // Assert the UI shows it
  await page.goto("/account/orders");
  await expect(page.getByTestId(`order-${orderId}`)).toBeVisible();
});
```

---

## 7. What NOT to Do

- **Don't use `page.waitForTimeout()`** for anything other than a last-resort debugging aid — use `expect` auto-retry or explicit load state waits instead
- **Don't hardcode `localhost:3000`** in test files — always go through `baseURL` in config
- **Don't hardcode credentials** — always use `TEST_EMAIL` / `TEST_PASSWORD` env vars
- **Don't use CSS class selectors** as a first choice — classes change during refactors; prefer role/label/testid
- **Don't write one test per action** — group related assertions in the same `test()` to reduce setup overhead and flakiness
- **Don't skip `waitForLoadState('networkidle')`** after navigation to pages with dynamic content — premature DOM inspection is the #1 cause of flaky tests

---

## 8. Resources

| Resource | When to use |
|---|---|
| `references/selectors.md` | Complex locators, chaining, filtering, iframe handling |
| `references/fixtures-pom.md` | POM class patterns, custom fixtures, multi-role auth |
| `references/ci-cd.md` | GitHub Actions setup, sharding, Trace Viewer, HTML reports |
| `assets/playwright.config.ts` | Copy to any new La-Z-Boy test project |
| `assets/base-page.ts` | Extend for every page object |
| `assets/fixtures.ts` | Extend for custom test fixtures |
