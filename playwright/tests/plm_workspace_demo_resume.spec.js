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
  await expect(page.locator('#change-output')).toContainText('Change Snapshot');
  await expect(page.locator('#change-output')).toContainText('Release Snapshot');
  await expect(page.locator('#change-output')).toContainText('ECO Focus');
  await expect(page.locator('#change-output')).toContainText('ECO Approvals');
  await expect(page.locator('#change-output')).toContainText('Pending ECO Approvals');
  await expect(page.locator('#change-output')).toContainText(fixture.ecoName);
  await expect(page.locator('#change-output')).toContainText('Readiness State');

  await page.click('#approval-rail-button');
  await expect(page.locator('#approval-rail-output')).toContainText('ECO-Native Governance');
  await expect(page.locator('#approval-rail-output')).toContainText('Pending ECO Approvals');
  await expect(page.locator('#approval-rail-output')).toContainText(fixture.ecoName);
  await expect(page.locator('#approval-rail-output')).not.toContainText('Approval rail load failed: 404');
  await expect(page.locator('#approval-detail-output')).toContainText('Generic approval detail lens is not exposed');

  await page.click(`[data-workspace-object-type="ECO"][data-workspace-object-id="${fixture.ecoId}"]`);
  await expect(page.locator('#session-status')).toContainText(`Workspace synced for ECO:${fixture.ecoId}`);
  await expect(page.locator('#active-object-key')).toContainText(`ECO:${fixture.ecoId}`);
  await expect(page.locator('[data-tab="detail"]')).toHaveClass(/is-active/);
  await expect(page.locator('#detail-output')).toContainText(fixture.ecoName);
  await expect(page.locator('#detail-output')).toContainText('ECO');
  await expect(page.locator('#detail-output')).toContainText('Source Recovery');
  await expect(page.locator('#detail-output')).toContainText('Return to Source Change');

  await page.locator('#detail-output').getByRole('button', { name: 'Return to Source Change' }).click();
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.partId}`);
  await expect(page.locator('[data-tab="change"]')).toHaveClass(/is-active/);
  await expect(page.locator('#change-output')).toContainText('Change Snapshot');
  await expect(page.locator('#change-output')).toContainText('Release Snapshot');
  await expect(page.locator('#change-output')).toContainText('Recent ECO Activity');
  await expect(page.locator('#change-output')).toContainText(fixture.ecoName);
  await expect(page.locator('#change-output')).not.toContainText('Use the source object to return to the governed product change flow after inspecting this ECO.');

  await page.click('[data-tab="docs"]');
  await page.evaluate(async () => {
    await loadDemoSample('doc-ui-product', 'change');
  });
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.partId}`);
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

test('bom demo can inspect non-empty release readiness without leaving native part context', async ({
  request,
  page,
}) => {
  const fixture = await createConfigParentDemoFixture(request);
  await loadConfigParentDemoPreset(page, fixture, 'bom');

  await signInWorkspace(page);
  await expect(page.locator('#session-status')).toContainText('Authenticated and resumed Config Parent.');
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);

  await page.click('[data-tab="change"]');
  await page.click('#release-readiness-button');

  await expect(page.locator('#release-readiness-output')).toContainText('Readiness Summary');
  await expect(page.locator('#release-readiness-output')).toContainText(fixture.mbomName);
  await expect(page.locator('#release-readiness-output')).toContainText(fixture.routingName);
  await expect(page.locator('#release-readiness-output')).toContainText(fixture.baselineName);

  await expect(page.locator('#release-readiness-detail-output')).toContainText('Resource Detail Lens');
  await expect(page.locator('#release-readiness-detail-output')).toContainText(fixture.mbomName);
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);

  await page.click('[data-readiness-resource-index="1"]');
  await expect(page.locator('#release-readiness-detail-output')).toContainText(fixture.routingName);
  await expect(page.locator('#release-readiness-detail-output')).toContainText('Routing readiness resources publish native detail only.');
  await expect(page.locator('#release-readiness-detail-output [data-readiness-handoff="select"]')).toBeDisabled();
  await expect(page.locator('#release-readiness-detail-output [data-readiness-handoff="detail"]')).toBeEnabled();
  await expect(page.locator('#release-readiness-detail-output [data-readiness-handoff="bom"]')).toBeDisabled();
  await expect(page.locator('#change-output [data-readiness-handoff="select"]')).toBeDisabled();
  await expect(page.locator('#change-output [data-readiness-handoff="detail"]')).toBeEnabled();
  await expect(page.locator('#change-output [data-readiness-handoff="bom"]')).toBeDisabled();
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);

  await page.click('[data-readiness-resource-index="2"]');
  await expect(page.locator('#release-readiness-detail-output')).toContainText(fixture.baselineName);
  await expect(page.locator('#release-readiness-detail-output')).toContainText('Native workspace does not publish first-class explorer, detail, or BOM views for readiness resources of type baseline yet.');
  await expect(page.locator('#release-readiness-detail-output [data-readiness-handoff="select"]')).toBeDisabled();
  await expect(page.locator('#release-readiness-detail-output [data-readiness-handoff="detail"]')).toBeDisabled();
  await expect(page.locator('#release-readiness-detail-output [data-readiness-handoff="bom"]')).toBeDisabled();
  await expect(page.locator('#change-output [data-readiness-handoff="select"]')).toBeDisabled();
  await expect(page.locator('#change-output [data-readiness-handoff="detail"]')).toBeDisabled();
  await expect(page.locator('#change-output [data-readiness-handoff="bom"]')).toBeDisabled();
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);
});

test('bom demo can drill from readiness MBOM resource into native MBOM detail and structure then recover to source part', async ({
  request,
  page,
}) => {
  const fixture = await createConfigParentDemoFixture(request);
  await loadConfigParentDemoPreset(page, fixture, 'bom');

  await signInWorkspace(page);
  await expect(page.locator('#session-status')).toContainText('Authenticated and resumed Config Parent.');
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);

  await page.click('[data-tab="change"]');
  await page.click('#release-readiness-button');

  await expect(page.locator('#release-readiness-output')).toContainText(fixture.mbomName);
  await expect(page.locator('#release-readiness-detail-output')).toContainText('MBOM readiness resources publish native detail and BOM drilldown only.');

  await page.locator('#release-readiness-detail-output').getByRole('button', { name: 'Open Detail' }).click();

  await expect(page.locator('#active-object-key')).toContainText(`MBOM:${fixture.mbomId}`);
  await expect(page.locator('[data-tab="detail"]')).toHaveClass(/is-active/);
  await expect(page.locator('#detail-output')).toContainText('MBOM Drilldown');
  await expect(page.locator('#detail-output')).toContainText(fixture.mbomName);
  await expect(page.locator('#detail-output')).toContainText('MBOM Scope');
  await expect(page.locator('#detail-output')).toContainText('Source Recovery');
  await expect(page.locator('#detail-output')).toContainText('Return to Source Part');

  await page.locator('#detail-output').getByRole('button', { name: 'Return to Source Part' }).click();

  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);
  await expect(page.locator('[data-tab="detail"]')).toHaveClass(/is-active/);
  await expect(page.locator('#detail-output')).toContainText(fixture.parentNumber);
  await expect(page.locator('#detail-output')).not.toContainText('MBOM Drilldown');

  await page.click('[data-tab="change"]');
  await page.click('#release-readiness-button');
  await page.locator('#release-readiness-detail-output').getByRole('button', { name: 'Open BOM' }).click();

  await expect(page.locator('#active-object-key')).toContainText(`MBOM:${fixture.mbomId}`);
  await expect(page.locator('[data-tab="bom"]')).toHaveClass(/is-active/);
  await expect(page.locator('#bom-output')).toContainText(fixture.mbomName);
  await expect(page.locator('#bom-output')).toContainText(fixture.childANumber);
  await expect(page.locator('#bom-output')).toContainText(fixture.childBNumber);
  await expect(page.locator('#bom-output')).toContainText('Source Recovery');
  await expect(page.locator('#bom-output')).toContainText('Return to Source Part');
  await expect(page.locator('#where-used-output')).toContainText('Where-used is not published for MBOM native drilldown yet.');

  await page.locator('#bom-output').getByRole('button', { name: 'Return to Source Part' }).click();

  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);
  await expect(page.locator('[data-tab="detail"]')).toHaveClass(/is-active/);
  await expect(page.locator('#detail-output')).toContainText(fixture.parentNumber);
});

test('bom demo can drill from readiness routing resource into native routing detail then recover to source part', async ({
  request,
  page,
}) => {
  const fixture = await createConfigParentDemoFixture(request);
  await loadConfigParentDemoPreset(page, fixture, 'bom');

  await signInWorkspace(page);
  await expect(page.locator('#session-status')).toContainText('Authenticated and resumed Config Parent.');
  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);

  await page.click('[data-tab="change"]');
  await page.click('#release-readiness-button');
  await page.click('[data-readiness-resource-index="1"]');

  await expect(page.locator('#release-readiness-detail-output')).toContainText(fixture.routingName);
  await expect(page.locator('#release-readiness-detail-output')).toContainText('Routing readiness resources publish native detail only.');

  await page.locator('#release-readiness-detail-output').getByRole('button', { name: 'Open Detail' }).click();

  await expect(page.locator('#active-object-key')).toContainText(`Routing:${fixture.routingId}`);
  await expect(page.locator('[data-tab="detail"]')).toHaveClass(/is-active/);
  await expect(page.locator('#detail-output')).toContainText('Routing Drilldown');
  await expect(page.locator('#detail-output')).toContainText(fixture.routingName);
  await expect(page.locator('#detail-output')).toContainText('Routing Scope');
  await expect(page.locator('#detail-output')).toContainText('Released Operations');
  await expect(page.locator('#detail-output')).toContainText('Op 10');
  await expect(page.locator('#detail-output')).toContainText('Operations');
  await expect(page.locator('#detail-output')).toContainText('Source Recovery');
  await expect(page.locator('#detail-output')).toContainText('Return to Source Part');
  await expect(page.locator('#bom-output')).toContainText('BOM is not published for routing native drilldown.');
  await expect(page.locator('#files-output')).toContainText('Routing drilldown does not publish file attachments.');

  await page.locator('#detail-output').getByRole('button', { name: 'Return to Source Part' }).click();

  await expect(page.locator('#active-object-key')).toContainText(`Part:${fixture.parentId}`);
  await expect(page.locator('[data-tab="detail"]')).toHaveClass(/is-active/);
  await expect(page.locator('#detail-output')).toContainText(fixture.parentNumber);
  await expect(page.locator('#detail-output')).not.toContainText('Routing Drilldown');
});
