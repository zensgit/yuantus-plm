const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { test, expect } = require('@playwright/test');

const shouldRun = process.env.RUN_PLAYWRIGHT_CAD_PREVIEW === '1';
const skipBrowser = process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD === '1';
const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:7910';

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
  const loginData = await loginResp.json();
  const token = loginData.access_token;
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

function ensurePreview(fileId) {
  const python = process.env.PY || path.join(process.cwd(), '.venv', 'bin', 'python');
  const scriptPath = path.join(process.cwd(), 'scripts', 'run_cad_preview_direct.py');
  const dbUrl =
    process.env.PLAYWRIGHT_DB_URL ||
    process.env.YUANTUS_DATABASE_URL ||
    'sqlite:////tmp/yuantus_playwright.db';

  const env = {
    ...process.env,
    FILE_ID: fileId,
    TENANT: 'tenant-1',
    ORG: 'org-1',
    YUANTUS_TENANCY_MODE: 'single',
    YUANTUS_SCHEMA_MODE: 'create_all',
    YUANTUS_DATABASE_URL: dbUrl,
    YUANTUS_IDENTITY_DATABASE_URL: dbUrl,
    YUANTUS_DATABASE_URL_TEMPLATE: '',
  };
  execFileSync(python, [scriptPath], { env, stdio: 'inherit' });
}

test.describe('CAD preview browser render', () => {
  test.skip(!shouldRun, 'RUN_PLAYWRIGHT_CAD_PREVIEW=1 required');
  test.skip(skipBrowser, 'Browser not available when PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1');

  test('renders preview image in browser', async ({ request, page }) => {
    const samplePath =
      process.env.CAD_PREVIEW_SAMPLE_FILE ||
      path.join(process.cwd(), 'docs', 'samples', 'cad_ml_preview_sample.dxf');
    expect(fs.existsSync(samplePath)).toBeTruthy();

    const { headers } = await login(request);
    const importResp = await request.post('/api/v1/cad/import', {
      headers,
      multipart: {
        file: {
          name: path.basename(samplePath),
          mimeType: 'application/dxf',
          buffer: fs.readFileSync(samplePath),
        },
        create_preview_job: 'false',
        create_geometry_job: 'false',
        create_dedup_job: 'false',
        create_ml_job: 'false',
        create_extract_job: 'false',
      },
    });
    expect(importResp.ok()).toBeTruthy();
    const importData = await importResp.json();
    const fileId = importData.file_id;
    expect(fileId).toBeTruthy();

    ensurePreview(fileId);

    const response = await page.goto(`${BASE_URL}/api/v1/file/${fileId}/preview`);
    expect(response).toBeTruthy();
    expect(response.ok()).toBeTruthy();
    const contentType = (response.headers()['content-type'] || '').toLowerCase();
    expect(contentType).toContain('image');
  });
});
