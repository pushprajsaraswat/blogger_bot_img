import { test, expect } from '@playwright/test';

const BASE_URL = 'https://anime-archive-fan.blogspot.com';

test.use({
  viewport: { width: 1280, height: 800 },
  navigationTimeout: 60000,
});

test('snapshot live site homepage', async ({ page }) => {
  await page.goto(BASE_URL + '/', { waitUntil: 'networkidle', timeout: 60000 });
  await expect(page).toHaveTitle(/ANIME ARCHIVE/);
  await page.screenshot({ path: 'screenshots/homepage.png', fullPage: true, timeout: 30000 });
});

test('snapshot frieren live post', async ({ page }) => {
  await page.goto(BASE_URL + '/2026/11/frieren-beyond-journeys-end.html', { waitUntil: 'networkidle', timeout: 60000 });
  await expect(page).toHaveTitle(/anime-archive/);
  await page.screenshot({ path: 'screenshots/frieren.png', fullPage: true, timeout: 30000 });
});

test('snapshot school rumble live post', async ({ page }) => {
  await page.goto(BASE_URL + '/2026/11/school-rumble-2004-encyclopedia-profile_0496945087.html', { waitUntil: 'networkidle', timeout: 60000 });
  await expect(page).toHaveTitle(/anime-archive/);
  await page.screenshot({ path: 'screenshots/school_rumble.png', fullPage: true, timeout: 30000 });
});
