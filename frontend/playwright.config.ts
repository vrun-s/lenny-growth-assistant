import { defineConfig, devices } from '@playwright/test'

// Minimal smoke-test config (PRD §8: "1-2 Playwright smoke tests"). Both
// specs mock every /api/* call via page.route(), so they never depend on a
// live backend, database, or LLM — `npx playwright test` works standalone.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
