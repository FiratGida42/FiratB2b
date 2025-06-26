// Önbellek adını güncelliyoruz, bu sayede eski önbellekler temizlenip yenisi kurulur.
const CACHE_NAME = 'firat-b2b-cache-v2';

// Uygulamanın "kabuğunu" oluşturan, çevrimdışı çalışması gereken tüm dosyalar.
const STATIC_ASSETS = [
  '/',
  '/products',
  '/cart',
  '/orders',
  '/customer-balances',
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

// 3. Fetch (Getirme) Aşaması: İstekleri akıllıca yönet
self.addEventListener('fetch', event => {
  // Yönlendirme yapan istekleri (navigate) veya POST gibi metodları doğrudan ağa gönder.
  // Bu, ana sayfanın /products'a yönlendirmesi gibi işlemlerin engellenmesini önler.
  if (
    event.request.mode === 'navigate' ||
    event.request.method !== 'GET'
  ) {
    event.respondWith(fetch(event.request));
    return;
  }

  // API istekleri için (dinamik veri)
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      // Önce ağı dene (Stale-While-Revalidate'in basitleştirilmiş hali)
      fetch(event.request)
        .then(networkResponse => {
          // Ağdan gelen yanıtı hem önbelleğe kaydet hem de sayfaya döndür
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
        })
        .catch(() => {
          // Ağ hatası olursa, önbellekten yanıtı döndürmeyi dene
          return caches.match(event.request);
        })
    );
    return;
  }

  // Diğer tüm GET istekleri için (statik varlıklar: HTML, CSS, JS)
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Önbellekte varsa direkt oradan döndür
        if (response) {
          return response;
        }
        // Önbellekte yoksa, ağdan getirmeyi dene
        return fetch(event.request);
      })
  );
});

// --- YENİ: Arka Plan Senkronizasyonu (Background Sync) ---
self.addEventListener('sync', event => {
  if (event.tag === 'sync-new-orders') {
    console.log('SYNC: "sync-new-orders" etiketi yakalandı.');
    event.waitUntil(syncNewOrders());
  }
});

function openSyncDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('FiratB2B_DB', 2); // Versiyonun cart.html ile aynı olduğundan emin ol
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getAllFromDB(db, storeName) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const store = tx.objectStore(storeName);
    // getAll() tüm kayıtları, anahtarlarıyla birlikte getirebilir. Biz sadece değerleri istiyoruz.
    const request = store.getAll(); 
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

// Bu fonksiyon tüm bekleyen siparişleri göndermeye çalışacak
async function syncNewOrders() {
  let db;
  try {
    db = await openSyncDB();
    const tx = db.transaction('sync-orders', 'readonly');
    const store = tx.objectStore('sync-orders');
    const request = store.openCursor(); // İmleç ile tek tek ilerleyeceğiz
    
    request.onsuccess = event => {
      const cursor = event.target.result;
      if (cursor) {
        const orderData = cursor.value;
        const orderKey = cursor.key; // Silme işlemi için anahtarı sakla

        console.log('SYNC: Gönderilecek sipariş bulundu:', orderData);

        fetch('/api/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(orderData)
        })
        .then(response => {
          if (!response.ok) {
            // Sunucudan hata dönerse, tekrar denemek üzere bırakabiliriz.
            // Veya hatayı loglayıp siparişi silebiliriz. Şimdilik loglayalım.
            console.error('SYNC: Sunucu siparişi reddetti. Status:', response.status, response.statusText);
            // Belki 4xx hatalarında siparişi silmek mantıklı olabilir.
          } else {
            // Başarılı olursa, siparişi IndexedDB'den sil
            console.log('SYNC: Sipariş başarıyla sunucuya gönderildi. IDBden siliniyor, key:', orderKey);
            // Yeni bir transaction içinde silme işlemi yapmalıyız.
            return openSyncDB().then(db2 => deleteFromDB(db2, 'sync-orders', orderKey));
          }
        })
        .catch(err => {
          // Bu ağ hatası demektir. Bir şey yapmaya gerek yok,
          // tarayıcı sync işlemini daha sonra tekrar deneyecektir.
          console.error('SYNC: Sipariş gönderilemedi (ağ hatası). Daha sonra tekrar denenecek.', err);
          // Hatayı re-throw ederek sync işleminin başarısız olduğunu belirtelim.
          throw err;
        });

        cursor.continue(); // Bir sonraki kayda geç
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