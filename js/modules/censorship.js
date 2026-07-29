/**
 * USAFE - Censorship Detection Module
 * Tests for DNS manipulation, blocking, and network interference
 */

const CensorshipModule = {
    results: {},

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
        document.querySelectorAll('[data-test]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const testType = e.target.dataset.test;
                await this.runTest(testType);
            });
        });

        document.getElementById('run-censorship-tests')?.addEventListener('click', () => {
            this.runAllTests();
        });
    },

    /**
     * Run a specific test
     */
    async runTest(testType) {
        const statusEl = document.getElementById(`${testType}-status`);
        const resultsEl = document.getElementById(`${testType}-results`);
        
        if (statusEl) {
            statusEl.textContent = 'Running...';
            statusEl.className = 'test-status running';
        }
        
        if (resultsEl) {
            resultsEl.innerHTML = '<div class="loading">Testing...</div>';
        }

        try {
            let result;
            switch (testType) {
                case 'dns':
                    result = await this.runDNSTest();
                    break;
                case 'webrtc':
                    result = await this.runWebRTCTest();
                    break;
                case 'blocking':
                    result = await this.runBlockingTest();
                    break;
                case 'vpn':
                    result = await this.runVPNTest();
                    break;
                default:
                    throw new Error(`Unknown test: ${testType}`);
            }

            this.results[testType] = result;
            this.displayResult(testType, result);
        } catch (error) {
            this.displayError(testType, error);
        }
    },

    /**
     * Run all censorship tests
     */
    async runAllTests() {
        const tests = ['dns', 'webrtc', 'blocking', 'vpn'];
        for (const test of tests) {
            await this.runTest(test);
            // Small delay between tests
            await new Promise(r => setTimeout(r, 500));
        }
    },

    /**
     * DNS manipulation test
     */
    async runDNSTest() {
        const testDomains = ['google.com', 'cloudflare.com', 'github.com'];
        const results = [];

        for (const domain of testDomains) {
            const comparison = await USAFENetwork.compareDNS(domain);
            results.push(comparison);
        }

        const hasManipulation = results.some(r => r.manipulation);
        const allInconclusive = results.every(r => r.inconclusive);
        const someInconclusive = results.some(r => r.inconclusive);

        let status = 'pass';
        let message = 'DNS responses are consistent';

        if (hasManipulation) {
            status = 'warning';
            message = 'Possible DNS manipulation detected';
        } else if (allInconclusive) {
            status = 'warning';
            message = 'All DNS-over-HTTPS resolvers failed - this often means they are blocked, not that DNS is clean';
        } else if (someInconclusive) {
            status = 'warning';
            message = 'DNS responses are consistent where reachable, but some resolvers could not be reached';
        }

        return {
            status,
            message,
            details: results
        };
    },

    /**
     * WebRTC leak test
     */
    async runWebRTCTest() {
        const result = await USAFENetwork.detectWebRTCLeak();
        const publicIP = await USAFENetwork.getPublicIP();

        let status = 'pass';
        let message = 'No WebRTC IP leak detected';

        if (!result.supported) {
            status = 'pass';
            message = 'WebRTC is disabled or not supported';
        } else if (result.ips.public.length > 0) {
            if (publicIP && result.ips.public.includes(publicIP)) {
                status = 'warning';
                message = 'WebRTC exposes your public IP';
            } else if (result.ips.public.length > 0) {
                status = 'fail';
                message = 'WebRTC leaking different IP than HTTP';
            }
        }

        if (result.ips.local.length > 0) {
            status = status === 'pass' ? 'warning' : status;
            message += `. Local IPs visible: ${result.ips.local.join(', ')}`;
        }

        return {
            status,
            message,
            details: {
                supported: result.supported,
                publicIPs: result.ips.public,
                localIPs: result.ips.local,
                ipv6: result.ips.ipv6,
                httpIP: publicIP
            }
        };
    },

    /**
     * Site blocking test
     */
    async runBlockingTest() {
        const sites = USAFENetwork.getTestSites();
        const results = await USAFENetwork.testSites(sites);
        
        const blocked = results.filter(r => !r.reachable);
        const reachable = results.filter(r => r.reachable);

        let status = 'pass';
        let message = 'All tested sites are reachable';

        if (blocked.length > 0) {
            status = blocked.length > 3 ? 'fail' : 'warning';
            message = `${blocked.length} of ${sites.length} sites may be blocked`;
        }

        return {
            status,
            message,
            details: {
                total: sites.length,
                reachable: reachable.length,
                blocked: blocked.length,
                sites: results
            }
        };
    },

    /**
     * VPN leak check - note this cannot detect whether a VPN is active at
     * all, only whether one (if active) is leaking your real IP/DNS.
     */
    async runVPNTest() {
        const result = await USAFENetwork.detectVPN();

        let status = 'pass';
        let message = 'No leaks detected (this does not confirm a VPN is active)';
        let leakDetected = false;

        if (result.checks.webrtcLeak) {
            status = 'warning';
            message = 'WebRTC may be leaking your real IP';
            leakDetected = true;
        }

        if (result.checks.dnsLeak) {
            status = 'warning';
            message += (leakDetected ? '. DNS leak possible' : 'DNS leak possible');
            leakDetected = true;
        }

        return {
            status,
            message,
            details: {
                publicIP: result.publicIP,
                webrtcIPs: result.webrtc.ips,
                checks: result.checks,
                leakDetected
            }
        };
    },

    /**
     * Display test result
     */
    displayResult(testType, result) {
        const statusEl = document.getElementById(`${testType}-status`);
        const resultsEl = document.getElementById(`${testType}-results`);

        if (statusEl) {
            statusEl.textContent = result.status.toUpperCase();
            statusEl.className = `test-status ${result.status}`;
        }

        if (resultsEl) {
            let html = `<div class="result-message ${result.status}">${result.message}</div>`;
            
            // Add detailed results based on test type
            switch (testType) {
                case 'dns':
                    html += this.formatDNSResults(result.details);
                    break;
                case 'webrtc':
                    html += this.formatWebRTCResults(result.details);
                    break;
                case 'blocking':
                    html += this.formatBlockingResults(result.details);
                    break;
                case 'vpn':
                    html += this.formatVPNResults(result.details);
                    break;
            }

            resultsEl.innerHTML = html;
        }
    },

    /**
     * Display error
     */
    displayError(testType, error) {
        const statusEl = document.getElementById(`${testType}-status`);
        const resultsEl = document.getElementById(`${testType}-results`);

        if (statusEl) {
            statusEl.textContent = 'ERROR';
            statusEl.className = 'test-status fail';
        }

        if (resultsEl) {
            resultsEl.innerHTML = `<div class="result-error">Error: ${error.message}</div>`;
        }
    },

    /**
     * Format DNS results
     */
    formatDNSResults(details) {
        let html = '<div class="dns-results">';
        
        for (const result of details) {
            const icon = result.consistent ? '✓' : (result.inconclusive ? '❓' : '⚠️');
            html += `<div class="dns-domain">
                <strong>${result.domain}</strong>
                ${icon}${result.inconclusive ? ' <span class="text-warning">(all resolvers blocked/unreachable)</span>' : ''}
            </div>`;

            for (const [resolver, ips] of Object.entries(result.results)) {
                html += `<div class="dns-resolver">
                    ${resolver}: ${ips ? ips.join(', ') : 'failed'}
                </div>`;
            }
        }
        
        html += '</div>';
        return html;
    },

    /**
     * Format WebRTC results
     */
    formatWebRTCResults(details) {
        let html = '<div class="webrtc-results">';
        
        html += `<div>WebRTC Supported: ${details.supported ? 'Yes' : 'No'}</div>`;
        html += `<div>HTTP Public IP: ${details.httpIP || 'Unknown'}</div>`;
        
        if (details.publicIPs?.length) {
            html += `<div>WebRTC Public IPs: ${details.publicIPs.join(', ')}</div>`;
        }
        
        if (details.localIPs?.length) {
            html += `<div class="text-warning">Local IPs Exposed: ${details.localIPs.join(', ')}</div>`;
        }
        
        if (details.ipv6?.length) {
            html += `<div>IPv6: ${details.ipv6.join(', ')}</div>`;
        }
        
        html += '</div>';
        return html;
    },

    /**
     * Format blocking results
     */
    formatBlockingResults(details) {
        let html = `<div class="blocking-results">
            <div>Tested: ${details.total} sites | Reachable: ${details.reachable} | Blocked: ${details.blocked}</div>
            <div class="site-list">`;
        
        for (const site of details.sites) {
            const icon = site.reachable ? '✓' : '✗';
            const cls = site.reachable ? 'text-safe' : 'text-danger';
            const latency = site.latency ? ` (${site.latency}ms)` : '';
            html += `<div class="${cls}">${icon} ${site.name}${latency}</div>`;
        }
        
        html += '</div></div>';
        return html;
    },

    /**
     * Format VPN results
     */
    formatVPNResults(details) {
        let html = '<div class="vpn-results">';
        
        html += `<div>Public IP: ${details.publicIP || 'Unknown'}</div>`;
        
        if (details.webrtcIPs?.public?.length) {
            html += `<div>WebRTC IPs: ${details.webrtcIPs.public.join(', ')}</div>`;
        }
        
        html += '<div class="checks">';
        html += `<div>WebRTC Leak: ${details.checks.webrtcLeak ? '⚠️ Possible' : '✓ None detected'}</div>`;
        html += `<div>DNS Leak: ${details.checks.dnsLeak ? '⚠️ Possible' : '✓ None detected'}</div>`;
        html += '</div>';
        
        html += '</div>';
        return html;
    },

    /**
     * Get summary for dashboard
     */
    getSummary() {
        const hasResults = Object.keys(this.results).length > 0;
        
        if (!hasResults) {
            return {
                status: 'pending',
                icon: '⏳',
                value: 'Not tested'
            };
        }

        const statuses = Object.values(this.results).map(r => r.status);
        
        if (statuses.includes('fail')) {
            return {
                status: 'danger',
                icon: '🔴',
                value: 'Issues detected'
            };
        }
        
        if (statuses.includes('warning')) {
            return {
                status: 'warning',
                icon: '🟡',
                value: 'Some concerns'
            };
        }
        
        return {
            status: 'safe',
            icon: '🟢',
            value: 'Looking good'
        };
    }
};

// Export
window.CensorshipModule = CensorshipModule;
