const { test, expect } = require('@playwright/test');

test.describe('CAD material Workbench UI', () => {
  test('renders structured config controls and updates draft JSON locally', async ({ page }) => {
    await page.goto('/api/v1/workbench');

    await expect(page.locator('#section-cad-material')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'CAD Material Profiles' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Structured Rule Builder' })).toBeVisible();

    await page.locator('#cad-material-field-name').fill('length');
    await page.locator('#cad-material-field-label').fill('长');
    await page.locator('#cad-material-field-type').selectOption('number');
    await page.locator('#cad-material-field-cad-key').fill('长');
    await page.locator('#cad-material-field-unit').fill('mm');
    await page.locator('#cad-material-field-display-precision').fill('0');
    await page.getByRole('button', { name: 'Upsert field' }).click();

    await expect(page.locator('#cad-material-config')).toHaveValue(/"fields"/);
    await expect(page.locator('#cad-material-config')).toHaveValue(/"cad_key": "长"/);

    await page.locator('#cad-material-compose-template').fill('{length}*{width}*{thickness}');
    await expect(page.locator('#cad-material-compose-preview')).toHaveText('1200*600*12');
    await page.getByRole('button', { name: 'Set template' }).click();
    await expect(page.locator('#cad-material-config')).toHaveValue(/"template": "\{length\}\*\{width\}\*\{thickness\}"/);

    await page.locator('#cad-material-match-fields').fill('material_category,material,specification');
    await page.locator('#cad-material-overwrite-default').selectOption('true');
    await page.getByRole('button', { name: 'Set matching' }).click();

    await expect(page.locator('#cad-material-config')).toHaveValue(/"matching"/);
    await expect(page.locator('#cad-material-config')).toHaveValue(/"sync_defaults"/);
    await expect(page.locator('#cad-material-config')).toHaveValue(/"overwrite": true/);

    await expect(page.getByRole('heading', { name: 'CAD Write Confirmation' })).toBeVisible();
    await page.locator('#cad-material-write-fields').fill('{"规格":"1200*600*12"}');
    await page.getByRole('button', { name: 'Confirm write package' }).click();
    await expect(page.locator('#action-status')).toHaveText('CAD write package confirmed');
  });
});
