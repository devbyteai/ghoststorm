"""Flow recorder with Patchright CDP integration and floating toolbar."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

import structlog

from ghoststorm.core.flow.storage import FlowStorage, get_flow_storage
from ghoststorm.core.models.flow import (
    Checkpoint,
    CheckpointType,
    FlowStatus,
    RecordedFlow,
    TimingConfig,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


class StealthConfig(TypedDict, total=False):
    """Stealth configuration for recording."""

    use_proxy: bool
    use_fingerprint: bool
    block_webrtc: bool
    canvas_noise: bool


# Floating toolbar HTML/CSS/JS to inject into the browser
RECORDING_TOOLBAR_HTML = """
<div id="ghoststorm-recording-toolbar" style="
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 2147483647;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 2px solid #e94560;
    border-radius: 12px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    box-shadow: 0 8px 32px rgba(233, 69, 96, 0.3);
    cursor: move;
    user-select: none;
">
    <!-- Recording indicator -->
    <div id="gs-record-indicator" style="
        width: 14px;
        height: 14px;
        background: #e94560;
        border-radius: 50%;
        animation: gs-pulse 1.5s ease-in-out infinite;
    "></div>

    <!-- Status text -->
    <span id="gs-status-text" style="
        color: #fff;
        font-size: 13px;
        font-weight: 500;
        min-width: 80px;
    ">Recording...</span>

    <!-- Checkpoint count -->
    <span id="gs-checkpoint-count" style="
        color: #0f3460;
        background: #e94560;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    ">0</span>

    <!-- Buttons -->
    <div style="display: flex; gap: 8px; margin-left: 8px;">
        <!-- Mark Checkpoint -->
        <button id="gs-btn-checkpoint" title="Mark Checkpoint" style="
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 8px;
            background: #0f3460;
            color: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        " onmouseover="this.style.background='#e94560'" onmouseout="this.style.background='#0f3460'">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
            </svg>
        </button>

        <!-- Pause/Resume -->
        <button id="gs-btn-pause" title="Pause Recording" style="
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 8px;
            background: #0f3460;
            color: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        " onmouseover="this.style.background='#e94560'" onmouseout="this.style.background='#0f3460'">
            <svg id="gs-pause-icon" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
            </svg>
        </button>

        <!-- Stop & Save -->
        <button id="gs-btn-stop" title="Stop & Save" style="
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 8px;
            background: #e94560;
            color: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        " onmouseover="this.style.background='#c73e54'" onmouseout="this.style.background='#e94560'">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="1"></rect>
            </svg>
        </button>
    </div>
</div>

<!-- Checkpoint Modal -->
<div id="gs-checkpoint-modal" style="
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 2147483648;
    justify-content: center;
    align-items: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
">
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #e94560;
        border-radius: 16px;
        padding: 24px;
        width: 400px;
        max-width: 90vw;
    ">
        <h3 style="color: #fff; margin: 0 0 20px 0; font-size: 18px;">
            📌 Mark Checkpoint
        </h3>

        <!-- Goal Description -->
        <div style="margin-bottom: 16px;">
            <label style="color: #a0a0a0; font-size: 12px; display: block; margin-bottom: 6px;">
                Goal Description *
            </label>
            <input id="gs-input-goal" type="text" placeholder="e.g., Click the login button" style="
                width: 100%;
                padding: 12px;
                border: 1px solid #0f3460;
                border-radius: 8px;
                background: #0a0a1a;
                color: #fff;
                font-size: 14px;
                box-sizing: border-box;
            ">
        </div>

        <!-- Checkpoint Type -->
        <div style="margin-bottom: 16px;">
            <label style="color: #a0a0a0; font-size: 12px; display: block; margin-bottom: 6px;">
                Checkpoint Type
            </label>
            <select id="gs-input-type" style="
                width: 100%;
                padding: 12px;
                border: 1px solid #0f3460;
                border-radius: 8px;
                background: #0a0a1a;
                color: #fff;
                font-size: 14px;
                box-sizing: border-box;
            ">
                <option value="navigation">🧭 Navigation</option>
                <option value="click">👆 Click</option>
                <option value="input">⌨️ Input</option>
                <option value="wait">⏳ Wait</option>
                <option value="scroll">📜 Scroll</option>
                <option value="external">🔗 External</option>
                <option value="custom" selected>✨ Custom</option>
            </select>
        </div>

        <!-- Element Description -->
        <div style="margin-bottom: 16px;">
            <label style="color: #a0a0a0; font-size: 12px; display: block; margin-bottom: 6px;">
                Element Description (optional)
            </label>
            <input id="gs-input-element" type="text" placeholder="e.g., the blue submit button" style="
                width: 100%;
                padding: 12px;
                border: 1px solid #0f3460;
                border-radius: 8px;
                background: #0a0a1a;
                color: #fff;
                font-size: 14px;
                box-sizing: border-box;
            ">
        </div>

        <!-- Timing -->
        <div style="display: flex; gap: 12px; margin-bottom: 20px;">
            <div style="flex: 1;">
                <label style="color: #a0a0a0; font-size: 12px; display: block; margin-bottom: 6px;">
                    Min Delay (s)
                </label>
                <input id="gs-input-min-delay" type="number" value="0.5" min="0" step="0.1" style="
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #0f3460;
                    border-radius: 8px;
                    background: #0a0a1a;
                    color: #fff;
                    font-size: 14px;
                    box-sizing: border-box;
                ">
            </div>
            <div style="flex: 1;">
                <label style="color: #a0a0a0; font-size: 12px; display: block; margin-bottom: 6px;">
                    Max Delay (s)
                </label>
                <input id="gs-input-max-delay" type="number" value="3" min="0" step="0.1" style="
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #0f3460;
                    border-radius: 8px;
                    background: #0a0a1a;
                    color: #fff;
                    font-size: 14px;
                    box-sizing: border-box;
                ">
            </div>
        </div>

        <!-- Buttons -->
        <div style="display: flex; gap: 12px; justify-content: flex-end;">
            <button id="gs-btn-cancel" style="
                padding: 12px 24px;
                border: 1px solid #0f3460;
                border-radius: 8px;
                background: transparent;
                color: #fff;
                cursor: pointer;
                font-size: 14px;
            ">Cancel</button>
            <button id="gs-btn-save-checkpoint" style="
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                background: #e94560;
                color: #fff;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
            ">Save Checkpoint</button>
        </div>
    </div>
</div>

<style>
@keyframes gs-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(1.1); }
}
</style>
"""

RECORDING_TOOLBAR_SCRIPT = """
(() => {
    // State
    let isPaused = false;
    let checkpointCount = 0;

    // Elements
    const toolbar = document.getElementById('ghoststorm-recording-toolbar');
    const modal = document.getElementById('gs-checkpoint-modal');
    const statusText = document.getElementById('gs-status-text');
    const countBadge = document.getElementById('gs-checkpoint-count');
    const indicator = document.getElementById('gs-record-indicator');
    const pauseBtn = document.getElementById('gs-btn-pause');
    const pauseIcon = document.getElementById('gs-pause-icon');

    // Make toolbar draggable
    let isDragging = false;
    let dragOffset = { x: 0, y: 0 };

    toolbar.addEventListener('mousedown', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
        isDragging = true;
        dragOffset = {
            x: e.clientX - toolbar.offsetLeft,
            y: e.clientY - toolbar.offsetTop
        };
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        toolbar.style.right = 'auto';
        toolbar.style.left = (e.clientX - dragOffset.x) + 'px';
        toolbar.style.top = (e.clientY - dragOffset.y) + 'px';
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
    });

    // Checkpoint button
    document.getElementById('gs-btn-checkpoint').addEventListener('click', () => {
        if (isPaused) return;
        modal.style.display = 'flex';
        document.getElementById('gs-input-goal').focus();
    });

    // Pause button
    pauseBtn.addEventListener('click', () => {
        isPaused = !isPaused;
        if (isPaused) {
            statusText.textContent = 'Paused';
            indicator.style.animation = 'none';
            indicator.style.background = '#666';
            pauseIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        } else {
            statusText.textContent = 'Recording...';
            indicator.style.animation = 'gs-pulse 1.5s ease-in-out infinite';
            indicator.style.background = '#e94560';
            pauseIcon.innerHTML = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
        }
        window.__ghoststorm_recording_paused = isPaused;
    });

    // Stop button - sends message to backend
    document.getElementById('gs-btn-stop').addEventListener('click', () => {
        window.__ghoststorm_stop_recording = true;
    });

    // Modal cancel
    document.getElementById('gs-btn-cancel').addEventListener('click', () => {
        modal.style.display = 'none';
        clearModalInputs();
    });

    // Modal save checkpoint
    document.getElementById('gs-btn-save-checkpoint').addEventListener('click', async () => {
        const goal = document.getElementById('gs-input-goal').value.trim();
        if (!goal) {
            document.getElementById('gs-input-goal').style.borderColor = '#e94560';
            return;
        }

        const checkpoint = {
            goal: goal,
            checkpoint_type: document.getElementById('gs-input-type').value,
            element_description: document.getElementById('gs-input-element').value.trim() || null,
            timing: {
                min_delay: parseFloat(document.getElementById('gs-input-min-delay').value) || 0.5,
                max_delay: parseFloat(document.getElementById('gs-input-max-delay').value) || 3.0
            },
            url: window.location.href,
            timestamp: Date.now()
        };

        // Send to backend via window property
        window.__ghoststorm_new_checkpoint = checkpoint;

        // Update UI
        checkpointCount++;
        countBadge.textContent = checkpointCount;

        // Close modal
        modal.style.display = 'none';
        clearModalInputs();

        // Flash indicator
        indicator.style.background = '#00ff00';
        setTimeout(() => {
            indicator.style.background = '#e94560';
        }, 300);
    });

    // ESC to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            modal.style.display = 'none';
            clearModalInputs();
        }
    });

    function clearModalInputs() {
        document.getElementById('gs-input-goal').value = '';
        document.getElementById('gs-input-goal').style.borderColor = '#0f3460';
        document.getElementById('gs-input-element').value = '';
        document.getElementById('gs-input-type').value = 'custom';
        document.getElementById('gs-input-min-delay').value = '0.5';
        document.getElementById('gs-input-max-delay').value = '3';
    }

    // Initialize state
    window.__ghoststorm_recording_paused = false;
    window.__ghoststorm_stop_recording = false;
    window.__ghoststorm_new_checkpoint = null;
    window.__ghoststorm_checkpoint_count = 0;

    // Update function for external updates
    window.__ghoststorm_update_count = (count) => {
        checkpointCount = count;
        countBadge.textContent = count;
        window.__ghoststorm_checkpoint_count = count;
    };
})();
"""


@dataclass
class RecordingSession:
    """Active recording session state."""

    flow: RecordedFlow
    browser: Any = None  # Patchright browser instance
    context: Any = None  # Browser context
    page: Any = None  # Active page
    cdp_session: Any = None  # CDP session for events
    is_paused: bool = False
    is_stopped: bool = False
    on_checkpoint: Callable[[Checkpoint], None] | None = None
    on_stop: Callable[[RecordedFlow], None] | None = None
    stealth: StealthConfig | None = None
    proxy_used: str | None = None


class FlowRecorder:
    """Records browser flows using Patchright CDP."""

    def __init__(
        self,
        storage: FlowStorage | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        """Initialize flow recorder.

        Args:
            storage: Flow storage instance.
            project_root: Project root directory.
        """
        self.storage = storage or get_flow_storage()

        if project_root is None:
            self.project_root = Path(__file__).parents[4]
        else:
            self.project_root = Path(project_root)

        self._active_session: RecordingSession | None = None
        self._poll_task: asyncio.Task | None = None

        logger.info("FlowRecorder initialized")

    @property
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._active_session is not None and not self._active_session.is_stopped

    @property
    def current_flow(self) -> RecordedFlow | None:
        """Get the current flow being recorded."""
        if self._active_session:
            return self._active_session.flow
        return None

    async def start_recording(
        self,
        name: str,
        start_url: str,
        description: str = "",
        *,
        stealth: StealthConfig | None = None,
        on_checkpoint: Callable[[Checkpoint], None] | None = None,
        on_stop: Callable[[RecordedFlow], None] | None = None,
    ) -> RecordedFlow:
        """Start recording a new flow.

        Args:
            name: Name for the flow.
            start_url: URL to navigate to.
            description: Optional description.
            stealth: Optional stealth configuration.
            on_checkpoint: Callback when checkpoint is added.
            on_stop: Callback when recording stops.

        Returns:
            The new flow being recorded.
        """
        if self._active_session:
            raise RuntimeError("Recording already in progress")

        # Create new flow
        flow = RecordedFlow(
            name=name,
            description=description,
            start_url=start_url,
            status=FlowStatus.DRAFT,
        )

        # Launch Patchright browser with stealth options
        try:
            from patchright.async_api import async_playwright

            playwright = await async_playwright().start()

            # Build browser args based on stealth config
            browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]

            # WebRTC protection
            if stealth and stealth.get("block_webrtc"):
                browser_args.extend(
                    [
                        "--disable-webrtc",
                        "--disable-webrtc-encryption",
                        "--disable-webrtc-hw-decoding",
                        "--disable-webrtc-hw-encoding",
                        "--webrtc-ip-handling-policy=disable_non_proxied_udp",
                    ]
                )
                logger.info("WebRTC protection enabled")

            # Canvas/WebGL noise (via preferences)
            # Note: Actual noise injection requires script injection, handled in context

            # Get proxy if enabled
            proxy_config = None
            proxy_used = None
            if stealth and stealth.get("use_proxy"):
                proxy_config, proxy_used = await self._get_recording_proxy()
                if proxy_config:
                    logger.info("Using proxy for recording", proxy=proxy_used)

            browser = await playwright.chromium.launch(
                headless=False,  # Headed mode for recording
                args=browser_args,
            )

            # Build context options
            context_options: dict[str, Any] = {
                "viewport": {"width": 1280, "height": 800},
            }

            # Apply proxy to context
            if proxy_config:
                context_options["proxy"] = proxy_config

            # Apply fingerprint if enabled
            if stealth and stealth.get("use_fingerprint"):
                fingerprint_options = await self._generate_recording_fingerprint()
                context_options.update(fingerprint_options)
                logger.info("Random fingerprint applied")

            context = await browser.new_context(**context_options)

            page = await context.new_page()

            # Inject canvas/WebGL noise if enabled
            if stealth and stealth.get("canvas_noise"):
                await self._inject_canvas_noise(page)
                logger.info("Canvas/WebGL noise injection enabled")

            # Create CDP session
            cdp_session = await context.new_cdp_session(page)

            # Create session
            self._active_session = RecordingSession(
                flow=flow,
                browser=browser,
                context=context,
                page=page,
                cdp_session=cdp_session,
                on_checkpoint=on_checkpoint,
                on_stop=on_stop,
                stealth=stealth,
                proxy_used=proxy_used,
            )

            # Inject toolbar
            await self._inject_toolbar(page)

            # Navigate to start URL
            await page.goto(start_url, wait_until="domcontentloaded")

            # Re-inject toolbar after navigation
            await self._inject_toolbar(page)

            # Start polling for checkpoint additions and stop signal
            self._poll_task = asyncio.create_task(self._poll_for_events())

            # Listen for navigation to re-inject toolbar
            page.on("load", lambda: asyncio.create_task(self._on_page_load()))

            stealth_mode = "enabled" if stealth and any(stealth.values()) else "disabled"
            logger.info(
                "Recording started",
                flow_id=flow.id,
                name=name,
                url=start_url,
                stealth=stealth_mode,
                proxy=proxy_used,
            )

            # Save initial state
            await self.storage.save(flow)

            return flow

        except Exception as e:
            logger.error("Failed to start recording", error=str(e))
            raise

    async def _get_recording_proxy(self) -> tuple[dict[str, str] | None, str | None]:
        """Get a proxy for recording session.

        Returns:
            Tuple of (proxy_config_for_playwright, proxy_string_for_logging)
        """
        try:
            # Try to get proxy from file provider
            proxy_file = self.project_root / "data" / "proxies" / "proxies.txt"
            if proxy_file.exists():
                lines = proxy_file.read_text().strip().splitlines()
                valid_proxies = [
                    line.strip() for line in lines if line.strip() and not line.startswith("#")
                ]
                if valid_proxies:
                    proxy_str = random.choice(valid_proxies)
                    # Parse proxy string (format: host:port or user:pass@host:port)
                    if "@" in proxy_str:
                        auth, server = proxy_str.rsplit("@", 1)
                        if ":" in auth:
                            username, password = auth.split(":", 1)
                            return {
                                "server": f"http://{server}",
                                "username": username,
                                "password": password,
                            }, proxy_str
                    return {"server": f"http://{proxy_str}"}, proxy_str
        except Exception as e:
            logger.warning("Failed to get proxy for recording", error=str(e))
        return None, None

    async def _generate_recording_fingerprint(self) -> dict[str, Any]:
        """Generate fingerprint options for recording context.

        Returns:
            Context options dict with fingerprint settings.
        """
        # Common realistic user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]

        # Common screen sizes
        screen_sizes = [
            {"width": 1920, "height": 1080},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
            {"width": 2560, "height": 1440},
            {"width": 1680, "height": 1050},
        ]

        # Common locales
        locales = ["en-US", "en-GB", "en-CA", "en-AU"]

        # Common timezones
        timezones = [
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Europe/London",
            "Europe/Paris",
        ]

        screen = random.choice(screen_sizes)

        return {
            "user_agent": random.choice(user_agents),
            "viewport": screen,
            "screen": screen,
            "locale": random.choice(locales),
            "timezone_id": random.choice(timezones),
            "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
            "is_mobile": False,
            "has_touch": False,
        }

    async def _inject_canvas_noise(self, page: Any) -> None:
        """Inject canvas/WebGL noise to prevent fingerprinting."""
        noise_script = """
        (() => {
            // Canvas noise
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' || type === 'image/webp') {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        const data = imageData.data;
                        // Add subtle noise
                        for (let i = 0; i < data.length; i += 4) {
                            data[i] = data[i] + Math.floor(Math.random() * 3) - 1;     // R
                            data[i+1] = data[i+1] + Math.floor(Math.random() * 3) - 1; // G
                            data[i+2] = data[i+2] + Math.floor(Math.random() * 3) - 1; // B
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                }
                return originalToDataURL.apply(this, arguments);
            };

            // WebGL noise
            const getParameterProxied = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // Add noise to RENDERER and VENDOR
                if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                    return 'Google Inc. (NVIDIA)';
                }
                if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                    const renderers = [
                        'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0)',
                        'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)',
                        'ANGLE (AMD, AMD Radeon RX 6800 Direct3D11 vs_5_0 ps_5_0)',
                    ];
                    return renderers[Math.floor(Math.random() * renderers.length)];
                }
                return getParameterProxied.call(this, parameter);
            };
        })();
        """
        await page.add_init_script(noise_script)

    async def _inject_toolbar(self, page: Any) -> None:
        """Inject the recording toolbar into the page."""
        try:
            # Check if toolbar already exists
            exists = await page.evaluate(
                "() => !!document.getElementById('ghoststorm-recording-toolbar')"
            )
            if exists:
                return

            # Inject HTML
            await page.evaluate(
                f"""() => {{
                    const container = document.createElement('div');
                    container.innerHTML = `{RECORDING_TOOLBAR_HTML}`;
                    document.body.appendChild(container);
                }}"""
            )

            # Inject script
            await page.evaluate(RECORDING_TOOLBAR_SCRIPT)

            # Update checkpoint count
            if self._active_session:
                count = len(self._active_session.flow.checkpoints)
                await page.evaluate(
                    f"() => window.__ghoststorm_update_count && window.__ghoststorm_update_count({count})"
                )

            logger.debug("Toolbar injected")

        except Exception as e:
            logger.warning("Failed to inject toolbar", error=str(e))

    async def _on_page_load(self) -> None:
        """Handle page load events."""
        if self._active_session and self._active_session.page:
            await asyncio.sleep(0.5)  # Wait for page to stabilize
            await self._inject_toolbar(self._active_session.page)

    async def _poll_for_events(self) -> None:
        """Poll for checkpoint additions and stop signal from the browser."""
        while self._active_session and not self._active_session.is_stopped:
            try:
                page = self._active_session.page

                # Check for new checkpoint
                checkpoint_data = await page.evaluate(
                    """() => {
                        const cp = window.__ghoststorm_new_checkpoint;
                        window.__ghoststorm_new_checkpoint = null;
                        return cp;
                    }"""
                )

                if checkpoint_data:
                    await self._handle_checkpoint(checkpoint_data)

                # Check for stop signal
                should_stop = await page.evaluate("() => window.__ghoststorm_stop_recording")

                if should_stop:
                    await self.stop_recording()
                    break

                # Check paused state
                is_paused = await page.evaluate("() => window.__ghoststorm_recording_paused")
                self._active_session.is_paused = is_paused

            except Exception as e:
                # Page might be navigating or closed
                if "Target closed" in str(e) or "has been closed" in str(e):
                    await self.stop_recording()
                    break
                logger.debug("Poll error (may be transient)", error=str(e))

            await asyncio.sleep(0.3)

    async def _handle_checkpoint(self, data: dict[str, Any]) -> None:
        """Handle a new checkpoint from the browser."""
        if not self._active_session:
            return

        try:
            # Take screenshot
            screenshot_b64 = None
            try:
                screenshot_bytes = await self._active_session.page.screenshot(type="png")
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            except Exception as e:
                logger.warning("Failed to capture screenshot", error=str(e))

            # Create checkpoint
            timing = data.get("timing", {})
            checkpoint = Checkpoint(
                checkpoint_type=CheckpointType(data.get("checkpoint_type", "custom")),
                goal=data.get("goal", ""),
                url_pattern=data.get("url"),
                element_description=data.get("element_description"),
                timing=TimingConfig(
                    min_delay=timing.get("min_delay", 0.5),
                    max_delay=timing.get("max_delay", 3.0),
                ),
                reference_screenshot=screenshot_b64,
            )

            # Add to flow
            self._active_session.flow.add_checkpoint(checkpoint)

            # Save
            await self.storage.save(self._active_session.flow)

            # Callback
            if self._active_session.on_checkpoint:
                self._active_session.on_checkpoint(checkpoint)

            logger.info(
                "Checkpoint added",
                flow_id=self._active_session.flow.id,
                checkpoint_id=checkpoint.id,
                goal=checkpoint.goal,
            )

        except Exception as e:
            logger.error("Failed to handle checkpoint", error=str(e))

    async def add_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        goal: str,
        element_description: str | None = None,
        input_value: str | None = None,
        timing: TimingConfig | None = None,
    ) -> Checkpoint | None:
        """Programmatically add a checkpoint.

        Args:
            checkpoint_type: Type of checkpoint.
            goal: Goal description.
            element_description: Description of target element.
            input_value: Value to input (for INPUT type).
            timing: Timing configuration.

        Returns:
            The created checkpoint, or None if no active session.
        """
        if not self._active_session:
            return None

        # Take screenshot
        screenshot_b64 = None
        try:
            screenshot_bytes = await self._active_session.page.screenshot(type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception:
            pass

        checkpoint = Checkpoint(
            checkpoint_type=checkpoint_type,
            goal=goal,
            url_pattern=self._active_session.page.url,
            element_description=element_description,
            input_value=input_value,
            timing=timing or TimingConfig(),
            reference_screenshot=screenshot_b64,
        )

        self._active_session.flow.add_checkpoint(checkpoint)
        await self.storage.save(self._active_session.flow)

        if self._active_session.on_checkpoint:
            self._active_session.on_checkpoint(checkpoint)

        return checkpoint

    async def stop_recording(self) -> RecordedFlow | None:
        """Stop the recording session.

        Returns:
            The completed flow, or None if no active session.
        """
        if not self._active_session:
            return None

        session = self._active_session
        session.is_stopped = True

        # Cancel poll task
        if self._poll_task:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task

        # Finalize flow
        flow = session.flow
        if flow.checkpoints:
            flow.finalize()
        flow.updated_at = datetime.now()

        # Generate summary goal if not set
        if not flow.summary_goal and flow.checkpoints:
            goals = [cp.goal for cp in flow.checkpoints[:5]]
            flow.summary_goal = "; ".join(goals)

        # Save final state
        await self.storage.save(flow)

        # Close browser
        try:
            if session.browser:
                await session.browser.close()
        except Exception as e:
            logger.warning("Error closing browser", error=str(e))

        # Callback
        if session.on_stop:
            session.on_stop(flow)

        self._active_session = None

        logger.info(
            "Recording stopped",
            flow_id=flow.id,
            checkpoints=len(flow.checkpoints),
            status=flow.status.value,
        )

        return flow

    async def cancel_recording(self) -> None:
        """Cancel the recording without saving."""
        if not self._active_session:
            return

        flow_id = self._active_session.flow.id
        self._active_session.is_stopped = True

        # Cancel poll task
        if self._poll_task:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task

        # Close browser
        try:
            if self._active_session.browser:
                await self._active_session.browser.close()
        except Exception:
            pass

        # Delete the draft flow
        await self.storage.delete(flow_id)

        self._active_session = None
        logger.info("Recording cancelled", flow_id=flow_id)


# Global recorder instance
_recorder: FlowRecorder | None = None


def get_flow_recorder() -> FlowRecorder:
    """Get the global flow recorder instance."""
    global _recorder
    if _recorder is None:
        _recorder = FlowRecorder()
    return _recorder
