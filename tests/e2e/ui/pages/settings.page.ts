import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Settings Page Object - handles configuration UI.
 */
export class SettingsPage extends BasePage {
  // Section tabs
  readonly settingsTabs: Locator;
  readonly browserTab: Locator;
  readonly proxyTab: Locator;
  readonly apiTab: Locator;
  readonly behaviorTab: Locator;
  readonly advancedTab: Locator;

  // Browser settings
  readonly browserContainer: Locator;
  readonly headlessToggle: Locator;
  readonly browserTypeSelect: Locator;
  readonly userAgentInput: Locator;
  readonly viewportWidthInput: Locator;
  readonly viewportHeightInput: Locator;
  readonly stealhModeToggle: Locator;
  readonly fingerprintToggle: Locator;

  // Proxy settings
  readonly proxyContainer: Locator;
  readonly useProxyToggle: Locator;
  readonly proxyTypeSelect: Locator;
  readonly rotationIntervalInput: Locator;
  readonly maxRetries: Locator;

  // API settings
  readonly apiContainer: Locator;
  readonly ollamaUrlInput: Locator;
  readonly ollamaModelSelect: Locator;
  readonly testConnectionButton: Locator;
  readonly connectionStatus: Locator;

  // Behavior settings
  readonly behaviorContainer: Locator;
  readonly watchTimeMinInput: Locator;
  readonly watchTimeMaxInput: Locator;
  readonly scrollBehaviorSelect: Locator;
  readonly interactionsToggle: Locator;
  readonly humanDelayToggle: Locator;

  // Advanced settings
  readonly advancedContainer: Locator;
  readonly workersInput: Locator;
  readonly timeoutInput: Locator;
  readonly retryDelayInput: Locator;
  readonly debugModeToggle: Locator;
  readonly loggingLevelSelect: Locator;

  // Actions
  readonly saveButton: Locator;
  readonly resetButton: Locator;
  readonly exportButton: Locator;
  readonly importButton: Locator;

  // Presets
  readonly presetsContainer: Locator;
  readonly presetCards: Locator;
  readonly createPresetButton: Locator;
  readonly presetNameInput: Locator;

  constructor(page: Page) {
    super(page);

    // Section tabs
    this.settingsTabs = page.locator('.settings-tabs [role="tab"], .settings-nav button');
    this.browserTab = page.locator('[data-tab="browser"], button:has-text("Browser")');
    this.proxyTab = page.locator('[data-tab="proxy"], button:has-text("Proxy")');
    this.apiTab = page.locator('[data-tab="api"], button:has-text("API")');
    this.behaviorTab = page.locator('[data-tab="behavior"], button:has-text("Behavior")');
    this.advancedTab = page.locator('[data-tab="advanced"], button:has-text("Advanced")');

    // Browser settings
    this.browserContainer = page.locator('.browser-settings, [data-section="browser"]');
    this.headlessToggle = page.locator('input[name="headless"], #headless-toggle');
    this.browserTypeSelect = page.locator('select[name="browser_type"], #browser-type');
    this.userAgentInput = page.locator('input[name="user_agent"], #user-agent');
    this.viewportWidthInput = page.locator('input[name="viewport_width"], #viewport-width');
    this.viewportHeightInput = page.locator('input[name="viewport_height"], #viewport-height');
    this.stealhModeToggle = page.locator('input[name="stealth_mode"], #stealth-mode');
    this.fingerprintToggle = page.locator('input[name="fingerprint"], #fingerprint');

    // Proxy settings
    this.proxyContainer = page.locator('.proxy-settings, [data-section="proxy"]');
    this.useProxyToggle = page.locator('input[name="use_proxy"], #use-proxy');
    this.proxyTypeSelect = page.locator('select[name="proxy_type"], #proxy-type');
    this.rotationIntervalInput = page.locator('input[name="rotation_interval"], #rotation-interval');
    this.maxRetries = page.locator('input[name="max_retries"], #max-retries');

    // API settings
    this.apiContainer = page.locator('.api-settings, [data-section="api"]');
    this.ollamaUrlInput = page.locator('input[name="ollama_url"], #ollama-url');
    this.ollamaModelSelect = page.locator('select[name="ollama_model"], #ollama-model');
    this.testConnectionButton = page.locator('button:has-text("Test Connection"), button:has-text("Test")');
    this.connectionStatus = page.locator('.connection-status, [data-testid="connection-status"]');

    // Behavior settings
    this.behaviorContainer = page.locator('.behavior-settings, [data-section="behavior"]');
    this.watchTimeMinInput = page.locator('input[name="watch_time_min"], #watch-time-min');
    this.watchTimeMaxInput = page.locator('input[name="watch_time_max"], #watch-time-max');
    this.scrollBehaviorSelect = page.locator('select[name="scroll_behavior"], #scroll-behavior');
    this.interactionsToggle = page.locator('input[name="interactions"], #interactions');
    this.humanDelayToggle = page.locator('input[name="human_delay"], #human-delay');

    // Advanced settings
    this.advancedContainer = page.locator('.advanced-settings, [data-section="advanced"]');
    this.workersInput = page.locator('input[name="workers"], #workers');
    this.timeoutInput = page.locator('input[name="timeout"], #timeout');
    this.retryDelayInput = page.locator('input[name="retry_delay"], #retry-delay');
    this.debugModeToggle = page.locator('input[name="debug_mode"], #debug-mode');
    this.loggingLevelSelect = page.locator('select[name="logging_level"], #logging-level');

    // Actions
    this.saveButton = page.locator('button:has-text("Save"), button:has-text("Apply")');
    this.resetButton = page.locator('button:has-text("Reset"), button:has-text("Restore Defaults")');
    this.exportButton = page.locator('button:has-text("Export Settings")');
    this.importButton = page.locator('button:has-text("Import Settings")');

    // Presets
    this.presetsContainer = page.locator('.presets-container, [data-testid="presets"]');
    this.presetCards = page.locator('.preset-card, [data-testid="preset-card"]');
    this.createPresetButton = page.locator('button:has-text("Create Preset"), button:has-text("Save as Preset")');
    this.presetNameInput = page.locator('input[name="preset_name"], #preset-name');
  }

  /**
   * Navigate to Settings page.
   */
  async gotoSettingsPage() {
    await this.goto('/');
    await this.navigateToTab('Settings');
  }

  /**
   * Switch to a settings section.
   */
  async switchSection(section: string) {
    const tab = this.settingsTabs.filter({ hasText: section });
    await tab.click();
  }

  // ==================== Browser Settings ====================

  /**
   * Configure browser settings.
   */
  async configureBrowser(config: {
    headless?: boolean;
    browserType?: string;
    userAgent?: string;
    viewportWidth?: number;
    viewportHeight?: number;
    stealthMode?: boolean;
    fingerprint?: boolean;
  }) {
    await this.switchSection('Browser');

    if (config.headless !== undefined) {
      if (config.headless) {
        await this.headlessToggle.check();
      } else {
        await this.headlessToggle.uncheck();
      }
    }

    if (config.browserType) {
      await this.browserTypeSelect.selectOption(config.browserType);
    }

    if (config.userAgent) {
      await this.userAgentInput.fill(config.userAgent);
    }

    if (config.viewportWidth) {
      await this.viewportWidthInput.fill(config.viewportWidth.toString());
    }

    if (config.viewportHeight) {
      await this.viewportHeightInput.fill(config.viewportHeight.toString());
    }

    if (config.stealthMode !== undefined) {
      if (config.stealthMode) {
        await this.stealhModeToggle.check();
      } else {
        await this.stealhModeToggle.uncheck();
      }
    }

    if (config.fingerprint !== undefined) {
      if (config.fingerprint) {
        await this.fingerprintToggle.check();
      } else {
        await this.fingerprintToggle.uncheck();
      }
    }
  }

  // ==================== Proxy Settings ====================

  /**
   * Configure proxy settings.
   */
  async configureProxy(config: {
    useProxy?: boolean;
    proxyType?: string;
    rotationInterval?: number;
    maxRetries?: number;
  }) {
    await this.switchSection('Proxy');

    if (config.useProxy !== undefined) {
      if (config.useProxy) {
        await this.useProxyToggle.check();
      } else {
        await this.useProxyToggle.uncheck();
      }
    }

    if (config.proxyType) {
      await this.proxyTypeSelect.selectOption(config.proxyType);
    }

    if (config.rotationInterval) {
      await this.rotationIntervalInput.fill(config.rotationInterval.toString());
    }

    if (config.maxRetries) {
      await this.maxRetries.fill(config.maxRetries.toString());
    }
  }

  // ==================== API Settings ====================

  /**
   * Configure API settings.
   */
  async configureAPI(config: {
    ollamaUrl?: string;
    ollamaModel?: string;
  }) {
    await this.switchSection('API');

    if (config.ollamaUrl) {
      await this.ollamaUrlInput.fill(config.ollamaUrl);
    }

    if (config.ollamaModel) {
      await this.ollamaModelSelect.selectOption(config.ollamaModel);
    }
  }

  /**
   * Test API connection.
   */
  async testAPIConnection(): Promise<boolean> {
    await this.testConnectionButton.click();
    await this.waitForLoadingComplete();

    const statusText = await this.connectionStatus.textContent();
    return statusText?.toLowerCase().includes('connected') ?? false;
  }

  // ==================== Behavior Settings ====================

  /**
   * Configure behavior settings.
   */
  async configureBehavior(config: {
    watchTimeMin?: number;
    watchTimeMax?: number;
    scrollBehavior?: string;
    interactions?: boolean;
    humanDelay?: boolean;
  }) {
    await this.switchSection('Behavior');

    if (config.watchTimeMin) {
      await this.watchTimeMinInput.fill(config.watchTimeMin.toString());
    }

    if (config.watchTimeMax) {
      await this.watchTimeMaxInput.fill(config.watchTimeMax.toString());
    }

    if (config.scrollBehavior) {
      await this.scrollBehaviorSelect.selectOption(config.scrollBehavior);
    }

    if (config.interactions !== undefined) {
      if (config.interactions) {
        await this.interactionsToggle.check();
      } else {
        await this.interactionsToggle.uncheck();
      }
    }

    if (config.humanDelay !== undefined) {
      if (config.humanDelay) {
        await this.humanDelayToggle.check();
      } else {
        await this.humanDelayToggle.uncheck();
      }
    }
  }

  // ==================== Advanced Settings ====================

  /**
   * Configure advanced settings.
   */
  async configureAdvanced(config: {
    workers?: number;
    timeout?: number;
    retryDelay?: number;
    debugMode?: boolean;
    loggingLevel?: string;
  }) {
    await this.switchSection('Advanced');

    if (config.workers) {
      await this.workersInput.fill(config.workers.toString());
    }

    if (config.timeout) {
      await this.timeoutInput.fill(config.timeout.toString());
    }

    if (config.retryDelay) {
      await this.retryDelayInput.fill(config.retryDelay.toString());
    }

    if (config.debugMode !== undefined) {
      if (config.debugMode) {
        await this.debugModeToggle.check();
      } else {
        await this.debugModeToggle.uncheck();
      }
    }

    if (config.loggingLevel) {
      await this.loggingLevelSelect.selectOption(config.loggingLevel);
    }
  }

  // ==================== Actions ====================

  /**
   * Save all settings.
   */
  async saveSettings() {
    await this.saveButton.click();
    await this.waitForLoadingComplete();
    await this.waitForToast('saved');
  }

  /**
   * Reset settings to defaults.
   */
  async resetSettings() {
    await this.resetButton.click();

    // Confirm reset
    const confirmButton = this.page.locator('button:has-text("Confirm"), button:has-text("Yes")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }

    await this.waitForLoadingComplete();
  }

  /**
   * Export settings.
   */
  async exportSettings(): Promise<string> {
    const [download] = await Promise.all([
      this.page.waitForEvent('download'),
      this.exportButton.click(),
    ]);
    return download.suggestedFilename();
  }

  /**
   * Import settings from file.
   */
  async importSettings(filePath: string) {
    const [fileChooser] = await Promise.all([
      this.page.waitForEvent('filechooser'),
      this.importButton.click(),
    ]);
    await fileChooser.setFiles(filePath);
    await this.waitForLoadingComplete();
  }

  // ==================== Presets ====================

  /**
   * Select a preset.
   */
  async selectPreset(presetName: string) {
    const preset = this.presetCards.filter({ hasText: presetName });
    await preset.click();
  }

  /**
   * Create a new preset.
   */
  async createPreset(name: string) {
    await this.createPresetButton.click();
    await this.presetNameInput.fill(name);

    const savePresetButton = this.page.locator('button:has-text("Save Preset")');
    await savePresetButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Get preset names.
   */
  async getPresetNames(): Promise<string[]> {
    const names: string[] = [];
    const count = await this.presetCards.count();

    for (let i = 0; i < count; i++) {
      const name = await this.presetCards.nth(i).locator('.preset-name').textContent();
      if (name) names.push(name);
    }

    return names;
  }

  /**
   * Delete a preset.
   */
  async deletePreset(presetName: string) {
    const preset = this.presetCards.filter({ hasText: presetName });
    const deleteButton = preset.locator('button[aria-label="Delete"], button:has-text("Delete")');
    await deleteButton.click();

    // Confirm deletion
    const confirmButton = this.page.locator('button:has-text("Confirm")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }
}
