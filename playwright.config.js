const { defineConfig } = require('@playwright/test');

const PORT = process.env.PORT || process.env.YUANTUS_PLAYWRIGHT_PORT || '7910';
const BASE_URL = process.env.BASE_URL || `http://127.0.0.1:${PORT}`;
const PLAYWRIGHT_DB_PATH = process.env.YUANTUS_PLAYWRIGHT_DB_PATH || '/tmp/yuantus_playwright.db';
const PLAYWRIGHT_DB_URL = `sqlite:////${PLAYWRIGHT_DB_PATH.replace(/^\/+/, '')}`;

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
        `export YUANTUS_DATABASE_URL=${PLAYWRIGHT_DB_URL}`,
        `export YUANTUS_IDENTITY_DATABASE_URL=${PLAYWRIGHT_DB_URL}`,
        'export YUANTUS_TEST_FAILPOINTS_ENABLED=true',
        `rm -f ${PLAYWRIGHT_DB_PATH}`,
        './.venv/bin/yuantus seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin',
        './.venv/bin/yuantus seed-meta',
        `./.venv/bin/uvicorn yuantus.api.app:app --host 127.0.0.1 --port ${PORT}`,
      ].join(' && ') +
      "'",
    url: `${BASE_URL}/api/v1/health`,
    reuseExistingServer: true,
    timeout: 120000,
  },
});
