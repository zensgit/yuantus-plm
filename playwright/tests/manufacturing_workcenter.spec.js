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
