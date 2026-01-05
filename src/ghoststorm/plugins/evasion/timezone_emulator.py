"""JavaScript timezone emulation for coherent identity.

Generates init scripts that override timezone-related JavaScript APIs
to match the coherent identity's timezone and locale.

This prevents detection from:
- Date.getTimezoneOffset() returning wrong offset
- Intl.DateTimeFormat using wrong timezone
- navigator.language not matching expected locale
"""

from __future__ import annotations


def generate_timezone_script(timezone_id: str, locale: str) -> str:
    """Generate JavaScript to emulate timezone consistently.

    Args:
        timezone_id: IANA timezone (e.g., "Asia/Tokyo")
        locale: BCP 47 locale (e.g., "ja-JP")

    Returns:
        JavaScript code to inject as init script
    """
    # Escape for JavaScript string
    tz_escaped = timezone_id.replace("'", "\\'")
    locale_escaped = locale.replace("'", "\\'")

    return f"""
(function() {{
    'use strict';

    const TARGET_TIMEZONE = '{tz_escaped}';
    const TARGET_LOCALE = '{locale_escaped}';
    const TARGET_LANGUAGE = TARGET_LOCALE.split('-')[0];

    // =========================================================================
    // TIMEZONE OFFSET EMULATION
    // =========================================================================

    // Calculate the offset for the target timezone
    function getTimezoneOffsetForDate(date) {{
        try {{
            const utcDate = new Date(date.toLocaleString('en-US', {{ timeZone: 'UTC' }}));
            const tzDate = new Date(date.toLocaleString('en-US', {{ timeZone: TARGET_TIMEZONE }}));
            return Math.round((utcDate - tzDate) / 60000);
        }} catch (e) {{
            // Fallback to original if timezone is invalid
            return date.getTimezoneOffset();
        }}
    }}

    // Override Date.prototype.getTimezoneOffset
    const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Object.defineProperty(Date.prototype, 'getTimezoneOffset', {{
        value: function() {{
            return getTimezoneOffsetForDate(this);
        }},
        writable: true,
        configurable: true
    }});

    // =========================================================================
    // INTL API EMULATION
    // =========================================================================

    // Override Intl.DateTimeFormat to use target timezone by default
    const OriginalDateTimeFormat = Intl.DateTimeFormat;

    function PatchedDateTimeFormat(locales, options) {{
        const opts = Object.assign({{}}, options || {{}});

        // Use target timezone if not explicitly specified
        if (!opts.timeZone) {{
            opts.timeZone = TARGET_TIMEZONE;
        }}

        // Use target locale if not explicitly specified
        const resolvedLocales = locales || TARGET_LOCALE;

        return new OriginalDateTimeFormat(resolvedLocales, opts);
    }}

    // Copy static methods and prototype
    PatchedDateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
    PatchedDateTimeFormat.supportedLocalesOf = OriginalDateTimeFormat.supportedLocalesOf;

    Object.defineProperty(Intl, 'DateTimeFormat', {{
        value: PatchedDateTimeFormat,
        writable: true,
        configurable: true
    }});

    // =========================================================================
    // NAVIGATOR LANGUAGE EMULATION
    // =========================================================================

    // Override navigator.language
    Object.defineProperty(navigator, 'language', {{
        get: function() {{
            return TARGET_LOCALE;
        }},
        configurable: true
    }});

    // Override navigator.languages
    Object.defineProperty(navigator, 'languages', {{
        get: function() {{
            return Object.freeze([TARGET_LOCALE, TARGET_LANGUAGE]);
        }},
        configurable: true
    }});

    // =========================================================================
    // DATE STRING EMULATION
    // =========================================================================

    // Patch toLocaleString methods to use target locale/timezone
    const originalToLocaleString = Date.prototype.toLocaleString;
    Object.defineProperty(Date.prototype, 'toLocaleString', {{
        value: function(locales, options) {{
            const opts = Object.assign({{}}, options || {{}});
            if (!opts.timeZone) {{
                opts.timeZone = TARGET_TIMEZONE;
            }}
            return originalToLocaleString.call(this, locales || TARGET_LOCALE, opts);
        }},
        writable: true,
        configurable: true
    }});

    const originalToLocaleDateString = Date.prototype.toLocaleDateString;
    Object.defineProperty(Date.prototype, 'toLocaleDateString', {{
        value: function(locales, options) {{
            const opts = Object.assign({{}}, options || {{}});
            if (!opts.timeZone) {{
                opts.timeZone = TARGET_TIMEZONE;
            }}
            return originalToLocaleDateString.call(this, locales || TARGET_LOCALE, opts);
        }},
        writable: true,
        configurable: true
    }});

    const originalToLocaleTimeString = Date.prototype.toLocaleTimeString;
    Object.defineProperty(Date.prototype, 'toLocaleTimeString', {{
        value: function(locales, options) {{
            const opts = Object.assign({{}}, options || {{}});
            if (!opts.timeZone) {{
                opts.timeZone = TARGET_TIMEZONE;
            }}
            return originalToLocaleTimeString.call(this, locales || TARGET_LOCALE, opts);
        }},
        writable: true,
        configurable: true
    }});

    // =========================================================================
    // RESOLVED OPTIONS EMULATION
    // =========================================================================

    // Ensure Intl.DateTimeFormat().resolvedOptions() returns correct timezone
    const originalResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
    Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
        value: function() {{
            const options = originalResolvedOptions.call(this);
            // If timeZone wasn't explicitly set, report target timezone
            if (!this._explicitTimeZone) {{
                options.timeZone = TARGET_TIMEZONE;
            }}
            return options;
        }},
        writable: true,
        configurable: true
    }});

}})();
"""


def generate_language_script(locale: str, languages: list[str]) -> str:
    """Generate JavaScript to emulate navigator language properties.

    Args:
        locale: Primary locale (e.g., "ja-JP")
        languages: List of accepted languages (e.g., ["ja-JP", "ja", "en"])

    Returns:
        JavaScript code to inject as init script
    """
    # Escape for JavaScript
    locale_escaped = locale.replace("'", "\\'")
    languages_json = str(languages).replace("'", '"')

    return f"""
(function() {{
    'use strict';

    const TARGET_LOCALE = '{locale_escaped}';
    const TARGET_LANGUAGES = {languages_json};

    // Override navigator.language
    Object.defineProperty(navigator, 'language', {{
        get: function() {{
            return TARGET_LOCALE;
        }},
        configurable: true
    }});

    // Override navigator.languages
    Object.defineProperty(navigator, 'languages', {{
        get: function() {{
            return Object.freeze(TARGET_LANGUAGES);
        }},
        configurable: true
    }});
}})();
"""


def generate_geolocation_script(
    latitude: float,
    longitude: float,
    accuracy: float = 100.0,
) -> str:
    """Generate JavaScript to override geolocation API.

    Args:
        latitude: Target latitude
        longitude: Target longitude
        accuracy: Accuracy in meters

    Returns:
        JavaScript code to inject as init script
    """
    return f"""
(function() {{
    'use strict';

    const TARGET_COORDS = {{
        latitude: {latitude},
        longitude: {longitude},
        accuracy: {accuracy},
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null
    }};

    // Override getCurrentPosition
    const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition;
    navigator.geolocation.getCurrentPosition = function(success, error, options) {{
        success({{
            coords: TARGET_COORDS,
            timestamp: Date.now()
        }});
    }};

    // Override watchPosition
    const originalWatchPosition = navigator.geolocation.watchPosition;
    let watchId = 0;
    navigator.geolocation.watchPosition = function(success, error, options) {{
        watchId++;
        success({{
            coords: TARGET_COORDS,
            timestamp: Date.now()
        }});
        return watchId;
    }};
}})();
"""


def generate_full_coherence_script(
    timezone_id: str,
    locale: str,
    languages: list[str],
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Generate complete coherence script combining all emulations.

    Args:
        timezone_id: IANA timezone
        locale: Primary BCP 47 locale
        languages: List of accepted languages
        latitude: Optional geolocation latitude
        longitude: Optional geolocation longitude

    Returns:
        Complete JavaScript init script for identity coherence
    """
    scripts = [
        generate_timezone_script(timezone_id, locale),
    ]

    # Only add separate language script if different from timezone script
    # (timezone script already sets navigator.language)

    if latitude is not None and longitude is not None:
        scripts.append(generate_geolocation_script(latitude, longitude))

    return "\n".join(scripts)
