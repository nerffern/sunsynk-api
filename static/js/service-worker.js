const CACHE_NAME = 'ocs-pwa-v1';
const OFFLINE_URL = '/offline';

const PRECACHE_ASSETS = [
  OFFLINE_URL,
  '/static/css/style.css',
  '/static/css/bootstrap.min.css',
  '/static/css/material-symbols.css',
  '/static/js/jquery-3.3.1.min.js',
  '/static/js/jquery.dataTables.js',
  '/static/js/script.js',
  '/static/js/pwa-register.js',
  '/static/icons/favicon-16.png',
  '/static/icons/favicon-32.png',
  '/static/icons/icon-192-maskable.png',
  '/static/icons/icon-512-maskable.png'
];

const DYNAMIC_API_PATHS = [
  '/health/refresh',
  '/jobs/refresh',
  '/policy/refresh',
  '/license/refresh',
  '/occupancy/refresh'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      Promise.all(
        PRECACHE_ASSETS.map(url =>
          cache.add(url).catch(error => {
            console.warn('Failed to pre-cache', url, error);
            return undefined;
          })
        )
      )
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
          return undefined;
        })
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') {
    return;
  }

  const request = event.request;
  const url = new URL(request.url);

  if (
    url.origin === self.location.origin &&
    DYNAMIC_API_PATHS.some(path => url.pathname.startsWith(path))
  ) {
    event.respondWith(fetch(request));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches.match(request).then(cached => cached || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) {
        return cached;
      }

      return fetch(request)
        .then(response => {
          if (
            response &&
            response.status === 200 &&
            (response.type === 'basic' || response.type === 'cors')
          ) {
            const responseCopy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, responseCopy));
          }
          return response;
        })
        .catch(() => {
          if (request.destination === 'document') {
            return caches.match(OFFLINE_URL);
          }
          return undefined;
        });
    })
  );
});
