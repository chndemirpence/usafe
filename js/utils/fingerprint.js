/**
 * USAFE - Fingerprint Utilities
 * Browser fingerprinting detection and analysis
 */

const USAFEFingerprint = {
    /**
     * Draw the same deterministic scene onto a fresh canvas and return its
     * data URL. Kept separate from getCanvasFingerprint so the exact same
     * draw can be repeated to test for anti-fingerprinting noise.
     */
    _drawFingerprintCanvas() {
        const canvas = document.createElement('canvas');
        canvas.width = 280;
        canvas.height = 60;

        const ctx = canvas.getContext('2d');

        // Draw text with various styles
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillStyle = '#f60';
        ctx.fillRect(125, 1, 62, 20);

        ctx.fillStyle = '#069';
        ctx.fillText('USAFE fingerprint test 🛡️', 2, 15);

        ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
        ctx.fillText('Canvas fingerprinting check', 4, 45);

        // Add some shapes
        ctx.beginPath();
        ctx.arc(50, 50, 10, 0, Math.PI * 2, true);
        ctx.closePath();
        ctx.fill();

        return canvas.toDataURL();
    },

    /**
     * Get canvas fingerprint.
     *
     * Also draws the identical scene a second time and compares hashes:
     * browsers with anti-fingerprinting canvas noise (Brave, Tor Browser,
     * Firefox resistFingerprinting) inject small randomized per-read noise,
     * so the same drawing hashes differently each time. A browser with no
     * such protection produces byte-identical output every time. Without
     * this check the previous version reported "fingerprinting possible" for
     * 100% of browsers just because the Canvas API exists - including
     * browsers that are already actively defeating it.
     */
    async getCanvasFingerprint() {
        try {
            const dataURL = this._drawFingerprintCanvas();
            const dataURL2 = this._drawFingerprintCanvas();
            const hash = await USAFECrypto.sha256(dataURL);
            const hash2 = await USAFECrypto.sha256(dataURL2);
            const noiseProtected = hash !== hash2;

            return {
                hash: hash.substring(0, 16),
                fullHash: hash,
                dataURL: dataURL,
                supported: true,
                noiseProtected
            };
        } catch (e) {
            return { supported: false, error: e.message };
        }
    },

    /**
     * Get WebGL fingerprint
     */
    async getWebGLFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            if (!gl) {
                return { supported: false };
            }

            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            
            const info = {
                vendor: gl.getParameter(gl.VENDOR),
                renderer: gl.getParameter(gl.RENDERER),
                unmaskedVendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : null,
                unmaskedRenderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : null,
                version: gl.getParameter(gl.VERSION),
                shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                maxCubeMapTextureSize: gl.getParameter(gl.MAX_CUBE_MAP_TEXTURE_SIZE),
                maxRenderbufferSize: gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),
                maxVertexAttribs: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
                maxVertexUniformVectors: gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS),
                maxFragmentUniformVectors: gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS),
                maxVaryingVectors: gl.getParameter(gl.MAX_VARYING_VECTORS),
                aliasedLineWidthRange: gl.getParameter(gl.ALIASED_LINE_WIDTH_RANGE),
                aliasedPointSizeRange: gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE),
                extensions: gl.getSupportedExtensions()
            };

            const hash = await USAFECrypto.sha256(JSON.stringify(info));
            
            return {
                supported: true,
                hash: hash.substring(0, 16),
                fullHash: hash,
                info: info
            };
        } catch (e) {
            return { supported: false, error: e.message };
        }
    },

    /**
     * Get audio fingerprint.
     *
     * Uses OfflineAudioContext rather than a live AudioContext +
     * ScriptProcessorNode. The live-context version needed a manual
     * onaudioprocess listener and an explicit close() with a race between
     * that resolving and a timeout fallback - under rapid repeated calls
     * this reliably produced a "Cannot close a closed AudioContext" message
     * logged directly by Chromium (not a catchable JS exception or promise
     * rejection - try/catch, .catch(), and an idempotency guard all failed
     * to suppress it). OfflineAudioContext renders synchronously to a
     * buffer via startRendering() - no live audio device, no manual
     * close()/timeout race, and it's the technique real fingerprinting
     * libraries (e.g. FingerprintJS) use for exactly this reason.
     */
    async getAudioFingerprint() {
        try {
            const OfflineCtx = window.OfflineAudioContext || window.webkitOfflineAudioContext;
            if (!OfflineCtx) {
                return { supported: false };
            }

            const context = new OfflineCtx(1, 5000, 44100);
            const oscillator = context.createOscillator();
            const gainNode = context.createGain();

            gainNode.gain.value = 0; // Mute
            oscillator.type = 'triangle';
            oscillator.frequency.value = 10000;

            oscillator.connect(gainNode);
            gainNode.connect(context.destination);
            oscillator.start(0);

            const renderedBuffer = await context.startRendering();
            const data = renderedBuffer.getChannelData(0);
            const hash = await USAFECrypto.sha256(data.slice(4500, 5000).toString());

            return {
                supported: true,
                hash: hash.substring(0, 16),
                fullHash: hash,
                sampleRate: context.sampleRate
            };
        } catch (e) {
            return { supported: false, error: e.message };
        }
    },

    /**
     * Detect installed fonts
     */
    async detectFonts() {
        const baseFonts = ['monospace', 'sans-serif', 'serif'];
        const testFonts = [
            'Arial', 'Arial Black', 'Arial Narrow', 'Calibri', 'Cambria', 
            'Century Gothic', 'Comic Sans MS', 'Consolas', 'Courier', 
            'Courier New', 'Georgia', 'Helvetica', 'Impact', 'Lucida Console',
            'Lucida Sans Unicode', 'Microsoft Sans Serif', 'Palatino Linotype',
            'Segoe UI', 'Tahoma', 'Times', 'Times New Roman', 'Trebuchet MS',
            'Verdana', 'Wingdings', 'Garamond', 'Bookman Old Style',
            'Franklin Gothic Medium', 'Monaco', 'Menlo', 'SF Pro Display',
            'Roboto', 'Open Sans', 'Lato', 'Montserrat', 'Noto Sans'
        ];

        const testString = 'mmmmmmmmmmlli';
        const testSize = '72px';
        const h = document.getElementsByTagName('body')[0];

        // Create test span
        const s = document.createElement('span');
        s.style.position = 'absolute';
        s.style.left = '-9999px';
        s.style.fontSize = testSize;
        s.style.lineHeight = 'normal';
        s.innerHTML = testString;
        
        // Get base widths
        const baseWidths = {};
        for (const base of baseFonts) {
            s.style.fontFamily = base;
            h.appendChild(s);
            baseWidths[base] = s.offsetWidth;
            h.removeChild(s);
        }

        // Test fonts
        const detectedFonts = [];
        for (const font of testFonts) {
            let detected = false;
            for (const base of baseFonts) {
                s.style.fontFamily = `'${font}', ${base}`;
                h.appendChild(s);
                const width = s.offsetWidth;
                h.removeChild(s);
                
                if (width !== baseWidths[base]) {
                    detected = true;
                    break;
                }
            }
            if (detected) {
                detectedFonts.push(font);
            }
        }

        const hash = await USAFECrypto.sha256(detectedFonts.join(','));

        return {
            count: detectedFonts.length,
            fonts: detectedFonts,
            hash: hash.substring(0, 16),
            fullHash: hash
        };
    },

    /**
     * Get hardware info
     */
    getHardwareInfo() {
        return {
            screen: {
                width: screen.width,
                height: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                devicePixelRatio: window.devicePixelRatio || 1
            },
            navigator: {
                hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
                deviceMemory: navigator.deviceMemory || 'unknown',
                maxTouchPoints: navigator.maxTouchPoints || 0,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages ? [...navigator.languages] : [navigator.language],
                cookieEnabled: navigator.cookieEnabled,
                doNotTrack: navigator.doNotTrack || window.doNotTrack || 'unset'
            },
            timezone: {
                offset: new Date().getTimezoneOffset(),
                name: Intl.DateTimeFormat().resolvedOptions().timeZone
            }
        };
    },

    /**
     * Get plugins info
     */
    getPluginsInfo() {
        const plugins = [];
        
        if (navigator.plugins) {
            for (let i = 0; i < navigator.plugins.length; i++) {
                const plugin = navigator.plugins[i];
                plugins.push({
                    name: plugin.name,
                    description: plugin.description,
                    filename: plugin.filename
                });
            }
        }

        return {
            count: plugins.length,
            plugins: plugins,
            mimeTypes: navigator.mimeTypes ? navigator.mimeTypes.length : 0
        };
    },

    /**
     * Check for common browser features
     */
    getFeatures() {
        return {
            localStorage: !!window.localStorage,
            sessionStorage: !!window.sessionStorage,
            indexedDB: !!window.indexedDB,
            webGL: !!(document.createElement('canvas').getContext('webgl')),
            webGL2: !!(document.createElement('canvas').getContext('webgl2')),
            canvas: !!(document.createElement('canvas').getContext('2d')),
            webRTC: !!(window.RTCPeerConnection),
            webWorker: !!window.Worker,
            serviceWorker: !!navigator.serviceWorker,
            webSocket: !!window.WebSocket,
            fetch: !!window.fetch,
            crypto: !!(window.crypto && window.crypto.subtle),
            geolocation: !!navigator.geolocation,
            bluetooth: !!navigator.bluetooth,
            usb: !!navigator.usb,
            battery: !!navigator.getBattery,
            mediaDevices: !!navigator.mediaDevices,
            speechSynthesis: !!window.speechSynthesis,
            speechRecognition: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
            notifications: !!window.Notification,
            clipboard: !!(navigator.clipboard),
            share: !!navigator.share,
            vibrate: !!navigator.vibrate,
            wakeLock: !!navigator.wakeLock
        };
    },

    /**
     * Run full fingerprint analysis
     */
    async runFullAnalysis() {
        const [canvas, webgl, audio, fonts] = await Promise.all([
            this.getCanvasFingerprint(),
            this.getWebGLFingerprint(),
            this.getAudioFingerprint(),
            this.detectFonts()
        ]);

        const hardware = this.getHardwareInfo();
        const plugins = this.getPluginsInfo();
        const features = this.getFeatures();

        // Calculate combined fingerprint hash
        const combinedData = JSON.stringify({
            canvas: canvas.hash,
            webgl: webgl.hash,
            audio: audio.hash,
            fonts: fonts.hash,
            hardware: hardware,
            plugins: plugins.count,
            features: features
        });

        const combinedHash = await USAFECrypto.sha256(combinedData);

        // Calculate uniqueness score (heuristic)
        let uniquenessScore = 0;
        
        // Canvas is highly unique - UNLESS the browser randomizes its output
        // per read, in which case it can't be used as a stable tracking
        // signal across visits and shouldn't count against the score.
        if (canvas.supported && !canvas.noiseProtected) uniquenessScore += 25;
        
        // WebGL with unmasked renderer is very unique
        if (webgl.supported && webgl.info?.unmaskedRenderer) uniquenessScore += 20;
        
        // Audio context varies
        if (audio.supported) uniquenessScore += 15;
        
        // Font count affects uniqueness
        uniquenessScore += Math.min(20, fonts.count / 2);
        
        // Screen resolution
        const commonResolutions = [[1920, 1080], [1366, 768], [1536, 864], [1440, 900]];
        const isCommonRes = commonResolutions.some(r => 
            r[0] === hardware.screen.width && r[1] === hardware.screen.height
        );
        if (!isCommonRes) uniquenessScore += 10;
        
        // Language combinations
        if (hardware.navigator.languages?.length > 3) uniquenessScore += 5;
        
        // Plugin count
        if (plugins.count > 5) uniquenessScore += 5;

        return {
            canvas,
            webgl,
            audio,
            fonts,
            hardware,
            plugins,
            features,
            combinedHash: combinedHash.substring(0, 32),
            uniquenessScore: Math.min(100, uniquenessScore),
            uniquenessLevel: uniquenessScore < 40 ? 'common' : 
                            uniquenessScore < 70 ? 'moderate' : 'unique'
        };
    },

    /**
     * Get risk assessment
     */
    getRiskAssessment(analysis) {
        const risks = [];

        if (analysis.canvas.supported && !analysis.canvas.noiseProtected) {
            risks.push({
                type: 'canvas',
                level: 'high',
                message: 'Canvas fingerprinting is possible - your browser returns identical output every time',
                recommendation: 'Use a browser with canvas fingerprint protection (Brave, Tor Browser, or Firefox with resistFingerprinting)'
            });
        } else if (analysis.canvas.supported && analysis.canvas.noiseProtected) {
            risks.push({
                type: 'canvas',
                level: 'low',
                message: 'Canvas fingerprinting is resisted - your browser randomizes canvas output',
                recommendation: 'No action needed, this protection is already active'
            });
        }

        if (analysis.webgl.supported && analysis.webgl.info?.unmaskedRenderer) {
            risks.push({
                type: 'webgl',
                level: 'high',
                message: `GPU exposed: ${analysis.webgl.info.unmaskedRenderer}`,
                recommendation: 'Disable WebGL or use privacy-focused browser'
            });
        }

        if (analysis.hardware.navigator.doNotTrack === 'unset') {
            risks.push({
                type: 'dnt',
                level: 'medium',
                message: 'Do Not Track is not enabled',
                recommendation: 'Enable Do Not Track in browser settings'
            });
        }

        if (analysis.fonts.count > 30) {
            risks.push({
                type: 'fonts',
                level: 'medium',
                message: `${analysis.fonts.count} fonts detected (high uniqueness)`,
                recommendation: 'Limit installed fonts or use font fingerprint protection'
            });
        }

        if (analysis.plugins.count > 0) {
            risks.push({
                type: 'plugins',
                level: 'low',
                message: `${analysis.plugins.count} browser plugins detected`,
                recommendation: 'Disable or remove unnecessary plugins'
            });
        }

        if (analysis.features.geolocation) {
            risks.push({
                type: 'geolocation',
                level: 'info',
                message: 'Geolocation API is available',
                recommendation: 'Deny location access to untrusted sites'
            });
        }

        return risks;
    }
};

// Export for use
window.USAFEFingerprint = USAFEFingerprint;
