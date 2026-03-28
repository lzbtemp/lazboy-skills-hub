# E2E Test Patterns with Playwright

Proven patterns for building maintainable, reliable end-to-end test suites with Playwright.

---

## Table of Contents

1. [Page Object Model](#1-page-object-model)
2. [Test Data Factories](#2-test-data-factories)
3. [Authentication Handling](#3-authentication-handling)
4. [API Seeding Before UI Tests](#4-api-seeding-before-ui-tests)
5. [Visual Regression Testing](#5-visual-regression-testing)
6. [Network Mocking](#6-network-mocking)
7. [Parallel Execution](#7-parallel-execution)
8. [Retry Strategies](#8-retry-strategies)
9. [Test Tagging and Filtering](#9-test-tagging-and-filtering)
10. [Anti-Patterns to Avoid](#10-anti-patterns-to-avoid)

---

## 1. Page Object Model

Encapsulate page structure and interactions in dedicated classes. Tests read like user stories; implementation details stay in page objects.

### Structure

```
tests/
  pages/
    base.page.ts          # Shared page behavior
    login.page.ts
    dashboard.page.ts
    settings.page.ts
  fixtures/
    pages.fixture.ts      # Register page objects as fixtures
  specs/
    login.spec.ts
    dashboard.spec.ts
```

### Base Page

```typescript
// tests/pages/base.page.ts
import { type Locator, type Page } from '@playwright/test';

export abstract class BasePage {
  readonly page: Page;
  readonly heading: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1 });
  }

  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  async getTitle(): Promise<string> {
    return this.page.title();
  }

  async screenshot(name: string): Promise<Buffer> {
    return this.page.screenshot({ fullPage: true, path: `screenshots/${name}.png` });
  }
}
```

### Concrete Page Object

```typescript
// tests/pages/login.page.ts
import { type Locator, type Page, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class LoginPage extends BasePage {
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
    this.errorMessage = page.getByRole('alert');
  }

  async goto(): Promise<void> {
    await this.page.goto('/login');
  }

  async login(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectError(message: string): Promise<void> {
    await expect(this.errorMessage).toContainText(message);
  }

  async expectLoggedIn(): Promise<void> {
    await expect(this.page).toHaveURL(/\/dashboard/);
  }
}
```

### Page Object Fixture

```typescript
// tests/fixtures/pages.fixture.ts
import { test as base } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { DashboardPage } from '../pages/dashboard.page';

type PageFixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
};

export const test = base.extend<PageFixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
});

export { expect } from '@playwright/test';
```

### Test Using Page Objects

```typescript
// tests/specs/login.spec.ts
import { test, expect } from '../fixtures/pages.fixture';

test.describe('Login', () => {
  test('successful login redirects to dashboard', async ({ loginPage }) => {
    await loginPage.goto();
    await loginPage.login('user@example.com', 'password123');
    await loginPage.expectLoggedIn();
  });

  test('invalid credentials show error', async ({ loginPage }) => {
    await loginPage.goto();
    await loginPage.login('user@example.com', 'wrong');
    await loginPage.expectError('Invalid credentials');
  });
});
```

**Key principles**:
- Page objects expose **behaviors**, not locators directly
- Assertions live in tests, not in page objects (except convenience methods like `expectLoggedIn`)
- Page objects never reference other page objects -- composition happens in tests or fixtures
- Keep page objects focused: one class per page or major component

---

## 2. Test Data Factories

Generate consistent, isolated test data without hardcoding values.

```typescript
// tests/factories/user.factory.ts
import { randomUUID } from 'crypto';

interface UserData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  role: 'admin' | 'user' | 'viewer';
}

export function createUser(overrides: Partial<UserData> = {}): UserData {
  const id = randomUUID().slice(0, 8);
  return {
    email: `test-${id}@example.com`,
    password: 'TestPass123!',
    firstName: `First${id}`,
    lastName: `Last${id}`,
    role: 'user',
    ...overrides,
  };
}

export function createAdminUser(overrides: Partial<UserData> = {}): UserData {
  return createUser({ role: 'admin', ...overrides });
}
```

```typescript
// tests/factories/order.factory.ts
interface OrderData {
  productId: string;
  quantity: number;
  status: 'pending' | 'shipped' | 'delivered';
}

export function createOrder(overrides: Partial<OrderData> = {}): OrderData {
  return {
    productId: `prod-${Date.now()}`,
    quantity: 1,
    status: 'pending',
    ...overrides,
  };
}
```

**Usage in tests**:

```typescript
test('user can place an order', async ({ page }) => {
  const user = createUser();
  const order = createOrder({ quantity: 3 });
  // Seed via API, then test UI...
});
```

---

## 3. Authentication Handling

Reuse authentication state across tests to avoid logging in for every test.

### Storage State (Recommended)

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  projects: [
    // Setup project: runs first and saves auth state
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
});
```

```typescript
// tests/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate as standard user', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('user@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign in' }).click();

  // Wait for auth to complete
  await page.waitForURL('/dashboard');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  // Save signed-in state
  await page.context().storageState({ path: authFile });
});
```

### Multiple Roles

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'admin-tests',
      use: { storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
      testMatch: /.*admin.*\.spec\.ts/,
    },
    {
      name: 'user-tests',
      use: { storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
      testMatch: /.*user.*\.spec\.ts/,
    },
  ],
});
```

### API-Based Auth (Faster)

```typescript
// tests/auth.setup.ts
setup('authenticate via API', async ({ request }) => {
  const response = await request.post('/api/auth/login', {
    data: { email: 'user@example.com', password: 'password123' },
  });
  expect(response.ok()).toBeTruthy();

  // The response sets cookies; save the state
  await request.storageState({ path: 'playwright/.auth/user.json' });
});
```

---

## 4. API Seeding Before UI Tests

Create test data via API before running UI tests. This is faster and more reliable than creating data through the UI.

```typescript
// tests/fixtures/api.fixture.ts
import { test as base, type APIRequestContext } from '@playwright/test';

type ApiFixtures = {
  apiContext: APIRequestContext;
  seedUser: (data: any) => Promise<{ id: string }>;
  seedProduct: (data: any) => Promise<{ id: string }>;
};

export const test = base.extend<ApiFixtures>({
  apiContext: async ({ playwright }, use) => {
    const context = await playwright.request.newContext({
      baseURL: process.env.API_URL || 'http://localhost:3000',
      extraHTTPHeaders: {
        Authorization: `Bearer ${process.env.API_TOKEN}`,
      },
    });
    await use(context);
    await context.dispose();
  },

  seedUser: async ({ apiContext }, use) => {
    const createdIds: string[] = [];

    const seed = async (data: any) => {
      const response = await apiContext.post('/api/users', { data });
      const body = await response.json();
      createdIds.push(body.id);
      return body;
    };

    await use(seed);

    // Cleanup: delete created users after test
    for (const id of createdIds) {
      await apiContext.delete(`/api/users/${id}`);
    }
  },

  seedProduct: async ({ apiContext }, use) => {
    const createdIds: string[] = [];

    const seed = async (data: any) => {
      const response = await apiContext.post('/api/products', { data });
      const body = await response.json();
      createdIds.push(body.id);
      return body;
    };

    await use(seed);

    for (const id of createdIds) {
      await apiContext.delete(`/api/products/${id}`);
    }
  },
});
```

```typescript
// tests/specs/checkout.spec.ts
import { test, expect } from '../fixtures/api.fixture';

test('user can add product to cart and checkout', async ({ page, seedProduct }) => {
  // Seed data via API
  const product = await seedProduct({
    name: 'Test Widget',
    price: 29.99,
    stock: 100,
  });

  // Now test the UI with known data
  await page.goto(`/products/${product.id}`);
  await page.getByRole('button', { name: 'Add to cart' }).click();
  await page.goto('/cart');
  await expect(page.getByText('Test Widget')).toBeVisible();
});
```

---

## 5. Visual Regression Testing

Detect unintended visual changes by comparing screenshots.

```typescript
// tests/specs/visual.spec.ts
import { test, expect } from '@playwright/test';

test('homepage visual regression', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // Full page screenshot comparison
  await expect(page).toHaveScreenshot('homepage.png', {
    maxDiffPixelRatio: 0.01,  // Allow 1% pixel difference
    animations: 'disabled',    // Freeze animations
  });
});

test('component visual regression', async ({ page }) => {
  await page.goto('/components/button');

  // Screenshot of a specific element
  const button = page.getByRole('button', { name: 'Primary' });
  await expect(button).toHaveScreenshot('primary-button.png');
});

// Mask dynamic content
test('dashboard with masked dynamic content', async ({ page }) => {
  await page.goto('/dashboard');

  await expect(page).toHaveScreenshot('dashboard.png', {
    mask: [
      page.getByTestId('current-time'),
      page.getByTestId('user-avatar'),
    ],
  });
});
```

**Configuration**:

```typescript
// playwright.config.ts
export default defineConfig({
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      animations: 'disabled',
      caret: 'hide',
    },
  },
  updateSnapshots: process.env.UPDATE_SNAPSHOTS === 'true' ? 'all' : 'missing',
});
```

**Best practices**:
- Set a consistent viewport size for visual tests
- Disable animations to avoid flaky comparisons
- Mask dynamic content (timestamps, avatars, ads)
- Use `--update-snapshots` intentionally, not routinely
- Review snapshot changes in code review (store in version control)

---

## 6. Network Mocking

Intercept and mock network requests for deterministic tests.

### Mock API Responses

```typescript
test('displays user list from API', async ({ page }) => {
  // Mock the API response before navigating
  await page.route('**/api/users', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 1, name: 'Alice', email: 'alice@example.com' },
        { id: 2, name: 'Bob', email: 'bob@example.com' },
      ]),
    })
  );

  await page.goto('/users');
  await expect(page.getByText('Alice')).toBeVisible();
  await expect(page.getByText('Bob')).toBeVisible();
});
```

### Simulate Error States

```typescript
test('shows error when API fails', async ({ page }) => {
  await page.route('**/api/users', (route) =>
    route.fulfill({ status: 500, body: 'Internal Server Error' })
  );

  await page.goto('/users');
  await expect(page.getByText('Something went wrong')).toBeVisible();
});
```

### Simulate Slow Responses

```typescript
test('shows loading indicator for slow API', async ({ page }) => {
  await page.route('**/api/data', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto('/data');
  await expect(page.getByRole('progressbar')).toBeVisible();
});
```

### Intercept and Modify

```typescript
test('modify API response on the fly', async ({ page }) => {
  await page.route('**/api/settings', async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.featureFlag = true;  // Override a specific field
    await route.fulfill({ response, json });
  });

  await page.goto('/settings');
});
```

### HAR File Replay

```bash
# Record network traffic
npx playwright open --save-har=tests/mocks/api.har http://localhost:3000

# Use in tests
```

```typescript
test('replay from HAR file', async ({ page }) => {
  await page.routeFromHAR('tests/mocks/api.har', {
    url: '**/api/**',
    update: false,
  });

  await page.goto('/');
});
```

---

## 7. Parallel Execution

Playwright runs test files in parallel by default. Each file gets its own worker process.

### Configuration

```typescript
// playwright.config.ts
export default defineConfig({
  // Number of parallel worker processes
  workers: process.env.CI ? 2 : undefined, // undefined = half CPU cores

  // Run tests within a file serially (default) or in parallel
  fullyParallel: true, // Each test gets its own worker

  // Limit failures before stopping
  maxFailures: process.env.CI ? 10 : 0,
});
```

### Test Isolation

Each test gets a fresh browser context by default, ensuring isolation.

```typescript
// Tests in this file run serially (use when tests share state)
test.describe.serial('Checkout flow', () => {
  test('add to cart', async ({ page }) => { /* ... */ });
  test('enter shipping', async ({ page }) => { /* ... */ });
  test('complete payment', async ({ page }) => { /* ... */ });
});
```

### Sharding (CI)

Split tests across multiple CI machines:

```bash
# Machine 1
npx playwright test --shard=1/4

# Machine 2
npx playwright test --shard=2/4

# Machine 3
npx playwright test --shard=3/4

# Machine 4
npx playwright test --shard=4/4
```

---

## 8. Retry Strategies

Handle flaky tests without masking real failures.

```typescript
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 2 : 0, // Retry only in CI

  // Per-project retry configuration
  projects: [
    {
      name: 'stable-tests',
      testMatch: /.*\.spec\.ts/,
      retries: 0,
    },
    {
      name: 'flaky-tests',
      testMatch: /.*\.flaky\.spec\.ts/,
      retries: 3,
    },
  ],
});
```

### Built-in Waiting

Playwright auto-waits for elements to be actionable. Avoid manual `waitForTimeout`:

```typescript
// BAD: arbitrary sleep
await page.waitForTimeout(2000);
await page.click('#submit');

// GOOD: Playwright auto-waits
await page.getByRole('button', { name: 'Submit' }).click();

// GOOD: explicit wait for a condition
await page.waitForResponse('**/api/submit');
await expect(page.getByText('Success')).toBeVisible();
```

### Custom Retry Logic for Setup

```typescript
async function waitForService(url: string, maxRetries = 30): Promise<void> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Service not ready yet
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`Service at ${url} not available after ${maxRetries} retries`);
}
```

---

## 9. Test Tagging and Filtering

Organize tests with tags for selective execution.

### Tagging Tests

```typescript
// Tag individual tests
test('user login @smoke @auth', async ({ page }) => { /* ... */ });
test('password reset @auth', async ({ page }) => { /* ... */ });
test('complex report generation @slow', async ({ page }) => { /* ... */ });

// Tag a group
test.describe('Payment @payment @critical', () => {
  test('credit card checkout', async ({ page }) => { /* ... */ });
  test('refund processing', async ({ page }) => { /* ... */ });
});
```

### Running by Tag

```bash
# Run only smoke tests
npx playwright test --grep @smoke

# Run all auth tests
npx playwright test --grep @auth

# Exclude slow tests
npx playwright test --grep-invert @slow

# Combine: smoke tests that are NOT slow
npx playwright test --grep "@smoke" --grep-invert "@slow"
```

### Annotations

```typescript
test('feature behind flag @skip', async ({ page }) => {
  test.skip(process.env.FEATURE_FLAG !== 'true', 'Feature flag disabled');
  // ...
});

test('slow data export @slow', async ({ page }) => {
  test.slow(); // Triples the timeout
  // ...
});

test.fixme('broken after API change', async ({ page }) => {
  // Known broken -- skip but track
});
```

---

## 10. Anti-Patterns to Avoid

| Anti-Pattern | Problem | Better Approach |
|-------------|---------|-----------------|
| `page.waitForTimeout(N)` | Arbitrary, slow, flaky | Use auto-wait, `waitForResponse`, or `expect().toBeVisible()` |
| Testing implementation details | Brittle, breaks on refactor | Test user-visible behavior |
| Shared mutable state between tests | Order-dependent, flaky | Each test sets up its own data |
| Long, linear test flows | Hard to debug, slow feedback | Break into focused, independent tests |
| Hardcoded test data | Collisions in parallel runs | Use factories with unique IDs |
| Logging in via UI for every test | Slow | Use storage state reuse |
| `page.evaluate` for everything | Bypasses real user interactions | Use Playwright's locator API |
| Overly broad selectors | Match wrong elements | Use role-based and test-ID selectors |
| No cleanup after tests | Data leaks across tests | Use fixtures with teardown or API cleanup |
| Testing third-party services | Slow, unreliable, outside your control | Mock external dependencies |
