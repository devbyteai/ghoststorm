import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Proxies Page Object - handles proxy management UI.
 */
export class ProxiesPage extends BasePage {
  // Stats cards
  readonly statsContainer: Locator;
  readonly totalProxiesCard: Locator;
  readonly healthyProxiesCard: Locator;
  readonly failedProxiesCard: Locator;
  readonly lastScrapeCard: Locator;

  // Actions
  readonly scrapeButton: Locator;
  readonly testAllButton: Locator;
  readonly clearButton: Locator;
  readonly exportButton: Locator;
  readonly importButton: Locator;

  // Sources
  readonly sourcesContainer: Locator;
  readonly sourceCards: Locator;
  readonly enabledSources: Locator;
  readonly disabledSources: Locator;

  // Premium providers
  readonly providersContainer: Locator;
  readonly decodoProvider: Locator;
  readonly brightdataProvider: Locator;
  readonly oxylabsProvider: Locator;
  readonly configureProviderButton: Locator;

  // Proxy table
  readonly proxyTable: Locator;
  readonly proxyRows: Locator;
  readonly proxySearch: Locator;
  readonly proxyFilter: Locator;
  readonly selectAllCheckbox: Locator;

  // Modals
  readonly importModal: Locator;
  readonly importTextarea: Locator;
  readonly importSubmitButton: Locator;
  readonly configureModal: Locator;
  readonly apiKeyInput: Locator;
  readonly saveConfigButton: Locator;

  // Job status
  readonly activeJobs: Locator;
  readonly jobProgress: Locator;
  readonly cancelJobButton: Locator;

  constructor(page: Page) {
    super(page);

    // Stats
    this.statsContainer = page.locator('.proxy-stats, [data-testid="proxy-stats"]');
    this.totalProxiesCard = page.locator('[data-stat="total"], .stat-total');
    this.healthyProxiesCard = page.locator('[data-stat="healthy"], .stat-healthy');
    this.failedProxiesCard = page.locator('[data-stat="failed"], .stat-failed');
    this.lastScrapeCard = page.locator('[data-stat="last-scrape"], .stat-last-scrape');

    // Actions
    this.scrapeButton = page.locator('button:has-text("Scrape"), button:has-text("Fetch Proxies")');
    this.testAllButton = page.locator('button:has-text("Test All"), button:has-text("Validate")');
    this.clearButton = page.locator('button:has-text("Clear"), button:has-text("Remove All")');
    this.exportButton = page.locator('button:has-text("Export")');
    this.importButton = page.locator('button:has-text("Import")');

    // Sources
    this.sourcesContainer = page.locator('.proxy-sources, [data-testid="proxy-sources"]');
    this.sourceCards = page.locator('.source-card, [data-testid="source-card"]');
    this.enabledSources = page.locator('.source-card.enabled, [data-enabled="true"]');
    this.disabledSources = page.locator('.source-card.disabled, [data-enabled="false"]');

    // Premium providers
    this.providersContainer = page.locator('.premium-providers, [data-testid="premium-providers"]');
    this.decodoProvider = page.locator('[data-provider="decodo"]');
    this.brightdataProvider = page.locator('[data-provider="brightdata"]');
    this.oxylabsProvider = page.locator('[data-provider="oxylabs"]');
    this.configureProviderButton = page.locator('button:has-text("Configure"), button:has-text("Setup")');

    // Proxy table
    this.proxyTable = page.locator('table, .proxy-table, [data-testid="proxy-table"]');
    this.proxyRows = page.locator('tbody tr, .proxy-row');
    this.proxySearch = page.locator('input[placeholder*="Search"], #proxy-search');
    this.proxyFilter = page.locator('select[name="filter"], #proxy-filter');
    this.selectAllCheckbox = page.locator('thead input[type="checkbox"], .select-all');

    // Modals
    this.importModal = page.locator('.import-modal, [data-modal="import"]');
    this.importTextarea = page.locator('textarea[name="proxies"], #import-textarea');
    this.importSubmitButton = page.locator('.import-modal button:has-text("Import")');
    this.configureModal = page.locator('.configure-modal, [data-modal="configure"]');
    this.apiKeyInput = page.locator('input[name="api_key"], #api-key');
    this.saveConfigButton = page.locator('.configure-modal button:has-text("Save")');

    // Job status
    this.activeJobs = page.locator('.active-jobs, [data-testid="active-jobs"]');
    this.jobProgress = page.locator('.job-progress, [role="progressbar"]');
    this.cancelJobButton = page.locator('button:has-text("Cancel Job"), button[aria-label="Cancel"]');
  }

  /**
   * Navigate to Proxies page.
   */
  async gotoProxiesPage() {
    await this.goto('/');
    await this.navigateToTab('Proxies');
  }

  /**
   * Get total proxies count.
   */
  async getTotalProxies(): Promise<number> {
    const text = await this.totalProxiesCard.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0]) : 0;
  }

  /**
   * Get healthy proxies count.
   */
  async getHealthyProxies(): Promise<number> {
    const text = await this.healthyProxiesCard.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0]) : 0;
  }

  /**
   * Get failed proxies count.
   */
  async getFailedProxies(): Promise<number> {
    const text = await this.failedProxiesCard.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0]) : 0;
  }

  /**
   * Start scraping proxies.
   */
  async startScrape() {
    await this.scrapeButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Test all proxies.
   */
  async testAllProxies() {
    await this.testAllButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Clear all proxies.
   */
  async clearAllProxies() {
    await this.clearButton.click();

    // Confirm deletion
    const confirmButton = this.page.locator('button:has-text("Confirm"), button:has-text("Yes")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Export proxies.
   */
  async exportProxies(): Promise<string> {
    const [download] = await Promise.all([
      this.page.waitForEvent('download'),
      this.exportButton.click(),
    ]);
    return download.suggestedFilename();
  }

  /**
   * Import proxies from text.
   */
  async importProxies(proxyList: string) {
    await this.importButton.click();
    await this.importModal.waitFor({ state: 'visible' });
    await this.importTextarea.fill(proxyList);
    await this.importSubmitButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Toggle a proxy source.
   */
  async toggleSource(sourceName: string) {
    const source = this.sourceCards.filter({ hasText: sourceName });
    const toggle = source.locator('input[type="checkbox"], button.toggle');
    await toggle.click();
  }

  /**
   * Get enabled source names.
   */
  async getEnabledSources(): Promise<string[]> {
    const sources: string[] = [];
    const count = await this.enabledSources.count();
    for (let i = 0; i < count; i++) {
      const name = await this.enabledSources.nth(i).locator('.source-name').textContent();
      if (name) sources.push(name);
    }
    return sources;
  }

  /**
   * Configure premium provider.
   */
  async configureProvider(provider: string, apiKey: string) {
    const providerCard = this.providersContainer.locator(`[data-provider="${provider}"]`);
    await providerCard.locator(this.configureProviderButton).click();

    await this.configureModal.waitFor({ state: 'visible' });
    await this.apiKeyInput.fill(apiKey);
    await this.saveConfigButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Search proxies.
   */
  async searchProxies(query: string) {
    await this.proxySearch.fill(query);
    await this.page.waitForTimeout(300); // Debounce
  }

  /**
   * Filter proxies by status.
   */
  async filterByStatus(status: 'all' | 'healthy' | 'failed' | 'untested') {
    await this.proxyFilter.selectOption(status);
  }

  /**
   * Get proxy row count.
   */
  async getProxyRowCount(): Promise<number> {
    return await this.proxyRows.count();
  }

  /**
   * Select a proxy row.
   */
  async selectProxy(index: number) {
    const checkbox = this.proxyRows.nth(index).locator('input[type="checkbox"]');
    await checkbox.check();
  }

  /**
   * Select all proxies.
   */
  async selectAllProxies() {
    await this.selectAllCheckbox.check();
  }

  /**
   * Test selected proxies.
   */
  async testSelected() {
    const testSelectedButton = this.page.locator('button:has-text("Test Selected")');
    await testSelectedButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Delete selected proxies.
   */
  async deleteSelected() {
    const deleteButton = this.page.locator('button:has-text("Delete Selected")');
    await deleteButton.click();

    // Confirm
    const confirmButton = this.page.locator('button:has-text("Confirm")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Check if scrape job is running.
   */
  async isJobRunning(): Promise<boolean> {
    return await this.jobProgress.isVisible();
  }

  /**
   * Cancel running job.
   */
  async cancelJob() {
    if (await this.cancelJobButton.isVisible()) {
      await this.cancelJobButton.click();
    }
  }

  /**
   * Wait for job to complete.
   */
  async waitForJobComplete(timeout: number = 60000) {
    await this.jobProgress.waitFor({ state: 'hidden', timeout });
  }
}
