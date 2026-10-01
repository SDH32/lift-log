// Lets the app open without a connection. Network first, so updates show up right away;
// the saved copy is used when offline, or if the network takes longer than 3 seconds.
const CACHE = 'liftlog';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const cached = () => caches.match(req, { ignoreSearch: true });
  // no-cache: always ask the server if there's a newer version (GitHub Pages otherwise lets the
  // browser reuse a copy for 10 minutes). Page loads have to be refetched by URL.
  const network = fetch(req.mode === 'navigate' ? req.url : req, { cache: 'no-cache' }).then((res) => {
    if (res.ok) {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
    }
    return res;
  });
  const slow = new Promise((r) => setTimeout(r, 3000)).then(cached).then((hit) => hit || network);
  e.respondWith(Promise.race([network, slow]).catch(() => cached().then((hit) => hit || Response.error())));
});
