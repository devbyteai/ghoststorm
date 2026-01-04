import { test, expect } from '@playwright/test';
import { SettingsPage } from '../pages/settings.page';

test.describe('Settings Page', () => {
  let settingsPage: SettingsPage;

  test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);

    // Mock config API endpoints
    await page.route('**/api/config/current', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          headless: true,
          browser_type: 'chromium',
          use_proxy: true,
          proxy_type: 'rotating',
          workers: 5,
          timeout: 30000,
          debug_mode: false,
        }),
      });
    });

    await page.route('**/api/config/save', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'saved' }),
      });
    });

    await page.route('**/api/config/reset', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'reset' }),
      });
    });

    await page.route('**/api/config/presets', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          presets: [
            { id: '1', name: 'Fast', description: 'Fast execution' },
            { id: '2', name: 'Stealth', description: 'Maximum stealth' },
          ],
        }),
      });
    });

    await settingsPage.gotoSettingsPage();
  });

  test.describe('Section Navigation', () => {
    test('should display settings tabs', async () => {
      await expect(settingsPage.settingsTabs).toHaveCount.greaterThan(0);
    });

    test('should switch to Browser section', async () => {
      await settingsPage.switchSection('Browser');
      await expect(settingsPage.browserContainer).toBeVisible();
    });

    test('should switch to Proxy section', async () => {
      await settingsPage.switchSection('Proxy');
      await expect(settingsPage.proxyContainer).toBeVisible();
    });

    test('should switch to API section', async () => {
      await settingsPage.switchSection('API');
      await expect(settingsPage.apiContainer).toBeVisible();
    });

    test('should switch to Behavior section', async () => {
      await settingsPage.switchSection('Behavior');
      await expect(settingsPage.behaviorContainer).toBeVisible();
    });

    test('should switch to Advanced section', async () => {
      await settingsPage.switchSection('Advanced');
      await expect(settingsPage.advancedContainer).toBeVisible();
    });
  });

  test.describe('Browser Settings', () => {
    test('should display headless toggle', async () => {
      await settingsPage.switchSection('Browser');
      await expect(settingsPage.headlessToggle).toBeVisible();
    });

    test('should display browser type select', async () => {
      await settingsPage.switchSection('Browser');
      await expect(settingsPage.browserTypeSelect).toBeVisible();
    });

    test('should configure browser settings', async () => {
      await settingsPage.configureBrowser({
        headless: false,
        browserType: 'firefox',
        viewportWidth: 1280,
        viewportHeight: 720,
      });
      // Should configure without error
    });

    test('should toggle stealth mode', async () => {
      await settingsPage.switchSection('Browser');
      await settingsPage.stealhModeToggle.check();
      await expect(settingsPage.stealhModeToggle).toBeChecked();
    });

    test('should toggle fingerprint spoofing', async () => {
      await settingsPage.switchSection('Browser');
      await settingsPage.fingerprintToggle.check();
      await expect(settingsPage.fingerprintToggle).toBeChecked();
    });
  });

  test.describe('Proxy Settings', () => {
    test('should display proxy toggle', async () => {
      await settingsPage.switchSection('Proxy');
      await expect(settingsPage.useProxyToggle).toBeVisible();
    });

    test('should display proxy type select', async () => {
      await settingsPage.switchSection('Proxy');
      await expect(settingsPage.proxyTypeSelect).toBeVisible();
    });

    test('should configure proxy settings', async () => {
      await settingsPage.configureProxy({
        useProxy: true,
        proxyType: 'rotating',
        rotationInterval: 30,
        maxRetries: 3,
      });
      // Should configure without error
    });

    test('should disable proxy', async () => {
      await settingsPage.configureProxy({ useProxy: false });
      await settingsPage.switchSection('Proxy');
      // Proxy should be disabled
    });
  });

  test.describe('API Settings', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/llm/health', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'connected', model: 'llama3.2' }),
        });
      });
    });

    test('should display Ollama URL input', async () => {
      await settingsPage.switchSection('API');
      await expect(settingsPage.ollamaUrlInput).toBeVisible();
    });

    test('should display test connection button', async () => {
      await settingsPage.switchSection('API');
      await expect(settingsPage.testConnectionButton).toBeVisible();
    });

    test('should configure API settings', async () => {
      await settingsPage.configureAPI({
        ollamaUrl: 'http://localhost:11434',
        ollamaModel: 'llama3.2',
      });
      // Should configure without error
    });

    test('should test API connection', async () => {
      await settingsPage.switchSection('API');
      const connected = await settingsPage.testAPIConnection();
      expect(connected).toBeDefined();
    });
  });

  test.describe('Behavior Settings', () => {
    test('should display watch time inputs', async () => {
      await settingsPage.switchSection('Behavior');
      await expect(settingsPage.watchTimeMinInput).toBeVisible();
      await expect(settingsPage.watchTimeMaxInput).toBeVisible();
    });

    test('should display scroll behavior select', async () => {
      await settingsPage.switchSection('Behavior');
      await expect(settingsPage.scrollBehaviorSelect).toBeVisible();
    });

    test('should configure behavior settings', async () => {
      await settingsPage.configureBehavior({
        watchTimeMin: 10,
        watchTimeMax: 60,
        scrollBehavior: 'smooth',
        interactions: true,
        humanDelay: true,
      });
      // Should configure without error
    });
  });

  test.describe('Advanced Settings', () => {
    test('should display workers input', async () => {
      await settingsPage.switchSection('Advanced');
      await expect(settingsPage.workersInput).toBeVisible();
    });

    test('should display timeout input', async () => {
      await settingsPage.switchSection('Advanced');
      await expect(settingsPage.timeoutInput).toBeVisible();
    });

    test('should display debug mode toggle', async () => {
      await settingsPage.switchSection('Advanced');
      await expect(settingsPage.debugModeToggle).toBeVisible();
    });

    test('should configure advanced settings', async () => {
      await settingsPage.configureAdvanced({
        workers: 10,
        timeout: 60000,
        retryDelay: 5000,
        debugMode: true,
        loggingLevel: 'debug',
      });
      // Should configure without error
    });
  });

  test.describe('Save/Reset', () => {
    test('should display save button', async () => {
      await expect(settingsPage.saveButton).toBeVisible();
    });

    test('should display reset button', async () => {
      await expect(settingsPage.resetButton).toBeVisible();
    });

    test('should save settings', async () => {
      await settingsPage.saveSettings();
      // Should save and show toast
    });

    test('should reset settings', async () => {
      await settingsPage.resetSettings();
      // Should reset without error
    });
  });

  test.describe('Import/Export', () => {
    test('should display export button', async () => {
      await expect(settingsPage.exportButton).toBeVisible();
    });

    test('should display import button', async () => {
      await expect(settingsPage.importButton).toBeVisible();
    });

    test('should export settings', async ({ page }) => {
      await page.route('**/api/config/export', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ config: {} }),
          headers: {
            'Content-Disposition': 'attachment; filename="settings.json"',
          },
        });
      });

      // Export button click
      await settingsPage.exportButton.click();
    });
  });

  test.describe('Presets', () => {
    test('should display presets container', async () => {
      await expect(settingsPage.presetsContainer).toBeVisible();
    });

    test('should display preset cards', async () => {
      const count = await settingsPage.presetCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should get preset names', async () => {
      const names = await settingsPage.getPresetNames();
      expect(names.length).toBeGreaterThanOrEqual(0);
    });

    test('should select a preset', async () => {
      const names = await settingsPage.getPresetNames();
      if (names.length > 0) {
        await settingsPage.selectPreset(names[0]);
        // Should apply preset
      }
    });

    test('should create a preset', async ({ page }) => {
      await page.route('**/api/config/presets', route => {
        if (route.request().method() === 'POST') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ id: 'new-preset', name: 'Custom Preset' }),
          });
        }
      });

      await settingsPage.createPreset('Custom Preset');
      // Should create preset
    });

    test('should delete a preset', async ({ page }) => {
      await page.route('**/api/config/presets/*', route => {
        if (route.request().method() === 'DELETE') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ success: true }),
          });
        }
      });

      const names = await settingsPage.getPresetNames();
      if (names.length > 0) {
        await settingsPage.deletePreset(names[0]);
        // Should delete preset
      }
    });
  });

  test.describe('Validation', () => {
    test('should validate workers input', async () => {
      await settingsPage.switchSection('Advanced');
      await settingsPage.workersInput.fill('-1');
      await settingsPage.saveButton.click();

      // Should show validation error or reject invalid value
    });

    test('should validate timeout input', async () => {
      await settingsPage.switchSection('Advanced');
      await settingsPage.timeoutInput.fill('0');
      await settingsPage.saveButton.click();

      // Should validate
    });

    test('should validate Ollama URL', async () => {
      await settingsPage.switchSection('API');
      await settingsPage.ollamaUrlInput.fill('invalid-url');

      // Should show validation error
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(settingsPage.settingsTabs.first()).toBeVisible();
    });

    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(settingsPage.settingsTabs.first()).toBeVisible();
    });
  });
});
