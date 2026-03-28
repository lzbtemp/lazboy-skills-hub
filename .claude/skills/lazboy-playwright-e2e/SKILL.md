---
name: lazboy-playwright-e2e
description: "Write end-to-end tests for La-Z-Boy web applications using Playwright. Covers test patterns, page object models, CI integration, visual regression testing, and test data management. Use when writing E2E tests or setting up test automation."
version: "1.0.0"
category: QA/Testing
tags: [testing, qa, playwright, e2e, automation]
---

# La-Z-Boy Playwright E2E Testing Skill

Standards for writing reliable end-to-end tests at La-Z-Boy.

**Reference files — load when needed:**
- `references/test-patterns.md` — approved E2E test patterns
- `references/selectors-guide.md` — selector strategy and data-testid conventions

**Scripts — run when needed:**
- `scripts/generate_test.py` — scaffold a new E2E test from a user story
- `scripts/setup_playwright.py` — configure Playwright for a project

---

## 1. Project Setup

```bash
npm init playwright@latest
```

### Config (`playwright.config.ts`)
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html'], ['junit', { outputFile: 'test-results.xml' }]],
  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
```

## 2. Page Object Model

```typescript
// e2e/pages/SkillsPage.ts
import { Page, Locator } from '@playwright/test';

export class SkillsPage {
  readonly page: Page;
  readonly searchInput: Locator;
  readonly skillCards: Locator;
  readonly categoryFilter: Locator;

  constructor(page: Page) {
    this.page = page;
    this.searchInput = page.getByPlaceholder('Search skills...');
    this.skillCards = page.getByTestId('skill-card');
    this.categoryFilter = page.getByTestId('category-filter');
  }

  async goto() {
    await this.page.goto('/browse');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForResponse('**/api/**');
  }

  async selectCategory(name: string) {
    await this.categoryFilter.getByText(name).click();
  }

  async getSkillCount(): Promise<number> {
    return this.skillCards.count();
  }
}
```

## 3. Test Patterns

### User Flow Test
```typescript
import { test, expect } from '@playwright/test';
import { SkillsPage } from './pages/SkillsPage';

test.describe('Skills Browse', () => {
  test('user can search and find a skill', async ({ page }) => {
    const skills = new SkillsPage(page);
    await skills.goto();

    await skills.search('react');
    const count = await skills.getSkillCount();
    expect(count).toBeGreaterThan(0);

    await skills.skillCards.first().click();
    await expect(page).toHaveURL(/\/skills\//);
    await expect(page.getByTestId('skill-title')).toBeVisible();
  });
});
```

## 4. Selector Strategy

Priority order:
1. `getByRole()` — most accessible
2. `getByText()` — user-visible text
3. `getByPlaceholder()` — form inputs
4. `getByTestId()` — fallback with `data-testid`

**Never use**: CSS selectors, XPath, or `nth-child`

## 5. CI Integration

```yaml
# In GitHub Actions
- name: Run E2E Tests
  run: npx playwright test
  env:
    BASE_URL: http://localhost:5173
- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: playwright-report
    path: playwright-report/
```

## 6. Test Coverage Targets

| Area | Coverage |
|---|---|
| Critical user flows | 100% |
| Authentication | 100% |
| CRUD operations | 100% |
| Error states | 80% |
| Edge cases | 60% |
