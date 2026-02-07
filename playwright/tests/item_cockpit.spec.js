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

test('Item cockpit returns impact + readiness + open ECOs + links', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `COCKPIT-${ts}`, 'Cockpit Part');

  const resp = await request.get(`/api/v1/items/${partId}/cockpit`, { headers });
  expect(resp.ok()).toBeTruthy();

  const data = await resp.json();
  expect(data.item.id).toBe(partId);
  expect(data.impact_summary.item_id).toBe(partId);
  expect(data.release_readiness.item_id).toBe(partId);
  expect(data.open_ecos).toBeTruthy();

  const links = data.links || {};
  expect(String(links.impact_export || '')).toContain(
    `/api/v1/impact/items/${partId}/summary/export`
  );
  expect(String(links.release_readiness_export || '')).toContain(
    `/api/v1/release-readiness/items/${partId}/export`
  );
});

