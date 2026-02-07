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
      },
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  expect(data.id).toBeTruthy();
  return data.id;
}

async function createBaseline(request, headers, rootItemId, name) {
  const resp = await request.post('/api/v1/baselines', {
    headers,
    data: {
      name,
      root_item_id: rootItemId,
      // Keep the baseline small and stable for regression runs.
      auto_populate: false,
      max_levels: 0,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const baseline = await resp.json();
  expect(baseline.id).toBeTruthy();
  return baseline.id;
}

async function assertZipDownload(resp, expectedFilename) {
  expect(resp.ok()).toBeTruthy();
  const headers = resp.headers();
  expect(String(headers['content-type'] || '')).toContain('application/zip');
  expect(String(headers['content-disposition'] || '')).toContain(expectedFilename);

  const body = await resp.body();
  expect(body.length).toBeGreaterThan(8);
  // ZIP local file header signature.
  expect(body[0]).toBe(0x50);
  expect(body[1]).toBe(0x4b);
}

test('Export bundles (impact/readiness/cockpit) + baseline release-diagnostics are reachable', async ({
  request,
}) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `EXP-${ts}`, 'Export Bundle Part');
  const baselineId = await createBaseline(request, headers, partId, `BL-${ts}`);

  const diagResp = await request.get(`/api/v1/baselines/${baselineId}/release-diagnostics`, {
    headers,
  });
  expect(diagResp.ok()).toBeTruthy();
  const diag = await diagResp.json();
  expect(diag.resource_type).toBe('baseline');
  expect(diag.resource_id).toBe(baselineId);
  expect(Array.isArray(diag.errors)).toBeTruthy();
  expect(diag.errors.length).toBe(0);

  const impactZip = await request.get(
    `/api/v1/impact/items/${partId}/summary/export?export_format=zip`,
    { headers }
  );
  await assertZipDownload(impactZip, `impact-summary-${partId}.zip`);

  const readinessZip = await request.get(
    `/api/v1/release-readiness/items/${partId}/export?export_format=zip`,
    { headers }
  );
  await assertZipDownload(readinessZip, `release-readiness-${partId}.zip`);

  const cockpitZip = await request.get(
    `/api/v1/items/${partId}/cockpit/export?export_format=zip`,
    { headers }
  );
  await assertZipDownload(cockpitZip, `item-cockpit-${partId}.zip`);
});

