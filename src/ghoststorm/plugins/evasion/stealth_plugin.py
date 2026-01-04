"""Stealth plugin for anti-detection JavaScript injection.

Enterprise-grade evasion with 2025 anti-detection techniques:
- Dynamic canvas fingerprint noise (per-render)
- WebGL parameter randomization
- AudioContext timing jitter
- Headless detection bypass
- CDP/Automation indicator removal
- Realistic plugin/MIME spoofing
- WebRTC leak prevention
"""

from __future__ import annotations

import contextlib
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ghoststorm.core.registry.hookspecs import hookimpl

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import Fingerprint


class StealthPlugin:
    """Plugin that injects anti-detection JavaScript into browser pages.

    Enterprise Evasion Techniques (v2.0):
    - Dynamic canvas fingerprint noise (per-render randomization)
    - WebGL parameter randomization (GLSL version, texture limits)
    - AudioContext timing jitter (Safari 17+ defense)
    - CDP/Automation trace removal
    - Realistic plugin/MIME type spoofing
    - Chrome runtime emulation (headless detection bypass)
    - Stack trace sanitization
    - Document visibility spoofing
    - Navigator property spoofing
    - Battery API randomization
    - WebRTC leak prevention
    - Font enumeration masking
    """

    name = "stealth"

    def __init__(self) -> None:
        self._template: str | None = None
        self._template_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "data"
            / "evasion"
            / "stealth_template.js"
        )

    def _load_template(self) -> str:
        """Load the stealth JavaScript template."""
        if self._template is None:
            if self._template_path.exists():
                self._template = self._template_path.read_text()
            else:
                self._template = self._generate_minimal_stealth()
        return self._template

    def _generate_minimal_stealth(self) -> str:
        """Generate minimal stealth script if template not found."""
        return """
// Minimal stealth script
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Hide automation indicators
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

// Chrome runtime check
if (window.chrome) {
    window.chrome.runtime = {};
}

// Plugins array
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [1, 2, 3, 4, 5];
        arr.item = (i) => arr[i];
        arr.namedItem = (n) => arr.find(p => p.name === n);
        arr.refresh = () => {};
        return arr;
    }
});

// Languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// Permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({state: Notification.permission}) :
    originalQuery(parameters)
);
"""

    def generate_stealth_script(
        self,
        fingerprint: Fingerprint | None = None,
        *,
        canvas_noise: bool = True,
        webgl_spoof: bool = True,
        fonts_mask: bool = True,
        rtc_block: bool = True,
    ) -> str:
        """Generate stealth script with fingerprint values substituted.

        Args:
            fingerprint: Fingerprint to use for spoofing values
            canvas_noise: Enable canvas fingerprint noise
            webgl_spoof: Enable WebGL parameter spoofing
            fonts_mask: Enable font enumeration masking
            rtc_block: Block WebRTC to prevent IP leaks

        Returns:
            JavaScript code string ready for injection
        """
        template = self._load_template()

        # Generate random values if no fingerprint provided
        if fingerprint is None:
            vendor = random.choice(["Google Inc.", "Apple Computer, Inc.", ""])
            oscpu = random.choice(
                [
                    "Windows NT 10.0; Win64; x64",
                    "Intel Mac OS X 10_15_7",
                    "Linux x86_64",
                ]
            )
            history_length = random.randint(2, 50)
            hardware_concurrency = random.choice([2, 4, 6, 8, 12, 16])
            device_memory = random.choice([2, 4, 8, 16])
            color_depth = 24
            pixel_depth = 24
            canvas_noise_rgba = [
                random.randint(-20, 20),
                random.randint(-20, 20),
                random.randint(-20, 20),
                random.randint(-5, 5),
            ]
            webgl_renderer = random.choice(
                [
                    "WebKit WebGL",
                    "ANGLE (NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0)",
                    "ANGLE (Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
                    "ANGLE (AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
                ]
            )
            fonts = self._generate_random_fonts()
            is_chrome = True
        else:
            vendor = fingerprint.navigator.vendor if fingerprint.navigator else "Google Inc."
            oscpu = (
                fingerprint.navigator.oscpu
                if fingerprint.navigator and fingerprint.navigator.oscpu
                else ""
            )
            history_length = random.randint(2, 50)
            hardware_concurrency = (
                fingerprint.navigator.hardware_concurrency if fingerprint.navigator else 4
            )
            device_memory = fingerprint.navigator.device_memory if fingerprint.navigator else 8
            color_depth = fingerprint.screen.color_depth if fingerprint.screen else 24
            pixel_depth = fingerprint.screen.pixel_depth if fingerprint.screen else 24
            canvas_noise_rgba = [
                fingerprint.canvas.noise_r if fingerprint.canvas else random.randint(-20, 20),
                fingerprint.canvas.noise_g if fingerprint.canvas else random.randint(-20, 20),
                fingerprint.canvas.noise_b if fingerprint.canvas else random.randint(-20, 20),
                fingerprint.canvas.noise_a if fingerprint.canvas else random.randint(-5, 5),
            ]
            webgl_renderer = fingerprint.webgl.renderer if fingerprint.webgl else "WebKit WebGL"
            fonts = fingerprint.fonts if fingerprint.fonts else self._generate_random_fonts()
            is_chrome = "Chrome" in (fingerprint.user_agent or "Chrome")

        # Build substitution map
        substitutions = {
            "[vendor]": vendor,
            "[oscpu]": oscpu,
            "[history.length]": str(history_length),
            "[hardware.concurrency]": str(hardware_concurrency),
            "[device.memory]": str(device_memory),
            "[color.depth]": str(color_depth),
            "[pixel.depth]": str(pixel_depth),
            "[canvasnoiseone]": str(canvas_noise_rgba[0]),
            "[canvasnoisetwo]": str(canvas_noise_rgba[1]),
            "[canvasnoisethree]": str(canvas_noise_rgba[2]),
            "[canvasnoisefour]": str(canvas_noise_rgba[3]),
            "[key]": "37446",  # UNMASKED_RENDERER_WEBGL
            "[value]": webgl_renderer,
            "[chrome_browser]": "true" if is_chrome else "false",
            "[webgl]": "true" if webgl_spoof else "false",
            "[canvas]": "true" if canvas_noise else "false",
            "[fonts]": "true" if fonts_mask else "false",
            '"fonts"': f'"{fonts}"',
        }

        script = template
        for placeholder, value in substitutions.items():
            script = script.replace(placeholder, value)

        # Add WebRTC blocking if enabled
        if rtc_block:
            script = self._add_rtc_blocking(script)

        return script

    def _generate_random_fonts(self) -> str:
        """Generate a random list of common fonts."""
        common_fonts = [
            "Arial",
            "Helvetica",
            "Times New Roman",
            "Georgia",
            "Verdana",
            "Courier New",
            "Comic Sans MS",
            "Impact",
            "Trebuchet MS",
            "Arial Black",
            "Palatino Linotype",
            "Lucida Console",
            "Tahoma",
            "Century Gothic",
            "Bookman Old Style",
            "Garamond",
            "MS Sans Serif",
        ]
        selected = random.sample(common_fonts, min(len(common_fonts), random.randint(8, 15)))
        return ",".join(selected)

    def _add_rtc_blocking(self, script: str) -> str:
        """Add WebRTC IP leak prevention to script."""
        rtc_block = """
// WebRTC IP Leak Prevention
(function() {
    const originalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
    if (originalRTCPeerConnection) {
        const modifiedRTCPeerConnection = function(config, constraints) {
            if (config && config.iceServers) {
                config.iceServers = [];
            }
            return new originalRTCPeerConnection(config, constraints);
        };
        modifiedRTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
        window.RTCPeerConnection = modifiedRTCPeerConnection;
        if (window.webkitRTCPeerConnection) {
            window.webkitRTCPeerConnection = modifiedRTCPeerConnection;
        }
    }
})();
"""
        return rtc_block + "\n" + script

    @hookimpl
    async def after_page_load(self, page: Any, url: str) -> None:
        """Inject stealth script after page loads."""
        script = self.generate_stealth_script()
        try:
            await page.evaluate(script)
        except Exception:
            pass  # Silently fail on script injection errors

    @hookimpl
    async def before_page_load(self, page: Any, url: str) -> str:
        """Set up page interception for stealth injection."""
        script = self.generate_stealth_script()
        with contextlib.suppress(Exception):
            await page.add_init_script(script)
        return url
