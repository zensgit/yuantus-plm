const { test, expect } = require('@playwright/test');
const {
  createDocUiDemoFixture,
  loadDocUiDemoPreset,
  signInWorkspace,
} = require('./helpers/plmWorkspaceDemo');

test.use({ channel: 'chrome' });

test('demo preset resumes after UI login and hydrates change + documents flow', async ({ request, page }) => {
  const fixture = await createDocUiDemoFixture(request);
  await loadDocUiDemoPreset(page, fixture, 'change');
  await expect(page.locator('#session-status')).toContainText('Demo preset Doc UI Product is loaded.');
  await expect(page.locator('#session-status')).toContainText('Bearer token is required before syncing protected PLM object data.');
  await expect(page.locator('#active-object-pills')).toContainText('Pending demo Doc UI Product (Change demo)');

  await signInWorkspace(page);
  await expect(page.locator('#session-status')).toContainText('Authenticated and resumed Doc UI Product.');
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.partId}`);
  await expect(page.locator('#change-output')).toContainText('ECO Focus');
  await expect(page.locator('#change-output')).toContainText(`DOCUI-ECO-`);

  await page.click('[data-tab="docs"]');
  await expect(page.locator('#active-object-pills')).toContainText('Product summary loaded');
  await expect(page.locator('#files-output')).toContainText(`${fixture.partNumber}_drawing_v1.pdf`);
  await expect(page.locator('#related-documents-output')).toContainText('Doc UI Doc');
});
