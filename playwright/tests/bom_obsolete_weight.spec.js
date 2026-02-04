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

async function markObsolete(request, headers, id) {
  const resp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'update',
      id,
      properties: { engineering_state: 'obsoleted', obsolete: true },
    },
  });
  expect(resp.ok()).toBeTruthy();
}

test('BOM obsolete scan + resolve', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const parent = await createPart(request, headers, `OBS-P-${ts}`, 'Obsolete Parent');
  const childOld = await createPart(request, headers, `OBS-O-${ts}`, 'Obsolete Child');
  const childNew = await createPart(request, headers, `OBS-N-${ts}`, 'Replacement Child');

  await markObsolete(request, headers, childOld);

  const updateResp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'update',
      id: childOld,
      properties: { replacement_id: childNew },
    },
  });
  expect(updateResp.ok()).toBeTruthy();

  const addResp = await request.post(`/api/v1/bom/${parent}/children`, {
    headers,
    data: { child_id: childOld, quantity: 1 },
  });
  expect(addResp.ok()).toBeTruthy();

  const scanResp = await request.get(`/api/v1/bom/${parent}/obsolete`, { headers });
  expect(scanResp.ok()).toBeTruthy();
  const scan = await scanResp.json();
  expect(scan.count).toBe(1);
  expect(scan.entries[0].replacement_id).toBe(childNew);

  const resolveResp = await request.post(`/api/v1/bom/${parent}/obsolete/resolve`, {
    headers,
    data: { mode: 'update' },
  });
  expect(resolveResp.ok()).toBeTruthy();
  const resolve = await resolveResp.json();
  expect(resolve.summary.updated_lines).toBe(1);

  const scanAfterResp = await request.get(`/api/v1/bom/${parent}/obsolete`, { headers });
  const scanAfter = await scanAfterResp.json();
  expect(scanAfter.count).toBe(0);

  const treeResp = await request.get(`/api/v1/bom/${parent}/tree?depth=1`, { headers });
  expect(treeResp.ok()).toBeTruthy();
  const tree = await treeResp.json();
  const childId = tree.children[0].child.id;
  expect(childId).toBe(childNew);
});

test('BOM weight rollup + write_back', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const parent = await createPart(request, headers, `ROLL-P-${ts}`, 'Rollup Parent');
  const child1 = await createPart(request, headers, `ROLL-C1-${ts}`, 'Child 1', {
    weight: 2.5,
  });
  const child2 = await createPart(request, headers, `ROLL-C2-${ts}`, 'Child 2', {
    weight: 1.0,
  });

  const addResp1 = await request.post(`/api/v1/bom/${parent}/children`, {
    headers,
    data: { child_id: child1, quantity: 2 },
  });
  expect(addResp1.ok()).toBeTruthy();

  const addResp2 = await request.post(`/api/v1/bom/${parent}/children`, {
    headers,
    data: { child_id: child2, quantity: 3 },
  });
  expect(addResp2.ok()).toBeTruthy();

  const rollupResp = await request.post(`/api/v1/bom/${parent}/rollup/weight`, {
    headers,
    data: {
      write_back: true,
      write_back_field: 'weight_rollup',
      write_back_mode: 'missing',
      rounding: 3,
    },
  });
  expect(rollupResp.ok()).toBeTruthy();
  const rollup = await rollupResp.json();
  expect(rollup.summary.total_weight).toBeCloseTo(8.0, 6);

  const getResp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'get',
      id: parent,
    },
  });
  expect(getResp.ok()).toBeTruthy();
  const item = await getResp.json();
  expect(item.items[0].properties.weight_rollup).toBeCloseTo(8.0, 6);
});
