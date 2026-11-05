import { test, expect } from '@playwright/test';

const SITE_URL = 'https://anime-archive-fan.blogspot.com';

test.describe('Live Site Snapshots', () => {
  test('@live-snapshot homepage renders post cards', async ({ page }) => {
    await page.goto(SITE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const cards = page.locator('.poster-card');
    const count = await cards.count();
    console.log(`HOMEPAGE: ${count} poster cards found`);

    await page.screenshot({ path: 'snapshot-homepage.png', fullPage: true });

    if (count > 0) {
      const firstTitle = cards.first().locator('.poster-title');
      if (await firstTitle.count() > 0) {
        console.log(`First card title: ${await firstTitle.textContent()}`);
      }
    } else {
      const emptyState = page.locator('.empty-state');
      if (await emptyState.count() > 0) {
        console.log('HOMEPAGE: Empty state shown - no posts rendering');
      }
    }
  });

  test('@live-snapshot single post page renders content', async ({ page }) => {
    await page.goto(`${SITE_URL}/2026/11/frieren-beyond-journeys-end-2023_01221335584.html`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const title = page.title();
    console.log(`POST PAGE title: ${title}`);

    const aaPost = page.locator('#aaPost');
    const ledgerBody = page.locator('#aaBody');
    const emptyState = page.locator('.empty-state');

    console.log(`POST PAGE: aaPost visible=${await aaPost.isVisible()}`);
    console.log(`POST PAGE: ledgerBody visible=${await ledgerBody.isVisible()}`);
    console.log(`POST PAGE: emptyState visible=${await emptyState.isVisible()}`);

    await page.screenshot({ path: 'snapshot-post-frieren.png', fullPage: true });

    const bodyText = await ledgerBody.locator('p, h2, h3').first().textContent();
    console.log(`POST PAGE: first content = ${bodyText?.substring(0, 100)}`);
  });
});
