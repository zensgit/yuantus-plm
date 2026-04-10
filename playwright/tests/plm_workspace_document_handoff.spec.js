const { test, expect } = require('@playwright/test');
const {
  createDocUiDemoFixture,
  loadDocUiDemoPreset,
  signInWorkspace,
} = require('./helpers/plmWorkspaceDemo');

test.use({ channel: 'chrome' });

test('related document handoff returns to source documents with source recovery intact', async ({ request, page }) => {
  const fixture = await createDocUiDemoFixture(request);

  await loadDocUiDemoPreset(page, fixture, 'change');
  await signInWorkspace(page);

  await expect(page.locator('#session-status')).toContainText('Authenticated and resumed Doc UI Product.');

  await page.click('[data-tab="docs"]');
  await expect(page.locator('#related-documents-output')).toContainText('Doc UI Doc');
  await page.locator('#related-documents-output').getByRole('button', { name: 'Open Change' }).first().click();

  await expect(page.locator('#active-object-key')).toContainText(`Document:${fixture.docId}`);
  await expect(page.locator('#active-object-pills')).toContainText(`Handoff from Part:${fixture.partId}`);
  await expect(page.locator('#product-context-output')).toContainText('Viewing related document object.');
  await expect(page.locator('#product-context-output')).toContainText('Return to Source Product');
  await expect(page.locator('#change-output')).toContainText('Document Focus');
  await expect(page.locator('#change-output')).toContainText('Workspace Journey');
  await expect(page.locator('#change-output')).toContainText('Governance Boundary');
  await expect(page.locator('#change-output')).toContainText('Document Source');
  await expect(page.locator('#change-output')).toContainText('Not published for this object');
  await expect(page.locator('#change-output')).not.toContainText('Change Snapshot');
  await expect(page.locator('#change-output')).not.toContainText('Release Snapshot');

  await page.getByRole('button', { name: 'Return to Source Product' }).first().click();
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.partId}`);
  await expect(page.locator('#product-context-output')).not.toContainText('Viewing related document object.');
  await page.click('[data-tab="docs"]');
  await expect(page.locator('#files-output')).toContainText(`${fixture.partNumber}_drawing_v1.pdf`);
  await expect(page.locator('#related-documents-output')).toContainText('Doc UI Doc');
  await expect(page.locator('#active-object-pills')).toContainText('Product summary loaded');
  await page.click('[data-tab="change"]');
  await expect(page.locator('#change-output')).toContainText('Change Snapshot');
  await expect(page.locator('#change-output')).toContainText('Release Snapshot');
  await expect(page.locator('#change-output')).toContainText('Recent ECO Activity');
});
