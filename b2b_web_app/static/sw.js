// Önbellek adını güncelliyoruz, bu sayede eski önbellekler temizlenip yenisi kurulur.
const CACHE_NAME = 'firat-b2b-cache-v4';

// Uygulamanın "kabuğunu" oluşturan, çevrimdışı çalışması gereken tüm dosyalar.
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/images/Logo.png',
  'https://bootswatch.com/5/yeti/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/css/lightgallery.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/css/lg-zoom.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/lightgallery.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.1/plugins/zoom/lg-zoom.min.js'
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

// 3. Fetch (Getirme) Aşaması: SADECE API isteklerini ve statik varlıkları yönet
self.addEventListener('fetch', event => {
  // HTML sayfalarına hiç karışma - direkt ağa git
  if (
    event.request.mode === 'navigate' ||
    event.request.destination === 'document' ||
    event.request.url.includes('/products') ||
    event.request.url.includes('/cart') ||
    event.request.url.includes('/orders') ||
    event.request.url.includes('/customer-balances') ||
    event.request.url.endsWith('/') ||
    event.request.method !== 'GET'
  ) {
    // Bu istekleri hiç engelleme, direkt ağa git
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

  // Statik varlıklar için cache-first stratejisi
  if (
    event.request.url.includes('/static/') ||
    event.request.url.includes('bootstrap') ||
    event.request.url.includes('lightgallery') ||
    event.request.url.includes('cdn.jsdelivr')
  ) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          return response || fetch(event.request);
        })
    );
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