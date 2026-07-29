/**
 * USAFE - Main Application
 * Universal Security And Freedom Evaluator
 */

const USAFE = {
    version: '1.0.0',
    
    /**
     * Initialize the application
     */
    async init() {
        console.log('USAFE v' + this.version + ' initializing...');

        // Apply saved/OS theme and language immediately (before anything is shown)
        this.initTheme();
        this.initLanguage();

        // Show loading screen
        await this.showLoading();
        
        // Initialize modules
        CensorshipModule.init();
        SurveillanceModule.init();
        SecureCommModule.init();
        
        // Bind navigation
        this.bindNavigation();
        
        // Bind other events
        this.bindEvents();
        
        // Populate initial data
        await this.populateBrowserInfo();
        
        // Hide loading, show app
        this.hideLoading();

        // Register service worker for offline support (non-blocking)
        this.registerServiceWorker();

        console.log('USAFE initialized successfully');
    },

    /**
     * Show loading animation
     */
    async showLoading() {
        return new Promise(resolve => {
            setTimeout(resolve, 1500); // Minimum loading time for effect
        });
    },

    /**
     * Hide loading screen
     */
    hideLoading() {
        const loadingScreen = document.getElementById('loading-screen');
        const app = document.getElementById('app');
        
        if (loadingScreen) {
            loadingScreen.classList.add('hidden');
        }
        
        if (app) {
            app.classList.remove('hidden');
        }
    },

    /**
     * Register the service worker so the app shell works offline.
     * Does not affect the Censorship module, which always hits the network.
     */
    registerServiceWorker() {
        if (!('serviceWorker' in navigator)) return;
        navigator.serviceWorker.register('/sw.js').catch((err) => {
            console.warn('Service worker registration failed:', err);
        });
    },

    /**
     * Bind navigation events
     */
    bindNavigation() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const moduleId = e.currentTarget.dataset.module;
                this.switchModule(moduleId);
            });
        });
    },

    /**
     * Switch between modules
     */
    switchModule(moduleId) {
        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.module === moduleId);
        });

        // Update modules
        document.querySelectorAll('.module').forEach(module => {
            module.classList.toggle('active', module.id === moduleId);
        });
    },

    /**
     * Bind general events
     */
    bindEvents() {
        // Run all tests button
        document.getElementById('run-all-tests')?.addEventListener('click', () => {
            this.runAllTests();
        });

        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => {
            this.toggleTheme();
        });

        // Export report
        document.getElementById('export-btn')?.addEventListener('click', () => {
            this.exportReport();
        });

        // About modal
        document.getElementById('about-link')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.showModal('about-modal');
        });

        // Privacy modal
        document.getElementById('privacy-link')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.showModal('privacy-modal');
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.remove('active');
            });
        });

        // Close modal on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                }
            });
        });

        // Language select
        document.getElementById('lang-select')?.addEventListener('change', (e) => {
            this.setLanguage(e.target.value);
        });
    },

    /**
     * Populate browser info on dashboard
     */
    async populateBrowserInfo() {
        // Browser info
        const browserInfo = USAFENetwork.getBrowserInfo();
        document.getElementById('browser-info').textContent = 
            `${browserInfo.browser} ${browserInfo.version}`;

        // OS info
        const osInfo = USAFENetwork.getOSInfo();
        document.getElementById('os-info').textContent = 
            `${osInfo.os} ${osInfo.version}`;

        // Screen info
        document.getElementById('screen-info').textContent = 
            `${screen.width}x${screen.height} @ ${screen.colorDepth}bit`;

        // Timezone
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const offset = new Date().getTimezoneOffset();
        const offsetHours = -offset / 60;
        document.getElementById('timezone-info').textContent = 
            `${tz} (UTC${offsetHours >= 0 ? '+' : ''}${offsetHours})`;

        // Language
        document.getElementById('language-info').textContent = 
            navigator.language;

        // IP address (async)
        this.fetchIPAddress();

        // Update encryption status
        this.updateEncryptionStatus();
    },

    /**
     * Fetch and display IP address
     */
    async fetchIPAddress() {
        const ipEl = document.getElementById('ip-address');
        try {
            const ip = await USAFENetwork.getPublicIP();
            ipEl.textContent = ip || 'Unable to detect';
        } catch (e) {
            ipEl.textContent = 'Unable to detect';
        }
    },

    /**
     * Update encryption support status
     */
    updateEncryptionStatus() {
        const statusEl = document.getElementById('encryption-status');
        const valueEl = document.getElementById('encryption-value');
        
        if (USAFECrypto.isAvailable()) {
            statusEl.textContent = '🟢';
            valueEl.textContent = 'Supported';
        } else {
            statusEl.textContent = '🔴';
            valueEl.textContent = 'Not available';
        }
    },

    /**
     * Run all tests from dashboard
     */
    async runAllTests() {
        const btn = document.getElementById('run-all-tests');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="icon">⏳</span> Running tests...';
        }

        try {
            // Run censorship tests
            await CensorshipModule.runAllTests();
            this.updateDashboardStat('censorship', CensorshipModule.getSummary());

            // Run surveillance tests
            await SurveillanceModule.runFullAnalysis();
            this.updateDashboardStat('fingerprint', SurveillanceModule.getSummary());

            // Update tracking status based on fingerprint
            const fpSummary = SurveillanceModule.getSummary();
            this.updateDashboardStat('tracking', {
                status: fpSummary.status,
                icon: fpSummary.icon,
                value: fpSummary.status === 'safe' ? 'Low risk' : 
                       fpSummary.status === 'warning' ? 'Moderate' : 'High risk'
            });

            // Update overall score
            this.updateOverallScore();

            // Update recommendations
            this.updateRecommendations();

        } catch (error) {
            console.error('Error running tests:', error);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="icon">▶️</span> Run All Tests';
            }
        }
    },

    /**
     * Update a dashboard stat
     */
    updateDashboardStat(type, summary) {
        const statusEl = document.getElementById(`${type}-status`);
        const valueEl = document.getElementById(`${type}-value`);
        
        if (statusEl) statusEl.textContent = summary.icon;
        if (valueEl) valueEl.textContent = summary.value;
    },

    /**
     * Calculate and update overall score
     */
    updateOverallScore() {
        let score = 100;
        
        // Deduct based on censorship results
        const censorshipSummary = CensorshipModule.getSummary();
        if (censorshipSummary.status === 'warning') score -= 15;
        if (censorshipSummary.status === 'danger') score -= 30;
        
        // Deduct based on fingerprint uniqueness
        if (SurveillanceModule.analysis) {
            score -= Math.floor(SurveillanceModule.analysis.uniquenessScore * 0.5);
        }
        
        // Ensure score is between 0-100
        score = Math.max(0, Math.min(100, score));
        
        // Update display
        const scoreValue = document.getElementById('overall-score');
        const scoreCircle = document.getElementById('score-circle');
        const scoreLabel = document.getElementById('score-label');
        
        if (scoreValue) scoreValue.textContent = score;
        
        if (scoreCircle) {
            // Circle circumference is 2 * PI * r = 2 * 3.14159 * 45 ≈ 283
            const circumference = 283;
            const offset = circumference - (score / 100 * circumference);
            scoreCircle.style.strokeDashoffset = offset;
            
            // Color based on score
            if (score >= 70) {
                scoreCircle.style.stroke = 'var(--status-safe)';
            } else if (score >= 40) {
                scoreCircle.style.stroke = 'var(--status-warning)';
            } else {
                scoreCircle.style.stroke = 'var(--status-danger)';
            }
        }
        
        if (scoreLabel) {
            if (score >= 70) {
                scoreLabel.textContent = 'Good privacy protection';
            } else if (score >= 40) {
                scoreLabel.textContent = 'Moderate privacy risks';
            } else {
                scoreLabel.textContent = 'High privacy risks detected';
            }
        }
    },

    /**
     * Update recommendations based on test results
     */
    updateRecommendations() {
        const list = document.getElementById('recommendations-list');
        if (!list) return;

        const recommendations = [];
        
        // Based on fingerprint analysis
        if (SurveillanceModule.analysis) {
            const risks = USAFEFingerprint.getRiskAssessment(SurveillanceModule.analysis);
            risks.forEach(risk => {
                recommendations.push({
                    level: risk.level === 'high' ? 'danger' : 
                           risk.level === 'medium' ? 'warning' : 'safe',
                    text: risk.recommendation
                });
            });
        }
        
        // Based on censorship results
        if (CensorshipModule.results.webrtc?.status === 'warning' || 
            CensorshipModule.results.webrtc?.status === 'fail') {
            recommendations.push({
                level: 'warning',
                text: 'Disable WebRTC or use a browser extension to prevent IP leaks'
            });
        }
        
        if (CensorshipModule.results.blocking?.details?.blocked > 0) {
            recommendations.push({
                level: 'warning',
                text: 'Some sites are blocked. Consider using a VPN or Tor'
            });
        }
        
        // Always recommend
        if (recommendations.length === 0) {
            recommendations.push({
                level: 'safe',
                text: 'Your privacy settings look good! Keep your browser updated.'
            });
        }
        
        // Render
        list.innerHTML = recommendations.slice(0, 5).map(rec => 
            `<li class="${rec.level}">${rec.text}</li>`
        ).join('');
    },

    /**
     * Apply a theme ('dark' or 'light'), update the toggle icon, and persist it.
     */
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('usafe-theme', theme);

        const btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.textContent = theme === 'light' ? '☀️' : '🌙';
            btn.title = theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme';
        }
    },

    /**
     * Load the saved theme, falling back to the OS preference.
     */
    initTheme() {
        const saved = localStorage.getItem('usafe-theme');
        const theme = saved || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
        this.applyTheme(theme);
    },

    /**
     * Toggle between dark and light theme.
     */
    toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
        this.applyTheme(current === 'light' ? 'dark' : 'light');
    },

    /**
     * Export report as JSON
     */
    exportReport() {
        const report = {
            version: this.version,
            timestamp: new Date().toISOString(),
            browser: USAFENetwork.getBrowserInfo(),
            os: USAFENetwork.getOSInfo(),
            censorship: CensorshipModule.results,
            fingerprint: SurveillanceModule.analysis ? {
                uniquenessScore: SurveillanceModule.analysis.uniquenessScore,
                uniquenessLevel: SurveillanceModule.analysis.uniquenessLevel,
                canvas: SurveillanceModule.analysis.canvas?.hash,
                webgl: SurveillanceModule.analysis.webgl?.hash,
                audio: SurveillanceModule.analysis.audio?.hash,
                fonts: SurveillanceModule.analysis.fonts?.count,
                features: SurveillanceModule.analysis.features
            } : null
        };

        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `usafe-report-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    },

    /**
     * Show modal
     */
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
        }
    },

    /**
     * i18n strings for elements tagged with data-i18n="key".
     * Scoped to persistent chrome + module headers (not every micro-label,
     * e.g. individual test-result strings generated at runtime) - covers
     * what a user sees before running anything, which is what matters most
     * for a first-run experience in a non-English locale.
     */
    i18n: {
        en: {
            'header.tagline': 'Universal Security And Freedom Evaluator',
            'nav.dashboard': 'Dashboard',
            'nav.censorship': 'Censorship',
            'nav.surveillance': 'Surveillance',
            'nav.secureComm': 'Secure Comm',
            'dashboard.title': '📊 Privacy Dashboard',
            'dashboard.subtitle': 'Overview of your digital privacy status',
            'dashboard.runAll': 'Run All Tests',
            'censorship.title': '🚫 Censorship & Blocking Detector',
            'censorship.subtitle': 'Detect network interference, DNS manipulation, and blocked services',
            'censorship.runAll': 'Run All Censorship Tests',
            'surveillance.title': '👁️ Surveillance & Tracking Detector',
            'surveillance.subtitle': 'Analyze how unique your browser fingerprint is and detect trackers',
            'surveillance.runAll': 'Run Full Fingerprint Analysis',
            'secureComm.title': '🔐 Secure Communication',
            'secureComm.subtitle': 'End-to-end encrypted messaging - no servers, no tracking',
            'footer.note': "USAFE v1.0 - Encryption, fingerprint analysis, and all other processing happen locally in your browser. The Censorship tests are the exception: those make real network requests (DNS resolvers, IP lookups, the sites being tested) because that's what they measure - see Privacy for details."
        },
        tr: {
            'header.tagline': 'Evrensel Güvenlik ve Özgürlük Değerlendiricisi',
            'nav.dashboard': 'Panel',
            'nav.censorship': 'Sansür',
            'nav.surveillance': 'Gözetim',
            'nav.secureComm': 'Güvenli İletişim',
            'dashboard.title': '📊 Gizlilik Paneli',
            'dashboard.subtitle': 'Dijital gizlilik durumunuza genel bakış',
            'dashboard.runAll': 'Tüm Testleri Çalıştır',
            'censorship.title': '🚫 Sansür ve Engelleme Dedektörü',
            'censorship.subtitle': 'Ağ müdahalesini, DNS manipülasyonunu ve engellenen servisleri tespit edin',
            'censorship.runAll': 'Tüm Sansür Testlerini Çalıştır',
            'surveillance.title': '👁️ Gözetim ve İzleme Dedektörü',
            'surveillance.subtitle': 'Tarayıcı parmak izinizin ne kadar benzersiz olduğunu analiz edin ve izleyicileri tespit edin',
            'surveillance.runAll': 'Tam Parmak İzi Analizi Çalıştır',
            'secureComm.title': '🔐 Güvenli İletişim',
            'secureComm.subtitle': 'Uçtan uca şifreli mesajlaşma - sunucu yok, izleme yok',
            'footer.note': 'USAFE v1.0 - Şifreleme, parmak izi analizi ve diğer tüm işlemler tarayıcınızda yerel olarak çalışır. Sansür testleri istisnadır: bunlar gerçek ağ istekleri yapar (DNS çözücüleri, IP sorguları, test edilen siteler) çünkü ölçtükleri şey tam olarak budur - ayrıntılar için Gizlilik bölümüne bakın.'
        }
    },

    /**
     * Apply a language by swapping textContent on every data-i18n element.
     * Falls back to the English string (already present as the element's
     * default markup) for any key missing in the target language.
     */
    setLanguage(lang) {
        const strings = this.i18n[lang] || this.i18n.en;

        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            if (strings[key]) {
                el.textContent = strings[key];
            }
        });

        document.documentElement.lang = lang;
        localStorage.setItem('usafe-lang', lang);
    },

    /**
     * Load the saved language on startup (defaults to English).
     */
    initLanguage() {
        const saved = localStorage.getItem('usafe-lang') || 'en';
        const select = document.getElementById('lang-select');
        if (select) select.value = saved;
        this.setLanguage(saved);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    USAFE.init();
});

// Export
window.USAFE = USAFE;
