# B2B Entegrasyon ve Yönetim Projesi

Bu proje, bir SQL Server veritabanındaki ürün ve cari bilgilerini çekerek bir web arayüzünde sunmayı ve yönetmeyi amaçlamaktadır. Proje, bir masaüstü yönetim paneli (PySide6 ile geliştirilmiş) ve bir web uygulaması (FastAPI ile geliştirilmiş) olmak üzere iki ana bileşenden oluşmaktadır.

**Canlı Web Uygulaması (Render):** [https://firatb2b.onrender.com](https://firatb2b.onrender.com)

## 🌟 Temel Özellikler

*   **Masaüstü Yönetim Paneli (`main_window.py`):**
    *   SQL Server veritabanına güvenli bağlantı (ayarlar `settings.json` ve `keyring` ile yönetilir).
    *   Veritabanlarını listeleme ve seçme.
    *   Ürün verilerini çekme, filtreleme (grup koduna göre) ve `QTableWidget` üzerinde önizleme.
    *   Filtrelenmiş ürün verilerini JSON formatında kaydetme.
    *   Çekilen ürün verilerini web API'sine (`/api/products`) gönderme. Bu API, `PRODUCTS_API_KEY` ortam değişkeni ile korunur.
    *   Cari hesap verilerini çekme, filtreleme (grup kodu ve arama ile) ve tabloda gösterme.
    *   Filtrelenmiş cari verilerini canlı web uygulamasındaki `/api/update-customer-balances` API endpoint'ine gönderme. Bu işlem `background_scheduler_cariler.pyw` script'i tarafından yapılır ve bu script, API anahtarını yerel `settings.json` dosyasındaki `customer_sync_api_key` alanından okur.
    *   Kategori ağacını statik olarak görüntüleme.
    *   Tam ekran modu, menü çubuğu ve kullanıcı dostu arayüz.
    *   Otomatik ürün güncelleme için zamanlayıcı ayarları.
*   **Web Uygulaması (`b2b_web_app/`):**
    *   FastAPI tabanlı RESTful API'ler.
    *   Ürün ve sipariş yönetimi için API endpoint'leri.
        *   `/api/products`: Masaüstü uygulamasından ürün verilerini alır. Bu endpoint, Render üzerinde `PRODUCTS_API_KEY` adlı bir ortam değişkeni ile tanımlanan API anahtarı ile korunur.
        *   `/api/update-customer-balances`: Yerel `background_scheduler_cariler.pyw` script'inden cari bakiye verilerini alır. Bu endpoint, Render üzerinde `SERVER_API_KEY` adlı bir ortam değişkeni ile tanımlanan API anahtarı ile korunur.
    *   Admin girişi ve yetkilendirme.
    *   Jinja2 şablonları ile dinamik HTML sayfaları:
        *   Ürün listeleme ve detayları.
        *   Sepet ve sipariş oluşturma (admin tarafından).
        *   Cari bakiye görüntüleme.
        *   Siparişleri listeleme ve durum güncelleme.
    *   Masaüstü uygulamasından gönderilen ürün verilerini (`received_products.json`) ve API ile güncellenen cari verilerini (`b2b_web_app/static/json_data/filtrelenen_cariler.json`) kullanarak bilgi sunumu.
*   **Veri Çekme ve İşleme (`data_extractor.py`):**
    *   SQL Server'dan ürün ve cari verilerini çeken merkezi modül.
    *   Türkçe karakter düzeltmeleri ve sayısal veri dönüşümleri yapar.
    *   Ürünler için yerel resim yollarını bulur veya varsayılan bir yer tutucu atar.
*   **Arka Plan Zamanlayıcıları:**
    *   **`background_scheduler.pyw` (Ürünler İçin - Yerel Makinede Çalışır):**
        *   Belirlenen aralıklarla otomatik olarak ürün verilerini çekip web API'sine (`/api/products`) gönderir.
        *   API'ye göndereceği anahtarı yerel `settings.json` dosyasındaki `products_api_key` alanından okur.
    *   **`background_scheduler_cariler.pyw` (Cariler İçin - Yerel Makinede Çalışır):**
        *   Her dakika otomatik olarak cari verilerini SQL Server'dan (yerel veya erişilebilir bir ağdaki) çeker.
        *   Carileri filtreler:
            *   Sadece Grup Kodu "SERVÝS", "TOPTAN" olan veya Grup Kodu boş olan cariler dahil edilir.
            *   Net bakiyesi sıfır olmayan cariler dahil edilir.
        *   Filtrelenmiş verileri canlı web uygulamasındaki bir API endpoint'ine (`/api/update-customer-balances`) gönderir. Bu işlem için kullanılacak API anahtarını yerel `settings.json` dosyasındaki `customer_sync_api_key` alanından okur.
        *   Canlı uygulama (`/api/update-customer-balances` endpoint'i), bu gelen isteği kendi `SERVER_API_KEY` ortam değişkeni ile doğrular ve veriyi alarak sunucudaki `b2b_web_app/static/json_data/filtrelenen_cariler.json` dosyasını günceller.
        *   Yerel script, ayrıca kendi loglarını da tutar (`b2b_web_app/logs/` altında).
*   **Resim İşleme ve İndirme:**
    *   `image_processor.py`: Ürün adlarını temizler, resim URL'lerinden dosya uzantısı alır ve resimleri indirip kaydeder.
    *   `batch_image_downloader.py`: Toplu resim indirme işlemleri için script (DuckDuckGo arama entegrasyonu ile).
*   **Veritabanı Migrasyonları (`alembic/`):**
    *   SQLAlchemy ve Alembic kullanılarak veritabanı şema değişiklikleri yönetilir.

## 🛠️ Kullanılan Teknolojiler

*   **Masaüstü Uygulaması:**
    *   Python 3
    *   PySide6 (Qt for Python)
    *   `pyodbc` (SQL Server bağlantısı)
    *   `keyring` (Güvenli şifre saklama)
    *   `requests` (API istekleri)
    *   `duckduckgo_search` (Otomatik resim bulma)
    *   `schedule` (Arka plan görevleri için)
*   **Web Uygulaması:**
    *   Python 3
    *   FastAPI (Web framework)
    *   Uvicorn (ASGI sunucusu) & Gunicorn (WSGI sunucusu - üretim için)
    *   Jinja2 (Şablon motoru)
    *   SQLAlchemy (ORM)
    *   Alembic (Veritabanı migrasyonları)
    *   Pydantic (Veri doğrulama)
    *   `python-dotenv` (Ortam değişkenleri yönetimi)
    *   `passlib` & `bcrypt` (Şifre hashleme)
*   **Veritabanı:**
    *   Microsoft SQL Server (Ana veri kaynağı)
    *   SQLite (Web uygulaması için potansiyel yerel depolama veya Alembic tarafından kullanılan)
*   **Diğer Araçlar:**
    *   Git (Versiyon kontrolü)

## 🚀 Kurulum ve Başlatma

### Gereksinimler

*   Python 3.9+
*   Microsoft SQL Server
*   ODBC Driver for SQL Server
*   Node.js ve npm (opsiyonel, eğer `prettier` gibi araçlar kullanılacaksa)

### Adımlar

1.  **Proje Klonlama:**
    ```bash
    git clone <proje_git_url>
    cd <proje_dizini>
    ```

2.  **Sanal Ortam Oluşturma ve Aktifleştirme (Önerilir):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```

3.  **Bağımlılıkları Yükleme:**
    ```bash
    pip install -r requirements.txt
    ```
    Gerekirse `python-dotenv` kütüphanesini de yükleyin: `pip install python-dotenv` (FastAPI uygulaması `.env` dosyasını kullanıyorsa).

4.  **Ortam Değişkenleri ve API Anahtarları:**
    *   **Web Uygulaması (Render üzerinde):**
        Canlı web uygulaması (`b2b_web_app/main.py`) için gerekli ortam değişkenleri doğrudan Render platformunun arayüzünden ayarlanmalıdır. Önemli ortam değişkenleri şunlardır:
        *   `FASTAPI_SECRET_KEY`: FastAPI session ve diğer güvenlik işlemleri için güçlü, rastgele bir anahtar.
        *   `PRODUCTS_API_KEY`: `/api/products` endpoint'ini korumak için API anahtarı.
        *   `SERVER_API_KEY`: `/api/update-customer-balances` endpoint'ini korumak için API anahtarı.
        *   `ADMIN_CONFIG_PATH` (Opsiyonel): Admin kullanıcı bilgilerinin tutulduğu dosyanın yolu (varsayılan: `admin_config.json`).
        *   `PRODUCTS_FILE_PATH` (Opsiyonel): Masaüstünden gelen ürünlerin kaydedileceği dosyanın yolu (varsayılan: `received_products.json`).
        *   Eğer veritabanı kullanılıyorsa, `SQLALCHEMY_DATABASE_URL` gibi veritabanı bağlantı bilgileri.
    *   **Yerel Geliştirme için `.env` Dosyası (Opsiyonel):**
        `b2b_web_app` dizini içinde bir `.env` dosyası oluşturarak yukarıdaki ortam değişkenlerini yerel geliştirme ortamınız için tanımlayabilirsiniz. FastAPI uygulaması başlangıçta bu dosyayı okuyacaktır.
        ```env
        FASTAPI_SECRET_KEY="yerel_cok_gizli_bir_anahtar"
        PRODUCTS_API_KEY="yerel_urun_api_anahtari"
        SERVER_API_KEY="yerel_cari_api_anahtari"
        # SQLALCHEMY_DATABASE_URL="sqlite:///./b2b_app_local.sqlite3"
        # ADMIN_CONFIG_PATH="../admin_config.json" # Ana dizindeki config'i işaret edebilir
        ```
    *   **Masaüstü Uygulaması ve Yerel Scriptler (`settings.json`):**
        *   `main_window.py` (Masaüstü Yönetim Paneli):
            *   SQL Server bağlantı bilgileri (sunucu, kullanıcı adı) ve seçilen veritabanı adı `settings.json` dosyasına kaydedilir. Şifre, işletim sisteminin `keyring` servisinde saklanır.
            *   `/api/products` endpoint'ine veri göndermek için kullanılacak API anahtarı `settings.json` içindeki `products_api_key` alanına girilmelidir. Bu anahtar, Render'daki `PRODUCTS_API_KEY` ortam değişkeni ile eşleşmelidir.
        *   `background_scheduler.pyw` (Ürünler İçin Zamanlayıcı):
            *   API anahtarını `settings.json` dosyasındaki `products_api_key` alanından okur.
        *   `background_scheduler_cariler.pyw` (Cariler İçin Zamanlayıcı):
            *   API anahtarını `settings.json` dosyasındaki `customer_sync_api_key` alanından okur. Bu anahtar, Render'daki `SERVER_API_KEY` ortam değişkeni ile eşleşmelidir.

5.  **Admin Kullanıcısı Oluşturma (Web Uygulaması için):**
    Web uygulamasının admin paneline erişim için bir kullanıcı oluşturun:
    ```bash
    python create_admin.py
    ```
    Bu komut, `admin_config.json` (veya `.env`'de belirttiğiniz yolda) dosyasını oluşturacaktır. **Bu dosyayı güvende tutun ve `.gitignore` dosyanızda olduğundan emin olun!**

6.  **Veritabanı Migrasyonları (Web Uygulaması için):**
    Eğer web uygulaması bir veritabanı (örn: SQLite, PostgreSQL) kullanıyorsa ve Alembic ile yönetiliyorsa, migrasyonları uygulayın:
    *   `alembic.ini` dosyasındaki `sqlalchemy.url` adresini kontrol edin ve gerekirse kendi veritabanı bağlantı dizenizle güncelleyin.
    *   Mevcut migrasyonları uygulamak için:
        ```bash
        alembic upgrade head
        ```

7.  **Masaüstü Yönetim Paneli Ayarları:**
    *   `main_window.py` uygulamasını ilk kez çalıştırdığınızda "Ayarlar" bölümüne gidin.
    *   SQL Server bağlantı bilgilerinizi (Sunucu Adresi, Kullanıcı Adı, Şifre) girin.
    *   "Veritabanlarını Listele" butonu ile veritabanınızı seçin.
    *   "Ürünler API Anahtarı" alanına, Render'daki `PRODUCTS_API_KEY` ortam değişkeni için belirlediğiniz/belirleyeceğiniz değeri girin.
    *   "Cariler İçin API Anahtarı" alanına (eğer arayüzde varsa, yoksa doğrudan `settings.json`'a ekleyin: `customer_sync_api_key`), Render'daki `SERVER_API_KEY` ortam değişkeni için belirlediğiniz/belirleyeceğiniz değeri girin.
    *   "Tüm Ayarları Kaydet" butonuna tıklayın. Bu ayarlar `settings.json` dosyasına (şifre işletim sisteminizin `keyring`'ine) kaydedilecektir.

8.  **Masaüstü Yönetim Panelini Çalıştırma:**
    ```bash
    python main_window.py
    ```

9.  **Web Uygulamasını Çalıştırma:**
    `b2b_web_app` dizininde:
    ```bash
    uvicorn main:app --reload
    ```
    Uygulama genellikle `http://127.0.0.1:8000` adresinde çalışacaktır. API dokümantasyonuna `/docs` veya `/redoc` üzerinden erişebilirsiniz.
    Canlı web uygulaması [https://firatb2b.onrender.com](https://firatb2b.onrender.com) adresinde yayınlanmaktadır.

10. **Arka Plan Zamanlayıcısını Çalıştırma (Opsiyonel):**
    Otomatik ürün güncellemeleri için (canlı sunucudaki API'ye veri gönderir):
    ```bash
    pythonw background_scheduler.pyw
    ```
    Otomatik cari bakiye güncellemeleri için (yerel makinede çalışır, canlı sunucuya API ile veri gönderir):
    ```bash
    pythonw background_scheduler_cariler.pyw
    ```
    `.pyw` uzantısı sayesinde bu script'ler genellikle konsol penceresi olmadan arka planda çalışır. `background_scheduler_cariler.pyw` loglarını kendi çalışma dizini altındaki `b2b_web_app/logs/` dizininde bulabilirsiniz. Canlı sunucudaki FastAPI uygulaması ise kendi loglarını Render platformu üzerinden tutacaktır.

    **Not (Yerel Scriptler için):** `background_scheduler.pyw` ve `background_scheduler_cariler.pyw` script'lerinin Windows her açıldığında otomatik olarak başlaması için Windows Görev Zamanlayıcısı'na (Task Scheduler) eklenmeleri önerilir. Görev Zamanlayıcısı'nda "Oturum açtığımda" tetikleyicisi ile `pythonw.exe` programını ve ilgili `.pyw` script'inin tam yolunu argüman olarak belirterek bir görev oluşturabilirsiniz. Script'in bulunduğu dizini "Başlama yeri" olarak ayarlamak önemlidir.

## 📁 Proje Yapısı (Özet)

```
.
├── alembic/                      # Alembic veritabanı migrasyonları
├── b2b_web_app/                  # FastAPI web uygulaması
│   ├── static/                   # Statik dosyalar (CSS, JS, resimler)
│   │   └── images/               # Ürün resimleri (masaüstü uygulamasından senkronize edilebilir)
│   │   └── json_data/            # Web tarafından kullanılan JSON verileri (örn: filtrelenen_cariler.json - Bu dosya canlı sunucuda API ile güncellenir)
│   ├── templates/                # Jinja2 HTML şablonları
│   │   └── __init__.py
│   │   └── database.py               # SQLAlchemy veritabanı bağlantısı ve session yönetimi
│   │   └── main.py                   # Ana FastAPI uygulama dosyası, endpoint'ler
│   │   └── models.py                 # SQLAlchemy veritabanı modelleri ve Pydantic şemaları
│   ├── images/                       # Masaüstü uygulamasında kullanılan genel resimler (örn: urun_yok.png)
│   ├── logs/                         # Uygulama logları (b2b_web_app/logs altına taşındı)
│   ├── __pycache__/                  # Python derlenmiş dosyaları (gitignore ile hariç tutulur)
│   ├── .cursorrules.json             # Cursor IDE için proje kuralları
│   ├── .env                          # Ortam değişkenleri (gitignore ile hariç tutulur)
│   ├── .env.example                  # Ortam değişkenleri için örnek dosya
│   ├── .gitignore                    # Git tarafından takip edilmeyecek dosyalar
│   ├── admin_config.json             # Web admin kullanıcı bilgileri (gitignore ile hariç tutulur)
│   ├── alembic.ini                   # Alembic yapılandırma dosyası
│   ├── background_scheduler.pyw      # Arka planda çalışan otomatik ürün güncelleme scripti
│   ├── background_scheduler_cariler.pyw # Arka planda çalışan otomatik cari bakiye güncelleme scripti (yerel makinede çalışır, canlı sunucuya API ile veri gönderir)
│   ├── batch_image_downloader.py     # Ürünler için toplu resim indirme scripti
│   ├── create_admin.py               # Web admin kullanıcısı oluşturma scripti
│   ├── customers_filter_settings.json# Masaüstü cari filtresi ayarları
│   ├── customers_module.py           # Masaüstü uygulaması için Cari yönetimi sayfası
│   ├── data_extractor.py             # SQL Server'dan veri çekme ve işleme modülü
│   ├── db_connection_ui.py           # (Artık ana panelde) Veritabanı bağlantı arayüzü (eski)
│   ├── filtrelenen_cariler.json      # (Artık kullanılmıyor, sadece referans veya yerel yedek olarak kalabilir) Web'e gönderilecek filtrelenmiş cari verileri 
│   ├── helpers.py                    # Yardımcı fonksiyonlar (örn: para formatlama)
│   ├── image_processor.py            # Resim işleme fonksiyonları
│   ├── main_window.py                # Ana PySide6 masaüstü uygulaması
│   ├── onizlenen_filtrelenmis_urunler.json # Masaüstünde önizlenen ve JSON'a kaydedilen ürünler
│   ├── received_products.json        # Web API'sine gönderilen ve orada kaydedilen ürünler
│   ├── requirements.txt              # Python bağımlılıkları
│   ├── settings.json                 # Masaüstü uygulama ayarları (gitignore ile hariç tutulur)
│   ├── todo.md                       # Yapılacaklar listesi ve tamamlanan görevler
│   └── ui_styles.py                  # PySide6 arayüzü için QSS stil tanımları
```

## 📝 Yapılacaklar ve Gelecek Planları

Detaylı yapılacaklar listesi ve tamamlanan görevler için `todo.md` dosyasına bakınız. Başlıca gelecek planları şunlardır:

*   PostgreSQL veritabanına geçiş için fizibilite ve planlama.
*   Web sitesi için daha gelişmiş kullanıcı rolleri ve yetkilendirme.
*   Çoklu dil desteği.
*   Masaüstü panelinde daha detaylı raporlama ve analiz özellikleri.

##🤝 Katkıda Bulunma

Katkıda bulunmak isterseniz, lütfen bir "issue" açın veya "pull request" gönderin.

## 📄 Lisans

Bu proje [LISANS_TURU] altında lisanslanmıştır. (Eğer varsa lisansınızı buraya ekleyin, örneğin MIT, GPL vb.) 