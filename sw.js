/**
 * USAFE Service Worker
 * Caches the app shell so it works offline. Deliberately does NOT cache the
 * Censorship module's own network requests (DNS-over-HTTPS, IP lookups, the
 * sites being tested) - caching those would make the tests meaningless.
 */

const CACHE_NAME = 'usafe-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/index.html',
    '/manifest.json',
    '/css/style.css',
    '/js/app.js',
    '/js/modules/censorship.js',
    '/js/modules/surveillance.js',
    '/js/modules/secure-comm.js',
    '/js/utils/crypto.js',
    '/js/utils/network.js',
    '/js/utils/fingerprint.js',
    '/js/utils/qrcode.js',
    '/assets/icons/shield.svg'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(ASSETS_TO_CACHE))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((names) => Promise.all(
                names.filter((name) => name !== CACHE_NAME)
                     .map((name) => caches.delete(name))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;
    if (!event.request.url.startsWith('http')) return;

    // Never intercept the Censorship module's measurement requests - those
    // must hit the real network every time, or the tests would just report
    // stale cached results forever.
    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) return;

    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;

            return fetch(event.request)
                .then((response) => {
                    if (response.ok) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    }
                    return response;
                })
                .catch(() => {
                    if (event.request.mode === 'navigate') {
                        return caches.match('/index.html');
                    }
                    return undefined;
                });
        })
    );
});
