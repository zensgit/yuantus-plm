const { test, expect } = require('@playwright/test');

test.use({ channel: 'chrome' });

function documentFixture({ fileStatus = { state: 'error', error: 'file side down' }, relatedStatus = { state: 'ok' } } = {}) {
  return {
    detail: {
      id: 'doc-1',
      item_type_id: 'Document',
      name: 'Doc UI Doc',
      state: 'Draft',
      properties: {
        item_number: 'DOCUI-D-1768357216',
        name: 'Doc UI Doc',
      },
    },
    source: {
      id: 'part-1',
      type: 'Part',
      title: 'Doc UI Product',
      number: 'DOCUI-P-1768357216',
      state: 'Draft',
      files_count: 1,
      related_documents_count: 1,
      open_eco_count: 1,
    },
    files: null,
    relatedDocuments: {
      items: [
        {
          id: '93bdaa95-cce2-4e17-9f2d-2b036a1b23d2',
          item_number: 'DOCUI-D-1768357216',
          name: 'Doc UI Doc',
          state: 'Draft',
          config_id: 'cfg-doc-1',
        },
      ],
    },
    fileStatus,
    relatedStatus,
  };
}

async function loadDocumentWorkspaceState(page, fixture = documentFixture()) {
  await page.goto('/api/v1/plm-workspace');
  await page.evaluate((payload) => {
    itemTypeInput.value = 'Document';
    itemIdInput.value = payload.detail.id;
    workspaceState.detail = payload.detail;
    workspaceState.handoffSource = payload.source;
    workspaceState.files = payload.files;
    workspaceState.relatedDocuments = payload.relatedDocuments;
    workspaceState.filesStatus = payload.fileStatus;
    workspaceState.relatedDocumentsStatus = payload.relatedStatus;
    workspaceState.objectStaleReason = null;
    refreshSummary();
    renderDetail(workspaceState.detail);
    renderChangeTab();
    renderDocumentsOverview();
    activateTab('docs');
  }, fixture);
}

test('documents tab shows boundary, source snapshot, and partial degradation warning', async ({ page }) => {
  await loadDocumentWorkspaceState(page);

  await expect(page.locator('#active-object-pills')).toContainText('Documents partial: Files');
  await expect(page.locator('#active-object-pills')).toContainText('Source 1 file(s) · 1 AML doc(s) · 1 ECO(s)');
  await expect(page.locator('#documents-overview-output')).toContainText('File attachments unavailable');
  await expect(page.locator('#documents-overview-output')).toContainText('Current documents view is partial.');
  await expect(page.locator('#documents-overview-output')).toContainText('Viewing related document object.');
  await expect(page.locator('#documents-overview-output')).toContainText('Document Boundary');
  await expect(page.locator('#documents-overview-output')).toContainText('Workspace Journey');
  await expect(page.locator('#documents-overview-output')).toContainText('Journey Path');
  await expect(page.locator('#documents-overview-output')).toContainText('Source Object');
  await expect(page.locator('#documents-overview-output')).toContainText('Source Files');
  await expect(page.locator('#documents-overview-output')).toContainText('Source AML Docs');
  await expect(page.locator('#documents-overview-output')).toContainText('Source ECOs');
});

test('detail and change surfaces keep document status and source recovery aligned', async ({ page }) => {
  await loadDocumentWorkspaceState(page);

  await page.click('[data-tab="detail"]');
  await expect(page.locator('#detail-output')).toContainText('Viewing related document object.');
  await expect(page.locator('#detail-output')).toContainText('Document Workspace');
  await expect(page.locator('#detail-output')).toContainText('Document Surface Status');
  await expect(page.locator('#detail-output')).toContainText('Attachments Source');
  await expect(page.locator('#detail-output')).toContainText('Failed: file side down');
  await expect(page.locator('#detail-output')).toContainText('Source Recovery');

  await page.click('[data-tab="change"]');
  await expect(page.locator('#change-output')).toContainText('Viewing related document object.');
  await expect(page.locator('#change-output')).toContainText('Document Focus');
  await expect(page.locator('#change-output')).toContainText('Document Surface Status');
  await expect(page.locator('#change-output')).toContainText('Governance Boundary');
  await expect(page.locator('#change-output')).toContainText('Attachments Source');
  await expect(page.locator('#change-output')).toContainText('Failed: file side down');
});
