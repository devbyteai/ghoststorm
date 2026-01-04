import { Page, Locator, expect } from '@playwright/test';

/**
 * Flow Recorder Component - handles the flow recording modal.
 */
export class FlowRecorderComponent {
  readonly page: Page;

  // Modal container
  readonly modal: Locator;
  readonly closeButton: Locator;

  // URL input
  readonly urlInput: Locator;
  readonly startRecordingButton: Locator;

  // Recording status
  readonly recordingIndicator: Locator;
  readonly recordingTimer: Locator;
  readonly pauseButton: Locator;
  readonly resumeButton: Locator;
  readonly stopButton: Locator;

  // Stealth options
  readonly stealthSection: Locator;
  readonly stealthPresets: Locator;
  readonly customStealthToggle: Locator;

  // Stealth toggles
  readonly webdriverToggle: Locator;
  readonly webglToggle: Locator;
  readonly canvasToggle: Locator;
  readonly pluginsToggle: Locator;
  readonly languagesToggle: Locator;
  readonly timezoneToggle: Locator;
  readonly hardwareToggle: Locator;
  readonly fontsToggle: Locator;
  readonly audioToggle: Locator;
  readonly permissionsToggle: Locator;

  // Presets
  readonly minimalPreset: Locator;
  readonly standardPreset: Locator;
  readonly aggressivePreset: Locator;
  readonly cloudPreset: Locator;

  // Action recording
  readonly recordedActions: Locator;
  readonly actionItems: Locator;
  readonly deleteActionButton: Locator;
  readonly editActionButton: Locator;

  // Checkpoints
  readonly addCheckpointButton: Locator;
  readonly checkpointsList: Locator;
  readonly checkpointItems: Locator;

  // Finalize
  readonly flowNameInput: Locator;
  readonly flowDescriptionInput: Locator;
  readonly saveFlowButton: Locator;
  readonly cancelButton: Locator;

  // Browser preview
  readonly browserPreview: Locator;
  readonly previewUrl: Locator;

  constructor(page: Page) {
    this.page = page;

    // Modal
    this.modal = page.locator('.flow-recorder-modal, [data-testid="flow-recorder"]');
    this.closeButton = page.locator('.flow-recorder-modal button[aria-label="Close"], .modal-close');

    // URL
    this.urlInput = page.locator('.flow-recorder-modal input[name="url"], #flow-url');
    this.startRecordingButton = page.locator('button:has-text("Start Recording")');

    // Recording status
    this.recordingIndicator = page.locator('.recording-indicator, [data-recording="true"]');
    this.recordingTimer = page.locator('.recording-timer, [data-testid="recording-timer"]');
    this.pauseButton = page.locator('button:has-text("Pause")');
    this.resumeButton = page.locator('button:has-text("Resume")');
    this.stopButton = page.locator('button:has-text("Stop Recording"), button:has-text("Stop")');

    // Stealth section
    this.stealthSection = page.locator('.stealth-options, [data-testid="stealth-options"]');
    this.stealthPresets = page.locator('.stealth-presets, [data-testid="stealth-presets"]');
    this.customStealthToggle = page.locator('input[name="custom_stealth"], #custom-stealth');

    // Stealth toggles
    this.webdriverToggle = page.locator('input[name="stealth_webdriver"], #stealth-webdriver');
    this.webglToggle = page.locator('input[name="stealth_webgl"], #stealth-webgl');
    this.canvasToggle = page.locator('input[name="stealth_canvas"], #stealth-canvas');
    this.pluginsToggle = page.locator('input[name="stealth_plugins"], #stealth-plugins');
    this.languagesToggle = page.locator('input[name="stealth_languages"], #stealth-languages');
    this.timezoneToggle = page.locator('input[name="stealth_timezone"], #stealth-timezone');
    this.hardwareToggle = page.locator('input[name="stealth_hardware"], #stealth-hardware');
    this.fontsToggle = page.locator('input[name="stealth_fonts"], #stealth-fonts');
    this.audioToggle = page.locator('input[name="stealth_audio"], #stealth-audio');
    this.permissionsToggle = page.locator('input[name="stealth_permissions"], #stealth-permissions');

    // Presets
    this.minimalPreset = page.locator('[data-preset="minimal"], button:has-text("Minimal")');
    this.standardPreset = page.locator('[data-preset="standard"], button:has-text("Standard")');
    this.aggressivePreset = page.locator('[data-preset="aggressive"], button:has-text("Aggressive")');
    this.cloudPreset = page.locator('[data-preset="cloud"], button:has-text("Cloud")');

    // Actions
    this.recordedActions = page.locator('.recorded-actions, [data-testid="recorded-actions"]');
    this.actionItems = page.locator('.action-item, [data-testid="action-item"]');
    this.deleteActionButton = page.locator('.action-item button[aria-label="Delete"]');
    this.editActionButton = page.locator('.action-item button[aria-label="Edit"]');

    // Checkpoints
    this.addCheckpointButton = page.locator('button:has-text("Add Checkpoint")');
    this.checkpointsList = page.locator('.checkpoints-list, [data-testid="checkpoints"]');
    this.checkpointItems = page.locator('.checkpoint-item, [data-testid="checkpoint-item"]');

    // Finalize
    this.flowNameInput = page.locator('input[name="flow_name"], #flow-name');
    this.flowDescriptionInput = page.locator('textarea[name="flow_description"], #flow-description');
    this.saveFlowButton = page.locator('button:has-text("Save Flow"), button:has-text("Finalize")');
    this.cancelButton = page.locator('.flow-recorder-modal button:has-text("Cancel")');

    // Preview
    this.browserPreview = page.locator('.browser-preview, [data-testid="browser-preview"]');
    this.previewUrl = page.locator('.preview-url, [data-testid="preview-url"]');
  }

  /**
   * Wait for modal to be visible.
   */
  async waitForModal() {
    await this.modal.waitFor({ state: 'visible' });
  }

  /**
   * Close the modal.
   */
  async close() {
    await this.closeButton.click();
    await this.modal.waitFor({ state: 'hidden' });
  }

  /**
   * Start recording a flow.
   */
  async startRecording(url: string) {
    await this.urlInput.fill(url);
    await this.startRecordingButton.click();
    await this.recordingIndicator.waitFor({ state: 'visible' });
  }

  /**
   * Stop recording.
   */
  async stopRecording() {
    await this.stopButton.click();
    await this.recordingIndicator.waitFor({ state: 'hidden' });
  }

  /**
   * Pause recording.
   */
  async pauseRecording() {
    await this.pauseButton.click();
  }

  /**
   * Resume recording.
   */
  async resumeRecording() {
    await this.resumeButton.click();
  }

  /**
   * Check if recording is active.
   */
  async isRecording(): Promise<boolean> {
    return await this.recordingIndicator.isVisible();
  }

  /**
   * Get recording duration.
   */
  async getRecordingTime(): Promise<string> {
    return await this.recordingTimer.textContent() || '00:00';
  }

  /**
   * Select a stealth preset.
   */
  async selectStealthPreset(preset: 'minimal' | 'standard' | 'aggressive' | 'cloud') {
    const presetButton = {
      minimal: this.minimalPreset,
      standard: this.standardPreset,
      aggressive: this.aggressivePreset,
      cloud: this.cloudPreset,
    }[preset];

    await presetButton.click();
  }

  /**
   * Enable custom stealth configuration.
   */
  async enableCustomStealth() {
    await this.customStealthToggle.check();
  }

  /**
   * Configure individual stealth options.
   */
  async configureStealthOptions(options: {
    webdriver?: boolean;
    webgl?: boolean;
    canvas?: boolean;
    plugins?: boolean;
    languages?: boolean;
    timezone?: boolean;
    hardware?: boolean;
    fonts?: boolean;
    audio?: boolean;
    permissions?: boolean;
  }) {
    await this.enableCustomStealth();

    const toggleMap = {
      webdriver: this.webdriverToggle,
      webgl: this.webglToggle,
      canvas: this.canvasToggle,
      plugins: this.pluginsToggle,
      languages: this.languagesToggle,
      timezone: this.timezoneToggle,
      hardware: this.hardwareToggle,
      fonts: this.fontsToggle,
      audio: this.audioToggle,
      permissions: this.permissionsToggle,
    };

    for (const [key, value] of Object.entries(options)) {
      if (value !== undefined) {
        const toggle = toggleMap[key as keyof typeof toggleMap];
        if (value) {
          await toggle.check();
        } else {
          await toggle.uncheck();
        }
      }
    }
  }

  /**
   * Get count of recorded actions.
   */
  async getActionCount(): Promise<number> {
    return await this.actionItems.count();
  }

  /**
   * Delete an action by index.
   */
  async deleteAction(index: number) {
    const action = this.actionItems.nth(index);
    await action.locator('button[aria-label="Delete"]').click();
  }

  /**
   * Add a checkpoint.
   */
  async addCheckpoint(name?: string) {
    await this.addCheckpointButton.click();

    if (name) {
      const nameInput = this.page.locator('input[name="checkpoint_name"]');
      await nameInput.fill(name);
    }

    const confirmButton = this.page.locator('button:has-text("Add"), button:has-text("Confirm")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Get checkpoint count.
   */
  async getCheckpointCount(): Promise<number> {
    return await this.checkpointItems.count();
  }

  /**
   * Delete a checkpoint.
   */
  async deleteCheckpoint(index: number) {
    const checkpoint = this.checkpointItems.nth(index);
    await checkpoint.locator('button[aria-label="Delete"]').click();
  }

  /**
   * Finalize and save the flow.
   */
  async saveFlow(name: string, description?: string) {
    await this.flowNameInput.fill(name);

    if (description) {
      await this.flowDescriptionInput.fill(description);
    }

    await this.saveFlowButton.click();
    await this.modal.waitFor({ state: 'hidden' });
  }

  /**
   * Cancel and discard the flow.
   */
  async cancel() {
    await this.cancelButton.click();

    // Confirm discard if prompted
    const confirmButton = this.page.locator('button:has-text("Discard"), button:has-text("Yes")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }

    await this.modal.waitFor({ state: 'hidden' });
  }

  /**
   * Get preview URL.
   */
  async getPreviewUrl(): Promise<string> {
    return await this.previewUrl.textContent() || '';
  }

  /**
   * Complete flow recording workflow.
   */
  async recordCompleteFlow(config: {
    url: string;
    stealthPreset?: 'minimal' | 'standard' | 'aggressive' | 'cloud';
    recordDuration?: number;
    flowName: string;
    flowDescription?: string;
  }) {
    // Start recording
    await this.startRecording(config.url);

    // Apply stealth preset if specified
    if (config.stealthPreset) {
      await this.selectStealthPreset(config.stealthPreset);
    }

    // Wait for recording duration
    if (config.recordDuration) {
      await this.page.waitForTimeout(config.recordDuration);
    }

    // Stop and save
    await this.stopRecording();
    await this.saveFlow(config.flowName, config.flowDescription);
  }
}
