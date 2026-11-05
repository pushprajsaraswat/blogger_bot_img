import { test, expect } from '@playwright/test';

const BLOG_ID = process.env.BLOGGER_BLOG_ID || '3269668895056439997';
const THEME_PATH = process.env.THEME_XML_PATH || './blogger_theme.xml';

test('deploy theme via Blogger dashboard', async ({ page }) => {
  // Navigate to Blogger dashboard theme editor
  await page.goto(
    `https://www.blogger.com/blogger.g?blogID=${BLOG_ID}#editor/src=theme`,
    { waitUntil: 'domcontentloaded', timeout: 60000 },
  );

  // Check if we're on the login page (not authenticated)
  const title = await page.title();
  const url = page.url();

  if (url.includes('accounts.google.com') || title.includes('Sign in')) {
    // Not authenticated — capture evidence and fail with guidance
    await page.screenshot({ path: 'blogger-login-required.png', fullPage: true });
    throw new Error(
      'Blogger dashboard requires Google authentication. ' +
      'Please export session cookies from your logged-in Chromium profile ' +
      'and configure them as GitHub secrets, or deploy the theme manually ' +
      'via Blogger dashboard > Theme > Edit HTML.',
    );
  }

  // If authenticated, proceed with theme deployment
  // TODO: Add steps to paste theme XML and save once auth is available
  await expect(page).toHaveTitle(/blogger|theme/i);
});
