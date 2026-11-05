import { test, expect } from '@playwright/test';

test.use({ storageState: 'playwright/.auth/blogger.json' });

test.describe('Blogger.com Login', () => {
  test('@blogger-login logs into blogger.com successfully', async ({ page }) => {
    const email = process.env.BLOGGER_EMAIL;
    const password = process.env.BLOGGER_PASSWORD;

    if (!email || !password) {
      test.skip(true, 'BLOGGER_EMAIL and BLOGGER_PASSWORD secrets not configured');
    }

    // Navigate to Blogger login
    await page.goto('https://www.blogger.com', { waitUntil: 'networkidle' });

    // Click sign-in if present
    const signIn = page.locator('text=Sign in, a:has-text("Sign in"), [href*="accounts.google.com"]');
    if (await signIn.count() > 0) {
      await signIn.first().click();
    }

    // Enter email
    await page.locator('input[type="email"], input[name="identifier"]').fill(email);
    await page.click('button:has-text("Next"), input[type="submit"], #identifierNext');

    // Wait for password screen
    await page.waitForURL('**/accounts.google.com/**', { timeout: 30000 });

    // Enter password
    await page.locator('input[type="password"], input[name="password"]').fill(password);
    await page.click('button:has-text("Next"), input[type="submit"], #passwordNext');

    // Wait for redirect back to Blogger dashboard
    await page.waitForURL('**/blogger.com/**', { timeout: 30000 });

    // Verify login succeeded - check for dashboard elements
    const dashboard = page.locator('text=Posts, text=Statistics, text=Comments, [href*="blogger.com/blog/posts"]');
    await expect(dashboard.first()).toBeVisible({ timeout: 15000 });

    // Save storage state for reuse
    await page.context().storageState({ path: 'playwright/.auth/blogger.json' });
  });
});
