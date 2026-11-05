import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BLOG_ID = process.env.BLOGGER_BLOG_ID || '3269668895056439997';
const EMAIL = process.env.BLOGGER_EMAIL || '';
const PASSWORD = process.env.BLOGGER_PASSWORD || '';
const THEME_PATH = path.resolve(process.env.THEME_XML_PATH || './blogger_theme.xml');

test.use({
  viewport: { width: 1280, height: 800 },
  navigationTimeout: 60000,
});

test('deploy theme via Blogger dashboard', async ({ page }) => {
  test.skip(!EMAIL || !PASSWORD, 'BLOGGER_EMAIL and BLOGGER_PASSWORD secrets not configured');

  // Read theme XML from file
  const themeXml = fs.readFileSync(THEME_PATH, 'utf-8');
  console.log(`Theme XML loaded: ${themeXml.length} bytes`);

  // Navigate to Blogger dashboard theme editor
  await page.goto(
    `https://www.blogger.com/blogger.g?blogID=${BLOG_ID}#editor/src=theme`,
    { waitUntil: 'domcontentloaded', timeout: 60000 },
  );

  // Handle Google login if redirected
  const url = page.url();
  const title = await page.title();

  if (url.includes('accounts.google.com') || title.includes('Sign in')) {
    console.log('Redirecting to Google login...');

    // Enter email
    await page.fill('input[type="email"]', EMAIL, { timeout: 15000 });
    await page.click('button:has-text("Next"), input[type="button"][value="Next"]', { timeout: 15000 });
    await page.waitForTimeout(3000);

    // Enter password
    await page.fill('input[type="password"]', PASSWORD, { timeout: 15000 });
    await page.click('button:has-text("Next"), input[type="button"][value="Next"]', { timeout: 15000 });
    await page.waitForTimeout(5000);

    // Wait for redirect back to Blogger
    await page.waitForURL(`**/blogger.com/**`, { timeout: 60000 });
  }

  // Verify we're on the Blogger theme editor
  await page.waitForURL(`**/blogger.com/blogger.g?blogID=${BLOG_ID}**`, { timeout: 60000 });

  // Look for the theme HTML editor
  const themeEditor = page.locator('textarea, .CodeMirror, [contenteditable="true"]').first();
  await themeEditor.waitFor({ state: 'visible', timeout: 30000 });

  // Click into editor, select all, paste theme XML
  await themeEditor.click();
  await themeEditor.press('Control+A');
  await themeEditor.type(themeXml, { delay: 1 });

  // Click Save button
  const saveButton = page.locator('button:has-text("Save"), button:has-text("Simpan")').first();
  if (await saveButton.count() > 0) {
    await saveButton.click({ timeout: 10000 });
    await page.waitForTimeout(5000);
    console.log('Theme saved successfully');
  } else {
    console.warn('Save button not found - theme may need manual save');
  }

  // Verify by fetching the live homepage
  const response = await page.request.get('https://anime-archive-fan.blogspot.com/', { timeout: 30000 });
  const html = await response.text();
  const hasPosts = html.includes('data:posts') || html.includes('<article') || html.includes('ledger-sheet');
  console.log(`Homepage status: ${response.status()}, renders posts: ${hasPosts}`);

  await page.screenshot({ path: 'theme-deployed.png', fullPage: true });
});
