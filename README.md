# USAFE - Internet Freedom & Privacy Toolkit

> **U**niversal **S**ecurity **A**nd **F**reedom **E**valuator
> 
> Client-side privacy & security analysis toolkit - No server, no tracking, runs entirely in your browser.

## 🎯 Overview

USAFE is a comprehensive, client-side web application that helps users understand and protect their digital privacy. Inspired by OTF (Open Technology Fund) categories: Internet Filtering, Surveillance Detection, and Secure Communications.

## 🏗️ Architecture

```
USAFE/
├── index.html              # Main entry point
├── css/
│   └── style.css           # Dark + light theme UI (CSS custom properties)
├── js/
│   ├── app.js              # Main application logic, theme + i18n
│   ├── modules/
│   │   ├── censorship.js   # Module 1: Censorship/Blocking Detector
│   │   ├── surveillance.js # Module 2: Surveillance/Tracking Detector  
│   │   └── secure-comm.js  # Module 3: Secure Communication Tool
│   └── utils/
│       ├── crypto.js       # Web Crypto API wrappers
│       ├── network.js      # Network testing utilities
│       ├── fingerprint.js  # Fingerprint detection
│       └── qrcode.js       # Vendored qrcode-generator (MIT) - no network calls
└── assets/
    └── icons/
```

Test-site lists, tracker patterns, and fingerprint-technique data live inline in
the relevant `js/utils/*.js` / `js/modules/*.js` files rather than as separate
`data/*.json` files - there's no loader that reads external data files, so
there's nothing to keep in sync between two places.

## 📦 Three Core Modules

### 1. 🚫 Censorship/Blocking Detector
**Goal:** Detect if sites/services are blocked in user's country/network

**Features:**
- DNS manipulation detection (compare multiple DNS resolvers)
- TCP connection blocking tests
- TLS/SNI blocking detection
- HTTP/HTTPS redirect manipulation check
- Known blocked sites database (updateable)
- WebRTC leak detection for VPN users
- Real IP vs reported IP comparison

**Techniques:**
```javascript
// DNS-over-HTTPS comparison
const dohResolvers = [
  'https://cloudflare-dns.com/dns-query',
  'https://dns.google/resolve',
  'https://dns.quad9.net/dns-query'
];

// Test if responses differ = potential DNS manipulation
```

### 2. 👁️ Surveillance/Tracking Detector
**Goal:** Show users how they're being tracked/fingerprinted

**Features:**
- Browser fingerprint uniqueness score
- Canvas fingerprint detection
- WebGL fingerprint detection
- AudioContext fingerprint detection
- Font enumeration detection
- Screen resolution & color depth
- Plugin/extension enumeration
- Timezone & language leaks
- Do Not Track header status
- Cookie & localStorage analysis
- Third-party tracker simulation
- Known tracker domain checking

**Techniques (AmIUnique/Cover Your Tracks style):**
```javascript
// Canvas fingerprinting detection
const canvas = document.createElement('canvas');
const ctx = canvas.getContext('2d');
ctx.textBaseline = 'top';
ctx.font = '14px Arial';
ctx.fillText('Browser fingerprint test', 2, 2);
const dataURL = canvas.toDataURL();
const hash = await crypto.subtle.digest('SHA-256', ...);
```

### 3. 🔐 Secure Communication Tool
**Goal:** End-to-end encrypted messaging with no server storage

**Features:**
- Client-side only encryption (Web Crypto API)
- Ephemeral key pairs (no permanent storage)
- QR code key exchange for in-person setup
- Time-limited self-destructing messages
- No accounts, no registration
- File encryption & secure sharing
- One-time pad option for paranoid mode

**Flow:**
```
1. User A generates ephemeral key pair
2. User A shares public key via QR/link
3. User B encrypts message with A's public key
4. Encrypted blob can be shared via any channel
5. Only User A can decrypt with private key
6. Keys expire after configurable time
```

## 🛡️ Technical Stack

- **Pure JavaScript** - No frameworks, one small vendored library (QR codes)
- **Web Crypto API** - Native browser encryption
- **No third-party servers** - Fingerprinting and encryption never leave your browser. The Censorship module is the deliberate exception: DNS-over-HTTPS resolvers, IP-lookup services, and the sites being tested are queried directly, because that's what those tests measure.
- **No cookies/tracking** - Zero telemetry
- **Progressive Web App** - Installable, works offline via a service worker
- **Dark + light theme** - Toggle in the header, persisted, follows OS preference by default

## 🎨 UI Design

- Modern dark theme (#0a0a0f background)
- Glassmorphism cards
- Real-time status indicators
- Traffic light risk scoring (🟢🟡🔴)
- Animated progress indicators
- Mobile-responsive

## 📊 Risk Scoring System

| Level | Color | Meaning |
|-------|-------|---------|
| Safe | 🟢 Green | Low fingerprint uniqueness, no blocking detected |
| Warning | 🟡 Yellow | Moderate risk, some trackers present |
| Danger | 🔴 Red | High uniqueness, blocking/manipulation detected |

## 🔧 Implementation Phases

### Phase 1: Foundation
- [x] Project structure
- [x] Basic HTML/CSS shell
- [x] Module loading system
- [x] Dark theme UI

### Phase 2: Censorship Detector
- [x] DNS-over-HTTPS comparison (with an explicit "inconclusive" state when every resolver is unreachable)
- [ ] TCP connectivity tests (not feasible from a browser sandbox - see the scope notice on the Censorship tab)
- [x] WebRTC IP leak detection
- [x] VPN leak check (does not detect VPN presence, only leaks)
- [x] Known blocked sites check

### Phase 3: Surveillance Detector
- [x] Canvas fingerprint (now also detects anti-fingerprint noise/randomization)
- [x] WebGL fingerprint
- [x] Audio fingerprint
- [x] Font enumeration
- [x] Screen/hardware info
- [x] Browser plugins
- [x] Uniqueness scoring (heuristic - see the caveat shown alongside the score)

### Phase 4: Secure Communication
- [x] Key generation (ECDH)
- [x] AES-GCM encryption
- [x] QR code key exchange
- [x] Message expiration (password mode)
- [x] File encryption

### Phase 5: Polish
- [x] PWA manifest
- [x] Service worker (offline)
- [x] Localization (TR/EN - persistent chrome and module headers; in-test result strings are English-only)
- [x] Export reports
- [ ] Share results

## 🚀 Usage

```bash
# Just open in browser - no server needed!
open index.html

# Or serve locally
python -m http.server 8080
# Then visit http://localhost:8080
```

## 📚 Inspirations & References

- **OONI Probe** - Network interference measurement. OONI's own [Probe Web announcement](https://ooni.org/post/introducing-ooni-probe-web/) is explicit that browser-based measurement has real false-positive/negative limits and isn't a replacement for their native apps - USAFE's Censorship module inherits the same limits and says so on the tab.
- **AmIUnique** / **Cover Your Tracks (EFF)** - Browser fingerprinting research. Both calibrate uniqueness against a real collected population sample; USAFE's uniqueness score is a simpler, uncalibrated heuristic and is labeled as such in the UI.
- **PrivateBin** - Zero-knowledge, client-side-encrypted sharing (AES-GCM, key never touches the server). Close in spirit to USAFE's password-based message encryption.
- **BrowserLeaks** - Browser security testing
- **privacytools.io** - Privacy tool recommendations

## ⚖️ License

MIT License - Free as in freedom.

---

**USAFE** - Know your digital footprint. Protect your privacy.
