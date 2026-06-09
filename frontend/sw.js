const CACHE = 'mtg-judge-v1';
const PRECACHE = ['/', '/manifest.json', '/icon.svg'];

// On install: cache the app shell so the UI loads offline
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

// On activate: evict old cache versions
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API calls always go to the network — never serve stale answers
  const API_PATHS = ['/ask', '/card/', '/search', '/health'];
  if (API_PATHS.some(p => url.pathname.startsWith(p))) return;

  // Shell assets: cache-first with network fallback + dynamic caching
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        const clone = response.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return response;
      });
    })
  );
});
