import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'tests/ui',
  timeout: 180_000,
  fullyParallel: true,
  reporter: [['list']],
  outputDir: '/tmp/playwright-output',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    // Use chromium with specific launch options for Docker
    channel: 'chromium',
    launchOptions: {
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    },
  },
});


