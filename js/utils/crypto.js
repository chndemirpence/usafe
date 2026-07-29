/**
 * USAFE - Crypto Utilities
 * Web Crypto API wrappers for encryption/decryption
 */

const USAFECrypto = {
    /**
     * Check if Web Crypto API is available
     */
    isAvailable() {
        return !!(window.crypto && window.crypto.subtle);
    },

    /**
     * Generate a random password
     */
    generatePassword(length = 24) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
        const array = new Uint8Array(length);
        crypto.getRandomValues(array);
        return Array.from(array, byte => chars[byte % chars.length]).join('');
    },

    /**
     * Generate random bytes as hex string
     */
    randomHex(bytes = 16) {
        const array = new Uint8Array(bytes);
        crypto.getRandomValues(array);
        return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
    },

    /**
     * Calculate SHA-256 hash
     */
    async sha256(data) {
        const encoder = new TextEncoder();
        const dataBuffer = typeof data === 'string' ? encoder.encode(data) : data;
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    },

    /**
     * Derive encryption key from password using PBKDF2.
     * 600,000 iterations follows OWASP's current PBKDF2-SHA256 guidance
     * (the old default of 100,000 is well below that).
     */
    async deriveKey(password, salt, iterations = 600000) {
        const encoder = new TextEncoder();
        const passwordBuffer = encoder.encode(password);
        
        // Import password as raw key
        const baseKey = await crypto.subtle.importKey(
            'raw',
            passwordBuffer,
            'PBKDF2',
            false,
            ['deriveKey']
        );

        // Derive AES-GCM key
        const derivedKey = await crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: salt,
                iterations: iterations,
                hash: 'SHA-256'
            },
            baseKey,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );

        return derivedKey;
    },

    /**
     * Encrypt message with password (AES-256-GCM)
     */
    async encryptWithPassword(message, password) {
        const encoder = new TextEncoder();
        const data = encoder.encode(message);
        
        // Generate random salt and IV
        const salt = crypto.getRandomValues(new Uint8Array(16));
        const iv = crypto.getRandomValues(new Uint8Array(12));
        
        // Derive key from password
        const key = await this.deriveKey(password, salt);
        
        // Encrypt
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            data
        );

        // Combine salt + iv + ciphertext
        const combined = new Uint8Array(salt.length + iv.length + encrypted.byteLength);
        combined.set(salt, 0);
        combined.set(iv, salt.length);
        combined.set(new Uint8Array(encrypted), salt.length + iv.length);

        // Return as base64
        return this.bytesToBase64(combined);
    },

    /**
     * Decrypt message with password
     */
    async decryptWithPassword(encryptedBase64, password) {
        try {
            // Decode base64
            const combined = Uint8Array.from(atob(encryptedBase64), c => c.charCodeAt(0));
            
            // Extract salt, iv, ciphertext
            const salt = combined.slice(0, 16);
            const iv = combined.slice(16, 28);
            const ciphertext = combined.slice(28);

            // Derive key from password
            const key = await this.deriveKey(password, salt);

            // Decrypt
            const decrypted = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: iv },
                key,
                ciphertext
            );

            const decoder = new TextDecoder();
            return { success: true, data: decoder.decode(decrypted) };
        } catch (error) {
            return { success: false, error: 'Decryption failed. Wrong password?' };
        }
    },

    /**
     * Generate ECDH key pair for key exchange
     */
    async generateKeyPair() {
        const keyPair = await crypto.subtle.generateKey(
            {
                name: 'ECDH',
                namedCurve: 'P-256'
            },
            true,
            ['deriveKey']
        );

        // Export public key
        const publicKeyRaw = await crypto.subtle.exportKey('raw', keyPair.publicKey);
        const publicKeyB64 = this.bytesToBase64(new Uint8Array(publicKeyRaw));

        // Export private key
        const privateKeyJwk = await crypto.subtle.exportKey('jwk', keyPair.privateKey);

        return {
            publicKey: publicKeyB64,
            privateKey: JSON.stringify(privateKeyJwk),
            keyPair: keyPair
        };
    },

    /**
     * Import public key from base64
     */
    async importPublicKey(publicKeyB64) {
        const publicKeyRaw = Uint8Array.from(atob(publicKeyB64), c => c.charCodeAt(0));
        return await crypto.subtle.importKey(
            'raw',
            publicKeyRaw,
            { name: 'ECDH', namedCurve: 'P-256' },
            false,
            []
        );
    },

    /**
     * Import private key from JWK string
     */
    async importPrivateKey(privateKeyJson) {
        const jwk = JSON.parse(privateKeyJson);
        return await crypto.subtle.importKey(
            'jwk',
            jwk,
            { name: 'ECDH', namedCurve: 'P-256' },
            false,
            ['deriveKey']
        );
    },

    /**
     * Derive shared secret from ECDH key exchange
     */
    async deriveSharedKey(privateKey, publicKey) {
        return await crypto.subtle.deriveKey(
            {
                name: 'ECDH',
                public: publicKey
            },
            privateKey,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );
    },

    /**
     * Encrypt with ECDH (using recipient's public key)
     * The sender's own public key is embedded in the output so the recipient
     * can derive the same shared secret with their private key alone -
     * without this, ECDH decryption is impossible (there is no way to
     * re-derive the shared secret without the sender's public key).
     */
    async encryptWithPublicKey(message, recipientPublicKeyB64, senderKeyPair) {
        const encoder = new TextEncoder();
        const data = encoder.encode(message);
        const iv = crypto.getRandomValues(new Uint8Array(12));

        // Import recipient's public key
        const recipientPublicKey = await this.importPublicKey(recipientPublicKeyB64);

        // Derive shared secret
        const sharedKey = await this.deriveSharedKey(senderKeyPair.privateKey, recipientPublicKey);

        // Encrypt
        const encrypted = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            sharedKey,
            data
        );

        // Export sender's raw public key (P-256 uncompressed point = 65 bytes)
        const senderPublicKeyRaw = new Uint8Array(
            await crypto.subtle.exportKey('raw', senderKeyPair.publicKey)
        );

        // Combine senderPublicKey + iv + ciphertext
        const combined = new Uint8Array(senderPublicKeyRaw.length + iv.length + encrypted.byteLength);
        combined.set(senderPublicKeyRaw, 0);
        combined.set(iv, senderPublicKeyRaw.length);
        combined.set(new Uint8Array(encrypted), senderPublicKeyRaw.length + iv.length);

        return this.bytesToBase64(combined);
    },

    /**
     * Decrypt an ECDH-encrypted message using the recipient's private key.
     * Reads the sender's public key back out of the payload (see
     * encryptWithPublicKey) to re-derive the same shared secret.
     */
    async decryptWithPrivateKey(encryptedB64, recipientPrivateKey) {
        try {
            const combined = this.base64ToBytes(encryptedB64);

            const senderPublicKeyRaw = combined.slice(0, 65); // P-256 uncompressed point
            const iv = combined.slice(65, 65 + 12);
            const ciphertext = combined.slice(65 + 12);

            const senderPublicKey = await crypto.subtle.importKey(
                'raw',
                senderPublicKeyRaw,
                { name: 'ECDH', namedCurve: 'P-256' },
                false,
                []
            );

            const sharedKey = await this.deriveSharedKey(recipientPrivateKey, senderPublicKey);

            const decrypted = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: iv },
                sharedKey,
                ciphertext
            );

            const decoder = new TextDecoder();
            return { success: true, data: decoder.decode(decrypted) };
        } catch (error) {
            return { success: false, error: 'Decryption failed. Wrong key?' };
        }
    },

    /**
     * Base64-encode a Uint8Array without spreading it into function
     * arguments (String.fromCharCode(...bytes) throws "Maximum call stack
     * size exceeded" on large inputs - chunk it instead).
     */
    bytesToBase64(bytes) {
        const chunkSize = 8192;
        let binary = '';
        for (let i = 0; i < bytes.length; i += chunkSize) {
            binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
        }
        return btoa(binary);
    },

    /**
     * Decode a base64 string back to a Uint8Array.
     */
    base64ToBytes(base64) {
        return Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    },

    /**
     * Encrypt a file with password
     */
    async encryptFile(file, password, onProgress) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    
                    // Generate salt and IV
                    const salt = crypto.getRandomValues(new Uint8Array(16));
                    const iv = crypto.getRandomValues(new Uint8Array(12));
                    
                    // Derive key
                    const key = await this.deriveKey(password, salt);
                    
                    if (onProgress) onProgress(30);
                    
                    // Encrypt
                    const encrypted = await crypto.subtle.encrypt(
                        { name: 'AES-GCM', iv: iv },
                        key,
                        data
                    );
                    
                    if (onProgress) onProgress(70);
                    
                    // Create header with metadata
                    const metadata = JSON.stringify({
                        name: file.name,
                        type: file.type,
                        size: file.size,
                        encrypted: Date.now()
                    });
                    const metadataBytes = new TextEncoder().encode(metadata);
                    const metadataLen = new Uint8Array(4);
                    new DataView(metadataLen.buffer).setUint32(0, metadataBytes.length);
                    
                    // Combine: metadataLen + metadata + salt + iv + ciphertext
                    const combined = new Uint8Array(
                        4 + metadataBytes.length + salt.length + iv.length + encrypted.byteLength
                    );
                    let offset = 0;
                    combined.set(metadataLen, offset); offset += 4;
                    combined.set(metadataBytes, offset); offset += metadataBytes.length;
                    combined.set(salt, offset); offset += salt.length;
                    combined.set(iv, offset); offset += iv.length;
                    combined.set(new Uint8Array(encrypted), offset);
                    
                    if (onProgress) onProgress(100);
                    
                    // Create blob
                    const blob = new Blob([combined], { type: 'application/octet-stream' });
                    resolve({
                        blob: blob,
                        filename: file.name + '.usafe'
                    });
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = () => reject(reader.error);
            reader.readAsArrayBuffer(file);
        });
    },

    /**
     * Decrypt a file with password
     */
    async decryptFile(file, password, onProgress) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    let offset = 0;
                    
                    // Read metadata length
                    const metadataLen = new DataView(data.buffer).getUint32(0);
                    offset += 4;
                    
                    // Read metadata
                    const metadataBytes = data.slice(offset, offset + metadataLen);
                    const metadata = JSON.parse(new TextDecoder().decode(metadataBytes));
                    offset += metadataLen;
                    
                    // Read salt and IV
                    const salt = data.slice(offset, offset + 16);
                    offset += 16;
                    const iv = data.slice(offset, offset + 12);
                    offset += 12;
                    
                    // Read ciphertext
                    const ciphertext = data.slice(offset);
                    
                    if (onProgress) onProgress(30);
                    
                    // Derive key
                    const key = await this.deriveKey(password, salt);
                    
                    if (onProgress) onProgress(50);
                    
                    // Decrypt
                    const decrypted = await crypto.subtle.decrypt(
                        { name: 'AES-GCM', iv: iv },
                        key,
                        ciphertext
                    );
                    
                    if (onProgress) onProgress(100);
                    
                    // Create blob with original type
                    const blob = new Blob([decrypted], { type: metadata.type || 'application/octet-stream' });
                    resolve({
                        blob: blob,
                        filename: metadata.name,
                        metadata: metadata
                    });
                } catch (error) {
                    reject(new Error('Decryption failed. Wrong password?'));
                }
            };
            
            reader.onerror = () => reject(reader.error);
            reader.readAsArrayBuffer(file);
        });
    },

    /**
     * Check password strength
     */
    checkPasswordStrength(password) {
        let score = 0;
        let feedback = [];

        if (password.length >= 8) score += 1;
        if (password.length >= 12) score += 1;
        if (password.length >= 16) score += 1;
        if (/[a-z]/.test(password)) score += 1;
        if (/[A-Z]/.test(password)) score += 1;
        if (/[0-9]/.test(password)) score += 1;
        if (/[^a-zA-Z0-9]/.test(password)) score += 1;

        if (password.length < 8) feedback.push('Use at least 8 characters');
        if (!/[A-Z]/.test(password)) feedback.push('Add uppercase letters');
        if (!/[0-9]/.test(password)) feedback.push('Add numbers');
        if (!/[^a-zA-Z0-9]/.test(password)) feedback.push('Add special characters');

        const levels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong', 'Excellent'];
        const colors = ['#ff4444', '#ff6600', '#ffaa00', '#88cc00', '#00cc44', '#00aa88', '#00d4aa'];

        return {
            score: score,
            percent: Math.min(100, (score / 7) * 100),
            level: levels[Math.min(score, levels.length - 1)],
            color: colors[Math.min(score, colors.length - 1)],
            feedback: feedback
        };
    }
};

// Export for use
window.USAFECrypto = USAFECrypto;
