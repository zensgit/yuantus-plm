const { expect } = require('@playwright/test');

async function login(request) {
  const loginResp = await request.post('/api/v1/auth/login', {
    data: {
      tenant_id: 'tenant-1',
      org_id: 'org-1',
      username: 'admin',
      password: 'admin',
    },
  });
  expect(loginResp.ok()).toBeTruthy();
  const login = await loginResp.json();
  const token = login.access_token;
  expect(token).toBeTruthy();
  return {
    token,
    headers: {
      Authorization: `Bearer ${token}`,
      'x-tenant-id': 'tenant-1',
      'x-org-id': 'org-1',
    },
  };
}

async function ensureItemType(request, headers, typeId, payload) {
  const resp = await request.get(`/api/v1/meta/item-types/${encodeURIComponent(typeId)}`, {
    headers,
  });
  if (resp.ok()) {
    return;
  }
  const createResp = await request.post('/api/v1/meta/item-types', {
    headers,
    data: payload,
  });
  expect([200, 409]).toContain(createResp.status());
}

async function createPart(request, headers, number, name) {
  const resp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'add',
      properties: {
        item_number: number,
        name,
      },
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  expect(data.id).toBeTruthy();
  return data.id;
}

async function createDocument(request, headers, number, name) {
  const resp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Document',
      action: 'add',
      properties: {
        item_number: number,
        doc_number: number,
        name,
      },
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  expect(data.id).toBeTruthy();
  return data.id;
}

async function createRelationship(request, headers, sourceId, relationId, relatedId) {
  const resp = await request.post('/api/v1/rpc/', {
    headers,
    data: {
      model: 'Relationship',
      method: 'add',
      args: [sourceId, relationId, relatedId, {}],
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  expect(data.result?.status).toBe('success');
}

async function uploadFileAndAttach(request, headers, itemId, filename) {
  const uploadResp = await request.post('/api/v1/file/upload?generate_preview=false', {
    headers: {
      Authorization: headers.Authorization,
      'x-tenant-id': headers['x-tenant-id'],
      'x-org-id': headers['x-org-id'],
    },
    multipart: {
      file: {
        name: filename,
        mimeType: 'application/pdf',
        buffer: Buffer.from(`demo file ${filename}`),
      },
      author: 'Doc UI Author',
      source_system: 'playwright-e2e',
      source_version: 'v1',
      document_version: 'A.1',
    },
  });
  expect(uploadResp.ok()).toBeTruthy();
  const upload = await uploadResp.json();
  expect(upload.id).toBeTruthy();

  const attachResp = await request.post('/api/v1/file/attach', {
    headers,
    data: {
      item_id: itemId,
      file_id: upload.id,
      file_role: 'drawing',
      description: 'demo drawing attachment',
    },
  });
  expect(attachResp.ok()).toBeTruthy();
  const attach = await attachResp.json();
  expect(['created', 'updated']).toContain(attach.status);
}

async function createEcoFlow(request, headers, partId, ts) {
  const stageResp = await request.post('/api/v1/eco/stages', {
    headers,
    data: {
      name: `DOCUI-STAGE-${ts}`,
      sequence: 90,
      approval_type: 'mandatory',
      approval_roles: ['admin'],
      auto_progress: false,
      is_blocking: false,
      sla_hours: 0,
    },
  });
  expect(stageResp.ok()).toBeTruthy();
  const stage = await stageResp.json();
  expect(stage.id).toBeTruthy();

  const ecoResp = await request.post('/api/v1/eco', {
    headers,
    data: {
      name: `DOCUI-ECO-${ts}`,
      eco_type: 'bom',
      product_id: partId,
      description: 'doc ui summary',
    },
  });
  expect(ecoResp.ok()).toBeTruthy();
  const eco = await ecoResp.json();
  expect(eco.id).toBeTruthy();

  const moveResp = await request.post(`/api/v1/eco/${eco.id}/move-stage`, {
    headers,
    data: { stage_id: stage.id },
  });
  expect(moveResp.ok()).toBeTruthy();
  const moved = await moveResp.json();
  expect(moved.stage_id).toBe(stage.id);

  return eco.id;
}

async function createDocUiDemoFixture(request) {
  const { headers } = await login(request);
  const ts = Date.now();

  await ensureItemType(request, headers, 'Document', {
    id: 'Document',
    label: 'Document',
    is_relationship: false,
    is_versionable: true,
  });
  await ensureItemType(request, headers, 'Document Part', {
    id: 'Document Part',
    label: 'Document Part',
    is_relationship: true,
    is_versionable: false,
    source_item_type_id: 'Part',
    related_item_type_id: 'Document',
  });

  const partNumber = `DOCUI-P-${ts}`;
  const docNumber = `DOCUI-D-${ts}`;
  const partId = await createPart(request, headers, partNumber, 'Doc UI Product');
  const docId = await createDocument(request, headers, docNumber, 'Doc UI Doc');
  await createRelationship(request, headers, partId, 'Document Part', docId);
  await uploadFileAndAttach(request, headers, partId, `${partNumber}_drawing_v1.pdf`);
  const ecoId = await createEcoFlow(request, headers, partId, ts);

  return { partId, partNumber, docId, docNumber, ecoId };
}

async function loadDocUiDemoPreset(page, fixture, mode = 'change') {
  await page.goto('/api/v1/plm-workspace');
  await page.evaluate(
    ({ partId, partNumber }) => {
      demoSamples['doc-ui-product'].itemId = partId;
      demoSamples['doc-ui-product'].itemNumber = partNumber;
      demoSamples['doc-ui-product'].searchQuery = partNumber;
    },
    fixture,
  );
  await page.click(`[data-demo-sample="doc-ui-product"][data-demo-mode="${mode}"]`);
}

async function signInWorkspace(page, { username = 'admin', password = 'admin' } = {}) {
  await page.fill('#login-username', username);
  await page.fill('#login-password', password);
  await page.click('#login-button');
}

module.exports = {
  createDocUiDemoFixture,
  loadDocUiDemoPreset,
  signInWorkspace,
};
