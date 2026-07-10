/* ICML 2026 schedule — service worker: network-first with full cache fallback */
var VERSION = 'icml2026-v8';
var SHELL = [
  './',
  'index.html',
  'manifest.webmanifest',
  'assets/style.css',
  'assets/app.js',
  'assets/icon-192.png',
  'assets/icon-512.png',
  'data/schedule.js',
  'data/details.js'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(VERSION).then(function (c) { return c.addAll(SHELL); }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== VERSION; }).map(function (k) {
        return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;

  e.respondWith(
    fetch(req).then(function (resp) {
      if (resp && resp.status === 200) {
        var copy = resp.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
      }
      return resp;
    }).catch(function () {
      return caches.match(req, { ignoreSearch: req.mode === 'navigate' }).then(function (hit) {
        if (hit) return hit;
        if (req.mode === 'navigate') return caches.match('index.html');
        return new Response('', { status: 504 });
      });
    })
  );
});
