/**
 * USAFE - Secure Communication Module
 * End-to-end encrypted messaging and file encryption
 */

const SecureCommModule = {
    keyPair: null,

    /**
     * Initialize the module
     */
    init() {
        this.bindEvents();
        this.checkCryptoSupport();
    },

    /**
     * Check Web Crypto API support
     */
    checkCryptoSupport() {
        if (!USAFECrypto.isAvailable()) {
            this.showError('Web Crypto API is not available. Encryption features will not work.');
        }
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Tab switching
        document.querySelectorAll('.comm-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Encryption method toggle
        document.querySelectorAll('input[name="encrypt-method"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.toggleEncryptionMethod(e.target.value);
            });
        });

        // Password visibility toggles
        document.querySelectorAll('.show-password').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const input = e.target.previousElementSibling;
                input.type = input.type === 'password' ? 'text' : 'password';
                e.target.textContent = input.type === 'password' ? '👁️' : '🙈';
            });
        });

        // Password generators
        document.querySelectorAll('.generate-password').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const input = e.target.closest('.password-input').querySelector('input');
                input.value = USAFECrypto.generatePassword();
                input.type = 'text';
                this.updatePasswordStrength(input);
            });
        });

        // Password strength
        document.getElementById('encrypt-password')?.addEventListener('input', (e) => {
            this.updatePasswordStrength(e.target);
        });

        // Expiry checkbox
        document.getElementById('add-expiry')?.addEventListener('change', (e) => {
            document.getElementById('expiry-options').style.display = e.target.checked ? 'block' : 'none';
        });

        // Encrypt button
        document.getElementById('encrypt-btn')?.addEventListener('click', () => {
            this.encryptMessage();
        });

        // Decrypt button
        document.getElementById('decrypt-btn')?.addEventListener('click', () => {
            this.decryptMessage();
        });

        // Copy buttons
        document.getElementById('copy-encrypted')?.addEventListener('click', () => {
            this.copyToClipboard('encrypted-result');
        });

        document.getElementById('copy-pubkey')?.addEventListener('click', () => {
            this.copyToClipboard('my-pubkey');
        });

        // QR code display
        document.getElementById('qr-encrypted')?.addEventListener('click', () => {
            this.showQRCode(document.getElementById('encrypted-result').value, 'Encrypted Message');
        });

        document.getElementById('show-qr-key')?.addEventListener('click', () => {
            this.showQRCode(document.getElementById('my-pubkey').value, 'Your Public Key');
        });

        // Key pair generation
        document.getElementById('generate-keypair')?.addEventListener('click', () => {
            this.generateKeyPair();
        });

        document.getElementById('new-keypair')?.addEventListener('click', () => {
            this.generateKeyPair();
        });

        // File handling
        this.initFileHandling();
    },

    /**
     * Switch between tabs
     */
    switchTab(tabId) {
        // Update tab buttons
        document.querySelectorAll('.comm-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });

        // Update panels
        document.querySelectorAll('.comm-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `${tabId}-panel`);
        });
    },

    /**
     * Toggle encryption method UI
     */
    toggleEncryptionMethod(method) {
        document.getElementById('password-group').style.display = method === 'password' ? 'block' : 'none';
        document.getElementById('keypair-group').style.display = method === 'keypair' ? 'block' : 'none';
    },

    /**
     * Update password strength indicator
     */
    updatePasswordStrength(input) {
        const strength = USAFECrypto.checkPasswordStrength(input.value);
        const strengthEl = document.getElementById('password-strength');
        
        if (strengthEl) {
            strengthEl.style.setProperty('--strength', `${strength.percent}%`);
            strengthEl.style.setProperty('--strength-color', strength.color);
            strengthEl.title = `${strength.level}: ${strength.feedback.join(', ') || 'Strong password!'}`;
        }
    },

    /**
     * Encrypt message
     */
    async encryptMessage() {
        const message = document.getElementById('encrypt-message').value.trim();
        const method = document.querySelector('input[name="encrypt-method"]:checked').value;
        
        if (!message) {
            alert('Please enter a message to encrypt');
            return;
        }

        try {
            let encrypted;
            
            if (method === 'password') {
                const password = document.getElementById('encrypt-password').value;
                if (!password) {
                    alert('Please enter a password');
                    return;
                }
                
                // Add metadata
                const payload = {
                    m: message,
                    t: Date.now(),
                    v: 1
                };
                
                // Check for expiry
                if (document.getElementById('add-expiry').checked) {
                    const expirySeconds = parseInt(document.getElementById('expiry-time').value);
                    payload.e = Date.now() + (expirySeconds * 1000);
                }
                
                encrypted = await USAFECrypto.encryptWithPassword(JSON.stringify(payload), password);
                encrypted = 'USAFE:1:' + encrypted; // Version prefix
                
            } else {
                // Key pair encryption
                const recipientKey = document.getElementById('recipient-pubkey').value.trim();
                if (!recipientKey) {
                    alert('Please enter recipient\'s public key');
                    return;
                }
                
                if (!this.keyPair) {
                    await this.generateKeyPair();
                }

                encrypted = await USAFECrypto.encryptWithPublicKey(message, recipientKey, this.keyPair.keyPair);
                encrypted = 'USAFE:2:' + encrypted;
            }

            // Show result
            document.getElementById('encrypt-output').style.display = 'block';
            document.getElementById('encrypted-result').value = encrypted;

        } catch (error) {
            alert(`Encryption failed: ${error.message}`);
        }
    },

    /**
     * Decrypt message
     */
    async decryptMessage() {
        const encrypted = document.getElementById('decrypt-input').value.trim();
        const password = document.getElementById('decrypt-password').value;

        if (!encrypted) {
            alert('Please enter an encrypted message');
            return;
        }

        try {
            // Check version prefix
            if (!encrypted.startsWith('USAFE:')) {
                throw new Error('Invalid USAFE encrypted message format');
            }

            const parts = encrypted.split(':');
            const version = parts[1];
            const data = parts.slice(2).join(':');

            let decrypted;
            
            if (version === '1') {
                // Password-based
                if (!password) {
                    alert('Please enter the password');
                    return;
                }
                
                const result = await USAFECrypto.decryptWithPassword(data, password);
                if (!result.success) {
                    throw new Error(result.error);
                }
                
                // Parse payload
                const payload = JSON.parse(result.data);
                
                // Check expiry
                if (payload.e && Date.now() > payload.e) {
                    throw new Error('This message has expired');
                }
                
                decrypted = {
                    message: payload.m,
                    timestamp: new Date(payload.t).toLocaleString(),
                    expiry: payload.e ? new Date(payload.e).toLocaleString() : null
                };
                
            } else if (version === '2') {
                // Key pair (ECDH) - resolve which private key to decrypt with:
                // prefer a pasted key (JWK JSON) so users can decrypt on a
                // different device/session than the one that generated the
                // key pair; otherwise fall back to this session's ephemeral key.
                let privateKey;
                const pastedKey = password.trim();

                if (pastedKey) {
                    try {
                        privateKey = await USAFECrypto.importPrivateKey(pastedKey);
                    } catch (e) {
                        throw new Error('Could not read the private key - paste the exact key pair JSON');
                    }
                } else if (this.keyPair) {
                    privateKey = this.keyPair.keyPair.privateKey;
                } else {
                    throw new Error('No private key available - paste your private key or generate a key pair first');
                }

                const result = await USAFECrypto.decryptWithPrivateKey(data, privateKey);
                if (!result.success) {
                    throw new Error(result.error);
                }

                decrypted = {
                    message: result.data,
                    timestamp: null,
                    expiry: null
                };

            } else {
                throw new Error('Unknown encryption version');
            }

            // Show result
            document.getElementById('decrypt-output').style.display = 'block';
            document.getElementById('decrypted-result').textContent = decrypted.message;
            
            let meta = decrypted.timestamp ? `Encrypted: ${decrypted.timestamp}` : 'Decrypted with ECDH key pair (no timestamp embedded)';
            if (decrypted.expiry) {
                meta += ` • Expires: ${decrypted.expiry}`;
            }
            document.getElementById('message-meta').textContent = meta;

        } catch (error) {
            alert(`Decryption failed: ${error.message}`);
        }
    },

    /**
     * Render a QR code for the given text into the shared QR modal.
     * QR codes need light modules on a dark background (or vice versa) with
     * real contrast to scan reliably, independent of the app's dark theme -
     * so the code is always rendered on a plain white tile.
     */
    showQRCode(text, title) {
        const display = document.getElementById('qr-display');
        if (!display) return;

        if (!text || !text.trim()) {
            alert('Nothing to encode yet - generate/encrypt first');
            return;
        }

        display.innerHTML = '';

        // qrcode-generator throws once the payload exceeds the largest
        // symbol size (type 40) for the chosen error-correction level -
        // step typeNumber up from auto-detect(0) and report clearly if it
        // still doesn't fit, rather than letting the exception bubble up.
        let qr;
        try {
            qr = qrcode(0, 'M');
            qr.addData(text);
            qr.make();
        } catch (e) {
            display.innerHTML = `<p class="qr-error">Too much data for a QR code (${text.length} characters). Use "Copy" and share the text directly instead.</p>`;
            document.getElementById('qr-modal').querySelector('h3').textContent = title || 'QR Code';
            USAFE.showModal('qr-modal');
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'qr-code-tile';
        wrapper.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 4, scalable: true });
        display.appendChild(wrapper);

        const caption = document.createElement('p');
        caption.className = 'qr-caption';
        caption.textContent = title || '';
        display.appendChild(caption);

        document.getElementById('qr-modal').querySelector('h3').textContent = '📱 ' + (title || 'QR Code');
        USAFE.showModal('qr-modal');
    },

    /**
     * Generate new key pair
     */
    async generateKeyPair() {
        try {
            this.keyPair = await USAFECrypto.generateKeyPair();
            document.getElementById('my-pubkey').value = this.keyPair.publicKey;
        } catch (error) {
            alert(`Key generation failed: ${error.message}`);
        }
    },

    /**
     * Copy to clipboard
     */
    async copyToClipboard(elementId) {
        const element = document.getElementById(elementId);
        const text = element.value || element.textContent;
        
        try {
            await navigator.clipboard.writeText(text);
            // Show feedback
            const btn = document.querySelector(`[id$="copy-${elementId.replace('-result', '').replace('my-', '')}"], #copy-${elementId.split('-')[0]}`);
            if (btn) {
                const originalText = btn.textContent;
                btn.textContent = '✓ Copied!';
                setTimeout(() => { btn.textContent = originalText; }, 2000);
            }
        } catch (error) {
            // Fallback
            element.select();
            document.execCommand('copy');
        }
    },

    /**
     * Initialize file handling
     */
    initFileHandling() {
        const dropZone = document.getElementById('file-drop-zone');
        const fileInput = document.getElementById('file-input');
        
        if (!dropZone || !fileInput) return;

        // Click to select
        dropZone.addEventListener('click', () => fileInput.click());

        // Drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });

        // Encrypt/Decrypt file buttons
        document.getElementById('encrypt-file-btn')?.addEventListener('click', () => {
            this.encryptFile();
        });

        document.getElementById('decrypt-file-btn')?.addEventListener('click', () => {
            this.decryptFile();
        });
    },

    selectedFile: null,

    /**
     * Handle selected file
     */
    handleFile(file) {
        this.selectedFile = file;
        
        document.getElementById('file-info').style.display = 'flex';
        document.getElementById('file-name').textContent = file.name;
        document.getElementById('file-size').textContent = this.formatFileSize(file.size);
        
        // Enable buttons
        const isEncrypted = file.name.endsWith('.usafe');
        document.getElementById('encrypt-file-btn').disabled = isEncrypted;
        document.getElementById('decrypt-file-btn').disabled = !isEncrypted;
    },

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    /**
     * Encrypt file
     */
    async encryptFile() {
        if (!this.selectedFile) return;

        const password = document.getElementById('file-password').value;
        if (!password) {
            alert('Please enter a password');
            return;
        }

        const progressEl = document.getElementById('file-progress');
        const progressFill = document.getElementById('file-progress-fill');
        const progressText = document.getElementById('file-progress-text');

        progressEl.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = 'Encrypting...';

        try {
            const result = await USAFECrypto.encryptFile(this.selectedFile, password, (percent) => {
                progressFill.style.width = `${percent}%`;
                progressText.textContent = `Encrypting... ${percent}%`;
            });

            // Download encrypted file
            const url = URL.createObjectURL(result.blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.filename;
            a.click();
            URL.revokeObjectURL(url);

            progressText.textContent = 'Encryption complete!';
            setTimeout(() => { progressEl.style.display = 'none'; }, 2000);

        } catch (error) {
            progressText.textContent = `Error: ${error.message}`;
        }
    },

    /**
     * Decrypt file
     */
    async decryptFile() {
        if (!this.selectedFile) return;

        const password = document.getElementById('file-password').value;
        if (!password) {
            alert('Please enter the password');
            return;
        }

        const progressEl = document.getElementById('file-progress');
        const progressFill = document.getElementById('file-progress-fill');
        const progressText = document.getElementById('file-progress-text');

        progressEl.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = 'Decrypting...';

        try {
            const result = await USAFECrypto.decryptFile(this.selectedFile, password, (percent) => {
                progressFill.style.width = `${percent}%`;
                progressText.textContent = `Decrypting... ${percent}%`;
            });

            // Download decrypted file
            const url = URL.createObjectURL(result.blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.filename;
            a.click();
            URL.revokeObjectURL(url);

            progressText.textContent = 'Decryption complete!';
            setTimeout(() => { progressEl.style.display = 'none'; }, 2000);

        } catch (error) {
            progressText.textContent = `Error: ${error.message}`;
        }
    },

    /**
     * Show error message
     */
    showError(message) {
        const panel = document.querySelector('.comm-panel.active .card');
        if (panel) {
            const error = document.createElement('div');
            error.className = 'error-message';
            error.style.cssText = 'background: var(--status-danger); color: white; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;';
            error.textContent = message;
            panel.insertBefore(error, panel.firstChild);
        }
    },

    /**
     * Get summary for dashboard
     */
    getSummary() {
        const supported = USAFECrypto.isAvailable();
        
        return {
            status: supported ? 'safe' : 'danger',
            icon: supported ? '🟢' : '🔴',
            value: supported ? 'Available' : 'Not supported'
        };
    }
};

// Export
window.SecureCommModule = SecureCommModule;
