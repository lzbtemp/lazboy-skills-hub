# Playwright Selector Patterns

Read this for complex locator patterns — chaining, filtering, iframe handling, and accessibility-aware querying.

---

## Table of Contents
1. [Selector Priority Rationale](#1-selector-priority-rationale)
2. [Locator Chaining and Filtering](#2-locator-chaining-and-filtering)
3. [Form Inputs](#3-form-inputs)
4. [Dynamic and List Content](#4-dynamic-and-list-content)
5. [Iframes and Shadow DOM](#5-iframes-and-shadow-dom)
6. [Debugging Selectors](#6-debugging-selectors)

---

## 1. Selector Priority Rationale

### Why `getByRole` first?

`getByRole` mirrors how assistive technologies (screen readers) navigate the page. A test that finds a button by its ARIA role and accessible name is simultaneously testing that the element is correctly labeled for accessibility. If the role or name is wrong, both the test and the screen reader fail — which is the right behavior.

```typescript
// Tests the button exists AND is accessible
await page.getByRole("button", { name: "Add to Cart" }).click();

// Only tests that a CSS class exists — provides no accessibility signal
await page.locator(".add-to-cart-btn").click();
```

### When to use `getByTestId`

`getByTestId` is the right choice when an element has no meaningful semantic role (e.g., a product card container that's a `<div>`). Add `data-testid` attributes to components that tests need to target — this is an explicit contract between dev and QA.

```html
<!-- In the React component -->
<div data-testid="product-card" data-sku={product.sku}>
```

```typescript
// In the test
const card = page.getByTestId("product-card").filter({ hasText: "Barcelona Recliner" });
```

---

## 2. Locator Chaining and Filtering

### Scope a locator within a parent

```typescript
// Find the price inside a specific product card
const productCard = page.getByTestId("product-card").filter({ hasText: "Barcelona Recliner" });
const price = productCard.getByTestId("product-price");
await expect(price).toContainText("$1,299");
```

### Filter by child content

```typescript
// Find a list item that contains a specific badge
const featuredItem = page.getByRole("listitem").filter({
  has: page.getByTestId("featured-badge"),
});
```

### nth() for indexed items

```typescript
// First product in a grid (0-indexed)
const firstProduct = page.getByTestId("product-card").nth(0);

// Last item in cart
const lastCartItem = page.getByTestId("cart-item").last();
```

### And/or locator composition

```typescript
// Element that is both a link AND contains "View Details"
const viewLink = page.getByRole("link").and(page.getByText("View Details"));
```

---

## 3. Form Inputs

```typescript
// By label text (preferred — tests accessibility contract)
await page.getByLabel("Email address").fill("test@lazboy.com");

// By placeholder (acceptable when no label exists)
await page.getByPlaceholder("Search products...").fill("recliner");

// Dropdown / select
await page.getByLabel("Fabric Grade").selectOption("Grade A");

// Checkbox / radio
await page.getByRole("checkbox", { name: "Add protection plan" }).check();
await page.getByRole("radio", { name: "Ship to address" }).click();

// File upload
await page.getByLabel("Upload image").setInputFiles("./test-image.jpg");
```

---

## 4. Dynamic and List Content

### Wait for list to populate

```typescript
// Wait until at least one product card exists
await expect(page.getByTestId("product-card").first()).toBeVisible();

// Then assert count
await expect(page.getByTestId("product-card")).toHaveCount(12);
```

### Iterate over list items

```typescript
const items = page.getByTestId("cart-item");
const count = await items.count();

for (let i = 0; i < count; i++) {
  const item = items.nth(i);
  const name = await item.getByTestId("item-name").textContent();
  console.log(`Cart item ${i + 1}: ${name}`);
}
```

### Find by dynamic attribute

```typescript
// Product card for a specific SKU
const product = page.locator('[data-sku="LZB-BARCELONA-001"]');

// Order row for a specific order ID
const orderRow = page.locator(`[data-order-id="${orderId}"]`);
```

---

## 5. Iframes and Shadow DOM

### Handle iframes (e.g., payment widgets, third-party embeds)

```typescript
// Wait for iframe to load
const paymentFrame = page.frameLocator("#stripe-payment-iframe");

// Interact within the iframe
await paymentFrame.getByLabel("Card number").fill("4242 4242 4242 4242");
await paymentFrame.getByLabel("Expiry date").fill("12/26");
await paymentFrame.getByLabel("CVC").fill("123");
```

### Shadow DOM

```typescript
// Playwright pierces shadow DOM automatically for most locators
// If needed, use >> to pierce explicitly
const shadowInput = page.locator("my-custom-element >> input");
```

---

## 6. Debugging Selectors

### Playwright Inspector — explore selectors interactively

```bash
PWDEBUG=1 npx playwright test tests/checkout/checkout.spec.ts
```

This opens the inspector with a selector playground and step-through debugging.

### Use `page.pause()` in a test

```typescript
test("debug checkout", async ({ page }) => {
  await page.goto("/checkout");
  await page.pause();  // Opens inspector; remove before committing
  await page.getByRole("button", { name: "Place Order" }).click();
});
```

### Screenshot on failure (configured in `playwright.config.ts`)

```typescript
// In config — captures screenshot automatically on test failure
use: {
  screenshot: "only-on-failure",
  trace: "retain-on-failure",
}
```
