const CACHE_NAME = 'filesender-v1';
const ASSETS = [
  './',
  './index.html',
  './pc-widget.html',
  './manifest.json',
  './widget-template.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// Eventos del Widget de Windows
self.addEventListener('widgetinstall', (event) => {
  console.log('Widget instalado:', event.widget.tag);
});

self.addEventListener('widgetuninstall', (event) => {
  console.log('Widget desinstalado:', event.widget.tag);
});

self.addEventListener('widgetresume', (event) => {
  console.log('Widget resumido:', event.widget.tag);
});

self.addEventListener('widgetclick', (event) => {
  // Manejar clics si es necesario
  console.log('Widget click:', event.action);
});
