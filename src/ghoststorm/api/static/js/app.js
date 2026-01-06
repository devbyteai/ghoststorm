// ============ STATE ============
let currentPlatform = 'generic';
let currentMode = 'batch';
let ws = null;
let tasks = {};
let events = [];
let currentTaskFilter = 'all';
let selectedTaskId = null;
let currentPage = 'tasks';

// Wizard state
let currentWizardStep = 1;
const WIZARD_TOTAL_STEPS = 6;
let wizardDataStats = {
    proxies: { total: 0, alive: 0, dead: 0, untested: 0 },
    user_agents: { total: 0, files: [] },
    fingerprints: { total: 0, files: [] },
    screen_sizes: { total: 0 },
    behavior: { total: 0 },
    referrers: { total: 0 },
    evasion: { total: 0 }
};

// Behavior state (Step 5)
let currentBehaviorMode = 'preset';
let currentReferrerMode = 'realistic';
let currentMouseStyle = 'natural';
let currentEngagementLevel = 'active';
let currentLLMBehaviorProvider = 'openai';

// Proxy state
let proxySources = [];
let customSources = [];
let currentScrapeJobId = null;
let currentTestJobId = null;
let scrapePollingInterval = null;
let testPollingInterval = null;
let sourcesScrapeStatus = {};

// Data manager state
let currentDataCategory = null;
let currentDataItems = [];

// Zefoy state
let zefoyJobs = {};
let selectedZefoyServices = new Set();
let zefoyPollingInterval = null;
let zefoyCaptchasSolved = 0;

// Event log resize state
let isResizing = false;
let startY = 0;
let startHeight = 0;

// Platform detection patterns
const PLATFORM_PATTERNS = {
    tiktok: [/tiktok\.com/, /vm\.tiktok\.com/],
    instagram: [/instagram\.com/],
    youtube: [/youtube\.com/, /youtu\.be/],
    dextools: [/dextools\.io/],
};

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', async () => {
    await loadPages();
    connectWebSocket();
    loadTasks();
    loadMetrics();
    setupPlatformChips();
    checkActiveScrapeJob();
    setupStealthCheckboxListeners();
});

function setupStealthCheckboxListeners() {
    // Update identity preview when stealth checkboxes are toggled manually
    const proxyEl = document.getElementById('record-use-proxy');
    const fingerprintEl = document.getElementById('record-use-fingerprint');

    if (proxyEl) {
        proxyEl.addEventListener('change', updateIdentityPreviewVisibility);
    }
    if (fingerprintEl) {
        fingerprintEl.addEventListener('change', updateIdentityPreviewVisibility);
    }
}

async function checkActiveScrapeJob() {
    try {
        const response = await fetch('/api/proxies/scrape/active');
        const data = await response.json();

        if (data.job_id) {
            // Restore the scrape job popup
            currentScrapeJobId = data.job_id;
            document.getElementById('scrape-sources-total').textContent = data.sources_total;
            document.getElementById('scrape-sources-done').textContent = data.sources_done;
            document.getElementById('scrape-proxies-found').textContent = data.proxies_found.toLocaleString();
            document.getElementById('scrape-tested-count').textContent = (data.tested_total || 0).toLocaleString();
            document.getElementById('scrape-alive-count').textContent = (data.alive_total || 0).toLocaleString();
            document.getElementById('scrape-current-source').textContent = data.current_source || 'Processing...';

            const progress = (data.sources_done / data.sources_total) * 100;
            document.getElementById('scrape-progress-bar').style.width = progress + '%';

            // Show minimized floating popup (less intrusive on page load)
            document.getElementById('scrape-floating').classList.remove('hidden');
            updateFloatingProgress(data);

            // Start polling
            scrapePollingInterval = setInterval(pollScrapeJob, 500);
            addEvent('info', 'Reconnected to running scrape job');
        }
    } catch (error) {
        // No active scrape job or error - that's fine
    }
}

async function loadPages() {
    const pages = ['tasks', 'knowledge-base', 'proxies', 'data', 'settings', 'zefoy', 'engine', 'algorithms', 'llm', 'docs'];
    const container = document.getElementById('pages-container');

    for (const page of pages) {
        try {
            const response = await fetch(`/static/pages/${page}.html`);
            if (response.ok) {
                const html = await response.text();
                container.insertAdjacentHTML('beforeend', html);
            }
        } catch (error) {
            console.error(`Failed to load ${page} page:`, error);
        }
    }
}

function setupPlatformChips() {
    document.querySelectorAll('.platform-chip').forEach(chip => {
        chip.addEventListener('click', () => setPlatform(chip.dataset.platform));
    });
}

// ============ KNOWLEDGE BASE ============
function toggleAccordion(id) {
    const content = document.getElementById(id);
    const icon = document.getElementById(id + '-icon');
    if (content) {
        content.classList.toggle('hidden');
    }
    if (icon) {
        icon.classList.toggle('rotate-180');
    }
}

// ============ PAGE NAVIGATION ============
function switchPage(page) {
    currentPage = page;

    document.querySelectorAll('.main-tab').forEach(tab => {
        if (tab.dataset.page === page) {
            tab.classList.add('border-primary', 'text-primary', 'bg-surface-light/50');
            tab.classList.remove('border-transparent', 'text-gray-400');
        } else {
            tab.classList.remove('border-primary', 'text-primary', 'bg-surface-light/50');
            tab.classList.add('border-transparent', 'text-gray-400');
        }
    });

    document.querySelectorAll('.page-content').forEach(p => {
        p.classList.add('hidden');
    });
    document.getElementById(`page-${page}`).classList.remove('hidden');

    if (page === 'proxies') {
        loadProxyStats();
        loadProxySources();
    } else if (page === 'data') {
        loadDataStats();
    } else if (page === 'zefoy') {
        loadZefoyStats();
        loadZefoyJobs();
        setupZefoyServiceButtons();
        loadZefoyServiceStatus();
    } else if (page === 'algorithms') {
        loadAlgorithmStats();
    } else if (page === 'engine') {
        loadEngineStats();
        loadEngineJobs();
        loadEnginePresets();
    } else if (page === 'settings') {
        loadSettings();
    } else if (page === 'docs') {
        initDocsPage();
    }
}

// ============ WEBSOCKET ============
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`);

    ws.onopen = () => {
        updateConnectionStatus(true);
        addEvent('system', 'Connected to server');
    };

    ws.onclose = () => {
        updateConnectionStatus(false);
        addEvent('system', 'Disconnected from server');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'task_created':
        case 'task_started':
        case 'task_progress':
        case 'task_completed':
            updateTaskFromEvent(data);
            break;
        case 'task_failed':
            updateTaskFromEvent(data);
            // Also forward to LLM handler for AI Control page
            if (window.llmEventHandler) {
                window.llmEventHandler(data);
            }
            break;
        case 'video_watched':
            addEvent('success', `Video watched: ${data.data?.duration?.toFixed(1)}s`);
            break;
        case 'bio_clicked':
            addEvent('action', 'Bio link clicked');
            break;
        case 'proxy_rotated':
            addEvent('info', 'Proxy rotated');
            break;
        case 'heartbeat':
            break;

        // LLM/AI events - forward to LLM page handler
        case 'llm_navigated':
        case 'llm_analysis_ready':
        case 'llm_task_complete':
        case 'llm.analyzing':
        case 'llm.analysis_ready':
        case 'llm.action_suggested':
        case 'llm.action_executing':
        case 'llm.action_completed':
        case 'llm.task_complete':
        case 'llm.vision_fallback':
        case 'dom_extracted':
        case 'dom.extracted':
        case 'dom.element_found':
        case 'screenshot_captured':
        case 'visual.screenshot_live':
            // Forward to LLM page handler if registered
            if (window.llmEventHandler) {
                window.llmEventHandler(data);
            }
            // Also add to event log
            addEvent('info', `${data.type}`);
            break;

        default:
            if (data.type !== 'connected' && data.type !== 'pong') {
                addEvent('info', `${data.type}: ${JSON.stringify(data.data || {})}`);
            }
    }
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    const dot = status.querySelector('span:first-child');
    const text = status.querySelector('span:last-child');

    if (connected) {
        dot.className = 'w-2 h-2 rounded-full bg-green-500';
        text.textContent = 'Connected';
    } else {
        dot.className = 'w-2 h-2 rounded-full bg-red-500';
        text.textContent = 'Disconnected';
    }
}

// ============ PLATFORM DETECTION ============
function detectPlatform(url) {
    let detected = 'generic';
    for (const [platform, patterns] of Object.entries(PLATFORM_PATTERNS)) {
        if (patterns.some(p => p.test(url))) {
            detected = platform;
            break;
        }
    }
    setPlatform(detected);
}

function setPlatform(platform) {
    currentPlatform = platform;
    document.querySelectorAll('.platform-chip').forEach(chip => {
        chip.classList.remove('active', 'ring-2', 'ring-white/50');
        if (chip.dataset.platform === platform) {
            chip.classList.add('active', 'ring-2', 'ring-white/50');
        }
    });
}

function clearUrl() {
    document.getElementById('url-input').value = '';
    setPlatform('generic');
}

// ============ CONFIG TABS ============
function switchConfigTab(tab) {
    document.querySelectorAll('.config-tab').forEach(t => {
        t.classList.remove('border-primary', 'text-primary');
        t.classList.add('border-transparent', 'text-gray-400');
    });
    document.querySelector(`[data-tab="${tab}"]`).classList.add('border-primary', 'text-primary');
    document.querySelector(`[data-tab="${tab}"]`).classList.remove('border-transparent', 'text-gray-400');

    document.querySelectorAll('.config-section').forEach(s => s.classList.add('hidden'));
    document.getElementById(`tab-${tab}`).classList.remove('hidden');
}

// ============ WIZARD NAVIGATION ============
function goToWizardStep(step) {
    if (step < 1 || step > WIZARD_TOTAL_STEPS) return;

    // Validate step 1 before proceeding
    if (currentWizardStep === 1 && step > 1) {
        const url = document.getElementById('url-input')?.value.trim();
        if (!url) {
            addEvent('error', 'Please enter a URL first');
            return;
        }
    }

    currentWizardStep = step;
    updateWizardUI();
    loadWizardStepData(step);
}

function nextWizardStep() {
    goToWizardStep(currentWizardStep + 1);
}

function prevWizardStep() {
    goToWizardStep(currentWizardStep - 1);
}

function updateWizardUI() {
    // Update step content visibility
    for (let i = 1; i <= WIZARD_TOTAL_STEPS; i++) {
        const stepEl = document.getElementById(`wizard-step-${i}`);
        if (stepEl) {
            stepEl.classList.toggle('hidden', i !== currentWizardStep);
        }
    }

    // Update step indicators
    document.querySelectorAll('.wizard-step-indicator').forEach(el => {
        const step = parseInt(el.dataset.step);
        if (step <= currentWizardStep) {
            el.classList.add('bg-primary');
            el.classList.remove('bg-gray-700');
        } else {
            el.classList.remove('bg-primary');
            el.classList.add('bg-gray-700');
        }
    });

    // Update step labels
    document.querySelectorAll('.wizard-step-label').forEach(el => {
        const step = parseInt(el.dataset.step);
        if (step === currentWizardStep) {
            el.classList.add('text-primary');
            el.classList.remove('text-gray-500');
        } else if (step < currentWizardStep) {
            el.classList.add('text-gray-400');
            el.classList.remove('text-gray-500', 'text-primary');
        } else {
            el.classList.add('text-gray-500');
            el.classList.remove('text-primary', 'text-gray-400');
        }
    });

    // Update step counter
    const stepCounter = document.getElementById('wizard-current-step');
    if (stepCounter) stepCounter.textContent = currentWizardStep;

    // Update navigation buttons
    const backBtn = document.getElementById('wizard-back-btn');
    const nextBtn = document.getElementById('wizard-next-btn');
    const startBtn = document.getElementById('wizard-start-btn');

    if (backBtn) backBtn.classList.toggle('hidden', currentWizardStep === 1);
    if (nextBtn) nextBtn.classList.toggle('hidden', currentWizardStep === WIZARD_TOTAL_STEPS);
    if (startBtn) startBtn.classList.toggle('hidden', currentWizardStep !== WIZARD_TOTAL_STEPS);

    // Update summary on last step
    if (currentWizardStep === WIZARD_TOTAL_STEPS) {
        updateWizardSummary();
    }
}

async function loadWizardStepData(step) {
    switch (step) {
        case 2: // Proxies
            await loadWizardProxyStats();
            break;
        case 3: // User Agents
            await loadWizardUAStats();
            break;
        case 4: // Fingerprints
            await loadWizardFPStats();
            break;
        case 5: // Behavior
            await loadWizardBehaviorStats();
            break;
        case 6: // Execution
            await loadWizardExecutionStats();
            break;
    }
}

async function loadWizardProxyStats() {
    try {
        const response = await fetch('/api/proxies/stats');
        if (response.ok) {
            const data = await response.json();
            wizardDataStats.proxies = data;

            const total = document.getElementById('wizard-proxy-total');
            const alive = document.getElementById('wizard-proxy-alive');
            const dead = document.getElementById('wizard-proxy-dead');
            const untested = document.getElementById('wizard-proxy-untested');

            if (total) total.textContent = (data.total || 0).toLocaleString();
            if (alive) alive.textContent = (data.alive || 0).toLocaleString();
            if (dead) dead.textContent = (data.dead || 0).toLocaleString();
            if (untested) untested.textContent = (data.untested || 0).toLocaleString();
        }
    } catch (error) {
        console.log('Proxy stats not available');
    }
}

async function loadWizardUAStats() {
    try {
        const response = await fetch('/api/data/user_agents');
        if (response.ok) {
            const data = await response.json();
            wizardDataStats.user_agents.files = data.files || [];
            wizardDataStats.user_agents.total = data.files?.reduce((sum, f) => sum + f.count, 0) || 0;

            const total = document.getElementById('wizard-ua-total');
            if (total) total.textContent = wizardDataStats.user_agents.total.toLocaleString();

            // Populate source dropdown
            const select = document.getElementById('wizard-ua-source');
            if (select && data.files?.length > 0) {
                select.innerHTML = data.files.map(f =>
                    `<option value="${f.name}">${f.name} (${f.count.toLocaleString()})</option>`
                ).join('');

                // Select platform-specific file if recommendation exists
                if (uaRecommendation?.recommended_file) {
                    const option = Array.from(select.options).find(o => o.value === uaRecommendation.recommended_file);
                    if (option) select.value = option.value;
                }
            } else if (select) {
                select.innerHTML = '<option value="">No files found</option>';
            }
        }

        // Load platform-specific recommendation
        if (currentPlatform) {
            await loadUARecommendation(currentPlatform);
        }
    } catch (error) {
        console.log('UA stats not available');
    }
}

async function loadWizardFPStats() {
    try {
        // Load fingerprints
        const fpResponse = await fetch('/api/data/fingerprints');
        if (fpResponse.ok) {
            const data = await fpResponse.json();
            wizardDataStats.fingerprints.files = data.files || [];
            wizardDataStats.fingerprints.total = data.files?.reduce((sum, f) => sum + f.count, 0) || 0;

            const total = document.getElementById('wizard-fp-total');
            if (total) total.textContent = wizardDataStats.fingerprints.total.toLocaleString();

            const select = document.getElementById('wizard-fp-source');
            if (select && data.files?.length > 0) {
                select.innerHTML = data.files.map(f =>
                    `<option value="${f.name}">${f.name} (${f.count.toLocaleString()})</option>`
                ).join('');
            } else if (select) {
                select.innerHTML = '<option value="">No files found</option>';
            }
        }

        // Load screen sizes
        const screenResponse = await fetch('/api/data/screen_sizes');
        if (screenResponse.ok) {
            const data = await screenResponse.json();
            wizardDataStats.screen_sizes.total = data.files?.reduce((sum, f) => sum + f.count, 0) || 0;

            const total = document.getElementById('wizard-screen-total');
            if (total) total.textContent = wizardDataStats.screen_sizes.total.toLocaleString();
        }
    } catch (error) {
        console.log('FP stats not available');
    }
}

async function loadWizardBehaviorStats() {
    try {
        const response = await fetch('/api/data/behavior');
        if (response.ok) {
            const data = await response.json();
            wizardDataStats.behavior.total = data.files?.reduce((sum, f) => sum + f.count, 0) || 0;

            const total = document.getElementById('wizard-behavior-total');
            if (total) total.textContent = wizardDataStats.behavior.total.toLocaleString();
        }
    } catch (error) {
        console.log('Behavior stats not available');
    }
}

async function loadWizardExecutionStats() {
    // Generate dynamic summary when entering Step 6
    generateConfigSummary();
    generateResourceEstimate();
}

function updateWizardSummary() {
    // Delegate to new summary functions
    generateConfigSummary();
    generateResourceEstimate();
}

// ============ STEP 6: DYNAMIC SUMMARY ============
function generateConfigSummary() {
    const summary = document.getElementById('config-summary');
    if (!summary) return;

    const config = collectWizardConfig();

    summary.innerHTML = `
        <!-- Step 1: Target -->
        <div class="flex items-start gap-3 p-2 bg-surface-light/50 rounded-lg hover:bg-surface-light transition-colors">
            <span class="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">1</span>
            <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-500 uppercase tracking-wide">Target</div>
                <div class="text-sm text-white truncate">${config.url || 'Not set'}</div>
                <div class="text-xs text-gray-500">Platform: <span class="text-blue-400">${formatPlatformName(config.platform)}</span></div>
            </div>
            <button onclick="goToWizardStep(1)" class="text-xs text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded hover:bg-cyan-500/10 flex-shrink-0">Edit</button>
        </div>

        <!-- Step 2: Proxies -->
        <div class="flex items-start gap-3 p-2 bg-surface-light/50 rounded-lg hover:bg-surface-light transition-colors">
            <span class="w-5 h-5 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">2</span>
            <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-500 uppercase tracking-wide">Proxies</div>
                <div class="text-sm text-white">${formatProxyConfig(config)}</div>
                ${config.use_proxies ? `<div class="text-xs text-gray-500">${formatProxyDetails(config)}</div>` : ''}
            </div>
            <button onclick="goToWizardStep(2)" class="text-xs text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded hover:bg-cyan-500/10 flex-shrink-0">Edit</button>
        </div>

        <!-- Step 3: User Agents -->
        <div class="flex items-start gap-3 p-2 bg-surface-light/50 rounded-lg hover:bg-surface-light transition-colors">
            <span class="w-5 h-5 rounded-full bg-orange-500/20 text-orange-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">3</span>
            <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-500 uppercase tracking-wide">User Agents</div>
                <div class="text-sm text-white">${formatUAConfig(config)}</div>
                ${config.use_user_agents ? `<div class="text-xs text-gray-500">${formatUADetails(config)}</div>` : ''}
            </div>
            <button onclick="goToWizardStep(3)" class="text-xs text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded hover:bg-cyan-500/10 flex-shrink-0">Edit</button>
        </div>

        <!-- Step 4: Fingerprints -->
        <div class="flex items-start gap-3 p-2 bg-surface-light/50 rounded-lg hover:bg-surface-light transition-colors">
            <span class="w-5 h-5 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">4</span>
            <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-500 uppercase tracking-wide">Fingerprints</div>
                <div class="text-sm text-white">${formatFPConfig(config)}</div>
                ${config.use_fingerprints ? `<div class="text-xs text-gray-500">${formatFPDetails(config)}</div>` : ''}
            </div>
            <button onclick="goToWizardStep(4)" class="text-xs text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded hover:bg-cyan-500/10 flex-shrink-0">Edit</button>
        </div>

        <!-- Step 5: Behavior -->
        <div class="flex items-start gap-3 p-2 bg-surface-light/50 rounded-lg hover:bg-surface-light transition-colors">
            <span class="w-5 h-5 rounded-full bg-yellow-500/20 text-yellow-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">5</span>
            <div class="flex-1 min-w-0">
                <div class="text-xs text-gray-500 uppercase tracking-wide">Behavior</div>
                <div class="text-sm text-white">${formatBehaviorConfig(config)}</div>
                <div class="text-xs text-gray-500">${formatBehaviorDetails(config)}</div>
            </div>
            <button onclick="goToWizardStep(5)" class="text-xs text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded hover:bg-cyan-500/10 flex-shrink-0">Edit</button>
        </div>
    `;
}

// Format helpers for config summary
function formatPlatformName(platform) {
    const names = {
        'tiktok': 'TikTok',
        'instagram': 'Instagram',
        'youtube': 'YouTube',
        'dextools': 'DEXTools',
        'generic': 'Generic Website'
    };
    return names[platform] || platform;
}

function formatProxyConfig(config) {
    if (!config.use_proxies || config.proxy_provider === 'none') return '<span class="text-gray-500">Disabled</span>';

    const providers = {
        'decodo': 'Decodo (Residential)',
        'brightdata': 'Bright Data',
        'oxylabs': 'Oxylabs',
        'tor': 'Tor Network',
        'file': 'File-based'
    };
    return providers[config.proxy_provider] || config.proxy_provider;
}

function formatProxyDetails(config) {
    const parts = [];
    if (config.proxy_country) parts.push(`Country: ${config.proxy_country.toUpperCase()}`);
    if (config.proxy_rotation) parts.push(`Rotation: ${config.proxy_rotation.replace('_', ' ')}`);
    if (config.proxy_provider === 'tor') parts.push(`Port: ${config.tor_port}`);
    if (config.proxy_provider === 'file' && wizardDataStats.proxies.alive > 0) {
        parts.push(`${wizardDataStats.proxies.alive.toLocaleString()} alive`);
    }
    return parts.join(' | ') || 'Default settings';
}

function formatUAConfig(config) {
    if (!config.use_user_agents || config.user_agent_mode === 'none') return '<span class="text-gray-500">Disabled</span>';

    if (config.user_agent_mode === 'dynamic') {
        return `<span class="text-orange-400">Dynamic</span> (browserforge)`;
    }
    return `<span class="text-orange-400">File-based</span>`;
}

function formatUADetails(config) {
    const parts = [];
    if (config.user_agent_mode === 'dynamic') {
        parts.push(`Browser: ${config.user_agent_browser}`);
        parts.push(`OS: ${config.user_agent_os}`);
        parts.push(`Pool: ${config.user_agent_pool_size.toLocaleString()}`);
        if (config.user_agent_include_mobile) parts.push('+Mobile');
    } else {
        parts.push(`Source: ${config.user_agent_source || 'default'}`);
        parts.push(`Total: ${wizardDataStats.user_agents.total.toLocaleString()}`);
    }
    return parts.join(' | ');
}

function formatFPConfig(config) {
    if (!config.use_fingerprints || config.fingerprint_mode === 'none') return '<span class="text-gray-500">Disabled</span>';

    if (config.fingerprint_mode === 'dynamic') {
        return `<span class="text-purple-400">Dynamic</span> (browserforge)`;
    }
    return `<span class="text-purple-400">File-based</span>`;
}

function formatFPDetails(config) {
    const parts = [];
    if (config.fingerprint_mode === 'dynamic') {
        const components = Object.entries(config.fingerprint_components || {})
            .filter(([k, v]) => v)
            .map(([k]) => k.charAt(0).toUpperCase() + k.slice(1));
        parts.push(`Components: ${components.slice(0, 4).join(', ')}${components.length > 4 ? '...' : ''}`);
        parts.push(`Pool: ${config.fingerprint_pool_size.toLocaleString()}`);
    } else {
        parts.push(`Source: ${config.fingerprint_source || 'default'}`);
    }
    return parts.join(' | ');
}

function formatBehaviorConfig(config) {
    const b = config.behavior;
    if (!b) return '<span class="text-gray-500">Default</span>';

    const modeLabels = {
        'preset': '<span class="text-green-400">Preset</span> (Pattern-based)',
        'llm': '<span class="text-violet-400">LLM</span> (AI-driven)',
        'hybrid': '<span class="text-cyan-400">Hybrid</span> (Preset + AI fallback)'
    };
    return modeLabels[b.mode] || b.mode;
}

function formatBehaviorDetails(config) {
    const b = config.behavior;
    if (!b) return '';

    const parts = [];

    // Traffic source
    const referrerLabels = {
        'realistic': 'Realistic mix',
        'search_heavy': 'Search-heavy',
        'social_viral': 'Social viral',
        'brand_focused': 'Brand focused',
        'custom': 'Custom weights',
        'none': 'None'
    };
    parts.push(`Traffic: ${referrerLabels[b.referrer?.mode] || b.referrer?.preset || 'realistic'}`);

    // Mouse style
    parts.push(`Mouse: ${b.interaction?.mouse_style || 'natural'}`);

    // Engagement
    const engageLabels = { 'passive': '5-15s', 'active': '15-60s', 'deep': '60-300s' };
    parts.push(`Dwell: ${engageLabels[b.session?.engagement_level] || '15-60s'}`);

    // LLM if enabled
    if (b.llm && (b.mode === 'llm' || b.mode === 'hybrid')) {
        parts.push(`<span class="text-violet-400">LLM: ${b.llm.provider}/${b.llm.model}</span>`);
    }

    return parts.join(' | ');
}

function generateResourceEstimate() {
    const estimate = document.getElementById('resource-estimate');
    if (!estimate) return;

    const config = collectWizardConfig();
    const workers = config.workers || 1;
    const repeat = config.repeat || 1;
    const totalSessions = workers * repeat;

    // Proxy estimate
    let proxyEstimate = 'N/A';
    let proxyColor = 'text-gray-400';
    if (config.use_proxies && config.proxy_provider !== 'none') {
        proxyColor = 'text-green-400';
        if (config.proxy_rotation === 'per_request') {
            proxyEstimate = `~${totalSessions * 3}-${totalSessions * 8}`;
        } else if (config.proxy_rotation === 'per_page') {
            proxyEstimate = `~${totalSessions * 2}-${totalSessions * 5}`;
        } else {
            proxyEstimate = `~${totalSessions}`;
        }
    }

    // Time estimate (rough)
    const avgSessionTime = config.behavior?.session?.dwell_time_max_sec || 60;
    const minSessionTime = config.behavior?.session?.dwell_time_min_sec || 15;
    const avgTime = (avgSessionTime + minSessionTime) / 2;
    const totalMinutes = Math.ceil((totalSessions * avgTime) / workers / 60);
    const timeEstimate = totalMinutes < 1 ? '<1min' : `~${totalMinutes}min`;

    // LLM cost estimate
    let llmEstimate = 'N/A';
    let llmColor = 'text-gray-400';
    if (config.behavior?.llm && (config.behavior.mode === 'llm' || config.behavior.mode === 'hybrid')) {
        llmColor = 'text-purple-400';
        const provider = config.behavior.llm.provider;
        const freq = config.behavior.llm.decision_frequency;

        if (provider === 'ollama') {
            llmEstimate = 'Local';
        } else {
            // Estimate calls per session
            const callsPerSession = freq === 'every' ? 15 : freq === 'key' ? 5 : 2;
            // Cost per call (rough estimate)
            const costPerCall = provider === 'anthropic' ? 0.015 : 0.01;
            const totalCost = totalSessions * callsPerSession * costPerCall;
            llmEstimate = totalCost < 0.01 ? '<$0.01' : `~$${totalCost.toFixed(2)}`;
        }
    }

    estimate.innerHTML = `
        <div class="text-center p-3 bg-surface-light/50 rounded-lg">
            <div class="text-2xl font-bold text-cyan-400">${totalSessions.toLocaleString()}</div>
            <div class="text-xs text-gray-500">Total Sessions</div>
        </div>
        <div class="text-center p-3 bg-surface-light/50 rounded-lg">
            <div class="text-2xl font-bold ${proxyColor}">${proxyEstimate}</div>
            <div class="text-xs text-gray-500">Proxy Requests</div>
        </div>
        <div class="text-center p-3 bg-surface-light/50 rounded-lg">
            <div class="text-2xl font-bold text-purple-400">${timeEstimate}</div>
            <div class="text-xs text-gray-500">Est. Runtime</div>
        </div>
        ${config.behavior?.llm ? `
        <div class="col-span-3 text-center p-2 bg-violet-500/10 border border-violet-500/30 rounded-lg">
            <span class="text-xs text-violet-400">LLM Cost: ${llmEstimate}</span>
            ${config.behavior.llm.provider !== 'ollama' ? '<span class="text-xs text-gray-500 ml-2">(estimated)</span>' : ''}
        </div>
        ` : ''}
    `;
}

// ============ USER AGENT FUNCTIONS ============
let currentUAMode = 'dynamic';
let uaRecommendation = null;

function setUAMode(mode) {
    currentUAMode = mode;

    // Update UI
    document.querySelectorAll('.ua-mode-option').forEach(el => {
        el.classList.remove('border-primary');
        el.classList.add('border-gray-700');
    });
    const selected = document.querySelector(`input[name="ua_mode"][value="${mode}"]`);
    if (selected) {
        selected.closest('.ua-mode-option')?.classList.remove('border-gray-700');
        selected.closest('.ua-mode-option')?.classList.add('border-primary');
    }

    // Show/hide options
    const dynamicOptions = document.getElementById('ua-dynamic-options');
    const fileOptions = document.getElementById('ua-file-options');

    dynamicOptions?.classList.add('hidden');
    fileOptions?.classList.add('hidden');

    if (mode === 'dynamic') {
        dynamicOptions?.classList.remove('hidden');
    } else if (mode === 'file') {
        fileOptions?.classList.remove('hidden');
    }

    hideUAPreview();
}

async function loadUARecommendation(platform) {
    try {
        const response = await fetch(`/api/data/user_agents/recommendation/${platform}`);
        const data = await response.json();

        uaRecommendation = data;

        const banner = document.getElementById('ua-recommendation-banner');
        const text = document.getElementById('ua-recommendation-text');
        const platformEl = document.getElementById('ua-recommendation-platform');

        if (banner && text) {
            text.textContent = data.message;
            if (platformEl) platformEl.textContent = platform.charAt(0).toUpperCase() + platform.slice(1);
            banner.classList.remove('hidden');
        }

        // Auto-apply settings based on recommendation
        if (data.settings) {
            if (data.settings.browser) {
                const browserSelect = document.getElementById('ua-dynamic-browser');
                if (browserSelect) browserSelect.value = data.settings.browser;
            }
            if (data.settings.os) {
                const osSelect = document.getElementById('ua-dynamic-os');
                if (osSelect) osSelect.value = data.settings.os;
            }
            if (data.settings.include_mobile !== undefined) {
                const mobileCheck = document.getElementById('ua-include-mobile');
                if (mobileCheck) mobileCheck.checked = data.settings.include_mobile;
            }
            if (data.settings.include_webview !== undefined) {
                const webviewCheck = document.getElementById('ua-include-webview');
                if (webviewCheck) webviewCheck.checked = data.settings.include_webview;
            }
        }
    } catch (error) {
        console.error('Failed to load UA recommendation:', error);
    }
}

function applyUARecommendation() {
    if (!uaRecommendation) return;

    setUAMode(uaRecommendation.recommended_mode);

    if (uaRecommendation.recommended_mode === 'file') {
        const sourceSelect = document.getElementById('wizard-ua-source');
        if (sourceSelect) {
            sourceSelect.value = uaRecommendation.recommended_file;
            updateUAFileInfo();
        }
    }

    // Hide banner after applying
    document.getElementById('ua-recommendation-banner')?.classList.add('hidden');
    addEvent('info', `Applied UA settings for ${uaRecommendation.platform}`);
}

async function previewDynamicUA() {
    const browser = document.getElementById('ua-dynamic-browser')?.value || 'chrome';
    const os = document.getElementById('ua-dynamic-os')?.value || 'windows';

    try {
        const response = await fetch('/api/data/user_agents/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ browser, os, count: 1 })
        });
        const data = await response.json();

        if (data.success && data.user_agents?.length > 0) {
            const ua = data.user_agents[0];
            showUAPreview(ua.user_agent, browser, os, 'Desktop');
        } else {
            addEvent('error', data.error || 'Failed to generate UA');
        }
    } catch (error) {
        addEvent('error', 'Failed to generate UA: ' + error.message);
    }
}

let generatedUAPool = [];

async function generateUAPool() {
    const browser = document.getElementById('ua-dynamic-browser')?.value || 'chrome';
    const os = document.getElementById('ua-dynamic-os')?.value || 'windows';
    const poolSize = parseInt(document.getElementById('ua-dynamic-pool-size')?.value) || 1000;

    const statusEl = document.getElementById('ua-pool-status');
    if (statusEl) {
        statusEl.textContent = 'Generating...';
        statusEl.className = 'text-xs text-yellow-400';
    }

    try {
        // Generate in batches (API supports up to 500 per request)
        const batchSize = 500;
        const batches = Math.ceil(poolSize / batchSize);
        generatedUAPool = [];

        for (let i = 0; i < batches; i++) {
            const count = Math.min(batchSize, poolSize - (i * batchSize));
            const response = await fetch('/api/data/user_agents/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ browser, os, count })
            });
            const data = await response.json();

            if (data.success && data.user_agents) {
                generatedUAPool.push(...data.user_agents.map(u => u.user_agent));
            }

            if (statusEl) {
                const progress = Math.min(100, Math.round(((i + 1) * batchSize / poolSize) * 100));
                statusEl.textContent = `Generating... ${progress}%`;
            }
        }

        if (statusEl) {
            statusEl.textContent = `Pool ready: ${generatedUAPool.length.toLocaleString()} UAs`;
            statusEl.className = 'text-xs text-green-400';
        }

        addEvent('success', `Generated ${generatedUAPool.length.toLocaleString()} user agents`);
    } catch (error) {
        if (statusEl) {
            statusEl.textContent = 'Generation failed';
            statusEl.className = 'text-xs text-red-400';
        }
        addEvent('error', 'Failed to generate pool: ' + error.message);
    }
}

async function previewFileUA() {
    const filename = document.getElementById('wizard-ua-source')?.value;
    if (!filename) {
        addEvent('warning', 'Please select a file first');
        return;
    }

    try {
        const response = await fetch(`/api/data/user_agents/sample/${filename}`);
        const data = await response.json();

        if (data.success) {
            showUAPreview(data.user_agent, data.browser, data.os, data.device);
        } else {
            addEvent('error', data.error || 'Failed to get sample');
        }
    } catch (error) {
        addEvent('error', 'Failed to get sample: ' + error.message);
    }
}

function showUAPreview(ua, browser, os, device) {
    const panel = document.getElementById('ua-preview-panel');
    const text = document.getElementById('ua-preview-text');
    const browserEl = document.getElementById('ua-preview-browser');
    const osEl = document.getElementById('ua-preview-os');
    const deviceEl = document.getElementById('ua-preview-device');

    if (panel && text) {
        text.textContent = ua;
        if (browserEl) browserEl.textContent = browser;
        if (osEl) osEl.textContent = os;
        if (deviceEl) deviceEl.textContent = device;
        panel.classList.remove('hidden');
    }
}

function hideUAPreview() {
    document.getElementById('ua-preview-panel')?.classList.add('hidden');
}

async function updateUAFileInfo() {
    const filename = document.getElementById('wizard-ua-source')?.value;
    if (!filename) return;

    try {
        const response = await fetch(`/api/data/user_agents/sample/${filename}`);
        const data = await response.json();

        if (data.success) {
            const totalEl = document.getElementById('wizard-ua-total');
            if (totalEl) totalEl.textContent = data.total_in_file.toLocaleString();
        }
    } catch (error) {
        console.error('Failed to update UA file info:', error);
    }
}

// Load UA sources when step 3 is entered
async function loadUASources() {
    try {
        const response = await fetch('/api/data/user_agents');
        const data = await response.json();

        const select = document.getElementById('wizard-ua-source');
        if (!select) return;

        select.innerHTML = '';

        if (data.files && data.files.length > 0) {
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file.name;
                option.textContent = `${file.name} (${file.count.toLocaleString()})`;
                select.appendChild(option);
            });

            // Set default based on recommendation
            if (uaRecommendation?.recommended_file) {
                select.value = uaRecommendation.recommended_file;
            }

            updateUAFileInfo();
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No UA files found';
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Failed to load UA sources:', error);
    }
}

// ============ FINGERPRINT FUNCTIONS ============
let currentFPMode = 'dynamic';
let generatedFPPool = [];

function setFPMode(mode) {
    currentFPMode = mode;

    // Update UI
    document.querySelectorAll('.fp-mode-option').forEach(el => {
        el.classList.remove('border-primary');
        el.classList.add('border-gray-700');
    });
    const selected = document.querySelector(`input[name="fp_mode"][value="${mode}"]`);
    if (selected) {
        selected.closest('.fp-mode-option')?.classList.remove('border-gray-700');
        selected.closest('.fp-mode-option')?.classList.add('border-primary');
    }

    // Show/hide options
    const dynamicOptions = document.getElementById('fp-dynamic-options');
    const fileOptions = document.getElementById('fp-file-options');

    dynamicOptions?.classList.add('hidden');
    fileOptions?.classList.add('hidden');

    if (mode === 'dynamic') {
        dynamicOptions?.classList.remove('hidden');
    } else if (mode === 'file') {
        fileOptions?.classList.remove('hidden');
    }

    hideFPPreview();
}

async function previewDynamicFP() {
    const browser = document.getElementById('fp-dynamic-browser')?.value || 'chrome';
    const os = document.getElementById('fp-dynamic-os')?.value || 'windows';

    try {
        const response = await fetch('/api/data/fingerprints/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ browser, os, count: 1 })
        });
        const data = await response.json();

        if (data.success && data.fingerprints?.length > 0) {
            const fp = data.fingerprints[0];
            showFPPreview(fp);
        } else {
            addEvent('error', data.error || 'Failed to generate fingerprint');
        }
    } catch (error) {
        addEvent('error', 'Failed to generate fingerprint: ' + error.message);
    }
}

async function previewFileFP() {
    try {
        const response = await fetch('/api/data/fingerprints/sample');
        const data = await response.json();

        if (data.success && data.fingerprint) {
            // Convert file format to display format
            const fp = data.fingerprint;
            showFPPreviewFromFile(fp);
        } else {
            addEvent('error', data.error || 'Failed to get sample');
        }
    } catch (error) {
        addEvent('error', 'Failed to get sample: ' + error.message);
    }
}

function showFPPreview(fp) {
    const panel = document.getElementById('fp-preview-panel');
    if (!panel) return;

    document.getElementById('fp-preview-screen').textContent = `${fp.screen?.width}x${fp.screen?.height}`;
    document.getElementById('fp-preview-platform').textContent = fp.navigator?.platform || '-';
    document.getElementById('fp-preview-gpu').textContent = fp.videoCard?.renderer?.substring(0, 30) || '-';
    document.getElementById('fp-preview-memory').textContent = `${fp.navigator?.deviceMemory || '-'} GB`;
    document.getElementById('fp-preview-cores').textContent = fp.navigator?.hardwareConcurrency || '-';
    document.getElementById('fp-preview-language').textContent = fp.navigator?.language || '-';

    panel.classList.remove('hidden');
}

function showFPPreviewFromFile(fp) {
    const panel = document.getElementById('fp-preview-panel');
    if (!panel) return;

    // File format has different structure
    const nav = fp.Navigator || {};
    const emu = fp.Emulation || {};

    document.getElementById('fp-preview-screen').textContent = emu.Screen_size || '-';
    document.getElementById('fp-preview-platform').textContent = nav.Platform || '-';
    document.getElementById('fp-preview-gpu').textContent = '-';
    document.getElementById('fp-preview-memory').textContent = `${nav.Device_memory || '-'} GB`;
    document.getElementById('fp-preview-cores').textContent = nav.Cpu_cores || '-';
    document.getElementById('fp-preview-language').textContent = nav.Browser_language || '-';

    panel.classList.remove('hidden');
}

function hideFPPreview() {
    document.getElementById('fp-preview-panel')?.classList.add('hidden');
}

async function generateFPPool() {
    const browser = document.getElementById('fp-dynamic-browser')?.value || 'chrome';
    const os = document.getElementById('fp-dynamic-os')?.value || 'windows';
    const poolSize = parseInt(document.getElementById('fp-dynamic-pool-size')?.value) || 1000;

    const statusEl = document.getElementById('fp-pool-status');
    if (statusEl) {
        statusEl.textContent = 'Generating...';
        statusEl.className = 'text-xs text-yellow-400';
    }

    try {
        // Generate in batches (API supports up to 100 per request for FPs)
        const batchSize = 100;
        const batches = Math.ceil(poolSize / batchSize);
        generatedFPPool = [];

        for (let i = 0; i < batches; i++) {
            const count = Math.min(batchSize, poolSize - (i * batchSize));
            const response = await fetch('/api/data/fingerprints/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ browser, os, count })
            });
            const data = await response.json();

            if (data.success && data.fingerprints) {
                generatedFPPool.push(...data.fingerprints);
            }

            if (statusEl) {
                const progress = Math.min(100, Math.round(((i + 1) * batchSize / poolSize) * 100));
                statusEl.textContent = `Generating... ${progress}%`;
            }
        }

        if (statusEl) {
            statusEl.textContent = `Pool ready: ${generatedFPPool.length.toLocaleString()} FPs`;
            statusEl.className = 'text-xs text-cyan-400';
        }

        addEvent('success', `Generated ${generatedFPPool.length.toLocaleString()} fingerprints`);
    } catch (error) {
        if (statusEl) {
            statusEl.textContent = 'Generation failed';
            statusEl.className = 'text-xs text-red-400';
        }
        addEvent('error', 'Failed to generate pool: ' + error.message);
    }
}

function collectWizardConfig() {
    return {
        // Target
        url: document.getElementById('url-input')?.value.trim(),
        platform: currentPlatform,

        // Proxies
        use_proxies: selectedProxyProvider !== 'none',
        proxy_provider: selectedProxyProvider,
        proxy_rotation: document.getElementById('wizard-proxy-rotation')?.value || 'per_request',
        proxy_country: document.getElementById('wizard-proxy-country')?.value || null,
        proxy_session_type: document.getElementById('wizard-proxy-session')?.value || 'rotating',
        // Tor settings
        tor_port: parseInt(document.getElementById('wizard-tor-port')?.value || 9050),
        tor_rotation: document.getElementById('wizard-tor-rotation')?.value || 'per_session',

        // User Agents
        use_user_agents: currentUAMode !== 'none',
        user_agent_mode: currentUAMode,
        user_agent_source: document.getElementById('wizard-ua-source')?.value || '',
        user_agent_browser: document.getElementById('ua-dynamic-browser')?.value || 'chrome',
        user_agent_os: document.getElementById('ua-dynamic-os')?.value || 'windows',
        user_agent_pool_size: parseInt(document.getElementById('ua-dynamic-pool-size')?.value) || 1000,
        user_agent_pool: generatedUAPool.length > 0 ? generatedUAPool : null,
        user_agent_include_mobile: document.getElementById('ua-include-mobile')?.checked ?? false,
        user_agent_include_webview: document.getElementById('ua-include-webview')?.checked ?? false,
        user_agent_modern_only: document.getElementById('ua-modern-only')?.checked ?? true,
        user_agent_match_fingerprint: document.getElementById('ua-match-fingerprint')?.checked ?? true,

        // Fingerprints
        use_fingerprints: currentFPMode !== 'none',
        fingerprint_mode: currentFPMode,
        fingerprint_source: document.getElementById('wizard-fp-source')?.value || '',
        fingerprint_browser: document.getElementById('fp-dynamic-browser')?.value || 'chrome',
        fingerprint_os: document.getElementById('fp-dynamic-os')?.value || 'windows',
        fingerprint_pool_size: parseInt(document.getElementById('fp-dynamic-pool-size')?.value) || 1000,
        fingerprint_pool: generatedFPPool.length > 0 ? generatedFPPool : null,
        fingerprint_components: {
            screen: document.getElementById('fp-comp-screen')?.checked ?? true,
            webgl: document.getElementById('fp-comp-webgl')?.checked ?? true,
            audio: document.getElementById('fp-comp-audio')?.checked ?? true,
            fonts: document.getElementById('fp-comp-fonts')?.checked ?? true,
            canvas: document.getElementById('fp-comp-canvas')?.checked ?? true,
            timezone: document.getElementById('fp-comp-timezone')?.checked ?? true,
            language: document.getElementById('fp-comp-language')?.checked ?? true,
            hardware: document.getElementById('fp-comp-hardware')?.checked ?? true,
        },
        use_screen_sizes: document.getElementById('wizard-use-screen-sizes')?.checked ?? true,
        screen_types: Array.from(document.querySelectorAll('input[name="screen_type"]:checked')).map(el => el.value),

        // Behavior (Enhanced Step 5)
        behavior: {
            mode: currentBehaviorMode,
            preset_name: currentBehaviorMode === 'preset' ? 'natural' : null,

            // Referrer Distribution
            referrer: {
                mode: currentReferrerMode,
                preset: document.getElementById('referrer-preset')?.value || 'realistic',
                direct_weight: parseInt(document.getElementById('ref-direct')?.value || 45),
                google_weight: parseInt(document.getElementById('ref-google')?.value || 25),
                social_weight: parseInt(document.getElementById('ref-social')?.value || 12),
                referral_weight: parseInt(document.getElementById('ref-referral')?.value || 8),
                email_weight: parseInt(document.getElementById('ref-email')?.value || 5),
                ai_search_weight: parseInt(document.getElementById('ref-ai')?.value || 2),
                variance_percent: parseInt(document.getElementById('ref-variance')?.value || 10),
            },

            // Interaction Patterns
            interaction: {
                mouse_style: currentMouseStyle,
                scroll_behavior: document.getElementById('scroll-behavior')?.value || 'smooth',
                tremor_amplitude: parseInt(document.getElementById('mouse-tremor')?.value || 15) / 10,
                overshoot_probability: parseInt(document.getElementById('mouse-overshoot')?.value || 15) / 100,
                speed_multiplier: parseInt(document.getElementById('mouse-speed')?.value || 100) / 100,
            },

            // Session Behavior
            session: {
                engagement_level: currentEngagementLevel,
                dwell_time_min_sec: parseInt(document.getElementById('dwell-min')?.value || 15),
                dwell_time_max_sec: parseInt(document.getElementById('dwell-max')?.value || 60),
                page_depth_min: parseInt(document.getElementById('depth-min')?.value || 1),
                page_depth_max: parseInt(document.getElementById('depth-max')?.value || 5),
                micro_breaks_enabled: document.getElementById('micro-breaks')?.checked ?? true,
            },

            // LLM Settings (when mode is llm or hybrid)
            llm: (currentBehaviorMode === 'llm' || currentBehaviorMode === 'hybrid') ? {
                provider: currentLLMBehaviorProvider,
                model: document.getElementById('llm-model')?.value || 'gpt-4o',
                personality: document.getElementById('llm-personality')?.value || 'casual',
                custom_prompt: document.getElementById('llm-custom-prompt')?.value || null,
                decision_frequency: document.getElementById('llm-frequency')?.value || 'key',
                vision_enabled: document.getElementById('llm-vision')?.checked || false,
                temperature: parseInt(document.getElementById('llm-temperature')?.value || 3) / 10,
            } : null,
        },

        // Execution
        mode: currentMode,
        workers: currentMode === 'batch' ? parseInt(document.getElementById('workers')?.value || 5) : 1,
        repeat: parseInt(document.getElementById('repeat')?.value || 1),
        headless: document.getElementById('headless')?.checked ?? true,
        browser_engine: document.getElementById('browser-engine')?.value || 'patchright',
    };
}

// ============ MODE TOGGLE ============
function setMode(mode) {
    currentMode = mode;
    const batchBtn = document.getElementById('mode-batch');
    const debugBtn = document.getElementById('mode-debug');
    const workersControl = document.getElementById('workers-control');

    if (mode === 'batch') {
        batchBtn.classList.add('bg-primary', 'text-white');
        batchBtn.classList.remove('text-gray-400');
        debugBtn.classList.remove('bg-primary', 'text-white');
        debugBtn.classList.add('text-gray-400');
        workersControl.classList.remove('opacity-50', 'pointer-events-none');
    } else {
        debugBtn.classList.add('bg-primary', 'text-white');
        debugBtn.classList.remove('text-gray-400');
        batchBtn.classList.remove('bg-primary', 'text-white');
        batchBtn.classList.add('text-gray-400');
        workersControl.classList.add('opacity-50', 'pointer-events-none');
    }
    updateTotalSessions();
}

function updateTotalSessions() {
    const workers = currentMode === 'batch' ? parseInt(document.getElementById('workers')?.value || 1) : 1;
    const repeat = parseInt(document.getElementById('repeat')?.value || 1);
    const total = workers * repeat;

    // Update preview in Section A
    const preview = document.getElementById('total-sessions-preview');
    if (preview) preview.textContent = total.toLocaleString();

    // Also update resource estimate if on Step 6
    if (currentWizardStep === 6) {
        generateResourceEstimate();
    }
}

// Hook up input listeners for live updates
document.addEventListener('DOMContentLoaded', () => {
    // Delayed to ensure elements exist after page load
    setTimeout(() => {
        const workersInput = document.getElementById('workers');
        const repeatInput = document.getElementById('repeat');

        if (workersInput) workersInput.addEventListener('input', updateTotalSessions);
        if (repeatInput) repeatInput.addEventListener('input', updateTotalSessions);
    }, 1000);
});

// ============ SLIDERS ============
function updateSlider(type) {
    const slider = document.getElementById(`${type}-prob`);
    const display = document.getElementById(`${type}-value`);
    display.textContent = `${slider.value}%`;
}

// ============ BEHAVIOR CONTROLS (Step 5) ============

// Section A: Behavior Mode
function setBehaviorMode(mode) {
    currentBehaviorMode = mode;
    const options = document.querySelectorAll('.behavior-mode-option');

    options.forEach(opt => {
        const radio = opt.querySelector('input[type="radio"]');
        if (radio.value === mode) {
            opt.classList.remove('border-gray-600');
            if (mode === 'preset') {
                opt.classList.add('border-cyan-500', 'bg-cyan-500/10');
            } else if (mode === 'llm') {
                opt.classList.add('border-violet-500', 'bg-violet-500/10');
            } else {
                opt.classList.add('border-amber-500', 'bg-amber-500/10');
            }
            radio.checked = true;
        } else {
            opt.classList.remove('border-cyan-500', 'border-violet-500', 'border-amber-500');
            opt.classList.remove('bg-cyan-500/10', 'bg-violet-500/10', 'bg-amber-500/10');
            opt.classList.add('border-gray-600');
            radio.checked = false;
        }
    });

    // Show/hide LLM section
    const llmSection = document.getElementById('behavior-llm-section');
    if (mode === 'llm' || mode === 'hybrid') {
        llmSection?.classList.remove('hidden');
    } else {
        llmSection?.classList.add('hidden');
    }
}

// Section B: Referrer Distribution
function setReferrerMode(mode) {
    currentReferrerMode = mode;
    const modes = ['realistic', 'custom', 'none'];

    modes.forEach(m => {
        const btn = document.getElementById(`ref-mode-${m}`);
        if (m === mode) {
            btn.classList.remove('bg-surface-light', 'text-gray-400', 'border-gray-600');
            btn.classList.add('bg-green-500/20', 'text-green-400', 'border-green-500/30');
        } else {
            btn.classList.remove('bg-green-500/20', 'text-green-400', 'border-green-500/30');
            btn.classList.add('bg-surface-light', 'text-gray-400', 'border-gray-600');
        }
    });

    // Show/hide appropriate sections
    const realisticOpts = document.getElementById('referrer-realistic-options');
    const customWeights = document.getElementById('referrer-custom-weights');
    const varianceControl = document.getElementById('referrer-variance-control');

    if (mode === 'realistic') {
        realisticOpts?.classList.remove('hidden');
        customWeights?.classList.add('hidden');
        varianceControl?.classList.remove('hidden');
    } else if (mode === 'custom') {
        realisticOpts?.classList.add('hidden');
        customWeights?.classList.remove('hidden');
        varianceControl?.classList.remove('hidden');
    } else {
        realisticOpts?.classList.add('hidden');
        customWeights?.classList.add('hidden');
        varianceControl?.classList.add('hidden');
    }
}

function updateRefSlider(type) {
    const slider = document.getElementById(`ref-${type}`);
    const display = document.getElementById(`ref-${type}-val`);
    if (type === 'variance') {
        display.textContent = slider.value;
    } else {
        display.textContent = `${slider.value}%`;
    }
}

function updateReferrerPreset() {
    // Could fetch preset weights and update display
    const preset = document.getElementById('referrer-preset')?.value;
    console.log('Selected referrer preset:', preset);
}

// Section C: Interaction Patterns
function setMouseStyle(style) {
    currentMouseStyle = style;
    const styles = ['natural', 'fast', 'slow', 'nervous', 'confident', 'random'];

    styles.forEach(s => {
        const btn = document.getElementById(`mouse-${s}`);
        if (s === style) {
            btn.classList.remove('bg-surface-light', 'text-gray-400', 'border-gray-600');
            btn.classList.add('bg-cyan-500/20', 'text-cyan-400', 'border-cyan-500/30');
        } else {
            btn.classList.remove('bg-cyan-500/20', 'text-cyan-400', 'border-cyan-500/30');
            btn.classList.add('bg-surface-light', 'text-gray-400', 'border-gray-600');
        }
    });
}

function toggleAdvancedMouse() {
    const advanced = document.getElementById('advanced-mouse');
    const icon = document.getElementById('advanced-mouse-icon');

    if (advanced.classList.contains('hidden')) {
        advanced.classList.remove('hidden');
        icon.style.transform = 'rotate(90deg)';
    } else {
        advanced.classList.add('hidden');
        icon.style.transform = 'rotate(0deg)';
    }
}

function updateMouseSlider(type) {
    const slider = document.getElementById(`mouse-${type}`);
    const display = document.getElementById(`mouse-${type}-val`);

    if (type === 'tremor') {
        display.textContent = (slider.value / 10).toFixed(1);
    } else if (type === 'overshoot') {
        display.textContent = `${slider.value}%`;
    } else if (type === 'speed') {
        display.textContent = `${(slider.value / 100).toFixed(1)}x`;
    }
}

// Section D: Session Behavior
function setEngagement(level) {
    currentEngagementLevel = level;
    const levels = ['passive', 'active', 'deep'];

    // Update button styles
    levels.forEach(l => {
        const btn = document.getElementById(`engage-${l}`);
        const label = btn.querySelector('.text-sm');

        if (l === level) {
            btn.classList.remove('bg-surface-light', 'border-gray-600');
            btn.classList.add('bg-cyan-500/10', 'border-cyan-500/30');
            label.classList.remove('text-gray-300');
            label.classList.add('text-cyan-400');
        } else {
            btn.classList.remove('bg-cyan-500/10', 'border-cyan-500/30');
            btn.classList.add('bg-surface-light', 'border-gray-600');
            label.classList.remove('text-cyan-400');
            label.classList.add('text-gray-300');
        }
    });

    // Update dwell time based on engagement level
    const dwellMin = document.getElementById('dwell-min');
    const dwellMax = document.getElementById('dwell-max');
    const depthMin = document.getElementById('depth-min');
    const depthMax = document.getElementById('depth-max');

    const presets = {
        passive: { dwellMin: 5, dwellMax: 15, depthMin: 1, depthMax: 2 },
        active: { dwellMin: 15, dwellMax: 60, depthMin: 3, depthMax: 5 },
        deep: { dwellMin: 60, dwellMax: 300, depthMin: 5, depthMax: 15 }
    };

    const preset = presets[level];
    if (preset) {
        dwellMin.value = preset.dwellMin;
        dwellMax.value = preset.dwellMax;
        depthMin.value = preset.depthMin;
        depthMax.value = preset.depthMax;
    }
}

// Section E: LLM Settings
function setLLMProvider(provider) {
    currentLLMBehaviorProvider = provider;
    const providers = ['openai', 'anthropic', 'ollama'];

    providers.forEach(p => {
        const btn = document.getElementById(`llm-${p}`);
        if (p === provider) {
            btn.classList.remove('bg-surface-light', 'text-gray-400', 'border-gray-600');
            btn.classList.add('bg-green-500/20', 'text-green-400', 'border-green-500/30');
        } else {
            btn.classList.remove('bg-green-500/20', 'text-green-400', 'border-green-500/30');
            btn.classList.add('bg-surface-light', 'text-gray-400', 'border-gray-600');
        }
    });

    // Update model dropdown based on provider
    updateLLMModels(provider);
}

function updateLLMModels(provider) {
    const modelSelect = document.getElementById('llm-model');
    if (!modelSelect) return;

    const models = {
        openai: [
            { value: 'gpt-4o', text: 'GPT-4o (Recommended)' },
            { value: 'gpt-4o-mini', text: 'GPT-4o Mini (Faster)' },
            { value: 'gpt-4-turbo', text: 'GPT-4 Turbo' },
        ],
        anthropic: [
            { value: 'claude-sonnet-4-20250514', text: 'Claude Sonnet 4 (Recommended)' },
            { value: 'claude-3-5-sonnet-20241022', text: 'Claude 3.5 Sonnet' },
            { value: 'claude-3-haiku-20240307', text: 'Claude 3 Haiku (Fast)' },
        ],
        ollama: [
            { value: 'llama3', text: 'Llama 3 (8B)' },
            { value: 'llama3:70b', text: 'Llama 3 (70B)' },
            { value: 'mistral', text: 'Mistral 7B' },
            { value: 'mixtral', text: 'Mixtral 8x7B' },
        ]
    };

    modelSelect.innerHTML = '';
    (models[provider] || models.openai).forEach(m => {
        const option = document.createElement('option');
        option.value = m.value;
        option.textContent = m.text;
        modelSelect.appendChild(option);
    });
}

function toggleCustomPrompt() {
    const personality = document.getElementById('llm-personality')?.value;
    const container = document.getElementById('llm-custom-prompt-container');

    if (personality === 'custom') {
        container?.classList.remove('hidden');
    } else {
        container?.classList.add('hidden');
    }
}

function updateLLMTemp() {
    const slider = document.getElementById('llm-temperature');
    const display = document.getElementById('llm-temp-val');
    display.textContent = (slider.value / 10).toFixed(1);
}

// ============ PRESETS ============
async function applyPreset(preset) {
    try {
        const response = await fetch(`/api/config/presets/${preset}`);
        const data = await response.json();

        if (data.config) {
            if (data.config.skip_probability !== undefined) {
                document.getElementById('skip-prob').value = data.config.skip_probability * 100;
                updateSlider('skip');
            }
            if (data.config.videos_per_session_min !== undefined) {
                document.getElementById('videos-min').value = data.config.videos_per_session_min;
                document.getElementById('videos-max').value = data.config.videos_per_session_max;
            }
            addEvent('info', `Applied "${preset}" preset`);
        }
    } catch (error) {
        addEvent('error', `Failed to load preset: ${error.message}`);
    }
}

// ============ TASK MANAGEMENT ============
async function startTask() {
    // Collect full wizard config
    const wizardConfig = collectWizardConfig();
    const url = wizardConfig.url;

    if (!url) {
        addEvent('error', 'Please enter a URL');
        goToWizardStep(1);
        return;
    }

    const urlLower = url.toLowerCase();
    if (urlLower.includes('tiktok.com')) {
        if (urlLower.includes('/photo/')) {
            addEvent('error', 'Photo URLs not supported - use a video URL (/video/) or profile (@username)');
            return;
        }
        if (urlLower.includes('/live/')) {
            addEvent('error', 'Live stream URLs not supported - use a video URL (/video/) or profile (@username)');
            return;
        }
    }
    if (urlLower.includes('instagram.com')) {
        if (urlLower.includes('/stories/')) {
            addEvent('error', 'Story URLs not supported - use a reel URL (/reel/) or profile');
            return;
        }
    }

    // Build the full config for the backend
    const config = {
        // Proxy settings
        use_proxies: wizardConfig.use_proxies,
        proxy_provider: wizardConfig.proxy_provider,
        proxy_rotation: wizardConfig.proxy_rotation,
        proxy_country: wizardConfig.proxy_country,
        proxy_session_type: wizardConfig.proxy_session_type,
        tor_port: wizardConfig.tor_port,
        tor_rotation: wizardConfig.tor_rotation,

        // User Agent settings
        use_user_agents: wizardConfig.use_user_agents,
        user_agent_mode: wizardConfig.user_agent_mode,
        user_agent_source: wizardConfig.user_agent_source,
        user_agent_browser: wizardConfig.user_agent_browser,
        user_agent_os: wizardConfig.user_agent_os,
        user_agent_pool_size: wizardConfig.user_agent_pool_size,
        user_agent_pool: wizardConfig.user_agent_pool,

        // Fingerprint settings
        use_fingerprints: wizardConfig.use_fingerprints,
        fingerprint_mode: wizardConfig.fingerprint_mode,
        fingerprint_source: wizardConfig.fingerprint_source,
        fingerprint_browser: wizardConfig.fingerprint_browser,
        fingerprint_os: wizardConfig.fingerprint_os,
        fingerprint_pool_size: wizardConfig.fingerprint_pool_size,
        fingerprint_pool: wizardConfig.fingerprint_pool,
        fingerprint_components: wizardConfig.fingerprint_components,
        use_screen_sizes: wizardConfig.use_screen_sizes,
        screen_types: wizardConfig.screen_types,

        // Behavior settings (Step 5)
        behavior: wizardConfig.behavior,

        // Execution
        headless: wizardConfig.headless,
        browser_engine: wizardConfig.browser_engine,
    };

    // Get LLM mode from behavior config
    const behaviorMode = wizardConfig.behavior?.mode || 'preset';
    const llmConfig = wizardConfig.behavior?.llm || null;

    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                platform: wizardConfig.platform,
                mode: wizardConfig.mode,
                workers: wizardConfig.workers,
                repeat: wizardConfig.repeat,
                config: config,
                behavior: wizardConfig.behavior,
            }),
        });

        const task = await response.json();
        tasks[task.task_id] = task;
        renderTasks();
        addEvent('success', `Task created: ${task.task_id}`);

        // Reset wizard to step 1 after successful task creation
        goToWizardStep(1);
        document.getElementById('url-input').value = '';
        setPlatform('generic');
    } catch (error) {
        addEvent('error', `Failed to create task: ${error.message}`);
    }
}

async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();
        tasks = {};
        data.tasks.forEach(task => {
            tasks[task.task_id] = task;
        });
        renderTasks();
        updateStats(data);
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

function updateTaskFromEvent(data) {
    const isStatusChange = ['task_created', 'task_started', 'task_completed', 'task_failed'].includes(data.type);

    if (data.task_id && tasks[data.task_id]) {
        if (data.progress !== undefined) tasks[data.task_id].progress = data.progress;
        if (data.status) tasks[data.task_id].status = data.status;
        if (data.results) tasks[data.task_id].results = data.results;
        if (data.error) tasks[data.task_id].error = data.error;
        renderTasks();

        if (selectedTaskId === data.task_id && isStatusChange) {
            selectTask(data.task_id);
        }
    }

    if (isStatusChange) {
        loadTasks();
        loadMetrics();
    }
}

function renderTasks() {
    const container = document.getElementById('tasks-list');
    if (!container) return;

    let filteredTasks = Object.values(tasks);

    if (currentTaskFilter !== 'all') {
        filteredTasks = filteredTasks.filter(t => t.status === currentTaskFilter);
    }

    filteredTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    if (filteredTasks.length === 0) {
        container.innerHTML = `<div class="text-sm text-gray-500 text-center py-8">No ${currentTaskFilter === 'all' ? '' : currentTaskFilter + ' '}tasks</div>`;
        return;
    }

    const statusColors = {
        pending: 'bg-blue-500/20 text-blue-400',
        running: 'bg-yellow-500/20 text-yellow-400',
        completed: 'bg-green-500/20 text-green-400',
        failed: 'bg-red-500/20 text-red-400',
        cancelled: 'bg-gray-500/20 text-gray-400',
    };

    const platformColors = {
        tiktok: 'text-pink-400',
        instagram: 'text-purple-400',
        youtube: 'text-red-400',
        dextools: 'text-blue-400',
        generic: 'text-gray-400',
    };

    container.innerHTML = filteredTasks.map(task => `
        <div class="px-4 py-3 hover:bg-surface-light cursor-pointer ${selectedTaskId === task.task_id ? 'bg-surface-light ring-1 ring-primary/50' : ''}" onclick="selectTask('${task.task_id}')">
            <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-mono text-gray-300">${task.task_id}</span>
                    <span class="text-xs ${platformColors[task.platform] || 'text-gray-400'}">${task.platform}</span>
                </div>
                <span class="text-xs px-2 py-0.5 rounded-full ${statusColors[task.status] || 'bg-gray-500/20 text-gray-400'}">${task.status}</span>
            </div>
            <div class="text-xs text-gray-500 truncate">${task.url}</div>
            ${task.status === 'running' ? `
                <div class="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                    <div class="task-progress h-full bg-gradient-to-r from-indigo-500 to-purple-500" style="width: ${(task.progress * 100).toFixed(0)}%"></div>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function setTaskFilter(filter) {
    currentTaskFilter = filter;

    document.querySelectorAll('.task-filter-tab').forEach(tab => {
        if (tab.dataset.filter === filter) {
            tab.classList.add('border-primary', 'text-primary');
            tab.classList.remove('border-transparent', 'text-gray-400');
        } else {
            tab.classList.remove('border-primary', 'text-primary');
            tab.classList.add('border-transparent', 'text-gray-400');
        }
    });

    renderTasks();
}

async function selectTask(taskId) {
    selectedTaskId = taskId;
    renderTasks();

    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        if (!response.ok) throw new Error('Task not found');
        const task = await response.json();
        renderTaskDetails(task);
    } catch (error) {
        addEvent('error', `Failed to load task: ${error.message}`);
    }
}

function renderTaskDetails(task) {
    const panel = document.getElementById('task-details-panel');
    const content = document.getElementById('task-details-content');
    if (!panel || !content) return;

    const statusColors = {
        pending: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        running: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        completed: 'bg-green-500/20 text-green-400 border-green-500/30',
        failed: 'bg-red-500/20 text-red-400 border-red-500/30',
        cancelled: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };

    const formatTime = (ts) => ts ? new Date(ts).toLocaleString() : '-';
    const formatDuration = (seconds) => {
        if (!seconds) return '-';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    };

    let html = `
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <span class="font-mono text-sm">${task.task_id}</span>
                <span class="text-xs px-2 py-0.5 rounded-full border ${statusColors[task.status]}">${task.status}</span>
            </div>
            <span class="text-xs text-gray-400">${task.platform}</span>
        </div>
        <div>
            <div class="text-xs text-gray-500 mb-1">URL</div>
            <div class="text-xs text-gray-300 break-all">${task.url}</div>
        </div>
        <div class="grid grid-cols-3 gap-2 text-center">
            <div class="bg-surface-light rounded p-2">
                <div class="text-xs text-gray-400">Mode</div>
                <div class="text-sm font-medium">${task.mode || 'batch'}</div>
            </div>
            <div class="bg-surface-light rounded p-2">
                <div class="text-xs text-gray-400">Workers</div>
                <div class="text-sm font-medium">${task.workers || 1}</div>
            </div>
            <div class="bg-surface-light rounded p-2">
                <div class="text-xs text-gray-400">Repeat</div>
                <div class="text-sm font-medium">${task.repeat || 1}</div>
            </div>
        </div>
        <div class="space-y-1 text-xs">
            <div class="flex justify-between"><span class="text-gray-500">Created:</span><span>${formatTime(task.created_at)}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Started:</span><span>${formatTime(task.started_at)}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Completed:</span><span>${formatTime(task.completed_at)}</span></div>
        </div>
    `;

    if (task.status === 'running') {
        html += `
            <div>
                <div class="flex justify-between text-xs mb-1">
                    <span class="text-gray-500">Progress</span>
                    <span>${(task.progress * 100).toFixed(0)}%</span>
                </div>
                <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all" style="width: ${(task.progress * 100).toFixed(0)}%"></div>
                </div>
            </div>
        `;
    }

    if (task.status === 'completed' && task.results) {
        const r = task.results;
        html += `<div><div class="text-xs text-gray-500 mb-2">Results</div>
            <div class="grid grid-cols-2 gap-2 text-center">
                ${r.videos_watched !== undefined ? `
                    <div class="${r.videos_watched > 0 ? 'bg-green-500/10 border-green-500/20' : 'bg-gray-500/10 border-gray-600'} border rounded p-2">
                        <div class="text-lg font-bold ${r.videos_watched > 0 ? 'text-green-400' : 'text-gray-500'}">${r.videos_watched}</div>
                        <div class="text-xs text-gray-400">Videos</div>
                    </div>
                ` : ''}
                ${r.bio_links_clicked !== undefined ? `
                    <div class="${r.bio_links_clicked > 0 ? 'bg-purple-500/10 border-purple-500/20' : 'bg-gray-500/10 border-gray-600'} border rounded p-2">
                        <div class="text-lg font-bold ${r.bio_links_clicked > 0 ? 'text-purple-400' : 'text-gray-500'}">${r.bio_links_clicked}</div>
                        <div class="text-xs text-gray-400">Bio Clicks</div>
                    </div>
                ` : ''}
            </div>
        </div>`;
    }

    if (task.status === 'failed' && task.error) {
        html += `
            <div>
                <div class="text-xs text-gray-500 mb-2">Error</div>
                <div class="bg-red-500/10 border border-red-500/30 rounded p-3 text-xs text-red-400">${task.error}</div>
            </div>
        `;
    }

    html += `<div class="flex gap-2 pt-2">`;
    if (task.status === 'running' || task.status === 'pending') {
        html += `<button onclick="cancelTask('${task.task_id}')" class="flex-1 px-3 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded hover:bg-red-500/30 text-xs font-medium">Cancel</button>`;
    }
    if (task.status === 'failed' || task.status === 'cancelled') {
        html += `<button onclick="retryTask('${task.task_id}')" class="flex-1 px-3 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded hover:bg-blue-500/30 text-xs font-medium">Retry</button>`;
    }
    html += `</div>`;

    content.innerHTML = html;
    panel.classList.remove('hidden');
}

function closeTaskDetails() {
    document.getElementById('task-details-panel').classList.add('hidden');
    selectedTaskId = null;
    renderTasks();
}

async function cancelTask(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to cancel');
        addEvent('info', `Task ${taskId} cancelled`);
        loadTasks();
        closeTaskDetails();
    } catch (error) {
        addEvent('error', `Failed to cancel: ${error.message}`);
    }
}

async function retryTask(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/retry`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to retry');
        const newTask = await response.json();
        addEvent('success', `Task retried as ${newTask.task_id}`);
        loadTasks();
        selectTask(newTask.task_id);
    } catch (error) {
        addEvent('error', `Failed to retry: ${error.message}`);
    }
}

function updateStats(data) {
    const running = document.getElementById('stat-running');
    const completed = document.getElementById('stat-completed');
    const failed = document.getElementById('stat-failed');
    if (running) running.textContent = data.running || 0;
    if (completed) completed.textContent = data.completed || 0;
    if (failed) failed.textContent = data.failed || 0;
}

async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();

        const activeWorkers = document.getElementById('active-workers');
        const uptime = document.getElementById('uptime');

        if (activeWorkers) activeWorkers.textContent = data.workers_active || 0;
        if (uptime && data.uptime_seconds) {
            const mins = Math.floor(data.uptime_seconds / 60);
            const hours = Math.floor(mins / 60);
            uptime.textContent = hours > 0 ? `${hours}h ${mins % 60}m` : `${mins}m`;
        }
    } catch (error) {
        console.error('Failed to load metrics:', error);
    }
}

// ============ PROXY MANAGEMENT ============
async function loadProxyStats() {
    try {
        const response = await fetch('/api/proxies/stats');
        if (response.ok) {
            const data = await response.json();
            const total = document.getElementById('proxy-total');
            const alive = document.getElementById('proxy-alive');
            const dead = document.getElementById('proxy-dead');
            const untested = document.getElementById('proxy-untested');

            if (total) total.textContent = data.total?.toLocaleString() || '0';
            if (alive) alive.textContent = data.alive?.toLocaleString() || '0';
            if (dead) dead.textContent = data.dead?.toLocaleString() || '0';
            if (untested) untested.textContent = data.untested?.toLocaleString() || '0';

            const fileOption = document.querySelector('option[value="file"]');
            if (fileOption) {
                fileOption.textContent = `File (${data.total?.toLocaleString() || '0'} proxies)`;
            }
        }
    } catch (error) {
        console.log('Proxy stats not available');
    }
}

async function loadProxySources() {
    try {
        const response = await fetch('/api/proxies/sources');
        const data = await response.json();
        proxySources = data.sources || [];
        renderProxySources();
        const sourcesCount = document.getElementById('sources-count');
        if (sourcesCount) sourcesCount.textContent = `${proxySources.length} sources available`;
    } catch (error) {
        console.error('Failed to load sources:', error);
    }
}

function renderProxySources(filteredSources = null) {
    const container = document.getElementById('proxy-sources-list');
    if (!container) return;

    const sources = filteredSources || [...proxySources, ...customSources];

    const typeColors = {
        'plain': 'bg-blue-500/20 text-blue-400',
        'raw_txt': 'bg-cyan-500/20 text-cyan-400',
        'html_table': 'bg-green-500/20 text-green-400',
        'geonode_api': 'bg-purple-500/20 text-purple-400',
        'hidemy': 'bg-orange-500/20 text-orange-400',
        'proxynova': 'bg-red-500/20 text-red-400',
        'custom': 'bg-yellow-500/20 text-yellow-400',
    };

    container.innerHTML = sources.map((source, idx) => {
        const status = sourcesScrapeStatus[source.name] || {};
        const isActive = status.status === 'scraping';
        const isDone = status.status === 'done';
        const found = status.found || 0;

        const alive = status.alive || 0;

        let statusBadge = '';
        if (isActive) {
            statusBadge = `<span class="px-2 py-0.5 rounded text-xs bg-yellow-500/30 text-yellow-400 animate-pulse">Scraping...</span>`;
        } else if (isDone) {
            const foundColor = found > 0 ? 'bg-blue-500/30 text-blue-400' : 'bg-gray-500/30 text-gray-400';
            const aliveColor = alive > 0 ? 'bg-green-500/30 text-green-400' : 'bg-gray-500/30 text-gray-400';
            statusBadge = `
                <span class="px-2 py-0.5 rounded text-xs ${foundColor}">${found}</span>
                <span class="px-2 py-0.5 rounded text-xs ${aliveColor}">${alive} alive</span>
            `;
        } else {
            statusBadge = `<span class="px-2 py-0.5 rounded text-xs ${typeColors[source.type] || 'bg-gray-500/20 text-gray-400'}">${source.type}</span>`;
        }

        return `
        <div class="p-3 hover:bg-surface-light group ${isActive ? 'bg-yellow-500/5 border-l-2 border-yellow-500' : ''}" data-source="${source.name}">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded flex items-center justify-center text-xs font-bold ${isActive ? 'bg-yellow-500/30 text-yellow-400' : isDone ? 'bg-green-500/20 text-green-400' : typeColors[source.type] || 'bg-gray-500/20 text-gray-400'}">
                    ${isDone ? '✓' : (idx + 1).toString().padStart(2, '0')}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium truncate">${source.name}</div>
                    <div class="text-xs text-gray-500 truncate">${source.url.length > 50 ? source.url.slice(0, 50) + '...' : source.url}</div>
                </div>
                ${statusBadge}
            </div>
        </div>
    `}).join('');

    const sourcesCount = document.getElementById('sources-count');
    if (sourcesCount) sourcesCount.textContent = `${sources.length} sources available`;
}

function updateSourceStatus(currentSource, results) {
    sourcesScrapeStatus = {};
    if (results) {
        results.forEach(r => {
            sourcesScrapeStatus[r.name] = {
                status: 'done',
                found: r.found,
                method: r.method,
                alive: r.alive || 0
            };
        });
    }
    if (currentSource && !sourcesScrapeStatus[currentSource]) {
        sourcesScrapeStatus[currentSource] = { status: 'scraping' };
    }
    renderProxySources();
}

function clearSourceStatus() {
    sourcesScrapeStatus = {};
    renderProxySources();
}

function filterSources() {
    const searchEl = document.getElementById('source-search');
    const filterEl = document.getElementById('source-filter');
    if (!searchEl || !filterEl) return;

    const search = searchEl.value.toLowerCase();
    const typeFilter = filterEl.value;

    let filtered = [...proxySources, ...customSources];

    if (search) {
        filtered = filtered.filter(s =>
            s.name.toLowerCase().includes(search) ||
            s.url.toLowerCase().includes(search)
        );
    }

    if (typeFilter !== 'all') {
        filtered = filtered.filter(s => s.type === typeFilter);
    }

    renderProxySources(filtered);
}

function addCustomSource() {
    const nameEl = document.getElementById('custom-source-name');
    const urlEl = document.getElementById('custom-source-url');
    if (!nameEl || !urlEl) return;

    const name = nameEl.value.trim();
    const url = urlEl.value.trim();

    if (!name || !url) {
        addEvent('error', 'Please enter both name and URL');
        return;
    }

    if (!url.startsWith('http')) {
        addEvent('error', 'URL must start with http:// or https://');
        return;
    }

    customSources.push({
        id: 'custom_' + Date.now(),
        name: name,
        url: url,
        type: 'custom'
    });

    nameEl.value = '';
    urlEl.value = '';

    renderProxySources();
    addEvent('success', `Added custom source: ${name}`);
}

// ============ SCRAPE JOB ============
async function startScrapeJob() {
    try {
        const response = await fetch('/api/proxies/scrape/start', { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            addEvent('error', data.error);
            return;
        }

        currentScrapeJobId = data.job_id;
        document.getElementById('scrape-sources-total').textContent = data.sources_total;
        document.getElementById('scrape-modal').classList.remove('hidden');
        document.getElementById('scrape-close-btn').classList.add('hidden');
        document.getElementById('scrape-results-list').innerHTML = '';
        // Reset summary and OK button for new scrape
        document.getElementById('scrape-summary').classList.add('hidden');
        document.getElementById('scrape-ok-btn').classList.add('hidden');
        document.getElementById('scrape-progress-bar').style.width = '0%';
        document.getElementById('scrape-sources-done').textContent = '0';
        document.getElementById('scrape-proxies-found').textContent = '0';
        document.getElementById('scrape-tested-count').textContent = '0';
        document.getElementById('scrape-alive-count').textContent = '0';
        document.getElementById('scrape-current-source').textContent = 'Starting...';

        scrapePollingInterval = setInterval(pollScrapeJob, 500);
        addEvent('info', 'Scraping started...');
    } catch (error) {
        addEvent('error', 'Failed to start scrape: ' + error.message);
    }
}

async function pollScrapeJob() {
    if (!currentScrapeJobId) return;

    try {
        const response = await fetch(`/api/proxies/scrape/${currentScrapeJobId}`);
        const job = await response.json();

        if (job.error) {
            clearInterval(scrapePollingInterval);
            return;
        }

        // Update status text based on current phase
        const statusText = job.status === 'testing'
            ? `Testing: ${job.testing_source || 'proxies'}...`
            : (job.current_source || 'Processing...');
        document.getElementById('scrape-current-source').textContent = statusText;
        document.getElementById('scrape-sources-done').textContent = job.sources_done;
        document.getElementById('scrape-proxies-found').textContent = job.proxies_found.toLocaleString();
        document.getElementById('scrape-tested-count').textContent = (job.tested_total || 0).toLocaleString();
        document.getElementById('scrape-alive-count').textContent = (job.alive_total || 0).toLocaleString();

        const progress = (job.sources_done / job.sources_total) * 100;
        document.getElementById('scrape-progress-bar').style.width = progress + '%';

        updateFloatingProgress(job);
        updateSourceStatus(job.current_source, job.results);

        if (job.status === 'completed') {
            clearInterval(scrapePollingInterval);
            scrapePollingInterval = null;
            document.getElementById('scrape-current-source').textContent = 'Complete!';
            document.getElementById('scrape-close-btn').classList.remove('hidden');
            document.getElementById('scrape-floating').classList.add('hidden');
            updateSourceStatus(null, job.results);

            // Show summary and OK button
            document.getElementById('scrape-summary').classList.remove('hidden');
            document.getElementById('scrape-ok-btn').classList.remove('hidden');
            const aliveCount = job.alive_total || 0;
            document.getElementById('scrape-summary-text').textContent =
                `${job.proxies_found.toLocaleString()} found, ${aliveCount.toLocaleString()} ALIVE and ready to use!`;

            addEvent('success', `Done! ${aliveCount.toLocaleString()} alive proxies ready`);
            loadProxyStats();
        }
    } catch (error) {
        clearInterval(scrapePollingInterval);
        scrapePollingInterval = null;
    }
}

function closeScrapeModal() {
    document.getElementById('scrape-modal').classList.add('hidden');
    document.getElementById('scrape-floating').classList.add('hidden');
    if (scrapePollingInterval) {
        clearInterval(scrapePollingInterval);
        scrapePollingInterval = null;
    }
    currentScrapeJobId = null;
    clearSourceStatus();
}

function minimizeScrapeModal() {
    document.getElementById('scrape-modal').classList.add('hidden');
    document.getElementById('scrape-floating').classList.remove('hidden');
}

function maximizeScrapeModal() {
    document.getElementById('scrape-floating').classList.add('hidden');
    document.getElementById('scrape-modal').classList.remove('hidden');
}

function updateFloatingProgress(job) {
    const status = document.getElementById('scrape-floating-status');
    const count = document.getElementById('scrape-floating-count');
    const alive = document.getElementById('scrape-floating-alive');
    const bar = document.getElementById('scrape-floating-bar');

    if (status) status.textContent = `${job.sources_done}/${job.sources_total} sources`;
    if (count) count.textContent = job.proxies_found.toLocaleString();
    if (alive) alive.textContent = `${(job.alive_total || 0).toLocaleString()} alive`;
    if (bar) {
        const progress = (job.sources_done / job.sources_total) * 100;
        bar.style.width = progress + '%';
    }
}

// ============ TEST JOB ============
async function startTestJob() {
    try {
        const sourceFile = document.getElementById('test-source-file')?.value || 'aggregated';
        const response = await fetch(`/api/proxies/test/start?source_file=${sourceFile}`, { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            addEvent('error', data.error);
            return;
        }

        currentTestJobId = data.job_id;
        document.getElementById('test-total').textContent = data.total;
        document.getElementById('test-progress-panel').classList.remove('hidden');

        testPollingInterval = setInterval(pollTestJob, 500);
        addEvent('info', `Testing ${data.total.toLocaleString()} proxies...`);
    } catch (error) {
        addEvent('error', 'Failed to start test: ' + error.message);
    }
}

async function pollTestJob() {
    if (!currentTestJobId) return;

    try {
        const response = await fetch(`/api/proxies/test/${currentTestJobId}`);
        const job = await response.json();

        if (job.error) {
            clearInterval(testPollingInterval);
            return;
        }

        document.getElementById('test-tested').textContent = job.tested;
        document.getElementById('test-alive').textContent = job.alive;
        document.getElementById('test-dead-count').textContent = job.dead;
        document.getElementById('test-progress-status').textContent = `~${job.speed_per_sec}/sec`;

        if (job.eta_seconds > 0) {
            const mins = Math.floor(job.eta_seconds / 60);
            const secs = job.eta_seconds % 60;
            document.getElementById('test-eta').textContent = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
        }

        const progress = job.total > 0 ? (job.tested / job.total) * 100 : 0;
        document.getElementById('test-progress-bar').style.width = progress + '%';

        if (job.status === 'completed' || job.status === 'cancelled') {
            clearInterval(testPollingInterval);

            // Update to show completion state
            document.getElementById('test-progress-bar').style.width = '100%';
            document.getElementById('test-progress-bar').classList.remove('bg-blue-500');
            document.getElementById('test-progress-bar').classList.add('bg-green-500');
            document.getElementById('test-progress-status').textContent = 'Complete!';
            document.getElementById('test-eta').textContent = '--';

            // Show final results for 5 seconds before hiding
            setTimeout(() => {
                document.getElementById('test-progress-panel').classList.add('hidden');
                // Reset bar color for next run
                document.getElementById('test-progress-bar').classList.remove('bg-green-500');
                document.getElementById('test-progress-bar').classList.add('bg-blue-500');
            }, 5000);

            addEvent('success', `Test complete: ${job.alive} alive, ${job.dead} dead`);
            loadProxyStats();
            currentTestJobId = null;
        }
    } catch (error) {
        clearInterval(testPollingInterval);
    }
}

async function stopTestJob() {
    if (!currentTestJobId) return;

    try {
        await fetch(`/api/proxies/test/${currentTestJobId}/stop`, { method: 'POST' });
        addEvent('info', 'Stopping test...');
    } catch (error) {
        addEvent('error', 'Failed to stop: ' + error.message);
    }
}

// ============ OTHER PROXY FUNCTIONS ============
async function importProxiesFromText() {
    const textarea = document.getElementById('import-proxies-text');
    const text = textarea.value.trim();
    if (!text) {
        addEvent('error', 'Please paste proxies first');
        return;
    }

    const lines = text.split('\n').filter(l => l.trim());
    addEvent('info', `Importing ${lines.length} proxies...`);

    try {
        const response = await fetch('/api/proxies/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ proxies: lines })
        });
        const data = await response.json();

        if (data.error) {
            addEvent('error', data.error);
            return;
        }

        addEvent('success', `Imported ${data.added.toLocaleString()} proxies (${data.duplicates} duplicates skipped)`);
        textarea.value = '';
        loadProxyStats();
    } catch (error) {
        addEvent('error', 'Import failed: ' + error.message);
    }
}

function importProxiesFromFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
        const text = e.target.result;
        document.getElementById('import-proxies-text').value = text;
        addEvent('info', `Loaded ${file.name}`);
    };
    reader.readAsText(file);
    event.target.value = '';
}

// Premium Provider Configuration
let currentProvider = null;
let selectedProxyProvider = 'file';  // Task wizard proxy provider selection

const providerInfo = {
    decodo: { name: 'Decodo', subtitle: 'Smartproxy - $3.50/GB residential', usesUsername: true },
    brightdata: { name: 'Bright Data', subtitle: 'Enterprise - $8/GB, zones supported', usesUsername: false },
    oxylabs: { name: 'Oxylabs', subtitle: 'Enterprise - $8/GB residential', usesUsername: true },
    iproyal: { name: 'IPRoyal', subtitle: 'Budget - $5.50/GB residential', usesUsername: true },
    webshare: { name: 'Webshare', subtitle: 'Budget - Free tier available', usesUsername: false, usesApiKey: true },
};

async function configureProvider(provider) {
    currentProvider = provider;
    const info = providerInfo[provider] || { name: provider, subtitle: 'Premium proxy provider' };

    // Update modal title
    document.getElementById('provider-modal-title').textContent = `Configure ${info.name}`;
    document.getElementById('provider-modal-subtitle').textContent = info.subtitle;

    // Show/hide provider-specific fields
    document.getElementById('brightdata-fields').classList.toggle('hidden', provider !== 'brightdata');
    document.getElementById('webshare-fields').classList.toggle('hidden', provider !== 'webshare');
    document.getElementById('prov-username-group').classList.toggle('hidden', provider === 'webshare');
    document.getElementById('prov-password-group').classList.toggle('hidden', provider === 'webshare');

    // Clear previous values
    document.getElementById('prov-username').value = '';
    document.getElementById('prov-password').value = '';
    document.getElementById('prov-customer-id').value = '';
    document.getElementById('prov-zone').value = 'residential';
    document.getElementById('prov-api-key').value = '';
    document.getElementById('prov-country').value = '';
    document.getElementById('prov-city').value = '';
    document.getElementById('prov-session-type').value = 'rotating';
    document.getElementById('prov-test-result').classList.add('hidden');

    // Load existing configuration if any
    try {
        const response = await fetch(`/api/proxies/providers/${provider}`);
        const data = await response.json();
        if (data.configured && data.config) {
            const config = data.config;
            if (config.username) document.getElementById('prov-username').value = config.username;
            if (config.customer_id) document.getElementById('prov-customer-id').value = config.customer_id;
            if (config.zone) document.getElementById('prov-zone').value = config.zone;
            if (config.country) document.getElementById('prov-country').value = config.country;
            if (config.city) document.getElementById('prov-city').value = config.city;
            if (config.session_type) document.getElementById('prov-session-type').value = config.session_type;
        }
    } catch (error) {
        console.error('Failed to load provider config:', error);
    }

    // Show modal
    document.getElementById('provider-modal').classList.remove('hidden');
}

function closeProviderModal() {
    document.getElementById('provider-modal').classList.add('hidden');
    currentProvider = null;
}

async function testProvider() {
    if (!currentProvider) return;

    const testBtn = document.getElementById('prov-test-btn');
    const resultDiv = document.getElementById('prov-test-result');
    const resultMsg = document.getElementById('prov-test-message');

    testBtn.disabled = true;
    testBtn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg> Testing...';

    // First save, then test
    await saveProviderInternal();

    try {
        const response = await fetch(`/api/proxies/providers/${currentProvider}/test`, { method: 'POST' });
        const data = await response.json();

        resultDiv.classList.remove('hidden');
        if (data.success) {
            resultDiv.className = 'p-3 rounded-lg text-sm bg-green-500/20 border border-green-500/30';
            resultMsg.innerHTML = `<span class="text-green-400 font-medium">Connection successful!</span><br>
                <span class="text-gray-400">IP: ${data.ip || 'N/A'} | Latency: ${data.latency_ms || 'N/A'}ms</span>`;
        } else {
            resultDiv.className = 'p-3 rounded-lg text-sm bg-red-500/20 border border-red-500/30';
            resultMsg.innerHTML = `<span class="text-red-400 font-medium">Connection failed</span><br>
                <span class="text-gray-400">${data.error || 'Unknown error'}</span>`;
        }
    } catch (error) {
        resultDiv.classList.remove('hidden');
        resultDiv.className = 'p-3 rounded-lg text-sm bg-red-500/20 border border-red-500/30';
        resultMsg.innerHTML = `<span class="text-red-400 font-medium">Test failed</span><br>
            <span class="text-gray-400">${error.message}</span>`;
    }

    testBtn.disabled = false;
    testBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Test Connection';
}

async function saveProviderInternal() {
    if (!currentProvider) return false;

    const config = {
        provider: currentProvider,
        username: document.getElementById('prov-username').value || null,
        password: document.getElementById('prov-password').value || null,
        api_key: document.getElementById('prov-api-key').value || null,
        customer_id: document.getElementById('prov-customer-id').value || null,
        zone: document.getElementById('prov-zone').value || null,
        country: document.getElementById('prov-country').value || null,
        city: document.getElementById('prov-city').value || null,
        session_type: document.getElementById('prov-session-type').value,
    };

    try {
        const response = await fetch('/api/proxies/providers/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        return data.success;
    } catch (error) {
        console.error('Failed to save provider:', error);
        return false;
    }
}

async function saveProvider() {
    if (!currentProvider) return;

    const saveBtn = document.getElementById('prov-save-btn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    const success = await saveProviderInternal();

    if (success) {
        addEvent('success', `${providerInfo[currentProvider]?.name || currentProvider} provider configured`);
        closeProviderModal();
        // Refresh provider list in UI
        loadProviderStatus();
    } else {
        addEvent('error', 'Failed to save provider configuration');
    }

    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Provider';
}

async function loadProviderStatus() {
    // Update provider buttons in the UI to show configured status
    try {
        const response = await fetch('/api/proxies/providers');
        const data = await response.json();

        for (const provider of data.providers || []) {
            // Update status in task wizard
            const statusEl = document.getElementById(`${provider.name}-status`);
            if (statusEl) {
                if (provider.configured) {
                    statusEl.textContent = provider.country ? `Configured (${provider.country.toUpperCase()})` : 'Configured';
                    statusEl.classList.remove('text-gray-500');
                    statusEl.classList.add('text-green-400');
                } else {
                    statusEl.textContent = 'Not configured';
                    statusEl.classList.remove('text-green-400');
                    statusEl.classList.add('text-gray-500');
                }
            }
        }
    } catch (error) {
        console.error('Failed to load provider status:', error);
    }
}

// Proxy provider selection in task wizard
function setProxyProvider(provider) {
    selectedProxyProvider = provider;

    // Show/hide appropriate sections
    const freeSection = document.getElementById('wizard-free-proxy-section');
    const premiumSection = document.getElementById('wizard-premium-proxy-section');
    const torSection = document.getElementById('wizard-tor-proxy-section');
    const infoEl = document.getElementById('premium-provider-info');

    // Hide all sections first
    freeSection?.classList.add('hidden');
    premiumSection?.classList.add('hidden');
    torSection?.classList.add('hidden');

    if (provider === 'file') {
        freeSection?.classList.remove('hidden');
    } else if (provider === 'tor') {
        torSection?.classList.remove('hidden');
    } else if (provider === 'none') {
        // All hidden - direct connection
    } else {
        // Premium provider selected
        premiumSection?.classList.remove('hidden');

        // Check if configured
        const statusEl = document.getElementById(`${provider}-status`);
        const isConfigured = statusEl?.textContent?.includes('Configured');

        if (infoEl) {
            if (isConfigured) {
                infoEl.textContent = `Using ${providerInfo[provider]?.name || provider} for proxy rotation`;
                infoEl.classList.remove('text-yellow-400');
                infoEl.classList.add('text-gray-500');
            } else {
                infoEl.innerHTML = `<span class="text-yellow-400">Provider not configured.</span> <a href="#" onclick="switchPage('proxies'); return false;" class="text-primary underline">Configure now</a>`;
            }
        }
    }

    // Update radio visual
    document.querySelectorAll('.proxy-provider-option').forEach(el => {
        el.classList.remove('border-primary');
    });
    const selectedInput = document.querySelector(`input[name="proxy_provider"][value="${provider}"]`);
    if (selectedInput) {
        selectedInput.closest('.proxy-provider-option')?.classList.add('border-primary');
    }
}

// Test Tor connection
async function testTorConnection() {
    const statusEl = document.getElementById('tor-connection-status');
    const port = document.getElementById('wizard-tor-port')?.value || 9050;

    if (statusEl) {
        statusEl.textContent = 'Testing...';
        statusEl.className = 'text-xs text-yellow-400';
    }

    try {
        const response = await fetch('/api/proxies/providers/tor/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port: parseInt(port) })
        });
        const data = await response.json();

        if (statusEl) {
            if (data.connected) {
                statusEl.textContent = `Connected! IP: ${data.ip || 'Unknown'}`;
                statusEl.className = 'text-xs text-green-400';
                document.getElementById('tor-status').textContent = 'Connected';
                document.getElementById('tor-status').className = 'text-xs text-green-400 mt-1';
            } else {
                statusEl.textContent = data.error || 'Connection failed';
                statusEl.className = 'text-xs text-red-400';
            }
        }
    } catch (error) {
        if (statusEl) {
            statusEl.textContent = 'Test failed: ' + error.message;
            statusEl.className = 'text-xs text-red-400';
        }
    }
}

async function exportProxies() {
    try {
        const response = await fetch('/api/proxies/export');
        const data = await response.json();

        if (data.error) {
            addEvent('error', data.error);
            return;
        }

        const blob = new Blob([data.proxies.join('\n')], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `proxies_${new Date().toISOString().slice(0,10)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        addEvent('success', `Exported ${data.proxies.length.toLocaleString()} proxies`);
    } catch (error) {
        addEvent('error', 'Export failed: ' + error.message);
    }
}

function clearDeadProxies() {
    // Open the modal instead of using confirm()
    const modal = document.getElementById('clear-dead-modal');
    const confirmSection = document.getElementById('clear-dead-confirm');
    const progressSection = document.getElementById('clear-dead-progress');
    const resultSection = document.getElementById('clear-dead-result');

    // Reset to initial state
    confirmSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    resultSection.classList.add('hidden');

    // Sync dropdown selection to modal radio buttons
    const sourceFile = document.getElementById('clear-source-file')?.value || 'alive';
    const radio = document.querySelector(`input[name="clear-source"][value="${sourceFile}"]`);
    if (radio) radio.checked = true;

    modal.classList.remove('hidden');
}

function closeClearDeadModal() {
    document.getElementById('clear-dead-modal').classList.add('hidden');
}

async function confirmClearDead() {
    const sourceFile = document.querySelector('input[name="clear-source"]:checked')?.value || 'alive';
    const fileName = sourceFile === 'alive' ? 'alive_proxies.txt' : 'aggregated.txt';

    // Show progress state
    document.getElementById('clear-dead-confirm').classList.add('hidden');
    document.getElementById('clear-dead-progress').classList.remove('hidden');
    document.getElementById('clear-dead-result').classList.add('hidden');
    document.getElementById('clear-dead-status').textContent = `Testing proxies in ${fileName}...`;

    addEvent('info', `Testing and clearing dead from ${fileName}...`);

    try {
        const response = await fetch(`/api/proxies/clear-dead?source_file=${sourceFile}`, { method: 'POST' });
        const data = await response.json();

        // Show result state
        document.getElementById('clear-dead-progress').classList.add('hidden');
        document.getElementById('clear-dead-result').classList.remove('hidden');

        const resultContent = document.getElementById('clear-dead-result-content');

        if (data.error) {
            resultContent.innerHTML = `
                <div class="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <svg class="w-8 h-8 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <div>
                        <div class="font-medium text-red-400">Error</div>
                        <div class="text-sm text-gray-400">${data.error}</div>
                    </div>
                </div>
            `;
            addEvent('error', data.error);
            return;
        }

        resultContent.innerHTML = `
            <div class="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                <svg class="w-8 h-8 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                <div>
                    <div class="font-medium text-green-400">Complete!</div>
                    <div class="text-sm text-gray-400">Tested ${data.tested} proxies</div>
                </div>
            </div>
            <div class="grid grid-cols-3 gap-3 mt-4">
                <div class="text-center p-3 bg-surface-light rounded-lg">
                    <div class="text-2xl font-bold text-blue-400">${data.tested}</div>
                    <div class="text-xs text-gray-400">Tested</div>
                </div>
                <div class="text-center p-3 bg-surface-light rounded-lg">
                    <div class="text-2xl font-bold text-red-400">${data.removed}</div>
                    <div class="text-xs text-gray-400">Removed</div>
                </div>
                <div class="text-center p-3 bg-surface-light rounded-lg">
                    <div class="text-2xl font-bold text-green-400">${data.remaining}</div>
                    <div class="text-xs text-gray-400">Alive</div>
                </div>
            </div>
        `;

        addEvent('success', `Tested ${data.tested}, removed ${data.removed} dead, ${data.remaining} alive`);
        loadProxyStats();
    } catch (error) {
        document.getElementById('clear-dead-progress').classList.add('hidden');
        document.getElementById('clear-dead-result').classList.remove('hidden');
        document.getElementById('clear-dead-result-content').innerHTML = `
            <div class="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <svg class="w-8 h-8 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                <div>
                    <div class="font-medium text-red-400">Error</div>
                    <div class="text-sm text-gray-400">${error.message}</div>
                </div>
            </div>
        `;
        addEvent('error', 'Failed to clear dead: ' + error.message);
    }
}

async function cleanDeadProxies() {
    if (!confirm('This will remove all dead proxies. Continue?')) return;

    addEvent('info', 'Removing dead proxies...');

    try {
        const response = await fetch('/api/proxies/clean', { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            addEvent('error', data.error);
            return;
        }

        if (data.removed === 0) {
            addEvent('info', 'No dead proxies to remove');
        } else {
            addEvent('success', `Removed ${data.removed.toLocaleString()} dead proxies`);
        }

        loadProxyStats();
    } catch (error) {
        addEvent('error', 'Failed to clean proxies: ' + error.message);
    }
}

// ============ EVENT LOG RESIZE ============
function startResizeEventLog(e) {
    isResizing = true;
    startY = e.clientY;
    const container = document.getElementById('event-log-container');
    startHeight = container.offsetHeight;
    document.addEventListener('mousemove', resizeEventLog);
    document.addEventListener('mouseup', stopResizeEventLog);
    e.preventDefault();
}

function resizeEventLog(e) {
    if (!isResizing) return;
    const container = document.getElementById('event-log-container');
    const delta = startY - e.clientY;
    const newHeight = Math.min(400, Math.max(80, startHeight + delta));
    container.style.height = newHeight + 'px';
}

function stopResizeEventLog() {
    isResizing = false;
    document.removeEventListener('mousemove', resizeEventLog);
    document.removeEventListener('mouseup', stopResizeEventLog);
}

function expandEventLog() {
    const container = document.getElementById('event-log-container');
    const currentHeight = container.offsetHeight;
    container.style.height = currentHeight < 300 ? '400px' : '150px';
}

// ============ DATA MANAGEMENT ============
async function loadDataStats() {
    try {
        const response = await fetch('/api/data/stats');
        if (response.ok) {
            const data = await response.json();
            const ua = document.getElementById('ua-count');
            const fp = document.getElementById('fp-count');
            const ref = document.getElementById('ref-count');
            const bl = document.getElementById('bl-count');
            const screen = document.getElementById('screen-count');
            const behavior = document.getElementById('behavior-count');
            const evasion = document.getElementById('evasion-count');

            if (ua) ua.textContent = (data.user_agents || 0).toLocaleString();
            if (fp) fp.textContent = (data.fingerprints || 0).toLocaleString();
            if (ref) ref.textContent = (data.referrers || 0).toLocaleString();
            if (bl) bl.textContent = (data.blacklists || 0).toLocaleString();
            if (screen) screen.textContent = (data.screen_sizes || 0).toLocaleString();
            if (behavior) behavior.textContent = (data.behavior || 0).toLocaleString();
            if (evasion) evasion.textContent = (data.evasion || 0).toLocaleString();
        }
    } catch (error) {
        console.log('Data stats not available');
    }
}

async function openDataManager(category, title) {
    currentDataCategory = category;
    document.getElementById('data-manager-title').textContent = `Manage ${title}`;
    document.getElementById('data-manager-modal').classList.remove('hidden');
    document.getElementById('new-data-item').value = '';
    document.getElementById('data-search').value = '';
    document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-gray-500">Loading...</div>';

    try {
        const response = await fetch(`/api/data/${category}`);
        if (response.ok) {
            const data = await response.json();
            const select = document.getElementById('data-file-select');
            select.innerHTML = '<option value="">-- Select a file --</option>';

            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const opt = document.createElement('option');
                    opt.value = file.name;
                    opt.textContent = `${file.name} (${file.count} items)`;
                    select.appendChild(opt);
                });
                select.selectedIndex = 1;
                loadFileData();
            } else {
                document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-gray-500">No data files found</div>';
            }
        }
    } catch (error) {
        document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-red-400">Error loading data</div>';
    }
}

function closeDataManager() {
    document.getElementById('data-manager-modal').classList.add('hidden');
    currentDataCategory = null;
    currentDataItems = [];
    loadDataStats();
}

// ============ DATA GENERATION ============
function openGenerateModal(category, title) {
    document.getElementById('generate-category').value = category;
    document.getElementById('generate-modal-title').textContent = `Generate ${title}`;
    document.getElementById('generate-status').classList.add('hidden');
    document.getElementById('generate-btn').disabled = false;
    document.getElementById('generate-btn').textContent = 'Generate & Save';

    // Show/hide browser options based on category
    const browserOptions = document.getElementById('generate-browser-options');
    if (category === 'user_agents' || category === 'fingerprints') {
        browserOptions.classList.remove('hidden');
    } else {
        browserOptions.classList.add('hidden');
    }

    // Set default filename based on category
    const filenameInput = document.getElementById('generate-filename');
    if (category === 'fingerprints') {
        filenameInput.value = 'generated.json';
    } else {
        filenameInput.value = 'generated.txt';
    }

    document.getElementById('generate-data-modal').classList.remove('hidden');
}

function closeGenerateModal() {
    document.getElementById('generate-data-modal').classList.add('hidden');
}

async function generateAndSaveData() {
    const category = document.getElementById('generate-category').value;
    const count = parseInt(document.getElementById('generate-count').value);
    const browser = document.getElementById('generate-browser').value;
    const os = document.getElementById('generate-os').value;
    const targetFile = document.getElementById('generate-filename').value;

    const statusEl = document.getElementById('generate-status');
    const btn = document.getElementById('generate-btn');

    statusEl.textContent = `Generating ${count} items...`;
    statusEl.classList.remove('hidden', 'text-red-400', 'text-green-400');
    statusEl.classList.add('text-gray-400');
    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
        const response = await fetch(`/api/data/${category}/generate-and-save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                count,
                browser,
                os,
                target_file: targetFile
            })
        });

        const data = await response.json();

        if (data.success) {
            statusEl.textContent = `Generated ${data.generated} items. Saved to ${data.saved_to}. Total: ${data.new_total.toLocaleString()}`;
            statusEl.classList.remove('text-gray-400');
            statusEl.classList.add('text-green-400');
            btn.textContent = 'Done!';

            // Refresh stats
            loadDataStats();

            // Close modal after 2 seconds
            setTimeout(() => {
                closeGenerateModal();
            }, 2000);
        } else {
            statusEl.textContent = `Error: ${data.error}`;
            statusEl.classList.remove('text-gray-400');
            statusEl.classList.add('text-red-400');
            btn.disabled = false;
            btn.textContent = 'Generate & Save';
        }
    } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
        statusEl.classList.remove('text-gray-400');
        statusEl.classList.add('text-red-400');
        btn.disabled = false;
        btn.textContent = 'Generate & Save';
    }
}

async function loadFileData() {
    const select = document.getElementById('data-file-select');
    const filename = select.value;

    if (!filename || !currentDataCategory) {
        document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-gray-500">Select a file to view items</div>';
        return;
    }

    document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-gray-500">Loading...</div>';

    try {
        const response = await fetch(`/api/data/${currentDataCategory}/${filename}`);
        if (response.ok) {
            const data = await response.json();
            currentDataItems = data.data || [];
            renderDataItems();
        } else {
            document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-red-400">Error loading file</div>';
        }
    } catch (error) {
        document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-red-400">Error loading file</div>';
    }
}

function renderDataItems() {
    const search = document.getElementById('data-search').value.toLowerCase();
    const filtered = currentDataItems.filter(item => {
        const itemStr = typeof item === 'object' ? JSON.stringify(item) : String(item);
        return itemStr.toLowerCase().includes(search);
    });

    document.getElementById('data-item-count').textContent = filtered.length;

    if (filtered.length === 0) {
        document.getElementById('data-items-list').innerHTML = '<div class="p-8 text-center text-gray-500">No items found</div>';
        return;
    }

    const html = filtered.slice(0, 100).map((item) => {
        const display = typeof item === 'object' ? JSON.stringify(item) : String(item);
        const truncated = display.length > 100 ? display.substring(0, 100) + '...' : display;
        return `
            <div class="flex items-center gap-2 px-4 py-2 border-b border-gray-700 hover:bg-surface-light group">
                <div class="flex-1 text-sm font-mono truncate" title="${display.replace(/"/g, '&quot;')}">${truncated}</div>
                <button onclick="deleteDataItem('${display.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')" class="text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 p-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
            </div>
        `;
    }).join('');

    document.getElementById('data-items-list').innerHTML = html;

    if (filtered.length > 100) {
        document.getElementById('data-items-list').innerHTML += `<div class="p-4 text-center text-gray-500 text-sm">Showing first 100 of ${filtered.length} items</div>`;
    }
}

function filterDataItems() {
    renderDataItems();
}

async function addDataItem() {
    const input = document.getElementById('new-data-item');
    const content = input.value.trim();
    const filename = document.getElementById('data-file-select').value;

    if (!content || !filename || !currentDataCategory) return;

    try {
        const response = await fetch(`/api/data/${currentDataCategory}/${filename}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            input.value = '';
            loadFileData();
        } else {
            alert('Failed to add item');
        }
    } catch (error) {
        alert('Error adding item');
    }
}

async function deleteDataItem(content) {
    const filename = document.getElementById('data-file-select').value;

    if (!filename || !currentDataCategory) return;
    if (!confirm('Delete this item?')) return;

    try {
        const response = await fetch(`/api/data/${currentDataCategory}/${filename}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            loadFileData();
        } else {
            alert('Failed to delete item');
        }
    } catch (error) {
        alert('Error deleting item');
    }
}

// ============ SETTINGS ============
async function saveSettings() {
    try {
        // Map UI fields to backend Config model field names
        const settings = {
            engine: {
                default: document.getElementById('settings-browser-engine')?.value || 'patchright',
                headless: document.getElementById('settings-headless')?.checked ?? true,
            },
            concurrency: {
                max_workers: parseInt(document.getElementById('settings-workers')?.value) || 10,
            },
            proxy: {
                rotation_strategy: document.getElementById('settings-proxy-provider')?.value || 'weighted',
                health_check_interval: parseInt(document.getElementById('settings-proxy-timeout')?.value) * 30 || 300,
            },
            captcha: {
                enabled: !!document.getElementById('settings-2captcha-key')?.value,
                api_key: document.getElementById('settings-2captcha-key')?.value || null,
            },
            output: {
                debug: document.getElementById('settings-debug')?.checked ?? false,
            },
        };

        const response = await fetch('/api/config/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            addEvent('success', 'Settings saved successfully');
        } else {
            const error = await response.json();
            addEvent('error', `Failed to save settings: ${error.detail}`);
        }
    } catch (err) {
        console.error('Save settings error:', err);
        addEvent('error', 'Failed to save settings');
    }
}

async function resetSettings() {
    try {
        const response = await fetch('/api/config/reset', {
            method: 'POST'
        });

        if (response.ok) {
            addEvent('success', 'Settings reset to defaults');
            // Reload settings to show defaults
            await loadSettings();
        } else {
            addEvent('error', 'Failed to reset settings');
        }
    } catch (err) {
        console.error('Reset settings error:', err);
        addEvent('error', 'Failed to reset settings');
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/config/current');
        if (!response.ok) return;

        const config = await response.json();

        // Populate form fields - map backend field names to UI
        const browserEngine = document.getElementById('settings-browser-engine');
        if (browserEngine) browserEngine.value = config.engine?.default || 'patchright';

        const headless = document.getElementById('settings-headless');
        if (headless) headless.checked = config.engine?.headless ?? true;

        const workers = document.getElementById('settings-workers');
        if (workers) workers.value = config.concurrency?.max_workers || 10;

        const proxyProvider = document.getElementById('settings-proxy-provider');
        if (proxyProvider) proxyProvider.value = config.proxy?.rotation_strategy || 'weighted';

        const autoTest = document.getElementById('settings-auto-test');
        if (autoTest) autoTest.checked = true; // Always enabled by default

        const proxyTimeout = document.getElementById('settings-proxy-timeout');
        if (proxyTimeout) proxyTimeout.value = Math.round((config.proxy?.health_check_interval || 300) / 30);

        const captchaKey = document.getElementById('settings-2captcha-key');
        if (captchaKey && config.captcha?.api_key) captchaKey.value = config.captcha.api_key;

        const debug = document.getElementById('settings-debug');
        if (debug) debug.checked = config.output?.debug ?? false;

        console.log('Settings loaded from server');
    } catch (err) {
        console.error('Failed to load settings:', err);
    }
}

// ============ EVENT LOG ============
function addEvent(type, message) {
    const colors = {
        success: 'text-green-400',
        error: 'text-red-400',
        info: 'text-blue-400',
        action: 'text-purple-400',
        system: 'text-gray-400',
    };

    const time = new Date().toLocaleTimeString();
    const log = document.getElementById('event-log');
    if (!log) return;

    const entry = document.createElement('div');
    entry.className = `event-fade ${colors[type] || 'text-gray-400'}`;
    entry.innerHTML = `<span class="text-gray-500">${time}</span> ${message}`;
    log.insertBefore(entry, log.firstChild);

    while (log.children.length > 50) {
        log.removeChild(log.lastChild);
    }
}

function clearEvents() {
    const log = document.getElementById('event-log');
    if (log) log.innerHTML = '';
}

// ============ ZEFOY AUTOMATION ============
async function loadZefoyStats() {
    try {
        const response = await fetch('/api/zefoy/stats');
        if (response.ok) {
            const data = await response.json();
            const totalRuns = document.getElementById('zefoy-total-runs');
            const successful = document.getElementById('zefoy-successful');
            const failed = document.getElementById('zefoy-failed');
            const running = document.getElementById('zefoy-running');

            if (totalRuns) totalRuns.textContent = data.total_runs || 0;
            if (successful) successful.textContent = data.successful || 0;
            if (failed) failed.textContent = data.failed || 0;
            if (running) running.textContent = data.running || 0;

            zefoyCaptchasSolved = data.captchas_solved || 0;
            const captchaSolvedEl = document.getElementById('zefoy-captcha-solved');
            if (captchaSolvedEl) captchaSolvedEl.textContent = zefoyCaptchasSolved;
        }
    } catch (error) {
        console.log('Zefoy stats not available');
    }
}

async function loadZefoyJobs() {
    try {
        const response = await fetch('/api/zefoy/jobs');
        if (response.ok) {
            const data = await response.json();
            zefoyJobs = {};
            (data.jobs || []).forEach(job => {
                zefoyJobs[job.job_id] = job;
            });
            renderZefoyJobs();
        }
    } catch (error) {
        console.error('Failed to load zefoy jobs:', error);
    }
}

function renderZefoyJobs() {
    const container = document.getElementById('zefoy-active-jobs');
    if (!container) return;

    const jobs = Object.values(zefoyJobs).sort((a, b) =>
        new Date(b.created_at) - new Date(a.created_at)
    );

    if (jobs.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-4">No active jobs</div>';
        return;
    }

    const statusColors = {
        pending: 'bg-blue-500/20 text-blue-400',
        running: 'bg-yellow-500/20 text-yellow-400',
        completed: 'bg-green-500/20 text-green-400',
        failed: 'bg-red-500/20 text-red-400',
        cancelled: 'bg-gray-500/20 text-gray-400',
    };

    container.innerHTML = jobs.slice(0, 10).map(job => `
        <div class="px-4 py-3 hover:bg-surface-light">
            <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-mono text-gray-300">${job.job_id}</span>
                <span class="text-xs px-2 py-0.5 rounded-full ${statusColors[job.status] || 'bg-gray-500/20 text-gray-400'}">${job.status}</span>
            </div>
            <div class="text-xs text-gray-500 truncate mb-1">${job.services?.join(', ') || 'N/A'}</div>
            ${job.status === 'running' ? `
                <div class="h-1 bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-pink-500 to-purple-500" style="width: ${((job.completed_runs / job.total_runs) * 100).toFixed(0)}%"></div>
                </div>
                <div class="text-xs text-gray-400 mt-1">${job.completed_runs}/${job.total_runs} runs</div>
            ` : ''}
            <div class="flex gap-2 mt-2">
                ${job.status === 'running' || job.status === 'pending' ? `
                    <button onclick="cancelZefoyJob('${job.job_id}')" class="text-xs text-red-400 hover:text-red-300">Cancel</button>
                ` : ''}
                <button onclick="viewZefoyJobLogs('${job.job_id}')" class="text-xs text-blue-400 hover:text-blue-300">View Logs</button>
            </div>
        </div>
    `).join('');
}

function setupZefoyServiceButtons() {
    // Note: onclick handlers are already in HTML, no need to add listeners here
    // Just reset the selection state
    selectedZefoyServices.clear();
}

function toggleZefoyService(btn) {
    const service = btn.dataset.service;
    if (selectedZefoyServices.has(service)) {
        selectedZefoyServices.delete(service);
        btn.classList.remove('border-pink-500', 'text-pink-400', 'bg-pink-500/10');
        btn.classList.add('border-gray-600', 'text-gray-400');
    } else {
        selectedZefoyServices.add(service);
        btn.classList.add('border-pink-500', 'text-pink-400', 'bg-pink-500/10');
        btn.classList.remove('border-gray-600', 'text-gray-400');
    }
}

async function startZefoyJob() {
    const url = document.getElementById('zefoy-url')?.value.trim();
    if (!url) {
        addEvent('error', 'Please enter a TikTok URL');
        addZefoyLog('error', 'Missing TikTok URL');
        return;
    }

    if (!url.includes('tiktok.com')) {
        addEvent('error', 'Please enter a valid TikTok URL');
        addZefoyLog('error', 'Invalid URL - must be TikTok');
        return;
    }

    if (selectedZefoyServices.size === 0) {
        addEvent('error', 'Please select at least one service');
        addZefoyLog('error', 'No services selected');
        return;
    }

    const config = {
        url: url,
        services: Array.from(selectedZefoyServices),
        repeat_count: parseInt(document.getElementById('zefoy-repeat')?.value || 1),
        delay_seconds: parseInt(document.getElementById('zefoy-delay')?.value || 60),
        workers: parseInt(document.getElementById('zefoy-workers')?.value || 1),
        use_proxy: document.getElementById('zefoy-use-proxy')?.checked ?? true,
        headless: document.getElementById('zefoy-headless')?.checked ?? true,
        rotate_proxy: document.getElementById('zefoy-rotate-proxy')?.checked ?? true,
    };

    addZefoyLog('info', `Starting job for ${config.services.length} services...`);

    try {
        const response = await fetch('/api/zefoy/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });

        const data = await response.json();

        if (data.error) {
            addEvent('error', data.error);
            addZefoyLog('error', data.error);
            return;
        }

        zefoyJobs[data.job_id] = data;
        renderZefoyJobs();
        addEvent('success', `Job started: ${data.job_id}`);
        addZefoyLog('success', `Job ${data.job_id} created - click Refresh to update status`);
    } catch (error) {
        addEvent('error', 'Failed to start job: ' + error.message);
        addZefoyLog('error', 'Failed to start: ' + error.message);
    }
}

function refreshZefoyJobs() {
    loadZefoyJobs();
    loadZefoyStats();
    addZefoyLog('info', 'Refreshed job status');
}

async function cancelZefoyJob(jobId) {
    try {
        const response = await fetch(`/api/zefoy/jobs/${jobId}`, { method: 'DELETE' });
        if (response.ok) {
            addEvent('info', `Zefoy job ${jobId} cancelled`);
            addZefoyLog('info', `Job ${jobId} cancelled`);
            loadZefoyJobs();
        } else {
            addEvent('error', 'Failed to cancel job');
        }
    } catch (error) {
        addEvent('error', 'Failed to cancel: ' + error.message);
    }
}

function addZefoyLog(type, message) {
    const container = document.getElementById('zefoy-logs');
    if (!container) return;

    const colors = {
        success: 'text-green-400',
        error: 'text-red-400',
        info: 'text-blue-400',
        warning: 'text-yellow-400',
    };

    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `${colors[type] || 'text-gray-400'}`;
    entry.innerHTML = `<span class="text-gray-500">${time}</span> ${message}`;

    // Remove placeholder if exists
    const placeholder = container.querySelector('.text-gray-500:only-child');
    if (placeholder && placeholder.textContent.includes('Waiting')) {
        placeholder.remove();
    }

    container.insertBefore(entry, container.firstChild);

    // Limit to 50 entries
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

function clearZefoyLogs() {
    const container = document.getElementById('zefoy-logs');
    if (container) {
        container.innerHTML = '<div class="text-gray-500">Waiting for activity...</div>';
    }
}

// Zefoy service status cache
let zefoyServiceStatus = {};

async function checkZefoyStatus() {
    const btn = document.getElementById('zefoy-check-btn');
    const timeEl = document.getElementById('zefoy-status-time');

    btn.disabled = true;
    btn.textContent = 'Checking...';
    btn.classList.add('opacity-50');
    addZefoyLog('info', 'Checking Zefoy service status...');

    try {
        const response = await fetch('/api/zefoy/services/check', { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            addZefoyLog('error', 'Status check failed: ' + data.error);
            return;
        }

        zefoyServiceStatus = data.status || {};
        updateZefoyServiceButtons();

        const onlineCount = Object.values(zefoyServiceStatus).filter(v => v).length;
        const totalCount = Object.keys(zefoyServiceStatus).length;

        addZefoyLog('success', `Status check complete: ${onlineCount}/${totalCount} services online`);

        if (data.last_check) {
            const time = new Date(data.last_check).toLocaleTimeString();
            timeEl.textContent = `Last: ${time}`;
        }
    } catch (error) {
        addZefoyLog('error', 'Status check error: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Check Status';
        btn.classList.remove('opacity-50');
    }
}

function updateZefoyServiceButtons() {
    const buttons = document.querySelectorAll('.zefoy-service-btn');

    buttons.forEach(btn => {
        const service = btn.dataset.service;
        const isOnline = zefoyServiceStatus[service];
        const statusDot = btn.querySelector('.status-dot');

        // Remove old status dot if exists
        if (statusDot) statusDot.remove();

        // Add new status indicator
        const dot = document.createElement('span');
        dot.className = 'status-dot w-2 h-2 rounded-full inline-block ml-1';

        // Never disable buttons - let users try any service
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');

        if (isOnline === true) {
            dot.classList.add('bg-green-500');
            btn.title = 'Service online';
        } else if (isOnline === false) {
            dot.classList.add('bg-yellow-500');
            btn.title = 'Service may be offline - try anyway';
        } else {
            dot.classList.add('bg-gray-500');
            btn.title = 'Click to select';
        }

        btn.appendChild(dot);
    });
}

async function loadZefoyServiceStatus() {
    try {
        const response = await fetch('/api/zefoy/services/status');
        const data = await response.json();

        if (data.status && Object.keys(data.status).length > 0) {
            zefoyServiceStatus = data.status;
            updateZefoyServiceButtons();

            if (data.last_check) {
                const time = new Date(data.last_check).toLocaleTimeString();
                const timeEl = document.getElementById('zefoy-status-time');
                if (timeEl) timeEl.textContent = `Last: ${time}`;
            }
        }
    } catch (error) {
        console.log('No cached status');
    }
}

async function viewZefoyJobLogs(jobId) {
    try {
        const response = await fetch(`/api/zefoy/jobs/${jobId}`);
        if (!response.ok) {
            addZefoyLog('error', 'Failed to fetch job logs');
            return;
        }

        const job = await response.json();
        const container = document.getElementById('zefoy-logs');
        if (!container) return;

        container.innerHTML = `<div class="text-pink-400 font-bold mb-2">Logs for ${jobId}:</div>`;

        if (!job.logs || job.logs.length === 0) {
            container.innerHTML += '<div class="text-gray-500">No logs yet</div>';
            return;
        }

        job.logs.forEach(log => {
            const time = new Date(log.timestamp).toLocaleTimeString();
            const color = log.message.includes('error') || log.message.includes('failed')
                ? 'text-red-400'
                : log.message.includes('success') ? 'text-green-400' : 'text-gray-300';
            container.innerHTML += `<div class="${color}"><span class="text-gray-500">${time}</span> ${log.message}</div>`;
        });
    } catch (error) {
        addZefoyLog('error', 'Error fetching logs: ' + error.message);
    }
}

// ============ ALGORITHMS MANAGEMENT ============
let algorithmData = {};
let currentAlgorithmName = null;

async function loadAlgorithmStats() {
    try {
        const response = await fetch('/api/algorithms');
        if (response.ok) {
            const data = await response.json();
            algorithmData = data.algorithms || {};
            updateAlgorithmCards();
            updateAlgorithmStats();
        }
    } catch (error) {
        console.log('Algorithm stats not available');
    }
}

function updateAlgorithmStats() {
    const algorithms = Object.values(algorithmData);
    const active = algorithms.filter(a => a.status === 'active').length;
    const outdated = algorithms.filter(a => a.status === 'outdated').length;
    const deprecated = algorithms.filter(a => a.status === 'deprecated').length;
    const total = algorithms.length;

    const activeEl = document.getElementById('algo-active-count');
    const outdatedEl = document.getElementById('algo-outdated-count');
    const deprecatedEl = document.getElementById('algo-deprecated-count');
    const totalEl = document.getElementById('algo-total-count');

    if (activeEl) activeEl.textContent = active;
    if (outdatedEl) outdatedEl.textContent = outdated;
    if (deprecatedEl) deprecatedEl.textContent = deprecated;
    if (totalEl) totalEl.textContent = total;
}

function updateAlgorithmCards() {
    // Update status badges on cards based on API data
    for (const [name, algo] of Object.entries(algorithmData)) {
        const card = document.querySelector(`[data-algo="${name}"]`);
        if (!card) continue;

        const badge = card.querySelector('.status-badge');
        if (badge) {
            badge.className = 'status-badge px-2 py-0.5 rounded text-xs font-medium';
            if (algo.status === 'active') {
                badge.classList.add('bg-green-500/20', 'text-green-400');
                badge.textContent = 'Active';
            } else if (algo.status === 'outdated') {
                badge.classList.add('bg-yellow-500/20', 'text-yellow-400');
                badge.textContent = 'Outdated';
            } else if (algo.status === 'deprecated') {
                badge.classList.add('bg-red-500/20', 'text-red-400');
                badge.textContent = 'Deprecated';
            }
        }

        // Update last updated
        const lastUpdated = card.querySelector('.last-updated');
        if (lastUpdated && algo.last_updated) {
            lastUpdated.textContent = `Updated: ${algo.last_updated}`;
        }
    }
}

async function showAlgorithmDetail(name) {
    currentAlgorithmName = name;
    const modal = document.getElementById('algorithm-detail-modal');
    const title = document.getElementById('algo-modal-title');
    const status = document.getElementById('algo-modal-status');
    const content = document.getElementById('algo-modal-content');

    if (!modal) {
        console.error('Modal not found');
        addAlgoLog('error', 'Modal element not found');
        return;
    }

    modal.classList.remove('hidden');
    if (title) title.textContent = name;
    if (content) content.innerHTML = '<div class="text-center text-gray-400 py-8">Loading...</div>';

    try {
        const response = await fetch(`/api/algorithms/${encodeURIComponent(name)}`);
        if (response.ok) {
            const algo = await response.json();

            if (title) title.textContent = algo.name || name;

            if (status) {
                status.className = 'px-2 py-1 rounded text-xs font-medium';
                if (algo.status === 'active') {
                    status.classList.add('bg-green-500/20', 'text-green-400');
                    status.textContent = 'Active';
                } else if (algo.status === 'outdated') {
                    status.classList.add('bg-yellow-500/20', 'text-yellow-400');
                    status.textContent = 'Outdated';
                } else if (algo.status === 'deprecated') {
                    status.classList.add('bg-red-500/20', 'text-red-400');
                    status.textContent = 'Deprecated';
                } else {
                    status.classList.add('bg-gray-500/20', 'text-gray-400');
                    status.textContent = algo.status || 'Unknown';
                }
            }

            // Build content HTML
            let html = `
                <div class="space-y-4">
                    <div>
                        <div class="text-xs text-gray-500 mb-1">Description</div>
                        <p class="text-sm text-gray-300">${algo.description || 'No description available'}</p>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <div class="text-xs text-gray-500 mb-1">Platform</div>
                            <div class="text-sm">${algo.platform || 'Unknown'}</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-500 mb-1">Type</div>
                            <div class="text-sm">${algo.type || 'Unknown'}</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-500 mb-1">Method</div>
                            <div class="text-sm">${algo.method || 'Unknown'}</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-500 mb-1">Headers</div>
                            <div class="text-sm">${(algo.headers || []).join(', ') || 'None'}</div>
                        </div>
                    </div>
                    ${algo.last_updated ? `
                    <div>
                        <div class="text-xs text-gray-500 mb-1">Last Updated</div>
                        <div class="text-sm">${new Date(algo.last_updated).toLocaleDateString()}</div>
                    </div>
                    ` : ''}
                    ${algo.code ? `
                    <div>
                        <div class="text-xs text-gray-500 mb-1">Code</div>
                        <pre class="bg-gray-900 rounded-lg p-4 text-xs text-gray-300 overflow-x-auto max-h-64 overflow-y-auto"><code>${escapeHtml(algo.code)}</code></pre>
                    </div>
                    ` : '<div class="text-sm text-gray-500">No code available. Click "Refresh" to download from source.</div>'}
                </div>
            `;
            if (content) content.innerHTML = html;

            // Show/hide buttons based on algorithm capabilities
            const cdnBtn = document.getElementById('algo-cdn-btn');
            const refreshBtn = document.getElementById('algo-refresh-btn');

            if (cdnBtn) {
                if (algo.cdn_source) {
                    cdnBtn.classList.remove('hidden');
                } else {
                    cdnBtn.classList.add('hidden');
                }
            }

            if (refreshBtn) {
                if (algo.can_fetch) {
                    refreshBtn.classList.remove('hidden');
                } else {
                    refreshBtn.classList.add('hidden');
                }
            }
        } else {
            const errorText = await response.text();
            console.error('API error:', response.status, errorText);
            if (content) content.innerHTML = `<div class="text-center text-red-400 py-8">Error loading algorithm (${response.status})</div>`;
        }
    } catch (error) {
        console.error('Fetch error:', error);
        if (content) content.innerHTML = `<div class="text-center text-red-400 py-8">Error: ${error.message}</div>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function closeAlgorithmModal() {
    document.getElementById('algorithm-detail-modal').classList.add('hidden');
    currentAlgorithmName = null;
}

async function refreshAlgorithm() {
    // Refresh current algorithm from GitHub
    if (!currentAlgorithmName) return;

    const btn = document.getElementById('algo-refresh-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Refreshing...';
    btn.disabled = true;

    addAlgoLog('info', `Refreshing ${currentAlgorithmName} from source...`);

    try {
        const response = await fetch(`/api/algorithms/${encodeURIComponent(currentAlgorithmName)}/fetch/github`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.error) {
            addAlgoLog('error', `Refresh failed: ${data.error}`);
        } else {
            addAlgoLog('success', `${currentAlgorithmName}: Updated! (${data.size || 0} bytes)`);
            loadAlgorithmStats();
            // Reload the modal content
            showAlgorithmDetail(currentAlgorithmName);
        }
    } catch (error) {
        addAlgoLog('error', `Refresh error: ${error.message}`);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function fetchAlgorithm(name) {
    // Quick fetch from GitHub (used by card buttons)
    addAlgoLog('info', `Fetching ${name}...`);
    try {
        const response = await fetch(`/api/algorithms/${encodeURIComponent(name)}/fetch/github`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.error) {
            addAlgoLog('error', `Fetch failed: ${data.error}`);
        } else {
            addAlgoLog('success', `${name}: ${data.message || 'Fetched successfully'}`);
            loadAlgorithmStats();
        }
    } catch (error) {
        addAlgoLog('error', `Fetch error: ${error.message}`);
    }
}

function fetchAlgorithmFromCDN() {
    fetchFromCDN(currentAlgorithmName);
}

function openDocs(platform) {
    const docsUrls = {
        'instagram': 'https://developers.facebook.com/docs/instagram-api/',
        'youtube': 'https://developers.google.com/youtube/v3',
        'twitter': 'https://developer.twitter.com/en/docs/twitter-api',
        'facebook': 'https://developers.facebook.com/docs/graph-api/',
        'spotify': 'https://developer.spotify.com/documentation/web-api',
        'twitch': 'https://dev.twitch.tv/docs/api/',
    };
    const url = docsUrls[platform];
    if (url) {
        window.open(url, '_blank');
    } else {
        addAlgoLog('info', `No docs URL for ${platform}`);
    }
}

function testToken(platform) {
    addAlgoLog('info', `Token testing for ${platform} - configure in Settings`);
}

async function fetchFromGithub(name) {
    if (!name) name = currentAlgorithmName;
    if (!name) return;

    addAlgoLog('info', `Fetching ${name} from GitHub...`);

    try {
        const response = await fetch(`/api/algorithms/${encodeURIComponent(name)}/fetch/github`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.error) {
            addAlgoLog('error', `GitHub fetch failed: ${data.error}`);
        } else {
            addAlgoLog('success', `GitHub: ${data.message || 'Fetched successfully'}`);
            loadAlgorithmStats();
            if (currentAlgorithmName === name) {
                showAlgorithmDetail(name);
            }
        }
    } catch (error) {
        addAlgoLog('error', `GitHub error: ${error.message}`);
    }
}

async function fetchFromCDN(name) {
    if (!name) name = currentAlgorithmName;
    if (!name) return;

    addAlgoLog('info', `Fetching ${name} from CDN...`);

    try {
        const response = await fetch(`/api/algorithms/${encodeURIComponent(name)}/fetch/cdn`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.error) {
            addAlgoLog('error', `CDN fetch failed: ${data.error}`);
        } else {
            addAlgoLog('success', `CDN: ${data.message || 'Fetched successfully'}`);
            loadAlgorithmStats();
            if (currentAlgorithmName === name) {
                showAlgorithmDetail(name);
            }
        }
    } catch (error) {
        addAlgoLog('error', `CDN error: ${error.message}`);
    }
}

async function testAlgorithm(name) {
    if (!name) name = currentAlgorithmName;
    if (!name) return;

    addAlgoLog('info', `Testing ${name}...`);

    try {
        const response = await fetch(`/api/algorithms/${encodeURIComponent(name)}/test`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.error) {
            addAlgoLog('error', `Test failed: ${data.error}`);
        } else if (data.success) {
            addAlgoLog('success', `Test passed! Output: ${data.output || 'OK'}`);
        } else {
            addAlgoLog('warning', `Test inconclusive: ${data.message || 'Unknown result'}`);
        }
    } catch (error) {
        addAlgoLog('error', `Test error: ${error.message}`);
    }
}

async function refreshAllAlgorithms() {
    addAlgoLog('info', 'Refreshing all algorithms...');

    try {
        const response = await fetch('/api/algorithms/refresh', { method: 'POST' });
        const data = await response.json();

        if (data.error) {
            addAlgoLog('error', `Refresh failed: ${data.error}`);
        } else {
            addAlgoLog('success', `Refreshed ${data.updated || 0} algorithms`);
            loadAlgorithmStats();
        }
    } catch (error) {
        addAlgoLog('error', `Refresh error: ${error.message}`);
    }
}

function viewDocs(name) {
    const docsUrls = {
        'instagram_oauth': 'https://developers.facebook.com/docs/instagram-api/',
        'youtube_api': 'https://developers.google.com/youtube/v3',
        'twitter_api': 'https://developer.twitter.com/en/docs/twitter-api',
        'facebook_api': 'https://developers.facebook.com/docs/graph-api/',
        'spotify_api': 'https://developer.spotify.com/documentation/web-api',
        'twitch_api': 'https://dev.twitch.tv/docs/api/',
    };

    const url = docsUrls[name];
    if (url) {
        window.open(url, '_blank');
    } else {
        addAlgoLog('info', `No docs URL configured for ${name}`);
    }
}

function addAlgoLog(type, message) {
    const container = document.getElementById('algo-fetch-log');
    if (!container) return;

    const colors = {
        success: 'text-green-400',
        error: 'text-red-400',
        info: 'text-blue-400',
        warning: 'text-yellow-400',
    };

    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `${colors[type] || 'text-gray-400'}`;
    entry.innerHTML = `<span class="text-gray-500">${time}</span> ${message}`;

    // Remove placeholder if exists
    const placeholder = container.querySelector('.text-gray-500:only-child');
    if (placeholder && placeholder.textContent.includes('Waiting')) {
        placeholder.remove();
    }

    container.insertBefore(entry, container.firstChild);

    // Limit to 50 entries
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

function clearAlgoLogs() {
    const container = document.getElementById('algo-fetch-log');
    if (container) {
        container.innerHTML = '<div class="text-gray-500">No fetch operations yet...</div>';
    }
}

// Alias for HTML onclick
function clearFetchLog() {
    clearAlgoLogs();
}

// ============ ENGINE FUNCTIONS ============
let engineJobs = {};
let enginePollingInterval = null;

async function loadEngineStats() {
    try {
        const response = await fetch('/api/engine/stats');
        const stats = await response.json();
        document.getElementById('engine-total').textContent = stats.total || 0;
        document.getElementById('engine-successful').textContent = stats.successful || 0;
        document.getElementById('engine-failed').textContent = stats.failed || 0;
        document.getElementById('engine-running').textContent = stats.running || 0;
    } catch (error) {
        console.error('Failed to load engine stats:', error);
    }
}

async function loadEngineJobs() {
    try {
        const response = await fetch('/api/engine/jobs');
        const data = await response.json();
        engineJobs = {};
        (data.jobs || []).forEach(job => {
            engineJobs[job.job_id] = job;
        });
        renderEngineJobs();
    } catch (error) {
        console.error('Failed to load engine jobs:', error);
    }
}

function renderEngineJobs() {
    const container = document.getElementById('engine-jobs');
    if (!container) return;

    const jobs = Object.values(engineJobs);
    if (jobs.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-4">No jobs yet</div>';
        return;
    }

    container.innerHTML = jobs.map(job => {
        const statusColors = {
            running: 'text-yellow-400',
            completed: 'text-green-400',
            failed: 'text-red-400',
            cancelled: 'text-gray-400',
        };
        const color = statusColors[job.status] || 'text-gray-400';
        return `
            <div class="px-4 py-3 hover:bg-surface-light/50">
                <div class="flex justify-between items-center">
                    <span class="font-medium text-sm">${job.name || job.job_id}</span>
                    <span class="text-xs ${color}">${job.status}</span>
                </div>
                <div class="text-xs text-gray-500 mt-1">${job.url || '-'}</div>
                <div class="text-xs text-gray-500">
                    States: ${(job.states_visited || []).length} |
                    Captchas: ${job.captchas_solved || 0}
                </div>
            </div>
        `;
    }).join('');
}

function refreshEngineJobs() {
    loadEngineJobs();
    loadEngineStats();
}

async function quickTestEngine() {
    const url = document.getElementById('engine-test-url').value.trim();
    if (!url) {
        alert('Please enter a URL to test');
        return;
    }

    const resultDiv = document.getElementById('engine-test-result');
    resultDiv.classList.remove('hidden');
    document.getElementById('engine-test-title').textContent = 'Testing...';
    document.getElementById('engine-test-status').textContent = 'loading';
    document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-yellow-500/20 text-yellow-400';

    try {
        const response = await fetch('/api/engine/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                headless: document.getElementById('engine-headless')?.checked ?? true,
                screenshot: true,
            }),
        });
        const result = await response.json();

        if (result.success) {
            document.getElementById('engine-test-title').textContent = result.title || 'Page loaded';
            document.getElementById('engine-test-status').textContent = 'success';
            document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-green-500/20 text-green-400';
            document.getElementById('engine-test-url-display').textContent = result.url || url;
            document.getElementById('engine-test-text').textContent = result.text_preview || '-';

            if (result.screenshot) {
                addEngineLog('success', 'Screenshot saved: ' + result.screenshot);
            }
        } else {
            document.getElementById('engine-test-title').textContent = 'Test failed';
            document.getElementById('engine-test-status').textContent = 'error';
            document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-red-500/20 text-red-400';
            document.getElementById('engine-test-text').textContent = result.error || 'Unknown error';
        }
    } catch (error) {
        document.getElementById('engine-test-title').textContent = 'Request failed';
        document.getElementById('engine-test-status').textContent = 'error';
        document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-red-500/20 text-red-400';
        document.getElementById('engine-test-text').textContent = error.message;
    }
}

// ============ ENGINE DETECTION FUNCTIONS ============
let lastDetectionResult = null;

async function analyzeEngineUrl() {
    const url = document.getElementById('engine-test-url').value.trim();
    if (!url) {
        alert('Please enter a URL to analyze');
        return;
    }

    // Show loading state
    const resultDiv = document.getElementById('engine-test-result');
    const detectionPanel = document.getElementById('engine-detection-panel');
    resultDiv.classList.remove('hidden');
    detectionPanel.classList.add('hidden');
    document.getElementById('engine-test-title').textContent = 'Analyzing page...';
    document.getElementById('engine-test-status').textContent = 'analyzing';
    document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-yellow-500/20 text-yellow-400';

    try {
        const response = await fetch('/api/engine/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                headless: document.getElementById('engine-headless')?.checked ?? true,
                screenshot: true,
            }),
        });
        const result = await response.json();

        if (result.success) {
            // Show basic result
            document.getElementById('engine-test-title').textContent = result.title || 'Page loaded';
            document.getElementById('engine-test-status').textContent = 'success';
            document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-green-500/20 text-green-400';
            document.getElementById('engine-test-url-display').textContent = result.url || url;
            document.getElementById('engine-test-text').textContent = result.text_preview || '-';

            // Show detection results if available
            if (result.detection) {
                lastDetectionResult = result.detection;
                lastDetectionResult.url = result.url || url;
                renderDetectionResults(result.detection);
                detectionPanel.classList.remove('hidden');
                addEngineLog('info', `Detected page type: ${result.detection.page_type} (${Math.round(result.detection.confidence * 100)}%)`);
            }
        } else {
            document.getElementById('engine-test-title').textContent = 'Analysis failed';
            document.getElementById('engine-test-status').textContent = 'error';
            document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-red-500/20 text-red-400';
            document.getElementById('engine-test-text').textContent = result.error || 'Unknown error';
        }
    } catch (error) {
        document.getElementById('engine-test-title').textContent = 'Request failed';
        document.getElementById('engine-test-status').textContent = 'error';
        document.getElementById('engine-test-status').className = 'text-xs px-2 py-1 rounded bg-red-500/20 text-red-400';
        document.getElementById('engine-test-text').textContent = error.message;
    }
}

function renderDetectionResults(detection) {
    // Show page type
    const pageTypeEl = document.getElementById('engine-page-type');
    pageTypeEl.textContent = `${detection.page_type} (${Math.round(detection.confidence * 100)}%)`;

    // Render detected elements
    const elementsDiv = document.getElementById('engine-detected-elements');
    if (detection.detected_elements && detection.detected_elements.length > 0) {
        elementsDiv.innerHTML = detection.detected_elements.map(elem => `
            <span class="px-2 py-1 bg-surface rounded text-xs flex items-center gap-1" title="${elem.selector}">
                <span class="text-blue-400">${elem.type}</span>
                <span class="text-gray-500">${Math.round(elem.confidence * 100)}%</span>
            </span>
        `).join('');
    } else {
        elementsDiv.innerHTML = '<span class="text-gray-500 text-xs">No elements detected</span>';
    }

    // Render suggested keywords
    const keywordsDiv = document.getElementById('engine-suggested-keywords');
    if (detection.suggested_goal_keywords && detection.suggested_goal_keywords.length > 0) {
        keywordsDiv.innerHTML = detection.suggested_goal_keywords.map(kw => `
            <button onclick="addKeywordToGoal('${kw}')"
                class="px-2 py-1 bg-surface hover:bg-blue-500/20 rounded text-xs transition-colors">
                + ${kw}
            </button>
        `).join('');
    } else {
        keywordsDiv.innerHTML = '<span class="text-gray-500 text-xs">No keywords suggested</span>';
    }

    // Show captcha selectors if detected
    const captchaSuggestionsDiv = document.getElementById('engine-captcha-suggestions');
    const captchaDisplayDiv = document.getElementById('engine-captcha-display');
    if (detection.suggested_captcha_selectors) {
        captchaSuggestionsDiv.classList.remove('hidden');
        const cs = detection.suggested_captcha_selectors;
        captchaDisplayDiv.innerHTML = `
            <div class="flex justify-between"><span class="text-gray-500">Image:</span> <span class="text-green-400">${cs.image || 'not found'}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Input:</span> <span class="text-green-400">${cs.input || 'not found'}</span></div>
            <div class="flex justify-between"><span class="text-gray-500">Submit:</span> <span class="text-green-400">${cs.submit || 'not found'}</span></div>
        `;
    } else {
        captchaSuggestionsDiv.classList.add('hidden');
    }
}

function addKeywordToGoal(keyword) {
    const input = document.getElementById('engine-goal-keywords');
    const existing = input.value.trim();
    const keywords = existing.split(',').map(k => k.trim().toLowerCase());
    if (keywords.includes(keyword.toLowerCase())) {
        return;
    }
    input.value = existing ? `${existing}, ${keyword}` : keyword;
    addEngineLog('info', `Added keyword: ${keyword}`);
}

function applyDetectionResults() {
    if (!lastDetectionResult) {
        alert('No detection results to apply');
        return;
    }

    const detection = lastDetectionResult;

    // Apply suggested goal keywords
    if (detection.suggested_goal_keywords && detection.suggested_goal_keywords.length > 0) {
        const existing = document.getElementById('engine-goal-keywords').value.trim();
        const existingKeywords = existing ? existing.split(',').map(k => k.trim().toLowerCase()) : [];
        const newKeywords = detection.suggested_goal_keywords.filter(kw => !existingKeywords.includes(kw.toLowerCase()));
        if (newKeywords.length > 0) {
            document.getElementById('engine-goal-keywords').value = existing
                ? `${existing}, ${newKeywords.join(', ')}`
                : newKeywords.join(', ');
        }
    }

    // Apply captcha selectors
    if (detection.suggested_captcha_selectors) {
        const cs = detection.suggested_captcha_selectors;
        if (cs.image) document.getElementById('engine-captcha-image').value = cs.image;
        if (cs.input) document.getElementById('engine-captcha-input').value = cs.input;
        if (cs.submit) document.getElementById('engine-captcha-submit').value = cs.submit;
    }

    // Apply suggested actions
    if (detection.suggested_actions && detection.suggested_actions.length > 0) {
        document.getElementById('engine-actions').innerHTML = '';
        detection.suggested_actions.forEach(action => {
            addEngineActionFromDetection(action);
        });
    }

    addEngineLog('success', 'Applied detection suggestions');
}

function applyAndFillUrl() {
    applyDetectionResults();
    if (lastDetectionResult && lastDetectionResult.url) {
        document.getElementById('engine-url').value = lastDetectionResult.url;
        const name = lastDetectionResult.page_type.charAt(0).toUpperCase() + lastDetectionResult.page_type.slice(1) + ' Automation';
        document.getElementById('engine-name').value = name;
    }
    addEngineLog('success', 'Applied suggestions and filled URL');
}

function addEngineActionFromDetection(action) {
    const actionsDiv = document.getElementById('engine-actions');
    const actionId = Date.now() + Math.random();

    const actionHtml = `
        <div class="flex gap-2 items-center bg-surface-light rounded p-2" data-action-id="${actionId}">
            <select class="bg-surface border border-gray-600 rounded px-2 py-1 text-sm" onchange="updateEngineActionFields(this)">
                <option value="click" ${action.type === 'click' ? 'selected' : ''}>Click</option>
                <option value="fill" ${action.type === 'fill' ? 'selected' : ''}>Fill Input</option>
                <option value="wait" ${action.type === 'wait' ? 'selected' : ''}>Wait</option>
            </select>
            <input type="text" placeholder="Selector" value="${action.selectors ? action.selectors[0] : ''}"
                class="flex-1 bg-surface border border-gray-600 rounded px-2 py-1 text-sm action-selector">
            <input type="text" placeholder="Value" value="${action.value || ''}"
                class="w-32 bg-surface border border-gray-600 rounded px-2 py-1 text-sm action-value ${action.type !== 'fill' ? 'hidden' : ''}">
            <button onclick="removeEngineAction(this)" class="text-red-400 hover:text-red-300 px-2">X</button>
        </div>
    `;
    actionsDiv.insertAdjacentHTML('beforeend', actionHtml);
}

// ============ ENGINE PRESETS ============
let enginePresets = {};
let currentPresetCategory = 'all';

async function loadEnginePresets() {
    try {
        const response = await fetch('/api/engine/presets');
        const data = await response.json();
        enginePresets = data.presets || {};
        renderPresetGrid();
    } catch (error) {
        console.error('Failed to load presets:', error);
        document.getElementById('engine-presets-grid').innerHTML =
            '<div class="text-center text-red-400 py-4 col-span-4">Failed to load presets</div>';
    }
}

function renderPresetGrid() {
    const grid = document.getElementById('engine-presets-grid');
    const presetList = Object.values(enginePresets);

    // Filter by category
    const filtered = currentPresetCategory === 'all'
        ? presetList
        : presetList.filter(p => p.category === currentPresetCategory);

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="text-center text-gray-500 py-4 col-span-4">No presets in this category</div>';
        return;
    }

    grid.innerHTML = filtered.map(preset => {
        const iconColor = getCategoryColor(preset.category);
        return `
            <div onclick="loadPreset('${preset.id}')"
                class="bg-surface-light hover:bg-surface border border-gray-700 hover:border-blue-500/50 rounded-lg p-3 cursor-pointer transition-all group">
                <div class="flex items-center gap-2 mb-2">
                    <span class="w-8 h-8 rounded-lg ${iconColor} flex items-center justify-center">
                        ${getPresetIcon(preset.icon || preset.category)}
                    </span>
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-sm truncate">${preset.name}</div>
                        <div class="text-xs text-gray-500">${preset.category}</div>
                    </div>
                    ${!preset.builtin ? `
                        <button onclick="event.stopPropagation(); deletePreset('${preset.id}')"
                            class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 transition-opacity">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
                <div class="text-xs text-gray-400 line-clamp-2">${preset.description || 'No description'}</div>
                ${preset.url ? `<div class="text-xs text-blue-400 mt-1 truncate">${preset.url}</div>` : ''}
            </div>
        `;
    }).join('');
}

function getCategoryColor(category) {
    const colors = {
        login: 'bg-green-500/20 text-green-400',
        captcha: 'bg-yellow-500/20 text-yellow-400',
        form: 'bg-blue-500/20 text-blue-400',
        social: 'bg-purple-500/20 text-purple-400',
        custom: 'bg-gray-500/20 text-gray-400',
    };
    return colors[category] || colors.custom;
}

function getPresetIcon(icon) {
    const icons = {
        key: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>',
        'shield-check': '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>',
        mail: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>',
        'trending-up': '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
        music: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>',
        login: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/></svg>',
        captcha: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>',
        form: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>',
        social: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>',
        custom: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/></svg>',
    };
    return icons[icon] || icons.custom;
}

function filterPresets(category) {
    currentPresetCategory = category;

    // Update tab styles
    document.querySelectorAll('.preset-tab').forEach(tab => {
        if (tab.dataset.category === category) {
            tab.classList.add('bg-gray-700');
            tab.classList.remove('bg-gray-800');
        } else {
            tab.classList.remove('bg-gray-700');
            tab.classList.add('bg-gray-800');
        }
    });

    renderPresetGrid();
}

function loadPreset(presetId) {
    const preset = enginePresets[presetId];
    if (!preset) {
        addEngineLog('error', 'Preset not found: ' + presetId);
        return;
    }

    // Fill form fields
    if (preset.url) document.getElementById('engine-url').value = preset.url;
    document.getElementById('engine-name').value = preset.name || '';

    // Goal keywords
    if (preset.goal_keywords && preset.goal_keywords.length > 0) {
        document.getElementById('engine-goal-keywords').value = preset.goal_keywords.join(', ');
    }

    // Captcha selectors
    if (preset.captcha_selectors) {
        const cs = preset.captcha_selectors;
        if (cs.image) document.getElementById('engine-captcha-image').value = cs.image;
        if (cs.input) document.getElementById('engine-captcha-input').value = cs.input;
        if (cs.submit) document.getElementById('engine-captcha-submit').value = cs.submit;
    }

    // Settings
    if (preset.settings) {
        if ('headless' in preset.settings) {
            document.getElementById('engine-headless').checked = preset.settings.headless;
        }
        if ('solve_captcha' in preset.settings) {
            document.getElementById('engine-solve-captcha').checked = preset.settings.solve_captcha;
        }
        if ('max_iterations' in preset.settings) {
            document.getElementById('engine-max-iterations').value = preset.settings.max_iterations;
        }
    }

    // Actions
    if (preset.actions && preset.actions.length > 0) {
        document.getElementById('engine-actions').innerHTML = '';
        preset.actions.forEach(action => {
            addEngineActionFromDetection(action);
        });
    }

    addEngineLog('info', `Loaded preset: ${preset.name}`);
}

async function saveCurrentAsPreset() {
    const name = prompt('Enter preset name:');
    if (!name) return;

    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
    const description = prompt('Enter description (optional):', '') || '';
    const category = prompt('Enter category (login, captcha, form, social, custom):', 'custom') || 'custom';

    // Gather current form values
    const url = document.getElementById('engine-url').value.trim();
    const goalKeywordsStr = document.getElementById('engine-goal-keywords').value.trim();
    const goalKeywords = goalKeywordsStr ? goalKeywordsStr.split(',').map(s => s.trim()).filter(s => s) : [];

    const captchaSelectors = {};
    const captchaImage = document.getElementById('engine-captcha-image').value.trim();
    const captchaInput = document.getElementById('engine-captcha-input').value.trim();
    const captchaSubmit = document.getElementById('engine-captcha-submit').value.trim();
    if (captchaImage) captchaSelectors.image = captchaImage;
    if (captchaInput) captchaSelectors.input = captchaInput;
    if (captchaSubmit) captchaSelectors.submit = captchaSubmit;

    const settings = {
        headless: document.getElementById('engine-headless').checked,
        solve_captcha: document.getElementById('engine-solve-captcha').checked,
        max_iterations: parseInt(document.getElementById('engine-max-iterations').value) || 30,
    };

    const actions = getEngineActions();

    try {
        const response = await fetch('/api/engine/presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id,
                name,
                description,
                category,
                url,
                goal_keywords: goalKeywords,
                captcha_selectors: captchaSelectors,
                actions,
                settings,
            }),
        });

        const result = await response.json();
        if (result.status === 'saved') {
            addEngineLog('success', `Saved preset: ${name}`);
            await loadEnginePresets();
        } else {
            addEngineLog('error', 'Failed to save preset');
        }
    } catch (error) {
        addEngineLog('error', 'Failed to save preset: ' + error.message);
    }
}

async function deletePreset(presetId) {
    if (!confirm('Delete this preset?')) return;

    try {
        const response = await fetch(`/api/engine/presets/${presetId}`, {
            method: 'DELETE',
        });

        const result = await response.json();
        if (result.status === 'deleted') {
            addEngineLog('info', 'Deleted preset');
            await loadEnginePresets();
        } else {
            addEngineLog('error', result.detail || 'Failed to delete preset');
        }
    } catch (error) {
        addEngineLog('error', 'Failed to delete preset: ' + error.message);
    }
}

async function startEngineJob() {
    const url = document.getElementById('engine-url').value.trim();
    const name = document.getElementById('engine-name').value.trim() || 'Custom';
    const goalKeywordsStr = document.getElementById('engine-goal-keywords').value.trim();
    const headless = document.getElementById('engine-headless').checked;
    const solveCaptcha = document.getElementById('engine-solve-captcha').checked;
    const maxIterations = parseInt(document.getElementById('engine-max-iterations').value) || 30;

    if (!url) {
        alert('Please enter a target URL');
        return;
    }

    const goalKeywords = goalKeywordsStr ? goalKeywordsStr.split(',').map(s => s.trim()).filter(s => s) : [];

    const captchaSelectors = {};
    const captchaImage = document.getElementById('engine-captcha-image').value.trim();
    const captchaInput = document.getElementById('engine-captcha-input').value.trim();
    const captchaSubmit = document.getElementById('engine-captcha-submit').value.trim();
    if (captchaImage) captchaSelectors.image = captchaImage;
    if (captchaInput) captchaSelectors.input = captchaInput;
    if (captchaSubmit) captchaSelectors.submit = captchaSubmit;

    const actions = getEngineActions();

    addEngineLog('info', 'Starting automation for ' + name + '...');

    try {
        const response = await fetch('/api/engine/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                name,
                goal_keywords: goalKeywords,
                captcha_selectors: captchaSelectors,
                actions,
                headless,
                solve_captcha: solveCaptcha,
                max_iterations: maxIterations,
            }),
        });
        const result = await response.json();

        if (result.job_id) {
            addEngineLog('success', 'Job started: ' + result.job_id);
            startEnginePolling();
            loadEngineStats();
            loadEngineJobs();
        } else {
            addEngineLog('error', result.error || 'Failed to start job');
        }
    } catch (error) {
        addEngineLog('error', 'Request failed: ' + error.message);
    }
}

function startEnginePolling() {
    if (enginePollingInterval) return;
    enginePollingInterval = setInterval(() => {
        loadEngineJobs();
        loadEngineStats();
    }, 3000);
}

let engineActionCount = 0;

function addEngineAction() {
    const container = document.getElementById('engine-actions');
    const id = engineActionCount++;

    const div = document.createElement('div');
    div.className = 'flex gap-2 items-center bg-surface-light rounded p-2';
    div.id = 'engine-action-' + id;
    div.innerHTML = '<select class="bg-surface border border-gray-600 rounded px-2 py-1 text-sm" onchange="updateEngineActionFields(' + id + ')">' +
        '<option value="click">Click</option>' +
        '<option value="fill">Fill Input</option>' +
        '<option value="wait">Wait</option>' +
        '</select>' +
        '<input type="text" placeholder="Selector: button, #id, .class" class="flex-1 bg-surface border border-gray-600 rounded px-2 py-1 text-sm engine-action-selector">' +
        '<input type="text" placeholder="Value (for fill)" class="w-32 bg-surface border border-gray-600 rounded px-2 py-1 text-sm engine-action-value hidden">' +
        '<button onclick="removeEngineAction(' + id + ')" class="text-red-400 hover:text-red-300 px-2">X</button>';
    container.appendChild(div);
}

function updateEngineActionFields(id) {
    const div = document.getElementById('engine-action-' + id);
    if (!div) return;

    const select = div.querySelector('select');
    const selectorInput = div.querySelector('.engine-action-selector');
    const valueInput = div.querySelector('.engine-action-value');

    if (select.value === 'fill') {
        valueInput.classList.remove('hidden');
        selectorInput.placeholder = 'Selector: input#email';
    } else if (select.value === 'wait') {
        valueInput.classList.add('hidden');
        selectorInput.placeholder = 'Seconds to wait';
    } else {
        valueInput.classList.add('hidden');
        selectorInput.placeholder = 'Selector: button, #id, .class';
    }
}

function removeEngineAction(id) {
    const div = document.getElementById('engine-action-' + id);
    if (div) div.remove();
}

function getEngineActions() {
    const actions = [];
    document.querySelectorAll('#engine-actions > div').forEach(div => {
        const select = div.querySelector('select');
        const selectorInput = div.querySelector('.engine-action-selector');
        const valueInput = div.querySelector('.engine-action-value');

        if (!select || !selectorInput) return;

        const type = select.value;
        const selector = selectorInput.value.trim();

        if (type === 'wait') {
            const seconds = parseFloat(selector) || 2;
            actions.push({ type: 'wait', seconds, name: 'Wait ' + seconds + 's' });
        } else if (type === 'fill' && selector) {
            actions.push({
                type: 'fill',
                selectors: [selector],
                value: valueInput.value || '',
                name: 'Fill ' + selector,
            });
        } else if (type === 'click' && selector) {
            actions.push({
                type: 'click',
                selectors: [selector],
                name: 'Click ' + selector,
            });
        }
    });
    return actions;
}

function addEngineLog(type, message) {
    const container = document.getElementById('engine-logs');
    if (!container) return;

    const colors = {
        success: 'text-green-400',
        error: 'text-red-400',
        info: 'text-blue-400',
        warning: 'text-yellow-400',
    };

    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = colors[type] || 'text-gray-400';
    entry.innerHTML = '<span class="text-gray-500">' + time + '</span> ' + message;

    const placeholder = container.querySelector('.text-gray-500:only-child');
    if (placeholder && placeholder.textContent.includes('logs')) {
        placeholder.remove();
    }

    container.insertBefore(entry, container.firstChild);

    while (container.children.length > 100) {
        container.removeChild(container.lastChild);
    }
}

function clearEngineLogs() {
    const container = document.getElementById('engine-logs');
    if (container) {
        container.innerHTML = '<div class="text-gray-500">Engine logs will appear here...</div>';
    }
}

// ============================================================================
// FLOW RECORDING & EXECUTION
// ============================================================================

// Record Flow Modal
let currentIdentityPreview = null;  // Store current identity for use when starting

async function openRecordFlowModal() {
    const modal = document.getElementById('record-flow-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.getElementById('record-flow-name').value = '';
    document.getElementById('record-flow-url').value = '';
    document.getElementById('record-flow-description').value = '';

    // Hide error/stuck sections from previous attempts
    document.getElementById('recording-error-section')?.classList.add('hidden');
    document.getElementById('recording-stuck-section')?.classList.add('hidden');

    // Check if recording is stuck (is_recording=true but no browser window)
    try {
        const response = await fetch('/api/flows/record/status');
        const status = await response.json();
        if (status.is_recording) {
            document.getElementById('recording-stuck-section')?.classList.remove('hidden');
        }
    } catch (e) {}

    // Check if any stealth options are enabled and load identity preview
    updateIdentityPreviewVisibility();
}

function closeRecordFlowModal() {
    const modal = document.getElementById('record-flow-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    currentIdentityPreview = null;
}

async function forceResetRecording() {
    try {
        const response = await fetch('/api/flows/record/cancel', { method: 'POST' });
        if (response.ok) {
            document.getElementById('recording-stuck-section')?.classList.add('hidden');
            addEvent('success', 'Recording session reset');
        } else {
            addEvent('error', 'Failed to reset recording');
        }
    } catch (error) {
        addEvent('error', 'Failed to reset: ' + error.message);
    }
}

function updateIdentityPreviewVisibility() {
    const useProxy = document.getElementById('record-use-proxy')?.checked;
    const useFingerprint = document.getElementById('record-use-fingerprint')?.checked;
    const section = document.getElementById('identity-preview-section');

    if (useProxy || useFingerprint) {
        section?.classList.remove('hidden');
        refreshIdentityPreview();
    } else {
        section?.classList.add('hidden');
    }
}

async function refreshIdentityPreview() {
    const section = document.getElementById('identity-preview-section');
    if (!section || section.classList.contains('hidden')) return;

    try {
        const response = await fetch('/api/flows/record/preview-identity');
        const data = await response.json();
        currentIdentityPreview = data;

        // Update UI
        document.getElementById('identity-proxy').textContent = data.proxy || 'No proxy';
        document.getElementById('identity-browser').textContent = data.browser || 'Unknown';
        document.getElementById('identity-screen').textContent = data.screen || 'Unknown';
        document.getElementById('identity-locale').textContent = data.locale || 'Unknown';
        document.getElementById('identity-timezone').textContent = data.timezone || 'Unknown';
        document.getElementById('identity-proxy-count').textContent =
            data.proxy_available > 0 ? `${data.proxy_available} proxies available` : 'No proxies available';
    } catch (error) {
        document.getElementById('identity-proxy').textContent = 'Error loading';
    }
}

async function startRecording() {
    const name = document.getElementById('record-flow-name').value.trim();
    const url = document.getElementById('record-flow-url').value.trim();
    const description = document.getElementById('record-flow-description').value.trim();

    if (!name) {
        addEvent('error', 'Please enter a flow name');
        return;
    }
    if (!url) {
        addEvent('error', 'Please enter a start URL');
        return;
    }

    // Gather stealth options
    const stealth = {
        use_proxy: document.getElementById('record-use-proxy')?.checked || false,
        use_fingerprint: document.getElementById('record-use-fingerprint')?.checked || false,
        block_webrtc: document.getElementById('record-block-webrtc')?.checked || false,
        canvas_noise: document.getElementById('record-canvas-noise')?.checked || false
    };

    try {
        const response = await fetch('/api/flows/record/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, start_url: url, description, stealth })
        });

        const data = await response.json();
        if (response.ok) {
            // Hide error section if visible
            document.getElementById('recording-error-section')?.classList.add('hidden');

            closeRecordFlowModal();
            const stealthMode = stealth.use_proxy || stealth.use_fingerprint ? ' with stealth mode' : '';
            addEvent('success', `Recording started${stealthMode}! Browser window opening...`);

            // Show recording control panel and start polling
            currentRecordingFlowId = data.flow_id;
            currentRecordingFlowName = name;
            showRecordingControlPanel(name, stealth.use_proxy);
            startRecordingStatusPolling();
        } else {
            // Show error section with retry options
            showRecordingError(data.detail || 'Failed to start recording');
        }
    } catch (error) {
        showRecordingError('Error starting recording: ' + error.message);
    }
}

function showRecordingError(message) {
    const errorSection = document.getElementById('recording-error-section');
    const errorMessage = document.getElementById('recording-error-message');
    if (errorSection && errorMessage) {
        errorMessage.textContent = message;
        errorSection.classList.remove('hidden');
    }
    addEvent('error', message);
}

async function retryWithNewIdentity() {
    // Refresh identity and try again
    await refreshIdentityPreview();
    document.getElementById('recording-error-section')?.classList.add('hidden');
    startRecording();
}

function startRecordingNoProxy() {
    // Disable proxy and try again
    const proxyEl = document.getElementById('record-use-proxy');
    if (proxyEl) proxyEl.checked = false;
    updateIdentityPreviewVisibility();
    document.getElementById('recording-error-section')?.classList.add('hidden');
    startRecording();
}

// Recording control variables
let currentRecordingFlowId = null;
let currentRecordingFlowName = null;
let recordingPollingInterval = null;
let recordingStartTime = null;
let recordingDurationInterval = null;

function showRecordingControlPanel(flowName, useProxy) {
    const panel = document.getElementById('recording-control-panel');
    if (!panel) return;

    document.getElementById('recording-flow-name').textContent = flowName;
    document.getElementById('recording-proxy-status').textContent = useProxy ? 'Using proxy' : 'No proxy';
    document.getElementById('recording-duration').textContent = '00:00';
    document.getElementById('recording-actions-count').textContent = '0 actions';

    panel.classList.remove('hidden');

    // Start duration counter
    recordingStartTime = Date.now();
    recordingDurationInterval = setInterval(updateRecordingDuration, 1000);
}

function hideRecordingControlPanel() {
    const panel = document.getElementById('recording-control-panel');
    if (panel) panel.classList.add('hidden');

    if (recordingDurationInterval) {
        clearInterval(recordingDurationInterval);
        recordingDurationInterval = null;
    }
    if (recordingPollingInterval) {
        clearInterval(recordingPollingInterval);
        recordingPollingInterval = null;
    }
}

function updateRecordingDuration() {
    if (!recordingStartTime) return;
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const secs = (elapsed % 60).toString().padStart(2, '0');
    const el = document.getElementById('recording-duration');
    if (el) el.textContent = `${mins}:${secs}`;
}

function startRecordingStatusPolling() {
    recordingPollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/flows/record/status');
            const data = await response.json();

            if (!data.is_recording) {
                hideRecordingControlPanel();
                addEvent('info', 'Recording ended');
                loadFlows();
                return;
            }

            // Update actions count
            const actionsEl = document.getElementById('recording-actions-count');
            if (actionsEl && data.actions_recorded !== undefined) {
                actionsEl.textContent = `${data.actions_recorded} actions`;
            }

            // Update proxy status
            const proxyEl = document.getElementById('recording-proxy-status');
            if (proxyEl && data.proxy_used) {
                proxyEl.textContent = `Proxy: ${data.proxy_used}`;
            }
        } catch (error) {
            console.error('Failed to poll recording status:', error);
        }
    }, 1000);
}

async function stopRecording() {
    if (!currentRecordingFlowId) {
        addEvent('error', 'No active recording');
        return;
    }

    try {
        const response = await fetch(`/api/flows/record/${currentRecordingFlowId}/stop`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok) {
            hideRecordingControlPanel();
            addEvent('success', `Flow saved! ${data.actions_count || 0} actions recorded`);
            loadFlows();
        } else {
            addEvent('error', data.detail || 'Failed to stop recording');
        }
    } catch (error) {
        addEvent('error', 'Error stopping recording: ' + error.message);
    }

    currentRecordingFlowId = null;
    currentRecordingFlowName = null;
}

async function cancelRecording() {
    try {
        const response = await fetch('/api/flows/record/cancel', {
            method: 'POST'
        });

        if (response.ok) {
            hideRecordingControlPanel();
            addEvent('info', 'Recording cancelled');
        } else {
            const data = await response.json();
            addEvent('error', data.detail || 'Failed to cancel recording');
        }
    } catch (error) {
        addEvent('error', 'Error cancelling recording: ' + error.message);
    }

    currentRecordingFlowId = null;
    currentRecordingFlowName = null;
}

async function createCheckpoint() {
    if (!currentRecordingFlowId) {
        addEvent('error', 'No active recording');
        return;
    }

    const checkpointName = prompt('Checkpoint name (optional):') || `Checkpoint ${Date.now()}`;

    try {
        const response = await fetch(`/api/flows/record/${currentRecordingFlowId}/checkpoint`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: checkpointName })
        });

        if (response.ok) {
            addEvent('success', `Checkpoint created: ${checkpointName}`);
        } else {
            const data = await response.json();
            addEvent('error', data.detail || 'Failed to create checkpoint');
        }
    } catch (error) {
        addEvent('error', 'Error creating checkpoint: ' + error.message);
    }
}

async function changeRecordingProxy() {
    addEvent('warning', 'Proxy change requires restarting recording');
    // Could implement live proxy change if backend supports it
}

// Set stealth mode presets for recording
function setRecordStealth(level) {
    const proxyEl = document.getElementById('record-use-proxy');
    const fingerprintEl = document.getElementById('record-use-fingerprint');
    const webrtcEl = document.getElementById('record-block-webrtc');
    const canvasEl = document.getElementById('record-canvas-noise');

    switch (level) {
        case 'none':
            if (proxyEl) proxyEl.checked = false;
            if (fingerprintEl) fingerprintEl.checked = false;
            if (webrtcEl) webrtcEl.checked = false;
            if (canvasEl) canvasEl.checked = false;
            addEvent('warning', 'Stealth disabled - using your real identity');
            break;
        case 'basic':
            if (proxyEl) proxyEl.checked = false;
            if (fingerprintEl) fingerprintEl.checked = true;
            if (webrtcEl) webrtcEl.checked = true;
            if (canvasEl) canvasEl.checked = true;
            addEvent('success', 'Basic stealth - fingerprint + anti-leak protections');
            break;
        case 'full':
            if (proxyEl) proxyEl.checked = true;
            if (fingerprintEl) fingerprintEl.checked = true;
            if (webrtcEl) webrtcEl.checked = true;
            if (canvasEl) canvasEl.checked = true;
            addEvent('success', 'Full stealth - all protections enabled!');
            break;
    }

    // Update identity preview based on new settings
    updateIdentityPreviewVisibility();
}

// Flow Library Modal
function openFlowLibraryModal() {
    const modal = document.getElementById('flow-library-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    loadFlows();
}

function closeFlowLibraryModal() {
    const modal = document.getElementById('flow-library-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

async function loadFlows() {
    try {
        const response = await fetch('/api/flows');
        const data = await response.json();

        document.getElementById('flows-total').textContent = data.total;
        document.getElementById('flows-ready').textContent = data.ready;
        document.getElementById('flows-draft').textContent = data.draft;

        const container = document.getElementById('flow-list');

        if (data.flows.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <div class="text-gray-500 mb-2">No flows recorded yet</div>
                    <button onclick="closeFlowLibraryModal(); openRecordFlowModal();" class="text-purple-400 hover:text-purple-300">
                        Record your first flow →
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = data.flows.map(flow => `
            <div class="bg-surface-light rounded-lg p-4 hover:ring-1 hover:ring-purple-500/50 transition-all">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="font-medium">${escapeHtml(flow.name)}</span>
                            <span class="px-2 py-0.5 text-xs rounded-full ${
                                flow.status === 'ready' ? 'bg-green-500/20 text-green-400' :
                                flow.status === 'draft' ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-gray-500/20 text-gray-400'
                            }">${flow.status}</span>
                        </div>
                        <div class="text-sm text-gray-400 mb-2">${escapeHtml(flow.description || flow.start_url)}</div>
                        <div class="flex items-center gap-4 text-xs text-gray-500">
                            <span>📌 ${flow.checkpoint_count} checkpoints</span>
                            <span>🚀 ${flow.times_executed} runs</span>
                            <span>✅ ${(flow.success_rate * 100).toFixed(0)}% success</span>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        ${flow.status === 'ready' ? `
                            <button onclick="openExecuteFlowModal('${flow.id}', '${escapeHtml(flow.name)}')" class="p-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30" title="Execute">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>
                            </button>
                        ` : `
                            <button onclick="finalizeFlow('${flow.id}')" class="p-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30" title="Finalize">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                            </button>
                        `}
                        <button onclick="deleteFlow('${flow.id}')" class="p-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30" title="Delete">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load flows:', error);
        document.getElementById('flow-list').innerHTML = `
            <div class="text-red-400 text-center py-4">Error loading flows</div>
        `;
    }
}

async function deleteFlow(flowId) {
    if (!confirm('Are you sure you want to delete this flow?')) return;

    try {
        const response = await fetch(`/api/flows/${flowId}`, { method: 'DELETE' });
        if (response.ok) {
            addEvent('success', 'Flow deleted');
            loadFlows();
        } else {
            const data = await response.json();
            addEvent('error', data.detail || 'Failed to delete flow');
        }
    } catch (error) {
        addEvent('error', 'Error deleting flow: ' + error.message);
    }
}

async function finalizeFlow(flowId) {
    try {
        const response = await fetch(`/api/flows/${flowId}/finalize`, { method: 'POST' });
        if (response.ok) {
            addEvent('success', 'Flow finalized and ready for execution');
            loadFlows();
        } else {
            const data = await response.json();
            addEvent('error', data.detail || 'Failed to finalize flow');
        }
    } catch (error) {
        addEvent('error', 'Error finalizing flow: ' + error.message);
    }
}

// Execute Flow Modal
function openExecuteFlowModal(flowId, flowName) {
    document.getElementById('execute-flow-id').value = flowId;
    document.getElementById('execute-flow-name').textContent = flowName;

    const modal = document.getElementById('execute-flow-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeExecuteFlowModal() {
    const modal = document.getElementById('execute-flow-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

async function executeFlow() {
    const flowId = document.getElementById('execute-flow-id').value;
    const browser = document.getElementById('execute-flow-browser').value;
    const variation = document.getElementById('execute-flow-variation').value;
    const workers = parseInt(document.getElementById('execute-flow-workers').value);
    const timeout = parseInt(document.getElementById('execute-flow-timeout').value);
    const useProxy = document.getElementById('execute-flow-proxy').checked;

    try {
        const response = await fetch(`/api/flows/${flowId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                browser_engine: browser,
                variation_level: variation,
                workers: workers,
                checkpoint_timeout: timeout,
                use_proxy: useProxy
            })
        });

        const data = await response.json();
        if (response.ok) {
            closeExecuteFlowModal();
            closeFlowLibraryModal();
            addEvent('success', `Flow execution started with ${workers} worker(s)`);
        } else {
            addEvent('error', data.detail || 'Failed to execute flow');
        }
    } catch (error) {
        addEvent('error', 'Error executing flow: ' + error.message);
    }
}

// Helper for HTML escaping
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ LLM PAGE ============

// Model lists - Ollama only (text + vision)
const LLM_MODELS = {
    text: [
        { value: 'llama3.2', label: 'Llama 3.2 (Recommended)' },
        { value: 'llama3', label: 'Llama 3' },
        { value: 'llama3:70b', label: 'Llama 3 70B' },
        { value: 'mistral', label: 'Mistral' },
        { value: 'mixtral', label: 'Mixtral 8x7B' },
        { value: 'codellama', label: 'Code Llama' },
        { value: 'qwen2.5', label: 'Qwen 2.5' },
    ],
    vision: [
        { value: 'llama3.2-vision', label: 'Llama 3.2 Vision (Recommended)' },
        { value: 'llava', label: 'LLaVA (~4GB)' },
        { value: 'llava:13b', label: 'LLaVA 13B (~8GB)' },
        { value: 'llava:34b', label: 'LLaVA 34B (~20GB)' },
        { value: 'bakllava', label: 'BakLLaVA' },
    ],
};

// Current task state
let currentLLMTask = null;
let pendingAction = null;

function updateLLMModels() {
    const visionEl = document.getElementById('llm-page-vision');
    const modelSelect = document.getElementById('llm-model');
    if (!visionEl || !modelSelect) return;

    const vision = visionEl.value;
    const useVision = vision === 'always' || vision === 'auto';
    const models = useVision ? LLM_MODELS.vision : LLM_MODELS.text;

    modelSelect.innerHTML = models.map(m =>
        `<option value="${m.value}">${m.label}</option>`
    ).join('');
}

async function startLLMTask() {
    let url = document.getElementById('llm-url').value.trim();
    const goal = document.getElementById('llm-goal').value.trim();
    const provider = document.getElementById('llm-provider').value;
    const mode = document.getElementById('llm-mode').value;
    const vision = document.getElementById('llm-page-vision').value;

    if (!url) {
        addEvent('error', 'Please enter a URL');
        return;
    }

    // Check if Ollama is available first
    if (!ollamaAvailable) {
        const analysisContent = document.getElementById('llm-analysis-content');
        if (analysisContent) {
            analysisContent.innerHTML = `
                <div class="text-red-400">
                    <strong>Cannot Start - Ollama Not Running</strong>
                    <p class="mt-2 text-gray-300">Please install and start Ollama first.</p>
                    <p class="mt-2 text-sm text-gray-400">
                        Install: <code class="bg-black/30 px-1 rounded">curl -fsSL https://ollama.com/install.sh | sh</code><br>
                        Start: <code class="bg-black/30 px-1 rounded">ollama serve</code><br>
                        Get model: <code class="bg-black/30 px-1 rounded">ollama pull llama3.2-vision</code>
                    </p>
                </div>`;
        }
        addEvent('error', 'Ollama not running - cannot start AI task');
        return;
    }

    // Auto-add https:// if missing
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
    }

    // Show live indicator
    document.getElementById('live-indicator').classList.remove('bg-gray-500');
    document.getElementById('live-indicator').classList.add('bg-green-500', 'animate-pulse');

    const payload = {
        url: url,
        llm_mode: mode,
        llm_task: goal || null,
        vision_mode: vision,
        mode: 'debug',
        workers: 1,
        config: {
            llm_provider: provider,
        }
    };

    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const task = await response.json();
            currentLLMTask = task.task_id;
            addEvent('success', 'AI task started');
            addLLMTimelineEntry('navigate', url, 'Navigating to URL');
        } else {
            const error = await response.json();
            // Parse validation errors
            let errorMsg = 'Failed to start task';
            if (error.detail) {
                if (Array.isArray(error.detail)) {
                    errorMsg = error.detail.map(e => e.msg || e).join(', ');
                } else {
                    errorMsg = error.detail;
                }
            }
            // Show in Analysis panel
            const analysisContent = document.getElementById('llm-analysis-content');
            if (analysisContent) {
                analysisContent.innerHTML = `<div class="text-red-400"><strong>Error:</strong> ${errorMsg}</div>`;
            }
            // Reset indicator
            document.getElementById('live-indicator').classList.remove('bg-green-500', 'animate-pulse');
            document.getElementById('live-indicator').classList.add('bg-red-500');
            addEvent('error', errorMsg);
        }
    } catch (err) {
        const analysisContent = document.getElementById('llm-analysis-content');
        if (analysisContent) {
            analysisContent.innerHTML = `<div class="text-red-400"><strong>Error:</strong> ${err.message || 'Network error'}</div>`;
        }
        document.getElementById('live-indicator').classList.remove('bg-green-500', 'animate-pulse');
        document.getElementById('live-indicator').classList.add('bg-red-500');
        addEvent('error', 'Network error');
        console.error(err);
    }
}

function addLLMTimelineEntry(action, target, description) {
    const timeline = document.getElementById('action-timeline');
    if (!timeline) return;

    const isEmpty = timeline.querySelector('.text-gray-500');
    if (isEmpty) isEmpty.remove();

    const icons = {
        navigate: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3"/>',
        click: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/>',
        type: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
        scroll: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>',
        wait: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>',
        extract: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>',
    };

    const entry = document.createElement('div');
    entry.className = 'flex items-start gap-2 p-2 rounded-lg bg-surface-light/50 animate-fade-in';
    entry.innerHTML = `
        <div class="w-6 h-6 bg-violet-500/20 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg class="w-3 h-3 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                ${icons[action] || icons.click}
            </svg>
        </div>
        <div class="flex-1 min-w-0">
            <div class="text-xs font-medium text-violet-300 capitalize">${action}</div>
            <div class="text-xs text-gray-400 truncate" title="${target}">${target}</div>
        </div>
        <span class="text-xs text-gray-600">${new Date().toLocaleTimeString()}</span>
    `;

    timeline.insertBefore(entry, timeline.firstChild);
}

function updateLLMElements(elements) {
    const container = document.getElementById('elements-list');
    const countEl = document.getElementById('elements-count');
    if (!container || !countEl) return;

    if (!elements || elements.length === 0) {
        container.innerHTML = '<div class="text-sm text-gray-500 text-center py-4">No elements detected</div>';
        countEl.textContent = '0';
        return;
    }

    countEl.textContent = elements.length;

    container.innerHTML = elements.slice(0, 50).map((el, i) => `
        <div class="flex items-center gap-2 p-2 rounded hover:bg-surface-light cursor-pointer" onclick="highlightElement(${i})">
            <span class="text-xs px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400">${el.tag || 'div'}</span>
            <span class="text-xs text-gray-300 truncate flex-1">${el.text || el.selector || 'unnamed'}</span>
            <span class="text-xs text-gray-500">${(el.confidence * 100).toFixed(0)}%</span>
        </div>
    `).join('');
}

function updateLLMScreenshot(base64Data) {
    const img = document.getElementById('live-screenshot');
    const placeholder = document.getElementById('screenshot-placeholder');
    if (!img) return;

    img.src = `data:image/png;base64,${base64Data}`;
    img.classList.remove('hidden');
    if (placeholder) placeholder.classList.add('hidden');
}

function updateLLMAnalysis(analysis) {
    const content = document.getElementById('llm-analysis-content');
    const confidence = document.getElementById('llm-confidence');
    if (!content) return;

    content.innerHTML = `<p class="text-sm text-gray-300">${analysis.text || analysis}</p>`;

    if (confidence && analysis.confidence !== undefined) {
        const conf = (analysis.confidence * 100).toFixed(0);
        confidence.textContent = `${conf}% confident`;
        confidence.className = `text-xs px-2 py-1 rounded-full ${
            conf >= 80 ? 'bg-green-500/20 text-green-400' :
            conf >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
        }`;
    }
}

function showSuggestedAction(action) {
    const panel = document.getElementById('llm-action-panel');
    if (!panel) return;

    document.getElementById('action-type').textContent = action.type || 'Action';
    document.getElementById('action-target').textContent = action.selector || action.target || '--';
    document.getElementById('action-reason').textContent = action.reason || '';
    panel.classList.remove('hidden');
    pendingAction = action;
}

function approveAction() {
    if (!pendingAction || !currentLLMTask) return;

    if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        window.ws.send(JSON.stringify({
            type: 'llm_action_approved',
            task_id: currentLLMTask,
            action: pendingAction
        }));
    }

    addLLMTimelineEntry(pendingAction.type || 'action', pendingAction.selector || pendingAction.target || '--', 'Approved');
    document.getElementById('llm-action-panel').classList.add('hidden');
    pendingAction = null;
}

function rejectAction() {
    if (!pendingAction || !currentLLMTask) return;

    if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        window.ws.send(JSON.stringify({
            type: 'llm_action_rejected',
            task_id: currentLLMTask,
            action: pendingAction
        }));
    }

    document.getElementById('llm-action-panel').classList.add('hidden');
    pendingAction = null;
}

function clearLLMTimeline() {
    const timeline = document.getElementById('action-timeline');
    if (timeline) {
        timeline.innerHTML = '<div class="text-sm text-gray-500 text-center py-4">No actions yet</div>';
    }
}

function highlightElement(index) {
    console.log('Highlight element', index);
}

function refreshLLMScreenshot() {
    if (!currentLLMTask) return;
    fetch(`/api/llm/screenshot/${currentLLMTask}`)
        .then(r => r.json())
        .then(data => {
            if (data.screenshot) {
                updateLLMScreenshot(data.screenshot);
            }
        })
        .catch(console.error);
}

function toggleLLMFullscreen() {
    const wrapper = document.getElementById('screenshot-wrapper');
    if (!wrapper) return;

    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        wrapper.requestFullscreen();
    }
}

// Handle WebSocket events for LLM page
function handleLLMWebSocketEvent(data) {
    switch (data.type) {
        case 'screenshot_captured':
        case 'visual.screenshot_live':
            if (data.task_id === currentLLMTask && data.data?.screenshot) {
                updateLLMScreenshot(data.data.screenshot);
            }
            break;

        case 'llm_analysis_ready':
        case 'llm.analysis_ready':
            if (data.task_id === currentLLMTask) {
                updateLLMAnalysis(data.data || data);
                if (data.next_action) {
                    showSuggestedAction(data.next_action);
                }
            }
            break;

        case 'dom_extracted':
        case 'dom.extracted':
            if (data.task_id === currentLLMTask) {
                updateLLMElements(data.elements || []);
            }
            break;

        case 'llm_navigated':
            if (data.task_id === currentLLMTask) {
                const urlEl = document.getElementById('current-url');
                if (urlEl) urlEl.textContent = data.url;
            }
            break;

        case 'llm.action_executing':
            if (data.task_id === currentLLMTask && data.action) {
                addLLMTimelineEntry(data.action.type, data.action.selector || '', 'Executing');
            }
            break;

        case 'llm_task_complete':
        case 'llm.task_complete':
            if (data.task_id === currentLLMTask) {
                const indicator = document.getElementById('live-indicator');
                if (indicator) indicator.classList.remove('animate-pulse');
                if (data.success) {
                    addEvent('success', 'AI task completed successfully');
                } else {
                    addEvent('error', 'AI task failed');
                }
            }
            break;

        case 'task_failed':
            if (data.task_id === currentLLMTask) {
                const indicator = document.getElementById('live-indicator');
                if (indicator) {
                    indicator.classList.remove('bg-green-500', 'animate-pulse');
                    indicator.classList.add('bg-red-500');
                }
                // Convert technical error to user-friendly message
                const errorInfo = formatLLMError(data.error);

                // Show error in AI Analysis panel for visibility
                const analysisContent = document.getElementById('llm-analysis-content');
                if (analysisContent) {
                    analysisContent.innerHTML = `
                        <div class="text-red-400">
                            <strong>${errorInfo.title}</strong>
                            <p class="mt-2 text-gray-300">${errorInfo.message}</p>
                            ${errorInfo.fix ? `<p class="mt-2 text-yellow-400"><strong>How to fix:</strong> ${errorInfo.fix}</p>` : ''}
                        </div>`;
                }
                addEvent('error', errorInfo.title);
                addLLMTimelineEntry('error', errorInfo.title, 'Failed');
            }
            break;
    }
}

// Format technical errors to user-friendly messages
function formatLLMError(error) {
    if (!error) {
        return { title: 'Unknown Error', message: 'Something went wrong.', fix: null };
    }

    const errorStr = error.toLowerCase();

    // Ollama not running
    if (errorStr.includes('ollama') || errorStr.includes('connection refused') && errorStr.includes('11434')) {
        return {
            title: 'Ollama Not Running',
            message: 'The AI requires Ollama to be installed and running on your computer.',
            fix: 'Run: curl -fsSL https://ollama.com/install.sh | sh && ollama serve && ollama pull llama3.2-vision'
        };
    }

    // Network/connection errors
    if (errorStr.includes('err_connection_reset') || errorStr.includes('err_connection_refused')) {
        return {
            title: 'Connection Failed',
            message: 'Could not connect to the website. The site may be blocking automated access or your network/proxy is having issues.',
            fix: 'Try a different URL, check your internet connection, or try with a proxy enabled.'
        };
    }

    if (errorStr.includes('err_empty_response')) {
        return {
            title: 'No Response from Website',
            message: 'The website did not respond. It may be down, blocking your IP, or the URL is incorrect.',
            fix: 'Verify the URL is correct and try enabling proxy rotation.'
        };
    }

    if (errorStr.includes('timeout') || errorStr.includes('timed out')) {
        return {
            title: 'Request Timed Out',
            message: 'The operation took too long. The website may be slow or unresponsive.',
            fix: 'Try again or check if the website is accessible in a normal browser.'
        };
    }

    // LLM model errors
    if (errorStr.includes('model') && (errorStr.includes('not found') || errorStr.includes('does not exist'))) {
        return {
            title: 'AI Model Not Found',
            message: 'The required AI model is not installed.',
            fix: 'Run: ollama pull llama3.2-vision'
        };
    }

    // Browser errors
    if (errorStr.includes('browser') || errorStr.includes('playwright') || errorStr.includes('chromium')) {
        return {
            title: 'Browser Error',
            message: 'Failed to start or control the browser.',
            fix: 'Try restarting the server or run: playwright install chromium'
        };
    }

    // Default - show original error but make it cleaner
    return {
        title: 'Task Failed',
        message: error,
        fix: null
    };
}

// Register LLM handler
window.llmEventHandler = handleLLMWebSocketEvent;

// Track Ollama availability
let ollamaAvailable = false;

async function checkLLMProviderHealth() {
    try {
        const response = await fetch('/api/llm/health');
        const health = await response.json();

        const ollamaStatus = health.providers?.ollama;
        ollamaAvailable = ollamaStatus?.available || false;

        // Only show warning on AI Control page (check if llm-page-vision exists)
        const isLLMPage = document.getElementById('llm-page-vision') !== null;
        if (!ollamaAvailable && isLLMPage) {
            // Show warning in the AI Analysis panel instead of global banner
            const analysisContent = document.getElementById('llm-analysis-content');
            if (analysisContent) {
                analysisContent.innerHTML = `
                    <div class="text-yellow-400">
                        <strong>Ollama Not Running</strong>
                        <p class="mt-2 text-gray-300">AI features require Ollama to be installed and running.</p>
                        <p class="mt-2 text-sm text-gray-400">
                            Install: <code class="bg-black/30 px-1 rounded">curl -fsSL https://ollama.com/install.sh | sh</code><br>
                            Start: <code class="bg-black/30 px-1 rounded">ollama serve</code><br>
                            Get model: <code class="bg-black/30 px-1 rounded">ollama pull llama3.2-vision</code>
                        </p>
                    </div>`;
            }
        }
    } catch (err) {
        ollamaAvailable = false;
        console.error('Failed to check provider health:', err);
    }
}

// Initialize LLM page when it becomes visible
function initLLMPage() {
    const visionEl = document.getElementById('llm-page-vision');
    if (visionEl) {
        visionEl.addEventListener('change', updateLLMModels);
        updateLLMModels();
        checkLLMProviderHealth();
    }
}

// Call init after pages are loaded
setTimeout(initLLMPage, 1000);

// ============================================================
// DOCUMENTATION PAGE
// ============================================================

let currentDocSlug = 'index';
let docsCache = [];

// Load docs list
async function loadDocsList() {
    try {
        const response = await fetch('/api/docs');
        const data = await response.json();

        if (data.success && data.docs) {
            docsCache = data.docs;
            renderDocsList(data.docs);
            // Load index by default
            loadDoc('index');
        }
    } catch (err) {
        console.error('Failed to load docs list:', err);
        const nav = document.getElementById('docs-nav');
        if (nav) {
            nav.innerHTML = '<div class="text-center text-red-400 py-4 text-sm">Failed to load docs</div>';
        }
    }
}

// Render docs navigation list
function renderDocsList(docs) {
    const nav = document.getElementById('docs-nav');
    if (!nav) return;

    // Order: index first, then alphabetically
    const ordered = [...docs].sort((a, b) => {
        if (a.slug === 'index') return -1;
        if (b.slug === 'index') return 1;
        return a.title.localeCompare(b.title);
    });

    nav.innerHTML = ordered.map(doc => `
        <button onclick="loadDoc('${doc.slug}')"
            class="doc-nav-item w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-surface-light transition-colors ${doc.slug === currentDocSlug ? 'bg-emerald-500/20 text-emerald-400' : 'text-gray-300'}"
            data-slug="${doc.slug}">
            ${doc.title}
        </button>
    `).join('');
}

// Filter docs by search
function filterDocs() {
    const search = document.getElementById('docs-search')?.value.toLowerCase() || '';
    const filtered = docsCache.filter(doc =>
        doc.title.toLowerCase().includes(search) ||
        doc.slug.toLowerCase().includes(search)
    );
    renderDocsList(filtered);
}

// Load a specific doc
async function loadDoc(slug) {
    currentDocSlug = slug;

    // Update nav highlighting
    document.querySelectorAll('.doc-nav-item').forEach(el => {
        if (el.dataset.slug === slug) {
            el.classList.add('bg-emerald-500/20', 'text-emerald-400');
            el.classList.remove('text-gray-300');
        } else {
            el.classList.remove('bg-emerald-500/20', 'text-emerald-400');
            el.classList.add('text-gray-300');
        }
    });

    const contentEl = document.getElementById('docs-content');
    const titleEl = document.getElementById('docs-current-title');

    if (!contentEl) return;

    // Show loading
    contentEl.innerHTML = '<div class="text-center text-gray-500 py-12"><div class="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4"></div>Loading...</div>';

    try {
        const response = await fetch(`/api/docs/${slug}`);
        const data = await response.json();

        if (data.success && data.content) {
            // Update title
            if (titleEl) {
                titleEl.textContent = data.title;
            }

            // Configure marked
            if (typeof marked !== 'undefined') {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    highlight: function(code, lang) {
                        if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                            try {
                                return hljs.highlight(code, { language: lang }).value;
                            } catch (err) {}
                        }
                        return code;
                    }
                });

                contentEl.innerHTML = marked.parse(data.content);

                // Apply syntax highlighting to code blocks
                if (typeof hljs !== 'undefined') {
                    contentEl.querySelectorAll('pre code').forEach(block => {
                        hljs.highlightElement(block);
                    });
                }
            } else {
                // Fallback: render as preformatted text
                contentEl.innerHTML = `<pre style="white-space: pre-wrap;">${data.content}</pre>`;
            }
        } else {
            contentEl.innerHTML = '<div class="text-center text-red-400 py-12">Document not found</div>';
        }
    } catch (err) {
        console.error('Failed to load doc:', err);
        contentEl.innerHTML = '<div class="text-center text-red-400 py-12">Failed to load document</div>';
    }
}

// Refresh current doc
function refreshCurrentDoc() {
    loadDoc(currentDocSlug);
}

// Open docs on GitHub
function openDocsOnGithub() {
    // This would link to your GitHub repo's docs folder
    window.open('https://github.com/devbyteai/ghoststorm/tree/main/docs', '_blank');
}

// Initialize docs page when it becomes visible
function initDocsPage() {
    const docsNav = document.getElementById('docs-nav');
    if (docsNav && docsNav.innerHTML.includes('Loading docs')) {
        loadDocsList();
    }
}

// Call init after pages are loaded
setTimeout(initDocsPage, 1000);
