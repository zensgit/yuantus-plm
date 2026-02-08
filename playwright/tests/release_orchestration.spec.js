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

async function addBomChild(request, headers, parentId, childId) {
  const resp = await request.post(`/api/v1/bom/${parentId}/children`, {
    headers,
    data: { child_id: childId, quantity: 1, uom: 'EA' },
  });
  expect(resp.ok()).toBeTruthy();
  return await resp.json();
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
  const wc = await resp.json();
  expect(wc.id).toBeTruthy();
  return wc.id;
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
  return op.id;
}

async function listMbomsBySource(request, headers, sourceItemId) {
  const resp = await request.get(
    `/api/v1/mboms?source_item_id=${encodeURIComponent(sourceItemId)}`,
    { headers }
  );
  expect(resp.ok()).toBeTruthy();
  return await resp.json();
}

async function createManifest(request, headers, itemId, generation) {
  const resp = await request.post('/api/v1/esign/manifests', {
    headers,
    data: {
      item_id: itemId,
      generation,
      required_signatures: [{ meaning: 'approved', role: 'admin', required: true }],
    },
  });
  expect(resp.ok()).toBeTruthy();
  return await resp.json();
}

async function signApproved(request, headers, itemId) {
  const resp = await request.post('/api/v1/esign/sign', {
    headers,
    data: {
      item_id: itemId,
      meaning: 'approved',
      reason_text: 'release approved',
      comment: 'ok',
    },
  });
  expect(resp.ok()).toBeTruthy();
  return await resp.json();
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

test('Release orchestration baseline is gated by e-sign manifest completeness', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `ORCH-ESIGN-${ts}`, 'Orchestration E-sign Gate Part');
  const baselineId = await createBaseline(request, headers, partId, `BL-ESIGN-${ts}`);

  await createManifest(request, headers, partId, 1);

  const planResp = await request.get(`/api/v1/release-orchestration/items/${partId}/plan`, { headers });
  expect(planResp.ok()).toBeTruthy();
  const plan = await planResp.json();
  const baselineStep = (plan.steps || []).find(
    (s) => s.kind === 'baseline_release' && s.resource_id === baselineId
  );
  expect(baselineStep).toBeTruthy();
  expect(baselineStep.action).toBe('requires_esign');

  const execBlocked = await request.post(`/api/v1/release-orchestration/items/${partId}/execute`, {
    headers,
    data: {
      include_routings: false,
      include_mboms: false,
      include_baselines: true,
      ruleset_id: 'default',
    },
  });
  expect(execBlocked.ok()).toBeTruthy();
  const blockedData = await execBlocked.json();
  const blockedResult = (blockedData.results || []).find(
    (r) => r.kind === 'baseline_release' && r.resource_id === baselineId
  );
  expect(blockedResult).toBeTruthy();
  expect(blockedResult.status).toBe('blocked_esign_incomplete');

  await signApproved(request, headers, partId);

  const execAfterSign = await request.post(`/api/v1/release-orchestration/items/${partId}/execute`, {
    headers,
    data: {
      include_routings: false,
      include_mboms: false,
      include_baselines: true,
      ruleset_id: 'default',
    },
  });
  expect(execAfterSign.ok()).toBeTruthy();
  const execData = await execAfterSign.json();
  const baselineResult = (execData.results || []).find(
    (r) => r.kind === 'baseline_release' && r.resource_id === baselineId
  );
  expect(baselineResult).toBeTruthy();
  expect(baselineResult.status).toBe('executed');
  expect(String(baselineResult.state_after || '')).toContain('released');
});

test('Release orchestration rolls back routing+mbom when baseline is blocked by e-sign', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const parentId = await createPart(request, headers, `ORCH-RB-P-${ts}`, 'Orchestration Rollback Parent');
  const childId = await createPart(request, headers, `ORCH-RB-C-${ts}`, 'Orchestration Rollback Child');
  await addBomChild(request, headers, parentId, childId);

  const baselineId = await createBaseline(request, headers, parentId, `BL-RB-${ts}`);

  const mbom = await createMbomFromEbom(request, headers, parentId, `MBOM-RB-${ts}`);
  const workcenterId = await createWorkcenter(request, headers, `WC-RB-${ts}`, `WorkCenter RB ${ts}`);
  const routing = await createRouting(request, headers, mbom.id, parentId, `Routing RB ${ts}`);
  await addRoutingOperation(request, headers, routing.id, workcenterId);

  // Create an e-sign manifest but do not sign; baseline release should be blocked.
  await createManifest(request, headers, parentId, 1);

  const execResp = await request.post(`/api/v1/release-orchestration/items/${parentId}/execute`, {
    headers,
    data: {
      ruleset_id: 'default',
      include_routings: true,
      include_mboms: true,
      include_baselines: true,
      rollback_on_failure: true,
      // Keep the test stable even if baseline diagnostics become stricter.
      baseline_force: true,
    },
  });
  expect(execResp.ok()).toBeTruthy();
  const execData = await execResp.json();
  const results = execData.results || [];

  const routingRelease = results.find((r) => r.kind === 'routing_release' && r.resource_id === routing.id);
  expect(routingRelease).toBeTruthy();
  expect(routingRelease.status).toBe('executed');

  const mbomRelease = results.find((r) => r.kind === 'mbom_release' && r.resource_id === mbom.id);
  expect(mbomRelease).toBeTruthy();
  expect(mbomRelease.status).toBe('executed');

  const baselineResult = results.find((r) => r.kind === 'baseline_release' && r.resource_id === baselineId);
  expect(baselineResult).toBeTruthy();
  expect(baselineResult.status).toBe('blocked_esign_incomplete');

  // Rollback steps are appended after abort.
  const mbomRollback = results.find((r) => r.kind === 'mbom_reopen' && r.resource_id === mbom.id);
  expect(mbomRollback).toBeTruthy();
  expect(mbomRollback.status).toBe('rolled_back');

  const routingRollback = results.find((r) => r.kind === 'routing_reopen' && r.resource_id === routing.id);
  expect(routingRollback).toBeTruthy();
  expect(routingRollback.status).toBe('rolled_back');

  const routingGet = await request.get(`/api/v1/routings/${routing.id}`, { headers });
  expect(routingGet.ok()).toBeTruthy();
  const routingAfter = await routingGet.json();
  expect(String(routingAfter.state || '')).toBe('draft');

  const mbomsAfter = await listMbomsBySource(request, headers, parentId);
  const mbomAfter = (mbomsAfter || []).find((m) => m.id === mbom.id);
  expect(mbomAfter).toBeTruthy();
  expect(String(mbomAfter.state || '')).toBe('draft');
});

test('Release orchestration execute rejects unknown ruleset_id (400)', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `ORCH-BADRULE-${ts}`, 'Orchestration Bad Ruleset Part');

  const execResp = await request.post(`/api/v1/release-orchestration/items/${partId}/execute`, {
    headers,
    data: {
      include_routings: false,
      include_mboms: false,
      include_baselines: true,
      ruleset_id: 'does-not-exist',
    },
  });
  expect(execResp.status()).toBe(400);
  const body = await execResp.json();
  expect(String(body.detail || '')).toContain('Unknown release ruleset');
});

test('Release orchestration execute rejects rollback_on_failure with continue_on_error=true (400)', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `ORCH-BADRB-${ts}`, 'Orchestration Bad Rollback Config Part');

  const execResp = await request.post(`/api/v1/release-orchestration/items/${partId}/execute`, {
    headers,
    data: {
      include_routings: false,
      include_mboms: false,
      include_baselines: false,
      ruleset_id: 'default',
      rollback_on_failure: true,
      continue_on_error: true,
    },
  });
  expect(execResp.status()).toBe(400);
  const body = await execResp.json();
  expect(String(body.detail || '')).toContain('rollback_on_failure requires continue_on_error=false');
});

test('Release orchestration execute dry_run does not change baseline state', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  const partId = await createPart(request, headers, `ORCH-DRY-${ts}`, 'Orchestration Dry Run Part');
  const baselineId = await createBaseline(request, headers, partId, `BL-DRY-${ts}`);

  const execResp = await request.post(`/api/v1/release-orchestration/items/${partId}/execute`, {
    headers,
    data: {
      include_routings: false,
      include_mboms: false,
      include_baselines: true,
      ruleset_id: 'default',
      dry_run: true,
    },
  });
  expect(execResp.ok()).toBeTruthy();
  const execData = await execResp.json();
  const baselineResult = (execData.results || []).find(
    (r) => r.kind === 'baseline_release' && r.resource_id === baselineId
  );
  expect(baselineResult).toBeTruthy();
  expect(baselineResult.status).toBe('planned');

  const baselineGet = await request.get(`/api/v1/baselines/${baselineId}`, { headers });
  expect(baselineGet.ok()).toBeTruthy();
  const baseline = await baselineGet.json();
  expect(String(baseline.state || '')).toBe('draft');
});
