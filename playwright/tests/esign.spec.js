const { test, expect } = require('@playwright/test');

test('e-sign end-to-end: reason, manifest, sign, verify, revoke', async ({ request }) => {
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

  const headers = {
    Authorization: `Bearer ${token}`,
    'x-tenant-id': 'tenant-1',
    'x-org-id': 'org-1',
  };

  const reasonResp = await request.post('/api/v1/esign/reasons', {
    headers,
    data: {
      code: `APPROVE-${Date.now()}`,
      name: 'Release Approval',
      meaning: 'approved',
      requires_password: true,
      requires_comment: true,
      item_type_id: 'Part',
      sequence: 1,
    },
  });
  expect(reasonResp.ok()).toBeTruthy();
  const reason = await reasonResp.json();
  expect(reason.id).toBeTruthy();

  const amlResp = await request.post('/api/v1/aml/apply', {
    headers,
    data: {
      type: 'Part',
      action: 'add',
      properties: {
        item_number: `ESIGN-${Date.now()}`,
        name: 'E-Sign Test Part',
        revision: 'A',
        state: 'Draft',
      },
    },
  });
  expect(amlResp.ok()).toBeTruthy();
  const aml = await amlResp.json();
  const itemId = aml.id || (aml.items && aml.items[0] && aml.items[0].id);
  expect(itemId).toBeTruthy();

  const manifestResp = await request.post('/api/v1/esign/manifests', {
    headers,
    data: {
      item_id: itemId,
      generation: 1,
      required_signatures: [
        { meaning: 'approved', role: 'admin', required: true },
      ],
    },
  });
  expect(manifestResp.ok()).toBeTruthy();

  const signResp = await request.post('/api/v1/esign/sign', {
    headers,
    data: {
      item_id: itemId,
      meaning: 'approved',
      reason_id: reason.id,
      comment: 'release approved',
      password: 'admin',
    },
  });
  expect(signResp.ok()).toBeTruthy();
  const signature = await signResp.json();
  expect(signature.id).toBeTruthy();
  expect(signature.status).toBe('valid');

  const verifyResp = await request.post(`/api/v1/esign/verify/${signature.id}`, {
    headers,
  });
  expect(verifyResp.ok()).toBeTruthy();
  const verify = await verifyResp.json();
  expect(verify.is_valid).toBeTruthy();

  const manifestStatusResp = await request.get(
    `/api/v1/esign/manifests/${itemId}?generation=1`,
    { headers }
  );
  expect(manifestStatusResp.ok()).toBeTruthy();
  const manifestStatus = await manifestStatusResp.json();
  expect(manifestStatus.is_complete).toBeTruthy();

  const revokeResp = await request.post(`/api/v1/esign/revoke/${signature.id}`, {
    headers,
    data: { reason: 'test revoke' },
  });
  expect(revokeResp.ok()).toBeTruthy();

  const listResp = await request.get(
    `/api/v1/esign/items/${itemId}/signatures?include_revoked=true`,
    { headers }
  );
  expect(listResp.ok()).toBeTruthy();
  const list = await listResp.json();
  expect(list.items.length).toBeGreaterThan(0);
});
