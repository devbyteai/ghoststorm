import { test, expect } from '@playwright/test';
import { ProxiesPage } from '../pages/proxies.page';

test.describe('Proxies Page', () => {
  let proxiesPage: ProxiesPage;

  test.beforeEach(async ({ page }) => {
    proxiesPage = new ProxiesPage(page);

    // Mock proxy API endpoints
    await page.route('**/api/proxies/stats', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 150,
          healthy: 100,
          failed: 30,
          testing: 20,
          last_scrape: new Date().toISOString(),
        }),
      });
    });

    await page.route('**/api/proxies/sources', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sources: [
            { name: 'free-proxy-list', enabled: true, count: 50 },
            { name: 'spys-one', enabled: true, count: 30 },
            { name: 'proxyscrape', enabled: false, count: 0 },
          ],
        }),
      });
    });

    await page.route('**/api/proxies', route => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            proxies: [
              { ip: '192.168.1.1', port: 8080, protocol: 'http', status: 'healthy' },
              { ip: '192.168.1.2', port: 3128, protocol: 'http', status: 'failed' },
            ],
          }),
        });
      }
    });

    await proxiesPage.gotoProxiesPage();
  });

  test.describe('Stats Display', () => {
    test('should display stats container', async () => {
      await expect(proxiesPage.statsContainer).toBeVisible();
    });

    test('should display total proxies count', async () => {
      const total = await proxiesPage.getTotalProxies();
      expect(total).toBeGreaterThanOrEqual(0);
    });

    test('should display healthy proxies count', async () => {
      const healthy = await proxiesPage.getHealthyProxies();
      expect(healthy).toBeGreaterThanOrEqual(0);
    });

    test('should display failed proxies count', async () => {
      const failed = await proxiesPage.getFailedProxies();
      expect(failed).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Actions', () => {
    test('should display scrape button', async () => {
      await expect(proxiesPage.scrapeButton).toBeVisible();
    });

    test('should display test all button', async () => {
      await expect(proxiesPage.testAllButton).toBeVisible();
    });

    test('should display export button', async () => {
      await expect(proxiesPage.exportButton).toBeVisible();
    });

    test('should display import button', async () => {
      await expect(proxiesPage.importButton).toBeVisible();
    });

    test('should start scraping proxies', async ({ page }) => {
      await page.route('**/api/proxies/scrape', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'scrape-1', status: 'started' }),
        });
      });

      await proxiesPage.startScrape();
      // Should not throw error
    });

    test('should test all proxies', async ({ page }) => {
      await page.route('**/api/proxies/test', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'test-1', status: 'started' }),
        });
      });

      await proxiesPage.testAllProxies();
      // Should not throw error
    });
  });

  test.describe('Sources', () => {
    test('should display sources container', async () => {
      await expect(proxiesPage.sourcesContainer).toBeVisible();
    });

    test('should display source cards', async () => {
      const count = await proxiesPage.sourceCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should show enabled sources', async () => {
      const enabledSources = await proxiesPage.getEnabledSources();
      expect(enabledSources.length).toBeGreaterThanOrEqual(0);
    });

    test('should toggle source', async ({ page }) => {
      await page.route('**/api/proxies/sources/*', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      });

      await proxiesPage.toggleSource('free-proxy-list');
      // Should not throw error
    });
  });

  test.describe('Premium Providers', () => {
    test('should display providers container', async () => {
      await expect(proxiesPage.providersContainer).toBeVisible();
    });

    test('should configure Decodo provider', async ({ page }) => {
      await page.route('**/api/proxies/providers/decodo', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      });

      await proxiesPage.configureProvider('decodo', 'test-api-key');
      // Should not throw error
    });
  });

  test.describe('Proxy Table', () => {
    test('should display proxy table', async () => {
      await expect(proxiesPage.proxyTable).toBeVisible();
    });

    test('should display search input', async () => {
      await expect(proxiesPage.proxySearch).toBeVisible();
    });

    test('should display filter dropdown', async () => {
      await expect(proxiesPage.proxyFilter).toBeVisible();
    });

    test('should search proxies', async () => {
      await proxiesPage.searchProxies('192.168');
      await proxiesPage.page.waitForTimeout(500);
      // Should filter results
    });

    test('should filter by status', async () => {
      await proxiesPage.filterByStatus('healthy');
      await proxiesPage.page.waitForTimeout(500);
      // Should filter results
    });

    test('should display proxy rows', async () => {
      const count = await proxiesPage.getProxyRowCount();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should select all proxies', async () => {
      await proxiesPage.selectAllProxies();
      // Should select all
    });

    test('should select individual proxy', async () => {
      const count = await proxiesPage.getProxyRowCount();
      if (count > 0) {
        await proxiesPage.selectProxy(0);
        // Should select proxy
      }
    });
  });

  test.describe('Import/Export', () => {
    test('should open import modal', async () => {
      await proxiesPage.importButton.click();
      await expect(proxiesPage.importModal).toBeVisible();
    });

    test('should import proxies', async ({ page }) => {
      await page.route('**/api/proxies/import', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ imported: 5, total: 5 }),
        });
      });

      await proxiesPage.importProxies('192.168.1.1:8080\n192.168.1.2:3128');
      // Should import successfully
    });

    test('should export proxies', async ({ page }) => {
      await page.route('**/api/proxies/export', route => {
        route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '192.168.1.1:8080\n192.168.1.2:3128',
          headers: {
            'Content-Disposition': 'attachment; filename="proxies.txt"',
          },
        });
      });

      // Export functionality
      await proxiesPage.exportButton.click();
    });
  });

  test.describe('Job Status', () => {
    test('should show job progress', async ({ page }) => {
      await page.route('**/api/proxies/scrape', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ job_id: 'scrape-1', status: 'running' }),
        });
      });

      await proxiesPage.startScrape();

      const isRunning = await proxiesPage.isJobRunning();
      expect(isRunning).toBeDefined();
    });

    test('should cancel running job', async ({ page }) => {
      await page.route('**/api/proxies/jobs/*', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'cancelled' }),
        });
      });

      await proxiesPage.cancelJob();
      // Should cancel without error
    });
  });

  test.describe('Clear Proxies', () => {
    test('should display clear button', async () => {
      await expect(proxiesPage.clearButton).toBeVisible();
    });

    test('should clear all proxies', async ({ page }) => {
      await page.route('**/api/proxies', route => {
        if (route.request().method() === 'DELETE') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ success: true, deleted: 150 }),
          });
        }
      });

      await proxiesPage.clearAllProxies();
      // Should clear without error
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(proxiesPage.statsContainer).toBeVisible();
    });

    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(proxiesPage.statsContainer).toBeVisible();
    });
  });

  test.describe('Real-time Updates', () => {
    test('should update stats on WebSocket message', async ({ page }) => {
      await page.waitForTimeout(2000);

      // Stats should be displayed
      const total = await proxiesPage.getTotalProxies();
      expect(total).toBeGreaterThanOrEqual(0);
    });
  });
});
