#!/usr/bin/env python3
"""
Playwright Project Setup Script

Sets up Playwright in a project: installs dependencies, generates configuration,
creates directory structure, and provides an example test.

Usage:
    python setup_playwright.py
    python setup_playwright.py --project-dir /path/to/project
    python setup_playwright.py --base-url http://localhost:3000
    python setup_playwright.py --browsers chromium firefox
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def check_prerequisites(project_dir: str) -> dict:
    """Check for package.json and Node.js."""
    issues = []
    info = {}

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, check=True
        )
        info["node_version"] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("Node.js is not installed. Install from https://nodejs.org/")

    # Check npm
    try:
        result = subprocess.run(
            ["npm", "--version"], capture_output=True, text=True, check=True
        )
        info["npm_version"] = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("npm is not installed.")

    # Check package.json
    package_json_path = os.path.join(project_dir, "package.json")
    if os.path.exists(package_json_path):
        info["has_package_json"] = True
        with open(package_json_path) as f:
            info["package_json"] = json.load(f)
    else:
        info["has_package_json"] = False

    info["issues"] = issues
    return info


def init_package_json(project_dir: str) -> None:
    """Initialize package.json if it doesn't exist."""
    package_json_path = os.path.join(project_dir, "package.json")
    if not os.path.exists(package_json_path):
        print("No package.json found. Initializing...")
        subprocess.run(
            ["npm", "init", "-y"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        print("Created package.json")


def install_playwright(project_dir: str) -> None:
    """Install @playwright/test as a dev dependency."""
    print("Installing @playwright/test...")
    subprocess.run(
        ["npm", "install", "--save-dev", "@playwright/test"],
        cwd=project_dir,
        check=True,
    )
    print("Installed @playwright/test")


def install_browsers(project_dir: str, browsers: list[str]) -> None:
    """Install Playwright browsers."""
    print(f"Installing browsers: {', '.join(browsers)}...")
    subprocess.run(
        ["npx", "playwright", "install", "--with-deps"] + browsers,
        cwd=project_dir,
        check=True,
    )
    print("Browsers installed")


def generate_config(
    project_dir: str,
    base_url: str,
    browsers: list[str],
    ci_mode: bool,
) -> str:
    """Generate playwright.config.ts."""
    browser_projects = []
    for browser in browsers:
        display_name = browser.capitalize()
        if browser == "chromium":
            browser_projects.append(f"""    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }}""")
        elif browser == "firefox":
            browser_projects.append(f"""    {{
      name: 'firefox',
      use: {{ ...devices['Desktop Firefox'] }},
    }}""")
        elif browser == "webkit":
            browser_projects.append(f"""    {{
      name: 'webkit',
      use: {{ ...devices['Desktop Safari'] }},
    }}""")

    projects_str = ",\n".join(browser_projects)

    config = f"""import {{ defineConfig, devices }} from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({{
  testDir: './tests',
  /* Maximum time one test can run for */
  timeout: 30_000,
  /* Expect timeout */
  expect: {{
    timeout: 5_000,
  }},
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use */
  reporter: [
    ['html', {{ open: 'never' }}],
    ['list'],
    ...(process.env.CI ? [['junit' as const, {{ outputFile: 'test-results/junit.xml' }}]] : []),
  ],
  /* Shared settings for all the projects below */
  use: {{
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: '{base_url}',
    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    /* Video on failure */
    video: 'retain-on-failure',
  }},

  /* Configure projects for major browsers */
  projects: [
{projects_str},
  ],

  /* Run your local dev server before starting the tests */
  // webServer: {{
  //   command: 'npm run dev',
  //   url: '{base_url}',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120_000,
  // }},
}});
"""
    config_path = os.path.join(project_dir, "playwright.config.ts")
    with open(config_path, "w") as f:
        f.write(config)
    print(f"Created: {config_path}")
    return config_path


def create_directory_structure(project_dir: str) -> list[str]:
    """Create test directory structure."""
    dirs = [
        "tests/specs",
        "tests/pages",
        "tests/fixtures",
        "tests/factories",
        "tests/mocks",
        "playwright/.auth",
    ]
    created = []
    for d in dirs:
        full_path = os.path.join(project_dir, d)
        os.makedirs(full_path, exist_ok=True)
        created.append(full_path)
        print(f"Created directory: {d}/")

    # Create .gitkeep files for empty directories
    for d in ["tests/mocks", "playwright/.auth"]:
        gitkeep = os.path.join(project_dir, d, ".gitkeep")
        if not os.path.exists(gitkeep):
            Path(gitkeep).touch()

    return created


def create_example_page_object(project_dir: str) -> str:
    """Create an example page object."""
    content = """import { type Locator, type Page, expect } from '@playwright/test';

/**
 * Example Page Object for the home page.
 *
 * Page objects encapsulate page structure and interactions,
 * keeping tests clean and maintainable.
 */
export class HomePage {
  readonly page: Page;
  readonly heading: Locator;
  readonly navLinks: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1 });
    this.navLinks = page.getByRole('navigation').getByRole('link');
  }

  async goto(): Promise<void> {
    await this.page.goto('/');
  }

  async getHeadingText(): Promise<string> {
    return (await this.heading.textContent()) ?? '';
  }

  async getNavLinkCount(): Promise<number> {
    return this.navLinks.count();
  }
}
"""
    file_path = os.path.join(project_dir, "tests", "pages", "home.page.ts")
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Created: tests/pages/home.page.ts")
    return file_path


def create_example_test(project_dir: str) -> str:
    """Create an example test file."""
    content = """import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/home.page';

test.describe('Home Page', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.goto();
  });

  test('should have a title', async ({ page }) => {
    // Verify the page has a title
    await expect(page).toHaveTitle(/.+/);
  });

  test('should display main heading', async () => {
    // Verify the main heading is visible
    await expect(homePage.heading).toBeVisible();
  });

  test('should have navigation links', async () => {
    // Verify navigation contains at least one link
    const count = await homePage.getNavLinkCount();
    expect(count).toBeGreaterThan(0);
  });
});

// Example of a standalone test without page object
test('home page responds with 200', async ({ request }) => {
  const response = await request.get('/');
  expect(response.ok()).toBeTruthy();
});
"""
    file_path = os.path.join(project_dir, "tests", "specs", "home.spec.ts")
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Created: tests/specs/home.spec.ts")
    return file_path


def create_test_fixture(project_dir: str) -> str:
    """Create a custom test fixture file."""
    content = """import { test as base } from '@playwright/test';
import { HomePage } from '../pages/home.page';

/**
 * Custom test fixtures.
 *
 * Extend the base test to provide page objects and other
 * reusable setup to all tests.
 */
type Fixtures = {
  homePage: HomePage;
};

export const test = base.extend<Fixtures>({
  homePage: async ({ page }, use) => {
    const homePage = new HomePage(page);
    await use(homePage);
  },
});

export { expect } from '@playwright/test';
"""
    file_path = os.path.join(project_dir, "tests", "fixtures", "pages.fixture.ts")
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Created: tests/fixtures/pages.fixture.ts")
    return file_path


def create_auth_setup(project_dir: str) -> str:
    """Create authentication setup file."""
    content = """import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

/**
 * Authentication setup.
 *
 * This runs before tests that depend on authenticated state.
 * It logs in once and saves the auth state to be reused by other tests.
 *
 * Configure in playwright.config.ts:
 *   projects: [
 *     { name: 'setup', testMatch: /.*\\.setup\\.ts/ },
 *     {
 *       name: 'chromium',
 *       use: { storageState: authFile },
 *       dependencies: ['setup'],
 *     },
 *   ]
 */
setup('authenticate', async ({ page }) => {
  // Navigate to login page
  await page.goto('/login');

  // Fill in credentials
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Sign in' }).click();

  // Wait until the page receives the auth cookies
  await page.waitForURL('/dashboard');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  // Save signed-in state to file
  await page.context().storageState({ path: authFile });
});
"""
    file_path = os.path.join(project_dir, "tests", "auth.setup.ts")
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Created: tests/auth.setup.ts")
    return file_path


def add_npm_scripts(project_dir: str) -> None:
    """Add Playwright-related scripts to package.json."""
    package_json_path = os.path.join(project_dir, "package.json")
    with open(package_json_path) as f:
        package = json.load(f)

    scripts = package.get("scripts", {})
    playwright_scripts = {
        "test:e2e": "playwright test",
        "test:e2e:ui": "playwright test --ui",
        "test:e2e:headed": "playwright test --headed",
        "test:e2e:debug": "playwright test --debug",
        "test:e2e:codegen": "playwright codegen",
        "test:e2e:report": "playwright show-report",
        "test:e2e:update-snapshots": "playwright test --update-snapshots",
    }

    added = []
    for key, value in playwright_scripts.items():
        if key not in scripts:
            scripts[key] = value
            added.append(key)

    package["scripts"] = scripts
    with open(package_json_path, "w") as f:
        json.dump(package, f, indent=2)
        f.write("\n")

    if added:
        print(f"Added npm scripts: {', '.join(added)}")
    else:
        print("All Playwright npm scripts already exist")


def update_gitignore(project_dir: str) -> None:
    """Add Playwright-related entries to .gitignore."""
    gitignore_path = os.path.join(project_dir, ".gitignore")
    entries = [
        "",
        "# Playwright",
        "test-results/",
        "playwright-report/",
        "playwright/.cache/",
        "playwright/.auth/",
        "blob-report/",
    ]

    existing = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path) as f:
            existing = f.read()

    # Only add entries that are not already present
    new_entries = [e for e in entries if e and e not in existing]
    if new_entries or not existing:
        with open(gitignore_path, "a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n".join(entries) + "\n")
        print("Updated .gitignore with Playwright entries")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up Playwright testing in a project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --project-dir /path/to/project
  %(prog)s --base-url http://localhost:8080 --browsers chromium firefox webkit
  %(prog)s --skip-install  # Only generate config and files
        """,
    )
    parser.add_argument(
        "--project-dir", "-d", default=".",
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--base-url", "-b", default="http://localhost:3000",
        help="Base URL for tests (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--browsers", nargs="+", default=["chromium"],
        choices=["chromium", "firefox", "webkit"],
        help="Browsers to configure (default: chromium)",
    )
    parser.add_argument(
        "--skip-install", action="store_true",
        help="Skip npm install and browser installation",
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="Configure for CI environment",
    )

    args = parser.parse_args()
    project_dir = os.path.abspath(args.project_dir)

    print(f"Setting up Playwright in: {project_dir}")
    print(f"Base URL: {args.base_url}")
    print(f"Browsers: {', '.join(args.browsers)}")
    print()

    # Check prerequisites
    info = check_prerequisites(project_dir)
    if info["issues"]:
        for issue in info["issues"]:
            print(f"Error: {issue}")
        sys.exit(1)

    print(f"Node.js: {info.get('node_version', 'unknown')}")
    print(f"npm: {info.get('npm_version', 'unknown')}")
    print()

    # Initialize package.json if needed
    if not info["has_package_json"]:
        init_package_json(project_dir)

    # Install dependencies
    if not args.skip_install:
        install_playwright(project_dir)
        install_browsers(project_dir, args.browsers)
    else:
        print("Skipping dependency installation (--skip-install)")

    print()

    # Generate configuration
    generate_config(project_dir, args.base_url, args.browsers, args.ci)

    # Create directory structure
    create_directory_structure(project_dir)

    # Create example files
    print()
    create_example_page_object(project_dir)
    create_example_test(project_dir)
    create_test_fixture(project_dir)
    create_auth_setup(project_dir)

    # Update package.json scripts
    print()
    add_npm_scripts(project_dir)

    # Update .gitignore
    update_gitignore(project_dir)

    # Summary
    print()
    print("=" * 60)
    print("Playwright setup complete!")
    print("=" * 60)
    print()
    print("Directory structure:")
    print("  tests/")
    print("    specs/          # Test files (*.spec.ts)")
    print("    pages/          # Page objects (*.page.ts)")
    print("    fixtures/       # Custom fixtures")
    print("    factories/      # Test data factories")
    print("    mocks/          # HAR files and mock data")
    print("    auth.setup.ts   # Authentication setup")
    print("  playwright.config.ts")
    print()
    print("Available commands:")
    print("  npm run test:e2e              # Run all tests")
    print("  npm run test:e2e:ui           # Open interactive UI mode")
    print("  npm run test:e2e:headed       # Run with visible browser")
    print("  npm run test:e2e:debug        # Debug with Playwright Inspector")
    print("  npm run test:e2e:codegen      # Record tests with codegen")
    print("  npm run test:e2e:report       # View HTML report")
    print()
    print("Next steps:")
    print("  1. Update base URL in playwright.config.ts")
    print("  2. Uncomment webServer config if using a dev server")
    print("  3. Update auth.setup.ts with your login flow")
    print("  4. Run: npm run test:e2e")


if __name__ == "__main__":
    main()
