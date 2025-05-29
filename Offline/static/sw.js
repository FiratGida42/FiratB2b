const CACHE_NAME = 'b2b-offline-cache-v3'; // Önbellek sürümünü değiştirerek güncelleyebilirsiniz
const OFFLINE_FALLBACK_PAGE = '/offline'; // Özel offline sayfası URL'si

const urlsToCache = [
    '/',
    '/cart',
    '/orders',
    '/customer-balances',
    '/login', // Login sayfası da çevrimdışı görüntülenebilir
    '/admin/me', // Admin sayfası da çevrimdışı görüntülenebilir

    // Ana HTML dosyaları (yukarıdakilerle aynı ama açıkça belirtmek iyi olabilir)
    // '/templates/products.html', // Gerçek dosya yolları değil, URL yolları olacak
    // '/templates/cart.html',
    // ... diğer HTML'ler için URL yolları

    // CSS
    '/static/css/bootstrap.min.css',
    '/static/css/select2.min.css',
    '/static/css/select2-bootstrap-5-theme.min.css',
    '/static/css/dataTables.bootstrap5.min.css',
    '/static/css/bootstrap-icons.css',
    '/static/css/lightgallery.min.css',
    '/static/css/lg-zoom.min.css',
    '/static/css/fonts/bootstrap-icons.woff', // Fontlar
    '/static/css/fonts/bootstrap-icons.woff2',

    // JS
    '/static/js/jquery.min.js',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/select2.full.min.js',
    '/static/js/xlsx.full.min.js',
    '/static/js/jspdf.umd.min.js',
    '/static/js/jspdf.plugin.autotable.min.js',
    '/static/js/jquery.dataTables.min.js',
    '/static/js/dataTables.bootstrap5.min.js',
    '/static/js/lightgallery.min.js',
    '/static/js/lg-zoom.min.js',

    // JSON Veri Dosyaları
    '/static/json_data/received_products.json',
    '/static/json_data/filtrelenen_cariler.json',
    '/static/json_data/tr.json', // DataTables için Türkçe dil dosyası

    // Temel Görseller (Logo, placeholder vb.)
    '/static/images/Logo.png',
    '/static/images/urun_yok.png',
    // '/static/images/urun_placeholder_1.png', // Eğer kullanılıyorsa
    // '/static/images/urun_placeholder_2.png', // Eğer kullanılıyorsa
    // '/static/images/urun_placeholder_3.png', // Eğer kullanılıyorsa
    // '/static/images/favicon.ico', // Eklendi
    '/static/images/icon-192.png',
    '/static/images/icon-512.png',

    OFFLINE_FALLBACK_PAGE, // Offline sayfası
    '/static/manifest.json'
];

// Service Worker kurulumu
self.addEventListener('install', event => {
    console.log('[SW] Install event. Cache Name:', CACHE_NAME); // Cache adını loglayalım
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Opened cache:', CACHE_NAME);
                return cache.addAll(urlsToCache);
            })
            .catch(error => {
                // Hangi URL'in sorun çıkardığını bulmak için daha detaylı loglama
                console.error('[SW] Failed to cache urls during install. Error:', error);
                urlsToCache.forEach(url => {
                    fetch(url).catch(fetchError => console.error(`[SW] Failed to fetch for caching: ${url}`, fetchError));
                });
            })
    );
    self.skipWaiting();
});

// Service Worker aktivasyonu - Eski önbellekleri temizleme
self.addEventListener('activate', event => {
    console.log('[SW] Activate event. Current Cache Name:', CACHE_NAME);
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim(); // Kontrolü hemen al
});

// Ağ isteklerini yönetme (Fetch event)
self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);

    // Sadece kendi origin'imizden gelen GET isteklerini önbellekten sunmaya çalışalım
    // Diğer origin'lerden (CDN vs. olsaydı) veya POST gibi istekleri farklı yönetebiliriz.
    if (event.request.method === 'GET' && requestUrl.origin === self.location.origin) {
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {
                    if (cachedResponse) {
                        // console.log('[SW] Serving from cache:', event.request.url);
                        return cachedResponse;
                    }
                    // console.log('[SW] Fetching from network:', event.request.url);
                    return fetch(event.request).then(networkResponse => {
                        // İsteği önbelleğe alabiliriz (opsiyonel, dinamik içerik için dikkatli olun)
                        // if (networkResponse && networkResponse.status === 200) {
                        //     const responseToCache = networkResponse.clone();
                        //     caches.open(CACHE_NAME).then(cache => {
                        //         cache.put(event.request, responseToCache);
                        //     });
                        // }
                        return networkResponse;
                    }).catch(error => {
                        console.error('[SW] Fetch failed; returning offline page or error for:', event.request.url, error);
                        return caches.match(OFFLINE_FALLBACK_PAGE);
                    });
                })
        );
    } else if (event.request.method === 'POST' && requestUrl.pathname === '/api/orders') {
        // Sipariş POST isteğini yakala (Background Sync için)
        // Şimdilik sadece normal fetch yapmasına izin veriyoruz,
        // Gelişmiş senaryoda burada isteği IndexedDB'ye kaydedip sync event'ini bekleyebiliriz.
        console.log('[SW] Intercepted POST to /api/orders. Passing through for now.');
        event.respondWith(fetch(event.request));
    }
    // Diğer tüm istekler (farklı origin, POST olmayanlar vb.) normal şekilde devam eder.
});


// Arka Plan Senkronizasyon (Background Sync)
self.addEventListener('sync', event => {
    console.log('[SW] Sync event triggered, tag:', event.tag);
    if (event.tag === 'sync-new-order') {
        event.waitUntil(syncNewOrders()); // Bu fonksiyon IndexedDB'den siparişleri alıp gönderecek
    } else if (event.tag === 'manual-sync-trigger') {
        // Manuel tetikleme için de aynı veya farklı bir senkronizasyon fonksiyonu çağrılabilir.
        event.waitUntil(
            Promise.all([
                syncNewOrders()
                // syncOtherDataIfNeeded() // Başka senkronize edilecek veri varsa
            ]).then(() => {
                console.log('[SW] Manual sync tasks completed.');
                 // İsteğe bağlı: Tüm açık client'lara senkronizasyonun bittiğini bildirin
                self.clients.matchAll().then(clients => {
                    clients.forEach(client => {
                        client.postMessage({ type: 'SYNC_COMPLETED', tag: event.tag });
                    });
                });
            }).catch(err => {
                console.error('[SW] Error during manual sync tasks:', err);
            })
        );
    }
});

// Örnek bir senkronizasyon fonksiyonu (IndexedDB ile çalışacak şekilde geliştirilmeli)
async function syncNewOrders() {
    console.log('[SW] Attempting to sync new orders...');
    // 1. IndexedDB'den "PENDING_SYNC" durumundaki siparişleri çek
    // 2. Her birini /api/orders adresine POST et
    // 3. Başarılı olursa IndexedDB'den sil veya durumunu "SYNCED" yap
    // Bu kısım IndexedDB helper kütüphanesi (idb.js gibi) veya direkt IndexedDB API'si ile yazılmalı.
    // Şimdilik sadece bir log basıyoruz.
    try {
        // const pendingOrders = await getPendingOrdersFromDB(); // Farazi fonksiyon
        // if (pendingOrders && pendingOrders.length > 0) {
        //     for (const order of pendingOrders) {
        //         const response = await fetch('/api/orders', {
        //             method: 'POST',
        //             headers: {'Content-Type': 'application/json'},
        //             body: JSON.stringify(order.payload) // payload, IndexedDB'de saklanan sipariş verisi
        //         });
        //         if (response.ok) {
        //             await markOrderAsSyncedInDB(order.id); // Farazi fonksiyon
        //             console.log('[SW] Order synced successfully:', order.id);
        //         } else {
        //             console.error('[SW] Failed to sync order:', order.id, await response.text());
        //         }
        //     }
        // } else {
        //     console.log('[SW] No pending orders to sync.');
        // }
        console.log('[SW] syncNewOrders function needs to be implemented with IndexedDB.');
    } catch (error) {
        console.error('[SW] Error during syncNewOrders:', error);
    }
}

// Push bildirimleri (isteğe bağlı)
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event.data.text());
  const title = 'B2B Portal';
  const options = {
    body: event.data.text(),
    icon: '/static/images/icon-192.png',
    badge: '/static/images/icon-192.png'
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click received.');
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/') // Bildirime tıklandığında ana sayfayı aç
  );
});

console.log('[SW] Service Worker script loaded and evaluated.'); 