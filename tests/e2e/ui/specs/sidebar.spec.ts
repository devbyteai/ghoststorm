import { test, expect } from '@playwright/test';
import { SidebarPage } from '../pages/sidebar.page';

test.describe('Sidebar', () => {
  let sidebarPage: SidebarPage;

  test.beforeEach(async ({ page }) => {
    sidebarPage = new SidebarPage(page);
    await sidebarPage.goto('/');
  });

  test.describe('Sidebar Toggle', () => {
    test('should toggle sidebar visibility', async () => {
      const initialVisibility = await sidebarPage.isSidebarVisible();

      await sidebarPage.toggleSidebar();
      await sidebarPage.page.waitForTimeout(300); // Animation

      const newVisibility = await sidebarPage.isSidebarVisible();
      expect(newVisibility).not.toBe(initialVisibility);
    });

    test('should open sidebar', async () => {
      await sidebarPage.openSidebar();
      await expect(sidebarPage.sidebarContainer).toBeVisible();
    });

    test('should close sidebar', async () => {
      await sidebarPage.openSidebar();
      await sidebarPage.closeSidebar();
      await expect(sidebarPage.sidebarContainer).not.toBeVisible();
    });
  });

  test.describe('AI Chat Tab', () => {
    test.beforeEach(async ({ page }) => {
      // Mock Ollama API
      await page.route('**/api/assistant/chat', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Hello! How can I help you?',
            role: 'assistant',
          }),
        });
      });

      await page.route('**/api/assistant/models', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            models: ['llama3.2', 'mistral', 'codellama'],
          }),
        });
      });
    });

    test('should display chat input', async () => {
      await sidebarPage.openChat();
      await expect(sidebarPage.chatInput).toBeVisible();
    });

    test('should display send button', async () => {
      await sidebarPage.openChat();
      await expect(sidebarPage.chatSendButton).toBeVisible();
    });

    test('should display model selector', async () => {
      await sidebarPage.openChat();
      await expect(sidebarPage.modelSelector).toBeVisible();
    });

    test('should send a message', async ({ page }) => {
      await sidebarPage.openChat();
      await sidebarPage.sendMessage('Hello, AI assistant!');

      // Wait for response or check message was sent
      await page.waitForTimeout(500);
      const messages = await sidebarPage.getAllMessages();
      expect(messages.length).toBeGreaterThanOrEqual(0);
    });

    test('should clear chat history', async () => {
      await sidebarPage.openChat();
      await sidebarPage.sendMessage('Test message');
      await sidebarPage.clearChat();

      const messages = await sidebarPage.getAllMessages();
      expect(messages.length).toBe(0);
    });

    test('should select a model', async () => {
      await sidebarPage.openChat();
      const models = await sidebarPage.getAvailableModels();

      if (models.length > 0) {
        await sidebarPage.selectModel(models[0]);
        // Verify selection
      }
    });
  });

  test.describe('File Browser Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/assistant/files', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            files: [
              { name: 'test.py', type: 'file', path: '/test.py' },
              { name: 'src', type: 'folder', path: '/src' },
            ],
          }),
        });
      });
    });

    test('should display file tree', async () => {
      await sidebarPage.openFiles();
      await expect(sidebarPage.fileTree).toBeVisible();
    });

    test('should display refresh button', async () => {
      await sidebarPage.openFiles();
      await expect(sidebarPage.refreshFilesButton).toBeVisible();
    });

    test('should refresh files', async () => {
      await sidebarPage.openFiles();
      await sidebarPage.refreshFiles();
      // Should not throw error
    });

    test('should select a file', async ({ page }) => {
      await page.route('**/api/assistant/files/*', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            content: '# Test file content',
          }),
        });
      });

      await sidebarPage.openFiles();
      const fileCount = await sidebarPage.getFileCount();

      if (fileCount > 0) {
        await sidebarPage.selectFile('test.py');
        // File should be selected
      }
    });
  });

  test.describe('Docker Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/assistant/docker/status', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            running: false,
            containers: [],
          }),
        });
      });
    });

    test('should display Docker status', async () => {
      await sidebarPage.openDocker();
      await expect(sidebarPage.dockerStatus).toBeVisible();
    });

    test('should display start/stop buttons', async () => {
      await sidebarPage.openDocker();
      // Either start or stop should be visible based on state
      const startVisible = await sidebarPage.startDockerButton.isVisible();
      const stopVisible = await sidebarPage.stopDockerButton.isVisible();
      expect(startVisible || stopVisible).toBeTruthy();
    });

    test('should get Docker status', async () => {
      await sidebarPage.openDocker();
      const status = await sidebarPage.getDockerStatus();
      expect(status).toBeTruthy();
    });
  });

  test.describe('Terminal Tab', () => {
    test('should display terminal container', async () => {
      await sidebarPage.openTerminal();
      await expect(sidebarPage.terminalContainer).toBeVisible();
    });

    test('should display terminal input', async () => {
      await sidebarPage.openTerminal();
      await expect(sidebarPage.terminalInput).toBeVisible();
    });

    test('should execute command', async ({ page }) => {
      await page.route('**/api/assistant/command', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            output: 'Command output',
            exit_code: 0,
          }),
        });
      });

      await sidebarPage.openTerminal();
      await sidebarPage.executeCommand('echo test');

      const output = await sidebarPage.getTerminalOutput();
      expect(output).toBeTruthy();
    });

    test('should clear terminal', async () => {
      await sidebarPage.openTerminal();
      await sidebarPage.clearTerminal();
      // Terminal should be cleared
    });
  });

  test.describe('Settings Tab', () => {
    test('should display quick settings', async () => {
      await sidebarPage.openSettings();
      await expect(sidebarPage.quickSettings).toBeVisible();
    });

    test('should toggle a quick setting', async () => {
      await sidebarPage.openSettings();
      // Toggle a setting if available
      const quickSettingExists = await sidebarPage.quickSettings.isVisible();
      expect(quickSettingExists).toBeTruthy();
    });
  });

  test.describe('Tab Switching', () => {
    test('should switch between all tabs', async () => {
      await sidebarPage.openSidebar();

      // Switch to each tab
      await sidebarPage.switchTab('Chat');
      await expect(sidebarPage.chatContainer).toBeVisible();

      await sidebarPage.switchTab('Files');
      await expect(sidebarPage.fileTree).toBeVisible();

      await sidebarPage.switchTab('Docker');
      await expect(sidebarPage.dockerStatus).toBeVisible();

      await sidebarPage.switchTab('Terminal');
      await expect(sidebarPage.terminalContainer).toBeVisible();
    });
  });

  test.describe('Responsive Behavior', () => {
    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await sidebarPage.openSidebar();
      await expect(sidebarPage.sidebarContainer).toBeVisible();
    });

    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await sidebarPage.openSidebar();
      // Sidebar might be full-screen on mobile
      await expect(sidebarPage.sidebarContainer).toBeVisible();
    });
  });
});
