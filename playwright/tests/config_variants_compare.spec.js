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
  return data.id;
}

test('Config compare: selection differences + BOM differences', async ({ request }) => {
  const { headers } = await login(request);
  const ts = Date.now();

  // Create a simple BOM where a variant rule can modify quantity.
  const parent = await createPart(request, headers, `CFG-P-${ts}`, 'Config Parent');
  const child = await createPart(request, headers, `CFG-C-${ts}`, 'Config Child');

  const addChildResp = await request.post(`/api/v1/bom/${parent}/children`, {
    headers,
    data: { child_id: child, quantity: 1, uom: 'EA' },
  });
  expect(addChildResp.ok()).toBeTruthy();

  // Create a unique option set and options, so reusing an existing server/DB won't collide.
  const colorKey = `Color_${ts}`;
  const osResp = await request.post('/api/v1/config/option-sets', {
    headers,
    data: {
      name: colorKey,
      label: colorKey,
      value_type: 'string',
      allow_multiple: false,
      is_required: false,
      is_active: true,
    },
  });
  expect(osResp.ok()).toBeTruthy();
  const optionSet = await osResp.json();
  expect(optionSet.id).toBeTruthy();

  const optRedResp = await request.post(`/api/v1/config/option-sets/${optionSet.id}/options`, {
    headers,
    data: { key: 'Red', value: 'Red', label: 'Red', is_active: true },
  });
  expect(optRedResp.ok()).toBeTruthy();

  const optBlueResp = await request.post(`/api/v1/config/option-sets/${optionSet.id}/options`, {
    headers,
    data: { key: 'Blue', value: 'Blue', label: 'Blue', is_active: true },
  });
  expect(optBlueResp.ok()).toBeTruthy();

  // Variant rule: when Color=Red, multiply quantity of the child by 2.
  const ruleResp = await request.post('/api/v1/config/variant-rules', {
    headers,
    data: {
      name: `PW-VR-${ts}`,
      parent_item_id: parent,
      condition: { option: colorKey, value: 'Red' },
      action_type: 'modify_qty',
      target_item_id: child,
      action_params: { quantity_multiplier: 2.0 },
      priority: 100,
      is_active: true,
    },
  });
  expect(ruleResp.ok()).toBeTruthy();

  const selRed = { [colorKey]: 'Red' };
  const selBlue = { [colorKey]: 'Blue' };

  // Sanity check effective BOM results reflect the rule.
  const effRedResp = await request.post('/api/v1/config/effective-bom', {
    headers,
    data: { product_item_id: parent, selections: selRed, levels: 1 },
  });
  expect(effRedResp.ok()).toBeTruthy();
  const effRed = await effRedResp.json();
  expect(effRed.children.length).toBe(1);
  expect(Number(effRed.children[0].relationship.properties.quantity)).toBe(2);

  const effBlueResp = await request.post('/api/v1/config/effective-bom', {
    headers,
    data: { product_item_id: parent, selections: selBlue, levels: 1 },
  });
  expect(effBlueResp.ok()).toBeTruthy();
  const effBlue = await effBlueResp.json();
  expect(effBlue.children.length).toBe(1);
  expect(Number(effBlue.children[0].relationship.properties.quantity)).toBe(1);

  // Save configurations and compare.
  const cfgRedResp = await request.post('/api/v1/config/configurations', {
    headers,
    data: {
      product_item_id: parent,
      name: `CFG-RED-${ts}`,
      selections: selRed,
    },
  });
  expect(cfgRedResp.ok()).toBeTruthy();
  const cfgRed = await cfgRedResp.json();
  expect(cfgRed.id).toBeTruthy();

  const cfgBlueResp = await request.post('/api/v1/config/configurations', {
    headers,
    data: {
      product_item_id: parent,
      name: `CFG-BLUE-${ts}`,
      selections: selBlue,
    },
  });
  expect(cfgBlueResp.ok()).toBeTruthy();
  const cfgBlue = await cfgBlueResp.json();
  expect(cfgBlue.id).toBeTruthy();

  const compareResp = await request.post('/api/v1/config/configurations/compare', {
    headers,
    data: {
      config_id_a: cfgRed.id,
      config_id_b: cfgBlue.id,
      levels: 1,
    },
  });
  expect(compareResp.ok()).toBeTruthy();
  const compare = await compareResp.json();

  expect(compare.selection_differences).toEqual([
    { option: colorKey, config_a: 'Red', config_b: 'Blue' },
  ]);

  const bomDiff = compare.bom_differences;
  expect(bomDiff.summary.added).toBe(0);
  expect(bomDiff.summary.removed).toBe(0);
  expect(bomDiff.summary.changed).toBe(1);
  expect(bomDiff.summary.changed_major).toBe(1);

  expect(bomDiff.changed.length).toBe(1);
  expect(Number(bomDiff.changed[0].before_line.quantity)).toBe(2);
  expect(Number(bomDiff.changed[0].after_line.quantity)).toBe(1);
});

