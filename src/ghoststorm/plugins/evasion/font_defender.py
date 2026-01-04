"""Font fingerprint defense plugin.

Provides advanced font enumeration protection with OS-specific font bundles
to prevent fingerprinting via CSS font detection techniques.

Key Features:
- Bundled OS fonts (Windows 11 22H2, macOS Sonoma, Linux TOR)
- Font loading event masking
- CSS fontFamily enumeration blocking
- Realistic font stack generation
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from ghoststorm.core.registry.hookspecs import hookimpl

logger = structlog.get_logger(__name__)


class OSType(str, Enum):
    """Operating system types for font spoofing."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


@dataclass
class FontProfile:
    """Font profile for a specific OS."""

    os: OSType
    system_fonts: list[str]
    fallback_fonts: list[str]
    monospace_fonts: list[str]


# Windows 11 22H2 font list (common fonts)
WINDOWS_11_FONTS = FontProfile(
    os=OSType.WINDOWS,
    system_fonts=[
        "Segoe UI",
        "Arial",
        "Times New Roman",
        "Tahoma",
        "Verdana",
        "Georgia",
        "Trebuchet MS",
        "Calibri",
        "Cambria",
        "Candara",
        "Century Gothic",
        "Comic Sans MS",
        "Corbel",
        "Garamond",
        "Impact",
        "Lucida Console",
        "Lucida Sans Unicode",
        "Microsoft Sans Serif",
        "MS Gothic",
        "MS PGothic",
        "MS UI Gothic",
        "Palatino Linotype",
        "Segoe Print",
        "Segoe Script",
        "Segoe UI Symbol",
        "Sylfaen",
        "Symbol",
        "Webdings",
        "Wingdings",
    ],
    fallback_fonts=["Arial", "Helvetica", "sans-serif"],
    monospace_fonts=["Consolas", "Lucida Console", "Courier New", "monospace"],
)

# macOS Sonoma font list
MACOS_SONOMA_FONTS = FontProfile(
    os=OSType.MACOS,
    system_fonts=[
        "-apple-system",
        "BlinkMacSystemFont",
        "Helvetica Neue",
        "Helvetica",
        "Arial",
        "Lucida Grande",
        "Geneva",
        "Verdana",
        "Times",
        "Times New Roman",
        "Georgia",
        "Palatino",
        "Baskerville",
        "Didot",
        "Futura",
        "Gill Sans",
        "Hoefler Text",
        "Optima",
        "American Typewriter",
        "Andale Mono",
        "Courier",
        "Courier New",
        "Monaco",
        "Menlo",
        "SF Pro",
        "SF Pro Display",
        "SF Pro Text",
        "SF Mono",
        "New York",
    ],
    fallback_fonts=["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
    monospace_fonts=["SF Mono", "Menlo", "Monaco", "Courier New", "monospace"],
)

# Linux TOR Browser font list (minimal fingerprint)
LINUX_TOR_FONTS = FontProfile(
    os=OSType.LINUX,
    system_fonts=[
        "Liberation Sans",
        "Liberation Serif",
        "Liberation Mono",
        "DejaVu Sans",
        "DejaVu Serif",
        "DejaVu Sans Mono",
        "Noto Sans",
        "Noto Serif",
        "Noto Mono",
        "Ubuntu",
        "Ubuntu Mono",
        "Cantarell",
        "FreeSans",
        "FreeSerif",
        "FreeMono",
        "Droid Sans",
        "Droid Serif",
        "Droid Sans Mono",
    ],
    fallback_fonts=["DejaVu Sans", "Liberation Sans", "sans-serif"],
    monospace_fonts=["DejaVu Sans Mono", "Liberation Mono", "monospace"],
)


# Font profiles by OS
FONT_PROFILES = {
    OSType.WINDOWS: WINDOWS_11_FONTS,
    OSType.MACOS: MACOS_SONOMA_FONTS,
    OSType.LINUX: LINUX_TOR_FONTS,
}


@dataclass
class FontDefenderConfig:
    """Configuration for font defender."""

    # Target OS to spoof fonts for
    target_os: OSType = OSType.WINDOWS

    # Block all font enumeration attempts
    block_enumeration: bool = True

    # Randomize font order
    randomize_order: bool = True

    # Include generic families
    include_generic: bool = True

    # Maximum fonts to expose
    max_fonts: int = 20


class FontDefender:
    """Advanced font fingerprint defense.

    Protects against font enumeration fingerprinting by:
    1. Providing OS-specific font lists
    2. Blocking font loading event timing attacks
    3. Masking CSS font-family detection
    4. Generating realistic font stacks

    Usage:
        defender = FontDefender(FontDefenderConfig(target_os=OSType.WINDOWS))
        js_script = defender.generate_defense_script()
        await page.add_init_script(js_script)
    """

    def __init__(self, config: FontDefenderConfig | None = None) -> None:
        """Initialize font defender.

        Args:
            config: Font defender configuration
        """
        self.config = config or FontDefenderConfig()
        self._profile = FONT_PROFILES[self.config.target_os]

    @property
    def allowed_fonts(self) -> list[str]:
        """Get list of allowed fonts for current profile."""
        fonts = self._profile.system_fonts.copy()

        if self.config.randomize_order:
            random.shuffle(fonts)

        if self.config.max_fonts > 0:
            fonts = fonts[: self.config.max_fonts]

        if self.config.include_generic:
            fonts.extend(["serif", "sans-serif", "monospace", "cursive", "fantasy"])

        return fonts

    def generate_defense_script(self) -> str:
        """Generate JavaScript for font fingerprint defense.

        Returns:
            JavaScript code to inject before page load
        """
        allowed_fonts = self.allowed_fonts
        fonts_json = ",".join(f'"{f.lower()}"' for f in allowed_fonts)

        script = f"""
(() => {{
    'use strict';

    // Allowed fonts list (OS-specific)
    const ALLOWED_FONTS = new Set([{fonts_json}]);
    const GENERIC_FAMILIES = new Set(['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui', 'ui-serif', 'ui-sans-serif', 'ui-monospace', 'ui-rounded', 'inherit', 'initial', 'unset']);

    // Font filtering function
    const filterFontFamily = (family) => {{
        if (!family) return family;

        const fonts = family.replace(/["']/g, '').split(',');
        const filtered = fonts.filter(font => {{
            const normalized = font.trim().toLowerCase();
            return ALLOWED_FONTS.has(normalized) || GENERIC_FAMILIES.has(normalized);
        }});

        return filtered.length > 0 ? filtered.join(', ') : 'sans-serif';
    }};

    // Block font loading timing attacks
    if (typeof FontFace !== 'undefined') {{
        const OriginalFontFace = FontFace;

        window.FontFace = function(family, source, descriptors) {{
            // Add random delay to mask timing
            const face = new OriginalFontFace(family, source, descriptors);
            const originalLoad = face.load.bind(face);

            face.load = function() {{
                return new Promise((resolve, reject) => {{
                    const delay = Math.random() * 50 + 10; // 10-60ms random delay
                    setTimeout(() => {{
                        originalLoad().then(resolve).catch(reject);
                    }}, delay);
                }});
            }};

            return face;
        }};

        window.FontFace.prototype = OriginalFontFace.prototype;
    }}

    // Override document.fonts.check to always return true for allowed fonts
    if (document.fonts && document.fonts.check) {{
        const originalCheck = document.fonts.check.bind(document.fonts);

        document.fonts.check = function(font, text) {{
            // Extract font family from font string
            const match = font.match(/([\\d.]+(?:px|pt|em|rem|%)?)?\\s*(.+)/i);
            if (match && match[2]) {{
                const family = match[2].toLowerCase().replace(/["']/g, '');
                if (ALLOWED_FONTS.has(family) || GENERIC_FAMILIES.has(family)) {{
                    return true;
                }}
            }}
            return originalCheck(font, text);
        }};
    }}

    // Override CSSStyleDeclaration.setProperty for font-family
    const originalSetProperty = CSSStyleDeclaration.prototype.setProperty;
    CSSStyleDeclaration.prototype.setProperty = function(prop, value, priority) {{
        if (prop.toLowerCase() === 'font-family') {{
            value = filterFontFamily(value);
        }}
        return originalSetProperty.call(this, prop, value, priority);
    }};

    // Override fontFamily property
    try {{
        const descriptor = Object.getOwnPropertyDescriptor(CSSStyleDeclaration.prototype, 'fontFamily');
        if (descriptor && descriptor.set) {{
            const originalSet = descriptor.set;
            Object.defineProperty(CSSStyleDeclaration.prototype, 'fontFamily', {{
                get: descriptor.get,
                set: function(value) {{
                    originalSet.call(this, filterFontFamily(value));
                }},
                configurable: true,
                enumerable: true
            }});
        }}
    }} catch (e) {{}}

    // Block canvas-based font detection
    const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {{
        const result = originalMeasureText.call(this, text);

        // Add subtle noise to width measurements
        const noise = (Math.random() - 0.5) * 0.1;
        const width = result.width + noise;

        return {{
            width: width,
            actualBoundingBoxLeft: result.actualBoundingBoxLeft,
            actualBoundingBoxRight: result.actualBoundingBoxRight,
            actualBoundingBoxAscent: result.actualBoundingBoxAscent,
            actualBoundingBoxDescent: result.actualBoundingBoxDescent,
            fontBoundingBoxAscent: result.fontBoundingBoxAscent,
            fontBoundingBoxDescent: result.fontBoundingBoxDescent,
        }};
    }};

    // Mask getComputedStyle font-family
    const originalGetComputedStyle = window.getComputedStyle;
    window.getComputedStyle = function(element, pseudoElt) {{
        const style = originalGetComputedStyle(element, pseudoElt);

        // Create proxy to filter font-family
        return new Proxy(style, {{
            get: function(target, prop) {{
                const value = target[prop];
                if (prop === 'fontFamily' || prop === 'font-family') {{
                    return filterFontFamily(value);
                }}
                if (typeof value === 'function') {{
                    return value.bind(target);
                }}
                return value;
            }}
        }});
    }};

    console.debug('[FontDefender] Initialized with', ALLOWED_FONTS.size, 'allowed fonts');
}})();
"""
        return script

    def get_font_stack(self, font_type: str = "sans-serif") -> str:
        """Generate a realistic font stack for the target OS.

        Args:
            font_type: Type of font stack (sans-serif, serif, monospace)

        Returns:
            CSS font-family string
        """
        if font_type == "monospace":
            fonts = self._profile.monospace_fonts.copy()
        elif font_type == "serif":
            # Use system serif fonts
            serif_fonts = [
                f
                for f in self._profile.system_fonts
                if any(
                    s in f.lower()
                    for s in ["times", "georgia", "palatino", "garamond", "serif"]
                )
            ]
            fonts = serif_fonts if serif_fonts else self._profile.fallback_fonts
        else:
            fonts = self._profile.fallback_fonts.copy()

        return ", ".join(fonts)

    @staticmethod
    def get_profile_for_user_agent(user_agent: str) -> FontProfile:
        """Detect OS from user agent and return matching font profile.

        Args:
            user_agent: Browser user agent string

        Returns:
            Matching FontProfile
        """
        ua_lower = user_agent.lower()

        if "windows" in ua_lower:
            return WINDOWS_11_FONTS
        elif "mac" in ua_lower or "darwin" in ua_lower:
            return MACOS_SONOMA_FONTS
        else:
            return LINUX_TOR_FONTS


class FontDefenderPlugin:
    """Plugin wrapper for font defender integration."""

    name = "font_defender"

    def __init__(self, config: FontDefenderConfig | None = None) -> None:
        self.defender = FontDefender(config)

    @hookimpl
    async def before_page_load(self, page: Any, url: str) -> str:
        """Inject font defense script before page load."""
        script = self.defender.generate_defense_script()
        try:
            await page.add_init_script(script)
            logger.debug("Font defender script injected")
        except Exception as e:
            logger.warning("Failed to inject font defender", error=str(e))
        return url


def get_font_defender(
    target_os: OSType | str = OSType.WINDOWS,
    **kwargs: Any,
) -> FontDefender:
    """Factory function to create font defender.

    Args:
        target_os: Target OS for font spoofing
        **kwargs: Additional config options

    Returns:
        Configured FontDefender instance
    """
    if isinstance(target_os, str):
        target_os = OSType(target_os.lower())

    config = FontDefenderConfig(target_os=target_os, **kwargs)
    return FontDefender(config)
