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

async function createPart(request, headers, number, name, extra = {}) {
  const resp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'add',
      properties: {
        item_number: number,
        name,
        ...extra,
      },
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  return data.id;
}

test('Product UI summaries include obsolete + weight rollup', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const parent = await createPart(request, headers, `PROD-UI-P-${ts}`, 'Product UI Parent');
  const child = await createPart(request, headers, `PROD-UI-C-${ts}`, 'Product UI Child', {
    weight: 2.0,
  });
  const obsChild = await createPart(
    request,
    headers,
    `PROD-UI-OBS-${ts}`,
    'Product UI Obsolete',
    { weight: 1.5, obsolete: true }
  );

  const addResp = await request.post(`/api/v1/bom/${parent}/children`, {
    headers,
    data: { child_id: child, quantity: 1, uom: 'EA' },
  });
  expect(addResp.ok()).toBeTruthy();

  const addObsResp = await request.post(`/api/v1/bom/${parent}/children`, {
    headers,
    data: { child_id: obsChild, quantity: 2, uom: 'EA' },
  });
  expect(addObsResp.ok()).toBeTruthy();

  const detailResp = await request.get(
    `/api/v1/products/${parent}` +
      '?include_versions=false&include_files=false' +
      '&include_bom_summary=true' +
      '&include_bom_obsolete_summary=true' +
      '&include_bom_weight_rollup=true' +
      '&bom_weight_levels=1',
    { headers }
  );
  expect(detailResp.ok()).toBeTruthy();
  const detail = await detailResp.json();

  const obsoleteSummary = detail.bom_obsolete_summary || {};
  expect(obsoleteSummary.authorized).toBeTruthy();
  expect(obsoleteSummary.count).toBe(1);
  const sample = obsoleteSummary.sample || [];
  expect(sample.length).toBeGreaterThan(0);
  expect(sample.some((entry) => entry.child_id === obsChild)).toBeTruthy();

  const rollup = detail.bom_weight_rollup_summary || {};
  expect(rollup.authorized).toBeTruthy();
  const totalWeight = Number(rollup.total_weight);
  expect(totalWeight).toBeCloseTo(5.0, 6);

  const cockpitResp = await request.get(
    `/api/v1/products/${parent}` +
      '?include_versions=false&include_files=false' +
      '&include_release_readiness_summary=true' +
      '&release_readiness_ruleset_id=readiness',
    { headers }
  );
  expect(cockpitResp.ok()).toBeTruthy();
  const cockpit = await cockpitResp.json();
  const readiness = cockpit.release_readiness_summary || {};
  expect(readiness.authorized).toBeTruthy();
  expect(readiness.links && readiness.links.export).toContain(
    `/api/v1/release-readiness/items/${parent}/export`
  );
});
