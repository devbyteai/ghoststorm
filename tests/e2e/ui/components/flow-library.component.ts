import { Page, Locator, expect } from '@playwright/test';

/**
 * Flow Library Component - handles the flow library modal.
 */
export class FlowLibraryComponent {
  readonly page: Page;

  // Modal container
  readonly modal: Locator;
  readonly closeButton: Locator;

  // Search and filter
  readonly searchInput: Locator;
  readonly platformFilter: Locator;
  readonly sortSelect: Locator;

  // Flow list
  readonly flowList: Locator;
  readonly flowCards: Locator;
  readonly emptyMessage: Locator;

  // Flow card elements
  readonly flowName: Locator;
  readonly flowPlatform: Locator;
  readonly flowDate: Locator;
  readonly flowStats: Locator;

  // Flow actions
  readonly executeButton: Locator;
  readonly editButton: Locator;
  readonly duplicateButton: Locator;
  readonly exportButton: Locator;
  readonly deleteButton: Locator;

  // Execute modal
  readonly executeModal: Locator;
  readonly executionConfig: Locator;
  readonly repeatInput: Locator;
  readonly delayInput: Locator;
  readonly useProxyCheckbox: Locator;
  readonly confirmExecuteButton: Locator;

  // Edit modal
  readonly editModal: Locator;
  readonly editNameInput: Locator;
  readonly editDescriptionInput: Locator;
  readonly editStealthConfig: Locator;
  readonly saveEditButton: Locator;

  // Import/Export
  readonly importButton: Locator;
  readonly exportAllButton: Locator;
  readonly importFileInput: Locator;

  constructor(page: Page) {
    this.page = page;

    // Modal
    this.modal = page.locator('.flow-library-modal, [data-testid="flow-library"]');
    this.closeButton = page.locator('.flow-library-modal button[aria-label="Close"]');

    // Search and filter
    this.searchInput = page.locator('.flow-library-modal input[placeholder*="Search"], #flow-search');
    this.platformFilter = page.locator('select[name="platform_filter"], #platform-filter');
    this.sortSelect = page.locator('select[name="sort"], #sort-select');

    // Flow list
    this.flowList = page.locator('.flow-list, [data-testid="flow-list"]');
    this.flowCards = page.locator('.flow-card, [data-testid="flow-card"]');
    this.emptyMessage = page.locator('.empty-message, :has-text("No flows found")');

    // Flow card elements
    this.flowName = page.locator('.flow-card .flow-name');
    this.flowPlatform = page.locator('.flow-card .flow-platform');
    this.flowDate = page.locator('.flow-card .flow-date');
    this.flowStats = page.locator('.flow-card .flow-stats');

    // Flow actions
    this.executeButton = page.locator('button:has-text("Execute"), button[aria-label="Execute"]');
    this.editButton = page.locator('button:has-text("Edit"), button[aria-label="Edit"]');
    this.duplicateButton = page.locator('button:has-text("Duplicate"), button[aria-label="Duplicate"]');
    this.exportButton = page.locator('button:has-text("Export"), button[aria-label="Export"]');
    this.deleteButton = page.locator('button:has-text("Delete"), button[aria-label="Delete"]');

    // Execute modal
    this.executeModal = page.locator('.execute-modal, [data-testid="execute-modal"]');
    this.executionConfig = page.locator('.execution-config, [data-testid="execution-config"]');
    this.repeatInput = page.locator('input[name="repeat"], #repeat-count');
    this.delayInput = page.locator('input[name="delay"], #delay-seconds');
    this.useProxyCheckbox = page.locator('input[name="use_proxy"], #use-proxy-checkbox');
    this.confirmExecuteButton = page.locator('.execute-modal button:has-text("Start"), button:has-text("Execute")');

    // Edit modal
    this.editModal = page.locator('.edit-flow-modal, [data-testid="edit-flow-modal"]');
    this.editNameInput = page.locator('.edit-flow-modal input[name="name"]');
    this.editDescriptionInput = page.locator('.edit-flow-modal textarea[name="description"]');
    this.editStealthConfig = page.locator('.edit-flow-modal .stealth-config');
    this.saveEditButton = page.locator('.edit-flow-modal button:has-text("Save")');

    // Import/Export
    this.importButton = page.locator('button:has-text("Import Flow")');
    this.exportAllButton = page.locator('button:has-text("Export All")');
    this.importFileInput = page.locator('input[type="file"][accept*=".json"]');
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
   * Search for flows.
   */
  async search(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(300); // Debounce
  }

  /**
   * Filter by platform.
   */
  async filterByPlatform(platform: string) {
    await this.platformFilter.selectOption(platform);
  }

  /**
   * Sort flows.
   */
  async sortBy(sortOption: string) {
    await this.sortSelect.selectOption(sortOption);
  }

  /**
   * Get flow count.
   */
  async getFlowCount(): Promise<number> {
    return await this.flowCards.count();
  }

  /**
   * Get flow names.
   */
  async getFlowNames(): Promise<string[]> {
    const names: string[] = [];
    const count = await this.flowCards.count();

    for (let i = 0; i < count; i++) {
      const name = await this.flowCards.nth(i).locator('.flow-name').textContent();
      if (name) names.push(name);
    }

    return names;
  }

  /**
   * Select a flow by name.
   */
  async selectFlow(flowName: string) {
    const flow = this.flowCards.filter({ hasText: flowName });
    await flow.click();
  }

  /**
   * Execute a flow.
   */
  async executeFlow(flowName: string, config?: {
    repeat?: number;
    delay?: number;
    useProxy?: boolean;
  }) {
    const flow = this.flowCards.filter({ hasText: flowName });
    await flow.locator(this.executeButton).click();

    await this.executeModal.waitFor({ state: 'visible' });

    if (config?.repeat) {
      await this.repeatInput.fill(config.repeat.toString());
    }

    if (config?.delay) {
      await this.delayInput.fill(config.delay.toString());
    }

    if (config?.useProxy !== undefined) {
      if (config.useProxy) {
        await this.useProxyCheckbox.check();
      } else {
        await this.useProxyCheckbox.uncheck();
      }
    }

    await this.confirmExecuteButton.click();
    await this.executeModal.waitFor({ state: 'hidden' });
  }

  /**
   * Edit a flow.
   */
  async editFlow(flowName: string, updates: {
    name?: string;
    description?: string;
  }) {
    const flow = this.flowCards.filter({ hasText: flowName });
    await flow.locator(this.editButton).click();

    await this.editModal.waitFor({ state: 'visible' });

    if (updates.name) {
      await this.editNameInput.clear();
      await this.editNameInput.fill(updates.name);
    }

    if (updates.description) {
      await this.editDescriptionInput.clear();
      await this.editDescriptionInput.fill(updates.description);
    }

    await this.saveEditButton.click();
    await this.editModal.waitFor({ state: 'hidden' });
  }

  /**
   * Duplicate a flow.
   */
  async duplicateFlow(flowName: string): Promise<string> {
    const flow = this.flowCards.filter({ hasText: flowName });
    await flow.locator(this.duplicateButton).click();

    // Wait for new flow to appear
    await this.page.waitForTimeout(500);

    // Return new flow name (typically "flowName (copy)")
    return `${flowName} (copy)`;
  }

  /**
   * Export a flow.
   */
  async exportFlow(flowName: string): Promise<string> {
    const flow = this.flowCards.filter({ hasText: flowName });

    const [download] = await Promise.all([
      this.page.waitForEvent('download'),
      flow.locator(this.exportButton).click(),
    ]);

    return download.suggestedFilename();
  }

  /**
   * Delete a flow.
   */
  async deleteFlow(flowName: string) {
    const flow = this.flowCards.filter({ hasText: flowName });
    await flow.locator(this.deleteButton).click();

    // Confirm deletion
    const confirmButton = this.page.locator('button:has-text("Confirm"), button:has-text("Yes")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Import a flow from file.
   */
  async importFlow(filePath: string) {
    await this.importButton.click();

    const [fileChooser] = await Promise.all([
      this.page.waitForEvent('filechooser'),
      this.importFileInput.click(),
    ]);

    await fileChooser.setFiles(filePath);
    await this.page.waitForTimeout(500);
  }

  /**
   * Export all flows.
   */
  async exportAllFlows(): Promise<string> {
    const [download] = await Promise.all([
      this.page.waitForEvent('download'),
      this.exportAllButton.click(),
    ]);

    return download.suggestedFilename();
  }

  /**
   * Check if flow exists.
   */
  async flowExists(flowName: string): Promise<boolean> {
    const flow = this.flowCards.filter({ hasText: flowName });
    return await flow.count() > 0;
  }

  /**
   * Get flow details.
   */
  async getFlowDetails(flowName: string): Promise<{
    name: string;
    platform: string;
    date: string;
    stats: string;
  }> {
    const flow = this.flowCards.filter({ hasText: flowName });

    return {
      name: await flow.locator('.flow-name').textContent() || '',
      platform: await flow.locator('.flow-platform').textContent() || '',
      date: await flow.locator('.flow-date').textContent() || '',
      stats: await flow.locator('.flow-stats').textContent() || '',
    };
  }

  /**
   * Wait for flow list to update.
   */
  async waitForListUpdate(previousCount: number) {
    await expect(async () => {
      const currentCount = await this.getFlowCount();
      expect(currentCount).not.toBe(previousCount);
    }).toPass({ timeout: 10000 });
  }
}
