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

async function addBomChild(request, headers, parentId, childId, quantity = 1, uom = 'EA') {
  const resp = await request.post(`/api/v1/bom/${parentId}/children`, {
    headers,
    data: {
      child_id: childId,
      quantity,
      uom,
    },
  });
  expect(resp.ok()).toBeTruthy();
}

async function createBaseline(request, headers, rootItemId, name) {
  const resp = await request.post('/api/v1/baselines', {
    headers,
    data: {
      name,
      root_item_id: rootItemId,
      auto_populate: false,
      max_levels: 0,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const baseline = await resp.json();
  expect(baseline.id).toBeTruthy();
  return baseline;
}

async function createMbomFromEbom(request, headers, sourceItemId, name) {
  const resp = await request.post('/api/v1/mboms/from-ebom', {
    headers,
    data: {
      source_item_id: sourceItemId,
      name,
      version: '1.0',
      plant_code: 'PLANT-1',
    },
  });
  expect(resp.ok()).toBeTruthy();
  const mbom = await resp.json();
  expect(mbom.id).toBeTruthy();
  return mbom;
}

async function createWorkcenter(request, headers, code, name) {
  const resp = await request.post('/api/v1/workcenters', {
    headers,
    data: {
      code,
      name,
      plant_code: 'PLANT-1',
      department_code: 'LINE-1',
      is_active: true,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const workcenter = await resp.json();
  expect(workcenter.id).toBeTruthy();
  return workcenter;
}

async function createRouting(request, headers, mbomId, itemId, name) {
  const resp = await request.post('/api/v1/routings', {
    headers,
    data: {
      name,
      mbom_id: mbomId,
      item_id: itemId,
      version: '1.0',
      is_primary: true,
      plant_code: 'PLANT-1',
      line_code: 'LINE-1',
    },
  });
  expect(resp.ok()).toBeTruthy();
  const routing = await resp.json();
  expect(routing.id).toBeTruthy();
  return routing;
}

async function addRoutingOperation(request, headers, routingId, workcenterId) {
  const resp = await request.post(`/api/v1/routings/${routingId}/operations`, {
    headers,
    data: {
      operation_number: '10',
      name: 'Op 10',
      operation_type: 'fabrication',
      workcenter_id: workcenterId,
      setup_time: 5,
      run_time: 1,
      sequence: 10,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const op = await resp.json();
  expect(op.id).toBeTruthy();
  return op;
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
  const ecoName = `DOCUI-ECO-${ts}`;
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
      name: ecoName,
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

  return { ecoId: eco.id, ecoName };
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
  const { ecoId, ecoName } = await createEcoFlow(request, headers, partId, ts);

  return { partId, partNumber, docId, docNumber, ecoId, ecoName };
}

async function createConfigParentDemoFixture(request) {
  const { headers } = await login(request);
  const ts = Date.now();

  const partNumber = `CFG-P-${ts}`;
  const childANumber = `CFG-C1-${ts}`;
  const childBNumber = `CFG-C2-${ts}`;
  const parentId = await createPart(request, headers, partNumber, 'Config Parent');
  const childAId = await createPart(request, headers, childANumber, 'Config Child A');
  const childBId = await createPart(request, headers, childBNumber, 'Config Child B');

  await addBomChild(request, headers, parentId, childAId, 2, 'EA');
  await addBomChild(request, headers, parentId, childBId, 4, 'EA');

  const baseline = await createBaseline(request, headers, parentId, `BL-CFG-${ts}`);
  const mbom = await createMbomFromEbom(request, headers, parentId, `MBOM-CFG-${ts}`);
  const workcenter = await createWorkcenter(request, headers, `WC-CFG-${ts}`, `Config WC ${ts}`);
  const routing = await createRouting(request, headers, mbom.id, parentId, `Routing CFG ${ts}`);
  const operation = await addRoutingOperation(request, headers, routing.id, workcenter.id);

  return {
    parentId,
    parentNumber: partNumber,
    childAId,
    childANumber,
    childBId,
    childBNumber,
    baselineId: baseline.id,
    baselineName: baseline.name,
    mbomId: mbom.id,
    mbomName: mbom.name,
    routingId: routing.id,
    routingName: routing.name,
    workcenterId: workcenter.id,
    workcenterName: workcenter.name,
    routingOperationId: operation.id,
  };
}

async function loadDocUiDemoPreset(page, fixture, mode = 'change') {
  await page.goto('/api/v1/plm-workspace');
  await page.evaluate(
    async ({ partId, partNumber, demoMode }) => {
      demoSamples['doc-ui-product'].itemId = partId;
      demoSamples['doc-ui-product'].itemNumber = partNumber;
      demoSamples['doc-ui-product'].searchQuery = partNumber;
      await loadDemoSample('doc-ui-product', demoMode);
    },
    { ...fixture, demoMode: mode },
  );
}

async function loadConfigParentDemoPreset(page, fixture, mode = 'bom') {
  await page.goto('/api/v1/plm-workspace');
  await page.evaluate(
    async ({ parentId, parentNumber, demoMode }) => {
      demoSamples['config-parent'].itemId = parentId;
      demoSamples['config-parent'].itemNumber = parentNumber;
      demoSamples['config-parent'].searchQuery = parentNumber;
      await loadDemoSample('config-parent', demoMode);
    },
    { ...fixture, demoMode: mode },
  );
}

async function signInWorkspace(page, { username = 'admin', password = 'admin' } = {}) {
  await page.fill('#login-username', username);
  await page.fill('#login-password', password);
  await page.click('#login-button');
}

module.exports = {
  createConfigParentDemoFixture,
  createDocUiDemoFixture,
  loadConfigParentDemoPreset,
  loadDocUiDemoPreset,
  signInWorkspace,
};
