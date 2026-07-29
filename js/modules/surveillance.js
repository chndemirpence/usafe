/**
 * USAFE - Surveillance Detection Module
 * Browser fingerprinting analysis and tracker detection
 */

const SurveillanceModule = {
    analysis: null,

    /**
     * Initialize the module
     */
    init() {
        this.bindEvents();
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
        document.getElementById('run-surveillance-tests')?.addEventListener('click', () => {
            this.runFullAnalysis();
        });
    },

    /**
     * Run full fingerprint analysis
     */
    async runFullAnalysis() {
        const btn = document.getElementById('run-surveillance-tests');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="icon">⏳</span> Analyzing...';
        }

        try {
            // Run all fingerprint tests
            this.analysis = await USAFEFingerprint.runFullAnalysis();
            
            // Display results
            this.displayCanvasResult();
            this.displayWebGLResult();
            this.displayAudioResult();
            this.displayFontsResult();
            this.displayHardwareResult();
            this.displayPluginsResult();
            this.updateUniquenessScore();
            this.displayTrackerResults();

        } catch (error) {
            console.error('Analysis error:', error);
            this.displayError(error);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="icon">▶️</span> Run Full Fingerprint Analysis';
            }
        }
    },

    /**
     * Display canvas fingerprint result
     */
    displayCanvasResult() {
        const statusEl = document.getElementById('canvas-status');
        const hashEl = document.getElementById('canvas-hash');
        const detailEl = document.getElementById('canvas-detail');
        const data = this.analysis.canvas;

        if (data.supported && data.noiseProtected) {
            statusEl.textContent = 'Protected';
            statusEl.className = 'fp-status common';
            hashEl.textContent = data.hash;
            detailEl.textContent = 'Your browser randomizes canvas output - fingerprinting is resisted';
        } else if (data.supported) {
            statusEl.textContent = 'Unique';
            statusEl.className = 'fp-status unique';
            hashEl.textContent = data.hash;
            detailEl.textContent = 'Canvas fingerprinting is possible on your browser';
        } else {
            statusEl.textContent = 'Protected';
            statusEl.className = 'fp-status common';
            hashEl.textContent = 'Blocked';
            detailEl.textContent = 'Canvas fingerprinting is blocked';
        }
    },

    /**
     * Display WebGL fingerprint result
     */
    displayWebGLResult() {
        const statusEl = document.getElementById('webgl-status');
        const hashEl = document.getElementById('webgl-hash');
        const detailEl = document.getElementById('webgl-detail');
        const data = this.analysis.webgl;

        if (data.supported) {
            const hasUnmasked = data.info?.unmaskedRenderer;
            statusEl.textContent = hasUnmasked ? 'Unique' : 'Moderate';
            statusEl.className = `fp-status ${hasUnmasked ? 'unique' : 'moderate'}`;
            hashEl.textContent = data.hash;
            
            let detail = data.info?.renderer || 'Unknown GPU';
            if (hasUnmasked) {
                detail = data.info.unmaskedRenderer;
            }
            detailEl.textContent = detail;
        } else {
            statusEl.textContent = 'Protected';
            statusEl.className = 'fp-status common';
            hashEl.textContent = 'Disabled';
            detailEl.textContent = 'WebGL is disabled';
        }
    },

    /**
     * Display audio fingerprint result
     */
    displayAudioResult() {
        const statusEl = document.getElementById('audio-status');
        const hashEl = document.getElementById('audio-hash');
        const detailEl = document.getElementById('audio-detail');
        const data = this.analysis.audio;

        if (data.supported) {
            statusEl.textContent = 'Moderate';
            statusEl.className = 'fp-status moderate';
            hashEl.textContent = data.hash;
            detailEl.textContent = `Sample rate: ${data.sampleRate}Hz`;
        } else {
            statusEl.textContent = 'Protected';
            statusEl.className = 'fp-status common';
            hashEl.textContent = 'Blocked';
            detailEl.textContent = 'AudioContext fingerprinting blocked';
        }
    },

    /**
     * Display fonts result
     */
    displayFontsResult() {
        const statusEl = document.getElementById('fonts-status');
        const countEl = document.getElementById('fonts-count');
        const detailEl = document.getElementById('fonts-detail');
        const data = this.analysis.fonts;

        const uniqueness = data.count > 30 ? 'unique' : data.count > 15 ? 'moderate' : 'common';
        statusEl.textContent = uniqueness.charAt(0).toUpperCase() + uniqueness.slice(1);
        statusEl.className = `fp-status ${uniqueness}`;
        countEl.textContent = `${data.count} fonts detected`;
        detailEl.textContent = data.fonts.slice(0, 5).join(', ') + (data.count > 5 ? '...' : '');
    },

    /**
     * Display hardware result
     */
    displayHardwareResult() {
        const statusEl = document.getElementById('hardware-status');
        const infoEl = document.getElementById('hardware-info');
        const detailEl = document.getElementById('hardware-detail');
        const data = this.analysis.hardware;

        statusEl.textContent = 'Visible';
        statusEl.className = 'fp-status moderate';
        infoEl.textContent = `${data.screen.width}x${data.screen.height} @ ${data.screen.colorDepth}bit`;
        
        const details = [];
        if (data.navigator.hardwareConcurrency !== 'unknown') {
            details.push(`${data.navigator.hardwareConcurrency} CPU cores`);
        }
        if (data.navigator.deviceMemory !== 'unknown') {
            details.push(`${data.navigator.deviceMemory}GB RAM`);
        }
        details.push(`DPR: ${data.screen.devicePixelRatio}`);
        detailEl.textContent = details.join(', ');
    },

    /**
     * Display plugins result
     */
    displayPluginsResult() {
        const statusEl = document.getElementById('plugins-status');
        const countEl = document.getElementById('plugins-count');
        const detailEl = document.getElementById('plugins-detail');
        const data = this.analysis.plugins;

        const uniqueness = data.count > 5 ? 'moderate' : 'common';
        statusEl.textContent = uniqueness.charAt(0).toUpperCase() + uniqueness.slice(1);
        statusEl.className = `fp-status ${uniqueness}`;
        countEl.textContent = `${data.count} plugins, ${data.mimeTypes} MIME types`;
        
        if (data.plugins.length > 0) {
            detailEl.textContent = data.plugins.slice(0, 3).map(p => p.name).join(', ');
        } else {
            detailEl.textContent = 'No plugins detected';
        }
    },

    /**
     * Update uniqueness score display
     */
    updateUniquenessScore() {
        const fillEl = document.getElementById('uniqueness-fill');
        const textEl = document.getElementById('uniqueness-text');
        const score = this.analysis.uniquenessScore;
        const level = this.analysis.uniquenessLevel;

        // Update meter (inverted - higher score = less fill from right)
        if (fillEl) {
            fillEl.style.width = `${100 - score}%`;
        }

        if (textEl) {
            const messages = {
                common: `Your browser fingerprint appears relatively common (${score}% uniqueness). This provides some protection against tracking.`,
                moderate: `Your browser fingerprint is moderately unique (${score}% uniqueness). Some tracking is possible.`,
                unique: `Your browser fingerprint is highly unique (${score}% uniqueness). You are easily trackable across sites.`
            };
            textEl.textContent = messages[level] +
                ' This is a simplified heuristic based on signals present in your browser, not a measurement against a real population sample (unlike EFF\'s Cover Your Tracks or AmIUnique) - treat it as a rough indicator, not a precise entropy score.';
        }
    },

    /**
     * Display tracker detection results
     */
    displayTrackerResults() {
        const resultsEl = document.getElementById('tracker-results');
        const risks = USAFEFingerprint.getRiskAssessment(this.analysis);

        let html = '<div class="tracker-list">';
        
        if (risks.length === 0) {
            html += '<div class="tracker-item safe">✓ No significant tracking risks detected</div>';
        } else {
            risks.forEach(risk => {
                const icon = risk.level === 'high' ? '🔴' : 
                            risk.level === 'medium' ? '🟡' : 
                            risk.level === 'low' ? '🟢' : 'ℹ️';
                html += `
                    <div class="tracker-item ${risk.level}">
                        <span class="tracker-icon">${icon}</span>
                        <div class="tracker-info">
                            <strong>${risk.message}</strong>
                            <p class="tracker-rec">${risk.recommendation}</p>
                        </div>
                    </div>
                `;
            });
        }

        html += '</div>';

        // Add feature list
        html += '<div class="features-list"><h4>Browser Features Detected</h4><div class="feature-grid">';
        const features = this.analysis.features;
        for (const [feature, enabled] of Object.entries(features)) {
            const icon = enabled ? '✓' : '✗';
            const cls = enabled ? 'enabled' : 'disabled';
            html += `<span class="feature ${cls}">${icon} ${feature}</span>`;
        }
        html += '</div></div>';

        resultsEl.innerHTML = html;
    },

    /**
     * Display error
     */
    displayError(error) {
        const resultsEl = document.getElementById('tracker-results');
        if (resultsEl) {
            resultsEl.innerHTML = `<div class="error">Error running analysis: ${error.message}</div>`;
        }
    },

    /**
     * Get summary for dashboard
     */
    getSummary() {
        if (!this.analysis) {
            return {
                status: 'pending',
                icon: '⏳',
                value: 'Not tested'
            };
        }

        const score = this.analysis.uniquenessScore;
        
        if (score >= 70) {
            return {
                status: 'danger',
                icon: '🔴',
                value: `${score}% unique`
            };
        }
        
        if (score >= 40) {
            return {
                status: 'warning',
                icon: '🟡',
                value: `${score}% unique`
            };
        }
        
        return {
            status: 'safe',
            icon: '🟢',
            value: `${score}% unique`
        };
    },

    /**
     * Get combined fingerprint hash
     */
    getFingerprint() {
        return this.analysis?.combinedHash || null;
    }
};

// Add styles for tracker results
const trackerStyles = document.createElement('style');
trackerStyles.textContent = `
    .tracker-list {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .tracker-item {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.75rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        border-left: 3px solid var(--border-color);
    }
    
    .tracker-item.high { border-left-color: var(--status-danger); }
    .tracker-item.medium { border-left-color: var(--status-warning); }
    .tracker-item.low { border-left-color: var(--status-safe); }
    .tracker-item.info { border-left-color: var(--status-info); }
    .tracker-item.safe { border-left-color: var(--status-safe); }
    
    .tracker-icon {
        font-size: 1.25rem;
    }
    
    .tracker-info {
        flex: 1;
    }
    
    .tracker-info strong {
        display: block;
        margin-bottom: 0.25rem;
    }
    
    .tracker-rec {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin: 0;
    }
    
    .features-list {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-color);
    }
    
    .features-list h4 {
        margin-bottom: 0.75rem;
        font-size: 0.875rem;
        color: var(--text-secondary);
    }
    
    .feature-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .feature {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-sm);
    }
    
    .feature.enabled { color: var(--status-safe); }
    .feature.disabled { color: var(--text-muted); }
`;
document.head.appendChild(trackerStyles);

// Export
window.SurveillanceModule = SurveillanceModule;
