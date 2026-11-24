/* Salfa Studio service worker: works offline for pages already visited.
   Pages: network first, cached copy if offline, offline.html as last resort.
   Static assets: cache first. Data JSON: network first. Never touched: other origins
   (Supabase, YouTube, fonts), POST requests, video files, studio.html (always live). */
const V = "salfa-v1";
const SHELL = ["/", "/episodes.html", "/offline.html", "/assets/site.css", "/assets/icon-192.png", "/favicon.ico"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
const put = (req, res) => { if (res && res.ok && res.type === "basic") { const c = res.clone(); caches.open(V).then((x) => x.put(req, c)); } return res; };
self.addEventListener("fetch", (e) => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin) return;
  if (u.pathname.startsWith("/media/") || u.pathname === "/studio.html" || u.pathname === "/callback.html") return;
  if (r.mode === "navigate") {
    e.respondWith(fetch(r).then((res) => put(r, res)).catch(() =>
      caches.match(r, { ignoreSearch: true }).then((m) => m || caches.match("/offline.html"))));
    return;
  }
  if (u.pathname.startsWith("/data/") || u.pathname.endsWith(".json") || u.pathname.endsWith(".xml")) {
    e.respondWith(fetch(r).then((res) => put(r, res)).catch(() => caches.match(r)));
    return;
  }
  if (u.pathname.startsWith("/assets/") || u.pathname === "/favicon.ico") {
    e.respondWith(caches.match(r).then((m) => m || fetch(r).then((res) => put(r, res))));
  }
});
