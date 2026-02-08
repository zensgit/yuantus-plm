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

