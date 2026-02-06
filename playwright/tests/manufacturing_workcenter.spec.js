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
  return data.id;
}

test('WorkCenter CRUD API skeleton', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();
  const code = `WC-${ts}`;

  const createResp = await request.post('/api/v1/workcenters', {
    headers,
    data: {
      code,
      name: 'Assembly Center',
      plant_code: 'PLANT-A',
      capacity_per_day: 10,
      efficiency: 0.95,
    },
  });
  expect(createResp.ok()).toBeTruthy();
  const created = await createResp.json();
  expect(created.id).toBeTruthy();
  expect(created.code).toBe(code);
  expect(created.is_active).toBeTruthy();

  const getResp = await request.get(`/api/v1/workcenters/${created.id}`, { headers });
  expect(getResp.ok()).toBeTruthy();
  const loaded = await getResp.json();
  expect(loaded.code).toBe(code);
  expect(loaded.plant_code).toBe('PLANT-A');

  const updateResp = await request.patch(`/api/v1/workcenters/${created.id}`, {
    headers,
    data: {
      name: 'Assembly Center Updated',
      is_active: false,
      machine_count: 2,
    },
  });
  expect(updateResp.ok()).toBeTruthy();
  const updated = await updateResp.json();
  expect(updated.name).toBe('Assembly Center Updated');
  expect(updated.is_active).toBeFalsy();
  expect(updated.machine_count).toBe(2);

  const activeListResp = await request.get('/api/v1/workcenters', { headers });
  expect(activeListResp.ok()).toBeTruthy();
  const activeItems = await activeListResp.json();
  expect(activeItems.some((x) => x.id === created.id)).toBeFalsy();

  const allListResp = await request.get('/api/v1/workcenters?include_inactive=true', {
    headers,
  });
  expect(allListResp.ok()).toBeTruthy();
  const allItems = await allListResp.json();
  expect(allItems.some((x) => x.id === created.id)).toBeTruthy();
});

test('Routing operations validate workcenter association', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();
  const activeCode = `WC-ACT-${ts}`;
  const inactiveCode = `WC-INACT-${ts}`;

  const activeResp = await request.post('/api/v1/workcenters', {
    headers,
    data: { code: activeCode, name: 'Active Cell', is_active: true },
  });
  expect(activeResp.ok()).toBeTruthy();
  const activeWC = await activeResp.json();

  const inactiveCreateResp = await request.post('/api/v1/workcenters', {
    headers,
    data: { code: inactiveCode, name: 'Inactive Cell', is_active: true },
  });
  expect(inactiveCreateResp.ok()).toBeTruthy();
  const inactiveWC = await inactiveCreateResp.json();

  const deactivateResp = await request.patch(`/api/v1/workcenters/${inactiveWC.id}`, {
    headers,
    data: { is_active: false },
  });
  expect(deactivateResp.ok()).toBeTruthy();

  const partId = await createPart(request, headers, `RTG-P-${ts}`, 'Routing Part');
  const routingResp = await request.post('/api/v1/routings', {
    headers,
    data: {
      name: `Routing-${ts}`,
      item_id: partId,
    },
  });
  expect(routingResp.ok()).toBeTruthy();
  const routing = await routingResp.json();
  expect(routing.id).toBeTruthy();

  const okOpResp = await request.post(`/api/v1/routings/${routing.id}/operations`, {
    headers,
    data: {
      operation_number: '10',
      name: 'Cut',
      workcenter_id: activeWC.id,
    },
  });
  expect(okOpResp.ok()).toBeTruthy();
  const okOp = await okOpResp.json();
  expect(okOp.workcenter_id).toBe(activeWC.id);
  expect(okOp.workcenter_code).toBe(activeCode);

  const mismatchResp = await request.post(`/api/v1/routings/${routing.id}/operations`, {
    headers,
    data: {
      operation_number: '20',
      name: 'Assemble',
      workcenter_id: activeWC.id,
      workcenter_code: 'WC-MISMATCH',
    },
  });
  expect(mismatchResp.status()).toBe(400);
  const mismatchBody = await mismatchResp.json();
  expect((mismatchBody.detail || '').includes('id/code mismatch')).toBeTruthy();

  const inactiveOpResp = await request.post(`/api/v1/routings/${routing.id}/operations`, {
    headers,
    data: {
      operation_number: '30',
      name: 'Inspect',
      workcenter_code: inactiveCode,
    },
  });
  expect(inactiveOpResp.status()).toBe(400);
  const inactiveBody = await inactiveOpResp.json();
  expect((inactiveBody.detail || '').includes('inactive')).toBeTruthy();
});
