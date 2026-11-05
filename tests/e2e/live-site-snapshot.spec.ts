import { test, expect } from '@playwright/test';

const BASE_URL = 'https://anime-archive-fan.blogspot.com';

test.use({
  viewport: { width: 1280, height: 800 },
  navigationTimeout: 45000,
});

async function safeSnapshot(page: any, name: string, url: string) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (e) {
    // Page may still have loaded partially; continue to screenshot
  }
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true, timeout: 30000 });
}

test('snapshot live site homepage', async ({ page }) => {
  await safeSnapshot(page, 'homepage', BASE_URL + '/');
});

test('snapshot frieren live post', async ({ page }) => {
  await safeSnapshot(page, 'frieren', BASE_URL + '/2026/11/frieren-beyond-journeys-end.html');
});

test('snapshot school rumble live post', async ({ page }) => {
  await safeSnapshot(page, 'school_rumble', BASE_URL + '/2026/11/school-rumble-2004-encyclopedia-profile_0496945087.html');
});
