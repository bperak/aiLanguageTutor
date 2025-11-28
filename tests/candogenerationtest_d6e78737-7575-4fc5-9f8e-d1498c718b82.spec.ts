
import { test } from '@playwright/test';
import { expect } from '@playwright/test';

test('CanDoGenerationTest_2025-10-25', async ({ page, context }) => {
  
    // Navigate to URL
    await page.goto('http://localhost:3000');

    // Navigate to URL
    await page.goto('http://localhost:3000');

    // Take screenshot
    await page.screenshot({ path: 'homepage_initial.png', { fullPage: true } });

    // Navigate to URL
    await page.goto('http://localhost:3000/cando/test_cando_001');

    // Take screenshot
    await page.screenshot({ path: 'cando_page_test.png', { fullPage: true } });
});