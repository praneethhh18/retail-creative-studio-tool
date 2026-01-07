import { test, expect } from '@playwright/test';

test.describe('Retail Creative Tool', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the application', async ({ page }) => {
    // Check that main components are visible
    await expect(page.getByText('Retail Creative Tool')).toBeVisible();
    await expect(page.getByText('Asset Library')).toBeVisible();
    await expect(page.getByText('Validator')).toBeVisible();
  });

  test('should have channel selector', async ({ page }) => {
    const channelSelect = page.getByRole('combobox');
    await expect(channelSelect).toBeVisible();
    
    // Check options
    await channelSelect.click();
    await expect(page.getByText('Facebook Feed')).toBeVisible();
    await expect(page.getByText('Instagram Feed')).toBeVisible();
    await expect(page.getByText('Instagram Story')).toBeVisible();
  });

  test('should have upload zones', async ({ page }) => {
    await expect(page.getByText('Drop Packshot here or browse')).toBeVisible();
    await expect(page.getByText('Drop Logo here or browse')).toBeVisible();
    await expect(page.getByText('Drop Background here or browse')).toBeVisible();
  });

  test('should have toolbar buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /generate/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /validate/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /export/i })).toBeVisible();
  });

  test('should show export dialog on click', async ({ page }) => {
    await page.getByRole('button', { name: /export/i }).click();
    await expect(page.getByText('Export Creative')).toBeVisible();
    await expect(page.getByText('Select Channels')).toBeVisible();
  });

  test('should change channel', async ({ page }) => {
    const channelSelect = page.getByRole('combobox');
    await channelSelect.selectOption('instagram_story');
    
    // Verify selection changed
    await expect(channelSelect).toHaveValue('instagram_story');
  });

  test('should have undo/redo buttons', async ({ page }) => {
    const undoButton = page.getByTitle('Undo (Ctrl+Z)');
    const redoButton = page.getByTitle('Redo (Ctrl+Y)');
    
    await expect(undoButton).toBeVisible();
    await expect(redoButton).toBeVisible();
  });
});

test.describe('Asset Upload Flow', () => {
  test('should show upload dropzone', async ({ page }) => {
    await page.goto('/');
    
    const dropzone = page.locator('.dropzone').first();
    await expect(dropzone).toBeVisible();
  });
});

test.describe('Export Dialog', () => {
  test('should allow channel selection', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /export/i }).click();
    
    // Select multiple channels
    const facebookOption = page.getByText('Facebook Feed').locator('..');
    await facebookOption.click();
    
    const instagramOption = page.getByText('Instagram Feed').locator('..');
    await instagramOption.click();
  });

  test('should close on cancel', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /export/i }).click();
    
    await expect(page.getByText('Export Creative')).toBeVisible();
    
    await page.getByRole('button', { name: /cancel/i }).click();
    
    await expect(page.getByText('Export Creative')).not.toBeVisible();
  });
});
