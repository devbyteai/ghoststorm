// ============ AI ASSISTANT SIDEBAR ============

let sidebarOpen = false;
let settingsOpen = false;
let chatMessages = [];
let pendingActions = [];
let currentModel = 'qwen2.5-coder:32b';
let isStreaming = false;
let isPulling = false;

// Initialize sidebar
document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
    loadModels();
    setupKeyboardShortcuts();
});

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl + K to toggle sidebar
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            toggleSidebar();
        }
        // Escape to close sidebar
        if (e.key === 'Escape' && sidebarOpen) {
            toggleSidebar();
        }
    });
}

function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    const sidebar = document.getElementById('ai-sidebar');
    const mainContent = document.getElementById('pages-container');
    const toggleBtn = document.getElementById('sidebar-toggle-btn');

    if (sidebarOpen) {
        sidebar.classList.remove('translate-x-full');
        sidebar.classList.add('translate-x-0');
        mainContent.classList.add('mr-96');
        toggleBtn.classList.add('bg-primary/20');
        document.getElementById('chat-input')?.focus();
    } else {
        sidebar.classList.remove('translate-x-0');
        sidebar.classList.add('translate-x-full');
        mainContent.classList.remove('mr-96');
        toggleBtn.classList.remove('bg-primary/20');
    }
}

// ============ CHAT FUNCTIONS ============

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message || isStreaming) return;

    input.value = '';
    addMessage('user', message);

    isStreaming = true;
    updateSendButton();

    try {
        const response = await fetch('/api/assistant/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, stream: false }),
        });

        const data = await response.json();

        if (data.content) {
            addMessage('assistant', data.content);
        }

        if (data.has_pending_actions) {
            loadPendingActions();
        }
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    } finally {
        isStreaming = false;
        updateSendButton();
    }
}

function addMessage(role, content) {
    const msg = { role, content, timestamp: new Date().toISOString() };
    chatMessages.push(msg);
    saveChatHistory();
    renderMessages();
}

function renderMessages() {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    container.innerHTML = chatMessages.map((msg, i) => {
        const isUser = msg.role === 'user';
        const isSystem = msg.role === 'system';

        let bgClass = isUser ? 'bg-primary/20' : isSystem ? 'bg-red-500/20' : 'bg-surface-light';
        let alignClass = isUser ? 'ml-8' : 'mr-8';

        // Parse code blocks
        const formattedContent = formatContent(msg.content);

        return `
            <div class="message ${alignClass} ${bgClass} rounded-lg p-3 text-sm">
                <div class="flex items-center gap-2 mb-1 text-xs text-gray-400">
                    <span>${isUser ? 'You' : isSystem ? 'System' : 'Assistant'}</span>
                    <span>${new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="message-content prose prose-invert prose-sm max-w-none">
                    ${formattedContent}
                </div>
            </div>
        `;
    }).join('');

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function formatContent(content) {
    // Escape HTML
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre class="bg-gray-800 rounded p-2 overflow-x-auto"><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
    });

    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="bg-gray-700 px-1 rounded">$1</code>');

    // Bold
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

function updateSendButton() {
    const btn = document.getElementById('send-btn');
    if (!btn) return;

    if (isStreaming) {
        btn.disabled = true;
        btn.innerHTML = `
            <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
        `;
    } else {
        btn.disabled = false;
        btn.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
        `;
    }
}

// ============ ACTIONS ============

async function loadPendingActions() {
    try {
        const response = await fetch('/api/assistant/pending');
        const data = await response.json();
        pendingActions = data.pending || [];
        renderPendingActions();
    } catch (error) {
        console.error('Failed to load pending actions:', error);
    }
}

function renderPendingActions() {
    const container = document.getElementById('pending-actions');
    if (!container) return;

    if (pendingActions.length === 0) {
        container.innerHTML = '';
        container.classList.add('hidden');
        return;
    }

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="text-xs font-medium text-amber-400 mb-2">Pending Actions</div>
        ${pendingActions.map(([id, action]) => `
            <div class="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-2">
                <div class="text-sm font-medium text-amber-300 mb-1">${action.type}</div>
                <div class="text-xs text-gray-400 mb-2 font-mono">${action.command || action.path || ''}</div>
                <div class="flex gap-2">
                    <button onclick="approveAction('${id}')" class="flex-1 px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-xs">
                        Approve
                    </button>
                    <button onclick="rejectAction('${id}')" class="flex-1 px-2 py-1 bg-red-600 hover:bg-red-500 rounded text-xs">
                        Reject
                    </button>
                </div>
            </div>
        `).join('')}
    `;
}

async function approveAction(actionId) {
    try {
        const response = await fetch('/api/assistant/action/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action_id: actionId, approved: true }),
        });
        const data = await response.json();
        addMessage('system', `Action executed: ${JSON.stringify(data.result, null, 2)}`);
        loadPendingActions();
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

async function rejectAction(actionId) {
    try {
        await fetch('/api/assistant/action/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action_id: actionId, approved: false }),
        });
        addMessage('system', 'Action rejected');
        loadPendingActions();
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

// ============ MODELS ============

async function loadModels() {
    try {
        const response = await fetch('/api/assistant/models');
        const data = await response.json();

        const select = document.getElementById('model-select');
        if (!select) return;

        if (data.models && data.models.length > 0) {
            // Sort: recommended models first, then others
            const recommended = new Set(data.recommended || []);
            const sortedModels = [...data.models].sort((a, b) => {
                const aRec = recommended.has(a) || data.recommended?.some(r => a.startsWith(r.split(':')[0]));
                const bRec = recommended.has(b) || data.recommended?.some(r => b.startsWith(r.split(':')[0]));
                if (aRec && !bRec) return -1;
                if (!aRec && bRec) return 1;
                return a.localeCompare(b);
            });

            select.innerHTML = sortedModels.map(model => {
                const isRecommended = recommended.has(model) || data.recommended?.some(r => model.startsWith(r.split(':')[0]));
                const isBest = model === data.best_available;
                const label = isBest ? `${model} (Best)` : isRecommended ? `${model} (Coding)` : model;
                const selected = model === data.current ? 'selected' : '';
                return `<option value="${model}" ${selected}>${label}</option>`;
            }).join('');

            currentModel = data.current;

            // Auto-select best available if current isn't a coding model
            if (data.best_available && data.current !== data.best_available) {
                const isCurrent = data.recommended?.some(r => data.current.startsWith(r.split(':')[0]));
                if (!isCurrent) {
                    await changeModel(data.best_available);
                    addMessage('system', `Auto-selected best coding model: ${data.best_available}`);
                }
            }
        } else if (data.error) {
            select.innerHTML = `<option value="qwen2.5-coder:32b">qwen2.5-coder:32b (Ollama offline)</option>`;
            addMessage('system', `Ollama offline. Install a coding model:\n\`\`\`\nollama pull qwen2.5-coder:32b\n\`\`\``);
        }
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

async function changeModel(modelOverride = null) {
    const select = document.getElementById('model-select');
    if (!select && !modelOverride) return;

    const model = modelOverride || select.value;
    try {
        await fetch(`/api/assistant/models/set?model=${encodeURIComponent(model)}`, {
            method: 'POST',
        });
        currentModel = model;
        if (select) select.value = model;
        if (!modelOverride) {
            addMessage('system', `Switched to model: ${model}`);
        }
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

// ============ FILE BROWSER ============

async function browseFiles(path = '.') {
    try {
        const response = await fetch(`/api/assistant/files?path=${encodeURIComponent(path)}&recursive=false`);
        const data = await response.json();

        if (data.error) {
            addMessage('system', `Error: ${data.error}`);
            return;
        }

        const modal = document.getElementById('file-browser-modal');
        const list = document.getElementById('file-list');

        if (!modal || !list) return;

        list.innerHTML = data.files.map(file => `
            <div class="flex items-center gap-2 p-2 hover:bg-surface-light rounded cursor-pointer" onclick="selectFile('${file}')">
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <span class="text-sm truncate">${file}</span>
            </div>
        `).join('');

        modal.classList.remove('hidden');
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

async function selectFile(path) {
    try {
        const response = await fetch(`/api/assistant/file?path=${encodeURIComponent(path)}`);
        const data = await response.json();

        if (data.error) {
            addMessage('system', `Error: ${data.error}`);
            return;
        }

        // Add file content to chat context
        addMessage('system', `File: ${path}\n\`\`\`\n${data.content.substring(0, 2000)}${data.content.length > 2000 ? '\n...(truncated)' : ''}\n\`\`\``);

        closeFileModal();
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

function closeFileModal() {
    const modal = document.getElementById('file-browser-modal');
    if (modal) modal.classList.add('hidden');
}

// ============ QUICK ACTIONS ============

function quickSearch() {
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('search-input');
    const results = document.getElementById('search-results');

    if (modal) {
        modal.classList.remove('hidden');
        results.innerHTML = '';
        if (input) {
            input.value = '';
            input.focus();
        }
    }
}

function closeSearchModal() {
    const modal = document.getElementById('search-modal');
    if (modal) modal.classList.add('hidden');
}

async function executeSearch() {
    const input = document.getElementById('search-input');
    const pattern = document.getElementById('search-pattern');
    const resultsEl = document.getElementById('search-results');

    const query = input?.value.trim();
    if (!query) return;

    const filePattern = pattern?.value || '*.py';

    resultsEl.innerHTML = '<p class="text-gray-400">Searching...</p>';

    try {
        const response = await fetch('/api/assistant/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, file_pattern: filePattern }),
        });
        const data = await response.json();

        if (data.error) {
            resultsEl.innerHTML = `<p class="text-red-400">Error: ${data.error}</p>`;
            return;
        }

        if (!data.matches || data.matches.length === 0) {
            resultsEl.innerHTML = `<p class="text-gray-400">No matches found for: ${query}</p>`;
            return;
        }

        resultsEl.innerHTML = data.matches.slice(0, 20).map(m => `
            <div class="p-2 hover:bg-surface-light rounded cursor-pointer mb-1" onclick="openSearchResult('${m.file}', ${m.line})">
                <div class="text-xs text-primary">${m.file}:${m.line}</div>
                <div class="text-gray-300 truncate">${escapeHtml(m.content)}</div>
            </div>
        `).join('');

        // Also add to chat
        const chatResults = data.matches.slice(0, 10).map(m =>
            `${m.file}:${m.line}: ${m.content}`
        ).join('\n');
        addMessage('system', `Search results for "${query}":\n\`\`\`\n${chatResults}\n\`\`\``);

    } catch (error) {
        resultsEl.innerHTML = `<p class="text-red-400">Error: ${error.message}</p>`;
    }
}

async function openSearchResult(file, line) {
    closeSearchModal();
    try {
        const response = await fetch(`/api/assistant/file?path=${encodeURIComponent(file)}`);
        const data = await response.json();

        if (data.error) {
            addMessage('system', `Error: ${data.error}`);
            return;
        }

        // Show a snippet around the line
        const lines = data.content.split('\n');
        const start = Math.max(0, line - 3);
        const end = Math.min(lines.length, line + 3);
        const snippet = lines.slice(start, end).map((l, i) => {
            const lineNum = start + i + 1;
            const marker = lineNum === line ? '>' : ' ';
            return `${marker}${lineNum}: ${l}`;
        }).join('\n');

        addMessage('system', `File: ${file}\n\`\`\`\n${snippet}\n\`\`\``);
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

function quickExecute() {
    const modal = document.getElementById('terminal-modal');
    const input = document.getElementById('terminal-input');
    const output = document.getElementById('terminal-output');

    if (modal) {
        modal.classList.remove('hidden');
        output.innerHTML = '<p class="text-gray-500">Output will appear here...</p>';
        if (input) {
            input.value = '';
            input.focus();
        }
    }
}

function closeTerminalModal() {
    const modal = document.getElementById('terminal-modal');
    if (modal) modal.classList.add('hidden');
}

async function executeTerminalCommand() {
    const input = document.getElementById('terminal-input');
    const output = document.getElementById('terminal-output');

    const command = input?.value.trim();
    if (!command) return;

    output.innerHTML = `<p class="text-green-400">$ ${escapeHtml(command)}</p><p class="text-gray-400">Running...</p>`;

    try {
        const response = await fetch('/api/assistant/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command }),
        });
        const data = await response.json();

        if (data.requires_approval) {
            output.innerHTML = `
                <p class="text-green-400">$ ${escapeHtml(command)}</p>
                <p class="text-yellow-400">Command requires approval. Check pending actions in chat.</p>
            `;
            addMessage('system', 'Command requires approval. Check pending actions.');
            loadPendingActions();
            return;
        }

        if (data.status === 'blocked') {
            output.innerHTML = `
                <p class="text-green-400">$ ${escapeHtml(command)}</p>
                <p class="text-red-400">Blocked: ${escapeHtml(data.stderr)}</p>
            `;
            return;
        }

        const result = data.stdout || data.stderr || '(no output)';
        output.innerHTML = `
            <p class="text-green-400">$ ${escapeHtml(command)}</p>
            <pre class="text-gray-300 whitespace-pre-wrap">${escapeHtml(result)}</pre>
            ${data.exit_code !== 0 ? `<p class="text-red-400">Exit code: ${data.exit_code}</p>` : ''}
        `;

        // Also add to chat
        addMessage('system', `Command: ${command}\n\`\`\`\n${result}\n\`\`\``);

        // Clear input for next command
        input.value = '';

    } catch (error) {
        output.innerHTML = `
            <p class="text-green-400">$ ${escapeHtml(command)}</p>
            <p class="text-red-400">Error: ${error.message}</p>
        `;
    }
}

// ============ PERSISTENCE ============

function saveChatHistory() {
    try {
        // Keep last 50 messages
        const toSave = chatMessages.slice(-50);
        localStorage.setItem('ghoststorm_chat', JSON.stringify(toSave));
    } catch (error) {
        console.error('Failed to save chat history:', error);
    }
}

function loadChatHistory() {
    try {
        const saved = localStorage.getItem('ghoststorm_chat');
        if (saved) {
            chatMessages = JSON.parse(saved);
            renderMessages();
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

function clearChat() {
    if (!confirm('Clear chat history?')) return;
    chatMessages = [];
    localStorage.removeItem('ghoststorm_chat');
    renderMessages();

    // Reset server conversation
    fetch('/api/assistant/reset', { method: 'POST' }).catch(() => {});
}

// Handle enter key in input
document.addEventListener('keydown', (e) => {
    if (e.target.id === 'chat-input' && e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ============ SETTINGS ============

function toggleSettings() {
    settingsOpen = !settingsOpen;
    const chatPanel = document.getElementById('chat-panel');
    const settingsPanel = document.getElementById('settings-panel');

    if (settingsOpen) {
        chatPanel.classList.add('hidden');
        settingsPanel.classList.remove('hidden');
        loadSettings();
    } else {
        chatPanel.classList.remove('hidden');
        settingsPanel.classList.add('hidden');
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/assistant/settings');
        const data = await response.json();

        // Update sliders
        document.getElementById('temp-slider').value = data.temperature;
        document.getElementById('temp-value').textContent = data.temperature.toFixed(1);
        document.getElementById('tokens-slider').value = data.max_tokens;
        document.getElementById('tokens-value').textContent = data.max_tokens;
        document.getElementById('timeout-slider').value = data.command_timeout;
        document.getElementById('timeout-value').textContent = data.command_timeout + 's';

        // Update recommended models list
        renderRecommendedModels(data.recommended_models);

        // Load installed models
        await loadInstalledModels();
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function loadInstalledModels() {
    try {
        const response = await fetch('/api/assistant/models');
        const data = await response.json();

        const container = document.getElementById('installed-models');
        if (!container) return;

        if (data.models && data.models.length > 0) {
            container.innerHTML = data.models.map(model => `
                <div class="flex items-center justify-between p-2 bg-surface-light rounded mb-1">
                    <div class="flex items-center gap-2">
                        <input type="radio" name="active-model" value="${model}"
                               ${model === data.current ? 'checked' : ''}
                               onchange="selectModel('${model}')"
                               class="text-primary">
                        <span class="text-sm">${model}</span>
                        ${model === data.current ? '<span class="text-xs text-green-400">(active)</span>' : ''}
                    </div>
                    <button onclick="deleteModel('${model}')" class="p-1 hover:bg-red-600/30 rounded text-red-400" title="Delete">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="text-gray-400 text-sm">No models installed</p>';
        }
    } catch (error) {
        console.error('Failed to load installed models:', error);
    }
}

function renderRecommendedModels(models) {
    const container = document.getElementById('recommended-models');
    if (!container) return;

    container.innerHTML = models.map(model => `
        <button onclick="pullModel('${model}')"
                class="flex items-center justify-between w-full p-2 bg-surface-light hover:bg-gray-600 rounded mb-1 text-left"
                ${isPulling ? 'disabled' : ''}>
            <span class="text-sm">${model}</span>
            <svg class="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
        </button>
    `).join('');
}

async function selectModel(model) {
    try {
        await fetch(`/api/assistant/models/set?model=${encodeURIComponent(model)}`, {
            method: 'POST',
        });
        currentModel = model;
        addMessage('system', `Switched to model: ${model}`);
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

async function pullModel(model) {
    if (isPulling) return;

    isPulling = true;
    const progressContainer = document.getElementById('pull-progress');
    const progressBar = document.getElementById('pull-progress-bar');
    const progressText = document.getElementById('pull-progress-text');

    progressContainer.classList.remove('hidden');
    progressText.textContent = `Pulling ${model}...`;
    progressBar.style.width = '0%';

    try {
        const response = await fetch(`/api/assistant/models/pull?model=${encodeURIComponent(model)}`, {
            method: 'POST',
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const lines = decoder.decode(value).split('\n');
            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    if (data.total && data.completed) {
                        const percent = Math.round((data.completed / data.total) * 100);
                        progressBar.style.width = `${percent}%`;
                        progressText.textContent = `${model}: ${percent}% (${formatBytes(data.completed)}/${formatBytes(data.total)})`;
                    } else if (data.status) {
                        progressText.textContent = `${model}: ${data.status}`;
                    } else if (data.error) {
                        progressText.textContent = `Error: ${data.error}`;
                    }
                } catch (e) {}
            }
        }

        progressBar.style.width = '100%';
        progressText.textContent = `${model} installed successfully!`;
        await loadInstalledModels();

        setTimeout(() => {
            progressContainer.classList.add('hidden');
        }, 2000);

    } catch (error) {
        progressText.textContent = `Error: ${error.message}`;
    } finally {
        isPulling = false;
    }
}

async function deleteModel(model) {
    if (!confirm(`Delete model ${model}?`)) return;

    try {
        const response = await fetch(`/api/assistant/models/${encodeURIComponent(model)}`, {
            method: 'DELETE',
        });

        if (response.ok) {
            addMessage('system', `Deleted model: ${model}`);
            await loadInstalledModels();
        } else {
            const data = await response.json();
            addMessage('system', `Error: ${data.detail || 'Failed to delete'}`);
        }
    } catch (error) {
        addMessage('system', `Error: ${error.message}`);
    }
}

async function updateSetting(setting, value) {
    try {
        await fetch(`/api/assistant/settings?${setting}=${value}`, {
            method: 'POST',
        });
    } catch (error) {
        console.error('Failed to update setting:', error);
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

async function pullCustomModel() {
    const input = document.getElementById('custom-model-input');
    const model = input.value.trim();
    if (!model) return;

    input.value = '';
    await pullModel(model);
}

// ============ DOCKER/OLLAMA MANAGEMENT ============

let dockerPollingInterval = null;
let dockerLogsVisible = false;

async function checkDockerStatus() {
    try {
        const response = await fetch('/api/assistant/docker/status');
        const data = await response.json();
        updateDockerUI(data);
        return data;
    } catch (error) {
        updateDockerUI({
            docker_available: false,
            container_exists: false,
            container_running: false,
            error: 'Failed to check status'
        });
        return null;
    }
}

function updateDockerUI(status) {
    const statusEl = document.getElementById('docker-status');
    const startBtn = document.getElementById('docker-start-btn');
    const stopBtn = document.getElementById('docker-stop-btn');
    const errorEl = document.getElementById('docker-error');

    if (!statusEl) return;

    // Update status indicator
    let statusDot, statusText;

    if (!status.docker_available) {
        statusDot = 'bg-red-500';
        statusText = status.error || 'Docker unavailable';
        errorEl.textContent = status.error || 'Docker is not installed or not running';
        errorEl.classList.remove('hidden');
    } else if (status.container_running) {
        statusDot = 'bg-green-500';
        statusText = 'Running';
        errorEl.classList.add('hidden');
    } else if (status.container_exists) {
        statusDot = 'bg-yellow-500';
        statusText = 'Stopped';
        errorEl.classList.add('hidden');
    } else {
        statusDot = 'bg-gray-500';
        statusText = 'Not created';
        errorEl.classList.add('hidden');
    }

    statusEl.innerHTML = `
        <span class="w-2 h-2 rounded-full ${statusDot}"></span>
        <span class="text-xs text-gray-400">${statusText}</span>
    `;

    // Update buttons
    if (startBtn && stopBtn) {
        if (!status.docker_available) {
            startBtn.disabled = true;
            stopBtn.disabled = true;
        } else if (status.container_running) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }
}

async function startOllama() {
    const startBtn = document.getElementById('docker-start-btn');
    const errorEl = document.getElementById('docker-error');

    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = `
            <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Starting...
        `;
    }

    try {
        const response = await fetch('/api/assistant/docker/start', {
            method: 'POST',
        });

        const data = await response.json();

        if (response.ok) {
            addMessage('system', `Ollama container ${data.status}${data.gpu === false ? ' (CPU mode - no GPU detected)' : ' with GPU support'}`);
            errorEl.classList.add('hidden');

            // Start polling for status
            startDockerPolling();

            // Reload models after a short delay (container needs time to start)
            setTimeout(loadModels, 3000);
        } else {
            throw new Error(data.detail || 'Failed to start container');
        }
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
        addMessage('system', `Error starting Ollama: ${error.message}`);
    } finally {
        await checkDockerStatus();
        if (startBtn) {
            startBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                Start Ollama
            `;
        }
    }
}

async function stopOllama() {
    const stopBtn = document.getElementById('docker-stop-btn');

    if (stopBtn) {
        stopBtn.disabled = true;
        stopBtn.innerHTML = `
            <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Stopping...
        `;
    }

    try {
        const response = await fetch('/api/assistant/docker/stop', {
            method: 'POST',
        });

        const data = await response.json();

        if (data.status === 'stopped' || data.status === 'already_stopped') {
            addMessage('system', 'Ollama container stopped');
            stopDockerPolling();
        }
    } catch (error) {
        addMessage('system', `Error stopping Ollama: ${error.message}`);
    } finally {
        await checkDockerStatus();
        if (stopBtn) {
            stopBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
                </svg>
                Stop
            `;
        }
    }
}

function toggleDockerLogs() {
    const logsEl = document.getElementById('docker-logs');
    const chevron = document.getElementById('docker-logs-chevron');

    if (!logsEl) return;

    dockerLogsVisible = !dockerLogsVisible;

    if (dockerLogsVisible) {
        logsEl.classList.remove('hidden');
        chevron.classList.add('rotate-180');
        fetchDockerLogs();
    } else {
        logsEl.classList.add('hidden');
        chevron.classList.remove('rotate-180');
    }
}

async function fetchDockerLogs() {
    const logsEl = document.getElementById('docker-logs');
    if (!logsEl || !dockerLogsVisible) return;

    try {
        const response = await fetch('/api/assistant/docker/logs?tail=50');

        if (!response.ok) {
            logsEl.innerHTML = '<p class="text-gray-500">Container not running</p>';
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let logs = '';

        // Read a limited amount then stop
        const { value } = await reader.read();
        if (value) {
            logs = decoder.decode(value);
        }
        reader.cancel();

        if (logs.trim()) {
            logsEl.innerHTML = `<pre class="whitespace-pre-wrap">${escapeHtml(logs)}</pre>`;
            logsEl.scrollTop = logsEl.scrollHeight;
        } else {
            logsEl.innerHTML = '<p class="text-gray-500">No logs available</p>';
        }
    } catch (error) {
        logsEl.innerHTML = `<p class="text-red-400">Error: ${error.message}</p>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function startDockerPolling() {
    if (dockerPollingInterval) return;
    dockerPollingInterval = setInterval(checkDockerStatus, 5000);
}

function stopDockerPolling() {
    if (dockerPollingInterval) {
        clearInterval(dockerPollingInterval);
        dockerPollingInterval = null;
    }
}

// Check Docker status when settings panel opens
const originalLoadSettings = loadSettings;
loadSettings = async function() {
    await originalLoadSettings();
    await checkDockerStatus();
};
