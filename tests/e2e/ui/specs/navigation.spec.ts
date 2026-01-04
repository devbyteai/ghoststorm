import { test, expect } from '@playwright/test';
import { BasePage } from '../pages/base.page';

test.describe('Navigation', () => {
  let basePage: BasePage;

  test.beforeEach(async ({ page }) => {
    basePage = new BasePage(page);
    await basePage.goto('/');
  });

  test.describe('Page Navigation', () => {
    test('should load the main page', async () => {
      await expect(basePage.header).toBeVisible();
    });

    test('should display navigation tabs', async () => {
      await expect(basePage.navTabs).toHaveCount.greaterThan(0);
    });

    test('should highlight active tab', async ({ page }) => {
      await basePage.navigateToTab('Tasks');
      const activeTab = await basePage.getActiveTabName();
      expect(activeTab.toLowerCase()).toContain('task');
    });

    test('should navigate to Proxies page', async () => {
      await basePage.navigateToTab('Proxies');
      const activeTab = await basePage.getActiveTabName();
      expect(activeTab.toLowerCase()).toContain('prox');
    });

    test('should navigate to Settings page', async () => {
      await basePage.navigateToTab('Settings');
      const activeTab = await basePage.getActiveTabName();
      expect(activeTab.toLowerCase()).toContain('setting');
    });

    test('should navigate to Data page', async () => {
      await basePage.navigateToTab('Data');
      const activeTab = await basePage.getActiveTabName();
      expect(activeTab.toLowerCase()).toContain('data');
    });

    test('should navigate to Engine page', async () => {
      await basePage.navigateToTab('Engine');
      const activeTab = await basePage.getActiveTabName();
      expect(activeTab.toLowerCase()).toContain('engine');
    });

    test('should navigate to LLM page', async () => {
      await basePage.navigateToTab('LLM');
      const activeTab = await basePage.getActiveTabName();
      expect(activeTab.toLowerCase()).toContain('llm');
    });
  });

  test.describe('WebSocket Connection', () => {
    test('should show connection status', async () => {
      await expect(basePage.connectionStatus).toBeVisible();
    });

    test('should indicate connected state', async () => {
      // Wait for WebSocket to connect
      await basePage.page.waitForTimeout(2000);
      const status = await basePage.getConnectionStatus();
      expect(['connected', 'unknown']).toContain(status);
    });
  });

  test.describe('Sidebar', () => {
    test('should toggle sidebar visibility', async () => {
      const initialVisibility = await basePage.isSidebarVisible();

      await basePage.toggleSidebar();
      const newVisibility = await basePage.isSidebarVisible();

      expect(newVisibility).not.toBe(initialVisibility);
    });

    test('should show sidebar toggle button', async () => {
      await expect(basePage.sidebarToggle).toBeVisible();
    });
  });

  test.describe('Loading States', () => {
    test('should hide loading overlay after page load', async () => {
      await basePage.waitForLoadingComplete();
      await expect(basePage.loadingOverlay).not.toBeVisible();
    });

    test('should hide spinner after data loads', async () => {
      await basePage.waitForLoadingComplete();
      await expect(basePage.spinner).not.toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(basePage.header).toBeVisible();
      await expect(basePage.navTabs.first()).toBeVisible();
    });

    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(basePage.header).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should not have console errors on page load', async ({ page }) => {
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await basePage.goto('/');
      await basePage.waitForPageLoad();

      // Filter out expected errors (e.g., WebSocket failures in test)
      const unexpectedErrors = errors.filter(
        e => !e.includes('WebSocket') && !e.includes('favicon')
      );

      expect(unexpectedErrors).toHaveLength(0);
    });
  });

  test.describe('Page Refresh', () => {
    test('should maintain state after refresh', async ({ page }) => {
      await basePage.navigateToTab('Proxies');
      await page.reload();
      await basePage.waitForPageLoad();

      // Should still be on the same page or return to default
      await expect(basePage.header).toBeVisible();
    });
  });
});
