import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Tasks Page Object - handles the 6-step task creation wizard.
 */
export class TasksPage extends BasePage {
  // URL Input section
  readonly urlInput: Locator;
  readonly detectButton: Locator;
  readonly platformBadge: Locator;

  // Wizard steps
  readonly wizardSteps: Locator;
  readonly currentStep: Locator;
  readonly nextButton: Locator;
  readonly prevButton: Locator;
  readonly submitButton: Locator;

  // Step 1: Platform
  readonly platformSelect: Locator;
  readonly platformCards: Locator;

  // Step 2: Task Type
  readonly taskTypeSelect: Locator;
  readonly taskTypeCards: Locator;

  // Step 3: Target Config
  readonly targetUrlInput: Locator;
  readonly videoIdInput: Locator;
  readonly usernameInput: Locator;

  // Step 4: Behavior
  readonly behaviorPresets: Locator;
  readonly watchTimeSlider: Locator;
  readonly interactionToggles: Locator;

  // Step 5: Proxy Config
  readonly proxyToggle: Locator;
  readonly proxyTypeSelect: Locator;
  readonly proxyCountInput: Locator;

  // Step 6: Review
  readonly reviewSummary: Locator;
  readonly startTaskButton: Locator;

  // Task list
  readonly taskList: Locator;
  readonly taskCards: Locator;
  readonly noTasksMessage: Locator;

  // Flow actions
  readonly recordFlowButton: Locator;
  readonly loadFlowButton: Locator;
  readonly flowLibraryButton: Locator;

  constructor(page: Page) {
    super(page);

    // URL Input
    this.urlInput = page.locator('input[placeholder*="URL"], input[name="url"], #url-input');
    this.detectButton = page.locator('button:has-text("Detect"), button:has-text("Auto-detect")');
    this.platformBadge = page.locator('.platform-badge, [data-testid="platform-badge"]');

    // Wizard
    this.wizardSteps = page.locator('.wizard-steps, [role="tablist"], .step-indicator');
    this.currentStep = page.locator('.step-active, [aria-current="step"]');
    this.nextButton = page.locator('button:has-text("Next"), button:has-text("Continue")');
    this.prevButton = page.locator('button:has-text("Back"), button:has-text("Previous")');
    this.submitButton = page.locator('button:has-text("Create Task"), button:has-text("Start")');

    // Step 1: Platform
    this.platformSelect = page.locator('select[name="platform"], #platform-select');
    this.platformCards = page.locator('.platform-card, [data-testid="platform-option"]');

    // Step 2: Task Type
    this.taskTypeSelect = page.locator('select[name="task_type"], #task-type-select');
    this.taskTypeCards = page.locator('.task-type-card, [data-testid="task-type-option"]');

    // Step 3: Target
    this.targetUrlInput = page.locator('input[name="target_url"], #target-url');
    this.videoIdInput = page.locator('input[name="video_id"], #video-id');
    this.usernameInput = page.locator('input[name="username"], #username');

    // Step 4: Behavior
    this.behaviorPresets = page.locator('.behavior-preset, [data-testid="behavior-preset"]');
    this.watchTimeSlider = page.locator('input[type="range"][name="watch_time"]');
    this.interactionToggles = page.locator('.interaction-toggle, [data-testid="interaction-toggle"]');

    // Step 5: Proxy
    this.proxyToggle = page.locator('input[type="checkbox"][name="use_proxy"], #use-proxy');
    this.proxyTypeSelect = page.locator('select[name="proxy_type"], #proxy-type');
    this.proxyCountInput = page.locator('input[name="proxy_count"], #proxy-count');

    // Step 6: Review
    this.reviewSummary = page.locator('.review-summary, [data-testid="review-summary"]');
    this.startTaskButton = page.locator('button:has-text("Start Task"), button:has-text("Create")');

    // Task list
    this.taskList = page.locator('.task-list, [data-testid="task-list"]');
    this.taskCards = page.locator('.task-card, [data-testid="task-card"]');
    this.noTasksMessage = page.locator(':has-text("No tasks"), :has-text("no active tasks")');

    // Flow actions
    this.recordFlowButton = page.locator('button:has-text("Record Flow"), button:has-text("Record")');
    this.loadFlowButton = page.locator('button:has-text("Load Flow"), button:has-text("Import")');
    this.flowLibraryButton = page.locator('button:has-text("Flow Library"), button:has-text("Library")');
  }

  /**
   * Navigate to Tasks page.
   */
  async gotoTasksPage() {
    await this.goto('/');
    await this.navigateToTab('Tasks');
  }

  /**
   * Enter URL and detect platform.
   */
  async enterUrlAndDetect(url: string) {
    await this.urlInput.fill(url);
    await this.detectButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Get detected platform name.
   */
  async getDetectedPlatform(): Promise<string> {
    return await this.platformBadge.textContent() || '';
  }

  /**
   * Select platform by name.
   */
  async selectPlatform(platform: string) {
    const platformCard = this.platformCards.filter({ hasText: platform });
    await platformCard.click();
  }

  /**
   * Select task type by name.
   */
  async selectTaskType(taskType: string) {
    const typeCard = this.taskTypeCards.filter({ hasText: taskType });
    await typeCard.click();
  }

  /**
   * Go to next wizard step.
   */
  async nextStep() {
    await this.nextButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Go to previous wizard step.
   */
  async prevStep() {
    await this.prevButton.click();
  }

  /**
   * Get current step number.
   */
  async getCurrentStepNumber(): Promise<number> {
    const stepText = await this.currentStep.textContent();
    const match = stepText?.match(/\d+/);
    return match ? parseInt(match[0]) : 0;
  }

  /**
   * Configure target URL.
   */
  async setTargetUrl(url: string) {
    await this.targetUrlInput.fill(url);
  }

  /**
   * Select behavior preset.
   */
  async selectBehaviorPreset(preset: string) {
    const presetOption = this.behaviorPresets.filter({ hasText: preset });
    await presetOption.click();
  }

  /**
   * Configure proxy settings.
   */
  async configureProxy(enabled: boolean, type?: string, count?: number) {
    if (enabled) {
      await this.checkCheckbox('input[name="use_proxy"]');
      if (type) {
        await this.selectOption('select[name="proxy_type"]', type);
      }
      if (count) {
        await this.proxyCountInput.fill(count.toString());
      }
    } else {
      await this.uncheckCheckbox('input[name="use_proxy"]');
    }
  }

  /**
   * Submit task creation.
   */
  async submitTask() {
    await this.startTaskButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Get count of task cards.
   */
  async getTaskCount(): Promise<number> {
    return await this.taskCards.count();
  }

  /**
   * Click a task card by index.
   */
  async clickTask(index: number) {
    await this.taskCards.nth(index).click();
  }

  /**
   * Get task status by index.
   */
  async getTaskStatus(index: number): Promise<string> {
    const statusBadge = this.taskCards.nth(index).locator('.status, [data-status]');
    return await statusBadge.textContent() || '';
  }

  /**
   * Open flow recorder modal.
   */
  async openFlowRecorder() {
    await this.recordFlowButton.click();
  }

  /**
   * Open flow library modal.
   */
  async openFlowLibrary() {
    await this.flowLibraryButton.click();
  }

  /**
   * Create a complete task with all steps.
   */
  async createTask(config: {
    url: string;
    platform?: string;
    taskType?: string;
    useProxy?: boolean;
    proxyType?: string;
    behaviorPreset?: string;
  }) {
    // Enter URL
    await this.enterUrlAndDetect(config.url);

    // Step 1: Platform (auto-detected or select)
    if (config.platform) {
      await this.selectPlatform(config.platform);
    }
    await this.nextStep();

    // Step 2: Task Type
    if (config.taskType) {
      await this.selectTaskType(config.taskType);
    }
    await this.nextStep();

    // Step 3: Target config (URL already set)
    await this.nextStep();

    // Step 4: Behavior
    if (config.behaviorPreset) {
      await this.selectBehaviorPreset(config.behaviorPreset);
    }
    await this.nextStep();

    // Step 5: Proxy
    await this.configureProxy(
      config.useProxy ?? true,
      config.proxyType,
    );
    await this.nextStep();

    // Step 6: Review & Submit
    await this.submitTask();
  }

  /**
   * Wait for task list to update.
   */
  async waitForTaskListUpdate(previousCount: number) {
    await expect(async () => {
      const currentCount = await this.getTaskCount();
      expect(currentCount).not.toBe(previousCount);
    }).toPass({ timeout: 10000 });
  }

  /**
   * Cancel a task by index.
   */
  async cancelTask(index: number) {
    const taskCard = this.taskCards.nth(index);
    const cancelButton = taskCard.locator('button:has-text("Cancel"), button[aria-label="Cancel"]');
    await cancelButton.click();

    // Confirm cancellation if dialog appears
    const confirmButton = this.page.locator('button:has-text("Confirm"), button:has-text("Yes")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Retry a failed task by index.
   */
  async retryTask(index: number) {
    const taskCard = this.taskCards.nth(index);
    const retryButton = taskCard.locator('button:has-text("Retry"), button[aria-label="Retry"]');
    await retryButton.click();
  }
}
