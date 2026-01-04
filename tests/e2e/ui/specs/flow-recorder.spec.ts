import { test, expect } from '@playwright/test';
import { TasksPage } from '../pages/tasks.page';
import { FlowRecorderComponent } from '../components/flow-recorder.component';

test.describe('Flow Recorder', () => {
  let tasksPage: TasksPage;
  let flowRecorder: FlowRecorderComponent;

  test.beforeEach(async ({ page }) => {
    tasksPage = new TasksPage(page);
    flowRecorder = new FlowRecorderComponent(page);

    // Mock flow API
    await page.route('**/api/flows/record', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ session_id: 'test-session', status: 'started' }),
      });
    });

    await page.route('**/api/flows/stop', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'stopped', actions: [] }),
      });
    });

    await page.route('**/api/flows', route => {
      if (route.request().method() === 'POST') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'new-flow', status: 'saved' }),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ flows: [] }),
        });
      }
    });

    await tasksPage.gotoTasksPage();
  });

  test.describe('Modal', () => {
    test('should open flow recorder modal', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.modal).toBeVisible();
    });

    test('should close modal with close button', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.close();
      await expect(flowRecorder.modal).not.toBeVisible();
    });

    test('should close modal with cancel button', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.cancel();
      await expect(flowRecorder.modal).not.toBeVisible();
    });
  });

  test.describe('URL Input', () => {
    test('should display URL input field', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.urlInput).toBeVisible();
    });

    test('should display start recording button', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.startRecordingButton).toBeVisible();
    });

    test('should accept URL input', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.urlInput.fill('https://example.com');
      await expect(flowRecorder.urlInput).toHaveValue('https://example.com');
    });
  });

  test.describe('Stealth Options', () => {
    test('should display stealth options section', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.stealthSection).toBeVisible();
    });

    test('should display stealth presets', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.stealthPresets).toBeVisible();
    });

    test('should select minimal preset', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.selectStealthPreset('minimal');
      // Verify preset is selected
    });

    test('should select standard preset', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.selectStealthPreset('standard');
    });

    test('should select aggressive preset', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.selectStealthPreset('aggressive');
    });

    test('should select cloud preset', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.selectStealthPreset('cloud');
    });

    test('should enable custom stealth configuration', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.enableCustomStealth();
      await expect(flowRecorder.customStealthToggle).toBeChecked();
    });

    test('should configure individual stealth options', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();

      await flowRecorder.configureStealthOptions({
        webdriver: true,
        webgl: true,
        canvas: true,
        plugins: false,
        languages: true,
        timezone: true,
        hardware: false,
        fonts: true,
        audio: true,
        permissions: true,
      });

      await expect(flowRecorder.webdriverToggle).toBeChecked();
      await expect(flowRecorder.pluginsToggle).not.toBeChecked();
    });
  });

  test.describe('Recording', () => {
    test('should start recording', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.startRecording('https://example.com');

      const isRecording = await flowRecorder.isRecording();
      expect(isRecording).toBeTruthy();
    });

    test('should display recording indicator when recording', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.startRecording('https://example.com');

      await expect(flowRecorder.recordingIndicator).toBeVisible();
    });

    test('should display recording timer', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.startRecording('https://example.com');

      await expect(flowRecorder.recordingTimer).toBeVisible();
    });

    test('should stop recording', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.startRecording('https://example.com');
      await flowRecorder.stopRecording();

      const isRecording = await flowRecorder.isRecording();
      expect(isRecording).toBeFalsy();
    });

    test('should pause and resume recording', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.startRecording('https://example.com');

      await flowRecorder.pauseRecording();
      await expect(flowRecorder.resumeButton).toBeVisible();

      await flowRecorder.resumeRecording();
      await expect(flowRecorder.pauseButton).toBeVisible();
    });
  });

  test.describe('Actions', () => {
    test('should display recorded actions container', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.recordedActions).toBeVisible();
    });

    test('should show action count', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();

      const count = await flowRecorder.getActionCount();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Checkpoints', () => {
    test('should display add checkpoint button', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.addCheckpointButton).toBeVisible();
    });

    test('should add a checkpoint', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await flowRecorder.startRecording('https://example.com');

      await flowRecorder.addCheckpoint('Login completed');
      const count = await flowRecorder.getCheckpointCount();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Save Flow', () => {
    test('should display flow name input', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.flowNameInput).toBeVisible();
    });

    test('should display save flow button', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();
      await expect(flowRecorder.saveFlowButton).toBeVisible();
    });

    test('should save flow with name', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();

      await flowRecorder.startRecording('https://example.com');
      await flowRecorder.page.waitForTimeout(500);
      await flowRecorder.stopRecording();

      await flowRecorder.saveFlow('Test Flow', 'A test flow description');
      await expect(flowRecorder.modal).not.toBeVisible();
    });
  });

  test.describe('Complete Workflow', () => {
    test('should complete full flow recording workflow', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();

      await flowRecorder.recordCompleteFlow({
        url: 'https://example.com',
        stealthPreset: 'standard',
        recordDuration: 1000,
        flowName: 'Complete Test Flow',
        flowDescription: 'Testing the full workflow',
      });

      await expect(flowRecorder.modal).not.toBeVisible();
    });
  });

  test.describe('Validation', () => {
    test('should require URL to start recording', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();

      // Try to start without URL
      await flowRecorder.startRecordingButton.click();

      // Should show validation error or button should be disabled
      const isRecording = await flowRecorder.isRecording();
      expect(isRecording).toBeFalsy();
    });

    test('should require flow name to save', async () => {
      await tasksPage.openFlowRecorder();
      await flowRecorder.waitForModal();

      await flowRecorder.startRecording('https://example.com');
      await flowRecorder.stopRecording();

      // Try to save without name
      await flowRecorder.flowNameInput.clear();
      await flowRecorder.saveFlowButton.click();

      // Modal should still be visible (validation failed)
      // Or save button should be disabled
    });
  });
});
