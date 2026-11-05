import { test, expect } from '@playwright/test';

const BASE_URL = 'https://anime-archive-fan.blogspot.com';

test('snapshot live site homepage', async ({ page }) => {
  await page.goto(BASE_URL + '/');
  await expect(page).toHaveTitle(/ANIME ARCHIVE/);
  await page.screenshot({ path: 'screenshots/homepage.png', fullPage: true });
});

test('snapshot frieren live post', async ({ page }) => {
  await page.goto(BASE_URL + '/2026/11/frieren-beyond-journeys-end.html');
  await expect(page).toHaveTitle(/anime-archive/);
  await page.screenshot({ path: 'screenshots/frieren.png', fullPage: true });
});

test('snapshot school rumble live post', async ({ page }) => {
  await page.goto(BASE_URL + '/2026/11/school-rumble-2004-encyclopedia-profile_0496945087.html');
  await expect(page).toHaveTitle(/anime-archive/);
  await page.screenshot({ path: 'screenshots/school_rumble.png', fullPage: true });
});
