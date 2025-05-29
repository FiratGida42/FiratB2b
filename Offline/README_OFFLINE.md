# B2B Portal - Offline Sürüm Kurulum ve Kullanım Rehberi

Bu döküman, B2B portalının çevrimdışı (offline) çalışacak sürümünün kurulumu ve kullanımı hakkında bilgi verir. Bu sürüm, tablet gibi cihazlarda internet bağlantısı olmadan da temel işlevleri kullanmanızı sağlar.

## 📂 Klasör Yapısı (Offline)

```
Offline/
├── main.py                 # Ana FastAPI uygulaması (çevrimdışı)
├── database.py             # Çevrimdışı veritabanı ayarları (SQLite)
├── models.py               # SQLAlchemy veri modelleri (çevrimdışı tablolar)
├── setup_offline.py        # Kurulum ve başlangıç ayar script'i
├── download_assets.py      # Gerekli CSS/JS kütüphanelerini indirme script'i
├── received_products.json  # Yerel ürün verilerinin saklandığı dosya (örnek)
├── b2b_offline_data.db     # SQLite veritabanı dosyası (setup sonrası oluşur)
├── static/                 # Statik dosyalar (CSS, JS, Resimler, JSON verileri)
│   ├── css/
│   ├── js/
│   ├── images/
│   │   ├── icon-192.png    # PWA ikonu (placeholder, değiştirilmeli)
│   │   └── icon-512.png    # PWA ikonu (placeholder, değiştirilmeli)
│   ├── json_data/
│   │   └── filtrelenen_cariler.json # Yerel cari verileri (örnek)
│   ├── manifest.json       # Progressive Web App (PWA) manifest dosyası
│   └── sw.js               # Service Worker script'i (önbellekleme ve offline için)
├── templates/              # HTML şablonları (setup sonrası kopyalanıp düzenlenmeli)
│   ├── offline.html        # Çevrimdışı durumunda gösterilecek sayfa
│   └── (diğer HTML'ler buraya kopyalanacak)
└── .env.example            # Örnek ortam değişkenleri dosyası (opsiyonel)
```

## 🚀 Kurulum Adımları

**Ön Koşullar:**
* Python 3.7+ kurulu olmalı.
* `pip` paket yöneticisi.

**Kurulum:**

1.  **Proje Kök Dizini:** Terminalinizi ana proje (`b2b`) dizinine getirin.
2.  **Gerekli Python Kütüphaneleri:**
    ```bash
    pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-multipart jinja2 python-dotenv requests
    ```
    *(Eğer `requirements.txt` varsa `pip install -r requirements.txt` ile de yüklenebilir.)*

3.  **Offline Klasörüne Geçin:**
    ```bash
    cd Offline
    ```

4.  **Kurulum Script'ini Çalıştırın:**
    Bu script, gerekli alt klasörleri oluşturacak, veritabanını hazırlayacak ve örnek JSON dosyalarını yaratacaktır.
    ```bash
    python setup_offline.py
    ```

5.  **Statik Varlıkları (CSS/JS) İndirin:**
    ```bash
    python download_assets.py
    ```
    Bu script, `static/css` ve `static/js` klasörlerine gerekli kütüphaneleri indirecektir. Bootstrap Icons fontları için manuel indirme gerekebilir (script sonunda notu okuyun).

6.  **HTML Şablonlarını Hazırlayın:**
    *   Ana projenizin `b2b_web_app/templates/` klasöründeki tüm `.html` dosyalarını `Offline/templates/` klasörüne kopyalayın.
    *   **ÖNEMLİ:** Kopyaladığınız bu HTML dosyalarını düzenleyin:
        *   Tüm CDN linklerini (CSS ve JS için) yerel `static/` klasöründeki karşılıklarıyla değiştirin. Örneğin:
            *   `<link href="https://bootswatch.com/5/yeti/bootstrap.min.css" ...>` -> `<link href="/static/css/bootstrap.min.css" ...>`
            *   `<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>` -> `<script src="/static/js/jquery.min.js"></script>`
        *   Her HTML dosyasının `<head>` bölümüne PWA manifest ve Service Worker kaydı için gerekli satırları ekleyin:
            ```html
            <link rel="manifest" href="/static/manifest.json">
            <script>
                if ('serviceWorker' in navigator) {
                    window.addEventListener('load', () => {
                        navigator.serviceWorker.register('/static/sw.js')
                            .then(registration => console.log('ServiceWorker registration successful with scope: ', registration.scope))
                            .catch(err => console.log('ServiceWorker registration failed: ', err));
                    });
                }
            </script>
            ```
        * `<title>` etiketlerini güncelleyerek "(Offline)" ibaresi ekleyebilirsiniz.

7.  **PWA İkonlarını Ekleyin:**
    `Offline/static/images/` klasörüne `icon-192.png` (192x192 piksel) ve `icon-512.png` (512x512 piksel) adında PWA ikonlarınızı ekleyin. `setup_offline.py` scripti placeholder metin dosyaları oluşturur, bunları gerçek resimlerle değiştirin.

8.  **Admin Kullanıcısı:**
    Eğer ana projede `admin_config.json` dosyanız yoksa veya yeni bir tane oluşturmak istiyorsanız, ana proje dizinine dönüp `create_admin.py` script'ini çalıştırın.
    ```bash
    cd .. 
    python create_admin.py
    cd Offline 
    ```
    `Offline/main.py` içindeki `ADMIN_CONFIG_FILE` yolunun doğru olduğundan emin olun (genellikle ana proje dizinini işaret eder).

9.  **(Opsiyonel) Ortam Değişkenleri:**
    `Offline` klasöründe bir `.env` dosyası oluşturarak aşağıdaki değişkenleri ayarlayabilirsiniz (varsayılan değerler de mevcuttur):
    ```env
    # Offline/.env
    OFFLINE_DATABASE_URL="sqlite:///./b2b_offline_data.db"
    PRODUCTS_FILE_PATH="./received_products.json" # main.py ile aynı dizinde
    FASTAPI_SECRET_KEY="cok_gizli_bir_anahtar_buraya_123" # Daha güçlü bir anahtar kullanın
    PRODUCTS_API_KEY="offline_urun_api_anahtari"
    SERVER_API_KEY="offline_musteri_api_anahtari"
    ```

10. **Uygulamayı Başlatın:**
    Terminalde `Offline` klasöründeyken:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8001
    ```
    `--reload` geliştirme sırasında değişiklikleri otomatik algılar. `--host 0.0.0.0` tabletinizin ağ üzerinden erişebilmesi için gereklidir. Port (`8001`) çakışıyorsa farklı bir port kullanabilirsiniz.

## 📱 PWA Olarak Tablete Kurulum

1.  Tablettinizde bir web tarayıcısı (Chrome, Edge vb.) açın.
2.  FastAPI sunucusunun çalıştığı IP adresini ve portu girin. Örneğin, bilgisayarınızın IP adresi `192.168.1.10` ise ve port `8001` ise: `http://192.168.1.10:8001`
3.  Sayfa yüklendikten sonra, tarayıcının menüsünde (genellikle üç nokta veya benzeri bir ikon) "Ana Ekrana Ekle", "Uygulamayı Yükle" veya benzer bir seçenek olacaktır. Buna tıklayın.
4.  Uygulama, tabletinizin ana ekranına bir ikon olarak eklenecektir ve normal bir uygulama gibi başlatılabilir.

## ⚙️ Çevrimdışı Çalışma Prensibi

*   **Service Worker:** Arka planda çalışarak statik varlıkları (HTML, CSS, JS, resimler) ve bazı API yanıtlarını önbelleğe alır. İnternet kesildiğinde bu önbellekten hizmet verir.
*   **Yerel Depolama:**
    *   **SQLite Veritabanı (`b2b_offline_data.db`):** Siparişler gibi dinamik veriler bu veritabanında saklanır.
    *   **JSON Dosyaları:** Ürün listesi (`received_products.json`) ve cari listesi (`static/json_data/filtrelenen_cariler.json`) yerel JSON dosyalarından okunur.
*   **Veri Senkronizasyonu:**
    *   Tablet internete bağlandığında, masaüstü uygulamasından veya sunucudan `/api/products` ve `/api/update-customer-balances` gibi endpoint'lere veri gönderilerek yerel JSON dosyaları güncellenebilir.
    *   Çevrimdışı oluşturulan siparişlerin sunucuya gönderilmesi için Service Worker'ın `sync` özelliği kullanılabilir (bu örnekte tam implementasyonu yapılmamıştır, geliştirilebilir).

## 🔄 Veri Güncelleme (Tablet İnternete Bağlıyken)

*   **Yeni Ürünler:** Masaüstü uygulamanızdan veya başka bir sistemden, tabletin IP adresindeki `http://[tablet_IP]:8001/api/products` endpoint'ine (`PRODUCTS_API_KEY` ile) POST isteği yaparak `received_products.json` dosyasını güncelleyebilirsiniz.
*   **Cari Bakiyeler:** Benzer şekilde, `http://[tablet_IP]:8001/api/update-customer-balances` endpoint'ine (`SERVER_API_KEY` ile) POST isteği yaparak `filtrelenen_cariler.json` dosyasını güncelleyebilirsiniz.

## 🔧 Sorun Giderme

*   **Port Çakışması:** `uvicorn` komutunda farklı bir port kullanın (örn: `--port 8002`).
*   **Veritabanı Sorunları:** `Offline/b2b_offline_data.db` dosyasını silip `setup_offline.py` script'ini tekrar çalıştırabilirsiniz.
*   **Önbellek Sorunları (PWA):** Tarayıcının geliştirici araçlarından (Application -> Storage -> Clear site data) site verilerini ve önbelleği temizleyip uygulamayı yeniden yükleyebilirsiniz.
*   **"ModuleNotFoundError":** Scriptleri doğru klasörden çalıştırdığınızdan emin olun (`Offline` klasörü içinden).

Bu rehber, B2B portalınızın çevrimdışı sürümünü başarıyla kurmanıza ve kullanmanıza yardımcı olacaktır. 