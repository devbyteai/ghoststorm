import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Sidebar Page Object - handles AI chat, file browser, Docker controls.
 */
export class SidebarPage extends BasePage {
  // Sidebar container
  readonly sidebarContainer: Locator;
  readonly sidebarTabs: Locator;

  // AI Chat section
  readonly chatTab: Locator;
  readonly chatContainer: Locator;
  readonly chatInput: Locator;
  readonly chatSendButton: Locator;
  readonly chatMessages: Locator;
  readonly userMessages: Locator;
  readonly assistantMessages: Locator;
  readonly chatHistory: Locator;
  readonly clearChatButton: Locator;

  // Model selector
  readonly modelSelector: Locator;
  readonly modelOptions: Locator;

  // File browser section
  readonly filesTab: Locator;
  readonly fileTree: Locator;
  readonly fileItems: Locator;
  readonly folderItems: Locator;
  readonly selectedFile: Locator;
  readonly fileContent: Locator;
  readonly refreshFilesButton: Locator;

  // Docker section
  readonly dockerTab: Locator;
  readonly dockerStatus: Locator;
  readonly containerList: Locator;
  readonly startDockerButton: Locator;
  readonly stopDockerButton: Locator;
  readonly dockerLogs: Locator;

  // Terminal section
  readonly terminalTab: Locator;
  readonly terminalContainer: Locator;
  readonly terminalInput: Locator;
  readonly terminalOutput: Locator;
  readonly clearTerminalButton: Locator;

  // Settings quick access
  readonly settingsTab: Locator;
  readonly quickSettings: Locator;

  constructor(page: Page) {
    super(page);

    // Sidebar container
    this.sidebarContainer = page.locator('aside, .sidebar, [data-testid="sidebar"]');
    this.sidebarTabs = page.locator('.sidebar-tabs button, .sidebar [role="tablist"] [role="tab"]');

    // AI Chat
    this.chatTab = page.locator('[data-tab="chat"], button:has-text("Chat"), button:has-text("AI")');
    this.chatContainer = page.locator('.chat-container, [data-testid="chat-container"]');
    this.chatInput = page.locator('textarea[placeholder*="message"], input[placeholder*="Ask"], #chat-input');
    this.chatSendButton = page.locator('button:has-text("Send"), button[aria-label="Send"], .chat-send');
    this.chatMessages = page.locator('.chat-message, [data-testid="chat-message"]');
    this.userMessages = page.locator('.chat-message.user, [data-role="user"]');
    this.assistantMessages = page.locator('.chat-message.assistant, [data-role="assistant"]');
    this.chatHistory = page.locator('.chat-history, [data-testid="chat-history"]');
    this.clearChatButton = page.locator('button:has-text("Clear"), button[aria-label="Clear chat"]');

    // Model selector
    this.modelSelector = page.locator('select[name="model"], #model-select, .model-selector');
    this.modelOptions = page.locator('select[name="model"] option, .model-option');

    // File browser
    this.filesTab = page.locator('[data-tab="files"], button:has-text("Files"), button:has-text("Browse")');
    this.fileTree = page.locator('.file-tree, [data-testid="file-tree"]');
    this.fileItems = page.locator('.file-item, [data-type="file"]');
    this.folderItems = page.locator('.folder-item, [data-type="folder"]');
    this.selectedFile = page.locator('.file-item.selected, [data-selected="true"]');
    this.fileContent = page.locator('.file-content, [data-testid="file-content"]');
    this.refreshFilesButton = page.locator('button:has-text("Refresh"), button[aria-label="Refresh files"]');

    // Docker
    this.dockerTab = page.locator('[data-tab="docker"], button:has-text("Docker"), button:has-text("Container")');
    this.dockerStatus = page.locator('.docker-status, [data-testid="docker-status"]');
    this.containerList = page.locator('.container-list, [data-testid="container-list"]');
    this.startDockerButton = page.locator('button:has-text("Start Docker"), button:has-text("Start Container")');
    this.stopDockerButton = page.locator('button:has-text("Stop Docker"), button:has-text("Stop Container")');
    this.dockerLogs = page.locator('.docker-logs, [data-testid="docker-logs"]');

    // Terminal
    this.terminalTab = page.locator('[data-tab="terminal"], button:has-text("Terminal")');
    this.terminalContainer = page.locator('.terminal-container, [data-testid="terminal"]');
    this.terminalInput = page.locator('.terminal-input, [data-testid="terminal-input"]');
    this.terminalOutput = page.locator('.terminal-output, [data-testid="terminal-output"]');
    this.clearTerminalButton = page.locator('button:has-text("Clear Terminal"), button[aria-label="Clear terminal"]');

    // Settings
    this.settingsTab = page.locator('[data-tab="settings"], button:has-text("Settings")');
    this.quickSettings = page.locator('.quick-settings, [data-testid="quick-settings"]');
  }

  /**
   * Open sidebar if not visible.
   */
  async openSidebar() {
    if (!(await this.sidebarContainer.isVisible())) {
      await this.toggleSidebar();
    }
  }

  /**
   * Close sidebar if visible.
   */
  async closeSidebar() {
    if (await this.sidebarContainer.isVisible()) {
      await this.toggleSidebar();
    }
  }

  /**
   * Switch to a sidebar tab.
   */
  async switchTab(tabName: string) {
    await this.openSidebar();
    const tab = this.sidebarTabs.filter({ hasText: tabName });
    await tab.click();
  }

  // ==================== AI Chat Methods ====================

  /**
   * Open AI Chat tab.
   */
  async openChat() {
    await this.switchTab('Chat');
  }

  /**
   * Send a chat message.
   */
  async sendMessage(message: string) {
    await this.chatInput.fill(message);
    await this.chatSendButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Wait for assistant response.
   */
  async waitForResponse(timeout: number = 30000) {
    const initialCount = await this.assistantMessages.count();
    await expect(async () => {
      const currentCount = await this.assistantMessages.count();
      expect(currentCount).toBeGreaterThan(initialCount);
    }).toPass({ timeout });
  }

  /**
   * Get last assistant message.
   */
  async getLastResponse(): Promise<string> {
    const count = await this.assistantMessages.count();
    if (count === 0) return '';
    return await this.assistantMessages.nth(count - 1).textContent() || '';
  }

  /**
   * Get all chat messages.
   */
  async getAllMessages(): Promise<{ role: string; content: string }[]> {
    const messages: { role: string; content: string }[] = [];
    const count = await this.chatMessages.count();

    for (let i = 0; i < count; i++) {
      const msg = this.chatMessages.nth(i);
      const role = await msg.getAttribute('data-role') || 'unknown';
      const content = await msg.textContent() || '';
      messages.push({ role, content });
    }

    return messages;
  }

  /**
   * Clear chat history.
   */
  async clearChat() {
    await this.clearChatButton.click();

    // Confirm if dialog appears
    const confirmButton = this.page.locator('button:has-text("Confirm"), button:has-text("Yes")');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Select a model.
   */
  async selectModel(modelName: string) {
    await this.modelSelector.selectOption({ label: modelName });
  }

  /**
   * Get available models.
   */
  async getAvailableModels(): Promise<string[]> {
    const options = await this.modelOptions.allTextContents();
    return options.filter(o => o.trim() !== '');
  }

  // ==================== File Browser Methods ====================

  /**
   * Open Files tab.
   */
  async openFiles() {
    await this.switchTab('Files');
  }

  /**
   * Navigate to folder.
   */
  async navigateToFolder(folderPath: string) {
    const folders = folderPath.split('/').filter(f => f);
    for (const folder of folders) {
      const folderItem = this.folderItems.filter({ hasText: folder });
      await folderItem.click();
    }
  }

  /**
   * Select a file.
   */
  async selectFile(fileName: string) {
    const fileItem = this.fileItems.filter({ hasText: fileName });
    await fileItem.click();
  }

  /**
   * Get selected file content.
   */
  async getFileContent(): Promise<string> {
    return await this.fileContent.textContent() || '';
  }

  /**
   * Refresh file tree.
   */
  async refreshFiles() {
    await this.refreshFilesButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Get file count in current directory.
   */
  async getFileCount(): Promise<number> {
    return await this.fileItems.count();
  }

  // ==================== Docker Methods ====================

  /**
   * Open Docker tab.
   */
  async openDocker() {
    await this.switchTab('Docker');
  }

  /**
   * Get Docker status.
   */
  async getDockerStatus(): Promise<string> {
    return await this.dockerStatus.textContent() || '';
  }

  /**
   * Start Docker container.
   */
  async startDocker() {
    await this.startDockerButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Stop Docker container.
   */
  async stopDocker() {
    await this.stopDockerButton.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Get Docker logs.
   */
  async getDockerLogs(): Promise<string> {
    return await this.dockerLogs.textContent() || '';
  }

  /**
   * Get container count.
   */
  async getContainerCount(): Promise<number> {
    return await this.containerList.locator('.container-item').count();
  }

  // ==================== Terminal Methods ====================

  /**
   * Open Terminal tab.
   */
  async openTerminal() {
    await this.switchTab('Terminal');
  }

  /**
   * Execute command in terminal.
   */
  async executeCommand(command: string) {
    await this.terminalInput.fill(command);
    await this.terminalInput.press('Enter');
    await this.page.waitForTimeout(500); // Wait for command execution
  }

  /**
   * Get terminal output.
   */
  async getTerminalOutput(): Promise<string> {
    return await this.terminalOutput.textContent() || '';
  }

  /**
   * Clear terminal.
   */
  async clearTerminal() {
    await this.clearTerminalButton.click();
  }

  // ==================== Settings Methods ====================

  /**
   * Open Settings tab.
   */
  async openSettings() {
    await this.switchTab('Settings');
  }

  /**
   * Toggle a quick setting.
   */
  async toggleQuickSetting(settingName: string) {
    const setting = this.quickSettings.locator(`[data-setting="${settingName}"], :has-text("${settingName}")`);
    const toggle = setting.locator('input[type="checkbox"], button');
    await toggle.click();
  }
}
