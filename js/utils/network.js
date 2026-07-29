/**
 * USAFE - Network Utilities
 * DNS testing, connectivity checks, WebRTC leak detection
 */

const USAFENetwork = {
    /**
     * Get user's public IP address
     */
    async getPublicIP() {
        const services = [
            'https://api.ipify.org?format=json',
            'https://api.ip.sb/ip',
            'https://ifconfig.me/ip'
        ];

        for (const service of services) {
            try {
                const response = await fetch(service);
                const data = await response.text();
                
                // Try to parse as JSON first
                try {
                    const json = JSON.parse(data);
                    return json.ip || data.trim();
                } catch {
                    return data.trim();
                }
            } catch (e) {
                continue;
            }
        }
        return null;
    },

    /**
     * Detect WebRTC IP leak
     */
    async detectWebRTCLeak() {
        return new Promise((resolve) => {
            const ips = {
                local: [],
                public: [],
                ipv6: []
            };

            if (!window.RTCPeerConnection) {
                resolve({ supported: false, ips: ips });
                return;
            }

            const pc = new RTCPeerConnection({
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
            });

            pc.createDataChannel('');

            pc.onicecandidate = (e) => {
                if (!e.candidate) {
                    pc.close();
                    resolve({ supported: true, ips: ips });
                    return;
                }

                const candidate = e.candidate.candidate;
                
                // Extract IP addresses from candidate
                const ipRegex = /([0-9]{1,3}\.){3}[0-9]{1,3}/g;
                const ipv6Regex = /([a-f0-9:]+:+)+[a-f0-9]+/gi;
                
                const ipv4Matches = candidate.match(ipRegex);
                const ipv6Matches = candidate.match(ipv6Regex);

                if (ipv4Matches) {
                    ipv4Matches.forEach(ip => {
                        if (ip.startsWith('10.') || ip.startsWith('192.168.') || ip.startsWith('172.')) {
                            if (!ips.local.includes(ip)) ips.local.push(ip);
                        } else {
                            if (!ips.public.includes(ip)) ips.public.push(ip);
                        }
                    });
                }

                if (ipv6Matches) {
                    ipv6Matches.forEach(ip => {
                        if (!ips.ipv6.includes(ip)) ips.ipv6.push(ip);
                    });
                }
            };

            pc.createOffer()
                .then(offer => pc.setLocalDescription(offer))
                .catch(() => {
                    resolve({ supported: false, ips: ips, error: 'Failed to create offer' });
                });

            // Timeout after 5 seconds
            setTimeout(() => {
                pc.close();
                resolve({ supported: true, ips: ips, timeout: true });
            }, 5000);
        });
    },

    /**
     * DNS over HTTPS query.
     *
     * Has an explicit timeout - without one, a resolver that never responds
     * (verified: dns.quad9.net hangs indefinitely from some networks/sandboxes
     * with no error at all, not even a fast rejection) hangs the ENTIRE DNS
     * test forever via Promise.all in compareDNS(), with no feedback to the
     * user. This matters more than usual here: DoH resolvers are exactly the
     * kind of endpoint censorship regimes block, so "the resolver never
     * responds" is a realistic, expected outcome for USAFE's actual users,
     * not just a sandbox artifact - it must degrade to "unreachable", not hang.
     */
    async dohQuery(domain, resolver = 'cloudflare', timeoutMs = 6000) {
        const resolvers = {
            cloudflare: 'https://cloudflare-dns.com/dns-query',
            google: 'https://dns.google/resolve',
            quad9: 'https://dns.quad9.net/dns-query' // standard DoH port (443) - :5053 is not a valid DoH port for Quad9 and just times out
        };

        const url = resolvers[resolver] || resolver;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const params = new URLSearchParams({
                name: domain,
                type: 'A'
            });

            const response = await fetch(`${url}?${params}`, {
                headers: {
                    'Accept': 'application/dns-json'
                },
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            return {
                success: true,
                resolver: resolver,
                domain: domain,
                answers: data.Answer || [],
                status: data.Status
            };
        } catch (error) {
            return {
                success: false,
                resolver: resolver,
                domain: domain,
                error: error.name === 'AbortError' ? 'timeout' : error.message
            };
        } finally {
            clearTimeout(timeoutId);
        }
    },

    /**
     * Compare DNS responses from multiple resolvers
     */
    async compareDNS(domain) {
        const resolvers = ['cloudflare', 'google', 'quad9'];
        const results = await Promise.all(
            resolvers.map(r => this.dohQuery(domain, r))
        );

        // Extract IPs from each resolver
        const ipsByResolver = {};
        results.forEach(r => {
            if (r.success && r.answers) {
                ipsByResolver[r.resolver] = r.answers
                    .filter(a => a.type === 1)
                    .map(a => a.data)
                    .sort();
            } else {
                ipsByResolver[r.resolver] = null;
            }
        });

        // Check for discrepancies
        const allIps = Object.values(ipsByResolver).filter(Boolean);
        const allSame = allIps.every(ips =>
            JSON.stringify(ips) === JSON.stringify(allIps[0])
        );

        // If every DoH resolver failed, this is NOT the same as "consistent" -
        // it's inconclusive, and in many censorship regimes it's actually the
        // most likely outcome, since Cloudflare/Google/Quad9's DoH endpoints
        // are themselves commonly blocked. Reporting this as "clean" would be
        // a false negative at exactly the moment a user is most censored.
        const allFailed = allIps.length === 0;

        return {
            domain: domain,
            results: ipsByResolver,
            consistent: allSame && !allFailed,
            inconclusive: allFailed,
            manipulation: !allSame && allIps.length > 1
        };
    },

    /**
     * Test if a URL is reachable
     */
    async testConnectivity(url, timeout = 10000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const startTime = performance.now();
            const response = await fetch(url, {
                method: 'HEAD',
                mode: 'no-cors',
                signal: controller.signal
            });
            const endTime = performance.now();

            clearTimeout(timeoutId);
            
            return {
                url: url,
                reachable: true,
                latency: Math.round(endTime - startTime),
                status: response.status || 'opaque'
            };
        } catch (error) {
            clearTimeout(timeoutId);
            return {
                url: url,
                reachable: false,
                error: error.name === 'AbortError' ? 'timeout' : error.message
            };
        }
    },

    /**
     * Test multiple sites for blocking
     */
    async testSites(sites) {
        const results = await Promise.all(
            sites.map(site => this.testConnectivity(site.url))
        );

        return sites.map((site, i) => ({
            ...site,
            ...results[i]
        }));
    },

    /**
     * Common sites to test for blocking
     */
    getTestSites() {
        return [
            { name: 'Google', url: 'https://www.google.com', category: 'search' },
            { name: 'YouTube', url: 'https://www.youtube.com', category: 'video' },
            { name: 'Twitter/X', url: 'https://twitter.com', category: 'social' },
            { name: 'Facebook', url: 'https://www.facebook.com', category: 'social' },
            { name: 'Wikipedia', url: 'https://www.wikipedia.org', category: 'reference' },
            { name: 'GitHub', url: 'https://github.com', category: 'tech' },
            { name: 'Reddit', url: 'https://www.reddit.com', category: 'social' },
            { name: 'Cloudflare', url: 'https://www.cloudflare.com', category: 'tech' },
            { name: 'Telegram', url: 'https://telegram.org', category: 'messaging' },
            { name: 'Signal', url: 'https://signal.org', category: 'messaging' },
            { name: 'ProtonMail', url: 'https://proton.me', category: 'email' },
            { name: 'Tor Project', url: 'https://www.torproject.org', category: 'privacy' }
        ];
    },

    /**
     * Detect VPN usage (heuristic)
     */
    async detectVPN() {
        const checks = {
            webrtcLeak: false,
            ipMismatch: false,
            commonVPNPorts: false,
            dnsLeak: false
        };

        // Check WebRTC
        const webrtc = await this.detectWebRTCLeak();
        const publicIP = await this.getPublicIP();

        if (webrtc.supported && webrtc.ips.public.length > 0) {
            // If WebRTC shows a different IP than the HTTP IP
            if (publicIP && !webrtc.ips.public.includes(publicIP)) {
                checks.webrtcLeak = true;
            }
        }

        // Check if IP looks like a known VPN range (basic heuristic)
        // This is simplified - real detection would use IP reputation databases
        const vpnIndicators = {
            likelyVPN: false,
            reasons: []
        };

        // Check DNS consistency
        const dnsCheck = await this.compareDNS('google.com');
        if (!dnsCheck.consistent) {
            checks.dnsLeak = true;
            vpnIndicators.reasons.push('DNS responses inconsistent');
        }

        return {
            publicIP: publicIP,
            webrtc: webrtc,
            checks: checks,
            indicators: vpnIndicators
        };
    },

    /**
     * Get browser info
     */
    getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown';
        let version = '';

        if (ua.includes('Firefox/')) {
            browser = 'Firefox';
            version = ua.match(/Firefox\/([0-9.]+)/)?.[1] || '';
        } else if (ua.includes('Chrome/')) {
            if (ua.includes('Edg/')) {
                browser = 'Edge';
                version = ua.match(/Edg\/([0-9.]+)/)?.[1] || '';
            } else if (ua.includes('OPR/')) {
                browser = 'Opera';
                version = ua.match(/OPR\/([0-9.]+)/)?.[1] || '';
            } else {
                browser = 'Chrome';
                version = ua.match(/Chrome\/([0-9.]+)/)?.[1] || '';
            }
        } else if (ua.includes('Safari/') && !ua.includes('Chrome')) {
            browser = 'Safari';
            version = ua.match(/Version\/([0-9.]+)/)?.[1] || '';
        }

        return { browser, version, userAgent: ua };
    },

    /**
     * Get OS info
     */
    getOSInfo() {
        const ua = navigator.userAgent;
        let os = 'Unknown';
        let version = '';

        if (ua.includes('Windows NT 10')) {
            os = 'Windows';
            version = '10/11';
        } else if (ua.includes('Windows NT 6.3')) {
            os = 'Windows';
            version = '8.1';
        } else if (ua.includes('Windows NT 6.2')) {
            os = 'Windows';
            version = '8';
        } else if (ua.includes('Windows NT 6.1')) {
            os = 'Windows';
            version = '7';
        } else if (ua.includes('Mac OS X')) {
            os = 'macOS';
            version = ua.match(/Mac OS X ([0-9_]+)/)?.[1]?.replace(/_/g, '.') || '';
        } else if (ua.includes('Linux')) {
            os = 'Linux';
            if (ua.includes('Android')) {
                os = 'Android';
                version = ua.match(/Android ([0-9.]+)/)?.[1] || '';
            }
        } else if (ua.includes('iPhone') || ua.includes('iPad')) {
            os = 'iOS';
            version = ua.match(/OS ([0-9_]+)/)?.[1]?.replace(/_/g, '.') || '';
        }

        return { os, version, platform: navigator.platform };
    }
};

// Export for use
window.USAFENetwork = USAFENetwork;
