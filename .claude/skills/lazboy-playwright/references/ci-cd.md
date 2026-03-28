# CI/CD, Reporting, and Trace Viewer

Read this when setting up Playwright in GitHub Actions, configuring parallel sharding, or debugging a failing test with Trace Viewer.

---

## Table of Contents
1. [GitHub Actions Setup](#1-github-actions-setup)
2. [Parallel Sharding](#2-parallel-sharding)
3. [Trace Viewer Workflow](#3-trace-viewer-workflow)
4. [HTML Reporter](#4-html-reporter)
5. [Required Environment Variables](#5-required-environment-variables)

---

## 1. GitHub Actions Setup

```yaml
# .github/workflows/playwright.yml
name: Playwright Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    name: "Playwright Tests (Shard ${{ matrix.shardIndex }}/${{ matrix.shardTotal }})"
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        shardIndex: [1, 2, 3, 4]
        shardTotal: [4]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Run Playwright tests
        run: npx playwright test --shard=${{ matrix.shardIndex }}/${{ matrix.shardTotal }}
        env:
          BASE_URL: ${{ vars.STAGING_URL }}
          TEST_CUSTOMER_EMAIL: ${{ secrets.TEST_CUSTOMER_EMAIL }}
          TEST_CUSTOMER_PASSWORD: ${{ secrets.TEST_CUSTOMER_PASSWORD }}
          TEST_ADMIN_EMAIL: ${{ secrets.TEST_ADMIN_EMAIL }}
          TEST_ADMIN_PASSWORD: ${{ secrets.TEST_ADMIN_PASSWORD }}
          TEST_API_TOKEN: ${{ secrets.TEST_API_TOKEN }}

      - name: Upload shard report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-shard-${{ matrix.shardIndex }}
          path: playwright-report/
          retention-days: 14

      - name: Upload traces on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-traces-shard-${{ matrix.shardIndex }}
          path: test-results/
          retention-days: 7

  merge-reports:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - run: npm ci
      - name: Download all reports
        uses: actions/download-artifact@v4
        with:
          path: all-reports
          pattern: playwright-report-shard-*
      - name: Merge reports
        run: npx playwright merge-reports --reporter html ./all-reports
      - name: Upload merged report
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-merged
          path: playwright-report/
          retention-days: 30
```

---

## 2. Parallel Sharding

Sharding splits the test suite across parallel workers, reducing total CI time by the shard count.

```bash
# Run locally with 2 shards (useful for debugging sharding behavior)
npx playwright test --shard=1/2
npx playwright test --shard=2/2
```

Set shard count based on suite size:
- < 50 tests: no sharding needed
- 50–200 tests: 2–4 shards
- > 200 tests: 4–8 shards

Tests within a shard still run in parallel per the `workers` setting in config.

---

## 3. Trace Viewer Workflow

The Trace Viewer is Playwright's most powerful debugging tool. It records every action, network request, console log, and screenshot in a timeline you can replay.

### Enable tracing

In `playwright.config.ts`:
```typescript
use: {
  trace: "retain-on-failure",  // Only save traces for failed tests (saves disk space)
  screenshot: "only-on-failure",
  video: "retain-on-failure",
}
```

Options:
- `"on"` — always trace (expensive, use during local debugging)
- `"retain-on-failure"` — trace everything, discard on pass (recommended for CI)
- `"on-first-retry"` — trace only on retries (useful for investigating flakes)

### Open a trace

```bash
# After a test failure, the trace is in test-results/
npx playwright show-trace test-results/checkout-test-failed/trace.zip
```

### What to look for in the Trace Viewer

1. **Timeline** — each test action with duration; long gaps indicate slow network or missed waits
2. **DOM snapshots** — see exactly what the page looked like at each step
3. **Network panel** — check for 4xx/5xx responses during the test
4. **Console panel** — JavaScript errors that didn't fail the test but indicate problems
5. **Source panel** — which line of test code triggered each action

### Common failure patterns in traces

| What you see | Likely cause |
|---|---|
| Selector times out immediately | Element never rendered; check network tab for missing API response |
| Action succeeds but assertion fails | React state update async; add `waitForLoadState` or rely on `expect` retry |
| 401/403 in network tab | Auth state expired; check `storageState` setup |
| `networkidle` never fires | Page has polling/websocket traffic; use `waitForURL` or `waitForSelector` instead |

---

## 4. HTML Reporter

Playwright's built-in HTML reporter gives you a searchable test results page with screenshots and trace links.

```typescript
// playwright.config.ts
reporter: [
  ["html", { open: "never", outputFolder: "playwright-report" }],
  ["list"],  // also show results in terminal
],
```

Open locally after a test run:
```bash
npx playwright show-report
```

The HTML report is self-contained — upload the `playwright-report/` folder to any static host (S3, GitHub Pages, Netlify) to share results with the team.

---

## 5. Required Environment Variables

Document these in your project `.env.example` file — never commit actual values.

```bash
# .env.example
BASE_URL=http://localhost:3000          # Override in CI to staging URL

# Test credentials — create dedicated test accounts, not real accounts
TEST_CUSTOMER_EMAIL=customer@test.lazboy.com
TEST_CUSTOMER_PASSWORD=change-me
TEST_ADMIN_EMAIL=admin@test.lazboy.com
TEST_ADMIN_PASSWORD=change-me
TEST_API_TOKEN=your-test-api-token      # For API seeding in tests

# Optional — for agent-specific header injection
PW_AUTOMATED_BY=playwright-lazboy
```

Set `BASE_URL` and all `TEST_*` secrets as GitHub Actions Secrets (never as plain vars).
