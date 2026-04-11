const { test, expect } = require('@playwright/test');
const {
  createDocUiDemoFixture,
  loadDocUiDemoPreset,
  signInWorkspace,
} = require('./helpers/plmWorkspaceDemo');

test.use({ channel: 'chrome' });

async function workspaceHeaders(page) {
  const token = await page.inputValue('#bearer-token');
  expect(token).toBeTruthy();
  return {
    Authorization: `Bearer ${token}`,
    'x-tenant-id': 'tenant-1',
    'x-org-id': 'org-1',
  };
}

test('change tab can approve the focused ECO and refresh native governance context', async ({ request, page }) => {
  const fixture = await createDocUiDemoFixture(request);
  await loadDocUiDemoPreset(page, fixture, 'change');

  await signInWorkspace(page);
  await page.click('[data-tab="change"]');

  await expect(page.locator('#change-output')).toContainText(fixture.ecoName);
  await expect(page.locator('#change-output [data-eco-action="approve"]').first()).toBeVisible();

  await page.locator('#change-output [data-eco-action="approve"]').first().click();

  await expect(page.locator('#session-status')).toContainText(`ECO ${fixture.ecoId} approved.`);
  await expect(page.locator('#session-status')).toContainText('Current ECO state approved.');
  await expect(page.locator('#change-output')).toContainText('Approve ECO');

  const headers = await workspaceHeaders(page);
  const ecoResp = await request.get(`/api/v1/eco/${fixture.ecoId}`, { headers });
  expect(ecoResp.ok()).toBeTruthy();
  const eco = await ecoResp.json();
  expect(eco.state).toBe('approved');

  const approvalsResp = await request.get(`/api/v1/eco/${fixture.ecoId}/approvals`, { headers });
  expect(approvalsResp.ok()).toBeTruthy();
  const approvals = await approvalsResp.json();
  expect(Array.isArray(approvals)).toBeTruthy();
  expect(approvals.some((entry) => entry.status === 'approved')).toBeTruthy();
});

test('change tab can reject the focused ECO with a reason and keep the workspace in sync', async ({ request, page }) => {
  const fixture = await createDocUiDemoFixture(request);
  await loadDocUiDemoPreset(page, fixture, 'change');

  await signInWorkspace(page);
  await page.click('[data-tab="change"]');

  await expect(page.locator('#change-output')).toContainText(fixture.ecoName);
  await expect(page.locator('#change-output [data-eco-action="reject"]').first()).toBeVisible();

  page.once('dialog', (dialog) => dialog.accept('Needs additional change detail'));
  await page.locator('#change-output [data-eco-action="reject"]').first().click();

  await expect(page.locator('#session-status')).toContainText(`ECO ${fixture.ecoId} rejected.`);
  await expect(page.locator('#session-status')).toContainText('Current ECO state progress.');
  await expect(page.locator('#change-output')).toContainText('Reject ECO');

  const headers = await workspaceHeaders(page);
  const ecoResp = await request.get(`/api/v1/eco/${fixture.ecoId}`, { headers });
  expect(ecoResp.ok()).toBeTruthy();
  const eco = await ecoResp.json();
  expect(eco.state).toBe('progress');

  const approvalsResp = await request.get(`/api/v1/eco/${fixture.ecoId}/approvals`, { headers });
  expect(approvalsResp.ok()).toBeTruthy();
  const approvals = await approvalsResp.json();
  expect(Array.isArray(approvals)).toBeTruthy();
  expect(
    approvals.some((entry) => entry.status === 'rejected' && entry.comment === 'Needs additional change detail')
  ).toBeTruthy();
});
