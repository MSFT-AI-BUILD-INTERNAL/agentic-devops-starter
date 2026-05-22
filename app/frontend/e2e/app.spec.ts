import { test, expect } from '@playwright/test'

test('app loads and renders root element', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/AI Assistant/)
  await expect(page.locator('#root')).toBeAttached()
})
