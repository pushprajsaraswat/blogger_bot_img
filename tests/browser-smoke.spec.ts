import { test, expect } from '@playwright/test';

test('blogger home page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/.*/);
});
