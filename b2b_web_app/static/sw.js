// Önbellek adını güncelliyoruz, bu sayede eski önbellekler temizlenip yenisi kurulur.
const CACHE_NAME = 'firat-b2b-cache-v8';

// Uygulamanın "kabuğunu" oluşturan, çevrimdışı çalışması gereken tüm dosyalar.
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/images/Logo.png',
  // HTML sayfaları da önbelleğe alıyoruz
  '/products',
  '/cart', 
  '/orders',
  '/customer-balances',
  'https://bootswatch.com/5/yeti/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/css/lightgallery.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/css/lg-zoom.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/lightgallery.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/plugins/zoom/lg-zoom.min.js',
  // jQuery ve Select2 bağımlılıkları (cart.html için)
  'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.full.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/css/select2.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/select2-bootstrap-5-theme/1.3.0/select2-bootstrap-5-theme.min.css',
  // DataTables bağımlılıkları (customer_balances.html için)
  'https://code.jquery.com/jquery-3.7.0.js',
  'https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js',
  'https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js',
  'https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css'
];

// 1. Install (Kurulum) Aşaması: Statik varlıkları önbelleğe al
self.addEventListener('install', event => {
  console.log('SW Install: Yeni Service Worker kuruluyor.');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('SW Install: Önbellek açıldı, statik varlıklar ekleniyor.');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        // Yeni Service Worker'ın beklemeden, hemen aktif olmasını sağla.
        // Bu, güncelleme sürecini hızlandırır.
        console.log('SW Install: skipWaiting() çağrıldı.');
        return self.skipWaiting();
      })
  );
});

// 2. Activate (Aktivasyon) Aşaması: Eski önbellekleri temizle
self.addEventListener('activate', event => {
  console.log('SW Activate: Yeni Service Worker aktifleşiyor.');
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('SW Activate: Eski önbellek siliniyor:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Service Worker'ın kontrolü hemen almasını sağla.
      // Bu, açık olan tüm sekmelerin yeni SW tarafından yönetilmesini garantiler.
      console.log('SW Activate: clients.claim() çağrıldı.');
      return self.clients.claim();
    })
  );
});

// 3. Fetch (Getirme) Aşaması: API isteklerini, statik varlıkları ve HTML sayfalarını yönet
self.addEventListener('fetch', event => {
  // POST, PUT, DELETE gibi istekleri hiç engelleme
  if (event.request.method !== 'GET') {
    return;
  }

  // Cart sayfası için cache-first stratejisi (offline çalışması için)
  if (event.request.url.includes('/cart')) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          if (response) {
            return response;
          }
          // Cache'te yoksa network'ten al ve cache'e kaydet
          return fetch(event.request).then(fetchResponse => {
            if (fetchResponse && fetchResponse.status === 200) {
              const responseToCache = fetchResponse.clone();
              caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, responseToCache);
              });
            }
            return fetchResponse;
          }).catch(() => {
            // Offline fallback
            return new Response(`
              <!DOCTYPE html>
              <html lang="tr">
              <head>
                  <meta charset="UTF-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                  <title>Sepet - Çevrimdışı</title>
                  <link href="https://bootswatch.com/5/yeti/bootstrap.min.css" rel="stylesheet">
              </head>
              <body>
                  <div class="container mt-5">
                      <h1>Sepet - Çevrimdışı Modu</h1>
                      <p>Sepet sayfası çevrimdışı olarak yüklenemedi.</p>
                      <button onclick="location.reload()" class="btn btn-primary">Yeniden Dene</button>
                      <a href="/products" class="btn btn-secondary">Ürünlere Dön</a>
                  </div>
              </body>
              </html>
            `, {
              headers: { 'Content-Type': 'text/html' }
            });
          });
        })
    );
    return;
  }

  // Diğer HTML sayfaları için network-first stratejisi (çevrimdışı fallback ile)
  if (
    event.request.mode === 'navigate' ||
    event.request.destination === 'document' ||
    event.request.url.includes('/products') ||
    event.request.url.includes('/orders') ||
    event.request.url.includes('/customer-balances') ||
    event.request.url.endsWith('/')
  ) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Başarılı yanıtı cache'e kaydet
          if (response && response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => {
          // Çevrimdışıysa cache'ten döndür
          return caches.match(event.request).then(cachedResponse => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // Cache'te de yoksa basit bir offline sayfası döndür
            return new Response(`
              <!DOCTYPE html>
              <html lang="tr">
              <head>
                  <meta charset="UTF-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                  <title>Çevrimdışı - B2B Portalı</title>
                  <link href="https://bootswatch.com/5/yeti/bootstrap.min.css" rel="stylesheet">
              </head>
              <body>
                  <div class="container mt-5 text-center">
                      <h1 class="text-primary">Çevrimdışı Modu</h1>
                      <p class="lead">Bu sayfa çevrimdışı kullanıma hazır değil.</p>
                      <p>Lütfen internet bağlantınızı kontrol edin veya ana sayfaya dönün.</p>
                      <a href="/products" class="btn btn-primary">Ana Sayfaya Dön</a>
                      <button onclick="location.reload()" class="btn btn-secondary">Yeniden Dene</button>
                  </div>
              </body>
              </html>
            `, {
              headers: { 'Content-Type': 'text/html' }
            });
          });
        })
    );
    return;
  }

  // API istekleri için cache-then-network stratejisi
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(networkResponse => {
          // Ağdan gelen yanıtı önbelleğe kaydet
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
        })
        .catch(() => {
          // Ağ hatası olursa, önbellekten yanıtı döndür
          return caches.match(event.request);
        })
    );
    return;
  }

  // Statik varlıklar ve resimler için cache-first stratejisi
  if (
    event.request.url.includes('/static/') ||
    event.request.url.includes('bootstrap') ||
    event.request.url.includes('lightgallery') ||
    event.request.url.includes('cdn.jsdelivr') ||
    event.request.url.includes('/images/') ||
    event.request.destination === 'image' ||
    /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(event.request.url)
  ) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          if (response) {
            return response;
          }
          // Cache'te yoksa, ağdan çek ve cache'e kaydet
          return fetch(event.request).then(fetchResponse => {
            if (fetchResponse && fetchResponse.status === 200) {
              const responseToCache = fetchResponse.clone();
              caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, responseToCache);
              });
            }
            return fetchResponse;
          }).catch(() => {
            // Resim yüklenemezse varsayılan resim döndür (isteğe bağlı)
            if (event.request.destination === 'image') {
              return caches.match('/static/images/Logo.png');
            }
          });
        })
    );
    return;
  }
});

// --- Background Sync için helper fonksiyonlar ---
function openSyncDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('FiratB2B_DB', 2);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function deleteFromDB(db, storeName, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const request = store.delete(key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// --- Background Sync Event Handler ---
self.addEventListener('sync', event => {
  if (event.tag === 'sync-new-orders') {
    console.log('SYNC: "sync-new-orders" etiketi yakalandı.');
    event.waitUntil(syncNewOrders());
  }
});

// Bu fonksiyon tüm bekleyen siparişleri göndermeye çalışacak
async function syncNewOrders() {
  let db;
  try {
    db = await openSyncDB();
    const tx = db.transaction('sync-orders', 'readonly');
    const store = tx.objectStore('sync-orders');
    const request = store.openCursor();
    
    request.onsuccess = event => {
      const cursor = event.target.result;
      if (cursor) {
        const orderData = cursor.value;
        const orderKey = cursor.key;

        console.log('SYNC: Gönderilecek sipariş bulundu:', orderData);

        fetch('/api/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(orderData)
        })
        .then(response => {
          if (!response.ok) {
            console.error('SYNC: Sunucu siparişi reddetti. Status:', response.status, response.statusText);
          } else {
            console.log('SYNC: Sipariş başarıyla sunucuya gönderildi. IDBden siliniyor, key:', orderKey);
            return openSyncDB().then(db2 => deleteFromDB(db2, 'sync-orders', orderKey));
          }
        })
        .catch(err => {
          console.error('SYNC: Sipariş gönderilemedi (ağ hatası). Daha sonra tekrar denenecek.', err);
          throw err;
        });

        cursor.continue();
      } else {
        console.log('SYNC: Gönderilecek başka sipariş kalmadı.');
      }
    };
    request.onerror = (event) => {
        console.error('SYNC: IndexedDB cursor hatası:', event.target.error);
    };

  } catch (error) {
    console.error('SYNC: Senkronizasyon işlemi sırasında hata:', error);
  } finally {
    if (db) {
      db.close();
    }
  }
} 