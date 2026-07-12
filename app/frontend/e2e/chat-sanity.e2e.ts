import { expect, test } from '@playwright/test';

test('normal chat returns an assistant response for "Hello Copilot"', async ({ page }) => {
  if (process.env.PLAYWRIGHT_MOCK_CHAT === 'true') {
    await page.route('**/api/', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          'data: {"type":"RUN_STARTED"}',
          'data: {"type":"TEXT_MESSAGE_START"}',
          'data: {"type":"TEXT_MESSAGE_CONTENT","delta":"Hello! "}',
          'data: {"type":"TEXT_MESSAGE_CONTENT","delta":"How can I help you today?"}',
          'data: {"type":"TEXT_MESSAGE_END"}',
          'data: {"type":"RUN_FINISHED"}',
          '',
        ].join('\n'),
      });
    });
  }

  await page.goto('/');

  const messageInput = page.getByLabel('Message input');
  await expect(messageInput).toBeVisible();

  await messageInput.fill('Hello Copilot');
  await page.getByRole('button', { name: 'Send message' }).click();

  await expect(
    page.locator('.whitespace-pre-wrap.break-words').filter({ hasText: 'Hello Copilot' }).first()
  ).toBeVisible();

  const assistantBubble = page.locator('.bg-message-assistant').last();
  await expect(assistantBubble).toBeVisible();
  await expect(assistantBubble).not.toContainText('Thinking…');
  await expect.poll(async () => (await assistantBubble.innerText()).trim().length).toBeGreaterThan(20);
});
