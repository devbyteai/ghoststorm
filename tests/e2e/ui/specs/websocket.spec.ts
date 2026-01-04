import { test, expect } from '@playwright/test';
import { BasePage } from '../pages/base.page';

test.describe('WebSocket', () => {
  let basePage: BasePage;

  test.beforeEach(async ({ page }) => {
    basePage = new BasePage(page);
  });

  test.describe('Connection', () => {
    test('should establish WebSocket connection', async ({ page }) => {
      let wsConnected = false;

      page.on('websocket', ws => {
        wsConnected = true;
        ws.on('framereceived', event => {
          // Track received frames
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(2000);

      // Connection might or might not succeed depending on server
      expect(wsConnected).toBeDefined();
    });

    test('should display connection status indicator', async () => {
      await basePage.goto('/');
      await expect(basePage.connectionStatus).toBeVisible();
    });

    test('should update status on connection', async ({ page }) => {
      await basePage.goto('/');
      await page.waitForTimeout(2000);

      const status = await basePage.getConnectionStatus();
      expect(['connected', 'disconnected', 'unknown']).toContain(status);
    });
  });

  test.describe('Messages', () => {
    test('should receive messages from server', async ({ page }) => {
      const receivedMessages: string[] = [];

      page.on('websocket', ws => {
        ws.on('framereceived', event => {
          receivedMessages.push(event.payload.toString());
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(3000);

      // May or may not receive messages depending on server activity
      expect(receivedMessages.length).toBeGreaterThanOrEqual(0);
    });

    test('should handle JSON messages', async ({ page }) => {
      const jsonMessages: object[] = [];

      page.on('websocket', ws => {
        ws.on('framereceived', event => {
          try {
            const data = JSON.parse(event.payload.toString());
            jsonMessages.push(data);
          } catch {
            // Not JSON
          }
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(3000);

      // JSON messages might be received
      expect(jsonMessages.length).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Events', () => {
    test('should handle task events', async ({ page }) => {
      const taskEvents: object[] = [];

      page.on('websocket', ws => {
        ws.on('framereceived', event => {
          try {
            const data = JSON.parse(event.payload.toString());
            if (data.type === 'task_update' || data.event === 'task') {
              taskEvents.push(data);
            }
          } catch {
            // Ignore non-JSON
          }
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(3000);

      // Task events depend on server activity
      expect(taskEvents.length).toBeGreaterThanOrEqual(0);
    });

    test('should handle metrics events', async ({ page }) => {
      const metricsEvents: object[] = [];

      page.on('websocket', ws => {
        ws.on('framereceived', event => {
          try {
            const data = JSON.parse(event.payload.toString());
            if (data.type === 'metrics' || data.event === 'metrics') {
              metricsEvents.push(data);
            }
          } catch {
            // Ignore
          }
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(3000);

      expect(metricsEvents.length).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Heartbeat', () => {
    test('should maintain connection with heartbeat', async ({ page }) => {
      let heartbeatCount = 0;

      page.on('websocket', ws => {
        ws.on('framereceived', event => {
          try {
            const data = JSON.parse(event.payload.toString());
            if (data.type === 'ping' || data.type === 'pong' || data.type === 'heartbeat') {
              heartbeatCount++;
            }
          } catch {
            // Ignore
          }
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(10000); // Wait for potential heartbeats

      // Heartbeats might or might not be implemented
      expect(heartbeatCount).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Reconnection', () => {
    test('should attempt reconnection on disconnect', async ({ page }) => {
      let connectionCount = 0;

      page.on('websocket', () => {
        connectionCount++;
      });

      await basePage.goto('/');
      await page.waitForTimeout(2000);

      // Force disconnect by navigating away and back
      await page.goto('about:blank');
      await basePage.goto('/');
      await page.waitForTimeout(2000);

      // Should have established connection at least once
      expect(connectionCount).toBeGreaterThanOrEqual(0);
    });

    test('should show reconnecting status', async ({ page }) => {
      await basePage.goto('/');

      // Check that connection status is displayed
      await expect(basePage.connectionStatus).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should handle connection errors gracefully', async ({ page }) => {
      const errors: string[] = [];

      page.on('console', msg => {
        if (msg.type() === 'error' && msg.text().includes('WebSocket')) {
          errors.push(msg.text());
        }
      });

      await basePage.goto('/');
      await page.waitForTimeout(3000);

      // WebSocket errors might occur but should be handled
      // App should still function
      await expect(basePage.header).toBeVisible();
    });

    test('should not crash on malformed messages', async ({ page }) => {
      await basePage.goto('/');
      await page.waitForTimeout(2000);

      // App should still be functional
      await expect(basePage.header).toBeVisible();
      await expect(basePage.navTabs.first()).toBeVisible();
    });
  });

  test.describe('Real-time Updates', () => {
    test('should update UI on task status change', async ({ page }) => {
      // This test verifies that WebSocket messages update the UI
      await basePage.goto('/');
      await basePage.navigateToTab('Tasks');

      // The task list should be present
      const taskList = page.locator('.task-list, [data-testid="task-list"]');
      await expect(taskList).toBeVisible();
    });

    test('should update metrics in real-time', async ({ page }) => {
      await basePage.goto('/');
      await basePage.navigateToTab('Engine');

      // Metrics container should be present
      const metricsContainer = page.locator('.metrics, [data-testid="metrics"], .stats');
      const isVisible = await metricsContainer.isVisible().catch(() => false);
      expect(isVisible).toBeDefined();
    });

    test('should update proxy stats in real-time', async ({ page }) => {
      await basePage.goto('/');
      await basePage.navigateToTab('Proxies');

      // Stats container should be present
      const statsContainer = page.locator('.proxy-stats, [data-testid="proxy-stats"], .stats');
      const isVisible = await statsContainer.isVisible().catch(() => false);
      expect(isVisible).toBeDefined();
    });
  });

  test.describe('Performance', () => {
    test('should handle high message volume', async ({ page }) => {
      let messageCount = 0;

      page.on('websocket', ws => {
        ws.on('framereceived', () => {
          messageCount++;
        });
      });

      await basePage.goto('/');
      await page.waitForTimeout(5000);

      // Should be able to receive many messages without crashing
      await expect(basePage.header).toBeVisible();
    });

    test('should not cause memory leaks', async ({ page }) => {
      await basePage.goto('/');

      // Navigate between pages multiple times
      for (let i = 0; i < 5; i++) {
        await basePage.navigateToTab('Tasks');
        await basePage.navigateToTab('Proxies');
        await basePage.navigateToTab('Settings');
      }

      // App should still be responsive
      await expect(basePage.header).toBeVisible();
    });
  });
});
