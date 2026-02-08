const { defineConfig } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:7910';

module.exports = defineConfig({
  testDir: './playwright/tests',
  timeout: 60000,
  retries: 0,
  use: {
    baseURL: BASE_URL,
  },
  webServer: {
    command:
      "bash -lc '" +
      [
        'export PYTHONPATH=src',
        'export YUANTUS_TENANCY_MODE=single',
        'export YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_playwright.db',
        'export YUANTUS_IDENTITY_DATABASE_URL=sqlite:////tmp/yuantus_playwright.db',
        'export YUANTUS_TEST_FAILPOINTS_ENABLED=true',
        'rm -f /tmp/yuantus_playwright.db',
        './.venv/bin/yuantus seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin',
        './.venv/bin/yuantus seed-meta',
        './.venv/bin/uvicorn yuantus.api.app:app --host 127.0.0.1 --port 7910',
      ].join(' && ') +
      "'",
    url: `${BASE_URL}/api/v1/health`,
    reuseExistingServer: true,
    timeout: 120000,
  },
});
