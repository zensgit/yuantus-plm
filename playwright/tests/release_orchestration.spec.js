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
      auto_populate: false,
      max_levels: 0,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const baseline = await resp.json();
  expect(baseline.id).toBeTruthy();
  return baseline.id;
}

test('Release orchestration plan + execute (baseline-only) works', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `ORCH-${ts}`, 'Orchestration Part');
  const baselineId = await createBaseline(request, headers, partId, `BL-${ts}`);

  const planResp = await request.get(`/api/v1/release-orchestration/items/${partId}/plan`, {
    headers,
  });
  expect(planResp.ok()).toBeTruthy();
  const plan = await planResp.json();
  expect(plan.item_id).toBe(partId);
  expect(plan.readiness.item_id).toBe(partId);

  const steps = plan.steps || [];
  expect(steps.length).toBeGreaterThan(0);
  const baselineStep = steps.find(
    (s) => s.kind === 'baseline_release' && s.resource_id === baselineId
  );
  expect(baselineStep).toBeTruthy();

  const execResp = await request.post(`/api/v1/release-orchestration/items/${partId}/execute`, {
    headers,
    data: {
      include_routings: false,
      include_mboms: false,
      include_baselines: true,
      ruleset_id: 'default',
    },
  });
  expect(execResp.ok()).toBeTruthy();
  const execData = await execResp.json();
  const results = execData.results || [];
  const baselineResult = results.find(
    (r) => r.kind === 'baseline_release' && r.resource_id === baselineId
  );
  expect(baselineResult).toBeTruthy();
  expect(baselineResult.status).toBe('executed');
  expect(String(baselineResult.state_after || '')).toContain('released');

  // Baseline state should now be released.
  const baselineGet = await request.get(`/api/v1/baselines/${baselineId}`, { headers });
  expect(baselineGet.ok()).toBeTruthy();
  const baseline = await baselineGet.json();
  expect(String(baseline.state || '')).toContain('released');
});

