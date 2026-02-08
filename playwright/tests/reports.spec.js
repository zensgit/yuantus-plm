const { test, expect } = require('@playwright/test');

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

async function createPart(request, headers, number, name) {
  const resp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'add',
      properties: {
        item_number: number,
        name,
        description: name,
      },
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  expect(data.id).toBeTruthy();
  return data.id;
}

async function createMbomFromEbom(request, headers, sourceItemId, name, plantCode) {
  const resp = await request.post('/api/v1/mboms/from-ebom', {
    headers,
    data: {
      source_item_id: sourceItemId,
      name,
      version: '1.0',
      plant_code: plantCode,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const mbom = await resp.json();
  expect(mbom.id).toBeTruthy();
  return mbom;
}

async function createWorkcenter(request, headers, code, name, plantCode, lineCode) {
  const resp = await request.post('/api/v1/workcenters', {
    headers,
    data: {
      code,
      name,
      plant_code: plantCode,
      department_code: lineCode,
      is_active: true,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const wc = await resp.json();
  expect(wc.id).toBeTruthy();
  return wc.id;
}

async function createRouting(request, headers, mbomId, itemId, name, plantCode, lineCode) {
  const resp = await request.post('/api/v1/routings', {
    headers,
    data: {
      name,
      mbom_id: mbomId,
      item_id: itemId,
      version: '1.0',
      is_primary: true,
      plant_code: plantCode,
      line_code: lineCode,
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
  return op.id;
}

test('Reports: advanced search, saved search, report execute/export (API-only) works', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const name = `RPT-${ts} Report Test Part`;
  await createPart(request, headers, `RPT-${ts}-001`, name);
  await createPart(request, headers, `RPT-${ts}-002`, name);

  const searchResp = await request.post('/api/v1/reports/search', {
    headers,
    data: {
      item_type_id: 'Part',
      full_text: `RPT-${ts}`,
      page: 1,
      page_size: 10,
      include_count: true,
    },
  });
  expect(searchResp.ok()).toBeTruthy();
  const search = await searchResp.json();
  expect(Array.isArray(search.items)).toBeTruthy();
  expect(search.total).toBeGreaterThanOrEqual(2);

  const savedCreate = await request.post('/api/v1/reports/saved-searches', {
    headers,
    data: {
      name: `SavedSearch-${ts}`,
      description: 'playwright test',
      is_public: false,
      criteria: {
        item_type_id: 'Part',
        full_text: `RPT-${ts}`,
      },
    },
  });
  expect(savedCreate.ok()).toBeTruthy();
  const saved = await savedCreate.json();
  expect(saved.id).toBeTruthy();

  const savedRun = await request.post(`/api/v1/reports/saved-searches/${saved.id}/run?page=1&page_size=10`, {
    headers,
  });
  expect(savedRun.ok()).toBeTruthy();
  const savedResult = await savedRun.json();
  expect(savedResult.total).toBeGreaterThanOrEqual(2);

  const reportCreate = await request.post('/api/v1/reports/definitions', {
    headers,
    data: {
      name: `Report-${ts}`,
      code: `RPT-${ts}`,
      description: 'playwright test',
      category: 'test',
      report_type: 'table',
      data_source: {
        type: 'query',
        item_type_id: 'Part',
        full_text: `RPT-${ts}`,
      },
      is_public: false,
      is_active: true,
    },
  });
  expect(reportCreate.ok()).toBeTruthy();
  const report = await reportCreate.json();
  expect(report.id).toBeTruthy();

  const execResp = await request.post(`/api/v1/reports/definitions/${report.id}/execute`, {
    headers,
    data: { page: 1, page_size: 10 },
  });
  expect(execResp.ok()).toBeTruthy();
  const exec = await execResp.json();
  expect(exec.execution_id).toBeTruthy();
  expect(exec.data).toBeTruthy();
  expect(exec.data.total).toBeGreaterThanOrEqual(2);

  const exportResp = await request.post(`/api/v1/reports/definitions/${report.id}/export`, {
    headers,
    data: { export_format: 'csv', page: 1, page_size: 100 },
  });
  expect(exportResp.ok()).toBeTruthy();
  const csvText = await exportResp.text();
  expect(csvText).toContain(`RPT-${ts}`);

  // Best-effort cleanup (avoid polluting shared sqlite DB across test files).
  const delSaved = await request.delete(`/api/v1/reports/saved-searches/${saved.id}`, { headers });
  expect(delSaved.ok()).toBeTruthy();
  const delReport = await request.delete(`/api/v1/reports/definitions/${report.id}`, { headers });
  expect(delReport.ok()).toBeTruthy();
});

test('Reports: summary endpoint returns counts + request context meta', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `RPT-SUM-${ts}-001`, `RPT-SUM-${ts} Summary Part`);
  await createPart(request, headers, `RPT-SUM-${ts}-002`, `RPT-SUM-${ts} Summary Part`);

  // Add at least one manufacturing object so summary dimensions are exercised.
  const plantCode = `PLANT-SUM-${ts}`;
  const lineCode = `LINE-SUM-${ts}`;
  const mbom = await createMbomFromEbom(
    request,
    headers,
    partId,
    `MBOM-SUM-${ts}`,
    plantCode
  );
  const wcId = await createWorkcenter(
    request,
    headers,
    `WC-SUM-${ts}`,
    `WorkCenter SUM ${ts}`,
    plantCode,
    lineCode
  );
  const routing = await createRouting(
    request,
    headers,
    mbom.id,
    partId,
    `Routing SUM ${ts}`,
    plantCode,
    lineCode
  );
  await addRoutingOperation(request, headers, routing.id, wcId);

  const resp = await request.get('/api/v1/reports/summary', { headers });
  expect(resp.ok()).toBeTruthy();
  const summary = await resp.json();

  expect(summary.meta).toBeTruthy();
  expect(summary.meta.tenant_id).toBe('tenant-1');
  expect(summary.meta.org_id).toBe('org-1');
  expect(summary.meta.tenancy_mode).toBe('single');
  expect(String(summary.meta.generated_at || '')).toContain('T');

  expect(summary.items).toBeTruthy();
  expect(typeof summary.items.total).toBe('number');
  expect(summary.items.total).toBeGreaterThanOrEqual(2);

  const byType = summary.items.by_type || [];
  const partRow = byType.find((r) => r.item_type_id === 'Part');
  expect(partRow).toBeTruthy();
  expect(partRow.count).toBeGreaterThanOrEqual(2);

  // Basic smoke checks for the other sections.
  expect(typeof summary.files.total).toBe('number');
  expect(Array.isArray(summary.files.by_conversion_status || [])).toBeTruthy();
  expect(Array.isArray(summary.files.by_is_native_cad || [])).toBeTruthy();
  expect(typeof summary.versions.total).toBe('number');
  expect(typeof summary.ecos.total).toBe('number');
  expect(typeof summary.jobs.total).toBe('number');

  expect(summary.manufacturing).toBeTruthy();
  expect(typeof summary.manufacturing.mboms.total).toBe('number');
  expect(typeof summary.manufacturing.routings.total).toBe('number');
  expect(typeof summary.manufacturing.workcenters.total).toBe('number');
  expect(typeof summary.manufacturing.operations.total).toBe('number');

  const mbomByPlant = summary.manufacturing.mboms.by_plant_code || [];
  const mbomPlantRow = mbomByPlant.find((r) => r.plant_code === plantCode);
  expect(mbomPlantRow).toBeTruthy();
  expect(mbomPlantRow.count).toBeGreaterThanOrEqual(1);

  const routingByPlant = summary.manufacturing.routings.by_plant_code || [];
  const routingPlantRow = routingByPlant.find((r) => r.plant_code === plantCode);
  expect(routingPlantRow).toBeTruthy();
  expect(routingPlantRow.count).toBeGreaterThanOrEqual(1);
});
