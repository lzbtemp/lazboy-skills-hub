# Playwright Selector Strategies Guide

Best practices for writing stable, maintainable selectors in Playwright tests.

---

## Table of Contents

1. [Selector Priority](#1-selector-priority)
2. [Role-Based Selectors](#2-role-based-selectors)
3. [Text-Based Selectors](#3-text-based-selectors)
4. [Test ID Selectors](#4-test-id-selectors)
5. [Label-Based Selectors](#5-label-based-selectors)
6. [CSS Selectors](#6-css-selectors)
7. [XPath Selectors](#7-xpath-selectors)
8. [Chaining and Filtering](#8-chaining-and-filtering)
9. [Nth and Positional Selectors](#9-nth-and-positional-selectors)
10. [Frame Handling](#10-frame-handling)
11. [Shadow DOM](#11-shadow-dom)
12. [Best Practices](#12-best-practices)

---

## 1. Selector Priority

Use selectors in this order of preference. Higher priority selectors are more resilient to code changes and more closely match how users identify elements.

| Priority | Selector Type | Why |
|----------|--------------|-----|
| 1 | `getByRole` | Matches accessible role; resilient to text/structure changes |
| 2 | `getByLabel` | Tied to form label; stable and accessible |
| 3 | `getByPlaceholder` | Reasonably stable for inputs |
| 4 | `getByText` | Matches visible text; intuitive |
| 5 | `getByTestId` | Explicit test hook; decoupled from UI |
| 6 | CSS selector | Tied to structure/styling; less stable |
| 7 | XPath | Fragile; use only as last resort |

---

## 2. Role-Based Selectors

The recommended default. Based on ARIA roles, which reflect the semantic purpose of elements.

### `getByRole`

```typescript
// Buttons
page.getByRole('button', { name: 'Submit' });
page.getByRole('button', { name: /submit/i });  // Case-insensitive regex

// Links
page.getByRole('link', { name: 'Home' });

// Headings
page.getByRole('heading', { name: 'Dashboard' });
page.getByRole('heading', { level: 1 });  // <h1> specifically

// Form elements
page.getByRole('textbox', { name: 'Email' });
page.getByRole('checkbox', { name: 'Remember me' });
page.getByRole('radio', { name: 'Monthly' });
page.getByRole('combobox', { name: 'Country' });
page.getByRole('spinbutton', { name: 'Quantity' });
page.getByRole('slider', { name: 'Volume' });

// Navigation
page.getByRole('navigation', { name: 'Main' });
page.getByRole('menuitem', { name: 'Settings' });

// Tables
page.getByRole('table');
page.getByRole('row', { name: 'Alice' });
page.getByRole('cell', { name: '42' });

// Dialogs
page.getByRole('dialog', { name: 'Confirm deletion' });
page.getByRole('alertdialog');

// Tabs
page.getByRole('tab', { name: 'Profile' });
page.getByRole('tabpanel');

// Lists
page.getByRole('list');
page.getByRole('listitem');

// State-based filtering
page.getByRole('checkbox', { checked: true });
page.getByRole('button', { disabled: true });
page.getByRole('tab', { selected: true });
page.getByRole('option', { selected: true });
page.getByRole('treeitem', { expanded: true });
```

### Common ARIA Roles Reference

| HTML Element | Default Role | Notes |
|-------------|-------------|-------|
| `<button>` | `button` | |
| `<a href>` | `link` | Must have `href` |
| `<input type="text">` | `textbox` | |
| `<input type="checkbox">` | `checkbox` | |
| `<input type="radio">` | `radio` | |
| `<select>` | `combobox` | |
| `<textarea>` | `textbox` | |
| `<h1>`-`<h6>` | `heading` | Use `level` option |
| `<nav>` | `navigation` | |
| `<table>` | `table` | |
| `<tr>` | `row` | |
| `<td>` | `cell` | |
| `<img>` | `img` | |
| `<dialog>` | `dialog` | |
| `<ul>`, `<ol>` | `list` | |
| `<li>` | `listitem` | |

---

## 3. Text-Based Selectors

### `getByText`

Matches visible text content. Good for static text, labels, and messages.

```typescript
// Exact match
page.getByText('Welcome back');

// Substring match (default behavior)
page.getByText('Welcome');

// Exact match only
page.getByText('Welcome back', { exact: true });

// Regex for flexible matching
page.getByText(/welcome back/i);
page.getByText(/total: \$\d+/);

// Avoid matching hidden text
// getByText only matches visible text by default
```

### `getByAltText`

For images:

```typescript
page.getByAltText('Company logo');
page.getByAltText(/profile photo/i);
```

### `getByTitle`

For elements with `title` attribute:

```typescript
page.getByTitle('Close dialog');
```

---

## 4. Test ID Selectors

Dedicated data attributes for testing. Use when semantic selectors are not feasible.

### Setup

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    testIdAttribute: 'data-testid', // Default; can customize
  },
});
```

### Usage

```html
<!-- In your component -->
<div data-testid="user-profile-card">
  <span data-testid="user-name">Alice</span>
</div>
```

```typescript
// In your test
page.getByTestId('user-profile-card');
page.getByTestId('user-name');

// Regex matching
page.getByTestId(/user-/);
```

### When to Use Test IDs

- Complex components where role/text selectors are ambiguous
- Dynamic lists where items lack unique visible text
- Third-party components where you cannot control ARIA attributes
- Canvas or non-standard UI elements

### When NOT to Use Test IDs

- When a role-based selector works cleanly
- For standard form controls (use `getByLabel` or `getByRole`)
- For buttons and links with clear text (use `getByRole`)

---

## 5. Label-Based Selectors

### `getByLabel`

Finds form controls by their associated `<label>`.

```typescript
// <label for="email">Email address</label><input id="email" />
page.getByLabel('Email address');

// <label>Username <input /></label>
page.getByLabel('Username');

// aria-label
// <input aria-label="Search" />
page.getByLabel('Search');

// aria-labelledby
// <span id="price-label">Price</span><input aria-labelledby="price-label" />
page.getByLabel('Price');
```

### `getByPlaceholder`

```typescript
// <input placeholder="Enter your email" />
page.getByPlaceholder('Enter your email');
page.getByPlaceholder(/email/i);
```

---

## 6. CSS Selectors

Use when Playwright's built-in locators do not suffice. Less stable than semantic selectors.

```typescript
// By class
page.locator('.card-header');

// By ID
page.locator('#main-content');

// By attribute
page.locator('[data-status="active"]');
page.locator('input[type="file"]');

// Combinators
page.locator('.sidebar > .nav-item');         // Direct child
page.locator('.card .card-title');            // Descendant
page.locator('.item + .item');                // Adjacent sibling
page.locator('.tab:first-child');             // Pseudo-class

// Multiple conditions
page.locator('button.primary[disabled]');

// Playwright CSS extensions
page.locator(':visible');                     // Only visible elements
page.locator('button:has-text("Save")');      // Button containing text
page.locator('div:has(> img)');               // Div with direct img child
page.locator(':text("exact text")');          // Text matching
page.locator(':text-is("exact")');            // Exact text
page.locator(':text-matches("[A-Z]+")');      // Regex text
```

---

## 7. XPath Selectors

Avoid XPath unless absolutely necessary. XPath selectors are fragile and hard to maintain.

```typescript
// Prefix with xpath= to use XPath
page.locator('xpath=//button[@type="submit"]');
page.locator('xpath=//div[contains(@class, "modal")]//button');

// When XPath might be needed:
// - Selecting elements by complex text patterns
// - Navigating upward in the DOM (parent selection)
// - Legacy applications with no accessible markup
```

**Why to avoid XPath**:
- Breaks when DOM structure changes
- Harder to read and maintain than CSS
- No auto-completion in editors
- Performance can be worse in some browsers

---

## 8. Chaining and Filtering

### Chaining Locators

Narrow down selections by chaining `.locator()`:

```typescript
// Find a button inside a specific section
page.getByRole('region', { name: 'Sidebar' })
    .getByRole('button', { name: 'Settings' });

// Find text inside a specific card
page.locator('.user-card')
    .getByText('Alice');

// Nested role-based selection
page.getByRole('table')
    .getByRole('row', { name: 'Alice' })
    .getByRole('button', { name: 'Edit' });
```

### Filtering

```typescript
// Filter by text
page.getByRole('listitem')
    .filter({ hasText: 'JavaScript' });

// Filter by NOT having text
page.getByRole('listitem')
    .filter({ hasNotText: 'Deprecated' });

// Filter by child locator
page.getByRole('listitem')
    .filter({ has: page.getByRole('button', { name: 'Delete' }) });

// Filter by NOT having a child
page.getByRole('listitem')
    .filter({ hasNot: page.getByRole('img') });

// Chain multiple filters
page.getByRole('row')
    .filter({ hasText: 'Active' })
    .filter({ has: page.getByRole('button', { name: 'Edit' }) });
```

### `and` / `or` Combinators

```typescript
// Match elements that satisfy BOTH locators
const saveButton = page.getByRole('button').and(page.getByText('Save'));

// Match elements that satisfy EITHER locator
const actionButton = page.getByRole('button', { name: 'Save' })
    .or(page.getByRole('button', { name: 'Update' }));
```

---

## 9. Nth and Positional Selectors

```typescript
// First matching element
page.getByRole('listitem').first();

// Last matching element
page.getByRole('listitem').last();

// Nth element (0-indexed)
page.getByRole('listitem').nth(2);  // Third item

// Count elements
const count = await page.getByRole('listitem').count();
```

**Caution**: Positional selectors are fragile. Prefer filtering by text or attributes when possible.

```typescript
// BAD: relies on position
page.locator('tr').nth(3).locator('td').nth(1);

// GOOD: filter by content
page.getByRole('row', { name: 'Alice' }).getByRole('cell').nth(1);
```

---

## 10. Frame Handling

### iframes

```typescript
// By name or URL
const frame = page.frameLocator('iframe[name="editor"]');
frame.getByRole('textbox').fill('Hello');

// By index
const firstFrame = page.frameLocator('iframe').first();

// Nested frames
page.frameLocator('#outer').frameLocator('#inner').getByRole('button');

// Frame locators support all locator methods
const editorFrame = page.frameLocator('#editor-frame');
await editorFrame.getByRole('button', { name: 'Bold' }).click();
await editorFrame.getByRole('textbox').fill('Content');
```

### Named Frames

```typescript
// <iframe name="payment-form" src="..."></iframe>
const paymentFrame = page.frameLocator('iframe[name="payment-form"]');
await paymentFrame.getByLabel('Card number').fill('4242424242424242');
```

---

## 11. Shadow DOM

Playwright pierces shadow DOM by default for CSS selectors and built-in locators.

```typescript
// Automatically pierces shadow roots
page.getByRole('button', { name: 'Shadow Button' });  // Works
page.locator('custom-element button');                  // Pierces shadow DOM

// Explicit shadow DOM handling if needed
page.locator('custom-element').locator('internal-part');
```

For web components:

```typescript
// <my-component>
//   #shadow-root
//     <button>Click me</button>
// </my-component>

// All of these work:
page.getByRole('button', { name: 'Click me' });
page.locator('my-component button');
page.locator('my-component').getByRole('button');
```

---

## 12. Best Practices

### Selector Stability Checklist

1. **Does it match user intent?** Use role-based selectors that describe what the element IS, not how it looks.
2. **Is it resilient to refactoring?** Avoid selectors tied to CSS classes, DOM structure, or implementation details.
3. **Is it unique?** Use Playwright's strict mode (default) -- it fails if a locator matches multiple elements.
4. **Is it readable?** Future you should understand what element is being targeted.

### Naming Conventions for Test IDs

```
data-testid="<component>-<element>[-<qualifier>]"

Examples:
  data-testid="user-card-name"
  data-testid="nav-link-home"
  data-testid="modal-close-button"
  data-testid="order-row-123"
```

### Debugging Selectors

```bash
# Use Playwright Inspector to find selectors interactively
npx playwright test --debug

# Use codegen to generate selectors by clicking
npx playwright codegen http://localhost:3000

# Highlight elements matching a selector in headed mode
npx playwright test --headed
```

```typescript
// In code: highlight to debug
await page.getByRole('button', { name: 'Submit' }).highlight();
```

### Assertion Patterns

```typescript
// Visibility
await expect(page.getByText('Success')).toBeVisible();
await expect(page.getByText('Loading')).toBeHidden();

// Content
await expect(page.getByRole('heading')).toHaveText('Dashboard');
await expect(page.getByRole('textbox')).toHaveValue('hello@example.com');

// Count
await expect(page.getByRole('listitem')).toHaveCount(5);

// Attributes
await expect(page.getByRole('button')).toBeEnabled();
await expect(page.getByRole('button')).toBeDisabled();
await expect(page.getByRole('checkbox')).toBeChecked();

// URL
await expect(page).toHaveURL(/\/dashboard/);
await expect(page).toHaveTitle('Dashboard - MyApp');
```

### Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| `page.locator('.btn-primary')` | Class names change | `page.getByRole('button', { name: '...' })` |
| `page.locator('#root > div > div:nth-child(3) > button')` | Extremely fragile | Add test IDs or use role selectors |
| `page.locator('text=Submit')` | Legacy syntax | `page.getByText('Submit')` or `page.getByRole('button', { name: 'Submit' })` |
| `page.waitForSelector('.loaded')` | Legacy API | `await expect(locator).toBeVisible()` |
| Using `$` and `$$` | ElementHandle API is legacy | Use Locator API |
