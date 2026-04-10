const { test, expect } = require('@playwright/test');
const {
  createConfigParentDemoFixture,
  createDocUiDemoFixture,
  loadConfigParentDemoPreset,
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

test('bom demo preset resumes after UI login and hydrates non-empty structure flow', async ({ request, page }) => {
  const fixture = await createConfigParentDemoFixture(request);
  await loadConfigParentDemoPreset(page, fixture, 'bom');

  await expect(page.locator('#session-status')).toContainText('Demo preset Config Parent is loaded.');
  await expect(page.locator('#session-status')).toContainText('Bearer token is required before syncing protected PLM object data.');
  await expect(page.locator('#active-object-pills')).toContainText('Pending demo Config Parent (BOM demo)');

  await signInWorkspace(page);
  await expect(page.locator('#session-status')).toContainText('Authenticated and resumed Config Parent.');
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);
  await expect(page.locator('[data-tab="bom"]')).toHaveClass(/is-active/);
  await expect(page.locator('#bom-output')).toContainText(fixture.parentNumber);
  await expect(page.locator('#bom-output')).toContainText(fixture.childANumber);
  await expect(page.locator('#bom-output')).toContainText(fixture.childBNumber);
  await expect(page.locator('#bom-output')).toContainText('Descendants');
  await expect(page.locator('#where-used-output')).toContainText('Parents 0');
});
