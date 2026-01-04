import { Page, Locator, expect } from '@playwright/test';

/**
 * Base Page Object with common functionality for all pages.
 */
export class BasePage {
  readonly page: Page;

  // Header elements
  readonly header: Locator;
  readonly logo: Locator;
  readonly connectionStatus: Locator;

  // Navigation
  readonly navTabs: Locator;
  readonly activeTab: Locator;

  // Sidebar toggle
  readonly sidebarToggle: Locator;
  readonly sidebar: Locator;

  // Toast notifications
  readonly toasts: Locator;

  // Loading indicators
  readonly spinner: Locator;
  readonly loadingOverlay: Locator;

  constructor(page: Page) {
    this.page = page;

    // Header
    this.header = page.locator('header, [role="banner"]');
    this.logo = page.locator('.logo, [data-testid="logo"]');
    this.connectionStatus = page.locator('[data-testid="connection-status"], .connection-status');

    // Navigation
    this.navTabs = page.locator('nav button, nav a, [role="tablist"] [role="tab"]');
    this.activeTab = page.locator('nav button.active, nav a.active, [role="tab"][aria-selected="true"]');

    // Sidebar
    this.sidebarToggle = page.locator('[data-testid="sidebar-toggle"], .sidebar-toggle');
    this.sidebar = page.locator('aside, [role="complementary"], .sidebar');

    // Toasts
    this.toasts = page.locator('.toast, [role="alert"], .notification');

    // Loading
    this.spinner = page.locator('.spinner, [role="progressbar"], .loading');
    this.loadingOverlay = page.locator('.loading-overlay, [data-loading="true"]');
  }

  /**
   * Navigate to a specific page by URL path.
   */
  async goto(path: string = '/') {
    await this.page.goto(path);
    await this.waitForPageLoad();
  }

  /**
   * Wait for page to fully load.
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Wait for loading overlay to disappear.
   */
  async waitForLoadingComplete() {
    await this.loadingOverlay.waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {});
    await this.spinner.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
  }

  /**
   * Navigate to a tab by name.
   */
  async navigateToTab(tabName: string) {
    const tab = this.navTabs.filter({ hasText: tabName }).first();
    await tab.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Get the currently active tab name.
   */
  async getActiveTabName(): Promise<string> {
    return await this.activeTab.textContent() || '';
  }

  /**
   * Check if sidebar is visible.
   */
  async isSidebarVisible(): Promise<boolean> {
    return await this.sidebar.isVisible();
  }

  /**
   * Toggle sidebar visibility.
   */
  async toggleSidebar() {
    await this.sidebarToggle.click();
  }

  /**
   * Wait for toast notification with specific text.
   */
  async waitForToast(text: string, timeout: number = 5000) {
    await this.toasts.filter({ hasText: text }).first().waitFor({ timeout });
  }

  /**
   * Dismiss all visible toasts.
   */
  async dismissToasts() {
    const closeButtons = this.toasts.locator('button[aria-label="Close"], .toast-close');
    const count = await closeButtons.count();
    for (let i = 0; i < count; i++) {
      await closeButtons.nth(i).click();
    }
  }

  /**
   * Check WebSocket connection status.
   */
  async getConnectionStatus(): Promise<'connected' | 'disconnected' | 'unknown'> {
    const statusText = await this.connectionStatus.textContent();
    if (statusText?.toLowerCase().includes('connected')) return 'connected';
    if (statusText?.toLowerCase().includes('disconnected')) return 'disconnected';
    return 'unknown';
  }

  /**
   * Take a screenshot with a descriptive name.
   */
  async screenshot(name: string) {
    await this.page.screenshot({
      path: `test-results/screenshots/${name}.png`,
      fullPage: true,
    });
  }

  /**
   * Press keyboard shortcut.
   */
  async pressShortcut(keys: string) {
    await this.page.keyboard.press(keys);
  }

  /**
   * Wait for API response.
   */
  async waitForAPIResponse(urlPattern: string | RegExp) {
    return await this.page.waitForResponse(urlPattern);
  }

  /**
   * Intercept and mock API response.
   */
  async mockAPIResponse(urlPattern: string | RegExp, response: object) {
    await this.page.route(urlPattern, route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response),
      });
    });
  }

  /**
   * Get all console errors from the page.
   */
  async getConsoleErrors(): Promise<string[]> {
    const errors: string[] = [];
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    return errors;
  }

  /**
   * Scroll to bottom of page.
   */
  async scrollToBottom() {
    await this.page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
    });
  }

  /**
   * Scroll to top of page.
   */
  async scrollToTop() {
    await this.page.evaluate(() => {
      window.scrollTo(0, 0);
    });
  }

  /**
   * Wait for element to be stable (no layout shifts).
   */
  async waitForStable(locator: Locator, timeout: number = 5000) {
    await locator.waitFor({ state: 'visible', timeout });
    // Wait for any animations to complete
    await this.page.waitForTimeout(100);
  }

  /**
   * Fill input field with value.
   */
  async fillInput(selector: string, value: string) {
    const input = this.page.locator(selector);
    await input.clear();
    await input.fill(value);
  }

  /**
   * Select option from dropdown.
   */
  async selectOption(selector: string, value: string) {
    await this.page.selectOption(selector, value);
  }

  /**
   * Check checkbox.
   */
  async checkCheckbox(selector: string) {
    const checkbox = this.page.locator(selector);
    if (!(await checkbox.isChecked())) {
      await checkbox.check();
    }
  }

  /**
   * Uncheck checkbox.
   */
  async uncheckCheckbox(selector: string) {
    const checkbox = this.page.locator(selector);
    if (await checkbox.isChecked()) {
      await checkbox.uncheck();
    }
  }
}
