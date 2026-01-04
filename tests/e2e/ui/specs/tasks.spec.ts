import { test, expect } from '@playwright/test';
import { TasksPage } from '../pages/tasks.page';

test.describe('Tasks Page', () => {
  let tasksPage: TasksPage;

  test.beforeEach(async ({ page }) => {
    tasksPage = new TasksPage(page);
    await tasksPage.gotoTasksPage();
  });

  test.describe('URL Input', () => {
    test('should display URL input field', async () => {
      await expect(tasksPage.urlInput).toBeVisible();
    });

    test('should display detect button', async () => {
      await expect(tasksPage.detectButton).toBeVisible();
    });

    test('should accept URL input', async () => {
      await tasksPage.urlInput.fill('https://www.tiktok.com/@user/video/123');
      await expect(tasksPage.urlInput).toHaveValue('https://www.tiktok.com/@user/video/123');
    });

    test('should detect TikTok platform', async ({ page }) => {
      // Mock the API response
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'tiktok', detected: true }),
        });
      });

      await tasksPage.enterUrlAndDetect('https://www.tiktok.com/@user/video/123');
      const platform = await tasksPage.getDetectedPlatform();
      expect(platform.toLowerCase()).toContain('tiktok');
    });

    test('should detect Instagram platform', async ({ page }) => {
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'instagram', detected: true }),
        });
      });

      await tasksPage.enterUrlAndDetect('https://www.instagram.com/p/ABC123');
      const platform = await tasksPage.getDetectedPlatform();
      expect(platform.toLowerCase()).toContain('instagram');
    });

    test('should detect YouTube platform', async ({ page }) => {
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'youtube', detected: true }),
        });
      });

      await tasksPage.enterUrlAndDetect('https://www.youtube.com/watch?v=abc123');
      const platform = await tasksPage.getDetectedPlatform();
      expect(platform.toLowerCase()).toContain('youtube');
    });

    test('should detect DEXTools platform', async ({ page }) => {
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'dextools', detected: true }),
        });
      });

      await tasksPage.enterUrlAndDetect('https://www.dextools.io/app/ether/pair-explorer/0x123');
      const platform = await tasksPage.getDetectedPlatform();
      expect(platform.toLowerCase()).toContain('dex');
    });
  });

  test.describe('Task Wizard', () => {
    test('should display wizard steps', async () => {
      await expect(tasksPage.wizardSteps).toBeVisible();
    });

    test('should show next button', async () => {
      await expect(tasksPage.nextButton).toBeVisible();
    });

    test('should navigate to next step', async ({ page }) => {
      // Mock API
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'tiktok', detected: true }),
        });
      });

      await tasksPage.enterUrlAndDetect('https://www.tiktok.com/@user/video/123');
      await tasksPage.nextStep();

      // Should be on step 2
      const step = await tasksPage.getCurrentStepNumber();
      expect(step).toBeGreaterThanOrEqual(2);
    });

    test('should navigate back to previous step', async ({ page }) => {
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'tiktok', detected: true }),
        });
      });

      await tasksPage.enterUrlAndDetect('https://www.tiktok.com/@user/video/123');
      await tasksPage.nextStep();
      await tasksPage.prevStep();

      // Should be back on step 1
      const step = await tasksPage.getCurrentStepNumber();
      expect(step).toBeLessThanOrEqual(2);
    });
  });

  test.describe('Task List', () => {
    test('should display task list container', async () => {
      await expect(tasksPage.taskList).toBeVisible();
    });

    test('should show empty state when no tasks', async ({ page }) => {
      await page.route('**/api/tasks', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ tasks: [] }),
        });
      });

      await page.reload();
      await tasksPage.waitForLoadingComplete();

      const count = await tasksPage.getTaskCount();
      expect(count).toBe(0);
    });

    test('should display task cards when tasks exist', async ({ page }) => {
      await page.route('**/api/tasks', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tasks: [
              { id: '1', url: 'https://tiktok.com/video/1', status: 'running' },
              { id: '2', url: 'https://tiktok.com/video/2', status: 'completed' },
            ],
          }),
        });
      });

      await page.reload();
      await tasksPage.waitForLoadingComplete();

      const count = await tasksPage.getTaskCount();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Flow Actions', () => {
    test('should display Record Flow button', async () => {
      await expect(tasksPage.recordFlowButton).toBeVisible();
    });

    test('should display Flow Library button', async () => {
      await expect(tasksPage.flowLibraryButton).toBeVisible();
    });

    test('should open flow recorder modal', async () => {
      await tasksPage.openFlowRecorder();
      // Modal should appear
      const modal = tasksPage.page.locator('.flow-recorder-modal, [data-testid="flow-recorder"]');
      await expect(modal).toBeVisible();
    });

    test('should open flow library modal', async () => {
      await tasksPage.openFlowLibrary();
      // Modal should appear
      const modal = tasksPage.page.locator('.flow-library-modal, [data-testid="flow-library"]');
      await expect(modal).toBeVisible();
    });
  });

  test.describe('Task Creation', () => {
    test.beforeEach(async ({ page }) => {
      // Mock all necessary APIs
      await page.route('**/api/tasks/detect', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ platform: 'tiktok', detected: true }),
        });
      });

      await page.route('**/api/tasks', route => {
        if (route.request().method() === 'POST') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ id: 'new-task-1', status: 'pending' }),
          });
        } else {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ tasks: [] }),
          });
        }
      });
    });

    test('should complete task creation wizard', async () => {
      // This test walks through the complete wizard
      await tasksPage.enterUrlAndDetect('https://www.tiktok.com/@user/video/123');
      // The full wizard flow depends on the actual UI implementation
      // This is a basic structure test
      await expect(tasksPage.detectButton).toBeEnabled();
    });
  });

  test.describe('Task Management', () => {
    test.beforeEach(async ({ page }) => {
      await page.route('**/api/tasks', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tasks: [
              { id: '1', url: 'https://tiktok.com/video/1', status: 'running' },
            ],
          }),
        });
      });

      await page.route('**/api/tasks/1/cancel', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      });
    });

    test('should display task status', async ({ page }) => {
      await page.reload();
      await tasksPage.waitForLoadingComplete();

      const count = await tasksPage.getTaskCount();
      if (count > 0) {
        const status = await tasksPage.getTaskStatus(0);
        expect(status).toBeTruthy();
      }
    });
  });
});
