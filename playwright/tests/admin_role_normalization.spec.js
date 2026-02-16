const { test, expect } = require('@playwright/test');

async function login(request, username, password, orgId = 'org-1') {
  const loginResp = await request.post('/api/v1/auth/login', {
    data: {
      tenant_id: 'tenant-1',
      org_id: orgId,
      username,
      password,
    },
  });
  expect(loginResp.ok()).toBeTruthy();
  const login = await loginResp.json();
  const token = login.access_token;
  expect(token).toBeTruthy();
  return token;
}

function headersFromToken(token) {
  return {
    Authorization: `Bearer ${token}`,
    'x-tenant-id': 'tenant-1',
    'x-org-id': 'org-1',
  };
}

test('Admin role normalization: superuser path + mixed-case roles export (API-only)', async ({ request }) => {
  const ts = Date.now();
  const marker = `ROLE-NORM-${ts}`;

  const adminToken = await login(request, 'admin', 'admin', 'org-1');
  const adminHeaders = headersFromToken(adminToken);

  // Fixture item used by release-orchestration plan and report query.
  const partResp = await request.post('/api/v1/aml/apply', {
    headers: adminHeaders,
    data: {
      type: 'Part',
      action: 'add',
      properties: {
        item_number: `${marker}-PART`,
        name: `${marker} Part`,
        description: marker,
      },
    },
  });
  expect(partResp.ok()).toBeTruthy();
  const part = await partResp.json();
  expect(part.id).toBeTruthy();
  const partId = part.id;

  // Create a superuser with non-admin org role; superuser should still pass
  // release/esign admin checks.
  const suUsername = `su_role_norm_${ts}`;
  const suPassword = `su-pass-${ts}`;
  const suCreateResp = await request.post('/api/v1/admin/users', {
    headers: adminHeaders,
    data: {
      username: suUsername,
      password: suPassword,
      is_superuser: true,
    },
  });
  expect(suCreateResp.ok()).toBeTruthy();
  const suUser = await suCreateResp.json();
  expect(suUser.id).toBeTruthy();

  const suMemberResp = await request.post('/api/v1/admin/orgs/org-1/members', {
    headers: adminHeaders,
    data: {
      user_id: suUser.id,
      roles: ['viewer'],
      is_active: true,
    },
  });
  expect(suMemberResp.ok()).toBeTruthy();

  const suToken = await login(request, suUsername, suPassword, 'org-1');
  const suHeaders = headersFromToken(suToken);

  const planResp = await request.get(`/api/v1/release-orchestration/items/${partId}/plan`, {
    headers: suHeaders,
  });
  expect(planResp.ok()).toBeTruthy();
  const plan = await planResp.json();
  expect(plan.item_id).toBe(partId);

  const auditSummaryResp = await request.get('/api/v1/esign/audit-summary', {
    headers: suHeaders,
  });
  expect(auditSummaryResp.ok()).toBeTruthy();
  const auditSummary = await auditSummaryResp.json();
  expect(typeof auditSummary).toBe('object');

  // Create a normal user with mixed-case/whitespace role token payload.
  const viewerUsername = `viewer_role_norm_${ts}`;
  const viewerPassword = `viewer-pass-${ts}`;
  const viewerCreateResp = await request.post('/api/v1/admin/users', {
    headers: adminHeaders,
    data: {
      username: viewerUsername,
      password: viewerPassword,
      is_superuser: false,
    },
  });
  expect(viewerCreateResp.ok()).toBeTruthy();
  const viewerUser = await viewerCreateResp.json();
  expect(viewerUser.id).toBeTruthy();

  const viewerMemberResp = await request.post('/api/v1/admin/orgs/org-1/members', {
    headers: adminHeaders,
    data: {
      user_id: viewerUser.id,
      roles: [' Viewer '],
      is_active: true,
    },
  });
  expect(viewerMemberResp.ok()).toBeTruthy();

  const reportCreateResp = await request.post('/api/v1/reports/definitions', {
    headers: adminHeaders,
    data: {
      name: `RoleNorm Report ${ts}`,
      code: `ROLE-NORM-${ts}`,
      description: 'role normalization export contract',
      category: 'test',
      report_type: 'table',
      data_source: {
        type: 'query',
        item_type_id: 'Part',
        full_text: marker,
      },
      is_public: true,
      allowed_roles: [' viewer '],
      is_active: true,
    },
  });
  expect(reportCreateResp.ok()).toBeTruthy();
  const report = await reportCreateResp.json();
  expect(report.id).toBeTruthy();
  const reportId = report.id;

  const viewerToken = await login(request, viewerUsername, viewerPassword, 'org-1');
  const viewerHeaders = headersFromToken(viewerToken);

  const exportResp = await request.post(`/api/v1/reports/definitions/${reportId}/export`, {
    headers: viewerHeaders,
    data: {
      export_format: 'csv',
      page: 1,
      page_size: 100,
    },
  });
  expect(exportResp.ok()).toBeTruthy();
  const exportDisposition = exportResp.headers()['content-disposition'] || '';
  expect(exportDisposition).toContain(`report_${reportId}.csv`);
  const csvBody = await exportResp.text();
  expect(csvBody.length).toBeGreaterThan(0);
  expect(csvBody).toContain(marker);

  // Best-effort cleanup for shared playwright DB.
  const reportDeleteResp = await request.delete(`/api/v1/reports/definitions/${reportId}`, {
    headers: adminHeaders,
  });
  expect(reportDeleteResp.ok()).toBeTruthy();
});
