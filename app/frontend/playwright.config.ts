import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig, devices } from '@playwright/test';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8080';
const useLocalWebServer = !process.env.PLAYWRIGHT_BASE_URL;
const hasRealToken = !!process.env.PLAYWRIGHT_GITHUB_TOKEN;

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  globalSetup: './e2e/global-setup.ts',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['line']] : 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
    // Use the pre-built session cookie only when a real GitHub token is available.
    storageState: hasRealToken
      ? path.join(__dirname, 'e2e/.auth/user.json')
      : undefined,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: useLocalWebServer
    ? {
        command: 'npm run dev -- --host 127.0.0.1 --port 8080',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      }
    : undefined,
});
