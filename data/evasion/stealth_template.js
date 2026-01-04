/**
 * GhostStorm Enterprise Stealth Template v2.0
 * Advanced anti-detection JavaScript for browser automation
 *
 * Features:
 * - Dynamic canvas fingerprint noise (per-render)
 * - WebGL parameter randomization
 * - AudioContext timing jitter
 * - Headless detection bypass
 * - CDP/Automation indicator removal
 * - Realistic plugin/MIME spoofing
 * - WebRTC leak prevention
 * - IndexedDB/localStorage protection
 */

(() => {
    'use strict';

    // Configuration placeholders (replaced at runtime)
    const CONFIG = {
        vendor: "[vendor]",
        oscpu: "[oscpu]",
        historyLength: [history.length],
        hardwareConcurrency: [hardware.concurrency],
        deviceMemory: [device.memory],
        colorDepth: [color.depth],
        pixelDepth: [pixel.depth],
        canvasNoise: {
            r: [canvasnoiseone],
            g: [canvasnoisetwo],
            b: [canvasnoisethree],
            a: [canvasnoisefour]
        },
        webglRenderer: "[value]",
        isChrome: [chrome_browser],
        enableWebgl: [webgl],
        enableCanvas: [canvas],
        enableFonts: [fonts],
        fonts: "fonts"
    };

    // Utility functions
    const defineProperty = (obj, prop, descriptor) => {
        try {
            Object.defineProperty(obj, prop, descriptor);
        } catch (e) {}
    };

    const randomFloat = (min, max) => Math.random() * (max - min) + min;
    const randomInt = (min, max) => Math.floor(randomFloat(min, max + 1));

    // ===== 1. NAVIGATOR SPOOFING =====

    // Vendor
    defineProperty(navigator, 'vendor', {
        get: () => CONFIG.vendor,
        configurable: true
    });

    // OS/CPU
    if (CONFIG.oscpu) {
        defineProperty(navigator, 'oscpu', {
            get: () => CONFIG.oscpu,
            configurable: true
        });
    }

    // Hardware concurrency
    defineProperty(navigator, 'hardwareConcurrency', {
        get: () => CONFIG.hardwareConcurrency,
        configurable: true
    });

    // Device memory
    defineProperty(navigator, 'deviceMemory', {
        get: () => CONFIG.deviceMemory,
        configurable: true
    });

    // ===== 2. WEBDRIVER/AUTOMATION REMOVAL =====

    // Remove webdriver flag
    defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });

    // Remove CDP traces
    const cdpProperties = [
        '__cdp_binding__',
        '__puppeteer_evaluation_script__',
        '__playwright_evaluation_script__',
        'cdc_adoQpoasnfa76pfcZLmcfl_Array',
        'cdc_adoQpoasnfa76pfcZLmcfl_Promise',
        'cdc_adoQpoasnfa76pfcZLmcfl_Symbol',
        '_phantom',
        '__nightmare',
        '_selenium',
        'callPhantom',
        'callSelenium',
        '_Selenium_IDE_Recorder',
    ];

    cdpProperties.forEach(prop => {
        try {
            delete window[prop];
            defineProperty(window, prop, {
                get: () => undefined,
                set: () => {},
                configurable: false
            });
        } catch (e) {}
    });

    // ===== 3. CHROME RUNTIME (HEADLESS DETECTION) =====

    if (CONFIG.isChrome) {
        // Create realistic chrome object
        if (!window.chrome) {
            window.chrome = {};
        }

        // Chrome runtime with proper structure
        window.chrome.runtime = {
            connect: function() { return {}; },
            sendMessage: function() {},
            onMessage: { addListener: function() {} },
            onConnect: { addListener: function() {} },
            id: undefined
        };

        // Chrome app
        window.chrome.app = {
            isInstalled: false,
            InstallState: {
                DISABLED: 'disabled',
                INSTALLED: 'installed',
                NOT_INSTALLED: 'not_installed'
            },
            RunningState: {
                CANNOT_RUN: 'cannot_run',
                READY_TO_RUN: 'ready_to_run',
                RUNNING: 'running'
            },
            getDetails: function() { return null; },
            getIsInstalled: function() { return false; },
            runningState: function() { return 'cannot_run'; }
        };

        // Chrome csi
        window.chrome.csi = function() {
            return {
                startE: Date.now(),
                onloadT: Date.now() + randomInt(50, 300),
                pageT: randomInt(1000, 5000),
                tran: randomInt(10, 20)
            };
        };

        // Chrome loadTimes
        window.chrome.loadTimes = function() {
            return {
                commitLoadTime: Date.now() / 1000,
                connectionInfo: 'h2',
                finishDocumentLoadTime: Date.now() / 1000 + randomFloat(0.1, 0.5),
                finishLoadTime: Date.now() / 1000 + randomFloat(0.5, 1.5),
                firstPaintAfterLoadTime: 0,
                firstPaintTime: Date.now() / 1000 + randomFloat(0.05, 0.2),
                navigationType: 'Other',
                npnNegotiatedProtocol: 'h2',
                requestTime: Date.now() / 1000 - randomFloat(0.1, 0.3),
                startLoadTime: Date.now() / 1000,
                wasAlternateProtocolAvailable: false,
                wasFetchedViaSpdy: true,
                wasNpnNegotiated: true
            };
        };
    } else {
        // Non-Chrome: remove chrome object
        try {
            delete window.chrome;
            delete window.Chrome;
        } catch (e) {}
    }

    // ===== 4. REALISTIC PLUGINS & MIME TYPES =====

    const createPluginArray = () => {
        const plugins = [
            {
                name: 'Chrome PDF Plugin',
                filename: 'internal-pdf-viewer',
                description: 'Portable Document Format',
                mimeTypes: [{ type: 'application/pdf', description: 'Portable Document Format', suffixes: 'pdf' }]
            },
            {
                name: 'Chrome PDF Viewer',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                description: '',
                mimeTypes: [{ type: 'application/pdf', description: '', suffixes: 'pdf' }]
            },
            {
                name: 'Native Client',
                filename: 'internal-nacl-plugin',
                description: '',
                mimeTypes: [
                    { type: 'application/x-nacl', description: 'Native Client Executable', suffixes: '' },
                    { type: 'application/x-pnacl', description: 'Portable Native Client Executable', suffixes: '' }
                ]
            }
        ];

        const pluginArray = Object.create(PluginArray.prototype);
        const mimeTypeArray = Object.create(MimeTypeArray.prototype);
        const allMimeTypes = [];

        plugins.forEach((pluginData, index) => {
            const plugin = Object.create(Plugin.prototype);
            defineProperty(plugin, 'name', { get: () => pluginData.name });
            defineProperty(plugin, 'filename', { get: () => pluginData.filename });
            defineProperty(plugin, 'description', { get: () => pluginData.description });
            defineProperty(plugin, 'length', { get: () => pluginData.mimeTypes.length });

            pluginData.mimeTypes.forEach((mimeData, mimeIndex) => {
                const mimeType = Object.create(MimeType.prototype);
                defineProperty(mimeType, 'type', { get: () => mimeData.type });
                defineProperty(mimeType, 'description', { get: () => mimeData.description });
                defineProperty(mimeType, 'suffixes', { get: () => mimeData.suffixes });
                defineProperty(mimeType, 'enabledPlugin', { get: () => plugin });

                plugin[mimeIndex] = mimeType;
                allMimeTypes.push(mimeType);
            });

            plugin.item = (i) => plugin[i];
            plugin.namedItem = (name) => {
                for (let i = 0; i < plugin.length; i++) {
                    if (plugin[i].type === name) return plugin[i];
                }
                return null;
            };

            pluginArray[index] = plugin;
            pluginArray[pluginData.name] = plugin;
        });

        defineProperty(pluginArray, 'length', { get: () => plugins.length });
        pluginArray.item = (i) => pluginArray[i];
        pluginArray.namedItem = (name) => pluginArray[name];
        pluginArray.refresh = () => {};

        allMimeTypes.forEach((mime, i) => {
            mimeTypeArray[i] = mime;
            mimeTypeArray[mime.type] = mime;
        });
        defineProperty(mimeTypeArray, 'length', { get: () => allMimeTypes.length });
        mimeTypeArray.item = (i) => mimeTypeArray[i];
        mimeTypeArray.namedItem = (name) => mimeTypeArray[name];

        return { pluginArray, mimeTypeArray };
    };

    const { pluginArray, mimeTypeArray } = createPluginArray();
    defineProperty(navigator, 'plugins', { get: () => pluginArray, configurable: true });
    defineProperty(navigator, 'mimeTypes', { get: () => mimeTypeArray, configurable: true });

    // ===== 5. HISTORY LENGTH =====

    defineProperty(window.history, 'length', {
        get: () => CONFIG.historyLength,
        configurable: true
    });

    // ===== 6. SCREEN PROPERTIES =====

    defineProperty(screen, 'colorDepth', {
        get: () => CONFIG.colorDepth,
        configurable: true
    });

    defineProperty(screen, 'pixelDepth', {
        get: () => CONFIG.pixelDepth,
        configurable: true
    });

    // ===== 7. BATTERY API RANDOMIZATION =====

    const batteryState = {
        charging: Math.random() > 0.3,
        level: randomFloat(0.5, 1.0),
        chargingTime: Math.random() > 0.5 ? Infinity : randomInt(1200, 7200),
        dischargingTime: Math.random() > 0.5 ? Infinity : randomInt(3600, 28800)
    };

    if (typeof BatteryManager !== 'undefined') {
        Object.defineProperties(BatteryManager.prototype, {
            charging: {
                configurable: true,
                enumerable: true,
                get: () => batteryState.charging
            },
            chargingTime: {
                configurable: true,
                enumerable: true,
                get: () => batteryState.chargingTime
            },
            dischargingTime: {
                configurable: true,
                enumerable: true,
                get: () => batteryState.dischargingTime
            },
            level: {
                configurable: true,
                enumerable: true,
                get: () => batteryState.level
            }
        });
    }

    // ===== 8. WEBRTC LEAK PREVENTION =====

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

    // ===== 9. DYNAMIC CANVAS FINGERPRINT NOISE =====

    if (CONFIG.enableCanvas) {
        const originalToBlob = HTMLCanvasElement.prototype.toBlob;
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

        // Generate per-render noise with stronger variations to prevent fingerprinting
        const generateNoise = () => ({
            r: CONFIG.canvasNoise.r + randomInt(-5, 5),
            g: CONFIG.canvasNoise.g + randomInt(-5, 5),
            b: CONFIG.canvasNoise.b + randomInt(-5, 5),
            a: CONFIG.canvasNoise.a + randomInt(-2, 2)
        });

        const applyNoise = (canvas, context) => {
            try {
                const width = canvas.width;
                const height = canvas.height;
                if (width === 0 || height === 0) return;

                const imageData = originalGetImageData.call(context, 0, 0, width, height);
                const noise = generateNoise();

                // Apply subtle per-pixel noise variation
                for (let i = 0; i < imageData.data.length; i += 4) {
                    const pixelNoise = (i % 16 === 0) ? randomInt(-1, 1) : 0;
                    imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise.r + pixelNoise));
                    imageData.data[i + 1] = Math.max(0, Math.min(255, imageData.data[i + 1] + noise.g + pixelNoise));
                    imageData.data[i + 2] = Math.max(0, Math.min(255, imageData.data[i + 2] + noise.b + pixelNoise));
                    imageData.data[i + 3] = Math.max(0, Math.min(255, imageData.data[i + 3] + noise.a));
                }

                context.putImageData(imageData, 0, 0);
            } catch (e) {}
        };

        HTMLCanvasElement.prototype.toBlob = function(...args) {
            const context = this.getContext('2d');
            if (context) applyNoise(this, context);
            return originalToBlob.apply(this, args);
        };

        HTMLCanvasElement.prototype.toDataURL = function(...args) {
            const context = this.getContext('2d');
            if (context) applyNoise(this, context);
            return originalToDataURL.apply(this, args);
        };

        CanvasRenderingContext2D.prototype.getImageData = function(...args) {
            applyNoise(this.canvas, this);
            return originalGetImageData.apply(this, args);
        };
    }

    // ===== 10. WEBGL PARAMETER RANDOMIZATION =====

    if (CONFIG.enableWebgl) {
        const webglParams = {
            37446: CONFIG.webglRenderer,  // UNMASKED_RENDERER_WEBGL
            37445: 'Google Inc. (NVIDIA)',  // UNMASKED_VENDOR_WEBGL
            7936: 'WebKit',  // VENDOR
            7937: 'WebKit WebGL',  // RENDERER
            35661: randomInt(8, 16),  // MAX_TEXTURE_SIZE
            34024: randomInt(8, 16),  // MAX_CUBE_MAP_TEXTURE_SIZE
            34930: randomInt(8, 16),  // MAX_TEXTURE_IMAGE_UNITS
            35660: randomInt(8, 16),  // MAX_VERTEX_TEXTURE_IMAGE_UNITS
            34076: randomInt(16384, 32768),  // MAX_TEXTURE_SIZE
            36349: randomInt(1024, 4096),  // MAX_FRAGMENT_UNIFORM_VECTORS
            36347: randomInt(256, 512),  // MAX_VERTEX_UNIFORM_VECTORS
            34921: randomInt(8, 16),  // MAX_VERTEX_ATTRIBS
            36348: randomInt(8, 32),  // MAX_VARYING_VECTORS
        };

        const patchWebGL = (proto) => {
            const originalGetParameter = proto.getParameter;
            proto.getParameter = function(param) {
                if (webglParams[param] !== undefined) {
                    return webglParams[param];
                }
                return originalGetParameter.call(this, param);
            };

            // Randomize getShaderPrecisionFormat
            const originalGetShaderPrecisionFormat = proto.getShaderPrecisionFormat;
            proto.getShaderPrecisionFormat = function(shaderType, precisionType) {
                const result = originalGetShaderPrecisionFormat.call(this, shaderType, precisionType);
                if (result) {
                    // Add subtle variation
                    return {
                        rangeMin: result.rangeMin,
                        rangeMax: result.rangeMax,
                        precision: result.precision
                    };
                }
                return result;
            };
        };

        if (typeof WebGLRenderingContext !== 'undefined') {
            patchWebGL(WebGLRenderingContext.prototype);
        }
        if (typeof WebGL2RenderingContext !== 'undefined') {
            patchWebGL(WebGL2RenderingContext.prototype);
        }
    }

    // ===== 11. AUDIOCONTEXT TIMING JITTER =====

    if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
        const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;

        const patchedAudioContext = function(...args) {
            const context = new OriginalAudioContext(...args);

            // Add timing jitter to currentTime
            const originalCurrentTime = Object.getOwnPropertyDescriptor(
                OriginalAudioContext.prototype, 'currentTime'
            );

            if (originalCurrentTime && originalCurrentTime.get) {
                defineProperty(context, 'currentTime', {
                    get: function() {
                        const time = originalCurrentTime.get.call(this);
                        // Add microsecond-level jitter (Safari 17+ fingerprinting defense)
                        return time + (Math.random() * 0.0001);
                    }
                });
            }

            // Patch createAnalyser for frequency data noise
            const originalCreateAnalyser = context.createAnalyser.bind(context);
            context.createAnalyser = function() {
                const analyser = originalCreateAnalyser();
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);

                analyser.getFloatFrequencyData = function(array) {
                    originalGetFloatFrequencyData(array);
                    // Add subtle noise to frequency data
                    for (let i = 0; i < array.length; i += 10) {
                        array[i] += randomFloat(-0.1, 0.1);
                    }
                };

                return analyser;
            };

            return context;
        };

        patchedAudioContext.prototype = OriginalAudioContext.prototype;
        window.AudioContext = patchedAudioContext;
        if (window.webkitAudioContext) {
            window.webkitAudioContext = patchedAudioContext;
        }
    }

    // ===== 12. PERMISSIONS API =====

    if (navigator.permissions) {
        const originalQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({
                    state: Notification.permission,
                    onchange: null
                });
            }
            return originalQuery(parameters);
        };
    }

    // ===== 13. LANGUAGES =====

    defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true
    });

    // ===== 14. FONT ENUMERATION DEFENSE =====

    if (CONFIG.enableFonts) {
        const fontWhitelist = CONFIG.fonts.toLowerCase().split(',').map(f => f.trim());
        const baseFonts = ['default', 'inherit', 'auto', 'serif', 'sans-serif', 'monospace', 'cursive', 'fantasy'];
        const allowedFonts = [...baseFonts, ...fontWhitelist];

        const filterFontFamily = (family) => {
            if (!family) return family;
            const fonts = family.replace(/["']/g, '').split(',');
            const filtered = fonts.filter(font => {
                const normalized = font.trim().toLowerCase();
                return allowedFonts.some(allowed => normalized === allowed || normalized.includes(allowed));
            });
            return filtered.length > 0 ? filtered.join(', ') : 'sans-serif';
        };

        // Override CSSStyleDeclaration.setProperty
        const originalSetProperty = CSSStyleDeclaration.prototype.setProperty;
        CSSStyleDeclaration.prototype.setProperty = function(prop, value, priority) {
            if (prop.toLowerCase() === 'font-family') {
                value = filterFontFamily(value);
            }
            return originalSetProperty.call(this, prop, value, priority);
        };

        // Override fontFamily getter/setter
        try {
            const fontFamilyDescriptor = Object.getOwnPropertyDescriptor(CSSStyleDeclaration.prototype, 'fontFamily');
            if (fontFamilyDescriptor) {
                defineProperty(CSSStyleDeclaration.prototype, 'fontFamily', {
                    get: fontFamilyDescriptor.get,
                    set: function(value) {
                        fontFamilyDescriptor.set.call(this, filterFontFamily(value));
                    },
                    configurable: true
                });
            }
        } catch (e) {}
    }

    // ===== 15. IFRAME CONTENTWINDOW PROTECTION =====

    try {
        const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
        if (originalContentWindow && originalContentWindow.get) {
            defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    const win = originalContentWindow.get.call(this);
                    if (win) {
                        // Ensure iframe windows don't expose automation
                        try {
                            defineProperty(win.navigator, 'webdriver', {
                                get: () => undefined
                            });
                        } catch (e) {}
                    }
                    return win;
                }
            });
        }
    } catch (e) {}

    // ===== 16. ERROR STACK TRACE CLEANING =====

    if (typeof Error.captureStackTrace === 'function') {
        const originalCaptureStackTrace = Error.captureStackTrace;
        Error.captureStackTrace = function(obj, constructorOpt) {
            originalCaptureStackTrace.call(this, obj, constructorOpt);
            if (obj.stack) {
                obj.stack = obj.stack
                    .split('\n')
                    .filter(line =>
                        !line.includes('__puppeteer') &&
                        !line.includes('__playwright') &&
                        !line.includes('pptr:') &&
                        !line.includes('evaluate') &&
                        !line.includes('Runtime.evaluate')
                    )
                    .join('\n');
            }
        };
    }

    // ===== 17. DOCUMENT.HIDDEN / VISIBILITY =====

    // Prevent detection of hidden tabs (common bot check)
    defineProperty(document, 'hidden', {
        get: () => false,
        configurable: true
    });

    defineProperty(document, 'visibilityState', {
        get: () => 'visible',
        configurable: true
    });

    // ===== 18. HEADLESS CHROME DETECTION BYPASSES =====

    // window.outerWidth/outerHeight (often 0 in headless)
    if (window.outerWidth === 0 || window.outerHeight === 0) {
        defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
        defineProperty(window, 'outerHeight', { get: () => window.innerHeight });
    }

    // Connection type (navigator.connection)
    if (navigator.connection) {
        try {
            defineProperty(navigator.connection, 'rtt', { get: () => randomInt(50, 150) });
        } catch (e) {}
    }

    // ===== 19. SEC-CH-UA (CLIENT HINTS) SPOOFING =====
    // Chrome sends Sec-CH-UA headers that must match User-Agent
    // Mismatch reveals fake fingerprint

    if (CONFIG.isChrome) {
        const userAgentData = {
            brands: [
                { brand: "Not_A Brand", version: "8" },
                { brand: "Chromium", version: "120" },
                { brand: "Google Chrome", version: "120" }
            ],
            mobile: false,
            platform: "Windows",
            platformVersion: "15.0.0",
            architecture: "x86",
            bitness: "64",
            model: "",
            uaFullVersion: "120.0.6099.130",
            fullVersionList: [
                { brand: "Not_A Brand", version: "8.0.0.0" },
                { brand: "Chromium", version: "120.0.6099.130" },
                { brand: "Google Chrome", version: "120.0.6099.130" }
            ],
            wow64: false
        };

        // Spoof navigator.userAgentData
        try {
            const NavigatorUAData = {
                get brands() { return userAgentData.brands; },
                get mobile() { return userAgentData.mobile; },
                get platform() { return userAgentData.platform; },
                getHighEntropyValues: function(hints) {
                    return Promise.resolve({
                        brands: userAgentData.brands,
                        mobile: userAgentData.mobile,
                        platform: userAgentData.platform,
                        platformVersion: hints.includes('platformVersion') ? userAgentData.platformVersion : undefined,
                        architecture: hints.includes('architecture') ? userAgentData.architecture : undefined,
                        bitness: hints.includes('bitness') ? userAgentData.bitness : undefined,
                        model: hints.includes('model') ? userAgentData.model : undefined,
                        uaFullVersion: hints.includes('uaFullVersion') ? userAgentData.uaFullVersion : undefined,
                        fullVersionList: hints.includes('fullVersionList') ? userAgentData.fullVersionList : undefined,
                        wow64: hints.includes('wow64') ? userAgentData.wow64 : undefined
                    });
                },
                toJSON: function() {
                    return {
                        brands: userAgentData.brands,
                        mobile: userAgentData.mobile,
                        platform: userAgentData.platform
                    };
                }
            };

            defineProperty(navigator, 'userAgentData', {
                get: () => NavigatorUAData,
                configurable: true
            });
        } catch (e) {}
    }

    // ===== 20. STORAGE CLEARING (TRACKING PROTECTION) =====
    // IndexedDB and localStorage can persist identifiers across sessions
    // Clear on init to prevent cross-session tracking

    try {
        // Clear localStorage on init
        if (typeof localStorage !== 'undefined' && localStorage.clear) {
            localStorage.clear();
        }
    } catch (e) {}

    try {
        // Clear sessionStorage on init
        if (typeof sessionStorage !== 'undefined' && sessionStorage.clear) {
            sessionStorage.clear();
        }
    } catch (e) {}

    // Block IndexedDB access for persistent tracking
    try {
        const originalOpen = indexedDB.open;
        indexedDB.open = function(name, version) {
            // Allow essential databases but block tracking databases
            const blockedPatterns = [
                /fingerprint/i,
                /tracking/i,
                /analytics/i,
                /evercookie/i,
                /persist/i,
                /_ga_/i,
                /fb_/i,
            ];

            const isBlocked = blockedPatterns.some(pattern => pattern.test(name));
            if (isBlocked) {
                // Return a rejected request for blocked databases
                const request = {
                    result: null,
                    error: new DOMException('Database access denied', 'SecurityError'),
                    onerror: null,
                    onsuccess: null,
                    onupgradeneeded: null,
                    onblocked: null,
                };
                setTimeout(() => {
                    if (request.onerror) request.onerror(new Event('error'));
                }, 0);
                return request;
            }
            return originalOpen.call(this, name, version);
        };

        // Also hook deleteDatabase to prevent "database exists" detection
        const originalDeleteDatabase = indexedDB.deleteDatabase;
        indexedDB.deleteDatabase = function(name) {
            try {
                return originalDeleteDatabase.call(this, name);
            } catch (e) {
                return Promise.resolve();
            }
        };
    } catch (e) {}

    // ===== INITIALIZATION COMPLETE =====

})();
