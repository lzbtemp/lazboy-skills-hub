/**
 * La-Z-Boy Standard Playwright Configuration
 * Copy this file to the root of your test project and adjust as needed.
 * See https://playwright.dev/docs/test-configuration
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  // Test directory
  testDir: "./tests",

  // Run tests in parallel (set lower if tests share state)
  workers: process.env.CI ? 2 : 4,

  // Retry failed tests once in CI to reduce flakiness noise
  retries: process.env.CI ? 1 : 0,

  // Fail the suite if too many tests fail (catches cascading failures)
  maxFailures: process.env.CI ? 10 : undefined,

  // Timeout for each individual test (30s default; increase for checkout flows)
  timeout: 30_000,

  // Timeout for expect() assertions (default 5s — enough for most dynamic content)
  expect: {
    timeout: 5_000,
  },

  // Reporter: HTML for artifacts + list for terminal output
  reporter: [
    ["html", { open: "never", outputFolder: "playwright-report" }],
    ["list"],
  ],

  use: {
    // All test files use this base URL; override with BASE_URL env var in CI
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",

    // Collect trace on first retry (captures failures without overhead on green tests)
    trace: "on-first-retry",

    // Screenshot and video only when tests fail (saves disk space)
    screenshot: "only-on-failure",
    video: "retain-on-failure",

    // Inject La-Z-Boy test identifier into all requests
    extraHTTPHeaders: {
      "X-Automated-By": "playwright-lazboy",
      "X-Test-Run": process.env.CI ? "ci" : "local",
    },

    // Reasonable viewport — matches the most common internal screen size
    viewport: { width: 1440, height: 900 },

    // Locale and timezone matching La-Z-Boy's primary market
    locale: "en-US",
    timezoneId: "America/Detroit",  // La-Z-Boy HQ timezone
  },

  // Project matrix — desktop + mobile coverage
  projects: [
    // Setup project: runs global-setup.ts to create auth state files
    {
      name: "setup",
      testMatch: /global-setup\.ts/,
    },

    // Desktop Chrome (primary)
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
    },

    // Mobile Safari (high-traffic mobile segment)
    {
      name: "mobile-safari",
      use: { ...devices["iPhone 14"] },
      dependencies: ["setup"],
    },

    // Tablet (for product configurator — heavily used on iPad)
    {
      name: "tablet",
      use: { ...devices["iPad Pro 11"] },
      dependencies: ["setup"],
    },

    // Accessibility audit project — runs @a11y tagged tests
    // Uncomment when @axe-core/playwright is installed
    // {
    //   name: "accessibility",
    //   use: { ...devices["Desktop Chrome"] },
    //   grep: /@a11y/,
    //   dependencies: ["setup"],
    // },
  ],

  // Output directory for test artifacts (traces, screenshots, videos)
  outputDir: "test-results/",

  // Run global setup once before all tests (creates auth state)
  globalSetup: "./global-setup.ts",
});
